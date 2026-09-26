"""W3: the public surface of khg_contracts.record (DESIGN §10.2) and the record calls of the §1.3 sequences."""
from __future__ import annotations

import json
import subprocess
import sys

import khg_contracts
from khg_contracts import data, record
from khg_contracts.schema import load_schema

S = load_schema(data.path("fixture/fixture.relation-schema.json"))
C1 = data.load_json("fixture/fixture.c1.json")
FACTS = {r["id"]: r for r in C1["records"] if r["kind"] == "hyperedge"}

SECTION_10_2 = ["read_container", "iter_jsonl", "write_container", "normalize", "derive", "content_key", "core_key",
                "key_digest", "arity", "valid_time", "value_identity", "window", "container_sha256",
                "resolve_redirects", "supported_values", "render_text"]
PROJECTIONS = ["position_map", "positional", "hyper_relational", "role_value_set", "rdf_relation_instance",
               "from_rdf_relation_instance", "incidence_rows", "from_incidence_rows"]


def test_the_section_10_2_names_exist():
    assert all(callable(getattr(record, n)) for n in SECTION_10_2)
    assert all(callable(getattr(record.project, n)) for n in PROJECTIONS)
    assert all(hasattr(record, n) for n in record.__all__)
    assert khg_contracts.record is record
    assert record.FORMAT == "khg-record/1.0.0" and record.RENDER_FORMAT == "khg-render/1"
    # FORMAT is the stamp of a container without 1.1 features; the contract is 1.1.0 (ruling 22)
    assert record.FORMAT_1_1.split("/")[1] == khg_contracts.CONTRACTS["khg-record"]
    assert record.RENDER_FORMAT.split("/")[1] == khg_contracts.CONTRACTS["khg-render"]


def test_the_record_calls_of_the_consumer_sequences(tmp_path):
    # P3a: normalise, write a slice, dedup, leak check, arity bins
    records = [record.normalize(f, S) for f in FACTS.values() if f["status"] == "asserted"
               and S.kind(f["relation"]) == "fact"]
    entities = [r for r in C1["records"] if r["kind"] == "entity"]
    record.write_container({"header": C1["header"], "records": entities + records}, tmp_path / "slice.khg.jsonl",
                           format="jsonl")
    assert len(record.read_container(tmp_path / "slice.khg.jsonl")["records"]) == 22 + 14
    dedup = {record.content_key(r, S) for r in records}
    assert len(dedup) == 14
    train, test = records[:7], records[7:]
    assert not {record.core_key(r, S) for r in test} & {record.core_key(r, S) for r in train}
    bins = [record.arity(r, S)["arity"] for r in records]
    assert sorted(bins) == [1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4, 9]
    # P3b: a literal-free positional projection
    rows = [record.project.positional(f, S, literals="drop", widths={"agent": 4})
            for f in records if f["relation"] == "co_administration_causes"]
    assert rows == [("co_administration_causes", "ex:insulin", "ex:metformin", "khg:none", "khg:none",
                     "ex:hypoglycaemia")]
    # P7 and P10: prompts from rendered facts
    labels = {e["id"]: e["label"] for e in entities}
    prompt = [record.render_text(f, labels, schema=S) for f in records if f["relation"] == "born_in"]
    assert prompt == ["born_in(person: an anonymous scribe; birthplace: some value)",
                      "born_in(person: Maria Skłodowska; birthplace: Warszawa)"]


def test_importing_record_loads_no_validation_engine_and_no_heavy_library():
    code = ("import json, sys\n"
            "import khg_contracts.record\n"
            "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in "
            "('jsonschema', 'fastjsonschema', 'xgi', 'hypernetx', 'pandas', 'numpy', 'scipy'))))\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == []
