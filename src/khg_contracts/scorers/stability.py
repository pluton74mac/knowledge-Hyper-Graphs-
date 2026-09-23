"""The stability scorer (DESIGN §9.3; R05 §2.2.2): how much extraction output changes across runs and orders.

Each unit (a run ``(run_id, order_id)``, or with ``unit="run_id"`` all the orders of a run pooled) gives a set of
facts: ``(doc_id, key)`` for each item, on ``content_key`` and on ``core_key``. Everything is computed on each key:

- **S-M1** the pairwise Jaccard J(i, j) = |S_i ∩ S_j| / |S_i ∪ S_j| (1 when both are empty, counted in
  ``n_empty_pairs``) and its mean over the C(K, 2) pairs;
- **S-M2** the core ratio |∩ S_i| / |∪ S_i| (1 when every set is empty);
- **S-M3** the support histogram (how many facts s units contain) and the unstable fraction (0 < s < K);
- **S-M4** the mean churn δ = s(K − s)/C(K, 2) over the facts;
- **S-M5** with ``gold``: the shares of gold facts found by all, some or none of the units (``stable``, ``unstable``,
  ``miss``), matching by the key;
- **S-M7** the order effect on (run_id, order_id) units: J_within over pairs with the same order_id, J_between over
  pairs with different ones, and Δ_order = J_within − J_between.
"""
from __future__ import annotations

import itertools
import math
from fractions import Fraction
from typing import Any, Iterable, Literal, Mapping

from ..errors import ValidationError
from . import _inputs
from ._common import as_schema, fnum, mean, report, sort_key
from ._facts import entity_index, prepare

__all__ = ["KEYS", "UNITS", "score"]

KEYS = ("content_key", "core_key")
UNITS = ("run", "run_id")
Element = tuple[str, str]


def _jaccard(a: set[Element], b: set[Element]) -> Fraction:
    return Fraction(1) if not a and not b else Fraction(len(a & b), len(a | b))


def _pairwise(sets: list[set[Element]]) -> dict[str, Any]:
    pairs = list(itertools.combinations(range(len(sets)), 2))
    js = [_jaccard(sets[i], sets[j]) for i, j in pairs]
    return {"pairwise_jaccard": [float(j) for j in js], "mean_pairwise_jaccard": fnum(mean(js)),
            "n_empty_pairs": sum(1 for i, j in pairs if not sets[i] and not sets[j])}


def _metrics(sets: list[set[Element]]) -> dict[str, Any]:
    k = len(sets)
    union: set[Element] = set().union(*sets) if sets else set()
    inter: set[Element] = set.intersection(*sets) if sets else set()
    support = {f: sum(f in s for s in sets) for f in union}
    hist: dict[int, int] = {}
    for s in support.values():
        hist[s] = hist.get(s, 0) + 1
    pairs = math.comb(k, 2)
    churn = [Fraction(s * (k - s), pairs) for s in support.values()] if pairs else []
    return {**_pairwise(sets), "n_facts": len(union),
            "core_ratio": float(Fraction(len(inter), len(union))) if union else 1.0,
            "support_histogram": {str(s): hist[s] for s in sorted(hist)},
            "unstable_fraction": float(Fraction(sum(1 for s in support.values() if 0 < s < k), len(union)))
            if union else 0.0,
            "mean_churn": fnum(mean(churn)) if churn else 0.0}


def _order_effect(units: list[tuple[Any, Any]], sets: list[set[Element]]) -> dict[str, Any]:
    within, between = [], []
    for i, j in itertools.combinations(range(len(units)), 2):
        (within if units[i][1] == units[j][1] else between).append(_jaccard(sets[i], sets[j]))
    jw, jb = mean(within), mean(between)
    return {"n_within_pairs": len(within), "n_between_pairs": len(between), "J_within": fnum(jw),
            "J_between": fnum(jb), "delta_order": fnum(jw - jb) if jw is not None and jb is not None else None}


def _partition(gold: dict[Element, str], sets: list[set[Element]]) -> dict[str, Any]:
    counts = {"stable": 0, "unstable": 0, "miss": 0}
    for g in gold:
        n = sum(g in s for s in sets)
        counts["stable" if n == len(sets) else "miss" if n == 0 else "unstable"] += 1
    total = len(gold)
    return {**{k: float(Fraction(v, total)) if total else None for k, v in counts.items()}, "n_gold": total}


def score(items: Iterable[Mapping[str, Any]], *, schema: Any, unit: Literal["run", "run_id"] = "run",
          keys: tuple[str, ...] = ("content_key", "core_key"), gold: Iterable[Mapping[str, Any]] | None = None
          ) -> dict[str, Any]:
    """Score run-to-run stability (DESIGN §9.2, §9.3). ``items``: C3 queue items (or C1 hyperedges naming their
    document, which form one unit). ``unit="run"`` is (run_id, order_id); ``"run_id"`` pools the orders of a run.
    ``gold``: optional ``c4-extraction-doc`` items for S-M5. Returns ``{scorer, config, contracts, aggregate,
    breakdowns, items, bootstrap}``; ``items`` is keyed by doc id and ``bootstrap`` is None."""
    if unit not in UNITS:
        raise ValueError(f"unit must be one of {UNITS}, not {unit!r}")
    keys = tuple(keys)
    if not keys or any(k not in KEYS for k in keys) or len(set(keys)) != len(keys):
        raise ValueError(f"keys is a non-empty subset of {KEYS}, not {keys!r}")
    s = as_schema(schema)
    preds = _inputs.predictions(items)
    docs, headers = _inputs.check_items(gold or [], kinds=("c4-extraction-doc",))
    entities = entity_index([e for p in preds for e in p.entities] + [e for d in docs for e in d.get("entities", [])])
    runs = sorted({(p.run_id, p.order_id) for p in preds}, key=lambda r: (sort_key(r[0]), sort_key(r[1])))
    elems: dict[tuple[Any, Any], dict[str, set[Element]]] = {r: {k: set() for k in keys} for r in runs}
    for p in preds:
        f = prepare(p.record, s, entities, fid=p.pid)
        for k in keys:
            elems[p.run_id, p.order_id][k].add((p.doc_id, getattr(f, k)))
    if unit == "run":
        units = [{"run_id": r[0], "order_id": r[1]} for r in runs]
        unit_sets = [elems[r] for r in runs]
    else:
        ids = sorted({r[0] for r in runs}, key=sort_key)
        units = [{"run_id": i} for i in ids]
        unit_sets = [{k: set().union(*(elems[r][k] for r in runs if r[0] == i)) for k in keys} for i in ids]
    gold_elems: dict[str, dict[Element, str]] = {k: {} for k in keys}
    depends: dict[str, list[str]] = {}
    for n, d in enumerate(docs):
        depends[d["doc_id"]] = sorted(r.get("id") for r in d["gold"])
        for i, r in enumerate(d["gold"]):
            try:
                f = prepare(r, s, entities)
            except ValidationError as e:
                raise _inputs.embedded_error(e, f"/docs/{n}/gold/{i}") from None
            for k in keys:
                gold_elems[k].setdefault((d["doc_id"], getattr(f, k)), f.id)
    aggregate: dict[str, Any] = {"unit": unit, "n_units": len(units), "units": units}
    for k in keys:
        sets = [u[k] for u in unit_sets]
        block = _metrics(sets)
        block["gold_partition"] = _partition(gold_elems[k], sets) if docs else None
        block["order_effect"] = _order_effect(runs, [elems[r][k] for r in runs])
        aggregate[k] = block
    doc_ids = sorted({p.doc_id for p in preds} | set(depends))
    per_doc: dict[str, Any] = {}
    for d in doc_ids:
        entry: dict[str, Any] = {"depends_on": depends.get(d, [])}
        for k in keys:
            sets = [{e for e in u[k] if e[0] == d} for u in unit_sets]
            entry[k] = _pairwise(sets) | {"n_facts": len(set().union(*sets)) if sets else 0}
        per_doc[d] = entry
    for k in keys:
        means = [v[k]["mean_pairwise_jaccard"] for v in per_doc.values()
                 if v[k]["n_facts"] and v[k]["mean_pairwise_jaccard"] is not None]
        aggregate[k]["per_document_mean_jaccard"] = math.fsum(means) / len(means) if means else None
    qsets = [d["qset"] for d in docs] + [h["qset"] for h in headers]
    config = {"unit": unit, "keys": list(keys)}
    by_unit = [{**u, "n_facts": {k: len(us[k]) for k in keys}} for u, us in zip(units, unit_sets, strict=True)]
    return report("stability", config, aggregate=aggregate, breakdowns={"n_items": len(preds), "by_unit": by_unit},
                  items=per_doc, bootstrap=None, qsets=qsets, schema=s)
