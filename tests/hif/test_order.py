"""W6: the §4.2 order recomputed from node attrs (``canonical_order``), and ``node_value`` (DESIGN §4.2, §5).

The loaders export profile files in this order whatever order a library returns, so it must be a function of the
records alone: shuffling a file and ordering it again gives the file back.
"""
from __future__ import annotations

import copy
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


def test_an_incidence_of_an_entity_the_file_does_not_declare_sorts_by_its_entity_value(c1, schema):
    """A container that is not complete may name an entity it does not hold. ``to_hif`` writes that incidence with
    the entity id as its node and no node record, in canonical binding order by the entity value; the recomputed
    order must agree (it read the value as null, which sorts first, so the loaders reordered an edit-free round
    trip)."""
    c = copy.deepcopy(c1)
    del c["header"]["complete"]
    c["records"] = [r for r in c["records"] if r.get("id") != "ex:metformin"]
    h = hif.to_hif(c, schema)
    assert "ex:metformin" not in {n["node"] for n in h["nodes"]}
    assert [(i["node"], i["attrs"]["khg-bid"]) for i in h["incidences"] if i["edge"] == "f:coadmin-1"] == [
        ("ex:insulin", "b1"), ("ex:metformin", "b2"), ("ex:hypoglycaemia", "b3")]
    assert hif.canonical_order(h) == h
    nodes = {n["node"]: n for n in h["nodes"]}
    inc = next(i for i in h["incidences"] if i["node"] == "ex:metformin")
    declared = {**nodes, "ex:metformin": {"node": "ex:metformin", "attrs": {"khg-kind": "entity"}}}
    assert hif.incidence_sort_key(inc, nodes) == hif.incidence_sort_key(inc, declared)


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
