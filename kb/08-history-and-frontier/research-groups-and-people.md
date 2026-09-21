---
title: Research groups and people working on knowledge hypergraphs
type: survey
status: draft
tags: [people, groups, community, affiliations, ecosystem]
created: 2026-09-20
updated: 2026-09-21
---

# Who works on knowledge hypergraphs

Affiliations as stated by the **latest source checked on 2026-09-20**. Academic affiliations change
often; anything not confirmed from a primary page (personal site, lab page, institutional directory,
paper front matter) is marked `[unverified]`. Nobody here is listed from memory.

Grouped by the community they come from, because that predicts what they mean by "hypergraph" —
see [machine-learning-era.md](machine-learning-era.md) for the four-community picture.

---

## 1. Knowledge-hypergraph embedding and reasoning

### Bahare Fatemi and David Poole

The pair who put "knowledge hypergraph" into the embedding literature
([arXiv:1906.00137](https://arxiv.org/abs/1906.00137), IJCAI 2020;
[ReAlE, arXiv:2102.09557](https://arxiv.org/abs/2102.09557)), with Perouz Taslakian and David
Vazquez (then ServiceNow Research / Element AI).

- **Bahare Fatemi** — PhD, University of British Columbia, supervised by David Poole, graduated
  May 2023; now **Senior Research Scientist, Google Research (Graph Mining team)**
  ([ResearchGate profile](https://www.researchgate.net/profile/Bahare-Fatemi);
  [UBC CS theses 2023](https://www.cs.ubc.ca/cs-theses/cs-theses-2023)). Her current work is on
  graphs and language models rather than knowledge hypergraphs specifically.
- **David Poole** — **Professor Emeritus, Department of Computer Science, University of British
  Columbia** (faculty since 1988; retired from administrative duties and undergraduate teaching as
  of July 2024, research continuing). Areas: knowledge representation, reasoning under uncertainty,
  statistical relational AI, lifted inference
  ([UBC page](https://www.cs.ubc.ca/~poole/)).
- **ServiceNow Research** hosts the publication records for both KHG papers
  ([record](https://www.servicenow.com/research/publication/bahare-fatemi-know-jmlr2023.html)).

### Mikhail (Michael) Galkin

Author of StarE (EMNLP 2020), WD50K, the inductive-hyper-relational ISWC 2021 best paper, ULTRA
(ICLR 2024) and HYPER (arXiv, Jun 2025; ICLR 2026). **Research Scientist at Google**, working on graph ML, knowledge
graphs and graph foundation models; speaker at the ICML 2026 "Graph Foundation Models" workshop
([personal site](https://migalkin.github.io/);
[Google at ICML 2026](https://research.google/conferences-and-events/google-at-icml-2026/)).
Previously Mila / McGill and Intel AI Labs `[unverified]`.

### Xingyue Huang, Michael M. Bronstein, İsmail İlkan Ceylan

The Oxford-centred line on relational hypergraphs and expressivity: "Link Prediction with Relational
Hypergraphs" ([arXiv:2402.04062](https://arxiv.org/abs/2402.04062), with Miguel Romero Orth and
Pablo Barceló) and HYPER ([arXiv:2506.12362](https://arxiv.org/abs/2506.12362), with Galkin).
Institutional affiliations are not stated on the arXiv abstract pages checked `[unverified]`;
the HYPER implementation is at [github.com/HxyScotthuang/HYPER](https://github.com/HxyScotthuang/HYPER).

### Paolo Rosso, Dingqi Yang, Philippe Cudré-Mauroux — the Fribourg line

Authors of HINGE / "Beyond Triplets" (WWW 2020), the paper that named the **hyper-relational**
formalisation ([DOI 10.1145/3366423.3380257](https://doi.org/10.1145/3366423.3380257)).

- **Philippe Cudré-Mauroux** — **Full Professor of Computer Science, University of Fribourg**,
  director of the **eXascale Infolab** (Bd de Pérolles 90, 1700 Fribourg); Big Data infrastructures,
  systems for AI, emergent semantics ([exascale.info](https://exascale.info/phil/);
  [UniFR directory](https://www.unifr.ch/directory/en/people/10710/c0027)).
- **Paolo Rosso** — listed as an **alumnus** of eXascale Infolab, where he was a PhD student under
  Cudré-Mauroux on KG embeddings; current position not stated on the lab page `[unverified]`
  ([lab page](https://exascale.info/members/paolo-rosso/)).
- **Dingqi Yang** — formerly eXascale Infolab, Fribourg; now at the **University of Macau**
  `[unverified]` (the THOR preprint's PDF metadata gives a Macau, China contact, which is
  suggestive but not a primary affiliation statement). Continues the line with schema-aware
  hyper-relational embeddings, **VITA** ([arXiv:2505.11803](https://arxiv.org/abs/2505.11803), with
  ChongIn Un, Yuhuan Lu, Tianyue Yang) and **THOR**
  ([arXiv:2602.05424](https://arxiv.org/abs/2602.05424), with Weijian Yu and Yuhuan Lu). Also a
  co-author of the *ACM CSUR* hypergraph representation-learning survey
  ([DOI 10.1145/3605776](https://doi.org/10.1145/3605776)).

### Saiping Guan and the CAS group

The n-ary relational data line: NaLP (WWW 2019,
[DOI 10.1145/3308558.3313414](https://doi.org/10.1145/3308558.3313414)) and the first comprehensive
survey of the area.

**Saiping Guan, Xiaolong Jin, Jiafeng Guo, Xueqi Cheng, Jiyao Wei, Da Li** — affiliations as printed
on the EMNLP 2025 survey: **School of Computer Science and Technology, University of Chinese Academy
of Sciences** and the **Key Laboratory of Network Data Science and Technology, Institute of
Computing Technology, Chinese Academy of Sciences**
([Wei et al., EMNLP 2025, pp. 28545–28567](https://aclanthology.org/2025.emnlp-main.1451/)).
Survey repository: [github.com/JiyaoWei/LP_NKGs](https://github.com/JiyaoWei/LP_NKGs).

---

## 2. Hypergraph learning and hypergraph foundation models

### Yue Gao, Yifan Feng and iMoon-Lab, Tsinghua University

The single most productive group in the field, and unusual for spanning learning, foundation models
and RAG.

- **Yue Gao** — Tsinghua University; **Yifan Feng** — Tsinghua University. Lab: **iMoon-Lab**, which
  maintains **DHG / DeepHypergraph**, a PyTorch library for graph and hypergraph computation
  ([github.com/iMoonLab/DeepHypergraph](https://github.com/iMoonLab/DeepHypergraph)) and the
  original HGNN code ([github.com/iMoonLab/HGNN](https://github.com/iMoonLab/HGNN)).
- Output: HGNN (AAAI 2019, [DOI 10.1609/aaai.v33i01.33013558](https://doi.org/10.1609/aaai.v33i01.33013558)),
  HGNN⁺ (*TPAMI* 45(3), 2023), "Hypergraph Learning: Methods and Practices" (*TPAMI*),
  "Hypergraph Computation" (*Engineering* 40:188–201, 2024, with Shuyi Ji, Xiangmin Han, Qionghai
  Dai, [DOI 10.1016/j.eng.2024.04.017](https://doi.org/10.1016/j.eng.2024.04.017)), **Hyper-FM**
  (*TPAMI* 48:4063–4080, Apr 2026), **Hyper-RAG** (*Nature Communications* 17:5778, 27 Apr 2026),
  **Hyper-KGGen / HyperDocRED** ([arXiv:2602.19543](https://arxiv.org/abs/2602.19543)) and
  **Hypergraph as Language** ([arXiv:2605.21858](https://arxiv.org/abs/2605.21858)). Frequent
  co-authors: Shaoyi Du (Xi'an Jiaotong University), Shihui Ying, Xiangmin Han, Jun-Hai Yong,
  Chuan Shi, Han Hu.
- Gao is also a signatory of the ICML 2024 topological-deep-learning position paper
  ([arXiv:2402.08871](https://arxiv.org/abs/2402.08871)) — a visible bridge between the Chinese
  hypergraph-learning community and the TDL community.

### Kijung Shin, Geon Lee, Fanchen Bu (hypergraph mining)

Authors of "A Survey on Hypergraph Mining: Patterns, Tools, and Generators" (*ACM CSUR* 57,
24 Mar 2025, [DOI 10.1145/3719002](https://doi.org/10.1145/3719002)) and the KDD 2024 HGNN survey
([DOI 10.1145/3637528.3671457](https://doi.org/10.1145/3637528.3671457)). KAIST `[unverified]`.

### Tina Eliassi-Rad

Co-author of the hypergraph-mining survey and co-organiser of Dagstuhl Seminar 21352 on higher-order
graph models ([Dagstuhl 21352](https://www.dagstuhl.de/seminars/seminar-calendar/seminar-details/21352)).
Northeastern University `[unverified]`.

---

## 3. Higher-order network science

### Federico Battiston

Central figure of the physics wing: the *Physics Reports* 874 review (2020), the *Nature Physics*
perspective (2021), and the Hypergraphx library and data repository. **Central European University**
(the CEU research portal hosts the *Physics Reports* record;
[CEU portal](https://research.ceu.edu/en/publications/networks-beyond-pairwise-interactions-structure-and-dynamics/)).
Hypergraphx-data (2026) lists him with Quintino Francesco Lotito, Lorenzo Betti, Berné Nortier and
Alberto Montresor ([DOI 10.1093/comnet/cnag014](https://doi.org/10.1093/comnet/cnag014)).

### The XGI team

XGI (CompleX Group Interactions) is the NSF-supported Python package for higher-order networks
([github.com/xgi-org/xgi](https://github.com/xgi-org/xgi);
[JOSS 8(85):5162](https://joss.theoj.org/papers/10.21105/joss.05162)). Authors on the JOSS paper,
with affiliations from their own pages where found:

| Person | Affiliation (source) |
|---|---|
| **Nicholas W. Landry** | Assistant Professor, University of Virginia ([UVA profile](https://as.virginia.edu/faculty-profile/nicholas-landry); [personal site/CV](https://nwlandry.com/assets/docs/CV.pdf)) |
| **Maxime Lucas** | University of Namur / Namur Institute for Complex Systems `[unverified]` ([personal site](https://maximelucas.github.io/)) |
| **Iacopo Iacopini** | Network Science Institute, Northeastern University London ([NU London profile](https://www.nulondon.ac.uk/people/iacopo-iacopini/)) |
| **Alice Patania** | Assistant Professor, Department of Mathematics and Statistics, University of Vermont; core faculty, Vermont Complex Systems Institute ([UVM profile](https://www.uvm.edu/cems/mathstat/profile/alice-patania)) |
| **Leo Torres** | Max Planck Institute for Mathematics in the Sciences `[unverified]` ([personal site](https://leotrs.com/)) |
| **Giovanni Petri**, **Alice Schwarze** | co-authors on the JOSS paper; current affiliations not checked `[unverified]` |

Note a correction to a common assumption: **Phil Chodrow is not listed among the XGI JOSS authors.**
He is a separate node in the same community — **Assistant Professor, Department of Computer Science,
Middlebury College** (on leave for the 2026–2027 academic year), working on random hypergraph models
and community detection in hypergraphs, and co-organiser with Alyssa Smith and Nicholas Landry of
the higher-order hackathon at NetSci 2026
([philchodrow.prof](https://www.philchodrow.prof/);
[hackathon page](https://www.philchodrow.prof/higher-order-hackathon/)).

### The PNNL hypernetwork-science team

Pacific Northwest National Laboratory maintains **HyperNetX**, the first widely used Python
hypergraph library (first released 3 Jan 2019). The JOSS 9(95):6016 paper (9 Mar 2024) authors are
**Brenda Praggastis, Sinan Aksoy, Dustin Arendt, Mark Bonicillo, Cliff Joslyn, Emilie Purvine,
Madelyn Shapiro, Ji Young Yun** ([JOSS](https://joss.theoj.org/papers/10.21105/joss.06016)); the
group's programme statement is "Hypernetwork Science"
([arXiv:2003.11782](https://arxiv.org/abs/2003.11782)). Affiliation PNNL is stated in the OSTI DOE
CODE record ([OSTI](https://www.osti.gov/doecode/biblio/22160)); individual affiliations are not
printed on the JOSS landing page `[unverified]`.

### The HIF authors

The interchange-format effort deliberately spans the competing libraries: **Martín Coll, Cliff A.
Joslyn, Nicholas W. Landry, Quintino Francesco Lotito, Audun Myers, Joshua Pickard, Brenda
Praggastis, Przemysław Szufel** ([*Network Science* 13:e21, 2025](https://doi.org/10.1017/nws.2025.10018)).
**Przemysław Szufel** (SGH Warsaw School of Economics `[unverified]`) also maintains
**SimpleHypergraphs.jl** ([github.com/pszufe/SimpleHypergraphs.jl](https://github.com/pszufe/SimpleHypergraphs.jl))
with **Bogumił Kamiński**, whose hypergraph-modularity clustering work is built into it; the HIF
reference repository lives at [github.com/HIF-org/HIF-standard](https://github.com/HIF-org/HIF-standard).

### Austin Benson

Author of "Simplicial closure and higher-order link prediction" (*PNAS* 115(48), 2018), which
defined higher-order link prediction and shipped 19 datasets that are still in use. Formerly
Assistant Professor of Computer Science at **Cornell University**
([Cornell page](https://www.cs.cornell.edu/~arb/)); secondary sources describe him as having left
academia for quantitative finance in New York `[unverified]` — the Cornell page was still live at
the check on 2026-09-20, so treat the current position as unconfirmed.

---

## 4. Topological deep learning

### Mustafa Hajij and the pyt-team / TopoX consortium

**Mustafa Hajij** — **Assistant Professor, University of San Francisco**
([USF/ResearchGate profile](https://www.researchgate.net/profile/Mustafa-Hajij);
[LinkedIn](https://www.linkedin.com/in/mustafa-hajij/)). Lead author of **TopoX**
([arXiv:2402.02441](https://arxiv.org/abs/2402.02441); *JMLR* 25), the suite of TopoNetX,
TopoEmbedX and TopoModelX covering "hypergraphs, simplicial, cellular, path and combinatorial
complexes" ([github.com/pyt-team/TopoModelX](https://github.com/pyt-team/TopoModelX)). TopoX has
43 listed co-authors including Mathilde Papillon, Nina Miolane, Theodore Papamarkou, Michael T.
Schaub, Simone Scardapane and Karthikeyan Natesan Ramamurthy.

The **ICML 2024 position paper** ([arXiv:2402.08871](https://arxiv.org/abs/2402.08871)) has 22
authors, led by **Theodore Papamarkou** and including **Tolga Birdal, Michael Bronstein, Gunnar
Carlsson, Justin Curry, Yue Gao, Mustafa Hajij, Roland Kwitt, Pietro Liò, Paolo Di Lorenzo**.
That author list is the best single snapshot of who is bridging TDL and hypergraph learning.

### Michael T. Schaub

Co-author of the *SIAM Review* "What Are Higher-Order Networks?" ([DOI 10.1137/21M1414024](https://doi.org/10.1137/21M1414024)),
of the *PNAS* higher-order link prediction paper, and of TopoX; co-organiser of Dagstuhl 21352.
RWTH Aachen `[unverified]`.

---

## 5. LLM-era systems

### Haoran Luo

Author of **HyperGraphRAG** (NeurIPS 2025). **Research Fellow, College of Computing and Data
Science, Nanyang Technological University**; previously a CS PhD student at **Beijing University of
Posts and Telecommunications** ([personal homepage](https://lhrlab.github.io/)). The HyperGraphRAG
author list spans BUPT, NTU, the Beijing Institute of Computer Technology and Application, the
National University of Singapore, China Mobile Research Institute and Beijing Anzhen Hospital
([paper](https://arxiv.org/abs/2503.21322)). Code: [github.com/LHRLAB/HyperGraphRAG](https://github.com/LHRLAB/HyperGraphRAG).

### Xiangjun Zai, Xingyu Tan and co-authors

PRoH (WWW 2026, [arXiv:2510.12434](https://arxiv.org/abs/2510.12434)) and DocTrace
([arXiv:2606.10921](https://arxiv.org/abs/2606.10921)), with Xiaoyang Wang, Wenjie Zhang, Chen Chen,
Qing Liu and Xiwei Xu. Affiliations not stated on the arXiv abstract pages checked `[unverified]`;
the recurring co-author set suggests an Australian university–national-laboratory collaboration,
which should be confirmed from the papers' front matter before being asserted.

### Maciej Besta and Torsten Hoefler (ETH Zürich)

"Higher-Order Graph Databases" ([arXiv:2506.19661](https://arxiv.org/abs/2506.19661), 24 Jun 2025),
with Shriram Chandran, Jakub Cudak, Patrick Iff, Marcin Copik, Robert Gerstenberger, Tomasz Szydlo
and Jürgen Müller. Hoefler leads the Scalable Parallel Computing Laboratory at ETH Zürich
`[unverified]`; the group is the main systems-side presence in this field.

---

## 6. Database and industry systems

### TypeDB (formerly Grakn)

**Haikal Pribadi** — original author and founder; the company was founded in 2015 as Grakn Labs
Ltd., later Vaticle, now TypeDB; Grakn 0.1.1 released 9 September 2016; renamed TypeDB in 2021;
stable release **3.13.0 on 8 September 2026**, Mozilla Public License 2.0
([Wikipedia, TypeDB](https://en.wikipedia.org/wiki/TypeDB), checked 2026-09-20;
[Crunchbase profile](https://www.crunchbase.com/person/haikal-pribadi)). The data model is an
entity–relation–attribute type system in which a relation type `relates` several **roles**, which
makes it the most mature commercial n-ary/hyper-relational store.

### HypergraphDB

**Borislav Iordanov** (Kobrix Software) — "HyperGraphDB: A Generalized Graph Database," WAIM 2010
Workshops, LNCS, pp. 25–36 ([Springer](https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3);
[hypergraphdb.org](http://hypergraphdb.org/)). An embedded Java database whose atoms are hyperedges
that may themselves contain hyperedges, with a customisable type system and OWL/RDF/Prolog support
([repository README](https://github.com/hypergraphdb/hypergraphdb)). The project's release cadence
could not be established in this run `[unverified]`; treat it as historically important rather than
actively maintained until checked. Personal site: [bolerio.me](http://bolerio.me/).

### OpenCog Hyperon

**Ben Goertzel** and collaborators (SingularityNET, TrueAGI, the Artificial Superintelligence
Alliance). The Atomspace is a self-modifying **metagraph** — hyperedges that may contain hyperedges
— paired with the **MeTTa** rewriting language
([hyperon.opencog.org](https://hyperon.opencog.org/);
[arXiv:2310.18318](https://arxiv.org/abs/2310.18318);
[arXiv:2112.08272](https://arxiv.org/abs/2112.08272);
implementation at [github.com/trueagi-io/hyperon-experimental](https://github.com/trueagi-io/hyperon-experimental)).
An "OpenCog Hyperon Alpha" release has been announced and a production stack was targeted for late
2025; the project describes itself as at an active pre-alpha stage of development
([SingularityNET announcement](https://medium.com/singularitynet/announcing-the-release-of-opencog-hyperon-alpha-38941f8f389f)).
A 2025 AGI-conference chapter, "OpenCog Hyperon: A Practical Path to Beneficial AGI and ASI," exists
([Springer](https://dl.acm.org/doi/abs/10.1007/978-3-032-00686-8_18)). This strand is the most
distant from the mainstream KHG literature and cites it barely at all.

---

## 7. How to use this list

- **Read the affiliation as a clue to the formalism.** Fribourg/CAS/Google → triple+qualifiers or
  ordered tuples. Tsinghua/PNNL/CEU → undirected set hyperedges. ETH → storage systems. TypeDB →
  typed roles.
- **Cross-community co-authorship is the signal to watch.** The ICML 2024 position paper, the HIF
  author list and the HYPER author list are the three documents where communities that used to
  ignore each other appear together.
- Groups, libraries and datasets in more operational detail are in
  [../09-ecosystem/software-libraries.md](../09-ecosystem/software-libraries.md); venues are in
  [venues-and-community-events.md](venues-and-community-events.md).

## Sources

- Fatemi, B. ResearchGate profile (UBC PhD). https://www.researchgate.net/profile/Bahare-Fatemi ; UBC CS Theses 2023. https://www.cs.ubc.ca/cs-theses/cs-theses-2023
- ServiceNow Research. Publication records for the Fatemi et al. knowledge-hypergraph papers. https://www.servicenow.com/research/publication/bahare-fatemi-know-jmlr2023.html
- Poole, D. Personal page, UBC Department of Computer Science. https://www.cs.ubc.ca/~poole/
- Galkin, M. Personal site. https://migalkin.github.io/ ; Google at ICML 2026. https://research.google/conferences-and-events/google-at-icml-2026/
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. HYPER implementation. https://github.com/HxyScotthuang/HYPER
- Cudré-Mauroux, P. eXascale Infolab. https://exascale.info/phil/ ; University of Fribourg directory. https://www.unifr.ch/directory/en/people/10710/c0027
- eXascale Infolab. Paolo Rosso (alumnus) page. https://exascale.info/members/paolo-rosso/
- Rosso, P., Yang, D., Cudré-Mauroux, P. "Beyond Triplets." WWW 2020. https://doi.org/10.1145/3366423.3380257
- Un, C., Lu, Y., Yang, T., Yang, D. "VITA." arXiv:2505.11803. https://arxiv.org/abs/2505.11803 ; Yu, W., Lu, Y., Yang, D. "THOR." arXiv:2602.05424. https://arxiv.org/abs/2602.05424
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. "A Survey of Link Prediction in N-ary Knowledge Graphs." EMNLP 2025. https://aclanthology.org/2025.emnlp-main.1451/ ; repository https://github.com/JiyaoWei/LP_NKGs
- Guan, S., Jin, X., Wang, Y., Cheng, X. "Link Prediction on N-ary Relational Data." WWW 2019. https://doi.org/10.1145/3308558.3313414
- iMoon-Lab. DeepHypergraph. https://github.com/iMoonLab/DeepHypergraph ; HGNN. https://github.com/iMoonLab/HGNN
- Gao, Y., Ji, S., Han, X., Dai, Q. "Hypergraph Computation." *Engineering* 40:188–201, 2024. https://doi.org/10.1016/j.eng.2024.04.017
- Gao, Y. et al. "Hypergraph Foundation Model." *IEEE TPAMI* 48:4063–4080, 2026. https://doi.org/10.1109/TPAMI.2025.3647504
- Feng, Y. et al. "Hyper-RAG." *Nature Communications* 17(1):5778, 27 Apr 2026. https://doi.org/10.1038/s41467-026-71411-1
- Lee, G., Bu, F., Eliassi-Rad, T., Shin, K. "A Survey on Hypergraph Mining." *ACM CSUR* 57, 2025. https://doi.org/10.1145/3719002
- Kim, S., Lee, G., Gao, Y., Antelmi, A., Polato, M., Shin, K. "A Survey on Hypergraph Neural Networks." KDD 2024. https://doi.org/10.1145/3637528.3671457
- Schloss Dagstuhl. Seminar 21352, "Higher-Order Graph Models." https://www.dagstuhl.de/seminars/seminar-calendar/seminar-details/21352
- Battiston, F. et al. "Networks beyond pairwise interactions." *Physics Reports* 874, 2020. https://research.ceu.edu/en/publications/networks-beyond-pairwise-interactions-structure-and-dynamics/
- Lotito, Q. F., Betti, L., Nortier, B., Montresor, A., Battiston, F. "Hypergraphx-data." *Journal of Complex Networks* 14, 2026. https://doi.org/10.1093/comnet/cnag014
- Landry, N. W. et al. "XGI." *JOSS* 8(85):5162, 2023. https://joss.theoj.org/papers/10.21105/joss.05162 ; repository https://github.com/xgi-org/xgi
- Landry, N. W. University of Virginia profile. https://as.virginia.edu/faculty-profile/nicholas-landry ; CV https://nwlandry.com/assets/docs/CV.pdf
- Iacopini, I. Northeastern University London profile. https://www.nulondon.ac.uk/people/iacopo-iacopini/
- Patania, A. University of Vermont profile. https://www.uvm.edu/cems/mathstat/profile/alice-patania
- Lucas, M. Personal site. https://maximelucas.github.io/ ; Torres, L. Personal site. https://leotrs.com/
- Chodrow, P. Personal site. https://www.philchodrow.prof/ ; higher-order hackathon. https://www.philchodrow.prof/higher-order-hackathon/
- Praggastis, B., Aksoy, S., Arendt, D., Bonicillo, M., Joslyn, C., Purvine, E., Shapiro, M., Yun, J. Y. "HyperNetX." *JOSS* 9(95):6016, 2024. https://joss.theoj.org/papers/10.21105/joss.06016 ; OSTI DOE CODE record. https://www.osti.gov/doecode/biblio/22160
- Coll, M. et al. "HIF." *Network Science* 13:e21, 2025. https://doi.org/10.1017/nws.2025.10018 ; https://github.com/HIF-org/HIF-standard ; SimpleHypergraphs.jl https://github.com/pszufe/SimpleHypergraphs.jl
- Benson, A. R. Cornell page. https://www.cs.cornell.edu/~arb/ ; Benson et al., *PNAS* 115(48), 2018. https://arxiv.org/abs/1802.06916
- Hajij, M. ResearchGate profile. https://www.researchgate.net/profile/Mustafa-Hajij ; LinkedIn. https://www.linkedin.com/in/mustafa-hajij/ ; TopoX arXiv:2402.02441. https://arxiv.org/abs/2402.02441 ; TopoModelX https://github.com/pyt-team/TopoModelX
- Papamarkou, T. et al. ICML 2024 position paper. https://arxiv.org/abs/2402.08871
- Bick, C., Gross, E., Harrington, H. A., Schaub, M. T. "What Are Higher-Order Networks?" *SIAM Review* 65(3), 2023. https://doi.org/10.1137/21M1414024
- Luo, H. Personal homepage. https://lhrlab.github.io/ ; HyperGraphRAG arXiv:2503.21322. https://arxiv.org/abs/2503.21322 ; code https://github.com/LHRLAB/HyperGraphRAG
- Zai, X. et al. PRoH. https://arxiv.org/abs/2510.12434 ; DocTrace. https://arxiv.org/abs/2606.10921
- Besta, M. et al. "Higher-Order Graph Databases." arXiv:2506.19661. https://arxiv.org/abs/2506.19661
- Wikipedia. "TypeDB" (checked 2026-09-20). https://en.wikipedia.org/wiki/TypeDB ; Crunchbase, Haikal Pribadi. https://www.crunchbase.com/person/haikal-pribadi
- Iordanov, B. "HyperGraphDB: A Generalized Graph Database." WAIM 2010 Workshops. https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3 ; http://hypergraphdb.org/ ; https://github.com/hypergraphdb/hypergraphdb ; http://bolerio.me/
- OpenCog Hyperon. https://hyperon.opencog.org/ ; Goertzel, B. et al. arXiv:2310.18318. https://arxiv.org/abs/2310.18318 ; arXiv:2112.08272. https://arxiv.org/abs/2112.08272 ; https://github.com/trueagi-io/hyperon-experimental ; SingularityNET, "Announcing the Release of OpenCog Hyperon Alpha." https://medium.com/singularitynet/announcing-the-release-of-opencog-hyperon-alpha-38941f8f389f ; "OpenCog Hyperon: A Practical Path to Beneficial AGI and ASI," AGI 2025. https://dl.acm.org/doi/abs/10.1007/978-3-032-00686-8_18
- Antelmi, A., Cordasco, G., Polato, M., Scarano, V., Spagnuolo, C., Yang, D. "A Survey on Hypergraph Representation Learning." *ACM CSUR* 56(1), 2023. https://doi.org/10.1145/3605776
