"""Layer D, first pass of a HIF run: decoding the file into C1 (DESIGN §4.3, §8.1).

Decoding reads only a file that passed layers H, R and P. Those layers record their outcome in
``ctx.state["hif_layers"]`` (letter -> True when the layer reported no error) through ``note``; a layer that did not
run in this run (a ``steps`` subset) is checked here without reporting. After an H, R or P error nothing is
decoded and this step reports nothing, since those layers already rejected the file.

The schema is ``ctx.relation_schema()``: the caller's, else ``metadata["khg-schema-document"]`` (its V and M
findings are reported at its path), else D009. ``hif.decode`` then reports D001 (a node or edge declared twice),
D002 (an undeclared node, an unresolved fact reference), D003 (an undeclared edge), D005 (a derived id that does not
match), D009 (the schema pin), P010, P016 and P017, and S001, S002 and S016 (another layer's codes, emitted while
decoding, §8.1). When decoding finds no error, ``ctx.state["c1"]`` is the decoded container, as written (so layer S
still sees strings that are not NFC); layers C, S and ``d_container`` then check it. Cases: the 8 decoding D cases
and MC063.
"""
from __future__ import annotations

from typing import Any, Mapping

from ...hif import decode
from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "STATE_KEY", "note", "run"]

LETTER = "D"
OWNER = "W6"
IMPLEMENTED = True

#: ``ctx.state`` key: HIF layer letter (H, R, P) -> True when that layer reported no error in this run.
STATE_KEY = "hif_layers"

Finding = dict[str, str]


def _errors(findings: list[Finding]) -> bool:
    return any(f["severity"] == "error" for f in findings)


def note(ctx: Context, letter: str, findings: list[Finding]) -> list[Finding]:
    """Record whether HIF layer ``letter`` reported an error in this run; returns ``findings``."""
    ctx.state.setdefault(STATE_KEY, {})[letter] = not _errors(findings)
    return findings


def _passed(ctx: Context) -> bool:
    """True when layers H, R and P accept the file: from this run's record, else checked here."""
    from . import h, p, r

    recorded = ctx.state.get(STATE_KEY, {})
    for letter, check in (("H", h.findings), ("R", r.findings), ("P", p.findings)):
        ok: Any = recorded.get(letter)
        if ok is None:
            ok = not _errors(check(ctx.doc, engine=ctx.engine))
        if not ok:
            return False
    return True


def run(ctx: Context) -> list[Finding]:
    """Decode a HIF file that passed H, R and P; set ``ctx.state["c1"]`` when decoding finds no error."""
    if ctx.kind != "hif" or not isinstance(ctx.doc, Mapping) or not _passed(ctx):
        return []
    schema, out = ctx.relation_schema()
    if schema is None:
        return out
    container, found = decode(ctx.doc, schema)
    out = out + found
    if container is not None and not _errors(out):
        ctx.state["c1"] = container
    return out
