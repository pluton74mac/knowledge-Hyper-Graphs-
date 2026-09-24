"""Helpers shared by the loaders: typed id keys, library values as JSON values, and the reserved names (DESIGN §5).

HIF ids are strings or integers, and the integer ``1`` and the string ``"1"`` are two ids (R03 c12), so every lookup
uses a typed key ``(type name, value)``. Values read back from HyperNetX may be numpy scalars; ``plain`` turns them
into Python values without importing numpy.
"""
from __future__ import annotations

from typing import Any, Tuple

__all__ = [
    "EXTRA",
    "LIBRARIES",
    "VALIDATE_MODES",
    "TypedKey",
    "is_default_weight",
    "is_missing",
    "library_of",
    "plain",
    "tkey",
]

#: The reserved HyperNetX cell key that carries records 2..k of one (edge, node) pair.
EXTRA = "khg-extra-incidences"
#: The ``validate=`` modes of ``load_xgi`` and ``load_hnx``.
VALIDATE_MODES = ("profile", "convention", "none")
#: The libraries a ``Bundle`` can hold, by their short names.
LIBRARIES = ("xgi", "hnx")

TypedKey = Tuple[str, Any]


def tkey(x: Any) -> TypedKey:
    """The typed key of a HIF id: ``(type name, value)``; it also sorts ids of one type by value."""
    return (type(x).__name__, x)


def plain(v: Any) -> Any:
    """A numpy scalar as the equal Python value; anything else unchanged (numpy is never imported here)."""
    if type(v).__module__ == "numpy" and hasattr(v, "item"):
        return v.item()
    return v


def is_missing(v: Any) -> bool:
    """True for the values pandas uses for a missing cell: None, NaN, ``pd.NA`` and ``pd.NaT``."""
    if v is None or type(v).__name__ in ("NAType", "NaTType"):
        return True
    return isinstance(v, float) and v != v


def is_default_weight(v: Any) -> bool:
    """True when a library weight says nothing: absent, missing, or HyperNetX's default 1."""
    v = plain(v)
    if is_missing(v):
        return True
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == 1


def library_of(graph: Any) -> str | None:
    """``"xgi"`` or ``"hnx"`` from the class of a library object (neither library is imported), else None."""
    top = type(graph).__module__.split(".", 1)[0]
    return {"xgi": "xgi", "hypernetx": "hnx"}.get(top)
