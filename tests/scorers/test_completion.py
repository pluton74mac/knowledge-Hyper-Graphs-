"""The completion scorer beyond the R05 tables (DESIGN §9.2, §9.3): ``build_queries``, the filter index, the
presets, missing outputs, the adjusted measures and the report."""
from __future__ import annotations

import json
from fractions import Fraction as F

import pytest

from khg_contracts import data
from khg_contracts.errors import ValidationError
from khg_contracts.record import arity_bin, literal_node_id
from khg_contracts.scorers import _inputs, completion
from khg_contracts.scorers.bootstrap import Bootstrap


def config(**kw):
    return completion.CompletionConfig(bootstrap=Bootstrap(resamples=0), **kw)


@pytest.fixture(scope="module")
def fixture_records():
    return data.load_json("fixture/fixture.c1.json")["records"]


def test_build_queries_on_the_fixture(fixture_records, fixture_schema):
    queries = completion.build_queries(fixture_records, fixture_schema)
    assert len(queries) == 33 and queries.excluded == {"literal": 13, "special": 2}
    assert all(_inputs.c4_findings(q) == [] for q in queries)
    king = next(q for q in queries if q["qid"] == "cq:f:king-14#b1")
    example = next(x for x in data.load_jsonl("fixture/c4-items.jsonl") if x["kind"] == "c4-completion-query")
    same = ("fact_id", "relation", "arity", "model_arity", "target", "context", "candidate_universe", "split")
    assert {k: king[k] for k in same} == {k: example[k] for k in same}
    assert (king["id"], king["qset"]) == ("c4:cq:f:king-14#b1", "khg-completion")
    # goals, lifecycle records and special targets make no query; ordered stops are three queries
    assert not any(q["fact_id"] in ("g:who-1774", "m:sup-1") for q in queries)
    assert [q["target"]["bid"] for q in queries if q["fact_id"] == "f:route-1"] == ["b1", "b2", "b3", "b4"]
    fact_ids = [q["fact_id"] for q in queries]
    assert fact_ids == sorted(fact_ids) and len({q["qid"] for q in queries}) == 33


def test_build_queries_options(fixture_records, fixture_schema):
    core = completion.build_queries(fixture_records, fixture_schema, slots=("core",))
    assert all(q["target"]["slot"] == "core" for q in core)
    assert all(b["role"] != "replaces" for q in core for b in q["context"])
    with_literals = completion.build_queries(fixture_records, fixture_schema, literal_targets="include",
                                             qset="p3b-test", split="valid")
    assert len(with_literals) == 33 + 13 and with_literals.excluded == {"literal": 0, "special": 2}
    lit = next(q for q in with_literals if q["fact_id"] == "f:pop-łódź-2019" and q["target"]["role"] == "quantity")
    assert lit["candidate_universe"]["kind"] == "list"
    assert literal_node_id(lit["target"]["value"]["literal"]) in lit["candidate_universe"]["ids"]
    assert (lit["qset"], lit["split"]) == ("p3b-test", "valid")
    seen = completion.build_queries(fixture_records, fixture_schema, universe="seen_in_position")
    king = next(q for q in seen if q["qid"] == "cq:f:king-14#b1")
    # holder is position_held's primary subject: the universe is every entity seen as a subject or object
    assert king["candidate_universe"] == {"kind": "list", "ids": ["ex:KingOfFrance", "ex:LouisXIII", "ex:LouisXIV"]}
    claim = next(q for q in completion.build_queries(fixture_records, fixture_schema)
                 if q["fact_id"] == "f:claim-1" and q["target"]["role"] == "claim")
    assert claim["candidate_universe"] == {"kind": "list", "ids": ["f:born-louis14-paris", "f:born-scribe",
                                                                   "f:born-skłodowska-kraków",
                                                                   "f:born-skłodowska-warszawa"]}
    for bad in (dict(slots=("time",)), dict(literal_targets="only"), dict(universe="all"), dict(split="dev")):
        with pytest.raises(ValueError):
            completion.build_queries(fixture_records, fixture_schema, **bad)


def test_the_filter_index(fixture_records, fixture_schema):
    index = completion.FilterIndex.from_records(fixture_records, schema=fixture_schema)
    assert len(index) == 14 and index.split_of("f:king-14") == "train"
    queries = {q["qid"]: q for q in completion.build_queries(fixture_records, fixture_schema)}
    # a quoted fact is looked up by id but is no known answer: its own query finds nothing to filter
    quoted = queries["cq:f:born-louis14-paris#b1"]
    assert index.fact("f:born-louis14-paris")["status"] == "quoted"
    assert index.known_answers(quoted) == set() and index.known_answers(quoted, "time_aware") == set()
    assert index.fact("m:sup-1") is None and index.fact("g:who-1774") is None
    spouse = queries["cq:f:married-curie#b1"]
    assert index.known_answers(spouse) == {"ex:Maria_Skłodowska"}
    # the agent of a co-administration: the other agent's binding stays in the context
    agent = queries["cq:f:coadmin-1#b1"]
    assert index.known_answers(agent) == {"ex:insulin"}
    manifest = next(x for x in data.load_jsonl("fixture/c4-items.jsonl") if x["kind"] == "c4-split-manifest")
    split = completion.FilterIndex.from_records(fixture_records, schema=fixture_schema, manifest=manifest)
    assert split.split_of("f:king-14") == "test" and split.split_of("f:king-13") == "valid" and len(split) == 14
    with pytest.raises(ValueError):
        index.known_answers(agent, "fuzzy")
    with pytest.raises(ValueError):
        completion.FilterIndex.from_records(fixture_records, manifest={"kind": "c4-header"})


def test_without_a_schema_the_filter_is_the_full_tuple(fixture_records, fixture_schema):
    """The §1.3 call ``FilterIndex.from_records(train, valid, test)`` works without a schema: every binding of a
    known fact takes part (time included), and the query fact's own bindings are used when it is indexed."""
    index = completion.FilterIndex.from_records(fixture_records[:30], [], fixture_records[30:])
    queries = {q["qid"]: q for q in completion.build_queries(fixture_records, fixture_schema)}
    assert index.known_answers(queries["cq:f:king-14#b1"]) == {"ex:LouisXIV"}
    assert index.known_answers(queries["cq:f:married-curie#b1"]) == {"ex:Maria_Skłodowska"}
    with pytest.raises(ValueError):
        index.known_answers(queries["cq:f:king-14#b1"], "monotone")
    with pytest.raises(ValueError):
        index.known_answers(queries["cq:f:king-14#b1"], "time_aware")


def _records(queries, greater):
    return [{"kind": "completion-rank", "qid": q["qid"], "n_candidates": 50, "n_filtered_out": 1,
             "n_greater": g, "n_equal": e} for q, (g, e) in zip(queries, greater, strict=True)]


def test_presets(fixture_records, fixture_schema):
    queries = [q for q in completion.build_queries(fixture_records, fixture_schema)
               if q["fact_id"] in ("f:king-13", "f:king-14")]
    assert [q["target"]["role"] for q in queries] == ["holder", "position", "holder", "position", "replaces"]
    records = _records(queries, [(0, 1), (2, 0), (0, 3), (0, 0), (4, 1)])
    hype = completion.score(queries, records, config=config(preset="hype"))
    assert hype["config"]["effective"] == {"filter": "exact", "rank": "pessimistic"}
    assert hype["aggregate"]["headline"] == "per_task"
    assert hype["aggregate"]["per_task"]["mrr"] == pytest.approx((1 / 2 + 1 / 3 + 1 / 4 + 1 + 1 / 6) / 5)
    hyper = completion.score(queries, records, config=config(preset="hyper"))
    assert hyper["aggregate"]["per_task"] == hype["aggregate"]["per_task"]
    with pytest.raises(ValueError):
        completion.score(queries, records, config=config(preset="stare"))
    stare = completion.score(queries, records, config=config(preset="stare"), schema=fixture_schema)
    agg = stare["aggregate"]
    assert agg["n_queries"] == 4 and agg["headline"] == "stare"  # replaces is not a subject or object
    assert agg["stare"]["positions"]["subject"]["mrr"] == pytest.approx((1 / 2 + 1 / 4) / 2)
    assert agg["stare"]["positions"]["object"]["mrr"] == pytest.approx((1 / 3 + 1) / 2)
    assert agg["stare"]["mrr"] == pytest.approx(((1 / 2 + 1 / 4) / 2 + (1 / 3 + 1) / 2) / 2)
    assert agg["approximated"] == ["qualifier_order", "sort_order_ties"]
    with_order = [dict(r, model_rank=1 + r["n_greater"]) for r in records]
    exact_order = completion.score(queries, with_order, config=config(preset="stare"), schema=fixture_schema)
    assert exact_order["aggregate"]["approximated"] == ["qualifier_order"]
    assert exact_order["aggregate"]["stare"]["positions"]["subject"]["mrr"] == 1.0


def test_missing_and_unmatched_outputs(fixture_records, fixture_schema):
    queries = completion.build_queries([r for r in fixture_records if r["id"] == "f:king-14"], fixture_schema)
    records = _records(queries[:1], [(0, 0)]) + [{"kind": "completion-rank", "qid": "cq:elsewhere",
                                                   "n_candidates": 3, "n_filtered_out": 0, "n_greater": 0,
                                                   "n_equal": 0}]
    rep = completion.score(queries, records, config=config())
    agg = rep["aggregate"]
    assert (agg["n_queries"], agg["n_outputs"], agg["n_missing"], agg["n_unmatched_outputs"]) == (3, 1, 2, 1)
    assert agg["per_task"]["mrr"] == pytest.approx(1 / 3) and agg["per_task"]["mr"] == 1.0
    assert rep["items"][queries[1]["qid"]] == {"depends_on": ["f:king-14"], "fact_id": "f:king-14",
                                               "relation": "position_held", "role": "position", "missing": True,
                                               "rr": 0.0, "rank": None, "hits@1": 0.0, "hits@3": 0.0,
                                               "hits@10": 0.0}
    with pytest.raises(ValidationError) as e:
        completion.score(queries, records + records[:1], config=config())
    assert e.value.codes == ("KHG-C010",)
    inconsistent = _records(queries[:1], [(10, 0)])
    inconsistent[0]["n_candidates"] = 5
    with pytest.raises(ValidationError) as e:
        completion.score(queries, inconsistent, config=config())
    assert e.value.codes == ("KHG-C010",)


def test_a_model_rank_outside_the_tie_block_is_c010(fixture_records, fixture_schema):
    """``model_rank`` only orders the target's tie block [1 + n_greater, 1 + n_greater + n_equal] (§9.3), which
    ``rank_stats`` checks too: a record that ranks the target first although 49 candidates scored above it is C010,
    not an MRR of 1 (review f-scorers-05)."""
    queries = completion.build_queries([r for r in fixture_records if r["id"] == "f:king-14"], fixture_schema)[:1]
    assert queries[0]["qid"] == "cq:f:king-14#b1"
    record = {"kind": "completion-rank", "qid": "cq:f:king-14#b1", "n_candidates": 100, "n_filtered_out": 0,
              "n_greater": 49, "n_equal": 0, "model_rank": 1}
    for kw in (dict(config=config(rank="model")), dict(config=config(preset="stare"), schema=fixture_schema),
               dict(config=config())):
        with pytest.raises(ValidationError) as e:
            completion.score(queries, [record], **kw)
        assert e.value.codes == ("KHG-C010",)
        assert e.value.info["findings"][0]["path"] == "/cq:f:king-14#b1/model_rank"
    tied = dict(record, n_greater=1, n_equal=2)  # the tie block is [2, 4]
    for model_rank in (1, 5):
        with pytest.raises(ValidationError):
            completion.score(queries, [dict(tied, model_rank=model_rank)], config=config(rank="model"))
    for model_rank in (2, 3, 4):
        rep = completion.score(queries, [dict(tied, model_rank=model_rank)], config=config(rank="model"))
        assert rep["aggregate"]["per_task"]["mrr"] == 1 / model_rank


def test_every_per_arity_table_is_given_on_model_arity_too(fixture_records, fixture_schema):
    """DESIGN §9.1: every per-arity table is given on ``arity`` and on ``model_arity``. The fixture's facts with
    literals have a smaller model arity (the population fact: 3 and 1), so the two tables differ. Here their targets
    rank first with a right top-1, the others fifth with a wrong one, and every table is checked against its own
    bins (review f-scorers-09)."""
    queries = completion.build_queries(fixture_records, fixture_schema)
    good = {q["qid"] for q in queries if q["arity"] != q["model_arity"]}
    assert 0 < len(good) < len(queries)
    records = [{"kind": "completion-rank", "qid": q["qid"], "n_candidates": 20, "n_filtered_out": 0,
                "n_greater": 0 if q["qid"] in good else 4, "n_equal": 0,
                "top1": {"value": q["target"]["value"] if q["qid"] in good else {"entity": "ex:Nobody"}, "prob": 0.9}}
               for q in queries]
    rep = completion.score(queries, records, config=config(min_bin_queries=1))
    rr = {q["qid"]: F(1) if q["qid"] in good else F(1, 5) for q in queries}
    facts: dict[str, list] = {}
    for q in queries:
        facts.setdefault(q["fact_id"], []).append(q)
    tables = {}
    for kind in ("arity", "model_arity"):
        bins: dict[str, list] = {}
        for q in queries:
            bins.setdefault(arity_bin(q[kind]), []).append(q)
        by_arity, cal = rep["breakdowns"]["by_arity"][kind], rep["breakdowns"]["calibration_by_arity"][kind]
        assert set(by_arity) == set(cal) == set(bins), kind
        for b, qs in bins.items():
            assert by_arity[b]["n_queries"] == len(qs) == cal[b]["n"], (kind, b)
            assert by_arity[b]["mrr"] == float(sum(rr[q["qid"]] for q in qs) / len(qs)), (kind, b)
            assert cal[b]["accuracy"] == float(F(sum(q["qid"] in good for q in qs), len(qs))), (kind, b)
        per_bin: dict[str, list] = {}
        for qs in facts.values():  # macro over the bins of the per-fact means
            per_bin.setdefault(arity_bin(qs[0][kind]), []).append(sum(rr[q["qid"]] for q in qs) / len(qs))
        macro = rep["aggregate"][f"macro_{kind}"]
        assert macro["n_bins"] == len(per_bin), kind
        assert macro["mrr"] == float(sum(sum(v) / len(v) for v in per_bin.values()) / len(per_bin)), kind
        tables[kind] = (macro["n_bins"], macro["mrr"], sorted(by_arity))
    assert tables["arity"] != tables["model_arity"]  # (5 bins, 0.5886) against (4 bins, 0.45)


def test_adjusted_measures_and_the_audit(fixture_records, fixture_schema):
    queries = completion.build_queries([r for r in fixture_records if r["id"] == "f:king-14"], fixture_schema)
    records = [{"kind": "completion-rank", "qid": q["qid"], "n_candidates": 11, "n_filtered_out": 1,
                "n_greater": 0, "n_equal": 1} for q in queries]
    agg = completion.score(queries, records, config=config())["aggregate"]
    # 10 unfiltered candidates, target tied with one other: E[Hits@1] = 1/10 under random scoring
    assert agg["per_task"]["hits@1"] == 0.5 and agg["per_task"]["mr"] == 1.5
    assert agg["adjusted"]["hits@1"] == pytest.approx((0.5 - 0.1) / 0.9)
    assert agg["adjusted"]["amri"] == pytest.approx((1.5 - 5.5) / (1 - 5.5))
    assert agg["rank_audit"] == {"optimistic_mrr": 1.0, "pessimistic_mrr": 0.5, "realistic_mrr": pytest.approx(2 / 3),
                                 "tie_exact_mrr": 0.75}


def test_top1_correctness_accepts_known_answers_with_the_index(build, r05_schema):
    """C-M7: the top-1 is correct when it is any known-true filler, which only the filter index knows."""
    test = build.fact("f-test", "s", A="s0", B="t")
    other = build.fact("f-other", "s", A="s0", B="u")
    index = completion.FilterIndex.from_records([other], [], [test], schema=r05_schema)
    q = next(q for q in completion.build_queries([test], r05_schema) if q["target"]["role"] == "B")
    rec = completion.rank_stats(q, {"t:t": 0.3, "t:u": 0.6, "t:v": 0.1}, index, top1=("t:u", 0.6))
    without = completion.score([q], [rec], config=config())["aggregate"]["calibration"]
    with_index = completion.score([q], [rec], config=config(), index=index)["aggregate"]
    assert without["accuracy"] == 0.0 and with_index["calibration"]["accuracy"] == 1.0
    assert "top1_known_answers" not in with_index["approximated"]


def test_large_tie_blocks_use_the_harmonic_expansion(fixture_records, fixture_schema):
    queries = completion.build_queries([r for r in fixture_records if r["id"] == "f:king-14"], fixture_schema)[:1]
    records = [{"kind": "completion-rank", "qid": queries[0]["qid"], "n_candidates": 100000, "n_filtered_out": 0,
                "n_greater": 10, "n_equal": 50000}]
    rr = completion.score(queries, records, config=config())["aggregate"]["per_task"]["mrr"]
    exact = sum(1 / r for r in range(11, 50012)) / 50001
    assert rr == pytest.approx(exact, rel=1e-12)


def test_the_report(fixture_records, fixture_schema):
    queries = completion.build_queries([r for r in fixture_records if r["id"] == "f:king-14"], fixture_schema)
    records = _records(queries, [(0, 0), (1, 0), (0, 2)])
    rep = completion.score(queries, records)
    assert list(rep) == ["scorer", "config", "contracts", "aggregate", "breakdowns", "items", "bootstrap"]
    assert rep["config"]["qset"] == ["khg-completion"] and rep["config"]["filter"] == "exact"
    assert rep["bootstrap"]["unit"] == "query" and rep["bootstrap"]["n_units"] == 3
    assert set(rep["breakdowns"]) == {"filters", "by_arity", "by_role", "by_slot", "by_relation",
                                      "calibration_by_arity"}
    assert rep["breakdowns"]["by_slot"]["qualifier"]["n_queries"] == 1
    assert json.loads(json.dumps(rep)) == rep
    assert rep == completion.score(list(reversed(queries)), list(reversed(records)))


@pytest.mark.parametrize("bad", [dict(preset="kbgat"), dict(filter="all"), dict(rank="random"), dict(hits=(0,)),
                                 dict(ece_bins=0), dict(min_bin_queries=-1), dict(bootstrap=None)])
def test_the_configuration_is_checked(bad):
    with pytest.raises(ValueError):
        completion.CompletionConfig(**bad)


def test_lifecycle_records_and_goals_are_never_indexed(fixture_records):
    index = completion.FilterIndex.from_records(fixture_records)  # without a schema too
    assert index.fact("m:sup-1") is None and index.fact("g:who-1774") is None
    assert index.fact("f:born-skłodowska-kraków")["status"] == "superseded" and len(index) == 14
