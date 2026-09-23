"""Read-only walks over a HIF document that never raise on a malformed structure."""
from __future__ import annotations

from typing import Any, Iterator, Mapping

__all__ = ["attrs_of", "mapping", "records"]

_EMPTY: Mapping[str, Any] = {}


def mapping(value: Any) -> Mapping[str, Any]:
    """``value`` when it is an object, else an empty mapping."""
    return value if isinstance(value, Mapping) else _EMPTY


def records(doc: Mapping[str, Any], key: str) -> Iterator[tuple[int, Mapping[str, Any]]]:
    """``(index, record)`` for the objects in ``doc[key]`` (``nodes``, ``edges`` or ``incidences``), in file order;
    nothing when ``doc[key]`` is not an array."""
    items = doc.get(key)
    for j, item in enumerate(items if isinstance(items, list) else []):
        if isinstance(item, Mapping):
            yield j, item


def attrs_of(item: Mapping[str, Any]) -> Mapping[str, Any]:
    """A record's ``attrs`` when it is an object, else an empty mapping."""
    return mapping(item.get("attrs"))
