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
from khg_contracts.schema import load_schema
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
