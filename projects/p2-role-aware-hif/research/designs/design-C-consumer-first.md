---
title: P2 design C (consumer-first) - role-aware HIF and the shared contracts C1, C2, C3, C5
type: design
status: draft
created: 2026-09-23
angle: consumer- and implementation-first
---

# P2 design C: role-aware HIF and the shared contracts (consumer-first)

This is one of the independent designs for project P2 (`projects/p2-role-aware-hif/README.md`;
`projects/PLAN.md` §3, §4, §7). It derives the contracts from the calls the
consumers actually make: P1's five store backends, P3a's corpus build from Wikidata, P3b's replications, P5's
drawings, P6's schema parse, P7's supersession walk, P9's queue and scoring, P10's code-owned walker, and the C5
scorers. Every call a consumer needs is written out with its cost (§1.4): each store read is one index probe, each
per-record call is one pass over one record, and nothing a consumer needs requires a second query or a conversion.

It designs within the director's fixed decisions F1 to F15. I have no objection to any of them (§14 records two
risks that sit next to F12).

**How to read the evidence.** `[R01 §2.3 C1-R13]` is research report 01, section 2.3, requirement C1-R13;
`[R02 §5 case 02]`, `[R03 §3 row 3]`, `[R04 M3]` / `[R04 O5]`, `[R05 §2.2 E-M6]` / `[R05 D-C5-06]` likewise.
Reports live in `projects/p2-role-aware-hif/research/`. **[validated]** means the statement was executed for this
design in `designs/work-C-consumer-first/` (§1.2 lists the commands and results). Every JSON example in this
document was inserted by `assemble.py` from an artefact that passed the validators; none was typed by hand.

## Contents

1. Summary and the gate
2. C1 record format
3. Relation-type schema language
4. HIF mapping: the `roles` convention and the khg-hif profile
5. Library loaders (XGI, HyperNetX)
6. C2 store interface
7. C3 candidate queue, structural linter and action log
8. Validator and the malformed-case list
9. C5 scorers and the C4 item shapes
10. Package layout
11. Versioning and migration
12. v1 scope, later versions, and the upstream proposals
13. Decisions log
14. Risks and open questions

---

## 1. Summary and the gate

### 1.1 The design in fourteen lines

1. **Container.** C1 data is a JSONL file: a header line, then relation-type schema records, entity records,
   hyperedge records and supersession records, each one canonical JSON object per line (§2.1).
2. **Hyperedge.** A hyperedge is `relation` plus a list of **bindings** `{bid, role, slot, direction?, position?,
   value}`. A value is a tagged union: `entity`, `literal`, `hyperedge` (nesting) or `special`
   (`somevalue`, `novalue`, `unbound`) (§2.4-§2.6).
3. **One binding is one HIF incidence record.** A node that plays k roles in one fact has k incidence records,
   each with a single `attrs.role` string and its own `direction`. This settles the contested choice in favour of
   R02/R03 (§4.2): it is the only encoding in which a node can be tail and head of one edge, and it round-tripped
   exactly through both libraries **[validated]**.
4. **Four identifiers (F6):** the opaque `id`; `keys.content` and `keys.core` (the content hash in two scopes, for
   dedup, leak checks and stability); `keys.key` (the declared-key digest, for supersession and collisions); and
   `evidence[].event_hash` on extraction events (§2.2).
5. **Arity** is the number of `core`, `qualifier` and `time` bindings whose value is an entity, a literal, a
   hyperedge or `somevalue`. `participants` (distinct values) and `core` are reported beside it (§2.7).
6. **Lifecycle on four axes (F7):** `status`, `valid_time`, `rank`, `visibility`. A fact that ended in the world
   gets a closed `valid_time` in a new version; `superseded` is reached only through a supersession record (F8).
   Versions are immutable and carry `recorded_at` (§2.9, §2.10, §2.13).
7. **Schema language:** global roles; per-relation role usages with slot class, fillers, `min`/`max`, `ordered`,
   `direction`; a key `{roles, temporal, on_collision}`; co-occurrence constraints; `primary`; `nestable`;
   relation `kind` (§3). P6 gets a deterministic schema hypergraph from one function call (§3.6).
8. **HIF profile:** generic keys `relation` (edge), `role` (incidence) and `label` (node), everything else as flat
   `khg-*` keys; literals become value-shared nodes `khg-lit:<hash>`; nested references become mirror nodes
   `khg-ref:<edge id>`; special-valued bindings live in the edge's `khg-special-bindings`; no `weight`, ever (§4).
9. **Loaders** build XGI and HyperNetX objects through public constructors and carry the rest in a bundled side
   table; export reconciles and, in strict mode, raises on stale or unlabelled incidences (§5, F1).
10. **C2** is a 16-method Protocol (9 core methods a backend writes, 7 derived by a base class) with one `Where`
    filter object, results in id order, key collisions that are never resolved silently, and four atomic
    lifecycle events. A reference in-memory store passes 18 declarative scenarios **[validated]** (§6).
11. **C3** is one append-only JSONL per queue: header, items, log entries. Lint findings carry rule ids and
    SHACL-like severities; identity lints turn into proposal items; verdicts attach to `(core_key, event_hash)`
    (§7).
12. **Validator:** L0 strict JSON, L1 the vendored HIF schema, L2 draft-07 profile/record/meta/queue schemas whose
    subschemas carry `x-khg-code`, L3 Python semantics. The malformed-case list has 96 cases; every one is rejected
    at its expected layer with its expected code **[validated]** (§8).
13. **C5:** five pure-Python scorers (extraction, stability, completion, retrieval, memory), deterministic, no LLM
    by default, with every R05 unit-test table shipped as tests (F14), and the C4 item shapes P3a must fill (§9).
14. **Package** `khg-contracts` (import `khg_contracts`), src layout at the repository root, core dependency
    `jsonschema` only, extras `[xgi]`, `[hypernetx]`, `[fast]`; seven CLI entry points (§10).

### 1.2 What was executed for this design

All in `designs/work-C-consumer-first/`, Python 3.11.15, xgi 0.10.2, hypernetx 2.4.3, pandas 2.3.3,
jsonschema 4.26.0, fastjsonschema 2.22.2, and no network: `requests.get` is patched to raise, and HyperNetX's schema
fetch in the evidence test is served the vendored bytes. The README there has the commands.

| Check | Result |
|---|---|
| Gate fixture (41 container lines: header, schema, 24 entities, 14 hyperedges, 1 supersession) against `khg-record-1.0.0.schema.json`, the schema record against `khg-relation-schema-1.0.0.schema.json`, and all L3 semantic checks | 0 findings |
| Full-fixture HIF export (`network-type` undirected; 39 nodes, 15 edges, 45 incidences, 3 repeated (edge, node) pairs) against the vendored `hif_schema_v0.1.0.json` (blob `e2105bb`) with jsonschema **and** fastjsonschema | valid, valid |
| The same file against the khg-hif profile schema, which `allOf`-includes the vendored HIF schema by its `$id`, resolved offline (jsonschema registry; fastjsonschema `https` handler) | valid, valid |
| Directed slice (5 relations; `network-type` directed; 27 nodes, 7 edges, 18 incidences, 2 repeated (edge, node) pairs), same four validations | valid x4 |
| HIF -> C1 import of the full export equals the original container (canonical JSON equality) | true |
| Chain C1 -> HIF -> XGI -> HIF -> HyperNetX -> HIF -> C1, and the reverse library order, through `research/probes/role_loaders_sketch.py`, for the full fixture and the directed slice | 4 of 4 chains exact; XGI class `Hypergraph` / `DiHypergraph`; `gene:TP53` in both the tail and head set of the XGI edge; 0 stale, 0 unlabelled |
| The libraries' own HIF functions on the same files (the F1 evidence test) | §5.6: XGI keeps 0 of 45 roles; HyperNetX's `to_hif` returns `None` on the full file (writes `"nil"` for 23 missing directions) |
| Malformed cases M01-M99 (86) and Q01-Q10 (10) | 96 of 96 rejected at the expected layer with the expected code |
| C2 conformance: 18 declarative scenarios against the reference store; the same run declaring only 2 of the 9 capabilities (`literal_values`, `nesting`) | 18 passed; then 8 passed, 10 inapplicable, 0 failed |
| Smoke test: candidate -> queue -> structural lint -> store -> export; a duplicate from a second run; a malformed candidate; replay | accepted as `khg:f01-treats@1`; duplicate merged as evidence (`@2`), not a second fact; malformed candidate rejected, never stored; export is valid HIF; replay reproduces the store |
| Migration of `schemas/sample.hif.json` (legacy `attrs.role`, `weight` used as confidence) | 13 records; legacy `arity` agrees with the C1 rule on 3 of 3 edges; 3 weights reported and dropped unless the operator passes a flag; HIF round trip exact |
| Every valid artefact under fastjsonschema | 0 failures |

### 1.3 The gate, clause by clause

PLAN §4: "A record round-trips repo format to HIF to XGI and HyperNetX and back with roles intact; the validator
rejects each malformed case in its test list; a smoke test runs one record through queue, structural lint, store
and export."

| Clause | Test (all offline; `tests/conftest.py` blocks sockets) | What it asserts |
|---|---|---|
| **G1** round trip with roles intact | `tests/gate/test_roundtrip.py`, parametrised over fixtures {`gate.khg.jsonl` (full, undirected with directions), its directed slice, the migrated KB sample} x chains {C1 -> HIF -> XGI -> HIF -> HNX -> HIF -> C1; C1 -> HIF -> HNX -> HIF -> XGI -> HIF -> C1; each library alone} | (a) the final container equals the input structurally (`compare_containers(a, b) == []`, F10); (b) the multiset of `(edge, node, role, direction, khg-bid)` over incidences is unchanged at every HIF stage; (c) `load_xgi(directed)` holds `gene:TP53` in both tail and head of `khg:f03-regulates`; (d) HNX cell `(khg:f02-trial, drug:metformin)` has role `intervention` natively and `background_therapy` in `khg-extra-incidences`; (e) strict export raised nothing (0 stale, 0 unlabelled); (f) output is byte-identical under four `PYTHONHASHSEED` values |
| **G2** the validator rejects each malformed case | `tests/gate/test_malformed.py` over `tests/fixtures/malformed/INDEX.json` (96 cases, §8.3), plus `tests/gate/test_positive.py` (the valid fixtures pass every layer) | for each case: the first rejecting layer is the listed one and the listed code is among its findings; for each valid fixture: zero error findings |
| **G3** smoke: queue, structural lint, store, export | `tests/gate/test_smoke.py` (§7.8) | the candidate passes structural lint and is accepted; the stored record's content equals the fixture record; a second-run duplicate becomes evidence on the same fact; a malformed candidate is rejected and absent from the store; `export("khg-jsonl")` re-validates and `export("hif")` validates against the vendored HIF schema; `replay(queue)` into a fresh store reproduces the store content |

The gate never touches the network, never calls `xgi.read_hif`/`write_hif` or `hnx.from_hif`/`to_hif` (F1), and
never depends on upstream acceptance (F15). The separate evidence test (§5.6) does call those functions, offline,
and is not part of the gate.

### 1.4 The consumer call sequences this design is derived from

Each block is the complete call sequence a consumer runs against P2; after each block, what its calls cost. Every
name comes from these imports:

```python
from khg_contracts import (read_container, parse_container, write_container, compare_containers, normalize,
                           entity_ids, render_text, load_schema, schema_hypergraph, to_hif,
                           validate_record, validate_container, validate_item)
from khg_contracts.record import project
from khg_contracts.loaders import load_xgi, load_hnx
from khg_contracts.store import Where, KeyCollision, Timed, conformance
from khg_contracts.queue import Queue, Linter, make_candidate, queue_items
from khg_contracts.scorers import extraction, stability, completion, retrieval, memory
from khg_contracts.scorers.completion import CompletionConfig
```

**P1 (five store backends; gate: fidelity, load time, query latency).**

```python
s = Timed(TypeDBStore(schemas=[schema]))                 # one timing wrapper for all five backends (§6.9)
report = s.load(read_container("p3a-slice.khg.jsonl"))   # bulk import that keeps version and recorded_at
back = parse_container(s.export("khg-jsonl"))            # round-trip fidelity ...
diff = compare_containers(read_container("p3a-slice.khg.jsonl"), back)   # ... is [] when exact
for q in query_set:                                      # the same calls on every backend
    s.incident(q.node, role=q.role, where=Where(as_of=q.as_of))
    s.find(q.relation, q.pattern, match="at_least")
    s.find_by_key(q.relation, q.key, where=Where(as_of=q.as_of))
    s.supersession_walk(q.fact)
earl = conformance.run(TypeDBStore)                      # "inapplicable" is never counted as "passed" (§6.7)
```

Every read is one index probe on an incidence table: `(entity_id | fact_ref)` for `incident`, `(relation,
key_digest)` for `find_by_key`, `superseded`/`superseding` for the walk. `load` is one pass that does not re-run the
validator, so P1 times the backend; `export` is one pass in id order, and `compare_containers` one merge of two
sorted containers. What a backend cannot do is a capability flag, so P1 reports "inapplicable" instead of a false
fidelity loss (§6.5, §6.8).

**P3a (Wikidata corpus; gate: leak check, dedup, arity histogram, split, question sets).**

```python
schema = load_schema("p3a-wikidata.schema.json")         # meta-schema + D- checks; raises SchemaInvalid
facts = []
for stmt in wikidata_dump:                               # P3a's reader; mapping tables in §2.6 and §2.9
    rec = normalize(p3a_to_c1(stmt), schema)             # fills slot, direction, valid_time, arity, keys
    report = validate_record(rec, schema)                # L2 + L3 for one record: report.ok, report.errors
    if report.ok:
        facts.append(rec)
write_container("p3a-v1.khg.jsonl", entities + facts, schemas=[schema])   # header + canonical order
assert validate_container("p3a-v1.khg.jsonl").ok        # cross-record checks: references, keys, supersession
# dedup on rec["keys"]["content"]; leak check on rec["keys"]["core"]; histogram on rec["arity"]["arity"]
assert all(validate_item(item).ok for item in c4_items)  # C4 shapes, dispatched on item["kind"] (§9.6)
```

`normalize` and `validate_record` are one pass over one record's bindings, with no store and no I/O.
`validate_container` is one streaming pass that keeps an id index and a key index, and `write_container` sorts in
memory (n log n); those two are the only calls whose memory grows with the corpus. Dedup, the leak check and the
histogram read fields already on every record, so they are dictionary passes, and two builds of the corpus produce
the same keys because the Wikidata mapping (datatypes, precisions, calendars, ranks, references, `somevalue`,
`novalue`, time qualifiers) is fixed in §2.6 and §2.9.

**P3b (two replications; gate: reproduced within tolerance, calibration by arity).**

```python
idx = completion.FilterIndex.from_records(train, valid, test)                 # C1 records of the three splits
outputs = [completion.rank_stats(q, model.scores(q), idx) for q in queries]   # counts, not score vectors
report = completion.score(queries, outputs, config=CompletionConfig(preset="stare"))
tuples = [project.positional(r, schema) for r in train]                      # model input (§2.14)
```

`from_records` is one pass that keys every fact by (relation, target role, the other bindings as a set);
`rank_stats` is one probe into that index plus one pass over the model's score map; `score` is one pass plus the
bootstrap; `project.positional` is one pass over one record.

**P5 (reader study; roles visible in XGI and HyperNetX drawings).**

```python
hif = to_hif(read_container("slice.khg.jsonl"), relations={"regulates", "compared_in_trial"})   # a directed slice
L = load_xgi(hif)                                  # xgi.DiHypergraph + bundled side table
L.roles("khg:f03-regulates", "gene:TP53")          # ["regulator", "target"]
H = load_hnx(hif)                                  # the first role is a native cell property
```

`to_hif` is one pass over the bindings; each loader validates the file and builds the library object through public
constructors in one pass over the incidences; `roles` is one dictionary lookup in the side table. Labels travel as
node attrs, so a drawing needs no second source.

**P6 (schema width survey; gate: class and width of a schema file, a constructed cyclic case).**

```python
schema = load_schema(path)
hg = schema_hypergraph(schema)                     # {"vertices": [roles], "hyperedges": {relation: [roles]}}
hg_meta = schema_hypergraph(schema, slots=("core", "qualifier", "time", "meta"))   # meta roles included
```

One pass over the usages, sorted output. P6's classifier (GYO, widths) runs on two plain dicts, and the constructed
cyclic case is a shipped fixture (§3.6).

**P7 (identity and supersession; gate: identity test list, memory comparison).**

```python
try:
    s.put(new, actor="p7")
except KeyCollision as e:                          # e.info == {"conflicts": [ids], "suggested": policy}
    olds = s.get_many(e.info["conflicts"])
    decision = classify(new, olds, e.info["suggested"])            # P7's own identity rules
    if decision == "supersede":                    # belief revision (F7, F8)
        s.apply({"op": "supersede", "id": sid, "superseded": e.info["conflicts"], "record": new,
                 "reason": "incorrect", "evidence": ev}, actor="p7")
    elif decision == "close_older":                # a world change, not a supersession (F7)
        for old in e.info["conflicts"]:
            s.apply({"op": "end_validity", "target": old, "to": new["valid_time"]["from"]}, actor="p7")
        s.put(new, actor="p7")
now = s.find_by_key("chief_executive", [{"role": "organisation", "value": {"entity": "org:Acme"}}],
                    where=Where(as_of=t, as_at=tau))
chain = s.supersession_walk(fact_id)               # always terminates (§6.3)
text = render_text(record, s.get_many(entity_ids([record])))     # the flat vector-store baseline's document
report = memory.score(questions, responses)
```

`put` is one pass over the record plus one key-index probe; the collision names the conflicting ids, so the
decision needs one `get_many`; each event is one atomic write; `find_by_key` is one probe on (relation, key digest);
the walk reads each supersession record once; `memory.score` is one pass.

**P9 (extraction gate; gate: P/R and role accuracy against P3a, instability over 3 runs x 2 orders, output
validates against C3).**

```python
linter = Linter(schema, store=kb, doc_text=texts)  # kb: a store with P3a's entities; texts: {doc id: NFC text}
q = Queue.create("queues/p9-r1-o1.khg-queue.jsonl", queue_id="p9-r1-o1")
for position, doc in enumerate(order_o1):
    for c in extractor(doc):
        payload = make_candidate(c, schema=schema)                 # status candidate; normalised; keys; event_hash
        item = q.submit("hyperedge", payload, submitted_by="p9-x/0.3",
                        run={"run_id": "r1", "order_id": "o1", "position": position, "seed": 13},
                        doc={"doc": doc.id, "doc_sha256": doc.sha256})   # assigns the qid and the cand: id
        linter.lint(q, item["qid"])                                # one log entry; maybe proposal items
paths = sorted(glob("queues/p9-*.khg-queue.jsonl"))                # 3 runs x 2 orders = 6 files
report = extraction.score(gold_docs, queue_items(paths), schema=schema)   # E-M1 P/R, E-M6 role accuracy
stab = stability.score(queue_items(paths))                                # S-M1 .. S-M7, delta_order
# "output validates against C3":  khg-validate queues/*.khg-queue.jsonl
```

`make_candidate` is one pass over one record; `submit` is one append after a schema check of the line; `lint` is
L2 and L3 on one payload plus at most two store probes (`find(match="exact")` for duplicates, `find_by_key` for
collisions). `queue_items` streams the files. `extraction.score` runs one Hungarian alignment per (document, run)
over that document's few facts; `stability.score` compares the 6 runs pairwise (15 pairs) on the two content keys.

**P10 (code-owned walker; gate: answers the P3a questions, cost/latency/accuracy behind one interface).**

```python
w = Where(as_of=question["as_of"])                 # null as_of: no valid-time filter
node = question["anchors"][0]                      # a start node from the C4 item (§9.6): no entity linking
edges = s.incident(node, where=w)                  # full records with roles, in id order: reproducible closed choices
deg = s.degree(node, where=w)                      # the same count without materialising the records
labels = s.get_many(entity_ids(edges))             # one batch lookup for every label the prompt needs
choices = [render_text(e, labels) for e in edges]
# the next node is an entity-valued binding of the chosen edge; a literal value is a terminal answer
report = retrieval.score(questions, responses, facts=s.iter_records())
```

`incident` and `degree` are one index probe each, and every `incident` result carries the whole binding list, so the
walker never makes a second query for members [R01 §3 C2-R12]; `get_many` is one batch lookup; `render_text` is one
pass over one record; `retrieval.score` is one pass over the responses.

**Phase 2 and 3 consumers.** P4 needs the pairwise projection with back-pointers and a GraphRAG-Bench adapter; P11
needs a bind event, an unbound-slot query and binding proposals. Both land in 1.1, before those projects open
(§12). P8 needs only what 1.0 has: per-item outputs keyed by stable ids from all four scorers, and the `inferred`
evidence type for completer output.

---

## 2. C1 record format

Format id: **`khg-record/1.0.0`**. JSON Schema: `khg-record-1.0.0.schema.json` (draft-07) for structure; the Python
layer (§8) for everything draft-07 cannot say.

### 2.1 The container

A C1 file is **JSONL** (UTF-8, LF line ends, extension `.khg.jsonl`): one canonical JSON object per line. Line 1 is
the header; then relation-type schema records (sorted by id, version), entity records (sorted by id), hyperedge
records (sorted by id, then version), supersession records (sorted by id). JSONL because P3a's corpus and P1's bulk
loads need streaming, which a single HIF document cannot give [R01 §7 PF-28], and because line-oriented files diff
and append cleanly (the queue in §7 is JSONL for the same reason).

**Canonical JSON** (for serialisation and every hash): keys sorted by code point, separators `,` and `:` with no
whitespace, UTF-8 without escaping non-ASCII, strings in NFC, no `NaN`/`Infinity`, integers only where the schema
says integer, numbers never used inside hash inputs (literal values are strings, §2.6). Tests compare parsed
structures, not bytes (F10); the canonical bytes exist so that hashes and diffs are stable.

| Header field | Type | Req. | Meaning |
|---|---|---|---|
| `kind` | `"header"` | yes | |
| `format` | `"khg-record/1.<m>.<p>"` | yes | record-format version; a reader rejects an unknown major (M82) |
| `content` | `"snapshot"` \| `"history"` | yes | snapshot: at most one version per hyperedge id (the current one at `as_at`); history: every version |
| `as_at` | RFC 3339 UTC | no | the transaction time a snapshot was taken at |
| `created_at`, `created_by` | timestamp, string | no | provenance of the file |
| `title`, `description` | string | no | |
| `schemas` | `[{id, version, sha256}]` | yes | the relation-type schema documents this file carries; `sha256` of their canonical JSON |

The relation-type schema documents themselves are records of kind `relation-schema` in the same file (§3), so a
container is self-describing and HIF can carry it verbatim (§4.6).

Reading and writing: `read_container(path)` and `parse_container(text)` run L0 and return the records in file
order; `write_container(path, records, *, schemas, content="snapshot", title=None)` sorts the records into the order
above, writes the header with the schema hashes, and writes canonical JSON; `compare_containers(a, b)` returns the
list of structural differences (F10), empty when the two are equal, header provenance fields aside.

```json
{
  "kind": "header",
  "format": "khg-record/1.0.0",
  "content": "snapshot",
  "as_at": "2026-09-23T12:00:00Z",
  "created_at": "2026-09-23T12:00:00Z",
  "created_by": "p2-gate-fixture/1.0.0",
  "title": "P2 gate fixture (adversarial)",
  "schemas": [
    {
      "id": "p2-gate",
      "sha256": "0acc5bc47da530243090e868492b376b444b37a8873d83f648b472e4bcc42943",
      "version": "1.0.0"
    }
  ]
}
```

### 2.2 Identifiers

**Id grammar.** Every entity, hyperedge and supersession id is a string `ns:local`: `ns` matches
`[a-z][a-z0-9-]{0,31}`; `local` is 1 to 256 code points with no white space, no C0 control or DEL, and none of
`<>"{}|\^` and backtick (so every id can become an IRI for P1's RDF backend by prefix expansion); the whole id is
NFC. Non-ASCII is allowed (`x:Zürich`). Ids are unique **across record kinds** in a container or store, so
`incident(x)` never has to ask whether `x` is an entity or a hyperedge (M81). F10 restricts HIF's
string-or-integer ids to strings; foreign integer ids are mapped on import (§4.5).

Reserved namespaces: `khg-lit` and `khg-ref` (HIF node ids, §4.3), `hif` and `hif-int` (foreign-import ids,
§4.5), `cand` (provisional ids of queue payloads, §7.2). A C1 record outside those contexts using them is rejected
(M44).

Schema symbols (role, relation and entity-type ids) match `[A-Za-z][A-Za-z0-9_.-]{0,63}`; binding ids `bid` and
evidence ids `eid` match `[A-Za-z0-9._-]{1,64}` and are unique within their record.

**The four identifiers (F6)** [R01 D-05; R04 M3, O-list; INDRA's uuid/shallow/full hashes, R04 §3.1]:

| Identifier | Field | Computed from | Used by |
|---|---|---|---|
| Fact id | `id` | minted by the writer; opaque, never parsed; stable across versions | every reference, every store index, HIF edge id |
| Content hash, full scope | `keys.content` | `sha256(cjson({"k":"content","r":relation,"b":items(bindings whose slot != meta)}))` | dedup (P3a), stability over runs (P9, S-M1), duplicate lint (C3) |
| Content hash, core scope | `keys.core` | same with `"k":"core"` and core-slot bindings only | leak checks on the main fact (P3a), core P/R (C5 E-M2), refinement lint |
| Declared-key digest | `keys.key` (present iff the relation declares a key) | same with `"k":"key"` and bindings whose role is a key role | key lookup (`find_by_key`), collision check, supersession (P7); P1's `UNIQUE (relation, key_digest, valid WITHOUT OVERLAPS)` [R04 §3.3] |
| Extraction-event hash | `evidence[].event_hash` (only on `type: extracted`) | `sha256(cjson({"k":"event","content":keys.content,"doc":source.doc_sha256,"pos":sorted [start,end] of position selectors,"agent":activity.agent,"model":activity.model}))` | "the same sentence re-extracted by the same reader is the same event" [R01 C1-R03]; verdict unit (§7.5) |

`items(bs)` is the sorted list of `[role, cjson(value), position-or-""]` for the chosen bindings. Bids, slots and
directions are excluded (bids are local names; slot and direction follow from the role). The `"k"` field
separates the domains, so a key digest never equals a content hash by accident. All four are written as
`sha256:<64 hex>`. Changing any hash input is a **major** version change (§11).

### 2.3 Entity record

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `kind` | `"entity"` | yes | |
| `id` | Id | yes | |
| `types` | `[Sym]` | yes (may be `[]`) | entity types declared in the schema; filler checks walk `parents` (§3.1); an empty list skips type checks |
| `label` | string, non-empty | yes | display label for P5, P10 prompts and P7's text rendering [R01 C1-R21] |
| `aliases` | `[string]` | no | surface forms (C5 alias matching) |
| `same_as` | `[Id]` | no | external identities, for example `wd:Q72` |

Entities are immutable in 1.0: a second `put` with different content raises `EntityConflict`. Entity versioning and
redirects after merges come in 1.1 (§12).

```json
{"kind": "entity", "id": "x:Zürich", "types": ["Place"], "label": "Zürich"}
```

### 2.4 Hyperedge record

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `kind` | `"hyperedge"` | yes | |
| `id` | Id | yes | opaque stable fact id |
| `version` | int >= 1 | in containers | assigned by the store; versions are immutable (F8) |
| `recorded_at` | RFC 3339 UTC | in containers | transaction-time start of this version; its end is the next version's `recorded_at` |
| `recorded_by` | string | in containers | actor that wrote this version |
| `change` | `{op, reason?, ref?}` | in containers | why the version exists: `op` in `put`, `supersede`, `transition`, `end_validity`, `add_evidence`; `ref` names a supersession record |
| `schema` | `"<schema id>/<semver>"` | in containers | the relation-type schema the record was typed under [R01 C1-R32] |
| `relation` | Sym | yes | relation type (its `kind` fact/meta/rule is declared in the schema, §3.1) |
| `status` | enum (§2.10) | yes | record status |
| `rank` | `preferred` \| `normal` \| `deprecated` | canonical | editorial rank, default `normal` [R04 M5] |
| `rank_reason` | string | no | for Wikidata `P2241`/`P7452` reasons, for example `wd:Q25895909` |
| `visibility` | `visible` \| `suppressed` | canonical | governance tier, default `visible` [R01 C1-R45] |
| `valid_time` | `{from?, to?, end_cause?}` | no | world validity, half-open (§2.9) |
| `bindings` | `[Binding]`, at least one | yes | §2.5 |
| `confidence` | `{value, scale, method?}` | no | aggregate belief (§2.11) |
| `evidence` | `[Evidence]` | yes unless `status` is `goal` | §2.12 |
| `superseded_by` | `[Id]` | iff `status` is `superseded` | index pointer to the superseding facts (F8); equals the set named by supersession records |
| `arity` | `{arity, core, participants}` | canonical | derived (§2.7) |
| `keys` | `{content, core, key?}` | canonical | derived (§2.2) |

"In containers" means required in a container file and filled by the store on `put`; a writer may omit them in
`put()` input. "Canonical" means `normalize()` materialises the field; the validator recomputes it and rejects a
mismatch (`R-DERIVED`, M58, M59).

There is no per-record `kind` of edge (fact, meta, rule): the relation type declares it (§3.1), so the kind can
never disagree with the relation, and P10 filters on relations it already knows [R01 C1-R05, DIR §5].

### 2.5 Bindings, slot classes, direction, position

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `bid` | local id | yes | the binding's name inside the record; evidence refers to it (`binding_refs`); writers keep it stable across versions |
| `role` | Sym | yes | global role id (F4) |
| `slot` | `core` \| `qualifier` \| `time` \| `meta` | canonical | copied from the role usage |
| `direction` | `tail` \| `head` | iff the usage declares one | copied from the usage; a contradicting value is `S-DIRECTION` (M72) |
| `position` | int >= 0 | iff the usage is `ordered` | positions of one ordered role are exactly `0..n-1` (M73) |
| `value` | Value (§2.6) | yes | |

Canonical order of bindings: by `(role, position or -1, cjson(value), bid)`, a total order on valid records.

**Slot classes** (four, per R04 O12, justified by consumers):

- `core`: the participants without which the fact is not the fact. They define `keys.core`, the triple view
  (`primary`), P3a's leak check on the main fact and P7's refinement rule.
- `qualifier`: refinements. Adding one narrows a fact and never contradicts it [R04 M3, HyperMono via SCH §4].
  Counted in arity.
- `time`: time qualifiers (`start_time`, `end_time`, `point_in_time`). They stay bindings, because P3a imports them
  and P9 extracts them, and they **derive** `valid_time` through the schema's time model (§2.9) [R01 C1-R47].
- `meta`: statement metadata that Wikidata stores as qualifiers but that are not participants (`P2241`, `P7452`,
  date uncertainty, "named as"). Excluded from arity, from `keys.content` and from P6's hypergraph by default,
  because the P6 probe found them to be the most widely shared attributes and they would dominate the measurement
  [R04 §8.2].

**Direction** belongs to the binding and is separate from the role [R01 C1-R19]. In 1.0 it is fully determined by
the role usage, and `normalize()` writes it into the binding so that HIF export needs no schema lookup. A node can
be tail and head of one fact through two bindings (`khg:f03-regulates`).

**Repeated and symmetric roles.** A role with `max > 1` and not `ordered` is interchangeable: its fillers form a
multiset, and permuting them changes no key [R01 C1-R15]. A symmetric binary relation is one role with
`min = max = 2` (`married`, §3.5); never `partner_1`/`partner_2` [R04 §1.5].

### 2.6 Values

A value is a JSON object with exactly one tag key: `entity`, `literal`, `hyperedge` or `special` (M45).

| Value | Shape | Meaning |
|---|---|---|
| entity | `{"entity": Id}` | an entity; must resolve to an entity record (M80) |
| literal | `{"literal": lexical, "datatype": dt, ...}` | a typed literal, table below |
| hyperedge | `{"hyperedge": Id}` | nesting: a fact about a fact (§2.8) |
| some value | `{"special": "somevalue"}` | a filler exists and is unknown (Wikidata `somevalue`) [R01 C1-R08] |
| no value | `{"special": "novalue"}` | asserted absence ("this reaction has no catalyst") [OWA §3 via R01] |
| unbound | `{"special": "unbound", "expects"?: {"entity_types": [Sym]}}` | an open slot waiting to be bound; legal only when `status` is `goal` (M69) [R01 C1-R09] |

**Literals.** Every lexical form is a string, so no hash input is ever a float and 2^53 hazards cannot arise
[R02 §5 case 22].

| `datatype` | Canonical lexical form | Other fields | Wikidata source |
|---|---|---|---|
| `string` | any NFC string | none | string, external-id, commonsMedia |
| `lang-string` | NFC string | `lang` (BCP 47, lower case), required | monolingualtext |
| `integer` | `-?(0\|[1-9][0-9]*)`, not `-0` | none | |
| `decimal` | `-?(0\|[1-9][0-9]*)(\.[0-9]*[1-9])?`, not `-0` (no `+`, no exponent, no trailing zero) | none | |
| `boolean` | `true` \| `false` | none | |
| `time` | `YYYY` (millennium, century, decade, year), `YYYY-MM` (month), `YYYY-MM-DD` (day), `YYYY-MM-DDThh:mm:ssZ` (second); year may be signed and longer than 4 digits | `precision` (required), `calendar: "julian"` (optional; Gregorian is the default and is omitted) | time: `+1643-05-14T00:00:00Z` precision 11 becomes `"1643-05-14"`, `"day"`; codes 6/7/8/9/10/11/14 map to millennium/century/decade/year/month/day/second; codes 12 and 13 (marked unused upstream [R04 M2]) are truncated to day and counted; `before`/`after` are dropped (unused upstream) |
| `quantity` | amount as a canonical decimal | `unit` (required: an Id such as `wd:Q3241121`, or `"1"`), `lower`, `upper` (optional decimals with `lower <= amount <= upper`, M51) | quantity: `+443037` becomes `"443037"`; unit IRI becomes `wd:Q…` |
| `iri` | absolute IRI | none | url |

Globe coordinates, geo-shapes, lexemes and the other Wikidata datatypes are not in 1.0; P3a counts and skips them.

**Literal equality** is equality of the canonical object: datatype, lexical form, precision, calendar, unit,
bounds, language. `"2023"`/`year` and `"2023"`/`day` are different literals (scenario S-FIND-003). The "finer
refines coarser" relation is a C5 matching rule (`truncate_to_gold`, §9.2), not identity [R05 §2.2.1].

**Special values.** `somevalue` counts in arity, satisfies a role's `min`, and is never equal to anything for
`must_differ` (two unknown partners may be the same person). `novalue` does not count in arity, satisfies `min`
(the role was addressed), and cannot share its role with another value (M70). `unbound` does not count in arity;
in a goal, missing required roles are warnings, not errors (§2.10).

### 2.7 Arity (settled)

> **arity** = the number of bindings whose slot is `core`, `qualifier` or `time` and whose value is an entity, a
> literal, a hyperedge reference or `somevalue`. Repeated fillers count once per binding. `novalue`, `unbound` and
> `meta` bindings do not count.
>
> **participants** = the number of distinct values among those bindings (each `somevalue` is its own value).
> **core** = the arity restricted to core bindings.

`record["arity"] = {"arity": …, "core": …, "participants": …}` is materialised, so P3a's histogram, C5's bins
(`0-1`, `2`, `3`, `4`, `5+`) and P9's stratified scores all read the same number [R01 C1-R16, D-06; R05 §1 item 5].
Examples from the gate fixture **[validated]**:

| Fact | Bindings | arity / core / participants |
|---|---|---|
| `khg:f02-trial` | metformin as intervention and as background therapy, insulin, HbA1c | 4 / 4 / 3 |
| `khg:f03-regulates` | TP53 as regulator and target, HeLa | 3 / 2 / 2 |
| `khg:f05-route` | operator, stops YYZ, ORD, YYZ, flight number | 5 / 4 / 4 |
| `khg:f09-married` | Zoë, `somevalue`, start time 1990 | 3 / 2 / 3 |
| `khg:f10-catalysis` | reaction R1, catalyst `novalue` | 1 / 1 / 1 |
| `khg:f14-goal` | treatment `unbound`, condition T1DM | 1 / 1 / 1 |

The KB sample's own `edges[].attrs.arity` agrees with this rule on all three of its facts **[validated]**. The
rule counts qualifier and time bindings, as the WikiPeople and JF17K statistics do when they count qualifier values
[R01 D-06]. P3a should confirm it before C4 is built (§14, Q1).

### 2.8 Nesting

A binding whose value is `{"hyperedge": id}` makes a fact about a fact. Three checks, all in L3: the referenced id
exists (`C-HYPEREDGE-REF`); the referencing usage allows hyperedge fillers of that relation and the
referenced relation is `nestable` (M68); the graph of references is acyclic (M67) [R01 C1-R23, C1-R24; META §1].
Depth is unbounded in C1 and one level in the gate and the conformance scenarios [R01 D-11].
Supersession is **not** nesting: it is its own record kind (§2.13), so it never pollutes `incident()` or the arity
histogram.

### 2.9 Time

**Valid time** is on the hyperedge [F7; R01 C1-R46]: `valid_time = {"from"?, "to"?, "end_cause"?}`, half-open
`[from, to)`. An absent `from` is minus infinity, an absent `to` plus infinity; there is no sentinel date
[R04 M4]. A bound is a string in one of four granularities (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`,
`YYYY-MM-DDThh:mm:ssZ`, Gregorian).

**Comparison rule (one rule, written down):** a bound denotes the first instant of its period. `"2019"` is
2019-01-01T00:00:00Z. A fact is valid at instant `t` iff `lower(from) <= t < lower(to)`. `as_of` in queries is a
bound string read the same way. The rule is conservative for a coarse `to` (an end in "2021" is read as ending at
the start of 2021); the precision stays in the string, and in the time binding, for anyone who needs another reading
(§14, Q3).

**Derivation from time bindings.** The schema's `time_model` names the roles (`from_role`, `to_role`,
`point_role`). `normalize()` sets `valid_time.from` from the `from_role` binding and `valid_time.to` from the
`to_role` binding; a `point_role` binding without the others gives `[t, next(t))`, the precision-wide interval
(`point_in_time` 2023/year gives `{"from": "2023", "to": "2024"}`). A record that has time bindings and a
`valid_time` that disagrees is rejected (M59). Relations without time roles set `valid_time` directly (P7's memory
traces, `chief_executive` in the fixture). Julian-calendar day-precision dates are converted to Gregorian through
the Julian day number (test: Julian 1582-10-05 = Gregorian 1582-10-15); coarser Julian values are used unchanged.

| Wikidata | C1 |
|---|---|
| `P580` start time | binding `start_time` (slot `time`), gives `valid_time.from` |
| `P582` end time | binding `end_time` (slot `time`), gives `valid_time.to` |
| `P585` point in time | binding `point_in_time` (slot `time`), gives `[t, next(t))` when no start/end |
| `P1534` end cause | `valid_time.end_cause` (an Id) |
| `P1319`, `P1326`, `P8554`, `P8555`, `P12506` (date uncertainty) | slot `meta` bindings in 1.0; `valid_from_bounds`/`valid_to_bounds` in 1.1 [R04 M4] |

**Transaction time** is `recorded_at` on each immutable version; a version's end is the next version's
`recorded_at`, derived by the store and never written into a record (so a stored version never changes, F8).
`as_at` selects, for each id, the version with the largest `recorded_at <= as_at`.

**A fact that ended in the world is not superseded (F7).** Louis XIV's `position_held` has `valid_time
[1643-05-14, 1715-09-01)` and status `asserted`; the Alice/Bob pair is a belief revision and uses a supersession
record [R04 M5].

### 2.10 Status, rank, visibility and the transition table

| `status` | Meaning | Unbound allowed | Evidence required | Seen by default reads |
|---|---|---|---|---|
| `candidate` | proposed; lives only in C3 payloads (F9); `put()` refuses it | no | yes (C3) | never in a store |
| `asserted` | believed | no | yes | yes |
| `disputed` | conflicting claims for the same key and interval are both kept [R01 §6.3 case 3b] | no | yes | no (opt in) |
| `superseded` | replaced as belief by a supersession record (F8) | no | yes | no |
| `retracted` | withdrawn without a replacement | no | yes | no |
| `goal` | a pattern with open slots (P11) | yes | no | no (opt in) |

`rank` (`preferred`, `normal`, `deprecated`, plus `rank_reason`) is editorial and never implies falsehood
[R04 M5, "deprecated is not false"]. Default reads exclude `deprecated`, as Wikidata's queries do. `visibility`
(`visible`, `suppressed`) is governance; default reads exclude `suppressed`; nothing is ever deleted.

Status changes are events (§6.1), never a silent edit:

| From \ to | asserted | disputed | superseded | retracted | goal |
|---|---|---|---|---|---|
| (new record) | `put` | `put` | no | no | `put` |
| asserted | | `transition` | `supersede` | `transition` | no |
| disputed | `transition` | | `supersede` | `transition` | no |
| goal | `transition` (no unbound left, evidence present) | no | no | `transition` | `put` of a new version |
| superseded, retracted | terminal in 1.0 | | | | |

Status-dependent validation [R01 C1-R72]: in a goal (and a candidate) a missing required role is a warning, not an
error; `unbound` is legal only in a goal; evidence is required for every status except goal.

### 2.11 Confidence

`confidence = {"value": number, "scale": Sym, "method"?: string}`; the scale must be declared in the schema with its
range (`probability` 0..1, an LLM score `llm-1-10` 1..10, and so on) and the value must lie in it (M76)
[R01 C1-R49]. It may sit on the hyperedge (aggregate belief, recomputable [R04 M6]) and on each evidence record
(the extractor's own score for that event). It is never an identity field and never a HIF `weight` [R01 D-13;
R03 D6].

### 2.12 Evidence

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `eid` | local id | yes | unique within the record |
| `type` | `curated` \| `imported` \| `extracted` \| `inferred` \| `agent_bound` | yes | evidence type [R04 O7]; ECO cross-references: curated -> ECO:0000352 (evidence used in manual assertion); imported -> ECO:0000313; extracted -> ECO:0007669; inferred (completion, P8) -> ECO:0000501; agent_bound (P11) -> ECO:0000501 or ECO:0000352 by `mode` |
| `mode` | `manual` \| `automatic` \| `semi_automatic` | yes | EARL assertion mode [R04 M6] |
| `source` | `{doc, doc_sha256?, fragment?, url?, revision?, retrieved?, licence?}` | yes | `doc` is an Id; `doc_sha256` is the SHA-256 of the NFC-normalised UTF-8 text and is required when selectors are present (M55); `fragment` holds a source-internal id such as a Wikidata statement GUID, which must not become a C1 id [R04 §3.4] |
| `selectors` | `[{"type":"quote","exact",prefix?,suffix?} \| {"type":"position","start","end"}]` | no | F11: Unicode code points, half-open, over the NFC text; a quote and a position selector together; when both are present `end - start` equals the quote length (M56) |
| `reference` | `[{"prop": Id, "value": Value}]` | no | Wikidata-style reference snaks (`wd:P248` stated in, `wd:P854` URL, `wd:P813` retrieved) |
| `activity` | `{agent, model?, run?, prompt?, params?}` | no | who produced it: extractor and version, model and version, run id, prompt or skill version, decoding parameters [R01 C1-R38] |
| `binding_refs` | `[bid]` | no | evidence for particular bindings (D-20 "evidence on a binding"); must resolve (M54) |
| `confidence` | Confidence | no | the producer's score for this event |
| `event_hash` | `sha256:…` | canonical, iff `type` is `extracted` | §2.2 |

Offsets from other conventions (UTF-16 code units, inclusive ends as in SemMedDB) are converted at import
[R04 M6, O8]. The fixture's `khg:f07-zurich` has a German sentence whose `ü` and `ä` make code-point, UTF-8 and
UTF-16 offsets differ, which is why it is in the fixture.

### 2.13 Supersession record

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `kind` | `"supersession"` | yes | |
| `id` | Id | yes | |
| `superseded` | Id | yes | the fact no longer believed |
| `superseding` | Id | yes | the fact that replaces it |
| `reason` | `incorrect` \| `unconfirmed` \| `conflation` \| `withdrawn` \| `duplicate` \| `refined` | yes | modelled on Wikidata `P2241` reasons [R04 M5] |
| `reason_detail` | string | no | |
| `recorded_at`, `recorded_by` | timestamp, string | in containers | |
| `evidence` | `[Evidence]`, at least one | yes | what decided it [R01 C1-R42] |

One record links one pair; merges (n to 1) and splits (1 to n) are several records written by one atomic event
(§6.1), and the walk handles the resulting DAG. Invariants (L3, M77-M79): both ends exist; no fact supersedes
itself; the links are acyclic; a fact has status `superseded` iff at least one record names it, and its
`superseded_by` equals the set of superseding ids. A pair with different relations or key digests draws a warning,
not an error, because P7 owns identity semantics.

```json
{
  "kind": "supersession",
  "id": "khg:s01",
  "recorded_at": "2026-09-23T11:00:00Z",
  "recorded_by": "p2-gate-fixture/1.0.0",
  "evidence": [
    {
      "eid": "ev1",
      "type": "curated",
      "mode": "manual",
      "source": {"doc": "doc:acme-pr-2021"},
      "activity": {"agent": "curator:reviewer-1"}
    }
  ],
  "superseded": "khg:f11-ceo-alice",
  "superseding": "khg:f12-ceo-bob",
  "reason": "incorrect",
  "reason_detail": "the 2019 press release named the wrong person; corrected in 2021"
}
```

```json
{
  "kind": "hyperedge",
  "id": "khg:f11-ceo-alice",
  "version": 2,
  "recorded_at": "2026-09-23T11:00:00Z",
  "recorded_by": "p2-gate-fixture/1.0.0",
  "change": {"op": "supersede", "ref": "khg:s01"},
  "schema": "p2-gate/1.0.0",
  "relation": "chief_executive",
  "status": "superseded",
  "rank": "normal",
  "visibility": "visible",
  "valid_time": {"from": "2019-01-01"},
  "bindings": [
    {"bid": "b1", "role": "organisation", "slot": "core", "direction": "tail", "value": {"entity": "org:Acme"}},
    {"bid": "b2", "role": "person", "slot": "core", "direction": "head", "value": {"entity": "x:Alice"}}
  ],
  "evidence": [
    {
      "eid": "ev1",
      "type": "curated",
      "mode": "manual",
      "source": {"doc": "doc:acme-pr-2019"},
      "activity": {"agent": "curator:reviewer-1"}
    }
  ],
  "superseded_by": ["khg:f12-ceo-bob"],
  "arity": {"arity": 2, "core": 2, "participants": 2},
  "keys": {
    "content": "sha256:b69ad50b61f8ff24258f49a2c9be0246444b7ed5089f8aa24e8ecfa57691e43f",
    "core": "sha256:9031158fbbc0edff06b6110b4d43942c265ee3d6f51dd1e8b502a54a973f8c9e",
    "key": "sha256:1bcb00fd07a8146ddb6aa5c24b83de5076596794221dc483f2daec7c1bf565fb"
  }
}
```

### 2.14 Canonical form, `normalize()`, projections and text

`normalize(record, schema)` is the single function every writer calls (P3a's builder, P9's `make_candidate`, the
store's `put`). In order: materialise `rank`/`visibility` defaults and `schema`; copy `slot` and `direction` from
the role usages; sort bindings canonically; derive `valid_time` from time bindings (§2.9); compute `arity` (§2.7);
compute `keys` (§2.2); compute `event_hash` on extracted evidence; sort evidence by `eid`. The validator runs
the same function and compares (`R-DERIVED`), so a consumer can trust derived fields after validation.

Derived views, all deterministic, in `khg_contracts.record`:

- `render_text(record, labels)`: `relation(core role: label; ... | qualifier role: label; ...) [valid from, to)`,
  core bindings, then qualifier bindings after `|`, each group in canonical binding order (§2.5, so ordered roles by
  position and no schema is needed); time bindings appear only as the `[from, to)` suffix and meta bindings are left
  out; literals by lexical form with unit or language, `(some value)`, `(no value)`, `?` for unbound. `labels` maps
  an entity id to its entity record or to a label string, so the dict `get_many` returns works as is; an id with no
  label renders as the id. P7's flat baseline and P10's prompts use it [R01 C1-R61].
- `entity_ids(records)`: the sorted, distinct entity ids bound in the records, which is what P7 and P10 pass to
  `get_many` to fetch labels in one call.
- `project.positional(record, schema)`: one fixed role order per relation (schema usage order; repeated unordered
  fillers sorted by canonical value). `project.hyper_relational(record, schema)`: main triple from `primary` plus
  sorted qualifier pairs. `project.role_value_set(record)` [R01 C1-R58]. P3b feeds models from these.

### 2.15 Examples from the gate fixture

The treats fact: two evidence records, one extracted with a span and an event hash, one curated and attached to
the `dose` binding; a quantity with a unit; a decimal; a direction on the core roles only.

```json
{
  "kind": "hyperedge",
  "id": "khg:f01-treats",
  "version": 1,
  "recorded_at": "2026-09-23T10:00:00Z",
  "recorded_by": "p2-gate-fixture/1.0.0",
  "change": {"op": "put"},
  "schema": "p2-gate/1.0.0",
  "relation": "treats",
  "status": "asserted",
  "rank": "normal",
  "visibility": "visible",
  "valid_time": {"from": "2024-01-01"},
  "bindings": [
    {"bid": "b2", "role": "condition", "slot": "core", "direction": "head", "value": {"entity": "disease:T2DM"}},
    {
      "bid": "b3",
      "role": "dose",
      "slot": "qualifier",
      "value": {"datatype": "quantity", "literal": "500", "unit": "wd:Q3241121"}
    },
    {"bid": "b5", "role": "hba1c_change", "slot": "qualifier", "value": {"datatype": "decimal", "literal": "-1.12"}},
    {"bid": "b4", "role": "population", "slot": "qualifier", "value": {"entity": "pop:adults"}},
    {"bid": "b1", "role": "treatment", "slot": "core", "direction": "tail", "value": {"entity": "drug:metformin"}}
  ],
  "confidence": {"scale": "probability", "value": 0.95},
  "evidence": [
    {
      "eid": "ev1",
      "type": "extracted",
      "mode": "automatic",
      "source": {"doc": "doc:soc-2024", "doc_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739"},
      "selectors": [
        {
          "exact": "Metformin is the preferred initial pharmacologic agent for the treatment of type 2 diabetes in adults.",
          "type": "quote"
        },
        {"end": 102, "start": 0, "type": "position"}
      ],
      "activity": {
        "agent": "p9-extractor/0.1.0",
        "model": "model-y/2026-08",
        "params": {"seed": 13, "temperature": 0},
        "prompt": "treats-skill/1.2.0",
        "run": "r1"
      },
      "confidence": {"scale": "probability", "value": 0.9},
      "event_hash": "sha256:ec92cafb15cde9c2454f34b99581c8a85537289c02a4f27eb1af576a6698fb17"
    },
    {
      "eid": "ev2",
      "type": "curated",
      "mode": "manual",
      "source": {"doc": "doc:soc-2024", "doc_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739"},
      "selectors": [
        {"exact": "The usual starting dose is 500 mg", "type": "quote"},
        {"end": 136, "start": 103, "type": "position"}
      ],
      "activity": {"agent": "curator:reviewer-1"},
      "binding_refs": ["b3"]
    }
  ],
  "arity": {"arity": 5, "core": 2, "participants": 5},
  "keys": {
    "content": "sha256:09c8cc13dc74f8c3f6f2db9d3bdff24860523db953aeb713dc80eb6e1d1dc6d7",
    "core": "sha256:55449857f34d1a8a27ef8c72d6117c4a882cc055e83a3b572db6f7e0f0966b57"
  }
}
```

The Zürich population count: a temporal key on `place`, a `point_in_time` that derives a precision-wide valid
time, an imported Wikidata-style reference, and a code-point span over a German sentence.

```json
{
  "kind": "hyperedge",
  "id": "khg:f07-zurich",
  "version": 1,
  "recorded_at": "2026-09-23T10:00:00Z",
  "recorded_by": "p2-gate-fixture/1.0.0",
  "change": {"op": "put"},
  "schema": "p2-gate/1.0.0",
  "relation": "population_count",
  "status": "asserted",
  "rank": "preferred",
  "visibility": "visible",
  "valid_time": {"from": "2023", "to": "2024"},
  "bindings": [
    {
      "bid": "b2",
      "role": "count",
      "slot": "core",
      "value": {"datatype": "quantity", "literal": "443037", "lower": "443000", "unit": "1", "upper": "443100"}
    },
    {"bid": "b1", "role": "place", "slot": "core", "value": {"entity": "x:Zürich"}},
    {
      "bid": "b3",
      "role": "point_in_time",
      "slot": "time",
      "value": {"datatype": "time", "literal": "2023", "precision": "year"}
    }
  ],
  "evidence": [
    {
      "eid": "ev1",
      "type": "imported",
      "mode": "automatic",
      "source": {"doc": "wd:Q72"},
      "reference": [
        {"prop": "wd:P248", "value": {"entity": "x:stat-zurich-2023"}},
        {"prop": "wd:P813", "value": {"datatype": "time", "literal": "2026-09-20", "precision": "day"}}
      ],
      "activity": {"agent": "p3a-builder/0.1.0", "run": "dump-2026-09-15"}
    },
    {
      "eid": "ev2",
      "type": "extracted",
      "mode": "automatic",
      "source": {"doc": "doc:zh-stat-2023", "doc_sha256": "5cc4f38f1c32b9bd8bd165d4f7a3e8b1d2b29d8688f43b50bd55bc8a337955c0"},
      "selectors": [{"exact": "Zürich zählte Ende 2023 443 037", "type": "quote"}, {"end": 41, "start": 10, "type": "position"}],
      "activity": {"agent": "p9-extractor/0.1.0", "model": "model-y/2026-08", "run": "r1"},
      "event_hash": "sha256:eae1a537297e8379ebdd309ea3387e902b070bd632d93bfe42c4a8d277aa89e8"
    }
  ],
  "arity": {"arity": 3, "core": 2, "participants": 3},
  "keys": {
    "content": "sha256:b9f1d2136f03fa83c77df11eb0d857a1961b68a4a89877fb5fa1fc6c19073fd3",
    "core": "sha256:1620544ef9f0ebb04ba9e80b765d71aeec83f6d66d1a8957bf6c7039b969de35",
    "key": "sha256:9909c7eec0939612411d1a28410e33647493a05ad87305df39848efd35616c31"
  }
}
```

A goal with an unbound slot (P11's shape, representable in 1.0):

```json
{
  "kind": "hyperedge",
  "id": "khg:f14-goal",
  "version": 1,
  "recorded_at": "2026-09-23T10:00:00Z",
  "recorded_by": "p2-gate-fixture/1.0.0",
  "change": {"op": "put"},
  "schema": "p2-gate/1.0.0",
  "relation": "treats",
  "status": "goal",
  "rank": "normal",
  "visibility": "visible",
  "bindings": [
    {"bid": "b2", "role": "condition", "slot": "core", "direction": "head", "value": {"entity": "disease:T1DM"}},
    {
      "bid": "b1",
      "role": "treatment",
      "slot": "core",
      "direction": "tail",
      "value": {"expects": {"entity_types": ["Drug"]}, "special": "unbound"}
    }
  ],
  "arity": {"arity": 1, "core": 1, "participants": 1},
  "keys": {
    "content": "sha256:8cdef4395484060b4ede55850f0c61c5f2f3cbf3f52f8ea25e1c7ecae278a9d7",
    "core": "sha256:681ea421d08c12073dc6a5ec60baa8177b93fb635180c22de2bff79756d8e85a"
  }
}
```

---

## 3. Relation-type schema language

Format id **`khg-relation-schema/1.0.0`** (versioned with C1). A schema document is JSON, validated by the draft-07
meta-schema `khg-relation-schema-1.0.0.schema.json` and by the D-code checks of §3.7. Its concepts mirror LinkML
(global slots, per-class `slot_usage`, `unique_keys`) so that a LinkML export is mechanical, and it adds what no
existing language has together: temporal keys with a declared collision policy, slot classes, co-occurrence
constraints, and a semver id [R04 M8, O10; R01 D-15].

### 3.1 Document fields

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `kind` | `"relation-schema"` | yes | |
| `format` | `"khg-relation-schema/1.<m>.<p>"` | yes | language version |
| `id` | `[a-z][a-z0-9-]{0,63}` | yes | schema id, for example `p3a-wikidata` |
| `version` | semver | yes | the schema's own version (M90); records cite `id/version` |
| `label`, `description` | string | no | |
| `entity_types` | `[{id, label, parents?, same_as?}]` | no | a type hierarchy; filler checks accept a subtype (`Airline` is an `Organisation`) |
| `confidence_scales` | `[{id, kind: probability\|bounded, min, max}]` | no | the scales `confidence.scale` may name |
| `time_model` | `{from_role?, to_role?, point_role?}` | no | which global roles derive `valid_time` (§2.9) |
| `roles` | `[{id, label, description?, aliases?, same_as?}]`, at least one | yes | the **global** role vocabulary (F4): one identity per role across all relations [R01 C1-R26; R04 O1] |
| `relations` | `[Relation]`, at least one | yes | relation types, below |

Relation type:

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `id`, `label` | Sym, string | yes | |
| `kind` | `fact` \| `meta` \| `rule` | yes | what the hyperedges of this relation are: n-ary facts; facts about facts; rule hyperarcs (tail to head) [R01 C1-R05] |
| `roles` | `[Usage]`, at least one | yes | the per-relation usage declarations (M91) |
| `key` | `{roles, temporal, on_collision}` | no | declared key role set (§3.3) |
| `primary` | `{subject, object}` | no | the triple view: two core usages with `max` 1 (M95) [R01 C1-R18] |
| `constraints` | `[Constraint]` | no | co-occurrence constraints (§3.4) |
| `nestable` | boolean, default false | no | whether hyperedges of this relation may be referenced from other facts [R01 C1-R24] |
| `aliases`, `same_as` | lists | no | raw extracted phrases; external mappings (`wd:P39`, FrameNet frames) [R01 C1-R31] |

### 3.2 Role usage

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `role` | Sym | yes | a role id from the global vocabulary (M97) |
| `slot` | `core` \| `qualifier` \| `time` \| `meta` | yes | slot class (§2.5) |
| `fillers` | object, at least one key | yes | `entity_types: [Sym]` (with subtypes); `datatypes: [dt]`; `precisions: [p]` (time); `units: [Id \| "1"]` (quantity); `hyperedge: {relations: [Sym \| "*"]}` |
| `min` | int >= 0 | yes | within-fact multiplicity: the least number of bindings of this role (`required` = `min >= 1`) |
| `max` | int >= 1 or `null` | yes | the most; `null` is unbounded [R04 §1.3: within-fact vs across-fact cardinality] |
| `ordered` | boolean | no | bindings carry positions `0..n-1` |
| `direction` | `tail` \| `head` | no | the direction every binding of this role gets |
| `label`, `aliases` | | no | a local label for this usage (VerbNet/LinkML style) |

Interchangeable and symmetric participation is a repeated, unordered role (`agent` with `min` 2, `max` `null`;
`partner` with `min` = `max` = 2), never numbered roles [R04 §1.5]. Across-fact participation ("one CEO per
organisation at a time") is not a usage property: it is the key.

### 3.3 Keys and collision policies

`key = {"roles": [...], "temporal": bool, "on_collision": policy}`. Key roles must be usages with `min >= 1`
(M93, M94), so the digest is always defined. With `temporal: true`, two current `asserted` records collide when
their key digests are equal **and** their valid times overlap (SQL:2011 `WITHOUT OVERLAPS`); with `false`, equal
digests collide whatever the time [R04 §3.3]. Goals and candidates never collide.

The store never resolves a collision silently: `put()` raises `KeyCollision(conflicts, suggested=policy)` for every
policy. The policy tells the linter which proposal to raise and tells P7 which of the four deployed semantics the
relation means [R04 §3.3, O3; risk 1 in R04 §11]:

| `on_collision` | Meaning | Linter action (§7.6) | What the caller then does | Precedent |
|---|---|---|---|---|
| `reject` (default) | the second fact is an error | violation, reject | fix the data | SQL:2011, PostgreSQL 18 temporal keys |
| `close_older` | the world changed: the older fact ended | info with a suggested `end_validity` | `apply(end_validity)` then `put` | Wikidata "outdated -> add end time" [R04 M5] |
| `supersede` | belief revision: the older record was wrong | info + `supersession_proposal` | `apply(supersede)` | nanopub `npx:supersedes` [R04 M5] |
| `merge` | same fact | info + `merge_proposal` (duplicate) | `apply(add_evidence)` on the older | OWL 2 `HasKey` identity [R04 §3.3] |
| `dispute` | genuine conflict, keep both | info | `transition` both to `disputed` | Wikidata ranks and disputed claims |

Wikidata's single-value constraint with separators maps onto a key: key roles = subject role + separator
qualifiers; `temporal: false` when the separator is `point_in_time`, or the time roles are left out and
`temporal: true` is used, as the fixture's `population_count` does [R04 §3.3].

### 3.4 Constraints

`{"type": "requires", "if": role, "then": role}`; `{"type": "excludes", "roles": [...]}` (not more than one);
`{"type": "at_least_one_of", "roles": [...]}` (FrameNet's CoreSet); `{"type": "must_differ", "roles": [...]}` (all
fillers of the listed roles pairwise distinct; special values never count as equal) [R04 §1.2; R01 C1-R34].
Violations are `S-CONSTRAINT` errors (M75). `must_agree` comes in 1.1.

### 3.5 Example (six relation types)

A subset of the gate schema: `treats` (primary pair, qualifiers, a literal-valued role), `co_administration_causes`
(an interchangeable, symmetric `agent` role), `married` (a symmetric binary relation with `must_differ`),
`position_held` (time roles and a temporal key with `close_older`), `chief_executive` (a temporal key with
`supersede`) and `reported_in` (a meta relation whose filler is a hyperedge of a `nestable` relation). It validates
against the meta-schema and passes every D-check **[validated]**.

```json
{
  "kind": "relation-schema",
  "format": "khg-relation-schema/1.0.0",
  "id": "p2-gate-example",
  "version": "1.0.0",
  "label": "six relation types from the P2 gate schema",
  "entity_types": [
    {"id": "Thing", "label": "thing"},
    {"id": "Drug", "label": "drug", "parents": ["Thing"]},
    {"id": "Disease", "label": "disease", "parents": ["Thing"]},
    {"id": "Population", "label": "population", "parents": ["Thing"]},
    {"id": "AdverseEffect", "label": "adverse effect", "parents": ["Thing"]},
    {"id": "Organisation", "label": "organisation", "parents": ["Thing"]},
    {"id": "Person", "label": "person", "parents": ["Thing"]},
    {"id": "Position", "label": "position", "parents": ["Thing"]},
    {"id": "Document", "label": "document", "parents": ["Thing"]}
  ],
  "confidence_scales": [
    {"id": "probability", "kind": "probability", "min": 0, "max": 1},
    {"id": "llm-1-10", "kind": "bounded", "min": 1, "max": 10}
  ],
  "time_model": {"from_role": "start_time", "to_role": "end_time"},
  "roles": [
    {"id": "agent", "label": "agent"},
    {"id": "condition", "label": "condition"},
    {"id": "dose", "label": "dose"},
    {"id": "effect", "label": "effect"},
    {"id": "end_time", "label": "end time"},
    {"id": "hba1c_change", "label": "hba1c change"},
    {"id": "holder", "label": "holder"},
    {"id": "organisation", "label": "organisation"},
    {"id": "partner", "label": "partner"},
    {"id": "person", "label": "person"},
    {"id": "population", "label": "population"},
    {"id": "position", "label": "position"},
    {"id": "report", "label": "report"},
    {"id": "start_time", "label": "start time"},
    {"id": "statement", "label": "statement"},
    {"id": "treatment", "label": "treatment"}
  ],
  "relations": [
    {
      "id": "treats",
      "label": "treats",
      "kind": "fact",
      "nestable": true,
      "aliases": ["is used to treat"],
      "primary": {"subject": "treatment", "object": "condition"},
      "roles": [
        {
          "role": "treatment",
          "slot": "core",
          "fillers": {"entity_types": ["Drug"]},
          "min": 1,
          "max": 1,
          "direction": "tail"
        },
        {
          "role": "condition",
          "slot": "core",
          "fillers": {"entity_types": ["Disease"]},
          "min": 1,
          "max": 1,
          "direction": "head"
        },
        {"role": "dose", "slot": "qualifier", "fillers": {"datatypes": ["quantity"]}, "min": 0, "max": 1},
        {"role": "population", "slot": "qualifier", "fillers": {"entity_types": ["Population"]}, "min": 0, "max": 1},
        {"role": "hba1c_change", "slot": "qualifier", "fillers": {"datatypes": ["decimal"]}, "min": 0, "max": 1}
      ]
    },
    {
      "id": "co_administration_causes",
      "label": "co-administration causes",
      "kind": "fact",
      "roles": [
        {
          "role": "agent",
          "slot": "core",
          "fillers": {"entity_types": ["Drug"]},
          "min": 2,
          "max": null,
          "direction": "tail"
        },
        {
          "role": "effect",
          "slot": "core",
          "fillers": {"entity_types": ["AdverseEffect"]},
          "min": 1,
          "max": 1,
          "direction": "head"
        }
      ]
    },
    {
      "id": "position_held",
      "label": "position held",
      "kind": "fact",
      "key": {"roles": ["position"], "temporal": true, "on_collision": "close_older"},
      "roles": [
        {"role": "holder", "slot": "core", "fillers": {"entity_types": ["Person"]}, "min": 1, "max": 1},
        {"role": "position", "slot": "core", "fillers": {"entity_types": ["Position"]}, "min": 1, "max": 1},
        {"role": "start_time", "slot": "time", "fillers": {"datatypes": ["time"]}, "min": 0, "max": 1},
        {"role": "end_time", "slot": "time", "fillers": {"datatypes": ["time"]}, "min": 0, "max": 1}
      ]
    },
    {
      "id": "married",
      "label": "married",
      "kind": "fact",
      "constraints": [{"type": "must_differ", "roles": ["partner"]}],
      "roles": [
        {"role": "partner", "slot": "core", "fillers": {"entity_types": ["Person"]}, "min": 2, "max": 2},
        {"role": "start_time", "slot": "time", "fillers": {"datatypes": ["time"]}, "min": 0, "max": 1}
      ]
    },
    {
      "id": "chief_executive",
      "label": "chief executive",
      "kind": "fact",
      "key": {"roles": ["organisation"], "temporal": true, "on_collision": "supersede"},
      "roles": [
        {
          "role": "organisation",
          "slot": "core",
          "fillers": {"entity_types": ["Organisation"]},
          "min": 1,
          "max": 1,
          "direction": "tail"
        },
        {
          "role": "person",
          "slot": "core",
          "fillers": {"entity_types": ["Person"]},
          "min": 1,
          "max": 1,
          "direction": "head"
        }
      ]
    },
    {
      "id": "reported_in",
      "label": "reported in",
      "kind": "meta",
      "roles": [
        {
          "role": "statement",
          "slot": "core",
          "fillers": {"hyperedge": {"relations": ["treats"]}},
          "min": 1,
          "max": 1,
          "direction": "head"
        },
        {
          "role": "report",
          "slot": "core",
          "fillers": {"entity_types": ["Document"]},
          "min": 1,
          "max": 1,
          "direction": "tail"
        }
      ]
    }
  ]
}
```

### 3.6 How P6 parses a schema into a hypergraph

`schema_hypergraph(schema, slots=("core", "qualifier", "time")) -> {"vertices": [...], "hyperedges": {...}}`.
The rule for "attribute" [R01 C1-R27]: an attribute is a **global role id**; each relation type is one hyperedge
whose vertices are the role ids of its usages whose slot is in `slots`; `meta` usages are excluded unless asked
for. Vertices and hyperedge members are sorted, so the output is deterministic. Global roles are what make the
measurement meaningful: with relation-local roles every schema hypergraph is a disjoint union and trivially
acyclic [R04 §8.2]. The example above gives **[validated]**:

```json
{
  "vertices": [
    "agent",
    "condition",
    "dose",
    "effect",
    "end_time",
    "hba1c_change",
    "holder",
    "organisation",
    "partner",
    "person",
    "population",
    "position",
    "report",
    "start_time",
    "statement",
    "treatment"
  ],
  "hyperedges": {
    "chief_executive": ["organisation", "person"],
    "co_administration_causes": ["agent", "effect"],
    "married": ["partner", "start_time"],
    "position_held": ["end_time", "holder", "position", "start_time"],
    "reported_in": ["report", "statement"],
    "treats": ["condition", "dose", "hba1c_change", "population", "treatment"]
  }
}
```

The GYO reduction of this hypergraph empties it (alpha-acyclic); the triangle fixture's hypergraph
`{"r1": ["a", "b"], "r2": ["b", "c"], "r3": ["a", "c"]}` does not reduce (alpha-cyclic), as P6's gate
requires **[validated]**.

P2 ships `tests/fixtures/schemas/cyclic.schema.json`, three relations `r1(a, b)`, `r2(b, c)`, `r3(c, a)`, whose
hypergraph is a triangle and therefore alpha-cyclic, for P6's "constructed cyclic case". How the main-snak roles of
Wikidata properties are named is P3a's and P6's decision; the P6 probe showed it does not change alpha-acyclicity
[R04 §8.2], so the language does not fix it.

### 3.7 What the validator checks against a schema

Schema documents (D-codes): semver version (M90), at least one usage per relation (M91), no role used twice in one
relation (M92), key roles are usages (M93) and required (M94), `primary` names core usages with `max` 1 (M95),
known entity types and acyclic `parents` (M96), usages only of declared global roles (M97), `min <= max` (M98),
`kind` in the enum (M99), known relations in `fillers.hyperedge.relations`, `precisions`/`units` only with
time/quantity, time-model roles exist as time-slot usages (warning).

Records against the schema (S-codes): relation declared (M60); role allowed (M61); `min` (M62, a warning for goals
and candidates) and `max` (M63); filler kind, entity type with subtypes, datatype, precision and unit (M64, M65);
at least one binding (M66); nesting allowed (M68); `unbound` only in goals (M69); `novalue` alone in its role
(M70); evidence present (M71); direction as declared (M72); positions `0..n-1` on ordered roles (M73); no
duplicate binding in an unordered role (M74); constraints (M75); confidence within its declared scale (M76); and
all derived fields as `normalize()` computes them (M58, M59).

### 3.8 Generators

TypeQL (`relation treats, relates treatment, relates condition; ...` with roles scoped as
`treats:treatment`), SQL DDL for the incidence table (§6.8), SHACL 1.2 shapes (`sh:uniqueValuesFor` for
non-temporal keys) and a LinkML export are SHOULD [R01 D-15] and land in 1.1. P1 writes its own mappings for its
gate; §6.8 fixes what they must preserve.

---

## 4. HIF mapping: the `roles` convention and the khg-hif profile

### 4.1 Two layers

1. **The `roles` convention** (the external artefact, proposed upstream, §12.3): a generic, v1-compatible rule set
   any HIF producer can follow. Incidence `attrs.role` (one string per record); a node that plays several roles in
   one edge appears in one incidence record per role; edge `attrs.relation`; a metadata declaration
   `roles-convention` with an optional `roles-vocabulary`. Nothing else.
2. **The khg-hif profile** (`khg-hif/1.0.0`): how a C1 container is written as HIF so that it comes back exactly.
   Every C1 field goes into `attrs` under a `khg-*` key or into `metadata`; nothing is ever added at the top level
   or at record level (F3; the HIF schema forbids both [R02 §5 cases 04-06, 11, 13, 14]).

Profile-valid implies HIF-valid, because the profile schema `allOf`-includes the vendored HIF schema by its `$id`
(resolved offline; §1.2) [R02 §11 item 2].

### 4.2 The contested choice: one incidence record per role

The three reports disagree on how a node that plays two roles in one fact is written [R01 C1-R63, D-01; R02 §11
item 4; R03 D2; R04 O2].

| Option | For | Against |
|---|---|---|
| (b) one record per (edge, node) with a list `attrs.roles` [R01] | naive readers (HyperNetX's `from_hif`) keep the list in one cell | **cannot express a node that is tail and head of one edge**: HIF `direction` is one value per record [R03 §8, case c06]; per-binding data (position, bid, evidence refs) would need parallel lists; the upstream paper's own example is a single string `{"role": "PI"}` [R02 §3] |
| (c) role-keyed bindings in C1, converted to a role list in HIF [R04 O2] | draft-07 could count repeated roles with `minItems`/`maxItems` | the reason goes away under F5 (role-usage conformance is a Python check); inherits (b)'s direction problem in HIF |
| **(a) one incidence record per binding, repeated (edge, node) pairs allowed** [R02, R03] | the only encoding that expresses tail and head for one node [R02 §3 inconsistency 2; R03 §8]; the paper says a node may be in both tail and head, and an upstream compliant test repeats a pair [R02 §3]; each C1 binding maps to exactly one record, so `bid`, `position` and `direction` each have a home; the KB's own sample already writes one `attrs.role` string per record; round-tripped exactly through both libraries via the loaders [R03 §7.4] and again here on the gate fixture (3 repeated pairs, 4 chains exact) **[validated]** | readers that do not use P2's loaders lose the second record of a pair (HyperNetX keeps the first [R03 §3 row 3]); both libraries need adapter work under any option [R03 D2] |

**Decision: (a).** A duplicate record means the same `(edge, khg-bid)` twice (M25), or the same role, value and
position twice in C1 (M74); a repeated `(edge, node)` pair with different roles or positions is legal. The cost to
naive readers is documented and is the first item of the upstream proposal (readers must keep repeated pairs). The
key is `role`, singular, matching the paper, the upstream test and the KB sample [R02 §6 item 2]; `roles` survives
only as the convention's name and as a list form accepted by the foreign importer (§4.5).

### 4.3 C1 to HIF, exactly

`to_hif(records, *, network_type="auto", relations=None) -> dict`:

- **E1 Edges.** One edge record per hyperedge and per supersession record, `edge` = the C1 id.
- **E2 Edge attrs.** `relation` = the relation; `khg-kind` = `hyperedge` or `supersession`; every other C1 field
  `f` except `kind`, `id`, `relation`, `bindings` (hyperedges) or `superseded`, `superseding` (supersessions) goes
  to `khg-` + `f` with `_` replaced by `-` (`recorded_at` -> `khg-recorded-at`, `valid_time` -> `khg-valid-time`,
  `evidence` -> `khg-evidence`). One rule, no exceptions, flat dash-case keys as the paper recommends [R02 §3].
  Supersession edges get `relation` = `khg-supersedes`.
- **E3 Incidences.** One incidence per binding whose value is an entity, a literal or a hyperedge reference:
  `{"edge": id, "node": node_id(value), "direction"?: b.direction, "attrs": {"role": b.role, "khg-bid": b.bid,
  "khg-slot": b.slot, "khg-position"?: b.position}}`. A supersession edge has two incidences: role `superseding`,
  direction `tail`, and role `superseded`, direction `head`, each to a hyperedge mirror node.
- **E4 Special values** have no participant, so they are not incidences: bindings with `somevalue`, `novalue` or
  `unbound` are written verbatim to the edge's `khg-special-bindings`. A goal whose slots are all unbound is an edge
  without incidences, which HIF permits [R01 D-18; R02 §5 case 27].
- **E5 Entity nodes.** One node per entity record: `{"node": id, "attrs": {"khg-kind": "entity", "label": ...,
  "khg-types": [...], "khg-aliases"?, "khg-same-as"?}}`, including entities no fact uses (isolated nodes).
- **E6 Literal nodes, shared by value** [R01 D-09]: id `khg-lit:` + the first 32 hex digits of the SHA-256 of the
  literal's canonical JSON; attrs `{"khg-kind": "literal", "label": lexical form, "khg-literal": the literal
  object}`. Equal literals are one node; the id is recomputed and checked on import (M29).
- **E7 Hyperedge mirror nodes** [R01 C1-R67; R02 §11 item 7]: id `khg-ref:` + edge id; attrs `{"khg-kind":
  "hyperedge-ref", "khg-ref": edge id}`. Nesting is read only from this explicit attribute, never from id equality
  (upstream data reuses ids across nodes and edges [R02 §5 case 03]).
- **E8 `network-type`** = `directed` iff every incidence has a direction, otherwise `undirected` (`auto`); an
  explicit `directed` raises if some incidence lacks one. `direction` is always written when the binding has one,
  also in undirected files, which HIF allows [R02 §3.2, case 24]. `asc` is never written [R03 D8].
- **E9 `weight`** is never written on any record [R03 D6; R01 D-13].
- **E10 Metadata** as in §4.6. No `name`, no `default_attrs` (HyperNetX interprets both [R03 D7]).
- **E11 Canonical order.** Nodes by id, edges by id, incidences by `(edge, khg-bid, role, node, direction)`.
- **E12 Slices.** `relations={...}` exports only those relations and the supersession records whose two ends are
  both exported; `metadata["khg-slice"]` records the filter. P5 uses slices to get directed files.

### 4.4 HIF to C1, exactly

`from_hif(doc) -> list[record]` requires `metadata["khg-profile"]` (otherwise §4.5) and inverts E1-E12:

- **I1** L0-L2 first (strict JSON, vendored HIF schema, profile schema).
- **I2** Node and edge ids unique (M24; the libraries disagree on duplicates [R03 D5]); every incidence names a
  declared node and edge (M26, M27); in a directed file every incidence has a direction (M21).
- **I3** Header and schema records from `metadata["khg-header"]` and `metadata["khg-schemas"]`, verbatim.
- **I4** Entity records from `khg-kind: entity` nodes (`label`, and `khg-x` -> field `x`).
- **I5** A hyperedge from each `khg-kind: hyperedge` edge: `relation`; `khg-x` -> field `x` (dash to underscore);
  bindings = one per incidence of the edge plus `khg-special-bindings`. A binding's value is `{"entity": node}` for
  an entity node, the `khg-literal` object for a literal node (after checking the id, M29), `{"hyperedge": ref}` for
  a mirror node (after checking the edge exists, M28). `khg-bid` is unique per edge (M25).
- **I6** A supersession record from each `khg-kind: supersession` edge, its ends from the `superseding` and
  `superseded` incidences.
- **I7** Bindings in canonical order; records in container order; then the full L3 container check (§8.1).

Round trip: `from_hif(to_hif(c)) == c` for every valid container `c` (canonical JSON equality) **[validated]** on
the gate fixture and the migrated sample.

### 4.5 Foreign HIF (no khg profile)

`import_foreign(doc, mapping) -> (records, report)`, used for any HIF file without `khg-profile`, including files
that follow only the `roles` convention and legacy files such as the KB's sample. Nothing is guessed silently:

- **Ids.** A string id that is a valid C1 id stays; another string `s` becomes `hif:` + percent-encoded `s`; an
  integer `n` becomes `hif-int:n`, so `1` and `"1"` stay distinct [R02 §5 case 16]. A collision is an error. The
  mapping is reported so an export can restore the original ids.
- **Roles.** `attrs.role` (string) gives one binding per record; `attrs.roles` (list) gives one binding per element
  with the record's direction; both present and disagreeing is `F-ROLE-CONFLICT` [R01 V20]; neither present gives
  role `member` with a warning and the file is flagged "not role-labelled".
- **Relations.** `edges[].attrs.relation` if present, else the mapping's default relation.
- **Schema.** Generated from observed usages (role -> slot from the mapping, default `core`; fillers from node
  types; `max` from observed counts; direction if consistent per usage) or supplied by the operator.
- **Weights** are dropped and listed in the report, unless the operator passes `--weight-as-confidence <scale>`.
  Weight is never read as confidence by default [R01 PF-11, D-13].
- **Other attrs** map through the mapping file (`source` -> evidence source, `valid-from` -> `valid_time.from`,
  `arity` -> checked against the C1 rule and dropped) or are dropped and reported.
- Imported facts get status `asserted` with one `curated`/`imported` evidence record naming the file, or `candidate`
  queue items when the operator wants them reviewed.

The KB sample migrates with this importer (§11.4) **[validated]**.

### 4.6 The metadata declaration block

| Key | Layer | Req. | Value |
|---|---|---|---|
| `roles-convention` | roles convention | yes | `"1.0.0"`: incidence `attrs.role` and edge `attrs.relation` follow the convention |
| `roles-vocabulary` | roles convention | no | `{role id: {"label", "description"?}}`; when present every incidence role is a key of it (warning in the profile) |
| `hif-schema` | profile | yes | the commit-pinned URL of `hif_schema_v0.1.0.json` at `b691a3d2ec32100c0229ebe1151e9afad015c356` (F2) |
| `hif-schema-sha256` | profile | yes | `639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196` (blob `e2105bb`) |
| `hif-schema-doi` | profile | no | `10.5281/zenodo.17257719` (the v0.1.2 archive the paper calls "the stable schema") [R02 §2.2, §10] |
| `khg-profile` | profile | yes | `"khg-hif/1.0.0"` |
| `khg-header` | profile | yes | the C1 container header, verbatim |
| `khg-schemas` | profile | yes | the relation-type schema documents, verbatim |
| `khg-slice` | profile | no | the export filter, when the file is a slice |

A file with only the first two keys is a valid "roles convention" file that is not a khg-hif file.

### 4.7 The gate fixture as HIF

An excerpt first: the fact where metformin plays two roles in the same direction (two records for one pair), the
fact where TP53 is regulator (tail) and target (head), the ordered route that visits YYZ twice (positions 0 and 2),
a literal node, a mirror node, the special bindings, and the supersession edge.

```jsonc
// incidences: f02 (metformin twice, both tail), f03 (TP53 tail and head), f05 (YYZ at 0 and 2), s01
"incidences": [
  {"edge": "khg:f02-trial", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "intervention", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f02-trial", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "background_therapy", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f02-trial", "node": "drug:insulin", "direction": "tail", "attrs": {"role": "comparator", "khg-bid": "b3", "khg-slot": "core"}},
  {"edge": "khg:f02-trial", "node": "outcome:HbA1c", "direction": "head", "attrs": {"role": "outcome", "khg-bid": "b4", "khg-slot": "core"}},
  {"edge": "khg:f03-regulates", "node": "gene:TP53", "direction": "tail", "attrs": {"role": "regulator", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f03-regulates", "node": "gene:TP53", "direction": "head", "attrs": {"role": "target", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f03-regulates", "node": "cell:HeLa", "direction": "tail", "attrs": {"role": "context", "khg-bid": "b3", "khg-slot": "qualifier"}},
  {"edge": "khg:f05-route", "node": "x:air-canada", "attrs": {"role": "operator", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f05-route", "node": "x:YYZ", "attrs": {"role": "stop", "khg-bid": "b2", "khg-slot": "core", "khg-position": 0}},
  {"edge": "khg:f05-route", "node": "x:ORD", "attrs": {"role": "stop", "khg-bid": "b3", "khg-slot": "core", "khg-position": 1}},
  {"edge": "khg:f05-route", "node": "x:YYZ", "attrs": {"role": "stop", "khg-bid": "b4", "khg-slot": "core", "khg-position": 2}},
  {"edge": "khg:f05-route", "node": "khg-lit:ccbbd652f7fd8dce4c4e4baab2bfd2fc", "attrs": {"role": "flight_number", "khg-bid": "b5", "khg-slot": "qualifier"}},
  {"edge": "khg:s01", "node": "khg-ref:khg:f11-ceo-alice", "direction": "head", "attrs": {"role": "superseded"}},
  {"edge": "khg:s01", "node": "khg-ref:khg:f12-ceo-bob", "direction": "tail", "attrs": {"role": "superseding"}}
]

// nodes: a literal node shared by value, a hyperedge mirror node, an isolated entity
{"node": "khg-lit:ccbbd652f7fd8dce4c4e4baab2bfd2fc", "attrs": {"khg-kind": "literal", "label": "AC 857", "khg-literal": {"literal": "AC 857", "datatype": "string"}}}
{"node": "khg-ref:khg:f02-trial", "attrs": {"khg-kind": "hyperedge-ref", "khg-ref": "khg:f02-trial"}}
{"node": "x:Москва", "attrs": {"khg-kind": "entity", "label": "Москва", "khg-types": ["Place"]}}

// edges: special values ride in khg-special-bindings; the goal edge has no incidences at all
{
  "edge": "khg:f09-married",
  "attrs": {
    "relation": "married",
    "khg-kind": "hyperedge",
    "khg-status": "asserted",
    "khg-rank": "deprecated",
    "khg-rank-reason": "wd:Q25895909",
    "khg-special-bindings": [{"bid": "b2", "role": "partner", "value": {"special": "somevalue"}, "slot": "core"}]
  }
}
{
  "edge": "khg:f14-goal",
  "attrs": {
    "relation": "treats",
    "khg-kind": "hyperedge",
    "khg-version": 1,
    "khg-recorded-at": "2026-09-23T10:00:00Z",
    "khg-recorded-by": "p2-gate-fixture/1.0.0",
    "khg-change": {"op": "put"},
    "khg-status": "goal",
    "khg-schema": "p2-gate/1.0.0",
    "khg-rank": "normal",
    "khg-visibility": "visible",
    "khg-arity": {"arity": 1, "core": 1, "participants": 1},
    "khg-keys": {
      "content": "sha256:8cdef4395484060b4ede55850f0c61c5f2f3cbf3f52f8ea25e1c7ecae278a9d7",
      "core": "sha256:681ea421d08c12073dc6a5ec60baa8177b93fb635180c22de2bff79756d8e85a"
    },
    "khg-special-bindings": [
      {
        "bid": "b1",
        "role": "treatment",
        "value": {"special": "unbound", "expects": {"entity_types": ["Drug"]}},
        "slot": "core",
        "direction": "tail"
      }
    ]
  }
}
{
  "edge": "khg:s01",
  "attrs": {
    "relation": "khg-supersedes",
    "khg-kind": "supersession",
    "khg-reason": "incorrect",
    "khg-reason-detail": "the 2019 press release named the wrong person; corrected in 2021",
    "khg-recorded-at": "2026-09-23T11:00:00Z",
    "khg-recorded-by": "p2-gate-fixture/1.0.0",
    "khg-evidence": [
      {
        "eid": "ev1",
        "type": "curated",
        "mode": "manual",
        "source": {"doc": "doc:acme-pr-2021"},
        "activity": {"agent": "curator:reviewer-1"}
      }
    ]
  }
}
```

(The `khg:f09-married` edge is shown with six of its attrs; the full record is in the complete file
below. Everything else is shown whole.)

The complete file (`gate-full.hif.json`, 238 lines in this layout, one record per line). It validates
against the vendored HIF schema and the profile schema under jsonschema and fastjsonschema, and it imports back to
the gate container exactly **[validated]**. `network-type` is `undirected` because the qualifiers of `treats`,
`flight_route` and others declare no direction; the directed slice (the five fully directed relations) exports as
`directed` and is the second G1 fixture.

```json
{
 "network-type": "undirected",
 "metadata": {
  "roles-convention": "1.0.0",
  "roles-vocabulary": {
   "agent": {"label": "agent"},
   "background_therapy": {"label": "background therapy"},
   "catalyst": {"label": "catalyst"},
   "comparator": {"label": "comparator"},
   "condition": {"label": "condition"},
   "context": {"label": "context"},
   "count": {"label": "count"},
   "dose": {"label": "dose"},
   "effect": {"label": "effect"},
   "end_time": {"label": "end time"},
   "flight_number": {"label": "flight number"},
   "hba1c_change": {"label": "hba1c change"},
   "holder": {"label": "holder"},
   "intervention": {"label": "intervention"},
   "open_access": {"label": "open access"},
   "operator": {"label": "operator"},
   "organisation": {"label": "organisation"},
   "outcome": {"label": "outcome"},
   "page_count": {"label": "page count"},
   "partner": {"label": "partner"},
   "person": {"label": "person"},
   "place": {"label": "place"},
   "point_in_time": {"label": "point in time"},
   "population": {"label": "population"},
   "position": {"label": "position"},
   "publication": {"label": "publication"},
   "publisher": {"label": "publisher"},
   "reaction": {"label": "reaction"},
   "regulator": {"label": "regulator"},
   "report": {"label": "report"},
   "start_time": {"label": "start time"},
   "statement": {"label": "statement"},
   "stop": {"label": "stop"},
   "superseded": {"label": "superseded record (profile role)"},
   "superseding": {"label": "superseding record (profile role)"},
   "target": {"label": "target"},
   "title": {"label": "title"},
   "treatment": {"label": "treatment"},
   "url": {"label": "url"}
  },
  "hif-schema": "https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json",
  "hif-schema-sha256": "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196",
  "hif-schema-doi": "10.5281/zenodo.17257719",
  "khg-profile": "khg-hif/1.0.0",
  "khg-header": {"kind": "header", "format": "khg-record/1.0.0", "content": "snapshot", "as_at": "2026-09-23T12:00:00Z", "created_at": "2026-09-23T12:00:00Z", "created_by": "p2-gate-fixture/1.0.0", "title": "P2 gate fixture (adversarial)", "schemas": [{"id": "p2-gate", "version": "1.0.0", "sha256": "0acc5bc47da530243090e868492b376b444b37a8873d83f648b472e4bcc42943"}]},
  "khg-schemas": [{
   "kind": "relation-schema",
   "format": "khg-relation-schema/1.0.0",
   "id": "p2-gate",
   "version": "1.0.0",
   "label": "P2 gate fixture schema",
   "entity_types": [
    {"id": "Thing", "label": "thing"},
    {"id": "Drug", "label": "drug", "parents": ["Thing"]},
    {"id": "Disease", "label": "disease", "parents": ["Thing"]},
    {"id": "Outcome", "label": "outcome", "parents": ["Thing"]},
    {"id": "Population", "label": "population", "parents": ["Thing"]},
    {"id": "AdverseEffect", "label": "adverse effect", "parents": ["Thing"]},
    {"id": "Gene", "label": "gene", "parents": ["Thing"]},
    {"id": "CellLine", "label": "cell line", "parents": ["Thing"]},
    {"id": "Organisation", "label": "organisation", "parents": ["Thing"]},
    {"id": "Airline", "label": "airline", "parents": ["Organisation"]},
    {"id": "Person", "label": "person", "parents": ["Thing"]},
    {"id": "Position", "label": "position", "parents": ["Thing"]},
    {"id": "Airport", "label": "airport", "parents": ["Thing"]},
    {"id": "Place", "label": "place", "parents": ["Thing"]},
    {"id": "Document", "label": "document", "parents": ["Thing"]},
    {"id": "Reaction", "label": "reaction", "parents": ["Thing"]},
    {"id": "Chemical", "label": "chemical", "parents": ["Thing"]}
   ],
   "confidence_scales": [{"id": "probability", "kind": "probability", "min": 0, "max": 1}, {"id": "llm-1-10", "kind": "bounded", "min": 1, "max": 10}],
   "time_model": {"from_role": "start_time", "to_role": "end_time", "point_role": "point_in_time"},
   "roles": [
    {"id": "agent", "label": "agent"},
    {"id": "background_therapy", "label": "background therapy"},
    {"id": "catalyst", "label": "catalyst"},
    {"id": "comparator", "label": "comparator"},
    {"id": "condition", "label": "condition"},
    {"id": "context", "label": "context"},
    {"id": "count", "label": "count"},
    {"id": "dose", "label": "dose"},
    {"id": "effect", "label": "effect"},
    {"id": "end_time", "label": "end time"},
    {"id": "flight_number", "label": "flight number"},
    {"id": "hba1c_change", "label": "hba1c change"},
    {"id": "holder", "label": "holder"},
    {"id": "intervention", "label": "intervention"},
    {"id": "open_access", "label": "open access"},
    {"id": "operator", "label": "operator"},
    {"id": "organisation", "label": "organisation"},
    {"id": "outcome", "label": "outcome"},
    {"id": "page_count", "label": "page count"},
    {"id": "partner", "label": "partner"},
    {"id": "person", "label": "person"},
    {"id": "place", "label": "place"},
    {"id": "point_in_time", "label": "point in time"},
    {"id": "population", "label": "population"},
    {"id": "position", "label": "position"},
    {"id": "publication", "label": "publication"},
    {"id": "publisher", "label": "publisher"},
    {"id": "reaction", "label": "reaction"},
    {"id": "regulator", "label": "regulator"},
    {"id": "report", "label": "report"},
    {"id": "start_time", "label": "start time"},
    {"id": "statement", "label": "statement"},
    {"id": "stop", "label": "stop"},
    {"id": "target", "label": "target"},
    {"id": "title", "label": "title"},
    {"id": "treatment", "label": "treatment"},
    {"id": "url", "label": "url"}
   ],
   "relations": [
    {"id": "treats", "label": "treats", "kind": "fact", "nestable": true, "aliases": ["is used to treat"], "primary": {"subject": "treatment", "object": "condition"}, "roles": [{"role": "treatment", "slot": "core", "fillers": {"entity_types": ["Drug"]}, "min": 1, "max": 1, "direction": "tail"}, {"role": "condition", "slot": "core", "fillers": {"entity_types": ["Disease"]}, "min": 1, "max": 1, "direction": "head"}, {"role": "dose", "slot": "qualifier", "fillers": {"datatypes": ["quantity"]}, "min": 0, "max": 1}, {"role": "population", "slot": "qualifier", "fillers": {"entity_types": ["Population"]}, "min": 0, "max": 1}, {"role": "hba1c_change", "slot": "qualifier", "fillers": {"datatypes": ["decimal"]}, "min": 0, "max": 1}]},
    {"id": "compared_in_trial", "label": "compared in trial", "kind": "fact", "nestable": true, "roles": [{"role": "intervention", "slot": "core", "fillers": {"entity_types": ["Drug"]}, "min": 1, "max": 1, "direction": "tail"}, {"role": "background_therapy", "slot": "core", "fillers": {"entity_types": ["Drug"]}, "min": 0, "max": 1, "direction": "tail"}, {"role": "comparator", "slot": "core", "fillers": {"entity_types": ["Drug"]}, "min": 1, "max": 1, "direction": "tail"}, {"role": "outcome", "slot": "core", "fillers": {"entity_types": ["Outcome"]}, "min": 1, "max": 1, "direction": "head"}]},
    {"id": "regulates", "label": "regulates", "kind": "fact", "roles": [{"role": "regulator", "slot": "core", "fillers": {"entity_types": ["Gene"]}, "min": 1, "max": 1, "direction": "tail"}, {"role": "target", "slot": "core", "fillers": {"entity_types": ["Gene"]}, "min": 1, "max": 1, "direction": "head"}, {"role": "context", "slot": "qualifier", "fillers": {"entity_types": ["CellLine"]}, "min": 0, "max": 1, "direction": "tail"}]},
    {"id": "co_administration_causes", "label": "co-administration causes", "kind": "fact", "roles": [{"role": "agent", "slot": "core", "fillers": {"entity_types": ["Drug"]}, "min": 2, "max": null, "direction": "tail"}, {"role": "effect", "slot": "core", "fillers": {"entity_types": ["AdverseEffect"]}, "min": 1, "max": 1, "direction": "head"}]},
    {"id": "flight_route", "label": "flight route", "kind": "fact", "roles": [{"role": "operator", "slot": "core", "fillers": {"entity_types": ["Airline"]}, "min": 1, "max": 1}, {"role": "stop", "slot": "core", "fillers": {"entity_types": ["Airport"]}, "min": 2, "max": null, "ordered": true}, {"role": "flight_number", "slot": "qualifier", "fillers": {"datatypes": ["string"]}, "min": 0, "max": 1}]},
    {"id": "position_held", "label": "position held", "kind": "fact", "key": {"roles": ["position"], "temporal": true, "on_collision": "close_older"}, "roles": [{"role": "holder", "slot": "core", "fillers": {"entity_types": ["Person"]}, "min": 1, "max": 1}, {"role": "position", "slot": "core", "fillers": {"entity_types": ["Position"]}, "min": 1, "max": 1}, {"role": "start_time", "slot": "time", "fillers": {"datatypes": ["time"]}, "min": 0, "max": 1}, {"role": "end_time", "slot": "time", "fillers": {"datatypes": ["time"]}, "min": 0, "max": 1}]},
    {"id": "population_count", "label": "population count", "kind": "fact", "key": {"roles": ["place"], "temporal": true, "on_collision": "reject"}, "roles": [{"role": "place", "slot": "core", "fillers": {"entity_types": ["Place"]}, "min": 1, "max": 1}, {"role": "count", "slot": "core", "fillers": {"datatypes": ["quantity"], "units": ["1"]}, "min": 1, "max": 1}, {"role": "point_in_time", "slot": "time", "fillers": {"datatypes": ["time"], "precisions": ["year", "month", "day"]}, "min": 1, "max": 1}]},
    {"id": "publishes", "label": "publishes", "kind": "fact", "roles": [{"role": "publisher", "slot": "core", "fillers": {"entity_types": ["Organisation"]}, "min": 1, "max": 1}, {"role": "publication", "slot": "core", "fillers": {"entity_types": ["Document"]}, "min": 1, "max": 1}, {"role": "title", "slot": "qualifier", "fillers": {"datatypes": ["lang-string"]}, "min": 0, "max": 1}, {"role": "url", "slot": "qualifier", "fillers": {"datatypes": ["iri"]}, "min": 0, "max": 1}, {"role": "open_access", "slot": "qualifier", "fillers": {"datatypes": ["boolean"]}, "min": 0, "max": 1}, {"role": "page_count", "slot": "qualifier", "fillers": {"datatypes": ["integer"]}, "min": 0, "max": 1}]},
    {"id": "married", "label": "married", "kind": "fact", "constraints": [{"type": "must_differ", "roles": ["partner"]}], "roles": [{"role": "partner", "slot": "core", "fillers": {"entity_types": ["Person"]}, "min": 2, "max": 2}, {"role": "start_time", "slot": "time", "fillers": {"datatypes": ["time"]}, "min": 0, "max": 1}]},
    {"id": "catalysed_by", "label": "catalysed by", "kind": "fact", "roles": [{"role": "reaction", "slot": "core", "fillers": {"entity_types": ["Reaction"]}, "min": 1, "max": 1}, {"role": "catalyst", "slot": "core", "fillers": {"entity_types": ["Chemical"]}, "min": 1, "max": null}]},
    {"id": "chief_executive", "label": "chief executive", "kind": "fact", "key": {"roles": ["organisation"], "temporal": true, "on_collision": "supersede"}, "roles": [{"role": "organisation", "slot": "core", "fillers": {"entity_types": ["Organisation"]}, "min": 1, "max": 1, "direction": "tail"}, {"role": "person", "slot": "core", "fillers": {"entity_types": ["Person"]}, "min": 1, "max": 1, "direction": "head"}]},
    {"id": "reported_in", "label": "reported in", "kind": "meta", "roles": [{"role": "statement", "slot": "core", "fillers": {"hyperedge": {"relations": ["compared_in_trial", "treats"]}}, "min": 1, "max": 1, "direction": "head"}, {"role": "report", "slot": "core", "fillers": {"entity_types": ["Document"]}, "min": 1, "max": 1, "direction": "tail"}]}
   ]
  }]
 },
 "nodes": [
  {"node": "cell:HeLa", "attrs": {"khg-kind": "entity", "label": "HeLa", "khg-types": ["CellLine"]}},
  {"node": "disease:T1DM", "attrs": {"khg-kind": "entity", "label": "type 1 diabetes mellitus", "khg-types": ["Disease"]}},
  {"node": "disease:T2DM", "attrs": {"khg-kind": "entity", "label": "type 2 diabetes mellitus", "khg-types": ["Disease"]}},
  {"node": "doc:soc-2024", "attrs": {"khg-kind": "entity", "label": "Standards of Care in Diabetes—2024", "khg-types": ["Document"]}},
  {"node": "doc:trial-report-1998", "attrs": {"khg-kind": "entity", "label": "Trial report (1998)", "khg-types": ["Document"]}},
  {"node": "drug:insulin", "attrs": {"khg-kind": "entity", "label": "insulin", "khg-types": ["Drug"]}},
  {"node": "drug:metformin", "attrs": {"khg-kind": "entity", "label": "metformin", "khg-types": ["Drug"]}},
  {"node": "effect:hypoglycaemia", "attrs": {"khg-kind": "entity", "label": "hypoglycaemia", "khg-types": ["AdverseEffect"]}},
  {"node": "gene:TP53", "attrs": {"khg-kind": "entity", "label": "TP53", "khg-types": ["Gene"]}},
  {"node": "khg-lit:162ec375f18cb42984e8797fb5eddd1c", "attrs": {"khg-kind": "literal", "label": "true", "khg-literal": {"literal": "true", "datatype": "boolean"}}},
  {"node": "khg-lit:2cbeb0f7dd4958a97cec1cb63486460f", "attrs": {"khg-kind": "literal", "label": "320", "khg-literal": {"literal": "320", "datatype": "integer"}}},
  {"node": "khg-lit:3a72af3827d92f5b15858abd51641048", "attrs": {"khg-kind": "literal", "label": "1990", "khg-literal": {"literal": "1990", "datatype": "time", "precision": "year"}}},
  {"node": "khg-lit:4c6b0105560057b69e0d4668fb667aba", "attrs": {"khg-kind": "literal", "label": "-1.12", "khg-literal": {"literal": "-1.12", "datatype": "decimal"}}},
  {"node": "khg-lit:558537e4f43324060bd3f9711346fbc5", "attrs": {"khg-kind": "literal", "label": "https://diabetesjournals.org/care/issue/47/Supplement_1", "khg-literal": {"literal": "https://diabetesjournals.org/care/issue/47/Supplement_1", "datatype": "iri"}}},
  {"node": "khg-lit:6a698e70cd927a0dd4a56e5c14f410c1", "attrs": {"khg-kind": "literal", "label": "2023", "khg-literal": {"literal": "2023", "datatype": "time", "precision": "year"}}},
  {"node": "khg-lit:9268ee921c4c0de5f7ef609c0dee9fcf", "attrs": {"khg-kind": "literal", "label": "1715-09-01", "khg-literal": {"literal": "1715-09-01", "datatype": "time", "precision": "day"}}},
  {"node": "khg-lit:a2a4fef6f92a2ee3402c01311df80290", "attrs": {"khg-kind": "literal", "label": "500", "khg-literal": {"literal": "500", "datatype": "quantity", "unit": "wd:Q3241121"}}},
  {"node": "khg-lit:b1d1806600e2189f2bfa767af223490e", "attrs": {"khg-kind": "literal", "label": "Standards of Care in Diabetes—2024", "khg-literal": {"literal": "Standards of Care in Diabetes—2024", "datatype": "lang-string", "lang": "en"}}},
  {"node": "khg-lit:b9a49935d7c1b51b1907db59ef3b2d84", "attrs": {"khg-kind": "literal", "label": "443037", "khg-literal": {"literal": "443037", "datatype": "quantity", "unit": "1", "lower": "443000", "upper": "443100"}}},
  {"node": "khg-lit:ccbbd652f7fd8dce4c4e4baab2bfd2fc", "attrs": {"khg-kind": "literal", "label": "AC 857", "khg-literal": {"literal": "AC 857", "datatype": "string"}}},
  {"node": "khg-lit:ea7910186938afd226392138fdaa1602", "attrs": {"khg-kind": "literal", "label": "1643-05-14", "khg-literal": {"literal": "1643-05-14", "datatype": "time", "precision": "day"}}},
  {"node": "khg-ref:khg:f02-trial", "attrs": {"khg-kind": "hyperedge-ref", "khg-ref": "khg:f02-trial"}},
  {"node": "khg-ref:khg:f11-ceo-alice", "attrs": {"khg-kind": "hyperedge-ref", "khg-ref": "khg:f11-ceo-alice"}},
  {"node": "khg-ref:khg:f12-ceo-bob", "attrs": {"khg-kind": "hyperedge-ref", "khg-ref": "khg:f12-ceo-bob"}},
  {"node": "org:ADA", "attrs": {"khg-kind": "entity", "label": "American Diabetes Association", "khg-types": ["Organisation"]}},
  {"node": "org:Acme", "attrs": {"khg-kind": "entity", "label": "Acme Corp.", "khg-types": ["Organisation"]}},
  {"node": "outcome:HbA1c", "attrs": {"khg-kind": "entity", "label": "glycated haemoglobin (HbA1c)", "khg-types": ["Outcome"]}},
  {"node": "pop:adults", "attrs": {"khg-kind": "entity", "label": "adults", "khg-types": ["Population"]}},
  {"node": "x:Alice", "attrs": {"khg-kind": "entity", "label": "Alice", "khg-types": ["Person"]}},
  {"node": "x:Bob", "attrs": {"khg-kind": "entity", "label": "Bob", "khg-types": ["Person"]}},
  {"node": "x:Louis_XIV", "attrs": {"khg-kind": "entity", "label": "Louis XIV", "khg-types": ["Person"]}},
  {"node": "x:ORD", "attrs": {"khg-kind": "entity", "label": "Chicago O'Hare", "khg-types": ["Airport"]}},
  {"node": "x:R1", "attrs": {"khg-kind": "entity", "label": "reaction R1", "khg-types": ["Reaction"]}},
  {"node": "x:Roi_de_France", "attrs": {"khg-kind": "entity", "label": "roi de France", "khg-types": ["Position"]}},
  {"node": "x:YYZ", "attrs": {"khg-kind": "entity", "label": "Toronto Pearson", "khg-types": ["Airport"]}},
  {"node": "x:Zoë", "attrs": {"khg-kind": "entity", "label": "Zoë", "khg-types": ["Person"]}},
  {"node": "x:Zürich", "attrs": {"khg-kind": "entity", "label": "Zürich", "khg-types": ["Place"]}},
  {"node": "x:air-canada", "attrs": {"khg-kind": "entity", "label": "Air Canada", "khg-types": ["Airline"]}},
  {"node": "x:Москва", "attrs": {"khg-kind": "entity", "label": "Москва", "khg-types": ["Place"]}}
 ],
 "edges": [
  {"edge": "khg:f01-treats", "attrs": {"relation": "treats", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "extracted", "mode": "automatic", "source": {"doc": "doc:soc-2024", "doc_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739"}, "selectors": [{"type": "quote", "exact": "Metformin is the preferred initial pharmacologic agent for the treatment of type 2 diabetes in adults."}, {"type": "position", "start": 0, "end": 102}], "activity": {"agent": "p9-extractor/0.1.0", "model": "model-y/2026-08", "run": "r1", "prompt": "treats-skill/1.2.0", "params": {"seed": 13, "temperature": 0}}, "confidence": {"value": 0.9, "scale": "probability"}, "event_hash": "sha256:ec92cafb15cde9c2454f34b99581c8a85537289c02a4f27eb1af576a6698fb17"}, {"eid": "ev2", "type": "curated", "mode": "manual", "source": {"doc": "doc:soc-2024", "doc_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739"}, "selectors": [{"type": "quote", "exact": "The usual starting dose is 500 mg"}, {"type": "position", "start": 103, "end": 136}], "activity": {"agent": "curator:reviewer-1"}, "binding_refs": ["b3"]}], "khg-valid-time": {"from": "2024-01-01"}, "khg-confidence": {"value": 0.95, "scale": "probability"}, "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 5, "core": 2, "participants": 5}, "khg-keys": {"content": "sha256:09c8cc13dc74f8c3f6f2db9d3bdff24860523db953aeb713dc80eb6e1d1dc6d7", "core": "sha256:55449857f34d1a8a27ef8c72d6117c4a882cc055e83a3b572db6f7e0f0966b57"}}},
  {"edge": "khg:f02-trial", "attrs": {"relation": "compared_in_trial", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:trial-report-1998"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 4, "core": 4, "participants": 3}, "khg-keys": {"content": "sha256:089b4367c127643b17196120b56e476974269ab8dd617ee67be9cb462aa4d152", "core": "sha256:6aa7243fbd8ebc9d7d4f4095e29dc71c4b3ea6fdbb30773f5f53ea4e9cabfb8a"}}},
  {"edge": "khg:f03-regulates", "attrs": {"relation": "regulates", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:tp53-review"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 3, "core": 2, "participants": 2}, "khg-keys": {"content": "sha256:249022b02a47d05f4c1c5f82cc579b91893378a793de0f7a935000c87b562a5e", "core": "sha256:2c351eadf1bd518dc2f516f9628fec951c453f979be1563296b65efc11fc4ede"}}},
  {"edge": "khg:f04-coadmin", "attrs": {"relation": "co_administration_causes", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:soc-2024"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-confidence": {"value": 7, "scale": "llm-1-10"}, "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 3, "core": 3, "participants": 3}, "khg-keys": {"content": "sha256:31162aba80d29ea524bad8e50c5a551e09707574a180511c031a9b222bacf868", "core": "sha256:fc2439f2ff6a6f3424592bf9aa837a10c26f6af1da901e42301e1f4c335212e9"}}},
  {"edge": "khg:f05-route", "attrs": {"relation": "flight_route", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:timetable-2026"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 5, "core": 4, "participants": 4}, "khg-keys": {"content": "sha256:149b608de47be1ad3699232b31a69b1ae8bb6533e7aca2b192b8a895440e402b", "core": "sha256:aacb2de32082370463435c34fb4a9efdef0dda55ec5c3b47b369db80ecccd722"}}},
  {"edge": "khg:f06-louis", "attrs": {"relation": "position_held", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:encyclopaedia"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-valid-time": {"from": "1643-05-14", "to": "1715-09-01"}, "khg-arity": {"arity": 4, "core": 2, "participants": 4}, "khg-keys": {"content": "sha256:d0ba8aa9b254b072a059294d0ef2525147afbd70fdb2fd6007781c78f8eab2c8", "core": "sha256:a3e9a852ab643750e7c2360bdda811657b80fe6207405bdf48f7eb3ea7aed98d", "key": "sha256:b055329463dfc44585557156b790a95c751149e91c339ab34fe646385e1c6d0e"}}},
  {"edge": "khg:f07-zurich", "attrs": {"relation": "population_count", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "imported", "mode": "automatic", "source": {"doc": "wd:Q72"}, "reference": [{"prop": "wd:P248", "value": {"entity": "x:stat-zurich-2023"}}, {"prop": "wd:P813", "value": {"literal": "2026-09-20", "datatype": "time", "precision": "day"}}], "activity": {"agent": "p3a-builder/0.1.0", "run": "dump-2026-09-15"}}, {"eid": "ev2", "type": "extracted", "mode": "automatic", "source": {"doc": "doc:zh-stat-2023", "doc_sha256": "5cc4f38f1c32b9bd8bd165d4f7a3e8b1d2b29d8688f43b50bd55bc8a337955c0"}, "selectors": [{"type": "quote", "exact": "Zürich zählte Ende 2023 443 037"}, {"type": "position", "start": 10, "end": 41}], "activity": {"agent": "p9-extractor/0.1.0", "model": "model-y/2026-08", "run": "r1"}, "event_hash": "sha256:eae1a537297e8379ebdd309ea3387e902b070bd632d93bfe42c4a8d277aa89e8"}], "khg-rank": "preferred", "khg-schema": "p2-gate/1.0.0", "khg-visibility": "visible", "khg-valid-time": {"from": "2023", "to": "2024"}, "khg-arity": {"arity": 3, "core": 2, "participants": 3}, "khg-keys": {"content": "sha256:b9f1d2136f03fa83c77df11eb0d857a1961b68a4a89877fb5fa1fc6c19073fd3", "core": "sha256:1620544ef9f0ebb04ba9e80b765d71aeec83f6d66d1a8957bf6c7039b969de35", "key": "sha256:9909c7eec0939612411d1a28410e33647493a05ad87305df39848efd35616c31"}}},
  {"edge": "khg:f08-publishes", "attrs": {"relation": "publishes", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:soc-2024"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 6, "core": 2, "participants": 6}, "khg-keys": {"content": "sha256:57864c492c6b68840d7151a063bdc3e8cde9190d96faf47abf5631a7d8be31e5", "core": "sha256:c3e19fccd4e00ed0d89758d6ae884183a61242f718ba01984eabebbc9932413b"}}},
  {"edge": "khg:f09-married", "attrs": {"relation": "married", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:register-extract"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-rank": "deprecated", "khg-rank-reason": "wd:Q25895909", "khg-schema": "p2-gate/1.0.0", "khg-visibility": "visible", "khg-valid-time": {"from": "1990"}, "khg-arity": {"arity": 3, "core": 2, "participants": 3}, "khg-keys": {"content": "sha256:3c1ed0bbb4e6bf7dbf88efe7130050e9190f7fe9351c0a281824f0fe6b87610c", "core": "sha256:e2f9ea8cb5dec3386fa4bb84cffa0d566528aba2b0d8295c18bd77195aa8babe"}, "khg-special-bindings": [{"bid": "b2", "role": "partner", "value": {"special": "somevalue"}, "slot": "core"}]}},
  {"edge": "khg:f10-catalysis", "attrs": {"relation": "catalysed_by", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:lab-notebook-7"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 1, "core": 1, "participants": 1}, "khg-keys": {"content": "sha256:3b185a0b7ff2eebca1c841ec580b3ba4f7a4132ba6d6ba1c389e4409e78d1dac", "core": "sha256:185ae5a32b46723314f75b1014fda216cc38f756b91dbaee93613a64ad3ec016"}, "khg-special-bindings": [{"bid": "b2", "role": "catalyst", "value": {"special": "novalue"}, "slot": "core"}]}},
  {"edge": "khg:f11-ceo-alice", "attrs": {"relation": "chief_executive", "khg-kind": "hyperedge", "khg-version": 2, "khg-recorded-at": "2026-09-23T11:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "supersede", "ref": "khg:s01"}, "khg-status": "superseded", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:acme-pr-2019"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-superseded-by": ["khg:f12-ceo-bob"], "khg-valid-time": {"from": "2019-01-01"}, "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 2, "core": 2, "participants": 2}, "khg-keys": {"content": "sha256:b69ad50b61f8ff24258f49a2c9be0246444b7ed5089f8aa24e8ecfa57691e43f", "core": "sha256:9031158fbbc0edff06b6110b4d43942c265ee3d6f51dd1e8b502a54a973f8c9e", "key": "sha256:1bcb00fd07a8146ddb6aa5c24b83de5076596794221dc483f2daec7c1bf565fb"}}},
  {"edge": "khg:f12-ceo-bob", "attrs": {"relation": "chief_executive", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T11:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:acme-pr-2021"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-valid-time": {"from": "2019-01-01"}, "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 2, "core": 2, "participants": 2}, "khg-keys": {"content": "sha256:214c126c8bd06d84879559eac9134bc19fbe475524c655cbc9a0354fc938ba1b", "core": "sha256:3a35b074cb59e1002bc2c57b779d8c65b1203ad211a984811294f50919b13e82", "key": "sha256:1bcb00fd07a8146ddb6aa5c24b83de5076596794221dc483f2daec7c1bf565fb"}}},
  {"edge": "khg:f13-reported", "attrs": {"relation": "reported_in", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "asserted", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:trial-report-1998"}, "activity": {"agent": "curator:reviewer-1"}}], "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 2, "core": 2, "participants": 2}, "khg-keys": {"content": "sha256:e339305b2144acfdaa0e3e1cac8ac8f19c26f0fb7a61cf6eb09dc6302e1123f6", "core": "sha256:970d76370b4d603f29f1554642cfd60e506f4b5c82be85b1d12b6e86be1e383a"}}},
  {"edge": "khg:f14-goal", "attrs": {"relation": "treats", "khg-kind": "hyperedge", "khg-version": 1, "khg-recorded-at": "2026-09-23T10:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-change": {"op": "put"}, "khg-status": "goal", "khg-schema": "p2-gate/1.0.0", "khg-rank": "normal", "khg-visibility": "visible", "khg-arity": {"arity": 1, "core": 1, "participants": 1}, "khg-keys": {"content": "sha256:8cdef4395484060b4ede55850f0c61c5f2f3cbf3f52f8ea25e1c7ecae278a9d7", "core": "sha256:681ea421d08c12073dc6a5ec60baa8177b93fb635180c22de2bff79756d8e85a"}, "khg-special-bindings": [{"bid": "b1", "role": "treatment", "value": {"special": "unbound", "expects": {"entity_types": ["Drug"]}}, "slot": "core", "direction": "tail"}]}},
  {"edge": "khg:s01", "attrs": {"relation": "khg-supersedes", "khg-kind": "supersession", "khg-reason": "incorrect", "khg-reason-detail": "the 2019 press release named the wrong person; corrected in 2021", "khg-recorded-at": "2026-09-23T11:00:00Z", "khg-recorded-by": "p2-gate-fixture/1.0.0", "khg-evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:acme-pr-2021"}, "activity": {"agent": "curator:reviewer-1"}}]}}
 ],
 "incidences": [
  {"edge": "khg:f01-treats", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "treatment", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f01-treats", "node": "disease:T2DM", "direction": "head", "attrs": {"role": "condition", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f01-treats", "node": "khg-lit:a2a4fef6f92a2ee3402c01311df80290", "attrs": {"role": "dose", "khg-bid": "b3", "khg-slot": "qualifier"}},
  {"edge": "khg:f01-treats", "node": "pop:adults", "attrs": {"role": "population", "khg-bid": "b4", "khg-slot": "qualifier"}},
  {"edge": "khg:f01-treats", "node": "khg-lit:4c6b0105560057b69e0d4668fb667aba", "attrs": {"role": "hba1c_change", "khg-bid": "b5", "khg-slot": "qualifier"}},
  {"edge": "khg:f02-trial", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "intervention", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f02-trial", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "background_therapy", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f02-trial", "node": "drug:insulin", "direction": "tail", "attrs": {"role": "comparator", "khg-bid": "b3", "khg-slot": "core"}},
  {"edge": "khg:f02-trial", "node": "outcome:HbA1c", "direction": "head", "attrs": {"role": "outcome", "khg-bid": "b4", "khg-slot": "core"}},
  {"edge": "khg:f03-regulates", "node": "gene:TP53", "direction": "tail", "attrs": {"role": "regulator", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f03-regulates", "node": "gene:TP53", "direction": "head", "attrs": {"role": "target", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f03-regulates", "node": "cell:HeLa", "direction": "tail", "attrs": {"role": "context", "khg-bid": "b3", "khg-slot": "qualifier"}},
  {"edge": "khg:f04-coadmin", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "agent", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f04-coadmin", "node": "drug:insulin", "direction": "tail", "attrs": {"role": "agent", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f04-coadmin", "node": "effect:hypoglycaemia", "direction": "head", "attrs": {"role": "effect", "khg-bid": "b3", "khg-slot": "core"}},
  {"edge": "khg:f05-route", "node": "x:air-canada", "attrs": {"role": "operator", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f05-route", "node": "x:YYZ", "attrs": {"role": "stop", "khg-bid": "b2", "khg-slot": "core", "khg-position": 0}},
  {"edge": "khg:f05-route", "node": "x:ORD", "attrs": {"role": "stop", "khg-bid": "b3", "khg-slot": "core", "khg-position": 1}},
  {"edge": "khg:f05-route", "node": "x:YYZ", "attrs": {"role": "stop", "khg-bid": "b4", "khg-slot": "core", "khg-position": 2}},
  {"edge": "khg:f05-route", "node": "khg-lit:ccbbd652f7fd8dce4c4e4baab2bfd2fc", "attrs": {"role": "flight_number", "khg-bid": "b5", "khg-slot": "qualifier"}},
  {"edge": "khg:f06-louis", "node": "x:Louis_XIV", "attrs": {"role": "holder", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f06-louis", "node": "x:Roi_de_France", "attrs": {"role": "position", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f06-louis", "node": "khg-lit:ea7910186938afd226392138fdaa1602", "attrs": {"role": "start_time", "khg-bid": "b3", "khg-slot": "time"}},
  {"edge": "khg:f06-louis", "node": "khg-lit:9268ee921c4c0de5f7ef609c0dee9fcf", "attrs": {"role": "end_time", "khg-bid": "b4", "khg-slot": "time"}},
  {"edge": "khg:f07-zurich", "node": "x:Zürich", "attrs": {"role": "place", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f07-zurich", "node": "khg-lit:b9a49935d7c1b51b1907db59ef3b2d84", "attrs": {"role": "count", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f07-zurich", "node": "khg-lit:6a698e70cd927a0dd4a56e5c14f410c1", "attrs": {"role": "point_in_time", "khg-bid": "b3", "khg-slot": "time"}},
  {"edge": "khg:f08-publishes", "node": "org:ADA", "attrs": {"role": "publisher", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f08-publishes", "node": "doc:soc-2024", "attrs": {"role": "publication", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f08-publishes", "node": "khg-lit:b1d1806600e2189f2bfa767af223490e", "attrs": {"role": "title", "khg-bid": "b3", "khg-slot": "qualifier"}},
  {"edge": "khg:f08-publishes", "node": "khg-lit:558537e4f43324060bd3f9711346fbc5", "attrs": {"role": "url", "khg-bid": "b4", "khg-slot": "qualifier"}},
  {"edge": "khg:f08-publishes", "node": "khg-lit:162ec375f18cb42984e8797fb5eddd1c", "attrs": {"role": "open_access", "khg-bid": "b5", "khg-slot": "qualifier"}},
  {"edge": "khg:f08-publishes", "node": "khg-lit:2cbeb0f7dd4958a97cec1cb63486460f", "attrs": {"role": "page_count", "khg-bid": "b6", "khg-slot": "qualifier"}},
  {"edge": "khg:f09-married", "node": "x:Zoë", "attrs": {"role": "partner", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f09-married", "node": "khg-lit:3a72af3827d92f5b15858abd51641048", "attrs": {"role": "start_time", "khg-bid": "b3", "khg-slot": "time"}},
  {"edge": "khg:f10-catalysis", "node": "x:R1", "attrs": {"role": "reaction", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f11-ceo-alice", "node": "org:Acme", "direction": "tail", "attrs": {"role": "organisation", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f11-ceo-alice", "node": "x:Alice", "direction": "head", "attrs": {"role": "person", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f12-ceo-bob", "node": "org:Acme", "direction": "tail", "attrs": {"role": "organisation", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f12-ceo-bob", "node": "x:Bob", "direction": "head", "attrs": {"role": "person", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f13-reported", "node": "khg-ref:khg:f02-trial", "direction": "head", "attrs": {"role": "statement", "khg-bid": "b1", "khg-slot": "core"}},
  {"edge": "khg:f13-reported", "node": "doc:trial-report-1998", "direction": "tail", "attrs": {"role": "report", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:f14-goal", "node": "disease:T1DM", "direction": "head", "attrs": {"role": "condition", "khg-bid": "b2", "khg-slot": "core"}},
  {"edge": "khg:s01", "node": "khg-ref:khg:f11-ceo-alice", "direction": "head", "attrs": {"role": "superseded"}},
  {"edge": "khg:s01", "node": "khg-ref:khg:f12-ceo-bob", "direction": "tail", "attrs": {"role": "superseding"}}
 ]
}
```

---

## 5. Library loaders (XGI and HyperNetX)

The loaders operate on HIF, not on C1, so they serve any file that follows the `roles` convention; the khg layer
sits on top (`from_records`). They never call `xgi.read_hif`/`write_hif`, `xgi.from_hif_dict`, `hnx.from_hif` or
`hnx.to_hif` (F1; R03 D3): XGI's reader drops every incidence `attrs` and every `weight`, and HyperNetX's needs the
network, returns `None` instead of raising, drops metadata and cannot read its own directed output [R03 §3, §4].

### 5.1 API

```python
def load_xgi(doc: dict, *, validate: Literal["profile", "hif", "none"] = "profile") -> LoadedXGI
def load_hnx(doc: dict, *, validate: Literal["profile", "hif", "none"] = "profile") -> LoadedHNX
def from_records(records: Iterable[dict], *, library: Literal["xgi", "hnx"],
                 relations: Collection[str] | None = None, network_type: str = "auto") -> LoadedXGI | LoadedHNX

@dataclass
class LoadedXGI:
    hypergraph: "xgi.Hypergraph | xgi.DiHypergraph"   # DiHypergraph iff network-type is directed
    context: HifContext                               # bundled: the two cannot be separated [R03 D1]
    def roles(self, edge: str, node: str) -> list[str]            # every role of node in edge, record order
    def incidence_records(self, edge: str) -> list[dict]          # the full HIF records of one edge
    def export(self, *, strict: bool = True) -> dict              # HIF, canonical order (§4.3 E11)
    last_report: ExportReport | None

@dataclass
class LoadedHNX:                                      # same surface; hypergraph is an hnx.Hypergraph
    hypergraph: "hnx.Hypergraph"
    context: HifContext
    def roles(self, edge: str, node: str) -> list[str]
    def incidence_records(self, edge: str) -> list[dict]
    def export(self, *, strict: bool = True) -> dict
    last_report: ExportReport | None

@dataclass
class ExportReport:
    stale: list[dict]        # context records whose membership no longer exists in the library object
    unlabelled: list[dict]   # memberships that exist but have no record (added natively)

class StaleIncidences(LoaderError): ...
class UnlabelledMemberships(LoaderError): ...
```

`validate="profile"` runs L0-L3 for khg-hif files; `"hif"` runs L0-L1 plus the convention's own checks (every
incidence has a non-empty string role, repeated pairs differ in role or direction) for any roles-convention file;
`"none"` is for re-loading an export the package just produced.

### 5.2 What the library holds and what the context holds

| Data | XGI 0.10.2 | HyperNetX 2.4.3 | Context (`HifContext`) |
|---|---|---|---|
| memberships | edge member sets; `DiHypergraph` tail (`in`) and head (`out`) sets, built with `add_node_to_edge` | cells, built with the public `hnx.Hypergraph(df, edge_col, node_col, cell_weight_col, misc_cell_properties_col="attrs", node_properties, edge_properties, misc_properties_col="attrs")` constructor [R03 §7.2] | |
| role of each incidence record | nowhere (XGI has no incidence store [R03 X1]) | first record of a pair: native cell properties (`role`, `khg-bid`, `khg-slot`, `khg-position`); records 2..k: reserved cell attr `khg-extra-incidences`, so they follow `rename`, `dual` and `restrict_to_*` [R03 §7.4] | **every** source record, in canonical order; the XGI adapter keys them by `(edge, node, direction)` plus an ordinal so two records for one pair stay two |
| `direction` | tail/head sets (directed files) | a cell column | in the records |
| node and edge attrs | `set_node_attributes`, `set_edge_attributes` (never `**attrs` splats, which crash on an attr named `node` [R03 X5]) | node and edge property stores, including isolated nodes and empty edges | declaration order |
| `metadata` | network attrs (`H[k] = v`) | not held (only `name` exists) | verbatim |
| `network-type` | the class | not held | verbatim |
| record-level `weight` (foreign files only) | not held | held, but HyperNetX invents `1` where absent | which weights were present |

### 5.3 Export, reconciliation and strict mode

The library object decides which nodes, edges and memberships exist now, so native edits are honoured; the
context supplies the full records for memberships that still exist. Records whose membership is gone are **stale**
(dropped and reported); memberships without a record are **unlabelled** (exported bare and reported). In
`strict=True` mode, the default and the gate's mode, either raises. A record is never re-attached to a different
pair, ids are never renumbered, no `weight` is invented, no `"nil"` is written, and output is in canonical order.

### 5.4 Determinism

Export order is the canonical order of §4.3, never set iteration order: XGI's own writer produced four different
files under four `PYTHONHASHSEED` values, the sketch adapters one [R03 §4.1]. G1 repeats the chain under four seeds
and compares bytes (§1.3).

### 5.5 Native operations between load and export [R03 D9, §5, §7.4]

| Class | XGI | HyperNetX | What export does |
|---|---|---|---|
| **safe** (identity-preserving) | `copy`, `set_*_attributes`, weak `remove_node`, `merge_duplicate_edges` | `clone`, `rename` (roles follow the node), `dual` (roles follow the pair), `restrict_to_edges`, `remove_edges`, `remove_incidences`, `H.incidences[(e, n)].role = ...`, `add_incidence(..., direction=...)` | exact |
| **reported** (drop or add memberships) | strong `remove_node`, `subhypergraph` (undirected), `add_edge`, `add_node_to_edge` | `restrict_to_nodes` (trims n-ary facts, stale `arity`), `remove_nodes` | stale / unlabelled lists; strict export raises; the C1 import then fails `R-DERIVED`/`S-ROLE-MIN`, so a trimmed fact can never pass as valid |
| **unsafe** (renumber, merge or move roles) | `H << H2`, `convert_labels_to_integers` (overwrites `label`), `cleanup`, `dual`, `subhypergraph` on a `DiHypergraph` (raises) | `collapse_nodes`, `collapse_nodes_and_edges` (moved `publisher`/`tail` onto a `publication` participant [R03 §5.2]), `collapse_edges` (sums weights), `sum(H2)`, `add_edge`/`add_node` without an incidence | documented as unsupported; strict export raises on the resulting stale records |

The option of mirroring XGI records into edge attrs so they survive `<<` (R03 D1 option B) is left for 1.1, if a
consumer needs roles to follow renumbered edges.

### 5.6 The library-evidence test (not part of the gate)

`tests/evidence/test_library_hif_functions.py` runs the libraries' **own** HIF functions on the gate fixture and
asserts what they do today, as material for the upstream proposal and issues (§12.3, §12.4). It stays offline by
patching `hypernetx.hif.requests.get` to return the vendored schema bytes. It is marked `evidence` and runs in CI;
when a library release changes behaviour the test fails and the evidence table is updated. Observed on the gate
fixture **[validated]**:

| | Full fixture (undirected, some directions) | Directed slice |
|---|---|---|
| incidence records in (all role-labelled) | 45 | 18 |
| `xgi.read_hif` -> `xgi.write_hif`: records out / records with a role | 42 / 0 | 17 / 0 |
| XGI keeps `metadata` | yes | yes |
| `hnx.from_hif` -> `hnx.to_hif(network_type=<input>)` returns | `None` (see below) | a dict with 16 records, 16 with a role; metadata keys ['default_attrs'] |
| HyperNetX second generation (`from_hif` of its own output, then `to_hif`) | n/a | `None` |

The mixed-direction result is new: on a file where only some incidences carry `direction` (legal HIF [R02 §5
case 24]), HyperNetX's `to_hif` writes `"direction": "nil"` for the other 23 incidences, fails its own schema check
and returns `None` [R03 N6 generalised]. The directed-slice numbers reproduce R03 §3 rows 1, 3, 4, 13 and §4.2.

---

## 6. C2 store interface

Interface id **`khg-store/1.0.0`** (its own semver, PLAN §7). Nine core methods a backend implements; seven more
come from `StoreBase` defaults that a backend may override for speed.

### 6.1 The Protocol

```python
Record = dict[str, Any]                   # a C1 record (entity, hyperedge or supersession)
Pattern = dict[str, Any]                  # {"role": Sym, "value": Value, "position"?: int}
Direction = Literal["forward", "backward"]

@dataclass(frozen=True)
class Where:                              # any iterable of strings is accepted and frozen by __post_init__,
                                          # so Where(status={"asserted", "disputed"}) works
    status: frozenset[str] = frozenset({"asserted"})
    rank: frozenset[str] = frozenset({"preferred", "normal"})
    visibility: frozenset[str] = frozenset({"visible"})
    as_of: str | None = None              # valid-time instant (a C1 time bound); None = no valid-time filter
    as_at: str | None = None              # transaction-time instant (RFC 3339 UTC); None = latest versions

DEFAULT = Where()

class Store(Protocol):
    interface_version: str                # "khg-store/1.0.0"
    record_format: str                    # "khg-record/1.0.0"
    capabilities: frozenset[str]          # §6.5

    # core: a backend implements these nine
    def put(self, record: Record, *, actor: str, at: str | None = None) -> PutResult: ...
    def apply(self, event: dict, *, actor: str) -> list[PutResult]: ...
    def load(self, records: Iterable[Record]) -> LoadReport: ...
    def get(self, id: str, *, as_at: str | None = None, version: int | None = None) -> Record | None: ...
    def history(self, id: str) -> list[Record]: ...
    def incident(self, node: str, *, role: str | None = None, relation: str | None = None,
                 where: Where = DEFAULT, limit: int | None = None, after: str | None = None) -> list[Record]: ...
    def find(self, relation: str, pattern: Sequence[Pattern], *, match: Literal["at_least", "exact"] = "at_least",
             where: Where = DEFAULT, limit: int | None = None, after: str | None = None) -> list[Record]: ...
    def supersessions(self, id: str, *, direction: Direction = "forward", as_at: str | None = None) -> list[Record]: ...
    def iter_records(self, *, content: Literal["snapshot", "history"] = "snapshot",
                     where: Where | None = None) -> Iterator[Record]: ...

    # derived: StoreBase implements these seven from the core
    def put_many(self, records: Iterable[Record], *, actor: str) -> list[PutResult]: ...
    def get_many(self, ids: Iterable[str], *, as_at: str | None = None) -> dict[str, Record]: ...
    def degree(self, node: str, *, role: str | None = None, relation: str | None = None,
               where: Where = DEFAULT) -> int: ...
    def find_by_key(self, relation: str, key: Sequence[Pattern], *, where: Where = DEFAULT) -> list[Record]: ...
    def supersession_walk(self, id: str, *, direction: Direction = "forward", as_at: str | None = None) -> Walk: ...
    def export(self, format: Literal["khg-jsonl", "hif"] = "khg-jsonl", *, content: str = "snapshot",
               where: Where | None = None, relations: Collection[str] | None = None) -> str | dict: ...
    def close(self) -> None: ...

class PutResult(TypedDict):  id: str; version: int; created: bool
class LoadReport(TypedDict): records: int; versions: int; seconds: float
class Walk(TypedDict):       start: str; direction: str; steps: list[dict]; terminal: list[str]
# errors: ValidationFailed(findings), KeyCollision(conflicts, suggested), TransitionError, NotFound,
#         EntityConflict, CapabilityMissing(capability); every error has .code and .info
```

**Events** (`apply`), each one atomic [R01 C2-R19]:

| `op` | Fields | Effect |
|---|---|---|
| `supersede` | `id`, `superseded: [Id]`, one of `superseding: Id` or `record: Record`, `reason`, `reason_detail?`, `evidence` (at least one), `at?` | puts `record` if given (the collision with the superseded facts is expected and allowed), writes one supersession record per superseded id (`id`, or `id-1`, `id-2`, ...), and a new version of each superseded fact with `status: superseded` and `superseded_by`; rejects a cycle |
| `transition` | `target`, `to`, `reason`, `evidence?`, `at?` | a new version with the new status, checked against §2.10; `to: asserted` re-validates and re-checks keys |
| `end_validity` | `target`, `to` (a time bound), `end_cause?`, `bid?`, `evidence?`, `at?` | a new version with `valid_time.to` closed and status unchanged (F7); when the relation has a `to_role`, the `end_time` binding is written and `valid_time` re-derived, so bindings stay the source of truth |
| `add_evidence` | `target`, `evidence` (at least one), `at?` | a new version with the evidence appended (new `eid`s only) |

`at` (on `put` and on every event) lets an importer or a replay fix transaction time; it may not precede the id's
latest `recorded_at` (`C-TX-ORDER`). A live call omits it and the store's clock decides.

### 6.2 Semantics

- **`put`** normalises and validates the record (L2 and L3 against its schema, entity and hyperedge references
  against the store), then: if the id is new, writes version 1; if the content equals the current version, returns
  `created: False` and writes nothing (idempotent) [R01 C2-R01]; otherwise appends version n+1. `put` refuses status
  `candidate` (F9) and `superseded` (only `supersede` gets there), and refuses a status change (`transition` does
  that). Asserted records with a key are checked for collisions (§3.3) and never overwritten.
- **`load`** imports a canonical container (snapshot or history) as it is, keeping `version`, `recorded_at`,
  `recorded_by` and `change`. It is the bulk path P1 times, and what the export round trip goes through
  [R01 C2-R15]. A snapshot load keeps only the versions it carries. `load` trusts its input: it does not re-run the
  validator (validate the file first with `validate_container`, as P1's harness does), so P1 times the backend and
  not the validator; it checks only the header's major version (M82) and that versions and transaction times
  increase per id (`C-TX-ORDER`).
- **Reads** take one `Where`. Defaults: status `{asserted}`, rank `{preferred, normal}`, visibility `{visible}`, no
  valid-time filter, latest versions [R01 C2-R13]. The as-of default is deliberately "no filter", not "now": P10
  answers historical questions (Louis XIV) and P3a's facts mostly have past validity; a now-filter would silently
  hide them. `as_of` and `as_at` compose: the version at `as_at` is chosen first, then its `valid_time` is tested
  against `as_of` [R01 C2-R07]. A fact with no `valid_time` passes any `as_of` (open world).
- **`get`** returns entity, hyperedge or supersession records; for a hyperedge, the version current at `as_at` (or
  the given `version`). It ignores `Where` status filters: a direct lookup always answers.
- **`incident(node)`** returns every hyperedge, current at `where.as_at` and passing `where`, in which `node` is the
  value of some binding (an entity id or, for nesting, a hyperedge id), optionally only in role `role` or relation
  `relation`. A node in two roles of one fact returns that fact once. Literals are values, not nodes, so they are
  never incident: find them with `find` [R01 D-09].
- **`find(relation, pattern, match)`**: `at_least` (default) returns hyperedges whose binding multiset contains the
  pattern's `(role, value)` multiset, so two `agent` patterns need two distinct `agent` bindings; `exact` requires
  equality of the whole multiset [R01 C2-R04; TypeQL "at least" semantics]. Values compare by canonical equality
  (§2.6); positions compare only when the pattern gives them. A pattern value `{"special": "unbound"}` finds goals
  with that open slot.
- **`find_by_key(relation, key)`** requires the pattern to bind exactly the declared key roles and returns the
  records with that key digest that pass `where` (with `as_of`, "the fact valid then for that key").
- **Order and pagination.** Every list result is ordered by id in code-point order; `limit` and `after=<last id>`
  paginate stably [R01 C2-R16]. This is the order P10's closed choices and P9's replays rely on.
- **Degree** counts what `incident` would return, without materialising it [R01 C2-R12].
- **Nothing is deleted.** Retraction, supersession and suppression are new versions; physical erasure is not in 1.0
  [R01 C2-R08].

### 6.3 Supersession walk

`supersession_walk(id, direction)` is a breadth-first traversal over supersession records: `forward` follows
superseded -> superseding, `backward` the reverse. Steps are `{"depth", "via", "reason", "from", "to"}` ordered by
depth, then `recorded_at`, then id; `terminal` lists the reached facts with no further supersession in that
direction (going forward, the current beliefs). It terminates because writes reject cycles and the walker keeps a
visited set [R01 C2-R05]. With `as_at`, only supersession records recorded by then count.

### 6.4 Export

`export("khg-jsonl")` is the canonical container of `iter_records`; `export("hif")` passes it through `to_hif`
(snapshot only; `relations` makes a slice). `iter_records(where=None)` yields every current record whatever its
status, which is what a round trip needs; a `Where` exports a filtered view.

### 6.5 Capability flags

A missing capability makes a scenario `inapplicable`, never `passed` [R04 §9.3], and the method raises
`CapabilityMissing` rather than answering wrongly. The un-flagged core is: entity and hyperedge records with entity
values, `put`, `get`, `incident`, `find`, `iter_records`, `export`.

| Flag | Semantics it covers |
|---|---|
| `literal_values` | literal-valued bindings stored and matched with C1 literal equality |
| `special_values` | `somevalue`, `novalue`, `unbound`, including goals whose slots are all unbound |
| `nesting` | hyperedge-valued bindings; `incident(fact_id)` |
| `ordered_roles` | positions |
| `temporal_valid` | `where.as_of`, `end_validity` |
| `temporal_tx` | `where.as_at`, `history`, `get(version=)` |
| `key_index` | `find_by_key`, collision detection |
| `atomic_events` | `apply` is all-or-nothing |
| `history_export` | `iter_records(content="history")`, `load` of history containers |

### 6.6 Reference implementation

`khg_contracts.store.memory.MemoryStore(schemas, clock)`: versions per id in lists, indexes `node -> fact ids`,
`relation -> fact ids`, `(relation, key digest) -> fact ids`, and supersession maps in both directions. Reads pick
the version at `as_at`, then test the filters. It has every capability. A prototype of it passed all 18 scenarios
of §6.7, including two round trips of the whole gate fixture that reproduce the fixture container
exactly, versions and supersession included **[validated]**.

### 6.7 The conformance suite

Declarative scenario files, format **`khg-store-scenario/1.0.0`**, in the style of the openCypher TCK and the W3C
manifests [R04 §9.2, O13]; one pytest runner parametrised over a registry of store factories, as rdflib does; an
EARL-shaped JSON report with outcomes `passed`, `failed`, `inapplicable`, `untested`.

| Scenario field | Meaning |
|---|---|
| `id`, `title` | |
| `requires` | capability flags; missing means `inapplicable` |
| `given` | steps: `{"fixture": [ids] or "all"}` writes records of the gate fixture through `put` (and `apply` for the supersession); `{"put": record}`; `{"apply": event}`; `{"load": "fixture:gate"}` or `{"load": [records]}` bulk-loads a container |
| `when` | `{"op": <Store method>, "args": {...}}` |
| `then` | `{"ids": [...]}` (result ids in order), `{"result": {...}}` (subset match), `{"count": n}`, `{"container_equals": "fixture:gate"}` (the export parses to that container, header provenance fields aside), or `{"error": code, "info"?: {...}, "codes"?: [...]}` |
| `side_effects` | further `{op, args, then}` checks on the store's state |

Clock rule: the runner gives the store a clock starting at `2026-09-23T10:00:00Z` that advances one second per
written version, so transaction times in scenarios are exact. Records in `given` are written as a writer would send
them: store-assigned and derived fields stripped (the store must recompute them).

A factory is any callable `factory(schemas, clock) -> Store` that returns an empty store. The same runner serves
three entry points: the pytest plugin (`--khg-store=module:factory`), the CLI (`khg-conformance`), and
`khg_contracts.store.conformance.run(factory, *, capabilities=None) -> dict`, which returns the EARL-shaped report
and is what P1 calls per backend (§1.4). `capabilities` defaults to the store's own flags; passing fewer reproduces
the capability-limited run below.

One scenario, as run **[validated]**:

```json
{
  "id": "S-SUP-001",
  "title": "supersede is atomic: record, status, pointer; the walk terminates at the current belief",
  "requires": ["atomic_events", "key_index"],
  "given": [
    {
      "fixture": [
        "cell:HeLa",
        "disease:T1DM",
        "disease:T2DM",
        "doc:soc-2024",
        "doc:trial-report-1998",
        "drug:insulin",
        "drug:metformin",
        "effect:hypoglycaemia",
        "gene:TP53",
        "org:ADA",
        "org:Acme",
        "outcome:HbA1c",
        "pop:adults",
        "x:Alice",
        "x:Bob",
        "x:Louis_XIV",
        "x:ORD",
        "x:R1",
        "x:Roi_de_France",
        "x:YYZ",
        "x:Zoë",
        "x:Zürich",
        "x:air-canada",
        "x:Москва",
        "khg:f11-ceo-alice"
      ]
    },
    {
      "apply": {
        "op": "supersede",
        "id": "khg:s01",
        "superseded": ["khg:f11-ceo-alice"],
        "record": "fixture:khg:f12-ceo-bob",
        "reason": "incorrect",
        "evidence": [
          {
            "eid": "ev1",
            "type": "curated",
            "mode": "manual",
            "source": {"doc": "doc:acme-pr-2021"},
            "activity": {"agent": "curator:reviewer-1"}
          }
        ],
        "actor": "curator:reviewer-1"
      }
    }
  ],
  "when": {"op": "supersession_walk", "args": {"id": "khg:f11-ceo-alice"}},
  "then": {"result": {"terminal": ["khg:f12-ceo-bob"]}},
  "side_effects": [
    {
      "op": "get",
      "args": {"id": "khg:f11-ceo-alice"},
      "then": {"result": {"status": "superseded", "version": 2, "superseded_by": ["khg:f12-ceo-bob"]}}
    },
    {
      "op": "find_by_key",
      "args": {"relation": "chief_executive", "key": [{"role": "organisation", "value": {"entity": "org:Acme"}}]},
      "then": {"ids": ["khg:f12-ceo-bob"]}
    },
    {
      "op": "supersession_walk",
      "args": {"id": "khg:f12-ceo-bob", "direction": "backward"},
      "then": {"result": {"terminal": ["khg:f11-ceo-alice"]}}
    }
  ]
}
```

Scenario list for 1.0 (the 18 marked P were prototyped and pass; the rest are specified the same way):

| Area | Scenarios |
|---|---|
| put | S-PUT-001 identical put is a no-op (P); 002 changed content appends a version, `get(as_at)` sees the old one (P); 003 a candidate is refused (P); 004 `unbound` accepted in a goal, refused in an asserted fact (P); 005 an invalid record is refused with its codes; 006 a status change through `put` is refused; 007 an unknown entity reference is refused; 008 `EntityConflict` |
| incident | S-INC-001 default filter and id order (P); 002 role filter, a node in two roles returns the fact once (P); 003 nesting (P); 004 `where.status` and pagination (P); 005 `as_of`; 006 `as_at`; 007 rank and visibility defaults; 008 `degree` equals `len(incident)` |
| find | S-FIND-001 at_least as a multiset (P); 002 exact (P); 003 literal precision (P); 004 quantity units and bounds; 005 ordered positions; 006 `unbound` pattern finds goals; 007 `novalue` |
| keys | S-KEY-001 `find_by_key` with `as_of` (P); 002 collision raises with the policy (P); 003 temporal keys with disjoint intervals do not collide; 004 non-temporal key collides regardless of time; 005 `transition` to asserted re-checks keys |
| lifecycle | S-SUP-001 atomic supersede and walk (P); 002 m superseded by one (merge); 003 cycle refused; 004 `as_at` before the supersession sees the old status; S-TIME-001 `end_validity` keeps status (P); 002 `end_validity` writes `end_time` when the relation has a `to_role`; S-LIFE-001 asserted -> goal refused (P); 002 goal -> asserted needs no unbound slot; 003 `add_evidence` |
| export | S-EXP-001 the gate fixture rebuilt through `put` and one `supersede` event exports equal to it (P); 002 `load` of the gate container keeps versions and transaction times and exports equal to it (P); 003 history export and reload; 004 HIF export validates and imports back |

Run with a store that declares only `literal_values` and `nesting`, the prototype gave 8 passed, 10 inapplicable,
0 failed **[validated]**: every scenario that needs a missing capability is reported inapplicable, none fails.

### 6.8 How P1's five backends implement C2

| Backend | Records | `incident` / `find` / keys / walk | as-of / as-at | Capabilities it would lack, natively |
|---|---|---|---|---|
| **Incidence table** (PostgreSQL 18, SQLite, DuckDB) | `fact_version(id, version, recorded_at, relation, status, rank, visibility, valid_from, valid_to, content_key, core_key, key_digest, arity, record_json)`; `binding(id, version, bid, role, slot, direction, position, entity_id, fact_ref, lit_datatype, lit_lexical, lit_precision, lit_unit, lit_lang, lit_lower, lit_upper, lit_calendar, special)`; `entity(id, label, types)`; `supersession(id, superseded, superseding, reason, recorded_at, record_json)` | index probes on `binding(entity_id)`, `binding(fact_ref)`, `fact_version(relation, key_digest)`, `supersession(superseded)`; temporal keys as `EXCLUDE USING gist (relation WITH =, key_digest WITH =, tstzrange(valid_from, valid_to) WITH &&)` on current asserted rows [R04 §3.3] | version rows plus a `tx_to` column maintained on append | none |
| **Reified RDF 1.2**, relation-instance pattern (pyoxigraph) | a fact node `khgf:<id>` with `rdf:type khgr:<relation>`; one binding node per binding (`khg:role`, `khg:value`, `khg:position`, `khg:direction`), roles as sub-properties of `khg:role` so role triples are told apart from metadata [R01 §3]; literals as typed literals or value nodes (quantity, precision); special values as `khg:somevalue`/`khg:novalue`/`khg:unbound` individuals; versions as named graphs | SPARQL over binding nodes; `khg:keyDigest` literal indexed by the store | named graph per version for as-at | `temporal_tx` and `history_export` if versions are not kept as named graphs; the RDF 1.2 annotation form (only with `primary`) is a lossy extra [R01 C1-R57] |
| **Bipartite property graph** (Neo4j; Kùzu pinned at 0.11.3, archived [R04 M9]) | `(:Fact {id, version, relation, status, ...})-[:BINDS {bid, role, slot, direction, position}]->(:Entity \| :Literal \| :Fact)`; role as a relationship property (open vocabulary) or as the relationship type (small vocabulary, faster) [R01 §3] | `MATCH (n)<-[:BINDS]-(f)`; key digest as an indexed property; `(:Supersession)` nodes | `(:FactVersion)` chain | `temporal_tx` if versions are not kept |
| **TypeDB 3.x** | `relation treats, relates treats:treatment ...` with scoped role names derived from the global ids; entity fillers as role players; hyperedge fillers as relations playing roles (nesting); literal fillers as attributes owned by the relation [R04 M2] | TypeQL `match`; key digest as an owned `@unique` attribute; temporal collisions checked in code | versions as explicit relations | `ordered_roles` (no ordered role lists [R04 M1]), `special_values` (a goal with no role players is removed as a dangling relation [R04 §11]), `temporal_tx`, `history_export`; literal `incident` does not arise (literals are not nodes in C2 either) |
| **HIF** (an in-memory index over a khg-hif file) | `from_hif` into a `MemoryStore` | as the reference store | snapshot only | `temporal_tx`, `history_export` (a HIF file carries one snapshot) |

A backend may emulate a missing capability (TypeDB can reify bindings as relations to get positions); that is
exactly the cost P1 measures, so the flags describe the native mapping and P1 reports both.

### 6.9 Timing hooks

`Timed(store, clock=time.perf_counter_ns)` wraps any `Store` and records `(method, args digest, nanoseconds,
result size)` per call, so P1 measures load time and query latency the same way on every backend
[R01 C2-R15].

---

## 7. C3: candidate queue, structural linter and action log

Format id **`khg-queue/1.0.0`** (versioned with C1, PLAN §7). JSON Schema: `khg-queue-1.0.0.schema.json`.

### 7.1 The queue file

One queue is one append-only JSONL file (`.khg-queue.jsonl`): line 1 a `queue-header`, then `queue-item` and
`log-entry` lines in append order. Nothing is ever rewritten; an item's state is a fold over its log entries
(F9; R01 D-18, C3-R11). One writer per file: P9 writes one file per (run, order), and ids are scoped by the queue id
(`q:<queue_id>.<seq>`, `l:<queue_id>.<seq>`, payload ids `cand:<queue_id>.<seq>`), so files from parallel runs
concatenate without collisions for scoring and replay.

```json
{
  "kind": "queue-header",
  "format": "khg-queue/1.0.0",
  "queue_id": "p2-smoke",
  "record_format": "khg-record/1.0.0",
  "created_at": "2026-09-23T10:00:00Z"
}
```

The API, in `khg_contracts.queue`, is what P9's loop in §1.4 calls:

```python
class Queue:
    queue_id: str
    @classmethod
    def create(cls, path: str | Path, *, queue_id: str, clock: Callable[[], str] | None = None) -> "Queue": ...
        # writes the queue-header line; refuses an existing file; clock defaults to UTC wall time (RFC 3339)
    @classmethod
    def open(cls, path: str | Path, *, clock: Callable[[], str] | None = None) -> "Queue": ...
        # reads and checks an existing file (L0, L2, L3: Q- codes); later appends go to its end
    def submit(self, item_kind: Literal["hyperedge", "supersession_proposal", "merge_proposal"], payload: dict, *,
               submitted_by: str, run: dict | None = None, doc: dict | None = None,
               entities: list[dict] | None = None) -> dict: ...
        # assigns qid q:<queue_id>.<seq>; a hyperedge payload without an id gets cand:<queue_id>.<seq> (same seq;
        # any other id is Q-PAYLOAD); checks the line against the queue schema, appends it and returns it
    def log(self, target: str, action: str, *, actor: dict, mode: str = "automatic", **fields) -> dict: ...
        # checks the state machine (Q-TRANSITION), sets lid and parent, appends and returns the entry
    def item(self, qid: str) -> dict: ...
    def state(self, qid: str) -> str: ...                                   # the fold of §7.3
    def items(self, *, item_kind: str | None = None, state: str | None = None) -> list[dict]: ...   # append order
    def entries(self, qid: str) -> list[dict]: ...                          # the item's log entries, in order

def make_candidate(record: dict, *, schema: Schema) -> dict: ...
    # drops store-assigned fields, sets status candidate, runs normalize (slots, keys, arity, event_hash)
def queue_items(paths: Iterable[str | Path], *, item_kind: str = "hyperedge") -> Iterator[dict]: ...
    # the items of that kind from several files, file by file in append order: what C5 reads (§9.2)
```

Items and log entries have separate sequences, so the smoke test's fourth item is `q:p2-smoke.000004` while its
lint entry is `l:p2-smoke.000005` (§7.8).

### 7.2 Queue items

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `kind` | `"queue-item"` | yes | |
| `qid` | `q:<queue_id>.<seq>` | yes | |
| `item_kind` | `hyperedge` \| `supersession_proposal` \| `merge_proposal` | yes | |
| `submitted_at`, `submitted_by` | timestamp, string | yes | |
| `run` | `{run_id, order_id, position, seed?, permutation?}` | for `hyperedge` | what P9's instability design needs: run, insertion order and position in it (Q05) [R01 C3-R02; PLAN §4 P9] |
| `doc` | `{doc, doc_sha256}` | for `hyperedge` | the source document and its NFC SHA-256; extracted evidence must point at it (`Q-DOC-HASH`) |
| `payload` | object | yes | per kind, below |
| `entities` | `[entity record]` | no | entities the candidate introduces (so a candidate can name a new entity) |

Payloads:

- `hyperedge`: a C1 hyperedge record with `status: candidate` and a provisional id in the reserved `cand:` namespace
  (assigned by `submit`), normalised by `make_candidate` (so it carries `keys.content` for set agreement across runs
  [R01 C3-R04] and `event_hash` on its extracted evidence), with at least one evidence record (Q01-Q04). The
  extractor, model, prompt or skill version and decoding parameters live in `evidence[].activity` [R01 C3-R02,
  C3-R13]; the model's own score in `evidence[].confidence` [R01 C3-R03].
- `supersession_proposal`: `{superseded, superseding (store id or qid), reason, evidence}`.
- `merge_proposal`: `{source (qid or store id), target (store id), relation: duplicate | refinement, evidence?}`.

Binding proposals for goal slots (P11) arrive in 1.1 [R01 C3-R14].

```json
{
  "kind": "queue-item",
  "qid": "q:p2-smoke.000001",
  "item_kind": "hyperedge",
  "submitted_at": "2026-09-23T10:00:01Z",
  "submitted_by": "p9-extractor/0.1.0",
  "run": {"run_id": "r1", "order_id": "o1", "position": 0, "seed": 13},
  "doc": {"doc": "doc:soc-2024", "doc_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739"},
  "payload": {
    "kind": "hyperedge",
    "id": "cand:p2-smoke.000001",
    "schema": "p2-gate/1.0.0",
    "relation": "treats",
    "status": "candidate",
    "rank": "normal",
    "visibility": "visible",
    "valid_time": {"from": "2024-01-01"},
    "bindings": [
      {"bid": "b2", "role": "condition", "slot": "core", "direction": "head", "value": {"entity": "disease:T2DM"}},
      {
        "bid": "b3",
        "role": "dose",
        "slot": "qualifier",
        "value": {"datatype": "quantity", "literal": "500", "unit": "wd:Q3241121"}
      },
      {
        "bid": "b5",
        "role": "hba1c_change",
        "slot": "qualifier",
        "value": {"datatype": "decimal", "literal": "-1.12"}
      },
      {"bid": "b4", "role": "population", "slot": "qualifier", "value": {"entity": "pop:adults"}},
      {"bid": "b1", "role": "treatment", "slot": "core", "direction": "tail", "value": {"entity": "drug:metformin"}}
    ],
    "confidence": {"scale": "probability", "value": 0.95},
    "evidence": [
      {
        "eid": "ev1",
        "type": "extracted",
        "mode": "automatic",
        "source": {"doc": "doc:soc-2024", "doc_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739"},
        "selectors": [
          {
            "exact": "Metformin is the preferred initial pharmacologic agent for the treatment of type 2 diabetes in adults.",
            "type": "quote"
          },
          {"end": 102, "start": 0, "type": "position"}
        ],
        "activity": {
          "agent": "p9-extractor/0.1.0",
          "model": "model-y/2026-08",
          "params": {"seed": 13, "temperature": 0},
          "prompt": "treats-skill/1.2.0",
          "run": "r1"
        },
        "confidence": {"scale": "probability", "value": 0.9},
        "event_hash": "sha256:ec92cafb15cde9c2454f34b99581c8a85537289c02a4f27eb1af576a6698fb17"
      },
      {
        "eid": "ev2",
        "type": "curated",
        "mode": "manual",
        "source": {"doc": "doc:soc-2024", "doc_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739"},
        "selectors": [
          {"exact": "The usual starting dose is 500 mg", "type": "quote"},
          {"end": 136, "start": 103, "type": "position"}
        ],
        "activity": {"agent": "curator:reviewer-1"},
        "binding_refs": ["b3"]
      }
    ],
    "arity": {"arity": 5, "core": 2, "participants": 5},
    "keys": {
      "content": "sha256:09c8cc13dc74f8c3f6f2db9d3bdff24860523db953aeb713dc80eb6e1d1dc6d7",
      "core": "sha256:55449857f34d1a8a27ef8c72d6117c4a882cc055e83a3b572db6f7e0f0966b57"
    }
  }
}
```

### 7.3 State machine

`pending` -> (`lint` with outcome `pass`) `linted` | (`flag`) `needs_review` | (`reject`) `rejected`;
`linted` -> `accepted` | `rejected` | `merged` | `needs_review`; `needs_review` -> `accepted` | `rejected` |
`merged`. `accepted`, `rejected` and `merged` are terminal. A log entry that breaks the machine is `Q-TRANSITION`
(Q09); a log entry for an unknown item is `Q-LOG-TARGET` (Q08). `verdict` entries annotate and do not change state
[R01 C3-R05].

### 7.4 Log entries (who, what, when, why, before, after)

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `kind` | `"log-entry"` | yes | |
| `lid` | `l:<queue_id>.<seq>` | yes | |
| `parent` | lid or null | yes | the previous entry for the same target, so replay order is defined (MediaWiki's parent revision) [R04 M7] |
| `target` | qid | yes | |
| `action` | `lint` \| `accept` \| `reject` \| `flag` \| `merge` \| `verdict` \| `auto_fix` | yes | what (Q06) |
| `outcome` | `pass` \| `flag` \| `reject` | for `lint` | |
| `findings` | `[{rule, rule_version, severity, path?, value?, message, proposal?}]` | for `lint` | severities `violation`, `warning`, `info` (SHACL's) [R04 M7] |
| `result` | `"<store id>@<version>"` | for `accept`, `merge` | the store record the item became [R01 C3-R05] |
| `reason` | string | no | why |
| `before`, `after` | object | for `auto_fix` and `merge` | snapshots, as INDRA's curation table keeps `pa_json`/`ev_json` [R04 M7] |
| `verdict` | §7.5 | for `verdict` | |
| `at` | timestamp | yes | when |
| `actor` | `{kind: linter\|person\|agent\|system, id}` | yes | who: `khg-lint/1.0.0`, a curator, an acceptor agent |
| `mode` | `automatic` \| `manual` \| `semi_automatic` | yes | EARL mode |

### 7.5 Verdicts

The verdict unit is the pair (candidate, evidence), keyed by `(keys.core, event_hash)`, so a verdict carries over
to every re-extraction of the same event in later runs [R04 O9; INDRA]. Labels: `correct`, `no_relation`,
`wrong_relation`, `wrong_role`, `wrong_filler`, `span_boundary`, `missing_participant` (R01's "incomplete"),
`negated`, `hypothesis`, `other` (a `note` is required, Q10); `binding_refs` names the wrong bindings
[R01 C3-R06]. A candidate's verdict is `correct` if any of its pairs is correct, else the most frequent error label,
ties broken in the order listed.

### 7.6 The structural linter

`Linter(schema, store=None, doc_text=None).lint(queue, qid) -> log entry`. `store` answers entity references and
the identity lints; without one, `C-ENTITY-REF` accepts only the entities in `item.entities` and the identity lints
are skipped. `doc_text` maps a document id to its NFC text and enables `Q-SPAN`. **Structural lint** (the gate's
clause) is the first six rules; identity lints run only when no violation was found.

| Rule | Severity | Action | What |
|---|---|---|---|
| any `R-*` from L2 (record schema) | violation | reject | the payload is not a C1 record |
| any `R-*`, `S-*` error from L3 against the schema | violation | reject | the payload breaks the relation type (role not allowed, `max`, filler type, datatype, positions, constraints) [R01 C3-R08] |
| `S-ROLE-MIN` on a candidate | warning | flag -> `needs_review` | an incomplete candidate is reviewed, not dropped (R01's "incomplete") |
| `C-ENTITY-REF` | violation | reject | an entity neither in the store nor in `item.entities` |
| `Q-DOC-HASH` | violation | reject | extracted evidence does not point at `item.doc` |
| `Q-SPAN` (when `doc_text` is given) | violation | reject | a quote selector differs from `text[start:end]` |
| `L-DUPLICATE` | info | a `merge_proposal` (duplicate) | `keys.content` equals a current stored fact: add as evidence, never a second fact [R01 C3-R10] |
| `L-REFINEMENT` | info | a `merge_proposal` (refinement) | same `keys.core`, and the candidate's qualifier bindings are a superset: flagged for review, never merged blindly [R01 C3-R09; ER §5 via R01] |
| `L-KEY-COLLISION` | violation if the policy is `reject`, else info | per policy (§3.3): `supersession_proposal`, `merge_proposal`, a suggested `end_validity`, or a note | a current fact has the same key digest and an overlapping valid time |
| `L-SAME-EVENT` | info | a `merge_proposal` that is a no-op | the same `event_hash` already reached the store |

Outcome: `reject` if any violation, else `flag` if any warning, else `pass`. The corpus-level quality lints of
R01 C3-R09 (provenance coverage, role completeness, evidence-type mix) come in 1.1.

### 7.7 Accept, merge, replay

`accept(queue, qid, store, new_id, actor)` re-ids the payload (`cand:` to a store id), sets `status: asserted`, puts
the entities it introduced and the record, and logs `accept` with `result`. `merge(queue, qid, target, store,
actor)` calls `apply({"op": "add_evidence"})` on the target and logs `merge`. `replay(queue_lines, store)`
re-applies every `accept` and `merge` in log order to a fresh store; the result must equal the original store's
content (`V49`'s concern is a replay test, not a malformed file) [R01 C3-R11].

### 7.8 The smoke test (G3), as run

Three candidates from the gate fixture's treats fact: the fact itself from run r1; the same fact from run r2 with
one new extracted evidence record; and a copy whose `condition` role was renamed to `remedy` **[validated]**:

```jsonc
// queue item q:p2-smoke.000001: a hyperedge candidate (cand:p2-smoke.000001), shown in full above for the first one
{"kind": "log-entry", "lid": "l:p2-smoke.000001", "parent": null, "target": "q:p2-smoke.000001", "action": "lint", "outcome": "pass", "findings": [], "at": "2026-09-23T10:00:02Z", "actor": {"id": "khg-lint/1.0.0", "kind": "linter"}, "mode": "automatic"}
{"kind": "log-entry", "lid": "l:p2-smoke.000002", "parent": "l:p2-smoke.000001", "target": "q:p2-smoke.000001", "action": "accept", "result": "khg:f01-treats@1", "at": "2026-09-23T10:00:04Z", "actor": {"id": "p2-smoke-acceptor/1.0.0", "kind": "agent"}, "mode": "automatic"}
// queue item q:p2-smoke.000002: a hyperedge candidate (cand:p2-smoke.000002), shown in full above for the first one
{"kind": "queue-item", "qid": "q:p2-smoke.000003", "item_kind": "merge_proposal", "payload": {"relation": "duplicate", "source": "q:p2-smoke.000002", "target": "khg:f01-treats"}, "submitted_at": "2026-09-23T10:00:06Z", "submitted_by": "khg-lint/1.0.0"}
{"kind": "log-entry", "lid": "l:p2-smoke.000003", "parent": null, "target": "q:p2-smoke.000002", "action": "lint", "outcome": "pass", "findings": [{"message": "same content key as khg:f01-treats: add as evidence", "proposal": "q:p2-smoke.000003", "rule": "L-DUPLICATE", "rule_version": "khg-lint/1.0.0", "severity": "info"}], "at": "2026-09-23T10:00:07Z", "actor": {"id": "khg-lint/1.0.0", "kind": "linter"}, "mode": "automatic"}
{"kind": "log-entry", "lid": "l:p2-smoke.000004", "parent": "l:p2-smoke.000003", "target": "q:p2-smoke.000002", "action": "merge", "result": "khg:f01-treats@2", "at": "2026-09-23T10:00:09Z", "actor": {"id": "p2-smoke-acceptor/1.0.0", "kind": "agent"}, "mode": "automatic"}
// queue item q:p2-smoke.000004: a hyperedge candidate (cand:p2-smoke.000004), shown in full above for the first one
{"kind": "log-entry", "lid": "l:p2-smoke.000005", "parent": null, "target": "q:p2-smoke.000004", "action": "lint", "outcome": "reject", "findings": [{"message": "cannot normalise against the schema: ('treats', 'remedy')", "rule": "R-DERIVED", "rule_version": "khg-lint/1.0.0", "severity": "violation"}, {"message": "role remedy not allowed for treats", "path": "cand:p2-smoke.000004/b2", "rule": "S-ROLE", "rule_version": "khg-lint/1.0.0", "severity": "violation"}, {"message": "condition bound 0 times, min 1", "path": "cand:p2-smoke.000004", "rule": "S-ROLE-MIN", "rule_version": "khg-lint/1.0.0", "severity": "warning"}], "at": "2026-09-23T10:00:11Z", "actor": {"id": "khg-lint/1.0.0", "kind": "linter"}, "mode": "automatic"}
```

Assertions of `tests/gate/test_smoke.py`, with the prototype's results:

| Assertion | Result |
|---|---|
| first candidate: structural lint outcome, findings | `pass`, none |
| accepted as | `khg:f01-treats@1` |
| stored content equals the fixture record | True |
| second-run duplicate: lint outcome, findings | `pass`, L-DUPLICATE (with a merge proposal) |
| merged into | `khg:f01-treats@2` (evidence now ev1, ev2, ev3; 2 versions, one fact) |
| malformed candidate: lint outcome, rules | `reject`, R-DERIVED, S-ROLE, S-ROLE-MIN |
| malformed candidate reached the store | False |
| final states | `q:p2-smoke.000001` accepted, `q:p2-smoke.000002` merged, `q:p2-smoke.000003` pending, `q:p2-smoke.000004` rejected |
| `export('khg-jsonl')` lines; `export('hif')` valid against the vendored schema | 27; True |
| replay of the log into a fresh store reproduces the store | True |
| every queue line valid against `khg-queue-1.0.0` | True |

---

## 8. Validator and the malformed-case list

### 8.1 Layers

| Layer | What | Engine | Codes |
|---|---|---|---|
| **L0 strict JSON** | UTF-8, not empty, no duplicate keys, no `NaN`/`Infinity`, no lone surrogates, top level (or each JSONL line) an object | `json.loads(parse_constant=..., object_pairs_hook=...)` | `J-ENCODING`, `J-PARSE`, `J-DUP-KEY`, `J-NAN`, `J-SURROGATE`, `J-NOT-OBJECT` |
| **L1 HIF schema** | the vendored `hif_schema_v0.1.0.json` (blob `e2105bb`), unchanged (F2); HIF inputs only | jsonschema `Draft7Validator` or fastjsonschema | `H-SCHEMA` |
| **L2 profile schemas** (draft-07, F5) | `khg-hif-1.0.0` (P), `khg-record-1.0.0` (R), `khg-relation-schema-1.0.0` (D), `khg-queue-1.0.0` (Q), `khg-c4-items-0.1.0` (I) | same; the HIF `$ref` resolves offline to the vendored bytes | from `x-khg-code` annotations, else `<layer>-SCHEMA` |
| **L3 semantic** (Python) | references, keys, time, acyclicity, role-usage conformance, derived fields, status rules, queue state | `khg_contracts.validate.semantic` | `P-`, `R-`, `S-`, `C-`, `D-`, `Q-`, `L-` codes |

A later layer runs only when the earlier ones pass, so every malformed input has one first rejecting layer; within
L3 every finding is reported. A finding is `{"code", "severity": "error"|"warning", "layer", "path" (JSON pointer),
"record" (id or line number), "message"}`. Codes are the contract; messages are not.

The entry points, in `khg_contracts.validate` and re-exported at the top level:

```python
def validate_container(src: str | Path | Iterable[str], *, engine: str = "jsonschema") -> Report  # L0-L3
def validate_record(record: dict, schema: Schema, *, engine: str = "jsonschema") -> Report        # L2, L3 (R-, S-)
def validate_hif(src: str | Path | dict, *, profile: bool = True, engine: str = "jsonschema") -> Report
    # profile=True: L0-L3 of khg-hif; profile=False: L0-L1 plus the roles-convention checks (any HIF file)
def validate_schema(src: str | Path | dict) -> Report                                            # D- codes
def validate_queue(src: str | Path | Iterable[str], *, schema: Schema | None = None) -> Report   # Q- codes
def validate_item(item: dict) -> Report                            # I- codes, dispatched on item["kind"]

@dataclass(frozen=True)
class Report:
    findings: tuple[Finding, ...]      # layer, then record, then path order
    errors: tuple[Finding, ...]        # the findings with severity "error"
    ok: bool                           # no errors; warnings allowed
```

`load_schema(src) -> Schema` runs `validate_schema` and raises `SchemaInvalid(report)` on any error, so every
`Schema` object a consumer holds is valid. `validate_record` leaves out the cross-record `C-` checks, which need the
whole container or a store.

**Mapping a JSON Schema error to a code.** Walk the error's absolute schema path from the root, dereferencing `$ref`
before each step (jsonschema leaves `$ref` out of the path and continues inside the target), and keep the last
`x-khg-code` seen; for `oneOf`/`anyOf` failures walk the branch errors too; with no annotation the code is
`<layer>-SCHEMA`. fastjsonschema reports only the first error but exposes its subschema (`exc.definition`), whose
`x-khg-code` is the code. The value union is dispatched by tag (`if required entity then ...`) with a separate
exactly-one-tag rule, so a bad literal reports `R-LIT-LEXICAL`, not an opaque `oneOf` failure **[validated]**.
jsonschema is the default (it reports every error; the gate uses it); fastjsonschema (extra `[fast]`) is the fast
path for bulk validation of P3a's corpus. Draft-07 and both engines are what HIF itself uses [R02 §5; R04 O11].

**Status-dependent rules** [R01 C1-R72]: goals and candidates may miss required roles (warning); only goals may hold
`unbound`; goals need no evidence; `candidate` never appears in a store or container (M85); `cand:` ids appear only
in queue payloads.

### 8.2 The code registry

`khg_contracts/validate/codes.py` lists every code with its layer, default severity and message template; the
malformed-case index names codes from it, and a test asserts that every code in the registry is exercised by at
least one case or unit test.

| Prefix | Layer | Scope |
|---|---|---|
| `J-` | L0 | JSON text |
| `H-` | L1 | the HIF schema |
| `P-` | L2, L3 | the khg-hif profile and the HIF import |
| `R-` | L2, L3 | one C1 record in itself |
| `S-` | L3 | one C1 record against its relation-type schema |
| `C-` | L3 | across records of a container or store |
| `D-` | L2, L3 | relation-type schema documents |
| `Q-` | L2, L3 | queue files |
| `I-` | L2 | C4 items (§9.6) |
| `L-` | lint | identity lints (never make a file invalid) |
| `F-` | foreign import | legacy and foreign HIF (§4.5) |

### 8.3 The malformed-case list for 1.0

Every case is a minimal mutation of a valid fixture (the gate container, its HIF export, the directed slice, or the
smoke-test queue), stored under `tests/fixtures/malformed/` with `INDEX.json` giving the expected layer and code.
All 96 were run through the prototype validator and rejected as listed **[validated]**; "Also reported" shows the
other codes the same input raised.

| Case | Input | Malformed case | Layer | Code | Also reported | Source |
|---|---|---|---|---|---|---|
| M01 | HIF | zero-byte file | L0 | `J-PARSE` |  | R02 case 34 |
| M02 | HIF | NaN literal in attrs | L0 | `J-NAN` |  | R01 V19; R02 case 35; R03 c22 |
| M03 | HIF | duplicate key inside one attrs object | L0 | `J-DUP-KEY` |  | R02 case 36 |
| M04 | HIF | lone UTF-16 surrogate escape in a string | L0 | `J-SURROGATE` |  | RFC 8259 §8.2 |
| M05 | HIF | no incidences key | L1 | `H-SCHEMA` |  | R01 V01; R02 case 31 |
| M06 | HIF | extra top-level key (roles) | L1 | `H-SCHEMA` |  | R01 V02; R02 case 05 |
| M07 | HIF | top-level version key | L1 | `H-SCHEMA` |  | R02 case 04 |
| M08 | HIF | record-level role on an incidence (outside attrs) | L1 | `H-SCHEMA` |  | R01 V03; R02 case 11 |
| M09 | HIF | incidence without node | L1 | `H-SCHEMA` |  | R01 V04 |
| M10 | HIF | direction outside head/tail | L1 | `H-SCHEMA` |  | R01 V05; R02 case 12 |
| M11 | HIF | id of the wrong type (float) | L1 | `H-SCHEMA` |  | R01 V06; R02 cases 18-20 |
| M12 | HIF | integer id (valid HIF, outside the profile: ids are strings) | L2 | `P-ID` |  | R02 case 15; F10 |
| M13 | HIF | network-type asc | L2 | `P-NETWORK-TYPE` |  | R03 D8, c04 |
| M14 | HIF | metadata without the profile declaration | L2 | `P-METADATA` |  | R01 V07 |
| M15 | HIF | metadata without the roles-convention declaration | L2 | `P-METADATA` |  | R01 V07; F15 |
| M16 | HIF | incidence without a role | L2 | `P-ROLE` |  | R01 V08 |
| M17 | HIF | empty role string | L2 | `P-ROLE` |  | R01 V09 |
| M18 | HIF | role list instead of one role per incidence record | L2 | `P-ROLE` |  | R01 V09; §4.2 |
| M19 | HIF | metadata.default_attrs (HyperNetX would invent values from it) | L2 | `P-METADATA` |  | R03 D7, c20 |
| M20 | HIF | record-level weight (the profile never writes or reads weight) | L2 | `P-SCHEMA` |  | R03 D6; R01 D-13 |
| M21 | HIF (directed) | directed network, one incidence without direction | L2 | `P-DIRECTED-NO-DIRECTION` |  | R01 V12; R02 case 23; R03 c14 |
| M22 | HIF | edge without relation | L2 | `P-RELATION` |  | R01 V14 |
| M23 | HIF | edge attr outside relation/khg-* (confidence written as a bare number) | L2 | `P-SCHEMA` |  | R01 C1-R64; F3 |
| M24 | HIF | node declared twice | L3 | `P-DUP-NODE` |  | R01 V16; R03 D5, c19 |
| M25 | HIF | the same incidence record twice (same edge and khg-bid) | L3 | `P-DUP-BID` |  | R01 V10 (as refined in §4.2) |
| M26 | HIF | incidence names a node with no node record | L3 | `P-UNDECLARED-NODE` |  | R01 V17; R02 case 28 |
| M27 | HIF | incidence names an edge with no edge record | L3 | `P-UNDECLARED-EDGE` |  | R02 case 29 |
| M28 | HIF | hyperedge-reference node pointing at a missing edge | L3 | `P-REF-DANGLING` |  | R01 V18 |
| M29 | HIF | literal node whose id is not the hash of its literal | L3 | `P-LITERAL-ID` |  | R01 D-09 |
| M30 | HIF | role not allowed for the relation (caught after import) | L3 | `S-ROLE` |  | R01 V22 |
| M40 | container | unknown record kind | L2 | `R-KIND` |  | §2.1 |
| M41 | container | hyperedge without relation | L2 | `R-SCHEMA` |  | R01 V14 |
| M42 | container | id without namespace and with a space | L2 | `R-ID` |  | R01 C1-R04; R02 cases 16, 21 |
| M43 | container | id not in NFC (decomposed e + diaeresis) | L3 | `R-ID-NFC` | C-ENTITY-REF | R03 c13; F11 |
| M44 | container | id in a reserved namespace | L3 | `R-ID-RESERVED` | C-ENTITY-REF | §2.2 |
| M45 | container | value with two tags | L2 | `R-VALUE` |  | R01 C1-R06 |
| M46 | container | decimal not in canonical form (trailing zero) | L2 | `R-LIT-LEXICAL` |  | R01 C1-R52; R04 M2 |
| M47 | container | impossible calendar date | L3 | `R-LIT-DATE` | R-DERIVED | R01 V26 |
| M48 | container | time lexical form finer than its declared precision | L2 | `R-LIT-LEXICAL` |  | R01 V26 |
| M49 | container | quantity without unit | L2 | `R-LIT-UNIT` |  | R01 V26 |
| M50 | container | lang-string without lang | L2 | `R-LIT-LANG` |  | R01 V26 |
| M51 | container | quantity amount below its lower bound | L3 | `R-LIT-BOUNDS` | R-DERIVED | R04 M2 |
| M52 | container | status outside the lifecycle | L2 | `R-STATUS` |  | R01 V36 |
| M53 | container | two bindings with the same bid | L3 | `R-DUP-BID` |  | §2.5 |
| M54 | container | evidence on a binding that does not exist | L3 | `R-EVIDENCE-REF` |  | R01 C1-R36 |
| M55 | container | text selectors without the document hash | L2 | `R-EVIDENCE-DOC-HASH` |  | F11; R04 O8 |
| M56 | container | position span disagrees with the quote length (code points) | L3 | `R-SELECTOR-SPAN` | R-DERIVED | F11; R04 M6 |
| M57 | container | valid_time.from after valid_time.to | L3 | `R-VALID-TIME` |  | R01 V30 |
| M58 | container | declared arity disagrees with the bindings | L3 | `R-DERIVED` |  | R01 V15 |
| M59 | container | valid_time disagrees with the time bindings | L3 | `R-DERIVED` |  | R01 C1-R47, D-07 |
| M60 | container | relation not declared in the schema | L3 | `S-RELATION` | S-FILLER, S-NESTING | R01 V21 |
| M61 | container | role not allowed for the relation | L3 | `S-ROLE` |  | R01 V22 |
| M62 | container | required role missing on an asserted fact | L3 | `S-ROLE-MIN` |  | R01 V23 |
| M63 | container | role bound more often than max | L3 | `S-ROLE-MAX` | S-FILLER | R01 V24 |
| M64 | container | entity of the wrong type | L3 | `S-FILLER` |  | R01 V25 |
| M65 | container | literal where an entity is expected | L3 | `S-FILLER` |  | R01 V25 |
| M66 | container | hyperedge with no bindings | L3 | `S-NO-BINDINGS` | S-ROLE-MIN | R01 V27 |
| M67 | container | a hyperedge that references itself | L3 | `C-NESTING-CYCLE` | S-FILLER, S-NESTING | R01 V28 |
| M68 | container | reference to a relation that is not nestable | L3 | `S-NESTING` | S-FILLER | R01 V29 |
| M69 | container | unbound value outside a goal | L3 | `S-UNBOUND` |  | R01 V34 |
| M70 | container | novalue and a concrete value for the same role | L3 | `S-NOVALUE-MIXED` | S-FILLER | R01 V35 |
| M71 | container | asserted fact without evidence | L3 | `S-EVIDENCE-MISSING` |  | R01 V33 |
| M72 | container | direction contradicting the role usage | L3 | `S-DIRECTION` |  | R01 V38 |
| M73 | container | ordered role with a gap in positions | L3 | `S-POSITION` |  | R01 C1-R15 |
| M74 | container | the same filler twice in an unordered role | L3 | `S-DUP-BINDING` |  | R01 C1-R14, C1-R15 |
| M75 | container | must_differ violated | L3 | `S-CONSTRAINT` | S-DUP-BINDING | R01 C1-R34; R04 M1 |
| M76 | container | confidence outside its declared scale | L3 | `S-CONFIDENCE` |  | R01 V32 |
| M77 | container | supersession naming a missing record | L3 | `C-SUPERSESSION` |  | R01 V37 |
| M78 | container | supersession cycle | L3 | `C-SUPERSESSION` |  | R01 V37 |
| M79 | container | status not superseded although a supersession record names it | L3 | `C-SUPERSESSION` | C-KEY-COLLISION | F8 |
| M80 | container | entity reference without an entity record | L3 | `C-ENTITY-REF` |  | R01 V17 |
| M81 | container | entity and hyperedge share an id | L3 | `C-DUP-ID` |  | §2.2 |
| M82 | container | container of an unknown major version | L2 | `R-FORMAT` |  | R01 V41 |
| M83 | container | record typed under a schema the container does not carry | L3 | `C-SCHEMA-REF` |  | R01 V41 |
| M84 | container | two current facts with the same key and overlapping valid time | L3 | `C-KEY-COLLISION` |  | R01 V42 |
| M85 | container | candidate status in a store container | L3 | `C-STATUS-CANDIDATE` |  | F9; R01 D-18 |
| M90 | schema doc | schema version not semver | L2 | `D-SEMVER` |  | R01 V45 |
| M91 | schema doc | relation type with no roles | L2 | `D-NO-ROLES` |  | R01 V43 |
| M92 | schema doc | role used twice in one relation | L3 | `D-DUP-USAGE` |  | R01 V44 |
| M93 | schema doc | key names a role the relation does not use | L3 | `D-KEY` |  | R01 V44 |
| M94 | schema doc | key role that is not required | L3 | `D-KEY` | R-DERIVED | R04 M3 |
| M95 | schema doc | primary names a non-core role | L3 | `D-PRIMARY` |  | R01 V44 |
| M96 | schema doc | unknown entity type in fillers | L3 | `D-TYPE` | S-FILLER | R01 V46 |
| M97 | schema doc | usage of a role missing from the global vocabulary | L3 | `D-ROLE-UNDECLARED` | D-PRIMARY, S-ROLE, S-ROLE-MIN | F4 |
| M98 | schema doc | min > max | L3 | `D-CARDINALITY` | S-ROLE-MIN | §3.2 |
| M99 | schema doc | relation kind outside the enum | L2 | `D-SCHEMA` |  | R01 V40 |

Queue files:

| Case | Malformed case | Layer | Code | Source |
|---|---|---|---|---|
| Q01 | candidate without run metadata | L2 | `Q-PAYLOAD` | R01 V47 |
| Q02 | candidate without evidence | L2 | `Q-PAYLOAD` | R01 V47 |
| Q03 | candidate payload id outside cand: | L2 | `Q-PAYLOAD` | §7.2 |
| Q04 | candidate payload status not candidate | L2 | `Q-PAYLOAD` | F9 |
| Q05 | run without order_id | L2 | `Q-RUN` | PLAN §4 (P9) |
| Q06 | log action outside the vocabulary | L2 | `Q-LOG-ACTION` | R01 V48 |
| Q07 | lint entry without outcome | L2 | `Q-SCHEMA` | §7.4 |
| Q08 | log entry naming a missing queue item | L3 | `Q-LOG-TARGET` | R01 V48 |
| Q09 | accept after a lint reject | L3 | `Q-TRANSITION` | R01 C3-R05 |
| Q10 | verdict 'other' without a note | L2 | `Q-SCHEMA` | R04 M7 |

**R01 candidates not in the list, and why.** V11 (a role repeated inside one incidence's role list): there are no
role lists (M18 rejects the list form). V13 (`direction` in an undirected file): allowed, because HIF allows it and
mixed files need it (§4.3 E8). V20 (legacy `role` and `roles` disagree): a foreign-import error `F-ROLE-CONFLICT`,
tested with the importer. V31 (a transaction interval that ends before it starts): transaction ends are derived and
cannot be written; `C-TX-ORDER` guards history containers. V39 (a node both tail and head of a rule hyperarc): a
1.1 lint for `kind: rule`. V40 (no edge kind): the kind lives on the relation type (M99). V49 (a merge not in the
log): a replay test (§7.7).

### 8.4 The adversarial gate fixture

Checked against R01 D-20 [R01 §9 D-20]:

| D-20 item | Where in `gate.khg.jsonl` |
|---|---|
| a node in two roles, same direction | `khg:f02-trial`: metformin is `intervention` and `background_therapy` (tail, tail) |
| a node in two roles, tail and head | `khg:f03-regulates`: TP53 is `regulator` (tail) and `target` (head) |
| a repeated role | `khg:f04-coadmin`: two `agent` bindings; `khg:f09-married`: two `partner` bindings |
| an ordered role | `khg:f05-route`: `stop` at positions 0, 1, 2 with YYZ twice |
| typed literals with precision | all eight datatypes: time at day (`khg:f06-louis`) and year (`khg:f07-zurich`, `khg:f09-married`) precision; quantity with a unit (`khg:f01-treats`) and with bounds (`khg:f07-zurich`); decimal, string, lang-string, iri, boolean, integer |
| a nested reference | `khg:f13-reported`: `statement` is `{"hyperedge": "khg:f02-trial"}` |
| direction | core roles of `treats`, all roles of five relations |
| a qualifier | `dose`, `population`, `hba1c_change`, `context`, `flight_number`, `title`, `url`, ... |
| evidence on a binding | `khg:f01-treats` evidence `ev2` has `binding_refs: ["b3"]` (the dose) |
| non-ASCII ids | `x:Zürich`, `x:Zoë`; a German evidence span whose offsets differ in code points, UTF-8 and UTF-16 |
| `somevalue` and `novalue` | `khg:f09-married` (`somevalue` partner); `khg:f10-catalysis` (`novalue` catalyst) |
| an unbound goal slot | `khg:f14-goal` (`status: goal`, treatment `unbound`, expects `Drug`) |
| a superseded pair | `khg:f11-ceo-alice` superseded by `khg:f12-ceo-bob` through `khg:s01` (reason `incorrect`) |
| and, beyond D-20 | an ended fact that is not superseded (`khg:f06-louis`); three key policies; a deprecated rank with a reason; a confidence on a declared LLM scale; an isolated entity with a Cyrillic id (`x:Москва`); a meta relation |

### 8.5 Positive fixtures

`tests/gate/test_positive.py` runs every layer on `gate.khg.jsonl`, `gate.hif.json`, `gate-directed.hif.json`, the
migrated KB sample (container and HIF), the smoke queue, `gate-schema.json` and `cyclic.schema.json`, and requires
zero error findings, under both engines. This is the W3C split: positive syntax, negative syntax, evaluation
[R04 §9.2].

---

## 9. C5 scorers and the C4 item shapes

Scorer version **`khg-scorers/1.0.0`** (versioned with C1, PLAN §7). The P2 gate does not exercise C5, so C5 ships
with every R05 unit-test table as tests (F14; R05 §9 risk 1).

### 9.1 Conventions shared by all scorers [R05 §1]

- **Deterministic, no LLM.** An LLM-judged metric is an adapter with a named judge, pinned prompt and temperature,
  reported under its own name, never merged with C5's numbers [R05 D-C5-13, D-C5-16].
- **Canonical values.** Entities match by id, literals by C1 equality (§2.6); strings enter only answer-text
  metrics, through SQuAD normalisation. Linking is scored separately; C5 does not do mention matching in 1.0 [R05
  D-C5-03].
- **Empty sets written down.** No predictions: P = 0 with flag `no_predictions`; no gold: R = 0 with `no_gold`; both
  empty: P = R = F1 = 1 with `both_empty` [R05 §1 item 3].
- **Three averages.** Micro over units, macro over relation types, macro over arity bins; the denominator is named
  in the output key.
- **Arity bins** from `record["arity"]["arity"]` (§2.7): `0-1`, `2`, `3`, `4`, `5+`. Recall is binned by gold arity,
  precision by predicted arity [R05 §1 item 5].
- **Per-item outputs keyed by stable ids** (fact ids, qids, doc ids), each listing the gold hyperedge ids it depends
  on, so P8 can join the four abilities per fact [R01 C5-R03].
- **Dispersion.** K >= 3 runs where the system is stochastic; a percentile bootstrap over scoring units, 1,000
  resamples, seed 0, 95 %; the paired bootstrap for comparisons [R05 D-C5-18].
- **Version stamp** on every output: `{"c1": "khg-record/1.0.0", "c5": "khg-scorers/1.0.0", "c4": <corpus
  version>, "qset": <question-set version>, "split": ..., "config_sha256": ...}` [R01 C5-R01]. `Versions` is that
  dict. A scorer called with `versions=None` fills `c1`, `c5` and `config_sha256` itself and reads `qset` and
  `split` from the C4 items (every item carries both; mixed values raise); `c4` is then null unless given.
- **One entry point per ability.** Each ability is one module with one function, `score(...)`, in
  `khg_contracts.scorers.{extraction, stability, completion, retrieval, memory}`, and each takes the C4 items and
  the system outputs exactly as P3a and the systems write them: no converter sits between a consumer and C5.
- **Pure Python.** The assignment solver is an in-package Hungarian implementation, cross-checked by brute force in
  tests; SciPy is an optional speed-up; `metametric` has no licence and is not used [R05 D-C5-17].

### 9.2 Extraction and stability

```python
@dataclass(frozen=True)
class ExtractionConfig:
    literal_rule: Literal["truncate_to_gold", "exact"] = "truncate_to_gold"
    use_alternatives: bool = True
    ign_seen: bool = False
    bootstrap: Bootstrap | None = Bootstrap(resamples=1000, seed=0, ci=0.95)

# khg_contracts.scorers.extraction
def score(gold: Iterable[dict], predictions: Iterable[dict], *, schema: Schema,
          config: ExtractionConfig = ExtractionConfig(), versions: Versions | None = None) -> dict
# khg_contracts.scorers.stability
def score(predictions: Iterable[dict], *, gold: Iterable[dict] | None = None,
          keys: tuple[str, ...] = ("content", "core"), versions: Versions | None = None) -> dict
```

`gold` are `c4-extraction-doc` items; `predictions` are C3 queue items of kind `hyperedge`, as `queue_items` yields
them, grouped by `doc.doc` and by run, where a run is the pair `(run.run_id, run.order_id)`. So P9's output is
scored without conversion, and P/R are reported per run and over runs with their dispersion. Predictions are
deduplicated by `keys.content` first and the number removed is reported (the nested-loop pitfall, R05 E6). Metrics
[R05 §2.2]: E-M1 strict fact P/R/F1 (the P9 gate's "precision, recall"); E-M2 core (core-slot bindings,
`keys.core`); E-M3 one 1:1 alignment per document by Hungarian matching with value-first weights and lexicographic
tie-breaks [R05 D-C5-02]; E-M4 argument identification; E-M5 argument classification (binding F1, partial credit
across arity); **E-M6 role accuracy** = TP_C / TP_I (the P9 gate's "role accuracy") [R01 C5-R08]; E-M7 pooled
bindings and the grouping gap; E-M8 pairwise-projection F1; E-M9 participant-set match; E-M10 arity profile; E-M11
the Ign variant over `seen_core_keys`. Literal rule `truncate_to_gold`: a time prediction matches if it is at least
as precise as the gold value and agrees after truncation; a quantity matches inside the gold bounds [R05 D-C5-04].
False positives are split into `contradicts_gold`, `in_kb_not_annotated` and `unknown` when the gold is marked
non-exhaustive [R05 §2.5 item 6]. Soft F1 (E-M12) is 1.1.

Stability [R05 §2.2.2, D-C5-05], on `keys.content` and on `keys.core`: S-M1 mean pairwise Jaccard, S-M2 core
ratio, S-M3 support histogram and unstable fraction, S-M4 fact churn, S-M5 gold-conditioned partition, S-M6 score
dispersion, S-M7 order effect `J_within`, `J_between`, `delta_order` (P9's 3 runs x 2 orders give 6 within-order
and 9 between-order pairs). Runs and orders are read from each item's `run` field, so the same queue items feed both
scorers; `gold` (extraction documents) enables S-M5.

### 9.3 Completion

```python
class FilterIndex:
    @classmethod
    def from_records(cls, *splits: Iterable[dict]) -> "FilterIndex": ...
    def known_answers(self, query: dict, *, mode: Literal["exact", "monotone", "time_aware"] = "exact") -> frozenset[str]: ...

def rank_stats(query: dict, scores: Mapping[str, float], index: FilterIndex, *,
               universe: Iterable[str] | None = None, target_prob: float | None = None,
               top1: tuple[dict, float] | None = None, prob_map: dict | None = None) -> dict

@dataclass(frozen=True)
class CompletionConfig:
    preset: Literal["hype", "stare", "hyper"] | None = None
    rank: Literal["tie_exact", "realistic", "optimistic", "pessimistic", "sort_order"] = "tie_exact"
    filter: Literal["exact", "monotone", "time_aware"] = "exact"
    positions: Literal["all_roles", "subject_object"] = "all_roles"
    ks: tuple[int, ...] = (1, 3, 10)
    calibration_bins: int = 15
    min_bin_queries: int = 100

# khg_contracts.scorers.completion
def score(queries: Iterable[dict], outputs: Iterable[dict], *,
          config: CompletionConfig = CompletionConfig(), versions: Versions | None = None) -> dict
```

The model never hands C5 a score vector; it calls `rank_stats` with C5's filter index and emits
`{qid, n_candidates, n_filtered_out, n_greater, n_equal, target_prob, top1, prob_map}` [R05 D-C5-10]. Filters
compare the other bindings as a set, never a sequence (the ordered-qualifier pitfall of StarE's index)
[R05 D-C5-08]; `monotone` adds known facts with a superset of the query's qualifiers; `time_aware` keeps only facts
valid at the query's `as_of`. Ranks default to the tie-exact expectation (a four-way tie at the top gives
E[RR] = 25/48, not 1/2.5) with the other conventions as an audit [R05 D-C5-06]; MRR, Hits@k and MR are reported per
task, per fact and macro over arity [R05 D-C5-07]; calibration is top-1 ECE with 15 equal-width and 15 equal-mass
bins, Brier and the reliability table, per arity bin, bins under 100 queries suppressed with their counts
[R05 D-C5-09]. Presets reproduce the replicated codebases for P3b's tolerance test [R05 §3.4]: `hype` (all
positions, pessimistic ties, full-tuple filter, per-task average), `stare` (subject and object averaged, sort-order
ties, `(s, r, quals)` filter, universe restricted to entities seen as subject or object), `hyper` (all positions,
pessimistic ties).

### 9.4 Retrieval

```python
@dataclass(frozen=True)
class RetrievalConfig:
    ks: tuple[int, ...] = (1, 3, 5, 10, 20)
    ndcg_discount: Literal["log2(i+1)", "longmemeval"] = "log2(i+1)"
    price_table: str | None = None

# khg_contracts.scorers.retrieval
def score(questions: Iterable[dict], responses: Iterable[dict], *, facts: Iterable[dict],
          config: RetrievalConfig = RetrievalConfig(), versions: Versions | None = None) -> dict
```

A response is `{qid, answer: {values, text, abstained}, retrieved: [{rank, unit_id, unit_kind: hyperedge | pair |
chunk, hyperedge_ids}], support_claimed?, cost: {prompt_tokens, completion_tokens, llm_calls, retrieval_calls,
hyperedges_visited, retrieval_ms, wall_ms, usd?, price_table?}}`. Every unit carries hyperedge back-pointers, so
P4's hyperedge, pair and chunk conditions score on one scale [R05 D-C5-11]. `facts` is any iterable of C1 records (a
container, or `store.iter_records()`); its hyperedges are indexed by id for `binding_coverage@k`. Metrics R-M1 to
R-M12 [R05 §4.2]: hit@k, `support_success@k` (headline, over alternative minimal support sets [R05 D-C5-12]),
support recall, mrr@k (cut-off), R-precision, nDCG with the discount named, support P/R/F1/EM, `binding_coverage@k`
(needs `facts`), answer EM on canonical ids then SQuAD token F1, joint and gated scores, abstention, and cost (mean,
median, p90, p95, total; accuracy against a token budget). Broken down by hops, required-edge arity and source
class. The GraphRAG-Bench adapter (Xiang et al., arXiv id and commit pinned, native names) is 1.1, before P4 opens.

### 9.5 Memory

```python
# khg_contracts.scorers.memory
def score(questions: Iterable[dict], responses: Iterable[dict], *, versions: Versions | None = None,
          lenient: Literal["longmemeval"] = "longmemeval") -> dict
```

Outcomes O1-O7 per item (`current`, `hedged`, `stale` split into `expired` and `retracted`, `anachronistic`,
`wrong`, `abstained`, `correct_abstention`/`hallucinated`) and metrics M-M1 to M-M8 [R05 §5.2, D-C5-14]: strict
accuracy as the headline, lenient beside it (LongMemEval-compatible), stale rate always. The split follows F7:
`expired` values come from facts whose valid time ended (`end_validity`), `retracted` values from facts superseded
or retracted as belief. Text-only systems (P7's flat baseline) are mapped through aliases; an answer naming both
values is `hedged`. A memory trace is a list of C2 `put`/`apply` events with transaction times, so P7 replays it
into any store unchanged, and the question's `as_of`/`as_at` are the `Where` P7 queries with.

### 9.6 The C4 item shapes P3a must produce (draft, `khg-c4-items/0.1.0`)

P3a owns C4; C5 fixes the shapes it reads [R05 D-C5-15]. The draft schema `khg-c4-items-0.1.0.schema.json`
references C1 values and records by the record schema's `$id`, so a C4 file is checked by the same validator
(`I-` codes). Beyond R05's field list [R05 §6], two consumer-driven additions: `anchors` on retrieval questions (the
entity ids the question names, so P10's walker starts without entity linking), and memory events that are literally
C2 `put`/`apply` payloads. Examples built from the gate fixture, each validated against the draft schema
**[validated]**:

Extraction document (its gold fact is the plain C1 record of §2.15):

```json
{
  "kind": "c4-extraction-doc",
  "doc_id": "doc:soc-2024",
  "split": "test",
  "qset": "p3a-extraction/0.1.0",
  "text": "Metformin is the preferred initial pharmacologic agent for the treatment of type 2 diabetes in adults. The usual starting dose is 500 mg once or twice daily.",
  "text_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739",
  "annotation": {"method": "curated", "exhaustive": false, "annotators": 2},
  "gold": [
    {
      "kind": "hyperedge",
      "id": "khg:f01-treats",
      "version": 1,
      "recorded_at": "2026-09-23T10:00:00Z",
      "recorded_by": "p2-gate-fixture/1.0.0",
      "change": {"op": "put"},
      "schema": "p2-gate/1.0.0",
      "relation": "treats",
      "status": "asserted",
      "rank": "normal",
      "visibility": "visible",
      "valid_time": {"from": "2024-01-01"},
      "bindings": [
        {"bid": "b2", "role": "condition", "slot": "core", "direction": "head", "value": {"entity": "disease:T2DM"}},
        {
          "bid": "b3",
          "role": "dose",
          "slot": "qualifier",
          "value": {"datatype": "quantity", "literal": "500", "unit": "wd:Q3241121"}
        },
        {
          "bid": "b5",
          "role": "hba1c_change",
          "slot": "qualifier",
          "value": {"datatype": "decimal", "literal": "-1.12"}
        },
        {"bid": "b4", "role": "population", "slot": "qualifier", "value": {"entity": "pop:adults"}},
        {
          "bid": "b1",
          "role": "treatment",
          "slot": "core",
          "direction": "tail",
          "value": {"entity": "drug:metformin"}
        }
      ],
      "confidence": {"scale": "probability", "value": 0.95},
      "evidence": [
        {
          "eid": "ev1",
          "type": "extracted",
          "mode": "automatic",
          "source": {"doc": "doc:soc-2024", "doc_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739"},
          "selectors": [
            {
              "exact": "Metformin is the preferred initial pharmacologic agent for the treatment of type 2 diabetes in adults.",
              "type": "quote"
            },
            {"end": 102, "start": 0, "type": "position"}
          ],
          "activity": {
            "agent": "p9-extractor/0.1.0",
            "model": "model-y/2026-08",
            "params": {"seed": 13, "temperature": 0},
            "prompt": "treats-skill/1.2.0",
            "run": "r1"
          },
          "confidence": {"scale": "probability", "value": 0.9},
          "event_hash": "sha256:ec92cafb15cde9c2454f34b99581c8a85537289c02a4f27eb1af576a6698fb17"
        },
        {
          "eid": "ev2",
          "type": "curated",
          "mode": "manual",
          "source": {"doc": "doc:soc-2024", "doc_sha256": "90f986112e682299bc5a2818c1ad6422767fa494110e669a35008023faa8e739"},
          "selectors": [
            {"exact": "The usual starting dose is 500 mg", "type": "quote"},
            {"end": 136, "start": 103, "type": "position"}
          ],
          "activity": {"agent": "curator:reviewer-1"},
          "binding_refs": ["b3"]
        }
      ],
      "arity": {"arity": 5, "core": 2, "participants": 5},
      "keys": {
        "content": "sha256:09c8cc13dc74f8c3f6f2db9d3bdff24860523db953aeb713dc80eb6e1d1dc6d7",
        "core": "sha256:55449857f34d1a8a27ef8c72d6117c4a882cc055e83a3b572db6f7e0f0966b57"
      }
    }
  ],
  "entity_aliases": {"drug:metformin": ["Metformin"]},
  "seen_core_keys": []
}
```

Completion query:

```json
{
  "kind": "c4-completion-query",
  "qid": "p3a:cq-000001",
  "split": "test",
  "qset": "p3a-completion/0.1.0",
  "fact_id": "khg:f02-trial",
  "relation": "compared_in_trial",
  "arity": 4,
  "target": {"bid": "b3", "role": "comparator", "slot": "core", "direction": "tail", "value": {"entity": "drug:insulin"}},
  "context": [
    {
      "bid": "b2",
      "role": "background_therapy",
      "slot": "core",
      "direction": "tail",
      "value": {"entity": "drug:metformin"}
    },
    {
      "bid": "b1",
      "role": "intervention",
      "slot": "core",
      "direction": "tail",
      "value": {"entity": "drug:metformin"}
    },
    {"bid": "b4", "role": "outcome", "slot": "core", "direction": "head", "value": {"entity": "outcome:HbA1c"}}
  ],
  "candidate_universe": "all_entities",
  "as_of": null,
  "inductive": {"unseen_context_entities": 0, "unseen_relation": false}
}
```

Retrieval question (two hops, with anchors):

```json
{
  "kind": "c4-retrieval-question",
  "qid": "p3a:rq-000001",
  "qset": "p3a-retrieval/0.1.0",
  "split": "test",
  "type": "retrieval_qa",
  "text": "Which drug was the comparator in the trial described in the 1998 trial report?",
  "template_id": "reported_in>compared_in_trial/comparator/v1",
  "anchors": ["doc:trial-report-1998"],
  "answer": {"mode": "single", "values": [{"entity": "drug:insulin"}]},
  "aliases": {"drug:insulin": ["insulin"]},
  "support": {"sets": [["khg:f13-reported", "khg:f02-trial"]]},
  "required_edge": {"fact_id": "khg:f02-trial", "relation": "compared_in_trial", "arity": 4},
  "hops": 2,
  "source_class": "n-ary",
  "as_of": null,
  "answerable": true,
  "provenance": {"generator": "template", "generator_version": "0.1.0", "verified": "none"}
}
```

Memory trace (C2 events):

```json
{
  "kind": "c4-memory-trace",
  "trace_id": "p3a:mt-000001",
  "qset": "p3a-memory/0.1.0",
  "split": "test",
  "events": [
    {
      "step": 1,
      "tx_time": "2026-01-10T09:00:00Z",
      "text": "Acme announced that Alice is its chief executive from 1 January 2019.",
      "put": {
        "kind": "hyperedge",
        "id": "khg:f11-ceo-alice",
        "schema": "p2-gate/1.0.0",
        "relation": "chief_executive",
        "status": "asserted",
        "rank": "normal",
        "visibility": "visible",
        "valid_time": {"from": "2019-01-01"},
        "bindings": [
          {"bid": "b1", "role": "organisation", "direction": "tail", "value": {"entity": "org:Acme"}},
          {"bid": "b2", "role": "person", "direction": "head", "value": {"entity": "x:Alice"}}
        ],
        "evidence": [
          {
            "eid": "ev1",
            "type": "curated",
            "mode": "manual",
            "source": {"doc": "doc:acme-pr-2019"},
            "activity": {"agent": "curator:reviewer-1"}
          }
        ]
      }
    },
    {
      "step": 2,
      "tx_time": "2026-02-02T09:00:00Z",
      "text": "Acme corrected its 2019 announcement: the chief executive since 1 January 2019 is Bob.",
      "apply": {
        "op": "supersede",
        "id": "khg:s01",
        "superseded": ["khg:f11-ceo-alice"],
        "record": {
          "kind": "hyperedge",
          "id": "khg:f12-ceo-bob",
          "schema": "p2-gate/1.0.0",
          "relation": "chief_executive",
          "status": "asserted",
          "rank": "normal",
          "visibility": "visible",
          "valid_time": {"from": "2019-01-01"},
          "bindings": [
            {"bid": "b1", "role": "organisation", "direction": "tail", "value": {"entity": "org:Acme"}},
            {"bid": "b2", "role": "person", "direction": "head", "value": {"entity": "x:Bob"}}
          ],
          "evidence": [
            {
              "eid": "ev1",
              "type": "curated",
              "mode": "manual",
              "source": {"doc": "doc:acme-pr-2021"},
              "activity": {"agent": "curator:reviewer-1"}
            }
          ]
        },
        "reason": "incorrect",
        "evidence": [
          {
            "eid": "ev1",
            "type": "curated",
            "mode": "manual",
            "source": {"doc": "doc:acme-pr-2021"},
            "activity": {"agent": "curator:reviewer-1"}
          }
        ]
      }
    }
  ]
}
```

Memory question:

```json
{
  "kind": "c4-memory-question",
  "qid": "p3a:mq-000001",
  "trace_id": "p3a:mt-000001",
  "qset": "p3a-memory/0.1.0",
  "split": "test",
  "ask_after_step": 2,
  "subtype": "current_value",
  "text": "Who is the chief executive of Acme?",
  "as_of": "end_of_trace",
  "as_at": "after_step",
  "key": {
    "relation": "chief_executive",
    "key": [{"role": "organisation", "value": {"entity": "org:Acme"}}],
    "target_role": "person"
  },
  "answer": {"mode": "single", "values": [{"entity": "x:Bob"}]},
  "stale_values": [{"value": {"entity": "x:Alice"}, "fact_id": "khg:f11-ceo-alice", "kind": "retracted"}],
  "future_values": [],
  "support": {"current": ["khg:f12-ceo-bob"], "history": ["khg:f11-ceo-alice", "khg:s01"]},
  "aliases": {"x:Bob": ["Bob"], "x:Alice": ["Alice"]},
  "answerable": true,
  "tolerance": null,
  "keyed_relation_arity": 2,
  "n_supersessions_on_key": 1
}
```

System output shapes (not C4, but the other half of the scorer contract): extraction predictions are C3 queue
files; completion outputs are `rank_stats` records; retrieval and memory responses are as in §9.4 and §9.5. Each
output record carries the `qid` or `doc_id` of the item it answers.

### 9.7 The unit-test tables that ship

`tests/scorers/test_extraction.py`, `test_stability.py`, `test_completion.py`, `test_retrieval.py`,
`test_memory.py`, with the expected values literal in `tests/fixtures/scorers/*.json`: every case of R05 §2.7,
§3.7, §4.7 and §5.7, which is the 46 entries of `research/probes/scorers/c5_reference_cases.out.json` (E1-E11 with
E5b, E5c and the nested-loop pitfall E6; S1-S4; C1-C8 with raw/filtered and both filter variants; R1-R8; M1-M8 with
M4a/M4b). The values were computed by hand in R05 and recomputed by the probe; the tests assert them to 1e-6. Two
more: the Hungarian solver against brute force on random 6x6 matrices, and determinism of every scorer output
(identical JSON on two runs and under four hash seeds).

---

## 10. Package layout

Distribution **`khg-contracts`**, import **`khg_contracts`**, `pyproject.toml` at the repository root, code in
`src/khg_contracts/`, tests in `tests/`, Python >= 3.10, MIT (F12). Build backend hatchling, with the sdist limited
to `src/`, `tests/`, `LICENSE` and the package README so the KB content is not shipped.

```
src/khg_contracts/
  __init__.py            public API; __version__ = "1.0.0"; format ids re-exported
  formats.py             RECORD = "khg-record/1.0.0", SCHEMA_LANG, HIF_PROFILE, ROLES_CONVENTION, QUEUE,
                         STORE = "khg-store/1.0.0", SCORERS, SCENARIOS, C4_ITEMS
  jsonio.py              L0 strict JSON; canonical dumps; read_container, parse_container, write_container
  ids.py                 id grammar, reserved namespaces, foreign id mapping
  record/
    values.py            literal canonical forms and equality; time bounds, lower_instant, next_period, julian
    keys.py              content_key, core_key, key_digest, event_hash, literal_node_id
    normalize.py         normalize(record, schema)
    arity.py             arity(record)
    render.py            render_text(record, labels), entity_ids(records)
    project.py           positional, hyper_relational, role_value_set
    container.py         Container, compare_containers(a, b) -> list[Difference]
  schema/
    language.py          load_schema, Schema (usages, type closure, key roles, time model), SchemaInvalid
    hypergraph.py        schema_hypergraph(schema, slots=...)
  validate/
    __init__.py          validate_container, validate_record, validate_hif, validate_schema, validate_queue,
                         validate_item; Report, Finding
    layers.py            L0-L3 orchestration; engine choice; x-khg-code mapping
    semantic.py          L3 checks
    codes.py             the code registry
  schemas/               package data, draft-07: hif_schema_v0.1.0.json (vendored: blob e2105bb, sha256
                         639466b7..., DOI 10.5281/zenodo.17257719, upstream MIT licence text), khg-record-1.0.0,
                         khg-relation-schema-1.0.0, khg-hif-1.0.0, khg-queue-1.0.0, khg-c4-items-0.1.0,
                         khg-store-scenario-1.0.0; VENDORED.md with provenance
  hif/
    codec.py             to_hif, from_hif, canonical_hif
    foreign.py           import_foreign(doc, mapping)
    diff.py              structural HIF diff (from research/probes/probe_common.py)
  loaders/
    context.py           HifContext, reconcile, ExportReport, StaleIncidences, UnlabelledMemberships
    xgi_loader.py        load_xgi, LoadedXGI                        [extra: xgi]
    hnx_loader.py        load_hnx, LoadedHNX                        [extra: hypernetx]
  store/
    protocol.py          Store, Where, DEFAULT, PutResult, LoadReport, Walk, errors, CAPABILITIES
    base.py              StoreBase: the seven derived methods
    memory.py            MemoryStore
    timing.py            Timed
    conformance/runner.py, scenarios/*.json, pytest_plugin.py   (--khg-store=module:factory)
  queue/
    queue.py             Queue (append-only JSONL, state machine), queue_items
    lint.py              Linter and rules
    ops.py               make_candidate, accept, reject, flag, merge, verdict, replay
  scorers/
    common.py            prf, bins, bootstrap, hungarian, literal_match, Versions
    extraction.py  stability.py  completion.py  retrieval.py  memory.py
  migrate/
    registry.py          MIGRATIONS: {(from_major, to_major): function}
    legacy_hif.py        legacy and foreign HIF -> C1 with a mapping file
  cli.py
tests/
  conftest.py            socket guard (no network), fixture loader, hash-seed helper
  fixtures/gate/         gate-schema.json, gate.khg.jsonl, gate.hif.json, gate-directed.hif.json,
                         sample-mapping.json, sample-migrated.khg.jsonl, smoke-expected.json
  fixtures/malformed/    INDEX.json + M01..M99, Q01..Q10 input files
  fixtures/schemas/      cyclic.schema.json, minimal.schema.json
  fixtures/scorers/      extraction.json, stability.json, completion.json, retrieval.json, memory.json
  gate/                  test_roundtrip.py (G1), test_malformed.py + test_positive.py (G2), test_smoke.py (G3)
  evidence/              test_library_hif_functions.py (marker "evidence"; F1)
  unit/                  values, keys, normalize, arity, render/project, schema language, hypergraph, codec,
                         foreign import, loaders and native operations, queue, lint, migrate, codes registry
  conformance/           test_memory_store.py: every scenario against MemoryStore
  scorers/               the R05 tables (§9.7)
```

**Public API** (`from khg_contracts import ...`): `read_container`, `parse_container`, `write_container`,
`compare_containers`, `normalize`, `arity`, `render_text`, `entity_ids`, `load_schema`, `schema_hypergraph`,
`validate_container`, `validate_record`, `validate_hif`, `validate_schema`, `validate_queue`, `validate_item`,
`to_hif`, `from_hif`, `import_foreign`; submodules `khg_contracts.record` (`project`), `.loaders`, `.store`,
`.queue`, `.scorers`, `.migrate`. §1.4 lists the imports each consumer needs.

**Dependencies.** Core: `jsonschema>=4.18` (for the `referencing` registry that resolves the vendored HIF schema
offline). Extras: `xgi = ["xgi==0.10.2"]`; `hypernetx = ["hypernetx==2.4.3", "pandas>=2,<3", "fastjsonschema"]`
(HyperNetX imports fastjsonschema without declaring it [R03 Sources, HNX #173]); `fast =
["fastjsonschema==2.22.2"]`; `scipy = ["scipy>=1.11"]`; `test = ["pytest>=8"]`. Pins move only with a re-run of
R03's probe suite [R03 D10].

**CLI entry points.**

| Command | Does |
|---|---|
| `khg-validate PATH [--kind auto\|container\|hif\|schema\|queue\|c4] [--schema S] [--engine jsonschema\|fastjsonschema] [--json]` | all layers; exit 1 on any error; findings as text or JSON |
| `khg-convert IN OUT [--to hif\|khg] [--relations r1,r2] [--network-type auto\|directed\|undirected]` | C1 <-> HIF (profile files) |
| `khg-normalize IN OUT --schema S` | fills derived fields of hand-written records |
| `khg-migrate legacy-hif IN --mapping M [--weight-as-confidence SCALE] -o OUT`; `khg-migrate record --to 2 IN -o OUT` | §11 |
| `khg-lint QUEUE --schema S [--store CONTAINER] [--doc-text DIR]` | lints pending items and appends log entries |
| `khg-conformance --store module:factory [--report OUT]` | the C2 suite; EARL-shaped JSON |
| `khg-score {extraction\|stability\|completion\|retrieval\|memory} ...` | C5 on files |

**Tests mapped to the gate, and CI.**

```bash
python -m pip install -e ".[xgi,hypernetx,fast,test]"
python -m pytest -q tests/gate                       # the P2 gate: G1, G2, G3
python -m pytest -q -m "not evidence" tests          # everything else, offline
python -m pytest -q -m evidence tests/evidence       # the F1 library-evidence test, offline
khg-validate tests/fixtures/gate/gate.khg.jsonl && khg-validate tests/fixtures/gate/gate.hif.json
```

CI matrix: Python 3.10 to 3.13 with all extras; plus one job with the core only (no extras), where loader tests are
skipped by `importorskip`, which proves the core carries no heavy dependency.

---

## 11. Versioning and migration

### 11.1 Identifiers

| Id | What | Versioned how |
|---|---|---|
| `khg-record/1.0.0` | C1 records and containers | semver; C3 and C5 bump with it (PLAN §7) |
| `khg-relation-schema/1.0.0` | the schema language | with C1 |
| `khg-queue/1.0.0` | C3 | with C1 |
| `khg-scorers/1.0.0` | C5 | with C1 |
| `khg-store/1.0.0` | the C2 interface | its own semver (PLAN §7: "interface version") |
| `khg-store-scenario/1.0.0` | conformance scenario files | with C2 |
| `khg-hif/1.0.0` | the HIF profile | its own semver; major follows C1's major |
| `roles-convention` `1.0.0` | the generic HIF convention | its own semver, upstream-facing |
| `khg-c4-items/0.1.0` | the C4 draft shapes | handed to P3a, who owns C4 |
| `<schema id>/<semver>` | each relation-type schema document | the domain owner's semver; every record cites the version it was typed under |

The package version equals the C1 version (1.0.0), so "each project records the contract versions it consumed"
(PLAN §7) is one string plus the store interface version.

### 11.2 Semver rules

- **Patch:** documentation; validator fixes that reject only what the text already forbade (listed in the
  changelog).
- **Minor** (a 1.m reader reads every 1.k file, k <= m): new optional fields, new enum values (statuses, datatypes,
  special values, evidence types, event ops, item kinds), new record kinds, new store methods with defaults, new
  scenarios, new scorers or metrics. A 1.k validator may reject a 1.m file with new fields; consumers pin.
- **Major:** anything that changes meaning or a hash: removing or renaming a field, changing canonicalisation or any
  hash input (content keys change, so dedup and leak reports change), the arity rule, the `Where` defaults, the time
  comparison rule, the transition table.

### 11.3 Migration policy

Every major ships `khg_contracts/migrate/<n>_to_<n+1>.py`, a pure function over containers, queue files and schema
documents that keeps history (versions and transaction times stay), recomputes derived fields and keys, and writes a
header with the new `format` plus `migrated_from`. Each migration has golden input and output files in its tests.
PLAN §7: the consumers' gates are rerun on every contract change; the status board records the versions. Minor
versions need no migration.

### 11.4 Migrating the KB's `schemas/sample.hif.json`

The sample is legacy HIF: `attrs.role` strings with no declaration, confidence carried in `edges[].weight`, an
`arity` edge attr, `source` and `valid-from` edge attrs, a moving schema URL in metadata, and edge ids `f1`..`f3`
that are not C1 ids. `khg-migrate legacy-hif schemas/sample.hif.json --mapping sample-mapping.json` uses the foreign
importer (§4.5) with this mapping **[validated]**:

```json
{
  "schema_id": "kb-sample",
  "schema_version": "1.0.0",
  "edge_namespace": "kb-sample",
  "slots": {
    "treatment": "core",
    "condition": "core",
    "dosage": "qualifier",
    "population": "qualifier",
    "agent": "core",
    "effect": "core",
    "publisher": "core",
    "publication": "core"
  },
  "edge_attrs": {
    "relation": "relation",
    "arity": "check-and-drop",
    "source": "evidence.source.doc",
    "valid-from": "valid_time.from"
  },
  "weight": "drop",
  "evidence_default": {"type": "curated", "mode": "manual", "activity": {"agent": "kb-author"}}
}
```

Result: 13 container lines (header, a generated schema `kb-sample/1.0.0` with three relations, 8 entities, 3
hyperedges); roles and directions unchanged (the sample already writes one role per record, so the convention
needs only its declaration); the legacy `arity` agrees with the C1 rule on all three facts and is dropped; the three
weights 0.95, 0.80 and 1.0 are dropped and reported, because weight has no defined meaning in HIF, and become
`confidence {value, scale: "probability"}` only when the operator passes `--weight-as-confidence probability`; the
metadata's moving schema URL is replaced by the pinned declaration. The migrated HIF validates against the vendored
schema and the profile, is `directed` (every sample incidence has a direction), and imports back exactly. One
migrated fact:

```json
{
  "kind": "hyperedge",
  "id": "kb-sample:f1",
  "version": 1,
  "recorded_at": "2026-09-19T00:00:00Z",
  "recorded_by": "khg-migrate/1.0.0",
  "change": {"op": "put", "reason": "migrated from legacy HIF"},
  "schema": "kb-sample/1.0.0",
  "relation": "treats",
  "status": "asserted",
  "rank": "normal",
  "visibility": "visible",
  "valid_time": {"from": "2024-01-01"},
  "bindings": [
    {"bid": "b2", "role": "condition", "slot": "core", "direction": "head", "value": {"entity": "disease:T2DM"}},
    {"bid": "b3", "role": "dosage", "slot": "qualifier", "direction": "tail", "value": {"entity": "dose:500mg-bid"}},
    {"bid": "b4", "role": "population", "slot": "qualifier", "direction": "tail", "value": {"entity": "pop:adults"}},
    {"bid": "b1", "role": "treatment", "slot": "core", "direction": "tail", "value": {"entity": "drug:metformin"}}
  ],
  "evidence": [
    {
      "eid": "ev1",
      "type": "curated",
      "mode": "manual",
      "source": {"doc": "doc:guideline-2024"},
      "activity": {"agent": "kb-author"}
    }
  ],
  "arity": {"arity": 4, "core": 2, "participants": 4},
  "keys": {
    "content": "sha256:ef01bb9ac4c0e4871f6b7d7e1e91709df32d0deefebce31ee1d96bc66d127aac",
    "core": "sha256:55449857f34d1a8a27ef8c72d6117c4a882cc055e83a3b572db6f7e0f0966b57"
  }
}
```

---

## 12. v1 scope, later versions, and the upstream proposals

### 12.1 What 1.0 contains, by consumer gate (F13)

| Gate | What in 1.0 serves it |
|---|---|
| P2 | C1, schema language, HIF codec and profile, loaders, validator with 96 cases, reference store, queue and linter, smoke test |
| P1 | the C2 Protocol, `StoreBase`, `MemoryStore`, capability flags, `load`/`export`, `compare_containers`, `Timed`, the scenario suite and runner, the backend mapping table (§6.8) |
| P3a | C1 with the Wikidata mapping (datatypes, precisions, calendars, ranks, references, special values, time qualifiers), `normalize`, the four identifiers, `arity`, the C4 draft shapes and `validate_item` |
| P3b | `FilterIndex`, `rank_stats`, the completion scorer with presets and calibration by arity, `project.positional`/`hyper_relational` |
| P5 | `to_hif` with slices, `load_xgi`, `load_hnx`, `roles()`, labels in node attrs |
| P6 | the schema language and `schema_hypergraph`, the cyclic fixture |
| P7 | keys and policies, `find_by_key`, the four events, `supersession_walk`, `as_of`/`as_at`, `render_text`, the memory scorer, memory traces as C2 events |
| P9 | the queue, `make_candidate`, the linter, the extraction and stability scorers, `khg-validate` on queue files |
| P10 | `incident`, `degree`, `get_many`, `Where`, id order, `render_text`, the retrieval scorer with cost |

### 12.2 Later versions

| Item | Version | Needed by | Why not in 1.0 |
|---|---|---|---|
| `bind` event, `unbound_slots()` query, binding-proposal queue items | 1.1 | P11 (phase 3) | goals and `unbound` are already representable and storable; the workflow is P11's |
| pairwise projection with back-pointers; GraphRAG-Bench adapter | 1.1 | P4 (phase 2) | not a phase-1 gate [R01 C1-R59] |
| LongMemEval KU and LoCoMo adapters (run in place, native names) | 1.1 | P7 (optional), P8 | P7's gate uses P3a's set [R05 D-C5-16] |
| per-binding validity intervals | 1.1 | P7, if it tests [07.10] | nothing found attaches intervals below the hyperedge [R01 C1-R48]; option ii of case 4a works in 1.0 |
| valid-time uncertainty bounds (`valid_from_bounds`, `valid_to_bounds`) | 1.1 | P3a, P7 | carried as `meta` bindings in 1.0 [R04 M4] |
| entity versioning, `redirect` event, entity merge | 1.1 | P9, P7 | entities are immutable in 1.0 [R01 C2-R20, MAY] |
| corpus quality lints; `must_agree`; the rule tail/head lint | 1.1 | P9, P3a | non-blocking [R01 C3-R09, C1-R34, V39] |
| TypeQL, SQL, SHACL 1.2, LinkML generators | 1.1 | P1 (helpful) | P1 maps by hand for its gate [R01 C1-R33] |
| XGI edge-attr mirror of records (survives `<<`) | 1.1 | if a consumer renumbers | the side table is enough for the gate [R03 D1] |
| soft F1 (E-M12), adjusted ranks (C-M6), per-candidate calibration (C-M8), mention mapping, HyperRED preset | 1.1 | P9, P3b, P8 | optional in R05 |
| an `attributed` (recorded, not endorsed) status; a withheld (tombstoned) special value; per-field suppression | 1.1 | governance, P1's RDF non-asserted claims | open questions [R01 C1-R44, C1-R10; OQ 10.6] |
| globe coordinates and other Wikidata datatypes | 1.1 | P3a | counted and skipped in 1.0 |
| a different time-bound reading, a different arity rule | 2.0, only if P3a or P7 show the need | P3a, P7 | these change keys and bins |
| a structural HIF role field and a data-file version marker | `khg-hif/2.0.0`, after upstream adopts them | the HIF proposal | F15 |

### 12.3 The HIF proposal (issue first, F15)

Filed as an issue on `HIF-org/HIF-standard`, the first by someone outside the author group [R02 §9]:

1. **Title:** "A v1-compatible `role` convention for incidence attributes (no schema change)".
2. **Motivation.** The paper's own example of an incidence attribute is a role, `{"edge": 1, "node": 3, "attrs":
   {"role": "PI"}}` (p.7), and the upstream compliant test `single_incidence_with_attrs.json` uses the same key; no
   convention says what it means, how a file declares it, or how a node plays two roles [R02 §3, §6].
3. **The convention, five rules.** (R1) An incidence's role is `attrs.role`, a non-empty string. (R2) A node that
   plays several roles in one edge has one incidence record per role; records of one (edge, node) pair may differ in
   `direction`, which is how a node is in both tail and head, as §2 of the paper allows. (R3) An edge may carry
   `attrs.relation`. (R4) A file declares `metadata["roles-convention"] = "1.0.0"` and may add
   `metadata["roles-vocabulary"]` (`{role: {label, description?}}`); when it does, every role is a key of it. (R5)
   Readers keep every incidence record, including repeated pairs and unknown attrs; writers never invent weights
   or defaults.
4. **Compliant fixtures** (all valid under `hif_schema.json` unchanged): basic roles; two roles of one node in one
   direction; one node as tail and head; a vocabulary declaration. They are the loader probe's c05 and c06 plus the
   KB sample with its declaration added [R03 §0.3].
5. **What libraries do today** (§5.6 and R03 §3): XGI keeps no incidence attrs; HyperNetX keeps the first record of
   a repeated pair, and cannot write a file where only some incidences have a direction.
6. **v2 requests, offered separately:** a structural per-incidence `role` field that generalises `direction`, with
   a statement that incidences form a multiset; a data-file version marker (for example a top-level `hif-version`).
   Cited: #44 (attribute-first temporal extension), #21 ("structural information ... metadata in `attrs`"), #51 and
   #55 (v2 planning), the paper's §3.2 (validation is the libraries' job) [R02 §8, §9].
7. **Offer:** a follow-up pull request limited to README text and the fixtures, the kind the core team has merged
   quickly [R02 §8].

### 12.4 Issues for XGI and HyperNetX [R03 §7.5, D12]

**XGI** (`convert/hif_dict.py`): read and write incidence `attrs` and every `weight` (for example an incidence
mapping returned beside `H`); raise a clear error for a missing or invalid `direction` in directed files (today
`KeyError`, and `"treatment"` becomes head); stop splatting attrs into `add_node`/`add_edge` (`TypeError` on an attr
named `node` or `members`); copy `_net_attr` in the `SimplicialComplex` conversion; write in a deterministic order;
document that repeated (edge, node) incidences collapse.

**HyperNetX** (`hif.py`): vendor the schema or allow skipping validation (#171); raise the `HyperNetXError` it
constructs instead of returning `None`; keep all `metadata`; fix `to_hif(metadata=dict)` (`metadata =
metadata.update(...)`); stop writing `default_attrs.incidences.direction: null` or reading it back as a column
default (second-generation directed files); drop `fillna("nil")`, which also breaks every mixed-direction file
(**new**, §5.6); export isolated nodes and empty edges; read `network-type`; honour `aggregate_by` or document that
duplicate cells are dropped; handle `{"incidences": []}`; close files; declare `fastjsonschema` (#173).

---

## 13. Decisions log

Every contested decision from the reports, with the choice, what was rejected, and the evidence. "C-nn" are this
design's own decisions.

| Id | Decision | Choice | Rejected | Evidence |
|---|---|---|---|---|
| R01 D-01, R03 D2, R04 O2 | roles in HIF; a node with several roles | `incidences[].attrs.role`, one string per record; one record per binding; repeated (edge, node) pairs legal when role or position differ | one record per pair with a `roles` list (R01); role-keyed bindings converted to a list (R04); namespaced key; edge-level role map | c06 (tail + head) is inexpressible with one record per pair [R03 §8]; paper example and upstream test [R02 §3]; 4 of 4 chains exact [validated]; F5 removes the draft-07 motive for role-keyed bindings |
| R01 D-02 | declaring versions | `metadata`: `roles-convention`, `khg-profile`, `hif-schema` (commit-pinned), `hif-schema-sha256`, `hif-schema-doi` | top-level keys (invalid HIF); relying on the schema URL | R02 §5 cases 04-07, §4.4; F2, F3 |
| R01 D-03, R04 O12 | slot classes | four (`core`, `qualifier`, `time`, `meta`) on usages; one binding list | one class; two classes; a separate qualifier list | R04 §8.2 (meta qualifiers dominate P6's attributes); P3a, P3b, P7 needs [R01 §1] |
| R01 D-04, R04 O1 | role identity | global ids with per-relation usages (F4); main-snak naming left to P3a and P6 | relation-local roles | local roles make P6 trivial [R04 §8.2]; naming does not change alpha-acyclicity [R04 §8.2] |
| R01 D-05, R04 M3 | identity | four identifiers with exact hash inputs, content hash in two scopes, domain-separated | text as id, member-set keys, name + type keys | F6; INDRA and Wikibase precedent [R04 §3.1]; R01 §6 identity cases |
| R01 D-06 | arity | bindings in core/qualifier/time with entity, literal, hyperedge or somevalue values; `participants` and `core` beside it | distinct participants only; core only; positions | R01 D-06; the KB sample agrees 3 of 3 [validated]; benchmark statistics count qualifier values |
| R01 D-07, R04 M4 | time | bitemporal on the hyperedge; time bindings are the source, `valid_time` derived; point in time -> precision-wide interval; a bound is its first instant; tx end derived | time only as qualifiers; only as fields; per-binding validity in 1.0 | R04 M4 (SQL:2011, Datomic, Graphiti's in-place flaw); R01 C1-R47 |
| R01 D-08, R04 O4 | lifecycle | four axes (F7); statuses candidate/asserted/disputed/superseded/retracted/goal; transition table; events | one status field | R04 M5 (Wikidata's three-way distinction) |
| R01 D-09 | literals | inline typed values in C1; value-shared `khg-lit:` nodes in HIF; never incident in C2 | one literal node per binding; literal on the incidence | HIF needs a node per incidence [R01 PF-09]; C2 walkers never walk literals |
| R01 D-10, R04 O5 | supersession carrier | its own record kind, one per pair, plus the `superseded_by` pointer (F8) | a meta hyperedge (pollutes `incident` and arity, needs nesting in every backend); a field only; closing intervals only | R04 M5 (nanopub, PROV); P1's backends (§6.8) |
| R01 D-11 | nesting depth | unbounded and acyclic; one level in gate and suite | flat; one level | R01 D-11 |
| R01 D-12 | direction | on the binding, fixed by the role usage in 1.0; `directed` iff every incidence has one; always written | free per-binding direction; dropping direction in undirected files | R02 §3.2, case 24; R03 §3 rows 6-8 |
| R01 D-13, R03 D6 | confidence and weight | `{value, scale, method?}` on facts and evidence; `weight` never written, never read as confidence | weight as confidence | R03 §3 rows 9-11 (XGI drops, HNX invents and sums) |
| R01 D-14, R04 O7 | evidence | a list per fact, `binding_refs`, ECO-mapped `type`, EARL `mode`, F11 selectors, reference snaks, `fragment` | a source field; full ECO ids; nanopub graphs | R04 M6 |
| R01 D-15, R04 O10 | schema syntax | own JSON, LinkML-shaped, draft-07 meta-schema; generators in 1.1 | LinkML itself; SHACL; TypeQL as source | R04 M8 (dependencies, missing temporal keys) |
| R01 D-16 | store defaults | `at_least` matching; status asserted; rank preferred/normal; visible; **no valid-time filter**; latest versions; id order | as-of "now" by default | a now-filter hides every historical fact P10 and P3a need |
| R01 D-17 | erasure | not in 1.0; suppression only; tombstone value in 1.1 | deleting facts or incidences | OQ 10.6 open [R01 PF-14] |
| R01 D-18 | queue | a separate append-only JSONL of items and log entries (F9); an all-unbound goal is an edge without incidences | candidates in the store | R01 D-18; R04 M7 |
| R01 D-19, R03 D3 | loader strategy | public constructors plus a context; library HIF functions only in the evidence test (F1) | patching library readers | R03 §3, §4 |
| R01 D-20 | gate fixture | adversarial, §8.4 | a minimal record | R01 D-20 |
| R01 D-21, R05 D-C5-01/02 | extraction matching | strict facts; bindings under one Hungarian alignment with value-first weights; role accuracy TP_C/TP_I | greedy; role-weighted alignment | R05 §2.5 items 4-5, E8 |
| R01 D-22 | scope | phase-1 gates (F13); later list §12.2 | everything at once | PLAN §7 "versioned, not frozen" |
| R03 D1 | XGI records | side table bundled with `H` (A) | records in edge attrs (B, 1.1); node->roles maps (C: integer keys become strings) | R03 §7.4 |
| R03 D4 | directed file, missing or bad direction | reject (M21, M10) | defaulting | R03 X4 |
| R03 D5 | duplicate node or edge declarations | reject (M24) | a library's merge rule | R03 c19 |
| R03 D7 | `default_attrs`, `name` | forbid `default_attrs` (M19); never write `name` | allow | R03 c20 |
| R03 D8 | `asc` | reject (M13) | load as simplicial complex | R03 c04 |
| R03 D9 | native operations | safe / reported / unsafe classes; strict export | allow all silently | R03 §5, §7.4 |
| R03 D10 | dependencies | optional pinned extras; core `jsonschema` only | hard dependencies | R03 D10; F12 |
| R03 D11 | output order | canonical order; structural comparison; byte determinism of our own output across hash seeds | library order | R03 §4.1 |
| R03 D12, F15 | upstream | issues first (§12.3, §12.4); gate independent | pull requests first | R02 §8 |
| R04 O3 | key declaration | roles + temporal + policy; five policies (`close_older` split from `supersede` per F7); the store always raises | roles only; silent resolution | R04 §3.3 (four deployed semantics) |
| R04 O6 | versioning | immutable versions; tx end derived | in-place updates | R04 M4 (Graphiti cannot answer as-at) |
| R04 O8 | spans | code points, NFC, half-open, doc hash, quote + position (F11) | UTF-16, inclusive ends | R04 M6 |
| R04 O9 | verdict unit | (candidate, evidence) keyed by `(keys.core, event_hash)` | per candidate | R04 M7 (INDRA) |
| R04 O11 | JSON Schema dialect | draft-07, jsonschema default, fastjsonschema fast path | 2020-12 | F5; R04 §8.1 |
| R04 O13 | conformance format | declarative scenarios, capability gating, EARL-shaped report | code-only tests | R04 §9.2 |
| R05 D-C5-03 | entity matching | canonical ids; mention mapping in 1.1 | string matching | R05 §2.1.4 |
| R05 D-C5-04 | literal equality in scoring | `truncate_to_gold`, `exact` preset | partial credit | R05 E9 |
| R05 D-C5-05 | stability | S-M1..S-M7 on both keys | run-1 anchor only | R05 §2.1.5 |
| R05 D-C5-06/07 | ranks, denominators | tie-exact expectation; three denominators; presets | one convention | R05 C3, C4 |
| R05 D-C5-08 | filters | exact default, monotone and time-aware reported, set equality | sequence equality | R05 §3.1.2 |
| R05 D-C5-09/10 | calibration; model interface | top-1 ECE, both binnings, Brier, per arity; rank statistics | per-triple only; score vectors | R05 §3.1.4, §3.3 |
| R05 D-C5-11/12 | retrieval units; support | back-pointers, `binding_coverage@k`; alternative minimal sets, `support_success@k` | KILT recall as headline | R05 R1, R2 |
| R05 D-C5-13/14 | answers; memory outcomes | structured answers; O1-O7, strict headline, stale split by F7 | LLM judge as headline | R05 §5.1 |
| R05 D-C5-15 | question-set shapes | `khg-c4-items/0.1.0` with `anchors` and C2-event traces | free-form items | §9.6 |
| R05 D-C5-16/17/18 | adapters; solver; dispersion | 1.1 in place; pure Python Hungarian; bootstrap 1000, seed 0 | vendoring; metametric | R05 §7 |
| C-01 | repo format | JSONL container with header and schema records | one JSON document; HIF as the repo format (no history, no schema) | R01 PF-28 |
| C-02 | special values in HIF | no incidence; `khg-special-bindings` on the edge | blank nodes per `somevalue` | no invented ids, no value-sharing hazards |
| C-03 | profile attr keys | flat `khg-*` keys by one mechanical rule; generic `relation`, `role`, `label` | one nested `khg` object (not filterable in XGI) | R02 §3 (dash-case advice) |
| C-04 | id space | `ns:local`, IRI-safe, NFC, unique across kinds, reserved namespaces | per-kind id spaces | `incident()` needs no kind argument |
| C-05 | derived fields | materialised by `normalize()` and checked | computed on demand by each consumer | every consumer would need the schema and the code |
| C-06 | import vs write | `load` keeps transaction fields and does not re-validate; `put` validates and assigns them (`at` may pin the time, never backwards) | one method | P1's round trip and load timing; S-EXP-001 and S-EXP-002 [validated] |
| C-07 | queue ids | scoped by queue id; one writer per file | global counters | P9's parallel runs |
| C-08 | error codes | `x-khg-code` along the schema path; tag-dispatched value union | message matching | M45-M50 [validated] |
| C-09 | edge kind | on the relation type | a per-record field | cannot disagree with the relation |
| C-10 | candidate ids | `Queue.submit` assigns `cand:<queue_id>.<seq>` with the item's own sequence number | ids minted by the extractor | one call fewer in P9's loop; a payload id can never disagree with its item [validated: the smoke queue is byte-identical] |
| C-11 | scorer entry points | one `score()` per ability, reading C4 items, C3 queue items and C2 records as written; the version stamp filled from the items | per-consumer converters; a required `versions` argument | P9 scores its queue files and P10 its store without conversion (§1.4) |
| C-12 | text rendering | `render_text(record, labels)` in canonical binding order, labels from one `get_many` | schema usage order (needs the schema at every call site) | P7's baseline and P10's prompts are deterministic from the record alone |

---

## 14. Risks and open questions

**Objections to the fixed decisions:** none. Two risks sit next to F12 and are listed below (R8, R9).

| # | Risk | Mitigation |
|---|---|---|
| R1 | The arity rule counts qualifier and time bindings; if P3a's literature comparison needs another count, every per-arity number moves | `participants` and `core` are materialised beside it; confirm with P3a before C4 (Q1) |
| R2 | Naive HIF readers (plain `hnx.from_hif`) drop the second record of a repeated pair | P5 and every consumer use P2's loaders; the upstream proposal's first ask; the evidence test documents it |
| R3 | Mixed-direction files are `undirected`, so XGI shows no arrows and HyperNetX's own writer fails | slices (`relations=`) give directed files for drawings; reported upstream |
| R4 | Value-shared literal nodes create hubs in XGI/HNX analytics (a year shared by thousands of facts) | `khg-kind: literal` lets analysts drop them; C2 never walks literals; revisit if P5 or P1 see distortion (R01 open question 2) |
| R5 | TypeDB cannot hold ordered roles, all-unbound goals or literal role players natively | capability flags make those scenarios inapplicable; emulation costs are P1's finding |
| R6 | Entities are immutable in 1.0: a label fix needs a new id | P3a finalises labels before its release; entity versioning in 1.1 |
| R7 | The conformance suite assumes an injectable clock; a backend with server-assigned timestamps cannot match exact `as_at` values | scenarios use the runner's clock via `at`; a backend without one declares no `temporal_tx` |
| R8 | F12's repository-root `pyproject.toml` couples package releases to the KB repository | hatchling sdist includes only `src/`, `tests/`, `LICENSE` and the package README; release tags `khg-contracts-v1.0.0` |
| R9 | Python 3.10 with the newest `jsonschema` stack (`rpds-py` needs 3.11 in its 2026 releases [R04 §8.1]) | pip resolves older compatible versions; CI tests 3.10 explicitly |
| R10 | Hash stability: any change in canonical JSON or NFC handling changes every key | golden-hash tests pin `keys` of the gate fixture; changes are majors |
| R11 | C5 is not exercised by the gate and meets real C4 items only later | the R05 tables ship as tests (F14); `khg-c4-items/0.1.0` gives P3a a validator now |
| R12 | Queue files written concurrently by one run would interleave | one writer per file is part of the contract; P9 writes one file per (run, order) |

| # | Open question for the director | Proposed default |
|---|---|---|
| Q1 | Confirm the arity rule (§2.7) with P3a before C4 | adopt as written; P3a reports `participants` too |
| Q2 | How P3a names the Wikidata main-snak roles (subject/value per property, or generic) | P3a and P6 decide together; the schema language supports either [R04 §8.2] |
| Q3 | The time-bound reading: first instant of the period (conservative for coarse ends) vs the end of the period | keep the first-instant rule in 1.0; P7 reports whether it mattered; change only in a major |
| Q4 | Should `disputed` facts be in P10's default reads? | no (default status `asserted`); P10 passes `Where(status={"asserted", "disputed"})` if its study needs them |
| Q5 | Should P7's option iii (per-binding validity) be in 1.0 for question [07.10]? | 1.1, unless P7 commits to testing [07.10] in phase 1 |
| Q6 | Is an HIF export of queue candidates (status `candidate`) needed, for example for P5? | no in 1.0; the profile rejects `candidate` edges |
| Q7 | Upstream timing: file the HIF issue when the package is on PyPI, or before | before: the fixtures and the evidence table already exist, and the gate does not depend on the answer (F15) |
