"""The §4.2 order of a ``khg-hif`` file, recomputed from the node ``attrs`` (DESIGN §4.2, §5; critique GL-09).

Entity nodes by id, then derived nodes by id; edges by id; incidences by edge, then in canonical binding order
(role, position, value), where the value is the one the incidence's node carries. ``to_hif`` writes this order,
and the loaders use ``canonical_order`` to export profile files in it, whatever order a library returns.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from ..record import binding_sort_key
from ._doc import attrs_of
from .nodes import node_value

__all__ = ["canonical_order", "incidence_sort_key", "node_sort_key"]


def node_sort_key(node: Mapping[str, Any]) -> tuple[bool, str]:
    """Entity nodes (ids without ``_:``) first, then derived nodes; each by id."""
    nid = str(node.get("node"))
    return (nid.startswith("_:"), nid)


def incidence_sort_key(incidence: Mapping[str, Any], nodes: Mapping[Any, Mapping[str, Any]]) -> tuple[Any, ...]:
    """By edge, then in canonical binding order of (role, role-position, the value of the incidence's node).
    ``nodes`` maps node ids to node records. An incidence whose node has no record carries an entity value, as
    ``to_hif`` writes it: every derived node is declared, so only an entity outside the container (one that is not
    complete) is not."""
    attrs = attrs_of(incidence)
    nid = incidence.get("node")
    node = nodes.get(nid)
    binding = {"role": attrs.get("role"), "position": attrs.get("role-position", 0),
               "value": node_value(node) if node is not None else {"entity": nid}}
    return (str(incidence.get("edge")), *binding_sort_key(binding))


def canonical_order(hif: Mapping[str, Any]) -> dict[str, Any]:
    """A copy of a ``khg-hif`` document with its nodes, edges and incidences in the §4.2 order (stable: records
    with equal keys keep their order)."""
    out = copy.deepcopy(dict(hif))
    nodes = [n for n in out.get("nodes") or [] if isinstance(n, Mapping)]
    by_id = {n.get("node"): n for n in nodes if isinstance(n.get("node"), (str, int))}
    if "nodes" in out:
        out["nodes"] = sorted(nodes, key=node_sort_key)
    if "edges" in out:
        out["edges"] = sorted((e for e in out["edges"] or [] if isinstance(e, Mapping)),
                              key=lambda e: str(e.get("edge")))
    if "incidences" in out:
        out["incidences"] = sorted((i for i in out["incidences"] or [] if isinstance(i, Mapping)),
                                   key=lambda i: incidence_sort_key(i, by_id))
    return out
