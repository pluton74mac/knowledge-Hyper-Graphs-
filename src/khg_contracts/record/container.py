"""C1 containers on disk: ``.khg.json`` and ``.khg.jsonl`` (DESIGN §2.1, §7, §10.2).

- ``.khg.json`` is ``{"header": {...}, "records": [...]}``; ``.khg.jsonl`` has the header on line 1, then one
  record per line, so it streams. ``read_container`` picks the form by suffix (``.jsonl``, else JSON).
- ``serialize`` writes the canonical container: records normalised and in canonical order. JSONL is one canonical
  JSON text per line. JSON wraps the same canonical texts, one record per line, in an indented object.
- ``write_container`` runs the V and C checks first and raises ``ValidationError`` (V001, C codes).
- ``container_sha256`` is the plain SHA-256 of the canonical ``.khg.jsonl`` text (the queue's ``base``).
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from typing import Any, Iterator, Mapping

from .. import jsonio
from ..errors import ValidationError, make_finding
from ._structure import structure_findings, version_findings
from .canonical import canonical_container

__all__ = [
    "FORMATS",
    "check_container",
    "container_sha256",
    "iter_jsonl",
    "read_container",
    "serialize",
    "write_container",
]

FORMATS = ("jsonl", "json")


def _name(path: Any) -> str:
    return str(getattr(path, "name", None) or os.fspath(path))


def _format_of(path: Any) -> str:
    return "jsonl" if _name(path).endswith(".jsonl") else "json"


def _read_bytes(path: Any) -> bytes:
    if hasattr(path, "read_bytes"):
        return path.read_bytes()
    with open(path, "rb") as fh:
        return fh.read()


def _checked(container: dict[str, Any]) -> dict[str, Any]:
    v = version_findings(container)
    if v:
        raise ValidationError.from_findings(v)
    return container


def read_container(path: Any) -> dict[str, Any]:
    """Read a ``.khg.json`` or ``.khg.jsonl`` container (by suffix) under layer J, then the version gate (V001).
    The container is returned as written, not normalised."""
    raw = _read_bytes(path)
    if _format_of(path) == "jsonl":
        lines = jsonio.loads_lines(raw)
        return _checked({"header": lines[0], "records": lines[1:]})
    return _checked(jsonio.loads(raw))


def iter_jsonl(path: Any) -> Iterator[dict[str, Any]]:
    """Stream a ``.khg.jsonl`` file: the header, then each record, one line at a time under layer J (a finding on
    the n-th non-blank line has the path ``/lines/<n>``). Blank lines are skipped; lines end at ``\\n`` only."""
    index = 0
    with (path.open("rb") if hasattr(path, "open") else open(path, "rb")) as fh:
        for lineno, raw in enumerate(fh, 1):  # binary lines end at b"\n" only
            try:
                blank = not raw.decode("utf-8").strip()  # as jsonio.loads_lines skips them
            except UnicodeDecodeError:
                blank = False  # J002 below
            if blank:
                continue
            try:
                record = jsonio.loads(raw.rstrip(b"\n").rstrip(b"\r"))
            except ValidationError as e:
                findings = [dict(f, path=f"/lines/{index}{f.get('path', '')}") for f in e.info.get("findings", [])]
                raise ValidationError.from_findings(findings, index=index, lineno=lineno) from None
            yield record
            index += 1
    if index == 0:
        raise ValidationError.from_findings([make_finding("KHG-J001", "", "empty document")])


def serialize(container: Mapping[str, Any], *, format: str = "jsonl") -> str:
    """The text of the canonical container, without checks: ``jsonl`` (the header line, then one record per line,
    each canonical JSON) or ``json`` (the same canonical texts inside ``{"header": ..., "records": [...]}``)."""
    if format not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}, not {format!r}")
    c = canonical_container(container)
    header = jsonio.canonical(c["header"])
    records = [jsonio.canonical(r) for r in c["records"]]
    if format == "jsonl":
        return "".join(line + "\n" for line in [header, *records])
    if not records:
        return '{\n "header": ' + header + ',\n "records": []\n}\n'
    return '{\n "header": ' + header + ',\n "records": [\n  ' + ",\n  ".join(records) + "\n ]\n}\n"


def check_container(container: Any) -> list[dict[str, str]]:
    """The findings of layers V and C on a container: V001 alone (it stops the run), else the record schema's
    findings; [] when both pass."""
    return version_findings(container) or structure_findings(container)


def write_container(container: Mapping[str, Any], path: Any, *, format: str | None = None) -> None:
    """Write a container in canonical order after the V and C checks (``ValidationError`` with V001 or C codes;
    nothing is written then). ``format`` is ``"jsonl"`` or ``"json"``; by default the suffix decides (``.json``
    gives JSON, anything else JSONL). The file is replaced atomically."""
    findings = check_container(container)
    if any(f["severity"] == "error" for f in findings):
        raise ValidationError.from_findings(findings)
    text = serialize(container, format=format or ("json" if _name(path).endswith(".json") else "jsonl"))
    target = os.fspath(path)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target) or ".", prefix=".khg-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def container_sha256(container: Mapping[str, Any]) -> str:
    """``sha256:`` + the plain SHA-256 of the canonical ``.khg.jsonl`` text (the header line, then the records in
    canonical order): the queue header's ``base.sha256``."""
    return "sha256:" + hashlib.sha256(serialize(container, format="jsonl").encode("utf-8")).hexdigest()
