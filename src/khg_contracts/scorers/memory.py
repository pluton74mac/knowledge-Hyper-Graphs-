"""The memory gold (normative) and the memory scorer (DESIGN §9.2, §9.3, §9.5; R05 §5.2).

**Memory gold.** ``derive_memory_gold(trace, question, *, schema, incorrect_reasons)`` replays a
``c4-memory-trace`` into a fresh ``MemoryStore``: the trace's entities one second before its first step, then each
event at its ``tx_time`` with actor ``trace:<trace_id>`` (a ``put`` of C1 hyperedges, or an ``apply`` event), in
step order, up to the question's ``ask_after_step``. With τ that step's ``tx_time`` and t the question's
``where.as_of`` instant (or null), the sets hold the target-role values of the facts on the question's key:

- V_cur (``answer.values``): what ``find_by_key`` returns under the question's ``where`` at ``as_at`` τ; when one of
  those facts is preferred, only the preferred ones;
- ``expired``: asserted, not deprecated, and the possible validity ends at or before t (e_hi <= t);
- ``revised``: superseded or retracted at τ after being asserted at some τ′ < τ; and deprecated facts whose
  ``rank_reason`` names an incorrect reason (default ``wd:Q41755623``);
- V_fut (``future_values``): asserted, not deprecated, and the possible validity starts after t (s_lo > t);
- ``disputed_values``: disputed at τ.

V_cur is subtracted from the other sets; a value both expired and revised is ``expired``; ``answerable`` is false
when V_cur is empty and something is disputed. With ``as_of`` null there is no valid-time filter, so ``expired`` and
V_fut are empty. Values are written in canonical form and sorted by their identity (§2.3). ``check_question``
compares an item's stored gold with the replay, value sets by identity (I005); layer I and ``score`` use it.

**The scorer.** ``score(questions, responses, *, traces, schema, config)`` checks the ``c4-memory-question`` and
``c4-memory-trace`` items (the draft schema, the trace replays, the stored gold against the replay under
``config.incorrect_reasons``) and the ``memory-response`` records, then gives each question one outcome (R05 §5.2):

| Outcome | When (Â: the answered values, after redirects) | strict, lenient |
|---|---|---|
| ``current`` (O1) | Â meets V_cur and nothing stale or future; or V_cur is empty and Â is empty, not abstained | 1, 1 |
| ``hedged`` (O2) | Â meets V_cur and a stale or future value | 0, 1 |
| ``stale`` (O3) | Â misses V_cur and meets a stale value (``stale_kind`` expired before revised) | 0, 0 |
| ``anachronistic`` (O4) | Â misses V_cur and the stale values and meets V_fut | 0, 0 |
| ``wrong`` (O5) | anything else | 0, 0 |
| ``abstained`` (O6) | the abstain flag, or Â empty while V_cur is not | 0, 0 |
| ``correct_abstention`` (O7) | an unanswerable question, abstained (the flag, or Â empty) | 1, 1 |
| ``hallucinated`` (O7) | an unanswerable question, answered | 0, 0 |

A question without a response is ``missing`` (0, 0). Accuracy pools the correct abstentions (``acc_strict``, the
headline, and ``acc_lenient``, the ``lenient`` preset's headline); the rates of O2-O6 are over the answerable
questions, the stale rate split into ``expired`` and ``revised``; abstention precision and recall are over the
unanswerable ones. Also reported: set P/R/F1 against V_cur, ranked efficacy (CounterFact's ES on ``value_scores``)
and ``support_success@k`` against the current support. A question's ``tolerance {"amount": d}`` lets a quantity
answer within ``d`` of a gold quantity of the same unit match it (R05 M-M8), unless the answer equals a gold value of
V_cur, V_old or V_fut, which it then matches alone.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, Iterable, Literal, Mapping, Sequence

from ..errors import KHGError, ValidationError, make_finding
from ..record import bounds, canonical_value, decimal, identity_key, parse_instant, resolve_redirects, value_kind
from ..record.lifecycle import RANKS, STATUSES, VISIBILITIES
from ..schema import Schema
from ..store import MemoryStore, ScenarioClock, Where, format_timestamp, parse_timestamp
from . import _inputs
from ._common import as_schema, mean, prf_split, report
from .bootstrap import Bootstrap, mean_interval

__all__ = [
    "GOLD_FIELDS",
    "INCORRECT_REASONS",
    "KS",
    "MISSING",
    "MODES",
    "OUTCOMES",
    "MemoryConfig",
    "Replay",
    "check_question",
    "classify",
    "derive_memory_gold",
    "gold_findings",
    "read_gold",
    "replay_findings",
    "replay_trace",
    "score",
]

#: Wikidata's "incorrect value", the default deprecation reason that marks a revised value (§9.5; ruling 3)
INCORRECT_REASONS = frozenset({"wd:Q41755623"})
MODES = ("strict", "lenient")
#: The outcomes O1-O7 of R05 §5.2 (O7 is two outcomes); ``MISSING`` marks a question without a response.
OUTCOMES = ("current", "hedged", "stale", "anachronistic", "wrong", "abstained", "correct_abstention",
            "hallucinated")
MISSING = "missing"
#: The cut-offs of ``support_success@k`` (the retrieval scorer's defaults).
KS = (1, 3, 5, 10, 20)
#: The gold fields of a ``c4-memory-question`` that the replay derives.
GOLD_FIELDS = ("answer", "stale_values", "future_values", "disputed_values", "answerable")
_SECOND = 1_000_000  # microseconds
_ALL_STATUSES, _ALL_RANKS, _ALL_VISIBILITIES = frozenset(STATUSES), frozenset(RANKS), frozenset(VISIBILITIES)

Finding = dict[str, Any]


def _reasons(reasons: Any) -> frozenset[str]:
    if isinstance(reasons, (str, bytes)) or not isinstance(reasons, Iterable):
        raise TypeError("incorrect_reasons is a collection of rank reason ids, not a string")
    out = frozenset(reasons)
    if any(not isinstance(r, str) or not r for r in out):
        raise ValueError(f"incorrect_reasons are non-empty strings, not {sorted(map(repr, out))}")
    return out


@dataclass(frozen=True)
class MemoryConfig:
    """The memory scorer's settings (DESIGN §9.2): the headline (``strict``, or ``lenient`` for the preset), the
    deprecation reasons that make a value ``revised``, and the bootstrap."""

    mode: Literal["strict", "lenient"] = "strict"
    incorrect_reasons: frozenset[str] = INCORRECT_REASONS
    bootstrap: Bootstrap = Bootstrap()

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, not {self.mode!r}")
        object.__setattr__(self, "incorrect_reasons", _reasons(self.incorrect_reasons))
        if not isinstance(self.bootstrap, Bootstrap):
            raise ValueError("bootstrap must be a Bootstrap")


# ------------------------------------------------------------------------------------------------ the replay


def _field(item: Mapping[str, Any], name: str, kind: str) -> Any:
    if not isinstance(item, Mapping) or name not in item:
        raise ValueError(f"a {kind} needs {name!r}")
    return item[name]


class Replay:
    """A ``c4-memory-trace`` replayed into a fresh ``MemoryStore`` (DESIGN §9.5).

    ``run`` puts the trace's entities one second before its first step, then runs each event at its ``tx_time``
    with actor ``trace:<trace_id>``, in step order (events of one step in list order). ``times`` maps each step
    replayed to its ``tx_time`` (a step's last event). ``position`` names the write under way: ``"entities"``, or
    the index of the event in ``trace["events"]``; after a store error it names the write that failed, and it is
    None once the run is over. Store errors propagate unchanged.
    """

    def __init__(self, trace: Mapping[str, Any], schema: Any):
        self.schema: Schema = as_schema(schema)
        self.trace_id: str = _field(trace, "trace_id", "c4-memory-trace")
        events = _field(trace, "events", "c4-memory-trace")
        if not isinstance(events, list) or not events or not all(
                isinstance(e, Mapping) and type(e.get("step")) is int and isinstance(e.get("tx_time"), str)
                for e in events):
            raise ValueError("a c4-memory-trace has a non-empty list of events, each with a step and a tx_time")
        self.actor = f"trace:{self.trace_id}"
        self._events = sorted(enumerate(events), key=lambda x: x[1]["step"])
        self.start = format_timestamp(parse_timestamp(self._events[0][1]["tx_time"]) - _SECOND)
        self._entities = list(trace.get("entities") or [])
        self.store = MemoryStore(self.schema, clock=ScenarioClock(self.start))
        self.times: dict[int, str] = {}
        self.position: str | int | None = None

    def run(self, *, upto_step: int | None = None) -> Replay:
        """Replay the trace (up to and including ``upto_step``) and return the replay."""
        self.position = "entities"
        if self._entities:
            self.store.put(copy.deepcopy(self._entities), actor=self.actor, at=self.start)
        for index, ev in self._events:
            if upto_step is not None and ev["step"] > upto_step:
                break
            self.position = index
            if "put" in ev:
                self.store.put(copy.deepcopy(ev["put"]), actor=self.actor, at=ev["tx_time"])
            else:
                self.store.apply(copy.deepcopy(ev["apply"]), actor=self.actor, at=ev["tx_time"])
            self.times[ev["step"]] = ev["tx_time"]
        self.position = None
        return self

    def tau(self, step: Any) -> str:
        """The ``tx_time`` of ``step``; ``ValueError`` when the replay has no such step."""
        if isinstance(step, bool) or step not in self.times:
            raise ValueError(f"trace {self.trace_id!r} has no step {step!r} (replayed: {sorted(self.times)})")
        return self.times[step]

    def entities(self) -> dict[str, dict[str, Any]]:
        """The entity records of the store (latest versions), by id: they resolve redirects in answers."""
        return {r["id"]: r for r in self.store.iter_records() if r.get("kind") == "entity"}


def replay_trace(trace: Mapping[str, Any], schema: Any, *, upto_step: int | None = None) -> Replay:
    """``Replay(trace, schema).run(upto_step=upto_step)``: the trace replayed into a fresh ``MemoryStore``."""
    return Replay(trace, schema).run(upto_step=upto_step)


def _collect(records: Iterable[Mapping[str, Any]], role: str, into: dict[str, dict[str, Any]]) -> None:
    """Add the values of ``role`` in ``records`` to ``into`` ({identity key: canonical value}); the first writing of
    a value (in id order) is kept, and unbound values are no answers."""
    for r in records:
        for b in r.get("bindings") or []:
            v = b.get("value")
            if b.get("role") == role and value_kind(v) != "unbound":
                into.setdefault(identity_key(v), canonical_value(v))


def _sorted(values: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [values[k] for k in sorted(values)]


def read_gold(replay: Replay, question: Mapping[str, Any], *,
              incorrect_reasons: Iterable[str] = INCORRECT_REASONS) -> dict[str, Any]:
    """The memory gold of ``question`` read from a replay at τ, the ``tx_time`` of its ``ask_after_step`` (the table
    of §9.5): ``{answer: {values}, stale_values, future_values, disputed_values, answerable, as_at}``.

    Raises ``ValidationError`` S001 or S002 when the question's relation, key roles or target role are not in the
    schema, and ``ValueError`` when the replay has no such step, the relation declares no key, or the key does not
    bind exactly the key roles."""
    reasons = _reasons(incorrect_reasons)
    schema, store = replay.schema, replay.store
    tau = replay.tau(_field(question, "ask_after_step", "c4-memory-question"))
    rel = _field(question, "relation", "c4-memory-question")
    role = _field(question, "target_role", "c4-memory-question")
    key = list(_field(question, "key", "c4-memory-question"))
    w = _field(question, "where", "c4-memory-question")
    schema.usage(rel, role)
    for p in key:
        schema.usage(rel, p["role"] if isinstance(p, Mapping) and isinstance(p.get("role"), str) else "")
    try:
        where = Where(status=w["status"], rank=w["rank"], as_of=w["as_of"], valid_mode=w["valid_mode"], as_at=tau)
    except (KeyError, TypeError) as e:
        raise ValueError(f"where is {{as_of, valid_mode, rank, status}}, not {w!r} ({e})") from None
    current = store.find_by_key(rel, key, where=where)
    preferred = [r for r in current if r.get("rank") == "preferred"]
    v_cur: dict[str, dict[str, Any]] = {}
    _collect(preferred or current, role, v_cur)
    t = parse_instant(w["as_of"]) if w["as_of"] is not None else None
    tau_us = parse_timestamp(tau)
    expired: dict[str, dict[str, Any]] = {}
    revised: dict[str, dict[str, Any]] = {}
    future: dict[str, dict[str, Any]] = {}
    disputed: dict[str, dict[str, Any]] = {}
    everything = Where(status=_ALL_STATUSES, rank=_ALL_RANKS, visibility=_ALL_VISIBILITIES, as_at=tau)
    for r in store.find_by_key(rel, key, where=everything):
        status, rank = r.get("status"), r.get("rank", "normal")
        if status == "asserted" and rank != "deprecated" and t is not None:
            b = bounds(r, schema)
            if b.e_hi <= t:
                _collect([r], role, expired)
            elif b.s_lo > t:
                _collect([r], role, future)
        if status in ("superseded", "retracted") and any(
                v.get("status") == "asserted" and parse_timestamp(v["recorded_at"]) < tau_us
                for v in store.history(r["id"])):
            _collect([r], role, revised)
        if rank == "deprecated" and set(r.get("rank_reason") or []) & reasons:
            _collect([r], role, revised)
        if status == "disputed":
            _collect([r], role, disputed)
    for d in (expired, revised, future, disputed):
        for k in v_cur:
            d.pop(k, None)
    stale = [{"value": v, "kind": "expired"} for v in _sorted(expired)] + \
            [{"value": revised[k], "kind": "revised"} for k in sorted(revised) if k not in expired]
    return {"answer": {"values": _sorted(v_cur)}, "stale_values": stale, "future_values": _sorted(future),
            "disputed_values": _sorted(disputed), "answerable": bool(v_cur) or not disputed, "as_at": tau}


def derive_memory_gold(trace: Mapping[str, Any], question: Mapping[str, Any], *, schema: Any,
                       incorrect_reasons: frozenset[str] = INCORRECT_REASONS) -> dict[str, Any]:
    """The memory gold of ``question`` replayed from ``trace`` (DESIGN §9.5, normative).

    Replays the trace into a fresh ``MemoryStore`` up to the question's ``ask_after_step`` and reads the table at
    its ``tx_time`` τ. Returns ``{answer: {values}, stale_values: [{value, kind}], future_values, disputed_values,
    answerable, as_at}``. The question needs ``ask_after_step``, ``relation``, ``key``, ``target_role`` and
    ``where`` (not its gold fields). Store errors of the replay propagate (``ValidationError``, ``VersionError``,
    ``KeyCollision``); see ``read_gold`` for the question's own errors."""
    tid = question.get("trace_id") if isinstance(question, Mapping) else None
    if tid is not None and tid != _field(trace, "trace_id", "c4-memory-trace"):
        raise ValueError(f"the question names trace {tid!r}, not {trace.get('trace_id')!r}")
    step = _field(question, "ask_after_step", "c4-memory-question")
    if isinstance(step, bool) or not isinstance(step, int):
        raise ValueError(f"ask_after_step is a step number, not {step!r}")
    return read_gold(replay_trace(trace, schema, upto_step=step), question, incorrect_reasons=incorrect_reasons)


# ------------------------------------------------------------------------------------------------ gold checks


def _nested(code: str, path: str, message: str, inner: Mapping[str, Any] | None) -> Finding:
    f: Finding = {**make_finding(code, path, message)}
    if inner is not None:
        f["nested"] = dict(inner)
    return f


def replay_findings(error: BaseException, *, path: str = "") -> list[Finding]:
    """I003 for a trace the store refuses: one finding per error finding of ``error`` (a ``KHGError``), each under
    ``nested``; without a code, one I003 with the message."""
    if isinstance(error, KHGError):
        inner = [f for f in error.info.get("findings") or [] if f.get("severity", "error") == "error"]
        if not inner:
            inner = [make_finding(c, "", error.message) for c in error.codes]
        if inner:
            return [_nested("KHG-I003", path, f"the store refuses the replay: {f.get('code')}: "
                                              f"{f.get('message', '')}", f) for f in inner]
    return [make_finding("KHG-I003", path, f"the store cannot replay the trace: {type(error).__name__}: {error}")]


def _keys(values: Any, path: str, bad: list[Finding], kinds: bool = False) -> list[Any] | None:
    """The sorted identity keys of stored values (with their kind for stale values), or None after an I003."""
    out: list[Any] = []
    for j, x in enumerate(values):
        v = x["value"] if kinds else x
        try:
            k = identity_key(v)
        except (KHGError, ValueError, TypeError, KeyError) as e:
            code = e.code if isinstance(e, KHGError) and e.code else "KHG-C001"
            p = f"{path}/{j}" + ("/value" if kinds else "")
            inner = make_finding(code, "", str(e))
            bad.append(_nested("KHG-I003", p, f"an embedded value is invalid: {code}: {e}", inner))
            return None
        out.append((k, x["kind"]) if kinds else k)
    return sorted(out)


def _show(keys: Sequence[Any]) -> str:
    text = ", ".join(k if isinstance(k, str) else f"{k[1]} {k[0]}" for k in keys)
    return "[" + (text if len(text) <= 160 else text[:159] + "…") + "]"


def gold_findings(question: Mapping[str, Any], gold: Mapping[str, Any], *, path: str = "") -> list[Finding]:
    """I005 for each stored gold field of ``question`` that disagrees with ``gold`` (the replay). Value lists compare
    as multisets of value identities (stale values with their kind), so order and writing do not matter;
    ``answer.text`` is not compared. I003 for a stored value whose identity cannot be computed."""
    out: list[Finding] = []
    pairs = [("answer/values", question["answer"]["values"], gold["answer"]["values"], False),
             ("stale_values", question["stale_values"], gold["stale_values"], True),
             ("future_values", question["future_values"], gold["future_values"], False),
             ("disputed_values", question["disputed_values"], gold["disputed_values"], False)]
    for name, stored, derived, kinds in pairs:
        p = f"{path}/{name}"
        mine = _keys(stored, p, out, kinds)
        theirs = _keys(derived, p, [], kinds)
        if mine is not None and mine != theirs:
            out.append(make_finding("KHG-I005", p, f"stored {_show(mine)}, derive_memory_gold replays "
                                                   f"{_show(theirs or [])}"))
    if bool(question["answerable"]) != bool(gold["answerable"]):
        out.append(make_finding("KHG-I005", f"{path}/answerable",
                                f"stored {question['answerable']}, derive_memory_gold replays {gold['answerable']}"))
    return out


def check_question(replay: Replay, question: Mapping[str, Any], *, path: str = "",
                   incorrect_reasons: Iterable[str] = INCORRECT_REASONS) -> tuple[dict[str, Any] | None,
                                                                                   list[Finding]]:
    """``(gold, findings)`` for a ``c4-memory-question`` against its replayed trace: the gold read at τ and the
    I005 findings of ``gold_findings``. A question the replay cannot answer gives no gold: I003 (the S finding
    nested) for a relation, key role or target role outside the schema, I005 for a step the trace lacks, a relation
    without a key or a key that does not bind exactly the key roles."""
    try:
        gold = read_gold(replay, question, incorrect_reasons=incorrect_reasons)
    except KHGError as e:
        inner = [f for f in e.info.get("findings") or []] or [make_finding(c, "", e.message) for c in e.codes]
        return None, [_nested("KHG-I003", path, f"the question's relation, roles or values are refused: "
                                                f"{f.get('code')}: {f.get('message', '')}", f) for f in inner]
    except ValueError as e:
        return None, [make_finding("KHG-I005", path, f"derive_memory_gold cannot replay the question: {e}")]
    return gold, gold_findings(question, gold, path=path)


# ------------------------------------------------------------------------------------------------ outcomes


def _quantity(value: Mapping[str, Any]) -> tuple[Decimal, str] | None:
    lit = value.get("literal") if isinstance(value, Mapping) else None
    if isinstance(lit, Mapping) and lit.get("datatype") == "quantity":
        return decimal(lit["amount"]), lit["unit"]
    return None


#: The gold sets that decide an outcome; a disputed value is counted in ``hits`` but never changes the outcome.
_OUTCOME_SETS = ("current", "expired", "revised", "future")


def _hits(key: str, value: Mapping[str, Any], gold: Mapping[str, Mapping[str, Any]],
          tolerance: Decimal | None) -> list[str]:
    """The gold values an answered value matches: by identity, or a quantity of the same unit within the tolerance."""
    if key in gold:
        return [key]
    q = _quantity(value) if tolerance is not None else None
    if q is None:
        return []
    out = []
    for k in sorted(gold):
        g = _quantity(gold[k])
        if g is not None and g[1] == q[1] and abs(g[0] - q[0]) <= tolerance:  # type: ignore[operator]
            out.append(k)
    return out


def _index(values: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {identity_key(v): v for v in values}


def classify(answered: Sequence[tuple[str, Mapping[str, Any]]], abstained: bool, gold: Mapping[str, Any], *,
             tolerance: Decimal | None = None) -> dict[str, Any]:
    """The outcome of one response (R05 §5.2; the table in the module docstring) against a question's gold.

    ``answered`` is Â as ``[(identity key, canonical value)]`` (redirects resolved), ``abstained`` the response's
    flag, ``gold`` a ``read_gold`` dict and ``tolerance`` a quantity tolerance. Returns ``{outcome, strict, lenient,
    stale_kind, hits, set}``: ``hits`` counts the gold values met per set (``current``, ``expired``, ``revised``,
    ``future``, ``disputed``) and the answered values that meet none (``other``); ``set`` is P/R/F1 of Â against
    V_cur (None for an abstention or an unanswerable question). A disputed value never changes the outcome.

    Identity comes first: an answered value equal to a value of V_cur, V_old or V_fut matches by identity only, and
    the tolerance reaches only the answered values that equal none of them. So a tolerance never makes an exact
    current answer hedged, nor gives an exact stale answer lenient credit."""
    sets = {"current": _index(gold["answer"]["values"]),
            "expired": _index(s["value"] for s in gold["stale_values"] if s["kind"] == "expired"),
            "revised": _index(s["value"] for s in gold["stale_values"] if s["kind"] == "revised"),
            "future": _index(gold["future_values"]), "disputed": _index(gold["disputed_values"])}
    distinct = dict(answered)
    hit: dict[str, set[str]] = {name: set() for name in sets}
    matched = other = 0
    for k in sorted(distinct):
        near = None if any(k in sets[name] for name in _OUTCOME_SETS) else tolerance
        got = {name: _hits(k, distinct[k], members, near) for name, members in sets.items()}
        for name, found in got.items():
            hit[name].update(found)
        matched += bool(got["current"])
        other += not any(got.values())
    cur, old, fut = bool(hit["current"]), bool(hit["expired"] or hit["revised"]), bool(hit["future"])
    stale_kind = None
    if not gold["answerable"]:
        outcome = "correct_abstention" if abstained or not distinct else "hallucinated"
    elif abstained or (not distinct and sets["current"]):
        outcome = "abstained"
    elif not distinct or (cur and not (old or fut)):
        outcome = "current"  # an empty answer is right when the gold is "no current value"
    elif cur:
        outcome = "hedged"
    elif old:
        outcome, stale_kind = "stale", "expired" if hit["expired"] else "revised"
    elif fut:
        outcome = "anachronistic"
    else:
        outcome = "wrong"
    strict = int(outcome in ("current", "correct_abstention"))
    counts = {name: len(found) for name, found in hit.items()}
    counts["other"] = other
    pr = None
    if gold["answerable"] and not abstained:
        pr = prf_split(matched, len(distinct), len(hit["current"]), len(sets["current"]))
    return {"outcome": outcome, "strict": strict, "lenient": int(strict or outcome == "hedged"),
            "stale_kind": stale_kind, "hits": counts, "set": pr}


# ------------------------------------------------------------------------------------------------ inputs


def _tolerance(question: Mapping[str, Any], path: str, findings: list[Finding]) -> Decimal | None:
    """The ``amount`` of a question's ``tolerance`` (a number or a C1 decimal string, at least 0); I002 when it is
    neither. Other tolerance keys are not read."""
    tol = question.get("tolerance")
    if not isinstance(tol, Mapping) or "amount" not in tol:
        return None
    amount = tol["amount"]
    try:
        if isinstance(amount, bool) or not isinstance(amount, (int, float, str)):
            raise ValueError(amount)
        d = decimal(amount) if isinstance(amount, str) else Decimal(repr(amount))
        if not d.is_finite() or d < 0:
            raise ValueError(amount)
    except (KHGError, ValueError, ArithmeticError):
        findings.append(make_finding("KHG-I002", f"{path}/tolerance/amount",
                                     f"tolerance amount {amount!r} is not a decimal of at least 0"))
        return None
    return d


def _answered(values: Sequence[Mapping[str, Any]], entities: Mapping[str, Mapping[str, Any]], path: str,
              findings: list[Finding]) -> list[tuple[str, dict[str, Any]]]:
    """``[(identity key, canonical value)]`` of answered values, entities resolved through ``redirect_to``; the
    finding of a value whose identity cannot be computed (S006, a year 0) goes to ``findings``."""
    out = []
    for j, v in enumerate(values):
        if isinstance(v, Mapping) and set(v) == {"entity"} and isinstance(v["entity"], str) and entities:
            v = {"entity": resolve_redirects(v["entity"], entities)}
        try:
            out.append((identity_key(v), canonical_value(v)))
        except KHGError as e:
            findings.append(make_finding(e.code or "KHG-C001", f"{path}/{j}", e.message))
    return out


@dataclass
class _Question:
    """A checked question: the item, its replayed gold, its trace's entities and its tolerance."""

    item: Mapping[str, Any]
    gold: dict[str, Any]
    entities: Mapping[str, Mapping[str, Any]]
    tolerance: Decimal | None


def _checked(qs: list[dict[str, Any]], ts: list[dict[str, Any]], schema: Schema,
             reasons: frozenset[str]) -> tuple[list[_Question], list[Finding]]:
    """Replay the traces the questions name and check each question's stored gold (I002, I003, I005)."""
    findings: list[Finding] = []
    seen: set[str] = set()
    for n, q in enumerate(qs):
        if q["qid"] in seen:
            findings.append(make_finding("KHG-I002", f"/questions/{n}/qid", f"qid {q['qid']!r} appears twice"))
        seen.add(q["qid"])
    trace_at: dict[str, int] = {}
    for m, t in enumerate(ts):
        if t["trace_id"] in trace_at:
            findings.append(make_finding("KHG-I002", f"/traces/{m}/trace_id",
                                         f"trace_id {t['trace_id']!r} appears twice"))
        trace_at.setdefault(t["trace_id"], m)
    replays: dict[str, tuple[Replay, dict[str, dict[str, Any]]] | None] = {}
    out = []
    for n, q in enumerate(qs):
        at = trace_at.get(q["trace_id"])
        if at is None:
            findings.append(make_finding("KHG-I003", f"/questions/{n}/trace_id",
                                         f"no c4-memory-trace has trace_id {q['trace_id']!r}"))
            continue
        if q["trace_id"] not in replays:
            rp = Replay(ts[at], schema)
            try:
                replays[q["trace_id"]] = (rp.run(), rp.entities())
            except (KHGError, ValueError, TypeError, KeyError) as e:
                where = "" if rp.position is None else "/entities" if rp.position == "entities" else \
                    f"/events/{rp.position}"
                findings += replay_findings(e, path=f"/traces/{at}{where}")
                replays[q["trace_id"]] = None
        done = replays[q["trace_id"]]
        if done is None:
            continue
        gold, found = check_question(done[0], q, path=f"/questions/{n}", incorrect_reasons=reasons)
        findings += found
        tolerance = _tolerance(q, f"/questions/{n}", findings)
        if gold is not None:
            out.append(_Question(q, gold, done[1], tolerance))
    return out, findings


# ------------------------------------------------------------------------------------------------ scoring


def _efficacy(scored: Sequence[tuple[str, float]], gold: Mapping[str, Any]) -> int | None:
    """CounterFact's efficacy on ``value_scores`` (R05 M-M6): 1 when the best-scored current value outscores every
    stale value (an unscored value ranks last); None without scores, current values or stale values."""
    old = [identity_key(s["value"]) for s in gold["stale_values"]]
    if not scored or not gold["answer"]["values"] or not old:
        return None
    best: dict[str, float] = {}
    for k, x in scored:
        best[k] = max(best.get(k, float("-inf")), x)
    cur = max(best.get(identity_key(v), float("-inf")) for v in gold["answer"]["values"])
    return int(cur != float("-inf") and cur > max(best.get(k, float("-inf")) for k in old))


def _support(response: Mapping[str, Any], question: Mapping[str, Any]) -> dict[str, int] | None:
    """``support_success@k`` for k in ``KS``: the current support inside the hyperedges of the top-k units (by
    ``rank``, then input order); None without retrieved units or support."""
    support = set(question["support"])
    if "retrieved" not in response or not support:
        return None
    units = [u for _, u in sorted(enumerate(response["retrieved"]), key=lambda x: (x[1]["rank"], x[0]))]
    return {f"support_success@{k}": int(support <= {h for u in units[:k] for h in u["hyperedge_ids"]}) for k in KS}


def _mean(values: Iterable[Any]) -> Fraction | None:
    return mean([Fraction(v) for v in values])


def _rate(count: int, n: int) -> Fraction | None:
    return Fraction(count, n) if n else None


def _block(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {o: sum(1 for r in rows if r["outcome"] == o) for o in (*OUTCOMES, MISSING)}
    return {"n": len(rows), "acc_strict": _mean(r["strict"] for r in rows),
            "acc_lenient": _mean(r["lenient"] for r in rows), "outcomes": counts}


def _row(q: _Question, r: Mapping[str, Any] | None, answered: list[tuple[str, dict[str, Any]]],
         scored: list[tuple[str, float]]) -> dict[str, Any]:
    item, gold = q.item, q.gold
    row: dict[str, Any] = {"qid": item["qid"], "answerable": gold["answerable"], "subtype": item["subtype"],
                           "relation": item["relation"], "trace_id": item["trace_id"],
                           "ask_after_step": item["ask_after_step"], "depends_on": sorted(set(item["support"])),
                           "missing": r is None}
    if r is None:
        row.update(outcome=MISSING, strict=0, lenient=0)
        return row
    c = classify(answered, bool(r["answer"]["abstained"]), gold, tolerance=q.tolerance)
    row.update(outcome=c["outcome"], strict=c["strict"], lenient=c["lenient"], stale_kind=c["stale_kind"],
               hits=c["hits"])
    if c["set"] is not None:
        row.update(set_p=c["set"]["p"], set_r=c["set"]["r"], set_f1=c["set"]["f1"], set_flag=c["set"]["flag"])
    if gold["answerable"]:
        row["ranked_efficacy"] = _efficacy(scored, gold)
    row.update(_support(r, item) or {})
    return row


def _aggregate(rows: list[dict[str, Any]], n_responses: int, n_unmatched: int, mode: str) -> dict[str, Any]:
    answerable = [r for r in rows if r["answerable"]]
    count = _block(rows)["outcomes"]
    n_a, n_u = len(answerable), len(rows) - len(answerable)
    expired = sum(1 for r in rows if r["outcome"] == "stale" and r.get("stale_kind") == "expired")
    abstaining = count["abstained"] + count["correct_abstention"]
    acc = {"acc_strict": _mean(r["strict"] for r in rows), "acc_lenient": _mean(r["lenient"] for r in rows)}
    headline = "acc_strict" if mode == "strict" else "acc_lenient"
    efficacy = [r["ranked_efficacy"] for r in rows if r.get("ranked_efficacy") is not None]
    supported = [r for r in rows if "support_success@1" in r]
    return {
        "n_questions": len(rows), "n_responses": n_responses, "n_missing": count[MISSING],
        "n_unmatched_responses": n_unmatched, "n_answerable": n_a, "n_unanswerable": n_u,
        "headline": {"metric": headline, "value": acc[headline]}, **acc, "pooled_abstention": True,
        "answerable": _block(answerable), "outcomes": count,
        "stale_rate": _rate(count["stale"], n_a), "stale_expired_rate": _rate(expired, n_a),
        "stale_revised_rate": _rate(count["stale"] - expired, n_a),
        "stale_share_of_errors": _rate(count["stale"], sum(1 for r in answerable if not r["strict"])),
        "anachronism_rate": _rate(count["anachronistic"], n_a), "hedge_rate": _rate(count["hedged"], n_a),
        "abstention_rate": _rate(count["abstained"], n_a), "wrong_rate": _rate(count["wrong"], n_a),
        "abstention": {"precision": _rate(count["correct_abstention"], abstaining),
                       "recall": _rate(count["correct_abstention"], n_u),
                       "hallucination_rate": _rate(count["hallucinated"], n_u),
                       "n_abstained": abstaining, "n_unanswerable": n_u},
        "set_f1": _mean(r.get("set_f1", 0) for r in answerable),
        "ranked_efficacy": {"value": _mean(efficacy), "n": len(efficacy)},
        "support": {"n": len(supported), **{f"support_success@{k}": _mean(r[f"support_success@{k}"]
                                                                           for r in supported) for k in KS}},
    }


def score(questions: Iterable[Mapping[str, Any]], responses: Iterable[Mapping[str, Any]], *,
          traces: Iterable[Mapping[str, Any]], schema: Any, config: MemoryConfig = MemoryConfig()) -> dict[str, Any]:
    """Score memory responses (DESIGN §9.2, §9.3; R05 §5.2).

    ``questions``: ``c4-memory-question`` items; ``traces``: the ``c4-memory-trace`` items they name (a whole C4 file
    may be passed for either); ``responses``: ``memory-response`` records (``khg-c5-io``). The items pass layer I's
    checks: the draft schema, the trace replays (I003) and the stored gold against the replay under
    ``config.incorrect_reasons`` (I005). Returns ``{scorer, config, contracts, aggregate, breakdowns, items,
    bootstrap}`` with ``items`` keyed by qid; raises ``ValidationError`` on a malformed input."""
    if not isinstance(config, MemoryConfig):
        raise TypeError("config must be a MemoryConfig")
    s = as_schema(schema)
    qs, q_headers = _inputs.check_items(questions, kinds=("c4-memory-question",))
    ts, t_headers = _inputs.check_items(traces, kinds=("c4-memory-trace",))
    recs = _inputs.check_outputs(responses, kind="memory-response")
    checked, findings = _checked(qs, ts, s, config.incorrect_reasons)
    by_qid: dict[str, tuple[int, dict[str, Any]]] = {}
    for n, output in enumerate(recs):
        if output["qid"] in by_qid:
            findings.append(make_finding("KHG-C010", f"/responses/{n}/qid",
                                         f"two memory responses for {output['qid']!r}"))
        by_qid.setdefault(output["qid"], (n, output))
    prepared = []
    for q in checked:
        found = by_qid.get(q.item["qid"])
        r: dict[str, Any] | None = None
        answered: list[tuple[str, dict[str, Any]]] = []
        scored: list[tuple[str, float]] = []
        if found is not None:
            n, r = found
            answered = _answered(r["answer"]["values"], q.entities, f"/responses/{n}/answer/values", findings)
            scores = r.get("value_scores") or []
            keys = _answered([x["value"] for x in scores], q.entities, f"/responses/{n}/value_scores", findings)
            if len(keys) == len(scores):  # else a value was refused, and the findings raise below
                scored = [(k, float(x["score"])) for (k, _), x in zip(keys, scores, strict=True)]
        prepared.append((q, r, answered, scored))
    if any(f["severity"] == "error" for f in findings):
        raise ValidationError.from_findings(findings)

    rows = [_row(q, r, answered, scored) for q, r, answered, scored in prepared]
    qids = {q.item["qid"] for q in checked}
    aggregate = _aggregate(rows, len(recs), len(set(by_qid) - qids), config.mode)
    breakdowns: dict[str, Any] = {}
    for key in ("subtype", "relation"):
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            groups.setdefault(str(row[key]), []).append(row)
        breakdowns[f"by_{key}"] = {g: _block(v) for g, v in sorted(groups.items())}
    items = {row["qid"]: {k: v for k, v in row.items() if k != "qid" and v is not None} for row in rows}
    boot: dict[str, Any] | None = None
    if config.bootstrap.resamples and rows:
        boot = {**config.bootstrap.as_dict(), "unit": "question", "n_units": len(rows),
                "intervals": {"acc_strict": mean_interval([row["strict"] for row in rows], config.bootstrap),
                              "acc_lenient": mean_interval([row["lenient"] for row in rows], config.bootstrap)}}
    qsets = [x["qset"] for x in (*qs, *ts, *q_headers, *t_headers)]
    return report("memory", config, aggregate=aggregate, breakdowns=breakdowns, items=items, bootstrap=boot,
                  qsets=qsets, schema=s)
