"""``queue_items(paths) -> Iterator[dict]`` (DESIGN §7): the items of queue files with their folded state and
verdicts, for the scorers (``scorers.extraction``, ``scorers.stability`` read them as they are).

Each item is its ``queue-item`` line plus ``state`` (the fold) and ``verdicts``: the ``verdict`` log entries, from
every file read, whose (``core_key``, ``event_hash``) is the item's ``keys.core_key`` and the ``event_hash`` of one of
its payload's extracted or inferred evidence records. A verdict thus carries over to a re-extraction of the same
event in another run. Files come in the order given, items in append order, verdicts in file then log order. Every
file is read and its structure checked before the first item is yielded (``ValidationError``).
"""
from __future__ import annotations

import copy
import os
from typing import Any, Iterable, Iterator, Mapping

from ..errors import ValidationError
from ..record import EVENT_TYPES
from .fold import Fold, check
from .lines import errors, read_lines

__all__ = ["queue_items"]


def _sources(paths: Any) -> list[Any]:
    if isinstance(paths, (str, bytes, os.PathLike)) or hasattr(paths, "read_bytes"):
        return [paths]
    if isinstance(paths, Iterable):
        return list(paths)
    raise TypeError(f"queue_items takes queue paths, not {type(paths).__name__}")


def _event_hashes(item: Mapping[str, Any]) -> list[Any]:
    payload = item.get("payload")
    evidence = payload.get("evidence") if isinstance(payload, Mapping) else None
    return [e.get("event_hash") for e in evidence if isinstance(e, Mapping) and e.get("type") in EVENT_TYPES] \
        if isinstance(evidence, list) else []


def _verdict_key(entry: Mapping[str, Any]) -> tuple[Any, Any]:
    v = entry.get("verdict")
    return (v.get("core_key"), v.get("event_hash")) if isinstance(v, Mapping) else (None, None)


def queue_items(paths: Any) -> Iterator[dict[str, Any]]:
    """The items of the queue files ``paths`` (one path, a ``Queue``, or an iterable of them), each with ``state``
    and ``verdicts``; see the module docstring."""
    folds: list[Fold] = []
    for source in _sources(paths):
        fold, findings = check(read_lines(source))
        if errors(findings):
            raise ValidationError.from_findings(findings, source=os.fspath(source)
                                                if isinstance(source, (str, os.PathLike)) else None)
        folds.append(fold)
    by_key: dict[tuple[Any, Any], list[tuple[int, int, dict[str, Any]]]] = {}
    for f, fold in enumerate(folds):
        for n, entry in fold.verdicts:
            by_key.setdefault(_verdict_key(entry), []).append((f, n, entry))
    return _items(folds, by_key)


def _items(folds: list[Fold], by_key: Mapping[tuple[Any, Any], list[tuple[int, int, dict[str, Any]]]]
           ) -> Iterator[dict[str, Any]]:
    for fold in folds:
        for qid, item in fold.items.items():
            keys = item.get("keys")
            core = keys.get("core_key") if isinstance(keys, Mapping) else None
            found = {(f, n): entry for h in _event_hashes(item) for f, n, entry in by_key.get((core, h), [])}
            out = copy.deepcopy(item)
            out["state"] = fold.state[qid]
            out["verdicts"] = [copy.deepcopy(found[k]) for k in sorted(found)]
            yield out
