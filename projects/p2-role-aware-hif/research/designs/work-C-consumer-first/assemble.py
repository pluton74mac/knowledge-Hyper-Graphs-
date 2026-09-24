"""Assemble ../design-C-consumer-first.md from doc-0..doc-6.md, filling every placeholder from validated artefacts.

Everything inserted is either an artefact that passed the validators (run_checks.py, malformed.py, conformance.py,
queue_c3.py, queue_cases.py, migrate_sample.py) or is built and validated here (schema example, C4 items, cyclic
schema). The script fails if a placeholder is left or a quoted count disagrees with the artefacts.
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "design-C-consumer-first.md")
sys.path.insert(0, HERE)
import jsonschema  # noqa: E402
from referencing import Registry, Resource  # noqa: E402

import c1  # noqa: E402
import gate_fixture  # noqa: E402
import migrate_sample  # noqa: E402
import semantic  # noqa: E402


def L(p):
    with open(os.path.join(HERE, p), encoding="utf-8") as f:
        return json.load(f)


def fmt(o, lvl=0, width=116):
    s = json.dumps(o, ensure_ascii=False, separators=(", ", ": "))
    if len(s) + 2 * lvl <= width or not isinstance(o, (dict, list)) or not o:
        return s
    pad = "  " * (lvl + 1)
    if isinstance(o, dict):
        inner = ",\n".join(f"{pad}{json.dumps(k, ensure_ascii=False)}: {fmt(v, lvl + 1, width)}" for k, v in o.items())
        return "{\n" + inner + "\n" + "  " * lvl + "}"
    inner = ",\n".join(pad + fmt(v, lvl + 1, width) for v in o)
    return "[\n" + inner + "\n" + "  " * lvl + "]"


ORDER = ["kind", "id", "version", "recorded_at", "recorded_by", "change", "schema", "relation", "status", "rank",
         "rank_reason", "visibility", "valid_time", "bindings", "confidence", "evidence", "superseded_by",
         "superseded", "superseding", "reason", "reason_detail", "arity", "keys", "types", "label", "aliases",
         "same_as", "format", "content", "as_at", "created_at", "created_by", "title", "description", "schemas"]
B_ORDER = ["bid", "role", "slot", "direction", "position", "value"]
E_ORDER = ["eid", "type", "mode", "source", "selectors", "reference", "activity", "binding_refs", "confidence", "event_hash"]


def ordered(d, order):
    out = {k: d[k] for k in order if k in d}
    out.update({k: d[k] for k in d if k not in out})
    return out


def logical(r):
    r = ordered(r, ORDER)
    if "bindings" in r:
        r["bindings"] = [ordered(b, B_ORDER) for b in r["bindings"]]
    if "evidence" in r:
        r["evidence"] = [ordered(e, E_ORDER) for e in r["evidence"]]
    return r


def block(o, lang="json"):
    return f"```{lang}\n{fmt(o)}\n```"


FIX = c1.load_jsonl(os.path.join(HERE, "gate.khg.jsonl"))
BY_ID = {r.get("id", r["kind"]): r for r in FIX}
V_REC = jsonschema.Draft7Validator(L("khg-record-1.0.0.schema.json"))
META = L("khg-relation-schema-1.0.0.schema.json")
V_META = jsonschema.Draft7Validator(META)


def rec_block(i):
    r = BY_ID[i]
    assert not list(V_REC.iter_errors(r)), i
    return block(logical(r))


# ------------------------------------------------------------------ schema example (subset) + P6 hypergraph
def schema_example():
    keep = ["treats", "co_administration_causes", "married", "position_held", "chief_executive", "reported_in"]
    S = copy.deepcopy(gate_fixture.SCHEMA)
    rels = [r for r in S["relations"] if r["id"] in keep]
    for r in rels:
        if r["id"] == "reported_in":
            r["roles"][0]["fillers"] = {"hyperedge": {"relations": ["treats"]}}
    roles_used = sorted({u["role"] for r in rels for u in r["roles"]})
    types_used = set()
    for r in rels:
        for u in r["roles"]:
            types_used |= set(u["fillers"].get("entity_types", []))
    types = {t["id"]: t for t in S["entity_types"]}
    closure = set()
    stack = list(types_used)
    while stack:
        t = stack.pop()
        if t not in closure:
            closure.add(t)
            stack.extend(types[t].get("parents", []))
    doc = {"kind": "relation-schema", "format": S["format"], "id": "p2-gate-example", "version": "1.0.0",
           "label": "six relation types from the P2 gate schema",
           "entity_types": [t for t in S["entity_types"] if t["id"] in closure],
           "confidence_scales": S["confidence_scales"],
           "time_model": {"from_role": "start_time", "to_role": "end_time"},
           "roles": [r for r in S["roles"] if r["id"] in roles_used],
           "relations": rels}
    errs = [e.message for e in V_META.iter_errors(doc)]
    findings = semantic.check_schema_doc(doc)
    assert not errs and not findings, (errs, findings)
    return doc


def schema_hypergraph(doc, slots=("core", "qualifier", "time")):
    hes = {r["id"]: sorted(u["role"] for u in r["roles"] if u["slot"] in slots) for r in doc["relations"]}
    return {"vertices": sorted({v for vs in hes.values() for v in vs}), "hyperedges": dict(sorted(hes.items()))}


def gyo_acyclic(hes):
    edges = [set(v) for v in hes.values()]
    changed = True
    while changed and edges:
        changed = False
        count = {}
        for e in edges:
            for v in e:
                count[v] = count.get(v, 0) + 1
        for e in edges:
            lone = {v for v in e if count[v] == 1}
            if lone:
                e -= lone
                changed = True
        keep = []
        for i, e in enumerate(edges):
            if not e or any(i != j and e <= f and (e != f or j < i) for j, f in enumerate(edges)):
                changed = True
                continue
            keep.append(e)
        edges = keep
    return not edges


def cyclic_schema():
    doc = {"kind": "relation-schema", "format": "khg-relation-schema/1.0.0", "id": "cyclic", "version": "1.0.0",
           "entity_types": [{"id": "Thing", "label": "thing"}],
           "roles": [{"id": x, "label": x} for x in ("a", "b", "c")],
           "relations": [{"id": r, "label": r, "kind": "fact",
                          "roles": [{"role": x, "slot": "core", "fillers": {"entity_types": ["Thing"]}, "min": 1, "max": 1}
                                    for x in xs]}
                         for r, xs in (("r1", "ab"), ("r2", "bc"), ("r3", "ca"))]}
    assert not list(V_META.iter_errors(doc)) and not semantic.check_schema_doc(doc)
    hg = schema_hypergraph(doc)
    assert not gyo_acyclic(hg["hyperedges"]), "the triangle must be alpha-cyclic"
    ex = schema_hypergraph(schema_example())
    return hg, gyo_acyclic(ex["hyperedges"])


# ------------------------------------------------------------------ HIF pieces
FULL = L("gate-full.hif.json")
DIRECTED = L("gate-directed.hif.json")


def hif_excerpt():
    incs = [i for i in FULL["incidences"] if i["edge"] in ("khg:f02-trial", "khg:f03-regulates", "khg:f05-route", "khg:s01")]
    lit = next(n for n in FULL["nodes"] if n["attrs"]["khg-kind"] == "literal" and n["attrs"]["label"] == "AC 857")
    ref = next(n for n in FULL["nodes"] if n["node"] == "khg-ref:khg:f02-trial")
    ent = next(n for n in FULL["nodes"] if n["node"] == "x:Москва")
    goal = next(e for e in FULL["edges"] if e["edge"] == "khg:f14-goal")
    sup = next(e for e in FULL["edges"] if e["edge"] == "khg:s01")
    married = next(e for e in FULL["edges"] if e["edge"] == "khg:f09-married")
    lines = ["// incidences: f02 (metformin twice, both tail), f03 (TP53 tail and head), f05 (YYZ at 0 and 2), s01",
             '"incidences": [']
    lines += [f"  {json.dumps(i, ensure_ascii=False, separators=(', ', ': '))}," for i in incs]
    lines[-1] = lines[-1].rstrip(",")
    lines += ["]", "", "// nodes: a literal node shared by value, a hyperedge mirror node, an isolated entity",
              json.dumps(lit, ensure_ascii=False, separators=(", ", ": ")),
              json.dumps(ref, ensure_ascii=False, separators=(", ", ": ")),
              json.dumps(ent, ensure_ascii=False, separators=(", ", ": ")),
              "", "// edges: special values ride in khg-special-bindings; the goal edge has no incidences at all",
              fmt({"edge": married["edge"], "attrs": {k: married["attrs"][k] for k in
                                                      ("relation", "khg-kind", "khg-status", "khg-rank", "khg-rank-reason", "khg-special-bindings")}}),
              fmt(goal), fmt(sup)]
    return "```jsonc\n" + "\n".join(lines) + "\n```\n\n(The `khg:f09-married` edge is shown with six of its attrs; " \
           "the full record is in the complete file\nbelow. Everything else is shown whole.)"


def pretty_full():
    with open(os.path.join(HERE, "gate-full.hif.pretty.json"), encoding="utf-8") as f:
        t = f.read()
    assert json.loads(t) == FULL
    return t


# ------------------------------------------------------------------ evidence, scenarios, queue, smoke
def lib_evidence():
    d = L("run_checks.out.json")["library_evidence"]
    f, g = d["full"], d["directed"]
    rows = [
        "| | Full fixture (undirected, some directions) | Directed slice |",
        "|---|---|---|",
        f"| incidence records in (all role-labelled) | {f['input_incidence_records_with_role']} | {g['input_incidence_records_with_role']} |",
        f"| `xgi.read_hif` -> `xgi.write_hif`: records out / records with a role | {f['xgi: incidence records out']} / {f['xgi.read_hif->write_hif: records with role']} | {g['xgi: incidence records out']} / {g['xgi.read_hif->write_hif: records with role']} |",
        f"| XGI keeps `metadata` | {'yes' if f['xgi: metadata keys kept'] else 'no'} | {'yes' if g['xgi: metadata keys kept'] else 'no'} |",
        f"| `hnx.from_hif` -> `hnx.to_hif(network_type=<input>)` returns | `None` (see below) | a dict with {g['hnx: incidence records out']} records, {g['hnx: records with role']} with a role; metadata keys {g['hnx: metadata keys out']} |",
        f"| HyperNetX second generation (`from_hif` of its own output, then `to_hif`) | n/a | `{g['hnx second generation to_hif returned']}` |",
    ]
    return "\n".join(rows)


def scenario(sid):
    sc = next(s for s in L("conformance-scenarios.json")["scenarios"] if s["id"] == sid)
    res = next(r for r in L("conformance-results.json")["full"] if r["test"] == sid)
    assert res["outcome"] == "passed"
    return block(sc)


QLINES = c1.load_jsonl(os.path.join(HERE, "smoke.queue.jsonl"))


def queue_header():
    return block(ordered(QLINES[0], ["kind", "format", "queue_id", "record_format", "created_at"]))


def queue_item():
    it = next(ln for ln in QLINES if ln["kind"] == "queue-item" and ln["item_kind"] == "hyperedge")
    it = dict(it)
    it["payload"] = logical(it["payload"])
    it["run"] = ordered(it["run"], ["run_id", "order_id", "position", "seed", "permutation"])
    return block(ordered(it, ["kind", "qid", "item_kind", "submitted_at", "submitted_by", "run", "doc", "payload"]))


def smoke_lines():
    out = []
    for ln in QLINES[1:]:
        if ln["kind"] == "queue-item" and ln["item_kind"] == "hyperedge":
            out.append(f"// queue item {ln['qid']}: a hyperedge candidate ({ln['payload']['id']}), shown in full above for the first one")
            continue
        o = ordered(ln, ["kind", "lid", "qid", "parent", "target", "item_kind", "action", "outcome", "findings",
                         "result", "payload", "at", "actor", "mode", "submitted_at", "submitted_by"])
        out.append(json.dumps(o, ensure_ascii=False, separators=(", ", ": ")))
    return "```jsonc\n" + "\n".join(out) + "\n```"


def smoke_result():
    d = L("smoke.out.json")
    rows = ["| Assertion | Result |", "|---|---|",
            f"| first candidate: structural lint outcome, findings | `{d['lint_1'][0]}`, {d['lint_1'][1] or 'none'} |",
            f"| accepted as | `{d['accept_1']}` |",
            f"| stored content equals the fixture record | {d['f01_content_equals_fixture_v1']} |",
            f"| second-run duplicate: lint outcome, findings | `{d['lint_2'][0]}`, {', '.join(d['lint_2'][1])} (with a merge proposal) |",
            f"| merged into | `{d['merge_2']}` (evidence now {', '.join(d['f01_evidence_eids'])}; {d['f01_versions']} versions, one fact) |",
            f"| malformed candidate: lint outcome, rules | `{d['lint_3'][0]}`, {', '.join(d['lint_3'][1])} |",
            f"| malformed candidate reached the store | {d['store_has_bad_candidate']} |",
            f"| final states | {', '.join(f'`{k}` {v}' for k, v in d['states'].items())} |",
            f"| `export('khg-jsonl')` lines; `export('hif')` valid against the vendored schema | {d['export_lines']}; {d['hif_valid']} |",
            f"| replay of the log into a fresh store reproduces the store | {d['replay_reproduces_store']} |",
            f"| every queue line valid against `khg-queue-1.0.0` | {d['queue_lines_valid']} |"]
    assert d["lint_1"][0] == "pass" and d["lint_3"][0] == "reject" and d["hif_valid"] and d["replay_reproduces_store"]
    assert not d["store_has_bad_candidate"] and d["queue_lines_valid"] and d["f01_content_equals_fixture_v1"]
    return "\n".join(rows)


# ------------------------------------------------------------------ malformed tables
SRC = {
    "M01": "R02 case 34", "M02": "R01 V19; R02 case 35; R03 c22", "M03": "R02 case 36", "M04": "RFC 8259 §8.2",
    "M05": "R01 V01; R02 case 31", "M06": "R01 V02; R02 case 05", "M07": "R02 case 04", "M08": "R01 V03; R02 case 11",
    "M09": "R01 V04", "M10": "R01 V05; R02 case 12", "M11": "R01 V06; R02 cases 18-20", "M12": "R02 case 15; F10",
    "M13": "R03 D8, c04", "M14": "R01 V07", "M15": "R01 V07; F15", "M16": "R01 V08", "M17": "R01 V09",
    "M18": "R01 V09; §4.2", "M19": "R03 D7, c20", "M20": "R03 D6; R01 D-13", "M21": "R01 V12; R02 case 23; R03 c14",
    "M22": "R01 V14", "M23": "R01 C1-R64; F3", "M24": "R01 V16; R03 D5, c19", "M25": "R01 V10 (as refined in §4.2)",
    "M26": "R01 V17; R02 case 28", "M27": "R02 case 29", "M28": "R01 V18", "M29": "R01 D-09", "M30": "R01 V22",
    "M40": "§2.1", "M41": "R01 V14", "M42": "R01 C1-R04; R02 cases 16, 21", "M43": "R03 c13; F11",
    "M44": "§2.2", "M45": "R01 C1-R06", "M46": "R01 C1-R52; R04 M2", "M47": "R01 V26", "M48": "R01 V26",
    "M49": "R01 V26", "M50": "R01 V26", "M51": "R04 M2", "M52": "R01 V36", "M53": "§2.5", "M54": "R01 C1-R36",
    "M55": "F11; R04 O8", "M56": "F11; R04 M6", "M57": "R01 V30", "M58": "R01 V15", "M59": "R01 C1-R47, D-07",
    "M60": "R01 V21", "M61": "R01 V22", "M62": "R01 V23", "M63": "R01 V24", "M64": "R01 V25", "M65": "R01 V25",
    "M66": "R01 V27", "M67": "R01 V28", "M68": "R01 V29", "M69": "R01 V34", "M70": "R01 V35", "M71": "R01 V33",
    "M72": "R01 V38", "M73": "R01 C1-R15", "M74": "R01 C1-R14, C1-R15", "M75": "R01 C1-R34; R04 M1",
    "M76": "R01 V32", "M77": "R01 V37", "M78": "R01 V37", "M79": "F8", "M80": "R01 V17", "M81": "§2.2",
    "M82": "R01 V41", "M83": "R01 V41", "M84": "R01 V42", "M85": "F9; R01 D-18", "M90": "R01 V45", "M91": "R01 V43",
    "M92": "R01 V44", "M93": "R01 V44", "M94": "R04 M3", "M95": "R01 V44", "M96": "R01 V46", "M97": "F4",
    "M98": "§3.2", "M99": "R01 V40",
    "Q01": "R01 V47", "Q02": "R01 V47", "Q03": "§7.2", "Q04": "F9", "Q05": "PLAN §4 (P9)", "Q06": "R01 V48",
    "Q07": "§7.4", "Q08": "R01 V48", "Q09": "R01 C3-R05", "Q10": "R04 M7",
}
INPUT = {"hif": "HIF", "c1": "container"}


def malformed_table():
    rows = L("malformed-results.json")
    import malformed as M
    kinds = {c[0]: c[1] for c in M.CASES}
    assert all(r["ok"] for r in rows) and len(rows) == 86
    out = ["| Case | Input | Malformed case | Layer | Code | Also reported | Source |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        layer, code = r["expect"].split()
        got = r["got"].split()[1:]
        also = sorted(set(got) - {code, "H-SCHEMA"} if layer == "L1" else set(got) - {code})
        inp = INPUT[kinds[r["id"]]] if not r["id"].startswith("M9") else "schema doc"
        if r["id"] == "M21":
            inp = "HIF (directed)"
        out.append(f"| {r['id']} | {inp} | {r['what']} | {layer} | `{code}` | {', '.join(also) or ''} | {SRC[r['id']]} |")
    return "\n".join(out)


def queue_cases_table():
    rows = L("queue-cases-results.json")
    assert all(r["ok"] for r in rows) and len(rows) == 10
    out = ["| Case | Malformed case | Layer | Code | Source |", "|---|---|---|---|---|"]
    for r in rows:
        layer, code = r["expect"].split()
        out.append(f"| {r['id']} | {r['what']} | {layer} | `{code}` | {SRC[r['id']]} |")
    return "\n".join(out)


# ------------------------------------------------------------------ C4 items
def c4_examples():
    C4 = L("khg-c4-items-0.1.0.schema.json")
    REC = L("khg-record-1.0.0.schema.json")
    reg = Registry().with_resource(REC["$id"], Resource.from_contents(REC))
    V = jsonschema.Draft7Validator(C4, registry=reg)
    f01, f02 = BY_ID["khg:f01-treats"], BY_ID["khg:f02-trial"]
    ext = {"kind": "c4-extraction-doc", "doc_id": "doc:soc-2024", "split": "test", "qset": "p3a-extraction/0.1.0",
           "text": gate_fixture.DOC_SOC, "text_sha256": c1.sha256_text(gate_fixture.DOC_SOC),
           "annotation": {"method": "curated", "exhaustive": False, "annotators": 2},
           "gold": [logical(f01)], "entity_aliases": {"drug:metformin": ["Metformin"]}, "seen_core_keys": []}
    target = next(b for b in f02["bindings"] if b["role"] == "comparator")
    comp = {"kind": "c4-completion-query", "qid": "p3a:cq-000001", "split": "test", "qset": "p3a-completion/0.1.0",
            "fact_id": f02["id"], "relation": f02["relation"], "arity": f02["arity"]["arity"],
            "target": ordered(target, B_ORDER),
            "context": [ordered(b, B_ORDER) for b in f02["bindings"] if b is not target],
            "candidate_universe": "all_entities", "as_of": None,
            "inductive": {"unseen_context_entities": 0, "unseen_relation": False}}
    retr = {"kind": "c4-retrieval-question", "qid": "p3a:rq-000001", "qset": "p3a-retrieval/0.1.0", "split": "test",
            "type": "retrieval_qa", "text": "Which drug was the comparator in the trial described in the 1998 trial report?",
            "template_id": "reported_in>compared_in_trial/comparator/v1", "anchors": ["doc:trial-report-1998"],
            "answer": {"mode": "single", "values": [{"entity": "drug:insulin"}]},
            "aliases": {"drug:insulin": ["insulin"]},
            "support": {"sets": [["khg:f13-reported", "khg:f02-trial"]]},
            "required_edge": {"fact_id": "khg:f02-trial", "relation": "compared_in_trial", "arity": 4},
            "hops": 2, "source_class": "n-ary", "as_of": None, "answerable": True,
            "provenance": {"generator": "template", "generator_version": "0.1.0", "verified": "none"}}
    alice = {k: v for k, v in copy.deepcopy(BY_ID["khg:f11-ceo-alice"]).items()
             if k not in ("version", "recorded_at", "recorded_by", "change", "superseded_by", "arity", "keys")}
    alice["status"] = "asserted"
    for b in alice["bindings"]:
        b.pop("slot", None)
    bob = {k: v for k, v in copy.deepcopy(BY_ID["khg:f12-ceo-bob"]).items()
           if k not in ("version", "recorded_at", "recorded_by", "change", "arity", "keys")}
    for b in bob["bindings"]:
        b.pop("slot", None)
    trace = {"kind": "c4-memory-trace", "trace_id": "p3a:mt-000001", "qset": "p3a-memory/0.1.0", "split": "test",
             "events": [
                 {"step": 1, "tx_time": "2026-01-10T09:00:00Z", "text": "Acme announced that Alice is its chief executive from 1 January 2019.",
                  "put": logical(alice)},
                 {"step": 2, "tx_time": "2026-02-02T09:00:00Z",
                  "text": "Acme corrected its 2019 announcement: the chief executive since 1 January 2019 is Bob.",
                  "apply": {"op": "supersede", "id": "khg:s01", "superseded": ["khg:f11-ceo-alice"],
                            "record": logical(bob), "reason": "incorrect",
                            "evidence": [ordered(e, E_ORDER) for e in copy.deepcopy(BY_ID["khg:s01"]["evidence"])]}}]}
    q = {"kind": "c4-memory-question", "qid": "p3a:mq-000001", "trace_id": "p3a:mt-000001", "qset": "p3a-memory/0.1.0",
         "split": "test", "ask_after_step": 2, "subtype": "current_value", "text": "Who is the chief executive of Acme?",
         "as_of": "end_of_trace", "as_at": "after_step",
         "key": {"relation": "chief_executive", "key": [{"role": "organisation", "value": {"entity": "org:Acme"}}],
                 "target_role": "person"},
         "answer": {"mode": "single", "values": [{"entity": "x:Bob"}]},
         "stale_values": [{"value": {"entity": "x:Alice"}, "fact_id": "khg:f11-ceo-alice", "kind": "retracted"}],
         "future_values": [], "support": {"current": ["khg:f12-ceo-bob"], "history": ["khg:f11-ceo-alice", "khg:s01"]},
         "aliases": {"x:Bob": ["Bob"], "x:Alice": ["Alice"]}, "answerable": True, "tolerance": None,
         "keyed_relation_arity": 2, "n_supersessions_on_key": 1}
    out = []
    for name, item in (("Extraction document (its gold fact is the plain C1 record of §2.15)", ext),
                       ("Completion query", comp), ("Retrieval question (two hops, with anchors)", retr),
                       ("Memory trace (C2 events)", trace), ("Memory question", q)):
        errs = [f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in V.iter_errors(item)]
        assert not errs, (name, errs[:3])
        out.append(f"{name}:\n\n{block(item)}")
    return "\n\n".join(out)


# ------------------------------------------------------------------ sample migration
def sample_mapping():
    return block(migrate_sample.MAPPING)


def sample_fact():
    recs = c1.load_jsonl(os.path.join(HERE, "sample-migrated.khg.jsonl"))
    assert len(recs) == 13
    r = next(x for x in recs if x.get("id") == "kb-sample:f1")
    assert not list(V_REC.iter_errors(r))
    return block(logical(r))


# ------------------------------------------------------------------ assemble
def main():
    text = "".join(open(os.path.join(HERE, f"doc-{i}.md"), encoding="utf-8").read() for i in range(7))
    hg_cyclic, example_acyclic = cyclic_schema()
    ex = schema_example()
    counts = lambda d: (f"{len(d['nodes'])} nodes, {len(d['edges'])} edges, {len(d['incidences'])} incidences, "  # noqa: E731
                        f"{sum(1 for k, n in _pairs(d).items() if n > 1)} repeated (edge, node) pairs")
    kinds = {}
    for r in FIX:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    subs = {
        "<<HEADER>>": block(logical(FIX[0])),
        "<<SCHEMA_EXAMPLE>>": block(ex),
        "<<SCHEMA_HG_EXAMPLE>>": block(schema_hypergraph(ex)) + (
            f"\n\nThe GYO reduction of this hypergraph {'empties it (alpha-acyclic)' if example_acyclic else 'does not empty it (alpha-cyclic)'}; "
            f"the triangle fixture's hypergraph\n`{json.dumps(hg_cyclic['hyperedges'])}` does not reduce "
            "(alpha-cyclic), as P6's gate\nrequires **[validated]**."),
        "<<HIF_EXCERPT>>": hif_excerpt(),
        "<<GATE_HIF>>": "```json\n" + pretty_full() + "\n```",
        "<<PRETTY_LINES>>": str(pretty_full().count("\n") + 1),
        "<<N_FIX_LINES>>": str(len(FIX)), "<<N_FIX_ENT>>": str(kinds["entity"]), "<<N_FIX_HE>>": str(kinds["hyperedge"]),
        "<<FULL_COUNTS>>": counts(FULL), "<<DIR_COUNTS>>": counts(DIRECTED),
        "<<LIB_EVIDENCE>>": lib_evidence(),
        "<<SCENARIO:S-SUP-001>>": scenario("S-SUP-001"),
        "<<QUEUE_HEADER>>": queue_header(), "<<QUEUE_ITEM>>": queue_item(),
        "<<SMOKE_LINES>>": smoke_lines(), "<<SMOKE_RESULT>>": smoke_result(),
        "<<MALFORMED_TABLE>>": malformed_table(), "<<QUEUE_CASES_TABLE>>": queue_cases_table(),
        "<<C4_EXAMPLES>>": c4_examples(),
        "<<SAMPLE_MAPPING>>": sample_mapping(), "<<SAMPLE_MIGRATED_FACT>>": sample_fact(),
    }
    for k in list(re.findall(r"<<REC:([^>]+)>>", text)):
        subs[f"<<REC:{k}>>"] = rec_block(k)
    for k, v in subs.items():
        text = text.replace(k, v)
    left = re.findall(r"<<[A-Z_:0-9a-z\-]+>>", text)
    assert not left, left
    # consistency checks on quoted numbers
    conf = L("conformance-results.json")
    assert sum(r["outcome"] == "passed" for r in conf["full"]) == 18 == len(conf["full"])
    lim = conf["limited"]["results"]
    assert (sum(r["outcome"] == "passed" for r in lim), sum(r["outcome"] == "inapplicable" for r in lim),
            sum(r["outcome"] == "failed" for r in lim)) == (8, 10, 0)
    assert "96 of 96" in text and len(L("malformed-results.json")) + len(L("queue-cases-results.json")) == 96
    rc = L("run_checks.out.json")
    assert rc["library_evidence"]["full"]["xgi.read_hif->write_hif: records with role"] == 0
    assert rc["library_evidence"]["full"]["input_incidence_records_with_role"] == 45
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {OUT}: {text.count(chr(10)) + 1} lines, {len(text)} chars")


def _pairs(d):
    out = {}
    for i in d["incidences"]:
        out[(i["edge"], i["node"])] = out.get((i["edge"], i["node"]), 0) + 1
    return out


if __name__ == "__main__":
    main()
