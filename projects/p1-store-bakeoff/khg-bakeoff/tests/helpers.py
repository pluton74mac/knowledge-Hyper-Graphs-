"""Test helpers for khg-bakeoff: where the fixtures are, and which backends this run can reach."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from khg_bakeoff.backends import BACKENDS, available

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parents[1] / "fixtures"
EMBEDDED = ("sqlite", "oxigraph", "hif")
SERVERS = ("postgres", "neo4j", "typedb")
ALL = EMBEDDED + SERVERS


def backend_params(names: tuple[str, ...] = ALL) -> list[Any]:
    """``pytest.param`` per backend: marked ``server`` for a client-server one, skipped when it cannot run here."""
    out = []
    for name in names:
        marks: list[Any] = []
        if BACKENDS[name].env is not None:
            marks.append(pytest.mark.server)
        if not available(name):
            why = f"{BACKENDS[name].env} is not set" if BACKENDS[name].env else f"{BACKENDS[name].client} is missing"
            marks.append(pytest.mark.skip(reason=f"{name}: {why}"))
        out.append(pytest.param(name, marks=marks, id=name))
    return out
