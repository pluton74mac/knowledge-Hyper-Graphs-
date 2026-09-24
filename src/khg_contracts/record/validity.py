"""Valid time: the bound table, definite and possible validity, and the ``valid_time`` view (DESIGN §2.6).

For an interval relation the start and end bindings each give a window:

| Start binding | [s_lo, s_hi) | End binding | [e_lo, e_hi) |
|---|---|---|---|
| a literal | its precision window | a literal | its precision window |
| absent or ``somevalue`` | (-inf, e_hi) | absent or ``novalue`` | e_lo = e_hi = +inf (still holds) |
| ``novalue`` | s_lo = s_hi = -inf (held since forever) | ``somevalue`` | [s_lo, +inf) (ended, date unknown) |

Definite validity is [s_hi, e_lo); possible validity is [s_lo, e_hi). Facts of ``invariant`` and ``timeless``
relations hold at every instant. Instants are seconds (see ``windows``), with -inf and +inf for open sides.
"""
from __future__ import annotations

from typing import Any, Mapping, NamedTuple, Union

from ._common import SchemaLike, as_schema, bindings, hyperedge, value_kind
from .values import canonical_value
from .windows import NEG_INF, POS_INF, format_instant, parse_instant, window_seconds

__all__ = ["Bounds", "bounds", "definite_overlap", "possible_overlap", "valid_time", "VALID_MODES"]

Instant = Union[int, float]
VALID_MODES = ("definite", "possible")


class Bounds(NamedTuple):
    """The bound table of one fact: its kind and the instants s_lo, s_hi, e_lo and e_hi (seconds, or +/-inf)."""

    kind: str
    s_lo: Instant
    s_hi: Instant
    e_lo: Instant
    e_hi: Instant

    @property
    def definite(self) -> tuple[Instant, Instant] | None:
        """[s_hi, e_lo), or None when it is empty."""
        return (self.s_hi, self.e_lo) if self.s_hi < self.e_lo else None

    @property
    def possible(self) -> tuple[Instant, Instant]:
        """[s_lo, e_hi) (empty when s_lo >= e_hi, which is S009)."""
        return self.s_lo, self.e_hi

    def holds_at(self, instant: Instant | str, mode: str = "definite") -> bool:
        """Does an ``as_of`` read at ``instant`` (seconds, or the §2.1 grammar) match? ``definite``:
        s_hi <= t < e_lo; ``possible``: s_lo <= t < e_hi."""
        t = parse_instant(instant) if isinstance(instant, str) else instant
        if mode == "definite":
            return self.s_hi <= t < self.e_lo
        if mode == "possible":
            return self.s_lo <= t < self.e_hi
        raise ValueError(f"valid_mode must be one of {VALID_MODES}, not {mode!r}")


def definite_overlap(a: Bounds, b: Bounds) -> bool:
    """Two facts definitely overlap iff max(s_hi) < min(e_lo)."""
    return max(a.s_hi, b.s_hi) < min(a.e_lo, b.e_lo)


def possible_overlap(a: Bounds, b: Bounds) -> bool:
    """Two facts possibly overlap iff max(s_lo) < min(e_hi)."""
    return max(a.s_lo, b.s_lo) < min(a.e_hi, b.e_hi)


def _bound(record: Mapping[str, Any], role: str) -> tuple[str, tuple[int, int] | None]:
    for b in bindings(record):
        if b.get("role") == role:
            v = b.get("value")
            kind = value_kind(v)
            if kind == "literal":
                return "literal", window_seconds(v["literal"])
            if kind == "special":
                return v["special"], None
            return "other", None
    return "absent", None


def bounds(record: Mapping[str, Any], schema: SchemaLike) -> Bounds:
    """The bound table of a hyperedge under its relation's time model (S001 for an undeclared relation)."""
    hyperedge(record)
    tm = as_schema(schema).time_model(record.get("relation"))
    if tm.get("model") != "interval":
        return Bounds(tm.get("model", "timeless"), NEG_INF, NEG_INF, POS_INF, POS_INF)
    st, sw = _bound(record, tm["start"])
    et, ew = _bound(record, tm["end"])
    e_lo: Instant | None
    if et == "literal":
        e_lo, e_hi = ew  # type: ignore[misc]
    elif et in ("novalue", "absent"):
        e_lo = e_hi = POS_INF
    else:  # somevalue: ended after the start, when is unknown
        e_lo, e_hi = None, POS_INF
    if st == "literal":
        s_lo, s_hi = sw  # type: ignore[misc]
    elif st == "novalue":
        s_lo = s_hi = NEG_INF
    else:  # absent or somevalue: started at an unknown time before the end
        s_lo, s_hi = NEG_INF, e_hi
    if e_lo is None:
        e_lo = s_lo
    if st == "literal" and et == "literal":
        kind = "period"
    elif st == "literal" and et in ("absent", "novalue"):
        kind = "since"
    elif st == "literal":
        kind = "ended"
    elif et == "literal":
        kind = "until"
    else:
        kind = "undated"
    return Bounds(kind, s_lo, s_hi, e_lo, e_hi)


def valid_time(record: Mapping[str, Any], schema: SchemaLike) -> dict[str, Any]:
    """``derived.valid_time``: ``{kind, start?, end?, definite: [lo, hi] | None, possible: [lo, hi]}`` with instants
    in the §2.1 grammar and None for an unbounded side. ``start`` and ``end`` are the bound values of an interval
    relation, in canonical form."""
    s = as_schema(schema)
    b = bounds(record, s)
    out: dict[str, Any] = {"kind": b.kind}
    tm = s.time_model(record["relation"])
    if tm.get("model") == "interval":
        for side in ("start", "end"):
            for x in bindings(record):
                if x.get("role") == tm[side]:
                    out[side] = canonical_value(x["value"])
    d = b.definite
    out["definite"] = [format_instant(d[0]), format_instant(d[1])] if d is not None else None
    out["possible"] = [format_instant(b.s_lo), format_instant(b.e_hi)]
    return out
