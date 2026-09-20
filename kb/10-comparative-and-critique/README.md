---
title: 10 — Comparative and critique
type: index
status: draft
tags: [comparison, critique, limitations, debates, glossary, index]
created: 2026-09-20
updated: 2026-09-20
---

# 10 — Comparative and critique

The adversarial section. Everywhere else in this KB the knowledge hypergraph is the subject; here it
is the defendant. Two jobs:

1. **Comparison** — place the KHG precisely against fifteen neighbouring formalisms, and say which
   translations between them are lossless and which are not.
2. **Critique** — state the limitations, failure modes, unresolved debates and over-claims honestly
   enough that someone could use this section to argue *against* building a knowledge hypergraph.

Three conclusions run through all of it:

- **The interesting differences are almost never about expressivity.** Nearly every formalism here
  can encode nearly every other. What differs is which operations are primitive, which invariants a
  type system enforces, and which questions are cheap to ask.
- **"Hypergraph" is a research-programme label, not a technical term.** It currently names at least
  five incompatible data models. Say which one you mean.
- **The strongest recent claims are the least replicated.** The hypergraph-RAG results are
  self-evaluated on self-generated benchmarks, and the one large neutral benchmark in the area does
  not test a hypergraph system at all.

## Notes in this section

| Note | What it covers |
|---|---|
| [formalism-comparison-matrix.md](formalism-comparison-matrix.md) | Fifteen formalisms (RDF, LPG, RDF-star/hyper-relational, positional and role-based KHG, simplicial and combinatorial complexes, bipartite/factor graphs, Johnson hypernetworks, conceptual graphs, frames, relational databases, tensors, metagraphs, higher-order networks) scored on eleven dimensions, plus a table of which translations between them are lossless and which are lossy. |
| [hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md) | "Every hypergraph is a bipartite graph — so why bother?" The objection is formally correct; five arguments for hypergraph vocabulary ranked by strength, three arguments to stop making, and the technical correction that the bijection is with *bicolored*, not bipartite, graphs. |
| [property-graph-vs-typedb-vs-rdf-star.md](property-graph-vs-typedb-vs-rdf-star.md) | The vendor argument, with each camp quoted in its own words and six specific claims fact-checked: Neo4j's intermediate-node stance, TypeDB's hedged "can be seen as a hypergraph", RDF 1.2's explicit non-support for n-ary, and one archived database as a tooling-risk case study. |
| [limitations-and-failure-modes.md](limitations-and-failure-modes.md) | Twelve failure modes with evidence: n-ary sparsity (11.6–13.6% of facts in the Wikidata-derived benchmarks), arity-driven data starvation, role-position ambiguity, typed-hyperedge explosion, the 44.5% JF17K test leak, no standard query language, expansion blow-up, LLM extraction error compounding, provenance loss, retrieval cost, versioning, interoperability gaps. |
| [when-to-use-and-when-not.md](when-to-use-and-when-not.md) | A nine-question decision procedure, six worked examples (clinical guidelines, friendship graphs, M&A deals, encyclopaedic KBs, co-authorship, reaction networks) and twelve anti-patterns. |
| [open-debates.md](open-debates.md) | Six live disagreements: is "knowledge hypergraph" a rebranding of n-ary relations; hyper-relational vs n-ary; are the hypergraph-RAG gains robust; hyperedges vs events; RDF 1.2 triple terms vs full n-ary; and a measured account of the higher-order-network / knowledge-representation citation gap. |
| [critical-reading-of-hypergraph-rag-claims.md](critical-reading-of-hypergraph-rag-claims.md) | Close reading of HyperGraphRAG, Hyper-RAG, HyperRAG and PRoH against GraphRAG-Bench (ICLR 2026): baselines, self-generated question sets, LLM-as-judge metrics, cost tables, an internal result that cuts against the stated mechanism, and an eight-point checklist for the next paper. |
| [glossary-of-confusable-terms.md](glossary-of-confusable-terms.md) | Hypergraph vs hypernetwork (four senses) vs hyper-relational vs higher-order (three senses) vs multi-relational vs multiplex vs multilayer vs heterogeneous graph vs metagraph (two senses) vs hypernode graph vs ubergraph, with a disambiguation table. |

## Reading order

1. **[glossary-of-confusable-terms.md](glossary-of-confusable-terms.md)** — read first if any of the
   terms above are fuzzy; the rest of the section assumes them.
2. **[formalism-comparison-matrix.md](formalism-comparison-matrix.md)** — the map.
3. **[hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md)** — the
   objection you will be asked about first.
4. **[when-to-use-and-when-not.md](when-to-use-and-when-not.md)** — the operative note if you are
   about to build something.
5. **[limitations-and-failure-modes.md](limitations-and-failure-modes.md)** — the costs.
6. **[critical-reading-of-hypergraph-rag-claims.md](critical-reading-of-hypergraph-rag-claims.md)**
   and **[open-debates.md](open-debates.md)** — what is unsettled.

## Relationship to other sections

- [01 Foundations](../01-foundations/) proves the correspondences; this section argues about what
  they mean. In particular
  [hypergraphs-vs-bipartite-vs-simplicial.md](../01-foundations/hypergraphs-vs-bipartite-vs-simplicial.md)
  gives the mathematics that
  [hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md) treats as
  settled background.
- [02 Knowledge representation](../02-knowledge-representation/) catalogues the competing
  definitions; this section asks whether the term survives the catalogue.
- [03 Construction](../03-construction/) describes the LLM pipelines;
  [critical-reading-of-hypergraph-rag-claims.md](critical-reading-of-hypergraph-rag-claims.md)
  evaluates their published results.
- [05 Query, embeddings, reasoning](../05-query-embeddings-reasoning/) covers benchmarks and
  protocols; the leakage and sparsity findings here are the caveats to those numbers.

Bibliography for this section: [`sources/by-topic/10-comparative-and-critique.md`](../../sources/by-topic/10-comparative-and-critique.md).

## Standing caveats

- **Evidence vs opinion** is marked inline throughout. Anything labelled **Opinion** is this KB's
  reading, not a result.
- **`[unverified]`** marks claims whose primary source could not be retrieved in the research run of
  2026-09-20, including several "I found no example of X" statements — absence of evidence from a
  bounded search, not evidence of absence.
- **Maturity and tooling judgements decay.** They are a snapshot of September 2026.
