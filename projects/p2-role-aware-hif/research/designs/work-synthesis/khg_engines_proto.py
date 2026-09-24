"""Prototype of validate/engines.py (DESIGN §8.1): both JSON Schema engines, offline, with closed resolvers.

- jsonschema: a referencing.Registry preloaded with every packaged schema under its $id (the vendored HIF schema under
  its https $id, ours under tag: ids); its retrieve function raises, so nothing is ever fetched.
- fastjsonschema: handlers for http, https and tag that serve only the packaged schemas and raise on anything else.
Codes: an error's code is the x-khg-code of the failing subschema (jsonschema: error.schema; fastjsonschema:
exception.definition), else the H table for the vendored HIF schema (keyword, instance path)."""
from __future__ import annotations

import hashlib
import json
import re
import socket
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).parent
VENDORED = HERE.parent.parent / "probes" / "hif-schema" / "hif_schema_v0.1.0.json"
VENDORED_SHA256 = "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196"
HIF_ID = "https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json"


class Unresolvable(Exception):
    pass


@contextmanager
def no_network():
    """Block sockets, as tests/conftest.py does (F1)."""
    orig = socket.socket

    class _NoNet(socket.socket):
        def connect(self, *a, **k):
            raise OSError("network disabled")
    socket.socket = _NoNet
    try:
        yield
    finally:
        socket.socket = orig


def load_schemas(schema_dir: Path) -> dict:
    raw = VENDORED.read_bytes()
    if hashlib.sha256(raw).hexdigest() != VENDORED_SHA256:
        raise RuntimeError("the vendored HIF schema does not hash to the pinned value")
    out = {}
    hs = json.loads(raw)
    out[hs["$id"]] = hs
    for p in sorted(Path(schema_dir).glob("*.schema.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        out[s["$id"]] = s
    return out


def _split(uri):
    base, _, frag = uri.partition("#")
    return base, frag


# ------------------------------------------------------------------ the H table (vendored schema, no x-khg-code)

def h_code(keyword, path):
    path = [p for p in path]
    top = path[0] if path else None
    depth_record = len(path) >= 2 and top in ("nodes", "edges", "incidences") and isinstance(path[1], int)
    last = path[-1] if path else None
    if keyword == "required":
        return "KHG-H001" if not path else "KHG-H006"
    if keyword in ("additionalProperties", "unevaluatedProperties"):
        return "KHG-H002" if not path else ("KHG-H003" if depth_record and len(path) == 2 else "KHG-H009")
    if keyword == "type":
        if last in ("attrs", "metadata"):
            return "KHG-H004"
        if depth_record and len(path) == 3 and last in ("node", "edge"):
            return "KHG-H007"
        return "KHG-H009"
    if keyword == "enum":
        if path == ["network-type"]:
            return "KHG-H008"
        if last == "direction":
            return "KHG-H005"
    return "KHG-H009"


def _code_of(sub, keyword):
    c = sub.get("x-khg-code") if isinstance(sub, dict) else None
    if isinstance(c, str):
        return c
    if isinstance(c, dict):
        return c.get(keyword) or c.get("default")
    return None


# ------------------------------------------------------------------ jsonschema

class JSValidator:
    def __init__(self, schemas: dict, root_id: str, fragment: str = ""):
        import jsonschema
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7

        def retrieve(uri):
            raise Unresolvable(f"closed registry: {uri} is not packaged")
        reg = Registry(retrieve=retrieve)
        for sid, s in schemas.items():
            reg = reg.with_resource(sid, Resource.from_contents(s, default_specification=DRAFT7))
        schema = {"$ref": root_id + ("#" + fragment if fragment else "")}
        self.v = jsonschema.Draft7Validator(schema, registry=reg)
        self.vendored_id = next(i for i in schemas if i.startswith("https://"))

    def findings(self, instance):
        out = []
        for e in self.v.iter_errors(instance):
            out.extend(self._flatten(e))
        return out

    def _flatten(self, e):
        # descend into $ref wrappers: an error on the root $ref carries the real errors in context only for anyOf/oneOf;
        # for $ref, jsonschema reports the inner error directly with its own schema
        code = _code_of(e.schema, e.validator)
        if code is None:
            code = h_code(e.validator, list(e.absolute_path))
        return [{"code": code, "path": "/" + "/".join(str(p) for p in e.absolute_path), "keyword": e.validator,
                 "message": e.message[:160]}]


# ------------------------------------------------------------------ fastjsonschema

class FastValidator:
    def __init__(self, schemas: dict, root_id: str, fragment: str = ""):
        import fastjsonschema

        def serve(uri):
            base, _ = _split(uri)
            if base in schemas:
                return schemas[base]
            raise Unresolvable(f"closed handlers: {uri} is not packaged")
        handlers = {"http": serve, "https": serve, "tag": serve}
        schema = {"$schema": "http://json-schema.org/draft-07/schema#",
                  "$ref": root_id + ("#" + fragment if fragment else "")}
        self.f = fastjsonschema.compile(schema, handlers=handlers)
        self.vendored = schemas[next(i for i in schemas if i.startswith("https://"))]

    def findings(self, instance):
        import fastjsonschema
        try:
            self.f(instance)
            return []
        except fastjsonschema.JsonSchemaValueException as e:
            code = _code_of(e.definition, e.rule)
            path = _fast_path(e.name)
            if code is None:
                code = h_code(e.rule, path)
            return [{"code": code, "path": "/" + "/".join(str(p) for p in path), "keyword": e.rule,
                     "message": e.message[:160]}]


def _fast_path(name):
    """'data.incidences[3].direction' -> ['incidences', 3, 'direction']"""
    out = []
    for m in re.finditer(r"\.([^.\[\]]+)|\[(\d+)\]", name[len("data"):] if name.startswith("data") else name):
        out.append(m.group(1) if m.group(1) is not None else int(m.group(2)))
    return out


def validators(schemas, root_id, fragment="", engines=("jsonschema", "fastjsonschema")):
    out = {}
    if "jsonschema" in engines:
        out["jsonschema"] = JSValidator(schemas, root_id, fragment)
    if "fastjsonschema" in engines:
        out["fastjsonschema"] = FastValidator(schemas, root_id, fragment)
    return out
