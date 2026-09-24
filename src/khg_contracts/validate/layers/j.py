"""Layer J: the strict parse (DESIGN §8.1), wired to ``jsonio``.

- A path (``str``, ``os.PathLike`` or a packaged file with ``read_bytes``) is read and parsed: a ``.jsonl`` file line
  by line, anything else as one JSON document. Queue and C4 files are always JSONL.
- Raw ``bytes`` are parsed the same way. For a container, or when the kind is ``auto``, a text with more than one
  JSON value is read as JSONL.
- An object already in memory is checked for what the parser refuses: NaN and +/-Infinity (J004), lone surrogates
  (J005), integers beyond +/-(2^53-1) (J006), a top level (or JSONL line) that is not an object (J007), and values
  or keys that are not JSON at all (J001). Tuples and other mappings are read as JSON arrays and objects. A list is
  read as the lines of a JSONL file; a single object given for a queue or C4 file is read as a file of one line.
- **One nesting limit** for every form of input: a document (or JSONL line) whose objects and arrays nest deeper
  than ``MAX_DEPTH`` (256) levels is J001, at the first value too deep. The limit is checked after parsing text too,
  so a document gets one verdict whether it is given as an object, bytes or a file, and whatever the caller's stack
  depth (the parser's own limit, near 1000 levels from a shallow stack, is not the rule). It is well inside what the
  later layers and the package's recursive walkers process at two interpreter frames a level, so ``validate`` never
  meets Python's recursion limit on what J accepts (it also catches cycles in objects). ``MAX_DEPTH`` and the scan
  live in ``schema.checks``, whose ``check_schema`` applies the same rule.

J reports the first fault only, and a J finding stops the run. JSONL findings are at ``/lines/<n>``.
"""
from __future__ import annotations

import math
import os
import re
from typing import Any, Mapping

from ... import jsonio
from ...errors import ValidationError, make_finding
from ...schema import Schema
from ...schema.checks import MAX_DEPTH, nesting_fault
from ..context import Context
from ..engines import pointer

__all__ = ["IMPLEMENTED", "JSONL_KINDS", "LETTER", "MAX_DEPTH", "OWNER", "is_path", "parse", "run"]

LETTER = "J"
OWNER = "W4"
IMPLEMENTED = True

#: The kinds whose files are always JSONL.
JSONL_KINDS = ("queue", "item")
_SURROGATE = re.compile("[\ud800-\udfff]")

Finding = dict[str, str]


def run(ctx: Context) -> list[Finding]:
    """Parse ``ctx.source`` for ``ctx.kind`` and set ``ctx.doc``; return the J findings."""
    doc, findings = parse(ctx.source, ctx.kind)
    if not findings:
        ctx.doc = doc
    return findings


def is_path(source: Any) -> bool:
    """True for what the validator reads from disk: a ``str``, an ``os.PathLike`` or a packaged file."""
    if isinstance(source, (str, os.PathLike)):
        return True
    return hasattr(source, "read_bytes") and hasattr(source, "name")


def parse(source: Any, kind: str = "auto") -> tuple[Any, list[Finding]]:
    """``(doc, findings)``: the parsed input (a dict, or a list of line dicts) and the J findings; ``doc`` is None
    when there is a finding. An unreadable path raises ``OSError``."""
    if isinstance(source, Schema):
        source = source.doc
    if is_path(source):
        name = os.fspath(source) if isinstance(source, (str, os.PathLike)) else str(source.name)
        return _parse_bytes(_read(source), kind, jsonl=str(name).endswith(".jsonl"))
    if isinstance(source, (bytes, bytearray, memoryview)):
        return _parse_bytes(bytes(source), kind, jsonl=None)
    return _check_object(source, kind)


# ------------------------------------------------------------------------------------------------ text


def _read(source: Any) -> bytes:
    if hasattr(source, "read_bytes"):
        return source.read_bytes()
    with open(os.fspath(source), "rb") as fh:
        return fh.read()


def _findings_of(e: ValidationError) -> list[Finding]:
    found = e.info.get("findings")
    if found:
        return [dict(f) for f in found]
    return [make_finding(e.code or "KHG-J001", "", e.message)]


def _several_values(e: ValidationError) -> bool:
    """True when a one-document parse failed only because the text holds more than one JSON value."""
    return e.codes == ("KHG-J001",) and "Extra data" in e.message


def _parse_bytes(raw: bytes, kind: str, *, jsonl: bool | None) -> tuple[Any, list[Finding]]:
    doc, findings = _parse_text(raw, kind, jsonl=jsonl)
    if findings:
        return None, findings
    if raw.count(b"{") + raw.count(b"[") <= MAX_DEPTH:
        return doc, []  # fewer brackets than levels: the nesting cannot be that deep
    for path, part in ([(f"/lines/{n}", line) for n, line in enumerate(doc)] if isinstance(doc, list) else
                       [("", doc)]):
        deep = nesting_fault(part)
        if deep is not None:
            return None, [make_finding("KHG-J001", path + deep, f"nesting deeper than {MAX_DEPTH} levels")]
    return doc, []


def _parse_text(raw: bytes, kind: str, *, jsonl: bool | None) -> tuple[Any, list[Finding]]:
    try:
        if kind in JSONL_KINDS or jsonl:
            return jsonio.loads_lines(raw), []
        if jsonl is None and kind in ("container", "auto"):
            try:
                return jsonio.loads(raw), []
            except ValidationError as e:
                if not _several_values(e):
                    raise
            return jsonio.loads_lines(raw), []
        return jsonio.loads(raw), []
    except ValidationError as e:
        return None, _findings_of(e)


# ------------------------------------------------------------------------------------------------ objects


def _check_object(obj: Any, kind: str) -> tuple[Any, list[Finding]]:
    if isinstance(obj, (list, tuple)) and kind in (*JSONL_KINDS, "container", "auto"):
        if not obj:
            return None, [make_finding("KHG-J001", "", "empty document: no lines")]
        lines = []
        for n, line in enumerate(obj):
            found, plain = _checked(line, f"/lines/{n}")
            if found:
                return None, found
            lines.append(plain)
        return lines, []
    if isinstance(obj, Mapping) and kind in JSONL_KINDS:
        found, plain = _checked(obj, "/lines/0")
        return (None, found) if found else ([plain], [])
    found, plain = _checked(obj, "")
    return (None, found) if found else (plain, [])


def _checked(obj: Any, path: str) -> tuple[list[Finding], Any]:
    """The J finding of one document (or line) in memory, and the document as plain JSON types."""
    if not isinstance(obj, Mapping):
        return [make_finding("KHG-J007", path, f"top level is {type(obj).__name__}, not an object")], None
    problem, convert = _scan(obj)
    if problem is not None:
        code, link, message = problem
        return [make_finding(code, path + _path(link), message)], None
    return [], _plain(obj) if convert else obj


def _scan(obj: Any) -> tuple[tuple[str, Any, str] | None, bool]:
    """The first J fault in a value, depth first in document order, as ``(code, link, message)`` (``link`` builds
    its path), and whether the value holds tuples or mappings that are not dicts."""
    convert = False
    stack: list[tuple[Any, Any, int]] = [(obj, None, 0)]
    while stack:
        value, link, depth = stack.pop()
        if value is None or isinstance(value, bool):
            continue
        if isinstance(value, str):
            if _SURROGATE.search(value):
                return ("KHG-J005", link, "lone surrogate in a string"), convert
        elif isinstance(value, int):
            if abs(value) > jsonio.MAX_SAFE_INTEGER:
                return ("KHG-J006", link, f"integer {value} outside +/-(2^53-1)"), convert
        elif isinstance(value, float):
            if not math.isfinite(value):
                return ("KHG-J004", link, f"non-finite number {value!r}"), convert
        elif isinstance(value, (Mapping, list, tuple)):
            if depth >= MAX_DEPTH:
                return ("KHG-J001", link, f"nesting deeper than {MAX_DEPTH} levels"), convert
            children: list[tuple[Any, Any, int]] = []
            if isinstance(value, Mapping):
                convert = convert or not isinstance(value, dict)
                for k, v in value.items():
                    if not isinstance(k, str):
                        return ("KHG-J001", link, f"object key {k!r} is not a string"), convert
                    if _SURROGATE.search(k):
                        return ("KHG-J005", (link, k), "lone surrogate in an object key"), convert
                    children.append((v, (link, k), depth + 1))
            else:
                convert = convert or isinstance(value, tuple)
                children = [(v, (link, i), depth + 1) for i, v in enumerate(value)]
            stack.extend(reversed(children))
        else:
            return ("KHG-J001", link, f"a {type(value).__name__} is not a JSON value"), convert
    return None, convert


def _path(link: Any) -> str:
    parts: list[Any] = []
    while link is not None:
        link, key = link
        parts.append(key)
    return pointer(reversed(parts))


def _plain(value: Any) -> Any:
    """A copy with mappings as dicts and tuples as lists (iterative)."""
    out: list[Any] = []
    stack: list[tuple[Any, Any, Any]] = [(value, out, 0)]
    while stack:
        x, parent, key = stack.pop()
        if isinstance(x, Mapping):
            y: Any = dict.fromkeys(x)  # the key order; the values are filled in below
            stack.extend((v, y, k) for k, v in x.items())
        elif isinstance(x, (list, tuple)):
            y = [None] * len(x)
            stack.extend((v, y, i) for i, v in enumerate(x))
        else:
            y = x
        if parent is out:
            out.append(y)
        else:
            parent[key] = y
    return out[0]
