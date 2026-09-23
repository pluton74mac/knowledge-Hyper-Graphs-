"""Layer I: C4 items ``khg-c4-items/0.1.0`` (DESIGN §9.6, §8.1).

TODO(W11a): a stub that returns no findings until W11a fills it; then set ``IMPLEMENTED = True``.

The prototype (``khg_validate_proto._i``) runs ``engines.findings(engines.C4_SCHEMA_ID, line, engine=ctx.engine)``
on every line (I001 an unknown kind, I002 the draft schema, I004 the mandatory ``stale_values`` and
``future_values``), then checks the embedded C1 records with ``layers.s.record_findings`` (and
``layers.c.record_findings``), reporting each error nested under I003, and replays memory questions against
``derive_memory_gold`` (I005). The relation-type schema is ``ctx.relation_schema()``. Cases: the 5 I cases.
"""
from __future__ import annotations

from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "run"]

LETTER = "I"
OWNER = "W11a"
IMPLEMENTED = False  # TODO(W11a)


def run(ctx: Context) -> list[dict[str, str]]:
    """TODO(W11a): the C4 item schema, embedded C1 (nested under I003) and memory gold. The stub reports
    nothing."""
    return []
