"""Facts prepared for scoring, and value matching (DESIGN §9.1).

- Entities match by id after following ``redirect_to`` (``record.resolve_redirects``) over the entity records the
  inputs carry.
- Literals match under ``truncate_to_gold`` (value refinement, a prediction at least as precise as the gold and
  inside its window, whatever the calendars) or ``exact`` (value identity). With ``calendar="as_written"`` a
  predicted date is read in the gold's calendar before it is compared.
- ``somevalue`` and ``novalue`` match only themselves; facts match by id.

A fact's bindings are its content bindings (core, qualifier and time), each with its role, position and value.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .. import jsonio
from ..record import (
    binding_sort_key,
    canonical_literal,
    canonical_value,
    content_bindings,
    content_key,
    core_key,
    identity_key,
    resolve_redirects,
    value_kind,
    value_refines,
)
from ..schema import Schema
from ._common import arity_pair

__all__ = ["Binding", "Fact", "Matcher", "entity_index", "prepare"]

LITERAL_MATCHES = ("truncate_to_gold", "exact")
CALENDARS = ("strict", "as_written")


@dataclass(frozen=True)
class Binding:
    """A content binding ready for matching: role, position, canonical value, value kind and identity key."""

    role: str
    position: int | None
    value: Mapping[str, Any]
    kind: str
    ident: str

    @property
    def triple(self) -> tuple[str, int | None, str]:
        return self.role, self.position, self.ident


@dataclass(frozen=True)
class Fact:
    """A hyperedge prepared for scoring."""

    id: str
    relation: str
    bindings: tuple[Binding, ...]
    core: tuple[Binding, ...]
    content_key: str
    core_key: str
    arity: int
    model_arity: int
    primary: tuple[str, str] | None
    has_literal: bool = False

    @property
    def core_signature(self) -> tuple[str, tuple[tuple[str, int | None, str], ...]]:
        return self.relation, tuple(sorted(b.triple for b in self.core))


def entity_index(records: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Entity records by id (the first record of an id wins)."""
    out: dict[str, Mapping[str, Any]] = {}
    for e in records:
        if isinstance(e, Mapping) and e.get("kind", "entity") == "entity" and isinstance(e.get("id"), str):
            out.setdefault(e["id"], e)
    return out


def _redirected(record: Mapping[str, Any], entities: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    out = dict(record)
    bs = []
    for b in record.get("bindings") or []:
        v = b.get("value") if isinstance(b, Mapping) else None
        if isinstance(v, Mapping) and set(v) == {"entity"} and isinstance(v["entity"], str) and entities:
            target = resolve_redirects(v["entity"], entities)
            if target != v["entity"]:
                b = {**b, "value": {"entity": target}}
        bs.append(b)
    out["bindings"] = bs
    return out


def prepare(record: Mapping[str, Any], schema: Schema, entities: Mapping[str, Mapping[str, Any]], *,
            fid: str | None = None, core_roles: str = "slot") -> Fact:
    """A hyperedge as a ``Fact``: redirected entity values, content bindings in canonical order, the core set
    (``core_roles="slot"``: the core slot; ``"key"``: the relation's key roles, else the core slot), the keys and
    both arities. Raises ``ValidationError`` (C and S codes) on a malformed record."""
    if not isinstance(record, Mapping) or record.get("kind") != "hyperedge":
        raise ValueError("a scored fact is a C1 hyperedge record")
    if record.get("status") == "goal":
        raise ValueError(f"{record.get('id')!r}: goals are not scored")
    r = _redirected(record, entities)
    rel = r["relation"]
    bs = sorted(content_bindings(r, schema), key=binding_sort_key)
    prepared = tuple(Binding(b["role"], b.get("position"), canonical_value(b["value"]), value_kind(b["value"]),
                             identity_key(b["value"])) for b in bs)
    if core_roles == "key" and schema.key(rel):
        wanted = set(schema.key(rel)["roles"])  # type: ignore[index]
        core = tuple(b for b in prepared if b.role in wanted)
    else:
        core = tuple(b for b in prepared if schema.slot(rel, b.role) == "core")
    arity, m_arity = arity_pair(r, schema)
    primary = schema.relation(rel).get("primary")
    return Fact(id=str(fid if fid is not None else r.get("id")), relation=rel, bindings=prepared, core=core,
                content_key=content_key(r, schema), core_key=core_key(r, schema), arity=arity, model_arity=m_arity,
                primary=(primary["subject"], primary["object"]) if primary else None,
                has_literal=any(b.kind == "literal" for b in prepared))


class Matcher:
    """Value and binding matching under a literal rule and a calendar reading (prediction first, gold second)."""

    def __init__(self, literal_match: str = "truncate_to_gold", calendar: str = "strict"):
        if literal_match not in LITERAL_MATCHES:
            raise ValueError(f"literal_match must be one of {LITERAL_MATCHES}, not {literal_match!r}")
        if calendar not in CALENDARS:
            raise ValueError(f"calendar must be one of {CALENDARS}, not {calendar!r}")
        self.literal_match = literal_match
        self.calendar = calendar
        self._cache: dict[tuple[str, str], bool] = {}

    @property
    def by_identity(self) -> bool:
        """True when matching is identity of values, so multiset intersections count matchings."""
        return self.literal_match == "exact" and self.calendar == "strict"

    def plain(self, *facts: Fact) -> bool:
        """True when identity decides every match between these facts: the exact rule, or no literal at all."""
        return self.by_identity or not any(f.has_literal for f in facts)

    def values(self, p: Binding, g: Binding) -> bool:
        """Does the predicted value ``p`` match the gold value ``g``?"""
        if p.kind != g.kind:
            return False
        if p.kind != "literal" or self.by_identity:
            return p.ident == g.ident
        key = (jsonio.canonical(p.value), jsonio.canonical(g.value))
        hit = self._cache.get(key)
        if hit is None:
            hit = self._cache[key] = self._literals(p.value["literal"], g.value["literal"])
        return hit

    def _literals(self, p: Mapping[str, Any], g: Mapping[str, Any]) -> bool:
        if self.calendar == "as_written" and p.get("datatype") == "time" and g.get("datatype") == "time":
            calendar = canonical_literal(g).get("calendar")
            if calendar:
                p = {**p, "calendar": calendar}
        pv, gv = {"literal": p}, {"literal": g}
        if self.literal_match == "exact":
            return identity_key(pv) == identity_key(gv)
        return value_refines(pv, gv)

    def bindings(self, p: Binding, g: Binding) -> bool:
        """Same role, same position, matching value."""
        return p.role == g.role and p.position == g.position and self.values(p, g)
