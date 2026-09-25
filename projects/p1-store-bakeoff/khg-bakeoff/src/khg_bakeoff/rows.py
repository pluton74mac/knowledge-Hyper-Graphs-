"""The natural row layout every adapter shares (DESIGN §3; research 01 §1), and the instant guard (ruling 4).

A hyperedge version is one **fact row** plus one **binding row** per binding (P2 DESIGN §2.10 ``incidence_rows`` plus
the columns the reads filter on); an entity version is one row holding the record as canonical JSON.

- The fact row holds ``relation``, ``rel_kind`` (``fact`` or ``lifecycle``), ``status``, ``status_ref``, ``rank``,
  ``visibility``, ``key_digest``, the four bound-table instants ``s_lo``, ``s_hi``, ``e_lo``, ``e_hi`` (seconds on
  the proleptic Gregorian line; ``record.bounds``), ``n_bindings``, the store fields, and ``payload``: the canonical
  JSON of every other field (evidence, confidence, goal, rank_reason, reason, note, source_text, typed_under,
  extensions).
- The binding row holds ``bid``, ``role``, ``position``, ``direction``, ``value_kind``, ``ref`` (the entity or fact
  id), ``ident`` (the value identity, ``record.identity_key``; None for ``unbound``), ``value_json`` (the value as
  written) and ``extensions`` (canonical JSON).

Query parameters are computed with the same functions, so equality in a backend is C1's value identity.

**Instants** (ruling 4). ``instant(x)`` maps an instant to what an int64 backend stores: ±∞ become the sentinels
±2^62 and a finite instant must satisfy ``|x| <= 2^62 - 2``; ``query_instant(t)`` clamps an ``as_of`` parameter to
``±(2^62 - 1)``, which keeps every comparison with a stored value exact. ``unheld_instants(record, schema)`` lists
the finite instants of a record's bound table outside that range: an int64 backend refuses such a record
(``TableStore.cannot_hold``). PostgreSQL stores ``numeric`` and needs no guard (``numeric_instant``).
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from khg_contracts import jsonio
from khg_contracts.record import NEG_INF, POS_INF, binding_sort_key, bounds, identity_key, key_digest
from khg_contracts.schema import LIFECYCLE_RELATIONS

__all__ = ["BIND_COLS", "ENTITY_COLS", "FACT_COLS", "HEADER_FIELDS", "INT64_HELD", "NEG", "POS", "Pat",
           "assemble", "binding_rows", "entity_row", "fact_row", "instant", "numeric_instant", "prepare",
           "query_instant", "split", "unheld_instants"]

#: The sentinels of -inf and +inf in an int64 backend.
NEG, POS = -(2 ** 62), 2 ** 62
#: The largest magnitude of a finite instant an int64 backend holds (2^62 - 2).
INT64_HELD = 2 ** 62 - 2
#: The record fields a fact row holds in its own columns (the rest goes to ``payload``).
HEADER_FIELDS = ("kind", "id", "relation", "status", "status_ref", "rank", "visibility", "bindings", "version",
                 "recorded_at", "recorded_by")
FACT_COLS = ("id", "version", "tx_from", "tx_to", "recorded_at", "recorded_by", "relation", "rel_kind", "status",
             "status_ref", "rank", "visibility", "key_digest", "s_lo", "s_hi", "e_lo", "e_hi", "n_bindings", "payload")
BIND_COLS = ("fact_id", "version", "bid", "role", "position", "direction", "value_kind", "ref", "ident", "value_json",
             "extensions")
ENTITY_COLS = ("id", "version", "tx_from", "tx_to", "recorded_at", "recorded_by", "record")


def instant(x: float | int) -> int:
    """An instant as an int64 backend stores it: the sentinels for ±inf, else the integer (``ValueError`` beyond the
    guard; ``cannot_hold`` refuses such a record first)."""
    if x == NEG_INF:
        return NEG
    if x == POS_INF:
        return POS
    x = int(x)
    if not -INT64_HELD <= x <= INT64_HELD:
        raise ValueError(f"instant {x} is outside the int64 guard ±(2^62 - 2)")
    return x


def numeric_instant(x: float | int) -> Decimal:
    """An instant as PostgreSQL ``numeric`` stores it: exact, with ±Infinity."""
    if x == NEG_INF:
        return Decimal("-Infinity")
    if x == POS_INF:
        return Decimal("Infinity")
    return Decimal(int(x))


def query_instant(t: int) -> int:
    """An ``as_of`` parameter (seconds) for an int64 backend: clamped to ±(2^62 - 1). Every stored finite instant
    lies within ±(2^62 - 2) and the sentinels at ±2^62, so each comparison gives the answer the exact value gives."""
    return max(-(2 ** 62) + 1, min(2 ** 62 - 1, int(t)))


def _bounds(record: Mapping[str, Any], schema: Any) -> tuple[Any, Any, Any, Any]:
    try:
        b = bounds(record, schema)
        return b.s_lo, b.s_hi, b.e_lo, b.e_hi
    except Exception:  # noqa: BLE001 - a record a trusted load kept but cannot read passes no as_of filter
        return POS_INF, POS_INF, NEG_INF, NEG_INF


def unheld_instants(record: Mapping[str, Any], schema: Any) -> list[int]:
    """The finite instants of the record's bound table that an int64 backend cannot hold (``|x| > 2^62 - 2``)."""
    if not isinstance(record, Mapping) or record.get("kind") != "hyperedge":
        return []
    return [int(x) for x in _bounds(record, schema)
            if x not in (NEG_INF, POS_INF) and not -INT64_HELD <= int(x) <= INT64_HELD]


def _digest(record: Mapping[str, Any], schema: Any) -> str | None:
    try:
        return key_digest(record, schema)
    except Exception:  # noqa: BLE001 - as Entry.key_digest: what cannot be read has no key
        return None


def fact_row(record: Mapping[str, Any], schema: Any, t: int, *, as_instant: Any = instant) -> dict[str, Any]:
    """The fact row of a stored hyperedge version recorded at ``t`` (microseconds); ``tx_to`` is None."""
    rel = record["relation"]
    s_lo, s_hi, e_lo, e_hi = (as_instant(x) for x in _bounds(record, schema))
    return {
        "id": record["id"], "version": record["version"], "tx_from": t, "tx_to": None,
        "recorded_at": record["recorded_at"], "recorded_by": record["recorded_by"],
        "relation": rel, "rel_kind": "lifecycle" if rel in LIFECYCLE_RELATIONS else "fact",
        "status": record.get("status"), "status_ref": record.get("status_ref"),
        "rank": record.get("rank", "normal"), "visibility": record.get("visibility", "visible"),
        "key_digest": _digest(record, schema), "s_lo": s_lo, "s_hi": s_hi, "e_lo": e_lo, "e_hi": e_hi,
        "n_bindings": len(record.get("bindings") or []),
        "payload": jsonio.canonical({k: v for k, v in record.items() if k not in HEADER_FIELDS}),
    }


def binding_rows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One row per binding of a stored hyperedge version."""
    rows = []
    for b in record.get("bindings") or []:
        v = b["value"]
        (kind,) = v.keys()
        rows.append({
            "fact_id": record["id"], "version": record["version"], "bid": b["bid"], "role": b["role"],
            "position": b.get("position"), "direction": b.get("direction"), "value_kind": kind,
            "ref": v[kind] if kind in ("entity", "fact") else None,
            "ident": None if kind == "unbound" else identity_key(v),
            "value_json": jsonio.canonical(v),
            "extensions": jsonio.canonical(b["extensions"]) if "extensions" in b else None,
        })
    return rows


def split(record: Mapping[str, Any], schema: Any, t: int, *,
          as_instant: Any = instant) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """``(fact row, binding rows)`` of a stored hyperedge version."""
    return fact_row(record, schema, t, as_instant=as_instant), binding_rows(record)


def assemble(fact: Mapping[str, Any], rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """The hyperedge record of a fact row and its binding rows (the inverse of ``split``)."""
    r: dict[str, Any] = {"kind": "hyperedge", "id": fact["id"], "relation": fact["relation"],
                         "status": fact["status"], "rank": fact["rank"], "visibility": fact["visibility"]}
    if fact.get("status_ref") is not None:
        r["status_ref"] = fact["status_ref"]
    r.update(json.loads(fact["payload"]))
    bindings = []
    for row in rows:
        b: dict[str, Any] = {"bid": row["bid"], "role": row["role"]}
        kind = row["value_kind"]
        b["value"] = {kind: row["ref"]} if kind in ("entity", "fact") else json.loads(row["value_json"])
        if row.get("position") is not None:
            b["position"] = int(row["position"])
        if row.get("direction") is not None:
            b["direction"] = row["direction"]
        if row.get("extensions") is not None:
            b["extensions"] = json.loads(row["extensions"])
        bindings.append(b)
    r["bindings"] = sorted(bindings, key=binding_sort_key)
    r["version"] = int(fact["version"])
    r["recorded_at"] = fact["recorded_at"]
    r["recorded_by"] = fact["recorded_by"]
    return r


def entity_row(record: Mapping[str, Any], t: int) -> dict[str, Any]:
    """The row of a stored entity version recorded at ``t``."""
    return {"id": record["id"], "version": record["version"], "tx_from": t, "tx_to": None,
            "recorded_at": record["recorded_at"], "recorded_by": record["recorded_by"],
            "record": jsonio.canonical(dict(record))}


class Pat:
    """One prepared ``find`` pattern: role, position (None: any), kind (``value``, ``any``, ``any_unbound``) and the
    value identity."""

    __slots__ = ("role", "position", "kind", "ident")

    def __init__(self, role: str, position: int | None, kind: str, ident: str | None):
        self.role, self.position, self.kind, self.ident = role, position, kind, ident

    def __repr__(self) -> str:
        return f"Pat({self.role!r}, {self.position!r}, {self.kind!r}, {self.ident!r})"


def prepare(pattern: Any) -> list[Pat]:
    """The prepared patterns; ``TypeError`` or ``ValueError`` on a malformed one (as ``TableStore.find``)."""
    if isinstance(pattern, (str, bytes, Mapping)) or not isinstance(pattern, Sequence):
        raise TypeError("pattern is a sequence of {role, value, position?}")
    out = []
    for p in pattern:
        if not isinstance(p, Mapping) or not isinstance(p.get("role"), str) or "value" not in p or \
                set(p) - {"role", "value", "position"}:
            raise ValueError(f"a pattern is {{role, value, position?}}, not {p!r}")
        position = p.get("position")
        if "position" in p and (isinstance(position, bool) or not isinstance(position, int) or position < 1):
            raise ValueError(f"a pattern position is a positive integer, not {position!r}")
        v = p["value"]
        if v == {"any": True}:
            out.append(Pat(p["role"], position, "any", None))
        elif v == {"any_unbound": True}:
            out.append(Pat(p["role"], position, "any_unbound", None))
        else:
            out.append(Pat(p["role"], position, "value", identity_key(v)))
    return out
