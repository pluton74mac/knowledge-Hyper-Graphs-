"""Scorer reports do not depend on ``PYTHONHASHSEED`` (set iteration order): four scorers run in child processes with
different seeds and give byte-identical reports."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = r'''
import hashlib, json, random, sys
sys.path.insert(0, sys.argv[1])
from conftest import Items, doc, fact, question, response
from khg_contracts import data
from khg_contracts.schema import load_schema
from khg_contracts.scorers import completion, extraction, retrieval, stability

r05 = load_schema(sys.argv[1] + "/r05.relation-schema.json")
fs = load_schema(data.load_json("fixture/fixture.relation-schema.json"))
rng = random.Random(0)
items, docs, preds = Items(), [], []
for d in range(8):
    gold = [fact(f"g{d}-{i}", rng.choice(["r", "s"]), A=f"a{rng.randint(0, 4)}", B=f"b{rng.randint(0, 4)}")
            for i in range(5)]
    docs.append(doc(f"d{d}", gold))
    for run, order in (("r1", "o1"), ("r1", "o2"), ("r2", "o1")):
        for g in gold:
            if rng.random() < 0.7:
                preds.append(items(dict(g, relation=rng.choice(["r", "s"])), run=run, order=order, doc_id=f"d{d}"))
out = {"extraction": extraction.score(docs, preds, schema=r05),
       "stability": stability.score(preds, schema=r05, gold=docs)}
records = data.load_json("fixture/fixture.c1.json")["records"]
queries = [q for q in completion.build_queries(records, fs) if "entity" in q["target"]["value"]]
index = completion.FilterIndex.from_records(records, schema=fs)
ents = sorted({b["value"]["entity"] for r in records if r["kind"] == "hyperedge" for b in r["bindings"]
               if "entity" in b["value"]})
outputs = {m: [completion.rank_stats(q, {e: rng.choice([0.1, 0.5, 0.9]) for e in ents}, index, filter=m)
               for q in queries] for m in completion.FILTERS}
out["completion"] = completion.score(queries, outputs, index=index)
out["retrieval"] = retrieval.score([question(f"q{n}", [[f"h{n}", f"h{n + 1}"]]) for n in range(6)],
                                   [response(f"q{n}", [f"h{n + 1}", f"h9", f"h{n}"]) for n in range(6)])
print(hashlib.sha256(json.dumps(out).encode("utf-8")).hexdigest())
'''


def test_reports_do_not_depend_on_the_hash_seed():
    here = str(Path(__file__).resolve().parent)
    digests = set()
    for seed in ("0", "1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        out = subprocess.run([sys.executable, "-c", SCRIPT, here], capture_output=True, text=True, env=env,
                             check=True)
        digests.add(out.stdout.strip())
    assert len(digests) == 1 and len(digests.pop()) == 64
