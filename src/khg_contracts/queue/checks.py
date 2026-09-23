"""The content checks on queue items and verdicts (DESIGN §7), shared by layer Q and the ``Linter``.

On one hyperedge item (paths are relative to the item line):

- Q002 a payload id that is ``cand:<queue>.<seq>`` for another queue (the schema reports any other form);
- Q009 extracted evidence that does not cite the item's ``doc`` (``doc_id`` and ``doc_sha256``);
- Q010 item ``keys`` that differ from the keys of the payload read as asserted, or an ``event_hash`` of extracted or
  inferred evidence that differs from ``khg-event/1`` over that content key (with the relation-type schema);
- Q011 an entity value that ``item.entities`` and the other sources given do not resolve.

On a verdict entry: Q008 an ``evidence_id`` the payload lacks or whose evidence has no ``event_hash``, or a binding
tuple (role, position, value identity) that is not a binding of the payload; Q010 a ``core_key`` or ``event_hash``
other than the item's. The header checks D009 (the schema pin) and Q012 (the base against the header's pin) serve
``Queue.open``, the linter and ``replay``. What a payload cannot be read for is left to layers C and S.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from .. import jsonio
from ..errors import KHGError, make_finding
from ..record import EVENT_TYPES, container_sha256, content_key, core_key, event_hash, key_digest, value_identity
from ..schema import Schema
from .model import CAND_PATTERN, SHA256_PATTERN, seq_of

__all__ = ["KEY_FIELDS", "base_findings", "cand_findings", "item_core_key", "item_findings", "item_keys",
           "keys_or_none", "pin_findings", "verdict_findings"]

KEY_FIELDS = ("content_key", "core_key", "key_digest")
_UNREADABLE = (KHGError, ValueError, TypeError, KeyError, AttributeError)

Finding = dict[str, str]


def _f(code: str, path: str, message: str) -> Finding:
    return make_finding(code, path, message)


def _list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else []


def _sha(x: Any) -> bool:
    return isinstance(x, str) and re.fullmatch(SHA256_PATTERN, x) is not None


# ------------------------------------------------------------------------------------------------ keys


def item_keys(payload: Mapping[str, Any], schema: Schema) -> dict[str, str | None]:
    """``{content_key, core_key, key_digest}`` of a payload read as asserted (§7); raises what ``record`` raises on
    a payload it cannot read."""
    probe = dict(payload)
    probe["status"] = "asserted"
    return {"content_key": content_key(probe, schema), "core_key": core_key(probe, schema),
            "key_digest": key_digest(probe, schema)}


def keys_or_none(payload: Any, schema: Schema | None) -> dict[str, str | None] | None:
    """``item_keys``, or None without a schema or when the payload cannot be read."""
    if schema is None or not isinstance(payload, Mapping):
        return None
    try:
        return item_keys(payload, schema)
    except _UNREADABLE:
        return None


def _stored_well_formed(keys: Mapping[str, Any], name: str) -> bool:
    value = keys[name]
    return _sha(value) or (name == "key_digest" and value is None)


# ------------------------------------------------------------------------------------------------ items


def item_findings(item: Mapping[str, Any], *, queue_id: str | None, schema: Schema | None,
                  entities: Mapping[str, Any] | Iterable[str] = (), path: str = "") -> list[Finding]:
    """Q002, Q009, Q010 and Q011 on one hyperedge item. ``entities`` holds the ids resolved by the sources after
    ``item.entities`` (the linter's entities or the base, then the store); Q010 needs ``schema``."""
    payload = item.get("payload")
    if not isinstance(payload, Mapping):
        return []  # the queue schema reports it
    out = cand_findings(payload.get("id"), queue_id, path)
    out += _doc_findings(item.get("doc"), payload, path)
    out += _key_findings(item, payload, schema, path)
    out += _entity_findings(item, payload, entities, path)
    return out


def cand_findings(pid: Any, queue_id: str | None, path: str = "") -> list[Finding]:
    """Q002 when ``pid`` is ``cand:<queue>.<seq>`` for a queue other than ``queue_id`` (``path`` is the item's)."""
    if not isinstance(queue_id, str) or not isinstance(pid, str) or not re.fullmatch(CAND_PATTERN, pid):
        return []
    if seq_of(pid, "cand", queue_id) is None:
        return [_f("KHG-Q002", f"{path}/payload/id", f"{pid} is not cand:{queue_id}.<seq>")]
    return []


def _doc_findings(doc: Any, payload: Mapping[str, Any], path: str) -> list[Finding]:
    if not isinstance(doc, Mapping):
        return []  # Q001 (the schema)
    out = []
    for k, e in enumerate(_list(payload.get("evidence"))):
        if not isinstance(e, Mapping) or e.get("type") != "extracted" or not isinstance(e.get("source"), Mapping):
            continue
        source = e["source"]
        if source.get("doc_id") != doc.get("doc_id") or source.get("doc_sha256") != doc.get("doc_sha256"):
            out.append(_f("KHG-Q009", f"{path}/payload/evidence/{k}/source",
                          f"extracted evidence {e.get('id')!r} cites {source.get('doc_id')!r} "
                          f"({source.get('doc_sha256')!r}), not the item's doc {doc.get('doc_id')!r}"))
    return out


def _key_findings(item: Mapping[str, Any], payload: Mapping[str, Any], schema: Schema | None,
                  path: str) -> list[Finding]:
    want = keys_or_none(payload, schema)
    if want is None:
        return []
    out = []
    keys = item.get("keys")
    if isinstance(keys, Mapping):
        wrong = [k for k in KEY_FIELDS if k in keys and _stored_well_formed(keys, k) and keys[k] != want[k]]
        if wrong:
            out.append(_f("KHG-Q010", f"{path}/keys", f"{', '.join(wrong)} differ from the keys of the payload "
                                                      f"read as asserted"))
    for k, e in enumerate(_list(payload.get("evidence"))):
        if not isinstance(e, Mapping) or e.get("type") not in EVENT_TYPES:
            continue
        try:
            recomputed = event_hash(want["content_key"], e)  # type: ignore[arg-type]
        except _UNREADABLE:
            continue  # layer C reports the evidence
        if e.get("event_hash") != recomputed:
            out.append(_f("KHG-Q010", f"{path}/payload/evidence/{k}/event_hash",
                          f"the event_hash of evidence {e.get('id')!r} is not khg-event/1 of the payload"))
    return out


def _entity_findings(item: Mapping[str, Any], payload: Mapping[str, Any], entities: Any,
                     path: str) -> list[Finding]:
    known = {e.get("id") for e in _list(item.get("entities")) if isinstance(e, Mapping)}
    known.update(entities)
    out = []
    for j, b in enumerate(_list(payload.get("bindings"))):
        value = b.get("value") if isinstance(b, Mapping) else None
        if isinstance(value, Mapping) and len(value) == 1 and isinstance(value.get("entity"), str) and \
                value["entity"] not in known:
            out.append(_f("KHG-Q011", f"{path}/payload/bindings/{j}/value",
                          f"{value['entity']} is resolved by neither item.entities, the base nor the store"))
    return out


# ------------------------------------------------------------------------------------------------ verdicts


def _content_tuple(b: Mapping[str, Any]) -> str | None:
    """A binding's (role, position, value identity), the element ``content_key`` hashes, as canonical text; None
    for a value that cannot be read."""
    value = b.get("value")
    if not isinstance(value, Mapping):
        return None
    try:
        return jsonio.canonical([b.get("role"), b.get("position"), value_identity(value)])
    except _UNREADABLE:
        return None


def item_core_key(item: Mapping[str, Any], schema: Schema | None) -> str | None:
    """The item's ``core_key``: the stored ``keys.core_key`` (what ``queue_items`` attaches verdicts by), else the
    payload's, recomputed with ``schema``."""
    keys = item.get("keys")
    if isinstance(keys, Mapping) and _sha(keys.get("core_key")):
        return keys["core_key"]
    return (keys_or_none(item.get("payload"), schema) or {}).get("core_key")


def verdict_findings(entry: Mapping[str, Any], item: Mapping[str, Any], *, schema: Schema | None,
                     path: str = "") -> list[Finding]:
    """Q008 and Q010 on a verdict entry about ``item`` (paths are relative to the entry): Q008 for an
    ``evidence_id`` the payload lacks or whose evidence has no ``event_hash`` (verdicts judge extracted and inferred
    evidence), and for a binding tuple that is not a binding of the payload; Q010 for a ``core_key`` or
    ``event_hash`` other than the item's and the evidence's."""
    v = entry.get("verdict")
    payload = item.get("payload")
    if not isinstance(v, Mapping) or not isinstance(payload, Mapping):
        return []  # the queue schema reports it
    p = f"{path}/verdict"
    out = []
    evidence = [e for e in _list(payload.get("evidence")) if isinstance(e, Mapping)]
    ev = next((e for e in evidence if e.get("id") == v.get("evidence_id")), None)
    if isinstance(v.get("evidence_id"), str) and ev is None:
        out.append(_f("KHG-Q008", f"{p}/evidence_id", f"the payload has no evidence {v['evidence_id']!r}"))
    elif ev is not None and ev.get("type") not in EVENT_TYPES:
        out.append(_f("KHG-Q008", f"{p}/evidence_id", f"evidence {ev.get('id')!r} is {ev.get('type')!r}: a verdict "
                                                      f"judges extracted or inferred evidence"))
        ev = None
    want = item_core_key(item, schema)
    if _sha(v.get("core_key")) and want is not None and v["core_key"] != want:
        out.append(_f("KHG-Q010", f"{p}/core_key", "the verdict's core_key is not the item's"))
    if ev is not None and _sha(v.get("event_hash")) and v["event_hash"] != ev.get("event_hash"):
        out.append(_f("KHG-Q010", f"{p}/event_hash", f"the verdict's event_hash is not the event_hash of evidence "
                                                     f"{ev.get('id')!r} ({ev.get('event_hash')!r})"))
    held = {_content_tuple(b) for b in _list(payload.get("bindings")) if isinstance(b, Mapping)}
    held.discard(None)
    for i, b in enumerate(_list(v.get("bindings"))):
        if isinstance(b, Mapping) and _content_tuple(b) not in held:
            out.append(_f("KHG-Q008", f"{p}/bindings/{i}", "the verdict names a (role, position, value) that is not "
                                                           "a binding of the payload"))
    return out


# ------------------------------------------------------------------------------------------------ the header


def pin_findings(header: Mapping[str, Any], schema: Schema) -> list[Finding]:
    """D009 when the header's schema pin ``{id, version, sha256}`` is not ``schema``'s."""
    declared = header.get("schema")
    if not isinstance(declared, Mapping):
        return []  # Q008 (the schema)
    differ = [k for k, want in (("id", schema.id), ("version", schema.version), ("sha256", schema.sha256))
              if declared.get(k) != want]
    if not differ:
        return []
    return [_f("KHG-D009", "/lines/0/schema", f"the queue's schema pin differs from {schema.ref} "
                                              f"({schema.sha256}) in {', '.join(differ)}")]


def base_findings(header: Mapping[str, Any], base: Mapping[str, Any] | None) -> list[Finding]:
    """Q012 when the base supplied (a container, or None) does not match the header's ``base``
    ``{document_id, sha256}``: a base the header names and nobody supplied, a supplied base the header does not
    name, or a document id or ``record.container_sha256`` that differs."""
    pin = header.get("base")
    if pin is None and base is None:
        return []
    if pin is None:
        return [_f("KHG-Q012", "/lines/0", "a base was supplied, but the queue header names none")]
    if base is None:
        name = pin.get("document_id") if isinstance(pin, Mapping) else pin
        return [_f("KHG-Q012", "/lines/0/base", f"the header names the base {name!r}; none was supplied")]
    head = base.get("header")
    doc_id = head.get("document_id") if isinstance(head, Mapping) else None
    try:
        digest = container_sha256(base)
    except _UNREADABLE:
        digest = None
    if not isinstance(pin, Mapping) or doc_id != pin.get("document_id") or digest != pin.get("sha256"):
        return [_f("KHG-Q012", "/lines/0/base", f"the base supplied ({doc_id!r}, {digest}) is not the header's "
                                                f"base {pin!r}")]
    return []
