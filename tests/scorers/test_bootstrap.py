"""The percentile bootstrap (DESIGN §9.1, §9.7): random.Random(seed), indices int(rng.random() * n), positions
⌊0.025·R⌋ and ⌊0.975·R⌋ − 1, and the paired bootstrap on one index sequence."""
from __future__ import annotations

import random

import pytest

from khg_contracts.scorers import Bootstrap
from khg_contracts.scorers import bootstrap as B

PINNED = [0, 1, 1, 0, 1, 1, 1, 0, 1, 1]


def test_the_pinned_interval():
    assert B.mean_interval(PINNED) == [0.4, 1.0]
    assert B.mean_interval(PINNED, Bootstrap()) == B.mean_interval(PINNED, Bootstrap(resamples=1000, seed=0))


def test_the_procedure_is_the_documented_one():
    """Recompute the resample means by hand: the same index draws, sorted, positions 25 and 974."""
    rng = random.Random(0)
    n = len(PINNED)
    means = sorted(sum(PINNED[int(rng.random() * n)] for _ in range(n)) / n for _ in range(1000))
    assert B.mean_interval(PINNED) == [means[25], means[974]]
    assert B.percentile_positions(1000, 0.05) == (25, 974)
    assert B.percentile_positions(200, 0.1) == (10, 189)
    first = next(B.resample_indices(10, Bootstrap(seed=0)))
    rng = random.Random(0)
    assert first == [int(rng.random() * 10) for _ in range(10)]


def test_seeds_and_general_statistics():
    other = B.mean_interval(PINNED, Bootstrap(seed=1))
    assert other == B.mean_interval(PINNED, Bootstrap(seed=1))  # reproducible for any seed
    assert 0 <= other[0] <= 0.7 <= other[1] <= 1  # it brackets the sample mean
    ratio = B.interval([(1, 2), (0, 1), (2, 2), (1, 3)], lambda s: sum(a for a, _ in s) / sum(b for _, b in s))
    lo, hi = ratio
    assert 0 <= lo <= hi <= 1
    undefined = B.interval([None, None], lambda s: None)
    assert undefined is None
    assert B.mean_interval(PINNED, Bootstrap(resamples=0)) is None and B.mean_interval([]) is None


def test_the_paired_bootstrap_reuses_one_index_sequence():
    a = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    b = [1, 1, 0, 1, 1, 1, 0, 1, 1, 1]

    def mean(sample):
        return sum(sample) / len(sample)

    out = B.paired(a, b, mean)
    assert out["a"] == B.interval(a, mean) and out["b"] == B.interval(b, mean)
    assert out["resamples_used"] == 1000
    # b is never below a unit by unit, so on every shared resample b's mean is at least a's
    assert out["difference"][0] >= 0 and out["b_better"] > 0.9
    with pytest.raises(ValueError):
        B.paired([1], [1, 2], mean)
    assert B.paired(a, b, mean, Bootstrap(resamples=0)) is None


@pytest.mark.parametrize("bad", [dict(resamples=-1), dict(resamples=1.5), dict(seed="0"), dict(alpha=0),
                                 dict(alpha=1), dict(alpha=True)])
def test_the_settings_are_checked(bad):
    with pytest.raises(ValueError):
        Bootstrap(**bad)
