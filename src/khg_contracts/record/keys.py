"""Keys, the key invariant, L008 and collisions (DESIGN §2.5, §2.6).

A relation may declare ``key: {roles, temporal, on_collision}``; ``record.key_digest`` hashes a fact's key bindings
by value identity, and is None without a key, with a key role absent, or with a special or unbound key value.

- **The invariant (D016).** The facts with status ``asserted``, a rank other than ``deprecated``, a fact relation
  and a non-null key digest form groups by (relation, key digest). At every instant of their *definite* windows
  (§2.6), or at every instant for a non-temporal key, at most one of them holds, or exactly one of those holding is
  ``preferred``. The set of holding facts changes only where a definite window starts or ends, so the judgement is
  made at each of those instants (``key_invariant_violations``).
- **L008.** Two facts of one temporal key whose windows possibly, but not definitely, overlap: a warning of store
  receipts and ``validate_container`` (``possible_only_overlaps``, ``l008_warnings``).
- **Collisions.** ``collisions`` gives the ``info["collisions"]`` of ``KeyCollision``: every incoming record that
  breaks the invariant or the disputed-key rule, with its policy and, per conflict, the ``shape``, the ``class``
  and the normative ``action`` of the §2.5 table (``action_for``). The store checks invariants and never applies a
  policy; the caller acts.
"""
from __future__ import annotations

from typing import Any, Collection, Iterable, Mapping, NamedTuple, Union

from ..errors import KeyCollision
from ..schema import Schema
from ._common import SchemaLike, as_schema, hyperedge
from .derive import content_key, key_digest
from .refine import fact_refines
from .validity import Bounds, bounds, definite_overlap, possible_overlap
from .windows import NEG_INF, POS_INF, format_instant

__all__ = [
    "ACTIONS",
    "CLASSES",
    "MERGE_CLASSES",
    "POLICIES",
    "SHAPES",
    "Violation",
    "action_for",
    "classify",
    "collisions",
    "key_collision",
    "key_groups",
    "key_invariant_violations",
    "l008_warnings",
    "possible_only_overlaps",
    "shape_of",
]

Record = Mapping[str, Any]
Records = Union[Mapping[str, Record], Iterable[Record]]
KeyRef = tuple[str, str]

POLICIES = ("close_older", "supersede", "dispute", "reject")
SHAPES = ("succession", "backfill", "overlap_after_end", "same_start")
CLASSES = ("duplicate", "refines", "generalises", "distinct")
#: The classes that make a conflict a merge whatever the policy (R01 case 1; C3-R10).
MERGE_CLASSES = ("duplicate", "refines", "generalises")
ACTIONS = ("merge", "close_older", "close_incoming", "dispute", "supersede", "reject")


class Violation(NamedTuple):
    """Facts of one key that hold together without exactly one ``preferred`` among them: the relation, the key
    digest, whether the key is temporal, the sorted ids, and the first instant where they hold together (the §2.1
    grammar; None for a non-temporal key or when they hold since forever)."""

    relation: str
    key_digest: str
    temporal: bool
    ids: tuple[str, ...]
    at: str | None


def _values(records: Records) -> list[Record]:
    items = records.values() if isinstance(records, Mapping) else records
    return [r for r in items if isinstance(r, Mapping)]


def _by_id(records: Records) -> dict[str, Record]:
    if isinstance(records, Mapping):
        return {k: v for k, v in records.items() if isinstance(v, Mapping)}
    return {r["id"]: r for r in _values(records) if isinstance(r.get("id"), str)}


def _fact(r: Record, s: Schema) -> bool:
    """A hyperedge of a declared fact relation (lifecycle records are excluded from keys, §2.7)."""
    rel = r.get("kind") == "hyperedge" and r.get("relation")
    return isinstance(rel, str) and s.has_relation(rel) and s.kind(rel) != "lifecycle"


def _covered(r: Record, s: Schema, statuses: Collection[str]) -> bool:
    return _fact(r, s) and r.get("status") in statuses and r.get("rank", "normal") != "deprecated"


def _temporal(s: Schema, relation: str) -> bool:
    key = s.key(relation)
    return bool(key and key["temporal"])


def key_groups(records: Records, schema: SchemaLike, *, statuses: Collection[str] = ("asserted",),
               keys: Collection[KeyRef] | None = None) -> dict[KeyRef, list[Record]]:
    """The facts a key constrains, by (relation, key digest) in sorted order, each group in input order: hyperedges
    of fact relations with a status in ``statuses``, a rank other than ``deprecated`` and a non-null key digest.
    ``keys`` restricts the result to those groups."""
    s = as_schema(schema)
    groups: dict[KeyRef, list[Record]] = {}
    for r in _values(records):
        if not _covered(r, s, statuses):
            continue
        kd = key_digest(r, s)
        if kd is None or (keys is not None and (r["relation"], kd) not in keys):
            continue
        groups.setdefault((r["relation"], kd), []).append(r)
    return {k: groups[k] for k in sorted(groups)}


def _holding(rs: list[Record], s: Schema, temporal: bool) -> Iterable[tuple[list[int], float | int | None]]:
    """(indices of the facts that hold, the instant) at every instant where the holding set changes; one set, at
    no instant, for a non-temporal key."""
    if not temporal:
        yield list(range(len(rs))), None
        return
    windows = [(i, b.s_hi, b.e_lo) for i, b in ((i, bounds(r, s)) for i, r in enumerate(rs)) if b.s_hi < b.e_lo]
    points = sorted({x for _, lo, hi in windows for x in (lo, hi)})
    for p in points:
        yield [i for i, lo, hi in windows if lo <= p < hi], p


def key_invariant_violations(records: Records, schema: SchemaLike, *,
                             keys: Collection[KeyRef] | None = None) -> list[Violation]:
    """D016 over a set of current records: every set of facts of one key that hold together, at some instant of
    their definite windows (at any instant, for a non-temporal key), without exactly one ``preferred`` among them.
    Groups in key order, then by instant; a set is listed once, at the first instant where it holds."""
    s = as_schema(schema)
    out: list[Violation] = []
    for (rel, kd), rs in key_groups(records, s, keys=keys).items():
        temporal = _temporal(s, rel)
        seen: set[tuple[str, ...]] = set()
        for held, p in _holding(rs, s, temporal):
            if len(held) < 2 or sum(rs[i].get("rank") == "preferred" for i in held) == 1:
                continue
            ids = tuple(sorted(str(rs[i].get("id")) for i in held))
            if ids not in seen:
                seen.add(ids)
                at = format_instant(p) if p is not None and p not in (NEG_INF, POS_INF) else None
                out.append(Violation(rel, kd, temporal, ids, at))
    return out


def possible_only_overlaps(records: Records, schema: SchemaLike, *,
                           ids: Collection[str] | None = None) -> list[tuple[str, str]]:
    """L008: the pairs of facts of one temporal key whose windows possibly but not definitely overlap, as sorted id
    pairs, in key order. With ``ids``, only the pairs that include one of them."""
    s = as_schema(schema)
    wanted = None if ids is None else set(ids)
    out: list[tuple[str, str]] = []
    for (rel, _), rs in key_groups(records, s).items():
        if not _temporal(s, rel) or (wanted is not None and not any(r.get("id") in wanted for r in rs)):
            continue
        facts = sorted(((str(r.get("id")), bounds(r, s)) for r in rs), key=lambda x: x[0])
        for n, (a, ba) in enumerate(facts):
            for b, bb in facts[n + 1:]:
                if wanted is not None and a not in wanted and b not in wanted:
                    continue
                if possible_overlap(ba, bb) and not definite_overlap(ba, bb):
                    out.append((a, b))
    return out


def l008_warnings(records: Records, schema: SchemaLike, *, ids: Collection[str] | None = None) -> list[dict[str, Any]]:
    """The L008 warnings of a store receipt (§6.1): ``[{"code": "KHG-L008", "ids": [a, b]}]`` for every possible-only
    overlap in the current ``records``; with ``ids`` (the records a write touched), those that involve one of them."""
    return [{"code": "KHG-L008", "ids": list(pair)} for pair in possible_only_overlaps(records, schema, ids=ids)]


# ------------------------------------------------------------------------------------------------ one conflict


def classify(incoming: Record, stored: Record, schema: SchemaLike) -> str:
    """The class of a conflict, from refinement (§2.9): ``duplicate`` (equal content keys), ``refines`` (incoming ⊑
    stored), ``generalises`` (stored ⊑ incoming) or ``distinct``."""
    s = as_schema(schema)
    if content_key(incoming, s) == content_key(stored, s):
        return "duplicate"
    if fact_refines(incoming, stored, s):
        return "refines"
    if fact_refines(stored, incoming, s):
        return "generalises"
    return "distinct"


def shape_of(incoming: Record, stored: Record, schema: SchemaLike) -> str | None:
    """The shape of a conflict on a temporal key (None for a non-temporal key). The fact whose start window lies
    wholly before the other's is the earlier one: ``succession`` when that is the stored fact and it still holds (its
    end is absent or ``novalue``), ``backfill`` when it is the incoming fact and it still holds,
    ``overlap_after_end`` when the earlier fact has an end, and ``same_start`` when neither start lies before the
    other (two starts at -inf included)."""
    s = as_schema(schema)
    hyperedge(incoming)
    if not _temporal(s, incoming.get("relation")):
        return None
    n, o = bounds(incoming, s), bounds(stored, s)
    stored_first, incoming_first = o.s_hi <= n.s_lo, n.s_hi <= o.s_lo
    if stored_first == incoming_first:
        return "same_start"
    earlier: Bounds = o if stored_first else n
    if earlier.e_lo == POS_INF:
        return "succession" if stored_first else "backfill"
    return "overlap_after_end"


def action_for(policy: str, cls: str, shape: str | None) -> str:
    """The normative action of the §2.5 table: ``merge`` for a duplicate, refining or generalising conflict whatever
    the policy; for a distinct one, ``close_older`` on a succession and ``close_incoming`` on a backfill under
    ``close_older`` (else ``dispute``), and the policy itself under ``dispute``, ``supersede`` or ``reject``."""
    if cls not in CLASSES:
        raise ValueError(f"class must be one of {CLASSES}, not {cls!r}")
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}, not {policy!r}")
    if shape is not None and shape not in SHAPES:
        raise ValueError(f"shape must be one of {SHAPES} or None, not {shape!r}")
    if cls in MERGE_CLASSES:
        return "merge"
    if policy == "close_older":
        return {"succession": "close_older", "backfill": "close_incoming"}.get(shape or "", "dispute")
    return policy


# ------------------------------------------------------------------------------------------------ a write


def _conflict(r: Record, other: Record, s: Schema, batch_ids: set[Any], policy: str) -> dict[str, Any]:
    cls, shape = classify(r, other, s), shape_of(r, other, s)
    return {"id": other.get("id"), "in_batch": other.get("id") in batch_ids, "shape": shape, "class": cls,
            "action": action_for(policy, cls, shape)}


def collisions(state: Records, batch: Iterable[Record], schema: SchemaLike, *, post: Records | None = None,
               disputed_rule: bool = True) -> list[dict[str, Any]]:
    """What a write raises as ``KeyCollision`` (§2.5); [] when it is accepted.

    ``state`` holds the current records before the write (``{id: record}`` or records), ``batch`` the records
    written, and ``post`` the whole state after the write when it is not ``state`` overlaid with ``batch`` (an event
    that also changes other records). Each incoming asserted fact of a keyed relation (not deprecated) collides with
    the facts it holds together with in a violation of the invariant, and, with ``disputed_rule`` (a ``put``), with
    the ``disputed`` facts of its key when the key is not temporal or their definite windows overlap: it joins
    their dispute (policy ``dispute``). Collisions come in record id order, each conflict list in id order with the
    disputed facts last::

        {"record", "relation", "key_digest", "policy", "conflicts": [{"id", "in_batch", "shape", "class",
         "action"}]}

    ``state`` and ``post`` may be restricted to the facts of the batch's keys (a store's key index): the result is
    the same.
    """
    s = as_schema(schema)
    incoming = sorted(_values(batch), key=lambda r: str(r.get("id")))
    after = _by_id(post) if post is not None else {**_by_id(state), **{r["id"]: r for r in incoming}}
    batch_ids = {r.get("id") for r in incoming}
    keyed = [(r, key_digest(r, s)) for r in incoming if _covered(r, s, ("asserted",))]
    keyed = [(r, kd) for r, kd in keyed if kd is not None]
    touched = {(r["relation"], kd) for r, kd in keyed}
    violations = key_invariant_violations(after.values(), s, keys=touched)
    disputed = key_groups(after.values(), s, statuses=("disputed",), keys=touched) if disputed_rule else {}
    out = []
    for r, kd in keyed:
        rel = r["relation"]
        key = s.key(rel)
        temporal = bool(key["temporal"])
        conflict_ids = sorted({i for v in violations if (v.relation, v.key_digest) == (rel, kd) and r["id"] in v.ids
                               for i in v.ids} - {r["id"]})
        joined = [x for x in disputed.get((rel, kd), []) if x.get("id") != r["id"]
                  and (not temporal or definite_overlap(bounds(r, s), bounds(x, s)))]
        if not conflict_ids and not joined:
            continue
        policy = key["on_collision"]
        conflicts = [_conflict(r, after[i], s, batch_ids, policy) for i in conflict_ids]
        conflicts += [_conflict(r, x, s, batch_ids, "dispute")
                      for x in sorted(joined, key=lambda x: str(x.get("id")))]
        out.append({"record": r["id"], "relation": rel, "key_digest": kd,
                    "policy": policy if conflict_ids else "dispute", "conflicts": conflicts})
    return out


def key_collision(found: list[dict[str, Any]], message: str | None = None) -> KeyCollision:
    """The ``KeyCollision`` (D016) for the ``collisions`` of a write; ``info["collisions"]`` holds them."""
    if message is None:
        ids = ", ".join(str(c.get("record")) for c in found)
        message = f"the write breaks the key invariant or the disputed-key rule ({ids}); nothing was written"
    return KeyCollision(message, codes=["KHG-D016"], info={"collisions": found})
