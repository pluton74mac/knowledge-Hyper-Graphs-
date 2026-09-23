"""R05 §3.7 completion tables C1-C8 and C7b (DESIGN §9.7) through ``FilterIndex``, ``rank_stats`` and
``completion.score``. C3 gives E[RR] 25/48; C7 gives ECE 13/100 at M = 10 and M = 15 and Brier 393/2000; C7b gives
1/4 with equal width and 2/5 with equal mass; C8 (correct = [1, 1, 1, 0, 1, 1, 0, 0, 0, 0]) gives 1/4 and 19/100."""
from __future__ import annotations

from fractions import Fraction as F

import pytest

from khg_contracts.scorers import completion
from khg_contracts.scorers.bootstrap import Bootstrap

CONF7 = [0.95] * 4 + [0.55] * 4 + [0.15] * 2
CORR7 = [1, 1, 1, 0, 1, 1, 0, 0, 0, 0]


def config(**kw):
    return completion.CompletionConfig(bootstrap=Bootstrap(resamples=0), **kw)


def query_for(build, schema, fact, role):
    return next(q for q in completion.build_queries([fact], schema) if q["target"]["role"] == role)


def scores_of(**s):
    return {"t:" + k: v for k, v in s.items()}


def item(report, qid):
    return report["items"][qid]


def test_c1_no_ties(build, r05_schema):
    f = build.fact("f1", "s", A="s0", B="t")
    q = query_for(build, r05_schema, f, "B")
    index = completion.FilterIndex.from_records([], [], [f], schema=r05_schema)
    rec = completion.rank_stats(q, scores_of(t=0.5, x=0.9, y=0.8, z=0.1), index)
    assert (rec["n_candidates"], rec["n_filtered_out"], rec["n_greater"], rec["n_equal"]) == (4, 0, 2, 0)
    it = item(completion.score([q], [rec], config=config()), q["qid"])
    assert (it["optimistic"], it["pessimistic"], it["rr"]) == (3, 3, float(F(1, 3)))
    assert (it["hits@1"], it["hits@3"], it["hits@10"]) == (0.0, 1.0, 1.0)


def test_c2_filtering(build, r05_schema):
    """e1 0.9 is a known answer: the raw rank of e3 is 2 (RR 0.5); filtered it is 1."""
    f = build.fact("f-test", "s", A="s0", B="e3")
    known = build.fact("f-train", "s", A="s0", B="e1")
    q = query_for(build, r05_schema, f, "B")
    s = scores_of(e1=0.9, e2=0.2, e3=0.7, e4=0.1, e5=0.05)
    raw = completion.rank_stats(q, s, completion.FilterIndex.from_records([], [], [f], schema=r05_schema))
    filtered = completion.rank_stats(q, s, completion.FilterIndex.from_records([known], [], [f], schema=r05_schema))
    assert (raw["n_greater"], raw["n_filtered_out"]) == (1, 0)
    assert (filtered["n_greater"], filtered["n_filtered_out"]) == (0, 1)
    assert item(completion.score([q], [raw], config=config()), q["qid"])["rr"] == 0.5
    assert item(completion.score([q], [filtered], config=config()), q["qid"])["rr"] == 1.0


def test_c3_four_way_tie(build, r05_schema):
    f = build.fact("f1", "s", A="s0", B="t")
    q = query_for(build, r05_schema, f, "B")
    rec = completion.rank_stats(q, scores_of(t=0.8, a=0.8, b=0.8, c=0.8, d=0.1),
                                completion.FilterIndex.from_records([f], schema=r05_schema))
    assert (rec["n_greater"], rec["n_equal"]) == (0, 3)
    tie = completion.score([q], [rec], config=config())
    it = item(tie, q["qid"])
    assert (it["optimistic"], it["pessimistic"], it["rank"]) == (1, 4, 2.5)
    assert it["rr"] == float(F(25, 48)) and it["hits@1"] == 0.25 and it["hits@3"] == 0.75
    assert tie["aggregate"]["rank_audit"]["realistic_mrr"] == 0.4
    realistic = item(completion.score([q], [rec], config=config(rank="realistic")), q["qid"])
    assert (realistic["rr"], realistic["hits@1"], realistic["hits@3"]) == (0.4, 0.0, 1.0)


def test_c4_denominators(build, r05_schema):
    """F1 (arity 2): RRs 1, 1; F2 (arity 4): RR 0.1 four times. Per task 0.40, per fact 0.55, macro-arity 0.55."""
    f1 = build.fact("F1", "r2", A="a", B="b")
    f2 = build.fact("F2", "r4", A="a", B="b", C="c", D="d")
    queries = completion.build_queries([f1, f2], r05_schema)
    assert [q["qid"] for q in queries] == ["cq:F1#b1", "cq:F1#b2", "cq:F2#b1", "cq:F2#b2", "cq:F2#b3", "cq:F2#b4"]
    records = [{"kind": "completion-rank", "qid": q["qid"], "n_candidates": 20, "n_filtered_out": 0,
                "n_greater": 0 if q["fact_id"] == "F1" else 9, "n_equal": 0} for q in queries]
    agg = completion.score(queries, records, config=config())["aggregate"]
    assert agg["per_task"]["mrr"] == float(F(2 + F(4, 10), 6)) == 0.4
    assert agg["per_fact"]["mrr"] == 0.55
    assert agg["macro_arity"]["mrr"] == 0.55 and agg["macro_arity"]["n_bins"] == 2
    assert agg["headline"] == "macro_arity"


def test_c5_time_aware_filter(build, fixture_schema):
    """o1 held the position 2010-2015 (0.9), o2 from 2016 (the target, 0.8), o3 never (0.1). The time-agnostic
    filter removes o1 (rank 1); the time-aware filter keeps it, since o1 is not valid when o2 is (rank 2)."""
    def held(fid, who, start, end=None):
        bs = [("holder", {"entity": who}), ("position", {"entity": "ex:Chair"}),
              ("start_time", build.time(start, 9))]
        if end:
            bs.append(("end_time", build.time(end, 9)))
        return build.literal_fact(fid, "position_held", bs)

    o1 = held("f:o1", "ex:o1", "+2010-00-00T00:00:00Z", "+2015-00-00T00:00:00Z")
    o2 = held("f:o2", "ex:o2", "+2016-00-00T00:00:00Z")
    q = query_for(build, fixture_schema, o2, "holder")
    index = completion.FilterIndex.from_records([o1], [], [o2], schema=fixture_schema)
    assert index.known_answers(q, "exact") == {"ex:o1", "ex:o2"}
    assert index.known_answers(q, "time_aware") == {"ex:o2"}
    s = {"ex:o1": 0.9, "ex:o2": 0.8, "ex:o3": 0.1}
    by_filter = {m: [completion.rank_stats(q, s, index, filter=m)] for m in ("exact", "time_aware")}
    rep = completion.score([q], by_filter, config=config())
    assert item(rep, q["qid"])["rr"] == 1.0
    assert rep["breakdowns"]["filters"]["time_aware"]["per_task"]["mrr"] == 0.5
    assert rep["breakdowns"]["filters"]["exact"]["per_task"]["mrr"] == 1.0
    assert rep["breakdowns"]["filters"]["monotone"] is None
    time_aware = completion.score([q], by_filter, config=config(filter="time_aware"))
    assert time_aware["aggregate"]["per_task"]["mrr"] == 0.5 and time_aware["aggregate"]["filter"] == "time_aware"


def test_c6_monotone_filter(build, r05_schema):
    """Query (s, r, ?, {deg: BSc}) with target ETH 0.6; the known (s, r, UZH, {deg: BSc, year: 1900}) scores 0.7.
    The exact filter keeps UZH (rank 2); the monotone filter (⊑) removes it (rank 1)."""
    f = build.fact("f-test", "r", A="s", B="ETH", C="bsc")
    known = build.fact("f-known", "r", A="s", B="UZH", C="bsc", D="y1900")
    q = query_for(build, r05_schema, f, "B")
    index = completion.FilterIndex.from_records([known], [], [f], schema=r05_schema)
    s = scores_of(ETH=0.6, UZH=0.7, TUM=0.1)
    exact = completion.rank_stats(q, s, index)
    monotone = completion.rank_stats(q, s, index, filter="monotone")
    assert (exact["n_greater"], exact["n_filtered_out"]) == (1, 0)
    assert (monotone["n_greater"], monotone["n_filtered_out"]) == (0, 1)
    rep = completion.score([q], {"exact": [exact], "monotone": [monotone]}, config=config())
    assert rep["breakdowns"]["filters"]["exact"]["per_task"]["mrr"] == 0.5
    assert rep["breakdowns"]["filters"]["monotone"]["per_task"]["mrr"] == 1.0


def _calibration_queries(build, r05_schema, conf, correct, arities=None):
    queries, records = [], []
    for n, (c, y) in enumerate(zip(conf, correct, strict=True)):
        arity = (arities or [2] * len(conf))[n]
        rel = {2: "r2", 4: "r4"}[arity]
        roles = {"A": f"a{n}", "B": f"b{n}", **({"C": f"c{n}", "D": f"d{n}"} if arity == 4 else {})}
        f = build.fact(f"F{n:02d}", rel, **roles)
        q = query_for(build, r05_schema, f, "A")
        queries.append(q)
        top = q["target"]["value"] if y else {"entity": "t:wrong"}
        records.append({"kind": "completion-rank", "qid": q["qid"], "n_candidates": 10, "n_filtered_out": 0,
                        "n_greater": 0 if y else 1, "n_equal": 0, "top1": {"value": top, "prob": c}})
    return queries, records


@pytest.mark.parametrize("bins", [10, 15])
def test_c7_calibration(build, r05_schema, bins):
    queries, records = _calibration_queries(build, r05_schema, CONF7, CORR7)
    cal = completion.score(queries, records, config=config(ece_bins=bins))["aggregate"]["calibration"]
    assert cal["n"] == 10 and cal["accuracy"] == 0.5 and cal["mean_confidence"] == 0.63
    assert cal["ece"] == {"equal_width": 0.13, "equal_mass": 0.13}
    assert cal["brier"] == float(F(393, 2000)) == 0.1965
    width = cal["reliability"]["equal_width"]
    assert [(r["n"], r["accuracy"], r["confidence"]) for r in width] == [(2, 0.0, 0.15), (4, 0.5, 0.55),
                                                                         (4, 0.75, 0.95)]


def test_c7b_equal_width_against_equal_mass(build, r05_schema):
    queries, records = _calibration_queries(build, r05_schema, [0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1])
    cal = completion.score(queries, records, config=config(ece_bins=2))["aggregate"]["calibration"]
    assert cal["ece"] == {"equal_width": 0.25, "equal_mass": 0.4}
    assert [r["n"] for r in cal["reliability"]["equal_mass"]] == [2, 2]


def test_c8_ece_by_arity(build, r05_schema):
    """The first five queries are arity 2 and the last five arity 4; bins under ``min_bin_queries`` are counted
    only."""
    queries, records = _calibration_queries(build, r05_schema, CONF7, CORR7, arities=[2] * 5 + [4] * 5)
    for bins in (10, 15):
        rep = completion.score(queries, records, config=config(ece_bins=bins, min_bin_queries=5))
        by_arity = rep["breakdowns"]["calibration_by_arity"]["arity"]
        assert by_arity["2"]["ece"]["equal_width"] == 0.25
        assert by_arity["4"]["ece"]["equal_width"] == 0.19
    suppressed = completion.score(queries, records, config=config())["breakdowns"]["calibration_by_arity"]["arity"]
    assert suppressed == {"2": {"n": 5, "suppressed": True}, "4": {"n": 5, "suppressed": True}}


def test_the_expected_values_are_the_probe_values(reference):
    probe = reference["completion"]
    assert (probe["C1_no_ties"]["optimistic"], probe["C1_no_ties"]["rr_realistic"]) == (3, round(1 / 3, 6))
    assert (probe["C2_raw"]["rr_realistic"], probe["C2_filtered"]["rr_realistic"]) == (0.5, 1.0)
    c3 = probe["C3_four_way_tie"]
    assert (c3["optimistic"], c3["pessimistic"], c3["realistic"], c3["rr_realistic"]) == (1, 4, 2.5, 0.4)
    assert (c3["expected_rr_random_ties"], c3["expected_hits1"], c3["expected_hits3"]) == \
        (round(25 / 48, 6), 0.25, 0.75)
    assert probe["C4_averaging"] == {"macro_over_arity_mrr": 0.55, "per_fact_mrr": 0.55, "per_task_mrr": 0.4}
    assert (probe["C5_time_agnostic_filter"]["optimistic"], probe["C5_time_aware_filter"]["optimistic"]) == (1, 2)
    assert (probe["C6_exact_filter"]["optimistic"], probe["C6_monotone_filter"]["optimistic"]) == (2, 1)
    assert probe["C7_calibration"] == {"accuracy": 0.5, "brier_top1": 0.1965, "ece_10_bins": 0.13,
                                       "mean_confidence": 0.63}
    assert probe["C8_ece_by_arity"] == {"arity2": 0.25, "arity4": 0.19}
