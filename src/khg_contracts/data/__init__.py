"""The packaged data files (DESIGN §10.1), read with importlib.resources.

``data/`` is the single source of packaged files: the JSON Schemas (with the vendored HIF schema and its licence),
the code registry, the malformed cases, the fixture set, the role-convention files, the conformance scenarios and the
migration goldens. ``manifest.json`` pins the sha256 of every one of them; ``verify()`` checks it.
"""
from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from typing import TYPE_CHECKING, Any, Iterator

from .. import jsonio

if TYPE_CHECKING:  # pragma: no cover
    from importlib.resources.abc import Traversable

__all__ = [
    "HIF_SCHEMA",
    "HIF_SCHEMA_ID",
    "HIF_SCHEMA_SHA256",
    "HIF_SCHEMA_URL",
    "HIF_LICENSE",
    "MANIFEST",
    "root",
    "path",
    "read_bytes",
    "read_text",
    "load_json",
    "load_jsonl",
    "iter_files",
    "sha256",
    "manifest",
    "verify",
    "hif_schema",
    "schema_documents",
]

#: The vendored HIF schema, unchanged (F2): HIF-standard blob e2105bb at b691a3d, MIT, "HIF development team".
HIF_SCHEMA = "schemas/hif_schema_v0.1.0.json"
HIF_SCHEMA_SHA256 = "sha256:639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196"
HIF_SCHEMA_ID = "https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json"
HIF_SCHEMA_URL = ("https://raw.githubusercontent.com/HIF-org/HIF-standard/"
                  "b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json")
HIF_LICENSE = "schemas/HIF-LICENSE.txt"
MANIFEST = "manifest.json"
_SKIP_SUFFIXES = (".py", ".pyc", ".pyo")


def root() -> Traversable:
    """The ``data/`` directory as a Traversable."""
    return files(__name__)


def path(relpath: str) -> Traversable:
    """A packaged file by its ``/``-separated path relative to ``data/``."""
    node = root()
    for part in relpath.split("/"):
        if part in ("", ".", ".."):
            raise ValueError(f"bad data path {relpath!r}")
        node = node / part
    return node


def read_bytes(relpath: str) -> bytes:
    return path(relpath).read_bytes()


def read_text(relpath: str) -> str:
    return read_bytes(relpath).decode("utf-8")


def load_json(relpath: str) -> dict[str, Any]:
    """A packaged ``.json`` file, parsed under the layer-J rules."""
    return jsonio.loads(read_bytes(relpath))


def load_jsonl(relpath: str) -> list[dict[str, Any]]:
    """A packaged ``.jsonl`` file, one object per line, parsed under the layer-J rules."""
    return jsonio.loads_lines(read_bytes(relpath))


def _walk(node: Traversable, prefix: str) -> Iterator[str]:
    for child in node.iterdir():
        name = child.name
        if name.startswith(".") or name == "__pycache__":
            continue
        rel = f"{prefix}{name}"
        if child.is_dir():
            yield from _walk(child, rel + "/")
        elif not name.endswith(_SKIP_SUFFIXES) and rel != MANIFEST:
            yield rel


def iter_files() -> list[str]:
    """Every packaged data file (not code, caches or the manifest), sorted by path."""
    return sorted(_walk(root(), ""))


def sha256(relpath: str) -> str:
    """``sha256:<hex>`` of a packaged file's bytes."""
    return "sha256:" + hashlib.sha256(read_bytes(relpath)).hexdigest()


def manifest() -> dict[str, Any]:
    """The manifest computed from the files present: ``{"algorithm": "sha256", "files": {path: hash}}``."""
    return {"algorithm": "sha256", "files": {p: sha256(p) for p in iter_files()}}


def verify() -> list[str]:
    """Problems between the packaged files and ``manifest.json`` (missing, changed or unlisted files); [] if none."""
    want = load_json(MANIFEST).get("files", {})
    have = manifest()["files"]
    out = [f"missing: {p}" for p in sorted(set(want) - set(have))]
    out += [f"changed: {p}" for p in sorted(set(want) & set(have)) if want[p] != have[p]]
    out += [f"not in the manifest: {p}" for p in sorted(set(have) - set(want))]
    return out


def hif_schema() -> dict[str, Any]:
    """The vendored HIF schema, after checking its pinned sha256 (raises RuntimeError on a mismatch)."""
    raw = read_bytes(HIF_SCHEMA)
    got = "sha256:" + hashlib.sha256(raw).hexdigest()
    if got != HIF_SCHEMA_SHA256:
        raise RuntimeError(f"the vendored HIF schema hashes to {got}, not {HIF_SCHEMA_SHA256}")
    return jsonio.loads(raw)


def schema_documents() -> dict[str, dict[str, Any]]:
    """Every packaged JSON Schema under its ``$id``: ours under ``tag:`` ids, the vendored HIF schema under its
    https id."""
    out = {HIF_SCHEMA_ID: hif_schema()}
    for rel in iter_files():
        if rel.startswith("schemas/") and rel.endswith(".schema.json"):
            doc = load_json(rel)
            out[doc["$id"]] = doc
    return out


def _dump_manifest() -> str:
    return json.dumps(manifest(), ensure_ascii=False, indent=1) + "\n"
