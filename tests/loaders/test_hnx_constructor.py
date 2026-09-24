"""W7: the pinned HyperNetX constructor call (DESIGN §5; critique GL-13).

``load_hnx`` calls ``hypernetx.Hypergraph(incidences_df, edge_col="edge", node_col="node", cell_weight_col="weight",
misc_cell_properties_col="attrs", node_properties=nodes_df, edge_properties=edges_df, misc_properties_col="attrs")``.
HyperNetX 2.4.3 silently ignores the per-kind ``misc_node_properties_col`` and ``misc_edge_properties_col``: with them
the attrs land in a plain ``attrs`` column and ``misc_properties`` stays empty, exactly as with no keyword at all. The
HyperNetX issue lists this (§12.4); a HyperNetX upgrade that changes it fails the last test here.
"""
from __future__ import annotations

from typing import Any

import pytest

from khg_contracts import loaders

hypernetx = pytest.importorskip("hypernetx")
pandas = pytest.importorskip("pandas")

pytestmark = pytest.mark.libs

PINNED = {"edge_col": "edge", "node_col": "node", "cell_weight_col": "weight", "misc_cell_properties_col": "attrs",
          "misc_properties_col": "attrs"}


@pytest.fixture()
def calls(monkeypatch) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
    """Every ``hypernetx.Hypergraph`` call, recorded and passed through."""
    seen: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    original = hypernetx.Hypergraph

    def spy(*args: Any, **kwargs: Any) -> Any:
        seen.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(hypernetx, "Hypergraph", spy)
    return seen


def test_the_loader_makes_exactly_the_pinned_call(calls, full):
    b = loaders.load_hnx(full)
    assert isinstance(b.graph, hypernetx.classes.hypergraph.Hypergraph)
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert len(args) == 1 and list(args[0].columns) == ["edge", "node", "weight", "direction", "attrs"]
    assert set(kwargs) == set(PINNED) | {"node_properties", "edge_properties"}
    assert {k: kwargs[k] for k in PINNED} == PINNED == loaders.HNX_KEYWORDS
    assert "misc_node_properties_col" not in kwargs and "misc_edge_properties_col" not in kwargs
    assert list(kwargs["node_properties"].columns) == ["node", "weight", "attrs"]
    assert list(kwargs["edge_properties"].columns) == ["edge", "weight", "attrs"]
    assert len(args[0]) == 56 and len(kwargs["node_properties"]) == 46 and len(kwargs["edge_properties"]) == 18


def test_a_file_without_declarations_passes_no_property_frames(calls):
    loaders.load_hnx({"incidences": [{"edge": "e", "node": "n"}]}, validate="none")
    _, kwargs = calls[0]
    assert kwargs["node_properties"] is None and kwargs["edge_properties"] is None


def _frames() -> tuple[Any, Any, Any]:
    cells = pandas.DataFrame([{"edge": "e1", "node": "a", "weight": 1, "attrs": {"role": "r1"}}],
                             columns=["edge", "node", "weight", "attrs"])
    nodes = pandas.DataFrame([{"node": "a", "weight": 3, "attrs": {"label": "A"}}], columns=["node", "weight", "attrs"])
    edges = pandas.DataFrame([{"edge": "e1", "weight": 0.5, "attrs": {"relation": "r"}}],
                             columns=["edge", "weight", "attrs"])
    return cells, nodes, edges


def _stores(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    cells, nodes, edges = _frames()
    h = hypernetx.Hypergraph(cells, edge_col="edge", node_col="node", cell_weight_col="weight",
                             misc_cell_properties_col="attrs", node_properties=nodes, edge_properties=edges, **kwargs)
    return (h.nodes.property_store.properties.to_dict(orient="index")["a"],
            h.edges.property_store.properties.to_dict(orient="index")["e1"])


def test_misc_properties_col_puts_node_and_edge_attrs_into_misc_properties():
    node, edge = _stores(misc_properties_col="attrs")
    assert node == {"weight": 3, "misc_properties": {"label": "A"}}
    assert edge == {"weight": 0.5, "misc_properties": {"relation": "r"}}


def test_hypernetx_2_4_3_silently_ignores_the_per_kind_misc_keywords():
    ignored = _stores(misc_node_properties_col="attrs", misc_edge_properties_col="attrs")
    assert ignored == _stores()  # exactly as with no keyword at all
    node, edge = ignored
    assert node["misc_properties"] == {} and node["attrs"] == {"label": "A"}
    assert edge["misc_properties"] == {} and edge["attrs"] == {"relation": "r"}
    assert hypernetx.__version__ == "2.4.3"
