"""The scorers' input checks (DESIGN §9.2, §9.4, §9.6): system outputs against ``khg-c5-io-1.0.0``, C4 items
through the draft schema (layer I, embedded C1 findings under I003), and extraction outputs (C3 queue items or C1
hyperedges naming their document). A malformed input raises ``ValidationError``."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data
from khg_contracts.errors import ValidationError
from khg_contracts.scorers import _inputs, completion, extraction, retrieval
from khg_contracts.scorers.bootstrap import Bootstrap


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
    named = dict(rec, evidence=[{"id": "e1", "type": "extracted", "mode": "automatic",
                                 "source": {"doc_id": "d1", "doc_sha256": "sha256:" + "0" * 64}}])
    agg = extraction.score([doc], [named], schema=r05_schema, config=config)["aggregate"]
    assert agg["strict"]["tp"] == 1 and agg["n_runs"] == 1
    bad_payload = build.items(rec)
    bad_payload["payload"]["bindings"][0]["value"] = {"entity": "t:a", "literal": {}}
    with pytest.raises(ValidationError) as e:
        extraction.score([doc], [bad_payload], schema=r05_schema, config=config)
    assert e.value.codes == ("KHG-C001",)


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
