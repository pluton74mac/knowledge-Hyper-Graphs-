"""W7: export reconciles the library object with the context (DESIGN §5; critique GL-05, GL-08, GL-09,
LOADER-STRICT): weights, node and edge records, attrs from the library, the strict rule, ``strict=False``, and the
order of profile and other files, independent of ``PYTHONHASHSEED``."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import hif, jsonio, loaders
from khg_contracts.errors import LoaderError
from khg_contracts.loaders.reconcile import reconcile_weight
from khg_contracts.validate import validate_hif

xgi = pytest.importorskip("xgi")
hypernetx = pytest.importorskip("hypernetx")

pytestmark = pytest.mark.libs

LOAD = {"xgi": loaders.load_xgi, "hnx": loaders.load_hnx}
EXPORT = {"xgi": loaders.export_xgi, "hnx": loaders.export_hnx}
LIBS = ("xgi", "hnx")
C12 = Path(__file__).resolve().parent / "r03-cases" / "c12-mixed-int-str-ids.hif.json"


def _incidences(doc: dict[str, Any], edge: Any) -> list[dict[str, Any]]:
    return [i for i in doc["incidences"] if i["edge"] == edge]


def _item(doc: dict[str, Any], key: str, i: Any) -> dict[str, Any]:
    return next(x for x in doc[key] if x[key[:-1]] == i)


def _strict_refusal(bundle: loaders.Bundle) -> dict[str, Any]:
    with pytest.raises(LoaderError) as err:
        EXPORT[bundle.lib](bundle)
    assert err.value.codes == ("KHG-P005",)
    assert err.value.info["report"] is bundle.report
    return err.value.info["report"]


def _errors(doc: dict[str, Any], schema: Any) -> list[tuple[str, str]]:
    return [(f["code"], f["path"]) for f in validate_hif(doc, schema=schema)["findings"] if f["severity"] == "error"]


# ------------------------------------------------------------------------------------------------ weights


@pytest.mark.parametrize("library, loaded, want", [
    (2.0, 2, 2), (0.75, 0.5, 0.75), (None, 3, 3), (float("nan"), 3, 3), (3.0, 2, 3), (1.0, None, 1.0),
    (0.5, 0.5, 0.5), (4, 3, 4),
])
def test_reconcile_weight_keeps_the_loaded_value_unless_the_library_differs(library, loaded, want):
    got = reconcile_weight(library, loaded)
    assert got == want and type(got) is type(want)


def test_reconcile_weight_reads_numpy_scalars():
    numpy = pytest.importorskip("numpy")
    got = reconcile_weight(numpy.float64(2.0), 2)
    assert got == 2 and type(got) is int
    assert type(reconcile_weight(numpy.float64(0.25), None)) is float


def test_hypernetx_holds_floats_and_the_export_writes_the_loaded_json_number_types(full):
    b = loaders.load_hnx(full)
    assert b.graph.edges.property_store.properties.loc["f:route-1", "weight"] == 2.0
    out = loaders.export_hnx(b)
    route = _item(out, "edges", "f:route-1")["weight"]
    assert route == 2 and type(route) is int
    assert type(_item(out, "nodes", "ex:TP53")["weight"]) is int


def test_native_hypernetx_weight_edits_are_exported(full):
    b = loaders.load_hnx(full)
    edges, nodes, cells = (b.graph.edges.property_store, b.graph.nodes.property_store,
                           b.graph.incidences.property_store)
    edges.set_property("f:reg-1", "weight", 0.75)
    edges.set_property("f:route-1", "weight", 2.0)  # numerically the loaded value: stays the integer 2
    nodes.set_property("ex:TP53", "weight", 4)
    nodes.set_property("ex:Paris", "weight", 1)  # the default: nothing to write
    cells.set_property(("f:coadmin-1", "ex:insulin"), "weight", 0.5)
    cells.set_property(("f:reg-1", "ex:HeLa"), "weight", 0.125)
    out = loaders.export_hnx(b)
    assert {e["edge"]: e["weight"] for e in out["edges"] if "weight" in e} == {"f:reg-1": 0.75, "f:route-1": 2}
    assert {n["node"]: n["weight"] for n in out["nodes"] if "weight" in n} == {"ex:TP53": 4}
    weighted = {(i["edge"], i["node"]): i["weight"] for i in out["incidences"] if "weight" in i}
    assert weighted == {("f:coadmin-1", "ex:insulin"): 0.5, ("f:reg-1", "ex:HeLa"): 0.125}
    assert not any(b.report.values())


def test_xgi_weights_come_from_the_context(full):
    b = loaders.load_xgi(full)
    out = loaders.export_xgi(b)
    assert _item(out, "nodes", "ex:TP53")["weight"] == 3 and _item(out, "edges", "f:reg-1")["weight"] == 0.5
    assert [i["weight"] for i in out["incidences"] if "weight" in i] == [0.25]


# ------------------------------------------------------------------------------------------------ nodes and edges


@pytest.mark.parametrize("lib", LIBS)
def test_the_loaded_isolated_node_is_exported(full, lib):
    out = EXPORT[lib](LOAD[lib](full))
    assert _item(out, "nodes", "ex:Mazarin") == _item(full, "nodes", "ex:Mazarin")
    assert not any(i["node"] == "ex:Mazarin" for i in out["incidences"])


def test_nodes_left_without_incidences_are_dropped_and_reported_derived_nodes_included(full, schema):
    b = loaders.load_xgi(full)
    b.graph.remove_edge("f:station-東京")
    out = loaders.export_xgi(b)
    dropped_bids = [r["attrs"]["khg-bid"] for r in b.report["dropped_records"]]
    assert dropped_bids == [f"b{k}" for k in (7, 4, 5, 8, 9, 3, 2, 6, 1)]  # source order
    dropped = b.report["dropped_nodes"]
    assert dropped[0] == "ex:東京駅" and len(dropped) == 9
    assert all(n.startswith("_:lit:") for n in dropped[1:])  # the station's eight literal nodes
    assert not {n["node"] for n in out["nodes"]} & set(dropped)
    assert b.report["stale"] == [] and b.report["unlabelled"] == []
    back = hif.from_hif(out, schema)  # still a complete, valid file: the fact was removed whole
    assert not any(r.get("id") in ("f:station-東京", "ex:東京駅") for r in back["records"])


def test_a_loaded_empty_edge_that_no_longer_exists_is_reported():
    doc = {"network-type": "undirected", "edges": [{"edge": "e1"}, {"edge": "empty", "attrs": {"k": 1}}],
           "incidences": [{"edge": "e1", "node": "a", "attrs": {"role": "r"}}]}
    b = loaders.load_xgi(doc, validate="none")
    assert loaders.export_xgi(b) == doc
    b.graph.remove_edge("empty")
    out = loaders.export_xgi(b)
    assert b.report["dropped_edges"] == ["empty"] and [e["edge"] for e in out["edges"]] == ["e1"]


def test_an_edge_left_without_incidences_is_dropped_and_reported(full):
    b = loaders.load_xgi(full)
    for n in ("ex:HeLa", "ex:TP53"):
        b.graph.remove_node_from_edge("f:reg-1", n, remove_empty=False)
    assert "f:reg-1" in b.graph.edges
    report = _strict_refusal(b)  # its three records are partial: the edge survives, empty
    assert [r["attrs"]["khg-bid"] for r in report["stale"]] == ["b1", "b2", "b3"]
    out = loaders.export_xgi(b, strict=False)
    assert b.report["dropped_edges"] == ["f:reg-1"] and b.report["dropped_nodes"] == ["ex:HeLa", "ex:TP53"]
    assert not any(e["edge"] == "f:reg-1" for e in out["edges"]) and not _incidences(out, "f:reg-1")


@pytest.mark.parametrize("lib", LIBS)
def test_node_and_edge_attrs_come_from_the_library(full, schema, lib):
    b = LOAD[lib](full)
    if lib == "xgi":
        b.graph.set_node_attributes({"ex:Paris": {"label": "Paris, France"}})
        b.graph.set_edge_attributes({"f:reg-1": {"khg-note": "checked twice"}})
    else:
        b.graph.nodes.property_store.set_property("ex:Paris", "label", "Paris, France")
        b.graph.edges.property_store.set_property("f:reg-1", "khg-note", "checked twice")
    out = EXPORT[lib](b)
    assert _item(out, "nodes", "ex:Paris")["attrs"]["label"] == "Paris, France"
    assert _item(out, "edges", "f:reg-1")["attrs"]["khg-note"] == "checked twice"
    back = {r["id"]: r for r in hif.from_hif(out, schema)["records"]}
    assert back["ex:Paris"]["label"] == "Paris, France" and back["f:reg-1"]["note"] == "checked twice"


def test_absent_and_empty_attrs_stay_apart():
    doc = {"nodes": [{"node": "a", "attrs": {}}, {"node": "b"}], "edges": [{"edge": "e", "attrs": {}}],
           "incidences": [{"edge": "e", "node": "a", "attrs": {}}, {"edge": "e", "node": "b"}]}
    for lib in LIBS:
        b = LOAD[lib](doc, validate="none")
        out = EXPORT[lib](b)
        assert out == doc and jsonio.canonical(out) == jsonio.canonical(doc)
        assert set(out) == {"nodes", "edges", "incidences"}  # no network-type or metadata was invented


# ------------------------------------------------------------------------------------------------ network-type

#: The fixture's only facts with incidences that have no direction (the loop's and the marriage's seven records).
UNDIRECTED_FACTS = ("f:loop-yyz", "f:married-curie")


def _remove_edges(bundle: loaders.Bundle, edges: tuple[str, ...]) -> None:
    if bundle.lib == "xgi":
        for e in edges:
            bundle.graph.remove_edge(e)
    else:
        bundle.graph.remove_edges(list(edges))


@pytest.mark.parametrize("lib", LIBS)
def test_a_profile_file_left_with_directed_records_only_exports_as_directed(full, schema, lib):
    """§4.2 and P011: network-type is directed iff every incidence has a direction. Removing the facts without a
    direction (a supported native edit) leaves only directed records, so the export is a directed file that the
    profile, the loaders and ``from_hif`` accept (it was written ``undirected`` and refused with P011)."""
    assert {i["edge"] for i in full["incidences"] if "direction" not in i} == set(UNDIRECTED_FACTS)
    b = LOAD[lib](full)
    _remove_edges(b, UNDIRECTED_FACTS)
    out = EXPORT[lib](b)
    assert len(b.report["dropped_records"]) == 7 and b.report["stale"] == b.report["unlabelled"] == []
    assert all("direction" in i for i in out["incidences"]) and out["network-type"] == "directed"
    assert _errors(out, schema) == []
    again = LOAD[lib](out)  # the loaders accept their own export: XGI now builds a DiHypergraph
    assert type(again.graph) is (xgi.DiHypergraph if lib == "xgi" else hypernetx.Hypergraph)
    assert EXPORT[lib](again) == out
    assert hif.to_hif(hif.from_hif(out, schema), schema) == out  # what to_hif writes for the decoded container


@pytest.mark.parametrize("lib", LIBS)
def test_a_restriction_to_the_directed_facts_goes_back_to_c1(c1, schema, lib):
    """The §5 table's restrictions (``restrict_to_edges``, ``subhypergraph``, then ``derive``) through the C1
    conveniences: the removals are reported and ``*_to_khg`` returns the container of the remaining facts."""
    keep = [r["id"] for r in c1["records"] if r["kind"] == "hyperedge" and r["id"] not in UNDIRECTED_FACTS]
    if lib == "xgi":
        b = loaders.khg_to_xgi(c1, schema)
        d = b.derive(xgi.subhypergraph(b.graph, edges=keep))
        back = loaders.xgi_to_khg(d, schema)
    else:
        b = loaders.khg_to_hnx(c1, schema)
        d = b.derive(b.graph.restrict_to_edges(keep))
        back = loaders.hnx_to_khg(d, schema)
    assert len(d.report["dropped_records"]) == 7
    facts = {r["id"] for r in back["records"] if r["kind"] == "hyperedge"}
    assert facts == set(keep) and not facts & set(UNDIRECTED_FACTS)


def test_a_directed_profile_file_that_loses_a_direction_no_longer_exports_as_directed(directed_slice, schema):
    """The mirror case: a HyperNetX cell's direction removed natively. The export follows the library and the
    direction rule (``undirected``; it was ``directed`` and refused with P010); the usage gives the direction back
    on import, so the decoded container is the slice's."""
    b = loaders.load_hnx(directed_slice)
    b.graph.incidences.property_store.set_property(("f:reg-1", "ex:HeLa"), "direction", None)
    out = loaders.export_hnx(b)
    assert out["network-type"] == "undirected" and not any(b.report.values())
    assert _incidences(out, "f:reg-1")[0] == {"edge": "f:reg-1", "node": "ex:HeLa",
                                              "attrs": {"role": "context", "khg-bid": "b1"}}
    assert _errors(out, schema) == []
    assert jsonio.canonical(hif.from_hif(out, schema)) == jsonio.canonical(hif.from_hif(directed_slice, schema))


@pytest.mark.parametrize("lib", LIBS)
def test_the_loaded_network_type_stays_outside_the_direction_rule(full, lib):
    """Files without the profile keep their network-type (HIF allows native directions in any network type), and
    so does a profile file exported without any record, where both values pass."""
    doc = {"network-type": "undirected", "metadata": {"role-convention": "1.0.0"},
           "incidences": [{"edge": "e", "node": "a", "direction": "tail", "attrs": {"role": "r"}},
                          {"edge": "e", "node": "b", "direction": "head", "attrs": {"role": "s"}}]}
    assert EXPORT[lib](LOAD[lib](doc, validate="convention")) == doc
    b = LOAD[lib](full)
    _remove_edges(b, tuple(e["edge"] for e in full["edges"]))
    out = EXPORT[lib](b)
    assert out["incidences"] == [] and out["network-type"] == "undirected"


# ------------------------------------------------------------------------------------------------ the strict rule


@pytest.mark.parametrize("lib", LIBS)
def test_an_unlabelled_membership_raises_and_is_never_exported_bare(full, lib):
    b = LOAD[lib](full)
    if lib == "xgi":
        b.graph.add_node_to_edge("f:reg-1", "ex:Paris")
    else:
        b.graph.add_incidence("f:reg-1", "ex:Paris")
    report = _strict_refusal(b)
    assert report["unlabelled"] == [{"edge": "f:reg-1", "node": "ex:Paris"}]
    assert report["stale"] == [] and report["moved_conflict"] == []
    out = EXPORT[lib](b, strict=False)
    assert b.report["unlabelled"] == [{"edge": "f:reg-1", "node": "ex:Paris"}]
    assert out == full  # dropped: nothing bare was written


@pytest.mark.parametrize("lib", LIBS)
def test_a_partial_fact_raises_and_strict_false_drops_and_reports_it(full, lib):
    b = LOAD[lib](full)
    if lib == "xgi":
        b.graph.remove_node_from_edge("f:reg-1", "ex:HeLa")
    else:
        b.graph.remove_incidences([("f:reg-1", "ex:HeLa")])
    report = _strict_refusal(b)
    assert [(r["edge"], r["node"], r["attrs"]["khg-bid"]) for r in report["stale"]] == [("f:reg-1", "ex:HeLa", "b1")]
    out = EXPORT[lib](b, strict=False)
    assert [i["attrs"]["khg-bid"] for i in _incidences(out, "f:reg-1")] == ["b2", "b3"]
    assert b.report["stale"] == report["stale"]


def test_a_move_whose_node_map_is_not_injective_raises(full):
    b = loaders.load_hnx(full)
    b.graph.rename(nodes={"ex:insulin": "ex:metformin"})  # two co-administered drugs collapse into one node
    report = _strict_refusal(b)
    move = {"edge": "f:coadmin-1", "bid": "b1", "from": "ex:insulin", "to": "ex:metformin"}
    assert report["moved"] == [move] and move in report["moved_conflict"]
    assert report["stale"] == []


def _by_edge(moves: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(moves, key=lambda m: (m["edge"], m["bid"]))


@pytest.mark.parametrize("names, conflicts", [
    ({"ex:Paris": "ex:Kraków"},
     [{"edge": "f:born-louis14-paris", "bid": "b2", "from": "ex:Paris", "to": "ex:Kraków"}]),
    ({"ex:HeLa": "ex:X", "ex:insulin": "ex:X"},
     [{"edge": "f:coadmin-1", "bid": "b1", "from": "ex:insulin", "to": "ex:X"},
      {"edge": "f:reg-1", "bid": "b1", "from": "ex:HeLa", "to": "ex:X"}]),
], ids=["onto-an-existing-node", "two-nodes-into-one"])
def test_a_collapse_across_edges_raises(full, names, conflicts):
    """§5: a moved record passes only when the old-to-new node map is injective; a collapse raises. Here the merged
    records sit in different edges, so no edge repeats a bid and only the node map catches the collapse (the test
    above is also caught by the repeated bid). ``strict=False`` exports the moved records as the library holds them
    and reports them (W7: only a record repeating a bid another cell carries is not exported)."""
    b = loaders.load_hnx(full)
    b.graph.rename(nodes=names)
    report = _strict_refusal(b)
    assert _by_edge(report["moved_conflict"]) == conflicts and _by_edge(report["moved"]) == conflicts
    assert report["stale"] == report["unlabelled"] == []
    out = loaders.export_hnx(b, strict=False)
    assert _by_edge(b.report["moved_conflict"]) == conflicts and _by_edge(b.report["moved"]) == conflicts
    for move in conflicts:
        assert [i["node"] for i in _incidences(out, move["edge"]) if i["attrs"]["khg-bid"] == move["bid"]] == \
            [move["to"]]


def test_an_injective_rename_is_moved_not_raised(full):
    b = loaders.load_hnx(full)
    b.graph.rename(nodes={"ex:insulin": "ex:insulin-glargine"})
    out = loaders.export_hnx(b)
    assert b.report["moved"] == [{"edge": "f:coadmin-1", "bid": "b1", "from": "ex:insulin",
                                  "to": "ex:insulin-glargine"}]
    agent = [i for i in _incidences(out, "f:coadmin-1") if i["attrs"]["khg-bid"] == "b1"]
    assert agent == [{"edge": "f:coadmin-1", "node": "ex:insulin-glargine", "direction": "tail", "weight": 0.25,
                      "attrs": {"role": "agent", "khg-bid": "b1"}}]


@pytest.mark.parametrize("lib", LIBS)
def test_records_of_an_edge_removed_whole_are_reported_not_raised(full, lib):
    b = LOAD[lib](full)
    if lib == "xgi":
        b.graph.remove_edge("f:reg-1")
    else:
        b.graph.remove_edges(["f:reg-1"])
    out = EXPORT[lib](b)
    assert [r["attrs"]["khg-bid"] for r in b.report["dropped_records"]] == ["b1", "b2", "b3"]
    assert b.report["dropped_nodes"] == ["ex:HeLa", "ex:TP53"]
    assert b.report["stale"] == [] and not _incidences(out, "f:reg-1")
    assert not any(e["edge"] == "f:reg-1" for e in out["edges"])


@pytest.mark.parametrize("lib", LIBS)
def test_the_report_is_set_by_the_last_export(full, lib):
    b = LOAD[lib](full)
    assert b.report is None
    EXPORT[lib](b)
    assert b.report == loaders.report.new_report() and tuple(b.report) == loaders.REPORT_KEYS
    (b.graph.remove_node_from_edge if lib == "xgi" else lambda e, n: b.graph.remove_incidences([(e, n)]))(
        "f:reg-1", "ex:HeLa")
    with pytest.raises(LoaderError):
        EXPORT[lib](b)
    assert len(b.report["stale"]) == 1  # a refused export still leaves its report


# ------------------------------------------------------------------------------------------------ order


@pytest.mark.parametrize("lib", LIBS)
def test_profile_files_export_in_the_section_4_2_order_whatever_the_input_order(full, lib):
    shuffled = copy.deepcopy(full)
    for key in ("nodes", "edges", "incidences"):
        shuffled[key].reverse()
    out = EXPORT[lib](LOAD[lib](shuffled))
    assert out == full and jsonio.canonical(out) == jsonio.canonical(full)
    assert out == hif.canonical_order(shuffled)


@pytest.mark.parametrize("lib", LIBS)
def test_an_edit_free_round_trip_keeps_the_order_of_an_entity_the_file_does_not_declare(c1, schema, lib):
    """``to_hif`` of a container that is not complete and names an entity it does not hold (valid C1): the node has
    no record, and the recomputed §4.2 order must place its incidence as ``to_hif`` did (it came first)."""
    c = copy.deepcopy(c1)
    del c["header"]["complete"]
    c["records"] = [r for r in c["records"] if r.get("id") != "ex:metformin"]
    h = hif.to_hif(c, schema)
    b = LOAD[lib](h)
    assert EXPORT[lib](b) == h and not any(b.report.values())


@pytest.mark.parametrize("lib", LIBS)
def test_other_files_keep_the_source_order_of_their_records(lib):
    doc = jsonio.load(C12)
    for d in (doc, {**doc, "incidences": list(reversed(doc["incidences"]))}):
        out = EXPORT[lib](LOAD[lib](d, validate="none"))
        assert out == d and [type(i["edge"]).__name__ + type(i["node"]).__name__ for i in out["incidences"]] == \
            [type(i["edge"]).__name__ + type(i["node"]).__name__ for i in d["incidences"]]


@pytest.mark.parametrize("lib", LIBS)
def test_new_records_follow_the_loaded_ones_sorted_by_a_typed_key(lib):
    doc = {"network-type": "undirected", "metadata": {"role-convention": "1.0.0"},
           "incidences": [{"edge": "e", "node": "z", "attrs": {"role": "r"}},
                          {"edge": 2, "node": 10, "attrs": {"role": "r"}}]}
    b = LOAD[lib](doc, validate="convention")
    for e, n in (("e", "b"), (2, 9), ("e", 1)):
        if lib == "xgi":
            b.graph.add_node_to_edge(e, n)
        else:
            b.graph.add_incidence(e, n)
        b.label(e, n, role="new")
    out = EXPORT[lib](b)
    assert [(i["edge"], i["node"]) for i in out["incidences"]] == [("e", "z"), (2, 10), (2, 9), ("e", 1), ("e", "b")]
    assert out["incidences"][2]["attrs"] == {"role": "new"}


def test_the_export_order_never_depends_on_pythonhashseed():
    code = (
        "import hashlib, json, sys, warnings\n"
        "warnings.filterwarnings('ignore')\n"
        "from khg_contracts import jsonio, loaders\n"
        "doc = jsonio.load(sys.argv[1])\n"
        "hx = loaders.export_xgi(loaders.load_xgi(doc, validate='none'))\n"
        "hh = loaders.export_hnx(loaders.load_hnx(hx, validate='none'))\n"
        "b = loaders.load_xgi(doc, validate='none')\n"
        "b.graph.add_node_to_edge(1, 'y'); b.graph.add_node_to_edge('1', 'x2')\n"
        "loaders.export_xgi(b, strict=False)\n"
        "print(json.dumps({'xgi': jsonio.canonical(hx), 'hnx': jsonio.canonical(hh),\n"
        "                  'unlabelled': b.report['unlabelled']}))\n")
    outs = []
    for seed in ("0", "1", "2", "3"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, "-c", code, str(C12)], env=env, capture_output=True, text=True,
                           timeout=600)
        assert r.returncode == 0, r.stderr
        outs.append(json.loads(r.stdout))
    assert all(o == outs[0] for o in outs)
    source = jsonio.canonical(jsonio.load(C12))
    assert outs[0]["xgi"] == outs[0]["hnx"] == source
    assert outs[0]["unlabelled"] == [{"edge": 1, "node": "y"}, {"edge": "1", "node": "x2"}]
