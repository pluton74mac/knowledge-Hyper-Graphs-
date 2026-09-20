---
title: Courses, tutorials and workshops — verified teaching material
type: survey
status: draft
tags: [ecosystem, teaching, courses, tutorials, workshops, seminars, community, gap-filling]
created: 2026-09-20
updated: 2026-09-20
---

# Courses, tutorials and workshops

[books-surveys-and-courses.md](books-surveys-and-courses.md) §8 says that teaching material is "the
weakest part of the ecosystem" and lists most candidates as `[unverified]`, deferring confirmation
to a later run. **This is that run.** Everything below was resolved against a primary page on
**2026-09-20**; anything that could not be is marked `[unverified]` and is not tabulated as fact.

The headline correction to the earlier note: **conference tutorials are not thin at all.** One
research group (Kijung Shin's at KAIST, with collaborators in Turin and Tsinghua) has run a
hypergraph tutorial at **seven** major venues between 2022 and 2025. What is thin is *knowledge*-
hypergraph teaching: no tutorial anywhere covers n-ary or hyper-relational knowledge graphs.

---

## 1. University courses

| Year | Institution | Code and title | Instructor | URL | Covers |
|---|---|---|---|---|---|
| Fall 2024 | UNC Chapel Hill | DATA 890-003, *Special Topic in Data Science: **Graphs and Hypergraphs*** | Can Chen | [tarheels.live/canc/teaching](https://tarheels.live/canc/teaching/) | "Graphs and hypergraphs are fundamental mathematical structures with wide-ranging applications in various fields, including computer science, mathematics, biology" — theory, learning techniques and applications of graphs *and* hypergraphs |
| Fall 2025 | UNC Chapel Hill | DATA 890-003, *Machine Learning with Graphs* | Can Chen | same | The 2025 successor course; the hypergraph half is dropped from the stated description |
| 2019–2026, annually | KAIST | AI607, *Graph Mining and Social Network Analysis* | Kijung Shin | [kijungs.github.io](https://kijungs.github.io/) | Graph mining with substantial higher-order/hypergraph content, per the instructor's own page |
| 2020–2026, annually | KAIST | AI506, *Data Mining and Search* | Kijung Shin | same | Adjacent; mining foundations |

**Reading.** Two institutions, one dedicated course, and that course ran **once**: UNC's DATA 890
was "Graphs and Hypergraphs" in Fall 2024 and "Machine Learning with Graphs" in Fall 2025. A
hypergraph course is currently a special topic that depends on one faculty member's interest, not a
standing curriculum item anywhere this run could find.

`[unverified]` Tsinghua's Yue Gao is the co-author of the textbook *Hypergraph Computation* (Dai and
Gao, Springer 2023) and of the DHG library, and a corresponding taught course is plausible; no
syllabus page was reachable in this run, so none is listed.

---

## 2. Conference tutorials

This is the strongest teaching resource in the ecosystem and it was missing from the KB.

| Years | Venues | Tutorial | Organisers | URL | Covers |
|---|---|---|---|---|---|
| 2024–2025 | **KDD 2024, ICDM 2024, AAAI 2025, CIKM 2025** | *Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide* | Sunwoo Kim (KAIST), Alessia Antelmi (Turin), Soo Yong Lee (KAIST), Mirko Polato (Turin), Yue Gao (Tsinghua), Kijung Shin (KAIST) | [sites.google.com/view/hnn-tutorial](https://sites.google.com/view/hnn-tutorial) | Six parts: inputs; input features and structures; message-passing schemes; training strategies; applications (recommenders, time series); open problems. Slides downloadable per part. |
| 2022–2023 | **CIKM 2022, ICDM 2022, WWW 2023, KDD 2023** | *Mining of Real-world Hypergraphs: Patterns, Tools, and Generators* | Geon Lee (KAIST), Jaemin Yoo (CMU Heinz), Kijung Shin (KAIST) | [sites.google.com/view/hypergraph-tutorial](https://sites.google.com/view/hypergraph-tutorial) | Four parts: group interactions and data repositories; static structural patterns at node/hyperedge/hypergraph level; dynamic/temporal patterns; generative models. **3-hour video plus 20-minute teaser, PDF slides for all four parts, 22 referenced papers with code links.** |

Both tutorials have published companion surveys, which is the cheapest way to read them: the HNN
tutorial corresponds to [Kim, Lee, Gao, Antelmi, Polato and Shin, *A Survey on Hypergraph Neural
Networks: An In-Depth and Step-By-Step Guide*, KDD 2024 /
arXiv:2404.01039](https://arxiv.org/abs/2404.01039) (the arXiv comment reads "To appear in KDD 2024
(survey paper)"), and the mining tutorial to [Lee, Bu, Eliassi-Rad and Shin, *A Survey on Hypergraph
Mining*, arXiv:2401.08878](https://arxiv.org/abs/2401.08878), both already in
[books-surveys-and-courses.md](books-surveys-and-courses.md) §§3–4 as *surveys* without the
teaching material attached to them.

A third, related-but-different tutorial by the same group is listed for **KDD 2026 and CIKM 2026**:
*Retrieval-Augmented Generation for LLM-based Recommender Systems*
([kijungs.github.io](https://kijungs.github.io/)). It is not a hypergraph tutorial.

**The gap.** No tutorial at ISWC, ESWC, WWW, IJCAI or KDD covers **n-ary or hyper-relational
knowledge graphs**. Searches for one on 2026-09-20 returned only research papers. `[unverified]`
Given that the n-ary link-prediction literature now numbers "nearly 50 methods" ([Wei, Guan, Li,
Jin, Guo and Cheng, EMNLP 2025](https://arxiv.org/abs/2506.08970)), a Semantic Web venue tutorial is
overdue and is a concrete community contribution this KB's readers could make.

---

## 3. The topological deep learning challenge series

A distinctive institution: an annual *competition* that doubles as a teaching device, because
entries must be contributions to the TopoX packages.

| Year | Host workshop | Outcome paper | Covers |
|---|---|---|---|
| 2023 | ICML 2023 Workshop on **Topology and Geometry in Machine Learning (TAG-ML)** | Papillon, Hajij et al., *ICML 2023 Topological Deep Learning Challenge: Design and Results*, [PMLR 221:3–8](https://proceedings.mlr.press/v221/papillon23a.html) / [arXiv:2309.15188](https://arxiv.org/abs/2309.15188) | Participants provide open-source implementations of topological neural networks from the literature by contributing to **TopoNetX** (data processing) and **TopoModelX** (deep learning). **28 qualifying submissions** over two months. |
| 2024 | ICML 2024 ELLIS Workshop on **Geometry-grounded Representation Learning and Generative Modeling (GRaM)** | Bernárdez, Telyatnikov, Montagna et al. (73 authors), *ICML Topological Deep Learning Challenge 2024: Beyond the Graph Domain*, [arXiv:2409.05211](https://arxiv.org/abs/2409.05211) | Data *transformation* into topological domains — **hypergraphs**, simplicial complexes, cell complexes and combinatorial complexes — from point clouds and graphs. **52 submissions** met all criteria. |

For a knowledge-hypergraph reader, the 2024 edition is the relevant one: "lift a graph into a
hypergraph" is precisely the operation in
[../03-construction/from-knowledge-graphs-to-hypergraphs.md](../03-construction/from-knowledge-graphs-to-hypergraphs.md),
and the challenge produced 52 implementations of it. The software is catalogued in
[software-libraries.md](software-libraries.md); the theory context is
[../05-query-embeddings-reasoning/hypergraph-neural-networks.md](../05-query-embeddings-reasoning/hypergraph-neural-networks.md).

---

## 4. Workshops, satellites and hackathons

The 2026 editions are documented in
[../08-history-and-frontier/venues-and-community-events.md](../08-history-and-frontier/venues-and-community-events.md)
§6 and are not repeated here. What that note establishes, and this one endorses:

- **HONS — Higher-Order Network Science**, a recurring NetSci satellite
  ([hons-web.github.io](https://hons-web.github.io/online/)).
- **TopoNets 2026**, 2 June 2026, Boston, "Networks beyond pairwise interactions"
  ([site](https://sites.google.com/view/toponets2026/home-page)) — with a long prior-edition lineage.
- **A Higher Order Hackathon — "A Blue Start"**, 31 May 2026, Northeastern University, organised by
  Phil Chodrow, A. Smith and Nicholas Landry
  ([page](https://www.philchodrow.prof/higher-order-hackathon/)), using **XGI** on a Bluesky
  starter-pack dataset.

The hackathon is the format worth copying for this KB: it is simultaneously teaching, library
maintenance and dataset production. NetSci 2025 additionally ran parallel sessions "Higher order
networks 1" and "2", chaired by Giovanni Petri and Alec Kirkley respectively
([netsci2025.github.io](https://netsci2025.github.io/focus_sessions/)) — evidence that the topic is
now a standing programme item, not a satellite-only subject.

`[unverified]` No dedicated **hypergraph tutorial** at NetSci or at the Complex Networks conference
was confirmed from a primary programme page in this run, despite being frequently referred to.

---

## 5. Dagstuhl seminars

| Number | Dates | Title | Organisers | URL |
|---|---|---|---|---|
| **21352** | 29 Aug – 1 Sep 2021 | *Higher-Order Graph Models: From Theoretical Foundations to Machine Learning* | see seminar page | [dagstuhl.de/21352](https://www.dagstuhl.de/seminars/seminar-calendar/seminar-details/21352) |
| **26411** | 4–9 Oct 2026 | *Large Language Models Meet Knowledge Graphs* | Angela Bonifati (Lyon), Jan-Christoph Kalo (Amsterdam), Jeff Z. Pan (Edinburgh), Simon Razniewski (TU Dresden), Luke Zettlemoyer (Washington) | [dagstuhl.de/26411](https://www.dagstuhl.de/26411) |

Two neighbours found in this run that
[../08-history-and-frontier/venues-and-community-events.md](../08-history-and-frontier/venues-and-community-events.md)
does not list, and which a reader tracking this area should know about:

- **25291**, *(Actual) Neurosymbolic AI: Combining Deep Learning and Knowledge Graphs*
  ([dagstuhl.de/…/25291](https://www.dagstuhl.de/seminars/seminar-calendar/seminar-details/25291)).
- **22372**, *Knowledge Graphs and Their Role in the Knowledge Engineering of the 21st Century*
  ([dagstuhl.de/22372](https://www.dagstuhl.de/22372)).

The pattern holds: the **graph-model** community gets Dagstuhls (21352), the **knowledge-graph**
community gets Dagstuhls (18371, 22372, 25291, 26411), and the intersection — n-ary knowledge
representation — has never had one.

---

## 6. Library tutorials: the hands-on layer

| Resource | What it teaches | URL | Checked |
|---|---|---|---|
| **HIF-standard `tutorials/`** | Nine notebooks — `EG.ipynb`, `HAT.ipynb`, `HIF-demo.ipynb`, `HIF-SimpleHypergraphs-demo.ipynb`, `hgx.ipynb`, `hnx.ipynb`, `tnx.ipynb`, `xgi.ipynb` plus a `data/` folder — one per library (EasyGraph, HAT, Hypergraphx, HyperNetX, SimpleHypergraphs.jl, TopoNetX, XGI) showing HIF read/write | [github.com/HIF-org/HIF-standard/tree/main/tutorials](https://github.com/HIF-org/HIF-standard/tree/main/tutorials) (36 stars, MIT) | 2026-09-20 |
| **HyperNetX `tutorials/`** | Six Colab-runnable notebooks: *HNX Basics*, *Visualization Methods*, *LesMis Case Study*, *LesMis Visualizations — Book Tour*, *HNX attributed hypergraph*, *Hypergraph Arithmetic* | [github.com/pnnl/HyperNetX](https://github.com/pnnl/HyperNetX) (716 stars, BSD-3-Clause); docs [hypernetx.readthedocs.io](https://hypernetx.readthedocs.io/) | 2026-09-20 |
| **XGI docs tutorials** | Begins with *XGI in 1 minute 🚀* — create hypergraphs, add nodes and hyperedges singly or in bulk, plot, query counts — then focused tutorials including plotting | [xgi.readthedocs.io/en/stable/api/tutorials/getting_started_1.html](https://xgi.readthedocs.io/en/stable/api/tutorials/getting_started_1.html) (XGI 0.10.2, released 15 May 2026) | 2026-09-20 |

**Note for future runs:** the XGI tutorials *index* page at
`xgi.readthedocs.io/en/stable/api/tutorials.html` returned **404** on 2026-09-20; individual
tutorial pages resolve. Link to the individual page, not the index.

The `HyperNetX` *Hypergraph Arithmetic* notebook and the `HNX attributed hypergraph` notebook are
the two closest to what a knowledge-hypergraph reader needs — attributes on incidences are the
role-labelling primitive discussed in
[../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md](../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md).

Start with [getting-started-toolchain.md](getting-started-toolchain.md), which already runs all
three libraries against [../../schemas/sample.hif.json](../../schemas/sample.hif.json).

---

## 7. Video and long-form written material

| Resource | Form | URL | Note |
|---|---|---|---|
| *Mining of Real-world Hypergraphs* tutorial | 3-hour video + 20-minute teaser, plus four PDF decks | [sites.google.com/view/hypergraph-tutorial](https://sites.google.com/view/hypergraph-tutorial) | **The single best free video resource found.** Confirmed from the tutorial page. |
| Bianconi, *Higher-Order Networks* | Cambridge Element, *Structure and Dynamics of Complex Networks* series, online 23 Nov 2021 | [10.1017/9781108770996](https://doi.org/10.1017/9781108770996) | Book-length introduction built on simplicial complexes; **not currently in [books-surveys-and-courses.md](books-surveys-and-courses.md)** and should be added on the next revision of that note |
| HIntNets project page (Michael Schaub, RWTH Aachen) | Talk index and links, 2017–2020, incl. NetSci 2018, Complex Networks 2018, ICCS 2018 | [michaelschaub.github.io/HIntNets](https://michaelschaub.github.io/HIntNets/) | "Higher-order interactions and Laplacian dynamics in complex networks"; links to a YouTube channel and code, no slide deck archive |

`[unverified]` **YouTube.** Several playlists and individual lectures on hypergraphs and
higher-order networks are indexed by search engines — a "Hypergraph Theory" playlist, and multiple
recorded lectures by Ginestra Bianconi on the topology and dynamics of higher-order networks. Direct
fetches of `youtube.com` watch and playlist URLs on 2026-09-20 returned only site chrome, so **no
YouTube URL is listed here as verified**. The tutorial video linked from the KAIST tutorial page is
the exception, because the tutorial page itself vouches for it. A future run with a working
YouTube-metadata path should fill this row in.

---

## 8. What is still missing

1. **A knowledge-hypergraph tutorial.** Nothing at any venue covers n-ary or hyper-relational KGs as
   teaching material. The two surveys ([Wei et al. 2025](https://arxiv.org/abs/2506.08970); [Lu,
   Tupikina and Alam 2026](https://arxiv.org/abs/2506.05626)) are the raw material for one.
2. **A standing university course.** One special-topic course, run once.
3. **A hands-on n-ary lab.** The library tutorials teach unlabelled hyperedges; none teaches
   role-labelled facts, because no library exposes incidence roles as a first-class concept — finding
   1 of [README.md](README.md).
4. **A Dagstuhl for n-ary knowledge representation** (§5).
5. **An archived, citable video corpus.** Everything except the KAIST tutorial video is
   uncatalogued.

**What this KB can do cheaply.** The hackathon and the TDL challenge both show the pattern: *make
the teaching artefact a contribution to shared software*. A "lift a Wikidata subgraph into a
role-labelled HIF file" exercise, built on
[getting-started-toolchain.md](getting-started-toolchain.md), would be the missing n-ary lab and
would produce a reusable dataset at the same time.

## Sources

- Chen, C. "Teaching" (DATA 890-003 *Graphs and Hypergraphs*, Fall 2024; DATA 890-003 *Machine Learning with Graphs*, Fall 2025; DATA 110), University of North Carolina at Chapel Hill. Checked 2026-09-20. <https://tarheels.live/canc/teaching/>
- Shin, K. Personal page listing courses (AI607 *Graph Mining and Social Network Analysis*, 2019–2026; AI506 *Data Mining and Search*, 2020–2026) and tutorials. KAIST. Checked 2026-09-20. <https://kijungs.github.io/>
- Kim, S., Antelmi, A., Lee, S. Y., Polato, M., Gao, Y., Shin, K. "Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide" (tutorial; KDD 2024, ICDM 2024, AAAI 2025, CIKM 2025). Checked 2026-09-20. <https://sites.google.com/view/hnn-tutorial>
- Kim, S., Lee, S. Y., Gao, Y., Antelmi, A., Polato, M., Shin, K. "A Survey on Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide." KDD 2024; arXiv:2404.01039 (v1 1 Apr 2024, rev. 25 Jul 2024). <https://arxiv.org/abs/2404.01039> ; <https://dl.acm.org/doi/abs/10.1145/3637528.3671457>
- "A Tutorial on Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide." CIKM 2025, pp. 6829–6832. <https://doi.org/10.1145/3746252.3761449>
- Lee, G., Yoo, J., Shin, K. "Mining of Real-world Hypergraphs: Patterns, Tools, and Generators" (tutorial; CIKM 2022, ICDM 2022, WWW 2023, KDD 2023). Checked 2026-09-20. <https://sites.google.com/view/hypergraph-tutorial> ; CIKM 2022 slide deck <http://dmlab.kaist.ac.kr/~kijungs/papers/tutorialCIKM2022.pdf>
- Lee, G., Bu, F., Eliassi-Rad, T., Shin, K. "A Survey on Hypergraph Mining: Patterns, Tools, and Generators." arXiv:2401.08878. <https://arxiv.org/abs/2401.08878>
- Papillon, M., Hajij, M. et al. "ICML 2023 Topological Deep Learning Challenge: Design and Results." PMLR 221:3–8; arXiv:2309.15188. <https://proceedings.mlr.press/v221/papillon23a.html> ; <https://arxiv.org/abs/2309.15188>
- Bernárdez, G., Telyatnikov, L., Montagna, M. et al. "ICML Topological Deep Learning Challenge 2024: Beyond the Graph Domain." Proceedings of the GRaM Workshop at ICML 2024; arXiv:2409.05211, 8 Sep 2024. <https://arxiv.org/abs/2409.05211>
- Schloss Dagstuhl. Seminar 21352, "Higher-Order Graph Models: From Theoretical Foundations to Machine Learning," 29 Aug – 1 Sep 2021. <https://www.dagstuhl.de/seminars/seminar-calendar/seminar-details/21352>
- Schloss Dagstuhl. Seminar 26411, "Large Language Models Meet Knowledge Graphs," 4–9 Oct 2026. <https://www.dagstuhl.de/26411>
- Schloss Dagstuhl. Seminar 25291, "(Actual) Neurosymbolic AI: Combining Deep Learning and Knowledge Graphs." <https://www.dagstuhl.de/seminars/seminar-calendar/seminar-details/25291>
- Schloss Dagstuhl. Seminar 22372, "Knowledge Graphs and Their Role in the Knowledge Engineering of the 21st Century." <https://www.dagstuhl.de/22372>
- HIF-standard repository, `tutorials/` directory listing, 36 stars, MIT licence. Checked 2026-09-20. <https://github.com/HIF-org/HIF-standard/tree/main/tutorials>
- HyperNetX repository, 716 stars, BSD-3-Clause, `tutorials/` folder with six basic notebooks. Checked 2026-09-20. <https://github.com/pnnl/HyperNetX> ; <https://hypernetx.readthedocs.io/>
- XGI documentation, "XGI in 1 minute 🚀", version 0.10.2 (released 15 May 2026). Checked 2026-09-20. <https://xgi.readthedocs.io/en/stable/api/tutorials/getting_started_1.html>
- Bianconi, G. *Higher-Order Networks.* Cambridge Elements in the Structure and Dynamics of Complex Networks, Cambridge University Press, online 23 Nov 2021. <https://doi.org/10.1017/9781108770996>
- Schaub, M. T. "HIntNets — Higher-order interactions and Laplacian dynamics in complex networks," project page, RWTH Aachen. Checked 2026-09-20. <https://michaelschaub.github.io/HIntNets/>
- NetSci 2025 focus sessions and "Higher order networks 1 / 2" parallel sessions. Checked 2026-09-20. <https://netsci2025.github.io/focus_sessions/>
- Chodrow, P. et al. "A Higher Order Hackathon — A Blue Start at NetSci 2026," 31 May 2026. <https://www.philchodrow.prof/higher-order-hackathon/>
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. "A Survey of Link Prediction in N-ary Knowledge Graphs." EMNLP 2025; arXiv:2506.08970. <https://arxiv.org/abs/2506.08970>
- Lu, X., Tupikina, L., Alam, M. "Two-Dimensional Taxonomy for n-Ary Knowledge Representation Learning Methods." IEEE TKDE 2026; arXiv:2506.05626. <https://arxiv.org/abs/2506.05626>
