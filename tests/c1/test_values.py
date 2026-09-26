"""W3: values and typed literals: canonical forms, value identity, literal labels and the derived node ids
(DESIGN §2.3, §4.2)."""
from __future__ import annotations

import hashlib
import unicodedata

import pytest

from khg_contracts import data, jsonio, record
from khg_contracts.errors import ValidationError

HIF = data.load_json("fixture/fixture.hif.json")
C1 = data.load_json("fixture/fixture.c1.json")
FACTS = {r["id"]: r for r in C1["records"] if r["kind"] == "hyperedge"}


def T(time, precision, calendar=None):
    lit = {"datatype": "time", "time": time, "precision": precision}
    if calendar:
        lit["calendar"] = calendar
    return lit


def code(fn, *args, **kwargs):
    with pytest.raises(ValidationError) as exc:
        fn(*args, **kwargs)
    return exc.value.code


# ------------------------------------------------------------------------------------------------ canonical forms


def test_the_canonical_literal_keeps_the_written_form():
    assert record.canonical_literal(T("+1643-05-14T00:00:00Z", 11)) == T("+1643-05-14T00:00:00Z", 11, "gregorian")
    julian = T("+1700-00-00T00:00:00Z", 9, "julian")
    assert record.canonical_literal(julian) == julian  # the Julian calendar stays Julian
    assert record.canonical_literal({"datatype": "lang_string", "value": "Tokyo", "lang": "EN-gb"}) == \
        {"datatype": "lang_string", "value": "Tokyo", "lang": "en-gb"}
    decomposed = unicodedata.normalize("NFD", "R\u00e9sum\u00e9")
    assert len(decomposed) == 8
    assert record.canonical_literal({"datatype": "string", "value": decomposed}) == \
        {"datatype": "string", "value": unicodedata.normalize("NFC", decomposed)}
    assert record.canonical_literal(T("+1643-05-14T00:00:00Z", 11.0))["precision"] == 11


def test_canonical_literals_are_new_objects():
    lit = T("+1643-05-14T00:00:00Z", 11)
    out = record.canonical_literal(lit)
    assert out is not lit and "calendar" not in lit


@pytest.mark.parametrize("lit, want", [
    ({"datatype": "decimal", "value": "1"}, "KHG-C002"),
    ({"datatype": "quantity", "amount": "+1"}, "KHG-C004"),                          # no unit
    ({"datatype": "quantity", "amount": "+1", "unit": "1", "lower": "+0"}, "KHG-C004"),  # an unpaired bound
    ({"datatype": "quantity", "amount": "3.5", "unit": "1"}, "KHG-C004"),            # no sign
    ({"datatype": "quantity", "amount": "+3.50", "unit": "1"}, "KHG-C004"),          # a redundant zero
    ({"datatype": "quantity", "amount": 3.5, "unit": "1"}, "KHG-C004"),              # a JSON number
    ({"datatype": "boolean", "value": "true"}, "KHG-C004"),
    ({"datatype": "geo", "lat": "+1", "lon": "+2", "globe": "wd:Q2"}, "KHG-C004"),   # no precision
    ({"datatype": "lang_string", "value": "x"}, "KHG-C004"),                         # no lang
    ({"datatype": "string", "value": 7}, "KHG-C004"),
    (T("+1500-01-01T00:00:00Z", 11), "KHG-S006"),
    (T("+1643-05-14T00:00:00Z", 11, None) | {"calendar": None}, "KHG-C004"),
])
def test_malformed_literals_are_refused(lit, want):
    assert code(record.canonical_literal, lit) == want
    assert code(record.value_identity, {"literal": lit}) == want


def test_lenient_canonicalisation_never_raises_and_hides_nothing():
    old = T("+1500-01-01T00:00:00Z", 11)
    assert record.canonical_literal(old, strict=False) == old  # no calendar invented before 1583
    weird = {"datatype": "quantity", "amount": "three and a half", "unit": "1"}
    assert record.canonical_literal(weird, strict=False) == weird
    # a decimal in another writing is written in C1's form (ruling 22); the checks still refuse the raw writing
    number = {"datatype": "quantity", "amount": 3.5, "unit": "1"}
    assert record.canonical_literal(number, strict=False) == dict(number, amount="+3.5")
    assert code(record.value_identity, {"literal": number}) == "KHG-C004"
    assert record.canonical_value({"entity": "ex:a", "fact": "f:b"}, strict=False) == {"entity": "ex:a", "fact": "f:b"}


@pytest.mark.parametrize("value, want", [
    ({}, "KHG-C001"), ({"entity": "ex:a", "fact": "f:b"}, "KHG-C001"), ("ex:a", "KHG-C001"),
    ({"thing": "x"}, "KHG-C002"), ({"special": "missing"}, "KHG-C002"), ({"entity": 7}, "KHG-C010"),
    ({"unbound": "who"}, "KHG-C010"),
])
def test_malformed_values_are_refused(value, want):
    assert code(record.value_identity, value) == want


# ------------------------------------------------------------------------------------------------ identity


def test_a_time_literal_is_its_gregorian_window_plus_its_precision():
    assert record.literal_identity(T("+1643-05-14T00:00:00Z", 11, "gregorian")) == {
        "datatype": "time", "window": ["+1643-05-14T00:00:00Z", "+1643-05-15T00:00:00Z"], "precision": 11}


def test_julian_and_gregorian_writings_of_one_day_are_one_value():
    julian = {"literal": T("+1582-10-05T00:00:00Z", 11, "julian")}
    gregorian = {"literal": T("+1582-10-15T00:00:00Z", 11, "gregorian")}
    assert record.value_identity(julian) == record.value_identity(gregorian)
    assert record.values_equal(julian, gregorian)
    assert record.identity_key(julian) == record.identity_key(gregorian)
    assert record.canonical_value(julian) != record.canonical_value(gregorian)  # the written form is kept


def test_precision_takes_part_in_identity():
    # S-KEY-019: 2019/9 and 2019-06-30/11 are different values, though one window holds the other
    assert not record.values_equal({"literal": T("+2019-00-00T00:00:00Z", 9)},
                                   {"literal": T("+2019-06-30T00:00:00Z", 11)})
    # the same window at two precisions is still two values
    assert not record.values_equal({"literal": T("+2019-01-01T00:00:00Z", 11)},
                                   {"literal": T("+2019-01-01T00:00:00Z", 12)})


def test_other_literals_are_their_canonical_form():
    a = {"literal": {"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573", "lower": "+3", "upper": "+4"}}
    b = {"literal": {"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573"}}
    assert not record.values_equal(a, b)  # the bounds take part in equality
    assert record.value_identity(a) == a
    assert record.values_equal({"literal": {"datatype": "lang_string", "value": "Tokyo", "lang": "EN"}},
                               {"literal": {"datatype": "lang_string", "value": "Tokyo", "lang": "en"}})
    assert not record.values_equal({"literal": {"datatype": "string", "value": "TYO"}},
                                   {"literal": {"datatype": "iri", "value": "TYO"}})


def test_entities_facts_and_specials():
    assert record.value_identity({"entity": unicodedata.normalize("NFD", "ex:\u0141\u00f3d\u017a")}) == \
        {"entity": "ex:\u0141\u00f3d\u017a"}
    assert not record.values_equal({"entity": "f:x"}, {"fact": "f:x"})
    assert record.value_identity({"special": "somevalue"}) == {"special": "somevalue"}
    assert record.value_identity({"unbound": {"var": "who"}}) == {"unbound": {"var": "who"}}
    assert [record.value_kind(v) for v in ({"entity": "a"}, {"literal": {}}, {"fact": "f"}, {"special": "novalue"},
                                           {"unbound": {"var": "v"}})] == list(record.VALUE_KINDS)


def test_every_fixture_value_has_an_identity_invariant_under_canonicalisation():
    kinds: dict[str, int] = {}
    for f in FACTS.values():
        for b in f["bindings"]:
            kind = record.value_kind(b["value"])
            kinds[kind] = kinds.get(kind, 0) + 1
            assert record.value_identity(record.canonical_value(b["value"])) == record.value_identity(b["value"])
    assert kinds == {"entity": 33, "literal": 20, "fact": 3, "special": 2, "unbound": 1}


# ------------------------------------------------------------------------------------------------ labels and node ids


LITERAL_NODES = [n for n in HIF["nodes"] if n["attrs"]["khg-kind"] == "literal"]


@pytest.mark.parametrize("node", LITERAL_NODES, ids=[n["attrs"]["label"] for n in LITERAL_NODES])
def test_labels_and_shared_literal_node_ids_equal_the_fixture_hif(node):
    lit = node["attrs"]["khg-literal"]
    assert record.literal_label(lit) == node["attrs"]["label"]
    assert record.literal_node_id(lit) == node["node"]


def test_the_seven_datatypes_label_as_section_4_2_says():
    assert len(LITERAL_NODES) == 18
    labels = {n["attrs"]["khg-literal"]["datatype"] for n in LITERAL_NODES}
    assert labels == set(record.DATATYPES)
    assert record.literal_label(T("+1700-00-00T00:00:00Z", 9, "julian")) == "+1700-00-00T00:00:00Z/9 (Julian)"
    assert record.literal_label({"datatype": "quantity", "amount": "+679941", "unit": "1"}) == "+679941"
    assert record.literal_label({"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573", "lower": "+3",
                                 "upper": "+4"}) == "+3.5 wd:Q11573 [+3, +4]"
    assert record.literal_label({"datatype": "boolean", "value": False}) == "false"


def test_a_literal_node_is_shared_by_written_value():
    # the canonical literal, not the identity: the Julian writing of a day is its own node
    assert record.literal_node_id(T("+1643-05-14T00:00:00Z", 11)) == \
        record.literal_node_id(T("+1643-05-14T00:00:00Z", 11, "gregorian"))
    assert record.literal_node_id(T("+1582-10-05T00:00:00Z", 11, "julian")) != \
        record.literal_node_id(T("+1582-10-15T00:00:00Z", 11, "gregorian"))


@pytest.mark.parametrize("fact, bid, kind", [("f:born-scribe", "b2", "somevalue"), ("f:cat-7", "b2", "novalue"),
                                             ("g:who-1774", "b1", "unbound")])
def test_special_node_ids_equal_the_fixture_hif(fact, bid, kind):
    nid = record.special_node_id(kind, fact, bid)
    inc = next(i for i in HIF["incidences"] if i["edge"] == fact and i["attrs"]["khg-bid"] == bid)
    assert inc["node"] == nid
    assert nid.startswith({"somevalue": "_:sv:", "novalue": "_:nv:", "unbound": "_:var:"}[kind])


def test_per_binding_and_reference_node_ids():
    want = hashlib.sha256('khg-literal-binding/1\n["f:station-東京","b6"]'.encode()).hexdigest()[:32]
    assert record.literal_binding_node_id("f:station-東京", "b6") == "_:litb:" + want
    assert record.ref_node_id("f:born-louis14-paris") == "_:ref:f:born-louis14-paris"
    assert any(n["node"] == "_:ref:f:born-louis14-paris" for n in HIF["nodes"])
    with pytest.raises(ValueError):
        record.special_node_id("withheld", "f:x", "b1")
    assert jsonio.canonical(record.NONE_ID) == '"khg:none"'
