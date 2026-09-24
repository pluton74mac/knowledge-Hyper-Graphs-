"""The write path of ``MemoryStore``: the checks every write runs, in the order of DESIGN §6.2, then the commit.

A write collects its records in a ``Pending`` (canonical form, without store fields; the post-state is the store
overlaid with them). The operation checks its own preconditions first (capability, ``NotFound``, D014); then:

1. record validation: layers C and S on every record written (``ValidationError``);
2. the version rule on new versions (D013, ``VersionError``);
3. references: every new or changed entity and fact value resolves in the post-state (D002) and names no entity
   with ``redirect_to`` (D020); and, for events, the lifecycle pointers (D010);
4. nesting cycles (D008);
5. the key invariant and, for ``put``, the disputed-key rule (D016, ``KeyCollision``), on the key groups the write
   touches; a write that breaks the invariant without an incoming asserted fact taking part (retracting the only
   preferred fact of a key while two normal ones hold) raises too, with ``info["violations"]``;
6. supersession constraints (D011) and cycles (D012);
7. transaction time (D018); then every record is written at one ``recorded_at``.

Temporal keys and L008 need ``valid_time`` beside ``key_constraint``: without it only non-temporal keys are
checked (§6.3). Layer C runs fastjsonschema first and jsonschema only to list every finding of a refused record.
"""
from __future__ import annotations

from typing import Any, Iterable, Iterator, Mapping

from ..errors import KeyCollision, ValidationError, VersionError, make_finding
from ..record import key_digest, keys, lifecycle, normalize
from ..record.canonical import STORE_FIELDS
from ..schema import LIFECYCLE_RELATIONS
from ..validate.layers import c as layer_c
from ..validate.layers import s as layer_s
from ._table import bound_nodes
from .clocks import format_timestamp, parse_timestamp
from .protocol import Receipt

__all__ = ["Pending", "WriteMixin", "fail"]

_SAFE = (ValueError, TypeError, KeyError, AttributeError)


def fail(code: str, message: str, path: str = "", **info: Any) -> ValidationError:
    """A ``ValidationError`` with one error finding."""
    return ValidationError.from_findings([make_finding(code, path, message)], **info)


def _errors(findings: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [f for f in findings if f.get("severity", "error") == "error"]


class Pending:
    """The records of one write, in order, keyed by id; ``get`` reads the post-state."""

    def __init__(self, table: Any):
        self.table = table
        self.writes: dict[str, dict[str, Any]] = {}
        self.fresh: set[str] = set()  # ids whose content is new (created, or new bindings or values)

    def add(self, record: dict[str, Any], *, fresh: bool = True) -> None:
        if record["id"] in self.writes:
            raise fail("KHG-D001", f"{record['id']} is written twice by one call", "/id")
        self.writes[record["id"]] = record
        if fresh:
            self.fresh.add(record["id"])

    def get(self, rid: Any) -> dict[str, Any] | None:
        if not isinstance(rid, str):
            return None
        return self.writes.get(rid) or self.table.current(rid)

    def records(self) -> list[dict[str, Any]]:
        return list(self.writes.values())

    def __bool__(self) -> bool:
        return bool(self.writes)


class _View(Mapping):
    """The entities or the hyperedges of a post-state, by id, for layer S (it only calls ``get``)."""

    def __init__(self, pending: Pending, kind: str):
        self._pending, self._kind = pending, kind

    def __getitem__(self, rid: str) -> dict[str, Any]:
        r = self._pending.get(rid)
        if r is None or r.get("kind") != self._kind:
            raise KeyError(rid)
        return r

    def __iter__(self) -> Iterator[str]:
        ids = set(self._pending.table.ids()) | set(self._pending.writes)
        return iter(sorted(i for i in ids if i in self))

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __bool__(self) -> bool:
        return True


def _c_findings(record: Any, path: str) -> list[dict[str, str]]:
    fast = layer_c.record_findings(record, engine="fastjsonschema", path=path)
    if not _errors(fast):
        return []
    return layer_c.record_findings(record, engine="jsonschema", path=path) or fast


def _changed(record: Mapping[str, Any], old: Mapping[str, Any] | None) -> list[int]:
    """The indices of the bindings of ``record`` that are new or whose value differs from ``old``."""
    if old is None:
        return list(range(len(record.get("bindings") or [])))
    before = {b.get("bid"): b.get("value") for b in old.get("bindings") or [] if isinstance(b, Mapping)}
    out = []
    for j, b in enumerate(record.get("bindings") or []):
        if not isinstance(b, Mapping) or b.get("bid") not in before or before[b.get("bid")] != b.get("value"):
            out.append(j)
    return out


class WriteMixin:
    """The checks and the commit shared by ``put`` and the events. Needs ``schema``, ``capabilities``, ``clock``,
    ``need`` and ``_table``."""

    schema: Any
    capabilities: frozenset[str]
    clock: Any
    _table: Any
    need: Any  # StoreBase.need: raise CapabilityMissing unless the flag is present

    # ------------------------------------------------------------------------------------------ arguments

    @staticmethod
    def _actor(actor: Any) -> str:
        if not isinstance(actor, str) or not actor:
            raise fail("KHG-C010", "actor is a non-empty string (it becomes recorded_by)", "/recorded_by")
        return actor

    @staticmethod
    def _at(at: Any) -> int | None:
        return None if at is None else parse_timestamp(at)

    @staticmethod
    def _incoming(record: Any, where: str) -> dict[str, Any]:
        """An incoming record in canonical form without store fields; C codes when it cannot be read as an
        entity or a hyperedge with a string id."""
        if not isinstance(record, Mapping):
            raise fail("KHG-C010", f"a record is an object, not {type(record).__name__}", where)
        kind = record.get("kind")
        if kind not in ("entity", "hyperedge"):
            code = "KHG-C010" if kind is None else "KHG-C002"
            raise fail(code, f"a store holds entity and hyperedge records, not {kind!r}", f"{where}/kind")
        if not isinstance(record.get("id"), str):
            findings = _c_findings(dict(record), where)
            raise ValidationError.from_findings(findings or [make_finding("KHG-C010", f"{where}/id",
                                                                          "a record id is a string")])
        out = normalize(record)
        for f in STORE_FIELDS:
            out.pop(f, None)
        return out

    def _need_data(self, records: Iterable[Any]) -> None:
        from .flags import data_flags

        for r in records:
            for flag in sorted(data_flags(r)):
                self.need(flag)

    # ------------------------------------------------------------------------------------------ checks

    def _validate(self, pending: Pending) -> None:
        """Layers C and S on every record written; one ``ValidationError`` with every error finding."""
        entities, facts = _View(pending, "entity"), _View(pending, "hyperedge")
        found: list[dict[str, str]] = []
        for i, r in enumerate(pending.records()):
            path = f"/records/{i}"
            fs = _c_findings(r, path)
            if not _errors(fs):
                fs = layer_s.record_findings(r, self.schema, entities=entities, facts=facts, path=path)
                fs += layer_s.nfc_findings(r, path)
            found += [dict(f, message=f"{r['id']}: {f['message']}") for f in _errors(fs)]
        if found:
            raise ValidationError.from_findings(found)

    def _check_versions(self, pairs: Iterable[tuple[Mapping[str, Any], Mapping[str, Any]]], *,
                        allow_novalue_end: bool = False) -> None:
        """D013 between each (current, new) pair."""
        problems = []
        for old, new in pairs:
            problems += lifecycle.version_problems(old, new, self.schema, allow_novalue_end=allow_novalue_end)
        if problems:
            raise lifecycle.error_for(problems)

    def _check_references(self, pending: Pending) -> None:
        """D002 and D020 on the new or changed entity and fact values of the records with new content."""
        found = []
        for i, r in enumerate(pending.records()):
            if r["id"] not in pending.fresh or r.get("kind") != "hyperedge":
                continue
            changed = set(_changed(r, self._table.current(r["id"])))
            for j, kind, target in bound_nodes(r):
                if j not in changed:
                    continue
                held = pending.get(target) or {}
                path = f"/records/{i}/bindings/{j}/value"
                if kind == "entity" and held.get("kind") != "entity":
                    found.append(make_finding("KHG-D002", path, f"{r['id']}: entity {target!r} is not held by the "
                                                                "store"))
                elif kind == "entity" and held.get("redirect_to"):
                    found.append(make_finding("KHG-D020", path, f"{r['id']}: entity {target!r} redirects to "
                                                                f"{held['redirect_to']!r}"))
                elif kind == "fact" and held.get("kind") != "hyperedge":
                    found.append(make_finding("KHG-D002", path, f"{r['id']}: fact reference {target!r} does not "
                                                                "resolve"))
        if found:
            raise ValidationError.from_findings(found)

    def _check_pointers(self, pending: Pending) -> None:
        """D010 on the neighbourhood of the write: the records written, the lifecycle records they name, the facts
        their lifecycle records bind and the lifecycle records those name."""
        subset: dict[str, dict[str, Any]] = {}

        def take(rid: Any) -> dict[str, Any] | None:
            r = pending.get(rid)
            if r is not None:
                subset[rid] = r
            return r

        for r in pending.records():
            take(r["id"])
            take(r.get("status_ref"))
            if r.get("relation") in LIFECYCLE_RELATIONS:
                for _, _, target in bound_nodes(r):
                    bound = take(target)
                    if bound is not None:
                        take(bound.get("status_ref"))
        problems = lifecycle.pointer_problems(subset)
        if problems:
            raise lifecycle.error_for(problems)

    def _check_nesting(self, pending: Pending) -> None:
        """D008: a nesting cycle reachable from the records written."""
        subset: dict[str, dict[str, Any]] = {}
        todo = [r["id"] for r in pending.records() if r.get("kind") == "hyperedge"
                and r.get("relation") not in LIFECYCLE_RELATIONS]
        while todo:
            rid = todo.pop()
            r = pending.get(rid)
            if r is None or rid in subset or r.get("kind") != "hyperedge":
                continue
            subset[rid] = r
            todo += [target for _, kind, target in bound_nodes(r) if kind == "fact"]
        problem = lifecycle.nesting_cycle(subset)
        if problem is not None:
            raise lifecycle.error_for([problem])

    def _keyed(self) -> tuple[bool, bool]:
        """(keys checked, temporal keys checked)."""
        on = "key_constraint" in self.capabilities
        return on, on and "valid_time" in self.capabilities

    def _groups(self, records: Iterable[Mapping[str, Any] | None], temporal: bool) -> set[tuple[str, str]]:
        out = set()
        for r in records:
            if r is None or r.get("kind") != "hyperedge" or r.get("relation") in LIFECYCLE_RELATIONS:
                continue
            try:
                key = self.schema.key(r["relation"])
                digest = key_digest(r, self.schema) if key else None
            except _SAFE:
                continue
            if digest is not None and (temporal or not key["temporal"]):
                out.add((r["relation"], digest))
        return out

    def _check_keys(self, pending: Pending, *, disputed_rule: bool) -> None:
        """D016 on the key groups the write touches (their facts before and after it)."""
        on, temporal = self._keyed()
        if not on:
            return
        written = pending.records()
        touched = self._groups([self._table.current(r["id"]) for r in written] + written, temporal)
        if not touched:
            return
        ids = set(pending.writes)
        for group in touched:
            ids |= self._table.by_key(*group)
        before = {i: r for i in sorted(ids) if (r := self._table.current(i)) is not None}
        after = {i: r for i in sorted(ids) if (r := pending.get(i)) is not None}
        batch = [r for r in written if r.get("kind") == "hyperedge" and r.get("status") == "asserted"
                 and self._groups([r], temporal)]
        found = keys.collisions(before, batch, self.schema, post=after, disputed_rule=disputed_rule)
        if found:
            raise keys.key_collision(found)
        # a violation already there (after a trusted load) is not blamed on the write, nor is what is left of it
        # when the write takes facts out of it (retracting one of three normal facts on one key)
        old = [(v.relation, v.key_digest, set(v.ids)) for v in keys.key_invariant_violations(before, self.schema,
                                                                                              keys=touched)]
        new = [v for v in keys.key_invariant_violations(after, self.schema, keys=touched)
               if not any((rel, kd) == (v.relation, v.key_digest) and set(v.ids) <= ids for rel, kd, ids in old)]
        if new:
            listed = [{"relation": v.relation, "key_digest": v.key_digest, "temporal": v.temporal,
                       "ids": list(v.ids), "at": v.at} for v in new]
            raise KeyCollision(f"the write leaves facts {', '.join(new[0].ids)} holding together on one key without "
                               "exactly one preferred fact; nothing was written", codes=["KHG-D016"],
                               info={"collisions": [], "violations": listed})

    def _check_supersessions(self, pending: Pending) -> None:
        """D011 on the asserted ``khg:supersedes`` records that bind a record written; D012 when one is written."""
        written = set(pending.writes)
        subset: dict[str, dict[str, Any]] = {}
        lifecycle_ids = set()
        for rid in written:
            lifecycle_ids |= self._table.by_node(rid)
        lifecycle_ids |= {r["id"] for r in pending.records() if r.get("relation") == "khg:supersedes"}
        for lid in sorted(lifecycle_ids):
            lc = pending.get(lid)
            if lc is None or lc.get("relation") != "khg:supersedes" or lc.get("status") != "asserted":
                continue
            subset[lid] = lc
            for _, _, target in bound_nodes(lc):
                r = pending.get(target)
                if r is not None:
                    subset[target] = r
        problems = lifecycle.supersession_problems(subset, self.schema, ids=written)
        if problems:
            raise lifecycle.error_for(problems)
        if any(r.get("relation") == "khg:supersedes" for r in pending.records()):
            every = {lid: r for lid in sorted(self._table.by_relation("khg:supersedes") | lifecycle_ids)
                     if (r := pending.get(lid)) is not None}
            cycle = lifecycle.supersession_cycle(every)
            if cycle is not None:
                raise lifecycle.error_for([cycle])

    # ------------------------------------------------------------------------------------------ commit

    def _write_time(self, at: int | None) -> int:
        """The transaction time of a write: ``at`` pinned forward, else the clock (after the store's latest)."""
        latest = self._table.latest
        if at is None:
            now = parse_timestamp(self.clock.now())
            return now if latest is None or now > latest else latest + 1
        if latest is not None and at <= latest:
            raise VersionError(f"KHG-D018: transaction time {format_timestamp(at)} is not after the store's latest "
                               f"{format_timestamp(latest)}", codes=["KHG-D018"],
                               info={"at": format_timestamp(at), "latest": format_timestamp(latest)})
        return at

    def _advance_clock(self, t: int) -> None:
        if parse_timestamp(self.clock.now()) < t:
            self.clock.set(format_timestamp(t))
        self.clock.tick()

    def _warnings(self, ids: Iterable[str]) -> list[dict[str, Any]]:
        """L008: the possible-only overlaps on temporal keys that involve the records written."""
        on, temporal = self._keyed()
        if not temporal:
            return []
        written = [r for i in ids if (r := self._table.current(i)) is not None]
        groups = {g for g in self._groups(written, True) if self.schema.key(g[0])["temporal"]}
        if not groups:
            return []
        subset = {i: self._table.current(i) for g in sorted(groups) for i in sorted(self._table.by_key(*g))}
        return keys.l008_warnings(subset, self.schema, ids=set(ids))

    def _commit(self, pending: Pending, *, actor: str, at: int | None, noops: Iterable[tuple[str, int, str]] = (),
                disputed_rule: bool = False, pointers: bool = False,
                d011: Iterable[lifecycle.Problem] = ()) -> Receipt:
        """Steps 3 (pointers) to 7 of the write path, then the write and the receipt."""
        if pointers:
            self._check_pointers(pending)
        self._check_nesting(pending)
        self._check_keys(pending, disputed_rule=disputed_rule)
        early = list(d011)
        if early:
            raise lifecycle.error_for(early)
        self._check_supersessions(pending)
        t = self._write_time(at)
        stamp = format_timestamp(t)
        rows = list(noops)
        for r in pending.records():
            previous = self._table.latest_version(r["id"])
            r["version"] = previous + 1
            r["recorded_at"] = stamp
            r["recorded_by"] = actor
            self._table.add(r, t)
            rows.append((r["id"], r["version"], "versioned" if previous else "created"))
        self._advance_clock(t)
        return {"records": sorted(rows), "at": stamp, "warnings": self._warnings(list(pending.writes))}
