"""W4: code coverage over the registry (DESIGN §8.1, §8.2).

- Every active code of layers J to I is listed by a case, except the coverage exception D019 (a store scenario).
- Every such code is detected: at least one of its cases passes the G2 rule (its first rejecting layer is the listed
  layer and its code is among the error codes). Reserved codes are skipped (never emitted), and so are the lint and
  migration layers L and F, which the store receipts and the migration test cover.
- A code whose cases all depend on a layer module that is still a stub is a strict xfail naming the step that owns
  the module; it turns into a plain test when the owner sets ``IMPLEMENTED = True``.
- No case or base yields a code that is reserved, planned or unregistered, and the layers of W4 never reject a
  case before the layer that the case is for.
"""
from __future__ import annotations

import pytest

from khg_contracts import data
from khg_contracts.validate import layers, pipeline_letters, registry, run

REG = registry()
LIST = data.load_json("malformed-cases.json")
CASES = LIST["cases"]
EXCEPTIONS = LIST["coverage_exceptions"]
KIND = {"json": "hif", "c1": "container", "hif": "hif", "relation-schema": "schema", "queue": "queue", "c4": "item"}
CHECKED = [c.code for c in REG.codes(status="active") if c.layer not in ("L", "F")]


def module_for(case):
    """The layer module a case depends on (the conftest's ``Malformed.module_for``)."""
    kind = KIND[case["kind"]]
    if kind == "hif" and case["layer"] in ("C", "S", "D"):
        return "d_decode"
    return next(n for n in layers.PIPELINES[kind] if layers.spec(n).letter == case["layer"])


def _params():
    out = []
    for code in CHECKED:
        cases = [c for c in CASES if c["code"] == code]
        marks = []
        if code in EXCEPTIONS:
            marks = [pytest.mark.skip(reason=f"{code} is a coverage exception: {EXCEPTIONS[code]}")]
        else:
            modules = sorted({module_for(c) for c in cases})
            if modules and not any(layers.implemented(m) for m in modules):
                owners = " and ".join(f"{m} ({layers.spec(m).owner})" for m in modules)
                what = ("layer module {} is a stub until its owner step fills it" if len(modules) == 1 else
                        "layer modules {} are stubs until their owner steps fill them")
                marks = [pytest.mark.xfail(strict=True, reason=f"{code}: {what.format(owners)}")]
        out.append(pytest.param(code, [c["id"] for c in cases], marks=marks, id=code))
    return out


def _passes(case, report):
    return report.first_layer == case["layer"] and case["code"] in {f["code"] for f in report.errors}


def test_there_are_123_active_codes_in_layers_j_to_i():
    assert len(CHECKED) == 123 and not set(CHECKED) & set(REG.reserved())
    assert set(REG.active()) - set(CHECKED) == {"KHG-L008", "KHG-F006", "KHG-F015", "KHG-F016", "KHG-F017"}


def test_every_active_code_of_layers_j_to_i_is_listed_by_a_case():
    listed = {c["code"] for c in CASES}
    assert set(CHECKED) - listed == set(EXCEPTIONS) == {"KHG-D019"}
    assert listed <= set(CHECKED)


@pytest.mark.parametrize(("code", "case_ids"), _params())
def test_every_active_code_is_detected(code, case_ids, malformed):
    assert case_ids, f"no case lists {code}"
    passing = [cid for cid in case_ids if _passes(malformed.by_id[cid], malformed.report(cid))]
    assert passing, f"{code}: none of {case_ids} is rejected first at its layer with its code"


def test_the_stub_modules_name_their_owner_steps():
    stubs = {s.name: s.owner for s in layers.LAYERS if not layers.implemented(s.name)}
    assert set(stubs) <= {"h", "r", "p", "d_decode", "d_container", "q", "i"}
    assert all(stubs[m] == {"h": "W6", "r": "W6", "p": "W6", "d_decode": "W6", "d_container": "W5", "q": "W9",
                            "i": "W11a"}[m] for m in stubs)
    for name in stubs:
        assert f"TODO({stubs[name]})" in (layers.module(name).__doc__ or "")


@pytest.mark.parametrize("case_id", [c["id"] for c in CASES])
def test_no_case_yields_a_reserved_planned_or_unregistered_code(case_id, malformed):
    for engine in ("jsonschema", "fastjsonschema"):
        report = malformed.report(case_id, engine)
        for f in report.findings:
            assert f["code"] in REG and REG[f["code"]].active, (case_id, f)
            assert f["layer"] == REG[f["code"]].layer
        assert report.skipped == []


@pytest.mark.parametrize("case_id", [c["id"] for c in CASES])
def test_no_layer_rejects_a_case_before_its_own_layer(case_id, malformed):
    """The layers built so far never report an error of a letter that precedes the case's layer in its kind's
    pipeline, so a case passes once the layer it is for is filled."""
    case = malformed.by_id[case_id]
    order = pipeline_letters(KIND[case["kind"]])
    earlier = set(order[:order.index(case["layer"])])
    report = malformed.report(case_id)
    assert [f for f in report.errors if f["layer"] in earlier] == []


BASE_KINDS = {"fixture.c1.json": "container", "fixture.history.c1.json": "container", "fixture.hif.json": "hif",
              "fixture.directed-slice.hif.json": "hif", "fixture.relation-schema.json": "schema",
              "smoke-queue.khg-queue.jsonl": "queue", "c4-items.jsonl": "item"}


@pytest.mark.parametrize("engine", ("jsonschema", "fastjsonschema"))
def test_no_base_yields_an_error_or_an_unregistered_code(engine, malformed):
    """Every unpatched base of the list validates with no error finding (a harness self-check of §8.2)."""
    assert sorted(BASE_KINDS) == sorted(LIST["bases"])
    for name, kind in BASE_KINDS.items():
        base = malformed.base(name)
        report = run(base["lines"] if kind in ("queue", "item") else base, kind=kind,
                     schema=None if kind == "schema" else malformed.loaded_schema, doc_texts=malformed.doc_texts,
                     bases=[malformed.smoke_base], engine=engine)
        assert report.errors == [] and report.skipped == [], name
        assert all(f["code"] in REG and REG[f["code"]].active for f in report.findings)
