"""The ids of derived nodes (DESIGN §4.2), used by the projections (§2.10) and by the HIF codec.

- ``_:lit:<32 hex>`` of ``digest("khg-literal-node/1", canonical literal)``: one node per literal value (shared);
- ``_:litb:<32 hex>`` of ``digest("khg-literal-binding/1", [record id, bid])``: one node per literal binding;
- ``_:sv:``, ``_:nv:`` or ``_:var:`` + ``<32 hex>`` of ``digest("khg-special-node/1", [record id, bid])``: one node per
  ``somevalue``, ``novalue`` or ``unbound`` binding;
- ``_:ref:<fact id>`` for a fact reference;
- ``khg:none``, the reserved id of an absent optional position in ``project.positional``.
"""
from __future__ import annotations

from typing import Any, Mapping

from .. import jsonio
from .values import canonical_literal

__all__ = ["NONE_ID", "SPECIAL_TAGS", "literal_binding_node_id", "literal_node_id", "ref_node_id", "special_node_id"]

NONE_ID = "khg:none"
#: value kind -> the tag of its derived node id
SPECIAL_TAGS = {"somevalue": "sv", "novalue": "nv", "unbound": "var"}
_HEX = 32


def literal_node_id(literal: Mapping[str, Any]) -> str:
    """``_:lit:`` + 32 hex digits of ``khg-literal-node/1`` over the canonical literal (C004, S006 when the literal
    is malformed)."""
    return "_:lit:" + jsonio.hexdigest("khg-literal-node/1", canonical_literal(literal))[:_HEX]


def literal_binding_node_id(record_id: str, bid: str) -> str:
    """``_:litb:`` + 32 hex digits of ``khg-literal-binding/1`` over ``[record id, bid]``."""
    return "_:litb:" + jsonio.hexdigest("khg-literal-binding/1", [record_id, bid])[:_HEX]


def special_node_id(kind: str, record_id: str, bid: str) -> str:
    """``_:sv:``, ``_:nv:`` or ``_:var:`` + 32 hex digits of ``khg-special-node/1`` over ``[record id, bid]``; ``kind``
    is ``somevalue``, ``novalue`` or ``unbound``."""
    try:
        tag = SPECIAL_TAGS[kind]
    except KeyError:
        raise ValueError(f"kind must be one of {', '.join(SPECIAL_TAGS)}, not {kind!r}") from None
    return f"_:{tag}:" + jsonio.hexdigest("khg-special-node/1", [record_id, bid])[:_HEX]


def ref_node_id(fact_id: str) -> str:
    """``_:ref:<fact id>``, the node of a fact reference."""
    return "_:ref:" + fact_id
