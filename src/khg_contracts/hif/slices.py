"""Closed slices of a C1 container (DESIGN §4.6; critique GL-17, CONS-14).

A slice keeps three things:

- the hyperedges of the listed relations;
- the lifecycle record named by the ``status_ref`` of every kept record, applied until nothing is added;
- the entities that kept records reference.

Its header says ``complete: false``. A fact reference to a fact outside the slice stays a reference; ``to_hif``
writes it as an external node (``khg-external: true``). Embedded ``relation-schema`` records are not kept, since
HIF does not carry them (``to_hif(schema_document=True)`` inlines the schema instead).
"""
from __future__ import annotations

import copy
from typing import Any, Iterable, Mapping

__all__ = ["select_slice"]


def _entity_ids(record: Mapping[str, Any]) -> list[str]:
    out = []
    bindings = record.get("bindings")
    for b in bindings if isinstance(bindings, list) else []:
        value = b.get("value") if isinstance(b, Mapping) else None
        if isinstance(value, Mapping) and len(value) == 1 and isinstance(value.get("entity"), str):
            out.append(value["entity"])
    return out


def select_slice(container: Mapping[str, Any], relations: Iterable[str]) -> dict[str, Any]:
    """The closed slice of ``container`` for ``relations``: a new container, with the kept records in their order
    and ``complete: false`` in the header."""
    wanted = set(relations)
    records = [r for r in container["records"] if isinstance(r, Mapping)]
    latest: dict[str, Mapping[str, Any]] = {}  # hyperedges by id; the last version in a history container
    keep: set[str] = set()
    for r in records:
        rid, relation = r.get("id"), r.get("relation")
        if r.get("kind") == "hyperedge" and isinstance(rid, str):
            latest[rid] = r
            if isinstance(relation, str) and relation in wanted:
                keep.add(rid)
    todo = sorted(keep)
    while todo:  # closed over status_ref: a kept lifecycle record may itself be disputed or retracted
        ref = latest[todo.pop()].get("status_ref")
        if isinstance(ref, str) and ref in latest and ref not in keep:
            keep.add(ref)
            todo.append(ref)

    def kept_edge(r: Mapping[str, Any]) -> bool:
        return r.get("kind") == "hyperedge" and isinstance(r.get("id"), str) and r["id"] in keep

    entities = {e for r in records if kept_edge(r) for e in _entity_ids(r)}

    def kept(r: Mapping[str, Any]) -> bool:
        return kept_edge(r) or (r.get("kind") == "entity" and isinstance(r.get("id"), str) and r["id"] in entities)

    header = copy.deepcopy(dict(container["header"]))
    header["complete"] = False
    return {"header": header, "records": [copy.deepcopy(dict(r)) for r in records if kept(r)]}
