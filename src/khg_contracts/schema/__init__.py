"""The relation-type schema language ``khg-relation-schema/1.1.0`` (DESIGN §3; 1.1 is ruling 22: a key's
``separators`` and a qualifier usage's ``monotone: false``). The reader takes 1.0.x and 1.1.x documents.

- ``load_schema(path | mapping) -> Schema`` checks a document (layers J, V, M) and raises ``ValidationError``.
- ``Schema`` gives ``.id``, ``.version``, ``.ref``, ``.sha256``, ``.relation(id)``, ``.usage(rel, role)`` and the
  built-in lifecycle relations and ``khg:end_cause`` usage.
- ``check_schema(doc, engine=...)`` returns the findings instead of raising; ``required_format(doc)`` is the lowest
  ``format`` a writer stamps (``FORMAT`` or ``FORMAT_1_1``).
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
from .checks import FORMAT, FORMAT_1_1, check_schema, load_schema, required_format
from .hypergraph import is_alpha_acyclic, schema_hypergraph
from .model import Schema

__all__ = [
    "CONSTRAINT_TYPES",
    "DATATYPES",
    "DEFAULT_TIME",
    "END_CAUSE",
    "FORMAT",
    "FORMAT_1_1",
    "LIFECYCLE_RELATIONS",
    "POLICIES",
    "SEVERITIES",
    "SLOTS",
    "TIME_MODELS",
    "Schema",
    "check_schema",
    "is_alpha_acyclic",
    "load_schema",
    "required_format",
    "schema_hypergraph",
]
