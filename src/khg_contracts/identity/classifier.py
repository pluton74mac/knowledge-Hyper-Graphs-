"""``relate``: how an incoming fact relates to a stored one (non-normative; DESIGN §2.9, [DB §2.18-§2.19]).

The labels, in the order they are tried:

1. facts of different relations are ``distinct``;
2. the class of §2.5, from refinement: ``duplicate`` (equal content keys), ``refines`` (a ⊑ b) or ``generalises``
   (b ⊑ a);
3. ``negation_conflict``: on some core role one fact says ``novalue`` and the other binds it (``somevalue``
   included), every other core role holds the same values, and the validities possibly overlap;
4. equal non-null key digests: ``key_timeline`` when the key is temporal and the definite windows do not overlap
   (the §2.6 ruling: undated facts have no definite validity), else ``key_conflict``;
5. otherwise ``distinct``.

P7 may replace this classifier; the store never calls it. What a caller does on a key conflict is the §2.5 action
(``record.keys``).
"""
from __future__ import annotations

from typing import Any, Mapping

from ..record import bounds, content_bindings, definite_overlap, identity_key, key_digest, possible_overlap
from ..record._common import SchemaLike, as_schema, hyperedge, is_special
from ..record.keys import classify
from ..schema import Schema

__all__ = ["LABELS", "relate"]

LABELS = ("duplicate", "refines", "generalises", "distinct", "key_conflict", "key_timeline", "negation_conflict")


def relate(a: Mapping[str, Any], b: Mapping[str, Any], *, schema: SchemaLike) -> str:
    """One of ``LABELS`` for an incoming fact ``a`` and a stored fact ``b``. ``schema`` is a ``Schema`` or a schema
    document (used unchecked); a malformed record raises ``ValidationError`` with its code."""
    hyperedge(a)
    hyperedge(b)
    if a.get("relation") != b.get("relation"):
        return "distinct"
    s = as_schema(schema)
    cls = classify(a, b, s)
    if cls != "distinct":
        return cls
    if _negation_conflict(a, b, s):
        return "negation_conflict"
    ka, kb = key_digest(a, s), key_digest(b, s)
    if ka is not None and ka == kb:
        key = s.key(a["relation"]) or {}
        if key.get("temporal") and not definite_overlap(bounds(a, s), bounds(b, s)):
            return "key_timeline"
        return "key_conflict"
    return "distinct"


def _core(record: Mapping[str, Any], s: Schema) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = {}
    for x in content_bindings(record, s, ("core",)):
        out.setdefault(x["role"], []).append(x["value"])
    return out


def _negation_conflict(a: Mapping[str, Any], b: Mapping[str, Any], s: Schema) -> bool:
    ra, rb = _core(a, s), _core(b, s)
    roles = sorted(set(ra) | set(rb))
    negated = [r for r in roles if ra.get(r) and rb.get(r) and any(is_special(v, "novalue") for v in ra[r])
               != any(is_special(v, "novalue") for v in rb[r])]
    if not negated:
        return False
    same_rest = all(sorted(map(identity_key, ra.get(r, []))) == sorted(map(identity_key, rb.get(r, [])))
                    for r in roles if r not in negated)
    return same_rest and possible_overlap(bounds(a, s), bounds(b, s))
