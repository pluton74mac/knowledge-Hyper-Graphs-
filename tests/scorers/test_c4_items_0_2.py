"""P2 ruling 20: the C4 draft ``khg-c4-items`` 0.2.0 (DESIGN §9.6), from P3a's proposal (``notes/c4-change-proposal.md``
part A, P3a DESIGN §11) and P9's candidate table (P9 DESIGN §3.1, §8 items 1-2, D6).

- **Compatible.** A 0.1.0 file stays valid (the packaged ``c4-items.jsonl`` is the witness); the reader takes 0.0.x to
  0.2.x and reads them all by the 0.2.0 schema (stamps tell older readers what they cannot read, as in ruling 19).
- **Header:** ``corpus {id, version, tier?}``; ``record_format`` is any ``khg-record`` stamp the reader takes (V001).
- **Split manifests:** the split value ``inference``; ``scheme``, ``seed``, ``container {document_id, sha256}``,
  ``probe {fact id: [leak kinds]}`` (probe facts are test facts: I002) and ``lite`` (ids).
- **Extraction documents:** ``doc_kind`` (``wiki``, ``rendered``), ``source {url, revision?, licence?,
  attribution?}``, ``gold_scope`` (declared relations: I003 with S001 nested) and ``mentions``, the leak-free
  candidate table: ``[{entity: <C1 entity>, source: link | subject | match | distractor, spans?: [[start, end]],
  description?}]``; spans in code points of the NFC text, one entry per entity (I002).
- **Retrieval questions:** ``answer_mode`` (``single``, ``set``, ``count``; a count is one quantity of unit ``"1"``),
  read per item before ``RetrievalConfig.answer_mode``; ``provenance`` stays open (P10's extras).
- **Completion queries:** ``manifest``, the id of the split manifest a query belongs to.
"""
from __future__ import annotations

import copy
from typing import Any, Callable

import pytest

import khg_contracts
from khg_contracts import data, record
from khg_contracts.scorers import completion, retrieval
from khg_contracts.validate import ENGINES, engines, run, validate_item

OLD = data.load_jsonl("fixture/c4-items.jsonl")
NEW_FILE = "fixture/c4-items-0.2.0.jsonl"
FIXTURE = data.load_json("fixture/fixture.c1.json")
DOC_TEXTS = data.load_json("fixture/fixture.doc-texts.json")
SCHEMA = data.load_json("fixture/fixture.relation-schema.json")


def new_lines() -> list[dict[str, Any]]:
    return data.load_jsonl(NEW_FILE)


def at(lines: list[dict[str, Any]], key: str) -> int:
    """The line of the item whose id, qid, trace_id or kind is ``key``."""
    return next(n for n, x in enumerate(lines) if key in (x.get("id"), x.get("qid"), x.get("trace_id"), x["kind"]))


def changed(change: Callable[[list[dict[str, Any]]], Any]) -> list[dict[str, Any]]:
    out = copy.deepcopy(new_lines())
    change(out)
    return out


def found(items: Any, engine: str = "jsonschema") -> list[tuple[str, str, str | None]]:
    """``(code, path, nested code)`` of every finding of a layer-I run with the fixture schema."""
    rep = run(items, kind="item", schema=SCHEMA, engine=engine)
    assert rep.skipped == []
    return [(f["code"], f["path"], (f.get("nested") or {}).get("code")) for f in rep.findings]


# ------------------------------------------------------------------------------------------------ versions


def test_the_draft_is_0_2_0():
    assert khg_contracts.CONTRACTS["khg-c4-items"] == "0.2.0"
    assert engines.C4_SCHEMA_ID == "tag:khg-contracts,2026:schema/khg-c4-items/0.2.0"
    files = data.iter_files()
    assert "schemas/khg-c4-items-0.2.0.schema.json" in files and "schemas/khg-c4-items-0.1.0.schema.json" not in files
    assert data.load_json("schemas/khg-c4-items-0.2.0.schema.json")["$id"] == engines.C4_SCHEMA_ID


@pytest.mark.parametrize("engine", ENGINES)
def test_a_0_1_0_file_stays_valid(engine):
    assert OLD[0]["format"] == "khg-c4-items/0.1.0"
    assert validate_item(OLD, schema=SCHEMA, doc_texts=DOC_TEXTS, engine=engine) == {"ok": True, "findings": []}


@pytest.mark.parametrize("engine", ENGINES)
def test_the_0_2_0_example_is_valid(engine):
    lines = new_lines()
    assert lines[0]["format"] == "khg-c4-items/0.2.0"
    assert validate_item(data.path(NEW_FILE), schema=SCHEMA, doc_texts=DOC_TEXTS, engine=engine) == \
        {"ok": True, "findings": []}


def test_the_example_shows_every_new_field():
    lines = new_lines()
    head = lines[0]
    assert head["corpus"] == {"id": "p2-gate-fixture", "version": "1.0.0", "tier": "core"}
    doc = lines[at(lines, "c4-extraction-doc")]
    assert doc["doc_kind"] == "rendered" and doc["gold_scope"] == ["position_held"]
    assert {m["source"] for m in doc["mentions"]} == {"match", "distractor"}
    modes = {q.get("answer_mode") for q in lines if q["kind"] == "c4-retrieval-question"}
    assert modes == {"single", "set", "count"}
    assert all({"template", "pair_hops", "nary_dependent", "anchor_degree"} <= set(q["provenance"])
               for q in lines if q["kind"] == "c4-retrieval-question")
    query = lines[at(lines, "c4-completion-query")]
    manifests = {m["id"]: m for m in lines if m["kind"] == "c4-split-manifest"}
    assert query["manifest"] in manifests
    assert {m["scheme"] for m in manifests.values()} == {"semi_inductive", "leak_probe"}
    assert any("inference" in m["splits"].values() for m in manifests.values())
    probe = next(m for m in manifests.values() if m["scheme"] == "leak_probe")
    assert probe["probe"] == {"f:loop-yyz": ["same_pair_other_relation"]} and probe["lite"]
    assert all(m["container"] == {"document_id": "p2-gate-fixture", "sha256": record.container_sha256(FIXTURE)}
               for m in manifests.values())


@pytest.mark.parametrize(("stamp", "ok"), [("khg-c4-items/0.2.0", True), ("khg-c4-items/0.2.7", True),
                                           ("khg-c4-items/0.1.0", True), ("khg-c4-items/0.3.0", False),
                                           ("khg-c4-items/1.0.0", False)])
def test_the_version_gate_takes_0_0_to_0_2(stamp, ok):
    """Layer V only: a file stamped 0.1.x is replayed by the 0.1 memory rules (ruling 21), so the example's memory
    questions then disagree with their replay (``tests/scorers/test_memory_1_1.py``)."""
    lines = changed(lambda x: x[0].update(format=stamp))
    want = [] if ok else [("KHG-V001", "/lines/0/format", None)]
    assert [f for f in found(lines) if f[0].startswith("KHG-V")] == want
    assert ok or found(lines) == want  # a V finding stops the run


@pytest.mark.parametrize(("stamp", "ok"), [("khg-record/1.0.0", True), ("khg-record/1.0.4", True),
                                           ("khg-record/2.0.0", False), ("khg-record/1.9.0", False)])
def test_the_record_format_of_a_header_is_version_gated(stamp, ok):
    lines = changed(lambda x: x[0].update(record_format=stamp))
    want = [] if ok else [("KHG-V001", "/lines/0/record_format", None)]
    assert found(lines) == want


# ------------------------------------------------------------------------------------------------ header


@pytest.mark.parametrize(("change", "path"), [
    (lambda h: h["corpus"].pop("version"), "/lines/0/corpus"),
    (lambda h: h["corpus"].update(edition="x"), "/lines/0/corpus"),
    (lambda h: h["corpus"].update(tier=""), "/lines/0/corpus/tier"),
])
def test_a_malformed_corpus_is_i002(change, path):
    assert found(changed(lambda x: change(x[0]))) == [("KHG-I002", path, None)]


def test_the_corpus_is_optional_and_its_tier_too():
    assert found(changed(lambda x: x[0].pop("corpus"))) == []
    assert found(changed(lambda x: x[0]["corpus"].pop("tier"))) == []


# ------------------------------------------------------------------------------------------------ split manifests


def manifest(lines: list[dict[str, Any]], scheme: str) -> dict[str, Any]:
    return next(m for m in lines if m["kind"] == "c4-split-manifest" and m.get("scheme") == scheme)


@pytest.mark.parametrize(("change", "code", "where"), [
    (lambda m: m["splits"].update({"f:cat-7": "holdout"}), "KHG-I002", "/splits/f:cat-7"),
    (lambda m: m.update(scheme="random"), "KHG-I002", "/scheme"),
    (lambda m: m.update(seed=""), "KHG-I002", "/seed"),
    (lambda m: m["container"].pop("sha256"), "KHG-I002", "/container"),
    (lambda m: m["container"].update(sha256="sha256:xyz"), "KHG-I003", "/container/sha256"),
    (lambda m: m["probe"].update({"f:loop-yyz": ["near_duplicate"]}), "KHG-I002", "/probe/f:loop-yyz/0"),
    (lambda m: m["probe"].update({"f:loop-yyz": []}), "KHG-I002", "/probe/f:loop-yyz"),
    (lambda m: m["lite"].append(m["lite"][0]), "KHG-I002", "/lite"),
])
def test_a_malformed_manifest_field_is_refused(change, code, where):
    lines = new_lines()
    n = at(lines, manifest(lines, "leak_probe")["id"])
    lines[n] = copy.deepcopy(lines[n])
    change(lines[n])
    assert found(lines) == [(code, f"/lines/{n}{where}", "KHG-C011" if code == "KHG-I003" else None)]


def test_a_probe_fact_is_a_test_fact_of_the_manifest():
    """P3a DESIGN §6.2: a probe fact stays in test while its leaked counterparts move to train."""
    lines = new_lines()
    n = at(lines, manifest(lines, "leak_probe")["id"])
    lines[n]["splits"]["f:loop-yyz"] = "train"
    assert found(lines) == [("KHG-I002", f"/lines/{n}/probe/f:loop-yyz", None)]
    lines[n]["splits"].pop("f:loop-yyz")
    assert found(lines) == [("KHG-I002", f"/lines/{n}/probe/f:loop-yyz", None)]


def test_the_filter_index_reads_the_inference_split():
    """Facts an inductive model sees at test time are known facts: indexed under ``inference`` and filtered."""
    lines = new_lines()
    m = manifest(lines, "semi_inductive")
    inference = sorted(f for f, s in m["splits"].items() if s == "inference")
    assert inference
    facts = [r for r in FIXTURE["records"] if r.get("kind") == "hyperedge"]
    index = completion.FilterIndex.from_records(facts, schema=SCHEMA, manifest=m)
    assert [index.split_of(f) for f in inference] == ["inference"] * len(inference)
    assert {index.split_of(f) for f in m["splits"]} == set(m["splits"].values())


# ------------------------------------------------------------------------------------------------ extraction docs


def doc_line(lines: list[dict[str, Any]]) -> int:
    return at(lines, "c4-extraction-doc")


@pytest.mark.parametrize(("change", "where"), [
    (lambda d: d.update(doc_kind="news"), "/doc_kind"),
    (lambda d: d.update(source={"licence": "CC BY-SA 4.0"}), "/source"),
    (lambda d: d.update(source={"url": "https://example.org/x", "note": "?"}), "/source"),
    (lambda d: d.update(source={"url": "https://example.org/x", "revision": 1375387986}), "/source/revision"),
    (lambda d: d.update(gold_scope=["position_held", "position_held"]), "/gold_scope"),
    (lambda d: d["mentions"][0].update(source="table"), "/mentions/0/source"),
    (lambda d: d["mentions"][0].pop("source"), "/mentions/0"),
    (lambda d: d["mentions"][0].update(spans=[[0, 9, 1]]), "/mentions/0/spans/0"),
    (lambda d: d["mentions"][0].update(spans=[[0, 9], [0, 9]]), "/mentions/0/spans"),
])
def test_a_malformed_extraction_field_is_i002(change, where):
    lines = new_lines()
    n = doc_line(lines)
    change(lines[n])
    assert found(lines) == [("KHG-I002", f"/lines/{n}{where}", None)]


def test_the_source_takes_its_four_fields():
    lines = new_lines()
    n = doc_line(lines)
    lines[n]["source"] = {"url": "https://en.wikipedia.org/wiki/Louis_XIV", "revision": "1375387986",
                          "licence": "CC BY-SA 4.0", "attribution": "Wikipedia contributors"}
    assert found(lines) == []


def test_a_gold_scope_relation_is_declared_in_the_schema():
    lines = new_lines()
    n = doc_line(lines)
    lines[n]["gold_scope"] = ["position_held", "succeeded_by"]
    assert found(lines) == [("KHG-I003", f"/lines/{n}/gold_scope/1", "KHG-S001")]
    lines[n]["gold_scope"] = ["khg:disputes"]  # a lifecycle relation is never extracted
    assert found(lines) == [("KHG-I003", f"/lines/{n}/gold_scope/0", "KHG-S001")]
    lines[n]["gold_scope"] = []  # nothing audited complete
    assert found(lines) == []


@pytest.mark.parametrize(("span", "ok"), [([0, 9], True), ([66, 75], True), ([0, 0], False), ([9, 3], False),
                                          ([70, 76], False), ([-1, 3], False)])
def test_a_mention_span_lies_in_the_text(span, ok):
    """Spans are half-open, in code points of the NFC text (75 of them here), as position selectors are (§2.8)."""
    lines = new_lines()
    n = doc_line(lines)
    assert len(lines[n]["text"]) == 75
    lines[n]["mentions"][0]["spans"] = [span]
    if ok:
        assert found(lines) == []
    elif span[0] < 0:
        assert found(lines) == [("KHG-I002", f"/lines/{n}/mentions/0/spans/0/0", None)]
    else:
        assert found(lines) == [("KHG-I002", f"/lines/{n}/mentions/0/spans/0", None)]


def test_spans_count_code_points_outside_the_basic_plane():
    lines = new_lines()
    n = doc_line(lines)
    text = "Note by 𠮷田: Louis XIV reigned."
    lines[n]["text"], lines[n]["text_sha256"] = text, record.text_sha256(text)
    lines[n]["gold"] = []
    lines[n]["mentions"] = [m for m in lines[n]["mentions"] if m["entity"]["id"] == "ex:LouisXIV"]
    lines[n]["mentions"][0]["spans"] = [[12, 21]]
    assert text[12:21] == "Louis XIV"
    assert found(lines) == []
    lines[n]["mentions"][0]["spans"] = [[12, 32]]
    assert found(lines) == [("KHG-I002", f"/lines/{n}/mentions/0/spans/0", None)]


def test_a_mention_names_one_entity_once():
    lines = new_lines()
    n = doc_line(lines)
    lines[n]["mentions"].append(copy.deepcopy(lines[n]["mentions"][0]))
    k = len(lines[n]["mentions"]) - 1
    assert found(lines) == [("KHG-I002", f"/lines/{n}/mentions/{k}/entity/id", None)]


def test_a_mention_carries_a_c1_entity_record():
    lines = new_lines()
    n = doc_line(lines)
    lines[n]["mentions"][0]["entity"].pop("types")
    assert found(lines) == [("KHG-I003", f"/lines/{n}/mentions/0/entity", "KHG-C010")]


def test_the_candidate_table_does_not_need_the_gold_entities():
    """The table is built from the text, not from the gold (P9 §3.1): a distractor need not be a gold entity, and
    a gold entity need not be offered."""
    lines = new_lines()
    doc = lines[doc_line(lines)]
    offered = {m["entity"]["id"] for m in doc["mentions"]}
    gold = {e["id"] for e in doc["entities"]}
    assert offered - gold == {"ex:Mazarin"}
    assert all(m["source"] == "distractor" and "spans" not in m for m in doc["mentions"]
               if m["entity"]["id"] == "ex:Mazarin")
    for m in doc["mentions"]:
        for s, e in m.get("spans", []):
            assert doc["text"][s:e] in {m["entity"]["label"], *m["entity"].get("aliases", [])}


# ------------------------------------------------------------------------------------------------ retrieval, completion


def question(lines: list[dict[str, Any]], mode: str) -> int:
    return next(n for n, q in enumerate(lines) if q["kind"] == "c4-retrieval-question" and q.get("answer_mode") == mode)


@pytest.mark.parametrize(("change", "where"), [
    (lambda q: q.update(answer_mode="list"), "/answer_mode"),
    (lambda q: q["answer"]["values"].append(copy.deepcopy(q["answer"]["values"][0])), "/answer/values"),
    (lambda q: q["answer"].update(values=[{"entity": "ex:AirCanada"}]), "/answer/values/0"),
    (lambda q: q["answer"]["values"][0]["literal"].update(unit="wd:Q11573"), "/answer/values/0/literal/unit"),
])
def test_a_count_is_one_quantity_of_unit_1(change, where):
    lines = new_lines()
    n = question(lines, "count")
    change(lines[n])
    assert found(lines) == [("KHG-I002", f"/lines/{n}{where}", None)]


def test_an_unanswerable_count_has_no_value():
    lines = new_lines()
    n = question(lines, "count")
    lines[n].update(answerable=False, answer={"values": []})
    assert found(lines) == []


def test_provenance_stays_open():
    lines = new_lines()
    n = question(lines, "single")
    lines[n]["provenance"]["anything"] = {"nested": [1, 2]}
    assert found(lines) == []


def test_a_query_manifest_is_an_id():
    lines = new_lines()
    n = at(lines, "c4-completion-query")
    lines[n]["manifest"] = "c4 splits"
    assert found(lines) == [("KHG-I003", f"/lines/{n}/manifest", "KHG-C011")]


def test_the_retrieval_scorer_reads_the_mode_of_each_question():
    """A question's ``answer_mode`` comes before ``RetrievalConfig.answer_mode``; ``count`` scores as ``single`` does
    (the one value, by identity)."""
    lines = new_lines()
    qs = [q for q in lines if q["kind"] == "c4-retrieval-question"]
    cost = {"prompt_tokens": 1, "completion_tokens": 1, "llm_calls": 1, "retrieval_calls": 1, "retrieval_ms": 1,
            "wall_ms": 1}

    def response(q: dict[str, Any], values: list[Any]) -> dict[str, Any]:
        return {"kind": "retrieval-response", "qid": q["qid"], "answer": {"values": values, "abstained": False},
                "retrieved": [], "cost": cost}

    by_mode = {q["answer_mode"]: q for q in qs}
    single, many, count = by_mode["single"], by_mode["set"], by_mode["count"]
    rs = [response(single, single["answer"]["values"]), response(many, many["answer"]["values"][:1]),
          response(count, count["answer"]["values"])]
    rep = retrieval.score(qs, rs)
    items = rep["items"]
    assert (items[single["qid"]]["answer_mode"], items[single["qid"]]["em"]) == ("single", 1.0)
    assert items[many["qid"]]["answer_mode"] == "set"
    assert (items[many["qid"]]["set_p"], items[many["qid"]]["set_r"], items[many["qid"]]["em"]) == (1.0, 0.5, 0.0)
    assert (items[count["qid"]]["answer_mode"], items[count["qid"]]["em"]) == ("count", 1.0)
    assert "set_p" not in items[count["qid"]] and "set_p" not in items[single["qid"]]
    assert rep["aggregate"]["answer"]["set_r"] == 0.5  # over the set-mode questions only
    assert rep["breakdowns"]["by_answer_mode"]["set"]["n"] == 1
    # the configuration's mode is the mode of questions that declare none
    bare = [dict(q) for q in qs]
    for q in bare:
        q.pop("answer_mode")
    rep = retrieval.score(bare, rs, config=retrieval.RetrievalConfig(answer_mode="set"))
    assert {it["answer_mode"] for it in rep["items"].values()} == {"set"}
    assert retrieval.RetrievalConfig(answer_mode="count").answer_mode == "count"
