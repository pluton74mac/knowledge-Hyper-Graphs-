"""W4: the 2 V, 20 C and 33 C1 S cases of the G2 list under both engines, and the bases (DESIGN §8.1, §8.2).

A case passes when its first rejecting layer is the listed layer and the listed code is among its error codes.
Each case runs once per engine with the full report (every step); the findings up to the first rejecting step are
what the prototype harness recorded (its runs stopped there), so their error codes equal the case's ``reported``
codes. Engine agreement is checked on these single-fault inputs: fastjsonschema's codes at the first rejecting step
are among jsonschema's. No step may fail on what an earlier layer rejected.
"""
from __future__ import annotations

import pytest

from khg_contracts import data
from khg_contracts.validate import run, validate

CASES = data.load_json("malformed-cases.json")["cases"]
V_CASES = [c["id"] for c in CASES if c["layer"] == "V"]
C_CASES = [c["id"] for c in CASES if c["layer"] == "C"]
S_CASES = [c["id"] for c in CASES if c["layer"] == "S" and c["kind"] == "c1"]
W4_CASES = V_CASES + C_CASES + S_CASES
ENGINES = ("jsonschema", "fastjsonschema")


def _codes(findings):
    return sorted({f["code"] for f in findings if f["severity"] == "error"})


def _resolve(doc, pointer):
    for p in pointer.split("/")[1:]:
        doc = doc[int(p)] if isinstance(doc, list) else doc[p]
    return doc


def test_the_list_has_2_v_20_c_and_33_c1_s_cases():
    assert len(V_CASES) == 2 and len(C_CASES) == 20 and len(S_CASES) == 33
    assert {c["code"] for c in CASES if c["id"] in C_CASES} == {f"KHG-C{i:03d}" for i in range(1, 13)}
    s_codes = {c["code"] for c in CASES if c["id"] in S_CASES}
    assert s_codes == {f"KHG-S{i:03d}" for i in (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 13, 14, 15, 16, 18, 19, 20, 21,
                                                   22, 23, 24, 25, 26)}


@pytest.mark.parametrize("case_id", W4_CASES)
def test_case_self_checks(case_id, malformed):
    """Every patch applies, the input differs from its base, and every expect_target resolves in the base."""
    case = malformed.by_id[case_id]
    obj, schema, _ = malformed.inputs(case)
    base = malformed.base(case["base"])
    assert obj != base or schema != malformed.schema
    for pointer, want in (case.get("expect_target") or {}).items():
        assert pointer.startswith("/records/")
        assert _resolve(base, pointer)["id"] == want


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("case_id", W4_CASES)
def test_case_is_rejected_first_at_its_layer_with_its_code(case_id, engine, malformed):
    case = malformed.by_id[case_id]
    report = malformed.report(case_id, engine)
    assert not report.ok
    assert report.first_layer == case["layer"]
    assert case["code"] in _codes(report.findings)
    assert report.skipped == []  # no step failed on what an earlier layer rejected


@pytest.mark.parametrize("case_id", W4_CASES)
def test_the_first_rejecting_step_reports_exactly_the_listed_codes(case_id, malformed):
    """jsonschema's report up to the first rejecting step has the codes the prototype recorded."""
    case = malformed.by_id[case_id]
    report = malformed.report(case_id)
    assert _codes(report.until_first_rejection()) == sorted(case["reported"])
    assert report.first_rejecting_step == case["layer"].lower()


@pytest.mark.parametrize("case_id", W4_CASES)
def test_single_fault_engine_containment(case_id, malformed):
    case = malformed.by_id[case_id]
    full = malformed.report(case_id, "jsonschema")
    fast = malformed.report(case_id, "fastjsonschema")
    assert fast.first_layer == full.first_layer == case["layer"]
    assert fast.first_rejecting_step == full.first_rejecting_step
    fast_codes, full_codes = _codes(fast.until_first_rejection()), _codes(full.until_first_rejection())
    assert set(fast_codes) <= set(full_codes)
    if case["layer"] == "C":  # a JSON Schema step: fastjsonschema stops at its first error
        assert len([f for f in fast.until_first_rejection() if f["severity"] == "error"]) == 1
    else:  # V and S are Python checks: both engines agree exactly
        assert fast_codes == full_codes


@pytest.mark.parametrize("case_id", W4_CASES)
def test_the_run_stops_only_after_v(case_id, malformed):
    report = malformed.report(case_id)
    steps = [name for name, _ in report.steps]
    if malformed.by_id[case_id]["layer"] == "V":
        assert report.stopped == "v" and steps == ["j", "v"]
    else:
        assert report.stopped is None and steps == ["j", "v", "c", "s", "d_container"]


def test_the_full_report_goes_on_after_c(malformed):
    """MC080 (no relation) leaves S nothing to read; MC083 (a lifecycle record without reason) is C012 only, since
    S026 judges a reason that is present; MC069 (precision 15) is C004 from C and again from the S parse."""
    assert _codes(malformed.report("MC080").findings) == ["KHG-C010"]
    assert _codes(malformed.report("MC083").findings) == ["KHG-C012"]
    r69 = malformed.report("MC069")
    assert [f["code"] for f in r69.errors] == ["KHG-C004", "KHG-C004"]
    assert [name for name, found in r69.steps if found] == ["c", "s"]
    assert r69.errors[1]["path"] == "/records/30/bindings/4/value/literal"


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("rel", ["fixture/fixture.c1.json", "fixture/fixture.c1.jsonl",
                                 "fixture/fixture.with-derived.c1.json", "fixture/fixture.history.c1.json",
                                 "fixture/smoke-base.c1.json"])
def test_the_c1_bases_have_no_error_and_only_the_designed_warning(rel, engine, malformed):
    result = validate(data.path(rel), schema=malformed.schema, doc_texts=malformed.doc_texts, engine=engine)
    assert result["ok"] is True
    found = [(f["code"], f["severity"], f["path"]) for f in result["findings"]]
    if "history" in rel or "smoke" in rel:
        assert found == []
    else:
        assert found == [("KHG-S024", "warning", "/records/31")]  # must_differ on f:loop-yyz (§1.4)


def test_the_sample_container_is_valid_under_its_own_schema():
    result = validate(data.path("sample/sample.khg.json"), schema=data.path("sample/sample.relation-schema.json"))
    assert result == {"ok": True, "findings": []}


@pytest.mark.parametrize("engine", ENGINES)
def test_the_other_bases_pass_the_w4_layers(engine, malformed):
    """The HIF, schema, queue and C4 bases pass J and V (and M, and C and S on the queue payloads)."""
    for name, kind in [("fixture.hif.json", "hif"), ("fixture.directed-slice.hif.json", "hif"),
                       ("fixture.relation-schema.json", "schema"), ("smoke-queue.khg-queue.jsonl", "queue"),
                       ("c4-items.jsonl", "item")]:
        base = malformed.base(name)
        obj = base["lines"] if kind in ("queue", "item") else base
        report = run(obj, kind=kind, schema=None if kind == "schema" else malformed.schema,
                     doc_texts=malformed.doc_texts, bases=[malformed.smoke_base], engine=engine)
        assert (report.ok, report.findings, report.skipped) == (True, [], []), name
