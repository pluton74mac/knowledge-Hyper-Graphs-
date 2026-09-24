"""Builds <examples>/c4-items.jsonl (one C4 item of each kind, in C1 terms, from the gate fixture) and
<examples>/c5-outputs.jsonl (one system output of each C5 kind). Memory gold is computed by derive_memory_gold
(khg_c5_proto) and written into the questions, so the file passes I005 by construction; the script then re-checks it."""
import copy
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import khg_synth as K  # noqa: E402
import khg_c5_proto as C5  # noqa: E402

EX = Path(sys.argv[1])
FIX = json.loads((EX / "fixture.c1.json").read_text(encoding="utf-8"))
SCH = json.loads((EX / "fixture.relation-schema.json").read_text(encoding="utf-8"))
TEXTS = {k: v["text"] for k, v in json.loads((EX / "fixture.doc-texts.json").read_text(encoding="utf-8"))["texts"].items()}
S = K.Schema(SCH)
REC = {r["id"]: r for r in FIX["records"]}
QSET = "p2-fixture-qset"


def strip(r):
    r = copy.deepcopy(r)
    for f in K.STORE_FIELDS:
        r.pop(f, None)
    return r


def E(*ids):
    return [copy.deepcopy(REC[i]) for i in ids]


def sha(text):
    return "sha256:" + hashlib.sha256(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()


header = {"kind": "c4-header", "format": "khg-c4-items/0.1.0", "qset": QSET, "record_format": "khg-record/1.0.0",
          "schema": copy.deepcopy(FIX["header"]["schema"]), "created_by": "P2 design examples (P3a fills real sets)"}

# ---------------------------------------------------------------- extraction document with position-selector gold
bio = TEXTS["doc:louis-bio"]
q = "Louis XIV succeeded his father Louis XIII as King of France on 14 May 1643"
s0 = bio.index(q)
gold = {"kind": "hyperedge", "id": "f:gold-louis-bio-1", "relation": "position_held", "status": "asserted",
        "bindings": [{"bid": "b1", "role": "holder", "value": {"entity": "ex:LouisXIV"}},
                     {"bid": "b2", "role": "position", "value": {"entity": "ex:KingOfFrance"}},
                     {"bid": "b3", "role": "start_time", "value": {"literal": {"datatype": "time",
                                                                               "time": "+1643-05-14T00:00:00Z",
                                                                               "precision": 11, "calendar": "gregorian"}}},
                     {"bid": "b4", "role": "replaces", "value": {"entity": "ex:LouisXIII"}}],
        "evidence": [{"id": "e1", "type": "curated", "mode": "manual",
                      "source": {"doc_id": "doc:louis-bio", "doc_sha256": sha(bio)},
                      "selectors": [{"type": "quote", "exact": q, "prefix": "", "suffix": "."},
                                    {"type": "position", "start": s0, "end": s0 + len(q)}],
                      "supports": ["b1", "b2", "b3", "b4"]}]}
ext = {"kind": "c4-extraction-doc", "id": "c4:ext-louis-bio", "qset": QSET, "split": "test", "doc_id": "doc:louis-bio",
       "text": bio, "text_sha256": sha(bio),
       "annotation": {"guideline": "p2-fixture-guideline/0", "annotators": 1, "adjudicated": False},
       "gold": [K.canonical_record(gold)], "entities": E("ex:KingOfFrance", "ex:LouisXIII", "ex:LouisXIV")}

# ---------------------------------------------------------------- completion query (literal-free projection)
k14 = REC["f:king-14"]
d = K.derived(S, k14)
ctx = [b for b in k14["bindings"] if K.slot_of(S, k14, b) in ("core", "qualifier") and b["bid"] != "b1"]
model_arity = sum(1 for b in k14["bindings"] if K.slot_of(S, k14, b) in ("core", "qualifier")
                  and K.vkind(b["value"]) != "literal")
cq = {"kind": "c4-completion-query", "id": "c4:cq-king-14-holder", "qset": QSET, "split": "test",
      "qid": "cq:king-14-holder", "fact_id": "f:king-14", "relation": "position_held", "arity": d["arity"],
      "model_arity": model_arity,
      "target": {"bid": "b1", "role": "holder", "slot": "core", "value": {"entity": "ex:LouisXIV"}},
      "context": copy.deepcopy(ctx), "candidate_universe": {"kind": "entities_of_type", "types": ["Person"]}}

# ---------------------------------------------------------------- retrieval question (its read is part of the item)
rq = {"kind": "c4-retrieval-question", "id": "c4:rq-king-1700", "qset": QSET, "split": "test", "qid": "rq:king-1700",
      "type": "temporal", "text": "Who was King of France on 1 January 1700?", "anchors": ["ex:KingOfFrance"],
      "answer": {"values": [{"entity": "ex:LouisXIV"}], "text": "Louis XIV"}, "support": {"sets": [["f:king-14"]]},
      "hops": 1, "source_class": "fixture", "answerable": True,
      "where": {"as_of": "+1700-01-01T00:00:00Z", "valid_mode": "definite", "rank": ["preferred", "normal"],
                "status": ["asserted"]},
      "provenance": {"generator": "p2-design-examples"}}

# ---------------------------------------------------------------- memory traces and questions
t = lambda s: f"2026-10-01T00:00:{s:02d}Z"
kra = strip(REC["f:born-skłodowska-kraków"])
kra["status"] = "asserted"
kra.pop("status_ref")
war = strip(REC["f:born-skłodowska-warszawa"])
sup = {"op": "supersede", "id": "m:sup-1", "superseded": ["f:born-skłodowska-kraków"], "records": [war],
       "reason": "correction", "note": "birthplace is Warsaw, per the curated biography",
       "evidence": copy.deepcopy(REC["m:sup-1"]["evidence"])}
tr_kings = {"kind": "c4-memory-trace", "id": "c4:mt-kings", "qset": QSET, "split": "test", "trace_id": "t:kings",
            "entities": E("ex:KingOfFrance", "ex:LouisXIII", "ex:LouisXIV"),
            "events": [{"step": 1, "tx_time": t(1), "put": [strip(REC["f:king-13"])]},
                       {"step": 2, "tx_time": t(2), "put": [strip(REC["f:king-14"])]}]}
tr_maria = {"kind": "c4-memory-trace", "id": "c4:mt-maria", "qset": QSET, "split": "test", "trace_id": "t:maria",
            "entities": E("ex:Kraków", "ex:Maria_Skłodowska", "ex:Warszawa"),
            "events": [{"step": 1, "tx_time": t(1), "put": [kra]}, {"step": 2, "tx_time": t(2), "apply": sup}]}
WHERE = lambda as_of: {"as_of": as_of, "valid_mode": "definite", "rank": ["preferred", "normal"], "status": ["asserted"]}
KEYPOS = [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}]


def question(qid, trace, step, text, rel, key, role, where, support, subtype="current_value"):
    x = {"kind": "c4-memory-question", "id": "c4:" + qid.replace(":", "-"), "qset": QSET, "split": "test", "qid": qid,
         "trace_id": trace["trace_id"], "ask_after_step": step, "subtype": subtype, "text": text, "relation": rel,
         "key": key, "target_role": role, "where": where, "support": support}
    g = C5.derive_memory_gold(trace, x, schema=S)
    for k in ("answer", "stale_values", "future_values", "disputed_values", "answerable"):
        x[k] = g[k]
    return x


mq1 = question("mq:king-1700", tr_kings, 2, "Who was King of France on 1 January 1700?", "position_held", KEYPOS,
               "holder", WHERE("+1700-01-01T00:00:00Z"), ["f:king-14"])
mq2 = question("mq:king-1620", tr_kings, 2, "Who was King of France on 1 January 1620?", "position_held", KEYPOS,
               "holder", WHERE("+1620-01-01T00:00:00Z"), ["f:king-13"])
mq3 = question("mq:maria-birthplace", tr_maria, 2, "Where was Maria Skłodowska born?", "born_in",
               [{"role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}], "birthplace", WHERE(None),
               ["f:born-skłodowska-warszawa"])
facts = sorted(r["id"] for r in FIX["records"] if r["kind"] == "hyperedge" and S.kind(r["relation"]) != "lifecycle")
splits = {"kind": "c4-split-manifest", "id": "c4:splits", "qset": QSET,
          "splits": {f: ("train", "valid", "test")[i % 3] for i, f in enumerate(facts)}}
lines = [header, ext, cq, rq, tr_kings, tr_maria, mq1, mq2, mq3, splits]
(EX / "c4-items.jsonl").write_text("".join(K.cjson(x) + "\n" for x in lines), encoding="utf-8")

# ---------------------------------------------------------------- C5 system outputs (khg-c5-io/1.0.0)
outs = [
    {"kind": "completion-rank", "qid": "cq:king-14-holder", "n_candidates": 9, "n_filtered_out": 1, "n_greater": 0,
     "n_equal": 1, "target_prob": 0.62, "top1": {"value": {"entity": "ex:LouisXIV"}, "prob": 0.62}},
    {"kind": "retrieval-response", "qid": "rq:king-1700",
     "answer": {"values": [{"entity": "ex:LouisXIV"}], "text": "Louis XIV", "abstained": False},
     "retrieved": [{"rank": 1, "unit_id": "f:king-14", "unit_kind": "hyperedge", "hyperedge_ids": ["f:king-14"],
                    "bids": [["f:king-14", "b1"], ["f:king-14", "b2"], ["f:king-14", "b3"], ["f:king-14", "b4"]]},
                   {"rank": 2, "unit_id": "f:king-13", "unit_kind": "hyperedge", "hyperedge_ids": ["f:king-13"]}],
     "support_claimed": ["f:king-14"],
     "cost": {"prompt_tokens": 412, "completion_tokens": 9, "llm_calls": 1, "retrieval_calls": 1, "retrieval_ms": 3.5,
              "wall_ms": 820.0}},
    {"kind": "memory-response", "qid": "mq:king-1700",
     "answer": {"values": [{"entity": "ex:LouisXIV"}], "text": "Louis XIV", "abstained": False},
     "value_scores": [{"value": {"entity": "ex:LouisXIV"}, "score": 0.9},
                      {"value": {"entity": "ex:LouisXIII"}, "score": 0.1}]},
]
(EX / "c5-outputs.jsonl").write_text("".join(K.cjson(x) + "\n" for x in outs), encoding="utf-8")
print("c4 items:", [x["kind"] for x in lines])
for m in (mq1, mq2, mq3):
    print(m["qid"], "V_cur", [v for v in m["answer"]["values"]], "stale", m["stale_values"], "future", m["future_values"],
          "answerable", m["answerable"])
