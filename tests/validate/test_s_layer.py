"""W4: layer S beyond the case list: severities, the other constraint types, entity and fact resolution, spans,
NFC, the schema a run uses, queue payloads, and the decoded container of a HIF run (DESIGN §2, §3, §7, §8.1)."""
from __future__ import annotations

import copy
import unicodedata

import pytest

from khg_contracts import data
from khg_contracts.schema import Schema, load_schema
from khg_contracts.validate import layers, run, validate, validate_record
from khg_contracts.validate.layers.s import latest_records, nfc_findings, record_findings

SCHEMA_DOC = data.load_json("fixture/fixture.relation-schema.json")
SCHEMA = load_schema(SCHEMA_DOC)
FIXTURE = data.load_json("fixture/fixture.c1.json")
ENTITIES = {r["id"]: r for r in FIXTURE["records"] if r["kind"] == "entity"}
FACTS = {r["id"]: r for r in FIXTURE["records"] if r["kind"] == "hyperedge"}
TEXTS = {k: v["text"] for k, v in data.load_json("fixture/fixture.doc-texts.json")["texts"].items()}


def fact(rid):
    return copy.deepcopy(FACTS[rid])


def check(record, schema=SCHEMA, **kw):
    kw.setdefault("entities", ENTITIES)
    kw.setdefault("facts", FACTS)
    return [(f["code"], f["severity"], f["path"]) for f in record_findings(record, schema, **kw)]


def binding(record, bid):
    return next(b for b in record["bindings"] if b["bid"] == bid)


def drop(record, role):
    """The record without the bindings of ``role``, and without their bids in the evidence's ``supports``."""
    gone = {b["bid"] for b in record["bindings"] if b["role"] == role}
    record["bindings"] = [b for b in record["bindings"] if b["role"] != role]
    for e in record.get("evidence", []):
        if "supports" in e:
            e["supports"] = [x for x in e["supports"] if x not in gone]
    return record


def with_constraints(relation, constraints):
    doc = copy.deepcopy(SCHEMA_DOC)
    next(r for r in doc["relations"] if r["id"] == relation)["constraints"] = constraints
    return Schema(doc)


def test_every_fixture_hyperedge_passes_with_its_texts():
    for rid, record in FACTS.items():
        found = check(record, doc_texts=TEXTS)
        assert found == ([("KHG-S024", "warning", "")] if rid == "f:loop-yyz" else []), rid


# ------------------------------------------------------------------------------------------------ severities


def test_s003_is_an_error_on_facts_and_a_warning_on_candidates():
    king = drop(fact("f:king-14"), "position")
    assert check(king) == [("KHG-S003", "error", "")]
    assert check(dict(king, status="candidate")) == [("KHG-S003", "warning", "")]
    assert check(king, candidate=True) == [("KHG-S003", "warning", "")]


def test_a_goal_omitting_a_role_is_s018_and_leaving_it_unbound_is_fine():
    goal = fact("g:who-1774")
    assert check(goal) == []
    assert check(drop(goal, "position")) == [("KHG-S018", "error", "")]


@pytest.mark.parametrize(("constraint", "roles", "bad"), [
    ("requires", ["context", "regulator"], False),
    ("requires", ["regulator", "context"], False),
    ("excludes", ["regulator", "context"], True),
    ("at_least_one_of", ["context"], False),
    ("must_agree", ["regulator", "target"], False),
    ("must_differ", ["regulator", "target"], True),
])
def test_the_five_constraint_types_on_f_reg_1(constraint, roles, bad):
    """f:reg-1 binds regulator TP53, target TP53 and context HeLa."""
    for severity in ("error", "warning"):
        schema = with_constraints("regulates", [{"type": constraint, "roles": roles, "severity": severity}])
        assert check(fact("f:reg-1"), schema) == ([("KHG-S024", severity, "")] if bad else [])


def test_requires_and_at_least_one_of_fail_when_the_roles_are_unbound():
    reg = drop(fact("f:reg-1"), "context")
    for con in ({"type": "requires", "roles": ["regulator", "context"], "severity": "error"},
                {"type": "at_least_one_of", "roles": ["context"], "severity": "error"}):
        assert check(reg, with_constraints("regulates", [con])) == [("KHG-S024", "error", "")]
    agree = {"type": "must_agree", "roles": ["regulator", "target"], "severity": "error"}
    binding(reg, "b3")["value"] = {"entity": "ex:HeLa"}
    assert ("KHG-S024", "error", "") in check(reg, with_constraints("regulates", [agree]))


# ------------------------------------------------------------------------------------------------ values


def test_fillers_accept_subtypes_and_resolved_entities_only():
    claim = fact("f:claim-1")  # claimant takes Agent; Ødegård is a Person, a subtype of Agent
    assert check(claim) == []
    binding(claim, "b1")["value"] = {"entity": "ex:Paris"}  # a Place
    assert check(claim) == [("KHG-S005", "error", "/bindings/1")]
    binding(claim, "b1")["value"] = {"entity": "ex:Unknown"}  # unresolved: D002 is layer D's
    assert check(claim) == []
    assert check(fact("f:claim-1"), entities={}) == []


def test_a_nested_fact_of_the_wrong_relation_is_s005():
    claim = fact("f:claim-1")
    binding(claim, "b2")["value"] = {"fact": "f:king-14"}
    assert check(claim) == [("KHG-S005", "error", "/bindings/0")]
    assert check(claim, facts={}) == []  # an unresolved fact reference is layer D's


def test_the_built_in_end_cause_takes_any_entity_or_a_string():
    king = fact("f:king-14")
    king["bindings"].append({"bid": "b6", "role": "khg:end_cause", "value": {"entity": "ex:Paris"}})
    assert check(king) == []
    king["bindings"][-1]["value"] = {"literal": {"datatype": "string", "value": "death"}}
    assert check(king) == []
    king["bindings"][-1]["value"] = {"literal": {"datatype": "boolean", "value": True}}
    assert check(king) == [("KHG-S005", "error", "/bindings/5")]


def test_repeated_somevalue_missing_positions_and_novalue_alone():
    married = fact("f:married-curie")
    for b in married["bindings"]:
        if b["role"] == "spouse":
            b["value"] = {"special": "somevalue"}
    assert check(married) == [("KHG-S014", "error", "")]
    route = fact("f:route-1")
    del binding(route, "b3")["position"]
    assert check(route) == [("KHG-S015", "error", "")]
    assert check(fact("f:cat-7")) == []  # novalue alone


def test_a_direction_where_the_usage_declares_one_is_s016_even_when_equal():
    reg = fact("f:reg-1")
    binding(reg, "b2")["direction"] = "tail"  # regulator declares tail
    assert check(reg) == [("KHG-S016", "error", "/bindings/1/direction")]
    loop = fact("f:loop-yyz")  # flies_between declares no direction
    binding(loop, "b1")["direction"] = "tail"
    assert [c for c, _, _ in check(loop)] == ["KHG-S024"]


def test_precision_min_and_units_at_their_bounds():
    pop = fact("f:pop-łódź-2019")
    assert check(pop) == []  # precision 9 is precision_min
    binding(pop, "b3")["value"]["literal"] = {"datatype": "time", "time": "+2019-06-00T00:00:00Z", "precision": 10,
                                              "calendar": "gregorian"}
    assert check(pop) == []


def test_distinct_variables_and_the_time_bounds():
    goal = fact("g:who-1774")
    goal["bindings"].append({"bid": "b4", "role": "replaces", "value": {"unbound": {"var": "whom"}}})
    assert check(goal) == []
    king = fact("f:king-14")
    binding(king, "b4")["value"] = {"special": "somevalue"}  # ended at an unknown time after the start
    assert check(king) == []
    binding(king, "b3")["value"] = {"special": "novalue"}  # held since forever
    binding(king, "b4")["value"] = {"literal": {"datatype": "time", "time": "+1600-00-00T00:00:00Z",
                                                "precision": 9}}
    assert check(king) == []
    binding(king, "b3")["value"] = {"literal": {"datatype": "time", "time": "+1600-00-00T00:00:00Z",
                                                "precision": 9}}
    assert check(king) == []  # start and end in one year: the possible validity [1600, 1601) is not empty
    binding(king, "b3")["value"]["literal"]["time"] = "+1601-00-00T00:00:00Z"
    assert check(king) == [("KHG-S009", "error", "")]  # the start window lies after the end window


# ------------------------------------------------------------------------------------------------ evidence


def test_confidence_on_the_probability_scale_and_a_declared_one():
    co = fact("f:coadmin-1")
    assert check(co) == []
    co["confidence"]["value"] = 1.5
    co["evidence"][0]["confidence"]["value"] = 10
    assert check(co) == [("KHG-S010", "error", "/confidence")]


def test_negated_evidence_does_not_support_and_lifecycle_records_need_none():
    reg = fact("f:reg-1")
    reg["evidence"][0]["epistemics"] = {"negated": True}
    assert check(reg) == [("KHG-S011", "error", "")]
    sup = fact("m:sup-1")
    del sup["evidence"]
    assert check(sup) == []
    assert check(dict(fact("f:reg-1"), status="quoted", evidence=[])) == []


def test_s026_judges_a_reason_that_is_present():
    sup = fact("m:sup-1")
    del sup["reason"]
    assert check(sup) == []  # a missing reason is layer C's C012
    sup["reason"] = "withdrawn"  # a khg:retracts reason
    assert check(sup) == [("KHG-S026", "error", "/reason")]


def test_spans_are_checked_against_the_text_only():
    route = fact("f:route-1")
    assert check(route, doc_texts=TEXTS) == []
    route["evidence"][0]["selectors"][1] = {"type": "position", "start": 30, "end": 58}  # UTF-16 offsets
    assert check(route, doc_texts=TEXTS) == [("KHG-S021", "error", "/evidence/0")]
    assert check(route) == []  # no text
    route["evidence"][0]["selectors"][1] = {"type": "position", "start": 60, "end": 999}
    assert check(route, doc_texts=TEXTS) == [("KHG-S021", "error", "/evidence/0")]
    route["evidence"][0]["selectors"] = route["evidence"][0]["selectors"][:1]  # a quote alone
    assert check(route, doc_texts=TEXTS) == []


# ------------------------------------------------------------------------------------------------ NFC


def test_nfc_findings_cover_every_string_and_key():
    nfd = unicodedata.normalize("NFD", "Łódź")
    assert nfd != "Łódź"
    record = {"kind": "entity", "id": "ex:x", "types": ["Place"], "aliases": ["ok", nfd],
              "extensions": {"ex:" + nfd: {"note": [nfd]}}}
    assert [f["path"] for f in nfc_findings(record, "/records/2")] == [
        "/records/2/aliases/1", f"/records/2/extensions/ex:{nfd}", f"/records/2/extensions/ex:{nfd}/note/0"]
    assert nfc_findings(FIXTURE) == []


def test_a_container_run_reports_s020_on_the_header_too():
    doc = copy.deepcopy(FIXTURE)
    doc["header"]["document_id"] = unicodedata.normalize("NFD", "p2-gate-fixture-é")
    assert [(f["code"], f["path"]) for f in validate(doc, schema=SCHEMA)["findings"] if f["severity"] == "error"] \
        == [("KHG-S020", "/header/document_id")]


# ------------------------------------------------------------------------------------------------ the run's schema


def test_without_a_schema_the_s_step_reports_d009_once():
    report = run(FIXTURE, kind="container")
    assert [(f["code"], f["path"]) for f in report.errors] == [("KHG-D009", "/header/schema")]
    assert [name for name, found in report.steps if found] == ["s"]
    assert [(f["code"], f["path"]) for f in validate_record(fact("f:king-14"))["findings"]] == [("KHG-D009", "")]


def test_a_container_uses_the_schema_it_embeds():
    doc = copy.deepcopy(FIXTURE)
    doc["records"].insert(0, copy.deepcopy(SCHEMA_DOC))
    assert run(doc, kind="container").findings[0]["code"] == "KHG-S024"
    assert [f["code"] for f in run(doc, kind="container").errors] == []
    doc["records"][0]["version"] = "1.0"  # the embedded schema fails M004: reported at its path, S cannot run
    report = run(doc, kind="container")
    assert [(f["code"], f["path"]) for f in report.errors] == [("KHG-M004", "/records/0/version")]
    assert report.first_layer == "M"


def test_the_callers_schema_wins_over_an_embedded_one():
    doc = copy.deepcopy(FIXTURE)
    embedded = copy.deepcopy(SCHEMA_DOC)
    embedded["relations"] = [r for r in embedded["relations"] if r["id"] != "regulates"]
    doc["records"].insert(0, embedded)
    # W5: the embedded schema no longer matches the header's pin either (D009 from layer D)
    assert [f["code"] for f in run(doc, kind="container").errors] == ["KHG-S001", "KHG-D009"]
    assert run(doc, kind="container", schema=SCHEMA).ok


def test_latest_records_picks_the_highest_version():
    history = data.load_json("fixture/fixture.history.c1.json")
    latest = latest_records(history["records"])
    assert latest["f:king-13"]["version"] == 2 and latest["f:reg-1"]["status"] == "retracted"
    assert sorted(latest) == sorted({r["id"] for r in history["records"]})


# ------------------------------------------------------------------------------------------------ queue payloads


def test_queue_payloads_are_candidates_resolved_through_item_entities_then_the_base():
    lines = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    base = data.load_json("fixture/smoke-base.c1.json")
    item = next(n for n, x in enumerate(lines) if x["kind"] == "queue-item")
    drop(lines[item]["payload"], "position")
    report = run(lines, kind="queue", schema=SCHEMA, bases=[base])
    assert report.ok and [(f["code"], f["severity"]) for f in report.findings] == [("KHG-S003", "warning")]
    assert report.findings[0]["path"] == f"/lines/{item}/payload"
    lines[item]["entities"] = [{"kind": "entity", "id": "ex:LouisXIII", "types": ["Place"], "label": "L"}]
    report = run(lines, kind="queue", schema=SCHEMA, bases=[base])
    assert [(f["code"], f["path"]) for f in report.errors] == [("KHG-S005", f"/lines/{item}/payload/bindings/2")]
    base_bad = copy.deepcopy(base)
    next(r for r in base_bad["records"] if r["id"] == "ex:LouisXIV")["types"] = ["Place"]
    lines[item]["entities"] = []
    assert run(lines, kind="queue", schema=SCHEMA, bases=[base]).ok
    assert run(lines, kind="queue", schema=SCHEMA, bases=[base_bad]).ok  # its sha256 is not the header's: unused


def test_queue_payloads_go_through_layer_c_as_hyperedges():
    lines = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    item = next(n for n, x in enumerate(lines) if x["kind"] == "queue-item")
    lines[item]["payload"]["rank"] = "top"
    report = run(lines, kind="queue", schema=SCHEMA)
    assert [(f["code"], f["path"]) for f in report.errors] == [("KHG-C002", f"/lines/{item}/payload/rank")]
    assert run(lines, kind="queue").errors[0]["code"] == "KHG-C002"
    assert ("KHG-D009", "/lines/0/schema") in [(f["code"], f["path"]) for f in run(lines, kind="queue").errors]


# ------------------------------------------------------------------------------------------------ HIF runs


def test_c_and_s_check_the_container_that_decoding_leaves(monkeypatch):
    """The contract with W6: ``d_decode`` sets ``ctx.state["c1"]``; C, S and ``d_container`` check it."""
    decoded = copy.deepcopy(FIXTURE)
    decoded["records"][35]["status"] = "believed"
    decoded["records"][30]["bindings"][3]["role"] = "tissue"  # f:king-14 b5 (replaces, optional)

    def decode(ctx):
        ctx.state["c1"] = decoded
        return []

    monkeypatch.setattr(layers.module("d_decode"), "run", decode)
    report = run(data.load_json("fixture/fixture.hif.json"), kind="hif", schema=SCHEMA)
    assert [(name, [f["code"] for f in found if f["severity"] == "error"]) for name, found in report.steps] == [
        ("j", []), ("v", []), ("h", []), ("r", []), ("p", []), ("d_decode", []), ("c", ["KHG-C002"]),
        ("s", ["KHG-S002"]), ("d_container", [])]
    assert report.first_layer == "C"


def test_a_hif_run_uses_the_inlined_schema_document(monkeypatch):
    hif = data.load_json("fixture/fixture.hif.json")
    hif["metadata"]["khg-schema-document"] = copy.deepcopy(SCHEMA_DOC)

    def decode(ctx):
        ctx.state["c1"] = copy.deepcopy(FIXTURE)
        return []

    monkeypatch.setattr(layers.module("d_decode"), "run", decode)
    report = run(hif, kind="hif")
    assert report.ok and [f["code"] for f in report.findings] == ["KHG-S024", "KHG-L008"]  # the designed warnings
    del hif["metadata"]["khg-schema-document"]
    assert [(f["code"], f["path"]) for f in run(hif, kind="hif").errors] == [("KHG-D009", "/metadata/khg-schema")]
