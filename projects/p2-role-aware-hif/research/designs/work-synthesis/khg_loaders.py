"""Prototype of loaders/ (DESIGN §5), revised after the critique (GL-03..GL-15, LOADER-STRICT). Research code.

Library objects are built with public constructors only; the libraries' own HIF functions are never called (F1).
- XGI: the context is the source of truth for incidence records (XGI cannot hold incidence attrs or weights);
  records are keyed by (edge, khg-bid), or by (edge, ordinal) in files without the profile.
- HyperNetX: the cell is the source of truth. A pair's first record is written as the cell's properties (so native
  readers see role, khg-bid, role-position), its weight in the cell weight column and its direction in the direction
  column; records 2..k of the same (edge, node) pair ride under the reserved cell key khg-extra-incidences.
- The context holds what neither library holds: metadata (authoritative), network-type, the loaded weights with their
  JSON number type (nodes, edges, incidences), which nodes were isolated and which edges were empty in the loaded file.
Export reconciles: the library object decides which memberships exist. Under strict=True it raises on an unlabelled
membership, on a record whose membership is gone while its edge still exists (a partial fact) and on a record that
moved to another node unless the node map is injective (a rename). Records of edges removed whole are dropped and
reported, never raised. With strict=False nothing raises: unlabelled memberships and partial records are dropped and
reported (never exported bare)."""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import khg_synth as K

EXTRA = "khg-extra-incidences"


class LoaderError(ValueError):
    def __init__(self, code, msg, report=None):
        super().__init__(f"{code}: {msg}")
        self.code = code
        self.report = report or {}


def _k(x):
    """Typed key: the integer 1 and the string "1" are different HIF ids."""
    return (type(x).__name__, x)


@dataclass
class Context:
    network_type: object
    metadata: object
    profile: bool
    records: dict                      # (typed edge, rkey) -> full incidence record, as loaded
    order: list                        # record keys in source order
    node_weight: dict                  # typed node id -> weight as loaded (int stays int)
    edge_weight: dict
    node_isolated: set                 # typed ids isolated in the loaded file
    edge_empty: set
    node_decl: list                    # declared node ids, source order
    edge_decl: list
    labels: list = field(default_factory=list)   # records added with Bundle.label (XGI)


class Bundle:
    def __init__(self, graph, context, lib):
        self.graph, self.context, self.lib = graph, context, lib
        self.report = None

    # -------------------------------------------------------------- reads
    def records(self, edge, node=None):
        """The incidence records of an edge (optionally of one (edge, node) pair) in record order."""
        if self.lib == "xgi":
            recs = [self.context.records[k] for k in self.context.order if k[0] == _k(edge)] + \
                   [r for r in self.context.labels if _k(r["edge"]) == _k(edge)]
        else:
            recs = [r for r in _hnx_cells(self.graph) if _k(r["edge"]) == _k(edge)]
        return tuple(copy.deepcopy(r) for r in recs if node is None or _k(r["node"]) == _k(node))

    def roles(self, edge, node):
        return [r["attrs"]["role"] for r in self.records(edge, node) if "role" in (r.get("attrs") or {})]

    # -------------------------------------------------------------- native edits the export cannot infer
    def derive(self, graph):
        """A bundle for a copy or restriction of this graph (copy, clone, restrict_to_*, subhypergraph)."""
        return Bundle(graph, self.context, self.lib)

    def label(self, edge, node, *, role, bid=None, direction=None, position=None, weight=None, extensions=None):
        """Give a new membership its record (required before a strict export)."""
        attrs = {"role": role}
        if bid is not None:
            attrs["khg-bid"] = bid
        if position is not None:
            attrs["role-position"] = position
        if extensions:
            attrs["khg-extensions"] = copy.deepcopy(extensions)
        rec = {"edge": edge, "node": node}
        if direction is not None:
            rec["direction"] = direction
        if weight is not None:
            rec["weight"] = weight
        rec["attrs"] = attrs
        if self.lib == "xgi":
            self.context.labels.append(rec)
        else:
            H = self.graph
            props = _cell_props(H, edge, node)
            if props is None:
                raise LoaderError("KHG-P005", f"no HyperNetX cell ({edge}, {node}) to label")
            store = H.incidences.property_store   # PropertyStore.set_property: public in HyperNetX 2.4.3
            if "role" not in props:
                for k2, v in attrs.items():
                    store.set_property((edge, node), k2, v)
            else:
                extra = list(props.get(EXTRA, []))
                extra.append(rec)
                store.set_property((edge, node), EXTRA, extra)


# ---------------------------------------------------------------------------------------------- loading
def _read(hif):
    if isinstance(hif, (str, os.PathLike)):
        return K.strict_loads(Path(hif).read_text(encoding="utf-8"))
    return copy.deepcopy(dict(hif))


def _check(doc, validate):
    """validate='profile' runs J, V, H, R and P (not S or D: those need the relation schema and run in from_hif);
    'convention' runs H and R; 'none' runs nothing. asc files and directed files with a direction-less incidence
    are refused whatever the mode (the libraries cannot represent them)."""
    if validate in ("profile", "convention"):
        import khg_validate_proto as VP
        if _VALIDATOR is None:
            raise LoaderError("KHG-V001", "call set_schema_dir() before validating")
        steps = ([_VALIDATOR._v_hif] if validate == "profile" else []) + [_VALIDATOR._h, _VALIDATOR._r] + \
            ([_VALIDATOR._p] if validate == "profile" else [])
        for st in steps:
            fs = VP.errors(st(doc))
            if fs:
                raise LoaderError(fs[0]["code"], fs[0]["message"])
    for kind, idf in (("nodes", "node"), ("edges", "edge")):
        ids = [_k(x[idf]) for x in doc.get(kind, []) or []]
        if len(ids) != len(set(ids)):
            raise LoaderError("KHG-D001", f"a {idf} is declared twice (R03 c19)")
    nt = doc.get("network-type")
    if nt == "asc":
        raise LoaderError("KHG-P007", "network-type asc is refused")
    if nt == "directed" and any(i.get("direction") not in ("head", "tail") for i in doc["incidences"]):
        raise LoaderError("KHG-P010", "a directed file with an incidence lacking direction is refused")
    return nt


_VALIDATOR = None


def set_schema_dir(path):
    global _VALIDATOR
    import khg_validate_proto as VP
    _VALIDATOR = VP.Validator(path, engine="jsonschema")


def _context(doc, nt, profile):
    records, order, seen_ord = {}, [], {}
    for r in doc["incidences"]:
        e = _k(r["edge"])
        if profile:
            rk = (e, r["attrs"]["khg-bid"])
        else:
            seen_ord[e] = seen_ord.get(e, 0) + 1
            rk = (e, ("#", seen_ord[e]))
        records[rk] = copy.deepcopy(r)
        order.append(rk)
    member_nodes = {_k(r["node"]) for r in doc["incidences"]}
    member_edges = {_k(r["edge"]) for r in doc["incidences"]}
    nw, ew, nd, ed = {}, {}, [], []
    for n in doc.get("nodes", []) or []:
        if "weight" in n:
            nw[_k(n["node"])] = n["weight"]
        nd.append(n["node"])
    for e in doc.get("edges", []) or []:
        if "weight" in e:
            ew[_k(e["edge"])] = e["weight"]
        ed.append(e["edge"])
    return Context(network_type=nt, metadata=copy.deepcopy(doc.get("metadata")), profile=profile, records=records,
                   order=order, node_weight=nw, edge_weight=ew,
                   node_isolated={_k(n) for n in nd} - member_nodes, edge_empty={_k(e) for e in ed} - member_edges,
                   node_decl=nd, edge_decl=ed)


def _merged(doc, kind):
    """attrs of repeated declarations are refused by the profile (D001); foreign files: later ones win (XGI rule)."""
    out, idf = {}, ("node" if kind == "nodes" else "edge")
    for r in doc.get(kind, []) or []:
        out.setdefault(_k(r[idf]), (r[idf], {}))[1].update(copy.deepcopy(r.get("attrs") or {}))
    return out


def load_xgi(hif, *, validate="profile"):
    import xgi
    doc = _read(hif)
    nt = _check(doc, validate)
    profile = validate == "profile" or "khg-profile" in (doc.get("metadata") or {})
    directed = nt == "directed"
    H = xgi.DiHypergraph() if directed else xgi.Hypergraph()
    # GL-15: no metadata is written into XGI network attributes; the context is authoritative
    for r in doc["incidences"]:
        if directed:
            H.add_node_to_edge(r["edge"], r["node"], "in" if r["direction"] == "tail" else "out")
        else:
            H.add_node_to_edge(r["edge"], r["node"])
    for i, a in _merged(doc, "nodes").values():
        if i not in H.nodes:
            H.add_node(i)
        H.set_node_attributes({i: a})
    for i, a in _merged(doc, "edges").values():
        if i not in H.edges:
            H.add_edge((set(), set()) if directed else set(), idx=i)
        H.set_edge_attributes({i: a})
    return Bundle(H, _context(doc, nt, profile), "xgi")


def load_hnx(hif, *, validate="profile"):
    import pandas as pd
    import hypernetx as hnx
    doc = _read(hif)
    nt = _check(doc, validate)
    profile = validate == "profile" or "khg-profile" in (doc.get("metadata") or {})
    groups = {}
    for r in doc["incidences"]:
        groups.setdefault((_k(r["edge"]), _k(r["node"])), []).append(r)
    has_dir = any("direction" in r for r in doc["incidences"])
    rows = []
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

    def props(kind):
        m = _merged(doc, kind)
        if not m:
            return None
        idf = "node" if kind == "nodes" else "edge"
        w = {_k(r[idf]): r["weight"] for r in doc.get(kind, []) or [] if "weight" in r}
        return pd.DataFrame([{idf: i, "weight": w.get(k, 1), "attrs": a} for k, (i, a) in m.items()],
                            columns=[idf, "weight", "attrs"])
    # GL-13: the pinned call; per-kind misc_*_properties_col arguments are silently ignored by HNX 2.4.3
    H = hnx.Hypergraph(pd.DataFrame(rows, columns=cols), edge_col="edge", node_col="node", cell_weight_col="weight",
                       misc_cell_properties_col="attrs", node_properties=props("nodes"),
                       edge_properties=props("edges"), misc_properties_col="attrs")
    return Bundle(H, _context(doc, nt, profile), "hnx")


# ---------------------------------------------------------------------------------------------- export
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


def _weight(lib_value, loaded):
    """GL-05: the loaded value (with its JSON number type) unless the library holds a numerically different one."""
    if loaded is not None and lib_value is not None and float(lib_value) == float(loaded):
        return loaded
    if lib_value is None:
        return loaded
    v = _clean(lib_value)
    return int(v) if isinstance(v, float) and v.is_integer() and loaded is not None and isinstance(loaded, int) else v


def _cell_props(H, e, n):
    try:
        p = H.get_cell_properties(e, n)
    except Exception:  # noqa: BLE001
        return None
    return {k: v for k, v in (p or {}).items() if k not in ("weight", "direction")}


def _hnx_cells(H):
    """Every record held by the HyperNetX cells: the first from the cell's properties, the rest from the reserved key."""
    df = H.incidences.to_dataframe
    out = []
    for (e, n), row in df.iterrows():
        e, n = _clean(e), _clean(n)
        a = copy.deepcopy(row["misc_properties"]) if isinstance(row["misc_properties"], dict) else {}
        extra = a.pop(EXTRA, [])
        for c in df.columns:
            if c not in ("weight", "direction", "misc_properties") and not _missing(row[c]):
                a[c] = _clean(row[c])
        r = {"edge": e, "node": n}
        if "direction" in df.columns and not _missing(row["direction"]):
            r["direction"] = row["direction"]
        r["_lib_weight"] = _clean(row["weight"])
        r["attrs"] = a
        out.append(r)
        for x in extra:
            x = copy.deepcopy(x)
            x["edge"], x["node"] = e, n  # records follow the cell (renames)
            out.append(x)
    return out


def _value_of_node(nrec):
    a = (nrec or {}).get("attrs") or {}
    k = a.get("khg-kind")
    if k == "entity":
        return {"entity": nrec["node"]}
    if k == "literal":
        return {"literal": a.get("khg-literal")}
    if k == "fact-ref":
        return {"fact": a.get("khg-ref")}
    if k in ("somevalue", "novalue"):
        return {"special": k}
    if k == "unbound":
        return {"unbound": a.get("khg-unbound")}
    return {"entity": str(nrec["node"]) if nrec else ""}


def _canonical_order(out):
    """§4.2 order, recomputed from node attrs (GL-09): entity nodes by id then derived nodes by id; edges by id;
    incidences by edge, then (role, position, canonical value)."""
    nodes = {n["node"]: n for n in out["nodes"]}
    out["nodes"] = sorted(out["nodes"], key=lambda n: (str(n["node"]).startswith("_:"), str(n["node"])))
    out["edges"] = sorted(out["edges"], key=lambda e: str(e["edge"]))

    def ikey(i):
        a = i.get("attrs") or {}
        v = _value_of_node(nodes.get(i["node"]))
        try:
            cv = K.cjson(K.canon_value(v))
        except Exception:  # noqa: BLE001
            cv = K.cjson(v)
        return (str(i["edge"]), a.get("role", ""), a.get("role-position", 0), cv)
    out["incidences"] = sorted(out["incidences"], key=ikey)
    return out


def _typed_sort_key(r):
    return (type(r["edge"]).__name__, str(r["edge"]), type(r["node"]).__name__, str(r["node"]), str(r.get("direction")))


def _finish(bundle, live_nodes, node_attrs, node_libw, edge_ids, edge_attrs, edge_libw, kept, report, strict, lib):
    ctx = bundle.context
    if strict and (report["unlabelled"] or report["stale"] or report["moved_conflict"]):
        raise LoaderError("KHG-P005", f"strict export refused: {len(report['unlabelled'])} unlabelled, "
                                      f"{len(report['stale'])} partial, {len(report['moved_conflict'])} moved to "
                                      f"one node", {k: v for k, v in report.items()})
    out = {}
    if ctx.network_type is not None:
        out["network-type"] = ctx.network_type
    if ctx.metadata is not None:
        out["metadata"] = copy.deepcopy(ctx.metadata)
    inc_nodes = {_k(r["node"]) for r in kept}
    inc_edges = {_k(r["edge"]) for r in kept}
    nodes = []
    for n in live_nodes:
        tk = _k(n)
        if tk not in inc_nodes and tk not in ctx.node_isolated:
            report["dropped_nodes"].append(n)
            continue
        rec = {"node": n}
        w = _weight(node_libw.get(tk), ctx.node_weight.get(tk))
        if w is not None and (tk in ctx.node_weight or node_libw.get(tk) not in (None, 1, 1.0)):
            rec["weight"] = w
        a = node_attrs.get(tk)
        if a:
            rec["attrs"] = a
        if len(rec) > 1 or tk in {_k(x) for x in ctx.node_decl}:
            nodes.append(rec)
    edges = []
    for e in edge_ids:
        tk = _k(e)
        if tk not in inc_edges and tk not in ctx.edge_empty:
            report["dropped_edges"].append(e)
            continue
        rec = {"edge": e}
        w = _weight(edge_libw.get(tk), ctx.edge_weight.get(tk))
        if w is not None and (tk in ctx.edge_weight or edge_libw.get(tk) not in (None, 1, 1.0)):
            rec["weight"] = w
        a = edge_attrs.get(tk)
        if a:
            rec["attrs"] = a
        if len(rec) > 1 or tk in {_k(x) for x in ctx.edge_decl}:
            edges.append(rec)
    now = {_k(n) for n in live_nodes}
    report["dropped_nodes"] += [n for n in ctx.node_decl if _k(n) in ctx.node_isolated and _k(n) not in now]
    out["nodes"], out["edges"], out["incidences"] = nodes, edges, kept
    if ctx.profile:
        out = _canonical_order(out)
    bundle.report = report
    return out


def _new_report():
    return {"stale": [], "unlabelled": [], "moved": [], "moved_conflict": [], "dropped_records": [],
            "dropped_nodes": [], "dropped_edges": []}


def export_xgi(bundle, *, strict=True):
    import xgi
    H, ctx = bundle.graph, bundle.context
    directed = isinstance(H, xgi.DiHypergraph)
    live = {}
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
    edges_now = {_k(e) for e in H.edges}
    report, kept, used = _new_report(), [], set()
    for rk in ctx.order:
        r = ctx.records[rk]
        mem = (_k(r["edge"]), _k(r["node"]), r.get("direction") if directed else None)
        if mem in live:
            kept.append(copy.deepcopy(r))
            used.add(mem)
        elif _k(r["edge"]) in edges_now:
            report["stale"].append(r)             # a partial fact: its edge survives
        else:
            report["dropped_records"].append(r)   # its edge was removed whole
    for r in ctx.labels:
        mem = (_k(r["edge"]), _k(r["node"]), r.get("direction") if directed else None)
        if mem in live:
            kept.append(copy.deepcopy(r))
            used.add(mem)
    new = [dict(edge=e, node=n, **({"direction": d} if d else {})) for m, (e, n, d) in live.items() if m not in used]
    for r in sorted(new, key=_typed_sort_key):
        report["unlabelled"].append(r)
    if not strict:
        pass  # unlabelled memberships are dropped, never exported bare
    node_attrs = {_k(n): copy.deepcopy(dict(H.nodes[n])) for n in H.nodes}
    edge_attrs = {_k(e): copy.deepcopy(dict(H.edges[e])) for e in H.edges}
    live_nodes = _ordered(list(H.nodes), ctx.node_decl)
    edge_ids = _ordered(list(H.edges), ctx.edge_decl)
    return _finish(bundle, live_nodes, node_attrs, {}, edge_ids, edge_attrs, {}, kept, report, strict, "xgi")


def _ordered(ids_now, declared):
    now = {_k(i): i for i in ids_now}
    out, seen = [], set()
    for i in list(declared) + sorted(ids_now, key=lambda x: (type(x).__name__, str(x))):
        if _k(i) in now and _k(i) not in seen:
            seen.add(_k(i))
            out.append(now[_k(i)])
    return out


def export_hnx(bundle, *, strict=True):
    H, ctx = bundle.graph, bundle.context
    cells = _hnx_cells(H)
    edges_now = {_k(e) for e in H.edges}
    report, kept = _new_report(), []
    # which loaded records are still carried by a cell, and on which node
    carried = {}
    loaded_pairs = {(_k(r["edge"]), _k(r["node"])) for r in ctx.records.values()}
    for r in cells:
        a = r.get("attrs") or {}
        new_pair = (_k(r["edge"]), _k(r["node"])) not in loaded_pairs
        if ctx.profile:
            if "khg-bid" not in a or "role" not in a:
                report["unlabelled"].append({k: v for k, v in r.items() if k != "_lib_weight"})
                continue
            rk = (_k(r["edge"]), a["khg-bid"])
        else:
            if new_pair and "role" not in a:   # a new membership needs a record; loaded cells are records as they are
                report["unlabelled"].append({k: v for k, v in r.items() if k != "_lib_weight"})
                continue
            rk = None
        if rk is not None:
            if rk in carried:
                report["moved_conflict"].append(r)
                continue
            carried[rk] = r
        loaded = ctx.records.get(rk) if rk else None
        out = {k: v for k, v in r.items() if k != "_lib_weight"}
        lw = r.get("_lib_weight")
        if "_lib_weight" in r:
            lw_loaded = loaded.get("weight") if loaded else None
            w = _weight(lw, lw_loaded)
            if loaded is not None and "weight" in loaded:
                out["weight"] = w
            elif lw not in (None, 1, 1.0):
                out["weight"] = _clean(lw)
        if loaded is not None and _k(loaded["node"]) != _k(r["node"]):
            report["moved"].append({"edge": r["edge"], "bid": rk[1], "from": loaded["node"], "to": r["node"]})
        if not ctx.profile and not out.get("attrs") and any(
                "attrs" not in x for x in ctx.records.values() if (_k(x["edge"]), _k(x["node"])) == (_k(r["edge"]), _k(r["node"]))):
            out.pop("attrs", None)          # absent attrs stay absent (R03 c15, c25)
        kept.append({k: out[k] for k in ("edge", "node", "direction", "weight", "attrs") if k in out})
    # moved records must come from an injective node map (a rename), else it is a collapse
    fwd = {}
    for m in report["moved"]:
        fwd.setdefault(_k(m["from"]), set()).add(_k(m["to"]))
    back = {}
    for m in report["moved"]:
        back.setdefault(_k(m["to"]), set()).add(_k(m["from"]))
    if any(len(v) > 1 for v in fwd.values()) or any(len(v) > 1 for v in back.values()):
        report["moved_conflict"] += report["moved"]
    for rk in ctx.order:
        if ctx.profile and rk not in carried:
            r = ctx.records[rk]
            (report["stale"] if _k(r["edge"]) in edges_now else report["dropped_records"]).append(r)
    if not ctx.profile:
        # GL-09: files without the profile keep the source order of their records; anything new follows, typed-sorted
        slots = {}
        for pos, rk in enumerate(ctx.order):
            r = ctx.records[rk]
            key = (_k(r["edge"]), _k(r["node"]), K.cjson(r.get("attrs") or {}), r.get("direction"))
            slots.setdefault(key, []).append(pos)

        def place(r):
            key = (_k(r["edge"]), _k(r["node"]), K.cjson(r.get("attrs") or {}), r.get("direction"))
            free = slots.get(key)
            return (free.pop(0), ()) if free else (len(ctx.order), _typed_sort_key(r))
        kept = [r for _, r in sorted(((place(r), r) for r in kept), key=lambda x: x[0])]
    # node and edge records from the property stores (they keep isolated nodes; views do not)
    def store_rows(view):
        st = view.property_store.properties
        out = {}
        for i in st.index:
            row = st.loc[i]
            a = copy.deepcopy(row["misc_properties"]) if isinstance(row["misc_properties"], dict) else {}
            for c in st.columns:
                if c not in ("weight", "misc_properties") and not _missing(row[c]):
                    a[c] = _clean(row[c])
            out[_k(_clean(i))] = (_clean(i), a, _clean(row["weight"]))
        return out
    nrows, erows = store_rows(H.nodes), store_rows(H.edges)
    live_nodes = _ordered([v[0] for v in nrows.values()], ctx.node_decl)
    edge_ids = _ordered([v[0] for v in erows.values() if v[0] in set(H.edges) or _k(v[0]) in ctx.edge_empty],
                        ctx.edge_decl)
    return _finish(bundle, live_nodes, {k: v[1] for k, v in nrows.items()}, {k: v[2] for k, v in nrows.items()},
                   edge_ids, {k: v[1] for k, v in erows.items()}, {k: v[2] for k, v in erows.items()},
                   kept, report, strict, "hnx")


# ---------------------------------------------------------------------------------------------- C1 conveniences
def khg_to_xgi(container, schema, **kw):
    return load_xgi(K.c1_to_hif(container, schema, **kw))


def khg_to_hnx(container, schema, **kw):
    return load_hnx(K.c1_to_hif(container, schema, **kw))


def xgi_to_khg(bundle, schema, *, strict=True):
    return K.hif_to_c1(export_xgi(bundle, strict=strict), schema)


def hnx_to_khg(bundle, schema, *, strict=True):
    return K.hif_to_c1(export_hnx(bundle, strict=strict), schema)
