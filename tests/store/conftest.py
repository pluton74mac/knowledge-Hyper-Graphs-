"""Shared data for the store tests (W8): the fixture, its schema, a fresh ``MemoryStore`` on the scenario clock, and
small builders for records and literals."""
from __future__ import annotations

import copy
from typing import Any, Callable

import pytest

from khg_contracts import data, store
from khg_contracts.schema import load_schema
from khg_contracts.store import conformance

#: The evidence the scenarios use for curated writes.
CUR = {"id": "e9", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:test"}}


@pytest.fixture(scope="session")
def schema():
    return load_schema(data.load_json("fixture/fixture.relation-schema.json"))


@pytest.fixture()
def fixture_doc() -> dict[str, Any]:
    return data.load_json("fixture/fixture.c1.json")


@pytest.fixture()
def entities(fixture_doc) -> list[dict[str, Any]]:
    return [r for r in fixture_doc["records"] if r["kind"] == "entity"]


@pytest.fixture()
def rec() -> Callable[..., dict[str, Any]]:
    """``rec("f:reg-1")``, or a patched copy: ``rec("f:king-13", drop_bindings=["b4"], set={"rank": ...})`` (the
    scenario patch keys)."""
    suite = conformance.suite()

    def build(rid: str, **patch: Any) -> dict[str, Any]:
        return suite.resolve({"@": rid, **patch}) if patch else suite.resolve("@" + rid)
    return build


@pytest.fixture()
def cur() -> dict[str, Any]:
    return copy.deepcopy(CUR)


@pytest.fixture()
def ms(schema) -> store.MemoryStore:
    """An empty reference store on the scenario clock (2026-10-01T00:00:00Z, one second per write)."""
    return store.MemoryStore(schema, clock=store.ScenarioClock())


@pytest.fixture()
def loaded(schema, fixture_doc) -> store.MemoryStore:
    """A reference store holding the fixture."""
    s = store.MemoryStore(schema, clock=store.ScenarioClock())
    s.load(fixture_doc)
    return s


def time_literal(t: str, precision: int = 11, calendar: str | None = None) -> dict[str, Any]:
    lit: dict[str, Any] = {"datatype": "time", "time": t, "precision": precision}
    if calendar:
        lit["calendar"] = calendar
    return {"literal": lit}


@pytest.fixture()
def T() -> Callable[..., dict[str, Any]]:
    """``T("+1643-05-14T00:00:00Z")``: a time literal value (precision 11 by default)."""
    return time_literal
