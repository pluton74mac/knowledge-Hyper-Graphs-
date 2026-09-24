"""W9: the state fold over a queue's log (DESIGN §7): the move table, Q005, Q007 and Q008.

``pending`` goes to ``linted``, ``needs_review`` or ``rejected``; ``linted`` to ``accepted``, ``rejected`` or
``needs_review``; ``needs_review`` to ``accepted`` or ``rejected``; any open state to ``withdrawn``; a verdict leaves
the state unchanged. A wrong ``state_before`` or a forbidden move is Q005 (the entry is folded, the state does not
move); an unknown target or a parent that is not the item's previous entry is Q007 (the entry is left out).
"""
from __future__ import annotations

import copy
import itertools

import pytest

from khg_contracts import data
from khg_contracts.queue.fold import Fold, check
from khg_contracts.queue.model import ACTIONS, LINT_STATES, MOVES, OPEN_STATES, STATES, cand_id, lid, qid, seq_of

LINES = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
HEADER, ITEM = LINES[0], LINES[1]
QID = ITEM["qid"]
EXTRA = {"lint": {"rule_set": {"id": "structural", "version": "1.0.0"}, "findings": [], "outcome": "pass"},
         "accept": {"reason": "r", "before": [], "after": [{"id": "f:x", "version": 1}],
                    "decision_hash": "sha256:" + "a" * 64},
         "reject": {"reason": "r"}, "flag": {"reason": "r"}, "withdraw": {"reason": "r"},
         "verdict": {"verdict": {"evidence_id": "e2", "core_key": ITEM["keys"]["core_key"],
                                 "event_hash": ITEM["payload"]["evidence"][1]["event_hash"], "label": "correct",
                                 "bindings": [], "missing": []}}}
#: The entries that bring the item from pending to each state.
PATHS = {"pending": [], "linted": [("lint", "pending", "linted")],
         "needs_review": [("flag", "pending", "needs_review")],
         "rejected": [("reject", "pending", "rejected")], "withdrawn": [("withdraw", "pending", "withdrawn")],
         "accepted": [("lint", "pending", "linted"), ("accept", "linted", "accepted")]}


class Log:
    """A queue of the smoke header and item, and entries appended with the right lids and parents."""

    def __init__(self) -> None:
        self.lines = [copy.deepcopy(HEADER), copy.deepcopy(ITEM)]
        self.last = None
        self.n = 0

    def entry(self, action, before, after, *, target=QID, parent="auto", **fields):
        self.n += 1
        e = {"kind": "log-entry", "lid": lid("p2-smoke", self.n), "parent": self.last if parent == "auto" else parent,
             "target": target, "action": action, "state_before": before, "state_after": after,
             "actor": {"type": "person", "id": "curator:t"}, "mode": "manual", "at": f"2026-10-01T00:01:{self.n:02d}Z"}
        e.update(copy.deepcopy(EXTRA.get(action, {})))
        e.update(fields)
        self.lines.append(e)
        return e

    def then(self, *steps):
        for action, before, after in steps:
            self.last = self.entry(action, before, after)["lid"]
        return self


def fold_codes(lines):
    fold = Fold()
    found = []
    for n, line in enumerate(lines):
        found += fold.feed(line, n)
    return fold, [(f["code"], f["path"]) for f in found]


def test_the_smoke_queue_folds_to_accepted_without_findings():
    fold, found = check(LINES)
    assert found == []
    assert fold.queue_id == "p2-smoke" and fold.header == HEADER
    assert list(fold.items) == [QID] and fold.state == {QID: "accepted"}
    assert fold.entries == {QID: [2, 3]} and fold.last == {QID: "l:p2-smoke.000002"}
    assert fold.lint_errors == {QID: False} and fold.verdicts == []
    assert [(n, e["action"]) for n, e in fold.accepts] == [(3, "accept")]
    assert (fold.item_seq, fold.entry_seq, fold.lines) == (1, 2, 4)


@pytest.mark.parametrize(("state", "action", "after"), list(itertools.product(STATES, ACTIONS, STATES)))
def test_the_move_table(state, action, after):
    log = Log().then(*PATHS[state])
    log.entry(action, state, after)
    fold, found = fold_codes(log.lines)
    allowed = after in MOVES[action].get(state, ())
    if allowed:
        assert found == [] and fold.state[QID] == after
    else:
        assert found == [("KHG-Q005", f"/lines/{len(log.lines) - 1}")] and fold.state[QID] == state
    assert fold.last[QID] == log.lines[-1]["lid"]  # a Q005 entry is still folded: the next one names it as parent


def test_the_move_table_is_the_design_s():
    assert {s for s, afters in MOVES["lint"].items() for _ in afters} == {"pending"}
    assert set(MOVES["lint"]["pending"]) == {"linted", "needs_review", "rejected"} == set(LINT_STATES.values())
    assert {s: set(a) for s, a in MOVES["accept"].items()} == {"linted": {"accepted"}, "needs_review": {"accepted"}}
    assert set(MOVES["reject"]) == set(OPEN_STATES) == set(MOVES["withdraw"])
    assert set(MOVES["flag"]) == {"pending", "linted"}
    assert all(MOVES["verdict"][s] == (s,) for s in MOVES["verdict"]) and "withdrawn" not in MOVES["verdict"]
    terminal = {"accepted", "rejected", "withdrawn"}
    assert all(not (terminal & set(MOVES[a])) for a in ACTIONS if a != "verdict")


def test_a_wrong_state_before_is_q005_and_the_state_holds():
    log = Log().then(("lint", "pending", "linted"))
    log.entry("accept", "pending", "accepted")  # MC167
    fold, found = fold_codes(log.lines)
    assert found == [("KHG-Q005", "/lines/3")] and fold.state[QID] == "linted" and fold.accepts == []


def test_an_accept_with_an_open_lint_error_is_q005():
    log = Log()
    log.last = log.entry("lint", "pending", "linted", findings=[
        {"code": "KHG-C002", "severity": "error", "path": "/payload/rank", "message": "rank"}])["lid"]
    log.entry("accept", "linted", "accepted")
    fold, found = fold_codes(log.lines)
    assert fold.lint_errors[QID] is True
    assert found == [("KHG-Q005", "/lines/3")] and fold.state[QID] == "linted"
    warned = Log()
    warned.last = warned.entry("lint", "pending", "needs_review", outcome="warn", findings=[
        {"code": "KHG-S003", "severity": "warning", "path": "/payload", "message": "a role is missing"}])["lid"]
    warned.entry("accept", "needs_review", "accepted")
    fold, found = fold_codes(warned.lines)
    assert found == [] and fold.state[QID] == "accepted" and fold.lint_errors[QID] is False


def test_an_unknown_target_or_a_wrong_parent_is_q007_and_left_out():
    log = Log().then(("lint", "pending", "linted"))
    log.entry("accept", "linted", "accepted", target="q:p2-smoke.000009")  # MC169
    fold, found = fold_codes(log.lines)
    assert found == [("KHG-Q007", "/lines/3/target")] and fold.state[QID] == "linted"
    assert fold.last[QID] == "l:p2-smoke.000001" and "l:p2-smoke.000002" not in fold.lids
    orphan = Log()
    orphan.entry("lint", "pending", "linted", parent="l:p2-smoke.000007")
    fold, found = fold_codes(orphan.lines)
    assert found == [("KHG-Q007", "/lines/2/parent")] and fold.state[QID] == "pending" and fold.last[QID] is None
    fork = Log().then(("lint", "pending", "linted"))
    fork.entry("reject", "linted", "rejected", parent=None)  # the item's first entry again
    fold, found = fold_codes(fork.lines)
    assert found == [("KHG-Q007", "/lines/3/parent")] and fold.state[QID] == "linted"


def test_the_entries_of_an_item_of_unknown_kind_are_q007():
    lines = [copy.deepcopy(x) for x in LINES]
    lines[1]["item_kind"] = "binding"  # MC164: the schema reports Q003, the fold leaves the item out
    fold, found = fold_codes(lines)
    assert fold.items == {} and found == [("KHG-Q007", "/lines/2/target"), ("KHG-Q007", "/lines/3/target")]


def test_an_entry_with_an_unknown_action_is_left_out():
    lines = [copy.deepcopy(x) for x in LINES]
    lines[2]["action"] = "auto_fix"  # the schema reports Q003
    fold, found = fold_codes(lines)
    assert found == [("KHG-Q007", "/lines/3/parent")] and fold.state[QID] == "pending"


def test_structural_violations_are_q008():
    fold, found = fold_codes(LINES[1:])
    assert found == []  # feed does not look for the header; check does (MC170)
    assert check(LINES[1:])[1] == [{"code": "KHG-Q008", "severity": "error", "layer": "Q", "path": "/lines/0",
                                    "message": "a queue file starts with its queue-header line"}]
    assert fold_codes(LINES + [copy.deepcopy(HEADER)])[1] == [("KHG-Q008", "/lines/4")]
    again = copy.deepcopy(ITEM)
    fold, found = fold_codes(LINES[:2] + [again] + LINES[2:])
    assert found == [("KHG-Q008", "/lines/2/qid")] and list(fold.items) == [QID] and fold.state[QID] == "accepted"
    twice = [copy.deepcopy(x) for x in LINES]
    twice[3]["lid"] = twice[2]["lid"]
    fold, found = fold_codes(twice)
    assert found == [("KHG-Q008", "/lines/3/lid")] and fold.state[QID] == "linted"


def test_ids_of_another_queue_are_q008_but_still_fold():
    lines = [copy.deepcopy(x) for x in LINES]
    for x in lines[2:]:
        x["target"] = "q:other.000001"
    lines[1]["qid"] = "q:other.000001"
    lines[2]["lid"], lines[3]["parent"] = "l:other.000001", "l:other.000001"
    fold, found = fold_codes(lines)
    assert found == [("KHG-Q008", "/lines/1/qid"), ("KHG-Q008", "/lines/2/lid")]
    assert fold.state == {"q:other.000001": "accepted"}
    for bad in (7, "p2 smoke"):  # no valid queue id: the schema reports the header, the fold judges no scope
        lines[0]["queue_id"] = bad
        fold, found = fold_codes(lines)
        assert found == [] and fold.queue_id is None


def test_sequence_numbers_and_scoped_ids():
    assert qid("p2-smoke", 1) == "q:p2-smoke.000001" and lid("p2-smoke", 12) == "l:p2-smoke.000012"
    assert cand_id("run-1.o1", 1234567) == "cand:run-1.o1.1234567"
    assert seq_of("q:run-1.o1.000003", "q", "run-1.o1") == 3
    assert seq_of("q:run-1.o1.000003", "q", "run-1") is None and seq_of("l:a.1", "q", "a") is None
    assert seq_of("q:a.x1", "q", "a") is None and seq_of(None, "q", "a") is None
    for bad in ((" a", 1), ("a", 0), ("a", True), ("a", "1"), ("", 1), ("x" * 129, 1)):
        with pytest.raises(ValueError):
            qid(*bad)
