"""Reference in-memory store for C2 (khg-store/1.0.0). Prototype for design C, section 6.

Semantics (normative in the design):
  * versions are immutable; put() of changed content appends version n+1; identical content is a no-op
  * reads take Where(status, rank, visibility, as_of, as_at); defaults: status {asserted}, rank {preferred, normal},
    visibility {visible}, as_of None (no valid-time filter), as_at None (latest versions)
  * results are ordered by id (code-point order); pagination with limit + after=<last id>
  * key collisions are never resolved silently: put() raises KeyCollision(conflicts, suggested=<policy>)
  * status changes go through apply(event); 'superseded' only through the supersede event
"""
from __future__ import annotations

import copy
import dataclasses
from collections import defaultdict

import c1
import semantic

INTERFACE = "khg-store/1.0.0"
CAPABILITIES = frozenset({"temporal_valid", "temporal_tx", "nesting", "ordered_roles", "special_values",
                          "literal_values", "key_index", "atomic_events", "history_export"})


class StoreError(Exception):
    code = "STORE"

    def __init__(self, msg, **info):
        super().__init__(msg)
        self.info = info


class ValidationFailed(StoreError):
    code = "VALIDATION"


class KeyCollision(StoreError):
    code = "KEY_COLLISION"


class TransitionError(StoreError):
    code = "TRANSITION"


class NotFound(StoreError):
    code = "NOT_FOUND"


class EntityConflict(StoreError):
    code = "ENTITY_CONFLICT"


@dataclasses.dataclass(frozen=True)
class Where:
    status: frozenset = frozenset({"asserted"})
    rank: frozenset = frozenset({"preferred", "normal"})
    visibility: frozenset = frozenset({"visible"})
    as_of: str | None = None
    as_at: str | None = None

    @staticmethod
    def from_json(d):
        d = dict(d or {})
        for k in ("status", "rank", "visibility"):
            if k in d:
                d[k] = frozenset(d[k])
        return Where(**d)


DEFAULT = Where()
ALLOWED = {  # (from, to) status transitions through apply({"op": "transition"})
    ("asserted", "disputed"), ("asserted", "retracted"),
    ("disputed", "asserted"), ("disputed", "retracted"),
    ("goal", "asserted"), ("goal", "retracted"),
}
VOLATILE = ("version", "recorded_at", "recorded_by", "change")


def _content(r):
    return {k: v for k, v in r.items() if k not in VOLATILE}


class MemoryStore:
    interface_version = INTERFACE
    record_format = c1.RECORD_FORMAT
    capabilities = CAPABILITIES

    def __init__(self, schemas, clock):
        self.schemas = {f"{s['id']}/{s['version']}": c1.Schema(s) for s in schemas}
        self.clock = clock
        self.versions = defaultdict(list)       # hyperedge id -> [versions]
        self.entities = {}
        self.sups = {}                          # supersession id -> record
        self.by_node = defaultdict(set)         # entity or hyperedge id -> hyperedge ids (any version)
        self.by_relation = defaultdict(set)
        self.by_key = defaultdict(set)          # (relation, key digest) -> ids
        self.sup_fwd = defaultdict(list)        # superseded id -> supersession ids
        self.sup_bwd = defaultdict(list)        # superseding id -> supersession ids

    # ------------------------------------------------------------------ writes
    def put(self, record, *, actor="store", at=None, _batch=None):
        k = record.get("kind")
        if k == "entity":
            return self._put_entity(record)
        if k != "hyperedge":
            raise ValidationFailed(f"put() takes entity or hyperedge records, got {k}")
        if record["status"] in ("candidate", "superseded"):
            raise TransitionError(f"status {record['status']} cannot be put (queue / supersede event)")
        schema = self.schemas.get(record.get("schema")) or next(iter(self.schemas.values()))
        rec = {k: v for k, v in copy.deepcopy(record).items() if k not in VOLATILE}
        rec.setdefault("schema", schema.ref)
        try:
            rec = c1.normalise(rec, schema)
        except (KeyError, ValueError) as e:
            raise ValidationFailed(f"cannot normalise: {e}")
        errs = [f for f in semantic.check_hyperedge(rec, schema, self._types) if f["severity"] == "error"]
        errs += self._ref_errors(rec, _batch or {})
        if errs:
            raise ValidationFailed("record rejected", findings=errs)
        cur = self._current(rec["id"])
        if cur is not None:
            if _content(cur) == _content(rec):
                return {"id": rec["id"], "version": cur["version"], "created": False}
            if cur["status"] != rec["status"]:
                raise TransitionError(f"put() cannot change status {cur['status']} -> {rec['status']}; use apply()")
        self._check_key(rec)
        return self._append(rec, {"op": "put"}, actor, at)

    def put_many(self, records, *, actor="store"):
        batch = {r["id"]: r for r in records}
        out = []
        for r in sorted(records, key=lambda r: (r["kind"] != "entity", r["id"])):
            out.append(self.put(r, actor=actor, _batch=batch))
        return out

    def _put_entity(self, e):
        cur = self.entities.get(e["id"])
        if cur is None:
            self.entities[e["id"]] = copy.deepcopy(e)
            return {"id": e["id"], "created": True}
        if cur != e:
            raise EntityConflict(f"entity {e['id']} exists with different content (entities are immutable in 1.0)")
        return {"id": e["id"], "created": False}

    def _append(self, rec, change, actor, at=None):
        vs = self.versions[rec["id"]]
        rec = copy.deepcopy(rec)
        rec["version"] = vs[-1]["version"] + 1 if vs else 1
        rec["recorded_at"] = at or self.clock()
        rec["recorded_by"] = actor
        rec["change"] = change
        self._index(rec)
        return {"id": rec["id"], "version": rec["version"], "created": True}

    def _index(self, rec):
        """Append one version and update the indexes; versions and transaction times must increase per id."""
        vs = self.versions[rec["id"]]
        if vs and (rec["version"] <= vs[-1]["version"] or rec["recorded_at"] < vs[-1]["recorded_at"]):
            raise ValidationFailed(f"C-TX-ORDER: {rec['id']} v{rec['version']} at {rec['recorded_at']} after "
                                   f"v{vs[-1]['version']} at {vs[-1]['recorded_at']}")
        vs.append(rec)
        self.by_relation[rec["relation"]].add(rec["id"])
        for b in rec["bindings"]:
            v = b["value"]
            if "entity" in v or "hyperedge" in v:
                self.by_node[v.get("entity") or v.get("hyperedge")].add(rec["id"])
        if rec["keys"].get("key"):
            self.by_key[(rec["relation"], rec["keys"]["key"])].add(rec["id"])

    def _add_sup(self, s):
        self.sups[s["id"]] = s
        self.sup_fwd[s["superseded"]].append(s["id"])
        self.sup_bwd[s["superseding"]].append(s["id"])

    def load(self, records):
        """Bulk import of a canonical container as it is (C2 load): version, recorded_at, recorded_by and change are
        kept, nothing is renumbered or re-validated (validate the file first); a snapshot keeps only its versions."""
        import time
        t0 = time.perf_counter()
        n_rec = n_ver = 0
        for r in records:
            k = r["kind"]
            if k == "header":
                if not r["format"].startswith("khg-record/1."):
                    raise ValidationFailed(f"R-FORMAT: unknown major version {r['format']}")
                continue
            if k == "relation-schema":
                ref = f"{r['id']}/{r['version']}"
                if ref in self.schemas and self.schemas[ref].doc != r:
                    raise ValidationFailed(f"schema {ref} differs from the one the store holds")
                self.schemas.setdefault(ref, c1.Schema(r))
                continue
            n_rec += 1
            if k == "entity":
                self._put_entity(r)
            elif k == "hyperedge":
                self._index(copy.deepcopy(r))
                n_ver += 1
            elif k == "supersession":
                self._add_sup(copy.deepcopy(r))
            else:
                raise ValidationFailed(f"R-KIND: {k}")
        return {"records": n_rec, "versions": n_ver, "seconds": time.perf_counter() - t0}

    def _types(self, i):
        e = self.entities.get(i)
        return e["types"] if e else None

    def _ref_errors(self, rec, batch):
        out = []
        for b in rec["bindings"]:
            v = b["value"]
            if "entity" in v and v["entity"] not in self.entities and v["entity"] not in batch:
                out.append(semantic.F("C-ENTITY-REF", rec["id"], f"unknown entity {v['entity']}"))
            if "hyperedge" in v and not self.versions.get(v["hyperedge"]) and v["hyperedge"] not in batch:
                out.append(semantic.F("C-HYPEREDGE-REF", rec["id"], f"unknown hyperedge {v['hyperedge']}"))
        return out

    def _check_key(self, rec, ignore=()):
        kd = rec["keys"].get("key")
        if not kd or rec["status"] != "asserted":
            return
        S = self.schemas[rec["schema"]]
        key = S.relations[rec["relation"]]["key"]
        conflicts = []
        for i in sorted(self.by_key[(rec["relation"], kd)]):
            if i == rec["id"] or i in ignore:
                continue
            o = self._current(i)
            if o["status"] == "asserted" and o["keys"].get("key") == kd and (
                    not key["temporal"] or semantic._overlap(o.get("valid_time"), rec.get("valid_time"))):
                conflicts.append(i)
        if conflicts:
            raise KeyCollision(f"key collision on {rec['relation']}", conflicts=conflicts,
                               suggested=key["on_collision"])

    def apply(self, ev, *, actor=None):
        actor = actor or ev.get("actor", "store")
        op = ev["op"]
        at = ev.get("at") or self.clock()
        if op == "transition":
            cur = self._need(ev["target"])
            if (cur["status"], ev["to"]) not in ALLOWED:
                raise TransitionError(f"{cur['status']} -> {ev['to']} not allowed")
            new = _content(cur)
            new["status"] = ev["to"]
            if ev["to"] == "asserted":
                errs = [f for f in semantic.check_hyperedge(new, self.schemas[new["schema"]], self._types)
                        if f["severity"] == "error"]
                if errs:
                    raise ValidationFailed("cannot assert", findings=errs)
                self._check_key(new)
            return self._append(new, {"op": "transition", "reason": ev.get("reason", "")}, actor, at)
        if op == "end_validity":
            cur = self._need(ev["target"])
            S = self.schemas[cur["schema"]]
            new = _content(cur)
            for f in ("arity", "keys"):
                new.pop(f, None)
            for b in new["bindings"]:
                b.pop("slot", None)
            vt = dict(new.pop("valid_time", {}) or {})
            to_role = S.time_model.get("to_role")
            if (new["relation"], to_role) in S.usage:     # time bindings stay the source of truth
                new["bindings"] = [b for b in new["bindings"] if b["role"] != to_role]
                new["bindings"].append({"bid": ev.get("bid", "b-end"), "role": to_role,
                                        "value": {"literal": ev["to"], "datatype": "time",
                                                  "precision": c1.granularity(ev["to"])}})
            else:
                vt["to"] = ev["to"]
                new["valid_time"] = {k: v for k, v in vt.items() if k != "end_cause"}
            new = c1.normalise(new, S)
            if ev.get("end_cause"):
                new["valid_time"]["end_cause"] = ev["end_cause"]
            if new.get("valid_time") and "from" in new["valid_time"] and \
                    c1.lower_instant(new["valid_time"]["from"]) >= c1.lower_instant(ev["to"]):
                raise ValidationFailed("valid_time.to must be after valid_time.from")
            return self._append(new, {"op": "end_validity", "reason": ev.get("reason", "")}, actor, at)
        if op == "add_evidence":
            cur = self._need(ev["target"])
            new = _content(cur)
            have = {e["eid"] for e in new.get("evidence", [])}
            add = [e for e in ev["evidence"] if e["eid"] not in have]
            new["evidence"] = new.get("evidence", []) + copy.deepcopy(add)
            new = c1.normalise(new, self.schemas[new["schema"]])
            return self._append(new, {"op": "add_evidence"}, actor, at)
        if op == "supersede":
            # atomic: validate everything first, then write
            new_rec = ev.get("record")
            olds = [self._need(i) for i in ev["superseded"]]
            for o in olds:
                if o["status"] not in ("asserted", "disputed"):
                    raise TransitionError(f"{o['id']} is {o['status']}, cannot be superseded")
            sup_id = ev["id"]
            if new_rec is not None:
                # the new record may collide with the ones it supersedes; that is the point
                rec = c1.normalise(new_rec, self.schemas.get(new_rec.get("schema")) or next(iter(self.schemas.values())))
                self._check_key(rec, ignore={o["id"] for o in olds})
                superseding = rec["id"]
            else:
                superseding = ev["superseding"]
                self._need(superseding)
            if self._reaches(superseding, {o["id"] for o in olds}):
                raise TransitionError("supersession would create a cycle")
            results = []
            if new_rec is not None:
                cur = self._current(rec["id"])
                if cur is None:
                    results.append(self._append(rec, {"op": "put"}, actor, at))
            for k, o in enumerate(olds):
                sid = sup_id if len(olds) == 1 else f"{sup_id}-{k + 1}"
                s = {"kind": "supersession", "id": sid, "superseded": o["id"], "superseding": superseding,
                     "reason": ev["reason"], "recorded_at": at, "recorded_by": actor,
                     "evidence": copy.deepcopy(ev["evidence"])}
                if ev.get("reason_detail"):
                    s["reason_detail"] = ev["reason_detail"]
                self._add_sup(s)
                new = _content(o)
                new["status"] = "superseded"
                new["superseded_by"] = sorted(set(new.get("superseded_by", [])) | {superseding})
                results.append(self._append(new, {"op": "supersede", "ref": sid}, actor, at))
            return results
        raise StoreError(f"unknown op {op}")

    def _reaches(self, start, targets):
        """Would linking start -> targets create a cycle? True if some target already (transitively) supersedes start."""
        stack, seen = list(targets), set()
        while stack:
            x = stack.pop()
            if x == start:
                return True
            if x in seen:
                continue
            seen.add(x)
            stack.extend(self.sups[s]["superseded"] for s in self.sup_bwd.get(x, []))
        return False

    # ------------------------------------------------------------------ reads
    def _current(self, i, as_at=None):
        vs = self.versions.get(i)
        if not vs:
            return None
        if as_at is None:
            return vs[-1]
        ok = [v for v in vs if v["recorded_at"] <= as_at]
        return ok[-1] if ok else None

    def _need(self, i):
        cur = self._current(i)
        if cur is None:
            raise NotFound(i)
        return cur

    def get(self, i, *, as_at=None, version=None):
        if i in self.entities:
            return copy.deepcopy(self.entities[i])
        if i in self.sups:
            s = self.sups[i]
            return copy.deepcopy(s) if as_at is None or s["recorded_at"] <= as_at else None
        if version is not None:
            v = next((v for v in self.versions.get(i, []) if v["version"] == version), None)
            return copy.deepcopy(v) if v else None
        cur = self._current(i, as_at)
        return copy.deepcopy(cur) if cur else None

    def history(self, i):
        return [copy.deepcopy(v) for v in self.versions.get(i, [])]

    def _passes(self, r, w):
        if r["status"] not in w.status or r["rank"] not in w.rank or r["visibility"] not in w.visibility:
            return False
        if w.as_of is not None:
            vt = r.get("valid_time") or {}
            t = c1.lower_instant(w.as_of)
            if "from" in vt and c1.lower_instant(vt["from"]) > t:
                return False
            if "to" in vt and c1.lower_instant(vt["to"]) <= t:
                return False
        return True

    def _page(self, ids, limit, after):
        ids = sorted(ids)
        if after is not None:
            ids = [i for i in ids if i > after]
        return ids if limit is None else ids[:limit]

    def incident(self, node, *, role=None, relation=None, where=DEFAULT, limit=None, after=None):
        out = []
        for i in sorted(self.by_node.get(node, ())):
            r = self._current(i, where.as_at)
            if r is None or (relation and r["relation"] != relation) or not self._passes(r, where):
                continue
            if any((b["value"].get("entity") == node or b["value"].get("hyperedge") == node)
                   and (role is None or b["role"] == role) for b in r["bindings"]):
                out.append(r)
        keep = set(self._page([r["id"] for r in out], limit, after))
        return [copy.deepcopy(r) for r in out if r["id"] in keep]

    def degree(self, node, **kw):
        return len(self.incident(node, **kw))

    def find(self, relation, pattern, *, match="at_least", where=DEFAULT, limit=None, after=None):
        want = [(p["role"], c1.cjson(p["value"])) for p in pattern]
        out = []
        for i in sorted(self.by_relation.get(relation, ())):
            r = self._current(i, where.as_at)
            if r is None or not self._passes(r, where):
                continue
            have = [(b["role"], c1.cjson(b["value"])) for b in r["bindings"]]
            if _multiset_contains(have, want) and (match == "at_least" or len(have) == len(want)):
                out.append(r)
        keep = set(self._page([r["id"] for r in out], limit, after))
        return [copy.deepcopy(r) for r in out if r["id"] in keep]

    def find_by_key(self, relation, key_bindings, *, where=DEFAULT):
        S = next(iter(self.schemas.values()))
        roles = S.key_roles(relation)
        if {b["role"] for b in key_bindings} != roles:
            raise StoreError(f"find_by_key needs exactly the key roles {sorted(roles)}")
        probe = {"relation": relation, "bindings": [dict(b, slot="core") for b in key_bindings]}
        kd = c1.key_digest(probe, roles)
        out = []
        for i in sorted(self.by_key.get((relation, kd), ())):
            r = self._current(i, where.as_at)
            if r is not None and r["keys"].get("key") == kd and self._passes(r, where):
                out.append(copy.deepcopy(r))
        return out

    def supersessions(self, i, direction="forward", as_at=None):
        ids = (self.sup_fwd if direction == "forward" else self.sup_bwd).get(i, [])
        return [copy.deepcopy(self.sups[s]) for s in ids if as_at is None or self.sups[s]["recorded_at"] <= as_at]

    def supersession_walk(self, i, *, direction="forward", as_at=None):
        steps, frontier, seen, depth = [], [i], {i}, 0
        while frontier:
            depth += 1
            nxt = []
            for x in frontier:
                for s in sorted(self.supersessions(x, direction, as_at), key=lambda s: (s["recorded_at"], s["id"])):
                    y = s["superseding"] if direction == "forward" else s["superseded"]
                    steps.append({"depth": depth, "via": s["id"], "reason": s["reason"], "from": x, "to": y})
                    if y not in seen:
                        seen.add(y)
                        nxt.append(y)
            frontier = sorted(nxt)
        reached = {st["to"] for st in steps} | {i}
        terminal = sorted(x for x in reached if not self.supersessions(x, direction, as_at))
        return {"start": i, "direction": direction, "steps": steps, "terminal": terminal}

    # ------------------------------------------------------------------ export
    def iter_records(self, *, content="snapshot", where=None, header=None):
        hdr = dict(header or {})
        hdr.update({"kind": "header", "format": c1.RECORD_FORMAT, "content": content,
                    "schemas": [{"id": s.doc["id"], "version": s.doc["version"], "sha256": c1.sha256_hex(s.doc)}
                                for s in self.schemas.values()]})
        yield hdr
        for s in sorted(self.schemas.values(), key=lambda s: s.ref):
            yield copy.deepcopy(s.doc)
        for i in sorted(self.entities):
            yield copy.deepcopy(self.entities[i])
        for i in sorted(self.versions):
            if content == "history":
                yield from (copy.deepcopy(v) for v in self.versions[i])
            else:
                r = self._current(i, where.as_at if where else None)
                if r is not None and (where is None or self._passes(r, where)):
                    yield copy.deepcopy(r)
        for i in sorted(self.sups):
            yield copy.deepcopy(self.sups[i])

    def export(self, fmt="khg-jsonl", **kw):
        recs = list(self.iter_records(**kw))
        if fmt == "khg-jsonl":
            return "".join(c1.cjson(r) + "\n" for r in recs)
        if fmt == "hif":
            import hif_codec
            return hif_codec.to_hif(recs)
        raise StoreError(f"unknown export format {fmt}")


def _multiset_contains(have, want):
    from collections import Counter
    h, w = Counter(have), Counter(want)
    return all(h[k] >= n for k, n in w.items())


class TickClock:
    """Deterministic clock for tests: each call advances one second from a start instant."""

    def __init__(self, start="2026-09-23T10:00:00Z"):
        import datetime as dt
        self.t = dt.datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")

    def __call__(self):
        import datetime as dt
        s = self.t.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.t += dt.timedelta(seconds=1)
        return s
