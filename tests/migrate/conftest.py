"""Fixtures of the migration tests (DESIGN §11.3).

``v0-sample.hif.json`` beside this file is a verbatim copy of the knowledge base's ``schemas/sample.hif.json``, so the
tests run from an sdist too; ``test_sample.py`` checks the copy against the original when the checkout has it. The
goldens are read from the package (``data/sample/``) through importlib.resources.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import data, hif, jsonio, migrate
from khg_contracts.schema import Schema, load_schema

HERE = Path(__file__).resolve().parent
V0_SAMPLE = HERE / "v0-sample.hif.json"
#: Output -> its golden under ``data/``.
GOLDENS = {
    "schema": "sample/sample.relation-schema.json",
    "container": "sample/sample.khg.json",
    "hif": "sample/sample.khg.hif.json",
    "report": "sample/sample.migration-report.json",
}


@pytest.fixture(scope="session")
def v0_path() -> Path:
    return V0_SAMPLE


@pytest.fixture
def v0() -> dict[str, Any]:
    """A fresh parsed copy of the v0 sample (tests may modify it)."""
    return jsonio.load(V0_SAMPLE)


@pytest.fixture(scope="session")
def migrated() -> migrate.Migration:
    return migrate.v0_sample_to_v1(jsonio.load(V0_SAMPLE))


@pytest.fixture(scope="session")
def schema(migrated: migrate.Migration) -> Schema:
    return load_schema(migrated.schema)


@pytest.fixture(scope="session")
def outputs(migrated: migrate.Migration, schema: Schema) -> dict[str, dict[str, Any]]:
    """The four documents that have goldens: the three results and the HIF export of the container."""
    return {"schema": migrated.schema, "container": migrated.container, "report": migrated.report,
            "hif": hif.to_hif(copy.deepcopy(migrated.container), schema)}


@pytest.fixture(scope="session")
def golden_files() -> dict[str, str]:
    """Output -> the packaged path of its golden."""
    return dict(GOLDENS)


@pytest.fixture(scope="session")
def goldens() -> dict[str, dict[str, Any]]:
    return {name: data.load_json(rel) for name, rel in GOLDENS.items()}
