"""W9: the public names and signatures of ``khg_contracts.queue`` (DESIGN §7, §10.2)."""
from __future__ import annotations

import inspect

import khg_contracts
from khg_contracts import queue
from khg_contracts.queue import Linter, Queue, make_candidate, queue_items, replay


def _params(fn):
    """``[(name, kind, default)]`` of a callable, without ``self`` and ``cls``."""
    return [(p.name, p.kind.name, p.default) for p in inspect.signature(fn).parameters.values()
            if p.name not in ("self", "cls")]


EMPTY = inspect.Parameter.empty
KW, POS = "KEYWORD_ONLY", "POSITIONAL_OR_KEYWORD"


def test_the_names_of_section_10_2():
    assert set(queue.__all__) == {"FORMAT", "Linter", "Queue", "make_candidate", "queue_items", "replay"}
    assert queue.FORMAT == "khg-queue/1.0.0" == "khg-queue/" + khg_contracts.CONTRACTS["khg-queue"]
    assert khg_contracts.queue is queue


def test_the_signatures_of_section_7():
    assert _params(Queue.create) == [("path", POS, EMPTY), ("queue_id", KW, EMPTY), ("schema", KW, EMPTY),
                                     ("base", KW, None), ("created_at", KW, None)]
    assert _params(Queue.open) == [("path", POS, EMPTY), ("schema", KW, EMPTY), ("base", KW, None)]
    assert _params(Queue.submit) == [("payload", POS, EMPTY), ("run", KW, EMPTY), ("doc", KW, EMPTY),
                                     ("submitted_by", KW, EMPTY), ("entities", KW, ()), ("at", KW, None)]
    assert _params(Queue.accept) == [("qid", POS, EMPTY), ("store", KW, EMPTY), ("id", KW, EMPTY),
                                     ("actor", KW, EMPTY), ("reason", KW, EMPTY), ("at", KW, None)]
    for decide in (Queue.reject, Queue.flag, Queue.withdraw):
        assert _params(decide) == [("qid", POS, EMPTY), ("actor", KW, EMPTY), ("reason", KW, EMPTY),
                                   ("at", KW, None)]
    assert _params(Queue.verdict) == [("qid", POS, EMPTY), ("actor", KW, EMPTY), ("verdict", KW, EMPTY),
                                      ("at", KW, None)]
    assert _params(make_candidate) == [("record", POS, EMPTY), ("queue_id", KW, EMPTY), ("seq", KW, EMPTY),
                                       ("schema", KW, EMPTY)]
    assert _params(Linter) == [("schema", POS, EMPTY), ("store", KW, None), ("entities", KW, None),
                               ("doc_texts", KW, None)]
    assert _params(Linter.lint) == [("queue", POS, EMPTY), ("qid", POS, EMPTY), ("at", KW, None)]
    assert _params(replay) == [("path", POS, EMPTY), ("schema", KW, EMPTY), ("factory", KW, EMPTY),
                               ("base", KW, None)]
    assert _params(queue_items) == [("paths", POS, EMPTY)]
