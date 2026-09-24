"""Prototype of migrate 0 -> 1.0.0 for the KB's pre-1.0 dialect (schemas/sample.hif.json).

Pre-1.0 dialect: HIF with incidences[].attrs.role (single string), edges[].attrs.relation/source/
valid-from/arity, confidence in edges[].weight, metadata.schema = moving 'latest' URL, metadata.conventions.
Rules (each one listed in the design, section 11):
  R1 attrs.role (string) -> binding role (unchanged key in HIF)
  R2 edges[].attrs.relation -> relation; attrs.arity dropped (derived, never stored)
  R3 edges[].attrs.source -> evidence {id: e1, type: curated, source}
  R4 edges[].weight -> evidence e1 confidence {value, scale: score, min: 0, max: 1}; weight not kept
  R5 edges[].attrs.valid-from -> valid.from
  R6 nodes[].attrs.type (string) -> types [type]; attrs.label -> label
  R7 status := asserted; direction kept per binding
  R8 metadata: title/description/created/kb-section kept; schema and conventions dropped (superseded by
     the declaration); khg-profile, khg-schema added
  R9 a relation-type schema is inferred from the data (observed types, max, direction; all core)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proto  # noqa: E402

SAMPLE = "/home/user/knowledge-Hyper-Graphs-/schemas/sample.hif.json"


def infer_schema(c1, schema_id):
    types = {t for n in c1.get("nodes", []) for t in n.get("types", [])}
    ntypes = {n["node"]: n.get("types", []) for n in c1.get("nodes", [])}
    rels = {}
    for e in c1["edges"]:
        r = rels.setdefault(e["relation"], {"roles": {}})
        counts = {}
        for b in e["bindings"]:
            counts[b["role"]] = counts.get(b["role"], 0) + 1
            u = r["roles"].setdefault(b["role"], {"slot": "core", "types": [], "max": 1, "direction": b["direction"]})
            for t in ntypes.get(b["node"], []):
                if t not in u["types"]:
                    u["types"].append(t)
        for role, c in counts.items():
            if c > 1:
                r["roles"][role]["max"] = None
    for r in rels.values():
        for u in r["roles"].values():
            u["types"].sort()
    return {"khg-schema": schema_id, "khg-profile": "1.0.0", "label": "inferred from schemas/sample.hif.json",
            "types": {t: {"label": t} for t in sorted(types)},
            "roles": {ro: {"label": ro} for ro in sorted({ro for r in rels.values() for ro in r["roles"]})},
            "relations": dict(sorted(rels.items()))}


def migrate(hif):
    meta = {k: v for k, v in hif.get("metadata", {}).items() if k not in ("schema", "conventions")}
    meta.update({"khg-profile": "1.0.0", "khg-schema": "kb-sample/1.0.0"})
    nodes = []
    for n in hif.get("nodes", []):
        a = dict(n.get("attrs", {}))
        r = {"node": n["node"]}
        if "type" in a:
            r["types"] = [a.pop("type")]
        if "label" in a:
            r["label"] = a.pop("label")
        if a:
            r["attrs"] = a
        nodes.append(r)
    edges = []
    for er in hif["edges"]:
        a = dict(er.get("attrs", {}))
        e = {"edge": er["edge"], "relation": a.pop("relation"), "status": "asserted"}
        a.pop("arity", None)
        ev = {"id": "e1", "type": "curated"}
        if "source" in a:
            ev["source"] = a.pop("source")
        if "weight" in er:
            ev["confidence"] = {"value": er["weight"], "scale": "score", "min": 0, "max": 1}
        if "valid-from" in a:
            e["valid"] = {"from": a.pop("valid-from")}
        e["evidence"] = [ev]
        if a:
            e["attrs"] = a
        e["bindings"] = [{"role": i["attrs"]["role"], "node": i["node"], "direction": i["direction"]}
                         for i in hif["incidences"] if i["edge"] == er["edge"]]
        edges.append(e)
    return {"metadata": meta, "nodes": nodes, "edges": edges}


if __name__ == "__main__":
    src = proto.strict_loads(open(SAMPLE, encoding="utf-8").read())
    c1 = migrate(src)
    sch = infer_schema(c1, "kb-sample/1.0.0")
    schema = proto.Schema(json.load(open(os.path.join(HERE, "builtin.schema.json"))), sch)
    c1 = proto.canonical_doc(c1, schema)
    out_hif = proto.to_hif(c1, schema)
    for name, obj in (("sample-migrated.khg.json", c1), ("sample-migrated.schema.json", sch),
                      ("sample-migrated.hif.json", out_hif)):
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")
    assert proto.from_hif(out_hif, schema) == c1
    print("migrated:", len(c1["nodes"]), "nodes,", len(c1["edges"]), "edges; arity f2 =",
          proto.arity([e for e in c1["edges"] if e["edge"] == "f2"][0], schema))
    print("role keys unchanged in HIF:", sorted({i["attrs"]["role"] for i in out_hif["incidences"]}) ==
          sorted({i["attrs"]["role"] for i in src["incidences"]}))
