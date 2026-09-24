"""The C1-semantics tests of DESIGN §9.7: the monotone filter is ⊑; ``truncate_to_gold`` is value refinement and
holds across calendars; E12 (core F1 against key roles). The Hungarian and bootstrap checks are in
test_hungarian.py and test_bootstrap.py."""
from __future__ import annotations

import itertools
import random

from khg_contracts import data
from khg_contracts.record import canonical_value, fact_refines, identity_key, value_refines
from khg_contracts.scorers import completion, extraction
from khg_contracts.scorers._facts import Binding, Matcher
from khg_contracts.scorers.bootstrap import Bootstrap

NO_BOOT = Bootstrap(resamples=0)


def _binding(value):
    return Binding("x", None, canonical_value(value), "literal", identity_key(value))


def test_the_monotone_filter_is_refinement(fixture_schema):
    """For every query built from the fixture, the monotone known answers are exactly the values c for which some
    indexed fact refines the completed query f[ρ←c] (checked by brute force over all facts and values)."""
    records = data.load_json("fixture/fixture.c1.json")["records"]
    index = completion.FilterIndex.from_records(records, schema=fixture_schema)
    queries = completion.build_queries(records, fixture_schema)
    facts = [r for r in records if r["kind"] == "hyperedge" and r["status"] in ("asserted", "disputed")
             and not r["relation"].startswith("khg:")]
    values = {b["value"]["entity"] for r in facts for b in r["bindings"] if "entity" in b["value"]}
    assert len(queries) == 33 and len(index) == len(facts) == 14
    by_id = {r["id"]: r for r in records}
    checked = 0
    for q in queries:
        if "entity" not in q["target"]["value"]:
            continue
        own = next(b for b in by_id[q["fact_id"]]["bindings"] if b["bid"] == q["target"]["bid"])
        position = {"position": own["position"]} if "position" in own else {}  # an ordered role keeps its slot
        want = set()
        for c in values:
            completed = {"kind": "hyperedge", "relation": q["relation"],
                         "bindings": q["context"] + [{"bid": "b0", "role": q["target"]["role"],
                                                      "value": {"entity": c}, **position}]}
            if any(fact_refines(g, completed, fixture_schema) for g in facts if g["relation"] == q["relation"]):
                want.add(c)
        got = index.known_answers(q, "monotone")
        assert got == want, q["qid"]
        assert index.known_answers(q, "exact") <= got
        checked += 1
    assert checked >= 20


def test_monotone_accepts_a_more_precise_qualifier(build, fixture_schema):
    """A known claim dated 1700-05-01 (day) refines the query's 1700 (year): monotone filters its claimant, exact
    does not."""
    claim = {"fact": "f:born-louis14-paris"}

    def claims(fid, who, when):
        return build.literal_fact(fid, "claims", [("claimant", {"entity": who}), ("claim", claim),
                                                  ("point_in_time", when)])

    test = claims("f:test", "ex:A", build.time("+1700-00-00T00:00:00Z", 9, "julian"))
    known = claims("f:known", "ex:B", build.time("+1700-05-01T00:00:00Z", 11, "julian"))
    coarser = claims("f:coarser", "ex:C", build.time("+1700-00-00T00:00:00Z", 7, "julian"))
    index = completion.FilterIndex.from_records([known, coarser], [], [test], schema=fixture_schema)
    q = next(q for q in completion.build_queries([test], fixture_schema) if q["target"]["role"] == "claimant")
    assert index.known_answers(q, "exact") == {"ex:A"}
    assert index.known_answers(q, "monotone") == {"ex:A", "ex:B"}  # a coarser date does not refine the query
    assert fact_refines(known, dict(test, bindings=[b if b["role"] != "claimant" else
                                                    dict(b, value={"entity": "ex:B"}) for b in test["bindings"]]),
                        fixture_schema)


def _time_literals():
    rng = random.Random(11)
    out = []
    for _ in range(60):
        year = rng.choice([1582, 1583, 1700, 1921, -44])
        month, day = rng.randint(1, 12), rng.randint(1, 28)
        precision = rng.choice([7, 9, 10, 11])
        calendar = rng.choice(["gregorian", "julian"])
        sign = "-" if year < 0 else "+"
        y = f"{abs(year):04d}"
        text = {7: f"{sign}{y}-00-00T00:00:00Z", 9: f"{sign}{y}-00-00T00:00:00Z",
                10: f"{sign}{y}-{month:02d}-00T00:00:00Z", 11: f"{sign}{y}-{month:02d}-{day:02d}T00:00:00Z"}[precision]
        out.append({"literal": {"datatype": "time", "time": text, "precision": precision, "calendar": calendar}})
    quantities = [{"literal": {"datatype": "quantity", "amount": a, "unit": "1", **b}}
                  for a, b in [("+3.5", {}), ("+3.5", {"lower": "+3", "upper": "+4"}), ("+3", {}),
                               ("+3.6", {"lower": "+3.5", "upper": "+3.7"})]]
    return out + quantities


def test_truncate_to_gold_is_value_refinement():
    """For time literals across precisions and both calendars, and for quantities with bounds, the literal rule
    ``truncate_to_gold`` agrees with ``record.value_refines`` (prediction ⊑ gold), and ``exact`` with identity."""
    lits = _time_literals()
    truncate, exact = Matcher("truncate_to_gold"), Matcher("exact")
    agree = 0
    for p, g in itertools.product(lits, repeat=2):
        bp, bg = _binding(p), _binding(g)
        assert truncate.values(bp, bg) == value_refines(p, g)
        assert exact.values(bp, bg) == (identity_key(p) == identity_key(g))
        agree += truncate.values(bp, bg)
    assert agree > len(lits)  # more than the diagonal: refinement relates distinct literals


def test_one_day_in_two_calendars_is_one_value(build, fixture_schema):
    """Julian 1582-10-05 and Gregorian 1582-10-15 are one identity: both rules match them (DESIGN §2.3, §9.1)."""
    def pop(fid, when):
        return build.literal_fact(fid, "population", [
            ("place", {"entity": "ex:Kraków"}),
            ("quantity", {"literal": {"datatype": "quantity", "amount": "+1000", "unit": "1"}}),
            ("point_in_time", when)])

    gold = pop("g", build.time("+1582-10-05T00:00:00Z", 11, "julian"))
    pred = pop("p", build.time("+1582-10-15T00:00:00Z", 11, "gregorian"))
    for rule in ("truncate_to_gold", "exact"):
        config = extraction.ExtractionConfig(literal_match=rule, bootstrap=NO_BOOT)
        rep = extraction.score([build.doc("d1", [gold])], [build.items(pred)], schema=fixture_schema, config=config)
        assert rep["aggregate"]["strict"]["tp"] == 1, rule


def test_as_written_reads_a_prediction_in_the_gold_calendar(build, fixture_schema):
    """Gold: the Julian year 1700 ([+1700-01-11, +1701-01-12) on the Gregorian line). A prediction written
    1700-01-05 as Gregorian lies before it; read as written in the gold's calendar it lies inside."""
    def pop(fid, when):
        return build.literal_fact(fid, "population", [
            ("place", {"entity": "ex:Łódź"}),
            ("quantity", {"literal": {"datatype": "quantity", "amount": "+1000", "unit": "1"}}),
            ("point_in_time", when)])

    gold = pop("g", build.time("+1700-00-00T00:00:00Z", 9, "julian"))
    early = pop("p", build.time("+1700-01-05T00:00:00Z", 11, "gregorian"))
    late = pop("p", build.time("+1700-06-15T00:00:00Z", 11, "gregorian"))

    def tp(pred, calendar):
        config = extraction.ExtractionConfig(calendar=calendar, bootstrap=NO_BOOT)
        rep = extraction.score([build.doc("d1", [gold])], [build.items(pred)], schema=fixture_schema, config=config)
        return rep["aggregate"]["strict"]["tp"]

    assert tp(early, "strict") == 0 and tp(early, "as_written") == 1
    assert tp(late, "strict") == 1 and tp(late, "as_written") == 1


def test_e12_core_against_key_roles(build, fixture_schema):
    """E12: population of Łódź, gold +679941 and prediction +685285, same point in time. The core slot (place,
    quantity) differs, so core F1 is 0; the key (place, point_in_time) agrees, so core F1 is 1 under
    ``core_roles="key"``."""
    def pop(fid, amount):
        return build.literal_fact(fid, "population", [
            ("place", {"entity": "ex:Łódź"}),
            ("quantity", {"literal": {"datatype": "quantity", "amount": amount, "unit": "1"}}),
            ("point_in_time", build.time("+2019-00-00T00:00:00Z", 9))])

    gold, pred = pop("f:pop-łódź-2019", "+679941"), pop("p", "+685285")
    for core_roles, want in (("slot", 0.0), ("key", 1.0)):
        config = extraction.ExtractionConfig(core_roles=core_roles, bootstrap=NO_BOOT)
        agg = extraction.score([build.doc("d1", [gold])], [build.items(pred)], schema=fixture_schema,
                               config=config)["aggregate"]
        assert agg["core"]["f1"] == want, core_roles
        assert agg["strict"]["f1"] == 0.0
        assert agg["arg_c"]["tp"] == 2 and agg["role_accuracy"] == 1.0
