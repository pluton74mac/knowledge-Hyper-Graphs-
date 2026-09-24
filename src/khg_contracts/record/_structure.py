"""Layers V and C for ``write_container``: the ``khg-record`` version gate and the packaged record schema.

Layer C is ``khg-record-1.0.0.schema.json`` run by jsonschema with a closed resolver (nothing is fetched); the code
of a finding is the ``x-khg-code`` of the failing subschema (C010 by default, DESIGN §8.1). This is a small
runner for one self-contained schema; ``validate`` runs the full pipelines.
"""
from __future__ import annotations

import functools
import re
from typing import Any, Callable, Mapping

from .. import data
from ..errors import make_finding

__all__ = ["RECORD_SCHEMA", "RECORD_SCHEMA_ID", "FORMAT", "version_findings", "structure_findings"]

RECORD_SCHEMA = "schemas/khg-record-1.0.0.schema.json"
RECORD_SCHEMA_ID = "tag:khg-contracts,2026:schema/khg-record/1.0.0"
FORMAT = "khg-record/1.0.0"
_FORMAT = re.compile(r"khg-record/(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")

Finding = dict[str, str]


def version_findings(container: Any) -> list[Finding]:
    """V001 unless the header's ``format`` is ``khg-record/1.0.x`` (another major or a newer minor is refused)."""
    header = container.get("header") if isinstance(container, Mapping) else None
    fmt = header.get("format") if isinstance(header, Mapping) else None
    m = _FORMAT.fullmatch(fmt) if isinstance(fmt, str) else None
    if m and int(m.group(1)) == 1 and int(m.group(2)) == 0:
        return []
    return [make_finding("KHG-V001", "/header/format", f"format {fmt!r} is not {FORMAT} (or a patch of it)")]


def _code(schema: Any, keyword: str) -> str:
    c = schema.get("x-khg-code") if isinstance(schema, Mapping) else None
    if isinstance(c, str):
        return c
    if isinstance(c, Mapping):
        return c.get(keyword) or c.get("default") or "KHG-C010"
    return "KHG-C010"


def _pointer(parts: Any) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def _refuse(uri: str) -> Any:
    raise LookupError(f"closed resolver: {uri} is not packaged")


@functools.cache
def _runner() -> Callable[[Any], list[Finding]]:
    import jsonschema
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    doc = data.load_json(RECORD_SCHEMA)
    registry = Registry(retrieve=_refuse).with_resource(  # type: ignore[call-arg]
        RECORD_SCHEMA_ID, Resource.from_contents(doc, default_specification=DRAFT7))
    validator = jsonschema.Draft7Validator(doc, registry=registry)

    def run(instance: Any) -> list[Finding]:
        return [make_finding(_code(e.schema, str(e.validator)), _pointer(e.absolute_path), e.message)
                for e in validator.iter_errors(instance)]
    return run


def structure_findings(container: Any) -> list[Finding]:
    """Layer C on a container: the findings of the packaged record schema ([] when it is valid)."""
    return _runner()(container)
