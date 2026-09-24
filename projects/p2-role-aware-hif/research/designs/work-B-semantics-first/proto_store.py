"""Lean prototype of the C2 reference store and the C3 queue, to check the interfaces of design B."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from khg_proto import (KHGError, Schema, _vk, c1_to_hif, canon_value, canonical_doc, cjson, definite_overlap, derived,
                       digest, fact_refines, key_digest, presumed_interval, relate, time_window, vkind)
from khg_semantic import validate_document

ALLOWED = {("fact", a, b) for a, b in [(None, "asserted"), (None, "disputed"), (None, "quoted"), ("asserted", "disputed"),
                                        ("asserted", "superseded"), ("asserted", "retracted"), ("disputed", "asserted"),
                                        ("disputed", "superseded"), ("disputed", "retracted"), ("quoted", "asserted"),
                                        ("quoted", "retracted"), ("superseded", "asserted"), ("retracted", "asserted"),
                                        ("asserted", "asserted"), ("disputed", "disputed"), ("quoted", "quoted")]}
ALLOWED |= {("goal", a, b) for a, b in [(None, "open"), ("open", "open"), ("open", "satisfied"), ("open", "abandoned")]}
ALLOWED |= {("meta", a, b) for a, b in [(None, "asserted"), ("asserted", "retracted")]}
ALLOWED |= {("entity", None, None)}


def _content(r):
    """What identity-preserving comparison looks at (store-assigned fields removed)."""
    x = {k: v for k, v in r.items() if k not in ("version", "recorded_at", "derived")}
    x["bindings"] = sorted((cjson([b["bid"], b["role"], b.get("position"), canon_value(b["value"])]) for b in r.get("bindings", [])))
    return cjson(x)


@dataclass
class StoreInfo:
    name: str
    interface_version: str = "khg-store/1.0.0"
    c1_version: str = "khg-record/1.0.0"
    capabilities: frozenset = frozenset({"history", "as_at", "valid_time", "nesting", "ordered_roles", "special_values",
                                         "goals", "literal_fillers", "key_constraint", "atomic_batch", "pagination"})


class MemoryStore:
    def __init__(self, schema: Schema, clock):
        self.schema, self.clock = schema, clock
        self.versions: dict[str, list[dict]] = {}
        self.seq = 0

    def info(self):
        return StoreInfo("memory")

    # -------------------------------------------------------------------------------------- writes
    def put(self, records, *, expect=None):
        records = [records] if isinstance(records, dict) else list(records)
        now = self.clock()
        staged, receipt = {}, []
        for r in records:
            r = copy.deepcopy(r)
            cur = self._current(r["id"], staged)
            if expect and r["id"] in expect and (cur or {}).get("version", 0) != expect[r["id"]]:
                raise KHGError("KHG-C2-409", f"{r['id']}: expected version {expect[r['id']]}")
            if cur is not None and _content(cur) == _content(r):
                receipt.append((r["id"], cur["version"], "noop"))
                continue
            if r.get("status") == "candidate":
                raise KHGError("KHG-D017", f"{r['id']}: candidates live in the queue, not the store")
            kind = r["kind"]
            if (kind, (cur or {}).get("status"), r.get("status")) not in ALLOWED:
                raise KHGError("KHG-D014", f"{r['id']}: transition {(cur or {}).get('status')} -> {r.get('status')} not allowed")
            if cur is not None and kind in ("fact", "rule"):
                if cur["relation"] != r["relation"] or not fact_refines(self.schema, r, cur):
                    raise KHGError("KHG-D013", f"{r['id']}: new version is not a refinement of version {cur['version']}")
                if cur["status"] in ("superseded", "retracted") and _content({**cur, "status": 0}) != _content({**r, "status": 0}) \
                        and cjson(cur["bindings"]) != cjson(r["bindings"]):
                    raise KHGError("KHG-D013", f"{r['id']}: content of a {cur['status']} fact is frozen")
                new_ev = {e["id"]: cjson(e) for e in r.get("evidence", [])}
                for e in cur.get("evidence", []):
                    if new_ev.get(e["id"]) != cjson(e):
                        raise KHGError("KHG-D013", f"{r['id']}: evidence {e['id']} changed or removed; evidence records are immutable and append-only")
            r["version"] = (cur or {}).get("version", 0) + 1
            r["recorded_at"] = now
            staged[r["id"]] = r
            receipt.append((r["id"], r["version"], "created" if r["version"] == 1 else "versioned"))
        # validate the prospective current state as one document (keys, refs, lifecycle pointers, acyclicity)
        state = {i: v[-1] for i, v in self.versions.items()}
        state.update(staged)
        doc = {"header": {"kind": "header", "khg": "khg-record/1.0.0", "document_id": "store", "schema": {}, "complete": True},
               "records": list(state.values())}
        errs = [e for e in validate_document(doc, self.schema) if e[1] == "violation"]
        if errs:
            raise KHGError(errs[0][0], "; ".join(f"{c} {m}" for c, _, m in errs[:3]))
        for i, r in staged.items():
            self.versions.setdefault(i, []).append(r)
        self.seq += 1
        return {"tx": self.seq, "recorded_at": now, "records": receipt}

    def _current(self, i, staged=None):
        if staged and i in staged:
            return staged[i]
        v = self.versions.get(i)
        return v[-1] if v else None

    # --------------------------------------------------------------------------------------- reads
    def get(self, id, *, as_at=None, version=None):
        vs = self.versions.get(id, [])
        if version is not None:
            return next((copy.deepcopy(v) for v in vs if v["version"] == version), None)
        vs = [v for v in vs if as_at is None or v["recorded_at"] <= as_at]
        return copy.deepcopy(vs[-1]) if vs else None

    def _snapshot(self, as_at):
        out = []
        for i in sorted(self.versions):
            r = self.get(i, as_at=as_at)
            if r is not None:
                out.append(r)
        return out

    def _visible(self, r, kinds, status, valid_at, valid_mode):
        if r["kind"] not in kinds or r.get("status") not in status:
            return False
        if r.get("rank") == "deprecated" or r.get("visibility") == "suppressed":
            return False
        if valid_at is not None and r["kind"] in ("fact", "rule"):
            iv = presumed_interval(self.schema, r)
            if iv["kind"] == "unstated" and valid_mode == "definite":
                return False            # known validity of an undated fact is empty (design §2.12.2)
            t = time_window({"time": valid_at, "precision": 11})[0]
            lo, hi = (iv["s_hi"], iv["e_lo"]) if valid_mode == "definite" else (iv["s_lo"], iv["e_hi"])
            if not (lo <= t < hi):
                return False
        return True

    def incident(self, node, *, role=None, relation=None, kinds=("fact",), status=("asserted",), valid_at=None,
                 valid_mode="definite", as_at=None, limit=None, after=None):
        out = []
        for r in self._snapshot(as_at):
            if r["kind"] == "entity" or (relation and r["relation"] != relation):
                continue
            if not self._visible(r, kinds, status, valid_at, valid_mode):
                continue
            if any((b["value"].get("entity") == node or b["value"].get("fact") == node) and (role is None or b["role"] == role)
                   for b in r["bindings"]):
                if after is None or r["id"] > after:
                    out.append(r)
        out.sort(key=lambda r: r["id"])
        return out[:limit] if limit else out

    def find(self, relation, pattern, *, match="at_least", kinds=("fact",), status=("asserted",), valid_at=None,
             valid_mode="definite", as_at=None):
        out = []
        for r in self._snapshot(as_at):
            if r["kind"] == "entity" or r["relation"] != relation or not self._visible(r, kinds, status, valid_at, valid_mode):
                continue
            pool = list(r["bindings"])
            ok = True
            for p in pattern:
                hit = next((b for b in pool if b["role"] == p["role"] and ("value" not in p or cjson(canon_value(b["value"])) == cjson(canon_value(p["value"])))), None)
                if hit is None:
                    ok = False
                    break
                pool.remove(hit)
            if ok and match == "exact":
                ok = not [b for b in pool if self.schema.usage(relation, b["role"])["slot"] != "meta"]
            if ok:
                out.append(r)
        return sorted(out, key=lambda r: r["id"])

    def by_key(self, relation, key_bindings, *, valid_at=None, valid_mode="definite", as_at=None, status=("asserted",)):
        probe = {"relation": relation, "bindings": [dict(b, bid=f"k{i}") for i, b in enumerate(key_bindings)]}
        kd = key_digest(self.schema, probe)
        rs = [r for r in self._snapshot(as_at) if r["kind"] == "fact" and r["relation"] == relation
              and self._visible(r, ("fact",), status, valid_at, valid_mode) and key_digest(self.schema, r) == kd]
        rank = {"preferred": 0, "normal": 1}
        return sorted(rs, key=lambda r: (rank.get(r.get("rank", "normal"), 2), presumed_interval(self.schema, r)["s_hi"], r["id"]))

    def supersession_walk(self, id, *, direction="forward", as_at=None):
        i = id
        snap = {r["id"]: r for r in self._snapshot(as_at)}
        frm, to = ("khg:superseded", "khg:superseding") if direction == "forward" else ("khg:superseding", "khg:superseded")
        steps, frontier, seen = [], [i], {i}
        while frontier:
            nxt = []
            for f in frontier:
                for m in sorted((r for r in snap.values() if r["kind"] == "meta" and r["relation"] == "khg:supersedes"
                                 and r["status"] == "asserted"), key=lambda r: r["id"]):
                    if any(b["role"] == frm and b["value"]["fact"] == f for b in m["bindings"]):
                        targets = sorted(b["value"]["fact"] for b in m["bindings"] if b["role"] == to)
                        steps.append({"from": f, "via": m["id"], "reason": m["meta"]["reason"], "to": targets})
                        nxt += [t for t in targets if t not in seen]
                        seen |= set(targets)
            frontier = nxt
        return steps

    def export(self, fmt="khg-json", *, as_at=None):
        doc = {"header": {"kind": "header", "khg": "khg-record/1.0.0", "document_id": "export",
                          "schema": {"id": self.schema.doc["id"], "version": self.schema.doc["version"], "sha256": self.schema.sha256()},
                          "snapshot": "current", "complete": True},
               "records": self._snapshot(as_at)}
        if fmt == "khg-json":
            return canonical_doc(doc, self.schema)
        if fmt == "hif":
            return c1_to_hif(doc, self.schema)
        raise KHGError("KHG-C2-400", f"unknown export format {fmt}")


class Queue:
    """Append-only candidate queue + action log. Item state is a fold over the log."""

    def __init__(self, schema: Schema, clock):
        self.schema, self.clock = schema, clock
        self.items, self.log = [], []

    def _log(self, item_id, action, s_before, s_after, actor, **kw):
        prev = next((e["log_id"] for e in reversed(self.log) if e["target"]["item_id"] == item_id), None)
        e = {"kind": "log_entry", "log_id": f"l-{len(self.log) + 1:06d}", "parent_log_id": prev, "target": {"item_id": item_id},
             "action": action, "state_before": s_before, "state_after": s_after, "actor": actor, "at": self.clock()}
        e.update(kw)
        self.log.append(e)
        return e

    def state(self, item_id):
        return next((e["state_after"] for e in reversed(self.log) if e["target"]["item_id"] == item_id), None)

    def submit(self, payload, extraction):
        item = {"kind": "queue_item", "khg_queue": "khg-queue/1.0.0", "item_id": f"q-{len(self.items) + 1:06d}",
                "item_kind": "new_fact", "payload": copy.deepcopy(payload), "extraction": extraction,
                "keys": {k: v for k, v in derived(self.schema, payload).items() if k in ("content_key", "core_key", "key_digest")},
                "submitted_at": self.clock()}
        self.items.append(item)
        self._log(item["item_id"], "submit", None, "pending", {"type": "agent", "id": extraction["extractor"]["name"],
                                                               "version": extraction["extractor"]["version"]})
        return item

    def lint(self, item_id, context_records):
        item = next(i for i in self.items if i["item_id"] == item_id)
        doc = {"header": {"kind": "header", "khg": "khg-record/1.0.0", "document_id": "lint", "schema": {}, "complete": True},
               "records": context_records + [item["payload"]]}
        findings = [{"rule_id": c, "severity": s, "message": m} for c, s, m in validate_document(doc, self.schema, candidate_ok=True)]
        worst = "violation" if any(f["severity"] == "violation" for f in findings) else ("warning" if findings else "pass")
        after = "rejected" if worst == "violation" else "linted"
        return self._log(item_id, "lint", "pending", after, {"type": "linter", "id": "khg-structural-lint", "version": "1.0.0"},
                         rule_set={"id": "structural", "version": "1.0.0"}, findings=findings, outcome=worst)

    def accept(self, item_id, store: MemoryStore, actor):
        item = next(i for i in self.items if i["item_id"] == item_id)
        cand = copy.deepcopy(item["payload"])
        cand["status"] = "asserted"
        rels = [(relate(self.schema, cand, r)[0], r["id"]) for r in store._snapshot(None)
                if r["kind"] == "fact" and r["status"] in ("asserted", "disputed", "quoted")]
        hits = [x for x in rels if x[0] not in ("distinct", "unrelated", "key_timeline")]
        if hits:
            return self._log(item_id, "flag", self.state(item_id), "needs_review", actor, reason=f"identity: {hits}")
        receipt = store.put([cand])
        return self._log(item_id, "accept", self.state(item_id), "accepted", actor,
                         result={"store_ids": [cand["id"]], "tx": receipt["tx"]},
                         before=None, after={"id": cand["id"], "version": receipt["records"][0][1]},
                         plan_hash=digest("khg-plan/1", {"insert": [cand["id"]]}))


# C3 queue states (design §7.2): a fold over the log. Actions that keep the state (verdict, flag without a
# decision, proposals) are moves from a non-terminal state to itself.
QUEUE_TERMINAL = {"accepted", "merged", "rejected", "withdrawn"}
QUEUE_MOVES = {(None, "pending"), ("pending", "linted"), ("pending", "rejected"),
               ("linted", "accepted"), ("linted", "merged"), ("linted", "rejected"), ("linted", "needs_review"),
               ("needs_review", "accepted"), ("needs_review", "merged"), ("needs_review", "rejected")}
QUEUE_MOVES |= {(s, "withdrawn") for s in ("pending", "linted", "needs_review")}
QUEUE_MOVES |= {(s, s) for s in ("pending", "linted", "needs_review")}


def fold_check(items, log):
    """KHG-Q005: an entry's state_before is not the fold's state, or the move is not allowed.
    KHG-Q007: an entry names an item that was never submitted. Returns [(code, log_id, message)]."""
    known = {i["item_id"] for i in items}
    state, out = {}, []
    for e in log:
        iid = e["target"]["item_id"]
        if iid not in known:
            out.append(("KHG-Q007", e["log_id"], f"log names a missing item {iid!r}"))
            continue
        cur = state.get(iid)
        if e["state_before"] != cur:
            out.append(("KHG-Q005", e["log_id"], f"state_before {e['state_before']!r} but the fold gives {cur!r}"))
        elif (cur, e["state_after"]) not in QUEUE_MOVES:
            out.append(("KHG-Q005", e["log_id"], f"move {cur!r} -> {e['state_after']!r} is not allowed"))
        state[iid] = e["state_after"]
    return out
