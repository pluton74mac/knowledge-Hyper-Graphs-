"""W2: the Schema object and the built-in parts of every schema (DESIGN §2.4-§2.7, §3)."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data
from khg_contracts.errors import ValidationError
from khg_contracts.schema import (DATATYPES, END_CAUSE, LIFECYCLE_RELATIONS, Schema, load_schema)

S = load_schema(data.path("fixture/fixture.relation-schema.json"))
FIXTURE_RELATIONS = ["regulates", "co_administration_causes", "flight_route", "flies_between", "position_held",
                     "married", "population", "station_profile", "born_in", "claims", "catalysed_by"]


def test_identity_matches_the_fixture_header():
    header = data.load_json("fixture/fixture.c1.json")["header"]["schema"]
    assert (S.id, S.version, S.sha256) == (header["id"], header["version"], header["sha256"])
    assert S.header == header
    assert S.ref == "p2-gate/1.0.0"
    assert S.label == "P2 gate fixture schema"
    assert repr(S).startswith("Schema('p2-gate'/'1.0.0', sha256=sha256:cadd01c")


def test_relations_in_schema_order_and_the_built_ins():
    assert S.relation_ids() == FIXTURE_RELATIONS
    assert S.relation_ids(builtins=True) == FIXTURE_RELATIONS + ["khg:supersedes", "khg:retracts", "khg:disputes"]
    assert all(S.kind(r) == "fact" for r in FIXTURE_RELATIONS)
    assert all(S.kind(r) == "lifecycle" for r in LIFECYCLE_RELATIONS)
    assert S.has_relation("khg:disputes") and not S.has_relation("khg:merges")


@pytest.mark.parametrize("rel, usages, reasons", [
    ("khg:supersedes", [("khg:superseding", "tail", 1), ("khg:superseded", "head", 1)],
     ["correction", "duplicate", "refinement", "conflation", "schema_migration", "other"]),
    ("khg:retracts", [("khg:retracted", "head", 1)], ["withdrawn", "unsupported", "other"]),
    ("khg:disputes", [("khg:disputed", "head", 2)], ["key_conflict", "negation_conflict", "curator", "other"]),
])
def test_lifecycle_relations_follow_the_table(rel, usages, reasons):
    got = [(u["role"], u["direction"], u["min"]) for u in S.usages(rel)]
    assert got == usages
    assert all(u["slot"] == "core" and u["max"] is None and u["fillers"] == [{"fact": []}] for u in S.usages(rel))
    assert S.reasons(rel) == reasons
    assert S.time_model(rel) == {"model": "timeless"}
    assert S.key(rel) is None


def test_every_interval_relation_has_the_end_cause_meta_usage():
    for rel in FIXTURE_RELATIONS:
        roles = [u["role"] for u in S.usages(rel)]
        interval = S.time_model(rel)["model"] == "interval"
        assert ("khg:end_cause" in roles) is interval, rel
        assert roles[: len(S.relation(rel)["roles"])] == [u["role"] for u in S.relation(rel)["roles"]]
    u = S.usage("position_held", "khg:end_cause")
    assert u == END_CAUSE
    assert (u["slot"], u["min"], u["max"], u["direction"]) == ("meta", 0, 1, "tail")
    assert u["fillers"] == [{"entity": []}, {"literal": "string"}]
    assert S.slot("married", "khg:end_cause") == "meta"
    assert S.usages("position_held")[-1]["role"] == "khg:end_cause"


def test_time_models_two_interval_four_invariant_five_timeless():
    models = {r: S.time_model(r)["model"] for r in FIXTURE_RELATIONS}
    assert sorted(r for r, m in models.items() if m == "interval") == ["married", "position_held"]
    assert sorted(r for r, m in models.items() if m == "invariant") == ["born_in", "claims", "population", "regulates"]
    assert sum(1 for m in models.values() if m == "timeless") == 5
    assert S.default_time == {"model": "timeless"}
    assert S.time_model("position_held") == {"model": "interval", "start": "start_time", "end": "end_time"}


def test_a_default_time_applies_to_relations_without_one():
    doc = copy.deepcopy(S.doc)
    doc["default_time"] = {"model": "invariant"}
    s = Schema(doc)
    assert s.time_model("flight_route") == {"model": "invariant"}
    assert s.time_model("position_held")["model"] == "interval"
    assert s.sha256 != S.sha256


def test_keys_with_their_defaults():
    assert S.key("position_held") == {"roles": ["position"], "temporal": True, "on_collision": "close_older"}
    assert S.key("population") == {"roles": ["place", "point_in_time"], "temporal": False, "on_collision": "dispute"}
    assert S.key("born_in") == {"roles": ["person"], "temporal": False, "on_collision": "dispute"}
    assert S.key("regulates") is None


def test_the_fixture_schema_exercises_what_section_3_lists():
    fillers = {f["literal"] for u in S.usages("station_profile") for f in u["fillers"] if "literal" in f}
    assert fillers == set(DATATYPES) and len(DATATYPES) == 7
    spouse, agent = S.usage("married", "spouse"), S.usage("co_administration_causes", "agent")
    assert spouse["max"] == 2 and not spouse.get("ordered") and spouse["complete"]
    assert agent["max"] is None and not agent.get("ordered")
    stop = S.usage("flight_route", "stop")
    assert stop["ordered"] and stop["complete"] and stop["min"] == 2
    assert S.usage("claims", "claim")["fillers"] == [{"fact": ["born_in"]}]
    assert S.relation("flies_between")["constraints"] == [
        {"type": "must_differ", "roles": ["origin", "destination"], "severity": "warning"}]
    assert S.relation("position_held")["primary"] == {"subject": "holder", "object": "position"}


def test_unknown_relations_and_roles_are_s001_and_s002():
    with pytest.raises(ValidationError) as exc:
        S.relation("likes")
    assert exc.value.codes == ("KHG-S001",)
    with pytest.raises(ValidationError) as exc:
        S.usage("likes", "fan")
    assert exc.value.codes == ("KHG-S001",)
    with pytest.raises(ValidationError) as exc:
        S.usage("regulates", "khg:end_cause")
    assert exc.value.codes == ("KHG-S002",)


def test_entity_types_and_subtypes():
    assert S.entity_types["Person"] == ["Agent"]
    assert S.is_subtype("Person", "Agent") and S.is_subtype("Person", "Person")
    assert not S.is_subtype("Agent", "Person") and not S.is_subtype("Gene", "Agent")
    assert len(S.roles) == 32 and S.roles[:3] == ["regulator", "target", "context"]


def test_confidence_scales():
    assert S.confidence_scale("probability") == {"id": "probability", "kind": "bounded", "min": 0, "max": 1}
    assert S.confidence_scale("llm-0-10") == {"id": "llm-0-10", "kind": "bounded", "min": 0, "max": 10}
    assert S.confidence_scale("likert-5") is None


def test_the_schema_copies_its_document_and_compares_by_digest():
    doc = copy.deepcopy(S.doc)
    s = Schema(doc)
    doc["relations"].pop()
    assert s.relation_ids() == FIXTURE_RELATIONS and s == S and hash(s) == hash(S)
    assert Schema(doc) != S
    returned = S.usages("regulates")
    returned.clear()
    assert len(S.usages("regulates")) == 3


def test_built_in_definitions_are_not_shared_between_schemas():
    s = Schema(S.doc)
    s.relation("khg:supersedes")["reasons"].append("mutated")
    assert "mutated" not in S.reasons("khg:supersedes")
    assert "mutated" not in LIFECYCLE_RELATIONS["khg:supersedes"]["reasons"]
