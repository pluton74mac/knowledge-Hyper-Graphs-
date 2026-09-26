"""Layer V: the version gate (DESIGN §8.1, §11). The format or profile id selects the schemas.

A reader accepts its own major version with a minor no newer than its own (writers stamp the lowest version whose
features a document uses). V001 otherwise, and a V finding stops the run:

| Kind | Id | Accepted |
|---|---|---|
| container | ``header.format`` | ``khg-record/1.0.x`` |
| hif | ``metadata["khg-profile"]`` and ``["khg-record"]`` | ``khg-hif/1.0.x`` and ``1.1.x``, ``khg-record/1.0.x`` |
| schema | ``format`` | ``khg-relation-schema/1.0.x`` |
| queue | ``format`` and ``record_format`` of a ``queue-header`` line 0 | ``khg-queue/1.0.x``, ``khg-record/1.0.x`` |
| item | ``format`` and ``record_format`` of line 0 | ``khg-c4-items/0.0.x`` to ``0.2.x``, ``khg-record/1.0.x`` |

A queue header without ``record_format`` passes V (the queue schema's Q008 reports it), and a HIF file without
``khg-profile`` or ``khg-record`` passes V (layer P reports P001). ``khg-hif/1.1.0`` is ruling 19's minor version and
``khg-c4-items/0.2.0`` ruling 20's. A single record and a role-convention file have no format id. ``detect_kind`` picks
the kind of an input for ``kind="auto"``; the runner reports V001 when it cannot tell.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from ...errors import make_finding
from ...schema.checks import version_findings as schema_version_findings
from ..context import Context

__all__ = ["HEADER_KINDS", "IMPLEMENTED", "LETTER", "OWNER", "detect_kind", "gate", "lone_header", "run"]

LETTER = "V"
OWNER = "W4"
IMPLEMENTED = True

_SEMVER = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
#: The kind of the header line of each JSONL format, and the input kind of its file.
HEADER_KINDS = {"header": "container", "queue-header": "queue", "c4-header": "item"}

Finding = dict[str, str]


def gate(value: Any, name: str, major: int, max_minor: int) -> bool:
    """True when ``value`` is ``<name>/<major>.<minor>.<patch>`` with ``minor <= max_minor``."""
    m = re.fullmatch(re.escape(name) + "/" + _SEMVER, value) if isinstance(value, str) else None
    return bool(m) and int(m.group(1)) == major and int(m.group(2)) <= max_minor


def _v001(path: str, value: Any, want: str) -> Finding:
    return make_finding("KHG-V001", path, f"{value!r} is not {want} (or a version this reader accepts)")


def _line0(doc: Any) -> Mapping[str, Any]:
    return doc[0] if isinstance(doc, list) and doc and isinstance(doc[0], Mapping) else {}


def run(ctx: Context) -> list[Finding]:
    doc, kind = ctx.doc, ctx.kind
    if kind == "container":
        header = doc.get("header") if isinstance(doc, Mapping) else None
        fmt = header.get("format") if isinstance(header, Mapping) else None
        return [] if gate(fmt, "khg-record", 1, 0) else [_v001("/header/format", fmt, "khg-record/1.0.0")]
    if kind == "hif":
        md = doc.get("metadata") if isinstance(doc, Mapping) else None
        md = md if isinstance(md, Mapping) else {}
        out = []
        if "khg-profile" in md and not gate(md["khg-profile"], "khg-hif", 1, 1):  # 1.1: ruling 19
            out.append(_v001("/metadata/khg-profile", md["khg-profile"], "khg-hif/1.1.0"))
        if "khg-record" in md and not gate(md["khg-record"], "khg-record", 1, 0):
            out.append(_v001("/metadata/khg-record", md["khg-record"], "khg-record/1.0.0"))
        return out
    if kind == "schema":
        return schema_version_findings(doc)
    if kind == "queue":
        h = _line0(doc)
        if h.get("kind") != "queue-header":
            return []
        out = []
        if not gate(h.get("format"), "khg-queue", 1, 0):
            out.append(_v001("/lines/0/format", h.get("format"), "khg-queue/1.0.0"))
        # the stamp of the payloads, when the header has one (a missing one is the queue schema's Q008)
        if "record_format" in h and not gate(h["record_format"], "khg-record", 1, 0):
            out.append(_v001("/lines/0/record_format", h["record_format"], "khg-record/1.0.0"))
        return out
    if kind == "item":
        h = _line0(doc)
        if h.get("kind") != "c4-header":
            return []
        out = []
        if not gate(h.get("format"), "khg-c4-items", 0, 2):  # 0.2: ruling 20
            out.append(_v001("/lines/0/format", h.get("format"), "khg-c4-items/0.2.0"))
        # the stamp of the embedded C1 records (a missing one is the draft schema's I002)
        if "record_format" in h and not gate(h["record_format"], "khg-record", 1, 0):
            out.append(_v001("/lines/0/record_format", h["record_format"], "khg-record/1.0.0"))
        return out
    return []


def lone_header(doc: Any) -> bool:
    """True for a JSONL file's header line given alone (an object whose ``kind`` is a header line's, and that is not
    a ``{header, records}`` container): a text of one line parses to it."""
    return isinstance(doc, Mapping) and not ("header" in doc and "records" in doc) and \
        isinstance(doc.get("kind"), str) and doc["kind"] in HEADER_KINDS


def detect_kind(doc: Any) -> str | None:
    """The kind of a parsed input, or None when it cannot be told.

    - lines (a list): by line 0's ``kind``: ``header`` a container, ``queue-header`` a queue, ``c4-header`` C4 items;
    - an object with ``header`` and ``records``: a container;
    - a lone header line (an object whose ``kind`` is one of those three): its file, of that one line (a text of one
      line parses to one object; the runner reads it as the lines of the file);
    - ``kind`` ``relation-schema``: a schema; ``entity`` or ``hyperedge``: a record;
    - an object with ``incidences``, ``nodes``, ``edges``, ``network-type`` or ``metadata`` (HIF): ``hif`` when its
      metadata has ``khg-profile``, else ``role-convention`` when it declares ``role-convention``, else ``hif``.
    """
    if isinstance(doc, list):
        return HEADER_KINDS.get(_line0(doc).get("kind"))
    if not isinstance(doc, Mapping):
        return None
    if "header" in doc and "records" in doc:
        return "container"
    if lone_header(doc):
        return HEADER_KINDS[doc["kind"]]
    k = doc.get("kind")
    if k == "relation-schema":
        return "schema"
    if k in ("entity", "hyperedge"):
        return "record"
    if any(key in doc for key in ("incidences", "nodes", "edges", "network-type", "metadata")):
        md = doc.get("metadata")
        md = md if isinstance(md, Mapping) else {}
        if "khg-profile" not in md and "role-convention" in md:
            return "role-convention"
        return "hif"
    return None
