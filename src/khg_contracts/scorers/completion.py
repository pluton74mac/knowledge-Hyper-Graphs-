"""The completion scorer (DESIGN §9.2, §9.3; R05 §3.2): n-ary link prediction scored from rank statistics.

- ``build_queries`` writes one ``c4-completion-query`` per core or qualifier binding of each fact (literal targets
  excluded and counted by default).
- ``FilterIndex.from_records(train, valid, test)`` indexes the known facts. Its filters (C-M1) compare the other
  bindings of a query as a set, never as a sequence: ``exact`` (the same relation and the same core and qualifier
  bindings apart from the target), ``monotone`` (a known fact that refines the completed query, ⊑, such as one
  with more qualifiers) and ``time_aware`` (``exact`` restricted to known facts whose definite validity overlaps the
  query fact's).
- ``rank_stats`` turns a model's scores into a ``completion-rank`` record (``khg-c5-io``): ``n_candidates``,
  ``n_filtered_out``, ``n_greater``, ``n_equal`` and the optional probabilities. The model never hands C5 a score
  vector.
- ``score`` reads queries and records. Ranks: o = 1 + n_greater, p = o + n_equal; ``tie_exact`` (the default) takes
  the expectation under uniformly random tie-breaking (E[RR] = Σ_{r=o..p} (1/r)/(p−o+1)), with ``optimistic``,
  ``pessimistic``, ``realistic`` and ``model`` (the model's own order, ``model_rank``) beside it. MRR, Hits@k and
  MR are averaged per task, per fact and macro over the arity bins (on ``arity`` and ``model_arity``). Calibration
  is top-1: equal-width and equal-mass ECE, the reliability tables and Brier, overall and per arity bin.
- Presets: ``hype`` (all positions, pessimistic ties, the full-tuple filter, per-task average), ``hyper`` (all
  positions, pessimistic ties) and ``stare`` (subject and object from ``primary``, averaged; ties in the model's
  order, else pessimistic with ``approximated: ["sort_order_ties"]``; a qualifier-set filter, always
  ``approximated: ["qualifier_order"]``).
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable, Literal, Mapping, Sequence

from .. import jsonio
from ..errors import ValidationError, make_finding
from ..record import (
    arity_bin,
    binding_sort_key,
    bounds,
    canonical_value,
    content_bindings,
    definite_overlap,
    fact_refines,
    identity_key,
    literal_node_id,
    value_kind,
)
from ..schema import Schema
from . import _inputs, calibration
from ._common import arity_pair, as_schema, frac, report
from .bootstrap import Bootstrap, mean_interval

__all__ = ["CompletionConfig", "FILTERS", "FilterIndex", "PRESETS", "QuerySet", "RANKS", "build_queries",
           "candidate_id", "rank_stats", "score"]

FILTERS = ("exact", "monotone", "time_aware")
RANKS = ("tie_exact", "optimistic", "pessimistic", "realistic", "model")
PRESETS = ("hype", "stare", "hyper")
LITERAL_TARGETS = ("exclude", "include")
UNIVERSES = ("entities_of_type", "seen_in_position")
QUERY_SLOTS = ("core", "qualifier")
BINS = ("0-1", "2", "3", "4", "5+")
#: statuses whose facts the filter index treats as known
KNOWN_STATUSES = ("asserted", "disputed")
_EXACT_TIE_BLOCK = 64


@dataclass(frozen=True)
class CompletionConfig:
    """The completion scorer's settings (DESIGN §9.2). A preset overrides ``filter`` and ``rank``."""

    preset: Literal["hype", "stare", "hyper"] | None = None
    filter: Literal["exact", "monotone", "time_aware"] = "exact"   # the other two are reported beside it
    rank: Literal["tie_exact", "optimistic", "pessimistic", "realistic", "model"] = "tie_exact"
    hits: tuple[int, ...] = (1, 3, 10)
    ece_bins: int = 15
    min_bin_queries: int = 100                        # per-arity ECE below this count: counts only
    bootstrap: Bootstrap = Bootstrap()

    def __post_init__(self) -> None:
        for name, value, allowed in (("preset", self.preset, PRESETS + (None,)), ("filter", self.filter, FILTERS),
                                     ("rank", self.rank, RANKS)):
            if value not in allowed:
                raise ValueError(f"{name} must be one of {allowed}, not {value!r}")
        hits = tuple(self.hits)
        if not hits or any(isinstance(k, bool) or not isinstance(k, int) or k < 1 for k in hits):
            raise ValueError(f"hits are positive integers, not {self.hits!r}")
        object.__setattr__(self, "hits", hits)
        for name in ("ece_bins", "min_bin_queries"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < (1 if name == "ece_bins" else 0):
                raise ValueError(f"{name} must be a {'positive' if name == 'ece_bins' else 'non-negative'} "
                                 f"integer, not {v!r}")
        if not isinstance(self.bootstrap, Bootstrap):
            raise ValueError("bootstrap must be a Bootstrap")

    def effective(self) -> tuple[str, str]:
        """``(filter, rank)`` after the preset: ``hype`` and ``hyper`` rank pessimistically with the exact filter;
        ``stare`` uses the model's order with the exact (qualifier-set) filter."""
        if self.preset in ("hype", "hyper"):
            return "exact", "pessimistic"
        if self.preset == "stare":
            return "exact", "model"
        return self.filter, self.rank


# ------------------------------------------------------------------------------------------------ candidates


def candidate_id(value: Mapping[str, Any]) -> str | None:
    """The candidate id of a value: an entity or fact id, the ``_:lit:`` id of a literal (as ``project.positional``
    writes it); None for a special or unbound value, which is never a candidate."""
    kind = value_kind(value)
    if kind in ("entity", "fact"):
        return jsonio.nfc(value[kind])
    if kind == "literal":
        return literal_node_id(value["literal"])
    return None


def _bid_id(prefix: str, fact_id: str, bid: str) -> str:
    text = f"{prefix}{fact_id}#{bid}"
    if len(text) <= 512:
        return text
    return prefix + hashlib.sha256(jsonio.canonical([fact_id, bid]).encode("utf-8")).hexdigest()


class QuerySet(list):
    """``build_queries``' result: the ``c4-completion-query`` items, with ``excluded``, the number of bindings left
    out by reason (``literal`` targets, ``special`` values)."""

    def __init__(self, items: Iterable[dict[str, Any]] = (), excluded: Mapping[str, int] | None = None):
        super().__init__(items)
        self.excluded: dict[str, int] = dict(excluded or {})


def _is_indexable(r: Any, schema: Schema | None) -> bool:
    """A hyperedge that is neither a goal nor a lifecycle record (the ``khg:`` relations are reserved, M008)."""
    if not isinstance(r, Mapping) or r.get("kind") != "hyperedge" or r.get("status") == "goal":
        return False
    rel = r.get("relation")
    if isinstance(rel, str) and rel.startswith("khg:"):
        return False
    return not (schema is not None and schema.has_relation(rel) and schema.kind(rel) == "lifecycle")


def build_queries(facts: Iterable[Mapping[str, Any]], schema: Any, *, slots: tuple[str, ...] = ("core", "qualifier"),
                  literal_targets: Literal["exclude", "include"] = "exclude",
                  universe: Literal["entities_of_type", "seen_in_position"] = "entities_of_type",
                  qset: str = "khg-completion", split: str = "test") -> QuerySet:
    """One ``c4-completion-query`` per core or qualifier binding of each fact (DESIGN §9.2), in fact-id and canonical
    binding order. The context is the fact's other bindings in ``slots``. Special values are never targets; literal
    targets are excluded unless ``literal_targets="include"``. Both are counted in ``.excluded``.

    ``universe``: ``entities_of_type`` names the target usage's entity types; ``seen_in_position`` lists the
    entities seen in the target's position among ``facts`` (for a ``primary`` subject or object: every entity seen
    as a subject or object, as StarE's WD50K universe; else the entities seen in that role). A fact target lists the
    facts of the relations its usage admits, and a literal target the literals seen in its role."""
    s = as_schema(schema)
    slots = tuple(slots)
    if not slots or any(x not in QUERY_SLOTS for x in slots):
        raise ValueError(f"slots are a non-empty subset of {QUERY_SLOTS}, not {slots!r}")
    if literal_targets not in LITERAL_TARGETS:
        raise ValueError(f"literal_targets must be one of {LITERAL_TARGETS}, not {literal_targets!r}")
    if universe not in UNIVERSES:
        raise ValueError(f"universe must be one of {UNIVERSES}, not {universe!r}")
    if split not in ("train", "valid", "test") or not isinstance(qset, str) or not qset:
        raise ValueError("qset is a non-empty string and split one of train, valid, test")
    records = sorted((r for r in facts if _is_indexable(r, s)), key=lambda r: str(r.get("id")))
    seen_role: dict[str, set[str]] = {}
    seen_primary: set[str] = set()
    literals_role: dict[str, set[str]] = {}
    fact_ids: dict[str, set[str]] = {}
    for r in records:
        fact_ids.setdefault(r["relation"], set()).add(r["id"])
        primary = s.relation(r["relation"]).get("primary") or {}
        for b in content_bindings(r, s, slots):
            kind = value_kind(b["value"])
            if kind == "entity":
                seen_role.setdefault(b["role"], set()).add(b["value"]["entity"])
                if b["role"] in primary.values():
                    seen_primary.add(b["value"]["entity"])
            elif kind == "literal":
                literals_role.setdefault(b["role"], set()).add(literal_node_id(b["value"]["literal"]))
    out = QuerySet(excluded={"literal": 0, "special": 0})
    for r in records:
        rel = r["relation"]
        ar, mar = arity_pair(r, s)
        bs = sorted(content_bindings(r, s, slots), key=binding_sort_key)
        primary = s.relation(rel).get("primary") or {}
        for b in bs:
            kind = value_kind(b["value"])
            if kind in ("special", "unbound"):
                out.excluded["special"] += 1
                continue
            if kind == "literal" and literal_targets == "exclude":
                out.excluded["literal"] += 1
                continue
            usage = s.usage(rel, b["role"])
            if kind == "entity" and universe == "entities_of_type":
                types = sorted({t for f in usage["fillers"] if "entity" in f for t in f["entity"]})
                cu: dict[str, Any] = {"kind": "entities_of_type", "types": types}
            elif kind == "entity":
                pool = seen_primary if b["role"] in primary.values() else seen_role.get(b["role"], set())
                cu = {"kind": "list", "ids": sorted(pool)}
            elif kind == "fact":
                rels = {x for f in usage["fillers"] if "fact" in f for x in f["fact"]}
                cu = {"kind": "list", "ids": sorted(i for x in rels for i in fact_ids.get(x, ()))}
            else:
                cu = {"kind": "list", "ids": sorted(literals_role.get(b["role"], set()))}
            qid = _bid_id("cq:", r["id"], b["bid"])
            out.append({
                "kind": "c4-completion-query", "id": _bid_id("c4:cq:", r["id"], b["bid"]), "qset": qset, "split": split,
                "qid": qid, "fact_id": r["id"], "relation": rel, "arity": ar, "model_arity": mar,
                "target": {"bid": b["bid"], "role": b["role"], "slot": s.slot(rel, b["role"]),
                           "value": canonical_value(b["value"])},
                "context": [dict(x, value=canonical_value(x["value"])) for x in bs if x is not b],
                "candidate_universe": cu})
    return out


# ------------------------------------------------------------------------------------------------ filter index


Triple = tuple[str, Any, str]


def _triple(b: Mapping[str, Any]) -> Triple:
    return b["role"], b.get("position"), identity_key(b["value"])


def _signature(bs: Iterable[Mapping[str, Any]]) -> tuple[Triple, ...]:
    return tuple(sorted(_triple(b) for b in bs))


class FilterIndex:
    """The known facts of the splits, for the filters of C-M1 (DESIGN §9.2). Facts with status ``asserted`` or
    ``disputed`` are known answers; facts in other statuses are kept only to be looked up by id (a query fact's
    validity); goals and lifecycle records are skipped.

    With ``schema`` the filters compare the bindings in ``slots`` (core and qualifier by default), so time bindings
    never take part in ``exact`` and ``time_aware`` reads the bound table. Without one every binding is compared
    (the full-tuple filter, with the query fact's own bindings when it is indexed), and ``monotone`` and
    ``time_aware`` are unavailable."""

    def __init__(self, facts: Sequence[Mapping[str, Any]], splits: Sequence[str], *, schema: Schema | None = None,
                 slots: tuple[str, ...] = QUERY_SLOTS):
        self.schema = schema
        self.slots = tuple(slots)
        self._facts: list[Mapping[str, Any]] = []
        self._split: dict[str, str] = {}
        self._records: dict[str, Mapping[str, Any]] = {}
        self._exact: dict[tuple[str, str, tuple[Triple, ...]], list[tuple[str, int]]] = {}
        self._by_relation: dict[str, list[int]] = {}
        self._anchor: dict[tuple[str, Triple], list[int]] = {}
        for r, sp in zip(facts, splits, strict=True):
            if not _is_indexable(r, schema):
                continue
            if isinstance(r.get("id"), str) and r["id"] not in self._records:
                self._records[r["id"]] = r
                self._split[r["id"]] = sp
            if r.get("status", "asserted") not in KNOWN_STATUSES:
                continue
            i = len(self._facts)
            self._facts.append(r)
            rel = r["relation"]
            self._by_relation.setdefault(rel, []).append(i)
            bs = self._filter_bindings(r)
            for x in bs:
                if value_kind(x["value"]) == "entity":
                    self._anchor.setdefault((rel, _triple(x)), []).append(i)
            for k, b in enumerate(bs):
                cid = candidate_id(b["value"])
                if cid is None:
                    continue
                key = (rel, b["role"], _signature(bs[:k] + bs[k + 1:]))
                self._exact.setdefault(key, []).append((cid, i))

    @classmethod
    def from_records(cls, *splits: Iterable[Mapping[str, Any]], schema: Any = None,
                     slots: tuple[str, ...] = QUERY_SLOTS, manifest: Mapping[str, Any] | None = None) -> FilterIndex:
        """Index the facts of the splits (C1 records; entities and other records are skipped). The splits are named
        ``train``, ``valid`` and ``test`` in that order (``split4``… beyond three). With a ``c4-split-manifest``
        item, only the facts it lists are indexed, under its split names. ``slots`` must be the slots the queries
        were built with (``build_queries``' default is the same)."""
        s = as_schema(schema) if schema is not None else None
        slots = tuple(slots)
        if not slots or any(x not in QUERY_SLOTS for x in slots):
            raise ValueError(f"slots are a non-empty subset of {QUERY_SLOTS}, not {slots!r}")
        names = ("train", "valid", "test")
        facts: list[Mapping[str, Any]] = []
        split_of: list[str] = []
        listed = None
        if manifest is not None:
            if not isinstance(manifest, Mapping) or manifest.get("kind") != "c4-split-manifest":
                raise ValueError("manifest is a c4-split-manifest item")
            _inputs.check_items([manifest], kinds=("c4-split-manifest",))
            listed = manifest["splits"]
        for n, split in enumerate(splits):
            for r in split:
                if not isinstance(r, Mapping):
                    continue
                if listed is not None:
                    if r.get("id") not in listed:
                        continue
                    name = listed[r["id"]]
                else:
                    name = names[n] if n < len(names) else f"split{n + 1}"
                facts.append(r)
                split_of.append(name)
        return cls(facts, split_of, schema=s, slots=slots)

    def __len__(self) -> int:
        """The number of known facts."""
        return len(self._facts)

    def split_of(self, fact_id: str) -> str | None:
        """The split an indexed fact came from."""
        return self._split.get(fact_id)

    def fact(self, fact_id: str) -> Mapping[str, Any] | None:
        """An indexed fact by id, whatever its status."""
        return self._records.get(fact_id)

    def _filter_bindings(self, r: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        bs = [b for b in r.get("bindings") or [] if isinstance(b, Mapping)]
        if self.schema is not None and self.schema.has_relation(r.get("relation")):
            bs = content_bindings(r, self.schema, self.slots)
        else:
            bs = [b for b in bs if b.get("role") != "khg:end_cause"]
        return sorted(bs, key=binding_sort_key)

    def _context(self, query: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        rel = query["relation"]
        ctx = [b for b in query.get("context") or [] if isinstance(b, Mapping)]
        if self.schema is not None and self.schema.has_relation(rel):
            return [b for b in ctx if self.schema.slot(rel, b["role"]) in self.slots]
        own = self.fact(query.get("fact_id"))
        if own is not None and own.get("relation") == rel:
            return [b for b in self._filter_bindings(own) if b.get("bid") != query["target"].get("bid")]
        return [b for b in ctx if b.get("role") != "khg:end_cause"]

    def _exact_hits(self, query: Mapping[str, Any]) -> list[tuple[str, int]]:
        key = (query["relation"], query["target"]["role"], _signature(self._context(query)))
        return self._exact.get(key, [])

    def known_answers(self, query: Mapping[str, Any], mode: str = "exact") -> frozenset[str]:
        """The candidate ids the filter ``mode`` treats as known answers of ``query`` (the target's own id
        included when its fact is indexed)."""
        if mode not in FILTERS:
            raise ValueError(f"mode must be one of {FILTERS}, not {mode!r}")
        if mode == "exact":
            return frozenset(c for c, _ in self._exact_hits(query))
        if self.schema is None:
            raise ValueError(f"the {mode} filter needs FilterIndex.from_records(..., schema=...)")
        if mode == "time_aware":
            own = self.fact(query.get("fact_id"))
            if own is None:
                raise ValueError(f"the time_aware filter needs the query fact {query.get('fact_id')!r} in the index")
            window = bounds(own, self.schema)
            return frozenset(c for c, i in self._exact_hits(query)
                             if definite_overlap(bounds(self._facts[i], self.schema), window))
        return self._monotone(query)

    def _monotone(self, query: Mapping[str, Any]) -> frozenset[str]:
        rel, role = query["relation"], query["target"]["role"]
        ctx = self._context(query)
        anchors = [self._anchor.get((rel, _triple(b)), []) for b in ctx if value_kind(b["value"]) == "entity"]
        pool = min(anchors, key=len) if anchors else self._by_relation.get(rel, [])
        out = set()
        for i in pool:
            g = self._facts[i]
            for b in self._filter_bindings(g):
                if b["role"] != role:
                    continue
                cid = candidate_id(b["value"])
                if cid is None or cid in out:
                    continue
                target = {"bid": "b0", "role": role, "value": b["value"]}
                if b.get("position") is not None:
                    target["position"] = b["position"]
                completed = {"kind": "hyperedge", "relation": rel, "bindings": list(ctx) + [target]}
                if fact_refines(g, completed, self.schema):  # type: ignore[arg-type]
                    out.add(cid)
        return frozenset(out)


# ------------------------------------------------------------------------------------------------ rank statistics


def _number(x: Any, what: str, *, lo: float | None = None, hi: float | None = None) -> float | int:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or (isinstance(x, float) and not math.isfinite(x)):
        raise ValueError(f"{what} is a finite number, not {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        raise ValueError(f"{what} lies in [{lo}, {hi}], not {x!r}")
    return x


def _top1_value(value: Any, target: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, str):
        kind = value_kind(target)
        if kind not in ("entity", "fact"):
            raise ValueError("a top-1 candidate id stands for an entity or a fact; give a C1 value for a literal")
        return {kind: value}
    if isinstance(value, Mapping):
        return canonical_value(value)
    raise ValueError(f"top1 names a C1 value or a candidate id, not {type(value).__name__}")


def rank_stats(query: Mapping[str, Any], scores: Mapping[str, float], index: FilterIndex, *,
               universe: Iterable[str] | None = None, target_prob: float | None = None,
               top1: Mapping[str, Any] | tuple[Any, float] | None = None, prob_map: Mapping[str, float] | None = None,
               model_rank: int | None = None, filter: str = "exact") -> dict[str, Any]:
    """The ``completion-rank`` record of one query (``khg-c5-io``). The candidates are ``universe``, else the keys
    of ``scores``; the known answers of ``filter`` other than the target are filtered out, then ``n_greater`` and
    ``n_equal`` count the remaining candidates scored above and level with the target. ``top1`` is ``{value,
    prob}`` or ``(value, prob)``; ``model_rank`` is the target's rank in the model's own order, which must lie in
    the tie block. Raises ``ValueError`` on inconsistent inputs."""
    if not isinstance(query, Mapping) or query.get("kind") != "c4-completion-query":
        raise ValueError("query is a c4-completion-query item")
    if filter not in FILTERS:
        raise ValueError(f"filter must be one of {FILTERS}, not {filter!r}")
    target = candidate_id(query["target"]["value"])
    if target is None:
        raise ValueError(f"{query.get('qid')!r}: a special value is not a completion target")
    candidates = set(universe) if universe is not None else set(scores)
    if target not in candidates or target not in scores:
        raise ValueError(f"{query.get('qid')!r}: the target {target!r} must be a scored candidate")
    known = (index.known_answers(query, filter) - {target}) & candidates
    t = _number(scores[target], f"the score of {target!r}")
    greater = equal = 0
    for c in candidates - known - {target}:
        if c not in scores:
            raise ValueError(f"{query.get('qid')!r}: no score for candidate {c!r}")
        v = _number(scores[c], f"the score of {c!r}")
        greater += v > t
        equal += v == t
    rec: dict[str, Any] = {"kind": "completion-rank", "qid": query["qid"], "n_candidates": len(candidates),
                           "n_filtered_out": len(known), "n_greater": greater, "n_equal": equal}
    if target_prob is not None:
        rec["target_prob"] = _number(target_prob, "target_prob", lo=0, hi=1)
    if top1 is not None:
        value, prob = (top1["value"], top1["prob"]) if isinstance(top1, Mapping) else tuple(top1)
        rec["top1"] = {"value": _top1_value(value, query["target"]["value"]),
                       "prob": _number(prob, "the top-1 probability", lo=0, hi=1)}
    if prob_map is not None:
        rec["prob_map"] = {str(k): _number(v, f"prob_map[{k!r}]") for k, v in prob_map.items()}
    if model_rank is not None:
        if isinstance(model_rank, bool) or not isinstance(model_rank, int) or \
                not 1 + greater <= model_rank <= 1 + greater + equal:
            raise ValueError(f"model_rank {model_rank!r} lies outside the tie block "
                             f"[{1 + greater}, {1 + greater + equal}]")
        rec["model_rank"] = model_rank
    findings = _inputs.c5_findings(rec)
    if findings:
        raise ValidationError.from_findings(findings)
    return rec


# ------------------------------------------------------------------------------------------------ score


def _harmonic(n: int) -> float:
    if n < 100:
        return math.fsum(1.0 / r for r in range(1, n + 1))
    return math.log(n) + 0.5772156649015329 + 1 / (2 * n) - 1 / (12 * n ** 2) + 1 / (120 * n ** 4)


def _expected_rr(o: int, p: int) -> Fraction | float:
    """E[1/rank] under uniformly random tie-breaking over ranks o..p (exact for small tie blocks)."""
    if p - o + 1 <= _EXACT_TIE_BLOCK:
        return sum((Fraction(1, r) for r in range(o, p + 1)), Fraction(0)) / (p - o + 1)
    if p < 100:
        return math.fsum(1.0 / r for r in range(o, p + 1)) / (p - o + 1)
    return (_harmonic(p) - _harmonic(o - 1)) / (p - o + 1)


def _measures(o: int, p: int, rank: str, model_rank: int | None, hits: tuple[int, ...]) -> dict[str, Any]:
    """RR, Hits@k and the rank of one query under a rank convention."""
    if rank == "tie_exact":
        n = p - o + 1
        return {"rr": _expected_rr(o, p), "rank": Fraction(o + p, 2),
                "hits": {k: Fraction(max(0, min(k, p) - o + 1), n) for k in hits}}
    if rank == "model" and model_rank is not None:
        r: Fraction = Fraction(model_rank)
    elif rank in ("pessimistic", "model"):
        r = Fraction(p)
    elif rank == "optimistic":
        r = Fraction(o)
    else:
        r = Fraction(o + p, 2)
    return {"rr": 1 / r, "rank": r, "hits": {k: Fraction(int(r <= k)) for k in hits}}


def _avg(values: Sequence[Any]) -> Any:
    """The mean: exact when every value is exact, else the correctly rounded float mean."""
    if not values:
        return None
    if all(isinstance(v, (int, Fraction)) for v in values):
        return sum(values, Fraction(0)) / len(values)
    return math.fsum(float(v) for v in values) / len(values)


def _flt(x: Any) -> Any:
    return None if x is None else float(x)


def _summary(rows: list[dict[str, Any]], hits: tuple[int, ...]) -> dict[str, Any]:
    """Per-task means of the measures of ``rows``."""
    ranked = [r for r in rows if r["rank"] is not None]
    out = {"n_queries": len(rows), "mrr": _flt(_avg([r["rr"] for r in rows])),
           "mr": _flt(_avg([r["rank"] for r in ranked]))}
    for k in hits:
        out[f"hits@{k}"] = _flt(_avg([r["hits"][k] for r in rows]))
    return out


def _grouped(rows: list[dict[str, Any]], key: str, hits: tuple[int, ...]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(str(r[key]), []).append(r)
    return {g: _summary(groups[g], hits) for g in sorted(groups)}


def _fact_means(rows: list[dict[str, Any]], hits: tuple[int, ...]) -> dict[str, dict[str, Any]]:
    by_fact: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_fact.setdefault(r["fact_id"], []).append(r)
    out = {}
    for f, rs in by_fact.items():
        ranked = [r["rank"] for r in rs if r["rank"] is not None]
        out[f] = {"rr": _avg([r["rr"] for r in rs]), "rank": _avg(ranked) if ranked else None,
                  "hits": {k: _avg([r["hits"][k] for r in rs]) for k in hits},
                  "arity": arity_bin(rs[0]["arity"]), "model_arity": arity_bin(rs[0]["model_arity"])}
    return out


def _mean_of(facts: Iterable[dict[str, Any]], hits: tuple[int, ...]) -> dict[str, Any]:
    fs = list(facts)
    ranked = [f["rank"] for f in fs if f["rank"] is not None]
    out = {"n_facts": len(fs), "mrr": _avg([f["rr"] for f in fs]), "mr": _avg(ranked) if ranked else None}
    for k in hits:
        out[f"hits@{k}"] = _avg([f["hits"][k] for f in fs])
    return out


def _averages(rows: list[dict[str, Any]], hits: tuple[int, ...]) -> dict[str, Any]:
    """Per task, per fact and macro over the arity bins (of the per-fact means), on both arities."""
    facts = _fact_means(rows, hits)
    out: dict[str, Any] = {"per_task": _summary(rows, hits), "per_fact": _mean_of(facts.values(), hits)}
    for kind in ("arity", "model_arity"):
        per_bin = {b: _mean_of([f for f in facts.values() if f[kind] == b], hits)
                   for b in BINS if any(f[kind] == b for f in facts.values())}
        macro = {"n_bins": len(per_bin)}
        for m in ["mrr", "mr"] + [f"hits@{k}" for k in hits]:
            vals = [v[m] for v in per_bin.values() if v[m] is not None]
            macro[m] = _avg(vals)
        out[f"macro_{kind}"] = macro
    return out


def _calibration(rows: list[dict[str, Any]], config: CompletionConfig, *, minimum: int) -> dict[str, Any]:
    cal = [r for r in rows if r.get("top1_correct") is not None]
    n = len(cal)
    if n < minimum or n == 0:
        return {"n": n, "suppressed": n > 0}
    conf = [r["top1_prob"] for r in cal]
    corr = [int(r["top1_correct"]) for r in cal]
    m = config.ece_bins
    return {"n": n, "suppressed": False, "bins": m,
            "accuracy": float(Fraction(sum(corr), n)),
            "mean_confidence": _flt(sum((frac(c) for c in conf), Fraction(0)) / n),
            "brier": _flt(calibration.brier(conf, corr)),
            "ece": {b: float(calibration.ece(conf, corr, m=m, binning=b)) for b in calibration.BINNINGS},
            "reliability": {b: calibration.reliability(conf, corr, m=m, binning=b) for b in calibration.BINNINGS}}


def _rows(queries: list[dict[str, Any]], outputs: Mapping[str, dict[str, Any]], rank: str,
          config: CompletionConfig, index: FilterIndex | None, filter_mode: str) -> list[dict[str, Any]]:
    rows = []
    for q in queries:
        rec = outputs.get(q["qid"])
        row: dict[str, Any] = {"qid": q["qid"], "fact_id": q["fact_id"], "relation": q["relation"],
                               "role": q["target"]["role"], "slot": q["target"]["slot"], "arity": q["arity"],
                               "model_arity": q["model_arity"]}
        if rec is None:
            row.update(missing=True, rr=Fraction(0), rank=None, hits={k: Fraction(0) for k in config.hits})
            rows.append(row)
            continue
        o = 1 + rec["n_greater"]
        p = o + rec["n_equal"]
        size = rec["n_candidates"] - rec["n_filtered_out"]
        if p > size:
            raise ValidationError.from_findings([make_finding(
                "KHG-C010", f"/{q['qid']}", f"n_greater + n_equal + 1 = {p} exceeds the {size} unfiltered candidates")])
        row.update(missing=False, o=o, p=p, size=size, model_rank=rec.get("model_rank"),
                   **_measures(o, p, rank, rec.get("model_rank"), config.hits))
        if "top1" in rec:
            got = identity_key(rec["top1"]["value"])
            correct = got == identity_key(q["target"]["value"])
            if not correct and index is not None:
                cid = candidate_id(rec["top1"]["value"])
                correct = cid is not None and cid in index.known_answers(q, filter_mode)
            row["top1_correct"] = correct
            row["top1_prob"] = rec["top1"]["prob"]
        rows.append(row)
    return rows


def _outputs_by_mode(outputs: Any, headline: str) -> dict[str, list[dict[str, Any]]]:
    if isinstance(outputs, Mapping):
        unknown = sorted(set(outputs) - set(FILTERS))
        if unknown:
            raise ValueError(f"outputs by filter take the keys {FILTERS}, not {unknown}")
        if headline not in outputs:
            raise ValueError(f"outputs by filter must include the headline filter {headline!r}")
        return {m: _inputs.check_outputs(outputs[m], kind="completion-rank") for m in FILTERS if m in outputs}
    return {headline: _inputs.check_outputs(outputs, kind="completion-rank")}


def _by_qid(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for n, r in enumerate(records):
        if r["qid"] in out:
            raise ValidationError.from_findings([make_finding("KHG-C010", f"/lines/{n}/qid",
                                                              f"two completion-rank records for {r['qid']!r}")])
        out[r["qid"]] = r
    return out


def _position(row: Mapping[str, Any], schema: Schema) -> str | None:
    """``subject`` or ``object`` when the query's target role is the relation's ``primary`` subject or object."""
    primary = schema.relation(row["relation"]).get("primary") or {}
    return "subject" if row["role"] == primary.get("subject") else \
        "object" if row["role"] == primary.get("object") else None


def score(queries: Iterable[Mapping[str, Any]], outputs: Any, *, config: CompletionConfig = CompletionConfig(),
          schema: Any = None, index: FilterIndex | None = None) -> dict[str, Any]:
    """Score completion (DESIGN §9.2, §9.3). ``queries``: ``c4-completion-query`` items (a whole C4 file may be
    passed). ``outputs``: ``completion-rank`` records computed with the headline filter, or ``{filter: records}``
    to report the three filters side by side. ``schema`` is needed by the ``stare`` preset (its ``primary``
    positions); ``index`` makes top-1 correctness accept any known answer (C-M7), else the target alone.
    Returns ``{scorer, config, contracts, aggregate, breakdowns, items, bootstrap}`` with ``items`` keyed by qid."""
    if not isinstance(config, CompletionConfig):
        raise TypeError("config must be a CompletionConfig")
    headline, rank = config.effective()
    qs, headers = _inputs.check_items(queries, kinds=("c4-completion-query",))
    seen: set[str] = set()
    for n, q in enumerate(qs):
        if q["qid"] in seen:
            raise ValidationError.from_findings([make_finding("KHG-I002", f"/queries/{n}/qid",
                                                              f"qid {q['qid']!r} appears twice")])
        seen.add(q["qid"])
    s = as_schema(schema) if schema is not None else None
    if config.preset == "stare" and s is None:
        raise ValueError("the stare preset needs schema= to find the primary subject and object")
    by_mode = {m: _by_qid(recs) for m, recs in _outputs_by_mode(outputs, headline).items()}
    rows_by_mode = {m: _rows(qs, recs, rank, config, index, m) for m, recs in by_mode.items()}
    if config.preset == "stare":
        for rs in rows_by_mode.values():
            for r in rs:
                r["position"] = _position(r, s)  # type: ignore[arg-type]
        rows_by_mode = {m: [r for r in rs if r["position"] is not None] for m, rs in rows_by_mode.items()}
    rows = rows_by_mode[headline]
    present = [r for r in rows if not r["missing"]]
    approximated = ["qualifier_order"] if config.preset == "stare" else []
    if rank == "model" and any(r["model_rank"] is None and r["p"] > r["o"] for r in present):
        approximated.append("sort_order_ties")
    if index is None and any(r.get("top1_correct") is not None for r in rows):
        approximated.append("top1_known_answers")
    aggregate: dict[str, Any] = {"n_queries": len(rows), "n_outputs": len(present),
                                 "n_missing": len(rows) - len(present),
                                 "n_unmatched_outputs": len(set(by_mode[headline]) - seen),
                                 "filter": headline, "rank": rank, **_averages(rows, config.hits)}
    if config.preset == "stare":
        positions = {pos: _summary([r for r in rows if r["position"] == pos], config.hits)
                     for pos in ("subject", "object")}
        aggregate["stare"] = {"positions": positions}
        for m in ["mrr", "mr"] + [f"hits@{k}" for k in config.hits]:
            vals = [v[m] for v in positions.values() if v[m] is not None]
            aggregate["stare"][m] = math.fsum(vals) / len(vals) if vals else None
    aggregate["headline"] = "stare" if config.preset == "stare" else "per_task" if config.preset else "macro_arity"
    aggregate["rank_audit"] = {f"{conv}_mrr": _flt(_avg([_measures(r["o"], r["p"], conv, r["model_rank"],
                                                                     config.hits)["rr"] for r in present]))
                               for conv in ("optimistic", "pessimistic", "realistic", "tie_exact")}
    aggregate["adjusted"] = _adjusted(present, config.hits)
    aggregate["calibration"] = _calibration(rows, config, minimum=1)
    aggregate["approximated"] = approximated
    breakdowns: dict[str, Any] = {
        "filters": {m: _averages(rows_by_mode[m], config.hits) if m in rows_by_mode else None for m in FILTERS},
        "by_arity": {k: _grouped([dict(r, bin=arity_bin(r[k])) for r in rows], "bin", config.hits)
                     for k in ("arity", "model_arity")},
        "by_role": _grouped(rows, "role", config.hits), "by_slot": _grouped(rows, "slot", config.hits),
        "by_relation": _grouped(rows, "relation", config.hits),
        "calibration_by_arity": {k: {b: _calibration([r for r in rows if arity_bin(r[k]) == b], config,
                                                     minimum=config.min_bin_queries)
                                     for b in BINS if any(arity_bin(r[k]) == b for r in rows)}
                                 for k in ("arity", "model_arity")}}
    items = {}
    for r in rows:
        item: dict[str, Any] = {"depends_on": [r["fact_id"]], "fact_id": r["fact_id"], "relation": r["relation"],
                                "role": r["role"], "missing": r["missing"], "rr": _flt(r["rr"]),
                                "rank": _flt(r["rank"]), **{f"hits@{k}": _flt(v) for k, v in r["hits"].items()}}
        if not r["missing"]:
            item.update(optimistic=r["o"], pessimistic=r["p"], n_unfiltered=r["size"])
            if "top1_correct" in r:
                item["top1_correct"] = r["top1_correct"]
        items[r["qid"]] = item
    boot = None
    if config.bootstrap.resamples and rows:
        boot = {**config.bootstrap.as_dict(), "unit": "query", "n_units": len(rows), "intervals": {
            "mrr": mean_interval([r["rr"] for r in rows], config.bootstrap),
            **{f"hits@{k}": mean_interval([r["hits"][k] for r in rows], config.bootstrap) for k in config.hits}}}
    qsets = [q["qset"] for q in qs] + [h["qset"] for h in headers]
    header_schema = headers[0]["schema"] if headers else None
    return report("completion", config, aggregate=aggregate, breakdowns=breakdowns, items=items, bootstrap=boot,
                  qsets=qsets, schema=s if s is not None else header_schema,
                  effective={"filter": headline, "rank": rank})


def _adjusted(rows: list[dict[str, Any]], hits: tuple[int, ...]) -> dict[str, Any]:
    """C-M6: adjusted Hits@k = (H − E[H])/(1 − E[H]) with E[H] = mean min(k/|C'|, 1), and AMRI =
    (MR − E[MR])/(1 − E[MR]) with E[MR] = mean (|C'| + 1)/2 (None where undefined)."""
    if not rows:
        return {"amri": None, **{f"hits@{k}": None for k in hits}}
    out: dict[str, Any] = {}
    for k in hits:
        h = _avg([r["hits"][k] for r in rows])
        e = _avg([min(Fraction(k, r["size"]), Fraction(1)) for r in rows])
        out[f"hits@{k}"] = _flt((h - e) / (1 - e)) if e != 1 else None
    mr = _avg([r["rank"] for r in rows])
    emr = _avg([Fraction(r["size"] + 1, 2) for r in rows])
    out["amri"] = _flt((mr - emr) / (1 - emr)) if emr != 1 else None
    return out
