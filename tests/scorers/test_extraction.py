"""The extraction scorer beyond the R05 tables (DESIGN §9.1-§9.3): runs and orders, deduplication, documents without
gold, redirects, the Ign variant, the presets, averages and the bootstrap."""
from __future__ import annotations

import json

import pytest

from khg_contracts.record import core_key
from khg_contracts.scorers import extraction
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
    assert rep["scorer"] == "extraction" and rep["contracts"]["khg-scorers"] == "1.0.0"
    assert rep["config"]["literal_match"] == "truncate_to_gold" and rep["config"]["seen"] == []
    assert rep["config"]["qset"] == ["r05"] and rep["config"]["schema"]["id"] == "r05-tables"
    assert json.loads(json.dumps(rep)) == rep


@pytest.mark.parametrize("bad", [dict(preset="docred"), dict(literal_match="fuzzy"), dict(calendar="julian"),
                                 dict(core_roles="primary"), dict(bootstrap=1000)])
def test_the_configuration_is_checked(bad):
    with pytest.raises(ValueError):
        extraction.ExtractionConfig(**bad)
