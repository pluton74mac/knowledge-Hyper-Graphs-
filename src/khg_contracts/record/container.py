"""C1 containers on disk: ``.khg.json`` and ``.khg.jsonl`` (DESIGN §2.1, §7, §10.2).

- ``.khg.json`` is ``{"header": {...}, "records": [...]}``; ``.khg.jsonl`` has the header on line 1, then one
  record per line, so it streams. ``read_container`` and ``write_container`` dispatch on the suffix only (DESIGN
  §14 ruling 4): ``.json`` is one JSON document, ``.jsonl`` is JSONL, and any other suffix raises ``ValueError``;
  ``write_container`` also raises ``ValueError`` when ``format`` is not the one the suffix names.
- ``serialize`` writes the canonical container: records normalised and in canonical order. JSONL is one canonical
  JSON text per line. JSON wraps the same canonical texts, one record per line, in an indented object.
- ``write_container`` runs the V and C checks first and raises ``ValidationError`` (V001, C codes).
- ``container_sha256`` is the plain SHA-256 of the canonical ``.khg.jsonl`` text (the queue's ``base``).
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import secrets
import stat
from typing import Any, Iterator, Mapping

from .. import jsonio
from ..errors import ValidationError, make_finding
from ._structure import structure_findings, version_findings
from .canonical import canonical_container

__all__ = [
    "FORMATS",
    "SUFFIXES",
    "check_container",
    "container_sha256",
    "iter_jsonl",
    "read_container",
    "serialize",
    "write_container",
]

FORMATS = ("jsonl", "json")
#: The container layout each file suffix names (§14 ruling 4); no other suffix is read or written.
SUFFIXES = {".jsonl": "jsonl", ".json": "json"}


def _name(path: Any) -> str:
    return str(getattr(path, "name", None) or os.fspath(path))


def _format_of(path: Any) -> str:
    """The layout the suffix of ``path`` names: ``.json`` one JSON document, ``.jsonl`` JSONL; ``ValueError``
    for any other suffix, so that nothing is written that ``read_container`` would misread."""
    name = _name(path)
    for suffix, fmt in SUFFIXES.items():
        if name.endswith(suffix):
            return fmt
    raise ValueError(f"{name!r}: a container file name ends in .json (one JSON document) or .jsonl (JSONL)")


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
    """Read a ``.khg.json`` or ``.khg.jsonl`` container (by suffix; ``ValueError`` for any other suffix) under
    layer J, then the version gate (V001). The container is returned as written, not normalised."""
    fmt = _format_of(path)
    raw = _read_bytes(path)
    if fmt == "jsonl":
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


def _utf8(text: str) -> bytes:
    """``text`` in UTF-8; a lone surrogate (possible in a container built in memory, never in a parsed one) is J005,
    as ``jsonio.digest`` reports it."""
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError:
        raise ValidationError.from_findings([make_finding("KHG-J005", "", "lone surrogate in a string: the text "
                                                                          "is not UTF-8")]) from None


def check_container(container: Any) -> list[dict[str, str]]:
    """The findings of layers V and C on a container: V001 alone (it stops the run), else the record schema's
    findings; [] when both pass."""
    return version_findings(container) or structure_findings(container)


def write_container(container: Mapping[str, Any], path: Any, *, format: str | None = None) -> None:
    """Write a container in canonical order after the V and C checks (``ValidationError`` with V001 or C codes, and
    J005 for a lone surrogate, which UTF-8 cannot hold; nothing is written then). The suffix of ``path`` names the
    layout (``.json`` or ``.jsonl``; any other suffix is ``ValueError``); ``format`` (``"jsonl"`` or ``"json"``)
    may restate it, and a ``format`` the suffix does not name is ``ValueError``. The file is replaced atomically. It
    gets the permissions the umask allows, or keeps the mode of an existing regular file at ``path``, as the CLI's
    outputs do (``cli._staged``)."""
    implied = _format_of(path)
    if format is not None and format not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}, not {format!r}")
    if format is not None and format != implied:
        raise ValueError(f"format {format!r} does not fit {_name(path)!r}, whose suffix names {implied}")
    findings = check_container(container)
    if any(f["severity"] == "error" for f in findings):
        raise ValidationError.from_findings(findings)
    data = _utf8(serialize(container, format=implied))  # J005 before any file is made
    target = os.fspath(path)
    # open(..., "x"), not tempfile.mkstemp, whose mode 0600 would survive the rename (as in cli._write_file)
    tmp = os.path.join(os.path.dirname(target) or ".", f".khg-{secrets.token_hex(8)}.tmp")
    fh = open(tmp, "xb")
    try:
        with fh:
            fh.write(data)
        _keep_mode(tmp, target)
        os.replace(tmp, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


def _keep_mode(tmp: str, target: str) -> None:
    """Give ``tmp`` the mode of an existing regular file at ``target`` (a private or read-only file stays so, as
    under shell redirection); a new file keeps the umask's mode."""
    try:
        st = os.stat(target)
    except FileNotFoundError:
        return
    if stat.S_ISREG(st.st_mode):
        os.chmod(tmp, stat.S_IMODE(st.st_mode))


def container_sha256(container: Mapping[str, Any]) -> str:
    """``sha256:`` + the plain SHA-256 of the canonical ``.khg.jsonl`` text (the header line, then the records in
    canonical order): the queue header's ``base.sha256``. A lone surrogate is J005."""
    return "sha256:" + hashlib.sha256(_utf8(serialize(container, format="jsonl"))).hexdigest()
