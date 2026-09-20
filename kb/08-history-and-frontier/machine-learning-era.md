---
title: The machine-learning era — three communities converge on the hyperedge (2006–2023)
type: survey
status: draft
tags: [history, hypergraph-learning, embeddings, hgnn, higher-order-networks, topological-deep-learning, benchmarks]
created: 2026-09-20
updated: 2026-09-20
---

# The machine-learning era, 2006–2023

Between 2006 and 2023 three largely separate research communities each arrived at the hyperedge and
built a stack on top of it. They had different motivations, different datasets, different journals,
and — for over a decade — almost no shared citations. Understanding which community a paper comes
from explains most of the terminological confusion in the field.

| Community | Object | Typical venue | Key question |
|---|---|---|---|
| **Hypergraph learning / spectral ML** | undirected, unlabelled hyperedge (a set of vertices) | NIPS/NeurIPS, TPAMI, AAAI | How do I do semi-supervised learning on a set system? |
| **KG embedding / n-ary link prediction** | labelled, ordered or role-annotated hyperedge (a *fact*) | IJCAI, WWW, EMNLP, ISWC | How do I score the plausibility of an unseen n-ary fact? |
| **Higher-order network science** | undirected hyperedge (a group interaction) | *Physics Reports*, *Nature Physics*, *SIAM Review*, NetSci | What dynamics and structure do groups produce that pairs cannot? |

Dated events: [timeline.md](timeline.md). What came before: the mathematics in
[origins-hypergraph-theory.md](origins-hypergraph-theory.md), the representational argument in
[knowledge-representation-lineage.md](knowledge-representation-lineage.md).

## 1. 2006: spectral hypergraph learning

The founding paper of hypergraph machine learning is:

> Zhou, D., Huang, J., Schölkopf, B. "Learning with Hypergraphs: Clustering, Classification, and
> Embedding." *Advances in Neural Information Processing Systems 19* (NIPS 2006)
> ([NIPS proceedings](https://papers.nips.cc/paper/3128-learning-with-hypergraphs-clustering-classification-and-embedding))

Its motivating sentence is the field's slogan: "Naively squeezing the complex relationships into
pairwise ones will inevitably lead to loss of information." Technically it generalises normalised
spectral clustering from graphs to hypergraphs by defining a hypergraph Laplacian from the incidence
matrix and vertex/edge degree matrices, then derives clustering, transductive classification and
embedding from it.

Two things about this lineage matter for knowledge hypergraphs:

- Its hyperedges are **unlabelled sets**. There is no relation type, no argument order, no role. The
  objects are "co-occurrence groups" (images sharing an attribute, documents sharing an author), not
  facts. Everything built directly on this line inherits that assumption.
- The **incidence matrix plus a Laplacian** became the standard computational interface, which is
  why so much later work reduces to a (weighted) clique expansion in disguise — the thing the 2026
  expressivity results quantify (§5).

The line was consolidated in Gao et al., "Hypergraph Learning: Methods and Practices," *IEEE TPAMI*
(first available 2020, issue 2021)
([DOI 10.1109/TPAMI.2020.3039374](https://doi.org/10.1109/TPAMI.2020.3039374)), and later in Gao,
Ji, Han, Dai, "Hypergraph Computation," *Engineering* 40:188–201, 2024
([DOI 10.1016/j.eng.2024.04.017](https://doi.org/10.1016/j.eng.2024.04.017)).

## 2. 2016–2021: the knowledge-hypergraph embedding wave

This is the line that actually produced the term "knowledge hypergraph." It is a sequence of five
moves, each fixing a defect of the previous one.

### 2.1 m-TransH (2016) — the problem statement

Wen, Li, Mao, Chen, Zhang, "On the Representation and Embedding of Knowledge Bases Beyond Binary
Relations," IJCAI 2016 ([arXiv:1604.08642](https://arxiv.org/abs/1604.08642), Apr 2016). Argues that
the standard star/clique conversion of an n-ary Freebase fact into triples loses information,
generalises TransH to instances of n-ary relations, and releases **JF17K**, derived from Freebase
CVTs. Every later benchmark in the line descends from this decision.

### 2.2 NaLP (2019) — role–value pairs

Guan, Jin, Wang, Cheng, "Link Prediction on N-ary Relational Data," WWW 2019, pp. 583–593
([DOI 10.1145/3308558.3313414](https://doi.org/10.1145/3308558.3313414)). Represents an n-ary fact
as a *set of role–value pairs* and scores the compatibility of the whole set. This removes the
fixed-order assumption and reintroduces Minsky's slots (see
[knowledge-representation-lineage.md](knowledge-representation-lineage.md)).

### 2.3 HINGE / StarE (2020) — "hyper-relational," and the benchmark crisis

Two papers in the same year fix the shape of the mainstream formalisation:

- Rosso, Yang, Cudré-Mauroux, "Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link
  Prediction" (HINGE), WWW 2020, pp. 1885–1896
  ([DOI 10.1145/3366423.3380257](https://doi.org/10.1145/3366423.3380257)). A fact is a **main
  triple plus key–value qualifiers** — the Wikidata shape — and the model preserves that asymmetry
  instead of flattening it into a bag.
- Galkin, Trivedi, Maheshwari, Usbeck, Lehmann, "Message Passing for Hyper-Relational Knowledge
  Graphs" (StarE), EMNLP 2020, pp. 7346–7359
  ([ACL Anthology](https://aclanthology.org/2020.emnlp-main.596/)). A graph-neural encoder for
  qualifier-annotated facts. Its second contribution matters as much as the first: the abstract
  states that "existing benchmarks for evaluating link prediction performance on hyper-relational
  KGs suffer from fundamental flaws and thus develop a new Wikidata-based dataset — **WD50K**."

The StarE critique is the field's first public benchmark crisis. It is commonly summarised as "test
leakage and degenerate arity distributions in JF17K and WikiPeople"; the *specific* flaws are
discussed in the paper rather than the abstract, so attribute the detailed leakage claims to the
full text, not to the abstract `[unverified]` in this run.

### 2.4 HypE / HSimplE (2019–2020) — the name

Fatemi, Taslakian, Vazquez, Poole, "Knowledge Hypergraphs: Prediction Beyond Binary Relations"
([arXiv:1906.00137](https://arxiv.org/abs/1906.00137), 1 June 2019; IJCAI 2020, pp. 2191–2197,
[DOI 10.24963/ijcai.2020/303](https://doi.org/10.24963/ijcai.2020/303)). Defines a knowledge
hypergraph as a set of tuples `r(e1,…,ek)` with fixed arity per relation, gives two embedding models
(HypE with positional convolutional filters, HSimplE with shifted entity embeddings), proves
expressiveness results, and releases the FB-AUTO / JF17K-derived splits.

The follow-up, "Knowledge Hypergraph Embedding Meets Relational Algebra" (ReAlE)
([arXiv:2102.09557](https://arxiv.org/abs/2102.09557), 18 Feb 2021), is the theoretically most
interesting of the family: it constructs embeddings that provably represent the primitive operations
of relational algebra (renaming, projection, set union, selection, join), tying the embedding line
back to Fagin's database line.

### 2.5 Expansions and the sceptical turn (2024–2025)

Two later papers close the loop:

- Liu, Yang, Ding, Yao, Li, "Generalizing Hyperedge Expansion for Hyper-relational Knowledge Graph
  Modeling" (TransEQ) ([arXiv:2411.06191](https://arxiv.org/abs/2411.06191), 9 Nov 2024) — an
  *equivalent* (information-preserving) transformation of a hyper-relational KG into an ordinary KG,
  plus an encoder–decoder that exploits it; reports ~15% MRR improvement on WikiPeople.
- Wang, Di, Wang, Li, Teng, Xin, Chen, "Understanding the Embedding Models on Hyper-relational
  Knowledge Graph," CIKM 2025 ([arXiv:2508.03280](https://arxiv.org/abs/2508.03280), 5 Aug 2025) —
  decomposes hyper-relational KGs into ordinary KGs, runs *classical* KG embedding models on them,
  and finds that "some KGE models achieve performance comparable to that of HKGE models."

Taken together these say something uncomfortable: much of the measured advantage of specialised
hyper-relational models may be an artefact of how the comparison was set up. Any claim of the form
"hypergraph representation improves link prediction by X%" made before 2025 should be re-read with
these two papers in hand. This is developed further in
[current-frontier-directions.md](current-frontier-directions.md) (§10) and in
[../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md).

## 3. 2018–2019: hypergraph neural networks

The deep-learning turn arrives via computer vision, not knowledge representation.

> Feng, Y., You, H., Zhang, Z., Ji, R., Gao, Y. "Hypergraph Neural Networks." AAAI 2019, pp.
> 3558–3565 ([DOI 10.1609/aaai.v33i01.33013558](https://doi.org/10.1609/aaai.v33i01.33013558);
> [arXiv:1809.09401](https://arxiv.org/abs/1809.09401), 25 Sep 2018)

HGNN defines a hyperedge convolution from the (normalised) hypergraph Laplacian of §1 — in effect a
two-stage vertex→edge→vertex message pass — and applies it to visual-object and citation
classification. It was followed by HGNN⁺, "General Hypergraph Neural Networks," *IEEE TPAMI*
45(3):3181–3199, 2023 ([DOI 10.1109/TPAMI.2022.3182052](https://doi.org/10.1109/TPAMI.2022.3182052)),
which generalises to multi-modal hyperedge groups, and by the **DHG / DeepHypergraph** PyTorch
library from Tsinghua's iMoon-Lab ([GitHub](https://github.com/iMoonLab/DeepHypergraph)).

By 2024 the area had its own taxonomy paper: Kim, Lee, Gao, Antelmi, Polato, Shin, "A Survey on
Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide," KDD 2024, pp. 6534–6544
([DOI 10.1145/3637528.3671457](https://doi.org/10.1145/3637528.3671457)).

Important caveat for KHG work: mainstream HGNNs operate on **undirected, unlabelled** hyperedges
with node features. They are not, out of the box, models of *facts*. Bridging them to
relation-typed, ordered hyperedges is the contribution of the relational-hypergraph line
([Huang, Romero Orth, Barceló, Bronstein, Ceylan, arXiv:2402.04062](https://arxiv.org/abs/2402.04062),
6 Feb 2024), which analyses link prediction with relational hypergraphs via relational
Weisfeiler–Leman algorithms and logical expressiveness.

## 4. 2018–2021: higher-order network science

A third, independent community — statistical physics and network science — reached hypergraphs from
the study of group interactions.

- Benson, Abebe, Schaub, Jadbabaie, Kleinberg, "Simplicial closure and higher-order link
  prediction," *PNAS* 115(48), 2018 ([arXiv:1802.06916](https://arxiv.org/abs/1802.06916)). Defines
  *higher-order link prediction* — predict which *groups* will appear — and ships 19 datasets. This
  is the network-science analogue of n-ary link prediction, developed with no contact with the KG
  embedding literature.
- Battiston, Cencetti, Iacopini, Latora, Lucas, Patania, Young, Petri, "Networks beyond pairwise
  interactions: Structure and dynamics," *Physics Reports* 874:1–92, Aug 2020
  ([DOI 10.1016/j.physrep.2020.05.004](https://doi.org/10.1016/j.physrep.2020.05.004)). The review
  that brought the physics community in.
- Battiston et al., "The physics of higher-order interactions in complex systems," *Nature Physics*
  17:1093–1098, Oct 2021 ([DOI 10.1038/s41567-021-01371-4](https://doi.org/10.1038/s41567-021-01371-4)).
- Bick, Gross, Harrington, Schaub, "What Are Higher-Order Networks?" *SIAM Review* 65(3):686–731,
  2023 ([DOI 10.1137/21M1414024](https://doi.org/10.1137/21M1414024)) — the paper that finally
  disentangles hypergraphs, simplicial complexes, cell complexes and multilayer networks.
- Joslyn et al. (PNNL), "Hypernetwork Science: From Multidimensional Networks to Computational
  Topology" ([arXiv:2003.11782](https://arxiv.org/abs/2003.11782), 26 Mar 2020) — the programme
  statement of the US national-lab group.

This community also produced the **software and data infrastructure** that the rest of the field now
uses: HyperNetX (PNNL, first released 3 Jan 2019;
[JOSS 9(95):6016, 9 Mar 2024](https://joss.theoj.org/papers/10.21105/joss.06016)), XGI (first PyPI
release 17 Nov 2021; [JOSS 8(85):5162, 17 May 2023](https://joss.theoj.org/papers/10.21105/joss.05162)),
Hypergraphx ([*Journal of Complex Networks* 11(3), 21 Apr 2023, DOI 10.1093/comnet/cnad019](https://doi.org/10.1093/comnet/cnad019)),
and SimpleHypergraphs.jl. Their maintainers are the people who later agreed the HIF interchange
format (see [standards-convergence.md](standards-convergence.md)).

And the mining side: Lee, Bu, Eliassi-Rad, Shin, "A Survey on Hypergraph Mining: Patterns, Tools,
and Generators," *ACM Computing Surveys* 57, published 24 Mar 2025
([DOI 10.1145/3719002](https://doi.org/10.1145/3719002); [arXiv:2401.08878](https://arxiv.org/abs/2401.08878),
Jan 2024).

## 5. 2022–2024: topological deep learning, and the theory catches up

The fourth strand generalises past hypergraphs altogether, to simplicial, cell and combinatorial
complexes, and asks what message passing on them can express.

- **TopoX** — Hajij, Papillon, Frantzen and 40+ co-authors, "TopoX: A Suite of Python Packages for
  Machine Learning on Topological Domains" ([arXiv:2402.02441](https://arxiv.org/abs/2402.02441),
  4 Feb 2024; *JMLR* 25, [paper page](https://jmlr.org/papers/v25/24-0110.html)): TopoNetX,
  TopoEmbedX, TopoModelX, covering "hypergraphs, simplicial, cellular, path and combinatorial
  complexes."
- **The position paper** — Papamarkou, Birdal, Bronstein, Carlsson, Curry, Gao, Hajij, Kwitt, Liò,
  Di Lorenzo et al. (22 authors), "Position: Topological Deep Learning is the New Frontier for
  Relational Learning," ICML 2024, PMLR 235
  ([arXiv:2402.08871](https://arxiv.org/abs/2402.08871), 14 Feb 2024). Notable for who signed it:
  the hypergraph-learning (Gao), geometric-deep-learning (Bronstein) and TDA (Carlsson) communities
  in one author list. That is the convergence, made visible.
- **The expressivity line** — relational Weisfeiler–Leman for relational hypergraphs
  ([Huang et al., 2024](https://arxiv.org/abs/2402.04062)), and then the sharpest result so far:
  Jiang, Li, Feng, Zheng, Niu, Ramasubramanian, Alomair, Bushnell, Poovendran, "The WidthWall: A
  Strict Expressivity Hierarchy for Hypergraph Neural Networks"
  ([arXiv:2605.13690](https://arxiv.org/abs/2605.13690), 13 May 2026), which shows that homomorphism
  densities "generate all continuous hypergraph invariants and organize them into a strict hierarchy
  indexed by hypertree width," gives a unified characterisation of 15 HGNN architectures, and
  "precisely identifies information lost by clique expansion."

That last item closes a 56-year circle: hypertree width, the database-theoretic measure descended
from Fagin's acyclicity hierarchy ([origins-hypergraph-theory.md](origins-hypergraph-theory.md)),
turns out to index what a hypergraph neural network can and cannot compute.

## 6. The convergence, and what it did not fix

By 2023–2024 the four strands share venues (ICML/NeurIPS/LoG, NetSci satellites), libraries (DHG,
HyperNetX, XGI, Hypergraphx, TopoX), surveys that cite across strands
([Antelmi, Cordasco, Polato, Scarano, Spagnuolo, Yang, *ACM CSUR* 56(1), 2023,
DOI 10.1145/3605776](https://doi.org/10.1145/3605776) is the first genuinely cross-community one),
and — after 2025 — an interchange format.

What the convergence did **not** fix, and what the LLM era inherits:

1. **Two incompatible fact models** still coexist (symmetric n-ary tuple vs. triple+qualifiers).
2. **Benchmarks are still Freebase-derived and still contested** (§2.5).
3. **Undirected/unlabelled hypergraph ML and labelled/directed KHG reasoning are still largely
   separate stacks.** HGNN code does not run on a knowledge hypergraph without adaptation.
4. **No storage or query standard** existed until the 2024–2026 wave.

The next note, [llm-era-2023-2026.md](llm-era-2023-2026.md), covers what happened when language
models started *building* the hypergraphs.

## Sources

- Zhou, D., Huang, J., Schölkopf, B. "Learning with Hypergraphs: Clustering, Classification, and Embedding." NIPS 19, 2006. https://papers.nips.cc/paper/3128-learning-with-hypergraphs-clustering-classification-and-embedding
- Gao, Y., Zhang, Z., Lin, H., Zhao, X., Du, S., Zou, C. "Hypergraph Learning: Methods and Practices." *IEEE TPAMI*, 2021. https://doi.org/10.1109/TPAMI.2020.3039374
- Gao, Y., Ji, S., Han, X., Dai, Q. "Hypergraph Computation." *Engineering* 40:188–201, 2024. https://doi.org/10.1016/j.eng.2024.04.017
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases Beyond Binary Relations." IJCAI 2016. https://arxiv.org/abs/1604.08642
- Guan, S., Jin, X., Wang, Y., Cheng, X. "Link Prediction on N-ary Relational Data." WWW 2019, pp. 583–593. https://doi.org/10.1145/3308558.3313414
- Rosso, P., Yang, D., Cudré-Mauroux, P. "Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction." WWW 2020, pp. 1885–1896. https://doi.org/10.1145/3366423.3380257
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs." EMNLP 2020, pp. 7346–7359. https://aclanthology.org/2020.emnlp-main.596/
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." IJCAI 2020, pp. 2191–2197. https://doi.org/10.24963/ijcai.2020/303 ; https://arxiv.org/abs/1906.00137
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraph Embedding Meets Relational Algebra." arXiv:2102.09557, 18 Feb 2021. https://arxiv.org/abs/2102.09557
- Liu, Y., Yang, S., Ding, J., Yao, Q., Li, Y. "Generalizing Hyperedge Expansion for Hyper-relational Knowledge Graph Modeling." arXiv:2411.06191, 9 Nov 2024. https://arxiv.org/abs/2411.06191
- Wang, Y., Di, S., Wang, Z., Li, H., Teng, F., Xin, H., Chen, L. "Understanding the Embedding Models on Hyper-relational Knowledge Graph." CIKM 2025; arXiv:2508.03280, 5 Aug 2025. https://arxiv.org/abs/2508.03280
- Feng, Y., You, H., Zhang, Z., Ji, R., Gao, Y. "Hypergraph Neural Networks." AAAI 2019, pp. 3558–3565. https://doi.org/10.1609/aaai.v33i01.33013558 ; https://arxiv.org/abs/1809.09401
- Gao, Y., Feng, Y., Ji, S., Ji, R. "HGNN⁺: General Hypergraph Neural Networks." *IEEE TPAMI* 45(3):3181–3199, 2023. https://doi.org/10.1109/TPAMI.2022.3182052
- iMoon-Lab. DeepHypergraph (DHG). https://github.com/iMoonLab/DeepHypergraph
- Kim, S., Lee, G., Gao, Y., Antelmi, A., Polato, M., Shin, K. "A Survey on Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide." KDD 2024, pp. 6534–6544. https://doi.org/10.1145/3637528.3671457
- Huang, X., Romero Orth, M., Barceló, P., Bronstein, M. M., Ceylan, İ. İ. "Link Prediction with Relational Hypergraphs." arXiv:2402.04062, 6 Feb 2024. https://arxiv.org/abs/2402.04062
- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. "Simplicial closure and higher-order link prediction." *PNAS* 115(48), 2018. https://arxiv.org/abs/1802.06916
- Battiston, F., Cencetti, G., Iacopini, I., Latora, V., Lucas, M., Patania, A., Young, J.-G., Petri, G. "Networks beyond pairwise interactions: Structure and dynamics." *Physics Reports* 874:1–92, 2020. https://doi.org/10.1016/j.physrep.2020.05.004
- Battiston, F. et al. "The physics of higher-order interactions in complex systems." *Nature Physics* 17:1093–1098, 2021. https://doi.org/10.1038/s41567-021-01371-4
- Bick, C., Gross, E., Harrington, H. A., Schaub, M. T. "What Are Higher-Order Networks?" *SIAM Review* 65(3):686–731, 2023. https://doi.org/10.1137/21M1414024
- Joslyn, C. A. et al. "Hypernetwork Science: From Multidimensional Networks to Computational Topology." arXiv:2003.11782, 26 Mar 2020. https://arxiv.org/abs/2003.11782
- Praggastis, B., Aksoy, S., Arendt, D., Bonicillo, M., Joslyn, C., Purvine, E., Shapiro, M., Yun, J. Y. "HyperNetX: A Python package for modeling complex network data as hypergraphs." *JOSS* 9(95):6016, 9 Mar 2024. https://joss.theoj.org/papers/10.21105/joss.06016
- Landry, N. W., Lucas, M., Iacopini, I., Petri, G., Schwarze, A., Patania, A., Torres, L. "XGI: A Python package for higher-order interaction networks." *JOSS* 8(85):5162, 17 May 2023. https://joss.theoj.org/papers/10.21105/joss.05162
- Lotito, Q. F. et al. "Hypergraphx: a library for higher-order network analysis." *Journal of Complex Networks* 11(3), 21 Apr 2023. https://doi.org/10.1093/comnet/cnad019
- Lee, G., Bu, F., Eliassi-Rad, T., Shin, K. "A Survey on Hypergraph Mining: Patterns, Tools, and Generators." *ACM Computing Surveys* 57, 24 Mar 2025. https://doi.org/10.1145/3719002 ; https://arxiv.org/abs/2401.08878
- Hajij, M., Papillon, M., Frantzen, F. et al. "TopoX: A Suite of Python Packages for Machine Learning on Topological Domains." arXiv:2402.02441, 4 Feb 2024; *JMLR* 25. https://jmlr.org/papers/v25/24-0110.html
- Papamarkou, T., Birdal, T., Bronstein, M., Carlsson, G., Curry, J., Gao, Y., Hajij, M., Kwitt, R., Liò, P., Di Lorenzo, P. et al. "Position: Topological Deep Learning is the New Frontier for Relational Learning." ICML 2024, PMLR 235. https://arxiv.org/abs/2402.08871
- Jiang, F., Li, Y., Feng, Y., Zheng, K., Niu, L., Ramasubramanian, B., Alomair, B., Bushnell, L., Poovendran, R. "The WidthWall: A Strict Expressivity Hierarchy for Hypergraph Neural Networks." arXiv:2605.13690, 13 May 2026. https://arxiv.org/abs/2605.13690
- Antelmi, A., Cordasco, G., Polato, M., Scarano, V., Spagnuolo, C., Yang, D. "A Survey on Hypergraph Representation Learning." *ACM Computing Surveys* 56(1), 2023. https://doi.org/10.1145/3605776
