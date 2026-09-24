"""G2: widths (DESIGN §3.2-§3.4, ruling Q3).

The truth comes from outside khg_width (review finding F2):

- tw, ghw and fhw of R01's 400 random hypergraphs (at most 7 roles) by brute force over every elimination ordering,
  with rho by trying every set of traces and rho* by an exact LP solved through vertex enumeration of its dual
  (``helpers.widths_by_orderings``);
- hw of those 400, of 150 denser ones and of R01's named instances as recorded from BalancedGo ``-exact -det`` and
  log-k-decomp ``-exact`` (``fixtures/random-hw.json``, written by ``record_random_hw.py``; CI needs no binaries).

Then: the reported values equal the truth, the reductions and the lifted certificates validate on H, the width
inequalities hold, and at ``time_limit=0.01`` the bounds still contain the truth. Q3: universal-role removal adds
exactly 1 to tw per role; twins are never merged for tw.
"""
from __future__ import annotations

import itertools
from fractions import Fraction

import pytest

from helpers import dense_set, named_set, random_set, recorded_hw, widths_by_orderings
from khg_width import Hypergraph, check_hypergraph, validate, width

RANDOM = [Hypergraph.from_mapping(e) for e in random_set()]
KIND = {"hw": "hd", "ghw": "ghd", "fhw": "fhd", "tw": "td"}
RECORDED = recorded_hw()


def truth(h: Hypergraph, hw: int) -> dict:
    tw, ghw, fhw = widths_by_orderings(list(dict.fromkeys(e for _, e in h.distinct().edges)))
    return {"hw": hw, "ghw": ghw, "fhw": fhw, "tw": tw}


TRUTH = [truth(h, hw) for h, hw in zip(RANDOM, RECORDED["hw"])]


def test_recorded_fixture_matches_the_generators():
    assert RECORDED["count"] == len(RANDOM) == 400 and len(RECORDED["dense_hw"]) == 150
    assert set(RECORDED["named_hw"]) == set(named_set())
    assert RECORDED["tools"]["balancedgo"]["commit"].startswith("872c662c")


def test_random_exact_values_and_inequalities():
    counts = {"ghw<hw": 0, "fhw<ghw": 0}
    for h, t in zip(RANDOM, TRUTH):
        acy, w, dis = check_hypergraph(h, solver="python")
        assert dis == []
        got = {m: w[m].value for m in w}
        assert all(w[m].exact for m in w), (h.as_dict(), {m: w[m].show() for m in w})
        assert got == t, (h.as_dict(), got, t)
        f, g, hw, tw = got["fhw"], got["ghw"], got["hw"], got["tw"]
        assert f <= g <= hw <= 3 * g + 1 and g <= tw + 1
        assert (hw == 1) == (acy.cls != "cyclic") == (g == 1) == (f == 1)
        counts["ghw<hw"] += g < hw
        counts["fhw<ghw"] += f < g
        for m in w:
            v = validate(h, w[m].certificate, kind=KIND[m])
            assert v.ok and v.width == w[m].upper, (m, v.failures)
    # R01: on this set every width invariant held; fhw < ghw occurs, ghw < hw does not
    assert counts["fhw<ghw"] > 0 and counts["ghw<hw"] == 0


def test_hw_matches_the_recorded_solvers():
    """hw of the denser random set and of R01's named instances (hw 2-3) equals BalancedGo's and log-k-decomp's
    recorded -exact values, with no disagreement."""
    cases = [(f"dense-{i}", e, hw) for i, (e, hw) in enumerate(zip(dense_set(), RECORDED["dense_hw"]))]
    cases += [(name, e, RECORDED["named_hw"][name]) for name, e in named_set().items()]
    for name, edges, hw in cases:
        h = Hypergraph.from_mapping(edges)
        w = width(h, "hw", solver="python", time_limit=30)
        assert w.exact and w.value == hw, (name, w.show(), hw)
        assert validate(h, w.certificate, kind="hd").ok


@pytest.mark.parametrize("limit", [0.01])
def test_bounds_contain_the_truth(limit):
    named = {
        "k5": {f"e{i}{j}": [f"x{i}", f"x{j}"] for i in range(1, 6) for j in range(i + 1, 6)},
        "adler": {"E1": ["V1", "V2", "V9"], "E2": ["V2", "V3", "V10"], "E3": ["V3", "V4"],
                  "E4": ["V4", "V5", "V9"], "E5": ["V5", "V6", "V10"], "E6": ["V6", "V7", "V9"],
                  "E7": ["V7", "V8", "V10"], "E8": ["V8", "V1"]},
        "grid4": {**{f"h{r}{c}": [f"r{r}c{c}", f"r{r}c{c + 1}"] for r in range(4) for c in range(3)},
                  **{f"v{r}{c}": [f"r{r}c{c}", f"r{r + 1}c{c}"] for r in range(3) for c in range(4)}},
    }
    known = {"k5": {"hw": 3, "ghw": 3, "fhw": Fraction(5, 2), "tw": 4},
             "adler": {"hw": 3, "ghw": 2, "fhw": Fraction(2), "tw": 4},
             "grid4": {"hw": 3, "ghw": 3, "fhw": Fraction(3), "tw": 4}}
    cases = [(h, t) for h, t in zip(RANDOM[::5], TRUTH[::5])]
    cases += [(Hypergraph.from_mapping(named[n]), known[n]) for n in named]
    for h, t in cases:
        _, w, _ = check_hypergraph(h, solver="python", time_limit=limit)
        for m, x in w.items():
            lo_ok = x.lower < t[m] if x.lower_exclusive else x.lower <= t[m]
            assert lo_ok and t[m] <= x.upper, (h.as_dict(), m, x.show(), t[m])
            assert validate(h, x.certificate, kind=KIND[m]).ok


def test_universal_role_adds_one_to_tw():
    """Q3: a role in every relation is removed for tw with +1; hw, ghw and fhw are unchanged by it."""
    tri = {"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"]}
    with_u = {k: v + ["u"] for k, v in tri.items()}
    _, w0, _ = check_hypergraph(Hypergraph.from_mapping(tri), solver="python")
    _, w1, _ = check_hypergraph(Hypergraph.from_mapping(with_u), solver="python")
    assert w0["tw"].value == 2 and w1["tw"].value == 3
    assert [w1[m].value for m in ("hw", "ghw", "fhw")] == [2, 2, Fraction(3, 2)]
    assert [w0[m].value for m in ("hw", "ghw", "fhw")] == [2, 2, Fraction(3, 2)]
    # and the tw certificate holds u in every bag
    assert all("u" in n.bag for n in w1["tw"].certificate)


def test_twins_not_merged_for_tw():
    """Q3: twin merging is unsound for tw (K_n); a triangle with every role doubled has a K6 primal graph."""
    h = Hypergraph.from_mapping({"E1": ["a1", "a2", "b1", "b2"], "E2": ["b1", "b2", "c1", "c2"],
                                 "E3": ["a1", "a2", "c1", "c2"]})
    acy, w, _ = check_hypergraph(h, solver="python")
    assert acy.cls == "cyclic"
    assert w["tw"].value == 5
    assert (w["hw"].value, w["ghw"].value, w["fhw"].value) == (2, 2, Fraction(3, 2))


def test_lifted_certificates_name_relations_of_h():
    """A GHD computed on the core (after GYO, twins and a universal role) is lifted to H: its guards are
    relations of H and every role of H appears."""
    h = Hypergraph.from_mapping({"sale": ["buyer", "seller", "s", "x1"], "brokerage": ["seller", "broker", "s"],
                                 "referral": ["broker", "buyer", "s", "x2", "x3"], "note": ["x2", "x3", "s"]})
    acy, w, _ = check_hypergraph(h, solver="python")
    g = w["ghw"]
    assert acy.cls == "cyclic" and g.value == 2
    names = {k for n in g.certificate for k in n.guard}
    assert names <= set(h.names)
    assert {v for n in g.certificate for v in n.bag} == set(h.vertices)
    assert validate(h, g.certificate, kind="ghd").ok


def test_empty_hypergraph():
    _, w, _ = check_hypergraph(Hypergraph(), solver="python")
    assert {m: w[m].value for m in w} == {"hw": 0, "ghw": 0, "fhw": 0, "tw": 0}


def test_width_api_single_measure():
    h = Hypergraph.from_mapping({"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"]})
    assert width(h, "fhw", solver="python").value == Fraction(3, 2)
    assert width(h, "tw", solver="python").value == 2
    assert width(h, "hw", solver="python").value == 2


def test_max_cliques_are_exactly_the_maximal_cliques():
    """The lazy Bron-Kerbosch enumeration behind the clique bounds, against brute force on 300 random graphs."""
    import itertools
    import random

    from khg_width.bounds import max_cliques

    rng = random.Random(20260924)
    for _ in range(300):
        n = rng.randint(1, 8)
        vs = [f"v{i}" for i in range(n)]
        adj = {v: set() for v in vs}
        for a, b in itertools.combinations(vs, 2):
            if rng.random() < 0.5:
                adj[a].add(b)
                adj[b].add(a)
        got = sorted(sorted(c) for c in max_cliques(adj))
        cl = [set(c) for r in range(1, n + 1) for c in itertools.combinations(vs, r)
              if all(b in adj[a] for a, b in itertools.combinations(c, 2))]
        assert got == sorted(sorted(c) for c in cl if not any(c < d for d in cl))


def test_partial_steps_are_logged():
    """F7: a step that stops at its deadline and keeps what it found says so ("timeout (partial kept)")."""
    from khg_width.bounds import clique_bounds
    from khg_width.reduce import tw_reduce
    from khg_width.steps import PARTIAL, Deadline, StepLog

    ring = Hypergraph.from_mapping({f"e{i}": [f"v{i}", f"v{(i + 1) % 600}"] for i in range(600)})
    res = clique_bounds({f"v{i}": {f"v{(i - 1) % 600}", f"v{(i + 1) % 600}"} for i in range(600)},
                        list(ring.edges), deadline=Deadline(0))
    assert res.complete is False
    log = StepLog()
    outcome, tr = log.run(lambda dl: tw_reduce(ring, deadline=dl), measure="tw", method="simplicial-rule", limit=0)
    assert outcome == PARTIAL and tr.complete is False and log.steps[-1]["outcome"] == PARTIAL
    adj = {f"v{i}": {f"v{(i - 1) % 600}", f"v{(i + 1) % 600}"} for i in range(600)}
    outcome, res = log.run(lambda dl: clique_bounds(adj, list(ring.edges), deadline=dl), measure="ghw",
                           method="clique", limit=0)
    assert outcome == PARTIAL and res.complete is False and res.seen < 600
    # a step that finishes is still "done", and one that keeps nothing is "timeout"
    assert log.run(lambda dl: clique_bounds(adj, list(ring.edges), deadline=dl), measure="ghw", method="clique",
                   limit=60)[0] == "done"
    assert log.run(lambda dl: dl.check() or dl.check(), measure="tw", method="x", limit=0)[0] in ("done", "timeout")


def test_lower_bound_witnesses():
    """F9: every lower bound carries its witness, and each witness checks out on H (a clique of H's primal graph
    with its rho and a feasible fractional dual, a minor-min-width block, the tw clique)."""
    from helpers import check_lower_witness

    # a 24-role ring with a K5 on four of its roles and one more: one block over the DP limit, with cliques
    ring = {f"c{i}": [f"v{i}", f"v{(i + 1) % 24}"] for i in range(24)}
    k5 = ["v0", "v3", "v6", "v9", "v12"]
    ring.update({f"k{a}_{b}": [a, b] for a, b in itertools.combinations(k5, 2)})
    h = Hypergraph.from_mapping(ring)
    acy, w, _ = check_hypergraph(h, solver="python", time_limit=20)
    assert w["ghw"].lower_method == "clique" and sorted(w["ghw"].lower_witness["roles"]) == sorted(k5)
    assert w["ghw"].lower == 3 and w["fhw"].lower == Fraction(5, 2) and w["fhw"].lower_method == "clique"
    checked = {m: check_lower_witness(h, m, w[m].to_json(), acy.to_json()) for m in w}
    assert checked["ghw"] == checked["fhw"] == "clique"
    # a witness that does not check out is caught
    bad = w["fhw"].to_json()
    bad["lower_witness"] = dict(bad["lower_witness"], dual={v: "1" for v in k5})
    with pytest.raises(AssertionError):
        check_lower_witness(h, "fhw", bad, acy.to_json())
    # the fixtures: every measure of every row has a witness that checks out
    from helpers import fixture_rows
    from khg_width import check, hypergraph

    for row in fixture_rows():
        rep = check(row["path"], slots=row["slot_tuple"], solver="python").to_json()
        hr = hypergraph(row["path"], slots=row["slot_tuple"])
        for m in ("hw", "ghw", "fhw", "tw"):
            check_lower_witness(hr, m, rep["widths"][m], rep["acyclicity"])
