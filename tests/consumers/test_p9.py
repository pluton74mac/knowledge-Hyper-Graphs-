"""P9's call sequence (DESIGN §1.3): extraction runs into queues, then scoring.

The extractor reads ``doc:louis-bio`` ("Louis XIV succeeded his father Louis XIII as King of France on 14 May 1643.")
and outputs one fact. ``gold`` is the packaged ``c4-extraction-doc`` item of that document, ``entity_base`` the G3
smoke base (the fixture's entities), and ``d`` and ``h`` the document's id and hash.

The sequence writes run 1, order o1. Two more queue files, written beforehand with the same calls, stand for the
other units the scorers compare: run 1 under order o2 finds the same fact, and run 2 under order o1 misses the
``replaces`` qualifier. ``paths`` lists all three, so ``stability.score`` sees three units.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import CONTRACTS, data, jsonio, queue, record, validate
from khg_contracts.scorers import extraction, stability

AGENT = {"agent": "p9-extractor", "agent_version": "1.0.0"}


def extracted(gold_fact: dict[str, Any], *, d: str, h: str, run_id: str, drop: tuple[str, ...] = ()) -> dict[str, Any]:
    """What the extractor outputs: the gold fact's bindings (minus ``drop``) without bids, with extracted evidence
    quoting the sentence (code points 0-74 of the NFC text)."""
    gold_evidence = gold_fact["evidence"][0]
    return {"kind": "hyperedge", "relation": gold_fact["relation"], "status": "asserted",
            "bindings": [{"role": b["role"], "value": copy.deepcopy(b["value"])}
                         for b in gold_fact["bindings"] if b["role"] not in drop],
            "evidence": [{"id": "e1", "type": "extracted", "mode": "automatic",
                          "source": {"doc_id": d, "doc_sha256": h},
                          "selectors": copy.deepcopy(gold_evidence["selectors"]),
                          "activity": {**AGENT, "run_id": run_id}}]}


def write_run(S: Any, path: str, run: dict[str, Any], fact: dict[str, Any], *, d: str, h: str,
              entity_base: dict[str, Any]) -> None:
    """One more unit, written with the calls of the sequence."""
    queue_id = f"{run['run_id']}.{run['order_id']}"
    q = queue.Queue.create(path, queue_id=queue_id, schema=S, base=entity_base)
    cand = queue.make_candidate(fact, queue_id=queue_id, seq=1, schema=S)
    qid = q.submit(cand, run=run, doc={"doc_id": d, "doc_sha256": h}, submitted_by="p9-extractor/1.0.0")
    queue.Linter(S, entities=entity_base).lint(q, qid)


def test_p9_sequence(S, c4_items, workdir: Path):
    doc = next(x for x in c4_items if x["kind"] == "c4-extraction-doc")
    gold = [doc]
    entity_base = data.load_json("fixture/smoke-base.c1.json")
    d, h = doc["doc_id"], doc["text_sha256"]
    fact = extracted(doc["gold"][0], d=d, h=h, run_id="run-1")
    write_run(S, "run-1.o2.khg-queue.jsonl", {"run_id": "run-1", "order_id": "o2", "position": 1},
              extracted(doc["gold"][0], d=d, h=h, run_id="run-1"), d=d, h=h, entity_base=entity_base)
    write_run(S, "run-2.o1.khg-queue.jsonl", {"run_id": "run-2", "order_id": "o1", "position": 1},
              extracted(doc["gold"][0], d=d, h=h, run_id="run-2", drop=("replaces",)), d=d, h=h,
              entity_base=entity_base)
    paths = ["run-1.o1.khg-queue.jsonl", "run-1.o2.khg-queue.jsonl", "run-2.o1.khg-queue.jsonl"]

    # >>> DESIGN §1.3
    # P9: extraction runs into queues, then scoring
    q = queue.Queue.create("run-1.o1.khg-queue.jsonl", queue_id="run-1.o1", schema=S, base=entity_base)
    cand = queue.make_candidate(fact, queue_id="run-1.o1", seq=1, schema=S)
    qid = q.submit(cand, run={"run_id": "run-1", "order_id": "o1", "position": 1},
                   doc={"doc_id": d, "doc_sha256": h}, submitted_by="p9-extractor/1.0.0")
    queue.Linter(S, entities=entity_base).lint(q, qid)
    items = list(queue.queue_items(paths))
    extraction.score(gold, items, schema=S)
    stability.score(items, schema=S, unit="run")                # a run is (run_id, order_id)
    # <<< DESIGN §1.3

    # the candidate: a queue-scoped id, status candidate, bids in listed order, the event hash stamped once
    assert (cand["id"], cand["status"]) == ("cand:run-1.o1.000001", "candidate")
    assert [(b["bid"], b["role"]) for b in cand["bindings"]] == \
        [("b1", "holder"), ("b2", "position"), ("b3", "replaces"), ("b4", "start_time")]
    assert cand["evidence"][0]["event_hash"].startswith("sha256:")
    # the item passed the structural lint; the queue file validates against C3 with its base
    assert qid == "q:run-1.o1.000001" and q.state(qid) == "linted"
    assert validate.validate_queue("run-1.o1.khg-queue.jsonl", schema=S, bases=[entity_base])["ok"]
    lint = [x for x in jsonio.loads_lines((workdir / "run-1.o1.khg-queue.jsonl").read_bytes())
            if x["kind"] == "log-entry"]
    assert [(x["action"], x["outcome"], x["rule_set"]["id"], x["findings"]) for x in lint] == \
        [("lint", "pass", "structural", [])]
    # the items of the three units, with their folded state and keys computed as asserted facts
    assert [(i["run"]["run_id"], i["run"]["order_id"], i["state"]) for i in items] == \
        [("run-1", "o1", "linted"), ("run-1", "o2", "linted"), ("run-2", "o1", "linted")]
    full, partial = items[0]["keys"], items[2]["keys"]
    assert items[1]["keys"] == full and full["core_key"] == partial["core_key"]
    assert full["content_key"] != partial["content_key"]
    assert full["content_key"] == record.content_key({**doc["gold"][0], "status": "asserted"}, S)

    # extraction (asked again: the sequence leaves the reports unnamed): every (run, document) unit against the gold
    ex = extraction.score(gold, items, schema=S)
    assert ex["scorer"] == "extraction" and ex["contracts"] == dict(CONTRACTS)
    agg = ex["aggregate"]
    assert (agg["n_docs"], agg["n_runs"], agg["n_gold"], agg["n_pred"]) == (1, 3, 1, 3)
    assert (agg["strict"]["tp"], agg["strict"]["f1"]) == (2, pytest.approx(2 / 3))  # run 2 misses a qualifier
    assert (agg["core"]["tp"], agg["core"]["f1"]) == (3, 1.0)                          # ... but not the core
    assert (agg["arg_c"]["tp"], agg["arg_c"]["n_pred"], agg["arg_c"]["n_gold"]) == (11, 11, 12)
    assert agg["arg_c"]["f1"] == pytest.approx(22 / 23) and agg["role_accuracy"] == 1.0
    unit = ex["items"][d]
    assert unit["depends_on"] == [doc["gold"][0]["id"]] == ["f:gold-louis-bio-1"]
    assert [(u["run_id"], u["order_id"], u["strict_tp"], u["missed"]) for u in unit["runs"]] == [
        ("run-1", "o1", 1, []), ("run-1", "o2", 1, []), ("run-2", "o1", 0, ["f:gold-louis-bio-1"])]

    # stability over the three (run_id, order_id) units, on both keys
    st = stability.score(items, schema=S, unit="run")
    sagg = st["aggregate"]
    assert sagg["units"] == [{"run_id": "run-1", "order_id": "o1"}, {"run_id": "run-1", "order_id": "o2"},
                             {"run_id": "run-2", "order_id": "o1"}]
    content, core = sagg["content_key"], sagg["core_key"]
    assert content["pairwise_jaccard"] == [1.0, 0.0, 0.0]
    assert content["mean_pairwise_jaccard"] == pytest.approx(1 / 3)
    assert (content["n_facts"], content["core_ratio"], content["support_histogram"]) == (2, 0.0, {"1": 1, "2": 1})
    assert (content["unstable_fraction"], content["mean_churn"]) == (1.0, pytest.approx(2 / 3))
    assert content["order_effect"] == {"n_within_pairs": 1, "n_between_pairs": 2, "J_within": 0.0,
                                       "J_between": 0.5, "delta_order": -0.5}
    assert (core["mean_pairwise_jaccard"], core["core_ratio"], core["support_histogram"]) == (1.0, 1.0, {"3": 1})
    assert core["order_effect"]["delta_order"] == 0.0
