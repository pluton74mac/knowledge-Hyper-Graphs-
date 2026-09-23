"""The ten capability flags of C2 (DESIGN §6.3) and what records, patterns and filters need.

| Flag | Covers |
|---|---|
| ``literal_values``, ``special_values`` | literal bindings (value identity); ``somevalue`` and ``novalue`` |
| ``goals`` | status ``goal``, ``unbound`` values and patterns |
| ``nesting`` | fact values in fact relations; ``incident(fact id)`` |
| ``ordered_roles`` | positions |
| ``valid_time`` | ``as_of``, ``valid_mode``, ``end_validity``, temporal keys |
| ``transaction_time`` | ``as_at``, ``get(version=)`` |
| ``key_constraint`` | the key invariant on writes |
| ``atomic_writes`` | multi-record calls (a batch, ``supersede``, a transition that writes a record) |
| ``history_export`` | ``content="history"`` in ``iter_records``, ``export`` and ``load`` |

A missing flag makes the method raise ``CapabilityMissing`` and the scenarios that need it ``inapplicable``. The
functions here read structure defensively: what they cannot read needs no flag (the validator reports it).
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..schema import LIFECYCLE_RELATIONS

__all__ = ["ALL_FLAGS", "DATA_FLAGS", "FLAGS", "capabilities", "data_flags", "pattern_flags", "value_flags",
           "where_flags"]

FLAGS = ("literal_values", "special_values", "goals", "nesting", "ordered_roles", "valid_time", "transaction_time",
         "key_constraint", "atomic_writes", "history_export")
ALL_FLAGS = frozenset(FLAGS)
#: The flags a record's content needs (the others belong to operations).
DATA_FLAGS = ("literal_values", "special_values", "goals", "nesting", "ordered_roles")


def capabilities(flags: Iterable[str] | None) -> frozenset[str]:
    """``flags`` as a frozenset (every flag when None); ``ValueError`` for an unknown flag."""
    if flags is None:
        return ALL_FLAGS
    if isinstance(flags, (str, bytes)):
        raise TypeError("capabilities is a collection of flag names, not a string")
    out = frozenset(flags)
    unknown = sorted(str(f) for f in out if f not in ALL_FLAGS)
    if unknown:
        raise ValueError(f"unknown capability flags {', '.join(unknown)}; the flags are {', '.join(FLAGS)}")
    return out


def _kind(value: Any) -> str | None:
    if isinstance(value, Mapping) and len(value) == 1:
        (k,) = value.keys()
        return k if isinstance(k, str) else None
    return None


def value_flags(value: Any, *, lifecycle: bool = False) -> set[str]:
    """The flags a binding value needs; a fact value in a lifecycle relation needs none."""
    kind = _kind(value)
    if kind == "literal":
        return {"literal_values"}
    if kind == "special":
        return {"special_values"}
    if kind == "unbound":
        return {"goals"}
    if kind == "fact" and not lifecycle:
        return {"nesting"}
    return set()


def data_flags(record: Any) -> frozenset[str]:
    """The flags the content of a record needs: its literal, special, unbound and nested fact values, its positions
    and a ``goal`` status. Entities need none."""
    if not isinstance(record, Mapping) or record.get("kind") != "hyperedge":
        return frozenset()
    out: set[str] = set()
    if record.get("status") == "goal":
        out.add("goals")
    lifecycle = record.get("relation") in LIFECYCLE_RELATIONS
    bindings = record.get("bindings")
    for b in bindings if isinstance(bindings, list) else []:
        if not isinstance(b, Mapping):
            continue
        out |= value_flags(b.get("value"), lifecycle=lifecycle)
        if "position" in b:
            out.add("ordered_roles")
    return frozenset(out)


def pattern_flags(pattern: Iterable[Any], *, lifecycle: bool = False) -> set[str]:
    """The flags a ``find`` pattern needs: its values as in a record, ``any_unbound`` (goals) and positions."""
    out: set[str] = set()
    for p in pattern:
        if not isinstance(p, Mapping):
            continue
        value = p.get("value")
        if isinstance(value, Mapping) and value.get("any_unbound") is True:
            out.add("goals")
        elif not (isinstance(value, Mapping) and value.get("any") is True):
            out |= value_flags(value, lifecycle=lifecycle)
        if "position" in p:
            out.add("ordered_roles")
    return out


def where_flags(where: Any) -> set[str]:
    """The flags a ``Where`` needs: ``valid_time`` for ``as_of`` or a ``possible`` read, ``transaction_time`` for
    ``as_at``, ``goals`` to read status ``goal``."""
    out: set[str] = set()
    if where.as_of is not None or where.valid_mode != "definite":
        out.add("valid_time")
    if where.as_at is not None:
        out.add("transaction_time")
    if "goal" in where.status:
        out.add("goals")
    return out
