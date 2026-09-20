---
title: Dataset quality, leakage and provenance problems in knowledge-hypergraph benchmarks
type: survey
status: draft
tags: [ecosystem, datasets, benchmarks, evaluation, leakage, reproducibility, critique, JF17K, WikiPeople, WD50K]
created: 2026-09-20
updated: 2026-09-20
---

# Dataset quality, leakage and provenance problems

Anyone who reads a table of MRR scores on JF17K, WikiPeople or WD50K should read this note
first. The benchmarks that the n-ary / hyper-relational literature is built on have documented
defects, and the higher-order-network and hypergraph-RAG benchmarks have different but equally
real problems. Dataset statistics referenced here are tabulated in
[datasets-and-benchmarks.md](datasets-and-benchmarks.md).

Throughout, **established** means "stated in the cited primary source"; **analysis** marks an
inference drawn here from cited facts.

---

## 1. JF17K: a 44.5% test-set leak

**Established.** [Galkin, Trivedi, Maheshwari, Usbeck, Lehmann (EMNLP 2020)](https://doi.org/10.18653/v1/2020.emnlp-main.596)
report that in JF17K

> "about 44.5% of the test statements share the same main (s,r,o) triple as the train
> statements. We consider this fact as a major data leakage."

**Attribution correction.** This finding is often credited to the HINGE paper
([Rosso, Yang, Cudré-Mauroux, WWW 2020](https://doi.org/10.1145/3366423.3380257)). The full text
of that paper was searched on 2026-09-20 for the strings `leak` and `redundan`: **neither
occurs**. Rosso et al. do contribute the statistics that expose WikiPeople's thinness
(section 3 below), but the leakage result is Galkin et al.'s.

**Analysis.** A model that memorises `(s,r,o)` triples from training can answer nearly half of
JF17K's test statements without using any qualifier at all. Reported gains from
"hyper-relational modelling" on JF17K therefore cannot be separated from memorisation, and
absolute JF17K numbers across papers are not a meaningful ranking.

---

## 2. JF17K has no official validation split

**Established.** [Fatemi, Taslakian, Vazquez, Poole (IJCAI 2020)](https://doi.org/10.24963/ijcai.2020/303)
state: "as no validation set is proposed for JF17K, we randomly select 20% of the train set as
validation."

**Analysis.** Every paper that tunes on JF17K therefore tunes on a *different*, unpublished
split. Two JF17K numbers from two papers are not comparable even before the leakage issue is
considered. Any reproduction must record which validation split was used.

---

## 3. WikiPeople is almost entirely binary, and its literals are handled inconsistently

**Established (density).**

- [Rosso et al., 2020, Table 1](https://doi.org/10.1145/3366423.3380257): only **2.6%** of
  WikiPeople training facts and 2.6% of test facts are hyper-relational (7,389 of 287,918 and
  971 of 37,586).
- [Galkin et al., 2020](https://doi.org/10.18653/v1/2020.emnlp-main.596): "less than 3% of the
  remaining statements contain any qualifier pairs", and of those, "about 80% possess only one
  qualifier. This fact renders WikiPeople less sensitive to hyper-relational models."
- [Wei et al., 2025, Table 1](https://arxiv.org/abs/2506.08970) instead reports **11.6%** n-ary
  for WikiPeople — a different preprocessing of the same name.

**Established (literals).** WikiPeople as originally released from Wikidata contains statements
whose qualifier values are literals (dates, quantities). The **WikiPeople-** variant shipped
with GRAN is defined as WikiPeople with literal-bearing statements removed
([PaddlePaddle/Research › KG/ACL2021_GRAN](https://github.com/PaddlePaddle/Research/tree/master/KG/ACL2021_GRAN),
checked 2026-09-20). Galkin et al. likewise filter literals when constructing WD50K.

**Analysis.** "WikiPeople" names at least three different datasets in the literature: the raw
release, the literal-filtered release, and per-paper re-preprocessings. Because fewer than one
statement in thirty carries a qualifier, a model can score well on WikiPeople while being
completely wrong about qualifiers. Improvements of a few MRR points on WikiPeople are close to
uninterpretable.

---

## 4. The same dataset name carries incompatible statistics

Collected from the three primary sources (all checked 2026-09-20):

| Reported by | JF17K entities | JF17K relations | WikiPeople entities | WikiPeople relations |
|---|---|---|---|---|
| [Fatemi et al., 2020](https://doi.org/10.24963/ijcai.2020/303) | 29,177 | 327 | — | — |
| [Rosso et al., 2020](https://doi.org/10.1145/3366423.3380257) | 28,645 | 322 | 34,839 | 375 |
| [Wei et al., 2025](https://arxiv.org/abs/2506.08970) | 28,645 | 501 | 47,765 | 193 |

The relation counts for JF17K differ by a factor of 1.55 and the WikiPeople relation counts by a
factor of 1.94.

**Analysis.** These are not typographical errors; they are different preprocessing pipelines
(whether inverse relations are counted, whether literals are kept, whether arity-1 facts are
dropped). A benchmark identified only by name is under-specified. Cite a *file hash or release
tag*, not a name.

The same problem exists in the higher-order-network catalogues: `email-Enron` is 148 nodes in
XGI-DATA and 84,172 nodes in hypergraphx-data (the core versus the full network);
`walmart-trips` is 65,979 hyperedges in hypergraphx-data and 69,906 in
[AllSet](https://arxiv.org/abs/2106.13264).

---

## 5. WD50K: what "doing it properly" looks like, and what it costs

**Established.** [Galkin et al. (2020)](https://doi.org/10.18653/v1/2020.emnlp-main.596) built
WD50K with explicit anti-leakage filtering: they "remove all statements from train and
validation sets that share the same main triple *(s,p,o)* with test statements", drop literal
values, and remove entities appearing fewer than twice.

**Established (cost).** The qualifier-dense variants are progressively smaller and lexically
different: WD50K has 236,507 statements over 532 relations; WD50K(100) has 31,314 statements
over **279** relations. The qualifier vocabulary moves the other way — 45 relations appear in
qualifiers in WD50K, 75 in WD50K(100).

**Analysis.** WD50K is the only one of the three main benchmarks with a published leakage
control, so it should be the default. But because the four variants have different entity and
relation vocabularies, a model's score on WD50K(100) is not a "harder-setting" version of its
score on WD50K; it is a score on a different dataset. Report all four or say which one.

---

## 6. Benchmark saturation and the signal-to-noise problem

**Established.** The StarE abstract reports gains "up to 25 MRR points compared to triple-based
representations" when qualifiers are actually present and used
([Galkin et al., 2020](https://doi.org/10.18653/v1/2020.emnlp-main.596)).

**Analysis.** Combine that with the density figures: 13.6% of WD50K statements and under 3% of
WikiPeople statements carry any qualifier. On WikiPeople, a 25-point gain on 3% of the data is a
sub-1-point gain on the benchmark as a whole, well inside the variance of an unshared validation
split. Two practical consequences:

- **Aggregate MRR on a sparse benchmark hides the effect being measured.** Always report the
  qualifier-bearing subset separately — WD50K(100) exists precisely for this.
- **Leaderboard movement on JF17K and WikiPeople is not evidence.** Given section 1 and
  section 3, differences of one or two MRR points on those two datasets should be treated as
  noise unless accompanied by a subset breakdown and a stated split.

`[unverified]` No systematic reproduction study of n-ary link-prediction results (an analogue of
the triple-based reproducibility studies) was located in this run. This is a genuine gap; see
[getting-started-toolchain.md](getting-started-toolchain.md) for the tooling that would make one
feasible.

---

## 7. Hypergraph-learning benchmarks: features that are not features, hyperedges that are not higher-order

**Established.** In the standard AllSet suite
([Chien et al., ICLR 2022](https://arxiv.org/abs/2106.13264)), **House** and **Walmart** have no
original node features; the authors "use Gaussian random vectors instead". Cora co-citation has a
maximum hyperedge size of 5; NTU2012 and ModelNet40 have exactly as many hyperedges as nodes
(k-NN construction), i.e. their hypergraph structure is *manufactured*, not observed.

**Established.** In the XGI-DATA index (checked 2026-09-20), `contact-high-school` has mean edge
size **2.05**, `email-eu` 2.39, `tags-math-sx` 2.19, `coauth-dblp` 2.79.

**Analysis.** Several widely used "higher-order" datasets are overwhelmingly pairwise. Reporting
that a hypergraph model beats a graph model on `contact-high-school` says little, because the
data is a graph with a few triangles. Prefer datasets with a large mean edge size
(`house-committees`, mean 34.7; `congress-bills`, mean 8.7) when the claim is about higher-order
structure. This is the empirical side of the argument in
[../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md).

---

## 8. Hypergraph-RAG corpora: provenance, archiving and circularity

**Established (distribution).**

- HyperGraphRAG's evaluation README instructs users to "download the contexts and datasets from
  Terabox" ([evaluation/README.md](https://github.com/LHRLAB/HyperGraphRAG/blob/main/evaluation/README.md),
  checked 2026-09-20) — a commercial file-hosting service, with no DOI, checksum or version.
- Hyper-RAG's README distributes data via Google Drive and Baidu Cloud
  ([repository README](https://github.com/iMoonLab/Hyper-RAG), checked 2026-09-20).

**Established (origin).** Three of HyperGraphRAG's five domains (Agriculture, Computer Science,
Legal) are taken from **UltraDomain**; the Medicine domain is built from "the latest
international hypertension guidelines"
([Luo et al., 2025](https://arxiv.org/html/2503.21322v3)).

**Established (question construction).** HyperGraphRAG samples 512 questions per domain by
traversing the constructed structure: 128 one-hop, 64 two-hop and 64 three-hop from binary
sources, and the same distribution from n-ary sources, "manually verified" afterwards.

**Analysis — three distinct risks.**

1. **No archival copy.** Terabox, Google Drive and Baidu Cloud links rot and are geo-restricted.
   A benchmark whose data cannot be fetched reproducibly in five years is not a benchmark. Zenodo
   or Hugging Face with a DOI is the minimum bar; XGI-DATA does this correctly.
2. **Copyright.** "The latest international hypertension guidelines" are a copyrighted clinical
   document. Redistributing its text as an evaluation corpus without a stated licence is a legal
   problem the repositories do not address.
3. **Circularity.** Questions generated by walking the hypergraph that the proposed method
   built, and then answered by that method, favour that method by construction. The comparison
   against StandardRAG and NaiveGeneration is a comparison on the proposer's home ground. An
   independent question set (or at least questions generated from the raw text, not from the
   extracted structure) would be needed before the reported margins mean much.

---

## 9. Licensing gaps

| Artefact | Problem | Checked |
|---|---|---|
| [ServiceNow/HypE](https://github.com/ServiceNow/HypE), [baharefatemi/HypE](https://github.com/baharefatemi/HypE) | ship FB-AUTO and M-FB15K with **no licence file** on the repository | 2026-09-20 |
| [Jpickard1/Hypergraph-Analysis-Toolbox](https://github.com/Jpickard1/Hypergraph-Analysis-Toolbox) | library with no licence file, despite a published paper | 2026-09-20 |
| [bdi-lab/HyNT](https://github.com/bdi-lab/HyNT), [xgi-org/xgi-data](https://github.com/xgi-org/xgi-data), [pnnl/hypernetx-widget](https://github.com/pnnl/hypernetx-widget) | GitHub licence metadata `NOASSERTION` ("Other") | 2026-09-20 |
| Freebase-derived sets (JF17K, FB-AUTO, M-FB15K) | Freebase was CC-BY; derivatives are redistributed without attribution statements | 2026-09-20 |

Absent a licence, the default is "all rights reserved" — an obstacle to any downstream
redistribution, including the manifest in [../../datasets/README.md](../../datasets/README.md).

---

## 10. Recommendations for this knowledge base and anything built from it

1. **Never cite a benchmark by name alone.** Record the repository, commit or release tag, and a
   checksum of the split files. The manifest format in
   [../../datasets/README.md](../../datasets/README.md) has fields for this.
2. **Default to WD50K and its variants** for hyper-relational link prediction; it is the only one
   of the three with published leakage control. Use JF17K and WikiPeople only for comparability
   with older work, and state the leakage and density caveats when you do.
3. **Always report the qualifier-bearing / n-ary subset separately** from the aggregate.
4. **Prefer datasets with mean hyperedge size well above 2** for claims about higher-order
   structure, and say what the mean is.
5. **Do not evaluate a construction method on questions derived from its own output.** If no
   independent question set exists, say so and treat the margins as indicative only.
6. **Re-archive anything you depend on.** Deposit a copy (where the licence permits) with a DOI,
   and record the original URL and the retrieval date.
7. **Treat missing licences as blockers, not warnings.** Record them in the manifest and contact
   the authors rather than silently redistributing.
8. **Build a leakage check into the toolchain.** For a hyper-relational split this is three lines
   of pandas: hash each test statement's main triple and intersect with train. Running that check
   is cheaper than believing a leaderboard.

---

## Sources

- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. (2020). *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020, 7346–7359. <https://doi.org/10.18653/v1/2020.emnlp-main.596> — JF17K leakage quote, WikiPeople qualifier density, WD50K construction and filtering.
- Rosso, P., Yang, D., Cudré-Mauroux, P. (2020). *Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction.* WWW 2020, 1885–1896. <https://doi.org/10.1145/3366423.3380257> — JF17K/WikiPeople Table 1; full text searched 2026-09-20 and found to contain no leakage claim.
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. (2020). *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020, 2191–2197. <https://doi.org/10.24963/ijcai.2020/303> — missing JF17K validation set; FB-AUTO / M-FB15K construction.
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. (2025). *A Survey of Link Prediction in N-ary Knowledge Graphs.* arXiv:2506.08970. <https://arxiv.org/abs/2506.08970> — a third set of JF17K/WikiPeople statistics.
- Chien, E., Pan, C., Peng, J., Milenkovic, O. (2022). *You are AllSet: A Multiset Function Framework for Hypergraph Neural Networks.* ICLR 2022; arXiv:2106.13264. <https://arxiv.org/abs/2106.13264> — Gaussian random features for House and Walmart; benchmark table.
- Luo, H., E, H., Chen, G. et al. (2025). *HyperGraphRAG.* arXiv:2503.21322v3. <https://arxiv.org/html/2503.21322v3>; evaluation instructions <https://github.com/LHRLAB/HyperGraphRAG/blob/main/evaluation/README.md>, checked 2026-09-20.
- Feng, Y., Hu, H., Ying, S. et al. (2026). *Hyper-RAG.* Nature Communications 17, 5778. <https://doi.org/10.1038/s41467-026-71411-1>; repository <https://github.com/iMoonLab/Hyper-RAG>, checked 2026-09-20.
- Wang, Q., Wang, H., Lyu, Y., Zhu, Y. (2021). *Link Prediction on N-ary Relational Facts: A Graph-based Approach.* Findings of ACL-IJCNLP 2021. <https://doi.org/10.18653/v1/2021.findings-acl.35>; WikiPeople- and arity-restricted variants at <https://github.com/PaddlePaddle/Research/tree/master/KG/ACL2021_GRAN>, checked 2026-09-20.
- XGI-DATA index (<https://raw.githubusercontent.com/xgi-org/xgi-data/main/index.json>) and hypergraphx-data catalogue (<https://hgx-team.github.io/hypergraphx-data/>), both retrieved 2026-09-20, for the conflicting `email-Enron` and `walmart-trips` statistics.
- GitHub repository licence metadata retrieved via the GitHub repository search API, 2026-09-20.
