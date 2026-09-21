---
title: Software libraries for hypergraphs and knowledge hypergraphs
type: tool
status: draft
tags: [ecosystem, software, libraries, hypergraph, n-ary, HIF, rdf-star, databases, visualization]
created: 2026-09-20
updated: 2026-09-21
---

# Software libraries for hypergraphs and knowledge hypergraphs

All figures in the tables below were **checked on 2026-09-20**. Star counts and last-commit
dates come from the GitHub repository search API; package versions come from PyPI, crates.io,
Maven Central and the Julia General registry (each named in the "release" column). GitHub star
counts move daily; treat them as an order-of-magnitude signal, not a measurement.

Four caveats about the table that matter more than any individual number:

1. **"Hypergraph library" and "knowledge hypergraph library" are almost disjoint sets.** The
   network-science stack (HyperNetX, XGI, hypergraphx, SimpleHypergraphs.jl, HAT) models a
   hyperedge as an *unlabelled set of vertices* with optional attributes. The n-ary
   knowledge-representation stack (TypeDB, AtomSpace, StarE, HypE, GRAN) models a fact as a
   *role-indexed tuple*. Only a handful of tools sit in both worlds. See
   [../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).
2. **HIF is the only cross-library interchange format, and it is young.** Its schema changelog
   still lists a single entry, `v0.0`
   ([HIF-standard/schemas/CHANGELOG.md](https://raw.githubusercontent.com/HIF-org/HIF-standard/main/schemas/CHANGELOG.md),
   checked 2026-09-20). Five libraries implement it. See
   [../04-storage-and-formats/hif-hypergraph-interchange-format.md](../04-storage-and-formats/hif-hypergraph-interchange-format.md).
3. **Stars are a poor maintenance signal.** DGL has 14k stars and no commit since 2025-07-31;
   halp has 101 stars and a PyPI release from 2014.
4. **Several important pieces of research code carry no licence file at all** (HypE, HAT),
   which makes reuse legally uncertain.

---

## 1. Hypergraph analysis libraries (network-science lineage)

| Name | Language | Purpose | Hyperedge model | Formats read / written | Licence | Stars | Latest release (checked 2026-09-20) | URL |
|---|---|---|---|---|---|---|---|---|
| **HyperNetX (HNX)** | Python | analysis + visualisation | undirected, attributed ("property hypergraph"): node, edge and incidence properties | HIF in/out (`from_hif`, `to_hif`); pandas DataFrame; dict-of-lists; NetworkX bipartite | 3-clause BSD in `LICENSE.rst` (GitHub metadata says "Other"/`NOASSERTION`) | 716 | PyPI `hypernetx` **2.4.3**, 2026-07-23; last commit 2026-07-08 | [pnnl/HyperNetX](https://github.com/pnnl/HyperNetX) |
| **XGI** | Python | analysis, generative models, drawing | undirected `Hypergraph`, **directed** `DiHypergraph` (head/tail), `SimplicialComplex`; attributed | HIF in/out incl. collections (`read_hif`, `write_hif`, `read_hif_collection`); edge list; bipartite edge list; incidence matrix; XGI JSON | 3-clause BSD in `LICENSE.md` (GitHub metadata `NOASSERTION`) | 255 | PyPI `xgi` **0.10.2**, 2026-05-15; last commit 2026-08-27 | [xgi-org/xgi](https://github.com/xgi-org/xgi) |
| **Hypergraphx (HGX)** | Python | analysis: community detection, motifs, centrality, contagion | undirected, **directed**, **temporal**, **multiplex** classes; attributes as per-node/per-edge metadata | HIF in/out (`read_hif`, `write_hif`); HGX JSON; pickle; built-in remote dataset catalogue | BSD-3-Clause (PyPI `license_expression`; `LICENSE.md` is 3-clause BSD text) | 334 | PyPI `hypergraphx` **1.8.0**, 2026-05-18; last commit 2026-08-03 | [HGX-Team/hypergraphx](https://github.com/HGX-Team/hypergraphx) |
| **SimpleHypergraphs.jl** | Julia | analysis + visualisation | undirected, weighted incidence matrix; vertex and hyperedge metadata | HIF; own `.hgf`; JSON | MIT | 88 | Julia General registry lists up to **v0.4.0**; last commit 2026-08-04 | [pszufe/SimpleHypergraphs.jl](https://github.com/pszufe/SimpleHypergraphs.jl) |
| **HyperGraphs.jl** | Julia | modelling oriented ("chemical") hypergraphs over arbitrary Julia objects | directed: source/target multisets with stoichiometry | none standard | MIT | 44 | **not registered** in the Julia General registry (`H/HyperGraphs/Versions.toml` → 404); last commit 2023-05-11 — dormant | [lpmdiaz/HyperGraphs.jl](https://github.com/lpmdiaz/HyperGraphs.jl) |
| **HAT** (Hypergraph Analysis Toolbox) | Python (also MATLAB) | tensor-based analysis: controllability, observability, similarity, entropy | undirected, uniform and non-uniform; adjacency/Laplacian tensors | HIF (listed as a HIF-supporting library in the HIF README) | **no licence file declared** on the repository | 39 | PyPI `HypergraphAnalysisToolbox` **1.1.18**, 2026-05-23; last commit 2026-05-23 | [Jpickard1/Hypergraph-Analysis-Toolbox](https://github.com/Jpickard1/Hypergraph-Analysis-Toolbox) |
| **halp** | Python 2 | directed-hypergraph algorithms (B-/F-hyperpaths, shortest hyperpaths) | **directed** (tail set → head set) and undirected | own plain-text hyperedge format | GPL-3.0 | 101 | PyPI `halp` **1.0.0**, 2014-10-22; last commit 2023-07-06 — effectively unmaintained | [Murali-group/halp](https://github.com/Murali-group/halp) |

Supporting evidence for the "purpose" and "format" columns of the three Python libraries was
obtained by importing them (versions in [getting-started-toolchain.md](getting-started-toolchain.md))
and enumerating their I/O functions, not only by reading documentation.

**Interoperability finding (verified locally, 2026-09-20).** Loading the repository's own
[../../schemas/sample.hif.json](../../schemas/sample.hif.json) into all three Python libraries:

- XGI 0.10.2 returns an `xgi.core.dihypergraph.DiHypergraph` — the `"direction"` field is honoured.
- HyperNetX 2.4.3 returns an undirected `Hypergraph`; `direction` is not modelled.
- Hypergraphx 1.8.0's `read_hif` is typed `-> hypergraphx.core.undirected.Hypergraph`; it
  **re-indexes node identifiers to integers** and keeps the original HIF ids only in the
  per-node metadata (`{'node': 'drug:metformin', 'attrs': {...}}`).

So a HIF round-trip is *not* currently lossless across libraries for directed knowledge
hypergraphs. HyperNetX also validates against a schema fetched at run time from
`https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json`
(`hypernetx.hif.schema_url`), a third URL distinct from both the `HIF-org` repository and the
`$id` recorded inside the published schema — see
[standards-bodies-and-specifications.md](standards-bodies-and-specifications.md).

---

## 2. Hypergraph learning libraries

| Name | Language | Purpose | Hyperedge model | Formats | Licence | Stars | Latest release (checked 2026-09-20) | URL |
|---|---|---|---|---|---|---|---|---|
| **DHG / DeepHypergraph** | Python (PyTorch) | learning: HGNN, HGNN⁺, HyperGCN, UniGNN; also graphs, bipartite, directed structures | undirected hypergraph with vertex feature tensors; "correlation structures" | own dataset pipeline (pickled); **no HIF** | Apache-2.0 | 887 | PyPI `dhg` **0.9.7**, 2026-08-02; last commit 2026-08-04 | [iMoonLab/DeepHypergraph](https://github.com/iMoonLab/DeepHypergraph) |
| **PyTorch Geometric** (`HypergraphConv`) | Python (PyTorch) | learning; hypergraphs are a layer, not a first-class object | `hyperedge_index`, a 2×N incidence pair list → undirected, attributed | PyG datasets | MIT | 24,093 | PyPI `torch-geometric` **2.8.0.post1**, 2026-07-20; last commit 2026-09-01 | [pyg-team/pytorch_geometric](https://github.com/pyg-team/pytorch_geometric) |
| **DGL** | Python (PyTorch/TF/MXNet) | learning on heterogeneous graphs; hypergraphs only via bipartite/incidence encoding | heterograph relations (bipartite) | DGL binary, CSV | Apache-2.0 | 14,284 | PyPI `dgl` **2.2.1**, **2024-05-13**; last commit **2025-07-31** — maintenance appears stalled | [dmlc/dgl](https://github.com/dmlc/dgl) |
| **TopoNetX** | Python | storage/analysis of topological domains: simplicial, cell, combinatorial complexes, **colored hypergraphs** | combinatorial complex generalises the attributed undirected hypergraph | own loaders; no HIF | MIT | 284 | PyPI `toponetx` **0.4.0**, 2026-01-21; last commit 2026-09-18 | [pyt-team/TopoNetX](https://github.com/pyt-team/TopoNetX) |
| **TopoModelX** | Python | topological deep learning incl. hypergraph message passing (AllSet, UniGNN, HNHN, HyperSAGE…) | via TopoNetX domains | — | MIT | 345 | PyPI `topomodelx` **0.0.1**, **2024-10-20**, while the repo's last commit is 2026-09-17 → install from source | [pyt-team/TopoModelX](https://github.com/pyt-team/TopoModelX) |
| **TopoEmbedX** | Python | representation learning on topological domains (`hyperedge2vec`, `cell2vec`, …) | via TopoNetX domains | — | MIT | 99 | PyPI `topoembedx` **0.3.0**, 2026-05-03; last commit 2026-09-19 | [pyt-team/TopoEmbedX](https://github.com/pyt-team/TopoEmbedX) |

The three `pyt-team` packages are published together as **TopoX**
([Hajij et al., 2024, arXiv:2402.02441](https://arxiv.org/abs/2402.02441), v5 dated 2024-12-09).

---

## 3. Storage and query engines

| Name | Language | Purpose | Hyperedge / n-ary model | Formats & query language | Licence | Stars | Latest release (checked 2026-09-20) | URL |
|---|---|---|---|---|---|---|---|---|
| **TypeDB** | Rust (server); Python/Java/Rust/Node/C# drivers | strongly-typed database with native n-ary relations | **n-ary relation types with named roles**; a relation can itself play a role in another relation (nesting) | TypeQL | MPL-2.0 | 4,458 | releases page shows **TypeDB 3.13.0** (published 8 September); crates.io `typedb-driver` **3.12.3**, 2026-08-11; last commit 2026-09-18 | [typedb/typedb](https://github.com/typedb/typedb) |
| **HyperGraphDB** | Java | embedded, general-purpose hypergraph store (BerkeleyDB backend) | directed, **ordered**, typed links; links can point at links (higher-order) | Java-object serialisation; HGQuery API | Apache-2.0 | 251 | last commit **2025-01-27**; no `org.hypergraphdb` artefact found in the Maven Central query used here `[unverified]` | [hypergraphdb/hypergraphdb](https://github.com/hypergraphdb/hypergraphdb) |
| **OpenCog AtomSpace** | C++ (Scheme, Python bindings) | metagraph/hypergraph database + rewriting engine | typed `Link`s over `Atom`s; ordered and unordered; arbitrarily nested; Values attached to atoms | Atomese s-expressions | GitHub metadata "Other" (`NOASSERTION`) | 999 | last commit 2026-02-10 | [opencog/atomspace](https://github.com/opencog/atomspace) |
| **Hyperon / MeTTa** | Rust + Python | knowledge representation *and* programming language over metagraphs | nested, typed symbolic expressions (a term can contain terms) | MeTTa source | MIT | 280 | PyPI `hyperon` **0.2.10**, 2026-02-11; last commit 2026-02-11 | [trueagi-io/hyperon-experimental](https://github.com/trueagi-io/hyperon-experimental) |
| **Hypergraph-DB** | Python | lightweight embedded hypergraph store with a bundled visualiser | undirected, attributed hyperedges keyed by vertex tuples | own JSON/pickle | Apache-2.0 | 87 | last commit 2025-11-05 | [iMoonLab/Hypergraph-DB](https://github.com/iMoonLab/Hypergraph-DB) |
| **Oxigraph** | Rust (+ `pyoxigraph`, JS/WASM) | SPARQL 1.1 graph database | RDF triples/quads; n-ary only by reification or RDF-star | Turtle, TriG, N-Triples, N-Quads, RDF/XML, N3; SPARQL | Apache-2.0 (crate is `MIT OR Apache-2.0`) | 1,924 | crates.io `oxigraph` **0.5.11**, 2026-09-02; PyPI `pyoxigraph` 0.5.11, 2026-09-02; last commit 2026-09-18 | [oxigraph/oxigraph](https://github.com/oxigraph/oxigraph) |
| **Apache Jena** | Java | RDF framework, TDB2 store, Fuseki server | RDF triples/quads; RDF-star supported | all RDF syntaxes; SPARQL; SHACL | Apache-2.0 | 1,448 | Maven Central `org.apache.jena:jena` **6.1.0**, 2026-05-03; last commit 2026-09-19 | [apache/jena](https://github.com/apache/jena) |
| **Eclipse RDF4J** | Java | RDF framework and stores | RDF triples/quads; RDF-star supported | all RDF syntaxes; SPARQL; SHACL | BSD-3-Clause (Eclipse Distribution Licence) | 415 | Maven Central `org.eclipse.rdf4j:rdf4j` parent POM **5.1.3**, 2025-04-15; last commit 2026-09-19 | [eclipse-rdf4j/rdf4j](https://github.com/eclipse-rdf4j/rdf4j) |
| **rdflib** | Python | RDF parsing, serialisation, in-memory store, SPARQL | RDF triples + named graphs. **No RDF-star**: see below | Turtle, TriG, N-Triples, N-Quads, N3, RDF/XML, JSON-LD, TriX, HexTuples, RDF Patch | BSD-3-Clause | 2,515 | PyPI `rdflib` **7.6.0**, 2026-02-13; last commit 2026-09-16 | [RDFLib/rdflib](https://github.com/RDFLib/rdflib) |

**Verified finding on rdflib and RDF 1.2 (2026-09-20).** In a clean virtualenv with
`rdflib==7.6.0`:

- the format name `turtle-star` raises `PluginException` (no such parser plugin);
- parsing `<< ex:a ex:b ex:c >> ex:certainty 0.9 .` as `turtle` raises `BadSyntax`;
- parsing the RDF-star annotation syntax `ex:s ex:p ex:o {| ex:certainty 0.9 |} .` also raises
  `BadSyntax`.

So as of 7.6.0 rdflib cannot read RDF-star / RDF 1.2 triple terms, and a Python pipeline that
needs them must use `pyoxigraph`, Jena or RDF4J instead. This matters directly for
[../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md](../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md).

---

## 4. Knowledge-graph embedding libraries and n-ary research code

| Name | Language | Purpose | Fact model | Licence | Stars | Last activity (checked 2026-09-20) | URL |
|---|---|---|---|---|---|---|---|
| **PyKEEN** | Python | KG embedding training/evaluation, ~40 models, ~30 datasets | **binary triples only.** A GitHub code search for `hyper-relational` / `hyperrelational` in `pykeen/pykeen` returned 0 matches | MIT | 2,036 | PyPI **1.11.1**, 2025-04-24; last commit 2026-09-06 | [pykeen/pykeen](https://github.com/pykeen/pykeen) |
| **LibKGE** | Python | reproducible KG embedding research (hyper-parameter search) | binary triples only | MIT | 835 | no PyPI distribution; last commit 2026-04-01 | [uma-pi1/kge](https://github.com/uma-pi1/kge) |
| **StarE** | Python | reference implementation of the hyper-relational message-passing encoder; ships **WD50K** | statement = base triple `(s,p,o)` + set of qualifier pairs `(qr,qv)` | MIT | 90 | last commit 2023-12-01 | [migalkin/StarE](https://github.com/migalkin/StarE) |
| **HypE / HSimplE** | Python | knowledge-hypergraph embedding (IJCAI 2020); ships **FB-AUTO** and **M-FB15K** | n-ary tuple `r(e1,…,en)` with positional roles | **no licence file** on either copy | 33 (ServiceNow) / 24 (author) | last commit 2022-07-15 / 2020-05-15 | [ServiceNow/HypE](https://github.com/ServiceNow/HypE), [baharefatemi/HypE](https://github.com/baharefatemi/HypE) |
| **GRAN** | Python (PaddlePaddle) | graph-attention model for n-ary facts (Findings of ACL 2021); ships JF17K, JF17K-3, JF17K-4, WikiPeople, WikiPeople-, WikiPeople-3, WikiPeople-4 | heterogeneous graph over one n-ary fact | Apache-2.0 (Baidu) | — (sub-directory of a monorepo) | — | [PaddlePaddle/Research › KG/ACL2021_GRAN](https://github.com/PaddlePaddle/Research/tree/master/KG/ACL2021_GRAN) |
| **HyNT** | Python | hyper-relational **and numeric** KGs with transformers (KDD 2023); ships the temporal/numeric datasets | qualified statement with numeric literals in qualifiers | GitHub metadata "Other" (`NOASSERTION`) | 36 | last commit 2025-05-27 | [bdi-lab/HyNT](https://github.com/bdi-lab/HyNT) |

---

## 5. LLM / retrieval pipelines that build knowledge hypergraphs

| Name | Language | Purpose | Knowledge model | Licence | Stars | Last activity (checked 2026-09-20) | URL |
|---|---|---|---|---|---|---|---|
| **HyperGraphRAG** | Python | RAG over an LLM-extracted knowledge hypergraph (NeurIPS 2025) | n-ary hyperedge = one natural-language fact linking ≥2 extracted entities | MIT | 451 | last commit 2026-05-12 | [LHRLAB/HyperGraphRAG](https://github.com/LHRLAB/HyperGraphRAG) |
| **Hyper-RAG** | Python | RAG with low-order (pairwise) *and* high-order hyperedges, backed by Hypergraph-DB, with a web UI (Nature Communications 2026) | mixed pairwise + hyperedge store | Apache-2.0 | 322 | last commit 2026-06-27 | [iMoonLab/Hyper-RAG](https://github.com/iMoonLab/Hyper-RAG) |
| **Hyper-Extract** | Python (3.11+) | CLI + library (`he`) turning documents into any of **nine** typed structures — Model, List, Set, Graph, **Hypergraph**, Temporal / Spatial / Spatio-Temporal Graph, Document corpus — via **ten** built-in engines and 40 bilingual domain templates; also an MCP server | hyperedge = named, typed record with an unordered `participants` list; identity declared per template (`entity_id`, `relation_id`, `relation_members`) | **Apache-2.0** (licence file and README badge; *corrected* from the 2026-09-20 reading of GitHub's metadata) | ~4,000 (458 forks) | created 2026-01-07; commit `395039e` 2026-09-20; PyPI `hyperextract` **0.10.3**, 2026-09-20 (19 releases) — checked 2026-09-21; the fastest-growing hypergraph repository found in this survey | [yifanfeng97/hyper-extract](https://github.com/yifanfeng97/hyper-extract) |
| **LightRAG** | Python | *contrast case*: graph RAG with **binary** entity–relation edges | binary edges + vector index | MIT | 39,768 | PyPI `lightrag-hku` **1.5.7**, 2026-09-02; last commit 2026-09-20 | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) |
| **nano-graphrag** | Python | *contrast case*: minimal graph RAG, binary edges; the code ancestor several hypergraph-RAG repos fork | binary edges | MIT | 3,990 | PyPI **0.0.8.2**, 2024-10-19; last commit 2026-01-27 | [gusye1234/nano-graphrag](https://github.com/gusye1234/nano-graphrag) |

Two things stand out. First, the binary-edge GraphRAG implementations still have an order of
magnitude more stars than the hypergraph research repositories (LightRAG 39,768 vs
HyperGraphRAG 451). Second, **Hyper-Extract**, created on 2026-01-07 by Yifan Feng — the author of DHG and
Hyper-RAG, and joint first author of Hyper-KGGen — reached roughly 4,000 stars in about eight months,
nearly as many as nano-graphrag and almost nine times HyperGraphRAG. The hypergraph idea appears to travel
much further when it is packaged as a one-command extraction tool than when it is packaged as a research
pipeline. See
[../07-applications/retrieval-augmented-generation.md](../07-applications/retrieval-augmented-generation.md).

**Hyper-Extract, verified in detail (repository cloned and read 2026-09-21).** The three README figures
most often quoted need deflating. The "11+ Extraction Engines" are ten registered methods —
`chunk_rag`, `graph_rag`, `light_rag`, `hyper_rag`, `hypergraph_rag`, `cog_rag`, `itext2kg`,
`itext2kg_star`, `kg_gen`, `atom` (`hyperextract/methods/registry.py`), of which three are
hypergraph-typed. The "80+ YAML Templates" are 40 files under `hyperextract/templates/presets/`
(general, finance, legal, medicine, tcm, industry, education), each declaring `language: [zh, en]`, so
the count is of language variants. The nine knowledge structures are real and are the nine modules in
`hyperextract/types/`. Two design points matter for this KB. (i) Templates carry an `identifiers:` block
and a validator with diagnostic codes HE-T001…HE-T009, which is more schema discipline than any research
KHG-RAG pipeline applies — but role slots are mandatory only for the *binary* graph family
(`source`/`target`, plus `time_field`/`location_field` for temporal and spatial graphs); the hypergraph
type takes one unordered participant list, so roles vanish exactly where arity rises. (ii) It is the only
tool here built for repeated ingestion — `he feed` under an existing source id, `he remove --document`,
`he info --sources`, with `track_sources=True` source ledgers on both node and edge memories — yet
identity is exact string equality on a key and post-collision merging is an LLM call
(`ontomem`'s `MergeStrategy.LLM.BALANCED`), so inserts can still fork an entity or silently change a
hyperedge's arity. Full analysis in
[../03-construction/skill-driven-extraction-and-the-scenario-gap.md](../03-construction/skill-driven-extraction-and-the-scenario-gap.md).

---

## 6. Knowledge-graph tooling with n-ary-capable data models

| Name | Language | Purpose | n-ary model | Licence | Stars | Latest release (checked 2026-09-20) | URL |
|---|---|---|---|---|---|---|---|
| **KGTK** | Python | Wikidata-scale KG ETL, filtering, querying, graph analytics | KGTK TSV edge file with an explicit `id` per edge, so qualifiers are edges **about edges** | MIT | 422 | PyPI `kgtk` **1.5.4**, 2023-06-29; last commit 2026-07-17 | [usc-isi-i2/kgtk](https://github.com/usc-isi-i2/kgtk) |
| **Wikidata Toolkit** | Java | reading/processing Wikidata JSON dumps and the Wikibase API | Wikibase statement model: main snak + qualifiers + references (a genuine n-ary record) | Apache-2.0 | 413 | Maven Central `org.wikidata.wdtk:*` **0.16.0**, 2024-09-23 | [Wikidata/Wikidata-Toolkit](https://github.com/Wikidata/Wikidata-Toolkit) |

---

## 7. Interchange format and visualisation widgets

| Name | Language | Purpose | Licence | Stars | Last activity (checked 2026-09-20) | URL |
|---|---|---|---|---|---|---|
| **HIF-standard** | JSON Schema + Jupyter notebooks | the Hypergraph Interchange Format: schema, validators for Python/R/Julia, per-library tutorials | MIT | 36 | schema `CHANGELOG.md` lists only **v0.0**; last commit 2026-03-19 | [HIF-org/HIF-standard](https://github.com/HIF-org/HIF-standard) |
| **hypernetx-widget** | JavaScript/React | interactive Jupyter widget for HyperNetX (drag, select, collapse) | GitHub metadata "Other" | 23 | last commit **2021-10-22** — dormant | [pnnl/hypernetx-widget](https://github.com/pnnl/hypernetx-widget) |
| **XGI drawing module** | Python (matplotlib) | `xgi.draw`, `draw_bipartite`, `draw_multilayer`, Rubber-band and convex-hull hyperedge drawing | part of XGI (3-clause BSD) | — | see XGI row above | [xgi.readthedocs.io](https://xgi.readthedocs.io) |
| **Hypergraph-DB visualiser** | Python + JS | browser-based hypergraph viewer shipped with Hypergraph-DB and reused by Hyper-RAG | Apache-2.0 | 87 | last commit 2025-11-05 | [imoonlab.github.io/Hypergraph-DB](https://imoonlab.github.io/Hypergraph-DB/) |

Encoding choices behind these widgets are catalogued in
[../06-visualization/visual-encodings-catalogue.md](../06-visualization/visual-encodings-catalogue.md).

---

## 8. What is missing from the ecosystem

Stated as observations from the table above, not as claims from any one source:

- **No production-grade knowledge-hypergraph database.** TypeDB is the closest (typed n-ary
  relations, active development, 4.5k stars) but is not a hypergraph library and does not read
  HIF. HyperGraphDB and AtomSpace are hypergraph-native but neither has a release in Maven
  Central or a commit in the last seven months respectively.
- **No HIF support anywhere in the learning stack.** DHG, PyG, DGL and the TopoX suite all use
  private formats, so an analysis-side hypergraph cannot be handed to a learning-side model
  without a bespoke converter.
- **No library implements roles on incidences as a first-class concept.** HIF permits
  `incidences[].attrs` (which is how [../../schemas/sample.hif.json](../../schemas/sample.hif.json)
  stores roles), but every library surveyed treats those attributes as opaque payload.
- **The n-ary KG research code is frozen.** StarE (2023-12-01), HypE (2022-07-15 / 2020-05-15)
  and HyNT (2025-05-27) have all stopped; none is packaged; none has a test suite that a
  newcomer can run.

---

## Sources

- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. (2025). *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21. <https://doi.org/10.1017/nws.2025.10018>
- HIF working group. *HIF-standard repository (README, `schemas/hif_schema.json`, `schemas/CHANGELOG.md`).* Checked 2026-09-20. <https://github.com/HIF-org/HIF-standard>
- Landry, N. W., Lucas, M., Iacopini, I., Petri, G., Schwarze, A., Patania, A., Torres, L. (2023). *XGI: A Python package for higher-order interaction networks.* Journal of Open Source Software 8(85), 5162. <https://doi.org/10.21105/joss.05162>
- Lotito, Q. F., Contisciani, M., De Bacco, C., Di Gaetano, L., Gallo, L., Montresor, A., Musciotto, F., Ruggeri, N., Battiston, F. (2023). *Hypergraphx: a library for higher-order network analysis.* Journal of Complex Networks 11(3), cnad019. <https://doi.org/10.1093/comnet/cnad019>
- Pickard, J., Chen, C., Salman, R., Stansbury, C., Kim, S., Surana, A., Bloch, A., Rajapakse, I. (2023). *HAT: Hypergraph analysis toolbox.* PLOS Computational Biology 19(6), e1011190. <https://doi.org/10.1371/journal.pcbi.1011190>
- Hajij, M., Papillon, M., Frantzen, F. et al. (2024). *TopoX: A Suite of Python Packages for Machine Learning on Topological Domains.* arXiv:2402.02441 (v5, 2024-12-09). <https://arxiv.org/abs/2402.02441>
- Feng, Y., You, H., Zhang, Z., Ji, R., Gao, Y. (2019). *Hypergraph Neural Networks.* AAAI 33, 3558–3565. <https://doi.org/10.1609/aaai.v33i01.33013558>
- Gao, Y., Feng, Y., Ji, S., Ji, R. (2023). *HGNN⁺: General Hypergraph Neural Networks.* IEEE TPAMI 45(3), 3181–3199. <https://doi.org/10.1109/TPAMI.2022.3182052>
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. (2020). *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020, 7346–7359. <https://doi.org/10.18653/v1/2020.emnlp-main.596>
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. (2020). *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020, 2191–2197. <https://doi.org/10.24963/ijcai.2020/303>
- Wang, Q., Wang, H., Lyu, Y., Zhu, Y. (2021). *Link Prediction on N-ary Relational Facts: A Graph-based Approach.* Findings of ACL-IJCNLP 2021, 396–407. <https://doi.org/10.18653/v1/2021.findings-acl.35>
- Chung, C., Lee, J., Whang, J. J. (2023). *Representation Learning on Hyper-Relational and Numeric Knowledge Graphs with Transformers.* KDD 2023, 310–322. <https://doi.org/10.1145/3580305.3599490>
- Luo, H., E, H., Chen, G. et al. (2025). *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation.* arXiv:2503.21322 (v3, 2025-10-21); NeurIPS 2025. <https://arxiv.org/abs/2503.21322>
- Feng, Y., Hu, H., Ying, S. et al. (2026). *Hyper-RAG: combating LLM hallucinations using hypergraph-driven retrieval-augmented generation.* Nature Communications 17, 5778 (published 2026-04-27). <https://doi.org/10.1038/s41467-026-71411-1>
- GitHub repository metadata (stars, licence, `pushed_at`) retrieved via the GitHub repository search API on 2026-09-20 for every repository linked above.
- PyPI JSON API (`https://pypi.org/pypi/<name>/json`), crates.io API, Maven Central `search.maven.org` and the Julia General registry (`JuliaRegistries/General`), all queried 2026-09-20, for package versions and upload dates.
- Local verification in a Python 3.11.15 virtualenv with `hypernetx==2.4.3`, `xgi==0.10.2`, `hypergraphx==1.8.0`, `rdflib==7.6.0` (2026-09-20): HIF round-trip behaviour, `hypernetx.hif.schema_url`, and the rdflib RDF-star parse failures reported above.
- Feng, Y. *Hyper-Extract* repository: `README.md`, `LICENSE` (Apache-2.0), `hyperextract/types/`, `hyperextract/methods/registry.py`, `hyperextract/templates/presets/`, `hyperextract/utils/template_engine/validator.py`. Cloned and read at commit `395039e` (2026-09-20); checked 2026-09-21. <https://github.com/yifanfeng97/hyper-extract>
- PyPI `hyperextract` 0.10.3 (Apache-2.0, uploaded 2026-09-20, 19 releases) and `ontomem` 0.6.0 (Apache-2.0), queried 2026-09-21. <https://pypi.org/project/hyperextract/> · <https://pypi.org/project/ontomem/>
