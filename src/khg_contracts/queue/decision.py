"""What an ``accept`` records (DESIGN §7): the versions it read and wrote, and ``decision_hash``.

``decision_hash`` is ``digest("khg-decision/1", [{id, version, record: decision_view(v)}])`` over the written
versions, sorted by id. ``decision_view`` drops the store-assigned fields (``version``, ``recorded_at``,
``recorded_by``, evidence ``recorded_at``, ``derived``) and keeps ``event_hash``, so the clock never changes the
hash. ``Queue.accept`` and ``replay`` both compute it here.
"""
from __future__ import annotations

import copy
from typing import Any, Iterable, Mapping

from .. import jsonio
from ..errors import NotFound
from ..record import decision_view

__all__ = ["DOMAIN", "accepted_record", "decision_hash", "read_versions", "written_versions"]

DOMAIN = "khg-decision/1"


def accepted_record(item: Mapping[str, Any], fact_id: str) -> dict[str, Any]:
    """The record an accept stores: the payload with ``id`` replaced and ``status`` set to asserted, nothing else
    changed."""
    record = copy.deepcopy(dict(item["payload"]))
    record["id"] = fact_id
    record["status"] = "asserted"
    return record


def read_versions(store: Any, ids: Iterable[Any]) -> list[dict[str, Any]]:
    """``[{id, version}]``, sorted by id: the current versions the store holds of ``ids`` before a write."""
    out = {}
    for rid in ids:
        if not isinstance(rid, str) or rid in out:
            continue
        current = store.get(rid)
        version = current.get("version") if isinstance(current, Mapping) else None
        if isinstance(version, int) and not isinstance(version, bool):
            out[rid] = version
    return [{"id": rid, "version": out[rid]} for rid in sorted(out)]


def written_versions(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    """``[{id, version}]``, sorted by id: the versions a ``put`` wrote (its receipt, without the no-ops)."""
    rows = [(r[0], r[1]) for r in receipt.get("records", []) if len(r) < 3 or r[2] != "noop"]
    return [{"id": rid, "version": version} for rid, version in sorted(rows)]


def decision_hash(store: Any, written: Iterable[Mapping[str, Any]]) -> str:
    """``khg-decision/1`` over the written versions, read back from ``store``."""
    views = []
    for w in sorted(written, key=lambda x: x["id"]):
        record = store.get(w["id"])
        if not isinstance(record, Mapping) or record.get("version") != w["version"]:
            record = store.get(w["id"], version=w["version"])
        if not isinstance(record, Mapping):
            raise NotFound(f"the store does not return {w['id']} version {w['version']}")
        views.append({"id": w["id"], "version": w["version"], "record": decision_view(record)})
    return jsonio.digest(DOMAIN, views)
