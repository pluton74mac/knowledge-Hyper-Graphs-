---
title: Social, collaborative and communication data
type: survey
status: draft
tags: [hypergraph, social-networks, group-interaction, misinformation, email, meetings, higher-order, contagion]
created: 2026-09-20
updated: 2026-09-20
---

# Social, collaborative and communication data

Human interaction is rarely dyadic: a meeting, an email thread, a group chat, a co-authored paper and a
committee vote are all *group* events. Social science was therefore the first field to build empirical
higher-order datasets, and it remains the field with the cleanest evaluation methodology for them —
which is why this note is useful to the rest of the KB even though its hyperedges carry no roles.

## 1. Group interactions as hyperedges

The reference study is [Benson, Abebe, Schaub, Jadbabaie and Kleinberg, 2018](https://www.pnas.org/doi/10.1073/pnas.1800683115)
(*PNAS* 115(48):E11221–E11230), covering **19 datasets** from biology, medicine, social networks and the
web. Two contributions matter here:

- **Simplicial closure** as a descriptive statistic — how often an open group (its pairs all present,
  the group itself absent) later appears as a full simplex — with rates that differ systematically
  across domains.
- **Higher-order link prediction** as the evaluation task: predict which *sets* will interact, not which
  pairs. This gives the higher-order community a falsifiable benchmark, which the knowledge-hypergraph
  community largely lacks.

The datasets themselves (email, co-authorship, co-tagging, drug co-prescription, contact records) are
published and widely reused ([Benson data page](https://www.cs.cornell.edu/~arb/)). Email threads and
meeting attendance are among the most natural hyperedges available: the recipient list *is* the
hyperedge, with no extraction step and no annotation ambiguity.

## 2. Contagion, opinion and misinformation

Higher-order contagion is where the hypergraph changes the *qualitative* behaviour of a model rather
than nudging a metric.

**Rumour propagation on hypergraphs** ([Oliveira, Traversa, Ferraz de Arruda, Moreno, 2025](https://arxiv.org/abs/2504.19305);
published version in [*Nature Communications*, 2026](https://www.nature.com/articles/s41467-026-70096-w))
introduces a group-based annihilation mechanism: a spreader becomes a stifler when the fraction of its
hyperedges already aware of the rumour exceeds a threshold. Findings:

- Two distinct subcritical decay behaviours — exponential and power-law — which can **coexist** depending
  on the heterogeneity of the hypergraph.
- Continuous phase transitions in both homogeneous and heterogeneous hypergraphs, contradicting the
  expectation that higher-order interactions necessarily give discontinuous transitions.
- Empirical validation on Telegram and email cascade data suggesting real rumour propagation sits **near
  criticality**.

That last point is the practically important one: near criticality, small changes in group structure
produce large changes in outcome, which is an argument for modelling the group structure explicitly
rather than averaging it into pairwise rates.

Related lines: adaptive rumour propagation and activity contagion in higher-order networks
([*Communications Physics*, 2025](https://www.nature.com/articles/s42005-025-02181-3)); an opinion
evolution model with higher-order interactions ([*PLOS One*](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0321718));
information propagation in hypergraph-based social networks, extending SEIR to hypernetworks
([PMC, 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11593332/)); efficient Gillespie algorithms for
spreading on large heterogeneous higher-order networks
([arXiv:2509.20174](https://arxiv.org/pdf/2509.20174)); and negative-influence blocking maximisation on
hypergraphs ([*Information Processing & Management*, 2025](https://www.sciencedirect.com/science/article/abs/pii/S0306457325002146)),
which is the intervention-design counterpart.

## 3. Detection rather than dynamics

Rumour *detection* has begun using hypergraphs as a fusion device: an edge-weighted hypergraph neural
network aggregates higher-order connections across multiple propagation subgraphs, with joint attention
over textual semantics, user behaviour and topology
([*ScienceDirect*, 2026](https://www.sciencedirect.com/science/article/pii/S2772941926000608)). This is
sense **D** — the hypergraph is a pooling structure over a propagation cascade — and the usual caution
applies: the reported gains are over graph baselines on the same benchmarks, and misinformation
benchmarks are notoriously sensitive to dataset construction.

## 4. What this domain contributes to knowledge hypergraphs

Three transferable things, and one warning.

1. **A real evaluation protocol.** Higher-order link prediction on timestamped group data is a
   well-posed task with no LLM in the loop. A knowledge-hypergraph analogue — predict the missing
   participant of an n-ary fact, evaluated temporally — would be a genuine benchmark.
2. **Ground-truth hyperedges for free.** Email recipient lists, meeting rosters and author lists do not
   need extraction, so they isolate the *representation* question from the *extraction* question that
   dominates [retrieval-augmented-generation](retrieval-augmented-generation.md).
3. **Evidence that group size matters non-linearly.** Threshold and critical-mass effects do not survive
   pairwise projection at all.

The warning: these hyperedges have no roles, no direction and no types. Results about them support
sense **B** of [applications-overview](applications-overview.md) and say nothing directly about whether
role-labelled n-ary *facts* are worth their cost.

## Sources

- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. *Simplicial closure and higher-order link prediction.* PNAS 115(48):E11221–E11230, 2018. https://www.pnas.org/doi/10.1073/pnas.1800683115
- Benson, A. R. Data and code page, Cornell University, checked 2026-09-20. https://www.cs.cornell.edu/~arb/
- Oliveira, K. A., Traversa, P., Ferraz de Arruda, G., Moreno, Y. *Rumor propagation on hypergraphs.* arXiv:2504.19305, 27 Apr 2025. https://arxiv.org/abs/2504.19305
- *Rumor propagation on hypergraphs.* Nature Communications, 2026. https://www.nature.com/articles/s41467-026-70096-w
- *Adaptive rumor propagation and activity contagion in higher-order networks.* Communications Physics, 2025. https://www.nature.com/articles/s42005-025-02181-3
- *An opinion evolution model for online social networks considering higher-order interactions.* PLOS One. https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0321718
- *Information Propagation in Hypergraph-Based Social Networks.* PMC, 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC11593332/
- *Efficient Gillespie algorithms for spreading phenomena in large and heterogeneous higher-order networks.* arXiv:2509.20174. https://arxiv.org/pdf/2509.20174
- *Hypergraph negative influence blocking maximization via influence estimation.* Information Processing & Management, 2025. https://www.sciencedirect.com/science/article/abs/pii/S0306457325002146
- *Edge-weighted hypergraph neural network for rumor detection in online social networks.* ScienceDirect, 2026. https://www.sciencedirect.com/science/article/pii/S2772941926000608
