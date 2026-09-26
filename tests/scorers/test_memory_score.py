"""W11a: the memory scorer (DESIGN §9.2, §9.3; R05 §5.2): configuration, report, inputs and the edge rules.

- ``MemoryConfig`` has the §9.2 defaults; ``lenient`` switches the headline.
- The report is ``{scorer, config, contracts, aggregate, breakdowns, items, bootstrap}`` with the §9.1 stamps; items
  are keyed by qid and list ``depends_on``.
- The §1.3 P7 call runs on packaged data (``c4-items.jsonl`` and the memory line of ``c5-outputs.jsonl``).
- The inputs pass layer I's checks (I002, I003, I005) and ``khg-c5-io`` (C010); a malformed input raises
  ``ValidationError``, and the stored gold must equal the replay under ``config.incorrect_reasons``.
- Missing responses, "no current value" gold, redirects, set P/R/F1, ``support_success@k``, breakdowns, the
  bootstrap, and determinism under three ``PYTHONHASHSEED`` values.
"""
from __future__ import annotations

import copy
import dataclasses
import inspect
import json
import os
import subprocess
import sys
from typing import Any

import pytest

import khg_contracts
from khg_contracts import data, jsonio
from khg_contracts.errors import ValidationError
from khg_contracts.scorers import Bootstrap, memory

LINES = data.load_jsonl("fixture/c4-items.jsonl")
TRACES = {x["trace_id"]: x for x in LINES if x["kind"] == "c4-memory-trace"}
QUESTIONS = {x["qid"]: x for x in LINES if x["kind"] == "c4-memory-question"}
MEMORY_OUTPUT = next(x for x in data.load_jsonl("fixture/c5-outputs.jsonl") if x["kind"] == "memory-response")
FIXTURE = {r["id"]: r for r in data.load_json("fixture/fixture.c1.json")["records"] if "id" in r}
EVIDENCE = [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}}]
XIII, XIV = {"entity": "ex:LouisXIII"}, {"entity": "ex:LouisXIV"}
OFF = memory.MemoryConfig(bootstrap=Bootstrap(resamples=0))
KINGS = [TRACES["t:kings"]]


def response(qid: str, *values: dict[str, Any], abstained: bool = False, **extra: Any) -> dict[str, Any]:
    return {"kind": "memory-response", "qid": qid, "answer": {"values": list(values), "abstained": abstained}, **extra}


def score(questions: list[dict[str, Any]], responses: list[dict[str, Any]], schema: Any,
          traces: list[dict[str, Any]] | None = None, config: memory.MemoryConfig = OFF) -> dict[str, Any]:
    return memory.score(questions, responses, traces=traces if traces is not None else list(TRACES.values()),
                        schema=schema, config=config)


def codes(e: pytest.ExceptionInfo[ValidationError]) -> list[str]:
    return sorted(set(e.value.codes))


def rec(rid: str, **changes: Any) -> dict[str, Any]:
    r = copy.deepcopy(FIXTURE[rid])
    for f in ("version", "recorded_at", "recorded_by", "status_ref"):
        r.pop(f, None)
    r["status"] = "asserted"
    r.update(changes)
    return r


# ------------------------------------------------------------------------------------------------ configuration


def test_the_configuration_and_its_defaults():
    assert {f.name: f.default for f in dataclasses.fields(memory.MemoryConfig)} == {
        "mode": "strict", "incorrect_reasons": memory.INCORRECT_REASONS, "outranked": True, "bootstrap": Bootstrap()}
    assert len(memory.INCORRECT_REASONS) == 10 and memory.INCORRECT_REASONS_0_1 == frozenset({"wd:Q41755623"})
    assert memory.MemoryConfig.__dataclass_params__.frozen
    assert memory.MemoryConfig(incorrect_reasons=["wd:Q1"]).incorrect_reasons == frozenset({"wd:Q1"})
    for bad in ({"mode": "loose"}, {"incorrect_reasons": [""]}, {"bootstrap": 3}):
        with pytest.raises(ValueError):
            memory.MemoryConfig(**bad)
    with pytest.raises(TypeError):
        memory.MemoryConfig(incorrect_reasons="wd:Q41755623")


def test_the_documented_signatures():
    kw = "KEYWORD_ONLY"
    d = {n: (p.kind.name, p.default) for n, p in inspect.signature(memory.derive_memory_gold).parameters.items()}
    assert list(d)[:2] == ["trace", "question"] and d["schema"][0] == kw
    assert d["incorrect_reasons"] == (kw, memory.INCORRECT_REASONS) and d["outranked"] == (kw, True)
    s = {n: (p.kind.name, p.default) for n, p in inspect.signature(memory.score).parameters.items()}
    assert list(s)[:2] == ["questions", "responses"]
    assert s["traces"][0] == kw and s["schema"][0] == kw and s["config"] == (kw, memory.MemoryConfig())
    assert memory.OUTCOMES == ("current", "hedged", "stale", "anachronistic", "wrong", "abstained",
                               "correct_abstention", "hallucinated")


# ------------------------------------------------------------------------------------------------ the report


def test_the_p7_call_of_section_1_3_on_packaged_data(fixture_schema):
    """``report = memory.score(questions, responses, traces=traces, schema=S)`` with whole C4 files."""
    rep = memory.score(LINES, [MEMORY_OUTPUT], traces=LINES, schema=fixture_schema)
    assert list(rep) == ["scorer", "config", "contracts", "aggregate", "breakdowns", "items", "bootstrap"]
    assert rep["scorer"] == "memory" and rep["contracts"] == dict(khg_contracts.CONTRACTS)
    assert rep["config"] == {"mode": "strict", "incorrect_reasons": sorted(memory.INCORRECT_REASONS),
                             "outranked": True, "bootstrap": {"resamples": 1000, "seed": 0, "alpha": 0.05},
                             "qset": ["p2-fixture-qset"], "schema": fixture_schema.header}
    assert sorted(rep["items"]) == ["mq:king-1620", "mq:king-1700", "mq:maria-birthplace"]
    item = rep["items"]["mq:king-1700"]
    assert (item["outcome"], item["strict"], item["lenient"], item["depends_on"]) == ("current", 1, 1, ["f:king-14"])
    assert item["ranked_efficacy"] == 1  # LouisXIV 0.9 against LouisXIII 0.1
    assert rep["items"]["mq:king-1620"]["outcome"] == "missing"
    agg = rep["aggregate"]
    assert (agg["n_questions"], agg["n_responses"], agg["n_missing"], agg["n_answerable"]) == (3, 1, 2, 3)
    assert agg["acc_strict"] == pytest.approx(1 / 3) and agg["headline"]["metric"] == "acc_strict"
    boot = rep["bootstrap"]
    assert (boot["unit"], boot["n_units"], boot["resamples"]) == ("question", 3, 1000)
    lo, hi = boot["intervals"]["acc_strict"]
    assert 0.0 <= lo <= agg["acc_strict"] <= hi <= 1.0
    json.dumps(rep)  # plain JSON


def test_items_carry_the_question_and_the_hits(fixture_schema):
    rep = score([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", XIV, XIII)], fixture_schema, KINGS)
    item = rep["items"]["mq:king-1700"]
    assert {k: item[k] for k in ("answerable", "subtype", "relation", "trace_id", "ask_after_step", "missing")} == {
        "answerable": True, "subtype": "current_value", "relation": "position_held", "trace_id": "t:kings",
        "ask_after_step": 2, "missing": False}
    assert item["hits"] == {"current": 1, "expired": 1, "revised": 0, "outranked": 0, "future": 0, "disputed": 0,
                            "other": 0}
    assert rep["bootstrap"] is None


def test_the_lenient_preset_switches_the_headline(fixture_schema):
    config = memory.MemoryConfig(mode="lenient", bootstrap=Bootstrap(resamples=0))
    rep = score([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", XIV, XIII)], fixture_schema, KINGS, config)
    assert rep["aggregate"]["headline"] == {"metric": "acc_lenient", "value": 1.0}
    assert rep["aggregate"]["acc_strict"] == 0.0 and rep["config"]["mode"] == "lenient"


def test_breakdowns_by_subtype_and_relation(fixture_schema):
    qs = list(QUESTIONS.values())
    rs = [response("mq:king-1700", XIV), response("mq:king-1620", XIV), response("mq:maria-birthplace",
                                                                                 {"entity": "ex:Warszawa"})]
    rep = score(qs, rs, fixture_schema)
    by = rep["breakdowns"]
    assert sorted(by["by_relation"]) == ["born_in", "position_held"]
    assert by["by_relation"]["position_held"]["n"] == 2 and by["by_relation"]["position_held"]["acc_strict"] == 0.5
    assert by["by_relation"]["born_in"]["outcomes"]["current"] == 1
    assert by["by_subtype"]["current_value"]["n"] == 3
    assert rep["aggregate"]["answerable"]["acc_strict"] == pytest.approx(2 / 3)


# ------------------------------------------------------------------------------------------------ edge rules


def test_a_missing_response_is_missing_not_an_abstention(fixture_schema):
    rep = score(list(QUESTIONS.values()), [response("mq:king-1700", abstained=True), response("mq:other", XIV)],
                fixture_schema)
    assert [rep["items"][q]["outcome"] for q in sorted(rep["items"])] == ["missing", "abstained", "missing"]
    agg = rep["aggregate"]
    assert (agg["n_missing"], agg["n_unmatched_responses"], agg["abstention"]["n_abstained"]) == (2, 1, 1)
    assert agg["acc_strict"] == 0.0 and agg["abstention_rate"] == pytest.approx(1 / 3)


def test_no_current_value_gold_rewards_an_empty_answer_and_not_an_abstention(fixture_schema):
    """§9.5: an empty V_cur with nothing disputed is a valid gold (here: the fact was retracted)."""
    tr = {"kind": "c4-memory-trace", "id": "c4:mt-ret", "qset": "w11a", "split": "test", "trace_id": "t:ret",
          "entities": [copy.deepcopy(FIXTURE[i]) for i in ("ex:Kraków", "ex:Maria_Skłodowska")],
          "events": [{"step": 1, "tx_time": "2026-10-01T00:00:01Z", "put": [rec("f:born-skłodowska-kraków")]},
                     {"step": 2, "tx_time": "2026-10-01T00:00:02Z",
                      "apply": {"op": "transition", "targets": ["f:born-skłodowska-kraków"], "to": "retracted",
                                "id": "m:ret-9", "reason": "withdrawn", "evidence": EVIDENCE}}]}
    q = dict(copy.deepcopy(QUESTIONS["mq:maria-birthplace"]), qid="mq:ret", trace_id="t:ret", support=[])
    q.update({k: v for k, v in memory.derive_memory_gold(tr, q, schema=fixture_schema).items()
              if k in memory.GOLD_FIELDS})
    assert q["answer"]["values"] == [] and q["answerable"] is True
    rep = score([q], [response("mq:ret")], fixture_schema, [tr])
    item = rep["items"]["mq:ret"]
    assert (item["outcome"], item["strict"], item["set_f1"], item["set_flag"]) == ("current", 1, 1.0, "both_empty")
    assert score([q], [response("mq:ret", abstained=True)], fixture_schema, [tr])["items"]["mq:ret"]["outcome"] == \
        "abstained"
    stale = score([q], [response("mq:ret", {"entity": "ex:Kraków"})], fixture_schema, [tr])["items"]["mq:ret"]
    assert (stale["outcome"], stale["stale_kind"]) == ("stale", "revised")


def test_answers_follow_redirects_over_the_traces_entities(fixture_schema):
    tr = copy.deepcopy(TRACES["t:kings"])
    tr["entities"].append({"kind": "entity", "id": "ex:Louis14", "label": "Louis XIV", "types": ["Person"],
                           "redirect_to": "ex:LouisXIV"})
    rep = score([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", {"entity": "ex:Louis14"})], fixture_schema,
                [tr])
    assert rep["items"]["mq:king-1700"]["outcome"] == "current"


def test_a_value_that_matches_nothing_is_wrong_and_writings_do_not_matter(fixture_schema):
    rep = score([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", {"entity": "ex:Mazarin"})], fixture_schema,
                KINGS)
    item = rep["items"]["mq:king-1700"]
    assert (item["outcome"], item["hits"]["other"], item["set_f1"]) == ("wrong", 1, 0.0)
    assert "set_flag" not in item and "stale_kind" not in item  # items leave out what is None
    assert rep["aggregate"]["wrong_rate"] == 1.0 and rep["aggregate"]["stale_share_of_errors"] == 0.0
    twice = score([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", XIV, XIV)], fixture_schema, KINGS)
    assert twice["items"]["mq:king-1700"]["set_p"] == 1.0  # Â is a set of value identities


def test_support_success_against_the_current_support(fixture_schema):
    units = [{"rank": 2, "unit_id": "f:king-14", "unit_kind": "hyperedge", "hyperedge_ids": ["f:king-14"]},
             {"rank": 1, "unit_id": "f:king-13", "unit_kind": "hyperedge", "hyperedge_ids": ["f:king-13"]}]
    rep = score([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", XIV, retrieved=units)], fixture_schema, KINGS)
    item = rep["items"]["mq:king-1700"]
    assert [item[f"support_success@{k}"] for k in memory.KS] == [0, 1, 1, 1, 1]
    assert rep["aggregate"]["support"] == {"n": 1, "support_success@1": 0.0, "support_success@3": 1.0,
                                           "support_success@5": 1.0, "support_success@10": 1.0,
                                           "support_success@20": 1.0}
    none = score([QUESTIONS["mq:king-1700"]], [response("mq:king-1700", XIV)], fixture_schema, KINGS)
    assert none["aggregate"]["support"]["n"] == 0 and "support_success@1" not in none["items"]["mq:king-1700"]


def test_the_scores_do_not_depend_on_the_order_of_the_inputs(fixture_schema):
    qs = list(QUESTIONS.values())
    rs = [response("mq:king-1700", XIV), response("mq:king-1620", XIV, XIII),
          response("mq:maria-birthplace", {"entity": "ex:Kraków"})]
    config = memory.MemoryConfig(bootstrap=Bootstrap(resamples=50))
    a = score(qs, rs, fixture_schema, config=config)
    b = memory.score(list(reversed(LINES)), list(reversed(rs)), traces=list(reversed(LINES)), schema=fixture_schema,
                     config=config)
    assert a["aggregate"] == b["aggregate"] and a["items"] == b["items"] and a["breakdowns"] == b["breakdowns"]


def test_the_report_does_not_depend_on_the_hash_seed(tmp_path):
    script = tmp_path / "memory_report.py"
    script.write_text(
        "import json\n"
        "from khg_contracts import data, jsonio\n"
        "from khg_contracts.schema import load_schema\n"
        "from khg_contracts.scorers import memory\n"
        "S = load_schema(data.load_json('fixture/fixture.relation-schema.json'))\n"
        "lines = data.load_jsonl('fixture/c4-items.jsonl')\n"
        "rs = [{'kind': 'memory-response', 'qid': q, 'answer': {'values': v, 'abstained': False}} for q, v in [\n"
        "    ('mq:king-1700', [{'entity': 'ex:LouisXIV'}, {'entity': 'ex:LouisXIII'}]),\n"
        "    ('mq:king-1620', [{'entity': 'ex:LouisXIV'}]), ('mq:maria-birthplace', [{'entity': 'ex:Kraków'}])]]\n"
        "print(jsonio.canonical(memory.score(lines, rs, traces=lines, schema=S)))\n", encoding="utf-8")
    outs = set()
    for seed in ("0", "1", "4242"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        outs.add(subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True,
                                env=env).stdout)
    assert len(outs) == 1
    rep = jsonio.loads(outs.pop())
    assert [rep["items"][q]["outcome"] for q in sorted(rep["items"])] == ["anachronistic", "hedged", "stale"]


# ------------------------------------------------------------------------------------------------ inputs


def test_the_stored_gold_must_equal_the_replay(fixture_schema):
    """MC180's fault, met by the scorer: I005."""
    q = copy.deepcopy(QUESTIONS["mq:king-1700"])
    q["answer"]["values"] = [XIII]
    with pytest.raises(ValidationError) as e:
        score([q], [response("mq:king-1700", XIV)], fixture_schema)
    assert codes(e) == ["KHG-I005"] and e.value.info["findings"][0]["path"] == "/questions/0/answer/values"


def test_the_replay_uses_the_configured_incorrect_reasons(fixture_schema):
    """A question set built with the default reasons must be scored with them (ruling 3)."""
    tr = {"kind": "c4-memory-trace", "id": "c4:mt-pop", "qset": "w11a", "split": "test", "trace_id": "t:pop",
          "entities": [copy.deepcopy(FIXTURE["ex:Łódź"])],
          "events": [{"step": 1, "tx_time": "2026-10-01T00:00:01Z",
                      "put": [rec("f:pop-łódź-2019"), rec("f:pop-łódź-2019-dep")]}]}
    key = [{"role": "place", "value": {"entity": "ex:Łódź"}},
           {"role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2019-00-00T00:00:00Z",
                                                           "precision": 9, "calendar": "gregorian"}}}]
    q = dict(copy.deepcopy(QUESTIONS["mq:maria-birthplace"]), qid="mq:pop", trace_id="t:pop", ask_after_step=1,
             relation="population", key=key, target_role="quantity", support=["f:pop-łódź-2019"])
    q.update({k: v for k, v in memory.derive_memory_gold(tr, q, schema=fixture_schema).items()
              if k in memory.GOLD_FIELDS})
    assert [s["kind"] for s in q["stale_values"]] == ["revised"]
    old = {"literal": {"datatype": "quantity", "amount": "+685285", "unit": "1"}}
    assert score([q], [response("mq:pop", old)], fixture_schema, [tr])["items"]["mq:pop"]["outcome"] == "stale"
    none = memory.MemoryConfig(incorrect_reasons=frozenset(), bootstrap=Bootstrap(resamples=0))
    with pytest.raises(ValidationError) as e:
        score([q], [response("mq:pop", old)], fixture_schema, [tr], none)
    assert codes(e) == ["KHG-I005"] and e.value.info["findings"][0]["path"] == "/questions/0/stale_values"


@pytest.mark.parametrize(("change", "code", "path"), [
    (lambda qs, ts, rs: qs.append(copy.deepcopy(qs[0])), "KHG-I002", "/questions/3/qid"),
    (lambda qs, ts, rs: ts.append(copy.deepcopy(ts[0])), "KHG-I002", "/traces/2/trace_id"),
    (lambda qs, ts, rs: ts.pop(), "KHG-I003", "/questions/2/trace_id"),
    (lambda qs, ts, rs: rs.append(copy.deepcopy(rs[0])), "KHG-C010", "/responses/1/qid"),
    (lambda qs, ts, rs: qs[0].update(tolerance={"amount": "-1"}), "KHG-I002", "/questions/0/tolerance/amount"),
    (lambda qs, ts, rs: rs[0]["answer"]["values"].append(
        {"literal": {"datatype": "time", "time": "+0000-00-00T00:00:00Z", "precision": 9}}),
     "KHG-S006", "/responses/0/answer/values/1"),
])
def test_malformed_inputs_raise(change, code, path, fixture_schema):
    qs = [copy.deepcopy(q) for q in QUESTIONS.values()]
    ts = [copy.deepcopy(t) for t in TRACES.values()]
    rs = [response("mq:king-1700", XIV)]
    change(qs, ts, rs)
    with pytest.raises(ValidationError) as e:
        memory.score(qs, rs, traces=ts, schema=fixture_schema, config=OFF)
    assert code in e.value.codes
    assert path in [f["path"] for f in e.value.info["findings"]]


def test_items_and_outputs_pass_their_schemas(fixture_schema):
    q = copy.deepcopy(QUESTIONS["mq:king-1700"])
    del q["future_values"]
    with pytest.raises(ValidationError) as e:
        score([q], [], fixture_schema)
    assert codes(e) == ["KHG-I004"]
    with pytest.raises(ValidationError) as e:
        score([QUESTIONS["mq:king-1700"]], [{"kind": "retrieval-response", "qid": "mq:king-1700"}], fixture_schema)
    assert "KHG-C010" in e.value.codes
    with pytest.raises(ValidationError) as e:  # an embedded C1 value that is not one: I003, the C finding nested
        bad = copy.deepcopy(QUESTIONS["mq:king-1700"])
        bad["key"][0]["value"] = {"entity": 5}
        score([bad], [], fixture_schema)
    assert codes(e) == ["KHG-I003"] and e.value.info["findings"][0]["nested"]["layer"] == "C"
    with pytest.raises(ValueError):
        memory.score([], [], traces=[], schema=None)
    with pytest.raises(TypeError):
        memory.score([], [], traces=[], schema=fixture_schema, config={"mode": "strict"})  # type: ignore[arg-type]


def test_a_trace_the_store_refuses_is_i003_with_the_store_finding_nested(fixture_schema):
    tr = copy.deepcopy(TRACES["t:maria"])
    tr["events"][1] = {"step": 2, "tx_time": "2026-10-01T00:00:02Z", "put": [rec("m:sup-1")]}
    with pytest.raises(ValidationError) as e:
        score([QUESTIONS["mq:maria-birthplace"]], [], fixture_schema, [tr])
    [f] = e.value.info["findings"]
    assert (f["code"], f["path"], f["nested"]["code"]) == ("KHG-I003", "/traces/0/events/1", "KHG-D014")


def test_an_empty_input_scores_nothing(fixture_schema):
    rep = memory.score([], [], traces=[], schema=fixture_schema)
    assert rep["items"] == {} and rep["aggregate"]["n_questions"] == 0 and rep["aggregate"]["acc_strict"] is None
    assert rep["bootstrap"] is None and rep["aggregate"]["stale_rate"] is None
    assert jsonio.canonical(rep)  # still plain JSON
