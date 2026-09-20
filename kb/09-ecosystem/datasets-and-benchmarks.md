---
title: Datasets and benchmarks for knowledge hypergraphs and higher-order networks
type: dataset
status: draft
tags: [ecosystem, datasets, benchmarks, n-ary, hyper-relational, JF17K, WikiPeople, WD50K, XGI-DATA, hypergraph-learning]
created: 2026-09-20
updated: 2026-09-20
---

# Datasets and benchmarks

Every number below is attributed to the specific publication or catalogue that reports it, and
every figure was **checked on 2026-09-20**. This matters more than usual here: the same dataset
name is reported with different statistics in different papers, which is the subject of
[dataset-quality-and-leakage-issues.md](dataset-quality-and-leakage-issues.md). Where two
sources disagree, both numbers appear.

The field has four largely separate benchmark traditions:

| Tradition | Unit of data | Typical task | Representative benchmark |
|---|---|---|---|
| **Hyper-relational / n-ary KG** | statement = base triple + qualifiers, or role-indexed tuple | link prediction (entity, relation) | JF17K, WikiPeople, WD50K |
| **Hypergraph learning** | set of vertices, vertices carry features | node classification, hyperedge prediction | Cora/Citeseer/Pubmed co-citation, Walmart, House |
| **Empirical higher-order networks** | timestamped sets of interacting entities | structure, dynamics, higher-order link prediction | Benson's collection, XGI-DATA, hypergraphx-data |
| **Hypergraph RAG** | LLM-extracted n-ary facts over a text corpus | question answering | HyperGraphRAG / Hyper-RAG domain corpora |

---

## 1. Hyper-relational and n-ary knowledge-graph benchmarks

### 1.1 The main three

| Dataset | Source KG | #Entities | #Relations | #Facts | Arity | % n-ary (arity > 2) | Reported by |
|---|---|---|---|---|---|---|---|
| **JF17K** | Freebase | 28,645 | 501 | 100,947 | 2–6 | 45.9% | [Wei et al., 2025, Table 1](https://arxiv.org/abs/2506.08970) |
| JF17K (same name, other counts) | Freebase | 28,645 | 322 | 76,379 train + 24,568 test | — | 42.2% of train facts | [Rosso, Yang, Cudré-Mauroux, 2020, Table 1](https://doi.org/10.1145/3366423.3380257) |
| JF17K (same name, other counts) | Freebase | 29,177 | 327 | 77,733 train + 24,915 test, **no official validation set** | 2–6 | arity 2: 56,322; 3: 34,550; 4: 9,509; 5: 2,230; 6: 37 | [Fatemi et al., 2020](https://doi.org/10.24963/ijcai.2020/303) |
| **WikiPeople** | Wikidata | 47,765 | 193 | 382,229 | 2–9 | 11.6% | [Wei et al., 2025, Table 1](https://arxiv.org/abs/2506.08970) |
| WikiPeople (same name, other counts) | Wikidata | 34,839 | 375 | 287,918 train + 37,586 test | — | **2.6%** of train facts | [Rosso et al., 2020, Table 1](https://doi.org/10.1145/3366423.3380257) |
| **WD50K** | Wikidata | 47,156 | 532 | 236,507 statements (166,435 / 23,913 / 46,159 train/valid/test) | 2–67 | 13.6% carry qualifiers | [Galkin et al., 2020, Table 1](https://doi.org/10.18653/v1/2020.emnlp-main.596) |

JF17K originates with [Wen et al., IJCAI 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)
(m-TransH); WikiPeople with [Guan et al., WWW 2019](https://doi.org/10.1145/3308558.3313414)
(NaLP); WD50K with the StarE paper.

### 1.2 The WD50K family

Built from Wikidata by seeding on entities that have a Freebase ID (`P646`) mapping from
FB15K-237, then keeping statements whose object and qualifier values are `wikibase:Item`
([Galkin et al., 2020](https://doi.org/10.18653/v1/2020.emnlp-main.596)).

| Variant | Statements | With qualifiers | #Entities | #Relations | Entities in quals | Relations in quals | Train / Valid / Test |
|---|---|---|---|---|---|---|---|
| WD50K | 236,507 | 32,167 (13.6%) | 47,156 | 532 | 5,460 | 45 | 166,435 / 23,913 / 46,159 |
| WD50K (33) | 102,107 | 31,866 (31.2%) | 38,124 | 475 | 6,463 | 47 | 73,406 / 10,568 / 18,133 |
| WD50K (66) | 49,167 | 31,696 (64.5%) | 27,347 | 494 | 7,167 | 53 | 35,968 / 5,154 / 8,045 |
| WD50K (100) | 31,314 | 31,314 (100%) | 18,792 | 279 | 7,862 | 75 | 22,738 / 3,279 / 5,297 |

*Task:* statement-level link prediction (predict the object of the main triple given the
qualifiers, or predict a qualifier value). *Licence:* derived from Wikidata, which is CC0-1.0;
the repository distributing the splits ([migalkin/StarE](https://github.com/migalkin/StarE)) is
MIT. *URL:* <https://github.com/migalkin/StarE>

### 1.3 Knowledge-hypergraph (role-indexed tuple) benchmarks

Introduced by [Fatemi, Taslakian, Vazquez, Poole, IJCAI 2020](https://doi.org/10.24963/ijcai.2020/303),
both derived from Freebase by "inverse reification": drop single-entity and numeric-entity facts,
then join triples that share a subject and relation, combining entities by role.

| Dataset | #Entities | #Relations | Train | Valid | Test | Arity distribution |
|---|---|---|---|---|---|---|
| **FB-AUTO** | 3,410 | 8 | 6,778 | 2,255 | 2,180 | arity 2: 3,786; 4: 215; 5: 7,212 |
| **M-FB15K** | 10,314 | 71 | 415,375 | 39,348 | 38,797 | arity 2: 82,247; 3: 400,027; 4: 26; 5: 11,220 |

FB-AUTO is the subset whose relations start with `automotive`; M-FB15K restricts to entities in
the Wikilinks database, following the FB15K construction strategy. *Licence:* the shipping
repositories ([ServiceNow/HypE](https://github.com/ServiceNow/HypE),
[baharefatemi/HypE](https://github.com/baharefatemi/HypE)) declare **no licence file**;
underlying Freebase data was CC-BY.

### 1.4 Filtered and arity-restricted variants

Shipped with the GRAN implementation
([PaddlePaddle/Research › KG/ACL2021_GRAN](https://github.com/PaddlePaddle/Research/tree/master/KG/ACL2021_GRAN),
Apache-2.0, checked 2026-09-20):

| Variant | Meaning |
|---|---|
| **JF17K-3**, **JF17K-4** | only the 3-ary, resp. 4-ary, facts of JF17K |
| **WikiPeople-** | WikiPeople with statements containing literals removed |
| **WikiPeople-3**, **WikiPeople-4** | only the 3-ary, resp. 4-ary, facts |

`[unverified]` The exact fact counts of these variants are not reported in any source checked
here; they must be read off the shipped files.

### 1.5 Temporal and numeric n-ary benchmarks

From the temporal table of [Wei et al., 2025](https://arxiv.org/abs/2506.08970):

| Dataset | #Entities | #Timestamps | Time granularity | % n-ary | Train / Valid / Test |
|---|---|---|---|---|---|
| NWIKI | 17,481 | 205 | 1 year | 81.9% | 108,397 / 14,370 / 15,591 |
| NICE | 10,860 | 4,017 | 24 hours | 97.5% | 368,868 / 5,268 / 46,159 |
| Wiki-hy | 11,140 | 507 | 1 year | 9.5% | 111,252 / 13,900 / 13,926 |
| YAGO-hy | 10,026 | 188 | 1 year | 6.9% | 51,193 / 10,973 / 10,977 |

Note on naming: **HyNT** ([Chung, Lee, Whang, KDD 2023](https://doi.org/10.1145/3580305.3599490))
is a *hyper-relational and **numeric*** model, not a temporal one; its datasets add numeric
literals in qualifier positions. Datasets at
[bdi-lab/HyNT](https://github.com/bdi-lab/HyNT) (licence: GitHub metadata "Other").
`[unverified]` per-dataset counts for the HyNT releases.

### 1.6 Inductive benchmarks: WD20K

Introduced by [Ali et al., ISWC 2021](https://doi.org/10.1007/978-3-030-88361-4_5)
(extended abstract: [IJCAI 2022](https://doi.org/10.24963/ijcai.2022/731)). Statistics as
reported by [Wei et al., 2025, Table 8](https://arxiv.org/abs/2506.08970):

| Variant | Train facts | Train % n-ary | Test facts | Test % n-ary | Inference graph |
|---|---|---|---|---|---|
| WD20K(25) | 39,819 | 30.0% | 3,453 | 22.0% | none (transductive-style split) |
| WD20K(100) V1 | 7,785 | 100.0% | 364 | 100.0% | 2,667 |

---

## 2. Hypergraph-learning benchmarks (node classification)

The de-facto standard suite, as tabulated by
[Chien, Pan, Peng, Milenkovic, ICLR 2022 (AllSet), Table 1](https://arxiv.org/abs/2106.13264):

| Dataset | Nodes | Hyperedges | Features | Classes | Max hyperedge size | Origin |
|---|---|---|---|---|---|---|
| Cora (co-citation) | 2,708 | 1,579 | 1,433 | 7 | 5 | citation network, hyperedge = papers co-cited by one paper |
| Citeseer (co-citation) | 3,312 | 1,079 | 3,703 | 6 | 26 | idem |
| Pubmed (co-citation) | 19,717 | 7,963 | 500 | 3 | 171 | idem |
| Cora-CA (co-authorship) | 2,708 | 1,072 | 1,433 | 7 | 43 | hyperedge = papers by one author |
| DBLP-CA (co-authorship) | 41,302 | 22,363 | 1,425 | 6 | 202 | idem |
| Zoo | 101 | 43 | 16 | 7 | 93 | UCI tabular → hyperedge per categorical value |
| 20Newsgroups | 16,242 | 100 | 100 | 4 | 2,241 | text |
| Mushroom | 8,124 | 298 | 22 | 2 | 1,808 | UCI tabular |
| NTU2012 | 2,012 | 2,012 | 100 | 67 | 5 | 3-D shapes, k-NN hyperedges |
| ModelNet40 | 12,311 | 12,311 | 100 | 40 | 5 | 3-D shapes, k-NN hyperedges |
| **Yelp** | 50,758 | 679,302 | 1,862 | 9 | 2,838 | nodes = restaurants, hyperedge = restaurants visited by one user |
| **House** | 1,290 | 341 | 100 (Gaussian random) | 2 | 81 | nodes = members of the US House, hyperedge = a committee |
| **Walmart** | 88,860 | 69,906 | 100 (Gaussian random) | 11 | 25 | nodes = products, hyperedge = a basket |

Two of these (House, Walmart) have **no real node features**; AllSet substitutes Gaussian random
vectors. The Cora/Citeseer/Pubmed co-citation splits trace back to
[Yadati et al., HyperGCN, NeurIPS 2019](https://papers.nips.cc/paper/2019/hash/1efa39bcaec6f3900149160693694536-Abstract.html).
*Trivago* (a click-session hypergraph) is used in several later papers; `[unverified]` its
statistics were not confirmed from a primary source in this run.

---

## 3. Empirical higher-order network collections

### 3.1 Austin Benson's "Data!" collection

<https://www.cs.cornell.edu/~arb/data/> — the origin of most temporal higher-order datasets.
Categories (verified from the index page, 2026-09-20): temporal higher-order networks
(`coauth-DBLP`, `coauth-MAG-Geology`, `coauth-MAG-History`, `tags-stack-overflow`,
`tags-math-sx`, `tags-ask-ubuntu`, `threads-*`, `NDC-substances`, `NDC-classes`, `DAWN`,
`congress-bills`, `email-Eu`, `email-Enron`) and hypergraphs with labelled nodes
(`stackoverflow-answers`, `walmart-trips`, `amazon-reviews`, `senate-bills`, …). The requested
citation is [Benson, Abebe, Schaub, Jadbabaie, Kleinberg, PNAS 2018](https://doi.org/10.1073/pnas.1800683115).
Per-dataset counts are on the individual dataset pages, not the index.

### 3.2 XGI-DATA

51 datasets in the index (`https://raw.githubusercontent.com/xgi-org/xgi-data/main/index.json`,
checked 2026-09-20), hosted as Zenodo records in the
[XGI community](https://zenodo.org/communities/xgi), distributed both as HIF-compliant JSON and
XGI JSON, loaded with `xgi.load_xgi_data("<name>")`. The index carries full statistics.

| Dataset | \|V\| | \|E\| | unique \|E\| | max edge size | mean edge size |
|---|---|---|---|---|---|
| email-enron | 148 | 10,885 | 1,514 | 37 | 2.47 |
| email-eu | 1,005 | 235,263 | 25,148 | 40 | 2.39 |
| contact-primary-school | 242 | 106,879 | 12,704 | 5 | 2.10 |
| contact-high-school | 327 | 172,035 | 7,818 | 5 | 2.05 |
| coauth-dblp | 1,930,378 | 3,700,681 | 2,467,389 | 280 | 2.79 |
| tags-math-sx | 1,629 | 822,059 | 170,476 | 5 | 2.19 |
| congress-bills | 1,718 | 282,049 | 105,733 | 400 | 8.66 |
| house-committees | 1,290 | 341 | 336 | 81 | 34.73 |
| senate-bills | 294 | 29,157 | 21,721 | 99 | 7.96 |
| diseasome | 516 | 903 | 481 | 11 | 1.72 |
| arxiv-kaggle | 1,821,977 | 2,765,236 | 1,986,653 | 2,811 | 4.61 |

Note that \|E\| counts *timestamped occurrences*; \|E\*\| counts distinct vertex sets. The mean
edge size of the contact and e-mail datasets is close to 2, i.e. these "hypergraph" datasets are
mostly pairwise — relevant to
[../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md).
Full catalogue: <https://github.com/xgi-org/xgi-data>. `[unverified]` per-dataset licences; the
xgi-data repository itself carries GitHub licence metadata "Other".

### 3.3 hypergraphx-data

<https://hgx-team.github.io/hypergraphx-data/> — **136 datasets** in the live catalogue
(obtained programmatically via `hypergraphx.readwrite.list_remote_datasets()` with
hypergraphx 1.8.0, 2026-09-20), tagged by type (Undirected / Directed / Temporal / Weighted /
Multiplex) and domain (Biology, Social, Authorship, Technology, Finance, Food, Culture,
Consumer behaviour, Discussion forum, Geopolitical).

| Dataset | \|V\| | \|E\| | tags |
|---|---|---|---|
| coauth-DBLP | 1,930,378 | 3,700,681 | Undirected, Temporal, Social, Authorship |
| amazon-reviews | 2,268,231 | 4,242,421 | Undirected, Consumer behaviour |
| stackoverflow-answers | 15,211,989 | 1,103,218 | Discussion forum, Undirected |
| tags-stack-overflow | 49,998 | 14,458,875 | Undirected, Temporal |
| tags-math-sx | 1,629 | 822,059 | Undirected, Temporal |
| email-Enron | 84,172 | 235,395 | **Directed**, Temporal, Social, Technology |
| email-Enron-core | 143 | 10,472 | Directed, Temporal, Social, Technology |
| email-EU | 1,005 | 209,508 | Undirected, Temporal, Social, Technology |
| contacts-primary-school | 242 | 106,879 | Undirected, Temporal, Social |
| contacts-high-school | 327 | 172,035 | Undirected, Temporal, Social |
| contacts-hospital | 75 | 27,835 | Undirected, Temporal, Social |
| congress-bills | 1,718 | 282,049 | Undirected, Temporal, Social |
| walmart-trips | 88,860 | 65,979 | Undirected, Consumer behaviour |
| NDC-substances | 5,556 | 112,919 | Undirected, Temporal, Weighted, Biology |
| DAWN | 2,558 | 2,272,433 | Undirected, Temporal, Weighted, Biology |

The same underlying datasets appear in both XGI-DATA and hypergraphx-data with **different
counts** (compare `email-Enron`: 148 nodes in XGI-DATA vs 84,172 in hypergraphx-data, which is
the full rather than the core network; `walmart-trips`: 65,979 vs AllSet's 69,906 hyperedges).
Always record which catalogue a number came from.

### 3.4 General network repositories

| Repository | Scope | Higher-order content | Licence / terms | URL | Checked |
|---|---|---|---|---|---|
| **SNAP** (Stanford Large Network Dataset Collection) | ~150+ network datasets | hosts a "Higher-order" project section; most datasets are pairwise graphs | no explicit licence statement on the index page; citation `@misc{snapnets}` requested | <https://snap.stanford.edu/data/> | 2026-09-20 |
| **KONECT** | network collection with unified statistics | `[unverified]` — <http://konect.cc/> returned **HTTP 503** when checked | — | <http://konect.cc/> | 2026-09-20 |

---

## 4. Hypergraph-RAG evaluation corpora

### 4.1 HyperGraphRAG

Five domains ([Luo et al., 2025, arXiv:2503.21322v3](https://arxiv.org/html/2503.21322v3)):

| Domain | Context source | Entities | Hyperedges |
|---|---|---|---|
| Medicine | "the latest international hypertension guidelines" | 7,675 | 4,818 |
| Agriculture | **UltraDomain** | 16,805 | 16,102 |
| Computer Science | **UltraDomain** | 19,913 | 26,902 |
| Legal | **UltraDomain** | 11,098 | 18,285 |
| Mix | combination of domains | 6,201 | 4,356 |

512 questions per domain: 256 "binary-source" (128×1-hop, 64×2-hop, 64×3-hop) and 256
"n-ary-source" (same split, over facts with n ≥ 3), all "manually verified". *Distribution:* the
repository's `evaluation/README.md` instructs users to "download the contexts and datasets from
Terabox" — a third-party file host, not an archival repository (checked 2026-09-20). *Code
licence:* MIT. *URL:* <https://github.com/LHRLAB/HyperGraphRAG>

### 4.2 Hyper-RAG

[Feng et al., Nature Communications 17, 5778 (2026)](https://doi.org/10.1038/s41467-026-71411-1).
The repository README names a **NeurologyCrop** dataset for the main experiment and "nine
diverse datasets" for the selection-based assessment, distributed via Google Drive and Baidu
Cloud. *Code licence:* Apache-2.0. `[unverified]` per-dataset sizes and provenance — neither the
README nor the repository ships a datasheet. *URL:* <https://github.com/iMoonLab/Hyper-RAG>

---

## 5. Large general knowledge bases used as n-ary sources

| Resource | Statement model | Size | Licence | URL | Checked |
|---|---|---|---|---|---|
| **Wikidata** dumps | Wikibase statements: main snak + **qualifiers** + references — a genuine n-ary record | full JSON dump, weekly | CC0-1.0 | <https://dumps.wikimedia.org/wikidatawiki/entities/> | `[unverified]` size/date not confirmed in this run |
| **Freebase** dumps | CVT (compound value type) nodes reify n-ary facts | final dump 2015, ~1.9 B triples `[unverified]` | CC-BY | <https://developers.google.com/freebase> | `[unverified]` |
| **YAGO 4.5** | schema.org-based taxonomy + **RDF-star "meta" facts** (facts about facts) | 49 million entities, 109 million facts | CC-BY-SA | <https://yago-knowledge.org/downloads/yago-4-5> | 2026-09-20 |
| **DBpedia** | binary triples extracted from Wikipedia infoboxes | `[unverified]` | CC-BY-SA | <https://www.dbpedia.org/> | `[unverified]` |
| **ConceptNet** | binary assertions (subject–relation–object), weighted; the site page names version **5.5** and lists 60+ languages | `[unverified]` edge count | CC-BY-SA 4.0 | <https://conceptnet.io/> | 2026-09-20 |
| **ATOMIC** | if–then commonsense inference tuples (event, relation, inference) — n-ary-ish but stored as triples | `[unverified]` | CC-BY | <https://allenai.org/data/atomic-2020> | `[unverified]` |

See [../02-knowledge-representation/wikidata-and-freebase-data-models.md](../02-knowledge-representation/wikidata-and-freebase-data-models.md)
for the data models themselves.

---

## 6. How to fetch these locally

Follow the manifest conventions in [../../datasets/README.md](../../datasets/README.md). No bulk
data is committed to this repository.

---

## Sources

- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. (2025). *A Survey of Link Prediction in N-ary Knowledge Graphs.* arXiv:2506.08970 (2025-06-10). <https://arxiv.org/abs/2506.08970>
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. (2020). *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020, 7346–7359. <https://doi.org/10.18653/v1/2020.emnlp-main.596> (WD50K statistics and construction).
- Rosso, P., Yang, D., Cudré-Mauroux, P. (2020). *Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction.* WWW 2020, 1885–1896. <https://doi.org/10.1145/3366423.3380257> (JF17K / WikiPeople statistics, Table 1).
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. (2020). *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020, 2191–2197. <https://doi.org/10.24963/ijcai.2020/303> (FB-AUTO, M-FB15K, JF17K arity distribution).
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. (2016). *On the Representation and Embedding of Knowledge Bases Beyond Binary Relations.* IJCAI 2016. <https://www.ijcai.org/Proceedings/16/Papers/188.pdf> (origin of JF17K).
- Guan, S., Jin, X., Wang, Y., Cheng, X. (2019). *Link Prediction on N-ary Relational Data.* WWW 2019, 583–593. <https://doi.org/10.1145/3308558.3313414> (origin of WikiPeople).
- Wang, Q., Wang, H., Lyu, Y., Zhu, Y. (2021). *Link Prediction on N-ary Relational Facts: A Graph-based Approach.* Findings of ACL-IJCNLP 2021, 396–407. <https://doi.org/10.18653/v1/2021.findings-acl.35>; code and JF17K-3/4, WikiPeople-/-3/-4 variants at <https://github.com/PaddlePaddle/Research/tree/master/KG/ACL2021_GRAN>.
- Ali, M., Berrendorf, M., Galkin, M., Thost, V., Ma, T., Tresp, V., Lehmann, J. (2021). *Improving Inductive Link Prediction Using Hyper-relational Facts.* ISWC 2021, LNCS. <https://doi.org/10.1007/978-3-030-88361-4_5> (WD20K).
- Chung, C., Lee, J., Whang, J. J. (2023). *Representation Learning on Hyper-Relational and Numeric Knowledge Graphs with Transformers.* KDD 2023, 310–322. <https://doi.org/10.1145/3580305.3599490> (HyNT).
- Chien, E., Pan, C., Peng, J., Milenkovic, O. (2022). *You are AllSet: A Multiset Function Framework for Hypergraph Neural Networks.* ICLR 2022; arXiv:2106.13264. <https://arxiv.org/abs/2106.13264> (Table 1 benchmark statistics; Yelp, House, Walmart).
- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. (2018). *Simplicial closure and higher-order link prediction.* PNAS 115(48). <https://doi.org/10.1073/pnas.1800683115>; data index <https://www.cs.cornell.edu/~arb/data/>.
- XGI-DATA index, <https://raw.githubusercontent.com/xgi-org/xgi-data/main/index.json> and <https://github.com/xgi-org/xgi-data>, retrieved 2026-09-20.
- hypergraphx-data catalogue, <https://hgx-team.github.io/hypergraphx-data/>, enumerated via `hypergraphx.readwrite.list_remote_datasets()` (hypergraphx 1.8.0) on 2026-09-20.
- Leskovec, J., Krevl, A. *SNAP Datasets: Stanford Large Network Dataset Collection.* <https://snap.stanford.edu/data/>, checked 2026-09-20.
- KONECT, <http://konect.cc/>, checked 2026-09-20 (HTTP 503).
- Luo, H., E, H., Chen, G. et al. (2025). *HyperGraphRAG.* arXiv:2503.21322v3. <https://arxiv.org/html/2503.21322v3>; evaluation instructions at <https://github.com/LHRLAB/HyperGraphRAG/blob/main/evaluation/README.md>, checked 2026-09-20.
- Feng, Y., Hu, H., Ying, S. et al. (2026). *Hyper-RAG.* Nature Communications 17, 5778. <https://doi.org/10.1038/s41467-026-71411-1>; repository <https://github.com/iMoonLab/Hyper-RAG>, checked 2026-09-20.
- YAGO 4.5 download page, <https://yago-knowledge.org/downloads/yago-4-5>, checked 2026-09-20.
- ConceptNet, <https://conceptnet.io/>, checked 2026-09-20.
