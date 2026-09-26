"""P2 ruling 21 (c): the order effect S-M7 of ``stability.score`` is the paired decomposition (DESIGN §9.3), P9's
fix of a scorer defect (P9 DESIGN §4; P9 ruling 5).

S-M7 of ``khg-scorers`` 1.0 compared the pairs of (run_id, order_id) units with the same order (which differ in run)
with the pairs of different orders, pooling the pairs of the same run with those of different runs. When runs are
paired (the same seed, or an extractor that ignores the order), same-run pairs agree more, so Δ_order came out
negative with no order effect at all (−61/378 on P9's fixture). Now:

- the three pair classes: ``same_order_diff_run`` (run noise), ``same_run_diff_order`` (the order effect, plus run
  noise when runs are independent samples) and ``diff_run_diff_order``, each ``{n_pairs, mean_jaccard}``;
- ``delta_order`` = J(same order, other run) − J(other order, other run): both terms differ in run, so it is the
  agreement lost when the order changes as well, paired runs or not;
- 1.0's number is kept as ``pooled_delta_order`` (with ``J_within``, ``J_between`` and the pair counts), for
  continuity with reports of 1.0 only.
"""
from __future__ import annotations

from fractions import Fraction as F

from khg_contracts.scorers import stability


def items(build, runs: dict[tuple[str, str], str]) -> list:
    """One item per fact label: ``{(run, order): "ab"}`` gives facts a and b in that unit, all from d1."""
    out = []
    for (run, order), labels in runs.items():
        out += [build.items(build.fact("f:" + x, "s", A=x), run=run, order=order) for x in labels]
    return out


def order_effect(build, r05_schema, runs) -> dict:
    return stability.score(items(build, runs), schema=r05_schema, keys=("content_key",))["aggregate"][
        "content_key"]["order_effect"]


def test_an_extractor_that_ignores_the_order_has_no_order_effect(build, r05_schema):
    """P9's case, small: runs differ (r2 finds c instead of b), each run gives the same output in both orders."""
    runs = {(r, o): out for o in ("o1", "o2") for r, out in (("r1", "ab"), ("r2", "ac"), ("r3", "ab"))}
    oe = order_effect(build, r05_schema, runs)
    assert oe["same_order_diff_run"] == {"n_pairs": 6, "mean_jaccard": float(F(5, 9))}
    assert oe["same_run_diff_order"] == {"n_pairs": 3, "mean_jaccard": 1.0}
    assert oe["diff_run_diff_order"] == {"n_pairs": 6, "mean_jaccard": float(F(5, 9))}
    assert oe["delta_order"] == 0.0
    # 1.0's pooled number: J_between pools 3 same-run pairs (1) with 6 cross-run pairs (5/9)
    assert (oe["n_within_pairs"], oe["n_between_pairs"]) == (6, 9)
    assert (oe["J_within"], oe["J_between"]) == (float(F(5, 9)), float(F(19, 27)))
    assert oe["pooled_delta_order"] == float(F(-4, 27))


def test_s3_keeps_its_value_and_shows_its_pairs(build, r05_schema):
    """R05 S3: no run noise, O1 gives {a, b} and O2 {a, c}; the paired and the pooled numbers agree (2/3)."""
    runs = {(f"s{s}", o): ("ab" if o == "O1" else "ac") for o in ("O1", "O2") for s in (1, 2, 3)}
    oe = order_effect(build, r05_schema, runs)
    assert oe["same_order_diff_run"] == {"n_pairs": 6, "mean_jaccard": 1.0}
    assert oe["same_run_diff_order"] == {"n_pairs": 3, "mean_jaccard": float(F(1, 3))}
    assert oe["diff_run_diff_order"] == {"n_pairs": 6, "mean_jaccard": float(F(1, 3))}
    assert oe["delta_order"] == oe["pooled_delta_order"] == float(F(2, 3))


def test_an_order_effect_under_run_noise(build, r05_schema):
    """Independent samples: in o1 the runs find {a, b}, {a, c}, {a, b}; in o2 the order adds d to every run."""
    runs = {}
    for r, out in (("r1", "ab"), ("r2", "ac"), ("r3", "ab")):
        runs[r, "o1"], runs[r, "o2"] = out, out + "d"
    oe = order_effect(build, r05_schema, runs)
    # same order: o1 pairs 1/3, 1, 1/3 and o2 pairs 2/4, 1, 2/4
    assert oe["same_order_diff_run"]["mean_jaccard"] == float((F(1, 3) + 1 + F(1, 3) + F(1, 2) + 1 + F(1, 2)) / 6)
    # same run: {a, b} against {a, b, d} is 2/3, three times
    assert oe["same_run_diff_order"] == {"n_pairs": 3, "mean_jaccard": float(F(2, 3))}
    cross = [F(1, 4), F(2, 3), F(1, 4), F(1, 4), F(2, 3), F(1, 4)]  # {a,b} vs {a,c,d}, {a,b,d}, ...
    assert oe["diff_run_diff_order"] == {"n_pairs": 6, "mean_jaccard": float(sum(cross) / 6)}
    assert oe["delta_order"] == float((F(1, 3) + 1 + F(1, 3) + F(1, 2) + 1 + F(1, 2)) / 6 - sum(cross) / 6)
    assert oe["delta_order"] > 0


def test_an_empty_pair_class_gives_no_delta(build, r05_schema):
    """One run in two orders: no pair differs in run, so neither Δ can be computed."""
    oe = order_effect(build, r05_schema, {("r1", "o1"): "ab", ("r1", "o2"): "ac"})
    assert oe["same_order_diff_run"] == {"n_pairs": 0, "mean_jaccard": None}
    assert oe["same_run_diff_order"] == {"n_pairs": 1, "mean_jaccard": float(F(1, 3))}
    assert oe["diff_run_diff_order"] == {"n_pairs": 0, "mean_jaccard": None}
    assert oe["delta_order"] is None and oe["pooled_delta_order"] is None
