"""The state fold over a queue's lines (DESIGN §7), and the structural checks that layer Q, ``Queue.open``,
``replay`` and ``queue_items`` share.

An item's state is a fold over its log entries; items are never edited (F9). ``check`` runs, line by line, the queue
schema and ``Fold.feed``, which reports:

- Q008 a file whose line 1 is not its ``queue-header`` (nothing else is checked then), a repeated header, a qid or
  lid used twice, and an id that is well formed but not scoped by the queue (``q:``/``l:<queue_id>.<seq>``);
- Q007 an entry whose target is not an item of the queue, or whose ``parent`` is not the item's previous entry (the
  entry is then left out of the fold);
- Q005 an entry whose ``state_before`` is not the item's state, a move the table forbids, or an ``accept`` while
  the item's lint recorded an error finding (the entry is folded, the state is unchanged).

An item of an unknown kind, an entry with an unknown action and a line of an unknown kind stay out of the fold: the
schema reports them (Q003), and the entries of such an item are Q007.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..errors import make_finding
from .lines import line_findings
from .model import ACTIONS, ITEM_KINDS, LID_PATTERN, MOVES, QID_PATTERN, QUEUE_ID_PATTERN, STATES, seq_of

__all__ = ["Fold", "check"]

Finding = dict[str, str]


def _f(code: str, path: str, message: str) -> Finding:
    return make_finding(code, path, message)


@dataclass
class Fold:
    """The folded state of a queue: its header, its hyperedge items by qid (in file order) with their line, state,
    last entry and entries, and the verdict and accept entries in log order."""

    header: dict[str, Any] | None = None
    items: dict[str, dict[str, Any]] = field(default_factory=dict)
    item_line: dict[str, int] = field(default_factory=dict)
    state: dict[str, str] = field(default_factory=dict)
    last: dict[str, Any] = field(default_factory=dict)
    entries: dict[str, list[int]] = field(default_factory=dict)
    lint_errors: dict[str, bool] = field(default_factory=dict)
    lids: dict[str, int] = field(default_factory=dict)
    verdicts: list[tuple[int, dict[str, Any]]] = field(default_factory=list)
    accepts: list[tuple[int, dict[str, Any]]] = field(default_factory=list)
    item_seq: int = 0
    entry_seq: int = 0
    lines: int = 0

    @property
    def queue_id(self) -> str | None:
        """The header's ``queue_id`` when it is a valid queue id (the schema reports any other)."""
        qid = self.header.get("queue_id") if self.header is not None else None
        return qid if isinstance(qid, str) and re.fullmatch(QUEUE_ID_PATTERN, qid) else None

    # ------------------------------------------------------------------------------------------ feeding

    def feed(self, line: Any, n: int) -> list[Finding]:
        """Fold line ``n`` into the state; the Q005, Q007 and Q008 findings of the fold (the schema's are
        ``line_findings``)."""
        self.lines = max(self.lines, n + 1)
        if not isinstance(line, Mapping):
            return []
        kind = line.get("kind")
        if kind == "queue-header":
            if n == 0 and self.header is None:
                self.header = dict(line)
                return []
            return [_f("KHG-Q008", f"/lines/{n}", "the queue-header line is repeated")]
        if kind == "queue-item":
            found, register = self._judge_item(line, n)
            if register:
                self._register(line, n)
            return found
        if kind == "log-entry":
            found, how = self.judge_entry(line, n)
            if how != "skip":
                self._apply(line, n, moved=how == "move")
            return found
        return []

    def _out_of_scope(self, value: str, prefix: str, pattern: str) -> bool:
        """True when ``value`` is a well-formed id (the schema reports any other) not scoped by this queue; never
        without a valid ``queue_id`` (the schema reports the header then)."""
        return self.queue_id is not None and seq_of(value, prefix, self.queue_id) is None and \
            re.fullmatch(pattern, value) is not None

    def _judge_item(self, line: Mapping[str, Any], n: int) -> tuple[list[Finding], bool]:
        qid = line.get("qid")
        if line.get("item_kind") not in ITEM_KINDS or not isinstance(qid, str):
            return [], False
        if qid in self.items:
            return [_f("KHG-Q008", f"/lines/{n}/qid", f"qid {qid} is used twice (line {self.item_line[qid]})")], False
        if self._out_of_scope(qid, "q", QID_PATTERN):
            return [_f("KHG-Q008", f"/lines/{n}/qid", f"{qid} is not q:{self.queue_id}.<seq>")], True
        return [], True

    def _register(self, line: Mapping[str, Any], n: int) -> None:
        qid = line["qid"]
        self.items[qid] = dict(line)
        self.item_line[qid] = n
        self.state[qid] = "pending"
        self.last[qid] = None
        self.entries[qid] = []
        self.lint_errors[qid] = False
        self.item_seq = max(self.item_seq, seq_of(qid, "q", self.queue_id) or 0)

    def judge_entry(self, line: Mapping[str, Any], n: int) -> tuple[list[Finding], str]:
        """What folding a log entry reports, without changing the fold, and how it folds: ``skip`` (left out),
        ``hold`` (folded, the state unchanged) or ``move``."""
        p = f"/lines/{n}"
        action = line.get("action")
        if action not in ACTIONS:
            return [], "skip"
        out: list[Finding] = []
        entry_id = line.get("lid")
        if isinstance(entry_id, str):
            if entry_id in self.lids:
                twice = f"lid {entry_id} is used twice (line {self.lids[entry_id]})"
                return [_f("KHG-Q008", f"{p}/lid", twice)], "skip"
            if self._out_of_scope(entry_id, "l", LID_PATTERN):
                out.append(_f("KHG-Q008", f"{p}/lid", f"{entry_id} is not l:{self.queue_id}.<seq>"))
        target = line.get("target")
        if not isinstance(target, str) or target not in self.items:
            return out + [_f("KHG-Q007", f"{p}/target", f"{target!r} is not an item of this queue")], "skip"
        if line.get("parent") != self.last[target]:
            return out + [_f("KHG-Q007", f"{p}/parent", f"the parent of an entry is the item's previous entry "
                                                       f"({self.last[target]!r}), not {line.get('parent')!r}")], "skip"
        before, after, current = line.get("state_before"), line.get("state_after"), self.state[target]
        if before not in STATES or after not in STATES:
            return out, "hold"  # the schema reports an unknown state (Q005)
        if before != current or after not in MOVES[action].get(current, ()):
            out.append(_f("KHG-Q005", p, f"{action} {before} -> {after} does not follow the fold: {target} is "
                                         f"{current}"))
            return out, "hold"
        if action == "accept" and self.lint_errors[target]:
            out.append(_f("KHG-Q005", p, f"{target} is accepted while its lint has an open error finding"))
            return out, "hold"
        return out, "move"

    def _apply(self, line: Mapping[str, Any], n: int, *, moved: bool) -> None:
        target, entry_id, action = line["target"], line.get("lid"), line["action"]
        if isinstance(entry_id, str):
            self.lids[entry_id] = n
            self.entry_seq = max(self.entry_seq, seq_of(entry_id, "l", self.queue_id) or 0)
        self.last[target] = entry_id
        if not moved:
            return
        self.state[target] = line["state_after"]
        self.entries[target].append(n)
        if action == "lint":
            found = line.get("findings")
            self.lint_errors[target] = isinstance(found, list) and any(
                isinstance(f, Mapping) and f.get("severity") == "error" for f in found)
        elif action == "verdict":
            self.verdicts.append((n, dict(line)))
        elif action == "accept":
            self.accepts.append((n, dict(line)))


def check(lines: list[Any], *, engine: str = "jsonschema") -> tuple[Fold, list[Finding]]:
    """The fold of a queue's lines and its structural findings: Q008 when line 1 is not the header (and nothing
    else), else each line against the queue schema followed by the fold's findings, line by line."""
    fold = Fold()
    if not lines or not isinstance(lines[0], Mapping) or lines[0].get("kind") != "queue-header":
        return fold, [_f("KHG-Q008", "/lines/0", "a queue file starts with its queue-header line")]
    out: list[Finding] = []
    for n, line in enumerate(lines):
        out += line_findings(line, engine=engine, path=f"/lines/{n}")
        out += fold.feed(line, n)
    return fold, out
