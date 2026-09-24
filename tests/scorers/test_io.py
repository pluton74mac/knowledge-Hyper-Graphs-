"""The scorers' input checks (DESIGN §9.2, §9.4, §9.6): system outputs against ``khg-c5-io-1.0.0``, C4 items
through the draft schema (layer I, embedded C1 findings under I003), and extraction outputs (C3 queue items or C1
hyperedges naming their document). A malformed input raises ``ValidationError``."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data
from khg_contracts.errors import ValidationError
from khg_contracts.scorers import _inputs, completion, extraction, retrieval, stability
from khg_contracts.scorers.bootstrap import Bootstrap

NO_BOOT = extraction.ExtractionConfig(bootstrap=Bootstrap(resamples=0))
EXTRACTED = {"id": "e1", "type": "extracted", "mode": "automatic",
             "source": {"doc_id": "d1", "doc_sha256": "sha256:" + "0" * 64},
             "selectors": [{"type": "position", "start": 0, "end": 3}],
             "activity": {"agent": "tests", "agent_version": "0", "model": "none", "run_id": "run-1"}}


@pytest.fixture(scope="module")
def outputs():
    return data.load_jsonl("fixture/c5-outputs.jsonl")


@pytest.fixture(scope="module")
def c4_items():
    return data.load_jsonl("fixture/c4-items.jsonl")


def test_the_three_example_outputs_are_valid(outputs):
    assert [o["kind"] for o in outputs] == ["completion-rank", "retrieval-response", "memory-response"]
    assert all(_inputs.c5_findings(o) == [] for o in outputs)
    assert _inputs.check_outputs(outputs[:1], kind="completion-rank") == outputs[:1]


@pytest.mark.parametrize("line, patch, code, path", [
    (0, lambda o: o.update(n_candidates=0), "KHG-C010", "/n_candidates"),
    (0, lambda o: o.pop("n_equal"), "KHG-C010", ""),
    (0, lambda o: o.update(target_prob=1.5), "KHG-C010", "/target_prob"),
    (0, lambda o: o.update(extra=1), "KHG-C010", ""),
    (0, lambda o: o["top1"].update(value={"entity": "a", "fact": "b"}), "KHG-C001", "/top1/value"),
    (1, lambda o: o.pop("cost"), "KHG-C010", ""),
    (1, lambda o: o["cost"].pop("wall_ms"), "KHG-C010", "/cost"),
    (1, lambda o: o["retrieved"][0].update(unit_kind="sentence"), "KHG-C010", "/retrieved/0/unit_kind"),
    (1, lambda o: o["retrieved"][0]["bids"].append(["f:king-14"]), "KHG-C010", "/retrieved/0/bids/4"),
    (1, lambda o: o["answer"]["values"].append({"literal": {"datatype": "colour"}}), "KHG-C002",
     "/answer/values/1/literal/datatype"),
    (2, lambda o: o.update(kind="judgement"), "KHG-C010", "/kind"),
])
def test_malformed_outputs(outputs, line, patch, code, path):
    bad = copy.deepcopy(outputs[line])
    patch(bad)
    findings = _inputs.c5_findings(bad)
    assert (code, path) in [(f["code"], f["path"]) for f in findings]
    with pytest.raises(ValidationError) as e:
        _inputs.check_outputs([bad], kind=bad.get("kind", "completion-rank"))
    assert code in e.value.codes


def test_scorers_refuse_malformed_or_foreign_outputs(outputs, c4_items):
    rq = [x for x in c4_items if x["kind"] == "c4-retrieval-question"]
    with pytest.raises(ValidationError) as e:
        retrieval.score(rq, [outputs[2]])  # a memory response
    assert e.value.codes == ("KHG-C010",) and e.value.info["findings"][0]["path"] == "/lines/0/kind"
    bad = copy.deepcopy(outputs[1])
    del bad["cost"]
    with pytest.raises(ValidationError):
        retrieval.score(rq, [bad])
    with pytest.raises(ValidationError) as e:
        retrieval.score(rq, ["not an object"])
    assert e.value.codes == ("KHG-J007",)


def test_the_c4_items_pass_and_their_faults_are_layer_i(c4_items):
    assert all(_inputs.c4_findings(x) == [] for x in c4_items)
    unknown = dict(c4_items[3], kind="c4-trivia-question")
    assert [f["code"] for f in _inputs.c4_findings(unknown)] == ["KHG-I001"]
    no_where = {k: v for k, v in c4_items[3].items() if k != "where"}
    assert [f["code"] for f in _inputs.c4_findings(no_where)] == ["KHG-I002"]
    no_stale = {k: v for k, v in c4_items[6].items() if k != "stale_values"}
    assert "KHG-I004" in [f["code"] for f in _inputs.c4_findings(no_stale)]
    bad_value = copy.deepcopy(c4_items[1])
    bad_value["gold"][0]["bindings"][0]["value"] = {"entity": "ex:LouisXIV", "fact": "f:x"}
    (f,) = _inputs.c4_findings(bad_value, "/lines/1")
    assert f["code"] == "KHG-I003" and f["path"] == "/lines/1/gold/0/bindings/0/value"
    assert f["nested"]["code"] == "KHG-C001"
    wanted, headers = _inputs.check_items(c4_items, kinds=("c4-completion-query",))
    assert [x["qid"] for x in wanted] == ["cq:king-14-holder"] and [h["qset"] for h in headers] == ["p2-fixture-qset"]
    with pytest.raises(ValidationError) as e:
        _inputs.check_items([c4_items[0], unknown], kinds=("c4-retrieval-question",))
    assert e.value.codes == ("KHG-I001",) and e.value.info["findings"][0]["path"] == "/lines/1/kind"


def test_embedded_gold_with_a_role_the_relation_does_not_allow_is_i003(c4_items, fixture_schema):
    """MC178's fault, met by the scorer: the S finding is nested under I003."""
    doc = copy.deepcopy(c4_items[1])
    doc["gold"][0]["bindings"][3]["role"] = "successor"
    with pytest.raises(ValidationError) as e:
        extraction.score([doc], [], schema=fixture_schema)
    assert e.value.codes == ("KHG-I003",)
    (f,) = e.value.info["findings"]
    assert f["nested"]["code"] == "KHG-S002" and f["path"] == "/docs/0/gold/0"


def test_extraction_outputs(build, r05_schema):
    rec = build.fact("f1", "s", A="a", B="b")
    doc = build.doc("d1", [rec])
    config = extraction.ExtractionConfig(bootstrap=Bootstrap(resamples=0))
    no_run = build.items(rec)
    del no_run["run"]
    with pytest.raises(ValidationError) as e:
        extraction.score([doc], [no_run], schema=r05_schema, config=config)
    assert e.value.codes == ("KHG-Q001",)
    with pytest.raises(ValidationError) as e:
        extraction.score([doc], [{"kind": "log-entry"}], schema=r05_schema, config=config)
    assert e.value.codes == ("KHG-Q003",)
    with pytest.raises(ValidationError) as e:  # a bare hyperedge must name its document through its evidence
        extraction.score([doc], [rec], schema=r05_schema, config=config)
    assert e.value.codes == ("KHG-C010",)
    extracted = {"id": "e1", "type": "extracted", "mode": "automatic",
                 "source": {"doc_id": "d1", "doc_sha256": "sha256:" + "0" * 64},
                 "selectors": [{"type": "position", "start": 0, "end": 3}],
                 "activity": {"agent": "tests", "agent_version": "0", "model": "none", "run_id": "run-1"}}
    named = dict(rec, evidence=[extracted])
    agg = extraction.score([doc], [named], schema=r05_schema, config=config)["aggregate"]
    assert agg["strict"]["tp"] == 1 and agg["n_runs"] == 1
    # a bare hyperedge is a C1 hyperedge, checked by layer C: extracted evidence needs its selectors and activity
    sketchy = dict(rec, evidence=[{k: v for k, v in extracted.items() if k not in ("selectors", "activity")}])
    with pytest.raises(ValidationError) as e:
        extraction.score([doc], [sketchy], schema=r05_schema, config=config)
    assert e.value.codes == ("KHG-C007",) and e.value.info["findings"][0]["path"] == "/lines/0/evidence/0"
    bad_payload = build.items(rec)
    bad_payload["payload"]["bindings"][0]["value"] = {"entity": "t:a", "literal": {}}
    with pytest.raises(ValidationError) as e:
        extraction.score([doc], [bad_payload], schema=r05_schema, config=config)
    # layer C on the payload, as validate_queue reports it: two keys (C001) and an incomplete literal (C004)
    assert [(f["code"], f["path"]) for f in e.value.info["findings"]] == [
        ("KHG-C001", "/lines/0/payload/bindings/0/value"), ("KHG-C004", "/lines/0/payload/bindings/0/value/literal")]


MALFORMED = [  # (name, patch of the predicted hyperedge, code, path in the hyperedge)
    ("relation is a list", lambda p: p.update(relation=[]), "KHG-C010", "/relation"),
    ("no relation", lambda p: p.pop("relation"), "KHG-C010", ""),
    ("bindings is a number", lambda p: p.update(bindings=5), "KHG-C010", "/bindings"),
    ("no bindings", lambda p: p.pop("bindings"), "KHG-C010", ""),
    ("no binding", lambda p: p.update(bindings=[]), "KHG-S007", "/bindings"),
    ("a binding is a number", lambda p: p["bindings"].__setitem__(0, 7), "KHG-C010", "/bindings/0"),
    ("a role is a list", lambda p: p["bindings"][0].update(role=[]), "KHG-C010", "/bindings/0/role"),
    ("a binding without its value", lambda p: p["bindings"][0].pop("value"), "KHG-C010", "/bindings/0"),
    ("a goal", lambda p: p.update(status="goal"), "KHG-C010", "/status"),
    ("an undeclared relation", lambda p: p.update(relation="nope"), "KHG-S001", "/relation"),
]


@pytest.mark.parametrize("patch, code, path", [m[1:] for m in MALFORMED], ids=[m[0] for m in MALFORMED])
def test_a_malformed_prediction_is_a_validation_error(build, r05_schema, patch, code, path):
    """A malformed predicted hyperedge, in a queue item or bare, raises ``ValidationError`` in both scorers, with
    the code layer C or S gives it (``validate_queue`` reports the same on a payload) at its line. It used to escape
    as KeyError, TypeError or a bare ValueError, or to be scored (review f-scorers-08, X-03)."""
    rec = build.fact("f1", "s", A="a", B="b")
    gold = [build.doc("d1", [rec])]
    item = build.items(rec)
    patch(item["payload"])
    bare = copy.deepcopy(dict(rec, evidence=[EXTRACTED]))
    patch(bare)
    scorers = {"extraction": lambda items: extraction.score(gold, items, schema=r05_schema, config=NO_BOOT),
               "stability": lambda items: stability.score(items, schema=r05_schema)}
    for items, where in (([item], "/lines/0/payload"), ([bare], "/lines/0")):
        for scorer, call in scorers.items():
            with pytest.raises(ValidationError) as e:
                call(items)
            found = [(f["code"], f["path"]) for f in e.value.info["findings"]]
            assert (code, where + path) in found, (scorer, where, found)
            assert all(p.startswith(where) for _, p in found), (scorer, where, found)


def _route(**changes):
    """The fixture's ordered route (stops at positions 1, 2 and 3), without its version fields."""
    fixture = {r["id"]: r for r in data.load_json("fixture/fixture.c1.json")["records"] if "id" in r}
    out = copy.deepcopy({k: v for k, v in fixture["f:route-1"].items()
                         if k not in ("version", "recorded_at", "recorded_by")})
    out.update(changes)
    return out


def test_an_ordered_role_without_a_position_is_s015(build, fixture_schema):
    """One stop of the ordered route without its position: layer C accepts it, the scorers cannot order it. S015 at
    the prediction's line, and I003 with S015 nested in gold (it was a TypeError; review f-scorers-08)."""
    good = _route(id="g1")
    bad = _route(id="p1")
    del bad["bindings"][2]["position"]
    assert "position" not in bad["bindings"][2] and bad["bindings"][2]["role"] == "stop"
    items = [build.items(bad)]
    for call in (lambda: extraction.score([build.doc("d1", [good])], items, schema=fixture_schema, config=NO_BOOT),
                 lambda: stability.score(items, schema=fixture_schema)):
        with pytest.raises(ValidationError) as e:
            call()
        assert e.value.codes == ("KHG-S015",) and e.value.info["findings"][0]["path"] == "/lines/0/payload"
    for call in (lambda: extraction.score([build.doc("d1", [dict(bad, id="g1")])], [], schema=fixture_schema,
                                          config=NO_BOOT),
                 lambda: stability.score([], schema=fixture_schema, gold=[build.doc("d1", [dict(bad, id="g1")])])):
        with pytest.raises(ValidationError) as e:
            call()
        (f,) = e.value.info["findings"]
        assert (f["code"], f["path"], f["nested"]["code"]) == ("KHG-I003", "/docs/0/gold/0", "KHG-S015")


def test_a_goal_in_the_gold_is_i003(build, r05_schema):
    """The draft lets a goal into an extraction document's gold, but it is no fact to score: I003 with C010 nested
    (it was a bare ValueError; review f-scorers-08)."""
    goal = dict(build.fact("g1", "s", A="a", B="b"), status="goal")
    gold = [build.doc("d1", [goal])]
    assert _inputs.c4_findings(gold[0]) == []
    for call in (lambda: extraction.score(gold, [], schema=r05_schema, config=NO_BOOT),
                 lambda: stability.score([], schema=r05_schema, gold=gold)):
        with pytest.raises(ValidationError) as e:
            call()
        (f,) = e.value.info["findings"]
        assert (f["code"], f["path"]) == ("KHG-I003", "/docs/0/gold/0")
        assert (f["nested"]["code"], f["nested"]["path"]) == ("KHG-C010", "/status")


def test_a_value_without_an_identity_is_located(build):
    """A year 0 passes the value patterns but has no identity (S006). In a question's gold it is I003 at the value,
    with S006 nested (as the memory scorer reports it); in a response, S006 at the response's value. Both used to
    raise S006 at the path '' (review f-scorers-08)."""
    year0 = {"literal": {"datatype": "time", "time": "+0000-01-01T00:00:00Z", "precision": 9,
                         "calendar": "gregorian"}}
    config = retrieval.RetrievalConfig(bootstrap=Bootstrap(resamples=0))
    q = build.question("q1", [["h1"]], answer={"values": [year0]})
    assert _inputs.c4_findings(q) == []
    with pytest.raises(ValidationError) as e:
        retrieval.score([q], [build.response("q1", ["h1"])], config=config)
    (f,) = e.value.info["findings"]
    assert (f["code"], f["path"], f["nested"]["code"]) == ("KHG-I003", "/questions/0/answer/values/0", "KHG-S006")
    fine = build.question("q1", [["h1"]], answer={"values": [{"entity": "t:x"}]})
    wrong = build.response("q1", ["h1"], answer={"values": [{"entity": "t:x"}, year0], "abstained": False})
    with pytest.raises(ValidationError) as e:
        retrieval.score([fine], [build.response("q0", ["h1"]), wrong], config=config)
    assert e.value.codes == ("KHG-S006",) and e.value.info["findings"][0]["path"] == "/lines/1/answer/values/1"


def test_rank_stats_writes_valid_records(c4_items, fixture_schema):
    q = next(x for x in c4_items if x["kind"] == "c4-completion-query")
    index = completion.FilterIndex.from_records(data.load_json("fixture/fixture.c1.json")["records"],
                                                schema=fixture_schema)
    rec = completion.rank_stats(q, {"ex:LouisXIV": 0.62, "ex:LouisXIII": 0.62, "ex:Mazarin": 0.1}, index,
                                target_prob=0.62, top1=("ex:LouisXIV", 0.62), prob_map={"temperature": 1.0},
                                model_rank=2)
    assert rec == {"kind": "completion-rank", "qid": "cq:king-14-holder", "n_candidates": 3, "n_filtered_out": 0,
                   "n_greater": 0, "n_equal": 1, "target_prob": 0.62,
                   "top1": {"value": {"entity": "ex:LouisXIV"}, "prob": 0.62}, "prob_map": {"temperature": 1.0},
                   "model_rank": 2}
    assert _inputs.c5_findings(rec) == []
    for kwargs in (dict(model_rank=3), dict(target_prob=1.2), dict(top1=({"entity": "x"}, -0.1))):
        with pytest.raises(ValueError):
            completion.rank_stats(q, {"ex:LouisXIV": 0.62, "ex:LouisXIII": 0.62, "ex:Mazarin": 0.1}, index, **kwargs)
    with pytest.raises(ValueError):  # the target must be a scored candidate
        completion.rank_stats(q, {"ex:LouisXIII": 0.62}, index)
    with pytest.raises(ValueError):  # every candidate of the universe needs a score
        completion.rank_stats(q, {"ex:LouisXIV": 0.62}, index, universe=["ex:LouisXIV", "ex:Mazarin"])
    with pytest.raises(ValueError):
        completion.rank_stats(q, {"ex:LouisXIV": float("nan")}, index)
