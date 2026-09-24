"""The C2 interface ``khg-store/1.0.0``: the ``Store`` and ``Clock`` protocols and the result types (DESIGN §6.1).

A backend implements the nine core methods; ``StoreBase`` derives the other six from them. A pattern binds one
role: ``{"role": str, "value": Value | {"any": True} | {"any_unbound": True}, "position"?: int}``.

Errors carry ``.codes`` and ``.info``: ``ValidationError`` (layers C and S, and D002, D008, D010 and D020 on
writes), ``KeyCollision`` (D016), ``VersionError`` (D011-D014, D018), ``ConcurrencyError`` (D019), ``NotFound``
and ``CapabilityMissing(flag)``.
"""
from __future__ import annotations

from typing import (Any, Collection, Iterable, Iterator, Literal, Mapping, Protocol, Sequence, TypedDict, Union,
                    runtime_checkable)

from .where import DEFAULT_WHERE, Where

__all__ = [
    "CORE_METHODS",
    "DERIVED_METHODS",
    "INTERFACE_VERSION",
    "METHODS",
    "RECORD_FORMAT",
    "Clock",
    "LoadReport",
    "Pattern",
    "Receipt",
    "Record",
    "Store",
    "StoreInfo",
    "Walk",
]

INTERFACE_VERSION = "khg-store/1.0.0"
RECORD_FORMAT = "khg-record/1.0.0"
CORE_METHODS = ("info", "put", "apply", "load", "get", "history", "incident", "find", "iter_records")
DERIVED_METHODS = ("get_many", "degree", "find_by_key", "supersession_walk", "export", "close")
METHODS = CORE_METHODS + DERIVED_METHODS

Record = dict[str, Any]
#: ``{"role", "value", "position"?}``; the value is a C1 value, ``{"any": True}`` or ``{"any_unbound": True}``.
Pattern = dict[str, Any]


@runtime_checkable
class Clock(Protocol):
    """``store.SystemClock``; ``store.ScenarioClock(start, step)`` for the conformance suite."""

    def now(self) -> str:
        """The current time, RFC 3339 UTC."""
        ...

    def tick(self) -> str:
        """Advance and return the new ``now()``."""
        ...

    def set(self, at: str) -> None:
        """Move the clock to ``at``."""
        ...


class StoreInfo(TypedDict):
    """What ``info()`` returns."""

    interface_version: str  # "khg-store/1.0.0"
    record_format: str  # "khg-record/1.0.0"
    capabilities: frozenset[str]
    store_id: str
    header: dict[str, Any] | None  # the kept document header (§6.2)
    contracts: dict[str, str]  # khg_contracts.CONTRACTS (§11)


class Receipt(TypedDict):
    """What a write returns: ``records`` are ``(id, version, created | versioned | noop)`` sorted by id, ``at`` the
    transaction time, ``warnings`` the ``[{code: "KHG-L008", ids}]`` possible overlaps of the written records."""

    records: list[tuple[str, int, str]]
    at: str
    warnings: list[dict[str, Any]]


class LoadReport(TypedDict):
    """What ``load`` returns: the ids and versions loaded, the ids skipped for a missing flag, the seconds taken."""

    records: int
    versions: int
    skipped: list[str]
    seconds: float


class Walk(TypedDict):
    """What ``supersession_walk`` returns: steps ``{depth, via, reason, from, to}`` and ``terminal`` ``[{id,
    status}]``."""

    start: str
    direction: str
    steps: list[dict[str, Any]]
    terminal: list[dict[str, Any]]


@runtime_checkable
class Store(Protocol):
    """The C2 store interface: nine core methods and six derived ones (``StoreBase`` implements the latter)."""

    # core: a backend implements these nine
    def info(self) -> StoreInfo: ...

    def put(self, records: Union[Record, Sequence[Record]], *, actor: str, at: str | None = None,
            expect: Mapping[str, int] | None = None) -> Receipt: ...

    def apply(self, event: Mapping[str, Any], *, actor: str, at: str | None = None) -> Receipt: ...

    def load(self, container: Union[Mapping[str, Any], Iterable[Record]], *, header: Mapping[str, Any] | None = None,
             at: str | None = None, on_missing: Literal["raise", "skip"] = "raise") -> LoadReport: ...

    def get(self, id: str, *, as_at: str | None = None, version: int | None = None) -> Record | None: ...

    def history(self, id: str) -> list[Record]: ...

    def incident(self, node: str, *, role: str | None = None, relation: str | None = None, where: Where = DEFAULT_WHERE,
                 limit: int | None = None, after: str | None = None) -> list[Record]: ...

    def find(self, relation: str, pattern: Sequence[Pattern], *, match: Literal["at_least", "exact"] = "at_least",
             where: Where = DEFAULT_WHERE, limit: int | None = None, after: str | None = None) -> list[Record]: ...

    def iter_records(self, *, content: Literal["snapshot", "history"] = "snapshot",
                     as_at: str | None = None) -> Iterator[Record]: ...

    # derived: StoreBase implements these six from the core
    def get_many(self, ids: Iterable[str], *, as_at: str | None = None) -> dict[str, Record]: ...

    def degree(self, node: str, *, role: str | None = None, relation: str | None = None,
               where: Where = DEFAULT_WHERE) -> int: ...

    def find_by_key(self, relation: str, key: Sequence[Pattern], *, where: Where = DEFAULT_WHERE) -> list[Record]: ...

    def supersession_walk(self, id: str, *, direction: Literal["forward", "backward"] = "forward",
                          as_at: str | None = None) -> Walk: ...

    def export(self, format: Literal["khg-json", "khg-jsonl", "hif"] = "khg-jsonl", *,
               content: Literal["snapshot", "history"] = "snapshot", as_at: str | None = None,
               relations: Collection[str] | None = None, header: Mapping[str, Any] | None = None,
               literal_nodes: Literal["shared", "per_binding"] = "shared") -> str | dict[str, Any]: ...

    def close(self) -> None: ...
