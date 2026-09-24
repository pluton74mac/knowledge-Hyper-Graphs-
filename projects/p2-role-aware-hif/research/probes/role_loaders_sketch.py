#!/usr/bin/env python3
"""Sketch of role-preserving HIF adapters for XGI 0.10.2 and HyperNetX 2.4.3 (P2 research, 2026-09-23).

This is research code that tests a design; it is not the P2 package. The approach:

* Never use the libraries' own HIF readers or writers. XGI's reader drops incidence attrs and weights
  and crashes on some valid files; HyperNetX's needs the network on every call, returns None instead
  of raising, drops metadata, and cannot read its own directed output back (see 03-library-probes.md).
* Load: build the library object with public construction APIs (XGI: add_node_to_edge / add_node /
  add_edge / set_*_attributes; HyperNetX: the Hypergraph DataFrame constructor), and return it together
  with a context object `Ctx` that holds what the library cannot: the full incidence records (XGI),
  record-level weights, network-type and metadata.
* HyperNetX has a native place for per-incidence data (cell properties), so roles are *also* written
  there. The one thing it cannot hold natively is a second record for the same (edge, node) pair; the
  second and later records ride in a reserved attrs key of the first record's cell.
* Export reconciles: the library object decides which nodes, edges and memberships exist now (so native
  edits are honoured), and the context supplies the full records for memberships that still exist.
  Records whose membership is gone are reported as `stale`; memberships with no record are exported
  bare and reported as `unlabelled`. Nothing is silently re-attached to a different pair.
"""
from __future__ import annotations

import copy
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

ABSENT = object()
EXTRA = "khg:extra-incidences"  # reserved key in an HNX cell's attrs: records 2..k of one (edge, node) pair


class HIFError(ValueError):
    pass


def _k(x):
    """Typed key: the integer 1 and the string "1" are different HIF ids."""
    return (type(x).__name__, x)


@dataclass
class Ctx:
    network_type: Any = ABSENT
    metadata: Any = ABSENT
    incidences: list = field(default_factory=list)  # full source records, in source order
    node_weight: dict = field(default_factory=dict)  # typed id -> weight (only when present in the source)
    edge_weight: dict = field(default_factory=dict)
    node_order: list = field(default_factory=list)  # declared node ids, source order, first occurrence
    edge_order: list = field(default_factory=list)
    report: dict = field(default_factory=dict)


def _check(doc):
    if not isinstance(doc, dict) or not isinstance(doc.get("incidences"), list):
        raise HIFError("not a HIF document: 'incidences' array missing")
    nt = doc.get("network-type", ABSENT)
    if nt is not ABSENT and nt not in ("undirected", "directed", "asc"):
        raise HIFError(f"network-type {nt!r} not in the HIF enum")
    if nt == "directed":
        bad = [r for r in doc["incidences"] if r.get("direction") not in ("head", "tail")]
        if bad:
            raise HIFError(f"directed network: {len(bad)} incidence(s) without direction head/tail, "
                           f"first: {bad[0]!r}")
    return nt


def _ctx(doc, nt):
    ctx = Ctx(network_type=nt, metadata=copy.deepcopy(doc["metadata"]) if "metadata" in doc else ABSENT,
              incidences=[copy.deepcopy(r) for r in doc["incidences"]])
    for kind, order, weights in (("nodes", ctx.node_order, ctx.node_weight), ("edges", ctx.edge_order, ctx.edge_weight)):
        seen = set()
        for r in doc.get(kind, []) or []:
            i = r["node" if kind == "nodes" else "edge"]
            if _k(i) not in seen:
                seen.add(_k(i))
                order.append(i)
            if "weight" in r:
                weights[_k(i)] = r["weight"]
    return ctx


def _merged_attrs(doc, kind):
    """Later declarations of the same id update earlier ones (XGI's rule; HNX keeps the first)."""
    out = OrderedDict()
    idf = "node" if kind == "nodes" else "edge"
    for r in doc.get(kind, []) or []:
        out.setdefault(_k(r[idf]), (r[idf], {}))[1].update(copy.deepcopy(r.get("attrs") or {}))
    return out


def _object_records(idf, ids_now, attrs_of, ctx_order, ctx_weight, isolated):
    """Node or edge records for export: declared ones in source order, then any with attrs/weight or isolated."""
    recs, seen = [], set()
    now = {_k(i): i for i in ids_now}
    declared_keys = {_k(j) for j in ctx_order}
    for i in list(ctx_order) + [i for i in ids_now if _k(i) not in declared_keys]:
        if _k(i) not in now or _k(i) in seen:
            continue
        seen.add(_k(i))
        a, w = attrs_of(i), ctx_weight.get(_k(i), ABSENT)
        if _k(i) in declared_keys or a or w is not ABSENT or isolated(i):
            r = {idf: i}
            if w is not ABSENT:
                r["weight"] = w
            if a:
                r["attrs"] = a
            recs.append(r)
    return recs


def _head(doc_out, ctx, directed_class=False):
    nt = ctx.network_type
    if directed_class and nt != "directed":
        nt = "directed"
    if nt is not ABSENT:
        doc_out["network-type"] = nt
    return nt


# --------------------------------------------------------------------------------------------
# XGI
# --------------------------------------------------------------------------------------------

def to_xgi(doc):
    import xgi
    nt = _check(doc)
    directed = nt == "directed"
    H = xgi.DiHypergraph() if directed else xgi.Hypergraph()  # 'asc' kept as a plain Hypergraph: no subfaces
    for k, v in (doc.get("metadata") or {}).items():
        H[k] = copy.deepcopy(v)
    for r in doc["incidences"]:
        if directed:
            H.add_node_to_edge(r["edge"], r["node"], "in" if r["direction"] == "tail" else "out")
        else:
            H.add_node_to_edge(r["edge"], r["node"])
    for i, a in _merged_attrs(doc, "nodes").values():
        if i not in H.nodes:
            H.add_node(i)  # never **attrs: an attrs key named 'node' would collide (hif_dict.py:171)
        H.set_node_attributes({i: a})
    for i, a in _merged_attrs(doc, "edges").values():
        if i not in H.edges:
            H.add_edge((set(), set()) if directed else set(), idx=i)  # never **attrs (hif_dict.py:184)
        H.set_edge_attributes({i: a})
    return H, _ctx(doc, nt)


def from_xgi(H, ctx):
    import xgi
    directed = isinstance(H, xgi.DiHypergraph)
    out = OrderedDict()
    _head(out, ctx, directed)
    if dict(H._net_attr) or ctx.metadata is not ABSENT:
        out["metadata"] = copy.deepcopy(dict(H._net_attr))

    def node_attrs(n):
        return copy.deepcopy(dict(H.nodes[n]))

    def edge_attrs(e):
        return copy.deepcopy(dict(H.edges[e]))
    iso = set(map(_k, H.nodes.isolates()))
    empty = set(map(_k, H.edges.empty()))
    nodes = _object_records("node", list(H.nodes), node_attrs, ctx.node_order, ctx.node_weight, lambda n: _k(n) in iso)
    edges = _object_records("edge", list(H.edges), edge_attrs, ctx.edge_order, ctx.edge_weight, lambda e: _k(e) in empty)
    if nodes:
        out["nodes"] = nodes
    if edges:
        out["edges"] = edges

    live = OrderedDict()  # (edge, node, direction-or-None) -> raw ids
    for e in H.edges:
        if directed:
            tail, head = H.edges.dimembers(e)
            for n in tail:
                live[(_k(e), _k(n), "tail")] = (e, n, "tail")
            for n in head:
                live[(_k(e), _k(n), "head")] = (e, n, "head")
        else:
            for n in H.edges.members(e):
                live[(_k(e), _k(n), None)] = (e, n, None)
    used, inc, stale = set(), [], []
    for r in ctx.incidences:
        key = (_k(r["edge"]), _k(r["node"]), r.get("direction") if directed else None)
        if key in live:
            inc.append(copy.deepcopy(r))
            used.add(key)
        else:
            stale.append(r)
    unlabelled = []
    for key, (e, n, d) in live.items():
        if key not in used:
            r = {"edge": e, "node": n}
            if d is not None:
                r["direction"] = d
            inc.append(r)
            unlabelled.append(r)
    out["incidences"] = inc
    ctx.report = {"stale_records_dropped": stale, "unlabelled_memberships_exported_bare": unlabelled}
    return dict(out)


# --------------------------------------------------------------------------------------------
# HyperNetX
# --------------------------------------------------------------------------------------------

def to_hnx(doc):
    import pandas as pd
    import hypernetx as hnx
    nt = _check(doc)
    groups = OrderedDict()
    for r in doc["incidences"]:
        groups.setdefault((_k(r["edge"]), _k(r["node"])), []).append(r)
    rows = []
    has_dir = any("direction" in r for r in doc["incidences"])
    for recs in groups.values():
        first = recs[0]
        attrs = copy.deepcopy(first.get("attrs") or {})
        if len(recs) > 1:
            attrs[EXTRA] = [copy.deepcopy(r) for r in recs[1:]]
        row = {"edge": first["edge"], "node": first["node"], "weight": first.get("weight", 1), "attrs": attrs}
        if has_dir:
            row["direction"] = first.get("direction")
        rows.append(row)
    cols = ["edge", "node", "weight"] + (["direction"] if has_dir else []) + ["attrs"]
    inc = pd.DataFrame(rows, columns=cols)

    def props(kind):
        m = _merged_attrs(doc, kind)
        if not m:
            return None
        idf = "node" if kind == "nodes" else "edge"
        w = {}
        for r in doc.get(kind, []) or []:
            if "weight" in r:
                w[_k(r[idf])] = r["weight"]
        return pd.DataFrame([{idf: i, "weight": w.get(k, 1), "attrs": a} for k, (i, a) in m.items()],
                            columns=[idf, "weight", "attrs"])
    H = hnx.Hypergraph(inc, edge_col="edge", node_col="node", cell_weight_col="weight",
                       misc_cell_properties_col="attrs", node_properties=props("nodes"),
                       edge_properties=props("edges"), misc_properties_col="attrs")
    return H, _ctx(doc, nt)


def _clean(v):
    try:
        import numpy as np
        if isinstance(v, np.generic):
            return v.item()
    except ImportError:
        pass
    return v


def _missing(v):
    return v is None or (isinstance(v, float) and v != v)


def from_hnx(H, ctx):
    out = OrderedDict()
    _head(out, ctx)
    if ctx.metadata is not ABSENT:
        out["metadata"] = copy.deepcopy(ctx.metadata)
    # which (edge, node) pairs carried a weight in the source (first record of each pair)
    first_weight = {}
    for r in ctx.incidences:
        first_weight.setdefault((_k(r["edge"]), _k(r["node"])), "weight" in r)

    for kind, view, ctx_order, ctx_weight in (("nodes", H.nodes, ctx.node_order, ctx.node_weight),
                                              ("edges", H.edges, ctx.edge_order, ctx.edge_weight)):
        store = view.property_store.properties  # includes isolated nodes / empty edges, unlike to_dataframe
        idf = kind[:-1]
        recs, seen = [], set()
        ids = [_clean(i) for i in store.index]
        idkeys = {_k(i) for i in ids}
        declared = {_k(j) for j in ctx_order}
        order = [i for i in ctx_order if _k(i) in idkeys] + [i for i in ids if _k(i) not in declared]
        for i in order:
            if _k(i) in seen:
                continue
            seen.add(_k(i))
            row = store.loc[i]
            r = {idf: _clean(i)}
            w = ctx_weight.get(_k(i), ABSENT)
            if w is not ABSENT:
                r["weight"] = _clean(row["weight"])
            elif not _missing(row["weight"]) and row["weight"] != view.default_weight:
                r["weight"] = _clean(row["weight"])
            a = copy.deepcopy(row["misc_properties"]) if isinstance(row["misc_properties"], dict) else {}
            for c in store.columns:
                if c not in ("weight", "misc_properties") and not _missing(row[c]):
                    a[c] = _clean(row[c])
            if a:
                r["attrs"] = a
            recs.append(r)
        if recs:
            out[kind] = recs

    df = H.incidences.to_dataframe
    inc = []
    for (e, n), row in df.iterrows():
        e, n = _clean(e), _clean(n)
        a = copy.deepcopy(row["misc_properties"]) if isinstance(row["misc_properties"], dict) else {}
        extra = a.pop(EXTRA, [])
        r = {"edge": e, "node": n}
        if "direction" in df.columns and not _missing(row["direction"]):
            r["direction"] = row["direction"]
        known = first_weight.get((_k(e), _k(n)))
        if known or (known is None and row["weight"] != H.incidences.default_weight) or \
                (known is False and row["weight"] != 1):
            r["weight"] = _clean(row["weight"])
        for c in df.columns:
            if c not in ("weight", "direction", "misc_properties") and not _missing(row[c]):
                a[c] = _clean(row[c])
        if a:
            r["attrs"] = a
        inc.append(r)
        for x in extra:
            x = copy.deepcopy(x)
            x["edge"], x["node"] = e, n  # follows renames of the cell
            inc.append(x)
    out["incidences"] = inc
    return dict(out)
