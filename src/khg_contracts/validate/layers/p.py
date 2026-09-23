"""Layer P: the ``khg-hif/1.0.0`` profile (DESIGN §4.2-§4.6, §8.1).

It runs on the ``hif`` kind:

1. ``khg-hif-1.0.0.schema.json`` through either engine. The profile schema ``allOf``s the vendored schema by its
   ``$id``, whose own violations are layer H's, so the H findings are dropped here. The schema covers the
   declaration block (P001, P008, P009), the id types and grammar (P002, P003), ``asc`` (P007), the edge ``attrs``
   (P012), the node kinds and payloads (P013) and the incidence ``attrs`` (P005, P014).
2. The Python checks (``hif.profile_findings``): P004 reserved ``_:`` prefixes, P017 external fact references,
   P010 and P011 the direction rule, P016 a repeated ``khg-bid`` in one edge.

A file without ``khg-profile`` passes V and is P001 here. Cases: the 24 P cases.
"""
from __future__ import annotations

from typing import Any

from ...hif import profile_findings
from .. import engines
from ..context import Context
from .d_decode import note

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "findings", "run"]

LETTER = "P"
OWNER = "W6"
IMPLEMENTED = True

Finding = dict[str, str]


def findings(doc: Any, *, engine: str = "jsonschema") -> list[Finding]:
    """The profile's findings on a document: the profile schema's (without layer H's), then the Python checks."""
    found = [f for f in engines.findings(engines.PROFILE_SCHEMA_ID, doc, engine=engine) if f["layer"] != "H"]
    return found + profile_findings(doc)


def run(ctx: Context) -> list[Finding]:
    if ctx.kind != "hif":
        return []
    return note(ctx, LETTER, findings(ctx.doc, engine=ctx.engine))
