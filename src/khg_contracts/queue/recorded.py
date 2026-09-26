"""The recorded reading of queue validity (DESIGN §7, §8.1; ``khg-queue`` 1.1.0, ruling 23, from P9's D5 a).

A queue records wrong candidates on purpose, and its items are never edited (F9). ``validate_queue`` runs layers C
and S on every payload, so under 1.0 a queue that once rejected a malformed candidate never validated again. Under
1.1, a finding of layer C or S (by its code) on an item line is **recorded** when:

- the item's folded state is ``rejected``, and
- one of its lint entries lists a finding with the same code, at the same path relative to the item line
  (``/payload/...``, ``/entities/...``), with severity ``error``.

``lower`` reports a recorded finding with severity ``info`` and a message naming the lint entry, so it does not make
the queue invalid; every other finding keeps its severity: an error the lint did not record, one on an item that is
not rejected, and every J, V, Q and D finding. The fold never lets an item with a recorded lint error be accepted
(Q005), so a recorded error never reached a store.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .fold import Fold

__all__ = ["LETTERS", "RecordedMap", "lower", "recorded_map"]

#: The layers whose findings a lint entry can record for the validator (the payload's C and S codes).
LETTERS = ("C", "S")
#: Item line -> {(code, path relative to the item): the line of the lint entry that recorded it}.
RecordedMap = dict[int, dict[tuple[str, str], int]]
_ITEM_PATH = re.compile(r"/lines/([0-9]+)(/.*)")


def recorded_map(lines: Sequence[Any]) -> RecordedMap:
    """The error findings each rejected item's lint entries recorded, by item line (see the module docstring). The
    fold is the one layer Q checks; a file whose line 1 is not its header records nothing."""
    if not lines or not isinstance(lines[0], Mapping) or lines[0].get("kind") != "queue-header":
        return {}
    fold = Fold()
    for n, line in enumerate(lines):
        fold.feed(line, n)
    out: RecordedMap = {}
    for qid, state in fold.state.items():
        if state != "rejected":
            continue
        found: dict[tuple[str, str], int] = {}
        for k in fold.entries[qid]:  # the entries the fold applied, in log order
            entry = lines[k]
            if entry.get("action") != "lint" or not isinstance(entry.get("findings"), list):
                continue
            for f in entry["findings"]:
                if isinstance(f, Mapping) and f.get("severity") == "error" and isinstance(f.get("code"), str) \
                        and isinstance(f.get("path"), str):
                    found.setdefault((f["code"], f["path"]), k)
        if found:
            out[fold.item_line[qid]] = found
    return out


def lower(findings: list[dict[str, Any]], recorded: RecordedMap) -> list[dict[str, Any]]:
    """``findings`` with each recorded one lowered to ``info`` (in place, and returned)."""
    if not recorded:
        return findings
    for f in findings:
        if f.get("severity") != "error" or str(f.get("code", ""))[4:5] not in LETTERS:
            continue
        m = _ITEM_PATH.fullmatch(f.get("path", ""))
        k = recorded.get(int(m.group(1)), {}).get((f["code"], m.group(2))) if m else None
        if k is not None:
            f["severity"] = "info"
            f["message"] = f"recorded by the lint entry at /lines/{k} of this rejected item: {f['message']}"
    return findings
