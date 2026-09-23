"""Layer R: ``role-convention`` 1.0.0, rules 1-4 (DESIGN §4.1, §8.1).

TODO(W6): a stub that returns no findings until W6 fills it; then set ``IMPLEMENTED = True``.

The prototype (``khg_validate_proto._r``) checks, for the ``hif`` and ``role-convention`` kinds: R003 the
``metadata["role-convention"]`` declaration (``"1.0.0"``); R001 every incidence of a role-carrying edge has one
non-empty string ``attrs.role``; R002 no exact repeat of (edge, node, role, role-position); R004 a
``role-position`` is an integer >= 1. Cases: the 6 R cases and the five ``data/role-convention/`` files.
"""
from __future__ import annotations

from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "run"]

LETTER = "R"
OWNER = "W6"
IMPLEMENTED = False  # TODO(W6)


def run(ctx: Context) -> list[dict[str, str]]:
    """TODO(W6): the four rules of role-convention 1.0.0. The stub reports nothing."""
    return []
