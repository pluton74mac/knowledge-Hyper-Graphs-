"""Adapter behaviour the suite does not reach (DESIGN §2–§3): refusals through the existing error model,
all-or-nothing writes, reopening a persistent store, the HIF file, the PostgreSQL key guard and collation."""
from __future__ import annotations

import copy
import json

import pytest

from khg_contracts.errors import CapabilityMissing, ValidationError
from khg_contracts.store import MemoryStore, ScenarioClock, compare_containers, conformance, parse_timestamp
from khg_contracts.validate import validate_hif

from khg_bakeoff.backends import BACKENDS, factory

from helpers import backend_params

FAR = "f:far-future"


def fresh(name, schema):
    return factory(name)(schema, ScenarioClock())


def far_future(edge_doc):
    by_id = {r["id"]: r for r in edge_doc["records"]}
    return [by_id["ex:Futurist"], by_id["ex:FarFuturePost"], by_id[FAR]]


# ------------------------------------------------------------------------------------------------ refusals


@pytest.mark.parametrize("name", backend_params())
def test_what_a_backend_cannot_hold_is_refused_without_a_code(name, edge_schema, edge_doc):
    """Ruling 4: an int64 backend refuses the 16-digit year (ValidationError without a code, info["cannot_hold"]),
    and nothing is written; PostgreSQL (numeric) and HIF hold it."""
    s = fresh(name, edge_schema)
    try:
        people, post, far = far_future(edge_doc)
        s.put([people, post], actor="t")
        before = s.export("khg-jsonl")
        if name in ("postgres", "hif"):
            assert s.put(far, actor="t")["records"] == [(FAR, 1, "created")]
            for as_of, mode, want in (("+10000000000000001-01-01T00:00:00Z", "definite", [FAR]),
                                      ("+9999999999999999-06-01T00:00:00Z", "definite", []),
                                      ("+9999999999999999-06-01T00:00:00Z", "possible", [FAR]),
                                      ("+2026-01-01T00:00:00Z", "possible", [])):
                got = s.incident("ex:FarFuturePost", where={"as_of": as_of, "valid_mode": mode})
                assert [r["id"] for r in got] == want, (as_of, mode)
            return
        with pytest.raises(ValidationError) as e:
            s.put(far, actor="t")
        assert e.value.codes == () and e.value.info["id"] == FAR
        assert e.value.info["cannot_hold"]["reason"] == "instant_range"
        assert s.export("khg-jsonl") == before and s.get(FAR) is None
    finally:
        s.close()


@pytest.mark.parametrize("name", backend_params())
def test_load_skips_or_raises_on_what_it_cannot_hold(name, edge_schema, edge_doc):
    s = fresh(name, edge_schema)
    try:
        if name in ("postgres", "hif", "typedb"):
            pytest.skip("holds the 16-digit year, or lacks flags the edge container needs")
        with pytest.raises(ValidationError):
            s.load(copy.deepcopy(edge_doc))
        assert list(s.iter_records()) == [] and s.info()["header"] is None
        report = s.load(copy.deepcopy(edge_doc), on_missing="skip")
        assert report["skipped"] == [FAR] and report["records"] == 40
    finally:
        s.close()


@pytest.mark.parametrize("name", backend_params(("typedb",)))
def test_typedb_refuses_what_its_natural_mapping_cannot_hold(name, edge_schema, edge_doc):
    s = fresh(name, edge_schema)
    try:
        report = s.load(copy.deepcopy(edge_doc), on_missing="skip")
        assert report["skipped"] == ["ex:Dual", "f:aliases-twice", "f:constant-c", "f:dual-profile", FAR,
                                     "g:who-what"]
        by_id = {r["id"]: r for r in edge_doc["records"]}
        assert s.cannot_hold(by_id["ex:Dual"])["reason"] == "instance_type"
        assert s.cannot_hold(by_id["f:constant-c"])["reason"] == "no_role_player"
        with pytest.raises(CapabilityMissing):
            s.load(copy.deepcopy(edge_doc))
    finally:
        s.close()


# ------------------------------------------------------------------------------------------------ atomic writes


@pytest.mark.parametrize("name", backend_params())
def test_a_failed_batch_writes_nothing(name, schema, fixture_doc):
    s = fresh(name, schema)
    try:
        s.load(copy.deepcopy(fixture_doc), on_missing="skip")
        before = s.export("khg-jsonl")
        suite = conformance.suite()
        ok = suite.resolve({"@": "f:reg-1", "set": {"rank": "preferred"}})
        bad = suite.resolve({"@": "f:loop-yyz", "set": {"relation": "nope"}})
        with pytest.raises(ValidationError):
            s.put([ok, bad], actor="t")
        assert s.export("khg-jsonl") == before
        assert s.put(ok, actor="t")["records"] == [("f:reg-1", 2, "versioned")]
        assert s.get("f:reg-1")["rank"] == "preferred"
    finally:
        s.close()


# ------------------------------------------------------------------------------------------------ reopening


@pytest.mark.parametrize("name", backend_params(("sqlite", "oxigraph", "hif")))
def test_an_embedded_store_reopens_from_its_file(name, schema, fixture_doc, tmp_path):
    module = __import__(BACKENDS[name].module, fromlist=["x"])
    cls = {"sqlite": "SQLiteStore", "oxigraph": "OxigraphStore", "hif": "HifStore"}[name]
    path = tmp_path / {"sqlite": "store.sqlite", "oxigraph": "store.oxigraph", "hif": "store.hif.json"}[name]
    a = getattr(module, cls)(schema, path=path, clock=ScenarioClock())
    a.load(copy.deepcopy(fixture_doc))
    a.put(conformance.suite().resolve({"@": "f:reg-1", "set": {"rank": "preferred"}}), actor="t")
    exported = a.export("khg-json")
    a.close()
    b = getattr(module, cls)(schema, path=path, clock=ScenarioClock())
    try:
        assert b.info()["header"] == a.info()["header"] is not None
        assert compare_containers(exported, b.export("khg-json"), ignore=()) == []
        assert b.get("f:reg-1")["version"] == 2
        at = b.put(conformance.suite().resolve({"@": "f:loop-yyz", "set": {"rank": "preferred"}}), actor="t")["at"]
        assert parse_timestamp(at) > parse_timestamp("2026-10-01T00:00:01Z")  # after the store's latest (D018)
    finally:
        b.close()


def test_the_hif_file_is_valid_hif_and_rewritten_only_by_a_write(schema, fixture_doc, tmp_path):
    from khg_bakeoff.hif import MARKER, HifStore

    path = tmp_path / "s.hif.json"
    s = HifStore(schema, path=path, clock=ScenarioClock())
    s.load(copy.deepcopy(fixture_doc))
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert validate_hif(doc, schema=schema)["ok"] and MARKER in doc["metadata"]
    assert s.persist_count == 1
    same = conformance.suite().resolve("@f:reg-1")
    assert s.put(same, actor="t")["records"] == [("f:reg-1", 1, "noop")]
    assert s.persist_count == 1  # a no-op writes nothing
    with pytest.raises(CapabilityMissing):
        s.get("f:reg-1", as_at="2026-10-01T00:00:00Z")
    assert s.info()["header"] == {k: v for k, v in fixture_doc["header"].items() if k != "content"}
    # the HIF profile keeps no recorded_by on entity nodes (P2 DESIGN §4.2): a finding of the bake-off
    assert "recorded_by" not in s.get("ex:Paris") and s.get("f:reg-1")["recorded_by"] == "load"


def test_a_hif_store_without_a_kept_header_computes_it(schema, fixture_doc):
    from khg_bakeoff.hif import HifStore

    entities = [r for r in fixture_doc["records"] if r["kind"] == "entity"]
    s, m = HifStore(schema, clock=ScenarioClock()), MemoryStore(schema, clock=ScenarioClock(), store_id="hif")
    try:
        for store in (s, m):
            store.put(entities, actor="t")
            store.put(conformance.suite().resolve("@f:reg-1"), actor="t")
        assert s.info()["header"] is None
        assert s.export("khg-json")["header"] == m.export("khg-json")["header"]
    finally:
        s.close()


# ------------------------------------------------------------------------------------------------ PostgreSQL


@pytest.mark.parametrize("name", backend_params(("postgres",)))
def test_postgres_collation_and_key_guard(name, schema, fixture_doc):
    s = fresh(name, schema)
    try:
        assert s.db.q("SELECT datcollate FROM pg_database WHERE datname = current_database()")[0][0] == "C"
        s.load(copy.deepcopy(fixture_doc))
        assert s.key_guard == "on" and s.db.q("SELECT count(*) FROM key_period")[0][0] == 0
        king = conformance.suite().resolve({"@": "f:king-14", "set": {"rank": "preferred"}})
        s.put(king, actor="t")
        rows = s.db.q("SELECT relation, fact_id, valid::text FROM key_period")
        assert [(r[0], r[1]) for r in rows] == [("position_held", "f:king-14")]
        with pytest.raises(Exception) as e:  # the database refuses a second preferred window on the key
            s.db.x("INSERT INTO key_period VALUES ('position_held', "
                   "(SELECT key_digest FROM key_period LIMIT 1), '[0,)'::int8range, 'x')")
        assert "exclusion" in type(e.value).__name__.lower() or "exclusion" in str(e.value)
        s.db.rollback()
    finally:
        s.close()


@pytest.mark.parametrize("name", backend_params(("postgres",)))
def test_postgres_suspends_the_guard_when_a_trusted_load_breaks_it(name, schema, fixture_doc):
    """Ruling 12 keeps what a trusted load brings; the guard steps aside instead of refusing the load."""
    doc = copy.deepcopy(fixture_doc)
    for r in doc["records"]:
        if r["id"] in ("f:king-13", "f:king-14"):
            r["rank"] = "preferred"
            r["bindings"] = [b if b["role"] != "end_time" else
                             dict(b, value={"literal": {"datatype": "time", "time": "+1700-01-01T00:00:00Z",
                                                        "precision": 11, "calendar": "gregorian"}})
                             for b in r["bindings"]]
    s = fresh(name, schema)
    try:
        s.load(doc)
        assert s.key_guard == "suspended" and len(list(s.iter_records())) == 40
    finally:
        s.close()
