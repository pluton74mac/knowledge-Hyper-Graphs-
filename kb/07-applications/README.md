---
title: 07 — Applications
type: index
status: draft
tags: [hypergraph, applications, index, matrix]
created: 2026-09-20
updated: 2026-09-21
---

# 07 — Applications

Where knowledge hypergraphs and hypergraph-structured knowledge are actually used, with what results,
and how strong the evidence is. Start with [applications-overview](applications-overview.md) for the
taxonomy of what a hyperedge *means* in each setting, then read by domain or by technique below.

## Files in this section

| File | What it covers |
|---|---|
| [applications-overview](applications-overview.md) | The four senses of "hypergraph" in applied work; application types; the domain × application-type matrix |
| [retrieval-augmented-generation](retrieval-augmented-generation.md) | HyperGraphRAG, Hyper-RAG, HyperRAG, PRoH, Cog-RAG, OG-RAG, EbmKG/IdepRAG, OKH-RAG, Hyper-KGGen; costs; the GraphRAG-Bench critique |
| [question-answering-over-n-ary-facts](question-answering-over-n-ary-facts.md) | WikiPeopleQA, StarQE/NQE/LKHGT complex query answering, temporal and event QA, SciREX/HyperDocRED |
| [biomedical-and-life-sciences](biomedical-and-life-sciences.md) | Reactions and pathways, protein complexes, HODDI, polypharmacy, HypKG, PrimeKG contrast, clinical RAG |
| [chemistry-and-reaction-networks](chemistry-and-reaction-networks.md) | Directed multi-hypergraphs, integer hyperflows, assembly, retrosynthesis AND/OR search |
| [scientific-knowledge-and-scholarly-graphs](scientific-knowledge-and-scholarly-graphs.md) | Co-authorship and simplicial closure, ORKG, SciERC vs SciREX, materials-science concept hypergraphs |
| [recommender-systems-and-e-commerce](recommender-systems-and-e-commerce.md) | HyperRec, DHCF, DHCN, HCCF, KHGRec; what recommender evidence does and does not transfer |
| [finance-legal-and-compliance](finance-legal-and-compliance.md) | Transactions as hyperedges, fraud detection, deals and ownership roles, legal/regulatory RAG |
| [cybersecurity-and-it-operations](cybersecurity-and-it-operations.md) | Attack graphs as directed hypergraphs, HAG threat intelligence, STIX Sighting, provenance, CMDBs |
| [social-collaborative-and-communication](social-collaborative-and-communication.md) | Group interactions, higher-order link prediction, rumour propagation and misinformation |
| [software-engineering-and-code-knowledge](software-engineering-and-code-knowledge.md) | HyperRes dependency resolution, build graphs, code KGs (and why they are binary) |
| [ai-agents-memory-and-planning](ai-agents-memory-and-planning.md) | AND/OR and HTN planning, tool-schema hypergraphs, HyperMem/HyperSkill/DocTrace, AtomSpace |
| [hierarchical-and-planned-hypergraph-retrieval](hierarchical-and-planned-hypergraph-retrieval.md) | Three generations of hypergraph retrieval: flat k-NN, planned traversal (PRoH's EWO, plan context graph, sub-question DAG) and learned policies (Graph-R1, HyperGraphPro), then hierarchy and community summaries (HiRAG, H²RAG at PAKDD 2026, HHS-RAG, EEG-MedRAG); cost and token-budget reporting, and why the ladder's baseline is out of date. Added in run 02. |
| [temporal-hyperedges-and-editable-agent-memory](temporal-hyperedges-and-editable-agent-memory.md) | Valid time on the hyperedge: what it would formally require, the bitemporal binary precedent (Graphiti/Zep, TOKI, Quipu), the n-ary state of the art split into interpolation (HypeTKG, VITA) and extrapolation (NE-Net, MT-Path, HTKGH), the supersession gap, the agent-memory consumers (HyperMem, HyperSkill, EvoGraph-R1, EdgeMem, MAGE) with verified benchmarks and judge protocols, LoCoMo vs LongMemEval, and a six-point data-model sketch. Added in run 02. |
| [industry-adoption-and-products](industry-adoption-and-products.md) | TypeDB, Wikidata, RDF 1.2/RDF-star, Stardog, Palantir, HypergraphDB, RelationalAI; maturity grades |
| [case-studies](case-studies.md) | Eight mini case studies with the concrete numbers, and what each number does not show |

Bibliography for this section: [`sources/by-topic/07-applications.md`](../../sources/by-topic/07-applications.md).

## Domain × technique matrix

Techniques, left to right: **KHG-store** = facts stored as role-bearing n-ary facts; **HG-retrieval** =
hypergraph used as a retrieval index for an LLM; **HGNN** = hypergraph neural network / representation
learning; **DH-algorithms** = directed-hypergraph algorithms (hyperpaths, B-connectivity, hyperflows,
AND/OR search); **HO-prediction** = higher-order link or fact prediction; **Qualifier-QA** =
qualifier-aware query answering; **Agent-memory** = hypergraph memory or planning for agents.

Strength: **●** repeatedly demonstrated with public code/data or long-standing practice; **◐** several
papers or one solid peer-reviewed result; **○** proposed, single demonstration, or structural argument
only; blank = nothing found in this research run.

| Domain \ Technique | KHG-store | HG-retrieval | HGNN | DH-algorithms | HO-prediction | Qualifier-QA | Agent-memory |
|---|---|---|---|---|---|---|---|
| Biomedicine / health | ◐ | ● | ◐ | ● | ◐ | ○ | |
| Chemistry / materials | ○ | ○ | ◐ | ● | ○ | | |
| Scholarly / science of science | ◐ | ○ | ◐ | | ● | | ○ |
| E-commerce / media | | ○ | ● | | ◐ | | |
| Finance | ○ | ◐ | ● | | ◐ | | |
| Legal / compliance | ○ | ◐ | | | | ○ | |
| Cybersecurity / IT | ◐ | | ◐ | ● | | | |
| Social / communication | | | ◐ | | ● | | |
| Software engineering | | ○ | | ● | | | ◐ |
| AI agents | ○ | ● | | ◐ | | | ● |
| General knowledge bases | ● | ● | ● | | ● | ● | |

Reading the matrix:

- The **DH-algorithms** column is the oldest and most solid, and it is almost entirely outside the
  LLM literature: metabolism, chemistry, attack graphs, build and dependency systems.
- The **HG-retrieval** column is the newest, the most crowded, and the least independently validated —
  see the critique section of [retrieval-augmented-generation](retrieval-augmented-generation.md).
- The **HGNN** column is large but mostly sense-D: the hyperedge is an inductive bias, not a fact
  ([recommender-systems-and-e-commerce](recommender-systems-and-e-commerce.md)).
- The **KHG-store** column — role-labelled n-ary facts actually stored as such — is the sparsest, which
  is the central tension of this whole section: the representation the KB is named after is the one with
  the fewest deployments ([industry-adoption-and-products](industry-adoption-and-products.md)).

## How to use this section

- **Choosing a representation for a project:** read [applications-overview](applications-overview.md)
  §1 to identify which sense of hyperedge you need, then the domain note, then
  [industry-adoption-and-products](industry-adoption-and-products.md) for what will actually store it.
- **Assessing a claim in a paper:** [case-studies](case-studies.md) gives the comparable numbers and the
  standard caveats.
- **Looking for an unclaimed research vector:** the blanks and the ○ cells above, plus the "what it does
  not show" lines in [case-studies](case-studies.md).
- **Pushing back on a hypergraph claim:** section 10, especially
  [critical-reading-of-hypergraph-rag-claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md),
  [limitations-and-failure-modes](../10-comparative-and-critique/limitations-and-failure-modes.md) and
  [hypergraph-vs-bipartite-graph-debate](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md).
