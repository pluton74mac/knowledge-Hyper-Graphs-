"""Prototype of the C2 reference store (MemoryStore) of DESIGN.md §6, used to execute the conformance scenarios,
derive memory gold (§9) and run the G3 smoke path. Research code: small, readable, not fast, not the package."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field

import khg_synth as K

ALL_FLAGS = frozenset({"literal_values", "special_values", "goals", "nesting", "ordered_roles", "valid_time",
                       "transaction_time", "key_constraint", "atomic_writes", "history_export"})
EDITABLE = {"rank", "rank_reason", "visibility", "confidence", "source_text", "extensions"}


class CapabilityMissing(Exception):
    def __init__(self, flag):
        super().__init__(f"capability missing: {flag}")
        self.flag = flag


class Clock:
    """The scenario clock: starts at 2026-10-01T00:00:00Z and ticks one second per write call."""

    def __init__(self, start="2026-10-01T00:00:00Z", step=1):
        self.t = _tx(start)
        self.step = step

    def now(self):
        return _rfc(self.t)

    def tick(self):
        self.t += self.step
        return self.now()

    def set(self, at):
        self.t = _tx(at)


def _tx(at):
    """RFC 3339 UTC timestamp -> seconds (via the instant grammar)."""
    return K.parse_instant("+" + at if not at.startswith(("+", "-")) else at)


def _rfc(t):
    return K.fmt_instant(t)[1:]


@dataclass(frozen=True)
class Where:
    status: frozenset = frozenset({"asserted"})
    rank: frozenset = frozenset({"preferred", "normal"})
    visibility: frozenset = frozenset({"visible"})
    kinds: frozenset = frozenset({"fact"})
    as_of: str | None = None
    valid_mode: str = "definite"
    as_at: str | None = None

    @classmethod
    def of(cls, d):
        d = dict(d or {})
        for k in ("status", "rank", "visibility", "kinds"):
            if k in d:
                d[k] = frozenset(d[k])
        return cls(**d)


def _strip_store(r):
    r = copy.deepcopy(r)
    for f in K.STORE_FIELDS:
        r.pop(f, None)
    r.pop("derived", None)
    return r


def _same_content(a, b):
    return K.cjson(K.canonical_record(_strip_store(a))) == K.cjson(K.canonical_record(_strip_store(b)))


class ProtoStore:
    def __init__(self, schema: K.Schema, *, clock=None, capabilities=None, store_id="proto"):
        self.S = schema
        self.clock = clock or Clock()
        self.flags = frozenset(ALL_FLAGS if capabilities is None else capabilities)
        self.store_id = store_id
        self.v = {}          # id -> [versions]
        self.header = None
        self.latest = None   # seconds

    # ------------------------------------------------------------------ helpers
    def need(self, flag):
        if flag not in self.flags:
            raise CapabilityMissing(flag)

    def info(self):
        return {"interface_version": "khg-store/1.0.0", "record_format": "khg-record/1.0.0",
                "capabilities": sorted(self.flags), "store_id": self.store_id, "header": copy.deepcopy(self.header)}

    def _at(self, at):
        if at is None:
            t = self.clock.t if self.latest is None or self.clock.t > self.latest else self.latest + 1
            at_s = _rfc(t)
        else:
            at_s = at
            t = _tx(at)
        if self.latest is not None and t <= self.latest:
            raise K.KHGError("KHG-D018", f"transaction time {at_s} is not after the store's latest {_rfc(self.latest)}")
        return t, at_s

    def _commit_time(self, t):
        self.latest = t
        if self.clock.t < t:
            self.clock.t = t
        self.clock.tick()

    def current(self, id, as_at=None):
        vs = self.v.get(id)
        if not vs:
            return None
        if as_at is None:
            return vs[-1]
        t = _tx(as_at)
        ok = [x for x in vs if _tx(x["recorded_at"]) <= t]
        return ok[-1] if ok else None

    def _state(self, as_at=None):
        out = {}
        for i in self.v:
            c = self.current(i, as_at)
            if c is not None:
                out[i] = c
        return out

    def _data_flags(self, r):
        fl = set()
        if r.get("kind") != "hyperedge":
            return fl
        if r.get("status") == "goal":
            fl.add("goals")
        for b in r.get("bindings", []):
            k = K.vkind(b["value"])
            if k == "literal":
                fl.add("literal_values")
            elif k == "special":
                fl.add("special_values")
            elif k == "unbound":
                fl.add("goals")
            elif k == "fact" and self.S.kind(r["relation"]) != "lifecycle":
                fl.add("nesting")
            if "position" in b:
                fl.add("ordered_roles")
        return fl

    # ------------------------------------------------------------------ validation of one record
    def _check_record(self, r, state, batch_ids):
        S = self.S
        if r.get("kind") == "entity":
            return
        if r.get("kind") != "hyperedge":
            raise K.KHGError("KHG-C002", f"record kind {r.get('kind')!r}")
        if r["relation"] not in S.rel:
            raise K.KHGError("KHG-S001", f"relation {r['relation']!r} not declared")
        st = r.get("status")
        if st == "candidate":
            raise K.KHGError("KHG-D017", "a candidate never enters a store")
        counts = {}
        for b in r["bindings"]:
            u = S.usage(r["relation"], b["role"])
            counts[b["role"]] = counts.get(b["role"], 0) + 1
            v = b["value"]
            k = K.vkind(v)
            if k == "unbound" and st != "goal":
                raise K.KHGError("KHG-C005", "unbound value outside a goal")
            if k == "literal":
                K.canon_literal(v["literal"])
                if v["literal"]["datatype"] == "time":
                    K.time_window(v["literal"])
            if k == "entity":
                ent = state.get(v["entity"])
                if ent is None:
                    raise K.KHGError("KHG-D002", f"entity {v['entity']!r} is not held by the store")
                if ent.get("redirect_to"):
                    raise K.KHGError("KHG-D020", f"entity {v['entity']!r} redirects to {ent['redirect_to']!r}")
                want = [t for f in u["fillers"] if "entity" in f for t in f["entity"]]
                if want and not any(S.is_subtype(t, w) for t in ent.get("types", []) for w in want):
                    raise K.KHGError("KHG-S005", f"{v['entity']} is not a {want}")
            if k == "fact" and v["fact"] not in state:
                raise K.KHGError("KHG-D002", f"fact reference {v['fact']!r} does not resolve")
        for u in S.usages(r["relation"]):
            n = counts.get(u["role"], 0)
            if st in ("asserted", "quoted", "disputed") and n < u.get("min", 0):
                raise K.KHGError("KHG-S003", f"role {u['role']} bound {n} times, min {u['min']}")
            if u.get("max") is not None and n > u["max"]:
                raise K.KHGError("KHG-S004", f"role {u['role']} bound {n} times, max {u['max']}")
        if st == "asserted" and self.S.kind(r["relation"]) != "lifecycle" and not r.get("evidence"):
            raise K.KHGError("KHG-S011", "asserted fact without evidence")
        b = K.bounds(S, r)
        if b["s_lo"] >= b["e_hi"]:
            raise K.KHGError("KHG-S009", "possible validity empty")

    def _version_rule(self, old, new, *, allow_novalue_end=False):
        S = self.S
        if old["kind"] == "entity":
            for f in set(old) | set(new):
                if f in K.STORE_FIELDS or f in ("kind", "id", "label", "aliases", "extensions"):
                    continue
                if f == "types":
                    if not set(old.get("types", [])) <= set(new.get("types", [])):
                        raise K.KHGError("KHG-D013", "entity types may only grow")
                elif f == "redirect_to":
                    if old.get("redirect_to") and old.get("redirect_to") != new.get("redirect_to"):
                        raise K.KHGError("KHG-D013", "redirect_to is set once and never changed")
                elif old.get(f) != new.get(f):
                    raise K.KHGError("KHG-D013", f"entity field {f} may not change")
            return
        if old["status"] in ("superseded", "retracted"):
            raise K.KHGError("KHG-D013", f"a {old['status']} fact is frozen")
        if old["relation"] != new["relation"]:
            raise K.KHGError("KHG-D013", "a new version keeps the relation")
        ob = {b["bid"]: b for b in old["bindings"]}
        nb = {b["bid"]: b for b in new["bindings"]}
        for bid, b in ob.items():
            n = nb.get(bid)
            if n is None or n["role"] != b["role"] or n.get("position") != b.get("position"):
                raise K.KHGError("KHG-D013", f"binding {bid} removed or changed role or position")
            if not K.value_refines(n["value"], b["value"]):
                is_novalue_end = (allow_novalue_end and K.vkind(b["value"]) == "special" and
                                  b["value"]["special"] == "novalue" and
                                  S.time_model(old["relation"]).get("end") == b["role"])
                if not is_novalue_end:
                    raise K.KHGError("KHG-D013", f"binding {bid} is not refined")
        for bid, b in nb.items():
            if bid not in ob:
                u = S.usage(new["relation"], b["role"])
                if u.get("complete") and any(x["role"] == b["role"] for x in old["bindings"]):
                    raise K.KHGError("KHG-D013", f"role {b['role']} is complete")
        oe = {e["id"]: e for e in old.get("evidence", [])}
        ne = {e["id"]: e for e in new.get("evidence", [])}
        for eid, e in oe.items():
            if eid not in ne or K.cjson(K.canonical_record({"kind": "hyperedge", "bindings": [], "evidence": [e]})) != \
                    K.cjson(K.canonical_record({"kind": "hyperedge", "bindings": [], "evidence": [ne[eid]]})):
                raise K.KHGError("KHG-D013", f"evidence {eid} changed or removed")
        for f in set(old) | set(new):
            if f in K.STORE_FIELDS or f in ("kind", "id", "relation", "status", "status_ref", "bindings", "evidence",
                                            "derived") or f in EDITABLE:
                continue
            if f == "goal" and old["status"] == "goal":
                continue
            if K.cjson(old.get(f)) != K.cjson(new.get(f)):
                raise K.KHGError("KHG-D013", f"field {f} may not change")

    def _post_checks(self, state, batch, *, check_keys=True, disputed_rule=False):
        """Nesting cycles (D008) and the key invariant (KeyCollision). state: the whole state after the write."""
        S = self.S
        graph = {i: [b["value"]["fact"] for b in r.get("bindings", []) if K.vkind(b["value"]) == "fact"]
                 for i, r in state.items() if r.get("kind") == "hyperedge" and S.kind(r["relation"]) != "lifecycle"}
        seen, stack = set(), set()

        def dfs(n):
            if n in stack:
                raise K.KHGError("KHG-D008", f"nesting cycle through {n}")
            if n in seen:
                return
            seen.add(n)
            stack.add(n)
            for m in graph.get(n, []):
                dfs(m)
            stack.discard(n)
        for n in sorted(graph):
            dfs(n)
        if check_keys and "key_constraint" in self.flags:
            cs = K.collisions(S, self._state(), [x for x in batch if x.get("kind") == "hyperedge"], post=state,
                              disputed_rule=disputed_rule)
            if cs:
                raise K.KHGError("KHG-D016", "key invariant", {"collisions": cs})

    def _write(self, recs, t, at_s, actor):
        out = []
        for r in recs:
            r = K.canonical_record(r)  # stores hold records in canonical form (defaults filled, bindings sorted)
            prev = self.v.get(r["id"])
            r["version"] = (prev[-1]["version"] + 1) if prev else 1
            r["recorded_at"] = at_s
            r["recorded_by"] = actor
            self.v.setdefault(r["id"], []).append(r)
            out.append([r["id"], r["version"], "versioned" if prev else "created"])
        return out

    def _receipt(self, rows, at_s, warnings=()):
        return {"records": sorted(rows), "at": at_s, "warnings": list(warnings)}

    def _warnings(self, state, ids):
        pairs = K.possible_only_overlaps(self.S, list(state.values()))
        return [{"code": "KHG-L008", "ids": p} for p in pairs if set(p) & set(ids)]

    # ------------------------------------------------------------------ writes
    def put(self, records, *, actor, at=None, expect=None):
        recs = [records] if isinstance(records, dict) else list(records)
        if len(recs) > 1:
            self.need("atomic_writes")
        for r in recs:
            for fl in self._data_flags(r):
                self.need(fl)
        if expect:
            for i, ver in expect.items():
                cur = self.v.get(i)
                if (cur[-1]["version"] if cur else 0) != ver:
                    raise K.KHGError("KHG-D019", f"expected {i} at version {ver}")
        # classification and status rules (D014, D017)
        state = self._state()
        new_state = dict(state)
        todo, rows_noop = [], []
        for r in recs:
            if r.get("kind") == "hyperedge":
                if r.get("status") == "candidate":
                    raise K.KHGError("KHG-D017", "a candidate never enters a store")
                if r["relation"] in self.S.rel and self.S.kind(r["relation"]) == "lifecycle":
                    raise K.KHGError("KHG-D014", "lifecycle records are written by events only")
            cur = state.get(r["id"])
            if cur is None:
                if r.get("kind") == "hyperedge" and r.get("status") not in ("asserted", "quoted", "goal"):
                    raise K.KHGError("KHG-D014", f"put cannot create a record in status {r.get('status')!r}")
            else:
                if r.get("kind") == "hyperedge" and cur.get("status") != r.get("status"):
                    raise K.KHGError("KHG-D014", "status changes only through events")
                if _same_content(cur, r):
                    rows_noop.append([r["id"], cur["version"], "noop"])
                    continue
            todo.append(r)
            new_state[r["id"]] = r
        for r in todo:
            self._check_record(r, new_state, {x["id"] for x in recs})
            cur = state.get(r["id"])
            if cur is not None:
                self._version_rule(cur, r)
        if not todo:
            return self._receipt(rows_noop, self.clock.now())
        t, at_s = self._at(at)
        self._post_checks(new_state, todo, disputed_rule=True)
        self._check_d011(new_state, {r["id"] for r in todo})
        rows = self._write(todo, t, at_s, actor)
        self._commit_time(t)
        return self._receipt(rows + rows_noop, at_s, self._warnings(self._state(), [r["id"] for r in todo]))

    def apply(self, event, *, actor, at=None):
        op = event.get("op")
        S = self.S
        state = self._state()
        if op == "add_evidence":
            cur = self._target(event["target"], state)
            new = copy.deepcopy(cur)
            new["evidence"] = new.get("evidence", []) + copy.deepcopy(event["evidence"])
            self._version_rule(cur, new)
            t, at_s = self._at(at)
            rows = self._write([_strip_store(new)], t, at_s, actor)
            self._commit_time(t)
            return self._receipt(rows, at_s)
        if op == "end_validity":
            self.need("valid_time")
            cur = self._target(event["target"], state)
            tm = S.time_model(cur["relation"])
            if tm["model"] != "interval":
                raise K.KHGError("KHG-S002", "end_validity needs an interval time model")
            if cur["status"] not in ("asserted", "disputed"):
                raise K.KHGError("KHG-D014", f"end_validity on a {cur['status']} fact")
            new = _strip_store(cur)
            bids = [int(b["bid"][1:]) for b in new["bindings"]]
            nxt = lambda: f"b{max(bids + [0]) + 1}"
            endb = next((b for b in new["bindings"] if b["role"] == tm["end"]), None)
            if endb is None:
                endb = {"bid": nxt(), "role": tm["end"], "value": copy.deepcopy(event["end"])}
                new["bindings"].append(endb)
                bids.append(int(endb["bid"][1:]))
            else:
                endb["value"] = copy.deepcopy(event["end"])
            supports = [endb["bid"]]
            if event.get("end_cause"):
                cb = {"bid": f"b{max(bids) + 1}", "role": "khg:end_cause", "value": copy.deepcopy(event["end_cause"])}
                new["bindings"].append(cb)
                supports.append(cb["bid"])
            evs = copy.deepcopy(event.get("evidence", []))
            for e in evs:
                e.setdefault("supports", supports)
            new["evidence"] = new.get("evidence", []) + evs
            self._check_record(new, state, set())
            self._version_rule(cur, new, allow_novalue_end=True)
            t, at_s = self._at(at)
            st2 = dict(state)
            st2[new["id"]] = new
            self._post_checks(st2, [new])
            rows = self._write([new], t, at_s, actor)
            self._commit_time(t)
            return self._receipt(rows, at_s, self._warnings(self._state(), [new["id"]]))
        if op == "supersede":
            return self._supersede(event, state, actor, at)
        if op == "transition":
            return self._transition(event, state, actor, at)
        raise K.KHGError("KHG-C002", f"event op {op!r}")

    def _target(self, i, state):
        cur = state.get(i)
        if cur is None:
            raise K.KHGError("KHG-D002", f"{i} not found")
        return cur

    def _new_records(self, event, state, *, status_after=None, status_ref=None):
        out = []
        for r in event.get("records", []) or []:
            r = copy.deepcopy(r)
            r.pop("status_ref", None)
            if r.get("status") != "asserted":
                raise K.KHGError("KHG-D014", "event records arrive as asserted")
            if r["id"] in state:
                raise K.KHGError("KHG-D014", f"event record {r['id']} already exists")
            out.append(r)
        return out

    def _lifecycle(self, rel, id, bindings, event):
        rec = {"kind": "hyperedge", "id": id, "relation": rel, "status": "asserted",
               "bindings": [{"bid": f"b{n}", "role": role, "value": {"fact": f}} for n, (role, f) in enumerate(bindings, 1)],
               "evidence": copy.deepcopy(event.get("evidence", []))}
        if event.get("reason") is not None:
            rec["reason"] = event["reason"]
        if event.get("note") is not None:
            rec["note"] = event["note"]
        if rec.get("reason") not in self.S.rel[rel]["reasons"]:
            raise K.KHGError("KHG-S026", f"reason {rec.get('reason')!r} not in {rel} reasons")
        return rec

    def _set_status(self, cur, status, ref):
        new = _strip_store(cur)
        new["status"] = status
        if ref:
            new["status_ref"] = ref
        else:
            new.pop("status_ref", None)
        return new

    def _finish(self, writes, state, actor, at, check_keys=True):
        t, at_s = self._at(at)
        st2 = dict(state)
        for w in writes:
            st2[w["id"]] = w
        self._post_checks(st2, [w for w in writes if w.get("status") == "asserted"], check_keys=check_keys)
        self._check_d012(st2)
        rows = self._write(writes, t, at_s, actor)
        self._commit_time(t)
        return self._receipt(rows, at_s, self._warnings(self._state(), [w["id"] for w in writes]))

    def _check_d011(self, state, ids):
        """SEM-11: a new version of a fact bound by an asserted khg:supersedes record must keep that record's
        constraint (correction: same relation and key digest; duplicate: equal content keys; refinement: refines)."""
        S = self.S
        for r in state.values():
            if r.get("kind") != "hyperedge" or r["relation"] != "khg:supersedes" or r["status"] != "asserted":
                continue
            sing = [b["value"]["fact"] for b in r["bindings"] if b["role"] == "khg:superseding"]
            sed = [b["value"]["fact"] for b in r["bindings"] if b["role"] == "khg:superseded"]
            if not (set(sing) | set(sed)) & ids:
                continue
            for a in (state[i] for i in sing if i in state):
                for b in (state[i] for i in sed if i in state):
                    reason = r.get("reason")
                    if reason == "correction" and (a["relation"] != b["relation"] or K.key_digest(S, a) != K.key_digest(S, b)):
                        raise K.KHGError("KHG-D011", f"{r['id']}: correction across relations or key digests")
                    if reason == "duplicate" and K.content_key(S, a) != K.content_key(S, b):
                        raise K.KHGError("KHG-D011", f"{r['id']}: duplicate needs equal content keys")
                    if reason == "refinement" and not K.fact_refines(S, a, b):
                        raise K.KHGError("KHG-D011", f"{r['id']}: the superseding fact no longer refines")

    def _check_d012(self, state):
        edges = {}
        for r in state.values():
            if r.get("kind") == "hyperedge" and r["relation"] == "khg:supersedes" and r["status"] == "asserted":
                sing = [b["value"]["fact"] for b in r["bindings"] if b["role"] == "khg:superseding"]
                sed = [b["value"]["fact"] for b in r["bindings"] if b["role"] == "khg:superseded"]
                for a in sing:
                    edges.setdefault(a, set()).update(sed)
        seen, stack = set(), set()

        def dfs(n):
            if n in stack:
                raise K.KHGError("KHG-D012", "supersession cycle")
            if n in seen:
                return
            seen.add(n)
            stack.add(n)
            for m in edges.get(n, ()):
                dfs(m)
            stack.discard(n)
        for n in sorted(edges):
            dfs(n)

    def _supersede(self, event, state, actor, at):
        self.need("atomic_writes")
        S = self.S
        new_recs = self._new_records(event, state)
        st = dict(state)
        for r in new_recs:
            for fl in self._data_flags(r):
                self.need(fl)
            st[r["id"]] = r
        for r in new_recs:
            self._check_record(r, st, set())
        sed = [self._target(i, state) for i in event["superseded"]]
        for f in sed:
            if f["status"] not in ("asserted", "disputed"):
                raise K.KHGError("KHG-D014", f"{f['id']} is {f['status']}")
        sing_ids = list(event.get("superseding", [])) + [r["id"] for r in new_recs]
        sing = [st[i] for i in sing_ids]
        for f in sing:
            if f["status"] != "asserted":
                raise K.KHGError("KHG-D011", f"superseding fact {f['id']} is not asserted")
        reason = event.get("reason")
        for a in sing:
            for b in sed:
                if reason == "correction" and (a["relation"] != b["relation"] or K.key_digest(S, a) != K.key_digest(S, b)):
                    raise K.KHGError("KHG-D011", "correction across relations or key digests")
                if reason == "duplicate" and K.content_key(S, a) != K.content_key(S, b):
                    raise K.KHGError("KHG-D011", "duplicate needs equal content keys")
                if reason == "refinement" and not K.fact_refines(S, a, b):
                    raise K.KHGError("KHG-D011", "refinement needs the superseding fact to refine the superseded one")
        lc = self._lifecycle("khg:supersedes", event["id"],
                             [("khg:superseding", i) for i in sing_ids] + [("khg:superseded", i) for i in event["superseded"]],
                             event)
        writes = new_recs + [lc] + [self._set_status(f, "superseded", event["id"]) for f in sed]
        return self._finish(writes, state, actor, at)

    def _transition(self, event, state, actor, at):
        S = self.S
        to = event["to"]
        targets = [self._target(i, state) for i in event["targets"]]
        if to == "disputed":
            self.need("atomic_writes")
            new_recs = self._new_records(event, state)
            for f in targets:
                if f["status"] not in ("asserted", "disputed") or S.kind(f["relation"]) == "lifecycle":
                    raise K.KHGError("KHG-D014", f"{f['id']} {f['status']} -> disputed")
            st = dict(state)
            for r in new_recs:
                st[r["id"]] = r
            for r in new_recs:
                self._check_record(r, st, set())
            ids = [f["id"] for f in targets] + [r["id"] for r in new_recs]
            lc = self._lifecycle("khg:disputes", event["id"], [("khg:disputed", i) for i in ids], event)
            writes = [lc] + [self._set_status(f, "disputed", event["id"]) for f in targets] + \
                     [dict(self._set_status(r, "disputed", event["id"])) for r in new_recs]
            return self._finish(writes, state, actor, at)
        if to == "retracted":
            if event.get("id") is None:
                raise K.KHGError("KHG-C010", "a retraction names its khg:retracts record")
            self.need("atomic_writes")
            writes, restored, extra_targets = [], [], []
            for f in targets:
                if S.kind(f["relation"]) == "lifecycle":
                    if f["relation"] == "khg:retracts" or f["status"] != "asserted":
                        raise K.KHGError("KHG-D014", f"{f['id']} cannot be retracted")
                    role = {"khg:supersedes": "khg:superseded", "khg:disputes": "khg:disputed"}[f["relation"]]
                    for b in f["bindings"]:
                        if b["role"] == role:
                            x = state[b["value"]["fact"]]
                            if x.get("status_ref") == f["id"]:
                                restored.append(self._set_status(x, "asserted", None))
                    if f["relation"] == "khg:supersedes":
                        sing = [state[b["value"]["fact"]] for b in f["bindings"] if b["role"] == "khg:superseding"]
                        how = event.get("resolve_superseding")
                        if how == "retract":
                            extra_targets += sing
                        elif how == "dispute":
                            did = event["dispute_id"]
                            ids = [x["id"] for x in sing] + [x["id"] for x in restored]
                            writes.append(self._lifecycle("khg:disputes", did, [("khg:disputed", i) for i in ids],
                                                          {"reason": "key_conflict", "evidence": event.get("evidence", [])}))
                            restored = [self._set_status(x, "disputed", did) for x in restored] + \
                                       [self._set_status(x, "disputed", did) for x in sing]
                elif f["status"] not in ("asserted", "disputed", "goal", "quoted"):
                    raise K.KHGError("KHG-D014", f"{f['id']} {f['status']} -> retracted")
            all_targets = targets + extra_targets
            lc = self._lifecycle("khg:retracts", event["id"], [("khg:retracted", f["id"]) for f in all_targets], event)
            writes += [lc] + [self._set_status(f, "retracted", event["id"]) for f in all_targets] + restored
            return self._finish(writes, state, actor, at)
        if to == "asserted":
            writes = []
            for f in targets:
                if f["status"] == "disputed" or f["status"] == "quoted":
                    new = self._set_status(f, "asserted", None)
                elif f["status"] == "goal":
                    if any(K.vkind(b["value"]) == "unbound" for b in f["bindings"]):
                        raise K.KHGError("KHG-C005", "a goal with an unbound slot cannot become asserted")
                    new = self._set_status(f, "asserted", None)
                    new.pop("goal", None)
                else:
                    raise K.KHGError("KHG-D014", f"{f['id']} {f['status']} -> asserted")
                evs = copy.deepcopy(event.get("evidence", []))
                for e in evs:
                    e.setdefault("supports", [])
                new["evidence"] = new.get("evidence", []) + evs
                writes.append(new)
            return self._finish(writes, state, actor, at)
        raise K.KHGError("KHG-D014", f"no transition to {to!r}")

    # ------------------------------------------------------------------ bulk load
    def load(self, container, *, at=None, on_missing="raise"):
        hdr = container["header"]
        if hdr.get("format") != "khg-record/1.0.0":
            raise K.KHGError("KHG-V001", f"format {hdr.get('format')!r}")
        self.header = {k: copy.deepcopy(v) for k, v in hdr.items() if k not in ("content", "as_at")}
        skipped, n = [], 0
        t_default, at_default = self._at(at)
        recs = container["records"]
        drop = set()
        for r in recs:
            missing = [f for f in self._data_flags(r) if f not in self.flags]
            if missing:
                if on_missing == "raise":
                    raise CapabilityMissing(missing[0])
                drop.add(r["id"])
        changed = True
        while changed:  # close over references to dropped records
            changed = False
            for r in recs:
                if r["id"] in drop or r.get("kind") != "hyperedge":
                    continue
                refs = {b["value"]["fact"] for b in r["bindings"] if K.vkind(b["value"]) == "fact"}
                if r.get("status_ref"):
                    refs.add(r["status_ref"])
                if refs & drop:
                    drop.add(r["id"])
                    changed = True
        latest = t_default
        for r in recs:
            if r["id"] in drop:
                skipped.append(r["id"])
                continue
            r = K.canonical_record(r)
            r.setdefault("version", 1)
            r.setdefault("recorded_at", at_default)
            r.setdefault("recorded_by", "load")
            tt = _tx(r["recorded_at"])
            if self.latest is not None and tt <= self.latest:
                raise K.KHGError("KHG-D018", "loaded versions must be later than the store's latest")
            latest = max(latest, tt)
            self.v.setdefault(r["id"], []).append(r)
            n += 1
        for i in self.v:
            self.v[i].sort(key=lambda x: x["version"])
        self._commit_time(latest)
        return {"records": len(self.v), "versions": n, "skipped": sorted(skipped)}

    # ------------------------------------------------------------------ reads
    def get(self, id, *, as_at=None, version=None):
        if as_at is not None or version is not None:
            self.need("transaction_time")
        if version is not None:
            return next((copy.deepcopy(x) for x in self.v.get(id, []) if x["version"] == version), None)
        c = self.current(id, as_at)
        return copy.deepcopy(c) if c else None

    def history(self, id):
        return copy.deepcopy(self.v.get(id, []))

    def get_many(self, ids, *, as_at=None):
        out = {}
        for i in ids:
            r = self.get(i, as_at=as_at)
            if r is not None:
                out[i] = r
        return dict(sorted(out.items()))

    def _passes(self, r, w: Where):
        if r.get("kind") != "hyperedge":
            return False
        if r["status"] not in w.status or r.get("rank", "normal") not in w.rank or \
                r.get("visibility", "visible") not in w.visibility:
            return False
        kind = "lifecycle" if self.S.kind(r["relation"]) == "lifecycle" else "fact"
        if kind not in w.kinds:
            return False
        if w.as_of is not None:
            t = K.parse_instant(w.as_of)
            b = K.bounds(self.S, r)
            if w.valid_mode == "definite":
                return b["s_hi"] <= t < b["e_lo"]
            return b["s_lo"] <= t < b["e_hi"]
        return True

    def _scan(self, w: Where):
        if w.as_of is not None or w.valid_mode != "definite":
            self.need("valid_time")
        if w.as_at is not None:
            self.need("transaction_time")
        st = self._state(w.as_at)
        return [r for i, r in sorted(st.items()) if self._passes(r, w)]

    @staticmethod
    def _page(rs, limit, after):
        if after is not None:
            rs = [r for r in rs if r["id"] > after]
        if limit is not None:
            rs = rs[:limit]
        return [copy.deepcopy(r) for r in rs]

    def incident(self, node, *, role=None, relation=None, where=None, limit=None, after=None):
        w = where or Where()
        out = []
        for r in self._scan(w):
            if relation and r["relation"] != relation:
                continue
            for b in r["bindings"]:
                v = b["value"]
                k = K.vkind(v)
                if k in ("entity", "fact") and v[k] == node and (role is None or b["role"] == role):
                    out.append(r)
                    break
        return self._page(out, limit, after)

    def degree(self, node, *, role=None, relation=None, where=None):
        return len(self.incident(node, role=role, relation=relation, where=where))

    @staticmethod
    def _pmatch(p, b):
        if p["role"] != b["role"]:
            return False
        if "position" in p and p["position"] != b.get("position"):
            return False
        v = p["value"]
        if v == {"any": True}:
            return True
        if v == {"any_unbound": True}:
            return K.vkind(b["value"]) == "unbound"
        if K.vkind(b["value"]) == "unbound":
            return False
        return K.values_equal(v, b["value"])

    def find(self, relation, pattern, *, match="at_least", where=None, limit=None, after=None):
        w = where or Where()
        out = []
        for r in self._scan(w):
            if r["relation"] != relation:
                continue
            bs = r["bindings"]
            if match == "exact" and len(pattern) != len(bs):
                continue
            if K._match(lambda i, j: self._pmatch(pattern[i], bs[j]), len(pattern), len(bs)):
                out.append(r)
        return self._page(out, limit, after)

    def find_by_key(self, relation, key, *, where=None):
        k = self.S.key(relation)
        if not k or sorted(p["role"] for p in key) != sorted(k["roles"]):
            raise ValueError("find_by_key binds exactly the key roles")
        probe = {"kind": "hyperedge", "relation": relation,
                 "bindings": [{"bid": f"b{n}", "role": p["role"], "value": p["value"]} for n, p in enumerate(key, 1)]}
        kd = K.key_digest(self.S, probe)
        return [copy.deepcopy(r) for r in self._scan(where or Where()) if r["relation"] == relation
                and K.key_digest(self.S, r) == kd]

    def supersession_walk(self, id, *, direction="forward", as_at=None):
        if as_at is not None:
            self.need("transaction_time")
        st = self._state(as_at)
        sups = [r for r in st.values() if r.get("kind") == "hyperedge" and r["relation"] == "khg:supersedes"
                and r["status"] == "asserted"]
        frm, to = ("khg:superseded", "khg:superseding") if direction == "forward" else ("khg:superseding", "khg:superseded")
        steps, seen, frontier, depth = [], {id}, [id], 0
        reached = [id]
        while frontier:
            depth += 1
            nxt = []
            for f in frontier:
                for s in sorted(sups, key=lambda x: x["id"]):
                    if any(b["role"] == frm and b["value"]["fact"] == f for b in s["bindings"]):
                        for b in s["bindings"]:
                            if b["role"] == to:
                                g = b["value"]["fact"]
                                steps.append({"depth": depth, "via": s["id"], "reason": s.get("reason"), "from": f, "to": g})
                                if g not in seen:
                                    seen.add(g)
                                    nxt.append(g)
                                    reached.append(g)
            frontier = sorted(nxt)

        def outgoing(f):
            return any(any(b["role"] == frm and b["value"]["fact"] == f for b in s["bindings"]) for s in sups)
        terminal = [{"id": f, "status": st[f]["status"] if f in st else None} for f in sorted(reached) if not outgoing(f)]
        return {"start": id, "direction": direction, "steps": steps, "terminal": terminal}

    def iter_records(self, *, content="snapshot", as_at=None):
        if content == "history":
            self.need("history_export")
            for i in sorted(self.v):
                for x in self.v[i]:
                    if as_at is None or _tx(x["recorded_at"]) <= _tx(as_at):
                        yield copy.deepcopy(x)
            return
        if as_at is not None:
            self.need("transaction_time")
        for i, r in sorted(self._state(as_at).items()):
            yield copy.deepcopy(r)

    def export(self, format="khg-json", *, content="snapshot", as_at=None, relations=None, header=None):
        recs = list(self.iter_records(content=content, as_at=as_at))
        if header is not None:
            hdr = copy.deepcopy(header)
        elif self.header is not None:
            hdr = copy.deepcopy(self.header)
        else:
            ents = {r["id"] for r in recs if r["kind"] == "entity"}
            refd = {b["value"]["entity"] for r in recs if r["kind"] == "hyperedge" for b in r["bindings"]
                    if K.vkind(b["value"]) == "entity"}
            hdr = {"kind": "header", "format": "khg-record/1.0.0", "document_id": f"store:{self.store_id}",
                   "schema": {"id": self.S.doc["id"], "version": self.S.doc["version"], "sha256": self.S.sha256()},
                   "complete": refd <= ents}
        hdr["content"] = content
        if as_at is not None:
            hdr["as_at"] = as_at
        doc = K.canonical_doc({"header": hdr, "records": recs})
        order = {"kind": 0, "format": 1, "document_id": 2, "schema": 3, "content": 4, "as_at": 5, "complete": 6}
        doc["header"] = dict(sorted(doc["header"].items(), key=lambda kv: order.get(kv[0], 9)))
        if format == "khg-json":
            return doc
        if format == "khg-jsonl":
            return "".join(K.cjson(x) + "\n" for x in [doc["header"]] + doc["records"])
        if format == "hif":
            return K.c1_to_hif(doc, self.S, relations=relations)
        raise ValueError(format)


def compare_containers(a, b, *, ignore=("version", "recorded_at", "recorded_by"),
                       header_ignore=("created_at", "generator")):
    """Structural differences between two containers: header fields (minus header_ignore), then records keyed by id
    (and version for history containers), each record compared without the ignored store fields."""
    diffs = []
    ha = {k: v for k, v in a["header"].items() if k not in header_ignore}
    hb = {k: v for k, v in b["header"].items() if k not in header_ignore}
    for k in sorted(set(ha) | set(hb)):
        if K.cjson(ha.get(k)) != K.cjson(hb.get(k)):
            diffs.append({"where": f"header.{k}", "a": ha.get(k), "b": hb.get(k)})
    hist = a["header"].get("content") == "history"

    def keyed(doc):
        out = {}
        for r in doc["records"]:
            r = K.canonical_record(r)
            key = (r.get("id"), r.get("version") if hist else None)
            for f in ignore:
                r.pop(f, None)
            out[key] = r
        return out
    ka, kb = keyed(a), keyed(b)
    for k in sorted(set(ka) | set(kb), key=lambda x: (x[0] or "", x[1] or 0)):
        if k not in ka or k not in kb or K.cjson(ka[k]) != K.cjson(kb[k]):
            diffs.append({"where": f"record {k[0]}", "a": ka.get(k), "b": kb.get(k)})
    return diffs
