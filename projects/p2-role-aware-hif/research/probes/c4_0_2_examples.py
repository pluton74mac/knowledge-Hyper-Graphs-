"""Build ``src/khg_contracts/data/fixture/c4-items-0.2.0.jsonl``, the example file of ``khg-c4-items`` 0.2.0 (DESIGN
§9.6; §14 ruling 20), from the gate fixture. Deterministic: run from the repository root, it rewrites the file byte
for byte (canonical JSON lines).

    python projects/p2-role-aware-hif/research/probes/c4_0_2_examples.py [OUT]

Every item uses the fixture schema ``p2-gate`` 1.0.0 and shows the fields 0.2.0 adds:

- the header's ``corpus``;
- an extraction document with ``doc_kind``, ``gold_scope`` and ``mentions`` (a leak-free candidate table: the
  entities whose labels occur in the text, with their spans, and one distractor of the same type);
- a completion query naming its split manifest (``manifest``);
- three retrieval questions, one per ``answer_mode`` (``single``, ``set``, ``count``), with P10's ``provenance``
  extras (``template``, ``pair_hops``, ``nary_dependent``, ``anchor_degree``: the anchors' degree under the question's
  ``where`` on the fixture);
- two split manifests: a semi-inductive one with ``inference`` facts, and a leak-probe one with a ``probe`` fact (an
  unordered entity pair under another relation) and a ``lite`` subset.

``validate_item`` accepts the file under both engines (``tests/scorers/test_c4_items_0_2.py``).
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

from khg_contracts import data, jsonio, record
from khg_contracts.store import MemoryStore, Where

OUT = Path("src/khg_contracts/data/fixture/c4-items-0.2.0.jsonl")
QSET = "p2-fixture-qset-0.2"
FIXTURE = data.load_json("fixture/fixture.c1.json")
SCHEMA = data.load_json("fixture/fixture.relation-schema.json")
TEXTS = {k: v["text"] for k, v in data.load_json("fixture/fixture.doc-texts.json")["texts"].items()}
OLD = data.load_jsonl("fixture/c4-items.jsonl")  # the 0.1.0 example: its lines are reused where they fit
BY_ID = {r["id"]: r for r in FIXTURE["records"] if "id" in r}
WHERE = {"as_of": None, "rank": ["preferred", "normal"], "status": ["asserted"], "valid_mode": "definite"}
CONTAINER = {"document_id": FIXTURE["header"]["document_id"], "sha256": record.container_sha256(FIXTURE)}


def entity(eid: str) -> dict[str, Any]:
    e = copy.deepcopy(BY_ID[eid])
    for f in ("version", "recorded_at", "recorded_by"):
        e.pop(f, None)
    return e


def old(kind: str) -> dict[str, Any]:
    return copy.deepcopy(next(x for x in OLD if x["kind"] == kind))


def spans(text: str, name: str) -> list[list[int]]:
    out, i = [], text.find(name)
    while i >= 0:
        out.append([i, i + len(name)])
        i = text.find(name, i + 1)
    return out


def store() -> MemoryStore:
    s = MemoryStore(SCHEMA)
    s.load(FIXTURE)
    return s


def degree(anchors: list[str], where: dict[str, Any]) -> int:
    """The anchors' degree under a question's ``where``: the facts ``incident`` returns, counted once."""
    s = store()
    w = Where(status=frozenset(where["status"]), rank=frozenset(where["rank"]), as_of=where["as_of"],
              valid_mode=where["valid_mode"])
    return len({r["id"] for a in anchors for r in s.incident(a, where=w)})


def header() -> dict[str, Any]:
    h = old("c4-header")
    h.update(format="khg-c4-items/0.2.0", qset=QSET, corpus={"id": CONTAINER["document_id"], "version": "1.0.0",
                                                              "tier": "core"},
             created_by="P2 design examples: khg-c4-items 0.2.0 (DESIGN §14 ruling 20)")
    return h


def extraction_doc() -> dict[str, Any]:
    d = old("c4-extraction-doc")
    text = d["text"]
    mentions = []
    for eid in ("ex:KingOfFrance", "ex:LouisXIII", "ex:LouisXIV"):  # the entities the text names, by their labels
        e = entity(eid)
        mentions.append({"entity": e, "source": "match", "spans": spans(text, e["label"])})
    mentions.append({"entity": entity("ex:Mazarin"), "source": "distractor",
                     "description": "a Person of the corpus that the text does not name"})
    d.update(qset=QSET, doc_kind="rendered", gold_scope=["position_held"], mentions=mentions)
    return d


def completion_query() -> dict[str, Any]:
    q = old("c4-completion-query")
    q.update(qset=QSET, manifest="c4:splits-inductive")
    return q


def retrieval_questions() -> list[dict[str, Any]]:
    single = old("c4-retrieval-question")
    single.update(qset=QSET, answer_mode="single")
    single["provenance"].update(template="temporal-holder", pair_hops=2, nary_dependent=True,
                                anchor_degree=degree(single["anchors"], single["where"]))
    many = {"kind": "c4-retrieval-question", "id": "c4:rq-coadmin-agents", "qset": QSET, "split": "test",
            "qid": "rq:coadmin-agents", "type": "single_hop", "answer_mode": "set",
            "text": "Which drugs, taken together, can cause hypoglycaemia?", "anchors": ["ex:hypoglycaemia"],
            "answer": {"values": [{"entity": "ex:insulin"}, {"entity": "ex:metformin"}],
                       "text": "insulin and metformin"},
            "support": {"sets": [["f:coadmin-1"]]}, "hops": 1, "source_class": "fixture", "answerable": True,
            "where": dict(WHERE),
            "provenance": {"generator": "p2-design-examples", "template": "joint-agents", "pair_hops": 1,
                           "nary_dependent": True}}
    many["provenance"]["anchor_degree"] = degree(many["anchors"], many["where"])
    count = {"kind": "c4-retrieval-question", "id": "c4:rq-route-stops", "qset": QSET, "split": "test",
             "qid": "rq:route-stops", "type": "aggregation", "answer_mode": "count",
             "text": "How many stops does Air Canada's route Toronto - Montreal - Toronto make?",
             "anchors": ["ex:AirCanada"],
             "answer": {"values": [{"literal": {"datatype": "quantity", "amount": "+3", "unit": "1"}}], "text": "3"},
             "support": {"sets": [["f:route-1"]]}, "hops": 1, "source_class": "fixture", "answerable": True,
             "where": dict(WHERE),
             "provenance": {"generator": "p2-design-examples", "template": "count-stops", "pair_hops": 1,
                           "nary_dependent": True}}
    count["provenance"]["anchor_degree"] = degree(count["anchors"], count["where"])
    return [single, many, count]


def manifests() -> list[dict[str, Any]]:
    facts = sorted(r["id"] for r in FIXTURE["records"] if r.get("kind") == "hyperedge"
                   and not r["relation"].startswith("khg:") and r["status"] != "goal")
    # semi-inductive (P3a §6.3): Louis XIV is a new entity; the fact with him as subject is test, the other fact
    # that names him is given to the model at test time
    inductive = {f: "train" for f in facts}
    inductive.update({"f:king-14": "test", "f:born-louis14-paris": "inference"})
    # leak probe (P3a §6.2): f:loop-yyz and f:route-1 share the unordered pair (Air Canada, Toronto Pearson) under two
    # relations; the probe fact stays in test and its counterpart moves to train
    probe = {f: "train" for f in facts}
    probe.update({"f:loop-yyz": "test", "f:king-14": "test", "f:cat-7": "valid"})
    return [{"kind": "c4-split-manifest", "id": "c4:splits-inductive", "qset": QSET, "scheme": "semi_inductive",
             "seed": "20260926:p2-fixture:semi_inductive", "container": dict(CONTAINER), "splits": inductive},
            {"kind": "c4-split-manifest", "id": "c4:splits-leak-probe", "qset": QSET, "scheme": "leak_probe",
             "seed": "20260926:p2-fixture:leak_probe", "container": dict(CONTAINER), "splits": probe,
             "probe": {"f:loop-yyz": ["same_pair_other_relation"]},
             "lite": ["rq:coadmin-agents", "rq:king-1700"]}]


def lines() -> list[dict[str, Any]]:
    return [header(), extraction_doc(), completion_query(), *retrieval_questions(), *manifests()]


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else OUT
    out.write_text("".join(jsonio.canonical(x) + "\n" for x in lines()), encoding="utf-8")
    sys.stderr.write(f"wrote {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
