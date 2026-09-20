---
title: 02 — Knowledge representation
type: index
status: draft
tags: [index, knowledge-representation, n-ary, hyper-relational, schema, benchmarks]
created: 2026-09-19
updated: 2026-09-20
---

# 02 — Knowledge representation

**Question this section answers.** What *is* a knowledge hypergraph, how is it defined in the
literature, and how does it relate to knowledge graphs and to n-ary knowledge representation
generally?

The short version: there is no single agreed definition. At least five communities — n-ary
embedding, hyper-relational embedding, retrieval-augmented generation, cognitive architecture, and
the semantic-network/semantic-web tradition — use the word for related but distinct formalisms.
They agree on one thing only: *a fact may involve more than two things, so the unit of knowledge is
a hyperedge rather than a binary edge.* They disagree about whether the hyperedge is ordered, typed,
qualified, nested, weighted or directed. These notes make each choice explicit, cite it to a primary
source, and say what it costs.

## Reading order

1. Start with **[what-is-a-knowledge-hypergraph.md](what-is-a-knowledge-hypergraph.md)** for the
   competing definitions.
2. Then **[hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md)**
   to fix the vocabulary and choose a representation.
3. Then **[knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md)** to turn
   that choice into a schema.
4. Everything else is depth on one axis: RDF workarounds, real data models, ontology languages,
   nesting, direction, uncertainty, benchmarks.

## Notes in this section

| Note | Type | What it covers |
|---|---|---|
| [what-is-a-knowledge-hypergraph.md](what-is-a-knowledge-hypergraph.md) | concept | Five competing definitions of "knowledge hypergraph", quoted verbatim and compared in a table: n-ary tuples (Wen 2016, Fatemi 2020), hyper-relational triples with qualifiers (Rosso 2020, Galkin 2020), LLM/RAG hypergraphs (2025), metagraphs (AtomSpace, HypergraphDB), and the conceptual-graph/RDF-as-hypergraph tradition. Ends with a working definition for this KB. |
| [hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md) | comparison | The terminology guide. The three formalisations named by the 2025 survey (hyperedge / role-value pair / hyper-relational), role-value models (NaLP, RAM), primary-triple-plus-qualifiers (HINGE, StarE), star-to-clique and reification with their losses, event-centric representations, semantic frames, and a **decision table** for choosing between them. |
| [knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md) | howto | Practical modelling: entity identity, relation types, roles and cardinality, qualifiers as a second slot class, provenance (PROV-O, references, nanopublications), valid vs transaction time, confidence scales. Includes a **complete example schema and instance file in JSON**, projections to Wikidata / RDF 1.2 / tuples / HIF, validation options, and pitfalls. |
| [n-ary-relations-and-reification.md](n-ary-relations-and-reification.md) | survey | Every binary-model workaround in order: RDF reification (1999/2004), the W3C n-ary note (2006), named graphs (2005), singleton property (2014), RDF-star (2021) and RDF 1.2 triple terms and reifiers (Candidate Recommendation Snapshot, 7 April 2026), property-graph edge properties. With a cost table in extra triples per qualified fact. |
| [wikidata-and-freebase-data-models.md](wikidata-and-freebase-data-models.md) | concept | The two data models that shape the field: Freebase compound value types (2007–2016) and Wikibase statements with qualifiers, references and ranks. The migration mapping between them, the RDF dump layering (`wdt:`, `p:`, `ps:`, `pq:`, `pr:`), and how much of each KB is genuinely n-ary. |
| [ontologies-and-schemas-for-n-ary-knowledge.md](ontologies-and-schemas-for-n-ary-knowledge.md) | survey | Schema and ontology languages: RDFS/OWL's binary properties and the 2006 patterns, schema.org `Role`, FrameNet and event schemas as role vocabularies, Conceptual Graphs and Common Logic (ISO/IEC 24707:2018, variable arity, sequence markers), TypeDB's `relates`/`plays` and nested relations, PG-Schema, SHACL 1.2 and ShEx. Comparison table of what each can constrain. |
| [semantic-web-hypergraph-view.md](semantic-web-hypergraph-view.md) | concept | Disentangles "RDF *is* a hypergraph" from "RDF *needs* a hypergraph". Hayes and Gutierrez (2004): an RDF graph is a simple ordered 3-uniform hypergraph, best handled through its bipartite incidence graph. Formal side-by-side of RDF 1.1/1.2, labelled property graphs and labelled ordered hypergraphs. |
| [directed-and-typed-hyperedges-for-knowledge.md](directed-and-typed-hyperedges-for-knowledge.md) | concept | Three incompatible senses of "directed": ordered arguments, tail-set → head-set, role-labelled incidences. The Gallo (1993) model, B-arcs as Horn clauses, hyperpaths as proofs, hyperedges as events, and hyperedges as contexts and provenance (named graphs, nanopublications). |
| [open-world-vs-closed-world-and-uncertainty.md](open-world-vs-closed-world-and-uncertainty.md) | survey | CWA, OWA and the partial completeness assumption; what KHG completion actually assumes; Wikidata's `novalue`/`somevalue` snaks as explicit negative and existential knowledge; uncertain KGs (UKGE, ConceptNet, NELL, STRING); Markov logic networks as weighted patterns over a knowledge hypergraph; probabilistic soft logic and hinge-loss MRFs; a table of what "absent" and "score" mean in each formalism. |
| [metagraphs-atomspace-and-hypergraphdb.md](metagraphs-atomspace-and-hypergraphdb.md) | survey | Edges that contain edges: ubergraphs (Joslyn and Nowak, 2017), the OpenCog metagraph, AtomSpace Atoms and Values, Hyperon/MeTTa, and HypergraphDB (Iordanov, 2010). Comparison table, what nesting buys a knowledge hypergraph, and the costs (no standard query language, few benchmarks, set-theoretic foundation issues). |
| [benchmarks-derived-from-freebase-and-wikidata.md](benchmarks-derived-from-freebase-and-wikidata.md) | dataset | JF17K, WikiPeople, FB-AUTO, M-FB15K and WD50K: who built each, from which dump, by what procedure, with full arity distributions — and the documented defects (JF17K's 44.5% test leakage and missing validation split; WikiPeople's literal-dominated qualifiers). Includes a table of the *conflicting* statistics reported for the same dataset names. |

## Cross-section links

- Mathematics of hypergraphs, directed hypergraphs and recursive variants:
  [`../01-foundations/hypergraph-definitions.md`](../01-foundations/hypergraph-definitions.md)
- Lifting existing KGs, tables and text into n-ary facts:
  [`../03-construction/from-knowledge-graphs-to-hypergraphs.md`](../03-construction/from-knowledge-graphs-to-hypergraphs.md)
  and [`../03-construction/n-ary-relation-extraction-from-text.md`](../03-construction/n-ary-relation-extraction-from-text.md)
- Bibliography for this section:
  [`../../sources/by-topic/02-knowledge-representation.md`](../../sources/by-topic/02-knowledge-representation.md)

## What this section deliberately does not cover

- **Embedding models and scoring functions** (HypE, HSimplE, StarE, NaLP, RAM, HAHE, …) — only
  their *representational commitments* are discussed here; the models themselves belong in
  section 05.
- **Extraction pipelines** — section 03.
- **Storage engines and serialisation formats** beyond their data models — section 04.
- **Critique of the KHG idea as a whole** — section 10.

## Open questions raised by this section

1. Is there a formulation of the partial completeness assumption for n-ary or hyper-relational
   facts? None was found in the sources consulted.
2. Is there a public *uncertain* n-ary benchmark? The uncertain KGs in use (ConceptNet, NELL-derived
   NL27k, STRING-derived PPI5k) are all binary.
3. Is there a formalism that is simultaneously **directed** (tail → head), **role-labelled** and
   **nested**? Ubergraphs are undirected by construction; metagraphs are ordered but not tail/head
   directed.
4. Do qualifiers and peer roles differ semantically in a way that can be tested, beyond the
   monotonicity property?
5. Does decomposition to binary actually cost accuracy? The 2025 evidence is mixed.
