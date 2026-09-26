"""The retrieval scorer beyond the R05 tables (DESIGN §9.2-§9.4): value answers, abstention, cost and the budget
curve, missing responses, breakdowns, the bootstrap and the report."""
from __future__ import annotations

import json

import pytest

from khg_contracts import data
from khg_contracts.errors import ValidationError
from khg_contracts.scorers import retrieval
from khg_contracts.scorers.bootstrap import Bootstrap


def config(**kw):
    return retrieval.RetrievalConfig(bootstrap=Bootstrap(resamples=0), **kw)


def test_the_fixture_question_and_response(fixture_schema):
    """The design examples: rq:king-1700 answered with Louis XIV, f:king-14 at rank 1 with four of its bids."""
    items = data.load_jsonl("fixture/c4-items.jsonl")
    outputs = [o for o in data.load_jsonl("fixture/c5-outputs.jsonl") if o["kind"] == "retrieval-response"]
    facts = {r["id"]: r for r in data.load_json("fixture/fixture.c1.json")["records"]}
    rep = retrieval.score(items, outputs, facts=facts, config=config())
    it = rep["items"]["rq:king-1700"]
    assert (it["em"], it["value_em"], it["text_em"], it["token_f1"]) == (1.0, 1.0, 1.0, 1.0)
    assert it["support_success@1"] == 1.0 and it["mrr@10"] == 1.0 and it["r_precision"] == 1.0
    assert it["binding_coverage@1"] == 0.8  # b1-b4 of f:king-14's five bindings
    assert (it["support_p"], it["support_em"], it["joint_f1"], it["gated_em"]) == (1.0, 1.0, 1.0, 1.0)
    assert it["depends_on"] == ["f:king-14"]
    assert rep["config"]["qset"] == ["p2-fixture-qset"] and rep["config"]["schema"]["id"] == "p2-gate"
    assert rep["aggregate"]["headline"] == {"support_success@10": 1.0, "mrr@10": 1.0}
    assert rep["aggregate"]["cost"]["wall_ms"]["total"] == 820.0


def test_value_answers_resolve_redirects_and_identity(build):
    old = {"kind": "entity", "id": "t:old", "types": ["Thing"], "redirect_to": "t:new"}
    q = build.question("q1", [["h1"]], answer={"values": [{"entity": "t:new"}]})
    r = build.response("q1", ["h1"], answer={"values": [{"entity": "t:old"}], "abstained": False})
    assert retrieval.score([q], [r], config=config())["items"]["q1"]["em"] == 0.0
    assert retrieval.score([q], [r], facts=[old], config=config())["items"]["q1"]["em"] == 1.0
    julian = {"literal": {"datatype": "time", "time": "+1582-10-05T00:00:00Z", "precision": 11, "calendar": "julian"}}
    gregorian = {"literal": {"datatype": "time", "time": "+1582-10-15T00:00:00Z", "precision": 11,
                             "calendar": "gregorian"}}
    q2 = build.question("q2", [["h1"]], answer={"values": [julian]})
    r2 = build.response("q2", ["h1"], answer={"values": [gregorian], "abstained": False})
    assert retrieval.score([q2], [r2], config=config())["items"]["q2"]["value_em"] == 1.0
    # single mode reads the first value; set mode compares the sets
    r3 = build.response("q1", ["h1"], answer={"values": [{"entity": "t:x"}, {"entity": "t:new"}], "abstained": False})
    assert retrieval.score([q], [r3], config=config())["items"]["q1"]["em"] == 0.0
    s = retrieval.score([q], [r3], config=config(answer_mode="set"))["items"]["q1"]
    assert (s["set_p"], s["set_r"], s["em"]) == (0.5, 1.0, 0.0)


def test_abstention(build):
    qs = [build.question("a1", [["h1"]], answer={"values": [{"entity": "t:x"}]}),
          build.question("u1", [], answerable=False), build.question("u2", [], answerable=False)]
    abstain = {"values": [], "abstained": True}
    rs = [build.response("a1", ["h1"], answer=abstain), build.response("u1", [], answer=abstain),
          build.response("u2", ["h9"], answer={"values": [{"entity": "t:y"}], "abstained": False})]
    agg = retrieval.score(qs, rs, config=config())["aggregate"]
    assert agg["abstention"] == {"precision": 0.5, "recall": 0.5, "n_abstained": 2, "n_unanswerable": 2}
    assert agg["answer"]["em"] == 0.0 and agg["n_answerable"] == 1
    assert agg["ranking"]["hit@1"] == 1.0  # only the question with support is ranked


def test_missing_and_unmatched_responses(build):
    qs = [build.question("q1", [["h1"]], answer={"values": [{"entity": "t:x"}]}),
          build.question("q2", [["h2"]], answer={"values": [{"entity": "t:y"}]})]
    rs = [build.response("q1", ["h1"], answer={"values": [{"entity": "t:x"}], "abstained": False}),
          build.response("q9", ["h9"])]
    rep = retrieval.score(qs, rs, config=config())
    agg = rep["aggregate"]
    assert (agg["n_missing"], agg["n_unmatched_responses"]) == (1, 1)
    assert agg["answer"]["em"] == 0.5 and agg["ranking"]["hit@1"] == 0.5
    assert rep["items"]["q2"]["missing"] is True and rep["items"]["q2"]["abstained"] is False
    with pytest.raises(ValidationError) as e:
        retrieval.score(qs, rs + rs[:1], config=config())
    assert e.value.codes == ("KHG-C010",)
    with pytest.raises(ValidationError) as e:
        retrieval.score(qs + qs[:1], rs, config=config())
    assert e.value.codes == ("KHG-I002",)
    with pytest.raises(ValueError):
        retrieval.score(qs, rs, facts={"h1": build.fact("h1", "s", A="a")}, config=config())  # h2 is missing


def test_cost_and_the_budget_curve(build):
    qs = [build.question(f"q{n}", [["h1"]], answer={"values": [{"entity": "t:x"}]}) for n in range(4)]
    right = {"values": [{"entity": "t:x"}], "abstained": False}
    wrong = {"values": [{"entity": "t:y"}], "abstained": False}
    rs = [build.response("q0", ["h1"], answer=right, cost={"prompt_tokens": 90, "completion_tokens": 10}),
          build.response("q1", ["h1"], answer=wrong, cost={"prompt_tokens": 290, "completion_tokens": 10}),
          build.response("q2", ["h1"], answer=right, cost={"prompt_tokens": 190, "completion_tokens": 10,
                                                            "usd": 0.5, "price_table": "prices-2026-09"}),
          build.response("q3", ["h1"], answer=right, cost={"prompt_tokens": 390, "completion_tokens": 10})]
    cost = retrieval.score(qs, rs, config=config())["aggregate"]["cost"]
    assert cost["prompt_tokens"] == {"n": 4, "mean": 240.0, "median": 240.0, "p90": 390.0, "p95": 390.0,
                                     "total": 960.0}
    assert cost["usd"]["n"] == 1 and cost["price_tables"] == ["prices-2026-09"]
    assert "hyperedges_visited" not in cost
    curve = cost["budget_curve"]
    assert len(curve) == 10 and curve[-1] == {"budget": 1000, "fraction": 1.0, "n_answered": 4, "answer_em": 0.75}
    assert curve[0] == {"budget": 100, "fraction": 0.1, "n_answered": 1, "answer_em": 0.25}
    assert curve[3]["budget"] == 400 and curve[3]["n_answered"] == 2 and curve[3]["answer_em"] == 0.25
    assert curve[5]["budget"] == 600 and curve[5]["n_answered"] == 3 and curve[5]["answer_em"] == 0.5


def test_text_only_gold_scores_a_missing_answer_as_zero(build):
    """A gold with text and no values (R3's): a missing response, an abstention and an answer without text score 0
    on text EM and token F1, so they stay in the answer averages, as a missing value answer does. One right answer
    of four gives EM 0.25, not 1.0 over the one question that had text (review f-scorers-02)."""
    gold = {"values": [], "text": "Royal Swedish Academy of Sciences"}
    qs = [build.question(f"q{n}", [["h1"]], answer=gold) for n in range(1, 5)]
    rs = [build.response("q1", ["h1"], answer={"values": [], "text": "the Royal Swedish Academy of Sciences",
                                               "abstained": False}, support_claimed=["h1"]),
          build.response("q2", ["h1"], answer={"values": [], "abstained": True}, support_claimed=["h1"]),
          build.response("q4", ["h1"], answer={"values": [{"entity": "t:x"}], "abstained": False},
                         support_claimed=["h1"])]
    rep = retrieval.score(qs, rs, config=config())
    for qid in ("q2", "q3", "q4"):
        it = rep["items"][qid]
        assert (it["em"], it["text_em"], it["token_f1"], it["gated_em"]) == (0.0, 0.0, 0.0, 0.0), qid
    assert (rep["items"]["q2"]["joint_em"], rep["items"]["q4"]["joint_f1"]) == (0.0, 0.0)
    agg = rep["aggregate"]
    assert agg["answer"] == {"em": 0.25, "value_em": None, "text_em": 0.25, "token_f1": 0.25}
    assert agg["gated_em"] == 0.25 and agg["joint"]["joint_em"] == 1 / 3  # the missing response claims no support
    assert rep["breakdowns"]["by_hops"]["1"]["em"] == 0.25
    assert agg["cost"]["budget_curve"][-1]["answer_em"] == 0.25
    boot = retrieval.score(qs, rs, config=retrieval.RetrievalConfig())["bootstrap"]["intervals"]["em"]
    assert boot[0] < 1.0  # the interval resamples four questions, not the one with text


def test_set_scores_need_a_gold_value_set(build):
    """In set mode a text-only gold has no value set, so set P, R and F1 are not given (an empty wrong answer got
    set F1 1 by ``both_empty``, a right one 0); EM falls back to the text. A gold that is the empty set, with no text,
    is still scored as a set (review f-scorers-12)."""
    gold = {"values": [], "text": "Royal Swedish Academy of Sciences"}
    qs = [build.question("q1", [["h1"]], answer=gold), build.question("q2", [["h1"]], answer=gold)]
    rs = [build.response("q1", ["h1"], answer={"values": [], "text": "nonsense", "abstained": False}),
          build.response("q2", ["h1"], answer={"values": [{"entity": "t:y"}],
                                               "text": "Royal Swedish Academy of Sciences", "abstained": False})]
    rep = retrieval.score(qs, rs, config=config(answer_mode="set"))
    for qid in ("q1", "q2"):
        assert not {"set_p", "set_r", "set_f1", "set_flag"} & set(rep["items"][qid]), qid
    assert (rep["items"]["q1"]["em"], rep["items"]["q2"]["em"]) == (0.0, 1.0)
    assert rep["aggregate"]["answer"]["set_f1"] is None and rep["aggregate"]["answer"]["em"] == 0.5
    empty = build.question("q3", [["h1"]], answer={"values": []})
    it = retrieval.score([empty], [build.response("q3", ["h1"])], config=config(answer_mode="set"))["items"]["q3"]
    assert (it["set_f1"], it["set_flag"]) == (1.0, "both_empty")


def test_the_budget_curve_counts_every_answerable_question(build):
    """A question without a response spends nothing and is never answered, and it stays in the denominator: one right
    answer of four answerable questions is 0.25 at the full budget, as the answer EM is (review f-scorers-03)."""
    qs = [build.question(f"q{n}", [["h1"]], answer={"values": [{"entity": "t:x"}]}) for n in range(4)]
    rs = [build.response("q0", ["h1"], answer={"values": [{"entity": "t:x"}], "abstained": False})]
    agg = retrieval.score(qs, rs, config=config())["aggregate"]
    assert agg["answer"]["em"] == 0.25 and agg["n_missing"] == 3
    curve = agg["cost"]["budget_curve"]
    assert curve[-1] == {"budget": 110, "fraction": 1.0, "n_answered": 1, "answer_em": 0.25}
    assert curve[0] == {"budget": 11, "fraction": 0.1, "n_answered": 0, "answer_em": 0.0}
    assert retrieval.score(qs, [], config=config())["aggregate"]["cost"]["budget_curve"] == []  # nothing spent


def test_breakdowns_bootstrap_and_report(build):
    qs = [build.question("q1", [["h1"]], hops=1, qtype="single_hop"),
          build.question("q2", [["h2", "h3"]], hops=2, qtype="multi_hop"),
          build.question("q3", [["h4"]], hops=2, qtype="multi_hop")]
    rs = [build.response("q1", ["h1"]), build.response("q2", ["h2", "h3"]), build.response("q3", ["h9", "h4"])]
    rep = retrieval.score(qs, rs, config=retrieval.RetrievalConfig(ks=(1, 2), headline_k=2))
    by_hops = rep["breakdowns"]["by_hops"]
    assert by_hops["1"]["support_success@2"] == 1.0 and by_hops["2"]["mrr@2"] == 0.75 and by_hops["2"]["n"] == 2
    assert set(rep["breakdowns"]) == {"by_hops", "by_type", "by_source_class", "by_answer_mode"}
    boot = rep["bootstrap"]
    assert (boot["unit"], boot["n_units"]) == ("question", 3)
    lo, hi = boot["intervals"]["mrr@2"]
    assert 0.5 <= lo <= hi <= 1.0
    assert list(rep) == ["scorer", "config", "contracts", "aggregate", "breakdowns", "items", "bootstrap"]
    assert rep["config"]["ks"] == [1, 2] and rep["config"]["ndcg_discount"] == "log2"
    assert json.loads(json.dumps(rep)) == rep
    assert rep == retrieval.score(list(reversed(qs)), list(reversed(rs)),
                                  config=retrieval.RetrievalConfig(ks=(1, 2), headline_k=2))


@pytest.mark.parametrize("bad", [dict(ks=()), dict(ks=(0,)), dict(headline_k=0), dict(ndcg_discount="log10"),
                                 dict(answer_mode="list"), dict(bootstrap={})])
def test_the_configuration_is_checked(bad):
    with pytest.raises(ValueError):
        retrieval.RetrievalConfig(**bad)
