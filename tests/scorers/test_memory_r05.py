"""W11a: R05's memory table M1-M8 (R05 §5.7, DESIGN §9.7) through ``memory.score``, in C1 terms.

The abstract values of the table become the fixture's kings: ``Qnew`` is ``ex:LouisXIV`` and ``Qold`` is
``ex:LouisXIII`` on the question "who was King of France on 1 January 1700" (``mq:king-1700``: V_cur {LouisXIV},
LouisXIII expired). M5's as-of-past question is ``mq:king-1620`` (V_cur {LouisXIII}, V_fut {LouisXIV}). M4 asks for
Maria Skłodowska's birthplace after a dispute (unanswerable), and M8 asks for a population of 18. The last test checks
the outcomes against the reference probe's output when the checkout has it.
"""
from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any

import pytest

from khg_contracts import data
from khg_contracts.record import identity_key
from khg_contracts.scorers import Bootstrap, memory

LINES = data.load_jsonl("fixture/c4-items.jsonl")
TRACES = {x["trace_id"]: x for x in LINES if x["kind"] == "c4-memory-trace"}
QUESTIONS = {x["qid"]: x for x in LINES if x["kind"] == "c4-memory-question"}
FIXTURE = {r["id"]: r for r in data.load_json("fixture/fixture.c1.json")["records"] if "id" in r}
EVIDENCE = [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}}]
QNEW, QOLD = {"entity": "ex:LouisXIV"}, {"entity": "ex:LouisXIII"}
QX = {"entity": "ex:Mazarin"}
OFF = memory.MemoryConfig(bootstrap=Bootstrap(resamples=0))


def rec(rid: str, **changes: Any) -> dict[str, Any]:
    r = copy.deepcopy(FIXTURE[rid])
    for f in ("version", "recorded_at", "recorded_by", "status_ref"):
        r.pop(f, None)
    r["status"] = "asserted"
    r.update(changes)
    return r


def trace(tid: str, ents: list[str], *events: tuple[str, Any]) -> dict[str, Any]:
    return {"kind": "c4-memory-trace", "id": "c4:" + tid.replace(":", "-"), "qset": "r05-memory", "split": "test",
            "trace_id": tid, "entities": [copy.deepcopy(FIXTURE[i]) for i in ents],
            "events": [{"step": i, "tx_time": f"2026-10-01T00:00:{i:02d}Z", kind: body}
                       for i, (kind, body) in enumerate(events, 1)]}


def question(qid: str, tr: dict[str, Any], relation: str, key: list[dict[str, Any]], role: str, *,
             as_of: str | None = None, support: list[str] | None = None, schema: Any, **extra: Any) -> dict[str, Any]:
    """A ``c4-memory-question`` whose gold is its replay (as P3a builds them)."""
    q = {"kind": "c4-memory-question", "id": "c4:" + qid.replace(":", "-"), "qset": "r05-memory", "split": "test",
         "qid": qid, "trace_id": tr["trace_id"], "ask_after_step": len(tr["events"]), "subtype": "current_value",
         "text": "?", "relation": relation, "key": key, "target_role": role,
         "where": {"as_of": as_of, "valid_mode": "definite", "rank": ["preferred", "normal"], "status": ["asserted"]},
         "support": support or [], **extra}
    g = memory.derive_memory_gold(tr, q, schema=schema)
    q.update({k: g[k] for k in memory.GOLD_FIELDS})
    return q


def response(qid: str, *values: dict[str, Any], abstained: bool = False, **extra: Any) -> dict[str, Any]:
    return {"kind": "memory-response", "qid": qid, "answer": {"values": list(values), "abstained": abstained}, **extra}


def renamed(qid: str, base: str = "mq:king-1700") -> dict[str, Any]:
    return dict(copy.deepcopy(QUESTIONS[base]), qid=qid, id="c4:" + qid.replace(":", "-"))


def one(questions: list[dict[str, Any]], responses: list[dict[str, Any]], traces: list[dict[str, Any]], schema: Any,
        config: memory.MemoryConfig = OFF) -> dict[str, Any]:
    return memory.score(questions, responses, traces=traces, schema=schema, config=config)


def outcome(rep: dict[str, Any], qid: str) -> tuple[str, int, int]:
    item = rep["items"][qid]
    return item["outcome"], item["strict"], item["lenient"]


def disputed_trace() -> dict[str, Any]:
    return trace("t:dis", ["ex:Kraków", "ex:Maria_Skłodowska", "ex:Warszawa"],
                 ("put", [rec("f:born-skłodowska-kraków")]),
                 ("apply", {"op": "transition", "targets": ["f:born-skłodowska-kraków"], "to": "disputed",
                            "id": "m:dis-9", "reason": "key_conflict", "records": [rec("f:born-skłodowska-warszawa")],
                            "evidence": EVIDENCE}))


def population_trace(amount: str) -> dict[str, Any]:
    fact = rec("f:pop-łódź-2019")
    fact["bindings"][2]["value"] = {"literal": {"datatype": "quantity", "amount": amount, "unit": "1"}}
    assert fact["bindings"][2]["role"] == "quantity"
    return trace("t:pop", ["ex:Łódź"], ("put", [fact]))


LODZ = [{"role": "place", "value": {"entity": "ex:Łódź"}},
        {"role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2019-00-00T00:00:00Z",
                                                        "precision": 9, "calendar": "gregorian"}}}]


# ------------------------------------------------------------------------------------------------ M1-M8


def test_m1_current(fixture_schema):
    rep = one([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", QNEW)], [TRACES["t:kings"]], fixture_schema)
    assert outcome(rep, "mq:king-1700") == ("current", 1, 1)


def test_m2_stale(fixture_schema):
    rep = one([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", QOLD)], [TRACES["t:kings"]], fixture_schema)
    assert outcome(rep, "mq:king-1700") == ("stale", 0, 0)
    assert rep["items"]["mq:king-1700"]["stale_kind"] == "expired"
    # the maria question's old value was revised, not expired
    rep = one([QUESTIONS["mq:maria-birthplace"]], [response("mq:maria-birthplace", {"entity": "ex:Kraków"})],
              [TRACES["t:maria"]], fixture_schema)
    assert outcome(rep, "mq:maria-birthplace") == ("stale", 0, 0)
    assert rep["items"]["mq:maria-birthplace"]["stale_kind"] == "revised"
    assert (rep["aggregate"]["stale_expired_rate"], rep["aggregate"]["stale_revised_rate"]) == (0.0, 1.0)


def test_m3_hedged(fixture_schema):
    rep = one([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", QOLD, QNEW)], [TRACES["t:kings"]],
              fixture_schema)
    assert outcome(rep, "mq:king-1700") == ("hedged", 0, 1)
    item = rep["items"]["mq:king-1700"]
    assert (item["set_p"], item["set_r"], item["set_f1"]) == (0.5, 1.0, pytest.approx(2 / 3))
    assert item["hits"] == {"current": 1, "expired": 1, "revised": 0, "outranked": 0, "future": 0, "disputed": 0,
                            "other": 0}


def test_m4_abstention_on_an_unanswerable_question(fixture_schema):
    tr = disputed_trace()
    q = question("mq:dis", tr, "born_in", [{"role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}],
                 "birthplace", schema=fixture_schema, subtype="abstention")
    assert q["answerable"] is False and q["answer"]["values"] == []
    rep = one([q], [response("mq:dis", abstained=True)], [tr], fixture_schema)
    assert outcome(rep, "mq:dis") == ("correct_abstention", 1, 1)
    rep = one([q], [response("mq:dis", QX)], [tr], fixture_schema)
    assert outcome(rep, "mq:dis") == ("hallucinated", 0, 0)
    # a disputed value is an answer too
    rep = one([q], [response("mq:dis", {"entity": "ex:Warszawa"})], [tr], fixture_schema)
    assert outcome(rep, "mq:dis") == ("hallucinated", 0, 0)
    assert rep["aggregate"]["abstention"]["hallucination_rate"] == 1.0


def test_m5_as_of_past_gets_the_future_value(fixture_schema):
    rep = one([QUESTIONS["mq:king-1620"]], [response("mq:king-1620", QNEW)], [TRACES["t:kings"]], fixture_schema)
    assert outcome(rep, "mq:king-1620") == ("anachronistic", 0, 0)
    assert rep["aggregate"]["anachronism_rate"] == 1.0


def test_m6_aggregate(fixture_schema):
    """10 items: 6 current, 3 stale, 1 abstained."""
    qs = [renamed(f"mq:m6-{i}") for i in range(10)]
    answers = [[QNEW]] * 6 + [[QOLD]] * 3 + [[]]
    rs = [response(q["qid"], *a, abstained=not a) for q, a in zip(qs, answers, strict=True)]
    agg = one(qs, rs, [TRACES["t:kings"]], fixture_schema)["aggregate"]
    assert agg["acc_strict"] == 0.6 and agg["stale_rate"] == 0.3 and agg["abstention_rate"] == 0.1
    assert agg["stale_share_of_errors"] == 0.75
    assert agg["acc_lenient"] == 0.6 and agg["hedge_rate"] == 0.0 and agg["anachronism_rate"] == 0.0
    assert agg["outcomes"] == {"current": 6, "hedged": 0, "stale": 3, "anachronistic": 0, "wrong": 0, "abstained": 1,
                               "correct_abstention": 0, "hallucinated": 0, "missing": 0}
    assert agg["headline"] == {"metric": "acc_strict", "value": 0.6}


def test_m7_ranked_efficacy(fixture_schema):
    q = [QUESTIONS["mq:king-1700"]]
    scores = [{"value": QNEW, "score": 0.7}, {"value": QOLD, "score": 0.6}, {"value": QX, "score": 0.1}]
    rep = one(q, [response("mq:king-1700", QNEW, value_scores=scores)], [TRACES["t:kings"]], fixture_schema)
    assert rep["items"]["mq:king-1700"]["ranked_efficacy"] == 1
    assert rep["aggregate"]["ranked_efficacy"] == {"value": 1.0, "n": 1}
    scores[1]["score"] = 0.7  # a tie is no efficacy
    rep = one(q, [response("mq:king-1700", QNEW, value_scores=scores)], [TRACES["t:kings"]], fixture_schema)
    assert rep["items"]["mq:king-1700"]["ranked_efficacy"] == 0


def test_m8_temporal_tolerance(fixture_schema):
    """Gold 18, answer 19: strict 0; with a tolerance of 1: 1 (a quantity tolerance, same unit)."""
    tr = population_trace("+18")
    q = question("mq:m8", tr, "population", LODZ, "quantity", schema=fixture_schema)
    answer = {"literal": {"datatype": "quantity", "amount": "+19", "unit": "1"}}
    assert outcome(one([q], [response("mq:m8", answer)], [tr], fixture_schema), "mq:m8") == ("wrong", 0, 0)
    tolerant = dict(q, tolerance={"amount": "+1"})
    assert outcome(one([tolerant], [response("mq:m8", answer)], [tr], fixture_schema), "mq:m8") == ("current", 1, 1)
    assert outcome(one([dict(q, tolerance={"amount": 1})], [response("mq:m8", answer)], [tr], fixture_schema),
                   "mq:m8") == ("current", 1, 1)
    far = {"literal": {"datatype": "quantity", "amount": "+20", "unit": "1"}}
    assert outcome(one([tolerant], [response("mq:m8", far)], [tr], fixture_schema), "mq:m8")[0] == "wrong"


def quantity(amount: str) -> dict[str, Any]:
    return {"literal": {"datatype": "quantity", "amount": amount, "unit": "1"}}


def test_m8_a_tolerance_never_blurs_an_exact_answer(fixture_schema):
    """Łódź's population is corrected from 19 to 18 (a supersede for a correction): V_cur {18}, revised {19}. With a
    tolerance of 1, an answer equal to a gold value matches that value alone, so 18 stays current and 19 stale, as
    without the tolerance (both were hedged: strict 0, lenient 1). An answer equal to no gold value still gets the
    tolerance (review f-scorers-06)."""
    def pop(fid: str, amount: str) -> dict[str, Any]:
        f = rec("f:pop-łódź-2019", id=fid, evidence=copy.deepcopy(EVIDENCE))
        f["bindings"][2]["value"] = quantity(amount)
        return f

    tr = trace("t:pop2", ["ex:Łódź"], ("put", [pop("f:p19", "+19")]),
               ("apply", {"op": "supersede", "id": "m:sup-p", "superseded": ["f:p19"], "records": [pop("f:p18", "+18")],
                          "reason": "correction", "evidence": EVIDENCE}))
    q = question("mq:pop", tr, "population", LODZ, "quantity", schema=fixture_schema)
    assert q["answer"]["values"] == [quantity("+18")]
    assert q["stale_values"] == [{"value": quantity("+19"), "kind": "revised"}]
    tolerant = dict(q, tolerance={"amount": "+1"})
    for item, amount, want in ((q, "+18", ("current", 1, 1)), (tolerant, "+18", ("current", 1, 1)),
                               (q, "+19", ("stale", 0, 0)), (tolerant, "+19", ("stale", 0, 0)),
                               (tolerant, "+17", ("current", 1, 1)), (tolerant, "+20", ("stale", 0, 0))):
        rep = one([item], [response("mq:pop", quantity(amount))], [tr], fixture_schema)
        assert outcome(rep, "mq:pop") == want, (amount, "tolerance" in item)
    rep = one([tolerant], [response("mq:pop", quantity("+19"))], [tr], fixture_schema)
    assert rep["items"]["mq:pop"]["stale_kind"] == "revised"
    assert rep["items"]["mq:pop"]["hits"] == {"current": 0, "expired": 0, "revised": 1, "outranked": 0, "future": 0,
                                              "disputed": 0, "other": 0}


def test_a_disputed_value_still_never_changes_the_outcome_under_a_tolerance():
    """An answer equal to a disputed value only is no exact gold answer: the tolerance still reaches V_cur, so the
    outcome is the one without the disputed value (current here)."""
    gold = {"answer": {"values": [quantity("+18")]}, "stale_values": [], "future_values": [],
            "disputed_values": [quantity("+19")], "answerable": True}
    answered = [(identity_key(quantity("+19")), quantity("+19"))]
    with_dispute = memory.classify(answered, False, gold, tolerance=Decimal(1))
    without = memory.classify(answered, False, dict(gold, disputed_values=[]), tolerance=Decimal(1))
    assert with_dispute["outcome"] == without["outcome"] == "current"
    assert with_dispute["hits"]["disputed"] == 1


def test_the_outcomes_agree_with_the_reference_probe(reference, fixture_schema):
    """``research/probes/scorers/c5_reference_cases.py`` computed the table's expected values."""
    want = reference["memory"]
    kings = [TRACES["t:kings"]]
    got = {}
    for name, answers in (("M1_current", [QNEW]), ("M2_stale", [QOLD]), ("M3_hedged", [QOLD, QNEW])):
        o, s, lenient = outcome(one([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", *answers)], kings,
                                    fixture_schema), "mq:king-1700")
        got[name] = {"outcome": o, "strict": s, "lenient": lenient}
    tr = disputed_trace()
    q = question("mq:dis", tr, "born_in", [{"role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}],
                 "birthplace", schema=fixture_schema)
    for name, r in (("M4a_unanswerable_abstains", response("mq:dis", abstained=True)),
                    ("M4b_unanswerable_answers", response("mq:dis", QX))):
        o, s, lenient = outcome(one([q], [r], [tr], fixture_schema), "mq:dis")
        got[name] = {"outcome": o, "strict": s, "lenient": lenient}
    o, s, lenient = outcome(one([QUESTIONS["mq:king-1620"]], [response("mq:king-1620", QNEW)], kings,
                                fixture_schema), "mq:king-1620")
    got["M5_as_of_past_gets_future_value"] = {"outcome": o, "strict": s, "lenient": lenient}
    for name in got:
        assert got[name] == want[name], name
    qs = [renamed(f"mq:m6-{i}") for i in range(10)]
    answers = [[QNEW]] * 6 + [[QOLD]] * 3 + [[]]
    agg = one(qs, [response(x["qid"], *a, abstained=not a) for x, a in zip(qs, answers, strict=True)], kings,
              fixture_schema)["aggregate"]
    assert {"accuracy": agg["acc_strict"], "stale_rate": agg["stale_rate"], "abstention_rate": agg["abstention_rate"],
            "stale_share_of_errors": agg["stale_share_of_errors"]} == want["M6_aggregate"]
    scores = [{"value": QNEW, "score": 0.7}, {"value": QOLD, "score": 0.6}]
    rep = one([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", QNEW, value_scores=scores)], kings,
              fixture_schema)
    assert rep["items"]["mq:king-1700"]["ranked_efficacy"] == want["M7_pairwise_efficacy"]
    tr = population_trace("+18")
    q8 = question("mq:m8", tr, "population", LODZ, "quantity", schema=fixture_schema)
    answer = {"literal": {"datatype": "quantity", "amount": "+19", "unit": "1"}}
    strict = outcome(one([q8], [response("mq:m8", answer)], [tr], fixture_schema), "mq:m8")[1]
    tolerant = outcome(one([dict(q8, tolerance={"amount": "+1"})], [response("mq:m8", answer)], [tr],
                           fixture_schema), "mq:m8")[1]
    assert {"strict": strict, "tolerance_1": tolerant} == want["M8_off_by_one"]
