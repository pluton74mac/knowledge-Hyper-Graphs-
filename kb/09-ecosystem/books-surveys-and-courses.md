---
title: Books, surveys and teaching material on hypergraphs and n-ary knowledge
type: survey
status: draft
tags: [ecosystem, books, surveys, reading-list, teaching, higher-order-networks, n-ary]
created: 2026-09-20
updated: 2026-09-20
---

# Books, surveys and teaching material

A reading list with provenance. Every entry was resolved through Crossref, the arXiv API or
Open Library on **2026-09-20**; anything that could not be resolved is marked `[unverified]`.
For where each item fits in the argument, see the section map in [README.md](README.md).

---

## 1. Books: the mathematical foundation

| Work | Author(s) | Publisher / series | Year | Identifier |
|---|---|---|---|---|
| **Graphs and Hypergraphs** | Claude Berge | North-Holland / American Elsevier | 1973 | ISBN 0-444-10399-6 (Open Library) |
| **Hypergraphs: Combinatorics of Finite Sets** | Claude Berge | North-Holland Mathematical Library 45 | 1989 | ISBN 0-444-87489-5 (Open Library) |
| **Coloring Mixed Hypergraphs: Theory, Algorithms and Applications** | Vitaly I. Voloshin | AMS, Fields Institute Monographs 17 | 2002 | [10.1090/fim/017](https://doi.org/10.1090/fim/017) |
| **Introduction to Graph and Hypergraph Theory** | Vitaly I. Voloshin | Nova Science Publishers | 2009 | ISBN 1-60692-372-2 (Open Library) |
| **Hypergraph Theory: An Introduction** | Alain Bretto | Springer, Mathematical Engineering | 2013 | [10.1007/978-3-319-00080-0](https://doi.org/10.1007/978-3-319-00080-0) |

Berge 1973 is the English edition of *Graphes et hypergraphes* (Dunod, 1970) `[unverified]`;
the 1989 volume is the one normally cited for the modern definition of a hypergraph as a family
of non-empty subsets. Bretto 2013 is the most usable modern textbook: short, with algorithms and
applications. Voloshin 2009 is the gentlest entry point and covers colourings in depth.

See [../01-foundations/hypergraph-definitions.md](../01-foundations/hypergraph-definitions.md)
for how the definitions differ between these books.

---

## 2. Books: higher-order systems and hypergraph computation

| Work | Editor(s)/Author(s) | Publisher / series | Year | Identifier |
|---|---|---|---|---|
| **Higher-Order Systems** | Federico Battiston, Giovanni Petri (eds.) | Springer, Understanding Complex Systems | 2022 | [10.1007/978-3-030-91374-8](https://doi.org/10.1007/978-3-030-91374-8) |
| **Hypergraph Computation** | Qionghai Dai, Yue Gao | Springer, Artificial Intelligence: Foundations, Theory, and Algorithms | 2023 | [10.1007/978-981-99-0185-2](https://doi.org/10.1007/978-981-99-0185-2) |

*Higher-Order Systems* is the edited volume behind much of the physics-side terminology
("higher-order interactions", simplicial contagion). *Hypergraph Computation* is the book-length
companion to the HGNN line of work and the DHG library
([software-libraries.md](software-libraries.md)).

---

## 3. Surveys: higher-order networks (structure and dynamics)

| Survey | Authors | Venue | Year | Identifier |
|---|---|---|---|---|
| **Networks beyond pairwise interactions: Structure and dynamics** | Battiston, Cencetti, Iacopini, Latora, Lucas, Patania, Young, Petri | Physics Reports 874, 1–92 | 2020 | [10.1016/j.physrep.2020.05.004](https://doi.org/10.1016/j.physrep.2020.05.004) |
| **The physics of higher-order interactions in complex systems** | Battiston, Amico, Barrat, Bianconi, Ferraz de Arruda, Franceschiello, Iacopini, Kéfi, Latora, Moreno, Murray, Peixoto, Vaccarino, Petri | Nature Physics 17, 1093–1098 | 2021 | [10.1038/s41567-021-01371-4](https://doi.org/10.1038/s41567-021-01371-4) |
| **What Are Higher-Order Networks?** | Bick, Gross, Harrington, Schaub | SIAM Review 65(3), 686–731 | 2023 | [10.1137/21M1414024](https://doi.org/10.1137/21M1414024) |
| **A Survey on Hypergraph Mining: Patterns, Tools, and Generators** | Lee, Bu, Eliassi-Rad, Shin | arXiv:2401.08878 (v2, 2025-02-18) | 2024–25 | <https://arxiv.org/abs/2401.08878> |
| **Spectral Theory of Hypergraphs: A Survey** | Shetty, Bhat | arXiv:2507.13664 | 2025 | <https://arxiv.org/abs/2507.13664> |
| **A survey of simplicial, relative, and chain complex homology theories for hypergraphs** | Gasparovic, Purvine, Sazdanovic, Wang, Wang, Ziegelmeier | arXiv:2409.18310 (v2, 2025-10-10) | 2024–25 | <https://arxiv.org/abs/2409.18310> |
| **Coloring Geometric Hypergraphs: A Survey** | Damásdi, Keszegh, Pach, Pálvölgyi, Tóth | arXiv:2512.09509 | 2025 | <https://arxiv.org/abs/2512.09509> |

**Start with Bick et al. 2023.** It is the one survey that takes the *modelling* question
seriously — when a higher-order representation is warranted and when a graph suffices — which is
exactly the question in
[../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md).
Battiston et al. 2020 is the encyclopaedic reference (92 pages).

---

## 4. Surveys: hypergraph representation learning

| Survey | Authors | Venue | Year | Identifier |
|---|---|---|---|---|
| **A Survey on Hypergraph Representation Learning** | Antelmi, Cordasco, Polato, Scarano, Spagnuolo, Yang | ACM Computing Surveys 56(1), 1–38 | 2023 | [10.1145/3605776](https://doi.org/10.1145/3605776) |
| **Hypergraph Learning: Methods and Practices** | Gao, Zhang, Lin, Zhao, Du, Zou | IEEE TPAMI | 2021 | [10.1109/TPAMI.2020.3039374](https://doi.org/10.1109/TPAMI.2020.3039374) |
| **HGNN⁺: General Hypergraph Neural Networks** | Gao, Feng, Ji, Ji | IEEE TPAMI 45(3), 3181–3199 | 2023 | [10.1109/TPAMI.2022.3182052](https://doi.org/10.1109/TPAMI.2022.3182052) |
| **Architectures of Topological Deep Learning: A Survey of Message-Passing Topological Neural Networks** | Papillon, Sanborn, Hajij, Miolane | arXiv:2304.10031 (v3, 2024-02-21) | 2023–24 | <https://arxiv.org/abs/2304.10031> |
| **On Hypergraph Neural Networks and Their Stability Towards Higher-Order Knowledge Representation and Learning** | Bhuyan, Singh, Tomar, Ramdane-Cherif | SN Computer Science | 2024 | [10.1007/s42979-024-03453-5](https://doi.org/10.1007/s42979-024-03453-5) |

HGNN⁺ is not formally a survey but is the standard reference for the general framework
(and the paper behind DHG). Papillon et al. is the map of the topological-deep-learning
neighbourhood that TopoX implements.

---

## 5. Surveys: n-ary and hyper-relational knowledge graphs

| Survey | Authors | Venue | Year | Identifier |
|---|---|---|---|---|
| **A Survey of Link Prediction in N-ary Knowledge Graphs** | Wei, Guan, Li, Jin, Guo, Cheng | arXiv:2506.08970 | 2025 | <https://arxiv.org/abs/2506.08970> |
| **Two-Dimensional Taxonomy for n-Ary Knowledge Representation Learning Methods** | Lu, Tupikina, Alam | IEEE TKDE (early access) | 2026 | [10.1109/TKDE.2026.3731554](https://doi.org/10.1109/TKDE.2026.3731554); preprint arXiv:2506.05626 (v3, 2026-09-06) |

These two are the most important recent entries for this knowledge base and they are
complementary. Wei et al. organise **methods** into spatial-mapping, tensor-decomposition and
neural-network families, and **settings** into general, temporal, inductive and few-shot, with
dataset tables for each (reproduced in [datasets-and-benchmarks.md](datasets-and-benchmarks.md)).
Lu, Tupikina and Alam cross-cut by representation *and* task.

Neither is a reproducibility study; see
[dataset-quality-and-leakage-issues.md](dataset-quality-and-leakage-issues.md) for why one is
needed.

`[unverified]` A survey published on TechRxiv in 2025 under the title "Survey of Hypergraph- and
Superhypergraph-Based Models" (Fujita, [10.36227/techrxiv.175623879.97576048/v1](https://doi.org/10.36227/techrxiv.175623879.97576048/v1))
appears in Crossref but is a non-peer-reviewed preprint and was not assessed here.

---

## 6. Software and standards papers worth reading as documentation

| Paper | Venue | Year | Identifier |
|---|---|---|---|
| **HIF: The hypergraph interchange format for higher-order networks** (Coll, Joslyn, Landry, Lotito, Myers, Pickard, Praggastis, Szufel) | Network Science 13, e21 | 2025 | [10.1017/nws.2025.10018](https://doi.org/10.1017/nws.2025.10018) |
| **XGI: A Python package for higher-order interaction networks** (Landry, Lucas, Iacopini, Petri, Schwarze, Patania, Torres) | JOSS 8(85), 5162 | 2023 | [10.21105/joss.05162](https://doi.org/10.21105/joss.05162) |
| **Hypergraphx: a library for higher-order network analysis** (Lotito, Contisciani, De Bacco, Di Gaetano, Gallo, Montresor, Musciotto, Ruggeri, Battiston) | Journal of Complex Networks 11(3), cnad019 | 2023 | [10.1093/comnet/cnad019](https://doi.org/10.1093/comnet/cnad019) |
| **HAT: Hypergraph analysis toolbox** (Pickard, Chen, Salman, Stansbury, Kim, Surana, Bloch, Rajapakse) | PLOS Computational Biology 19(6), e1011190 | 2023 | [10.1371/journal.pcbi.1011190](https://doi.org/10.1371/journal.pcbi.1011190) |
| **TopoX: A Suite of Python Packages for Machine Learning on Topological Domains** (Hajij, Papillon, Frantzen et al.) | arXiv:2402.02441 (v5, 2024-12-09) | 2024 | <https://arxiv.org/abs/2402.02441> |
| **Simplicial closure and higher-order link prediction** (Benson, Abebe, Schaub, Jadbabaie, Kleinberg) | PNAS 115(48) | 2018 | [10.1073/pnas.1800683115](https://doi.org/10.1073/pnas.1800683115) |

---

## 7. A suggested reading path

1. **Definitions and when to use them** — Bretto 2013 chapters 1–2, then Bick et al. 2023.
2. **Empirical higher-order structure** — Benson et al. 2018 (PNAS), then the dataset catalogues
   in [datasets-and-benchmarks.md](datasets-and-benchmarks.md).
3. **Knowledge side** — Wei et al. 2025 for the map, then the three primary dataset papers
   (Wen et al. 2016, Guan et al. 2019, Galkin et al. 2020), then
   [dataset-quality-and-leakage-issues.md](dataset-quality-and-leakage-issues.md).
4. **Learning** — Antelmi et al. 2023 (CSUR), then HGNN⁺ and AllSet.
5. **Tooling** — the HIF paper, then [getting-started-toolchain.md](getting-started-toolchain.md).

---

## 8. Courses, tutorials and seminars

This is the weakest part of the ecosystem, and the note says so rather than padding the list.

**Verified (2026-09-20):**

- **HIF tutorials.** The [HIF-standard repository](https://github.com/HIF-org/HIF-standard) ships
  a `tutorials/` folder with per-library notebooks showing how HypergraphX, HyperNetX, HAT,
  SimpleHypergraphs.jl and XGI each read and write HIF, plus validator snippets for Python, R and
  Julia in the README. This is the single best hands-on starting point.
- **Dagstuhl Seminar 26411, "Large Language Models Meet Knowledge Graphs"**, 4–9 October 2026,
  organised by Angela Bonifati, Jan-Christoph Kalo, Jeff Z. Pan, Simon Razniewski and Luke
  Zettlemoyer (<https://www.dagstuhl.de/en/seminars/seminar-calendar>). This is the closest
  scheduled venue to the subject of this knowledge base.
- **No Dagstuhl seminar dedicated to hypergraphs or higher-order networks** appears in the
  seminar calendar as searched on 2026-09-20.

**`[unverified]`** — named in the wider literature but not confirmed from a primary source in
this run, and therefore deliberately not tabulated: NetSci / Complex Networks conference
tutorials on higher-order networks; the XGI and HyperNetX conference tutorials; IJCAI/KDD/WWW
tutorials on n-ary knowledge-graph embedding; university courses on hypergraph theory. A future
research run should confirm these against conference programmes before they are listed.

Community channels and workshop series are in
[awesome-lists-and-communities.md](awesome-lists-and-communities.md).

---

## Sources

- Berge, C. (1973). *Graphs and Hypergraphs.* North-Holland / American Elsevier. ISBN 0-444-10399-6. Open Library record, checked 2026-09-20. <https://openlibrary.org/search?q=Graphs+and+hypergraphs+Berge>
- Berge, C. (1989). *Hypergraphs: Combinatorics of Finite Sets.* North-Holland Mathematical Library 45. ISBN 0-444-87489-5. Open Library record, checked 2026-09-20.
- Voloshin, V. I. (2002). *Coloring Mixed Hypergraphs: Theory, Algorithms and Applications.* AMS Fields Institute Monographs. <https://doi.org/10.1090/fim/017>
- Voloshin, V. I. (2009). *Introduction to Graph and Hypergraph Theory.* Nova Science Publishers. ISBN 1-60692-372-2. Open Library record, checked 2026-09-20.
- Bretto, A. (2013). *Hypergraph Theory: An Introduction.* Springer, Mathematical Engineering. <https://doi.org/10.1007/978-3-319-00080-0>
- Battiston, F., Petri, G. (eds.) (2022). *Higher-Order Systems.* Springer, Understanding Complex Systems. <https://doi.org/10.1007/978-3-030-91374-8>
- Dai, Q., Gao, Y. (2023). *Hypergraph Computation.* Springer. <https://doi.org/10.1007/978-981-99-0185-2>
- Battiston, F., Cencetti, G., Iacopini, I., Latora, V., Lucas, M., Patania, A., Young, J.-G., Petri, G. (2020). *Networks beyond pairwise interactions: Structure and dynamics.* Physics Reports 874, 1–92. <https://doi.org/10.1016/j.physrep.2020.05.004>
- Battiston, F., Amico, E., Barrat, A. et al. (2021). *The physics of higher-order interactions in complex systems.* Nature Physics 17, 1093–1098. <https://doi.org/10.1038/s41567-021-01371-4>
- Bick, C., Gross, E., Harrington, H. A., Schaub, M. T. (2023). *What Are Higher-Order Networks?* SIAM Review 65(3), 686–731. <https://doi.org/10.1137/21M1414024>
- Lee, G., Bu, F., Eliassi-Rad, T., Shin, K. (2024–25). *A Survey on Hypergraph Mining: Patterns, Tools, and Generators.* arXiv:2401.08878. <https://arxiv.org/abs/2401.08878>
- Shetty, S. S., Bhat, K. A. (2025). *Spectral Theory of Hypergraphs: A Survey.* arXiv:2507.13664. <https://arxiv.org/abs/2507.13664>
- Gasparovic, E., Purvine, E., Sazdanovic, R., Wang, B., Wang, Y., Ziegelmeier, L. (2024–25). *A survey of simplicial, relative, and chain complex homology theories for hypergraphs.* arXiv:2409.18310. <https://arxiv.org/abs/2409.18310>
- Damásdi, G., Keszegh, B., Pach, J., Pálvölgyi, D., Tóth, G. (2025). *Coloring Geometric Hypergraphs: A Survey.* arXiv:2512.09509. <https://arxiv.org/abs/2512.09509>
- Antelmi, A., Cordasco, G., Polato, M., Scarano, V., Spagnuolo, C., Yang, D. (2023). *A Survey on Hypergraph Representation Learning.* ACM Computing Surveys 56(1). <https://doi.org/10.1145/3605776>
- Gao, Y., Zhang, Z., Lin, H., Zhao, X., Du, S., Zou, C. (2021). *Hypergraph Learning: Methods and Practices.* IEEE TPAMI. <https://doi.org/10.1109/TPAMI.2020.3039374>
- Gao, Y., Feng, Y., Ji, S., Ji, R. (2023). *HGNN⁺: General Hypergraph Neural Networks.* IEEE TPAMI 45(3), 3181–3199. <https://doi.org/10.1109/TPAMI.2022.3182052>
- Papillon, M., Sanborn, S., Hajij, M., Miolane, N. (2023–24). *Architectures of Topological Deep Learning: A Survey of Message-Passing Topological Neural Networks.* arXiv:2304.10031. <https://arxiv.org/abs/2304.10031>
- Bhuyan, B., Singh, T., Tomar, R., Ramdane-Cherif, A. (2024). *On Hypergraph Neural Networks and Their Stability Towards Higher-Order Knowledge Representation and Learning.* SN Computer Science. <https://doi.org/10.1007/s42979-024-03453-5>
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. (2025). *A Survey of Link Prediction in N-ary Knowledge Graphs.* arXiv:2506.08970. <https://arxiv.org/abs/2506.08970>
- Lu, X., Tupikina, L., Alam, M. (2026). *Two-Dimensional Taxonomy for n-Ary Knowledge Representation Learning Methods.* IEEE TKDE. <https://doi.org/10.1109/TKDE.2026.3731554>; preprint <https://arxiv.org/abs/2506.05626>
- Coll, M., Joslyn, C. A., Landry, N. W. et al. (2025). *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21. <https://doi.org/10.1017/nws.2025.10018>
- Landry, N. W. et al. (2023). *XGI.* JOSS 8(85), 5162. <https://doi.org/10.21105/joss.05162>
- Lotito, Q. F. et al. (2023). *Hypergraphx.* Journal of Complex Networks 11(3), cnad019. <https://doi.org/10.1093/comnet/cnad019>
- Pickard, J. et al. (2023). *HAT: Hypergraph analysis toolbox.* PLOS Computational Biology 19(6), e1011190. <https://doi.org/10.1371/journal.pcbi.1011190>
- Hajij, M. et al. (2024). *TopoX.* arXiv:2402.02441. <https://arxiv.org/abs/2402.02441>
- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. (2018). *Simplicial closure and higher-order link prediction.* PNAS 115(48). <https://doi.org/10.1073/pnas.1800683115>
- Schloss Dagstuhl seminar calendar, <https://www.dagstuhl.de/en/seminars/seminar-calendar>, checked 2026-09-20 (Seminar 26411).
