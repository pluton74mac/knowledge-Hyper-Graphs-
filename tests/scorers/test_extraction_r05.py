"""R05 §2.7 extraction tables E1-E11, E5b and E5c through ``extraction.score`` (DESIGN §9.7). The expected values
are those of research/probes/scorers/c5_reference_cases.py, written as exact fractions; the last test checks them
against the probe's output."""
from __future__ import annotations

from fractions import Fraction as F

import pytest

from khg_contracts.scorers import extraction
from khg_contracts.scorers.bootstrap import Bootstrap

NO_BOOT = extraction.ExtractionConfig(bootstrap=Bootstrap(resamples=0))


def run(build, schema, gold, preds, config=NO_BOOT):
    items = [build.items(p) for p in preds]
    return extraction.score([build.doc("d1", gold)], items, schema=schema, config=config)["aggregate"]


def cases(build):
    """The R05 extraction cases: (id, gold, predictions)."""
    f = build.fact
    g4 = f("g1", "r", A="a", B="b", C="c", D="d")
    return {
        "E1_perfect": ([g4], [f("p1", "r", A="a", B="b", C="c", D="d")]),
        "E2_no_predictions": ([g4], []),
        "E3_both_empty": ([], []),
        "E4_arity_3_vs_4": ([g4], [f("p1", "r", A="a", B="b", C="c")]),
        "E5_role_swap": ([f("g1", "r", A="a", B="b")], [f("p1", "r", A="b", B="a")]),
        "E5b_partial_role_swap": ([f("g1", "r", A="a", B="b", C="c")], [f("p1", "r", A="b", B="a", C="c")]),
        "E5c_wrong_relation": ([f("g1", "r", A="a", B="b")], [f("p1", "s", A="a", B="b")]),
        "E6_duplicate_prediction": ([f("g1", "r", A="a", B="b")], [f("p1", "r", A="a", B="b"),
                                                                   f("p2", "r", A="a", B="b")]),
        "E7_one_pred_two_gold": ([f("g1", "r", A="a", B="b", C="c"), f("g2", "r", A="a", B="b", C="d")],
                                 [f("p1", "r", A="a", B="b", C="c")]),
        "E8_hungarian_vs_greedy": ([f("g1", "r", A="a", B="b", C="c", E="e"), f("g2", "r", A="a", B="b", D="d")],
                                   [f("p1", "r", A="a", B="b", C="c"), f("p2", "r", C="c", E="e")]),
        "E10_core_vs_strict": ([f("g1", "r", A="a", B="b", Q="q")], [f("p1", "r", A="a", B="b", Q="z")]),
    }


# (p, r, f1) per level; flag None unless stated; the probe's rounded values are checked in the last test
ONE, ZERO = (F(1), F(1), F(1)), (F(0), F(0), F(0))
EXPECTED = {
    "E1_perfect": {"strict": ONE, "arg_i": ONE, "arg_c": ONE, "pooled": ONE, "pairwise": ONE,
                   "participant_set": ONE, "role_accuracy": F(1), "grouping_gap_f1": F(0),
                   "n_duplicates_removed": 0},
    "E2_no_predictions": {"strict": ZERO, "arg_i": ZERO, "arg_c": ZERO, "pooled": ZERO, "pairwise": ZERO,
                          "participant_set": ZERO, "role_accuracy": None, "grouping_gap_f1": F(0),
                          "flag": "no_predictions"},
    "E3_both_empty": {"strict": ONE, "arg_i": ONE, "arg_c": ONE, "pooled": ONE, "pairwise": ONE,
                      "participant_set": ONE, "role_accuracy": None, "grouping_gap_f1": F(0), "flag": "both_empty"},
    "E4_arity_3_vs_4": {"strict": ZERO, "core": ONE, "arg_i": (F(1), F(3, 4), F(6, 7)),
                        "arg_c": (F(1), F(3, 4), F(6, 7)), "pooled": (F(1), F(3, 4), F(6, 7)),
                        "pairwise": (F(1), F(1, 2), F(2, 3)), "participant_set": ZERO, "role_accuracy": F(1),
                        "grouping_gap_f1": F(0)},
    "E5_role_swap": {"strict": ZERO, "arg_i": ONE, "arg_c": ZERO, "pooled": ZERO, "pairwise": ZERO,
                     "participant_set": ONE, "role_accuracy": F(0)},
    "E5b_partial_role_swap": {"strict": ZERO, "arg_i": ONE, "arg_c": (F(1, 3), F(1, 3), F(1, 3)),
                              "pooled": (F(1, 3), F(1, 3), F(1, 3)), "pairwise": ZERO, "participant_set": ONE,
                              "role_accuracy": F(1, 3)},
    "E5c_wrong_relation": {"strict": ZERO, "arg_i": ZERO, "arg_c": ZERO, "pooled": ZERO, "pairwise": ZERO,
                           "participant_set": ONE, "role_accuracy": None},
    "E6_duplicate_prediction": {"strict": ONE, "arg_i": ONE, "arg_c": ONE, "pooled": ONE, "pairwise": ONE,
                                "participant_set": ONE, "role_accuracy": F(1), "n_duplicates_removed": 1},
    "E7_one_pred_two_gold": {"strict": (F(1), F(1, 2), F(2, 3)), "arg_i": (F(1), F(1, 2), F(2, 3)),
                             "arg_c": (F(1), F(1, 2), F(2, 3)), "pooled": (F(1), F(3, 4), F(6, 7)),
                             "grouping_gap_f1": F(6, 7) - F(2, 3), "pairwise": (F(1), F(3, 5), F(3, 4)),
                             "participant_set": (F(1), F(1, 2), F(2, 3)), "role_accuracy": F(1)},
    "E8_hungarian_vs_greedy": {"strict": ZERO, "arg_i": (F(4, 5), F(4, 7), F(2, 3)),
                               "arg_c": (F(4, 5), F(4, 7), F(2, 3)), "pooled": (F(1), F(4, 5), F(8, 9)),
                               "grouping_gap_f1": F(8, 9) - F(2, 3), "pairwise": (F(1), F(1, 2), F(2, 3)),
                               "participant_set": ZERO, "role_accuracy": F(1)},
    "E10_core_vs_strict": {"strict": ZERO, "core": ONE, "arg_i": (F(2, 3), F(2, 3), F(2, 3)),
                           "arg_c": (F(2, 3), F(2, 3), F(2, 3)), "pooled": (F(2, 3), F(2, 3), F(2, 3)),
                           "pairwise": (F(1, 3), F(1, 3), F(1, 3)), "participant_set": ZERO, "role_accuracy": F(1)},
}


def _check(agg, expected):
    flag = expected.get("flag")
    for level, want in expected.items():
        if level in ("flag",):
            continue
        got = agg[level]
        if isinstance(want, tuple):
            assert (got["p"], got["r"], got["f1"]) == tuple(float(x) for x in want), level
            assert got["flag"] == flag, level
        elif want is None:
            assert got is None, level
        else:
            assert got == (float(want) if isinstance(want, F) else want), level


@pytest.mark.parametrize("case", sorted(EXPECTED))
def test_extraction_table(case, build, r05_schema):
    gold, preds = cases(build)[case]
    agg = run(build, r05_schema, gold, preds)
    _check(agg, EXPECTED[case])


def test_e4_counts_and_the_arity_bins(build, r05_schema):
    gold, preds = cases(build)["E4_arity_3_vs_4"]
    items = [build.items(p) for p in preds]
    rep = extraction.score([build.doc("d1", gold)], items, schema=r05_schema, config=NO_BOOT)
    agg = rep["aggregate"]
    assert agg["arg_c"]["tp"] == 3 and agg["arg_c"]["n_pred"] == 3 and agg["arg_c"]["n_gold"] == 4
    # an aligned pair counts for recall in the gold bin and for precision in the predicted bin
    bins = rep["breakdowns"]["by_arity"]["arity"]
    assert bins["3"]["arg_c"]["p"] == 1.0 and bins["3"]["arg_c"]["n_gold"] == 0
    assert bins["4"]["arg_c"]["r"] == 0.75 and bins["4"]["arg_c"]["n_pred"] == 0
    assert rep["breakdowns"]["aligned_arity_pairs"] == [{"pred_arity": 3, "gold_arity": 4, "n": 1}]
    assert rep["items"]["d1"]["runs"][0]["aligned"] == [{"pred": "q:000001", "gold": "g1", "nu": 3, "beta": 3}]


def test_e8_hungarian_beats_greedy(build, r05_schema):
    """The optimal alignment's Arg-C total is 4 (P 4/5, R 4/7); greedy on the overlap matrix [[3, 2], [2, 0]]
    takes 3 and scores F1 1/2 (R05 §2.5 item 4)."""
    gold, preds = cases(build)["E8_hungarian_vs_greedy"]
    items = [build.items(p) for p in preds]
    rep = extraction.score([build.doc("d1", gold)], items, schema=r05_schema, config=NO_BOOT)
    aligned = rep["items"]["d1"]["runs"][0]["aligned"]
    assert sum(a["beta"] for a in aligned) == 4
    assert {(a["pred"], a["gold"]) for a in aligned} == {("q:000001", "g2"), ("q:000002", "g1")}
    overlap = [[3, 2], [2, 0]]
    used_p, used_g, greedy = set(), set(), 0
    for w, i, j in sorted(((overlap[i][j], i, j) for i in range(2) for j in range(2)), reverse=True):
        if i not in used_p and j not in used_g and w > 0:
            used_p.add(i)
            used_g.add(j)
            greedy += w
    assert greedy == 3
    p, r = F(greedy, 5), F(greedy, 7)
    assert 2 * p * r / (p + r) == F(1, 2)
    assert rep["aggregate"]["arg_c"]["f1"] == float(F(2, 3))


def test_e6_nested_loop_counting_is_the_preset_pitfall(build, fixture_schema):
    """After dedup P = R = 1; HyperRED's nested-loop counting over lists (the preset) credits the duplicate twice,
    TP 2 and R 2.0 (R05 §2.5 item 2). The preset needs a relation with a primary subject and object."""
    king = build.literal_fact("g1", "position_held", [("holder", {"entity": "ex:LouisXIV"}),
                                                      ("position", {"entity": "ex:KingOfFrance"})])
    items = [build.items(dict(king, id="p1")), build.items(dict(king, id="p2"))]
    config = extraction.ExtractionConfig(preset="hyperred_quintuplet", bootstrap=Bootstrap(resamples=0))
    agg = extraction.score([build.doc("d1", [king])], items, schema=fixture_schema, config=config)["aggregate"]
    assert agg["strict"]["p"] == agg["strict"]["r"] == 1.0 and agg["n_duplicates_removed"] == 1
    preset = agg["preset"]
    assert (preset["tp"], preset["n_pred"], preset["n_gold"]) == (2, 2, 1)
    assert preset["p"] == 1.0 and preset["r"] == 2.0 and preset["counting"] == "nested_loop"


def test_e9_date_precision(build, fixture_schema):
    """``truncate_to_gold``: a day-precision prediction matches a year gold; ``exact`` does not; a year prediction
    against a day gold never matches."""
    def pop(fid, when):
        return build.literal_fact(fid, "population", [
            ("place", {"entity": "ex:Łódź"}),
            ("quantity", {"literal": {"datatype": "quantity", "amount": "+679941", "unit": "1"}}),
            ("point_in_time", when)])

    year, day = build.time("+1921-00-00T00:00:00Z", 9), build.time("+1921-05-02T00:00:00Z", 11)

    def strict(gold_when, pred_when, rule):
        items = [build.items(pop("p", pred_when))]
        config = extraction.ExtractionConfig(literal_match=rule, bootstrap=Bootstrap(resamples=0))
        rep = extraction.score([build.doc("d1", [pop("g", gold_when)])], items, schema=fixture_schema, config=config)
        return rep["aggregate"]["strict"]["tp"]

    assert strict(year, day, "truncate_to_gold") == 1
    assert strict(year, day, "exact") == 0
    assert strict(day, year, "truncate_to_gold") == 0
    assert strict(day, day, "exact") == 1


def test_e11_per_arity_recall(build, r05_schema):
    f = build.fact
    gold = [f("g1", "r2", A="a", B="b"), f("g2", "r4", A="a", B="b", C="c", D="d")]
    items = [build.items(f("p1", "r2", A="a", B="b"))]
    rep = extraction.score([build.doc("d1", gold)], items, schema=r05_schema, config=NO_BOOT)
    agg = rep["aggregate"]
    assert agg["strict"]["r"] == 0.5
    bins = rep["breakdowns"]["by_arity"]["arity"]
    assert bins["2"]["strict"]["r"] == 1.0 and bins["4"]["strict"]["r"] == 0.0
    assert agg["macro_arity"]["arity"]["strict"]["r"] == 0.5
    assert agg["macro_arity"]["arity"]["strict"]["p"] == 1.0  # the only predicted bin is arity 2
    # r2 and r4 hold entities only, so the literal-free arity is the same
    assert agg["macro_arity"]["model_arity"]["strict"] == agg["macro_arity"]["arity"]["strict"]


def test_the_expected_values_are_the_probe_values(reference):
    """Every expectation above equals research/probes/scorers/c5_reference_cases.out.json (6 decimals)."""
    probe = reference["extraction"]
    names = {"strict": "strict", "arg_i": "arg_identification", "arg_c": "arg_classification",
             "pooled": "pooled_binding", "pairwise": "pairwise", "participant_set": "participant_set",
             "core": "core", "role_accuracy": "role_accuracy", "grouping_gap_f1": "grouping_gap_f1",
             "n_duplicates_removed": "n_duplicates_removed"}
    for case, levels in EXPECTED.items():
        for level, want in levels.items():
            if level == "flag":
                continue
            got = probe[case][names[level]]
            if isinstance(want, tuple):
                assert [got["p"], got["r"], got["f1"]] == [round(float(x), 6) for x in want], (case, level)
                assert got["flag"] == levels.get("flag"), (case, level)
            elif want is None:
                assert got is None, (case, level)
            else:
                assert got == round(float(want), 6), (case, level)
    assert probe["E8_hungarian_vs_greedy"]["binding_greedy"]["f1"] == 0.5
    assert probe["E6_nested_loop_counting"] == {"tp": 2, "p": 1.0, "r": 2.0}
    e11 = probe["E11_per_arity"]
    assert (e11["micro_recall"], e11["recall_arity2"], e11["recall_arity4"], e11["macro_over_arity_recall"]) == \
        (0.5, 1.0, 0.0, 0.5)
    assert probe["E9_date_precision"] == {"truncate_to_gold": True, "exact": False,
                                          "coarser_prediction_truncate": False}
