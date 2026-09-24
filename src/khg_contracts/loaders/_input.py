"""What the loaders accept (DESIGN §5): reading a HIF file, the ``validate=`` modes and the refusals of every mode.

- A ``str`` or ``os.PathLike`` is a path, read under the layer-J rules; JSON text must be parsed first with
  ``jsonio.loads``. A mapping is copied as JSON (objects and arrays), so the caller's document is never changed.
- ``validate="profile"`` runs layers J, V, H, R and P (not S or D, which need the relation schema and run in
  ``from_hif``); ``"convention"`` runs the role-convention pipeline (J, H, R); ``"none"`` runs nothing, but a document
  without the HIF structure the loaders map is refused with layer H's codes.
- In every mode the loaders refuse duplicate node or edge declarations (D001), ``asc`` files (P007) and directed
  files with an incidence that lacks direction (P010).

A refused input raises ``LoaderError`` (§10.2); it is also a ``ValidationError``, and ``info["findings"]`` holds the
findings.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

from .. import jsonio
from ..errors import LoaderError, ValidationError, make_finding
from ._common import VALIDATE_MODES, tkey

__all__ = ["InputRefused", "bid_ok", "check_document", "copy_json", "is_profile", "read_document"]

_TOP = frozenset({"network-type", "metadata", "incidences", "nodes", "edges"})
_INCIDENCE = frozenset({"edge", "node", "weight", "direction", "attrs"})
_NODE = frozenset({"node", "weight", "attrs"})
_EDGE = frozenset({"edge", "weight", "attrs"})
_NETWORK_TYPES = ("undirected", "directed", "asc")
_BID_CHARS = frozenset("0123456789")


class InputRefused(LoaderError, ValidationError):
    """A loader refuses its input: a ``LoaderError`` that is also a ``ValidationError``; ``info["findings"]``."""


def copy_json(o: Any) -> Any:
    """A deep copy of a JSON value, with every mapping as a dict and every tuple as a list."""
    if isinstance(o, Mapping):
        return {k: copy_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [copy_json(v) for v in o]
    return o


def read_document(hif: Any) -> dict[str, Any]:
    """The HIF document of a loader argument: a path read under the layer-J rules, or a copy of a mapping."""
    if isinstance(hif, (str, os.PathLike)):
        try:
            return jsonio.load(hif)
        except ValidationError as e:
            raise InputRefused.from_findings(e.info.get("findings") or [make_finding(e.code or "KHG-J001")]) \
                from None
    if isinstance(hif, Mapping):
        return copy_json(hif)
    raise TypeError(f"hif is a mapping or a path, not {type(hif).__name__} (parse JSON text with jsonio.loads)")


def check_document(doc: dict[str, Any], validate: str) -> None:
    """Run the ``validate`` mode, then the refusals of every mode; raise ``InputRefused`` on the first failure."""
    if validate not in VALIDATE_MODES:
        raise ValueError(f"validate must be one of {', '.join(VALIDATE_MODES)}, not {validate!r}")
    if validate == "none":
        if not _loadable(doc):
            from ..validate.layers import h
            found = h.findings(doc) or [make_finding("KHG-H009", "", "not a HIF document the loaders can map")]
            raise InputRefused.from_findings(found)
    else:
        from ..hif import PROFILE_STEPS
        from ..validate.runner import run
        if validate == "profile":
            report = run(doc, kind="hif", steps=PROFILE_STEPS, stop="first")
        else:
            report = run(doc, kind="role-convention", stop="first")
        if not report.ok:
            raise InputRefused.from_findings(report.findings)
    _refusals(doc)


def is_profile(doc: Mapping[str, Any], validate: str) -> bool:
    """True when the document is a ``khg-hif`` file: validated as one, or declaring the profile with a well-formed
    ``khg-bid`` on every incidence, unique within its edge (records are then keyed by bid)."""
    if validate == "profile":
        return True
    metadata = doc.get("metadata")
    if not isinstance(metadata, Mapping) or "khg-profile" not in metadata:
        return False
    seen: set[tuple[Any, Any]] = set()
    for r in doc["incidences"]:
        key = (tkey(r["edge"]), (r.get("attrs") or {}).get("khg-bid"))
        if not bid_ok(key[1]) or key in seen:
            return False
        seen.add(key)
    return True


def bid_ok(bid: Any) -> bool:
    """A ``khg-bid``: ``b`` then a positive integer without leading zeros (the profile's pattern)."""
    return (isinstance(bid, str) and len(bid) > 1 and bid[0] == "b" and bid[1] != "0"
            and set(bid[1:]) <= _BID_CHARS)


def _refusals(doc: Mapping[str, Any]) -> None:
    found = []
    for key, idf in (("nodes", "node"), ("edges", "edge")):
        seen: set[Any] = set()
        for j, item in enumerate(doc.get(key) or []):
            k = tkey(item[idf])
            if k in seen:
                found.append(make_finding("KHG-D001", f"/{key}/{j}/{idf}", f"{idf} {item[idf]!r} is declared twice"))
            seen.add(k)
    if found:
        raise InputRefused.from_findings(found)
    if doc.get("network-type") == "asc":
        raise InputRefused.from_findings([make_finding("KHG-P007", "/network-type", "network-type asc is refused")])
    if doc.get("network-type") == "directed":
        found = [make_finding("KHG-P010", f"/incidences/{j}", "a directed file with an incidence without direction")
                 for j, r in enumerate(doc["incidences"]) if "direction" not in r]
        if found:
            raise InputRefused.from_findings(found)


# ------------------------------------------------------------------------------------------------ the shape guard


def _is_id(x: Any) -> bool:
    return isinstance(x, (str, int)) and not isinstance(x, bool)


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _item_ok(item: Any, ids: tuple[str, ...], allowed: frozenset[str]) -> bool:
    if not isinstance(item, dict) or not set(item) <= allowed or not all(_is_id(item.get(k)) for k in ids):
        return False
    if "weight" in item and not _is_number(item["weight"]):
        return False
    if "attrs" in item and not isinstance(item["attrs"], dict):
        return False
    return "direction" not in item or item["direction"] in ("head", "tail")


def _loadable(doc: Any) -> bool:
    """True when ``doc`` has the structure of the vendored HIF schema, which is what the loaders map."""
    if not isinstance(doc, dict) or not set(doc) <= _TOP:
        return False
    if "network-type" in doc and doc["network-type"] not in _NETWORK_TYPES:
        return False
    if "metadata" in doc and not isinstance(doc["metadata"], dict):
        return False
    incidences = doc.get("incidences")
    if not isinstance(incidences, list) or not all(_item_ok(i, ("edge", "node"), _INCIDENCE) for i in incidences):
        return False
    for key, idf, allowed in (("nodes", "node", _NODE), ("edges", "edge", _EDGE)):
        if key in doc and not (isinstance(doc[key], list) and all(_item_ok(x, (idf,), allowed) for x in doc[key])):
            return False
    return True
