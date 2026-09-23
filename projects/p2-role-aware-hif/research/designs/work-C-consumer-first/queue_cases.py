"""Queue-level malformed cases (design C, section 8, Q01-Q10): L2 queue schema, L3 state machine."""
import copy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonschema, c1, queue_c3 as Q, malformed as M
lines = c1.load_jsonl("smoke.queue.jsonl")
V = jsonschema.Draft7Validator(Q.QSCHEMA)
def codes(line):
    out = []
    for e in V.iter_errors(line):
        out += [c for c in (M._walk(Q.QSCHEMA, x) for x in M._leaves(e)) if c] or ["Q-SCHEMA"]
    return sorted(set(out))
def semantic_queue(ls):
    out, items, state = [], {l["qid"] for l in ls if l["kind"] == "queue-item"}, {}
    for l in ls:
        if l["kind"] != "log-entry":
            continue
        if l["target"] not in items:
            out.append("Q-LOG-TARGET"); continue
        s = state.get(l["target"], "pending")
        new = ({"pass": "linted", "flag": "needs_review", "reject": "rejected"}.get(l.get("outcome"))
               if l["action"] == "lint" else Q.ACTION_TO_STATE.get(l["action"]))
        if new and new not in Q.STATES.get(s, set()):
            out.append("Q-TRANSITION")
        state[l["target"]] = new or s
    return out
item = next(l for l in lines if l["kind"] == "queue-item" and l["item_kind"] == "hyperedge")
log = next(l for l in lines if l["kind"] == "log-entry")
cases = []
def c(cid, what, expect, line=None, ls=None):
    got = ("L2", codes(line)) if line is not None else ("L3", semantic_queue(ls))
    cases.append((cid, what, expect, got, expect[0] == got[0] and expect[1] in got[1]))
x = copy.deepcopy(item); x.pop("run"); c("Q01", "candidate without run metadata", ("L2", "Q-PAYLOAD"), x)
x = copy.deepcopy(item); x["payload"]["evidence"] = []; c("Q02", "candidate without evidence", ("L2", "Q-PAYLOAD"), x)
x = copy.deepcopy(item); x["payload"]["id"] = "khg:f01"; c("Q03", "candidate payload id outside cand:", ("L2", "Q-PAYLOAD"), x)
x = copy.deepcopy(item); x["payload"]["status"] = "asserted"; c("Q04", "candidate payload status not candidate", ("L2", "Q-PAYLOAD"), x)
x = copy.deepcopy(item); x["run"].pop("order_id"); c("Q05", "run without order_id", ("L2", "Q-RUN"), x)
x = copy.deepcopy(log); x["action"] = "approve"; c("Q06", "log action outside the vocabulary", ("L2", "Q-LOG-ACTION"), x)
x = copy.deepcopy(log); x.pop("outcome"); c("Q07", "lint entry without outcome", ("L2", "Q-SCHEMA"), x)
ls = copy.deepcopy(lines); e = copy.deepcopy(log); e["lid"] = "l:x.999999"; e["target"] = "q:x.999999"; ls.append(e)
c("Q08", "log entry naming a missing queue item", ("L3", "Q-LOG-TARGET"), ls=ls)
ls = copy.deepcopy(lines); rej = next(l for l in ls if l.get("outcome") == "reject"); acc = copy.deepcopy(rej)
acc.update({"lid": "l:x.999998", "action": "accept", "result": "khg:x@1"}); acc.pop("outcome"); acc.pop("findings"); ls.append(acc)
c("Q09", "accept after a lint reject", ("L3", "Q-TRANSITION"), ls=ls)
x = copy.deepcopy(log); x.update({"action": "verdict", "verdict": {"unit": {"core_key": "sha256:x", "event_hash": "sha256:y"}, "label": "other"}})
x.pop("outcome"); x.pop("findings"); c("Q10", "verdict 'other' without a note", ("L2", "Q-SCHEMA"), x)
for r in cases:
    print("ok  " if r[4] else "FAIL", r[0], r[2], "|", r[3], "|", r[1])
print(sum(r[4] for r in cases), "/", len(cases), "queue cases rejected as expected; valid queue file clean:",
      all(not codes(l) for l in lines) and semantic_queue(lines) == [])
import json as _json
with open("queue-cases-results.json", "w", encoding="utf-8") as _f:
    _json.dump([{"id": r[0], "what": r[1], "expect": f"{r[2][0]} {r[2][1]}", "got": f"{r[3][0]} {' '.join(r[3][1])}",
                 "ok": r[4]} for r in cases], _f, ensure_ascii=False, indent=1)
