"""The extraction scorer (DESIGN §9.3; R05 §2.2): C3 queue items, or C1 hyperedges naming their document, scored
against the gold facts of ``c4-extraction-doc`` items.

Predictions and gold are deduplicated by ``content_key`` per document and run (the number removed is reported).
A run is ``(run_id, order_id)``; every run is scored against every gold document. The metrics:

- **E-M1 strict** P/R/F1: 1:1 fact matches, same relation and a perfect matching of the bindings (role, position,
  value under the literal rule).
- **E-M2 core**: the same on the distinct cores, the core-slot bindings (``core_roles="slot"``, which is
  ``core_key`` equality under ``literal_match="exact"``) or the declared key roles (``"key"``).
- **E-M3 alignment**: one 1:1 alignment per document within a relation, on values, then bindings: the largest Σν,
  then the largest Σβ, with ν the shared values (role ignored) and β the shared bindings (the pair weight
  w = M·ν + β, with M above any alignment's Σβ); the Hungarian solver breaks the remaining ties by lexicographic fact
  ids. **E-M4 Arg-I** = Σν and **E-M5 Arg-C** = Σβ over the alignment, against all predicted and all gold bindings.
  **E-M6 role accuracy** = ΣArg-C/ΣArg-I.
- **E-M7 pooled** bindings (relation, role, position, value) per document and the grouping gap F1(pooled) − F1(Arg-C);
  **E-M8 pairwise** role-typed binding pairs; **E-M9 participant sets** (value multisets, relation and roles
  ignored); **E-M10** the arity profile; **E-M11 Ign** (with ``seen`` core keys).

Averages: micro over (run, document) units (the headline), macro over relations, and macro over the arity bins,
with recall binned by gold arity and precision by predicted arity, on ``arity`` and on ``model_arity``. The presets
``hyperred_quintuplet`` and ``text2nkg`` add their own counting unit, with nested-loop counting and exact literals.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Iterable, Literal, Mapping

from ..errors import ValidationError, make_finding
from ..record import arity_bin
from . import _inputs, hungarian
from ._common import as_schema, count_matching, fnum, mean, prf, prf_split, report, sort_key
from ._facts import Binding, Fact, Matcher, entity_index, item_entities, prepare
from .bootstrap import Bootstrap, interval

__all__ = ["ExtractionConfig", "PRESETS", "score"]

PRESETS = ("hyperred_quintuplet", "text2nkg")
CORE_ROLES = ("slot", "key")
ARITIES = ("arity", "model_arity")
BINS = ("0-1", "2", "3", "4", "5+")


@dataclass(frozen=True)
class ExtractionConfig:
    """The extraction scorer's settings (DESIGN §9.2)."""

    preset: Literal["hyperred_quintuplet", "text2nkg"] | None = None
    literal_match: Literal["truncate_to_gold", "exact"] = "truncate_to_gold"
    calendar: Literal["strict", "as_written"] = "strict"   # "as_written": read a predicted date in the gold's calendar
    core_roles: Literal["slot", "key"] = "slot"     # E-M2: core_key equality; "key": the declared key roles
    seen: frozenset[str] = frozenset()               # core keys for the Ign variant (E-M11)
    bootstrap: Bootstrap = Bootstrap()

    def __post_init__(self) -> None:
        if self.preset is not None and self.preset not in PRESETS:
            raise ValueError(f"preset must be one of {PRESETS} or None, not {self.preset!r}")
        if self.core_roles not in CORE_ROLES:
            raise ValueError(f"core_roles must be one of {CORE_ROLES}, not {self.core_roles!r}")
        Matcher(self.literal_match, self.calendar)  # checks both
        if isinstance(self.seen, str) or not all(isinstance(k, str) for k in self.seen):
            raise ValueError("seen is a set of core keys (strings)")
        object.__setattr__(self, "seen", frozenset(self.seen))
        if not isinstance(self.bootstrap, Bootstrap):
            raise ValueError("bootstrap must be a Bootstrap")


# ------------------------------------------------------------------------------------------------ one document


@dataclass
class _Counts:
    """Summable counts of one or more (run, document) units."""

    strict: list[int] = field(default_factory=lambda: [0, 0, 0])       # tp, n_pred, n_gold
    core: list[int] = field(default_factory=lambda: [0, 0, 0])
    arg: list[int] = field(default_factory=lambda: [0, 0, 0, 0])       # tp_i, tp_c, bindings pred, bindings gold
    pooled: list[int] = field(default_factory=lambda: [0, 0, 0])
    pairwise: list[int] = field(default_factory=lambda: [0, 0, 0])
    participant: list[int] = field(default_factory=lambda: [0, 0, 0])
    relation: dict[str, list[int]] = field(default_factory=dict)      # strict tp,np,ng; arg tp_i,tp_c,bp,bg
    bins: dict[str, dict[str, list[int]]] = field(default_factory=lambda: {a: {} for a in ARITIES})
    pairs: Counter = field(default_factory=Counter)                     # (pred arity, gold arity) of aligned pairs

    def add(self, o: _Counts) -> None:
        for name in ("strict", "core", "arg", "pooled", "pairwise", "participant"):
            mine, other = getattr(self, name), getattr(o, name)
            for i, v in enumerate(other):
                mine[i] += v
        for rel, v in o.relation.items():
            _add(self.relation.setdefault(rel, [0] * 7), v)
        for a in ARITIES:
            for b, v in o.bins[a].items():
                _add(self.bins[a].setdefault(b, [0] * 8), v)
        self.pairs.update(o.pairs)


def _add(acc: list[int], v: list[int]) -> None:
    for i, x in enumerate(v):
        acc[i] += x


def _fact_match(p: Fact, g: Fact, m: Matcher) -> bool:
    if p.relation != g.relation or len(p.bindings) != len(g.bindings):
        return False
    if m.plain(p, g):
        return p.content_key == g.content_key
    if sorted((b.role, b.position) for b in p.bindings) != sorted((b.role, b.position) for b in g.bindings):
        return False
    return count_matching(p.bindings, g.bindings, m.bindings) == len(g.bindings)


def _key_of(roles: bool) -> Any:
    return (lambda b: b.triple) if roles else (lambda b: (b.kind, b.ident))


def _set_match(p: tuple[Binding, ...], g: tuple[Binding, ...], m: Matcher, *, roles: bool, plain: bool) -> bool:
    if len(p) != len(g):
        return False
    if plain:
        key = _key_of(roles)
        return sorted(map(key, p)) == sorted(map(key, g))
    return count_matching(p, g, m.bindings if roles else m.values) == len(g)


def _strict_pairs(preds: list[Fact], golds: list[Fact], m: Matcher) -> list[tuple[int, int]]:
    if m.plain(*preds, *golds):  # a match is content_key equality, and both sides are deduplicated by it
        by_key = {g.content_key: j for j, g in enumerate(golds)}
        return [(i, by_key[p.content_key]) for i, p in enumerate(preds) if p.content_key in by_key]
    w = [[1 if _fact_match(p, g, m) else 0 for g in golds] for p in preds]
    return hungarian.solve(w) if preds and golds else []


def _distinct(items: list[tuple[Any, Any]]) -> list[Any]:
    seen: dict[Any, Any] = {}
    for k, v in items:
        seen.setdefault(k, v)
    return [seen[k] for k in sorted(seen, key=repr)]


def _alignment(preds: list[Fact], golds: list[Fact], m: Matcher) -> list[tuple[int, int, int, int]]:
    """The E-M3 alignment: ``(pred index, gold index, ν, β)`` for each aligned pair.

    The weight of a pair is w = M·ν + β. M exceeds the Σβ of any alignment (β ≤ the bindings of either fact, so
    Σβ ≤ min(Σ|B_p|, Σ|B_g|)), which makes the maximum ΣW lexicographic over the document's totals: the largest Σν,
    then the largest Σβ, then the solver's id tie-break. R05's M = N + 1 orders one pair by ν, then β, but a sum of
    β over several pairs can outweigh a unit of ν, and a qid then decided between (Σν, Σβ) = (3, 3) and (4, 0)."""
    if not preds or not golds:
        return []
    big = 1 + min(sum(len(f.bindings) for f in preds), sum(len(f.bindings) for f in golds))
    nu: dict[tuple[int, int], int] = {}
    beta: dict[tuple[int, int], int] = {}
    w = []
    for i, p in enumerate(preds):
        row = []
        for j, g in enumerate(golds):
            if p.relation != g.relation:
                row.append(0)
                continue
            plain = m.plain(p, g)
            n = count_matching(p.bindings, g.bindings, m.values, key=_key_of(False) if plain else None)
            k = count_matching(p.bindings, g.bindings, m.bindings, key=_key_of(True) if plain else None)
            nu[i, j], beta[i, j] = n, k
            row.append(big * n + k)
        w.append(row)
    return [(i, j, nu[i, j], beta[i, j]) for i, j in hungarian.solve(w)]


def _pooled(facts: list[Fact]) -> list[tuple[str, Binding]]:
    return _distinct([((f.relation, b.triple), (f.relation, b)) for f in facts for b in f.bindings])


def _pairs(facts: list[Fact]) -> list[tuple[str, Binding, Binding]]:
    out = []
    for f in facts:
        bs = f.bindings
        for x in range(len(bs)):
            for y in range(x + 1, len(bs)):
                key = (f.relation, tuple(sorted((bs[x].triple, bs[y].triple))))
                out.append((key, (f.relation, bs[x], bs[y])))
    return _distinct(out)


def _pair_match(p: tuple[str, Binding, Binding], g: tuple[str, Binding, Binding], m: Matcher) -> bool:
    if p[0] != g[0]:
        return False
    return (m.bindings(p[1], g[1]) and m.bindings(p[2], g[2])) or (m.bindings(p[1], g[2]) and m.bindings(p[2], g[1]))


def _doc(preds: list[Fact], golds: list[Fact], m: Matcher, *, full: bool = True) -> tuple[_Counts, dict[str, Any]]:
    """Score one (run, document) unit; ``full=False`` computes E-M1 to E-M6 only (the Ign variant)."""
    c = _Counts()
    strict = _strict_pairs(preds, golds, m)
    c.strict = [len(strict), len(preds), len(golds)]
    plain = m.plain(*preds, *golds)
    pc = _distinct([(f.core_signature, (f.relation, f.core)) for f in preds])
    gc = _distinct([(f.core_signature, (f.relation, f.core)) for f in golds])
    core_tp = count_matching(pc, gc, lambda x, y: x[0] == y[0] and _set_match(x[1], y[1], m, roles=True, plain=plain),
                             key=(lambda x: (x[0], tuple(sorted(b.triple for b in x[1])))) if plain else None)
    c.core = [core_tp, len(pc), len(gc)]
    aligned = _alignment(preds, golds, m)
    nb_pred = sum(len(f.bindings) for f in preds)
    nb_gold = sum(len(f.bindings) for f in golds)
    c.arg = [sum(a[2] for a in aligned), sum(a[3] for a in aligned), nb_pred, nb_gold]
    matched_p = {i for i, _ in strict}
    matched_g = {j for _, j in strict}
    for rel in {f.relation for f in preds + golds}:
        row = [0] * 7
        row[0] = sum(1 for i, j in strict if golds[j].relation == rel)
        row[1] = sum(1 for f in preds if f.relation == rel)
        row[2] = sum(1 for f in golds if f.relation == rel)
        row[3] = sum(a[2] for a in aligned if golds[a[1]].relation == rel)
        row[4] = sum(a[3] for a in aligned if golds[a[1]].relation == rel)
        row[5] = sum(len(f.bindings) for f in preds if f.relation == rel)
        row[6] = sum(len(f.bindings) for f in golds if f.relation == rel)
        c.relation[rel] = row
    beta_p = {a[0]: a[3] for a in aligned}
    beta_g = {a[1]: a[3] for a in aligned}
    for kind in ARITIES:
        for i, f in enumerate(preds):  # precision side: predicted arity
            b = c.bins[kind].setdefault(arity_bin(getattr(f, kind)), [0] * 8)
            b[0] += i in matched_p
            b[1] += 1
            b[4] += beta_p.get(i, 0)
            b[5] += len(f.bindings)
        for j, f in enumerate(golds):  # recall side: gold arity
            b = c.bins[kind].setdefault(arity_bin(getattr(f, kind)), [0] * 8)
            b[2] += j in matched_g
            b[3] += 1
            b[6] += beta_g.get(j, 0)
            b[7] += len(f.bindings)
    for i, j, _, _ in aligned:
        c.pairs[preds[i].arity, golds[j].arity] += 1
    detail = {"matched": [[preds[i].id, golds[j].id] for i, j in sorted(strict, key=lambda x: preds[x[0]].id)],
              "aligned": [{"pred": preds[i].id, "gold": golds[j].id, "nu": n, "beta": k}
                          for i, j, n, k in sorted(aligned, key=lambda x: preds[x[0]].id)],
              "missed": sorted(golds[j].id for j in range(len(golds)) if j not in matched_g),
              "spurious": sorted(preds[i].id for i in range(len(preds)) if i not in matched_p)}
    if not full:
        return c, detail
    pp, pg = _pooled(preds), _pooled(golds)
    c.pooled = [count_matching(pp, pg, lambda x, y: x[0] == y[0] and m.bindings(x[1], y[1]),
                               key=(lambda x: (x[0], x[1].triple)) if plain else None), len(pp), len(pg)]
    qp, qg = _pairs(preds), _pairs(golds)
    c.pairwise = [count_matching(qp, qg, lambda x, y: _pair_match(x, y, m),
                                 key=(lambda x: (x[0], tuple(sorted((x[1].triple, x[2].triple)))))
                                 if plain else None), len(qp), len(qg)]
    vp = _distinct([(tuple(sorted((b.kind, b.ident) for b in f.bindings)), f.bindings) for f in preds])
    vg = _distinct([(tuple(sorted((b.kind, b.ident) for b in f.bindings)), f.bindings) for f in golds])
    c.participant = [count_matching(vp, vg, lambda x, y: _set_match(x, y, m, roles=False, plain=plain),
                                    key=(lambda x: tuple(sorted((b.kind, b.ident) for b in x)))
                                    if plain else None), len(vp), len(vg)]
    return c, detail


# ------------------------------------------------------------------------------------------------ presets


def _head(f: Fact) -> tuple[tuple[Any, ...], list[Binding]] | None:
    if f.primary is None:
        return None
    s = [b for b in f.bindings if b.role == f.primary[0]]
    o = [b for b in f.bindings if b.role == f.primary[1]]
    if len(s) != 1 or len(o) != 1:
        return None
    rest = [b for b in f.bindings if b is not s[0] and b is not o[0]]
    return (f.relation, s[0].ident, o[0].ident), rest


def _preset_units(facts: list[Fact], preset: str, *, compact: bool) -> tuple[list[Any], int]:
    """The preset's scoring units of a list of facts (duplicates kept) and the number of unmapped facts."""
    units: list[Any] = []
    merged: dict[tuple[Any, ...], set[Any]] = {}
    order: list[tuple[Any, ...]] = []
    unmapped = 0
    for f in facts:
        h = _head(f)
        if h is None:
            unmapped += 1
            continue
        head, rest = h
        if preset == "hyperred_quintuplet":
            units += [head + b.triple for b in rest] or [head + (None, None, None)]
        elif compact:  # text2nkg: predicted quintuplets sharing (relation, subject, object) merge into one fact
            if head not in merged:
                merged[head] = set()
                order.append(head)
            merged[head] |= {b.triple for b in rest}
        else:
            units.append(head + (frozenset(b.triple for b in rest),))
    units += [head + (frozenset(merged[head]),) for head in order]
    return units, unmapped


def _nested_loop(pred: list[Any], gold: list[Any]) -> int:
    """HyperRED's and Text2NKG's counting: every equal (prediction, gold) pair counts."""
    cg = Counter(gold)
    return sum(cg[u] for u in pred)


# ------------------------------------------------------------------------------------------------ score


def _prf_block(t: list[int]) -> dict[str, Any]:
    return prf(t[0], t[1], t[2])


def _arg(counts: _Counts) -> dict[str, Any]:
    tp_i, tp_c, bp, bg = counts.arg
    return {"arg_i": prf(tp_i, bp, bg), "arg_c": prf(tp_c, bp, bg),
            "role_accuracy": float(Fraction(tp_c, tp_i)) if tp_i else None}


def _macro(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ps = [r["p"] for r in rows if r["n_pred"]]
    rs = [r["r"] for r in rows if r["n_gold"]]
    fs = [r["f1"] for r in rows]
    return {"p": fnum(mean(ps)), "r": fnum(mean(rs)), "f1": fnum(mean(fs)), "n": len(rows)}


def _bin_rows(bins: Mapping[str, list[int]]) -> dict[str, dict[str, Any]]:
    out = {}
    for b in (x for x in BINS if x in bins):
        v = bins[b]
        s = prf_split(v[0], v[1], v[2], v[3])
        a = prf_split(v[4], v[5], v[6], v[7])
        out[b] = {"strict": {"p": s["p"], "r": s["r"], "f1": s["f1"], "n_pred": v[1], "n_gold": v[3],
                             "flag": s["flag"]},
                  "arg_c": {"p": a["p"], "r": a["r"], "f1": a["f1"], "n_pred": v[5], "n_gold": v[7],
                            "flag": a["flag"]}}
    return out


def _aggregate(c: _Counts) -> dict[str, Any]:
    arg = _arg(c)
    pooled = prf(*c.pooled)
    agg = {"strict": _prf_block(c.strict), "core": _prf_block(c.core), **arg, "pooled": pooled,
           "grouping_gap_f1": pooled["f1"] - arg["arg_c"]["f1"], "pairwise": prf(*c.pairwise),
           "participant_set": prf(*c.participant)}
    rel_rows = {rel: {"strict": prf_split(v[0], v[1], v[0], v[2]) | {"n_pred": v[1], "n_gold": v[2]},
                      "arg_c": prf_split(v[4], v[5], v[4], v[6]) | {"n_pred": v[5], "n_gold": v[6]}}
                for rel, v in c.relation.items()}
    agg["macro_relation"] = {m: _macro([rel_rows[r][m] for r in sorted(rel_rows)]) for m in ("strict", "arg_c")}
    agg["macro_arity"] = {}
    for kind in ARITIES:
        rows = _bin_rows(c.bins[kind])
        agg["macro_arity"][kind] = {m: _macro([rows[b][m] for b in rows]) for m in ("strict", "arg_c")}
    return agg


def _breakdowns(c: _Counts) -> dict[str, Any]:
    by_rel = {}
    for rel in sorted(c.relation):
        v = c.relation[rel]
        tp_i, tp_c = v[3], v[4]
        by_rel[rel] = {"strict": prf(v[0], v[1], v[2]), "arg_i": prf(tp_i, v[5], v[6]),
                       "arg_c": prf(tp_c, v[5], v[6]), "role_accuracy": float(Fraction(tp_c, tp_i)) if tp_i else None}
    return {"by_relation": by_rel, "by_arity": {kind: _bin_rows(c.bins[kind]) for kind in ARITIES},
            "aligned_arity_pairs": [{"pred_arity": pa, "gold_arity": ga, "n": n}
                                    for (pa, ga), n in sorted(c.pairs.items())]}


def _dispersion(values: list[float | None]) -> dict[str, Any] | None:
    xs = [v for v in values if v is not None]
    if len(xs) < 2:
        return None
    mu = math.fsum(xs) / len(xs)
    sd = math.sqrt(math.fsum((x - mu) ** 2 for x in xs) / (len(xs) - 1))
    return {"mean": mu, "sd": sd, "min": min(xs), "max": max(xs), "n_runs": len(xs)}


def _dedup(facts: list[Fact]) -> tuple[list[Fact], int]:
    out: dict[str, Fact] = {}
    for f in sorted(facts, key=lambda x: x.id):
        out.setdefault(f.content_key, f)
    kept = sorted(out.values(), key=lambda x: x.id)
    return kept, len(facts) - len(kept)


def _read_gold(docs: list[dict[str, Any]], schema: Any, entities: Mapping[str, Mapping[str, Any]],
               config: ExtractionConfig) -> tuple[dict[str, list[Fact]], dict[str, list[Fact]], int]:
    """Gold facts by document: deduplicated, as written (for the presets), and the number of duplicates."""
    kept: dict[str, list[Fact]] = {}
    raw: dict[str, list[Fact]] = {}
    removed = 0
    for n, d in enumerate(docs):
        if d["doc_id"] in kept:
            raise ValidationError.from_findings([make_finding("KHG-I002", f"/docs/{n}/doc_id",
                                                              f"doc_id {d['doc_id']!r} appears twice")])
        facts = []
        for k, r in enumerate(d["gold"]):
            try:
                facts.append(prepare(r, schema, entities, core_roles=config.core_roles))
            except ValidationError as e:
                raise _inputs.embedded_error(e, f"/docs/{n}/gold/{k}") from None
        raw[d["doc_id"]] = facts
        kept[d["doc_id"]], dup = _dedup(facts)
        removed += dup
    return kept, raw, removed


def _preset_block(preset: str, counts: list[int]) -> dict[str, Any]:
    tp, n_p, n_g, un_p, un_g = counts
    f = prf_split(tp, n_p, tp, n_g)
    return {"name": preset, "unit": "quintuplet" if preset == "hyperred_quintuplet" else "fact",
            "counting": "nested_loop", "literal_match": "exact", "tp": tp, "n_pred": n_p, "n_gold": n_g,
            "p": f["p"], "r": f["r"], "f1": f["f1"], "flag": f["flag"], "n_unmapped_pred": un_p,
            "n_unmapped_gold": un_g,
            "approximated": ["entity_bounds"] if preset == "hyperred_quintuplet" else ["serialisation_order"]}


def _by_run(runs: list[tuple[Any, Any]], per_run: Mapping[tuple[Any, Any], _Counts]) -> dict[str, Any]:
    rows = []
    for run in runs:
        rc = per_run[run]
        arg = _arg(rc)
        rows.append({"run_id": run[0], "order_id": run[1], "strict": _prf_block(rc.strict),
                     "core": _prf_block(rc.core), "arg_c": arg["arg_c"], "role_accuracy": arg["role_accuracy"]})
    return {"by_run": rows, "run_dispersion": {
        "strict_f1": _dispersion([r["strict"]["f1"] for r in rows]),
        "arg_c_f1": _dispersion([r["arg_c"]["f1"] for r in rows]),
        "role_accuracy": _dispersion([r["role_accuracy"] for r in rows])}}


def score(gold: Iterable[Mapping[str, Any]], predictions: Iterable[Mapping[str, Any]], *, schema: Any,
          config: ExtractionConfig = ExtractionConfig()) -> dict[str, Any]:
    """Score extraction output against gold (DESIGN §9.2, §9.3).

    ``gold``: ``c4-extraction-doc`` items (a whole C4 file may be passed; other kinds are skipped). ``predictions``:
    C3 queue items, or C1 hyperedges whose evidence names their document. Returns ``{scorer, config, contracts,
    aggregate, breakdowns, items, bootstrap}``, with ``items`` keyed by doc id. Raises ``ValidationError`` on a
    malformed input (layer I for gold, embedded C1 findings under I003)."""
    if not isinstance(config, ExtractionConfig):
        raise TypeError("config must be an ExtractionConfig")
    s = as_schema(schema)
    m = Matcher(config.literal_match, config.calendar)
    docs, headers = _inputs.check_items(gold, kinds=("c4-extraction-doc",))
    preds = _inputs.predictions(predictions)
    entities = entity_index([e for d in docs for e in d.get("entities", [])])  # the gold's records only
    gold_by_doc, raw_gold, n_gold_dup = _read_gold(docs, s, entities, config)
    runs = sorted({(p.run_id, p.order_id) for p in preds}, key=lambda r: (sort_key(r[0]), sort_key(r[1])))
    runs = runs or [(None, None)]
    by_unit: dict[tuple[Any, Any, str], list[Fact]] = {}
    unscored: Counter = Counter()
    unreadable: list[dict[str, Any]] = []
    for p in preds:
        if p.doc_id not in gold_by_doc:
            unscored[p.doc_id] += 1
            continue
        try:
            fact = prepare(p.record, s, item_entities(p, entities), fid=p.pid, core_roles=config.core_roles)
        except ValidationError as e:  # located at the prediction's line
            unreadable += _inputs.located(e, p.path)
            continue
        by_unit.setdefault((p.run_id, p.order_id, p.doc_id), []).append(fact)
    if unreadable:
        raise ValidationError.from_findings(unreadable)
    total, ign_total = _Counts(), _Counts()
    per_doc: dict[str, list[Any]] = {d: [] for d in gold_by_doc}
    per_run: dict[tuple[Any, Any], _Counts] = {r: _Counts() for r in runs}
    unit_counts: dict[str, list[_Counts]] = {d: [] for d in gold_by_doc}
    n_dup = 0
    preset_counts = [0, 0, 0, 0, 0]  # tp, n_pred, n_gold, unmapped pred, unmapped gold
    ign_removed = [0, 0]
    for run in runs:
        for doc_id in sorted(gold_by_doc):
            raw = by_unit.get((run[0], run[1], doc_id), [])
            preds_d, dup = _dedup(raw)
            n_dup += dup
            golds_d = gold_by_doc[doc_id]
            c, detail = _doc(preds_d, golds_d, m)
            total.add(c)
            per_run[run].add(c)
            unit_counts[doc_id].append(c)
            per_doc[doc_id].append({"run_id": run[0], "order_id": run[1], "n_pred": len(preds_d),
                                    "n_duplicates_removed": dup, "strict_tp": c.strict[0], "arg_i_tp": c.arg[0],
                                    "arg_c_tp": c.arg[1], **detail})
            if config.seen:
                gs = [g for g in golds_d if g.core_key not in config.seen]
                ps = [p for p in preds_d if p.core_key not in config.seen]
                ign_removed[0] += len(golds_d) - len(gs)
                ign_removed[1] += len(preds_d) - len(ps)
                ign_total.add(_doc(ps, gs, m, full=False)[0])
            if config.preset:
                pu, pun = _preset_units(raw, config.preset, compact=True)
                gu, gun = _preset_units(raw_gold[doc_id], config.preset, compact=False)
                for i, v in enumerate((_nested_loop(pu, gu), len(pu), len(gu), pun, gun)):
                    preset_counts[i] += v
    aggregate: dict[str, Any] = {
        "n_docs": len(gold_by_doc), "n_runs": len(runs), "n_gold": sum(len(g) for g in gold_by_doc.values()),
        "n_pred": total.strict[1], "n_duplicates_removed": n_dup, "n_gold_duplicates_removed": n_gold_dup,
        "n_pred_unscored": sum(unscored.values()), **_aggregate(total)}
    if config.seen:
        aggregate["ign"] = {"n_gold_removed": ign_removed[0], "n_pred_removed": ign_removed[1],
                            "strict": _prf_block(ign_total.strict), "core": _prf_block(ign_total.core),
                            **_arg(ign_total)}
    if config.preset:
        aggregate["preset"] = _preset_block(config.preset, preset_counts)
    breakdowns = {**_breakdowns(total), **_by_run(runs, per_run), "unscored_docs": sorted(unscored)}
    boot = _bootstrap([unit_counts[d] for d in sorted(unit_counts)], config.bootstrap)
    items = {doc_id: {"depends_on": sorted(g.id for g in gold_by_doc[doc_id]), "n_gold": len(gold_by_doc[doc_id]),
                      "runs": per_doc[doc_id]} for doc_id in sorted(gold_by_doc)}
    qsets = [d["qset"] for d in docs] + [h["qset"] for h in headers]
    return report("extraction", config, aggregate=aggregate, breakdowns=breakdowns, items=items, bootstrap=boot,
                  qsets=qsets, schema=s)


def _bootstrap(units: list[list[_Counts]], config: Bootstrap) -> dict[str, Any] | None:
    """Percentile intervals over gold documents (each with its counts in every run)."""
    if config.resamples == 0 or not units:
        return None
    rows = []
    for cs in units:
        v = [0] * 7
        for c in cs:
            _add(v, [c.strict[0], c.strict[1], c.strict[2], c.arg[0], c.arg[1], c.arg[2], c.arg[3]])
        rows.append(v)

    def summed(sample: list[list[int]]) -> list[int]:
        acc = [0] * 7
        for v in sample:
            _add(acc, v)
        return acc

    def strict_f1(sample: list[list[int]]) -> Fraction:
        a = summed(sample)
        return prf_split(a[0], a[1], a[0], a[2])["f1"]

    def arg_c_f1(sample: list[list[int]]) -> Fraction:
        a = summed(sample)
        return prf_split(a[4], a[5], a[4], a[6])["f1"]

    def role_accuracy(sample: list[list[int]]) -> Fraction | None:
        a = summed(sample)
        return Fraction(a[4], a[3]) if a[3] else None

    return {**config.as_dict(), "unit": "doc", "n_units": len(rows),
            "intervals": {"strict.f1": interval(rows, strict_f1, config),
                          "arg_c.f1": interval(rows, arg_c_f1, config),
                          "role_accuracy": interval(rows, role_accuracy, config)}}
