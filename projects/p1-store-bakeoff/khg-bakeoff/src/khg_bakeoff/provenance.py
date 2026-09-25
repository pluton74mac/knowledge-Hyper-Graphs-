"""What every results file records (research 01 D10): the contract versions, the khg-contracts version and commit
(the last commit that changed ``src/khg_contracts``, and whether the working tree changes it), and the Python,
SQLite library and client versions. Each engine's own version comes from its store (``engine()``)."""
from __future__ import annotations

import importlib.metadata
import platform
import subprocess
from pathlib import Path
from typing import Any

from khg_contracts import CONTRACTS
from khg_contracts import __version__ as KHG_CONTRACTS_VERSION

from . import __version__

__all__ = ["CLIENTS", "provenance"]

#: The Python distributions of the clients (pinned in pyproject.toml).
CLIENTS = ("pyoxigraph", "psycopg", "neo4j", "typedb-driver")


def _git(*args: str) -> str | None:
    import khg_contracts

    root = Path(khg_contracts.__file__).resolve().parents[2]
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip()


def provenance() -> dict[str, Any]:
    clients = {}
    for name in CLIENTS:
        try:
            clients[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            clients[name] = None
    dirty = _git("status", "--porcelain", "--", "src/khg_contracts")
    return {
        "contracts": {"C1": f"khg-record/{CONTRACTS['khg-record']}", "C2": f"khg-store/{CONTRACTS['khg-store']}",
                      "scenarios": f"khg-scenario/{CONTRACTS['khg-scenario']}",
                      "HIF profile": f"khg-hif/{CONTRACTS['khg-hif']}"},
        "khg_contracts": {"version": KHG_CONTRACTS_VERSION,
                          "commit": _git("log", "-1", "--format=%H", "--", "src/khg_contracts"),
                          "src_modified": None if dirty is None else bool(dirty)},
        "khg_bakeoff": __version__,
        "python": platform.python_version(),
        "sqlite_library": __import__("sqlite3").sqlite_version,
        "clients": clients,
    }
