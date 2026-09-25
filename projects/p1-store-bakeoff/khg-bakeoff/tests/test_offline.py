"""The Neo4j and TypeDB adapters without their servers or drivers (review 01, R-14): they import, and their
pure-Python parts (the TypeQL schema, the labels, the UNWIND rows, the TypeQL ``find``) are right. CI runs these
without the neo4j and typedb clients."""
from __future__ import annotations

import importlib
import json
from types import SimpleNamespace

from khg_contracts.record import identity_key
from khg_contracts.store import Where

from khg_bakeoff.rows import prepare


def test_the_neo4j_and_typedb_adapters_import_without_their_clients():
    for name in ("khg_bakeoff.neo4j", "khg_bakeoff.typedb"):
        module = importlib.import_module(name)
        assert module.factory and module.__all__


def test_typeql_labels_are_injective_and_prefixed():
    from khg_bakeoff.typedb import label

    names = ["a:b", "a-b", "a_b", "ab", "a b", "é", "-65-", "match", "𠮷"]
    labels = [label("rel-", n) for n in names]
    assert len(set(labels)) == len(names) and all(x.startswith("rel-") for x in labels)
    assert label("rel-", "a:b") == "rel-a-3a-b" and label("ent-", "match") == "ent-match"


def test_the_typeql_schema_of_the_fixture_and_the_edge_schema(schema, edge_schema):
    from khg_bakeoff.typedb import TypeQLSchema

    tq = TypeQLSchema(schema)
    assert tq.text.startswith("define") and "relation khg-fact @abstract" in tq.text
    assert tq.unmapped == {} and set(tq.relation) >= {"position_held", "khg:supersedes"}
    assert "khg:end_cause" in tq.players["position_held"] and "khg:end_cause" in tq.literals["position_held"]
    edge = TypeQLSchema(edge_schema)
    assert edge.unmapped == {"measured_constant": "the relation has no entity or fact role (SVL41)"}
    assert "measured_constant" not in edge.relation


def test_neo4j_version_rows(schema, fixture_doc):
    from khg_bakeoff.neo4j import Neo4jStore, _write_query

    king = dict(next(r for r in fixture_doc["records"] if r["id"] == "f:king-14"), version=1,
                recorded_at="2026-10-01T00:00:00Z", recorded_by="load")
    row = Neo4jStore.version_row(SimpleNamespace(schema=schema), king, 5)
    assert row["id"] == "f:king-14" and row["kind"] == "fact" and row["props"]["tx_from"] == 5
    assert sorted(n["ref"] for n in row["nodes"]) == ["ex:KingOfFrance", "ex:LouisXIII", "ex:LouisXIV"]
    assert len(row["literals"]) == 2 and row["specials"] == [] and "tx_to" not in row["props"]
    assert "OPTIONAL MATCH (p:Version:NS" in _write_query("NS", True) and "OPTIONAL" not in _write_query("NS", False)


def _typedb(schema):
    """A ``TypeDBStore`` without a server: the TypeQL of ``find`` is captured instead of run."""
    from khg_bakeoff.typedb import TypeDBStore, TypeQLSchema

    s = TypeDBStore.__new__(TypeDBStore)
    s.tq = TypeQLSchema(schema)
    s.captured = []
    s._ids_where = lambda body, where, as_of, after, limit: s.captured.append(body) or ["x"]
    return s


def test_typedb_find_matches_in_typeql(schema):
    s = _typedb(schema)
    king = {"entity": "ex:KingOfFrance"}

    def run(pattern, match="at_least"):
        return s._n_find("position_held", prepare(pattern), match, Where(), None, None, None, None)

    assert run([{"role": "position", "value": king}]) == ["x"]
    assert 'links (role-position: $p0); $p0 isa khg-entity, has khg-id "ex:KingOfFrance";' in s.captured[-1]
    assert run([{"role": "position", "value": king}] * 2) == []  # one binding per role and identity is held
    end = {"literal": {"datatype": "string", "value": "abdication"}}
    run([{"role": "khg:end_cause", "value": {"any": True}}, {"role": "khg:end_cause", "value": {"any": True}}])
    body = s.captured[-1]  # a mixed role: the two any split between players and literals, three branches
    assert body.count("} or {") == 2 and "not { $x" in body and "!= $y" in body
    run([{"role": "khg:end_cause", "value": end}, {"role": "khg:end_cause", "value": {"any": True}}], "exact")
    assert f"has lit-khg-3a-end_cause {json.dumps(identity_key(end))}" in s.captured[-1]
    assert "has khg-n-bindings 2;" in s.captured[-1]
    assert run([{"role": "nope", "value": king}]) == []
