"""Executes the conformance scenarios of <examples>/conformance-scenarios against the prototype store.

usage: run_scenarios.py <examples dir> [--capabilities flag,flag,...] [--only ID]
Reports passed / failed / inapplicable per scenario. With --capabilities, the store is capability-limited and a
scenario must be passed or inapplicable, never failed."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import khg_synth as K  # noqa: E402
import khg_store_proto as P  # noqa: E402

EX = Path(sys.argv[1])
CAPS = None
ONLY = None
args = sys.argv[2:]
while args:
    a = args.pop(0)
    if a == "--capabilities":
        CAPS = frozenset(x for x in args.pop(0).split(",") if x)
    elif a == "--only":
        ONLY = args.pop(0)

FIX = json.loads((EX / "fixture.c1.json").read_text(encoding="utf-8"))
S = K.Schema(json.loads((EX / "fixture.relation-schema.json").read_text(encoding="utf-8")))
REC = {r["id"]: r for r in FIX["records"]}
ENTITIES = [r for r in FIX["records"] if r["kind"] == "entity"]
CORE_DROP = {"f:route-1", "f:born-scribe", "f:cat-7", "g:who-1774"}
CORE = {"header": copy.deepcopy(FIX["header"]), "records": [r for r in FIX["records"] if r.get("id") not in CORE_DROP]}
try:
    import jsonschema
    HS = json.loads((HERE.parent.parent / "probes" / "hif-schema" / "hif_schema_v0.1.0.json").read_text())
except ImportError:  # pragma: no cover
    jsonschema = None


class Fail(Exception):
    pass


def resolve(x):
    if isinstance(x, str) and x.startswith("@"):
        if x == "@entities":
            return copy.deepcopy(ENTITIES)
        if x == "@fixture":
            return copy.deepcopy(FIX)
        if x == "@fixture[core]":
            return copy.deepcopy(CORE)
        if x == "@fixture.header":
            return copy.deepcopy(FIX["header"])
        rid, _, path = x[1:].partition(".")
        return copy.deepcopy(REC[rid][path]) if path else copy.deepcopy(REC[rid])
    if isinstance(x, dict) and "@" in x:
        r = resolve("@" + x["@"])
        for k, v in x.get("set", {}).items():
            r[k] = resolve(v) if isinstance(v, (dict, list, str)) else v
        for k in x.get("drop", []):
            r.pop(k, None)
        bids = {b["bid"]: b for b in r.get("bindings", [])}
        for bid, val in x.get("set_binding", {}).items():
            bids[bid]["value"] = copy.deepcopy(val)
        for bid in x.get("drop_bindings", []):
            r["bindings"] = [b for b in r["bindings"] if b["bid"] != bid]
            for e in r.get("evidence", []):
                if "supports" in e:
                    e["supports"] = [s for s in e["supports"] if s != bid]
        evs = {e["id"]: e for e in r.get("evidence", [])}
        for eid, fields in x.get("set_evidence", {}).items():
            evs[eid].update(copy.deepcopy(fields))
        if "add_evidence" in x:
            r.setdefault("evidence", []).extend(copy.deepcopy(x["add_evidence"]))
        return r
    if isinstance(x, list):
        return [resolve(v) for v in x]
    if isinstance(x, dict):
        return {k: resolve(v) for k, v in x.items()}
    return x


def flat(items):
    out = []
    for it in items:
        r = resolve(it)
        out.extend(r if isinstance(r, list) else [r])
    return out


def new_store():
    return P.ProtoStore(S, clock=P.Clock(), capabilities=CAPS, store_id="conformance")


def run_given(store, given):
    for g in given:
        if "load" in g:
            store.load(resolve(g["load"]))
        elif "put" in g:
            recs = flat(g["put"])
            if "atomic_writes" in store.flags or len(recs) <= 1:
                store.put(recs, actor="scenario", at=g.get("at"))
            else:  # one record per call for a store without atomic_writes (entities come first in every put step)
                for i, r in enumerate(recs):
                    store.put(r, actor="scenario", at=g.get("at") if i == 0 else None)
        elif "apply" in g:
            store.apply(resolve(g["apply"]), actor="scenario", at=g.get("at"))


def call(store, st):
    a = copy.deepcopy(st["args"])
    at = st.get("at")
    o = st["op"]
    if "where" in a:
        a["where"] = P.Where.of(a["where"])
    if o == "put":
        return store.put(flat(a["records"]), actor="scenario", at=at, expect=a.get("expect"))
    if o == "apply":
        return store.apply(resolve(a["event"]), actor="scenario", at=at)
    if o == "get":
        return store.get(a["id"], as_at=a.get("as_at"), version=a.get("version"))
    if o == "history":
        return store.history(a["id"])
    if o == "get_many":
        return store.get_many(a["ids"], as_at=a.get("as_at"))
    if o == "incident":
        return store.incident(a["node"], role=a.get("role"), relation=a.get("relation"), where=a.get("where"),
                              limit=a.get("limit"), after=a.get("after"))
    if o == "degree":
        return store.degree(a["node"], role=a.get("role"), relation=a.get("relation"), where=a.get("where"))
    if o == "find":
        return store.find(a["relation"], a["pattern"], match=a.get("match", "at_least"), where=a.get("where"),
                          limit=a.get("limit"), after=a.get("after"))
    if o == "find_by_key":
        return store.find_by_key(a["relation"], a["key"], where=a.get("where"))
    if o == "supersession_walk":
        return store.supersession_walk(a["id"], direction=a.get("direction", "forward"), as_at=a.get("as_at"))
    if o == "export":
        hdr = resolve(a["header"]) if "header" in a else None
        return store.export(a.get("format", "khg-json"), content=a.get("content", "snapshot"), as_at=a.get("as_at"),
                            relations=a.get("relations"), header=hdr)
    raise Fail(f"unknown op {o}")


def canonical_no_store(r):
    r = K.canonical_record(r)
    for f in K.STORE_FIELDS:
        r.pop(f, None)
    return r


def path_get(obj, parts):
    for p in parts:
        if obj is None:
            return None
        if isinstance(obj, list):
            obj = obj[int(p)]
        else:
            obj = obj.get(p)
    return obj


def project(result, sel, store):
    if sel == "ids":
        if isinstance(result, dict):
            return sorted(result)
        return [r["id"] for r in result]
    if sel == "value":
        return result
    if sel == "record":
        return result
    if sel == "canonical":
        return canonical_no_store(result) if result else None
    if sel in ("version", "status", "status_ref", "goal"):
        return None if result is None else result.get(sel)
    if sel == "versions":
        return [x["version"] for x in result]
    if sel == "receipt.records":
        return result["records"]
    if sel == "receipt.warnings":
        return result.get("warnings", [])
    if sel == "evidence.ids":
        return [e["id"] for e in result.get("evidence", [])]
    if sel.startswith("evidence."):
        _, eid, fld = sel.split(".", 2)
        e = next((e for e in result.get("evidence", []) if e["id"] == eid), None)
        return None if e is None else path_get(e, fld.split("."))
    if sel.startswith("binding."):
        _, bid, fld = sel.split(".", 2)
        b = next((b for b in result["bindings"] if b["bid"] == bid), None)
        return None if b is None else path_get(b, fld.split("."))
    if sel.startswith("derived."):
        return path_get(K.derived(S, result), sel.split(".")[1:])
    if sel == "terminal":
        return result["terminal"]
    if sel == "terminal.ids":
        return [t["id"] for t in result["terminal"]]
    if sel == "steps.count":
        return len(result["steps"])
    if sel.startswith("record."):
        rid, _, fld = sel[len("record."):].rpartition(".")
        r = next((x for x in result["records"] if x.get("id") == rid), None)
        return None if r is None else r.get(fld)
    if sel.startswith("versions."):
        rid = sel[len("versions."):]
        lines = [json.loads(x) for x in result.splitlines()]
        return [x["version"] for x in lines[1:] if x.get("id") == rid]
    if sel.startswith("header."):
        return path_get(result["header"], sel.split(".")[1:])
    if sel.startswith("metadata."):
        return result["metadata"].get(sel[len("metadata."):])
    if sel.startswith("node."):
        rest = sel[len("node."):]
        nid, _, path = rest.partition(".attrs.")
        n = next((x for x in result["nodes"] if x["node"] == nid), None)
        return None if n is None else path_get(n["attrs"], path.split("."))
    raise Fail(f"unknown projection {sel}")


def expected(v, store):
    if isinstance(v, str) and v.startswith("@"):
        return canonical_no_store(resolve(v))
    if isinstance(v, str) and "{store_id}" in v:
        return v.replace("{store_id}", store.store_id)
    return v


def subset(exp, got):
    if isinstance(exp, dict):
        return isinstance(got, dict) and all(k in got and subset(v, got[k]) for k, v in exp.items())
    if isinstance(exp, list):
        return isinstance(got, list) and len(exp) == len(got) and all(subset(a, b) for a, b in zip(exp, got))
    return exp == got


def strip_attrs(h, ignore):
    h = copy.deepcopy(h)
    for coll in ("nodes", "edges", "incidences"):
        for x in h.get(coll, []):
            for k in ignore:
                (x.get("attrs") or {}).pop(k, None)
    return h


def hif_ok(h):
    if jsonschema is not None:
        errs = list(jsonschema.Draft7Validator(HS).iter_errors(h))
        if errs:
            raise Fail(f"HIF schema: {errs[0].message}")
    K.hif_to_c1(h, S)


def check_then(store, st, then, result, sc):
    if "select" in then:
        got = project(result, then["select"], store)
        want = expected(then["equals"], store)
        if K.cjson(got) != K.cjson(want):
            raise Fail(f"{st['op']} {then['select']}: got {json.dumps(got, ensure_ascii=False)[:300]} "
                       f"want {json.dumps(want, ensure_ascii=False)[:300]}")
    if "container_equals" in then:
        want = resolve(then["container_equals"])
        d = P.compare_containers(want, result, ignore=tuple(then.get("ignore", ())))
        if d:
            raise Fail(f"container differs: {json.dumps(d[:2], ensure_ascii=False)[:600]}")
    if then.get("hif_valid"):
        hif_ok(result)
    if "equals_file" in then:
        want = json.loads((EX / then["equals_file"]).read_text(encoding="utf-8"))
        ig = then.get("ignore", [])
        if K.cjson(strip_attrs(result, ig)) != K.cjson(strip_attrs(want, ig)):
            raise Fail("export differs from " + then["equals_file"])
    if then.get("reload_equal"):
        lines = [json.loads(x) for x in result.splitlines()]
        s2 = new_store()
        s2.load({"header": lines[0], "records": lines[1:]})
        again = s2.export(st["args"].get("format", "khg-jsonl"), content=st["args"].get("content", "snapshot"))
        if again != result:
            raise Fail("reload_equal: exports differ")
    if then.get("deterministic"):
        s2 = new_store()
        run_given(s2, sc["given"])
        if call(s2, st) != result:
            raise Fail("deterministic: two runs differ")


def run(sc):
    if CAPS is not None and not set(sc["requires"]) <= CAPS:
        return "inapplicable", ""
    store = new_store()
    try:
        try:
            run_given(store, sc["given"])
        except K.KHGError as e:
            raise Fail(f"given: unexpected {e.code}: {e}")
        for st in sc["when"]:
            then = st["then"]
            if "error" in then:
                try:
                    call(store, st)
                except K.KHGError as e:
                    if e.code != then["error"]:
                        raise Fail(f"{st['op']}: raised {e.code} ({e}), want {then['error']}")
                    if "info" in then and not subset(then["info"], e.info):
                        raise Fail(f"{st['op']}: info {json.dumps(e.info, ensure_ascii=False)[:700]} does not match "
                                   f"{json.dumps(then['info'], ensure_ascii=False)[:700]}")
                    continue
                raise Fail(f"{st['op']}: did not raise {then['error']}")
            try:
                result = call(store, st)
            except K.KHGError as e:
                raise Fail(f"{st['op']}: unexpected {e.code}: {e} {json.dumps(e.info, ensure_ascii=False)[:500]}")
            check_then(store, st, then, result, sc)
    except P.CapabilityMissing as e:
        return "inapplicable", f"capability {e.flag} (not declared in requires)" if e.flag not in sc["requires"] else ""
    except Fail as f:
        return "failed", str(f)
    return "passed", ""


files = sorted((EX / "conformance-scenarios").glob("S-*.json"))
res = {}
for f in files:
    sc = json.loads(f.read_text(encoding="utf-8"))
    if ONLY and not sc["id"].startswith(ONLY):
        continue
    outcome, msg = run(sc)
    res.setdefault(outcome, []).append(sc["id"])
    if outcome == "failed" or msg:
        print(f"{outcome.upper():12} {sc['id']}: {msg}")
print({k: len(v) for k, v in res.items()}, "capabilities:", "all" if CAPS is None else sorted(CAPS))
sys.exit(1 if res.get("failed") else 0)
