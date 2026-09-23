"""The four events of ``apply`` (DESIGN §2.7, §6.2): ``supersede``, ``transition``, ``end_validity`` and
``add_evidence``. Each is one atomic write.

- ``supersede`` {``id``, ``superseded``, ``superseding?``, ``records?``, ``reason``, ``note?``, ``evidence``}: writes
  ``records`` (asserted) and the ``khg:supersedes`` record ``id``, which binds the superseding facts (existing,
  then new), then the superseded ones; those become ``superseded`` with ``status_ref: id``.
- ``transition`` {``targets``, ``to``, ``id?``, ``records?``, ``reason?``, ``note?``, ``evidence``,
  ``resolve_superseding?``, ``dispute_id?``}: ``disputed`` writes a new ``khg:disputes`` record ``id`` binding the
  targets and ``records``, all disputed; ``retracted`` writes a ``khg:retracts`` record ``id`` (retracting a
  lifecycle record is undo); ``asserted`` takes a disputed, quoted or goal fact back, dropping ``status_ref`` and
  the ``goal`` block.
- ``end_validity`` {``target``, ``end``, ``end_cause?``, ``evidence``}: adds or refines the end binding, or replaces a
  ``novalue`` end; ``end_cause`` becomes a ``khg:end_cause`` binding; the status stays.
- ``add_evidence`` {``target``, ``evidence``}: appends evidence; superseded and retracted facts are frozen (D013).

Records carried by events arrive as ``asserted`` without ``status_ref``; the store sets both. Evidence without
``supports`` supports every bid of a new record, the end (and end cause) bindings for ``end_validity``, and nothing
for a transition that writes no lifecycle record (§2.8.1). The checks run in the order of §6.2: capability,
``NotFound``, D014, then the write path of ``_writes``.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from ..errors import NotFound
from ..record import canonical_value, lifecycle, normalize
from ..record.canonical import STORE_FIELDS
from ..record.lifecycle import Problem
from ..schema import LIFECYCLE_RELATIONS
from ._writes import Pending, WriteMixin, fail
from .flags import value_flags
from .protocol import Receipt

__all__ = ["EVENTS", "EventsMixin"]

EVENTS = ("supersede", "transition", "end_validity", "add_evidence")
_UNDO_ROLE = {"khg:supersedes": "khg:superseded", "khg:disputes": "khg:disputed"}


def _d014(rid: Any, message: str) -> Problem:
    return Problem("KHG-D014", rid, "/status", message)


def _content(record: Mapping[str, Any]) -> dict[str, Any]:
    """A stored record without its store fields, as the base of a new version."""
    out = copy.deepcopy(dict(record))
    for f in STORE_FIELDS:
        out.pop(f, None)
    return out


class EventsMixin(WriteMixin):
    """``apply`` and the four events of ``MemoryStore``."""

    def apply(self, event: Mapping[str, Any], *, actor: str, at: str | None = None) -> Receipt:
        """Apply one event (a dict with ``op``) atomically; see the module docstring."""
        actor = self._actor(actor)
        when = self._at(at)
        if not isinstance(event, Mapping):
            raise fail("KHG-C010", f"an event is an object, not {type(event).__name__}")
        op = event.get("op")
        handler = {"supersede": self._supersede, "transition": self._transition,
                   "end_validity": self._end_validity, "add_evidence": self._add_evidence}.get(op)  # type: ignore
        if handler is None:
            raise fail("KHG-C010" if op is None else "KHG-C002",
                       f"event op {op!r} is not one of {', '.join(EVENTS)}", "/op")
        return handler(event, actor, when)

    # ------------------------------------------------------------------------------------------ fields

    @staticmethod
    def _text(event: Mapping[str, Any], field: str, *, required: bool = True) -> str | None:
        value = event.get(field)
        if value is None and not required:
            return None
        if not isinstance(value, str) or not value:
            raise fail("KHG-C010", f"event field {field!r} is a non-empty string", f"/{field}")
        return value

    @staticmethod
    def _ids(event: Mapping[str, Any], field: str, *, required: bool = True) -> list[str]:
        value = event.get(field)
        if value is None and not required:
            return []
        if not isinstance(value, list) or (required and not value) or not all(isinstance(x, str) for x in value):
            raise fail("KHG-C010", f"event field {field!r} is a {'non-empty ' if required else ''}list of ids",
                       f"/{field}")
        return list(value)

    @staticmethod
    def _evidence(event: Mapping[str, Any], *, nonempty: bool = False) -> list[dict[str, Any]]:
        value = event.get("evidence")
        if not isinstance(value, list) or not all(isinstance(e, Mapping) for e in value) or (nonempty and not value):
            raise fail("KHG-C010", f"event field 'evidence' is a {'non-empty ' if nonempty else ''}list of evidence "
                       "records", "/evidence")
        return [copy.deepcopy(dict(e)) for e in value]

    def _held(self, rid: str) -> dict[str, Any]:
        r = self._table.current(rid)
        if r is None:
            raise NotFound(f"{rid!r} is not held by the store", codes=["KHG-D002"], info={"id": rid})
        return r

    def _new_records(self, event: Mapping[str, Any]) -> list[dict[str, Any]]:
        """The records an event carries: new ids, arriving as asserted (a ``status_ref`` is dropped)."""
        raw = event.get("records")
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise fail("KHG-C010", "event field 'records' is a list of records", "/records")
        out, problems = [], []
        for i, r in enumerate(raw):
            rec = self._incoming(r, f"/records/{i}")
            rec.pop("status_ref", None)
            p = lifecycle.put_problem(rec)
            if p is not None:
                problems.append(p)
            elif rec.get("kind") != "hyperedge" or rec.get("status") != "asserted":
                problems.append(_d014(rec["id"], "records carried by an event are hyperedges arriving as asserted"))
            elif rec["id"] in self._table:
                problems.append(_d014(rec["id"], f"{rec['id']} already exists: an event record is a new id"))
            out.append(rec)
        if problems:
            raise lifecycle.error_for(problems)
        return out

    @staticmethod
    def _lifecycle_record(relation: str, rid: str, bound: list[tuple[str, str]], evidence: list[dict[str, Any]], *,
                          reason: Any = None, note: Any = None) -> dict[str, Any]:
        """A lifecycle record written by an event, its bids b1... in ``bound`` order."""
        rec: dict[str, Any] = {"kind": "hyperedge", "id": rid, "relation": relation, "status": "asserted",
                               "bindings": [{"bid": f"b{n}", "role": role, "value": {"fact": fact}}
                                            for n, (role, fact) in enumerate(bound, 1)],
                               "evidence": copy.deepcopy(evidence)}
        if reason is not None:
            rec["reason"] = reason
        if note is not None:
            rec["note"] = note
        return normalize(rec)

    def _fresh_id(self, rid: str, taken: set[str]) -> None:
        if rid in self._table or rid in taken:
            raise lifecycle.error_for([_d014(rid, f"{rid} already exists: a lifecycle record is a new id")])
        taken.add(rid)

    @staticmethod
    def _append_evidence(record: dict[str, Any], evidence: list[dict[str, Any]], supports: list[str]) -> None:
        held = {e.get("id") for e in record.get("evidence") or [] if isinstance(e, Mapping)}
        clash = sorted(str(e.get("id")) for e in evidence if e.get("id") in held)
        if clash:
            raise lifecycle.error_for([Problem("KHG-D013", record.get("id"), "/evidence",
                                               f"evidence {', '.join(clash)} already exists: evidence is append-only")])
        for e in evidence:
            e.setdefault("supports", list(supports))
        record["evidence"] = list(record.get("evidence") or []) + evidence

    # ------------------------------------------------------------------------------------------ supersede

    def _supersede(self, event: Mapping[str, Any], actor: str, at: int | None) -> Receipt:
        eid = self._text(event, "id")
        superseded = self._ids(event, "superseded")
        superseding = self._ids(event, "superseding", required=False)
        evidence = self._evidence(event)
        self.need("atomic_writes")
        self._need_data(event.get("records") or [])
        old_sed = [self._held(i) for i in superseded]
        old_sing = [self._held(i) for i in superseding]
        new = self._new_records(event)
        taken: set[str] = set()
        for rid in [*superseded, *superseding, *(r["id"] for r in new)]:
            if rid in taken:
                raise fail("KHG-D001", f"{rid} is named twice by the event")
            taken.add(rid)
        self._fresh_id(eid, taken)  # type: ignore[arg-type]
        problems = [_d014(f["id"], f"only asserted or disputed facts are superseded, not a {f.get('status')} fact")
                    for f in old_sed if f.get("status") not in ("asserted", "disputed")
                    or f.get("relation") in LIFECYCLE_RELATIONS]
        problems += [_d014(f["id"], "a lifecycle record never supersedes") for f in old_sing
                     if f.get("relation") in LIFECYCLE_RELATIONS]
        if problems:
            raise lifecycle.error_for(problems)
        pending = Pending(self._table)
        for r in new:
            pending.add(r)
        sing_ids = superseding + [r["id"] for r in new]
        pending.add(self._lifecycle_record(
            "khg:supersedes", eid, [("khg:superseding", i) for i in sing_ids] +  # type: ignore[arg-type]
            [("khg:superseded", i) for i in superseded], evidence, reason=event.get("reason"), note=event.get("note")))
        for f in old_sed:
            pending.add(lifecycle.with_status(f, "superseded", eid), fresh=False)
        self._validate(pending)
        self._check_references(pending)
        d011 = [p for p in lifecycle.supersede_problems(old_sing + new, old_sed, event.get("reason"), self.schema,
                                                        event_id=eid) if p.code == "KHG-D011"]
        return self._commit(pending, actor=actor, at=at, pointers=True, d011=d011)

    # ------------------------------------------------------------------------------------------ transition

    def _transition(self, event: Mapping[str, Any], actor: str, at: int | None) -> Receipt:
        targets = self._ids(event, "targets")
        to = event.get("to")
        if not isinstance(to, str):
            raise fail("KHG-C010", "event field 'to' is a status", "/to")
        if len(set(targets)) != len(targets):
            raise fail("KHG-D001", "a target is named twice by the event", "/targets")
        if to == "disputed":
            return self._dispute(event, targets, actor, at)
        if to == "retracted":
            return self._retract(event, targets, actor, at)
        if to == "asserted":
            return self._assert(event, targets, actor, at)
        olds = [self._held(i) for i in targets]
        raise lifecycle.error_for([_d014(f["id"], f"{f.get('status')} -> {to} is not in the transition table")
                                   for f in olds])

    def _dispute(self, event: Mapping[str, Any], targets: list[str], actor: str, at: int | None) -> Receipt:
        eid = self._text(event, "id")
        evidence = self._evidence(event)
        self.need("atomic_writes")
        self._need_data(event.get("records") or [])
        olds = [self._held(i) for i in targets]
        new = self._new_records(event)
        taken = set(targets)
        for r in new:
            if r["id"] in taken:
                raise fail("KHG-D001", f"{r['id']} is named twice by the event")
            taken.add(r["id"])
        self._fresh_id(eid, taken)  # type: ignore[arg-type]
        problems = [p for f in olds if (p := lifecycle.transition_problem(
            f.get("status"), "disputed", relation=f.get("relation"), id=f["id"])) is not None]
        if problems:
            raise lifecycle.error_for(problems)
        pending = Pending(self._table)
        ids = targets + [r["id"] for r in new]
        pending.add(self._lifecycle_record("khg:disputes", eid, [("khg:disputed", i) for i in ids],  # type: ignore
                                           evidence, reason=event.get("reason"), note=event.get("note")))
        for f in olds:
            pending.add(lifecycle.with_status(f, "disputed", eid), fresh=False)
        for r in new:
            pending.add(lifecycle.with_status(r, "disputed", eid))
        self._validate(pending)
        self._check_references(pending)
        return self._commit(pending, actor=actor, at=at, pointers=True)

    def _retract(self, event: Mapping[str, Any], targets: list[str], actor: str, at: int | None) -> Receipt:
        eid = self._text(event, "id")  # a retraction names its khg:retracts record (C010)
        evidence = self._evidence(event)
        resolve = event.get("resolve_superseding")
        if resolve not in (None, "retract", "dispute"):
            raise fail("KHG-C002", f"resolve_superseding is retract or dispute, not {resolve!r}",
                       "/resolve_superseding")
        dispute_id = self._text(event, "dispute_id", required=resolve == "dispute")
        self.need("atomic_writes")
        olds = [self._held(i) for i in targets]
        taken = set(targets)
        self._fresh_id(eid, taken)  # type: ignore[arg-type]
        if resolve == "dispute":
            self._fresh_id(dispute_id, taken)  # type: ignore[arg-type]
        problems = self._retractable(olds)
        if problems:
            raise lifecycle.error_for(problems)
        restored: list[dict[str, Any]] = []
        extra: list[dict[str, Any]] = []
        superseding: list[dict[str, Any]] = []
        for f in olds:
            role = _UNDO_ROLE.get(f.get("relation"))  # type: ignore[arg-type]
            if role is None:
                continue
            bound = {(b.get("value") or {}).get("fact") for b in f.get("bindings", []) if b.get("role") == role}
            for fact in sorted(self._table.by_ref(f["id"]) & bound):  # the status_ref index
                x = self._table.current(fact)
                if x is not None and x.get("status_ref") == f["id"]:
                    restored.append(x)
            if f.get("relation") == "khg:supersedes" and resolve is not None:
                superseding += [self._held(b["value"]["fact"]) for b in f.get("bindings", [])
                                if b.get("role") == "khg:superseding"]
        if resolve == "retract":
            extra = superseding
            problems = self._retractable(extra)
        else:
            problems = [p for f in superseding if (p := lifecycle.transition_problem(
                f.get("status"), "disputed", relation=f.get("relation"), id=f["id"])) is not None]
        if problems:
            raise lifecycle.error_for(problems)
        pending = Pending(self._table)
        if resolve == "dispute":
            ids = [f["id"] for f in superseding] + [x["id"] for x in restored]
            pending.add(self._lifecycle_record("khg:disputes", dispute_id, [("khg:disputed", i) for i in ids],  # type: ignore
                                               evidence, reason="key_conflict"))
            for x in superseding + restored:
                pending.add(lifecycle.with_status(x, "disputed", dispute_id), fresh=False)
        else:
            for x in restored:
                pending.add(lifecycle.with_status(x, "asserted"), fresh=False)
        pending.add(self._lifecycle_record("khg:retracts", eid, [("khg:retracted", f["id"]) for f in olds + extra],  # type: ignore
                                           evidence, reason=event.get("reason"), note=event.get("note")))
        for f in olds + extra:
            pending.add(lifecycle.with_status(f, "retracted", eid), fresh=False)
        self._validate(pending)
        self._check_references(pending)
        return self._commit(pending, actor=actor, at=at, pointers=True)

    @staticmethod
    def _retractable(records: list[dict[str, Any]]) -> list[Problem]:
        """D014 for the records that cannot be retracted (``retracted`` is terminal)."""
        out = []
        for f in records:
            if f.get("status") == "retracted":
                out.append(_d014(f["id"], "retracted is terminal"))
                continue
            p = lifecycle.transition_problem(f.get("status"), "retracted", relation=f.get("relation"), id=f["id"])
            if p is not None:
                out.append(p)
        return out

    def _assert(self, event: Mapping[str, Any], targets: list[str], actor: str, at: int | None) -> Receipt:
        evidence = self._evidence(event)
        if len(targets) > 1:
            self.need("atomic_writes")
        olds = [self._held(i) for i in targets]
        problems = [_d014(f["id"], f"{f.get('status')} -> asserted is not a transition: only disputed, quoted and "
                                   "goal facts are asserted by one (undo retracts the lifecycle record)")
                    for f in olds if f.get("status") not in ("disputed", "quoted", "goal")
                    or f.get("relation") in LIFECYCLE_RELATIONS]
        if problems:
            raise lifecycle.error_for(problems)
        pending = Pending(self._table)
        pairs = []
        for f in olds:
            base = lifecycle.with_status(f, "asserted")
            new = copy.deepcopy(base)
            self._append_evidence(new, copy.deepcopy(evidence), [])
            new = normalize(new)
            pending.add(new, fresh=False)
            pairs.append((base, new))
        self._validate(pending)
        self._check_versions(pairs)
        self._check_references(pending)
        return self._commit(pending, actor=actor, at=at)

    # ------------------------------------------------------------------------------------------ one fact

    def _end_validity(self, event: Mapping[str, Any], actor: str, at: int | None) -> Receipt:
        target = self._text(event, "target")
        if "end" not in event:
            raise fail("KHG-C010", "end_validity needs 'end', a value", "/end")
        evidence = self._evidence(event)
        self.need("valid_time")
        for flag in sorted(value_flags(event["end"]) | value_flags(event.get("end_cause"))):
            self.need(flag)
        old = self._held(target)  # type: ignore[arg-type]
        status, relation = old.get("status"), old.get("relation")
        if old.get("kind") != "hyperedge" or relation in LIFECYCLE_RELATIONS:
            raise lifecycle.error_for([_d014(target, "end_validity applies to a fact")])
        if status in lifecycle.FROZEN:
            raise lifecycle.error_for([Problem("KHG-D013", target, "", f"a {status} fact is frozen")])
        if status not in ("asserted", "disputed"):
            raise lifecycle.error_for([_d014(target, f"end_validity applies to asserted or disputed facts, not a "
                                                     f"{status} fact")])
        tm = self.schema.time_model(relation)
        if tm.get("model") != "interval":
            raise fail("KHG-S002", f"{relation} has no interval time model: it takes no end", "/end")
        new = _content(old)
        bindings = new.setdefault("bindings", [])
        numbers = [int(b["bid"][1:]) for b in bindings if str(b.get("bid", "")).startswith("b")
                   and str(b["bid"])[1:].isdigit()]
        after = max(numbers, default=0)
        end = next((b for b in bindings if b.get("role") == tm["end"]), None)
        if end is None:
            after += 1
            end = {"bid": f"b{after}", "role": tm["end"], "value": None}
            bindings.append(end)
        end["value"] = canonical_value(event["end"])
        supports = [end["bid"]]
        if event.get("end_cause") is not None:
            after += 1
            bindings.append({"bid": f"b{after}", "role": "khg:end_cause", "value": canonical_value(event["end_cause"])})
            supports.append(f"b{after}")
        self._append_evidence(new, evidence, supports)
        new = normalize(new)
        pending = Pending(self._table)
        pending.add(new)
        self._validate(pending)
        self._check_versions([(old, new)], allow_novalue_end=True)
        self._check_references(pending)
        return self._commit(pending, actor=actor, at=at)

    def _add_evidence(self, event: Mapping[str, Any], actor: str, at: int | None) -> Receipt:
        target = self._text(event, "target")
        evidence = self._evidence(event, nonempty=True)
        old = self._held(target)  # type: ignore[arg-type]
        if old.get("kind") != "hyperedge":
            raise lifecycle.error_for([_d014(target, "evidence is appended to hyperedges")])
        new = _content(old)
        bids = [b.get("bid") for b in new.get("bindings") or [] if isinstance(b, Mapping)]
        self._append_evidence(new, evidence, [b for b in bids if isinstance(b, str)])
        new = normalize(new)
        pending = Pending(self._table)
        pending.add(new, fresh=False)
        self._validate(pending)
        self._check_versions([(old, new)])
        return self._commit(pending, actor=actor, at=at)
