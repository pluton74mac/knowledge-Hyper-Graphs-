"""Development tool: generates the packaged draft-07 JSON Schemas (DESIGN §8.1), so their codes stay consistent.

``python -m khg_contracts.schema.codegen OUTDIR`` writes:

- ``khg-record-1.0.0.schema.json``          C1 containers, records and JSONL lines (layer C)
- ``khg-relation-schema-1.0.0.schema.json`` relation-type schema documents (layer M, structural part)
- ``khg-hif-1.0.0.schema.json``             the HIF profile: ``allOf`` the vendored HIF schema plus the P rules
- ``khg-c4-items-0.1.0.schema.json``        C4 item lines (layer I); ``$ref``s into khg-record by ``tag:`` URI
- ``khg-c5-io-1.0.0.schema.json``           C5 system outputs

Every subschema that carries a constraint also carries ``x-khg-code``: a code, or a map from keyword to code with an
optional ``"default"``. Codes are authored at a few levels and propagated to every constraint-bearing subschema, so
both engines can name the code of a failure (jsonschema from ``error.schema``, fastjsonschema from
``exception.definition``). Every ``$ref`` is absolute. The packaged files are the output of this module, byte for
byte (``tests/schema/test_codegen.py``). Nothing here runs when the package is imported for use.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable

from .builtins import CONSTRAINT_TYPES, DATATYPES, POLICIES, SEVERITIES, SLOTS, TIME_MODELS

__all__ = ["TAG", "X", "iff", "propagate", "absolutise", "render", "build", "build_all", "write_all", "main"]

TAG = "tag:khg-contracts,2026:schema/"
HIF_ID = "https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json"
HIF_URL = ("https://raw.githubusercontent.com/HIF-org/HIF-standard/"
           "b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json")
HIF_SHA = "sha256:639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196"
STATUSES = ["candidate", "asserted", "disputed", "superseded", "retracted", "quoted", "goal"]
CONSTRAINT_KEYS = {"type", "enum", "const", "multipleOf", "maximum", "exclusiveMaximum", "minimum", "exclusiveMinimum",
                   "maxLength", "minLength", "pattern", "maxItems", "minItems", "uniqueItems", "contains",
                   "maxProperties", "minProperties", "required", "additionalProperties", "dependencies",
                   "propertyNames", "not", "anyOf", "oneOf"}
CHILD_MAPS = ("properties", "definitions", "patternProperties")
CHILD_ONE = ("items", "additionalProperties", "not", "if", "then", "else", "propertyNames", "contains",
             "additionalItems")
CHILD_LIST = ("allOf", "anyOf", "oneOf")
SEMVER = "^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$"


# ------------------------------------------------------------------------------------------------ helpers


def X(code: Any, s: dict[str, Any]) -> dict[str, Any]:
    """Attach an ``x-khg-code`` to a subschema."""
    s = dict(s)
    s["x-khg-code"] = code
    return s


def propagate(s: Any, inherited: Any = None) -> None:
    """Give every constraint-bearing subschema an ``x-khg-code``, inherited from the nearest ancestor that has one."""
    if not isinstance(s, dict):
        return
    code = s.get("x-khg-code", inherited)
    if "x-khg-code" not in s and CONSTRAINT_KEYS & set(s) and code is not None:
        s["x-khg-code"] = copy.deepcopy(code)
    for k in CHILD_MAPS:
        for v in (s.get(k) or {}).values():
            propagate(v, code)
    for k in CHILD_ONE:
        if isinstance(s.get(k), dict):
            propagate(s[k], code)
    for k in CHILD_LIST:
        for v in s.get(k) or []:
            propagate(v, code)
    if isinstance(s.get("dependencies"), dict):
        for v in s["dependencies"].values():
            if isinstance(v, dict):
                propagate(v, code)


def iff(cond_props: dict[str, Any], required: list[str], then: dict[str, Any], els: dict[str, Any] | None = None,
        code: Any = None) -> dict[str, Any]:
    """An if/then(/else) dispatch on property values (used instead of oneOf and anyOf)."""
    s: dict[str, Any] = {"if": {"properties": cond_props, "required": required}, "then": then}
    if els is not None:
        s["else"] = els
    return X(code, s) if code else s


def absolutise(s: Any, base: str) -> None:
    """Make every ``$ref`` absolute (fastjsonschema cannot join a relative ref against a ``tag:`` base URI)."""
    if isinstance(s, dict):
        for k, v in s.items():
            if k == "$ref" and isinstance(v, str) and v.startswith("#"):
                s[k] = base + v
            else:
                absolutise(v, base)
    elif isinstance(s, list):
        for v in s:
            absolutise(v, base)


def render(schema: dict[str, Any]) -> str:
    """The file text of a generated schema."""
    return json.dumps(schema, ensure_ascii=False, indent=1) + "\n"


def ref(name: str, doc: str = "khg-record/1.0.0") -> dict[str, str]:
    return {"$ref": f"{TAG}{doc}#/definitions/{name}"}


def LOCAL(n: str) -> dict[str, str]:
    return {"$ref": f"#/definitions/{n}"}


def pat(p: str) -> dict[str, Any]:
    return X({"type": "KHG-C010", "pattern": "KHG-C011"}, {"type": "string", "pattern": p})


# ------------------------------------------------------------------------------------------------ khg-record/1.0.0


def _record() -> dict[str, Any]:
    ID = X({"type": "KHG-C010", "pattern": "KHG-C011"},
           {"type": "string", "pattern": "^(?!_:)[^\\s\\x00-\\x1f\\x7f]{1,512}$"})
    VOCAB = X({"type": "KHG-C010", "pattern": "KHG-C011"},
              {"type": "string", "pattern": "^[^\\s\\x00-\\x1f\\x7f]{1,256}$"})
    defs = {
        "id": ID,
        "vocab_id": VOCAB,
        "bid": pat("^b[1-9][0-9]*$"),
        "eid": pat("^e[1-9][0-9]*$"),
        "semver": pat(SEMVER),
        "versioned_id": pat("^[^\\s\\x00-\\x1f\\x7f/]{1,256}/(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$"),
        "timestamp": pat("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{1,6})?Z$"),
        "instant": X({"type": "KHG-C010", "pattern": "KHG-C011"},
                     {"type": "string", "pattern": "^[+-][0-9]{4,}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"}),
        "sha256": pat("^sha256:[0-9a-f]{64}$"),
        "decimal": X({"type": "KHG-C011", "pattern": "KHG-C004"},
                     {"type": "string", "pattern": "^(\\+0|[+-](0\\.[0-9]*[1-9]|[1-9][0-9]*(\\.[0-9]*[1-9])?))$"}),
        "extensions": X("KHG-C011", {"type": "object", "propertyNames": {"pattern": "^[a-z][a-z0-9-]*:[^\\s]+$"}}),
        "header": X({"default": "KHG-C010", "additionalProperties": "KHG-C009", "enum": "KHG-C002",
                     "const": "KHG-C002"}, {
            "type": "object", "required": ["kind", "format", "document_id", "schema", "content"],
            "additionalProperties": False,
            "properties": {
                "kind": {"const": "header"},
                "format": pat("^khg-record/(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$"),
                "document_id": LOCAL("id"),
                "schema": {"type": "object", "required": ["id", "version", "sha256"], "additionalProperties": False,
                           "properties": {"id": LOCAL("vocab_id"), "version": LOCAL("semver"),
                                          "sha256": LOCAL("sha256")}},
                "content": {"enum": ["snapshot", "history"]},
                "as_at": LOCAL("timestamp"),
                "complete": {"type": "boolean"},
                "created_at": LOCAL("timestamp"),
                "generator": {"type": "object", "required": ["name", "version"], "additionalProperties": False,
                              "properties": {"name": {"type": "string"}, "version": {"type": "string"}}},
                "extensions": LOCAL("extensions"),
            }}),
        "record": X({"default": "KHG-C010", "enum": "KHG-C002"}, {
            "type": "object", "required": ["kind"],
            "properties": {"kind": {"enum": ["entity", "hyperedge", "relation-schema"]}},
            "allOf": [iff({"kind": {"const": "entity"}}, ["kind"], LOCAL("entity")),
                      iff({"kind": {"const": "hyperedge"}}, ["kind"], LOCAL("hyperedge")),
                      iff({"kind": {"const": "relation-schema"}}, ["kind"],
                          {"required": ["format", "id", "version"],
                           "properties": {"format": pat("^khg-relation-schema/[0-9]+\\.[0-9]+\\.[0-9]+$")}})]}),
        "entity": X({"default": "KHG-C010", "additionalProperties": "KHG-C009", "const": "KHG-C002"}, {
            "type": "object", "required": ["kind", "id", "types"], "additionalProperties": False,
            "properties": {
                "kind": {"const": "entity"}, "id": LOCAL("id"),
                "types": {"type": "array", "items": LOCAL("vocab_id"), "minItems": 1},
                "label": {"type": "string"}, "aliases": {"type": "array", "items": {"type": "string"}},
                "redirect_to": LOCAL("id"), "version": {"type": "integer", "minimum": 1},
                "recorded_at": LOCAL("timestamp"), "recorded_by": {"type": "string", "minLength": 1},
                "extensions": LOCAL("extensions")}}),
        "hyperedge": X({"default": "KHG-C010", "additionalProperties": "KHG-C009", "enum": "KHG-C002",
                        "const": "KHG-C002"}, {
            "type": "object", "required": ["kind", "id", "relation", "status", "bindings"],
            "additionalProperties": False,
            "properties": {
                "kind": {"const": "hyperedge"}, "id": LOCAL("id"), "relation": LOCAL("vocab_id"),
                "status": {"enum": STATUSES}, "status_ref": LOCAL("id"),
                "bindings": {"type": "array", "items": LOCAL("binding")},
                "evidence": {"type": "array", "items": LOCAL("evidence")},
                "rank": {"enum": ["preferred", "normal", "deprecated"]},
                "rank_reason": {"type": "array", "items": LOCAL("vocab_id"), "minItems": 1},
                "visibility": {"enum": ["visible", "suppressed"]},
                "confidence": LOCAL("confidence"),
                "goal": {"type": "object", "required": ["brief"], "additionalProperties": False,
                         "properties": {"brief": {"type": "string", "minLength": 1}, "owner": {"type": "string"}}},
                "reason": LOCAL("vocab_id"), "note": {"type": "string"}, "source_text": {"type": "string"},
                "typed_under": LOCAL("versioned_id"), "version": {"type": "integer", "minimum": 1},
                "recorded_at": LOCAL("timestamp"), "recorded_by": {"type": "string", "minLength": 1},
                "derived": {"type": "object"}, "extensions": LOCAL("extensions")},
            "allOf": [
                iff({"status": {"enum": ["disputed", "superseded", "retracted"]}}, ["status"],
                    X("KHG-C006", {"required": ["status_ref"]})),
                iff({"status": {"enum": ["candidate", "asserted", "quoted", "goal"]}}, ["status"],
                    X("KHG-C006", {"not": {"required": ["status_ref"]}})),
                iff({"rank": {"const": "deprecated"}}, ["rank"], X("KHG-C008", {"required": ["rank_reason"]})),
                iff({"status": {"not": {"const": "goal"}}}, ["status"], X("KHG-C012", {"not": {"required": ["goal"]}})),
                iff({"relation": {"pattern": "^khg:"}}, ["relation"], X("KHG-C012", {"required": ["reason"]}),
                    X("KHG-C012", {"not": {"anyOf": [{"required": ["reason"]}, {"required": ["note"]}]}})),
                iff({"status": {"not": {"const": "goal"}}}, ["status"],
                    {"properties": {"bindings": {"items": {"properties": {
                        "value": X("KHG-C005", {"not": {"required": ["unbound"]}})}}}}}),
            ]}),
        "binding": X({"default": "KHG-C010", "additionalProperties": "KHG-C009", "enum": "KHG-C002"}, {
            "type": "object", "required": ["bid", "role", "value"], "additionalProperties": False,
            "properties": {"bid": LOCAL("bid"), "role": LOCAL("vocab_id"), "value": LOCAL("value"),
                           "position": {"type": "integer", "minimum": 1}, "direction": {"enum": ["head", "tail"]},
                           "extensions": LOCAL("extensions")}}),
        "value": X({"default": "KHG-C001", "enum": "KHG-C002"}, {
            "type": "object", "minProperties": 1, "maxProperties": 1,
            "propertyNames": {"enum": ["entity", "literal", "fact", "special", "unbound"]},
            "properties": {"entity": LOCAL("id"), "fact": LOCAL("id"), "literal": LOCAL("literal"),
                           "special": {"enum": ["somevalue", "novalue"]}, "unbound": LOCAL("unbound")}}),
        "unbound": X({"default": "KHG-C010", "additionalProperties": "KHG-C009", "enum": "KHG-C002"}, {
            "type": "object", "required": ["var"], "additionalProperties": False,
            "properties": {"var": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]{0,63}$"},
                           "expect": {"type": "object", "additionalProperties": False,
                                      "properties": {"entity_types": {"type": "array", "items": LOCAL("vocab_id"),
                                                                      "minItems": 1},
                                                     "datatype": {"enum": DATATYPES}}}}}),
        "literal": X({"default": "KHG-C004", "additionalProperties": "KHG-C009"}, {
            "type": "object", "required": ["datatype"], "properties": {"datatype": X("KHG-C002", {"enum": DATATYPES})},
            "allOf": [
                iff({"datatype": {"const": "time"}}, ["datatype"], {
                    "required": ["datatype", "time", "precision"], "additionalProperties": False,
                    "properties": {"datatype": {}, "time": {"type": "string", "pattern":
                                                            "^[+-][0-9]{4,}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"},
                                   "precision": {"type": "integer", "minimum": 0, "maximum": 14},
                                   "calendar": {"enum": ["gregorian", "julian"]}}}),
                iff({"datatype": {"const": "quantity"}}, ["datatype"], {
                    "required": ["datatype", "amount", "unit"], "additionalProperties": False,
                    "dependencies": {"lower": ["upper"], "upper": ["lower"]},
                    "properties": {"datatype": {}, "amount": LOCAL("decimal"), "lower": LOCAL("decimal"),
                                   "upper": LOCAL("decimal"),
                                   "unit": {"type": "string",
                                            "pattern": "^(1|(?!_:)[^\\s\\x00-\\x1f\\x7f]{1,512})$"}}}),
                iff({"datatype": {"enum": ["string", "iri"]}}, ["datatype"], {
                    "required": ["datatype", "value"], "additionalProperties": False,
                    "properties": {"datatype": {}, "value": {"type": "string"}}}),
                iff({"datatype": {"const": "iri"}}, ["datatype"], {
                    "properties": {"value": {"pattern": "^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"}}}),
                iff({"datatype": {"const": "lang_string"}}, ["datatype"], {
                    "required": ["datatype", "value", "lang"], "additionalProperties": False,
                    "properties": {"datatype": {}, "value": {"type": "string"},
                                   "lang": {"type": "string", "pattern": "^[a-z]{1,8}(-[a-z0-9]{1,8})*$"}}}),
                iff({"datatype": {"const": "boolean"}}, ["datatype"], {
                    "required": ["datatype", "value"], "additionalProperties": False,
                    "properties": {"datatype": {}, "value": {"type": "boolean"}}}),
                iff({"datatype": {"const": "geo"}}, ["datatype"], {
                    "required": ["datatype", "lat", "lon", "precision", "globe"], "additionalProperties": False,
                    "properties": {"datatype": {}, "lat": LOCAL("decimal"), "lon": LOCAL("decimal"),
                                   "precision": LOCAL("decimal"), "globe": LOCAL("id")}}),
            ]}),
        "evidence": X({"default": "KHG-C007", "additionalProperties": "KHG-C009", "enum": "KHG-C002"}, {
            "type": "object", "required": ["id", "type", "mode", "source"], "additionalProperties": False,
            "properties": {
                "id": LOCAL("eid"),
                "type": {"enum": ["curated", "imported", "extracted", "inferred", "agent_bound"]},
                "mode": {"enum": ["manual", "automatic", "semi_automatic"]},
                "source": {"type": "object", "required": ["doc_id"], "additionalProperties": False,
                           "properties": {"doc_id": {"type": "string", "minLength": 1}, "doc_sha256": LOCAL("sha256"),
                                          "url": {"type": "string"}, "retrieved_at": LOCAL("timestamp"),
                                          "version": {"type": "string"}, "licence": {"type": "string"}}},
                "selectors": {"type": "array", "minItems": 1, "items": LOCAL("selector")},
                "activity": {"type": "object", "required": ["agent"], "additionalProperties": False,
                             "properties": {k: {"type": "string"} for k in
                                            ("agent", "agent_version", "model", "model_version", "prompt_id",
                                             "skill_id", "run_id")}},
                "inference": {"type": "object", "required": ["rule", "from"], "additionalProperties": False,
                              "properties": {"rule": {"type": "string", "minLength": 1},
                                             "from": {"type": "array", "items": LOCAL("id")}}},
                "supports": {"type": "array", "items": LOCAL("bid"), "uniqueItems": True},
                "confidence": LOCAL("confidence"),
                "epistemics": {"type": "object", "additionalProperties": False,
                               "properties": {"negated": {"type": "boolean"}, "hypothesis": {"type": "boolean"}}},
                "reference": {"type": "array", "items": {"type": "object", "required": ["role", "value"],
                                                         "additionalProperties": False,
                                                         "properties": {"role": LOCAL("vocab_id"),
                                                                        "value": LOCAL("value")}}},
                "recorded_at": LOCAL("timestamp"), "event_hash": LOCAL("sha256")},
            "allOf": [
                iff({"type": {"const": "extracted"}}, ["type"],
                    {"required": ["selectors", "activity"],
                     "properties": {"source": {"required": ["doc_id", "doc_sha256"]}}}),
                {"if": {"required": ["selectors"]},
                 "then": {"properties": {"source": {"required": ["doc_id", "doc_sha256"]}}}},
                iff({"type": {"const": "inferred"}}, ["type"], {"required": ["inference"]}),
                {"if": {"required": ["inference"],
                        "properties": {"inference": {"properties": {"rule": {"const": "model"}},
                                                     "required": ["rule"]}}},
                 "then": {"required": ["activity"],
                          "properties": {"activity": {"required": ["agent", "model", "model_version"]}}},
                 "else": {"properties": {"inference": {"properties": {"from": {"minItems": 1}}}}}},
            ]}),
        "selector": X({"default": "KHG-C007", "additionalProperties": "KHG-C009", "enum": "KHG-C002"}, {
            "type": "object", "required": ["type"], "properties": {"type": {"enum": ["quote", "position"]}},
            "allOf": [
                iff({"type": {"const": "quote"}}, ["type"], {
                    "required": ["type", "exact"], "additionalProperties": False,
                    "properties": {"type": {}, "exact": {"type": "string", "minLength": 1},
                                   "prefix": {"type": "string"}, "suffix": {"type": "string"}}}),
                iff({"type": {"const": "position"}}, ["type"], {
                    "required": ["type", "start", "end"], "additionalProperties": False,
                    "properties": {"type": {}, "start": {"type": "integer", "minimum": 0},
                                   "end": {"type": "integer", "minimum": 0}}})]}),
        "confidence": X("KHG-C003", {
            "type": "object", "required": ["value", "scale"], "additionalProperties": False,
            "properties": {"value": {"type": "number"}, "scale": LOCAL("vocab_id"),
                           "scorer": {"type": "object", "required": ["name", "version"], "additionalProperties": False,
                                      "properties": {"name": {"type": "string"}, "version": {"type": "string"}}}}}),
    }
    return X({"default": "KHG-C010", "additionalProperties": "KHG-C009"}, {
        "$schema": "http://json-schema.org/draft-07/schema#", "$id": TAG + "khg-record/1.0.0",
        "title": "C1 container khg-record/1.0.0 (layer C, draft). JSONL lines use #/definitions/header and "
                 "#/definitions/record",
        "type": "object", "required": ["header", "records"], "additionalProperties": False,
        "properties": {"header": LOCAL("header"), "records": {"type": "array", "items": LOCAL("record")}},
        "definitions": defs})


# ------------------------------------------------------------------------------------------------ khg-relation-schema


def _relation_schema() -> dict[str, Any]:
    """The meta-schema of ``khg-relation-schema/1.0.0`` (§3). Structural checks only; M002, M003, M005, M007 (naming),
    M008-M013, M016 and M017 need the whole document and run in Python (``khg_contracts.schema.checks``)."""
    def string() -> dict[str, str]:
        return {"type": "string"}

    defs = {
        "vocab_id": {"type": "string", "pattern": "^[^\\s\\x00-\\x1f\\x7f]{1,256}$"},
        "mappings": {"type": "object", "propertyNames": {"pattern": "^[a-z][a-z0-9-]*$"},
                     "additionalProperties": {"type": "string", "minLength": 1}},
        "entity_type": {"type": "object", "required": ["id"], "additionalProperties": False,
                        "properties": {"id": LOCAL("vocab_id"),
                                       "parents": {"type": "array", "items": LOCAL("vocab_id"), "uniqueItems": True}}},
        "role": {"type": "object", "required": ["id"], "additionalProperties": False,
                 "properties": {"id": LOCAL("vocab_id"), "label": string(),
                                "aliases": {"type": "array", "items": string()}, "mappings": LOCAL("mappings")}},
        "confidence_scale": {"type": "object", "required": ["id", "kind", "min", "max"], "additionalProperties": False,
                             "properties": {"id": LOCAL("vocab_id"), "kind": {"const": "bounded"},
                                            "min": {"type": "number"}, "max": {"type": "number"}}},
        "time_model": X("KHG-M007", {
            "type": "object", "required": ["model"], "properties": {"model": {"enum": TIME_MODELS}},
            "allOf": [iff({"model": {"const": "interval"}}, ["model"],
                          {"required": ["model", "start", "end"], "additionalProperties": False,
                           "properties": {"model": {}, "start": {"type": "string", "minLength": 1},
                                          "end": {"type": "string", "minLength": 1}}},
                          {"additionalProperties": False, "properties": {"model": {}}})]}),
        "filler": {
            "type": "object", "propertyNames": {"enum": ["entity", "literal", "fact", "units", "precision_min"]},
            "if": {"required": ["entity"]},
            "then": {"additionalProperties": False,
                     "properties": {"entity": {"type": "array", "items": LOCAL("vocab_id"), "uniqueItems": True}}},
            "else": {
                "if": {"required": ["literal"]},
                "then": {"additionalProperties": False,
                         "properties": {"literal": X("KHG-M006", {"enum": DATATYPES}),
                                        "units": {"type": "array", "items": {"type": "string", "minLength": 1},
                                                  "minItems": 1, "uniqueItems": True},
                                        "precision_min": {"type": "integer", "minimum": 0, "maximum": 14}}},
                "else": {
                    "if": {"required": ["fact"]},
                    "then": {"additionalProperties": False,
                             "properties": {"fact": {"type": "array", "items": LOCAL("vocab_id"),
                                                     "uniqueItems": True}}},
                    "else": {"not": {}}}}},
        "usage": {
            "type": "object", "required": ["role", "slot", "fillers", "min", "max"], "additionalProperties": False,
            "properties": {"role": LOCAL("vocab_id"), "slot": {"enum": SLOTS},
                           "fillers": {"type": "array", "minItems": 1, "items": LOCAL("filler")},
                           "min": {"type": "integer", "minimum": 0},
                           "max": {"type": ["integer", "null"], "minimum": 1},
                           "ordered": {"type": "boolean"}, "complete": {"type": "boolean"},
                           "direction": {"enum": ["tail", "head"]},
                           "somevalue": {"type": "boolean"}, "novalue": {"type": "boolean"}, "label": string()},
            "allOf": [iff({"complete": {"const": True}}, ["complete"],
                          X("KHG-M014", {"properties": {"min": {"minimum": 1}}})),
                      iff({"slot": {"const": "time"}}, ["slot"],
                          X("KHG-M007", {"properties": {"max": {"const": 1},
                                                        "fillers": {"maxItems": 1, "items": {
                                                            "required": ["literal"],
                                                            "properties": {"literal": {"const": "time"}}}}}}))]},
        "constraint": {"type": "object", "required": ["type", "roles", "severity"], "additionalProperties": False,
                       "properties": {"type": {"enum": CONSTRAINT_TYPES},
                                      "roles": {"type": "array", "items": LOCAL("vocab_id"), "minItems": 2,
                                                "uniqueItems": True},
                                      "severity": {"enum": SEVERITIES}}},
        "key": {"type": "object", "required": ["roles"], "additionalProperties": False,
                "properties": {"roles": {"type": "array", "items": LOCAL("vocab_id"), "minItems": 1,
                                         "uniqueItems": True},
                               "temporal": {"type": "boolean"}, "on_collision": {"enum": POLICIES}}},
        "primary": X("KHG-M012", {"type": "object", "required": ["subject", "object"], "additionalProperties": False,
                                  "properties": {"subject": {"type": "string", "minLength": 1},
                                                 "object": {"type": "string", "minLength": 1}}}),
        "relation": {
            "type": "object", "required": ["id"], "additionalProperties": False,
            "properties": {"id": LOCAL("vocab_id"), "kind": {"enum": ["fact"]}, "label": string(),
                           "mappings": LOCAL("mappings"), "primary": LOCAL("primary"), "time": LOCAL("time_model"),
                           "key": LOCAL("key"), "constraints": {"type": "array", "items": LOCAL("constraint")},
                           "roles": X({"default": "KHG-M015", "minItems": "KHG-M001"},
                                      {"type": "array", "minItems": 1, "items": LOCAL("usage")})},
            "allOf": [X("KHG-M001", {"required": ["roles"]})]},
    }
    return X("KHG-M015", {
        "$schema": "http://json-schema.org/draft-07/schema#", "$id": TAG + "khg-relation-schema/1.0.0",
        "title": "Relation-type schema document khg-relation-schema/1.0.0 (layer M, structural part; the M checks "
                 "that need the whole document run in Python)",
        "type": "object", "required": ["kind", "format", "id", "version", "roles", "relations"],
        "additionalProperties": False,
        "properties": {
            "kind": {"const": "relation-schema"},
            "format": {"type": "string", "pattern": "^khg-relation-schema/(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\."
                                                    "(0|[1-9][0-9]*)$"},
            "id": {"type": "string", "pattern": "^[^\\s\\x00-\\x1f\\x7f/]{1,256}$"},
            "version": X("KHG-M004", {"type": "string", "pattern": SEMVER}),
            "label": string(),
            "entity_types": {"type": "array", "items": LOCAL("entity_type")},
            "roles": {"type": "array", "items": LOCAL("role")},
            "relations": {"type": "array", "items": LOCAL("relation")},
            "default_time": LOCAL("time_model"),
            "confidence_scales": {"type": "array", "items": LOCAL("confidence_scale")},
        },
        "definitions": defs})


# ------------------------------------------------------------------------------------------------ khg-hif/1.0.0


def _profile() -> dict[str, Any]:
    khg_md = ["khg-profile", "khg-record", "khg-schema", "khg-schema-sha256", "khg-document-id", "khg-complete",
              "khg-slice", "khg-schema-document", "khg-literal-nodes"]
    hid = X({"type": "KHG-P002", "pattern": "KHG-P003"},
            {"type": "string",
             "pattern": "^(_:ref:[^\\s\\x00-\\x1f\\x7f]{1,512}|(?!_:ref:)[^\\s\\x00-\\x1f\\x7f]{1,512})$"})
    return X("KHG-P001", {
        "$schema": "http://json-schema.org/draft-07/schema#", "$id": TAG + "khg-hif/1.0.0",
        "title": "HIF profile khg-hif/1.0.0 (layer P, draft): the vendored HIF schema plus the profile rules",
        "allOf": [{"$ref": HIF_ID}, {"$ref": "#/definitions/profile"}],
        "definitions": {
            "hif_id": hid,
            "profile": X("KHG-P001", {
                "type": "object", "required": ["metadata"],
                "properties": {
                    "network-type": X("KHG-P007", {"not": {"const": "asc"}}),
                    "metadata": X({"default": "KHG-P001", "propertyNames": "KHG-P008", "const": "KHG-P009",
                                   "enum": "KHG-P009", "type": "KHG-P009"}, {
                        "type": "object",
                        "required": ["hif-schema", "hif-schema-sha256", "khg-profile", "khg-record", "khg-schema",
                                     "khg-schema-sha256", "khg-document-id", "khg-literal-nodes"],
                        "propertyNames": X("KHG-P008", {"not": {"anyOf": [{"const": "default_attrs"},
                                                                          {"allOf": [{"pattern": "^khg-"},
                                                                                     {"not": {"enum": khg_md}}]}]}}),
                        "properties": {
                            "hif-schema": {"const": HIF_URL}, "hif-schema-sha256": {"const": HIF_SHA},
                            "khg-literal-nodes": {"enum": ["shared", "per_binding"]},
                            "khg-document-id": {"type": "string"}, "khg-complete": {"type": "boolean"},
                            "khg-schema-document": {"type": "object"},
                            "khg-slice": {"type": "object", "required": ["relations"],
                                          "properties": {"relations": {"type": "array",
                                                                       "items": {"type": "string"}}}}}}),
                    "nodes": {"type": "array", "items": X({"default": "KHG-P013", "type": "KHG-P013"}, {
                        "required": ["attrs"],
                        "properties": {
                            "node": LOCAL("hif_id"),
                            "attrs": {"type": "object", "required": ["khg-kind"],
                                      "properties": {"khg-kind": {"enum": ["entity", "literal", "somevalue", "novalue",
                                                                           "unbound", "fact-ref"]}},
                                      "allOf": [iff({"khg-kind": {"const": "literal"}}, ["khg-kind"],
                                                    {"required": ["khg-literal"]}),
                                                iff({"khg-kind": {"const": "unbound"}}, ["khg-kind"],
                                                    {"required": ["khg-unbound"]}),
                                                iff({"khg-kind": {"const": "fact-ref"}}, ["khg-kind"],
                                                    {"required": ["khg-ref"]})]}}})},
                    "edges": {"type": "array", "items": X("KHG-P012", {
                        "required": ["attrs"],
                        "properties": {"edge": LOCAL("hif_id"),
                                       "attrs": {"type": "object", "required": ["relation", "khg-status"],
                                                 "properties": {"relation": {"type": "string", "minLength": 1},
                                                                "khg-status": {"enum": STATUSES}}}}})},
                    "incidences": {"type": "array",
                                   "items": X({"default": "KHG-P005", "propertyNames": "KHG-P014"}, {
                        "required": ["attrs"],
                        "properties": {"edge": LOCAL("hif_id"), "node": LOCAL("hif_id"),
                                       "attrs": {"type": "object", "required": ["role", "khg-bid"],
                                                 "propertyNames": X("KHG-P014", {"not": {"anyOf": [
                                                     {"const": "roles"},
                                                     {"allOf": [{"pattern": "^khg-"},
                                                                {"not": {"enum": ["khg-bid", "khg-extensions"]}}]}]}}),
                                                 "properties": {"khg-bid": {"type": "string",
                                                                            "pattern": "^b[1-9][0-9]*$"}}}}})},
                }})}})


# ------------------------------------------------------------------------------------------------ khg-c4-items/0.1.0


C4_KINDS = ["c4-header", "c4-extraction-doc", "c4-completion-query", "c4-retrieval-question", "c4-memory-trace",
            "c4-memory-question", "c4-split-manifest"]


def _c4() -> dict[str, Any]:
    where = {"type": "object", "required": ["as_of", "valid_mode", "rank", "status"], "additionalProperties": False,
             "properties": {"as_of": {"anyOf": [ref("instant"), {"type": "null"}]},
                            "valid_mode": {"enum": ["definite", "possible"]},
                            "rank": {"type": "array", "items": {"enum": ["preferred", "normal", "deprecated"]},
                                     "minItems": 1},
                            "status": {"type": "array", "items": {"enum": STATUSES}, "minItems": 1}}}
    answer = {"type": "object", "required": ["values"], "additionalProperties": False,
              "properties": {"values": {"type": "array", "items": ref("value")}, "text": {"type": "string"}}}
    keypat = {"type": "array", "minItems": 1,
              "items": {"type": "object", "required": ["role", "value"], "additionalProperties": False,
                        "properties": {"role": ref("vocab_id"), "value": ref("value")}}}
    common = ["kind", "id", "qset", "split"]
    common_props = {"kind": {"enum": C4_KINDS}, "id": ref("id"), "qset": {"type": "string", "minLength": 1},
                    "split": {"enum": ["train", "valid", "test"]}}

    def item(required: list[str], props: dict[str, Any]) -> dict[str, Any]:
        p = dict(common_props)
        p.update(props)
        return {"type": "object", "required": common + required, "additionalProperties": False, "properties": p}

    c4 = X({"default": "KHG-I002"}, {
        "$schema": "http://json-schema.org/draft-07/schema#", "$id": TAG + "khg-c4-items/0.1.0",
        "title": "C4 question-set lines khg-c4-items/0.1.0 (layer I, draft); C1 values and records by $ref to "
                 "khg-record",
        "type": "object", "required": ["kind"],
        "properties": {"kind": X("KHG-I001", {"enum": C4_KINDS})},
        "allOf": [
            iff({"kind": {"const": "c4-header"}}, ["kind"], {
                "required": ["kind", "format", "qset", "record_format", "schema"], "additionalProperties": False,
                "properties": {"kind": {}, "format": {"type": "string",
                                                      "pattern": "^khg-c4-items/[0-9]+\\.[0-9]+\\.[0-9]+$"},
                               "qset": {"type": "string"}, "record_format": {"const": "khg-record/1.0.0"},
                               "schema": {"type": "object", "required": ["id", "version", "sha256"]},
                               "created_by": {"type": "string"}, "created_at": ref("timestamp")}}),
            iff({"kind": {"const": "c4-extraction-doc"}}, ["kind"], item(
                ["doc_id", "text", "text_sha256", "annotation", "gold"],
                {"doc_id": {"type": "string"}, "text": {"type": "string"}, "text_sha256": ref("sha256"),
                 "annotation": {"type": "object", "required": ["guideline"],
                                "properties": {"guideline": {"type": "string"}, "annotators": {"type": "integer"},
                                               "adjudicated": {"type": "boolean"}}},
                 "gold": {"type": "array", "items": ref("hyperedge")},
                 "entities": {"type": "array", "items": ref("entity")}})),
            iff({"kind": {"const": "c4-completion-query"}}, ["kind"], item(
                ["qid", "fact_id", "relation", "arity", "model_arity", "target", "context", "candidate_universe"],
                {"qid": ref("id"), "fact_id": ref("id"), "relation": ref("vocab_id"),
                 "arity": {"type": "integer", "minimum": 0}, "model_arity": {"type": "integer", "minimum": 0},
                 "target": {"type": "object", "required": ["bid", "role", "slot", "value"],
                            "additionalProperties": False,
                            "properties": {"bid": ref("bid"), "role": ref("vocab_id"),
                                           "slot": {"enum": ["core", "qualifier"]}, "value": ref("value")}},
                 "context": {"type": "array", "items": ref("binding")},
                 "candidate_universe": {"type": "object", "required": ["kind"],
                                        "properties": {"kind": {"enum": ["entities_of_type", "list"]},
                                                       "types": {"type": "array", "items": ref("vocab_id")},
                                                       "ids": {"type": "array", "items": ref("id")}}}})),
            iff({"kind": {"const": "c4-retrieval-question"}}, ["kind"], item(
                ["qid", "type", "text", "anchors", "answer", "support", "hops", "source_class", "answerable", "where"],
                {"qid": ref("id"),
                 "type": {"enum": ["single_hop", "multi_hop", "temporal", "comparison", "aggregation"]},
                 "text": {"type": "string", "minLength": 1},
                 "anchors": {"type": "array", "items": ref("id"), "minItems": 1},
                 "answer": answer,
                 "support": {"type": "object", "required": ["sets"],
                             "properties": {"sets": {"type": "array", "items": {"type": "array",
                                                                                "items": ref("id")}}}},
                 "hops": {"type": "integer", "minimum": 1}, "source_class": {"type": "string"},
                 "answerable": {"type": "boolean"}, "where": where, "provenance": {"type": "object"}})),
            iff({"kind": {"const": "c4-memory-trace"}}, ["kind"], item(
                ["trace_id", "entities", "events"],
                {"trace_id": ref("id"), "entities": {"type": "array", "items": ref("entity")},
                 "events": {"type": "array", "minItems": 1, "items": {
                     "type": "object", "required": ["step", "tx_time"], "additionalProperties": False,
                     "properties": {"step": {"type": "integer", "minimum": 1}, "tx_time": ref("timestamp"),
                                    "put": {"type": "array", "items": ref("hyperedge"), "minItems": 1},
                                    "apply": {"type": "object", "required": ["op"]}},
                     "oneOf": [{"required": ["put"]}, {"required": ["apply"]}]}}})),
            iff({"kind": {"const": "c4-memory-question"}}, ["kind"], item(
                ["qid", "trace_id", "ask_after_step", "subtype", "text", "relation", "key", "target_role", "where",
                 "answer", "stale_values", "future_values", "disputed_values", "support", "answerable"],
                {"qid": ref("id"), "trace_id": ref("id"), "ask_after_step": {"type": "integer", "minimum": 1},
                 "subtype": {"enum": ["current_value", "past_value", "future_value", "abstention"]},
                 "text": {"type": "string", "minLength": 1}, "relation": ref("vocab_id"), "key": keypat,
                 "target_role": ref("vocab_id"), "where": where, "answer": answer,
                 "stale_values": X("KHG-I004", {"type": "array", "items": {
                     "type": "object", "required": ["value", "kind"], "additionalProperties": False,
                     "properties": {"value": ref("value"), "kind": {"enum": ["expired", "revised"]}}}}),
                 "future_values": X("KHG-I004", {"type": "array", "items": ref("value")}),
                 "disputed_values": {"type": "array", "items": ref("value")},
                 "support": {"type": "array", "items": ref("id")}, "answerable": {"type": "boolean"},
                 "tolerance": {"type": "object"}})),
            iff({"kind": {"const": "c4-split-manifest"}}, ["kind"], {
                "required": ["kind", "id", "qset", "splits"], "additionalProperties": False,
                "properties": {"kind": {}, "id": ref("id"), "qset": {"type": "string"},
                               "splits": {"type": "object",
                                          "additionalProperties": {"enum": ["train", "valid", "test"]}}}}),
        ]})
    # a memory question missing stale_values or future_values is I004, not the generic I002
    for sub in c4["allOf"]:
        th = sub["then"]
        if th.get("properties", {}).get("stale_values"):
            th["x-khg-code"] = {"default": "KHG-I002", "required": "KHG-I004"}
            th["required"] = [r for r in th["required"] if r not in ("stale_values", "future_values")]
            sub["then"] = {"allOf": [th, X("KHG-I004", {"required": ["stale_values", "future_values"]})]}
    return c4


# ------------------------------------------------------------------------------------------------ khg-c5-io/1.0.0


def _c5io() -> dict[str, Any]:
    cost = {"type": "object", "required": ["prompt_tokens", "completion_tokens", "llm_calls", "retrieval_calls",
                                           "retrieval_ms", "wall_ms"],
            "additionalProperties": False,
            "properties": {k: {"type": "integer", "minimum": 0} for k in
                           ("prompt_tokens", "completion_tokens", "llm_calls", "retrieval_calls",
                            "hyperedges_visited")}}
    cost["properties"].update({"retrieval_ms": {"type": "number", "minimum": 0},
                               "wall_ms": {"type": "number", "minimum": 0},
                               "usd": {"type": "number", "minimum": 0}, "price_table": {"type": "string"}})
    sys_answer = {"type": "object", "required": ["values", "abstained"], "additionalProperties": False,
                  "properties": {"values": {"type": "array", "items": ref("value")}, "text": {"type": "string"},
                                 "abstained": {"type": "boolean"}}}
    unit = {"type": "object", "required": ["rank", "unit_id", "unit_kind", "hyperedge_ids"],
            "additionalProperties": False,
            "properties": {"rank": {"type": "integer", "minimum": 1}, "unit_id": {"type": "string"},
                           "unit_kind": {"enum": ["hyperedge", "pair", "chunk", "path", "community"]},
                           "hyperedge_ids": {"type": "array", "items": ref("id")},
                           "bids": {"type": "array", "items": {"type": "array", "items": {"type": "string"},
                                                               "minItems": 2, "maxItems": 2}}}}
    return X("KHG-C010", {
        "$schema": "http://json-schema.org/draft-07/schema#", "$id": TAG + "khg-c5-io/1.0.0",
        "title": "C5 system outputs khg-c5-io/1.0.0 (draft): completion rank records, retrieval and memory "
                 "responses. Extraction outputs are C3 queue items.",
        "type": "object", "required": ["kind", "qid"],
        "properties": {"kind": {"enum": ["completion-rank", "retrieval-response", "memory-response"]},
                       "qid": ref("id")},
        "allOf": [
            iff({"kind": {"const": "completion-rank"}}, ["kind"], {
                "required": ["kind", "qid", "n_candidates", "n_filtered_out", "n_greater", "n_equal"],
                "additionalProperties": False,
                "properties": {"kind": {}, "qid": {}, "n_candidates": {"type": "integer", "minimum": 1},
                               "n_filtered_out": {"type": "integer", "minimum": 0},
                               "n_greater": {"type": "integer", "minimum": 0},
                               "n_equal": {"type": "integer", "minimum": 0},
                               "target_prob": {"type": "number", "minimum": 0, "maximum": 1},
                               "top1": {"type": "object", "required": ["value", "prob"],
                                        "properties": {"value": ref("value"),
                                                       "prob": {"type": "number", "minimum": 0, "maximum": 1}}},
                               "prob_map": {"type": "object", "additionalProperties": {"type": "number"}},
                               "model_rank": {"type": "integer", "minimum": 1}}}),
            iff({"kind": {"const": "retrieval-response"}}, ["kind"], {
                "required": ["kind", "qid", "answer", "retrieved", "cost"], "additionalProperties": False,
                "properties": {"kind": {}, "qid": {}, "answer": sys_answer,
                               "retrieved": {"type": "array", "items": unit},
                               "support_claimed": {"type": "array", "items": ref("id")}, "cost": cost}}),
            iff({"kind": {"const": "memory-response"}}, ["kind"], {
                "required": ["kind", "qid", "answer"], "additionalProperties": False,
                "properties": {"kind": {}, "qid": {}, "answer": sys_answer,
                               "value_scores": {"type": "array",
                                                "items": {"type": "object", "required": ["value", "score"],
                                                          "properties": {"value": ref("value"),
                                                                         "score": {"type": "number"}}}},
                               "retrieved": {"type": "array", "items": unit}, "cost": cost}}),
        ]})


# ------------------------------------------------------------------------------------------------ driver


BUILDERS: dict[str, Callable[[], dict[str, Any]]] = {
    "khg-record-1.0.0": _record,
    "khg-relation-schema-1.0.0": _relation_schema,
    "khg-hif-1.0.0": _profile,
    "khg-c4-items-0.1.0": _c4,
    "khg-c5-io-1.0.0": _c5io,
}


def build(name: str) -> dict[str, Any]:
    """One generated schema (absolute ``$ref``s, codes propagated), by file stem, e.g. ``khg-record-1.0.0``."""
    schema = BUILDERS[name]()
    absolutise(schema, schema["$id"])
    propagate(schema)
    return schema


def build_all() -> dict[str, dict[str, Any]]:
    """Every generated schema, by file name (``<stem>.schema.json``)."""
    return {f"{name}.schema.json": build(name) for name in BUILDERS}


def write_all(out_dir: str | Path) -> list[Path]:
    """Write every generated schema into ``out_dir``; returns the paths written."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for fname, schema in build_all().items():
        p = out / fname
        p.write_text(render(schema), encoding="utf-8")
        written.append(p)
    return written


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: python -m khg_contracts.schema.codegen OUTDIR\n")
        return 2
    for p in write_all(args[0]):
        sys.stderr.write(f"wrote {p}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
