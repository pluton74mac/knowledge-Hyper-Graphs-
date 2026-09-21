# Projects and exploration vectors

Prototypes and investigations that grow out of the knowledge base. Each project lives in its own
folder, created from `_template/`, and links back to the `kb/` notes it depends on.

| Project | Status | One-line goal |
|---|---|---|
| [hyper-base](https://github.com/pluton74mac/hyper-base) ([pointer](hyper-base/)) | idea | A knowledge base whose structure is a knowledge hypergraph: agents contribute facts through an extraction gate, a linter applies supersession rules, a judgment-model walker retrieves. First target: an EEG device across four disciplines. Combines P7 and P2 and layers B, E, G of the composed stack. |

## Candidate vectors (to be confirmed with the repository owner)

These are the projects the first research run suggested. None is started. The full reasoning, the
questions each one answers, and the themes it moves are in
[`kb/00-index/open-questions.md`](../kb/00-index/open-questions.md), Part C. Promote one by copying
`_template/` to a new folder and adding a row to the table above.

| Id | Project | One-line goal | Starting notes |
|---|---|---|---|
| P1 | Format and store bake-off | Hold one small KHG as incidence table, reified RDF 1.2, bipartite property graph, TypeDB and HIF; same queries; log round-trip fidelity and latency | `kb/04-storage-and-formats/format-recommendations.md`, `schemas/` |
| P2 | Role-aware HIF | A `roles` convention on incidence attributes, a validator, and role-preserving loaders for XGI and HyperNetX | `kb/04-storage-and-formats/hif-hypergraph-interchange-format.md`, `kb/09-ecosystem/software-libraries.md` |
| P3 | Clean n-ary benchmark and replication | Rebuild a leak-free, arity-stratified split from a recent Wikidata dump; replicate two models; report calibration by arity | `kb/02-knowledge-representation/benchmarks-derived-from-freebase-and-wikidata.md`, `kb/05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md` |
| P4 | Arity ablation of hypergraph RAG | Run one hypergraph-RAG system with hyperedges intact, split pairwise, and as whole-sentence chunks; add GraphRAG-Bench | `kb/07-applications/retrieval-augmented-generation.md`, `kb/10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md` |
| P5 | Reader study | Incidence vs Euler drawing of the same KHG, with and without role labels | `kb/06-visualization/knowledge-hypergraph-specific-visualization.md`, `kb/06-visualization/perception-and-evaluation-studies.md` |
| P6 | Schema width survey | Acyclicity class and hypertree width of Wikidata qualifier schemas and one biomedical schema | `kb/01-foundations/hypergraph-theory-results.md`, `kb/01-foundations/n-ary-relations-and-relational-algebra.md` |
| P7 | Agent memory prototype | Hypergraph memory for a small agent vs a flat vector store, with explicit fact-identity, arity-merging and valid-time/supersession rules | `kb/07-applications/ai-agents-memory-and-planning.md`, `kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md`, `kb/03-construction/incremental-and-streaming-construction.md` |
| P8 | Four-ability evaluation suite | One corpus scored on n-ary extraction, inductive completion, edge-ablated multi-hop retrieval, and a superseding memory trace | `kb/08-history-and-frontier/composed-stack-and-research-bets.md`, `kb/05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md` |
| P9 | Extraction gate | An n-ary extraction pass with role constraints, scored against gold facts, emitting a candidate queue instead of writing to the graph; measure instability across runs and insertion orders | `kb/03-construction/llm-based-khg-construction.md`, `kb/03-construction/skill-driven-extraction-and-the-scenario-gap.md`, `kb/03-construction/n-ary-relation-extraction-from-text.md` |
| P10 | Judgment-model walker | Retrieval as a policy over a code-owned traverser: code enumerates incident hyperedges, a judgment model scores next-edge, stop and prune as closed choices; a general LLM first, then a decision-only model behind the same interface, on a gold graph | `kb/07-applications/hierarchical-and-planned-hypergraph-retrieval.md`, `kb/07-applications/retrieval-augmented-generation.md`, `kb/05-query-embeddings-reasoning/llm-and-khg-interaction.md` |
| P11 | Goal-directed construction | Express a design idea as goal hyperedges with unbound roles; one agent per discipline binds roles with evidence; a termination criterion says when the disciplines connect. Two disciplines first, then the four-discipline EEG case | `kb/03-construction/incremental-and-streaming-construction.md`, `kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md`, `kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md` |

## Assembly order towards hyper-base

The candidates are stepping stones to [hyper-base](https://github.com/pluton74mac/hyper-base):
each returns one component or one measured insight, and hyper-base assembles them. The owner has
set a deadline of a working hyper-base in under two months. The week-by-week schedule, the scope
guards on P3, P5 and P8, and the done-condition of each project are in
[hyper-base/docs/roadmap.md](https://github.com/pluton74mac/hyper-base/blob/main/docs/roadmap.md).

| Week | Projects |
|---|---|
| 1 | P2 format, P3 phase 1 corpus, P6 schema check. Corpus and format frozen on day 5 |
| 2 | P7 fact identity and supersession, P9 extraction gate, P10 walker with a general LLM |
| 3 | P1 store bake-off, P10 with a decision-only model, P5 as an online quiz |
| 4 | P4 arity ablation with P10's walker on P3's corpus |
| 5 | P8 four-ability suite on one corpus |
| 6 | P11 goal-directed construction, two disciplines then the EEG goal set |
| 7 | Assembly: multi-writer queue and goal mechanism on P8's pipeline; EEG run end to end |
| 8 | Evaluation against an llm-wiki baseline; buffer; write-ups |

Each project ends with a folder here, one result table, one figure and one post draft.
