"""G3: the checker "flags a constructed cyclic case" (DESIGN §1), and tells every class boundary apart."""
from __future__ import annotations

from helpers import FIXTURES, fixture_path
from khg_contracts.schema import is_alpha_acyclic, load_schema, schema_hypergraph
from khg_width import check

CYCLIC = ["p2:fixture/cyclic.relation-schema.json", "p2:fixture/wikidata-shaped.relation-schema.json",
          "p6-qualifier-k5.relation-schema.json", "p6-adler.relation-schema.json"]
BOUNDARY = [("p6-berge-path", "berge"), ("p6-gamma-not-berge", "gamma"), ("p6-beta-not-gamma", "beta"),
            ("p6-alpha-not-beta", "alpha"), ("p2:fixture/cyclic", "cyclic")]


def test_constructed_cyclic():
    """Each constructed cyclic schema is flagged: class cyclic, alpha failed, the witness is the GYO residue and
    equals P2's is_alpha_acyclic residue; hw and ghw are at least 2 and fhw above 1; the exit status is 0
    (tested in test_cli)."""
    for src in CYCLIC:
        path = fixture_path(src)
        rep = check(path, solver="python")
        ok, residue = is_alpha_acyclic(schema_hypergraph(load_schema(path), slots=("core", "qualifier")))
        assert ok is False
        a = rep.acyclicity
        assert a.cls == "cyclic" and a.first_failed == "alpha"
        assert a.tests == {"alpha": False, "beta": None, "gamma": None, "berge": None}
        assert a.witness.kind == "gyo_residue" and a.witness.value == residue and a.witness.complete
        assert a.join_tree is None
        assert rep.widths["hw"].lower >= 2 and rep.widths["ghw"].lower >= 2
        assert rep.widths["fhw"].upper > 1
    # P2's cyclic fixture: the residue is the triangle itself
    rep = check(fixture_path(CYCLIC[0]), solver="python")
    assert rep.acyclicity.witness.value == [["buyer", "seller"], ["broker", "seller"], ["broker", "buyer"]]


def test_one_per_boundary():
    """One schema per class boundary: five fixtures, five different classes, each failing exactly the test that
    separates it from the next stricter class, with the witness kind of that test."""
    kinds = {"berge": None, "gamma": "berge_cycle", "beta": "gamma_triangle", "alpha": "beta_cycle",
             "cyclic": "gyo_residue"}
    first = {"berge": None, "gamma": "berge", "beta": "gamma", "alpha": "beta", "cyclic": "alpha"}
    seen = []
    for name, cls in BOUNDARY:
        src = f"{name}.relation-schema.json"
        rep = check(fixture_path(src), solver="python")
        a = rep.acyclicity
        assert a.cls == cls, name
        assert a.first_failed == first[cls]
        assert (a.witness.kind if a.witness else None) == kinds[cls]
        # hw = 1 exactly when alpha-acyclic (GLS Theorem 4.4)
        assert (rep.widths["hw"].value == 1) == (cls != "cyclic")
        seen.append(a.cls)
    assert seen == ["berge", "gamma", "beta", "alpha", "cyclic"]
    assert (FIXTURES / "p6-duplicate-role-set.relation-schema.json").exists()
