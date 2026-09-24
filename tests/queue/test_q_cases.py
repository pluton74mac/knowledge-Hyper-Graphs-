"""W9: layer Q in the validator and the 17 Q cases of the G2 list (DESIGN §7, §8.1, §8.2).

A case passes when its first rejecting layer is Q and its code is among the error codes. The findings up to the first
rejecting step are exactly the case's ``reported`` codes (the prototype harness stopped there), and fastjsonschema's
codes there are among jsonschema's. Layer Q never reports the schema pin (D009 is layer D's), and it replays the
accepts only when nothing else in it is an error.
"""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, jsonio, record
from khg_contracts.errors import ValidationError
from khg_contracts.queue import Queue, queue_items, replay
from khg_contracts.queue.lines import dump_line
from khg_contracts.schema import load_schema
from khg_contracts.store import memory_factory
from khg_contracts.validate import ENGINES, layers, run, validate_queue

LIST = data.load_json("malformed-cases.json")
CASES = [c for c in LIST["cases"] if c["layer"] == "Q"]
BY_ID = {c["id"]: c for c in CASES}
SCHEMA = load_schema(data.load_json("fixture/fixture.relation-schema.json"))
BASE = data.load_json("fixture/smoke-base.c1.json")
LINES = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")


def _parts(pointer):
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]


def patched(doc, patch):
    """RFC 6902 ``add``, ``replace`` and ``remove`` on a copy (the operations the Q cases use)."""
    doc = copy.deepcopy(doc)
    for op in patch:
        *head, last = _parts(op["path"])
        parent = doc
        for p in head:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        key = int(last) if isinstance(parent, list) else last
        if op["op"] == "remove":
            del parent[key]
        elif op["op"] == "replace":
            assert isinstance(parent, list) or key in parent, op["path"]
            parent[key] = copy.deepcopy(op["value"])
        else:
            assert op["op"] == "add", op
            if isinstance(parent, list):
                parent.insert(len(parent) if last == "-" else key, copy.deepcopy(op["value"]))
            else:
                parent[key] = copy.deepcopy(op["value"])
    return doc


def lines_of(case):
    return patched({"lines": LINES}, case["patch"])["lines"]


_REPORTS: dict = {}


def report(case_id, engine="jsonschema"):
    if (case_id, engine) not in _REPORTS:
        _REPORTS[case_id, engine] = run(lines_of(BY_ID[case_id]), kind="queue", schema=SCHEMA,
                                        bases={"p2-smoke-base": BASE}, engine=engine)
    return _REPORTS[case_id, engine]


def _codes(findings):
    return sorted({f["code"] for f in findings if f["severity"] == "error"})


def test_the_list_has_17_q_cases_covering_every_q_code():
    assert len(CASES) == 17
    assert {c["code"] for c in CASES} == {f"KHG-Q{i:03d}" for i in range(1, 13)}
    assert all(c["kind"] == "queue" and c["base"] == "smoke-queue.khg-queue.jsonl" for c in CASES)
    assert layers.implemented("q") and layers.spec("q").owner == "W9"


@pytest.mark.parametrize("case_id", sorted(BY_ID))
def test_case_self_checks(case_id):
    """Every patch applies, the input differs from its base, and every expect_target names its line."""
    case = BY_ID[case_id]
    assert lines_of(case) != LINES
    for pointer, (kind, ident) in case["expect_target"].items():
        line = LINES[int(_parts(pointer)[1])]
        assert line["kind"] == kind
        assert line.get("qid", line.get("lid")) == ident


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("case_id", sorted(BY_ID))
def test_case_is_rejected_first_at_layer_q_with_its_code(case_id, engine):
    r = report(case_id, engine)
    case = BY_ID[case_id]
    assert not r.ok and r.first_layer == "Q" and r.first_rejecting_step == "q"
    assert case["code"] in _codes(r.until_first_rejection())
    assert r.skipped == []


@pytest.mark.parametrize("case_id", sorted(BY_ID))
def test_the_first_rejecting_step_reports_exactly_the_listed_codes(case_id):
    assert _codes(report(case_id).until_first_rejection()) == sorted(BY_ID[case_id]["reported"])


@pytest.mark.parametrize("case_id", sorted(BY_ID))
def test_single_fault_engine_containment(case_id):
    fast, full = report(case_id, "fastjsonschema"), report(case_id)
    assert set(_codes(fast.until_first_rejection())) <= set(_codes(full.until_first_rejection()))
    assert BY_ID[case_id]["code"] in _codes(fast.until_first_rejection())


@pytest.mark.parametrize("engine", ENGINES)
def test_the_smoke_queue_is_clean(engine):
    r = run(LINES, kind="queue", schema=SCHEMA, bases=[BASE], engine=engine)
    assert r.findings == [] and [name for name, _ in r.steps] == ["j", "v", "q", "c", "s", "d_container"]
    assert validate_queue(data.path("fixture/smoke-queue.khg-queue.jsonl"), schema=SCHEMA,
                          bases=[data.path("fixture/smoke-base.c1.json")]) == {"ok": True, "findings": []}


def test_a_queue_whose_base_is_not_supplied_is_q012_and_its_entities_q011():
    found = [(f["code"], f["path"]) for f in dict(run(LINES, kind="queue", schema=SCHEMA).steps)["q"]]
    assert found == [("KHG-Q012", "/lines/0/base")] + [("KHG-Q011", f"/lines/1/payload/bindings/{i}/value")
                                                       for i in (1, 2, 3)]
    other = dict(BASE, header=dict(BASE["header"], document_id="another-base"))
    assert [f["code"] for f in dict(run(LINES, kind="queue", schema=SCHEMA, bases=[other]).steps)["q"]][0] == \
        "KHG-Q012"


def test_layer_q_leaves_the_schema_pin_to_layer_d():
    doc = data.load_json("fixture/fixture.relation-schema.json")
    replaces = next(r for r in next(x for x in doc["relations"] if x["id"] == "position_held")["roles"]
                    if r["role"] == "replaces")
    replaces["slot"] = "core"  # another schema, under which the item's core_key would differ
    other = load_schema(doc)
    assert record.core_key(LINES[1]["payload"], other) != LINES[1]["keys"]["core_key"]
    r = run(LINES, kind="queue", schema=other, bases=[BASE])
    assert dict(r.steps)["q"] == []  # no Q010 and no replay under a schema the header does not pin
    assert [(f["code"], f["path"]) for f in r.errors] == [("KHG-D009", "/lines/0/schema")] and r.first_layer == "D"
    none = run(LINES, kind="queue", bases=[BASE])
    assert dict(none.steps)["q"] == [] and [f["code"] for f in none.errors] == ["KHG-D009"]


def test_the_replay_runs_only_when_nothing_else_is_an_error():
    assert _codes(report("MC173").findings) == ["KHG-Q010"]  # the replayed decision would differ too
    assert [f["path"] for f in dict(report("MC168").steps)["q"]] == ["/lines/3/decision_hash"]
    lines = copy.deepcopy(LINES)
    lines[1]["payload"]["rank"] = "preferred"  # not in the keys or the event hash: only the replay sees it
    r = run(lines, kind="queue", schema=SCHEMA, bases=[BASE])
    assert [(f["code"], f["path"]) for f in r.errors] == [("KHG-Q006", "/lines/3/decision_hash")]


def _verdict_line(**change):
    v = {"evidence_id": "e2", "core_key": LINES[1]["keys"]["core_key"],
         "event_hash": LINES[1]["payload"]["evidence"][1]["event_hash"], "label": "correct",
         "bindings": [{"role": "replaces", "position": None, "value": {"entity": "ex:LouisXIII"}, "label": "correct"}],
         "missing": []}
    v.update(change)
    return {"kind": "log-entry", "lid": "l:p2-smoke.000003", "parent": "l:p2-smoke.000002",
            "target": "q:p2-smoke.000001", "action": "verdict", "state_before": "accepted", "state_after": "accepted",
            "actor": {"type": "person", "id": "curator:smoke"}, "mode": "manual", "at": "2026-10-01T00:01:00Z",
            "verdict": v}


@pytest.mark.parametrize(("change", "found"), [
    ({}, []),
    ({"core_key": "sha256:" + "3" * 64}, [("KHG-Q010", "/lines/4/verdict/core_key")]),
    ({"event_hash": "sha256:" + "4" * 64}, [("KHG-Q010", "/lines/4/verdict/event_hash")]),
    ({"evidence_id": "e3"}, [("KHG-Q008", "/lines/4/verdict/evidence_id")]),
    ({"bindings": [{"role": "replaces", "position": 1, "value": {"entity": "ex:LouisXIII"}, "label": "correct"}]},
     [("KHG-Q008", "/lines/4/verdict/bindings/0")]),
    # §7: the bid is only a hint. b1's (role, position, value) under b5's bid is b1, and no finding
    ({"bindings": [{"role": "holder", "position": None, "value": {"entity": "ex:LouisXIV"}, "bid": "b5",
                    "label": "correct"}]}, []),
])
def test_verdict_entries_are_checked_against_their_item(change, found):
    r = run(LINES + [_verdict_line(**change)], kind="queue", schema=SCHEMA, bases=[BASE])
    assert [(f["code"], f["path"]) for f in r.findings] == found


def test_a_candidate_id_of_another_queue_is_q002():
    lines = copy.deepcopy(LINES)
    lines[1]["payload"]["id"] = "cand:another-queue.000001"
    r = run(lines, kind="queue", schema=SCHEMA, bases=[BASE])
    assert [(f["code"], f["path"]) for f in r.errors] == [("KHG-Q002", "/lines/1/payload/id")]


def test_the_findings_and_their_order_do_not_depend_on_the_engine_for_the_python_checks():
    for case_id in ("MC167", "MC169", "MC171", "MC172", "MC174", "MC175"):
        full = [(f["code"], f["path"]) for f in dict(report(case_id).steps)["q"]]
        fast = [(f["code"], f["path"]) for f in dict(report(case_id, "fastjsonschema").steps)["q"]]
        assert fast == full, case_id
    again = run(lines_of(BY_ID["MC175"]), kind="queue", schema=SCHEMA, bases={"p2-smoke-base": BASE})
    assert jsonio.canonical(again.result()) == jsonio.canonical(report("MC175").result())


@pytest.mark.parametrize("engine", ENGINES)
def test_values_that_cannot_be_hashed_are_findings_not_type_errors(engine):
    """A list where layer Q looks up an id (an item entity's ``id``, a verdict's ``target``) is reported by the
    schema and the fold; the lookups raised ``TypeError`` from ``validate``."""
    lines = copy.deepcopy(LINES)
    lines[1]["entities"] = [{"kind": "entity", "id": ["ex:X"], "types": ["Person"]}]
    r = run(lines, kind="queue", schema=SCHEMA, bases=[BASE], engine=engine)
    assert [(f["code"], f["path"]) for f in r.errors] == [("KHG-C010", "/lines/1/entities/0/id")]
    for target in (["x"], {"qid": "q:p2-smoke.000001"}):
        r = run(LINES + [dict(_verdict_line(), target=target)], kind="queue", schema=SCHEMA, bases=[BASE],
                engine=engine)
        assert [(f["code"], f["path"]) for f in r.errors] == [("KHG-Q008", "/lines/4/target"),
                                                              ("KHG-Q007", "/lines/4/target")]
        assert validate_queue(LINES + [dict(_verdict_line(), target=target)], schema=SCHEMA,
                              bases=[BASE])["ok"] is False


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("kind", [["queue-item"], {"kind": "log-entry"}], ids=["list", "object"])
def test_a_line_kind_that_cannot_be_hashed_is_q003_not_a_type_error(tmp_path, kind, engine):
    """Review integration: the calendar check of queue times (Q-TIMESTAMP-CALENDAR) looked the line's ``kind`` up in
    a dict, so a list or object ``kind`` raised ``TypeError`` from ``validate``, ``Queue.open``, ``replay`` and
    ``queue_items``; at f99a8af it was the schema's Q003."""
    for n in range(1, len(LINES)):
        lines = copy.deepcopy(LINES)
        lines[n]["kind"] = kind
        r = run(lines, kind="queue", schema=SCHEMA, bases=[BASE], engine=engine)
        assert ("KHG-Q003", f"/lines/{n}/kind") in [(f["code"], f["path"]) for f in r.errors]
        path = tmp_path / f"q{n}.khg-queue.jsonl"
        path.write_text("".join(dump_line(x) for x in lines), encoding="utf-8")
        with pytest.raises(ValidationError):
            Queue.open(path, schema=SCHEMA)
        assert replay(path, schema=SCHEMA, factory=memory_factory, base=BASE)["ok"] is False
        with pytest.raises(ValidationError):
            list(queue_items(path))


def test_layer_q_asks_only_for_string_targets(monkeypatch):
    """Review integration (group ex's request): layer Q tests that a verdict's ``target`` is a string before it looks
    it up, so it does not rely on ``queue.fold.Fold.items`` answering ``in`` for an unhashable value."""
    from khg_contracts.validate.layers import q as layer_q

    real = layer_q.check

    def plain(lines, *, engine="jsonschema"):
        fold, out = real(lines, engine=engine)
        fold.items = dict(fold.items)  # a plain dict: ``[...] in fold.items`` is a TypeError
        return fold, out

    monkeypatch.setattr(layer_q, "check", plain)
    for target in (["x"], {"qid": "q:p2-smoke.000001"}):
        r = run(LINES + [dict(_verdict_line(), target=target)], kind="queue", schema=SCHEMA, bases=[BASE])
        assert [(f["code"], f["path"]) for f in r.errors] == [("KHG-Q008", "/lines/4/target"),
                                                              ("KHG-Q007", "/lines/4/target")]


@pytest.mark.parametrize("stamp", ["khg-record/1.1.0", "khg-record/2.0.0", "khg-record/1.0", "khg-queue/1.0.0", 7])
def test_a_record_format_this_reader_does_not_take_is_v001(tmp_path, stamp):
    """§11.2: a reader rejects a newer stamp with V001, the header's ``record_format`` as its ``format`` (it was the
    queue schema's Q008). The validator, ``Queue.open``, ``replay`` and ``queue_items`` read no further."""
    lines = copy.deepcopy(LINES)
    lines[0]["record_format"] = stamp
    want = [("KHG-V001", "/lines/0/record_format")]
    for engine in ENGINES:
        r = run(lines, kind="queue", schema=SCHEMA, bases=[BASE], engine=engine)
        assert [(f["code"], f["path"]) for f in r.errors] == want and r.first_layer == "V"
    path = tmp_path / "q.khg-queue.jsonl"
    path.write_text("".join(dump_line(x) for x in lines), encoding="utf-8")
    with pytest.raises(ValidationError) as exc:
        Queue.open(path, schema=SCHEMA)
    assert exc.value.codes == ("KHG-V001",)
    result = replay(path, schema=SCHEMA, factory=memory_factory, base=BASE)
    assert [(f["code"], f["path"]) for f in result["findings"]] == want and result["store"] is None
    with pytest.raises(ValidationError) as exc:
        list(queue_items(path))
    assert exc.value.codes == ("KHG-V001",)


def test_a_record_format_of_another_patch_is_read(tmp_path):
    lines = copy.deepcopy(LINES)
    lines[0]["record_format"] = "khg-record/1.0.9"
    assert validate_queue(lines, schema=SCHEMA, bases=[BASE]) == {"ok": True, "findings": []}
    path = tmp_path / "q.khg-queue.jsonl"
    path.write_text("".join(dump_line(x) for x in lines), encoding="utf-8")
    assert Queue.open(path, schema=SCHEMA).header["record_format"] == "khg-record/1.0.9"
    del lines[0]["record_format"]  # the header requires it: the schema's Q008
    assert [(f["code"], f["path"]) for f in run(lines, kind="queue", schema=SCHEMA, bases=[BASE]).errors] == [
        ("KHG-Q008", "/lines/0")]


@pytest.mark.parametrize(("n", "field"), [(0, "created_at"), (1, "submitted_at"), (2, "at"), (3, "at")])
@pytest.mark.parametrize("value", ["2026-02-30T00:00:03Z", "2026-99-99T99:99:99Z", "2026-10-01T24:00:00Z"])
def test_a_time_that_is_no_calendar_date_time_is_q008(n, field, value):
    """Queue times have the pattern of RFC 3339 timestamps and must be ones: an impossible date-time was accepted
    (only an accept's replay would fail on it)."""
    lines = copy.deepcopy(LINES)
    lines[n][field] = value
    for engine in ENGINES:
        r = run(lines, kind="queue", schema=SCHEMA, bases=[BASE], engine=engine)
        assert [(f["code"], f["path"]) for f in r.errors] == [("KHG-Q008", f"/lines/{n}/{field}")]
