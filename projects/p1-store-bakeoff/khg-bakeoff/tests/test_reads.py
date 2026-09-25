"""The native reads (DESIGN §2, §6.1; the director's ruling on review 01, R-06): filters, limits and counts in the
engine; the records of one call in a bounded number of queries; one row-to-record function; HIF labelled as a file
read in memory; and every read equal to ``MemoryStore``'s, on seeded random queries."""
from __future__ import annotations

import copy
import importlib
import math
import random

import pytest

from khg_contracts.store import MemoryStore, ScenarioClock, Where

from khg_bakeoff import rows, trips
from khg_bakeoff.backends import BACKENDS, factory
from khg_bakeoff.fidelity import _answer

from helpers import backend_params

SERVERS_AND_ENGINES = ("sqlite", "postgres", "oxigraph", "neo4j", "typedb")
CHUNKS = {"sqlite": 500, "postgres": 500, "oxigraph": 500, "neo4j": 500, "typedb": 100}


@pytest.mark.parametrize("name", backend_params(SERVERS_AND_ENGINES))
def test_r06_the_records_of_one_call_come_in_a_bounded_number_of_queries(name):
    """The calls of a read do not grow with its answers or the store, but by one or two per chunk of ids."""
    measured = trips.scaling(name, sizes=(0, 200))
    chunk = CHUNKS[name]
    for op in ("export", "degree ex:Paris", "get_many, every id", "incident ex:Paris"):
        small, large = measured[op]
        assert large["calls"] <= small["calls"] + 2 * math.ceil(large["records"] / chunk) + 2, (op, measured[op])
        assert large["calls"] <= 12, (op, measured[op])
    assert measured["degree ex:Paris"][0]["calls"] == measured["degree ex:Paris"][1]["calls"]
    if name != "typedb":  # a scan is one query per table, whatever the store holds
        assert measured["export"][0]["calls"] == measured["export"][1]["calls"]


@pytest.mark.parametrize("name", backend_params(SERVERS_AND_ENGINES))
def test_r06_degree_is_counted_by_the_engine(name, schema, fixture_doc, monkeypatch):
    s = factory(name)(schema, ScenarioClock())
    try:
        s.load(copy.deepcopy(fixture_doc), on_missing="skip")
        want = len(s.incident("ex:KingOfFrance", where=Where(status=frozenset({"asserted", "superseded"}))))
        monkeypatch.setattr(s, "_n_records", lambda *a: pytest.fail("degree fetched the records"))
        assert s.degree("ex:KingOfFrance", where=Where(status=frozenset({"asserted", "superseded"}))) == want == 2
    finally:
        s.close()


@pytest.mark.parametrize("name", backend_params(SERVERS_AND_ENGINES))
def test_r06_every_backend_rebuilds_its_records_with_one_function(name, schema, fixture_doc, monkeypatch):
    """``rows.record_of`` rebuilds every record a native read returns: one per record, on every backend."""
    module = importlib.import_module(BACKENDS[name].module)
    impl = importlib.import_module("khg_bakeoff.sql") if name in ("sqlite", "postgres") else module
    assert impl.record_of is rows.record_of
    s = factory(name)(schema, ScenarioClock())
    try:
        s.load(copy.deepcopy(fixture_doc), on_missing="skip")
        calls = []
        monkeypatch.setattr(impl, "record_of", lambda *a: calls.append(1) or rows.record_of(*a))
        got = s.incident("ex:KingOfFrance")
        assert len(calls) == len(got) == 2
    finally:
        s.close()


def test_r06_the_hif_store_is_labelled_a_file_read_in_memory():
    from khg_bakeoff.hif import HifStore

    assert HifStore.KIND == "file, read in memory" and not hasattr(HifStore, "_n_records")


# ------------------------------------------------------------------------------------------------ parity


def _queries(fixture_doc, seed: int, n: int) -> list[tuple[str, str, dict]]:
    """Seeded random reads over the fixture: get_many, degree, incident, find (with ``any`` and ``exact``),
    find_by_key and supersession walks."""
    rng = random.Random(seed)
    ids = sorted(r["id"] for r in fixture_doc["records"]) + ["ex:nothing", "f:nothing"]
    facts = [r for r in fixture_doc["records"] if r["kind"] == "hyperedge"]
    statuses = ["asserted", "superseded", "disputed", "retracted", "quoted"]

    def where():
        w: dict = {}
        if rng.random() < 0.4:
            w["status"] = frozenset(rng.sample(statuses, rng.randint(1, 3)))
        if rng.random() < 0.3:
            w["as_of"] = rng.choice(["+1700-01-01T00:00:00Z", "+1650-06-01T00:00:00Z", "+2019-06-01T00:00:00Z"])
            w["valid_mode"] = rng.choice(["definite", "possible"])
        if rng.random() < 0.15:
            w["rank"] = frozenset(rng.sample(["preferred", "normal", "deprecated"], rng.randint(1, 3)))
        if rng.random() < 0.15:
            w["kinds"] = frozenset(rng.sample(["fact", "lifecycle"], rng.randint(1, 2)))
        return Where(**w)

    out: list[tuple[str, str, dict]] = []
    for i in range(n):
        k = rng.random()
        if k < 0.1:
            out.append((f"q{i}", "get_many", {"ids": rng.sample(ids, rng.randint(0, 8))}))
        elif k < 0.3:
            op = rng.choice(["incident", "degree"])
            args = {"node": rng.choice(ids), "where": where()}
            if rng.random() < 0.3:
                args["role"] = rng.choice(sorted({b["role"] for f in facts for b in f["bindings"]}))
            if op == "incident" and rng.random() < 0.4:
                args["limit"] = rng.randint(0, 3)
            if op == "incident" and rng.random() < 0.3:
                args["after"] = rng.choice(ids)
            out.append((f"q{i}", op, args))
        elif k < 0.8:
            f = rng.choice(facts)
            chosen = rng.sample(f["bindings"], rng.randint(0, min(3, len(f["bindings"]))))
            pattern = []
            for b in chosen:
                x = rng.random()
                value = {"any": True} if x < 0.3 else b["value"]
                pattern.append({"role": b["role"], "value": value})
            if rng.random() < 0.15 and chosen:
                pattern.append(copy.deepcopy(pattern[0]))  # a repeated entry: injectivity
            args = {"relation": f["relation"], "pattern": pattern, "where": where()}
            if rng.random() < 0.2:
                args["match"] = "exact"
                if rng.random() < 0.5:
                    args["pattern"] = [{"role": b["role"], "value": b["value"]} for b in f["bindings"]
                                       if "position" not in b]
            if rng.random() < 0.3:
                args["limit"] = rng.randint(0, 2)
            if rng.random() < 0.2:
                args["after"] = rng.choice(ids)
            out.append((f"q{i}", "find", args))
        elif k < 0.9:
            out.append((f"q{i}", "supersession_walk", {"id": rng.choice(ids),
                                                       "direction": rng.choice(["forward", "backward"])}))
        else:
            out.append((f"q{i}", "find_by_key", {"relation": "position_held", "where": where(),
                                                 "key": [{"role": "position", "value": {"entity": rng.choice(
                                                     ["ex:KingOfFrance", "ex:Paris"])}}]}))
    return out


def _call(store, op, args):
    if op == "get_many":
        try:
            return "answer", sorted(store.get_many(args["ids"]))
        except Exception as e:  # noqa: BLE001
            return "refused", type(e).__name__
    return _answer(store, op, args)


@pytest.mark.slow
@pytest.mark.parametrize("name", backend_params())
def test_every_read_equals_the_reference_on_random_queries(name, schema, fixture_doc):
    """The native reads (get_many, degree, incident, find with ``any``, repeated and ``exact`` patterns, keys,
    walks) against ``MemoryStore`` with the backend's flags, holding what the backend holds."""
    s = factory(name)(schema, ScenarioClock())
    try:
        report = s.load(copy.deepcopy(fixture_doc), on_missing="skip")
        reference = MemoryStore(schema, clock=ScenarioClock(), capabilities=s.capabilities)
        reference.load({"header": fixture_doc["header"],
                        "records": [r for r in fixture_doc["records"] if r["id"] not in report["skipped"]]})
        bad = {}
        queries = _queries(fixture_doc, seed=17, n=260 if name == "typedb" else 400)
        for label, op, args in queries:
            a, b = _call(s, op, copy.deepcopy(args)), _call(reference, op, copy.deepcopy(args))
            if a != b:
                bad[label] = (op, args, a, b)
        assert not bad, list(bad.values())[:3]
        assert sum(1 for _, op, _ in queries if op == "find") > 100
    finally:
        s.close()
