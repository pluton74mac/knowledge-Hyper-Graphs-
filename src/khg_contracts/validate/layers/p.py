"""Layer P: the ``khg-hif/1.0.0`` profile (DESIGN §4.2-§4.5, §8.1).

TODO(W6): a stub that returns no findings until W6 fills it; then set ``IMPLEMENTED = True``.

The prototype (``khg_validate_proto._p``) runs ``engines.findings(engines.PROFILE_SCHEMA_ID, ctx.doc,
engine=ctx.engine)`` and drops the findings of layer H (the profile ``allOf``s the vendored schema, whose own
violations layer H reports), then the Python profile checks: P004 reserved ``_:`` prefixes, P017 external fact
references, P010 and P011 the direction rule, P016 a repeated ``khg-bid`` in one edge. Cases: the 24 P cases.
"""
from __future__ import annotations

from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "run"]

LETTER = "P"
OWNER = "W6"
IMPLEMENTED = False  # TODO(W6)


def run(ctx: Context) -> list[dict[str, str]]:
    """TODO(W6): the profile schema and the Python profile checks. The stub reports nothing."""
    return []
