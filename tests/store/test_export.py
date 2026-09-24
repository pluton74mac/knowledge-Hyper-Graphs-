"""W8: ``export`` and header state (DESIGN §6.2, critique STORE-HEADER): the three formats, the kept, passed and
computed headers, closed slices, ``as_at`` and history exports, and the G3 accept on the smoke base."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, jsonio, record, validate
from khg_contracts.errors import CapabilityMissing, ValidationError
from khg_contracts.store import ALL_FLAGS, MemoryStore, ScenarioClock, compare_containers


def test_the_three_formats_agree(loaded, schema, fixture_doc):
    doc = loaded.export("khg-json")
    text = loaded.export()  # khg-jsonl is the default
    assert isinstance(doc, dict) and isinstance(text, str)
    assert text == record.serialize(doc, format="jsonl")
    lines = jsonio.loads_lines(text)
    assert lines[0] == jsonio.loads(jsonio.canonical(doc["header"])) and len(lines) == 41
    assert list(doc["header"]) == ["kind", "format", "document_id", "schema", "content", "complete", "extensions"]
    assert [r["id"] for r in doc["records"]] == [r["id"] for r in record.canonical_container(fixture_doc)["records"]]
    assert all("derived" not in r and r["recorded_by"] == "load" for r in doc["records"])
    hif = loaded.export("hif")
    expected = data.load_json("fixture/fixture.hif.json")
    ignore = ("khg-version", "khg-recorded-at", "khg-recorded-by")
    for coll in ("nodes", "edges"):
        for item in hif[coll]:
            for k in ignore:
                item["attrs"].pop(k, None)
    assert hif == expected
    assert validate.validate_container(doc, schema=schema)["ok"]


def test_a_store_without_a_kept_header_computes_one(ms, schema, entities, rec):
    ms.put(entities + [rec("f:reg-1")], actor="t")
    header = ms.export("khg-json")["header"]
    assert header == {"kind": "header", "format": "khg-record/1.0.0", "document_id": "store:memory",
                      "schema": schema.header, "content": "snapshot", "complete": True}
    assert MemoryStore(schema, store_id="p1-pg").export("khg-json")["header"]["document_id"] == "store:p1-pg"
    orphan = MemoryStore(schema, clock=ScenarioClock())
    orphan.load({"header": {"kind": "header", "format": "khg-record/1.0.0", "document_id": "x",
                            "schema": schema.header, "content": "snapshot"},
                 "records": [rec("f:reg-1")]})
    assert "complete" not in orphan.export("khg-json")["header"]  # a kept header is kept as it is
    assert orphan.export("khg-json", header={"kind": "header", "format": "khg-record/1.0.0", "document_id": "y",
                                             "schema": schema.header})["header"]["document_id"] == "y"


def test_the_passed_header_overrides_and_content_and_as_at_are_the_exports(loaded, fixture_doc):
    header = dict(copy.deepcopy(fixture_doc["header"]), content="history", as_at="2000-01-01T00:00:00Z",
                  document_id="copy")
    doc = loaded.export("khg-json", header=header)
    assert doc["header"]["document_id"] == "copy" and doc["header"]["content"] == "snapshot"
    assert "as_at" not in doc["header"]
    doc = loaded.export("khg-json", as_at="2026-10-01T00:00:00Z")
    assert doc["header"]["as_at"] == "2026-10-01T00:00:00Z" and doc["header"]["document_id"] == "p2-gate-fixture"
    assert loaded.info()["header"]["document_id"] == "p2-gate-fixture"


def test_as_at_and_history_exports(ms, entities, rec, cur):
    ms.put(entities, actor="t")
    ms.put(rec("f:reg-1"), actor="t")
    ms.apply({"op": "add_evidence", "target": "f:reg-1", "evidence": [cur]}, actor="t")
    early = ms.export("khg-json", as_at="2026-10-01T00:00:00Z")
    assert [r["id"] for r in early["records"]][-1] == "ex:東京駅" and len(early["records"]) == 22
    history = ms.export("khg-jsonl", content="history")
    versions = [(x["id"], x["version"]) for x in jsonio.loads_lines(history)[1:] if x["id"] == "f:reg-1"]
    assert versions == [("f:reg-1", 1), ("f:reg-1", 2)]
    assert jsonio.loads_lines(history)[0]["content"] == "history"
    with pytest.raises(ValueError):
        ms.export("hif", content="history")
    for bad in ({"format": "turtle"}, {"content": "all"}, {"literal_nodes": "none"}):
        with pytest.raises(ValueError):
            ms.export(**{"format": "khg-json", **bad})


def test_exports_need_their_flags(schema, fixture_doc):
    s = MemoryStore(schema, clock=ScenarioClock(), capabilities=ALL_FLAGS - {"transaction_time",
                                                                              "history_export"})
    s.load(fixture_doc)
    with pytest.raises(CapabilityMissing) as e:
        s.export("khg-json", as_at="2026-10-01T00:00:00Z")
    assert e.value.flag == "transaction_time"
    with pytest.raises(CapabilityMissing) as e:
        s.export("khg-json", content="history")
    assert e.value.flag == "history_export"


def test_relations_export_a_closed_slice_in_every_format(loaded, schema):
    rels = ["born_in", "claims"]
    doc = loaded.export("khg-json", relations=rels)
    assert doc["header"]["complete"] is False
    edges = sorted(r["id"] for r in doc["records"] if r["kind"] == "hyperedge")
    assert edges == ["f:born-louis14-paris", "f:born-scribe", "f:born-skłodowska-kraków",
                     "f:born-skłodowska-warszawa", "f:claim-1", "m:sup-1"]
    hif = loaded.export("hif", relations=rels)
    assert hif["metadata"]["khg-slice"] == {"relations": rels} and hif["metadata"]["khg-complete"] is False
    assert sorted(e["edge"] for e in hif["edges"]) == edges
    assert validate.validate_hif(hif, schema=schema)["ok"]
    assert loaded.export("hif", literal_nodes="per_binding")["metadata"]["khg-literal-nodes"] == "per_binding"
    with pytest.raises(ValidationError) as e:
        loaded.export("khg-json", relations=["born_on"])
    assert e.value.codes == ("KHG-S001",)
    with pytest.raises(TypeError):
        loaded.export("khg-json", relations="born_in")


def test_the_g3_accept_reproduces_the_decision_hash(schema):
    """The smoke queue's accept, replayed on the smoke base: one atomic put of the payload with its id replaced and
    its status asserted writes f:king-14 version 1 with the committed decision_hash (DESIGN §1.2 G3, §7)."""
    base = data.load_json("fixture/smoke-base.c1.json")
    item = data.load_json("fixture/queue-item.json")
    entry = data.load_json("fixture/action-log.json")
    s = MemoryStore(schema)
    s.load(base, at="2000-01-01T00:00:00Z")
    stored = dict(copy.deepcopy(item["payload"]), id="f:king-14", status="asserted")
    receipt = s.put(list(item.get("entities", [])) + [stored], actor=entry["actor"]["id"], at=entry["at"])
    assert receipt["records"] == [("f:king-14", 1, "created")] and receipt["at"] == entry["at"]
    written = [{"id": "f:king-14", "version": 1, "record": record.decision_view(s.get("f:king-14"))}]
    assert jsonio.digest("khg-decision/1", written) == entry["decision_hash"]
    doc = s.export("khg-json")
    assert doc["header"]["document_id"] == "p2-smoke-base"
    assert validate.validate_container(doc, schema=schema)["ok"]
    assert validate.validate_hif(s.export("hif"), schema=schema)["ok"]
    assert compare_containers(base, doc) == [{"path": "/records/f:king-14", "id": "f:king-14", "a": None,
                                              "b": {k: v for k, v in record.normalize(stored).items()}}]
