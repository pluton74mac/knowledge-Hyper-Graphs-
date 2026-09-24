"""The percentile bootstrap (DESIGN §9.1, §9.7): random.Random(seed), indices int(rng.random() * n), positions
⌊0.025·R⌋ and ⌊0.975·R⌋ − 1, and the paired bootstrap on one index sequence. The last test pins one interval of each
scorer against the procedure written out here."""
from __future__ import annotations

import copy
import math
import random
from fractions import Fraction

import pytest

from khg_contracts import data
from khg_contracts.scorers import Bootstrap, completion, extraction, memory, retrieval
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


def documented(units, statistic=None):
    """DESIGN §9.1 written out: random.Random(0); 1,000 resamples of n indices int(rng.random() * n); the sorted
    statistics (the fsum mean by default; undefined ones left out) at ⌊0.025·R⌋ and ⌊0.975·R⌋ − 1."""
    rng = random.Random(0)
    n = len(units)
    stats = []
    for _ in range(1000):
        sample = [units[int(rng.random() * n)] for _ in range(n)]
        value = math.fsum(float(x) for x in sample) / n if statistic is None else statistic(sample)
        if value is not None:
            stats.append(float(value))
    stats.sort()
    return [stats[math.floor(Fraction(1, 40) * len(stats))], stats[math.floor(Fraction(39, 40) * len(stats)) - 1]]


def test_every_scorer_reports_the_documented_interval(build, r05_schema, fixture_schema):
    """One interval of each scorer, pinned against ``documented`` on the scorer's own per-unit values: a wrong
    statistic (the strict values under ``acc_lenient``) or seed used to survive the suite, which only checked that
    the bounds bracket the point estimate (review f-scorers-14)."""
    items = data.load_jsonl("fixture/c4-items.jsonl")
    # memory: the kings question ten times, answered current, hedged, stale or not at all
    base = next(x for x in items if x.get("qid") == "mq:king-1700")
    trace = next(x for x in items if x.get("trace_id") == "t:kings" and x["kind"] == "c4-memory-trace")
    new, old = {"entity": "ex:LouisXIV"}, {"entity": "ex:LouisXIII"}
    answers = [[new]] * 4 + [[old, new]] * 3 + [[old]] * 2 + [[]]
    qs = [dict(copy.deepcopy(base), qid=f"mq:b{i}", id=f"c4:mq-b{i}") for i in range(10)]
    rs = [{"kind": "memory-response", "qid": q["qid"], "answer": {"values": a, "abstained": not a}}
          for q, a in zip(qs, answers, strict=True)]
    rep = memory.score(qs, rs, traces=[trace], schema=fixture_schema)
    strict = [rep["items"][q["qid"]]["strict"] for q in qs]
    lenient = [rep["items"][q["qid"]]["lenient"] for q in qs]
    assert strict != lenient
    assert rep["bootstrap"]["intervals"] == {"acc_strict": documented(strict), "acc_lenient": documented(lenient)}
    # completion: the fixture's queries at ranks 1 to 5
    records = completion.build_queries(data.load_json("fixture/fixture.c1.json")["records"], fixture_schema)
    outputs = [{"kind": "completion-rank", "qid": q["qid"], "n_candidates": 20, "n_filtered_out": 0,
                "n_greater": n % 5, "n_equal": 0} for n, q in enumerate(records)]
    rep = completion.score(records, outputs)
    rr = [rep["items"][q["qid"]]["rr"] for q in records]
    assert rep["bootstrap"]["intervals"]["mrr"] == documented(rr)
    assert rep["bootstrap"]["intervals"]["hits@3"] == documented([rep["items"][q["qid"]]["hits@3"] for q in records])
    # retrieval: answer EM over the answerable questions
    questions = [build.question(f"q{n}", [["h1"]], answer={"values": [{"entity": "t:x"}]}) for n in range(8)]
    responses = [build.response(f"q{n}", ["h1"], answer={"values": [{"entity": "t:x" if n % 3 else "t:y"}],
                                                        "abstained": False}) for n in range(8)]
    rep = retrieval.score(questions, responses)
    em = [rep["items"][q["qid"]]["em"] for q in questions]
    assert rep["bootstrap"]["intervals"]["em"] == documented(em)
    # extraction: strict F1 over documents, each with its counts summed over the runs
    f = build.fact
    gold = [build.doc(f"d{n}", [f(f"g{n}", "s", A=f"a{n}", B="b"), f(f"h{n}", "s", A=f"c{n}", B="b")])
            for n in range(5)]
    preds = [build.items(f("x", "s", A=f"a{n}", B="b" if n % 2 else "z"), doc_id=f"d{n}") for n in range(5)]
    preds += [build.items(f("y", "s", A=f"c{n}", B="b"), doc_id=f"d{n}", run="run-2") for n in range(3)]
    rep = extraction.score(gold, preds, schema=r05_schema)
    units = [(sum(r["strict_tp"] for r in rep["items"][d]["runs"]), sum(r["n_pred"] for r in rep["items"][d]["runs"]),
              rep["items"][d]["n_gold"] * len(rep["items"][d]["runs"])) for d in sorted(rep["items"])]

    def strict_f1(sample):
        tp, n_pred, n_gold = (sum(u[i] for u in sample) for i in range(3))
        p, r = Fraction(tp, n_pred) if n_pred else Fraction(0), Fraction(tp, n_gold) if n_gold else Fraction(0)
        return 2 * p * r / (p + r) if p + r else Fraction(0)

    assert rep["bootstrap"]["intervals"]["strict.f1"] == documented(units, strict_f1)
    assert rep["bootstrap"]["intervals"]["strict.f1"][0] < rep["bootstrap"]["intervals"]["strict.f1"][1]
