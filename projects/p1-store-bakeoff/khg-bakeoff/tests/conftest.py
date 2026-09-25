"""Test configuration for khg-bakeoff (P1 DESIGN §6).

- The embedded backends (SQLite, HIF, and Oxigraph when pyoxigraph is installed) always run. A server backend runs
  only when its environment variable names an endpoint (``KHG_BAKEOFF_POSTGRES``, ``KHG_BAKEOFF_NEO4J``,
  ``KHG_BAKEOFF_TYPEDB``) and its client is installed; otherwise its tests skip (``helpers.backend_params``).
- Name resolution is limited to the loopback host: no test reaches the network beyond this machine.
- Fixtures: P2's gate fixture and its schema, and P1's edge-case container (``projects/p1-store-bakeoff/fixtures``).
"""
from __future__ import annotations

import copy
import os
import socket
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from helpers import FIXTURES  # noqa: E402

from khg_contracts import data  # noqa: E402
from khg_contracts.record import read_container  # noqa: E402
from khg_contracts.schema import load_schema  # noqa: E402

LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_getaddrinfo = socket.getaddrinfo


def _local_only(host, *args, **kwargs):
    if host is None or str(host) in LOOPBACK:
        return _getaddrinfo(host, *args, **kwargs)
    raise OSError(f"network access beyond the loopback host is blocked in the khg-bakeoff tests ({host})")


socket.getaddrinfo = _local_only
os.environ.setdefault("P1_TMP", tempfile.gettempdir())
os.environ.setdefault("KHG_BAKEOFF_FIXTURES", str(FIXTURES))


@pytest.fixture(scope="session")
def schema():
    return load_schema(data.load_json("fixture/fixture.relation-schema.json"))


@pytest.fixture()
def fixture_doc() -> dict[str, Any]:
    return data.load_json("fixture/fixture.c1.json")


@pytest.fixture(scope="session")
def edge_schema():
    return load_schema(FIXTURES / "edge.relation-schema.json")


@pytest.fixture()
def edge_doc() -> dict[str, Any]:
    return copy.deepcopy(read_container(FIXTURES / "edge.c1.json"))
