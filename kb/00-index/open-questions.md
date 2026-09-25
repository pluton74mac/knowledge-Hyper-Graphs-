---
title: Open questions
type: question
status: reviewed
tags: [index, open-questions, research-agenda]
created: 2026-09-20
updated: 2026-09-25
---

# Open questions

The register of questions the research raised and did not answer. Part A groups them into eight
cross-cutting themes, each with the experiment or search that would settle it. Part B lists the
questions by the section that raised them. Part C maps the most tractable ones to candidate
projects. Add new questions at the end of the relevant section list with the date and the note that
raised them.

Convention: **[NN.k]** is question k raised by section NN; the notes cited are where the evidence sits.
When a project moves a question, the entry keeps its original wording and gains a dated status,
**Closed**, **Narrowed** or **Reframed**, with a link to the project folder (see
[the programme plan](../../projects/PLAN.md) §1).

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
  **Narrowed 2026-09-24 by [P2](../../projects/p2-role-aware-hif/); answered in part.** A convention compatible with the current HIF schema exists. `role-convention` 1.0.0 puts the role in `incidences[].attrs.role`, writes one incidence record per role binding (repeating the (edge, node) pair when a node has two roles or sits in both tail and head), and declares itself in `metadata`; it needs no schema change. Role-labelled files round-trip with roles intact through XGI 0.10.2 and HyperNetX 2.4.3 via P2's loaders, which build the library objects directly; the libraries' own HIF functions lose roles (XGI drops every incidence attribute; HyperNetX drops repeated pairs). The relation type travels as `attrs.relation` on the edge, and statuses, evidence and provenance as flat `khg-*` keys in `attrs` and `metadata`, with the relation-type schema referenced by id and hash (the `khg-hif/1.0.0` profile). So HIF can carry them without becoming RDF, but only for readers that know the profile: that is P2's design, not a measured adoption. Still open: whether upstream adopts the convention (proposal drafted, not yet filed), whether it accepts repeated pairs ([04.6]), and whether the libraries' own readers will keep roles ([09.6]). See [HIF §10](../04-storage-and-formats/hif-hypergraph-interchange-format.md), [software libraries §1](../09-ecosystem/software-libraries.md).
- **[01.1] [08.3]** Higher-order motif analysis, hyper-cores, modularity and homophily are all defined on untyped, undirected hyperedges. What do they become on typed, directed, role-labelled facts, and does a typed motif census separate knowledge bases the way untyped profiles separate social hypergraphs? See [higher-order interactions](../01-foundations/higher-order-interactions.md), [current frontier directions](../08-history-and-frontier/current-frontier-directions.md).
- **[05.17] [03.9]** No n-ary model uses a linguistic role inventory, and extraction skills are free text with no role constraints (added 2026-09-21). See [geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md), [skill-driven extraction](../03-construction/skill-driven-extraction-and-the-scenario-gap.md).
- **[03.3]** Can role signatures be induced at LLM scale? Tensor methods work on small corpora; web-scale pipelines induce concepts, not roles. See [schema induction and ontology alignment](../03-construction/schema-induction-and-ontology-alignment.md).
- **[06.2]** Do role labels help or hurt readers of a hypergraph drawing, and at what density do they become noise? Every KHG tool shows them; nobody has measured. See [perception and evaluation studies](../06-visualization/perception-and-evaluation-studies.md).

**What would settle it:** a small role-aware extension to HIF, a role-weighted incidence tensor in one learning library, and a reader study. Candidate projects P2 and P5.

**Update 2026-09-24:** the first of the three exists. [P2](../../projects/p2-role-aware-hif/) passed its gate with a role convention on HIF incidence attributes, a validator that rejects all 180 cases on its malformed list, and role-preserving loaders for XGI and HyperNetX: a record went repo format → HIF → XGI → HIF → HyperNetX → HIF → repo format with every role intact, identically under five hash seeds. It narrowed [09.5] and [10.4] and reframed [04.1] and [09.2] (Theme 4). Still to do: the owner files the upstream HIF proposal and publishes the package; the libraries keeping roles natively ([09.6]); a role-weighted incidence tensor ([04.4], which P2 did not address); and the reader study (P5).

### Theme 3 — The evidence base is weak

The gap-filling pass confirmed that no replication study of n-ary link prediction exists, that neither of the two standard KG-embedding frameworks supports qualifiers or n-ary facts, and that six published models have no public implementation. It added **[05.6]** (de-leaked JF17K against a tuned classical baseline) and **[03.6]** (agreement as a function of arity). See [reproducibility of n-ary link prediction](../05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md).

- **[08.4]** Is there an n-ary completion benchmark not descended from the 2015 Freebase dump, and what happens to the 2016 to 2025 gains when one exists? JF17K leaks 44.5% of test main triples into training and has no validation split; WikiPeople is under 3% hyper-relational after literal filtering. See [benchmarks derived from Freebase and Wikidata](../02-knowledge-representation/benchmarks-derived-from-freebase-and-wikidata.md), [dataset quality and leakage](../09-ecosystem/dataset-quality-and-leakage-issues.md).
- **[09.3]** Does any replication study of n-ary link prediction exist, the analogue of the triple-based reproducibility literature? None was found. See [benchmarks and evaluation protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).
- **[05.13] [07.9] [03.7]** Three run-02 findings on evidence quality: HYPER's reified-ULTRA baseline moved by a factor of 50 between preprint versions and nobody has re-run it; PRoH's "harder" 3–6 hop split is self-generated and scores higher than its 1–3 hop split; Hyper-KGGen's "top-heavy extraction" failure mode is asserted, not measured; and HyperDocRED, the only document-level n-ary benchmark, is not distributed (added 2026-09-21).
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

- **[07.10] [05.8] [03.8]** Where does validity sit on an n-ary fact, which roles form its key, and does insertion order change the extracted graph? The second pass found the only incremental extractor keys hyperedges without their participants, so an insert can silently promote a binary edge (added 2026-09-21). See [temporal hyperedges and editable agent memory](../07-applications/temporal-hyperedges-and-editable-agent-memory.md).
- **[03.1] [04.3] [03.4]** When `r(a,b)` and `r(a,b,t)` are extracted from different documents, is the second a refinement, a distinct fact, or a contradiction? If an arity-4 fact becomes arity-5, is it the same fact? What is the delta unit for a versioned hypergraph? No system, format or benchmark has an opinion, and the answer determines incremental construction, archive formats and provenance. See [incremental and streaming construction](../03-construction/incremental-and-streaming-construction.md), [versioning, provenance and scale](../04-storage-and-formats/versioning-provenance-and-scale.md).
- **[02.1]** Is there a partial-completeness or local-closed-world assumption for n-ary facts? AMIE's assumption is stated for binary relations and its n-ary generalisation is ambiguous. See [open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).
- **[02.5]** What does a weight on a reifier mean? No semantics exists for probabilistic hyper-relational facts where the qualifiers are about, rather than part of, the fact.
- **[03.5]** Can a shape language validate hypergraph incidence? SHACL Core cannot express Wikidata's own qualifier constraints; no SHACL or ShEx profile targets hyperedges. See [curation, crowdsourcing and quality](../03-construction/curation-crowdsourcing-and-quality.md).
- **[04.1] [09.2]** HIF has one schema version, no version field in files, and four schema URLs in circulation, one of which is its own `$id` returning 404. What happens on the first breaking revision, and which document is normative?
  **Reframed 2026-09-24 by [P2](../../projects/p2-role-aware-hif/).** The premise was partly wrong. The four URLs are one repository under three names (`pszufe/HIF_validators`, then `pszufe/HIF-standard`, then `HIF-org/HIF-standard`, the old names reached by redirect) and two schema files whose validation rules have been identical since 2024-10-03. The 404 `$id` is a stale path left by a rename on 2025-05-02. The version labels do conflict: the CHANGELOG says `v0.0`, the schema file `0.1.0`, the Zenodo releases v0.1.0 to v0.1.2, and the maintainers "v1". On which document is normative: the paper and the schema agree, the README lags on `weight`, and the fixed reference is the Zenodo v0.1.2 archive or a commit-pinned URL. The first breaking revision is now in sight, because a v2 (temporal hypergraphs, a columnar format) is being planned. `hif_schema.json` is `latest` by design and will move silently, and a data file can declare a version only inside `metadata`, since a top-level key fails validation. The question becomes: **how should a HIF data file declare the rules it follows, and will v2 keep every v1 field so that v1 files stay valid?** P2's own files pin the schema by commit URL and sha256 in `metadata`, and its drafted upstream issue asks for a data-file version marker in v2. See [HIF §4](../04-storage-and-formats/hif-hypergraph-interchange-format.md), [standards bodies §4](../09-ecosystem/standards-bodies-and-specifications.md).

### Theme 5 — Bridges between theories that have not been built

- **[01.3]** Nobody has measured where real KHG schemas (Wikidata-style, biomedical) fall in Fagin's acyclicity hierarchy or what their hypertree width is; that number predicts query cost directly. See [hypergraph theory results](../01-foundations/hypergraph-theory-results.md), [n-ary relations and relational algebra](../01-foundations/n-ary-relations-and-relational-algebra.md).
  **Narrowed 2026-09-25 by [P6](../../projects/p6-schema-width/); answered in part.** P6 measured it with its checker `khg-width` on the schema hypergraph (one vertex per role, one hyperedge per relation). The premise was too broad: that hypergraph's width is the width of the query that joins *all* relations on same-named roles (the universal join of Fagin's scheme setting). So it bounds the cost of that universal join only. It does not bound a join of some of the relations, whose partial hypergraph can be wider (dropping the covering edge from a triangle with a cover turns hw 1 into hw 2), nor arbitrary queries, which join facts on entities and have their own hypergraphs. **Class:** under every naming with global roles, every Wikidata schema is α-cyclic. That holds for the declared one (allowed-qualifier constraints, 1,155 relations) and the observed ones (usage counts, 13,608 relations), and for Biolink Model v4.4.5 (103 relations). Relation-local roles give Berge-acyclic schemas with hw 1, a trivially acyclic control; GO-CAM's schema, with one central relation class, is α-acyclic ([research report 02](../../projects/p6-schema-width/research/02-data-sources-and-naming.md), findings 4 and 9). **Width:** Biolink's is exact, hw = ghw = fhw = 2, on a 5-relation core. Wikidata's is bounded, not exact. With core and qualifier roles, the declared schema has a GYO core of 391 relations and hw in [4, 38]. The observed schemas have hw in [4, 68] (qualifiers with ≥ 10 uses and ≥ 0.1 %; core 748) and [3, 61] (every observed qualifier; core 1,441). The baseline, HyperBench's 1,113 non-random conjunctive queries, has hw 1/2/3 = 673/432/8, so the declared and robust-observed Wikidata schemas are wider than all of them. The observed rows use SQID usage counts (dump of 2026-08-10) until P3a's exact counts from the 2026-09-22 dump replace them. Still open: the exact width of the Wikidata cores ([01.6]); whether the universal-join width predicts the cost of real Wikidata queries ([05.20]); how much of the measured structure is the role naming ([02.6]). See the [survey table](../../projects/p6-schema-width/results/survey.md), [hypergraph theory results §6](../01-foundations/hypergraph-theory-results.md) ("Measured"), [n-ary relations and relational algebra §2–§3](../01-foundations/n-ary-relations-and-relational-algebra.md).
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
3. [01.3] Acyclicity class and hypertree width of real KHG schemas. **Narrowed 2026-09-25** by [P6](../../projects/p6-schema-width/): Wikidata's qualifier schemas (1,155 declared, 13,608 observed relations) and Biolink v4.4.5 are α-cyclic under shared role names; Biolink has hw = 2 exactly, Wikidata hw in [4, 38] (declared) and [4, 68] or [3, 61] (observed), as bounds; the number is the width of the universal join on role names, not of arbitrary queries (Theme 5).
4. [01.4] Combinatorial complexes vs recursive hypergraphs for qualified facts.
5. [01.5] Role-weighted partitioning objective for sharding.
6. [01.6] What is the exact hypertree width of the Wikidata qualifier schemas' cyclic cores? P6 obtained bounds only: hw in [4, 38] for the declared schema (GYO core of 391 relations) and in [4, 68] and [3, 61] for the observed ones (cores of 748 and 1,441 relations), with core and qualifier roles. On each of these schemas the external solvers (BalancedGo, then log-k-decomp) used up their 20-minute budget without deciding a width. Cores of this size fall where HyperBench itself has exact hw for only 6 of its 23 graphs with 300 to 999 edges. The SAT-based exact solvers probed in P6's research (HtdLEO, htdsmt) were not run on these schemas. Raised 2026-09-25 by [P6](../../projects/p6-schema-width/) ([survey table](../../projects/p6-schema-width/results/survey.md); [research report 01 §3.5 and §4](../../projects/p6-schema-width/research/01-theory-and-solvers.md)); see [hypergraph theory results §6](../01-foundations/hypergraph-theory-results.md).

### 02 Knowledge representation
1. [02.1] Partial-completeness assumption for n-ary facts.
2. [02.2] Public uncertain n-ary benchmark; qualifier monotonicity as a probabilistic bound.
3. [02.3] A directed, role-labelled, nested formalism.
4. [02.4] Does decomposition to binary cost accuracy?
5. [02.5] Semantics of a weight on a reifier.
6. [02.6] How much of a KHG schema's measured structure is the role naming? P6 measured Wikidata under wd-roles r1, the naming it shares with P3a, which is one defensible choice among several. The class does not depend on it: every naming with global roles that was tested gives an α-cyclic schema, and relation-local roles an acyclic one. The cyclic core does. Naming a property's main-value role after the property joins its main use to its uses as a qualifier elsewhere, and grows the GYO residue over a property-local naming by 16 %, 26 % and 51 % on the declared, robust-observed and all-observed tables. Typing the main roles by constraint classes grows it by 24 %, 45 % and 99 %, while generic `subject`/`value` hubs change nothing. The widths were surveyed only under wd-roles r1 and the relation-local control. Raised 2026-09-25 by [P6](../../projects/p6-schema-width/) ([research report 02 §3.3–§3.4](../../projects/p6-schema-width/research/02-data-sources-and-naming.md); [wd-roles r1](../../projects/p6-schema-width/wd-roles.md)); see [Wikidata and Freebase data models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

### 03 Construction
1. [03.1] Arity-conditional merging of extracted facts.
2. [03.2] Does n-ary structure help as a function of arity? No arity-stratified results anywhere.
3. [03.3] Role-signature induction at LLM scale.
4. [03.4] The delta unit for a versioned hypergraph.
5. [03.5] A shape language for hypergraph incidence.
6. [03.6] Does inter-annotator agreement fall with arity? Re-analysing the MEE raw annotations by argument count would answer it without new annotation. Raised 2026-09-20 by [human-in-the-loop annotation and cost](../03-construction/human-in-the-loop-annotation-and-cost.md).
7. [03.7] Is the "top-heavy" failure mode real? No paper reports the arity distribution of an extractor's output against gold; an arity-stratified table on HyperDocRED would test Hyper-KGGen's own motivating claim. Raised 2026-09-21 by [skill-driven extraction and the scenario gap](../03-construction/skill-driven-extraction-and-the-scenario-gap.md).
8. [03.8] Does order of insertion change the graph? Feed the same corpus to an incremental extractor in two permutations and measure hyperedge-set agreement: the obvious confluence test, never run. Raised 2026-09-21 by the same note.
9. [03.9] What must a skill be, to be checkable? Free-text trigger–action skills cannot be validated, composed or transferred with guarantees; a typed skill (arity signature, role inventory, identity rule) could be, but nothing has tried. Raised 2026-09-21 by the same note.

### 04 Storage and formats
1. [04.1] HIF versioning on the first breaking change. **Reframed 2026-09-24** by [P2](../../projects/p2-role-aware-hif/): one repository and one rule set with conflicting labels; the question is now how a data file declares its version and whether v2 keeps every v1 field (Theme 4).
2. [04.2] Native hyperedge storage vs reified-node emulation, measured.
3. [04.3] Identity of a hyperedge whose membership changes.
4. [04.4] Role-labelled incidence tensors compatible with Laplacian operators.
5. [04.5] Incremental repartitioning of a live KHG.
6. [04.6] May HIF `incidences` repeat an (edge, node) pair? The paper's formal model makes the incidence set a *set*, yet the schema and upstream's compliant test `duplicated_nodes_edges.json` accept repeats, and the role convention needs them for a node with two roles or a node in both tail and head. XGI (edges are sets) and HyperNetX (cells keyed by the pair) both collapse them natively. P2's drafted upstream issue asks the maintainers to settle it; if they rule that incidences form a set, the convention needs a v2 ask rather than a v1 change. Raised 2026-09-24 by [P2](../../projects/p2-role-aware-hif/) ([DESIGN §12.3 and §14 risk 5](../../projects/p2-role-aware-hif/DESIGN.md); [report 02 §3](../../projects/p2-role-aware-hif/research/02-hif-standard.md)).
7. [04.7] What should a store do to the values that name an entity when that entity is merged into another? P2's v1 store refuses to set `redirect_to` on an entity while any record it holds names that entity (D020). So a store never holds a value naming a redirected entity and never exports an invalid file, but it cannot merge an entity while any fact names it. Rewriting values to follow a redirect is planned for version 1.2, and its semantics are open: rewrite every naming fact as a new version, resolve at read time, or keep both with provenance, and how each choice interacts with fact identity and supersession. Raised 2026-09-24 by [P2](../../projects/p2-role-aware-hif/) (review finding d-store-10; [DESIGN §12.2 and §14 ruling 10](../../projects/p2-role-aware-hif/DESIGN.md)); see also [entity resolution and canonicalisation](../03-construction/entity-resolution-and-canonicalisation.md).
8. [04.8] What does each storage backend lose against one conformance suite for n-ary facts? P2's store interface ships 114 executable scenarios with capability flags. A backend passes when no applicable scenario fails, and each inapplicable scenario is a fidelity loss. By P2's design analysis, TypeDB 3.x can apply 70 of the 114; ordered roles, special values, goals and transaction time are not native to it. P1 measures this for its five backends. Raised 2026-09-24 by [P2](../../projects/p2-role-aware-hif/) ([DESIGN §14 open question 1 and ruling 1](../../projects/p2-role-aware-hif/DESIGN.md)); companion to [04.2] and [08.1].

### 05 Query, embeddings, reasoning
1. [05.1] Width Wall hierarchy on relational hypergraphs.
2. [05.2] Rule mining at n-ary arity.
3. [05.3] Post-hoc hyperpath extraction from query-embedding models.
4. [05.4] Calibration as a function of arity.
5. [05.5] Hypertree-decomposition planning over an incidence index.
6. [05.6] Does any hyper-relational model beat a well-tuned classical KG embedding on de-leaked JF17K, on native rather than decomposed data? Raised 2026-09-20 by [reproducibility of n-ary link prediction](../05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md).
7. [05.7] Are hypergraph neural networks structurally a poor fit for knowledge hypergraphs? HADES (2026) finds they degrade on heterophilic nodes joined by semantically diverse hyperedges, which is what a typed n-ary fact looks like. Raised 2026-09-20 by [reading the frontier, 2026 Q3](../08-history-and-frontier/reading-the-frontier-2026-q3.md).
8. [05.8] Can a key role set (the roles whose binding may hold for at most one valid fact at a time) be induced from an extracted KHG rather than declared, so that supersession becomes decidable? Raised 2026-09-21 by [temporal and dynamic KHGs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md).
9. [05.9] Does VITA's time triplet, re-evaluated under an extrapolation split, beat timestamp-per-n-tuple models such as MT-Path, or does the interval representation only help interpolation? Raised 2026-09-21 by the same note.
10. [05.10] HYPER's Theorem C.2 only asserts that an injective, bounded, Lipschitz `Enc_PI` exists in the hypothesis class; does the trained encoder stay injective, and does injectivity or merely boundedness do the work? Raised 2026-09-21 by [HYPER anatomy](../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md).
11. [05.11] HYPER's relation graph has O(|R|²k²) edges; what sparsification keeps the transfer result at Wikidata-scale relation vocabularies (|R| ≈ 5,000, k = 9, about 2×10⁹ potential edges)? Raised 2026-09-21 by the same note.
12. [05.12] Why does pretraining on 50 knowledge graphs make both HYPER and ULTRA worse than pretraining on 3: distribution shift, or an optimisation artefact at 30,000 steps? Raised 2026-09-21 by the same note.
13. [05.13] Has anyone outside the authors' group re-run reified ULTRA on the 16 HYPER datasets, given that the published baseline moved by a factor of 50 between preprint versions? Raised 2026-09-21 by the same note.
14. [05.14] Is any n-ary benchmark actually hyperbolic? No δ-hyperbolicity statistic has been published for JF17K, FB-AUTO, M-FB15K, WikiPeople or WD50K, so the whole hyperbolic family rests on an analogy. Raised 2026-09-21 by [geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).
15. [05.15] Would ReAlE's five algebraic primitives, exposed as planner-callable tools, let an LLM plan beat an end-to-end query-embedding model on WD50K-QE or NQE query patterns? Raised 2026-09-21 by the same note (companion to [08.7]).
16. [05.16] Does the ReAlE parametrisation extend to Cartesian product (hence join), or is there an impossibility result analogous to its Theorem 10 for HypE and selection? Raised 2026-09-21 by the same note.
17. [05.17] Is there any n-ary link-prediction model that uses a linguistic role inventory (PropBank, FrameNet, VerbNet) so roles transfer across relations and datasets, rather than dataset-specific role strings? Raised 2026-09-21 by the same note.
18. [05.18] Does H²GNN's result survive a re-run against ReAlE and against HypE at its published numbers on the same splits? Raised 2026-09-21 by the same note.
19. [05.19] Is "an absent end bound means the fact still holds" the right default reading for n-ary facts drawn from mixed sources? P2's bound table presumes it (an absent start reads as unknown) and separates definite from possible readings; a source that means something else by an absent bound gets other answers. P2 did not measure what absent bounds mean in real qualifier data. Raised 2026-09-24 by [P2](../../projects/p2-role-aware-hif/) ([DESIGN §14 risk 1](../../projects/p2-role-aware-hif/DESIGN.md)); see [temporal and dynamic KHGs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md).
20. [05.20] Does a schema's universal-join width predict the cost of real queries over it? P6's number is the width of joining all relations on same-named roles, while real queries join facts on entity variables and have their own hypergraphs. On Wikidata the two diverge: the schema's hw is at least 3 or 4, whereas HyperBench reports that of 1,915,550 CQOF+ queries in Wikidata's query logs, 590,005 have hw 2 and the rest hw 1 (Bonifati, Martens and Timm, as quoted by [Fischl et al., 2021](https://doi.org/10.1145/3440015); not checked against the original `[unverified]`). A query-log study that relates each query's width and evaluation cost to the schema's cyclic core would settle it. Raised 2026-09-25 by [P6](../../projects/p6-schema-width/) ([research report 01 §2.5 and §3.4](../../projects/p6-schema-width/research/01-theory-and-solvers.md)); companion to [05.5]; see [query languages for hypergraphs §10](../05-query-embeddings-reasoning/query-languages-for-hypergraphs.md).

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
6. [07.6] Does a hierarchy beat a better search? H²RAG (hierarchical) and PRoH or Graph-R1 (planned or learned) have never been compared on the same corpus, and cost very differently. Raised 2026-09-21 by [hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md).
7. [07.7] What is the break-even query volume for a hierarchical index that costs about 35 LLM tokens per corpus token to build (HiRAG on UltraDomain Mix)? Raised 2026-09-21 by the same note.
8. [07.8] Is community detection over hyperedges better than GMM clustering over entity embeddings, holding the summary layer and the reader fixed (H²RAG vs HiRAG, isolated)? Raised 2026-09-21 by the same note.
9. [07.9] Why do both PRoH and HyperGraphRAG score higher on PRoH's 3–6 hop split than on the 1–3 hop split; does hop distance in an extracted hypergraph track question difficulty at all? Raised 2026-09-21 by the same note.
10. [07.10] At what granularity should validity sit on an n-ary fact, the whole hyperedge or each role-binding, given that whole-edge closure duplicates n−1 bindings on every single-role change? Raised 2026-09-21 by [temporal hyperedges and editable agent memory](../07-applications/temporal-hyperedges-and-editable-agent-memory.md).
11. [07.11] Would adding Graphiti-style invalidation to a hypergraph memory move LoCoMo's temporal column or LongMemEval's knowledge-update slice, and which is the right measurement? Raised 2026-09-21 by the same note.
12. [07.12] EvoGraph-R1 can insert, update and delete but is rewarded only on answer F1 and well-formedness; what reward makes an agent retract correctly, and can it be scored without a ground-truth timeline? Raised 2026-09-21 by the same note.
13. [07.13] Which defaults should memory gold use? In particular, which Wikidata deprecation reasons mark a value as *revised* (it was wrong) rather than *expired* (it stopped holding)? P2's default counts only `wd:Q41755623` ("incorrect value"). Its other v1 defaults, a same-unit amount tolerance for quantities and a `missing` outcome scored 0 for an unanswered question, are also provisional. P3a is to report the distribution of deprecation reasons it finds, and P3a and P7 confirm or replace these defaults before the memory question set is built. Raised 2026-09-24 by [P2](../../projects/p2-role-aware-hif/) ([DESIGN §14 open question 3 and rulings 3 and 8](../../projects/p2-role-aware-hif/DESIGN.md)).

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
2. [09.2] Which HIF schema document is normative. **Reframed 2026-09-24** by [P2](../../projects/p2-role-aware-hif/): the paper and the schema agree and the README lags on `weight`; the Zenodo v0.1.2 archive or a commit-pinned URL is the fixed reference; what remains is the moving `latest` file (Theme 4).
3. [09.3] Replication studies of n-ary link prediction.
4. [09.4] UltraDomain's canonical location and licence.
5. [09.5] Minimal extension that makes HIF a KHG format. **Narrowed 2026-09-24** by [P2](../../projects/p2-role-aware-hif/): `role-convention` 1.0.0 plus the `khg-hif/1.0.0` profile, with no schema change, round-trips through XGI and HyperNetX via P2's loaders; upstream acceptance pending (Theme 2).
6. [09.6] Will XGI's and HyperNetX's own HIF functions keep incidence attributes, weights, metadata and repeated records? On 2026-09-23 XGI 0.10.2 dropped every incidence `attrs` and weight, and HyperNetX 2.4.3 dropped repeated pairs and metadata, needed the network on every call, returned `None` instead of raising and could not re-read its own directed output. Issues with the evidence attached are drafted, not filed. Until upstream changes, role-preserving loading needs code outside both libraries, pinned to the probed versions. Raised 2026-09-24 by [P2](../../projects/p2-role-aware-hif/) ([report 03 §7.5](../../projects/p2-role-aware-hif/research/03-library-probes.md); [DESIGN §12.4 and §14 risk 4](../../projects/p2-role-aware-hif/DESIGN.md)).

### 10 Comparative and critique
1. [10.1] Any result that holds of KHGs but not of sets of ground atoms.
2. [10.2] Arity ablation of hypergraph-RAG gains.
3. [10.3] Hypergraph vs bipartite null models.
4. [10.4] HIF with roles, types and provenance without becoming RDF. **Narrowed 2026-09-24** by [P2](../../projects/p2-role-aware-hif/): roles in `attrs.role`, the relation type in the edge's `attrs.relation`, statuses and provenance as `khg-*` keys in `attrs` and `metadata`; readable only by readers that know the profile; upstream acceptance pending (Theme 2).
5. [10.5] Is the relation-instance pattern really the bottleneck?
6. [10.6] What are the correct erasure semantics for an n-ary fact? Removing one participant under a right-to-erasure request leaves three bad options: delete the fact, delete the incidence, or tombstone. No published system implements any. Raised 2026-09-20 by [privacy, licensing and governance](../10-comparative-and-critique/privacy-licensing-and-governance.md).
7. [10.7] Is a hyperedge measurably more re-identifying than its reification? An attribute-inference or k-anonymity attack on the same facts in both encodings has never been run. Raised 2026-09-20 by the same note.
8. [10.8] Would retrieval over an inductively completed hypergraph (HYPER-style) beat retrieval over the extracted one, and can the completion be made auditable? No system combines the two as of 2026-09-21. Raised 2026-09-21 by [hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md) (companion to [08.6]).
9. [10.9] What would a learned index scoring function (corpus-specific hyperedge weights) add on top of a learned traversal policy? Nothing learns the EWO analogue. Raised 2026-09-21 by the same note.

## Part C — Candidate first projects

Each is small enough to start from this repository and would move at least one theme. They are
listed in `projects/README.md` as candidate vectors and organised as one programme in
`projects/PLAN.md`. P2 passed its gate on 2026-09-24 and P6 on 2026-09-25. P2's publication (package release and
upstream proposal) is pending with the repository owner; P6's (a short note and a data deposit) is
still to be prepared, and the owner releases it. No other project has passed its gate.

| Id | Project | Themes moved | Questions |
|---|---|---|---|
| P1 | **Format and store bake-off**: one small KHG (the `schemas/` sample, grown to a few hundred facts) held as incidence table, reified RDF 1.2, bipartite property graph, TypeDB, HIF; same queries; round-trip fidelity and latency logged | 1, 4 | 04.2, 08.1, 04.1, 09.2 |
| P2 | **Role-aware HIF**: a `roles` convention on incidence attributes, a validator, and loaders for XGI and HyperNetX that keep roles. **Gate passed 2026-09-24**; base updated 2026-09-24; package release and upstream issue prepared, not yet published or filed. See [P2](../../projects/p2-role-aware-hif/) | 2 | 09.5, 10.4 (narrowed); 04.1, 09.2 (reframed); raised 04.6–04.8, 05.19, 07.13, 09.6; 04.4 not addressed |
| P3 | **Clean n-ary benchmark and replication**: rebuild a leak-free, arity-stratified split from a recent Wikidata dump; replicate two models; report calibration by arity | 3 | 08.4, 09.3, 05.4, 02.4 |
| P4 | **Arity ablation of hypergraph RAG**: run one hypergraph-RAG system with hyperedges intact, split pairwise, and as whole-sentence chunks, on one public domain and on GraphRAG-Bench | 1, 3 | 10.2, 07.1, 07.2 |
| P5 | **Reader study**: incidence vs Euler drawing of the same KHG, with and without role labels | 2, 6 | 06.1, 06.2 |
| P6 | **Schema width survey**: compute acyclicity class and hypertree width for Wikidata qualifier schemas and one biomedical schema. **Gate passed 2026-09-25**; base updated 2026-09-25. The observed Wikidata rows are to be rerun on P3a's counts. The note and a Zenodo deposit are still to be prepared and then released by the owner. See [P6](../../projects/p6-schema-width/) | 5 | 01.3 (narrowed); raised 01.6, 02.6, 05.20; 05.5 not addressed |
| P7 | **Agent memory prototype**: a hypergraph memory for a small agent vs a flat vector store, with fact identity, arity-conditional merging rules and **valid-time on the hyperedge with supersession** made explicit (reframed 2026-09-21) | 4, 8 | 03.1, 04.3, 08.6 |
| P8 | **Four-ability evaluation suite**: one corpus scored on gold n-ary extraction, inductive completion of the extracted graph, high-arity-edge-ablated multi-hop retrieval, and a superseding memory trace; see [the composed stack](../08-history-and-frontier/composed-stack-and-research-bets.md) §3 (added 2026-09-21) | 3, 8 | 08.6, 08.7, 08.8, 08.9 |
| P9 | **Extraction gate**: an n-ary extraction pass with role constraints, scored against gold facts, that emits a candidate queue rather than writing to the graph; instability measured across runs and insertion orders (added 2026-09-21) | 2, 3, 8 | 03.9, 05.17, 08.9, 07.10, 03.8, 03.5 |
| P10 | **Judgment-model walker**: retrieval as a policy over a code-owned traverser, where a judgment model answers next-edge, stop and prune as closed choices; a general LLM first, then a decision-only model behind the same interface, on a gold graph (added 2026-09-21) | 1, 8 | 08.6, 08.7, 07.2 |
| P11 | **Goal-directed construction**: a multi-discipline design question as goal hyperedges with unbound roles, one agent per discipline binding roles with evidence, and a termination criterion for when the disciplines connect (added 2026-09-21) | 4, 6, 8 | 03.1, 04.3, 07.10, 08.5 |

## Sources

This file cites no external sources directly; every question links to the note that holds the
evidence and its `## Sources` section.
