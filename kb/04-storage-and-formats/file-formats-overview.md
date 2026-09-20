---
title: File formats that can carry a hypergraph or n-ary knowledge
type: comparison
status: draft
tags: [file-format, serialisation, hif, rdf-star, graphml, hgr, interchange, mime]
created: 2026-09-20
updated: 2026-09-20
---

# File formats that can carry a hypergraph or n-ary knowledge

This note is the map of the territory: every file format that a knowledge hypergraph could be
written to, what it can and cannot express, and what will read it. Deep dives live in
[hif-hypergraph-interchange-format.md](hif-hypergraph-interchange-format.md),
[rdf-star-and-semantic-web-serialisations.md](rdf-star-and-semantic-web-serialisations.md) and
[tensor-and-sparse-representations.md](tensor-and-sparse-representations.md); the decision guide is
[format-recommendations.md](format-recommendations.md).

All entries were checked on 2026-09-20 unless a different date is given.

## 1. The three questions that separate the formats

A knowledge hypergraph needs four things from a file format, and almost no format gives all four:

1. **Arity.** Can one record name more than two entities? Formats split into *native* (a record is a
   set or tuple of members: HIF, `.hgr`, GraphML `<hyperedge>`, HypergraphDB, Atomese),
   *emulated* (the n-ary fact becomes a node plus n binary edges: every property-graph format, and
   RDF via reification), and *none*.
2. **Roles.** Once arity > 2, membership is not enough: `treats(metformin, T2DM, 500mg, adults)`
   needs to say which member is the dosage. Only HIF (via incidence `attrs`), RDF/TypeQL-style
   role properties, and the role-edge emulation patterns carry this. `.hgr` and most analysis
   formats do not — see [property-graph-emulation-patterns.md](property-graph-emulation-patterns.md).
3. **Direction.** Head/tail partition of the members (a directed hyperedge). HIF has it
   (`"direction": "head" | "tail"`), GraphML has it per endpoint (`in`/`out`/`undir`), `.hgr` does not.
4. **Nesting.** A fact whose member is itself a fact. Native only in HypergraphDB, Atomese/MeTTa and
   RDF 1.2 triple terms; everything else needs an identifier indirection.

## 2. Comparison table

Abbreviations: **HE** = hyperedge support (native / emulated / none); **Dir** = direction on
hyperedges; **Attr** = attributes on nodes/edges/incidences; **Nest** = an edge may be a member of
an edge.

| Format | Extension / media type | HE | Dir | Attr | Nest | Main tooling | Spec |
|---|---|---|---|---|---|---|---|
| **HIF** (Hypergraph Interchange Format) | `.json`, `.hif.json`; `application/json` (no registered type) | native (incidence records) | yes (`head`/`tail`) | node, edge, incidence, network | no (edge IDs only) | XGI, HyperNetX, HypergraphX, HAT, SimpleHypergraphs.jl, Hypergraph-DB | [HIF-standard repo](https://github.com/pszufe/HIF-standard); [Coll et al., 2025](https://doi.org/10.1017/nws.2025.10018) |
| **XGI legacy JSON** (`xgi-data` v1) | `.json` | native (`edge-dict`) | no (undirected/simplicial) | `hypergraph-data`, `node-data`, `edge-data` | no | XGI only; `write_json` deprecated in favour of `write_hif` | [xgi/readwrite/json.py](https://github.com/xgi-org/xgi/blob/main/xgi/readwrite/json.py) |
| **HypergraphX JSON** | `.json` | native (`{"type":"edge","interaction":[...]}`) | yes (DirectedHypergraph) | per-record `metadata`; `weight`, `layer`, `time` | no | HypergraphX | [hypergraphx/readwrite/io_json.py](https://github.com/HGX-Team/hypergraphx/blob/main/hypergraphx/readwrite/io_json.py) |
| **HypergraphX pickle** | `.pkl` | native | yes | yes | no | HypergraphX (Python only, unsafe across versions) | [hypergraphx/readwrite/save.py](https://github.com/HGX-Team/hypergraphx/blob/main/hypergraphx/readwrite/save.py) |
| **HyperNetX** (in-memory / pandas) | `.csv` incidence pairs, or HIF | native | no | yes (dataframe columns) | no | HyperNetX 2.4.3 (`to_hif`/`from_hif`) | [HyperNetX](https://github.com/pnnl/HyperNetX) |
| **Hypergraph-DB** | `.hgdb` (pickle); also `.hif.json` | native | no | vertex and hyperedge property dicts | no | `hypergraph-db` 0.3.0; Hyper-RAG | [Hypergraph-DB](https://github.com/iMoonLab/Hypergraph-DB) |
| **hMETIS / PaToH / KaHyPar** | `.hgr` (plain text) | native (one line per net) | no | integer weights only | no | hMETIS, PaToH, KaHyPar, Mt-KaHyPar, Zoltan | [Mt-KaHyPar FileFormats.md](https://github.com/kahypar/mt-kahypar/blob/master/mt-kahypar/io/docs/FileFormats.md); [hMETIS manual](https://karypis.github.io/glaros/files/sw/hmetis/manual.pdf) |
| **Matrix Market** (sparse incidence) | `.mtx`; text | native *as a matrix* (H is nodes x edges) | via two matrices (head/tail) | none (one numeric value per entry) | no | SciPy, MATLAB, Octave, most sparse-LA stacks | [NIST Matrix Market formats](https://math.nist.gov/MatrixMarket/formats.html) |
| **RDF 1.2 / RDF-star Turtle** | `.ttl`; `text/turtle` | emulated (reifier + role properties) or triple terms | n/a (roles instead) | yes, on the reifier | **yes** (triple terms) | Jena 6.x, Oxigraph, RDF4J, GraphDB, rdflib | [RDF 1.2 Turtle WD, 14 Sept 2026](https://www.w3.org/TR/rdf12-turtle/) |
| **RDF 1.2 TriG** | `.trig`; `application/trig` | emulated + named graphs per fact | n/a | yes | yes | same as Turtle | [RDF 1.2 Concepts CR, 7 Apr 2026](https://www.w3.org/TR/rdf12-concepts/) |
| **RDF 1.2 N-Triples / N-Quads** | `.nt`, `.nq`; `application/n-triples` | emulated / triple terms | n/a | yes | yes | streaming loaders | [RDF 1.2 N-Triples WD, 23 July 2026](https://www.w3.org/TR/rdf12-n-triples/) |
| **JSON-LD 1.1** | `.jsonld`; `application/ld+json` | emulated (relation-instance object) | n/a | yes | via nested objects (not triple terms) | rdflib, jsonld.js, Oxigraph 0.5.5+ | [JSON-LD 1.1, W3C Rec 16 July 2020](https://www.w3.org/TR/json-ld11/) |
| **TypeQL schema + data** | `.tql` | **native n-ary relation with named roles** | roles, not head/tail | attributes on relations | relations may play roles (nesting) | TypeDB / TypeQL only | [TypeDB docs](https://typedb.com/docs/core-concepts/typeql/entities-relations-attributes/) |
| **GraphML** | `.graphml`; `application/xml` | **native** `<hyperedge>` with `<endpoint>` | per endpoint: `in`/`out`/`undir` | `<data>` keys on nodes, edges, hyperedges | nested *graphs*, not nested edges | yEd, Gephi (partial); NetworkX **refuses** hyperedges | [GraphML DTD spec](http://graphml.graphdrawing.org/specification/dtd.html) |
| **GEXF** | `.gexf` | none (binary `<edge source target>`) | yes (binary) | `<attvalues>`, dynamic attributes | no | Gephi, NetworkX | [GEXF 1.3](https://gexf.net/basic.html) |
| **GML** (Graph Modelling Language) | `.gml` | none | yes (`directed 1`) | arbitrary key-value | no | Gephi, igraph, NetworkX | [NetworkX GML reader/writer docs](https://networkx.org/documentation/stable/reference/readwrite/gml.html) |
| **DOT (Graphviz)** | `.gv`, `.dot`; `text/vnd.graphviz` | none; `subgraph -> subgraph` expands to the pairwise cross product | yes | yes | no (clusters are layout, not semantics) | Graphviz, pydot | [DOT language](https://graphviz.org/doc/info/lang.html) |
| **Cypher CSV import** | `.csv` + `LOAD CSV` script | emulated (one CSV per hyperedge-node table) | via relationship types | node/relationship properties | no | Neo4j, Memgraph, `neo4j-admin import` | [Neo4j LOAD CSV](https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/) |
| **PG / PG-JSON / PG-JSONL** | `.pg`, `.json`, `.jsonl` | none (`--` and `->` are binary) | yes | labels + properties on both | no | `pg` tools (Chiba et al.) | [Property Graph Exchange Format](https://pg-format.github.io/) |
| **GraphSON 3.0** | `.json` | none (adjacency list of vertices) | yes | properties, meta-properties | no | Apache TinkerPop, Gremlin | [TinkerPop IO reference](https://tinkerpop.apache.org/docs/current/dev/io/) |
| **Cytoscape CX2** | `.cx2`; JSON | none (`edges` have exactly `s` and `t`) | yes | `v` attribute objects, declared types | no | Cytoscape Desktop/Web, NDEx | [CX2 specification, 22 July 2025](https://cytoscape.org/cx/cx2/specification/cytoscape-exchange-format-specification-(version-2)/) |
| **NetworkX JSON** (`node_link_data`) | `.json` | none | yes | yes | no | NetworkX 3.6.1 | [NetworkX JSON readwrite](https://networkx.org/documentation/stable/reference/readwrite/json_graph.html) |
| **OpenCog Atomese / MeTTa** | `.scm` (s-expressions), `.metta` | **native and nested** (a link is a tuple of atoms) | ordered arguments | Values attached per atom | **yes** | AtomSpace, `atomspace-rocks`, Hyperon/MeTTa | [AtomSpace README](https://github.com/opencog/atomspace) |
| **Parquet / Arrow incidence table** | `.parquet`, `.arrow`/IPC | native via a long `(edge_id, node_id, role, direction)` table | as a column | as columns; nested/struct columns allowed | via an `edge_id` appearing as a `node_id` | DuckDB, pandas, Polars, Spark | [Apache Parquet](https://parquet.apache.org/docs/), [Apache Arrow](https://arrow.apache.org/docs/format/Columnar.html) |
| **HDF5** | `.h5`, `.hdf5` | native via stored CSR/COO arrays | as an array | HDF5 attributes | no | h5py, PyTables, MATLAB | [HDF5 file format spec](https://support.hdfgroup.org/documentation/hdf5/latest/_s_p_e_c.html) |

Notes on the table:

- *"No registered media type"* applies to HIF, XGI JSON, HypergraphX JSON, GraphSON and CX2: they
  are JSON documents and travel as `application/json`. Only the W3C RDF family and DOT have IANA
  media types among the formats above.
- GraphML is the only *mainstream* graph format with a native hyperedge element, and it is the
  least used part of the format: "Applications not dealing with hyperedges may ignore this element"
  ([GraphML DTD specification](http://graphml.graphdrawing.org/specification/dtd.html)). NetworkX
  implements exactly that permission as a hard failure: its reader raises
  `NetworkXError("GraphML reader doesn't support hyperedges")`
  ([networkx/readwrite/graphml.py](https://github.com/networkx/networkx/blob/main/networkx/readwrite/graphml.py)).
  So "GraphML supports hyperedges" is true of the standard and false of most of the tool chain.

## 3. The `.hgr` family in detail (hMETIS / PaToH / KaHyPar)

This is the oldest widely used hypergraph file format and it is deliberately minimal. Mt-KaHyPar's
documentation gives the grammar:

```
% comment
num_hyperedges num_hypernodes [weight_type]
[hyperedge_weight_1] pin_1 pin_2 ... pin_i
...
[hypernode_weight_1]
...
```

"The first line is a header containing two or three numbers describing the total number of
hyperedges, the total number of hypernodes and the types of weights used by the hypergraph
(00/omitted = unweighted, 10 = node weights, 01 = edge weights, 11 = node and edge weights)"
([Mt-KaHyPar, FileFormats.md](https://github.com/kahypar/mt-kahypar/blob/master/mt-kahypar/io/docs/FileFormats.md),
checked 2026-09-20). Indices are 1-based in the file; Mt-KaHyPar shifts them to 0-based on read.

Consequences for knowledge hypergraphs: no labels, no roles, no direction, no attributes, integer
weights only. `.hgr` is a *partitioning* format, not a knowledge format. Use it as an export target
when you want to shard a KHG (see
[versioning-provenance-and-scale.md](versioning-provenance-and-scale.md)), never as a store.

## 4. Sparse-matrix formats as hypergraph formats

A hypergraph is equivalent to its incidence matrix **H** (nodes x hyperedges). Matrix Market
coordinate format writes exactly the non-zeros: the header line is
`%%MatrixMarket matrix coordinate real general`, followed by `rows cols nonzeros` and one
`row col value` line per entry ([NIST, Matrix Market formats](https://math.nist.gov/MatrixMarket/formats.html)).
Roles can be smuggled into `value` as an integer code; direction needs two matrices. This is the
cheapest lossless route between a KHG and a linear-algebra stack, and it is what
[tensor-and-sparse-representations.md](tensor-and-sparse-representations.md) builds on.

## 5. What "n-ary knowledge" formats add that "hypergraph" formats lack

The analysis formats (HIF, `.hgr`, Matrix Market, the library JSONs) were designed for
*higher-order network science*: nodes are anonymous integers, edges are sets, and the questions are
degree distributions and diffusion. The knowledge formats (RDF 1.2, JSON-LD, TypeQL) were designed
for *facts*: every member is an IRI, every position has a role name, and the questions are
entailment and provenance. HIF's `attrs` dictionaries are the bridge: they are schema-free, so a
role name on an incidence and a provenance pointer on an edge are legal HIF, but nothing in the
standard says what they mean. The sample in
[`schemas/sample.hif.json`](../../schemas/sample.hif.json) takes that bridge and documents the
convention it uses in its own `metadata` block; the same three facts in RDF 1.2 Turtle are in
[`schemas/sample-n-ary-fact.ttl`](../../schemas/sample-n-ary-fact.ttl).

## 6. Status of the standards landscape (checked 2026-09-20)

| Standard | Body | Status | Date |
|---|---|---|---|
| HIF | community (8 authors, 5 libraries) | schema `v0.0`, published in *Network Science* | 2025 |
| RDF 1.2 Concepts | W3C RDF & SPARQL WG | Candidate Recommendation Snapshot | 7 April 2026 |
| RDF 1.2 Turtle | W3C | Working Draft | 14 September 2026 |
| RDF 1.2 N-Triples | W3C | Working Draft | 23 July 2026 |
| SPARQL 1.2 Query | W3C | Working Draft | 13 September 2026 |
| JSON-LD 1.1 | W3C | Recommendation | 16 July 2020 |
| GQL | ISO/IEC JTC1 SC32 WG3 | published as ISO/IEC 39075:2024 | 12 April 2024 |
| SQL/PGQ | ISO/IEC | Part 16 of SQL:2023 | 2023 |
| GraphML | Graph Drawing community | stable, unchanged for years | 2007-era DTD |

Neither GQL nor SQL/PGQ has a hyperedge construct: both standardise the *property graph* model, so
a KHG in either is an emulation. See
[property-graph-emulation-patterns.md](property-graph-emulation-patterns.md) and
[relational-and-eav-storage.md](relational-and-eav-storage.md).

## Sources

- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B. and Szufel, P. (2025). *HIF: The hypergraph interchange format for higher-order networks*. Network Science 13, e21. https://doi.org/10.1017/nws.2025.10018
- HIF-standard repository (README and `schemas/hif_schema.json`, checked 2026-09-20). https://github.com/pszufe/HIF-standard — mirror https://github.com/HIF-org/HIF-standard
- XGI, `xgi/readwrite/json.py` and `xgi/convert/hif_dict.py` (XGI 0.10.2, 2026-05-15). https://github.com/xgi-org/xgi
- HypergraphX, `hypergraphx/readwrite/` (HGX 1.8.0, 2026-05-18). https://github.com/HGX-Team/hypergraphx
- HyperNetX 2.4.3 (2026-07-23), `hypernetx/__init__.py` exporting `to_hif`, `from_hif`. https://github.com/pnnl/HyperNetX
- Hypergraph-DB 0.3.0 (PyPI upload 2025-10-14). https://github.com/iMoonLab/Hypergraph-DB
- Mt-KaHyPar, *File Formats* documentation (checked 2026-09-20). https://github.com/kahypar/mt-kahypar/blob/master/mt-kahypar/io/docs/FileFormats.md
- Karypis, G. et al. *hMETIS: A Hypergraph Partitioning Package*, manual. https://karypis.github.io/glaros/files/sw/hmetis/manual.pdf
- KaHyPar repository README (checked 2026-09-20). https://github.com/kahypar/kahypar
- NIST. *Matrix Market: File Formats* (checked 2026-09-20). https://math.nist.gov/MatrixMarket/formats.html
- W3C. *RDF 1.2 Concepts and Abstract Syntax*, Candidate Recommendation Snapshot 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. *RDF 1.2 Turtle*, Working Draft 14 September 2026. https://www.w3.org/TR/rdf12-turtle/
- W3C. *RDF 1.2 N-Triples*, Working Draft 23 July 2026. https://www.w3.org/TR/rdf12-n-triples/
- W3C. *SPARQL 1.2 Query Language*, Working Draft 13 September 2026. https://www.w3.org/TR/sparql12-query/
- W3C. *JSON-LD 1.1*, Recommendation 16 July 2020. https://www.w3.org/TR/json-ld11/
- GraphML. *The GraphML File Format — DTD specification* (checked 2026-09-20). http://graphml.graphdrawing.org/specification/dtd.html
- GraphML Primer, section 3.2 "Hyperedges". http://graphml.graphdrawing.org/primer/graphml-primer.html
- NetworkX, `networkx/readwrite/graphml.py` (NetworkX 3.6.1). https://github.com/networkx/networkx/blob/main/networkx/readwrite/graphml.py
- GEXF format documentation, version 1.3 (checked 2026-09-20). https://gexf.net/basic.html
- Graphviz. *The DOT Language* (checked 2026-09-20). https://graphviz.org/doc/info/lang.html
- Chiba, H., Yamanaka, R. and Matsumoto, S. *Property Graph Exchange Format* (PG, PG-JSON, PG-JSONL), 2019. https://pg-format.github.io/
- Apache TinkerPop. *IO Reference — GraphSON* (checked 2026-09-20). https://tinkerpop.apache.org/docs/current/dev/io/
- Cytoscape. *Cytoscape Exchange Format Specification (Version 2)*, 22 July 2025. https://cytoscape.org/cx/cx2/specification/cytoscape-exchange-format-specification-(version-2)/
- TypeDB. *Entities, relations, attributes* (TypeQL documentation, checked 2026-09-20). https://typedb.com/docs/core-concepts/typeql/entities-relations-attributes/
- Apache Parquet documentation. https://parquet.apache.org/docs/
- Apache Arrow columnar format specification. https://arrow.apache.org/docs/format/Columnar.html
- Neo4j. *LOAD CSV* (Cypher Manual, checked 2026-09-20). https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/
- NetworkX. *JSON graph* read/write (node-link format). https://networkx.org/documentation/stable/reference/readwrite/json_graph.html
- OpenCog AtomSpace README (checked 2026-09-20). https://github.com/opencog/atomspace
- Wikipedia. *Graph Query Language* — ISO/IEC 39075:2024 published 12 April 2024; SQL/PGQ as Part 16 of SQL:2023 (checked 2026-09-20). https://en.wikipedia.org/wiki/Graph_Query_Language
