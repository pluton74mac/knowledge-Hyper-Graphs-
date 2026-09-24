"""Layer R: ``role-convention`` 1.0.0, rules 1-4 and nothing else (DESIGN §4.1, §8.1).

It runs on the ``hif`` and ``role-convention`` kinds (``hif.convention_findings``): R003 the
``metadata["role-convention"]`` declaration (``"1.0.0"``); R001 every incidence of a role-carrying edge has one
non-empty string ``attrs.role``; R004 a ``role-position`` is an integer >= 1; R002 no exact repeat of (edge, node,
role, role-position). Cases: the 6 R cases, and the five ``data/role-convention/`` files, which pass.
"""
from __future__ import annotations

from typing import Any

from ...hif import convention_findings
from ..context import Context
from .d_decode import note

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "findings", "run"]

LETTER = "R"
OWNER = "W6"
IMPLEMENTED = True

Finding = dict[str, str]


def findings(doc: Any, *, engine: str = "jsonschema") -> list[Finding]:
    """The R findings of a document (``engine`` is accepted for a uniform signature; R is Python only)."""
    return convention_findings(doc)


def run(ctx: Context) -> list[Finding]:
    if ctx.kind not in ("hif", "role-convention"):
        return []
    return note(ctx, LETTER, findings(ctx.doc))
