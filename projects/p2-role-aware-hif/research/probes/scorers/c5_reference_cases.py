"""Reference computations for the C5 scorer unit-test cases in 05-prior-art-scorers.md.

Research probe, not the C5 implementation. Pure Python standard library, deterministic.
Every function here restates a formula from the report so that the expected values quoted in
the report's unit-test tables are computed twice: once by hand, once by this script.

Run:  python3 c5_reference_cases.py  > c5_reference_cases.out.json
"""

from __future__ import annotations

import itertools
import json
import math
import re
import string
from collections import Counter
from fractions import Fraction


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def prf(tp: float, n_pred: float, n_gold: float) -> dict:
    """Precision, recall, F1 with the report's empty-set conventions.

    |P| = 0 -> precision 0 (flagged); |G| = 0 -> recall 0 (flagged);
    |P| = |G| = 0 -> all three are 1 (nothing to find, nothing claimed).
    """
    if n_pred == 0 and n_gold == 0:
        return {"p": 1.0, "r": 1.0, "f1": 1.0, "flag": "both_empty"}
    p = tp / n_pred if n_pred else 0.0
    r = tp / n_gold if n_gold else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    flag = "no_predictions" if n_pred == 0 else ("no_gold" if n_gold == 0 else None)
    return {"p": p, "r": r, "f1": f1, "flag": flag}


def rnd(x, k=6):
    if isinstance(x, dict):
        return {a: rnd(b, k) for a, b in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, k) for v in x]
    if isinstance(x, float):
        return round(x, k)
    return x


def best_assignment(weights: list[list[float]]) -> tuple[float, list[tuple[int, int]]]:
    """Maximum-weight 1:1 assignment by brute force (tests are tiny).

    The implementation should use the Hungarian algorithm (Kuhn 1955; Munkres 1957);
    brute force is used here only because it is obviously correct on 2x2 or 3x3 inputs.
    """
    n_p = len(weights)
    n_g = len(weights[0]) if weights else 0
    best, best_pairs = 0.0, []
    if n_p <= n_g:
        for perm in itertools.permutations(range(n_g), n_p):
            s = sum(weights[i][perm[i]] for i in range(n_p))
            if s > best:
                best, best_pairs = s, [(i, perm[i]) for i in range(n_p)]
    else:
        for perm in itertools.permutations(range(n_p), n_g):
            s = sum(weights[perm[j]][j] for j in range(n_g))
            if s > best:
                best, best_pairs = s, [(perm[j], j) for j in range(n_g)]
    return best, [pq for pq in best_pairs if weights[pq[0]][pq[1]] > 0]


def greedy_assignment(weights: list[list[float]]) -> float:
    cells = sorted(((w, i, j) for i, row in enumerate(weights) for j, w in enumerate(row)), reverse=True)
    used_p, used_g, total = set(), set(), 0.0
    for w, i, j in cells:
        if i in used_p or j in used_g or w <= 0:
            continue
        used_p.add(i)
        used_g.add(j)
        total += w
    return total


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
# A fact is (relation, frozenset of (role, value)).  Values are canonical strings.

def fact(rel: str, **bindings) -> tuple[str, frozenset]:
    return (rel, frozenset(bindings.items()))


def dedup(facts):
    seen, out, dups = set(), [], 0
    for f in facts:
        if f in seen:
            dups += 1
            continue
        seen.add(f)
        out.append(f)
    return out, dups


def extraction_scores(gold, pred, key_roles: dict | None = None) -> dict:
    pred, n_dup = dedup(pred)
    gold, _ = dedup(gold)
    # strict fact-level
    tp_strict = len(set(pred) & set(gold))
    strict = prf(tp_strict, len(pred), len(gold))
    # core / key-role fact level
    core = None
    if key_roles:
        def core_of(f):
            rel, b = f
            k = key_roles.get(rel, set())
            return (rel, frozenset((r, v) for r, v in b if r in k))
        cp, cg = {core_of(f) for f in pred}, {core_of(f) for f in gold}
        core = prf(len(cp & cg), len(cp), len(cg))
    # One 1:1 fact alignment per document.  Relation must match.  The weight is lexicographic:
    # first the number of shared values (role ignored, the ACE "identified" notion), then the number
    # of shared (role, value) bindings (the ACE "identified and classified" notion) as tie-breaker.
    def value_overlap(bp, bg):
        return sum((Counter(v for _, v in bp) & Counter(v for _, v in bg)).values())

    big = 1 + max([len(b) for _, b in pred + gold] or [0])
    w = [[(value_overlap(bp, bg) * big + len(bp & bg)) if rp == rg else 0 for (rg, bg) in gold]
         for (rp, bp) in pred] if pred and gold else []
    _, pairs = best_assignment(w) if w else (0.0, [])
    n_bp = sum(len(b) for _, b in pred)
    n_bg = sum(len(b) for _, b in gold)
    ident = sum(value_overlap(pred[i][1], gold[j][1]) for i, j in pairs)
    classified = sum(len(pred[i][1] & gold[j][1]) for i, j in pairs)
    arg_i = prf(ident, n_bp, n_bg)
    arg_c = prf(classified, n_bp, n_bg)          # = binding-level F1 under the alignment
    role_acc = classified / ident if ident else None
    binding = arg_c
    # greedy alignment on the same weights, for the Hungarian-vs-greedy test only
    wb = [[len(bp & bg) if rp == rg else 0 for (rg, bg) in gold] for (rp, bp) in pred] if pred and gold else []
    binding_greedy = prf(greedy_assignment(wb) if wb else 0.0, n_bp, n_bg)
    # pooled bindings (ignores grouping)
    pooled_p = {(rel, rv) for rel, b in pred for rv in b}
    pooled_g = {(rel, rv) for rel, b in gold for rv in b}
    pooled = prf(len(pooled_p & pooled_g), len(pooled_p), len(pooled_g))
    # role-typed pairwise projection (SciREX-style split of an n-ary fact into pairs)
    def pairs_of(fs):
        out = set()
        for rel, b in fs:
            for x, y in itertools.combinations(sorted(b), 2):
                out.add((rel, x, y))
        return out
    pp, pg = pairs_of(pred), pairs_of(gold)
    pairwise = prf(len(pp & pg), len(pp), len(pg))
    # participant-set match: relation and roles ignored, value multisets compared
    def vset(fs):
        return {tuple(sorted(Counter(v for _, v in b).elements())) for _, b in fs}
    vp_, vg_ = vset(pred), vset(gold)
    participant_set = prf(len(vp_ & vg_), len(vp_), len(vg_))
    return {
        "n_pred_after_dedup": len(pred), "n_duplicates_removed": n_dup, "n_gold": len(gold),
        "strict": strict, "core": core, "binding_optimal": binding, "binding_greedy": binding_greedy,
        "arg_identification": arg_i, "arg_classification": arg_c, "role_accuracy": role_acc,
        "pooled_binding": pooled, "grouping_gap_f1": pooled["f1"] - binding["f1"], "pairwise": pairwise,
        "participant_set": participant_set,
    }


def nested_loop_count(gold, pred) -> dict:
    """The HyperRED / Text2NKG counting pattern: every equal (pred, gold) pair counts."""
    tp = sum(1 for a in pred for b in gold if a == b)
    return {"tp": tp, "p": tp / len(pred), "r": tp / len(gold)}


def match_date(pred: str, pred_prec: str, gold: str, gold_prec: str, rule: str) -> bool:
    order = {"year": 0, "month": 1, "day": 2}
    cut = {"year": 4, "month": 7, "day": 10}
    if rule == "exact":
        return pred == gold and pred_prec == gold_prec
    if rule == "truncate_to_gold":
        return order[pred_prec] >= order[gold_prec] and pred[: cut[gold_prec]] == gold[: cut[gold_prec]]
    raise ValueError(rule)


def extraction_cases() -> dict:
    out = {}
    g4 = fact("r", A="a", B="b", C="c", D="d")
    out["E1_perfect"] = extraction_scores([g4], [g4])
    out["E2_no_predictions"] = extraction_scores([g4], [])
    out["E3_both_empty"] = extraction_scores([], [])
    out["E4_arity_3_vs_4"] = extraction_scores([g4], [fact("r", A="a", B="b", C="c")], key_roles={"r": {"A", "B"}})
    out["E5_role_swap"] = extraction_scores([fact("r", A="a", B="b")], [fact("r", A="b", B="a")])
    out["E5b_partial_role_swap"] = extraction_scores([fact("r", A="a", B="b", C="c")],
                                                     [fact("r", A="b", B="a", C="c")])
    out["E5c_wrong_relation"] = extraction_scores([fact("r", A="a", B="b")], [fact("s", A="a", B="b")])
    dup = fact("r", A="a", B="b")
    out["E6_duplicate_prediction"] = extraction_scores([dup], [dup, dup])
    out["E6_nested_loop_counting"] = nested_loop_count([dup], [dup, dup])
    g1, g2 = fact("r", A="a", B="b", C="c"), fact("r", A="a", B="b", C="d")
    out["E7_one_pred_two_gold"] = extraction_scores([g1, g2], [fact("r", A="a", B="b", C="c")])
    gold8 = [fact("r", A="a", B="b", C="c", E="e"), fact("r", A="a", B="b", D="d")]
    pred8 = [fact("r", A="a", B="b", C="c"), fact("r", C="c", E="e")]
    out["E8_hungarian_vs_greedy"] = extraction_scores(gold8, pred8)
    out["E9_date_precision"] = {
        "truncate_to_gold": match_date("1921-05-02", "day", "1921", "year", "truncate_to_gold"),
        "exact": match_date("1921-05-02", "day", "1921", "year", "exact"),
        "coarser_prediction_truncate": match_date("1921", "year", "1921-05-02", "day", "truncate_to_gold"),
    }
    out["E10_core_vs_strict"] = extraction_scores(
        [fact("r", A="a", B="b", Q="q")], [fact("r", A="a", B="b", Q="z")], key_roles={"r": {"A", "B"}})
    # E11 per-arity recall: one arity-2 gold found, one arity-4 gold missed
    ga2, ga4 = fact("r2", A="a", B="b"), fact("r4", A="a", B="b", C="c", D="d")
    s = extraction_scores([ga2, ga4], [ga2])
    out["E11_per_arity"] = {"micro_recall": s["strict"]["r"], "recall_arity2": 1.0, "recall_arity4": 0.0,
                            "macro_over_arity_recall": (1.0 + 0.0) / 2}
    return out


# ---------------------------------------------------------------------------
# Stability
# ---------------------------------------------------------------------------

def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def stability(runs: list[set]) -> dict:
    k = len(runs)
    pairs = list(itertools.combinations(range(k), 2))
    js = [jaccard(runs[i], runs[j]) for i, j in pairs]
    union = set().union(*runs)
    inter = set.intersection(*runs) if runs else set()
    support = {f: sum(f in r for r in runs) for f in union}
    unstable = sum(1 for s in support.values() if 0 < s < k)
    disagreement = {f: s * (k - s) / math.comb(k, 2) for f, s in support.items()}
    return {
        "pairwise_jaccard": js, "mean_pairwise_jaccard": sum(js) / len(js),
        "core_ratio": (len(inter) / len(union)) if union else 1.0,
        "support_histogram": dict(sorted(Counter(support.values()).items())),
        "unstable_fraction": unstable / len(union) if union else 0.0,
        "mean_fact_disagreement": sum(disagreement.values()) / len(disagreement) if disagreement else 0.0,
    }


def order_effect(runs: dict) -> dict:
    """runs: {(order, seed): set}.  Within = same order, between = different orders."""
    keys = sorted(runs)
    within, between = [], []
    for a, b in itertools.combinations(keys, 2):
        (within if a[0] == b[0] else between).append(jaccard(runs[a], runs[b]))
    jw, jb = sum(within) / len(within), sum(between) / len(between)
    return {"n_within_pairs": len(within), "n_between_pairs": len(between),
            "J_within": jw, "J_between": jb, "delta_order": jw - jb}


def stability_cases() -> dict:
    out = {"S1_three_runs": stability([{"a", "b", "c"}, {"a", "b", "d"}, {"a", "b", "c"}])}
    out["S2_all_empty"] = stability([set(), set(), set()])
    o1 = {"a", "b"}
    o2 = {"a", "c"}
    runs = {("O1", s): set(o1) for s in (1, 2, 3)}
    runs.update({("O2", s): set(o2) for s in (1, 2, 3)})
    out["S3_order_effect"] = order_effect(runs)
    gold = ["g1", "g2", "g3"]
    matched = [{"g1", "g2"}, {"g1"}, {"g1"}]
    part = {"stable": 0, "unstable": 0, "miss": 0}
    for g in gold:
        n = sum(g in m for m in matched)
        part["stable" if n == len(matched) else ("miss" if n == 0 else "unstable")] += 1
    out["S4_gold_conditioned"] = {k: v / len(gold) for k, v in part.items()}
    return out


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------

def ranks(scores: dict, target: str, known_true: set) -> dict:
    """Filtered ranks of target among candidates; known_true (minus target) is removed."""
    t = scores[target]
    others = [s for c, s in scores.items() if c != target and c not in known_true]
    opt = 1 + sum(s > t for s in others)
    pes = 1 + sum(s >= t for s in others)
    real = (opt + pes) / 2
    n = pes - opt + 1
    exp_rr = sum(Fraction(1, r) for r in range(opt, pes + 1)) / n
    def exp_hits(k):
        return max(0, min(k, pes) - opt + 1) / n
    return {"optimistic": opt, "pessimistic": pes, "realistic": real,
            "rr_realistic": 1 / real, "expected_rr_random_ties": float(exp_rr),
            "hits1_realistic": float(real <= 1), "expected_hits1": exp_hits(1),
            "hits3_realistic": float(real <= 3), "expected_hits3": exp_hits(3),
            "hits10_realistic": float(real <= 10), "expected_hits10": exp_hits(10)}


def ece(conf: list[float], correct: list[int], m: int = 10) -> float:
    bins = {}
    for c, y in zip(conf, correct):
        b = max(1, math.ceil(c * m))  # bin index for ((b-1)/m, b/m]; c == 0 goes to bin 1
        bins.setdefault(b, []).append((c, y))
    n = len(conf)
    total = 0.0
    for items in bins.values():
        acc = sum(y for _, y in items) / len(items)
        cf = sum(c for c, _ in items) / len(items)
        total += len(items) / n * abs(acc - cf)
    return total


def brier(conf, correct):
    return sum((c - y) ** 2 for c, y in zip(conf, correct)) / len(conf)


def completion_cases() -> dict:
    out = {}
    out["C1_no_ties"] = ranks({"t": 0.5, "x": 0.9, "y": 0.8, "z": 0.1}, "t", set())
    sc = {"e1": 0.9, "e2": 0.2, "e3": 0.7, "e4": 0.1, "e5": 0.05}
    out["C2_raw"] = ranks(sc, "e3", set())
    out["C2_filtered"] = ranks(sc, "e3", {"e1"})
    out["C3_four_way_tie"] = ranks({"t": 0.8, "a": 0.8, "b": 0.8, "c": 0.8, "d": 0.1}, "t", set())
    rr = {"F1": [1.0, 1.0], "F2": [0.1, 0.1, 0.1, 0.1]}
    per_task = sum(sum(v) for v in rr.values()) / sum(len(v) for v in rr.values())
    per_fact = sum(sum(v) / len(v) for v in rr.values()) / len(rr)
    out["C4_averaging"] = {"per_task_mrr": per_task, "per_fact_mrr": per_fact,
                           "macro_over_arity_mrr": (1.0 + 0.1) / 2}
    # C5 time-aware filtering: o1 valid 2010-2015, o2 valid 2016-now, query at 2020, target o2
    sc5 = {"o1": 0.9, "o2": 0.8, "o3": 0.1}
    out["C5_time_agnostic_filter"] = ranks(sc5, "o2", {"o1", "o2"})
    out["C5_time_aware_filter"] = ranks(sc5, "o2", {"o2"})
    # C6 qualifier-monotone filtering: UZH is the object of a known fact whose qualifiers are a superset
    sc6 = {"ETH": 0.6, "UZH": 0.7, "TUM": 0.1}
    out["C6_exact_filter"] = ranks(sc6, "ETH", {"ETH"})
    out["C6_monotone_filter"] = ranks(sc6, "ETH", {"ETH", "UZH"})
    conf = [0.95] * 4 + [0.55] * 4 + [0.15] * 2
    corr = [1, 1, 1, 0] + [1, 1, 0, 0] + [0, 0]
    out["C7_calibration"] = {"ece_10_bins": ece(conf, corr, 10), "brier_top1": brier(conf, corr),
                             "accuracy": sum(corr) / len(corr), "mean_confidence": sum(conf) / len(conf)}
    # C8: the same ten queries split by arity: arity 2 = first 5 items, arity 4 = last 5
    out["C8_ece_by_arity"] = {"arity2": ece(conf[:5], corr[:5], 10), "arity4": ece(conf[5:], corr[5:], 10)}
    return out


# ---------------------------------------------------------------------------
# Retrieval and answers
# ---------------------------------------------------------------------------

def normalize_answer(s: str) -> str:
    """SQuAD v1.1 normalisation (lower, strip punctuation, drop a/an/the, collapse whitespace)."""
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def token_f1(pred: str, gold: str) -> dict:
    pt, gt = normalize_answer(pred).split(), normalize_answer(gold).split()
    common = sum((Counter(pt) & Counter(gt)).values())
    if common == 0:
        return {"p": 0.0, "r": 0.0, "f1": 0.0}
    p, r = common / len(pt), common / len(gt)
    return {"p": p, "r": r, "f1": 2 * p * r / (p + r)}


def dcg(rels, discount):
    total = 0.0
    for i, rel in enumerate(rels, start=1):
        if discount == "log2(i+1)":
            total += rel / math.log2(i + 1)
        elif discount == "longmemeval":  # rel_1 + sum_{i>=2} rel_i / log2(i)
            total += rel if i == 1 else rel / math.log2(i)
    return total


def ndcg(ranked, gold, k, discount):
    rels = [1 if d in gold else 0 for d in ranked[:k]]
    ideal = [1] * min(len(gold), k)
    return dcg(rels, discount) / dcg(ideal, discount)


def kilt_recall_at_k(ranked, evidence_sets, k):
    """KILT: each evidence set counts as one point, placed at its last retrieved member."""
    sets = [set(s) for s in evidence_sets]
    rank = []
    for doc in ranked:
        found = False
        for idx, s in enumerate(sets):
            if doc in s:
                found = True
                key = f"set:{idx}"
                if key in rank:
                    rank.remove(key)
                s.discard(doc)
                rank.append(True if not s else key)
        if not found:
            rank.append(False)
    return rank[:k].count(True) / len(evidence_sets)


def r_precision(ranked, evidence_sets):
    return max(sum(1 for d in ranked[: len(s)] if d in s) / len(s) for s in evidence_sets)


def retrieval_cases() -> dict:
    out = {}
    ranked = ["h3", "h1", "h4", "h2"]
    gold = {"h1", "h2"}
    first = next(i for i, d in enumerate(ranked, start=1) if d in gold)
    out["R1_single_support_set"] = {
        "recall_any@1": float(any(d in gold for d in ranked[:1])),
        "recall_any@2": float(any(d in gold for d in ranked[:2])),
        "recall_all@2": float(gold <= set(ranked[:2])),
        "recall_all@4": float(gold <= set(ranked[:4])),
        "fractional_recall@2": len(gold & set(ranked[:2])) / len(gold),
        "mrr": 1 / first,
        "r_precision": r_precision(ranked, [gold]),
        "kilt_recall@2": kilt_recall_at_k(ranked, [gold], 2),
        "kilt_recall@3": kilt_recall_at_k(ranked, [gold], 3),
        "kilt_recall@4": kilt_recall_at_k(ranked, [gold], 4),
        "ndcg@4_log2(i+1)": ndcg(ranked, gold, 4, "log2(i+1)"),
        "ndcg@4_longmemeval": ndcg(ranked, gold, 4, "longmemeval"),
    }
    sets2 = [{"h1", "h2"}, {"h5"}]
    ranked2 = ["h5", "h1", "h9"]
    out["R2_alternative_support_sets"] = {"r_precision": r_precision(ranked2, sets2),
                                          "support_success@1": float(any(st <= set(ranked2[:1]) for st in sets2)),
                                          "kilt_recall@1": kilt_recall_at_k(ranked2, sets2, 1)}
    g = "Royal Swedish Academy of Sciences"
    out["R3_answer_em_f1"] = {
        "em_with_article_and_period": normalize_answer("the Royal Swedish Academy of Sciences.") == normalize_answer(g),
        "f1_partial": token_f1("Swedish Academy", g),
    }
    gold_ids, pred_ids = {"Q1", "Q2"}, {"Q1", "Q3"}
    tp = len(gold_ids & pred_ids)
    out["R4_entity_set"] = prf(tp, len(pred_ids), len(gold_ids)) | {"em": float(gold_ids == pred_ids)}
    pa, ra = out["R3_answer_em_f1"]["f1_partial"]["p"], out["R3_answer_em_f1"]["f1_partial"]["r"]
    ps, rs = 0.5, 0.5
    jp, jr = pa * ps, ra * rs
    out["R5_joint_f1"] = {"joint_p": jp, "joint_r": jr, "joint_f1": 2 * jp * jr / (jp + jr)}
    out["R6_gated_em"] = {"em1_rprec_0.5": 1 * float(0.5 == 1.0), "em1_rprec_1.0": 1 * float(1.0 == 1.0)}
    lat = sorted([100, 300, 200])
    nearest_rank_p90 = lat[math.ceil(0.9 * len(lat)) - 1]
    out["R7_cost"] = {"mean": sum(lat) / 3, "median": lat[1], "p90_nearest_rank": nearest_rank_p90}
    out["R8_subem_false_positive"] = {
        "char_substring": normalize_answer("5") in normalize_answer("15 items"),
        "token_containment": normalize_answer("5").split()[0] in normalize_answer("15 items").split(),
    }
    return out


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def memory_outcome(answer_ids: list[str], abstained: bool, current: set, earlier: set, answerable: bool,
                   later: set | None = None) -> dict:
    """Classify one memory answer.  current = values valid at the question's as-of time;
    earlier = values superseded before it (stale if returned); later = values that only become valid
    after the as-of time (anachronistic if returned; only non-empty for as-of-past questions)."""
    a, later = set(answer_ids), (later or set())
    if not answerable:
        return {"outcome": "correct_abstention" if abstained else "hallucinated", "strict": int(abstained),
                "lenient": int(abstained)}
    if abstained or not a:
        return {"outcome": "abstained", "strict": 0, "lenient": 0}
    has_cur, has_old, has_new = bool(a & current), bool(a & earlier), bool(a & later)
    if has_cur and not (has_old or has_new):
        return {"outcome": "current", "strict": 1, "lenient": 1}
    if has_cur:
        return {"outcome": "hedged", "strict": 0, "lenient": 1}
    if has_old:
        return {"outcome": "stale", "strict": 0, "lenient": 0}
    if has_new:
        return {"outcome": "anachronistic", "strict": 0, "lenient": 0}
    return {"outcome": "wrong", "strict": 0, "lenient": 0}


def memory_cases() -> dict:
    out = {
        "M1_current": memory_outcome(["Qnew"], False, {"Qnew"}, {"Qold"}, True),
        "M2_stale": memory_outcome(["Qold"], False, {"Qnew"}, {"Qold"}, True),
        "M3_hedged": memory_outcome(["Qold", "Qnew"], False, {"Qnew"}, {"Qold"}, True),
        "M4a_unanswerable_abstains": memory_outcome([], True, set(), set(), False),
        "M4b_unanswerable_answers": memory_outcome(["Qx"], False, set(), set(), False),
        "M5_as_of_past_gets_future_value": memory_outcome(["o2"], False, {"o1"}, set(), True, later={"o2"}),
    }
    outcomes = ["current"] * 6 + ["stale"] * 3 + ["abstained"]
    c = Counter(outcomes)
    out["M6_aggregate"] = {"accuracy": c["current"] / 10, "stale_rate": c["stale"] / 10,
                           "abstention_rate": c["abstained"] / 10,
                           "stale_share_of_errors": c["stale"] / (10 - c["current"])}
    scores = {"Qnew": 0.7, "Qold": 0.6, "Qother": 0.1}
    out["M7_pairwise_efficacy"] = int(scores["Qnew"] > max(scores[o] for o in ["Qold"]))
    out["M8_off_by_one"] = {"strict": int(19 == 18), "tolerance_1": int(abs(19 - 18) <= 1)}
    return out


if __name__ == "__main__":
    result = {
        "extraction": extraction_cases(),
        "stability": stability_cases(),
        "completion": completion_cases(),
        "retrieval": retrieval_cases(),
        "memory": memory_cases(),
    }

    def default(o):
        if isinstance(o, (set, frozenset)):
            return sorted(o)
        raise TypeError(type(o))

    print(json.dumps(rnd(result), indent=1, default=default, sort_keys=True))
