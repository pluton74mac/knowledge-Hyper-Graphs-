# Sources — section 04, storage and formats

Every source cited by a note in [`kb/04-storage-and-formats/`](../../kb/04-storage-and-formats/),
grouped by theme. Entries give author(s), title, venue or publisher, year, and URL. Repository,
documentation and specification entries give the date they were checked. Compiled 2026-09-20.

## Hypergraph interchange: the HIF standard

- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. "HIF: The hypergraph interchange format for higher-order networks." *Network Science* 13, e21, 2025. https://doi.org/10.1017/nws.2025.10018
- HIF-standard repository: README, `schemas/hif_schema.json` and `schemas/hif_schema_v0.1.0.json` (JSON Schema draft-07, identical validation rules), `schemas/CHANGELOG.md` (single entry, v0.0), `CITATION.cff`, `tests/`. Checked 2026-09-20; cloned in full 2026-09-23 at HEAD `b691a3d2ec32100c0229ebe1151e9afad015c356` (2026-03-19, 139 commits). https://github.com/HIF-org/HIF-standard — canonical home (corrected 2026-09-24: not a mirror). The same repository is reachable by GitHub redirect under its earlier names, https://github.com/pszufe/HIF-standard and https://github.com/pszufe/HIF_validators
- HIF Zenodo record, DOI 10.5281/zenodo.15802759. https://doi.org/10.5281/zenodo.15802759
- `pszufe/HIF_validators` is the original name of the HIF-standard repository, not a separate validators repository (corrected 2026-09-24). The `$id` of `hif_schema.json`, `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/schema.json`, returns 404 because the file was renamed 21 minutes after that `$id` was written (commits `58447e4`, `6ffdb48`, `c8e2d4f`, 2025-05-02).
- "A Blue Start: A large-scale pairwise and higher-order social network dataset." arXiv:2505.11608. https://arxiv.org/abs/2505.11608
- "Efficient Gillespie algorithms for spreading phenomena in large and heterogeneous higher-order networks." arXiv:2509.20174. https://arxiv.org/abs/2509.20174

## Hypergraph libraries and their file formats

- XGI repository: `xgi/convert/hif_dict.py`, `xgi/readwrite/json.py`, `xgi/convert/hypergraph_dict.py`. Version 0.10.2, released 2026-05-15. Checked 2026-09-20. https://github.com/xgi-org/xgi
- Landry, N. W., Lucas, M., Iacopini, I., Petri, G., Schwarze, A., Patania, A., Torres, L. "XGI: A Python package for higher-order interaction networks." *Journal of Open Source Software* 8, 5162, 2023. https://doi.org/10.21105/joss.05162
- xgi-data repository (all datasets stored in HIF, hosted on Zenodo). Checked 2026-09-20. https://github.com/xgi-org/xgi-data
- HyperNetX repository, `hypernetx/__init__.py` exporting `to_hif`/`from_hif`; version 2.4.3, released 2026-07-23. Checked 2026-09-20. https://github.com/pnnl/HyperNetX
- HypergraphX repository: `hypergraphx/readwrite/__init__.py`, `io_json.py`, `save.py`, `hif.py`. Version 1.8.0, released 2026-05-18. Checked 2026-09-20. https://github.com/HGX-Team/hypergraphx
- Hypergraph-DB repository: README (features, performance stress test, persistence, `save_as_hif`/`load_from_hif`). Version 0.3.0, PyPI upload 2025-10-14. Checked 2026-09-20. https://github.com/iMoonLab/Hypergraph-DB
- DHG (DeepHypergraph) repository: `dhg/structure/hypergraphs/hypergraph.py`; README news entry for v0.9.7, 2026-08-02. Checked 2026-09-20. https://github.com/iMoonLab/DeepHypergraph — documentation https://deephypergraph.readthedocs.io/
- NetworkX repository, `networkx/readwrite/graphml.py` (raises on `<hyperedge>`) and `gexf.py`. Version 3.6.1. Checked 2026-09-20. https://github.com/networkx/networkx
- NetworkX documentation: GML read/write, JSON (node-link) read/write. Checked 2026-09-20. https://networkx.org/documentation/stable/reference/readwrite/gml.html , https://networkx.org/documentation/stable/reference/readwrite/json_graph.html

## Partitioning formats and tools

- Mt-KaHyPar, *File Formats* documentation (hMetis grammar, weight types, fix file format, conversion tools). Checked 2026-09-20. https://github.com/kahypar/mt-kahypar/blob/master/mt-kahypar/io/docs/FileFormats.md
- KaHyPar repository README (objectives including km1, fixed vertices, hMetis format). Checked 2026-09-20. https://github.com/kahypar/kahypar
- Karypis, G. et al. *hMETIS: A Hypergraph Partitioning Package*, manual. https://karypis.github.io/glaros/files/sw/hmetis/manual.pdf

## Graph and network file formats

- GraphML, *The GraphML File Format — DTD specification* (`<hyperedge>`, `<endpoint>` with `type` in/out/undir). Checked 2026-09-20. http://graphml.graphdrawing.org/specification/dtd.html
- GraphML Primer, section 3.2 "Hyperedges". Checked 2026-09-20. http://graphml.graphdrawing.org/primer/graphml-primer.html
- GEXF format documentation, version 1.3. Checked 2026-09-20. https://gexf.net/basic.html
- Graphviz, *The DOT Language*. Checked 2026-09-20. https://graphviz.org/doc/info/lang.html
- Chiba, H., Yamanaka, R., Matsumoto, S. *Property Graph Exchange Format* (PG Format, PG-JSON, PG-JSONL), 2019. https://pg-format.github.io/
- Apache TinkerPop, *IO Reference* (GraphSON 3.0 adjacency-list form). Checked 2026-09-20. https://tinkerpop.apache.org/docs/current/dev/io/
- Apache TinkerPop, *Gremlin reference*. Checked 2026-09-20. https://tinkerpop.apache.org/docs/current/reference/
- Cytoscape, *Cytoscape Exchange Format Specification (Version 2)*, dated 22 July 2025. Checked 2026-09-20. https://cytoscape.org/cx/cx2/specification/cytoscape-exchange-format-specification-(version-2)/
- Neo4j, *Cypher Manual* and *LOAD CSV*. Checked 2026-09-20. https://neo4j.com/docs/cypher-manual/current/ , https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/

## Matrix, columnar and binary formats

- NIST, *Matrix Market: File Formats*. Checked 2026-09-20. https://math.nist.gov/MatrixMarket/formats.html
- Apache Parquet documentation. Checked 2026-09-20. https://parquet.apache.org/docs/
- Apache Arrow columnar format specification. Checked 2026-09-20. https://arrow.apache.org/docs/format/Columnar.html
- The HDF Group, *HDF5 File Format Specification*. Checked 2026-09-20. https://support.hdfgroup.org/documentation/hdf5/latest/_s_p_e_c.html
- SciPy, *Sparse arrays and matrices* reference. Checked 2026-09-20. https://docs.scipy.org/doc/scipy/reference/sparse.html

## W3C standards: RDF, SPARQL, JSON-LD, PROV

- W3C. *RDF 1.2 Concepts and Abstract Syntax*, Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. *RDF 1.2 Turtle*, Working Draft, 14 September 2026. https://www.w3.org/TR/rdf12-turtle/
- W3C. *RDF 1.2 N-Triples*, Working Draft, 23 July 2026. https://www.w3.org/TR/rdf12-n-triples/
- W3C. *SPARQL 1.2 Query Language*, Working Draft, 13 September 2026. https://www.w3.org/TR/sparql12-query/
- W3C. *RDF 1.1 Semantics*, Recommendation, 2014. https://www.w3.org/TR/rdf11-mt/
- W3C. *JSON-LD 1.1*, Recommendation, 16 July 2020. https://www.w3.org/TR/json-ld11/
- W3C. *PROV-O: The PROV Ontology*, Recommendation, 30 April 2013. https://www.w3.org/TR/prov-o/
- Noy, N., Rector, A. (eds.). *Defining N-ary Relations on the Semantic Web*. W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- Wikipedia. *Graph Query Language* — ISO/IEC 39075:2024 (GQL) published 12 April 2024; SQL/PGQ as Part 16 of SQL:2023. Checked 2026-09-20. https://en.wikipedia.org/wiki/Graph_Query_Language

## Triple stores and RDF implementations

- Apache Jena, `CHANGES.txt` — releases 5.4.0 (2025-04-27, experimental RDF 1.2 preview), 5.5.0 (2025-07-18, `StatementTerm`), 6.0.0 (2026-02-04), 6.1.0 (2026-05-11, full RDF 1.2 syntax I/O), 6.2.0 (2026-07-31). Checked 2026-09-20. https://github.com/apache/jena/blob/main/CHANGES.txt
- Oxigraph, `CHANGELOG.md` — 0.5.3 (2025-12-19), 0.5.4 (2026-01-24), 0.5.5 (2026-02-14), 0.5.7 (2026-04-19), unreleased join-order work. Checked 2026-09-20. https://github.com/oxigraph/oxigraph/blob/main/CHANGELOG.md
- pyoxigraph on PyPI, version 0.5.11 released 2026-09-02. Checked 2026-09-20. https://pypi.org/project/pyoxigraph/
- Ontotext, *RDF-star and SPARQL-star*, GraphDB 11.5 documentation. Checked 2026-09-20 (direct fetch returned an interstitial). https://graphdb.ontotext.com/documentation/11.5/rdf-sparql-star.html
- Stardog, *Edge Properties* documentation (Stardog 7.1+, subject position only, no nesting). Checked 2026-09-20. https://docs.stardog.com/query-stardog/edge-properties
- Eclipse RDF4J project site. Checked 2026-09-20. https://rdf4j.org/
- QLever, *Compliance* documentation (SPARQL 1.1 test suite only). Checked 2026-09-20. https://docs.qlever.dev/compliance/
- Blazegraph, *RDR* wiki page (Reification Done Right, statement identifiers). Checked 2026-09-20. https://github.com/blazegraph/database/wiki/RDR
- Franz Inc., *Triple Attributes*, AllegroGraph 9.0.3 documentation, last updated 20 August 2026. Checked 2026-09-20. https://franz.com/agraph/support/documentation/current/triple-attributes.html

## Hypergraph and n-ary databases

- Iordanov, B. "HyperGraphDB: A Generalized Graph Database." *Lecture Notes in Computer Science* 6185, pp. 25–36, 2010 (WAIM 2010 workshops). https://doi.org/10.1007/978-3-642-16720-1_3 — full text https://hypergraphdb.org/docs/hypergraphdb.pdf
- HyperGraphDB repository. Checked 2026-09-20. https://github.com/hypergraphdb/hypergraphdb
- TypeDB, *Entities, relations, attributes* (TypeQL documentation). Checked 2026-09-20. https://typedb.com/docs/core-concepts/typeql/entities-relations-attributes/
- OpenCog AtomSpace repository README (metagraph store, typed s-expressions, Atoms and Values). Checked 2026-09-20. https://github.com/opencog/atomspace
- `atomspace-rocks` (RocksDB persistence) and `atomspace-cog` (distributed storage). Checked 2026-09-20. https://github.com/opencog/atomspace-rocks , https://github.com/opencog/atomspace-cog
- TrueAGI, *hyperon-experimental* repository README (MeTTa, "Atomese 2"). Checked 2026-09-20. https://github.com/trueagi-io/hyperon-experimental
- Apache AGE repository README (PostgreSQL extension, openCypher, PostgreSQL 11–18). Checked 2026-09-20. https://github.com/apache/age
- Kùzu repository README (columnar disk-based storage, CSR join indices); version 0.11.3 released 2025-10-10. Checked 2026-09-20. https://github.com/kuzudb/kuzu
- TerminusDB repository README, "Project Overview (Updated May 2026)", version 12 features. Checked 2026-09-20. https://github.com/terminusdb/terminusdb
- ArangoDB graphs documentation. Checked 2026-09-20. https://docs.arangodb.com/stable/graphs/
- TigerGraph, *Defining a graph schema* (GSQL reference). Checked 2026-09-20. https://docs.tigergraph.com/gsql-ref/current/ddl-and-loading/defining-a-graph-schema
- SurrealDB, *Graph model* documentation. Checked 2026-09-20. https://surrealdb.com/docs/surrealdb/models/graph
- Datomic documentation. Checked 2026-09-20. https://docs.datomic.com/
- RelationalAI documentation. Checked 2026-09-20. https://docs.relational.ai/

## Relational, Datalog and query-engine foundations

- Souffle repository README (Datalog with records, optimal index selection). Checked 2026-09-20. https://github.com/souffle-lang/souffle — project site https://souffle-lang.github.io/
- Aref, M., ten Cate, B., Green, T. J., Kimelfeld, B., Olteanu, D., Pasalic, E., Veldhuizen, T. L., Washburn, G. "Design and Implementation of the LogicBlox System." SIGMOD 2015, pp. 1371–1382. https://doi.org/10.1145/2723372.2742796
- PostgreSQL documentation, `CREATE TABLE`. Checked 2026-09-20. https://www.postgresql.org/docs/current/sql-createtable.html

## Tensors, sparse representations and hypergraph learning

- Cooper, J., Dutle, A. "Spectra of uniform hypergraphs." *Linear Algebra and its Applications* 436(9), pp. 3268–3292, 2012. https://doi.org/10.1016/j.laa.2011.11.018
- Bai, S., Zhang, F., Torr, P. H. S. "Hypergraph Convolution and Hypergraph Attention." arXiv:1901.08150, 23 January 2019. https://arxiv.org/abs/1901.08150
- PyTorch Geometric, *HypergraphConv* API documentation (`hyperedge_index` of shape `(2, E)`). Checked 2026-09-20. https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.conv.HypergraphConv.html

## Hypergraph-RAG systems and hybrid storage

- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., Feng, Y., Kuang, Z., Song, M., Zhu, Y., Luu, A. T. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025, pp. 152206–152234. https://proceedings.neurips.cc/paper_files/paper/2025/hash/df55ee6e59f8ac4a625219e11fe9ddba-Abstract-Conference.html
- HyperGraphRAG repository: `hypergraphrag/hypergraphrag.py`, `storage.py`, `operate.py`, `base.py`. Checked 2026-09-20. https://github.com/LHRLAB/HyperGraphRAG
- Feng, Y., Hu, H., Ying, S., Hou, X., Liu, S., Yang, M., Li, J., Du, S., Zheng, N., Hu, H., Gao, Y. "Hyper-RAG: combating LLM hallucinations using hypergraph-driven retrieval-augmented generation." *Nature Communications* 17, 27 April 2026. https://doi.org/10.1038/s41467-026-71411-1
- Hyper-RAG repository: `hyperrag/storage.py`, `hyperrag/operate.py`, README. Checked 2026-09-20. https://github.com/iMoonLab/Hyper-RAG
- LightRAG repository and `docs/LightRAG-API-Server.md` ("Storage Types Supported", `PGTableGraphStorage` vs `PGGraphStorage` measurements from PR #3103). Checked 2026-09-20. https://github.com/HKUDS/LightRAG
- NanoVectorDB on PyPI, version 0.0.4.3 uploaded 2024-11-11. Checked 2026-09-20. https://pypi.org/project/nano-vectordb/
- Milvus documentation. https://milvus.io/docs
- Faiss repository. https://github.com/facebookresearch/faiss

## Provenance, versioning and scale

- Nanopublications documentation site (assertion / provenance / publication info; RDF; decentralized server network). Checked 2026-09-20. https://nanopub.net/
- Groth, P., Gibson, A., Velterop, J. "The anatomy of a nanopublication." *Information Services and Use* 30(1–2), 2010. https://dl.acm.org/doi/10.5555/1883685.1883690
- Wikidata, *Wikidata:Statistics* (item count; the page's figure is dated 31 August 2025). Checked 2026-09-20. https://www.wikidata.org/wiki/Wikidata:Statistics
- Wikipedia, *Wikidata* (≈1.65 billion statements, early 2025). Checked 2026-09-20. https://en.wikipedia.org/wiki/Wikidata
- Wikipedia, *Freebase (database)* (≈44 million topics, ≈2.4 billion facts at shutdown). Checked 2026-09-20. https://en.wikipedia.org/wiki/Freebase_(database)
- Bollacker, K., Evans, C., Paritosh, P., Sturge, T., Taylor, J. "Freebase: a collaboratively created graph database for structuring human knowledge." SIGMOD 2008. https://dl.acm.org/doi/10.1145/1376616.1376746

## Research prototypes, 2023–2026

- Bansal, A. "HGQL: Supporting Schematic Hypergraphs in GraphQL." IDEAS '23, pp. 9–16, 5 May 2023. https://doi.org/10.1145/3589462.3589481
- Adler, E., Böttcher, S., Hartel, R. "Compressing Hypergraphs using Suffix Sorting." arXiv:2506.05023, 5 June 2025. https://arxiv.org/abs/2506.05023
- Preti, G., Anagnostopoulos, A., Bonchi, F. "HyDRA: Lossless Hypergraph Summarization via Co-Clustering." arXiv:2606.18274, 5 June 2026. https://arxiv.org/abs/2606.18274
- "Labeled Incidence Structures for Native Transformer Modeling of Text, Knowledge Graphs, and Hypergraphs." arXiv:2609.20278, 29 July 2026. https://arxiv.org/abs/2609.20278

## Tools used to verify the sample files

- `jsonschema` 4.26.0 (Python), Draft-07 validator, used on [`schemas/sample.hif.json`](../../schemas/sample.hif.json) on 2026-09-20: 0 errors. https://pypi.org/project/jsonschema/
- `pyoxigraph` 0.5.11, used to parse [`schemas/sample-n-ary-fact.ttl`](../../schemas/sample-n-ary-fact.ttl) on 2026-09-20: 32 quads, no errors. https://pypi.org/project/pyoxigraph/

## Added by project P2 (2026-09-24) — HIF re-checked from primary sources

Cited by [`kb/04-storage-and-formats/hif-hypergraph-interchange-format.md`](../../kb/04-storage-and-formats/hif-hypergraph-interchange-format.md)
§0–§7 and §10, as corrected on 2026-09-24.

- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. "HIF: The hypergraph interchange format for higher-order networks." arXiv:2507.11520, v1 2025-07-15, v2 2026-01-30 (typeset in the journal template; page numbers in the KB refer to v2). https://arxiv.org/abs/2507.11520
- Crossref metadata for DOI 10.1017/nws.2025.10018: online publication 2025-12-11, licence CC BY 4.0, author affiliations. Checked 2026-09-24. https://api.crossref.org/works/10.1017/nws.2025.10018
- HIF Zenodo versions: v0.1.0, 2025-07-04, https://doi.org/10.5281/zenodo.15802760 ; v0.1.1, 2025-10-02, https://doi.org/10.5281/zenodo.17251025 ; v0.1.2, 2025-10-03, https://doi.org/10.5281/zenodo.17257719 (archive `pszufe/HIF-standard-v0.1.2.zip`, both schema files byte-identical to HEAD). Version list checked through the Zenodo API 2026-09-24.
- HIF-standard issues [#2](https://github.com/HIF-org/HIF-standard/issues/2) (repository name, 2024-07-26), [#51](https://github.com/HIF-org/HIF-standard/issues/51) (v2 goals, 2025-11-21), [#55](https://github.com/HIF-org/HIF-standard/issues/55) ("v1 released … HIF v2, in current development", 2025-12-09), and pull request [#34](https://github.com/HIF-org/HIF-standard/pull/34) ("Split schema title and version", merged 2025-05-02). Read via WebFetch 2026-09-23; issue comment threads not fully readable `[unverified]`.
- GitHub Docs. "Renaming a repository" and "Transferring a repository" (redirects stop if the old name is reused). Read 2026-09-23. https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository ; https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository
- JSON Schema draft 2019-09 release notes (`unevaluatedProperties` is new in 2019-09, so draft-07 validators ignore it). https://json-schema.org/draft/2019-09/release-notes
- P2 research report 02, "What the HIF standard says today, from primary sources" (2026-09-23), with vendored schema snapshots, 36 validation cases and results. [projects/p2-role-aware-hif/research/02-hif-standard.md](../../projects/p2-role-aware-hif/research/02-hif-standard.md)
- P2 research report 03, "XGI and HyperNetX HIF input and output, probed" (2026-09-23). [projects/p2-role-aware-hif/research/03-library-probes.md](../../projects/p2-role-aware-hif/research/03-library-probes.md)
- P2 design, §4 (`role-convention` 1.0.0, `khg-hif/1.0.0`), §5 (loaders), §12.3 (upstream proposal); library evidence file. [projects/p2-role-aware-hif/DESIGN.md](../../projects/p2-role-aware-hif/DESIGN.md) ; [tests/evidence/library-hif-evidence.json](../../tests/evidence/library-hif-evidence.json)
