"""G2: edge covers (DESIGN §3.3): exact rho* with both certificates, exact rho, SciPy rounding."""
from __future__ import annotations

import itertools
from fractions import Fraction

import pytest

from khg_width.covers import fractional_cover, greedy_cover, rho, rho_star, rho_star_scipy, traces

TRI = [("E1", frozenset("ab")), ("E2", frozenset("bc")), ("E3", frozenset("ac"))]
K5 = [(f"e{i}{j}", frozenset((f"x{i}", f"x{j}"))) for i, j in itertools.combinations(range(1, 6), 2)]


def check_certificates(bag, edges, fc):
    """x covers every role at least once, y respects every edge, and sum x = sum y = value."""
    for v in bag:
        assert sum((w for n, w in fc.weights.items() if v in dict(edges)[n]), Fraction(0)) >= 1
    for _, e in edges:
        assert sum((fc.dual.get(v, Fraction(0)) for v in e & bag), Fraction(0)) <= 1
    assert sum(fc.weights.values(), Fraction(0)) == fc.value == sum(fc.dual.values(), Fraction(0))


def test_triangle_three_halves():
    bag = frozenset("abc")
    fc = rho_star(bag, TRI)
    assert fc.value == Fraction(3, 2) and fc.exact and fc.method == "exact-simplex"
    assert fc.weights == {"E1": Fraction(1, 2), "E2": Fraction(1, 2), "E3": Fraction(1, 2)}
    check_certificates(bag, TRI, fc)
    k, names = rho(bag, TRI)
    assert k == 2 and frozenset().union(*(dict(TRI)[n] for n in names)) == bag


def test_k5_five_halves():
    bag = frozenset(f"x{i}" for i in range(1, 6))
    fc = rho_star(bag, K5)
    assert fc.value == Fraction(5, 2)
    check_certificates(bag, K5, fc)
    assert rho(bag, K5)[0] == 3
    assert len(greedy_cover(bag, K5)) == 3


def test_rho_exact_beats_greedy():
    # greedy takes the big trace first and then needs two more; the optimum is 2
    edges = [("big", frozenset("bcde")), ("L", frozenset("abc")), ("R", frozenset("def"))]
    bag = frozenset("abcdef")
    assert len(greedy_cover(bag, edges)) == 3
    k, names = rho(bag, edges)
    assert k == 2 and sorted(names) == ["L", "R"]


def test_traces_are_maximal():
    edges = [("A", frozenset("abc")), ("B", frozenset("ab")), ("C", frozenset("cd")), ("D", frozenset("abcx"))]
    ts = traces(frozenset("abcd"), edges)
    assert ts == [("A", frozenset("abc")), ("C", frozenset("cd"))]
    assert len(traces(frozenset("abcd"), edges, maximal=False)) == 3


def test_fractional_cover_dispatch():
    bag = frozenset("abc")
    assert fractional_cover(bag, TRI).value == Fraction(3, 2)
    # over the exact limit without SciPy the greedy cover is used; with SciPy the rounded LP
    big = frozenset(f"v{i}" for i in range(50))
    edges = [(f"e{i}", frozenset({f"v{i}", f"v{(i + 1) % 50}"})) for i in range(50)]
    fc = fractional_cover(big, edges)
    assert fc.exact is False and fc.value >= 25
    for v in big:
        assert sum((w for n, w in fc.weights.items() if v in dict(edges)[n]), Fraction(0)) >= 1


def test_scipy_rounding():
    pytest.importorskip("scipy")
    bag = frozenset(f"x{i}" for i in range(1, 6))
    fc = rho_star_scipy(bag, K5)
    assert fc.exact is False and fc.method == "scipy-rounded"
    assert Fraction(5, 2) <= fc.value <= Fraction(5, 2) + Fraction(1, 100)
    for v in bag:
        assert sum((w for n, w in fc.weights.items() if v in dict(K5)[n]), Fraction(0)) >= 1
