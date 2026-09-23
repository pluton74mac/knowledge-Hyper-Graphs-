"""``Where``: the filter of the C2 reads (DESIGN §6.1, §6.2).

The defaults are a ruling: status ``{asserted}``, rank ``{preferred, normal}``, visibility ``{visible}`` and kinds
``{fact}``, with **no valid-time filter** and the latest versions. ``as_at`` picks the versions (transaction time),
then ``as_of`` tests their validity with the bound table of §2.6, ``definite`` (s_hi <= t < e_lo) or ``possible``
(s_lo <= t < e_hi). Facts of ``invariant`` and ``timeless`` relations pass every ``as_of`` filter.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Iterable, Literal, Mapping

from ..record import VALID_MODES, parse_instant
from ..record.lifecycle import RANKS, STATUSES, VISIBILITIES, parse_timestamp

__all__ = ["DEFAULT_WHERE", "KINDS", "Where"]

#: The relation kinds a read can include: facts and lifecycle records (rules come in 1.1).
KINDS = ("fact", "lifecycle")
_SETS = (("status", STATUSES), ("rank", RANKS), ("visibility", VISIBILITIES), ("kinds", KINDS))


@dataclass(frozen=True)
class Where:
    """The filter of ``incident``, ``find``, ``find_by_key`` and ``degree``.

    The set fields accept any iterable of strings and are stored as frozensets; an unknown value is ``ValueError``.
    ``as_of`` is an instant ``[+-]YYYY-MM-DDThh:mm:ssZ`` and ``as_at`` an RFC 3339 UTC timestamp; a malformed one
    is ``ValidationError`` C011.
    """

    status: frozenset[str] = frozenset({"asserted"})
    rank: frozenset[str] = frozenset({"preferred", "normal"})
    visibility: frozenset[str] = frozenset({"visible"})
    kinds: frozenset[str] = frozenset({"fact"})
    as_of: str | None = None
    valid_mode: Literal["definite", "possible"] = "definite"
    as_at: str | None = None

    def __post_init__(self) -> None:
        for name, allowed in _SETS:
            value = getattr(self, name)
            if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
                raise TypeError(f"Where.{name} is a collection of strings, not {type(value).__name__}")
            items = frozenset(value)
            unknown = sorted(str(x) for x in items if x not in allowed)
            if unknown:
                raise ValueError(f"Where.{name}: {', '.join(unknown)} not in {', '.join(allowed)}")
            object.__setattr__(self, name, items)
        if self.valid_mode not in VALID_MODES:
            raise ValueError(f"Where.valid_mode must be one of {', '.join(VALID_MODES)}, not {self.valid_mode!r}")
        if self.as_of is not None:
            parse_instant(self.as_of)
        if self.as_at is not None:
            parse_timestamp(self.as_at)

    @classmethod
    def of(cls, where: Where | Mapping[str, Any] | None) -> Where:
        """A ``Where`` from a ``Where``, a mapping of its fields (lists allowed, as in the scenario files) or None
        (the defaults). Unknown keys are ``TypeError``."""
        if where is None:
            return cls()
        if isinstance(where, Where):
            return where
        if not isinstance(where, Mapping):
            raise TypeError(f"expected a Where or a mapping, not {type(where).__name__}")
        return cls(**dict(where))

    def as_dict(self) -> dict[str, Any]:
        """The field dict, with the sets as sorted lists (the ``khg-timed/1`` argument form)."""
        out: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            out[f.name] = sorted(value) if isinstance(value, frozenset) else value
        return out

    @property
    def as_of_seconds(self) -> int | None:
        """``as_of`` as seconds on the instant line (None without a valid-time filter)."""
        return None if self.as_of is None else parse_instant(self.as_of)

    @property
    def as_at_micros(self) -> int | None:
        """``as_at`` as microseconds (None for the latest versions)."""
        return None if self.as_at is None else parse_timestamp(self.as_at)


#: ``Where()``: the default filter of every read (one immutable instance, used as the default argument).
DEFAULT_WHERE = Where()
