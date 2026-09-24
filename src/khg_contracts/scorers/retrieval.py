"""The retrieval scorer (DESIGN §9.2–§9.4; R05 §4.2): ``c4-retrieval-question`` items against
``retrieval-response`` records (``khg-c5-io``), with cost.

Ranking (units in ``rank`` order; hyperedges(L[:k]) is the union of the top-k units' ``hyperedge_ids``; the
support is a list of alternative sets S_i):

- ``hit@k`` (any support hyperedge in the top k), ``support_success@k`` (some S_i inside it; the headline with
  ``mrr@k``), ``support_recall@k`` (max_i |S_i ∩ top k| / |S_i|), ``mrr@k`` (1/rank of the first unit holding a
  support hyperedge, 0 beyond k), ``r_precision`` (max_i over the top |S_i| units), ``ndcg@k`` (binary relevance, a
  support hyperedge counts at its first unit; DCG = Σ rel_i / log2(i + 1), or the LongMemEval discount
  rel_1 + Σ_{i≥2} rel_i / log2 i; ideal over min(|S_i|, k); max over the sets);
- ``binding_coverage@k`` with ``facts``: max_i of the share of S_i's bindings, as (hyperedge, bid), that the top k
  units point at (``bids``; a ``hyperedge`` unit without ``bids`` covers all its bindings).

Answers: in ``single`` mode, EM on value identity (the first answer value), then SQuAD-normalised text EM and token
F1; in ``set`` mode, set P, R, F1 (when the gold has values, or no text) and EM. A missing response, an abstention or
an answer without text scores 0 against a gold text, as a missing value answer does. Claimed support gets P, R, F1
and EM against its best set; joint scores multiply answer and support P and R; ``gated_em`` needs R-precision 1.
Abstention precision and recall are over the unanswerable questions. Cost: mean, median, p90 and p95 (nearest rank)
and total of every cost field, and the answer EM reached within cumulative token budgets, over every answerable
question.
"""
from __future__ import annotations

import math
import re
import string
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable, Literal, Mapping, Sequence

from ..errors import ValidationError, make_finding
from ..record import identity_key, resolve_redirects
from . import _inputs
from ._common import mean, prf_split, report
from .bootstrap import Bootstrap, mean_interval

__all__ = ["RetrievalConfig", "normalize_answer", "score", "token_f1"]

DISCOUNTS = ("log2", "longmemeval")
ANSWER_MODES = ("single", "set")
COST_FIELDS = ("prompt_tokens", "completion_tokens", "llm_calls", "retrieval_calls", "hyperedges_visited",
               "retrieval_ms", "wall_ms", "usd")
BUDGET_STEPS = 10


@dataclass(frozen=True)
class RetrievalConfig:
    """The retrieval scorer's settings (DESIGN §9.2)."""

    ks: tuple[int, ...] = (1, 3, 5, 10, 20)
    headline_k: int = 10
    ndcg_discount: Literal["log2", "longmemeval"] = "log2"
    answer_mode: Literal["single", "set"] = "single"
    bootstrap: Bootstrap = Bootstrap()

    def __post_init__(self) -> None:
        ks = tuple(self.ks)
        if not ks or any(isinstance(k, bool) or not isinstance(k, int) or k < 1 for k in ks):
            raise ValueError(f"ks are positive integers, not {self.ks!r}")
        object.__setattr__(self, "ks", ks)
        if isinstance(self.headline_k, bool) or not isinstance(self.headline_k, int) or self.headline_k < 1:
            raise ValueError(f"headline_k is a positive integer, not {self.headline_k!r}")
        if self.ndcg_discount not in DISCOUNTS:
            raise ValueError(f"ndcg_discount must be one of {DISCOUNTS}, not {self.ndcg_discount!r}")
        if self.answer_mode not in ANSWER_MODES:
            raise ValueError(f"answer_mode must be one of {ANSWER_MODES}, not {self.answer_mode!r}")
        if not isinstance(self.bootstrap, Bootstrap):
            raise ValueError("bootstrap must be a Bootstrap")

    @property
    def cutoffs(self) -> tuple[int, ...]:
        """The k values reported: ``ks`` plus ``headline_k``, sorted."""
        return tuple(sorted(set(self.ks) | {self.headline_k}))


# ------------------------------------------------------------------------------------------------ answer text


_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCTUATION = frozenset(string.punctuation)


def normalize_answer(text: str) -> str:
    """SQuAD v1.1 normalisation: lower case, no punctuation, no articles (a, an, the), single spaces."""
    text = "".join(ch for ch in text.lower() if ch not in _PUNCTUATION)
    return " ".join(_ARTICLES.sub(" ", text).split())


def token_f1(prediction: str, gold: str) -> dict[str, Fraction]:
    """Token precision, recall and F1 after ``normalize_answer`` (all 0 without a common token)."""
    pt, gt = normalize_answer(prediction).split(), normalize_answer(gold).split()
    counts: dict[str, int] = {}
    for t in gt:
        counts[t] = counts.get(t, 0) + 1
    common = 0
    for t in pt:
        if counts.get(t, 0) > 0:
            counts[t] -= 1
            common += 1
    if common == 0:
        zero = Fraction(0)
        return {"p": zero, "r": zero, "f1": zero}
    p, r = Fraction(common, len(pt)), Fraction(common, len(gt))
    return {"p": p, "r": r, "f1": 2 * p * r / (p + r)}


# ------------------------------------------------------------------------------------------------ ranking


def _units(response: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    indexed = list(enumerate(response.get("retrieved", [])))
    return [u for _, u in sorted(indexed, key=lambda x: (x[1]["rank"], x[0]))]


def _found(units: Sequence[Mapping[str, Any]], k: int) -> set[str]:
    return {h for u in units[:k] for h in u["hyperedge_ids"]}


def _dcg(rels: list[int], discount: str) -> float:
    if discount == "log2":
        return math.fsum(r / math.log2(i + 1) for i, r in enumerate(rels, start=1))
    return math.fsum((r if i == 1 else r / math.log2(i)) for i, r in enumerate(rels, start=1))


def _ndcg(units: Sequence[Mapping[str, Any]], s: set[str], k: int, discount: str) -> float:
    seen: set[str] = set()
    rels = []
    for u in units[:k]:
        new = (set(u["hyperedge_ids"]) & s) - seen
        rels.append(1 if new else 0)
        seen |= new
    ideal = _dcg([1] * min(len(s), k), discount)
    return _dcg(rels, discount) / ideal if ideal else 0.0


def _covered(units: Sequence[Mapping[str, Any]], k: int,
             facts: Mapping[str, Mapping[str, Any]]) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for u in units[:k]:
        if "bids" in u:
            out |= {(e, b) for e, b in u["bids"]}
        elif u["unit_kind"] == "hyperedge":
            for h in u["hyperedge_ids"]:
                for b in (facts.get(h) or {}).get("bindings", []):
                    out.add((h, b["bid"]))
    return out


def _ranking(q: Mapping[str, Any], r: Mapping[str, Any] | None, config: RetrievalConfig,
             facts: Mapping[str, Mapping[str, Any]] | None) -> dict[str, Any] | None:
    sets = [set(x) for x in q["support"]["sets"] if x]
    if not sets:
        return None
    units = _units(r) if r is not None else []
    union = set().union(*sets)
    first = next((i for i, u in enumerate(units, start=1) if union & set(u["hyperedge_ids"])), None)
    out: dict[str, Any] = {}
    for k in config.cutoffs:
        found = _found(units, k)
        out[f"hit@{k}"] = Fraction(int(bool(found & union)))
        out[f"support_success@{k}"] = Fraction(int(any(x <= found for x in sets)))
        out[f"support_recall@{k}"] = max(Fraction(len(x & found), len(x)) for x in sets)
        out[f"mrr@{k}"] = Fraction(1, first) if first is not None and first <= k else Fraction(0)
        out[f"ndcg@{k}"] = max(_ndcg(units, x, k, config.ndcg_discount) for x in sets)
    out["r_precision"] = max(Fraction(len(x & _found(units, len(x))), len(x)) for x in sets)
    if facts is not None:
        gold = []
        for x in sets:
            missing = sorted(h for h in x if h not in facts)
            if missing:
                raise ValueError(f"{q['qid']!r}: facts lacks the support hyperedges {missing}")
            gold.append({(h, b["bid"]) for h in x for b in facts[h].get("bindings", [])})
        for k in config.cutoffs:
            cov = _covered(units, k, facts)
            out[f"binding_coverage@{k}"] = max((Fraction(len(g & cov), len(g)) for g in gold if g), default=None)
    return out


# ------------------------------------------------------------------------------------------------ answers


def _ids(values: Iterable[Mapping[str, Any]], entities: Mapping[str, Mapping[str, Any]], path: str, *,
         gold: bool) -> list[str]:
    """The identity keys of values, entities after their redirects. A value whose identity cannot be computed (a
    year 0 is S006) raises ``ValidationError`` at ``path``/k: I003 with the finding nested for a gold value, which is
    embedded in a C4 item, and the finding's own code for a response's value."""
    out = []
    for k, v in enumerate(values):
        if set(v) == {"entity"} and entities:
            v = {"entity": resolve_redirects(v["entity"], entities)}
        try:
            out.append(identity_key(v))
        except ValidationError as e:
            where = f"{path}/{k}"
            raise (_inputs.embedded_error(e, where) if gold
                   else ValidationError.from_findings(_inputs.located(e, where))) from None
    return out


def _answer(q: Mapping[str, Any], r: Mapping[str, Any] | None, mode: str,
            entities: Mapping[str, Mapping[str, Any]], qpath: str, rpath: str) -> dict[str, Any]:
    gold_ids = _ids(q["answer"]["values"], entities, f"{qpath}/answer/values", gold=True)
    ans = r["answer"] if r is not None else {"values": [], "abstained": False}
    got = [] if ans["abstained"] else _ids(ans["values"], entities, f"{rpath}/answer/values", gold=False)
    out: dict[str, Any] = {"abstained": bool(ans["abstained"]), "text_em": None, "token_f1": None}
    gold_text, text = q["answer"].get("text"), ans.get("text")
    if gold_text is not None and text is not None and not ans["abstained"]:
        tf = token_f1(text, gold_text)
        out["text_em"] = Fraction(int(normalize_answer(text) == normalize_answer(gold_text)))
        out["token_f1"], out["token_p"], out["token_r"] = tf["f1"], tf["p"], tf["r"]
    elif gold_text is not None:  # no response, an abstention or no text scores 0, as a missing value answer does
        zero = Fraction(0)
        out["text_em"] = out["token_f1"] = out["token_p"] = out["token_r"] = zero
    if mode == "set":
        s = None
        if gold_ids or gold_text is None:  # text-only gold has no value set to compare with
            tp = len(set(got) & set(gold_ids))
            s = prf_split(tp, len(set(got)), tp, len(set(gold_ids)))
            out.update(set_p=s["p"], set_r=s["r"], set_f1=s["f1"], set_flag=s["flag"])
        out["value_em"] = Fraction(int(set(got) == set(gold_ids))) if gold_ids else None
        out["em"] = out["value_em"] if gold_ids else out["text_em"]
        out["answer_p"], out["answer_r"] = (s["p"], s["r"]) if gold_ids and s is not None else \
            (out.get("token_p"), out.get("token_r"))
    else:
        out["value_em"] = Fraction(int(bool(got) and got[0] in gold_ids)) if gold_ids else None
        out["em"] = out["value_em"] if gold_ids else out["text_em"]
        if gold_ids:
            out["answer_p"] = out["answer_r"] = out["value_em"]
        else:
            out["answer_p"], out["answer_r"] = out.get("token_p"), out.get("token_r")
    return out


def _support(q: Mapping[str, Any], r: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if r is None or "support_claimed" not in r:
        return None
    claimed = set(r["support_claimed"])
    best = None
    for x in (set(s) for s in q["support"]["sets"]):
        tp = len(claimed & x)
        s = prf_split(tp, len(claimed), tp, len(x))
        cand = {"p": s["p"], "r": s["r"], "f1": s["f1"], "em": Fraction(int(claimed == x))}
        if best is None or cand["f1"] > best["f1"]:
            best = cand
    return best


# ------------------------------------------------------------------------------------------------ cost


def _nearest_rank(sorted_values: Sequence[float], p: Fraction) -> float:
    return sorted_values[max(0, math.ceil(p * len(sorted_values)) - 1)]


def _cost_stats(values: list[float]) -> dict[str, Any]:
    xs = sorted(values)
    n = len(xs)
    median = xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
    return {"n": n, "mean": math.fsum(xs) / n, "median": median, "p90": _nearest_rank(xs, Fraction(9, 10)),
            "p95": _nearest_rank(xs, Fraction(19, 20)), "total": math.fsum(xs)}


def _budget(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Answer EM reached within cumulative token budgets (critique CONS-07): the questions in input order, each
    response spending its prompt and completion tokens; a question counts when the running total, itself included,
    stays within the budget. A question without a response spends nothing and is never answered. The budgets are
    tenths of the total; the denominator is every answerable question, with or without a response."""
    n_answerable = sum(1 for r in rows if r["answerable"])
    spent = [r for r in rows if not r["missing"]]
    if not spent or not n_answerable:
        return []
    total = sum(r["tokens"] for r in spent)
    out = []
    for step in range(1, BUDGET_STEPS + 1):
        limit = math.ceil(Fraction(total * step, BUDGET_STEPS))
        run, correct, answered = 0, Fraction(0), 0
        for r in spent:
            run += r["tokens"]
            if run > limit:
                break
            answered += 1
            if r["answerable"]:
                correct += r["em"] or 0
        out.append({"budget": limit, "fraction": step / BUDGET_STEPS, "n_answered": answered,
                    "answer_em": float(correct / n_answerable)})
    return out


# ------------------------------------------------------------------------------------------------ score


def _facts(facts: Any) -> tuple[dict[str, Mapping[str, Any]] | None, dict[str, Mapping[str, Any]]]:
    if facts is None:
        return None, {}
    records = list(facts.values()) if isinstance(facts, Mapping) else list(facts)
    edges = {r["id"]: r for r in records if isinstance(r, Mapping) and r.get("kind") == "hyperedge"}
    ents = {r["id"]: r for r in records if isinstance(r, Mapping) and r.get("kind") == "entity"}
    if isinstance(facts, Mapping):
        edges.update({k: v for k, v in facts.items() if isinstance(v, Mapping) and v.get("kind") == "hyperedge"})
    return edges or None, ents


def _mean_block(rows: list[dict[str, Any]], keys: Iterable[str]) -> dict[str, Any]:
    out = {}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        out[k] = None if not vals else float(mean(vals)) if all(isinstance(v, Fraction) for v in vals) \
            else math.fsum(float(v) for v in vals) / len(vals)
    return out


def score(questions: Iterable[Mapping[str, Any]], responses: Iterable[Mapping[str, Any]], *,
          facts: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]] | None = None,
          config: RetrievalConfig = RetrievalConfig()) -> dict[str, Any]:
    """Score retrieval (DESIGN §9.2, §9.3). ``questions``: ``c4-retrieval-question`` items (a whole C4 file may be
    passed). ``responses``: ``retrieval-response`` records. ``facts``: the gold hyperedges by id (or an iterable of
    C1 records), for ``binding_coverage@k``; entity records among them resolve redirects in answers. Returns
    ``{scorer, config, contracts, aggregate, breakdowns, items, bootstrap}`` with ``items`` keyed by qid."""
    if not isinstance(config, RetrievalConfig):
        raise TypeError("config must be a RetrievalConfig")
    qs, headers = _inputs.check_items(questions, kinds=("c4-retrieval-question",))
    recs = _inputs.check_outputs(responses, kind="retrieval-response")
    by_qid: dict[str, dict[str, Any]] = {}
    line_of: dict[str, int] = {}
    for n, r in enumerate(recs):
        if r["qid"] in by_qid:
            raise ValidationError.from_findings([make_finding("KHG-C010", f"/lines/{n}/qid",
                                                              f"two retrieval responses for {r['qid']!r}")])
        by_qid[r["qid"]] = r
        line_of[r["qid"]] = n
    edges, entities = _facts(facts)
    rows: list[dict[str, Any]] = []
    qids: set[str] = set()
    for n, q in enumerate(qs):
        if q["qid"] in qids:
            raise ValidationError.from_findings([make_finding("KHG-I002", f"/questions/{n}/qid",
                                                              f"qid {q['qid']!r} appears twice")])
        qids.add(q["qid"])
        r = by_qid.get(q["qid"])
        row: dict[str, Any] = {"qid": q["qid"], "missing": r is None, "answerable": q["answerable"],
                               "type": q["type"], "hops": q["hops"], "source_class": q["source_class"],
                               "depends_on": sorted({h for s in q["support"]["sets"] for h in s})}
        ranking = _ranking(q, r, config, edges)
        if ranking is not None:
            row.update(ranking)
        row["has_support"] = ranking is not None
        ans = _answer(q, r, config.answer_mode, entities, f"/questions/{n}",
                      f"/lines/{line_of[q['qid']]}" if r is not None else "")
        row.update(ans)
        sup = _support(q, r) if ranking is not None else None
        if sup is not None:
            row.update(support_p=sup["p"], support_r=sup["r"], support_f1=sup["f1"], support_em=sup["em"])
            if ans.get("answer_p") is not None and ans.get("answer_r") is not None:
                jp, jr = ans["answer_p"] * sup["p"], ans["answer_r"] * sup["r"]
                row["joint_p"], row["joint_r"] = jp, jr
                row["joint_f1"] = 2 * jp * jr / (jp + jr) if jp + jr else Fraction(0)
                if ans.get("em") is not None:
                    row["joint_em"] = ans["em"] * sup["em"]
        if ranking is not None and ans.get("em") is not None:
            row["gated_em"] = ans["em"] * int(ranking["r_precision"] == 1)
        cost = (r or {}).get("cost") or {}
        for f in COST_FIELDS:
            row[f"cost_{f}"] = cost.get(f)
        row["tokens"] = (cost["prompt_tokens"] + cost["completion_tokens"]) if cost else None
        rows.append(row)
    k = config.headline_k
    rank_keys = [f"{m}@{c}" for c in config.cutoffs for m in ("hit", "support_success", "support_recall", "mrr",
                                                                "ndcg")] + ["r_precision"]
    if edges is not None:
        rank_keys += [f"binding_coverage@{c}" for c in config.cutoffs]
    answer_keys = ["em", "value_em", "text_em", "token_f1"] + (["set_p", "set_r", "set_f1"]
                                                                if config.answer_mode == "set" else [])
    answerable = [r for r in rows if r["answerable"]]
    with_support = [r for r in rows if r["has_support"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    abstained = [r for r in rows if r["abstained"] and not r["missing"]]
    hit = sum(1 for r in abstained if not r["answerable"])
    aggregate: dict[str, Any] = {
        "n_questions": len(rows), "n_responses": len(recs), "n_missing": sum(r["missing"] for r in rows),
        "n_unmatched_responses": len(set(by_qid) - qids), "n_answerable": len(answerable),
        "headline": {f"support_success@{k}": _mean_block(with_support, [f"support_success@{k}"])[
            f"support_success@{k}"], f"mrr@{k}": _mean_block(with_support, [f"mrr@{k}"])[f"mrr@{k}"]},
        "ranking": _mean_block(with_support, rank_keys),
        "answer": _mean_block(answerable, answer_keys),
        "support": _mean_block(with_support, ["support_p", "support_r", "support_f1", "support_em"]),
        "joint": _mean_block(answerable, ["joint_p", "joint_r", "joint_f1", "joint_em"]),
        "gated_em": _mean_block(answerable, ["gated_em"])["gated_em"],
        "abstention": {"precision": float(Fraction(hit, len(abstained))) if abstained else None,
                       "recall": float(Fraction(hit, len(unanswerable))) if unanswerable else None,
                       "n_abstained": len(abstained), "n_unanswerable": len(unanswerable)},
        "ndcg_discount": "log2(i+1)" if config.ndcg_discount == "log2" else "longmemeval"}
    cost: dict[str, Any] = {}
    for f in COST_FIELDS:
        vals = [r[f"cost_{f}"] for r in rows if r[f"cost_{f}"] is not None]
        if vals:
            cost[f] = _cost_stats([float(v) for v in vals])
    cost["price_tables"] = sorted({r["cost"]["price_table"] for r in recs if "price_table" in r.get("cost", {})})
    cost["budget_curve"] = _budget(rows)
    aggregate["cost"] = cost
    breakdowns = {}
    for key in ("hops", "type", "source_class"):
        groups: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            groups.setdefault(str(r[key]), []).append(r)
        breakdowns[f"by_{key}"] = {g: {"n": len(v), **_mean_block([x for x in v if x["has_support"]],
                                                                  [f"support_success@{k}", f"mrr@{k}"]),
                                       **_mean_block([x for x in v if x["answerable"]], ["em"])}
                                   for g, v in sorted(groups.items())}
    items = {}
    for r in rows:
        item = {key: (float(v) if isinstance(v, Fraction) else v) for key, v in r.items()
                if key not in ("qid",) and not key.startswith("cost_") and v is not None}
        items[r["qid"]] = item
    boot = None
    if config.bootstrap.resamples and rows:
        intervals = {}
        for key, pool in ((f"support_success@{k}", with_support), (f"mrr@{k}", with_support), ("em", answerable)):
            vals = [r[key] for r in pool if r.get(key) is not None]
            intervals[key] = mean_interval(vals, config.bootstrap)
        boot = {**config.bootstrap.as_dict(), "unit": "question", "n_units": len(rows), "intervals": intervals}
    qsets = [q["qset"] for q in qs] + [h["qset"] for h in headers]
    return report("retrieval", config, aggregate=aggregate, breakdowns=breakdowns, items=items, bootstrap=boot,
                  qsets=qsets, schema=headers[0]["schema"] if headers else None)
