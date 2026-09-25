"""The C2 reads as native queries (DESIGN §2): ``NativeReads``, a mixin placed before ``TableStore``.

``TableStore`` (khg-contracts ``store.table``, ruling 17) gives every adapter the write path over its version table.
``NativeReads`` replaces the six reads that research 01 answered natively: ``get``, ``history``, ``incident``,
``find``, ``find_by_key`` and ``iter_records``. It checks the arguments, the capability flags and the relation in
the order ``TableStore`` does, so that a refusal is the same error; then it calls one backend hook:

| Hook | Returns |
|---|---|
| ``_n_get(id, t, version)`` | the record (a fresh copy) of ``id`` at transaction time ``t`` (µs, None: latest), or version ``version`` recorded at or before ``t``; None |
| ``_n_versions(id, t)`` | every version of ``id`` recorded at or before ``t`` (None: every version), oldest first |
| ``_n_ids(t)`` | every id with a version recorded at or before ``t`` (None: every id) |
| ``_n_is_fact(id)`` | whether ``id`` is a held hyperedge |
| ``_n_incident(node, role, relation, where, t, as_of, after, limit)`` | the ids, in code-point order |
| ``_n_find(relation, pats, match, where, t, as_of, after, limit)`` | the ids, in code-point order |
| ``_n_key(relation, digest, where, t, as_of)`` | the ids, in code-point order |
| ``_n_records(ids, t)`` | the records of ``ids`` at ``t`` (default: ``_n_get`` per id) |

``as_of`` is ``Where.as_of_seconds`` (an int, or None); an int64 backend clamps it with ``rows.query_instant``.
``supersession_walk``, ``get_many``, ``degree`` and ``export`` stay ``StoreBase``'s, over these reads.
"""
from __future__ import annotations

import copy
from typing import Any, Iterator, Mapping, Sequence

from khg_contracts.record import key_digest
from khg_contracts.schema import LIFECYCLE_RELATIONS
from khg_contracts.store import Where, parse_timestamp
from khg_contracts.store.flags import pattern_flags, where_flags

from .rows import Pat, prepare

__all__ = ["NativeReads"]


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
    _documents: list[dict[str, Any]]

    # ------------------------------------------------------------------------------------------ hooks
    def _n_get(self, id: str, t: int | None, version: int | None) -> dict[str, Any] | None:
        raise NotImplementedError

    def _n_versions(self, id: str, t: int | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def _n_ids(self, t: int | None) -> list[str]:
        raise NotImplementedError

    def _n_is_fact(self, id: str) -> bool:
        raise NotImplementedError

    def _n_incident(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                    as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        raise NotImplementedError

    def _n_find(self, relation: str, pats: list[Pat], match: str, where: Where, t: int | None, as_of: int | None,
                after: str | None, limit: int | None) -> list[str]:
        raise NotImplementedError

    def _n_key(self, relation: str, digest: str, where: Where, t: int | None, as_of: int | None) -> list[str]:
        raise NotImplementedError

    def _n_records(self, ids: Sequence[str], t: int | None) -> list[dict[str, Any]]:
        out = []
        for i in ids:
            r = self._n_get(i, t, None)
            if r is not None:
                out.append(r)
        return out

    # ------------------------------------------------------------------------------------------ checks
    def _need_where(self, where: Any) -> Where:
        where = Where.of(where)
        for flag in sorted(where_flags(where)):
            self.need(flag)
        return where

    @staticmethod
    def _t(as_at: str | None) -> int | None:
        return None if as_at is None else parse_timestamp(as_at)

    # ------------------------------------------------------------------------------------------ reads
    def get(self, id: str, *, as_at: str | None = None, version: int | None = None) -> dict[str, Any] | None:
        if as_at is not None or version is not None:
            self.need("transaction_time")
        return self._n_get(id, self._t(as_at), version)

    def history(self, id: str) -> list[dict[str, Any]]:
        return self._n_versions(id, None)

    def incident(self, node: str, *, role: str | None = None, relation: str | None = None,
                 where: Where = Where(), limit: int | None = None, after: str | None = None) -> list[dict]:
        _page(limit, after)
        where = self._need_where(where)
        if relation is not None:
            self.schema.relation(relation)
        if isinstance(node, str) and self._n_is_fact(node):
            self.need("nesting")
        if limit == 0:
            return []
        t = where.as_at_micros
        ids = self._n_incident(node, role, relation, where, t, where.as_of_seconds, after, limit)
        return self._n_records(ids, t)

    def find(self, relation: str, pattern: Sequence[Mapping[str, Any]], *, match: str = "at_least",
             where: Where = Where(), limit: int | None = None, after: str | None = None) -> list[dict]:
        _page(limit, after)
        if match not in ("at_least", "exact"):
            raise ValueError(f"match is at_least or exact, not {match!r}")
        self.schema.relation(relation)
        pats = prepare(pattern)
        pattern = list(pattern)
        where = self._need_where(where)
        for flag in sorted(pattern_flags(pattern, lifecycle=relation in LIFECYCLE_RELATIONS)):
            self.need(flag)
        if limit == 0:
            return []
        t = where.as_at_micros
        ids = self._n_find(relation, pats, match, where, t, where.as_of_seconds, after, limit)
        return self._n_records(ids, t)

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
        # the checks StoreBase's call of find makes
        self.schema.relation(relation)
        prepare(patterns)
        where = self._need_where(where)
        for flag in sorted(pattern_flags(patterns, lifecycle=relation in LIFECYCLE_RELATIONS)):
            self.need(flag)
        t = where.as_at_micros
        return self._n_records(self._n_key(relation, digest, where, t, where.as_of_seconds), t)

    def iter_records(self, *, content: str = "snapshot", as_at: str | None = None) -> Iterator[dict[str, Any]]:
        if content not in ("snapshot", "history"):
            raise ValueError(f"content is snapshot or history, not {content!r}")
        if content == "history":
            self.need("history_export")
        if as_at is not None:
            self.need("transaction_time")
        return self._iter(content, self._t(as_at))

    def _iter(self, content: str, t: int | None) -> Iterator[dict[str, Any]]:
        for doc in self._documents:
            yield copy.deepcopy(doc)
        ids = sorted(self._n_ids(t))
        if content == "snapshot":
            yield from self._n_records(ids, t)
            return
        for i in ids:
            yield from self._n_versions(i, t)
