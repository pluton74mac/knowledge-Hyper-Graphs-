"""Prototype of design A's C1 <-> HIF mapping (not the package). Standard library only.

C1 is "folded HIF": node and edge records keep HIF's names (node, edge, attrs, weight, direction);
each binding is one HIF incidence with its edge id removed, its role lifted out of attrs and its
value inline. to_hif() unfolds, from_hif() folds.
"""
from __future__ import annotations

import copy
import hashlib
import json
import unicodedata

HIF_PINNED = ("https://raw.githubusercontent.com/HIF-org/HIF-standard/"
              "b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json")
HIF_SHA256 = "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196"
ROLE_CONVENTION = "1.0.0"

EDGE_FIELDS = ("relation", "status", "valid", "evidence", "rank", "visibility", "recorded", "schema",
               "superseded-by")
BINDING_ATTR_FIELDS = ("role", "position", "evidence")
NODE_FIELDS = ("types", "label")
VALUE_KINDS = ("node", "literal", "edge", "special")
DERIVED_META = ("role-convention", "hif-schema", "hif-schema-sha256")


class StrictJSONError(ValueError):
    pass


def strict_loads(text: str):
    """RFC 8259 strict: no NaN/Infinity, no duplicate keys (layer J)."""
    def no_const(c):
        raise StrictJSONError(f"KHG-J003 non-standard constant {c}")

    def no_dupes(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise StrictJSONError(f"KHG-J002 duplicate key {k!r}")
            d[k] = v
        return d
    return json.loads(text, parse_constant=no_const, object_pairs_hook=no_dupes)


def jcs(x) -> bytes:
    """RFC 8785 canonical bytes. Equal to JCS for the payloads hashed here (ASCII keys, no floats)."""
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha(x) -> str:
    return "sha256:" + hashlib.sha256(jcs(x)).hexdigest()


# ------------------------------------------------------------------ schema helpers

class Schema:
    def __init__(self, *docs):
        self.relations, self.roles, self.types, self.valid_roles = {}, {}, {}, {}
        self.ids = []
        for d in docs:
            self.ids.append(d["khg-schema"])
            self.relations.update(d.get("relations", {}))
            self.roles.update(d.get("roles", {}))
            self.types.update(d.get("types", {}))
            self.valid_roles.update(d.get("valid-roles", {}))

    def usage(self, relation, role):
        return self.relations[relation]["roles"][role]

    def slot(self, relation, role):
        return self.usage(relation, role)["slot"]

    def hypergraph(self, slots=("core", "qualifier"), builtin=False):
        """P6: relation id -> frozenset of global role ids (the attributes)."""
        return {r: frozenset(ro for ro, u in rel["roles"].items() if u["slot"] in slots)
                for r, rel in sorted(self.relations.items()) if builtin or not r.startswith("khg:")}


# ------------------------------------------------------------------ values, canonical form

def value_kind(b):
    ks = [k for k in VALUE_KINDS if k in b]
    assert len(ks) == 1, b
    return ks[0]


def value_part(b):
    k = value_kind(b)
    return {k: b[k]}


def binding_sort_key(b):
    return (b["role"], b.get("position", -1), VALUE_KINDS.index(value_kind(b)),
            jcs(value_part(b)).decode("utf-8"))


def canonical_edge(e, schema: Schema | None = None):
    e = copy.deepcopy(e)
    if schema is not None:
        for b in e["bindings"]:
            d = schema.usage(e["relation"], b["role"]).get("direction")
            if d and "direction" not in b:
                b["direction"] = d
    e["bindings"] = sorted(e["bindings"], key=binding_sort_key)
    if "evidence" in e:
        e["evidence"] = sorted(e["evidence"], key=lambda ev: ev["id"])
    if e.get("rank") == "normal":
        del e["rank"]
    if e.get("visibility") == "visible":
        del e["visibility"]
    return e


def canonical_doc(doc, schema: Schema | None = None):
    doc = copy.deepcopy(doc)
    out = {"metadata": dict(sorted(doc["metadata"].items()))}
    if doc.get("nodes"):
        out["nodes"] = sorted(doc["nodes"], key=lambda n: n["node"])
    header_schema = doc["metadata"]["khg-schema"]
    edges = []
    for e in doc["edges"]:
        e = canonical_edge(e, schema)
        if e.get("schema") == header_schema:
            del e["schema"]
        edges.append(e)
    out["edges"] = sorted(edges, key=lambda e: (e["edge"], e.get("recorded", "")))
    return out


# ------------------------------------------------------------------ identity (F6) and arity

def binding_key(b, ordered):
    k = {"role": b["role"], **value_part(b)}
    if "direction" in b:
        k["direction"] = b["direction"]
    if ordered and "position" in b:
        k["position"] = b["position"]
    return k


def content_key(e, schema: Schema, scope="all"):
    """scope 'all' = core + qualifier bindings; 'core' = core bindings only; meta never counts."""
    slots = {"all": ("core", "qualifier"), "core": ("core",)}[scope]
    ks = []
    for b in e["bindings"]:
        u = schema.usage(e["relation"], b["role"])
        if u["slot"] in slots:
            ks.append(binding_key(b, u.get("ordered", False)))
    return sha({"relation": e["relation"], "bindings": sorted(ks, key=lambda k: jcs(k))})


def key_digest(e, schema: Schema):
    key = schema.relations[e["relation"]].get("key")
    if not key:
        return None
    ks = []
    for b in e["bindings"]:
        if b["role"] in key["roles"]:
            if b.get("special") in ("somevalue", "unbound"):
                return None  # an existential or open slot never collides
            ks.append(binding_key(b, schema.usage(e["relation"], b["role"]).get("ordered", False)))
    return sha({"relation": e["relation"], "key": sorted(ks, key=lambda k: jcs(k))})


def event_key(e, ev, schema: Schema):
    x = {"content": content_key(e, schema)}
    for f in ("source", "digest", "start", "end", "agent", "version", "model", "prompt"):
        if f in ev:
            x[f] = ev[f]
    return sha(x)


def arity(e, schema: Schema):
    """Bindings in core or qualifier slots whose value is a node, literal, edge or somevalue."""
    n = 0
    for b in e["bindings"]:
        if schema.slot(e["relation"], b["role"]) in ("core", "qualifier") and \
                b.get("special") not in ("novalue", "unbound"):
            n += 1
    return n


def participants(e, schema: Schema):
    vals = []
    for i, b in enumerate(e["bindings"]):
        if schema.slot(e["relation"], b["role"]) in ("core", "qualifier") and \
                b.get("special") not in ("novalue", "unbound"):
            vals.append(("some", i) if b.get("special") == "somevalue" else jcs(value_part(b)))
    return len(set(vals))


# ------------------------------------------------------------------ derived HIF node ids

def literal_node_id(lit):
    return "_:lit:" + hashlib.sha256(jcs(lit)).hexdigest()[:32]


def special_node_id(kind, role, n, edge):
    short = {"somevalue": "some", "novalue": "none", "unbound": "unbound"}[kind]
    return f"_:{short}:{role}/{n}/{edge}"


def edge_node_id(edge):
    return "_:edge:" + edge


# ------------------------------------------------------------------ C1 -> HIF (unfold)

def to_hif(doc, schema: Schema):
    doc = canonical_doc(doc, schema)
    all_dir = all("direction" in b for e in doc["edges"] for b in e["bindings"])
    meta = {k: v for k, v in doc["metadata"].items()}
    meta.update({"role-convention": ROLE_CONVENTION, "hif-schema": HIF_PINNED, "hif-schema-sha256": HIF_SHA256})
    nodes = {}
    for n in doc.get("nodes", []):
        r = {"node": n["node"]}
        attrs = {k: n[k] for k in NODE_FIELDS if k in n}
        attrs.update(n.get("attrs", {}))
        if "weight" in n:
            r["weight"] = n["weight"]
        if attrs:
            r["attrs"] = attrs
        nodes[n["node"]] = r
    edges, incidences = [], []
    for e in doc["edges"]:
        r = {"edge": e["edge"]}
        attrs = {k: e[k] for k in EDGE_FIELDS if k in e}
        attrs.update(e.get("attrs", {}))
        r["attrs"] = attrs
        if "weight" in e:
            r["weight"] = e["weight"]
        edges.append(r)
        counters = {}
        for b in e["bindings"]:
            kind = value_kind(b)
            if kind == "node":
                nid = b["node"]
            elif kind == "literal":
                nid = literal_node_id(b["literal"])
                nodes.setdefault(nid, {"node": nid, "attrs": {"literal": b["literal"]}})
            elif kind == "edge":
                nid = edge_node_id(b["edge"])
                nodes.setdefault(nid, {"node": nid, "attrs": {"edge": b["edge"]}})
            else:
                c = counters.setdefault((b["role"], b["special"]), 0)
                counters[(b["role"], b["special"])] = c + 1
                nid = special_node_id(b["special"], b["role"], c, e["edge"])
                nodes[nid] = {"node": nid, "attrs": {"special": b["special"]}}
            inc = {"edge": e["edge"], "node": nid}
            if "direction" in b:
                inc["direction"] = b["direction"]
            if "weight" in b:
                inc["weight"] = b["weight"]
            a = {"role": b["role"]}
            for k in ("position", "evidence"):
                if k in b:
                    a[k] = b[k]
            a.update(b.get("attrs", {}))
            inc["attrs"] = a
            incidences.append(inc)
    out = {"network-type": "directed" if all_dir else "undirected", "metadata": dict(sorted(meta.items()))}
    if nodes:
        out["nodes"] = [nodes[k] for k in sorted(nodes)]
    out["edges"] = edges
    out["incidences"] = incidences
    return out


# ------------------------------------------------------------------ HIF -> C1 (fold)

def from_hif(hif, schema: Schema | None = None):
    nodes = {n["node"]: n for n in hif.get("nodes", [])}
    meta = {k: v for k, v in hif["metadata"].items() if k not in DERIVED_META}
    out_nodes = []
    for nid, n in nodes.items():
        if nid.startswith("_:"):
            continue
        attrs = dict(n.get("attrs", {}))
        r = {"node": nid}
        for k in NODE_FIELDS:
            if k in attrs:
                r[k] = attrs.pop(k)
        if attrs:
            r["attrs"] = attrs
        if "weight" in n:
            r["weight"] = n["weight"]
        out_nodes.append(r)
    by_edge = {}
    for inc in hif["incidences"]:
        by_edge.setdefault(inc["edge"], []).append(inc)
    out_edges = []
    for er in hif["edges"]:
        attrs = dict(er["attrs"])
        e = {"edge": er["edge"]}
        for k in EDGE_FIELDS:
            if k in attrs:
                e[k] = attrs.pop(k)
        if attrs:
            e["attrs"] = attrs
        if "weight" in er:
            e["weight"] = er["weight"]
        bindings, specials = [], {}
        for inc in by_edge.get(er["edge"], []):
            a = dict(inc["attrs"])
            b = {"role": a.pop("role")}
            nid = inc["node"]
            if nid.startswith("_:"):
                na = nodes[nid]["attrs"]
                if "literal" in na:
                    b["literal"] = na["literal"]
                    assert nid == literal_node_id(na["literal"]), f"KHG-P010 literal id mismatch {nid}"
                elif "edge" in na:
                    b["edge"] = na["edge"]
                    assert nid == edge_node_id(na["edge"]), f"KHG-P010 edge-node id mismatch {nid}"
                else:
                    b["special"] = na["special"]
                    specials.setdefault((b["role"], b["special"]), []).append(nid)
            else:
                b["node"] = nid
            if "direction" in inc:
                b["direction"] = inc["direction"]
            for k in ("position", "evidence"):
                if k in a:
                    b[k] = a.pop(k)
            if a:
                b["attrs"] = a
            if "weight" in inc:
                b["weight"] = inc["weight"]
            bindings.append(b)
        for (role, kind), ids in specials.items():  # order-independent: ids are role/n/edge, n = 0..k-1
            want = {special_node_id(kind, role, n, er["edge"]) for n in range(len(ids))}
            assert set(ids) == want and len(ids) == len(set(ids)), f"KHG-P010 special ids {ids}"
        e["bindings"] = bindings
        out_edges.append(e)
    doc = {"metadata": meta, "edges": out_edges}
    if out_nodes:
        doc["nodes"] = out_nodes
    return canonical_doc(doc, schema)


def nfc_ok(s: str) -> bool:
    return unicodedata.is_normalized("NFC", s)
