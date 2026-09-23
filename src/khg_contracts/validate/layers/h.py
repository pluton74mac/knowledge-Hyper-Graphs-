"""Layer H: the vendored HIF schema ``hif_schema_v0.1.0.json``, unchanged (F2; DESIGN §4, §8.1).

TODO(W6): a stub that returns no findings until W6 fills it; then set ``IMPLEMENTED = True``.

The prototype (``khg_validate_proto._h``) runs ``engines.findings(engines.HIF_SCHEMA_ID, ctx.doc,
engine=ctx.engine)`` for the ``hif`` and ``role-convention`` kinds. The vendored schema carries no ``x-khg-code``,
so the codes come from the H table (``engines.h_code``, keyed on the keyword and the instance path). Cases: the 15
H cases of ``malformed-cases.json``.
"""
from __future__ import annotations

from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "run"]

LETTER = "H"
OWNER = "W6"
IMPLEMENTED = False  # TODO(W6)


def run(ctx: Context) -> list[dict[str, str]]:
    """TODO(W6): the vendored HIF schema. The stub reports nothing."""
    return []
