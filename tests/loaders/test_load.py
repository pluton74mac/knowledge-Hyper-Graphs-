"""W7: loading (DESIGN §5): construction through public constructors, the context, the ``validate=`` modes and the
refusals of every mode (P007, P010, D001)."""
from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from khg_contracts import jsonio, loaders
from khg_contracts.errors import LoaderError, ValidationError
from khg_contracts.loaders._common import tkey

xgi = pytest.importorskip("xgi")
hypernetx = pytest.importorskip("hypernetx")

pytestmark = pytest.mark.libs

LOAD = {"xgi": loaders.load_xgi, "hnx": loaders.load_hnx}
EXPORT = {"xgi": loaders.export_xgi, "hnx": loaders.export_hnx}
LIBS = ("xgi", "hnx")
MODES = loaders.VALIDATE_MODES


def _memberships(doc: dict[str, Any]) -> dict[str, set[tuple[Any, Any]]]:
    out: dict[str, set[tuple[Any, Any]]] = {}
    for i in doc["incidences"]:
        out.setdefault(i["edge"], set()).add((i["node"], i.get("direction")))
    return out


def _refused(call, *codes: str) -> LoaderError:
    with pytest.raises(LoaderError) as err:
        call()
    assert isinstance(err.value, ValidationError)  # a refused input is also a ValidationError
    assert err.value.codes[:len(codes)] == codes
    assert all(f["code"] in err.value.codes for f in err.value.info["findings"] if f["severity"] == "error")
    return err.value


# ------------------------------------------------------------------------------------------------ XGI construction


def test_xgi_builds_a_hypergraph_whose_member_sets_are_the_hif_memberships(full):
    b = loaders.load_xgi(full)
    assert type(b.graph) is xgi.Hypergraph and b.lib == "xgi"
    assert b.graph.num_nodes == 46 and b.graph.num_edges == 18
    for e, pairs in _memberships(full).items():
        assert b.graph.edges.members(e) == {n for n, _ in pairs}
    assert b.graph.edges.members("f:loop-yyz") == {"ex:AirCanada", "ex:YYZ"}  # two records, one member


def test_xgi_builds_a_dihypergraph_with_tail_as_in_and_head_as_out(directed_slice):
    b = loaders.load_xgi(directed_slice)
    assert type(b.graph) is xgi.DiHypergraph
    assert b.graph.num_nodes == 42 and b.graph.num_edges == 16
    for e, pairs in _memberships(directed_slice).items():
        tail, head = {n for n, d in pairs if d == "tail"}, {n for n, d in pairs if d == "head"}
        assert b.graph.edges.dimembers(e) == (tail, head)
    assert b.graph.edges.dimembers("f:reg-1") == ({"ex:HeLa", "ex:TP53"}, {"ex:TP53"})


def test_xgi_holds_the_node_and_edge_attrs_and_the_isolated_node(full):
    b = loaders.load_xgi(full)
    assert all(b.graph.nodes[n["node"]] == n["attrs"] for n in full["nodes"])
    assert all(b.graph.edges[e["edge"]] == e["attrs"] for e in full["edges"])
    assert b.graph.nodes["ex:Mazarin"] == {"khg-kind": "entity", "label": "Jules Mazarin", "khg-types": ["Person"]}
    assert b.graph.degree("ex:Mazarin") == 0


@pytest.mark.parametrize("directed", [False, True])
def test_xgi_builds_empty_edges_and_isolated_nodes(directed):
    doc = {"network-type": "directed" if directed else "undirected",
           "nodes": [{"node": "a"}, {"node": "iso", "attrs": {"k": [1, {"deep": None}]}}],
           "edges": [{"edge": "e1", "attrs": {"members": 1, "idx": 2}}, {"edge": "empty"}],
           "incidences": [{"edge": "e1", "node": "a", "direction": "tail"}, {"edge": "e1", "node": "b",
                                                                              "direction": "head"}]}
    b = loaders.load_xgi(doc, validate="none")
    assert sorted(b.graph.nodes) == ["a", "b", "iso"] and list(b.graph.edges) == ["e1", "empty"]
    assert b.graph.nodes["iso"] == {"k": [1, {"deep": None}]}
    assert b.graph.edges["e1"] == {"members": 1, "idx": 2}  # attrs are never splatted into keyword arguments
    empty = b.graph.edges.dimembers("empty") if directed else b.graph.edges.members("empty")
    assert empty == ((set(), set()) if directed else set())
    assert jsonio.canonical(loaders.export_xgi(b)) == jsonio.canonical(doc)


def test_xgi_network_attributes_stay_empty(full):
    b = loaders.load_xgi(full)
    for key in full["metadata"]:
        with pytest.raises(xgi.exception.XGIError):
            b.graph[key]


# ------------------------------------------------------------------------------------------ HyperNetX construction


def test_hnx_cells_hold_the_first_record_and_the_rest_under_the_reserved_key(full):
    b = loaders.load_hnx(full)
    frame = b.graph.incidences.to_dataframe
    pairs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for i in full["incidences"]:
        pairs.setdefault((i["edge"], i["node"]), []).append(i)
    assert len(frame) == len(pairs) == 56  # 59 records, 3 repeated pairs
    for (e, n), row in frame.iterrows():
        recs = pairs[(e, n)]
        expected = dict(recs[0]["attrs"])
        if len(recs) > 1:
            expected[loaders.EXTRA] = recs[1:]
        assert row["misc_properties"] == expected
        assert row["weight"] == recs[0].get("weight", 1)
        assert row["direction"] == recs[0].get("direction")
    cell = b.graph.get_cell_properties("f:route-1", "ex:YYZ")
    assert (cell["role"], cell["khg-bid"], cell["role-position"]) == ("stop", "b2", 1)
    assert [r["attrs"]["role-position"] for r in cell[loaders.EXTRA]] == [3]
    assert b.graph.get_cell_properties("f:coadmin-1", "ex:insulin")["weight"] == 0.25


def test_hnx_property_stores_hold_node_and_edge_weights_attrs_and_the_isolated_node(full):
    b = loaders.load_hnx(full)
    nodes = b.graph.nodes.property_store.properties
    edges = b.graph.edges.property_store.properties
    assert len(nodes) == 46 and len(edges) == 18
    assert nodes.loc["ex:TP53", "weight"] == 3 and edges.loc["f:reg-1", "weight"] == 0.5
    assert edges.loc["f:route-1", "weight"] == 2
    assert nodes.loc["ex:Mazarin", "misc_properties"]["label"] == "Jules Mazarin"
    assert "ex:Mazarin" not in list(b.graph.nodes)  # views show incident nodes only; the store keeps it
    assert edges.loc["f:station-東京", "misc_properties"]["relation"] == "station_profile"


@pytest.mark.parametrize("mode", ["convention", "none"])
def test_hnx_refuses_a_file_that_uses_its_reserved_cell_key(mode):
    doc = {"metadata": {"role-convention": "1.0.0"},
           "incidences": [{"edge": "e", "node": "a", "attrs": {"role": "r", loaders.EXTRA: []}}]}
    err = _refused(lambda: loaders.load_hnx(doc, validate=mode), "KHG-P014")
    assert err.info["findings"][0]["path"] == f"/incidences/0/attrs/{loaders.EXTRA}"
    assert loaders.export_xgi(loaders.load_xgi(doc, validate=mode)) == doc  # XGI carries it as an ordinary attr


# ------------------------------------------------------------------------------------------------ the context


@pytest.mark.parametrize("lib", LIBS)
def test_the_context_holds_what_neither_library_holds(full, lib):
    ctx = LOAD[lib](full).context
    assert isinstance(ctx, loaders.Context)
    assert ctx.metadata == full["metadata"] and ctx.metadata is not full["metadata"]
    assert ctx.network_type == "undirected" and not ctx.directed and ctx.profile
    assert len(ctx.records) == len(ctx.order) == 59
    assert ctx.order[:2] == [(tkey("f:born-louis14-paris"), "b2"), (tkey("f:born-louis14-paris"), "b1")]
    assert ctx.records[(tkey("f:reg-1"), "b3")]["attrs"]["khg-extensions"] == \
        {"ex:curation": {"checked": True, "by": ["curator:a", "curator:b"]}}
    assert ctx.records[(tkey("f:coadmin-1"), "b1")]["weight"] == 0.25
    assert ctx.node_weight == {tkey("ex:TP53"): 3} and type(ctx.node_weight[tkey("ex:TP53")]) is int
    assert ctx.edge_weight == {tkey("f:reg-1"): 0.5, tkey("f:route-1"): 2}
    assert type(ctx.edge_weight[tkey("f:route-1")]) is int
    assert ctx.isolated_nodes == {tkey("ex:Mazarin")} and ctx.empty_edges == frozenset()
    assert ctx.node_ids == [n["node"] for n in full["nodes"]] and ctx.edge_ids == [e["edge"] for e in full["edges"]]
    assert ctx.node_attrs == {tkey(n["node"]) for n in full["nodes"]}
    assert ctx.top_keys == ("network-type", "metadata", "nodes", "edges", "incidences")
    assert ctx.labels == []


def test_files_without_the_profile_key_their_records_by_ordinal():
    doc = {"network-type": "undirected", "incidences": [
        {"edge": 1, "node": "x", "attrs": {"role": "a"}}, {"edge": "1", "node": 1, "attrs": {"role": "b"}},
        {"edge": 1, "node": "x", "attrs": {"role": "c"}}]}
    ctx = loaders.load_xgi(doc, validate="none").context
    assert not ctx.profile
    assert ctx.order == [(("int", 1), ("#", 1)), (("str", "1"), ("#", 1)), (("int", 1), ("#", 2))]
    assert ctx.records[(("int", 1), ("#", 2))]["attrs"] == {"role": "c"}
    assert ctx.metadata is None and ctx.top_keys == ("network-type", "incidences")


def test_a_declared_profile_with_malformed_bids_is_read_as_a_file_without_the_profile(full):
    full["incidences"][0]["attrs"]["khg-bid"] = "b0"
    ctx = loaders.load_xgi(full, validate="none").context
    assert not ctx.profile and ctx.order[0] == (tkey("f:born-louis14-paris"), ("#", 1))


@pytest.mark.parametrize("lib", LIBS)
def test_the_callers_document_is_never_changed(full, lib):
    before = copy.deepcopy(full)
    b = LOAD[lib](full)
    b.context.metadata["title"] = "changed"
    out = EXPORT[lib](b)
    out["incidences"][0]["attrs"]["role"] = "changed"
    assert full == before


# ------------------------------------------------------------------------------------------------ validate modes


def test_profile_mode_refuses_a_file_without_the_profile(convention_file):
    _, doc = convention_file
    for lib in LIBS:
        _refused(lambda lib=lib: LOAD[lib](doc), "KHG-P001")


@pytest.mark.parametrize("lib", LIBS)
def test_convention_and_none_modes_load_the_role_convention_files(convention_file, lib):
    name, doc = convention_file
    for mode in ("convention", "none"):
        b = LOAD[lib](doc, validate=mode)
        assert not b.context.profile
        assert b.roles(doc["incidences"][0]["edge"], doc["incidences"][0]["node"]) == \
            [i["attrs"]["role"] for i in doc["incidences"]
             if (i["edge"], i["node"]) == (doc["incidences"][0]["edge"], doc["incidences"][0]["node"])]


@pytest.mark.parametrize("lib", LIBS)
def test_convention_mode_runs_layers_h_and_r(convention_file, lib):
    _, doc = convention_file
    no_role = copy.deepcopy(doc)
    del no_role["incidences"][0]["attrs"]["role"]
    _refused(lambda: LOAD[lib](no_role, validate="convention"), "KHG-R001")
    assert LOAD[lib](no_role, validate="none").context.records  # "none" runs no layer
    undeclared = copy.deepcopy(doc)
    del undeclared["metadata"]["role-convention"]
    _refused(lambda: LOAD[lib](undeclared, validate="convention"), "KHG-R003")
    extra_key = copy.deepcopy(doc)
    extra_key["incidences"][0]["role"] = "misplaced"
    _refused(lambda: LOAD[lib](extra_key, validate="convention"), "KHG-H003")


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.parametrize("patch, code", [
    (lambda d: d["metadata"].update({"khg-profile": "khg-hif/9.0.0"}), "KHG-V001"),
    (lambda d: d["incidences"][0].update({"role": "misplaced"}), "KHG-H003"),
    (lambda d: d["incidences"][0]["attrs"].update({"role": ""}), "KHG-R001"),
    (lambda d: d["incidences"][0]["attrs"].pop("khg-bid"), "KHG-P005"),
    (lambda d: d["metadata"].pop("khg-document-id"), "KHG-P001"),
    (lambda d: d["nodes"][0].update({"weight": float("nan")}), "KHG-J004"),
])
def test_profile_mode_runs_layers_j_v_h_r_and_p(full, lib, patch, code):
    patch(full)
    _refused(lambda: LOAD[lib](full), code)


@pytest.mark.parametrize("lib", LIBS)
def test_none_mode_runs_no_layer(full, lib):
    del full["metadata"]["khg-document-id"]  # P001 in profile mode
    b = LOAD[lib](full, validate="none")
    assert b.context.profile  # the file still declares the profile, with a bid on every incidence
    assert EXPORT[lib](b) == full


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.parametrize("doc, code", [
    ({"nodes": []}, "KHG-H001"),
    ({"incidences": [], "extra": 1}, "KHG-H002"),
    ({"incidences": [{"edge": "e", "node": "n", "extra": 1}]}, "KHG-H003"),
    ({"incidences": [{"edge": "e", "node": "n", "attrs": []}]}, "KHG-H004"),
    ({"incidences": [{"edge": "e", "node": "n", "direction": "up"}]}, "KHG-H005"),
    ({"incidences": [{"edge": "e"}]}, "KHG-H006"),
    ({"incidences": [{"edge": True, "node": "n"}]}, "KHG-H007"),
    ({"network-type": "hyper", "incidences": []}, "KHG-H008"),
])
def test_none_mode_refuses_a_document_without_the_hif_structure(lib, doc, code):
    _refused(lambda: LOAD[lib](doc, validate="none"), code)


def test_an_unknown_mode_is_a_value_error(full):
    with pytest.raises(ValueError, match="validate must be one of"):
        loaders.load_xgi(full, validate="strict")


# ------------------------------------------------------------------------------------------------ refusals


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.parametrize("mode", MODES)
def test_every_mode_refuses_asc_files(full, lib, mode):
    full["network-type"] = "asc"
    err = _refused(lambda: LOAD[lib](full, validate=mode), "KHG-P007")
    assert err.info["findings"][0]["path"] == "/network-type"


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.parametrize("mode", MODES)
def test_every_mode_refuses_a_directed_file_with_an_incidence_without_direction(directed_slice, lib, mode):
    del directed_slice["incidences"][5]["direction"]
    err = _refused(lambda: LOAD[lib](directed_slice, validate=mode), "KHG-P010")
    assert [f["path"] for f in err.info["findings"] if f["code"] == "KHG-P010"] == ["/incidences/5"]


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("key", ["nodes", "edges"])
def test_every_mode_refuses_duplicate_declarations(full, lib, mode, key):
    full[key].append(copy.deepcopy(full[key][3]))
    err = _refused(lambda: LOAD[lib](full, validate=mode), "KHG-D001")
    idf = key[:-1]
    assert err.info["findings"][0]["path"] == f"/{key}/{len(full[key]) - 1}/{idf}"


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.parametrize("mode", MODES)
def test_undirected_files_may_omit_directions(full, lib, mode):
    assert sum("direction" not in i for i in full["incidences"]) == 7
    b = LOAD[lib](full, validate=mode)
    assert EXPORT[lib](b) == full


# ------------------------------------------------------------------------------------------------ inputs


@pytest.mark.parametrize("lib", LIBS)
def test_a_str_or_pathlike_is_a_path(tmp_path, full, lib):
    path = tmp_path / "fixture.hif.json"
    path.write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
    assert EXPORT[lib](LOAD[lib](path)) == full
    assert EXPORT[lib](LOAD[lib](str(path))) == full


@pytest.mark.parametrize("lib", LIBS)
def test_json_text_must_be_parsed_first(full, lib):
    text = json.dumps(full)
    with pytest.raises(OSError):
        LOAD[lib](text[:200])  # a str is always a path
    with pytest.raises(TypeError, match="jsonio.loads"):
        LOAD[lib](text.encode("utf-8"))
    assert EXPORT[lib](LOAD[lib](jsonio.loads(text))) == full


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.parametrize("text, code", [
    ('{"incidences": [{"edge": "e", "node": "n", "weight": NaN}]}', "KHG-J004"),
    ('{"incidences": [], "incidences": []}', "KHG-J003"),
    ('{"incidences": [{"edge": 9007199254740993, "node": "n"}]}', "KHG-J006"),
    ('[]', "KHG-J007"),
])
def test_a_path_is_read_under_the_layer_j_rules(tmp_path, lib, text, code):
    path = tmp_path / "bad.hif.json"
    path.write_text(text, encoding="utf-8")
    for mode in MODES:
        _refused(lambda mode=mode: LOAD[lib](path, validate=mode), code)
