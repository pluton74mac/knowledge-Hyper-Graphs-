"""G2, G3: the class tests against the brute-force definitions (R01 §1.4), witnesses and join trees."""
from __future__ import annotations

from collections import Counter

import pytest

from helpers import brute_force_class, random_set
from khg_contracts.schema import is_alpha_acyclic
from khg_width import Hypergraph, classify
from khg_width.acyclicity import (InternalError, Witness, beta_reduce, berge, dm_reduce, gyo, running_intersection,
                                  verify_witness)
from khg_width.decomposition import validate

RANDOM = [Hypergraph.from_mapping(e) for e in random_set()]


def test_random_against_brute_force():
    """400 seeded random hypergraphs (3-7 roles, 2-7 relations): the polynomial tests agree with the definitions
    on every one, and the split by class is R01's (Berge 72, gamma 118, beta 78, alpha 31, cyclic 101)."""
    classes = Counter()
    for h in RANDOM:
        fast = classify(h).cls
        slow = brute_force_class(h.as_dict())
        assert fast == slow, h.as_dict()
        classes[fast] += 1
    assert dict(classes) == {"berge": 72, "gamma": 118, "beta": 78, "alpha": 31, "cyclic": 101}


def test_witnesses_and_join_trees():
    """Every witness satisfies its definition; every alpha-acyclic hypergraph gets a join tree that is a width-1
    HD of H; alpha agrees with P2's is_alpha_acyclic, residue included."""
    kinds = Counter()
    for h in RANDOM:
        a = classify(h)
        ok, residue = is_alpha_acyclic(h.as_dict())
        assert ok == (a.cls != "cyclic")
        if a.witness is not None:
            kinds[a.witness.kind] += 1
            target = h if a.witness.kind == "berge_cycle" else h.distinct()
            assert a.witness.complete
            assert verify_witness(target, a.witness), (h.as_dict(), a.witness)
        if a.cls == "cyclic":
            assert a.witness.value == residue
            assert a.join_tree is None
        else:
            v = validate(h, a.join_tree, kind="hd")
            assert v.ok and v.width == 1, v.failures
            g = gyo(h.edges)
            assert running_intersection(h, g.links)
    assert set(kinds) == {"berge_cycle", "gamma_triangle", "beta_cycle", "gyo_residue"}


def test_tests_implied_and_order():
    h = Hypergraph.from_mapping({"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"], "E4": ["a", "b", "c"]})
    a = classify(h)
    assert a.cls == "alpha" and a.tests == {"alpha": True, "beta": False, "gamma": None, "berge": None}
    assert a.witness.kind == "beta_cycle" and a.witness.value == ["a", "E1", "b", "E2", "c", "E3"]
    h2 = Hypergraph.from_mapping({"E1": ["x", "y"], "E2": ["x", "y", "z"]})
    a2 = classify(h2)
    assert a2.cls == "gamma" and a2.witness.value == ["y", "E1", "x", "E2"]
    assert a2.tests == {"alpha": True, "beta": True, "gamma": True, "berge": False}


def test_reductions_directly():
    tri = Hypergraph.from_mapping({"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"]})
    assert beta_reduce(tri) == frozenset("abc")
    assert dm_reduce(tri) == [frozenset("ab"), frozenset("ac"), frozenset("bc")]
    assert berge(Hypergraph.from_mapping({"E1": ["a", "b"], "E2": ["b", "c"]})) == (True, [])
    g = gyo(tri.edges)
    assert not g.acyclic and set(g.residue) == {"E1", "E2", "E3"}
    path = gyo([("E1", frozenset("ab")), ("E2", frozenset("bc")), ("E3", frozenset("cd"))])
    assert path.acyclic and len(path.links) == 2


def test_duplicates_are_berge_cycles():
    """Berge is computed on the named multi-hypergraph: two relations with one role set form a cycle."""
    h = Hypergraph.from_mapping({"R1": ["a", "b"], "R2": ["a", "b"]})
    a = classify(h)
    assert a.cls == "gamma" and a.witness.value == ["b", "R1", "a", "R2"]
    assert h.duplicate_groups == [["R1", "R2"]]


def test_bad_witness_raises():
    h = Hypergraph.from_mapping({"E1": ["a", "b"], "E2": ["b", "c"]})
    assert not verify_witness(h, Witness("berge_cycle", ["a", "E1", "c", "E2"]))
    assert not verify_witness(h, Witness("gamma_triangle", ["a", "b", "c"]))
    from khg_width.acyclicity import _verify

    with pytest.raises(InternalError):
        _verify(h, Witness("berge_cycle", ["a", "E1", "c", "E2"]))


def test_large_relation_local_classifies_fast():
    """Relation-local controls are disjoint relations; a 3,000-relation one classifies in well under a second
    (DESIGN §7: the indexed loops; observed-all under relation-local must take under 30 s)."""
    import time

    h = Hypergraph(tuple((f"P{i}", frozenset(f"P{i}:r{j}" for j in range(2 + i % 30))) for i in range(3000)))
    t0 = time.monotonic()
    a = classify(h)
    assert a.cls == "berge"
    assert time.monotonic() - t0 < 10
