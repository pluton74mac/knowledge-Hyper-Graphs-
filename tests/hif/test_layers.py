"""W6: the layer modules H, R, P and ``d_decode`` (DESIGN §8.1), and the profile's Python checks.

- H runs the vendored schema, unchanged, on HIF and role-convention files; P runs the profile schema without
  repeating H's findings, then the Python checks (P004, P017, P010, P011, P016).
- Decoding reads only files that passed H, R and P, and hands the decoded container to C, S and ``d_container``.
"""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, hif
from khg_contracts.schema import load_schema
from khg_contracts.validate import layers, run
from khg_contracts.validate.context import Context

SCHEMA = load_schema(data.load_json("fixture/fixture.relation-schema.json"))
ENGINES = ("jsonschema", "fastjsonschema")


def _full():
    return data.load_json("fixture/fixture.hif.json")


def _slice():
    return data.load_json("fixture/fixture.directed-slice.hif.json")


def _p(doc):
    return [(f["code"], f["path"]) for f in hif.profile_findings(doc)]


def test_the_w6_modules_are_implemented():
    for name, letter in (("h", "H"), ("r", "R"), ("p", "P"), ("d_decode", "D")):
        module = layers.module(name)
        assert (module.LETTER, module.OWNER, module.IMPLEMENTED) == (letter, "W6", True)
        assert "TODO" not in (module.__doc__ or "")


@pytest.mark.parametrize("engine", ENGINES)
def test_h_is_the_vendored_schema_on_both_kinds(engine):
    h = layers.module("h")
    assert h.findings(_full(), engine=engine) == []
    bad = _full()
    bad["network-type"] = "hyper"
    assert [(f["code"], f["path"]) for f in h.findings(bad, engine=engine)] == [("KHG-H008", "/network-type")]
    rc = data.load_json("role-convention/basic.hif.json")
    rc["version"] = "1"
    report = run(rc, engine=engine)
    assert report.kind == "role-convention" and [f["code"] for f in report.errors] == ["KHG-H002"]


@pytest.mark.parametrize("engine", ENGINES)
def test_p_does_not_repeat_the_findings_of_h(engine):
    bad = _full()
    bad["nodes"][12]["node"] = 1.5  # H007 in the vendored schema, P002 in the profile's id definition
    found = layers.module("p").findings(bad, engine=engine)
    assert {f["layer"] for f in found} <= {"P"}
    report = run(bad, kind="hif", schema=SCHEMA, engine=engine)
    # fastjsonschema stops at the first violation, the vendored schema's (the first branch of the allOf)
    want_p = [("p", ["KHG-P002"])] if engine == "jsonschema" else []
    assert [(name, sorted({f["code"] for f in fs})) for name, fs in report.steps if fs] == [
        ("h", ["KHG-H007"])] + want_p


@pytest.mark.parametrize("engine", ENGINES)
def test_p_accepts_the_three_khg_files(engine):
    p = layers.module("p")
    for doc in (_full(), _slice(), data.load_json("sample/sample.khg.hif.json")):
        assert p.findings(doc, engine=engine) == []


# ------------------------------------------------------------------------------------------------ the Python checks


def test_p004_reserved_prefixes():
    doc = _full()
    assert _p(doc) == []
    doc["nodes"][0]["node"] = "_:AirCanada"
    doc["nodes"][22]["node"] = "_:sv:" + doc["nodes"][22]["node"][6:]  # a literal node with another kind's prefix
    ref = next(n for n in doc["nodes"] if n["attrs"]["khg-kind"] == "fact-ref")
    ref["node"] = "f:born-louis14-paris"
    assert _p(doc) == [("KHG-P004", "/nodes/0/node"), ("KHG-P004", "/nodes/22/node"),
                       ("KHG-P004", f"/nodes/{doc['nodes'].index(ref)}/node")]
    litb = hif.to_hif(hif.from_hif(_full(), SCHEMA), SCHEMA, literal_nodes="per_binding")
    assert _p(litb) == []  # _:litb: is a literal prefix too


def test_p017_external_references():
    doc = _full()
    ref = next(n for n in doc["nodes"] if n["node"] == "_:ref:f:born-louis14-paris")
    ref["attrs"]["khg-external"] = True
    j = doc["nodes"].index(ref)
    assert _p(doc) == [("KHG-P017", f"/nodes/{j}/attrs/khg-external")]  # outside a slice
    doc["metadata"]["khg-slice"] = {"relations": ["claims"]}
    assert _p(doc) == [("KHG-P017", f"/nodes/{j}/attrs/khg-external")]  # a slice, but the fact is in the file
    doc["edges"] = [e for e in doc["edges"] if e["edge"] != "f:born-louis14-paris"]
    assert _p(doc) == []


def test_p010_and_p011_the_direction_rule():
    doc = _slice()
    del doc["incidences"][3]["direction"], doc["incidences"][7]["direction"]
    assert _p(doc) == [("KHG-P010", "/incidences/3"), ("KHG-P010", "/incidences/7")]
    doc = _slice()
    doc["network-type"] = "undirected"
    assert _p(doc) == [("KHG-P011", "/network-type")]
    del doc["network-type"]  # absent: HIF reads it as undirected
    assert _p(doc) == [("KHG-P011", "/network-type")]
    full = _full()
    assert full["network-type"] == "undirected" and _p(full) == []  # native directions stay in undirected files
    full["incidences"] = []
    assert _p(full) == []


def test_p016_a_repeated_bid_in_one_edge():
    doc = _full()
    doc["incidences"][40]["attrs"]["khg-bid"] = "b2"
    doc["incidences"][41]["attrs"]["khg-bid"] = "b3"  # f:route-1 b1 -> b3: repeated in f:route-1
    assert _p(doc) == [("KHG-P016", "/incidences/40/attrs/khg-bid"), ("KHG-P016", "/incidences/43/attrs/khg-bid")]


def test_the_python_checks_read_any_document():
    for doc in ({}, [], {"nodes": {}, "edges": 1, "incidences": "x"}, {"nodes": [1, [], {"node": 3}]},
                {"nodes": [{"node": "_:x", "attrs": []}], "incidences": [{"attrs": {"khg-bid": ["b1"]}}] * 2},
                {"metadata": 1, "network-type": "directed", "incidences": [{}]}):
        hif.profile_findings(doc)
    assert _p({"network-type": "directed", "incidences": [{"edge": "e", "node": "n"}]}) == [
        ("KHG-P010", "/incidences/0")]


# ------------------------------------------------------------------------------------------------ decoding


def test_decoding_leaves_the_container_for_c_s_and_d(monkeypatch):
    seen = {}
    s_run = layers.module("s").run

    def spy(ctx):
        seen["c1"] = ctx.container
        return s_run(ctx)

    monkeypatch.setattr(layers.module("s"), "run", spy)
    report = run(_full(), kind="hif", schema=SCHEMA)
    assert report.ok
    container = seen["c1"]
    assert container["header"]["document_id"] == "p2-gate-fixture" and len(container["records"]) == 40
    assert [f["path"] for f in report.findings if f["code"] == "KHG-S024"] == ["/records/31"]  # f:loop-yyz


def test_decoding_records_and_reads_the_outcome_of_h_r_and_p():
    ctx = Context(kind="hif", doc=_full(), schema=SCHEMA)
    for name in ("h", "r", "p"):
        layers.module(name).run(ctx)
    assert ctx.state["hif_layers"] == {"H": True, "R": True, "P": True}
    assert layers.module("d_decode").run(ctx) == [] and "c1" in ctx.state
    bad = _full()
    bad["metadata"]["khg-literal-nodes"] = "hub"  # P009
    ctx = Context(kind="hif", doc=bad, schema=SCHEMA)
    for name in ("h", "r", "p"):
        layers.module(name).run(ctx)
    assert ctx.state["hif_layers"] == {"H": True, "R": True, "P": False}
    assert layers.module("d_decode").run(ctx) == [] and "c1" not in ctx.state


@pytest.mark.parametrize("engine", ENGINES)
def test_decoding_checks_h_r_and_p_itself_when_they_did_not_run(engine):
    report = run(_full(), kind="hif", schema=SCHEMA, steps=["j", "d_decode", "s"], engine=engine)
    assert [name for name, _ in report.steps] == ["j", "d_decode", "s"]
    assert [f["code"] for f in report.findings] == ["KHG-S024"]  # decoded, then checked by S
    bad = _full()
    bad["nodes"][12]["node"] = "_:TP53"  # P004
    report = run(bad, kind="hif", schema=SCHEMA, steps=["j", "d_decode", "s"], engine=engine)
    assert report.findings == [] and report.ok  # not decoded: the P findings belong to the P step


def test_decoding_resolves_the_schema_once():
    report = run(_full(), kind="hif")
    assert [(name, f["code"], f["path"]) for name, fs in report.steps for f in fs] == [
        ("d_decode", "KHG-D009", "/metadata/khg-schema")]
    inl = hif.to_hif(hif.from_hif(_full(), SCHEMA), SCHEMA, schema_document=True)
    assert run(inl, kind="hif").ok
    inl["metadata"]["khg-schema-document"]["version"] = "1"  # M004; the digest no longer matches either
    report = run(inl, kind="hif")
    assert [(name, f["code"]) for name, fs in report.steps for f in fs if f["severity"] == "error"] == [
        ("d_decode", "KHG-M004")]
    assert report.first_layer == "M"


def test_decoding_keeps_strings_as_written_for_layer_s():
    doc = _full()
    assert doc["nodes"][2]["node"] == "ex:HeLa"
    doc["nodes"][2]["attrs"]["label"] = "Cafe\u0301"  # not NFC
    report = run(doc, kind="hif", schema=SCHEMA)
    assert [(f["code"], f["path"]) for f in report.errors] == [("KHG-S020", "/records/2/label")]
    assert hif.from_hif(doc, SCHEMA)["records"][2]["label"] == "Caf\u00e9"  # from_hif returns the canonical form


def test_the_steps_the_loaders_run():
    assert hif.PROFILE_STEPS == ("j", "v", "h", "r", "p")
    report = run(_full(), kind="hif", steps=hif.PROFILE_STEPS)
    assert report.ok and report.findings == [] and [name for name, _ in report.steps] == list(hif.PROFILE_STEPS)
    bad = copy.deepcopy(_full())
    bad["network-type"] = "asc"
    assert [f["code"] for f in run(bad, kind="hif", steps=hif.PROFILE_STEPS).errors] == ["KHG-P007"]
    assert run(bad, kind="role-convention", steps=["j", "h", "r"]).ok  # asc is valid HIF
