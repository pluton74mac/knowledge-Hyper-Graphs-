"""The packaged conformance suite (``khg-scenario/1.0.0``; DESIGN §6.4): ``index.json``, the 114 scenario files,
the fixture and its schema, read with ``importlib.resources``; and the ``@`` references of the scenarios.

References: ``"@<id>"`` (the fixture record), ``"@<id>.<field>"`` (a field of it), ``"@entities"`` (every entity),
``"@fixture"``, ``"@fixture[core]"`` (the fixture without the records that need ``ordered_roles``,
``special_values`` or ``goals``), ``"@fixture.header"``; and patches ``{"@": id, set, drop, set_binding,
drop_bindings, add_evidence, set_evidence}``. Every resolution returns a fresh copy.
"""
from __future__ import annotations

import copy
import fnmatch
import functools
from typing import Any, Iterable, Mapping

from ... import data
from ...schema import Schema, load_schema
from ..flags import data_flags

__all__ = ["CORE_FLAGS", "SCENARIO_FORMAT", "Suite", "select", "suite"]

SCENARIO_FORMAT = "khg-scenario/1.0.0"
#: The data flags whose records ``@fixture[core]`` leaves out.
CORE_FLAGS = frozenset({"ordered_roles", "special_values", "goals"})
_DIR = "scenarios"
_FILES = "fixture"


class Suite:
    """The index, the scenarios by id (in code-point id order), the fixture, its schema and the core fixture."""

    def __init__(self) -> None:
        self.index: dict[str, Any] = data.load_json(f"{_DIR}/index.json")
        ids = sorted(s["id"] for s in self.index["scenarios"])
        self.scenarios: dict[str, dict[str, Any]] = {i: data.load_json(f"{_DIR}/{i}.json") for i in ids}
        names = {(s["schema"], s["fixture"]) for s in self.scenarios.values()}
        if len(names) != 1:
            raise ValueError(f"the suite names more than one schema or fixture: {sorted(names)}")
        ((schema_name, fixture_name),) = names
        self.schema: Schema = load_schema(self.file(schema_name))
        self.fixture: dict[str, Any] = self.file(fixture_name)
        self.records = {r["id"]: r for r in self.fixture["records"]}
        self.entities = [r for r in self.fixture["records"] if r.get("kind") == "entity"]
        dropped = {r["id"] for r in self.fixture["records"] if data_flags(r) & CORE_FLAGS}
        self.core_dropped = sorted(dropped)
        self.core = {"header": copy.deepcopy(self.fixture["header"]),
                     "records": [r for r in self.fixture["records"] if r.get("id") not in dropped]}

    @staticmethod
    def file(name: str) -> dict[str, Any]:
        """A file a scenario names (``fixture.hif.json``, ...), from the packaged fixture set."""
        if "/" in name or name.startswith("."):
            raise ValueError(f"a scenario names a fixture file by its base name, not {name!r}")
        return data.load_json(f"{_FILES}/{name}")

    # ------------------------------------------------------------------------------------------ references

    def resolve(self, x: Any) -> Any:
        """``x`` with every ``@`` reference and patch resolved (a fresh copy)."""
        if isinstance(x, str) and x.startswith("@"):
            return self._named(x)
        if isinstance(x, Mapping) and "@" in x:
            return self._patched(x)
        if isinstance(x, list):
            return [self.resolve(v) for v in x]
        if isinstance(x, Mapping):
            return {k: self.resolve(v) for k, v in x.items()}
        return copy.deepcopy(x)

    def flat(self, items: Iterable[Any]) -> list[Any]:
        """Resolved items, with lists (``@entities``) spliced in."""
        out: list[Any] = []
        for item in items:
            r = self.resolve(item)
            out.extend(r if isinstance(r, list) else [r])
        return out

    def _named(self, ref: str) -> Any:
        if ref == "@entities":
            return copy.deepcopy(self.entities)
        if ref == "@fixture":
            return copy.deepcopy(self.fixture)
        if ref == "@fixture[core]":
            return copy.deepcopy(self.core)
        if ref == "@fixture.header":
            return copy.deepcopy(self.fixture["header"])
        rid, _, field = ref[1:].partition(".")
        if rid not in self.records:
            raise KeyError(f"the fixture has no record {rid!r}")
        record = self.records[rid]
        return copy.deepcopy(record[field] if field else record)

    def _patched(self, patch: Mapping[str, Any]) -> dict[str, Any]:
        r = self._named("@" + patch["@"])
        for k, v in patch.get("set", {}).items():
            r[k] = self.resolve(v)
        for k in patch.get("drop", []):
            r.pop(k, None)
        bindings = {b["bid"]: b for b in r.get("bindings", [])}
        for bid, value in patch.get("set_binding", {}).items():
            bindings[bid]["value"] = copy.deepcopy(value)
        for bid in patch.get("drop_bindings", []):
            r["bindings"] = [b for b in r["bindings"] if b["bid"] != bid]
            for e in r.get("evidence", []):
                if "supports" in e:
                    e["supports"] = [s for s in e["supports"] if s != bid]
        evidence = {e["id"]: e for e in r.get("evidence", [])}
        for eid, changes in patch.get("set_evidence", {}).items():
            evidence[eid].update(copy.deepcopy(changes))
        if "add_evidence" in patch:
            r.setdefault("evidence", []).extend(copy.deepcopy(patch["add_evidence"]))
        return r


@functools.lru_cache(maxsize=1)
def suite() -> Suite:
    """The packaged suite, read once (treat it as read-only; ``resolve`` returns copies)."""
    return Suite()


def select(ids: Iterable[str], only: str | Iterable[str] | None) -> list[str]:
    """The scenario ids that match ``only``: None (all), a glob (``"S-KEY-*"``) or several globs."""
    if only is None:
        return list(ids)
    patterns = [only] if isinstance(only, str) else list(only)
    return [i for i in ids if any(fnmatch.fnmatchcase(i, p) for p in patterns)]
