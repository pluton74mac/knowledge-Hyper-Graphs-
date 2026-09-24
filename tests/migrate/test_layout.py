"""W10: ``migrate.dumps``, the text layout of the committed migration goldens."""
from __future__ import annotations

import json

from khg_contracts import data, jsonio, migrate


def test_plain_layout_is_indent_1_json():
    doc = {"format": "khg-migration-report/1.0.0", "findings": [{"code": "KHG-F016", "message": "m"}]}
    assert migrate.dumps(doc) == json.dumps(doc, indent=1) + "\n"
    assert migrate.LAYOUT["report"] is None


def test_compact_layout_writes_one_record_per_line():
    doc = {"header": {"kind": "header", "x": [1, 2]}, "records": [{"id": "a", "v": 0.5}, {"id": "b", "v": 1.0}],
           "empty": [], "n": None}
    assert migrate.dumps(doc, compact=["records", "empty"]) == (
        '{\n'
        ' "header": {"kind": "header", "x": [1, 2]},\n'
        ' "records": [\n'
        '  {"id": "a", "v": 0.5},\n'
        '  {"id": "b", "v": 1.0}\n'
        ' ],\n'
        ' "empty": [\n'
        ' ],\n'
        ' "n": null\n'
        '}\n')


def test_the_layout_keeps_non_ascii_text_and_parses_back_to_the_same_document():
    doc = data.load_json("fixture/fixture.c1.json")  # Ødegård, 東京, 𠮷田 and a Kraków id
    text = migrate.dumps(doc, compact=migrate.LAYOUT["container"])
    assert "Ødegård" in text and "\\u" not in text
    assert jsonio.loads(text.encode("utf-8")) == doc
    assert text.count("\n") == len(doc["records"]) + 5


def test_a_listed_key_that_is_not_an_array_is_written_on_one_line():
    assert migrate.dumps({"records": {"a": 1}}, compact=["records"]) == '{\n "records": {"a": 1}\n}\n'


def test_the_layout_of_each_golden():
    assert dict(migrate.LAYOUT) == {"schema": ("entity_types", "roles", "relations"), "container": ("records",),
                                    "hif": ("nodes", "edges", "incidences"), "report": None}
