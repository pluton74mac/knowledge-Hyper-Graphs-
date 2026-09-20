---
title: Reading the frontier — 2026 Q3 snapshot (June–September 2026)
type: survey
status: draft
tags: [frontier, snapshot, arxiv, 2026, quarterly, hypergraph-rag, agent-memory, benchmarks, higher-order-networks, gap-filling]
created: 2026-09-20
updated: 2026-09-20
---

# Reading the frontier — 2026 Q3

**A dated, repeatable snapshot of what appeared on arXiv between 1 June and 20 September 2026.**
This is the note a future run repeats: same queries, new window, new file
(`reading-the-frontier-YYYY-qN.md`). Its companion is the stable map,
[current-frontier-directions.md](current-frontier-directions.md), whose fifteen directions are the
grouping used below.

## Method, so it can be repeated exactly

Queries were issued against the arXiv Atom API on **2026-09-20**, each restricted to
`submittedDate:[202606010000 TO 202609202359]`:

| Query | Hits |
|---|---|
| `all:hypergraph` | 379 |
| `all:"n-ary"` | 23 |
| `all:"higher-order networks"` | 14 |
| `abs:"higher-order network"` | 13 |
| `all:"knowledge hypergraph"` | 1 |
| `abs:"hyper-relational"` | **0** |
| `all:"hypergraph RAG"` | 0 |

**404 unique records.** These were filtered locally against a knowledge-relevance keyword set
(knowledge graph, RAG, LLM, n-ary, link prediction, entity, reasoning, embedding, database, query,
agent, multimodal, …), leaving **139 candidates**, from which the papers below were read and
classified. Records dominated by pure combinatorics (`math.CO`, ~60 of the 379), quantum error
correction (`quant-ph`), circuit partitioning and application-only hypergraph learning are excluded
and counted in §12.

**Caveats.** (i) `all:` matches title, abstract, authors and comments only, not full text, so a
paper that uses hyperedges without saying "hypergraph" in the abstract is invisible here. (ii)
Almost everything below is an unrefereed preprint; venue claims are the authors' own. (iii) arXiv
identifiers in this window take the `26MM.NNNNN` form.

---

## The three headline observations

1. **`abs:"hyper-relational"` returned zero hits for the whole quarter.** Against 43 such papers in
   arXiv's entire history, that is a stop. The hyper-relational *embedding* line — StarE → HINGE →
   HAHE → HyperMono → THOR — published nothing new in Jun–Sep 2026 under that keyword. The energy
   has moved to retrieval and memory.
2. **Hypergraph RAG is now a crowded sub-field with a naming collision problem.** Eight distinct
   RAG systems appeared in sixteen weeks (§2), several unaware of each other, and two *different*
   arXiv entries carry the identical title "SAG: SQL-Retrieval Augmented Generation with Query-Time
   Dynamic Hyperedges" ([2606.15971](https://arxiv.org/abs/2606.15971), 14 Jun;
   [2608.12129](https://arxiv.org/abs/2608.12129), 12 Aug) from the same author group.
3. **Infrastructure arrived.** Two of the quarter's most consequential papers are not models: the
   **AHORN** dataset repository and the **TAHB** text-attributed hypergraph benchmark (§8). Both
   attack the benchmark crisis that
   [current-frontier-directions.md](current-frontier-directions.md) §10 names as the field's worst
   problem.

---

## 1. Hypergraph foundation models (direction 1)

**Nothing new this quarter.** No paper in the 404 records proposes a hypergraph or knowledge-
hypergraph foundation model. The direction's anchors — HYPER and the Hypergraph Foundation Model —
both predate the window. The nearest adjacent work is a *representation* proposal:

| Paper | Date | id | Claim |
|---|---|---|---|
| Godavarti, "Labeled Incidence Structures for Native Transformer Modeling of Text, Knowledge Graphs, and Hypergraphs" | 29 Jul | [2609.20278](https://arxiv.org/abs/2609.20278) | One `(content, slot, relation-instance)` encoding lets a standard transformer process text, KGs and hypergraphs natively, with structure carried by operators rather than architecture. |

This is direction 14 material as much as direction 1, and it is the cleanest statement this quarter
of the "roles are first-class" thesis that runs through
[../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md](../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md).

---

## 2. LLM + KHG reasoning, and hypergraph RAG (directions 2 and 13)

The quarter's densest cluster.

| Paper | Date | id | One-line claim |
|---|---|---|---|
| Liu, Chen, Yang, He, Ju, Han, Liu, Zhou — **HyperSU** | 3 Jun | [2606.28351](https://arxiv.org/abs/2606.28351) | Replaces LLM-generated hyperedge summaries (hallucination-prone, expensive) with corpus-derived *semantic units*, plus clue-guided bidirectional retrieval. |
| Zhang, Ma — **HKVM-RAG** | 5 Jun | [2606.07218](https://arxiv.org/abs/2606.07218) | Key–value separation: answer-path hyperedges are retrieval *keys*, passage text stays the *value*; +3.426 F1 over KG-PPR on 2WikiMultiHopQA under a fixed-substrate protocol. |
| An, Zhang, Liang et al. — **HyCE-RAG** | 12 Jun | [2607.22597](https://arxiv.org/abs/2607.22597) | Query-aware evidence hypergraph with confidence propagation over the incidence structure, aimed at *explainable* multi-hop QA. |
| Wu, Li, Liang, Chen, Liang, Mo, Li — **SAG** | 14 Jun / 12 Aug | [2606.15971](https://arxiv.org/abs/2606.15971), [2608.12129](https://arxiv.org/abs/2608.12129) | No global KG at all: each chunk is an event + entities, i.e. a *latent hyperedge*; entities are SQL join keys at query time. |
| Khrouf, Fillastre, Correia | 2 Jul | [2607.20506](https://arxiv.org/abs/2607.20506) | Self-consistency prompting for extraction plus Personalized PageRank over the hypergraph for chunk retrieval, applied to HyperGraphRAG. |
| Wei, Chen, Gan, Liu, Fu, Kang, Lu, Liu, Zhang, Kwok — **VizRAG** | 22 Jul | [2607.19830](https://arxiv.org/abs/2607.19830) | First RAG system to feed a *rendered picture* of the hypergraph to a multimodal LLM. |
| Chen, Xu, Han, Xue, Wu, Gao, Yan, Gao — **Hyper-M2RAG** | 17 Aug | [2608.16628](https://arxiv.org/abs/2608.16628) | Multimodal document hypergraph with anchor-based *incremental* refinement instead of full-page reconstruction. |
| Nguyen Phu, Nguyen Quang, Luu, Ngo Van, Le, Nguyen — **HyperProve** | 12 Sep | [2609.13768](https://arxiv.org/abs/2609.13768) | Carries intermediate answers *and supporting hyperedges* as retrieval state, biasing the next local expansion. |

**Reading.** Three of the eight (HyperSU, HKVM-RAG, Khrouf et al.) explicitly attack the weak link
this KB identified — LLM extraction quality and retrieval diffusion — rather than proposing another
architecture. HKVM-RAG's "fixed-substrate protocol", which holds the tuple cache, candidate
passages, reader and evaluation budget constant across pairwise-graph and hypergraph variants, is
the first ablation design in this literature that isolates the *structure* as the independent
variable. That is exactly the experiment demanded by
[../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md)
— and it should be checked in full before being believed.

Adjacent, same direction:

- **GrOIL** (Mridul, Talukder, Seneviratne, 22 Aug, [2608.22135](https://arxiv.org/abs/2608.22135)):
  a seven-stage pipeline from documents to an auditable OWL TBox via "Unified Discourse-Hypergraphs",
  with LLM use "restricted to narrow, graph-grounded mediation tasks" and end-to-end provenance. The
  quarter's most direct answer to the provenance gap in
  [../03-construction/schema-induction-and-ontology-alignment.md](../03-construction/schema-induction-and-ontology-alignment.md).
- **HyperPatch** (Chan, Lien, Yao, Ruan, Lin, Shuai, Chiang, 2 Jun,
  [2606.03179](https://arxiv.org/abs/2606.03179)): names "N-ary Structural Drift" — sequential
  knowledge editing over reified triples "fractures relational atomicity", causing retrieval
  mis-grounding "frequently misdiagnosed as parametric hallucination". This is the strongest 2026
  argument that reification is not merely lossy but *actively harmful* under update; it belongs
  beside [../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md).
- **HPFA** (Zhu, Lai, Jiang, Zhang, Li, Kilbasovych, Hong, 3 Aug,
  [2608.02026](https://arxiv.org/abs/2608.02026)): hyperedges over reasoning steps to attribute LLM
  failures by comparing a failing path against a successful one.
- **HyperWorld** (Zhang, Liang, Zhang, Ding, Wu, Li, Su, Saifullah, An, Wang, 12 Jun,
  [2609.00002](https://arxiv.org/abs/2609.00002)): a *controlled* comparison of state serialisations
  for textual world models — independent sentences vs. pairwise triples vs. entity-centred hyperedge
  units — finding hyperedge serialisation gives the clearest gains at 0.5B–1.5B scale. One of very
  few papers in this KB where the serialisation is the independent variable (direction 14).

---

## 3. Agent memory (direction 12)

The fastest-growing direction, and the one where hyperedges are least contested.

| Paper | Date | id | Claim |
|---|---|---|---|
| Wang — **TOKI** | 4 Jun | [2606.06240](https://arxiv.org/abs/2606.06240) | Types the four production contradiction-resolution heuristics as bitemporal operators with isolation preconditions and provenance annotations preserving the losing fact; extends the fold operators "to n-ary conflict sets". |
| Zai, Tan, Chen, Wang, Zhang — **DocTrace** | 9 Jun | [2606.10921](https://arxiv.org/abs/2606.10921) | Query-triggered, on-demand hypergraph working memory plus reuse of prior reasoning experience. |
| Xu, Yang, Huang — **HyperSkill** | 17 Aug | [2608.16114](https://arxiv.org/abs/2608.16114) | Hyperedge per trajectory linking subtasks to reusable skills; dual-path retrieval. |
| Feng, Zhang, Luo, Lin, Yang, Luu — **MAGE** | 30 Aug | [2608.29678](https://arxiv.org/abs/2608.29678) | A hypergraph *database* as multi-agent memory engine: agents, messages, tools, errors, procedures, documents, decisions, evidence in one heterogeneous temporal hypergraph. |
| Cui, Cao, Wen, Yuan, Feng, Chen — **EdgeMem** | 3 Sep | [2609.05553](https://arxiv.org/abs/2609.05553) | **LLM-free** memory construction: preserve original turns, organise by content/temporal/episodic anchors, reserve the LLM for answer generation only. |

**Reading.** Two structural claims are now being tested rather than asserted. TOKI is the first
paper in this KB's coverage to treat **contradiction resolution as write-time concurrency control**,
with an audit row for the losing fact — the provenance-and-retraction machinery that
[../03-construction/incremental-and-streaming-construction.md](../03-construction/incremental-and-streaming-construction.md)
says every serious application needs and no paper had. EdgeMem is the counter-current: it argues
that the LLM summarisation step, not the pairwise structure, is what destroys evidence — a cost and
fidelity argument, not a representational one.

All five evaluate on LoCoMo and/or LongMemEval-S. The direction still lacks the benchmark where
memory *structure* is the independent variable.

---

## 4. Tool use and planning over hypergraphs (new: a sub-direction)

Three papers this quarter model **tools and schemas** as hyperedges. This did not exist as a
direction in the September map and should be added to it.

| Paper | Date | id | Claim |
|---|---|---|---|
| Hong, Dong, Yu, Jiang — **HYSET** | 28 Jul | [2607.25718](https://arxiv.org/abs/2607.25718) | Tool retrieval reframed as query-conditioned *hyperedge prediction* on a tool co-invocation hypergraph: the tool **set** is the unit of scoring, and existing retrieval paradigms reduce to restricted instances. |
| Zhai, Tan, Zou, Wang, Zhang — **HyperAgent** | 31 Jul | [2608.02650](https://arxiv.org/abs/2608.02650) | A **directed** Tool–Schema Hypergraph: each tool is a hyperedge from its input-schema nodes to its output-schema nodes; planning is traversal. |
| Wang, Liu, Zhang, Jin, Sun — HyperAgent4POI | 3 Aug | [2608.01846](https://arxiv.org/abs/2608.01846) | Multi-agent hypergraph message passing for missing-modality recommendation. |

HyperAgent is the quarter's most literal use of a **directed B-hypergraph** as an executable
artefact — the structure of
[../01-foundations/hypergraph-definitions.md](../01-foundations/hypergraph-definitions.md) §on
directed hypergraphs, used for planning rather than for Horn-clause inference.

---

## 5. Temporal and dynamic KHGs (direction 3)

| Paper | Date | id | Claim |
|---|---|---|---|
| Reddy, Saketh, Punjabi, Chandran — **HoT-SSM** | 4 Jun | [2606.05994](https://arxiv.org/abs/2606.05994) | Per-visit hypergraph over clinical concepts + state-space model for long-range temporal dependence in EHR reasoning. |
| Wang, Chen, Han, Hou, Cao, Fan, Zhang — **EHHN** | 2 Jul | [2607.01785](https://arxiv.org/abs/2607.01785) | Object-centric event logs as event–object hyperedges; flattening loses cross-object context, pairwise OCEL graphs lose multi-object events. |
| Liu, Pang, Wang, Shen, He, Cui, Wu, Luu, Luo — **TIEM** | 13 Aug | [2608.13024](https://arxiv.org/abs/2608.13024) | Timestamp-gated Event-Evidence Hypergraph + skill memory; introduces an "Evidence Chasm" framing of contamination/temporal leakage and a recent-period holdout benchmark. |

EHHN matters beyond its application: object-centric event logs are a *pre-existing industrial
n-ary data format*, and the argument that flattening them loses information is the process-mining
version of this KB's central claim. TIEM's temporal-leakage framing is the direction-10 critique
applied to time.

---

## 6. Higher-order network science (direction 7)

Fourteen `physics.soc-ph` / `cs.SI` papers in the window. The structurally interesting ones:

| Paper | Date | id | Claim |
|---|---|---|---|
| Smith, Hacker, Lazovskis, Unger, Smith, Egas Santander | 3 Aug | [2609.01624](https://arxiv.org/abs/2609.01624) | Rich-club analysis and configuration models for **general directed hypergraphs** — the first of these measures defined on the directed class that knowledge hypergraphs actually are. |
| Vasilyeva, Tupikina, Musatov, Raigorodskii, del Genio, Boccaletti | 23 Jul | [2607.20962](https://arxiv.org/abs/2607.20962) | Closeness, betweenness and eccentricity generalised using a hyperedge-size-aware distance rather than clique projection. |
| Nortier, van der Kolk, Jankowski, Dobson, Serrano, Battiston, Boguñá | 7 Sep | [2609.07906](https://arxiv.org/abs/2609.07906) | A latent geometric space coupling interactions across orders makes **nestedness** emerge spontaneously. |
| Jang, Min, Bianconi | 26 Aug | [2608.25560](https://arxiv.org/abs/2608.25560) | $(k,n)$-core percolation with *anchor* nodes: some nodes are essential to a hyperedge's function, others are not. |
| LaRuez, Rooney | 10 Aug | [2608.09788](https://arxiv.org/abs/2608.09788) | Preferential attachment as a mechanism producing the observed high **simpliciality** of real hypergraphs. |
| Rao, Huang | 18 Aug | [2608.17968](https://arxiv.org/abs/2608.17968) | Hypergraph and simplicial-complex encodings of the *same* group interactions differ qualitatively, not just quantitatively, in cooperation dynamics. |
| Han, Liu, Wang, Hao, Zheng, Tang | 11 Jul | [2607.10171](https://arxiv.org/abs/2607.10171) | Immunization strategies on **temporal** higher-order networks, where prior work assumed pairwise or static structure. |
| Nakajima, Sasaki, Aida | 17 Aug | [2608.16602](https://arxiv.org/abs/2608.16602) | Modularity of a field's co-citation network declines as an area emerges — applied to **higher-order network science** itself as one of three case areas. |

**Two of these should change how this KB writes.** The directed rich-club work
([2609.01624](https://arxiv.org/abs/2609.01624)) is the first serious transfer of network-science
structure measures to directed hypergraphs, which is cross-cutting gap 2 in
[current-frontier-directions.md](current-frontier-directions.md). And the anchor-node percolation
result ([2608.25560](https://arxiv.org/abs/2608.25560)) is, in this KB's vocabulary, a claim that
**incidences carry roles of differing criticality** — the physics community arriving independently
at role-typed incidences. See
[../01-foundations/higher-order-interactions.md](../01-foundations/higher-order-interactions.md).

Nakajima et al. is the quarter's oddest and most useful mirror: a quantitative measurement of this
KB's own subject field's coherence.

---

## 7. Expressivity, learning theory and architectures (directions 8, 9)

Thin this quarter. No new expressivity hierarchy appeared; the Width Wall
([2605.13690](https://arxiv.org/abs/2605.13690)) remains the reference and predates the window.

| Paper | Date | id | Claim |
|---|---|---|---|
| Cho, Kang, Ko — **HADES** | 8 Jun | [2606.08978](https://arxiv.org/abs/2606.08978) | HNNs perform substantially worse on **heterophilic** nodes connected through semantically diverse hyperedges; uses node heterophily as an estimate of teacher reliability in distillation. |

HADES's *observation* is the durable part and it bears directly on knowledge hypergraphs: a
hyperedge whose members are semantically diverse is exactly what a typed n-ary fact looks like
(a person, a university, a degree, a subject). If HNNs are systematically weak there, the
[hypergraph-neural-networks.md](../05-query-embeddings-reasoning/hypergraph-neural-networks.md)
architectures may be a poor fit for knowledge hypergraphs specifically.

---

## 8. Benchmarks, datasets and infrastructure (direction 10)

The quarter's most important non-model work.

| Resource | Date | id | What it is |
|---|---|---|---|
| **AHORN** — Frantzen, Schaub | 4 Aug | [2608.03491](https://arxiv.org/abs/2608.03491) | The Aachen Higher-Order Repository of Networks: curated, standardised higher-order datasets where "each dataset entry links a converted dataset to its source, metadata, citation guidance, conversion code, and version history", with revision-specific downloads, format validation and machine-readable discovery. |
| **TAHB** — Kang, Kim, Jeon, Kim | 15 Aug | [2608.15055](https://arxiv.org/abs/2608.15055) | "The first public benchmark integrating hypergraph structures and raw textual attributes": 10 datasets over e-commerce, academia, movies and politics. |
| **GRAFT** — Serna-Aguilera, Jindal, Goggin, Li, Goswami, Bucksch, Liu, Luu | 25 Jun | [2606.27413](https://arxiv.org/abs/2606.27413) | Paired graph *and* hypergraph benchmarks for gene expression and phenotype prediction in *Arabidopsis thaliana*. |

**AHORN is the direct answer to this KB's loudest dataset complaint.** Sections 09 and 10 record
that hypergraph-RAG corpora are distributed via Terabox, Google Drive and Baidu Cloud with no DOI,
no checksum and no licence, and that XGI-DATA's per-record licences are unverified. AHORN's design
— source link, conversion code, version history, revision-specific download, format validation — is
the governance model those sections ask for. It should be evaluated against the criteria in
[../10-comparative-and-critique/privacy-licensing-and-governance.md](../10-comparative-and-critique/privacy-licensing-and-governance.md)
and, if it holds up, adopted in [../../datasets/README.md](../../datasets/README.md).

TAHB closes the other half of the gap: a hypergraph benchmark with *text*, which is what every
LLM-plus-hypergraph method needs and none had.

---

## 9. Databases, indexing and systems (direction 6)

| Paper | Date | id | Claim |
|---|---|---|---|
| Konda — HEI | 24 Aug | [2608.22980](https://arxiv.org/abs/2608.22980) | Hypergraph Embedding Index: organise documents by *combinations* of highly activated latent dimensions, giving inverted-index candidate generation with dense-ranking semantics. |
| Feng, Zhang, Luo, Lin, Yang, Luu — MAGE | 30 Aug | [2608.29678](https://arxiv.org/abs/2608.29678) | A hypergraph-based multimodal *database* (also §3). |
| Liang, Feng, Ren — HySpecPro | 30 Jun | [2607.00055](https://arxiv.org/abs/2607.00055) | Scalable hypergraph partitioning by spectral projection — the hMETIS lineage, still alive. |

No new higher-order *graph database* paper appeared; Besta et al.'s Higher-Order Graph Databases
(Jun 2025) remains the reference.

---

## 10. Multimodal knowledge hypergraphs, and the rest of the window (direction 11)

Papers that are knowledge-relevant but do not cluster with the groups above, listed so the snapshot
is complete.

| Paper | Date | id | Claim |
|---|---|---|---|
| Liao, Tu, Xiao, Li, Shi | 18 Jun | [2606.20162](https://arxiv.org/abs/2606.20162) | Semantic communication over a hypergraph of implicit higher-order correlations rather than pairwise semantic graphs. |
| Lin, Jiang, Lin, Zhang, Zhu, Liu et al. — **EvoGraph-R1** | 14 Jul | [2607.12764](https://arxiv.org/abs/2607.12764) | Self-evolving *multimodal knowledge hypergraph* treated as an environment an agent edits, rather than a static index. |
| Wang, Zhang, Yu, Lei, Zhang — **HyperClaim** | 30 Jul | [2607.28375](https://arxiv.org/abs/2607.28375) | Fine-grained cross-modal hypergraph reasoning over video and text for misinformation detection. |
| Cheng, Wang, He, Dong, Guan — **ProPRL** | 4 Aug | [2608.03006](https://arxiv.org/abs/2608.03006) | Concept–resource hypergraph plus a directed behaviour graph for prerequisite-relation learning in educational KGs, with an anti-symmetry regulariser. |
| Ling, Wang, Tang, Tan, Yang, Guan, Jiang — **H2Table** | 1 Sep | [2609.01216](https://arxiv.org/abs/2609.01216) | Complex tables as hierarchical nested hypergraphs, headers as hyperedges over cells, encoded into an LLM by learnable query vectors. |
| Chen, Shao, Chang, Zhou, Chen, Yu — **STHMoE** | 14 Sep | [2609.15172](https://arxiv.org/abs/2609.15172) | Hypergraph-enhanced dependency coordination for LLM-based urban traffic forecasting. |

Direction 11 is therefore alive but scattered: EvoGraph-R1, HyperClaim, VizRAG (§2) and Hyper-M2RAG
(§2) are all multimodal hyperedge systems, and none of them evaluates the hyperedges themselves —
the gap analysed in
[../03-construction/multimodal-and-multilingual-construction.md](../03-construction/multimodal-and-multilingual-construction.md).

---

## 11. Directions with nothing this quarter

Recorded because silence is information:

- **Direction 4, inductive and zero-shot n-ary completion** — nothing; THOR (Feb 2026) unextended.
- **Direction 5, standards convergence** — nothing on arXiv; the action is at W3C and ISO, tracked
  in [standards-convergence.md](standards-convergence.md).
- **Direction 15, causal hypergraphs** — nothing in the window; the three anchors are all Nov–Dec
  2025.
- **Hyper-relational embedding** — zero abstract hits, as above.

---

## 12. What was excluded, and why it matters

Of 379 `all:hypergraph` records, roughly 60 are `math.CO` extremal combinatorics (Turán and Ramsey
numbers, colourings, percolation thresholds), a dozen are `quant-ph` (hypergraph product codes,
Kochen–Specker contextuality), and several dozen are applications in which the hypergraph is an
encoder device over images, point clouds, EEG, radar or recommendation baskets — the "hyperedge as
learning gadget" category of
[../10-comparative-and-critique/glossary-of-confusable-terms.md](../10-comparative-and-critique/glossary-of-confusable-terms.md).

The ratio itself is the finding: **roughly one in eight hypergraph papers this quarter concerns
knowledge at all.** Berge's object is thriving; the knowledge hypergraph is a small tenant in it.

---

## 13. What a future run should change

Add `abs:"hyperedge"`, `all:"higher-order knowledge"` and `all:"tool hypergraph"` to the query set —
§4's tool-schema cluster surfaced only through the broad `all:hypergraph` sweep. Query the ACL
Anthology and DBLP too, since ACL/EMNLP camera-ready papers appear there before or without an arXiv
posting. Record, for each paper, whether its code resolved on the day of the snapshot; the audit in
[../05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md](../05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md)
shows how fast that decays. And re-run the exclusion count (§12) so the knowledge-vs-total ratio
becomes a tracked time series.

## Sources

- arXiv Atom API, queries as listed in "Method", all issued 2026-09-20. <https://export.arxiv.org/api/query>
- Chan, Y.-K., Lien, W.-S., Yao, D.-T., Ruan, B.-K., Lin, K.-Y., Shuai, H.-H., Chiang, M.-F. "HyperPatch: Sequential Knowledge Editing Under n-ary Structural Drift." arXiv:2606.03179, 2 Jun 2026. <https://arxiv.org/abs/2606.03179>
- Liu, J., Chen, L., Yang, Z., He, C., Ju, M., Han, B., Liu, R., Zhou, X. "HyperSU: Corpus-Driven Semantic-Unit Hypergraph for Retrieval-Augmented Generation." arXiv:2606.28351, 3 Jun 2026. <https://arxiv.org/abs/2606.28351>
- Reddy, T. S., Saketh, V. N. S., Punjabi, Y., Chandran, M. "HoT-SSM: Higher-order Temporal Knowledge Graph Reasoning with State Space Models for Health Care." arXiv:2606.05994, 4 Jun 2026. <https://arxiv.org/abs/2606.05994>
- Wang, Z. "TOKI: A Bitemporal Operator Algebra for Contradiction Resolution in LLM-Agent Persistent Memory." arXiv:2606.06240, 4 Jun 2026. <https://arxiv.org/abs/2606.06240>
- Zhang, M., Ma, Y. "HKVM-RAG: Key-Value-Separated Hypergraph Evidence Organization for Multi-Hop RAG." arXiv:2606.07218, 5 Jun 2026. <https://arxiv.org/abs/2606.07218>
- Cho, J., Kang, D. Y. S., Ko, Y. "Heterophily-Aware Adaptive Knowledge Distillation for Hypergraph Neural Networks" (HADES). arXiv:2606.08978, 8 Jun 2026. <https://arxiv.org/abs/2606.08978>
- Zai, X., Tan, X., Chen, C., Wang, X., Zhang, W. "Trace Only What You Need: Structure-Aware On-Demand Hypergraph Memory for Long-Document Question Answering" (DocTrace). arXiv:2606.10921, 9 Jun 2026. <https://arxiv.org/abs/2606.10921>
- Zhang, Y.-J., Liang, C.-W., Zhang, T.-Y., Ding, J., Wu, Y.-L., Li, A.-B., Su, W.-C., Saifullah, An, H.-Y., Wang, M.-J.-S. "HyperWorld: Hypergraph-Structured State Serialization Improves Learned Textual World Models." arXiv:2609.00002, 12 Jun 2026. <https://arxiv.org/abs/2609.00002>
- An, H.-Y., Zhang, Y.-J., Liang, C.-W. et al. "HyCE-RAG: Hypergraph Chain-of-Evidence Retrieval-Augmented Generation for Explainable Multi-hop Question Answering." arXiv:2607.22597, 12 Jun 2026. <https://arxiv.org/abs/2607.22597>
- Wu, Y., Li, J., Liang, X., Chen, Y., Liang, Y., Mo, L., Li, G. "SAG: SQL-Retrieval Augmented Generation with Query-Time Dynamic Hyperedges." arXiv:2606.15971, 14 Jun 2026; duplicate entry arXiv:2608.12129, 12 Aug 2026. <https://arxiv.org/abs/2606.15971> ; <https://arxiv.org/abs/2608.12129>
- Liao, Y., Tu, S., Xiao, Y., Li, Y., Shi, G. "Implicit Semantic-Aware Communication Based on Hypergraph Reasoning." arXiv:2606.20162, 18 Jun 2026. <https://arxiv.org/abs/2606.20162>
- Serna-Aguilera, M., Jindal, V., Goggin, F. L., Li, J., Goswami, A., Bucksch, A., Liu, S., Luu, K. "GRAFT: Biological Graph and Hypergraph Benchmarks…" arXiv:2606.27413, 25 Jun 2026. <https://arxiv.org/abs/2606.27413>
- Liang, R., Feng, Z., Ren, H. "HySpecPro: Scalable Hypergraph Partitioning via Spectral Projection Optimization." arXiv:2607.00055, 30 Jun 2026. <https://arxiv.org/abs/2607.00055>
- Wang, J., Chen, K., Han, Z., Hou, C., Cao, B., Fan, J., Zhang, J. "EHHN: An Event-driven Heterogeneous Hypergraph Network for Object-Centric Next Activity Prediction." arXiv:2607.01785, 2 Jul 2026. <https://arxiv.org/abs/2607.01785>
- Khrouf, H., Fillastre, P., Correia, S. "Optimizing Hypergraph-Based RAG: Toward Better Fact Extraction and Chunk Retrieval." arXiv:2607.20506, 2 Jul 2026. <https://arxiv.org/abs/2607.20506>
- Han, Z., Liu, L., Wang, X., Hao, Y., Zheng, H., Tang, S. "Immunization on Temporal Higher-Order Networks." arXiv:2607.10171, 11 Jul 2026. <https://arxiv.org/abs/2607.10171>
- Lin, J. et al. "EvoGraph-R1: Self-Evolving Multimodal Knowledge Hypergraphs for Agentic Retrieval." arXiv:2607.12764, 14 Jul 2026. <https://arxiv.org/abs/2607.12764>
- Vasilyeva, E., Tupikina, L., Musatov, D., Raigorodskii, A. M., del Genio, C. I., Boccaletti, S. "Topological measures in weighted hypergraphs." arXiv:2607.20962, 23 Jul 2026. <https://arxiv.org/abs/2607.20962>
- Wei, Y., Chen, Y., Gan, R., Liu, Z., Fu, X., Kang, C., Lu, N., Liu, R., Zhang, Y., Kwok, J. "VizRAG: Enhancing Retrieval-Augmented Generation with Hypergraph Visualization." arXiv:2607.19830, 22 Jul 2026. <https://arxiv.org/abs/2607.19830>
- Hong, X., Dong, P., Yu, X., Jiang, B. "Tools Are Not Islands: Set-Level Tool Retrieval for LLM Agents via Query-Conditioned Hyperedge Prediction" (HYSET). arXiv:2607.25718, 28 Jul 2026. <https://arxiv.org/abs/2607.25718>
- Godavarti, M. "Labeled Incidence Structures for Native Transformer Modeling of Text, Knowledge Graphs, and Hypergraphs." arXiv:2609.20278, 29 Jul 2026. <https://arxiv.org/abs/2609.20278>
- Wang, X., Zhang, J., Yu, X., Lei, L., Zhang, D. C. "HyperClaim: Fine-Grained Cross-Modal Hypergraph Reasoning for Video Misinformation Detection." arXiv:2607.28375, 30 Jul 2026. <https://arxiv.org/abs/2607.28375>
- Zhai, Z., Tan, X., Zou, G., Wang, X., Zhang, W. "HyperAgent: Planning and Acting over Tool-Schema Hypergraphs for Tool-Use LLM Agents." arXiv:2608.02650, 31 Jul 2026. <https://arxiv.org/abs/2608.02650>
- Wang, J., Liu, Y., Zhang, T., Jin, J., Sun, Z. "HyperAgent4POI: Dynamic Semantic Message Passing on Multi-Agent Hypergraphs for Missing-Modality Recommendation." arXiv:2608.01846, 3 Aug 2026. <https://arxiv.org/abs/2608.01846>
- Zhu, R., Lai, H., Jiang, B., Zhang, J., Li, Z., Kilbasovych, O., Hong, J. "HPFA: Hypergraph-Based Paired Failure Attribution for LLM Reasoning." arXiv:2608.02026, 3 Aug 2026. <https://arxiv.org/abs/2608.02026>
- Smith, J. P., Hacker, C., Lazovskis, J., Unger, F., Smith, K. M., Egas Santander, D. "Higher-order rich clubs and configuration models on general directed hypergraphs." arXiv:2609.01624, 3 Aug 2026. <https://arxiv.org/abs/2609.01624>
- Cheng, X., Wang, J., He, C., Dong, R., Guan, Q. "ProPRL: Property-Aware Prerequisite Relation Learning in Educational Knowledge Graphs." arXiv:2608.03006, 4 Aug 2026. <https://arxiv.org/abs/2608.03006>
- Frantzen, F., Schaub, M. T. "A repository for discovery and reuse of higher-order network datasets" (AHORN). arXiv:2608.03491, 4 Aug 2026. <https://arxiv.org/abs/2608.03491>
- LaRuez, J., Rooney, B. "Preferential Attachment as a Simpliciality-Enforcing Mechanism in Hypergraphs." arXiv:2608.09788, 10 Aug 2026. <https://arxiv.org/abs/2608.09788>
- Liu, W., Pang, S., Wang, C., Shen, T., He, J., Cui, Z., Wu, X., Luu, A. T., Luo, H. "TIEM: Temporal Integration of Hypergraph Evidence and Skill Memory for Event-Driven Financial Forecasting." arXiv:2608.13024, 13 Aug 2026. <https://arxiv.org/abs/2608.13024>
- Kang, D. Y. S., Kim, J., Jeon, J., Kim, S.-W. "TAHB: A Comprehensive Benchmark for Text-Attributed Hypergraph Learning." arXiv:2608.15055, 15 Aug 2026. <https://arxiv.org/abs/2608.15055>
- Xu, R., Yang, T., Huang, W.-C. "HyperSkill: Self-Evolving LLM Agents via Hypergraph-Structured Skill Memory." arXiv:2608.16114, 17 Aug 2026. <https://arxiv.org/abs/2608.16114>
- Chen, S., Xu, Y., Han, X., Xue, R., Wu, D., Gao, Y., Yan, C., Gao, Y. "Hypergraph-based Multimodal Retrieval-Augmented Generation with Incremental Refinement" (Hyper-M2RAG). arXiv:2608.16628, 17 Aug 2026. <https://arxiv.org/abs/2608.16628>
- Nakajima, K., Sasaki, Y., Aida, M. "Declining Modularity of Intellectual Bases During the Emergence of Research Areas." arXiv:2608.16602, 17 Aug 2026. <https://arxiv.org/abs/2608.16602>
- Rao, W., Huang, J. "Simplicial closure fragments the explosive cooperation transitions in higher-order public goods games." arXiv:2608.17968, 18 Aug 2026. <https://arxiv.org/abs/2608.17968>
- Mridul, M. A., Talukder, A., Seneviratne, O. "GrOIL: Graph-Grounded Domain Ontology Induction with Constrained LLM Mediation." arXiv:2608.22135, 22 Aug 2026. <https://arxiv.org/abs/2608.22135>
- Konda, K. "Hypergraph Embedding Indexing for Efficient Dense Vector Retrieval." arXiv:2608.22980, 24 Aug 2026. <https://arxiv.org/abs/2608.22980>
- Jang, H., Min, B., Bianconi, G. "$(k,n)$-core percolation on hypergraphs with anchor nodes." arXiv:2608.25560, 26 Aug 2026. <https://arxiv.org/abs/2608.25560>
- Feng, Y., Zhang, R., Luo, H., Lin, Z., Yang, C., Luu, A. T. "Diachronic Hypergraphs for Orchestrated Multi-Agent Multimodal Memory Curation" (MAGE). arXiv:2608.29678, 30 Aug 2026. <https://arxiv.org/abs/2608.29678>
- Ling, J., Wang, Y., Tang, C., Tan, H., Yang, Y., Guan, Y., Jiang, J. "H2Table: Hierarchical Hypergraph-Enhanced Large Language Models for Complex Table Reasoning." arXiv:2609.01216, 1 Sep 2026. <https://arxiv.org/abs/2609.01216>
- Cui, Z., Cao, J., Wen, Z., Yuan, B., Feng, J., Chen, S. "EdgeMem: LLM-Free Agent Memory Construction and Retrieval via Evidence-Preserving Multi-Anchor Hypergraph." arXiv:2609.05553, 3 Sep 2026. <https://arxiv.org/abs/2609.05553>
- Nortier, B. L., van der Kolk, J., Jankowski, R., Dobson, S., Serrano, M. Á., Battiston, F., Boguñá, M. "Latent geometry organizes higher-order interactions." arXiv:2609.07906, 7 Sep 2026. <https://arxiv.org/abs/2609.07906>
- Nguyen Phu, A., Nguyen Quang, D., Luu, H. A., Ngo Van, L., Le, T., Nguyen, T. H. "HyperProve: Answer-Guided Hypergraph Expansion for Multi-Hop Question Answering." arXiv:2609.13768, 12 Sep 2026. <https://arxiv.org/abs/2609.13768>
- Chen, J., Shao, Q., Chang, Y., Zhou, M., Chen, D., Yu, W. "STHMoE: Hypergraph-Enhanced Heterogeneous Dependency Coordination for LLM-Based Urban Traffic Data Forecasting." arXiv:2609.15172, 14 Sep 2026. <https://arxiv.org/abs/2609.15172>
- Jiang, F., Li, Y., Feng, Y., Zheng, K., Niu, L. "The WidthWall: A Strict Expressivity Hierarchy for Hypergraph Neural Networks." arXiv:2605.13690, 13 May 2026 (outside the window; cited as the standing reference). <https://arxiv.org/abs/2605.13690>
- Yu, W., Lu, Y., Yang, D. "THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs." arXiv:2602.05424, 5 Feb 2026 (outside the window). <https://arxiv.org/abs/2602.05424>
