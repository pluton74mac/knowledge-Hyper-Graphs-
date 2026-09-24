"""W6: the HIF cases of the G2 list under both engines (DESIGN §8.1, §8.2): the 15 H, 6 R, 24 P and 8 decoding D
cases, and MC063 (S016, emitted while decoding).

A case passes when its first rejecting layer is the listed layer and the listed code is among its error codes. The
full report of each case runs every step; the findings up to the first rejecting step are what the prototype
harness recorded, so their error codes equal the case's ``reported`` codes. On these single-fault inputs
fastjsonschema's codes at the first rejecting step are among jsonschema's, and no step fails on what an earlier
layer rejected.
"""
from __future__ import annotations

import copy
import functools

import pytest

from khg_contracts import data
from khg_contracts.schema import load_schema
from khg_contracts.validate import run

CASES = [c for c in data.load_json("malformed-cases.json")["cases"] if c["kind"] == "hif"]
BY_ID = {c["id"]: c for c in CASES}
H = [c["id"] for c in CASES if c["layer"] == "H"]
R = [c["id"] for c in CASES if c["layer"] == "R"]
P = [c["id"] for c in CASES if c["layer"] == "P"]
D = [c["id"] for c in CASES if c["layer"] == "D"]
W6 = H + R + P + D + ["MC063"]
ENGINES = ("jsonschema", "fastjsonschema")
SCHEMA = load_schema(data.load_json("fixture/fixture.relation-schema.json"))
BASES = {"fixture.hif.json": "fixture/fixture.hif.json",
         "fixture.directed-slice.hif.json": "fixture/fixture.directed-slice.hif.json"}
#: The step that rejects each layer's cases first: decoding emits S016 (MC063).
STEP = {"H": "h", "R": "r", "P": "p", "D": "d_decode", "S": "d_decode"}


def _resolve(doc, pointer):
    for p in pointer.split("/")[1:]:
        doc = doc[int(p)] if isinstance(doc, list) else doc[p]
    return doc


def _patched(case):
    doc = data.load_json(BASES[case["base"]])
    for op in case["patch"]:
        *parents, last = op["path"].split("/")[1:]
        parent = _resolve(doc, "/" + "/".join(parents)) if parents else doc
        value = copy.deepcopy(op.get("value"))
        if op["op"] == "remove":
            del parent[int(last) if isinstance(parent, list) else last]
        elif op["op"] == "add" and isinstance(parent, list):
            parent.append(value) if last == "-" else parent.insert(int(last), value)
        else:
            parent[int(last) if isinstance(parent, list) else last] = value
    return doc


@functools.lru_cache(maxsize=None)
def _report(case_id, engine="jsonschema"):
    return run(_patched(BY_ID[case_id]), kind="hif", schema=SCHEMA,
               doc_texts=data.path("fixture/fixture.doc-texts.json"), engine=engine)


def _codes(findings):
    return sorted({f["code"] for f in findings if f["severity"] == "error"})


def test_the_list_has_15_h_6_r_24_p_and_8_decoding_d_cases():
    assert (len(H), len(R), len(P), len(D)) == (15, 6, 24, 8)
    assert {BY_ID[c]["code"] for c in H} == {f"KHG-H{i:03d}" for i in range(1, 10)}
    assert {BY_ID[c]["code"] for c in R} == {f"KHG-R{i:03d}" for i in range(1, 5)}
    assert {BY_ID[c]["code"] for c in P} == {f"KHG-P{i:03d}" for i in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14,
                                                                        16, 17)}
    assert {BY_ID[c]["code"] for c in D} == {"KHG-D001", "KHG-D002", "KHG-D003", "KHG-D005", "KHG-D009"}
    assert (BY_ID["MC063"]["layer"], BY_ID["MC063"]["code"]) == ("S", "KHG-S016")


@pytest.mark.parametrize("case_id", W6)
def test_case_self_checks(case_id):
    """Every patch applies, the input differs from its base, and every expect_target names what it says."""
    case = BY_ID[case_id]
    base = data.load_json(BASES[case["base"]])
    assert _patched(case) != base
    for pointer, want in (case.get("expect_target") or {}).items():
        got = _resolve(base, pointer)
        if pointer.startswith("/incidences/"):
            assert [got["edge"], got["attrs"]["khg-bid"]] == want
        else:
            assert got.get("node", got.get("edge")) == want


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("case_id", W6)
def test_case_is_rejected_first_at_its_layer_with_its_code(case_id, engine):
    case = BY_ID[case_id]
    report = _report(case_id, engine)
    assert not report.ok and report.first_layer == case["layer"]
    assert case["code"] in _codes(report.findings)
    assert report.first_rejecting_step == STEP[case["layer"]]
    assert report.skipped == [] and report.stopped is None


@pytest.mark.parametrize("case_id", W6)
def test_the_first_rejecting_step_reports_exactly_the_listed_codes(case_id):
    assert _codes(_report(case_id).until_first_rejection()) == sorted(BY_ID[case_id]["reported"])


@pytest.mark.parametrize("case_id", W6)
def test_single_fault_engine_containment(case_id):
    full, fast = _report(case_id), _report(case_id, "fastjsonschema")
    assert fast.first_layer == full.first_layer and fast.first_rejecting_step == full.first_rejecting_step
    fast_codes, full_codes = _codes(fast.until_first_rejection()), _codes(full.until_first_rejection())
    assert set(fast_codes) <= set(full_codes)
    if BY_ID[case_id]["layer"] in ("R", "D", "S"):  # Python checks: both engines agree exactly
        assert fast_codes == full_codes


@pytest.mark.parametrize("case_id", H + R + P)
def test_nothing_is_decoded_after_an_h_r_or_p_error(case_id):
    """Decoding reads only files that passed H, R and P, so C, S and D report nothing on these cases."""
    report = _report(case_id)
    steps = dict(report.steps)
    assert steps["d_decode"] == [] and steps["c"] == [] and steps["s"] == []
    assert {f["layer"] for f in report.findings} <= {"H", "R", "P"}


@pytest.mark.parametrize("case_id", D + ["MC063"])
def test_a_decoding_failure_leaves_nothing_to_check(case_id):
    report = _report(case_id)
    steps = dict(report.steps)
    assert [f["layer"] for f in report.errors] == [f["layer"] for f in steps["d_decode"]]
    assert steps["c"] == [] and steps["s"] == []


def test_findings_point_at_the_fault():
    paths = {cid: [f["path"] for f in _report(cid).until_first_rejection() if f["severity"] == "error"]
             for cid in ("MC015", "MC019", "MC027", "MC031", "MC052", "MC054", "MC055", "MC058", "MC059", "MC060",
                         "MC062", "MC063")}
    assert paths == {
        "MC015": ["/incidences/39"], "MC019": ["/incidences/39/direction"], "MC027": ["/incidences/39/attrs/role"],
        "MC031": ["/incidences/42/attrs/role-position"], "MC052": ["/nodes/12/node"],
        "MC054": ["/incidences/40/attrs/khg-bid"], "MC055": ["/nodes/41/attrs/khg-external"],
        "MC058": ["/incidences/39/node"], "MC059": ["/incidences/39/edge"], "MC060": ["/nodes/32/node"],
        "MC062": ["/metadata/khg-schema-sha256"], "MC063": ["/incidences/39/direction"]}


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("rel", ["fixture/fixture.hif.json", "fixture/fixture.directed-slice.hif.json"])
def test_the_hif_bases_have_no_error(rel, engine):
    report = run(data.path(rel), schema=SCHEMA, doc_texts=data.path("fixture/fixture.doc-texts.json"), engine=engine)
    assert report.kind == "hif" and report.ok and report.skipped == []
    assert [name for name, _ in report.steps] == ["j", "v", "h", "r", "p", "d_decode", "c", "s", "d_container"]
    # only the designed warnings of §1.4, found on the decoded container: S024 (must_differ on f:loop-yyz, not in
    # the slice) and L008 (the same-day handover of f:king-13 and f:king-14, in both files; layer D, W5)
    codes = {f["code"] for f in report.findings}
    assert codes == ({"KHG-L008"} if "slice" in rel else {"KHG-S024", "KHG-L008"})  # S4: exact with W5 in
    assert ("KHG-S024" in codes) is ("slice" not in rel)
    assert all(f["severity"] == "warning" for f in report.findings)
