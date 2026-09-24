"""G1: the schema generators (DESIGN §2.4, §2.5, §6.1, §6.2) on mini raw inputs.

The mini Wikidata raw set (tests/mini/wikidata/) covers: the interval time model, meta qualifiers (P2241, P813),
the built-in end cause (P1534), a required qualifier (min 1), a self-qualifier (``P131:qualifier``), rule 6a (the
relations P580 and P582), an excluded property (P1855, rule 8), a "no value" constraint (P166), a deprecated
constraint statement (P31) and an unknown qualifier id in the counts.
"""
from __future__ import annotations

import json
import shutil

import pytest

from helpers import MINI
from khg_contracts.schema import check_schema
from khg_width.sources import biolink, manifest, wikidata

RAW = MINI / "wikidata" / "raw"
P3A = MINI / "wikidata" / "p3a-qualifier-usage-mini.json"


def rel(doc: dict, rid: str) -> dict:
    return next(r for r in doc["relations"] if r["id"] == rid)


def roles(doc: dict, rid: str) -> dict:
    return {u["role"]: u for u in rel(doc, rid)["roles"]}


def test_declared_r1_rules():
    doc, notes = wikidata.build(RAW, "declared", "wd-roles-r1")
    assert check_schema(doc) == []
    assert doc["id"] == "p6-wikidata-declared-wd-roles-r1" and doc["version"] == "1.0.0"
    assert [r["id"] for r in doc["relations"]] == ["P39", "P131", "P166", "P580", "P582"]  # no P1855, no P31
    # P39: interval model, meta usages, end cause built in, required qualifier min 1, primary
    p39 = roles(doc, "P39")
    assert rel(doc, "P39")["time"] == {"model": "interval", "start": "P580", "end": "P582"}
    assert rel(doc, "P39")["primary"] == {"subject": "subject", "object": "P39"}
    assert (p39["subject"]["slot"], p39["subject"]["direction"], p39["P39"]["direction"]) == ("core", "tail", "head")
    assert p39["P580"]["slot"] == p39["P582"]["slot"] == "time" and p39["P580"]["max"] == 1
    assert p39["P580"]["min"] == 0  # required, but a time bound
    assert p39["P2241"]["slot"] == "meta" and p39["P813"]["slot"] == "meta"
    assert "P1534" not in p39  # khg:end_cause is built in on interval relations
    assert p39["P1365"]["slot"] == "qualifier" and p39["P1365"]["min"] == 1
    # rule 5: the self-qualifier
    p131 = roles(doc, "P131")
    assert p131["P131:qualifier"]["slot"] == "qualifier" and p131["P131"]["slot"] == "core"
    # rule 6a: no time model on P580 and P582; their bounds are qualifier usages
    assert "time" not in rel(doc, "P580") and "time" not in rel(doc, "P582")
    assert roles(doc, "P580")["P580:qualifier"]["slot"] == "qualifier"
    assert roles(doc, "P580")["P582"]["slot"] == "qualifier"
    assert roles(doc, "P582")["P580"]["slot"] == "qualifier"
    # "no value": only the core roles
    assert set(roles(doc, "P166")) == {"subject", "P166"}
    assert notes["self_qualifier_roles"] == 2 and notes["rule_6a_relations"] == 2 and notes["excluded_relations"] == 1


def test_relation_local_control():
    doc, _ = wikidata.build(RAW, "declared", "relation-local")
    assert check_schema(doc) == []
    assert set(roles(doc, "P39")) == {"P39:subject", "P39:value", "P39:P580", "P39:P582", "P39:P2241", "P39:P813",
                                      "P39:P1365"}
    assert rel(doc, "P39")["time"] == {"model": "interval", "start": "P39:P580", "end": "P39:P582"}
    assert "P131:P131" in roles(doc, "P131")
    assert "time" not in rel(doc, "P580")  # 6a kept in the control
    # every role belongs to one relation: the edges are pairwise disjoint
    seen: dict = {}
    for r in doc["relations"]:
        for u in r["roles"]:
            assert seen.setdefault(u["role"], r["id"]) == r["id"]


def test_observed_tables_from_sqid():
    tb, notes = wikidata.tables(wikidata.load(RAW))
    assert tb["observed-all"]["P39"] == ["P580", "P582", "P1365", "P2241"]  # 9999999 is unknown: dropped
    assert notes["observed_unknown_qualifier_ids"] == 1
    # robust: >= 10 uses and >= 0.1 % of main statements (P39: 10,000 -> 10); P2241 has 5 uses
    assert tb["observed-robust"]["P39"] == ["P580", "P582", "P1365"]
    assert tb["observed-robust"]["P31"] == ["P585"] and tb["observed-all"]["P31"] == ["P580", "P585"]
    assert "P1855" not in tb["observed-all"]  # excluded as a relation
    doc, _ = wikidata.build(RAW, "observed-all", "wd-roles-r1")
    assert check_schema(doc) == []
    assert rel(doc, "P31")["time"]["model"] == "interval"  # uses P580: interval model, P582 added


def test_p3a_counts_win_over_sqid_both_scopes():
    dump = wikidata.read_counts(P3A, scope="dump")
    doc, notes = wikidata.build(RAW, "observed-all", "wd-roles-r1", counts=dump)
    assert check_schema(doc) == []
    assert [r["id"] for r in doc["relations"]] == ["P39", "P131"]  # P3a's relations with statements
    assert set(roles(doc, "P39")) == {"subject", "P39", "P580", "P582", "P813", "P1365"}  # not SQID's P2241
    assert "P131:qualifier" in roles(doc, "P131")  # mapped back from P3a's r1 role id
    assert "counts P3a 2026-09-22" in doc["label"]
    assert notes["observed_unknown_qualifier_ids"] == 1  # P2937 is not in the mini property list
    robust, _ = wikidata.build(RAW, "observed-robust", "wd-roles-r1", counts=dump)
    assert set(roles(robust, "P39")) == {"subject", "P39", "P580", "P582", "P813"}  # P1365: 5 uses
    sl = wikidata.read_counts(P3A, scope="slice")
    doc2, _ = wikidata.build(RAW, "observed-robust", "wd-roles-r1", counts=sl)
    assert doc2["id"] == "p6-wikidata-observed-robust-slice-wd-roles-r1"
    assert set(roles(doc2, "P39")) == {"subject", "P39", "P580", "P582"}  # P582: 1 use in the slice
    with pytest.raises(ValueError, match="declared table does not depend"):
        wikidata.build(RAW, "declared", "wd-roles-r1", counts=dump)


def test_p3a_wrong_naming_refused(tmp_path):
    data = json.loads(P3A.read_text())
    data["naming"] = "wd-roles r0"
    with pytest.raises(ValueError, match="refused"):
        wikidata.read_counts(data)
    data["naming"], data["format"] = "wd-roles r1", "p3a-qualifier-usage/2"
    with pytest.raises(ValueError, match="not a p3a-qualifier-usage/1"):
        wikidata.read_counts(data)


def test_p3a_crosscheck():
    cc = wikidata.crosscheck_p3a(wikidata.read_counts(P3A), wikidata.load(RAW))
    assert {"relation": "P39", "role": "P813", "field": "slot", "p3a": "qualifier", "p6": "meta"} in cc["mismatches"]
    oos = next(m for m in cc["mismatches"] if m["field"] == "out_of_scope")
    assert oos["only_p3a"] == ["P2302"] and oos["only_p6"] == []


def test_manifest_verify(tmp_path):
    got = manifest.verify(MINI / "wikidata")
    assert set(got) == {f"raw/{p.name}" for p in RAW.iterdir()}
    copy = tmp_path / "wikidata"
    shutil.copytree(MINI / "wikidata", copy)
    (copy / "raw" / "properties.srj.json").write_text("{}")
    with pytest.raises(manifest.ManifestError, match="sha256"):
        manifest.verify(copy)
    (copy / "raw" / "properties.srj.json").unlink()
    with pytest.raises(manifest.ManifestError, match="missing"):
        manifest.verify(copy, ["raw/properties.srj.json"])
    with pytest.raises(manifest.ManifestError, match="not listed"):
        manifest.verify(copy, ["raw/nope.json"])


def test_rules_file():
    r = wikidata.rules()
    assert r["naming"] == "wd-roles r1" and len(r["meta"]) == 24
    assert r["meta_rank_reasons"] == ["P2241", "P7452"] and r["no_time_model_relations"] == ["P580", "P582"]


def test_biolink_from_rows():
    rows = json.loads((MINI / "biolink" / "rows.json").read_text())
    doc = biolink.schema_from_rows(rows, "formal", "global")
    assert check_schema(doc) == []
    assert doc["id"] == "p6-biolink-formal-global"
    assert [r["id"] for r in doc["relations"]] == ["ChemicalAffectsGeneAssociation", "GeneToDiseaseAssociation",
                                                   "GeneToExpressionSiteAssociation"]  # the abstract one is out
    assert set(roles(doc, "GeneToDiseaseAssociation")) == {"subject", "object", "species_context_qualifier",
                                                           "stage_qualifier"}
    dom = biolink.schema_from_rows(rows, "formal-domain", "global")
    assert "has_count" in roles(dom, "GeneToDiseaseAssociation")
    loc = biolink.schema_from_rows(rows, "formal", "relation-local")
    assert check_schema(loc) == []
    assert "GeneToDiseaseAssociation:stage_qualifier" in roles(loc, "GeneToDiseaseAssociation")


def test_biolink_extract_with_linkml():
    pytest.importorskip("linkml_runtime")
    rows = biolink.extract(MINI / "biolink" / "mini-biolink.yaml")
    by = {r["class"]: r for r in rows}
    assert set(by) == {"association", "gene to disease association", "gene to phenotype association"}
    assert by["association"]["abstract"] is True
    assert by["gene to disease association"]["qualifiers_formal"] == ["species context qualifier", "stage qualifier"]
    assert by["gene to disease association"]["domain_slots"] == ["has count"]
    assert "publications" in by["gene to disease association"]["meta_slots"]
    doc = biolink.build(MINI / "biolink" / "mini-biolink.yaml", "formal-domain", "global")
    assert check_schema(doc) == [] and len(doc["relations"]) == 2
