"""W9: ``replay(path, *, schema, factory, base=None) -> dict`` (DESIGN §7).

A fresh store from ``factory(schema, clock)`` loads ``base``, which must match the header's (Q012); then every
``accept`` runs again in log order at its ``at``, and ``after`` and ``decision_hash`` are checked (Q006). The result
is ``{ok, findings, decisions, store}``.
"""
from __future__ import annotations

import copy
import importlib

import pytest

from khg_contracts import data, record
from khg_contracts.errors import ValidationError
from khg_contracts.queue import Queue, replay
from khg_contracts.queue.lines import dump_line
from khg_contracts.schema import load_schema
from khg_contracts.store import MemoryStore, ScenarioClock, compare_containers, memory_factory

SMOKE = "fixture/smoke-queue.khg-queue.jsonl"


def _codes(result):
    return [(f["code"], f["path"]) for f in result["findings"]]


def _write(tmp_path, lines, name="x.khg-queue.jsonl"):
    p = tmp_path / name
    p.write_text("".join(dump_line(x) for x in lines), encoding="utf-8")
    return p


def test_replay_of_the_smoke_queue_reproduces_the_decision_hash(schema, base, king14, smoke):
    result = replay(data.path(SMOKE), schema=schema, factory=memory_factory, base=base)
    assert result["ok"] is True and result["findings"] == []
    assert result["decisions"] == [{"lid": "l:p2-smoke.000002", "target": "q:p2-smoke.000001",
                                    "after": [{"id": "f:king-14", "version": 1}],
                                    "decision_hash": smoke.DECISION_HASH}]
    stored = result["store"].get("f:king-14")
    assert record.decision_view(stored) == record.decision_view(king14)
    assert stored["recorded_at"] == smoke.TIMES["accept"] and stored["recorded_by"] == "curator:smoke"
    assert result["store"].get("ex:LouisXIV")["recorded_at"] == smoke.TIMES["created"]  # the base, loaded first


@pytest.mark.parametrize("form", ["str", "path", "packaged", "lines", "bytes", "queue"])
def test_the_queue_and_the_base_can_be_given_in_every_form(form, schema, base, smoke):
    lines = data.load_jsonl(SMOKE)
    source = {"str": str(data.path(SMOKE)), "path": data.path(SMOKE), "packaged": data.path(SMOKE), "lines": lines,
              "bytes": data.read_bytes(SMOKE), "queue": None}[form]
    if source is None:
        source = Queue.open(data.path(SMOKE), schema=schema)
    for b in (base, data.path("fixture/smoke-base.c1.json"), str(data.path("fixture/smoke-base.c1.json"))):
        result = replay(source, schema=data.path("fixture/fixture.relation-schema.json"), factory=memory_factory,
                        base=b)
        assert result["ok"] and result["decisions"][0]["decision_hash"] == smoke.DECISION_HASH
    assert lines == data.load_jsonl(SMOKE)  # the lines given are not changed


def test_the_base_must_be_the_header_s(schema, base, smoke):
    for b in (None, dict(base, records=base["records"][:-1])):
        result = replay(data.path(SMOKE), schema=schema, factory=memory_factory, base=b)
        assert result["ok"] is False and _codes(result) == [("KHG-Q012", "/lines/0/base")]
        assert result["store"] is None and result["decisions"] == []
    q = smoke.create(base=None)
    result = replay(q, schema=schema, factory=memory_factory, base=base)
    assert _codes(result) == [("KHG-Q012", "/lines/0")]
    with pytest.raises(ValidationError) as exc:  # a bad base argument is not a finding on the queue
        replay(data.path(SMOKE), schema=schema, factory=memory_factory, base=dict(base, header={"format": "x"}))
    assert exc.value.codes == ("KHG-V001",)


def test_another_schema_is_d009_and_nothing_is_replayed(base):
    other = data.load_json("fixture/fixture.relation-schema.json")
    other["label"] = "another schema"
    result = replay(data.path(SMOKE), schema=load_schema(other), factory=memory_factory, base=base)
    assert _codes(result) == [("KHG-D009", "/lines/0/schema")] and result["store"] is None


def test_a_structural_error_stops_before_the_replay(schema, base):
    lines = data.load_jsonl(SMOKE)
    lines[3]["state_before"] = "pending"
    result = replay(lines, schema=schema, factory=memory_factory, base=base)
    assert _codes(result) == [("KHG-Q005", "/lines/3")] and result["store"] is None
    with pytest.raises(ValidationError) as exc:
        replay(b'{"kind": "queue-header"\n', schema=schema, factory=memory_factory, base=base)
    assert exc.value.codes == ("KHG-J001",)


@pytest.mark.parametrize(("field", "value", "codes"), [
    ("decision_hash", "sha256:" + "1" * 64, [("KHG-Q006", "/lines/3/decision_hash")]),  # MC168
    ("after", [{"id": "f:king-14", "version": 2}], [("KHG-Q006", "/lines/3/after")]),
    ("after", [{"id": "f:king-14", "version": 1}, {"id": "f:king-15", "version": 1}], [("KHG-Q006", "/lines/3")]),
    ("after", [], [("KHG-Q006", "/lines/3")]),
    ("at", "2025-01-01T00:00:00Z", []),  # a time is not content: the base is loaded before it
])
def test_a_replay_mismatch_is_q006(field, value, codes, schema, base, smoke):
    lines = data.load_jsonl(SMOKE)
    lines[3][field] = value
    result = replay(lines, schema=schema, factory=memory_factory, base=base)
    assert _codes(result) == codes and result["ok"] is (codes == [])
    assert result["store"] is not None


def test_a_payload_that_differs_from_the_logged_decision_is_q006(schema, base):
    lines = data.load_jsonl(SMOKE)
    lines[1]["payload"]["rank"] = "preferred"  # not in the keys, but in the record the accept wrote
    result = replay(lines, schema=schema, factory=memory_factory, base=base)
    assert _codes(result) == [("KHG-Q006", "/lines/3/decision_hash")]
    assert result["store"].get("f:king-14")["rank"] == "preferred"


def test_an_accept_the_store_refuses_is_q006(tmp_path, schema, smoke, store):
    q, qid, _, _ = smoke.full(store)
    lines = [dict(line) for line in data.load_jsonl(SMOKE)]
    del lines[0]["base"]  # the same log without its base: the entities are missing
    result = replay(_write(tmp_path, lines), schema=schema, factory=memory_factory)
    assert [c for c, _ in _codes(result)] == ["KHG-Q006"] and "KHG-D002" in result["findings"][0]["message"]
    assert result["decisions"] == [] and result["store"].get("f:king-14") is None


def test_a_longer_log_replays_to_the_same_store(smoke, store, schema, base):
    q = smoke.create()
    henri = {"kind": "entity", "id": "ex:Henri", "types": ["Person"], "label": "Henri"}
    navarre = {"kind": "entity", "id": "ex:KingOfNavarre", "types": ["Position"], "label": "King of Navarre"}
    rec = copy.deepcopy(smoke.king14)
    rec["bindings"][2]["value"] = {"entity": "ex:KingOfNavarre"}  # another key than f:king-14's
    rec["bindings"][3]["value"] = {"entity": "ex:Henri"}
    rec["evidence"] = rec["evidence"][:1]
    a = smoke.submit(q)
    b = smoke.submit(q, smoke.candidate(q, 2, rec), entities=[henri, navarre], at="2026-10-01T00:00:04Z")
    c = smoke.submit(q, smoke.candidate(q, 3), at="2026-10-01T00:00:04.5Z")
    for qid in (a, b, c):
        smoke.lint(q, qid)
    q.reject(c, actor="curator:smoke", reason="a duplicate of the first item", at="2026-10-01T00:00:06Z")
    first = smoke.accept(q, a, store)
    second = smoke.accept(q, b, store, id="f:king-14b", at="2026-10-01T00:00:09.000001Z")
    q.verdict(a, actor="curator:smoke", verdict={"evidence_id": "e2", "label": "correct"})
    result = replay(q, schema=schema, factory=memory_factory, base=base)
    assert result["ok"] and [d["decision_hash"] for d in result["decisions"]] == [first["decision_hash"],
                                                                                 second["decision_hash"]]
    assert result["decisions"][1]["after"] == [{"id": "ex:Henri", "version": 1},
                                               {"id": "ex:KingOfNavarre", "version": 1},
                                               {"id": "f:king-14b", "version": 1}]
    assert compare_containers(store.export("khg-json"), result["store"].export("khg-json")) == []
    assert result["store"].get("f:king-14b")["recorded_at"] == "2026-10-01T00:00:09.000001Z"


def test_the_factory_builds_the_store_on_a_clock_before_the_first_accept(smoke, store, schema, base):
    q = smoke.create(base=base)
    qid = smoke.submit(q)
    smoke.lint(q, qid)
    smoke.accept(q, qid, store)
    built = []

    def factory(s, clock):
        built.append(clock.now())
        return MemoryStore(s, clock=clock, store_id="replay")
    result = replay(q, schema=schema, factory=factory, base=base)
    assert result["ok"] and result["store"].info()["store_id"] == "replay"
    assert built == ["2026-10-01T00:00:00Z"]  # the header's created_at
    late = Queue.create(smoke.path(), queue_id="p2-smoke", schema=schema, base=base,
                        created_at="2026-10-02T00:00:00Z")  # created after its accept's time: load just before
    late_store = MemoryStore(schema, clock=ScenarioClock())
    late_store.load(base)
    lq = smoke.submit(late)
    smoke.lint(late, lq)
    smoke.accept(late, lq, late_store)
    built.clear()
    assert replay(late, schema=schema, factory=factory, base=base)["ok"]
    assert built == ["2026-10-01T00:00:06.999999Z"]


# ------------------------------------------------------------------------------------------------ review fixes

Y0 = "0000-01-01T00:00:00Z"  # the first instant a queue timestamp names


def test_an_accept_at_the_first_instant_of_year_0_replays(smoke, schema, base):
    """The base load is never put before year 0, which no timestamp can name (it raised ``ValueError``)."""
    from khg_contracts.queue import Linter, make_candidate
    from khg_contracts.validate import validate_queue

    entities = [r for r in base["records"] if r["id"] in ("ex:LouisXIV", "ex:KingOfFrance", "ex:LouisXIII")]
    q = Queue.create(smoke.path(), queue_id="p2-smoke", schema=schema, created_at=Y0)  # no base
    qid = q.submit(make_candidate(smoke.king14, queue_id="p2-smoke", seq=1, schema=schema), run=smoke.RUN,
                   doc=smoke.DOC, submitted_by=smoke.SUBMITTED_BY, entities=entities, at=Y0)
    assert Linter(schema).lint(q, qid, at=Y0)["outcome"] == "pass"
    q.accept(qid, store=MemoryStore(schema, clock=ScenarioClock(Y0)), id="f:king-14", actor="curator:smoke",
             reason=smoke.REASON, at=Y0)
    assert validate_queue(q, schema=schema) == {"ok": True, "findings": []}
    result = replay(q, schema=schema, factory=memory_factory)
    assert result["ok"] and result["store"].get("f:king-14")["recorded_at"] == Y0
    # with a base, the load and the accept then share that instant: a finding on the accept, not an exception
    lines = data.load_jsonl(SMOKE)
    lines[3]["at"] = Y0
    assert [c for c, _ in _codes(replay(lines, schema=schema, factory=memory_factory, base=base))] == ["KHG-Q006"]


@pytest.mark.parametrize("depth", [300, 600])
def test_lines_in_memory_get_the_nesting_limit_of_a_file(tmp_path, schema, base, depth):
    """Lines given as objects are J001 beyond layer J's 256 levels, as the same lines in a file are (they were
    replayed at 300 levels and raised ``RecursionError`` at 600)."""
    from khg_contracts.validate import ENGINES, validate

    nested: list = []
    for _ in range(depth - 1):  # built without recursion: an empty list inside depth - 1 lists
        nested = [nested]
    lines = data.load_jsonl(SMOKE)
    lines[1]["payload"]["extensions"] = {"ex:x": nested}
    raised = []
    for source in (lines, _write(tmp_path, lines)):
        with pytest.raises(ValidationError) as exc:
            replay(source, schema=schema, factory=memory_factory, base=base)
        raised.append([(f["code"], f["path"]) for f in exc.value.info["findings"]])
    assert raised[0] == raised[1] and raised[0][0][0] == "KHG-J001"
    assert raised[0][0][1].startswith("/lines/1/payload/extensions/ex:x/0/0/")
    for engine in ENGINES:
        assert [(f["code"], f["path"]) for f in validate(lines, kind="queue", schema=schema, bases=[base],
                                                          engine=engine)["findings"]] == raised[0]


@pytest.mark.parametrize("where", ["record", "put"])
def test_a_recursion_error_in_a_replayed_accept_is_q006(monkeypatch, schema, base, where):
    """Python's recursion limit, met while the accepted record is built or written, is a Q006 finding on the
    accept, as a store error is (it propagated from ``replay`` and from layer Q)."""
    replay_module = importlib.import_module("khg_contracts.queue.replay")  # the package exports the function

    def deep(*args, **kwargs):
        raise RecursionError("maximum recursion depth exceeded")

    class Deep(MemoryStore):
        def put(self, *args, **kwargs):
            return deep()

    if where == "record":
        monkeypatch.setattr(replay_module, "accepted_record", deep)
    factory = memory_factory if where == "record" else (lambda s, clock: Deep(s, clock=clock))
    result = replay(data.path(SMOKE), schema=schema, factory=factory, base=base)
    assert _codes(result) == [("KHG-Q006", "/lines/3")] and result["decisions"] == []
    assert "maximum recursion depth exceeded" in result["findings"][0]["message"]
