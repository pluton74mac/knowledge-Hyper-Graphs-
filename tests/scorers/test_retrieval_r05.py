"""R05 §4.7 retrieval tables R1-R8 and R9 (DESIGN §9.7) through ``retrieval.score``. R1's nDCG is 0.650921, and
0.75 for the LongMemEval discount; R9's ``binding_coverage@1`` is 2/3 and ``@2`` is 1. KILT recall is not a C5
metric (R05 D-C5-12: adapters only), so R1's and R2's KILT columns are only checked against the probe."""
from __future__ import annotations

from fractions import Fraction as F

from khg_contracts.scorers import retrieval
from khg_contracts.scorers.bootstrap import Bootstrap


def config(**kw):
    kw.setdefault("ks", (1, 2, 3, 4))
    kw.setdefault("headline_k", 4)
    return retrieval.RetrievalConfig(bootstrap=Bootstrap(resamples=0), **kw)


def one(build, question, response, **kw):
    facts = kw.pop("facts", None)
    rep = retrieval.score([question], [response], facts=facts, config=config(**kw))
    return rep["items"][question["qid"]], rep


def test_r1_one_support_set(build):
    q = build.question("q1", [["h1", "h2"]])
    r = build.response("q1", ["h3", "h1", "h4", "h2"])
    it, rep = one(build, q, r)
    assert (it["hit@1"], it["hit@2"]) == (0.0, 1.0)
    assert (it["support_success@2"], it["support_success@4"]) == (0.0, 1.0)
    assert it["support_recall@2"] == 0.5 and it["mrr@2"] == 0.5 and it["mrr@4"] == 0.5
    assert it["mrr@1"] == 0.0  # cut-off MRR: nothing in the top 1
    assert it["r_precision"] == 0.5
    assert round(it["ndcg@4"], 6) == 0.650921
    expected = (1 / 1.584962500721156 + 1 / 2.321928094887362) / (1 + 1 / 1.584962500721156)
    assert abs(it["ndcg@4"] - expected) < 1e-12
    assert rep["aggregate"]["ndcg_discount"] == "log2(i+1)"
    lme, rep2 = one(build, q, r, ndcg_discount="longmemeval")
    assert lme["ndcg@4"] == 0.75 and rep2["aggregate"]["ndcg_discount"] == "longmemeval"


def test_r2_alternative_support_sets(build):
    it, _ = one(build, build.question("q2", [["h1", "h2"], ["h5"]]), build.response("q2", ["h5", "h1", "h9"]))
    assert it["r_precision"] == 1.0 and it["support_success@1"] == 1.0
    assert it["support_recall@1"] == 1.0  # the set {h5} is complete
    assert it["hit@1"] == 1.0


def test_r3_answer_text(build):
    gold = {"values": [], "text": "Royal Swedish Academy of Sciences"}
    q = build.question("q3", [["h1"]], answer=gold)
    exact, _ = one(build, q, build.response("q3", ["h1"], answer={
        "values": [], "text": "the Royal Swedish Academy of Sciences.", "abstained": False}))
    assert exact["text_em"] == 1.0 and exact["em"] == 1.0 and exact["token_f1"] == 1.0
    partial, _ = one(build, q, build.response("q3", ["h1"], answer={
        "values": [], "text": "Swedish Academy", "abstained": False}))
    assert partial["text_em"] == 0.0
    assert (partial["token_p"], partial["token_r"], partial["token_f1"]) == (1.0, 0.4, float(F(4, 7)))
    assert retrieval.normalize_answer("The  Royal, Swedish Academy of Sciences.") == "royal swedish academy of sciences"


def test_r4_entity_set(build):
    q = build.question("q4", [["h1"]], answer={"values": [{"entity": "Q1"}, {"entity": "Q2"}]})
    r = build.response("q4", ["h1"], answer={"values": [{"entity": "Q1"}, {"entity": "Q3"}], "abstained": False})
    it, rep = one(build, q, r, answer_mode="set")
    assert (it["set_p"], it["set_r"], it["set_f1"]) == (0.5, 0.5, 0.5)
    assert it["value_em"] == 0.0 and it["em"] == 0.0
    assert rep["aggregate"]["answer"]["set_f1"] == 0.5


def test_r5_joint(build):
    """Answer P 1 and R 0.4 (R3's partial text), support P 0.5 and R 0.5: joint P 0.5, R 0.2, F1 0.2/0.7."""
    q = build.question("q5", [["h1", "h2"]], answer={"values": [], "text": "Royal Swedish Academy of Sciences"})
    r = build.response("q5", ["h1", "h3"], answer={"values": [], "text": "Swedish Academy", "abstained": False},
                       support_claimed=["h1", "h3"])
    it, _ = one(build, q, r)
    assert (it["support_p"], it["support_r"], it["support_em"]) == (0.5, 0.5, 0.0)
    assert (it["joint_p"], it["joint_r"]) == (0.5, 0.2)
    assert it["joint_f1"] == float(F(2, 7))
    assert round(it["joint_f1"], 6) == 0.285714
    # joint EM (R-M10) needs both EMs: a right value answer with part of the support set is 0, with the set 1
    vq = build.question("q5v", [["h1", "h2"]], answer={"values": [{"entity": "Q1"}]})
    right = {"values": [{"entity": "Q1"}], "abstained": False}
    part, rep = one(build, vq, build.response("q5v", ["h1", "h2"], answer=right, support_claimed=["h1"]))
    assert (part["em"], part["support_em"], part["joint_em"]) == (1.0, 0.0, 0.0)
    assert rep["aggregate"]["joint"]["joint_em"] == 0.0
    full, _ = one(build, vq, build.response("q5v", ["h1", "h2"], answer=right, support_claimed=["h2", "h1"]))
    assert (full["em"], full["support_em"], full["joint_em"]) == (1.0, 1.0, 1.0)


def test_r6_gated_em(build):
    """EM 1 with R-precision 0.5 is gated to 0; EM 1 with R-precision 1 stays 1."""
    answer = {"values": [{"entity": "Q1"}]}
    ok = {"values": [{"entity": "Q1"}], "abstained": False}
    half, _ = one(build, build.question("q6", [["h1", "h2"]], answer=answer), build.response("q6", ["h1", "h3"],
                                                                                            answer=ok))
    full, _ = one(build, build.question("q6", [["h1", "h2"]], answer=answer), build.response("q6", ["h2", "h1"],
                                                                                            answer=ok))
    assert (half["em"], half["r_precision"], half["gated_em"]) == (1.0, 0.5, 0.0)
    assert (full["em"], full["r_precision"], full["gated_em"]) == (1.0, 1.0, 1.0)


def test_r7_cost(build):
    qs = [build.question(f"q7-{n}", [["h1"]]) for n in range(3)]
    rs = [build.response(f"q7-{n}", ["h1"], cost={"prompt_tokens": t}) for n, t in enumerate((100, 300, 200))]
    cost = retrieval.score(qs, rs, config=config())["aggregate"]["cost"]["prompt_tokens"]
    assert (cost["mean"], cost["median"], cost["p90"], cost["total"], cost["n"]) == (200.0, 200.0, 300.0, 600.0, 3)


def test_r8_the_substring_trap(build):
    """Gold "5" against "15 items": character-substring matching would accept it; C5's default gives 0."""
    q = build.question("q8", [["h1"]], answer={"values": [], "text": "5"})
    it, _ = one(build, q, build.response("q8", ["h1"], answer={"values": [], "text": "15 items", "abstained": False}))
    assert it["text_em"] == 0.0 and it["token_f1"] == 0.0 and it["em"] == 0.0
    assert "5" in "15 items"  # the trap C5 does not fall into


def test_r9_binding_coverage(build):
    """Gold h = r(A: a, B: b, C: c); units [pair(A, B), pair(A, C)] with bid back-pointers."""
    h = build.fact("h", "r", A="a", B="b", C="c")
    q = build.question("q9", [["h"]])
    r = build.response("q9", [("pair:h:AB", "h", [["h", "b1"], ["h", "b2"]]),
                              ("pair:h:AC", "h", [["h", "b1"], ["h", "b3"]])])
    it, rep = one(build, q, r, facts={"h": h})
    assert it["binding_coverage@1"] == float(F(2, 3)) and it["binding_coverage@2"] == 1.0
    assert rep["aggregate"]["ranking"]["binding_coverage@1"] == float(F(2, 3))
    # both units point at h, the only support hyperedge: it counts at its first unit only, so nDCG stays 1
    assert (it["ndcg@1"], it["ndcg@2"], it["ndcg@4"]) == (1.0, 1.0, 1.0)
    # a hyperedge unit without bids covers every binding of its hyperedge
    whole, _ = one(build, q, build.response("q9", ["h"]), facts=[h])
    assert whole["binding_coverage@1"] == 1.0
    # without facts the measure is not computed
    none, rep3 = one(build, q, r)
    assert "binding_coverage@1" not in none and "binding_coverage@1" not in rep3["aggregate"]["ranking"]


def test_the_expected_values_are_the_probe_values(reference):
    probe = reference["retrieval"]
    r1 = probe["R1_single_support_set"]
    assert (r1["recall_any@1"], r1["recall_any@2"], r1["recall_all@2"], r1["recall_all@4"]) == (0.0, 1.0, 0.0, 1.0)
    assert (r1["fractional_recall@2"], r1["mrr"], r1["r_precision"]) == (0.5, 0.5, 0.5)
    assert (r1["ndcg@4_log2(i+1)"], r1["ndcg@4_longmemeval"]) == (0.650921, 0.75)
    assert (r1["kilt_recall@2"], r1["kilt_recall@3"], r1["kilt_recall@4"]) == (0.0, 1.0, 1.0)
    assert probe["R2_alternative_support_sets"] == {"kilt_recall@1": 0.5, "r_precision": 1.0, "support_success@1": 1.0}
    assert probe["R3_answer_em_f1"] == {"em_with_article_and_period": True,
                                        "f1_partial": {"f1": 0.571429, "p": 1.0, "r": 0.4}}
    assert (probe["R4_entity_set"]["f1"], probe["R4_entity_set"]["em"]) == (0.5, 0.0)
    assert probe["R5_joint_f1"] == {"joint_f1": 0.285714, "joint_p": 0.5, "joint_r": 0.2}
    assert probe["R6_gated_em"] == {"em1_rprec_0.5": 0.0, "em1_rprec_1.0": 1.0}
    assert probe["R7_cost"] == {"mean": 200.0, "median": 200, "p90_nearest_rank": 300}
    assert probe["R8_subem_false_positive"] == {"char_substring": True, "token_containment": False}
