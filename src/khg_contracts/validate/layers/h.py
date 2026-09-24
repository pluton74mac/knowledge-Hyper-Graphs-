"""Layer H: the vendored HIF schema ``hif_schema_v0.1.0.json``, unchanged (F2; DESIGN §4, §8.1).

It runs on the ``hif`` and ``role-convention`` kinds through either engine, with the closed resolvers of
``validate/engines.py``. The vendored schema carries no ``x-khg-code``, so the codes come from the H table
(``engines.h_code``, keyed on the keyword and the instance path): H001 no incidences, H002 an extra top-level key,
H003 an extra record-level key, H004 ``attrs`` or ``metadata`` not an object, H005 a direction outside head and
tail, H006 a record without ``edge`` or ``node``, H007 an id of the wrong JSON type, H008 a ``network-type`` outside
the HIF enum, H009 another member of the wrong type. Cases: the 15 H cases of ``malformed-cases.json``.
"""
from __future__ import annotations

from typing import Any

from .. import engines
from ..context import Context
from .d_decode import note

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "findings", "run"]

LETTER = "H"
OWNER = "W6"
IMPLEMENTED = True

Finding = dict[str, str]


def findings(doc: Any, *, engine: str = "jsonschema") -> list[Finding]:
    """The vendored HIF schema's findings on a document ([] when it is valid HIF 0.1)."""
    return engines.findings(engines.HIF_SCHEMA_ID, doc, engine=engine)


def run(ctx: Context) -> list[Finding]:
    if ctx.kind not in ("hif", "role-convention"):
        return []
    return note(ctx, LETTER, findings(ctx.doc, engine=ctx.engine))
