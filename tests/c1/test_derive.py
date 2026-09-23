"""W3: the derived block: arity, the three keys and valid time (DESIGN §2.4, §2.5, §2.6, §2.9)."""
from __future__ import annotations

import copy
import unicodedata

import pytest

from khg_contracts import data, jsonio, record
from khg_contracts.errors import ValidationError
from khg_contracts.schema import load_schema

S = load_schema(data.path("fixture/fixture.relation-schema.json"))
C1 = data.load_json("fixture/fixture.c1.json")
WITH_DERIVED = data.load_json("fixture/fixture.with-derived.c1.json")
FACTS = {r["id"]: r for r in C1["records"] if r["kind"] == "hyperedge"}
STORED = {r["id"]: r.get("derived") for r in WITH_DERIVED["records"] if r["kind"] == "hyperedge"}


def T(time, precision, calendar="gregorian"):
    return {"literal": {"datatype": "time", "time": time, "precision": precision, "calendar": calendar}}


def fact(fid, *, drop=(), **values):
    f = copy.deepcopy(FACTS[fid])
    f["bindings"] = [b for b in f["bindings"] if b["bid"] not in drop]
    for b in f["bindings"]:
        if b["bid"] in values:
            b["value"] = values[b["bid"]]
    return f


# ------------------------------------------------------------------------------------------------ the fixture


def test_with_derived_equals_the_fixture_file():
    assert jsonio.canonical(record.with_derived(C1, S)) == jsonio.canonical(WITH_DERIVED)


@pytest.mark.parametrize("fid", sorted(STORED))
def test_derive_equals_the_stored_block(fid):
    want = STORED[fid]
    assert record.derive(FACTS[fid], S) == (want if want is not None else {})


def test_the_digests_of_king_14():
    k14 = FACTS["f:king-14"]
    assert record.content_key(k14, S) == "sha256:2706f2b5162301565965492815a53ac7f16064ea742b03756cadbbafefd9d76b"
    assert record.core_key(k14, S) == "sha256:5779b98f13640fbf96488b9834c5ce7e10f02902541882a23c2d43f84f93e916"
    assert record.key_digest(k14, S) == "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96"


def test_the_key_digests_of_the_section_2_5_collision_example():
    krakow = FACTS["f:born-skłodowska-kraków"]
    assert record.key_digest(krakow, S) == \
        "sha256:951a7bba11cca1f6c84ede16cd78c9502d08b7ab45060ff462b2ba4f0eea045c"
    assert record.key_digest(FACTS["f:born-skłodowska-warszawa"], S) == record.key_digest(krakow, S)
    k14b = fact("f:king-14", b3=T("+1640-01-01T00:00:00Z", 11))
    k14b["id"] = "f:king-14b"
    assert record.key_digest(k14b, S) == record.key_digest(FACTS["f:king-13"], S) == \
        "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96"


def test_content_key_is_the_digest_of_the_sorted_binding_tuples():
    scribe = FACTS["f:born-scribe"]
    payload = {"relation": "born_in", "bindings": [["birthplace", None, {"special": "somevalue"}],
                                                   ["person", None, {"entity": "ex:anonymous_scribe"}]]}
    assert record.content_key(scribe, S) == jsonio.digest("khg-content-key/1", payload)
    assert record.core_key(scribe, S) == jsonio.digest("khg-core-key/1", payload)
    assert record.key_digest(scribe, S) == jsonio.digest(
        "khg-key-digest/1", {"relation": "born_in", "bindings": [["person", None, {"entity": "ex:anonymous_scribe"}]]})


# ------------------------------------------------------------------------------------------------ arity


@pytest.mark.parametrize("fid, want", [
    ("f:king-14", {"arity": 3, "core_arity": 2, "statement_arity": 5, "distinct_fillers": 3}),
    ("f:route-1", {"arity": 4, "core_arity": 4, "statement_arity": 4, "distinct_fillers": 3}),
    ("f:station-東京", {"arity": 9, "core_arity": 1, "statement_arity": 9, "distinct_fillers": 9}),
    ("f:cat-7", {"arity": 1, "core_arity": 1, "statement_arity": 1, "distinct_fillers": 1}),  # novalue not counted
    ("f:born-scribe", {"arity": 2, "core_arity": 2, "statement_arity": 2, "distinct_fillers": 2}),  # somevalue is
    ("f:loop-yyz", {"arity": 3, "core_arity": 3, "statement_arity": 3, "distinct_fillers": 2}),
    ("f:claim-1", {"arity": 3, "core_arity": 2, "statement_arity": 3, "distinct_fillers": 3}),
    ("g:who-1774", {"n_bound": 2, "n_unbound": 1}),
])
def test_the_arity_table(fid, want):
    assert record.arity(FACTS[fid], S) == want


def test_somevalues_are_distinct_fillers():
    two = copy.deepcopy(FACTS["f:coadmin-1"])
    for b in two["bindings"][:2]:
        b["value"] = {"special": "somevalue"}
    assert record.arity(two, S) == {"arity": 3, "core_arity": 3, "statement_arity": 3, "distinct_fillers": 3}


def test_the_arity_bins():
    assert [record.arity_bin(n) for n in range(8)] == ["0-1", "0-1", "2", "3", "4", "5+", "5+", "5+"]
    bins = sorted({record.arity_bin(record.arity(f, S)["arity"]) for f in FACTS.values()
                   if f["status"] != "goal" and S.kind(f["relation"]) == "fact"})
    assert bins == ["0-1", "2", "3", "4", "5+"]


def test_lifecycle_records_and_entities_have_no_arity_and_no_derived_block():
    sup = FACTS["m:sup-1"]
    with pytest.raises(ValueError, match="lifecycle"):
        record.arity(sup, S)
    assert record.derive(sup, S) == {}
    entity = next(r for r in C1["records"] if r["kind"] == "entity")
    assert record.derive(entity, S) == {}
    with pytest.raises(ValueError):
        record.content_key(entity, S)
    assert record.key_digest(sup, S) is None


# ------------------------------------------------------------------------------------------------ keys


def test_what_never_enters_a_key():
    k14 = FACTS["f:king-14"]
    keys = (record.content_key(k14, S), record.core_key(k14, S), record.key_digest(k14, S))
    other = copy.deepcopy(k14)
    other.update(rank="preferred", visibility="suppressed", confidence={"value": 0.2, "scale": "probability"},
                 source_text="Louis XIV", evidence=[], derived={"arity": 99}, extensions={"hif:weight": 7})
    for n, b in enumerate(reversed(other["bindings"]), 1):
        b["bid"] = f"b{10 + n}"
    other["bindings"].reverse()
    other["bindings"].append({"bid": "b20", "role": "khg:end_cause", "value": {"entity": "ex:Mazarin"}})
    other["bindings"][0]["extensions"] = {"hif:weight": 0.5}
    assert (record.content_key(other, S), record.core_key(other, S), record.key_digest(other, S)) == keys


def test_keys_compare_values_by_identity():
    k14 = FACTS["f:king-14"]
    julian = fact("f:king-14", b3=T("+1643-05-04T00:00:00Z", 11, "julian"))  # = Gregorian 14 May 1643
    assert record.content_key(julian, S) == record.content_key(k14, S)
    route = FACTS["f:route-1"]
    as_floats = copy.deepcopy(route)
    for b in as_floats["bindings"]:
        if "position" in b:
            b["position"] = float(b["position"])  # RFC 8785: 2.0 is 2
    assert record.content_key(as_floats, S) == record.content_key(route, S)
    loodz = copy.deepcopy(FACTS["f:pop-łódź-2019"])
    loodz["bindings"][0]["value"] = {"entity": unicodedata.normalize("NFD", "ex:Łódź")}
    assert record.content_key(loodz, S) == record.content_key(FACTS["f:pop-łódź-2019"], S)


def test_time_bindings_and_qualifiers_are_content_but_not_core():
    k14 = FACTS["f:king-14"]
    second_term = fact("f:king-14", b3=T("+1720-01-01T00:00:00Z", 11), b4=T("+1730-01-01T00:00:00Z", 11))
    assert record.content_key(second_term, S) != record.content_key(k14, S)  # two periods: two facts
    assert record.core_key(second_term, S) == record.core_key(k14, S)
    no_qualifier = fact("f:king-14", drop=("b5",))
    assert record.content_key(no_qualifier, S) != record.content_key(k14, S)
    assert record.core_key(no_qualifier, S) == record.core_key(k14, S)
    coarser = fact("f:king-14", b3=T("+1643-00-00T00:00:00Z", 9))
    assert record.content_key(coarser, S) != record.content_key(k14, S)  # precision takes part


def test_key_digest_is_null_without_a_complete_concrete_key():
    assert record.key_digest(FACTS["f:route-1"], S) is None  # no key
    assert record.key_digest(fact("f:pop-łódź-2019", drop=("b3",)), S) is None  # a key role absent
    assert record.key_digest(fact("f:born-scribe", b1={"special": "somevalue"}), S) is None
    assert record.key_digest(fact("f:king-14", b2={"special": "novalue"}), S) is None
    goal = fact("g:who-1774", b2={"unbound": {"var": "office"}})
    assert record.key_digest(goal, S) is None
    assert record.key_digest(FACTS["g:who-1774"], S) == record.key_digest(FACTS["f:king-14"], S)


def test_precision_separates_key_groups():
    # S-KEY-019: 2019/9 and 2019-06-30/11 are different keys; the calendar is not
    q2 = fact("f:pop-łódź-2019", b3=T("+2019-06-30T00:00:00Z", 11))
    assert record.key_digest(q2, S) != record.key_digest(FACTS["f:pop-łódź-2019"], S)
    assert record.key_digest(FACTS["f:pop-łódź-2019-dep"], S) == record.key_digest(FACTS["f:pop-łódź-2019"], S)


def test_derive_refuses_an_invalid_record():
    bad_relation = dict(FACTS["f:king-14"], relation="reigned")
    bad_role = fact("f:king-14")
    bad_role["bindings"][0]["role"] = "reign"
    bad_time = fact("f:king-14", b3=T("+0000-00-00T00:00:00Z", 9))
    bad_value = fact("f:king-14", b1={"entity": "ex:a", "fact": "f:b"})
    for rec, code in ((bad_relation, "KHG-S001"), (bad_role, "KHG-S002"), (bad_time, "KHG-S006"),
                      (bad_value, "KHG-C001")):
        with pytest.raises(ValueError) as exc:
            record.derive(rec, S)
        assert isinstance(exc.value, ValidationError) and exc.value.code == code


def test_a_schema_document_works_as_the_schema():
    assert record.derive(FACTS["f:king-14"], S.doc) == STORED["f:king-14"]


# ------------------------------------------------------------------------------------------------ valid time


def vt(fid, **kw):
    return record.valid_time(fact(fid, **kw), S)


def test_the_bound_table():
    rows = {
        "period": vt("f:king-13"),
        "since (end absent)": vt("f:king-13", drop=("b4",)),
        "since (end novalue)": vt("f:king-13", b4={"special": "novalue"}),
        "ended (end somevalue)": vt("f:king-13", b4={"special": "somevalue"}),
        "until (start absent)": vt("f:king-13", drop=("b3",)),
        "until (start somevalue)": vt("f:king-13", b3={"special": "somevalue"}),
        "undated": vt("f:king-13", drop=("b3", "b4")),
        "since forever (start novalue)": vt("f:king-13", b3={"special": "novalue"}),
    }
    got = {k: (v["kind"], v["definite"], v["possible"]) for k, v in rows.items()}
    s, e = "+1610-05-14T00:00:00Z", "+1643-05-14T00:00:00Z"
    s_hi, e_hi = "+1610-05-15T00:00:00Z", "+1643-05-15T00:00:00Z"
    assert got == {
        "period": ("period", [s_hi, e], [s, e_hi]),
        "since (end absent)": ("since", [s_hi, None], [s, None]),
        "since (end novalue)": ("since", [s_hi, None], [s, None]),
        "ended (end somevalue)": ("ended", None, [s, None]),
        "until (start absent)": ("until", None, [None, e_hi]),
        "until (start somevalue)": ("until", None, [None, e_hi]),
        "undated": ("undated", None, [None, None]),
        "since forever (start novalue)": ("until", [None, e], [None, e_hi]),
    }
    assert rows["period"]["start"] == T("+1610-05-14T00:00:00Z", 11) and "end" not in rows["since (end absent)"]
    assert rows["since (end novalue)"]["end"] == {"special": "novalue"}


def test_invariant_and_timeless_facts_hold_at_every_instant():
    assert vt("f:reg-1") == {"kind": "invariant", "definite": [None, None], "possible": [None, None]}
    assert vt("f:route-1")["kind"] == "timeless"
    assert vt("m:sup-1")["kind"] == "timeless"
    b = record.bounds(FACTS["f:reg-1"], S)
    assert b.holds_at("-9999-01-01T00:00:00Z") and b.holds_at("+9999-01-01T00:00:00Z", "possible")


def test_the_same_day_handover_is_a_possible_but_not_a_definite_overlap():
    k13, k14 = record.bounds(FACTS["f:king-13"], S), record.bounds(FACTS["f:king-14"], S)
    assert not record.definite_overlap(k13, k14)  # a succession, not a conflict
    assert record.possible_overlap(k13, k14)      # the designed L008 warning of the fixture
    assert k13.definite == (record.parse_instant("+1610-05-15T00:00:00Z"),
                            record.parse_instant("+1643-05-14T00:00:00Z"))
    assert k13.holds_at("+1620-01-01T00:00:00Z") and not k13.holds_at("+1643-05-14T12:00:00Z")
    assert k13.holds_at("+1643-05-14T12:00:00Z", "possible")
    with pytest.raises(ValueError):
        k13.holds_at("+1620-01-01T00:00:00Z", "probable")


def test_an_empty_possible_validity_can_be_seen():
    reversed_ = record.bounds(fact("f:king-13", b3=T("+1700-01-01T00:00:00Z", 11)), S)
    assert reversed_.s_lo >= reversed_.e_hi  # S009, which the validator reports
    assert reversed_.definite is None


# ---------------------------------------------------------------------------- the S-TIME scenarios, record by record

SCENARIOS = ["S-TIME-001", "S-TIME-003", "S-TIME-005", "S-TIME-007", "S-TIME-008", "S-TIME-009", "S-TIME-010",
             "S-TIME-011", "S-TIME-012"]
DEFAULT_READ = {"status": ("asserted",), "rank": ("preferred", "normal"), "visibility": ("visible",)}


def _given(scenario):
    """The facts a scenario puts or loads, built from the fixture (only the forms these scenarios use)."""
    facts = {}
    for step in scenario["given"]:
        if step.get("load") == "@fixture":
            facts.update(copy.deepcopy(FACTS))
            continue
        for item in step["put"]:
            if not isinstance(item, dict) or "@" not in item:
                continue  # entities
            f = copy.deepcopy(FACTS[item["@"]])
            f.update(item.get("set", {}))
            f["bindings"] = [b for b in f["bindings"] if b["bid"] not in item.get("drop_bindings", [])]
            for b in f["bindings"]:
                b["value"] = item.get("set_binding", {}).get(b["bid"], b["value"])
            facts[f["id"]] = f
    return facts


def _incident(facts, node, where):
    out = []
    for fid, f in sorted(facts.items()):
        if f["status"] not in DEFAULT_READ["status"] or f.get("rank", "normal") not in DEFAULT_READ["rank"]:
            continue
        if S.kind(f["relation"]) != "fact" or not any(b["value"].get("entity") == node for b in f["bindings"]):
            continue
        if "as_of" in where and not record.bounds(f, S).holds_at(where["as_of"], where.get("valid_mode", "definite")):
            continue
        out.append(fid)
    return out


@pytest.mark.parametrize("sid", SCENARIOS)
def test_valid_time_scenarios(sid):
    scenario = data.load_json(f"scenarios/{sid}.json")
    facts = _given(scenario)
    checked = 0
    for step in scenario["when"]:
        args, then = step["args"], step["then"]
        if step["op"] == "incident":
            assert _incident(facts, args["node"], args.get("where", {})) == then["equals"], (sid, args)
            checked += 1
        elif step["op"] == "get" and then["select"].startswith("derived.valid_time."):
            got = record.derive(facts[args["id"]], S)["valid_time"][then["select"].rsplit(".", 1)[1]]
            assert got == then["equals"], (sid, then)
            checked += 1
    assert checked >= 1
