"""Shared set-up of the consumer acceptance tests (W13; DESIGN §1.3, §10.5).

DESIGN §1.3 writes one call sequence per consumer project (P1, P3a, P3b, P5, P6, P7, P9, P10) against the public API
of §10.2. Each ``test_<project>.py`` copies its sequence verbatim between the marker lines ``# >>> DESIGN §1.3`` and
``# <<< DESIGN §1.3``, supplies the sequence's free variables from packaged data, runs it on ``MemoryStore`` and then
asserts on what it produced. ``test_verbatim.py`` checks every copy, and the prologue, against DESIGN.md.

The sequences name their files relatively. ``workdir`` is a fresh directory, made the working directory, that holds
the packaged files under the names the sequences use:

- ``p2-gate.relation-schema.json``: ``fixture/fixture.relation-schema.json`` (the schema ``p2-gate`` 1.0.0);
- ``corpus.khg.jsonl``: ``fixture/fixture.c1.jsonl``, the gate fixture as JSONL;
- ``qset.c4.jsonl``: ``fixture/c4-items.jsonl``, the C4 draft's example items.

``S`` runs the prologue's schema line in ``workdir``. The other fixtures hand out fresh copies of packaged data.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import data
from khg_contracts import schema as sch

#: The name each sequence uses for a packaged file.
WORKDIR_FILES = {
    "p2-gate.relation-schema.json": "fixture/fixture.relation-schema.json",
    "corpus.khg.jsonl": "fixture/fixture.c1.jsonl",
    "qset.c4.jsonl": "fixture/c4-items.jsonl",
}


@pytest.fixture()
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh working directory holding the packaged files under the sequences' names."""
    for name, packaged in WORKDIR_FILES.items():
        (tmp_path / name).write_bytes(data.read_bytes(packaged))
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture()
def S(workdir: Path) -> sch.Schema:
    """The prologue's schema, loaded by the §1.3 line itself (``S`` is the name every sequence uses)."""
    # >>> DESIGN §1.3
    S = sch.load_schema("p2-gate.relation-schema.json")        # Schema; raises ValidationError (M codes)
    # <<< DESIGN §1.3
    return S


@pytest.fixture()
def fixture_doc() -> dict[str, Any]:
    """``fixture.c1.json``: 22 entities and 18 hyperedges (DESIGN §2.11)."""
    return data.load_json("fixture/fixture.c1.json")


@pytest.fixture()
def by_id(fixture_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The fixture's records by id (copies)."""
    return {r["id"]: copy.deepcopy(r) for r in fixture_doc["records"]}


@pytest.fixture()
def fixture_entities(fixture_doc: dict[str, Any]) -> list[dict[str, Any]]:
    """The fixture's 22 entity records, in id order."""
    return [copy.deepcopy(r) for r in fixture_doc["records"] if r["kind"] == "entity"]


@pytest.fixture()
def labels(fixture_entities: list[dict[str, Any]]) -> dict[str, str]:
    """Entity id -> label, as ``record.render_text`` takes them."""
    return {e["id"]: e["label"] for e in fixture_entities}


@pytest.fixture()
def derived() -> dict[str, dict[str, Any]]:
    """The recomputed ``derived`` block of every fixture hyperedge (``fixture.with-derived.c1.json``)."""
    doc = data.load_json("fixture/fixture.with-derived.c1.json")
    return {r["id"]: r["derived"] for r in doc["records"] if "derived" in r}


@pytest.fixture()
def c4_items() -> list[dict[str, Any]]:
    """The lines of the packaged C4 file ``c4-items.jsonl``: its header, then one item of each kind."""
    return data.load_jsonl("fixture/c4-items.jsonl")


@pytest.fixture()
def c5_outputs() -> list[dict[str, Any]]:
    """The three system outputs of ``c5-outputs.jsonl``: a completion rank, a retrieval and a memory response."""
    return data.load_jsonl("fixture/c5-outputs.jsonl")


@pytest.fixture()
def splits(c4_items: list[dict[str, Any]], by_id: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """The fixture's hyperedges split by the C4 split manifest (``c4:splits``): ``train``, ``valid``, ``test``."""
    manifest = next(x for x in c4_items if x["kind"] == "c4-split-manifest")["splits"]
    return {name: [by_id[i] for i in sorted(manifest) if manifest[i] == name] for name in ("train", "valid", "test")}
