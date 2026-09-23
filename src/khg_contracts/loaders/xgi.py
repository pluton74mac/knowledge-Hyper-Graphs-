"""The XGI loader (DESIGN §5): ``load_xgi`` and ``export_xgi``.

Construction uses public constructors only [R03 §7]: ``add_node_to_edge``, ``add_node``, ``add_edge`` and
``set_*_attributes``; ``xgi.read_hif`` and ``xgi.write_hif`` are never called (F1). A ``directed`` file becomes a
``DiHypergraph`` with tail as ``"in"`` and head as ``"out"``; any other file a ``Hypergraph``. Nothing is written into
XGI network attributes: the context holds the metadata (critique GL-15).

XGI cannot hold incidence attrs or weights, so the context's records are the source of truth: a record is exported
when its membership (edge, node and, in a ``DiHypergraph``, direction) still exists. xgi is imported on first use.
"""
from __future__ import annotations

import copy
import os
from types import ModuleType
from typing import Any, Literal, Mapping, Optional, Tuple, Union

from ..errors import LoaderError, make_finding
from ._common import TypedKey, tkey
from ._input import check_document, is_profile, read_document
from .bundle import Bundle
from .context import build_context
from .reconcile import Item, Kept, finish, membership, record_sort_key
from .report import ExportReport, new_report

__all__ = ["attach", "export_xgi", "load_xgi", "records"]

#: A membership as XGI holds it: (typed edge, typed node, "tail" or "head" in a DiHypergraph, else None).
Membership = Tuple[TypedKey, TypedKey, Optional[str]]


def _xgi() -> ModuleType:
    try:
        import xgi
    except ImportError as e:  # pragma: no cover - exercised only without the extra
        raise ImportError("the XGI loader needs xgi: pip install 'khg-contracts[xgi]'") from e
    return xgi


def load_xgi(hif: Union[Mapping[str, Any], str, os.PathLike],
             *, validate: Literal["profile", "convention", "none"] = "profile") -> Bundle:
    """Load a HIF file into an ``xgi.Hypergraph``, or an ``xgi.DiHypergraph`` when its ``network-type`` is
    ``directed``. ``hif`` is a parsed document or a path (a ``str`` is always a path). Raises ``LoaderError`` (also a
    ``ValidationError``) when the input is refused: the codes of the ``validate`` mode, or D001, P007 or P010."""
    doc = read_document(hif)
    check_document(doc, validate)
    ctx = build_context(doc, is_profile(doc, validate))
    xgi = _xgi()
    directed = ctx.directed
    graph = xgi.DiHypergraph() if directed else xgi.Hypergraph()
    for r in doc["incidences"]:
        if directed:
            graph.add_node_to_edge(r["edge"], r["node"], "in" if r["direction"] == "tail" else "out")
        else:
            graph.add_node_to_edge(r["edge"], r["node"])
    for n in doc.get("nodes") or []:
        if n["node"] not in graph.nodes:
            graph.add_node(n["node"])
        if n.get("attrs"):
            graph.set_node_attributes({n["node"]: copy.deepcopy(n["attrs"])})
    for e in doc.get("edges") or []:
        if e["edge"] not in graph.edges:
            graph.add_edge((set(), set()) if directed else set(), idx=e["edge"])
        if e.get("attrs"):
            graph.set_edge_attributes({e["edge"]: copy.deepcopy(e["attrs"])})
    return Bundle(graph, ctx, "xgi")


# ------------------------------------------------------------------------------------------------ memberships


def _is_directed(graph: Any) -> bool:
    return isinstance(graph, _xgi().DiHypergraph)


def _memberships(graph: Any, directed: bool) -> dict[Membership, dict[str, Any]]:
    """Every membership of the graph (only looked up and sorted, so set order never shows)."""
    out: dict[Membership, dict[str, Any]] = {}
    for e in graph.edges:
        if directed:
            tail, head = graph.edges.dimembers(e)
            for n in tail:
                out[(tkey(e), tkey(n), "tail")] = {"edge": e, "node": n, "direction": "tail"}
            for n in head:
                out[(tkey(e), tkey(n), "head")] = {"edge": e, "node": n, "direction": "head"}
        else:
            for n in graph.edges.members(e):
                out[(tkey(e), tkey(n), None)] = {"edge": e, "node": n}
    return out


def _key(record: Mapping[str, Any], directed: bool) -> Membership:
    return (tkey(record["edge"]), tkey(record["node"]), record.get("direction") if directed else None)


def _live(graph: Any, record: Mapping[str, Any], directed: bool) -> bool:
    edge, node = record["edge"], record["node"]
    if edge not in graph.edges:
        return False
    if not directed:
        return any(tkey(n) == tkey(node) for n in graph.edges.members(edge))
    tail, head = graph.edges.dimembers(edge)
    side = tail if record.get("direction") == "tail" else head if record.get("direction") == "head" else ()
    return any(tkey(n) == tkey(node) for n in side)


def _counts(record: Mapping[str, Any], profile: bool) -> bool:
    """A record labels its membership: a role, and in a profile file a khg-bid."""
    attrs = record.get("attrs") or {}
    return bool(attrs.get("role")) and (not profile or "khg-bid" in attrs)


def _check_bundle(bundle: Bundle) -> None:
    if bundle.lib != "xgi":
        raise TypeError(f"export_xgi needs an XGI bundle, not a {bundle.lib} one")


# ------------------------------------------------------------------------------------------------ export


def export_xgi(bundle: Bundle, *, strict: bool = True) -> dict[str, Any]:
    """The HIF document of an XGI bundle, reconciled with its context (DESIGN §5). Sets ``bundle.report``.
    ``strict=True`` raises ``LoaderError`` (P005) on an unlabelled membership, a partial fact or a non-injective
    move; ``strict=False`` drops and reports them."""
    _check_bundle(bundle)
    graph, ctx = bundle.graph, bundle.context
    directed = _is_directed(graph)
    live = _memberships(graph, directed)
    edges_now = {tkey(e) for e in graph.edges}
    report = new_report()
    kept: list[Kept] = []
    used: set[Membership] = set()
    for slot, rk in enumerate(ctx.order):
        _place(ctx.records[rk], slot, directed, live, used, edges_now, kept, report)
    for r in ctx.labels:
        if _counts(r, ctx.profile):
            _place(r, None, directed, live, used, edges_now, kept, report)
    report["unlabelled"] = sorted((copy.deepcopy(m) for k, m in live.items() if k not in used), key=record_sort_key)
    nodes: list[Item] = [(n, copy.deepcopy(dict(graph.nodes[n])), None) for n in graph.nodes]
    edges: list[Item] = [(e, copy.deepcopy(dict(graph.edges[e])), None) for e in graph.edges]
    return finish(bundle, nodes, edges, kept, report, strict)


def _place(record: dict[str, Any], slot: int | None, directed: bool, live: dict[Membership, dict[str, Any]],
           used: set[Membership], edges_now: set[TypedKey], kept: list[Kept], report: ExportReport) -> None:
    """Keep a record whose membership is live; else report it as stale (its edge survives) or dropped."""
    key = _key(record, directed)
    if key in live:
        kept.append((slot, copy.deepcopy(record)))
        used.add(key)
    elif tkey(record["edge"]) in edges_now:
        report["stale"].append(copy.deepcopy(record))  # a partial fact: its edge survives
    else:
        report["dropped_records"].append(copy.deepcopy(record))  # its edge was removed whole


# ------------------------------------------------------------------------------------------------ Bundle methods


def records(bundle: Bundle, edge: Any, node: Any = None) -> list[dict[str, Any]]:
    """The records of ``edge`` (and ``node``) whose membership is live: loaded records in source order, then
    labels."""
    graph, ctx = bundle.graph, bundle.context
    directed = _is_directed(graph)
    found = [ctx.records[rk] for rk in ctx.order] + [r for r in ctx.labels if _counts(r, ctx.profile)]
    return [r for r in found
            if tkey(r["edge"]) == tkey(edge) and (node is None or tkey(r["node"]) == tkey(node))
            and _live(graph, r, directed)]


def attach(bundle: Bundle, record: dict[str, Any]) -> None:
    """Keep ``record`` in the context as the record of its membership, which must exist."""
    graph = bundle.graph
    directed = _is_directed(graph)
    if directed and record.get("direction") is None:
        raise LoaderError("KHG-P010: a membership of a DiHypergraph needs its direction (tail or head)",
                          codes=["KHG-P010"], info={"findings": [make_finding(
                              "KHG-P010", "/direction", "a directed membership without direction")]})
    if not _live(graph, record, directed):
        what = membership(record)
        raise LoaderError(f"KHG-P005: no membership {what} to label", codes=["KHG-P005"],
                          info={"findings": [make_finding("KHG-P005", "", f"no membership {what} to label")]})
    bundle.context.labels.append(copy.deepcopy(record))
