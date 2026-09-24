"""The canonical form of C1 records and containers (DESIGN §2.1, §2.2, §2.8.1, §7).

``normalize`` writes a record in canonical form without checking it (P3a normalises, then validates):

- every string and object key in NFC; a ``lang`` tag in lower case; a time literal without calendar gets
  ``gregorian`` when its written year is 1583 or later (earlier years must state it: S006);
- a hyperedge gets the defaults ``rank: "normal"`` and ``visibility: "visible"``; its bindings are sorted in
  canonical binding order (role, position, canonical value); its evidence is sorted by id, and each evidence
  record's ``supports`` is sorted, defaulting to every bid (what ``put`` writes);
- the ``derived`` cache is dropped.

An evidence record supports what its bids held **in the first version that carries it** (§2.8.1), so an omitted
``supports`` of evidence that an earlier version already carries is not "every bid" of the later version: it is
what the evidence resolved to where it was first written. ``carried_supports`` (the versions of one hyperedge,
oldest first) and ``resolve_supports`` (the records of a history container) write those out before ``normalize``
defaults the rest; ``canonical_container`` does so for history containers, and the version rule, ``put`` and
``load`` read omitted ``supports`` the same way.

A canonical container has the header, then the records in canonical order: embedded ``relation-schema``
documents, then entities by id, then hyperedges by id, and by version in history containers.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .. import jsonio
from ._common import SchemaLike, nfc_deep
from .values import canonical_value

__all__ = [
    "KIND_ORDER",
    "STORE_FIELDS",
    "binding_sort_key",
    "canonical_container",
    "carried_supports",
    "decision_view",
    "normalize",
    "record_sort_key",
    "resolve_supports",
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


def _version(record: Mapping[str, Any]) -> int:
    """A record's version number: an integer, or an integral float as canonical JSON writes it (F10: ``2.0`` is
    ``2``); 0 for anything else."""
    v = record.get("version")
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def record_sort_key(record: Mapping[str, Any]) -> tuple[int, str, int]:
    """Canonical record order: relation-schema documents, entities, hyperedges; then id; then version."""
    rid = record.get("id")
    return (KIND_ORDER.get(record.get("kind"), len(KIND_ORDER)), rid if isinstance(rid, str) else "",
            _version(record))


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
        bids = _bids(r)
        for e in ev:
            if isinstance(e, dict):
                if "supports" not in e:
                    e["supports"] = list(bids)
                if isinstance(e["supports"], list):
                    e["supports"] = _sorted(e["supports"], None)
        r["evidence"] = _sorted(ev, lambda e: str(e.get("id", "")) if isinstance(e, Mapping) else "")
    return r


def _bids(record: Mapping[str, Any]) -> list[str]:
    """The string bids of a hyperedge, in binding order: what an omitted ``supports`` means where it is written."""
    bs = record.get("bindings")
    return [b["bid"] for b in bs if isinstance(b, Mapping) and isinstance(b.get("bid"), str)] \
        if isinstance(bs, list) else []


def carried_supports(versions: Iterable[Any]) -> list[Any]:
    """The versions of one hyperedge, oldest first, with ``supports`` written out on the evidence records that a
    later version carries without it (§2.8.1): such a record supports what it resolved to in the first version that
    carries it, that version's ``supports`` or else every bid of that version. The first carrier keeps its
    omission (``normalize`` gives it every bid). A version is copied only when something is filled in, and what
    cannot be read (an evidence id that is not a string, ``supports`` that is not a list) is left as it is."""
    first: dict[str, list[Any] | None] = {}
    out: list[Any] = []
    for version in versions:
        ev = version.get("evidence") if isinstance(version, Mapping) else None
        filled: list[Any] | None = None
        for k, e in enumerate(ev if isinstance(ev, list) else []):
            eid = e.get("id") if isinstance(e, Mapping) else None
            if not isinstance(eid, str):
                continue
            eid = jsonio.nfc(eid)
            if eid not in first:
                supports = e["supports"] if "supports" in e else _bids(version)
                first[eid] = list(supports) if isinstance(supports, list) else None
            elif "supports" not in e and first[eid] is not None:
                if filled is None:
                    filled = list(ev)  # type: ignore[arg-type]
                filled[k] = {**e, "supports": list(first[eid])}  # type: ignore[arg-type]
        out.append(version if filled is None else {**version, "evidence": filled})
    return out


def resolve_supports(records: Iterable[Any]) -> list[Any]:
    """The records of a history container, in their order, with the ``supports`` of carried evidence written out
    (``carried_supports`` over the versions of each hyperedge id, by version number)."""
    out = list(records)
    groups: dict[str, list[int]] = {}
    for i, r in enumerate(out):
        if isinstance(r, Mapping) and r.get("kind") == "hyperedge" and isinstance(r.get("id"), str):
            groups.setdefault(jsonio.nfc(r["id"]), []).append(i)
    for idx in groups.values():
        if len(idx) > 1:
            idx = sorted(idx, key=lambda i: _version(out[i]))  # stable: equal versions keep their order
            for i, r in zip(idx, carried_supports([out[i] for i in idx]), strict=True):
                out[i] = r
    return out


def canonical_container(container: Mapping[str, Any]) -> dict[str, Any]:
    """``{"header", "records"}`` with the header in NFC and the records normalised and in canonical order. In a
    history container, evidence carried without ``supports`` keeps what it supported where it was first written
    (``resolve_supports``)."""
    records = container.get("records")
    if not isinstance(records, list):
        records = []
    header = container.get("header")
    if isinstance(header, Mapping) and header.get("content") == "history":
        records = resolve_supports(records)
    normal = [normalize(r) if isinstance(r, Mapping) else r for r in records]
    return {"header": nfc_deep(header),
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
