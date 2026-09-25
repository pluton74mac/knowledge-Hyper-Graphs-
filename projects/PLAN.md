# The programme: eleven projects to move the field

The candidate projects in [README.md](README.md) form one programme. Its purpose is to move the
eight themes of the [open-questions register](../kb/00-index/open-questions.md): each project
closes, narrows or reframes named questions, and each ends in a result the community can use.

There is no calendar. The programme is a dependency graph of artefacts with a gate per project. A
phase closes when its gates pass, and nothing is built on a component whose gate has not passed.
How many projects run at once is a resource decision made per phase; the graph says only what can
run concurrently.

## 1. What "done" means

A project is done when all three hold:

1. **Gate passed.** Its testable done-condition (§4) is met.
2. **The base updated.** The notes that hold its questions are revised with the result, the
   questions in the register are marked closed, narrowed or reframed with a link to the project
   folder, and the run log records it. A negative result updates the base as much as a positive one.
3. **Publication shipped.** The project's publishable unit (§5) is out: the results folder is
   complete, the external artefact is released where its audience looks, and the post is published.

A project that has passed its gate but not shipped its publication is not done, and its row on the
status board says so.

## 2. Two kinds of project

- A **capability project** produces a reusable artefact (a format, a corpus, a module) that other
  projects consume. It finishes only when its gate passes.
- A **finding project** produces a measurement that closes or reframes questions in the register.
  It always finishes, because a negative or null result is a result and is published as such.

## 3. Projects, inputs, artefacts, consumers

| Id | Project | Kind | Consumes | Hands over | Consumed by | Themes |
|---|---|---|---|---|---|---|
| P2 | Role-aware HIF: `roles` convention on incidence attributes, JSON Schema, validator, role-preserving loaders for XGI and HyperNetX; plus the shared record format, store interface, queue format and scorers the other projects use | capability | nothing | contracts C1 to C3, C5 | every project | 2, 7 |
| P3a | Clean n-ary corpus: leak-checked, deduplicated, arity-stratified split from recent Wikidata, with roles and with question sets for retrieval and memory | capability (data) | C1 | contract C4 | P1, P3b, P4, P5, P7, P8, P9, P10 | 3 |
| P3b | Replication of two n-ary completion models on P3a; calibration by arity | finding | C4 | baselines and the calibration result | P8 | 3 |
| P1 | Format and store bake-off: incidence table, reified RDF 1.2, bipartite property graph, TypeDB, HIF; same queries; round-trip fidelity and latency | finding | C1, C2, C4 slice | measurement table | any project that stores | 1, 4 |
| P6 | Schema width survey: acyclicity class and hypertree width of Wikidata qualifier schemas and one biomedical schema; a checker for schema files | finding + tool | C1 | survey result, checker | P11 | 5 |
| P7 | Fact identity and supersession: key roles, arity-conditional merge, valid-time on the hyperedge, hypergraph memory vs flat vector store | capability | C1, C2, C4 | identity module, memory comparison | P8, P9, P11 | 4, 8 |
| P9 | Extraction gate: role-constrained n-ary extraction into a candidate queue, scored against gold; instability across runs and insertion orders | capability | C1, C3, C4 | extractor and scores | P8, P11 | 2, 3, 8 |
| P10 | Judgment-model walker: policy over a code-owned traverser; a general LLM, then a decision-only model, behind one judgment interface | capability | C1, C2, C4 | walker and model comparison | P4, P8, P11 | 1, 8 |
| P5 | Reader study: incidence vs Euler drawing of the same KHG, with and without role labels | finding | C1, C4 slice | perception result | P11 (review view) | 2, 6 |
| P4 | Arity ablation of hypergraph RAG: same walker, hyperedges intact vs pairwise vs sentence chunks; also on GraphRAG-Bench | finding | P10, C4 | retrieval evidence | P8 | 1, 3 |
| P8 | Four-ability suite: one corpus scored on extraction, inductive completion, retrieval and a superseding memory trace; correlation among the four | finding + integration | P7, P9, P10, P3b, an inductive completer | composition result | | 3, 8 |
| P11 | Goal-directed construction: goal hyperedges with unbound roles, one agent per discipline, termination criterion; two disciplines, then four | capability | P6, P7, P9, P10 | goal mechanism and the case reports | | 4, 6, 8 |

On P8's completer: an extracted graph contains entities no training set has seen, so its completer
must be inductive. The candidate is the released HYPER model
([hyper-foundation-model-anatomy](../kb/05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md)).
P3b's models are transductive and serve as calibration baselines. If no inductive completer runs
on the corpus, that is P8's completion finding, published as such.

## 4. Gates

| Id | Gate |
|---|---|
| P2 | A record round-trips repo format to HIF to XGI and HyperNetX and back with roles intact; the validator rejects each malformed case in its test list; a smoke test runs one record through queue, structural lint, store and export |
| P3a | Corpus released with leak-check report, deduplication report, arity histogram, fixed split, question sets |
| P3b | Two models replicated with reported numbers reproduced within stated tolerance; calibration by arity reported |
| P1 | Table of five stores by round-trip fidelity, load time and query latency on one query set |
| P6 | Survey table for the Wikidata qualifier schemas and the biomedical schema; the checker reports class and width for a given schema file and flags a constructed cyclic case |
| P7 | Every case in the identity test list (refinement, distinct fact, contradiction, arity change) is classified as specified; the memory comparison is reported on the superseding-fact question set |
| P9 | Extraction scored against P3a gold with precision, recall and role accuracy; instability across three runs and two insertion orders reported; output validates against C3 |
| P10 | The walker answers the P3a question set; general LLM and decision-only model compared on cost, latency and accuracy behind the same interface |
| P5 | Study run and reported with its sample and its limits |
| P4 | Three retrieval conditions on the same question set; one table, one figure; the GraphRAG-Bench run reported |
| P8 | One corpus, four scores (or three, stated), and their correlation |
| P11 | The two-discipline case reaches termination; the four-discipline case reaches termination or produces a stall report naming the unbound roles and why no brief could bind them |

## 5. Publishable unit per project

Every project ships the same four things: a complete folder here under `projects/<slug>/` (from
`_template/`, with the result table and the figure), the base updated (§1), an external artefact
released where its audience looks, and a post. The external artefact and its audience differ:

| Id | External artefact | Where | Audience |
|---|---|---|---|
| P2 | A proposal to the HIF standard for a `roles` convention, with the validator and loaders as a small package | Pull request or issue on the HIF-standard repository; package on PyPI | Hypergraph library maintainers and users |
| P3a | The corpus with its leak-check report and datasheet | Hugging Face or Zenodo, with a DOI | n-ary link prediction and hyper-relational KG researchers |
| P3b | Preprint: the leak measurement and calibration by arity | arXiv | Same, plus reviewers of the 2016 to 2025 results |
| P1 | Technical report with the measurement table and the query set | Repository release plus a post | Engineers choosing a store for n-ary facts |
| P6 | Short paper or note with the survey table; the checker as a tool | arXiv or a workshop; tool in the repository | Database theory and KG schema people |
| P7 | Preprint: a semantics for fact identity and supersession on n-ary facts, with the module | arXiv; module in the repository | Agent-memory and temporal-KG researchers |
| P9 | Preprint or technical report: extraction instability under role constraints | arXiv | KG-construction and LLM-extraction researchers |
| P10 | Technical report and a runnable demo of a decision-only model walking a knowledge hypergraph | Repository release plus a post | Graph-RAG builders; timely while decision-only models are new |
| P5 | Short paper with the study and an interactive demo of the two drawings | Visualization workshop; demo hosted | Visualization and knowledge-engineering people |
| P4 | Preprint: the arity ablation and the GraphRAG-Bench result | arXiv | Hypergraph-RAG authors and their critics |
| P8 | Preprint: do the layers compose, with the suite released | arXiv; suite in the repository | The knowledge-hypergraph research community |
| P11 | Technical report with the two case studies and the goal mechanism | Repository release plus a post | Agentic-research and design-automation builders |

The post is the owner's. Its draft is part of the project folder so that every completion has one
ready.

## 6. Phases

Phases are the levels of the dependency graph. Inside a phase every project can run concurrently.
The rule is per dependency, not per phase: a project may open as soon as what it consumes has
passed its gate, even if the rest of the earlier phase is still running.

| Phase | Establishes | Projects | Closes when |
|---|---|---|---|
| 0 Foundations | We can represent facts with roles, and we have ground truth | P2, P3a | Both gates pass and both publications ship |
| 1 Components | Each ability exists and is measured alone | P1, P3b, P5, P6, P7, P9, P10 | Every gate passes and every publication ships |
| 2 Evidence | The central retrieval claim is tested | P4 | Gate passes and publication ships |
| 3 Composition | The abilities compose, and goals can drive construction | P8, P11 | Both gates pass and both publications ship |

The programme has no assembly step. Its output is the set of published results and the base they
update. What the owner builds with what was learned is a separate matter, decided elsewhere.

## 7. Contracts shared by the projects

| Id | Contract | Owner | Versioned how |
|---|---|---|---|
| C1 | Record format: nodes, hyperedges with roles, evidence, status lifecycle, relation-type schema language | P2 | Semantic version in the schema id; migration script per major version |
| C2 | Store interface: put, get, incident hyperedges of a node, hyperedges by relation and key, supersession walk, export | P2 | Interface version; every implementation passes one conformance test |
| C3 | Candidate queue record and linter action log | P2 | With C1 |
| C4 | Corpus: gold facts, split, question sets | P3a | Corpus version with changelog; each project records the version it was scored on |
| C5 | Scorers: extraction, retrieval, memory, completion | P2, question sets from P3a | With C1 |

An implementation of C2 passes its conformance test when no applicable scenario fails; a scenario is
inapplicable only through a capability flag the implementation declares absent, and each such scenario is
reported as a fidelity loss. The contracts are specified in
[p2-role-aware-hif/DESIGN.md](p2-role-aware-hif/DESIGN.md).

Contracts are versioned, not frozen. A change ships with its migration and reruns the gate of every
consumer. Each project records the contract versions it consumed.

## 8. When a project does not finish

- **A capability project.** Its phase stays open and its dependents do not start. The status board
  names the blocker. The ways out are more effort, or a recorded design decision that changes the
  gate. A gate is never lowered silently.
- **A finding project.** It cannot fail to finish. It records the result it obtained, with its
  limits, updates the base with it, and publishes it.
- **A contract that turns out wrong.** Bump the version, ship the migration, rerun the consumers'
  gates.

## 9. Status board

| Id | Project | Phase | Kind | Gate | Base updated | Publication | Contracts consumed |
|---|---|---|---|---|---|---|---|
| P2 | Role-aware HIF and shared contracts | 0 | capability | passed | 2026-09-24 | | none (produces C1 khg-record/1.0.0, C2 khg-store/1.0.0, C3 khg-queue/1.0.0, C5 khg-scorers/1.0.0) |
| P3a | Clean n-ary corpus | 0 | capability (data) | not started | | | |
| P1 | Format and store bake-off | 1 | finding | in progress | | | C1 khg-record/1.0.0, C2 khg-store/1.0.0 |
| P3b | Completion replication | 1 | finding | not started | | | |
| P5 | Reader study | 1 | finding | not started | | | |
| P6 | Schema width survey | 1 | finding + tool | passed | 2026-09-25 | | C1 khg-relation-schema/1.0.0 |
| P7 | Fact identity and supersession | 1 | capability | not started | | | |
| P9 | Extraction gate | 1 | capability | not started | | | |
| P10 | Judgment-model walker | 1 | capability | not started | | | |
| P4 | Arity ablation | 2 | finding | not started | | | |
| P8 | Four-ability suite | 3 | finding + integration | not started | | | |
| P11 | Goal-directed construction | 3 | capability | not started | | | |

Gate is one of: not started, in progress, passed. Base updated and Publication are blank or the
date. A project is done when all three columns are filled.
