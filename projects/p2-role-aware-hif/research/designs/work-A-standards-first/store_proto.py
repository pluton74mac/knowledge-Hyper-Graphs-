"""Prototype of the C2 reference store (MemoryStore) of design A, a scenario runner, and the P2 smoke test.

Not the package: enough to show that the interface's semantics are implementable and consistent.
"""
from __future__ import annotations

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proto  # noqa: E402
import semantic_proto  # noqa: E402

INTERFACE_VERSION = "1.0.0"
TRANSITIONS = {  # (previous status or None for a new edge) -> allowed new statuses
    None: {"asserted", "goal"},
    "asserted": {"asserted", "superseded", "retracted"},
    "goal": {"goal", "asserted", "retracted"},
    "superseded": {"superseded"},
    "retracted": {"retracted"},
}


class StoreError(ValueError):
    def __init__(self, code, msg):
        super().__init__(f"{code} {msg}")
        self.code = code


def _content(r):
    return {k: v for k, v in r.items() if k != "recorded"}


def _instant(t):
    return semantic_proto._instant(t)


def _valid_at(e, t):
    v = e.get("valid", {})
    t = _instant(t)
    return ("from" not in v or _instant(v["from"]) <= t) and ("until" not in v or t < _instant(v["until"]))


def _overlap(a, b):
    va, vb = a.get("valid", {}), b.get("valid", {})
    lo = max(_instant(va.get("from", "0000")), _instant(vb.get("from", "0000")))
    hi = min(_instant(va.get("until", "9999")), _instant(vb.get("until", "9999")))
    return lo < hi


class MemoryStore:
    interface_version = INTERFACE_VERSION
    format_version = "1.0.0"
    capabilities = frozenset({"as_at", "as_of", "nesting", "literals", "ordered", "special_values", "atomic_batch"})

    def __init__(self, schema: proto.Schema, schema_id: str):
        self.schema, self.schema_id = schema, schema_id
        self.versions = {}   # edge id -> [versions in recorded order]
        self.nodes = {}
        self.clock = 0

    # ------------------------------------------------------------------ reads
    def _current(self, as_at=None):
        out = {}
        for eid, vs in self.versions.items():
            vs = [v for v in vs if as_at is None or v["recorded"] <= as_at]
            if vs:
                out[eid] = vs[-1]
        return out

    def get(self, id, *, kind="edge", as_at=None):
        if kind == "node":
            return copy.deepcopy(self.nodes.get(id))
        return copy.deepcopy(self._current(as_at).get(id))

    def _select(self, edges, status, as_of, limit, after):
        res = [e for eid, e in sorted(edges.items()) if e["status"] in status and
               (as_of is None or _valid_at(e, as_of)) and (after is None or eid > after)]
        return copy.deepcopy(res[:limit] if limit else res)

    def incident(self, node=None, *, edge=None, role=None, relation=None, status=("asserted",), as_of=None,
                 as_at=None, limit=None, after=None):
        if (node is None) == (edge is None):
            raise TypeError("exactly one of node= or edge=")
        kind, x = ("node", node) if node is not None else ("edge", edge)
        cur = {eid: e for eid, e in self._current(as_at).items()
               if (relation is None or e["relation"] == relation) and
               any(b.get(kind) == x and (role is None or b["role"] == role) for b in e["bindings"])}
        return self._select(cur, status, as_of, limit, after)

    def find(self, relation, bindings, *, match="at_least", status=("asserted",), as_of=None, as_at=None,
             limit=None, after=None):
        want = sorted(json.dumps(proto.binding_key(b, "position" in b), sort_keys=True) for b in bindings)
        cur = {}
        for eid, e in self._current(as_at).items():
            if e["relation"] != relation:
                continue
            have = sorted(json.dumps(proto.binding_key({k: v for k, v in b.items() if k != "direction"}, "position" in b),
                                     sort_keys=True) for b in e["bindings"])
            want_nd = sorted(json.dumps({k: v for k, v in json.loads(w).items() if k != "direction"}, sort_keys=True)
                             for w in want)
            if match == "exact":
                ok = have == want_nd
            else:
                pool = list(have)
                ok = True
                for w in want_nd:
                    if w in pool:
                        pool.remove(w)
                    else:
                        ok = False
                        break
            if ok:
                cur[eid] = e
        return self._select(cur, status, as_of, limit, after)

    def supersession_walk(self, id, *, direction="forward", as_at=None):
        cur = self._current(as_at)
        links = []
        for eid, e in sorted(cur.items()):
            if e["relation"] == "khg:supersedes" and e["status"] == "asserted":
                new = [b["edge"] for b in e["bindings"] if b["role"] == "khg:superseding"][0]
                old = [b["edge"] for b in e["bindings"] if b["role"] == "khg:superseded"][0]
                reason = [b["literal"]["value"] for b in e["bindings"] if b["role"] == "khg:reason"][0]
                links.append((old, new, eid, reason))
        steps, frontier, seen, depth = [], [id], {id}, 0
        while frontier:
            depth += 1
            nxt = []
            for x in frontier:
                for old, new, via, reason in links:
                    a, b = (old, new) if direction == "forward" else (new, old)
                    if a == x and b not in seen:
                        seen.add(b)
                        steps.append({"edge": b, "via": via, "reason": reason, "depth": depth})
                        nxt.append(b)
            frontier = sorted(nxt)
        return steps

    def export(self, format="khg", *, as_at=None, history=False):
        if history:
            edges = [v for vs in self.versions.values() for v in vs if as_at is None or v["recorded"] <= as_at]
        else:
            edges = list(self._current(as_at).values())
        doc = proto.canonical_doc({"metadata": {"khg-profile": "1.0.0", "khg-schema": self.schema_id},
                                   "nodes": list(self.nodes.values()), "edges": edges}, self.schema)
        return proto.to_hif(doc, self.schema) if format == "hif" else doc

    # ------------------------------------------------------------------ write
    def put(self, records, *, at=None):
        records = [records] if isinstance(records, dict) else list(records)
        self.clock += 1
        at = at or f"2026-01-01T00:00:{self.clock:02d}Z"
        nodes = [r for r in records if "node" in r and "edge" not in r]
        edges = [proto.canonical_edge(r, self.schema) for r in records if "edge" in r]
        cur = self._current()
        for e in edges:
            if e["status"] == "candidate":
                raise StoreError("KHG-S028", f"{e['edge']}: candidates stay in the queue (C3)")
        # semantic validation of the batch in the scope of the store; lifecycle rules see the batch plus
        # the current versions it does not replace
        scope = {**cur, **{e["edge"]: e for e in edges}}
        batch_doc = {"metadata": {"khg-profile": "1.0.0", "khg-schema": self.schema_id},
                     "nodes": list({**self.nodes, **{n["node"]: n for n in nodes}}.values()),
                     "edges": list(scope.values())}
        errs = semantic_proto.validate(batch_doc, self.schema)
        if errs:
            raise StoreError(errs[0][0], errs[0][2])
        written, unchanged, conflicts = [], [], []
        for e in edges:
            prev = cur.get(e["edge"])
            if prev is not None and _content(prev) == _content(e):
                unchanged.append(e["edge"])
                continue
            if e["status"] not in TRANSITIONS[prev["status"] if prev else None]:
                raise StoreError("KHG-S030", f"{e['edge']}: {prev['status'] if prev else 'new'} -> {e['status']}")
            if prev is not None:
                same = prev["relation"] == e["relation"] and (
                    prev["bindings"] == e["bindings"] or prev["status"] == "goal")
                if not same:
                    raise StoreError("KHG-S031", f"{e['edge']}: relation and bindings are immutable")
        final = {**cur, **{e["edge"]: e for e in edges}}
        for e in edges:
            kd = proto.key_digest(e, self.schema)
            if e["status"] != "asserted" or kd is None:
                continue
            key = self.schema.relations[e["relation"]]["key"]
            for oid, o in sorted(final.items()):
                if oid == e["edge"] or o["status"] != "asserted" or o["relation"] != e["relation"]:
                    continue
                if proto.key_digest(o, self.schema) == kd and (not key.get("temporal") or _overlap(e, o)):
                    policy = key.get("on-collision", "flag")
                    if policy == "reject":
                        raise StoreError("KHG-S029", f"key conflict {e['edge']} / {oid}")
                    conflicts.append({"relation": e["relation"], "key": kd, "edges": sorted([e["edge"], oid]),
                                      "policy": policy})
        for n in nodes:
            self.nodes[n["node"]] = copy.deepcopy(n)
        for e in edges:
            if e["edge"] in unchanged:
                continue
            v = copy.deepcopy(e)
            v["recorded"] = at
            self.versions.setdefault(e["edge"], []).append(v)
            written.append(e["edge"])
        return {"written": sorted(written), "unchanged": sorted(unchanged), "recorded": at,
                "conflicts": sorted({json.dumps(c, sort_keys=True) for c in conflicts})}


# ---------------------------------------------------------------------- scenario runner (C2 conformance)
def run_scenario(sc, schema, schema_id, factory=MemoryStore):
    st = factory(schema, schema_id)
    if not set(sc.get("requires", [])) <= st.capabilities:
        return "inapplicable", None
    try:
        for step in sc["given"]:
            st.put(step["put"], at=step.get("at"))
        op = sc["when"]
        args = dict(op.get("args", {}))
        if op["op"] == "put":
            res = st.put(args.pop("records"), **args)
        else:
            res = getattr(st, op["op"])(**args)
    except StoreError as e:
        got = {"error": e.code}
    else:
        if op["op"] in ("incident", "find"):
            got = {"ids": [r["edge"] for r in res]}
        elif op["op"] == "get":
            got = {"record": res and {k: v for k, v in res.items() if k != "recorded"}}
        elif op["op"] == "supersession_walk":
            got = {"steps": res}
        elif op["op"] == "put":
            got = {"put": res}
        else:
            got = {"result": res}
    want = sc["then"]
    ok = all(got.get(k) == v for k, v in want.items())
    return ("passed" if ok else "failed"), got
