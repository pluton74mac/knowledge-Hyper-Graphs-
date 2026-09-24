"""P5's call sequence (DESIGN §1.3): draw a directed slice.

``container`` is the packaged gate fixture. The slice of ``regulates`` and ``position_held`` has a direction on every
incidence (§4.6), so ``load_xgi`` builds an ``xgi.DiHypergraph``: tail maps to ``"in"`` and head to ``"out"`` (§5).
TP53 regulates itself in ``f:reg-1`` and keeps both roles. Literal nodes are per binding, so the two bindings that
hold the date of the 1643 handover are two nodes of one drawing, each with its own label.
"""
from __future__ import annotations

import pytest

from khg_contracts import hif, loaders

xgi = pytest.importorskip("xgi")

pytestmark = pytest.mark.libs


def test_p5_sequence(S, fixture_doc):
    container = fixture_doc

    # >>> DESIGN §1.3
    # P5: draw a directed slice
    h = hif.to_hif(container, S, relations=["regulates", "position_held"], literal_nodes="per_binding")
    b = loaders.load_xgi(h)                                     # a DiHypergraph when every incidence has a direction
    b.roles("f:reg-1", "ex:TP53")                               # ['regulator', 'target']
    # <<< DESIGN §1.3

    # a closed, directed slice (§4.6)
    assert h["network-type"] == "directed"
    meta = h["metadata"]
    assert meta["khg-slice"] == {"relations": ["position_held", "regulates"]} and meta["khg-complete"] is False
    assert meta["khg-literal-nodes"] == "per_binding"
    assert [e["edge"] for e in h["edges"]] == ["f:king-13", "f:king-14", "f:reg-1", "g:who-1774"]
    assert all("direction" in i for i in h["incidences"]) and len(h["incidences"]) == 15
    # the library object and the roles
    assert type(b.graph) is xgi.DiHypergraph
    assert b.roles("f:reg-1", "ex:TP53") == ["regulator", "target"]
    assert b.graph.edges.dimembers("f:reg-1") == ({"ex:HeLa", "ex:TP53"}, {"ex:TP53"})  # ("in", "out")
    assert [r["attrs"]["khg-bid"] for r in b.records("f:reg-1", "ex:TP53")] == ["b2", "b3"]
    assert b.roles("f:king-14", "ex:LouisXIII") == ["replaces"]
    # per-binding literal nodes: the end of f:king-13 and the start of f:king-14 are one date and two nodes
    node_of = {(i["edge"], i["attrs"]["role"]): i["node"] for i in h["incidences"]}
    end13, start14 = node_of[("f:king-13", "end_time")], node_of[("f:king-14", "start_time")]
    assert end13 != start14 and end13.startswith("_:litb:") and start14.startswith("_:litb:")
    labels = b.graph.nodes.attrs("label").asdict()
    assert labels[end13] == labels[start14] == "+1643-05-14T00:00:00Z/11"
    # labels travel as node attrs, so a drawing needs no second source
    assert labels["ex:TP53"] == "TP53" and labels["ex:KingOfFrance"] == "King of France"
    assert b.graph.edges.attrs["f:reg-1"]["relation"] == "regulates"
