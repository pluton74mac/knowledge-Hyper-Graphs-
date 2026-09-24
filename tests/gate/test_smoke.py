"""G3: smoke test of the queue, the structural lint, the store and export (DESIGN §1.2, §7).

The seven steps of the G3 list run once, in order, on packaged data:

1. ``MemoryStore.load(smoke-base)``;
2. ``Queue.create(base=smoke-base)``, then ``make_candidate`` (the fixture's ``f:king-14``), then ``Queue.submit``;
3. ``Linter.lint``, the structural rule set;
4. ``Queue.accept(qid, store=…, id="f:king-14", actor="curator:smoke", reason=…)``;
5. ``export`` as khg-json and as HIF, both valid;
6. ``validate_queue`` finds no error;
7. ``replay(path, schema=…, factory=store.memory_factory, base=smoke-base)`` reproduces ``decision_hash``
   ``sha256:518db0f4…7f29``.

The queue these steps write equals the committed ``smoke-queue.khg-queue.jsonl`` byte for byte, and
``queue-item.json`` and ``action-log.json`` are its item and accept lines.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import data, hif, record, store
from khg_contracts.queue import Linter, Queue, make_candidate, replay
from khg_contracts.schema import Schema, load_schema
from khg_contracts.validate import ENGINES, validate_container, validate_hif, validate_queue

pytestmark = pytest.mark.gate

SMOKE_QUEUE = "fixture/smoke-queue.khg-queue.jsonl"
DECISION_HASH = "sha256:518db0f4a88cffe427846b412c99d755945c35816fc3c5e83d31c2ea30807f29"
BASE_SHA256 = "sha256:f7933d12ef05e1751b3f130863a8595b0049f5e529d2c7bea9d4ff9cf02ccb6a"
REASON = "the regnal list and the biography sentence support every binding"


@dataclass
class G3:
    """What the seven steps produced."""

    schema: Schema
    base: dict[str, Any]
    king14: dict[str, Any]
    path: Path
    load: dict[str, Any]
    loaded: dict[str, Any]
    store: store.MemoryStore
    queue: Queue
    candidate: dict[str, Any]
    qid: str
    lint: dict[str, Any]
    accept: dict[str, Any]


@pytest.fixture(scope="module")
def g3(tmp_path_factory) -> G3:
    schema = load_schema(data.path("fixture/fixture.relation-schema.json"))
    base = data.load_json("fixture/smoke-base.c1.json")
    king14 = next(r for r in data.load_json("fixture/fixture.c1.json")["records"] if r["id"] == "f:king-14")
    # 1. the store loads the base
    s = store.MemoryStore(schema, clock=store.ScenarioClock())
    load = s.load(base)
    loaded = s.export("khg-json")
    # 2. the queue, the candidate and the item
    path = tmp_path_factory.mktemp("g3") / "p2-smoke.khg-queue.jsonl"
    q = Queue.create(path, queue_id="p2-smoke", schema=schema, base=base, created_at="2026-10-01T00:00:00Z")
    cand = make_candidate(king14, queue_id="p2-smoke", seq=1, schema=schema)
    e2 = next(e for e in cand["evidence"] if e["type"] == "extracted")
    qid = q.submit(cand, run={"run_id": "fixture-run-1", "order_id": "o1", "position": 0, "seed": 0, "temperature": 0},
                   doc={"doc_id": e2["source"]["doc_id"], "doc_sha256": e2["source"]["doc_sha256"]},
                   submitted_by="p2-fixture-extractor/0.0.1", at="2026-10-01T00:00:03Z")
    # 3. the structural lint
    lint = Linter(schema).lint(q, qid, at="2026-10-01T00:00:05Z")
    # 4. the accept
    accept = q.accept(qid, store=s, id="f:king-14", actor="curator:smoke", reason=REASON, at="2026-10-01T00:00:07Z")
    return G3(schema, base, king14, path, load, loaded, s, q, cand, qid, lint, accept)


def test_1_the_store_loads_the_smoke_base(g3):
    assert g3.load["records"] == g3.load["versions"] == len(g3.base["records"]) == 22 and g3.load["skipped"] == []
    assert store.compare_containers(g3.base, g3.loaded) == []
    assert record.container_sha256(g3.base) == BASE_SHA256 == g3.queue.header["base"]["sha256"]


def test_2_the_candidate_is_submitted(g3):
    item = data.load_json("fixture/queue-item.json")
    assert g3.qid == item["qid"] == "q:p2-smoke.000001"
    assert g3.candidate == item["payload"]
    assert g3.queue.item(g3.qid) == item
    assert item["keys"] == {"content_key": record.content_key(g3.king14, g3.schema),
                            "core_key": record.core_key(g3.king14, g3.schema),
                            "key_digest": record.key_digest(g3.king14, g3.schema)}


def test_3_the_structural_lint_passes(g3):
    assert (g3.lint["outcome"], g3.lint["findings"], g3.lint["state_after"]) == ("pass", [], "linted")
    assert g3.lint == data.load_jsonl(SMOKE_QUEUE)[2]


def test_4_the_accept_writes_king_14(g3):
    assert g3.accept == data.load_json("fixture/action-log.json")
    assert g3.accept["decision_hash"] == DECISION_HASH and g3.accept["after"] == [{"id": "f:king-14", "version": 1}]
    assert g3.queue.state(g3.qid) == "accepted"
    stored = g3.store.get("f:king-14")
    assert (stored["version"], stored["recorded_by"], stored["recorded_at"]) == (1, "curator:smoke",
                                                                                 "2026-10-01T00:00:07Z")
    assert record.decision_view(stored) == record.decision_view(g3.king14)  # the fixture record, nothing else


def test_5_both_exports_are_valid(g3):
    doc = g3.store.export("khg-json")
    for engine in ENGINES:
        assert validate_container(doc, schema=g3.schema, engine=engine) == {"ok": True, "findings": []}
    written = dict(copy.deepcopy(g3.candidate), id="f:king-14", status="asserted")
    assert store.compare_containers(g3.loaded, doc) == [  # the accept added f:king-14 and nothing else
        {"path": "/records/f:king-14", "id": "f:king-14", "a": None, "b": record.normalize(written)}]
    h = g3.store.export("hif")
    for engine in ENGINES:
        assert validate_hif(h, schema=g3.schema, engine=engine) == {"ok": True, "findings": []}
    assert store.compare_containers(hif.from_hif(h, g3.schema), doc) == []


def test_6_validate_queue_finds_no_error(g3):
    for engine in ENGINES:
        result = validate_queue(g3.path, schema=g3.schema, bases=[g3.base], engine=engine)
        assert result == {"ok": True, "findings": []}
    assert validate_queue(g3.queue, schema=g3.schema, bases=[data.path("fixture/smoke-base.c1.json")])["ok"]


def test_7_replay_reproduces_the_decision_hash(g3):
    result = replay(g3.path, schema=g3.schema, factory=store.memory_factory,
                    base=data.path("fixture/smoke-base.c1.json"))
    assert result["ok"] and result["findings"] == []
    assert [d["decision_hash"] for d in result["decisions"]] == [DECISION_HASH]
    assert store.compare_containers(g3.store.export("khg-json"), result["store"].export("khg-json")) == []
    committed = replay(data.path(SMOKE_QUEUE), schema=g3.schema, factory=store.memory_factory, base=g3.base)
    assert committed["ok"] and committed["decisions"] == result["decisions"]


def test_the_regenerated_smoke_queue_equals_the_packaged_file(g3):
    assert g3.path.read_bytes() == data.read_bytes(SMOKE_QUEUE)
    lines = data.load_jsonl(SMOKE_QUEUE)
    assert lines[1] == data.load_json("fixture/queue-item.json")
    assert lines[3] == data.load_json("fixture/action-log.json")


def test_a_tampered_queue_fails_the_gate_checks(g3, tmp_path):
    """The gate's checks can fail: a changed decision hash is Q006 in both validate_queue and replay."""
    raw = g3.path.read_text(encoding="utf-8").replace(DECISION_HASH, "sha256:" + "1" * 64)
    p = tmp_path / "tampered.khg-queue.jsonl"
    p.write_text(raw, encoding="utf-8")
    assert [f["code"] for f in validate_queue(p, schema=g3.schema, bases=[g3.base])["findings"]] == ["KHG-Q006"]
    assert [f["code"] for f in replay(p, schema=g3.schema, factory=store.memory_factory,
                                      base=copy.deepcopy(g3.base))["findings"]] == ["KHG-Q006"]
