"""Prototype of `khg-migrate legacy-hif` on schemas/sample.hif.json (design C, section 11).

Foreign/legacy HIF -> C1 1.0.0 container. The operator supplies a small mapping (slot classes, id namespace,
what edge attrs mean); nothing is guessed silently, and every dropped item is reported.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c1  # noqa: E402
import hif_codec  # noqa: E402

SAMPLE = "/home/user/knowledge-Hyper-Graphs-/schemas/sample.hif.json"
MAPPING = {
    "schema_id": "kb-sample", "schema_version": "1.0.0",
    "edge_namespace": "kb-sample",            # foreign edge ids f1.. are not C1 ids
    "slots": {"treatment": "core", "condition": "core", "dosage": "qualifier", "population": "qualifier",
              "agent": "core", "effect": "core", "publisher": "core", "publication": "core"},
    "edge_attrs": {"relation": "relation", "arity": "check-and-drop", "source": "evidence.source.doc",
                   "valid-from": "valid_time.from"},
    "weight": "drop",                         # or {"as_confidence": "probability"} when the operator says so
    "evidence_default": {"type": "curated", "mode": "manual", "activity": {"agent": "kb-author"}},
}


def migrate(doc, m, weight_as_confidence=None):
    report = {"dropped": [], "checked": []}
    rel_usage = {}
    for i in doc["incidences"]:
        e = next(x for x in doc["edges"] if x["edge"] == i["edge"])
        rel = e["attrs"]["relation"]
        role = i["attrs"]["role"]
        u = rel_usage.setdefault(rel, {}).setdefault(role, {"n": {}, "dir": set()})
        u["n"][i["edge"]] = u["n"].get(i["edge"], 0) + 1
        u["dir"].add(i.get("direction"))
    types = sorted({n["attrs"]["type"] for n in doc["nodes"]})
    node_type = {n["node"]: n["attrs"]["type"] for n in doc["nodes"]}
    relations = []
    for rel, roles in sorted(rel_usage.items()):
        usages = []
        for role, u in sorted(roles.items()):
            fillers = sorted({node_type[i["node"]] for i in doc["incidences"]
                              if i["attrs"]["role"] == role})
            usage = {"role": role, "slot": m["slots"][role], "fillers": {"entity_types": fillers},
                     "min": 1, "max": max(u["n"].values())}
            (d,) = u["dir"]  # the sample is consistent: one direction per role usage
            if d:
                usage["direction"] = d
            usages.append(usage)
        relations.append({"id": rel, "label": rel.replace("-", " "), "kind": "fact", "roles": usages})
    schema = {"kind": "relation-schema", "format": c1.SCHEMA_FORMAT, "id": m["schema_id"],
              "version": m["schema_version"], "label": "migrated from schemas/sample.hif.json",
              "entity_types": [{"id": t, "label": t} for t in types],
              "roles": [{"id": r, "label": r} for r in sorted(m["slots"])],
              "relations": relations}
    if weight_as_confidence:
        schema["confidence_scales"] = [{"id": weight_as_confidence, "kind": "probability", "min": 0, "max": 1}]
    S = c1.Schema(schema)
    entities = [{"kind": "entity", "id": n["node"], "types": [n["attrs"]["type"]], "label": n["attrs"]["label"]}
                for n in doc["nodes"]]
    hyperedges = []
    for e in doc["edges"]:
        a = e["attrs"]
        hid = f"{m['edge_namespace']}:{e['edge']}"
        bs = []
        for k, i in enumerate([i for i in doc["incidences"] if i["edge"] == e["edge"]], 1):
            bs.append({"bid": f"b{k}", "role": i["attrs"]["role"], "value": {"entity": i["node"]}})
        r = {"kind": "hyperedge", "id": hid, "version": 1, "recorded_at": "2026-09-19T00:00:00Z",
             "recorded_by": "khg-migrate/1.0.0", "change": {"op": "put", "reason": "migrated from legacy HIF"},
             "relation": a["relation"], "status": "asserted", "bindings": bs,
             "evidence": [{"eid": "ev1", **m["evidence_default"], "source": {"doc": a["source"]}}]}
        if "valid-from" in a:
            r["valid_time"] = {"from": a["valid-from"]}
        if "weight" in e:
            if weight_as_confidence:
                r["confidence"] = {"value": e["weight"], "scale": weight_as_confidence}
            else:
                report["dropped"].append({"edge": e["edge"], "weight": e["weight"],
                                          "why": "HIF weight has no defined meaning; pass --weight-as-confidence"})
        r = c1.normalise(r, S)
        if "arity" in a:
            report["checked"].append({"edge": e["edge"], "legacy_arity": a["arity"], "c1_arity": r["arity"]["arity"],
                                      "agree": a["arity"] == r["arity"]["arity"]})
        hyperedges.append(r)
    header = {"kind": "header", "format": c1.RECORD_FORMAT, "content": "snapshot", "created_by": "khg-migrate/1.0.0",
              "title": doc["metadata"]["title"], "description": doc["metadata"]["description"],
              "schemas": [{"id": schema["id"], "version": schema["version"], "sha256": c1.sha256_hex(schema)}]}
    recs = hif_codec.canonical_container([header, schema] + entities + hyperedges)
    return recs, report


if __name__ == "__main__":
    with open(SAMPLE, encoding="utf-8") as f:
        doc = json.load(f)
    recs, report = migrate(doc, MAPPING)
    c1.dump_jsonl(recs, os.path.join(HERE, "sample-migrated.khg.jsonl"))
    recs2, report2 = migrate(doc, MAPPING, weight_as_confidence="probability")
    hif = hif_codec.to_hif(recs)
    with open(os.path.join(HERE, "sample-migrated.hif.json"), "w", encoding="utf-8") as f:
        json.dump(hif, f, ensure_ascii=False, indent=1)
    back = hif_codec.from_hif(hif)
    print(json.dumps({"report_default": report, "confidences_with_flag": [r.get("confidence") for r in recs2 if r["kind"] == "hyperedge"],
                      "network-type": hif["network-type"], "roundtrip_equal": c1.cjson(back) == c1.cjson(recs),
                      "n_records": len(recs)}, indent=1))
