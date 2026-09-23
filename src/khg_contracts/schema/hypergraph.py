"""The schema as a hypergraph (P6; DESIGN §3): ``schema_hypergraph`` and the GYO test ``is_alpha_acyclic``."""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .builtins import SLOTS
from .model import Schema

__all__ = ["schema_hypergraph", "is_alpha_acyclic"]


def schema_hypergraph(schema: Schema | Mapping[str, Any], *,
                      slots: Sequence[str] = ("core", "qualifier")) -> dict[str, Any]:
    """``{"vertices": [roles], "hyperedges": {relation: [roles]}}``: one hyperedge per relation of the schema, over
    the roles of its usages in ``slots``; role lists are sorted, relations keep schema order.

    A role is one vertex whatever its slot (F4). Lifecycle relations never appear; a relation with no usage in
    ``slots`` is left out. Time and meta usages appear only when asked for (``khg:end_cause`` is the built-in meta
    usage of every interval relation).
    """
    bad = [s for s in slots if s not in SLOTS]
    if bad or isinstance(slots, str):
        raise ValueError(f"slots must be taken from {SLOTS}, got {slots!r}")
    s = schema if isinstance(schema, Schema) else Schema(schema)
    wanted = set(slots)
    edges: dict[str, list[str]] = {}
    for rel in s.relation_ids():
        roles = sorted({u["role"] for u in s.usages(rel) if u["slot"] in wanted})
        if roles:
            edges[rel] = roles
    return {"vertices": sorted({v for e in edges.values() for v in e}), "hyperedges": edges}


def _edges(hg: Any) -> list[set[str]]:
    if isinstance(hg, Mapping):
        body = hg["hyperedges"] if "hyperedges" in hg and isinstance(hg["hyperedges"], (Mapping, list)) else hg
        values: Iterable[Any] = body.values() if isinstance(body, Mapping) else body
    else:
        values = hg
    return [set(e) for e in values]


def is_alpha_acyclic(hg: Any) -> tuple[bool, list[list[str]]]:
    """The GYO reduction: alpha-acyclic iff repeatedly removing vertices that lie in one hyperedge only, and
    hyperedges contained in another, empties the hypergraph. Returns ``(acyclic, residue)``, the residue being the
    hyperedges left, each sorted, in input order.

    ``hg`` is the result of ``schema_hypergraph``, a mapping of hyperedges, or an iterable of role collections.
    """
    es = [e for e in _edges(hg) if e]
    changed = True
    while changed:
        changed = False
        count: dict[str, int] = {}
        for e in es:
            for v in e:
                count[v] = count.get(v, 0) + 1
        for e in es:
            lone = {v for v in e if count[v] == 1}
            if lone:
                e -= lone
                changed = True
        keep: list[set[str]] = []
        for i, e in enumerate(es):
            if not e:
                changed = True
                continue
            if any(j != i and e <= f and (e != f or j < i) for j, f in enumerate(es)):
                changed = True
                continue
            keep.append(e)
        es = keep
    return (not es), [sorted(e) for e in es]
