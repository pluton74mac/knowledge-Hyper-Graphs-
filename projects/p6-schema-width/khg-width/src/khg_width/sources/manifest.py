"""Dataset manifests (``datasets/<family>/<dataset>/MANIFEST.json``; DESIGN §6.1).

``verify(dataset_dir, paths=None)`` hashes the raw files the manifest lists and refuses (``ManifestError``) any
missing file or sha256 mismatch, before any generation reads them. It returns ``{path: sha256}`` for the provenance.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

__all__ = ["ManifestError", "load", "verify", "sha256_file"]


class ManifestError(ValueError):
    """A manifest is missing or unreadable, or a file it lists is missing or differs from its sha256."""


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(dataset_dir: str | os.PathLike) -> dict:
    p = Path(dataset_dir) / "MANIFEST.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except OSError as e:
        raise ManifestError(f"cannot read {p}: {e.strerror or e}") from None
    except ValueError as e:
        raise ManifestError(f"{p} is not JSON: {e}") from None


def verify(dataset_dir: str | os.PathLike, paths: Iterable[str] | None = None) -> dict[str, str]:
    """Check the listed files (all, or ``paths``, e.g. ``raw/properties.srj.json``) against the manifest."""
    root = Path(dataset_dir)
    m = load(root)
    listed = {f["path"]: f for f in m.get("files", [])}
    wanted = list(listed) if paths is None else list(paths)
    out: dict[str, str] = {}
    problems: list[str] = []
    for rel in wanted:
        entry = listed.get(rel)
        if entry is None:
            problems.append(f"{rel}: not listed in {root / 'MANIFEST.json'}")
            continue
        f = root / rel
        if not f.is_file():
            problems.append(f"{rel}: missing (fetch it: {entry.get('source_url', 'see the manifest')})")
            continue
        got = sha256_file(f)
        if got != entry.get("sha256"):
            problems.append(f"{rel}: sha256 {got} differs from the manifest's {entry.get('sha256')}")
            continue
        out[rel] = got
    if problems:
        raise ManifestError("; ".join(problems))
    return out
