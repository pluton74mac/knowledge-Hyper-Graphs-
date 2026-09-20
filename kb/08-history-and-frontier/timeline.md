---
title: Timeline of hypergraphs as knowledge structures (1956–2026)
type: timeline
status: draft
tags: [hypergraph, history, timeline, knowledge-graph, n-ary, standards, rag]
created: 2026-09-19
updated: 2026-09-19
---

# Timeline of hypergraphs as knowledge structures

This table gives one dated row per event, with the reason the event matters for **knowledge hypergraphs (KHG)** and a primary source. Dates were checked against the source in the last column on 2026-09-19. Where a source could only be reached second-hand, the row says so. Detailed narratives are in [origins-hypergraph-theory.md](origins-hypergraph-theory.md), [knowledge-representation-lineage.md](knowledge-representation-lineage.md), [machine-learning-era.md](machine-learning-era.md), [llm-era-2023-2026.md](llm-era-2023-2026.md) and [standards-convergence.md](standards-convergence.md).

Conventions: "arXiv" dates are v1 submission dates; conference years are the year of the proceedings.

## 1956–1989: prehistory, hypergraph theory, knowledge representation

| Year | Event | Why it matters for KHGs | Source |
|---|---|---|---|
| 1956 | Richard H. Richens (Cambridge Language Research Unit) implements the first computer semantic nets as an interlingua for machine translation | Earliest machine-readable "concept + typed link" structure; the ancestor of KGs | [Wikipedia, Semantic network](https://en.wikipedia.org/wiki/Semantic_network) (secondary) |
| 1968 | M. Ross Quillian, "Semantic Memory", in Minsky (ed.) *Semantic Information Processing*, MIT Press, pp. 227–270 | Canonical semantic-network model (nodes, property links, superordinate links, spreading activation); relations are binary edges | [Quillian, 1968 (summary page)](https://www.jimdavies.org/summaries/quillian1968.html); [PhilPapers record](https://philpapers.org/rec/QUISN) |
| 1969–1970 | Claude Berge, *Graphes et hypergraphes*, Dunod (Paris) | Names and systematises **hypergraphs** (edges as arbitrary vertex subsets); the mathematical object KHGs instantiate | [Wikipedia, Claude Berge](https://en.wikipedia.org/wiki/Claude_Berge); [Open Library record of the 1973 translation](https://openlibrary.org/books/OL14545454M/Graphs_and_hypergraphs) |
| 1972–1973 | Edgar W. Schneider coins the term "knowledge graph" | First use of the phrase later popularised by Google | [Wikipedia, Knowledge graph (History)](https://en.wikipedia.org/wiki/Knowledge_graph) (secondary) |
| 1973 | English edition *Graphs and Hypergraphs*, North-Holland Mathematical Library vol. 6 | Makes Berge's theory the standard English reference | [Internet Archive record](https://archive.org/details/graphshypergraph0000berg); [Stanford catalog](https://searchworks.stanford.edu/view/1348928) |
| 1974 | Marvin Minsky, "A Framework for Representing Knowledge", MIT AI Memo 306 | Frames: slot-filler structures, i.e. an entity with several typed participants; a proto n-ary record | [MIT DSpace](https://dspace.mit.edu/entities/publication/0eca0164-cb5f-42de-8c86-43f54b23306d) |
| 1976 (July) | John F. Sowa, "Conceptual Graphs for a Data Base Interface", *IBM J. Res. Dev.* 20(4):336–357 | Conceptual graphs: **relation nodes** of any arity linking concept nodes, a bipartite drawing of a hypergraph, used as a DB query interface | [Crossref/IBM](https://doi.org/10.1147/rd.204.0336); [ACM DL](https://dl.acm.org/citation.cfm?id=1664387) |
| 1983 (July) | Beeri, Fagin, Maier, Yannakakis, "On the Desirability of Acyclic Database Schemes", *JACM* 30(3):479–513; Fagin, "Degrees of Acyclicity for Hypergraphs and Relational Database Schemes", *JACM* 30(3):514–550 | A relational schema is a hypergraph; α/β/γ-acyclicity govern query tractability, the first large-scale "knowledge as hypergraph" application | [Crossref, Beeri et al.](https://doi.org/10.1145/2402.322389); [ACM DL, Fagin](https://dl.acm.org/doi/10.1145/2402.322390) |
| 1984 (July) | Cyc project starts at MCC under Douglas Lenat; spun out as Cycorp at the end of 1994 | Largest hand-built common-sense KB; uses higher-arity predicates in CycL, showing n-ary facts are needed in practice | [Wikipedia, Cyc](https://en.wikipedia.org/wiki/Cyc); [cyc.com leadership page](https://cyc.com/leadership-team/) |
| 1984 (Oct) | Sowa, *Conceptual Structures: Information Processing in Mind and Machine*, Addison-Wesley | Book-length CG theory; Peirce-style logic on graphs with n-ary relations | [Open Library](https://openlibrary.org/books/OL3500479M/Conceptual_structures); [ACM Guide](https://dl.acm.org/doi/abs/10.5555/4569) |
| 1987 | Berge, *Hypergraphes: combinatoires des ensembles finis*, Gauthier-Villars (English translation *Hypergraphs: Combinatorics of Finite Sets*, North-Holland, 1989 `[unverified]` year of English edition) | Consolidated hypergraph combinatorics | [Wikipedia, Claude Berge](https://en.wikipedia.org/wiki/Claude_Berge) |

## 1993–2011: directed hypergraphs, VLSI, Semantic Web, first hypergraph databases

| Year | Event | Why it matters | Source |
|---|---|---|---|
| 1993 | Gallo, Longo, Pallottino, Nguyen, "Directed hypergraphs and applications", *Discrete Applied Mathematics* 42:177–201 | Defines B-/F-/BF-hyperarcs, paths and cuts; applications to Horn logic, AND–OR graphs, relational databases: the model behind rule-like KHG edges | [ACM DL](https://dl.acm.org/citation.cfm?id=153586); [Semantic Scholar](https://www.semanticscholar.org/paper/158b6f53220b212027c3ffcea56d062d61f9ffd5) |
| 1998–2002 | Gottlob, Leone, Scarcello, "Hypertree Decompositions and Tractable Queries" (arXiv Dec 1998; *JCSS* 64(3):579–627, 2002) | Hypertree width: tractability of conjunctive queries seen as hypergraphs | [arXiv cs/9812022](https://arxiv.org/abs/cs/9812022) |
| 1999 (Feb 22) | W3C RDF Model and Syntax Recommendation | Fixes the binary-triple model that KHGs must later extend | [W3C REC-rdf-syntax-19990222](https://www.w3.org/TR/1999/REC-rdf-syntax-19990222/) |
| 1999 | Karypis, Aggarwal, Kumar, Shekhar, "Multilevel hypergraph partitioning: applications in VLSI domain", *IEEE TVLSI* 7(1):69–79; Çatalyürek & Aykanat, hypergraph partitioning for sparse matrix–vector multiplication, *IEEE TPDS* 10(7):673–693 | Hypergraph partitioning (hMETIS, PaToH) becomes industrial engineering practice | [Crossref Karypis](https://doi.org/10.1109/92.748202); [Crossref Çatalyürek](https://doi.org/10.1109/71.780863) |
| 2004 (Feb 10) | W3C RDF 1.0 suite (Concepts, Semantics, Primer) and OWL 1.0 become Recommendations | Description-logic ontologies on binary properties; n-ary relations need workarounds | [RDF Concepts 2004](https://www.w3.org/TR/2004/REC-rdf-concepts-20040210/); [OWL Reference](https://www.w3.org/TR/owl-ref/) |
| 2006 (Apr 12) | W3C Working Group Note "Defining N-ary Relations on the Semantic Web" (Noy, Rector, eds.) | Codifies the reification patterns (relation instance node; sequence) used to flatten n-ary facts into triples | [W3C swbp-n-aryRelations](https://www.w3.org/TR/swbp-n-aryRelations/) |
| 2006 (Dec) | Zhou, Huang, Schölkopf, "Learning with Hypergraphs: Clustering, Classification, and Embedding", NIPS 19 | Spectral hypergraph learning; the reference point for all later hypergraph ML | [NIPS proceedings](https://papers.nips.cc/paper/3128-learning-with-hypergraphs-clustering-classification-and-embedding) |
| 2007 (Mar 3) | Metaweb announces Freebase | Introduces Compound Value Types (CVTs, "mediators") to store n-ary facts as reified nodes; source of JF17K and FB15k-CVT | [Wikipedia, Freebase](https://en.wikipedia.org/wiki/Freebase_(database)); [Houle, CVTs in RDF](https://database_animals.silvrback.com/compound-value-types-in-rdf) |
| 2010 | Borislav Iordanov, "HyperGraphDB: A Generalized Graph Database", WAIM 2010 Workshops (LNCS), pp. 25–36; Kobrix Software | First production database whose atoms are hyperedges that may contain hyperedges (automatic reification) | [Springer chapter](https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3); [hypergraphdb.org](http://hypergraphdb.org/) |
| 2010 (Jul 16) | Google acquires Metaweb | Freebase becomes input to Google's Knowledge Graph | [Wikipedia, Freebase](https://en.wikipedia.org/wiki/Freebase_(database)) |

## 2012–2019: knowledge graphs at web scale, qualifiers, first n-ary embeddings

| Year | Event | Why it matters | Source |
|---|---|---|---|
| 2012 (May 16) | Google announces the Knowledge Graph ("things, not strings"), 500M objects, 3.5B facts | Popularises the term; industry adopts graph-shaped knowledge | [Google blog](https://blog.google/products-and-platforms/products/search/introducing-knowledge-graph-things-not/) |
| 2012 (Oct 29) | Wikidata launches; statements with qualifiers and references added 4 Feb 2013 | Statement + qualifiers = hyper-relational fact; the largest open source of n-ary data (WikiPeople, WD50K) | [Wikipedia, Wikidata](https://en.wikipedia.org/wiki/Wikidata); [Vrandečić & Krötzsch, CACM 2014](https://doi.org/10.1145/2629489) |
| 2014 (Dec 16) – 2016 (May 2) | Freebase shutdown announced; taken offline; data migrated toward Wikidata | Freezes the Freebase dump used by most n-ary benchmarks | [Wikipedia, Freebase](https://en.wikipedia.org/wiki/Freebase_(database)) |
| 2016 (Apr/Jul) | Wen, Li, Mao, Chen, Zhang, "On the Representation and Embedding of Knowledge Bases Beyond Binary Relations", IJCAI 2016 (arXiv Apr 2016) | **m-TransH**, the first n-ary KG embedding; shows star-to-clique flattening of Freebase loses structure; introduces JF17K | [IJCAI 2016 paper](https://www.ijcai.org/Proceedings/16/Papers/188.pdf); [arXiv 1604.08642](https://arxiv.org/abs/1604.08642) |
| 2016 (Sep 15) | Grakn 0.1.1 released (University of Cambridge origin; commercialised 2017 by Grakn Labs) | Typed n-ary relations with roles ("hyper-relations") in a database schema | [Wikipedia, TypeDB](https://en.wikipedia.org/wiki/TypeDB) |
| 2018 (Feb / Nov) | Benson, Abebe, Schaub, Jadbabaie, Kleinberg, "Simplicial closure and higher-order link prediction", *PNAS* 115(48) | Higher-order link prediction as a benchmark task on 19 hypergraph datasets | [arXiv 1802.06916](https://arxiv.org/abs/1802.06916) |
| 2018 (Sep 25) / 2019 | Feng, You, Zhang, Ji, Gao, "Hypergraph Neural Networks" (HGNN), AAAI 2019 | Starts the hypergraph-neural-network wave | [arXiv 1809.09401](https://arxiv.org/abs/1809.09401) |
| 2019 (Jan 3) | HyperNetX first released by PNNL (BSD-2) | First widely used Python hypergraph library | [OSTI DOE CODE record](https://www.osti.gov/doecode/biblio/22160) |
| 2019 (May) | Guan, Jin, Wang, Cheng, "Link Prediction on N-ary Relational Data" (NaLP), WWW 2019, pp. 583–593 | Role–value-pair formalisation of n-ary facts | [dblp](https://dblp.org/rec/conf/www/GuanJWC19.html) |
| 2019 (Jun 1) | Fatemi, Taslakian, Vazquez, Poole, "Knowledge Hypergraphs: Prediction Beyond Binary Relations" (arXiv; IJCAI 2020 pp. 2191–2197) | Popularises the term **knowledge hypergraph**; HSimplE and HypE embeddings | [arXiv 1906.00137](https://arxiv.org/abs/1906.00137); [IJCAI 2020](https://www.ijcai.org/proceedings/2020/0303.pdf) |
| 2019 (Sep 10) | ISO/IEC JTC 1 approves the GQL project | Start of the first ISO database language since SQL | [Wikipedia, GQL](https://en.wikipedia.org/wiki/Graph_Query_Language) |

## 2020–2023: hyper-relational KGs, higher-order network science, RDF-star

| Year | Event | Why it matters | Source |
|---|---|---|---|
| 2020 (Apr) | Rosso, Yang, Cudré-Mauroux, "Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction" (HINGE), WWW 2020, pp. 1885–1896 | Triple + key–value qualifiers as the "hyper-relational" formalisation | [ACM DL](https://dl.acm.org/doi/fullHtml/10.1145/3366423.3380257) |
| 2020 (Mar 26) | Joslyn et al. (PNNL), "Hypernetwork Science: From Multidimensional Networks to Computational Topology" | Programme statement of the PNNL hypernetwork group | [arXiv 2003.11782](https://arxiv.org/abs/2003.11782) |
| 2020 (Aug 25) | Battiston et al., "Networks beyond pairwise interactions: structure and dynamics", *Physics Reports* 874:1–92 | The higher-order network science review; brings physicists to hypergraphs | [CEU portal](https://research.ceu.edu/en/publications/networks-beyond-pairwise-interactions-structure-and-dynamics/) |
| 2020 (Nov) | Galkin, Trivedi, Maheshwari, Usbeck, Lehmann, "Message Passing for Hyper-Relational Knowledge Graphs" (StarE), EMNLP 2020, pp. 7346–7359 | GNN encoder for qualifiers; exposes leakage in WikiPeople/JF17K; releases WD50K | [ACL Anthology](https://aclanthology.org/2020.emnlp-main.596/) |
| 2020/2021 | Gao et al., "Hypergraph Learning: Methods and Practices", *IEEE TPAMI* | Consolidates a decade of hypergraph learning | [Crossref](https://doi.org/10.1109/TPAMI.2020.3039374) |
| 2021 (Feb 18) | Fatemi, Taslakian, Vazquez, Poole, "Knowledge Hypergraph Embedding Meets Relational Algebra" | ReAlE: embeddings that provably represent relational-algebra operations | [arXiv 2102.09557](https://arxiv.org/abs/2102.09557) |
| 2021 (Apr 20) | Bick, Gross, Harrington, Schaub, "What are higher-order networks?" (SIAM Review 65(3), 2023) | Clarifies hypergraph vs simplicial vs cell-complex models | [arXiv 2104.11329](https://arxiv.org/abs/2104.11329) |
| 2021 (May 20) | Grakn renamed TypeDB (2.1.0 released); Grakn Labs becomes Vaticle | Positions the typed hyper-relational model as a general database | [Wikipedia, TypeDB](https://en.wikipedia.org/wiki/TypeDB); [dbdb.io](https://dbdb.io/db/typedb) |
| 2021 (Jul 10) | Ali, Berrendorf, Galkin, Thost, Ma, Tresp, Lehmann, "Improving Inductive Link Prediction Using Hyper-Relational Facts", ISWC 2021 Best Paper | Qualifiers help inductive (unseen-entity) prediction | [arXiv 2107.04894](https://arxiv.org/abs/2107.04894); [Galkin site](https://migalkin.github.io/) |
| 2021 (Aug 29 – Sep 1) | Dagstuhl Seminar 21352 "Higher-Order Graph Models: From Theoretical Foundations to Machine Learning" (Eliassi-Rad, Latora, Rosvall, Scholtes) | First Dagstuhl meeting devoted to higher-order models | [Dagstuhl 21352](https://www.dagstuhl.de/seminars/seminar-calendar/seminar-details/21352) |
| 2021 (Oct 12) | Battiston et al., "The physics of higher-order interactions in complex systems", *Nature Physics* 17:1093–1098 | High-visibility perspective piece | [arXiv 2110.06023](https://arxiv.org/abs/2110.06023) |
| 2021 (Nov 17) | XGI 0.1 first released on PyPI | Second major Python hypergraph library (NumFOCUS-affiliated) | [PyPI xgi history](https://pypi.org/project/xgi/#history) |
| 2021 (Dec 12) | Goertzel, "Reflective Metagraph Rewriting as a Foundation for an AGI 'Language of Thought'" | MeTTa/Atomspace as a metagraph (hyperedges over hyperedges) | [arXiv 2112.08272](https://arxiv.org/abs/2112.08272) |
| 2021 (Dec 17) | RDF-star and SPARQL-star Final Community Group Report (Hartig, Champin, Kellogg, Seaborne) | Quoted triples: a standard way to annotate a triple with qualifiers | [CG report](https://w3c-cg.github.io/rdf-star/cg-spec/2021-12-17.html) |
| 2022 (Aug 25) | DHG (DeepHypergraph) 0.9.1 released by Tsinghua iMoon-Lab | PyTorch library for hypergraph neural networks | [GitHub iMoonLab/DeepHypergraph](https://github.com/iMoonLab/DeepHypergraph) |
| 2022 (Aug 29) | W3C RDF-star Working Group chartered (initially to 28 Aug 2024; rechartered 2024 for two more years) | Standardisation of statements about statements begins | [Charter 2022](https://www.w3.org/2022/08/rdf-star-wg-charter/); [Proposed 2024 charter](https://www.w3.org/2024/08/proposed-rdf-star-wg-charter.html) |
| 2023 (Mar) | HGNN+ (*TPAMI* 45(3)); Hypergraphx library (*J. Complex Networks* 11(3)) | Maturing HGNN and network-science tooling | [Crossref HGNN+](https://doi.org/10.1109/TPAMI.2022.3182052); [arXiv 2303.15356](https://arxiv.org/abs/2303.15356) |
| 2023 (May 17) | XGI paper, *JOSS* 8(85):5162 | Peer-reviewed release of XGI | [JOSS](https://joss.theoj.org/papers/10.21105/joss.05162) |
| 2023 (Jun) | SQL:2023 adopted, including Part 16 SQL/PGQ (ISO/IEC 9075-16:2023) | Property graphs enter SQL; still binary edges | [Wikipedia, SQL:2023](https://en.wikipedia.org/wiki/SQL:2023); [ISO 9075-16](https://www.iso.org/standard/79473.html) |
| 2023 (Aug 26) | Antelmi et al., "A Survey on Hypergraph Representation Learning", *ACM CSUR* 56(1) | Survey bridging network science and KG embedding communities | [Crossref](https://doi.org/10.1145/3605776) |
| 2023 (Oct) | Galkin et al., ULTRA, "Towards Foundation Models for Knowledge Graph Reasoning" (ICLR 2024); Goertzel et al., "OpenCog Hyperon" framework paper | Zero-shot KG reasoning across vocabularies; metagraph-based AGI substrate | [arXiv 2310.04562](https://arxiv.org/abs/2310.04562); [arXiv 2310.18318](https://arxiv.org/abs/2310.18318) |

## 2024–2026: standards land, LLM era, foundation models

| Year | Event | Why it matters | Source |
|---|---|---|---|
| 2024 (Jan–Feb) | Lee, Bu, Eliassi-Rad, Shin, hypergraph mining survey (*ACM CSUR*); TopoX suite (arXiv Feb 2024; *JMLR* 25); Huang, Romero Orth, Barceló, Bronstein, Ceylan, "Link Prediction with Relational Hypergraphs"; Papamarkou et al., "Position: Topological Deep Learning is the New Frontier for Relational Learning" (ICML 2024) | Topological deep learning and expressivity theory reach hypergraphs | [arXiv 2401.08878](https://arxiv.org/abs/2401.08878); [JMLR TopoX](https://jmlr.org/papers/v25/24-0110.html); [arXiv 2402.04062](https://arxiv.org/abs/2402.04062); [arXiv 2402.08871](https://arxiv.org/abs/2402.08871) |
| 2024 (Mar 9) | HyperNetX paper, *JOSS* 9(95):6016 | Peer-reviewed release of HyperNetX | [JOSS](https://joss.theoj.org/papers/10.21105/joss.06016) |
| 2024 (Apr 1) | Kim, Lee, Gao, Antelmi, Polato, Shin, "A Survey on Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide", KDD 2024 | HGNN taxonomy for the data-mining community | [arXiv 2404.01039](https://arxiv.org/abs/2404.01039) |
| 2024 (Apr 12) | ISO/IEC 39075:2024 GQL published | First ISO graph query language; property-graph model without n-ary relationships | [ISO](https://www.iso.org/standard/76120.html); [Wikipedia, GQL](https://en.wikipedia.org/wiki/Graph_Query_Language) |
| 2024 (Apr 24) | Edge et al. (Microsoft), "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" | GraphRAG: LLM-built KGs for retrieval; the template hypergraph RAG extends | [arXiv 2404.16130](https://arxiv.org/abs/2404.16130) |
| 2024 (Nov 9) | Liu et al., TransEQ, "Generalizing Hyperedge Expansion for Hyper-relational KG Modeling" | Principled HKG→KG expansions | [arXiv 2411.06191](https://arxiv.org/abs/2411.06191) |
| 2024 (Dec 20) | TypeDB 3.0 (Rust rewrite) | Hyper-relational database matures | [Wikipedia, TypeDB](https://en.wikipedia.org/wiki/TypeDB) |
| 2025 (Mar 3) | Gao, Feng et al., "Hypergraph Foundation Model" (Hyper-FM); 11 text-attributed hypergraph datasets; first "scaling law" claim for hypergraph FMs | Foundation-model framing reaches hypergraphs | [arXiv 2503.01203](https://arxiv.org/abs/2503.01203) |
| 2025 (Mar 27) | Luo et al., HyperGraphRAG (NeurIPS 2025) | First RAG pipeline built on an LLM-extracted **knowledge hypergraph** (n-ary facts as hyperedges) | [arXiv 2503.21322](https://arxiv.org/abs/2503.21322) |
| 2025 (Mar 30) | Feng, Gao et al., Hyper-RAG (arXiv 2504.08758; *Nature Communications* 17, 27 Apr 2026) | Hypergraph RAG against hallucination; published in a general-science venue | [arXiv 2504.08758](https://arxiv.org/abs/2504.08758); [Crossref](https://api.crossref.org/works/10.1038/s41467-026-71411-1) |
| 2025 (Apr 23) | Tsang, Wang, Song, "Transformers for Complex Query Answering over Knowledge Hypergraphs" | Logical CQA moves to KHGs | [arXiv 2504.16537](https://arxiv.org/abs/2504.16537) |
| 2025 (May 17) | Un, Lu, Yang, Yang, VITA, temporal hyper-relational KGs | Time-validity types on n-ary facts | [arXiv 2505.11803](https://arxiv.org/abs/2505.11803) |
| 2025 (Jun 6) | Xiang et al., GraphRAG-Bench, "When to use Graphs in RAG" (ICLR 2026) | Shows GraphRAG often loses to vanilla RAG; sets evaluation expectations | [arXiv 2506.05690](https://arxiv.org/abs/2506.05690); [GitHub](https://github.com/GraphRAG-Bench/GraphRAG-Benchmark) |
| 2025 (Jun) | Wei, Guan et al., "A Survey of Link Prediction in N-ary Knowledge Graphs"; Huang, Galkin, Bronstein, Ceylan, HYPER foundation model for inductive KHG link prediction | Field-level synthesis; transfer across arities | [arXiv 2506.08970](https://arxiv.org/abs/2506.08970); [arXiv 2506.12362](https://arxiv.org/abs/2506.12362) |
| 2025 (Jul 15) | HIF, "The hypergraph interchange format for higher-order networks" (arXiv; *Network Science* 13:e21, online 11 Dec 2025) | JSON interchange standard agreed by HyperNetX, XGI, Hypergraphx, SimpleHypergraphs.jl maintainers | [arXiv 2507.11520](https://arxiv.org/abs/2507.11520); [Cambridge Core](https://doi.org/10.1017/nws.2025.10018) |
| 2025 (Aug 5) | Wang et al., "Understanding the Embedding Models on Hyper-relational Knowledge Graph", CIKM 2025 | Shows plain KGE on decomposed HKGs matches specialised HKGE models: benchmark and method critique | [arXiv 2508.03280](https://arxiv.org/abs/2508.03280) |
| 2025 (Oct 14) | Zai et al., PRoH (WWW 2026) | Planning-and-reasoning agent over KHGs; +19.7% F1 over HyperGraphRAG | [arXiv 2510.12434](https://arxiv.org/abs/2510.12434) |
| 2026 (Feb 5) | Yu, Lu, Yang, THOR, fully inductive link prediction over HKGs | Inductive HKG completion across 12 datasets | [arXiv 2602.05424](https://arxiv.org/abs/2602.05424) |
| 2026 (Feb 16–23) | HyperRAG (n-ary reasoning retrieval); Hyper-KGGen with HyperDocRED benchmark | Retrieval that reasons over hyperedges; document-level KHG extraction benchmark | [arXiv 2602.14470](https://arxiv.org/abs/2602.14470); [arXiv 2602.19543](https://arxiv.org/abs/2602.19543) |
| 2026 (Apr 7) | RDF 1.2 Concepts and RDF 1.2 Semantics published as W3C Candidate Recommendation Snapshots (triple terms, reifiers, `rdf:reifies`); syntaxes and SPARQL 1.2 still Working Drafts as of Sept 2026 | The RDF answer to qualifiers becomes near-final | [RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/); [WG publications](https://www.w3.org/groups/wg/rdf-star/publications/) |
| 2026 (Apr–May) | HyperGVL benchmark for vision-language models on hypergraphs; "The WidthWall" strict expressivity hierarchy for HGNNs; "Hypergraph as Language" (Hyper-Align) tokenising hypergraphs for LLMs; Hypergraphx-data repository | Multimodal, theoretical and data infrastructure fronts open simultaneously | [arXiv 2604.15648](https://arxiv.org/abs/2604.15648); [arXiv 2605.13690](https://arxiv.org/abs/2605.13690); [arXiv 2605.21858](https://arxiv.org/abs/2605.21858); [arXiv 2605.18166](https://arxiv.org/abs/2605.18166) |
| 2026 (Jun–Aug) | DocTrace on-demand hypergraph working memory; EvoGraph-R1 self-evolving multimodal KHGs (CVPR 2026); HyperSkill hypergraph skill memory for agents | Hypergraphs move into **agent memory** | [arXiv 2606.10921](https://arxiv.org/abs/2606.10921); [arXiv 2607.12764](https://arxiv.org/abs/2607.12764); [arXiv 2608.16114](https://arxiv.org/abs/2608.16114) |
| 2026 (Nov 20–22, planned) | LoG 2026 (Boston), fifth Learning on Graphs conference; NetSci 2026 20th anniversary with a higher-order hackathon (31 May 2026) | Community venues where hypergraph work now concentrates | [LoG](https://logconference.org/); [Chodrow, hackathon page](https://www.philchodrow.prof/higher-order-hackathon/) |

## Reading the timeline

Three shapes stand out and are developed in the narrative notes:

1. **The n-ary idea recurs every decade and is flattened every decade.** Frames (1974), conceptual graphs (1976), Cyc (1984), Freebase CVTs (2007), Wikidata qualifiers (2012) each represented facts with more than two participants, and each time the dominant exchange format (RDF triples, property graphs) forced a reification pattern. See [knowledge-representation-lineage.md](knowledge-representation-lineage.md).
2. **Three separate communities converged around 2019–2021**: KG embedding (m-TransH → NaLP → HINGE/StarE → Fatemi et al.), hypergraph ML (Zhou 2006 → HGNN 2019 → TDL), and higher-order network science (Benson 2018 → Battiston 2020 → XGI/HyperNetX/HIF). See [machine-learning-era.md](machine-learning-era.md).
3. **From 2024 LLMs changed who builds the hypergraph.** GraphRAG (Apr 2024) → HyperGraphRAG and Hyper-RAG (Mar 2025) → planning agents and agent memory (2026). See [llm-era-2023-2026.md](llm-era-2023-2026.md).

## Sources

All sources in this file are listed, with full bibliographic detail, in [sources/by-topic/08-history-and-frontier.md](../../sources/by-topic/08-history-and-frontier.md). Key primary sources cited above:

- Berge, C. *Graphes et hypergraphes*. Dunod, 1970; *Graphs and Hypergraphs*, North-Holland, 1973. https://archive.org/details/graphshypergraph0000berg
- Quillian, M. R. "Semantic Memory." In Minsky (ed.), *Semantic Information Processing*, MIT Press, 1968. https://philpapers.org/rec/QUISN
- Minsky, M. "A Framework for Representing Knowledge." MIT AI Memo 306, 1974. https://dspace.mit.edu/entities/publication/0eca0164-cb5f-42de-8c86-43f54b23306d
- Sowa, J. F. "Conceptual Graphs for a Data Base Interface." *IBM J. Res. Dev.* 20(4), 1976. https://doi.org/10.1147/rd.204.0336
- Beeri, C., Fagin, R., Maier, D., Yannakakis, M. "On the Desirability of Acyclic Database Schemes." *JACM* 30(3), 1983. https://doi.org/10.1145/2402.322389
- Fagin, R. "Degrees of Acyclicity for Hypergraphs and Relational Database Schemes." *JACM* 30(3), 1983. https://dl.acm.org/doi/10.1145/2402.322390
- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. "Directed hypergraphs and applications." *Discrete Applied Mathematics* 42, 1993. https://dl.acm.org/citation.cfm?id=153586
- Gottlob, G., Leone, N., Scarcello, F. "Hypertree Decompositions and Tractable Queries." *JCSS* 64(3), 2002. https://arxiv.org/abs/cs/9812022
- Karypis, G., Aggarwal, R., Kumar, V., Shekhar, S. "Multilevel hypergraph partitioning: applications in VLSI domain." *IEEE TVLSI* 7(1), 1999. https://doi.org/10.1109/92.748202
- Çatalyürek, U. V., Aykanat, C. "Hypergraph-partitioning-based decomposition for parallel sparse-matrix vector multiplication." *IEEE TPDS* 10(7), 1999. https://doi.org/10.1109/71.780863
- W3C. RDF Model and Syntax Specification, Recommendation, 22 Feb 1999. https://www.w3.org/TR/1999/REC-rdf-syntax-19990222/
- W3C. RDF Concepts and Abstract Syntax, Recommendation, 10 Feb 2004. https://www.w3.org/TR/2004/REC-rdf-concepts-20040210/
- W3C. OWL Web Ontology Language Reference, Recommendation, 10 Feb 2004. https://www.w3.org/TR/owl-ref/
- Noy, N., Rector, A. (eds.). "Defining N-ary Relations on the Semantic Web." W3C Working Group Note, 12 Apr 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- Zhou, D., Huang, J., Schölkopf, B. "Learning with Hypergraphs." NIPS 19, 2006. https://papers.nips.cc/paper/3128-learning-with-hypergraphs-clustering-classification-and-embedding
- Wikipedia. "Freebase (database)". https://en.wikipedia.org/wiki/Freebase_(database)
- Houle, P. "Compound Value Types in RDF." https://database_animals.silvrback.com/compound-value-types-in-rdf
- Iordanov, B. "HyperGraphDB: A Generalized Graph Database." WAIM 2010 Workshops, LNCS. https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3
- Google. "Introducing the Knowledge Graph: things, not strings." 16 May 2012. https://blog.google/products-and-platforms/products/search/introducing-knowledge-graph-things-not/
- Wikipedia. "Wikidata". https://en.wikipedia.org/wiki/Wikidata
- Vrandečić, D., Krötzsch, M. "Wikidata: a free collaborative knowledgebase." *CACM* 57(10), 2014. https://doi.org/10.1145/2629489
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases Beyond Binary Relations." IJCAI 2016. https://arxiv.org/abs/1604.08642
- Wikipedia. "TypeDB". https://en.wikipedia.org/wiki/TypeDB ; Database of Databases, "TypeDB". https://dbdb.io/db/typedb
- Benson, A. R. et al. "Simplicial closure and higher-order link prediction." *PNAS* 115(48), 2018. https://arxiv.org/abs/1802.06916
- Feng, Y. et al. "Hypergraph Neural Networks." AAAI 2019. https://arxiv.org/abs/1809.09401
- OSTI DOE CODE. "pnnl/HyperNetX", released 3 Jan 2019. https://www.osti.gov/doecode/biblio/22160
- Guan, S. et al. "Link Prediction on N-ary Relational Data." WWW 2019. https://dblp.org/rec/conf/www/GuanJWC19.html
- Fatemi, B. et al. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." IJCAI 2020. https://arxiv.org/abs/1906.00137
- Rosso, P., Yang, D., Cudré-Mauroux, P. "Beyond Triplets." WWW 2020. https://dl.acm.org/doi/fullHtml/10.1145/3366423.3380257
- Joslyn, C. A. et al. "Hypernetwork Science." arXiv 2020. https://arxiv.org/abs/2003.11782
- Battiston, F. et al. "Networks beyond pairwise interactions." *Physics Reports* 874, 2020. https://research.ceu.edu/en/publications/networks-beyond-pairwise-interactions-structure-and-dynamics/
- Galkin, M. et al. "Message Passing for Hyper-Relational Knowledge Graphs." EMNLP 2020. https://aclanthology.org/2020.emnlp-main.596/
- Gao, Y. et al. "Hypergraph Learning: Methods and Practices." *IEEE TPAMI*. https://doi.org/10.1109/TPAMI.2020.3039374
- Fatemi, B. et al. "Knowledge Hypergraph Embedding Meets Relational Algebra." arXiv 2021. https://arxiv.org/abs/2102.09557
- Bick, C. et al. "What are higher-order networks?" *SIAM Review* 65(3), 2023. https://arxiv.org/abs/2104.11329
- Ali, M. et al. "Improving Inductive Link Prediction Using Hyper-Relational Facts." ISWC 2021. https://arxiv.org/abs/2107.04894
- Schloss Dagstuhl. Seminar 21352. https://www.dagstuhl.de/seminars/seminar-calendar/seminar-details/21352
- Battiston, F. et al. "The physics of higher-order interactions in complex systems." *Nature Physics* 17, 2021. https://arxiv.org/abs/2110.06023
- PyPI. "xgi" release history. https://pypi.org/project/xgi/#history
- Goertzel, B. "Reflective Metagraph Rewriting." arXiv 2021. https://arxiv.org/abs/2112.08272
- Hartig, O. et al. (eds.). "RDF-star and SPARQL-star." W3C Final Community Group Report, 17 Dec 2021. https://w3c-cg.github.io/rdf-star/cg-spec/2021-12-17.html
- iMoonLab. DeepHypergraph (DHG). https://github.com/iMoonLab/DeepHypergraph
- W3C. RDF-star Working Group Charter, 2022. https://www.w3.org/2022/08/rdf-star-wg-charter/ ; Proposed charter 2024. https://www.w3.org/2024/08/proposed-rdf-star-wg-charter.html
- Gao, Y., Feng, Y., Ji, S., Ji, R. "HGNN+." *IEEE TPAMI* 45(3), 2023. https://doi.org/10.1109/TPAMI.2022.3182052
- Lotito, Q. F. et al. "Hypergraphx." *J. Complex Networks* 11(3), 2023. https://arxiv.org/abs/2303.15356
- Landry, N. W. et al. "XGI." *JOSS* 8(85), 2023. https://joss.theoj.org/papers/10.21105/joss.05162
- Wikipedia. "SQL:2023". https://en.wikipedia.org/wiki/SQL:2023 ; ISO/IEC 9075-16:2023. https://www.iso.org/standard/79473.html
- Antelmi, A. et al. "A Survey on Hypergraph Representation Learning." *ACM CSUR* 56(1), 2023. https://doi.org/10.1145/3605776
- Galkin, M. et al. "Towards Foundation Models for Knowledge Graph Reasoning." ICLR 2024. https://arxiv.org/abs/2310.04562
- Goertzel, B. et al. "OpenCog Hyperon: A Framework for AGI at the Human Level and Beyond." arXiv 2023. https://arxiv.org/abs/2310.18318
- Lee, G., Bu, F., Eliassi-Rad, T., Shin, K. "A Survey on Hypergraph Mining." *ACM CSUR*. https://arxiv.org/abs/2401.08878
- Hajij, M. et al. "TopoX." *JMLR* 25, 2024. https://jmlr.org/papers/v25/24-0110.html
- Huang, X. et al. "Link Prediction with Relational Hypergraphs." arXiv 2024. https://arxiv.org/abs/2402.04062
- Papamarkou, T. et al. "Position: Topological Deep Learning is the New Frontier for Relational Learning." ICML 2024. https://arxiv.org/abs/2402.08871
- Praggastis, B. et al. "HyperNetX." *JOSS* 9(95), 2024. https://joss.theoj.org/papers/10.21105/joss.06016
- Kim, S. et al. "A Survey on Hypergraph Neural Networks." KDD 2024. https://arxiv.org/abs/2404.01039
- ISO/IEC 39075:2024 GQL. https://www.iso.org/standard/76120.html ; Wikipedia, "Graph Query Language". https://en.wikipedia.org/wiki/Graph_Query_Language
- Edge, D. et al. "From Local to Global: A Graph RAG Approach to Query-Focused Summarization." arXiv 2024. https://arxiv.org/abs/2404.16130
- Liu, Y. et al. "Generalizing Hyperedge Expansion for Hyper-relational Knowledge Graph Modeling." arXiv 2024. https://arxiv.org/abs/2411.06191
- Gao, Y., Feng, Y. et al. "Hypergraph Foundation Model." arXiv 2025. https://arxiv.org/abs/2503.01203
- Luo, H. et al. "HyperGraphRAG." NeurIPS 2025. https://arxiv.org/abs/2503.21322
- Feng, Y. et al. "Hyper-RAG." arXiv 2025; *Nature Communications* 17, 2026. https://arxiv.org/abs/2504.08758 ; https://api.crossref.org/works/10.1038/s41467-026-71411-1
- Tsang, H. T., Wang, Z., Song, Y. "Transformers for Complex Query Answering over Knowledge Hypergraphs." arXiv 2025. https://arxiv.org/abs/2504.16537
- Un, C., Lu, Y., Yang, T., Yang, D. "VITA." arXiv 2025. https://arxiv.org/abs/2505.11803
- Xiang, Z. et al. "When to use Graphs in RAG." ICLR 2026. https://arxiv.org/abs/2506.05690
- Wei, J., Guan, S. et al. "A Survey of Link Prediction in N-ary Knowledge Graphs." arXiv 2025. https://arxiv.org/abs/2506.08970
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. "HYPER." arXiv 2025. https://arxiv.org/abs/2506.12362
- Coll, M. et al. "HIF: The hypergraph interchange format for higher-order networks." *Network Science* 13, 2025. https://doi.org/10.1017/nws.2025.10018 ; https://arxiv.org/abs/2507.11520
- Wang, Y. et al. "Understanding the Embedding Models on Hyper-relational Knowledge Graph." CIKM 2025. https://arxiv.org/abs/2508.03280
- Zai, X. et al. "PRoH." WWW 2026. https://arxiv.org/abs/2510.12434
- Yu, W., Lu, Y., Yang, D. "THOR." arXiv 2026. https://arxiv.org/abs/2602.05424
- "HyperRAG: Reasoning N-ary Facts over Hypergraphs for RAG." arXiv 2026. https://arxiv.org/abs/2602.14470
- Huang, R. et al. "Hyper-KGGen." arXiv 2026. https://arxiv.org/abs/2602.19543
- W3C. RDF 1.2 Concepts and Abstract Data Model, CR Snapshot 7 Apr 2026. https://www.w3.org/TR/rdf12-concepts/ ; WG publications list. https://www.w3.org/groups/wg/rdf-star/publications/
- Wei, Y. et al. "HyperGVL." arXiv 2026. https://arxiv.org/abs/2604.15648
- "The WidthWall: A Strict Expressivity Hierarchy for Hypergraph Neural Networks." arXiv 2026. https://arxiv.org/abs/2605.13690
- Lei, M. et al. "Hypergraph as Language." arXiv 2026. https://arxiv.org/abs/2605.21858
- Lotito, Q. F. et al. "Hypergraphx-data." arXiv 2026. https://arxiv.org/abs/2605.18166
- Zai, X. et al. "Trace Only What You Need" (DocTrace). arXiv 2026. https://arxiv.org/abs/2606.10921
- Lin, J. et al. "EvoGraph-R1." CVPR 2026. https://arxiv.org/abs/2607.12764
- Xu, R., Yang, T., Huang, W.-C. "HyperSkill." arXiv 2026. https://arxiv.org/abs/2608.16114
- Learning on Graphs Conference. https://logconference.org/ ; Chodrow, P. "A Higher Order Hackathon." https://www.philchodrow.prof/higher-order-hackathon/
