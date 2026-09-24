"""Development tool: generates the packaged queue schema ``khg-queue-1.0.0.schema.json`` (DESIGN §7, §8.1).

``python -m khg_contracts.queue.codegen OUTDIR`` writes it. It starts from [DB]'s ``khg-queue-1.0.0.schema.json``,
renamed to the lines of §7 (``queue-header``, ``queue-item``, ``log-entry``; ``qid``, ``lid``, ``parent``,
``target``), and follows the conventions of ``schema/codegen.py``: every constraint carries an ``x-khg-code``,
if/then dispatch replaces ``oneOf`` and ``anyOf``, and every ``$ref`` is absolute. Its codes:

- Q003 an unknown line kind, item kind or action; Q001 the extraction fields (``submitted_by``, ``run``, ``doc``)
  and the payload's evidence; Q002 the payload's ``status`` and ``id``; Q004 the fields of a lint entry; Q005 a
  state that is not a queue state; Q010 the item ``keys``; Q008 every other structural violation;
- an item's ``entities`` are C1 entity records (``$ref`` into ``khg-record``, so their findings carry C codes).

The payload itself is checked by layer C against ``khg-record`` ``#/definitions/hyperedge``, and the rules that need
the whole file or the relation-type schema (the fold, ids scoped by the queue, keys, entity resolution, the base and
replay) are Python (``queue.fold``, ``queue.checks``, ``queue.replay``). Nothing here runs on import.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from ..schema.codegen import TAG, X, absolutise, end_anchors, iff, propagate, render
from . import model as M

__all__ = ["FILE_NAME", "build", "main", "write"]

FILE_NAME = "khg-queue-1.0.0.schema.json"
_RECORD = TAG + "khg-record/1.0.0"
_SEMVER = "^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$"


def _local(name: str) -> dict[str, str]:
    return {"$ref": f"#/definitions/{name}"}


def _pat(pattern: str) -> dict[str, Any]:
    return {"type": "string", "pattern": pattern}


def _text() -> dict[str, Any]:
    return {"type": "string", "minLength": 1}


def _definitions() -> dict[str, Any]:
    q008 = "KHG-Q008"
    written = X(q008, {"type": "object", "required": ["id", "version"], "additionalProperties": False,
                       "properties": {"id": _text(), "version": {"type": "integer", "minimum": 1}}})
    actor = X(q008, {"type": "object", "required": ["type", "id"], "additionalProperties": False,
                     "properties": {"type": {"enum": list(M.ACTOR_TYPES)}, "id": _text(), "version": _text()}})
    finding = X("KHG-Q004", {"type": "object", "required": ["code", "severity", "path", "message"],
                             "additionalProperties": False,
                             "properties": {"code": _pat("^KHG-[A-Z][0-9]{3}$"),
                                            "severity": {"enum": list(M.SEVERITIES)},
                                            "path": {"type": "string"}, "message": {"type": "string"}}})
    position = {"type": ["integer", "null"], "minimum": 1}
    verdict = X(q008, {
        "type": "object", "required": ["evidence_id", "core_key", "event_hash", "label", "bindings", "missing"],
        "additionalProperties": False,
        "properties": {
            "evidence_id": _pat("^e[1-9][0-9]*$"), "core_key": _local("sha256"), "event_hash": _local("sha256"),
            "label": {"enum": list(M.LABELS)},
            "bindings": {"type": "array", "items": {
                "type": "object", "required": ["role", "position", "value", "label"], "additionalProperties": False,
                "properties": {"role": _text(), "position": position, "value": {"type": "object"},
                               "bid": _pat("^b[1-9][0-9]*$"), "label": {"enum": list(M.LABELS)},
                               "should_be_role": _text()}}},
            "missing": {"type": "array", "items": {
                "type": "object", "required": ["role"], "additionalProperties": False,
                "properties": {"role": _text(), "position": position, "value": {"type": "object"}}}},
            "note": _text()},
        "allOf": [iff({"label": {"const": "other"}}, ["label"], {"required": ["note"]})]})
    header = X(q008, {
        "type": "object", "required": ["kind", "format", "queue_id", "record_format", "schema", "created_at"],
        "additionalProperties": False,
        "properties": {
            "kind": {"const": "queue-header"},
            "format": _pat("^khg-queue/" + _SEMVER[1:]),
            "queue_id": _pat(M.QUEUE_ID_PATTERN),
            "record_format": _pat("^khg-record/" + _SEMVER[1:]),  # which versions a reader takes is V001's
            "schema": {"type": "object", "required": ["id", "version", "sha256"], "additionalProperties": False,
                       "properties": {"id": _text(), "version": _pat(_SEMVER), "sha256": _local("sha256")}},
            "base": {"type": "object", "required": ["document_id", "sha256"], "additionalProperties": False,
                     "properties": {"document_id": _text(), "sha256": _local("sha256")}},
            "created_at": _local("timestamp")}})
    hyperedge_item = {
        "allOf": [X("KHG-Q001", {"required": ["run", "doc"]}), X("KHG-Q010", {"required": ["keys"]})],
        "properties": {"payload": X("KHG-Q002", {
            "required": ["id", "status"],
            "properties": {"id": _pat(M.CAND_PATTERN), "status": {"const": "candidate"},
                           "evidence": X("KHG-Q001", {"type": "array", "minItems": 1})},
            "allOf": [X("KHG-Q001", {"required": ["evidence"]})]})}}
    item = X(q008, {
        "type": "object", "required": ["kind", "qid", "item_kind", "submitted_at", "payload"],
        "additionalProperties": False,
        "properties": {
            "kind": {"const": "queue-item"},
            "qid": _local("qid"),
            "item_kind": X("KHG-Q003", {"enum": list(M.ITEM_KINDS)}),
            "submitted_at": _local("timestamp"),
            "submitted_by": X("KHG-Q001", _pat(M.SUBMITTED_BY_PATTERN)),
            "run": X({"default": "KHG-Q001", "additionalProperties": q008}, {
                "type": "object", "required": ["run_id", "order_id", "position"], "additionalProperties": False,
                "properties": {"run_id": _text(), "order_id": _text(), "position": {"type": "integer", "minimum": 0},
                               "seed": {"type": "integer"}, "temperature": {"type": "number", "minimum": 0},
                               "model": _text(), "prompt_id": _text(), "skill_id": _text()}}),
            "doc": X({"default": "KHG-Q001", "additionalProperties": q008}, {
                "type": "object", "required": ["doc_id", "doc_sha256"], "additionalProperties": False,
                "properties": {"doc_id": _text(), "doc_sha256": _pat(M.SHA256_PATTERN)}}),
            "payload": {"type": "object"},
            "keys": X("KHG-Q010", {
                "type": "object", "required": ["content_key", "core_key", "key_digest"],
                "additionalProperties": False,
                "properties": {"content_key": _pat(M.SHA256_PATTERN), "core_key": _pat(M.SHA256_PATTERN),
                               "key_digest": {"type": ["string", "null"], "pattern": M.SHA256_PATTERN}}}),
            "entities": {"type": "array", "items": {"$ref": _RECORD + "#/definitions/entity"}}},
        "allOf": [X("KHG-Q001", {"required": ["submitted_by"]}),
                  iff({"item_kind": {"const": "hyperedge"}}, ["item_kind"], hyperedge_item)]})
    entry = X(q008, {
        "type": "object",
        "required": ["kind", "lid", "parent", "target", "action", "state_before", "state_after", "actor", "mode",
                     "at"],
        "additionalProperties": False,
        "properties": {
            "kind": {"const": "log-entry"},
            "lid": _local("lid"),
            "parent": {"type": ["string", "null"], "pattern": M.LID_PATTERN},
            "target": _local("qid"),
            "action": X("KHG-Q003", {"enum": list(M.ACTIONS)}),
            "state_before": X("KHG-Q005", {"enum": list(M.STATES)}),
            "state_after": X("KHG-Q005", {"enum": list(M.STATES)}),
            "actor": _local("actor"),
            "mode": {"enum": list(M.MODES)},
            "at": _local("timestamp"),
            "rule_set": X("KHG-Q004", {"type": "object", "required": ["id", "version"],
                                       "additionalProperties": False,
                                       "properties": {"id": _text(), "version": _text()}}),
            "findings": X("KHG-Q004", {"type": "array", "items": _local("finding")}),
            "outcome": X("KHG-Q004", {"enum": list(M.OUTCOMES)}),
            "reason": _text(),
            "before": {"type": "array", "items": _local("written")},
            "after": {"type": "array", "items": _local("written")},
            "decision_hash": _local("sha256"),
            "verdict": _local("verdict")},
        "allOf": [
            iff({"action": {"const": "lint"}}, ["action"],
                X("KHG-Q004", {"required": ["rule_set", "findings", "outcome"]})),
            iff({"action": {"enum": list(M.REASON_ACTIONS)}}, ["action"], {"required": ["reason"]}),
            iff({"action": {"const": "accept"}}, ["action"], {"required": ["before", "after", "decision_hash"]}),
            iff({"action": {"const": "verdict"}}, ["action"], {"required": ["verdict"]})]})
    return {
        "timestamp": X(q008, _pat(M.TIMESTAMP_PATTERN)),
        "sha256": X(q008, _pat(M.SHA256_PATTERN)),
        "qid": X(q008, _pat(M.QID_PATTERN)),
        "lid": X(q008, _pat(M.LID_PATTERN)),
        "actor": actor,
        "written": written,
        "finding": finding,
        "verdict": verdict,
        "header": header,
        "item": item,
        "entry": entry,
    }


def build() -> dict[str, Any]:
    """The queue schema (absolute ``$ref``s, codes propagated, every pattern ending in ``schema.codegen.END``), as
    packaged."""
    schema = X({"default": "KHG-Q008", "required": "KHG-Q003"}, {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": M.SCHEMA_ID,
        "title": "C3 queue lines khg-queue/1.0.0 (layer Q): the header line, queue items and log entries",
        "description": "One line of a .khg-queue.jsonl file. Line 1 is the queue-header. A queue-item's payload is "
                       "checked by layer C against khg-record #/definitions/hyperedge; the fold, the ids scoped by "
                       "the queue, the keys, entity resolution, the base and replay are checked in Python (layer Q).",
        "type": "object",
        "required": ["kind"],
        "properties": {"kind": X("KHG-Q003", {"enum": list(M.LINE_KINDS)})},
        "allOf": [iff({"kind": {"const": kind}}, ["kind"], _local(name))
                  for kind, name in (("queue-header", "header"), ("queue-item", "item"), ("log-entry", "entry"))],
        "definitions": _definitions(),
    })
    absolutise(schema, schema["$id"])
    propagate(schema)
    end_anchors(schema)  # "$" would also match before a final newline
    return schema


def write(out_dir: str | Path) -> Path:
    """Write the schema into ``out_dir``; returns its path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / FILE_NAME
    path.write_text(render(build()), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: python -m khg_contracts.queue.codegen OUTDIR\n")
        return 2
    sys.stderr.write(f"wrote {write(args[0])}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
