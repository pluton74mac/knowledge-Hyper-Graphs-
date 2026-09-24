"""Shared data for the loader tests (W7): the fixture set through importlib.resources."""
from __future__ import annotations

from typing import Any

import pytest

from khg_contracts import data
from khg_contracts.schema import Schema, load_schema

ROLE_CONVENTION_FILES = ("basic", "two-roles", "tail-head", "ordered", "undirected")


@pytest.fixture(scope="session")
def schema() -> Schema:
    return load_schema(data.load_json("fixture/fixture.relation-schema.json"))


@pytest.fixture()
def c1() -> dict[str, Any]:
    return data.load_json("fixture/fixture.c1.json")


@pytest.fixture()
def full() -> dict[str, Any]:
    """``fixture.hif.json``: undirected, 46 nodes, 18 edges, 59 incidences (§4.6)."""
    return data.load_json("fixture/fixture.hif.json")


@pytest.fixture()
def directed_slice() -> dict[str, Any]:
    """``fixture.directed-slice.hif.json``: directed, 42 nodes, 16 edges, 52 incidences (§4.6)."""
    return data.load_json("fixture/fixture.directed-slice.hif.json")


@pytest.fixture(scope="session")
def slice_relations() -> list[str]:
    return data.load_json("fixture/fixture.directed-slice.hif.json")["metadata"]["khg-slice"]["relations"]


@pytest.fixture(params=ROLE_CONVENTION_FILES)
def convention_file(request) -> tuple[str, dict[str, Any]]:
    """One of the five fixture-PR files, which carry the convention but not the profile (§4.4)."""
    return request.param, data.load_json(f"role-convention/{request.param}.hif.json")
