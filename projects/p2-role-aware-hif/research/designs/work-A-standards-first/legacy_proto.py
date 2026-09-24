"""Prototype of legacy import (foreign HIF without the declaration) for design A, run over R03's library
cases. Run with venv-hif. For each case: strict parse -> vendored HIF schema -> legacy_import ->
C1 schema -> semantic checks against the inferred schema -> export to the profile -> profile schema,
then compare the multiset of (edge, node, role, direction) records with the input (ids as strings).
"""
import collections
import copy
import json
import os
import sys

import jsonschema
from referencing import Registry, Resource

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proto  # noqa: E402
import semantic_proto  # noqa: E402

PROBES = "/home/user/knowledge-Hyper-Graphs-/projects/p2-role-aware-hif/research/probes"
HIF = json.load(open(os.path.join(PROBES, "hif-schema", "hif_schema_v0.1.0.json")))
REG = Registry().with_resource(HIF["$id"], Resource.from_contents(HIF))
SC = {n: json.load(open(os.path.join(HERE, "schemas", n))) for n in os.listdir(os.path.join(HERE, "schemas"))}
BUILTIN = json.load(open(os.path.join(HERE, "builtin.schema.json")))
RESERVED_EDGE = set(proto.EDGE_FIELDS)
RESERVED_BIND = {"role", "position", "evidence"}
RESERVED_NODE = {"types", "label", "literal", "special", "edge"}


class LegacyError(ValueError):
    pass


def sid(x, seen, kind):
    """String ids (F10): integers become their decimal string; 1 and '1' in one namespace collide."""
    if isinstance(x, bool) or not isinstance(x, (str, int)):
        raise LegacyError(f"KHG-P003 {kind} id {x!r}")
    s = str(x)
    other = seen.setdefault(s, type(x))
    if other is not type(x):
        raise LegacyError(f"KHG-P003 {kind} ids {s!r} and {int(s)!r} collide after conversion to strings")
    if s.startswith("_:") or not s:
        raise LegacyError(f"KHG-P003 reserved or empty {kind} id {s!r}")
    return s


def _split(attrs, reserved):
    a, clash = dict(attrs or {}), sorted(set(attrs or {}) & reserved)
    return a, clash


def legacy_import(h, source):
    nt = h.get("network-type", "undirected")
    if nt == "asc":
        raise LegacyError("KHG-P006 network-type asc is not a knowledge hypergraph")
    if nt == "directed" and any(i.get("direction") not in ("head", "tail") for i in h["incidences"]):
        raise LegacyError("KHG-P005 directed file with an incidence lacking direction")
    report, nseen, eseen = collections.Counter(), {}, {}
    nodes, edges = {}, {}
    for n in h.get("nodes", []):
        i = sid(n["node"], nseen, "node")
        a, clash = _split(n.get("attrs"), RESERVED_NODE - {"label"})
        r = {"node": i}
        t = a.pop("type", None)
        if isinstance(t, str):
            r["types"] = [t]
        elif t is not None:
            a["type"] = t
        if isinstance(a.get("label"), str):
            r["label"] = a.pop("label")
        for k in clash:
            a[k + "@hif"] = a.pop(k)
            report["renamed-node-attr"] += 1
        if a:
            r["attrs"] = a
        if "weight" in n:
            r["weight"] = n["weight"]
        if i in nodes:
            raise LegacyError(f"KHG-P011 node {i} declared twice")
        nodes[i] = r
    for e in h.get("edges", []):
        i = sid(e["edge"], eseen, "edge")
        if i in edges:
            raise LegacyError(f"KHG-P011 edge {i} declared twice")
        a = dict(e.get("attrs") or {})
        rel = a.pop("relation", None)
        if not isinstance(rel, str):
            rel = "untyped"
            report["untyped-edge"] += 1
        r = {"edge": i, "relation": rel, "status": "asserted", "bindings": [],
             "evidence": [{"id": "import", "type": "imported", "source": source}]}
        for k in sorted(set(a) & RESERVED_EDGE):
            a[k + "@hif"] = a.pop(k)
            report["renamed-edge-attr"] += 1
        if a:
            r["attrs"] = a
        if "weight" in e:
            r["weight"] = e["weight"]
        edges[i] = r
    seen_inc = set()
    for inc in h["incidences"]:
        ei, ni = sid(inc["edge"], eseen, "edge"), sid(inc["node"], nseen, "node")
        if ei not in edges:
            edges[ei] = {"edge": ei, "relation": "untyped", "status": "asserted", "bindings": [],
                         "evidence": [{"id": "import", "type": "imported", "source": source}]}
            report["undeclared-edge"] += 1
        a = dict(inc.get("attrs") or {})
        roles = a.pop("role", None)
        if roles is None:
            roles = ["member"]
            report["unlabelled-incidence"] += 1
        elif isinstance(roles, str):
            roles = [roles]
        elif isinstance(roles, list) and roles and all(isinstance(x, str) for x in roles):
            report["list-valued-role"] += 1
        else:
            raise LegacyError(f"KHG-P004 role {roles!r}")
        for k in sorted(set(a) & RESERVED_BIND):
            a[k + "@hif"] = a.pop(k)
            report["renamed-incidence-attr"] += 1
        for ro in roles:
            b = {"role": ro, "node": ni}
            if "direction" in inc:
                b["direction"] = inc["direction"]
            if a:
                b["attrs"] = copy.deepcopy(a)
            if "weight" in inc:
                b["weight"] = inc["weight"]
            k = (ei, ni, ro, inc.get("direction"))
            if k in seen_inc:
                raise LegacyError(f"KHG-P013 duplicate incidence {k}")
            seen_inc.add(k)
            edges[ei]["bindings"].append(b)
    empty = [k for k, v in edges.items() if not v["bindings"]]
    for k in empty:   # C1 edges need >= 1 binding; empty HIF edges are reported, not imported
        del edges[k]
        report["empty-edge-dropped"] += 1
    meta = {k: v for k, v in (h.get("metadata") or {}).items() if not k.startswith(("khg-", "hif-schema")) and
            k not in ("role-convention",)}
    if "default_attrs" in meta:   # HyperNetX interprets it and invents values (R03 row 23): renamed
        meta["default_attrs@hif"] = meta.pop("default_attrs")
        report["renamed-metadata-key"] += 1
    meta.update({"khg-profile": "1.0.0", "khg-schema": "legacy-inferred/0.1.0"})
    doc = {"metadata": meta, "nodes": list(nodes.values()), "edges": list(edges.values())}
    return doc, infer(doc), dict(report)


def infer(doc):
    ntypes = {n["node"]: n.get("types", []) for n in doc["nodes"]}
    rels, types = {}, set()
    for e in doc["edges"]:
        rr = rels.setdefault(e["relation"], {"roles": {}})
        cnt = collections.Counter(b["role"] for b in e["bindings"])
        for b in e["bindings"]:
            u = rr["roles"].setdefault(b["role"], {"slot": "core", "types": ["Thing"], "max": 1, "_dirs": set()})
            u["_dirs"].add(b.get("direction"))
            for t in ntypes.get(b["node"], []):
                types.add(t)
                if t not in u["types"]:
                    u["types"].append(t)
        for ro, c in cnt.items():
            if c > 1:
                rr["roles"][ro]["max"] = None
    for rr in rels.values():
        for u in rr["roles"].values():
            d = u.pop("_dirs")
            if len(d) == 1 and None not in d:
                u["direction"] = d.pop()
            u["types"] = sorted(u["types"])
    # every node also gets type Thing, so an untyped node always conforms
    for n in doc["nodes"]:
        n["types"] = sorted(set(n.get("types", [])) | {"Thing"})
    return {"khg-schema": "legacy-inferred/0.1.0", "khg-profile": "1.0.0", "label": "inferred on import",
            "types": {t: {"label": t} for t in sorted(types | {"Thing"})},
            "roles": {ro: {"label": ro} for ro in sorted({ro for r in rels.values() for ro in r["roles"]})},
            "relations": dict(sorted(rels.items()))}


def triples(h):
    out = collections.Counter()
    for i in h["incidences"]:
        rs = (i.get("attrs") or {}).get("role", "member")
        for r in ([rs] if isinstance(rs, str) else rs):
            out[(str(i["edge"]), str(i["node"]), r, i.get("direction"))] += 1
    return out


if __name__ == "__main__":
    idx = json.load(open(os.path.join(PROBES, "lib-cases", "INDEX.json")))
    names = ["/home/user/knowledge-Hyper-Graphs-/schemas/sample.hif.json"] + \
        [os.path.join(PROBES, "lib-cases", f) for f in sorted(os.listdir(os.path.join(PROBES, "lib-cases")))
         if f.endswith(".hif.json")]
    vh = jsonschema.Draft7Validator(HIF)
    vc = jsonschema.Draft7Validator(SC["khg-document-1.0.0.json"])
    vp = jsonschema.Draft7Validator(SC["khg-hif-profile-1.0.0.json"], registry=REG)
    ok = 0
    for p in names:
        name = os.path.basename(p).replace(".hif.json", "")
        try:
            h = proto.strict_loads(open(p, encoding="utf-8").read())
        except proto.StrictJSONError as e:
            print(f"  {name:45} rejected J: {str(e)[:60]}")
            continue
        if list(vh.iter_errors(h)):
            print(f"  {name:45} rejected H")
            continue
        try:
            doc, sch, rep = legacy_import(h, "file:" + name)
        except LegacyError as e:
            print(f"  {name:45} rejected {str(e)[:90]}")
            continue
        schema = proto.Schema(BUILTIN, sch)
        cerr = [x.message for x in vc.iter_errors(doc)]
        serr = [x[0] for x in semantic_proto.validate(doc, schema)]
        out = proto.to_hif(doc, schema)
        perr = [x.message for x in vp.iter_errors(out)]
        same = triples(h) == triples(out)
        ok += same and not (cerr or serr or perr)
        print(f"  {name:45} imported: C1 {'ok' if not cerr else cerr[:1]} S {serr[:2] or 'ok'} "
              f"profile {'ok' if not perr else perr[:1]} role-records kept={same} {rep or ''}")
    print("imported with every (edge, node, role, direction) record kept:", ok)
