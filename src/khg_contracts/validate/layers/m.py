"""Layer M: relation-type schema documents (DESIGN §3, §8.1), wired to ``khg_contracts.schema``.

M has two parts, both from ``schema.checks``: the meta-schema ``khg-relation-schema-1.0.0.schema.json`` through the
run's engine (structure: M001, M004, M006, M007, M012, M014 and M015 by default), then the Python checks that need
the whole document (M002, M003, M005, M007-M013, M015-M017). Layers J and V ran before, so ``doc`` is an object
whose ``format`` is accepted.
"""
from __future__ import annotations

from ...schema.checks import meta_findings, python_findings
from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "run"]

LETTER = "M"
OWNER = "W4"
IMPLEMENTED = True


def run(ctx: Context) -> list[dict[str, str]]:
    if ctx.kind != "schema":
        return []
    return meta_findings(ctx.doc, engine=ctx.engine) + python_findings(ctx.doc)
