"""W5: layer D on containers, records and queues (``validate/layers/d_container.py``; DESIGN §8.1, §8.2).

The 22 container D cases of the G2 list (MC118-MC139) under both engines: each is rejected first at layer D with its
code, and the D step reports exactly the codes the case records. The C1 bases carry only the designed warnings (§1.4),
a single record gets D015 and D017, a queue header D009, and broken input never makes the layer raise.
"""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, jsonio
from khg_contracts.record import normalize, with_derived
from khg_contracts.schema import load_schema
from khg_contracts.validate import layers, run, validate, validate_record
from khg_contracts.validate.layers import d_container

SCHEMA_DOC = data.load_json("fixture/fixture.relation-schema.json")
S = load_schema(SCHEMA_DOC)
FIXTURE = data.load_json("fixture/fixture.c1.json")
FACTS = {r["id"]: r for r in FIXTURE["records"]}
CASES = [c for c in data.load_json("malformed-cases.json")["cases"] if c["kind"] == "c1" and c["layer"] == "D"]
ENGINES = ("jsonschema", "fastjsonschema")


def _parts(pointer: str) -> list[str]:
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]


def resolve(doc, pointer: str):
    for p in _parts(pointer):
        doc = doc[int(p)] if isinstance(doc, list) else doc[p]
    return doc


def apply_patch(doc, patch):
    """RFC 6902 add, replace and remove, on a copy (the operations of the case list)."""
    doc = copy.deepcopy(doc)
    for op in patch or []:
        parts = _parts(op["path"])
        parent = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        last, value = parts[-1], copy.deepcopy(op.get("value"))
        if op["op"] == "remove":
            del parent[int(last) if isinstance(parent, list) else last]
        elif isinstance(parent, list):
            if op["op"] == "replace":
                parent[int(last)] = value
            elif last == "-":
                parent.append(value)
            else:
                parent.insert(int(last), value)
        else:
            assert op["op"] == "add" or last in parent, op["path"]
            parent[last] = value
    return doc


def inputs(case):
    """The case's container and schema: the base plus its patch, and a schema patch with the digest re-stamped."""
    doc = apply_patch(data.load_json(f"fixture/{case['base']}"), case["patch"])
    if not case.get("schema_patch"):
        return doc, S
    schema_doc = apply_patch(SCHEMA_DOC, case["schema_patch"])
    doc["header"]["schema"]["sha256"] = jsonio.digest("khg-schema/1", schema_doc)
    return doc, load_schema(schema_doc)


def _errors(findings) -> list[str]:
    return sorted({f["code"] for f in findings if f["severity"] == "error"})


def _step(report, name):
    return next(found for step, found in report.steps if step == name)


# ------------------------------------------------------------------------------------------------ the D cases


def test_the_list_has_22_container_d_cases():
    assert [c["id"] for c in CASES] == [f"MC{n}" for n in range(118, 140)]
    assert {c["code"] for c in CASES} == {f"KHG-D{n:03d}" for n in (2, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
                                                                     20)}
    assert layers.implemented("d_container") and d_container.OWNER == "W5"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_case_self_checks(case):
    """Every patch applies, the input differs from its base, and every expect_target resolves in the base."""
    base = data.load_json(f"fixture/{case['base']}")
    doc, _ = inputs(case)
    assert doc != base
    for pointer, want in (case.get("expect_target") or {}).items():
        target = resolve(base, pointer)
        assert ([target["id"], target["version"]] if isinstance(want, list) else target["id"]) == want


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_case_is_rejected_first_at_layer_d_with_exactly_its_codes(case, engine):
    doc, schema = inputs(case)
    report = run(doc, kind="container", schema=schema, engine=engine)
    assert report.first_layer == "D" and case["code"] in _errors(report.findings)
    assert report.first_rejecting_step == "d_container" and report.skipped == []
    assert _errors(report.until_first_rejection()) == sorted(case["reported"])
    # the G2 harness mode stops after the first rejecting step and gives the same codes
    first = run(doc, kind="container", schema=schema, engine=engine, stop="first")
    assert first.stopped == "d_container" and _errors(first.findings) == sorted(case["reported"])


FINDINGS = {  # the D errors of some cases: (code, path)
    "MC118": [("KHG-D008", "/records/27/bindings/0/value")],
    "MC119": [("KHG-D010", "/records/24/status_ref")],
    "MC121": [("KHG-D010", "/records/24/status_ref"), ("KHG-D010", "/records/39/bindings/0/value"),
              ("KHG-D011", "/records/39")],
    "MC126": [("KHG-D016", "/records/29")],
    "MC130": [("KHG-D015", "/records/35/derived")],
    "MC131": [("KHG-D017", "/records/35/status")],
    "MC132": [("KHG-D002", "/records/34/bindings/0/value")],
    "MC133": [("KHG-D001", "/records/35"), ("KHG-D007", "/records/35"), ("KHG-D002", "/records/35/bindings/1/value"),
              ("KHG-D002", "/records/35/bindings/2/value")],
    "MC134": [("KHG-D009", "/header/schema")],
    "MC135": [("KHG-D020", "/records/22/bindings/0/value")],
    "MC136": [("KHG-D013", "/records/6/bindings/1/value")],
    "MC137": [("KHG-D013", "/records/6/evidence/0")],
    "MC138": [("KHG-D014", "/records/10/status"), ("KHG-D010", "/records/9/bindings/0/value")],
    "MC139": [("KHG-D018", "/records/6/recorded_at")],
}


@pytest.mark.parametrize("cid", sorted(FINDINGS))
def test_the_findings_point_at_the_record(cid):
    case = next(c for c in CASES if c["id"] == cid)
    doc, schema = inputs(case)
    found = _step(run(doc, kind="container", schema=schema), "d_container")
    assert [(f["code"], f["path"]) for f in found if f["severity"] == "error"] == FINDINGS[cid]
    assert all(f["message"] and f["layer"] == ("D" if f["severity"] == "error" else "L") for f in found)
    assert {f["code"] for f in found if f["severity"] == "warning"} <= {"KHG-L008"}


def test_the_key_invariant_message_names_the_facts_and_the_instant():
    case = next(c for c in CASES if c["id"] == "MC126")
    doc, schema = inputs(case)
    [f] = _step(run(doc, kind="container", schema=schema), "d_container")
    assert "f:king-13 and f:king-14 hold at +1640-01-02T00:00:00Z" in f["message"]


# ------------------------------------------------------------------------------------------------ bases


DESIGNED = [("KHG-S024", "warning", "/records/31"), ("KHG-L008", "warning", "/records/29")]


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize(("rel", "want"), [
    ("fixture/fixture.c1.json", DESIGNED), ("fixture/fixture.c1.jsonl", DESIGNED),
    ("fixture/fixture.with-derived.c1.json", DESIGNED), ("fixture/fixture.history.c1.json", []),
    ("fixture/smoke-base.c1.json", [])])
def test_the_bases_carry_only_the_designed_warnings(rel, want, engine):
    result = validate(data.path(rel), schema=S, engine=engine)
    assert result["ok"] is True
    assert [(f["code"], f["severity"], f["path"]) for f in result["findings"]] == want


def test_the_derived_blocks_of_the_store_form_agree():
    def d_step(doc):
        return [(f["code"], f["severity"], f["path"]) for f in _step(run(doc, kind="container", schema=S),
                                                                       "d_container")]

    stored = with_derived(FIXTURE, S)
    assert d_step(stored) == [("KHG-L008", "warning", "/records/29")]
    stored["records"][30]["derived"]["arity"] = 4
    assert d_step(stored) == [("KHG-D015", "error", "/records/30/derived"), ("KHG-L008", "warning", "/records/29")]
    lifecycle_record = stored["records"][39]
    assert lifecycle_record["id"] == "m:sup-1" and "derived" not in lifecycle_record
    lifecycle_record["derived"] = {}
    assert d_step(stored)[0] == ("KHG-D015", "error", "/records/30/derived") and len(d_step(stored)) == 2


def test_a_container_without_a_schema_gets_d009_once_and_no_other_d_rule():
    report = run(FIXTURE, kind="container")
    assert [(f["code"], f["path"]) for f in report.errors] == [("KHG-D009", "/header/schema")]
    assert _step(report, "d_container") == []
    only_d = run(FIXTURE, kind="container", steps=["d_container"])
    assert [(f["code"], f["path"]) for f in only_d.errors] == [("KHG-D009", "/header/schema")]


def test_an_embedded_schema_is_pinned_too():
    doc = copy.deepcopy(FIXTURE)
    doc["records"].insert(0, copy.deepcopy(SCHEMA_DOC))
    assert run(doc, kind="container").ok
    doc["header"]["schema"]["version"] = "1.0.1"
    [f] = run(doc, kind="container").errors
    assert (f["code"], f["path"]) == ("KHG-D009", "/header/schema") and "version" in f["message"]


def test_an_incomplete_container_may_reference_what_it_does_not_hold():
    doc = copy.deepcopy(FIXTURE)
    doc["header"]["complete"] = False
    doc["records"] = [r for r in doc["records"] if r.get("id") not in ("ex:HeLa", "f:born-louis14-paris")]
    assert run(doc, kind="container", schema=S).ok
    doc["header"]["complete"] = True
    assert [f["code"] for f in run(doc, kind="container", schema=S).errors] == ["KHG-D002", "KHG-D002"]


def test_vocabulary_ids_are_never_references():
    doc = copy.deepcopy(FIXTURE)
    assert "wd:Q11573" not in {r["id"] for r in doc["records"]}  # a unit, a globe and a rank reason
    assert run(doc, kind="container", schema=S).ok


# ------------------------------------------------------------------------------------------------ records, queues


def test_a_single_record_gets_d017_and_d015():
    reg = FACTS["f:reg-1"]
    assert validate_record(reg, schema=S)["ok"]
    candidate = dict(reg, status="candidate")
    assert [(f["code"], f["path"]) for f in validate_record(candidate, schema=S)["findings"]
            if f["severity"] == "error"] == [("KHG-D017", "/status")]
    derived = dict(normalize(reg), derived={"arity": 4})
    assert [(f["code"], f["path"]) for f in validate_record(derived, schema=S)["findings"]] == [
        ("KHG-D015", "/derived")]
    good = with_derived({"header": FIXTURE["header"], "records": [reg]}, S)["records"][0]
    assert validate_record(good, schema=S) == {"ok": True, "findings": []}
    assert [f["code"] for f in validate_record(candidate)["findings"] if f["severity"] == "error"] == [
        "KHG-D009", "KHG-D017"]


def test_a_queue_header_is_pinned_to_the_schema():
    lines = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    base = data.load_json("fixture/smoke-base.c1.json")
    assert _step(run(lines, kind="queue", schema=S, bases=[base]), "d_container") == []
    moved = copy.deepcopy(lines)
    moved[0]["schema"]["sha256"] = "sha256:" + "0" * 64
    found = _step(run(moved, kind="queue", schema=S, bases=[base]), "d_container")
    assert [(f["code"], f["path"]) for f in found] == [("KHG-D009", "/lines/0/schema")]
    assert _step(run(lines[1:], kind="queue", schema=S), "d_container") == []  # no header: Q008 is layer Q's


def test_a_hif_run_checks_the_decoded_container():
    """In a HIF run the cross-record rules run on the decoded container after S; decoding owns the pin."""
    assert layers.implemented("d_decode")  # W6 (S4: the stub-era skips are assertions now)
    report = run(data.path("fixture/fixture.hif.json"), kind="hif", schema=S)
    assert _step(report, "d_decode") == []  # the fixture decodes, with no D009 from the pin
    assert [(f["code"], f["severity"]) for f in _step(report, "d_container")] == [("KHG-L008", "warning")]


# ------------------------------------------------------------------------------------------------ broken input


def _broken():
    """Containers that layers C and S reject; layer D must read them without raising."""
    def edit(fn):
        doc = copy.deepcopy(FIXTURE)
        fn(doc)
        return doc

    recs = lambda d: d["records"]  # noqa: E731
    yield edit(lambda d: d.update(records={"a": 1}))
    yield edit(lambda d: d["header"].update(schema="p2-gate"))
    yield edit(lambda d: recs(d).append("not a record"))
    yield edit(lambda d: recs(d).append({"kind": "hyperedge", "id": ["x"], "status": "asserted"}))
    yield edit(lambda d: recs(d).append({"kind": "hyperedge", "id": "f:x", "relation": "no_such", "status": "asserted",
                                         "bindings": "none"}))
    yield edit(lambda d: recs(d)[29].update(bindings=[1, {"bid": "b1"}, {"value": {"entity": 3}}]))
    yield edit(lambda d: recs(d)[29]["bindings"][3].update(value={"literal": {"datatype": "time", "time": "x"}}))
    yield edit(lambda d: recs(d)[30]["bindings"][2].update(value={"entity": "ex:KingOfFrance", "fact": "f:x"}))
    yield edit(lambda d: recs(d)[24].update(status_ref=["m:sup-1"]))
    yield edit(lambda d: recs(d)[39].update(bindings=[{"bid": "b1", "role": "khg:superseding", "value": "f:x"}]))
    yield edit(lambda d: recs(d)[35].update(derived=[1, 2], status="candidate"))
    yield edit(lambda d: recs(d)[27]["bindings"].append({"bid": "b9", "role": "unknown", "value": {"fact": 7}}))
    history = copy.deepcopy(data.load_json("fixture/fixture.history.c1.json"))
    history["records"][6].update(version="2", recorded_at="yesterday")
    history["records"][7]["evidence"] = "none"
    history["header"]["as_at"] = 5
    yield history


@pytest.mark.parametrize("engine", ENGINES)
def test_broken_containers_never_make_the_layer_raise(engine):
    for n, doc in enumerate(_broken()):
        report = run(doc, kind="container", schema=S, engine=engine)
        assert report.skipped == [] and "d_container" in [s for s, _ in report.steps], n
        assert not report.ok, n
