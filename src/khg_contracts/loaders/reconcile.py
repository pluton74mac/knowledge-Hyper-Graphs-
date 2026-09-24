"""Export reconciles the library object with the context (DESIGN §5; critique GL-05, GL-08, GL-09, LOADER-STRICT).

The library object decides which memberships exist; the per-library modules find the records of those memberships
and fill the report's record classes. ``finish`` then writes the document:

- **weights**: the library's value only when it differs numerically from the loaded one, otherwise the loaded value
  with its JSON number type (``reconcile_weight``);
- **node and edge records** for nodes and edges with an exported incidence, plus those that were isolated or empty in
  the loaded file and still exist; the others, derived ``_:`` nodes included, are dropped and reported. Their
  ``attrs`` come from the library, so native attribute edits are honoured;
- **the strict rule**: ``strict=True`` raises ``LoaderError`` (P005) when a membership is unlabelled, a record is
  stale (a partial fact) or a move is not injective; records of edges removed whole are only reported;
- **network-type**: the loaded one, except that a profile file follows the profile's direction rule (§4.2; P010,
  P011) on the exported records: ``directed`` iff every record has a direction (``_network_type``);
- **order**: profile files in the §4.2 order recomputed from the node attrs; other files keep the source order of
  their records, and anything new follows, sorted by a typed key. Nothing depends on ``PYTHONHASHSEED``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Optional, Tuple

from .. import jsonio
from ..errors import LoaderError
from ._common import TypedKey, is_default_weight, is_missing, plain, tkey
from ._input import copy_json
from .report import ExportReport, strict_violations

if TYPE_CHECKING:  # pragma: no cover
    from .bundle import Bundle

__all__ = ["Item", "Kept", "clean_record", "finish", "membership", "reconcile_weight", "record_sort_key"]

#: A node or edge as the library holds it: ``(id, attrs, library weight or None)``.
Item = Tuple[Any, dict, Any]
#: An exported record and its source position (None for a record the loaded file did not have).
Kept = Tuple[Optional[int], dict]

_RECORD_FIELDS = ("edge", "node", "direction", "weight", "attrs")


def reconcile_weight(library: Any, loaded: Any) -> Any:
    """The weight to export (GL-05): the loaded value, with its JSON number type, unless the library holds a
    numerically different one; a float the library made of a loaded integer is written as an integer."""
    library = plain(library)
    if is_missing(library):
        return loaded
    if loaded is not None and float(library) == float(loaded):
        return loaded
    if isinstance(library, float) and library.is_integer() and isinstance(loaded, int):
        return int(library)
    return library


def membership(record: dict[str, Any]) -> dict[str, Any]:
    """The membership a record names: ``{edge, node, direction?}``."""
    out = {"edge": record["edge"], "node": record["node"]}
    if record.get("direction") is not None:
        out["direction"] = record["direction"]
    return out


def record_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    """The typed key new records and memberships are sorted by: edge, node, direction, then the attrs."""
    return (tkey(record["edge"]), tkey(record["node"]), record.get("direction") or "",
            jsonio.canonical(record.get("attrs") or {}))


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    """A record with the HIF incidence fields only, in the HIF order."""
    return {k: record[k] for k in _RECORD_FIELDS if k in record}


def _ordered_ids(ids: Iterable[Any], declared: list[Any]) -> list[Any]:
    """The declared ids that still exist, in source order, then the others sorted by typed key."""
    now = {tkey(i): i for i in ids}
    out = [now[tkey(i)] for i in declared if tkey(i) in now]
    seen = {tkey(i) for i in out}
    return out + sorted((i for k, i in now.items() if k not in seen), key=tkey)


def _items(idf: str, rows: list[Item], declared: list[Any], incident: set[TypedKey], kept_alone: frozenset,
           loaded_weights: dict[TypedKey, Any], with_attrs: frozenset, dropped: list[Any]) -> list[dict[str, Any]]:
    by_key = {tkey(i): (i, attrs, w) for i, attrs, w in rows}
    declared_keys = {tkey(i) for i in declared}
    out = []
    for i in _ordered_ids([r[0] for r in rows], declared):
        k = tkey(i)
        _, attrs, library_weight = by_key[k]
        if k not in incident and k not in kept_alone:
            dropped.append(i)
            continue
        item: dict[str, Any] = {idf: i}
        if k in loaded_weights:
            item["weight"] = reconcile_weight(library_weight, loaded_weights[k])
        elif not is_default_weight(library_weight):
            item["weight"] = plain(library_weight)
        if attrs or k in with_attrs:
            item["attrs"] = attrs
        if len(item) > 1 or k in declared_keys:
            out.append(item)
    return out


def _ordered_records(kept: list[Kept]) -> list[dict[str, Any]]:
    loaded = sorted(((slot, n) for n, (slot, _) in enumerate(kept) if slot is not None))
    new = sorted((r for slot, r in kept if slot is None), key=record_sort_key)
    return [kept[n][1] for _, n in loaded] + new


def _network_type(loaded: str | None, records: list[dict[str, Any]], profile: bool) -> str | None:
    """The exported ``network-type``. A profile file follows the profile's direction rule (§4.2; P010, P011) on the
    exported records, as ``to_hif`` does: ``directed`` when every record has a direction, and no longer ``directed``
    once one lacks it (an edit can remove the last incidence without a direction, or add one). Otherwise the loaded
    value stays: in files without the profile, where HIF allows native directions in any network type, and in an
    export without records, where both values pass."""
    if not profile or not records:
        return loaded
    if all(r.get("direction") is not None for r in records):
        return "directed"
    return "undirected" if loaded == "directed" else loaded


def finish(bundle: Bundle, nodes: list[Item], edges: list[Item], kept: list[Kept], report: ExportReport,
           strict: bool) -> dict[str, Any]:
    """Write the exported HIF document of ``bundle`` from the library's nodes and edges and the kept records,
    complete ``report``, set ``bundle.report``, and apply the strict rule."""
    ctx = bundle.context
    records = [clean_record(r) for _, r in kept] if ctx.profile else [clean_record(r) for r in _ordered_records(kept)]
    incident_nodes = {tkey(r["node"]) for r in records}
    incident_edges = {tkey(r["edge"]) for r in records}
    node_items = _items("node", nodes, ctx.node_ids, incident_nodes, ctx.isolated_nodes, ctx.node_weight,
                        ctx.node_attrs, report["dropped_nodes"])
    now = {tkey(n) for n, _, _ in nodes}
    report["dropped_nodes"].extend(n for n in ctx.node_ids if tkey(n) in ctx.isolated_nodes and tkey(n) not in now)
    edge_items = _items("edge", edges, ctx.edge_ids, incident_edges, ctx.empty_edges, ctx.edge_weight,
                        ctx.edge_attrs, report["dropped_edges"])
    now = {tkey(e) for e, _, _ in edges}
    report["dropped_edges"].extend(e for e in ctx.edge_ids if tkey(e) in ctx.empty_edges and tkey(e) not in now)
    bundle.report = report
    violations = strict_violations(report)
    if strict and violations:
        what = ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in violations.items())
        raise LoaderError(f"KHG-P005: strict export refused ({what}); label new memberships with Bundle.label, or "
                          f"export with strict=False to drop and report them", codes=["KHG-P005"],
                          info={"report": report})
    out: dict[str, Any] = {}
    network_type = _network_type(ctx.network_type, records, ctx.profile)
    if network_type is not None:
        out["network-type"] = network_type
    if ctx.metadata is not None:
        out["metadata"] = copy_json(ctx.metadata)
    if node_items or "nodes" in ctx.top_keys:
        out["nodes"] = node_items
    if edge_items or "edges" in ctx.top_keys:
        out["edges"] = edge_items
    out["incidences"] = records
    if ctx.profile:
        from ..hif import canonical_order
        out = canonical_order(out)
    return out
