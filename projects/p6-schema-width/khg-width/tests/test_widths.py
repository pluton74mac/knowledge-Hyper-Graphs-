"""G2: widths (DESIGN §3.2-§3.4, ruling Q3).

- On R01's 400 random hypergraphs, the reported values equal an independent computation on the *unreduced* H
  (subset DP over H's own primal graph, the normal-form search on H), so the reductions are checked, not trusted;
  the width inequalities hold; every certificate (lifted ones too) validates on H.
- At ``time_limit=0.01`` the bounds still contain the truth.
- Q3: universal-role removal adds exactly 1 to tw per role; twins are never merged for tw.
"""
from __future__ import annotations

from fractions import Fraction

import pytest

from helpers import random_set
from khg_width import Hypergraph, check_hypergraph, validate
from khg_width.exact import dp_width, hd_search, rho_cost, rho_star_cost
from khg_width.reduce import primal

RANDOM = [Hypergraph.from_mapping(e) for e in random_set()]
KIND = {"hw": "hd", "ghw": "ghd", "fhw": "fhd", "tw": "td"}


def truth(h: Hypergraph) -> dict:
    """Exact widths without any reduction (small inputs only)."""
    d = h.distinct()
    verts = list(h.vertices)
    adj = {v: set() for v in verts}
    adj.update(primal(dict(d.edges)))
    tw = dp_width(verts, adj, lambda m: m.bit_count() - 1)[0]
    ghw = max(1, dp_width(verts, adj, rho_cost(verts, list(d.edges)))[0])
    fhw = max(Fraction(1), dp_width(verts, adj, rho_star_cost(verts, list(d.edges)))[0])
    hw = next(k for k in range(1, 10) if hd_search(d, k) is not None)
    return {"hw": hw, "ghw": ghw, "fhw": fhw, "tw": tw}


TRUTH = [truth(h) for h in RANDOM]


def test_random_exact_values_and_inequalities():
    counts = {"ghw<hw": 0, "fhw<ghw": 0}
    for h, t in zip(RANDOM, TRUTH):
        acy, w, dis = check_hypergraph(h, solver="python")
        assert dis == []
        got = {m: w[m].value for m in w}
        assert all(w[m].exact for m in w), (h.as_dict(), {m: w[m].show() for m in w})
        assert got == t, h.as_dict()
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
    from khg_width import width

    h = Hypergraph.from_mapping({"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"]})
    assert width(h, "fhw", solver="python").value == Fraction(3, 2)
    assert width(h, "tw", solver="python").value == 2
    assert width(h, "hw", solver="python").value == 2
