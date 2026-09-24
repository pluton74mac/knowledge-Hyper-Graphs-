"""C3 prototype: append-only candidate queue, structural linter, action log, replay, and the P2 smoke test.

Design C, section 7. One JSONL file holds the queue header, queue items and log entries in append order.
"""
from __future__ import annotations

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jsonschema  # noqa: E402
from referencing import Registry, Resource  # noqa: E402

import c1  # noqa: E402
import hif_codec  # noqa: E402
import semantic  # noqa: E402
import store as st  # noqa: E402

QSCHEMA = json.load(open(os.path.join(HERE, "khg-queue-1.0.0.schema.json"), encoding="utf-8"))
RSCHEMA = json.load(open(os.path.join(HERE, "khg-record-1.0.0.schema.json"), encoding="utf-8"))
VQ = jsonschema.Draft7Validator(QSCHEMA)
VR = jsonschema.Draft7Validator(RSCHEMA)
LINT_VERSION = "khg-lint/1.0.0"
SEV = {"error": "violation", "warning": "warning"}
STATES = {"pending": {"linted", "needs_review", "rejected"},
          "linted": {"accepted", "rejected", "merged", "needs_review"},
          "needs_review": {"accepted", "rejected", "merged"}}
ACTION_TO_STATE = {"accept": "accepted", "reject": "rejected", "merge": "merged", "flag": "needs_review"}


class QueueError(Exception):
    pass


class Queue:
    def __init__(self, queue_id, clock):
        self.lines = [{"kind": "queue-header", "format": "khg-queue/1.0.0", "record_format": c1.RECORD_FORMAT,
                       "queue_id": queue_id, "created_at": clock()}]
        self.clock = clock
        self.queue_id = queue_id
        self.n_items = self.n_log = 0

    # ---------------------------------------------------------------- append
    def _append(self, line):
        errs = [e.message for e in VQ.iter_errors(line)]
        if errs:
            raise QueueError(f"Q-SCHEMA: {errs[:3]}")
        self.lines.append(copy.deepcopy(line))
        return line

    def submit(self, item_kind, payload, *, submitted_by, run=None, doc=None, entities=None):
        """Assigns the qid and, for a hyperedge payload without an id, the provisional id cand:<queue_id>.<seq>."""
        seq = f"{self.n_items + 1:06d}"
        if item_kind == "hyperedge":
            payload = copy.deepcopy(payload)
            cand = f"cand:{self.queue_id}.{seq}"
            if payload.setdefault("id", cand) != cand:
                raise QueueError(f"Q-PAYLOAD: a hyperedge payload id must be {cand}, got {payload['id']}")
        self.n_items += 1
        item = {"kind": "queue-item", "qid": f"q:{self.queue_id}.{seq}", "item_kind": item_kind, "payload": payload,
                "submitted_at": self.clock(), "submitted_by": submitted_by}
        if run:
            item["run"] = run
        if doc:
            item["doc"] = doc
        if entities:
            item["entities"] = entities
        return self._append(item)

    def log(self, target, action, actor, mode="automatic", **kw):
        state = self.state(target)
        new = kw.get("outcome_state") or ACTION_TO_STATE.get(action)
        kw.pop("outcome_state", None)
        if new and new not in STATES.get(state, set()):
            raise QueueError(f"Q-TRANSITION: {target} is {state}, cannot become {new}")
        self.n_log += 1
        prev = [ln["lid"] for ln in self.lines if ln["kind"] == "log-entry" and ln["target"] == target]
        entry = {"kind": "log-entry", "lid": f"l:{self.queue_id}.{self.n_log:06d}", "parent": prev[-1] if prev else None,
                 "target": target, "action": action, "at": self.clock(), "actor": actor, "mode": mode, **kw}
        return self._append(entry)

    # ---------------------------------------------------------------- read
    def item(self, qid):
        return next(ln for ln in self.lines if ln["kind"] == "queue-item" and ln["qid"] == qid)

    def state(self, qid):
        s = "pending"
        for ln in self.lines:
            if ln["kind"] == "log-entry" and ln["target"] == qid:
                if ln["action"] == "lint":
                    s = {"pass": "linted", "flag": "needs_review", "reject": "rejected"}[ln["outcome"]]
                elif ln["action"] in ACTION_TO_STATE:
                    s = ACTION_TO_STATE[ln["action"]]
        return s

    def dump(self, path):
        c1.dump_jsonl(self.lines, path)


# -------------------------------------------------------------------- linter
def lint(queue: Queue, qid: str, schema: c1.Schema, store: st.MemoryStore):
    item = queue.item(qid)
    p = copy.deepcopy(item["payload"])
    findings = []
    if item["item_kind"] == "hyperedge":
        for e in VR.iter_errors(p):
            findings.append({"rule": "R-SCHEMA", "rule_version": LINT_VERSION, "severity": "violation",
                             "path": "/".join(map(str, e.absolute_path)), "message": e.message[:200]})
        if not findings:
            new_ents = {e["id"]: e for e in item.get("entities", [])}
            types = lambda i: (store.entities.get(i) or new_ents.get(i) or {}).get("types")  # noqa: E731
            try:
                p = c1.normalise(p, schema)
            except (KeyError, ValueError) as e:
                findings.append({"rule": "R-DERIVED", "rule_version": LINT_VERSION, "severity": "violation",
                                 "message": f"cannot normalise against the schema: {e}"})
            for f in semantic.check_hyperedge(p, schema, types, canonical=False):
                if f["code"] == "R-ID-RESERVED" and f["where"] == p["id"] and p["id"].startswith("cand:"):
                    continue  # provisional candidate ids live in the reserved cand: namespace by design
                findings.append({"rule": f["code"], "rule_version": LINT_VERSION, "severity": SEV[f["severity"]],
                                 "path": f["where"], "message": f["message"]})
            for b in p["bindings"]:
                v = b["value"]
                if "entity" in v and v["entity"] not in store.entities and v["entity"] not in new_ents:
                    findings.append({"rule": "C-ENTITY-REF", "rule_version": LINT_VERSION, "severity": "violation",
                                     "path": b["bid"], "message": f"unknown entity {v['entity']}"})
            ev_docs = {e["source"].get("doc_sha256") for e in p.get("evidence", []) if e["type"] == "extracted"}
            if ev_docs and item["doc"]["doc_sha256"] not in ev_docs:
                findings.append({"rule": "Q-DOC-HASH", "rule_version": LINT_VERSION, "severity": "violation",
                                 "message": "extracted evidence does not point at the submitted document"})
            if not any(f["severity"] == "violation" for f in findings):
                findings += identity_lints(queue, p, schema, store, qid)
    outcome = ("reject" if any(f["severity"] == "violation" for f in findings)
               else "flag" if any(f["severity"] == "warning" for f in findings) else "pass")
    return queue.log(qid, "lint", {"kind": "linter", "id": LINT_VERSION}, outcome=outcome, findings=findings)


def identity_lints(queue, p, schema, store, qid):
    """Non-blocking identity lints; each finding carries a proposal item submitted to the queue."""
    out = []
    for f in store.find(p["relation"], [{"role": b["role"], "value": b["value"]} for b in p["bindings"]],
                        match="exact"):
        if f["keys"]["content"] == p["keys"]["content"]:
            prop = queue.submit("merge_proposal", {"source": qid, "target": f["id"], "relation": "duplicate"},
                                submitted_by=LINT_VERSION)
            out.append({"rule": "L-DUPLICATE", "rule_version": LINT_VERSION, "severity": "info",
                        "message": f"same content key as {f['id']}: add as evidence", "proposal": prop["qid"]})
    kd = p["keys"].get("key")
    if kd:
        key = schema.relations[p["relation"]]["key"]
        roles = key["roles"]
        kb = [{"role": b["role"], "value": b["value"]} for b in p["bindings"] if b["role"] in roles]
        for f in store.find_by_key(p["relation"], kb):
            if f["keys"]["content"] == p["keys"]["content"]:
                continue
            if not key["temporal"] or semantic._overlap(f.get("valid_time"), p.get("valid_time")):
                sev = "violation" if key["on_collision"] == "reject" else "info"
                out.append({"rule": "L-KEY-COLLISION", "rule_version": LINT_VERSION, "severity": sev,
                            "message": f"key collision with {f['id']}; policy {key['on_collision']}"})
    return out


def accept(queue, qid, store, new_id, actor):
    item = queue.item(qid)
    rec = copy.deepcopy(item["payload"])
    rec["id"], rec["status"] = new_id, "asserted"
    for e in item.get("entities", []):
        store.put(e)
    res = store.put(rec, actor=actor["id"])
    return queue.log(qid, "accept", actor, mode="manual" if actor["kind"] == "person" else "automatic",
                     result=f"{res['id']}@{res['version']}")


def merge(queue, qid, target, store, actor):
    item = queue.item(qid)
    res = store.apply({"op": "add_evidence", "target": target, "evidence": item["payload"]["evidence"]},
                      actor=actor["id"])
    return queue.log(qid, "merge", actor, result=f"{res['id']}@{res['version']}")


def replay(lines, store, new_ids):
    """Re-apply accept/merge actions in log order to a fresh store (C3-R11)."""
    items = {ln["qid"]: ln for ln in lines if ln["kind"] == "queue-item"}
    for ln in lines:
        if ln["kind"] != "log-entry":
            continue
        it = items[ln["target"]]
        if ln["action"] == "accept":
            rec = copy.deepcopy(it["payload"])
            rec["id"], rec["status"] = ln["result"].split("@")[0], "asserted"
            store.put(rec, actor=ln["actor"]["id"])
        elif ln["action"] == "merge":
            store.apply({"op": "add_evidence", "target": ln["result"].split("@")[0],
                         "evidence": it["payload"]["evidence"]}, actor=ln["actor"]["id"])
    return store


# -------------------------------------------------------------------- smoke test (gate clause 3)
def smoke():
    fix = {r.get("id", r["kind"]): r for r in c1.load_jsonl(os.path.join(HERE, "gate.khg.jsonl"))}
    schema_doc = next(r for r in fix.values() if r["kind"] == "relation-schema")
    S = c1.Schema(schema_doc)
    ents = [r for r in fix.values() if r.get("kind") == "entity"]
    clock = st.TickClock()
    store = st.MemoryStore([schema_doc], clock)
    store.put_many(ents)
    q = Queue("p2-smoke", clock)
    f01 = fix["khg:f01-treats"]
    cand = {k: copy.deepcopy(v) for k, v in f01.items()
            if k not in ("version", "recorded_at", "recorded_by", "change", "arity", "keys")}
    cand.pop("id")
    cand["status"] = "candidate"
    for b in cand["bindings"]:
        b.pop("slot", None)
    for e in cand["evidence"]:
        e.pop("event_hash", None)
    cand = c1.normalise(cand, S)
    doc = {"doc": "doc:soc-2024", "doc_sha256": cand["evidence"][0]["source"]["doc_sha256"]}
    run = {"run_id": "r1", "order_id": "o1", "position": 0, "seed": 13}
    it = q.submit("hyperedge", cand, submitted_by="p9-extractor/0.1.0", run=run, doc=doc)
    l1 = lint(q, it["qid"], S, store)
    a1 = accept(q, it["qid"], store, "khg:f01-treats", {"kind": "agent", "id": "p2-smoke-acceptor/1.0.0"})
    # a duplicate from a second run: linted, proposal raised, merged as evidence (never a second fact)
    cand2 = copy.deepcopy(cand)
    ev = copy.deepcopy(cand2["evidence"][0])
    ev["eid"], ev["activity"]["run"] = "ev3", "r2"
    cand2["evidence"] = [ev]
    cand2 = c1.normalise(cand2, S)
    it2 = q.submit("hyperedge", cand2, submitted_by="p9-extractor/0.1.0",
                   run={"run_id": "r2", "order_id": "o2", "position": 3, "seed": 14}, doc=doc)
    l2 = lint(q, it2["qid"], S, store)
    m2 = merge(q, it2["qid"], "khg:f01-treats", store, {"kind": "agent", "id": "p2-smoke-acceptor/1.0.0"})
    # a malformed candidate: role not allowed -> rejected by structural lint, never reaches the store
    bad = copy.deepcopy(cand)
    bad["bindings"][0]["role"] = "remedy"
    it3 = q.submit("hyperedge", bad, submitted_by="p9-extractor/0.1.0",
                   run={"run_id": "r1", "order_id": "o1", "position": 1}, doc=doc)
    l3 = lint(q, it3["qid"], S, store)
    q.dump(os.path.join(HERE, "smoke.queue.jsonl"))
    exported = store.export("khg-jsonl")
    hif = store.export("hif")
    stored = store.get("khg:f01-treats")
    fresh = st.MemoryStore([schema_doc], st.TickClock())
    fresh.put_many(ents)
    # replay uses a clock started at the same instant but not consuming queue ticks: compare content, not tx times
    replayed = replay(q.lines, fresh, None)
    same_content = [st._content(v) for v in store.versions["khg:f01-treats"]] == \
                   [st._content(v) for v in replayed.versions["khg:f01-treats"]]
    V = jsonschema.Draft7Validator(json.load(open(
        "/home/user/knowledge-Hyper-Graphs-/projects/p2-role-aware-hif/research/probes/hif-schema/hif_schema_v0.1.0.json")))
    return {
        "lint_1": (l1["outcome"], [f["rule"] for f in l1["findings"]]),
        "accept_1": a1["result"],
        "lint_2": (l2["outcome"], [f["rule"] for f in l2["findings"]]),
        "merge_2": m2["result"],
        "lint_3": (l3["outcome"], [f["rule"] for f in l3["findings"]][:3]),
        "states": {x: q.state(x) for x in (f"q:p2-smoke.{i:06d}" for i in range(1, 5))},
        "store_has_bad_candidate": store.get("cand:p2-smoke.000004") is not None,
        "f01_versions": len(store.versions["khg:f01-treats"]),
        "f01_evidence_eids": [e["eid"] for e in stored["evidence"]],
        "f01_content_equals_fixture_v1": st._content(store.versions["khg:f01-treats"][0]) == st._content(f01),
        "export_lines": len(exported.splitlines()),
        "hif_valid": not list(V.iter_errors(hif)),
        "replay_reproduces_store": same_content,
        "queue_lines_valid": all(not list(VQ.iter_errors(ln)) for ln in q.lines),
    }


if __name__ == "__main__":
    print(json.dumps(smoke(), indent=1))
