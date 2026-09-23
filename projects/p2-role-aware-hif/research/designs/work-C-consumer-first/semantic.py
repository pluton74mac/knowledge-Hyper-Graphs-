"""Layer-3 (semantic) checks for C1 containers and relation-type schemas. Prototype for design C, section 8.

Every finding is (code, severity, where, message). Codes are the ones listed in the design's error-code table.
"""
from __future__ import annotations

import unicodedata
from collections import Counter, defaultdict

import c1

ERROR, WARNING = "error", "warning"


def F(code, where, msg, sev=ERROR):
    return {"code": code, "severity": sev, "where": where, "message": msg}


# ------------------------------------------------------------------------------------------------
# relation-type schema documents (D-codes)
# ------------------------------------------------------------------------------------------------

def check_schema_doc(doc) -> list:
    out = []
    roles = [r["id"] for r in doc["roles"]]
    for r, n in Counter(roles).items():
        if n > 1:
            out.append(F("D-DUP-ID", f"roles/{r}", "role declared twice"))
    types = {t["id"]: t for t in doc.get("entity_types", [])}
    for t in types.values():
        for p in t.get("parents", []):
            if p not in types:
                out.append(F("D-TYPE", f"entity_types/{t['id']}", f"unknown parent {p}"))
    # parent cycles
    def cyc(t, seen):
        if t in seen:
            return True
        return any(cyc(p, seen | {t}) for p in types.get(t, {}).get("parents", []))
    for t in types:
        if cyc(t, frozenset()):
            out.append(F("D-TYPE", f"entity_types/{t}", "parent cycle"))
    rel_ids = [r["id"] for r in doc["relations"]]
    for r, n in Counter(rel_ids).items():
        if n > 1:
            out.append(F("D-DUP-ID", f"relations/{r}", "relation declared twice"))
    scales = {s["id"]: s for s in doc.get("confidence_scales", [])}
    for s in scales.values():
        if s["min"] >= s["max"]:
            out.append(F("D-SCALE", f"confidence_scales/{s['id']}", "min >= max"))
    rels = {r["id"]: r for r in doc["relations"]}
    for r in doc["relations"]:
        w = f"relations/{r['id']}"
        used = [u["role"] for u in r["roles"]]
        for x, n in Counter(used).items():
            if n > 1:
                out.append(F("D-DUP-USAGE", w, f"role {x} used twice"))
        for u in r["roles"]:
            if u["role"] not in roles:
                out.append(F("D-ROLE-UNDECLARED", w, f"role {u['role']} not in the role vocabulary"))
            if u["max"] is not None and u["min"] > u["max"]:
                out.append(F("D-CARDINALITY", w, f"{u['role']}: min > max"))
            for t in u["fillers"].get("entity_types", []):
                if t not in types:
                    out.append(F("D-TYPE", w, f"{u['role']}: unknown entity type {t}"))
            for x in u["fillers"].get("hyperedge", {}).get("relations", []):
                if x != "*" and x not in rels:
                    out.append(F("D-RELATION-REF", w, f"{u['role']}: unknown relation {x}"))
            if ("precisions" in u["fillers"] and "time" not in u["fillers"].get("datatypes", [])) or \
               ("units" in u["fillers"] and "quantity" not in u["fillers"].get("datatypes", [])):
                out.append(F("D-FILLERS", w, f"{u['role']}: precisions/units without time/quantity"))
            if u.get("ordered") and u["max"] == 1:
                out.append(F("D-ORDERED", w, f"{u['role']}: ordered role with max 1", WARNING))
        k = r.get("key")
        if k:
            usage = {u["role"]: u for u in r["roles"]}
            for x in k["roles"]:
                if x not in usage:
                    out.append(F("D-KEY", w, f"key role {x} is not a usage of the relation"))
                elif usage[x]["min"] < 1:
                    out.append(F("D-KEY", w, f"key role {x} is not required (min >= 1)"))
        p = r.get("primary")
        if p:
            usage = {u["role"]: u for u in r["roles"]}
            for x in (p["subject"], p["object"]):
                if x not in usage or usage[x]["slot"] != "core" or usage[x]["max"] != 1:
                    out.append(F("D-PRIMARY", w, f"primary role {x} must be a core usage with max 1"))
        for c in r.get("constraints", []):
            names = c.get("roles", []) + [c[x] for x in ("if", "then") if x in c]
            for x in names:
                if x not in used:
                    out.append(F("D-CONSTRAINT", w, f"constraint names {x}, not used by the relation"))
    tm = doc.get("time_model", {})
    for k, x in tm.items():
        ok = any(u["role"] == x and "time" in u["fillers"].get("datatypes", []) and u["slot"] == "time"
                 for r in doc["relations"] for u in r["roles"])
        if not ok:
            out.append(F("D-TIME-MODEL", f"time_model/{k}", f"{x} is not a time-slot role with datatype time",
                         WARNING))
    return out


# ------------------------------------------------------------------------------------------------
# records and containers
# ------------------------------------------------------------------------------------------------

def _id_checks(i, where):
    out = []
    if unicodedata.normalize("NFC", i) != i:
        out.append(F("R-ID-NFC", where, f"id {i!r} is not NFC"))
    if i.split(":", 1)[0] in c1.RESERVED_NS:
        out.append(F("R-ID-RESERVED", where, f"id {i!r} uses a reserved namespace"))
    return out


def _filler_ok(schema, u, v, entity_types_of):
    f = u["fillers"]
    if "entity" in v:
        allowed = f.get("entity_types")
        if not allowed:
            return False
        ts = entity_types_of(v["entity"])
        if ts is None:
            return True  # unresolved entity: reported by C-ENTITY-REF
        return any(set(allowed) & schema.type_closure(t) for t in ts) or not ts
    if "literal" in v:
        if v["datatype"] not in f.get("datatypes", []):
            return False
        if v["datatype"] == "time" and "precisions" in f and v["precision"] not in f["precisions"]:
            return False
        if v["datatype"] == "quantity" and "units" in f and v["unit"] not in f["units"]:
            return False
        return True
    if "hyperedge" in v:
        return "hyperedge" in f
    return True  # special values are checked separately


def check_hyperedge(r, schema: c1.Schema, entity_types_of=lambda i: None, canonical=True) -> list:
    out, w = [], r["id"]
    out += _id_checks(r["id"], w)
    bids = [b["bid"] for b in r["bindings"]]
    for x, n in Counter(bids).items():
        if n > 1:
            out.append(F("R-DUP-BID", w, f"bid {x} used twice"))
    eids = [e["eid"] for e in r.get("evidence", [])]
    for x, n in Counter(eids).items():
        if n > 1:
            out.append(F("R-DUP-EID", w, f"eid {x} used twice"))
    for e in r.get("evidence", []):
        for x in e.get("binding_refs", []):
            if x not in bids:
                out.append(F("R-EVIDENCE-REF", w, f"{e['eid']}: binding_refs names missing bid {x}"))
        q = [s for s in e.get("selectors", []) if s["type"] == "quote"]
        for s in e.get("selectors", []):
            if s["type"] == "position":
                if s["end"] <= s["start"]:
                    out.append(F("R-SELECTOR-SPAN", w, f"{e['eid']}: end <= start"))
                elif q and len(q[0]["exact"]) != s["end"] - s["start"]:
                    out.append(F("R-SELECTOR-SPAN", w, f"{e['eid']}: quote length != end - start (code points)"))
    for b in r["bindings"]:
        v = b["value"]
        if "literal" in v:
            for code in c1.literal_errors(v):
                out.append(F(code if code != "R-LIT-LEXICAL" or v.get("datatype") != "time" else "R-LIT-DATE",
                             f"{w}/{b['bid']}", f"literal {v}"))
        for k in ("entity", "hyperedge"):
            if k in v:
                out += _id_checks(v[k], f"{w}/{b['bid']}")
    vt = r.get("valid_time")
    if vt and "from" in vt and "to" in vt and c1.lower_instant(vt["from"]) >= c1.lower_instant(vt["to"]):
        out.append(F("R-VALID-TIME", w, "valid_time.from >= valid_time.to"))
    # --- against the relation-type schema
    rel = schema.relations.get(r["relation"])
    if rel is None:
        return out + [F("S-RELATION", w, f"relation {r['relation']} not declared in {schema.ref}")]
    if not r["bindings"]:
        out.append(F("S-NO-BINDINGS", w, "hyperedge with no bindings"))
    usage = {u["role"]: u for u in rel["roles"]}
    status = r["status"]
    by_role = defaultdict(list)
    for b in r["bindings"]:
        if b["role"] not in usage:
            out.append(F("S-ROLE", f"{w}/{b['bid']}", f"role {b['role']} not allowed for {r['relation']}"))
            continue
        by_role[b["role"]].append(b)
        u = usage[b["role"]]
        v = b["value"]
        if "direction" in b and b["direction"] != u.get("direction"):
            out.append(F("S-DIRECTION", f"{w}/{b['bid']}", "direction contradicts the role usage"))
        if canonical and "direction" in u and "direction" not in b:
            out.append(F("R-DERIVED", f"{w}/{b['bid']}", "declared direction not materialised"))
        if "slot" in b and b["slot"] != u["slot"]:
            out.append(F("R-DERIVED", f"{w}/{b['bid']}", "slot differs from the role usage"))
        sp = v.get("special")
        if sp == "unbound" and status != "goal":
            out.append(F("S-UNBOUND", f"{w}/{b['bid']}", "unbound value outside a goal"))
        if not sp and not _filler_ok(schema, u, v, entity_types_of):
            out.append(F("S-FILLER", f"{w}/{b['bid']}", f"filler {v} not allowed for {b['role']}"))
        if "hyperedge" in v and not rel.get("kind") in ("meta", "rule") and "hyperedge" not in u["fillers"]:
            out.append(F("S-NESTING", f"{w}/{b['bid']}", "hyperedge reference not allowed here"))
    for role, bs in by_role.items():
        u = usage[role]
        n = len(bs)
        if u["max"] is not None and n > u["max"]:
            out.append(F("S-ROLE-MAX", w, f"{role} bound {n} times, max {u['max']}"))
        specials = [b for b in bs if b["value"].get("special") == "novalue"]
        if specials and len(bs) > 1:
            out.append(F("S-NOVALUE-MIXED", w, f"{role}: novalue together with other values"))
        if u.get("ordered"):
            pos = sorted(b.get("position", -1) for b in bs)
            if pos != list(range(n)):
                out.append(F("S-POSITION", w, f"{role}: positions {pos} are not 0..{n - 1}"))
        elif any("position" in b for b in bs):
            out.append(F("S-POSITION", w, f"{role}: position on an unordered role"))
        seen = Counter((c1.cjson(b["value"]), b.get("position")) for b in bs
                       if b["value"].get("special") != "somevalue")
        for k, m in seen.items():
            if m > 1:
                out.append(F("S-DUP-BINDING", w, f"{role}: the same value bound twice"))
    for role, u in usage.items():
        if len(by_role.get(role, [])) < u["min"]:
            sev = WARNING if status in ("goal", "candidate") else ERROR
            out.append(F("S-ROLE-MIN", w, f"{role} bound {len(by_role.get(role, []))} times, min {u['min']}", sev))
    for c in rel.get("constraints", []):
        t = c["type"]
        present = {x for x in by_role}
        if t == "requires" and c["if"] in present and c["then"] not in present:
            out.append(F("S-CONSTRAINT", w, f"{c['if']} requires {c['then']}"))
        if t == "excludes" and len(present & set(c["roles"])) > 1:
            out.append(F("S-CONSTRAINT", w, f"at most one of {c['roles']}"))
        if t == "at_least_one_of" and not present & set(c["roles"]):
            out.append(F("S-CONSTRAINT", w, f"at least one of {c['roles']}"))
        if t == "must_differ":
            vals = [c1.cjson(b["value"]) for x in c["roles"] for b in by_role.get(x, [])
                    if b["value"].get("special") is None]
            if len(vals) != len(set(vals)):
                out.append(F("S-CONSTRAINT", w, f"fillers of {c['roles']} must differ"))
    if status in ("asserted", "disputed", "superseded", "retracted") and not r.get("evidence"):
        out.append(F("S-EVIDENCE-MISSING", w, f"{status} hyperedge without evidence"))
    conf = [r.get("confidence")] + [e.get("confidence") for e in r.get("evidence", [])]
    scales = {s["id"]: s for s in schema.doc.get("confidence_scales", [])}
    for cf in conf:
        if cf:
            s = scales.get(cf["scale"])
            if s is None:
                out.append(F("S-CONFIDENCE", w, f"undeclared confidence scale {cf['scale']}"))
            elif not s["min"] <= cf["value"] <= s["max"]:
                out.append(F("S-CONFIDENCE", w, f"confidence {cf['value']} outside [{s['min']}, {s['max']}]"))
    if status == "superseded" and not r.get("superseded_by"):
        out.append(F("C-SUPERSESSION", w, "status superseded without superseded_by"))
    if status != "superseded" and r.get("superseded_by"):
        out.append(F("C-SUPERSESSION", w, "superseded_by on a record that is not superseded"))
    # --- derived fields
    try:
        n = c1.normalise(r, schema)
        for f in ("arity", "keys", "valid_time"):
            if canonical and n.get(f) != r.get(f):
                out.append(F("R-DERIVED", w, f"derived field {f} is missing or wrong"))
        if [e.get("event_hash") for e in n.get("evidence", [])] != [e.get("event_hash") for e in r.get("evidence", [])]:
            out.append(F("R-DERIVED", w, "event_hash missing or wrong"))
    except ValueError as e:
        out.append(F("R-DERIVED", w, str(e)))
    except KeyError:
        pass  # undeclared role: already reported
    return out


def check_container(records) -> list:
    out = []
    if not records or records[0].get("kind") != "header":
        return [F("C-HEADER", "(line 1)", "first line must be the header")]
    header = records[0]
    content = header["content"]
    schemas = {}
    for r in records[1:]:
        if r["kind"] == "relation-schema":
            out += check_schema_doc(r)
            ref = f"{r['id']}/{r['version']}"
            schemas[ref] = c1.Schema(r)
    listed = {f"{s['id']}/{s['version']}": s["sha256"] for s in header["schemas"]}
    for ref, S in schemas.items():
        if listed.get(ref) != c1.sha256_hex(S.doc):
            out.append(F("C-SCHEMA-REF", ref, "schema not listed in the header or sha256 mismatch"))
    entities = {r["id"]: r for r in records if r["kind"] == "entity"}
    hyper = [r for r in records if r["kind"] == "hyperedge"]
    sups = [r for r in records if r["kind"] == "supersession"]
    # ids unique across kinds (snapshot: one version per id)
    seen = Counter()
    for r in records:
        if r["kind"] in ("entity", "hyperedge", "supersession"):
            seen[(r["id"], r.get("version") if content == "history" else None)] += 1
    for k, n in seen.items():
        if n > 1:
            out.append(F("C-DUP-ID", k[0], "id used by more than one record"))
    for r in records:
        if r["kind"] in ("entity", "supersession"):
            out += _id_checks(r["id"], r["id"])
    kinds_by_id = defaultdict(set)
    for r in records:
        if "id" in r and r["kind"] != "relation-schema":
            kinds_by_id[r["id"]].add(r["kind"])
    for i, ks in kinds_by_id.items():
        if len(ks) > 1:
            out.append(F("C-DUP-ID", i, f"id shared by kinds {sorted(ks)}"))
    current = {}
    for h in sorted(hyper, key=lambda r: (r["id"], r.get("version", 0))):
        current[h["id"]] = h
        for f in ("version", "recorded_at", "recorded_by", "schema"):
            if f not in h:
                out.append(F("C-NOT-CANONICAL", h["id"], f"container record lacks {f}"))
        if h["status"] == "candidate":
            out.append(F("C-STATUS-CANDIDATE", h["id"], "candidate records belong in the queue (C3)"))
        if h.get("id", "").startswith("cand:"):
            out.append(F("R-ID-RESERVED", h["id"], "cand: ids are provisional"))
        S = schemas.get(h.get("schema"))
        if S is None:
            out.append(F("C-SCHEMA-REF", h["id"], f"schema {h.get('schema')} not in the container"))
            continue
        out += check_hyperedge(h, S, lambda i: entities[i]["types"] if i in entities else None)
        for b in h["bindings"]:
            v = b["value"]
            if "entity" in v and v["entity"] not in entities:
                out.append(F("C-ENTITY-REF", f"{h['id']}/{b['bid']}", f"entity {v['entity']} has no entity record"))
    if content == "history":
        by = defaultdict(list)
        for h in hyper:
            by[h["id"]].append(h)
        for i, vs in by.items():
            vs.sort(key=lambda r: r["version"])
            if [v["version"] for v in vs] != list(range(1, len(vs) + 1)):
                out.append(F("C-VERSION", i, "versions are not 1..n"))
            if any(a["recorded_at"] > b["recorded_at"] for a, b in zip(vs, vs[1:])):
                out.append(F("C-TX-ORDER", i, "recorded_at decreases across versions"))
    # nested references resolve, relation nestable, acyclic
    refs = defaultdict(set)
    for h in current.values():
        for b in h["bindings"]:
            if "hyperedge" in b["value"]:
                t = b["value"]["hyperedge"]
                if t not in current:
                    out.append(F("C-HYPEREDGE-REF", f"{h['id']}/{b['bid']}", f"{t} not in the container"))
                    continue
                refs[h["id"]].add(t)
                S = schemas.get(h.get("schema"))
                tr = current[t]["relation"]
                if S and not S.relations.get(tr, {}).get("nestable", False):
                    out.append(F("S-NESTING", f"{h['id']}/{b['bid']}", f"relation {tr} is not nestable"))
                if S:
                    u = S.usage.get((h["relation"], b["role"]), {})
                    allowed = u.get("fillers", {}).get("hyperedge", {}).get("relations", [])
                    if allowed and "*" not in allowed and tr not in allowed:
                        out.append(F("S-FILLER", f"{h['id']}/{b['bid']}", f"relation {tr} not allowed here"))
    if _has_cycle(refs):
        out.append(F("C-NESTING-CYCLE", "(container)", "hyperedge references form a cycle"))
    # supersession: ends resolve, status consistent, acyclic, pointer index consistent
    sup_edges = defaultdict(set)
    superseded_by = defaultdict(set)
    for s in sups:
        for end in ("superseded", "superseding"):
            if s[end] not in current:
                out.append(F("C-SUPERSESSION", s["id"], f"{end} {s[end]} not in the container"))
        if s["superseded"] == s["superseding"]:
            out.append(F("C-SUPERSESSION", s["id"], "a record cannot supersede itself"))
        sup_edges[s["superseding"]].add(s["superseded"])
        superseded_by[s["superseded"]].add(s["superseding"])
        a, b = current.get(s["superseded"]), current.get(s["superseding"])
        if a and b and (a["relation"] != b["relation"] or a["keys"].get("key") != b["keys"].get("key")):
            out.append(F("C-SUPERSESSION-KEY", s["id"], "superseding and superseded differ in relation or key",
                         WARNING))
    if _has_cycle(sup_edges):
        out.append(F("C-SUPERSESSION", "(container)", "supersession links form a cycle"))
    for h in current.values():
        want = sorted(superseded_by.get(h["id"], []))
        if h["status"] == "superseded" and sorted(h.get("superseded_by", [])) != want:
            out.append(F("C-SUPERSESSION", h["id"], "superseded_by does not match the supersession records"))
        if want and h["status"] != "superseded":
            out.append(F("C-SUPERSESSION", h["id"], "superseded by a record but status is not superseded"))
    # key collisions among current asserted/disputed records
    groups = defaultdict(list)
    for h in current.values():
        if h["status"] in ("asserted",) and h["keys"].get("key"):
            groups[(h["relation"], h["keys"]["key"])].append(h)
    for (rel, _), hs in groups.items():
        S = schemas.get(hs[0].get("schema"))
        temporal = S.relations[rel]["key"]["temporal"] if S else True
        for i in range(len(hs)):
            for j in range(i + 1, len(hs)):
                if not temporal or _overlap(hs[i].get("valid_time"), hs[j].get("valid_time")):
                    out.append(F("C-KEY-COLLISION", f"{hs[i]['id']},{hs[j]['id']}",
                                 "two current asserted records share a key and overlap in valid time"))
    return out


def _overlap(a, b):
    lo = lambda v: c1.lower_instant(v["from"]) if v and "from" in v else (-10**9,)   # noqa: E731
    hi = lambda v: c1.lower_instant(v["to"]) if v and "to" in v else (10**9,)        # noqa: E731
    return lo(a) < hi(b) and lo(b) < hi(a)


def _has_cycle(edges):
    state = {}

    def visit(n):
        if state.get(n) == 1:
            return True
        if state.get(n) == 2:
            return False
        state[n] = 1
        if any(visit(m) for m in edges.get(n, ())):
            return True
        state[n] = 2
        return False
    return any(visit(n) for n in list(edges))
