"""W8: ``load`` as trusted bulk import (DESIGN §6.2): containers, streams and paths; V001 and D018; the kept
header; ``on_missing="raise"`` and ``on_missing="skip"`` (critique CONS-05)."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, record
from khg_contracts.errors import CapabilityMissing, ValidationError, VersionError
from khg_contracts.store import ALL_FLAGS, MemoryStore, ScenarioClock, compare_containers

CORE_DROPPED = ["f:born-scribe", "f:cat-7", "f:route-1", "g:who-1774"]


def fresh(schema, flags=None):
    return MemoryStore(schema, clock=ScenarioClock(), capabilities=flags)


def test_load_keeps_the_header_and_the_store_fields(schema, fixture_doc):
    s = fresh(schema)
    report = s.load(fixture_doc)
    assert (report["records"], report["versions"], report["skipped"]) == (40, 40, [])
    assert isinstance(report["seconds"], float) and report["seconds"] >= 0
    header = {k: v for k, v in fixture_doc["header"].items() if k != "content"}
    assert s.info()["header"] == header
    king = s.get("f:king-14")
    assert (king["version"], king["recorded_at"], king["recorded_by"]) == (1, "2026-10-01T00:00:00Z", "load")
    assert s.clock.now() == "2026-10-01T00:00:01Z"
    assert compare_containers(fixture_doc, s.export("khg-json")) == []


def test_on_missing_raise_loads_nothing(schema, fixture_doc):
    s = fresh(schema, ALL_FLAGS - {"goals"})
    with pytest.raises(CapabilityMissing) as e:
        s.load(fixture_doc)
    assert e.value.flag == "goals" and e.value.info["id"] == "g:who-1774"
    assert list(s.iter_records()) == [] and s.info()["header"] is None


@pytest.mark.parametrize("missing,skipped", [
    ({"goals"}, ["g:who-1774"]),
    ({"special_values"}, ["f:born-scribe", "f:cat-7"]),
    ({"ordered_roles"}, ["f:route-1"]),
    ({"ordered_roles", "special_values", "goals"}, CORE_DROPPED),
    ({"nesting"}, ["f:claim-1"]),
    ({"literal_values"}, ["f:claim-1", "f:king-13", "f:king-14", "f:married-curie", "f:pop-łódź-2019",
                          "f:pop-łódź-2019-dep", "f:station-東京", "g:who-1774"]),
])
def test_on_missing_skip_loads_what_the_flags_allow(schema, fixture_doc, missing, skipped):
    s = fresh(schema, ALL_FLAGS - missing)
    report = s.load(fixture_doc, on_missing="skip")
    assert report["skipped"] == skipped
    assert report["records"] == report["versions"] == 40 - len(skipped)
    held = {r["id"] for r in s.iter_records()}
    assert held == {r["id"] for r in fixture_doc["records"]} - set(skipped)
    if missing == {"ordered_roles", "special_values", "goals"}:
        core = {"header": fixture_doc["header"], "records": [r for r in fixture_doc["records"]
                                                             if r["id"] not in CORE_DROPPED]}
        assert compare_containers(core, s.export("khg-json")) == []


def test_skip_follows_references_to_skipped_records(schema, fixture_doc):
    """A record that references a skipped record is skipped too: a claim about a quoted fact that needs a flag,
    and a lifecycle record whose superseded fact is skipped, with the facts that name it in status_ref."""
    doc = copy.deepcopy(fixture_doc)
    records = {r["id"]: r for r in doc["records"]}
    records["f:born-louis14-paris"]["bindings"].append(
        {"bid": "b9", "role": "birthplace", "value": {"special": "somevalue"}})
    records["f:born-skłodowska-kraków"]["bindings"][0]["position"] = 1
    report = fresh(schema, ALL_FLAGS - {"special_values", "ordered_roles"}).load(doc, on_missing="skip")
    assert report["skipped"] == ["f:born-louis14-paris", "f:born-scribe", "f:born-skłodowska-kraków", "f:cat-7",
                                 "f:claim-1", "f:route-1", "m:sup-1"]


def test_load_streams_with_or_without_a_header_line(schema, fixture_doc):
    lines = [fixture_doc["header"]] + fixture_doc["records"]
    s = fresh(schema)
    assert s.load(iter(lines))["versions"] == 40
    assert s.info()["header"]["document_id"] == "p2-gate-fixture"
    headerless = fresh(schema)
    with pytest.raises(ValidationError) as e:
        headerless.load(iter(fixture_doc["records"]))
    assert e.value.codes == ("KHG-V001",)
    header = dict(fixture_doc["header"], document_id="p1-corpus")
    assert headerless.load(iter(fixture_doc["records"]), header=header)["versions"] == 40
    assert headerless.info()["header"]["document_id"] == "p1-corpus"
    overridden = fresh(schema)
    overridden.load(fixture_doc, header=header)
    assert overridden.export("khg-json")["header"]["document_id"] == "p1-corpus"


def test_load_reads_paths(schema, fixture_doc, tmp_path):
    for name, fmt in (("corpus.khg.jsonl", "jsonl"), ("corpus.khg.json", "json")):
        path = tmp_path / name
        record.write_container(fixture_doc, path, format=fmt)
        s = fresh(schema)
        assert s.load(str(path))["versions"] == 40
        assert compare_containers(fixture_doc, s.export("khg-json")) == []
    s = fresh(schema)
    assert s.load(record.iter_jsonl(tmp_path / "corpus.khg.jsonl"), on_missing="skip")["versions"] == 40
    with pytest.raises(TypeError):
        s.load(b"{}")
    other = tmp_path / "corpus.txt"  # §14 ruling 4: a path is read by its suffix, .json or .jsonl
    other.write_bytes((tmp_path / "corpus.khg.jsonl").read_bytes())
    s = fresh(schema)
    with pytest.raises(ValueError) as e:
        s.load(str(other))
    assert type(e.value) is ValueError and list(s.iter_records()) == []


def test_load_checks_the_format_and_transaction_times(schema, fixture_doc):
    with pytest.raises(ValidationError) as e:
        fresh(schema).load({"header": dict(fixture_doc["header"], format="khg-record/2.0.0"), "records": []})
    assert e.value.codes == ("KHG-V001",)
    with pytest.raises(ValidationError) as e:
        fresh(schema).load({"header": fixture_doc["header"], "records": [{"kind": "hyperedge"}]})
    assert e.value.codes == ("KHG-C010",)
    s = fresh(schema)
    s.put({"kind": "entity", "id": "ex:X", "types": ["Person"]}, actor="t", at="2026-10-02T00:00:00Z")
    with pytest.raises(VersionError) as e:  # a pinned load time before the store's latest
        s.load(fixture_doc, at="2026-10-01T00:00:00Z")
    assert e.value.codes == ("KHG-D018",)
    stamped = copy.deepcopy(fixture_doc)
    stamped["records"][0]["recorded_at"] = "2026-10-01T12:00:00Z"
    with pytest.raises(VersionError) as e:  # a kept recorded_at before the store's latest
        s.load(stamped)
    assert e.value.codes == ("KHG-D018",)
    with pytest.raises(ValueError):
        fresh(schema).load(fixture_doc, on_missing="ignore")


def test_load_at_stamps_records_without_transaction_times(schema, fixture_doc, rec):
    s = fresh(schema)
    s.load(fixture_doc, at="2000-01-01T00:00:00Z")
    assert s.get("f:reg-1")["recorded_at"] == "2000-01-01T00:00:00Z"
    receipt = s.put(rec("f:reg-1", add_evidence=[{"id": "e9", "type": "curated", "mode": "manual",
                                                  "source": {"doc_id": "d"}}]), actor="t")
    assert receipt["at"] == "2026-10-01T00:00:01Z"  # the load was a write: the clock ticked


def test_a_history_container_loads_every_version(schema):
    history = data.load_json("fixture/fixture.history.c1.json")
    with pytest.raises(CapabilityMissing) as e:
        fresh(schema, ALL_FLAGS - {"history_export"}).load(history)
    assert e.value.flag == "history_export"
    s = fresh(schema)
    report = s.load(history)
    assert (report["records"], report["versions"]) == (8, 10)
    assert [v["version"] for v in s.history("f:reg-1")] == [1, 2]
    assert s.get("f:reg-1")["status"] == "retracted"
    assert s.get("f:reg-1", as_at="2026-10-01T00:00:04Z")["status"] == "asserted"
    exported = s.export("khg-json", content="history")
    assert compare_containers(history, exported, ignore=()) == \
        [{"path": "/header/as_at", "a": "2026-10-01T00:00:05Z", "b": None}]
    assert s.clock.now() == "2026-10-01T00:00:06Z"


def _without_e1_supports(records):
    out = copy.deepcopy(records)
    for r in out:
        if r.get("id") == "f:king-13":
            r["evidence"][0].pop("supports")  # e1: v1 binds b1-b3, v2 adds b4
    return out


def test_a_loaded_history_keeps_what_carried_evidence_supports(schema):
    """§2.8.1: evidence that a later version carries without ``supports`` keeps what it supported where it was first
    written, so the store holds and exports the history unchanged (the history export validates)."""
    from khg_contracts import validate

    history = data.load_json("fixture/fixture.history.c1.json")
    doc = dict(history, records=_without_e1_supports(history["records"]))
    s = fresh(schema)
    s.load(doc)
    assert [v["evidence"][0]["supports"] for v in s.history("f:king-13")] == [["b1", "b2", "b3"]] * 2
    exported = s.export("khg-json", content="history")
    assert validate.validate_container(exported, schema=schema)["ok"]
    assert compare_containers(history, exported, ignore=())[1:] == []  # only the header's as_at differs
    snapshot = {r["id"]: r for r in s.export("khg-json")["records"]}
    assert snapshot["f:king-13"]["evidence"][0] == \
        next(r for r in history["records"] if r["id"] == "f:king-13" and r["version"] == 2)["evidence"][0]
    # a later load of version 2 carries over from the version the store holds
    first = dict(history, records=[r for r in history["records"] if r["kind"] == "entity"
                                   or (r["id"] == "f:king-13" and r["version"] == 1)])
    second = dict(history, header=dict(history["header"], content="snapshot"),
                  records=_without_e1_supports([r for r in history["records"]
                                                if r["id"] == "f:king-13" and r["version"] == 2]))
    s = fresh(schema)
    s.load(first)
    s.load(second)
    assert [v["evidence"][0]["supports"] for v in s.history("f:king-13")] == [["b1", "b2", "b3"]] * 2


def test_history_versions_must_increase(schema):
    history = data.load_json("fixture/fixture.history.c1.json")
    late = copy.deepcopy(history)
    late["header"]["as_at"] = "2026-10-01T00:00:04Z"
    with pytest.raises(VersionError) as e:  # a version after the header's as_at
        fresh(schema).load(late)
    assert e.value.codes == ("KHG-D018",)
    swapped = copy.deepcopy(history)
    for r in swapped["records"]:
        if r["id"] == "f:king-13":
            r["recorded_at"] = "2026-10-01T00:00:04Z" if r["version"] == 1 else "2026-10-01T00:00:02Z"
    with pytest.raises(VersionError) as e:  # a later version recorded before an earlier one
        fresh(schema).load(swapped)
    assert e.value.codes == ("KHG-D018",)
    s = fresh(schema)
    s.load(history)
    again = copy.deepcopy(history)
    again["records"] = [r for r in again["records"] if r["id"] == "f:king-13" and r["version"] == 2]
    again["records"][0]["recorded_at"] = "2026-10-02T00:00:00Z"
    with pytest.raises(VersionError) as e:  # version 2 of f:king-13 is held already
        s.load(again)
    assert e.value.codes == ("KHG-D018",)


def test_embedded_relation_schemas_are_kept_and_exported(schema, fixture_doc):
    doc = copy.deepcopy(fixture_doc)
    doc["records"].insert(0, copy.deepcopy(schema.doc))
    s = fresh(schema)
    assert s.load(doc)["versions"] == 40
    assert next(s.iter_records())["kind"] == "relation-schema"
    assert compare_containers(doc, s.export("khg-json")) == []
    assert s.get("p2-gate") is None


def test_reads_pass_over_a_malformed_record_that_a_load_kept(schema, fixture_doc):
    """``load`` is trusted: it keeps a record whose status, rank or visibility is not a string. The filters of the
    reads leave it out instead of raising TypeError (a list is not a member of a set of strings)."""
    for field, bad in (("rank", ["normal"]), ("status", {"s": "asserted"}), ("visibility", ["visible"])):
        doc = copy.deepcopy(fixture_doc)
        reg = next(r for r in doc["records"] if r["id"] == "f:reg-1")
        reg[field] = bad
        s = fresh(schema)
        s.load(doc)
        assert s.incident("ex:TP53") == [] and "f:reg-1" not in [r["id"] for r in s.find("regulates", [])]
        assert s.get("f:reg-1")[field] == bad  # get ignores Where and hands it out as loaded
