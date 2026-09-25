"""The trusted bulk load (DESIGN §2; review 01, R-01, R-02, R-03, R-15): Oxigraph's ``bulk_extend``, no read per
record, TypeDB and containers that are not complete, and Neo4j's linear flush."""
from __future__ import annotations

import copy
import math

import pytest

from khg_contracts.errors import ValidationError
from khg_contracts.store import MemoryStore, ScenarioClock, compare_containers

from khg_bakeoff import trips
from khg_bakeoff.backends import factory

from helpers import backend_params

#: Ids per query of each adapter's prefetch and batched reads (``CHUNK``; Neo4j's is ``BATCH``).
CHUNKS = {"sqlite": 500, "postgres": 500, "oxigraph": 500, "neo4j": 500, "typedb": 100}


def fresh(name, schema):
    return factory(name)(schema, ScenarioClock())


# ------------------------------------------------------------------------------------------------ R-01


class _Recording:
    """Stands in for a ``pyoxigraph.Store``: records the calls, and can fail right after ``bulk_extend`` wrote."""

    def __init__(self, real, fail=False):
        self.real, self.fail, self.calls = real, fail, []

    def __getattr__(self, name):
        return getattr(self.real, name)

    def __len__(self):
        return len(self.real)

    def bulk_extend(self, quads):
        self.calls.append("bulk_extend")
        self.real.bulk_extend(quads)
        if self.fail:
            raise RuntimeError("the disk filled up in the middle of bulk_extend")

    def update(self, text):
        self.calls.append("update")
        return self.real.update(text)


@pytest.mark.parametrize("name", backend_params(("oxigraph",)))
def test_r01_oxigraph_loads_an_empty_store_with_bulk_extend(name, schema, fixture_doc):
    s = fresh(name, schema)
    try:
        s.store = spy = _Recording(s.store)
        s.load(copy.deepcopy(fixture_doc))
        assert spy.calls == ["bulk_extend", "update"]  # the quads in bulk, then the store's own triples
        reference = MemoryStore(schema, clock=ScenarioClock(), store_id="oxigraph")
        reference.load(copy.deepcopy(fixture_doc))
        assert compare_containers(reference.export("khg-json"), s.export("khg-json"), ignore=()) == []
        spy.calls.clear()
        s.load(copy.deepcopy(fixture_doc))  # a store that holds data: one transactional update
        assert spy.calls == ["update"]
    finally:
        s.close()


@pytest.mark.parametrize("name", backend_params(("oxigraph",)))
def test_r01_a_failed_bulk_load_leaves_the_store_as_it_was(name, schema, fixture_doc):
    s = fresh(name, schema)
    try:
        real = s.store
        s.store = _Recording(real, fail=True)
        with pytest.raises(RuntimeError):
            s.load(copy.deepcopy(fixture_doc))
        assert len(real) == 0 and list(s.iter_records()) == [] and s.info()["header"] is None
        s.store = real
        header_only = {"header": fixture_doc["header"], "records": []}
        s.load(header_only)  # the store keeps a header and holds no version
        kept, quads = s.info()["header"], len(real)
        s.store = _Recording(real, fail=True)
        with pytest.raises(RuntimeError):
            s.load(copy.deepcopy(fixture_doc))
        assert len(real) == quads and list(s.iter_records()) == [] and s.info()["header"] == kept
        s.store = real
        assert s.load(copy.deepcopy(fixture_doc))["records"] == 40 and len(list(s.iter_records())) == 40
    finally:
        s.close()


# ------------------------------------------------------------------------------------------------ R-02


@pytest.mark.parametrize("name", backend_params(("sqlite", "postgres", "oxigraph", "neo4j", "typedb")))
def test_r02_a_load_reads_no_record_on_its_own(name):
    """Into an empty store a load makes the same few reads whatever it brings; into a store that holds its ids,
    a bounded number per chunk of ids. Its writes are per table or per batch, never per record."""
    measured = trips.scaling(name, sizes=(0, 200))
    empty, held = measured["load, empty store"], measured["load, every id held"]
    assert empty[0]["read"] == empty[1]["read"] <= 3, empty
    chunk = CHUNKS[name]
    for x in held:
        assert x["read"] <= 4 + 3 * math.ceil(x["records"] / chunk), held
    for x in empty + held:
        assert x["write"] <= 9 + 2 * math.ceil(x["records"] / trips_batch(name)), (empty, held)
    assert empty[0]["calls"] < 12 and held[0]["calls"] < 18


def trips_batch(name):
    """New instances per write call (TypeDB ``BATCH``; the others write whole tables or ``UNWIND`` batches)."""
    return {"typedb": 200, "neo4j": 500}.get(name, 10 ** 9)


# ------------------------------------------------------------------------------------------------ R-03


def incomplete(fixture_doc):
    """P2's fixture without ``ex:Paris``: a slice that is not complete."""
    doc = copy.deepcopy(fixture_doc)
    doc["records"] = [r for r in doc["records"] if r["id"] != "ex:Paris"]
    doc["header"]["complete"] = False
    return doc


@pytest.mark.parametrize("name", backend_params(("typedb",)))
def test_r03_typedb_skips_and_counts_a_fact_whose_player_it_does_not_hold(name, schema, fixture_doc):
    """Build ruling Q4 and P2 ruling 18: the fact is skipped and counted, with the facts that nest it; the rest
    loads."""
    doc = incomplete(fixture_doc)
    s = fresh(name, schema)
    try:
        report = s.load(copy.deepcopy(doc), on_missing="skip")
        flags = ["f:born-scribe", "f:cat-7", "f:route-1", "g:who-1774"]  # missing flags, as for the fixture
        assert report["skipped"] == sorted(flags + ["f:born-louis14-paris", "f:claim-1"])
        assert report["records"] == 39 - 6 == len(list(s.iter_records()))
        assert s.refusals["f:born-louis14-paris"]["reason"] == "player_not_held"
        assert s.refusals["f:born-louis14-paris"]["player"] == "ex:Paris"
        reference = MemoryStore(schema, clock=ScenarioClock(), capabilities=s.capabilities)
        reference.load({"header": doc["header"],
                        "records": [r for r in doc["records"] if r["id"] not in report["skipped"]]})
        assert [r["id"] for r in s.iter_records()] == [r["id"] for r in reference.iter_records()]
        assert [r["id"] for r in s.incident("ex:LouisXIV")] == [r["id"] for r in reference.incident("ex:LouisXIV")]
    finally:
        s.close()
    s = fresh(name, schema)
    try:
        by_id = {r["id"]: r for r in fixture_doc["records"]}
        small = {"header": doc["header"], "records": [by_id["ex:LouisXIV"], by_id["f:born-louis14-paris"]]}
        with pytest.raises(ValidationError) as e:
            s.load(copy.deepcopy(small))
        assert e.value.codes == () and e.value.info["cannot_hold"]["reason"] == "player_not_held"
        assert list(s.iter_records()) == [] and s.info()["header"] is None
        assert s.load(copy.deepcopy(small), on_missing="skip")["skipped"] == ["f:born-louis14-paris"]
        assert [r["id"] for r in s.iter_records()] == ["ex:LouisXIV"]
    finally:
        s.close()


@pytest.mark.parametrize("name", backend_params(("sqlite", "oxigraph", "postgres", "neo4j")))
def test_the_other_backends_hold_a_reference_to_a_record_they_do_not_hold(name, schema, fixture_doc):
    s = fresh(name, schema)
    try:
        report = s.load(incomplete(fixture_doc), on_missing="skip")
        assert report["skipped"] == [] and report["records"] == 39
    finally:
        s.close()


def test_the_hif_store_cannot_load_a_container_that_is_not_complete(schema, fixture_doc):
    """A finding of the fixes, open for a ruling (IMPLEMENTATION-NOTES §8): ``to_hif`` writes an incidence on a node
    the file does not declare, ``from_hif`` refuses the file (KHG-D002), and the whole load fails; the store is left
    as it was."""
    s = fresh("hif", schema)
    try:
        with pytest.raises(ValidationError) as e:
            s.load(incomplete(fixture_doc), on_missing="skip")
        assert e.value.code == "KHG-D002" and "ex:Paris" in str(e.value)
        assert list(s.iter_records()) == [] and s.info()["header"] is None and not s.path.exists()
    finally:
        s.close()


# ------------------------------------------------------------------------------------------------ R-15


class _Row(dict):
    """A buffered row that counts how often it is compared for equality."""

    compared = 0

    def __eq__(self, other):
        _Row.compared += 1
        return dict.__eq__(self, other)

    __hash__ = None


def test_r15_neo4j_partitions_its_buffer_in_one_pass():
    from khg_bakeoff.neo4j import partition

    rows = [_Row(id=f"x{i}", close=i % 3 == 0) for i in range(3000)]
    _Row.compared = 0
    closing, fresh_rows = partition(rows)
    assert _Row.compared == 0  # no list-membership test: linear, not O(n * c)
    assert [r["id"] for r in closing] == [f"x{i}" for i in range(0, 3000, 3)]
    assert len(closing) + len(fresh_rows) == 3000 and all("close" not in r for r in rows)
    assert [r["id"] for r in fresh_rows][:2] == ["x1", "x2"]
