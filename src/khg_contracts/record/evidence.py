"""Evidence: ``event_hash``, what evidence supports, and code-point spans (DESIGN §2.8, §2.9).

- ``event_hash`` is ``digest("khg-event/1", {content_key, doc, selectors, activity, reference?, inference?})``,
  computed **once, at extraction**, over the candidate payload's ``content_key`` and stored in the evidence record.
  It is never recomputed against the host record. Only ``extracted`` and ``inferred`` evidence has one.
- An evidence record supports the values its bids held **in the first version that carries it**
  (``supported_values``), so a later refinement is never attributed to earlier evidence.
- Selectors count code points, half-open, over the NFC text that ``doc_sha256`` hashes.
"""
from __future__ import annotations

import copy
import hashlib
from typing import Any, Iterable, Mapping

from .. import jsonio
from ._common import SchemaLike, bindings, fail
from .derive import content_key
from .values import canonical_value

__all__ = [
    "ACTIVITY_FIELDS",
    "EVENT_TYPES",
    "event_hash",
    "selected_text",
    "span_selectors",
    "stamp_event_hashes",
    "supported_values",
    "text_sha256",
]

#: The evidence types that carry an ``event_hash``.
EVENT_TYPES = ("extracted", "inferred")
#: The ``activity`` fields that enter ``event_hash`` (``run_id`` does not).
ACTIVITY_FIELDS = ("agent", "agent_version", "model", "model_version", "prompt_id", "skill_id")


def event_hash(content_key: str, evidence: Mapping[str, Any]) -> str:
    """``khg-event/1`` of one evidence record for a candidate whose content key is ``content_key``.

    The payload is ``{content_key, doc: doc_sha256 else doc_id, selectors: sorted canonical texts, activity: the
    six fields present, reference?: sorted canonical texts, inference?}``. So two references of one statement hash
    differently even when they share a ``doc_id``.
    """
    source = evidence.get("source")
    if not isinstance(source, Mapping) or not (source.get("doc_sha256") or source.get("doc_id")):
        raise fail("KHG-C010", "evidence source needs doc_id (or doc_sha256)", "/source")
    activity = evidence.get("activity") or {}
    payload: dict[str, Any] = {
        "content_key": content_key,
        "doc": source.get("doc_sha256") or source["doc_id"],
        "selectors": sorted(jsonio.canonical(s) for s in evidence.get("selectors") or []),
        "activity": {k: activity[k] for k in ACTIVITY_FIELDS if k in activity},
    }
    if evidence.get("reference"):
        payload["reference"] = sorted(jsonio.canonical(s) for s in evidence["reference"])
    if evidence.get("inference"):
        payload["inference"] = evidence["inference"]
    return jsonio.digest("khg-event/1", payload)


def stamp_event_hashes(record: Mapping[str, Any], schema: SchemaLike) -> dict[str, Any]:
    """A copy of ``record`` whose ``extracted`` and ``inferred`` evidence carries ``event_hash``, computed from the
    record's ``content_key`` (what ``make_candidate`` does). A stored ``event_hash`` is never replaced."""
    out = copy.deepcopy(dict(record))
    evidence = out.get("evidence") or []
    if any(e.get("type") in EVENT_TYPES and "event_hash" not in e for e in evidence):
        ck = content_key(out, schema)
        for e in evidence:
            if e.get("type") in EVENT_TYPES and "event_hash" not in e:
                e["event_hash"] = event_hash(ck, e)
    return out


def supported_values(history: Iterable[Mapping[str, Any]], evidence_id: str) -> dict[str, Any]:
    """``{bid: canonical value}``: the values that ``evidence_id`` supports, read in the first version of the
    hyperedge that carries it (§2.8.1); ``{}`` when no version carries it. Without ``supports`` it supports every
    bid of that version."""
    versions = sorted(history, key=lambda r: r.get("version", 1))
    for version in versions:
        ev = next((e for e in version.get("evidence") or [] if e.get("id") == evidence_id), None)
        if ev is None:
            continue
        bs = bindings(version)
        wanted = set(ev["supports"]) if "supports" in ev else {b["bid"] for b in bs}
        return {b["bid"]: canonical_value(b["value"]) for b in bs if b["bid"] in wanted}
    return {}


def text_sha256(text: str) -> str:
    """``doc_sha256`` of a document text: the SHA-256 of its NFC form, UTF-8 encoded."""
    return "sha256:" + hashlib.sha256(jsonio.nfc(text).encode("utf-8")).hexdigest()


def span_selectors(text: str, exact: str, *, occurrence: int = 0, context: int = 12) -> list[dict[str, Any]]:
    """The quote and position selectors of ``exact`` in ``text``: code points, half-open, over the NFC text, with
    up to ``context`` code points of prefix and suffix. ``occurrence`` picks the n-th match (from 0)."""
    t, q = jsonio.nfc(text), jsonio.nfc(exact)
    if not q:
        raise ValueError("an empty quote has no span")
    start = -1
    for _ in range(occurrence + 1):
        start = t.find(q, start + 1)
        if start < 0:
            raise ValueError(f"{exact!r} does not occur {occurrence + 1} time(s) in the text")
    end = start + len(q)  # Python str offsets count code points
    return [{"type": "quote", "exact": q, "prefix": t[max(0, start - context):start], "suffix": t[end:end + context]},
            {"type": "position", "start": start, "end": end}]


def selected_text(text: str, selector: Mapping[str, Any]) -> str:
    """The text a position selector selects: ``NFC(text)[start:end]`` in code points (``ValueError`` when the span
    is empty, reversed or outside the text: S021's first half)."""
    t = jsonio.nfc(text)
    start, end = selector.get("start"), selector.get("end")
    ints = all(isinstance(x, int) and not isinstance(x, bool) for x in (start, end))
    if not (ints and 0 <= start < end <= len(t)):
        raise ValueError(f"span [{start}, {end}) is empty, reversed or outside a text of {len(t)} code points")
    return t[start:end]
