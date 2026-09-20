---
title: The current research frontier — fifteen directions with 2024–2026 evidence
type: survey
status: draft
tags: [frontier, research-directions, foundation-models, neurosymbolic, temporal, inductive, standards, databases, topological-deep-learning, expressivity, benchmarks, multimodal, agents, evaluation, causality]
created: 2026-09-20
updated: 2026-09-20
---

# The current research frontier

A structured map of where knowledge-hypergraph research is active as of **2026-09-20**. Each
direction gives: the **claim** being pursued, **who** is pursuing it, **key papers** (2024–2026
unless a foundational older one is needed), and the **open problems** that a new project could
attack.

Directions are ordered roughly from most to least consolidated. History leading here:
[machine-learning-era.md](machine-learning-era.md) and [llm-era-2023-2026.md](llm-era-2023-2026.md).
People and affiliations: [research-groups-and-people.md](research-groups-and-people.md).

A caution before the list. Several of these directions rest on a small number of preprints, some
under review, and the field has a demonstrated benchmark problem (direction 11). Treat "state of the
art" claims as provisional.

---

## 1. Hypergraph foundation models

**Claim.** One pretrained model can serve many hypergraphs — different domains, different vertex
features, different arities — the way graph foundation models serve many graphs.

**Who.** Yue Gao and Yifan Feng's group at Tsinghua (Hyper-FM); Xingyue Huang, Mikhail Galkin,
Michael Bronstein and İsmail İlkan Ceylan (HYPER), continuing the ULTRA line.

**Key papers.**
- Gao, Feng, Liu, Han, Du, Wu, Hu, "Hypergraph Foundation Model," [arXiv:2503.01203](https://arxiv.org/abs/2503.01203)
  (3 Mar 2025); published *IEEE TPAMI* 48:4063–4080, April 2026
  ([DOI 10.1109/TPAMI.2025.3647504](https://doi.org/10.1109/TPAMI.2025.3647504)). Hierarchical
  vertex-knowledge embedding and multi-hypergraph structural extraction; 11 text-attributed
  hypergraph datasets; ~13.4% over baselines; the first proposed **scaling law for hypergraph
  models**, whose finding is that domain diversity beats raw size.
- Huang, Galkin, Bronstein, Ceylan, "HYPER," [arXiv:2506.12362](https://arxiv.org/abs/2506.12362)
  (14 Jun 2025) — see direction 4.
- Precursor: Galkin et al., ULTRA, [arXiv:2310.04562](https://arxiv.org/abs/2310.04562), ICLR 2024.

**Open problems.** Does the scaling law replicate on an independent corpus? What is the right
pretraining objective when hyperedges are unlabelled sets in one domain and typed facts in another?
Can one model span the *undirected/unlabelled* and the *relation-typed* hypergraph worlds
(the gap noted in [machine-learning-era.md](machine-learning-era.md) §6)? No public model weights or
shared pretraining corpus exist for hypergraphs comparable to the graph side.

---

## 2. LLM + knowledge-hypergraph neurosymbolic reasoning

**Claim.** A language model supplies language understanding and heuristic search; the hypergraph
supplies grounded, inspectable n-ary facts and a structure to plan over. Together they beat either
alone.

**Who.** Haoran Luo and collaborators (HyperGraphRAG; Luo now a research fellow at NTU); Xiangjun
Zai, Xingyu Tan and co-authors (PRoH, DocTrace; affiliations `[unverified]`); Jinyoung Park and
co-authors (HyperGraphPro);
Ben Goertzel and the OpenCog Hyperon effort from the AGI side (metagraph + MeTTa rewriting).

**Key papers.**
- Luo et al., HyperGraphRAG, [arXiv:2503.21322](https://arxiv.org/abs/2503.21322), NeurIPS 2025.
- Zai, Tan, Wang, Liu, Xu, Zhang, PRoH, [arXiv:2510.12434](https://arxiv.org/abs/2510.12434),
  WWW 2026: context-aware planning with neighbourhood sketches, question decomposition into a
  dynamically evolving DAG, entity-weighted-overlap retrieval; +19.73% F1 over HyperGraphRAG.
- Park, Lee, Khan, Kim, Kim, HyperGraphPro, [arXiv:2601.17755](https://arxiv.org/abs/2601.17755)
  (25 Jan 2026): RL with progress-shaped dense rewards for multi-hop traversal.
- Goertzel et al., OpenCog Hyperon, [arXiv:2310.18318](https://arxiv.org/abs/2310.18318);
  metagraph rewriting, [arXiv:2112.08272](https://arxiv.org/abs/2112.08272).

**Open problems.** Nobody has shown that the *symbolic* component is load-bearing: ablations that
replace the hypergraph with a well-tuned dense retriever are rare. Faithfulness — does the answer
actually follow from the retrieved hyperedges? — is mostly unmeasured. Cost per query versus a flat
retriever is almost never reported.

---

## 3. Temporal and dynamic knowledge hypergraphs

**Claim.** Facts have validity intervals, and hyperedges appear, change arity and disappear; models
should represent that rather than snapshotting.

**Who.** Dingqi Yang and collaborators (formerly eXascale Infolab, University of Fribourg; now
University of Macau `[unverified]`) — VITA, THOR; the authors of "Temporal Fact Reasoning over
Hyper-Relational Knowledge Graphs"; and the higher-order network science community on temporal
hypergraphs as dynamical objects.

**Key papers.**
- Un, Lu, Yang, Yang, "VITA," [arXiv:2505.11803](https://arxiv.org/abs/2505.11803) (17 May 2025): one
  time representation covering *since / until / period / time-invariant*; reports up to 75.3% gains
  over baselines on link prediction.
- Hypergraphx-data ships weighted, directed, **temporal** and multiplex hypergraph datasets: Lotito,
  Betti, Nortier, Montresor, Battiston, [arXiv:2605.18166](https://arxiv.org/abs/2605.18166)
  (18 May 2026); *Journal of Complex Networks* 14, 5 May 2026
  ([DOI 10.1093/comnet/cnag014](https://doi.org/10.1093/comnet/cnag014)).
- Earlier: "Temporal Fact Reasoning over Hyper-Relational Knowledge Graphs,"
  [arXiv:2307.10219](https://arxiv.org/abs/2307.10219) (2023).

**Open problems.** No standard temporal n-ary benchmark with realistic validity intervals. Nothing
on *retraction* and belief revision over hyperedges. Streaming/incremental construction — the
practical need for any deployed KHG — is essentially untouched.

---

## 4. Inductive and zero-shot n-ary completion

**Claim.** A model should handle entities *and relations* it never saw in training, across
arities — the precondition for any transferable KHG system.

**Who.** Huang/Galkin/Bronstein/Ceylan (HYPER); Weijian Yu, Yuhuan Lu, Dingqi Yang (THOR); earlier,
Ali, Berrendorf, Galkin et al. on qualifiers helping inductive prediction (ISWC 2021 best paper).

**Key papers.**
- Huang, Galkin, Bronstein, Ceylan, "HYPER: A Foundation Model for Inductive Link Prediction with
  Knowledge Hypergraphs," [arXiv:2506.12362](https://arxiv.org/abs/2506.12362) (14 Jun 2025).
  Encodes each entity *with its position in the hyperedge*, which is what lets knowledge transfer
  between relations of different arity; 16 new inductive datasets. Workshop presentation at NeurIPS
  2025 ([page](https://neurips.cc/virtual/2025/127653)); the authors' repository states ICLR 2026
  ([GitHub](https://github.com/HxyScotthuang/HYPER)).
- Yu, Lu, Yang, "THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs,"
  [arXiv:2602.05424](https://arxiv.org/abs/2602.05424) (5 Feb 2026): relation and entity foundation
  graphs, parallel encoders, transformer decoder, masked training; 12 datasets; reports 20.4% over
  the best fully-inductive baseline.
- Ali et al., "Improving Inductive Link Prediction Using Hyper-Relational Facts,"
  [arXiv:2107.04894](https://arxiv.org/abs/2107.04894), ISWC 2021.

**Open problems.** The inductive datasets are constructed by the same groups that propose the
models. Cross-domain transfer (train on a biomedical KHG, test on a legal one) is untested. Role
semantics are not transferred — only positions — so a model has no way to know that "dosage" means
the same thing in two schemas.

---

## 5. Standards convergence for n-ary knowledge

**Claim.** There should be an interchange format *and* a query language for typed, role-labelled
hyperedges. Neither exists.

**Who.** W3C RDF & SPARQL WG (RDF 1.2 reifiers); ISO/IEC JTC1 SC32 (GQL, SQL/PGQ); the HIF authors
(Coll, Joslyn, Landry, Lotito, Myers, Pickard, Praggastis, Szufel); LDBC (PG-Schema, LEX).

**Key documents.** See [standards-convergence.md](standards-convergence.md) for the full table.
Headlines: RDF 1.2 Concepts/Semantics at **Candidate Recommendation, 7 Apr 2026**; **ISO/IEC
39075:2024 GQL** published 12 Apr 2024 with a property-graph model that explicitly excludes n-ary
relationships; **HIF** in *Network Science* 13:e21, 2025.

**Open problems.** A schema language for hyperedges (types, roles, cardinalities) that is not
TypeDB-specific. A query algebra over role-labelled hyperedges with a cost model. A conformance
suite. Round-tripping between HIF and RDF 1.2 without loss. Whether GQL's second edition can admit
arity at all.

---

## 6. Scalable hypergraph databases

**Claim.** Hyperedges can be a *native* storage and indexing primitive with transactional
guarantees, not an emulation on top of a triple or property-graph store.

**Who.** Maciej Besta, Torsten Hoefler and co-authors at ETH Zürich `[unverified]` (higher-order
graph databases);
TypeDB (Haikal Pribadi's company, Rust rewrite since 3.0); HypergraphDB (Borislav Iordanov, the
2010 ancestor).

**Key papers and systems.**
- Besta, Chandran, Cudak, Iff, Copik, Gerstenberger, Szydlo, Müller, Hoefler, "Higher-Order Graph
  Databases," [arXiv:2506.19661](https://arxiv.org/abs/2506.19661) (24 Jun 2025). Proposes HO-GDBs
  with "lifting and lowering paradigms" to extend ordinary graph databases with native hypergraphs,
  node-tuples and subgraphs, with OLTP/OLAP guarantees and ACID compliance; reports a 44% GNN
  accuracy improvement in-database.
- TypeDB: entity–relation–attribute type system where a relation `relates` several roles; stable
  release 3.13.0 on 8 Sep 2026, MPL-2.0
  ([Wikipedia, TypeDB](https://en.wikipedia.org/wiki/TypeDB), checked 2026-09-20).
- Iordanov, "HyperGraphDB: A Generalized Graph Database," WAIM 2010 Workshops
  ([Springer](https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3)).

**Open problems.** No published benchmark comparing a native hyperedge store against (a) a
relational store of the same n-ary facts and (b) a reified triple store, on the same workload. No
standard index structure for variable-arity role-labelled edges. Nothing public on distributed
hyperedge partitioning for *knowledge* workloads, despite thirty years of VLSI partitioning theory
that ought to apply ([origins-hypergraph-theory.md](origins-hypergraph-theory.md) §3).

---

## 7. Higher-order network science meets knowledge representation

**Claim.** The structural and dynamical results of higher-order network science (hyper-cores,
higher-order homophily, group contagion, simplicial closure) apply to *knowledge* hypergraphs, not
only to social and biological ones.

**Who.** Federico Battiston (Central European University) and the Hypergraphx group; Nicholas Landry
(University of Virginia), Iacopo Iacopini (Northeastern University London), Alice Patania
(University of Vermont), Maxime Lucas, Leo Torres and the XGI team; Phil Chodrow (Middlebury
College — a separate node in the same community, **not** an XGI author or core developer); PNNL's hypernetwork-science group; Tina Eliassi-Rad and Kijung Shin on hypergraph mining.
Affiliations and caveats: [research-groups-and-people.md](research-groups-and-people.md).

**Key papers.**
- Lee, Bu, Eliassi-Rad, Shin, "A Survey on Hypergraph Mining: Patterns, Tools, and Generators,"
  *ACM CSUR* 57, 24 Mar 2025 ([DOI 10.1145/3719002](https://doi.org/10.1145/3719002)).
- Bick, Gross, Harrington, Schaub, "What Are Higher-Order Networks?" *SIAM Review* 65(3), 2023
  ([DOI 10.1137/21M1414024](https://doi.org/10.1137/21M1414024)).
- Hypergraphx-data, [arXiv:2605.18166](https://arxiv.org/abs/2605.18166) /
  [DOI 10.1093/comnet/cnag014](https://doi.org/10.1093/comnet/cnag014) (2026).

**Open problems.** Knowledge hypergraphs have *typed, directed, role-labelled* edges; almost every
network-science measure assumes untyped undirected ones. What is a hyper-core, a modularity, or a
homophily coefficient on a knowledge hypergraph? Nobody has systematically transferred these
measures, and the benchmark datasets on each side do not overlap at all.

---

## 8. Topological deep learning

**Claim.** Hypergraphs are one point in a lattice of topological domains (simplicial, cell, path,
combinatorial complexes), and learning should be defined on the lattice rather than on any one
member.

**Who.** Mustafa Hajij (University of San Francisco) and the pyt-team/TopoX consortium; Theodore
Papamarkou, Tolga Birdal, Michael Bronstein, Gunnar Carlsson, Yue Gao and 17 co-authors on the
position paper; Michael T. Schaub.

**Key papers.**
- Hajij, Papillon, Frantzen et al., "TopoX," [arXiv:2402.02441](https://arxiv.org/abs/2402.02441)
  (4 Feb 2024); *JMLR* 25 ([paper page](https://jmlr.org/papers/v25/24-0110.html)).
- Papamarkou et al., "Position: Topological Deep Learning is the New Frontier for Relational
  Learning," ICML 2024, PMLR 235 ([arXiv:2402.08871](https://arxiv.org/abs/2402.08871)).

**Open problems.** Almost no contact with *knowledge* hypergraphs: TDL benchmarks are molecules,
meshes and citation networks. Whether simplicial or cell structure buys anything on a fact base
(where a hyperedge's subsets are usually *not* also facts — the downward-closure assumption fails)
is an open and rather sceptical question.

---

## 9. Expressivity theory for hypergraph models

**Claim.** There are provable limits on what hypergraph neural networks can distinguish, and those
limits have a clean combinatorial index.

**Who.** Xingyue Huang, Miguel Romero Orth, Pablo Barceló, Michael Bronstein, İsmail İlkan Ceylan
(relational Weisfeiler–Leman); Fengqing Jiang, Radha Poovendran and co-authors (WidthWall;
affiliations `[unverified]`).

**Key papers.**
- Huang, Romero Orth, Barceló, Bronstein, Ceylan, "Link Prediction with Relational Hypergraphs,"
  [arXiv:2402.04062](https://arxiv.org/abs/2402.04062) (6 Feb 2024).
- Jiang, Li, Feng, Zheng, Niu, Ramasubramanian, Alomair, Bushnell, Poovendran, "The WidthWall: A
  Strict Expressivity Hierarchy for Hypergraph Neural Networks,"
  [arXiv:2605.13690](https://arxiv.org/abs/2605.13690) (13 May 2026). Homomorphism densities
  "generate all continuous hypergraph invariants and organize them into a strict hierarchy indexed
  by **hypertree width**"; unified characterisation of 15 HGNN architectures; precise account of
  what clique expansion loses; motivates density-aware models.

**Open problems.** The hierarchy is for *undirected, unlabelled* hypergraphs; the relation-typed
case is only partly covered. No corresponding theory for retrieval systems: what class of questions
does a hypergraph index answer that a binary one cannot? The link back to Fagin's α/β/γ-acyclicity
and to hypertree decompositions is suggestive and under-exploited.

---

## 10. Benchmarks and the evaluation crisis

**Claim (uncomfortable).** A large fraction of reported KHG progress may be measurement artefact.

**Who.** Galkin et al. raised it first (StarE, 2020); Yubo Wang, Shimin Di, Lei Chen and co-authors
(CIKM 2025); Zhishang Xiang, Jinsong Su and co-authors (GraphRAG-Bench); Rizhuo Huang, Yifan Feng,
Yue Gao (HyperDocRED, on the construction side).

**Key papers.**
- Galkin et al., StarE, EMNLP 2020: existing hyper-relational benchmarks "suffer from fundamental
  flaws," hence WD50K ([ACL Anthology](https://aclanthology.org/2020.emnlp-main.596/)).
- Wang, Di, Wang, Li, Teng, Xin, Chen, CIKM 2025,
  [arXiv:2508.03280](https://arxiv.org/abs/2508.03280): classical KG embedding on decomposed
  hyper-relational graphs matches specialised HKGE models.
- Xiang et al., "When to use Graphs in RAG," [arXiv:2506.05690](https://arxiv.org/abs/2506.05690),
  ICLR 2026: GraphRAG "frequently underperforms vanilla RAG"; stage-specific metrics.
- Huang et al., Hyper-KGGen / **HyperDocRED**,
  [arXiv:2602.19543](https://arxiv.org/abs/2602.19543) (23 Feb 2026): the first annotated
  document-level knowledge-hypergraph construction benchmark.

**Open problems.** Almost everything. A leakage audit of JF17K/WikiPeople/WD50K/FB-AUTO with modern
tooling (current state:
[../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md)). A benchmark not derived from the 2015 Freebase dump. Reporting conventions that force a
vanilla-retriever baseline and a compute budget. Separating construction error from retrieval error
from generation error. This is the highest-leverage unglamorous work in the field.

---

## 11. Multimodal knowledge hypergraphs

**Claim.** Hyperedges are a natural home for facts whose participants are images, tables, molecules
and text at once.

**Who.** Yanbin Wei, James Kwok and co-authors (HyperGVL); Jiashi Lin, Junjun He and co-authors
(EvoGraph-R1); Yue Gao's Tsinghua group (multi-modal hyperedge groups since HGNN⁺).

**Key papers.**
- Wei et al., "HyperGVL," [arXiv:2604.15648](https://arxiv.org/abs/2604.15648) (17 Apr 2026): 84k QA
  samples, 12 tasks, 12 vision-language models, and a systematic comparison of **12 textual and
  visual hypergraph representations** plus an adaptive routing method (WiseHyGR). Under review.
- Lin et al., "EvoGraph-R1: Self-Evolving Multimodal Knowledge Hypergraphs for Agentic Retrieval,"
  [arXiv:2607.12764](https://arxiv.org/abs/2607.12764) (14 Jul 2026), CVPR 2026.
- Lei et al., "Hypergraph as Language" (Hyper-Align),
  [arXiv:2605.21858](https://arxiv.org/abs/2605.21858) (21 May 2026).

**Open problems.** No multimodal n-ary *fact* benchmark (HyperGVL tests structural reasoning about
hypergraphs, not multimodal knowledge). Entity resolution across modalities. Whether a drawn
hypergraph is ever a better input to a model than a serialised one — HyperGVL is the only systematic
evidence, and it is one paper. See
[../06-visualization/visual-encodings-catalogue.md](../06-visualization/visual-encodings-catalogue.md).

---

## 12. Knowledge hypergraphs as agent memory

**Claim.** The hypergraph's real niche may not be a curated knowledge base at all but the *working
and skill memory an agent writes during a task*.

**Who.** Juwei Yue and colleagues (HyperMem, ACL 2026); Xiangjun Zai and colleagues (DocTrace);
Ruiyao Xu, Tiankai Yang, Wei-Chieh Huang (HyperSkill).

**Key papers.**
- Yue et al., "HyperMem," [arXiv:2604.08256](https://arxiv.org/abs/2604.08256), ACL 2026 Main
  ([anthology](https://aclanthology.org/2026.acl-long.1627/)): topics → episodes → facts with
  hyperedges grouping episodes; 92.73% LLM-as-a-judge accuracy on LoCoMo.
- Zai et al., DocTrace, [arXiv:2606.10921](https://arxiv.org/abs/2606.10921) (9 Jun 2026): hypergraph
  working memory built **on demand during reasoning**, plus graph-based experience memory.
- Xu, Yang, Huang, HyperSkill, [arXiv:2608.16114](https://arxiv.org/abs/2608.16114) (17 Aug 2026):
  hyperedges linking subtasks and reusable skills per trajectory; dual-path retrieval;
  quality-weighted hypergraph propagation for pruning and merging.

**Open problems.** No shared agent-memory benchmark where the memory *structure* is the independent
variable. Forgetting, compaction and conflict resolution in a hypergraph memory. Whether the
hyperedge is doing work or whether a flat episodic store with good retrieval matches it.

---

## 13. Hypergraph RAG evaluation and construction quality

**Claim (methodological).** The bottleneck in hypergraph RAG is the LLM extraction step, and current
evaluation cannot see it.

**Who.** Houda Khrouf and colleagues; Jiate Liu and colleagues (HyperSU); the Hyper-KGGen authors.

**Key papers.**
- Khrouf, Fillastre, Correia, "Optimizing Hypergraph-Based RAG,"
  [arXiv:2607.20506](https://arxiv.org/abs/2607.20506) (2 Jul 2026), APIA 2026: HyperGraphRAG
  "relies on error-prone LLM extraction and inefficient standard chunk retrieval"; self-consistency
  prompting and Personalized PageRank as fixes.
- Liu et al., HyperSU, [arXiv:2606.28351](https://arxiv.org/abs/2606.28351) (3 Jun 2026): hyperedge
  formation as an entity-aware **minimum-description-length** optimisation — a principled criterion
  for "what is one hyperedge"; up to 14.7% relative accuracy gain on GraphRAG-Bench.
- Huang et al., HyperDocRED, [arXiv:2602.19543](https://arxiv.org/abs/2602.19543).

**Open problems.** An agreed definition of hyperedge *granularity* (MDL is one proposal among none).
Inter-annotator agreement studies for n-ary fact annotation. Incremental re-extraction when the
corpus changes. Provenance from hyperedge back to span. See
[../03-construction/construction-pipeline-overview.md](../03-construction/construction-pipeline-overview.md).

---

## 14. Hypergraph generation and serialisation for language models

**Claim.** If a model is to read or write hypergraphs, the hypergraph needs a *linguistic* form, and
the choice of form is a first-class research variable.

**Who.** Mengqi Lei, Yue Gao and colleagues (Hyper-Align); the HyperGVL authors on representation
comparison.

**Key papers.**
- Lei, Xie, Ying, Du, Yong, Shi, Tian, Li, Gao, "Hypergraph as Language,"
  [arXiv:2605.21858](https://arxiv.org/abs/2605.21858) (21 May 2026, revised 15 Aug 2026):
  "Hypergraph Incidence Detail Template with Overview" for serialisation, a "Hypergraph Incidence
  Projector" mapping structure into token space, and HyperAlign-Bench; gains on standard and
  zero-shot tasks.
- Wei et al., HyperGVL ([arXiv:2604.15648](https://arxiv.org/abs/2604.15648)) — 12 representations
  compared.

**Open problems.** Nothing on *generation*: sampling a plausible hypergraph from a model, with
constraints. Tokenisation cost for large hypergraphs. Whether an incidence-list serialisation, a
HIF JSON document, or a drawing is the best input — and whether that depends on the task.

---

## 15. Causal hypergraphs

**Claim.** Causal structure is not always pairwise: a set of causes may act jointly, and the right
object is a directed acyclic **hypergraph**.

**Who.** Small, new, and mostly outside the KHG community: Alessio Zanga, Marco Scutari, Fabio
Stella; the higher-order causal-structure-learning authors; scattered applied groups.

**Key papers.**
- Zanga, Scutari, Stella, "Causal Discovery on Higher-Order Interactions,"
  [arXiv:2511.14206](https://arxiv.org/abs/2511.14206) (Nov 2025): higher-order structures for DAG
  aggregation from bootstrapped DAGs.
- "Higher-Order Causal Structure Learning with Additive Models,"
  [arXiv:2511.03831](https://arxiv.org/abs/2511.03831) (Nov 2025): causal additive models extended to
  higher-order interactions represented by **directed acyclic hypergraphs**, with identifiability
  results generalising Markov equivalence classes.
- "Information-theoretic signatures of causality in Bayesian networks and hypergraphs,"
  [arXiv:2512.20552](https://arxiv.org/abs/2512.20552) (Dec 2025): partial-information-decomposition
  signatures distinguishing parents, children, co-heads and co-tails in Bayesian hypergraphs.

**Open problems.** No connection at all to knowledge hypergraphs yet: causal hypergraph work is on
variables and distributions, KHG work is on entities and facts. Whether a KHG's hyperedges can carry
causal semantics, and what identifiability would even mean there, is wide open. Note also that this
is the least consolidated direction on the list — three preprints, no survey, no benchmark.

---

## Cross-cutting gaps (what nobody is doing)

These are the holes visible from the map rather than from inside any one direction, and they are the
most promising starting points for a project:

1. **A fair, three-way comparison**: native hyperedge store vs. reified triple store vs. relational
   tables, same facts, same workload, cost and latency reported.
2. **Transferring network-science structure measures to typed, directed knowledge hypergraphs**
   (direction 7).
3. **Provenance, retraction and versioning** for hyperedges — required by every serious application,
   absent from every paper surveyed here.
4. **A benchmark not descended from Freebase 2015.**
5. **A schema + query standard for role-labelled hyperedges** (direction 5).
6. **Human factors**: is an n-ary fact easier or harder for a person to curate, review and debug
   than the equivalent reified triples? No study found.

New questions raised by this survey should be added to `kb/00-index/open-questions.md` tagged `08`.

## Sources

- Gao, Y., Feng, Y., Liu, S., Han, X., Du, S., Wu, Z., Hu, H. "Hypergraph Foundation Model." arXiv:2503.01203; *IEEE TPAMI* 48:4063–4080, Apr 2026. https://doi.org/10.1109/TPAMI.2025.3647504
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. "HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs." arXiv:2506.12362, 14 Jun 2025. https://arxiv.org/abs/2506.12362 ; https://github.com/HxyScotthuang/HYPER ; https://neurips.cc/virtual/2025/127653
- Galkin, M. et al. "Towards Foundation Models for Knowledge Graph Reasoning" (ULTRA). arXiv:2310.04562; ICLR 2024. https://arxiv.org/abs/2310.04562
- Luo, H. et al. "HyperGraphRAG." arXiv:2503.21322; NeurIPS 2025. https://arxiv.org/abs/2503.21322
- Zai, X., Tan, X., Wang, X., Liu, Q., Xu, X., Zhang, W. "PRoH." arXiv:2510.12434; WWW 2026. https://arxiv.org/abs/2510.12434
- Park, J., Lee, S., Khan, O. Z., Kim, H. J., Kim, J.-K. "HyperGraphPro." arXiv:2601.17755, 25 Jan 2026. https://arxiv.org/abs/2601.17755
- Goertzel, B. et al. "OpenCog Hyperon: A Framework for AGI at the Human Level and Beyond." arXiv:2310.18318. https://arxiv.org/abs/2310.18318 ; Goertzel, B. "Reflective Metagraph Rewriting as a Foundation for an AGI 'Language of Thought'." arXiv:2112.08272. https://arxiv.org/abs/2112.08272
- Un, C., Lu, Y., Yang, T., Yang, D. "VITA." arXiv:2505.11803, 17 May 2025. https://arxiv.org/abs/2505.11803
- "Temporal Fact Reasoning over Hyper-Relational Knowledge Graphs." arXiv:2307.10219. https://arxiv.org/abs/2307.10219
- Lotito, Q. F., Betti, L., Nortier, B., Montresor, A., Battiston, F. "Hypergraphx-data: a repository for higher-order network data." arXiv:2605.18166, 18 May 2026; *Journal of Complex Networks* 14, 2026. https://doi.org/10.1093/comnet/cnag014
- Yu, W., Lu, Y., Yang, D. "THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs." arXiv:2602.05424, 5 Feb 2026. https://arxiv.org/abs/2602.05424
- Ali, M., Berrendorf, M., Galkin, M., Thost, V., Ma, T., Tresp, V., Lehmann, J. "Improving Inductive Link Prediction Using Hyper-Relational Facts." ISWC 2021; arXiv:2107.04894. https://arxiv.org/abs/2107.04894
- W3C. "RDF 1.2 Concepts and Abstract Data Model." CR Snapshot, 7 Apr 2026. https://www.w3.org/TR/rdf12-concepts/
- ISO/IEC 39075:2024 GQL. https://www.iso.org/standard/76120.html
- Coll, M. et al. "HIF: The hypergraph interchange format for higher-order networks." *Network Science* 13:e21, 2025. https://doi.org/10.1017/nws.2025.10018
- Besta, M., Chandran, S., Cudak, J., Iff, P., Copik, M., Gerstenberger, R., Szydlo, T., Müller, J., Hoefler, T. "Higher-Order Graph Databases." arXiv:2506.19661, 24 Jun 2025. https://arxiv.org/abs/2506.19661
- Wikipedia. "TypeDB" (checked 2026-09-20). https://en.wikipedia.org/wiki/TypeDB
- Iordanov, B. "HyperGraphDB: A Generalized Graph Database." WAIM 2010 Workshops. https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3
- Lee, G., Bu, F., Eliassi-Rad, T., Shin, K. "A Survey on Hypergraph Mining." *ACM CSUR* 57, 2025. https://doi.org/10.1145/3719002
- Bick, C., Gross, E., Harrington, H. A., Schaub, M. T. "What Are Higher-Order Networks?" *SIAM Review* 65(3), 2023. https://doi.org/10.1137/21M1414024
- Hajij, M. et al. "TopoX." arXiv:2402.02441; *JMLR* 25, 2024. https://jmlr.org/papers/v25/24-0110.html
- Papamarkou, T. et al. "Position: Topological Deep Learning is the New Frontier for Relational Learning." ICML 2024. https://arxiv.org/abs/2402.08871
- Huang, X., Romero Orth, M., Barceló, P., Bronstein, M. M., Ceylan, İ. İ. "Link Prediction with Relational Hypergraphs." arXiv:2402.04062. https://arxiv.org/abs/2402.04062
- Jiang, F. et al. "The WidthWall: A Strict Expressivity Hierarchy for Hypergraph Neural Networks." arXiv:2605.13690, 13 May 2026. https://arxiv.org/abs/2605.13690
- Galkin, M. et al. "Message Passing for Hyper-Relational Knowledge Graphs" (StarE). EMNLP 2020. https://aclanthology.org/2020.emnlp-main.596/
- Wang, Y. et al. "Understanding the Embedding Models on Hyper-relational Knowledge Graph." CIKM 2025; arXiv:2508.03280. https://arxiv.org/abs/2508.03280
- Xiang, Z. et al. "When to use Graphs in RAG." arXiv:2506.05690; ICLR 2026. https://arxiv.org/abs/2506.05690
- Huang, R. et al. "Hyper-KGGen" (with HyperDocRED). arXiv:2602.19543, 23 Feb 2026. https://arxiv.org/abs/2602.19543
- Wei, Y. et al. "HyperGVL." arXiv:2604.15648, 17 Apr 2026. https://arxiv.org/abs/2604.15648
- Lin, J. et al. "EvoGraph-R1." arXiv:2607.12764, 14 Jul 2026; CVPR 2026. https://arxiv.org/abs/2607.12764
- Lei, M. et al. "Hypergraph as Language." arXiv:2605.21858, 21 May 2026. https://arxiv.org/abs/2605.21858
- Yue, J. et al. "HyperMem: Hypergraph Memory for Long-Term Conversations." arXiv:2604.08256; ACL 2026 Main. https://aclanthology.org/2026.acl-long.1627/
- Zai, X. et al. "Trace Only What You Need" (DocTrace). arXiv:2606.10921, 9 Jun 2026. https://arxiv.org/abs/2606.10921
- Xu, R., Yang, T., Huang, W.-C. "HyperSkill." arXiv:2608.16114, 17 Aug 2026. https://arxiv.org/abs/2608.16114
- Khrouf, H., Fillastre, P., Correia, S. "Optimizing Hypergraph-Based RAG." arXiv:2607.20506, 2 Jul 2026; APIA 2026. https://arxiv.org/abs/2607.20506
- Liu, J. et al. "HyperSU." arXiv:2606.28351, 3 Jun 2026. https://arxiv.org/abs/2606.28351
- Zanga, A., Scutari, M., Stella, F. "Causal Discovery on Higher-Order Interactions." arXiv:2511.14206, Nov 2025. https://arxiv.org/abs/2511.14206
- "Higher-Order Causal Structure Learning with Additive Models." arXiv:2511.03831, Nov 2025. https://arxiv.org/abs/2511.03831
- "Information-theoretic signatures of causality in Bayesian networks and hypergraphs." arXiv:2512.20552, Dec 2025. https://arxiv.org/abs/2512.20552
