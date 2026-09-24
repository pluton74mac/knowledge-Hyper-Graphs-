"""Shared helpers for the validator tests: the malformed cases of G2 as inputs, and cached runs.

``malformed`` (a session fixture) builds each case's input as the G2 rule states it (DESIGN §8.2): the named base
plus its RFC 6902 patch (or ``input_text`` for layer J), a ``schema_patch`` applied to the fixture schema with the
base's schema digest re-stamped, the case's own ``doc_text``, and the smoke base for queues. Runs are cached per
(case, engine, stop), so the test modules share them.
"""
from __future__ import annotations

import copy
import functools
from typing import Any

import pytest

from khg_contracts import data, jsonio
from khg_contracts.schema import load_schema
from khg_contracts.validate import layers, run
from khg_contracts.validate.runner import Report

BASE_FILES = {
    "fixture.c1.json": "fixture/fixture.c1.json",
    "fixture.history.c1.json": "fixture/fixture.history.c1.json",
    "fixture.hif.json": "fixture/fixture.hif.json",
    "fixture.directed-slice.hif.json": "fixture/fixture.directed-slice.hif.json",
    "fixture.relation-schema.json": "fixture/fixture.relation-schema.json",
    "smoke-queue.khg-queue.jsonl": "fixture/smoke-queue.khg-queue.jsonl",
    "c4-items.jsonl": "fixture/c4-items.jsonl",
}
#: The case kinds of the list mapped to validate()'s kinds (J cases run as HIF, as in the prototype harness).
KIND = {"json": "hif", "c1": "container", "hif": "hif", "relation-schema": "schema", "queue": "queue", "c4": "item"}


def _parts(pointer: str) -> list[str]:
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]


def resolve(doc: Any, pointer: str) -> Any:
    for p in _parts(pointer):
        doc = doc[int(p)] if isinstance(doc, list) else doc[p]
    return doc


def apply_patch(doc: Any, patch: list[dict[str, Any]] | None) -> Any:
    """RFC 6902 ``add``, ``replace`` and ``remove`` (the operations the case list uses) on a copy."""
    doc = copy.deepcopy(doc)
    for op in patch or []:
        parts = _parts(op["path"])
        parent = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        last = parts[-1]
        value = copy.deepcopy(op.get("value"))
        if op["op"] == "remove":
            del parent[int(last) if isinstance(parent, list) else last]
        elif op["op"] == "replace":
            if isinstance(parent, list):
                parent[int(last)] = value
            else:
                assert last in parent, op["path"]
                parent[last] = value
        elif op["op"] == "add":
            if isinstance(parent, list):
                parent.append(value) if last == "-" else parent.insert(int(last), value)
            else:
                parent[last] = value
        else:  # pragma: no cover - the list uses only the three operations above
            raise AssertionError(op["op"])
    return doc


class Malformed:
    """The case list, its inputs and cached validator runs."""

    def __init__(self) -> None:
        doc = data.load_json("malformed-cases.json")
        self.cases: list[dict[str, Any]] = doc["cases"]
        self.by_id = {c["id"]: c for c in self.cases}
        self.schema = data.load_json("fixture/fixture.relation-schema.json")
        self.loaded_schema = load_schema(self.schema)
        self.smoke_base = data.load_json("fixture/smoke-base.c1.json")
        self.doc_texts = data.load_json("fixture/fixture.doc-texts.json")

    @functools.lru_cache(maxsize=None)  # noqa: B019 - one instance per session
    def base(self, name: str) -> Any:
        """A base as the patches address it: queue and C4 files as ``{"lines": [...]}``."""
        rel = BASE_FILES[name]
        return {"lines": data.load_jsonl(rel)} if rel.endswith(".jsonl") else data.load_json(rel)

    def kind(self, case: dict[str, Any]) -> str:
        return KIND[case["kind"]]

    def inputs(self, case: dict[str, Any]) -> tuple[Any, Any, dict[str, str]]:
        """``(input, schema document, doc_texts)`` of a case."""
        if case["kind"] == "json":
            return case["input_text"].encode("utf-8"), self.schema, {}
        schema = apply_patch(self.schema, case.get("schema_patch")) if case.get("schema_patch") else self.schema
        doc = apply_patch(self.base(case["base"]), case.get("patch"))
        if case.get("schema_patch"):
            digest = jsonio.digest("khg-schema/1", schema)
            if case["kind"] == "c1":
                doc["header"]["schema"]["sha256"] = digest
            elif case["kind"] == "hif":
                doc["metadata"]["khg-schema-sha256"] = digest
        obj = doc["lines"] if case["kind"] in ("queue", "c4") else doc
        return obj, schema, dict(case.get("doc_text") or {})

    @functools.lru_cache(maxsize=None)  # noqa: B019 - one instance per session
    def report(self, case_id: str, engine: str = "jsonschema", stop: str = "all") -> Report:
        """The full report of a case (``Report.until_first_rejection`` gives what ``stop="first"`` returns)."""
        case = self.by_id[case_id]
        obj, schema, texts = self.inputs(case)
        kind = self.kind(case)
        if kind == "schema":
            schema = None
        elif schema is self.schema:
            schema = self.loaded_schema  # loaded once: load_schema runs the M checks
        return run(obj, kind=kind, schema=schema, doc_texts=texts, bases={"p2-smoke-base": self.smoke_base},
                   engine=engine, stop=stop)

    def module_for(self, case: dict[str, Any]) -> str:
        """The layer module a case's code depends on: the module of its layer in its kind's pipeline, except that
        a HIF case of layer C, S or D depends on decoding (MC063 is S016 emitted while decoding)."""
        kind = self.kind(case)
        if kind == "hif" and case["layer"] in ("C", "S", "D"):
            return "d_decode"
        return next(name for name in layers.PIPELINES[kind] if layers.spec(name).letter == case["layer"])


@pytest.fixture(scope="session")
def malformed() -> Malformed:
    return Malformed()
