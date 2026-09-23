"""Shared data for the queue tests (W9): the fixture schema, the smoke base and queue, the fixture's ``f:king-14``,
and ``Smoke``, which builds the G3 smoke queue through the API (DESIGN §1.2 G3, §7)."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import data
from khg_contracts.queue import Linter, Queue, make_candidate
from khg_contracts.schema import Schema, load_schema
from khg_contracts.store import MemoryStore, ScenarioClock

#: The smoke item's extraction fields and times, and the accept's reason (``build_examples.py``).
RUN = {"run_id": "fixture-run-1", "order_id": "o1", "position": 0, "seed": 0, "temperature": 0}
DOC = {"doc_id": "doc:louis-bio",
       "doc_sha256": "sha256:56940b729460cb9a75d5d63ab1f907a502fef80530b4aabff2cd8e9c28a44b2f"}
SUBMITTED_BY = "p2-fixture-extractor/0.0.1"
REASON = "the regnal list and the biography sentence support every binding"
TIMES = {"created": "2026-10-01T00:00:00Z", "submitted": "2026-10-01T00:00:03Z", "lint": "2026-10-01T00:00:05Z",
         "accept": "2026-10-01T00:00:07Z"}
DECISION_HASH = "sha256:518db0f4a88cffe427846b412c99d755945c35816fc3c5e83d31c2ea30807f29"
SMOKE_QUEUE = "fixture/smoke-queue.khg-queue.jsonl"


@pytest.fixture(scope="session")
def schema() -> Schema:
    return load_schema(data.load_json("fixture/fixture.relation-schema.json"))


@pytest.fixture()
def base() -> dict[str, Any]:
    """``smoke-base.c1.json``: the fixture's entities, G3's base."""
    return data.load_json("fixture/smoke-base.c1.json")


@pytest.fixture()
def king14() -> dict[str, Any]:
    """The fixture's ``f:king-14`` (asserted, with its stored event hash)."""
    return copy.deepcopy(next(r for r in data.load_json("fixture/fixture.c1.json")["records"]
                              if r["id"] == "f:king-14"))


@pytest.fixture()
def smoke_lines() -> list[dict[str, Any]]:
    """The four lines of the committed smoke queue."""
    return data.load_jsonl(SMOKE_QUEUE)


@pytest.fixture()
def store(schema, base) -> MemoryStore:
    """A reference store on the scenario clock (2026-10-01T00:00:00Z), loaded with the smoke base."""
    s = MemoryStore(schema, clock=ScenarioClock())
    s.load(base)
    return s


class Smoke:
    """Builds queues in a temporary directory: the G3 smoke queue step by step, and small variants. The smoke
    item's constants are attributes, since test modules cannot import this file."""

    RUN, DOC, SUBMITTED_BY, REASON, TIMES, DECISION_HASH = RUN, DOC, SUBMITTED_BY, REASON, TIMES, DECISION_HASH

    def __init__(self, tmp_path: Path, schema: Schema, base: dict[str, Any], king14: dict[str, Any]) -> None:
        self.dir = tmp_path
        self.schema = schema
        self.base = base
        self.king14 = king14
        self._n = 0

    def path(self, name: str | None = None) -> Path:
        self._n += 1
        return self.dir / (name or f"q{self._n}.khg-queue.jsonl")

    def create(self, *, queue_id: str = "p2-smoke", base: Any = "smoke", path: Path | None = None) -> Queue:
        return Queue.create(path or self.path(), queue_id=queue_id, schema=self.schema,
                            base=self.base if base == "smoke" else base, created_at=TIMES["created"])

    def candidate(self, queue: Queue, seq: int = 1, record: dict[str, Any] | None = None) -> dict[str, Any]:
        return make_candidate(record or self.king14, queue_id=queue.queue_id, seq=seq, schema=self.schema)

    def submit(self, queue: Queue, payload: dict[str, Any] | None = None, **kw: Any) -> str:
        kw.setdefault("run", RUN)
        kw.setdefault("doc", DOC)
        kw.setdefault("submitted_by", SUBMITTED_BY)
        kw.setdefault("at", TIMES["submitted"])
        return queue.submit(payload if payload is not None else self.candidate(queue), **kw)

    def lint(self, queue: Queue, qid: str, **kw: Any) -> dict[str, Any]:
        return Linter(self.schema, **kw).lint(queue, qid, at=TIMES["lint"])

    def accept(self, queue: Queue, qid: str, store: Any, **kw: Any) -> dict[str, Any]:
        kw.setdefault("id", "f:king-14")
        kw.setdefault("actor", "curator:smoke")
        kw.setdefault("reason", REASON)
        kw.setdefault("at", TIMES["accept"])
        return queue.accept(qid, store=store, **kw)

    def full(self, store: Any) -> tuple[Queue, str, dict[str, Any], dict[str, Any]]:
        """The G3 queue: create, submit, lint, accept; returns ``(queue, qid, lint entry, accept entry)``."""
        q = self.create()
        qid = self.submit(q)
        lint = self.lint(q, qid)
        return q, qid, lint, self.accept(q, qid, store)


@pytest.fixture()
def smoke(tmp_path, schema, base, king14) -> Smoke:
    return Smoke(tmp_path, schema, base, king14)
