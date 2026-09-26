"""Layer Q: C3 queue files (DESIGN §7, §8.1).

In order, on the lines of a queue file:

- the structure and the state fold (``queue.fold.check``): Q008 a file whose line 1 is not its header (nothing else
  is checked then), V001 a header stamp this reader does not accept (layer V reports it first in a run, and the run
  stops there), a repeated header and ids used twice or not scoped by the queue; each line against the queue
  schema (Q001-Q005, Q008, Q010, and C codes for item entities); Q007 and Q005 the log against the fold;
- Q012 when the header names a base that ``bases`` does not supply with the header's ``record.container_sha256``
  (``Context.queue_base``);
- on each hyperedge item (``queue.checks.item_findings``): Q002 a candidate id of another queue, Q009, Q010 the item
  keys and event hashes against recomputation, Q011 an entity value that neither ``item.entities`` nor the verified
  base resolves; on each verdict entry, Q008 and Q010;
- Q006, when nothing above is an error: every ``accept`` re-run on a fresh reference store loaded with the base
  (``queue.replay.replay_accepts``), checking ``after`` and ``decision_hash``.

A C code this layer reports for an item's entities follows the recorded reading (``Context.recorded``, ``khg-queue``
1.1): an error that a rejected item's lint recorded is ``info``. The schema pin is layer D's (``d_container`` reports
D009), so this layer never reports it. It uses the caller's
schema without resolving it (the D009 of a missing schema is reported by the next step that asks), and it skips the
key checks and the replay when the header pins another schema, which D009 then explains. Layers C and S check the
payloads after this layer.
"""
from __future__ import annotations

from typing import Any, Mapping

from ...errors import make_finding
from ...queue.checks import item_findings, pin_findings, verdict_findings
from ...queue.fold import check
from ...queue.lines import errors
from ...queue.replay import replay_accepts
from ...record import container_sha256
from ...store import memory_factory
from ..context import Context

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "run"]

LETTER = "Q"
OWNER = "W9"
IMPLEMENTED = True

Finding = dict[str, str]


def _base_findings(ctx: Context, header: Mapping[str, Any], base: Mapping[str, Any] | None) -> list[Finding]:
    """Q012 when the header names a base and the run has no verified one."""
    pin = header.get("base")
    if not isinstance(pin, Mapping) or base is not None:
        return []  # no base named (a malformed one is the schema's Q008), or the verified base
    doc_id = pin.get("document_id")
    supplied = ctx.bases.get(doc_id) if isinstance(doc_id, str) else None
    if supplied is None:
        return [make_finding("KHG-Q012", "/lines/0/base", f"the header names the base {doc_id!r}; no base of that "
                                                          "document_id was supplied")]
    try:
        digest: str | None = container_sha256(supplied)
    except (ValueError, TypeError, KeyError):
        digest = None
    return [make_finding("KHG-Q012", "/lines/0/base", f"the base supplied as {doc_id!r} hashes to {digest}, not to "
                                                      f"the header's {pin.get('sha256')!r}")]


def _base_entity_ids(base: Mapping[str, Any] | None) -> set[str]:
    records = base.get("records") if isinstance(base, Mapping) else None
    return {r["id"] for r in records if isinstance(r, Mapping) and r.get("kind") == "entity"
            and isinstance(r.get("id"), str)} if isinstance(records, list) else set()


def run(ctx: Context) -> list[Finding]:
    if ctx.kind != "queue":
        return []
    lines = ctx.doc if isinstance(ctx.doc, list) else []
    fold, out = check(lines, engine=ctx.engine)
    out = ctx.recorded(out)
    if fold.header is None:
        return out
    schema = ctx.schema
    pinned = schema if schema is not None and not pin_findings(fold.header, schema) else None
    base = ctx.queue_base()
    out += _base_findings(ctx, fold.header, base)
    entities = _base_entity_ids(base)
    for n, line in enumerate(lines):
        if not isinstance(line, Mapping):
            continue
        if line.get("kind") == "queue-item" and line.get("item_kind") == "hyperedge":
            out += item_findings(line, queue_id=fold.queue_id, schema=pinned, entities=entities, path=f"/lines/{n}")
        elif line.get("kind") == "log-entry" and line.get("action") == "verdict" and \
                isinstance(line.get("target"), str) and line["target"] in fold.items:
            out += verdict_findings(line, fold.items[line["target"]], schema=pinned, path=f"/lines/{n}")
    if pinned is not None and not errors(out):
        out += replay_accepts(fold, pinned, memory_factory, base)[1]
    return out
