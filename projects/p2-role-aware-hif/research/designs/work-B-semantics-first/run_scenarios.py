"""Minimal runner for declarative C2 conformance scenarios against the prototype store."""
import copy, json, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from khg_proto import Schema, KHGError, derived
from proto_store import MemoryStore
FX = {r["id"]: r for r in json.loads((HERE / "fixture-directed.khg.json").read_text())["records"]}

def materialise(x):
    if isinstance(x, str) and x.startswith("@fixture:"):
        return copy.deepcopy(FX[x[len("@fixture:"):]])
    if isinstance(x, dict) and "@fixture" not in x:
        return copy.deepcopy(x)          # an inline record
    r = copy.deepcopy(FX[x["@fixture"]])
    for k in x.get("drop", []): r.pop(k, None)
    r.update(x.get("set", {}))
    r["bindings"] = [b for b in r.get("bindings", []) if b["bid"] not in x.get("drop_bindings", [])]
    for ev in r.get("evidence", []):
        if ev["id"] in x.get("set_evidence_supports", {}):
            ev["supports"] = x["set_evidence_supports"][ev["id"]]
    r.setdefault("evidence", []).extend(copy.deepcopy(x.get("add_evidence", [])))
    for bid, v in x.get("set_binding", {}).items():
        next(b for b in r["bindings"] if b["bid"] == bid)["value"] = v
    return r

def run(path):
    sc = json.loads(Path(path).read_text())
    S = Schema(json.loads((HERE / sc["schema"]).read_text()))
    clock_value = {"t": None}
    store = MemoryStore(S, lambda: clock_value["t"])
    for step in sc["given"]:
        clock_value["t"] = step["at"]
        store.put([materialise(x) for x in step["put"]])
    clock_value["t"] = "2026-10-01T00:59:59Z"
    ok = True
    for w in sc["when"]:
        args = dict(w["args"])
        if "records" in args: args["records"] = [materialise(x) for x in args["records"]]
        try:
            fn = getattr(store, w["op"])
            got = fn(**({"records": args["records"]} if w["op"] == "put" else {k: v for k, v in args.items()}))
            sel = w["then"].get("select")
            if sel == "status": got = got["status"]
            elif sel == "ids": got = [r["id"] for r in (got.items if hasattr(got, "items") and not isinstance(got, (list, dict)) else got)]
            elif sel == "receipt": got = [list(x) for x in got["records"]]
            elif sel == "valid_time_kind": got = derived(S, got)["valid_time"]["kind"]
            want = w["then"].get("equals", "<error>")
        except KHGError as ex:
            got, want = ex.code, w["then"].get("error")
        good = got == want
        ok &= good
        print(f"   {'PASS' if good else 'FAIL'} {sc['id']} {w['op']}({', '.join(f'{k}=...' if k == 'records' else f'{k}={v!r}' for k, v in w['args'].items())[:90]}) -> {got!r}"[:200])
    return ok

allok = all([run(p) for p in sorted((HERE / "scenarios").glob("*.json"))])
print("ALL SCENARIOS PASS" if allok else "SCENARIO FAILURES")
