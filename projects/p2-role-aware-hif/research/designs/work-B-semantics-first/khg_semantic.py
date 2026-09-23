"""Semantic layer (S*/D* codes) of the prototype validator: checks JSON Schema cannot express."""
from __future__ import annotations

import unicodedata
from collections import Counter, defaultdict

from khg_proto import (KHGError, Schema, _vk, canon_literal, canon_value, cjson, definite_overlap, derived,
                       key_digest, presumed_interval, vkind)

FACT_STATUSES_NEED_COMPLETE = {"asserted", "disputed", "superseded", "retracted", "quoted"}


def _types_closure(schema: Schema):
    parents = {t["id"]: set(t.get("parents", [])) for t in schema.doc.get("entity_types", [])}

    def anc(t, seen=None):
        seen = seen or set()
        for p in parents.get(t, ()):
            if p not in seen:
                seen.add(p)
                anc(p, seen)
        return seen
    return {t: {t} | anc(t) | {"Thing"} for t in parents}


def validate_document(doc, schema: Schema, *, candidate_ok=False):
    """Returns a list of (code, severity, message). severity is 'violation' or 'warning'."""
    out = []

    def err(code, msg, sev="violation"):
        out.append((code, sev, msg))

    recs = doc["records"]
    closure = _types_closure(schema)
    ents = {r["id"]: r for r in recs if r["kind"] == "entity"}
    edges = {}
    for r in recs:
        if r["kind"] == "entity":
            continue
        if r["id"] in edges:
            err("KHG-D001", f"record id {r['id']!r} twice in a current snapshot")
        edges[r["id"]] = r
    for i in set(ents) & set(edges):
        err("KHG-D007", f"id {i!r} names both an entity and a fact")
    complete = doc["header"].get("complete", False)
    scales = {"probability": (0.0, 1.0)}
    for s in schema.doc.get("confidence_scales", []):
        scales[s["id"]] = (s.get("min"), s.get("max"))

    def check_conf(c, where):
        if c["scale"] not in scales:
            err("KHG-S010", f"{where}: confidence scale {c['scale']!r} undeclared")
            return
        lo, hi = scales[c["scale"]]
        if (lo is not None and c["value"] < lo) or (hi is not None and c["value"] > hi):
            err("KHG-S010", f"{where}: confidence {c['value']} outside [{lo}, {hi}]")

    for r in recs:
        for idv in [r["id"]] + [b["value"].get("entity") or b["value"].get("fact") for b in r.get("bindings", [])
                                if vkind(b["value"]) in ("entity", "fact")]:
            if idv and unicodedata.normalize("NFC", idv) != idv:
                err("KHG-S020", f"id {idv!r} is not NFC")
        if r["kind"] == "entity":
            for t in r.get("types", []):
                if t not in closure:
                    err("KHG-S005", f"entity {r['id']!r}: undeclared type {t!r}")
            continue
        rel = r["relation"]
        if r["kind"] in ("fact", "rule", "goal") and (rel not in schema.rel or rel.startswith("khg:")):
            err("KHG-S001", f"{r['id']}: relation {rel!r} not declared")
            continue
        if r["kind"] == "fact" and r["status"] == "candidate" and not candidate_ok:
            err("KHG-D017", f"{r['id']}: status candidate outside the queue")
        if not r.get("bindings") and r["kind"] != "goal":
            err("KHG-S007", f"{r['id']}: no bindings")
        rdecl = schema.rel[rel]
        usages = {u["role"]: u for u in rdecl["roles"]}
        by_role = defaultdict(list)
        bids = Counter(b["bid"] for b in r["bindings"])
        for bid, k in bids.items():
            if k > 1:
                err("KHG-S025", f"{r['id']}: bid {bid!r} used twice")
        for b in r["bindings"]:
            u = usages.get(b["role"])
            if u is None:
                err("KHG-S002", f"{r['id']}: role {b['role']!r} not allowed for {rel!r}")
                continue
            by_role[b["role"]].append(b)
            k = _vk(b["value"])
            if k == "unbound":
                if r["kind"] != "goal":
                    err("KHG-S012", f"{r['id']}: unbound value outside a goal")
                continue
            if k.startswith("special:"):
                sp = k.split(":")[1]
                if not u.get(sp, True):
                    err("KHG-S005", f"{r['id']}.{b['bid']}: {sp} not allowed for role {b['role']!r}")
                continue
            ok = False
            for f in u["fillers"]:
                if k == "entity" and "entity" in f:
                    e = ents.get(b["value"]["entity"])
                    if e is None:
                        if complete:
                            err("KHG-D002", f"{r['id']}.{b['bid']}: entity {b['value']['entity']!r} has no record")
                        ok = True
                        break
                    allowed = set(f["entity"]) or {"Thing"}
                    if any(allowed & closure.get(t, {t}) for t in e.get("types", [])) or "Thing" in allowed:
                        ok = True
                        break
                if k == "literal" and "literal" in f and f["literal"] == b["value"]["literal"]["datatype"]:
                    lit = b["value"]["literal"]
                    try:
                        canon_literal(lit)
                    except KHGError as ex:
                        err(ex.code, f"{r['id']}.{b['bid']}: {ex}")
                    if "precision_min" in f and lit.get("precision", 99) < f["precision_min"]:
                        err("KHG-S023", f"{r['id']}.{b['bid']}: precision below {f['precision_min']}")
                    if "units" in f and lit.get("unit") not in f["units"]:
                        err("KHG-S023", f"{r['id']}.{b['bid']}: unit {lit.get('unit')!r} not allowed")
                    ok = True
                    break
                if k == "fact" and "fact" in f:
                    tgt = edges.get(b["value"]["fact"])
                    if tgt is None and complete:
                        err("KHG-D002", f"{r['id']}.{b['bid']}: fact {b['value']['fact']!r} not in document")
                        ok = True
                        break
                    if tgt is None or not f["fact"] or tgt["relation"] in f["fact"]:
                        ok = True
                        break
            if not ok:
                err("KHG-S005", f"{r['id']}.{b['bid']}: filler kind/type not allowed for role {b['role']!r}")
            d = b.get("direction")
            if d and u.get("direction") and d != u["direction"]:
                err("KHG-S016", f"{r['id']}.{b['bid']}: direction {d} contradicts declared {u['direction']}")
        for role, u in usages.items():
            bs = by_role.get(role, [])
            nonunb = [b for b in bs if _vk(b["value"]) != "unbound"]
            if u["max"] is not None and len(bs) > u["max"]:
                err("KHG-S004", f"{r['id']}: role {role!r} bound {len(bs)} times, max {u['max']}")
            if len(bs) < u["min"]:
                if r["kind"] == "goal":
                    err("KHG-S018", f"{r['id']}: goal omits required role {role!r} (bind it or leave it unbound)")
                elif r["status"] in FACT_STATUSES_NEED_COMPLETE:
                    err("KHG-S003", f"{r['id']}: required role {role!r} has {len(bs)} of {u['min']} bindings")
            if any(_vk(b["value"]) == "special:novalue" for b in bs) and len(bs) > 1:
                err("KHG-S013", f"{r['id']}: novalue and another filler for role {role!r}")
            if u.get("ordered"):
                pos = [b.get("position") for b in bs]
                if None in pos or sorted(pos) != list(range(1, len(bs) + 1)):
                    err("KHG-S015", f"{r['id']}: positions of ordered role {role!r} are {pos}, expected 1..{len(bs)}")
            else:
                if any("position" in b for b in bs):
                    err("KHG-S015", f"{r['id']}: position on unordered role {role!r}")
                vals = Counter(cjson(canon_value(b["value"])) for b in nonunb)
                if any(k > 1 for k in vals.values()):
                    err("KHG-S014", f"{r['id']}: duplicate filler in unordered role {role!r}")
        if r["kind"] == "goal":
            vars_ = Counter(b["value"]["unbound"]["var"] for b in r["bindings"] if _vk(b["value"]) == "unbound")
            if any(k > 1 for k in vars_.values()):
                err("KHG-S019", f"{r['id']}: an unbound variable is repeated")
        for c in rdecl.get("constraints", []):
            sev = c.get("severity", "violation")
            if c["type"] == "must_differ":
                vs = [cjson(canon_value(b["value"])) for role in c["roles"] for b in by_role.get(role, [])]
                if len(vs) != len(set(vs)):
                    err("KHG-S024", f"{r['id']}: must_differ {c['roles']} violated", sev)
        if r["kind"] in ("fact", "rule"):
            iv = presumed_interval(schema, r)
            if not iv["s_lo"] < iv["e_hi"]:
                err("KHG-S009", f"{r['id']}: valid time is empty (start after end)")
        for ev in r.get("evidence", []):
            for bid in ev.get("supports", []):
                if bid not in bids:
                    err("KHG-S022", f"{r['id']}.{ev['id']}: supports unknown bid {bid!r}")
            for sel in ev.get("selectors", []):
                if sel["type"] == "position" and not sel["start"] < sel["end"]:
                    err("KHG-S021", f"{r['id']}.{ev['id']}: empty or reversed span")
            if "confidence" in ev:
                check_conf(ev["confidence"], f"{r['id']}.{ev['id']}")
        if "confidence" in r:
            check_conf(r["confidence"], r["id"])
        if r["kind"] == "fact" and r["status"] == "asserted":
            if not any(not (ev.get("epistemics") or {}).get("negated") for ev in r.get("evidence", [])):
                err("KHG-S011", f"{r['id']}: asserted fact without supporting evidence")
        if r["kind"] == "rule":
            tails = {cjson(b["value"]) for b in r["bindings"] if (b.get("direction") or usages[b["role"]].get("direction")) == "tail"}
            heads = {cjson(b["value"]) for b in r["bindings"] if (b.get("direction") or usages[b["role"]].get("direction")) == "head"}
            if tails & heads:
                err("KHG-S017", f"{r['id']}: a node is both tail and head of a rule hyperarc")
        if "derived" in r and r["kind"] in ("fact", "rule", "goal"):
            if cjson(r["derived"]) != cjson(derived(schema, r)):
                err("KHG-D015", f"{r['id']}: derived fields disagree with the bindings")

    # nesting acyclicity (fact-valued bindings across all non-entity records)
    graph = {i: [b["value"]["fact"] for b in r["bindings"] if vkind(b["value"]) == "fact"] for i, r in edges.items()}
    state = {}

    def dfs(u, stack):
        state[u] = 1
        for v in graph.get(u, []):
            if state.get(v) == 1:
                err("KHG-D008", f"nesting cycle through {u!r} -> {v!r}")
            elif v in graph and state.get(v) is None:
                dfs(v, stack)
        state[u] = 2
    for i in sorted(graph):
        if state.get(i) is None:
            dfs(i, [])

    # lifecycle pointers and supersession records
    need_rel = {"superseded": ("khg:supersedes", "khg:superseded"), "retracted": ("khg:retracts", "khg:retracted"),
                "disputed": ("khg:disputes", "khg:disputed")}
    for i, r in edges.items():
        st = r.get("status")
        if st in need_rel:
            m = edges.get(r.get("status_ref"))
            rel, role = need_rel[st]
            if m is None or m["kind"] != "meta" or m["relation"] != rel or \
                    not any(b["role"] == role and b["value"].get("fact") == i for b in m["bindings"]):
                err("KHG-D010", f"{i}: status {st} needs status_ref to a {rel} record naming it as {role}")
    sup_graph = defaultdict(set)
    for i, m in edges.items():
        if m["kind"] == "meta" and m["relation"] == "khg:supersedes" and m["status"] == "asserted":
            new = [b["value"]["fact"] for b in m["bindings"] if b["role"] == "khg:superseding"]
            old = [b["value"]["fact"] for b in m["bindings"] if b["role"] == "khg:superseded"]
            for o in old:
                for n in new:
                    sup_graph[n].add(o)
            if m["meta"]["reason"] == "correction":
                rels = {edges[x]["relation"] for x in new + old if x in edges}
                if len(rels) > 1:
                    err("KHG-D011", f"{i}: correction across relations {sorted(rels)}")
                elif rels:
                    kd = {key_digest(schema, edges[x]) for x in new + old if x in edges}
                    if schema.key(rels.pop()) and len(kd) > 1:
                        err("KHG-D011", f"{i}: correction between facts with different key bindings")
            for o in old:
                if o in edges and edges[o].get("status") != "superseded":
                    err("KHG-D010", f"{i}: {o} is superseded here but its status is {edges[o].get('status')!r}")
    seen, onstack = set(), set()

    def sdfs(u):
        seen.add(u)
        onstack.add(u)
        for v in sup_graph.get(u, ()):
            if v in onstack:
                err("KHG-D012", f"supersession cycle through {u!r} -> {v!r}")
            elif v not in seen:
                sdfs(v)
        onstack.discard(u)
    for u in sorted(sup_graph):
        if u not in seen:
            sdfs(u)

    # key invariant: asserted, non-deprecated facts with one key digest must not (definitely) overlap
    groups = defaultdict(list)
    for i, r in edges.items():
        if r["relation"] not in schema.rel:
            continue
        if r["kind"] == "fact" and r["status"] == "asserted" and r.get("rank", "normal") != "deprecated":
            kd = key_digest(schema, r)
            if kd:
                groups[(r["relation"], kd)].append(r)
    for (rel, kd), rs in groups.items():
        key = schema.key(rel)
        if not key["temporal"]:
            instants = [None]
        else:
            instants = sorted({presumed_interval(schema, r)["s_hi"] for r in rs})
        for t in instants:
            if t is None:
                live = rs
            else:
                live = [r for r in rs if presumed_interval(schema, r)["s_hi"] <= t < presumed_interval(schema, r)["e_lo"]]
            pref = [r for r in live if r.get("rank") == "preferred"]
            if len(live) > 1 and len(pref) != 1:
                err("KHG-D016", f"key conflict on {rel}: {sorted(r['id'] for r in live)}")
                break
    return out
