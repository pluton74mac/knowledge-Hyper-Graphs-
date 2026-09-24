"""The derived block: arity, the three keys and ``valid_time`` (DESIGN §2.4, §2.5, §2.6, §2.9).

- **Arity** counts the core and qualifier bindings whose value is an entity, a literal, a fact or ``somevalue``; a
  repeated filler counts once per binding. Beside it: ``core_arity``; ``statement_arity`` (arity plus the time
  bindings that have a value); ``distinct_fillers`` (each ``somevalue`` counts as distinct). A goal reports
  ``n_bound`` and ``n_unbound`` instead. Bins are ``0-1``, ``2``, ``3``, ``4`` and ``5+``.
- **content_key** is ``digest("khg-content-key/1", {relation, bindings})`` over the core, qualifier and time bindings
  as ``[role, position, value identity]``, sorted by their canonical JSON; **core_key** is the same over the core
  bindings (``khg-core-key/1``); **key_digest** (``khg-key-digest/1``) covers the relation's key roles, and is None
  without a key, when a key role is absent, or when a key role holds a special or unbound value.
- Bids, evidence, derived fields, rank, visibility, confidence and text never enter a key; meta bindings never do.

Lifecycle records have no derived block (they are excluded from arity and keys, §2.7).
"""
from __future__ import annotations

from typing import Any, Mapping

from .. import jsonio
from ..schema import Schema
from ._common import SchemaLike, as_schema, bindings, hyperedge, is_special, value_kind
from .canonical import canonical_container
from .validity import valid_time
from .values import identity_key, value_identity

__all__ = [
    "CONTENT_SLOTS",
    "arity",
    "arity_bin",
    "content_bindings",
    "content_key",
    "core_key",
    "derive",
    "key_digest",
    "with_derived",
]

#: The slots whose bindings are content: they enter ``content_key`` (meta bindings never do).
CONTENT_SLOTS = ("core", "qualifier", "time")
_COUNTED = ("entity", "literal", "fact")


def content_bindings(record: Mapping[str, Any], schema: SchemaLike,
                     slots: tuple[str, ...] = CONTENT_SLOTS) -> list[Mapping[str, Any]]:
    """The bindings of ``record`` whose role is in one of ``slots`` (S001/S002 for an undeclared relation or
    role)."""
    hyperedge(record)
    s = as_schema(schema)
    rel = record.get("relation")
    return [b for b in bindings(record) if s.slot(rel, b.get("role")) in slots]


def _tuple(b: Mapping[str, Any]) -> list[Any]:
    return [b["role"], b.get("position"), value_identity(b["value"])]


def _key(domain: str, relation: str, bs: list[Mapping[str, Any]]) -> str:
    tuples = sorted((_tuple(b) for b in bs), key=jsonio.canonical)
    return jsonio.digest(domain, {"relation": relation, "bindings": tuples})


def content_key(record: Mapping[str, Any], schema: SchemaLike) -> str:
    """``khg-content-key/1`` over the core, qualifier and time bindings: dedup (P3a) and stability (P9)."""
    bs = content_bindings(record, schema)
    return _key("khg-content-key/1", record["relation"], bs)


def core_key(record: Mapping[str, Any], schema: SchemaLike) -> str:
    """``khg-core-key/1`` over the core bindings: the leak check and the verdict key."""
    bs = content_bindings(record, schema, ("core",))
    return _key("khg-core-key/1", record["relation"], bs)


def key_digest(record: Mapping[str, Any], schema: SchemaLike) -> str | None:
    """``khg-key-digest/1`` over the relation's key roles, or None (no key, a key role absent, or a key role holding
    a special or unbound value: the fact is then exempt from collisions)."""
    hyperedge(record)
    s = as_schema(schema)
    key = s.key(record.get("relation"))
    if not key:
        return None
    roles = set(key["roles"])
    kb = [b for b in bindings(record) if b.get("role") in roles]
    if {b["role"] for b in kb} != roles:
        return None
    if any(value_kind(b.get("value")) not in _COUNTED for b in kb):
        return None
    return _key("khg-key-digest/1", record["relation"], kb)


def _goal_counts(record: Mapping[str, Any]) -> dict[str, int]:
    bs = bindings(record)
    n_bound = sum(1 for b in bs if value_kind(b.get("value")) != "unbound")
    return {"n_bound": n_bound, "n_unbound": len(bs) - n_bound}


def _counts(record: Mapping[str, Any], schema: Schema) -> dict[str, int]:
    rel = record["relation"]
    core = timed = somevalues = 0
    counted: list[Mapping[str, Any]] = []
    distinct: set[str] = set()
    for b in content_bindings(record, schema):
        v = b.get("value")
        somevalue = is_special(v, "somevalue")
        if not (somevalue or value_kind(v) in _COUNTED):
            continue  # novalue and unbound have no value to count
        slot = schema.slot(rel, b["role"])
        if slot == "time":
            timed += 1
            continue
        counted.append(b)
        core += slot == "core"
        if somevalue:
            somevalues += 1
        else:
            distinct.add(identity_key(v))
    return {"arity": len(counted), "core_arity": core, "statement_arity": len(counted) + timed,
            "distinct_fillers": len(distinct) + somevalues}


def arity(record: Mapping[str, Any], schema: SchemaLike) -> dict[str, int]:
    """``{arity, core_arity, statement_arity, distinct_fillers}``, or ``{n_bound, n_unbound}`` for a goal.
    ``ValueError`` for a lifecycle record, which has no arity (§2.7)."""
    hyperedge(record)
    if record.get("status") == "goal":
        return _goal_counts(record)
    s = as_schema(schema)
    if s.kind(record.get("relation")) == "lifecycle":
        raise ValueError(f"{record.get('id')!r}: lifecycle records have no arity (§2.7)")
    return _counts(record, s)


def arity_bin(n: int) -> str:
    """The arity bin of §2.4: ``0-1``, ``2``, ``3``, ``4`` or ``5+``."""
    return "0-1" if n <= 1 else "5+" if n >= 5 else str(n)


def derive(record: Mapping[str, Any], schema: SchemaLike) -> dict[str, Any]:
    """The ``derived`` block of a record: the arity family, the three keys and ``valid_time`` for a fact;
    ``{n_bound, n_unbound}`` for a goal; ``{}`` for an entity or a lifecycle record. ``ValueError`` (a
    ``ValidationError`` with its code) on an invalid record."""
    if not isinstance(record, Mapping):
        raise ValueError(f"a record is an object, not {type(record).__name__}")
    if record.get("kind") != "hyperedge":
        return {}
    if record.get("status") == "goal":
        return _goal_counts(record)
    s = as_schema(schema)
    if s.kind(record.get("relation")) == "lifecycle":
        return {}
    return {**_counts(record, s), "content_key": content_key(record, s), "core_key": core_key(record, s),
            "key_digest": key_digest(record, s), "valid_time": valid_time(record, s)}


def with_derived(container: Mapping[str, Any], schema: SchemaLike) -> dict[str, Any]:
    """The store and export form of a container: canonical records in canonical order, each hyperedge with its
    ``derived`` block (entities and lifecycle records carry none)."""
    s = as_schema(schema)
    out = canonical_container(container)
    for r in out["records"]:
        d = derive(r, s)
        if d:
            r["derived"] = d
    return out
