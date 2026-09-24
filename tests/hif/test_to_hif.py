"""W6: C1 -> HIF, ``to_hif`` (DESIGN §4.2, §4.5, §4.6).

``to_hif`` reproduces ``fixture.hif.json`` and ``fixture.directed-slice.hif.json``, with literal labels, literal
nodes shared by value or per binding, per-binding special nodes, fact references, weights, binding extensions,
closed slices and the inlined schema.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from collections import Counter

import pytest

from khg_contracts import data, hif, jsonio
from khg_contracts.errors import ValidationError
from khg_contracts.record import literal_binding_node_id, literal_label, literal_node_id, special_node_id
from khg_contracts.validate import layers, run, validate_hif

SLICE_RELATIONS = ["born_in", "catalysed_by", "claims", "co_administration_causes", "flight_route", "population",
                   "position_held", "regulates", "station_profile"]


def _kinds(h):
    return Counter(n["attrs"]["khg-kind"] for n in h["nodes"])


def _node(h, nid):
    return next(n for n in h["nodes"] if n["node"] == nid)


def _incidences(h, edge):
    return [i for i in h["incidences"] if i["edge"] == edge]


# ------------------------------------------------------------------------------------------------ the fixture files


def test_to_hif_equals_fixture_hif(c1, schema, full):
    h = hif.to_hif(c1, schema)
    assert h == full
    assert jsonio.canonical(h) == jsonio.canonical(full)  # structural canonical equality (F10)


def test_to_hif_equals_the_directed_slice(c1, schema, directed_slice):
    assert directed_slice["metadata"]["khg-slice"] == {"relations": SLICE_RELATIONS}
    h = hif.to_hif(c1, schema, relations=SLICE_RELATIONS)
    assert h == directed_slice
    assert jsonio.canonical(h) == jsonio.canonical(directed_slice)
    # the relation list is a set: order and repeats do not matter
    assert hif.to_hif(c1, schema, relations=list(reversed(SLICE_RELATIONS)) + ["regulates"]) == directed_slice


def test_the_fixture_file_has_the_shape_of_section_4_6(c1, schema):
    h = hif.to_hif(c1, schema)
    assert h["network-type"] == "undirected"  # married and flies_between declare no direction
    assert len(h["nodes"]) == 46 and len(h["edges"]) == 18 and len(h["incidences"]) == 59
    assert _kinds(h) == {"entity": 22, "literal": 18, "fact-ref": 3, "somevalue": 1, "novalue": 1, "unbound": 1}
    assert sum("direction" in i for i in h["incidences"]) == 52
    pairs = Counter((i["edge"], i["node"]) for i in h["incidences"])
    assert sorted(p for p, n in pairs.items() if n > 1) == [("f:loop-yyz", "ex:YYZ"), ("f:reg-1", "ex:TP53"),
                                                            ("f:route-1", "ex:YYZ")]
    isolated = {n["node"] for n in h["nodes"]} - {i["node"] for i in h["incidences"]}
    assert isolated == {"ex:Mazarin"}


def test_the_directed_slice_has_the_shape_of_section_4_6(c1, schema):
    h = hif.to_hif(c1, schema, relations=SLICE_RELATIONS)
    assert h["network-type"] == "directed" and all("direction" in i for i in h["incidences"])
    assert len(h["nodes"]) == 42 and len(h["edges"]) == 16 and len(h["incidences"]) == 52
    kinds = _kinds(h)
    assert (kinds["entity"], kinds["literal"], kinds["fact-ref"]) == (20, 16, 3)
    assert kinds["somevalue"] + kinds["novalue"] + kinds["unbound"] == 3
    assert h["metadata"]["khg-complete"] is False
    assert {e["attrs"]["relation"] for e in h["edges"]} == set(SLICE_RELATIONS) | {"khg:supersedes"}


def test_to_hif_is_deterministic_across_hash_seeds(c1, schema, full):
    want = jsonio.digest("khg-test/1", full)
    code = ("from khg_contracts import data, hif, jsonio; from khg_contracts.schema import load_schema; "
            "S = load_schema(data.load_json('fixture/fixture.relation-schema.json')); "
            "c = data.load_json('fixture/fixture.c1.json'); "
            "print(jsonio.digest('khg-test/1', hif.to_hif(c, S)))")
    for seed in ("0", "3"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
        assert out.stdout.strip() == want
    assert jsonio.digest("khg-test/1", hif.to_hif(copy.deepcopy(c1), schema)) == want


# ------------------------------------------------------------------------------------------------ the mapping


def test_the_metadata_declaration_block(c1, schema, full):
    md = hif.to_hif(c1, schema)["metadata"]
    assert list(md) == ["role-convention", "hif-schema", "hif-schema-sha256", "khg-profile", "khg-record",
                        "khg-schema", "khg-schema-sha256", "khg-document-id", "khg-literal-nodes", "khg-complete",
                        "title"]
    assert md["role-convention"] == "1.0.0" and md["khg-profile"] == "khg-hif/1.0.0"
    assert md["hif-schema"].endswith("/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json")
    assert md["hif-schema-sha256"] == data.HIF_SCHEMA_SHA256 == data.sha256(data.HIF_SCHEMA)
    assert (md["khg-schema"], md["khg-schema-sha256"]) == ("p2-gate/1.0.0", schema.sha256)
    assert schema.sha256.startswith("sha256:cadd01cd")
    assert (md["khg-document-id"], md["khg-record"], md["khg-complete"]) == ("p2-gate-fixture", "khg-record/1.0.0",
                                                                             True)
    assert md["title"] == c1["header"]["extensions"]["hif:metadata"]["title"]  # passed through as a plain key
    assert "default_attrs" not in md and "khg-slice" not in md and "khg-schema-document" not in md


def test_entity_nodes_carry_the_entity_fields(c1, schema):
    h = hif.to_hif(c1, schema)
    assert _node(h, "ex:TP53") == {"node": "ex:TP53", "weight": 3,
                                   "attrs": {"khg-kind": "entity", "label": "TP53", "khg-types": ["Gene"]}}
    rec = {"kind": "entity", "id": "ex:X", "types": ["Person"], "label": "X", "aliases": ["x"], "redirect_to": "ex:Y",
           "version": 2, "recorded_at": "2026-01-01T00:00:00Z", "extensions": {"ex:note": "n", "hif:weight": 1.5}}
    c = {"header": c1["header"], "records": [rec]}
    node = hif.to_hif(c, schema)["nodes"][0]
    assert node == {"node": "ex:X", "weight": 1.5,
                    "attrs": {"khg-kind": "entity", "label": "X", "khg-types": ["Person"], "khg-aliases": ["x"],
                              "khg-redirect-to": "ex:Y", "khg-version": 2, "khg-recorded-at": "2026-01-01T00:00:00Z",
                              "khg-extensions": {"ex:note": "n"}}}


def test_edges_carry_the_hyperedge_fields(c1, schema):
    h = hif.to_hif(c1, schema)
    edges = {e["edge"]: e for e in h["edges"]}
    assert [e["edge"] for e in h["edges"]] == sorted(edges)
    sup = edges["f:born-skłodowska-kraków"]["attrs"]
    assert (sup["khg-status"], sup["khg-status-ref"]) == ("superseded", "m:sup-1")
    dep = edges["f:pop-łódź-2019-dep"]["attrs"]
    assert (dep["khg-rank"], dep["khg-rank-reason"]) == ("deprecated", ["wd:Q41755623"])
    assert edges["g:who-1774"]["attrs"]["khg-goal"]["owner"] == "agent:history-desk"
    assert edges["m:sup-1"]["attrs"]["khg-reason"] == "correction" and "khg-note" in edges["m:sup-1"]["attrs"]
    assert edges["f:route-1"]["attrs"]["khg-source-text"].startswith("Note by 𠮷田")
    assert edges["f:coadmin-1"]["attrs"]["khg-confidence"]["scale"] == "probability"
    assert all(set(e["attrs"]) >= {"relation", "khg-status", "khg-rank", "khg-visibility"} for e in h["edges"])
    assert all(k == "relation" or k.startswith("khg-") for e in h["edges"] for k in e["attrs"])


def test_weights_come_only_from_hif_weight_and_keep_their_json_type(c1, schema):
    h = hif.to_hif(c1, schema)
    weights = [(kind, x.get("node") or x.get("edge"), x["weight"]) for kind in ("nodes", "edges", "incidences")
               for x in h[kind] if "weight" in x]
    assert weights == [("nodes", "ex:TP53", 3), ("edges", "f:reg-1", 0.5), ("edges", "f:route-1", 2),
                       ("incidences", "ex:insulin", 0.25)]
    assert type(_node(h, "ex:TP53")["weight"]) is int
    assert _incidences(h, "f:coadmin-1")[0]["attrs"] == {"role": "agent", "khg-bid": "b1"}  # no khg-extensions left
    assert "hif:weight" not in json.dumps(h)


def test_binding_extensions_go_to_the_incidence(c1, schema):
    target = next(i for i in _incidences(hif.to_hif(c1, schema), "f:reg-1") if i["attrs"]["role"] == "target")
    assert target == {"edge": "f:reg-1", "node": "ex:TP53", "direction": "head",
                      "attrs": {"role": "target", "khg-bid": "b3",
                                "khg-extensions": {"ex:curation": {"checked": True, "by": ["curator:a", "curator:b"]}}}}


def test_an_empty_extensions_object_is_kept(c1, schema):
    c = copy.deepcopy(c1)
    c["records"][0]["extensions"] = {}
    node = hif.to_hif(c, schema)["nodes"][0]
    assert node["node"] == "ex:AirCanada" and node["attrs"]["khg-extensions"] == {} and "weight" not in node


def test_literal_labels_cover_every_datatype(c1, schema):
    labels = {n["attrs"]["label"] for n in hif.to_hif(c1, schema)["nodes"] if n["attrs"]["khg-kind"] == "literal"}
    assert {"+1914-12-20T00:00:00Z/11", "+1700-00-00T00:00:00Z/9 (Julian)", "+3.5 wd:Q11573 [+3, +4]", "+679941",
            "東京駅@ja", "Tokyo Station@en", "+35.6812,+139.7671", "true", "TYO",
            "https://www.tokyostationcity.com/"} <= labels
    assert hif.literal_label is literal_label
    assert literal_label({"datatype": "boolean", "value": False}) == "false"
    assert literal_label({"datatype": "quantity", "amount": "-2", "unit": "wd:Q11573"}) == "-2 wd:Q11573"
    assert literal_label({"datatype": "lang_string", "value": "Łódź", "lang": "PL"}) == "Łódź@pl"


def test_literal_nodes_are_shared_by_value(c1, schema):
    h = hif.to_hif(c1, schema)
    for n in h["nodes"]:
        if n["attrs"]["khg-kind"] == "literal":
            assert n["node"] == literal_node_id(n["attrs"]["khg-literal"])
            assert n["attrs"]["label"] == literal_label(n["attrs"]["khg-literal"])
            assert list(n["attrs"]) == ["khg-kind", "label", "khg-literal"]
    start = literal_node_id({"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11})
    assert {(i["edge"], i["attrs"]["role"]) for i in h["incidences"] if i["node"] == start} == {
        ("f:king-13", "end_time"), ("f:king-14", "start_time")}  # the same-day handover shares one node


def test_per_binding_literal_nodes(c1, schema):
    h = hif.to_hif(c1, schema, literal_nodes="per_binding")
    assert h["metadata"]["khg-literal-nodes"] == "per_binding"
    lits = [n for n in h["nodes"] if n["attrs"]["khg-kind"] == "literal"]
    assert len(lits) == 20 and all(n["node"].startswith("_:litb:") for n in lits)
    for i in h["incidences"]:
        if i["node"].startswith("_:litb:"):
            assert i["node"] == literal_binding_node_id(i["edge"], i["attrs"]["khg-bid"])
    shared = hif.to_hif(c1, schema)
    assert len(h["incidences"]) == len(shared["incidences"]) and h["edges"] == shared["edges"]
    assert validate_hif(h, schema=schema)["ok"]


def test_special_and_unbound_nodes_are_per_binding(c1, schema):
    h = hif.to_hif(c1, schema)
    specials = {n["node"]: n for n in h["nodes"] if n["attrs"]["khg-kind"] in ("somevalue", "novalue", "unbound")}
    assert specials == {
        special_node_id("somevalue", "f:born-scribe", "b2"): {
            "node": special_node_id("somevalue", "f:born-scribe", "b2"), "attrs": {"khg-kind": "somevalue"}},
        special_node_id("novalue", "f:cat-7", "b2"): {
            "node": special_node_id("novalue", "f:cat-7", "b2"), "attrs": {"khg-kind": "novalue"}},
        special_node_id("unbound", "g:who-1774", "b1"): {
            "node": special_node_id("unbound", "g:who-1774", "b1"),
            "attrs": {"khg-kind": "unbound", "khg-unbound": {"var": "who", "expect": {"entity_types": ["Person"]}}}},
    }
    assert all(nid[:5] in ("_:sv:", "_:nv:") or nid.startswith("_:var:") for nid in specials)


def test_fact_references_are_ref_nodes(c1, schema):
    h = hif.to_hif(c1, schema)
    refs = [n for n in h["nodes"] if n["attrs"]["khg-kind"] == "fact-ref"]
    assert [(n["node"], n["attrs"]["khg-ref"]) for n in refs] == [
        ("_:ref:f:born-louis14-paris", "f:born-louis14-paris"),
        ("_:ref:f:born-skłodowska-kraków", "f:born-skłodowska-kraków"),
        ("_:ref:f:born-skłodowska-warszawa", "f:born-skłodowska-warszawa")]
    assert not any("khg-external" in n["attrs"] for n in refs)  # every referenced fact is in the file


def test_directions_are_the_effective_ones(c1, schema):
    h = hif.to_hif(c1, schema)
    for rec in (r for r in c1["records"] if r["kind"] == "hyperedge"):
        for b in rec["bindings"]:
            inc = next(i for i in _incidences(h, rec["id"]) if i["attrs"]["khg-bid"] == b["bid"])
            usage = schema.usage(rec["relation"], b["role"])
            assert inc.get("direction") == (b.get("direction") or usage.get("direction"))
    undirected = {i["edge"] for i in h["incidences"] if "direction" not in i}
    assert undirected == {"f:loop-yyz", "f:married-curie"}
    assert h["network-type"] != "asc"


def test_an_ordered_role_keeps_its_positions(c1, schema):
    route = _incidences(hif.to_hif(c1, schema), "f:route-1")
    assert [(i["node"], i["attrs"]["role"], i["attrs"].get("role-position")) for i in route] == [
        ("ex:AirCanada", "carrier", None), ("ex:YYZ", "stop", 1), ("ex:YUL", "stop", 2), ("ex:YYZ", "stop", 3)]


def test_the_order_of_section_4_2(c1, schema):
    h = hif.to_hif(c1, schema)
    ids = [n["node"] for n in h["nodes"]]
    entities = [i for i in ids if not i.startswith("_:")]
    assert ids == entities + sorted(i for i in ids if i.startswith("_:")) and entities == sorted(entities)
    assert [i["edge"] for i in h["incidences"]] == sorted(i["edge"] for i in h["incidences"])
    assert hif.canonical_order(h) == h


def test_schema_document_inlines_the_schema(c1, schema, schema_doc, full):
    h = hif.to_hif(c1, schema, schema_document=True)
    assert h["metadata"].pop("khg-schema-document") == schema_doc
    assert h == full


def test_the_schema_may_be_a_document_or_a_path(c1, schema_doc, full):
    assert hif.to_hif(c1, schema_doc) == full
    assert hif.to_hif(data.path("fixture/fixture.c1.json"), data.path("fixture/fixture.relation-schema.json")) == full


def test_the_migrated_sample(c1):
    sample = data.load_json("sample/sample.khg.json")
    got = hif.to_hif(sample, data.path("sample/sample.relation-schema.json"))
    assert got == data.load_json("sample/sample.khg.hif.json")


# ------------------------------------------------------------------------------------------------ slices


def test_a_slice_of_claims_keeps_its_reference_as_external(c1, schema):
    h = hif.to_hif(c1, schema, relations=["claims"])
    assert h["metadata"]["khg-complete"] is False and h["metadata"]["khg-slice"] == {"relations": ["claims"]}
    assert [e["edge"] for e in h["edges"]] == ["f:claim-1"]
    assert _node(h, "_:ref:f:born-louis14-paris")["attrs"] == {
        "khg-kind": "fact-ref", "khg-ref": "f:born-louis14-paris", "khg-external": True}
    assert [n["node"] for n in h["nodes"] if n["attrs"]["khg-kind"] == "entity"] == ["ex:Chronicler_Ødegård"]
    assert validate_hif(h, schema=schema)["ok"]


def test_a_slice_is_closed_over_status_ref(c1, schema):
    h = hif.to_hif(c1, schema, relations=["born_in"])
    assert [e["edge"] for e in h["edges"]] == ["f:born-louis14-paris", "f:born-scribe", "f:born-skłodowska-kraków",
                                              "f:born-skłodowska-warszawa", "m:sup-1"]
    assert not any(n["attrs"].get("khg-external") for n in h["nodes"])
    only = hif.to_hif(c1, schema, relations=["khg:supersedes"])
    assert [e["edge"] for e in only["edges"]] == ["m:sup-1"]
    assert sorted(n["node"] for n in only["nodes"] if n["attrs"].get("khg-external")) == [
        "_:ref:f:born-skłodowska-kraków", "_:ref:f:born-skłodowska-warszawa"]


def test_select_slice(c1):
    s = hif.select_slice(c1, ["regulates"])
    assert s["header"]["complete"] is False and c1["header"]["complete"] is True
    assert [r["id"] for r in s["records"]] == ["ex:HeLa", "ex:TP53", "f:reg-1"]
    assert s["records"][1] is not c1["records"][12]  # a copy


def test_an_empty_slice(c1, schema):
    h = hif.to_hif(c1, schema, relations=[])
    assert (h["nodes"], h["edges"], h["incidences"]) == ([], [], [])
    assert h["metadata"]["khg-slice"] == {"relations": []}


# ------------------------------------------------------------------------------------------------ refusals


def test_bad_arguments(c1, schema):
    with pytest.raises(ValueError):
        hif.to_hif(c1, schema, literal_nodes="hub")
    with pytest.raises(TypeError):
        hif.to_hif(c1, schema, relations="claims")
    with pytest.raises(TypeError):
        hif.to_hif(c1, None)
    with pytest.raises(TypeError):
        hif.to_hif([c1], schema)
    with pytest.raises(ValidationError) as e:
        hif.to_hif(c1, schema, relations=["claim"])
    assert e.value.codes == ("KHG-S001",)


def test_a_container_pinned_to_another_schema_is_d009(c1, schema):
    c = copy.deepcopy(c1)
    c["header"]["schema"]["version"] = "1.0.1"
    with pytest.raises(ValidationError) as e:
        hif.to_hif(c, schema)
    assert e.value.codes == ("KHG-D009",)
    del c["header"]["schema"]  # no pin at all: the schema argument decides
    assert hif.to_hif(c, schema)["metadata"]["khg-schema-sha256"] == schema.sha256


def test_an_id_declared_twice_is_d001(c1, schema):
    history = data.load_json("fixture/fixture.history.c1.json")  # two versions of f:king-13
    with pytest.raises(ValidationError) as e:
        hif.to_hif(history, schema)
    assert e.value.codes == ("KHG-D001",)


@pytest.mark.parametrize(("change", "code"), [
    (lambda c: c["records"][22].update(relation="bornIn"), "KHG-S001"),
    (lambda c: c["records"][22]["bindings"][0].update(role="place"), "KHG-S002"),
    (lambda c: c["records"][22]["bindings"][0].update(value={"literal": {"datatype": "time", "time": "+1600",
                                                                         "precision": 11}}), "KHG-C004"),
    (lambda c: c["records"][22]["bindings"][0].update(value={"special": "withheld"}), "KHG-C002"),
    (lambda c: c["records"][22]["bindings"][0].pop("bid"), "KHG-C010"),
    (lambda c: c["records"][0].update(id=7), "KHG-C010"),
    (lambda c: c["header"].pop("document_id"), "KHG-C010"),
    (lambda c: c["records"][0].update(id="ex:" + "x" * 600), "KHG-P003"),
    (lambda c: c["header"]["extensions"]["hif:metadata"].update({"khg-profile": "x"}), "KHG-P008"),
    (lambda c: c["header"]["extensions"]["hif:metadata"].update({"default_attrs": {}}), "KHG-P008"),
])
def test_what_to_hif_refuses(c1, schema, change, code):
    c = copy.deepcopy(c1)
    change(c)
    with pytest.raises(ValidationError) as e:
        hif.to_hif(c, schema)
    assert code in e.value.codes


def _record(c, rid):
    return next(r for r in c["records"] if r.get("id") == rid)


@pytest.mark.parametrize("weight", ["0.5", True, None, [1], {}, float("nan"), float("inf")],
                         ids=["string", "bool", "null", "array", "object", "nan", "inf"])
@pytest.mark.parametrize("where", ["entity", "hyperedge", "binding"])
def test_a_hif_weight_that_is_not_a_finite_number_is_c010(c1, schema, where, weight):
    """§4.2: ``extensions["hif:weight"]`` becomes the HIF ``weight``, which HIF requires to be a number (H009). It was
    copied unchecked: a string, boolean, array or object gave an invalid file that ``from_hif`` and the loaders
    refused with H009, and null was dropped together with the whole ``extensions`` object."""
    c = copy.deepcopy(c1)
    owner = {"entity": lambda: _record(c, "ex:TP53"), "hyperedge": lambda: _record(c, "f:reg-1"),
             "binding": lambda: _record(c, "f:coadmin-1")["bindings"][0]}[where]()
    assert "hif:weight" in owner["extensions"]  # the fixture's weights: 3, 0.5 and 0.25
    owner["extensions"]["hif:weight"] = weight
    with pytest.raises(ValidationError) as e:
        hif.to_hif(c, schema)
    assert e.value.codes == ("KHG-C010",)
    assert "hif:weight" in e.value.info["findings"][0]["message"]


def test_a_hif_weight_of_any_json_number_is_written(c1, schema):
    """The other side: integers (a large one too) and floats pass, with their JSON number type."""
    c = copy.deepcopy(c1)
    _record(c, "ex:TP53")["extensions"]["hif:weight"] = 2 ** 40
    _record(c, "f:reg-1")["extensions"]["hif:weight"] = -1.5
    _record(c, "f:coadmin-1")["bindings"][0]["extensions"]["hif:weight"] = 0
    h = hif.to_hif(c, schema)
    assert _node(h, "ex:TP53")["weight"] == 2 ** 40 and next(e for e in h["edges"] if e["edge"] == "f:reg-1")[
        "weight"] == -1.5
    assert _incidences(h, "f:coadmin-1")[0]["weight"] == 0 and type(_incidences(h, "f:coadmin-1")[0]["weight"]) is int


@pytest.mark.parametrize("engine", ["jsonschema", "fastjsonschema"])
@pytest.mark.parametrize("options", [{}, {"relations": SLICE_RELATIONS}, {"literal_nodes": "per_binding"},
                                     {"schema_document": True}, {"relations": ["claims"]},
                                     {"relations": ["regulates", "position_held"], "literal_nodes": "per_binding"}])
def test_every_export_passes_the_vendored_schema_the_profile_and_decoding(c1, schema, options, engine):
    """G1 clause 1: the first HIF is valid against the vendored schema and the profile, under both engines; the
    full HIF pipeline (decoding, then C, S and D on the decoded container) finds no error either."""
    h = hif.to_hif(c1, schema, **options)
    assert layers.module("h").findings(h, engine=engine) == []  # the vendored schema, unchanged
    assert layers.module("p").findings(h, engine=engine) == []  # the profile schema and the Python checks
    assert hif.convention_findings(h) == []
    report = run(h, kind="hif", schema=schema, engine=engine)
    assert report.ok and report.skipped == [] and "d_decode" in dict(report.steps)
    assert {f["code"] for f in report.findings} <= {"KHG-S024", "KHG-L008"}  # the designed warnings (§1.4)


def test_to_hif_does_not_change_its_input(c1, schema):
    before = copy.deepcopy(c1)
    hif.to_hif(c1, schema, relations=["claims"], literal_nodes="per_binding", schema_document=True)
    assert c1 == before
