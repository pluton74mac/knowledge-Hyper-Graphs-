"""W9: the ``Queue`` handle (DESIGN §7): ``create``, ``open``, ``submit``, ``accept``, ``reject``, ``flag``,
``verdict`` and ``withdraw``.

Every line is canonical JSON, checked against the queue schema and the fold before it is written; a refused call
writes nothing. ``accept`` writes the payload with its id replaced and status asserted, with the item's entities, in
one atomic ``put`` at ``at``, and logs ``before``, ``after`` and ``decision_hash``.
"""
from __future__ import annotations

import copy
import os
import re

import pytest

from khg_contracts import data, jsonio, record
from khg_contracts.errors import ConcurrencyError, ValidationError
from khg_contracts.queue import Linter, Queue, make_candidate
from khg_contracts.queue.lines import dump_line
from khg_contracts.queue.model import TIMESTAMP_PATTERN
from khg_contracts.schema import load_schema
from khg_contracts.store import MemoryStore, ScenarioClock
from khg_contracts.validate import validate_queue

SMOKE = data.path("fixture/smoke-queue.khg-queue.jsonl")


def _codes(exc_info):
    return set(exc_info.value.codes)


def _size(q):
    return os.path.getsize(q.path)


# ------------------------------------------------------------------------------------------------ create and open


def test_create_writes_the_header_line(smoke, smoke_lines):
    q = smoke.create()
    assert q.header == smoke_lines[0] and q.queue_id == "p2-smoke" and q.qids == ()
    assert open(q.path, "rb").read() == dump_line(smoke_lines[0]).encode("utf-8")
    assert q.base == smoke.base and q.schema.sha256 == smoke.schema.sha256
    assert os.fspath(q) == q.path and "p2-smoke" in repr(q)
    by_path = smoke.create(base=data.path("fixture/smoke-base.c1.json"))
    assert by_path.header == smoke_lines[0]


def test_create_without_a_base_or_a_time(smoke, schema):
    q = Queue.create(smoke.path(), queue_id="run-1.o1", schema=schema)
    assert "base" not in q.header and q.base is None
    assert re.fullmatch(TIMESTAMP_PATTERN, q.header["created_at"])
    assert q.header["schema"] == {"id": "p2-gate", "version": "1.0.0", "sha256": schema.sha256}


def test_create_refuses(smoke, schema):
    q = smoke.create()
    with pytest.raises(FileExistsError):
        smoke.create(path=q.path)
    assert Queue.open(q.path, schema=schema).header == q.header  # the file is unchanged
    with pytest.raises(ValueError):
        Queue.create(smoke.path(), queue_id="p2 smoke", schema=schema)
    with pytest.raises(ValidationError) as exc:
        Queue.create(smoke.path(), queue_id="p2-smoke", schema=schema, created_at="yesterday")
    assert _codes(exc) == {"KHG-Q008"}
    bad = copy.deepcopy(smoke.base)
    bad["header"]["format"] = "khg-record/2.0.0"
    with pytest.raises(ValidationError) as exc:
        smoke.create(base=bad)
    assert _codes(exc) == {"KHG-V001"}
    with pytest.raises(TypeError):
        smoke.create(base=["not", "a", "container"])


def test_open_reads_the_smoke_queue(schema, smoke_lines):
    q = Queue.open(SMOKE, schema=schema)
    assert q.qids == ("q:p2-smoke.000001",) and q.state("q:p2-smoke.000001") == "accepted"
    assert q.item("q:p2-smoke.000001") == smoke_lines[1] and q.header == smoke_lines[0] and q.base is None
    with pytest.raises(ValidationError) as exc:
        q.state("q:p2-smoke.000002")
    assert _codes(exc) == {"KHG-Q007"}


def test_open_checks_the_base_and_the_schema_pin(smoke, schema, base):
    assert Queue.open(SMOKE, schema=schema, base=base).base == base
    changed = copy.deepcopy(base)
    changed["records"] = changed["records"][1:]
    with pytest.raises(ValidationError) as exc:
        Queue.open(SMOKE, schema=schema, base=changed)
    assert _codes(exc) == {"KHG-Q012"}
    plain = Queue.create(smoke.path(), queue_id="p2-smoke", schema=schema, created_at=smoke.TIMES["created"])
    with pytest.raises(ValidationError) as exc:
        Queue.open(plain.path, schema=schema, base=base)
    assert _codes(exc) == {"KHG-Q012"}
    other = data.load_json("fixture/fixture.relation-schema.json")
    other["label"] = "another schema"
    with pytest.raises(ValidationError) as exc:
        Queue.open(SMOKE, schema=load_schema(other))
    assert _codes(exc) == {"KHG-D009"}


def _write(tmp_path, lines, *, raw=None):
    p = tmp_path / "x.khg-queue.jsonl"
    p.write_bytes(raw if raw is not None else "".join(dump_line(x) for x in lines).encode("utf-8"))
    return p


@pytest.mark.parametrize(("change", "codes"), [
    (lambda ls: ls[1:], {"KHG-Q008"}),
    (lambda ls: ls + [ls[0]], {"KHG-Q008"}),
    (lambda ls: [ls[0], ls[1], dict(ls[2], state_before="linted"), ls[3]], {"KHG-Q005"}),
    (lambda ls: [ls[0], ls[1], ls[3]], {"KHG-Q007"}),
    (lambda ls: [ls[0], dict(ls[1], item_kind="merge_proposal")] + ls[2:], {"KHG-Q003", "KHG-Q007"}),
    (lambda ls: [dict(ls[0], format="khg-queue/1.1.0")] + ls[1:], {"KHG-V001"}),
])
def test_open_refuses_a_file_with_structural_errors(tmp_path, schema, smoke_lines, change, codes):
    with pytest.raises(ValidationError) as exc:
        Queue.open(_write(tmp_path, change(copy.deepcopy(smoke_lines))), schema=schema)
    assert _codes(exc) == codes


def test_open_refuses_a_file_that_does_not_parse(tmp_path, schema):
    duplicate = b'{"kind": "queue-header", "kind": 1}\n'
    for raw, code in ((b"", "KHG-J001"), (duplicate, "KHG-J003"), (b"[1]\n", "KHG-J007")):
        with pytest.raises(ValidationError) as exc:
            Queue.open(_write(tmp_path, [], raw=raw), schema=schema)
        assert exc.value.codes == (code,)


def test_appending_to_an_opened_file_continues_its_numbering(tmp_path, smoke, smoke_lines):
    raw = "".join(dump_line(x) for x in smoke_lines).rstrip("\n").encode("utf-8")  # no final newline
    q = Queue.open(_write(tmp_path, [], raw=raw), schema=smoke.schema)
    qid = smoke.submit(q, smoke.candidate(q, seq=2))
    assert qid == "q:p2-smoke.000002"
    entry = q.flag(qid, actor="curator:smoke", reason="check the dates", at="2026-10-01T00:01:00Z")
    assert entry["lid"] == "l:p2-smoke.000003" and entry["parent"] is None
    back = Queue.open(q.path, schema=smoke.schema)
    assert back.qids == ("q:p2-smoke.000001", "q:p2-smoke.000002") and back.state(qid) == "needs_review"
    assert open(q.path, "rb").read().count(b"\n") == 6


# ------------------------------------------------------------------------------------------------ submit


def test_submit_appends_the_smoke_item(smoke, smoke_lines):
    q = smoke.create()
    qid = smoke.submit(q)
    assert qid == "q:p2-smoke.000001" and q.qids == (qid,) and q.state(qid) == "pending"
    assert q.item(qid) == smoke_lines[1]
    assert open(q.path, "rb").read() == "".join(dump_line(x) for x in smoke_lines[:2]).encode("utf-8")


def test_submit_numbers_items_and_keeps_entities(smoke, schema):
    q = smoke.create(base=None)
    henri = {"kind": "entity", "id": "ex:Henri", "types": ["Person"], "label": "Henri"}
    rec = copy.deepcopy(smoke.king14)
    rec["bindings"][1]["value"] = {"entity": "ex:Henri"}  # holder
    first = smoke.submit(q, smoke.candidate(q, 1, rec), entities=[henri])
    second = smoke.submit(q, smoke.candidate(q, 2), at=None)
    assert (first, second) == ("q:p2-smoke.000001", "q:p2-smoke.000002")
    assert q.item(first)["entities"] == [henri] and "entities" not in q.item(second)
    assert q.item(first)["keys"] == {"content_key": record.content_key(rec, schema),
                                     "core_key": record.core_key(rec, schema),
                                     "key_digest": record.key_digest(rec, schema)}
    assert re.fullmatch(TIMESTAMP_PATTERN, q.item(second)["submitted_at"])


@pytest.mark.parametrize(("change", "kw", "codes"), [
    (lambda p: dict(p, id="cand:other.000001"), {}, {"KHG-Q002"}),
    (lambda p: dict(p, id="f:king-14"), {}, {"KHG-Q002"}),
    (lambda p: dict(p, status="asserted"), {}, {"KHG-Q002"}),
    (lambda p: {k: v for k, v in p.items() if k != "evidence"}, {}, {"KHG-Q001"}),
    (lambda p: p, {"run": {"run_id": "fixture-run-1", "position": 0}}, {"KHG-Q001"}),
    (lambda p: p, {"doc": {"doc_id": "doc:louis-bio"}}, {"KHG-Q001"}),
    (lambda p: p, {"submitted_by": "p2-fixture-extractor"}, {"KHG-Q001"}),
    (lambda p: p, {"entities": [{"kind": "entity", "id": "ex: x", "types": ["Person"]}]}, {"KHG-C011"}),
    (lambda p: p, {"at": "now"}, {"KHG-Q008"}),
    (lambda p: dict(p, relation="reigned"), {}, {"KHG-S001"}),
    (lambda p: dict(p, bindings="b1 b2"), {}, {"KHG-C010"}),
])
def test_submit_refuses_an_invalid_item_and_writes_nothing(smoke, change, kw, codes):
    q = smoke.create()
    size = _size(q)
    with pytest.raises(ValidationError) as exc:
        smoke.submit(q, change(smoke.candidate(q)), **kw)
    assert _codes(exc) == codes
    assert _size(q) == size and q.qids == ()


def test_submit_refuses_what_is_not_a_record(smoke):
    q = smoke.create()
    with pytest.raises(ValidationError) as exc:
        q.submit(["not a record"], run=smoke.RUN, doc=smoke.DOC, submitted_by=smoke.SUBMITTED_BY)  # type: ignore
    assert _codes(exc) == {"KHG-Q008"}


# ------------------------------------------------------------------------------------------------ accept


def test_the_smoke_accept_writes_king_14_and_logs_the_decision(smoke, store, smoke_lines, king14):
    q, qid, lint, entry = smoke.full(store)
    assert lint == smoke_lines[2] and entry == smoke_lines[3]
    assert entry["decision_hash"] == smoke.DECISION_HASH and q.state(qid) == "accepted"
    stored = store.get("f:king-14")
    assert stored["version"] == 1 and stored["recorded_at"] == smoke.TIMES["accept"]
    assert stored["recorded_by"] == "curator:smoke"
    assert record.decision_view(stored) == record.decision_view(king14)  # the fixture record: nothing else changed
    assert open(q.path, "rb").read() == SMOKE.read_bytes()


def test_the_decision_hash_does_not_depend_on_the_clock(smoke, schema, base):
    hashes = set()
    for start, at in (("2026-10-01T00:00:00Z", None), ("2031-01-01T00:00:00Z", "2031-01-01T08:00:00.25Z")):
        s = MemoryStore(schema, clock=ScenarioClock(start))
        s.load(base)
        q = smoke.create()
        qid = smoke.submit(q)
        smoke.lint(q, qid)
        entry = smoke.accept(q, qid, s, at=at, actor={"type": "agent", "id": "p9-curator", "version": "2"})
        assert entry["mode"] == "automatic" and entry["at"] == s.get("f:king-14")["recorded_at"]
        hashes.add(entry["decision_hash"])
    assert hashes == {smoke.DECISION_HASH}


def test_accept_writes_the_item_entities_in_the_same_put(smoke, store, schema):
    q = smoke.create()
    henri = {"kind": "entity", "id": "ex:Henri", "types": ["Person"], "label": "Henri"}
    louis = next(r for r in smoke.base["records"] if r["id"] == "ex:LouisXIV")
    rec = copy.deepcopy(smoke.king14)
    rec["bindings"][3]["value"] = {"entity": "ex:Henri"}  # replaces
    rec["evidence"] = rec["evidence"][:1]
    qid = smoke.submit(q, smoke.candidate(q, 1, rec), entities=[henri, louis])
    smoke.lint(q, qid)
    entry = smoke.accept(q, qid, store, id="f:king-14b")
    assert entry["before"] == [{"id": "ex:LouisXIV", "version": 1}]  # read: the ids the put names, as they were
    assert entry["after"] == [{"id": "ex:Henri", "version": 1}, {"id": "f:king-14b", "version": 1}]  # written
    assert store.get("ex:Henri")["recorded_at"] == store.get("f:king-14b")["recorded_at"] == entry["at"]
    views = [{"id": w["id"], "version": 1, "record": record.decision_view(store.get(w["id"]))} for w in entry["after"]]
    assert entry["decision_hash"] == jsonio.digest("khg-decision/1", views)


def test_accept_refuses_a_move_the_fold_forbids_and_writes_nothing(smoke, store):
    q = smoke.create()
    qid = smoke.submit(q)
    size = _size(q)
    with pytest.raises(ValidationError) as exc:
        smoke.accept(q, qid, store)  # still pending
    assert _codes(exc) == {"KHG-Q005"}
    assert store.get("f:king-14") is None and _size(q) == size
    with pytest.raises(ValidationError) as exc:
        smoke.accept(q, "q:p2-smoke.000009", store)
    assert _codes(exc) == {"KHG-Q007"}
    smoke.lint(q, qid)
    for kw, code in (({"reason": ""}, "KHG-Q008"), ({"id": ""}, "KHG-C010"), ({"actor": {"type": "person"}},
                                                                                "KHG-Q008")):
        with pytest.raises(ValidationError) as exc:
            smoke.accept(q, qid, store, **kw)
        assert exc.value.codes == (code,)
    with pytest.raises(TypeError):
        smoke.accept(q, qid, store, actor=42)
    assert store.get("f:king-14") is None and q.state(qid) == "linted"


def test_a_store_error_propagates_and_nothing_is_logged(smoke, schema):
    empty = MemoryStore(schema, clock=ScenarioClock())  # without the base: the entities are missing
    q = smoke.create()
    qid = smoke.submit(q)
    smoke.lint(q, qid)
    size = _size(q)
    with pytest.raises(ValidationError) as exc:
        smoke.accept(q, qid, empty)
    assert "KHG-D002" in exc.value.codes
    assert _size(q) == size and q.state(qid) == "linted" and empty.get("f:king-14") is None


def test_a_second_accept_of_one_item_is_q005(smoke, store):
    q, qid, _, _ = smoke.full(store)
    with pytest.raises(ValidationError) as exc:
        smoke.accept(q, qid, store, at="2026-10-01T00:00:09Z")
    assert _codes(exc) == {"KHG-Q005"}


# ------------------------------------------------------------------------------------------------ the other decisions


def test_flag_reject_and_withdraw_move_the_item(smoke, store):
    q = smoke.create()
    a, b, c = (smoke.submit(q, smoke.candidate(q, n)) for n in (1, 2, 3))
    e = q.flag(a, actor="curator:smoke", reason="two dates to check")
    assert (e["action"], e["state_before"], e["state_after"], e["mode"]) == ("flag", "pending", "needs_review",
                                                                              "manual")
    assert re.fullmatch(TIMESTAMP_PATTERN, e["at"]) and e["actor"] == {"type": "person", "id": "curator:smoke"}
    assert smoke.accept(q, a, store)["state_before"] == "needs_review"
    smoke.lint(q, b)
    assert q.reject(b, actor="curator:smoke", reason="a duplicate of the accepted item")["state_after"] == "rejected"
    bot = {"type": "agent", "id": "p9-extractor", "version": "1.0.0"}
    w = q.withdraw(c, actor=bot, reason="the run was cancelled", at="2026-10-01T00:02:00Z")
    assert (w["mode"], w["actor"], w["at"]) == ("automatic", bot, "2026-10-01T00:02:00Z")
    assert [q.state(x) for x in (a, b, c)] == ["accepted", "rejected", "withdrawn"]
    for decide, qid in ((q.withdraw, b), (q.reject, c), (q.flag, a)):
        with pytest.raises(ValidationError) as exc:
            decide(qid, actor="curator:smoke", reason="again")
        assert _codes(exc) == {"KHG-Q005"}
    with pytest.raises(ValidationError) as exc:
        q.reject(a, actor="curator:smoke", reason="")
    assert "KHG-Q008" in _codes(exc)
    assert validate_queue(q, schema=smoke.schema, bases=[smoke.base])["ok"]


def _verdict(**kw):
    v = {"evidence_id": "e2", "label": "correct",
         "bindings": [{"role": "holder", "position": None, "value": {"entity": "ex:LouisXIV"}, "bid": "b1",
                       "label": "correct"},
                      {"role": "replaces", "position": None, "value": {"entity": "ex:LouisXIII"}, "label": "correct"}]}
    v.update(kw)
    return v


def test_a_verdict_is_completed_from_the_item_and_leaves_the_state(smoke, store, smoke_lines):
    q, qid, _, _ = smoke.full(store)
    e = q.verdict(qid, actor="curator:smoke", verdict=_verdict(), at="2026-10-01T00:01:00Z")
    item = smoke_lines[1]
    assert e["verdict"] == dict(_verdict(), core_key=item["keys"]["core_key"],
                                event_hash=item["payload"]["evidence"][1]["event_hash"], missing=[])
    assert (e["state_before"], e["state_after"], q.state(qid)) == ("accepted", "accepted", "accepted")
    missing = q.verdict(qid, actor="curator:smoke", verdict={"evidence_id": "e2", "label": "missing_participant",
                                                            "missing": [{"role": "position"}]})
    assert missing["verdict"]["bindings"] == [] and missing["parent"] == e["lid"]
    assert validate_queue(q, schema=smoke.schema, bases=[smoke.base])["ok"]


@pytest.mark.parametrize(("verdict", "codes"), [
    (_verdict(core_key="sha256:" + "3" * 64), {"KHG-Q010"}),
    (_verdict(event_hash="sha256:" + "4" * 64), {"KHG-Q010"}),
    (_verdict(evidence_id="e7"), {"KHG-Q008"}),
    (_verdict(evidence_id="e1"), {"KHG-Q008"}),  # curated evidence has no event hash to key a verdict
    (_verdict(label="other"), {"KHG-Q008"}),
    (_verdict(bindings=[{"role": "holder", "position": None, "value": {"entity": "ex:LouisXIII"}, "bid": "b1",
                         "label": "wrong_filler"}]), {"KHG-Q008"}),
    (_verdict(bindings=[{"role": "holder", "position": 2, "value": {"entity": "ex:LouisXIV"}, "label": "correct"}]),
     {"KHG-Q008"}),
])
def test_a_wrong_verdict_is_refused(smoke, store, verdict, codes):
    q, qid, _, _ = smoke.full(store)
    size = _size(q)
    with pytest.raises(ValidationError) as exc:
        q.verdict(qid, actor="curator:smoke", verdict=verdict)
    assert _codes(exc) == codes and _size(q) == size


def test_a_verdict_on_a_withdrawn_item_is_q005(smoke):
    q = smoke.create()
    qid = smoke.submit(q)
    q.withdraw(qid, actor="p2-fixture-extractor", reason="duplicate run")
    with pytest.raises(ValidationError) as exc:
        q.verdict(qid, actor="curator:smoke", verdict=_verdict())
    assert _codes(exc) == {"KHG-Q005"}
    with pytest.raises(TypeError):
        q.verdict(qid, actor="curator:smoke", verdict=["correct"])  # type: ignore[arg-type]


# ------------------------------------------------------------------------------------------------ one appender


def test_a_handle_refuses_to_append_after_another_one_did(smoke, schema):
    q = smoke.create()
    qid = smoke.submit(q)
    other = Queue.open(q.path, schema=schema)
    other.flag(qid, actor="curator:b", reason="look again")
    size = _size(q)
    with pytest.raises(ConcurrencyError) as exc:
        q.reject(qid, actor="curator:a", reason="wrong")
    assert exc.value.info["path"] == q.path and _size(q) == size
    with pytest.raises(ConcurrencyError):
        Linter(schema).lint(q, qid)
    fresh = Queue.open(q.path, schema=schema)
    assert fresh.state(qid) == "needs_review"
    assert fresh.reject(qid, actor="curator:a", reason="wrong")["parent"] == "l:p2-smoke.000001"


def test_make_candidate_and_submit_follow_the_p9_sequence(tmp_path, schema, base, king14):
    """§1.3, P9: create with an entity base, make a candidate, submit, lint with the base as entities."""
    q = Queue.create(tmp_path / "run-1.o1.khg-queue.jsonl", queue_id="run-1.o1", schema=schema, base=base)
    cand = make_candidate(king14, queue_id="run-1.o1", seq=1, schema=schema)
    e2 = cand["evidence"][1]["source"]
    qid = q.submit(cand, run={"run_id": "run-1", "order_id": "o1", "position": 1},
                   doc={"doc_id": e2["doc_id"], "doc_sha256": e2["doc_sha256"]}, submitted_by="p9-extractor/1.0.0")
    entry = Linter(schema, entities=base).lint(q, qid)
    assert qid == "q:run-1.o1.000001" and entry["outcome"] == "pass" and q.state(qid) == "linted"
