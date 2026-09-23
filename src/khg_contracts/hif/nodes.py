"""The nodes that carry binding values in HIF (DESIGN §4.2).

- An entity value is its entity's node.
- A literal is a derived node ``_:lit:<32 hex>`` shared by value (``literal_nodes="shared"``) or ``_:litb:<32 hex>``
  per binding (``"per_binding"``), with ``{khg-kind: "literal", label, khg-literal}``.
- ``somevalue``, ``novalue`` and ``unbound`` are one derived node per binding (``_:sv:``, ``_:nv:``, ``_:var:``).
- A fact value is the node ``_:ref:<fact id>`` with ``{khg-kind: "fact-ref", khg-ref}``, plus ``khg-external: true``
  when the fact is not in the file. ``khg-ref`` is authoritative: a reference is never inferred from id equality.

``node_value`` reads a node back into a C1 value, from its ``attrs`` only.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from ..record import (canonical_value, literal_binding_node_id, literal_label, literal_node_id, ref_node_id,
                      special_node_id, value_kind)
from ._doc import attrs_of

__all__ = ["node_value", "value_node"]


def value_node(record_id: str, binding: Mapping[str, Any], nodes: dict[str, dict[str, Any]], *,
               literal_nodes: str, present: Any) -> str:
    """The id of the node that carries ``binding``'s value in record ``record_id``; a derived node is added to
    ``nodes`` (id -> node record) when it is new. ``present`` holds the ids of the facts in the file. A malformed
    value raises ``ValidationError`` (C001, C002, C004, C010, S006)."""
    value = canonical_value(binding["value"])
    kind = value_kind(value)
    bid: str = binding["bid"]
    if kind == "entity":
        return value["entity"]
    if kind == "literal":
        lit = value["literal"]
        nid = literal_node_id(lit) if literal_nodes == "shared" else literal_binding_node_id(record_id, bid)
        nodes.setdefault(nid, {"node": nid, "attrs": {"khg-kind": "literal", "label": literal_label(lit),
                                                      "khg-literal": lit}})
        return nid
    if kind == "fact":
        fid = value["fact"]
        nid = ref_node_id(fid)
        attrs: dict[str, Any] = {"khg-kind": "fact-ref", "khg-ref": fid}
        if fid not in present:
            attrs["khg-external"] = True
        nodes.setdefault(nid, {"node": nid, "attrs": attrs})
        return nid
    if kind == "special":
        nid = special_node_id(value["special"], record_id, bid)
        nodes[nid] = {"node": nid, "attrs": {"khg-kind": value["special"]}}
        return nid
    nid = special_node_id("unbound", record_id, bid)
    nodes[nid] = {"node": nid, "attrs": {"khg-kind": "unbound", "khg-unbound": copy.deepcopy(value["unbound"])}}
    return nid


def node_value(node: Mapping[str, Any]) -> dict[str, Any] | None:
    """The C1 value a node carries, from its ``attrs``: ``{"entity": id}``, ``{"literal": ...}``,
    ``{"fact": ...}``, ``{"special": ...}`` or ``{"unbound": ...}``; None for a node without a known ``khg-kind``.
    The value is not checked (decoding checks the derived ids)."""
    if not isinstance(node, Mapping):
        return None
    attrs = attrs_of(node)
    kind = attrs.get("khg-kind")
    if kind == "entity":
        return {"entity": node.get("node")}
    if kind == "literal":
        return {"literal": copy.deepcopy(attrs.get("khg-literal"))}
    if kind == "fact-ref":
        return {"fact": copy.deepcopy(attrs.get("khg-ref"))}
    if kind in ("somevalue", "novalue"):
        return {"special": kind}
    if kind == "unbound":
        return {"unbound": copy.deepcopy(attrs.get("khg-unbound"))}
    return None
