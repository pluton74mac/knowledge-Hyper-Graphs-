"""What every adapter shares (DESIGN §2): the declared flags, what a backend cannot hold, and a description of the
engine for the results files.

``cannot_hold(record)`` (the ``TableStore`` hook, ruling 17) refuses, in this order:

1. a record the row layout cannot split: a hyperedge whose bindings are not ``{bid, role, value}`` objects with one
   value key (a trusted load does not validate; ``put`` and ``apply`` never get this far with one);
2. in an int64 backend (``INT64``), a record whose bound table has a finite instant beyond ±(2^62 − 2) seconds
   (ruling 4; ``rows.unheld_instants``);
3. whatever the adapter adds (``_cannot_hold``: TypeDB's single-typed instances, for one).

The refusal is ``TableStore``'s: a ``ValidationError`` without a code, ``info["cannot_hold"]`` holding the dict
returned here; ``load(on_missing="skip")`` lists the id in ``LoadReport.skipped``. ``refusals`` keeps the last reason
given for each id (the fidelity report states why a load skipped a record).

``Trips`` counts the calls each adapter makes to its engine, by kind (DESIGN §6.1).
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from khg_contracts.store import ALL_FLAGS

from .rows import INT64_HELD, unheld_instants

__all__ = ["AdapterMixin", "Trips"]


class Trips(Counter):
    """The engine calls an adapter made, by kind (the round trips of DESIGN §6.1): ``read``, a query that returns
    rows; ``write``, a statement or bulk call that changes data; ``tx``, a transaction's begin, commit, rollback or
    savepoint; ``file``, a file read or written (HIF). Every adapter counts at the one place it calls its engine."""

    def hit(self, kind: str, n: int = 1) -> None:
        self[kind] += n

    def calls(self) -> int:
        """Every call counted."""
        return sum(self.values())


def _malformed(record: Mapping[str, Any]) -> str | None:
    if not isinstance(record, Mapping) or record.get("kind") != "hyperedge":
        return None
    bindings = record.get("bindings")
    if bindings is None:
        return None
    if not isinstance(bindings, list):
        return "bindings is not a list"
    for b in bindings:
        if not isinstance(b, Mapping) or not isinstance(b.get("bid"), str) or not isinstance(b.get("role"), str):
            return "a binding without a string bid and role"
        v = b.get("value")
        if not isinstance(v, Mapping) or len(v) != 1:
            return "a binding value without exactly one key"
    return None


class AdapterMixin:
    """Flags, refusals and engine facts shared by the adapters."""

    #: The flags the adapter declares (``info()["capabilities"]`` when ``capabilities`` is None).
    FLAGS: frozenset[str] = ALL_FLAGS
    #: The engine, for the results files.
    ENGINE = "?"
    #: ``embedded`` or ``client-server``.
    KIND = "embedded"
    #: Whether the backend stores instants as int64 (then the ±2^62 guard applies).
    INT64 = True

    schema: Any
    #: The engine calls made so far (``Trips``); the adapters count them, ``khg_bakeoff.trips`` reads them.
    trips: Trips

    def cannot_hold(self, record: Mapping[str, Any]) -> dict[str, Any] | None:
        why = self._why_not(record)
        if why is not None and isinstance(record, Mapping) and isinstance(record.get("id"), str):
            self.refusals[record["id"]] = why  # why a load skipped it (the fidelity report)
        return why

    @property
    def refusals(self) -> dict[str, dict[str, Any]]:
        """The last refusal ``cannot_hold`` gave for each id."""
        got = self.__dict__.get("_refusals")
        if got is None:
            got = self.__dict__["_refusals"] = {}
        return got

    def _why_not(self, record: Mapping[str, Any]) -> dict[str, Any] | None:
        why = _malformed(record)
        if why is not None:
            return {"reason": "malformed_record", "detail": why}
        if self.INT64:
            bad = unheld_instants(record, self.schema)
            if bad:
                return {"reason": "instant_range", "instants": [str(x) for x in bad],
                        "held": f"|instant| <= {INT64_HELD} s (2^62 - 2)"}
        return self._cannot_hold(record)

    def _cannot_hold(self, record: Mapping[str, Any]) -> dict[str, Any] | None:
        return None

    def engine(self) -> dict[str, Any]:
        """The engine's name, version and kind (the results files record them)."""
        return {"engine": self.ENGINE, "version": self.engine_version(), "kind": self.KIND}

    def engine_version(self) -> str:
        return "?"
