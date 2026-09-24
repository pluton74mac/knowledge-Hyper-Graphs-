"""P1's call sequence (DESIGN §1.3): five backends, one conformance suite, timed reads.

``MyPostgresStore`` stands in for P1's PostgreSQL backend: the reference ``MemoryStore`` under its own store id, so
the sequence runs as P1 runs it against each backend. ``corpus.khg.jsonl`` is the packaged gate fixture.

The companion test runs the same calls on a backend with the flags §6.5 gives TypeDB 3.x: ``load(on_missing="skip")``
skips what the backend cannot hold, the round trip loses exactly those records, and the conformance suite reports
no failure, only inapplicable scenarios (the director's ruling 1 on §14: P1 reports them as fidelity losses).
"""
from __future__ import annotations

from typing import Any

from khg_contracts import CONTRACTS, record, store

#: The flags a TypeDB 3.x backend has natively (DESIGN §6.5: it lacks ordered_roles, special_values, goals,
#: transaction_time and history_export).
TYPEDB_FLAGS = frozenset({"literal_values", "nesting", "valid_time", "key_constraint", "atomic_writes"})


class MyPostgresStore(store.MemoryStore):
    """The backend the P1 sequence names: here the reference store, with every flag, under the id ``my-postgres``."""

    def __init__(self, schema: Any, *, clock: Any = None) -> None:
        super().__init__(schema, clock=clock, store_id="my-postgres")


class TypeDBLikeStore(store.MemoryStore):
    """A backend that declares only the TypeDB 3.x flags of §6.5."""

    def __init__(self, schema: Any, *, clock: Any = None) -> None:
        super().__init__(schema, clock=clock, capabilities=TYPEDB_FLAGS, store_id="typedb-like")


def ids(records: list[dict[str, Any]]) -> list[str]:
    return [r["id"] for r in records]


def test_p1_sequence(S):
    # >>> DESIGN §1.3
    # P1: five backends, one conformance suite, timed reads
    backend = store.Timed(MyPostgresStore(S))                  # MyPostgresStore implements store.Store
    backend.load(record.iter_jsonl("corpus.khg.jsonl"), on_missing="skip")        # LoadReport{records, versions, skipped}
    assert store.compare_containers(record.read_container("corpus.khg.jsonl"), backend.export("khg-json")) == []
    backend.incident("ex:KingOfFrance", where=store.Where(as_of="+1700-01-01T00:00:00Z"))
    backend.find("position_held", [{"role": "holder", "value": {"entity": "ex:LouisXIV"}}])
    backend.find_by_key("position_held", [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}])
    backend.supersession_walk("f:born-skłodowska-kraków")
    report = store.conformance.run(lambda schema, clock: MyPostgresStore(schema, clock=clock))   # EARL-shaped
    # <<< DESIGN §1.3

    inner = backend.store
    assert isinstance(inner, store.Store) and isinstance(inner, store.StoreBase)
    # Timed kept one entry per call: the method, the args digest, the wall time and the size of the result
    assert [(c["method"], c["size"]) for c in backend.calls] == [
        ("load", 40), ("export", 40), ("incident", 1), ("find", 1), ("find_by_key", 2), ("supersession_walk", 1)]
    assert all(c["args"].startswith("sha256:") and c["ns"] >= 0 and "error" not in c for c in backend.calls)
    # the load kept the fixture's header as the store's document header (header state, §6.2)
    info = inner.info()
    assert info["store_id"] == "my-postgres" and info["capabilities"] == store.ALL_FLAGS
    assert info["header"]["document_id"] == "p2-gate-fixture" and "content" not in info["header"]
    assert info["contracts"] == dict(CONTRACTS)
    # what the four reads return (asked again of the unwrapped store, so the timings above stay as they were)
    as_of_1700 = store.Where(as_of="+1700-01-01T00:00:00Z")
    assert ids(inner.incident("ex:KingOfFrance", where=as_of_1700)) == ["f:king-14"]
    assert ids(inner.incident("ex:KingOfFrance")) == ["f:king-13", "f:king-14"]  # no as_of: no valid-time filter
    assert ids(inner.find("position_held", [{"role": "holder", "value": {"entity": "ex:LouisXIV"}}])) == ["f:king-14"]
    assert ids(inner.find_by_key("position_held", [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}])) \
        == ["f:king-13", "f:king-14"]
    assert inner.supersession_walk("f:born-skłodowska-kraków") == {
        "start": "f:born-skłodowska-kraków", "direction": "forward",
        "steps": [{"depth": 1, "via": "m:sup-1", "reason": "correction", "from": "f:born-skłodowska-kraków",
                   "to": "f:born-skłodowska-warszawa"}],
        "terminal": [{"id": "f:born-skłodowska-warszawa", "status": "asserted"}]}
    # the conformance report: EARL-shaped, every one of the 114 scenarios passed on this backend
    assert report["@context"]["@vocab"] == "http://www.w3.org/ns/earl#"
    assert report["subject"]["title"] == "my-postgres"
    assert report["summary"] == {"passed": 114, "failed": 0, "inapplicable": 0, "cantTell": 0, "total": 114}
    assert len(report["@graph"]) == 114
    assert {a["result"]["outcome"] for a in report["@graph"]} == {"passed"}


def test_p1_calls_on_a_backend_without_some_flags(S):
    """The same calls on a TypeDB-like backend: skipped records are fidelity losses, never failures."""
    backend = store.Timed(TypeDBLikeStore(S))
    loaded = backend.load(record.iter_jsonl("corpus.khg.jsonl"), on_missing="skip")
    skipped = ["f:born-scribe", "f:cat-7", "f:route-1", "g:who-1774"]  # somevalue, novalue, positions, a goal
    assert (loaded["records"], loaded["versions"], loaded["skipped"]) == (36, 36, skipped)
    diffs = store.compare_containers(record.read_container("corpus.khg.jsonl"), backend.export("khg-json"))
    assert [(d["id"], d["b"]) for d in diffs] == [(i, None) for i in skipped]
    assert ids(backend.incident("ex:KingOfFrance", where=store.Where(as_of="+1700-01-01T00:00:00Z"))) == ["f:king-14"]
    assert ids(backend.find_by_key("position_held", [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}])) \
        == ["f:king-13", "f:king-14"]
    report = store.conformance.run(lambda schema, clock: TypeDBLikeStore(schema, clock=clock))
    # §6.5: 70 of the 114 scenarios apply to TypeDB 3.x; the backend passes, as no applicable scenario fails
    assert report["summary"] == {"passed": 70, "failed": 0, "inapplicable": 44, "cantTell": 0, "total": 114}
    assert report["subject"]["capabilities"] == sorted(TYPEDB_FLAGS)
    inapplicable = [a for a in report["@graph"] if a["result"]["outcome"] == "inapplicable"]
    assert all(set(a["test"]["requires"]) - TYPEDB_FLAGS for a in inapplicable)
