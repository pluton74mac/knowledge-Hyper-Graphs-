"""Test configuration for khg-width (P6 DESIGN §5).

- ``fixtures/expected.csv`` holds the gate fixtures of DESIGN §5.1 with their expected class, first failed test,
  witness and the four widths; ``helpers.fixture_rows()`` reads it (P2's fixtures resolve through
  ``khg_contracts.data.path``).
- Tests marked ``solvers`` skip unless both BalancedGo and log-k-decomp are found (``scripts/build-solvers.sh``).
- Tests marked ``survey`` skip until ``projects/p6-schema-width/results/survey.csv`` exists.
- Name resolution is blocked for the session: no test reaches the network.
"""
from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from helpers import RESULTS  # noqa: E402


def _refuse(*args, **kwargs):
    raise OSError("network access is blocked in the khg-width tests")


for _name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "create_connection"):
    if hasattr(socket, _name):
        setattr(socket, _name, _refuse)


def pytest_collection_modifyitems(config, items):
    need_solvers = [it for it in items if it.get_closest_marker("solvers")]
    if need_solvers:
        from khg_width.solvers import find_solvers

        found = find_solvers()
        if not {"balancedgo", "logk"} <= set(found):
            skip = pytest.mark.skip(reason="BalancedGo and log-k-decomp not found (scripts/build-solvers.sh)")
            for it in need_solvers:
                it.add_marker(skip)
    if not (RESULTS / "survey.csv").exists():
        skip = pytest.mark.skip(reason="results/survey.csv does not exist yet (the survey has not run)")
        for it in items:
            if it.get_closest_marker("survey"):
                it.add_marker(skip)
