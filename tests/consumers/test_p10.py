"""P10's call sequence (DESIGN §1.3): retrieval over the store, scored with cost.

``ms`` is a ``MemoryStore`` holding the gate fixture. ``questions`` is the packaged ``c4-retrieval-question`` ("Who was
King of France on 1 January 1700?", anchored on ``ex:KingOfFrance``), ``responses`` the packaged
``retrieval-response``, and ``fact_ids`` the question's gold support. The question's ``where`` drives every read,
so the same question asked on the day of the 1643 handover finds nobody under a definite read and both kings under a
possible one (§2.6).
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from khg_contracts import CONTRACTS, record, store
from khg_contracts.scorers import retrieval

#: The §2.10 example: ``render_text(f:king-14)``.
KING_14_TEXT = ("position_held(holder: Louis XIV; position: King of France; replaces: Louis XIII) "
                "[+1643-05-14T00:00:00Z/11, +1715-09-01T00:00:00Z/11)")


def p10(S: Any, ms: Any, questions: list[dict[str, Any]], responses: list[dict[str, Any]], labels: dict[str, str],
        fact_ids: list[str]) -> dict[str, Any]:
    """The P10 sequence; returns its variables (those of the last question)."""
    # >>> DESIGN §1.3
    # P10: retrieval over the store, scored with cost
    for qn in questions:
        w = store.Where(as_of=qn["where"]["as_of"], valid_mode=qn["where"]["valid_mode"], rank=frozenset(qn["where"]["rank"]))
        facts = [f for a in qn["anchors"] for f in ms.incident(a, where=w)]
        degrees = {a: ms.degree(a, where=w) for a in qn["anchors"]}
        context = [record.render_text(f, labels, schema=S) for f in facts]
    retrieval.score(questions, responses, facts=ms.get_many(fact_ids))
    # <<< DESIGN §1.3
    return dict(locals())


@pytest.fixture()
def ms(S, fixture_doc) -> store.MemoryStore:
    s = store.MemoryStore(S)
    s.load(fixture_doc)
    return s


@pytest.fixture()
def questions(c4_items) -> list[dict[str, Any]]:
    return [x for x in c4_items if x["kind"] == "c4-retrieval-question"]


@pytest.fixture()
def responses(c5_outputs) -> list[dict[str, Any]]:
    return [x for x in c5_outputs if x["kind"] == "retrieval-response"]


def test_p10_sequence(S, ms, questions, responses, labels):
    fact_ids = sorted({f for qn in questions for s in qn["support"]["sets"] for f in s})
    out = p10(S, ms, questions, responses, labels, fact_ids)

    assert fact_ids == ["f:king-14"]
    assert out["w"] == store.Where(as_of="+1700-01-01T00:00:00Z", valid_mode="definite",
                                   rank=frozenset({"preferred", "normal"}))
    assert [f["id"] for f in out["facts"]] == ["f:king-14"]
    assert out["degrees"] == {"ex:KingOfFrance": 1}
    assert out["context"] == [KING_14_TEXT]
    # the score (asked again: the sequence leaves the report unnamed)
    report = retrieval.score(questions, responses, facts=ms.get_many(fact_ids))
    assert report["scorer"] == "retrieval" and report["contracts"] == dict(CONTRACTS)
    agg = report["aggregate"]
    assert (agg["n_questions"], agg["n_responses"], agg["n_missing"]) == (1, 1, 0)
    assert agg["headline"] == {"support_success@10": 1.0, "mrr@10": 1.0}
    assert agg["answer"]["em"] == 1.0 and agg["support"]["support_em"] == 1.0
    # cost is required in every response and summarised per field
    assert (agg["cost"]["prompt_tokens"]["total"], agg["cost"]["completion_tokens"]["total"]) == (412.0, 9.0)
    item = report["items"]["rq:king-1700"]
    assert item["depends_on"] == ["f:king-14"]
    # the response points at b1-b4 of f:king-14, not at b5 (replaces): four of the gold fact's five bindings
    assert item["binding_coverage@10"] == pytest.approx(4 / 5)


@pytest.mark.parametrize("valid_mode, expected", [("definite", []), ("possible", ["f:king-13", "f:king-14"])])
def test_p10_sequence_on_the_day_of_the_handover(S, ms, questions, responses, labels, valid_mode, expected):
    """As of 1643-05-14, the day Louis XIII's reign ends and Louis XIV's starts (day precision): neither reign
    definitely holds at that instant, and both possibly hold (§2.6)."""
    asked = copy.deepcopy(questions)
    asked[0]["where"].update(as_of="+1643-05-14T00:00:00Z", valid_mode=valid_mode)
    out = p10(S, ms, asked, responses, labels, ["f:king-14"])
    assert [f["id"] for f in out["facts"]] == expected
    assert out["degrees"] == {"ex:KingOfFrance": len(expected)}
    assert len(out["context"]) == len(expected)
