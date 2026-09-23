"""Queue file I/O (DESIGN §7): the lines of a queue, one canonical JSON object per line, and the per-line check
against the packaged queue schema ``khg-queue-1.0.0.schema.json``."""
from __future__ import annotations

import copy
import os
from typing import Any, Mapping

from .. import jsonio
from ..errors import ValidationError
from ..validate import engines
from .model import SCHEMA_ID

__all__ = ["dump_line", "errors", "line_findings", "raise_errors", "read_lines"]

Finding = dict[str, str]


def read_lines(source: Any) -> list[dict[str, Any]]:
    """The lines of a queue file: from a path (``str``, ``os.PathLike`` such as a ``Queue``, or a packaged file),
    raw ``bytes``, or lines already parsed (copied). Parsing follows layer J (``ValidationError`` J001-J007)."""
    if isinstance(source, (bytes, bytearray, memoryview)):
        return jsonio.loads_lines(bytes(source))
    if isinstance(source, (str, os.PathLike)) or hasattr(source, "read_bytes"):
        return jsonio.load_lines(source)
    if isinstance(source, (list, tuple)):
        if not all(isinstance(x, Mapping) for x in source):
            raise TypeError("the lines of a queue are objects")
        return [copy.deepcopy(dict(x)) for x in source]
    raise TypeError(f"a queue is a path, bytes or a list of lines, not {type(source).__name__}")


def dump_line(line: Mapping[str, Any]) -> str:
    """The text of one queue line: canonical JSON (code-point key order, NFC strings, RFC 8785 numbers) and a
    newline."""
    return jsonio.canonical(line) + "\n"


def line_findings(line: Any, *, engine: str = "jsonschema", path: str = "") -> list[Finding]:
    """The queue schema's findings on one line ([] when it is valid); ``path`` prefixes their paths."""
    return engines.findings(SCHEMA_ID, line, engine=engine, path=path)


def errors(findings: list[Finding]) -> list[Finding]:
    """The error findings."""
    return [f for f in findings if f.get("severity") == "error"]


def raise_errors(findings: list[Finding]) -> None:
    """Raise ``ValidationError`` when a finding is an error."""
    if errors(findings):
        raise ValidationError.from_findings(findings)
