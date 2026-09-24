"""Test configuration for khg-contracts.

- Network access is blocked for the whole session, before any test module is imported: IP connections, datagrams
  and name resolution raise ``OSError`` ("network access is blocked"). Local AF_UNIX sockets still work.
  ``tests/packaging/test_network_block.py`` checks the block itself.
- The markers ``gate`` (G1-G3), ``libs`` (needs xgi or HyperNetX) and ``evidence`` (writes the upstream evidence
  file) are registered here.
- The fixtures ``repo_root`` and ``examples_dir`` locate the repository and ``design-examples/``.
"""
from __future__ import annotations

import socket
from pathlib import Path

import pytest

BLOCKED_MESSAGE = "network access is blocked in the khg-contracts tests"
REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "projects" / "p2-role-aware-hif" / "design-examples"


class NetworkBlockedError(OSError):
    """Raised by every blocked socket operation."""


def _is_local(sock: socket.socket) -> bool:
    return getattr(socket, "AF_UNIX", None) is not None and sock.family == socket.AF_UNIX


def _guard_method(original):
    def method(self, *args, **kwargs):
        if _is_local(self):
            return original(self, *args, **kwargs)
        raise NetworkBlockedError(BLOCKED_MESSAGE)
    method.__name__ = getattr(original, "__name__", "blocked")
    method.__khg_blocked__ = True
    return method


def _refuse(*args, **kwargs):
    raise NetworkBlockedError(BLOCKED_MESSAGE)


def _block_network() -> None:
    if getattr(socket.socket.connect, "__khg_blocked__", False):
        return
    for name in ("connect", "connect_ex", "sendto", "sendmsg"):
        original = getattr(socket.socket, name, None)
        if original is not None:
            setattr(socket.socket, name, _guard_method(original))
    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "getnameinfo",
                 "create_connection"):
        if hasattr(socket, name):
            setattr(socket, name, _refuse)


_block_network()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "gate: a gate clause test (G1 round trip, G2 malformed cases, G3 smoke)")
    config.addinivalue_line("markers", "libs: needs xgi or HyperNetX (skipped by pytest.importorskip without them)")
    config.addinivalue_line("markers", "evidence: the upstream evidence test, which writes library-hif-evidence.json")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """The repository root (where pyproject.toml is)."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def examples_dir() -> Path:
    """``projects/p2-role-aware-hif/design-examples``; skips when the checkout does not have it (an sdist)."""
    if not EXAMPLES_DIR.is_dir():
        pytest.skip("design-examples/ is not available (not a repository checkout)")
    return EXAMPLES_DIR
