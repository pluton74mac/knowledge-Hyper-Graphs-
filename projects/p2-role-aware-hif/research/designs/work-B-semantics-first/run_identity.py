"""Classifies every identity case of R01 section 6 (and extra edge cases) under the design's semantics."""
import copy, json, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from khg_proto import Schema, relate, resolve, presumed_interval, key_digest, derived

TIME = [{"literal": "time"}]


def U(role, slot, fillers, mn, mx, **kw):
    u = {"role": role, "slot": slot, "fillers": fillers, "min": mn, "max": mx}
    u.update(kw)
    return u


ANY = [{"entity": []}]
IV = {"model": "interval", "start": "start_time", "end": "end_time"}
TR = [U("start_time", "time", TIME, 0, 1), U("end_time", "time", TIME, 0, 1)]


def schema(relations):
    return Schema({"khg_schema": "khg-schema/1.0.0", "id": "identity-cases", "version": "1.0.0", "roles": [], "relations": relations})


REL = {
    "position_held": {"id": "position_held", "time": IV, "key": {"roles": ["position"], "temporal": True, "on_collision": "close_older"},
                      "roles": [U("holder", "core", ANY, 1, 1), U("position", "core", ANY, 1, 1)] + TR},
    "treats_req": {"id": "treats", "roles": [U("drug", "core", ANY, 1, 1), U("condition", "core", ANY, 1, 1), U("population", "core", ANY, 1, 1)]},
    "treats_qual": {"id": "treats", "roles": [U("drug", "core", ANY, 1, 1), U("condition", "core", ANY, 1, 1), U("population", "qualifier", ANY, 0, 1)]},
    "population": {"id": "population", "time": {"model": "invariant"}, "key": {"roles": ["place", "point_in_time"], "temporal": False, "on_collision": "dispute"},
                   "roles": [U("place", "core", ANY, 1, 1), U("quantity", "core", [{"literal": "quantity"}], 1, 1), U("point_in_time", "qualifier", TIME, 0, 1)]},
    "population_naive": {"id": "population", "time": {"model": "invariant"}, "key": {"roles": ["place"], "temporal": False, "on_collision": "dispute"},
                         "roles": [U("place", "core", ANY, 1, 1), U("quantity", "core", [{"literal": "quantity"}], 1, 1), U("point_in_time", "qualifier", TIME, 0, 1)]},
    "defeated": {"id": "defeated", "time": {"model": "invariant"}, "key": {"roles": ["event"], "temporal": False, "on_collision": "dispute"},
                 "roles": [U("winner", "core", ANY, 1, 1), U("loser", "core", ANY, 1, 1), U("event", "qualifier", ANY, 0, 1)]},
    "spouse": {"id": "spouse", "time": IV, "roles": [U("person", "core", ANY, 1, 1), U("spouse", "core", ANY, 1, 1)] + TR},
    "spouse_keyed": {"id": "spouse", "time": IV, "key": {"roles": ["person"], "temporal": True, "on_collision": "close_older"},
                     "roles": [U("person", "core", ANY, 1, 1), U("spouse", "core", ANY, 1, 1)] + TR},
    "ceo": {"id": "chief_executive", "time": IV, "key": {"roles": ["organisation"], "temporal": True, "on_collision": "close_older"},
            "roles": [U("organisation", "core", ANY, 1, 1), U("person", "core", ANY, 1, 1)] + TR},
    "catalysed_by": {"id": "catalysed_by", "roles": [U("reaction", "core", ANY, 1, 1), U("catalyst", "core", ANY, 1, None)]},
    "committee_complete": {"id": "committee", "time": IV, "key": {"roles": ["body"], "temporal": True, "on_collision": "close_older"},
                           "roles": [U("body", "core", ANY, 1, 1), U("member", "core", ANY, 1, None, complete=True)] + TR},
    "committee_open": {"id": "committee", "time": IV, "key": {"roles": ["body"], "temporal": True, "on_collision": "close_older"},
                       "roles": [U("body", "core", ANY, 1, 1), U("member", "core", ANY, 1, None)] + TR},
    "founding": {"id": "founding", "time": {"model": "invariant"},
                 "roles": [U("founder", "core", ANY, 1, None), U("organisation", "core", ANY, 1, 1), U("point_in_time", "qualifier", TIME, 0, 1), U("location", "qualifier", ANY, 0, 1)]},
    "treats_src": {"id": "treats", "roles": [U("drug", "core", ANY, 1, 1), U("condition", "core", ANY, 1, 1), U("source", "qualifier", ANY, 0, None)]},
    "rel_ab": {"id": "rel", "roles": [U("a", "core", ANY, 1, 1), U("b", "core", ANY, 1, 1)]},
    "co_authors": {"id": "co_authors", "roles": [U("author", "core", ANY, 2, None)]},
    "award": {"id": "award_received", "time": {"model": "invariant"}, "roles": [U("recipient", "core", ANY, 1, 1), U("award", "core", ANY, 1, 1), U("point_in_time", "qualifier", TIME, 0, 1)]},
    "route_complete": {"id": "route", "roles": [U("stop", "core", ANY, 2, None, ordered=True, complete=True)]},
    "route_open": {"id": "route", "roles": [U("stop", "core", ANY, 2, None, ordered=True)]},
}


def F(rel, *bs, id="x", status="asserted"):
    return {"kind": "fact", "id": id, "relation": rel, "status": status,
            "bindings": [dict({"bid": f"b{i+1}"}, **b) for i, b in enumerate(bs)]}


def B(role, v, pos=None):
    d = {"role": role, "value": v}
    if pos:
        d["position"] = pos
    return d


def e(i): return {"entity": i}
def t(s, p): return {"literal": {"datatype": "time", "time": s, "precision": p}}
def q(a): return {"literal": {"datatype": "quantity", "amount": a, "unit": "1"}}
SV, NV = {"special": "somevalue"}, {"special": "novalue"}
D = lambda y, m, d: t(f"+{y:04d}-{m:02d}-{d:02d}T00:00:00Z", 11)
Y = lambda y: t(f"+{y:04d}-00-00T00:00:00Z", 9)

CASES = [
    # (id, R01 ref, description, schema key, existing, incoming)
    ("C1", "§6.1 case 1", "refinement: dates added to an undated position", "position_held",
     F("position_held", B("holder", e("LouisXIV")), B("position", e("KingOfFrance"))),
     F("position_held", B("holder", e("LouisXIV")), B("position", e("KingOfFrance")), B("start_time", D(1643, 5, 14)), B("end_time", D(1715, 9, 1)))),
    ("C1r", "§6.1 case 1, other order", "the undated report arrives second", "position_held",
     F("position_held", B("holder", e("LouisXIV")), B("position", e("KingOfFrance")), B("start_time", D(1643, 5, 14)), B("end_time", D(1715, 9, 1))),
     F("position_held", B("holder", e("LouisXIV")), B("position", e("KingOfFrance")))),
    ("C1c-i", "§6.1 counter-case, population required core", "stored with population=somevalue (the only asserted form), then specified", "treats_req",
     F("treats", B("drug", e("metformin")), B("condition", e("T2DM")), B("population", SV)),
     F("treats", B("drug", e("metformin")), B("condition", e("T2DM")), B("population", e("adults")))),
    ("C1c-ii", "§6.1 counter-case, population as qualifier", "population added as a qualifier", "treats_qual",
     F("treats", B("drug", e("metformin")), B("condition", e("T2DM"))),
     F("treats", B("drug", e("metformin")), B("condition", e("T2DM")), B("population", e("adults")))),
    ("C2a", "§6.2 case 2a", "population, key {place, point_in_time}, two census years", "population",
     F("population", B("place", e("CityX")), B("quantity", q("+1000")), B("point_in_time", Y(2019))),
     F("population", B("place", e("CityX")), B("quantity", q("+1200")), B("point_in_time", Y(2023)))),
    ("C2a-naive", "§6.2 case 2a with a naive key", "same pair under key {place}", "population_naive",
     F("population", B("place", e("CityX")), B("quantity", q("+1000")), B("point_in_time", Y(2019))),
     F("population", B("place", e("CityX")), B("quantity", q("+1200")), B("point_in_time", Y(2023)))),
    ("C2b", "§6.2 case 2b", "roles swapped, different events", "defeated",
     F("defeated", B("winner", e("P")), B("loser", e("Q")), B("event", e("E1"))),
     F("defeated", B("winner", e("Q")), B("loser", e("P")), B("event", e("E2")))),
    ("C2b'", "§6.2 case 2b without events", "roles swapped, no event qualifier", "defeated",
     F("defeated", B("winner", e("P")), B("loser", e("Q"))),
     F("defeated", B("winner", e("Q")), B("loser", e("P")))),
    ("C2c", "§6.2 case 2c", "same couple, disjoint periods, no key", "spouse",
     F("spouse", B("person", e("P")), B("spouse", e("Q")), B("start_time", Y(1990)), B("end_time", Y(1995))),
     F("spouse", B("person", e("P")), B("spouse", e("Q")), B("start_time", Y(2001)))),
    ("C2c-k", "§6.2 case 2c, keyed", "same couple, disjoint periods, key {person} temporal", "spouse_keyed",
     F("spouse", B("person", e("P")), B("spouse", e("Q")), B("start_time", Y(1990)), B("end_time", Y(1995))),
     F("spouse", B("person", e("P")), B("spouse", e("Q")), B("start_time", Y(2001)))),
    ("C3a", "§6.3 case 3a", "new CEO from a later date, older open-ended", "ceo",
     F("chief_executive", B("organisation", e("O")), B("person", e("X")), B("start_time", D(2019, 1, 1))),
     F("chief_executive", B("organisation", e("O")), B("person", e("Y")), B("start_time", D(2021, 6, 1)))),
    ("C3b", "§6.3 case 3b", "two CEOs claiming the same start", "ceo",
     F("chief_executive", B("organisation", e("O")), B("person", e("X")), B("start_time", D(2019, 1, 1))),
     F("chief_executive", B("organisation", e("O")), B("person", e("Y")), B("start_time", D(2019, 1, 1)))),
    ("C3c", "§6.3 case 3c", "no catalyst vs a catalyst", "catalysed_by",
     F("catalysed_by", B("reaction", e("R")), B("catalyst", NV)),
     F("catalysed_by", B("reaction", e("R")), B("catalyst", e("C")))),
    ("C4a", "§6.4 case 4a (option ii)", "committee gains a member on 2025-03-01; member role complete", "committee_complete",
     F("committee", B("body", e("C")), B("member", e("m1")), B("member", e("m2")), B("member", e("m3")), B("start_time", D(2024, 1, 1))),
     F("committee", B("body", e("C")), B("member", e("m1")), B("member", e("m2")), B("member", e("m3")), B("member", e("m4")), B("start_time", D(2025, 3, 1)))),
    ("C4a-u", "§6.4 case 4a, undated reports", "undated 3-member vs 4-member composition; member role complete", "committee_complete",
     F("committee", B("body", e("C")), B("member", e("m1")), B("member", e("m2")), B("member", e("m3"))),
     F("committee", B("body", e("C")), B("member", e("m1")), B("member", e("m2")), B("member", e("m3")), B("member", e("m4")))),
    ("C4a-o", "§6.4 case 4a, undated, open role", "same pair, member role NOT complete (reads 'includes')", "committee_open",
     F("committee", B("body", e("C")), B("member", e("m1")), B("member", e("m2")), B("member", e("m3"))),
     F("committee", B("body", e("C")), B("member", e("m1")), B("member", e("m2")), B("member", e("m3")), B("member", e("m4")))),
    ("C4b", "§6.4 case 4b", "founding: binary report, then with date and place", "founding",
     F("founding", B("founder", e("Musk")), B("organisation", e("SpaceX"))),
     F("founding", B("founder", e("Musk")), B("organisation", e("SpaceX")), B("point_in_time", Y(2002)), B("location", e("Hawthorne")))),
    ("I5", "§6.5 I5", "paraphrase: same content, different sentence", "rel_ab",
     F("rel", B("a", e("X")), B("b", e("Y"))), F("rel", B("a", e("X")), B("b", e("Y")))),
    ("I6", "§6.5 I6 (bad schema)", "provenance modelled as a role 'source'", "treats_src",
     F("treats", B("drug", e("metformin")), B("condition", e("T2DM")), B("source", e("doc1"))),
     F("treats", B("drug", e("metformin")), B("condition", e("T2DM")), B("source", e("doc2")))),
    ("I7", "§6.5 I7", "same member set, roles exchanged", "rel_ab",
     F("rel", B("a", e("X")), B("b", e("Y"))), F("rel", B("a", e("Y")), B("b", e("X")))),
    ("I8", "§6.5 I8", "permuted fillers of an interchangeable role", "co_authors",
     F("co_authors", B("author", e("A")), B("author", e("B")), B("author", e("C"))),
     F("co_authors", B("author", e("C")), B("author", e("A")), B("author", e("B")))),
    ("I11", "§6.5 I11", "year-precision date then day-precision date", "award",
     F("award_received", B("recipient", e("E")), B("award", e("N")), B("point_in_time", Y(1921))),
     F("award_received", B("recipient", e("E")), B("award", e("N")), B("point_in_time", D(1921, 5, 2)))),
    ("I11-x", "§6.5 I11, contradicting days", "two different days", "award",
     F("award_received", B("recipient", e("E")), B("award", e("N")), B("point_in_time", D(1921, 5, 2))),
     F("award_received", B("recipient", e("E")), B("award", e("N")), B("point_in_time", D(1921, 6, 2)))),
    ("I12", "§6.5 I12", "somevalue, then a witness", "spouse",
     F("spouse", B("person", e("P")), B("spouse", SV)), F("spouse", B("person", e("P")), B("spouse", e("Q")))),
    ("I14", "§6.5 I14", "same main triple, different point_in_time, no key", "award",
     F("award_received", B("recipient", e("E")), B("award", e("N")), B("point_in_time", Y(1921))),
     F("award_received", B("recipient", e("E")), B("award", e("N")), B("point_in_time", Y(1922)))),
    ("X1", "extra", "year-precision handover (X until 2021, Y since 2021)", "ceo",
     F("chief_executive", B("organisation", e("O")), B("person", e("X")), B("start_time", Y(2019)), B("end_time", Y(2021))),
     F("chief_executive", B("organisation", e("O")), B("person", e("Y")), B("start_time", Y(2021)))),
    ("X2", "extra", "older CEO already has an end that overlaps the newer", "ceo",
     F("chief_executive", B("organisation", e("O")), B("person", e("X")), B("start_time", D(2019, 1, 1)), B("end_time", D(2023, 1, 1))),
     F("chief_executive", B("organisation", e("O")), B("person", e("Y")), B("start_time", D(2021, 6, 1)))),
    ("X3", "extra", "two undated CEO claims", "ceo",
     F("chief_executive", B("organisation", e("O")), B("person", e("X"))),
     F("chief_executive", B("organisation", e("O")), B("person", e("Y")))),
    ("X4", "extra", "backfill: an older, open-ended CEO arrives after the newer", "ceo",
     F("chief_executive", B("organisation", e("O")), B("person", e("Y")), B("start_time", D(2021, 6, 1))),
     F("chief_executive", B("organisation", e("O")), B("person", e("X")), B("start_time", D(2019, 1, 1)))),
    ("X5", "extra", "novalue vs somevalue", "catalysed_by",
     F("catalysed_by", B("reaction", e("R")), B("catalyst", NV)), F("catalysed_by", B("reaction", e("R")), B("catalyst", SV))),
    ("X6", "extra", "ordered complete route: a stop appended", "route_complete",
     F("route", B("stop", e("YYZ"), 1), B("stop", e("YUL"), 2)), F("route", B("stop", e("YYZ"), 1), B("stop", e("YUL"), 2), B("stop", e("YYZ"), 3))),
    ("X7", "extra", "ordered open route: a stop appended", "route_open",
     F("route", B("stop", e("YYZ"), 1), B("stop", e("YUL"), 2)), F("route", B("stop", e("YYZ"), 1), B("stop", e("YUL"), 2), B("stop", e("YYZ"), 3))),
    ("X8", "extra", "ordered route: stops reordered", "route_open",
     F("route", B("stop", e("YYZ"), 1), B("stop", e("YUL"), 2)), F("route", B("stop", e("YUL"), 1), B("stop", e("YYZ"), 2))),
    ("X9", "extra", "undated marriage vs a dated one (one candidate target)", "spouse",
     F("spouse", B("person", e("P")), B("spouse", e("Q")), B("start_time", Y(1990)), B("end_time", Y(1995))),
     F("spouse", B("person", e("P")), B("spouse", e("Q")))),
]

POL = [("ceo", "supersede"), ("ceo", "dispute"), ("ceo", "reject")]

if __name__ == "__main__":
    out = []
    for cid, ref, desc, sk, ex, new in CASES:
        S = schema([REL[sk]])
        rel, outcome = resolve(S, copy.deepcopy(new), copy.deepcopy(ex))
        dn, de = derived(S, new), derived(S, ex)
        row = {"id": cid, "ref": ref, "desc": desc, "schema": sk, "relation": rel, "outcome": outcome,
               "arity": f"{de['arity']}->{dn['arity']}", "vt": f"{de['valid_time']['kind']}->{dn['valid_time']['kind']}",
               "same_core_key": dn["core_key"] == de["core_key"], "same_key": (dn["key_digest"] == de["key_digest"]) if dn["key_digest"] else None}
        out.append(row)
        print(f"{cid:8} {rel:18} arity {row['arity']:6} vt {row['vt']:18} core_key= {str(row['same_core_key']):5} key= {str(row['same_key']):5} | {outcome}")
    print("-- policy variants of C3a (key {organisation}, temporal):")
    ex, new = CASES[10][4], CASES[10][5]
    for sk, pol in POL:
        r = copy.deepcopy(REL[sk]); r["key"]["on_collision"] = pol
        rel, outcome = resolve(schema([r]), new, ex)
        print(f"   on_collision={pol:10} -> {rel}: {outcome}")
        out.append({"id": f"C3a-{pol}", "relation": rel, "outcome": outcome})
    # X9 at store level: an undated marriage against two dated marriages
    S = schema([REL["spouse"]])
    m1 = F("spouse", B("person", e("P")), B("spouse", e("Q")), B("start_time", Y(1990)), B("end_time", Y(1995)), id="m1")
    m2 = F("spouse", B("person", e("P")), B("spouse", e("Q")), B("start_time", Y(2001)), id="m2")
    und = F("spouse", B("person", e("P")), B("spouse", e("Q")), id="n")
    print("-- store-level: undated marriage vs {m1 1990-1995, m2 2001-}:", [relate(S, und, m)[0] for m in (m1, m2)], "=> ambiguous generalisation: needs_review")
    json.dump(out, open(HERE / "identity-results.json", "w"), indent=1)
