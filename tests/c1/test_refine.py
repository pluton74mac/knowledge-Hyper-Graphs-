"""W3: the refinement order on values and facts (DESIGN §2.3, §2.9)."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, record
from khg_contracts.errors import ValidationError
from khg_contracts.schema import load_schema

S = load_schema(data.path("fixture/fixture.relation-schema.json"))
C1 = data.load_json("fixture/fixture.c1.json")
FACTS = {r["id"]: r for r in C1["records"] if r["kind"] == "hyperedge"}


def T(time, precision, calendar="gregorian"):
    return {"literal": {"datatype": "time", "time": time, "precision": precision, "calendar": calendar}}


def Q(amount, lower=None, upper=None, unit="1"):
    lit = {"datatype": "quantity", "amount": amount, "unit": unit}
    if lower is not None:
        lit.update(lower=lower, upper=upper)
    return {"literal": lit}


def G(lat, lon, precision, globe="wd:Q2"):
    return {"literal": {"datatype": "geo", "lat": lat, "lon": lon, "precision": precision, "globe": globe}}


def S_(value):
    return {"literal": {"datatype": "string", "value": value}}


E = {"entity": "ex:Paris"}
SV, NV, UNB = {"special": "somevalue"}, {"special": "novalue"}, {"unbound": {"var": "x"}}

# (a, b, a ⊑ b, b ⊑ a)
VALUE_CASES = [
    # time: the window inside and the precision at least as fine, whatever the calendars
    (T("+1643-05-14T00:00:00Z", 11), T("+1643-00-00T00:00:00Z", 9), True, False),
    (T("+1643-05-04T00:00:00Z", 11, "julian"), T("+1643-05-00T00:00:00Z", 10), True, False),  # = Gregorian 14 May
    (T("+1643-05-04T00:00:00Z", 11, "julian"), T("+1643-05-14T00:00:00Z", 11), True, True),   # one identity
    (T("+1643-05-14T00:00:00Z", 11), T("+1644-00-00T00:00:00Z", 9), False, False),
    (T("+1643-00-00T00:00:00Z", 9), T("+1700-00-00T00:00:00Z", 7), True, False),               # 1601-1700
    (T("+1601-00-00T00:00:00Z", 9), T("+1700-00-00T00:00:00Z", 7), True, False),
    (T("+1601-00-00T00:00:00Z", 9), T("+1600-00-00T00:00:00Z", 7), False, False),              # 1501-1600
    (T("+1600-00-00T00:00:00Z", 9), T("+1600-00-00T00:00:00Z", 7), True, False),               # ordinal
    (T("+1700-00-00T00:00:00Z", 9), T("+1600-00-00T00:00:00Z", 7), False, False),
    (T("+2019-06-30T00:00:00Z", 11), T("+2019-00-00T00:00:00Z", 9), True, False),               # S-KEY-019 refines
    (T("+2019-01-01T05:00:00Z", 12), T("+2019-01-01T00:00:00Z", 11), True, False),   # an hour of that day
    (T("+2019-01-02T00:00:00Z", 12), T("+2019-01-01T00:00:00Z", 11), False, False),  # finer but not inside
    # quantity: the same unit; the interval inside and narrower
    (Q("+3.5"), Q("+3.5", "+3", "+4"), True, False),
    (Q("+3.5", "+3.4", "+3.6"), Q("+3.5", "+3", "+4"), True, False),
    (Q("+3.5", "+2", "+5"), Q("+3.5", "+3", "+4"), False, True),
    (Q("+3.6", "+3", "+4"), Q("+3.5", "+3", "+4"), False, False),   # the same interval, another amount
    (Q("+3.5", "+3", "+4", "wd:Q11573"), Q("+3.5", "+3", "+4"), False, False),
    (Q("+4"), Q("+3.5", "+3", "+4"), True, False),
    # geo: the same globe, a finer precision, inside the cell
    (G("+35.6812", "+139.7671", "+0.0001"), G("+35.68", "+139.77", "+0.01"), True, False),
    (G("+35.6812", "+139.7671", "+0.0001"), G("+35.7", "+139.8", "+0.1"), True, False),
    (G("+35.6812", "+139.7671", "+0.0001"), G("+35.6", "+139.77", "+0.01"), False, False),  # outside the cell
    (G("+35.68", "+139.77", "+0.01"), G("+35.68", "+139.77", "+0.01", "wd:Q405"), False, False),
    # string, iri, lang_string, boolean: equality only
    (S_("TYO"), S_("TYO"), True, True),
    (S_("TYO"), S_("Tokyo"), False, False),
    ({"literal": {"datatype": "boolean", "value": True}}, {"literal": {"datatype": "boolean", "value": False}},
     False, False),
    # special and unbound values
    (E, SV, True, False),
    (T("+1643-00-00T00:00:00Z", 9), SV, True, False),
    ({"fact": "f:x"}, SV, True, False),
    (E, UNB, True, False),
    (SV, UNB, False, False),
    (NV, NV, True, True),
    (E, NV, False, False),
    (NV, SV, False, False),
    (SV, SV, True, True),
    (E, {"entity": "ex:Warszawa"}, False, False),
    ({"entity": "f:x"}, {"fact": "f:x"}, False, False),
]


@pytest.mark.parametrize("a, b, down, up", VALUE_CASES)
def test_value_refinement(a, b, down, up):
    assert record.value_refines(a, b) is down
    assert record.value_refines(b, a) is up


def test_every_value_refines_itself():
    for f in FACTS.values():
        for binding in f["bindings"]:
            assert record.value_refines(binding["value"], binding["value"])


def test_a_malformed_value_is_refused():
    with pytest.raises(ValidationError) as exc:
        record.value_refines(T("+0000-00-00T00:00:00Z", 9), SV)
    assert exc.value.code == "KHG-S006"


# ------------------------------------------------------------------------------------------------ facts


def fact(fid, **changes):
    f = copy.deepcopy(FACTS[fid])
    for bid, value in changes.items():
        b = next((x for x in f["bindings"] if x["bid"] == bid), None)
        if value is None:
            f["bindings"].remove(b)
        else:
            b["value"] = value
    return f


def refines(a, b):
    return record.fact_refines(a, b, S)


def test_every_fixture_fact_refines_itself_and_only_its_duplicates():
    for fid, f in FACTS.items():
        assert refines(f, f), fid
        for gid, g in FACTS.items():
            if gid != fid and refines(f, g) and refines(g, f):
                assert record.content_key(f, S) == record.content_key(g, S)  # mutual refinement: a duplicate


def test_adding_a_qualifier_or_a_bound_refines():
    k14 = FACTS["f:king-14"]
    assert refines(k14, fact("f:king-14", b5=None)) and not refines(fact("f:king-14", b5=None), k14)
    assert refines(k14, fact("f:king-14", b4=None))  # the end bound added
    assert not refines(fact("f:king-14", b4=None), k14)


def test_a_finer_bound_refines_and_a_different_one_does_not():
    year = fact("f:king-14", b3=T("+1643-00-00T00:00:00Z", 9))
    assert refines(FACTS["f:king-14"], year) and not refines(year, FACTS["f:king-14"])
    julian = fact("f:king-14", b3=T("+1643-05-04T00:00:00Z", 11, "julian"))
    assert refines(julian, FACTS["f:king-14"]) and refines(FACTS["f:king-14"], julian)
    assert not refines(fact("f:king-14", b3=T("+1644-00-00T00:00:00Z", 9)), year)


def test_somevalue_is_refined_by_a_filler_and_novalue_only_by_novalue():
    scribe = FACTS["f:born-scribe"]
    assert refines(fact("f:born-scribe", b2={"entity": "ex:Paris"}), scribe)
    assert not refines(scribe, fact("f:born-scribe", b2={"entity": "ex:Paris"}))
    cat = FACTS["f:cat-7"]
    assert not refines(fact("f:cat-7", b2={"entity": "ex:insulin"}), cat)
    assert not refines(cat, fact("f:cat-7", b2={"entity": "ex:insulin"}))
    assert refines(cat, fact("f:cat-7", b2=None))  # a role left unbound may gain a novalue


def test_meta_bindings_are_ignored():
    k14 = FACTS["f:king-14"]
    with_cause = copy.deepcopy(k14)
    with_cause["bindings"].append({"bid": "b6", "role": "khg:end_cause", "value": {"entity": "ex:LouisXIV"}})
    assert refines(with_cause, k14) and refines(k14, with_cause)


def test_complete_roles_keep_their_size_and_ordered_roles_their_positions():
    route = FACTS["f:route-1"]
    longer = copy.deepcopy(route)
    longer["bindings"].append({"bid": "b5", "role": "stop", "value": {"entity": "ex:YUL"}, "position": 4})
    assert not refines(longer, route) and not refines(route, longer)
    swapped = copy.deepcopy(route)
    swapped["bindings"][1]["position"], swapped["bindings"][2]["position"] = 2, 1
    assert not refines(swapped, route)
    married = FACTS["f:married-curie"]
    assert not refines(fact("f:married-curie", b2={"entity": "ex:LouisXIV"}), married)


def test_the_matching_is_injective():
    coadmin = FACTS["f:coadmin-1"]  # agents insulin and metformin
    both_insulin = fact("f:coadmin-1", b2={"entity": "ex:insulin"})
    assert not refines(both_insulin, coadmin)  # one insulin binding cannot refine two agents
    three = copy.deepcopy(coadmin)
    three["bindings"].append({"bid": "b4", "role": "agent", "value": {"entity": "ex:insulin"}})
    assert refines(three, coadmin) and not refines(coadmin, three)


def test_different_relations_never_refine():
    assert not refines(FACTS["f:loop-yyz"], FACTS["f:route-1"])


def test_an_undeclared_role_is_s002():
    bad = copy.deepcopy(FACTS["f:king-14"])
    bad["bindings"][0]["role"] = "reign"
    with pytest.raises(ValidationError) as exc:
        refines(bad, FACTS["f:king-14"])
    assert exc.value.code == "KHG-S002"


def test_injective_match_uses_augmenting_paths():
    # a greedy pairing gives 0 -> 0 and strands 1; the matching moves 0 to 1
    ok = {(0, 0), (0, 1), (1, 0), (2, 1), (2, 2)}
    assert record.injective_match(3, 3, lambda i, j: (i, j) in ok)
    assert not record.injective_match(2, 3, lambda i, j: j == 0)
    assert not record.injective_match(3, 2, lambda i, j: True)
    assert record.injective_match(0, 0, lambda i, j: False)
    assert record.injective_match(40, 40, lambda i, j: j in (i, (i + 1) % 40))
