"""G1: a record round-trips C1 -> HIF -> XGI -> HIF -> HyperNetX -> HIF -> C1 with its roles intact (DESIGN §1.2).

The seven assertions of the G1 list, each for ``fixture.c1.json`` and for its directed slice:

1. the chain ``to_hif`` -> ``load_xgi`` -> ``export_xgi`` -> ``load_hnx`` -> ``export_hnx`` -> ``from_hif`` runs, and
   the first HIF is valid against the vendored schema and the profile under both engines;
2. the canonical serialisation of every intermediate HIF equals the first HIF's (metadata, ``network-type``, node,
   edge and incidence records, weights, extensions and order);
3. ``compare_containers(original, final) == []``, headers included;
4. both export reports are empty;
5. the library objects are right: XGI member sets, the tail and head sets of the ``DiHypergraph`` (``ex:TP53`` in both
   ``"in"`` and ``"out"`` of ``f:reg-1``), and in every HyperNetX cell the first record's role, with
   ``khg-extra-incidences`` holding the rest;
6. two native edits are reflected: a HyperNetX ``rename``, and an XGI membership removal (which raises) followed by
   its re-addition (an identical export);
7. five child processes (``PYTHONHASHSEED`` 0-3 and unset) print the digests of every intermediate document; all five
   agree and equal ``golden-sha256.json``.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import data, hif, jsonio, loaders
from khg_contracts.errors import LoaderError
from khg_contracts.record import canonical_container
from khg_contracts.schema import Schema, load_schema
from khg_contracts.store import compare_containers
from khg_contracts.validate import ENGINES, layers, run, validate_hif

xgi = pytest.importorskip("xgi")
hypernetx = pytest.importorskip("hypernetx")

pytestmark = [pytest.mark.gate, pytest.mark.libs]

HERE = Path(__file__).resolve().parent
PACKAGED = {"full": "fixture/fixture.hif.json", "slice": "fixture/fixture.directed-slice.hif.json"}
#: The four weights of §4.2: (kind, id, weight), and the incidence weight as (edge, bid).
WEIGHTS = {("node", "ex:TP53"): 3, ("edge", "f:reg-1"): 0.5, ("edge", "f:route-1"): 2}
INCIDENCE_WEIGHT = (("f:coadmin-1", "b1"), 0.25)
EXTENSION = {"ex:curation": {"checked": True, "by": ["curator:a", "curator:b"]}}
#: The designed warnings of the full validator (§1.4): S024 on f:loop-yyz, which the slice leaves out, and L008.
DESIGNED_WARNINGS = {"full": ["KHG-S024", "KHG-L008"], "slice": ["KHG-L008"]}


@dataclass
class Chain:
    """One run of the chain and every intermediate object."""

    name: str
    schema: Schema
    original: dict[str, Any]
    h0: dict[str, Any]
    bx: loaders.Bundle
    h1: dict[str, Any]
    bh: loaders.Bundle
    h2: dict[str, Any]
    back: dict[str, Any]


def _slice_relations() -> list[str]:
    return data.load_json(PACKAGED["slice"])["metadata"]["khg-slice"]["relations"]


def _run_chain(name: str) -> Chain:
    c1 = data.load_json("fixture/fixture.c1.json")
    schema = load_schema(data.load_json("fixture/fixture.relation-schema.json"))
    relations = None if name == "full" else _slice_relations()
    original = c1 if relations is None else hif.select_slice(c1, relations)
    h0 = hif.to_hif(c1, schema, relations=relations)
    bx = loaders.load_xgi(copy.deepcopy(h0))
    h1 = loaders.export_xgi(bx)
    bh = loaders.load_hnx(copy.deepcopy(h1))
    h2 = loaders.export_hnx(bh)
    back = hif.from_hif(h2, schema)
    return Chain(name, schema, original, h0, bx, h1, bh, h2, back)


@pytest.fixture(scope="module", params=["full", "slice"])
def chain(request) -> Chain:
    return _run_chain(request.param)


def _memberships(doc: dict[str, Any]) -> dict[str, set[tuple[str, str | None]]]:
    out: dict[str, set[tuple[str, str | None]]] = {}
    for i in doc["incidences"]:
        out.setdefault(i["edge"], set()).add((i["node"], i.get("direction")))
    return out


# ------------------------------------------------------------------------------------------------ 1. the chain runs


def test_1_the_first_hif_is_the_packaged_file_and_valid_under_both_engines(chain):
    assert chain.h0 == data.load_json(PACKAGED[chain.name])
    for engine in ENGINES:
        assert layers.module("h").findings(chain.h0, engine=engine) == []  # the vendored HIF schema
        assert layers.module("r").findings(chain.h0, engine=engine) == []  # role-convention 1.0.0
        assert layers.module("p").findings(chain.h0, engine=engine) == []  # the khg-hif/1.0.0 profile
        report = run(chain.h0, kind="hif", engine=engine, steps=hif.PROFILE_STEPS)
        assert report.ok and report.findings == []
        full = validate_hif(chain.h0, schema=chain.schema, engine=engine)
        assert full["ok"]
        assert [f["code"] for f in full["findings"]] == DESIGNED_WARNINGS[chain.name]
        assert {f["severity"] for f in full["findings"]} == {"warning"}


def test_1_the_chain_builds_the_expected_library_classes(chain):
    assert type(chain.bx.graph) is (xgi.DiHypergraph if chain.name == "slice" else xgi.Hypergraph)
    assert isinstance(chain.bh.graph, hypernetx.Hypergraph)
    assert chain.h0["network-type"] == ("directed" if chain.name == "slice" else "undirected")
    assert chain.bx.context.profile and chain.bh.context.profile


# ------------------------------------------------------------------------------------------------ 2. same HIF


def test_2_every_intermediate_hif_is_canonically_equal_to_the_first(chain):
    first = jsonio.canonical(chain.h0)
    assert jsonio.canonical(chain.h1) == first
    assert jsonio.canonical(chain.h2) == first


@pytest.mark.parametrize("step", ["h1", "h2"])
def test_2_metadata_network_type_records_and_order_survive_each_step(chain, step):
    h = getattr(chain, step)
    assert h["metadata"] == chain.h0["metadata"] and len(h["metadata"]) >= 11
    assert h["network-type"] == chain.h0["network-type"]
    for key in ("nodes", "edges", "incidences"):
        assert h[key] == chain.h0[key]  # the records and their order
    assert [n["node"] for n in h["nodes"]] == [n["node"] for n in chain.h0["nodes"]]
    assert [(i["edge"], i["attrs"]["khg-bid"]) for i in h["incidences"]] == \
        [(i["edge"], i["attrs"]["khg-bid"]) for i in chain.h0["incidences"]]


@pytest.mark.parametrize("step", ["h0", "h1", "h2"])
def test_2_the_four_weights_keep_their_json_number_type(chain, step):
    h = getattr(chain, step)
    got = {("node", n["node"]): n["weight"] for n in h["nodes"] if "weight" in n}
    got.update({("edge", e["edge"]): e["weight"] for e in h["edges"] if "weight" in e})
    assert got == WEIGHTS
    assert type(got[("node", "ex:TP53")]) is int and type(got[("edge", "f:route-1")]) is int
    assert type(got[("edge", "f:reg-1")]) is float
    (edge, bid), weight = INCIDENCE_WEIGHT
    weighted = [(i["edge"], i["attrs"]["khg-bid"], i["weight"]) for i in h["incidences"] if "weight" in i]
    assert weighted == [(edge, bid, weight)]


@pytest.mark.parametrize("step", ["h1", "h2"])
def test_2_binding_extensions_survive_each_step(chain, step):
    b3 = [i for i in getattr(chain, step)["incidences"] if i["edge"] == "f:reg-1" and i["attrs"]["khg-bid"] == "b3"]
    assert b3 == [{"edge": "f:reg-1", "node": "ex:TP53", "direction": "head",
                   "attrs": {"role": "target", "khg-bid": "b3", "khg-extensions": EXTENSION}}]


# ------------------------------------------------------------------------------------------------ 3. same C1


def test_3_the_final_container_equals_the_original_headers_included(chain):
    want = canonical_container(chain.original)
    assert chain.back["header"] == want["header"]
    assert chain.back["header"]["complete"] is (chain.name == "full")
    assert jsonio.canonical(chain.back) == jsonio.canonical(want)
    assert len(chain.back["records"]) == len(want["records"])


def test_3_compare_containers_finds_no_difference(chain):
    assert compare_containers(chain.original, chain.back, ignore=()) == []
    assert compare_containers(chain.original, chain.back) == []


# ------------------------------------------------------------------------------------------------ 4. empty reports


def test_4_both_export_reports_are_empty(chain):
    for bundle in (chain.bx, chain.bh):
        assert bundle.report == loaders.report.new_report()
        assert set(bundle.report) == set(loaders.REPORT_KEYS)


# ------------------------------------------------------------------------------------------------ 5. library objects


def test_5_xgi_member_sets_equal_the_hif_memberships(chain):
    graph, members = chain.bx.graph, _memberships(chain.h0)
    assert sorted(graph.edges) == sorted(members)
    if chain.name == "slice":
        for e, pairs in members.items():
            tail, head = graph.edges.dimembers(e)
            assert tail == {n for n, d in pairs if d == "tail"}
            assert head == {n for n, d in pairs if d == "head"}
        tail, head = graph.edges.dimembers("f:reg-1")
        assert "ex:TP53" in tail and "ex:TP53" in head  # regulator (in) and target (out)
    else:
        for e, pairs in members.items():
            assert graph.edges.members(e) == {n for n, _ in pairs}
        assert "ex:Mazarin" in graph.nodes and graph.nodes.degree["ex:Mazarin"] == 0  # the isolated entity


def test_5_no_metadata_is_written_into_xgi_network_attributes(chain):
    for key in chain.h0["metadata"]:
        with pytest.raises(xgi.exception.XGIError):
            chain.bx.graph[key]
    assert chain.bx.context.metadata == chain.h0["metadata"]


def test_5_xgi_node_and_edge_attrs_are_the_hif_attrs(chain):
    for n in chain.h0["nodes"]:
        assert chain.bx.graph.nodes[n["node"]] == n["attrs"]
    for e in chain.h0["edges"]:
        assert chain.bx.graph.edges[e["edge"]] == e["attrs"]


def test_5_every_hypernetx_cell_holds_the_first_record_and_the_rest_under_the_reserved_key(chain):
    pairs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for i in chain.h1["incidences"]:
        pairs.setdefault((i["edge"], i["node"]), []).append(i)
    graph = chain.bh.graph
    assert len(graph.incidences.to_dataframe) == len(pairs)
    repeated = 0
    for (e, n), recs in pairs.items():
        cell = graph.get_cell_properties(e, n)
        assert cell["role"] == recs[0]["attrs"]["role"]
        assert cell["khg-bid"] == recs[0]["attrs"]["khg-bid"]
        assert cell.get("role-position") == recs[0]["attrs"].get("role-position")
        if "direction" in recs[0]:  # the direction column; seven incidences of the full file have none
            assert cell["direction"] == recs[0]["direction"]
        assert cell["weight"] == recs[0].get("weight", 1)  # the cell weight column
        assert cell.get(loaders.EXTRA, []) == recs[1:]
        repeated += len(recs) > 1
    assert repeated == 3 if chain.name == "full" else repeated == 2  # f:reg-1, f:route-1 and f:loop-yyz (full)


def test_5_roles_are_intact_in_both_libraries(chain):
    for bundle in (chain.bx, chain.bh):
        assert bundle.roles("f:reg-1", "ex:TP53") == ["regulator", "target"]
        assert bundle.roles("f:route-1", "ex:YYZ") == ["stop", "stop"]
        assert [r["attrs"]["role-position"] for r in bundle.records("f:route-1", "ex:YYZ")] == [1, 3]
    for i in chain.h0["incidences"]:
        assert i["attrs"]["role"] in chain.bh.roles(i["edge"], i["node"])
        assert i["attrs"]["role"] in chain.bx.roles(i["edge"], i["node"])


# ------------------------------------------------------------------------------------------------ 6. native edits


def test_6_a_hypernetx_rename_is_reflected(chain):
    bundle = loaders.load_hnx(copy.deepcopy(chain.h0))
    bundle.graph.rename(nodes={"ex:HeLa": "ex:HeLa-cells"})
    out = loaders.export_hnx(bundle)
    assert bundle.report["moved"] == [{"edge": "f:reg-1", "bid": "b1", "from": "ex:HeLa", "to": "ex:HeLa-cells"}]
    assert bundle.report["moved_conflict"] == [] and bundle.report["stale"] == []
    assert [n["attrs"] for n in out["nodes"] if n["node"] == "ex:HeLa-cells"] == \
        [next(n["attrs"] for n in chain.h0["nodes"] if n["node"] == "ex:HeLa")]
    assert not any(n["node"] == "ex:HeLa" for n in out["nodes"])
    context = [i for i in out["incidences"] if i["edge"] == "f:reg-1" and i["attrs"]["role"] == "context"]
    assert context == [{"edge": "f:reg-1", "node": "ex:HeLa-cells", "direction": "tail",
                        "attrs": {"role": "context", "khg-bid": "b1"}}]
    assert jsonio.canonical(out) != jsonio.canonical(chain.h0)  # an echo export would fail this test


def test_6_an_xgi_membership_removal_raises_and_its_readdition_exports_identically(chain):
    bundle = loaders.load_xgi(copy.deepcopy(chain.h0))
    directed = chain.name == "slice"
    args = ("f:reg-1", "ex:HeLa") + (("in",) if directed else ())
    bundle.graph.remove_node_from_edge(*args)
    with pytest.raises(LoaderError) as err:
        loaders.export_xgi(bundle)
    assert err.value.codes == ("KHG-P005",)
    stale = err.value.info["report"]["stale"]
    assert [(r["edge"], r["node"], r["attrs"]["khg-bid"]) for r in stale] == [("f:reg-1", "ex:HeLa", "b1")]
    assert bundle.report["stale"] == stale
    bundle.graph.add_node_to_edge(*args)
    out = loaders.export_xgi(bundle)
    assert jsonio.canonical(out) == jsonio.canonical(chain.h0)
    assert not any(bundle.report.values())


# ------------------------------------------------------------------------------------------------ 7. hash seeds


def _children() -> list[dict[str, Any]]:
    helper = HERE / "g1_chain.py"
    procs = []
    for seed in ("0", "1", "2", "3", None):
        env = dict(os.environ)
        env.pop("PYTHONHASHSEED", None)
        if seed is not None:
            env["PYTHONHASHSEED"] = seed
        procs.append(subprocess.Popen([sys.executable, str(helper)], env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True))
    out = []
    for p in procs:
        stdout, stderr = p.communicate(timeout=600)
        assert p.returncode == 0, stderr
        out.append(json.loads(stdout))
    return out


def test_7_five_hash_seed_children_agree_with_the_golden_digests():
    golden = json.loads((HERE / "golden-sha256.json").read_text(encoding="utf-8"))
    assert golden["chain"] == "C1 -> HIF -> XGI -> HIF -> HyperNetX -> HIF -> C1"
    digests = _children()
    assert len(digests) == 5
    assert all(d == digests[0] for d in digests)
    assert digests[0] == golden["digests"]
    for name in ("full", "slice"):  # the HIF is the same document at every step
        steps = digests[0][name]
        assert steps["hif"] == steps["after_xgi"] == steps["after_hnx"]


def test_7_the_golden_digests_are_those_of_this_process():
    golden = json.loads((HERE / "golden-sha256.json").read_text(encoding="utf-8"))["digests"]
    for name in ("full", "slice"):
        c = _run_chain(name)
        got = {"hif": _digest(c.h0), "after_xgi": _digest(c.h1), "after_hnx": _digest(c.h2), "c1": _digest(c.back)}
        assert got == golden[name]


def _digest(doc: dict[str, Any]) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(jsonio.canonical(doc).encode("utf-8")).hexdigest()
