"""W11a: layer I, ``validate_item`` on C4 files (DESIGN §9.6, §8.1), with the memory-gold replay (I005, §9.5).

Beyond the five I cases of G2 (``tests/gate/test_malformed.py``): the packaged file is clean under both engines;
the header and repeated ids are I002; the schema pin is D009; embedded C1 content is I003 with the C, S or D finding
nested (the draft's C codes, layer S on embedded records, the store's refusals of a trace); I005 compares every
stored gold field with the replay, by value identity and with the default deprecation reasons.
"""
from __future__ import annotations

import copy
import unicodedata
from typing import Any, Callable

import pytest

from khg_contracts import data
from khg_contracts.scorers import memory
from khg_contracts.validate import ENGINES, layers, run, validate_item

LINES = data.load_jsonl("fixture/c4-items.jsonl")
FIXTURE = {r["id"]: r for r in data.load_json("fixture/fixture.c1.json")["records"] if "id" in r}
DOC_TEXTS = data.load_json("fixture/fixture.doc-texts.json")
N = {x.get("qid") or x.get("trace_id") or x["kind"]: n for n, x in enumerate(LINES)}
MQ, MARIA_Q, KINGS, MARIA, EXT = N["mq:king-1700"], N["mq:maria-birthplace"], N["t:kings"], N["t:maria"], 1


def lines(change: Callable[[list[dict[str, Any]]], Any] | None = None) -> list[dict[str, Any]]:
    out = copy.deepcopy(LINES)
    if change is not None:
        change(out)
    return out


def findings(items: Any, engine: str = "jsonschema", **kw: Any) -> list[tuple[str, str, str | None]]:
    """``(code, path, nested code)`` of every finding of a run (the fixture schema unless ``schema`` is given)."""
    kw.setdefault("schema", data.load_json("fixture/fixture.relation-schema.json"))
    rep = run(items, kind="item", engine=engine, **kw)
    assert rep.skipped == []
    return [(f["code"], f["path"], (f.get("nested") or {}).get("code")) for f in rep.findings]


def rec(rid: str) -> dict[str, Any]:
    r = copy.deepcopy(FIXTURE[rid])
    for f in ("version", "recorded_at", "recorded_by", "status_ref"):
        r.pop(f, None)
    r["status"] = "asserted"
    return r


@pytest.mark.parametrize("engine", ENGINES)
def test_the_packaged_file_is_valid(engine, fixture_schema):
    assert layers.implemented("i") and layers.spec("i").owner == "W11a"
    assert validate_item(data.path("fixture/c4-items.jsonl"), schema=fixture_schema, doc_texts=DOC_TEXTS,
                         engine=engine) == {"ok": True, "findings": []}
    assert findings(lines(), engine) == []
    assert [x["kind"] for x in LINES] == ["c4-header", "c4-extraction-doc", "c4-completion-query",
                                          "c4-retrieval-question", "c4-memory-trace", "c4-memory-trace",
                                          "c4-memory-question", "c4-memory-question", "c4-memory-question",
                                          "c4-split-manifest"]


# ------------------------------------------------------------------------------------------------ the file


def test_the_header_is_line_1_and_only_line_1():
    assert findings(lines(lambda x: x.pop(0))) == [("KHG-I002", "/lines/0", None)]
    assert findings(lines(lambda x: x.append(copy.deepcopy(x[0])))) == [("KHG-I002", "/lines/10/kind", None)]


@pytest.mark.parametrize(("field", "at", "source"), [
    ("id", "/lines/9/id", lambda x: x[9].update(id=x[2]["id"])),
    ("qid", "/lines/7/qid", lambda x: x[7].update(qid="mq:king-1700")),
    ("trace_id", "/lines/10/trace_id", lambda x: x.append(dict(copy.deepcopy(x[4]), id="c4:mt-kings-2"))),
    ("doc_id", "/lines/10/doc_id", lambda x: x.append(dict(copy.deepcopy(x[1]), id="c4:ext-2"))),
])
def test_an_id_used_twice_is_i002(field, at, source):
    found = findings(lines(source))
    assert ("KHG-I002", at, None) in found
    assert {code for code, _, _ in found} == {"KHG-I002"}  # an ambiguous trace is not replayed


def test_without_a_schema_the_file_is_d009_and_nothing_is_replayed():
    broken = lines(lambda x: x[MQ]["answer"].update(values=[{"entity": "ex:LouisXIII"}]))
    assert findings(broken, schema=None) == [("KHG-D009", "/lines/0/schema", None)]


def test_a_schema_the_header_does_not_pin_is_d009(r05_schema):
    broken = lines(lambda x: x[MQ]["answer"].update(values=[{"entity": "ex:LouisXIII"}]))
    rep = run(broken, kind="item", schema=r05_schema)
    assert [(f["code"], f["path"]) for f in rep.findings] == [("KHG-D009", "/lines/0/schema")]
    assert rep.first_layer == "D" and not rep.ok  # a letter outside J V I ranks after them


# ------------------------------------------------------------------------------------------------ I003


def test_an_embedded_value_the_draft_refuses_is_i003_with_the_c_finding_nested():
    found = findings(lines(lambda x: x[MQ]["key"][0].update(value={"entity": 5})))
    assert found and all(code == "KHG-I003" and nested[:5] == "KHG-C" for code, _, nested in found)
    assert found[0][1].startswith("/lines/6/key/0/value")
    rep = run(lines(lambda x: x[MQ]["key"][0].update(value={"entity": 5})), kind="item",
              schema=data.load_json("fixture/fixture.relation-schema.json"))
    assert rep.first_layer == "I" and {f["layer"] for f in rep.findings} == {"I"}


def test_embedded_records_pass_layer_s_with_the_s_finding_nested():
    def undeclared_role(x):
        x[KINGS]["events"][0]["put"][0]["bindings"][1]["role"] = "monarch"
    assert findings(lines(undeclared_role)) == [  # the holder is then unbound too (S003)
        ("KHG-I003", f"/lines/{KINGS}/events/0/put/0/bindings/1/role", "KHG-S002"),
        ("KHG-I003", f"/lines/{KINGS}/events/0/put/0", "KHG-S003")]

    def decomposed(x):
        x[MARIA]["entities"][0]["label"] = unicodedata.normalize("NFD", "Kraków")
    assert findings(lines(decomposed)) == [("KHG-I003", f"/lines/{MARIA}/entities/0/label", "KHG-S020")]


def test_the_extraction_gold_spans_are_read_against_the_items_own_text():
    def shifted(x):
        x[EXT]["gold"][0]["evidence"][0]["selectors"][1]["start"] += 1
    assert findings(lines(shifted)) == [("KHG-I003", f"/lines/{EXT}/gold/0/evidence/0", "KHG-S021")]


def test_warnings_of_embedded_records_are_not_reported():
    """``f:loop-yyz`` breaks a warning constraint (S024, must_differ): the item stays valid."""
    loop = rec("f:loop-yyz")
    assert findings(lines(lambda x: x[EXT]["gold"].append(loop))) == []


def test_a_trace_the_store_refuses_is_i003_at_the_event_with_the_store_finding_nested():
    def lifecycle_put(x):
        x[MARIA]["events"][1] = {"step": 2, "tx_time": "2026-10-01T00:00:02Z", "put": [rec("m:sup-1")]}
    assert findings(lines(lifecycle_put)) == [("KHG-I003", f"/lines/{MARIA}/events/1", "KHG-D014")]

    def same_time(x):
        x[KINGS]["events"][1]["tx_time"] = x[KINGS]["events"][0]["tx_time"]
    assert findings(lines(same_time)) == [("KHG-I003", f"/lines/{KINGS}/events/1", "KHG-D018")]

    def bad_event(x):
        x[MARIA]["events"][1]["apply"]["superseded"] = "f:born-skłodowska-kraków"
    assert findings(lines(bad_event)) == [("KHG-I003", f"/lines/{MARIA}/events/1", "KHG-C010")]


def test_a_question_whose_trace_is_missing_or_does_not_fit_the_schema():
    assert findings(lines(lambda x: x[MQ].update(trace_id="t:nowhere"))) == [
        ("KHG-I003", f"/lines/{MQ}/trace_id", None)]
    assert findings(lines(lambda x: x[MQ].update(relation="reigned"))) == [("KHG-I003", f"/lines/{MQ}", "KHG-S001")]
    assert findings(lines(lambda x: x[MQ].update(target_role="monarch"))) == [
        ("KHG-I003", f"/lines/{MQ}", "KHG-S002")]


# ------------------------------------------------------------------------------------------------ I005


@pytest.mark.parametrize(("change", "field"), [
    (lambda q: q["stale_values"][0].update(kind="revised"), "stale_values"),
    (lambda q: q["stale_values"].clear(), "stale_values"),
    (lambda q: q["future_values"].append({"entity": "ex:LouisXIII"}), "future_values"),
    (lambda q: q["disputed_values"].append({"entity": "ex:LouisXIV"}), "disputed_values"),
    (lambda q: q["answer"]["values"].append({"entity": "ex:LouisXIV"}), "answer/values"),
    (lambda q: q.update(answerable=False), "answerable"),
])
def test_each_stored_gold_field_is_checked_against_the_replay(change, field):
    assert findings(lines(lambda x: change(x[MQ]))) == [("KHG-I005", f"/lines/{MQ}/{field}", None)]


def test_questions_the_replay_cannot_answer_are_i005():
    assert findings(lines(lambda x: x[MQ].update(ask_after_step=3))) == [("KHG-I005", f"/lines/{MQ}", None)]
    key = [{"role": "holder", "value": {"entity": "ex:LouisXIV"}}]  # a role, but not the key
    assert findings(lines(lambda x: x[MQ].update(key=key))) == [("KHG-I005", f"/lines/{MQ}", None)]


def test_values_compare_by_identity_and_answer_text_is_free():
    """Order and writing do not matter (an NFD id is the same entity); ``answer.text`` is not gold."""
    def rewritten(x):
        x[MARIA_Q]["stale_values"][0]["value"]["entity"] = unicodedata.normalize("NFD", "ex:Kraków")
        x[MQ]["answer"]["text"] = "Louis XIV"
    assert findings(lines(rewritten)) == []
    both = copy.deepcopy(LINES[MQ])
    both.update(qid="mq:king-now", id="c4:mq-king-now", stale_values=[],
                where=dict(both["where"], as_of=None),
                answer={"values": [{"entity": "ex:LouisXIV"}, {"entity": "ex:LouisXIII"}]})
    assert findings(lines(lambda x: x.insert(9, both))) == []
    assert findings(lines(lambda x: x.insert(9, dict(both, answer={"values": [{"entity": "ex:LouisXIV"}] * 2})))) \
        == [("KHG-I005", "/lines/9/answer/values", None)]


def test_the_replay_uses_the_default_deprecation_reasons():
    """§14 question 3: I005 replays with ``wd:Q41755623`` only, so a set built with other reasons disagrees."""
    trace = {"kind": "c4-memory-trace", "id": "c4:mt-pop", "qset": "p2-fixture-qset", "split": "test",
             "trace_id": "t:pop", "entities": [copy.deepcopy(FIXTURE["ex:Łódź"])],
             "events": [{"step": 1, "tx_time": "2026-10-01T00:00:01Z",
                         "put": [rec("f:pop-łódź-2019"), dict(rec("f:pop-łódź-2019-dep"), status="asserted")]}]}
    key = [{"role": "place", "value": {"entity": "ex:Łódź"}},
           {"role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2019-00-00T00:00:00Z",
                                                           "precision": 9, "calendar": "gregorian"}}}]
    q = dict(copy.deepcopy(LINES[MQ]), qid="mq:pop", id="c4:mq-pop", trace_id="t:pop", ask_after_step=1,
             relation="population", key=key, target_role="quantity", support=["f:pop-łódź-2019"])
    schema = data.load_json("fixture/fixture.relation-schema.json")
    disagree = [("KHG-I005", "/lines/11/stale_values", None)]
    for reasons, want in ((memory.INCORRECT_REASONS, []), (frozenset(), disagree)):
        q.update({k: v for k, v in memory.derive_memory_gold(trace, q, schema=schema,
                                                             incorrect_reasons=reasons).items()
                  if k in memory.GOLD_FIELDS})
        assert findings(lines(lambda x, q=q: x.extend([trace, q]))) == want


# ------------------------------------------------------------------------------------------------ the draft


def test_the_draft_names_i001_i002_and_i004():
    assert findings(lines(lambda x: x[3].update(kind="c4-trivia"))) == [("KHG-I001", "/lines/3/kind", None)]
    assert findings(lines(lambda x: x[9].pop("kind"))) == [("KHG-I002", "/lines/9", None)]
    assert findings(lines(lambda x: x[MQ].pop("future_values"))) == [("KHG-I004", f"/lines/{MQ}", None)]
    # director's ruling 7: I004 is only a memory question without stale_values or future_values; any other missing
    # required field, such as text, is I002 (this supersedes observation 2 of the W11a notes)
    assert findings(lines(lambda x: x[MQ].pop("text"))) == [("KHG-I002", f"/lines/{MQ}", None)]


def test_fastjsonschema_stops_at_the_first_fault_of_a_line():
    def two_faults(x):
        x[3].pop("where")
        x[3]["hops"] = 0
    full, fast = findings(lines(two_faults)), findings(lines(two_faults), "fastjsonschema")
    assert len(full) == 2 and len(fast) == 1 and set(fast) <= set(full)
    assert {code for code, _, _ in full} == {"KHG-I002"}


@pytest.mark.parametrize("engine", ENGINES)
def test_odd_lines_never_raise(engine):
    odd = [[{"kind": "c4-header"}], [{}], [{"kind": "c4-memory-question", "trace_id": 3}],
           [LINES[0], {"kind": "c4-memory-trace", "events": [{"step": "x", "put": 5}]}],
           [LINES[0], {"kind": "c4-memory-question", **{k: v for k, v in LINES[MQ].items() if k != "kind"},
                       "where": {"as_of": "+1700", "valid_mode": "sometimes", "rank": [], "status": ["x"]}}],
           [LINES[0], LINES[MQ]]]
    for items in odd:
        rep = run(items, kind="item", schema=data.load_json("fixture/fixture.relation-schema.json"), engine=engine)
        assert rep.skipped == [] and not rep.ok
        assert {f["layer"] for f in rep.errors} <= {"V", "I", "D"}  # V: a header without its format
