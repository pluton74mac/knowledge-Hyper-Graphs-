"""Adapter behaviour the suite does not reach (DESIGN §2–§3): refusals through the existing error model,
all-or-nothing writes, the header state (review 01, R-07), reopening a persistent store, the HIF file, the
PostgreSQL key guard (R-04) and code-point order (R-05)."""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

import pytest

from khg_contracts.errors import CapabilityMissing, KeyCollision, ValidationError
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
        with pytest.raises(ValidationError) as e:  # records are checked in order: ex:Dual comes first
            s.load(copy.deepcopy(edge_doc))
        assert e.value.info["id"] == "ex:Dual" and e.value.codes == ()
        with pytest.raises(CapabilityMissing):
            s.load({"header": edge_doc["header"], "records": [by_id["g:who-what"]]})
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


# ------------------------------------------------------------------------------------------------ header state (R-07)


def test_r07_the_adapters_use_the_public_header_accessors_only():
    """Ruling 17 as amended on review 01: no adapter reads or writes ``TableStore``'s private header state."""
    import khg_bakeoff

    paths = sorted(Path(khg_bakeoff.__file__).parent.glob("*.py"))
    assert len(paths) >= 15
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\._header\b|\._documents\b", text), path.name
        assert "store._table" not in text and "store._writes" not in text, path.name


def _break_the_commit(name, s, monkeypatch):
    """Make the backend fail after ``TableStore.load`` has kept the new header, inside the write's transaction."""
    if name == "oxigraph":
        monkeypatch.setattr(s, "_pending_quads", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))
    elif name == "hif":
        monkeypatch.setattr(s, "_persist", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))
    else:
        monkeypatch.setattr(s._table, "flush", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))


@pytest.mark.parametrize("name", backend_params())
def test_r07_a_failed_load_rolls_the_header_back(name, schema, fixture_doc, monkeypatch):
    s = fresh(name, schema)
    try:
        first = {"header": fixture_doc["header"], "records": [r for r in fixture_doc["records"]
                                                              if r["kind"] == "entity"]}
        s.load(copy.deepcopy(first))
        kept, before = s.info()["header"], s.export("khg-jsonl")
        other = copy.deepcopy(fixture_doc)
        other["header"]["document_id"] = "doc:failed-load"
        other["records"] = [r for r in other["records"] if r["kind"] == "hyperedge"]
        with monkeypatch.context() as m:
            _break_the_commit(name, s, m)
            with pytest.raises(RuntimeError):
                s.load(other, on_missing="skip")
        assert s.info()["header"] == s.kept_header == kept and s.kept_documents == []
        assert s.export("khg-jsonl") == before
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
def test_postgres_key_guard(name, schema, fixture_doc):
    s = fresh(name, schema)
    try:
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


@pytest.mark.parametrize("name", backend_params(("postgres",)))
def test_r04_postgres_accepts_a_batch_that_moves_preferred_between_facts(name, schema, fixture_doc):
    """R-04: the guard rows of a write are deleted, then inserted, at its flush, so the order of the batch does not
    matter; the result equals ``MemoryStore``'s."""
    entities = [r for r in fixture_doc["records"] if r["kind"] == "entity"]
    suite = conformance.suite()
    king = suite.resolve({"@": "f:king-14", "set": {"rank": "preferred"}})
    king_b = dict(copy.deepcopy(king), id="f:king-14b", rank="normal")
    swap = [dict(copy.deepcopy(king_b), rank="preferred"), dict(copy.deepcopy(king), rank="normal")]  # B first
    s, m = fresh(name, schema), MemoryStore(schema, clock=ScenarioClock(), store_id="postgres")
    try:
        for store in (s, m):
            store.put(entities, actor="t")
            store.put([king, king_b], actor="t")
            assert store.put(swap, actor="t")["records"] == [("f:king-14", 2, "versioned"),
                                                              ("f:king-14b", 2, "versioned")]
        assert compare_containers(m.export("khg-json"), s.export("khg-json"), ignore=()) == []
        assert [r[0] for r in s.db.q("SELECT fact_id FROM key_period")] == ["f:king-14b"]
        back = [dict(copy.deepcopy(king), rank="preferred"), dict(copy.deepcopy(king_b), rank="normal")]
        s.put(back, actor="t")  # and back, the other order
        assert [r[0] for r in s.db.q("SELECT fact_id FROM key_period")] == ["f:king-14"]
    finally:
        s.close()


@pytest.mark.parametrize("name", backend_params(("postgres",)))
def test_r04_a_refusal_of_the_key_guard_is_the_c2_error(name, schema, fixture_doc):
    """R-04: when the database's guard refuses a write the write path accepted, the caller gets ``KeyCollision``
    (KHG-D016), never a psycopg error, and nothing is written."""
    s = fresh(name, schema)
    try:
        s.load(copy.deepcopy(fixture_doc))
        digest = s.db.q("SELECT key_digest FROM fact_version WHERE id = 'f:king-14'")[0][0]
        s.db.x("INSERT INTO key_period VALUES ('position_held', ?, '(,)'::int8range, 'f:phantom')", (digest,))
        before = s.export("khg-jsonl")
        with pytest.raises(KeyCollision) as e:
            s.put(conformance.suite().resolve({"@": "f:king-14", "set": {"rank": "preferred"}}), actor="t")
        assert e.value.codes == ("KHG-D016",) and e.value.info["guard"]["facts"] == ["f:king-14"]
        assert s.export("khg-jsonl") == before and s.get("f:king-14")["rank"] == "normal"
    finally:
        s.close()


@pytest.mark.parametrize("name", backend_params(("postgres",)))
def test_r05_every_text_column_orders_by_code_point(name, schema):
    """R-05: ``COLLATE "C"`` on every text column, and a database whose default collation is code-point order
    (the check reads the locale provider)."""
    s = fresh(name, schema)
    try:
        cols = s.db.q("SELECT table_name, column_name, collation_name FROM information_schema.columns "
                      "WHERE table_schema = ? AND data_type = 'text'", (s.db.namespace,))
        assert len(cols) >= 20 and all(c[2] == "C" for c in cols), [c for c in cols if c[2] != "C"]
        provider, collate, locale = s.db.q("SELECT datlocprovider, datcollate, datlocale FROM pg_database "
                                           "WHERE datname = current_database()")[0]
        assert (provider, collate) == ("c", "C") or (provider, locale) == ("b", "C")
    finally:
        s.close()


@pytest.fixture()
def icu_database():
    """A database with the ICU locale provider on the test server (dropped afterwards), or a skip where the
    server was built without ICU."""
    import psycopg

    conninfo = os.environ["KHG_BAKEOFF_POSTGRES"]
    name = f"khg_icu_{os.getpid()}_{os.urandom(3).hex()}"
    admin = psycopg.connect(f"{conninfo} dbname=postgres", autocommit=True)
    try:
        try:
            admin.execute(f"CREATE DATABASE {name} LOCALE_PROVIDER icu ICU_LOCALE 'en-US' LOCALE 'C' "
                          "TEMPLATE template0")
        except psycopg.errors.FeatureNotSupported as e:
            pytest.skip(f"this PostgreSQL server was built without ICU: {e}")
        yield conninfo, name
    finally:
        admin.execute(f"DROP DATABASE IF EXISTS {name}")
        admin.close()


ASTRAL_IDS = ["f:Z", "f:a", "f:é", "f:ł", "f:東京", "f:ｚ", "f:\ufffd", "f:\U00020bb7"]  # code-point order


@pytest.mark.parametrize("name", backend_params(("postgres",)))
def test_r05_an_icu_database_is_refused_and_the_columns_order_by_code_point_in_it(name, schema, icu_database):
    """R-05 against an ICU database: opening a store there is refused, naming the provider; and the adapter's
    tables, created in it, still order ids and page after one by code point, where ICU orders them otherwise."""
    import psycopg

    from khg_bakeoff.postgres import TEXT, PostgresStore
    from khg_bakeoff.sql import ddl

    conninfo, database = icu_database
    with pytest.raises(ValueError, match="icu"):
        PostgresStore(schema, conninfo=conninfo, database=database)
    con = psycopg.connect(f"{conninfo} dbname={database}", autocommit=True)
    try:
        assert con.execute("SELECT datlocprovider FROM pg_database WHERE datname = current_database()"
                           ).fetchone()[0] == "i"
        assert con.execute("SELECT 'f:\u6771\u4eac' < 'f:\uff5a'").fetchone()[0] is False  # ICU's order here
        con.execute("CREATE SCHEMA probe")
        con.execute("SET search_path TO probe")
        for stmt in ddl("NUMERIC", TEXT):
            con.execute(stmt)
        for i in reversed(ASTRAL_IDS):
            con.execute("INSERT INTO fact_version VALUES (%s, 1, 0, NULL, 'x', 'x', 'r', 'fact', 'asserted', NULL, "
                        "'normal', 'visible', NULL, 0, 0, 0, 0, 0, '{}')", [i])
        got = [r[0] for r in con.execute("SELECT id FROM fact_version ORDER BY id")]
        assert got == ASTRAL_IDS == sorted(ASTRAL_IDS)
        page = [r[0] for r in con.execute("SELECT id FROM fact_version WHERE id > %s ORDER BY id LIMIT 3",
                                          ["f:ł"])]
        assert page == ["f:東京", "f:ｚ", "f:\ufffd"]
    finally:
        con.close()
