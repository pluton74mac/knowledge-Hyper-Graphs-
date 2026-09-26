"""P2 ruling 23: C3 ``khg-queue`` 1.1.0 (DESIGN §7, §8.1), P9's proposals (P9 DESIGN §3.8, §10 D5 a and c; P9
ruling 5).

- **(a) The recorded reading of queue validity.** A queue records wrong candidates on purpose, and items are never
  edited. ``validate_queue`` runs layers C and S on every payload, so a queue that once rejected a malformed
  candidate never validated again. Now a C or S error on the payload of a **rejected** item, whose lint entry lists
  a finding with the same code at the same path (relative to the item) as an error, is reported with severity
  ``info`` and a message naming that lint entry: the queue is valid. Every other finding keeps its severity: an
  error the lint did not record, one on an item that is not rejected, and every J, V, Q and D finding.
- **(c) Q013**, a check of the linter's structural rule set 1.1.0: an evidence record's quote selector without a
  position selector escaped S021; when the linter has the document text, a quote whose prefix, exact text and suffix
  do not occur in it is Q013, an error, so the candidate is rejected. ``validate_queue`` does not repeat the check,
  so no queue file that was valid becomes invalid.
- The linter is ``khg-lint`` 1.1.0 and its rule set ``structural`` 1.1.0; queue files keep the stamp
  ``khg-queue/1.0.0``, and the reader takes ``khg-queue/1.0.x`` and ``1.1.x``.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

import khg_contracts
from khg_contracts import data, queue as queue_pkg
from khg_contracts.queue import Linter
from khg_contracts.queue import model as M
from khg_contracts.store import MemoryStore, ScenarioClock, memory_factory
from khg_contracts.validate import ENGINES, registry, run, validate_queue

TEXTS = data.load_json("fixture/fixture.doc-texts.json")
LOUIS_TEXT = TEXTS["texts"]["doc:louis-bio"]["text"]
LINT_AT = "2026-10-01T00:00:05Z"


def edited(smoke, queue, seq: int, change) -> dict[str, Any]:
    """A candidate of ``f:king-14`` after ``change(record)``, with its event hashes recomputed."""
    rec = copy.deepcopy(smoke.king14)
    change(rec)
    for e in rec["evidence"]:
        e.pop("event_hash", None)
    return smoke.candidate(queue, seq, rec)


def wrong_holder(rec: dict[str, Any]) -> None:
    """Paris as the holder: a Place where a Person is required (S005)."""
    next(b for b in rec["bindings"] if b["role"] == "holder")["value"] = {"entity": "ex:Paris"}


def quote_only(exact: str, prefix: str | None = None, suffix: str | None = None):
    """e2 with one quote selector and no position selector."""
    def change(rec: dict[str, Any]) -> None:
        quote: dict[str, Any] = {"type": "quote", "exact": exact}
        if prefix is not None:
            quote["prefix"] = prefix
        if suffix is not None:
            quote["suffix"] = suffix
        next(e for e in rec["evidence"] if e["id"] == "e2")["selectors"] = [quote]
    return change


def holder_at(payload: dict[str, Any]) -> str:
    return f"/bindings/{next(i for i, b in enumerate(payload['bindings']) if b['role'] == 'holder')}"


def result(q, smoke, **kw: Any) -> dict[str, Any]:
    return validate_queue(q.path, schema=smoke.schema, bases=[smoke.base], **kw)


def plain(findings: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    return [(f["code"], f["severity"], f["path"]) for f in findings]


# ------------------------------------------------------------------------------------------------ versions


def test_the_versions():
    assert khg_contracts.CONTRACTS["khg-queue"] == "1.1.0"
    assert M.FORMAT == "khg-queue/1.0.0"  # the stamp queue files keep: 1.1 changes no line of the format
    assert dict(M.LINTER) == {"type": "linter", "id": "khg-lint", "version": "1.1.0"}
    assert dict(M.RULE_SET) == {"id": "structural", "version": "1.1.0"}
    q013 = registry()["KHG-Q013"]
    assert (q013.layer, q013.severity, q013.status) == ("Q", "error", "active")


@pytest.mark.parametrize(("stamp", "ok"), [("khg-queue/1.1.0", True), ("khg-queue/1.1.4", True),
                                           ("khg-queue/1.0.0", True), ("khg-queue/1.2.0", False)])
def test_the_reader_takes_1_0_and_1_1(stamp, ok, smoke):
    lines = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    lines[0]["format"] = stamp
    rep = run(lines, kind="queue", schema=smoke.schema, bases=[smoke.base])
    assert rep.ok is ok and ([f["code"] for f in rep.findings] == ["KHG-V001"]) is (not ok)


# ------------------------------------------------------------------------------------------------ (a) recorded


@pytest.mark.parametrize("engine", ENGINES)
def test_a_rejected_candidate_whose_lint_recorded_the_error_is_valid(smoke, engine):
    q = smoke.create()
    payload = edited(smoke, q, 1, wrong_holder)
    qid = smoke.submit(q, payload)
    entry = smoke.lint(q, qid)
    at = holder_at(payload)
    assert plain(entry["findings"]) == [("KHG-S005", "error", f"/payload{at}")]
    assert q.state(qid) == "rejected"
    out = result(q, smoke, engine=engine)
    assert out["ok"] is True
    assert plain(out["findings"]) == [("KHG-S005", "info", f"/lines/1/payload{at}")]
    assert "recorded by the lint entry at /lines/2" in out["findings"][0]["message"]


def test_a_c_error_recorded_at_lint_is_read_the_same_way(smoke):
    q = smoke.create()
    qid = smoke.submit(q, edited(smoke, q, 1, lambda r: r.update(rank="high")))
    assert plain(smoke.lint(q, qid)["findings"]) == [("KHG-C002", "error", "/payload/rank")]
    out = result(q, smoke)
    assert out["ok"] and plain(out["findings"]) == [("KHG-C002", "info", "/lines/1/payload/rank")]


def test_an_error_the_lint_did_not_record_stays_an_error(smoke):
    """Rejected without a lint entry: nothing recorded the error."""
    q = smoke.create()
    payload = edited(smoke, q, 1, wrong_holder)
    qid = smoke.submit(q, payload)
    q.reject(qid, actor="curator:x", reason="not linted", at=LINT_AT)
    out = result(q, smoke)
    assert out["ok"] is False
    assert plain(out["findings"]) == [("KHG-S005", "error", f"/lines/1/payload{holder_at(payload)}")]


def test_a_recorded_error_needs_the_item_rejected(smoke):
    """A lint entry that records the error but leaves the item open (a hand-written log): the error stays an error
    until the item is rejected. The fold refuses an accept while the lint has an open error (Q005)."""
    q = smoke.create()
    payload = edited(smoke, q, 1, wrong_holder)
    qid = smoke.submit(q, payload)
    at = holder_at(payload)
    found = [{"code": "KHG-S005", "severity": "error", "path": f"/payload{at}", "message": "a Place is no Person"}]
    q._log(qid, "lint", M.LINTER, "automatic", at=LINT_AT, state_after="needs_review", rule_set=dict(M.RULE_SET),
           findings=found, outcome="fail")
    assert plain(result(q, smoke)["findings"]) == [("KHG-S005", "error", f"/lines/1/payload{at}")]
    q.reject(qid, actor="curator:x", reason="the holder is a place", at="2026-10-01T00:00:06Z")
    out = result(q, smoke)
    assert out["ok"] and plain(out["findings"]) == [("KHG-S005", "info", f"/lines/1/payload{at}")]


@pytest.mark.parametrize(("code", "path", "severity"), [
    ("KHG-S005", "/payload/bindings/0", "error"),   # another binding
    ("KHG-S004", None, "error"),                    # another code at the same path
    ("KHG-S005", None, "warning"),                  # recorded, but not as an error
])
def test_the_lint_must_record_the_same_code_at_the_same_path_as_an_error(smoke, code, path, severity):
    q = smoke.create()
    payload = edited(smoke, q, 1, wrong_holder)
    qid = smoke.submit(q, payload)
    at = holder_at(payload)
    assert at != "/bindings/0"
    found = [{"code": code, "severity": severity, "path": path or f"/payload{at}", "message": "m"}]
    outcome, state = ("fail", "rejected") if severity == "error" else ("warn", "needs_review")
    q._log(qid, "lint", M.LINTER, "automatic", at=LINT_AT, state_after=state, rule_set=dict(M.RULE_SET),
           findings=found, outcome=outcome)
    if state != "rejected":
        q.reject(qid, actor="curator:x", reason="no", at="2026-10-01T00:00:06Z")
    out = result(q, smoke)
    assert out["ok"] is False
    assert plain(out["findings"]) == [("KHG-S005", "error", f"/lines/1/payload{at}")]


def test_a_run_that_stops_at_the_first_error_does_not_stop_at_a_recorded_one(smoke):
    q = smoke.create()
    qid = smoke.submit(q, edited(smoke, q, 1, wrong_holder))
    smoke.lint(q, qid)
    rep = run(q.path, kind="queue", schema=smoke.schema, bases=[smoke.base], stop="first")
    assert rep.ok and rep.stopped is None and [n for n, _ in rep.steps] == ["j", "v", "q", "c", "s", "d_container"]


def test_p9_s_case_an_accepted_and_a_rejected_candidate(smoke, schema):
    """The good candidate is accepted, the malformed one rejected at lint: the queue is valid and replays."""
    store = MemoryStore(schema, clock=ScenarioClock())
    store.load(smoke.base)
    q = smoke.create()
    good = smoke.submit(q)
    bad = smoke.submit(q, edited(smoke, q, 2, wrong_holder))
    smoke.lint(q, good)
    smoke.lint(q, bad)
    smoke.accept(q, good, store)
    assert (q.state(good), q.state(bad)) == ("accepted", "rejected")
    out = result(q, smoke)
    assert out["ok"] and [f["severity"] for f in out["findings"]] == ["info"]
    replayed = queue_pkg.replay(q.path, schema=schema, factory=memory_factory, base=smoke.base)
    assert replayed["ok"] and len(replayed["decisions"]) == 1


def test_the_recorded_reading_changes_no_valid_queue():
    """The packaged smoke queue is valid as before, with no finding."""
    lines = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    base = data.load_json("fixture/smoke-base.c1.json")
    schema = data.load_json("fixture/fixture.relation-schema.json")
    for engine in ENGINES:
        assert validate_queue(lines, schema=schema, bases=[base], engine=engine) == {"ok": True, "findings": []}


# ------------------------------------------------------------------------------------------------ (c) Q013


def lint_quote(smoke, change, **linter: Any) -> tuple[dict[str, Any], Any, str]:
    q = smoke.create()
    qid = smoke.submit(q, edited(smoke, q, 1, change))
    return smoke.lint(q, qid, **linter), q, qid


def test_an_unlocatable_quote_without_a_position_is_q013(smoke):
    entry, q, qid = lint_quote(smoke, quote_only("Louis XIV was born in Paris"), doc_texts=TEXTS)
    assert plain(entry["findings"]) == [("KHG-Q013", "error", "/payload/evidence/1/selectors/0")]
    assert (entry["outcome"], q.state(qid)) == ("fail", "rejected")
    assert (entry["actor"], entry["rule_set"]) == (dict(M.LINTER), dict(M.RULE_SET))


@pytest.mark.parametrize(("exact", "prefix", "suffix", "found"), [
    ("Louis XIV succeeded his father Louis XIII", None, None, False),
    ("Louis XIV succeeded his father Louis XIII", "", " as King of ", False),
    ("his father", "succeeded ", " Louis XIII", False),
    ("his father", "preceded ", None, True),          # the prefix is not before it
    ("his father", None, " Louis XIV", True),         # nor the suffix after it
    ("King of France on 14 May 1643.", None, None, False),
    ("King of France on 14 May 1643..", None, None, True),
    ("louis xiv", None, None, True),                  # code points, not case-folded
])
def test_the_quote_with_its_prefix_and_suffix_must_occur_in_the_text(smoke, exact, prefix, suffix, found):
    assert (((prefix or "") + exact + (suffix or "")) in LOUIS_TEXT) is not found
    entry, _, _ = lint_quote(smoke, quote_only(exact, prefix, suffix), doc_texts=TEXTS)
    want = [("KHG-Q013", "error", "/payload/evidence/1/selectors/0")] if found else []
    assert plain(entry["findings"]) == want


def test_without_the_text_nothing_is_judged(smoke):
    entry, q, qid = lint_quote(smoke, quote_only("Louis XIV was born in Paris"))
    assert entry["findings"] == [] and q.state(qid) == "linted"


def test_a_quote_with_a_position_is_s021_s_as_before(smoke):
    def change(rec: dict[str, Any]) -> None:
        e2 = next(e for e in rec["evidence"] if e["id"] == "e2")
        e2["selectors"][0]["exact"] = "Louis XIV was born in Paris"
    entry, _, _ = lint_quote(smoke, change, doc_texts=TEXTS)
    assert plain(entry["findings"]) == [("KHG-S021", "error", "/payload/evidence/1")]


def test_a_text_of_another_revision_is_not_the_evidence_s_text(smoke):
    """As S021: the text must hash to the evidence's doc_sha256."""
    other = {"doc:louis-bio": "Louis XIV was born in Paris."}
    entry, _, _ = lint_quote(smoke, quote_only("Louis XIV was born in Paris"), doc_texts=other)
    assert entry["findings"] == []


def test_validate_queue_does_not_repeat_q013(smoke, schema):
    """Linted without the text and accepted, the unlocatable quote stays in a valid queue: 1.1 invalidates no file."""
    store = MemoryStore(schema, clock=ScenarioClock())
    store.load(smoke.base)
    entry, q, qid = lint_quote(smoke, quote_only("Louis XIV was born in Paris"))
    assert entry["outcome"] == "pass"
    smoke.accept(q, qid, store)
    assert result(q, smoke, doc_texts=TEXTS) == {"ok": True, "findings": []}


def test_q013_is_a_coverage_exception_of_the_malformed_cases():
    cases = data.load_json("malformed-cases.json")
    assert set(cases["coverage_exceptions"]) == {"KHG-D019", "KHG-Q013"}
    assert "Linter" in cases["coverage_exceptions"]["KHG-Q013"]
    assert "KHG-Q013" not in {c["code"] for c in cases["cases"]}


def test_the_linter_class_is_unchanged_in_its_call(smoke):
    """``Linter(schema, *, store=None, entities=None, doc_texts=None)`` as in 1.0."""
    import inspect
    params = inspect.signature(Linter).parameters
    assert list(params) == ["schema", "store", "entities", "doc_texts"]
