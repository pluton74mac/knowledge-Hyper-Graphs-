"""Lifecycle: the four axes, the transition table, the version rule and the rules on lifecycle records (DESIGN §2.6,
§2.7, §2.9, §6.2).

- **Four axes.** Belief (``status``), world (valid time), editorial (``rank``) and display (``visibility``) are
  independent: a fact that ended in the world keeps its status and gains an end binding (F7).
- **Transitions (D014).** A status changes only through the events of the §2.7 table (``TABLE``, ``TRANSITIONS``).
  ``put`` creates ``asserted``, ``quoted`` or ``goal`` records, never a lifecycle record (``candidate`` is D017).
  ``retracted`` is terminal; a lifecycle record may only be retracted (undo), and a ``khg:retracts`` record not even
  that.
- **The version rule (D013).** A new version keeps the relation; keeps every binding by bid, with its role and
  position and a refining value (``end_validity`` may replace a ``novalue`` end); adds bindings only where the role
  is not ``complete``; keeps every earlier evidence record unchanged; and changes no other field but ``rank``,
  ``rank_reason``, ``visibility``, ``confidence``, ``source_text`` and ``extensions`` (and ``goal`` while the status
  is ``goal``). Superseded and retracted facts are frozen. Entities: ``types`` only grow, ``redirect_to`` is set once.
- **Lifecycle records.** The pointer rule (D010), the supersession constraints (D011), supersession cycles (D012);
  and nesting cycles among fact references (D008). History containers: versions 1..n (D001), the version rule, the
  transitions and transaction times (D018).

Every rule returns ``Problem`` tuples (code, record id, JSON pointer inside that record, message, version), so the
validator reports findings and the store raises ``error_for(problems)``: ``VersionError`` for D011-D014 and D018,
``ValidationError`` otherwise. These are pure functions over records; the store applies events (W8).
"""
from __future__ import annotations

import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, NamedTuple, Sequence, Union

from .. import jsonio
from ..errors import KHGError, ValidationError, VersionError, make_finding
from ..schema.builtins import LIFECYCLE_RELATIONS
from ._common import SchemaLike, as_schema, fail, hyperedge, is_special, nfc_deep
from .canonical import STORE_FIELDS, carried_supports
from .derive import content_key, key_digest
from .refine import fact_refines, value_refines
from .validity import valid_time
from .windows import parse_instant

__all__ = [
    "AXES",
    "COMPOSITE_STEPS",
    "EDITABLE",
    "FROZEN",
    "LIFECYCLE_ROLE",
    "PUT_STATUSES",
    "RANKS",
    "STATUSES",
    "TABLE",
    "TERMINAL",
    "TRANSITIONS",
    "VISIBILITIES",
    "Problem",
    "Transition",
    "axes",
    "error_for",
    "history_problems",
    "nesting_cycle",
    "parse_timestamp",
    "pointer_problems",
    "put_problem",
    "supersede_problems",
    "supersession_constraint",
    "supersession_cycle",
    "supersession_problems",
    "transition_problem",
    "version_problems",
    "with_status",
]

Record = Mapping[str, Any]
Records = Union[Mapping[str, Record], Iterable[Record]]

STATUSES = ("candidate", "asserted", "disputed", "superseded", "retracted", "quoted", "goal")
RANKS = ("preferred", "normal", "deprecated")
VISIBILITIES = ("visible", "suppressed")
#: The four independent axes of a hyperedge (§2.7) and the field or view that carries each.
AXES: Mapping[str, str] = MappingProxyType(
    {"belief": "status", "world": "valid_time", "editorial": "rank", "display": "visibility"})
#: The statuses ``put`` may create a new id in.
PUT_STATUSES = ("asserted", "quoted", "goal")
#: A status that needs a ``status_ref`` (C006) -> (the lifecycle relation, the role that binds the fact).
LIFECYCLE_ROLE: Mapping[str, tuple[str, str]] = MappingProxyType({
    "disputed": ("khg:disputes", "khg:disputed"),
    "superseded": ("khg:supersedes", "khg:superseded"),
    "retracted": ("khg:retracts", "khg:retracted"),
})
FROZEN = ("superseded", "retracted")
TERMINAL = ("retracted",)
#: The fields other than bindings and evidence that a new version may change (§2.9).
EDITABLE = ("rank", "rank_reason", "visibility", "confidence", "source_text", "extensions")
_ENTITY_FREE = ("kind", "id", "label", "aliases", "extensions")
_EDGE_SKIP = ("kind", "id", "relation", "status", "status_ref", "bindings", "evidence", "derived")
_VERSION_CODES = ("KHG-D011", "KHG-D012", "KHG-D013", "KHG-D014", "KHG-D018")


class Transition(NamedTuple):
    """One row of the §2.7 transition table: the statuses a record leaves (``"new"`` for a new id), the statuses it
    may enter, the operation (``put``, ``supersede`` or ``transition``), the lifecycle record written or retracted
    (None when there is none) and a note."""

    sources: tuple[str, ...]
    targets: tuple[str, ...]
    how: str
    record: str | None
    note: str = ""


TABLE: tuple[Transition, ...] = (
    Transition(("new",), PUT_STATUSES, "put", None),
    Transition(("new",), ("asserted",), "supersede", "khg:supersedes", "a record of the event, bound as superseding"),
    Transition(("new",), ("disputed",), "transition", "khg:disputes", "a record of the dispute, bound as disputed"),
    Transition(("asserted", "disputed"), ("superseded",), "supersede", "khg:supersedes"),
    Transition(("asserted", "disputed"), ("disputed",), "transition", "khg:disputes",
               "over at least two facts, new or existing"),
    Transition(("asserted", "disputed", "goal", "quoted"), ("retracted",), "transition", "khg:retracts"),
    Transition(("disputed", "quoted"), ("asserted",), "transition", None, "re-checks the key"),
    Transition(("goal",), ("asserted",), "transition", None, "once every slot is bound (C005); drops goal"),
    Transition(("superseded", "disputed"), ("asserted",), "transition", "khg:retracts",
               "undo: retracts the lifecycle record, re-checks the key"),
)

#: The (from, to) status pairs the table allows for an existing fact.
TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    (s, t) for row in TABLE for s in row.sources if s != "new" for t in row.targets)


class Problem(NamedTuple):
    """One broken rule: its code, the id of the record at fault, a JSON pointer inside that record (``""`` for the
    record itself), a message, and the record's version when the rule concerns one version of a history."""

    code: str
    id: Any
    pointer: str
    message: str
    version: Any = None


# ------------------------------------------------------------------------------------------------ helpers


def _values(records: Records) -> list[Record]:
    items = records.values() if isinstance(records, Mapping) else records
    return [r for r in items if isinstance(r, Mapping)]


def _by_id(records: Records) -> dict[str, Record]:
    if isinstance(records, Mapping):
        return {k: v for k, v in records.items() if isinstance(v, Mapping)}
    return {r["id"]: r for r in _values(records) if isinstance(r.get("id"), str)}


def _bindings(record: Record) -> list[tuple[int, Mapping[str, Any]]]:
    bs = record.get("bindings")
    return [(j, b) for j, b in enumerate(bs) if isinstance(b, Mapping)] if isinstance(bs, list) else []


def _fact_ref(value: Any) -> str | None:
    if isinstance(value, Mapping) and len(value) == 1 and isinstance(value.get("fact"), str):
        return value["fact"]
    return None


def _refs(record: Record, role: str) -> list[tuple[int, str]]:
    """(binding index, fact id) of the fact values bound in ``role``."""
    return [(j, f) for j, b in _bindings(record) if b.get("role") == role
            for f in [_fact_ref(b.get("value"))] if f is not None]


def _hyperedges(records: Records) -> dict[str, Record]:
    return {i: r for i, r in _by_id(records).items() if r.get("kind") == "hyperedge"}


def _is_lifecycle(record: Record) -> bool:
    return record.get("relation") in LIFECYCLE_RELATIONS


def _same(a: Any, b: Any) -> bool:
    """Equal as canonical JSON (NFC strings, sorted keys); plain equality for what is not JSON."""
    try:
        return jsonio.canonical(a) == jsonio.canonical(b)
    except (TypeError, ValueError):
        return a == b


def _evidence_form(e: Any, bids: Sequence[Any]) -> str:
    """An evidence record for comparison across versions: NFC, ``supports`` defaulting to the bids of the version
    that carries it (§2.8.1), sorted."""
    if not isinstance(e, Mapping):
        return repr(e)
    form = nfc_deep(e)
    supports = form.get("supports", [b for b in bids if isinstance(b, str)])
    if isinstance(supports, list) and all(isinstance(x, str) for x in supports):
        form["supports"] = sorted(supports)
    try:
        return jsonio.canonical(form)
    except (TypeError, ValueError):
        return repr(form)


def _cycle(graph: Mapping[str, Sequence[tuple[str, Any]]]) -> list[tuple[str, Any]] | None:
    """A cycle of ``graph`` ({node: [(target, edge label), ...]}) as [(node, label of the edge leaving it), ...], or
    None. Iterative depth-first search from the nodes in sorted order, edges in their order: deterministic."""
    state: dict[str, int] = {}
    for start in sorted(graph):
        if start in state:
            continue
        state[start] = 1
        path, via = [start], []
        stack = [iter(graph.get(start, ()))]
        while stack:
            step = next(stack[-1], None)
            if step is None:
                state[path.pop()] = 2
                stack.pop()
                if via:
                    via.pop()
                continue
            target, label = step
            seen = state.get(target)
            if seen == 1:
                k = path.index(target)
                return list(zip(path[k:], via[k:] + [label], strict=True))
            if seen is None:
                state[target] = 1
                path.append(target)
                via.append(label)
                stack.append(iter(graph.get(target, ())))
    return None


# ------------------------------------------------------------------------------------------------ axes and errors


def axes(record: Record, schema: SchemaLike) -> dict[str, Any]:
    """A hyperedge's position on the four axes: ``belief`` (status), ``world`` (the §2.6 ``valid_time`` view),
    ``editorial`` (rank, default ``normal``) and ``display`` (visibility, default ``visible``)."""
    hyperedge(record)
    return {"belief": record.get("status"), "world": valid_time(record, schema),
            "editorial": record.get("rank", "normal"), "display": record.get("visibility", "visible")}


def error_for(problems: Iterable[Problem]) -> KHGError:
    """The exception a store raises for ``problems`` (the first one decides the class): ``VersionError`` for D011-D014
    and D018, else ``ValidationError``. ``codes`` lists the codes in order; ``info["problems"]`` holds the problems
    as dicts (a ``ValidationError`` also has ``info["findings"]``)."""
    ps = list(problems)
    if not ps:
        raise ValueError("error_for needs at least one problem")
    listed = [dict(p._asdict()) for p in ps]
    if ps[0].code in _VERSION_CODES:
        codes: list[str] = []
        for p in ps:
            if p.code not in codes:
                codes.append(p.code)
        more = f" (and {len(ps) - 1} more)" if len(ps) > 1 else ""
        return VersionError(f"{ps[0].code}: {ps[0].id}: {ps[0].message}{more}", codes=codes,
                            info={"problems": listed})
    findings = [make_finding(p.code, p.pointer, f"{p.id}: {p.message}") for p in ps]
    return ValidationError.from_findings(findings, problems=listed)


# ------------------------------------------------------------------------------------------------ transitions


def transition_problem(old: Any, new: Any, *, relation: Any = None, id: Any = None,
                       version: Any = None) -> Problem | None:
    """D014 when a record goes from status ``old`` to ``new`` outside the §2.7 table; None when the move is allowed
    or the status does not change. A lifecycle record (``relation`` khg:*) may only go from asserted to retracted
    (undo), and a ``khg:retracts`` record cannot be retracted."""
    if old == new:
        return None

    def problem(message: str) -> Problem:
        return Problem("KHG-D014", id, "/status", message, version)

    if relation in LIFECYCLE_RELATIONS:
        if (old, new) != ("asserted", "retracted"):
            return problem(f"a lifecycle record only goes from asserted to retracted, not {old} -> {new}")
        if relation == "khg:retracts":
            return problem("a khg:retracts record cannot itself be retracted")
        return None
    if (old, new) in TRANSITIONS:
        return None
    terminal = " (retracted is terminal)" if old in TERMINAL else ""
    return problem(f"{old} -> {new} is not in the transition table{terminal}")


def put_problem(record: Record, current: Record | None = None) -> Problem | None:
    """What ``put`` refuses before checking content (§6.2): a candidate (D017); a lifecycle record, a new id in a
    status other than asserted, quoted or goal, or a change of the ``current`` version's status or ``status_ref``
    (D014: both are the belief axis, which only events move). Entities have no status."""
    if record.get("kind") != "hyperedge":
        return None
    rid, status = record.get("id"), record.get("status")
    if status == "candidate":
        return Problem("KHG-D017", rid, "/status", "a candidate never enters a store: it stays a queue payload")
    if _is_lifecycle(record):
        return Problem("KHG-D014", rid, "/relation", "lifecycle records are written by events, never by put")
    if current is None:
        if status not in PUT_STATUSES:
            return Problem("KHG-D014", rid, "/status",
                           f"put creates records in status asserted, quoted or goal, not {status}")
        return None
    if current.get("status") != status:
        return Problem("KHG-D014", rid, "/status",
                       f"a status changes only through events: put cannot move {current.get('status')} -> {status}")
    if current.get("status_ref") != record.get("status_ref"):
        return Problem("KHG-D014", rid, "/status_ref",
                       f"status_ref changes only through events: put cannot move {current.get('status_ref')!r} -> "
                       f"{record.get('status_ref')!r}")
    return None


def with_status(record: Record, status: str, status_ref: str | None = None) -> dict[str, Any]:
    """A copy of ``record`` in ``status``, as an event writes it (§2.7): ``status_ref`` is set for disputed,
    superseded and retracted and dropped otherwise; leaving ``goal`` drops the ``goal`` block; store fields and the
    ``derived`` cache are dropped (the store assigns them)."""
    hyperedge(record)
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, not {status!r}")
    if (status in LIFECYCLE_ROLE) != (status_ref is not None):
        raise ValueError(f"status {status!r} {'needs' if status in LIFECYCLE_ROLE else 'takes no'} status_ref")
    out = nfc_deep(record)
    for f in (*STORE_FIELDS, "derived"):
        out.pop(f, None)
    if record.get("status") == "goal" and status != "goal":
        out.pop("goal", None)
    out["status"] = status
    if status_ref is None:
        out.pop("status_ref", None)
    else:
        out["status_ref"] = status_ref
    return out


# ------------------------------------------------------------------------------------------------ the version rule


def version_problems(old: Record, new: Record, schema: SchemaLike, *,
                     allow_novalue_end: bool = False) -> list[Problem]:
    """D013: the ways ``new`` breaks the version rule as the next version of ``old`` ([] when it keeps it).

    ``allow_novalue_end`` admits ``end_validity`` replacing a ``novalue`` end, the one non-refining change. Status
    and ``status_ref`` are the transitions' (``transition_problem``). A value that cannot be read is left to layers
    C and S."""
    rid, version = new.get("id"), new.get("version")

    def problem(message: str, pointer: str = "") -> Problem:
        return Problem("KHG-D013", rid, pointer, message, version)

    if old.get("kind") != new.get("kind"):
        return [problem(f"a new version keeps the kind ({old.get('kind')}, not {new.get('kind')})", "/kind")]
    if old.get("kind") == "entity":
        return _entity_problems(old, new, problem)
    if old.get("status") in FROZEN:
        return [problem(f"a {old.get('status')} fact is frozen: it takes no new content")]
    if old.get("relation") != new.get("relation"):
        return [problem(f"a new version keeps the relation {old.get('relation')!r}", "/relation")]
    s = as_schema(schema)
    out = _binding_problems(old, new, s, allow_novalue_end, problem)
    out += _evidence_problems(old, new, problem)
    for f in sorted(set(old) | set(new)):
        if f in STORE_FIELDS or f in _EDGE_SKIP or f in EDITABLE or (f == "goal" and old.get("status") == "goal"):
            continue
        if not _same(old.get(f), new.get(f)):
            out.append(problem(f"field {f!r} may not change in a new version", f"/{f}"))
    return out


def _entity_problems(old: Record, new: Record, problem: Any) -> list[Problem]:
    out = []
    for f in sorted(set(old) | set(new)):
        if f in STORE_FIELDS or f in _ENTITY_FREE:
            continue
        if f == "types":
            before, after = old.get("types"), new.get("types")
            if not (isinstance(before, list) and isinstance(after, list) and set(map(str, before)) <= set(
                    map(str, after))):
                out.append(problem("entity types may only grow", "/types"))
        elif f == "redirect_to":
            if old.get("redirect_to") and old.get("redirect_to") != new.get("redirect_to"):
                out.append(problem("redirect_to is set once and never changed", "/redirect_to"))
        elif not _same(old.get(f), new.get(f)):
            out.append(problem(f"entity field {f!r} may not change", f"/{f}"))
    return out


def _binding_problems(old: Record, new: Record, s: Any, allow_novalue_end: bool, problem: Any) -> list[Problem]:
    rel = old.get("relation")
    out: list[Problem] = []
    ob = {b.get("bid"): b for _, b in _bindings(old)}
    nb = {b.get("bid"): (j, b) for j, b in _bindings(new)}
    end_role = None
    if allow_novalue_end:
        try:
            end_role = s.time_model(rel).get("end")
        except (KHGError, ValueError, TypeError, KeyError):
            end_role = None
    for bid, b in ob.items():
        if bid not in nb:
            out.append(problem(f"binding {bid} was removed", "/bindings"))
            continue
        j, n = nb[bid]
        if n.get("role") != b.get("role") or n.get("position") != b.get("position"):
            out.append(problem(f"binding {bid} changed its role or position", f"/bindings/{j}"))
            continue
        try:
            refines = value_refines(n.get("value"), b.get("value"))
        except (KHGError, ValueError, TypeError, KeyError):
            continue  # a malformed value is reported by layers C and S
        if not refines and not (allow_novalue_end and is_special(b.get("value"), "novalue")
                                and end_role is not None and b.get("role") == end_role):
            out.append(problem(f"binding {bid} ({b.get('role')}) is not a refinement of its earlier value",
                               f"/bindings/{j}/value"))
    for bid, (j, n) in nb.items():
        if bid in ob:
            continue
        try:
            complete = bool(s.usage(rel, n.get("role")).get("complete"))
        except (KHGError, ValueError, TypeError, KeyError):
            continue  # an undeclared role is S002
        if complete:
            out.append(problem(f"binding {bid} adds a filler to the complete role {n.get('role')!r}",
                               f"/bindings/{j}"))
    return out


def _evidence_key(eid: Any) -> Any:
    """A hashable key for an evidence id as written (an id that is not a string is layer C's C010)."""
    return eid if isinstance(eid, str) else ("not a string", repr(eid))


def _evidence_problems(old: Record, new: Record, problem: Any) -> list[Problem]:
    """Every earlier evidence record is kept unchanged (the n-th record of an id against the n-th of the new version),
    and no new version gives an evidence id more often than the old one did: a second record under a held id would
    rewrite what the id names."""
    bids = [b.get("bid") for _, b in _bindings(old)]
    listed_old, listed_new = old.get("evidence"), new.get("evidence")
    oe = [e for e in listed_old if isinstance(e, Mapping)] if isinstance(listed_old, list) else []
    ne: dict[Any, list[tuple[int, Mapping[str, Any]]]] = {}
    for k, e in enumerate(listed_new if isinstance(listed_new, list) else []):
        if isinstance(e, Mapping):
            ne.setdefault(_evidence_key(e.get("id")), []).append((k, e))
    out = []
    held: dict[Any, int] = {}
    for e in oe:
        eid = e.get("id")
        key = _evidence_key(eid)
        n = held[key] = held.get(key, 0) + 1
        found = ne.get(key, [])
        if len(found) < n:
            out.append(problem(f"evidence {eid} was removed: evidence is append-only", "/evidence"))
        elif _evidence_form(e, bids) != _evidence_form(found[n - 1][1], bids):
            out.append(problem(f"evidence {eid} was changed: earlier evidence stays as written (event_hash "
                               "included)", f"/evidence/{found[n - 1][0]}"))
    for key, found in ne.items():
        if isinstance(key, str) and len(found) > max(1, held.get(key, 0)):
            out.append(problem(f"evidence {key} is given {len(found)} times: an evidence id names one record",
                               f"/evidence/{found[-1][0]}"))
    return out


# ------------------------------------------------------------------------------------------------ histories


def parse_timestamp(text: Any) -> int:
    """An RFC 3339 UTC timestamp (``recorded_at``, ``as_at``; ``YYYY-MM-DDThh:mm:ss[.ffffff]Z``) as microseconds on
    one line, so transaction times compare as integers; C011 on anything else."""
    m = _TIMESTAMP.fullmatch(text) if isinstance(text, str) else None
    if not m:
        raise fail("KHG-C011", f"timestamp {text!r} is not YYYY-MM-DDThh:mm:ss[.ffffff]Z (RFC 3339, UTC)")
    try:
        seconds = parse_instant(f"+{m.group(1)}Z")
    except ValidationError:
        raise fail("KHG-C011", f"timestamp {text!r} is not a calendar date-time") from None
    return seconds * 1_000_000 + int((m.group(2) or "").ljust(6, "0"))


_TIMESTAMP = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]{1,6}))?Z")


def _time(text: Any) -> int | None:
    try:
        return parse_timestamp(text)
    except ValidationError:
        return None


def _as_asserted(record: Record, goal: bool) -> dict[str, Any]:
    out = dict(record)
    out["status"] = "asserted"
    out.pop("status_ref", None)
    if goal:
        out.pop("goal", None)
    return out


def _version_number(value: Any, other: Any = 0) -> Any:
    """A version number: an int, or an integral float read as its int (F10: canonical JSON writes ``2.0`` as ``2``);
    ``other`` for anything else."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value if isinstance(value, int) and not isinstance(value, bool) else other


def history_problems(versions: Iterable[Record], schema: SchemaLike, *, as_at: Any = None) -> list[Problem]:
    """The rules on the versions of one id in a history container: versions 1..n (D001); each version recorded
    after the previous one and not after the header's ``as_at`` (D018); consecutive statuses in the transition
    table, or the one composite step of an undo resolved by a dispute (``COMPOSITE_STEPS``) (D014); and the version
    rule between consecutive versions (D013; a ``novalue`` end may be replaced).
    Evidence carried without ``supports`` supports what it did in the first version that carries it (§2.8.1,
    ``carried_supports``), as the canonical form writes it."""
    vs = sorted(_values(versions), key=lambda r: _version_number(r.get("version")))
    if not vs:
        return []
    vs = carried_supports(vs)
    out: list[Problem] = []
    rid = vs[0].get("id")
    numbers = [_version_number(v.get("version"), v.get("version")) for v in vs]
    if numbers != list(range(1, len(vs) + 1)):
        out.append(Problem("KHG-D001", rid, "/version", f"the versions of {rid} are {numbers}, not 1..{len(vs)}",
                           vs[0].get("version")))
    limit = _time(as_at) if as_at is not None else None
    prev: Record | None = None
    for v in vs:
        t = _time(v.get("recorded_at"))
        if t is not None and prev is not None:
            t_prev = _time(prev.get("recorded_at"))
            if t_prev is not None and t <= t_prev:
                out.append(Problem("KHG-D018", rid, "/recorded_at", f"version {v.get('version')} is not recorded "
                                   f"after version {prev.get('version')}", v.get("version")))
        if t is not None and limit is not None and t > limit:
            out.append(Problem("KHG-D018", rid, "/recorded_at", f"version {v.get('version')} is recorded after the "
                               f"header's as_at {as_at}", v.get("version")))
        if prev is not None and prev.get("kind") == v.get("kind"):
            out += _step_problems(prev, v, schema)
        prev = v
    return out


#: Consecutive statuses that one event writes as one version although no single row of the table gives them: an
#: undo whose ``resolve_superseding`` is ``dispute`` restores a superseded fact and disputes it at once (§2.7,
#: S-LIFE-013). The event path keeps refusing a direct move (``transition_problem``).
COMPOSITE_STEPS = frozenset({("superseded", "disputed")})


def _step_problems(prev: Record, v: Record, schema: SchemaLike) -> list[Problem]:
    if v.get("kind") != "hyperedge" or prev.get("status") == v.get("status"):
        return version_problems(prev, v, schema, allow_novalue_end=True)
    out = []
    composite = (prev.get("status"), v.get("status")) in COMPOSITE_STEPS and not _is_lifecycle(prev)
    moved = None if composite else transition_problem(prev.get("status"), v.get("status"),
                                                      relation=prev.get("relation"), id=v.get("id"),
                                                      version=v.get("version"))
    if moved is not None:
        out.append(moved)
    goal = prev.get("status") == "goal"
    out += version_problems(_as_asserted(prev, goal), _as_asserted(v, goal), schema, allow_novalue_end=True)
    return out


# ------------------------------------------------------------------------------------------------ lifecycle records


def pointer_problems(records: Records) -> list[Problem]:
    """D010 over the current versions of a document or store (``{id: record}`` or records): a disputed, superseded
    or retracted fact names in ``status_ref`` an asserted lifecycle record of the matching relation that binds it
    in the matching role; every fact an asserted ``khg:supersedes`` record binds as superseded, or a ``khg:retracts``
    record binds, has that status. A ``khg:disputes`` record may outlive its dispute."""
    facts = _hyperedges(records)
    out: list[Problem] = []
    for fid, r in facts.items():
        status = r.get("status")
        if status not in LIFECYCLE_ROLE:
            continue
        rel, role = LIFECYCLE_ROLE[status]
        ref = r.get("status_ref")
        lc = facts.get(ref) if isinstance(ref, str) else None
        if lc is None:
            message = f"a {status} fact's status_ref {ref!r} names no record"
        elif lc.get("relation") != rel:
            message = f"status_ref {ref!r} is a {lc.get('relation')!r} record, not a {rel} record"
        elif lc.get("status") != "asserted":
            message = f"status_ref {ref!r} is {lc.get('status')}, not an asserted {rel} record"
        elif fid not in {f for _, f in _refs(lc, role)}:
            message = f"status_ref {ref!r} does not bind {fid} as {role}"
        else:
            continue
        out.append(Problem("KHG-D010", fid, "/status_ref", message))
    for lid, lc in facts.items():
        rel = lc.get("relation")
        if rel not in ("khg:supersedes", "khg:retracts") or lc.get("status") != "asserted":
            continue
        role, want = ("khg:superseded", "superseded") if rel == "khg:supersedes" else ("khg:retracted", "retracted")
        for j, target in _refs(lc, role):
            f = facts.get(target)
            if f is not None and f.get("status") != want:
                out.append(Problem("KHG-D010", lid, f"/bindings/{j}/value",
                                   f"{lid} binds {target} as {role}, but {target} is {f.get('status')}"))
    return out


def supersession_constraint(reason: Any, superseding: Record, superseded: Record,
                            schema: SchemaLike) -> str | None:
    """The reason's constraint between one superseding and one superseded fact (§2.7), as a message, or None when it
    holds: ``correction`` keeps the relation and the key digest; ``duplicate`` needs equal content keys;
    ``refinement`` needs the superseding fact to refine the superseded one. Other reasons constrain nothing."""
    a, b = superseding, superseded
    if reason == "correction":
        if a.get("relation") != b.get("relation"):
            return (f"a correction keeps the relation: {a.get('id')} is {a.get('relation')!r}, {b.get('id')} is "
                    f"{b.get('relation')!r}")
        if key_digest(a, schema) != key_digest(b, schema):
            return f"a correction keeps the key digest: {a.get('id')} and {b.get('id')} have different keys"
    elif reason == "duplicate":
        if content_key(a, schema) != content_key(b, schema):
            return f"a duplicate needs equal content keys: {a.get('id')} and {b.get('id')} differ"
    elif reason == "refinement":
        if not fact_refines(a, b, schema):
            return f"a refinement needs {a.get('id')} to refine {b.get('id')}"
    return None


def _supersedes(records: Mapping[str, Record]) -> list[tuple[str, Record]]:
    return [(i, r) for i, r in records.items()
            if r.get("relation") == "khg:supersedes" and r.get("status") == "asserted"]


def supersession_problems(records: Records, schema: SchemaLike, *, ids: Iterable[str] | None = None) -> list[Problem]:
    """D011 on the current versions: each asserted ``khg:supersedes`` record keeps its reason's constraint between
    every superseding and every superseded fact present. With ``ids``, only the records that bind one of them (the
    ``put`` check on new versions of bound facts, S-LIFE-014). A pair that cannot be read is left to C and S."""
    facts = _hyperedges(records)
    wanted = None if ids is None else set(ids)
    out: list[Problem] = []
    for lid, lc in _supersedes(facts):
        sing = [f for _, f in _refs(lc, "khg:superseding")]
        sed = [f for _, f in _refs(lc, "khg:superseded")]
        if wanted is not None and not (set(sing) | set(sed)) & wanted:
            continue
        for a in (facts[i] for i in sing if i in facts):
            for b in (facts[i] for i in sed if i in facts):
                try:
                    message = supersession_constraint(lc.get("reason"), a, b, schema)
                except (KHGError, ValueError, TypeError, KeyError):
                    continue
                if message:
                    out.append(Problem("KHG-D011", lid, "", f"{lid} ({lc.get('reason')}): {message}"))
    return out


def supersede_problems(superseding: Sequence[Record], superseded: Sequence[Record], reason: Any,
                       schema: SchemaLike, *, event_id: Any = None) -> list[Problem]:
    """The preconditions of a ``supersede`` event (§2.7, §6.2): the superseded facts are asserted or disputed
    (D014); the superseding facts are asserted when the event runs, so events cannot form a cycle (D011); and the
    reason's constraint holds for every pair (D011)."""
    out: list[Problem] = []
    for b in superseded:
        if b.get("status") not in ("asserted", "disputed"):
            out.append(Problem("KHG-D014", b.get("id"), "/status",
                               f"only asserted or disputed facts are superseded, not a {b.get('status')} fact"))
    for a in superseding:
        if a.get("status") != "asserted":
            out.append(Problem("KHG-D011", a.get("id"), "/status",
                               f"a superseding fact must be asserted when the event runs, not {a.get('status')}"))
    for a in superseding:
        for b in superseded:
            message = supersession_constraint(reason, a, b, schema)
            if message:
                out.append(Problem("KHG-D011", event_id, "", message))
    return out


def supersession_cycle(records: Records) -> Problem | None:
    """D012: a cycle among the asserted ``khg:supersedes`` records (superseding -> superseded), reported at the
    record whose edge closes it; None when the supersessions are acyclic."""
    facts = _hyperedges(records)
    graph: dict[str, list[tuple[str, str]]] = {}
    for lid, lc in _supersedes(facts):
        for _, a in _refs(lc, "khg:superseding"):
            for _, b in _refs(lc, "khg:superseded"):
                graph.setdefault(a, []).append((b, lid))
    cycle = _cycle(graph)
    if cycle is None:
        return None
    nodes = [n for n, _ in cycle] + [cycle[0][0]]
    via = sorted({lid for _, lid in cycle})
    return Problem("KHG-D012", cycle[-1][1], "", f"supersession cycle {' -> '.join(nodes)} (through "
                   f"{', '.join(via)})")


def nesting_cycle(records: Records, schema: SchemaLike | None = None) -> Problem | None:
    """D008: a cycle among the fact references of the hyperedges (lifecycle records excluded), reported at the
    binding that starts it; None when nesting is acyclic. ``schema`` is accepted for symmetry and not needed."""
    facts = _hyperedges(records)
    graph = {fid: [(target, j) for j, b in _bindings(r) for target in [_fact_ref(b.get("value"))]
                   if target is not None]
             for fid, r in facts.items() if not _is_lifecycle(r)}
    cycle = _cycle(graph)
    if cycle is None:
        return None
    nodes = [n for n, _ in cycle] + [cycle[0][0]]
    first, j = cycle[0]
    return Problem("KHG-D008", first, f"/bindings/{j}/value", f"nesting cycle {' -> '.join(nodes)}")
