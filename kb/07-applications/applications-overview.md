---
title: Applications of knowledge hypergraphs — taxonomy and matrix
type: survey
status: draft
tags: [hypergraph, n-ary, applications, taxonomy, RAG, question-answering, recommendation, biomedicine]
created: 2026-09-19
updated: 2026-09-19
---

# Applications of knowledge hypergraphs — taxonomy and matrix

This note organises the application landscape of knowledge hypergraphs (KHGs) and, more broadly, of
hypergraph-structured knowledge. It distinguishes *what the hyperedge means* in each application, because
the word "hypergraph" is used for at least four different things in the applied literature, and the
value of the n-ary representation differs accordingly.

## 1. Four senses of "hypergraph" in applications

| Sense | What a hyperedge is | Typical example | Where the KHG framing is strongest |
|---|---|---|---|
| **A. N-ary fact** | One relational fact with 3+ typed participants (roles or qualifiers) | *acquisition(acquirer, target, bank, advisor, counsel)*; Wikidata statement with qualifiers | Knowledge bases, QA, RAG over extracted facts |
| **B. Group / set interaction** | A set of entities that co-occur in one event (no roles) | Co-authorship of a paper; drugs co-prescribed in one visit; accounts in one transaction | Social, biomedical pharmacovigilance, fraud |
| **C. Directed transformation** | Ordered pair of *sets* (tail set → head set), often with stoichiometry | Metabolic reaction A+B→C+D; a build rule; an AND/OR-graph arc | Chemistry, cellular networks, planning |
| **D. Latent / learned grouping** | A learned or heuristic cluster used as an inductive bias for a neural model | HCCF's learnable hypergraph for collaborative filtering; passage-as-hyperedge in HGRAG | Recommenders, retrieval indexing |

Sense A is what section 02 of this KB calls a knowledge hypergraph proper. Senses B and C are
hypergraphs of *knowledge-bearing events*; sense D is a machine-learning device. Many 2025–2026 RAG
papers mix A and D (an LLM extracts n-ary facts *and* passages are treated as hyperedges), which is one
reason reported gains are hard to compare — see [retrieval-augmented-generation](retrieval-augmented-generation.md).

## 2. Application types

1. **Knowledge completion / link prediction over n-ary facts** — predicting a missing participant or
   qualifier. The hyper-relational benchmark WD50K contains 236,507 Wikidata statements, about 14 % of
   which carry at least one qualifier pair, and qualifier-aware models gained up to 25 MRR points over
   triple-only baselines on JF17K [Galkin et al., 2020](https://arxiv.org/abs/2009.10847). Covered in
   section 05; applied uses appear in [question-answering-over-n-ary-facts](question-answering-over-n-ary-facts.md).
2. **Question answering** — answering questions whose answer requires more than two entities or a
   qualifier (time, role, location). The first n-ary KGQA dataset, WikiPeopleQA, has 4,491 QA pairs over a
   KG with 557 n-ary relation types [Zhang et al., 2022](https://arxiv.org/abs/2108.08297).
3. **Retrieval-augmented generation (RAG)** — using a hypergraph as the retrieval index for an LLM.
   Since HyperGraphRAG [Luo et al., 2025](https://arxiv.org/abs/2503.21322) and Hyper-RAG
   [Feng et al., 2025](https://arxiv.org/abs/2504.08758) this has become the most active applied area
   (30+ arXiv papers in 2025–2026, see the RAG note).
4. **Recommendation** — sessions, baskets, or knowledge-graph neighbourhoods as hyperedges
   [Wang et al., 2020](https://doi.org/10.1145/3397271.3401133); [Xia et al., 2022](https://arxiv.org/abs/2204.12200).
5. **Scientific discovery** — reaction networks as directed hypergraphs
   [Klamt et al., 2009](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000385);
   literature-scale concept hypergraphs for hypothesis generation
   [Stewart & Buehler, 2026](https://arxiv.org/abs/2601.04878).
6. **Reasoning and planning** — AND/OR graphs are directed hypergraphs
   [Gallo et al., 1993](https://doi.org/10.1016/0166-218X(93)90045-P); tool schemas and skill
   trajectories as hyperedges in LLM agents [Zhai et al., 2026](https://arxiv.org/abs/2608.02650);
   [Xu et al., 2026](https://arxiv.org/abs/2608.16114).
7. **Data integration and enterprise ontologies** — n-ary relations with roles as the native schema in a
   database (TypeDB) [Hemsley, 2026](https://typedb.com/blog/the-case-for-a-structured-hypergraph);
   n-ary business rules as a hyperedge layer over heterogeneous business systems
   [Wang et al., 2026](https://arxiv.org/abs/2605.14259).
8. **Anomaly and fraud detection** — multi-party transactions as hyperedges
   [Wu et al., 2025](https://arxiv.org/abs/2503.21463); [Cui et al., 2026](https://arxiv.org/abs/2601.11073).

## 3. Domain × application-type matrix

Legend: **●** mature or repeatedly demonstrated with public code/data; **◐** several papers, limited
evaluation or one group; **○** isolated or proposed; blank = nothing found in this research run.
Each cell names the note where the evidence lives.

| Domain \ Type | Completion | QA | RAG | Recommendation | Discovery | Reasoning/planning | Integration | Anomaly/fraud |
|---|---|---|---|---|---|---|---|---|
| Biomedicine / health | ◐ HODDI, HyperADRs | ◐ EEG-MedRAG | ● Hyper-RAG, HyperGraphRAG (medicine) | ◐ HypeMed | ● Reactome B-connectivity, repurposing | ○ | ◐ HypKG | |
| Chemistry / materials | ○ | | ○ | | ● reaction hypergraphs, DLGNet, ChemHGNN | ◐ retrosynthesis hypergraph search | | |
| Scholarly / science of science | ◐ higher-order link prediction | | ○ | | ● co-authorship, concept hypergraphs | | ◐ ORKG (reified) | |
| E-commerce / media | | | ○ | ● HyperRec, DHCN, HCCF, KHGRec | | | | |
| Finance | | | ○ TIEM | | ◐ credit hypergraphs | ○ | ◐ TypeDB deals | ● HyperDet, HIMVH, HCLNet |
| Legal / compliance | | | ◐ HyperGraphRAG (legal), OG-RAG | | | | ◐ GrOIL (insurance contracts) | |
| Cybersecurity / IT | | | | | | ○ privilege hypergraphs | ◐ HAG (CTI) | ◐ hypergraph IDS |
| Social / communication | ● simplicial closure | | | | ● rumour propagation, motifs | | | |
| Software engineering | | | ◐ HyperGraphRAG (CS domain) | | | ◐ tool-schema hypergraphs | ○ co-change hypergraphs | |
| AI agents / memory | | ● HyperMem, EdgeMem | ● HGMem, DocTrace | | | ● HyperSkill, HyperAgent, DaSH | ◐ AtomSpace | |
| Enterprise operations | | | | | | ◐ HEAR (n-ary rules) | ● TypeDB, RelationalAI (relational) | |

## 4. Where the n-ary representation demonstrably pays off

Evidence that the hyperedge, not just "more structure", is responsible for the gain:

- **Qualifiers change answers.** On WD50K variants with 33 %, 66 % and 100 % qualified statements,
  performance rises with the qualifier ratio [Galkin et al., 2020](https://arxiv.org/abs/2009.10847).
- **Pairwise projection loses connectivity semantics.** In Reactome, ~90 % of nodes reach >80 % of a
  directed *graph*, whereas under strict hypergraph B-connectivity only five nodes connect to more than
  20 others [Franzese et al., 2019](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1007384).
- **Higher-order drug combinations exist in the data.** HODDI records combinations of 2–8 drugs per
  adverse-event report; hypergraph models outperformed graph models, and an MLP beat standard GNNs
  [Wang et al., 2025](https://arxiv.org/abs/2502.06274).
- **Decomposing n-ary facts into triples hurts QA.** Baselines forced to split WikiPeopleQA n-ary facts
  via dummy entities reached 10.9–24.9 % accuracy versus 54.4 % for fact-tree reasoning
  [Zhang et al., 2022](https://arxiv.org/abs/2108.08297).

## 5. Where the case is weaker (opinion)

- Many recommender and retrieval "hypergraphs" are latent groupings (sense D); the gains are real but
  do not establish the value of n-ary *knowledge*.
- RAG evaluations often rely on LLM-as-judge and on datasets constructed by the same authors; cross-paper
  comparisons are rare (PRoH's reported +19.73 % F1 over HyperGraphRAG is one of the few
  [Zai et al., 2026](https://arxiv.org/abs/2510.12434)).
- Industrial adoption of true n-ary storage remains concentrated in a few vendors; the dominant graph
  databases connect exactly two nodes per relationship (see [industry-adoption-and-products](industry-adoption-and-products.md)).

## Sources

- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs." EMNLP 2020. https://arxiv.org/abs/2009.10847
- Zhang, Y., Li, P., Liang, H., Jatowt, A., Yang, Z. "Fact-Tree Reasoning for N-ary Question Answering over Knowledge Graphs." Findings of ACL 2022. https://arxiv.org/abs/2108.08297
- Luo, H. et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025. https://arxiv.org/abs/2503.21322
- Feng, Y. et al. "Hyper-RAG: Combating LLM Hallucinations using Hypergraph-Driven Retrieval-Augmented Generation." arXiv 2025; Nature Communications 17:5778, 2026. https://arxiv.org/abs/2504.08758
- Wang, J., Ding, K., Hong, L., Liu, H., Caverlee, J. "Next-item Recommendation with Sequential Hypergraphs." SIGIR 2020. https://doi.org/10.1145/3397271.3401133
- Xia, L., Huang, C., Xu, Y., Zhao, J., Yin, D., Huang, J. X. "Hypergraph Contrastive Collaborative Filtering." SIGIR 2022. https://arxiv.org/abs/2204.12200
- Klamt, S., Haus, U.-U., Theis, F. "Hypergraphs and Cellular Networks." PLoS Computational Biology 5(5):e1000385, 2009. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000385
- Stewart, I. A., Buehler, M. J. "Higher-Order Knowledge Representations for Agentic Scientific Reasoning." arXiv 2026. https://arxiv.org/abs/2601.04878
- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. "Directed hypergraphs and applications." Discrete Applied Mathematics 42:177–201, 1993. https://doi.org/10.1016/0166-218X(93)90045-P
- Zhai, Z., Tan, X., Zou, G., Wang, X., Zhang, W. "HyperAgent: Planning and Acting over Tool-Schema Hypergraphs for Tool-Use LLM Agents." arXiv 2026. https://arxiv.org/abs/2608.02650
- Xu, R., Yang, T., Huang, W.-C. "HyperSkill: Self-Evolving LLM Agents via Hypergraph-Structured Skill Memory." arXiv 2026. https://arxiv.org/abs/2608.16114
- Hemsley, C. "Graph databases, complex data, and the case for a structured hypergraph." TypeDB blog, 5 March 2026. https://typedb.com/blog/the-case-for-a-structured-hypergraph
- Wang, L. et al. "Hypergraph Enterprise Agentic Reasoner over Heterogeneous Business Systems." arXiv 2026. https://arxiv.org/abs/2605.14259
- Wu, J. et al. "Unveiling Latent Information in Transaction Hashes: Hypergraph Learning for Ethereum Ponzi Scheme Detection." arXiv 2025. https://arxiv.org/abs/2503.21463
- Cui, R., Zhang, N., Zhu, K., Zhang, Q. "Hippocampus-Inspired Multi-View Hypergraph Learning for Web Finance Fraud." arXiv 2026. https://arxiv.org/abs/2601.11073
- Franzese, N., Groce, A., Murali, T. M., Ritz, A. "Hypergraph-based connectivity measures for signaling pathway topologies." PLoS Computational Biology, 2019. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1007384
- Wang, Z., Shi, Y., Liu, X., Chen, C., Wen, J., Wang, R. "HODDI: A Dataset of High-Order Drug-Drug Interactions for Computational Pharmacovigilance." arXiv 2025. https://arxiv.org/abs/2502.06274
- Zai, X., Tan, X., Wang, X., Liu, Q., Xu, X., Zhang, W. "PRoH: Dynamic Planning and Reasoning over Knowledge Hypergraphs for Retrieval-Augmented Generation." WWW 2026. https://arxiv.org/abs/2510.12434
