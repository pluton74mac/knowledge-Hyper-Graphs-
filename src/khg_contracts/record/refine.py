"""The refinement order ⊑ on values and on facts (DESIGN §2.3, §2.9).

``value_refines(a, b)`` is a ⊑ b: ``a`` is at least as specific as ``b`` and says nothing ``b`` excludes.

- Equal identities refine each other; ``somevalue`` and ``unbound`` are refined by any entity, literal or fact;
  ``novalue`` refines only ``novalue``.
- ``time``: a's window lies inside b's and a's precision is at least b's, whatever the calendars.
- ``quantity``: the same unit, and a's interval (its bounds, else its amount) inside b's and narrower.
- ``geo``: the same globe, a finer precision, and a's point inside b's cell.
- ``string``, ``iri``, ``lang_string`` and ``boolean`` refine only by equality.

``fact_refines(a, b, schema)``: the same relation, and every core, qualifier and time binding of ``b`` has its own
refining binding in ``a`` (same role, same position for an ordered role; the matching is injective). Meta
bindings are ignored and ``complete`` roles keep their size. Mutual refinement is equal ``content_key``.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

from ..schema import Schema
from ._common import SchemaLike, as_schema, bindings, hyperedge, is_special, value_kind
from .values import canonical_literal, decimal, identity_key
from .windows import window_seconds

__all__ = ["value_refines", "fact_refines", "injective_match"]


def value_refines(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """a ⊑ b for two values (C and S codes on a malformed value)."""
    if identity_key(a) == identity_key(b):
        return True
    ka, kb = value_kind(a), value_kind(b)
    if kb == "unbound" or is_special(b, "somevalue"):
        return ka in ("entity", "literal", "fact")
    if ka != "literal" or kb != "literal":
        return False
    la, lb = canonical_literal(a["literal"]), canonical_literal(b["literal"])
    if la["datatype"] != lb["datatype"]:
        return False
    dt = la["datatype"]
    if dt == "time":
        (alo, ahi), (blo, bhi) = window_seconds(la), window_seconds(lb)
        return blo <= alo and ahi <= bhi and la["precision"] >= lb["precision"]
    if dt == "quantity":
        if la["unit"] != lb["unit"]:
            return False
        ia = (decimal(la.get("lower", la["amount"])), decimal(la.get("upper", la["amount"])))
        ib = (decimal(lb.get("lower", lb["amount"])), decimal(lb.get("upper", lb["amount"])))
        return ib[0] <= ia[0] and ia[1] <= ib[1] and ia != ib
    if dt == "geo":
        if la["globe"] != lb["globe"] or decimal(la["precision"]) >= decimal(lb["precision"]):
            return False
        half = decimal(lb["precision"]) / 2
        return (abs(decimal(la["lat"]) - decimal(lb["lat"])) <= half
                and abs(decimal(la["lon"]) - decimal(lb["lon"])) <= half)
    return False


def injective_match(n_from: int, n_to: int, ok: Callable[[int, int], bool]) -> bool:
    """True when every i in ``range(n_from)`` can be paired with its own j in ``range(n_to)`` such that
    ``ok(i, j)`` (bipartite matching by augmenting paths; deterministic)."""
    if n_from > n_to:
        return False
    edges = [[j for j in range(n_to) if ok(i, j)] for i in range(n_from)]
    owner: list[int | None] = [None] * n_to

    def augment(i: int, seen: list[bool]) -> bool:
        for j in edges[i]:
            if not seen[j]:
                seen[j] = True
                o = owner[j]
                if o is None or augment(o, seen):
                    owner[j] = i
                    return True
        return False

    return all(augment(i, [False] * n_to) for i in range(n_from))


def _by_role(record: Mapping[str, Any], schema: Schema, rel: str) -> dict[str, list[Mapping[str, Any]]]:
    out: dict[str, list[Mapping[str, Any]]] = {}
    for b in bindings(record):
        if schema.slot(rel, b.get("role")) != "meta":
            out.setdefault(b["role"], []).append(b)
    return out


def fact_refines(a: Mapping[str, Any], b: Mapping[str, Any], schema: SchemaLike) -> bool:
    """f′ ⊑ f with f′ = ``a`` and f = ``b`` (§2.9); S001/S002 when a role is not in the schema."""
    hyperedge(a)
    hyperedge(b)
    if a.get("relation") != b.get("relation"):
        return False
    s = as_schema(schema)
    rel = b["relation"]
    ra, rb = _by_role(a, s, rel), _by_role(b, s, rel)
    for role in sorted(set(ra) | set(rb)):
        ba, bb = ra.get(role, []), rb.get(role, [])
        u = s.usage(rel, role)
        nv_a = any(is_special(x["value"], "novalue") for x in ba)
        nv_b = any(is_special(x["value"], "novalue") for x in bb)
        if nv_a != nv_b and bb:  # novalue refines only novalue; a role b leaves unbound may gain one
            return False
        if u.get("complete") and len(ba) != len(bb):
            return False
        if not _fillers_refine(ba, bb, bool(u.get("ordered"))):
            return False
    return True


def _fillers_refine(ba: list[Mapping[str, Any]], bb: list[Mapping[str, Any]], ordered: bool) -> bool:
    """Every binding of ``bb`` has its own refining binding in ``ba`` (at the same position for an ordered role)."""

    def ok(i: int, j: int) -> bool:
        if ordered and bb[i].get("position") != ba[j].get("position"):
            return False
        return value_refines(ba[j]["value"], bb[i]["value"])

    return injective_match(len(bb), len(ba), ok)
