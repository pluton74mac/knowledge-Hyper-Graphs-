"""W9: the queue schema ``khg-queue-1.0.0.schema.json`` (DESIGN §7, §8.1).

- The packaged file is the output of ``khg_contracts.queue.codegen``, byte for byte, and the generator's CLI writes
  it.
- It compiles offline under both engines and accepts the four lines of the smoke queue.
- Each structural violation names its code (Q001-Q005, Q008, Q010, and C codes for an item's entities), under both
  engines; fastjsonschema's single code is among jsonschema's.
"""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data
from khg_contracts.queue import codegen
from khg_contracts.queue.lines import dump_line, line_findings, read_lines
from khg_contracts.queue.model import SCHEMA_FILE, SCHEMA_ID
from khg_contracts.validate import engines

ENGINES = engines.ENGINES
LINES = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
HEADER, ITEM, LINT, ACCEPT = LINES


def test_the_packaged_schema_is_the_generator_output(tmp_path):
    assert data.read_text(SCHEMA_FILE) == codegen.render(codegen.build())
    assert codegen.main([str(tmp_path)]) == 0
    assert (tmp_path / codegen.FILE_NAME).read_bytes() == data.read_bytes(SCHEMA_FILE)
    assert codegen.main([]) == 2
    doc = data.load_json(SCHEMA_FILE)
    assert doc["$id"] == SCHEMA_ID and doc["$schema"] == engines.DRAFT7
    assert SCHEMA_ID in data.schema_documents()


def test_every_ref_is_absolute_and_there_is_no_one_of_or_any_of():
    doc = data.load_json(SCHEMA_FILE)
    refs = list(engines.refs(doc))
    assert refs and all(r.startswith((SCHEMA_ID + "#/definitions/", engines.RECORD_SCHEMA_ID + "#/definitions/"))
                        for r in refs)
    text = data.read_text(SCHEMA_FILE)
    assert '"oneOf"' not in text and '"anyOf"' not in text


@pytest.mark.parametrize("engine", ENGINES)
def test_the_smoke_queue_lines_are_valid(engine):
    for n, line in enumerate(LINES):
        assert line_findings(line, engine=engine, path=f"/lines/{n}") == []


def test_lines_are_canonical_json_one_per_line():
    raw = data.read_text("fixture/smoke-queue.khg-queue.jsonl")
    assert raw == "".join(dump_line(line) for line in LINES)
    assert read_lines(data.path("fixture/smoke-queue.khg-queue.jsonl")) == LINES
    assert read_lines(raw.encode("utf-8")) == LINES
    copied = read_lines(LINES)
    assert copied == LINES and copied[1] is not LINES[1]
    with pytest.raises(TypeError):
        read_lines(42)
    with pytest.raises(TypeError):
        read_lines([1, 2])


def _set(obj, path, value):
    parts = path.split("/")
    for p in parts[:-1]:
        obj = obj[int(p)] if isinstance(obj, list) else obj[p]
    last = parts[-1]
    if value is _DROP:
        del obj[int(last) if isinstance(obj, list) else last]
    elif isinstance(obj, list):
        obj[int(last)] = value
    else:
        obj[last] = value


_DROP = object()
#: (line, JSON path in the line, new value or _DROP, the code, the finding's path)
BROKEN = [
    (ITEM, "run/run_id", _DROP, "KHG-Q001", "/run"),
    (ITEM, "run/position", -1, "KHG-Q001", "/run/position"),
    (ITEM, "submitted_by", _DROP, "KHG-Q001", ""),
    (ITEM, "submitted_by", "p2-fixture-extractor", "KHG-Q001", "/submitted_by"),
    (ITEM, "doc/doc_sha256", _DROP, "KHG-Q001", "/doc"),
    (ITEM, "doc", _DROP, "KHG-Q001", ""),
    (ITEM, "payload/evidence", _DROP, "KHG-Q001", "/payload"),
    (ITEM, "payload/evidence", [], "KHG-Q001", "/payload/evidence"),
    (ITEM, "payload/status", "asserted", "KHG-Q002", "/payload/status"),
    (ITEM, "payload/id", "f:king-14", "KHG-Q002", "/payload/id"),
    (ITEM, "item_kind", "merge_proposal", "KHG-Q003", "/item_kind"),
    (ITEM, "keys", _DROP, "KHG-Q010", ""),
    (ITEM, "keys/core_key", "sha256:1234", "KHG-Q010", "/keys/core_key"),
    (ITEM, "qid", "q-000001", "KHG-Q008", "/qid"),
    (ITEM, "submitted_at", "2026-10-01 00:00:03", "KHG-Q008", "/submitted_at"),
    (ITEM, "extra", 1, "KHG-Q008", ""),
    (ITEM, "run/extra", 1, "KHG-Q008", "/run"),
    (ITEM, "entities", [{"kind": "entity", "id": "ex: bad", "types": ["Person"]}], "KHG-C011", "/entities/0/id"),
    (LINT, "action", "auto_fix", "KHG-Q003", "/action"),
    (LINT, "kind", "log_entry", "KHG-Q003", "/kind"),
    (LINT, "findings", _DROP, "KHG-Q004", ""),
    (LINT, "rule_set", _DROP, "KHG-Q004", ""),
    (LINT, "outcome", "violation", "KHG-Q004", "/outcome"),
    (LINT, "findings", [{"code": "KHG-S003", "severity": "warning", "path": ""}], "KHG-Q004", "/findings/0"),
    (LINT, "state_before", "merged", "KHG-Q005", "/state_before"),
    (LINT, "lid", "l-000001", "KHG-Q008", "/lid"),
    (LINT, "parent", _DROP, "KHG-Q008", ""),
    (LINT, "actor/type", "robot", "KHG-Q008", "/actor/type"),
    (LINT, "mode", "manually", "KHG-Q008", "/mode"),
    (ACCEPT, "decision_hash", _DROP, "KHG-Q008", ""),
    (ACCEPT, "reason", "", "KHG-Q008", "/reason"),
    (ACCEPT, "after", [{"id": "f:king-14", "version": 0}], "KHG-Q008", "/after/0/version"),
    (HEADER, "queue_id", "p2 smoke", "KHG-Q008", "/queue_id"),
    (HEADER, "schema/sha256", _DROP, "KHG-Q008", "/schema"),
    (HEADER, "base/document_id", _DROP, "KHG-Q008", "/base"),
    (HEADER, "created_at", _DROP, "KHG-Q008", ""),
    (HEADER, "kind", "queue_header", "KHG-Q003", "/kind"),
]


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize(("line", "where", "value", "code", "path"), BROKEN,
                         ids=[f"{b[0]['kind']}:{b[1]}={'drop' if b[2] is _DROP else b[2]!r}" for b in BROKEN])
def test_each_violation_names_its_code(line, where, value, code, path, engine):
    bad = copy.deepcopy(line)
    _set(bad, where, value)
    found = line_findings(bad, engine=engine)
    assert found, (where, value)
    if engine == "jsonschema":
        assert (code, path) in [(f["code"], f["path"]) for f in found]
    else:  # fastjsonschema stops at its first error: its one code is among jsonschema's
        assert len(found) == 1 and found[0]["code"] in {f["code"] for f in line_findings(bad)}


def test_a_verdict_entry_is_checked_by_label_and_note():
    entry = {"kind": "log-entry", "lid": "l:p2-smoke.000003", "parent": "l:p2-smoke.000002",
             "target": "q:p2-smoke.000001", "action": "verdict", "state_before": "accepted",
             "state_after": "accepted", "actor": {"type": "person", "id": "curator:smoke"}, "mode": "manual",
             "at": "2026-10-01T00:01:00Z",
             "verdict": {"evidence_id": "e2", "core_key": ITEM["keys"]["core_key"],
                         "event_hash": ITEM["payload"]["evidence"][1]["event_hash"], "label": "correct",
                         "bindings": [{"role": "holder", "position": None, "value": {"entity": "ex:LouisXIV"},
                                       "bid": "b1", "label": "correct"}],
                         "missing": []}}
    for engine in ENGINES:
        assert line_findings(entry, engine=engine) == []
    other = copy.deepcopy(entry)
    other["verdict"]["label"] = "other"
    assert [(f["code"], f["path"]) for f in line_findings(other)] == [("KHG-Q008", "/verdict")]
    other["verdict"]["note"] = "a paraphrase, not a claim"
    assert line_findings(other) == []
    missing = copy.deepcopy(entry)
    del missing["verdict"]
    assert [(f["code"], f["path"]) for f in line_findings(missing)] == [("KHG-Q008", "")]
    wrong = copy.deepcopy(entry)
    wrong["verdict"]["bindings"][0]["label"] = "fine"
    assert [f["code"] for f in line_findings(wrong)] == ["KHG-Q008"]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_line_without_kind_or_of_another_kind_is_q003(engine):
    for bad in ({}, {"kind": "queue_item"}, {"kind": "header"}):
        assert [f["code"] for f in line_findings(bad, engine=engine)] == ["KHG-Q003"]


def test_every_pattern_ends_the_text():
    """``$`` also matches before a final newline. The packaged patterns end in ``schema.codegen.END``, as those of the
    other generated schemas do, so the file itself refuses ``"q:...\\n"`` (the engines anchor at load time too)."""
    import re

    from khg_contracts.schema.codegen import END, patterns

    found = list(patterns(data.load_json(SCHEMA_FILE)))
    assert found and all(p.endswith(END) for p in found)
    qid = data.load_json(SCHEMA_FILE)["definitions"]["qid"]["pattern"]
    assert re.search(qid, "q:p2-smoke.000001") and not re.search(qid, "q:p2-smoke.000001\n")
