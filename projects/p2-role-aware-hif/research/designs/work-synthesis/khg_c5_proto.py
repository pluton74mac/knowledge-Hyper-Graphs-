"""Prototype of the parts of C5 that DESIGN §9 makes normative and hand-checkable: derive_memory_gold (the memory-gold
table), the equal-mass calibration bins, the percentile bootstrap, binding_coverage@k and the E12 core-F1 case.
Research code; the scorers themselves are built in step 3 from research/probes/scorers/c5_reference_cases.py."""
from __future__ import annotations

import copy
import random
from fractions import Fraction

import khg_synth as K
import khg_store_proto as P

INCORRECT_REASONS = ("wd:Q41755623",)  # Wikidata "incorrect value", a deprecation reason that marks a revised value


def _tx_minus_one(ts):
    return P._rfc(P._tx(ts) - 1)


def replay_trace(trace, schema, *, upto_step=None):
    """Replay a c4-memory-trace into a fresh prototype store: entities first, then each event at its tx_time with
    actor trace:<trace_id>. Returns (store, {step: tx_time})."""
    events = sorted(trace["events"], key=lambda e: e["step"])
    actor = f"trace:{trace['trace_id']}"
    store = P.ProtoStore(schema, clock=P.Clock(_tx_minus_one(events[0]["tx_time"])), store_id=actor)
    if trace.get("entities"):
        store.put(copy.deepcopy(trace["entities"]), actor=actor, at=_tx_minus_one(events[0]["tx_time"]))
    times = {}
    for ev in events:
        if upto_step is not None and ev["step"] > upto_step:
            break
        if "put" in ev:
            store.put(copy.deepcopy(ev["put"]), actor=actor, at=ev["tx_time"])
        else:
            store.apply(copy.deepcopy(ev["apply"]), actor=actor, at=ev["tx_time"])
        times[ev["step"]] = ev["tx_time"]
    return store, times


def _values(recs, role):
    out = {}
    for r in recs:
        for b in r["bindings"]:
            if b["role"] == role:
                out[K.cjson(K.value_identity(b["value"]))] = K.canon_value(b["value"])
    return out


def derive_memory_gold(trace, question, *, schema, incorrect_reasons=INCORRECT_REASONS):
    """The normative memory-gold table of DESIGN §9 at tau = the tx_time of ask_after_step:
    - V_cur: target values of the facts find_by_key returns under the question's Where at as_at tau; if one of them is
      preferred, only the preferred facts' values;
    - V_old expired: asserted, non-deprecated facts on the key whose possible validity ends at or before as_of;
    - V_old revised: facts on the key that were asserted at some tau' < tau and are superseded or retracted at tau, and
      deprecated facts whose rank_reason names an 'incorrect' reason;
    - V_fut: asserted, non-deprecated facts on the key whose possible validity starts after as_of;
    - disputed: facts on the key that are disputed at tau.
    V_cur is subtracted from the others; answerable is false when V_cur is empty and disputed facts exist."""
    store, times = replay_trace(trace, schema, upto_step=question["ask_after_step"])
    tau = times[question["ask_after_step"]]
    w = question["where"]
    rel, role, key = question["relation"], question["target_role"], question["key"]
    where = P.Where(status=frozenset(w["status"]), rank=frozenset(w["rank"]), as_of=w["as_of"],
                    valid_mode=w["valid_mode"], as_at=tau)
    cur = store.find_by_key(rel, key, where=where)
    pref = [r for r in cur if r.get("rank") == "preferred"]
    v_cur = _values(pref or cur, role)
    probe = {"kind": "hyperedge", "relation": rel,
             "bindings": [{"bid": f"b{n}", "role": p["role"], "value": p["value"]} for n, p in enumerate(key, 1)]}
    kd = K.key_digest(schema, probe)
    on_key = [r for r in store._state(tau).values() if r.get("kind") == "hyperedge" and r["relation"] == rel
              and K.key_digest(schema, r) == kd]
    t = K.parse_instant(w["as_of"]) if w["as_of"] else None
    expired, revised, fut, disputed = {}, {}, {}, {}
    for r in on_key:
        b = K.bounds(schema, r)
        if r["status"] == "asserted" and r.get("rank", "normal") != "deprecated" and t is not None:
            if b["e_hi"] <= t:
                expired.update(_values([r], role))
            elif b["s_lo"] > t:
                fut.update(_values([r], role))
        if r["status"] in ("superseded", "retracted"):
            was = any(v["status"] == "asserted" and P._tx(v["recorded_at"]) < P._tx(tau) for v in store.history(r["id"]))
            if was:
                revised.update(_values([r], role))
        if r.get("rank") == "deprecated" and set(r.get("rank_reason", [])) & set(incorrect_reasons):
            revised.update(_values([r], role))
        if r["status"] == "disputed":
            disputed.update(_values([r], role))
    for d in (expired, revised, fut, disputed):
        for k in list(d):
            if k in v_cur:
                del d[k]
    srt = lambda d: [d[k] for k in sorted(d)]
    stale = [{"value": v, "kind": "expired"} for v in srt(expired)] + \
            [{"value": v, "kind": "revised"} for v in srt(revised) if K.cjson(K.value_identity(v)) not in expired]
    return {"answer": {"values": srt(v_cur)}, "stale_values": stale, "future_values": srt(fut),
            "disputed_values": srt(disputed), "answerable": bool(v_cur) or not disputed, "as_at": tau}


# ------------------------------------------------------------------ calibration: equal-mass bins (C5-HANDCHECK)

def ece(confs, correct, *, bins=15, binning="equal_width"):
    """Top-1 expected calibration error, exact (Fractions).
    equal_width: bins (i/M, (i+1)/M] for i = 0..M-1, with 0 in the first bin.
    equal_mass: sort by confidence; B = min(M, number of distinct confidences); for i = 1..B-1 the i-th cut is the end of
    the run of equal confidences that contains position ceil(i*n/B) (1-based), so ties are never split; empty bins are
    dropped."""
    n = len(confs)
    items = sorted(zip((Fraction(str(c)) if isinstance(c, float) else Fraction(c) for c in confs), correct),
                   key=lambda x: x[0])
    if binning == "equal_width":
        by = {}
        for c, y in items:
            i = max(0, min(bins - 1, -(-c * bins // 1) - 1))
            by.setdefault(i, []).append((c, y))
        groups = [by[i] for i in sorted(by)]
    else:
        B = min(bins, len({c for c, _ in items}))
        cuts = []
        for i in range(1, B):
            pos = -(-i * n // B)            # 1-based position ceil(i*n/B)
            end = pos
            while end < n and items[end][0] == items[pos - 1][0]:
                end += 1                    # extend to the end of the tie run
            cuts.append(end)
        cuts = sorted(set(cuts + [n]))
        groups, start = [], 0
        for c in cuts:
            if c > start:
                groups.append(items[start:c])
                start = c
    total = Fraction(0)
    for g in groups:
        acc = Fraction(sum(y for _, y in g), len(g))
        conf = sum(c for c, _ in g) / len(g)
        total += Fraction(len(g), n) * abs(acc - conf)
    return total


# ------------------------------------------------------------------ bootstrap (C5-IO): indices int(rng.random() * n)

def bootstrap_ci(values, *, resamples=1000, seed=0, alpha=0.05):
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(resamples):
        idx = [int(rng.random() * n) for _ in range(n)]
        means.append(sum(values[i] for i in idx) / n)
    means.sort()
    lo = means[int((alpha / 2) * resamples)]
    hi = means[int((1 - alpha / 2) * resamples) - 1]
    return lo, hi


# ------------------------------------------------------------------ binding_coverage@k (C5-HANDCHECK)

def binding_coverage_at_k(gold_bids, retrieved_units, k):
    """Share of the gold hyperedge's bindings covered by the (edge, bid) back-pointers of the top-k units."""
    covered = set()
    for u in retrieved_units[:k]:
        covered |= {tuple(x) for x in u.get("bids", [])}
    return Fraction(len(covered & set(gold_bids)), len(gold_bids))
