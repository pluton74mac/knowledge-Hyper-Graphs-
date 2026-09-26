"""``Linter``: the structural rule set (DESIGN §7), the gate's lint.

``Linter(schema, *, store=None, entities=None, doc_texts=None).lint(queue, qid, *, at=None)`` checks one item of a
``Queue`` and logs a ``lint`` entry through it: actor ``khg-lint`` 1.1.0, mode ``automatic``, rule set
``structural`` 1.1.0. The rule set is store-free:

- the item line against the queue schema: Q001-Q003, Q008 and Q010 for its structure, C codes for its entities;
- the C and S codes on the payload (layers C and S, S020 included), with S003 as a warning on candidates;
- Q002 (a candidate id of another queue), Q009, Q010 and Q011 (``queue.checks``);
- Q013 (1.1.0, ruling 23): with the document text, a quote selector without a position selector whose prefix,
  exact text and suffix do not occur in it (S021 checks a quote with a position selector). Only the linter runs it.

Entities resolve from ``item.entities`` first, then from the linter's ``entities`` (a container or a path to one,
entity records, or a mapping id -> record) or the queue's base, then from the store. S005 runs only on resolved
entities, and an unresolved one is Q011, an error. Fact values resolve from the base, then the store. The outcome is
``fail`` when a finding is an error (the item moves to ``rejected``), ``warn`` when one is a warning
(``needs_review``), else ``pass`` (``linted``). ``doc_texts`` (as ``validate`` takes them) enable the span check
S021 and Q013.

Nothing is logged when ``lint`` raises ``ValidationError``: D009 when the queue pins another schema; Q012 when the
base lint loads first (a container given as ``entities`` under the header's base ``document_id``, else the queue's
base) does not match the header, or when the header names a base and the linter has neither it, entities nor a
store; Q007 for an unknown item; Q005 when the item is not pending. The identity and quality rule sets come in 1.1.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..errors import KHGError, ValidationError, make_finding
from ..record import read_container
from ..schema import Schema, load_schema
from ..validate.layers import c as layer_c
from ..validate.layers import s as layer_s
from ..validate.layers.j import is_path
from ..validate.runner import _texts_arg as texts_arg
from .checks import base_findings, item_findings, pin_findings, quote_findings
from .lines import line_findings, raise_errors
from .model import LINT_STATES, LINTER, RULE_SET, LogEntry

__all__ = ["Linter"]

Finding = dict[str, str]
Records = dict[str, Mapping[str, Any]]


def _by_id(records: Iterable[Any], kind: str) -> Records:
    return {r["id"]: r for r in records if isinstance(r, Mapping) and r.get("kind") == kind
            and isinstance(r.get("id"), str)}


def _latest(container: Mapping[str, Any] | None, kind: str) -> Records:
    """The latest records of ``kind`` in a container, by id."""
    records = container.get("records") if isinstance(container, Mapping) else None
    return _by_id(layer_s.latest_records(records).values(), kind) if isinstance(records, list) else {}


def _is_container(x: Any) -> bool:
    return isinstance(x, Mapping) and "header" in x and "records" in x


def _document_id(container: Mapping[str, Any]) -> Any:
    head = container.get("header")
    return head.get("document_id") if isinstance(head, Mapping) else None


def _entity_source(entities: Any) -> tuple[Records, Mapping[str, Any] | None]:
    """``(entity records by id, the container they came from or None)``."""
    if entities is None:
        return {}, None
    if is_path(entities):
        entities = read_container(entities)
    if _is_container(entities):
        return _latest(entities, "entity"), entities
    if isinstance(entities, Mapping):
        return {k: v for k, v in entities.items() if isinstance(k, str) and isinstance(v, Mapping)}, None
    if isinstance(entities, Iterable) and not isinstance(entities, (str, bytes)):
        return _by_id(entities, "entity"), None
    raise TypeError(f"entities are a container, a path, entity records or a mapping, not {type(entities).__name__}")


def _plain(f: Mapping[str, Any]) -> dict[str, str]:
    """A finding as a lint entry records it: ``{code, severity, path, message}``."""
    return {"code": f["code"], "severity": f["severity"], "path": f["path"], "message": f["message"]}


def _outcome(findings: list[Finding]) -> str:
    severities = {f["severity"] for f in findings}
    return "fail" if "error" in severities else "warn" if "warning" in severities else "pass"


def _values(payload: Any, kind: str) -> list[str]:
    """The ids of the payload's ``entity`` or ``fact`` values, in binding order, without repeats."""
    bindings = payload.get("bindings") if isinstance(payload, Mapping) else None
    out: list[str] = []
    for b in bindings if isinstance(bindings, list) else []:
        value = b.get("value") if isinstance(b, Mapping) else None
        rid = value.get(kind) if isinstance(value, Mapping) and len(value) == 1 else None
        if isinstance(rid, str) and rid not in out:
            out.append(rid)
    return out


class Linter:
    """The structural linter; see the module docstring."""

    def __init__(self, schema: Any, *, store: Any = None, entities: Any = None, doc_texts: Any = None) -> None:
        self._schema: Schema = load_schema(schema)
        self._store = store
        self._entities, self._container = _entity_source(entities)
        self._texts = texts_arg(doc_texts)

    @property
    def schema(self) -> Schema:
        return self._schema

    def lint(self, queue: Any, qid: str, *, at: str | None = None) -> LogEntry:
        """Lint item ``qid`` of ``queue`` and log the entry, which is returned (a copy of the line written)."""
        header = queue.header
        raise_errors(pin_findings(header, self._schema))
        base = self._base(queue, header)
        item = queue.item(qid)
        findings = self._findings(item, queue_id=queue.queue_id, base=base)
        outcome = _outcome(findings)
        return queue._log(qid, "lint", LINTER, "automatic", at=at, state_after=LINT_STATES[outcome],
                          rule_set=dict(RULE_SET), findings=[_plain(f) for f in findings], outcome=outcome)

    def _findings(self, item: Mapping[str, Any], *, queue_id: str | None,
                  base: Mapping[str, Any] | None) -> list[Finding]:
        """The structural rule set on one item line (paths relative to the item), with ``base`` as the container
        lint loads first; nothing is logged."""
        payload = item.get("payload")
        entities = self._resolve(item, payload, base)
        out = line_findings(item)
        out += layer_c.record_findings(payload, definition="hyperedge", path="/payload")
        out += layer_s.nfc_findings(payload, "/payload")
        if isinstance(item.get("entities"), list):
            out += layer_s.nfc_findings(item["entities"], "/entities")
        out += layer_s.record_findings(payload, self._schema, entities=entities, facts=self._facts(payload, base),
                                       doc_texts=self._texts, path="/payload", candidate=True)
        out += item_findings(item, queue_id=queue_id, schema=self._schema, entities=entities)
        out += quote_findings(payload, self._texts)
        return out

    # ------------------------------------------------------------------------------------------ sources

    def _base(self, queue: Any, header: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """The container lint loads first, checked against the header's ``base`` (Q012 raised); None when the
        header names none."""
        pin = header.get("base")
        if not isinstance(pin, Mapping):
            return None
        mine = self._container
        base = mine if mine is not None and _document_id(mine) == pin.get("document_id") else queue.base
        if base is not None:
            raise_errors(base_findings(header, base))
            return base
        if self._store is None and not self._entities:
            raise ValidationError.from_findings([make_finding(
                "KHG-Q012", "/lines/0/base", f"the header names the base {pin.get('document_id')!r}; lint was given "
                                             "neither it, entities nor a store")])
        return None

    def _resolve(self, item: Mapping[str, Any], payload: Any, base: Mapping[str, Any] | None) -> Records:
        """The entity records of the payload's entity values, from the sources in order: ``item.entities``, the
        linter's entities, the base, the store."""
        own = item.get("entities")
        sources = [_by_id(own if isinstance(own, list) else [], "entity"), self._entities, _latest(base, "entity")]
        resolved: Records = {}
        for eid in _values(payload, "entity"):
            found = next((source[eid] for source in sources if eid in source), None)
            if found is None:
                stored = self._stored(eid)
                found = stored if stored is not None and stored.get("kind") == "entity" else None
            if found is not None:
                resolved[eid] = found
        return resolved

    def _facts(self, payload: Any, base: Mapping[str, Any] | None) -> Records:
        """The facts the payload's fact values name, from the base, then the store (S005 checks their relation)."""
        in_base = _latest(base, "hyperedge")
        out: Records = {}
        for fid in _values(payload, "fact"):
            found = in_base.get(fid) or self._stored(fid)
            if found is not None and found.get("kind") == "hyperedge":
                out[fid] = found
        return out

    def _stored(self, rid: str) -> Mapping[str, Any] | None:
        if self._store is None:
            return None
        try:
            record = self._store.get(rid)
        except KHGError:
            return None
        return record if isinstance(record, Mapping) else None
