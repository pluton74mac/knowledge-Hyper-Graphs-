"""W8: ``Timed(store)``, the timing proxy of P1 (DESIGN §6.3): one entry per call with the method, the
``khg-timed/1`` args digest, the nanoseconds and the result size."""
from __future__ import annotations

import pytest

from khg_contracts import jsonio
from khg_contracts.errors import KeyCollision, VersionError
from khg_contracts.store import ALL_FLAGS, METHODS, Store, Timed, Where
from khg_contracts.store.timed import args_digest, result_size

KING = [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}]


def test_every_protocol_method_is_timed(loaded, fixture_doc):
    t = Timed(loaded)
    assert isinstance(t, Store)
    calls = [
        ("info", lambda: t.info(), 3 + 3),
        ("get", lambda: t.get("f:reg-1"), 1),
        ("history", lambda: t.history("f:reg-1"), 1),
        ("incident", lambda: t.incident("ex:KingOfFrance"), 2),
        ("find", lambda: t.find("position_held", KING), 2),
        ("iter_records", lambda: list(t.iter_records()), 40),
        ("get_many", lambda: t.get_many(["f:reg-1", "ex:TP53", "f:nope"]), 2),
        ("degree", lambda: t.degree("ex:YYZ"), 2),
        ("find_by_key", lambda: t.find_by_key("position_held", KING), 2),
        ("supersession_walk", lambda: t.supersession_walk("f:born-skłodowska-kraków"), 1),
        ("export", lambda: t.export("khg-json"), 40),
        ("export", lambda: t.export("khg-jsonl"), 40),
        ("export", lambda: t.export("hif"), 18),
        ("apply", lambda: t.apply({"op": "add_evidence", "target": "f:reg-1", "evidence": [
            {"id": "e9", "type": "curated", "mode": "manual", "source": {"doc_id": "d"}}]}, actor="p1"), 1),
        ("put", lambda: t.put({"kind": "entity", "id": "ex:New", "types": ["Person"]}, actor="p1"), 1),
        ("close", lambda: t.close(), 0),
    ]
    results = [run() for _, run, _ in calls]
    assert [c["method"] for c in t.calls] == [name for name, _, _ in calls]
    assert [c["size"] for c in t.calls] == [size for _, _, size in calls]
    assert all(isinstance(c["ns"], int) and c["ns"] >= 0 and c["args"].startswith("sha256:") for c in t.calls)
    assert results[4] == loaded.find("position_held", KING)
    assert {c["method"] for c in t.calls} | {"load"} == set(METHODS)


def test_the_args_digest_is_over_named_arguments_with_defaults(loaded):
    t = Timed(loaded)
    t.incident("ex:KingOfFrance")
    t.incident(node="ex:KingOfFrance", where=Where())
    t.incident("ex:KingOfFrance", where=Where(status=frozenset({"asserted"}), rank=["normal", "preferred"]))
    t.incident("ex:KingOfFrance", role="holder")
    digests = [c["args"] for c in t.calls]
    assert digests[0] == digests[1] == digests[2] != digests[3]
    expected = jsonio.digest("khg-timed/1", {
        "node": "ex:KingOfFrance", "role": None, "relation": None, "limit": None, "after": None,
        "where": {"status": ["asserted"], "rank": ["normal", "preferred"], "visibility": ["visible"],
                  "kinds": ["fact"], "as_of": None, "valid_mode": "definite", "as_at": None}})
    assert digests[0] == expected == args_digest("incident", "ex:KingOfFrance")
    assert args_digest("get", "f:reg-1", colour="blue") == jsonio.digest(
        "khg-timed/1", {"args": ["f:reg-1"], "kwargs": {"colour": "blue"}})


def test_a_streamed_load_is_not_consumed_by_the_digest(ms, fixture_doc):
    t = Timed(ms)
    report = t.load(iter([fixture_doc["header"]] + fixture_doc["records"]))
    assert report["versions"] == 40 and t.calls[0]["size"] == 40
    assert t.calls[0]["args"] == args_digest("load", iter([]))


def test_errors_are_recorded_and_raised(loaded, rec):
    t = Timed(loaded)
    with pytest.raises(VersionError):  # a new record written before the store's latest
        t.put({"kind": "entity", "id": "ex:Late", "types": ["Person"]}, actor="p1", at="2000-01-01T00:00:00Z")
    with pytest.raises(KeyCollision):
        t.put(rec("f:born-skłodowska-kraków", set={"id": "f:b2", "status": "asserted"}, drop=["status_ref"]),
              actor="p1")
    with pytest.raises(ZeroDivisionError):
        t._call("get", lambda: 1 / 0, (), {})
    assert [(c["method"], c["error"], c["size"]) for c in t.calls] == \
        [("put", "KHG-D018", 0), ("put", "KHG-D016", 0), ("get", "ZeroDivisionError", 0)]
    t.clear()
    assert t.calls == []


def test_attributes_pass_through_untimed(loaded):
    t = Timed(loaded)
    assert t.capabilities == ALL_FLAGS and t.schema is loaded.schema and t.store is loaded
    assert t.calls == [] and repr(t).startswith("Timed(MemoryStore(")


def test_result_sizes():
    assert result_size("get", None) == 0 and result_size("degree", 7) == 7 and result_size("get", {"id": 1}) == 1
    assert result_size("export", "{}\n{}\n{}\n") == 2
    assert result_size("load", {"records": 3, "versions": 5, "skipped": [], "seconds": 0.1}) == 5
    assert result_size("supersession_walk", {"steps": [1, 2], "terminal": []}) == 2
    assert result_size("close", object()) == 1
