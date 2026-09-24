"""Build the draft-07 JSON Schemas of design A from shared definitions (prototype, not the package).

Writes into ./schemas/:
  khg-document-1.0.0.json   C1 document / record schema
  khg-hif-profile-1.0.0.json  the KHG profile of HIF: allOf [vendored HIF 0.1.0, profile constraints]
  khg-schema-1.0.0.json     meta-schema of relation-type schema documents
  khg-queue-1.0.0.json      C3 queue item and action-log entry
Every schema is self-contained (definitions bundled) except the profile's $ref to the vendored HIF schema,
which resolves offline through a registry keyed by the HIF schema's own $id.
"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "schemas")
HIF_ID = "https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json"
HIF_PINNED = ("https://raw.githubusercontent.com/HIF-org/HIF-standard/"
              "b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json")
HIF_SHA256 = "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196"

SEMVER = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
D = {
    # ids: non-empty, no C0/DEL control characters, never the reserved derived prefix "_:"
    "id": {"type": "string", "minLength": 1, "pattern": "^(?!_:)[^\\u0000-\\u001f\\u007f]+$"},
    # role, relation and type names: Unicode allowed (NFC checked in layer S); one optional prefix;
    # no whitespace, no '/', no control characters, no leading '_:' (reserved)
    "name": {"type": "string",
             "pattern": "^(?!_:)[^\\s/:\\u0000-\\u001f\\u007f]+(:[^\\s/:\\u0000-\\u001f\\u007f]+)?$"},
    "semver": {"type": "string", "pattern": "^" + SEMVER + "$"},
    "profileVersion": {"type": "string", "pattern": "^1\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$"},
    "schemaRef": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*/" + SEMVER + "$"},
    # ISO 8601 reduced precision (year, month, day, second, UTC) and ISO 8601-2 / EDTF unspecified
    # digits for decade (YYYX), century (YYXX) and millennium (YXXX)
    "timeValue": {"type": "string",
                  "pattern": "^-?([0-9]{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01])(T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z)?)?)?|[0-9]{3}X|[0-9]{2}XX|[0-9]XXX)$"},
    "datetime": {"type": "string",
                 "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\\.[0-9]{1,6})?Z$"},
    # canonical decimal: no '+', no leading zeros, no trailing fractional zeros, no '-0'
    "decimal": {"type": "string", "pattern": "^(0|-?[1-9][0-9]*|-?(0|[1-9][0-9]*)\\.[0-9]*[1-9])$"},
    "status": {"enum": ["asserted", "superseded", "retracted", "goal", "candidate"]},
    "direction": {"enum": ["tail", "head"]},
    "valid": {"type": "object", "minProperties": 1, "additionalProperties": False,
              "properties": {"from": {"$ref": "#/definitions/timeValue"},
                             "until": {"$ref": "#/definitions/timeValue"}}},
    "literal": {
        "type": "object", "required": ["datatype", "value"], "additionalProperties": False,
        "properties": {
            "datatype": {"enum": ["string", "text", "iri", "quantity", "time"]},
            "value": {"type": "string"},
            "lang": {"type": "string", "pattern": "^[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$"},
            "unit": {"type": "string", "minLength": 1},
            "lower": {"$ref": "#/definitions/decimal"},
            "upper": {"$ref": "#/definitions/decimal"},
            "calendar": {"enum": ["julian"]}},
        "allOf": [
            {"if": {"properties": {"datatype": {"const": "quantity"}}},
             "then": {"required": ["unit"], "properties": {"value": {"$ref": "#/definitions/decimal"}}},
             "else": {"not": {"anyOf": [{"required": ["unit"]}, {"required": ["lower"]}, {"required": ["upper"]}]}}},
            {"if": {"properties": {"datatype": {"const": "text"}}},
             "then": {"required": ["lang"]}, "else": {"not": {"required": ["lang"]}}},
            {"if": {"properties": {"datatype": {"const": "time"}}},
             "then": {"properties": {"value": {"$ref": "#/definitions/timeValue"}}},
             "else": {"not": {"required": ["calendar"]}}},
            {"if": {"properties": {"datatype": {"const": "iri"}}},
             "then": {"properties": {"value": {"pattern": "^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"}}}}]},
    "confidence": {
        "type": "object", "required": ["value", "scale"], "additionalProperties": False,
        "properties": {"value": {"type": "number"}, "scale": {"enum": ["probability", "score"]},
                       "min": {"type": "number"}, "max": {"type": "number"}},
        "if": {"properties": {"scale": {"const": "score"}}},
        "then": {"required": ["min", "max"]},
        "else": {"properties": {"value": {"minimum": 0, "maximum": 1}},
                 "not": {"anyOf": [{"required": ["min"]}, {"required": ["max"]}]}}},
    "evidence": {
        "type": "object", "required": ["id", "type"], "additionalProperties": False,
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "type": {"enum": ["curated", "imported", "extracted", "inferred"]},
            "source": {"type": "string", "minLength": 1},
            "digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "exact": {"type": "string", "minLength": 1},
            "prefix": {"type": "string"},
            "suffix": {"type": "string"},
            "start": {"type": "integer", "minimum": 0},
            "end": {"type": "integer", "minimum": 1},
            "reference": {"type": "array", "minItems": 1, "items": {"$ref": "#/definitions/binding"}},
            "agent": {"type": "string", "minLength": 1},
            "version": {"type": "string", "minLength": 1},
            "run": {"type": "string", "minLength": 1},
            "model": {"type": "string", "minLength": 1},
            "prompt": {"type": "string", "minLength": 1},
            "params": {"type": "object"},
            "confidence": {"$ref": "#/definitions/confidence"}},
        "dependencies": {"start": ["end", "digest", "exact"], "end": ["start"],
                         "prefix": ["exact"], "suffix": ["exact"]}},
    "binding": {
        "type": "object", "required": ["role"], "additionalProperties": False,
        "properties": {
            "role": {"$ref": "#/definitions/name"},
            "node": {"$ref": "#/definitions/id"},
            "literal": {"$ref": "#/definitions/literal"},
            "edge": {"$ref": "#/definitions/id"},
            "special": {"enum": ["somevalue", "novalue", "unbound"]},
            "direction": {"$ref": "#/definitions/direction"},
            "position": {"type": "integer", "minimum": 0},
            "evidence": {"type": "array", "minItems": 1, "uniqueItems": True,
                         "items": {"type": "string", "minLength": 1}},
            "attrs": {"type": "object",
                      "propertyNames": {"not": {"enum": ["role", "position", "evidence"]}}},
            "weight": {"type": "number"}},
        "oneOf": [{"required": ["node"]}, {"required": ["literal"]},
                  {"required": ["edge"]}, {"required": ["special"]}]},
    "node": {
        "type": "object", "required": ["node"], "additionalProperties": False,
        "properties": {
            "node": {"$ref": "#/definitions/id"},
            "types": {"type": "array", "uniqueItems": True, "items": {"$ref": "#/definitions/name"}},
            "label": {"type": "string"},
            "attrs": {"type": "object",
                      "propertyNames": {"not": {"enum": ["types", "label", "literal", "special", "edge"]}}},
            "weight": {"type": "number"}}},
    "edge": {
        "type": "object", "required": ["edge", "relation", "status", "bindings"],
        "additionalProperties": False,
        "properties": {
            "edge": {"$ref": "#/definitions/id"},
            "relation": {"$ref": "#/definitions/name"},
            "status": {"$ref": "#/definitions/status"},
            "bindings": {"type": "array", "minItems": 1, "items": {"$ref": "#/definitions/binding"}},
            "valid": {"$ref": "#/definitions/valid"},
            "evidence": {"type": "array", "items": {"$ref": "#/definitions/evidence"}},
            "rank": {"enum": ["preferred", "normal", "deprecated"]},
            "visibility": {"enum": ["visible", "suppressed"]},
            "recorded": {"$ref": "#/definitions/datetime"},
            "schema": {"$ref": "#/definitions/schemaRef"},
            "superseded-by": {"type": "array", "minItems": 1, "uniqueItems": True,
                              "items": {"$ref": "#/definitions/id"}},
            "attrs": {"type": "object", "propertyNames": {"not": {"enum": [
                "relation", "status", "valid", "evidence", "rank", "visibility", "recorded", "schema",
                "superseded-by"]}}},
            "weight": {"type": "number"}},
        "if": {"properties": {"status": {"const": "superseded"}}},
        "then": {"required": ["superseded-by"]},
        "else": {"not": {"required": ["superseded-by"]}}},
    "metadata": {
        "type": "object", "required": ["khg-profile", "khg-schema"],
        "properties": {"khg-profile": {"$ref": "#/definitions/profileVersion"},
                       "khg-schema": {"$ref": "#/definitions/schemaRef"}},
        "propertyNames": {"not": {"enum": ["role-convention", "hif-schema", "hif-schema-sha256"]}}},
}


def defs(*names):
    """Bundle the named definitions plus everything they reference (transitively)."""
    out, todo = {}, list(names)
    while todo:
        n = todo.pop()
        if n in out:
            continue
        out[n] = copy.deepcopy(D[n])
        s = json.dumps(D[n])
        for m in D:
            if f'"#/definitions/{m}"' in s:
                todo.append(m)
    return dict(sorted(out.items()))


def document_schema():
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "urn:khg-contracts:schema:c1-document:1.0.0",
        "title": "KHG contracts C1 document 1.0.0 (JSON container; JSONL lines use #/definitions/node, "
                 "#/definitions/edge and a first line {\"metadata\": ...})",
        "type": "object", "required": ["metadata", "edges"], "additionalProperties": False,
        "properties": {"metadata": {"$ref": "#/definitions/metadata"},
                       "nodes": {"type": "array", "items": {"$ref": "#/definitions/node"}},
                       "edges": {"type": "array", "items": {"$ref": "#/definitions/edge"}}},
        "definitions": defs("metadata", "node", "edge"),
    }


def hif_profile_schema():
    d = defs("name", "profileVersion", "schemaRef", "semver", "valid", "evidence", "literal",
             "datetime", "status", "id")
    reserved_node = {"anyOf": [{"required": ["literal"]}, {"required": ["special"]}, {"required": ["edge"]}]}
    profile = {
        "type": "object",
        "required": ["network-type", "metadata", "incidences", "edges"],
        "properties": {
            "network-type": {"enum": ["directed", "undirected"]},
            "metadata": {
                "type": "object",
                "required": ["role-convention", "khg-profile", "khg-schema", "hif-schema", "hif-schema-sha256"],
                "properties": {
                    "role-convention": {"$ref": "#/definitions/semver"},
                    "khg-profile": {"$ref": "#/definitions/profileVersion"},
                    "khg-schema": {"$ref": "#/definitions/schemaRef"},
                    "hif-schema": {"const": HIF_PINNED},
                    "hif-schema-sha256": {"const": HIF_SHA256},
                    "default_attrs": False}},
            "incidences": {"type": "array", "items": {
                "type": "object", "required": ["attrs"],
                "properties": {
                    "edge": {"type": "string", "minLength": 1},
                    "node": {"type": "string", "minLength": 1},
                    "attrs": {"type": "object", "required": ["role"],
                              "properties": {
                                  "role": {"$ref": "#/definitions/name"},
                                  "position": {"type": "integer", "minimum": 0},
                                  "evidence": {"type": "array", "minItems": 1, "uniqueItems": True,
                                               "items": {"type": "string", "minLength": 1}}}}}}},
            "nodes": {"type": "array", "items": {
                "type": "object",
                "properties": {"node": {"type": "string", "minLength": 1}},
                "if": {"properties": {"node": {"pattern": "^_:"}}, "required": ["node"]},
                "then": {"required": ["attrs"], "properties": {"attrs": {
                    "type": "object", "maxProperties": 1,
                    "oneOf": [
                        {"required": ["literal"], "properties": {"literal": {"$ref": "#/definitions/literal"}}},
                        {"required": ["special"], "properties": {"special": {"enum": ["somevalue", "novalue", "unbound"]}}},
                        {"required": ["edge"], "properties": {"edge": {"$ref": "#/definitions/id"}}}]}}},
                "else": {"properties": {
                    "node": {"$ref": "#/definitions/id"},
                    "attrs": {"not": reserved_node,
                              "properties": {"types": {"type": "array", "uniqueItems": True,
                                                       "items": {"$ref": "#/definitions/name"}},
                                             "label": {"type": "string"}}}}}}},
            "edges": {"type": "array", "items": {
                "type": "object", "required": ["attrs"],
                "properties": {
                    "edge": {"$ref": "#/definitions/id"},
                    "attrs": {"type": "object", "required": ["relation", "status"],
                              "properties": {
                                  "relation": {"$ref": "#/definitions/name"},
                                  "status": {"$ref": "#/definitions/status"},
                                  "valid": {"$ref": "#/definitions/valid"},
                                  "evidence": {"type": "array", "items": {"$ref": "#/definitions/evidence"}},
                                  "rank": {"enum": ["preferred", "normal", "deprecated"]},
                                  "visibility": {"enum": ["visible", "suppressed"]},
                                  "recorded": {"$ref": "#/definitions/datetime"},
                                  "schema": {"$ref": "#/definitions/schemaRef"},
                                  "superseded-by": {"type": "array", "minItems": 1, "uniqueItems": True,
                                                    "items": {"$ref": "#/definitions/id"}}}}}}}},
        "if": {"properties": {"network-type": {"const": "directed"}}, "required": ["network-type"]},
        "then": {"properties": {"incidences": {"items": {"required": ["direction"]}}}},
    }
    # evidence.reference items are bindings; in HIF they are carried verbatim in edge attrs
    d.update(defs("binding"))
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "urn:khg-contracts:schema:khg-hif-profile:1.0.0",
        "title": "KHG profile of HIF 1.0.0 (profile-valid implies HIF-valid)",
        "allOf": [{"$ref": HIF_ID}, profile],
        "definitions": dict(sorted(d.items())),
    }


def relation_schema_metaschema():
    usage = {
        "type": "object", "required": ["slot"], "additionalProperties": False,
        "properties": {
            "slot": {"enum": ["core", "qualifier", "meta"]},
            "types": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"$ref": "#/definitions/name"}},
            "datatypes": {"type": "array", "minItems": 1, "uniqueItems": True,
                          "items": {"enum": ["string", "text", "iri", "quantity", "time"]}},
            "edges": {"type": "array", "minItems": 1, "uniqueItems": True,
                      "items": {"anyOf": [{"const": "*"}, {"$ref": "#/definitions/name"}]}},
            "values": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string"}},
            "min": {"type": "integer", "minimum": 0, "default": 0},
            "max": {"type": ["integer", "null"], "minimum": 1, "default": 1},
            "ordered": {"type": "boolean", "default": False},
            "direction": {"$ref": "#/definitions/direction"},
            "label": {"type": "string"}},
        "anyOf": [{"required": ["types"]}, {"required": ["datatypes"]}, {"required": ["edges"]}],
        "dependencies": {"values": ["datatypes"]}}
    described = {"type": "object", "additionalProperties": False,
                 "properties": {"label": {"type": "string"},
                                "aliases": {"type": "array", "items": {"type": "string"}},
                                "mappings": {"type": "object", "additionalProperties": {"type": "string"}}}}
    relation = {
        "type": "object", "required": ["roles"], "additionalProperties": False,
        "properties": {
            "label": {"type": "string"},
            "aliases": {"type": "array", "items": {"type": "string"}},
            "mappings": {"type": "object", "additionalProperties": {"type": "string"}},
            "roles": {"type": "object", "minProperties": 1,
                      "propertyNames": {"$ref": "#/definitions/name"},
                      "additionalProperties": {"$ref": "#/definitions/usage"}},
            "key": {"type": "object", "required": ["roles"], "additionalProperties": False,
                    "properties": {
                        "roles": {"type": "array", "minItems": 1, "uniqueItems": True,
                                  "items": {"$ref": "#/definitions/name"}},
                        "temporal": {"type": "boolean", "default": False},
                        "on-collision": {"enum": ["reject", "flag", "end-older", "supersede-older"],
                                         "default": "flag"}},
                    "if": {"properties": {"on-collision": {"const": "end-older"}}, "required": ["on-collision"]},
                    "then": {"required": ["temporal"], "properties": {"temporal": {"const": True}}}}}}
    d = defs("name", "schemaRef", "profileVersion", "direction")
    d.update({"usage": usage, "described": described, "relation": relation})
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "urn:khg-contracts:schema:relation-schema:1.0.0",
        "title": "KHG relation-type schema document 1.0.0",
        "type": "object", "required": ["khg-schema", "khg-profile", "roles", "relations"],
        "additionalProperties": False,
        "properties": {
            "khg-schema": {"$ref": "#/definitions/schemaRef"},
            "khg-profile": {"$ref": "#/definitions/profileVersion"},
            "label": {"type": "string"},
            "types": {"type": "object", "propertyNames": {"$ref": "#/definitions/name"},
                      "additionalProperties": {"$ref": "#/definitions/described"}},
            "roles": {"type": "object", "propertyNames": {"$ref": "#/definitions/name"},
                      "additionalProperties": {"$ref": "#/definitions/described"}},
            "valid-roles": {"type": "object", "additionalProperties": False, "minProperties": 1,
                            "properties": {"from": {"$ref": "#/definitions/name"},
                                           "until": {"$ref": "#/definitions/name"}}},
            "relations": {"type": "object", "propertyNames": {"$ref": "#/definitions/name"},
                          "additionalProperties": {"$ref": "#/definitions/relation"}}},
        "definitions": dict(sorted(d.items())),
    }


def queue_schema():
    d = defs("edge", "node", "datetime", "metadata")
    key = {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}
    item = {
        "type": "object", "required": ["item", "at", "payload", "keys"], "additionalProperties": False,
        "properties": {
            "item": {"type": "string", "minLength": 1},
            "at": {"$ref": "#/definitions/datetime"},
            "payload": {"allOf": [{"$ref": "#/definitions/edge"},
                                  {"properties": {"status": {"const": "candidate"}}}]},
            "nodes": {"type": "array", "items": {"$ref": "#/definitions/node"}},
            "schema": {"$ref": "#/definitions/schemaRef"},
            "keys": {"type": "object", "required": ["content", "core", "events"], "additionalProperties": False,
                     "properties": {"content": key, "core": key,
                                    "events": {"type": "array", "items": key}}},
            "order": {"type": "object", "required": ["permutation", "position"], "additionalProperties": False,
                      "properties": {"permutation": {"type": "string", "minLength": 1},
                                     "position": {"type": "integer", "minimum": 0}}}}}
    actions = ["flag", "fix", "verdict", "accept", "merge", "reject", "review"]
    entry = {
        "type": "object", "required": ["log", "at", "item", "actor", "action"], "additionalProperties": False,
        "properties": {
            "log": {"type": "string", "minLength": 1},
            "at": {"$ref": "#/definitions/datetime"},
            "item": {"type": "string", "minLength": 1},
            "actor": {"type": "object", "required": ["agent"], "additionalProperties": False,
                      "properties": {"agent": {"type": "string", "minLength": 1},
                                     "version": {"type": "string", "minLength": 1}}},
            "action": {"enum": actions},
            "rule": {"type": "string", "pattern": "^KHG-[A-Z][0-9]{3}$"},
            "severity": {"enum": ["violation", "warning", "info"]},
            "path": {"type": "string"},
            "message": {"type": "string"},
            "reason": {"type": "string"},
            "verdict": {"enum": ["correct", "no-support", "wrong-relation", "wrong-role", "wrong-filler",
                                 "missing-participant", "other"]},
            "evidence": {"type": "string", "minLength": 1},
            "bindings": {"type": "array", "items": {"type": "integer", "minimum": 0}},
            "target": {"$ref": "#/definitions/id"},
            "before": {"type": "object"},
            "after": {"type": "object"}},
        "allOf": [
            {"if": {"properties": {"action": {"const": "flag"}}}, "then": {"required": ["rule", "severity", "message"]}},
            {"if": {"properties": {"action": {"const": "fix"}}}, "then": {"required": ["rule", "before", "after"]}},
            {"if": {"properties": {"action": {"const": "verdict"}}}, "then": {"required": ["verdict"]}},
            {"if": {"properties": {"action": {"const": "accept"}}}, "then": {"required": ["after"]}},
            {"if": {"properties": {"action": {"const": "merge"}}}, "then": {"required": ["target", "after"]}},
            {"if": {"properties": {"action": {"enum": ["reject", "review"]}}}, "then": {"required": ["reason"]}},
            {"if": {"properties": {"verdict": {"const": "other"}}, "required": ["verdict"]},
             "then": {"required": ["reason"]}}]}
    d.update({"item": item, "entry": entry})
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "urn:khg-contracts:schema:c3-queue:1.0.0",
        "title": "KHG contracts C3 queue stream line 1.0.0 (header, queue item or action-log entry)",
        "oneOf": [
            {"type": "object", "required": ["metadata"], "additionalProperties": False,
             "properties": {"metadata": {"allOf": [{"$ref": "#/definitions/metadata"},
                                                   {"required": ["queue"],
                                                    "properties": {"queue": {"type": "string", "minLength": 1}}}]}}},
            {"$ref": "#/definitions/item"},
            {"$ref": "#/definitions/entry"}],
        "definitions": dict(sorted(d.items())),
    }


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("khg-document-1.0.0.json", document_schema),
                     ("khg-hif-profile-1.0.0.json", hif_profile_schema),
                     ("khg-schema-1.0.0.json", relation_schema_metaschema),
                     ("khg-queue-1.0.0.json", queue_schema)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(fn(), f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("wrote", name)
