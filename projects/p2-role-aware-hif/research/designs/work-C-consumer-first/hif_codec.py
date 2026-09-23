"""C1 container <-> role-aware HIF (khg-hif profile 1.0.0). Prototype for design C, section 4.

Mapping in one paragraph:
  * one HIF edge per hyperedge (and per supersession record); C1 field f (other than kind, id, relation,
    bindings) -> edges[].attrs["khg-" + dash(f)]; relation -> attrs["relation"]; kind -> attrs["khg-kind"].
  * one HIF incidence per binding whose value is an entity, a literal or a hyperedge reference:
    {"edge": id, "node": node_id(value), "direction"?: b.direction,
     "attrs": {"role": b.role, "khg-bid": b.bid, "khg-slot": b.slot, "khg-position"?: b.position}}.
    A node that plays k roles in one fact has k incidence records (repeated (edge, node) pairs).
  * bindings with a special value (somevalue, novalue, unbound) have no participant: they go, verbatim,
    to edges[].attrs["khg-special-bindings"].
  * nodes: entity records (khg-kind entity), literal nodes shared by value (id khg-lit:<sha256[:32]> of the
    canonical literal), hyperedge-reference mirror nodes (id khg-ref:<edge id>, attrs.khg-ref = edge id).
  * network-type: "directed" iff every incidence has a direction (auto), else "undirected".
  * metadata: the generic roles-convention keys + the khg-* profile keys (header and schemas verbatim).
"""
from __future__ import annotations

import copy

import c1

HIF_SCHEMA_URL = ("https://raw.githubusercontent.com/HIF-org/HIF-standard/"
                  "b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json")
HIF_SCHEMA_SHA256 = "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196"
HIF_SCHEMA_DOI = "10.5281/zenodo.17257719"
PROFILE = "khg-hif/1.0.0"
ROLES_CONVENTION = "1.0.0"
SUPERSEDES = "khg-supersedes"
PROFILE_ROLES = {"superseding": "superseding record (profile role)",
                 "superseded": "superseded record (profile role)"}


def dash(f: str) -> str:
    return "khg-" + f.replace("_", "-")


def undash(k: str) -> str:
    assert k.startswith("khg-")
    return k[4:].replace("-", "_")


def split(records):
    out = {"header": None, "schemas": [], "entity": [], "hyperedge": [], "supersession": []}
    for r in records:
        k = r["kind"]
        if k == "header":
            out["header"] = r
        elif k == "relation-schema":
            out["schemas"].append(r)
        else:
            out[k].append(r)
    return out


def node_id(v: dict) -> str:
    if "entity" in v:
        return v["entity"]
    if "literal" in v:
        return c1.literal_node_id(v)
    if "hyperedge" in v:
        return "khg-ref:" + v["hyperedge"]
    raise ValueError(f"special values have no node: {v!r}")


def to_hif(records, *, network_type: str = "auto", relations=None) -> dict:
    """relations: optional set of relation ids to export (a slice); supersessions are kept when both ends are."""
    p = split(records)
    hyperedges = [h for h in p["hyperedge"] if relations is None or h["relation"] in relations]
    kept = {h["id"] for h in hyperedges}
    sups = [s for s in p["supersession"] if s["superseded"] in kept and s["superseding"] in kept]
    nodes, edges, incs = {}, [], []
    for e in p["entity"]:
        a = {"khg-kind": "entity", "label": e["label"]}
        for f, v in e.items():
            if f not in ("kind", "id", "label"):
                a[dash(f)] = copy.deepcopy(v)
        nodes[e["id"]] = {"node": e["id"], "attrs": a}

    def ensure(v):
        n = node_id(v)
        if n not in nodes:
            if "literal" in v:
                nodes[n] = {"node": n, "attrs": {"khg-kind": "literal", "label": v["literal"],
                                                 "khg-literal": copy.deepcopy(v)}}
            elif "hyperedge" in v:
                nodes[n] = {"node": n, "attrs": {"khg-kind": "hyperedge-ref", "khg-ref": v["hyperedge"]}}
            else:
                raise ValueError(f"entity {n} has no entity record")
        return n

    for h in hyperedges:
        a = {"relation": h["relation"], "khg-kind": "hyperedge"}
        for f, v in h.items():
            if f not in ("kind", "id", "relation", "bindings"):
                a[dash(f)] = copy.deepcopy(v)
        special = [copy.deepcopy(b) for b in h["bindings"] if "special" in b["value"]]
        if special:
            a["khg-special-bindings"] = special
        edges.append({"edge": h["id"], "attrs": a})
        for b in h["bindings"]:
            if "special" in b["value"]:
                continue
            inc = {"edge": h["id"], "node": ensure(b["value"])}
            if "direction" in b:
                inc["direction"] = b["direction"]
            inc["attrs"] = {"role": b["role"], "khg-bid": b["bid"], "khg-slot": b["slot"]}
            if b.get("position") is not None:
                inc["attrs"]["khg-position"] = b["position"]
            incs.append(inc)
    for s in sups:
        a = {"relation": SUPERSEDES, "khg-kind": "supersession"}
        for f, v in s.items():
            if f not in ("kind", "id", "superseded", "superseding"):
                a[dash(f)] = copy.deepcopy(v)
        edges.append({"edge": s["id"], "attrs": a})
        incs.append({"edge": s["id"], "node": ensure({"hyperedge": s["superseding"]}), "direction": "tail",
                     "attrs": {"role": "superseding"}})
        incs.append({"edge": s["id"], "node": ensure({"hyperedge": s["superseded"]}), "direction": "head",
                     "attrs": {"role": "superseded"}})
    all_dir = all("direction" in i for i in incs)
    nt = ("directed" if all_dir else "undirected") if network_type == "auto" else network_type
    if nt == "directed" and not all_dir:
        raise ValueError("network_type='directed' but some incidences have no direction")
    vocab = {}
    for s in p["schemas"]:
        for r in s["roles"]:
            vocab[r["id"]] = {"label": r["label"]}
    for r, l in PROFILE_ROLES.items():
        vocab[r] = {"label": l}
    used = {i["attrs"]["role"] for i in incs} | {b["role"] for h in hyperedges for b in h["bindings"]}
    vocab = {k: vocab[k] for k in sorted(vocab) if k in used}
    meta = {"roles-convention": ROLES_CONVENTION, "roles-vocabulary": vocab,
            "hif-schema": HIF_SCHEMA_URL, "hif-schema-sha256": HIF_SCHEMA_SHA256, "hif-schema-doi": HIF_SCHEMA_DOI,
            "khg-profile": PROFILE, "khg-header": copy.deepcopy(p["header"]),
            "khg-schemas": copy.deepcopy(p["schemas"])}
    if relations is not None:
        meta["khg-slice"] = {"relations": sorted(relations)}
    doc = {"network-type": nt, "metadata": meta,
           "nodes": [nodes[k] for k in sorted(nodes)],
           "edges": sorted(edges, key=lambda e: e["edge"]),
           "incidences": sorted(incs, key=inc_key)}
    return doc


def inc_key(i):
    a = i.get("attrs", {})
    return (i["edge"], a.get("khg-bid", ""), a.get("role", ""), i["node"], i.get("direction", ""))


def canonical_hif(doc: dict) -> dict:
    d = copy.deepcopy(doc)
    d["nodes"] = sorted(d.get("nodes", []), key=lambda n: n["node"])
    d["edges"] = sorted(d.get("edges", []), key=lambda e: e["edge"])
    d["incidences"] = sorted(d.get("incidences", []), key=inc_key)
    return d


class ImportError_(ValueError):
    pass


def from_hif(doc: dict) -> list:
    """Profile file -> C1 container records (canonical order). Raises on any profile inconsistency."""
    meta = doc["metadata"]
    if meta.get("khg-profile") != PROFILE:
        raise ImportError_("not a khg-hif/1.0.0 file (use the foreign importer)")
    nodes = {}
    for n in doc.get("nodes", []):
        if n["node"] in nodes:
            raise ImportError_(f"P-DUP-NODE {n['node']}")
        nodes[n["node"]] = n
    edges = {}
    for e in doc.get("edges", []):
        if e["edge"] in edges:
            raise ImportError_(f"P-DUP-EDGE {e['edge']}")
        edges[e["edge"]] = e
    by_edge = {}
    for i in doc["incidences"]:
        if i["edge"] not in edges:
            raise ImportError_(f"P-UNDECLARED-EDGE {i['edge']}")
        if i["node"] not in nodes:
            raise ImportError_(f"P-UNDECLARED-NODE {i['node']}")
        if doc.get("network-type") == "directed" and "direction" not in i:
            raise ImportError_("P-DIRECTED-NO-DIRECTION")
        by_edge.setdefault(i["edge"], []).append(i)

    def value_of(nid):
        a = nodes[nid]["attrs"]
        k = a["khg-kind"]
        if k == "entity":
            return {"entity": nid}
        if k == "literal":
            if c1.literal_node_id(a["khg-literal"]) != nid:
                raise ImportError_(f"P-LITERAL-ID {nid}")
            return copy.deepcopy(a["khg-literal"])
        if k == "hyperedge-ref":
            if a["khg-ref"] not in edges or nid != "khg-ref:" + a["khg-ref"]:
                raise ImportError_(f"P-REF-DANGLING {nid}")
            return {"hyperedge": a["khg-ref"]}
        raise ImportError_(f"P-NODE-KIND {nid}")

    records = [copy.deepcopy(meta["khg-header"])] + copy.deepcopy(meta["khg-schemas"])
    for nid, n in nodes.items():
        a = n["attrs"]
        if a["khg-kind"] == "entity":
            r = {"kind": "entity", "id": nid, "label": a["label"]}
            for k, v in a.items():
                if k.startswith("khg-") and k != "khg-kind":
                    r[undash(k)] = copy.deepcopy(v)
            records.append(r)
    for eid, e in edges.items():
        a = e["attrs"]
        if a["khg-kind"] == "hyperedge":
            r = {"kind": "hyperedge", "id": eid, "relation": a["relation"]}
            for k, v in a.items():
                if k.startswith("khg-") and k not in ("khg-kind", "khg-special-bindings"):
                    r[undash(k)] = copy.deepcopy(v)
            bs = copy.deepcopy(a.get("khg-special-bindings", []))
            seen = set()
            for i in by_edge.get(eid, []):
                ia = i["attrs"]
                if ia["khg-bid"] in seen:
                    raise ImportError_(f"P-DUP-BID {eid} {ia['khg-bid']}")
                seen.add(ia["khg-bid"])
                b = {"bid": ia["khg-bid"], "role": ia["role"], "slot": ia["khg-slot"], "value": value_of(i["node"])}
                if "khg-position" in ia:
                    b["position"] = ia["khg-position"]
                if "direction" in i:
                    b["direction"] = i["direction"]
                bs.append(b)
            r["bindings"] = sorted(bs, key=c1.binding_sort_key)
            records.append(r)
        elif a["khg-kind"] == "supersession":
            r = {"kind": "supersession", "id": eid}
            for k, v in a.items():
                if k.startswith("khg-") and k != "khg-kind":
                    r[undash(k)] = copy.deepcopy(v)
            ends = {i["attrs"]["role"]: value_of(i["node"])["hyperedge"] for i in by_edge.get(eid, [])}
            if set(ends) != {"superseding", "superseded"}:
                raise ImportError_(f"P-SUPERSESSION-ENDS {eid}")
            r["superseding"], r["superseded"] = ends["superseding"], ends["superseded"]
            records.append(r)
        else:
            raise ImportError_(f"P-EDGE-KIND {eid}")
    return canonical_container(records)


def canonical_container(records):
    order = {"header": 0, "relation-schema": 1, "entity": 2, "hyperedge": 3, "supersession": 4}
    return sorted(records, key=lambda r: (order[r["kind"]], r.get("id", ""), r.get("version", 0)))
