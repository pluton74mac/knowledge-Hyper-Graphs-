"""W10: what ``v0_sample_to_v1`` refuses, and with which registered codes (DESIGN §10.2, §11.3).

§10.2 names one refusal: a stored arity that disagrees with the C1 arity (``ValidationError``; D015, the code of a
stored derived value that disagrees with recomputation). The others keep the migration from guessing or dropping
anything: each case mutates the v0 sample once and names the codes and the path of the first finding. Input faults
have paths into the input; faults of the generated schema or container have paths into the document that
``info["schema"]`` or ``info["container"]`` holds.
"""
from __future__ import annotations

import copy
import unicodedata
from typing import Any, Callable

import pytest

from khg_contracts import migrate
from khg_contracts.errors import ValidationError
from khg_contracts.validate import registry

Mutation = Callable[[dict[str, Any]], Any]


def _set(path: tuple[Any, ...], value: Any) -> Mutation:
    def mutate(d: dict[str, Any]) -> None:
        for key in path[:-1]:
            d = d[key]
        d[path[-1]] = copy.deepcopy(value)
    return mutate


def _del(path: tuple[Any, ...]) -> Mutation:
    def mutate(d: dict[str, Any]) -> None:
        for key in path[:-1]:
            d = d[key]
        del d[path[-1]]
    return mutate


def _append(key: str, item: Any) -> Mutation:
    return lambda d: d[key].append(copy.deepcopy(item(d) if callable(item) else item))


NFD = unicodedata.normalize("NFD", "drug:métformin")

#: id -> (mutation of the v0 sample, the error's codes, the path of its first finding)
CASES: dict[str, tuple[Mutation, tuple[str, ...], str]] = {
    # the stored arity (§10.2)
    "stored-arity-disagrees": (_set(("edges", 1, "attrs", "arity"), 4), ("KHG-D015",), "/edges/1/attrs/arity"),
    "stored-arity-is-a-string": (_set(("edges", 0, "attrs", "arity"), "4"), ("KHG-D015",), "/edges/0/attrs/arity"),
    "stored-arity-is-a-boolean": (_set(("edges", 2, "attrs", "arity"), True), ("KHG-D015",), "/edges/2/attrs/arity"),
    # layers J and H
    "nan-weight": (_set(("edges", 0, "weight"), float("nan")), ("KHG-J004",), "/edges/0/weight"),
    "edges-not-an-array": (_set(("edges",), {}), ("KHG-H009",), "/edges"),
    "extra-top-level-key": (_set(("khg",), 1), ("KHG-H002",), ""),
    "direction-outside-head-and-tail": (_set(("incidences", 0, "direction"), "in"), ("KHG-H005",),
                                        "/incidences/0/direction"),
    # ids and declarations
    "integer-node-id": (_set(("nodes", 0, "node"), 7), ("KHG-P002", "KHG-D002"), "/nodes/0/node"),
    "integer-incidence-edge": (_set(("incidences", 0, "edge"), 1), ("KHG-P002",), "/incidences/0/edge"),
    "node-id-with-a-space": (_set(("nodes", 0, "node"), "drug metformin"), ("KHG-C011", "KHG-D002"), "/nodes/0/node"),
    "edge-id-with-the-reserved-prefix": (_set(("edges", 2, "edge"), "_:f3"), ("KHG-C011", "KHG-D003", "KHG-S007"),
                                         "/edges/2/edge"),
    "node-id-not-in-nfc": (_set(("nodes", 0, "node"), NFD), ("KHG-S020", "KHG-D002"), "/nodes/0/node"),
    "node-declared-twice": (_append("nodes", lambda d: d["nodes"][1]), ("KHG-D001",), "/nodes/8/node"),
    "edge-declared-twice": (_append("edges", lambda d: d["edges"][2]), ("KHG-D001",), "/edges/3/edge"),
    "incidence-to-an-undeclared-edge": (_set(("incidences", 8, "edge"), "f9"), ("KHG-D003",), "/incidences/8/edge"),
    "incidence-to-an-undeclared-node": (_set(("incidences", 8, "node"), "org:WHO"), ("KHG-D002",),
                                        "/incidences/8/node"),
    "edge-without-incidences": (_append("edges", {"edge": "f4", "attrs": {"relation": "publishes",
                                                                          "source": "doc:x"}}),
                                ("KHG-S007",), "/edges/3"),
    # roles
    "incidence-without-role": (_del(("incidences", 3, "attrs", "role")), ("KHG-R001",), "/incidences/3/attrs/role"),
    "empty-role": (_set(("incidences", 3, "attrs", "role"), ""), ("KHG-R001",), "/incidences/3/attrs/role"),
    "role-not-a-string": (_set(("incidences", 3, "attrs", "role"), ["population"]), ("KHG-R001",),
                          "/incidences/3/attrs/role"),
    "role-not-in-nfc": (_set(("incidences", 3, "attrs", "role"), unicodedata.normalize("NFD", "populatión")),
                        ("KHG-S020",), "/incidences/3/attrs/role"),
    "exact-repeat": (_append("incidences", lambda d: d["incidences"][5]), ("KHG-R002",), "/incidences/9"),
    # members the format does not have
    "role-position": (_set(("incidences", 5, "attrs", "role-position"), 1), ("KHG-C009",),
                      "/incidences/5/attrs/role-position"),
    "edge-confidence-attr": (_set(("edges", 0, "attrs", "confidence"), 0.9), ("KHG-C009",),
                             "/edges/0/attrs/confidence"),
    "node-attr": (_set(("nodes", 0, "attrs", "synonyms"), ["T2D"]), ("KHG-C009",), "/nodes/0/attrs/synonyms"),
    "node-weight": (_set(("nodes", 0, "weight"), 2), ("KHG-C009",), "/nodes/0/weight"),
    "incidence-weight": (_set(("incidences", 0, "weight"), 0.5), ("KHG-C009",), "/incidences/0/weight"),
    # the C1 fields the members become
    "node-without-type": (_del(("nodes", 0, "attrs", "type")), ("KHG-C010",), "/nodes/0/attrs/type"),
    "type-list": (_set(("nodes", 0, "attrs", "type"), ["Drug"]), ("KHG-C010",), "/nodes/0/attrs/type"),
    "label-not-a-string": (_set(("nodes", 0, "attrs", "label"), 3), ("KHG-C010",), "/nodes/0/attrs/label"),
    "edge-without-relation": (_del(("edges", 1, "attrs", "relation")), ("KHG-C010",), "/edges/1/attrs/relation"),
    "edge-without-source": (_del(("edges", 1, "attrs", "source")), ("KHG-C010",), "/edges/1/attrs/source"),
    "source-not-a-string": (_set(("edges", 1, "attrs", "source"), 5), ("KHG-C010",), "/edges/1/attrs/source"),
    "valid-from-not-a-date": (_set(("edges", 0, "attrs", "valid-from"), "2024-01-01T10:00:00Z"), ("KHG-C004",),
                              "/edges/0/attrs/valid-from"),
    "valid-from-february-30": (_set(("edges", 0, "attrs", "valid-from"), "2024-02-30"), ("KHG-S006",),
                               "/edges/0/attrs/valid-from"),
    "valid-from-before-1583": (_set(("edges", 0, "attrs", "valid-from"), "1500-06-01"), ("KHG-S006",),
                               "/edges/0/attrs/valid-from"),
    "valid-from-year-0": (_set(("edges", 0, "attrs", "valid-from"), "0000-06-01"), ("KHG-S006",),
                          "/edges/0/attrs/valid-from"),
    # network type and metadata
    "asc": (_set(("network-type",), "asc"), ("KHG-P007",), "/network-type"),
    "directed-without-a-direction": (_del(("incidences", 2, "direction")), ("KHG-P010",), "/incidences/2"),
    "undirected-with-every-direction": (_set(("network-type",), "undirected"), ("KHG-P011",), "/network-type"),
    "khg-metadata-key": (_set(("metadata", "khg-profile"), "khg-hif/1.0.0"), ("KHG-P008",), "/metadata/khg-profile"),
    "declaration-metadata-key": (_set(("metadata", "role-convention"), "1.0.0"), ("KHG-P008",),
                                 "/metadata/role-convention"),
    "default-attrs": (_set(("metadata", "default_attrs"), {}), ("KHG-P008",), "/metadata/default_attrs"),
    # the generated schema (paths into info["schema"])
    "reserved-role": (_set(("incidences", 8, "attrs", "role"), "khg:publication"), ("KHG-M008",), "/roles/5/id"),
    "start-time-as-a-role": (_set(("incidences", 1, "attrs", "role"), "start_time"), ("KHG-M002", "KHG-M007"),
                             "/relations/2/roles/4/role"),
    "type-with-a-space": (_set(("nodes", 7, "attrs", "type"), "Official Document"), ("KHG-M015",),
                          "/entity_types/4/id"),
    # the migrated container (paths into info["container"])
    "node-and-edge-share-an-id": (_append("nodes", {"node": "f2", "attrs": {"type": "Drug"}}),
                                  ("KHG-D001", "KHG-D007"), "/records/10"),
}


@pytest.mark.parametrize("case", CASES)
def test_the_refusal(case, v0):
    mutate, codes, first_path = CASES[case]
    mutate(v0)
    with pytest.raises(ValidationError) as err:
        migrate.v0_sample_to_v1(v0)
    assert err.value.codes == codes
    findings = err.value.info["findings"]
    assert findings[0]["path"] == first_path
    assert {f["code"] for f in findings if f["severity"] == "error"} == set(codes)
    reg = registry()
    for f in findings:
        assert f["code"] in reg and reg[f["code"]].active, f["code"]
        assert f["layer"] == f["code"][4] and f["message"]


def test_the_stored_arity_refusal_names_both_arities(v0):
    v0["edges"][0]["attrs"]["arity"] = 5  # design B's first migration run counted valid-from (DB §2.7)
    with pytest.raises(ValidationError) as err:
        migrate.v0_sample_to_v1(v0)
    assert err.value.info["findings"] == [{"code": "KHG-D015", "severity": "error", "layer": "D",
                                           "path": "/edges/0/attrs/arity",
                                           "message": "f1: the stored arity 5 disagrees with the C1 arity 4"}]
    assert isinstance(err.value, ValueError)


def test_every_stored_arity_that_disagrees_is_reported(v0):
    v0["edges"][0]["attrs"]["arity"] = 5
    v0["edges"][2]["attrs"]["arity"] = 1
    with pytest.raises(ValidationError) as err:
        migrate.v0_sample_to_v1(v0)
    assert [f["path"] for f in err.value.info["findings"]] == ["/edges/0/attrs/arity", "/edges/2/attrs/arity"]


def test_refusals_of_generated_documents_carry_the_document(v0):
    v0["incidences"][1]["attrs"]["role"] = "start_time"
    with pytest.raises(ValidationError) as err:
        migrate.v0_sample_to_v1(v0)
    schema = err.value.info["schema"]
    assert schema["relations"][2]["roles"][4]["role"] == "start_time"  # the path of the first finding
    assert all(f["message"].startswith("the generated schema: ") for f in err.value.info["findings"])


def test_refusals_of_the_container_name_the_record(v0):
    v0["nodes"].append({"node": "f2", "attrs": {"type": "Drug"}})
    with pytest.raises(ValidationError) as err:
        migrate.v0_sample_to_v1(v0)
    container = err.value.info["container"]
    assert container["records"][10]["id"] == "f2"
    assert [f["message"] for f in err.value.info["findings"]] == [
        "the migrated container: record 'f2': f2 is declared twice",
        "the migrated container: record 'f2': f2 names both an entity and a hyperedge"]


def test_a_refused_input_is_not_modified(v0):
    v0["edges"][0]["attrs"]["arity"] = 5
    before = copy.deepcopy(v0)
    with pytest.raises(ValidationError):
        migrate.v0_sample_to_v1(v0)
    assert v0 == before


@pytest.mark.parametrize("source, code", [(b"{", "KHG-J001"), (b'{"a": 1, "a": 2}', "KHG-J003"),
                                          ([1, 2], "KHG-J007"), (b"[]", "KHG-J007")])
def test_what_is_not_a_json_object(source, code):
    with pytest.raises(ValidationError) as err:
        migrate.v0_sample_to_v1(source)
    assert err.value.codes == (code,)


def test_an_unreadable_path_is_an_os_error(tmp_path):
    with pytest.raises(OSError):  # as in the validator: the path is an argument, not a finding
        migrate.v0_sample_to_v1(tmp_path / "missing.hif.json")
