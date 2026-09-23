"""W3: render_text, format khg-render/1 (DESIGN §2.10)."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, record
from khg_contracts.errors import ValidationError
from khg_contracts.schema import load_schema

S = load_schema(data.path("fixture/fixture.relation-schema.json"))
C1 = data.load_json("fixture/fixture.c1.json")
FACTS = {r["id"]: r for r in C1["records"] if r["kind"] == "hyperedge"}
LABELS = {r["id"]: r["label"] for r in C1["records"] if r["kind"] == "entity"}

RENDERED = {
    "f:born-louis14-paris": "born_in(person: Louis XIV; birthplace: Paris)",
    "f:born-scribe": "born_in(person: an anonymous scribe; birthplace: some value)",
    "f:born-skłodowska-kraków": "born_in(person: Maria Skłodowska; birthplace: Kraków)",
    "f:born-skłodowska-warszawa": "born_in(person: Maria Skłodowska; birthplace: Warszawa)",
    "f:cat-7": "catalysed_by(reaction: hydrolysis reaction 7; catalyst: no value)",
    "f:claim-1": "claims(claimant: Ødegård the chronicler; claim: [f:born-louis14-paris]; "
                 "point_in_time: +1700-00-00T00:00:00Z/9 (Julian))",
    "f:coadmin-1": "co_administration_causes(agent: insulin, metformin; effect: hypoglycaemia)",
    "f:king-13": "position_held(holder: Louis XIII; position: King of France) "
                 "[+1610-05-14T00:00:00Z/11, +1643-05-14T00:00:00Z/11)",
    "f:king-14": "position_held(holder: Louis XIV; position: King of France; replaces: Louis XIII) "
                 "[+1643-05-14T00:00:00Z/11, +1715-09-01T00:00:00Z/11)",
    "f:loop-yyz": "flies_between(carrier: Air Canada; origin: Toronto Pearson; destination: Toronto Pearson)",
    "f:married-curie": "married(spouse: Maria Skłodowska, Pierre Curie) "
                       "[+1895-07-26T00:00:00Z/11, +1906-04-19T00:00:00Z/11)",
    "f:pop-łódź-2019": "population(place: Łódź; quantity: +679941; point_in_time: +2019-00-00T00:00:00Z/9)",
    "f:pop-łódź-2019-dep": "population(place: Łódź; quantity: +685285; point_in_time: +2019-00-00T00:00:00Z/9)",
    "f:reg-1": "regulates(regulator: TP53; target: TP53; context: HeLa)",
    "f:route-1": "flight_route(carrier: Air Canada; stop: Toronto Pearson, Montréal–Trudeau, Toronto Pearson)",
    "f:station-東京": "station_profile(station: Tokyo Station; name: Tokyo Station@en, 東京駅@ja; code: TYO; "
                     "elevation: +3.5 wd:Q11573 [+3, +4]; opened: +1914-12-20T00:00:00Z/11; active: true; "
                     "homepage: https://www.tokyostationcity.com/; location: +35.6812,+139.7671)",
    "g:who-1774": "position_held(holder: ?who; position: King of France) [+1774-05-10T00:00:00Z/11, …)",
    "m:sup-1": "khg:supersedes(khg:superseding: [f:born-skłodowska-warszawa]; "
               "khg:superseded: [f:born-skłodowska-kraków])",
}


def test_the_design_example():
    assert record.render_text(FACTS["f:king-14"], LABELS, schema=S) == (
        "position_held(holder: Louis XIV; position: King of France; replaces: Louis XIII) "
        "[+1643-05-14T00:00:00Z/11, +1715-09-01T00:00:00Z/11)")
    assert record.RENDER_FORMAT == "khg-render/1"


@pytest.mark.parametrize("fid", sorted(RENDERED))
def test_every_fixture_hyperedge_renders_exactly(fid):
    assert record.render_text(FACTS[fid], LABELS, schema=S) == RENDERED[fid]


def test_core_usages_come_first_and_binding_order_does_not_matter():
    reg = copy.deepcopy(FACTS["f:reg-1"])
    reg["bindings"].reverse()  # the qualifier context is bound first
    assert record.render_text(reg, LABELS, schema=S) == RENDERED["f:reg-1"]


def test_meta_bindings_are_omitted_and_absent_bounds_are_an_ellipsis():
    k13 = copy.deepcopy(FACTS["f:king-13"])
    k13["bindings"] = [b for b in k13["bindings"] if b["role"] != "start_time"]
    k13["bindings"].append({"bid": "b5", "role": "khg:end_cause", "value": {"entity": "ex:LouisXIV"}})
    assert record.render_text(k13, LABELS, schema=S) == \
        "position_held(holder: Louis XIII; position: King of France) […, +1643-05-14T00:00:00Z/11)"
    ended = copy.deepcopy(FACTS["f:king-13"])
    ended["bindings"][0]["value"] = {"special": "somevalue"}  # b4, the end
    assert record.render_text(ended, LABELS, schema=S).endswith("[+1610-05-14T00:00:00Z/11, some value)")


def test_labels_fall_back_to_ids_and_may_name_relations_and_roles():
    assert record.render_text(FACTS["f:born-scribe"], {}, schema=S) == \
        "born_in(person: ex:anonymous_scribe; birthplace: some value)"
    assert record.render_text(FACTS["f:born-scribe"], None, schema=S) == \
        "born_in(person: ex:anonymous_scribe; birthplace: some value)"
    labels = dict(LABELS, born_in="was born in", birthplace="place of birth")
    assert record.render_text(FACTS["f:born-scribe"], labels, schema=S) == \
        "was born in(person: an anonymous scribe; place of birth: some value)"


def test_schema_labels_are_used():
    doc = copy.deepcopy(S.doc)
    rel = next(r for r in doc["relations"] if r["id"] == "born_in")
    rel["label"] = "born in"
    rel["roles"][1]["label"] = "birth place"
    assert record.render_text(FACTS["f:born-louis14-paris"], LABELS, schema=doc) == \
        "born in(person: Louis XIV; birth place: Paris)"


def test_undeclared_roles_and_relations_are_refused():
    bad = copy.deepcopy(FACTS["f:reg-1"])
    bad["bindings"][0]["role"] = "cell"
    with pytest.raises(ValidationError) as exc:
        record.render_text(bad, LABELS, schema=S)
    assert exc.value.code == "KHG-S002"
    with pytest.raises(ValidationError) as exc:
        record.render_text(dict(FACTS["f:reg-1"], relation="represses"), LABELS, schema=S)
    assert exc.value.code == "KHG-S001"


def test_render_value():
    assert record.render_value({"entity": "ex:Paris"}, LABELS) == "Paris"
    assert record.render_value({"special": "novalue"}) == "no value"
    assert record.render_value({"unbound": {"var": "who"}}) == "?who"
    assert record.render_value({"fact": "f:x"}) == "[f:x]"
    assert record.render_value({"literal": {"datatype": "boolean", "value": False}}) == "false"
