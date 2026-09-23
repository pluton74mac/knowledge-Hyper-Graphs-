"""Layer Q: C3 queue files (DESIGN §7, §8.1).

TODO(W9): a stub that returns no findings until W9 fills it; then set ``IMPLEMENTED = True``.

The prototype (``khg_validate_proto._q`` and ``_replay``) checks the queue structure (Q008 the header line, Q003
line kinds, item kinds and actions, Q001 extraction fields, Q002 the payload's status and id, Q004 lint entries),
Q009 the evidence's document, Q010 the item keys and event hashes, Q011 entity resolution, Q012 the base (the
verified base is ``ctx.queue_base()``), Q007 and Q005 the log and the state fold, and Q006 the replay of every
``accept``. Layers C and S already run on the payloads. Cases: the 17 Q cases.
"""
from __future__ import annotations

from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "run"]

LETTER = "Q"
OWNER = "W9"
IMPLEMENTED = False  # TODO(W9)


def run(ctx: Context) -> list[dict[str, str]]:
    """TODO(W9): the queue structure, the fold, keys, entity resolution, the base and replay. The stub reports
    nothing."""
    return []
