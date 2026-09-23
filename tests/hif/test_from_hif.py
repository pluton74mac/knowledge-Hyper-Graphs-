"""W6: HIF -> C1, ``from_hif`` and ``decode`` (DESIGN §4.3).

C1 -> HIF -> C1 gives the same canonical container, for the full fixture, its slices, per-binding literal nodes and
an inlined schema. Decoding refuses what §4.3 lists, with the registered codes.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from khg_contracts import data, hif, jsonio
from khg_contracts.errors import ValidationError
from khg_contracts.record import canonical_container

SLICE_RELATIONS = ["born_in", "catalysed_by", "claims", "co_administration_causes", "flight_route", "population",
                   "position_held", "regulates", "station_profile"]
ROLE_CONVENTION_FILES = ("basic", "two-roles", "tail-head", "ordered", "undirected")


def _same(a, b):
    return jsonio.canonical(a) == jsonio.canonical(b)


def _codes(fn, *args, **kw):
    with pytest.raises(ValidationError) as e:
        fn(*args, **kw)
    return e.value.codes


def _incidence(h, edge, bid):
    return next(i for i in h["incidences"] if i["edge"] == edge and i["attrs"]["khg-bid"] == bid)


# ------------------------------------------------------------------------------------------------ round trips


def test_the_fixture_decodes_to_the_fixture(c1, schema, full):
    back = hif.from_hif(full, schema)
    assert back == canonical_container(c1)  # from_hif returns the canonical container
    assert _same(back, c1)  # the fixture is canonical
    assert back["header"] == c1["header"]  # content snapshot, complete, hif:metadata title


def test_c1_to_hif_to_c1(c1, schema):
    assert _same(hif.from_hif(hif.to_hif(c1, schema), schema), c1)


def test_the_directed_slice_decodes_to_the_slice(c1, schema, directed_slice):
    back = hif.from_hif(directed_slice, schema)
    assert back["header"]["complete"] is False
    assert _same(back, canonical_container(hif.select_slice(c1, SLICE_RELATIONS)))
    assert len(back["records"]) == 20 + 16


def test_per_binding_literal_nodes_round_trip(c1, schema):
    assert _same(hif.from_hif(hif.to_hif(c1, schema, literal_nodes="per_binding"), schema), c1)


def test_an_inlined_schema_lets_from_hif_run_without_a_schema(c1, schema):
    h = hif.to_hif(c1, schema, schema_document=True)
    assert _same(hif.from_hif(h), c1)
    assert _same(hif.from_hif(h, schema), c1)


def test_a_slice_with_an_external_reference_decodes(c1, schema):
    back = hif.from_hif(hif.to_hif(c1, schema, relations=["claims"]), schema)
    claim = next(r for r in back["records"] if r["id"] == "f:claim-1")
    assert {"bid": "b2", "role": "claim", "value": {"fact": "f:born-louis14-paris"}} in claim["bindings"]
    assert [r["id"] for r in back["records"]] == ["ex:Chronicler_Ødegård", "f:claim-1"]


@pytest.mark.parametrize(("name", "relations"), [("full", None), ("slice", SLICE_RELATIONS)])
def test_the_library_free_steps_of_g1_give_the_golden_digests(c1, schema, name, relations):
    """The first HIF and the final C1 of the G1 chain (the plain SHA-256 of their canonical JSON), for the fixture
    and its directed slice; the library steps between them are W7's."""
    golden = jsonio.loads((Path(__file__).parents[1] / "gate" / "golden-sha256.json").read_bytes())
    want = golden["digests"][name]

    def sha(doc):
        return "sha256:" + hashlib.sha256(jsonio.canonical(doc).encode("utf-8")).hexdigest()

    first = hif.to_hif(c1, schema, relations=relations)
    assert sha(first) == want["hif"] == want["after_xgi"] == want["after_hnx"]
    assert sha(hif.from_hif(first, schema)) == want["c1"]


def test_from_hif_reads_paths_and_bytes(c1, schema):
    path = data.path("fixture/fixture.hif.json")
    assert _same(hif.from_hif(path, data.path("fixture/fixture.relation-schema.json")), c1)
    assert _same(hif.from_hif(path.read_bytes(), schema), c1)


def test_from_hif_does_not_change_its_input(full, schema):
    before = copy.deepcopy(full)
    hif.from_hif(full, schema)
    assert full == before


# ------------------------------------------------------------------------------------------------ what decoding reads


def test_directions_equal_to_the_usage_are_dropped_and_native_ones_kept(full, schema):
    h = copy.deepcopy(full)
    married = _incidence(h, "f:married-curie", "b1")
    married["direction"] = "tail"  # a native direction where the usage declares none
    back = hif.from_hif(h, schema)
    rec = {r["id"]: r for r in back["records"]}
    assert all("direction" not in b for b in rec["f:reg-1"]["bindings"])  # equal to the usage default: dropped
    spouse = next(b for b in rec["f:married-curie"]["bindings"] if b["bid"] == "b1")
    assert spouse["direction"] == "tail"
    del _incidence(h, "f:reg-1", "b2")["direction"]  # absent: the usage's applies
    assert all("direction" not in b for b in {r["id"]: r for r in hif.from_hif(h, schema)["records"]}["f:reg-1"][
        "bindings"])


def test_weights_and_extensions_decode_into_extensions(full, schema):
    rec = {r["id"]: r for r in hif.from_hif(full, schema)["records"]}
    assert rec["ex:TP53"]["extensions"] == {"hif:weight": 3} and type(rec["ex:TP53"]["extensions"]["hif:weight"]) is int
    assert rec["f:reg-1"]["extensions"] == {"hif:weight": 0.5}
    assert rec["f:route-1"]["extensions"] == {"hif:weight": 2}
    b1 = next(b for b in rec["f:coadmin-1"]["bindings"] if b["bid"] == "b1")
    assert b1["extensions"] == {"hif:weight": 0.25}
    b3 = next(b for b in rec["f:reg-1"]["bindings"] if b["bid"] == "b3")
    assert b3["extensions"] == {"ex:curation": {"checked": True, "by": ["curator:a", "curator:b"]}}


def test_weights_merge_with_khg_extensions(full, schema):
    h = copy.deepcopy(full)
    inc = _incidence(h, "f:reg-1", "b3")
    inc["weight"] = 1
    b3 = next(b for b in {r["id"]: r for r in hif.from_hif(h, schema)["records"]}["f:reg-1"]["bindings"]
              if b["bid"] == "b3")
    assert b3["extensions"] == {"ex:curation": {"checked": True, "by": ["curator:a", "curator:b"]}, "hif:weight": 1}


def test_an_empty_extensions_object_round_trips(c1, schema):
    c = copy.deepcopy(c1)
    c["records"][0]["extensions"] = {}
    c["records"][30]["bindings"][0]["extensions"] = {}
    assert _same(hif.from_hif(hif.to_hif(c, schema), schema), canonical_container(c))


def test_metadata_passes_through_to_hif_metadata(full, schema):
    h = copy.deepcopy(full)
    h["metadata"]["description"] = {"lang": "en", "text": "a fixture"}
    header = hif.from_hif(h, schema)["header"]
    assert header["extensions"] == {"hif:metadata": {"title": "P2 gate fixture (adversarial)",
                                                     "description": {"lang": "en", "text": "a fixture"}}}
    assert header["content"] == "snapshot" and header["schema"] == schema.header
    del h["metadata"]["title"], h["metadata"]["description"], h["metadata"]["khg-complete"]
    header = hif.from_hif(h, schema)["header"]
    assert "extensions" not in header and "complete" not in header


def test_decode_returns_the_container_as_written(full, schema):
    container, findings = hif.decode(full, schema)
    assert findings == []
    assert [r["id"] for r in container["records"]] == [n["node"] for n in full["nodes"]
                                                       if n["attrs"]["khg-kind"] == "entity"] + [
        e["edge"] for e in full["edges"]]
    reg = next(r for r in container["records"] if r["id"] == "f:reg-1")
    assert [b["bid"] for b in reg["bindings"]] == ["b1", "b2", "b3"]  # incidence order


# ------------------------------------------------------------------------------------------------ refusals


def test_without_a_schema_and_without_an_inlined_one_is_d009(full):
    assert _codes(hif.from_hif, full) == ("KHG-D009",)


def test_a_schema_that_differs_from_the_declared_one_is_d009(full, schema_doc):
    other = copy.deepcopy(schema_doc)
    other["version"] = "1.0.1"
    assert _codes(hif.from_hif, full, other) == ("KHG-D009",)
    h = copy.deepcopy(full)
    h["metadata"]["khg-schema"] = "p2-gate/1.0.1"
    assert _codes(hif.from_hif, h, schema_doc) == ("KHG-D009",)


def test_an_invalid_inlined_schema_raises_its_m_codes(full, schema_doc):
    h = copy.deepcopy(full)
    h["metadata"]["khg-schema-document"] = dict(copy.deepcopy(schema_doc), relations=[{"id": "r", "roles": []}])
    codes = _codes(hif.from_hif, h)
    assert codes and all(c.startswith("KHG-M") for c in codes)


@pytest.mark.parametrize("name", ROLE_CONVENTION_FILES)
def test_a_file_without_the_profile_is_p001(name, schema):
    codes = _codes(hif.from_hif, data.load_json(f"role-convention/{name}.hif.json"), schema)
    assert codes[0] == "KHG-P001"


def test_from_hif_raises_the_first_failing_layer(full, schema):
    h = copy.deepcopy(full)
    h["metadata"]["khg-profile"] = "khg-hif/2.0.0"
    assert _codes(hif.from_hif, h, schema) == ("KHG-V001",)
    h = copy.deepcopy(full)
    h["incidences"][0]["direction"] = "sideways"
    assert _codes(hif.from_hif, h, schema) == ("KHG-H005",)
    h = copy.deepcopy(full)
    del h["metadata"]["role-convention"]
    assert _codes(hif.from_hif, h, schema) == ("KHG-R003",)
    with pytest.raises(ValidationError) as e:
        hif.from_hif(b'{"incidences": [], "incidences": []}', schema)
    assert e.value.codes == ("KHG-J003",)


def _decoding_codes(h, schema):
    container, findings = hif.decode(h, schema)
    assert container is None
    return sorted({f["code"] for f in findings})


def test_decoding_refuses_duplicates_and_undeclared_references(full, schema):
    h = copy.deepcopy(full)
    h["nodes"].append(copy.deepcopy(h["nodes"][0]))
    h["edges"].append(copy.deepcopy(h["edges"][0]))
    assert _decoding_codes(h, schema) == ["KHG-D001"]
    h = copy.deepcopy(full)
    _incidence(h, "f:reg-1", "b1")["node"] = "ex:MDM2"
    _incidence(h, "f:reg-1", "b2")["edge"] = "f:reg-9"
    assert _decoding_codes(h, schema) == ["KHG-D002", "KHG-D003"]
    assert _codes(hif.from_hif, h, schema) == ("KHG-D002", "KHG-D003")


def test_decoding_checks_every_derived_id(full, schema):
    h = copy.deepcopy(full)
    lit = next(n for n in h["nodes"] if n["attrs"]["khg-kind"] == "literal")
    lit["attrs"]["khg-literal"] = {"datatype": "string", "value": "changed"}  # _:lit: no longer its digest
    assert _decoding_codes(h, schema) == ["KHG-D005"]
    h = copy.deepcopy(full)
    ref = next(n for n in h["nodes"] if n["attrs"]["khg-kind"] == "fact-ref")
    ref["attrs"]["khg-ref"] = "f:born-scribe"  # khg-ref is authoritative and must match the id
    assert _decoding_codes(h, schema) == ["KHG-D005"]
    h = copy.deepcopy(full)
    _incidence(h, "f:cat-7", "b2")["attrs"]["khg-bid"] = "b3"  # the novalue node of b2, now under b3
    assert _decoding_codes(h, schema) == ["KHG-D005"]
    h = hif.to_hif(hif.from_hif(full, schema), schema, literal_nodes="per_binding")
    litb = _incidence(h, "f:claim-1", "b3")
    _incidence(h, "f:king-13", "b3")["node"] = litb["node"]  # another binding's per-binding node
    assert _decoding_codes(h, schema) == ["KHG-D005"]


def test_decoding_refuses_a_malformed_literal_with_its_own_codes(full, schema):
    h = copy.deepcopy(full)
    lit = next(n for n in h["nodes"] if n["attrs"]["khg-kind"] == "literal")
    lit["attrs"]["khg-literal"] = {"datatype": "time", "time": "+0000-01-01T00:00:00Z", "precision": 11,
                                   "calendar": "julian"}  # year 0 does not exist
    container, findings = hif.decode(h, schema)
    assert container is None
    assert [(f["code"], f["path"]) for f in findings] == [("KHG-S006", f"/nodes/{h['nodes'].index(lit)}/attrs/"
                                                                       "khg-literal")]


def test_a_contradicting_direction_is_s016_while_decoding(full, schema):
    h = copy.deepcopy(full)
    _incidence(h, "f:reg-1", "b2")["direction"] = "head"  # regulator is tail (MC063)
    container, findings = hif.decode(h, schema)
    assert container is None
    assert [(f["code"], f["path"]) for f in findings] == [
        ("KHG-S016", f"/incidences/{h['incidences'].index(_incidence(h, 'f:reg-1', 'b2'))}/direction")]


def test_undeclared_relations_and_roles_are_s001_and_s002_while_decoding(full, schema):
    h = copy.deepcopy(full)
    h["edges"][0]["attrs"]["relation"] = "bornIn"
    _incidence(h, "f:reg-1", "b1")["attrs"]["role"] = "tissue"
    assert _decoding_codes(h, schema) == ["KHG-S001", "KHG-S002"]


def test_references_outside_the_file(full, directed_slice, schema):
    h = copy.deepcopy(full)
    next(n for n in h["nodes"] if n["node"] == "_:ref:f:born-louis14-paris")["attrs"]["khg-external"] = True
    assert _codes(hif.from_hif, h, schema) == ("KHG-P017",)  # the P layer, before decoding
    assert _decoding_codes(h, schema) == ["KHG-P017"]  # and decoding alone
    h = copy.deepcopy(directed_slice)
    h["edges"] = [e for e in h["edges"] if e["edge"] != "f:born-louis14-paris"]
    h["incidences"] = [i for i in h["incidences"] if i["edge"] != "f:born-louis14-paris"]
    assert _decoding_codes(h, schema) == ["KHG-D002"]  # a missing fact that is not marked external


def test_a_directed_file_needs_every_direction(directed_slice, schema):
    h = copy.deepcopy(directed_slice)
    del h["incidences"][0]["direction"]
    assert _codes(hif.from_hif, h, schema) == ("KHG-P010",)
    assert _decoding_codes(h, schema) == ["KHG-P010"]


def test_a_repeated_bid_is_p016(full, schema):
    h = copy.deepcopy(full)
    _incidence(h, "f:reg-1", "b3")["attrs"]["khg-bid"] = "b2"
    assert _codes(hif.from_hif, h, schema) == ("KHG-P016",)
    assert _decoding_codes(h, schema) == ["KHG-P016"]


def test_decoding_reports_every_problem_it_finds(full, schema):
    h = copy.deepcopy(full)
    h["metadata"]["khg-schema-sha256"] = "sha256:" + "0" * 64
    h["nodes"].append(copy.deepcopy(h["nodes"][3]))
    _incidence(h, "f:reg-1", "b2")["direction"] = "head"
    assert _decoding_codes(h, schema) == ["KHG-D001", "KHG-D009", "KHG-S016"]
