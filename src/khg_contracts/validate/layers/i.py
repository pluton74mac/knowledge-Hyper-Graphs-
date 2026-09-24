"""Layer I: C4 items ``khg-c4-items/0.1.0`` (DESIGN §9.5, §9.6, §8.1).

On the lines of a C4 file, in order:

- each line against the draft schema, through the run's engine (``item_findings``): I001 an unknown kind, I002 the
  item structure, I004 a memory question without ``stale_values`` or ``future_values``. A finding of a C1 value,
  record or lexical form that the draft takes from ``khg-record`` (a C code) becomes I003, with the C finding under
  ``nested``;
- I002 when line 1 is not the ``c4-header``, for a second header, and for an ``id``, ``qid``, trace ``trace_id`` or
  ``doc_id`` used twice;
- the relation-type schema: the caller's (D009 at ``/lines/0/schema`` without one), which must be the schema the
  header pins (D009 otherwise; the checks below then do not run);
- the embedded C1 records (an extraction document's gold and entities, a trace's entities and ``put`` records):
  layer S with S020, each error nested under I003. The gold's spans are read against the item's own text;
- every trace without an error is replayed into a fresh ``MemoryStore`` (``scorers.memory.Replay``). A write the
  store refuses is I003 at the entities or at the event, with the store's C, S or D findings nested;
- every memory question without an error: its stored gold against ``derive_memory_gold`` from its replayed trace,
  with the default deprecation reasons (I005; ``scorers.memory.check_question``). A question whose trace is not in
  the file is I003.

Warnings of the embedded records (a warning constraint, S024) are not reported: they do not make the item invalid.
"""
from __future__ import annotations

from typing import Any, Mapping

from ...errors import KHGError, make_finding
from ...schema import Schema
from ...scorers import memory
from .. import engines
from ..context import Context
from . import s as layer_s

__all__ = ["HEADER", "IMPLEMENTED", "LETTER", "OWNER", "embedded_findings", "item_findings", "run"]

LETTER = "I"
OWNER = "W11a"
IMPLEMENTED = True

HEADER = "c4-header"
TRACE = "c4-memory-trace"
QUESTION = "c4-memory-question"
EXTRACTION = "c4-extraction-doc"
#: The fields no two items may share, and the kind of item that holds each (None: any).
UNIQUE = (("id", None), ("qid", None), ("trace_id", TRACE), ("doc_id", EXTRACTION))

Finding = dict[str, Any]


def _nest(f: Finding, what: str) -> Finding:
    out: Finding = {**make_finding("KHG-I003", f["path"], f"{what}: {f['code']}: {f['message']}")}
    out["nested"] = dict(f)
    return out


def item_findings(line: Any, *, engine: str = "jsonschema", path: str = "") -> list[Finding]:
    """The draft schema on one C4 line: its I codes as they are, and each C code (an embedded C1 value, record or
    lexical form) as I003 with the C finding under ``nested``."""
    out = []
    for f in engines.findings(engines.C4_SCHEMA_ID, line, engine=engine, path=path):
        out.append(f if f["layer"] == LETTER else _nest(f, "embedded C1 content"))
    return out


def _by_id(records: Any) -> dict[str, Mapping[str, Any]]:
    return {r["id"]: r for r in records if isinstance(r, Mapping) and isinstance(r.get("id"), str)} \
        if isinstance(records, list) else {}


def embedded_findings(line: Mapping[str, Any], schema: Schema, *, doc_texts: Mapping[str, str] | None = None,
                      path: str = "") -> list[Finding]:
    """Layer S (and S020) on the C1 records a schema-valid line embeds, each error as I003 with the S finding under
    ``nested``: an extraction document's gold (spans against its own text) and entities; a trace's entities and
    ``put`` records (the store checks the records of ``apply`` events when the trace is replayed)."""
    kind = line.get("kind")
    texts = dict(doc_texts or {})
    found: list[Finding] = []
    records: list[tuple[str, Mapping[str, Any]]] = []
    facts: dict[str, Mapping[str, Any]] = {}
    if kind == EXTRACTION:
        texts[line["doc_id"]] = line["text"]
        records = [(f"{path}/gold/{i}", r) for i, r in enumerate(line["gold"])]
        facts = _by_id(line["gold"])
    elif kind == TRACE:
        for k, ev in enumerate(line["events"]):
            records += [(f"{path}/events/{k}/put/{j}", r) for j, r in enumerate(ev.get("put") or [])]
            facts.update(_by_id(ev.get("put")))
            carried = ev.get("apply").get("records") if isinstance(ev.get("apply"), Mapping) else None
            facts.update({i: r for i, r in _by_id(carried).items() if r.get("kind") == "hyperedge"})
    else:
        return []
    entities = line.get("entities") or []
    for j, e in enumerate(entities):
        found += layer_s.nfc_findings(e, f"{path}/entities/{j}")
    for p, r in records:
        found += layer_s.nfc_findings(r, p)
        found += layer_s.record_findings(r, schema, entities=_by_id(entities), facts=facts, doc_texts=texts, path=p)
    return [_nest(f, "embedded C1 record") for f in found if f["severity"] == "error"]


# ------------------------------------------------------------------------------------------------ the file


def _file_findings(lines: list[Any], bad: set[int]) -> tuple[list[Finding], set[str]]:
    """I002 for a missing or second header and for repeated ids; the repeated trace ids (ambiguous traces)."""
    out = []
    if not (isinstance(lines[0], Mapping) and lines[0].get("kind") == HEADER):
        out.append(make_finding("KHG-I002", "/lines/0", "line 1 of a C4 file is its c4-header"))
    for n, line in enumerate(lines[1:], start=1):
        if isinstance(line, Mapping) and line.get("kind") == HEADER:
            out.append(make_finding("KHG-I002", f"/lines/{n}/kind", "a C4 file has one c4-header, on line 1"))
    ambiguous: set[str] = set()
    for name, kind in UNIQUE:
        first: dict[str, int] = {}
        for n, line in enumerate(lines):
            if n in bad or not isinstance(line, Mapping) or (kind is not None and line.get("kind") != kind):
                continue
            value = line.get(name)
            if not isinstance(value, str):
                continue
            if value in first:
                out.append(make_finding("KHG-I002", f"/lines/{n}/{name}",
                                        f"{name} {value!r} is also used at /lines/{first[value]}"))
                if name == "trace_id":
                    ambiguous.add(value)
            else:
                first[value] = n
    return out, ambiguous


def _pin_findings(lines: list[Any], bad: set[int], schema: Schema) -> list[Finding]:
    """D009 when the header pins another relation-type schema than the run's."""
    header = lines[0] if isinstance(lines[0], Mapping) and lines[0].get("kind") == HEADER and 0 not in bad else None
    pin = header.get("schema") if header is not None else None
    if not isinstance(pin, Mapping) or all(pin.get(k) == v for k, v in schema.header.items()):
        return []
    return [make_finding("KHG-D009", "/lines/0/schema", f"the header pins {pin.get('id')}/{pin.get('version')} "
                                                        f"({pin.get('sha256')}), not {schema.ref} ({schema.sha256})")]


def _replay(n: int, line: Mapping[str, Any], schema: Schema) -> tuple[memory.Replay | None, list[Finding]]:
    """Replay one trace; I003 at the write the store refuses."""
    rp: memory.Replay | None = None
    try:
        rp = memory.Replay(line, schema)
        return rp.run(), []
    except (KHGError, ValueError, TypeError, KeyError) as e:
        at = rp.position if rp is not None else None
        where = "" if at is None else "/entities" if at == "entities" else f"/events/{at}"
        return None, memory.replay_findings(e, path=f"/lines/{n}{where}")


def run(ctx: Context) -> list[Finding]:
    if ctx.kind != "item":
        return []
    lines = ctx.doc if isinstance(ctx.doc, list) else []
    if not lines:
        return []
    out: list[Finding] = []
    bad: set[int] = set()
    for n, line in enumerate(lines):
        found = item_findings(line, engine=ctx.engine, path=f"/lines/{n}")
        if any(f["severity"] == "error" for f in found):
            bad.add(n)
        out += found
    found, ambiguous = _file_findings(lines, bad)
    out += found
    schema, found = ctx.relation_schema()
    out += found
    if schema is None:
        return out
    pinned = _pin_findings(lines, bad, schema)
    if pinned:
        return out + pinned
    for n, line in enumerate(lines):
        if n not in bad:
            found = embedded_findings(line, schema, doc_texts=ctx.doc_texts, path=f"/lines/{n}")
            if found:
                bad.add(n)
                out += found
    traces: dict[str, int] = {}
    replays: dict[str, memory.Replay | None] = {}
    for n, line in enumerate(lines):
        if isinstance(line, Mapping) and line.get("kind") == TRACE and isinstance(line.get("trace_id"), str):
            tid = line["trace_id"]
            traces.setdefault(tid, n)
            if n in bad or tid in ambiguous:
                replays[tid] = None
            elif tid not in replays:
                replays[tid], found = _replay(n, line, schema)
                out += found
    for n, line in enumerate(lines):
        if n in bad or line.get("kind") != QUESTION:
            continue
        if line["trace_id"] not in traces:
            out.append(make_finding("KHG-I003", f"/lines/{n}/trace_id",
                                    f"no c4-memory-trace in the file has trace_id {line['trace_id']!r}"))
            continue
        replayed = replays.get(line["trace_id"])
        if replayed is not None:
            out += memory.check_question(replayed, line, path=f"/lines/{n}")[1]
    return out
