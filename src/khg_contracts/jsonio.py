"""Layer J (strict JSON), canonical JSON with RFC 8785 numbers, and the domain-separated digest.

DESIGN §2.1, §2.9 and §8.1:

- ``loads``/``load`` parse one JSON document strictly and raise ``ValidationError`` with a J code: J001 not JSON,
  empty or truncated, or objects and arrays nested deeper than ``MAX_DEPTH`` levels; J002 a byte-order mark or
  invalid UTF-8; J003 a duplicate key; J004 NaN or +/-Infinity (also a number that overflows to infinity); J005 a
  lone surrogate; J006 an integer outside +/-(2**53 - 1), however many digits it has; J007 a top level that is not an
  object. ``loads_lines``/``load_lines`` do the same for each line of a ``.jsonl`` file (each line is a document).
- The nesting limit is explicit, so the verdict does not depend on the Python version (the parser's own limit is
  near 1000 levels on 3.10 and 3.11 and far higher on 3.13) and stays well inside what the package's recursive
  walkers process; layer J applies the same limit to objects in memory.
- ``canonical`` writes object keys sorted by code point, no white space, UTF-8, NFC strings, and numbers as RFC 8785
  (ECMAScript ``Number::toString``) serialises them, so ``2.0`` is ``2`` and exponents read ``1e-7`` and ``1e+21``.
  Any depth is written (a structure too deep for the Python stack is written iteratively); a container that holds
  itself is ``ValueError``.
- ``digest(domain, payload) = "sha256:" + hex(SHA-256(UTF-8(domain + "\\n" + canonical(payload))))``.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import unicodedata
from json.encoder import encode_basestring as _quote
from typing import Any, Mapping

from .errors import ValidationError, make_finding

__all__ = [
    "MAX_DEPTH",
    "MAX_SAFE_INTEGER",
    "loads",
    "load",
    "loads_lines",
    "load_lines",
    "canonical",
    "number",
    "digest",
    "hexdigest",
    "nfc",
]

MAX_SAFE_INTEGER = 2 ** 53 - 1
#: A JSON integer literal (no leading zeros) with more digits than this is outside +/-(2^53-1).
_SAFE_DIGITS = len(str(MAX_SAFE_INTEGER))
#: The deepest nesting of objects and arrays accepted in a document or JSONL line (J001 beyond it): the same limit
#: as layer J's for objects in memory, and well inside Python's default recursion limit at two frames a level.
MAX_DEPTH = 256
_BOM = "\ufeff"
_RAW_SURROGATE = re.compile("[\ud800-\udfff]")
_SURROGATE_ESCAPE = re.compile(r"\\u[dD][89a-fA-F][0-9a-fA-F]{2}")


class _Fault(Exception):
    """Internal: a J fault raised inside a json hook, turned into ValidationError by the caller."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str, path: str = "", **info: Any) -> ValidationError:
    return ValidationError.from_findings([make_finding(code, path, message)], **info)


# ------------------------------------------------------------------------------------------------ layer J


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise _Fault("KHG-J003", f"duplicate key {k!r}")
        out[k] = v
    return out


def _constant(name: str) -> Any:
    raise _Fault("KHG-J004", f"non-finite number {name}")


def _excerpt(digits: str) -> str:
    return digits if len(digits) <= 40 else f"{digits[:20]}...{digits[-4:]} ({len(digits)} characters)"


def _int(s: str) -> int:
    # count the digits first: int() refuses a literal of more than sys.get_int_max_str_digits() digits (4300 by
    # default) with a plain ValueError, and every literal of 17 digits or more is out of range anyway
    if len(s) - s.startswith("-") > _SAFE_DIGITS:
        raise _Fault("KHG-J006", f"integer {_excerpt(s)} outside +/-(2^53-1)")
    v = int(s)
    if abs(v) > MAX_SAFE_INTEGER:
        raise _Fault("KHG-J006", f"integer {s} outside +/-(2^53-1)")
    return v


def _float(s: str) -> float:
    v = float(s)
    if math.isinf(v):
        raise _Fault("KHG-J004", f"number {s} overflows to infinity")
    return v


def _has_lone_surrogate(o: Any) -> bool:
    stack = [o]
    while stack:
        x = stack.pop()
        if isinstance(x, str):
            if _RAW_SURROGATE.search(x):
                return True
        elif isinstance(x, list):
            stack.extend(x)
        elif isinstance(x, dict):
            stack.extend(x.keys())
            stack.extend(x.values())
    return False


def _deeper_than_max(doc: Any) -> bool:
    """True when objects and arrays nest deeper than ``MAX_DEPTH`` levels in a parsed document (level by level)."""
    level = [doc]
    for _ in range(MAX_DEPTH):
        level = [v for value in level for v in (value.values() if type(value) is dict else value)
                 if type(v) is dict or type(v) is list]
        if not level:
            return False
    return True


def _too_deep(doc: Any) -> str | None:
    """The JSON pointer of the first object or array of a parsed document nested deeper than ``MAX_DEPTH`` levels,
    depth first in document order (as layer J finds it in an object in memory); None when there is none."""
    stack: list[tuple[Any, Any, int]] = [(doc, None, 0)]
    while stack:
        value, link, depth = stack.pop()
        if depth >= MAX_DEPTH:
            parts: list[str] = []
            while link is not None:
                link, key = link
                parts.append("/" + str(key).replace("~", "~0").replace("/", "~1"))
            return "".join(reversed(parts))
        items = value.items() if isinstance(value, dict) else enumerate(value)
        stack.extend(reversed([(v, (link, k), depth + 1) for k, v in items if isinstance(v, (dict, list))]))
    return None


def _decode(data: str | bytes | bytearray | memoryview) -> str:
    if isinstance(data, str):
        return data
    raw = bytes(data)
    if raw.startswith(b"\xef\xbb\xbf"):
        raise _fail("KHG-J002", "byte-order mark")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise _fail("KHG-J002", f"invalid UTF-8 at byte {e.start}") from None


def _parse(text: str, path: str) -> dict[str, Any]:
    """Parse one document already decoded to text; J findings carry ``path``."""
    if text.startswith(_BOM):
        raise _fail("KHG-J002", "byte-order mark", path)
    if text.strip() == "":
        raise _fail("KHG-J001", "empty document", path)
    try:
        obj = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant, parse_int=_int,
                         parse_float=_float)
    except _Fault as f:
        raise _fail(f.code, str(f), path) from None
    except json.JSONDecodeError as e:
        raise _fail("KHG-J001", f"not JSON: {e.msg} (line {e.lineno}, column {e.colno})", path,
                    lineno=e.lineno, colno=e.colno) from None
    except RecursionError:  # deeper than the parser can go from the caller's stack: deeper than MAX_DEPTH too
        raise _fail("KHG-J001", "nesting too deep", path) from None
    if (_RAW_SURROGATE.search(text) or _SURROGATE_ESCAPE.search(text)) and _has_lone_surrogate(obj):
        raise _fail("KHG-J005", "lone surrogate in a string", path)
    if not isinstance(obj, dict):
        raise _fail("KHG-J007", f"top level is {type(obj).__name__}, not an object", path)
    # a text with no more brackets than MAX_DEPTH cannot nest deeper (a JSONL record line, as a rule): no walk
    if text.count("{") + text.count("[") > MAX_DEPTH and _deeper_than_max(obj):
        raise _fail("KHG-J001", f"nesting deeper than {MAX_DEPTH} levels", path + (_too_deep(obj) or ""))
    return obj


def loads(text: str | bytes | bytearray) -> dict[str, Any]:
    """Parse one JSON document under the layer-J rules; raise ``ValidationError`` (J001-J007)."""
    return _parse(_decode(text), "")


def load(path: str | os.PathLike[str] | Any) -> dict[str, Any]:
    """Read and parse a ``.json`` file (a path, or anything with ``read_bytes()``) under the layer-J rules."""
    return loads(_read(path))


def loads_lines(text: str | bytes | bytearray) -> list[dict[str, Any]]:
    """Parse a ``.jsonl`` text: one object per line; blank lines are skipped. J findings are at ``/lines/<n>``,
    where n counts the non-blank lines from 0 (the addressing of queue and C4 patches, §8.2)."""
    s = _decode(text)
    if s.startswith(_BOM):
        raise _fail("KHG-J002", "byte-order mark")
    if s.strip() == "":
        raise _fail("KHG-J001", "empty document")
    out: list[dict[str, Any]] = []
    for lineno, line in enumerate(s.split("\n"), 1):
        line = line[:-1] if line.endswith("\r") else line
        if not line.strip():
            continue
        try:
            out.append(_parse(line, f"/lines/{len(out)}"))
        except ValidationError as e:
            e.info["index"] = len(out)
            e.info["lineno"] = lineno
            raise
    return out


def load_lines(path: str | os.PathLike[str] | Any) -> list[dict[str, Any]]:
    """Read and parse a ``.jsonl`` file under the layer-J rules."""
    return loads_lines(_read(path))


def _read(path: Any) -> bytes:
    if hasattr(path, "read_bytes"):
        return path.read_bytes()
    with open(path, "rb") as fh:
        return fh.read()


# ------------------------------------------------------------------------------------------------ canonical JSON


def nfc(s: str) -> str:
    """The string in Unicode Normalization Form C."""
    return unicodedata.normalize("NFC", s)


def number(x: int | float) -> str:
    """A JSON number as RFC 8785 serialises it (ECMAScript ``Number::toString``); bools are refused."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise TypeError(f"not a JSON number: {x!r}")
    if isinstance(x, int):
        if abs(x) > MAX_SAFE_INTEGER:  # str() of an int beyond 4300 digits is itself a ValueError: name its size
            text = str(x) if x.bit_length() <= 256 else f"of {x.bit_length()} bits"
            raise _fail("KHG-J006", f"integer {text} outside +/-(2^53-1)")
        return str(x)
    if math.isnan(x) or math.isinf(x):
        raise _fail("KHG-J004", f"non-finite number {x!r}")
    if x == 0:
        return "0"  # also -0
    if x < 0:
        return "-" + number(-x)
    mant, _, exp = repr(x).lower().partition("e")  # shortest round-trip digits, as ECMAScript selects them
    ip, _, fp = mant.partition(".")
    digits = (ip + fp).lstrip("0")
    e = (int(exp) if exp else 0) - len(fp)  # value = int(digits) * 10**e
    while digits.endswith("0"):
        digits = digits[:-1]
        e += 1
    k = len(digits)
    n = k + e  # value = 0.d1...dk * 10**n
    if k <= n <= 21:
        return digits + "0" * (n - k)
    if 0 < n <= 21:
        return digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + digits
    e1 = n - 1
    return (digits if k == 1 else digits[0] + "." + digits[1:]) + "e" + ("+" if e1 >= 0 else "-") + str(abs(e1))


def _items(o: Mapping[str, Any]) -> list[tuple[str, Any]]:
    """The members of an object with NFC keys, in code-point key order (S020 when two keys normalise to one), as
    ``_write`` writes them."""
    items: dict[str, Any] = {}
    for k, v in o.items():
        if not isinstance(k, str):
            raise TypeError(f"object key {k!r} is not a string")
        nk = nfc(k)
        if nk in items:
            raise _fail("KHG-S020", f"two keys normalise to {nk!r}")
        items[nk] = v
    return [(k, items[k]) for k in sorted(items)]  # code-point order


def _scalar(o: Any) -> str:
    if o is None:
        return "null"
    if o is True:
        return "true"
    if o is False:
        return "false"
    if isinstance(o, str):
        return _quote(nfc(o))
    if isinstance(o, (int, float)):
        return number(o)
    raise TypeError(f"not JSON: {type(o).__name__}")


def _write(o: Any, out: list[str]) -> None:
    """The canonical text of ``o``, recursively (the fast path; ``_write_deep`` when the stack runs out)."""
    if o is None:
        out.append("null")
    elif o is True:
        out.append("true")
    elif o is False:
        out.append("false")
    elif isinstance(o, str):
        out.append(_quote(nfc(o)))
    elif isinstance(o, (int, float)):
        out.append(number(o))
    elif isinstance(o, Mapping):
        items: dict[str, Any] = {}
        for k, v in o.items():
            if not isinstance(k, str):
                raise TypeError(f"object key {k!r} is not a string")
            nk = nfc(k)
            if nk in items:
                raise _fail("KHG-S020", f"two keys normalise to {nk!r}")
            items[nk] = v
        out.append("{")
        for i, k in enumerate(sorted(items)):  # code-point order
            if i:
                out.append(",")
            out.append(_quote(k))
            out.append(":")
            _write(items[k], out)
        out.append("}")
    elif isinstance(o, (list, tuple)):
        out.append("[")
        for i, x in enumerate(o):
            if i:
                out.append(",")
            _write(x, out)
        out.append("]")
    else:
        raise TypeError(f"not JSON: {type(o).__name__}")


def _write_deep(obj: Any, out: list[str]) -> None:
    """The text ``_write`` gives, with an explicit stack, so any depth is written; a container that holds itself
    (which the recursive writer meets as a RecursionError) is ``ValueError``."""
    stack: list[tuple[Any, str, int]] = []  # (the members or items still to write, the closing text, the id)
    open_ids: set[int] = set()

    def enter(o: Any) -> bool:
        if not isinstance(o, (Mapping, list, tuple)):
            out.append(_scalar(o))
            return False
        if id(o) in open_ids:
            raise ValueError("not JSON: a container holds itself")
        open_ids.add(id(o))
        if isinstance(o, Mapping):
            out.append("{")
            stack.append((iter(_items(o)), "}", id(o)))
        else:
            out.append("[")
            stack.append((iter(o), "]", id(o)))
        return True

    enter(obj)
    while stack:
        members, closer, oid = stack[-1]
        for member in members:
            if closer == "}":
                out.append(_quote(member[0]) + ":")
                member = member[1]
            if enter(member):
                break
            out.append(",")
        else:  # every member written: close, replacing the separator after the last one
            stack.pop()
            open_ids.discard(oid)
            if out[-1] == ",":
                out[-1] = closer
            else:
                out.append(closer)
            if stack:
                out.append(",")


def canonical(obj: Any) -> str:
    """The canonical JSON text of ``obj``: code-point key order, no white space, NFC strings, RFC 8785 numbers."""
    out: list[str] = []
    try:
        _write(obj, out)
    except RecursionError:  # nested deeper than the Python stack allows: the same text, iteratively
        out = []
        _write_deep(obj, out)
    return "".join(out)


def _hash(domain: str, payload: Any) -> str:
    if not isinstance(domain, str) or not domain or "\n" in domain:
        raise ValueError(f"bad digest domain {domain!r}")
    try:
        data = (domain + "\n" + canonical(payload)).encode("utf-8")
    except UnicodeEncodeError:
        raise _fail("KHG-J005", "lone surrogate in a string") from None
    return hashlib.sha256(data).hexdigest()


def digest(domain: str, payload: Any) -> str:
    """``"sha256:" + hex(SHA-256(UTF-8(domain + "\\n" + canonical(payload))))`` (§2.9)."""
    return "sha256:" + _hash(domain, payload)


def hexdigest(domain: str, payload: Any) -> str:
    """The 64 hex digits of ``digest`` without the ``sha256:`` prefix (derived node ids use a prefix of it)."""
    return _hash(domain, payload)
