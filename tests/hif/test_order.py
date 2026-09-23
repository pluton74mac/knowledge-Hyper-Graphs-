"""W6: the §4.2 order recomputed from node attrs (``canonical_order``), and ``node_value`` (DESIGN §4.2, §5).

The loaders export profile files in this order whatever order a library returns, so it must be a function of the
records alone: shuffling a file and ordering it again gives the file back.
"""
from __future__ import annotations

import random

import pytest

from khg_contracts import data, hif


@pytest.mark.parametrize("rel", ["fixture/fixture.hif.json", "fixture/fixture.directed-slice.hif.json",
                                 "sample/sample.khg.hif.json"])
def test_canonical_order_restores_a_shuffled_file(rel):
    doc = data.load_json(rel)
    assert hif.canonical_order(doc) == doc
    rng = random.Random(7)
    for _ in range(3):
        shuffled = data.load_json(rel)
        for key in ("nodes", "edges", "incidences"):
            rng.shuffle(shuffled[key])
        assert shuffled != doc
        assert hif.canonical_order(shuffled) == doc


def test_canonical_order_is_a_copy_and_keeps_other_keys():
    doc = data.load_json("fixture/fixture.hif.json")
    doc["incidences"].reverse()
    out = hif.canonical_order(doc)
    assert out is not doc and out["incidences"] != doc["incidences"]
    assert out["metadata"] == doc["metadata"] and out["network-type"] == doc["network-type"]
    assert hif.canonical_order({"incidences": []}) == {"incidences": []}


def test_node_sort_key_puts_entities_first():
    ids = ["_:lit:0a", "ex:b", "_:ref:f:x", "ex:a", "_:sv:0b"]
    assert sorted(ids, key=lambda i: hif.node_sort_key({"node": i})) == [
        "ex:a", "ex:b", "_:lit:0a", "_:ref:f:x", "_:sv:0b"]


def test_incidences_follow_the_canonical_binding_order():
    doc = data.load_json("fixture/fixture.hif.json")
    nodes = {n["node"]: n for n in doc["nodes"]}
    station = [i for i in doc["incidences"] if i["edge"] == "f:station-東京"]
    keys = [hif.incidence_sort_key(i, nodes) for i in station]
    assert keys == sorted(keys)
    names = [i for i in station if i["attrs"]["role"] == "name"]  # one role, ordered by the literal's value
    assert [nodes[i["node"]]["attrs"]["label"] for i in names] == ["Tokyo Station@en", "東京駅@ja"]


def test_node_value_reads_every_kind():
    doc = data.load_json("fixture/fixture.hif.json")
    nodes = {n["node"]: n for n in doc["nodes"]}
    assert hif.node_value(nodes["ex:TP53"]) == {"entity": "ex:TP53"}
    assert hif.node_value(nodes["_:ref:f:born-louis14-paris"]) == {"fact": "f:born-louis14-paris"}
    lit = next(n for n in doc["nodes"] if n["attrs"].get("label") == "TYO")
    assert hif.node_value(lit) == {"literal": {"datatype": "string", "value": "TYO"}}
    kinds = {n["attrs"]["khg-kind"]: hif.node_value(n) for n in doc["nodes"]
             if n["attrs"]["khg-kind"] in ("somevalue", "novalue", "unbound")}
    assert kinds == {"somevalue": {"special": "somevalue"}, "novalue": {"special": "novalue"},
                     "unbound": {"unbound": {"var": "who", "expect": {"entity_types": ["Person"]}}}}
    assert hif.node_value({"node": "x", "attrs": {"khg-kind": "hub"}}) is None
    assert hif.node_value({"node": "x"}) is None and hif.node_value("x") is None  # type: ignore[arg-type]
