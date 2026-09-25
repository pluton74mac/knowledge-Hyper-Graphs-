"""The C2 reads as native queries (DESIGN §2; the director's ruling on review 01, R-06): ``NativeReads``, a mixin
placed before ``TableStore``.

``TableStore`` (khg-contracts ``store.table``, ruling 17) gives every adapter the write path over its version table.
``NativeReads`` answers every read natively: ``get``, ``history``, ``incident``, ``find``, ``find_by_key``,
``iter_records`` and the derived ``get_many``, ``degree`` and ``supersession_walk`` (``export`` is ``StoreBase``'s,
over ``iter_records``). Each read checks its arguments, the capability flags and the relation in the order
``TableStore`` does, so that a refusal is the same error; then it calls the backend hooks:

| Hook | Returns |
|---|---|
| ``_n_get(id, t, version)`` | the record (a fresh copy) of ``id`` at transaction time ``t`` (µs, None: latest), or version ``version`` recorded at or before ``t``; None |
| ``_n_versions(id, t)`` | every version of ``id`` recorded at or before ``t`` (None: every version), oldest first |
| ``_n_scan(t, history)`` | every record at ``t`` in id order (``history``: every version recorded at or before ``t``, by id then version), in a bounded number of queries |
| ``_n_is_fact(id)`` | whether ``id`` is a held hyperedge |
| ``_n_incident(node, role, relation, where, t, as_of, after, limit)`` | the ids, in code-point order |
| ``_n_count(node, role, relation, where, t, as_of)`` | how many ids ``_n_incident`` would give, counted by the engine |
| ``_n_find(relation, pats, match, where, t, as_of, after, limit)`` | the ids, in code-point order |
| ``_n_key(relation, digest, where, t, as_of)`` | the ids, in code-point order |
| ``_n_bound_by(relation, role, idents, where, t, as_of)`` | ``{ident: [ids]}``: the facts of ``relation`` with a binding in ``role`` whose value identity is ``ident``, ids in code-point order |
| ``_n_records(ids, t)`` | the records of ``ids`` at ``t``, in the order of ``ids`` (absent ids left out), in a bounded number of queries |

Filters, ``after``, ``limit`` and counts are pushed into the engine; the records of one call are fetched in a bounded
number of queries, never one query per record, and rebuilt by ``rows.record_of``, the one row-to-record function
of every backend. ``supersession_walk`` makes one ``_n_bound_by`` and one ``_n_records`` per level of the walk, and
one ``_n_records`` for the terminals. ``_reading()`` wraps each read (TypeDB opens one read transaction there).
``as_of`` is ``Where.as_of_seconds`` (an int, or None); an int64 backend clamps it with ``rows.query_instant``.
"""
from __future__ import annotations

import contextlib
import copy
from typing import Any, Iterable, Iterator, Mapping, Sequence

from khg_contracts.record import identity_key, key_digest
from khg_contracts.record.lifecycle import RANKS, VISIBILITIES
from khg_contracts.schema import LIFECYCLE_RELATIONS
from khg_contracts.store import Where, parse_timestamp
from khg_contracts.store.flags import pattern_flags, where_flags

from .rows import Pat, prepare

__all__ = ["NativeReads"]

SUPERSEDES = "khg:supersedes"


def _page(limit: Any, after: Any) -> None:
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise ValueError(f"limit is None or a non-negative integer, not {limit!r}")
    if after is not None and not isinstance(after, str):
        raise TypeError(f"after is None or an id, not {type(after).__name__}")


class NativeReads:
    """C2 reads over native queries; see the module docstring."""

    schema: Any
    capabilities: frozenset[str]
    need: Any
    kept_documents: list[dict[str, Any]]

    # ------------------------------------------------------------------------------------------ hooks
    def _n_get(self, id: str, t: int | None, version: int | None) -> dict[str, Any] | None:
        raise NotImplementedError

    def _n_versions(self, id: str, t: int | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def _n_scan(self, t: int | None, history: bool) -> Iterable[dict[str, Any]]:
        raise NotImplementedError

    def _n_is_fact(self, id: str) -> bool:
        raise NotImplementedError

    def _n_incident(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                    as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        raise NotImplementedError

    def _n_count(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                 as_of: int | None) -> int:
        raise NotImplementedError

    def _n_find(self, relation: str, pats: list[Pat], match: str, where: Where, t: int | None, as_of: int | None,
                after: str | None, limit: int | None) -> list[str]:
        raise NotImplementedError

    def _n_key(self, relation: str, digest: str, where: Where, t: int | None, as_of: int | None) -> list[str]:
        raise NotImplementedError

    def _n_bound_by(self, relation: str, role: str, idents: Sequence[str], where: Where, t: int | None,
                    as_of: int | None) -> dict[str, list[str]]:
        raise NotImplementedError

    def _n_records(self, ids: Sequence[str], t: int | None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def _reading(self) -> contextlib.AbstractContextManager[Any]:
        """The context of one read call (TypeDB: one read transaction); nothing by default."""
        return contextlib.nullcontext()

    # ------------------------------------------------------------------------------------------ checks
    def _need_where(self, where: Any) -> Where:
        where = Where.of(where)
        for flag in sorted(where_flags(where)):
            self.need(flag)
        return where

    @staticmethod
    def _t(as_at: str | None) -> int | None:
        return None if as_at is None else parse_timestamp(as_at)

    def _check_incident(self, node: Any, role: Any, relation: Any, where: Any, limit: Any, after: Any) -> Where:
        """``TableStore.incident``'s checks, in its order."""
        _page(limit, after)
        where = self._need_where(where)
        if relation is not None:
            self.schema.relation(relation)
        if isinstance(node, str) and self._n_is_fact(node):
            self.need("nesting")
        return where

    def _check_find(self, relation: Any, pattern: Any, match: Any, where: Any, limit: Any,
                    after: Any) -> tuple[list[Pat], Where]:
        """``TableStore.find``'s checks, in its order."""
        _page(limit, after)
        if match not in ("at_least", "exact"):
            raise ValueError(f"match is at_least or exact, not {match!r}")
        self.schema.relation(relation)
        pats = prepare(pattern)
        pattern = list(pattern)
        where = self._need_where(where)
        for flag in sorted(pattern_flags(pattern, lifecycle=relation in LIFECYCLE_RELATIONS)):
            self.need(flag)
        return pats, where

    # ------------------------------------------------------------------------------------------ reads
    def get(self, id: str, *, as_at: str | None = None, version: int | None = None) -> dict[str, Any] | None:
        if as_at is not None or version is not None:
            self.need("transaction_time")
        t = self._t(as_at)
        with self._reading():
            return self._n_get(id, t, version)

    def history(self, id: str) -> list[dict[str, Any]]:
        with self._reading():
            return self._n_versions(id, None)

    def get_many(self, ids: Iterable[str], *, as_at: str | None = None) -> dict[str, dict[str, Any]]:
        """``StoreBase.get_many`` (``get`` per id, missing ids left out, in id order) in one batched read."""
        if isinstance(ids, (str, bytes)):
            raise TypeError("ids is a collection of ids, not a string")
        unique = list(dict.fromkeys(ids))
        if not unique:
            return {}
        if as_at is not None:
            self.need("transaction_time")
        t = self._t(as_at)
        wanted = sorted(i for i in unique if isinstance(i, str))  # no other id is ever held (get gives None)
        with self._reading():
            got = self._n_records(wanted, t) if wanted else []
        return dict(sorted((r["id"], r) for r in got))

    def incident(self, node: str, *, role: str | None = None, relation: str | None = None,
                 where: Where = Where(), limit: int | None = None, after: str | None = None) -> list[dict]:
        with self._reading():
            where = self._check_incident(node, role, relation, where, limit, after)
            if limit == 0:
                return []
            t = where.as_at_micros
            ids = self._n_incident(node, role, relation, where, t, where.as_of_seconds, after, limit)
            return self._n_records(ids, t) if ids else []

    def degree(self, node: str, *, role: str | None = None, relation: str | None = None,
               where: Where = Where()) -> int:
        """``len(incident(...))``, counted by the engine."""
        with self._reading():
            where = self._check_incident(node, role, relation, where, None, None)
            return int(self._n_count(node, role, relation, where, where.as_at_micros, where.as_of_seconds))

    def find(self, relation: str, pattern: Sequence[Mapping[str, Any]], *, match: str = "at_least",
             where: Where = Where(), limit: int | None = None, after: str | None = None) -> list[dict]:
        with self._reading():
            pats, where = self._check_find(relation, pattern, match, where, limit, after)
            if limit == 0:
                return []
            t = where.as_at_micros
            ids = self._n_find(relation, pats, match, where, t, where.as_of_seconds, after, limit)
            return self._n_records(ids, t) if ids else []

    def find_by_key(self, relation: str, key: Sequence[Mapping[str, Any]], *, where: Where = Where()) -> list[dict]:
        """``StoreBase.find_by_key``'s checks in its order, then one lookup on the stored key digest."""
        declared = self.schema.key(relation)
        if not declared:
            raise ValueError(f"find_by_key: {relation!r} declares no key")
        if isinstance(key, Mapping) or isinstance(key, (str, bytes)):
            raise TypeError("key is a sequence of patterns {role, value, position?}")
        patterns = list(key)
        for p in patterns:
            value = p.get("value") if isinstance(p, Mapping) else None
            if not isinstance(value, Mapping) or value.get("any") is True or value.get("any_unbound") is True:
                raise ValueError("find_by_key binds each key role to a value")
        if {p.get("role") for p in patterns} != set(declared["roles"]):
            raise ValueError(f"find_by_key binds exactly the key roles {sorted(declared['roles'])}")
        probe = {"kind": "hyperedge", "id": "_:key", "relation": relation, "status": "asserted",
                 "bindings": [{"bid": f"b{n}", "role": p["role"], "value": p["value"],
                               **({"position": p["position"]} if "position" in p else {})}
                              for n, p in enumerate(patterns, 1)]}
        digest = key_digest(probe, self.schema)
        if digest is None:
            return []
        with self._reading():
            _, where = self._check_find(relation, patterns, "at_least", where, None, None)  # StoreBase calls find
            t = where.as_at_micros
            ids = self._n_key(relation, digest, where, t, where.as_of_seconds)
            return self._n_records(ids, t) if ids else []

    def supersession_walk(self, id: str, *, direction: str = "forward", as_at: str | None = None) -> dict[str, Any]:
        """``StoreBase.supersession_walk`` (breadth first over the asserted ``khg:supersedes`` records at ``as_at``),
        with one native lookup and one batched record read per level instead of one ``find`` per fact."""
        if direction not in ("forward", "backward"):
            raise ValueError(f"direction is forward or backward, not {direction!r}")
        frm, to = ("khg:superseded", "khg:superseding") if direction == "forward" else \
            ("khg:superseding", "khg:superseded")
        where = Where(status=frozenset({"asserted"}), rank=frozenset(RANKS), visibility=frozenset(VISIBILITIES),
                      kinds=frozenset({"lifecycle"}), as_at=as_at)
        with self._reading():
            _, where = self._check_find(SUPERSEDES, [{"role": frm, "value": {"fact": id}}], "at_least", where,
                                        None, None)  # the checks of StoreBase's first find
            t, as_of = where.as_at_micros, where.as_of_seconds
            outgoing: dict[str, list[dict[str, Any]]] = {}

            def expand(facts: Sequence[str]) -> None:
                todo = [f for f in facts if f not in outgoing]
                if not todo:
                    return
                ident = {f: identity_key({"fact": f}) for f in todo}
                found = self._n_bound_by(SUPERSEDES, frm, sorted(set(ident.values())), where, t, as_of)
                ids = sorted({i for f in todo for i in found.get(ident[f], [])})
                records = {r["id"]: r for r in (self._n_records(ids, t) if ids else [])}
                for f in todo:
                    outgoing[f] = [copy.deepcopy(records[i]) for i in found.get(ident[f], []) if i in records]

            steps: list[dict[str, Any]] = []
            seen, reached, frontier, depth = {id}, [id], [id], 0
            while frontier:
                depth += 1
                expand(frontier)
                following: list[str] = []
                for fact in frontier:
                    for s in outgoing[fact]:
                        for b in s.get("bindings", []):
                            value = b.get("value") if isinstance(b, Mapping) else None
                            target = value.get("fact") if isinstance(value, Mapping) else None
                            if b.get("role") != to or not isinstance(target, str):
                                continue
                            steps.append({"depth": depth, "via": s.get("id"), "reason": s.get("reason"),
                                          "from": fact, "to": target})
                            if target not in seen:
                                seen.add(target)
                                reached.append(target)
                                following.append(target)
                frontier = sorted(following)
            ends = [f for f in sorted(reached) if not outgoing[f]]
            held = {r["id"]: r for r in (self._n_records([f for f in ends if isinstance(f, str)], t) if ends else [])}
        terminal = [{"id": f, "status": held[f].get("status") if f in held else None} for f in ends]
        return {"start": id, "direction": direction, "steps": steps, "terminal": terminal}

    def iter_records(self, *, content: str = "snapshot", as_at: str | None = None) -> Iterator[dict[str, Any]]:
        if content not in ("snapshot", "history"):
            raise ValueError(f"content is snapshot or history, not {content!r}")
        if content == "history":
            self.need("history_export")
        if as_at is not None:
            self.need("transaction_time")
        return self._iter(content, self._t(as_at))

    def _iter(self, content: str, t: int | None) -> Iterator[dict[str, Any]]:
        yield from self.kept_documents
        with self._reading():
            records = list(self._n_scan(t, content == "history"))
        yield from records
