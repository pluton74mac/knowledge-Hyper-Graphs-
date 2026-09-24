"""The loader context: what a HIF file holds and neither library can (DESIGN §5; critique GL-03, GL-05, GL-08).

- the metadata (authoritative; nothing is written into XGI network attributes) and the ``network-type``;
- every incidence record as loaded, keyed by (edge, ``khg-bid``) in profile files and by (edge, ordinal) in other
  files, and their source order. XGI holds no incidence attrs or weights, so for XGI these records are the source
  of truth; for HyperNetX the cells are, and the loaded records tell a move from a new record;
- the loaded weights of nodes and edges with their JSON number type, so ``2`` stays ``2``;
- which nodes were isolated and which edges were empty in the loaded file;
- the declared node and edge ids in source order, and which declarations carried an ``attrs`` object;
- the records ``Bundle.label`` gave to new XGI memberships.

A context is built once per load and read by every export; only ``labels`` changes.
"""
from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from ._common import TypedKey, tkey

__all__ = ["Context", "RecordKey", "build_context", "record_key"]

#: ``(typed edge, khg-bid)`` in profile files; ``(typed edge, ("#", ordinal))`` in other files.
RecordKey = Tuple[TypedKey, Any]


@dataclass
class Context:
    """The side store of one loaded HIF file (DESIGN §5)."""

    network_type: str | None
    metadata: dict[str, Any] | None
    profile: bool
    records: dict[RecordKey, dict[str, Any]]
    order: list[RecordKey]
    node_weight: dict[TypedKey, int | float]
    edge_weight: dict[TypedKey, int | float]
    isolated_nodes: frozenset[TypedKey]
    empty_edges: frozenset[TypedKey]
    node_ids: list[Any]
    edge_ids: list[Any]
    node_attrs: frozenset[TypedKey]
    edge_attrs: frozenset[TypedKey]
    top_keys: tuple[str, ...]
    labels: list[dict[str, Any]] = field(default_factory=list)

    @property
    def directed(self) -> bool:
        """True for a file whose ``network-type`` is ``directed``."""
        return self.network_type == "directed"

    def slots(self) -> dict[RecordKey, int]:
        """The source position of each loaded record."""
        return {rk: i for i, rk in enumerate(self.order)}

    def pair_records(self) -> dict[tuple[TypedKey, TypedKey], list[RecordKey]]:
        """The loaded records of each (edge, node) pair, in source order."""
        out: dict[tuple[TypedKey, TypedKey], list[RecordKey]] = {}
        for rk in self.order:
            r = self.records[rk]
            out.setdefault((tkey(r["edge"]), tkey(r["node"])), []).append(rk)
        return out

    def derived(self) -> Context:
        """A copy for a derived bundle: the loaded state is shared, the labels are copied."""
        return dataclasses.replace(self, labels=[copy.deepcopy(r) for r in self.labels])


def record_key(record: Mapping[str, Any], profile: bool, ordinal: int) -> RecordKey:
    """The key of a loaded record: by ``khg-bid`` in profile files, by its ordinal within its edge otherwise."""
    if profile:
        return (tkey(record["edge"]), record["attrs"]["khg-bid"])
    return (tkey(record["edge"]), ("#", ordinal))


def _declared(doc: Mapping[str, Any], key: str, idf: str) -> tuple[list[Any], dict[TypedKey, Any], set[TypedKey]]:
    ids: list[Any] = []
    weights: dict[TypedKey, Any] = {}
    with_attrs: set[TypedKey] = set()
    for item in doc.get(key) or []:
        ids.append(item[idf])
        if "weight" in item:
            weights[tkey(item[idf])] = item["weight"]
        if "attrs" in item:
            with_attrs.add(tkey(item[idf]))
    return ids, weights, with_attrs


def build_context(doc: Mapping[str, Any], profile: bool) -> Context:
    """The context of a HIF document that passed the loader checks (``_input.check_document``)."""
    records: dict[RecordKey, dict[str, Any]] = {}
    order: list[RecordKey] = []
    ordinals: dict[TypedKey, int] = {}
    for r in doc["incidences"]:
        e = tkey(r["edge"])
        ordinals[e] = ordinals.get(e, 0) + 1
        rk = record_key(r, profile, ordinals[e])
        records[rk] = copy.deepcopy(dict(r))
        order.append(rk)
    member_nodes = {tkey(r["node"]) for r in doc["incidences"]}
    member_edges = {tkey(r["edge"]) for r in doc["incidences"]}
    node_ids, node_weight, node_attrs = _declared(doc, "nodes", "node")
    edge_ids, edge_weight, edge_attrs = _declared(doc, "edges", "edge")
    metadata = doc.get("metadata")
    return Context(
        network_type=doc.get("network-type"),
        metadata=copy.deepcopy(dict(metadata)) if metadata is not None else None,
        profile=profile,
        records=records,
        order=order,
        node_weight=node_weight,
        edge_weight=edge_weight,
        isolated_nodes=frozenset(tkey(n) for n in node_ids) - member_nodes,
        empty_edges=frozenset(tkey(e) for e in edge_ids) - member_edges,
        node_ids=node_ids,
        edge_ids=edge_ids,
        node_attrs=frozenset(node_attrs),
        edge_attrs=frozenset(edge_attrs),
        top_keys=tuple(doc),
    )
