"""Verdicts (DESIGN §7): one per (candidate, evidence) pair, keyed by (``core_key``, ``event_hash``), so a verdict
carries over to a re-extraction of the same event (``queue_items`` attaches it by that key). Per-binding labels name
a binding by its content tuple (role, position, value); the bid is only a hint.

``complete`` fills a verdict for ``Queue.verdict``; ``aggregate`` gives a candidate's verdict from its pairs as
[DB §7.3] states: ``correct`` when some pair is correct and none is ``no_relation`` or ``wrong_relation``, else the
most severe label in the order ``no_relation`` > ``wrong_relation`` > ``wrong_role`` > ``wrong_filler`` >
``missing_participant`` > ``extra_participant`` > ``span_boundary`` > ``negated`` > ``hypothesis`` > ``other``.
"""
from __future__ import annotations

import copy
from typing import Any, Iterable, Mapping

__all__ = ["SEVERITY_ORDER", "aggregate", "complete"]

SEVERITY_ORDER = ("no_relation", "wrong_relation", "wrong_role", "wrong_filler", "missing_participant",
                  "extra_participant", "span_boundary", "negated", "hypothesis", "other")


def complete(verdict: Mapping[str, Any], item: Mapping[str, Any]) -> dict[str, Any]:
    """The verdict object ``Queue.verdict`` writes: a copy of ``verdict`` whose ``core_key`` (the item's) and
    ``event_hash`` (that of the evidence ``evidence_id`` names) are filled when absent, and whose ``bindings`` and
    ``missing`` default to ``[]``. Values given are kept, and checked later (Q010)."""
    if not isinstance(verdict, Mapping):
        raise TypeError(f"a verdict is an object, not {type(verdict).__name__}")
    v = copy.deepcopy(dict(verdict))
    keys = item.get("keys")
    if "core_key" not in v and isinstance(keys, Mapping) and isinstance(keys.get("core_key"), str):
        v["core_key"] = keys["core_key"]
    payload = item.get("payload")
    evidence = payload.get("evidence") if isinstance(payload, Mapping) else None
    ev = next((e for e in evidence if isinstance(e, Mapping) and e.get("id") == v.get("evidence_id")), None) \
        if isinstance(evidence, list) else None
    if "event_hash" not in v and ev is not None and isinstance(ev.get("event_hash"), str):
        v["event_hash"] = ev["event_hash"]
    v.setdefault("bindings", [])
    v.setdefault("missing", [])
    return v


def aggregate(verdicts: Iterable[Mapping[str, Any]]) -> str | None:
    """A candidate's verdict label from its pair verdicts (verdict objects, or the log entries that carry them);
    None when there is none."""
    labels = []
    for v in verdicts:
        v = v.get("verdict", v) if isinstance(v, Mapping) else v
        if isinstance(v, Mapping) and isinstance(v.get("label"), str):
            labels.append(v["label"])
    if not labels:
        return None
    if "correct" in labels and not {"no_relation", "wrong_relation"} & set(labels):
        return "correct"
    ranked = [label for label in labels if label in SEVERITY_ORDER]
    return min(ranked, key=SEVERITY_ORDER.index) if ranked else None
