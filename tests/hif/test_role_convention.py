"""W6: ``role-convention`` 1.0.0 and layer R (DESIGN §4.1, §4.4, §12.3).

The five files of the upstream fixture PR are valid against the vendored schema and pass layer R under both
engines; ``from_hif`` refuses them (P001). The four rules are checked one by one.
"""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, hif
from khg_contracts.errors import ValidationError
from khg_contracts.validate import run, validate

FILES = ("basic", "two-roles", "tail-head", "ordered", "undirected")
ENGINES = ("jsonschema", "fastjsonschema")


def _load(name):
    return data.load_json(f"role-convention/{name}.hif.json")


def _r(doc):
    return [(f["code"], f["path"]) for f in hif.convention_findings(doc)]


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("name", FILES)
def test_the_five_files_pass_h_and_r(name, engine):
    path = data.path(f"role-convention/{name}.hif.json")
    report = run(path, engine=engine)  # auto: no khg-profile, a role-convention declaration
    assert report.kind == "role-convention"
    assert [step for step, _ in report.steps] == ["j", "h", "r"]
    assert (report.ok, report.findings, report.skipped) == (True, [], [])
    assert validate(path, kind="role-convention", engine=engine) == {"ok": True, "findings": []}


@pytest.mark.parametrize("name", FILES)
def test_the_five_files_use_the_convention_only(name):
    doc = _load(name)
    assert doc["metadata"]["role-convention"] == "1.0.0"
    assert not any(k.startswith(("khg-", "hif-")) for k in doc["metadata"])
    assert all(set(i["attrs"]) <= {"role", "role-position"} for i in doc["incidences"])
    assert _r(doc) == []


@pytest.mark.parametrize("name", FILES)
def test_from_hif_refuses_them_with_p001(name):
    with pytest.raises(ValidationError) as e:
        hif.from_hif(_load(name), data.load_json("fixture/fixture.relation-schema.json"))
    assert e.value.codes[0] == "KHG-P001"
    report = run(_load(name), kind="hif")
    assert report.first_layer == "P" and "KHG-P001" in {f["code"] for f in report.errors}


def test_what_the_files_show():
    assert [i["attrs"]["role"] for i in _load("two-roles")["incidences"] if i["node"] == "alice"] == ["buyer", "payer"]
    tail_head = [(i["attrs"]["role"], i["direction"]) for i in _load("tail-head")["incidences"] if i["node"] == "TP53"]
    assert tail_head == [("regulator", "tail"), ("target", "head")]
    ordered = [(i["node"], i["attrs"].get("role-position")) for i in _load("ordered")["incidences"]]
    assert ordered == [("AC", None), ("YYZ", 1), ("YUL", 2), ("YYZ", 3)]
    undirected = _load("undirected")
    assert undirected["network-type"] == "undirected" and sum("direction" in i for i in undirected["incidences"]) == 3
    assert set(_load("basic")["metadata"]["role-vocabulary"]) == {"buyer", "seller", "item"}


# ------------------------------------------------------------------------------------------------ rule 1: R001


def test_rule_1_every_incidence_of_a_role_carrying_edge_has_a_role():
    doc = _load("basic")
    assert _r(doc) == []
    no_roles = {"metadata": {"role-convention": "1.0.0"},
                "incidences": [{"edge": "e", "node": "a"}, {"edge": "e", "node": "b", "attrs": {}}]}
    assert _r(no_roles) == []  # an edge without any role is not role-carrying
    for bad in (None, "", ["buyer", "payer"], 7):
        d = copy.deepcopy(doc)
        if bad is None:
            del d["incidences"][1]["attrs"]["role"]
        else:
            d["incidences"][1]["attrs"]["role"] = bad
        assert _r(d) == [("KHG-R001", "/incidences/1/attrs/role")], bad
    d = copy.deepcopy(doc)
    del d["incidences"][2]["attrs"]
    assert _r(d) == [("KHG-R001", "/incidences/2/attrs/role")]
    d["incidences"].append({"edge": "other", "node": "x"})  # another edge, without roles: fine
    assert _r(d) == [("KHG-R001", "/incidences/2/attrs/role")]


# ------------------------------------------------------------------------------------------------ rule 2: R002


def test_rule_2_repeated_pairs_must_differ_in_role_or_position():
    assert _r(_load("two-roles")) == [] and _r(_load("tail-head")) == [] and _r(_load("ordered")) == []
    d = _load("tail-head")
    d["incidences"][1]["attrs"]["role"] = "regulator"  # same (edge, node, role) with another direction: a repeat
    assert _r(d) == [("KHG-R002", "/incidences/1")]
    d = _load("ordered")
    d["incidences"][3]["attrs"]["role-position"] = 1
    assert _r(d) == [("KHG-R002", "/incidences/3")]
    d["incidences"][3]["attrs"]["role-position"] = 1.0  # the same position (F10)
    assert _r(d) == [("KHG-R002", "/incidences/3")]
    d = _load("basic")
    d["incidences"].append({"edge": "sale-1", "node": "alice", "attrs": {"role": "buyer"}})
    assert _r(d) == [("KHG-R002", "/incidences/3")]
    d["incidences"][3]["edge"] = "sale-2"  # another edge
    assert _r(d) == []


def test_rule_2_keeps_json_types_apart():
    doc = {"metadata": {"role-convention": "1.0.0"},
           "incidences": [{"edge": 1, "node": 2, "attrs": {"role": "r"}},
                          {"edge": "1", "node": "2", "attrs": {"role": "r"}}]}
    assert _r(doc) == []


# ------------------------------------------------------------------------------------------------ rule 3: R003


@pytest.mark.parametrize("metadata", [None, {}, {"role-convention": "1.1.0"}, {"role-convention": 1},
                                      {"role-convention": "1.0"}])
def test_rule_3_the_declaration(metadata):
    d = _load("basic")
    if metadata is None:
        del d["metadata"]
    else:
        d["metadata"] = metadata
    assert _r(d) == [("KHG-R003", "/metadata/role-convention")]


# ------------------------------------------------------------------------------------------------ rule 4: R004


@pytest.mark.parametrize(("value", "ok"), [(1, True), (3, True), (2.0, True), (0, False), (-1, False),
                                           (1.5, False), ("1", False), (True, False), (None, False)])
def test_rule_4_role_position_is_an_integer_of_at_least_1(value, ok):
    d = _load("ordered")
    d["incidences"][2]["attrs"]["role-position"] = value
    assert _r(d) == ([] if ok else [("KHG-R004", "/incidences/2/attrs/role-position")])
    assert hif.role_position(value) == (int(value) if ok else None)


def test_the_r_checks_read_any_document():
    for doc in ({}, {"incidences": {}}, {"incidences": [1, "x", None]}, {"metadata": [], "incidences": [[]]},
                {"metadata": {"role-convention": "1.0.0"}, "incidences": [{"attrs": "role"}]}, [], "x"):
        hif.convention_findings(doc)
    assert _r({"metadata": {"role-convention": "1.0.0"}, "incidences": [{"edge": "e", "attrs": {"role": ["r"]}}]}) \
        == [("KHG-R001", "/incidences/0/attrs/role")]


@pytest.mark.parametrize("engine", ENGINES)
def test_r_findings_through_the_validator(engine):
    d = _load("ordered")
    d["incidences"][1]["attrs"]["role-position"] = 0
    report = run(d, engine=engine)
    assert report.kind == "role-convention" and report.first_layer == "R"
    assert [(f["code"], f["path"]) for f in report.findings] == [("KHG-R004", "/incidences/1/attrs/role-position")]
    d = _load("basic")
    d["incidences"][0]["direction"] = "treatment"
    report = run(d, engine=engine)
    assert report.first_layer == "H" and [f["code"] for f in report.errors] == ["KHG-H005"]
