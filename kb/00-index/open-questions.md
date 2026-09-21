---
title: Open questions
type: question
status: reviewed
tags: [index, open-questions, research-agenda]
created: 2026-09-20
updated: 2026-09-21
---

# Open questions

The register of questions the research raised and did not answer. Part A groups them into eight
cross-cutting themes, each with the experiment or search that would settle it. Part B lists the
questions by the section that raised them. Part C maps the most tractable ones to candidate
projects. Add new questions at the end of the relevant section list with the date and the note that
raised them.

Convention: **[NN.k]** is question k raised by section NN; the notes cited are where the evidence sits.

## Part A — Cross-cutting themes

### Theme 1 — Is the hyperedge doing any work?

The sharpest question in the KB. Kok and Domingos gave essentially today's definition of a knowledge
hypergraph in 2009 without the name; every hypergraph is a bicoloured bipartite graph; the flagship
hypergraph-RAG system stores a bipartite graph and gains more on binary than on n-ary questions.

- **[10.1]** Is there any result (complexity separation, learnability bound, index structure) that holds of knowledge hypergraphs but not of arbitrary sets of ground atoms? If not, "knowledge hypergraph" is a programme label, not a technical term. See [open debates](../10-comparative-and-critique/open-debates.md), [semantic-web hypergraph view](../02-knowledge-representation/semantic-web-hypergraph-view.md).
- **[10.2] [07.1] [03.2]** Does an arity ablation reproduce the hypergraph-RAG gains? Same pipeline, hyperedges split into pairwise edges, and a "keep the whole fact sentence as one chunk" baseline. Nobody has run either. Gains are currently larger on binary-source questions (+8.6 F1) than n-ary ones (+5.3). See [critical reading of hypergraph-RAG claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md), [retrieval-augmented generation](../07-applications/retrieval-augmented-generation.md).
- **[02.4]** Does decomposition to binary cost accuracy in link prediction? Fatemi et al. say yes; Wang et al. (CIKM 2025) find decomposed standard models competitive. Confounded by the JF17K leak. See [hyper-relational vs n-ary vs hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).
- **[08.1] [04.2]** Does a native hyperedge store beat (a) reified triples and (b) plain relational tables holding the same n-ary facts, on the same workload, with cost and latency reported? No three-way comparison exists. See [hypergraph databases](../04-storage-and-formats/hypergraph-databases.md), [format recommendations](../04-storage-and-formats/format-recommendations.md).
- **[10.3]** Do hypergraph and *bipartite* null models disagree, or only hypergraph versus *projected-graph* models? See [hypergraph vs bipartite graph debate](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md).

**What would settle it:** one repository that holds the same n-ary facts as an incidence table, as reified triples, as a bipartite property graph and as a HIF hypergraph, and runs the same query, link-prediction and RAG workloads over each with cost logged. This is candidate project P1 below.

### Theme 2 — Roles are the missing primitive

Every section found that role labels (which participant plays which part in a fact) are what makes
a hypergraph a *knowledge* hypergraph, and that nothing in the stack carries them: not the
interchange format, not the learning libraries, not the walk theory, not the visualisation tools.

- **[01.2]** Chitra and Raphael's edge-dependent vertex weights are the cheapest repair that makes a hypergraph walk genuinely higher-order. A KHG has a role label per incidence. Is there a principled map from roles to incidence weights, and does the resulting walk beat clique expansion on KHG tasks? See [random walks and spectral theory](../01-foundations/random-walks-spectral-and-expansion.md).
- **[04.4]** Every hypergraph-learning library takes a 0/1 incidence matrix. What tensor encoding carries role-labelled incidences and still supports the standard Laplacian operators? See [tensor and sparse representations](../04-storage-and-formats/tensor-and-sparse-representations.md).
- **[09.5] [10.4]** Would a versioned HIF schema plus a `roles` convention on incidence attributes make HIF a knowledge-hypergraph format, or does it need a relation-type and schema layer that no library has? Can it gain roles, types and provenance without becoming RDF? See [HIF](../04-storage-and-formats/hif-hypergraph-interchange-format.md), [standards bodies](../09-ecosystem/standards-bodies-and-specifications.md).
- **[01.1] [08.3]** Higher-order motif analysis, hyper-cores, modularity and homophily are all defined on untyped, undirected hyperedges. What do they become on typed, directed, role-labelled facts, and does a typed motif census separate knowledge bases the way untyped profiles separate social hypergraphs? See [higher-order interactions](../01-foundations/higher-order-interactions.md), [current frontier directions](../08-history-and-frontier/current-frontier-directions.md).
- **[03.3]** Can role signatures be induced at LLM scale? Tensor methods work on small corpora; web-scale pipelines induce concepts, not roles. See [schema induction and ontology alignment](../03-construction/schema-induction-and-ontology-alignment.md).
- **[06.2]** Do role labels help or hurt readers of a hypergraph drawing, and at what density do they become noise? Every KHG tool shows them; nobody has measured. See [perception and evaluation studies](../06-visualization/perception-and-evaluation-studies.md).

**What would settle it:** a small role-aware extension to HIF, a role-weighted incidence tensor in one learning library, and a reader study. Candidate projects P2 and P5.

### Theme 3 — The evidence base is weak

The gap-filling pass confirmed that no replication study of n-ary link prediction exists, that neither of the two standard KG-embedding frameworks supports qualifiers or n-ary facts, and that six published models have no public implementation. It added **[05.6]** (de-leaked JF17K against a tuned classical baseline) and **[03.6]** (agreement as a function of arity). See [reproducibility of n-ary link prediction](../05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md).

- **[08.4]** Is there an n-ary completion benchmark not descended from the 2015 Freebase dump, and what happens to the 2016 to 2025 gains when one exists? JF17K leaks 44.5% of test main triples into training and has no validation split; WikiPeople is under 3% hyper-relational after literal filtering. See [benchmarks derived from Freebase and Wikidata](../02-knowledge-representation/benchmarks-derived-from-freebase-and-wikidata.md), [dataset quality and leakage](../09-ecosystem/dataset-quality-and-leakage-issues.md).
- **[09.3]** Does any replication study of n-ary link prediction exist, the analogue of the triple-based reproducibility literature? None was found. See [benchmarks and evaluation protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).
- **[07.2]** Would a hypergraph-RAG system survive GraphRAG-Bench? The benchmark is public and contains zero occurrences of "hypergraph". See [critical reading of hypergraph-RAG claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md).
- **[07.3]** Is there a knowledge-hypergraph analogue of higher-order link prediction under Benson et al.'s LLM-free, temporally split protocol? Predicting the missing participant of an n-ary fact under that protocol would be a real benchmark. See [hypergraph algorithms for knowledge](../05-query-embeddings-reasoning/hypergraph-algorithms-for-knowledge.md).
- **[05.4]** Are n-ary link predictors more miscalibrated at higher arity, given that MRR averages over prediction tasks and so reweights by arity? No calibration study exists. See [explainability and uncertainty](../05-query-embeddings-reasoning/explainability-and-uncertainty.md).
- **[02.2]** Is there a public uncertain n-ary benchmark? Every uncertain KG in use is binary. See [open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).
- **[07.5]** Where is the public benchmark of role-labelled financial or legal n-ary facts, the domain with the best structural argument and the least public data? See [finance, legal and compliance](../07-applications/finance-legal-and-compliance.md).
- **[06.4]** What is the visualisation benchmark? "No established benchmark dataset, no established performance metrics" still holds. See [perception and evaluation studies](../06-visualization/perception-and-evaluation-studies.md).
- **[09.4]** What is UltraDomain's canonical location and licence? Three of HyperGraphRAG's five evaluation domains derive from it. See [datasets and benchmarks](../09-ecosystem/datasets-and-benchmarks.md).

**What would settle it:** a clean, leak-free, arity-stratified, versioned n-ary benchmark with a documented licence, and a replication of two or three published models on it. Candidate project P3.

### Theme 4 — What is a fact's identity when its arity changes?

The gap-filling pass added a governance angle: **[10.6]** erasure semantics for an n-ary fact and **[10.7]** whether a whole hyperedge is more re-identifying than its reification. Both turn on the same unanswered question of what the unit of a fact is. See [privacy, licensing and governance](../10-comparative-and-critique/privacy-licensing-and-governance.md).

- **[03.1] [04.3] [03.4]** When `r(a,b)` and `r(a,b,t)` are extracted from different documents, is the second a refinement, a distinct fact, or a contradiction? If an arity-4 fact becomes arity-5, is it the same fact? What is the delta unit for a versioned hypergraph? No system, format or benchmark has an opinion, and the answer determines incremental construction, archive formats and provenance. See [incremental and streaming construction](../03-construction/incremental-and-streaming-construction.md), [versioning, provenance and scale](../04-storage-and-formats/versioning-provenance-and-scale.md).
- **[02.1]** Is there a partial-completeness or local-closed-world assumption for n-ary facts? AMIE's assumption is stated for binary relations and its n-ary generalisation is ambiguous. See [open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).
- **[02.5]** What does a weight on a reifier mean? No semantics exists for probabilistic hyper-relational facts where the qualifiers are about, rather than part of, the fact.
- **[03.5]** Can a shape language validate hypergraph incidence? SHACL Core cannot express Wikidata's own qualifier constraints; no SHACL or ShEx profile targets hyperedges. See [curation, crowdsourcing and quality](../03-construction/curation-crowdsourcing-and-quality.md).
- **[04.1] [09.2]** HIF has one schema version, no version field in files, and four schema URLs in circulation, one of which is its own `$id` returning 404. What happens on the first breaking revision, and which document is normative?

### Theme 5 — Bridges between theories that have not been built

- **[01.3]** Nobody has measured where real KHG schemas (Wikidata-style, biomedical) fall in Fagin's acyclicity hierarchy or what their hypertree width is; that number predicts query cost directly. See [hypergraph theory results](../01-foundations/hypergraph-theory-results.md), [n-ary relations and relational algebra](../01-foundations/n-ary-relations-and-relational-algebra.md).
- **[05.1]** Does the 2026 Width Wall expressivity hierarchy for hypergraph neural networks transfer to relational (labelled, positional) hypergraphs? Relational Weisfeiler–Leman and hypertree width have not been reconciled in one statement. See [hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).
- **[05.5]** Can hypertree-decomposition query planning be made practical over an incidence index rather than a relational one? No engine exposes it. See [query languages for hypergraphs](../05-query-embeddings-reasoning/query-languages-for-hypergraphs.md).
- **[05.2]** Is there an "AMIE for hyperedges", rule mining at n-ary arity? Existing methods only weight predefined rules. See [logical reasoning and rules](../05-query-embeddings-reasoning/logical-reasoning-and-rules-over-n-ary-facts.md).
- **[05.3]** Can a hyperpath be extracted post hoc from a query-embedding model, joining the tractable symbolic explanation primitive (polynomial-delay hyperpath enumeration on B-hypergraphs) to the neural scorer?
- **[01.4]** Combinatorial complexes and recursive hypergraphs both encode facts about facts. Which is more expressive in practice, cheaper to store and query, and does the rank function's monotonicity ever bind on real qualifier structures? See [hypergraphs vs bipartite vs simplicial](../01-foundations/hypergraphs-vs-bipartite-vs-simplicial.md), [metagraphs, AtomSpace and HypergraphDB](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md).
- **[02.3]** Does a directed, role-labelled, nested formalism exist? Ubergraphs are undirected; metagraphs are ordered but not tail/head directed. See [directed and typed hyperedges](../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md).
- **[07.4]** Can chemistry and biology hypergraph algorithms (integer hyperflows, minimal hyperpaths, B-connectivity) transfer to knowledge hypergraphs? They are mature on reaction networks and unused on knowledge. See [chemistry and reaction networks](../07-applications/chemistry-and-reaction-networks.md), [biomedicine](../07-applications/biomedical-and-life-sciences.md).
- **[01.5] [04.5]** Is the connectivity metric the right partitioning objective for a distributed fact store where roles have different access frequencies, and is any production KHG sharded by hypergraph partitioning at all?
- **[08.2]** Does the hypergraph foundation model "scaling law" (domain diversity beats size) replicate on a corpus the authors did not curate?

### Theme 6 — Humans in the loop

- **[08.5]** Is an n-ary fact easier or harder for a person to curate, review and debug than the equivalent reified triples? This is the practical argument for KHGs and no human-factors study was found. See [curation, crowdsourcing and quality](../03-construction/curation-crowdsourcing-and-quality.md).
- **[06.1]** No study compares an incidence (bipartite) drawing against a region (Euler or hull) drawing of the *same* hypergraph on element-, set- and attribute-based tasks. The KB's central visual recommendation rests on information-theoretic, algorithmic and adoption arguments only. Cheap, publishable. See [knowledge-hypergraph-specific visualisation](../06-visualization/knowledge-hypergraph-specific-visualization.md).
- **[06.3]** Are 2D projections of hyperedge embeddings useful for exploration? No published evaluation. See [large-scale and interactive exploration](../06-visualization/large-scale-and-interactive-exploration.md).
- **[06.5]** Is there a readable encoding for nested facts? Region nesting fails past two or three levels; the incidence encoding makes nesting free and invisible.

### Theme 7 — Standards and community

- **[10.5]** Is the relation-instance pattern actually the bottleneck in real semantic-web projects, rather than vocabulary alignment or entity resolution? Twenty years of complaint have not moved RDF 1.2's design and nobody has measured. See [standards convergence](../08-history-and-frontier/standards-convergence.md).
- **[09.1]** Has any openCypher improvement proposal ever proposed hyperedges or n-ary relationships? The proposal archive was not searched.
- Two hypergraph communities (higher-order network science; knowledge representation and learning) measurably do not cite each other. What would a shared venue, dataset or format look like? See [venues and community events](../08-history-and-frontier/venues-and-community-events.md), [research groups and people](../08-history-and-frontier/research-groups-and-people.md).

### Theme 8 — Do the layers compose? (added 2026-09-21)

The second research pass arranged the frontier as one stack (extract → store → complete / algebra /
plan → generate and act → write back) and found that every published system implements two or three
layers and treats the rest as given. Two layer boundaries have never been crossed in one experiment.
See [the composed stack](../08-history-and-frontier/composed-stack-and-research-bets.md).

- **[08.6]** Does a planner's lift (PRoH over HyperGraphRAG) survive on an extracted, incomplete hypergraph that an inductive completer (HYPER-style) has filled? A completer has never been run under a retriever. See [hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md), [HYPER anatomy](../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md).
- **[08.7]** Can an embedding that implements relational algebra (ReAlE) be the query interface for an LLM planner, so the planner emits operators rather than English, and does that beat cosine retrieval on multi-hop questions? See [geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).
- **[08.8]** Is there one artefact on which extraction, inductive completion, retrieval and long-horizon memory can all be scored, and how do the four scores correlate? See [the composed stack](../08-history-and-frontier/composed-stack-and-research-bets.md) §3.
- **[08.9]** Do extraction skills (Hyper-KGGen) and agent procedural skills (HyperSkill) unify as typed hyperedges with arity and role constraints, and does typing reduce extraction instability? See [skill-driven extraction](../03-construction/skill-driven-extraction-and-the-scenario-gap.md), [AI agents memory and planning](../07-applications/ai-agents-memory-and-planning.md).

**What would settle it:** one pipeline that extracts, completes, plans and remembers over the same
corpus, scored on all four abilities. Candidate project P8.

## Part B — Questions by section

### 01 Foundations
1. [01.1] Typed motif census over role-labelled facts.
2. [01.2] Roles as edge-dependent vertex weights.
3. [01.3] Acyclicity class and hypertree width of real KHG schemas.
4. [01.4] Combinatorial complexes vs recursive hypergraphs for qualified facts.
5. [01.5] Role-weighted partitioning objective for sharding.

### 02 Knowledge representation
1. [02.1] Partial-completeness assumption for n-ary facts.
2. [02.2] Public uncertain n-ary benchmark; qualifier monotonicity as a probabilistic bound.
3. [02.3] A directed, role-labelled, nested formalism.
4. [02.4] Does decomposition to binary cost accuracy?
5. [02.5] Semantics of a weight on a reifier.

### 03 Construction
1. [03.1] Arity-conditional merging of extracted facts.
2. [03.2] Does n-ary structure help as a function of arity? No arity-stratified results anywhere.
3. [03.3] Role-signature induction at LLM scale.
4. [03.4] The delta unit for a versioned hypergraph.
5. [03.5] A shape language for hypergraph incidence.
6. [03.6] Does inter-annotator agreement fall with arity? Re-analysing the MEE raw annotations by argument count would answer it without new annotation. Raised 2026-09-20 by [human-in-the-loop annotation and cost](../03-construction/human-in-the-loop-annotation-and-cost.md).

### 04 Storage and formats
1. [04.1] HIF versioning on the first breaking change.
2. [04.2] Native hyperedge storage vs reified-node emulation, measured.
3. [04.3] Identity of a hyperedge whose membership changes.
4. [04.4] Role-labelled incidence tensors compatible with Laplacian operators.
5. [04.5] Incremental repartitioning of a live KHG.

### 05 Query, embeddings, reasoning
1. [05.1] Width Wall hierarchy on relational hypergraphs.
2. [05.2] Rule mining at n-ary arity.
3. [05.3] Post-hoc hyperpath extraction from query-embedding models.
4. [05.4] Calibration as a function of arity.
5. [05.5] Hypertree-decomposition planning over an incidence index.
6. [05.6] Does any hyper-relational model beat a well-tuned classical KG embedding on de-leaked JF17K, on native rather than decomposed data? Raised 2026-09-20 by [reproducibility of n-ary link prediction](../05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md).
7. [05.7] Are hypergraph neural networks structurally a poor fit for knowledge hypergraphs? HADES (2026) finds they degrade on heterophilic nodes joined by semantically diverse hyperedges, which is what a typed n-ary fact looks like. Raised 2026-09-20 by [reading the frontier, 2026 Q3](../08-history-and-frontier/reading-the-frontier-2026-q3.md).

### 06 Visualization
1. [06.1] Incidence vs region encodings on the same hypergraph, measured.
2. [06.2] Do role labels help or hurt readers?
3. [06.3] Hyperedge-embedding projections for exploration.
4. [06.4] A visualisation benchmark with roles, direction, time and provenance.
5. [06.5] A readable encoding for nested facts.

### 07 Applications
1. [07.1] Why are hypergraph-RAG gains larger on binary-source questions?
2. [07.2] Hypergraph RAG on GraphRAG-Bench.
3. [07.3] Higher-order link prediction protocol for knowledge hypergraphs.
4. [07.4] Transfer of reaction-network hypergraph algorithms.
5. [07.5] Public role-labelled financial or legal n-ary benchmark.

### 08 History and frontier
1. [08.1] Three-way store comparison with cost and latency.
2. [08.2] Replication of the hypergraph foundation-model scaling law.
3. [08.3] Higher-order network measures on typed, directed, role-labelled KHGs.
4. [08.4] An n-ary benchmark not descended from Freebase 2015.
5. [08.5] Human factors of curating n-ary facts vs reified triples.
6. [08.6] Planner lift on a completer-filled extracted hypergraph. Raised 2026-09-21 by [the composed stack](../08-history-and-frontier/composed-stack-and-research-bets.md).
7. [08.7] Relational-algebra embeddings as the planner's query interface. Raised 2026-09-21 by the same note.
8. [08.8] One artefact scoring extraction, completion, retrieval and memory. Raised 2026-09-21 by the same note.
9. [08.9] Extraction skills and agent skills as one typed-hyperedge object. Raised 2026-09-21 by the same note.

### 09 Ecosystem
1. [09.1] openCypher proposals for hyperedges.
2. [09.2] Which HIF schema document is normative.
3. [09.3] Replication studies of n-ary link prediction.
4. [09.4] UltraDomain's canonical location and licence.
5. [09.5] Minimal extension that makes HIF a KHG format.

### 10 Comparative and critique
1. [10.1] Any result that holds of KHGs but not of sets of ground atoms.
2. [10.2] Arity ablation of hypergraph-RAG gains.
3. [10.3] Hypergraph vs bipartite null models.
4. [10.4] HIF with roles, types and provenance without becoming RDF.
5. [10.5] Is the relation-instance pattern really the bottleneck?
6. [10.6] What are the correct erasure semantics for an n-ary fact? Removing one participant under a right-to-erasure request leaves three bad options: delete the fact, delete the incidence, or tombstone. No published system implements any. Raised 2026-09-20 by [privacy, licensing and governance](../10-comparative-and-critique/privacy-licensing-and-governance.md).
7. [10.7] Is a hyperedge measurably more re-identifying than its reification? An attribute-inference or k-anonymity attack on the same facts in both encodings has never been run. Raised 2026-09-20 by the same note.

## Part C — Candidate first projects

Each is small enough to start from this repository and would move at least one theme. They are
listed in `projects/README.md` as candidate vectors; none is started.

| Id | Project | Themes moved | Questions |
|---|---|---|---|
| P1 | **Format and store bake-off**: one small KHG (the `schemas/` sample, grown to a few hundred facts) held as incidence table, reified RDF 1.2, bipartite property graph, TypeDB, HIF; same queries; round-trip fidelity and latency logged | 1, 4 | 04.2, 08.1, 04.1, 09.2 |
| P2 | **Role-aware HIF**: a `roles` convention on incidence attributes, a validator, and loaders for XGI and HyperNetX that keep roles | 2 | 09.5, 10.4, 04.4 |
| P3 | **Clean n-ary benchmark and replication**: rebuild a leak-free, arity-stratified split from a recent Wikidata dump; replicate two models; report calibration by arity | 3 | 08.4, 09.3, 05.4, 02.4 |
| P4 | **Arity ablation of hypergraph RAG**: run one hypergraph-RAG system with hyperedges intact, split pairwise, and as whole-sentence chunks, on one public domain and on GraphRAG-Bench | 1, 3 | 10.2, 07.1, 07.2 |
| P5 | **Reader study**: incidence vs Euler drawing of the same KHG, with and without role labels | 2, 6 | 06.1, 06.2 |
| P6 | **Schema width survey**: compute acyclicity class and hypertree width for Wikidata qualifier schemas and one biomedical schema | 5 | 01.3, 05.5 |
| P7 | **Agent memory prototype**: a hypergraph memory for a small agent vs a flat vector store, with fact identity, arity-conditional merging rules and **valid-time on the hyperedge with supersession** made explicit (reframed 2026-09-21) | 4, 8 | 03.1, 04.3, 08.6 |
| P8 | **Four-ability evaluation suite**: one corpus scored on gold n-ary extraction, inductive completion of the extracted graph, high-arity-edge-ablated multi-hop retrieval, and a superseding memory trace; see [the composed stack](../08-history-and-frontier/composed-stack-and-research-bets.md) §3 (added 2026-09-21) | 3, 8 | 08.6, 08.7, 08.8, 08.9 |

## Sources

This file cites no external sources directly; every question links to the note that holds the
evidence and its `## Sources` section.
