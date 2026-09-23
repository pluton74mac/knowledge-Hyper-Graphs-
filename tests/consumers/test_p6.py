"""P6's call sequence (DESIGN §1.3): the schema as a hypergraph.

The sequence runs on the prologue's schema, ``p2-gate`` (α-acyclic), and on the two other schemas that ship for P6's
gate (§3, critique CONS-26): a constructed triangle and a Wikidata-shaped schema, both α-cyclic.
"""
from __future__ import annotations

from typing import Any

import pytest

from khg_contracts import data
from khg_contracts import schema as sch


def p6(S: sch.Schema) -> tuple[dict[str, Any], bool, list[list[str]]]:
    """The P6 sequence on the schema ``S``."""
    # >>> DESIGN §1.3
    # P6: the schema as a hypergraph
    hg = sch.schema_hypergraph(S, slots=("core", "qualifier"))
    acyclic, residue = sch.is_alpha_acyclic(hg)
    # <<< DESIGN §1.3
    return hg, acyclic, residue


def test_p6_sequence(S):
    hg, acyclic, residue = p6(S)
    # 30 roles and 11 relations; a role is one vertex whatever its slot; lifecycle relations never appear
    assert len(hg["vertices"]) == 30 and hg["vertices"] == sorted(hg["vertices"])
    assert sorted(hg["hyperedges"]) == sorted(S.relation_ids()) and len(hg["hyperedges"]) == 11
    assert not any(rel.startswith("khg:") for rel in hg["hyperedges"])
    assert hg["hyperedges"]["regulates"] == ["context", "regulator", "target"]
    assert hg["hyperedges"]["married"] == ["spouse"]
    # time usages appear only when asked for
    assert hg["hyperedges"]["position_held"] == ["holder", "position", "replaces"]
    assert "start_time" not in hg["vertices"]
    assert (acyclic, residue) == (True, [])


@pytest.mark.parametrize("name, ref, residue", [
    ("cyclic.relation-schema.json", "p2-cyclic/1.0.0",
     [["buyer", "seller"], ["broker", "seller"], ["broker", "buyer"]]),
    ("wikidata-shaped.relation-schema.json", "wd-shaped/1.0.0",
     [["replaces", "series_ordinal"], ["point_in_time", "series_ordinal"], ["point_in_time", "replaces"]]),
])
def test_p6_sequence_on_the_cyclic_schemas(name, ref, residue):
    S = sch.load_schema(data.load_json(f"fixture/{name}"))
    assert S.ref == ref
    hg, acyclic, found = p6(S)
    assert acyclic is False and found == residue
    assert all(set(edge) <= set(hg["vertices"]) for edge in found)
