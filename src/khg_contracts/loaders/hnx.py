"""The HyperNetX loader (DESIGN §5): ``load_hnx`` and ``export_hnx``.

Construction uses the public ``Hypergraph`` constructor with this call pinned (critique GL-13)::

    hypernetx.Hypergraph(incidences_df, edge_col="edge", node_col="node", cell_weight_col="weight",
                         misc_cell_properties_col="attrs", node_properties=nodes_df, edge_properties=edges_df,
                         misc_properties_col="attrs")

HyperNetX 2.4.3 silently ignores the per-kind ``misc_node_properties_col`` and ``misc_edge_properties_col``, so they
are not used. ``hnx.from_hif`` and ``hnx.to_hif`` are never called (F1): they fetch the HIF schema over the network,
drop the metadata and repeated records, and write ``"nil"`` for a missing direction [R03 §4, §6].

The cells are the source of truth for incidence records (critique GL-03). A pair's first record is the cell's
properties, so native readers see ``role``, ``khg-bid`` and ``role-position``; its weight is the cell weight and its
direction the direction column. Records 2..k of the same (edge, node) pair ride under the reserved cell key
``khg-extra-incidences`` and follow the cell through renames. pandas and hypernetx are imported on first use.
"""
from __future__ import annotations

import copy
import os
from types import ModuleType
from typing import Any, Literal, Mapping, Union

from ..errors import LoaderError, make_finding
from ._common import EXTRA, TypedKey, is_default_weight, is_missing, plain, tkey
from ._input import InputRefused, check_document, is_profile, read_document
from .bundle import Bundle
from .context import Context, RecordKey, build_context
from .reconcile import Item, Kept, clean_record, finish, membership, reconcile_weight
from .report import ExportReport, new_report

__all__ = ["HNX_KEYWORDS", "attach", "export_hnx", "load_hnx", "records"]

#: The pinned keyword arguments of the ``hypernetx.Hypergraph`` call (the property frames are added per file).
HNX_KEYWORDS = {"edge_col": "edge", "node_col": "node", "cell_weight_col": "weight",
                "misc_cell_properties_col": "attrs", "misc_properties_col": "attrs"}
_COLUMNS = ("weight", "direction", "misc_properties")


def _libraries() -> tuple[ModuleType, ModuleType]:
    try:
        import hypernetx
        import pandas
    except ImportError as e:  # pragma: no cover - exercised only without the extra
        raise ImportError("the HyperNetX loader needs hypernetx and pandas: pip install 'khg-contracts[hnx]'") from e
    return pandas, hypernetx


def _properties(pandas: ModuleType, doc: Mapping[str, Any], key: str) -> Any:
    """The node or edge property frame: id, weight (1 when absent) and attrs; None without declarations."""
    items = doc.get(key) or []
    if not items:
        return None
    idf = key[:-1]
    return pandas.DataFrame([{idf: x[idf], "weight": x.get("weight", 1), "attrs": copy.deepcopy(x.get("attrs") or {})}
                             for x in items], columns=[idf, "weight", "attrs"])


def _refuse_reserved_key(doc: Mapping[str, Any]) -> None:
    found = [make_finding("KHG-P014", f"/incidences/{j}/attrs/{EXTRA}", f"{EXTRA} is reserved for the HyperNetX loader")
             for j, r in enumerate(doc["incidences"]) if EXTRA in (r.get("attrs") or {})]
    if found:
        raise InputRefused.from_findings(found)


def load_hnx(hif: Union[Mapping[str, Any], str, os.PathLike],
             *, validate: Literal["profile", "convention", "none"] = "profile") -> Bundle:
    """Load a HIF file into a ``hypernetx.Hypergraph`` through its public constructor. ``hif`` is a parsed document
    or a path (a ``str`` is always a path). Raises ``LoaderError`` (also a ``ValidationError``) when the input is
    refused: the codes of the ``validate`` mode, D001, P007 or P010, and P014 for an incidence ``attrs`` key
    ``khg-extra-incidences``, which the loader reserves."""
    doc = read_document(hif)
    check_document(doc, validate)
    _refuse_reserved_key(doc)
    ctx = build_context(doc, is_profile(doc, validate))
    pandas, hypernetx = _libraries()
    groups: dict[tuple[TypedKey, TypedKey], list[dict[str, Any]]] = {}
    for r in doc["incidences"]:
        groups.setdefault((tkey(r["edge"]), tkey(r["node"])), []).append(r)
    rows = []
    for recs in groups.values():
        first = recs[0]
        attrs = copy.deepcopy(first.get("attrs") or {})
        if len(recs) > 1:
            attrs[EXTRA] = [copy.deepcopy(r) for r in recs[1:]]
        rows.append({"edge": first["edge"], "node": first["node"], "weight": first.get("weight", 1),
                     "direction": first.get("direction"), "attrs": attrs})
    columns = ["edge", "node", "weight", "direction", "attrs"]  # a direction column always, so labels can set it
    graph = hypernetx.Hypergraph(pandas.DataFrame(rows, columns=columns), edge_col="edge", node_col="node",
                                 cell_weight_col="weight", misc_cell_properties_col="attrs",
                                 node_properties=_properties(pandas, doc, "nodes"),
                                 edge_properties=_properties(pandas, doc, "edges"), misc_properties_col="attrs")
    return Bundle(graph, ctx, "hnx")


# ------------------------------------------------------------------------------------------------ reading the cells


def _cells(graph: Any) -> list[tuple[dict[str, Any], Any, list[dict[str, Any]]]]:
    """Each cell in the library's order: its first record (without weight), the cell weight, and its further
    records, which follow the cell's (edge, node)."""
    frame = graph.incidences.to_dataframe
    others = [c for c in frame.columns if c not in _COLUMNS]
    out = []
    for (e, n), row in frame.iterrows():
        e, n = plain(e), plain(n)
        misc = row["misc_properties"] if "misc_properties" in frame.columns else None
        attrs = copy.deepcopy(misc) if isinstance(misc, dict) else {}
        extra = attrs.pop(EXTRA, None)
        for c in others:
            if not is_missing(row[c]):
                attrs[c] = plain(row[c])
        first: dict[str, Any] = {"edge": e, "node": n}
        if "direction" in frame.columns and not is_missing(row["direction"]):
            first["direction"] = plain(row["direction"])
        first["attrs"] = attrs
        weight = plain(row["weight"]) if "weight" in frame.columns else None
        rest = []
        for x in extra if isinstance(extra, list) else []:
            if isinstance(x, dict):
                rest.append({"edge": e, "node": n, **{k: copy.deepcopy(v) for k, v in x.items()
                                                      if k not in ("edge", "node")}})
        out.append((first, weight, rest))
    return out


def _labelled(record: Mapping[str, Any], profile: bool) -> bool:
    attrs = record.get("attrs")
    if not isinstance(attrs, Mapping) or not isinstance(attrs.get("role"), str) or not attrs["role"]:
        return False
    return not profile or isinstance(attrs.get("khg-bid"), str)


def _with_weight(record: dict[str, Any], library_weight: Any, loaded: Mapping[str, Any] | None) -> dict[str, Any]:
    """The first record of a cell with its weight: reconciled with the loaded record's, or the cell's own when it is
    not the default."""
    record.pop("weight", None)
    if loaded is not None and "weight" in loaded:
        record["weight"] = reconcile_weight(library_weight, loaded["weight"])
    elif not is_default_weight(library_weight):
        record["weight"] = plain(library_weight)
    return record


def _keep_absent_attrs(record: dict[str, Any], loaded: Mapping[str, Any] | None) -> dict[str, Any]:
    """A record whose loaded form had no ``attrs`` keeps none while its attrs stay empty (R03 c15, c25)."""
    if not record.get("attrs") and loaded is not None and "attrs" not in loaded:
        record.pop("attrs", None)
    return record


class _Reconciled:
    """The records the cells carry, matched against the loaded records (DESIGN §5)."""

    def __init__(self, graph: Any, ctx: Context):
        self.ctx = ctx
        self.report: ExportReport = new_report()
        self.kept: list[Kept] = []
        self.carried: dict[RecordKey, dict[str, Any]] = {}
        self.moves: list[tuple[TypedKey, TypedKey, dict[str, Any]]] = []
        slots = ctx.slots()
        by_pair = ctx.pair_records()
        for first, weight, rest in _cells(graph):
            loaded_keys = by_pair.get((tkey(first["edge"]), tkey(first["node"])), [])
            for k, record in enumerate([first] + rest):
                keep, rk = self._by_bid(record) if ctx.profile else self._by_ordinal(record, loaded_keys, k)
                if not keep:
                    continue
                loaded = ctx.records.get(rk) if rk is not None else None
                if k == 0:
                    record = _with_weight(record, weight, loaded)
                if not ctx.profile:
                    record = _keep_absent_attrs(record, loaded)
                record = clean_record(record)
                if rk is not None:
                    self.carried[rk] = record
                self.kept.append((slots.get(rk) if rk is not None else None, record))

    def _by_bid(self, record: dict[str, Any]) -> tuple[bool, RecordKey | None]:
        """A record of a profile file, keyed by (edge, khg-bid); not kept when it is unlabelled or repeats a bid
        another cell carries (both reported)."""
        if not _labelled(record, True):
            self.report["unlabelled"].append(membership(record))
            return False, None
        bid = record["attrs"]["khg-bid"]
        rk = (tkey(record["edge"]), bid)
        loaded = self.ctx.records.get(rk)
        if rk in self.carried:
            self.report["moved_conflict"].append(
                {"edge": record["edge"], "bid": bid, "from": loaded["node"] if loaded else None, "to": record["node"]})
            return False, None
        if loaded is not None:
            self.moves.append((tkey(loaded["node"]), tkey(record["node"]), {
                "edge": record["edge"], "bid": bid, "from": loaded["node"], "to": record["node"]}))
        return True, rk

    def _by_ordinal(self, record: dict[str, Any], loaded_keys: list[RecordKey],
                    k: int) -> tuple[bool, RecordKey | None]:
        """A record of another file: the k-th record of a loaded pair is that pair's k-th loaded record; a new record
        needs a role (else it is reported unlabelled and not kept)."""
        rk = loaded_keys[k] if k < len(loaded_keys) else None
        if rk in self.carried:  # a second cell for one pair: its loaded record is carried already
            rk = None
        if rk is None and not _labelled(record, False):
            self.report["unlabelled"].append(membership(record))
            return False, None
        return True, rk

    def finish_moves(self) -> None:
        """Report moved records, and as conflicts those whose old-to-new node map is not injective."""
        forward: dict[TypedKey, set[TypedKey]] = {}
        backward: dict[TypedKey, set[TypedKey]] = {}
        for old, new, _ in self.moves:
            forward.setdefault(old, set()).add(new)
            backward.setdefault(new, set()).add(old)
        for old, new, move in self.moves:
            if old == new:
                continue
            self.report["moved"].append(move)
            if (len(forward[old]) > 1 or len(backward[new]) > 1) and move not in self.report["moved_conflict"]:
                self.report["moved_conflict"].append(move)

    def finish_loaded(self, edges_now: set[TypedKey]) -> None:
        """Loaded records no cell carries: stale while their edge exists, dropped when it was removed whole."""
        for rk in self.ctx.order:
            if rk not in self.carried:
                r = copy.deepcopy(self.ctx.records[rk])
                (self.report["stale"] if tkey(r["edge"]) in edges_now else self.report["dropped_records"]).append(r)


def _store_items(view: Any) -> list[Item]:
    """The nodes or edges of a property store (which keeps isolated nodes and empty edges; views do not)."""
    frame = view.property_store.properties
    others = [c for c in frame.columns if c not in ("weight", "misc_properties")]
    out: list[Item] = []
    for i, row in frame.iterrows():
        misc = row["misc_properties"] if "misc_properties" in frame.columns else None
        attrs = copy.deepcopy(misc) if isinstance(misc, dict) else {}
        for c in others:
            if not is_missing(row[c]):
                attrs[c] = plain(row[c])
        out.append((plain(i), attrs, plain(row["weight"]) if "weight" in frame.columns else None))
    return out


def _check_bundle(bundle: Bundle) -> None:
    if bundle.lib != "hnx":
        raise TypeError(f"export_hnx needs a HyperNetX bundle, not a {bundle.lib} one")


# ------------------------------------------------------------------------------------------------ export


def export_hnx(bundle: Bundle, *, strict: bool = True) -> dict[str, Any]:
    """The HIF document of a HyperNetX bundle, reconciled with its context (DESIGN §5). Sets ``bundle.report``.
    ``strict=True`` raises ``LoaderError`` (P005) on an unlabelled membership, a partial fact or a non-injective
    move; ``strict=False`` drops and reports them. A record whose ``khg-bid`` now sits on another node through an
    injective map (a rename) is exported and reported under ``moved``."""
    _check_bundle(bundle)
    graph, ctx = bundle.graph, bundle.context
    edges_now = {tkey(plain(e)) for e in graph.edges}
    rec = _Reconciled(graph, ctx)
    rec.finish_moves()
    rec.finish_loaded(edges_now)
    nodes = _store_items(graph.nodes)
    edges = [item for item in _store_items(graph.edges) if tkey(item[0]) in edges_now or tkey(item[0]) in
             ctx.empty_edges]
    return finish(bundle, nodes, edges, rec.kept, rec.report, strict)


# ------------------------------------------------------------------------------------------------ Bundle methods


def records(bundle: Bundle, edge: Any, node: Any = None) -> list[dict[str, Any]]:
    """The records the cells of ``edge`` (and ``node``) carry, in cell order: each cell's record, then its further
    records."""
    rec = _Reconciled(bundle.graph, bundle.context)
    return [r for _, r in rec.kept
            if tkey(r["edge"]) == tkey(edge) and (node is None or tkey(r["node"]) == tkey(node))]


def _cell_properties(graph: Any, edge: Any, node: Any) -> dict[str, Any] | None:
    frame = graph.incidences.to_dataframe
    for (e, n), row in frame.iterrows():
        if tkey(plain(e)) == tkey(edge) and tkey(plain(n)) == tkey(node):
            misc = row["misc_properties"] if "misc_properties" in frame.columns else None
            return misc if isinstance(misc, dict) else {}
    return None


def attach(bundle: Bundle, record: dict[str, Any]) -> None:
    """Write ``record`` into the cell of its membership, which must exist: as the cell's own record when the cell
    has no role yet (a new membership), else under ``khg-extra-incidences``."""
    graph = bundle.graph
    edge, node = record["edge"], record["node"]
    props = _cell_properties(graph, edge, node)
    if props is None:
        what = membership(record)
        raise LoaderError(f"KHG-P005: no HyperNetX cell {what} to label", codes=["KHG-P005"],
                          info={"findings": [make_finding("KHG-P005", "", f"no HyperNetX cell {what} to label")]})
    store = graph.incidences.property_store  # PropertyStore.set_property is public in HyperNetX 2.4.3
    uid = (edge, node)
    if not props.get("role"):
        for key, value in record["attrs"].items():
            store.set_property(uid, key, copy.deepcopy(value))
        for key in ("direction", "weight"):
            if key in record:
                store.set_property(uid, key, record[key])
    else:
        extra = [copy.deepcopy(x) for x in props.get(EXTRA) or []]
        extra.append(copy.deepcopy(record))
        store.set_property(uid, EXTRA, extra)
