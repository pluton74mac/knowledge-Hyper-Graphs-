"""The C3 candidate queue and action log ``khg-queue/1.0.0`` (DESIGN §7).

A queue file is append-only JSONL, one per (run, order): line 1 is the ``queue-header`` (the schema pin and the
optional ``base`` container), then ``queue-item`` and ``log-entry`` lines. An item's state is a fold over its log;
items are never edited. Ids are scoped by the queue: ``q:``, ``l:`` and ``cand:<queue_id>.<seq>``.

- ``Queue.create(path, *, queue_id, schema, base=None, created_at=None)``, ``Queue.open(path, *, schema,
  base=None)``; ``submit``, ``accept``, ``reject``, ``flag``, ``verdict``, ``withdraw``;
- ``make_candidate(record, *, queue_id, seq, schema)``;
- ``Linter(schema, *, store=None, entities=None, doc_texts=None).lint(queue, qid, *, at=None)``: the structural
  rule set;
- ``replay(path, *, schema, factory, base=None) -> dict``: the accepts re-run on a fresh store, ``decision_hash``
  checked (Q006);
- ``queue_items(paths)``: the items with their folded state and verdicts, for the scorers.

Layer Q of the validator (``validate_queue``) uses the same fold and checks; the queue schema is the packaged
``khg-queue-1.0.0.schema.json`` (``queue.codegen`` generates it).
"""
from __future__ import annotations

from .candidate import make_candidate
from .handle import Queue
from .items import queue_items
from .linter import Linter
from .model import FORMAT
from .replay import replay

__all__ = ["FORMAT", "Linter", "Queue", "make_candidate", "queue_items", "replay"]
