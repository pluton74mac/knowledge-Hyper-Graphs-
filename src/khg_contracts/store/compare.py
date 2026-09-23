"""``compare_containers``: the structural differences between two C1 containers (DESIGN §6.3; critique CONS-05,
GL-04).

Headers are compared field by field, without ``header_ignore`` (``created_at`` and ``generator``). Records are
compared in canonical form (so ``derived``, key order, binding and evidence order and default fields do not count),
without the ``ignore`` fields (the store fields ``version``, ``recorded_at`` and ``recorded_by``), keyed by id in
snapshots and by (id, version) in history containers. The result is [] when they agree, else one difference per
header field or record, in order: ``{"path", "a", "b"}``, with ``id`` and ``version`` for a record and ``fields``,
the top-level fields that differ, when both sides hold it.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .. import jsonio
from ..record import normalize

__all__ = ["compare_containers"]


def _text(x: Any) -> str:
    try:
        return jsonio.canonical(x)
    except (TypeError, ValueError):
        return repr(x)


def _escape(part: Any) -> str:
    return str(part).replace("~", "~0").replace("/", "~1")


def _keyed(container: Mapping[str, Any], ignore: Iterable[str], history: bool) -> dict[tuple[str, int], Any]:
    out: dict[tuple[str, int], Any] = {}
    records = container.get("records")
    for r in records if isinstance(records, list) else []:
        if not isinstance(r, Mapping):
            continue
        rec = normalize(r)
        rid, version = rec.get("id"), rec.get("version", 0)
        key = (rid if isinstance(rid, str) else _text(rid), version if history and isinstance(version, int) else 0)
        for f in ignore:
            rec.pop(f, None)
        out[key] = rec
    return out


def compare_containers(a: Mapping[str, Any], b: Mapping[str, Any], *,
                       ignore: Iterable[str] = ("version", "recorded_at", "recorded_by"),
                       header_ignore: Iterable[str] = ("created_at", "generator")) -> list[dict[str, Any]]:
    """The structural differences between containers ``a`` and ``b`` ([] when they are equal)."""
    for name, c in (("a", a), ("b", b)):
        if not isinstance(c, Mapping):
            raise TypeError(f"{name} is a container {{header, records}}, not {type(c).__name__}")
    ignore, header_ignore = tuple(ignore), tuple(header_ignore)
    diffs: list[dict[str, Any]] = []
    ha, hb = a.get("header") or {}, b.get("header") or {}
    for k in sorted((set(ha) | set(hb)) - set(header_ignore)):
        if _text(ha.get(k)) != _text(hb.get(k)):
            diffs.append({"path": f"/header/{_escape(k)}", "a": ha.get(k), "b": hb.get(k)})
    history = "history" in (ha.get("content"), hb.get("content"))
    ka, kb = _keyed(a, ignore, history), _keyed(b, ignore, history)
    for key in sorted(set(ka) | set(kb)):
        ra, rb = ka.get(key), kb.get(key)
        if ra is not None and rb is not None and _text(ra) == _text(rb):
            continue
        rid, version = key
        diff: dict[str, Any] = {"path": f"/records/{_escape(rid)}" + (f"/{version}" if history else ""), "id": rid}
        if history:
            diff["version"] = version
        if ra is not None and rb is not None:
            diff["fields"] = sorted(f for f in set(ra) | set(rb) if _text(ra.get(f)) != _text(rb.get(f)))
        diff["a"], diff["b"] = ra, rb
        diffs.append(diff)
    return diffs
