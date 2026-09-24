"""Layer C: the C1 record schema ``khg-record-1.0.0.schema.json`` (DESIGN §2, §8.1), through either engine.

| Kind | Checked |
|---|---|
| container | the container |
| record | the record against ``#/definitions/record`` |
| hif | the container that decoding produced (``state["c1"]``), when it did |
| queue | each ``queue-item`` payload against ``#/definitions/hyperedge``, at ``/lines/<n>/payload`` |

Codes come from the ``x-khg-code`` annotations (C001-C012). jsonschema reports every violation, fastjsonschema the
first one. ``record_findings`` is the entry point for one record, for the store, the queue linter and layer I.
"""
from __future__ import annotations

from typing import Any, Mapping

from .. import engines
from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "container_findings", "record_findings", "run"]

LETTER = "C"
OWNER = "W4"
IMPLEMENTED = True

Finding = dict[str, str]


def container_findings(container: Any, *, engine: str = "jsonschema", path: str = "") -> list[Finding]:
    """Layer C on a C1 container ([] when it is valid)."""
    return engines.findings(engines.RECORD_SCHEMA_ID, container, engine=engine, path=path)


def record_findings(record: Any, *, definition: str = "record", engine: str = "jsonschema",
                    path: str = "") -> list[Finding]:
    """Layer C on one record: ``definition`` is ``record`` (entity, hyperedge or embedded schema), ``hyperedge``
    or ``entity``; ``path`` prefixes the findings' paths."""
    return engines.findings(engines.RECORD_SCHEMA_ID, record, fragment=f"/definitions/{definition}", engine=engine,
                            path=path)


def run(ctx: Context) -> list[Finding]:
    if ctx.kind in ("container", "hif"):
        container = ctx.container
        return container_findings(container, engine=ctx.engine) if container is not None else []
    if ctx.kind == "record":
        return record_findings(ctx.doc, engine=ctx.engine)
    if ctx.kind == "queue":
        out: list[Finding] = []
        for n, line in enumerate(ctx.doc if isinstance(ctx.doc, list) else []):
            if isinstance(line, Mapping) and line.get("kind") == "queue-item":
                out += record_findings(line.get("payload"), definition="hyperedge", engine=ctx.engine,
                                       path=f"/lines/{n}/payload")
        return out
    return []
