"""Both JSON Schema engines, offline, with closed resolvers (DESIGN §8.1).

- **jsonschema**: a ``referencing.Registry`` preloaded with every packaged schema under its ``$id`` (the vendored HIF
  schema under its https id, ours under ``tag:`` ids). Its ``retrieve`` raises, so nothing is ever fetched; every
  ``$ref`` reachable from a root is resolved when the validator is compiled, so a ``$ref`` to anything that is not
  packaged fails closed at once.
- **fastjsonschema**: a handler map that answers every URI scheme (fastjsonschema opens a URL itself for a scheme
  it has no handler for) and serves only the packaged schemas, as copies, since its resolver rewrites ``$ref``
  values in place. Defaults and formats are never applied, so the instance is never changed.
- **Codes.** A finding's code is the ``x-khg-code`` of the failing subschema: a code, or a map from keyword to code
  with a ``default`` (jsonschema reads ``error.schema`` and ``error.validator``; fastjsonschema reads
  ``exception.definition`` and ``exception.rule``). The generator propagates the codes to every constraint. The
  vendored HIF schema carries no annotations, so its codes come from the H table, keyed on the keyword and the
  instance path.
- **End anchors.** jsonschema matches ``pattern`` with Python's ``re.search``, where ``$`` also matches before a final
  newline; ECMA-262, which JSON Schema names, and fastjsonschema (which rewrites ``$`` to ``\\Z``) do not. The
  generated schemas end their patterns with ``(?!\\n)$`` (``schema.codegen.END``); the jsonschema registry holds
  copies with the same end anchor on every pattern, so a schema generated elsewhere (the queue's) is read alike.

jsonschema reports every violation; fastjsonschema stops at its first, so it gives exactly one finding. Engine
agreement is defined on single-fault inputs: fastjsonschema's code is among jsonschema's.
"""
from __future__ import annotations

import copy
import functools
import re
from types import MappingProxyType
from typing import Any, Callable, Iterator, Mapping

from .. import data
from ..errors import make_finding

__all__ = [
    "C4_SCHEMA_ID",
    "C5_SCHEMA_ID",
    "DRAFT7",
    "ENGINES",
    "HIF_SCHEMA_ID",
    "PROFILE_SCHEMA_ID",
    "RECORD_SCHEMA_ID",
    "RELATION_SCHEMA_ID",
    "TAG",
    "Unresolvable",
    "check_engine",
    "code_of",
    "compile_schema",
    "findings",
    "h_code",
    "pointer",
    "refs",
    "schema_documents",
]

TAG = "tag:khg-contracts,2026:schema/"
HIF_SCHEMA_ID = data.HIF_SCHEMA_ID
RECORD_SCHEMA_ID = TAG + "khg-record/1.0.0"
PROFILE_SCHEMA_ID = TAG + "khg-hif/1.0.0"
RELATION_SCHEMA_ID = TAG + "khg-relation-schema/1.0.0"
C4_SCHEMA_ID = TAG + "khg-c4-items/0.2.0"
C5_SCHEMA_ID = TAG + "khg-c5-io/1.0.0"
DRAFT7 = "http://json-schema.org/draft-07/schema#"
ENGINES = ("jsonschema", "fastjsonschema")
MESSAGE_LIMIT = 200

Finding = dict[str, str]
Runner = Callable[[Any], list[Finding]]


class Unresolvable(LookupError):
    """A ``$ref`` to something that is not a packaged schema: the closed resolvers never fetch it."""


def check_engine(engine: str) -> str:
    """``engine`` when it is ``jsonschema`` or ``fastjsonschema``; ``ValueError`` otherwise."""
    if engine not in ENGINES:
        raise ValueError(f"engine must be one of {', '.join(ENGINES)}, not {engine!r}")
    return engine


# ------------------------------------------------------------------------------------------------ packaged schemas


@functools.cache
def _documents() -> Mapping[str, Mapping[str, Any]]:
    return MappingProxyType(data.schema_documents())


def schema_documents() -> dict[str, dict[str, Any]]:
    """Every packaged JSON Schema by ``$id`` (copies): ours under ``tag:`` ids, the vendored HIF schema, whose
    sha256 is checked, under its https id."""
    return {sid: copy.deepcopy(dict(doc)) for sid, doc in _documents().items()}


def _split(uri: str) -> tuple[str, str]:
    base, _, fragment = uri.partition("#")
    return base, fragment


def _serve(uri: str) -> dict[str, Any]:
    """The packaged document a URI names (a copy); ``Unresolvable`` for anything else."""
    doc = _documents().get(_split(uri)[0])
    if doc is None:
        raise Unresolvable(f"closed resolver: {uri!r} is not a packaged schema")
    return copy.deepcopy(dict(doc))


def refs(schema: Any) -> Iterator[str]:
    """Every ``$ref`` string in a schema document, in document order."""
    stack = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, Mapping):
            ref = node.get("$ref")
            if isinstance(ref, str):
                yield ref
            stack.extend(reversed(list(node.values())))
        elif isinstance(node, list):
            stack.extend(reversed(node))


def _absolute(ref: str, base: str) -> str:
    """A ``$ref`` made absolute against its document's id: only fragment-only refs can be joined, since a
    ``tag:`` base does not join (every packaged ``$ref`` is absolute, §8.1)."""
    if ref.startswith("#"):
        return base + ref
    if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", ref):
        return ref
    raise Unresolvable(f"closed resolver: the relative $ref {ref!r} in {base!r} cannot be resolved")


def _points(doc: Any, fragment: str) -> bool:
    """True when the JSON pointer ``fragment`` (``""`` or ``/a/b``) names a value in ``doc``."""
    if fragment == "":
        return True
    if not fragment.startswith("/"):
        return False
    node = doc
    for part in fragment[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, Mapping) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return False
    return True


def _reachable(root_uri: str) -> list[str]:
    """Every ``$ref`` reachable from ``root_uri`` across the packaged documents, made absolute; ``Unresolvable``
    when one names a document that is not packaged, or a pointer that names nothing."""
    out = [root_uri]
    todo, seen = [root_uri], set()
    while todo:
        uri = todo.pop()
        base, fragment = _split(uri)
        doc = _documents().get(base)
        if doc is None:
            raise Unresolvable(f"closed resolver: {base!r} is not a packaged schema")
        if not _points(doc, fragment):
            raise Unresolvable(f"closed resolver: {uri!r} points at nothing")
        if base in seen:
            continue
        seen.add(base)
        for ref in refs(doc):
            target = _absolute(ref, base)
            out.append(target)
            todo.append(target)
    return out


# ------------------------------------------------------------------------------------------------ codes


def code_of(subschema: Any, keyword: str) -> str | None:
    """The ``x-khg-code`` of a subschema for a failing keyword: the code, or the map's entry for the keyword, else
    its ``default``; None when the subschema carries none."""
    c = subschema.get("x-khg-code") if isinstance(subschema, Mapping) else None
    if isinstance(c, str):
        return c
    if isinstance(c, Mapping):
        return c.get(keyword) or c.get("default")
    return None


def h_code(keyword: str, path: list[Any]) -> str:
    """The H table: the code of a violation of the vendored HIF schema, by keyword and instance path."""
    top = path[0] if path else None
    record_level = len(path) >= 2 and top in ("nodes", "edges", "incidences") and isinstance(path[1], int)
    last = path[-1] if path else None
    if keyword == "required":
        return "KHG-H001" if not path else "KHG-H006"
    if keyword in ("additionalProperties", "unevaluatedProperties"):
        if not path:
            return "KHG-H002"
        return "KHG-H003" if record_level and len(path) == 2 else "KHG-H009"
    if keyword == "type":
        if last in ("attrs", "metadata"):
            return "KHG-H004"
        if record_level and len(path) == 3 and last in ("node", "edge"):
            return "KHG-H007"
        return "KHG-H009"
    if keyword == "enum":
        if path == ["network-type"]:
            return "KHG-H008"
        if last == "direction":
            return "KHG-H005"
    return "KHG-H009"


def pointer(parts: Any) -> str:
    """An RFC 6901 JSON pointer from path parts."""
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def _short(message: str) -> str:
    return message if len(message) <= MESSAGE_LIMIT else message[:MESSAGE_LIMIT - 1] + "…"


def _finding(subschema: Any, keyword: str, path: list[Any], message: str) -> Finding:
    code = code_of(subschema, keyword) or h_code(keyword, path)
    return make_finding(code, pointer(path), _short(message))


# ------------------------------------------------------------------------------------------------ jsonschema


def _end_anchored(doc: Mapping[str, Any]) -> dict[str, Any]:
    """A copy of a schema whose patterns end with ``(?!\\n)$``, the end of the string for Python's ``re`` as for
    ECMA-262 (a no-op on the generated schemas, which already do)."""
    from ..schema.codegen import end_anchors

    out = copy.deepcopy(dict(doc))
    end_anchors(out)
    return out


@functools.cache
def _registry() -> Any:
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7 as SPEC

    def retrieve(uri: str) -> Any:
        raise Unresolvable(f"closed resolver: {uri!r} is not a packaged schema")

    return Registry(retrieve=retrieve).with_resources(  # type: ignore[call-arg]
        (sid, Resource.from_contents(_end_anchored(doc), default_specification=SPEC))
        for sid, doc in _documents().items())


def _jsonschema(root_uri: str) -> Runner:
    import jsonschema
    from referencing.exceptions import Unresolvable as RefUnresolvable

    registry = _registry()
    resolver = registry.resolver()
    for uri in dict.fromkeys(_reachable(root_uri)):
        try:
            resolver.lookup(uri)
        except RefUnresolvable as e:
            raise Unresolvable(f"closed resolver: cannot resolve {uri!r} ({type(e).__name__})") from None
    validator = jsonschema.Draft7Validator({"$ref": root_uri}, registry=registry)

    def run(instance: Any) -> list[Finding]:
        return [_finding(e.schema, str(e.validator), list(e.absolute_path), e.message)
                for e in validator.iter_errors(instance)]
    return run


# ------------------------------------------------------------------------------------------------ fastjsonschema


class _ClosedHandlers(dict):  # type: ignore[type-arg]
    """fastjsonschema's handler map, answering every URI scheme with the packaged-schema server."""

    def __contains__(self, scheme: object) -> bool:
        return True

    def __missing__(self, scheme: str) -> Callable[[str], dict[str, Any]]:
        return _serve


def _fast_path(name: str) -> list[Any]:
    """fastjsonschema's ``data.incidences[3].direction`` -> ``["incidences", 3, "direction"]``."""
    rest = name[len("data"):] if name.startswith("data") else name
    return [m.group(1) if m.group(1) is not None else int(m.group(2))
            for m in re.finditer(r"\.([^.\[\]]+)|\[(\d+)\]", rest)]


def _fastjsonschema(root_uri: str) -> Runner:
    import fastjsonschema

    _reachable(root_uri)  # fail closed before compiling
    compiled = fastjsonschema.compile({"$schema": DRAFT7, "$ref": root_uri}, handlers=_ClosedHandlers(),
                                      use_default=False, use_formats=False)

    def run(instance: Any) -> list[Finding]:
        try:
            compiled(instance)
        except fastjsonschema.JsonSchemaValueException as e:
            return [_finding(e.definition, str(e.rule), _fast_path(str(e.name)), str(e.message))]
        return []
    return run


# ------------------------------------------------------------------------------------------------ entry points


@functools.cache
def compile_schema(root_id: str, fragment: str = "", *, engine: str = "jsonschema") -> Runner:
    """A cached runner ``instance -> findings`` for the packaged schema ``root_id`` (or its ``#fragment``, such as
    ``/definitions/hyperedge``) under one engine. Raises ``Unresolvable`` when a reachable ``$ref`` is not a
    packaged schema, and ``ValueError`` for an unknown engine."""
    check_engine(engine)
    root_uri = root_id + ("#" + fragment if fragment else "")
    if engine == "jsonschema":
        return _jsonschema(root_uri)
    return _fastjsonschema(root_uri)


def findings(root_id: str, instance: Any, *, fragment: str = "", engine: str = "jsonschema",
             path: str = "") -> list[Finding]:
    """The findings of a packaged schema on ``instance`` ([] when it is valid); ``path`` prefixes their paths."""
    out = compile_schema(root_id, fragment, engine=engine)(instance)
    if path:
        for f in out:
            f["path"] = path + f["path"]
    return out
