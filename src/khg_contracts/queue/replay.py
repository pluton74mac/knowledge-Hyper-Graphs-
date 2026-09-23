"""``replay(path, *, schema, factory, base=None) -> dict`` (DESIGN §7): re-run a queue's accepts on a fresh store.

The queue is read and its structure checked (layer J, the queue schema, the fold; D009 for another schema). The
base must be the header's (Q012: the same ``document_id`` and ``record.container_sha256``; a header without a base
takes none). Then ``factory(schema, clock)`` builds a store, which loads the base, and every ``accept`` runs again in
log order at its ``at``: one ``put`` of the item's entities and of the payload with the fact's id and status
asserted. Q006 when the put fails, or when the versions written or the recomputed ``decision_hash`` differ from the
entry's. The base is loaded just before the first accept (at the header's ``created_at``, or earlier), since a
store's transaction time only moves forward.

The result is ``{ok, findings, decisions, store}``: ``decisions`` lists ``{lid, target, after, decision_hash}``
as recomputed, and ``store`` is the replayed store (None when the checks before the replay failed).
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

from ..errors import KHGError, make_finding
from ..schema import Schema, load_schema
from ..store.clocks import ScenarioClock, format_timestamp, parse_timestamp
from .checks import base_findings, pin_findings
from .decision import accepted_record, decision_hash, written_versions
from .fold import Fold, check
from .handle import as_container
from .lines import errors, read_lines

__all__ = ["replay", "replay_accepts"]

Finding = dict[str, str]
_FAILURES = (KHGError, ValueError, TypeError, KeyError, LookupError)


def replay(path: Any, *, schema: Any, factory: Callable[[Schema, Any], Any], base: Any = None) -> dict[str, Any]:
    """Replay the accepts of the queue at ``path`` (a path, a ``Queue`` or its lines) on ``factory(schema,
    clock)`` loaded with ``base`` (a container or a path); see the module docstring. Raises ``ValidationError``
    only for a file that does not parse (layer J) or a bad schema or base argument."""
    s = load_schema(schema)
    lines = read_lines(path)
    container = as_container(base) if base is not None else None
    fold, findings = check(lines)
    if fold.header is not None:
        findings += pin_findings(fold.header, s)
        findings += base_findings(fold.header, container)
    if errors(findings):
        return {"ok": False, "findings": findings, "decisions": [], "store": None}
    store, found, decisions = replay_accepts(fold, s, factory, container)
    findings += found
    return {"ok": not errors(findings), "findings": findings, "decisions": decisions, "store": store}


def _micros(value: Any) -> int | None:
    try:
        return parse_timestamp(value)
    except _FAILURES:
        return None


def _load_time(fold: Fold) -> str:
    """Before every accept: the header's ``created_at``, or a microsecond before the first accept."""
    times = [_micros((fold.header or {}).get("created_at"))]
    times += [t - 1 for _, entry in fold.accepts if (t := _micros(entry.get("at"))) is not None]
    known = [t for t in times if t is not None]
    return format_timestamp(min(known)) if known else "1970-01-01T00:00:00Z"


def _fact_id(entry: Mapping[str, Any], item: Mapping[str, Any]) -> str | None:
    """The fact an accept wrote or read: the one id of ``after`` and ``before`` that is not an item entity."""
    entities = {e.get("id") for e in item.get("entities") or [] if isinstance(e, Mapping)}
    named = {w.get("id") for w in list(entry.get("after") or []) + list(entry.get("before") or [])
             if isinstance(w, Mapping)}
    facts = sorted(x for x in named - entities if isinstance(x, str))
    return facts[0] if len(facts) == 1 else None


def replay_accepts(fold: Fold, schema: Schema, factory: Callable[[Schema, Any], Any],
                   base: Mapping[str, Any] | None) -> tuple[Any, list[Finding], list[dict[str, Any]]]:
    """``(store, Q006 findings, decisions)`` of re-running the accepts of a structurally valid fold."""
    start = _load_time(fold)
    store = factory(schema, ScenarioClock(start))
    out: list[Finding] = []
    decisions: list[dict[str, Any]] = []
    if base is not None:
        try:
            store.load(base, at=start)
        except _FAILURES as exc:
            return store, [make_finding("KHG-Q006", "/lines/0/base", f"replay cannot load the base: {exc}")], []
    for n, entry in fold.accepts:
        item = fold.items[entry["target"]]
        fact = _fact_id(entry, item)
        if fact is None:
            out.append(make_finding("KHG-Q006", f"/lines/{n}", "the accept names no single fact in after or before"))
            continue
        entities = [dict(e) for e in item.get("entities") or [] if isinstance(e, Mapping)]
        record = accepted_record(item, fact)
        try:
            receipt = store.put(entities + [record] if entities else record, actor=entry["actor"]["id"],
                                at=entry["at"])
            after = written_versions(receipt)
            recomputed = decision_hash(store, after)
        except _FAILURES as exc:
            out.append(make_finding("KHG-Q006", f"/lines/{n}", f"replay of the accept failed: {exc}"))
            continue
        decisions.append({"lid": entry.get("lid"), "target": entry["target"], "after": after,
                          "decision_hash": recomputed})
        if after != entry.get("after"):
            out.append(make_finding("KHG-Q006", f"/lines/{n}/after", f"replay writes {after}, the entry records "
                                                                     f"{entry.get('after')}"))
        if recomputed != entry.get("decision_hash"):
            out.append(make_finding("KHG-Q006", f"/lines/{n}/decision_hash", f"replay recomputes {recomputed}"))
    return store, out, decisions
