"""``Linter``: the structural rule set (DESIGN §7), the gate's lint.

``Linter(schema, *, store=None, entities=None, doc_texts=None).lint(queue, qid, *, at=None)`` checks one item and
logs a ``lint`` entry (actor ``khg-lint`` 1.0.0, rule set ``structural`` 1.0.0) through the queue handle:

- the item line against the queue schema: Q001-Q003, and Q008 and C codes for its structure and entities;
- the C and S codes on the payload (layers C and S, with S020), S003 being a warning on candidates;
- Q002 (a payload id of another queue), Q009, Q010 and Q011 (``queue.checks``); Q012 for a base that does not match
  the header.

Entities resolve from ``item.entities`` first, then from ``entities`` (a container, entity records, or a mapping id
-> record) or the queue's base, then from the store; S005 runs only on resolved entities and an unresolved one is
Q011. A container given as ``entities`` whose ``document_id`` is the header's base must be that base (Q012), and
so must the queue's base; a header that names a base nobody supplied is Q012 unless a store is given. Fact values
resolve from the store. The outcome is ``fail`` with an error finding (the item goes to ``rejected``), ``warn`` with
a warning (``needs_review``), else ``pass`` (``linted``). The identity and quality rule sets come in 1.1.
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Mapping

from .. import jsonio
from ..errors import KHGError, ValidationError, make_finding
from ..record import read_container
from ..schema import Schema, load_schema
from ..validate.layers import c as layer_c
from ..validate.layers import s as layer_s
from .checks import base_findings, item_findings, pin_findings
from .lines import line_findings
from .model import LINT_STATES, LINTER, RULE_SET

__all__ = ["Linter"]

Finding = dict[str, str]


def _entity_map(records: Iterable[Any]) -> dict[str, Mapping[str, Any]]:
    return {r["id"]: r for r in records if isinstance(r, Mapping) and r.get("kind") == "entity"
            and isinstance(r.get("id"), str)}


def _entity_source(entities: Any) -> tuple[dict[str, Mapping[str, Any]], dict[str, Any] | None]:
    """``(entities by id, the container they came from or None)``."""
    if entities is None:
        return {}, None
    if isinstance(entities, (str, os.PathLike)):
        entities = read_container(entities)
    if isinstance(entities, Mapping) and "header" in entities and "records" in entities:
        records = entities["records"] if isinstance(entities["records"], list) else []
        latest = layer_s.latest_records(records)
        return _entity_map(latest.values()), dict(entities)
    if isinstance(entities, Mapping):
        return {k: v for k, v in entities.items() if isinstance(k, str) and isinstance(v, Mapping)}, None
    return _entity_map(entities), None


def _doc_texts(doc_texts: Any) -> dict[str, str]:
    """``{doc_id: text}`` from a mapping of texts, a ``khg-doc-texts`` document or a path to one."""
    if doc_texts is None:
        return {}
    if isinstance(doc_texts, (str, os.PathLike)) or hasattr(doc_texts, "read_bytes"):
        doc_texts = jsonio.load(doc_texts)
    if not isinstance(doc_texts, Mapping):
        raise TypeError("doc_texts maps doc ids to texts, or is a khg-doc-texts document or a path to one")
    if isinstance(doc_texts.get("texts"), Mapping):
        doc_texts = doc_texts["texts"]
    out = {}
    for doc_id, value in doc_texts.items():
        text = value.get("text") if isinstance(value, Mapping) else value
        if isinstance(doc_id, str) and isinstance(text, str):
            out[doc_id] = text
    return out


def _plain(f: Mapping[str, Any]) -> dict[str, str]:
    """A finding as a lint entry records it: ``{code, severity, path, message}``."""
    return {"code": f["code"], "severity": f["severity"], "path": f["path"], "message": f["message"]}


def _outcome(findings: list[Finding]) -> str:
    severities = {f["severity"] for f in findings}
    return "fail" if "error" in severities else "warn" if "warning" in severities else "pass"


class Linter:
    """The structural linter; store-free unless a store is given for entity and fact resolution."""

    def __init__(self, schema: Any, *, store: Any = None, entities: Any = None, doc_texts: Any = None) -> None:
        self._schema: Schema = load_schema(schema)
        self._store = store
        self._entities, self._container = _entity_source(entities)
        self._texts = _doc_texts(doc_texts)

    @property
    def schema(self) -> Schema:
        return self._schema

    def lint(self, queue: Any, qid: str, *, at: str | None = None) -> dict[str, Any]:
        """Lint item ``qid`` of ``queue`` and log the entry, which is returned. ``ValidationError``: D009 when the
        queue pins another schema; Q007 for an unknown item; Q005 when the item is not pending."""
        header = queue.header
        pin = pin_findings(header, self._schema)
        if pin:
            raise ValidationError.from_findings(pin)
        item = queue.item(qid)
        findings = self._findings(queue, item)
        outcome = _outcome(findings)
        return queue._log(qid, "lint", LINTER, "automatic", at=at, state_after=LINT_STATES[outcome],
                          rule_set=dict(RULE_SET), findings=[_plain(f) for f in findings], outcome=outcome)

    # ------------------------------------------------------------------------------------------ the rule set

    def _findings(self, queue: Any, item: Mapping[str, Any]) -> list[Finding]:
        payload = item.get("payload")
        base, extra, q012 = self._base(queue)
        entities = self._resolve(item, payload, extra, base)
        out = line_findings(item)
        out += layer_c.record_findings(payload, definition="hyperedge", path="/payload")
        out += layer_s.nfc_findings(payload, "/payload")
        if isinstance(item.get("entities"), list):
            out += layer_s.nfc_findings(item["entities"], "/entities")
        out += layer_s.record_findings(payload, self._schema, entities=entities, facts=self._facts(payload),
                                       doc_texts=self._texts, path="/payload", candidate=True)
        out += item_findings(item, queue_id=queue.queue_id, schema=self._schema, entities=entities)
        return out + q012

    def _base(self, queue: Any) -> tuple[Mapping[str, Any] | None, Mapping[str, Mapping[str, Any]], list[Finding]]:
        """``(the base the lint loads first, the linter's entities to use, Q012)``. A container given as
        ``entities`` with the header's base ``document_id`` is the base supplied, and must match the header (its
        entities are not used when it does not)."""
        header = queue.header
        pin = header.get("base")
        pinned_id = pin.get("document_id") if isinstance(pin, Mapping) else None
        mine = self._container
        mine_head = mine.get("header") if mine is not None else None
        if isinstance(mine_head, Mapping) and pinned_id is not None and mine_head.get("document_id") == pinned_id:
            found = base_findings(header, mine)
            if found:
                return queue.base, {}, [dict(f, path="") for f in found]
            return mine, self._entities, []
        if queue.base is not None:
            return queue.base, self._entities, []
        if pin is not None and self._store is None and not self._entities:
            return None, {}, [make_finding("KHG-Q012", "", f"the header names the base {pinned_id!r}; lint was given "
                                                           "neither it, entities nor a store")]
        return None, self._entities, []

    def _resolve(self, item: Mapping[str, Any], payload: Any, extra: Mapping[str, Mapping[str, Any]],
                 base: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
        """The entity records of the payload's entity values, from the sources in order: ``item.entities``, the
        linter's entities, the base, the store."""
        own = _entity_map(item.get("entities") if isinstance(item.get("entities"), list) else [])
        records = base.get("records") if isinstance(base, Mapping) else None
        from_base = _entity_map(layer_s.latest_records(records).values()) if isinstance(records, list) else {}
        resolved: dict[str, Mapping[str, Any]] = {}
        bindings = payload.get("bindings") if isinstance(payload, Mapping) else None
        for b in bindings if isinstance(bindings, list) else []:
            value = b.get("value") if isinstance(b, Mapping) else None
            eid = value.get("entity") if isinstance(value, Mapping) and len(value) == 1 else None
            if not isinstance(eid, str) or eid in resolved:
                continue
            for source in (own, extra, from_base):
                if eid in source:
                    resolved[eid] = source[eid]
                    break
            else:
                record = self._stored(eid)
                if record is not None and record.get("kind") == "entity":
                    resolved[eid] = record
        return resolved

    def _facts(self, payload: Any) -> dict[str, Mapping[str, Any]]:
        """The stored facts the payload's fact values name (S005 checks their relation)."""
        out: dict[str, Mapping[str, Any]] = {}
        bindings = payload.get("bindings") if isinstance(payload, Mapping) else None
        for b in bindings if isinstance(bindings, list) else []:
            value = b.get("value") if isinstance(b, Mapping) else None
            fid = value.get("fact") if isinstance(value, Mapping) and len(value) == 1 else None
            if isinstance(fid, str) and fid not in out:
                record = self._stored(fid)
                if record is not None and record.get("kind") == "hyperedge":
                    out[fid] = record
        return out

    def _stored(self, rid: str) -> Mapping[str, Any] | None:
        if self._store is None:
            return None
        try:
            record = self._store.get(rid)
        except KHGError:
            return None
        return record if isinstance(record, Mapping) else None
