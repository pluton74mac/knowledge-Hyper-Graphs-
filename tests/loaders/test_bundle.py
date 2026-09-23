"""W7: ``Bundle`` (DESIGN §5): ``records``, ``roles``, ``derive`` and ``label``; the C1 conveniences; the P5 call
sequence of §1.3; and F1, the libraries' own HIF functions are never called."""
from __future__ import annotations

import copy
from typing import Any

import pytest

from khg_contracts import hif, jsonio, loaders
from khg_contracts.errors import LoaderError
from khg_contracts.record import canonical_container

xgi = pytest.importorskip("xgi")
hypernetx = pytest.importorskip("hypernetx")

pytestmark = pytest.mark.libs

LOAD = {"xgi": loaders.load_xgi, "hnx": loaders.load_hnx}
EXPORT = {"xgi": loaders.export_xgi, "hnx": loaders.export_hnx}
LIBS = ("xgi", "hnx")


def _incidences(doc: dict[str, Any], edge: Any, node: Any = None) -> list[dict[str, Any]]:
    return [i for i in doc["incidences"] if i["edge"] == edge and (node is None or i["node"] == node)]


def _add(bundle: loaders.Bundle, edge: Any, node: Any) -> None:
    if bundle.lib == "xgi":
        bundle.graph.add_node_to_edge(edge, node)
    else:
        bundle.graph.add_incidence(edge, node)


def _code(call) -> tuple[str, ...]:
    with pytest.raises(LoaderError) as err:
        call()
    return err.value.codes


# ------------------------------------------------------------------------------------------------ records and roles


@pytest.mark.parametrize("lib", LIBS)
def test_records_are_the_full_incidence_records_in_record_order(full, lib):
    b = LOAD[lib](full)
    assert list(b.records("f:reg-1")) == _incidences(full, "f:reg-1")
    assert list(b.records("f:reg-1", "ex:TP53")) == _incidences(full, "f:reg-1", "ex:TP53")
    assert list(b.records("f:coadmin-1", "ex:insulin")) == [
        {"edge": "f:coadmin-1", "node": "ex:insulin", "direction": "tail", "weight": 0.25,
         "attrs": {"role": "agent", "khg-bid": "b1"}}]
    assert b.records("f:no-such-edge") == () and b.records("f:reg-1", "ex:Paris") == ()
    assert isinstance(b.records("f:reg-1"), tuple)


@pytest.mark.parametrize("lib", LIBS)
def test_records_are_copies(full, lib):
    b = LOAD[lib](full)
    b.records("f:reg-1")[0]["attrs"]["role"] = "changed"
    assert b.roles("f:reg-1", "ex:HeLa") == ["context"]
    assert EXPORT[lib](b) == full


@pytest.mark.parametrize("lib", LIBS)
def test_roles_of_a_node_with_two_roles_in_one_edge(full, directed_slice, lib):
    for doc in (full, directed_slice):
        b = LOAD[lib](doc)
        assert b.roles("f:reg-1", "ex:TP53") == ["regulator", "target"]
        assert b.roles("f:route-1", "ex:YYZ") == ["stop", "stop"]
    assert LOAD[lib](full).roles("f:loop-yyz", "ex:YYZ") == ["destination", "origin"]


def test_xgi_records_are_those_of_live_memberships(directed_slice):
    b = loaders.load_xgi(directed_slice)
    b.graph.remove_node_from_edge("f:reg-1", "ex:TP53", "out")  # TP53 stays the regulator (in), not the target
    assert b.roles("f:reg-1", "ex:TP53") == ["regulator"]
    assert [r["attrs"]["khg-bid"] for r in b.records("f:reg-1")] == ["b1", "b2"]


def test_hypernetx_records_follow_their_cell_through_a_rename(full):
    b = loaders.load_hnx(full)
    b.graph.rename(nodes={"ex:TP53": "ex:TP53-human"})
    assert b.roles("f:reg-1", "ex:TP53-human") == ["regulator", "target"]
    assert b.records("f:reg-1", "ex:TP53") == ()


@pytest.mark.parametrize("lib", LIBS)
def test_records_keep_integer_and_string_ids_apart(lib):
    doc = {"incidences": [{"edge": 1, "node": 1, "attrs": {"role": "int-in-int"}},
                          {"edge": 1, "node": "1", "attrs": {"role": "str-in-int"}},
                          {"edge": "1", "node": 1, "attrs": {"role": "int-in-str"}}]}
    b = LOAD[lib](doc, validate="none")
    assert b.roles(1, 1) == ["int-in-int"] and b.roles(1, "1") == ["str-in-int"] and b.roles("1", 1) == ["int-in-str"]
    assert b.roles("1", "1") == []


# ------------------------------------------------------------------------------------------------ derive


def test_derive_wraps_a_copy_with_the_context_and_its_own_labels(full):
    b = loaders.load_xgi(full)
    d = b.derive(b.graph.copy())
    assert d.lib == "xgi" and d.graph is not b.graph and d.report is None
    assert d.context.records is b.context.records and d.context.metadata == b.context.metadata
    d.graph.add_node_to_edge("f:reg-1", "ex:Paris")
    d.label("f:reg-1", "ex:Paris", role="context", bid="b4", direction="tail")
    assert len(d.context.labels) == 1 and b.context.labels == []  # labelling one bundle never changes the other
    assert loaders.export_xgi(b) == full
    assert [i["attrs"]["khg-bid"] for i in _incidences(loaders.export_xgi(d), "f:reg-1")] == ["b1", "b4", "b2", "b3"]


def test_derive_needs_an_object_of_the_bundles_library(full):
    bx, bh = loaders.load_xgi(full), loaders.load_hnx(full)
    with pytest.raises(TypeError, match="xgi bundle needs a xgi object"):
        bx.derive(bh.graph)
    with pytest.raises(TypeError, match="hnx bundle needs a hnx object"):
        bh.derive(bx.graph)
    with pytest.raises(ValueError, match="lib is one of"):
        loaders.Bundle(bx.graph, bx.context, "networkx")
    with pytest.raises(TypeError, match="export_hnx needs a HyperNetX bundle"):
        loaders.export_hnx(bx)
    with pytest.raises(TypeError, match="export_xgi needs an XGI bundle"):
        loaders.export_xgi(bh)


# ------------------------------------------------------------------------------------------------ label


@pytest.mark.parametrize("lib", LIBS)
def test_label_gives_a_new_membership_its_record(full, schema, lib):
    b = LOAD[lib](full)
    _add(b, "f:reg-1", "ex:Paris")
    b.label("f:reg-1", "ex:Paris", role="context", bid="b4", direction="tail", position=1,
            extensions={"ex:note": {"by": "curator:c"}})
    assert b.roles("f:reg-1", "ex:Paris") == ["context"]
    out = EXPORT[lib](b)
    assert _incidences(out, "f:reg-1", "ex:Paris") == [
        {"edge": "f:reg-1", "node": "ex:Paris", "direction": "tail",
         "attrs": {"role": "context", "khg-bid": "b4", "role-position": 1,
                   "khg-extensions": {"ex:note": {"by": "curator:c"}}}}]
    assert not any(b.report.values())
    reg = next(r for r in hif.from_hif(out, schema)["records"] if r.get("id") == "f:reg-1")
    assert {"bid": "b4", "role": "context", "value": {"entity": "ex:Paris"}, "position": 1,
            "extensions": {"ex:note": {"by": "curator:c"}}} in reg["bindings"]


def test_hypernetx_writes_a_new_cells_record_into_the_cell(full):
    b = loaders.load_hnx(full)
    b.graph.add_incidence("f:reg-1", "ex:Paris")
    b.label("f:reg-1", "ex:Paris", role="context", bid="b4", direction="tail", weight=0.3)
    cell = b.graph.get_cell_properties("f:reg-1", "ex:Paris")
    assert (cell["role"], cell["khg-bid"], cell["direction"], cell["weight"]) == ("context", "b4", "tail", 0.3)
    b.label("f:reg-1", "ex:Paris", role="regulator", bid="b5", direction="tail")  # a second record of the pair
    assert [r["attrs"]["role"] for r in b.graph.get_cell_properties("f:reg-1", "ex:Paris")[loaders.EXTRA]] == \
        ["regulator"]
    out = loaders.export_hnx(b)
    assert [(i["attrs"]["khg-bid"], i.get("weight")) for i in _incidences(out, "f:reg-1", "ex:Paris")] == \
        [("b4", 0.3), ("b5", None)]


def test_xgi_keeps_a_label_in_the_context(full):
    b = loaders.load_xgi(full)
    b.graph.add_node_to_edge("f:reg-1", "ex:Paris")
    b.label("f:reg-1", "ex:Paris", role="context", bid="b4", weight=0.3)
    assert b.context.labels == [{"edge": "f:reg-1", "node": "ex:Paris", "weight": 0.3,
                                 "attrs": {"role": "context", "khg-bid": "b4"}}]
    edge_attrs = next(e["attrs"] for e in full["edges"] if e["edge"] == "f:reg-1")
    assert b.graph.edges["f:reg-1"] == edge_attrs  # XGI cannot hold incidence records: nothing was written into it
    assert b.graph.nodes["ex:Paris"] == next(n["attrs"] for n in full["nodes"] if n["node"] == "ex:Paris")


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.parametrize("kwargs, code", [
    ({"role": ""}, "KHG-P005"),
    ({"role": "context"}, "KHG-P005"),  # a khg-hif file needs a bid
    ({"role": "context", "bid": "x4"}, "KHG-P005"),
    ({"role": "context", "bid": "b04"}, "KHG-P005"),
    ({"role": "context", "bid": "b4", "direction": "up"}, "KHG-H005"),
    ({"role": "context", "bid": "b4", "position": 0}, "KHG-R004"),
    ({"role": "context", "bid": "b4", "position": True}, "KHG-R004"),
    ({"role": "context", "bid": "b4", "weight": "heavy"}, "KHG-H009"),
    ({"role": "context", "bid": "b4", "extensions": ["x"]}, "KHG-H009"),
])
def test_label_refuses_a_record_that_is_not_one(full, lib, kwargs, code):
    b = LOAD[lib](full)
    _add(b, "f:reg-1", "ex:Paris")
    assert _code(lambda: b.label("f:reg-1", "ex:Paris", **kwargs)) == (code,)
    assert b.records("f:reg-1", "ex:Paris") == ()


@pytest.mark.parametrize("lib", LIBS)
def test_label_refuses_a_bid_a_live_record_of_the_edge_has(full, lib):
    b = LOAD[lib](full)
    _add(b, "f:reg-1", "ex:Paris")
    assert _code(lambda: b.label("f:reg-1", "ex:Paris", role="context", bid="b3")) == ("KHG-P016",)
    b.label("f:reg-1", "ex:Paris", role="context", bid="b4")  # a bid of another edge's records is fine: b4 is free
    assert b.roles("f:reg-1", "ex:Paris") == ["context"]


def test_a_bid_of_a_removed_membership_may_be_reused(full):
    b = loaders.load_xgi(full)
    b.graph.remove_node_from_edge("f:reg-1", "ex:HeLa")
    b.graph.add_node_to_edge("f:reg-1", "ex:Paris")
    b.label("f:reg-1", "ex:Paris", role="context", bid="b1", direction="tail")
    with pytest.raises(LoaderError):
        loaders.export_xgi(b)  # b1 of ex:HeLa is still a partial fact
    out = loaders.export_xgi(b, strict=False)
    assert [(i["node"], i["attrs"]["khg-bid"]) for i in _incidences(out, "f:reg-1")] == \
        [("ex:Paris", "b1"), ("ex:TP53", "b2"), ("ex:TP53", "b3")]


@pytest.mark.parametrize("lib", LIBS)
def test_label_needs_an_existing_membership(full, lib):
    b = LOAD[lib](full)
    assert _code(lambda: b.label("f:reg-1", "ex:Paris", role="context", bid="b4")) == ("KHG-P005",)
    assert _code(lambda: b.label("f:no-such-edge", "ex:Paris", role="context", bid="b1")) == ("KHG-P005",)


def test_a_directed_xgi_membership_is_named_by_its_direction(directed_slice):
    b = loaders.load_xgi(directed_slice)
    b.graph.add_node_to_edge("f:reg-1", "ex:Paris", "in")
    assert _code(lambda: b.label("f:reg-1", "ex:Paris", role="context", bid="b4")) == ("KHG-P010",)
    assert _code(lambda: b.label("f:reg-1", "ex:Paris", role="context", bid="b4", direction="head")) == ("KHG-P005",)
    b.label("f:reg-1", "ex:Paris", role="context", bid="b4", direction="tail")
    out = loaders.export_xgi(b)
    assert _incidences(out, "f:reg-1", "ex:Paris") == [
        {"edge": "f:reg-1", "node": "ex:Paris", "direction": "tail", "attrs": {"role": "context", "khg-bid": "b4"}}]


@pytest.mark.parametrize("lib", LIBS)
def test_files_without_the_profile_need_only_a_role(lib):
    doc = {"metadata": {"role-convention": "1.0.0"},
           "incidences": [{"edge": "e", "node": "a", "attrs": {"role": "r"}}]}
    b = LOAD[lib](doc, validate="convention")
    _add(b, "e", "b")
    b.label("e", "b", role="s")
    assert EXPORT[lib](b)["incidences"] == doc["incidences"] + [{"edge": "e", "node": "b", "attrs": {"role": "s"}}]


# ------------------------------------------------------------------------------------------------ C1 conveniences


def test_khg_to_xgi_and_back(c1, schema, slice_relations):
    b = loaders.khg_to_xgi(c1, schema)
    assert type(b.graph) is xgi.Hypergraph
    assert jsonio.canonical(loaders.xgi_to_khg(b, schema)) == jsonio.canonical(canonical_container(c1))
    s = loaders.khg_to_xgi(c1, schema, relations=slice_relations)
    assert type(s.graph) is xgi.DiHypergraph
    assert loaders.xgi_to_khg(s, schema)["header"]["complete"] is False


def test_khg_to_hnx_and_back(c1, schema):
    b = loaders.khg_to_hnx(c1, schema, literal_nodes="per_binding")
    assert isinstance(b.graph, hypernetx.Hypergraph) and b.context.metadata["khg-literal-nodes"] == "per_binding"
    assert jsonio.canonical(loaders.hnx_to_khg(b, schema)) == jsonio.canonical(canonical_container(c1))


def test_the_conveniences_pass_strict_through(c1, schema):
    b = loaders.khg_to_hnx(c1, schema)
    b.graph.remove_incidences([("f:reg-1", "ex:HeLa")])
    assert _code(lambda: loaders.hnx_to_khg(b, schema)) == ("KHG-P005",)
    back = loaders.hnx_to_khg(b, schema, strict=False)
    reg = next(r for r in back["records"] if r.get("id") == "f:reg-1")
    assert [x["bid"] for x in reg["bindings"]] == ["b2", "b3"]


def test_the_p5_call_sequence(c1, schema):
    # §1.3, P5: draw a directed slice
    h = hif.to_hif(c1, schema, relations=["regulates", "position_held"], literal_nodes="per_binding")
    b = loaders.load_xgi(h)  # a DiHypergraph when every incidence has a direction
    assert type(b.graph) is xgi.DiHypergraph
    assert b.roles("f:reg-1", "ex:TP53") == ["regulator", "target"]
    assert all(n.startswith("_:litb:") for n in b.graph.nodes if str(n).startswith("_:lit"))


# ------------------------------------------------------------------------------------------------ F1


def test_the_libraries_own_hif_functions_are_never_called(monkeypatch, full, directed_slice):
    import requests

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a library HIF function or the network was used")

    targets = [(xgi, name) for name in ("read_hif", "write_hif", "from_hif_dict", "to_hif_dict",
                                        "read_hif_collection", "write_hif_collection")]
    targets += [(xgi.readwrite.hif, "read_hif"), (xgi.readwrite.hif, "write_hif"),
                (xgi.convert.hif_dict, "from_hif_dict"), (xgi.convert.hif_dict, "to_hif_dict"),
                (hypernetx, "from_hif"), (hypernetx, "to_hif"), (hypernetx.hif, "from_hif"),
                (hypernetx.hif, "to_hif"), (requests, "get")]
    for module, name in targets:
        monkeypatch.setattr(module, name, forbidden)
    for doc in (full, directed_slice):
        h1 = loaders.export_xgi(loaders.load_xgi(copy.deepcopy(doc)))
        h2 = loaders.export_hnx(loaders.load_hnx(h1))
        assert h1 == h2 == doc
