"""The version-table interface of the table-backed stores (P2 DESIGN §14, ruling 17).

This is an implementation API of khg-contracts, outside the C2 contract: C2 ``khg-store/1.0.0`` is unchanged, and a
store that implements ``store.Store`` some other way needs nothing here. It lets a backend reuse the reference
store's write path (the checks of DESIGN §6.2, the four events, keys and transaction time) over its own storage,
and answer the reads with native queries (P1 research 01, D2).

``MemoryStore`` keeps every version in a *version table* and reaches its data only through it. Its write path and
its reads use thirteen members (``MEMBERS``), which ``VersionTableProtocol`` states:

| Member | Meaning |
|---|---|
| ``latest`` | the store's latest transaction time in microseconds (None when empty); read and set |
| ``rid in table``, ``len(table)`` | whether an id is held; the number of ids |
| ``ids()`` | every id, in code-point order |
| ``entries(rid)`` | every version of ``rid`` as an ``Entry``, oldest first ([] when absent) |
| ``current(rid)`` | the record of the latest version, or None; the caller does not change it |
| ``entry_at(rid, as_at)`` | the latest version recorded at or before ``as_at`` (microseconds; None: the latest) |
| ``latest_version(rid)`` | the version number of the latest version, 0 when absent |
| ``add(record, t)`` | append a version (its store fields set) recorded at ``t`` and index it; the new ``Entry`` |
| ``by_node(node)`` | the hyperedges that bind the entity or fact ``node`` as a value in some version |
| ``by_relation(relation)`` | the hyperedges of ``relation`` in some version |
| ``by_key(relation, digest)`` | the facts of ``relation`` whose key digest is ``digest`` in some version |
| ``by_ref(lifecycle_id)`` | the facts whose ``status_ref`` names ``lifecycle_id`` in some version |

The four ``by_*`` indexes return sets of ids that the caller only reads. They cover every version ever written, so a
read at an earlier ``as_at`` finds its candidates too; the reader then checks the version it picks.

- ``Entry(record, t, schema)``: one stored version, with its key digest, bounds and identity keys computed on first
  use.
- ``VersionTable(schema)``: the in-memory table, ``MemoryStore``'s.
- ``bound_nodes(record)``: ``(binding index, "entity" | "fact", id)`` for every node a hyperedge binds; what
  ``by_node`` indexes.
- ``TableStore(schema, *, table=None, clock=None, capabilities=None, store_id="store")``: every C2 method over the
  table that ``table(schema)`` returns (the in-memory one when None). ``MemoryStore`` is ``TableStore`` over
  ``VersionTable``. A backend subclass overrides:

  - ``transaction()``: a context manager around each write (``put``, ``apply``, ``load``): begin on entry, commit
    at the end, roll back when the block raises. The table must read its own uncommitted writes inside it.
    ``writing()`` is the re-entrant form the store uses, so a subclass can add work to a write's transaction;
  - ``cannot_hold(record)``: None, or a dict saying what the backend cannot hold of a record (``{"reason": ...}``).
    ``put`` and ``apply`` refuse such a record after every C2 check, and ``load`` treats it like a record that
    needs a missing flag (``on_missing="skip"`` lists it in ``LoadReport.skipped``). The refusal is a
    ``ValidationError`` without a code, with ``info["id"]`` and ``info["cannot_hold"]``;
  - any of ``get``, ``history``, ``incident``, ``find``, ``find_by_key``, ``iter_records``, with a native query that
    returns what the table-backed read returns.
"""
from __future__ import annotations

from typing import AbstractSet, Any, Protocol, Sequence, runtime_checkable

from ._table import Entry, VersionTable, bound_nodes
from .memory import TableStore

__all__ = ["MEMBERS", "Entry", "TableStore", "VersionTable", "VersionTableProtocol", "bound_nodes"]

#: The thirteen members of a version table that the write path and the reads use.
MEMBERS = ("latest", "__contains__", "__len__", "ids", "entries", "current", "entry_at", "latest_version", "add",
           "by_node", "by_relation", "by_key", "by_ref")


@runtime_checkable
class VersionTableProtocol(Protocol):
    """What ``TableStore`` needs of a version table (the table of the module docstring)."""

    latest: int | None

    def __contains__(self, rid: object) -> bool: ...

    def __len__(self) -> int: ...

    def ids(self) -> list[str]: ...

    def entries(self, rid: str) -> Sequence[Entry]: ...

    def current(self, rid: str) -> dict[str, Any] | None: ...

    def entry_at(self, rid: str, as_at: int | None = None) -> Entry | None: ...

    def latest_version(self, rid: str) -> int: ...

    def add(self, record: dict[str, Any], t: int) -> Entry: ...

    def by_node(self, node: str) -> AbstractSet[str]: ...

    def by_relation(self, relation: str) -> AbstractSet[str]: ...

    def by_key(self, relation: str, digest: str) -> AbstractSet[str]: ...

    def by_ref(self, lifecycle_id: str) -> AbstractSet[str]: ...
