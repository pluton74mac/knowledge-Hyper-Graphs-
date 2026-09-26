"""G2: each malformed case rejected (DESIGN §1.2, §8.1, §8.2).

The harness runs all 180 cases of the packaged ``malformed-cases.json`` as the list states them:

- the input is the named base plus its RFC 6902 patch (queue and C4 patches address ``/lines/<n>``), or
  ``input_text`` for layer J, which runs as HIF as in the prototype harness;
- a ``schema_patch`` applies to ``fixture.relation-schema.json``, and the base's schema digest is re-stamped so that
  D009 does not fire;
- the context: the fixture schema (none for relation-schema cases), a case's own ``doc_text`` only (the bases get
  ``fixture.doc-texts.json``) and ``smoke-base.c1.json`` as the queue's base;
- the engine is jsonschema, with the full report.

**The rule.** A case passes when its first rejecting layer (the earliest code letter, in its kind's pipeline order,
among the error findings) is the listed layer and the listed code is among its error codes. The findings up to the
first rejecting step also have exactly the case's ``reported`` codes, which the prototype recorded.

**Harness self-checks.** Every patch applies; the input differs from its base; every ``expect_target`` resolves and
pins exactly the indexed paths of the patch; every unpatched base validates with no error finding.

**Coverage and engines.** Every active code of layers J to I is listed by a case, except D019 (S-PUT-006 covers it)
and Q013 (the linter's own check, ruling 23), and each is detected; no case yields a reserved, planned or
unregistered code. fastjsonschema rejects every case at the same step, with codes contained in jsonschema's: exactly
one error finding at a schema step (H, P, C, I), the same codes at a Python step, and one code or the same codes at M
and Q, which add Python checks to a schema. The fastjsonschema runs are checked to be fastjsonschema runs: they pass
again while jsonschema refuses to run.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from khg_contracts import data, jsonio
from khg_contracts.schema import load_schema
from khg_contracts.validate import ENGINES, layers, pipeline_letters, registry, run
from khg_contracts.validate.runner import Report

pytestmark = pytest.mark.gate

LIST = data.load_json("malformed-cases.json")
CASES: list[dict[str, Any]] = LIST["cases"]
BY_ID = {c["id"]: c for c in CASES}
REG = registry()
SCHEMA_DOC = data.load_json("fixture/fixture.relation-schema.json")
SCHEMA = load_schema(SCHEMA_DOC)
DOC_TEXTS = data.load_json("fixture/fixture.doc-texts.json")
QUEUE_BASE = {"p2-smoke-base": data.load_json("fixture/smoke-base.c1.json")}

#: The bases of the list, their packaged files and the kinds validate() runs them as.
BASES = {"fixture.c1.json": ("fixture/fixture.c1.json", "container"),
         "fixture.history.c1.json": ("fixture/fixture.history.c1.json", "container"),
         "fixture.hif.json": ("fixture/fixture.hif.json", "hif"),
         "fixture.directed-slice.hif.json": ("fixture/fixture.directed-slice.hif.json", "hif"),
         "fixture.relation-schema.json": ("fixture/fixture.relation-schema.json", "schema"),
         "smoke-queue.khg-queue.jsonl": ("fixture/smoke-queue.khg-queue.jsonl", "queue"),
         "c4-items.jsonl": ("fixture/c4-items.jsonl", "item")}
#: The case kinds of the list, mapped to validate()'s kinds.
KIND = {"json": "hif", "c1": "container", "hif": "hif", "relation-schema": "schema", "queue": "queue", "c4": "item"}
#: What an indexed patch path names in a base: the identity ``expect_target`` pins (the prototype's IDX_KEYS).
IDENTITY = {"records": lambda x: x.get("id") if x.get("version") is None else [x.get("id"), x.get("version")],
            "nodes": lambda x: x.get("node"), "edges": lambda x: x.get("edge"),
            "incidences": lambda x: [x.get("edge"), (x.get("attrs") or {}).get("khg-bid")],
            "relations": lambda x: x.get("id"), "entity_types": lambda x: x.get("id"),
            "lines": lambda x: [x.get("kind"), x.get("qid") or x.get("lid") or x.get("id")]}
#: §8.2's table: cases per layer.
PER_LAYER = {"J": 8, "V": 2, "H": 15, "R": 6, "P": 24, "D": 30, "C": 20, "S": 34, "M": 19, "Q": 17, "I": 5}
#: The steps that are Python checks only: both engines report the same findings there.
PYTHON_STEPS = {"j", "v", "r", "d_decode", "d_container", "s"}
#: The schema steps, where fastjsonschema, which stops at its first error, reports exactly one error finding on a
#: single-fault case (§8.1). M and Q run Python checks beside their schema, which may report one fault twice.
SCHEMA_STEPS = {"h", "p", "c", "i"}


# ------------------------------------------------------------------------------------------------ the harness


def _parts(pointer: str) -> list[str]:
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]


def apply_patch(doc: Any, patch: list[dict[str, Any]] | None) -> Any:
    """RFC 6902 ``add``, ``replace`` and ``remove`` on a copy; a target that does not exist raises (the "every
    patch applies" self-check)."""
    doc = copy.deepcopy(doc)
    for op in patch or []:
        *head, last = _parts(op["path"])
        parent = doc
        for p in head:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        value = copy.deepcopy(op.get("value"))
        if isinstance(parent, list):
            index = len(parent) if last == "-" else int(last)
            if op["op"] == "add":
                if not 0 <= index <= len(parent):
                    raise IndexError(op["path"])
                parent.insert(index, value)
            elif op["op"] == "replace":
                parent[index] = value
            else:
                assert op["op"] == "remove", op
                del parent[index]
        else:
            if op["op"] in ("replace", "remove") and last not in parent:
                raise KeyError(op["path"])
            if op["op"] == "remove":
                del parent[last]
            else:
                assert op["op"] in ("add", "replace"), op
                parent[last] = value
    return doc


def base(name: str) -> Any:
    """A base as the patches address it: queue and C4 files as ``{"lines": [...]}``."""
    rel, _ = BASES[name]
    return {"lines": data.load_jsonl(rel)} if rel.endswith(".jsonl") else data.load_json(rel)


def targets(base_doc: Any, patch: list[dict[str, Any]] | None) -> dict[str, Any]:
    """What each indexed path of a patch names in the base, as ``expect_target`` pins it."""
    out = {}
    for op in patch or []:
        parts = _parts(op["path"])
        if len(parts) >= 2 and parts[0] in IDENTITY and parts[1].isdigit() and isinstance(base_doc, dict):
            items = base_doc.get(parts[0])
            if isinstance(items, list) and int(parts[1]) < len(items):
                out[f"/{parts[0]}/{parts[1]}"] = IDENTITY[parts[0]](items[int(parts[1])])
    return out


def inputs(case: dict[str, Any]) -> tuple[Any, Any, dict[str, str]]:
    """``(input, schema, doc_texts)`` of a case, as §8.2 states the harness."""
    if case["kind"] == "json":
        return case["input_text"].encode("utf-8"), SCHEMA, {}
    doc = apply_patch(base(case["base"]), case.get("patch"))
    schema: Any = SCHEMA
    if case.get("schema_patch"):
        schema = apply_patch(SCHEMA_DOC, case["schema_patch"])
        digest = jsonio.digest("khg-schema/1", schema)
        if case["kind"] == "c1":
            doc["header"]["schema"]["sha256"] = digest
        elif case["kind"] == "hif":
            doc["metadata"]["khg-schema-sha256"] = digest
    if KIND[case["kind"]] == "schema":
        schema = None
    obj = doc["lines"] if case["kind"] in ("queue", "c4") else doc
    return obj, schema, dict(case.get("doc_text") or {})


_REPORTS: dict[tuple[str, str, str], Report] = {}


def report(case_id: str, engine: str = "jsonschema", stop: str = "all") -> Report:
    """The validator's report on a case (cached per case, engine and stop rule)."""
    key = (case_id, engine, stop)
    if key not in _REPORTS:
        case = BY_ID[case_id]
        obj, schema, texts = inputs(case)
        _REPORTS[key] = run(obj, kind=KIND[case["kind"]], schema=schema, doc_texts=texts, bases=QUEUE_BASE,
                            engine=engine, stop=stop)
    return _REPORTS[key]


def error_codes(findings: list[dict[str, Any]]) -> list[str]:
    return sorted({f["code"] for f in findings if f["severity"] == "error"})


def passes(case: dict[str, Any], rep: Report) -> bool:
    """The G2 rule (§8.2)."""
    return rep.first_layer == case["layer"] and case["code"] in error_codes(rep.findings)


IDS = [c["id"] for c in CASES]
PATCHED = [c["id"] for c in CASES if c.get("base")]


# ------------------------------------------------------------------------------------------------ the list


def test_the_list_holds_180_cases_in_the_layers_of_section_8_2():
    assert LIST["format"] == "khg-malformed-cases/1.0.0" and LIST["count"] == len(CASES) == 180
    assert IDS == [f"MC{i:03d}" for i in range(1, 181)]
    counts: dict[str, int] = {}
    for c in CASES:
        counts[c["layer"]] = counts.get(c["layer"], 0) + 1
    assert counts == PER_LAYER
    assert sorted(LIST["bases"]) == sorted(BASES) == sorted({c["base"] for c in CASES if c.get("base")})
    assert all(("input_text" in c) == (c["kind"] == "json") == (c["layer"] == "J") for c in CASES)
    assert {c["id"] for c in CASES if c.get("schema_patch")} == {"MC115", "MC118"}


def test_the_pipelines_of_the_list_are_the_validators():
    """The list names each kind's pipeline; the validator runs exactly those letters, in that order."""
    for kind, letters in LIST["pipelines"].items():
        assert " ".join(pipeline_letters(kind)) == letters, kind
    assert set(LIST["pipelines"]) == set(KIND)


def test_every_layer_is_implemented():
    """G2 closes with W11a: no layer module is a stub any more."""
    assert [s.name for s in layers.LAYERS if not layers.implemented(s.name)] == []
    assert [s.name for s in layers.LAYERS if "TODO" in (layers.module(s.name).__doc__ or "")] == []


def test_the_rule_and_the_patches_are_not_vacuous():
    """The rule fails a wrong layer, a wrong code and an unpatched base; a patch that does not apply raises."""
    case = BY_ID["MC180"]
    assert passes(case, report("MC180"))
    assert not passes(dict(case, layer="Q"), report("MC180"))
    assert not passes(dict(case, code="KHG-I004"), report("MC180"))
    assert not passes(case, run(base("c4-items.jsonl")["lines"], kind="item", schema=SCHEMA))
    lines = base("c4-items.jsonl")
    with pytest.raises(KeyError):
        apply_patch(lines, [{"op": "replace", "path": "/lines/6/no_such_field", "value": 1}])
    with pytest.raises(IndexError):
        apply_patch(lines, [{"op": "add", "path": "/lines/99", "value": {}}])
    with pytest.raises(KeyError):
        apply_patch(lines, [{"op": "remove", "path": "/lines/6/no_such_field"}])
    assert apply_patch(lines, [{"op": "add", "path": "/lines/-", "value": {"kind": "x"}}])["lines"][-1] == {"kind": "x"}


# ------------------------------------------------------------------------------------------------ self-checks


@pytest.mark.parametrize("case_id", PATCHED)
def test_every_patch_applies_and_changes_the_input(case_id):
    case = BY_ID[case_id]
    before = base(case["base"])
    after = apply_patch(before, case.get("patch"))
    schema = apply_patch(SCHEMA_DOC, case.get("schema_patch"))
    assert after != before or schema != SCHEMA_DOC
    assert case.get("patch") or case.get("schema_patch")


@pytest.mark.parametrize("case_id", PATCHED)
def test_every_expect_target_resolves_and_pins_every_indexed_path(case_id):
    """``expect_target`` names what each indexed patch path points at in the base, so a regenerated base cannot
    shift a patch silently."""
    case = BY_ID[case_id]
    assert targets(base(case["base"]), case.get("patch")) == (case.get("expect_target") or {})


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("name", sorted(BASES))
def test_every_unpatched_base_validates_with_no_error(name, engine):
    doc = base(name)
    _, kind = BASES[name]
    rep = run(doc["lines"] if kind in ("queue", "item") else doc, kind=kind,
              schema=None if kind == "schema" else SCHEMA, doc_texts=DOC_TEXTS, bases=QUEUE_BASE, engine=engine)
    assert rep.errors == [] and rep.skipped == []
    assert all(f["code"] in REG and REG[f["code"]].active for f in rep.findings)
    # the only findings are the fixture's designed warnings (§1.4): S024 (f:loop-yyz) and L008 (the king handover)
    designed = {"fixture.c1.json": ["KHG-L008", "KHG-S024"], "fixture.hif.json": ["KHG-L008", "KHG-S024"],
                "fixture.directed-slice.hif.json": ["KHG-L008"]}
    assert sorted(f["code"] for f in rep.findings) == designed.get(name, [])


# ------------------------------------------------------------------------------------------------ the rule


@pytest.mark.parametrize("case_id", IDS)
def test_the_case_is_rejected_first_at_its_layer_with_its_code(case_id):
    case = BY_ID[case_id]
    rep = report(case_id)
    assert not rep.ok
    assert rep.first_layer == case["layer"], error_codes(rep.findings)
    assert case["code"] in error_codes(rep.findings)
    assert rep.skipped == []  # no layer failed on what an earlier layer rejected


@pytest.mark.parametrize("case_id", IDS)
def test_the_first_rejecting_step_reports_the_recorded_codes(case_id):
    """The findings up to the first rejecting step: the prototype's ``reported`` codes, and what a run that stops
    there (``stop="first"``) returns."""
    case = BY_ID[case_id]
    rep = report(case_id)
    assert error_codes(rep.until_first_rejection()) == sorted(case["reported"])
    first = report(case_id, stop="first")
    assert first.findings == rep.until_first_rejection()
    assert first.first_layer == case["layer"]


@pytest.mark.parametrize("case_id", IDS)
def test_single_fault_engine_containment(case_id):
    """fastjsonschema stops at its first error: at the same first rejecting step and layer, its codes are among
    jsonschema's. At a schema step it reports exactly one error finding (§8.1: "exactly one code at the first
    rejecting step"; jsonschema may report the fault twice), at a Python step both engines report the same codes,
    and at M and Q one code or the same codes."""
    full, fast = report(case_id), report(case_id, "fastjsonschema")
    assert fast.first_layer == full.first_layer == BY_ID[case_id]["layer"]
    assert fast.first_rejecting_step == full.first_rejecting_step
    fast_codes, full_codes = error_codes(fast.until_first_rejection()), error_codes(full.until_first_rejection())
    assert set(fast_codes) <= set(full_codes)
    assert len(fast_codes) == 1 or fast_codes == full_codes
    if full.first_rejecting_step in PYTHON_STEPS:
        assert fast_codes == full_codes
    if full.first_rejecting_step in SCHEMA_STEPS:
        assert len([f for f in fast.until_first_rejection() if f["severity"] == "error"]) == 1


def test_the_fastjsonschema_runs_do_not_run_jsonschema(monkeypatch):
    """The containment above holds as well when a layer quietly runs jsonschema for fastjsonschema (a layer that
    stopped passing ``engine`` on): its codes are then trivially contained. So every case runs again with
    fastjsonschema while jsonschema refuses to compile a packaged schema or to run the relation-schema meta-schema,
    and each report must equal the fastjsonschema report above."""
    from khg_contracts.schema import checks as schema_checks
    from khg_contracts.validate import engines

    prepared = {}
    for case_id in IDS:  # outside the guard: a schema argument is loaded, and checked, with jsonschema
        obj, schema, texts = inputs(BY_ID[case_id])
        prepared[case_id] = (obj, load_schema(schema) if isinstance(schema, dict) else schema, texts)
    expected = {case_id: report(case_id, "fastjsonschema") for case_id in IDS}
    ran: list[str] = []

    def refused(what: str) -> None:
        ran.append(what)
        raise RuntimeError(f"jsonschema ran during a fastjsonschema run ({what})")

    meta = schema_checks._meta_runner
    monkeypatch.setattr(engines, "_jsonschema", lambda root_uri: refused(root_uri))
    monkeypatch.setattr(schema_checks, "_meta_runner",
                        lambda engine: refused("the meta-schema") if engine == "jsonschema" else meta(engine))
    engines.compile_schema.cache_clear()  # the runners compiled so far include jsonschema's
    try:
        for case_id in IDS:
            obj, schema, texts = prepared[case_id]
            rep = run(obj, kind=KIND[BY_ID[case_id]["kind"]], schema=schema, doc_texts=texts, bases=QUEUE_BASE,
                      engine="fastjsonschema")
            assert (rep.findings, rep.skipped) == (expected[case_id].findings, []), case_id
    finally:
        engines.compile_schema.cache_clear()
    assert ran == []


# ------------------------------------------------------------------------------------------------ coverage


CHECKED = [c.code for c in REG.codes(status="active") if c.layer not in ("L", "F")]


def test_every_active_code_of_layers_j_to_i_is_listed_except_d019():
    listed = {c["code"] for c in CASES}
    assert len(CHECKED) == 124
    # D019: a store scenario; Q013: the linter's own check (ruling 23)
    assert set(CHECKED) - listed == set(LIST["coverage_exceptions"]) == {"KHG-D019", "KHG-Q013"}
    assert listed <= set(CHECKED)
    assert all(c["code"][4] == c["layer"] and REG[c["code"]].layer == c["layer"] for c in CASES)
    assert set(REG.active()) - set(CHECKED) == {"KHG-L008", "KHG-F006", "KHG-F015", "KHG-F016", "KHG-F017"}


@pytest.mark.parametrize("code", [c for c in CHECKED if c not in LIST["coverage_exceptions"]])
def test_every_listed_code_is_detected(code):
    ids = [c["id"] for c in CASES if c["code"] == code]
    assert ids and all(passes(BY_ID[i], report(i)) for i in ids), code


@pytest.mark.parametrize("case_id", IDS)
def test_no_case_yields_a_reserved_planned_or_unregistered_code(case_id):
    planned = {p["code"] for p in data.load_json("error-codes.json")["planned"]}
    for engine in ENGINES:
        for f in report(case_id, engine).findings:
            assert f["code"] in REG and REG[f["code"]].active and f["code"] not in planned, (engine, f)
            assert f["layer"] == REG[f["code"]].layer
            nested = f.get("nested")
            if nested is not None:  # I003 carries the C, S or D finding it wraps (§8.1)
                assert f["code"] == "KHG-I003" and nested["code"] in REG and REG[nested["code"]].active
