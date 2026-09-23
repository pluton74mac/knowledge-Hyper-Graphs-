"""Layer D: cross-record, container, history and queue rules (DESIGN §2.5-§2.9, §6.2, §8.1).

Containers (``ctx.container``: the input of a container run, or the container that decoding left in a HIF run):

- D009 the header's schema pin (id, version and sha256) against the run's schema (container runs; in a HIF run
  decoding checks the metadata's pin);
- D001 an id declared twice (an (id, version) pair in a history container); D007 an id naming both an entity and a
  hyperedge; D017 a ``candidate``; D015 a stored ``derived`` block that disagrees with recomputation;
- history containers (``content: "history"``): versions 1..n (D001), transaction times (D018), transitions (D014)
  and the version rule (D013) between consecutive versions of each id (``record.lifecycle.history_problems``);
- on the current versions (the latest of each id): D002 an entity or fact value that a ``complete`` document does
  not declare (vocabulary ids are never references); D020 a value naming an entity with ``redirect_to``; D008
  nesting cycles; D010 the lifecycle pointers; D011 the supersession constraints; D012 supersession cycles; D016 the
  key invariant, judged per instant on definite windows; and the L008 warning (``record.keys``).

A single record: D017 and D015. A queue: D009, the header's schema pin. Without a schema (D009, reported once by the
first step that asks) the container rules are skipped, as in the prototype. The layer reads broken structure without
raising: what layers C and S reject is skipped here.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from ... import jsonio
from ...errors import KHGError, make_finding
from ...record import bounds, derive, key_digest, lifecycle, normalize
from ...record import keys as keyrules
from ...record.lifecycle import Problem
from ...schema import Schema
from ..context import Context
from .s import latest_records

__all__ = ["IMPLEMENTED", "LETTER", "OWNER", "container_findings", "record_findings", "run"]

LETTER = "D"
OWNER = "W5"
IMPLEMENTED = True

Finding = dict[str, str]
_UNREADABLE = (KHGError, ValueError, TypeError, KeyError, AttributeError)


def run(ctx: Context) -> list[Finding]:
    if ctx.kind in ("container", "hif"):
        container = ctx.container
        if not isinstance(container, Mapping):
            return []
        schema, out = ctx.relation_schema()
        if schema is None:
            return out
        return out + container_findings(container, schema, pin=ctx.kind == "container", state=ctx.state)
    if ctx.kind == "record":
        schema, out = ctx.relation_schema()
        return out + record_findings(ctx.doc, schema)
    if ctx.kind == "queue":
        return _queue_findings(ctx)
    return []


# ------------------------------------------------------------------------------------------------ helpers


def _f(code: str, path: str, message: str, severity: str = "error") -> Finding:
    return make_finding(code, path, message, severity)


def _same(a: Any, b: Any) -> bool:
    try:
        return jsonio.canonical(a) == jsonio.canonical(b)
    except (TypeError, ValueError):
        return a == b


def _pin(declared: Any, schema: Schema, path: str) -> list[Finding]:
    """D009 when a declared ``{id, version, sha256}`` differs from the run's schema (C010 is layer C's)."""
    if not isinstance(declared, Mapping):
        return []
    differ = [k for k, want in (("id", schema.id), ("version", schema.version), ("sha256", schema.sha256))
              if declared.get(k) != want]
    if not differ:
        return []
    return [_f("KHG-D009", path, f"the declared schema differs from {schema.ref} ({schema.sha256}) in "
                                 f"{', '.join(differ)}")]


def _derived_findings(record: Mapping[str, Any], schema: Schema, path: str) -> list[Finding]:
    """D015: a stored ``derived`` block must equal ``derive`` on the canonical record."""
    if record.get("kind") != "hyperedge" or "derived" not in record:
        return []
    try:
        want = derive(normalize(record), schema)
    except _UNREADABLE:
        return []  # C and S report what makes the record unreadable
    if _same(record["derived"], want):
        return []
    return [_f("KHG-D015", f"{path}/derived", "the stored derived block disagrees with recomputation")]


def _problem_findings(problems: Iterable[Problem | None], paths: Mapping[Any, str]) -> list[Finding]:
    return [_f(p.code, paths.get(p.id, "") + p.pointer, p.message) for p in problems if p is not None]


def _usable(record: Mapping[str, Any], schema: Schema) -> bool:
    """A fact whose key digest and bounds can be computed (what cannot is C's or S's to report)."""
    try:
        key_digest(record, schema)
        bounds(record, schema)
    except _UNREADABLE:
        return False
    return True


# ------------------------------------------------------------------------------------------------ containers


def container_findings(container: Mapping[str, Any], schema: Schema, *, pin: bool = True,
                       state: dict[str, Any] | None = None) -> list[Finding]:
    """Layer D on a C1 container (see the module docstring). ``pin`` checks the header's schema pin; ``state`` may
    hold the latest ``entities`` and ``facts`` by id that layer S computed for the same container."""
    header = container.get("header") if isinstance(container.get("header"), Mapping) else {}
    listed = container.get("records")
    records = listed if isinstance(listed, list) else []
    history = header.get("content") == "history"
    out = _pin(header.get("schema"), schema, "/header/schema") if pin else []
    out += _declaration_findings(records, schema, history)
    if history:
        out += _history_findings(records, schema, header.get("as_at"))

    if state is not None and "entities" in state and "facts" in state:
        entities, facts = state["entities"], state["facts"]
    else:
        latest = latest_records(records)
        entities = {i: r for i, r in latest.items() if r.get("kind") == "entity"}
        facts = {i: r for i, r in latest.items() if r.get("kind") == "hyperedge"}
    index = {id(r): i for i, r in enumerate(records)}
    paths = {fid: f"/records/{index[id(r)]}" for fid, r in facts.items() if id(r) in index}

    out += _reference_findings(records, facts, entities, header.get("complete") is True)
    out += _problem_findings([lifecycle.nesting_cycle(facts)], paths)
    out += _problem_findings(lifecycle.pointer_problems(facts), paths)
    out += _problem_findings(lifecycle.supersession_problems(facts, schema), paths)
    out += _problem_findings([lifecycle.supersession_cycle(facts)], paths)
    out += _key_findings(facts, schema, paths)
    return out


def _declaration_findings(records: list[Any], schema: Schema, history: bool) -> list[Finding]:
    """D001 (an id, or an (id, version) pair in a history, declared twice), D007 (an id naming an entity and a
    hyperedge), D017 (a candidate) and D015 (a stored derived block), record by record."""
    out: list[Finding] = []
    seen: set[Any] = set()
    kinds: dict[str, str] = {}
    for i, r in enumerate(records):
        if not isinstance(r, Mapping) or r.get("kind") not in ("entity", "hyperedge") or not isinstance(
                r.get("id"), str):
            continue
        rid, path = r["id"], f"/records/{i}"
        version = r.get("version")
        key = (rid, version if isinstance(version, int) and not isinstance(version, bool) else repr(version)) \
            if history else rid
        if key in seen:
            what = f"{rid} version {version}" if history else rid
            out.append(_f("KHG-D001", path, f"{what} is declared twice"))
        seen.add(key)
        first = kinds.setdefault(rid, r["kind"])
        if first != r["kind"]:
            out.append(_f("KHG-D007", path, f"{rid} names both an entity and a hyperedge"))
        if r["kind"] == "hyperedge" and r.get("status") == "candidate":
            out.append(_f("KHG-D017", f"{path}/status", "status candidate outside a queue payload"))
        out += _derived_findings(r, schema, path)
    return out


def _history_findings(records: list[Any], schema: Schema, as_at: Any) -> list[Finding]:
    """D001, D013, D014 and D018 on the versions of each id of a history container."""
    by_id: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    for i, r in enumerate(records):
        if isinstance(r, Mapping) and r.get("kind") in ("entity", "hyperedge") and isinstance(r.get("id"), str):
            by_id.setdefault(r["id"], []).append((i, r))
    out: list[Finding] = []
    for rid in sorted(by_id):
        versions = by_id[rid]
        if len({r["kind"] for _, r in versions}) > 1:
            continue  # D007
        at = {}
        for i, r in versions:
            at.setdefault(repr(r.get("version")), f"/records/{i}")
        try:
            problems = lifecycle.history_problems([r for _, r in versions], schema, as_at=as_at)
        except _UNREADABLE:
            continue
        out += [_f(p.code, at.get(repr(p.version), f"/records/{versions[0][0]}") + p.pointer, f"{rid}: {p.message}")
                for p in problems]
    return out


def _reference_findings(records: list[Any], facts: Mapping[str, Any], entities: Mapping[str, Any],
                        complete: bool) -> list[Finding]:
    """D002 and D020 on the bindings of the current versions."""
    out: list[Finding] = []
    for i, r in enumerate(records):
        if not isinstance(r, Mapping) or r.get("kind") != "hyperedge" or not isinstance(r.get("id"), str) \
                or facts.get(r["id"]) is not r:
            continue
        bs = r.get("bindings")
        for j, b in enumerate(bs if isinstance(bs, list) else []):
            v = b.get("value") if isinstance(b, Mapping) else None
            if not isinstance(v, Mapping) or len(v) != 1:
                continue
            path = f"/records/{i}/bindings/{j}/value"
            eid, fid = v.get("entity"), v.get("fact")
            if isinstance(eid, str):
                e = entities.get(eid)
                if e is None:
                    if complete:
                        out.append(_f("KHG-D002", path, f"entity {eid} is absent from a complete document"))
                elif e.get("redirect_to"):
                    out.append(_f("KHG-D020", path, f"entity {eid} redirects to {e.get('redirect_to')}; values "
                                                    "may not name a redirected entity in 1.0"))
            elif isinstance(fid, str) and complete and fid not in facts:
                out.append(_f("KHG-D002", path, f"fact {fid} is absent from a complete document"))
    return out


def _key_findings(facts: Mapping[str, Mapping[str, Any]], schema: Schema, paths: Mapping[Any, str]) -> list[Finding]:
    """D016 for every set of facts that break the key invariant, and the L008 warning for every pair of facts of a
    temporal key that possibly but not definitely overlap."""
    usable = {fid: r for fid, r in facts.items() if _usable(r, schema)}
    out: list[Finding] = []
    for v in keyrules.key_invariant_violations(usable, schema):
        ids = " and ".join(v.ids)
        when = ("at every instant" if not v.temporal else f"at {v.at}" if v.at else "since forever")
        out.append(_f("KHG-D016", paths.get(v.ids[0], ""),
                      f"{ids} hold {when} on one key of {v.relation} ({v.key_digest}) without exactly one "
                      "preferred among them"))
    for a, b in keyrules.possible_only_overlaps(usable, schema):
        out.append(_f("KHG-L008", paths.get(a, ""),
                      f"{a} and {b} possibly, but not definitely, overlap on one temporal key of "
                      f"{usable[a].get('relation')}", "warning"))
    return out


# ------------------------------------------------------------------------------------------------ records, queues


def record_findings(record: Any, schema: Schema | None) -> list[Finding]:
    """Layer D on a single record: D017 (a candidate) and, with a schema, D015 (a stored derived block)."""
    if not isinstance(record, Mapping) or record.get("kind") != "hyperedge":
        return []
    out = []
    if record.get("status") == "candidate":
        out.append(_f("KHG-D017", "/status", "status candidate outside a queue payload"))
    if schema is not None:
        out += _derived_findings(record, schema, "")
    return out


def _queue_findings(ctx: Context) -> list[Finding]:
    """D009: the queue header's schema pin against the run's schema."""
    lines = ctx.doc if isinstance(ctx.doc, list) else []
    header = lines[0] if lines and isinstance(lines[0], Mapping) else None
    if header is None or header.get("kind") != "queue-header":
        return []  # Q008 is layer Q's
    schema, out = ctx.relation_schema()
    if schema is not None:
        out = out + _pin(header.get("schema"), schema, "/lines/0/schema")
    return out
