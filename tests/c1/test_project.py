"""W3: the projections of §2.10: positional, hyper-relational, role-value sets, the RDF relation instance and the
incidence rows."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, jsonio, record
from khg_contracts.record import project
from khg_contracts.schema import load_schema

S = load_schema(data.path("fixture/fixture.relation-schema.json"))
C1 = data.load_json("fixture/fixture.c1.json")
HIF = data.load_json("fixture/fixture.hif.json")
FACTS = {r["id"]: r for r in C1["records"] if r["kind"] == "hyperedge"}


def node_of(fid, bid):
    return next(i["node"] for i in HIF["incidences"] if i["edge"] == fid and i["attrs"]["khg-bid"] == bid)


def binding_structure(container):
    """The bindings the projections keep: {id: {relation, status, bindings}} without binding extensions."""
    out = {}
    for r in container["records"]:
        if r["kind"] == "hyperedge":
            bs = [{k: v for k, v in b.items() if k != "extensions"} for b in r["bindings"]]
            out[r["id"]] = {"relation": r["relation"], "status": r["status"],
                            "bindings": sorted(bs, key=record.binding_sort_key)}
    return out


# ------------------------------------------------------------------------------------------------ positional


def test_the_positional_example():
    assert project.positional(FACTS["f:route-1"], S, widths={"stop": 4}) == \
        ("flight_route", "ex:AirCanada", "ex:YYZ", "ex:YUL", "ex:YYZ", "khg:none")


def test_an_unbounded_usage_needs_a_width():
    with pytest.raises(ValueError, match="width"):
        project.positional(FACTS["f:route-1"], S)
    with pytest.raises(ValueError, match="width"):
        project.position_map(S, "co_administration_causes")
    with pytest.raises(ValueError, match="positions"):
        project.positional(FACTS["f:route-1"], S, widths={"stop": 2})  # three stops


def test_position_maps():
    assert project.position_map(S, "position_held", widths={"replaces": 2}) == \
        [("holder", 1), ("position", 1), ("replaces", 1), ("replaces", 2)]
    assert project.position_map(S, "position_held", slots=("core", "qualifier", "time"), widths={"replaces": 1}) == \
        [("holder", 1), ("position", 1), ("start_time", 1), ("end_time", 1), ("replaces", 1)]
    assert project.position_map(S, "station_profile", literals="drop", widths={"name": 2}) == [("station", 1)]
    assert project.position_map(S, "population", literals="drop") == [("place", 1)]
    with pytest.raises(ValueError):
        project.position_map(S, "population", literals="keep")


def test_positional_values_are_node_ids():
    k14 = FACTS["f:king-14"]
    assert project.positional(k14, S, widths={"replaces": 2}) == \
        ("position_held", "ex:LouisXIV", "ex:KingOfFrance", "ex:LouisXIII", "khg:none")
    timed = project.positional(k14, S, slots=("core", "time"))
    assert timed == ("position_held", "ex:LouisXIV", "ex:KingOfFrance", node_of("f:king-14", "b3"),
                     node_of("f:king-14", "b4"))
    assert project.positional(FACTS["f:cat-7"], S, widths={"catalyst": 1}) == \
        ("catalysed_by", "ex:R-hydrolysis-7", node_of("f:cat-7", "b2"))  # the per-binding _:nv: id
    assert project.positional(FACTS["f:claim-1"], S) == \
        ("claims", "ex:Chronicler_Ødegård", "f:born-louis14-paris", node_of("f:claim-1", "b3"))


def test_unordered_roles_fill_in_canonical_value_order():
    station = FACTS["f:station-東京"]
    got = project.positional(station, S, widths={"name": 3})
    assert got[:5] == ("station_profile", "ex:東京駅", node_of("f:station-東京", "b3"), node_of("f:station-東京", "b2"),
                       "khg:none")  # Tokyo Station@en before 東京駅@ja
    shuffled = copy.deepcopy(station)
    shuffled["bindings"].reverse()
    assert project.positional(shuffled, S, widths={"name": 3}) == got
    assert project.positional(station, S, literals="drop", widths={"name": 2}) == ("station_profile", "ex:東京駅")


def test_ordered_roles_fill_by_position():
    route = copy.deepcopy(FACTS["f:route-1"])
    for b, pos in zip(route["bindings"][1:], (3, 1, 2), strict=True):
        b["position"] = pos
    assert project.positional(route, S, widths={"stop": 3}) == \
        ("flight_route", "ex:AirCanada", "ex:YUL", "ex:YYZ", "ex:YYZ")


def test_lifecycle_and_goal_records_are_refused():
    for fid in ("m:sup-1", "g:who-1774"):
        with pytest.raises(ValueError, match="lifecycle and goal"):
            project.positional(FACTS[fid], S, widths={"khg:superseding": 1, "khg:superseded": 1})


# ------------------------------------------------------------------------------------------------ pairs


def test_hyper_relational():
    assert project.hyper_relational(FACTS["f:king-14"], S) == {
        "subject": "ex:LouisXIV", "relation": "position_held", "object": "ex:KingOfFrance",
        "qualifiers": [["end_time", node_of("f:king-14", "b4")], ["replaces", "ex:LouisXIII"],
                       ["start_time", node_of("f:king-14", "b3")]]}
    with pytest.raises(ValueError, match="primary"):
        project.hyper_relational(FACTS["f:route-1"], S)
    with pytest.raises(ValueError):
        project.hyper_relational(FACTS["g:who-1774"], S)  # an unbound holder has no id


def test_role_value_set():
    assert project.role_value_set(FACTS["f:coadmin-1"], S) == \
        [["agent", "ex:insulin"], ["agent", "ex:metformin"], ["effect", "ex:hypoglycaemia"]]
    assert project.role_value_set(FACTS["f:king-14"], S, slots=("core",)) == \
        [["holder", "ex:LouisXIV"], ["position", "ex:KingOfFrance"]]
    assert project.role_value_set(FACTS["f:loop-yyz"], S) == \
        [["carrier", "ex:AirCanada"], ["destination", "ex:YYZ"], ["origin", "ex:YYZ"]]


# ------------------------------------------------------------------------------------------------ RDF


def test_the_rdf_projection_round_trips_every_binding():
    triples = project.rdf_relation_instance(C1)
    assert len(triples) == 329
    assert project.from_rdf_relation_instance(triples) == binding_structure(C1)
    assert project.from_rdf_relation_instance(list(reversed(triples))) == binding_structure(C1)
    assert triples == sorted(triples, key=lambda t: jsonio.canonical(list(t)))


def test_the_rdf_vocabulary():
    triples = project.rdf_relation_instance(C1)
    preds = {p for _, p, _ in triples}
    assert preds == {project.RDF_TYPE} | {project.KHG_NS + x for x in (
        "relation", "status", "binding", "bid", "role", "position", "value", "valueKind", "valueJSON")}
    f = "urn:khg:f%3Aroute-1"
    assert (f, project.KHG_NS + "binding", f + "#b2") in triples
    assert (f + "#b2", project.KHG_NS + "position", {"literal": "1"}) in triples
    assert (f + "#b2", project.KHG_NS + "value", "urn:khg:ex%3AYYZ") in triples
    assert (f + "#b2", project.KHG_NS + "valueKind", {"literal": "entity"}) in triples
    lit = {"literal": {"datatype": "time", "time": "+1700-00-00T00:00:00Z", "precision": 9, "calendar": "julian"}}
    assert ("urn:khg:f%3Aclaim-1#b3", project.KHG_NS + "valueJSON", {"literal": jsonio.canonical(lit)}) in triples


def test_a_direction_is_projected_when_the_binding_has_one():
    doc = {"header": C1["header"], "records": [copy.deepcopy(FACTS["f:loop-yyz"])]}
    doc["records"][0]["bindings"][0]["direction"] = "tail"
    triples = project.rdf_relation_instance(doc)
    assert ("urn:khg:f%3Aloop-yyz#b1", project.KHG_NS + "direction", {"literal": "tail"}) in triples
    assert project.from_rdf_relation_instance(triples) == binding_structure(doc)


@pytest.mark.parametrize("identifier, iri", [
    ("ex:Łódź", "urn:khg:ex%3AŁódź"),
    ("f:station-東京", "urn:khg:f%3Astation-東京"),
    ("ex:a b/c#d%e?f", "urn:khg:ex%3Aa%20b%2Fc%23d%25e%3Ff"),
    ("ex:x~y_z.w-v", "urn:khg:ex%3Ax~y_z.w-v"),
    ("ex:" + chr(0x85) + chr(0xE000), "urn:khg:ex%3A%C2%85%EE%80%80"),  # outside ucschar: percent-encoded
])
def test_iris_are_percent_encoded_outside_iunreserved_and_reversible(identifier, iri):
    assert project.iri_encode(identifier) == iri
    assert project.iri_decode(iri) == identifier
    with pytest.raises(ValueError):
        project.iri_decode("https://example.org/x")


# ------------------------------------------------------------------------------------------------ incidence rows


def test_the_incidence_rows_round_trip_every_binding():
    rows = project.incidence_rows(C1)
    assert len(rows) == 59
    assert all(len(r) == len(project.INCIDENCE_COLUMNS) == 10 for r in rows)
    assert project.from_incidence_rows(rows) == binding_structure(C1)
    assert rows[:2] == [
        ("f:born-louis14-paris", 1, "born_in", "quoted", "b2", "birthplace", None, None, "entity", "ex:Paris"),
        ("f:born-louis14-paris", 1, "born_in", "quoted", "b1", "person", None, None, "entity", "ex:LouisXIV")]
    assert ("f:born-scribe", 1, "born_in", "asserted", "b2", "birthplace", None, None, "special",
            '{"special":"somevalue"}') in rows


def test_incidence_rows_keep_versions_in_canonical_order():
    history = data.load_json("fixture/fixture.history.c1.json")
    shuffled = {"header": history["header"], "records": list(reversed(history["records"]))}
    rows = project.incidence_rows(shuffled)
    assert [(r[0], r[1]) for r in rows if r[4] == "b1"] == \
        [("f:king-13", 1), ("f:king-13", 2), ("f:reg-1", 1), ("f:reg-1", 2), ("m:ret-1", 1)]
