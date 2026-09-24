"""W10: the knowledge base's ``schemas/sample.hif.json`` migrates to the committed goldens (DESIGN §11.3).

- the four goldens: the schema, the container and the report that ``v0_sample_to_v1`` returns, and the HIF export of
  the container, as documents and byte for byte in the goldens' layout;
- the report codes in order (F017, F006 and F015 per edge, then F016), all registered F codes;
- each pinned rule of the §11.3 table on the sample, and the migrated documents under the validator;
- the G1 chain on the migrated sample: C1 -> HIF -> XGI -> HIF -> HyperNetX -> HIF -> C1 (skipped without xgi and
  HyperNetX).
"""
from __future__ import annotations

import copy
import hashlib
import importlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import data, hif, jsonio, loaders, migrate, record
from khg_contracts.errors import LoaderError, ValidationError
from khg_contracts.schema import Schema
from khg_contracts.store import compare_containers
from khg_contracts.validate import ENGINES, layers, registry, validate, validate_container, validate_hif

REPORT_CODES = ["KHG-F017", "KHG-F006", "KHG-F015", "KHG-F006", "KHG-F015", "KHG-F006", "KHG-F015", "KHG-F016"]
REPORT_EDGES = ["f1", "f1", "f1", "f2", "f2", "f3", "f3", None]
SCHEMA_SHA256 = "sha256:69f63208d33e09c742a90b1bf4ede076cfe158a5939f7f4f4d47e40c21da7fc5"
WEIGHTS = {"f1": 0.95, "f2": 0.8, "f3": 1.0}
ARITIES = {"f1": 4, "f2": 3, "f3": 2}
#: The hash seeds of G1 assertion 7 (§1.2): PYTHONHASHSEED 0-3 and unset (None).
SEEDS = ("0", "1", "2", "3", None)


def _hyperedges(container: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in container["records"] if r["kind"] == "hyperedge"}


# ------------------------------------------------------------------------------------------------ the four goldens


def test_the_migration_returns_the_three_goldens(migrated, goldens):
    schema, container, report = migrated  # a (schema, container, report) tuple
    assert schema == goldens["schema"]
    assert container == goldens["container"]
    assert report == goldens["report"]


def test_the_hif_export_of_the_migrated_container_is_the_fourth_golden(outputs, goldens):
    assert outputs["hif"] == goldens["hif"]
    assert outputs["hif"]["metadata"]["khg-schema"] == "kb-sample/1.0.0"
    assert outputs["hif"]["network-type"] == "directed"


@pytest.mark.parametrize("name", ["schema", "container", "hif", "report"])
def test_each_golden_is_reproduced_byte_for_byte(name, outputs, golden_files):
    text = migrate.dumps(outputs[name], compact=migrate.LAYOUT[name])
    assert text.encode("utf-8") == data.read_bytes(golden_files[name])
    assert jsonio.canonical(jsonio.loads(text)) == jsonio.canonical(data.load_json(golden_files[name]))


def test_the_goldens_are_mirrored_in_design_examples(examples_dir, golden_files):
    for rel in golden_files.values():
        assert (examples_dir / Path(rel).name).read_bytes() == data.read_bytes(rel)


# ------------------------------------------------------------------------------------------------ the report


def test_the_report_codes_in_order(migrated):
    report = migrated.report
    assert report["format"] == migrate.REPORT_FORMAT == "khg-migration-report/1.0.0"
    assert report["from"] == migrate.V0_SAMPLE == "v0-sample"
    assert [f["code"] for f in report["findings"]] == REPORT_CODES
    assert [f.get("edge") for f in report["findings"]] == REPORT_EDGES


def test_the_report_messages_name_what_happened(migrated):
    messages = {(f["code"], f.get("edge")): f["message"] for f in migrated.report["findings"]}
    assert messages[("KHG-F017", "f1")] == "valid-from became a start_time binding"
    assert {messages[("KHG-F006", e)] for e in WEIGHTS} == {"weight kept as extensions hif:weight"}
    for edge, n in ARITIES.items():
        assert messages[("KHG-F015", edge)] == f"stored arity {n} checked and dropped"
    assert messages[("KHG-F016", None)] == "metadata schema and conventions replaced by the declaration block"


def test_every_report_code_is_a_registered_active_migration_code(migrated):
    reg = registry()
    for f in migrated.report["findings"]:
        assert f["code"] in reg and reg[f["code"]].active and reg[f["code"]].layer == "F"
        assert set(f) <= {"code", "edge", "message"}
    # v1 ships F006 and F015-F017 (§8.1); the sample uses all four
    assert {f["code"] for f in migrated.report["findings"]} == {"KHG-F006", "KHG-F015", "KHG-F016", "KHG-F017"}


# ------------------------------------------------------------------------------------------------ the pinned rules


def test_the_generated_schema_follows_the_pinned_rules(migrated):
    s = migrated.schema
    assert (s["kind"], s["format"], s["id"], s["version"]) == \
        ("relation-schema", "khg-relation-schema/1.0.0", "kb-sample", "1.0.0")
    assert [t["id"] for t in s["entity_types"]] == ["AdverseEffect", "Disease", "Document", "Dosage", "Drug",
                                                    "Organisation", "Population"]
    assert [r["id"] for r in s["roles"]] == sorted(r["id"] for r in s["roles"])
    assert [r["id"] for r in s["relations"]] == ["co-administration-causes", "publishes", "treats"]
    usages = {(r["id"], u["role"]): u for r in s["relations"] for u in r["roles"]}
    # agent repeats in f2: max null; every role occurs in every edge of its relation: min 1
    assert usages[("co-administration-causes", "agent")] == {
        "role": "agent", "slot": "core", "fillers": [{"entity": ["Drug"]}], "min": 1, "max": None,
        "direction": "tail"}
    assert usages[("treats", "condition")]["direction"] == "head"
    assert {u["slot"] for (rel, role), u in usages.items() if role not in ("start_time", "end_time")} == {"core"}
    for rel in s["relations"]:  # core usages sorted by role id, then the time usages
        core = [u["role"] for u in rel["roles"] if u["slot"] == "core"]
        assert core == sorted(core)


def test_valid_from_gives_an_interval_time_model_and_a_start_time_binding(migrated, schema):
    treats = next(r for r in migrated.schema["relations"] if r["id"] == "treats")
    assert treats["time"] == {"model": "interval", "start": "start_time", "end": "end_time"}
    assert treats["roles"][-2:] == [
        {"role": t, "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"}
        for t in ("start_time", "end_time")]
    assert all("time" not in r for r in migrated.schema["relations"] if r["id"] != "treats")
    f1 = _hyperedges(migrated.container)["f1"]
    start = [b for b in f1["bindings"] if b["role"] == "start_time"]
    assert start == [{"bid": "b4", "role": "start_time", "value": {"literal": {
        "datatype": "time", "time": "+2024-01-01T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}]
    vt = record.valid_time(f1, schema)  # holds since the day of valid-from; no end, so it still holds (§2.6)
    assert (vt["kind"], vt["possible"], vt["definite"]) == \
        ("since", ["+2024-01-01T00:00:00Z", None], ["+2024-01-02T00:00:00Z", None])


def test_one_binding_per_incidence_with_bids_in_canonical_binding_order(migrated, v0):
    edges = _hyperedges(migrated.container)
    for e in v0["edges"]:
        incidences = [(i["attrs"]["role"], i["node"]) for i in v0["incidences"] if i["edge"] == e["edge"]]
        bindings = edges[e["edge"]]["bindings"]
        entity_bindings = [(b["role"], b["value"]["entity"]) for b in bindings if "entity" in b["value"]]
        assert sorted(entity_bindings) == sorted(incidences)
        assert bindings == sorted(bindings, key=record.binding_sort_key)
        assert [b["bid"] for b in bindings] == [f"b{n}" for n in range(1, len(bindings) + 1)]
        assert all("direction" not in b for b in bindings)  # every usage has the observed direction
    assert [b["role"] for b in edges["f1"]["bindings"]] == ["condition", "dosage", "population", "start_time",
                                                            "treatment"]


def test_the_source_becomes_imported_evidence(migrated):
    for rid, r in _hyperedges(migrated.container).items():
        assert r["evidence"] == [{"id": "e1", "type": "imported", "mode": "automatic",
                                  "source": {"doc_id": "doc:guideline-2024"},
                                  "supports": [b["bid"] for b in r["bindings"]]}], rid
        assert (r["status"], r["rank"], r["visibility"]) == ("asserted", "normal", "visible")


def test_the_stored_arity_is_checked_and_dropped(migrated, schema):
    for rid, r in _hyperedges(migrated.container).items():
        assert record.arity(r, schema)["arity"] == ARITIES[rid]
        assert "arity" not in r and "derived" not in r
    assert record.arity(_hyperedges(migrated.container)["f1"], schema)["statement_arity"] == 5


def test_the_weight_is_an_extension_never_confidence(migrated):
    for rid, r in _hyperedges(migrated.container).items():
        assert r["extensions"] == {"hif:weight": WEIGHTS[rid]}
        assert type(r["extensions"]["hif:weight"]) is float
        assert "confidence" not in r and all("confidence" not in e for e in r["evidence"])


def test_the_header_and_the_metadata(migrated, schema, v0):
    header = migrated.container["header"]
    assert header == {
        "kind": "header", "format": "khg-record/1.0.0", "document_id": "kb-sample",
        "schema": {"id": "kb-sample", "version": "1.0.0", "sha256": SCHEMA_SHA256}, "content": "snapshot",
        "complete": True,
        "extensions": {"hif:metadata": {k: v0["metadata"][k] for k in ("title", "description", "created",
                                                                        "kb-section")}}}
    assert schema.sha256 == SCHEMA_SHA256 == jsonio.digest("khg-schema/1", migrated.schema)
    assert list(header["extensions"]["hif:metadata"]) == ["title", "description", "created", "kb-section"]


def test_the_entities_keep_type_and_label(migrated, v0):
    entities = {r["id"]: r for r in migrated.container["records"] if r["kind"] == "entity"}
    assert list(entities) == sorted(n["node"] for n in v0["nodes"])
    for n in v0["nodes"]:
        assert entities[n["node"]] == {"kind": "entity", "id": n["node"], "types": [n["attrs"]["type"]],
                                       "label": n["attrs"]["label"]}


# ------------------------------------------------------------------------------------------------ validity


def test_the_migrated_documents_validate_without_a_finding(migrated, schema, outputs):
    assert validate(migrated.schema, kind="schema") == {"ok": True, "findings": []}
    for engine in ENGINES:
        assert validate_container(migrated.container, schema=schema, engine=engine) == {"ok": True, "findings": []}
        assert validate_hif(outputs["hif"], schema=schema, engine=engine) == {"ok": True, "findings": []}
        for letter in ("h", "r", "p"):
            assert layers.module(letter).findings(outputs["hif"], engine=engine) == []


def test_the_container_round_trips_through_hif(migrated, schema, outputs):
    back = hif.from_hif(outputs["hif"], schema)
    assert back == migrated.container
    assert compare_containers(migrated.container, back, ignore=()) == []


@pytest.mark.parametrize("suffix", [".khg.json", ".khg.jsonl"])
def test_the_container_is_written_and_read_back_as_the_golden(migrated, goldens, golden_files, tmp_path, suffix):
    """``record.write_container`` (V and C checks, canonical layout) keeps the golden's content; only the text
    layout of the committed golden differs."""
    path = tmp_path / f"sample{suffix}"
    record.write_container(migrated.container, path)
    assert record.read_container(path) == goldens["container"]
    written = path.read_bytes()
    assert written != data.read_bytes(golden_files["container"])
    assert written.count(b"\n") == (1 if suffix == ".khg.jsonl" else 5) + len(goldens["container"]["records"])


# ------------------------------------------------------------------------------------------------ the call


def test_the_api_names(migrated):
    assert callable(migrate.v0_sample_to_v1) and migrate.MIGRATIONS == {"v0-sample": migrate.v0_sample_to_v1}
    assert isinstance(migrated, tuple) and migrated._fields == ("schema", "container", "report")
    module = sys.modules["khg_contracts.migrate.v0_sample_to_v1"]  # §10.1: migrate/v0_sample_to_v1.py
    assert module.v0_sample_to_v1 is migrate.v0_sample_to_v1
    assert importlib.import_module("khg_contracts.migrate.v0_sample_to_v1") is module
    import khg_contracts.migrate.v0_sample_to_v1 as by_name  # the package attribute: the function, not the module

    assert by_name is migrate.v0_sample_to_v1
    assert issubclass(ValidationError, ValueError)


def test_every_input_form_gives_the_same_result(migrated, v0_path):
    for source in (v0_path, str(v0_path), v0_path.read_bytes(), jsonio.load(v0_path)):
        assert migrate.v0_sample_to_v1(source) == migrated


def test_the_input_is_not_modified_and_shares_nothing_with_the_output(v0):
    v0["metadata"]["provenance"] = {"by": ["kb"]}
    before = copy.deepcopy(v0)
    m = migrate.v0_sample_to_v1(v0)
    assert v0 == before
    snapshot = copy.deepcopy(m)
    v0["metadata"]["provenance"]["by"].append("changed")
    v0["nodes"][0]["attrs"]["label"] = "changed"
    v0["edges"][0]["attrs"]["relation"] = "changed"
    assert m == snapshot
    assert m.container["header"]["extensions"]["hif:metadata"]["provenance"] == {"by": ["kb"]}


def test_the_result_does_not_depend_on_the_order_of_nodes_and_incidences(migrated, v0):
    v0["nodes"].reverse()
    v0["incidences"].reverse()
    assert migrate.v0_sample_to_v1(v0) == migrated


def _digest(m: migrate.Migration) -> str:
    return "sha256:" + hashlib.sha256(jsonio.canonical(list(m)).encode("utf-8")).hexdigest()


#: The first lines of every child process: sockets are blocked before the package is imported, as in the G1 child.
_NO_NETWORK = """
import socket
def refuse(*args, **kwargs):
    raise OSError("network access is blocked in the migration test child")
for name in ("connect", "connect_ex", "sendto", "sendmsg"):
    setattr(socket.socket, name, refuse)
for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "create_connection"):
    setattr(socket, name, refuse)
"""


def _children(code: str, v0_path: Path, seeds: tuple[str | None, ...]) -> list[str]:
    """The stdout of one child per hash seed (None: unset), run in parallel on the v0 sample."""
    procs = []
    for seed in seeds:
        env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
        if seed is not None:
            env["PYTHONHASHSEED"] = seed
        procs.append(subprocess.Popen([sys.executable, "-c", _NO_NETWORK + code, str(v0_path)], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    out = []
    for p in procs:
        stdout, stderr = p.communicate(timeout=600)
        assert p.returncode == 0, stderr
        out.append(stdout.strip())
    return out


def test_the_result_does_not_depend_on_the_hash_seed(migrated, v0_path):
    code = ("import hashlib, sys\n"
            "from khg_contracts import jsonio, migrate\n"
            "m = migrate.v0_sample_to_v1(sys.argv[1])\n"
            "print('sha256:' + hashlib.sha256(jsonio.canonical(list(m)).encode('utf-8')).hexdigest())\n")
    assert _children(code, v0_path, SEEDS) == [_digest(migrated)] * len(SEEDS)


# ------------------------------------------------------------------------------------------------ the KB's files


def test_the_input_copy_is_the_knowledge_base_sample(repo_root, v0_path):
    original = repo_root / "schemas" / "sample.hif.json"
    if not original.is_file():
        pytest.skip("schemas/sample.hif.json is not available (not a repository checkout)")
    assert v0_path.read_bytes() == original.read_bytes()


@pytest.mark.parametrize("name", ["schema", "container", "hif", "report"])
def test_goldens_committed_next_to_the_sample_equal_the_packaged_ones(name, repo_root, golden_files):
    """§11.3: the goldens sit next to ``schemas/sample.hif.json`` once they are committed there."""
    beside = repo_root / "schemas" / Path(golden_files[name]).name
    if not beside.is_file():
        pytest.skip(f"schemas/{beside.name} is not committed")
    assert beside.read_bytes() == data.read_bytes(golden_files[name])


# ------------------------------------------------------------------------------------------------ the G1 chain


@dataclass
class Chain:
    """C1 -> HIF -> XGI -> HIF -> HyperNetX -> HIF -> C1 on the migrated sample, with every intermediate object."""

    h0: dict[str, Any]
    bx: loaders.Bundle
    h1: dict[str, Any]
    bh: loaders.Bundle
    h2: dict[str, Any]
    back: dict[str, Any]


@pytest.fixture(scope="module")
def chain(migrated: migrate.Migration, schema: Schema) -> Chain:
    pytest.importorskip("xgi")
    pytest.importorskip("hypernetx")
    h0 = hif.to_hif(copy.deepcopy(migrated.container), schema)
    bx = loaders.load_xgi(copy.deepcopy(h0))
    h1 = loaders.export_xgi(bx)
    bh = loaders.load_hnx(copy.deepcopy(h1))
    h2 = loaders.export_hnx(bh)
    return Chain(h0, bx, h1, bh, h2, hif.from_hif(h2, schema))


@pytest.mark.libs
def test_g1_the_first_hif_is_the_golden_and_valid_under_both_engines(chain, goldens, schema):
    assert chain.h0 == goldens["hif"]
    for engine in ENGINES:
        assert validate_hif(chain.h0, schema=schema, engine=engine) == {"ok": True, "findings": []}


@pytest.mark.libs
def test_g1_every_intermediate_hif_equals_the_first(chain):
    first = jsonio.canonical(chain.h0)
    assert jsonio.canonical(chain.h1) == first and jsonio.canonical(chain.h2) == first
    assert chain.h1 == chain.h0 and chain.h2 == chain.h0  # records, order and metadata
    for h in (chain.h1, chain.h2):  # the weights keep their JSON number type
        assert {e["edge"]: e["weight"] for e in h["edges"]} == WEIGHTS
        assert {type(e["weight"]) for e in h["edges"]} == {float}


@pytest.mark.libs
def test_g1_the_final_container_equals_the_migrated_one(chain, migrated):
    assert chain.back == migrated.container
    assert compare_containers(migrated.container, chain.back, ignore=()) == []
    assert compare_containers(migrated.container, chain.back) == []


@pytest.mark.libs
def test_g1_both_export_reports_are_empty(chain):
    for bundle in (chain.bx, chain.bh):
        assert bundle.report == loaders.report.new_report()
        assert not any(bundle.report.values())


@pytest.mark.libs
def test_g1_the_library_objects_hold_the_memberships_and_the_roles(chain):
    import xgi

    assert type(chain.bx.graph) is xgi.DiHypergraph  # every incidence has a direction
    for edge in ("f1", "f2", "f3"):
        pairs = [(i["node"], i["direction"]) for i in chain.h0["incidences"] if i["edge"] == edge]
        tail, head = chain.bx.graph.edges.dimembers(edge)
        assert tail == {n for n, d in pairs if d == "tail"} and head == {n for n, d in pairs if d == "head"}
    for i in chain.h0["incidences"]:
        role = i["attrs"]["role"]
        assert chain.bx.roles(i["edge"], i["node"]) == [role]
        assert chain.bh.roles(i["edge"], i["node"]) == [role]
        cell = chain.bh.graph.get_cell_properties(i["edge"], i["node"])
        assert (cell["role"], cell["khg-bid"], cell["direction"]) == (role, i["attrs"]["khg-bid"], i["direction"])
        assert cell.get(loaders.EXTRA, []) == []  # the sample repeats no (edge, node) pair
    literal = next(i["node"] for i in chain.h0["incidences"] if i["attrs"]["role"] == "start_time")
    assert literal.startswith("_:lit:") and chain.bx.roles("f1", literal) == ["start_time"]


@pytest.mark.libs
def test_g1_the_convert_helpers_round_trip_the_migrated_container(migrated, schema, chain):
    assert loaders.xgi_to_khg(loaders.khg_to_xgi(migrated.container, schema), schema) == migrated.container
    assert loaders.hnx_to_khg(loaders.khg_to_hnx(migrated.container, schema), schema) == migrated.container


@pytest.mark.libs
def test_g1_a_hypernetx_rename_is_reflected(chain):
    bundle = loaders.load_hnx(copy.deepcopy(chain.h0))
    bundle.graph.rename(nodes={"org:ADA": "org:ADA-2024"})
    out = loaders.export_hnx(bundle)
    assert bundle.report["moved"] == [{"edge": "f3", "bid": "b2", "from": "org:ADA", "to": "org:ADA-2024"}]
    assert bundle.report["dropped_nodes"] == [] and bundle.report["stale"] == []  # the sample has no isolated node
    assert [i for i in out["incidences"] if i["edge"] == "f3" and i["attrs"]["role"] == "publisher"] == [
        {"edge": "f3", "node": "org:ADA-2024", "direction": "tail", "attrs": {"role": "publisher", "khg-bid": "b2"}}]
    assert [n["attrs"]["label"] for n in out["nodes"] if n["node"] == "org:ADA-2024"] == \
        ["American Diabetes Association"]


@pytest.mark.libs
def test_g1_an_xgi_membership_removal_raises_and_its_readdition_exports_identically(chain):
    bundle = loaders.load_xgi(copy.deepcopy(chain.h0))
    bundle.graph.remove_node_from_edge("f3", "org:ADA", "in")  # the publisher is in the tail ("in")
    with pytest.raises(LoaderError) as err:
        loaders.export_xgi(bundle)
    assert err.value.codes == ("KHG-P005",)
    stale = err.value.info["report"]["stale"]
    assert [(r["edge"], r["node"], r["attrs"]["khg-bid"]) for r in stale] == [("f3", "org:ADA", "b2")]
    bundle.graph.add_node_to_edge("f3", "org:ADA", "in")
    assert jsonio.canonical(loaders.export_xgi(bundle)) == jsonio.canonical(chain.h0)
    assert not any(bundle.report.values())


_CHAIN_CHILD = """
import hashlib, json, sys, warnings
warnings.filterwarnings("ignore")
from khg_contracts import hif, jsonio, loaders, migrate
from khg_contracts.schema import load_schema
m = migrate.v0_sample_to_v1(sys.argv[1])
s = load_schema(m.schema)
h0 = hif.to_hif(m.container, s)
h1 = loaders.export_xgi(loaders.load_xgi(h0))
h2 = loaders.export_hnx(loaders.load_hnx(h1))
d = lambda x: "sha256:" + hashlib.sha256(jsonio.canonical(x).encode("utf-8")).hexdigest()
print(json.dumps([d(list(m)), d(h0), d(h1), d(h2), d(hif.from_hif(h2, s))]))
"""


@pytest.mark.libs
def test_g1_hash_seed_children_agree_with_this_process(chain, migrated, goldens, v0_path):
    """G1 assertion 7 on the migrated sample: five children, each printing the digest of every intermediate
    document (the migration's three results, the three HIFs and the final container), agree with this process."""
    def digest(doc: Any) -> str:
        return "sha256:" + hashlib.sha256(jsonio.canonical(doc).encode("utf-8")).hexdigest()

    want = [_digest(migrated), digest(chain.h0), digest(chain.h1), digest(chain.h2), digest(chain.back)]
    assert want[1] == digest(goldens["hif"])  # the chain starts from the golden HIF
    outputs = _children(_CHAIN_CHILD, v0_path, SEEDS)
    assert [json.loads(stdout) for stdout in outputs] == [want] * len(SEEDS)
