"""The Hungarian solver against brute force on seeded matrices (DESIGN §9.7): the pure-Python backend, and SciPy
(the ``[fast]`` extra) giving the same assignment, ties broken by lexicographic ids."""
from __future__ import annotations

import random

import pytest

from khg_contracts.scorers import hungarian


def brute_force(w):
    """Every partial 1:1 assignment; the best by (total, then row 0's column first, row 1's next, …; an unaligned
    row ranks after every alignment of it)."""
    n, m = len(w), len(w[0]) if w else 0
    best = None

    def walk(i, used, acc):
        nonlocal best
        if i == n:
            pairs = sorted((r, c) for r, c in acc if c is not None and w[r][c] > 0)
            digits = tuple(m - dict(pairs).get(r, m) for r in range(n))
            key = (sum(w[r][c] for r, c in pairs), digits)
            if best is None or key > best[0]:
                best = (key, pairs)
            return
        walk(i + 1, used, acc + [(i, None)])
        for c in range(m):
            if c not in used:
                walk(i + 1, used | {c}, acc + [(i, c)])

    walk(0, frozenset(), [])
    return best[1]


def matrices(seed, count, size=4, values=(0, 0, 1, 2, 3)):
    rng = random.Random(seed)
    for _ in range(count):
        yield [[rng.choice(values) for _ in range(size)] for _ in range(size)]


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_python_equals_brute_force_on_seeded_4x4(seed):
    for w in matrices(seed, 300):
        want = brute_force(w)
        got = hungarian.solve(w, backend="python")
        assert got == want, w
        assert hungarian.total(w, got) == hungarian.total(w, want)


def test_rectangular_and_tie_heavy_matrices():
    rng = random.Random(5)
    for _ in range(400):
        n, m = rng.randint(1, 5), rng.randint(1, 5)
        w = [[rng.choice((0, 1, 1)) for _ in range(m)] for _ in range(n)]
        assert hungarian.solve(w, backend="python") == brute_force(w), w


def test_scipy_gives_the_same_assignment():
    pytest.importorskip("scipy")
    for w in matrices(3, 300):
        assert hungarian.solve(w, backend="scipy") == brute_force(w), w
    rng = random.Random(9)
    for _ in range(10):
        n, m = rng.randint(40, 70), rng.randint(40, 70)
        w = [[rng.choice((0, 0, 1, 2, 5)) for _ in range(m)] for _ in range(n)]
        assert hungarian.solve(w, backend="scipy") == hungarian.solve(w, backend="python")
        assert hungarian.solve(w) == hungarian.solve(w, backend="python")  # auto hands these to SciPy


def test_the_tie_break_prefers_earlier_ids():
    """Two optimal alignments of equal weight: row 0 takes column 0."""
    assert hungarian.solve([[1, 1], [1, 1]]) == [(0, 0), (1, 1)]
    assert hungarian.solve([[0, 1], [1, 1]]) == [(0, 1), (1, 0)]
    # a row that no optimal alignment needs stays unaligned rather than taking a zero
    assert hungarian.solve([[2, 0], [2, 0]]) == [(0, 0)]
    assert hungarian.solve([[0, 0], [0, 3]]) == [(1, 1)]


def test_edge_cases_and_errors():
    assert hungarian.solve([]) == [] and hungarian.solve([[]]) == [] and hungarian.solve([[0, 0]]) == []
    assert hungarian.solve([[5]]) == [(0, 0)]
    for bad in ([[1, -1]], [[1.5]], [[True]], [[1, 2], [3]]):
        with pytest.raises(ValueError):
            hungarian.solve(bad)
    with pytest.raises(ValueError):
        hungarian.solve([[1]], backend="fortran")


def test_importing_the_solver_does_not_load_scipy():
    import subprocess
    import sys

    code = ("import sys\nfrom khg_contracts.scorers import hungarian\nhungarian.solve([[1, 2], [3, 4]])\n"
            "print(sorted(m for m in sys.modules if m.split('.')[0] in ('scipy', 'numpy')))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


def test_the_bipartite_matching_takes_long_augmenting_paths():
    """``_common.matching`` (the counts of the literal rule) follows augmenting paths with an explicit stack: here
    the last row can only take column 0, which shifts every earlier row by one (a path longer than Python's default
    recursion limit)."""
    from khg_contracts.scorers._common import count_matching, matching

    n = 1500
    edges = {i: (i, i + 1) for i in range(n - 1)}
    edges[n - 1] = (0,)
    got = matching(n, n, lambda i, j: j in edges[i])
    assert len(got) == n and got[n - 1] == 0 and got[0] == 1
    assert count_matching([1, 1, 2], [1, 2, 2], lambda x, y: x == y) == 2
    assert count_matching([1, 1, 2], [1, 2, 2], None, key=lambda x: x) == 2
