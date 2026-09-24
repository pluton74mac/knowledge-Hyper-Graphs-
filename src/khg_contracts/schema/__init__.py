"""The relation-type schema language ``khg-relation-schema/1.0.0`` (DESIGN §3).

- ``load_schema(path | mapping) -> Schema`` checks a document (layers J, V, M) and raises ``ValidationError``.
- ``Schema`` gives ``.id``, ``.version``, ``.ref``, ``.sha256``, ``.relation(id)``, ``.usage(rel, role)`` and the
  built-in lifecycle relations and ``khg:end_cause`` usage.
- ``check_schema(doc, engine=...)`` returns the findings instead of raising.
- ``schema_hypergraph`` and ``is_alpha_acyclic`` give P6 the schema as a hypergraph and its GYO test.
"""
from __future__ import annotations

from .builtins import (
    CONSTRAINT_TYPES,
    DATATYPES,
    DEFAULT_TIME,
    END_CAUSE,
    LIFECYCLE_RELATIONS,
    POLICIES,
    SEVERITIES,
    SLOTS,
    TIME_MODELS,
)
from .checks import FORMAT, check_schema, load_schema
from .hypergraph import is_alpha_acyclic, schema_hypergraph
from .model import Schema

__all__ = [
    "CONSTRAINT_TYPES",
    "DATATYPES",
    "DEFAULT_TIME",
    "END_CAUSE",
    "FORMAT",
    "LIFECYCLE_RELATIONS",
    "POLICIES",
    "SEVERITIES",
    "SLOTS",
    "TIME_MODELS",
    "Schema",
    "check_schema",
    "is_alpha_acyclic",
    "load_schema",
    "schema_hypergraph",
]
