"""Finding the solver binaries (DESIGN §4.5).

Order: ``KHG_WIDTH_BALANCEDGO`` / ``KHG_WIDTH_LOGK`` (a binary), then ``KHG_WIDTH_SOLVERS`` (a DEST of
``scripts/build-solvers.sh``), then the default DEST ``${XDG_CACHE_HOME:-~/.cache}/khg-width/solvers``, then ``PATH``.
A DEST's ``solvers.json`` gives the commit; a binary from ``PATH`` or an explicit variable outside a DEST has commit
``"unknown"``. The sha256 of the binary is always computed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

__all__ = ["SolverInfo", "find_solvers", "default_dest", "TOOLS"]

#: tool -> (binary name, environment variable)
TOOLS = {"balancedgo": ("BalancedGo", "KHG_WIDTH_BALANCEDGO"), "logk": ("log-k-decomp", "KHG_WIDTH_LOGK")}


@dataclass(frozen=True)
class SolverInfo:
    """A found binary: ``path``, ``commit`` (or "unknown"), ``sha256`` of the binary, ``how`` it was found."""

    name: str
    path: str
    commit: str
    sha256: str
    how: str
    describe: str | None = None
    go_version: str | None = None

    def to_json(self) -> dict[str, str | None]:
        return {"name": self.name, "path": self.path, "commit": self.commit, "sha256": self.sha256, "how": self.how,
                "describe": self.describe, "go_version": self.go_version}


def default_dest(env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    base = env.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "khg-width" / "solvers"


_SHA: dict[tuple[str, float, int], str] = {}


def _sha256(path: str) -> str:
    st = os.stat(path)
    key = (os.path.realpath(path), st.st_mtime, st.st_size)
    if key not in _SHA:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        _SHA[key] = h.hexdigest()
    return _SHA[key]


def _executable(p: str | os.PathLike | None) -> bool:
    return bool(p) and os.path.isfile(p) and os.access(p, os.X_OK)


def _manifest(dest: Path, tool: str) -> dict:
    try:
        data = json.loads((dest / "solvers.json").read_text())
        entry = data.get(tool)
        return entry if isinstance(entry, dict) else {}
    except (OSError, ValueError):
        return {}


def _info(tool: str, path: str, how: str, dest: Path | None) -> SolverInfo:
    entry = _manifest(dest, tool) if dest is not None else {}
    sha = _sha256(path)
    commit = entry.get("commit", "unknown") if entry.get("sha256") in (None, sha) else "unknown"
    return SolverInfo(name=tool, path=os.path.abspath(path), commit=commit, sha256=sha, how=how,
                      describe=entry.get("describe") if commit != "unknown" else None,
                      go_version=entry.get("go_version") if commit != "unknown" else None)


def find_solvers(env: Mapping[str, str] | None = None) -> dict[str, SolverInfo]:
    """The solvers found, by tool name (``balancedgo``, ``logk``); a tool not found is absent."""
    env = os.environ if env is None else env
    out: dict[str, SolverInfo] = {}
    dests: list[tuple[Path, str]] = []
    if env.get("KHG_WIDTH_SOLVERS"):
        dests.append((Path(env["KHG_WIDTH_SOLVERS"]), "KHG_WIDTH_SOLVERS"))
    dests.append((default_dest(env), "default"))
    for tool, (binary, var) in TOOLS.items():
        explicit = env.get(var)
        if explicit:
            if _executable(explicit):
                parent = Path(explicit).resolve().parent.parent
                out[tool] = _info(tool, explicit, f"env:{var}", parent if (parent / "solvers.json").exists() else None)
            continue  # an explicit variable that points nowhere means "not found", not "search on"
        for dest, how in dests:
            cand = dest / "bin" / binary
            if _executable(cand):
                out[tool] = _info(tool, str(cand), how, dest)
                break
        else:
            found = shutil.which(binary, path=env.get("PATH"))
            if found:
                out[tool] = _info(tool, found, "PATH", None)
    return out
