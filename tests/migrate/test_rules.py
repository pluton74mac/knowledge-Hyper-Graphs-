"""W10: the pinned rules of DESIGN §11.3 beyond the sample, on small ``v0-sample`` documents.

The sample exercises each rule in one way only (every role in every edge, one repeated role, directions that agree,
one ``valid-from``). These documents exercise the other branch of each rule, the optional members, and the order
independence of the result.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from khg_contracts import hif, migrate, record
from khg_contracts.schema import load_schema
from khg_contracts.store import compare_containers

NODES = {"a1": "Alpha", "a2": "Alpha", "z1": "Zeta", "b1": "Beta", "b2": "Beta"}


def v0(incidences: list[tuple[str, str, str | None, str]], edges: dict[str, dict[str, Any]], *,
       nodes: dict[str, str] | None = None, network: str = "directed",
       metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """A v0 document: incidences are ``(edge, node, direction or None, role)``; an edge's ``weight`` key is the
    record weight, its other keys are ``attrs`` (``source`` defaults to ``doc:1``)."""
    doc: dict[str, Any] = {"network-type": network}
    if metadata is not None:
        doc["metadata"] = metadata
    doc["nodes"] = [{"node": n, "attrs": {"type": t, "label": n.upper()}} for n, t in (nodes or NODES).items()]
    doc["edges"] = []
    for e, spec in edges.items():
        attrs = {"source": "doc:1", **{k: v for k, v in spec.items() if k != "weight"}}
        doc["edges"].append({"edge": e, **({"weight": spec["weight"]} if "weight" in spec else {}), "attrs": attrs})
    doc["incidences"] = [{"edge": e, "node": n, **({"direction": d} if d else {}), "attrs": {"role": r}}
                         for e, n, d, r in incidences]
    return doc


def usages(m: migrate.Migration) -> dict[tuple[str, str], dict[str, Any]]:
    return {(r["id"], u["role"]): u for r in m.schema["relations"] for u in r["roles"]}


def hyperedge(m: migrate.Migration, rid: str) -> dict[str, Any]:
    return next(r for r in m.container["records"] if r["id"] == rid)


def round_trip(m: migrate.Migration) -> dict[str, Any]:
    schema = load_schema(m.schema)
    h = hif.to_hif(m.container, schema)
    back = hif.from_hif(h, schema)
    assert compare_containers(m.container, back, ignore=()) == []
    return h


# ------------------------------------------------------------------------------------------------ the usages


def test_min_is_one_only_for_a_role_that_occurs_in_every_edge_of_its_relation():
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x"), ("e1", "b1", "head", "y"), ("e2", "a2", "tail", "x")],
                                   {"e1": {"relation": "r"}, "e2": {"relation": "r"}}))
    u = usages(m)
    assert (u[("r", "x")]["min"], u[("r", "y")]["min"]) == (1, 0)
    assert [b["role"] for b in hyperedge(m, "e2")["bindings"]] == ["x"]


def test_max_is_null_only_for_a_role_that_repeats_in_an_edge():
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x"), ("e1", "a2", "tail", "x"), ("e1", "b1", "head", "y")],
                                   {"e1": {"relation": "r", "arity": 3}}))
    u = usages(m)
    assert (u[("r", "x")]["max"], u[("r", "y")]["max"]) == (None, 1)
    assert [f["code"] for f in m.report["findings"]] == ["KHG-F015"]


def test_the_fillers_are_the_observed_types_sorted_and_the_schema_lists_every_node_type():
    nodes = {**NODES, "lonely": "Omega"}
    m = migrate.v0_sample_to_v1(v0([("e1", "z1", "tail", "x"), ("e2", "a1", "tail", "x"), ("e1", "b1", "head", "y"),
                                    ("e2", "b2", "head", "y")],
                                   {"e1": {"relation": "r"}, "e2": {"relation": "r"}}, nodes=nodes))
    assert usages(m)[("r", "x")]["fillers"] == [{"entity": ["Alpha", "Zeta"]}]
    assert [t["id"] for t in m.schema["entity_types"]] == ["Alpha", "Beta", "Omega", "Zeta"]
    entities = [r["id"] for r in m.container["records"] if r["kind"] == "entity"]
    assert "lonely" in entities and len(entities) == len(nodes)  # an isolated node is still an entity


def test_relations_roles_and_usages_are_sorted_by_id():
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "zz"), ("e1", "b1", "head", "aa"), ("e2", "a2", "tail", "mm"),
                                    ("e2", "b2", "head", "bb")],
                                   {"e1": {"relation": "later"}, "e2": {"relation": "earlier"}}))
    assert [r["id"] for r in m.schema["relations"]] == ["earlier", "later"]
    assert [[u["role"] for u in r["roles"]] for r in m.schema["relations"]] == [["bb", "mm"], ["aa", "zz"]]
    assert [r["id"] for r in m.schema["roles"]] == ["aa", "bb", "mm", "zz"]


# ------------------------------------------------------------------------------------------------ directions


def test_a_usage_has_a_direction_only_when_its_incidences_agree_and_bindings_keep_theirs():
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x"), ("e1", "b1", "head", "y"), ("e2", "a2", "head", "x"),
                                    ("e2", "b2", "head", "y")],
                                   {"e1": {"relation": "r"}, "e2": {"relation": "r"}}))
    u = usages(m)
    assert "direction" not in u[("r", "x")] and u[("r", "y")]["direction"] == "head"
    assert [(b["role"], b.get("direction")) for b in hyperedge(m, "e1")["bindings"]] == [("x", "tail"), ("y", None)]
    assert [(b["role"], b.get("direction")) for b in hyperedge(m, "e2")["bindings"]] == [("x", "head"), ("y", None)]
    h = round_trip(m)
    assert h["network-type"] == "directed"
    assert [(i["edge"], i["node"], i["direction"]) for i in h["incidences"]] == [
        ("e1", "a1", "tail"), ("e1", "b1", "head"), ("e2", "a2", "head"), ("e2", "b2", "head")]


def test_an_undirected_file_keeps_its_native_directions():
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x"), ("e1", "b1", None, "y")], {"e1": {"relation": "r"}},
                                   network="undirected"))
    u = usages(m)
    assert u[("r", "x")]["direction"] == "tail" and "direction" not in u[("r", "y")]
    h = round_trip(m)
    assert h["network-type"] == "undirected"
    assert [i.get("direction") for i in h["incidences"]] == ["tail", None]


# ------------------------------------------------------------------------------------------------ time and bids


def test_the_time_model_comes_only_with_valid_from():
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x"), ("e2", "a2", "tail", "x"), ("e3", "b1", "tail", "y")],
                                   {"e1": {"relation": "r", "valid-from": "1999-12-31"}, "e2": {"relation": "r"},
                                    "e3": {"relation": "s"}}))
    relations = {r["id"]: r for r in m.schema["relations"]}
    assert relations["r"]["time"] == {"model": "interval", "start": "start_time", "end": "end_time"}
    assert "time" not in relations["s"]
    assert [b["role"] for b in hyperedge(m, "e1")["bindings"]] == ["start_time", "x"]
    assert [b["role"] for b in hyperedge(m, "e2")["bindings"]] == ["x"]  # the other edge gets no start_time
    assert [f["code"] for f in m.report["findings"]] == ["KHG-F017"]
    round_trip(m)
    plain = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x")], {"e1": {"relation": "r"}}))
    assert [r["id"] for r in plain.schema["roles"]] == ["x"]  # no time roles without valid-from


def test_bids_follow_the_canonical_binding_order_not_the_incidence_order():
    edges = {"e1": {"relation": "r", "valid-from": "2020-02-29"}}
    forward = [("e1", "b2", "head", "c"), ("e1", "a2", "tail", "a"), ("e1", "a1", "tail", "a"),
               ("e1", "b1", "head", "b")]
    m = migrate.v0_sample_to_v1(v0(forward, edges))
    assert [(b["bid"], b["role"], b["value"].get("entity")) for b in hyperedge(m, "e1")["bindings"]] == [
        ("b1", "a", "a1"), ("b2", "a", "a2"), ("b3", "b", "b1"), ("b4", "c", "b2"), ("b5", "start_time", None)]
    assert migrate.v0_sample_to_v1(v0(list(reversed(forward)), edges)) == m


# ------------------------------------------------------------------------------------------------ optional members


def test_optional_members_leave_no_trace():
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x")], {"e1": {"relation": "r"}}))
    e1 = hyperedge(m, "e1")
    assert "extensions" not in e1 and "extensions" not in m.container["header"]
    assert m.report == {"format": "khg-migration-report/1.0.0", "from": "v0-sample", "findings": []}
    doc = v0([("e1", "a1", "tail", "x")], {"e1": {"relation": "r"}})
    del doc["nodes"][0]["attrs"]["label"]
    entity = next(r for r in migrate.v0_sample_to_v1(doc).container["records"] if r["id"] == "a1")
    assert entity == {"kind": "entity", "id": "a1", "types": ["Alpha"]}


@pytest.mark.parametrize("metadata, replaced, kept", [
    ({"schema": "https://example.org/hif.json"}, "metadata schema replaced by the declaration block", None),
    ({"conventions": {"x": "y"}, "title": "T"}, "metadata conventions replaced by the declaration block",
     {"title": "T"}),
    ({"title": "T", "created": "2026-01-01", "source": {"by": ["kb"]}}, None,
     {"title": "T", "created": "2026-01-01", "source": {"by": ["kb"]}}),
    ({}, None, None),
])
def test_the_metadata(metadata, replaced, kept):
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x")], {"e1": {"relation": "r"}}, metadata=metadata))
    f016 = [f["message"] for f in m.report["findings"] if f["code"] == "KHG-F016"]
    assert f016 == ([replaced] if replaced else [])
    assert m.container["header"].get("extensions") == (None if kept is None else {"hif:metadata": kept})
    if kept:
        assert list(m.container["header"]["extensions"]["hif:metadata"]) == list(kept)  # source order
    h = round_trip(m)
    assert all(h["metadata"][k] == v for k, v in (kept or {}).items())


def test_weights_and_arities_of_any_json_number_type():
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x"), ("e2", "a2", "tail", "x")],
                                   {"e1": {"relation": "r", "weight": 3, "arity": 1.0},
                                    "e2": {"relation": "r", "weight": 0.5, "arity": 1}}))
    e1 = hyperedge(m, "e1")
    assert e1["extensions"] == {"hif:weight": 3} and type(e1["extensions"]["hif:weight"]) is int
    weight = "weight kept as extensions hif:weight"
    assert [(f["code"], f["edge"], f["message"]) for f in m.report["findings"]] == [
        ("KHG-F006", "e1", weight), ("KHG-F015", "e1", "stored arity 1.0 checked and dropped"),
        ("KHG-F006", "e2", weight), ("KHG-F015", "e2", "stored arity 1 checked and dropped")]
    h = round_trip(m)
    assert [e["weight"] for e in h["edges"]] == [3, 0.5]


def test_the_report_follows_the_edge_order_of_the_file():
    m = migrate.v0_sample_to_v1(v0([("e1", "a1", "tail", "x"), ("e2", "a2", "tail", "x")],
                                   {"e2": {"relation": "r", "weight": 1}, "e1": {"relation": "r", "weight": 2}}))
    assert [f["edge"] for f in m.report["findings"]] == ["e2", "e1"]
    assert [r["id"] for r in m.container["records"] if r["kind"] == "hyperedge"] == ["e1", "e2"]


def test_generate_schema_is_the_returned_schema_and_passes_the_m_layer():
    doc = v0([("e1", "a1", "tail", "x"), ("e1", "a2", "tail", "x"), ("e1", "b1", "head", "y")],
             {"e1": {"relation": "r", "valid-from": "2001-01-01"}})
    m = migrate.v0_sample_to_v1(copy.deepcopy(doc))
    assert migrate.generate_schema(doc) == m.schema
    assert load_schema(m.schema).relation_ids() == ["r"]
    assert record.arity(hyperedge(m, "e1"), m.schema)["arity"] == 3
