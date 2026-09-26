"""The extraction scorer beyond the R05 tables (DESIGN §9.1-§9.3): runs and orders, deduplication, documents without
gold, redirects, the Ign variant, the presets, averages, the E-M3 alignment over a document and the bootstrap."""
from __future__ import annotations

import itertools
import json
import random
from collections import Counter
from fractions import Fraction as F

import pytest

from khg_contracts import data
from khg_contracts.record import core_key
from khg_contracts.scorers import extraction, stability
from khg_contracts.scorers.bootstrap import Bootstrap

NO_BOOT = extraction.ExtractionConfig(bootstrap=Bootstrap(resamples=0))


def test_every_run_is_scored_against_every_document(build, r05_schema):
    f = build.fact
    gold = [build.doc("d1", [f("g1", "s", A="a", B="b")]), build.doc("d2", [f("g2", "s", A="c", B="d")])]
    items = [build.items(f("x", "s", A="a", B="b"), run="r1", order="o1", doc_id="d1"),
             build.items(f("x", "s", A="c", B="d"), run="r1", order="o1", doc_id="d2"),
             build.items(f("x", "s", A="a", B="b"), run="r2", order="o1", doc_id="d1"),
             build.items(f("x", "s", A="c", B="z"), run="r2", order="o1", doc_id="d2")]
    rep = extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)
    agg = rep["aggregate"]
    assert (agg["n_runs"], agg["n_docs"], agg["n_gold"]) == (2, 2, 2)
    assert agg["strict"] == {"p": 0.75, "r": 0.75, "f1": 0.75, "tp": 3, "n_pred": 4, "n_gold": 4, "flag": None}
    runs = rep["breakdowns"]["by_run"]
    assert [(r["run_id"], r["strict"]["f1"]) for r in runs] == [("r1", 1.0), ("r2", 0.5)]
    disp = rep["breakdowns"]["run_dispersion"]["strict_f1"]
    assert (disp["mean"], disp["min"], disp["max"], disp["n_runs"]) == (0.75, 0.5, 1.0, 2)
    assert rep["items"]["d2"]["runs"][1]["missed"] == ["g2"]
    assert rep["items"]["d2"]["runs"][1]["spurious"] == ["q:000004"]
    assert rep["items"]["d1"]["depends_on"] == ["g1"]


def test_duplicates_keep_the_smallest_id_and_order_does_not_matter(build, r05_schema):
    f = build.fact
    gold = [build.doc("d1", [f("g1", "s", A="a", B="b")])]
    items = [build.items(f("x", "s", A="a", B="b")) for _ in range(3)]
    forward = extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)
    backward = extraction.score(gold, list(reversed(items)), schema=r05_schema, config=NO_BOOT)
    assert forward == backward
    assert forward["aggregate"]["n_duplicates_removed"] == 2
    assert forward["items"]["d1"]["runs"][0]["matched"] == [["q:000001", "g1"]]


def test_documents_without_gold_are_not_scored(build, r05_schema):
    f = build.fact
    gold = [build.doc("d1", [f("g1", "s", A="a", B="b")])]
    items = [build.items(f("x", "s", A="a", B="b")), build.items(f("y", "s", A="q", B="r"), doc_id="elsewhere")]
    rep = extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)
    assert rep["aggregate"]["n_pred_unscored"] == 1 and rep["breakdowns"]["unscored_docs"] == ["elsewhere"]
    assert rep["aggregate"]["strict"]["p"] == 1.0


def test_entities_match_after_redirects(build, r05_schema):
    old = {"kind": "entity", "id": "t:old-a", "types": ["Thing"], "redirect_to": "t:a"}
    gold = [build.doc("d1", [build.fact("g1", "s", A="a", B="b")], entities=[old])]
    items = [build.items(build.fact("x", "s", A="old-a", B="b"))]
    assert extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)["aggregate"]["strict"]["tp"] == 1
    no_redirect = [build.doc("d1", [build.fact("g1", "s", A="a", B="b")])]
    assert extraction.score(no_redirect, items, schema=r05_schema, config=NO_BOOT)["aggregate"]["strict"]["tp"] == 0


BEE = {"kind": "entity", "id": "t:bee", "types": ["Thing"], "redirect_to": "t:b"}


def test_an_items_entity_records_resolve_only_its_own_values(build, r05_schema):
    """A prediction resolves through its own queue item's entity records, then the gold's (DESIGN §7's order), so one
    run's records never change another run's values, and the input order of the runs does not matter (review
    f-scorers-04: r2 scored 0 alone and 1 beside r1, and stability saw J(r1, r2) = 1 for different outputs)."""
    gold = [build.doc("d1", [build.fact("g1", "s", A="a", B="b")])]

    def by_run(items):
        rep = extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)
        return {r["run_id"]: r["strict"]["tp"] for r in rep["breakdowns"]["by_run"]}

    r1 = [build.items(build.fact("x", "s", A="a", B="b"), run="r1", entities=[BEE])]
    r2 = [build.items(build.fact("y", "s", A="a", B="bee"), run="r2")]
    assert by_run(r2) == {"r2": 0} and by_run(r1 + r2) == {"r1": 1, "r2": 0}
    agg = stability.score(r1 + r2, schema=r05_schema, keys=("content_key",))["aggregate"]["content_key"]
    assert agg["pairwise_jaccard"] == [0.0]
    # the run's own record redirects its value; a plain record of the same id in another run does not
    plain = {"kind": "entity", "id": "t:bee", "types": ["Thing"]}
    r1 = [build.items(build.fact("x", "s", A="a", B="bee"), run="r1", entities=[BEE])]
    r2 = [build.items(build.fact("y", "s", A="a", B="bee"), run="r2", entities=[plain])]
    assert by_run(r1 + r2) == by_run(r2 + r1) == {"r1": 1, "r2": 0}


def test_a_predictions_entity_records_never_rewrite_the_gold(build, r05_schema):
    """A record that redirects the gold's t:b to the predicted t:zzz resolves the prediction's values only, so a
    wrong value stays wrong in both scorers (review f-scorers-04)."""
    gold = [build.doc("d1", [build.fact("g1", "s", A="a", B="b")])]
    cheat = {"kind": "entity", "id": "t:b", "types": ["Thing"], "redirect_to": "t:zzz"}
    items = [build.items(build.fact("x", "s", A="a", B="zzz"), entities=[cheat])]
    assert extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)["aggregate"]["strict"]["tp"] == 0
    part = stability.score(items, schema=r05_schema, gold=gold)["aggregate"]["content_key"]["gold_partition"]
    assert (part["stable"], part["miss"]) == (0.0, 1.0)


def test_extraction_and_stability_resolve_entities_alike(build, r05_schema):
    """The gold document redirects t:old to t:a, and the prediction s(A: t:a, B: t:b) carries a plain t:old record.
    Gold resolves through the gold's records in both scorers, so both find the fact (stability used to read the
    prediction's record first and call it a miss; review f-scorers-04)."""
    redirect = {"kind": "entity", "id": "t:old", "types": ["Thing"], "redirect_to": "t:a"}
    plain = {"kind": "entity", "id": "t:old", "types": ["Thing"]}
    gold = [build.doc("d1", [build.fact("g1", "s", A="old", B="b")], entities=[redirect])]
    items = [build.items(build.fact("x", "s", A="a", B="b"), entities=[plain])]
    assert extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)["aggregate"]["strict"]["tp"] == 1
    part = stability.score(items, schema=r05_schema, gold=gold)["aggregate"]["content_key"]["gold_partition"]
    assert (part["stable"], part["miss"]) == (1.0, 0.0)


def test_the_ign_variant_drops_seen_core_keys(build, r05_schema):
    f = build.fact
    seen_fact = f("g1", "s", A="a", B="b")
    gold = [build.doc("d1", [seen_fact, f("g2", "s", A="c", B="d")])]
    items = [build.items(f("x", "s", A="a", B="b")), build.items(f("y", "s", A="c", B="z"))]
    config = extraction.ExtractionConfig(seen=[core_key(seen_fact, r05_schema)], bootstrap=Bootstrap(resamples=0))
    agg = extraction.score(gold, items, schema=r05_schema, config=config)["aggregate"]
    assert agg["strict"]["tp"] == 1 and agg["strict"]["p"] == 0.5
    ign = agg["ign"]
    assert (ign["n_gold_removed"], ign["n_pred_removed"]) == (1, 1)
    assert ign["strict"]["tp"] == 0 and ign["strict"]["n_gold"] == 1 and ign["arg_c"]["r"] == 0.5
    assert "ign" not in extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)["aggregate"]
    with pytest.raises(ValueError):
        extraction.ExtractionConfig(seen="sha256:abc")


def test_the_text2nkg_preset_compacts_predictions(build, fixture_schema):
    """Text2NKG merges predicted quintuplets that share (relation, subject, object) into one fact, then counts
    equal facts in a nested loop: two predictions of one king with different qualifiers become one fact."""
    def held(fid, replaces=None):
        bs = [("holder", {"entity": "ex:LouisXIV"}), ("position", {"entity": "ex:KingOfFrance"})]
        if replaces:
            bs.append(("replaces", {"entity": replaces}))
        return build.literal_fact(fid, "position_held", bs)

    gold = [build.doc("d1", [held("g1", "ex:LouisXIII")])]
    items = [build.items(held("p1")), build.items(held("p2", "ex:LouisXIII"))]
    config = extraction.ExtractionConfig(preset="text2nkg", bootstrap=Bootstrap(resamples=0))
    agg = extraction.score(gold, items, schema=fixture_schema, config=config)["aggregate"]
    assert agg["preset"]["unit"] == "fact" and agg["preset"]["n_pred"] == 1
    assert (agg["preset"]["tp"], agg["preset"]["p"], agg["preset"]["r"]) == (1, 1.0, 1.0)
    assert agg["preset"]["approximated"] == ["serialisation_order"]
    assert agg["strict"]["tp"] == 1 and agg["strict"]["n_pred"] == 2  # the C5 metrics are unchanged
    hyperred = extraction.ExtractionConfig(preset="hyperred_quintuplet", bootstrap=Bootstrap(resamples=0))
    q = extraction.score(gold, items, schema=fixture_schema, config=hyperred)["aggregate"]["preset"]
    assert (q["unit"], q["n_pred"], q["n_gold"], q["tp"]) == ("quintuplet", 2, 1, 1)


def test_the_presets_count_relations_without_primary_as_unmapped(build, r05_schema):
    gold = [build.doc("d1", [build.fact("g1", "s", A="a", B="b")])]
    items = [build.items(build.fact("x", "s", A="a", B="b"))]
    config = extraction.ExtractionConfig(preset="hyperred_quintuplet", bootstrap=Bootstrap(resamples=0))
    preset = extraction.score(gold, items, schema=r05_schema, config=config)["aggregate"]["preset"]
    assert (preset["n_unmapped_pred"], preset["n_unmapped_gold"], preset["flag"]) == (1, 1, "both_empty")


def test_macro_averages_and_model_arity(build, fixture_schema):
    """population's quantity and point in time are literals, so its model arity is 1 against an arity of 3; the
    per-arity tables are given on both. Macro over relations: born_in is found, population missed."""
    pop = build.literal_fact("g1", "population", [
        ("place", {"entity": "ex:Łódź"}),
        ("quantity", {"literal": {"datatype": "quantity", "amount": "+679941", "unit": "1"}}),
        ("point_in_time", build.time("+2019-00-00T00:00:00Z", 9))])
    born = build.literal_fact("g2", "born_in", [("person", {"entity": "ex:LouisXIV"}),
                                                ("birthplace", {"entity": "ex:Paris"})])
    gold = [build.doc("d1", [pop, born])]
    items = [build.items(born)]
    rep = extraction.score(gold, items, schema=fixture_schema, config=NO_BOOT)
    by_arity = rep["breakdowns"]["by_arity"]
    assert set(by_arity["arity"]) == {"2", "3"} and set(by_arity["model_arity"]) == {"0-1", "2"}
    assert by_arity["arity"]["3"]["strict"]["r"] == 0.0 and by_arity["model_arity"]["0-1"]["strict"]["r"] == 0.0
    macro = rep["aggregate"]["macro_relation"]["strict"]
    assert (macro["p"], macro["r"], macro["f1"], macro["n"]) == (1.0, 0.5, 0.5, 2)
    assert rep["breakdowns"]["by_relation"]["born_in"]["strict"]["f1"] == 1.0


FIXTURE_FACTS = {r["id"]: r for r in data.load_json("fixture/fixture.c1.json")["records"]
                 if r.get("kind") == "hyperedge"}


def test_the_macro_arity_average_is_given_on_model_arity_too(build, fixture_schema):
    """population (arity 3, model arity 1) is missed; king-14 (3, 3), claim-1 (3, 2) and born (2, 2) are found. The
    bins are {2, 3} on arity and {0-1, 2, 3} on model arity, so the two macro averages differ; in the test above
    both arities put the same facts in their bins (review f-scorers-09)."""
    def fact(fid):
        return dict(FIXTURE_FACTS[fid], status="asserted")  # the fixture quotes f:born-louis14-paris

    gold = [build.doc("d1", [fact(f) for f in ("f:pop-łódź-2019", "f:king-14", "f:claim-1", "f:born-louis14-paris")])]
    items = [build.items(fact(f)) for f in ("f:king-14", "f:claim-1", "f:born-louis14-paris")]
    rep = extraction.score(gold, items, schema=fixture_schema, config=NO_BOOT)
    macro = rep["aggregate"]["macro_arity"]
    assert macro["arity"]["strict"] == {"p": 1.0, "r": float(F(5, 6)), "f1": 0.9, "n": 2}
    assert macro["model_arity"]["strict"] == {"p": 1.0, "r": float(F(2, 3)), "f1": float(F(2, 3)), "n": 3}
    assert sorted(rep["breakdowns"]["by_arity"]["arity"]) == ["2", "3"]
    assert sorted(rep["breakdowns"]["by_arity"]["model_arity"]) == ["0-1", "2", "3"]
    assert rep["breakdowns"]["by_arity"]["model_arity"]["0-1"]["strict"]["r"] == 0.0


def _best_alignment(preds: list[dict[str, str]], golds: list[dict[str, str]]) -> tuple[int, int]:
    """The largest (Σν, Σβ), lexicographically, over every 1:1 alignment of one relation's facts (brute force). A
    fact is ``{role: value}``; ν counts the shared values (a multiset, roles ignored) and β the shared bindings."""
    def nu(p, g):
        return sum((Counter(p.values()) & Counter(g.values())).values())

    def beta(p, g):
        return len(set(p.items()) & set(g.items()))

    best = (0, 0)
    for k in range(1, min(len(preds), len(golds)) + 1):
        for rows in itertools.combinations(range(len(preds)), k):
            for cols in itertools.permutations(range(len(golds)), k):
                pairs = list(zip(rows, cols, strict=True))
                best = max(best, (sum(nu(preds[i], golds[j]) for i, j in pairs),
                                  sum(beta(preds[i], golds[j]) for i, j in pairs)))
    return best


EM3_CASES = {
    # the review's document (f-scorers-01): R05's pair weight (N + 1)·ν + β gives (Σν, Σβ) = (3, 3) and (4, 0) the
    # same total, 12, so the qids decided Arg-I, Arg-C and role accuracy
    "values_first": ("r", [dict(C="b", D="a"), dict(C="b", D="b"), dict(C="c", D="b"), dict(D="c", E="a")],
                     [dict(C="a", D="a"), dict(C="a", D="b"), dict(D="c", E="c")], (4, 0)),
    # found by a seeded search on r4, four core roles: (N + 1)·ν + β chose (9, 7) over (10, 2)
    "r4_search": ("r4", [dict(A="a", B="c", C="a", D="c"), dict(A="c", B="b", C="c", D="a"),
                         dict(A="c", B="c", C="b", D="a")],
                  [dict(A="a", B="a", C="b", D="c"), dict(A="b", B="c", C="b", D="c"),
                   dict(A="c", B="a", C="c", D="a")], (10, 2)),
}


@pytest.mark.parametrize("case", sorted(EM3_CASES))
def test_the_alignment_takes_values_then_bindings_over_the_document(case, build, r05_schema):
    """E-M3 aligns on values, then bindings (DESIGN §9.3): the largest Σν over the document, then the largest Σβ,
    whatever the submission order (so whatever the qids)."""
    relation, golds, preds, want = EM3_CASES[case]
    assert _best_alignment(preds, golds) == want
    gold = [build.doc("d1", [build.fact(f"g{j}", relation, **g) for j, g in enumerate(golds)])]
    for order in itertools.permutations(range(len(preds))):
        items = [build.items(build.fact("p", relation, **preds[i])) for i in order]
        agg = extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)["aggregate"]
        assert (agg["arg_i"]["tp"], agg["arg_c"]["tp"]) == want, order
        assert agg["role_accuracy"] == want[1] / want[0], order


def test_the_review_document_aligns_the_shared_values(build, r05_schema):
    """The (4, 0) alignment of the review's document: (C: a, D: b) takes g0 (two shared values), the others one value
    each; no role is right, so role accuracy is 0 in every order (it was 1 for two orders of six)."""
    relation, golds, preds, _ = EM3_CASES["values_first"]
    gold = [build.doc("d1", [build.fact(f"g{j}", relation, **g) for j, g in enumerate(golds)])]
    for order in itertools.permutations(range(3)):
        rep = extraction.score(gold, [build.items(build.fact("p", relation, **preds[i])) for i in order],
                               schema=r05_schema, config=NO_BOOT)
        aligned = rep["items"]["d1"]["runs"][0]["aligned"]
        assert sorted((a["gold"], a["nu"], a["beta"]) for a in aligned) == [("g0", 2, 0), ("g2", 1, 0), ("g3", 1, 0)]


def test_the_alignment_totals_are_the_brute_force_maximum(build, r05_schema):
    """On seeded random documents of r4 (every fact binds A, B, C and D), the alignment's (Σν, Σβ) is the
    lexicographic maximum over every 1:1 alignment."""
    rng = random.Random(20260924)
    for trial in range(80):
        def facts(n):
            out = {tuple(rng.choice("abc") for _ in "ABCD") for _ in range(n)}  # distinct, as the scorer dedups
            return [dict(zip("ABCD", x, strict=True)) for x in sorted(out)]
        golds, preds = facts(rng.randint(1, 4)), facts(rng.randint(1, 4))
        gold = [build.doc("d1", [build.fact(f"g{j}", "r4", **g) for j, g in enumerate(golds)])]
        items = [build.items(build.fact("p", "r4", **p)) for p in preds]
        agg = extraction.score(gold, items, schema=r05_schema, config=NO_BOOT)["aggregate"]
        assert (agg["arg_i"]["tp"], agg["arg_c"]["tp"]) == _best_alignment(preds, golds), trial


def test_the_bootstrap_resamples_documents(build, r05_schema):
    f = build.fact
    gold = [build.doc(f"d{n}", [f(f"g{n}", "s", A=f"a{n}", B="b")]) for n in range(6)]
    items = [build.items(f("x", "s", A=f"a{n}", B="b" if n % 2 else "wrong"), doc_id=f"d{n}") for n in range(6)]
    rep = extraction.score(gold, items, schema=r05_schema)
    boot = rep["bootstrap"]
    assert (boot["resamples"], boot["seed"], boot["alpha"], boot["unit"], boot["n_units"]) == (1000, 0, 0.05, "doc", 6)
    lo, hi = boot["intervals"]["strict.f1"]
    assert 0 <= lo <= rep["aggregate"]["strict"]["f1"] <= hi <= 1
    assert rep == extraction.score(gold, items, schema=r05_schema)  # the fixed seed makes it reproducible


def test_the_report_is_json_and_stamped(build, r05_schema):
    rep = extraction.score([build.doc("d1", [build.fact("g1", "s", A="a", B="b")])],
                           [build.items(build.fact("x", "s", A="a", B="b"))], schema=r05_schema, config=NO_BOOT)
    assert list(rep) == ["scorer", "config", "contracts", "aggregate", "breakdowns", "items", "bootstrap"]
    assert rep["scorer"] == "extraction" and rep["contracts"]["khg-scorers"] == "1.1.0"
    assert rep["config"]["literal_match"] == "truncate_to_gold" and rep["config"]["seen"] == []
    assert rep["config"]["qset"] == ["r05"] and rep["config"]["schema"]["id"] == "r05-tables"
    assert json.loads(json.dumps(rep)) == rep


@pytest.mark.parametrize("bad", [dict(preset="docred"), dict(literal_match="fuzzy"), dict(calendar="julian"),
                                 dict(core_roles="primary"), dict(bootstrap=1000)])
def test_the_configuration_is_checked(bad):
    with pytest.raises(ValueError):
        extraction.ExtractionConfig(**bad)
