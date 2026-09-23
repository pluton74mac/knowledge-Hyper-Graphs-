"""R05 §2.7 stability tables S1-S4 through ``stability.score`` (DESIGN §9.7), on C3 queue items. A fact ``x`` of
the tables is ``s(A: t:x)`` extracted from document d1."""
from __future__ import annotations

from fractions import Fraction as F

from khg_contracts.scorers import stability


def run_items(build, run, order, labels, doc_id="d1"):
    return [build.items(build.fact("f:" + x, "s", A=x), run=run, order=order, doc_id=doc_id) for x in labels]


def test_s1_three_runs(build, r05_schema):
    items = (run_items(build, "r1", "o1", "abc") + run_items(build, "r2", "o1", "abd")
             + run_items(build, "r3", "o1", "abc"))
    rep = stability.score(items, schema=r05_schema)
    for key in ("content_key", "core_key"):  # s has only core roles: both keys agree
        agg = rep["aggregate"][key]
        assert agg["pairwise_jaccard"] == [0.5, 1.0, 0.5]
        assert agg["mean_pairwise_jaccard"] == float(F(2, 3))
        assert agg["core_ratio"] == 0.5 and agg["n_facts"] == 4
        assert agg["support_histogram"] == {"1": 1, "2": 1, "3": 2}
        assert agg["unstable_fraction"] == 0.5
        assert agg["mean_churn"] == float(F(1, 3))
    assert rep["aggregate"]["units"] == [{"run_id": "r1", "order_id": "o1"}, {"run_id": "r2", "order_id": "o1"},
                                         {"run_id": "r3", "order_id": "o1"}]
    assert rep["breakdowns"]["by_unit"][1] == {"run_id": "r2", "order_id": "o1",
                                               "n_facts": {"content_key": 3, "core_key": 3}}


def test_s2_all_empty(build, r05_schema):
    """Three runs that extract nothing from d-empty: J = 1 by convention, flagged in n_empty_pairs; churn 0."""
    items = run_items(build, "r1", "o1", "x", "d-other") + run_items(build, "r2", "o1", "x", "d-other") + \
        run_items(build, "r3", "o1", "x", "d-other")
    gold = [build.doc("d-empty", [build.fact("g1", "s", A="g")])]
    rep = stability.score(items, schema=r05_schema, gold=gold)
    empty = rep["items"]["d-empty"]["content_key"]
    assert empty["pairwise_jaccard"] == [1.0, 1.0, 1.0] and empty["mean_pairwise_jaccard"] == 1.0
    assert empty["n_empty_pairs"] == 3 and empty["n_facts"] == 0
    assert rep["items"]["d-empty"]["depends_on"] == ["g1"]
    other = rep["items"]["d-other"]["content_key"]
    assert other["n_empty_pairs"] == 0 and other["mean_pairwise_jaccard"] == 1.0
    agg = rep["aggregate"]["content_key"]
    assert agg["mean_churn"] == 0.0 and agg["unstable_fraction"] == 0.0 and agg["core_ratio"] == 1.0
    # the per-document mean only averages documents with output
    assert agg["per_document_mean_jaccard"] == 1.0


def test_s3_order_effect(build, r05_schema):
    items = []
    for s in (1, 2, 3):
        items += run_items(build, f"s{s}", "O1", "ab")
    for s in (1, 2, 3):
        items += run_items(build, f"s{s}", "O2", "ac")
    rep = stability.score(items, schema=r05_schema, keys=("content_key",))
    effect = rep["aggregate"]["content_key"]["order_effect"]
    assert effect == {"n_within_pairs": 6, "n_between_pairs": 9, "J_within": 1.0, "J_between": float(F(1, 3)),
                      "delta_order": float(F(2, 3))}
    assert "core_key" not in rep["aggregate"]
    # pooling the orders of a run: three units, identical sets; the order effect still reads (run_id, order_id)
    pooled = stability.score(items, schema=r05_schema, unit="run_id", keys=("content_key",))
    assert pooled["aggregate"]["n_units"] == 3 and pooled["aggregate"]["units"] == [
        {"run_id": "s1"}, {"run_id": "s2"}, {"run_id": "s3"}]
    assert pooled["aggregate"]["content_key"]["mean_pairwise_jaccard"] == 1.0
    assert pooled["aggregate"]["content_key"]["order_effect"] == effect


def test_s4_gold_partition(build, r05_schema):
    gold = [build.doc("d1", [build.fact(f"g{i}", "s", A=f"g{i}") for i in (1, 2, 3)])]
    items = run_items(build, "r1", "o1", ["g1", "g2"]) + run_items(build, "r2", "o1", ["g1"]) + \
        run_items(build, "r3", "o1", ["g1"])
    rep = stability.score(items, schema=r05_schema, gold=gold)
    part = rep["aggregate"]["content_key"]["gold_partition"]
    assert part == {"stable": float(F(1, 3)), "unstable": float(F(1, 3)), "miss": float(F(1, 3)), "n_gold": 3}
    assert rep["config"]["qset"] == ["r05"]


def test_the_expected_values_are_the_probe_values(reference):
    probe = reference["stability"]
    s1 = probe["S1_three_runs"]
    assert s1["pairwise_jaccard"] == [0.5, 1.0, 0.5] and s1["mean_pairwise_jaccard"] == round(2 / 3, 6)
    assert s1["core_ratio"] == 0.5 and s1["unstable_fraction"] == 0.5
    assert s1["mean_fact_disagreement"] == round(1 / 3, 6) and s1["support_histogram"] == {"1": 1, "2": 1, "3": 2}
    s2 = probe["S2_all_empty"]
    assert s2["mean_pairwise_jaccard"] == 1.0 and s2["mean_fact_disagreement"] == 0
    s3 = probe["S3_order_effect"]
    assert (s3["n_within_pairs"], s3["n_between_pairs"], s3["J_within"], s3["J_between"], s3["delta_order"]) == \
        (6, 9, 1.0, round(1 / 3, 6), round(2 / 3, 6))
    assert probe["S4_gold_conditioned"] == {"miss": round(1 / 3, 6), "stable": round(1 / 3, 6),
                                            "unstable": round(1 / 3, 6)}
