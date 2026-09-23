"""The canonical form of C1 records and containers (DESIGN §2.1, §2.2, §2.8.1, §7).

``normalize`` writes a record in canonical form without checking it (P3a normalises, then validates):

- every string and object key in NFC; a ``lang`` tag in lower case; a time literal without calendar gets
  ``gregorian`` when its written year is 1583 or later (earlier years must state it: S006);
- a hyperedge gets the defaults ``rank: "normal"`` and ``visibility: "visible"``; its bindings are sorted in
  canonical binding order (role, position, canonical value); its evidence is sorted by id, and each evidence
  record's ``supports`` is sorted, defaulting to every bid (what ``put`` writes);
- the ``derived`` cache is dropped.

A canonical container has the header, then the records in canonical order: embedded ``relation-schema``
documents, then entities by id, then hyperedges by id, and by version in history containers.
"""
from __future__ import annotations

from typing import Any, Mapping

from .. import jsonio
from ._common import SchemaLike, nfc_deep
from .values import canonical_value

__all__ = [
    "KIND_ORDER",
    "STORE_FIELDS",
    "binding_sort_key",
    "canonical_container",
    "decision_view",
    "normalize",
    "record_sort_key",
]

KIND_ORDER = {"relation-schema": 0, "entity": 1, "hyperedge": 2}
#: The fields a store assigns (transaction time, §2.6); ``decision_view`` drops them.
STORE_FIELDS = ("version", "recorded_at", "recorded_by")


def _text(obj: Any) -> str:
    try:
        return jsonio.canonical(obj)
    except (TypeError, ValueError):
        return repr(obj)


def binding_sort_key(binding: Mapping[str, Any]) -> tuple[str, float, str]:
    """Canonical binding order: role, then position (absent sorts as 0), then the canonical value's JSON text."""
    role = binding.get("role")
    pos = binding.get("position", 0)
    value = binding.get("value")
    return (role if isinstance(role, str) else "",
            pos if isinstance(pos, (int, float)) and not isinstance(pos, bool) else 0,
            _text(canonical_value(value, strict=False)) if isinstance(value, Mapping) else _text(value))


def record_sort_key(record: Mapping[str, Any]) -> tuple[int, str, int]:
    """Canonical record order: relation-schema documents, entities, hyperedges; then id; then version."""
    rid, version = record.get("id"), record.get("version", 0)
    return (KIND_ORDER.get(record.get("kind"), len(KIND_ORDER)), rid if isinstance(rid, str) else "",
            version if isinstance(version, int) and not isinstance(version, bool) else 0)


def _sorted(items: list[Any], key: Any) -> list[Any]:
    try:
        return sorted(items, key=key)
    except TypeError:
        return items


def normalize(record: Mapping[str, Any], schema: SchemaLike | None = None) -> dict[str, Any]:
    """The canonical form of a record (a new dict); nothing is checked and nothing raises on bad content.

    ``schema`` is accepted for the §10.2 signature; the canonical form does not depend on it.
    """
    if not isinstance(record, Mapping):
        raise TypeError(f"a record is an object, not {type(record).__name__}")
    r: dict[str, Any] = nfc_deep(record)
    r.pop("derived", None)
    if r.get("kind") != "hyperedge":
        return r
    r.setdefault("rank", "normal")
    r.setdefault("visibility", "visible")
    bs = r.get("bindings")
    if isinstance(bs, list):
        for b in bs:
            if isinstance(b, dict) and isinstance(b.get("value"), Mapping):
                b["value"] = canonical_value(b["value"], strict=False)
        r["bindings"] = _sorted(bs, lambda b: binding_sort_key(b) if isinstance(b, Mapping) else ("", 0, ""))
    ev = r.get("evidence")
    if isinstance(ev, list):
        bids = [b.get("bid") for b in bs if isinstance(b, Mapping)] if isinstance(bs, list) else []
        for e in ev:
            if isinstance(e, dict):
                if "supports" not in e:
                    e["supports"] = [x for x in bids if isinstance(x, str)]
                if isinstance(e["supports"], list):
                    e["supports"] = _sorted(e["supports"], None)
        r["evidence"] = _sorted(ev, lambda e: str(e.get("id", "")) if isinstance(e, Mapping) else "")
    return r


def canonical_container(container: Mapping[str, Any]) -> dict[str, Any]:
    """``{"header", "records"}`` with the header in NFC and the records normalised and in canonical order."""
    records = container.get("records")
    if not isinstance(records, list):
        records = []
    normal = [normalize(r) if isinstance(r, Mapping) else r for r in records]
    return {"header": nfc_deep(container.get("header")),
            "records": _sorted(normal, lambda r: record_sort_key(r) if isinstance(r, Mapping) else (99, "", 0))}


def decision_view(record: Mapping[str, Any]) -> dict[str, Any]:
    """What ``decision_hash`` covers (§7): the canonical record without the store-assigned fields ``version``,
    ``recorded_at``, ``recorded_by``, evidence ``recorded_at`` and ``derived``. ``event_hash`` stays."""
    r = normalize(record)
    for f in STORE_FIELDS:
        r.pop(f, None)
    for e in r.get("evidence", []) if isinstance(r.get("evidence"), list) else []:
        if isinstance(e, dict):
            e.pop("recorded_at", None)
    return r
