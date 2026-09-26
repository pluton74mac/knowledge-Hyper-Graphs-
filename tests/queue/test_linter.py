"""W9: ``Linter(schema, *, store=None, entities=None, doc_texts=None).lint(queue, qid, *, at=None)``, the structural
rule set (DESIGN §7).

The C and S codes on the payload (S003 a warning on candidates), Q001-Q003, Q009, Q010 and Q011. Entities resolve
from ``item.entities``, then the linter's entities or the queue's base, then the store; S005 runs only on resolved
entities and an unresolved one is Q011. The outcome moves the item: pass to linted, warn to needs_review, fail to
rejected. A schema pin or a base that does not match raises before anything is logged.
"""
from __future__ import annotations

import copy
import os

import pytest

from khg_contracts import data, record
from khg_contracts.errors import ValidationError
from khg_contracts.queue import Linter, Queue
from khg_contracts.schema import load_schema
from khg_contracts.store import MemoryStore, ScenarioClock

TEXTS = data.load_json("fixture/fixture.doc-texts.json")


def _codes(entry):
    return [(f["code"], f["severity"], f["path"]) for f in entry["findings"]]


def _entity(base, eid, **change):
    return dict(copy.deepcopy(next(r for r in base["records"] if r["id"] == eid)), **change)


def test_the_smoke_item_passes(smoke, smoke_lines):
    q = smoke.create()
    qid = smoke.submit(q)
    entry = smoke.lint(q, qid)
    assert entry == smoke_lines[2] and q.state(qid) == "linted"
    assert (entry["actor"], entry["mode"], entry["rule_set"]) == (
        {"type": "linter", "id": "khg-lint", "version": "1.1.0"}, "automatic", {"id": "structural", "version": "1.1.0"})


def test_without_a_source_every_entity_is_q011_and_the_item_is_rejected(smoke):
    q = smoke.create(base=None)
    qid = smoke.submit(q)
    entry = smoke.lint(q, qid)
    assert entry["outcome"] == "fail" and entry["state_after"] == "rejected" and q.state(qid) == "rejected"
    assert _codes(entry) == [("KHG-Q011", "error", f"/payload/bindings/{i}/value") for i in (1, 2, 3)]
    assert all(set(f) == {"code", "severity", "path", "message"} for f in entry["findings"])


@pytest.mark.parametrize("source", ["container", "path", "records", "mapping", "store"])
def test_entities_resolve_from_the_linter_or_the_store(smoke, base, source):
    q = smoke.create(base=None)
    qid = smoke.submit(q)
    entities = [r for r in base["records"] if r["kind"] == "entity"]
    kw = {"container": {"entities": base}, "path": {"entities": data.path("fixture/smoke-base.c1.json")},
          "records": {"entities": entities}, "mapping": {"entities": {r["id"]: r for r in entities}}}.get(source)
    if kw is None:
        s = MemoryStore(smoke.schema, clock=ScenarioClock())
        s.load(base)
        kw = {"store": s}
    entry = smoke.lint(q, qid, **kw)
    assert entry["outcome"] == "pass" and entry["findings"] == []


def test_item_entities_come_first_then_the_linter_s_then_the_base_then_the_store(smoke, base):
    place = _entity(base, "ex:LouisXIII", types=["Place"])
    q = smoke.create()
    first = smoke.submit(q, entities=[place])
    entry = smoke.lint(q, first)
    assert _codes(entry) == [("KHG-S005", "error", "/payload/bindings/3")] and q.state(first) == "rejected"
    second = smoke.submit(q, smoke.candidate(q, 2))
    assert _codes(smoke.lint(q, second, entities=[place])) == [("KHG-S005", "error", "/payload/bindings/3")]
    third = smoke.submit(q, smoke.candidate(q, 3))
    bad_store = MemoryStore(smoke.schema, clock=ScenarioClock())
    bad_store.put(place, actor="t")
    assert smoke.lint(q, third, store=bad_store)["outcome"] == "pass"  # the base resolves before the store
    fourth = smoke.submit(q, smoke.candidate(q, 4), entities=[_entity(base, "ex:LouisXIII")])
    assert smoke.lint(q, fourth, entities=[place])["outcome"] == "pass"  # item.entities before the linter's


def test_a_base_that_does_not_match_the_header_raises_q012_and_logs_nothing(smoke, base, store):
    q = smoke.create()
    qid = smoke.submit(q)
    size = os.path.getsize(q.path)
    changed = copy.deepcopy(base)
    changed["records"] = changed["records"][:-1]
    with pytest.raises(ValidationError) as exc:
        smoke.lint(q, qid, entities=changed)  # the header's document_id, another sha256
    assert exc.value.codes == ("KHG-Q012",)
    reopened = Queue.open(q.path, schema=smoke.schema)  # no base on the handle
    with pytest.raises(ValidationError) as exc:
        Linter(smoke.schema).lint(reopened, qid)
    assert exc.value.codes == ("KHG-Q012",)
    assert os.path.getsize(q.path) == size and reopened.state(qid) == "pending"
    other_doc = copy.deepcopy(changed)
    other_doc["header"]["document_id"] = "another-base"  # not the header's base: just entities
    assert smoke.lint(reopened, qid, entities=other_doc)["outcome"] == "pass"
    second = smoke.submit(reopened, smoke.candidate(reopened, 2))
    assert Linter(smoke.schema, store=store).lint(reopened, second)["outcome"] == "pass"  # the store resolves


def test_another_schema_raises_d009(smoke):
    q = smoke.create()
    qid = smoke.submit(q)
    other = data.load_json("fixture/fixture.relation-schema.json")
    other["label"] = "another schema"
    with pytest.raises(ValidationError) as exc:
        Linter(load_schema(other)).lint(q, qid)
    assert exc.value.codes == ("KHG-D009",) and q.state(qid) == "pending"


def test_lint_needs_a_pending_item(smoke, store):
    q, qid, _, _ = smoke.full(store)
    with pytest.raises(ValidationError) as exc:
        smoke.lint(q, qid)
    assert exc.value.codes == ("KHG-Q005",)
    with pytest.raises(ValidationError) as exc:
        smoke.lint(q, "q:p2-smoke.000002")
    assert exc.value.codes == ("KHG-Q007",)


def test_a_missing_required_role_is_a_warning_and_the_item_needs_review(smoke, store):
    rec = copy.deepcopy(smoke.king14)
    rec["bindings"] = [b for b in rec["bindings"] if b["role"] != "position"]
    for e in rec["evidence"]:
        e["supports"] = [x for x in e["supports"] if x != "b2"]
        e.pop("event_hash", None)
    q = smoke.create()
    qid = smoke.submit(q, smoke.candidate(q, 1, rec))
    entry = Linter(smoke.schema).lint(q, qid)
    assert (entry["outcome"], entry["state_after"]) == ("warn", "needs_review")
    assert _codes(entry) == [("KHG-S003", "warning", "/payload")]
    with pytest.raises(ValidationError) as exc:  # a warning on the candidate, an error on the asserted record
        smoke.accept(q, qid, store, id="f:king-14-partial")
    assert exc.value.codes == ("KHG-S003",) and q.state(qid) == "needs_review"
    assert store.get("f:king-14-partial") is None


@pytest.mark.parametrize(("change", "kw", "codes"), [
    (lambda p: dict(p, rank="top"), {}, [("KHG-C002", "/payload/rank")]),
    (lambda p: p, {"doc": {"doc_id": "doc:louis-bio", "doc_sha256": "sha256:" + "2" * 64}},
     [("KHG-Q009", "/payload/evidence/1/source")]),
    (lambda p: dict(p, evidence=[p["evidence"][0], dict(p["evidence"][1], event_hash="sha256:" + "4" * 64)]), {},
     [("KHG-Q010", "/payload/evidence/1/event_hash")]),
    (lambda p: dict(p, bindings=[b if b["role"] != "replaces" else dict(b, value={"entity": "ex:LouisXII"})
                                 for b in p["bindings"]]), {},
     [("KHG-Q010", "/payload/evidence/1/event_hash"), ("KHG-Q011", "/payload/bindings/3/value")]),
    (lambda p: dict(p, bindings=p["bindings"] + [{"bid": "b6", "role": "holder",
                                                  "value": {"entity": "ex:Mazarin"}}]), {},
     [("KHG-S004", "/payload"), ("KHG-Q010", "/payload/evidence/1/event_hash")]),
])
def test_each_error_rejects_the_item(smoke, change, kw, codes):
    q = smoke.create()
    qid = smoke.submit(q, change(smoke.candidate(q)), **kw)
    entry = smoke.lint(q, qid)
    assert entry["outcome"] == "fail" and q.state(qid) == "rejected"
    assert [(c, p) for c, s, p in _codes(entry) if s == "error"] == codes


def test_spans_are_checked_against_the_document_texts(smoke):
    rec = copy.deepcopy(smoke.king14)
    rec["evidence"][1]["selectors"][1]["start"] = 1  # the position selector no longer selects the quote
    rec["evidence"][1].pop("event_hash")
    q = smoke.create()
    flat = {k: v["text"] for k, v in TEXTS["texts"].items()}
    for texts in (TEXTS, flat, data.path("fixture/fixture.doc-texts.json")):
        qid = smoke.submit(q, smoke.candidate(q, len(q.qids) + 1, rec))
        entry = smoke.lint(q, qid, doc_texts=texts)
        assert [c for c, s, _ in _codes(entry) if s == "error"] == ["KHG-S021"]
    qid = smoke.submit(q, smoke.candidate(q, len(q.qids) + 1, rec))
    assert smoke.lint(q, qid)["outcome"] == "pass"  # no text, no span check


def test_fact_values_resolve_from_the_store(smoke, schema):
    fixture = data.load_json("fixture/fixture.c1.json")
    claim = copy.deepcopy(next(r for r in fixture["records"] if r["id"] == "f:claim-1"))
    full = MemoryStore(schema, clock=ScenarioClock())
    full.load(fixture)
    q = smoke.create()
    good = smoke.submit(q, smoke.candidate(q, 1, claim))
    assert smoke.lint(q, good, store=full)["outcome"] == "pass"
    claim["bindings"][0]["value"] = {"fact": "f:king-14"}  # a position_held fact where born_in is required
    wrong = smoke.submit(q, smoke.candidate(q, 2, claim))
    assert [c for c, s, _ in _codes(smoke.lint(q, wrong, store=full)) if s == "error"] == ["KHG-S005"]
    unresolved = smoke.submit(q, smoke.candidate(q, 3, claim))
    assert smoke.lint(q, unresolved)["outcome"] == "pass"  # a fact the linter cannot resolve is not judged


def test_the_linter_takes_its_schema_as_a_document_or_a_path(smoke):
    q = smoke.create()
    qid = smoke.submit(q)
    path = data.path("fixture/fixture.relation-schema.json")
    for s in (data.load_json("fixture/fixture.relation-schema.json"), path, str(path)):
        assert Linter(s).schema.sha256 == smoke.schema.sha256
    assert Linter(path).lint(q, qid)["outcome"] == "pass"
    with pytest.raises(TypeError):
        Linter(smoke.schema, entities=42)
    with pytest.raises(TypeError):
        Linter(smoke.schema, doc_texts=["doc:louis-bio"])


def test_the_lint_entry_keeps_the_order_and_text_of_the_findings(smoke):
    rec = copy.deepcopy(smoke.king14)
    rec["rank"] = "top"
    rec["bindings"][1]["value"] = {"entity": "ex:Nobody"}
    rec["evidence"][1].pop("event_hash")
    q = smoke.create()
    qid = smoke.submit(q, smoke.candidate(q, 1, rec))
    entry = smoke.lint(q, qid)
    assert [f["code"] for f in entry["findings"]] == ["KHG-C002", "KHG-Q011"]
    assert entry["findings"][1]["message"].startswith("ex:Nobody")
    assert record.normalize(q.item(qid)["payload"]) == q.item(qid)["payload"]
