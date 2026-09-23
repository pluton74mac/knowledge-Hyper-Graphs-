"""Layer D, first pass of a HIF run: decoding the file into C1 (DESIGN §4.3, §8.1).

TODO(W6): a stub that returns no findings until W6 fills it; then set ``IMPLEMENTED = True``.

The prototype (``khg_validate_proto._decode``) decodes with ``hif_to_c1`` and reports what decoding refuses: D001
(a duplicate node or edge), D002 (an undeclared node or fact reference), D003 (an undeclared edge), D005 (a derived
id that does not match), D009 (the schema pin, or no schema), P016, P017, P010 and S016 (a direction that
contradicts the usage, emitted while decoding). On success it sets ``ctx.state["c1"]`` to the decoded container;
layers C, S and ``d_container`` then check it. The schema for decoding is ``ctx.relation_schema()``: the caller's,
else ``metadata["khg-schema-document"]``, else D009. Cases: the 8 decoding D cases and MC063.
"""
from __future__ import annotations

from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "run"]

LETTER = "D"
OWNER = "W6"
IMPLEMENTED = False  # TODO(W6)


def run(ctx: Context) -> list[dict[str, str]]:
    """TODO(W6): decode the HIF file and set ``ctx.state["c1"]``. The stub reports nothing and decodes nothing."""
    return []
