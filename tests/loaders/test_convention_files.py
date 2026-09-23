"""W7: the five role-convention files, which carry the convention but not the profile (DESIGN §4.4, §5).

The loaders accept them with ``validate="convention"`` and round-trip them through XGI and HyperNetX in source order,
repeated pairs included; ``from_hif`` refuses them (P001) in v1.
"""
from __future__ import annotations

import pytest

from khg_contracts import data, hif, jsonio, loaders
from khg_contracts.errors import ValidationError

xgi = pytest.importorskip("xgi")
hypernetx = pytest.importorskip("hypernetx")

pytestmark = pytest.mark.libs


def test_both_loaders_round_trip_them_in_source_order(convention_file):
    name, doc = convention_file
    bx = loaders.load_xgi(doc, validate="convention")
    ox = loaders.export_xgi(bx)
    bh = loaders.load_hnx(ox, validate="convention")
    oh = loaders.export_hnx(bh)
    assert ox["incidences"] == doc["incidences"] == oh["incidences"]
    assert jsonio.canonical(ox) == jsonio.canonical(doc) == jsonio.canonical(oh)
    assert not any(bx.report.values()) and not any(bh.report.values())
    assert not bx.context.profile and bx.context.order[0][1] == ("#", 1)
    assert type(bx.graph) is (xgi.DiHypergraph if doc["network-type"] == "directed" else xgi.Hypergraph)


def test_a_node_in_the_tail_and_the_head_of_one_edge():
    doc = data.load_json("role-convention/tail-head.hif.json")
    bx = loaders.load_xgi(doc, validate="convention")
    assert bx.graph.edges.dimembers("reg-1") == ({"TP53", "HeLa"}, {"TP53"})
    bh = loaders.load_hnx(doc, validate="convention")
    cell = bh.graph.get_cell_properties("reg-1", "TP53")
    assert (cell["role"], cell["direction"]) == ("regulator", "tail")
    assert cell[loaders.EXTRA] == [{"edge": "reg-1", "node": "TP53", "direction": "head", "attrs": {"role": "target"}}]
    assert bx.roles("reg-1", "TP53") == bh.roles("reg-1", "TP53") == ["regulator", "target"]


@pytest.mark.parametrize("name, edge, node, roles", [
    ("two-roles", "sale-2", "alice", ["buyer", "payer"]),
    ("ordered", "route-1", "YYZ", ["stop", "stop"]),
    ("undirected", "marriage-1", "maria", ["spouse"]),
    ("basic", "sale-1", "book-7", ["item"]),
])
def test_roles_in_both_libraries(name, edge, node, roles):
    doc = data.load_json(f"role-convention/{name}.hif.json")
    for load in (loaders.load_xgi, loaders.load_hnx):
        assert load(doc, validate="convention").roles(edge, node) == roles


def test_from_hif_refuses_them(convention_file, schema):
    _, doc = convention_file
    with pytest.raises(ValidationError) as err:
        hif.from_hif(doc, schema)
    assert err.value.codes[0] == "KHG-P001"
