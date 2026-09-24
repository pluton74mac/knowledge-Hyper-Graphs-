"""Writes the C2 conformance scenarios of design A as JSON files, runs them on the prototype MemoryStore
(EARL-style outcomes), then runs the P2 smoke test: queue -> structural lint -> accept -> store -> export.
Run with venv-hif (jsonschema) for the export validation.
"""
import copy
import json
import os
import sys

import jsonschema
from referencing import Registry, Resource

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proto  # noqa: E402
import semantic_proto  # noqa: E402
import store_proto  # noqa: E402

FIX = json.load(open(os.path.join(HERE, "gate-fixture.khg.json"), encoding="utf-8"))
SCHEMA = proto.Schema(json.load(open(os.path.join(HERE, "builtin.schema.json"))),
                      json.load(open(os.path.join(HERE, "gate-demo.schema.json"))))
E = {e["edge"]: e for e in FIX["edges"]}
N = FIX["nodes"]


def ed(eid, **kw):
    e = copy.deepcopy(E[eid])
    e.update(kw)
    return e


f10_asserted = ed("f10", status="asserted")
f10_asserted.pop("superseded-by")
f11_ended = ed("f11", valid={"from": "2019-05", "until": "2021-06"})
f12 = {"edge": "f12", "relation": "chief-executive", "status": "asserted",
       "bindings": [{"role": "organisation", "node": "ex:acme"}, {"role": "person", "node": "ex:ana"}],
       "valid": {"from": "2021-06"}, "evidence": [{"id": "e1", "type": "curated", "source": "doc:press-2021"}]}
f7 = ed("f6", edge="f7", bindings=[dict(b) for b in E["f6"]["bindings"]])
f7["bindings"][0] = {"role": "count", "literal": {"datatype": "quantity", "value": "434335", "unit": "1"}, "direction": "head"}
r1 = {"edge": "r1", "relation": "khg:retracts", "status": "asserted",
      "bindings": [{"role": "khg:retracted", "edge": "f2"},
                   {"role": "khg:reason", "literal": {"datatype": "string", "value": "unsupported"}}],
      "evidence": [{"id": "e1", "type": "curated", "source": "doc:erratum-2025"}]}
g1_bound = ed("g1", status="asserted", evidence=[{"id": "e1", "type": "curated", "source": "doc:enzyme-db-2026"}],
              bindings=[{"role": "catalyst", "node": "ex:TP53", "direction": "head"},
                        {"role": "reaction", "node": "ex:R2", "direction": "tail"}])
N_ENZ = [dict(n) for n in N] + [{"node": "ex:TP53", "types": ["Gene", "Enzyme"], "label": "TP53"}]
N_ENZ = list({n["node"]: n for n in N_ENZ}.values())
T1, T2, T3 = "2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z", "2026-03-01T00:00:00Z"

SC = [
    ("C2-01", "put then get returns the canonical record", [], [{"put": N + [E["f2"]], "at": T1}],
     {"op": "get", "args": {"id": "f2"}}, {"record": proto.canonical_edge(E["f2"], SCHEMA)}),
    ("C2-02", "putting identical content again is a no-op", [], [{"put": N + [E["f2"]], "at": T1}],
     {"op": "put", "args": {"records": [E["f2"]], "at": T2}},
     {"put": {"written": [], "unchanged": ["f2"], "recorded": T2, "conflicts": []}}),
    ("C2-03", "a closed valid interval is a new version; as_at sees the old one", ["as_at"],
     [{"put": N + [E["f11"]], "at": T1}, {"put": [f11_ended], "at": T2}],
     {"op": "get", "args": {"id": "f11", "as_at": T1}}, {"record": proto.canonical_edge(E["f11"], SCHEMA)}),
    ("C2-04", "incident is complete and ordered by edge id", [], [{"put": N + [E["f2"], E["f1"]], "at": T1}],
     {"op": "incident", "args": {"node": "ex:metformin"}}, {"ids": ["f1", "f2"]}),
    ("C2-05", "incident filtered by role", [], [{"put": N + [E["f1"], E["f2"]], "at": T1}],
     {"op": "incident", "args": {"node": "ex:metformin", "role": "agent"}}, {"ids": ["f2"]}),
    ("C2-06", "default status filter excludes superseded versions", [],
     [{"put": N + [f10_asserted], "at": T1}, {"put": [E["f11"], E["f10"], E["s1"]], "at": T2}],
     {"op": "incident", "args": {"node": "ex:acme"}}, {"ids": ["f11"]}),
    ("C2-07", "status filter can include superseded", [],
     [{"put": N + [f10_asserted], "at": T1}, {"put": [E["f11"], E["f10"], E["s1"]], "at": T2}],
     {"op": "incident", "args": {"node": "ex:acme", "status": ["asserted", "superseded"]}}, {"ids": ["f10", "f11"]}),
    ("C2-08", "as_of filters by valid time (an ended fact stays asserted)", ["as_of"],
     [{"put": N + [f11_ended], "at": T1}],
     {"op": "incident", "args": {"node": "ex:acme", "as_of": "2022-01-01"}}, {"ids": []}),
    ("C2-09", "find matches at least the given bindings", [], [{"put": N + [E["f1"], E["f2"]], "at": T1}],
     {"op": "find", "args": {"relation": "treats", "bindings": [{"role": "treatment", "node": "ex:metformin"}]}},
     {"ids": ["f1"]}),
    ("C2-10", "find exact needs the whole binding multiset", [], [{"put": N + [E["f1"]], "at": T1}],
     {"op": "find", "args": {"relation": "treats", "bindings": [{"role": "treatment", "node": "ex:metformin"}],
                             "match": "exact"}}, {"ids": []}),
    ("C2-11", "temporal key: overlapping holders are reported under end-older, not rewritten", ["as_of"],
     [{"put": N + [E["f11"]], "at": T1}],
     {"op": "put", "args": {"records": [f12], "at": T2}},
     {"put": {"written": ["f12"], "unchanged": [], "recorded": T2, "conflicts": [json.dumps(
         {"edges": ["f11", "f12"], "key": proto.key_digest(E["f11"], SCHEMA), "policy": "end-older",
          "relation": "chief-executive"}, sort_keys=True)]}}),
    ("C2-12", "key conflict under reject policy is an error", [], [{"put": N + [E["f6"]], "at": T1}],
     {"op": "put", "args": {"records": [f7], "at": T2}}, {"error": "KHG-S029"}),
    ("C2-13", "supersession is one batch; the walk follows it forward", ["atomic_batch", "nesting"],
     [{"put": N + [f10_asserted], "at": T1}, {"put": [E["f11"], E["f10"], E["s1"]], "at": T2}],
     {"op": "supersession_walk", "args": {"id": "f10"}},
     {"steps": [{"edge": "f11", "via": "s1", "reason": "correction", "depth": 1}]}),
    ("C2-14", "the walk runs backward too", ["atomic_batch", "nesting"],
     [{"put": N + [f10_asserted], "at": T1}, {"put": [E["f11"], E["f10"], E["s1"]], "at": T2}],
     {"op": "supersession_walk", "args": {"id": "f11", "direction": "backward"}},
     {"steps": [{"edge": "f10", "via": "s1", "reason": "correction", "depth": 1}]}),
    ("C2-15", "superseded without a supersession record is rejected", [],
     [{"put": N + [f10_asserted], "at": T1}],
     {"op": "put", "args": {"records": [E["f11"], E["f10"]], "at": T2}}, {"error": "KHG-S022"}),
    ("C2-16", "retracted is terminal", [],
     [{"put": N + [E["f2"]], "at": T1}, {"put": [ed("f2", status="retracted"), r1], "at": T2}],
     {"op": "put", "args": {"records": [ed("f2")], "at": T3}}, {"error": "KHG-S030"}),
    ("C2-17", "candidates never enter the store", [], [{"put": N, "at": T1}],
     {"op": "put", "args": {"records": [ed("f2", status="candidate")], "at": T2}}, {"error": "KHG-S028"}),
    ("C2-18", "bindings of an asserted edge are immutable", [],
     [{"put": N + [{"node": "ex:glipizide", "types": ["Drug"], "label": "glipizide"}, E["f2"]], "at": T1}],
     {"op": "put", "args": {"records": [ed("f2", bindings=E["f2"]["bindings"] + [
         {"role": "agent", "node": "ex:glipizide", "direction": "tail"}])], "at": T2}}, {"error": "KHG-S031"}),
    ("C2-19", "a goal's unbound slot can be bound by a new version", ["special_values"],
     [{"put": N_ENZ + [E["g1"]], "at": T1}, {"put": [g1_bound], "at": T2}],
     {"op": "incident", "args": {"node": "ex:TP53", "role": "catalyst"}}, {"ids": ["g1"]}),
    ("C2-20", "keyset pagination is stable", [], [{"put": N + [E["f1"], E["f2"]], "at": T1}],
     {"op": "incident", "args": {"node": "ex:metformin", "after": "f1", "limit": 1}}, {"ids": ["f2"]}),
    ("C2-21", "the unbound goal is visible only when goals are asked for", ["special_values"],
     [{"put": N + [E["g1"]], "at": T1}],
     {"op": "incident", "args": {"node": "ex:R2", "status": ["goal"]}}, {"ids": ["g1"]}),
    ("C2-22", "nesting: incident on an edge id returns the facts about it", ["nesting"],
     [{"put": N + [E["f1"], E["f9"]], "at": T1}],
     {"op": "incident", "args": {"edge": "f1"}}, {"ids": ["f9"]}),
]

if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "scenarios"), exist_ok=True)
    report = []
    for sid, title, req, given, when, then in SC:
        sc = {"id": sid, "title": title, "requires": req, "schema": "gate-demo/1.0.0",
              "given": given, "when": when, "then": then}
        json.dump(sc, open(os.path.join(HERE, "scenarios", sid + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        outcome, got = store_proto.run_scenario(sc, SCHEMA, "gate-demo/1.0.0")
        report.append({"test": sid, "outcome": outcome})
        print(f"  {outcome:8} {sid} {title}" + ("" if outcome == "passed" else f"  got={json.dumps(got)[:300]}"))
    print("conformance:", sum(r["outcome"] == "passed" for r in report), "/", len(report), "passed")

    # ------------------------------------------------------------------ smoke test (gate clause 3)
    print("smoke test: queue -> structural lint -> accept -> store -> export")
    cand = copy.deepcopy(E["f1"])
    cand["status"] = "candidate"
    keys = {"content": proto.content_key(cand, SCHEMA), "core": proto.content_key(cand, SCHEMA, "core"),
            "events": sorted(proto.event_key(cand, ev, SCHEMA) for ev in cand["evidence"] if ev["type"] == "extracted")}
    queue = [{"metadata": {"khg-profile": "1.0.0", "khg-schema": "gate-demo/1.0.0", "queue": "smoke"}},
             {"item": "q1", "at": T1, "payload": cand, "keys": keys,
              "nodes": [n for n in N if n["node"] in ("ex:metformin", "ex:T2DM", "ex:adults")]}]
    lint = semantic_proto.validate({"metadata": queue[0]["metadata"], "nodes": queue[1]["nodes"],
                                    "edges": [queue[1]["payload"]]}, SCHEMA)
    violations = [x for x in lint if x[0].startswith("KHG-S")]
    queue.append({"log": "l1", "at": T1, "item": "q1", "actor": {"agent": "khg-lint", "version": "1.0.0"},
                  "action": "flag", "rule": "KHG-L003", "severity": "info", "path": "/bindings",
                  "message": f"structural lint: {len(violations)} violations"})
    st = store_proto.MemoryStore(SCHEMA, "gate-demo/1.0.0")
    accepted = dict(cand, status="asserted")
    res = st.put(queue[1]["nodes"] + [accepted], at=T2)
    queue.append({"log": "l2", "at": T2, "item": "q1", "actor": {"agent": "person:reviewer-1"}, "action": "accept",
                  "reason": "no violations", "after": {"edge": "f1", "recorded": res["recorded"]}})
    khg = st.export("khg")
    hif = st.export("hif")
    PROBES = "/home/user/knowledge-Hyper-Graphs-/projects/p2-role-aware-hif/research/probes"
    HIF = json.load(open(os.path.join(PROBES, "hif-schema", "hif_schema_v0.1.0.json")))
    reg = Registry().with_resource(HIF["$id"], Resource.from_contents(HIF))
    prof = json.load(open(os.path.join(HERE, "schemas", "khg-hif-profile-1.0.0.json")))
    qs = json.load(open(os.path.join(HERE, "schemas", "khg-queue-1.0.0.json")))
    doc_s = json.load(open(os.path.join(HERE, "schemas", "khg-document-1.0.0.json")))
    errs = list(jsonschema.Draft7Validator(prof, registry=reg).iter_errors(hif))
    qerrs = [e for ln in queue for e in jsonschema.Draft7Validator(qs).iter_errors(ln)]
    derrs = list(jsonschema.Draft7Validator(doc_s).iter_errors(khg))
    roles = sorted(i["attrs"]["role"] for i in hif["incidences"])
    back = proto.from_hif(hif, SCHEMA)
    print(f"  lint violations={len(violations)} put={res['written']} queue-lines-valid={not qerrs} "
          f"khg-export-valid={not derrs} hif-export-profile-valid={not errs} roles={roles} "
          f"hif->khg equals khg export={back == khg}")
    assert not violations and not errs and not qerrs and not derrs and back == khg
