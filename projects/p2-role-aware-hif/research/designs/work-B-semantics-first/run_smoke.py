import copy, json, sys, itertools
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import jsonschema
from referencing import Registry, Resource
from khg_proto import Schema, KHGError, cjson, canonical_doc
from proto_store import MemoryStore, Queue

S = Schema(json.loads((HERE / "p2-gate.schema.json").read_text()))
FX = json.loads((HERE / "fixture-directed.khg.json").read_text())
HIF = json.loads((HERE / "hif_schema_v0.1.0.json").read_text())
PROF = json.loads((HERE / "khg-hif-1.0.0.schema.json").read_text())
REC = json.loads((HERE / "khg-record-1.0.0.schema.json").read_text())
reg = Registry().with_resource(HIF["$id"], Resource.from_contents(HIF))
ok = lambda s, x: not list(jsonschema.Draft7Validator(s, registry=reg).iter_errors(x))
ticks = itertools.count(1)
clock = lambda: f"2026-10-01T00:00:{next(ticks):02d}Z"
rec = lambda i: copy.deepcopy(next(r for r in FX["records"] if r["id"] == i))

print("== smoke test: queue -> structural lint -> store -> export")
store, q = MemoryStore(S, clock), Queue(S, clock)
base = [r for r in FX["records"] if r["id"] not in ("f:king-14",)]
# the superseded pair enters as history: v1 asserted, then v2 superseded together with its supersession record
kr = rec("f:born-skłodowska-kraków"); kr1 = dict(kr, status="asserted"); kr1.pop("status_ref"); kr1.pop("version")
store.put([r for r in base if r["id"] not in ("f:born-skłodowska-kraków", "m:sup-1", "f:born-skłodowska-warszawa")] + [kr1])
kr2 = dict(kr); kr2.pop("version")
store.put([rec("f:born-skłodowska-warszawa"), rec("m:sup-1"), kr2])
cand = rec("f:king-14"); cand["status"] = "candidate"
item = q.submit(cand, {"run_id": "smoke-1", "order_id": "o1", "position": 0, "seed": 0,
                       "extractor": {"name": "p2-fixture-extractor", "version": "0.0.1"},
                       "doc": {"doc_id": "doc:louis-bio"}})
e1 = q.lint(item["item_id"], [r for r in FX["records"] if r["kind"] == "entity"])
print("   lint:", e1["state_after"], e1["outcome"], [f["rule_id"] for f in e1["findings"]])
e2 = q.accept(item["item_id"], store, {"type": "person", "id": "curator:smoke", "version": None})
print("   accept:", e2["state_after"], e2.get("result"))
exp = store.export("khg-json")
hif = store.export("hif")
print("   export khg-json valid:", ok(REC, exp), "| export HIF valid (vendored, profile):", ok(HIF, hif), ok(PROF, hif))
fx = canonical_doc(FX, S)
strip = lambda d: [{k: v for k, v in r.items() if k not in ("version", "recorded_at")} for r in d["records"]]
print("   exported records == fixture records (ignoring store-assigned version/recorded_at):", cjson(strip(exp)) == cjson(strip(fx)))
print("   action log:", [(e["log_id"], e["action"], e["state_before"], e["state_after"], e["actor"]["type"]) for e in q.log])

print("== scenarios")
def expect(name, f, want):
    try:
        got = f()
    except KHGError as ex:
        got = ex.code
    print(f"   {'PASS' if got == want else 'FAIL'} {name}: got {got!r}" + ("" if got == want else f", want {want!r}"))

t1 = "2026-10-01T00:00:03Z"  # after the first batch (ticks 1..), before the supersession batch
expect("S-ASAT-01 as-at before the supersession sees the old belief", lambda: store.get("f:born-skłodowska-kraków", as_at="2026-10-01T00:00:01Z")["status"], "asserted")
expect("S-ASAT-02 as-at now sees the revision", lambda: store.get("f:born-skłodowska-kraków")["status"], "superseded")
expect("S-WALK-01 forward walk", lambda: store.supersession_walk("f:born-skłodowska-kraków"),
       [{"from": "f:born-skłodowska-kraków", "via": "m:sup-1", "reason": "correction", "to": ["f:born-skłodowska-warszawa"]}])
expect("S-WALK-02 backward walk", lambda: [s["to"] for s in store.supersession_walk("f:born-skłodowska-warszawa", direction="backward")], [["f:born-skłodowska-kraków"]])
expect("S-KEY-01 key timeline ordered by start", lambda: [r["id"] for r in store.by_key("position_held", [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}])], ["f:king-13", "f:king-14"])
expect("S-KEY-02 by_key as of 1650-01-01", lambda: [r["id"] for r in store.by_key("position_held", [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}], valid_at="+1650-01-01T00:00:00Z")], ["f:king-14"])
bad = rec("f:king-14"); bad["id"] = "f:king-14b"; bad["bindings"][2]["value"]["literal"]["time"] = "+1640-01-01T00:00:00Z"
expect("S-KEY-03 overlapping put is refused atomically", lambda: store.put([bad]), "KHG-D016")
expect("S-KEY-04 refused put wrote nothing", lambda: store.get("f:king-14b"), None)
k13 = store.get("f:king-13"); k13x = copy.deepcopy(k13); k13x["bindings"][0]["value"] = {"entity": "ex:LouisXIV"}
expect("S-ID-01 changing a core binding in a new version is refused", lambda: store.put([k13x]), "KHG-D013")
k13y = copy.deepcopy(k13); k13y["evidence"].append({"id": "e9", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:x"}})
expect("S-ID-02 appending evidence makes a new version", lambda: store.put([k13y])["records"][0][2], "versioned")
expect("S-ID-03 identical put is a no-op", lambda: store.put([k13y])["records"][0][2], "noop")
c = rec("f:reg-1"); c["id"] = "f:reg-2"; c["status"] = "candidate"
expect("S-Q-01 a candidate cannot enter the store", lambda: store.put([c]), "KHG-D017")
expect("S-INC-01 incident on TP53 (both roles, one fact)", lambda: [r["id"] for r in store.incident("ex:TP53")], ["f:reg-1"])
expect("S-INC-02 incident on TP53 as target", lambda: [r["id"] for r in store.incident("ex:TP53", role="target")], ["f:reg-1"])
expect("S-INC-03 default status filter hides superseded and quoted", lambda: [r["id"] for r in store.incident("ex:Maria_Skłodowska")], ["f:born-skłodowska-warszawa"])
expect("S-INC-04 incident on a fact (nesting)", lambda: [r["id"] for r in store.incident("f:born-louis14-paris")], ["f:claim-1"])
expect("S-FIND-01 at_least with a repeated role", lambda: [r["id"] for r in store.find("co_administration_causes", [{"role": "agent", "value": {"entity": "ex:metformin"}}, {"role": "agent", "value": {"entity": "ex:insulin"}}])], ["f:coadmin-1"])
expect("S-FIND-02 exact rejects a partial pattern", lambda: [r["id"] for r in store.find("co_administration_causes", [{"role": "agent", "value": {"entity": "ex:metformin"}}], match="exact")], [])

print("== C3 records: khg-queue/1.0.0 under jsonschema and fastjsonschema, and the fold over the log")
import fastjsonschema
from khg_proto import event_hash
from proto_store import fold_check
QS = json.loads((HERE / "khg-queue-1.0.0.schema.json").read_text())
fq = fastjsonschema.compile(QS)
def both(x):
    try:
        fq(x); fj = True
    except fastjsonschema.JsonSchemaException:
        fj = False
    return jsonschema.Draft7Validator(QS).is_valid(x) and fj
e2 = next(e for e in item["payload"]["evidence"] if e["id"] == "e2")
verdict = {"kind": "verdict", "verdict_id": "v-000001", "item_id": item["item_id"], "evidence_id": "e2",
           "content_key": item["keys"]["content_key"], "event_hash": event_hash(item["keys"]["content_key"], e2),
           "label": "correct", "bindings": [{"bid": "b1", "label": "correct"}, {"bid": "b5", "label": "correct"}],
           "curator": {"type": "person", "id": "curator:smoke"}, "at": "2026-10-01T00:01:00Z"}
expect("S-Q-02 queue item, 3 log entries and a verdict are valid under both validators",
       lambda: all(both(x) for x in [item] + q.log + [verdict]), True)
expect("S-Q-03 the log folds without a Q005/Q007", lambda: fold_check(q.items, q.log), [])
expect("S-Q-04 the verdict's keys equal the design's example (§7.3)", lambda: (verdict["content_key"], verdict["event_hash"]),
       ("sha256:187ca682671fd4daaa6944fced4e05b7b9198b6bf0b4c29e6bb402d61bf9ecd2",
        "sha256:852ea9ca3abcc722e33e903dcdab88f5895cef077241fdf339ee1db0aeb55524"))
json.dump({"item": item, "log": q.log, "verdict": verdict}, open(HERE / "queue-examples.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
