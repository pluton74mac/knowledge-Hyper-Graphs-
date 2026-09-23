"""Prototype of the layer-S (semantic) validator of design A, document scope. Standard library only.

validate(doc, schema, texts=None) -> list of (code, path, message). Store-scope rules (S029-S031) need a
store and are exercised by the C2 conformance scenarios instead.
"""
from __future__ import annotations

import calendar
import hashlib
import re
import unicodedata

import proto

LIFECYCLE_REL = {"superseded": "khg:supersedes", "retracted": "khg:retracts"}
EVIDENCE_REQUIRED = ("asserted", "superseded", "retracted")


def _time_ok(v):
    m = re.fullmatch(r"-?(\d{4})(?:-(\d{2})(?:-(\d{2})(?:T.*)?)?)?", v)
    if not m:
        return True  # decade/century/millennium forms: regex-checked by layer P
    y, mo, d = m.groups()
    if d:
        return 1 <= int(d) <= calendar.monthrange(int(y), int(mo))[1]
    return True


def _strings(x, path=""):
    if isinstance(x, str):
        yield path, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from _strings(k, path + "/<key>")
            yield from _strings(v, f"{path}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _strings(v, f"{path}/{i}")


def validate(doc, schema: proto.Schema, texts: dict | None = None, scope_edges: dict | None = None):
    out = []

    def err(code, path, msg):
        out.append((code, path, msg))

    for p, s in _strings(doc):
        if not unicodedata.is_normalized("NFC", s):
            err("KHG-S027", p, f"string not NFC: {s!r}")
    if doc["metadata"]["khg-schema"] not in schema.ids:
        err("KHG-S025", "/metadata/khg-schema", "schema id not loaded")
    nodes = {}
    for i, n in enumerate(doc.get("nodes", [])):
        if n["node"] in nodes:
            err("KHG-S026", f"/nodes/{i}", f"duplicate node record {n['node']}")
        nodes[n["node"]] = n
    edges, seen = {}, set()
    for i, e in enumerate(doc["edges"]):
        k = (e["edge"], e.get("recorded"))
        if k in seen:
            err("KHG-S026", f"/edges/{i}", f"duplicate edge record {e['edge']}")
        seen.add(k)
        edges[e["edge"]] = e
    scope = dict(scope_edges or {})
    scope.update(edges)
    for i, e in enumerate(doc["edges"]):
        P = f"/edges/{i}"
        rel = schema.relations.get(e["relation"])
        if rel is None:
            err("KHG-S001", P + "/relation", f"unknown relation {e['relation']}")
            continue
        if e.get("schema") and e["schema"] not in schema.ids:
            err("KHG-S025", P + "/schema", "edge typed under a schema that is not loaded")
        st = e["status"]
        counts, positions, seen_b, specials = {}, {}, set(), {}
        ev_ids = [ev["id"] for ev in e.get("evidence", [])]
        if len(ev_ids) != len(set(ev_ids)):
            err("KHG-S017", P + "/evidence", "duplicate evidence id")
        for j, b in enumerate(e["bindings"]):
            BP = f"{P}/bindings/{j}"
            role = b["role"]
            if role in schema.valid_roles.values():
                err("KHG-S024", BP, f"time role {role} must be lifted into 'valid'")
            u = rel["roles"].get(role)
            if u is None:
                err("KHG-S002", BP, f"role {role} not declared for {e['relation']}")
                continue
            kind = proto.value_kind(b)
            counts[role] = counts.get(role, 0) + (0 if b.get("special") == "novalue" else 1)
            specials.setdefault(role, set()).add(b.get("special", kind))
            if kind == "node":
                if "types" not in u:
                    err("KHG-S005", BP, "entity filler not allowed for this role")
                elif b["node"] in nodes and nodes[b["node"]].get("types") and \
                        not set(nodes[b["node"]]["types"]) & set(u["types"]):
                    err("KHG-S006", BP, f"{b['node']} has types {nodes[b['node']]['types']}, role wants {u['types']}")
            elif kind == "literal":
                lit = b["literal"]
                if lit["datatype"] not in u.get("datatypes", []):
                    err("KHG-S005", BP, f"literal {lit['datatype']} not allowed for this role")
                elif "values" in u and lit["value"] not in u["values"]:
                    err("KHG-S007", BP, f"value {lit['value']!r} not in {u['values']}")
                if lit["datatype"] == "time" and not _time_ok(lit["value"]):
                    err("KHG-S007", BP, f"invalid calendar date {lit['value']}")
                if lit["datatype"] == "quantity":
                    lo, hi, v = lit.get("lower"), lit.get("upper"), lit["value"]
                    if (lo is not None and float(lo) > float(v)) or (hi is not None and float(hi) < float(v)):
                        err("KHG-S007", BP, "quantity outside its bounds")
            elif kind == "edge":
                if "edges" not in u:
                    err("KHG-S005", BP, "hyperedge filler not allowed for this role")
                elif b["edge"] not in scope:
                    err("KHG-S013", BP, f"dangling reference to edge {b['edge']}")
                elif u["edges"] != ["*"] and scope[b["edge"]]["relation"] not in u["edges"]:
                    err("KHG-S015", BP, f"edge {b['edge']} of relation {scope[b['edge']]['relation']} not allowed")
            else:
                if b["special"] == "unbound" and st != "goal":
                    err("KHG-S008", BP, "unbound slot outside a goal")
            if u.get("ordered"):
                if "position" not in b:
                    err("KHG-S010", BP, "ordered role without position")
                else:
                    if b["position"] in positions.setdefault(role, set()):
                        err("KHG-S010", BP, "duplicate position")
                    positions[role].add(b["position"])
            elif "position" in b:
                err("KHG-S010", BP, "position on an unordered role")
            if u.get("direction") and b.get("direction") and b["direction"] != u["direction"]:
                err("KHG-S011", BP, f"direction {b['direction']} contradicts declared {u['direction']}")
            key = (role, b.get("position"), repr(proto.value_part(b)))
            if key in seen_b and b.get("special") not in ("somevalue", "unbound"):
                err("KHG-S012", BP, "duplicate binding")
            seen_b.add(key)
            for ref in b.get("evidence", []):
                if ref not in ev_ids:
                    err("KHG-S017", BP + "/evidence", f"unknown evidence id {ref}")
        for role, ks in specials.items():
            if "novalue" in ks and len(ks) > 1:
                err("KHG-S009", P, f"novalue together with another value for {role}")
        for role, u in rel["roles"].items():
            n = counts.get(role, 0)
            mx = u.get("max", 1)
            if mx is not None and n > mx:
                err("KHG-S004", P, f"role {role} bound {n} times, max {mx}")
            has_none = "novalue" in specials.get(role, set())
            if n < u.get("min", 0) and not has_none and st in EVIDENCE_REQUIRED:
                err("KHG-S003", P, f"role {role} bound {n} times, min {u.get('min', 0)}")
        if st in EVIDENCE_REQUIRED and not e.get("evidence"):
            err("KHG-S016", P, f"{st} edge without evidence")
        for k, ev in enumerate(e.get("evidence", [])):
            EP = f"{P}/evidence/{k}"
            if ev["type"] in ("extracted", "inferred") and not all(f in ev for f in ("agent", "version", "run")):
                err("KHG-S019", EP, "model-produced evidence needs agent, version and run")
            if "start" in ev:
                if ev["start"] >= ev["end"] or len(ev["exact"]) != ev["end"] - ev["start"]:
                    err("KHG-S018", EP, "span: start < end and len(exact) == end - start required")
                elif texts and ev.get("source") in texts:
                    t = texts[ev["source"]]
                    if "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest() != ev["digest"]:
                        err("KHG-S018", EP, "digest does not match the source text")
                    elif t[ev["start"]:ev["end"]] != ev["exact"]:
                        err("KHG-S018", EP, "text[start:end] != exact")
            c = ev.get("confidence")
            if c and c["scale"] == "score" and not (c["min"] < c["max"] and c["min"] <= c["value"] <= c["max"]):
                err("KHG-S021", EP, "confidence outside its declared range")
        v = e.get("valid")
        if v and "from" in v and "until" in v and _instant(v["from"]) >= _instant(v["until"]):
            err("KHG-S020", P + "/valid", "empty or reversed interval")
    # nesting: acyclic over edge-valued bindings
    graph = {eid: [b["edge"] for b in e["bindings"] if "edge" in b] for eid, e in edges.items()}
    state = {}

    def visit(x, stack):
        if state.get(x) == 1:
            err("KHG-S014", f"/edges/{x}", "nesting cycle: " + " -> ".join(stack + [x]))
            return
        if state.get(x) == 2 or x not in graph:
            return
        state[x] = 1
        for y in graph[x]:
            visit(y, stack + [x])
        state[x] = 2
    for x in sorted(graph):
        visit(x, [])
    # lifecycle consistency (F8): status <-> meta-edge <-> superseded-by index
    sup = {}
    retr = set()
    for eid, e in edges.items():
        if e["relation"] == "khg:supersedes" and e["status"] == "asserted":
            new = [b["edge"] for b in e["bindings"] if b["role"] == "khg:superseding"][0]
            old = [b["edge"] for b in e["bindings"] if b["role"] == "khg:superseded"][0]
            sup.setdefault(old, set()).add(new)
            if new == old:
                err("KHG-S022", f"/edges/{eid}", "an edge cannot supersede itself")
            elif new in scope and old in scope:
                a, b_ = scope[new], scope[old]
                if a["relation"] != b_["relation"] or proto.key_digest(a, schema) != proto.key_digest(b_, schema):
                    err("KHG-S023", f"/edges/{eid}", "supersession across relations or key bindings")
        if e["relation"] == "khg:retracts" and e["status"] == "asserted":
            retr.add([b["edge"] for b in e["bindings"] if b["role"] == "khg:retracted"][0])
    for eid, e in edges.items():
        if e["status"] == "superseded" and set(e.get("superseded-by", [])) != sup.get(eid, set()):
            err("KHG-S022", f"/edges/{eid}", "superseded-by disagrees with the khg:supersedes records")
        if e["status"] != "superseded" and eid in sup:
            err("KHG-S022", f"/edges/{eid}", "a khg:supersedes record names an edge that is not superseded")
        if e["status"] == "retracted" and eid not in retr:
            err("KHG-S022", f"/edges/{eid}", "retracted without a khg:retracts record")
    return out


def _instant(t):
    t = t.replace("X", "0")
    if len(t.lstrip("-")) == 4:
        t += "-01-01"
    elif len(t.lstrip("-")) == 7:
        t += "-01"
    return t if "T" in t else t + "T00:00:00Z"
