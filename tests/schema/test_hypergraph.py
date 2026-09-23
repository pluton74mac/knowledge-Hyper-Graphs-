"""W2: the schema as a hypergraph (P6) and the GYO test on the three packaged schemas (DESIGN §3)."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from khg_contracts import data
from khg_contracts.schema import is_alpha_acyclic, load_schema, schema_hypergraph

FIXTURE = load_schema(data.path("fixture/fixture.relation-schema.json"))
CYCLIC = load_schema(data.path("fixture/cyclic.relation-schema.json"))
WD = load_schema(data.path("fixture/wikidata-shaped.relation-schema.json"))


def test_the_fixture_schema_hypergraph():
    hg = schema_hypergraph(FIXTURE, slots=("core", "qualifier"))
    assert len(hg["vertices"]) == 30 and len(hg["hyperedges"]) == 11
    assert hg["hyperedges"]["regulates"] == ["context", "regulator", "target"]
    assert hg["hyperedges"]["married"] == ["spouse"]
    assert hg["hyperedges"]["position_held"] == ["holder", "position", "replaces"]
    assert hg["vertices"] == sorted(hg["vertices"])
    assert list(hg["hyperedges"]) == FIXTURE.relation_ids()
    assert not any(v.startswith("khg:") for v in hg["vertices"])
    assert schema_hypergraph(FIXTURE) == hg


def test_a_role_is_one_vertex_whatever_its_slot():
    hg = schema_hypergraph(FIXTURE)
    assert hg["vertices"].count("point_in_time") == 1
    assert "point_in_time" in hg["hyperedges"]["population"] and "point_in_time" in hg["hyperedges"]["claims"]


def test_time_and_meta_usages_appear_only_when_asked_for():
    plain = schema_hypergraph(FIXTURE)
    timed = schema_hypergraph(FIXTURE, slots=("core", "qualifier", "time"))
    assert {"start_time", "end_time"} & set(plain["vertices"]) == set()
    assert timed["hyperedges"]["married"] == ["end_time", "spouse", "start_time"]
    assert len(timed["vertices"]) == 32
    meta = schema_hypergraph(FIXTURE, slots=("meta",))
    assert meta == {"vertices": ["khg:end_cause"],
                    "hyperedges": {"position_held": ["khg:end_cause"], "married": ["khg:end_cause"]}}


def test_a_mapping_is_accepted_and_bad_slots_are_refused():
    assert schema_hypergraph(data.load_json("fixture/cyclic.relation-schema.json")) == schema_hypergraph(CYCLIC)
    with pytest.raises(ValueError):
        schema_hypergraph(FIXTURE, slots=("core", "context"))
    with pytest.raises(ValueError):
        schema_hypergraph(FIXTURE, slots="core")


def test_the_fixture_schema_is_alpha_acyclic():
    assert is_alpha_acyclic(schema_hypergraph(FIXTURE)) == (True, [])


def test_the_cyclic_schema_is_a_triangle():
    hg = schema_hypergraph(CYCLIC)
    assert hg["hyperedges"] == {"sale": ["buyer", "seller"], "brokerage": ["broker", "seller"],
                                "referral": ["broker", "buyer"]}
    assert is_alpha_acyclic(hg) == (False, [["buyer", "seller"], ["broker", "seller"], ["broker", "buyer"]])


def test_the_wikidata_shaped_schema_is_cyclic_with_the_stated_residue():
    acyclic, residue = is_alpha_acyclic(schema_hypergraph(WD))
    assert not acyclic
    assert residue == [["replaces", "series_ordinal"], ["point_in_time", "series_ordinal"],
                       ["point_in_time", "replaces"]]


@pytest.mark.parametrize("edges, want", [
    ([], (True, [])),
    ([["a"]], (True, [])),
    ([["a", "b"], ["b", "c"], ["c", "d"]], (True, [])),
    ([["a", "b", "c"], ["a", "b"], ["b", "c"], ["a", "c"]], (True, [])),
    ([["a", "b"], ["b", "c"], ["a", "c"]], (False, [["a", "b"], ["b", "c"], ["a", "c"]])),
    ({"r1": ["x", "y"], "r2": ["x", "y"]}, (True, [])),
])
def test_gyo_on_small_hypergraphs(edges, want):
    assert is_alpha_acyclic(edges) == want


def test_the_residue_does_not_depend_on_the_hash_seed():
    code = ("import json; from khg_contracts import data; from khg_contracts.schema import *; "
            "print(json.dumps([is_alpha_acyclic(schema_hypergraph(load_schema(data.path(p)))) for p in "
            "('fixture/cyclic.relation-schema.json', 'fixture/wikidata-shaped.relation-schema.json')]))")
    outs = set()
    for seed in ("0", "1", "2", "3"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
        outs.add(r.stdout)
    assert len(outs) == 1
    assert json.loads(outs.pop())[1][1] == [["replaces", "series_ordinal"], ["point_in_time", "series_ordinal"],
                                           ["point_in_time", "replaces"]]
