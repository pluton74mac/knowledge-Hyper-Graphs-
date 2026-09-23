"""Shared data for the HIF tests (W6): the fixture set, its schema, and the HIF cases of the G2 list with their
inputs built as DESIGN §8.2 states (the named base plus its RFC 6902 patch)."""
from __future__ import annotations

import copy
from typing import Any

import pytest

from khg_contracts import data
from khg_contracts.schema import load_schema

HIF_BASES = {"fixture.hif.json": "fixture/fixture.hif.json",
             "fixture.directed-slice.hif.json": "fixture/fixture.directed-slice.hif.json"}
ROLE_CONVENTION_FILES = ("basic", "two-roles", "tail-head", "ordered", "undirected")
ENGINES = ("jsonschema", "fastjsonschema")


def _parts(pointer: str) -> list[str]:
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]


def resolve(doc: Any, pointer: str) -> Any:
    """The value an RFC 6901 pointer names."""
    for p in _parts(pointer):
        doc = doc[int(p)] if isinstance(doc, list) else doc[p]
    return doc


def apply_patch(doc: Any, patch: list[dict[str, Any]]) -> Any:
    """RFC 6902 ``add``, ``replace`` and ``remove`` (the operations of the case list) on a copy."""
    doc = copy.deepcopy(doc)
    for op in patch:
        parts = _parts(op["path"])
        parent = resolve(doc, "".join("/" + p.replace("~", "~0").replace("/", "~1") for p in parts[:-1]))
        last, value = parts[-1], copy.deepcopy(op.get("value"))
        if op["op"] == "remove":
            del parent[int(last) if isinstance(parent, list) else last]
        elif op["op"] == "replace":
            assert isinstance(parent, list) or last in parent, op["path"]
            parent[int(last) if isinstance(parent, list) else last] = value
        else:
            assert op["op"] == "add", op
            if isinstance(parent, list):
                parent.append(value) if last == "-" else parent.insert(int(last), value)
            else:
                parent[last] = value
    return doc


def hif_cases() -> list[dict[str, Any]]:
    """The HIF cases of the list: the 15 H, 6 R, 24 P and 8 decoding D cases, MC063 (S016) and MC010 (V)."""
    return [c for c in data.load_json("malformed-cases.json")["cases"] if c["kind"] == "hif"]


def case_input(case: dict[str, Any]) -> dict[str, Any]:
    return apply_patch(data.load_json(HIF_BASES[case["base"]]), case["patch"])


@pytest.fixture(scope="session")
def schema_doc() -> dict[str, Any]:
    return data.load_json("fixture/fixture.relation-schema.json")


@pytest.fixture(scope="session")
def schema(schema_doc):
    return load_schema(schema_doc)


@pytest.fixture()
def c1() -> dict[str, Any]:
    return data.load_json("fixture/fixture.c1.json")


@pytest.fixture()
def full() -> dict[str, Any]:
    return data.load_json("fixture/fixture.hif.json")


@pytest.fixture()
def directed_slice() -> dict[str, Any]:
    return data.load_json("fixture/fixture.directed-slice.hif.json")


@pytest.fixture(scope="session")
def doc_texts() -> dict[str, Any]:
    return data.load_json("fixture/fixture.doc-texts.json")
