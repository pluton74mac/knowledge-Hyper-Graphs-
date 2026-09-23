"""Every valid artefact validates under fastjsonschema too (F5); the vendored HIF schema is resolved offline."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fastjsonschema, c1
L = lambda p: json.load(open(p, encoding="utf-8"))
H = L("/home/user/knowledge-Hyper-Graphs-/projects/p2-role-aware-hif/research/probes/hif-schema/hif_schema_v0.1.0.json")
vr, vm = fastjsonschema.compile(L("khg-record-1.0.0.schema.json")), fastjsonschema.compile(L("khg-relation-schema-1.0.0.schema.json"))
vq = fastjsonschema.compile(L("khg-queue-1.0.0.schema.json"))
vp = fastjsonschema.compile(L("khg-hif-1.0.0.schema.json"), handlers={"https": lambda uri: H})
bad = 0
for f in ("gate.khg.jsonl", "sample-migrated.khg.jsonl"):
    for r in c1.load_jsonl(f):
        try: (vm if r["kind"] == "relation-schema" else vr)(r)
        except fastjsonschema.JsonSchemaException as e: bad += 1; print(f, r.get("id"), e.message)
for r in c1.load_jsonl("smoke.queue.jsonl"):
    try: vq(r)
    except fastjsonschema.JsonSchemaException as e: bad += 1; print("queue", e.message)
for f in ("gate-full.hif.json", "gate-directed.hif.json", "sample-migrated.hif.json"):
    try: vp(L(f))
    except fastjsonschema.JsonSchemaException as e: bad += 1; print(f, e.message)
print("fastjsonschema failures on valid artefacts:", bad)
