---
title: Biomedicine and the life sciences
type: survey
status: draft
tags: [hypergraph, n-ary, biomedicine, metabolic-networks, reactome, polypharmacy, drug-drug-interaction, EHR, protein-complex]
created: 2026-09-20
updated: 2026-09-21
---

# Biomedicine and the life sciences

Biology is where hypergraph-structured knowledge has the longest and best-evidenced track record,
because two of its core objects are *irreducibly* n-ary: a biochemical reaction consumes a set and
produces a set, and a protein complex is a set of subunits. Neither survives projection to pairwise
edges without loss. This note separates the strong cases from the fashionable ones.

## 1. Reactions and pathways as directed hyperedges

The founding argument is [Klamt, Haus and Theis, 2009](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000385)
(*PLoS Computational Biology* 5(5):e1000385). A reaction `A + B → C + D` is a directed hyperedge whose
tail is `{A, B}` and head is `{C, D}`, with stoichiometric coefficients as a function from nodes to
natural numbers. Their concrete demonstration of information loss uses protein complexes from tandem
affinity purification: computing the *k*-core of the same data gives a maximum 2-core of `{A, C, E}`
under the hypergraph model but a maximum 3-core of `{A, B, C, D}` under the graph projection — i.e.
graph projection can misidentify which proteins form the network core. They also stress that metabolic
analysis requires the **AND** semantics between reactants, which a plain graph (and, they argue, even a
bipartite graph used naively) does not enforce.

The strongest quantitative follow-up is
[Franzese, Groce, Murali and Ritz, 2019](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1007384)
(*PLoS Computational Biology* 15(10):e1007384) on Reactome signalling pathways. They define
**B-connectivity** (a hyperedge may be traversed only when *every* node in its tail is already reached)
and a parameterised **B-relaxation distance** that interpolates towards bipartite-graph connectivity.
On a Reactome hypergraph of roughly 19,650 entities and 8,773 hyperedges (15,440 nodes and 8,773
hyperedges after filtering out small molecules), across 34 signalling pathways for influence analysis
and 140 non-redundant pathways benchmarked against 1.4 million STRING protein pairs:

| Representation | Reachability |
|---|---|
| Directed graph | ~90 % of nodes reach >80 % of the network |
| Compound / bipartite graph | 30–40 % of node pairs reachable |
| Hypergraph, strict B-connectivity | only **5** nodes reach more than 20 others; most reach none |

That gap is the single most striking number in this KB. It says the "everything is connected to
everything" impression given by pathway *graphs* is largely an artefact of relaxing the AND semantics.
Whether strict B-connectivity is the biologically right notion is a separate question — the authors
introduce B-relaxation precisely because reality sits between the two — but the pairwise projection is
demonstrably over-optimistic.

**Databases.** Reactome (release 97, 30 June 2026, [reactome.org](https://reactome.org/)) is curated as
reactions with input and output sets, so it is natively a directed hypergraph even though it is usually
consumed as a graph. KEGG and MetaCyc encode the same structure with stoichiometry; the *hypergraph*
framing of these resources is the Klamt/Franzese line rather than a claim the databases themselves make.
[unverified: current node/reaction counts for Reactome 97, KEGG and MetaCyc were not retrievable in this
research run]

## 2. Protein complexes

A complex is a set of subunits, which is a hyperedge with no natural direction. The k-core example above
is the canonical illustration of what pairwise projection (the "spoke" or "matrix" models of
purification data) does to complex membership. This is also the cleanest case of sense **B**
(group interaction) in [applications-overview](applications-overview.md): no roles, just co-membership.

## 3. Higher-order drug interactions and polypharmacy

The pairwise baseline here is **Decagon** ([Zitnik, Agrawal, Leskovec, 2018](https://arxiv.org/abs/1802.00543),
*Bioinformatics* 34(13):i457–i466, ISMB 2018), a multi-relational graph convolutional model over
protein–protein, drug–protein and drug–drug edges, where each side-effect type is a separate edge
type. It reports up to 69 % improvement over alternatives and about 20 % average gain. Decagon is
explicitly a *graph* model: a polypharmacy side effect is a drug–drug edge, so a three-drug interaction
must be decomposed.

**HODDI** ([Wang et al., 2025](https://arxiv.org/abs/2502.06274)) is the dataset that makes the
higher-order case empirically. Built from a decade (2014–2024) of FDA Adverse Event Reporting System
records, it contains **109,744 records over 2,506 unique drugs and 4,569 unique side effects**, curated
specifically so that a record is a *set* of co-administered drugs rather than a pair — existing
resources such as TWOSIDES are pairwise. Two findings from the paper are worth keeping:

1. Hypergraph models outperform graph models on capturing multi-drug interactions.
2. A plain multi-layer perceptron can outperform the graph models. That is a warning, not a
   confirmation: it suggests that on this dataset much of the signal is in the drug-set features rather
   than in relational propagation, and that graph baselines were not strong.

## 4. Patient context: EHRs as hyperedges over a knowledge graph

**HypKG** ([Xie, Han, Xu, Hu, Lu, Yang, 2025](https://arxiv.org/abs/2507.19726), ISWC 2025 research
track) links entities mentioned in electronic health records to a general biomedical KG, then uses a
hypergraph to *contextualise* the KG with patient state: the hyperedge groups a patient's diagnoses and
medications with the KG knowledge they activate, and hypergraph transformers learn joint representations
of patients and knowledge under a downstream prediction objective
([code](https://github.com/constantjxyz/HypKG)). The paper reports significant improvements on
healthcare prediction tasks over baselines across multiple metrics.
[unverified: the exact EHR datasets, their sizes, and the numerical gains were not retrievable from the
abstract in this research run]

This is a genuinely different use of a hyperedge from the RAG systems: the hyperedge is a *context
window over a knowledge graph*, sense D with a clinical justification.

## 5. Contrast: PrimeKG, a large biomedical KG that is not a hypergraph

**PrimeKG** ([Chandak, Huang, Zitnik, 2023](https://www.nature.com/articles/s41597-023-01960-3),
*Scientific Data*) integrates 20 resources into over 100,000 nodes and **4,050,249 relationships across
29 edge types**, covering 17,080 diseases, and is notable for carrying indication, contraindication and
off-label-use drug–disease edges that most biomedical KGs lack ([code](https://github.com/mims-harvard/PrimeKG)).

It is worth stating plainly: PrimeKG is a **binary** knowledge graph, and it is the most widely used
biomedical KG of its generation. Its provenance, dosage, population and evidence-level context lives in
edge attributes or is dropped, not in n-ary facts. Any claim that biomedicine "needs" knowledge
hypergraphs has to explain why PrimeKG is as useful as it is. The honest reading is that the n-ary
requirement is sharp for *mechanism* (reactions, complexes, multi-drug events) and soft for
*association* (gene–disease, drug–target), which is what most biomedical KGs encode.

## 6. Clinical RAG and QA

Medicine is the domain where hypergraph RAG has been tested most:

- HyperGraphRAG's Medicine split (built from international hypertension guidelines) shows its largest
  margin: F1 35.35 against 27.90 for chunk RAG and 12.79–21.34 for the four graph RAG baselines
  ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)).
- Hyper-RAG's primary corpus is a neurology corpus of ~1.97M tokens, with +12.3 % accuracy over direct
  LLM use, +6.3 % over GraphRAG and +6.0 % over LightRAG, and a second medical corpus in pathology
  ([Feng et al., 2025](https://arxiv.org/abs/2504.08758);
  [Feng et al., 2026](https://www.nature.com/articles/s41467-026-71411-1)).
- **EbmKG / IdepRAG** ([Dou et al., 2025](https://arxiv.org/abs/2503.16530), arXiv only) is the earliest of
  the three, and the only one built for *evidence-based medicine* rather than general QA: 41,504
  drug descriptions and clinical guidelines (UpToDate and a Chinese pharmacy site, mixed language)
  become 806,495 evidence hyperedges over MeSH-normalised entities, grouped under 433,611 topic
  hyperedges. Six test sets covering licensing-exam QA, hallucination detection and a 100-case
  decision-support set. Average 82.4 against 79.1 without retrieval and 76.3 for GraphRAG
  (Qwen2.5-72B); nearly all of the margin is on decision support, and on the exam sets no retrieval
  method helps. The stated limitation is the honest one: the system retrieves evidence but does
  not grade its quality, which is half of what evidence-based medicine means. The released data
  link was dead on 2026-09-21.

Details, costs and caveats are in [retrieval-augmented-generation](retrieval-augmented-generation.md).
The caveats apply with extra force in medicine, where LLM-as-a-judge scoring is a poor proxy for
clinical correctness.

## 7. Summary of the evidence

| Claim | Strength |
|---|---|
| Metabolic/signalling reactions are directed hyperedges | Established; standard in systems biology since 2009 |
| Pairwise projection distorts pathway connectivity | Strong, quantified on Reactome (2019) |
| Protein complexes need set semantics | Established, with a worked k-core counterexample |
| Higher-order drug combinations exist and matter | Good data (HODDI); modelling results mixed |
| Hypergraph contextualisation of EHR + KG helps prediction | Single paper, peer-reviewed venue |
| Hypergraph RAG helps clinical QA | Several papers, all from proponents, LLM-judged |

## Sources

- Klamt, S., Haus, U.-U., Theis, F. *Hypergraphs and Cellular Networks.* PLoS Computational Biology 5(5):e1000385, 2009. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000385
- Franzese, N., Groce, A., Murali, T. M., Ritz, A. *Hypergraph-based connectivity measures for signaling pathway topologies.* PLoS Computational Biology 15(10):e1007384, 2019. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1007384
- Reactome, release 97 (30 June 2026), checked 2026-09-20. https://reactome.org/
- Zitnik, M., Agrawal, M., Leskovec, J. *Modeling polypharmacy side effects with graph convolutional networks.* Bioinformatics 34(13):i457–i466, ISMB 2018; arXiv:1802.00543. https://arxiv.org/abs/1802.00543
- Wang, Z., Shi, Y., Liu, X., Chen, C., Wen, J., Wang, R. *HODDI: A Dataset of High-Order Drug-Drug Interactions for Computational Pharmacovigilance.* arXiv:2502.06274, Feb 2025. https://arxiv.org/abs/2502.06274
- Xie, Y., Han, X., Xu, R., Hu, X., Lu, J., Yang, C. *HypKG: Hypergraph-based Knowledge Graph Contextualization for Precision Healthcare.* ISWC 2025; arXiv:2507.19726. https://arxiv.org/abs/2507.19726
- HypKG code repository, GitHub, checked 2026-09-20. https://github.com/constantjxyz/HypKG
- Chandak, P., Huang, K., Zitnik, M. *Building a knowledge graph to enable precision medicine.* Scientific Data, 2023. https://www.nature.com/articles/s41597-023-01960-3
- PrimeKG code repository, GitHub, checked 2026-09-20. https://github.com/mims-harvard/PrimeKG
- Luo, H. et al. *HyperGraphRAG.* NeurIPS 2025; arXiv:2503.21322. https://arxiv.org/abs/2503.21322
- Feng, Y. et al. *Hyper-RAG.* arXiv:2504.08758, 30 Mar 2025; *Nature Communications* 17(1):5778, 27 Apr 2026. https://arxiv.org/abs/2504.08758 ; https://doi.org/10.1038/s41467-026-71411-1
- Dou, C., Zhang, Y., Jin, Z., Jiao, W., Zhao, H., Zhao, Y., Tao, Z. *Enhancing LLM Generation with Knowledge Hypergraph for Evidence-Based Medicine.* arXiv:2503.16530, 18 Mar 2025. https://arxiv.org/abs/2503.16530
