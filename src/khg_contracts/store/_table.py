"""The version table of ``MemoryStore`` (DESIGN §6.3): every version of every id, and four indexes. ``store.table``
publishes it with its interface (ruling 17).

The indexes cover every version ever written, so a read at an earlier ``as_at`` finds its candidates too; a read
then checks the version it picks. They map a node (an entity or fact id bound as a value) to the hyperedges that
bind it, a relation to its hyperedges, ``(relation, key_digest)`` to the facts on that key, and a lifecycle record
id to the facts whose ``status_ref`` names it. Per-version values (key digest, bounds, identity keys) are computed
once, on first use; what cannot be computed from a malformed record is None.
"""
from __future__ import annotations

from typing import Any, Iterator, Mapping

from ..errors import KHGError
from ..record import Bounds, bounds, identity_key, key_digest
from ..schema import Schema

__all__ = ["Entry", "VersionTable", "bound_nodes"]

_SAFE = (KHGError, ValueError, TypeError, KeyError, AttributeError)
_UNSET: Any = object()


def bound_nodes(record: Mapping[str, Any]) -> list[tuple[int, str, str]]:
    """``(binding index, "entity" | "fact", id)`` for every entity or fact value of a hyperedge: its nodes."""
    out = []
    bindings = record.get("bindings")
    for j, b in enumerate(bindings if isinstance(bindings, list) else []):
        value = b.get("value") if isinstance(b, Mapping) else None
        if isinstance(value, Mapping) and len(value) == 1:
            for kind in ("entity", "fact"):
                if isinstance(value.get(kind), str):
                    out.append((j, kind, value[kind]))
    return out


class Entry:
    """One stored version: the record (canonical form, with its store fields) and its transaction time in
    microseconds, plus values computed on first use."""

    __slots__ = ("record", "t", "_schema", "_kd", "_bounds", "_idents")

    def __init__(self, record: dict[str, Any], t: int, schema: Schema):
        self.record = record
        self.t = t
        self._schema = schema
        self._kd: Any = _UNSET
        self._bounds: Any = _UNSET
        self._idents: Any = _UNSET

    @property
    def is_edge(self) -> bool:
        return self.record.get("kind") == "hyperedge"

    @property
    def key_digest(self) -> str | None:
        """The fact's key digest (None without a key, for a special key value, or when it cannot be read)."""
        if self._kd is _UNSET:
            try:
                self._kd = key_digest(self.record, self._schema) if self.is_edge else None
            except _SAFE:
                self._kd = None
        return self._kd

    @property
    def bounds(self) -> Bounds | None:
        """The bound table of §2.6 (None for an entity or when it cannot be read)."""
        if self._bounds is _UNSET:
            try:
                self._bounds = bounds(self.record, self._schema) if self.is_edge else None
            except _SAFE:
                self._bounds = None
        return self._bounds

    @property
    def idents(self) -> list[str | None]:
        """The identity key of each binding's value, in binding order (None for an unbound or malformed value)."""
        if self._idents is _UNSET:
            out: list[str | None] = []
            bindings = self.record.get("bindings")
            for b in bindings if isinstance(bindings, list) else []:
                value = b.get("value") if isinstance(b, Mapping) else None
                try:
                    unreadable = not isinstance(value, Mapping) or "unbound" in value
                    out.append(None if unreadable else identity_key(value))  # type: ignore[arg-type]
                except _SAFE:
                    out.append(None)
            self._idents = out
        return self._idents


class VersionTable:
    """Version lists by id and the indexes over them; ``latest`` is the store's latest transaction time."""

    def __init__(self, schema: Schema):
        self.schema = schema
        self.latest: int | None = None
        self._versions: dict[str, list[Entry]] = {}
        self._nodes: dict[str, set[str]] = {}
        self._relations: dict[str, set[str]] = {}
        self._keys: dict[tuple[str, str], set[str]] = {}
        self._refs: dict[str, set[str]] = {}

    def __contains__(self, rid: object) -> bool:
        return rid in self._versions

    def __len__(self) -> int:
        return len(self._versions)

    def ids(self) -> list[str]:
        """Every id, in code-point order."""
        return sorted(self._versions)

    def entries(self, rid: str) -> list[Entry]:
        return self._versions.get(rid, [])

    def current(self, rid: str) -> dict[str, Any] | None:
        """The latest version of ``rid`` (the stored object: do not change it), or None."""
        vs = self._versions.get(rid)
        return vs[-1].record if vs else None

    def entry_at(self, rid: str, as_at: int | None = None) -> Entry | None:
        """The latest version of ``rid`` recorded at or before ``as_at`` (microseconds; None: the latest)."""
        vs = self._versions.get(rid)
        if not vs:
            return None
        if as_at is None:
            return vs[-1]
        for e in reversed(vs):
            if e.t <= as_at:
                return e
        return None

    def latest_version(self, rid: str) -> int:
        """The version number of the latest version of ``rid``, 0 when it is not held."""
        vs = self._versions.get(rid)
        return vs[-1].record.get("version", len(vs)) if vs else 0

    def add(self, record: dict[str, Any], t: int) -> Entry:
        """Append a version (its store fields already set) and index it."""
        e = Entry(record, t, self.schema)
        rid = record["id"]
        self._versions.setdefault(rid, []).append(e)
        if e.is_edge:
            for _, _, node in bound_nodes(record):
                self._nodes.setdefault(node, set()).add(rid)
            rel = record.get("relation")
            if isinstance(rel, str):
                self._relations.setdefault(rel, set()).add(rid)
                kd = e.key_digest
                if kd is not None:
                    self._keys.setdefault((rel, kd), set()).add(rid)
            ref = record.get("status_ref")
            if isinstance(ref, str):
                self._refs.setdefault(ref, set()).add(rid)
        self.latest = t if self.latest is None else max(self.latest, t)
        return e

    def by_node(self, node: str) -> set[str]:
        """The hyperedges that bind ``node`` as a value in some version."""
        return self._nodes.get(node, set())

    def by_relation(self, relation: str) -> set[str]:
        return self._relations.get(relation, set())

    def by_key(self, relation: str, digest: str) -> set[str]:
        return self._keys.get((relation, digest), set())

    def by_ref(self, lifecycle_id: str) -> set[str]:
        """The facts whose ``status_ref`` names ``lifecycle_id`` in some version."""
        return self._refs.get(lifecycle_id, set())

    def __iter__(self) -> Iterator[str]:
        return iter(self.ids())
