"""P3b's call sequence (DESIGN §1.3): link prediction on a literal-free projection.

``train``, ``valid`` and ``test`` are the fixture's facts under the C4 split manifest (``c4:splits``). ``model`` is a
deterministic stand-in for a trained completer: it scores the candidate universe of each query, giving the target
1.0, the first other candidate in id order 1.0 as well (a tie), and every other candidate 0.0. ``model_runs`` pairs
each query with the model's probability for the target (0.75) and its top-1 guess, the target. So every query has
rank 1 or a two-way tie at the top, unless the filter removes the tied candidate as a known answer, and the numbers
below follow by hand.
"""
from __future__ import annotations

from typing import Any

import pytest

from khg_contracts import CONTRACTS, record
from khg_contracts.scorers import completion

TARGET_PROB = 0.75


class TieModel:
    """Scores a query's candidate universe: the target and the first other candidate 1.0, the rest 0.0."""

    def __init__(self, schema: Any, entities: list[dict[str, Any]]) -> None:
        self.schema = schema
        self.entities = entities

    def candidates(self, q: dict[str, Any]) -> list[str]:
        """The query's universe as candidate ids: a listed universe as it is, else the entities of the types."""
        cu = q["candidate_universe"]
        if cu["kind"] == "list":
            return list(cu["ids"])
        return sorted(e["id"] for e in self.entities
                      if any(self.schema.is_subtype(t, want) for t in e["types"] for want in cu["types"]))

    def scores(self, q: dict[str, Any]) -> dict[str, float]:
        target = completion.candidate_id(q["target"]["value"])
        out = {c: 1.0 if c == target else 0.0 for c in self.candidates(q)}
        others = sorted(c for c in out if c != target)
        if others:
            out[others[0]] = 1.0
        return out


def test_p3b_sequence(S, splits, fixture_entities):
    train, valid, test = splits["train"], splits["valid"], splits["test"]
    model = TieModel(S, fixture_entities)
    queries = completion.build_queries(test, S, slots=("core", "qualifier"), literal_targets="exclude")
    model_runs = [(q, TARGET_PROB, (completion.candidate_id(q["target"]["value"]), TARGET_PROB)) for q in queries]

    # >>> DESIGN §1.3
    # P3b: link prediction on a literal-free projection
    queries = completion.build_queries(test, S, slots=("core", "qualifier"), literal_targets="exclude")
    index = completion.FilterIndex.from_records(train, valid, test)
    rows = [record.project.positional(f, S, literals="drop", widths={"agent": 4}) for f in train]
    outputs = [completion.rank_stats(q, model.scores(q), index, target_prob=p, top1=t) for q, p, t in model_runs]
    report = completion.score(queries, outputs, config=completion.CompletionConfig(preset="hype"))
    # <<< DESIGN §1.3

    # one query per core or qualifier binding of the five test facts; three literal targets are left out
    assert [q["qid"] for q in queries] == [
        "cq:f:born-skłodowska-kraków#b2", "cq:f:born-skłodowska-kraków#b1", "cq:f:claim-1#b2", "cq:f:claim-1#b1",
        "cq:f:king-14#b1", "cq:f:king-14#b2", "cq:f:king-14#b5", "cq:f:pop-łódź-2019#b1", "cq:f:route-1#b1",
        "cq:f:route-1#b2", "cq:f:route-1#b3", "cq:f:route-1#b4"]
    assert queries.excluded == {"literal": 3, "special": 0}
    # the literal-free projection of train: literal-only usages dropped, the unbounded agent role padded to 4
    assert rows == [
        ("born_in", "ex:LouisXIV", "ex:Paris"),
        ("born_in", "ex:Maria_Skłodowska", "ex:Warszawa"),
        ("co_administration_causes", "ex:insulin", "ex:metformin", "khg:none", "khg:none", "ex:hypoglycaemia"),
        ("flies_between", "ex:AirCanada", "ex:YYZ", "ex:YYZ"),
        ("population", "ex:Łódź"),
        ("station_profile", "ex:東京駅")]
    # rank statistics, not score vectors: the target is never beaten; a tie remains unless the filter removed it
    by_qid = {o["qid"]: o for o in outputs}
    assert [o["qid"] for o in outputs] == [q["qid"] for q in queries]
    assert all(o["kind"] == "completion-rank" and o["n_greater"] == 0 for o in outputs)
    assert [by_qid[q["qid"]]["n_candidates"] for q in queries] == [len(model.candidates(q)) for q in queries]
    # Maria's other birthplace, ex:Warszawa, is a known answer in train: it is filtered out of the Kraków query
    assert by_qid["cq:f:born-skłodowska-kraków#b2"]["n_filtered_out"] == 1
    assert sum(o["n_filtered_out"] for o in outputs) == 1
    # the position and carrier queries have one candidate each, so no tie; the other ten tie at the top
    singles = {"cq:f:king-14#b2", "cq:f:route-1#b1"}
    assert {qid for qid, o in by_qid.items() if o["n_equal"] == 0} == singles
    assert all(o["target_prob"] == TARGET_PROB and o["top1"]["prob"] == TARGET_PROB for o in outputs)
    # the score under the hype preset: per-task average, pessimistic ties, the full-tuple filter
    assert report["contracts"] == dict(CONTRACTS)
    agg = report["aggregate"]
    assert (agg["headline"], agg["filter"], agg["rank"]) == ("per_task", "exact", "pessimistic")
    assert (agg["n_queries"], agg["n_outputs"], agg["n_missing"]) == (12, 12, 0)
    assert agg["per_task"]["mrr"] == pytest.approx((2 * 1 + 10 * (1 / 2)) / 12)
    assert agg["per_task"]["hits@1"] == pytest.approx(2 / 12)
    assert agg["per_task"]["hits@3"] == agg["per_task"]["hits@10"] == 1.0
    assert agg["rank_audit"]["optimistic_mrr"] == 1.0
    assert agg["rank_audit"]["tie_exact_mrr"] == pytest.approx((2 * 1 + 10 * (1 + 1 / 2) / 2) / 12)
    # top-1 calibration: every top-1 guess is right at confidence 0.75
    cal = agg["calibration"]
    assert (cal["n"], cal["accuracy"], cal["mean_confidence"]) == (12, 1.0, TARGET_PROB)
    assert cal["ece"] == {"equal_width": pytest.approx(0.25), "equal_mass": pytest.approx(0.25)}
    assert cal["brier"] == pytest.approx(0.0625)
    assert set(report["items"]) == set(by_qid)
    assert report["items"]["cq:f:king-14#b1"]["depends_on"] == ["f:king-14"]


def test_p3b_a_fact_target_is_in_its_own_universe(S, splits):
    """``f:claim-1`` is in the test split; the fact it claims, ``f:born-louis14-paris``, is in train. The query's
    candidate universe still holds its target, so a model can rank it."""
    claim = next(q for q in completion.build_queries(splits["test"], S) if q["qid"] == "cq:f:claim-1#b2")
    assert claim["target"]["value"] == {"fact": "f:born-louis14-paris"}
    assert claim["candidate_universe"] == {"kind": "list",
                                           "ids": ["f:born-louis14-paris", "f:born-skłodowska-kraków"]}
