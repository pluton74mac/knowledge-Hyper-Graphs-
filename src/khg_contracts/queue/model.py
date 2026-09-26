"""The vocabulary of the C3 queue ``khg-queue/1.1.0`` (DESIGN §7): line kinds, states and moves, actions, verdict
labels and the queue-scoped ids ``q:``, ``l:`` and ``cand:<queue_id>.<seq>``.

1.1 (ruling 23) changes no line of the format, so queue files keep the stamp ``khg-queue/1.0.0`` (``FORMAT``, the
lowest version whose features they use, §11.2) and a 1.0 reader reads them. It changes how a queue is judged (the
recorded reading, ``queue.recorded``) and what the linter checks: ``khg-lint`` 1.1.0 runs the structural rule set
1.1.0, which adds Q013 (``queue.checks.quote_findings``).

The fold's moves: ``pending`` goes to ``linted``, ``needs_review`` or ``rejected``; ``linted`` to ``accepted``,
``rejected`` or ``needs_review``; ``needs_review`` to ``accepted`` or ``rejected``; any open state to ``withdrawn``;
a ``verdict`` leaves the state unchanged (the prototype refuses one on a withdrawn item).
"""
from __future__ import annotations

import re
from types import MappingProxyType
from typing import Any, Dict, Mapping

__all__ = [
    "ACTIONS",
    "ACTOR_TYPES",
    "CAND_PATTERN",
    "FORMAT",
    "ITEM_KINDS",
    "LABELS",
    "LID_PATTERN",
    "LINE_KINDS",
    "LINTER",
    "LINT_STATES",
    "LogEntry",
    "MODES",
    "MOVES",
    "OPEN_STATES",
    "OUTCOMES",
    "QID_PATTERN",
    "QUEUE_ID_PATTERN",
    "REASON_ACTIONS",
    "RECORD_FORMAT",
    "RULE_SET",
    "SCHEMA_FILE",
    "SCHEMA_ID",
    "SEVERITIES",
    "SHA256_PATTERN",
    "STATES",
    "SUBMITTED_BY_PATTERN",
    "TIMESTAMP_PATTERN",
    "cand_id",
    "check_queue_id",
    "lid",
    "qid",
    "seq_of",
]

#: A log entry as a queue line holds it (what ``Queue.accept``, ``reject``, ``flag``, ``verdict``, ``withdraw`` and
#: ``Linter.lint`` return).
LogEntry = Dict[str, Any]

#: The stamp queue files are written with (no 1.1 feature is a line of the file); the reader takes 1.0.x and 1.1.x.
FORMAT = "khg-queue/1.0.0"
RECORD_FORMAT = "khg-record/1.0.0"
SCHEMA_ID = "tag:khg-contracts,2026:schema/khg-queue/1.0.0"
#: The packaged file of the queue schema, under ``khg_contracts/data``.
SCHEMA_FILE = "schemas/khg-queue-1.0.0.schema.json"

LINE_KINDS = ("queue-header", "queue-item", "log-entry")
#: v1 item kinds; the proposal kinds come in 1.1 (Q003).
ITEM_KINDS = ("hyperedge",)
STATES = ("pending", "linted", "needs_review", "accepted", "rejected", "withdrawn")
OPEN_STATES = ("pending", "linted", "needs_review")
#: v1 log actions; ``merge`` and ``auto_fix`` come in 1.1 (Q003).
ACTIONS = ("lint", "accept", "reject", "flag", "verdict", "withdraw")
#: action -> {state_before: allowed states_after}.
MOVES: Mapping[str, Mapping[str, tuple[str, ...]]] = MappingProxyType({
    "lint": MappingProxyType({"pending": ("linted", "needs_review", "rejected")}),
    "accept": MappingProxyType({"linted": ("accepted",), "needs_review": ("accepted",)}),
    "reject": MappingProxyType({s: ("rejected",) for s in OPEN_STATES}),
    "flag": MappingProxyType({"pending": ("needs_review",), "linted": ("needs_review",)}),
    "verdict": MappingProxyType({s: (s,) for s in ("pending", "linted", "needs_review", "accepted", "rejected")}),
    "withdraw": MappingProxyType({s: ("withdrawn",) for s in OPEN_STATES}),
})
OUTCOMES = ("pass", "warn", "fail")
#: The state a lint entry moves a pending item to, by outcome (what ``Linter.lint`` writes).
LINT_STATES: Mapping[str, str] = MappingProxyType({"pass": "linted", "warn": "needs_review", "fail": "rejected"})
#: The actions whose entries carry a ``reason``.
REASON_ACTIONS = ("accept", "reject", "flag", "withdraw")
ACTOR_TYPES = ("agent", "linter", "person", "system")
MODES = ("automatic", "manual", "semi_automatic")
SEVERITIES = ("error", "warning", "info")
#: Verdict labels (§7); they aggregate as in [DB §7.3] (``verdicts.aggregate``).
LABELS = ("correct", "no_relation", "wrong_relation", "wrong_role", "wrong_filler", "span_boundary",
          "missing_participant", "extra_participant", "negated", "hypothesis", "other")

#: The linter's actor and its rule set (the gate's structural lint); 1.1.0 adds Q013 (ruling 23).
LINTER: Mapping[str, str] = MappingProxyType({"type": "linter", "id": "khg-lint", "version": "1.1.0"})
RULE_SET: Mapping[str, str] = MappingProxyType({"id": "structural", "version": "1.1.0"})

_QUEUE_ID = r"[0-9A-Za-z][0-9A-Za-z._:-]{0,127}"
QUEUE_ID_PATTERN = rf"^{_QUEUE_ID}$"
QID_PATTERN = rf"^q:{_QUEUE_ID}\.[0-9]+$"
LID_PATTERN = rf"^l:{_QUEUE_ID}\.[0-9]+$"
CAND_PATTERN = rf"^cand:{_QUEUE_ID}\.[0-9]+$"
SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
TIMESTAMP_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$"
#: ``"<agent>/<version>"``.
SUBMITTED_BY_PATTERN = r"^[^\s]+/[^\s/]+$"


def check_queue_id(queue_id: object) -> str:
    """``queue_id`` when it is a valid queue id (ASCII letters, digits and ``._:-``, from a letter or digit, at
    most 128 characters); ``ValueError`` otherwise."""
    if not isinstance(queue_id, str) or not re.fullmatch(QUEUE_ID_PATTERN, queue_id):
        raise ValueError(f"a queue id matches {QUEUE_ID_PATTERN}, not {queue_id!r}")
    return queue_id


def _scoped(prefix: str, queue_id: str, seq: int) -> str:
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
        raise ValueError(f"a sequence number is a positive integer, not {seq!r}")
    return f"{prefix}:{check_queue_id(queue_id)}.{seq:06d}"


def qid(queue_id: str, seq: int) -> str:
    """``q:<queue_id>.<seq>``, the seq zero-padded to six digits."""
    return _scoped("q", queue_id, seq)


def lid(queue_id: str, seq: int) -> str:
    """``l:<queue_id>.<seq>``."""
    return _scoped("l", queue_id, seq)


def cand_id(queue_id: str, seq: int) -> str:
    """``cand:<queue_id>.<seq>``, a candidate payload's id."""
    return _scoped("cand", queue_id, seq)


def seq_of(value: object, prefix: str, queue_id: object) -> int | None:
    """The sequence number of ``value`` when it is ``<prefix>:<queue_id>.<digits>``; None otherwise."""
    if not isinstance(value, str) or not isinstance(queue_id, str):
        return None
    head = f"{prefix}:{queue_id}."
    rest = value[len(head):]
    if not value.startswith(head) or not rest.isascii() or not rest.isdigit():
        return None
    return int(rest)
