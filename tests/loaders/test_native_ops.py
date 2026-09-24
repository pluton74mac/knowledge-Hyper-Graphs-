"""W7: the native-operation table of DESIGN §5, one test per row of ``native-ops.json`` (20 rows).

Each XGI or HyperNetX operation is applied to the gate fixture (``fixture.hif.json``, or the directed slice for the
``DiHypergraph`` row) and exported with ``strict=True``. The outcome classes, as the prototype ``native_ops.py``
records them:

- ``exact``: the export equals the loaded file;
- ``removals``: it exports; records of edges removed whole, and nodes left without incidences, are dropped and
  reported;
- ``moved``: it exports; a record moved to another node through an injective map (a rename);
- ``needs-label -> ...``: it raises until ``Bundle.label`` gives each new membership its record, then exports;
- ``raises (partial)`` or ``raises (unlabelled)``: a partial fact, or memberships without a record;
- ``unsupported (...)``: the library itself raises.

Beyond the outcome, each test checks what the design's table says about the row.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

import pytest

from khg_contracts import data, jsonio, loaders
from khg_contracts.errors import LoaderError

xgi = pytest.importorskip("xgi")
hypernetx = pytest.importorskip("hypernetx")

pytestmark = pytest.mark.libs

TABLE = json.loads((Path(__file__).resolve().parent / "native-ops.json").read_text(encoding="utf-8"))
ROWS = TABLE["rows"]
FILES = {"full": "fixture/fixture.hif.json", "slice": "fixture/fixture.directed-slice.hif.json"}

Op = Callable[[loaders.Bundle], loaders.Bundle]
Relabel = Callable[[loaders.Bundle], None]


# ------------------------------------------------------------------------------------------------ the operations


def _x_add_edge(b: loaders.Bundle) -> loaders.Bundle:
    b.graph.add_edge({"ex:TP53", "ex:HeLa"}, idx="f:new")
    b.graph.set_edge_attributes({"f:new": {"relation": "regulates", "khg-status": "asserted"}})
    return b


def _x_add_edge_label(b: loaders.Bundle) -> None:
    b.label("f:new", "ex:TP53", role="regulator", bid="b1", direction="tail")
    b.label("f:new", "ex:HeLa", role="context", bid="b2", direction="tail")


def _x_readd(b: loaders.Bundle) -> loaders.Bundle:
    b.graph.remove_node_from_edge("f:reg-1", "ex:HeLa")
    b.graph.add_node_to_edge("f:reg-1", "ex:HeLa")
    return b


def _but_hela(nodes: Any) -> list[Any]:
    return [n for n in nodes if n != "ex:HeLa"]


def _in_place(action: Callable[[Any], Any]) -> Op:
    def op(b: loaders.Bundle) -> loaders.Bundle:
        action(b.graph)
        return b
    return op


def _h_collapse(b: loaders.Bundle) -> loaders.Bundle:
    r = b.graph.collapse_nodes()
    return b.derive(r[0] if isinstance(r, tuple) else r)


def _h_sum(b: loaders.Bundle) -> loaders.Bundle:
    other = loaders.load_hnx(data.load_json(FILES["slice"]))
    return b.derive(b.graph.sum(other.graph))


OPERATIONS: dict[tuple[str, str], tuple[Op, Relabel | None]] = {
    ("xgi", "copy() then derive"): (lambda b: b.derive(b.graph.copy()), None),
    ("xgi", "remove_node('ex:HeLa') (weak: f:reg-1 survives)"): (_in_place(lambda g: g.remove_node("ex:HeLa")), None),
    ("xgi", "remove_node('ex:HeLa', strong=True) (f:reg-1 removed whole)"):
        (_in_place(lambda g: g.remove_node("ex:HeLa", strong=True)), None),
    ("xgi", "add_edge + set_edge_attributes, then label"): (_x_add_edge, _x_add_edge_label),
    ("xgi", "add_node_to_edge('f:reg-1', 'ex:Paris'), then label"):
        (_in_place(lambda g: g.add_node_to_edge("f:reg-1", "ex:Paris")),
         lambda b: b.label("f:reg-1", "ex:Paris", role="context", bid="b4", direction="tail")),
    ("xgi", "remove_node_from_edge + add_node_to_edge (same pair)"): (_x_readd, None),
    ("xgi", "subhypergraph(all nodes but ex:HeLa) then derive"):
        (lambda b: b.derive(xgi.subhypergraph(b.graph, nodes=_but_hela(b.graph.nodes))), None),
    ("xgi", "subhypergraph on a DiHypergraph"):
        (lambda b: b.derive(xgi.subhypergraph(b.graph, nodes=_but_hela(b.graph.nodes))), None),
    ("xgi", "convert_labels_to_integers"): (lambda b: b.derive(xgi.convert_labels_to_integers(b.graph)), None),
    ("xgi", "dual()"): (lambda b: b.derive(b.graph.dual()), None),
    ("xgi", "cleanup() (relabels to integers by default)"): (_in_place(lambda g: g.cleanup()), None),
    ("hnx", "clone() then derive (HyperNetX drops the isolated ex:Mazarin)"):
        (lambda b: b.derive(b.graph.clone()), None),
    ("hnx", "restrict_to_edges(all but f:reg-1) then derive"):
        (lambda b: b.derive(b.graph.restrict_to_edges([e for e in b.graph.edges if e != "f:reg-1"])), None),
    ("hnx", "remove_edges(['f:reg-1'])"): (_in_place(lambda g: g.remove_edges(["f:reg-1"])), None),
    ("hnx", "remove_incidences([('f:reg-1', 'ex:HeLa')])"):
        (_in_place(lambda g: g.remove_incidences([("f:reg-1", "ex:HeLa")])), None),
    ("hnx", "rename(nodes={'ex:HeLa': 'ex:HeLa-cells'})"):
        (_in_place(lambda g: g.rename(nodes={"ex:HeLa": "ex:HeLa-cells"})), None),
    ("hnx", "add_incidence('f:reg-1', 'ex:Paris'), then label"):
        (_in_place(lambda g: g.add_incidence("f:reg-1", "ex:Paris", direction="tail")),
         lambda b: b.label("f:reg-1", "ex:Paris", role="context", bid="b4")),
    ("hnx", "restrict_to_nodes(all but ex:HeLa) then derive"):
        (lambda b: b.derive(b.graph.restrict_to_nodes(_but_hela(b.graph.nodes))), None),
    ("hnx", "collapse_nodes() then derive"): (_h_collapse, None),
    ("hnx", "sum(slice) then derive (the slice is a subset; the isolated node is lost)"): (_h_sum, None),
}


# ------------------------------------------------------------------------------------------------ the runner


def _outcome(bundle: loaders.Bundle, original: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    export = loaders.export_xgi if bundle.lib == "xgi" else loaders.export_hnx
    try:
        out = export(bundle)
    except LoaderError as e:
        assert e.codes == ("KHG-P005",)
        report = e.info["report"]
        why = "partial" if report["stale"] else "unlabelled" if report["unlabelled"] else "moved to one node"
        return f"raises ({why})", None
    report = bundle.report
    if jsonio.canonical(out) == jsonio.canonical(original):
        return "exact", out
    if report["moved"]:
        return "moved", out
    if report["dropped_records"] or report["dropped_nodes"] or report["dropped_edges"]:
        return "removals", out
    return "exports (changed)", out


def _run(row: dict[str, Any]) -> tuple[str, loaders.Bundle | None, dict[str, Any] | None, dict[str, Any] | None]:
    """The outcome, the bundle that was exported, the export, and the first (refused) report of a relabelled row."""
    doc = data.load_json(FILES[row["file"]])
    op, relabel = OPERATIONS[(row["library"], row["operation"])]
    bundle = (loaders.load_xgi if row["library"] == "xgi" else loaders.load_hnx)(copy.deepcopy(doc))
    try:
        derived = op(bundle)
    except Exception as e:  # noqa: BLE001 - the library's own refusal is the outcome
        return f"unsupported ({type(e).__name__})", None, None, None
    result, out = _outcome(derived, doc)
    first = None
    if result == "raises (unlabelled)" and relabel is not None:
        first = copy.deepcopy(derived.report)
        relabel(derived)
        second, out = _outcome(derived, doc)
        result = f"needs-label -> {second}"
    return result, derived, out, first


def test_the_table_has_the_twenty_rows_of_section_5():
    assert TABLE["format"] == "khg-native-ops/1.0.0" and TABLE["strict"] is True
    assert len(ROWS) == 20 and all(r["ok"] for r in ROWS)
    assert [(r["library"], r["operation"]) for r in ROWS] == list(OPERATIONS)
    assert sum(r["library"] == "xgi" for r in ROWS) == 11 and sum(r["library"] == "hnx" for r in ROWS) == 9
    assert [r["file"] for r in ROWS].count("slice") == 1


@pytest.mark.parametrize("row", ROWS, ids=[f"{r['library']}: {r['operation']}" for r in ROWS])
def test_native_operation(row):
    result, bundle, out, first = _run(row)
    assert result == row["outcome"]
    assert result.split(" ")[0] == row["expected"].split(" ")[0]
    CHECKS.get((row["library"], row["operation"]), lambda *a: None)(bundle, out, first)


# ------------------------------------------------------------------------------------------------ per-row content


def _bids(out: dict[str, Any], edge: str) -> list[str]:
    return [i["attrs"]["khg-bid"] for i in out["incidences"] if i["edge"] == edge]


def _check_weak_remove(bundle, out, first):
    assert [(r["edge"], r["node"]) for r in bundle.report["stale"]] == [("f:reg-1", "ex:HeLa")]


def _check_strong_remove(bundle, out, first):
    assert [r["attrs"]["khg-bid"] for r in bundle.report["dropped_records"]] == ["b1", "b2", "b3"]
    assert bundle.report["dropped_nodes"] == ["ex:TP53"]  # orphaned by the removal of f:reg-1
    assert "f:reg-1" not in {e["edge"] for e in out["edges"]} and not _bids(out, "f:reg-1")


def _check_add_edge(bundle, out, first):
    assert first["unlabelled"] == [{"edge": "f:new", "node": "ex:HeLa"}, {"edge": "f:new", "node": "ex:TP53"}]
    assert _bids(out, "f:new") == ["b2", "b1"]  # context, regulator: the §4.2 order
    assert {"edge": "f:new", "attrs": {"relation": "regulates", "khg-status": "asserted"}} in out["edges"]


def _check_add_member(bundle, out, first):
    assert first["unlabelled"] == [{"edge": "f:reg-1", "node": "ex:Paris"}]
    assert _bids(out, "f:reg-1") == ["b1", "b4", "b2", "b3"]


def _check_subhypergraph(bundle, out, first):
    assert [r["attrs"]["khg-bid"] for r in bundle.report["dropped_records"]] == ["b1", "b2", "b3"]
    assert bundle.report["dropped_nodes"] == ["ex:TP53"] and not _bids(out, "f:reg-1")


def _check_relabelled(bundle, out, first):
    assert len(bundle.report["dropped_records"]) == 59  # every edge id was rewritten
    assert bundle.report["unlabelled"] and bundle.report["stale"] == []


def _check_clone(bundle, out, first):
    assert bundle.report["dropped_nodes"] == ["ex:Mazarin"]
    assert "ex:Mazarin" not in {n["node"] for n in out["nodes"]} and len(out["incidences"]) == 59


def _check_without_reg1(bundle, out, first):
    assert [r["attrs"]["khg-bid"] for r in bundle.report["dropped_records"]] == ["b1", "b2", "b3"]
    assert bundle.report["dropped_nodes"] == ["ex:HeLa", "ex:TP53"]


def _check_remove_incidence(bundle, out, first):
    assert [(r["edge"], r["node"], r["attrs"]["khg-bid"]) for r in bundle.report["stale"]] == \
        [("f:reg-1", "ex:HeLa", "b1")]


def _check_rename(bundle, out, first):
    assert bundle.report["moved"] == [{"edge": "f:reg-1", "bid": "b1", "from": "ex:HeLa", "to": "ex:HeLa-cells"}]
    assert bundle.report["moved_conflict"] == []
    assert bundle.report["dropped_nodes"] == ["ex:Mazarin"]  # HyperNetX's rename also loses the isolated node
    assert "ex:HeLa-cells" in {n["node"] for n in out["nodes"]}


def _check_add_incidence(bundle, out, first):
    assert first["unlabelled"] == [{"edge": "f:reg-1", "node": "ex:Paris", "direction": "tail"}]
    assert [i for i in out["incidences"] if i["node"] == "ex:Paris" and i["edge"] == "f:reg-1"] == [
        {"edge": "f:reg-1", "node": "ex:Paris", "direction": "tail", "attrs": {"role": "context", "khg-bid": "b4"}}]


def _check_restrict_nodes(bundle, out, first):
    assert [(r["edge"], r["attrs"]["khg-bid"]) for r in bundle.report["stale"]] == [("f:reg-1", "b1")]


def _check_collapse(bundle, out, first):
    assert bundle.report["stale"] and bundle.report["moved"]


def _check_sum(bundle, out, first):
    assert bundle.report["dropped_nodes"] == ["ex:Mazarin"] and len(out["incidences"]) == 59


CHECKS = {
    ("xgi", "remove_node('ex:HeLa') (weak: f:reg-1 survives)"): _check_weak_remove,
    ("xgi", "remove_node('ex:HeLa', strong=True) (f:reg-1 removed whole)"): _check_strong_remove,
    ("xgi", "add_edge + set_edge_attributes, then label"): _check_add_edge,
    ("xgi", "add_node_to_edge('f:reg-1', 'ex:Paris'), then label"): _check_add_member,
    ("xgi", "subhypergraph(all nodes but ex:HeLa) then derive"): _check_subhypergraph,
    ("xgi", "convert_labels_to_integers"): _check_relabelled,
    ("xgi", "dual()"): _check_relabelled,
    ("xgi", "cleanup() (relabels to integers by default)"): _check_relabelled,
    ("hnx", "clone() then derive (HyperNetX drops the isolated ex:Mazarin)"): _check_clone,
    ("hnx", "restrict_to_edges(all but f:reg-1) then derive"): _check_without_reg1,
    ("hnx", "remove_edges(['f:reg-1'])"): _check_without_reg1,
    ("hnx", "remove_incidences([('f:reg-1', 'ex:HeLa')])"): _check_remove_incidence,
    ("hnx", "rename(nodes={'ex:HeLa': 'ex:HeLa-cells'})"): _check_rename,
    ("hnx", "add_incidence('f:reg-1', 'ex:Paris'), then label"): _check_add_incidence,
    ("hnx", "restrict_to_nodes(all but ex:HeLa) then derive"): _check_restrict_nodes,
    ("hnx", "collapse_nodes() then derive"): _check_collapse,
    ("hnx", "sum(slice) then derive (the slice is a subset; the isolated node is lost)"): _check_sum,
}
