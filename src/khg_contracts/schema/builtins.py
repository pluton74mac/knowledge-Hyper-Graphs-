"""The vocabulary of the schema language and the built-in parts of every schema (DESIGN §2.4-§2.7, §3).

- The lifecycle relations ``khg:supersedes``, ``khg:retracts`` and ``khg:disputes`` (kind ``lifecycle``) with their
  roles and reason lists (§2.7).
- ``khg:end_cause``, the meta usage built into every relation with an interval time model (Wikidata P1534).
- The built-in confidence scale ``probability``.
"""
from __future__ import annotations

import copy
from typing import Any

__all__ = [
    "DATATYPES",
    "SLOTS",
    "TIME_MODELS",
    "POLICIES",
    "CONSTRAINT_TYPES",
    "SEVERITIES",
    "RESERVED_PREFIX",
    "DEFAULT_TIME",
    "DEFAULT_POLICY",
    "PROBABILITY",
    "LIFECYCLE_RELATIONS",
    "END_CAUSE",
    "lifecycle_relations",
    "end_cause_usage",
]

DATATYPES = ("time", "quantity", "string", "lang_string", "boolean", "iri", "geo")
SLOTS = ("core", "qualifier", "time", "meta")
TIME_MODELS = ("interval", "invariant", "timeless")
POLICIES = ("close_older", "supersede", "dispute", "reject")
CONSTRAINT_TYPES = ("requires", "excludes", "at_least_one_of", "must_differ", "must_agree")
SEVERITIES = ("error", "warning")
RESERVED_PREFIX = "khg:"
DEFAULT_TIME: dict[str, str] = {"model": "timeless"}
DEFAULT_POLICY = "dispute"
PROBABILITY: dict[str, Any] = {"id": "probability", "kind": "bounded", "min": 0, "max": 1}


def _lifecycle_usage(role: str, direction: str, minimum: int) -> dict[str, Any]:
    return {"role": role, "slot": "core", "fillers": [{"fact": []}], "min": minimum, "max": None,
            "direction": direction}


LIFECYCLE_RELATIONS: dict[str, dict[str, Any]] = {
    "khg:supersedes": {
        "id": "khg:supersedes", "kind": "lifecycle",
        "reasons": ["correction", "duplicate", "refinement", "conflation", "schema_migration", "other"],
        "roles": [_lifecycle_usage("khg:superseding", "tail", 1), _lifecycle_usage("khg:superseded", "head", 1)],
    },
    "khg:retracts": {
        "id": "khg:retracts", "kind": "lifecycle",
        "reasons": ["withdrawn", "unsupported", "other"],
        "roles": [_lifecycle_usage("khg:retracted", "head", 1)],
    },
    "khg:disputes": {
        "id": "khg:disputes", "kind": "lifecycle",
        "reasons": ["key_conflict", "negation_conflict", "curator", "other"],
        "roles": [_lifecycle_usage("khg:disputed", "head", 2)],
    },
}

END_CAUSE: dict[str, Any] = {"role": "khg:end_cause", "slot": "meta",
                             "fillers": [{"entity": []}, {"literal": "string"}],
                             "min": 0, "max": 1, "direction": "tail"}


def lifecycle_relations() -> dict[str, dict[str, Any]]:
    """A fresh copy of the built-in lifecycle relations, by id."""
    return copy.deepcopy(LIFECYCLE_RELATIONS)


def end_cause_usage() -> dict[str, Any]:
    """A fresh copy of the built-in ``khg:end_cause`` meta usage."""
    return copy.deepcopy(END_CAUSE)
