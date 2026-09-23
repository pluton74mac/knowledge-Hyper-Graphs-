"""Calibration measures (DESIGN §9.3, §9.7): equal-width and equal-mass ECE, Brier and the reliability table, with
the hand values of C7, C7b and C8."""
from __future__ import annotations

from fractions import Fraction as F

import pytest

from khg_contracts.scorers import calibration as C

CONF7 = [0.95] * 4 + [0.55] * 4 + [0.15] * 2
CORR7 = [1, 1, 1, 0, 1, 1, 0, 0, 0, 0]


def test_c7_hand_values():
    assert C.ece(CONF7, CORR7, m=10) == F(13, 100)
    assert C.ece(CONF7, CORR7, m=15) == F(13, 100)
    assert C.ece(CONF7, CORR7, m=15, binning="equal_mass") == F(13, 100)
    assert C.brier(CONF7, CORR7) == F(393, 2000)


def test_c7b_equal_width_against_equal_mass():
    assert C.ece([0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1], m=2) == F(1, 4)
    assert C.ece([0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1], m=2, binning="equal_mass") == F(2, 5)


def test_c8_by_arity():
    assert C.ece(CONF7[:5], CORR7[:5], m=10) == F(1, 4) == C.ece(CONF7[:5], CORR7[:5])
    assert C.ece(CONF7[5:], CORR7[5:], m=10) == F(19, 100) == C.ece(CONF7[5:], CORR7[5:])


def test_equal_width_bins_are_right_closed():
    """(i/M, (i+1)/M]: 0.2 falls in (0.1, 0.2] at M = 10, and 0 in the first bin; decimals are read exactly."""
    groups = C.bins([0.2, 0.0, 0.1, 1.0, 0.25], [1, 0, 0, 1, 0], m=10)
    assert [[float(c) for c, _ in g] for g in groups] == [[0.0, 0.1], [0.2], [0.25], [1.0]]


def test_equal_mass_never_splits_ties():
    """B = min(M, distinct confidences); each cut ends the run of ties that holds position ⌈i·n/B⌉."""
    conf = [0.1, 0.5, 0.5, 0.5, 0.5, 0.9]
    groups = C.bins(conf, [0] * 6, m=3, binning="equal_mass")
    assert [[float(c) for c, _ in g] for g in groups] == [[0.1, 0.5, 0.5, 0.5, 0.5], [0.9]]
    assert [len(g) for g in C.bins([0.3] * 5, [1] * 5, m=15, binning="equal_mass")] == [5]
    assert [len(g) for g in C.bins([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], [0] * 6, m=3, binning="equal_mass")] == [2, 2, 2]


def test_reliability_table():
    rows = C.reliability(CONF7, CORR7, m=10)
    assert rows == [{"n": 2, "accuracy": 0.0, "confidence": 0.15, "min_confidence": 0.15, "max_confidence": 0.15},
                    {"n": 4, "accuracy": 0.5, "confidence": 0.55, "min_confidence": 0.55, "max_confidence": 0.55},
                    {"n": 4, "accuracy": 0.75, "confidence": 0.95, "min_confidence": 0.95, "max_confidence": 0.95}]


def test_empty_and_bad_inputs():
    assert C.ece([], []) == 0 and C.brier([], []) is None and C.bins([], []) == []
    for conf, corr in (([1.5], [1]), ([0.5], [2]), ([0.5], [1, 0]), ([True], [1])):
        with pytest.raises(ValueError):
            C.ece(conf, corr)
    with pytest.raises(ValueError):
        C.ece([0.5], [1], m=0)
    with pytest.raises(ValueError):
        C.ece([0.5], [1], binning="adaptive")
