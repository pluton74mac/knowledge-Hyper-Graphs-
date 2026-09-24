"""W9: ``queue_items(paths)`` and verdict aggregation (DESIGN §7).

Each item comes with its folded ``state`` and the ``verdicts`` keyed by (``core_key``, ``event_hash``), so a verdict
carries over to a re-extraction of the same event in another run. The scorers read the items as they come (§1.3,
P9).
"""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data
from khg_contracts.errors import ValidationError
from khg_contracts.queue import Queue, queue_items
from khg_contracts.queue.lines import dump_line
from khg_contracts.queue.verdicts import SEVERITY_ORDER, aggregate, complete
from khg_contracts.scorers import stability

SMOKE = data.path("fixture/smoke-queue.khg-queue.jsonl")


def test_the_smoke_item_comes_with_its_state(smoke_lines):
    items = list(queue_items(SMOKE))
    assert items == [dict(smoke_lines[1], state="accepted", verdicts=[])]
    assert list(queue_items([SMOKE, str(SMOKE)]))[1]["qid"] == "q:p2-smoke.000001"


def _run(smoke, store, name, queue_id, run_id, *, rec=None, verdict=None):
    q = Queue.create(smoke.dir / name, queue_id=queue_id, schema=smoke.schema, base=smoke.base,
                     created_at=smoke.TIMES["created"])
    qid = smoke.submit(q, smoke.candidate(q, 1, rec), run=dict(smoke.RUN, run_id=run_id))
    smoke.lint(q, qid)
    if verdict is not None:
        q.verdict(qid, actor="curator:smoke", verdict=verdict)
    return q, qid


def test_verdicts_carry_over_to_a_re_extraction(smoke, store):
    first, a = _run(smoke, store, "r1.jsonl", "run-1.o1", "run-1", verdict={"evidence_id": "e2", "label": "correct"})
    second, b = _run(smoke, store, "r2.jsonl", "run-2.o1", "run-2")
    other_text = copy.deepcopy(smoke.king14)
    other_text["evidence"][1]["selectors"] = other_text["evidence"][1]["selectors"][:1]  # another event
    other_text["evidence"][1].pop("event_hash")
    third, c = _run(smoke, store, "r3.jsonl", "run-3.o1", "run-3", rec=other_text,
                    verdict={"evidence_id": "e2", "label": "span_boundary"})
    items = list(queue_items([first, second, third]))
    assert [(i["qid"], i["state"], i["run"]["run_id"]) for i in items] == [(a, "linted", "run-1"),
                                                                            (b, "linted", "run-2"),
                                                                            (c, "linted", "run-3")]
    assert items[0]["keys"]["core_key"] == items[1]["keys"]["core_key"] == items[2]["keys"]["core_key"]
    labels = [[v["verdict"]["label"] for v in i["verdicts"]] for i in items]
    assert labels == [["correct"], ["correct"], ["span_boundary"]]  # the verdict of run 1 carries over to run 2
    assert items[1]["verdicts"][0]["target"] == a  # the entry as logged in run 1's queue
    assert list(queue_items([second])) == [dict(items[1], verdicts=[])]  # only the files read


def test_verdicts_come_in_file_then_log_order_and_items_are_copies(smoke, store):
    q, qid = _run(smoke, store, "r.jsonl", "run-1.o1", "run-1", verdict={"evidence_id": "e2", "label": "negated"})
    q.verdict(qid, actor="curator:b", verdict={"evidence_id": "e2", "label": "correct"})
    items = list(queue_items(q))
    assert [v["verdict"]["label"] for v in items[0]["verdicts"]] == ["negated", "correct"]
    assert aggregate(items[0]["verdicts"]) == "correct"
    items[0]["payload"]["relation"] = "changed"
    assert next(queue_items(q))["payload"]["relation"] == "position_held"


def test_a_file_with_a_structural_error_raises_before_any_item(tmp_path, smoke_lines):
    bad = copy.deepcopy(smoke_lines)
    bad[3]["target"] = "q:p2-smoke.000009"
    p = tmp_path / "bad.khg-queue.jsonl"
    p.write_text("".join(dump_line(x) for x in bad), encoding="utf-8")
    with pytest.raises(ValidationError) as exc:
        queue_items([SMOKE, p])  # raised by the call, not by the iteration
    assert exc.value.codes == ("KHG-Q007",) and exc.value.info["source"] == str(p)
    with pytest.raises(TypeError):
        queue_items(42)


def test_the_stability_scorer_reads_queue_items(smoke, store, schema):
    """§1.3, P9: ``stability.score(items, schema=S, unit="run")`` over the items of two runs."""
    first, _ = _run(smoke, store, "r1.jsonl", "run-1.o1", "run-1")
    second, _ = _run(smoke, store, "r2.jsonl", "run-2.o1", "run-2")
    report = stability.score(list(queue_items([first, second])), schema=schema, unit="run")
    assert report["scorer"] == "stability" and report["breakdowns"]["n_items"] == 2
    assert report["aggregate"]["units"] == [{"run_id": "run-1", "order_id": "o1"},
                                            {"run_id": "run-2", "order_id": "o1"}]
    assert report["aggregate"]["content_key"]["mean_pairwise_jaccard"] == 1.0  # one fact, extracted by both runs


@pytest.mark.parametrize(("labels", "want"), [
    ([], None),
    (["correct"], "correct"),
    (["correct", "wrong_role", "span_boundary"], "correct"),
    (["correct", "no_relation"], "no_relation"),
    (["correct", "wrong_relation", "wrong_role"], "wrong_relation"),
    (["hypothesis", "negated", "span_boundary"], "span_boundary"),
    (["other", "extra_participant", "missing_participant"], "missing_participant"),
    (["wrong_filler", "wrong_role"], "wrong_role"),
])
def test_aggregation_follows_db_7_3(labels, want):
    assert aggregate([{"label": x} for x in labels]) == want
    assert aggregate([{"verdict": {"label": x}} for x in labels]) == want
    assert list(SEVERITY_ORDER)[:3] == ["no_relation", "wrong_relation", "wrong_role"]


def test_complete_fills_the_keys_from_the_item(smoke_lines):
    item = smoke_lines[1]
    v = complete({"evidence_id": "e2", "label": "correct"}, item)
    assert v == {"evidence_id": "e2", "label": "correct", "core_key": item["keys"]["core_key"],
                 "event_hash": item["payload"]["evidence"][1]["event_hash"], "bindings": [], "missing": []}
    given = complete({"evidence_id": "e1", "label": "correct", "core_key": "sha256:" + "3" * 64}, item)
    assert given["core_key"] == "sha256:" + "3" * 64 and "event_hash" not in given  # kept; checked later


def test_an_event_hash_that_is_not_a_string_names_no_event(tmp_path, smoke_lines):
    """The queue schema leaves the payload to layer C, so ``queue_items`` reads a payload whose event hash is a list
    (C010 in ``validate_queue``); that evidence attaches no verdict. It raised ``TypeError`` while iterating."""
    lines = copy.deepcopy(smoke_lines)
    lines[1]["payload"]["evidence"][1]["event_hash"] = ["sha256:x"]
    path = tmp_path / "q.khg-queue.jsonl"
    path.write_text("".join(dump_line(x) for x in lines), encoding="utf-8")
    assert [(i["qid"], i["state"], i["verdicts"]) for i in queue_items([path])] == [
        ("q:p2-smoke.000001", "accepted", [])]
