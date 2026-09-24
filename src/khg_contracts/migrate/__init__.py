"""Migrations to the current contracts (DESIGN §11.2, §11.3).

- ``v0_sample_to_v1(hif) -> Migration(schema, container, report)`` migrates the knowledge base's
  ``schemas/sample.hif.json`` (the ``v0-sample`` format) to ``khg-record/1.0.0``: a generated relation-type schema,
  the canonical C1 container and a ``khg-migration-report/1.0.0`` report of F findings. A stored arity that
  disagrees with the C1 rule raises ``ValidationError`` (D015).
- ``MIGRATIONS`` maps each ``khg-migrate --from`` id to its function.
- ``dumps`` and ``LAYOUT`` write the outputs in the layout of the committed goldens (``data/sample/``).

The function is also the name of its module, ``migrate/v0_sample_to_v1.py`` (§10.1): ``migrate.v0_sample_to_v1``
is the function, and so is ``import khg_contracts.migrate.v0_sample_to_v1 as m`` (it reads the package attribute).
``importlib.import_module("khg_contracts.migrate.v0_sample_to_v1")`` gives the module.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Callable, Mapping

from .layout import LAYOUT, dumps
from .v0_sample_to_v1 import REPORT_FORMAT, V0_SAMPLE, Migration, generate_schema, v0_sample_to_v1

__all__ = ["LAYOUT", "MIGRATIONS", "REPORT_FORMAT", "V0_SAMPLE", "Migration", "dumps", "generate_schema",
           "v0_sample_to_v1"]

#: ``--from`` id -> migration.
MIGRATIONS: Mapping[str, Callable[[Any], Migration]] = MappingProxyType({V0_SAMPLE: v0_sample_to_v1})
