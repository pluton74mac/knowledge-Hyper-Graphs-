"""Review fix b-validate-10: S021 reads a selector against the text that the evidence's ``doc_sha256`` hashes
(DESIGN §2.8: "code points, half-open, over the NFC text that doc_sha256 hashes").

``doc_texts`` maps a ``doc_id`` or a ``doc_sha256`` to a text. For evidence with a ``doc_sha256``, layer S reads the
text stored under that digest, else the ``doc_id`` text when it hashes to that digest; a text of another revision is
not the evidence's text, so the span is not judged (as when no text is given). Evidence without a ``doc_sha256``
(layer C's C007 when it has selectors) is read against its ``doc_id`` text.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from khg_contracts import data
from khg_contracts.record.evidence import span_selectors, text_sha256
from khg_contracts.schema import load_schema
from khg_contracts.validate import validate
from khg_contracts.validate.layers.s import record_findings

ENGINES = ("jsonschema", "fastjsonschema")
SCHEMA = load_schema(data.load_json("fixture/fixture.relation-schema.json"))
FIXTURE = data.load_json("fixture/fixture.c1.json")
TEXTS = data.load_json("fixture/fixture.doc-texts.json")
REV1 = TEXTS["texts"]["doc:louis-bio"]["text"]
REV2 = "Revised. " + REV1
KING = next(i for i, r in enumerate(FIXTURE["records"]) if r["id"] == "f:king-14")


def _errors(result: Any) -> list[tuple[str, str]]:
    return [(f["code"], f["path"]) for f in result["findings"] if f["severity"] == "error"]


def _two_revisions() -> dict[str, Any]:
    """f:king-14 with e2 over revision 1 of doc:louis-bio (the fixture's) and e3 over revision 2, spans correct."""
    doc = copy.deepcopy(FIXTURE)
    king = doc["records"][KING]
    e2 = king["evidence"][1]
    assert e2["source"]["doc_sha256"] == text_sha256(REV1)
    e3 = copy.deepcopy(e2)
    e3["id"] = "e3"
    e3.pop("event_hash")
    e3["source"]["doc_sha256"] = text_sha256(REV2)
    e3["selectors"] = span_selectors(REV2, e2["selectors"][0]["exact"])
    assert e3["selectors"][1]["start"] == 9
    king["evidence"].append(e3)
    return doc


@pytest.mark.parametrize("engine", ENGINES)
def test_a_newer_revision_under_the_same_doc_id_is_not_the_evidences_text(engine):
    assert validate(FIXTURE, schema=SCHEMA, doc_texts=TEXTS, engine=engine)["ok"]
    assert validate(FIXTURE, schema=SCHEMA, doc_texts={"doc:louis-bio": REV2}, engine=engine)["ok"]


@pytest.mark.parametrize("engine", ENGINES)
def test_two_revisions_of_one_document_each_read_against_its_own_text(engine):
    doc = _two_revisions()
    by_digest = {text_sha256(REV1): REV1, text_sha256(REV2): REV2}
    for texts in (None, {"doc:louis-bio": REV1}, {"doc:louis-bio": REV2}, by_digest,
                  {"doc:louis-bio": REV1, text_sha256(REV2): REV2}):
        assert validate(doc, schema=SCHEMA, doc_texts=texts, engine=engine)["ok"], texts


@pytest.mark.parametrize("engine", ENGINES)
def test_a_shifted_selector_over_the_matching_revision_is_still_s021(engine):
    doc = _two_revisions()
    e3 = doc["records"][KING]["evidence"][2]
    e3["selectors"][1]["start"], e3["selectors"][1]["end"] = 8, 49  # one code point early
    path = f"/records/{KING}/evidence/2"
    for texts in ({text_sha256(REV2): REV2}, {"doc:louis-bio": REV2}, {"doc:louis-bio": REV1,
                                                                       text_sha256(REV2): REV2}):
        assert _errors(validate(doc, schema=SCHEMA, doc_texts=texts, engine=engine)) == [("KHG-S021", path)], texts
    assert validate(doc, schema=SCHEMA, doc_texts={"doc:louis-bio": REV1}, engine=engine)["ok"]  # no rev-2 text


def test_a_text_keyed_by_a_digest_it_does_not_have_is_not_used():
    king = copy.deepcopy(FIXTURE["records"][KING])
    king["evidence"][1]["selectors"][1]["start"] = 1  # MC111
    assert [f["code"] for f in record_findings(king, SCHEMA, doc_texts={"doc:louis-bio": REV1})] == ["KHG-S021"]
    assert record_findings(king, SCHEMA, doc_texts={text_sha256(REV1): REV2}) == []  # a wrong mapping
    assert [f["code"] for f in record_findings(king, SCHEMA, doc_texts={text_sha256(REV1): REV1})] == ["KHG-S021"]


def test_evidence_without_a_digest_is_read_against_its_doc_id_text():
    king = copy.deepcopy(FIXTURE["records"][KING])
    e2 = king["evidence"][1]
    del e2["source"]["doc_sha256"]  # layer C's C007; S still reads the doc_id text
    e2["selectors"][1]["start"] = 1
    assert [f["code"] for f in record_findings(king, SCHEMA, doc_texts={"doc:louis-bio": REV2})] == ["KHG-S021"]


def test_a_khg_doc_texts_document_and_its_path_still_feed_the_check():
    doc = copy.deepcopy(FIXTURE)
    doc["records"][KING]["evidence"][1]["selectors"][1]["start"] = 1
    for texts in (TEXTS, data.path("fixture/fixture.doc-texts.json")):
        assert _errors(validate(doc, schema=SCHEMA, doc_texts=texts)) == [("KHG-S021", f"/records/{KING}/evidence/1")]
