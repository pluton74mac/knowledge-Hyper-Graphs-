"""``render_text``: a fact as one line of text, format ``khg-render/1`` (DESIGN §2.10).

The relation's label, then ``role: value`` groups in parentheses separated by ``; ``: core usages first, then
qualifier usages, each in the relation's usage order; the fillers of one role in canonical binding order, joined
by ``, ``. An entity renders as its label (else its id), a literal as its §4.2 label, ``somevalue`` as
``some value``, ``novalue`` as ``no value``, ``unbound`` as ``?var`` and a nested fact as ``[<fact id>]``. An
interval relation adds `` [start, end)``, with ``…`` for an absent bound. Meta bindings are omitted.

Labels: ``labels`` maps entity ids to labels; a relation or role id found there is used as its label too.
Otherwise a relation renders as its schema ``label`` (else its id) and a role as its usage's local ``label``
(else its id).
"""
from __future__ import annotations

from typing import Any, Mapping

from ._common import SchemaLike, as_schema, bindings, hyperedge, value_kind
from .canonical import binding_sort_key
from .values import literal_label

__all__ = ["RENDER_FORMAT", "render_text", "render_value"]

RENDER_FORMAT = "khg-render/1"
ABSENT = "…"


def render_value(value: Mapping[str, Any], labels: Mapping[str, str] | None = None) -> str:
    """One value as ``render_text`` writes it."""
    labels = labels or {}
    kind = value_kind(value)
    if kind == "entity":
        return labels.get(value["entity"], value["entity"])
    if kind == "literal":
        return literal_label(value["literal"])
    if kind == "fact":
        return f"[{value['fact']}]"
    if kind == "special":
        return {"somevalue": "some value", "novalue": "no value"}[value["special"]]
    return "?" + value["unbound"]["var"]


def render_text(record: Mapping[str, Any], labels: Mapping[str, str] | None, *, schema: SchemaLike) -> str:
    """``khg-render/1`` text of a hyperedge (S001/S002 when its relation or a role is not in the schema)."""
    hyperedge(record)
    s = as_schema(schema)
    labels = labels or {}
    rel = record.get("relation")
    decl = s.relation(rel)
    bs = sorted(bindings(record), key=binding_sort_key)
    usages = s.usages(rel)
    for b in bs:
        s.usage(rel, b.get("role"))  # every role must be declared
    parts = []
    for slot in ("core", "qualifier"):
        for u in usages:
            if u["slot"] != slot:
                continue
            fillers = [render_value(b["value"], labels) for b in bs if b["role"] == u["role"]]
            if fillers:
                parts.append(f"{labels.get(u['role'], u.get('label', u['role']))}: " + ", ".join(fillers))
    text = f"{labels.get(rel, decl.get('label', rel))}({'; '.join(parts)})"
    tm = s.time_model(rel)
    if tm.get("model") == "interval":
        def bound(role: str) -> str:
            b = next((x for x in bs if x["role"] == role), None)
            return ABSENT if b is None else render_value(b["value"], labels)
        text += f" [{bound(tm['start'])}, {bound(tm['end'])})"
    return text
