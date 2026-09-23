"""The ``then`` clauses of a scenario step (DESIGN §6.4; ``index.json``: ``then`` and ``projections``).

- ``{select, equals}``: a projection of the result equals the value (canonical JSON). ``"@..."`` expected values are
  fixture records in canonical form without store fields; ``{store_id}`` is the store's id.
- ``{error, info?}``: the call raises; the code is among the error's codes; ``info`` matches as a subset (objects:
  the listed keys; lists: the same length, element-wise).
- ``{container_equals, ignore}``: ``compare_containers`` finds no difference.
- ``{hif_valid}``: ``validate_hif`` finds no error (the vendored schema, the profile, decoding and the C1 checks).
- ``{equals_file, ignore}``: the export equals the packaged file, without the listed ``attrs`` keys.
- ``{reload_equal}``: a fresh store that loads the export exports the same text; ``{deterministic}``: a second
  fresh run gives the same result.

``derived.*`` projections are computed from the returned record (``derived`` is an optional cache). A check that
fails raises ``Failed``; a projection or clause the runner does not know raises ``Unknown`` (``cantTell``).
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from ... import jsonio
from ...record import derive, normalize
from ...record.canonical import STORE_FIELDS
from ..compare import compare_containers

__all__ = ["CLAUSES", "Failed", "Unknown", "canonical_no_store", "project", "subset", "text"]

#: The ``then`` keys the runner evaluates.
CLAUSES = ("select", "equals", "error", "info", "container_equals", "ignore", "hif_valid", "equals_file",
           "reload_equal", "deterministic")


class Failed(Exception):
    """An assertion of the scenario does not hold."""


class Unknown(Exception):
    """The scenario asks for something the runner cannot evaluate."""


def text(x: Any, limit: int = 300) -> str:
    """A short canonical rendering for messages."""
    try:
        out = jsonio.canonical(_plain(x))
    except (TypeError, ValueError):
        out = repr(x)
    return out if len(out) <= limit else out[:limit] + "..."


def _plain(x: Any) -> Any:
    """Tuples as lists and frozensets as sorted lists, so results compare as JSON."""
    if isinstance(x, Mapping):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, (set, frozenset)):
        return sorted(_plain(v) for v in x)
    return x


def same(a: Any, b: Any) -> bool:
    """Equal as canonical JSON."""
    try:
        return jsonio.canonical(_plain(a)) == jsonio.canonical(_plain(b))
    except (TypeError, ValueError):
        return _plain(a) == _plain(b)


def canonical_no_store(record: Any) -> Any:
    """A record in canonical form without ``version``, ``recorded_at`` and ``recorded_by``."""
    if not isinstance(record, Mapping):
        return record
    r = normalize(record)
    for f in STORE_FIELDS:
        r.pop(f, None)
    return r


def _path(obj: Any, parts: list[str]) -> Any:
    for p in parts:
        if obj is None:
            return None
        if isinstance(obj, list):
            obj = obj[int(p)] if p.isdigit() and int(p) < len(obj) else None
        elif isinstance(obj, Mapping):
            obj = obj.get(p)
        else:
            return None
    return obj


def _by(items: Any, key: str, value: str) -> Any:
    return next((x for x in items or [] if isinstance(x, Mapping) and x.get(key) == value), None)


def project(result: Any, sel: str, schema: Any) -> Any:
    """The projection ``sel`` of a result (the ``projections`` of ``index.json``)."""
    if sel == "ids":
        if isinstance(result, Mapping):
            return sorted(result)
        return [r.get("id") for r in result]
    if sel in ("value", "record"):
        return result
    if sel == "canonical":
        return canonical_no_store(result) if result else None
    if sel in ("version", "status", "status_ref", "goal"):
        return None if result is None else result.get(sel)
    if sel == "versions":
        return [x.get("version") for x in result]
    if sel == "receipt.records":
        return [list(row) for row in result["records"]]
    if sel == "receipt.warnings":
        return result.get("warnings", [])
    if sel == "evidence.ids":
        return [e.get("id") for e in result.get("evidence", [])]
    if sel == "terminal":
        return result["terminal"]
    if sel == "terminal.ids":
        return [t["id"] for t in result["terminal"]]
    if sel == "steps.count":
        return len(result["steps"])
    head, _, rest = sel.partition(".")
    if head == "evidence" and rest:
        eid, _, field = rest.partition(".")
        return _path(_by(result.get("evidence"), "id", eid), field.split("."))
    if head == "binding" and rest:
        bid, _, field = rest.partition(".")
        return _path(_by(result.get("bindings"), "bid", bid), field.split("."))
    if head == "derived" and rest:
        return _path(derive(result, schema), rest.split("."))
    if head == "record" and rest:
        rid, _, field = rest.rpartition(".")
        r = _by(result.get("records"), "id", rid)
        return None if r is None else r.get(field)
    if head == "versions" and rest:
        lines = jsonio.loads_lines(result)
        return [x.get("version") for x in lines[1:] if x.get("id") == rest]
    if head == "header" and rest:
        return _path(result.get("header"), rest.split("."))
    if head == "metadata" and rest:
        return (result.get("metadata") or {}).get(rest)
    if head == "node" and rest:
        nid, _, path = rest.partition(".attrs.")
        n = _by(result.get("nodes"), "node", nid)
        return None if n is None else _path(n.get("attrs"), path.split("."))
    raise Unknown(f"unknown projection {sel!r}")


def subset(expected: Any, got: Any) -> bool:
    """The ``info`` rule: objects match on the listed keys, lists element-wise with the same length."""
    if isinstance(expected, Mapping):
        return isinstance(got, Mapping) and all(k in got and subset(v, got[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(got, (list, tuple)) and len(expected) == len(got) and all(
            subset(a, b) for a, b in zip(expected, got, strict=True))
    return same(expected, got)


def strip_attrs(hif: Mapping[str, Any], ignore: list[str]) -> dict[str, Any]:
    """A HIF document without the listed ``attrs`` keys of its nodes, edges and incidences."""
    out = copy.deepcopy(dict(hif))
    for coll in ("nodes", "edges", "incidences"):
        for x in out.get(coll, []):
            attrs = x.get("attrs") if isinstance(x, dict) else None
            for k in ignore:
                if isinstance(attrs, dict):
                    attrs.pop(k, None)
    return out


def container_differences(expected: Mapping[str, Any], result: Any, ignore: list[str]) -> list[dict[str, Any]]:
    if not isinstance(result, Mapping):
        raise Failed(f"the export is not a container but {type(result).__name__}")
    return compare_containers(expected, result, ignore=tuple(ignore))
