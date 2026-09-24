"""W8: ``compare_containers`` (DESIGN §6.3; critique CONS-05, GL-04): headers compared, records in canonical form
keyed by id (snapshots) or (id, version) (history containers), store fields ignored by default."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data
from khg_contracts.store import compare_containers


def test_equal_containers_have_no_difference(fixture_doc):
    other = copy.deepcopy(fixture_doc)
    other["records"].reverse()
    for r in other["records"]:
        if r["kind"] == "hyperedge":
            r["bindings"].reverse()
            if r.get("rank") == "normal":
                r.pop("rank")  # a default
            r["derived"] = {"arity": 99}  # an optional cache
            r["version"], r["recorded_at"], r["recorded_by"] = 7, "2026-10-01T00:00:00Z", "somebody"
    other["header"]["created_at"] = "2026-10-01T00:00:00Z"
    other["header"]["generator"] = {"name": "p1", "version": "0.1"}
    assert compare_containers(fixture_doc, other) == []


def test_header_differences(fixture_doc):
    other = copy.deepcopy(fixture_doc)
    other["header"]["document_id"] = "other"
    other["header"]["created_at"] = "2026-10-01T00:00:00Z"
    other["header"].pop("complete")
    assert compare_containers(fixture_doc, other) == [
        {"path": "/header/complete", "a": True, "b": None},
        {"path": "/header/document_id", "a": "p2-gate-fixture", "b": "other"}]
    assert compare_containers(fixture_doc, other, header_ignore=()) == [
        {"path": "/header/complete", "a": True, "b": None},
        {"path": "/header/created_at", "a": None, "b": "2026-10-01T00:00:00Z"},
        {"path": "/header/document_id", "a": "p2-gate-fixture", "b": "other"}]


def test_record_differences_name_the_fields(fixture_doc):
    other = copy.deepcopy(fixture_doc)
    records = {r["id"]: r for r in other["records"]}
    records["f:reg-1"]["status"] = "quoted"
    records["f:reg-1"]["recorded_by"] = "x"
    other["records"] = [r for r in other["records"] if r["id"] != "ex:HeLa"]
    other["records"].append({"kind": "entity", "id": "ex:New", "types": ["Person"]})
    diffs = compare_containers(fixture_doc, other)
    assert [(d["path"], d["id"], d.get("fields")) for d in diffs] == [
        ("/records/ex:HeLa", "ex:HeLa", None), ("/records/ex:New", "ex:New", None),
        ("/records/f:reg-1", "f:reg-1", ["status"])]
    assert diffs[0]["b"] is None and diffs[1]["a"] is None
    assert [d["fields"] for d in compare_containers(fixture_doc, other, ignore=()) if "fields" in d] == \
        [["recorded_by", "status"]]


def test_history_containers_key_records_by_version():
    history = data.load_json("fixture/fixture.history.c1.json")
    other = copy.deepcopy(history)
    other["records"] = [r for r in other["records"] if not (r["id"] == "f:king-13" and r["version"] == 2)]
    assert compare_containers(history, other) == [
        {"path": "/records/f:king-13/2", "id": "f:king-13", "version": 2,
         "a": {k: v for k, v in next(r for r in history["records"] if r["id"] == "f:king-13"
                                     and r["version"] == 2).items()
               if k not in ("version", "recorded_at", "recorded_by")}, "b": None}]
    assert compare_containers(history, copy.deepcopy(history), ignore=()) == []


def test_carried_evidence_without_supports_is_no_difference():
    """§2.8.1: in a history, evidence carried without ``supports`` supports what it did where it was first written,
    so leaving the list out of both versions of f:king-13's e1 (v2 adds b4) changes nothing."""
    history = data.load_json("fixture/fixture.history.c1.json")
    implicit = copy.deepcopy(history)
    for r in implicit["records"]:
        if r["id"] == "f:king-13":
            r["evidence"][0].pop("supports")
    assert compare_containers(history, implicit, ignore=()) == []
    widened = copy.deepcopy(history)
    next(r for r in widened["records"] if r["id"] == "f:king-13" and r["version"] == 2)["evidence"][0]["supports"] = \
        ["b1", "b2", "b3", "b4"]
    assert [d["path"] for d in compare_containers(implicit, widened)] == ["/records/f:king-13/2"]


def test_only_containers_compare(fixture_doc):
    with pytest.raises(TypeError):
        compare_containers(fixture_doc, "{}")
    assert compare_containers({"header": {}, "records": []}, {"header": {}, "records": []}) == []
