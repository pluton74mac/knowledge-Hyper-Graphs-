"""Shared fixtures of the scorer tests (DESIGN §9.7).

``r05.relation-schema.json`` maps R05's abstract tables to C1: relation ``r`` has A and B in the core slot, C, D, E
and Q in the qualifier slot and the key {A, B}; ``s``, ``r2`` and ``r4`` complete it. An abstract value ``a`` is
the entity ``t:a``. ``build`` makes the C1 facts, C4 items, C3 queue items and C5 outputs the tests feed the scorers.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from khg_contracts import data
from khg_contracts.schema import load_schema

HERE = Path(__file__).resolve().parent
REFERENCE = ("projects", "p2-role-aware-hif", "research", "probes", "scorers", "c5_reference_cases.out.json")
WHERE = {"as_of": None, "valid_mode": "definite", "rank": ["preferred", "normal"], "status": ["asserted"]}
COST = {"prompt_tokens": 100, "completion_tokens": 10, "llm_calls": 1, "retrieval_calls": 1, "retrieval_ms": 1.5,
        "wall_ms": 20}


def fact(fid: str, relation: str, **bindings: str) -> dict[str, Any]:
    """An asserted hyperedge whose roles hold the entities ``t:<value>``, bids in role order."""
    return {"kind": "hyperedge", "id": fid, "relation": relation, "status": "asserted",
            "bindings": [{"bid": f"b{i}", "role": role, "value": {"entity": "t:" + v}}
                         for i, (role, v) in enumerate(sorted(bindings.items()), 1)]}


def literal_fact(fid: str, relation: str, bindings: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """An asserted hyperedge with explicit ``(role, value)`` bindings."""
    return {"kind": "hyperedge", "id": fid, "relation": relation, "status": "asserted",
            "bindings": [{"bid": f"b{i}", "role": r, "value": v} for i, (r, v) in enumerate(bindings, 1)]}


def time(text: str, precision: int, calendar: str = "gregorian") -> dict[str, Any]:
    return {"literal": {"datatype": "time", "time": text, "precision": precision, "calendar": calendar}}


def doc(doc_id: str, gold: list[dict[str, Any]], *, qset: str = "r05", entities: list[Any] | None = None) -> dict:
    """A ``c4-extraction-doc`` item."""
    text = f"the text of {doc_id}"
    out = {"kind": "c4-extraction-doc", "id": "c4:" + doc_id, "qset": qset, "split": "test", "doc_id": doc_id,
           "text": text, "text_sha256": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
           "annotation": {"guideline": "r05-tables/0"}, "gold": gold}
    if entities:
        out["entities"] = entities
    return out


class Items:
    """C3 queue items with increasing qids."""

    def __init__(self) -> None:
        self.n = 0

    def __call__(self, record: dict[str, Any], *, run: str = "run-1", order: str = "o1", doc_id: str = "d1",
                 entities: list[Any] | None = None) -> dict[str, Any]:
        self.n += 1
        payload = dict(copy.deepcopy(record), id=f"cand:q.{self.n}", status="candidate")
        out = {"kind": "queue-item", "qid": f"q:{self.n:06d}", "item_kind": "hyperedge",
               "submitted_at": "2026-10-01T00:00:00Z", "submitted_by": "tests/0",
               "run": {"run_id": run, "order_id": order, "position": self.n},
               "doc": {"doc_id": doc_id, "doc_sha256": "sha256:" + "0" * 64}, "payload": payload}
        if entities:
            out["entities"] = entities
        return out


def question(qid: str, sets: list[list[str]], *, answer: dict[str, Any] | None = None, answerable: bool = True,
             qtype: str = "single_hop", hops: int = 1) -> dict[str, Any]:
    """A ``c4-retrieval-question`` item."""
    return {"kind": "c4-retrieval-question", "id": "c4:" + qid, "qset": "r05", "split": "test", "qid": qid,
            "type": qtype, "text": "?", "anchors": ["t:a"], "answer": answer or {"values": []},
            "support": {"sets": sets}, "hops": hops, "source_class": "n-ary", "answerable": answerable,
            "where": dict(WHERE)}


def response(qid: str, ranked: list[Any], *, answer: dict[str, Any] | None = None, cost: dict[str, Any] | None = None,
             **extra: Any) -> dict[str, Any]:
    """A ``retrieval-response``: a ranked unit is a hyperedge id, or ``(unit_id, hyperedge_id, bids)`` for a pair."""
    units = []
    for i, u in enumerate(ranked, 1):
        if isinstance(u, str):
            units.append({"rank": i, "unit_id": u, "unit_kind": "hyperedge", "hyperedge_ids": [u]})
        else:
            units.append({"rank": i, "unit_id": u[0], "unit_kind": "pair", "hyperedge_ids": [u[1]], "bids": u[2]})
    return {"kind": "retrieval-response", "qid": qid, "answer": answer or {"values": [], "abstained": False},
            "retrieved": units, "cost": dict(COST, **(cost or {})), **extra}


@pytest.fixture(scope="session")
def r05_schema():
    """The R05 table schema (tests/scorers/r05.relation-schema.json)."""
    return load_schema(HERE / "r05.relation-schema.json")


@pytest.fixture(scope="session")
def fixture_schema():
    """The gate fixture's relation schema (packaged)."""
    return load_schema(data.load_json("fixture/fixture.relation-schema.json"))


@pytest.fixture
def build() -> SimpleNamespace:
    """Builders of C1 facts, C4 items, queue items and C5 outputs."""
    return SimpleNamespace(fact=fact, literal_fact=literal_fact, time=time, doc=doc, items=Items(),
                           question=question, response=response)


@pytest.fixture(scope="session")
def reference(repo_root) -> dict[str, Any]:
    """The expected values computed by research/probes/scorers/c5_reference_cases.py (repository checkouts)."""
    path = repo_root.joinpath(*REFERENCE)
    if not path.is_file():
        pytest.skip("the research probe output is only in a repository checkout")
    return json.loads(path.read_text(encoding="utf-8"))
