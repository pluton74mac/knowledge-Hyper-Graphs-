"""Layer S: a record against its relation-type schema (DESIGN §2, §3, §8.1).

``record_findings`` checks one hyperedge:

- S001 the relation is declared; S007 it has a binding (both end the checks of the record); S002 each role is
  allowed; S025 each bid is unique; S016 a binding's direction where the usage declares one;
- per value: S005 the filler kind, the entity type (resolved entities only), the datatype, the relation of a
  nested fact and a forbidden special value; S006 a time literal out of range (``record.parse_time``, which also
  emits C004 for the lexical form); S023 ``precision_min`` and the allowed units;
- per usage: S003 a required role missing (a warning on candidates), S018 instead for a goal; S004 max; S013
  ``novalue`` with another filler; S015 positions; S014 a repeated filler or two ``somevalue`` fillers;
- S019 a variable used twice; S009 an empty possible validity; S011 an asserted fact without supporting evidence;
  S010 confidence scales; S022 supports an unknown bid; S021 spans against the document texts; S024 the relation's
  constraints, with the schema's severity; S026 a lifecycle reason outside the relation's list.

S021 reads the text that the evidence's ``doc_sha256`` hashes (§2.8): ``doc_texts`` maps a ``doc_id`` or a
``doc_sha256`` to a text, and the text under the digest is used, else the ``doc_id``'s text when it hashes to the
digest. A text of another revision of the document is not the evidence's text, so the span is not judged, as when
no text is given. Evidence without a ``doc_sha256`` is read against its ``doc_id``'s text.

``nfc_findings`` reports S020 for every string and key not in NFC. Findings on a structure that layer C rejects are
not repeated: S skips what it cannot read. Without a schema the step reports D009, once per run.
"""
from __future__ import annotations

import functools
import unicodedata
from typing import Any, Iterable, Mapping

from ... import jsonio
from ...errors import KHGError, make_finding
from ...record import bounds, identity_key, parse_time, text_sha256
from ...schema import Schema
from ..context import Context
from ..engines import pointer

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "container_findings", "latest_records", "nfc_findings",
           "record_findings", "run"]

LETTER = "S"
OWNER = "W4"
IMPLEMENTED = True

_VALUE_KINDS = ("entity", "literal", "fact", "special", "unbound")
_SPECIALS = ("somevalue", "novalue")

Finding = dict[str, str]


def _f(code: str, path: str, message: str, severity: str = "error") -> Finding:
    return make_finding(code, path, message, severity)


def _integral(x: Any) -> int | None:
    """``x`` as an int when it is an integer or an integral float (F10: ``2.0`` is ``2``, as canonical JSON and both
    engines read it); None for a bool, a fractional or non-finite float and anything else."""
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return None


def _number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _kind(value: Any) -> str | None:
    """The kind of a well-formed value, else None (layer C reports it)."""
    if isinstance(value, Mapping) and len(value) == 1:
        (k,) = value.keys()
        return k if k in _VALUE_KINDS else None
    return None


def _identity(value: Any) -> str | None:
    """The canonical text of a value's identity, or None when the value is malformed (reported elsewhere)."""
    try:
        return identity_key(value)
    except (KHGError, ValueError, TypeError, KeyError):
        return None


def _is_special(value: Any, which: str) -> bool:
    return _kind(value) == "special" and value["special"] == which


def _strings(x: Any) -> list[str]:
    return [t for t in x if isinstance(t, str)] if isinstance(x, list) else []


# ------------------------------------------------------------------------------------------------ S020


def nfc_findings(value: Any, path: str = "") -> list[Finding]:
    """S020 for every string and object key under ``value`` that is not in Unicode NFC, in document order."""
    out: list[Finding] = []
    stack: list[tuple[Any, str]] = [(value, path)]
    while stack:
        x, p = stack.pop()
        if isinstance(x, str):
            if not unicodedata.is_normalized("NFC", x):
                out.append(_f("KHG-S020", p, "string not in Unicode NFC"))
        elif isinstance(x, Mapping):
            children = []
            for k, v in x.items():
                kp = p + pointer([k])
                if isinstance(k, str) and not unicodedata.is_normalized("NFC", k):
                    out.append(_f("KHG-S020", kp, "object key not in Unicode NFC"))
                children.append((v, kp))
            stack.extend(reversed(children))
        elif isinstance(x, list):
            stack.extend(reversed([(v, f"{p}/{i}") for i, v in enumerate(x)]))
    return out


# ------------------------------------------------------------------------------------------------ one record


def record_findings(record: Any, schema: Schema, *, entities: Mapping[str, Any] | None = None,
                    facts: Mapping[str, Any] | None = None, doc_texts: Mapping[str, str] | None = None,
                    path: str = "", candidate: bool = False) -> list[Finding]:
    """Layer S on one hyperedge (entities and other records give []), without S020 (see ``nfc_findings``).

    ``entities`` and ``facts`` resolve entity and fact values by id (S005 runs only on resolved ones);
    ``doc_texts`` maps a ``doc_id`` or a ``doc_sha256`` to a text (S021 reads the text the evidence's ``doc_sha256``
    hashes); ``candidate`` makes S003 a warning, as on queue payloads.
    """
    if not isinstance(record, Mapping) or record.get("kind") != "hyperedge":
        return []
    rel = record.get("relation")
    if not isinstance(rel, str):
        return []
    if not schema.has_relation(rel):
        return [_f("KHG-S001", f"{path}/relation", f"relation {rel!r} is not declared in {schema.ref}")]
    bindings = record.get("bindings")
    if not isinstance(bindings, list):
        return []
    if not bindings:
        return [_f("KHG-S007", f"{path}/bindings", "a hyperedge needs at least one binding")]
    ents = entities or {}
    known = facts or {}
    status = record.get("status")
    lifecycle = schema.kind(rel) == "lifecycle"
    usages = schema.usages(rel)
    by_usage: dict[str, Mapping[str, Any]] = {}
    for u in usages:
        by_usage.setdefault(u["role"], u)

    out: list[Finding] = []
    seen_bids: set[str] = set()
    by_role: dict[str, list[Mapping[str, Any]]] = {}
    for j, b in enumerate(bindings):
        p = f"{path}/bindings/{j}"
        if not isinstance(b, Mapping):
            continue
        bid = b.get("bid")
        if isinstance(bid, str):
            if bid in seen_bids:
                out.append(_f("KHG-S025", f"{p}/bid", f"bid {bid!r} is used twice"))
            seen_bids.add(bid)
        role = b.get("role")
        if not isinstance(role, str):
            continue
        u = by_usage.get(role)
        if u is None:
            out.append(_f("KHG-S002", f"{p}/role", f"role {role!r} is not allowed for {rel!r}"))
            continue
        by_role.setdefault(role, []).append(b)
        out += _value_findings(schema, u, b.get("value"), ents, known, p)
        if "direction" in b and u.get("direction") is not None:
            out.append(_f("KHG-S016", f"{p}/direction", f"the usage of {role!r} declares {u['direction']!r}"))

    for u in usages:
        out += _usage_findings(u, by_role.get(u["role"], []), status, candidate, path)
    out += _variable_findings(bindings, path)
    if not lifecycle:
        out += _validity_findings(record, schema, path)
    listed = record.get("evidence")
    evidence = [(k, e) for k, e in enumerate(listed if isinstance(listed, list) else []) if isinstance(e, Mapping)]
    if status == "asserted" and not lifecycle and not any(not _negated(e) for _, e in evidence):
        out.append(_f("KHG-S011", path, "an asserted fact needs supporting (non-negated) evidence"))
    out += _confidence_findings(schema, record.get("confidence"), f"{path}/confidence")
    for k, e in evidence:
        out += _confidence_findings(schema, e.get("confidence"), f"{path}/evidence/{k}/confidence")
    bids = {b.get("bid") for b in bindings if isinstance(b, Mapping) and isinstance(b.get("bid"), str)}
    for k, e in evidence:
        q = f"{path}/evidence/{k}"
        unknown = [x for x in _strings(e.get("supports")) if x not in bids]
        if unknown:
            out.append(_f("KHG-S022", f"{q}/supports", f"supports unknown bids {unknown}"))
        out += _span_findings(e, doc_texts or {}, q)
    for con in schema.relation(rel).get("constraints") or []:
        if isinstance(con, Mapping):
            out += _constraint_findings(con, by_role, path)
    if lifecycle and "reason" in record and record.get("reason") not in schema.reasons(rel):
        out.append(_f("KHG-S026", f"{path}/reason", f"reason {record.get('reason')!r} is not one of "
                                                    f"{schema.reasons(rel)}"))
    return out


def _value_findings(schema: Schema, u: Mapping[str, Any], value: Any, ents: Mapping[str, Any],
                    facts: Mapping[str, Any], p: str) -> list[Finding]:
    kind = _kind(value)
    fillers = [f for f in u.get("fillers") or [] if isinstance(f, Mapping)]
    if kind == "entity":
        options = [f["entity"] for f in fillers if "entity" in f]
        if not options:
            return [_f("KHG-S005", p, f"{u['role']!r} takes no entity")]
        want = [t for o in options for t in _strings(o)]
        eid = value["entity"]
        ent = ents.get(eid) if isinstance(eid, str) else None
        if isinstance(ent, Mapping) and want:
            types = _strings(ent.get("types"))
            if not any(schema.is_subtype(t, w) for t in types for w in want):
                return [_f("KHG-S005", p, f"{eid} ({', '.join(types)}) is not a {' or '.join(want)}")]
        return []
    if kind == "literal":
        lit = value["literal"]
        if not isinstance(lit, Mapping):
            return []
        dt = lit.get("datatype")
        options = [f for f in fillers if f.get("literal") == dt]
        if not options:
            return [_f("KHG-S005", p, f"datatype {dt!r} is not allowed for {u['role']!r}")]
        # the fillers are a disjunction (§3): S023 only when no filler of the datatype allows the literal
        if dt == "time":
            try:
                parse_time(lit.get("time"), lit.get("precision"), lit.get("calendar"))
            except KHGError as e:
                return [_f(e.code or "KHG-S006", f"{p}/value/literal", e.message)]
            except (ValueError, OverflowError) as e:  # e.g. a year with more digits than Python converts
                return [_f("KHG-S006", f"{p}/value/literal", f"time {str(lit.get('time'))[:40]!r}...: {e}"[:200])]
            mins = [_integral(o.get("precision_min")) for o in options]
            precision = lit.get("precision")
            if _number(precision) and all(pm is not None and precision < pm for pm in mins):
                least = min(pm for pm in mins if pm is not None)
                return [_f("KHG-S023", p, f"precision {precision} is below precision_min {least}")]
        if dt == "quantity":
            allowed = [o.get("units") for o in options]
            unit = lit.get("unit")
            if all(isinstance(a, list) and a and unit not in a for a in allowed):
                units = list(dict.fromkeys(x for a in allowed for x in a))
                return [_f("KHG-S023", p, f"unit {unit!r} is not one of {units}")]
        return []
    if kind == "fact":
        options = [f["fact"] for f in fillers if "fact" in f]
        if not options:
            return [_f("KHG-S005", p, f"{u['role']!r} takes no fact reference")]
        want = [x for o in options for x in _strings(o)]
        fid = value["fact"]
        target = facts.get(fid) if isinstance(fid, str) else None
        if isinstance(target, Mapping) and want and target.get("relation") not in want:
            return [_f("KHG-S005", p, f"{fid} is a {target.get('relation')!r} fact, not {' or '.join(want)}")]
        return []
    if kind == "special":
        sv = value["special"]
        if sv in _SPECIALS and not u.get(sv, True):
            return [_f("KHG-S005", p, f"{sv} is not allowed for {u['role']!r}")]
    return []


def _usage_findings(u: Mapping[str, Any], bs: list[Mapping[str, Any]], status: Any, candidate: bool,
                    path: str) -> list[Finding]:
    role, n = u["role"], len(bs)
    out = []
    minimum = _integral(u.get("min", 0))
    if minimum is not None and n < minimum:
        if status == "goal":
            out.append(_f("KHG-S018", path, f"goal omits {role!r}: leave it unbound instead"))
        else:
            severity = "warning" if candidate or status == "candidate" else "error"
            out.append(_f("KHG-S003", path, f"{role!r} is bound {n} times, min {minimum}", severity))
    maximum = _integral(u.get("max"))
    if maximum is not None and n > maximum:
        out.append(_f("KHG-S004", path, f"{role!r} is bound {n} times, max {maximum}"))
    values = [b.get("value") for b in bs]
    if n > 1 and any(_is_special(v, "novalue") for v in values):
        out.append(_f("KHG-S013", path, f"novalue with another filler of {role!r}"))
    if u.get("ordered"):
        positions = [_integral(b.get("position")) for b in bs]
        if None in positions or sorted(positions) != list(range(1, n + 1)):  # type: ignore[type-var]
            out.append(_f("KHG-S015", path, f"the positions of {role!r} are not 1..{n}"))
    else:
        if any("position" in b for b in bs):
            out.append(_f("KHG-S015", path, f"{role!r} is not ordered: no positions"))
        ids = [x for x in (_identity(v) for v in values if _kind(v) in ("entity", "literal", "fact")) if x]
        if len(ids) != len(set(ids)) or sum(_is_special(v, "somevalue") for v in values) > 1:
            out.append(_f("KHG-S014", path, f"a filler of {role!r} is repeated"))
    return out


def _variable_findings(bindings: list[Any], path: str) -> list[Finding]:
    names = []
    for b in bindings:
        v = b.get("value") if isinstance(b, Mapping) else None
        if _kind(v) == "unbound" and isinstance(v["unbound"], Mapping) and isinstance(v["unbound"].get("var"), str):
            names.append(v["unbound"]["var"])
    if len(names) != len(set(names)):
        return [_f("KHG-S019", path, "an unbound variable is used twice")]
    return []


def _validity_findings(record: Mapping[str, Any], schema: Schema, path: str) -> list[Finding]:
    try:
        b = bounds(record, schema)
    except (KHGError, ValueError, TypeError, KeyError):
        return []  # a malformed bound is S006 or a C code, reported with its value
    if b.s_lo >= b.e_hi:
        return [_f("KHG-S009", path, "the possible validity is empty: the start is not before the end")]
    return []


def _negated(e: Mapping[str, Any]) -> bool:
    epistemics = e.get("epistemics")
    return isinstance(epistemics, Mapping) and bool(epistemics.get("negated"))


def _confidence_findings(schema: Schema, c: Any, p: str) -> list[Finding]:
    if not isinstance(c, Mapping) or not isinstance(c.get("scale"), str):
        return []  # absent, or layer C's C003
    scale = schema.confidence_scale(c["scale"])
    if scale is None:
        return [_f("KHG-S010", p, f"confidence scale {c['scale']!r} is not declared")]
    lo, hi, value = scale.get("min"), scale.get("max"), c.get("value")
    if _number(lo) and _number(hi) and _number(value) and not lo <= value <= hi:
        return [_f("KHG-S010", p, f"confidence {value} is outside [{lo}, {hi}]")]
    return []


@functools.lru_cache(maxsize=64)
def _text_digest(text: str) -> str:
    return text_sha256(text)


def _source_text(source: Any, texts: Mapping[str, str]) -> str | None:
    """The text an evidence's selectors are read against (see the module docstring), or None."""
    if not isinstance(source, Mapping):
        return None
    doc_id, want = source.get("doc_id"), source.get("doc_sha256")
    if not isinstance(want, str):
        text = texts.get(doc_id) if isinstance(doc_id, str) else None
        return text if isinstance(text, str) else None
    for key in (want, doc_id):
        text = texts.get(key) if isinstance(key, str) else None
        if isinstance(text, str) and _text_digest(text) == want:
            return text
    return None


def _span_findings(e: Mapping[str, Any], texts: Mapping[str, str], p: str) -> list[Finding]:
    listed = e.get("selectors")
    selectors = [s for s in listed if isinstance(s, Mapping)] if isinstance(listed, list) else []
    text = _source_text(e.get("source"), texts) if selectors and texts else None
    if text is None:
        return []
    t = jsonio.nfc(text)
    quote = next((s for s in selectors if s.get("type") == "quote"), None)
    position = next((s for s in selectors if s.get("type") == "position"), None)
    if position is None:
        return []
    start, end = _integral(position.get("start")), _integral(position.get("end"))
    if start is None or end is None or not 0 <= start < end <= len(t):
        return [_f("KHG-S021", p, f"span [{position.get('start')}, {position.get('end')}) is empty, reversed or "
                                  f"outside a text of {len(t)} code points")]
    if quote is not None and t[start:end] != quote.get("exact"):
        return [_f("KHG-S021", p, "the quote differs from text[start:end] (code points, NFC)")]
    return []


def _constraint_findings(con: Mapping[str, Any], by_role: Mapping[str, list[Mapping[str, Any]]],
                         path: str) -> list[Finding]:
    roles = _strings(con.get("roles"))
    vals = {r: [x for x in (_identity(b.get("value")) for b in by_role.get(r, [])) if x] for r in roles}
    kind = con.get("type")
    if kind == "must_differ":
        bad = len({x for r in roles for x in vals[r]}) < sum(len(vals[r]) for r in roles)
    elif kind == "must_agree":
        bad = len({x for r in roles for x in vals[r]}) > 1
    elif kind == "requires":
        bad = bool(roles) and bool(vals[roles[0]]) and not all(vals[r] for r in roles[1:])
    elif kind == "excludes":
        bad = sum(1 for r in roles if vals[r]) > 1
    elif kind == "at_least_one_of":
        bad = not any(vals[r] for r in roles)
    else:
        return []
    if not bad:
        return []
    severity = "warning" if con.get("severity") == "warning" else "error"
    return [_f("KHG-S024", path, f"constraint {kind} {roles} is violated", severity)]


# ------------------------------------------------------------------------------------------------ containers


def latest_records(records: Iterable[Any]) -> dict[str, Mapping[str, Any]]:
    """The latest version of each entity and hyperedge by id (the highest ``version``; without one, the last)."""
    latest: dict[str, Mapping[str, Any]] = {}
    for r in records:
        if not isinstance(r, Mapping) or r.get("kind") not in ("entity", "hyperedge") or not isinstance(
                r.get("id"), str):
            continue
        version = _integral(r.get("version")) or 0
        held = latest.get(r["id"])
        if held is None or version >= (_integral(held.get("version")) or 0):
            latest[r["id"]] = r
    return latest


def container_findings(container: Any, schema: Schema | None, *, doc_texts: Mapping[str, str] | None = None,
                       state: dict[str, Any] | None = None) -> list[Finding]:
    """Layer S on a C1 container: S020 on the header and on every record, and ``record_findings`` on every
    hyperedge (with a schema). Entity and fact values resolve against the latest versions in the container, which
    are left in ``state`` (``"entities"``, ``"facts"``) for layer D."""
    if not isinstance(container, Mapping):
        return []
    out = nfc_findings(container.get("header"), "/header") if "header" in container else []
    records = container.get("records")
    records = records if isinstance(records, list) else []
    latest = latest_records(records)
    entities = {i: r for i, r in latest.items() if r.get("kind") == "entity"}
    facts = {i: r for i, r in latest.items() if r.get("kind") == "hyperedge"}
    if state is not None:
        state["entities"], state["facts"] = entities, facts
    for i, r in enumerate(records):
        base = f"/records/{i}"
        out += nfc_findings(r, base)
        if schema is not None:
            out += record_findings(r, schema, entities=entities, facts=facts, doc_texts=doc_texts, path=base)
    return out


def _queue_findings(ctx: Context, schema: Schema | None) -> list[Finding]:
    lines = ctx.doc if isinstance(ctx.doc, list) else []
    base = ctx.queue_base()
    base_entities = {i: r for i, r in latest_records((base or {}).get("records") or []).items()
                     if r.get("kind") == "entity"}
    out: list[Finding] = []
    for n, line in enumerate(lines):
        if not isinstance(line, Mapping) or line.get("kind") != "queue-item":
            continue
        p = f"/lines/{n}"
        own = line.get("entities") if isinstance(line.get("entities"), list) else []
        out += nfc_findings(own, f"{p}/entities") + nfc_findings(line.get("payload"), f"{p}/payload")
        if schema is None:
            continue
        entities = dict(base_entities)
        entities.update({e["id"]: e for e in own if isinstance(e, Mapping) and isinstance(e.get("id"), str)})
        out += record_findings(line.get("payload"), schema, entities=entities, facts={}, doc_texts=ctx.doc_texts,
                               path=f"{p}/payload", candidate=True)
    return out


def run(ctx: Context) -> list[Finding]:
    if ctx.kind not in ("container", "hif", "record", "queue"):
        return []
    if ctx.kind == "hif" and ctx.container is None:
        return []  # nothing decoded
    schema, out = ctx.relation_schema()
    if ctx.kind in ("container", "hif"):
        return out + container_findings(ctx.container, schema, doc_texts=ctx.doc_texts, state=ctx.state)
    if ctx.kind == "record":
        out += nfc_findings(ctx.doc)
        if schema is not None:
            out += record_findings(ctx.doc, schema, doc_texts=ctx.doc_texts)
        return out
    return out + _queue_findings(ctx, schema)
