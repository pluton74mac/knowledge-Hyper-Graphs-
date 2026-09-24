"""Entity redirects (DESIGN §2.2, §2.9, §9.1): ``redirect_to`` names the entity one was merged into."""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Union

__all__ = ["resolve_redirects"]

Entities = Union[Mapping[str, Mapping[str, Any]], Iterable[Mapping[str, Any]]]


def _index(entities: Entities) -> Mapping[str, Mapping[str, Any]]:
    if isinstance(entities, Mapping):
        return entities
    return {e["id"]: e for e in entities if isinstance(e, Mapping) and e.get("kind", "entity") == "entity"}


def resolve_redirects(entity_id: str, entities: Entities) -> str:
    """The surviving entity: follow ``redirect_to`` from ``entity_id`` until an entity without one, or an id not in
    ``entities`` ({id: entity record}, or an iterable of entity records). A redirect cycle (invalid data) stops at
    the first entity met twice."""
    index = _index(entities)
    seen: set[str] = set()
    current = entity_id
    while current not in seen:
        record = index.get(current)
        target = record.get("redirect_to") if isinstance(record, Mapping) else None
        if not isinstance(target, str) or not target:
            return current
        seen.add(current)
        current = target
    return current
