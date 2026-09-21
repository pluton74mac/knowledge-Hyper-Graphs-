---
title: Glossary
type: glossary
status: reviewed
tags: [glossary, index]
created: 2026-09-20
updated: 2026-09-21
---

# Glossary

## How to use this page

Every technical term, acronym, model, dataset, format, standard and tool that a reader of this
knowledge base will meet, defined once in plain English and pointed at the note that treats it
properly. Entries are alphabetical under letter headings; each ends with a **See:** link to the
one or two notes that define or discuss the term best. Where the KB records that a term is
**contested or ambiguous** — "knowledge hypergraph", "directed hypergraph", "hyper-relational",
"reification", "hypernetwork", "higher-order", "metagraph" — the entry says so and links to the
note that lays out the competing senses.

Two companion pages go deeper and are not duplicated here. Mathematical **symbols** (`H`, `W`, `r`,
`δ(e)`, `Δ`, `γ₂`) and the clashes between authors' conventions are in the
[notation cheat sheet](../01-foundations/notation-cheatsheet.md). The **disambiguation table** for
the eleven most-confused terms, with "who uses it" and "what it is not" for each, is in the
[glossary of confusable terms](../10-comparative-and-critique/glossary-of-confusable-terms.md).
This page is the wide index; those two are the deep ones.

## Core ten

The ten terms a newcomer should learn first, in the order they build on each other:

1. **[Hypergraph](#h)** — the bare mathematical object: edges may contain any number of vertices.
2. **[Hyperedge](#h)** — one such edge; in this KB, one fact.
3. **[Arity](#a)** — how many participants a fact has.
4. **[Knowledge hypergraph](#k)** — the contested term this KB is named after; at least five senses.
5. **[N-ary relation](#n)** — a relation with more than two arguments; the oldest framing of the idea.
6. **[Role](#r)** — the name of the part a participant plays in a fact.
7. **[Qualifier](#q)** — an optional binding that restricts a fact rather than constituting it.
8. **[Hyper-relational fact](#h)** — a primary triple plus qualifiers; Wikidata's shape.
9. **[Reification](#r)** — turning a statement into an addressable object; the universal workaround.
10. **[Levi graph](#l)** — the incidence graph; the lossless bipartite encoding every system uses.

---

## 0–9

**2-section** — Berge's name for the [clique expansion](#c): the graph on the same vertices in which
two vertices are joined whenever some hyperedge contains both. Written `[H]₂`. Lossy: it cannot
recover which cliques were hyperedges.
See: [Incidence, matrices, tensors and graph expansions](../01-foundations/incidence-and-matrix-representations.md).

---

## A

**ACE 2005** — the Automatic Content Extraction corpus and guidelines, the closed-schema ancestor of
n-ary extraction: 8 event types, 33 subtypes, each with typed argument roles. Notably forbids events
as arguments of other events, so ACE events are flat hyperedges.
See: [N-ary relation and event extraction from text](../03-construction/n-ary-relation-extraction-from-text.md).

**AGM bound** (Atserias–Grohe–Marx bound) — a tight bound on the output size of a full conjunctive
query in terms of the fractional edge cover number of the query hypergraph; the arity structure, not
the data, determines the worst case.
See: [N-ary relations, relational algebra and the query hypergraph](../01-foundations/n-ary-relations-and-relational-algebra.md).

**AllSet** — a 2022 hypergraph neural network framework showing that an HNN layer is exactly a
composition of two learnable *multiset* functions (vertex-set → hyperedge, hyperedge-set → vertex).
Most later HNNs are special cases. Also the name of the standard hypergraph node-classification
dataset suite it shipped.
See: [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

**α-acyclicity** (alpha-acyclicity) — the weakest and most general of Fagin's degrees of hypergraph
acyclicity: the hypergraph admits a join tree, equivalently reduces to empty under
[GYO reduction](#g). Exactly the boundary of tractable join evaluation.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**AMIE** — the reference rule-mining system for incomplete knowledge bases, and the source of the
[partial completeness assumption](#p). It operates on triples; there is no published "AMIE for
hyperedges".
See: [Logical reasoning and rules over n-ary facts](../05-query-embeddings-reasoning/logical-reasoning-and-rules-over-n-ary-facts.md).

**AND/OR graph** — a search structure in which an AND node requires all its children; formally a
directed hypergraph, and one of the applications Gallo et al. list in 1993. Retrosynthesis trees,
HTN plans and exploit rules are all instances.
See: [AI agents — memory and planning](../07-applications/ai-agents-memory-and-planning.md).

**Anti-rank** — the minimum hyperedge size `min_e |e|` of a hypergraph; contrast [rank](#r).
See: [Notation cheat sheet](../01-foundations/notation-cheatsheet.md).

**Arity** — the number of arguments a relation takes, or participants a fact has. Conventions
differ: in the hyper-relational literature arity sometimes counts the primary triple's two entities
plus qualifier values, sometimes only entities, so arity distributions are not comparable across
papers without checking.
See: [Hyper-relational vs n-ary vs hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).

**Arity ablation** — reporting link-prediction or extraction scores separately for arity 2, 3, 4 and
≥5 rather than as an aggregate. The KB's repeated recommendation, because aggregate MRR is dominated
by the binary majority; no published KHG construction paper does it.
See: [Benchmarks and evaluation protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).

**Atom** — in HypergraphDB and OpenCog, the single representational unit: an object with an
associated tuple of other atoms (its *target set*). Arity 0 atoms are nodes, arity > 0 atoms are
links, so nesting is free.
See: [Metagraphs, ubergraphs and hypergraph databases](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md).

**Atomese** — OpenCog's language of Atom types: typed s-expressions that describe structural
relationships and double as abstract syntax trees for computation.
See: [Metagraphs, ubergraphs and hypergraph databases](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md).

**AtomSpace** — OpenCog's in-RAM "generalized hypergraph (metagraph) database" with a query engine
and graph-rewriting system. Splits immutable, indexed **Atoms** from mutable, unindexed **Values** —
a split a KHG schema should copy.
See: [Hypergraph and n-ary databases](../04-storage-and-formats/hypergraph-databases.md).

**Attributed hypergraph** — a hypergraph with key–value data on vertices, hyperedges and/or
incidences. A software convention rather than a textbook notion; the incidence level is where a role
label belongs.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**AutoSchemaKG** — an LLM pipeline that extracts triples and *induces a schema* simultaneously by
conceptualisation, reported at web scale (900+ million nodes, 5.9 billion edges) with 92% semantic
alignment to human schemas.
See: [Schema induction and ontology alignment](../03-construction/schema-induction-and-ontology-alignment.md).

---

**Aware-less** — the third category of Lu, Tupikina and Alam's semantic-awareness axis: models encoding
neither entity position nor semantic role, treating a fact's entities as an unordered collection
(e.g. m-DistMult, GETD, S2S).
See: [Geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).

## B

**B-arc** (backward arc) — a directed hyperedge with a single head: many tails, one head. It *is* a
Horn clause `b₁ ∧ … ∧ b_k → h`, and also a functional dependency and a production rule.
See: [Directed and typed hyperedges for knowledge](../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md).

**B-connectivity** — reachability in a directed hypergraph where a hyperedge may be traversed only
when *every* node in its tail is already reached. The AND semantics; relaxing it is what makes
pathway graphs look far more connected than they are.
See: [Biomedicine and the life sciences](../07-applications/biomedical-and-life-sciences.md).

**B-hypergraph** — a directed hypergraph all of whose hyperarcs are B-arcs. Reachability is
linear-time, and s-t hyperpath enumeration is polynomial-delay — unlike the F- and BF- cases.
See: [Hypergraph algorithms for knowledge work](../05-query-embeddings-reasoning/hypergraph-algorithms-for-knowledge.md).

**B-hyperpath** — a minimal set of B-arcs justifying a conclusion; equivalently a proof, and the
natural provenance record for a multi-hop inference.
See: [Logical reasoning and rules over n-ary facts](../05-query-embeddings-reasoning/logical-reasoning-and-rules-over-n-ary-facts.md).

**Berge acyclicity** — the most restrictive acyclicity notion: the incidence graph is a forest.
Brault-Baron argues it is a *multi*-hypergraph notion rather than a hypergraph one, since the
two-copy multiset `[{x,y},{x,y}]` fails it while the set `{{x,y}}` does not.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**β-acyclicity** (beta-acyclicity) — every sub-hypergraph is α-acyclic; equivalently a β-elimination
order exists. Sits strictly between γ- and α-acyclicity and has no simple join-tree characterisation.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**BF-hypergraph** — a directed hypergraph whose hyperarcs are each a B-arc or an F-arc.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**Bicoloured graph** — a bipartite graph *together with a fixed choice of which side is which*.
Hypergraphs are in bijection with bicoloured graphs, not with bipartite graphs: a bipartite graph
with k components admits 2^k bicolourings, each a different hypergraph. The correction that most
statements of the "it's just a bipartite graph" objection get wrong.
See: [The hypergraph-vs-bipartite-graph debate](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md).

**BIBD** (balanced incomplete block design) — a k-uniform, r-regular hypergraph with constant
pairwise co-degree λ. Design theory is the oldest branch of hypergraph theory and a source of
techniques rather than models, because knowledge hypergraphs are maximally irregular.
See: [Hypergraphs vs bipartite vs simplicial](../01-foundations/hypergraphs-vs-bipartite-vs-simplicial.md).

**Bubble Sets** — a set-visualisation overlay that draws isocontours around set members over a
*fixed* layout, routing around non-members. The strongest family to borrow when node positions are
already decided by something else.
See: [Set visualisation and hypergraph visualisation](../06-visualization/set-visualization-connection.md).

---

## C

**Calibration** — whether a model's score can be read as a probability. Studied for binary KG
embeddings (Platt scaling, isotonic regression fix much of it); **no calibration study of n-ary link
predictors exists**, which matters more here because MRR averages over prediction tasks and so
reweights by arity.
See: [Explainability and uncertainty](../05-query-embeddings-reasoning/explainability-and-uncertainty.md).

**Cell complex** — a topological structure that adds a hierarchy to sets but imposes geometric
gluing conditions real data rarely satisfies. The motivation for [combinatorial complexes](#c).
See: [Hypergraphs vs bipartite vs simplicial](../01-foundations/hypergraphs-vs-bipartite-vs-simplicial.md).

**CGIF** (Conceptual Graph Interchange Format) — the serialisation of conceptual graphs, with
prefix-form relations of any arity plus contexts and negation; standardised as Annex B of
ISO/IEC 24707 Common Logic.
See: [Ontologies and schemas for n-ary knowledge](../02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md).

**Cheeger inequality (hypergraph)** — `γ₂/2 ≤ φ_H ≤ 2√γ₂`, relating the second eigenvalue of the
*non-linear* hypergraph Laplacian to hypergraph expansion. No linear operator can play this role,
and computing `γ₂` costs an `O(log r)` approximation factor.
See: [Random walks, spectral theory and expansion](../01-foundations/random-walks-spectral-and-expansion.md).

**Chromatic number** `χ(H)` — the fewest colours such that no hyperedge is monochromatic (the weak
colouring convention). The combinatorial shell of constraint satisfaction over facts.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**Claim** (Wikidata) — the core of a statement without its references and rank: property, value and
qualifiers.
See: [Wikidata and Freebase data models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

**Clique expansion** — replace each hyperedge by a clique on its vertices. **Lossy**: hyperedge
identity and size vanish, cut parameters can be distorted by a factor `Ω(r)`, and one hyperedge of
size 1,000 becomes 499,500 edges. The single most common thing to avoid materialising.
See: [Incidence, matrices, tensors and graph expansions](../01-foundations/incidence-and-matrix-representations.md).

**Closed-world assumption (CWA)** — a fact not present is false. Standard in databases and in MLN
weight learning; wrong for most knowledge bases. Contrast [OWA](#o) and [PCA](#p).
See: [Open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).

**Coarse-to-fine hyperedge extraction** — extracting a binary skeleton first, then qualified binary
relations (time, place, conditions), then general n-ary event hyperedges, rather than emitting all
arities in one prompt; Hyper-KGGen's construction ladder.
See: [Skill-driven extraction and the scenario gap](../03-construction/skill-driven-extraction-and-the-scenario-gap.md).

**Cog-RAG** — a 2026 hypergraph-RAG system with a dual hypergraph: a *theme* hypergraph over chunks
plus an *entity* hypergraph, aligned by a top-down retrieval pass.
See: [Retrieval-augmented generation](../07-applications/retrieval-augmented-generation.md).

**Combinatorial complex** — Hajij et al.'s structure that adds a **rank function** to a set system
without requiring downward closure, so it has hierarchy without the wrong entailments of a
simplicial complex. Generalises hypergraphs.
See: [Hypergraphs vs bipartite vs simplicial](../01-foundations/hypergraphs-vs-bipartite-vs-simplicial.md).

**Common Logic** (ISO/IEC 24707:2018) — a standardised family of first-order logic languages with
dialects CLIF, CGIF and XCL. Its **variable-arity relations** and **sequence markers** are, as far
as this KB found, the only standardised device for writing a rule that holds for every arity.
See: [Ontologies and schemas for n-ary knowledge](../02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md).

**Conceptual graph** — Sowa's bipartite notation of concept nodes and n-adic conceptual-relation
nodes with numbered arcs. Structurally the incidence graph of a labelled hypergraph, drawn in 1976.
See: [The knowledge-representation lineage](../08-history-and-frontier/knowledge-representation-lineage.md).

**Conditional message passing** — message passing whose node initialisation and messages depend on the
query, so representations are query-relative rather than absolute; the NBFNet → HCNet → HYPER family.
See: [HYPER anatomy](../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md).

**Conformality** — the dual of the Helly property: a hypergraph is k-conformal iff its dual is
k-Helly.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**Conjunctive query** — a select-project-join query; its *query hypergraph* has variables as
vertices and atoms as hyperedges, and its tractability is governed by acyclicity and
[hypertree width](#h).
See: [Query languages for knowledge hypergraphs](../05-query-embeddings-reasoning/query-languages-for-hypergraphs.md).

**Connectivity metric (λ−1, km1)** — the hypergraph-partitioning objective that charges each
hyperedge `(λ(e) − 1) · w(e)` for the number of blocks it touches. The right default for sharding a
KHG, because a fact touching λ shards costs roughly λ−1 extra messages.
See: [Versioning, provenance and scale](../04-storage-and-formats/versioning-provenance-and-scale.md).

**Coverage** — the evaluation axis asking whether a constructed KHG retains the information in its
source, measured by fact-verification against a gold fact list; distinct from extraction precision
and from downstream QA.
See: [Evaluating constructed knowledge hypergraphs](../03-construction/evaluation-of-constructed-khgs.md).

**CubeRE** — a "cube-filling" supervised extractor for hyper-relational facts (triple plus
qualifiers), the baseline shipped with HyperRED.
See: [N-ary relation and event extraction from text](../03-construction/n-ary-relation-extraction-from-text.md).

**Cut-net** — the hypergraph-partitioning objective that simply counts (or weighs) the hyperedges
crossing a boundary; the simpler alternative to the connectivity metric.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**CVT** (compound value type) — Freebase's anonymous intermediate object used to represent n-ary
relations: a typed node with a mid, linked from the subject and pointing at each component value.
Pattern 1 of the W3C n-ary note, applied at web scale, and the structure JF17K and FB-AUTO were
mined back out of.
See: [Wikidata and Freebase data models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

**Cypher** — Neo4j's property-graph query language and the ancestor of GQL. Binary edges only; an
n-ary fact becomes a reified node plus one relationship per participant.
See: [Emulating hyperedges in property graphs](../04-storage-and-formats/property-graph-emulation-patterns.md).

**Cyc / CycL** — the longest-running hand-curated knowledge base (from 1984) and its language, which
has full first-order logic, higher-arity predicates, statements about statements, and per-assertion
contexts (*microtheories*) as first-class terms. Roughly 2,000 person-years of curation.
See: [Curation, crowdsourcing and quality control](../03-construction/curation-crowdsourcing-and-quality.md).

---

## D

**Datalog** — a rule language whose atoms are n-ary by definition, so a knowledge hypergraph in the
labelled-tuple form *is* a Datalog extensional database. Gives recursion and a well-understood
complexity picture; almost no KHG system exposes it.
See: [Relational, EAV and Datalog storage](../04-storage-and-formats/relational-and-eav-storage.md).

**Datomic** — a database of immutable entity–attribute–value–transaction *datoms*. The transaction
component makes "as-of" queries free, and a fact entity with one attribute per role is idiomatic
rather than a workaround.
See: [Relational, EAV and Datalog storage](../04-storage-and-formats/relational-and-eav-storage.md).

**DHG (DeepHypergraph)** — Tsinghua iMoon-Lab's PyTorch library for graph and hypergraph neural
networks (HGNN, HGNN⁺, HyperGCN, UniGNN). Stores a hyperedge list in named *groups* and derives
sparse matrices on demand; persistence is pickle, with no HIF support.
See: [Software libraries](../09-ecosystem/software-libraries.md).

**Directed hypergraph** — **contested term with three incompatible senses**: (D1) the hyperedge is an
ordered tuple so position carries the role, (D2) the hyperedge is a pair `(tail set, head set)` in
Gallo et al.'s sense, (D3) each incidence carries a role label. D2 carries *inference*; D1 and D3
carry *assertion*. Storing both in one edge set without a type marker is a recurring bug.
See: [Directed and typed hyperedges for knowledge](../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md)
and [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**DocRED** — a document-level relation-extraction benchmark (5,053 annotated Wikipedia documents,
96 relation types) whose headline finding is that "at least 40.7% of relational facts can only be
extracted from multiple sentences". Its relations are binary.
See: [N-ary relation and event extraction from text](../03-construction/n-ary-relation-extraction-from-text.md).

**DocTrace** — a 2026 multi-agent long-document QA system that builds a hypergraph **working memory
on demand during reasoning** rather than indexing one in advance, plus a graph-structured experience
memory of successful plans. A direct answer to the cost objection against graph RAG.
See: [AI agents — memory and planning](../07-applications/ai-agents-memory-and-planning.md).

**Drips** — PAOH's compaction glyph: degree-one vertices are hidden and their existence hinted by
small grey dots at the lower end of a hyperedge line.
See: [Dynamic and temporal hypergraph visualization](../06-visualization/dynamic-and-temporal-hypergraph-visualization.md).

**Dual hypergraph** `H*` — swap the roles of vertices and hyperedges; in matrix terms, transpose the
incidence matrix. Every query over entities has a dual query over facts, which is why a KHG store
should index both directions.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

---

## E

**EdgeMem** — a 2026 LLM-free agent memory that preserves original conversation turns in a multi-anchor
hypergraph indexed by content, calendar-month and episodic cues; reports LoCoMo under a strict judge
and LongMemEval-S retrieval metrics, neither comparable to HyperMem's LLM-as-a-judge score.
See: [Temporal hyperedges and editable agent memory](../07-applications/temporal-hyperedges-and-editable-agent-memory.md).

**ED-HNN** — a 2023 hypergraph neural network derived from hypergraph *diffusion* rather than from
GNNs; provably approximates any continuous equivariant hypergraph diffusion operator, implemented as
message passing over the star expansion.
See: [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

**EDC (Extract–Define–Canonicalize)** — a three-phase LLM pipeline: open extraction, then natural
language definitions for each induced schema component, then canonicalisation against a target
schema or self-canonicalisation. Motivated by schemas that do not fit in a prompt.
See: [Schema induction and ontology alignment](../03-construction/schema-induction-and-ontology-alignment.md).

**EDVW** (edge-dependent vertex weights) — giving each *incidence* its own weight `γ_e(v)`, so a
vertex counts differently inside different hyperedges. The cheapest genuinely higher-order repair
for random walks, and the structural home of a role label.
See: [Random walks, spectral theory and expansion](../01-foundations/random-walks-spectral-and-expansion.md).

**Edge standard** — Mäkinen's drawing convention in which hyperedges are curves or trees connecting
their vertices; contrast the [subset standard](#s). The bipartite/extra-node encoding is its
practical form.
See: [Hypergraph drawing algorithms](../06-visualization/hypergraph-drawing-algorithms.md).

**Enc_PI (positional-interaction encoder)** — HYPER's `MLP([p_a ‖ p_b])` over sinusoidal position
encodings, mapping a position pair to a vector; required to be injective and extrapolating so a model
can act on arities it never saw. Theorem C.2 shows such an encoder exists in the hypothesis class, not
that the trained one is injective.
See: [HYPER anatomy](../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md).

**Entity linking** — mapping a mention to an identifier in a reference knowledge base (Wikidata,
UMLS). Skipped by every current LLM-based KHG pipeline, which merge entities on exact upper-cased
string match.
See: [Entity resolution and canonicalisation](../03-construction/entity-resolution-and-canonicalisation.md).

**Entity resolution** — deciding when two mentions denote the same thing. In a KHG it has three
levels: mention → entity, phrase → relation/role, and fact → fact, and the third is unsolved because
two extractions of the same fact routinely differ in arity.
See: [Entity resolution and canonicalisation](../03-construction/entity-resolution-and-canonicalisation.md).

**Euler diagram** — closed curves whose overlap regions carry the semantics. The best-supported
negative result in hypergraph visualisation: accuracy collapses between 6 and 8 sets (one task fell
from 0.86 to 0.16).
See: [Perception and evaluation studies](../06-visualization/perception-and-evaluation-studies.md).

**Event-centric knowledge graph (EKG)** — a graph of event nodes, entity nodes and three edge
families (event–event, event–entity, entity–entity). An event node is a hyperedge that has been
given an identity; the reification route for n-ary facts about happenings.
See: [Hyper-relational vs n-ary vs hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).

**Evidence code** — the Gene Ontology's per-annotation record of *why* a curated fact is believed
(IDA, IMP, ISS, TAS, IEA …), grouped into experimental, phylogenetic, computational, author,
curatorial and automatic categories. The model a KHG mixing human and LLM facts should copy: an
evidence *type* per hyperedge, not a single confidence number.
See: [Curation, crowdsourcing and quality control](../03-construction/curation-crowdsourcing-and-quality.md).

**EWO (Entity-Weighted Overlap)** — PRoH's query-conditioned score for the next hyperedge to traverse:
the aggregate (mean combined with maximum) of LLM-assigned relevance weights over the entities shared
by the current and candidate hyperedges, with entities below an embedding-similarity threshold scored
zero.
See: [Hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md).

**Expander, hypergraph** — two largely separate programmes share the phrase: combinatorial/spectral
r-uniform hypergraph expanders, and topological high-dimensional expanders (HDX) defined on
simplicial complexes. HDX results need downward closure and so do **not** transfer to knowledge
hypergraphs.
See: [Random walks, spectral theory and expansion](../01-foundations/random-walks-spectral-and-expansion.md).

---

## F

**F-arc** (forward arc) — a directed hyperedge with a single tail and many heads. Several hyperpath
problems that are linear-time on B-hypergraphs are NP-hard on F-hypergraphs.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**Factor graph** — a bipartite graph representing the factorisation of a function, with variable
nodes and factor nodes. Structurally the incidence graph of a hypergraph, with function-valued
"hyperedges"; the natural home for message passing.
See: [Comparison matrix](../10-comparative-and-critique/formalism-comparison-matrix.md).

**FB-AUTO** — a small Freebase-derived knowledge-hypergraph benchmark (3,410 entities, 8 relations,
automotive domain) built by *inverse reification* of CVTs. Its arity distribution is extremely lumpy
— no ternary facts at all, dominated by arity 5 — so it is a sanity check rather than a benchmark.
See: [Benchmarks derived from Freebase and Wikidata](../02-knowledge-representation/benchmarks-derived-from-freebase-and-wikidata.md).

**FB15K / FB15K-237** — the standard *binary* Freebase benchmarks, produced by star-to-clique
conversion of mediator structures. FB15K-237's entities are the seed set from which WD50K was built.
See: [From knowledge graphs to hypergraphs](../03-construction/from-knowledge-graphs-to-hypergraphs.md).

**Filtered setting** — the ranking protocol that removes other known-true facts from the candidate
list before scoring a corrupted one. What is filtered, and which positions are predicted, differ
between papers and are a main reason two "MRR on JF17K" numbers are not comparable.
See: [Benchmarks and evaluation protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).

**Fractional edge cover** — the LP relaxation of edge cover on a query hypergraph; its optimum is
the exponent in the [AGM bound](#a) and the basis of fractional hypertree width.
See: [N-ary relations, relational algebra and the query hypergraph](../01-foundations/n-ary-relations-and-relational-algebra.md).

**Frame** — Minsky's 1974 data structure for a stereotyped situation, with named **slots** filled by
values, defaults or other frames. An n-ary record with inheritance; the ancestor of role-value-pair
models such as NaLP.
See: [The knowledge-representation lineage](../08-history-and-frontier/knowledge-representation-lineage.md).

**Frame element (FE)** — FrameNet's name for a role. FEs are *local to a frame*, which gives a large
and partly redundant inventory; *core* FEs correspond to required roles.
See: [Ontologies and schemas for n-ary knowledge](../02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md).

**Frame Element Group (FEG)** — a combination of frame elements observed together in real sentences;
FrameNet's record that one frame surfaces at several arities, which is the same phenomenon as role
reuse across arities in n-ary KGs.
See: [Hyper-relational vs n-ary vs hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).

**FrameNet** — the largest curated inventory of named semantic roles, organised by frame. Maps onto
a KHG schema as frame ≈ relation type, FE ≈ role, frame instance ≈ n-ary fact — with the caveat that
frames are lexical, built to explain syntax rather than to be a database schema.
See: [Ontologies and schemas for n-ary knowledge](../02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md).

---

## G

**GAHE** — a 2025 geometry-aware hyper-relational model embedding qualifier slots in Euclidean,
hyperbolic and spherical subspaces with position-dependent sub-relations; bibliographic details known
only from the two-axis taxonomy's reference list `[unverified]`.
See: [Geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).

**G-E** (Generation Evaluation) — HyperGraphRAG's LLM-judged metric: an average over seven
dimensions (correctness, relevance, factuality, comprehensiveness, knowledgeability, logical
coherence, diversity), itself averaged with the question's F1.
See: [Evaluating constructed knowledge hypergraphs](../03-construction/evaluation-of-constructed-khgs.md).

**γ-acyclicity** (gamma-acyclicity) — the strongest of Fagin's three degrees, characterised by
DM-reducibility and by a rooted join tree for every hyperedge. Strictly stronger than β-acyclicity,
strictly weaker than Berge acyclicity.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**GETD** — a 2020 n-ary embedding model generalising Tucker decomposition by reshaping the core
tensor and applying tensor-ring decomposition. Cannot handle facts of different arity at once, which
S2S later fixed.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**Gleaning** — GraphRAG's loop of re-prompting the extractor ("many entities were missed — add
them") to compensate for single-pass under-recall, allowing larger chunks without a quality drop.
Copied by HyperGraphRAG and Hyper-RAG.
See: [LLM-based knowledge hypergraph construction](../03-construction/llm-based-khg-construction.md).

**Global Skill Library** — Hyper-KGGen's external memory of free-text `{trigger, action}` extraction
rules (at most 50 words each), distilled from the gold relations that K resampled extraction runs
recover only sometimes, and injected into the prompt at inference.
See: [Skill-driven extraction and the scenario gap](../03-construction/skill-driven-extraction-and-the-scenario-gap.md).

**GQL** (ISO/IEC 39075:2024) — the first new ISO database language since SQL, published 12 April
2024. It standardises the **property graph**, whose edges connect exactly two nodes, and explicitly
does not include n-ary relationships. The newest graph standard re-affirmed the binary edge.
See: [Standards bodies and specifications](../09-ecosystem/standards-bodies-and-specifications.md).

**GRAN** — a 2021 model that represents each n-ary fact as a small heterogeneous graph over its own
elements and runs fully connected attention with **edge-type-aware biases** (triple–triple,
triple–qualifier, qualifier–qualifier). Still the standard strong baseline.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**GraphML hyperedge** — GraphML is the only mainstream graph format with a native `<hyperedge>`
element carrying `<endpoint>`s with `in`/`out`/`undir` direction. It is also the least implemented
part of the format: NetworkX's reader raises on hyperedges. "GraphML supports hyperedges" is true of
the standard and false of the tool chain.
See: [File formats overview](../04-storage-and-formats/file-formats-overview.md).

**Graph-R1** — an ICML 2026 system from the HyperGraphRAG authors: a knowledge-hypergraph environment
with a GRPO-trained think–query–retrieve agent; average F1 57.82 against HyperGraphRAG's 29.40 on six
open-domain datasets, evidence that the gain came from the search rather than the representation.
See: [Hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md).

**GraphRAG** — Microsoft's 2024 graph-based retrieval-augmented generation system: LLM extraction of
entities and binary relations per chunk, community detection, community summaries, global answers.
The template every hypergraph RAG system modifies, and the system whose binary edges motivate them.
See: [Retrieval-augmented generation](../07-applications/retrieval-augmented-generation.md).

**GraphRAG-Bench** — the largest independent benchmark of graph RAG (ICLR 2026): medical guidelines
plus pre-20th-century novels, four difficulty levels, seven systems, stage-specific metrics. Finds
vanilla RAG competitive or better on simple fact retrieval and graph RAG ahead on complex reasoning,
at 4×–380× the prompt tokens. **It contains no hypergraph system**, which is itself the finding.
See: [A critical reading of hypergraph-RAG claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md).

**GYO reduction** (Graham–Yu–Özsoyoğlu) — repeatedly remove a hyperedge contained in another, or a
vertex appearing in only one hyperedge. A hypergraph is α-acyclic exactly when GYO reduces it to
empty, which is also how a join tree is computed.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

---

**Gyro-polygon** — PolygonE's encoding of an n-ary fact as a polygon in a gyrovector (hyperbolic)
space whose vertices are the entities, scored by the vertex-to-gyrocentroid geodesic.
See: [Geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).

## H

**H²GNN** — a 2024 hyperbolic hypergraph neural network for knowledge hypergraphs: "hyper-star"
message passing (position-typed star expansion) with two-stage aggregation in Lorentz space; arXiv
preprint only, and its reported FB-AUTO and JF17K numbers sit below ReAlE's.
See: [Geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).

**H²RAG** — a PAKDD 2026 hypergraph RAG system that adds bounded-recursion community detection and a
hierarchical summary layer above the hyperedges, retrieved by a dual-layer scorer, claiming gains over
HyperGraphRAG and HiRAG on UltraDomain; no preprint or code found as of 2026-09-21.
See: [Hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md).

**HAHE** — a 2023 hyper-relational model with two attention modules, a *global* one over the
hypergraph structure and a *local* one over a fact's element sequence. Best method across JF17K,
WikiPeople and WD50K in the field's own survey comparison.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**HART** — a 2025 inductive model combining hypergraph GNNs and transformers with a role-aware
mechanism; a 3–4× MRR jump over QBLP and StarE on WD20K suggests earlier "inductive" models were
barely inductive.
See: [Inductive and few-shot settings](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md).

**HAT** (Hypergraph Analysis Toolbox) — a tensor-oriented Python/MATLAB hypergraph library
(controllability, observability, entropy) and one of the five HIF-implementing projects. Ships with
no licence file.
See: [Software libraries](../09-ecosystem/software-libraries.md).

**HCNet** — the architecture from "Link Prediction with Relational Hypergraphs", which lifts
conditional message passing to k-ary relations and is characterised by relational Weisfeiler–Leman
algorithms and logical expressiveness. The theoretical backbone HYPER builds on.
See: [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

**H-eigenpair** — `T c^{m−1} = λ c^{[m−1]}` for an adjacency tensor, with entry-wise powers. Unlike
the Z-eigenpair the positive eigenvector is unique up to scaling and the power method converges.
See: [Incidence, matrices, tensors and graph expansions](../01-foundations/incidence-and-matrix-representations.md).

**Helly property** — every pairwise-intersecting subfamily of hyperedges has a common element.
Dual to conformality; decidable in polynomial time for fixed p, NP-hard when p varies.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**HGNN** — the 2019 hypergraph neural network that started the deep-learning wave: spectral
convolution via the normalised hypergraph Laplacian, i.e. clique expansion with principled weights.
Collapses on knowledge hypergraphs (MRR ~0.10) because it ignores relation labels.
See: [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

**HGNN⁺** — the 2023 generalisation of HGNN to multi-modal hyperedge groups; the standard reference
framework behind the DHG library.
See: [The machine-learning era](../08-history-and-frontier/machine-learning-era.md).

**HIF** (Hypergraph Interchange Format) — the only cross-library interchange standard for
higher-order networks: JSON with a draft-07 schema, five top-level keys of which only `incidences`
is required, direction carried per incidence, and attributes at network, node, edge and incidence
level. **Incidence-list-first**, which is what lets a role label live where it belongs. It has no
relation types, no roles, no schema, no nesting and exactly one schema version (`v0.0`) with four
competing schema URLs in circulation.
See: [HIF — the Hypergraph Interchange Format](../04-storage-and-formats/hif-hypergraph-interchange-format.md).

**Higher-order** — **contested term with three unrelated senses**: (1) a group interaction among
three or more units, (2) memory over sequences, as in a higher-order Markov chain, (3) a tensor of
order ≥ 3. A paper titled "higher-order X" may belong to any of three literatures.
See: [Glossary of confusable terms](../10-comparative-and-critique/glossary-of-confusable-terms.md).

**Higher-order link prediction** — predict which *sets* will interact, not which pairs. The
network-science community's falsifiable benchmark task, defined with 19 timestamped datasets, and
the closest thing to a clean higher-order evaluation.
See: [Social, collaborative and communication data](../07-applications/social-collaborative-and-communication.md).

**HINGE** — a 2020 hyper-relational model: a CNN with min-pooling over primary-triple/qualifier
interactions. The paper that popularised "hyper-relational data (a.k.a. multi-fold or n-ary
relational data)".
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**HiRAG** — an EMNLP 2025 Findings hierarchical *graph* RAG that builds layers of LLM-written "summary
entities" by GMM clustering (HiIndex) and retrieves local, global (community) and bridge knowledge
(HiRetrieval); the hierarchy baseline the hypergraph papers benchmark against.
See: [Hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md).

**Hits@k** — the fraction of ranking queries whose correct answer appears in the top k. Read Hits@1
when you care whether the model is *right*; the gap to MRR is informative.
See: [Benchmarks and evaluation protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).

**hMETIS / `.hgr`** — the classical multilevel hypergraph partitioner and its plain-text file
format: a header of counts plus one line of pin indices per hyperedge. No labels, no roles, no
direction, integer weights only. A *partitioning* format, never a knowledge format.
See: [File formats overview](../04-storage-and-formats/file-formats-overview.md).

**HNHN** — a 2020 hypergraph neural network giving hyperedges their own hidden representations and
nonlinearities, alternating vertex→hyperedge and hyperedge→vertex updates over the star expansion.
See: [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

**HODDI** — a 2025 higher-order drug–drug-interaction dataset built from a decade of FDA adverse
event reports: 109,744 records, 2,506 drugs, 4,569 side effects, each record a *set* of
co-administered drugs rather than a pair. Hypergraph models beat graph models on it; an MLP beat
both, which is a warning about baseline strength.
See: [Biomedicine and the life sciences](../07-applications/biomedical-and-life-sciences.md).

**HSimplE** — the 2020 companion of HypE: shifts an entity's embedding by its position in the tuple
and combines it with a relation embedding.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**HTKGH** — Hyper-Relational Temporal Knowledge Generalized Hypergraph: a 2026 generalisation of
hyper-relational temporal knowledge graphs supporting more than two primary entities per temporal
fact, with the `htkgh-polecat` forecasting dataset.
See: [Temporal hyperedges and editable agent memory](../07-applications/temporal-hyperedges-and-editable-agent-memory.md).

**HyConvE** — a 2023 knowledge-hypergraph model using 3D convolution with role-aware and
position-aware filters to capture intra-fact interactions.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**HyCubE** — a 2024 efficiency-focused model using 3D circular convolution with masked stacking.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**HyNT** — a 2023 KDD model, the first to treat **numeric literals** as first-class in both the
primary triple and the qualifiers, with a context transformer and a prediction transformer. Matters
because every earlier model dropped timestamps and quantities.
See: [Temporal and dynamic knowledge hypergraphs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md).

**HypE** — the 2020 IJCAI model that popularised the term *knowledge hypergraph*: position-specific
convolutional filters, so an entity's representation depends on the role it plays. Its reification
baseline r-SimplE collapsing (JF17K MRR 0.102 vs 0.494) is the field's standard argument against
decomposing n-ary facts — though the authors attribute the collapse to unlearnable auxiliary
entities, not to information loss.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**HYPER** — the 2025 **foundation model** for knowledge hypergraphs: generalises to unseen entities
*and* unseen relations of arbitrary arity by encoding each entity together with its position, via a
sinusoidal *positional interaction encoder* that is injective and extrapolating. Ships 16 inductive
datasets; its zero-shot results beat end-to-end training on one benchmark.
See: [Inductive and few-shot settings](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md).

**Hyper-Extract** — a 2026 CLI and library turning unstructured text into graphs, hypergraphs or
spatio-temporal structures with an LLM. Notable for adoption: ~4,000 GitHub stars in eight months,
nine times HyperGraphRAG's, suggesting the bottleneck is packaging rather than expressiveness.
Apache-2.0; nine typed output structures, ten engines, 40 bilingual domain templates; the only KHG
tool with per-document provenance and rollback, and still not consistent on insert (checked
2026-09-21). See: [Skill-driven extraction and the scenario gap](../03-construction/skill-driven-extraction-and-the-scenario-gap.md).
See: [Software libraries](../09-ecosystem/software-libraries.md).

**Hyper-FM** — a 2025 hypergraph foundation model with hierarchical vertex-knowledge embedding and
multi-hypergraph structural extraction, over 11 text-attributed hypergraph datasets; proposes the
first scaling law for hypergraph models, whose finding is that domain diversity beats raw size.
See: [The current research frontier](../08-history-and-frontier/current-frontier-directions.md).

**Hyper-KGGen** — a 2026 coarse-to-fine LLM extractor with a distilled "global skill library"; its
durable contribution is **HyperDocRED**, the first annotated document-level knowledge-hypergraph
construction benchmark. Published at KDD 2026 (DOI 10.1145/3770855.3818198).
See: [Evaluating constructed knowledge hypergraphs](../03-construction/evaluation-of-constructed-khgs.md).

**Hyper-M2RAG** — a 2026 multimodal extension of Hyper-RAG whose contribution is *anchor-driven
incremental refinement*: rebuild only the local hyper-topology around boundary-crossing anchor nodes
instead of a global sweep.
See: [Incremental, streaming and temporal construction](../03-construction/incremental-and-streaming-construction.md).

**Hyper-RAG** — a 2025 hypergraph-RAG system (published in a general-science journal in 2026) that
extracts entities plus *low-order* (pairwise) and *high-order* (multi-entity) correlations and
stores them in a native hypergraph store, Hypergraph-DB. Framed as a hallucination remedy; evaluated
with LLM-judged scoring on author-assembled corpora.
See: [Retrieval-augmented generation](../07-applications/retrieval-augmented-generation.md).

**Hyper-relational fact** — a **primary triple** `(h, r, t)` plus a set of **qualifier** key–value
pairs. Wikidata's statement shape and the canonical formalisation of HINGE and StarE. **Contested
against "n-ary"**: the StarE authors argue explicitly that hyper-relational graphs and hypergraphs
are conceptually different, because folding qualifiers into the relation symbol causes a
combinatorial explosion of typed hyperedges, while the reverse conversion loses the attribution of
entities to triple versus qualifier. Neither formalism contains the other for free.
See: [Hyper-relational vs n-ary vs hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md)
and [Open debates](../10-comparative-and-critique/open-debates.md).

**HyperAgent** — a 2026 agent framework in which tools are hyperedges from their required input
schema nodes to their output schema nodes, so tool chaining becomes minimal-hyperpath search over
schema types.
See: [AI agents — memory and planning](../07-applications/ai-agents-memory-and-planning.md).

**Hyperarc** — a directed hyperedge, written `e = (T(e), H(e))` for a tail set and a head set.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**HyperDocRED** — the first document-level knowledge-hypergraph extraction benchmark, built by
manually restructuring Re-DocRED into n-ary relations: 50 training and 100 test documents. Small
enough to rank systems and not to train them, and currently a single point of failure for the field.
Announced as released, but not distributed as of 2026-09-21; the repository ships code only.
See: [Evaluating constructed knowledge hypergraphs](../03-construction/evaluation-of-constructed-khgs.md).

**Hyperedge** — a member of `E` in a hypergraph: any non-empty subset of the vertices. In this KB a
knowledge hyperedge additionally has an identity, a relation type, role-labelled bindings and
optionally qualifiers, provenance, time and confidence.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**Hyperedge formalisation** — the survey term for representing an n-ary fact as an ordered tuple
`(H, e₁, …, e_n)` in which position carries the role and arity is fixed per relation. Contrast
[role-value pair](#r) and [hyper-relational](#h).
See: [Hyper-relational vs n-ary vs hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).

**HyperGCN** — a 2019 hypergraph neural network that replaces each hyperedge, per layer, by a single
mediator-augmented edge chosen from the current embedding (adaptive rather than full clique
expansion).
See: [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

**Hypergraph** — a pair `H = (V, E)` where `E` is a family of non-empty subsets of `V`. A graph is
the 2-uniform case. **Textbooks disagree** on whether empty hyperedges, isolated vertices and
repeated hyperedges are allowed (Berge, Voloshin, Bretto each differ), and the word is used for at
least three incompatible refinements: plain set hyperedges, ordered and labelled hyperedges, and
directed tail/head pairs.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**Hypergraph-DB** — a lightweight embedded Python hypergraph store with property dicts, pickle
(`.hgdb`) persistence and HIF import/export. The graph layer behind Hyper-RAG, and the pattern to
copy: treat HIF as interchange, not as storage.
See: [Hypergraph and n-ary databases](../04-storage-and-formats/hypergraph-databases.md).

**HypergraphDB** — Iordanov's 2010 Java embedded database and the reference design for a native
hypergraph store: atoms with tuple target sets, links that may target links, and a two-layer
key-value storage model with an incidence index. Historically important, lightly maintained.
See: [Hypergraph and n-ary databases](../04-storage-and-formats/hypergraph-databases.md).

**hypergraphx (HGX)** — a Python hypergraph-analysis library with undirected, directed, temporal and
multiplex classes, community detection, motifs and centrality. Reads HIF but re-indexes node
identifiers to integers, so HIF round-trips are not lossless across libraries.
See: [Software libraries](../09-ecosystem/software-libraries.md).

**hypergraphx-data** — the hypergraphx dataset catalogue, 136 datasets tagged by type (undirected,
directed, temporal, weighted, multiplex) and domain. Reports different counts from XGI-DATA for the
same underlying data, so always record which catalogue a number came from.
See: [Datasets and benchmarks](../09-ecosystem/datasets-and-benchmarks.md).

**HypergraphConv** — PyTorch Geometric's hypergraph convolution layer. It takes `hyperedge_index`,
a `(2, E)` tensor of node/hyperedge index pairs — that is, COO with the values dropped, which is
column-for-column the HIF incidence array with integer ids.
See: [Tensor and sparse-matrix representations](../04-storage-and-formats/tensor-and-sparse-representations.md).

**HyperGraphRAG** — the 2025 reference hypergraph-RAG system: LLM extraction of "knowledge
fragments" as hyperedges with confidence scores, storage as a **bipartite graph**, separate vector
indexes for entities and hyperedge sentences, and fused entity/hyperedge/chunk retrieval. Reports
+7.45 F1 over chunk RAG across five domains at roughly 3× the query cost — with the gain *larger* on
binary-source questions than on n-ary ones.
See: [Retrieval-augmented generation](../07-applications/retrieval-augmented-generation.md)
and [A critical reading of hypergraph-RAG claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md).

**HyperMem** — a 2026 ACL system using a hypergraph as long-term conversational memory, organised as
topics → episodes → facts with hyperedges grouping related episodes and their facts.
See: [AI agents — memory and planning](../07-applications/ai-agents-memory-and-planning.md).

**HyperMLN** — a 2022 Markov logic network over n-ary facts coupled to a knowledge-hypergraph
embedding by variational EM. The field's own survey calls it "the only method that explicitly
addresses explainability in link prediction in NKGs" — one method out of nearly fifty. Its rules are
*predefined*, not mined.
See: [Explainability and uncertainty](../05-query-embeddings-reasoning/explainability-and-uncertainty.md).

**HyperMono** — a 2024 model that re-derives ShrinkE's qualifier monotonicity with **cone
embeddings**: each added qualifier narrows the cone's angle and hence the answer set.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**HyperNetX (HNX)** — PNNL's Python hypergraph library and the reference implementation of s-line
graphs and s-centralities. Treats the incidence structure as primitive, `H = (V, E, I)`, and ships
hull, two-column, UpSet and storyline drawings.
See: [Tools and libraries for drawing hypergraphs](../06-visualization/tools-and-libraries.md).

**hypernetx-widget** — the interactive Jupyter widget for HyperNetX (drag, select, hide, collapse,
recolour). A 2023 beta with no release since; the clearest instance of the KB's "no maintained
interactive hypergraph viewer" gap.
See: [Tools and libraries for drawing hypergraphs](../06-visualization/tools-and-libraries.md).

**Hypernetwork** — **the worst term in the field: four unrelated senses.** (1) Johnson's relational
simplices in complex systems, where the relation is part of the object and order matters;
(2) PNNL's usage for hypergraph-structured real-world systems; (3) an (s,d)-hypernetwork in
F-hypergraph theory, a minimal connecting sub-hypergraph; (4) in deep learning, a network that
generates another network's weights. Never use it without saying which.
See: [Glossary of confusable terms](../10-comparative-and-critique/glossary-of-confusable-terms.md).

**Hypernode graph** — a structure whose *edge endpoints* are sets of nodes, i.e. a binary relation
over sets with signed weights. Not a hypergraph: a hyperedge is one set, a hypernode edge is a pair
of sets.
See: [Glossary of confusable terms](../10-comparative-and-critique/glossary-of-confusable-terms.md).

**Hyperon** — OpenCog's current rewrite: an Atomspace metagraph plus the **MeTTa** language, with
programs represented as sub-metagraphs. Self-described as pre-alpha; research infrastructure, not a
production store.
See: [Metagraphs, ubergraphs and hypergraph databases](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md).

**Hyperpath** — a path in a directed hypergraph: a sequence of hyperarcs from a source to a
destination. Enumerating induced s-t hyperpaths is not output-polynomial unless P = NP, but on
B-hypergraphs enumeration is polynomial-delay — a usable licence for an explanation engine.
See: [Hypergraph algorithms for knowledge work](../05-query-embeddings-reasoning/hypergraph-algorithms-for-knowledge.md).

**HyperRAG** — a 2026 WWW system that assumes an n-ary hypergraph exists and trains retrievers over
it: a structural-semantic *HyperRetriever* and a memory-guided beam search. Notable for one of the
few direct **arity ablations**: reducing its hypergraph to a binary KG costs about 2.3 MRR points.
See: [Retrieval-augmented generation](../07-applications/retrieval-augmented-generation.md).

**HyperRED** — the main supervised benchmark for hyper-relational extraction: 39,840 distantly
supervised training sentences plus human-annotated dev and test splits, 62 relation and 44 qualifier
labels, with a published annotation rubric that separates invalid triplets from invalid qualifiers.
See: [N-ary relation and event extraction from text](../03-construction/n-ary-relation-extraction-from-text.md).

**HyperRes** — a formal system for versioned dependency resolution over a hypergraph, with a
parse → resolve → deploy pipeline and a SAT-based solver, able to model dozens of package managers.
The KB's control case: a hypergraph deployed for its algebra, with nobody writing a position paper.
See: [Software engineering and code knowledge](../07-applications/software-engineering-and-code-knowledge.md).

**HyperSkill** — a 2026 agent system storing procedural memory as a hypergraph with two node types
(subtask steps, reusable skills) and one hyperedge per trajectory, retrieved dual-path.
See: [AI agents — memory and planning](../07-applications/ai-agents-memory-and-planning.md).

**Hyper-star message passing** — H²GNN's scheme that instantiates each n-ary fact as a hyperedge node
linked to its entities by position-typed relations, forming a two-level tree; described as a lossless
expansion but not proved to be one.
See: [Geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).

**HyperStorylines** — a temporal encoding in which entities are lines through time and each
hyperedge is a rectangle intersecting its participants; supports aggregation and nesting of entity
types, and beat PAOHVis for identifying and characterising relationships in the only head-to-head
comparison of two dynamic-hypergraph techniques.
See: [Dynamic and temporal hypergraph visualization](../06-visualization/dynamic-and-temporal-hypergraph-visualization.md).

**HyperSU** — a 2026 system treating hyperedge formation as an entity-aware **minimum-description-
length** optimisation, the first principled answer to "what should count as one hyperedge".
See: [The current research frontier](../08-history-and-frontier/current-frontier-directions.md).

**Hypertree width** (`hw`, `ghw`, `fhw`) — the width parameters measuring how far a query hypergraph
is from acyclic. Only `hw ≤ k` is polynomial-time checkable for fixed k; `ghw ≤ 2` and `fhw ≤ 2` are
NP-complete. The same parameter indexes hypergraph-neural-network expressivity, which is the KB's
most striking cross-field connection.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md)
and [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

---

## I

**Incidence** — the pair `(v, e)` recording that vertex `v` belongs to hyperedge `e`. The right
place to hang a role label, a direction bit and an edge-dependent weight, and the unit HIF, the SQL
incidence table and `hyperedge_index` all count.
See: [HIF — the Hypergraph Interchange Format](../04-storage-and-formats/hif-hypergraph-interchange-format.md).

**Incidence matrix** `H` — the `n × p` 0/1 matrix with `H[v,e] = 1` iff `v ∈ e`. The only
representation that is lossless for a labelled hypergraph, and the object from which every adjacency
matrix, Laplacian and expansion is derived. It cannot carry roles without attributed entries.
See: [Incidence, matrices, tensors and graph expansions](../01-foundations/incidence-and-matrix-representations.md).

**Incidence table** — the SQL form of the same thing: a `fact` table plus an `incidence` table of
`(fact_id, entity_id, role, direction, position)`. The KB's recommended system of record, because it
handles unbounded and open-vocabulary arity with no migrations.
See: [Relational, EAV and Datalog storage](../04-storage-and-formats/relational-and-eav-storage.md).

**Inductive link prediction** — predicting facts involving entities (node-inductive) or entities
*and* relations (relation-inductive, fully inductive) that were unseen in training. Knowledge
hypergraphs add a fourth axis binary KGs do not have: unseen **arity**.
See: [Inductive and few-shot settings](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md).

**Interaction hypergraph** — the KB's term for a hypergraph whose hyperedges are *observed groups*
rather than *asserted facts*: no relation type, no roles, participants interchangeable.
Co-authorship, baskets and contact records are interaction hypergraphs; a five-question test
separates them from knowledge hypergraphs.
See: [Hypergraph construction from structured data](../03-construction/hypergraph-construction-from-data.md).

**Interpolation vs extrapolation (temporal KGs)** — interpolation completes missing elements at
timestamps inside the observed range; extrapolation predicts facts at future timestamps. Agent
memory's "who owns it now" is extrapolation-shaped; VITA and HypeTKG are interpolation-only, NE-Net,
MT-Path and HTKGH are extrapolation.
See: [Temporal and dynamic KHGs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md).

**iText2KG** — an incremental LLM KG constructor that keeps a global entity set and matches new
local entities by cosine similarity above a validated threshold, reporting a false-discovery rate.
See: [Entity resolution and canonicalisation](../03-construction/entity-resolution-and-canonicalisation.md).

---

## J

**JF17K** — the first n-ary benchmark, carved from Freebase in 2016, and still one of the three
standard ones. **Two documented defects**: no official validation split, so every paper tunes on a
different unpublished one; and a test leak in which about **44.5% of test statements share their
main (s, r, o) triple with training**. Its statistics are also published inconsistently — 322, 327
or 501 relations depending on the source.
See: [Dataset quality, leakage and provenance problems](../09-ecosystem/dataset-quality-and-leakage-issues.md).

**Jena (Apache Jena)** — the Java RDF framework, TDB2 store and Fuseki server; as of 2026 the most
complete implementation of RDF 1.2 syntax, input and output.
See: [RDF-star, RDF 1.2 and the semantic-web serialisations](../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md).

**Join tree** — a tree labelled by a query's atoms such that, for any two nodes, every node on the
path between them contains their shared variables. Exists exactly when the query hypergraph is
α-acyclic, and is what the Yannakakis algorithm consumes.
See: [N-ary relations, relational algebra and the query hypergraph](../01-foundations/n-ary-relations-and-relational-algebra.md).

**JSON-LD** — the W3C JSON serialisation of RDF. It has no triple-term syntax, so the only encoding
available for an n-ary fact is the relation-instance pattern — which is a feature: a nested JSON
object with a fixed `@context` *is* RDF, which suits LLM pipelines that emit JSON.
See: [RDF-star, RDF 1.2 and the semantic-web serialisations](../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md).

---

## K

**KaHyPar** — the n-level hypergraph partitioner: coarsening to one level per vertex, LSH pin
sparsification, Louvain preprocessing, localized k-way local search and flow-based refinement, with
an optional memetic layer. Reads `.hgr` and supports pinned (fixed) vertices.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**KelpFusion** — a set-overlay technique whose single parameter interpolates "from the minimal
spanning tree to the convex hull" — literally the dial between the edge and subset drawing
standards. Beat Bubble Sets on accuracy and time.
See: [Set visualisation and hypergraph visualisation](../06-visualization/set-visualization-connection.md).

**Key role set** — the subset of a relation's roles whose binding may be held by at most one valid
fact at any instant; the n-ary analogue of a binary edge's implicit (subject, relation) functional
dependency, and the precondition for detecting supersession. No existing n-ary schema language
declares one.
See: [Temporal hyperedges and editable agent memory](../07-applications/temporal-hyperedges-and-editable-agent-memory.md).

**KG-ICL** — a 2024 prompt-based knowledge-graph foundation model for in-context reasoning (Cui, Sun,
Hu, NeurIPS 2024); run zero-shot on reified hypergraphs in HYPER's appendix it averages MRR 0.14
against HYPER's 0.24.
See: [HYPER anatomy](../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md).

**KGTK** — the Knowledge Graph Toolkit: Wikidata-scale ETL over a TSV edge format with an explicit
`id` per edge, so edges can be the subject of other edges — the qualifier mechanism in tabular form.
See: [Software libraries](../09-ecosystem/software-libraries.md).

**Knowledge graph (KG)** — a graph-shaped knowledge base of typed binary edges. The term was
popularised by Google in 2012; the academic embedding literature that grew around it took the triple
as the atom, and with it the binary restriction this KB is about.
See: [The knowledge-representation lineage](../08-history-and-frontier/knowledge-representation-lineage.md).

**Knowledge hypergraph (KHG)** — **the KB's central contested term: at least five incompatible
senses.** (a) a set of n-ary tuples `r(e₁,…,e_k)` with fixed arity per relation; (b) hyper-relational
facts, a triple plus qualifiers; (b′) unordered role-value sets with no privileged pair; (c) the
LLM/RAG sense, an untyped entity set with a free-text description and a confidence score; (d) a
metagraph in which edges may contain edges; (e) the conceptual-graph / RDF-as-hypergraph tradition.
The KB's working definition is a superset: typed hyperedges over entities, with named role bindings,
optional qualifiers, provenance, validity time and confidence, and hyperedges allowed to fill roles
of other hyperedges.
See: [What is a knowledge hypergraph?](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md)
and [Open debates](../10-comparative-and-critique/open-debates.md).

**k-uniform hypergraph** — every hyperedge has exactly k vertices. The setting for extremal
combinatorics and for adjacency-tensor spectral theory. Knowledge hypergraphs are the opposite:
arities are mixed, so tensor methods need a uniformisation step that is not part of the mathematics.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**Kùzu** — an embedded property-graph database archived by its owner in October 2025. The KB's
concrete tooling-risk example: choosing a formalism only one implementation supports couples your
data model to a company.
See: [Property graph vs TypeDB vs RDF-star](../10-comparative-and-critique/property-graph-vs-typedb-vs-rdf-star.md).

---

## L

**Laplacian, hypergraph** — **not one operator but at least five.** Chung, Bolla, Rodríguez,
Zhou–Huang–Schölkopf and the non-linear Chan–Louis construction. Agarwal et al. showed the first
four reduce to clique or star expansions with particular weightings, and that for k-uniform
hypergraphs clique and star are spectrally identical; Chan et al. proved no *linear* operator can
capture hypergraph expansion in a Cheeger-like way, which is why the working theory is non-linear.
See: [Incidence, matrices, tensors and graph expansions](../01-foundations/incidence-and-matrix-representations.md).

**Leakage** — train/test overlap that lets a model memorise rather than generalise. The canonical
case here is JF17K's 44.5% shared main triples; WD50K was built to eliminate it by construction, and
a three-line pandas check should be standard before reporting any number.
See: [Dataset quality, leakage and provenance problems](../09-ecosystem/dataset-quality-and-leakage-issues.md).

**Levi graph** — the bipartite incidence graph of a hypergraph: one node per vertex, one per
hyperedge, an edge per membership. Also called the incidence graph, the König representation, the
star expansion and the extra-node encoding. **Lossless**, provided the two sides are labelled;
unlabelled, it confuses a hypergraph with its dual. The encoding almost every KHG system actually
stores.
See: [Hypergraphs vs bipartite vs simplicial](../01-foundations/hypergraphs-vs-bipartite-vs-simplicial.md)
and [Visualising knowledge hypergraphs in practice](../06-visualization/knowledge-hypergraph-specific-visualization.md).

**LightRAG** — the binary-edge graph-RAG system that both major hypergraph-RAG systems fork from:
key–value profiles instead of community summaries, deduplication, and incremental update by union of
node and edge sets. Its edges are binary; calling them hyperedges would be wrong.
See: [LLM-based knowledge hypergraph construction](../03-construction/llm-based-khg-construction.md).

**Line graph / line expansion** — one vertex per hyperedge, joined when hyperedges intersect; the
2-section of the dual hypergraph. Loses the vertices themselves. Generalised to the
[s-line graph](#s).
See: [Incidence, matrices, tensors and graph expansions](../01-foundations/incidence-and-matrix-representations.md).

**Linear diagram** — a set encoding in which each set is a horizontal segment and overlap in x means
intersection. Backed by the strongest empirical design guidance in set visualisation, and found
superior to Euler and Venn diagrams.
See: [Perception and evaluation studies](../06-visualization/perception-and-evaluation-studies.md).

**Linear hypergraph** — simple, and any two hyperedges share at most one vertex.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**LineSets** — a set overlay drawing each set as one smooth curve through its elements. Minimal ink,
and the direct ancestor of the metro-map metaphor.
See: [Set visualisation and hypergraph visualisation](../06-visualization/set-visualization-connection.md).

**LKHGT** (Logical Knowledge Hypergraph Transformer) — a 2025 complex-query-answering model over
genuine knowledge hypergraphs (not just hyper-relational graphs), with a projection encoder, a
logical encoder and a type-aware bias; ships the JF17k-HCQA and M-FB15k-HCQA query datasets.
See: [Logical reasoning and rules over n-ary facts](../05-query-embeddings-reasoning/logical-reasoning-and-rules-over-n-ary-facts.md).

**LLM-as-judge** — scoring generated answers with a language model, standard in graph- and
hypergraph-RAG evaluation. Known failure modes: position, verbosity and self-enhancement bias. The
last is acute when the same model family extracts the graph, writes the questions and grades the
answers.
See: [Evaluating constructed knowledge hypergraphs](../03-construction/evaluation-of-constructed-khgs.md).

**Local closed-world assumption (LCWA)** — see [partial completeness assumption](#p).
See: [Open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).

---

## M

**MAGE** — a 2026 "diachronic hypergraph" database used as a multi-agent memory engine over agents,
messages, tools, errors, procedures, documents, decisions and evidence; whether its lifecycle
management is bitemporal is `[unverified]`.
See: [Temporal hyperedges and editable agent memory](../07-applications/temporal-hyperedges-and-editable-agent-memory.md).

**Matching (hypergraph)** — a family of pairwise disjoint hyperedges. Maximum matching is set
packing, NP-hard from arity 3 (3-dimensional matching is one of Karp's original problems): one of
the two textbook polynomial graph problems that break at arity ≥ 3.
See: [Hypergraph algorithms for knowledge work](../05-query-embeddings-reasoning/hypergraph-algorithms-for-knowledge.md).

**Matrix Market** — the NIST sparse-matrix text format. Writing the incidence matrix in coordinate
form is the cheapest lossless route between a KHG and a linear-algebra stack; roles can be smuggled
into the value field and direction needs two matrices.
See: [File formats overview](../04-storage-and-formats/file-formats-overview.md).

**MetaNIR** — a 2025 meta-learning model that simulates inductive tasks to generate adaptive
embeddings for unseen entities in n-ary knowledge graphs.
See: [Inductive and few-shot settings](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md).

**Metagraph** — **contested term with two senses.** (1) A generalised hypergraph with **nesting**: a
hyperedge may contain other hyperedges. This is the sense used in this KB — HypergraphDB, OpenCog's
AtomSpace — and nesting is its defining feature. (2) A metapath template or meta-structure in
heterogeneous-graph mining, which is about queries over a schema, not about data.
See: [Metagraphs, ubergraphs and hypergraph databases](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md).

**MetaRH** — a 2024 few-shot model that applies meta-learning to refine relation representations for
n-ary facts with very few instances.
See: [Inductive and few-shot settings](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md).

**MetroSets** — a set-visualisation tool using the metro-map metaphor: each set is a line, each
element a station, over a path-based support. The only abstract set technique to win a three-way
controlled readability study, and it degrades gracefully with size.
See: [Catalogue of visual encodings](../06-visualization/visual-encodings-catalogue.md).

**MeTTa** (Meta Type Talk) — Hyperon's language: programs are sub-metagraphs of the Atomspace,
interpreted as metagraph rewrite rules, so rules and facts live in one store and self-modifying code
is natural. Types are built *within* the metagraph rather than given.
See: [Metagraphs, ubergraphs and hypergraph databases](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md).

**M-FB15K** — a Freebase-derived knowledge-hypergraph benchmark (10,314 entities, 71 relations,
~493k facts) built by inverse reification and restricted to Wikilinks entities. Dominated by arity 3
(400,027 of 493,520 facts), so aggregate scores on it say little about higher arities.
See: [Benchmarks derived from Freebase and Wikidata](../02-knowledge-representation/benchmarks-derived-from-freebase-and-wikidata.md).

**MINE** — a fact-coverage benchmark of 100 articles with 15 gold facts each, used to ask whether a
constructed graph retains the information in its source.
See: [Evaluating constructed knowledge hypergraphs](../03-construction/evaluation-of-constructed-khgs.md).

**MLN** (Markov logic network) — a set of pairs (first-order formula, weight) that, with a set of
constants, defines a Markov network. A ground relational database *is* a labelled ordered knowledge
hypergraph, and an MLN is a weighted set of patterns over it. **A weight is a log-linear parameter
on a formula, not a probability of a fact** — reading it as confidence is a category error.
See: [Open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).

**Modularity, hypergraph** — not a single function: one must decide when a hyperedge counts as
"inside" a community (all vertices, a majority, at least two), and each choice gives a different
modularity. The choice is a domain decision, not a detail.
See: [Hypergraph algorithms for knowledge work](../05-query-embeddings-reasoning/hypergraph-algorithms-for-knowledge.md).

**Motif, higher-order** — a small connected pattern of *overlapping hyperedges*; motif profiles
fingerprint a hypergraph's local structure and are not predicted by the clique expansion. No motif
analysis over role-labelled hypergraphs exists.
See: [Higher-order interactions](../01-foundations/higher-order-interactions.md).

**MRR** (mean reciprocal rank) — the mean of `1/rank` over ranking queries. Dominated by the head of
the ranking. Critically, MRR here averages over **prediction tasks**, not facts, so a dataset's
arity distribution silently reweights its own metric.
See: [Benchmarks and evaluation protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).

**MT-Path** — a 2025 mixture-policy reinforcement-learning model for multi-hop extrapolation over
n-tuple temporal knowledge graphs; current best on NWIKI and NICE.
See: [Temporal and dynamic KHGs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md).

**m-TransH** — the 2016 model that started the line: generalises TransH to n-ary facts by projecting
each entity onto a relation-specific hyperplane according to its role. Also introduced JF17K.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**Multi-fold relation** — Wen et al.'s 2016 term: a relation `R` with role set `M` is a subset of
`N^M`, so an instance is a *function from roles to entities*. Introduced precisely because the
positional definition leaves the role of each coordinate unspecified.
See: [What is a knowledge hypergraph?](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md).

**Multi-hypergraph** — the hyperedge family may contain the same vertex set more than once. Matters
directly for knowledge: two distinct facts can involve the same entities, so hyperedges need
identities of their own.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**Multilayer network** — a network whose nodes and/or edges are distributed over layers, with
intra- and inter-layer edges. **Not** a hypergraph: layers are about contexts or edge types, not
group size.
See: [Glossary of confusable terms](../10-comparative-and-critique/glossary-of-confusable-terms.md).

**Multiplex network** — the multilayer special case where every layer has the same node set and
inter-layer edges connect a node only to its own copies. Multiplex ≠ multi-relational ≠ n-ary; all
three are orthogonal.
See: [Glossary of confusable terms](../10-comparative-and-critique/glossary-of-confusable-terms.md).

**Multi-relational graph** — a graph with many *types* of binary edge: the standard KG setting.
About the number of relation types, not the number of arguments; a KG with 10,000 predicates and
only triples is maximally multi-relational and entirely binary.
See: [Glossary of confusable terms](../10-comparative-and-critique/glossary-of-confusable-terms.md).

---

## N

**NaLP** — the 2019 model that drops positional encoding entirely: a fact is a set of role-value
pairs, a convolution extracts per-pair features and an MLP scores the whole set. Introduced
WikiPeople. Its acknowledged weakness — it treats all pairs equally — is what RAM attacks.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**Named graph** — a pair of an IRI (or blank node) and an RDF graph; the RDF mechanism for
provenance and trust, standardised as part of RDF datasets. A named graph *is* a labelled hyperedge
whose members are triples. Good for "this group of facts came from source S", poor for per-fact
validity unless every fact gets its own graph.
See: [N-ary relations and reification](../02-knowledge-representation/n-ary-relations-and-reification.md).

**Nanopublication** — one assertion published as its own citable unit: an assertion graph, a
provenance graph and a publication-info graph, in RDF/TriG with hash-based identifiers. The maximal
version of per-fact provenance, and the design lesson is "one fact, one identifier, three graphs".
See: [Versioning, provenance and scale](../04-storage-and-formats/versioning-provenance-and-scale.md).

**n-ary knowledge graph (NKG)** — the survey term for a knowledge graph whose facts may contain more
than two entities. Its three formalisations — hyperedge, role-value pair, hyper-relational — are the
axis on which the whole literature splits.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**n-ary relation** — a relation of arity n > 2; set-theoretically a subset of `S₁ × … × S_n`, whose
elements are tuples. Codd's relational model had this in 1970 with a type system, which is why the
KB's recurring point is that the *computational* half of the n-ary problem was solved long ago and
the *representational* half was not. W3C's own statement of the gap is that in RDF and OWL "a
property is a binary relation".
See: [N-ary relations, relational algebra and the query hypergraph](../01-foundations/n-ary-relations-and-relational-algebra.md)
and [N-ary relations and reification](../02-knowledge-representation/n-ary-relations-and-reification.md).

**Negative sampling** — training by corrupting one argument of a true fact and treating the result
as false. In an n-ary setting it is **position-dependent**: corrupting a core role and corrupting a
qualifier value are not equally informative, and papers differ in whether qualifier positions are
corrupted at all.
See: [Open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).

**NeuInfer** — a 2020 hyper-relational model that scores the primary triple *and* its compatibility
with each qualifier separately, making explicit the claim that qualifiers restrict rather than
define a fact.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**NQE** — a 2023 model for complex query answering over hyper-relational KGs covering the full
existential fragment (∃, ∧, ∨, ¬) with a dual-heterogeneous transformer and fuzzy logic; ships
WD50K-NFOL.
See: [Logical reasoning and rules over n-ary facts](../05-query-embeddings-reasoning/logical-reasoning-and-rules-over-n-ary-facts.md).

**NWIKI and NICE** — the two temporal n-ary benchmarks introduced with NE-Net: overwhelmingly n-ary
(81.9% and 97.5%) at one-year and 24-hour granularity respectively. Contrast Wiki-hy and YAGO-hy,
which are mostly binary, so results on the two families should not be pooled.
See: [Temporal and dynamic knowledge hypergraphs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md).

**NYLON** — a 2024 model extending GRAN to *noisy* n-ary knowledge graphs, computing **fact-level
and element-level confidence** and using them to drive selective annotation. The element-level score
doubles as an attribution: it says which participant is probably wrong.
See: [Explainability and uncertainty](../05-query-embeddings-reasoning/explainability-and-uncertainty.md).

---

## O

**OCEL 2.0** — the object-centric event log standard, which qualifies event-to-object relationships.
Effectively a serialisation format for timestamped n-ary facts with roles, developed independently
of the KHG literature; no published pipeline builds a KHG from it.
See: [Hypergraph construction from structured data](../03-construction/hypergraph-construction-from-data.md).

**ODKE+** — a production open-domain knowledge-extraction system notable for two ideas: per-entity-
type **ontology snippets** in the prompt, and a staleness-driven extraction initiator that makes
streaming KB maintenance a question of "which facts are missing or old", not of document arrival.
See: [Incremental, streaming and temporal construction](../03-construction/incremental-and-streaming-construction.md).

**OG-RAG** — an ontology-grounded hypergraph RAG system whose hyperedges are ontology-grounded fact
clusters and whose retrieval finds a *minimal covering set* of hyperedges; reports the largest
attribution-speed gain in the family, which matters for compliance work.
See: [Finance, legal and compliance](../07-applications/finance-legal-and-compliance.md).

**Ontology matching** — aligning an induced schema onto a standard vocabulary; evaluated since 2004
by the OAEI. Its tracks align classes and properties, i.e. unary and binary constructs; **no
benchmark aligns n-ary signatures or qualifier vocabularies**.
See: [Schema induction and ontology alignment](../03-construction/schema-induction-and-ontology-alignment.md).

**OpenIE** — open information extraction: relation tuples with no predefined schema. Output is
uncanonical and mostly binary; conjunctions are expanded into several tuples, which is exactly the
opposite of what a KHG wants.
See: [N-ary relation and event extraction from text](../03-construction/n-ary-relation-extraction-from-text.md).

**Open-world assumption (OWA)** — a fact not present is *unknown*, not false. What RDF-based KBs do,
and the reason rule mining needs a device such as the PCA to manufacture negative evidence.
See: [Open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).

**Ordered hyperedge** — a hyperedge that is a tuple rather than a set, so position carries the role.
Neither ordered nor role-labelled hyperedges appear in the classical textbooks; they come from the
database and KR traditions.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**Oriented hypergraph** — each vertex–edge *incidence* carries a sign (+1 or −1). Weaker than
direction: it signs incidences without splitting a hyperedge into tail and head.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**ORKG** (Open Research Knowledge Graph) — the largest attempt to represent scholarly
*contributions* rather than metadata, with machine-actionable comparisons. Built on RDF, so an
n-ary contribution is represented by reification, not by a native hyperedge.
See: [Scientific knowledge and scholarly graphs](../07-applications/scientific-knowledge-and-scholarly-graphs.md).

**Oxigraph** — a Rust SPARQL database with Python bindings (`pyoxigraph`); one of the few stacks that
can actually parse RDF 1.2 triple terms, and the tool this KB used to validate its Turtle sample.
See: [Software libraries](../09-ecosystem/software-libraries.md).

---

## P

**PAOH** (Parallel Aggregated Ordered Hypergraph) — the reference temporal encoding: vertices as
parallel horizontal bars, hyperedges as vertical lines with dots at their members, time in discrete
slots. Designed for 50–500 vertices, with eight vertex orderings, packing, drips, and — uniquely
among published techniques — an explicit **role channel** (a symbol at the incidence).
See: [Dynamic and temporal hypergraph visualization](../06-visualization/dynamic-and-temporal-hypergraph-visualization.md).

**PAOHVis** — the PAOH implementation: about 5,000 lines of Dart compiled to JavaScript on HTML
Canvas, handling hundreds of vertices and thousands of hyperedges with reordering, packing and
filtering.
See: [Tools and libraries for drawing hypergraphs](../06-visualization/tools-and-libraries.md).

**Parquet** — the columnar file format; the recommended analysis and archival form of an incidence
table, because dictionary encoding collapses repeated entity and role strings and predicate pushdown
makes "facts with relation R" a metadata scan.
See: [Relational, EAV and Datalog storage](../04-storage-and-formats/relational-and-eav-storage.md).

**Partial completeness assumption (PCA)** — AMIE's middle ground between OWA and CWA: if the KB
knows some `r`-attribute of `x`, assume it knows all of them. Stated for binary `r(x, y)`; **no
formulation of the PCA for n-ary or hyper-relational facts was found**, which is an open problem.
See: [Open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).

**Path-based support** — a support graph in which every hyperedge's induced subgraph contains a
Hamiltonian path, so each hyperedge can be drawn as one metro line. Minimum-edge and planar variants
are NP-complete; a path-based *tree* support is polynomial.
See: [Hypergraph drawing algorithms](../06-visualization/hypergraph-drawing-algorithms.md).

**PG-Schema** — the reference schema proposal for property graphs: PG-Types with multi-inheritance
and PG-Keys-based constraints, aimed at a future GQL DDL. Shows the property-graph community
investing in *schema* while leaving *arity* alone.
See: [Ontologies and schemas for n-ary knowledge](../02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md).

**Plan context graph** — PRoH's sketch of the entities and hyperedges within a few hops of the topic
entities and target hyperedges, shown to the LLM so its reasoning plan can only propose steps the
index can serve.
See: [Hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md).

**Planner–store interface gap** — the observation that LLM planners emit natural language while
retrieval layers answer with similarity, so the relational algebra an n-ary store actually supports is
never exposed as planner-callable operations.
See: [Geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).

**Polygon metaphor** — a subset-standard encoding drawing each hyperedge as a polygon whose corners
are its vertices, with a joint primal–dual layout; scaled to thousands of hyperedges by
structure-aware simplification. Implemented in HGPolyVis.
See: [Catalogue of visual encodings](../06-visualization/visual-encodings-catalogue.md).

**Positional formalisation** — see [hyperedge formalisation](#h). Its failure modes are the same
entity in two positions, symmetric roles, optional roles and schema drift when a new argument is
inserted.
See: [Limitations and failure modes](../10-comparative-and-critique/limitations-and-failure-modes.md).

**Positional interaction** — an ordered pair `(a, b)` recording that one entity occupies slot `a` of one
fact and slot `b` of another; HYPER's generalisation of a knowledge graph's four fundamental
relations.
See: [HYPER anatomy](../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md).

**PRoH** — a 2026 WWW system that replaces static retrieval planning over a knowledge hypergraph
with a context-aware planner, question decomposition into a dynamically evolving DAG of
subquestions, and entity-weighted-overlap path retrieval. Reports the largest margin over
HyperGraphRAG (+19.73% F1) — measured on HyperGraphRAG's own evaluation design.
See: [Retrieval-augmented generation](../07-applications/retrieval-augmented-generation.md).

**PRoH-L** — PRoH's lightweight variant with a fully embedding-based EWO and only path hyperedges as
generation context; the only configuration for which token costs are reported.
See: [Hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md).

**PROV-O** — the W3C provenance ontology (Entity, Activity, Agent, plus relations). Its **qualified
terms** — `prov:qualifiedDerivation` and friends — are reified hyperedges by another name, i.e. the
n-ary pattern standardised in the one vocabulary everyone already imports. The KB's recommendation
is to use PROV-O terms as the attribute vocabulary on hyperedges rather than inventing keys.
See: [Versioning, provenance and scale](../04-storage-and-formats/versioning-provenance-and-scale.md).

**Provenance** — where a fact came from and when it was believed. In a hypergraph the hyperedge *is*
an object with an identity, so provenance is just more attributes on it; in a pairwise decomposition
the question has no well-defined subject, which is one of the cleanest arguments for a first-class
fact object.
See: [Limitations and failure modes](../10-comparative-and-critique/limitations-and-failure-modes.md).

**PSL** (probabilistic soft logic) — first-order rules with conjunctive bodies and single-literal
heads over `[0,1]` soft truth values, on hinge-loss Markov random fields with convex MAP inference.
PSL rules are literally weighted B-arcs over soft-truth atoms.
See: [Open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).

**PyTorch Geometric (PyG)** — the graph learning library whose `HypergraphConv` layer is the usual
entry point for hypergraph learning. It takes incidence pairs, not matrices, so HIF →
`hyperedge_index` is a dictionary lookup and two lists.
See: [Tensor and sparse-matrix representations](../04-storage-and-formats/tensor-and-sparse-representations.md).

---

## Q

**QBLP** — the 2021 ISWC model, the first genuinely inductive one for hyper-relational facts:
embeddings for unseen entities are generated from textual descriptions and auxiliary facts. Also
contributed the WD20K benchmark family.
See: [Inductive and few-shot settings](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md).

**Qualifier** — an optional key–value binding that *restricts* a fact rather than constituting it:
Wikidata's `start time`, `point in time`, `determination method`. Its defining semantic property is
**monotonicity** — attaching more qualifiers can only narrow the answer set, never enlarge it —
which peer roles in a flat tuple do not have. The operational test for whether something is a
qualifier or a participant: remove it and ask whether what remains is still a true, useful,
independently assertable fact.
See: [Knowledge hypergraph schema design](../02-knowledge-representation/knowledge-hypergraph-schema-design.md)
and [When to use a knowledge hypergraph](../10-comparative-and-critique/when-to-use-and-when-not.md).

**Query hypergraph** — vertices are query variables, hyperedges are query atoms. One of **three
different "hypergraphs of a database"** — the others being the schema hypergraph (attributes,
relation schemas) and the instance hypergraph (entities, tuples) — and confusing them is a common
error. A KHG is the third; acyclicity and width results are about the first two.
See: [N-ary relations, relational algebra and the query hypergraph](../01-foundations/n-ary-relations-and-relational-algebra.md).

---

## R

**RAE** — a 2018 n-ary model adding a learned *relatedness* term between co-occurring entities to
m-TransH's geometry, used to prune candidates.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**RAM** (Role-Aware Modeling) — a 2021 model giving roles their own latent space: role embeddings
are linear combinations of shared basis vectors, so semantically related roles land close. Its
supporting measurement is that over 80% of roles in beyond-ternary WikiPeople relations also appear
in lower-arity ones — the argument for a *global* role vocabulary.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**Rank (hypergraph)** `r(H)` — the maximum hyperedge size `max_e |e|`. Appears in the `Ω(r)` cut
distortion of clique expansion and the `O(log r)` cost of the non-linear Laplacian. Not to be
confused with Wikidata rank.
See: [Notation cheat sheet](../01-foundations/notation-cheatsheet.md).

**Rank (Wikidata)** — preferred / normal / deprecated, an **editorial preference, not a probability**.
Deprecated means recorded and disfavoured, not false. Contradictory statements coexist and are
ranked rather than deleted — a pattern a KHG view should copy.
See: [Wikidata and Freebase data models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

**RDF** — the W3C triple model `(subject, predicate, object)`. An RDF graph is a *simple ordered
3-uniform hypergraph* in Hayes and Gutierrez's 2004 reading — note that this is a hypergraph of
*statements* with fixed arity 3 in which the predicate is a **member**, not a hypergraph of facts
over many entities with the relation as a **label**. Mixing the two conventions is the single most
common confusion in this area.
See: [The semantic-web hypergraph view](../02-knowledge-representation/semantic-web-hypergraph-view.md).

**RDF 1.2** — the current revision (Concepts and Semantics at Candidate Recommendation, 7 April
2026; syntaxes and SPARQL 1.2 still Working Drafts). Adds [triple terms](#t) and [reifiers](#r).
It solves *statement annotation*, **not** n-ary relations: the specification itself says relations
over more than two entities "can only be indirectly expressed in RDF" and points at the 2006 n-ary
note.
See: [Standards convergence](../08-history-and-frontier/standards-convergence.md).

**RDF4J** — the Eclipse Java RDF framework and store family; supports RDF-star, and GraphDB is built
on it.
See: [Software libraries](../09-ecosystem/software-libraries.md).

**rdflib** — the Python RDF library. Verified limitation as of version 7.6.0: it **cannot parse
RDF-star / RDF 1.2 triple terms** in any syntax, so a Python pipeline needing them must use
pyoxigraph, Jena or RDF4J.
See: [Software libraries](../09-ecosystem/software-libraries.md).

**RDF-star** — the 2021 Community Group design using **quoted triples** in subject or object
position. Superseded by RDF 1.2, which moved to triple terms in object position only plus explicit
reifiers — a breaking change for data. The two most widely deployed commercial stores still
implement the older dialect, so "RDF-star support" names two incompatible things.
See: [RDF-star, RDF 1.2 and the semantic-web serialisations](../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md).

**ReAlE** — the 2021 follow-up to HypE (JMLR 24(105):1–34, 2023): embeddings that provably represent
five primitive operations of relational algebra (renaming, projection, union, selection, set
difference; not Cartesian product, hence not join), tying the embedding line back to database theory.
Only renaming is an equality of scores; the others are bounds.
See also: [Geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).
See: [The machine-learning era](../08-history-and-frontier/machine-learning-era.md).

**Re-DocRED** — a re-annotation of 4,053 DocRED documents fixing pervasive false negatives; models
gained about 13 F1. The reason recall on any n-ary benchmark should be read as a lower bound.
See: [Evaluating constructed knowledge hypergraphs](../03-construction/evaluation-of-constructed-khgs.md).

**Reification** — **a contested family of mechanisms, not one thing.** Making a statement into an
addressable object: RDF 1.1's four-triple `rdf:Statement` vocabulary (deliberately non-committal —
"a reification of a triple does not entail the triple"); RDF 1.2's `rdf:reifies` plus a triple term;
the W3C n-ary note's *relation instance*; a property graph's intermediate node; a Freebase CVT; a
Wikidata `wds:` statement node. These have different semantics and different costs, and the
n-ary/statement-about-a-statement distinction is routinely elided.
See: [N-ary relations and reification](../02-knowledge-representation/n-ary-relations-and-reification.md)
and [Glossary of confusable terms](../10-comparative-and-critique/glossary-of-confusable-terms.md).

**Reifier** — in RDF 1.2, the subject of a triple whose predicate is `rdf:reifies` and whose object
is a triple term. It "may denote a variety of things related to the triple term's proposition, such
as a statement or belief that the proposition holds", and one reifier may reify several
propositions. Structurally a Wikidata statement node.
See: [RDF-star, RDF 1.2 and the semantic-web serialisations](../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md).

**Relation graph** — a graph whose nodes are relation types and whose typed edges record how those
relations' argument slots intersect; introduced by InGram, used by ULTRA, generalised to arity by
HYPER, where it has O(|R|²k²) potential edges.
See: [HYPER anatomy](../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md).

**Relation-instance pattern** — Pattern 1 of the 2006 W3C n-ary note: create a class for the
relation and one property per participant. The oldest, most portable and least lossy way to put an
n-ary fact in RDF, and the only shape that round-trips to a role-labelled hyperedge. Its documented
costs are a maintenance burden, a class lattice for role-combination constraints, and awkward
inverses.
See: [N-ary relations and reification](../02-knowledge-representation/n-ary-relations-and-reification.md).

**RelationalAI** — a Datalog-family commercial system over relations of arbitrary arity; the arity
argument for relational knowledge graphs is sound in principle, though the vendor makes no
hypergraph claim.
See: [Industry adoption and products](../07-applications/industry-adoption-and-products.md).

**Role** — the name of the part a participant plays in a fact (`recipient`, `dosage`, `buyer`).
Roles can be **global** (reusable across relations and arities, as RAM's 80% reuse measurement
argues) or **local to a relation** (FrameNet's choice, which pays with a large redundant inventory).
Roles are the feature almost every hypergraph library lacks: HIF permits them only as opaque
incidence attributes, and no surveyed library interprets them.
See: [Knowledge hypergraph schema design](../02-knowledge-representation/knowledge-hypergraph-schema-design.md)
and [Getting started toolchain](../09-ecosystem/getting-started-toolchain.md).

**Role-value pair formalisation** — an n-ary fact as an unordered set `{rᵢ : vᵢ}` with no privileged
pair. Flexible across arities, but "fails to account for the varying importance or prominence of
different entities within the same fact", and gives up the cheap triple view and the monotonicity
property.
See: [Hyper-relational vs n-ary vs hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).

**R-S** (Retrieval Similarity) — HyperGraphRAG's metric: cosine similarity between concatenated
retrieved knowledge and the concatenated ground-truth knowledge used to *construct* the question.
A method whose retrieval unit is the construction unit has a structural advantage on it, so the KB
recommends discounting R-S-style numbers.
See: [A critical reading of hypergraph-RAG claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md).

**r-SimplE** — the reification baseline in the HypE paper, whose collapse (JF17K MRR 0.102 against
HypE's 0.494; Hits@10 0.025 at arity 3) is the field's standard citation against decomposition. The
authors attribute it to auxiliary entities appearing in too few facts to learn embeddings for —
a failure of a *learning method*, not of the representation.
See: [Limitations and failure modes](../10-comparative-and-critique/limitations-and-failure-modes.md).

---

**rspmm** — relational sparse-matrix multiplication, the NBFNet-derived aggregation kernel reused by
ULTRA and KG-ICL and rewritten in Triton for arbitrary arity in HYPER.
See: [HYPER anatomy](../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md).

## S

**S2S** — a 2021 tensor-decomposition model that partitions embeddings so parameters can be shared
across facts of different arity, fixing GETD's sparsity problem.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**Scenario gap** — the claim that a generic extraction prompt underperforms a hand-tuned domain prompt
because the model lacks explicit scenario skills rather than capability; the motivating problem of
Hyper-KGGen.
See: [Skill-driven extraction and the scenario gap](../03-construction/skill-driven-extraction-and-the-scenario-gap.md).

**Schema hypergraph** — vertices are attributes, hyperedges are relation schemas. The object of
Fagin's acyclicity results and the first large-scale reading of a knowledge base as a hypergraph.
Distinct from the query and instance hypergraphs.
See: [Origins — Berge and the first applications](../08-history-and-frontier/origins-hypergraph-theory.md).

**Schema induction** — deriving relation names, role names and arities from the extractions
themselves rather than from a given ontology. Inducing *relation names* is crowded (EDC,
AutoSchemaKG, DIAL-KG); inducing **role signatures** is a distinct, older and much emptier problem
whose clearest statement, TFBA's higher-order relation schema induction, has had few successors.
See: [Schema induction and ontology alignment](../03-construction/schema-induction-and-ontology-alignment.md).

**SciREX** — a document-level n-ary scientific IE dataset over Method, Metric, Task, Material and
Score. Caveat from its own repository: about half the annotated relations contain an entity with no
textual mention, because it appeared only in a discarded table.
See: [Scientific knowledge and scholarly graphs](../07-applications/scientific-knowledge-and-scholarly-graphs.md).

**Semantic frame** — see [FrameNet](#f) and [frame](#f). A frame is a relation type, its frame
elements are roles, and an annotated instance is an n-ary fact — with the caveat that frames are
lexical rather than schematic.
See: [Ontologies and schemas for n-ary knowledge](../02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md).

**Semantic operators** — Patel et al.'s declarative relational-algebra-shaped operators (`sem_filter`,
`sem_join`, `sem_agg`, `sem_topk`) over tables with natural-language predicates, implemented in LOTUS;
the closest existing analogue to an algebraic interface for an LLM planner.
See: [Geometry and algebraic interfaces](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).

**Semantic role labelling (SRL)** — assigning predicate–argument roles (PropBank's numbered Arg0,
Arg1…; FrameNet's named FEs) to a sentence. An SRL-labelled sentence is already a set of n-ary
propositions; turning them into a corpus-level hypergraph still needs entity resolution and role
canonicalisation.
See: [N-ary relation and event extraction from text](../03-construction/n-ary-relation-extraction-from-text.md).

**Set system** — a finite family of subsets of a universe. The same object as a hypergraph, under
the combinatorics community's name and the set-visualisation community's vocabulary (element =
vertex, set = hyperedge, membership = incidence).
See: [Set visualisation and hypergraph visualisation](../06-visualization/set-visualization-connection.md).

**SHACL** — the W3C shapes constraint language. **SHACL 1.2 Core** (Working Draft, September 2026)
is the first standards-track way to constrain RDF 1.2 reification, with `sh:reifierShape` and
`sh:reificationRequired` — so a shape can require every `award_received` statement to carry a
`point_in_time` qualifier of the right datatype. SHACL-Core is demonstrably insufficient for
Wikidata's own constraint set.
See: [Ontologies and schemas for n-ary knowledge](../02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md).

**ShEx** (Shape Expressions) — the alternative RDF shape language, at version 2.1 (2019) and making
no mention of RDF 1.2 or triple terms, so qualifier-aware ShEx validation is not available from the
published specification. Wikidata's EntitySchemas are stored in ShExC.
See: [Ontologies and schemas for n-ary knowledge](../02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md).

**ShrinkE** — a 2023 model giving qualifiers a geometric meaning: the primary triple maps the head
to a **query box**, each qualifier *shrinks* that box, and the containment is a geometric proof of
qualifier monotonicity. The most semantically principled model in the family.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**SimpleHypergraphs.jl** — the Julia hypergraph library (weighted incidence matrix, vertex and
hyperedge metadata, HIF support), maintained alongside the hypergraph-modularity clustering work.
See: [Software libraries](../09-ecosystem/software-libraries.md).

**Simplicial closure** — the empirical study of how often an "open" group whose pairs are all
present later appears as a full simplex. The descriptive statistic behind higher-order link
prediction, and the point where the hypergraph and simplicial views meet by measurement rather than
assumption.
See: [Higher-order interactions](../01-foundations/higher-order-interactions.md).

**Simplicial complex** — a family of sets **closed downward**: every subset of a simplex is a
simplex. That derivation is the point, and it is almost always wrong for knowledge, because
`married(Alice, Bob, 2011)` does not entail `married(Alice, Bob)` as an independently asserted fact.
What it buys is homology, Hodge theory and high-dimensional expansion, none of which is defined on
arbitrary hypergraphs.
See: [Hypergraphs vs bipartite vs simplicial](../01-foundations/hypergraphs-vs-bipartite-vs-simplicial.md).

**Singleton property** — the 2014 proposal to mint one property instance per statement, linked to
its generic property by `rdf:singletonPropertyOf`. One extra triple instead of four, at the cost of
an explosion of property IRIs and unfriendliness to property paths and predicate-based indexes.
See: [N-ary relations and reification](../02-knowledge-representation/n-ary-relations-and-reification.md).

**s-line graph** — the graph on hyperedges of size ≥ s, joined when they share at least s vertices.
`H` is s-connected iff `L_s(H)` is connected, which is how s-analytics are implemented; building it
naively costs `Θ(|E|²)` intersection tests.
See: [Hypergraph algorithms for knowledge work](../05-query-embeddings-reasoning/hypergraph-algorithms-for-knowledge.md).

**Snak** — Wikidata's basic information unit. Three kinds: `PropertyValueSnak` (has this value),
`PropertySomeValueSnak` (has *some* value, unspecified), `PropertyNoValueSnak` (has *no* value). The
last two are explicit existential and negative knowledge, unusual in KGs — and thrown away by
WikiPeople's construction.
See: [Wikidata and Freebase data models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

**Soufflé** — a Datalog engine compiling to parallel C++, notable here because it derives which
indexes an n-ary relation needs from the rules — the thing you otherwise do by hand on an incidence
table.
See: [Relational, EAV and Datalog storage](../04-storage-and-formats/relational-and-eav-storage.md).

**SPARQL** — the W3C RDF query language. In SPARQL 1.1 an n-ary fact must be reified first and the
query must enumerate every role, so arity is hard-coded in the query text, the hyperedge has no
identity in the algebra, and one hyperedge pattern becomes an n-way self-join.
See: [Query languages for knowledge hypergraphs](../05-query-embeddings-reasoning/query-languages-for-hypergraphs.md).

**SPARQL 1.2** — the in-progress revision adding triple-term syntax `<<( s p o )>>`, reifiers `~`,
annotation blocks `{| … |}`, the functions `TRIPLE`, `SUBJECT`, `PREDICATE`, `OBJECT`, `isTRIPLE`,
and a `VERSION` declaration. It makes the hyper-relational shape queryable; it gives no aggregate
over a hyperedge's members, no arity predicate, and no "all facts where X plays role R" without
knowing R.
See: [Query languages for knowledge hypergraphs](../05-query-embeddings-reasoning/query-languages-for-hypergraphs.md).

**Sparsification, spectral** — thinning a hypergraph while preserving its Laplacian quadratic form
to within `1 ± ε`. Achievable with `O*(n)` hyperedges, **independent of hyperedge rank** — so
spectral summaries of a large fact base need not grow with arity.
See: [Random walks, spectral theory and expansion](../01-foundations/random-walks-spectral-and-expansion.md).

**SQL/PGQ** (ISO/IEC 9075-16:2023) — SQL:2023's property-graph query part: define a graph *view*
over existing tables and pattern-match on it. A standardised flattening — the base tables are n-ary,
the graph view is binary — and the only standards-track answer today to "graph queries over n-ary
facts".
See: [Relational, EAV and Datalog storage](../04-storage-and-formats/relational-and-eav-storage.md).

**Stability** — running an extractor K times on the same corpus and reporting the Jaccard overlap of
the resulting hyperedge sets. An under-used metric: a pipeline whose output changes between runs
cannot support incremental merging, whatever its F1.
See: [Evaluating constructed knowledge hypergraphs](../03-construction/evaluation-of-constructed-khgs.md).

**Stability-based relative reward** — Hyper-KGGen's partition of gold relations into stable, unstable
and missed by how many of K parallel extraction rollouts recover them, distilling skills only from the
latter two; it requires gold annotations, so it is a supervised signal.
See: [Skill-driven extraction and the scenario gap](../03-construction/skill-driven-extraction-and-the-scenario-gap.md).

**Star expansion** — see [Levi graph](#l). Weighted `w(e)/δ(e)` in the spectral literature.
See: [Incidence, matrices, tensors and graph expansions](../01-foundations/incidence-and-matrix-representations.md).

**StarE** — the 2020 EMNLP model: a CompGCN-style encoder that folds qualifier pairs into a modified
relation representation before message passing, with a transformer decoder. Two lasting
contributions beyond the model: the demonstration that existing benchmarks "suffer from fundamental
flaws", and the **WD50K** family.
See: [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md).

**StarQE** — the 2022 ICLR model, the first to answer multi-hop *logical queries* over
hyper-relational KGs, with the WD50K-QE query dataset. Its finding is that qualifiers help query
answering, because context that restricts a fact also restricts a query.
See: [Logical reasoning and rules over n-ary facts](../05-query-embeddings-reasoning/logical-reasoning-and-rules-over-n-ary-facts.md).

**Star-to-clique (S2C)** — converting an n-ary fact into `C(k,2)` binary edges with compound
relation labels. **Irreversible and lossy**: the graph no longer records which pairwise edges
belonged to one fact, so spurious tuples become derivable. FB15K was built this way, which is why
JF17K exists.
See: [Hyper-relational vs n-ary vs hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).

**Statement (Wikidata)** — a main snak plus zero or more qualifier snaks, zero or more reference
records, and a rank. A hyperedge whose members are the subject, the main value and every qualifier
value, labelled by the main property and keyed by qualifier properties.
See: [Wikidata and Freebase data models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

**StepGRPO** — HyperGraphPro's variant of GRPO in which each retrieval step's advantage is modulated by
a dense progress reward (reduction in uncertainty about the gold answer) plus a graph-structure
reward, instead of a single outcome reward.
See: [Hierarchical and planned hypergraph retrieval](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md).

**Subset standard** — Mäkinen's drawing convention in which vertices are points and each hyperedge
is a closed curve enveloping them. Dominates the academic drawing literature and has near-zero
adoption in knowledge-graph tooling, where every system draws fact nodes with role-labelled links
instead.
See: [Hypergraph drawing algorithms](../06-visualization/hypergraph-drawing-algorithms.md).

**Superhypergraph** — a term from a body of recent preprint literature extending hypergraphs
recursively over power sets. Flagged so readers recognise it; not established in the mainstream
higher-order or KR literature and not used in this KB.
See: [Glossary of confusable terms](../10-comparative-and-critique/glossary-of-confusable-terms.md).

**Support (drawing)** — a graph on the vertices in which every hyperedge induces a *connected*
subgraph; the combinatorial core of subset-standard drawing. Tree, path, cycle and cactus supports
are polynomial; **planar, compact and 2-outerplanar supports are NP-complete**. Since KHG hyperedges
are not closed under intersection and rarely planar, none of the easy cases applies.
See: [Hypergraph drawing algorithms](../06-visualization/hypergraph-drawing-algorithms.md).

**s-walk** — a walk between hyperedges in which consecutive hyperedges share at least `s` vertices.
The parameterised generalisation of connectivity, and the most useful hypergraph idea for knowledge
retrieval: `s` is the knob for how much co-participation counts as a connection. `s = 1` recovers
the ordinary graph walk; `s > 1` is possible only on hypergraphs and is provably not reducible to a
Markov process on nodes.
See: [Hypergraph algorithms for knowledge work](../05-query-embeddings-reasoning/hypergraph-algorithms-for-knowledge.md).

---

## T

**Temporal hypergraph** — a sequence of timestamped hyperedges, `{(S_i, t_i)}`. For a KHG, keep two
clocks apart: **valid time** (when the fact holds in the world, part of its content) and
**Time triplet (VITA)** — `(c, t₁, t₂)` with `c ∈ {Since, Until, Period, Invariant}`, the only
interval-valued time representation found in the hyper-relational literature (2025); evaluated only
in the interpolation setting.
See: [Temporal and dynamic KHGs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md).

**transaction time** (when the system recorded it, metadata). Conflating them makes temporal queries
wrong.
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**Tensor, adjacency** — for a k-uniform hypergraph, the order-k symmetric array with a non-zero at
each hyperedge. Mathematically natural and practically unusable for knowledge: it requires
uniformity, and the index tuple per non-zero is k integers against 2 for an incidence matrix.
See: [Tensor and sparse-matrix representations](../04-storage-and-formats/tensor-and-sparse-representations.md).

**Text2NKG** — the first extractor targeting all four n-ary KG schemas: multi-label classification
of ordered span-tuples with packed levitated markers, then *hetero-ordered merging* and *output
merging* to build facts of arbitrary arity.
See: [N-ary relation and event extraction from text](../03-construction/n-ary-relation-extraction-from-text.md).

**THOR** — a 2026 fully inductive model for hyper-relational KGs built on relation and entity
*foundation graphs* that are agnostic to specific relations and entities, with masked training and
fully-inductive inference across 12 datasets.
See: [Inductive and few-shot settings](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md).

**Toplex** — HyperNetX's name for a maximal hyperedge (one not contained in another). A simple
hypergraph's hyperedges are all toplexes; a simplicial complex is determined by its toplexes
(facets).
See: [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md).

**TopoX** — the suite of Python packages (TopoNetX, TopoEmbedX, TopoModelX) for machine learning on
topological domains: hypergraphs, simplicial, cellular, path and combinatorial complexes. The
topological-deep-learning community's tooling, with almost no contact with *knowledge* hypergraphs.
See: [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

**Transversal** (hitting set, vertex cover) — a vertex set meeting every hyperedge; `τ(H)` is the
minimum size. NP-complete, approximable only to `(1 − o(1)) ln n`, and enumerating *minimal*
transversals is the open monotone-dualization problem. "Smallest set of entities touching all these
facts" inherits all of that.
See: [Classical hypergraph theory results](../01-foundations/hypergraph-theory-results.md).

**Triple term** — in RDF 1.2, an RDF triple used as the **object** of another triple, written
`<<( s p o )>>`. Triple terms are *not asserted*, which is what lets you record "source X claims P"
without asserting P. Only object position, unlike the 2021 RDF-star design.
See: [RDF-star, RDF 1.2 and the semantic-web serialisations](../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md).

**TypeDB** — the only mainstream database whose schema language has unbounded-arity relations with
**typed, named roles**, declared with `relates` and `plays`, validated at write time, and with
relations able to own attributes and play roles in other relations (hence nesting). Its own
marketing hedges correctly: the data structure "can be seen as a hypergraph" — a TypeDB relation is
a role-labelled relation instance, and the hypergraph analogy imports none of the mathematics.
See: [Property graph vs TypeDB vs RDF-star](../10-comparative-and-critique/property-graph-vs-typedb-vs-rdf-star.md).

**TypeQL** — TypeDB's query language. Its distinctive feature for KHGs is **partial-tuple
semantics**: a relation pattern matches relations with *at least* the listed role players, so
omitting a role *widens* the match. This is the "match a hyperedge with at least these
participants" primitive SPARQL lacks — and a generation trap for LLMs, which silently return a
superset when unsure.
See: [Query languages for knowledge hypergraphs](../05-query-embeddings-reasoning/query-languages-for-hypergraphs.md).

---

## U

**Ubergraph** — Joslyn and Nowak's 2017 formalisation of a recursive hypergraph: edges may contain
vertices *or other edges*, with an explicit depth parameter. Every hypergraph is a depth-0
ubergraph; the incidence structure becomes a DAG (the uber-Levi graph), and unrestricted
self-reference would violate the axiom of foundation. Defined only for the **undirected** case.
See: [Metagraphs, ubergraphs and hypergraph databases](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md).

**ULTRA** — the 2024 foundation model for *knowledge graph* reasoning that transfers zero-shot
across unseen entity and relation vocabularies; the direct ancestor of HYPER. Applied to reified
hypergraphs it consistently underperforms, which is the strongest evidence that reification is not
just lossy but **transfer-hostile**.
See: [Inductive and few-shot settings](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md).

**UltraDomain** — the long-document QA corpus collection (from MemoRAG) that supplies the
Agriculture, Computer Science and Legal domains of HyperGraphRAG's evaluation and LightRAG's before
it.
See: [Datasets and benchmarks](../09-ecosystem/datasets-and-benchmarks.md).

**UniGNN** — a 2021 framework unifying GCN, GAT, GIN and GraphSAGE over both graphs and hypergraphs
by observing that a hypergraph layer is two aggregations: vertices into a hyperedge, then incident
hyperedges into a vertex.
See: [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

**UpSet** — the matrix-and-bar encoding for set *intersections*: rows are intersections, a dot
matrix shows which sets each belongs to, bars show sizes. The only widely adopted set encoding that
scales to dozens of sets. **Caution for KHGs**: its rows are intersections, not hyperedges, so it
collapses two distinct facts over the same entities.
See: [Set visualisation and hypergraph visualisation](../06-visualization/set-visualization-connection.md).

---

## V

**Valid time** — when a fact holds in the world, as opposed to transaction time. In Wikidata it is a
qualifier (`start time`, `end time`, `point in time`), so the hyperedge's own arity encodes its
temporal extent; as a column it is faster to query. Both are defensible; mixing them is not.
See: [Versioning, provenance and scale](../04-storage-and-formats/versioning-provenance-and-scale.md).

**Venn diagram** — the special case of an Euler diagram showing all possible intersections. Deciding
whether a hypergraph admits a vertex- or hyperedge-based Venn-style drawing is **NP-complete**, and
readability collapses below ten sets.
See: [Hypergraph drawing algorithms](../06-visualization/hypergraph-drawing-algorithms.md).

---

## W

**WCOJ** (worst-case optimal join) — a join algorithm whose running time matches the AGM bound;
invented for exactly the access pattern a hypergraph query has, a multiway join over relations
sharing variables. Any KHG engine that plans joins pairwise is provably suboptimal on cyclic
queries.
See: [N-ary relations, relational algebra and the query hypergraph](../01-foundations/n-ary-relations-and-relational-algebra.md).

**WD20K** — the inductive hyper-relational benchmark family: WD20K(25) provides textual descriptions
only, forcing reliance on text features, while WD20K(100) V1 and V2 add an inference graph
containing unseen entities.
See: [Benchmarks and evaluation protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).

**WD50K** — the Wikidata-derived hyper-relational benchmark built to repair JF17K's leak and
WikiPeople's thinness: seeded from FB15K-237 entities, literals removed, and **all train/valid
statements sharing a test statement's main triple deleted**. 236,507 statements, 13.6% with
qualifiers, arity 2 to 67. Its **(33) / (66) / (100) variants** hold the qualified statements
roughly fixed and vary the triple-only accompaniment, so qualifier sensitivity becomes measurable —
but they have different entity and relation vocabularies, so they are different datasets, not
difficulty levels. The default choice for hyper-relational link prediction.
See: [Benchmarks derived from Freebase and Wikidata](../02-knowledge-representation/benchmarks-derived-from-freebase-and-wikidata.md).

**WidthWall** — the 2026 result organising all continuous hypergraph invariants into a **strict
hierarchy indexed by generalized hypertree width**, with clique-expansion invariants strictly
weakest, and a unified placement of 15 HGNN architectures. Once an architecture exposes only
width-r coordinates, no amount of width, readout or training recovers invariants above r.
See: [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

**Wikidata** — the largest deployed n-ary knowledge base, and not a hypergraph database: a statement
is a main snak plus qualifiers, references and a rank. Its RDF dump exposes both a "truthy" layer
(`wdt:`) and a statement-node layer (`p:`, `ps:`, `pq:`, `pr:`), the latter being plain-RDF
reification of the hyperedge. Nearly every hyper-relational benchmark is carved out of it, so the
field's implicit definition of "n-ary fact" is Wikidata's.
See: [Wikidata and Freebase data models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

**WikiPeople** — the Wikidata-derived n-ary benchmark built from facts about humans (382,229 facts).
**Read with care**: after removing literal-bearing statements — which most users do — under 3% of
the remainder carries any qualifier, so a "gain on WikiPeople" is mostly a gain on ordinary triples.
Its published statistics also differ by up to a factor of two between sources.
See: [Dataset quality, leakage and provenance problems](../09-ecosystem/dataset-quality-and-leakage-issues.md).

**WikiPeopleQA** — the first KGQA dataset whose background KB is itself n-ary: 4,491 QA pairs over
557 n-ary relation types. Its headline result is the cleanest published measurement of the cost of
decomposition: baselines that split facts into triples via dummy entities scored 10.9–24.9%
accuracy, against 54.4% for reasoning that keeps facts intact.
See: [Question answering over n-ary facts](../07-applications/question-answering-over-n-ary-facts.md).

---

## X

**XGI** (CompleX Group Interactions) — the Python higher-order network library with undirected
`Hypergraph`, directed `DiHypergraph` and `SimplicialComplex` classes, generative models and
drawing. Verified finding: of the three main Python libraries, **only XGI preserves HIF's
`direction` field**.
See: [Getting started toolchain](../09-ecosystem/getting-started-toolchain.md).

**XGI-DATA** — the reference dataset collection for XGI, archived on Zenodo and distributed in HIF:
over fifty datasets with full statistics. Worth reading critically — several widely used
"higher-order" datasets have mean edge size close to 2, i.e. they are graphs with a few triangles.
See: [Datasets and benchmarks](../09-ecosystem/datasets-and-benchmarks.md).

---

## Y

**Yannakakis algorithm** — evaluates an acyclic conjunctive query in two passes of semi-joins over
its join tree (bottom-up to remove dangling tuples, top-down to propagate) before joining. The
reason α-acyclicity is the tractability boundary.
See: [N-ary relations, relational algebra and the query hypergraph](../01-foundations/n-ary-relations-and-relational-algebra.md).

---

## Z

**Z-eigenpair** — `T c^{m−1} = λ c` for an adjacency tensor. Perron–Frobenius gives a positive
solution but **not uniqueness**, and the resulting centrality can be numerically unstable; contrast
the [H-eigenpair](#h).
See: [Incidence, matrices, tensors and graph expansions](../01-foundations/incidence-and-matrix-representations.md).

**Zykov planarity** — a hypergraph is Zykov-planar iff its **incidence graph is planar**, so it is
testable in linear time. The cheap planarity notion, and one more reason the bipartite encoding is
the pragmatic default: every region-based drawability question is NP-complete or worse.
See: [Hypergraph drawing algorithms](../06-visualization/hypergraph-drawing-algorithms.md).

**Zykov representation** — drawing hyperedges as faces of a subdivision realised by their vertices,
obtained by deforming an Euler diagram towards the incidence graph; the intermediate coloured stage
is named *PaintSplash*. Used heavily for simplicial complexes.
See: [Catalogue of visual encodings](../06-visualization/visual-encodings-catalogue.md).

---

## Sources

This glossary is a synthesis of the 106 notes in `kb/`; every entry's evidence and citations live in
the note it links to. The two partial glossaries it complements rather than replaces are:

- Notation and symbol conventions, with the clash index for overloaded letters:
  [../01-foundations/notation-cheatsheet.md](../01-foundations/notation-cheatsheet.md)
- Disambiguation of the eleven most-confused terms, with a comparison table:
  [../10-comparative-and-critique/glossary-of-confusable-terms.md](../10-comparative-and-critique/glossary-of-confusable-terms.md)

Section-level bibliographies, with full author, venue, year and URL for every primary source cited
above, are in `sources/by-topic/`. Section indexes:
[01](../01-foundations/README.md) ·
[02](../02-knowledge-representation/README.md) ·
[03](../03-construction/README.md) ·
[04](../04-storage-and-formats/README.md) ·
[05](../05-query-embeddings-reasoning/README.md) ·
[06](../06-visualization/README.md) ·
[07](../07-applications/README.md) ·
[08](../08-history-and-frontier/README.md) ·
[09](../09-ecosystem/README.md) ·
[10](../10-comparative-and-critique/README.md).
