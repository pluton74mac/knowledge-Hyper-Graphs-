---
title: Reproducibility of n-ary and hyper-relational link prediction
type: survey
status: draft
tags: [reproducibility, replication, benchmarks, link-prediction, n-ary, hyper-relational, pykeen, libkge, code-availability, gap-filling]
created: 2026-09-20
updated: 2026-09-20
---

# Reproducibility of n-ary link prediction

Triple-based knowledge-graph embedding had two reckonings. In 2020 Ruffinelli, Broscheit and Gemulla
retrained the classic models under a common training pipeline and found that "when trained
appropriately, the relative performance differences between various model architectures often shrinks
and sometimes even reverses when compared to prior results, and many of the more advanced
architectures and techniques proposed in the literature should be revisited to reassess their
individual benefits" ([*You CAN Teach an Old Dog New Tricks! On Training Knowledge Graph
Embeddings*, ICLR 2020](https://dblp.org/rec/conf/iclr/RuffinelliBG20.html)). In 2021 Ali,
Berrendorf, Hoyt, Vermue, Galkin, Sharifzadeh, Fischer, Tresp and Lehmann re-implemented **21
models** in one framework and benchmarked them over four datasets with **24,804 GPU hours**
([*Bringing Light Into the Dark*, IEEE
TPAMI](https://doi.org/10.1109/TPAMI.2021.3124805); code
<https://github.com/pykeen/benchmarking>).

**The n-ary field has had no equivalent.** This note establishes that claim, surveys the one paper
that comes close, audits the code behind every model in
[knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md), and gives a
concrete replication plan this repository could execute.

---

## 1. Does a replication study exist? No — and one near-miss

### The near-miss: Wang et al., CIKM 2025

The closest thing to a re-evaluation is *Understanding the Embedding Models on Hyper-relational
Knowledge Graph* ([Wang, Di, Wang, Li, Teng, Xin and Chen, CIKM 2025 /
arXiv:2508.03280](https://arxiv.org/abs/2508.03280), submitted 5 Aug 2025). Its question is the
right one: does an HKGE model's advantage "arise from their base KGE model or the specially
designed extension module"? Its method is to **decompose** hyper-relational graphs into plain KG
format by three different decompositions and run classical KGE models on the result.

Its headline result is the one that matters for this KB: **"some KGE models achieve performance
comparable to that of HKGE models."** The authors then qualify it — the decompositions "alter the
original HKG topology and fail to fully preserve HKG information" — and propose their own model,
FormerGNN.

**Why this is not the replication study the field needs.** Three reasons:

1. **It changes the data, not the training.** Ruffinelli et al. held the data fixed and varied the
   training pipeline. Wang et al. hold the training roughly fixed and vary the *representation*.
   Both are useful; only the first tests whether published numbers are trustworthy.
2. **It ends in a new model.** A paper that concludes with FormerGNN has an incentive structure
   that a pure reproducibility paper does not.
3. **It is hyper-relational only.** It says nothing about the hyperedge-formalisation branch
   (HypE, GETD, HSimplE, m-TransH), where the notorious r-SimplE collapse (JF17K MRR 0.102 vs.
   HypE 0.494) lives — see
   [knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md) §4b.

Its result nonetheless *rhymes* with Ruffinelli et al.: a well-trained simple baseline matches
specialised architectures. That is now two independent hints, in two sub-fields, pointing the same
way.

### What else was searched and not found

`[unverified]` — absence from a bounded search on 2026-09-20, not proof of absence:

- No paper titled or framed as a reproducibility/replication study of n-ary or hyper-relational link
  prediction was found in the arXiv, ACL Anthology or DBLP results consulted.
- The two surveys — [Wei, Guan, Li, Jin, Guo and Cheng, EMNLP 2025 /
  arXiv:2506.08970](https://arxiv.org/abs/2506.08970) and [Lu, Tupikina and Alam, IEEE TKDE 2026 /
  arXiv:2506.05626](https://arxiv.org/abs/2506.05626) — **copy numbers from the original papers**.
  Wei et al. are explicit that their Table 2 takes HypE and S2S figures from Di et al. 2021 and the
  rest from Luo et al. 2023. No survey re-ran anything.
- The arXiv Jun–Sep 2026 sweep reported in
  [../08-history-and-frontier/reading-the-frontier-2026-q3.md](../08-history-and-frontier/reading-the-frontier-2026-q3.md)
  returned **zero** new papers matching `abs:"hyper-relational"` in that window, so nothing appeared
  between the CIKM 2025 paper and this note's date.

---

## 2. Why the n-ary field is *harder* to replicate than the triple field

Four structural obstacles, each documented elsewhere in this KB:

1. **Three incompatible task definitions.** Hyperedge-formalisation papers predict every position;
   hyper-relational papers predict the object of the primary triple. Same dataset name, different
   task — see [benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md).
2. **A leaking benchmark with no validation split.** 44.5% of JF17K test statements share their
   main triple with training, and JF17K ships no official validation split, so every paper invents
   one — see
   [../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md)
   §§1–2. Two papers with identical code can report different numbers purely from split choice.
3. **Statistics that differ by a factor of two under the same dataset name** (ibid. §4).
4. **No shared framework.** Which is §3.

---

## 3. Framework support: PyKEEN and LibKGE do not do n-ary

This is the single most consequential engineering fact in the note.

| Framework | Stars (checked 2026-09-20) | Licence | n-ary / qualifier support |
|---|---|---|---|
| [pykeen/pykeen](https://github.com/pykeen/pykeen) | — | MIT | **None.** The model reference lists translational, semantic-matching, neural, GNN and multimodal families; every model is documented as scoring "plausibility of a triple (h,r,t)". No qualifier or n-ary model appears. |
| [uma-pi1/kge](https://github.com/uma-pi1/kge) (LibKGE) | 835 | MIT | **None.** 1,325 commits, not archived; the README describes triple-based KGE only and does not mention n-ary or hyper-relational facts. |

PyKEEN itself is documented in [Ali et al., *PyKEEN 1.0*,
arXiv:2007.14175](https://arxiv.org/abs/2007.14175).

Consequence: there is **no** "PyKEEN for hyper-relational KGs". Every model in §4 ships its own
loader, its own negative sampler, its own filtering rule and its own evaluation loop. That is
precisely the condition Ali et al. described as "heterogeneity in […] implementations, training, and
evaluation", and which they spent 24,804 GPU hours removing for triples. Nobody has spent it here.

The nearest thing to a unifying implementation is **HYPER**, whose repository states that it also
supports HCNet inference — one repo, two models
([HxyScotthuang/HYPER](https://github.com/HxyScotthuang/HYPER)).

---

## 4. Code audit of the section-05 model table

Every URL below was fetched on **2026-09-20**. "Last commit" is the first entry of the repository's
GitHub Atom commit feed; where the feed was not fetched the cell says so rather than guessing.

| Model | Year | Repository | Exists | Stars | Licence | Commits | Last commit |
|---|---|---|---|---|---|---|---|
| m-TransH | 2016 | none published | — | — | — | — | — |
| RAE | 2018 | none published | — | — | — | — | — |
| NaLP | 2019 | [gsp2014/NaLP](https://github.com/gsp2014/NaLP) | yes | 14 | none stated | 22 | not fetched |
| HINGE | 2020 | [eXascaleInfolab/HINGE_code](https://github.com/eXascaleInfolab/HINGE_code) | yes | 38 | none stated | 11 | **2020-07-15** |
| NeuInfer | 2020 | none found | — | — | — | — | — |
| HypE / HSimplE | 2020 | [ServiceNow/HypE](https://github.com/ServiceNow/HypE) | yes | 33 | GPL-3.0 | 33 | **2022-07-15** |
| HypE (mirror) | 2020 | [baharefatemi/HypE](https://github.com/baharefatemi/HypE) | yes | 24 | GPL-3.0 | 31 | not fetched |
| GETD | 2020 | [liuyuaa/GETD](https://github.com/liuyuaa/GETD) | yes | 11 | MIT | **1** | **2020-01-17** |
| StarE | 2020 | [migalkin/StarE](https://github.com/migalkin/StarE) | yes | 90 | MIT | 26 | **2023-12-01** |
| GRAN | 2021 | [PaddlePaddle/Research › KG/ACL2021_GRAN](https://github.com/PaddlePaddle/Research/tree/master/KG/ACL2021_GRAN) | yes | (monorepo) | Apache-2.0 | — | not fetched |
| S2S | 2021 | none found | — | — | — | — | — |
| StarQE | 2022 | [DimitrisAlivas/StarQE](https://github.com/DimitrisAlivas/StarQE) | yes | 33 | MIT | 10 | not fetched |
| HAHE | 2023 | [LHRLAB/HAHE](https://github.com/LHRLAB/HAHE) | yes | 28 | MIT | 31 | **2025-08-18** |
| ShrinkE | 2023 | [xiongbo010/ShrinkE](https://github.com/xiongbo010/ShrinkE) | yes | 6 | none stated | 17 | **2024-07-05** |
| HyNT | 2023 | [bdi-lab/HyNT](https://github.com/bdi-lab/HyNT) | yes | 36 | CC BY-NC-SA 4.0 | 39 | **2025-05-27** |
| Text2NKG | 2024 | [LHRLAB/Text2NKG](https://github.com/LHRLAB/Text2NKG) | yes | 37 | MIT | 91 | not fetched |
| HyperMono | 2024 | [zhiweihu1103/HKGC-HyperMono](https://github.com/zhiweihu1103/HKGC-HyperMono) | yes | 0 | none stated | 21 | not fetched |
| HYPER | 2025 | [HxyScotthuang/HYPER](https://github.com/HxyScotthuang/HYPER) | yes | 21 | MIT | 6 | **2026-03-25** |
| HCNet | 2024 | via HYPER repo (inference support) | partial | — | — | — | — |
| THOR | 2026 | none found | — | — | — | — | — |
| FormerGNN | 2025 | none found | — | — | — | — | — |

Six findings from the audit:

1. **Every repository that was claimed to exist does exist.** No dead links in the section-05 table.
   That is better than the field's reputation suggests.
2. **Four of the field's most-cited models have no public code at all**: m-TransH, RAE, NeuInfer and
   S2S. Their numbers are in every comparison table in the literature and cannot be reproduced by
   anyone.
3. **Licences are a mess.** Two repositories state no licence (legal default: all rights reserved),
   two are GPL-3.0, one is **CC BY-NC-SA 4.0** — a *non-commercial* licence on the HyNT code and
   data. Anyone building on HyNT commercially is in breach. Compare
   [../10-comparative-and-critique/privacy-licensing-and-governance.md](../10-comparative-and-critique/privacy-licensing-and-governance.md).
4. **GETD has one commit.** A single code drop from January 2020, never touched since; MIT-licensed,
   so at least usable.
5. **Maintenance correlates with recency, not with citation count.** HINGE (38 stars, heavily cited)
   last moved in 2020; HYPER (21 stars, 2025 paper) moved in March 2026.
6. **The newest results are the least reproducible.** THOR (Feb 2026) and FormerGNN (CIKM 2025) —
   both of which claim state of the art — had no locatable public implementation on 2026-09-20.
   `[unverified]`

---

## 5. A replication plan for this repository

Scoped so that it is actually executable, and ordered so that each step is useful even if the next
is never done.

**Step 0 — fix the protocol before touching a model.** Write down, in one file, which of the three
task definitions is being evaluated, the filtering rule, and the validation split. Publish the split
files. Most of the field's incomparability is created here.

**Step 1 — the leakage-controlled baseline (cheap, high value).** Re-run **one** cheap model
(HSimplE or GETD, both MIT/GPL and self-contained) on JF17K twice: once as published, once with the
44.5% leaking test statements removed. Report both. Nobody has published the delta, and it is the
number that decides whether a decade of JF17K results means anything. Data and leak evidence:
[../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md)
§1; fetch instructions in [../../datasets/README.md](../../datasets/README.md).

**Step 2 — the old-dog test.** Take HypE and HSimplE from
[ServiceNow/HypE](https://github.com/ServiceNow/HypE) (the repo ships both plus m-DistMult and
m-TransH re-implementations) and sweep learning rate, embedding dimension, negative-sample count and
regulariser over a fixed budget. Ruffinelli et al.'s finding was that this alone reorders the
leaderboard. The HypE repository is the only place where four models of the hyperedge branch live
under one training loop — it is the field's accidental LibKGE and should be used as one.

**Step 3 — arity stratification.** Report MRR **per arity** on JF17K and FB-AUTO. §5 of the
[benchmarks note](benchmarks-and-evaluation-protocols.md) records that no arity-stratified result
exists anywhere. This requires no new training at all: only re-bucketing the predictions from steps
1–2.

**Step 4 — cross-check the survey tables.** For each number this KB reproduces in
[knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md) §4a, record
whether it was (i) re-run here, (ii) taken from the model's own paper, or (iii) taken from a third
paper's table. Today almost everything is (iii)-via-(ii).

**Step 5 — publish a datasheet.** Following [Gebru et al.,
CACM 2021](https://doi.org/10.1145/3458723), so that the splits this repository creates do not
become the next JF17K.

**What would count as success.** Not "we beat the state of the art" but: a table in which every cell
says where it came from, and at least one published number is shown to be wrong, unreachable, or
protocol-dependent.

---

## 6. Open problems

1. Does any hyper-relational model beat a well-tuned classical KGE baseline **on de-leaked data**?
   Wang et al. suggest not on decomposed data; nobody has checked on native data.
2. What is the variance of these models across seeds? No paper in
   [knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md) reports
   error bars.
3. Would a PyKEEN-style unified framework for n-ary facts change the rankings the way it did for
   triples? The framework does not exist, so the question is open by construction.
4. Are the four code-less models (m-TransH, RAE, NeuInfer, S2S) reproducible at all from their
   papers?

Questions raised here belong in [../00-index/open-questions.md](../00-index/open-questions.md)
tagged `05`.

## Sources

- Ruffinelli, D., Broscheit, S., Gemulla, R. "You CAN Teach an Old Dog New Tricks! On Training Knowledge Graph Embeddings." ICLR 2020. <https://dblp.org/rec/conf/iclr/RuffinelliBG20.html>
- Ali, M., Berrendorf, M., Hoyt, C. T., Vermue, L., Galkin, M., Sharifzadeh, S., Fischer, A., Tresp, V., Lehmann, J. "Bringing Light Into the Dark: A Large-Scale Evaluation of Knowledge Graph Embedding Models Under a Unified Framework." *IEEE TPAMI*, 2021/2022. <https://doi.org/10.1109/TPAMI.2021.3124805> ; benchmarking code <https://github.com/pykeen/benchmarking>
- Ali, M. et al. "PyKEEN 1.0: A Python Library for Training and Evaluating Knowledge Graph Embeddings." arXiv:2007.14175. <https://arxiv.org/abs/2007.14175>
- Wang, Y., Di, S., Wang, Z., Li, H., Teng, F., Xin, H., Chen, L. "Understanding the Embedding Models on Hyper-relational Knowledge Graph." CIKM 2025; arXiv:2508.03280, 5 Aug 2025. <https://arxiv.org/abs/2508.03280>
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. "A Survey of Link Prediction in N-ary Knowledge Graphs." EMNLP 2025; arXiv:2506.08970. <https://arxiv.org/abs/2506.08970>
- Lu, X., Tupikina, L., Alam, M. "Two-Dimensional Taxonomy for n-Ary Knowledge Representation Learning Methods." IEEE TKDE 2026; arXiv:2506.05626. <https://arxiv.org/abs/2506.05626>
- Gebru, T., Morgenstern, J., Vecchione, B., Wortman Vaughan, J., Wallach, H., Daumé III, H., Crawford, K. "Datasheets for Datasets." *CACM* 64(12), Dec 2021; arXiv:1803.09010. <https://doi.org/10.1145/3458723>
- PyKEEN model reference documentation, checked 2026-09-20. <https://pykeen.readthedocs.io/en/stable/reference/models.html>
- LibKGE repository (uma-pi1/kge), checked 2026-09-20. <https://github.com/uma-pi1/kge>
- Repository pages and GitHub Atom commit feeds fetched 2026-09-20 for: gsp2014/NaLP, eXascaleInfolab/HINGE_code, ServiceNow/HypE, baharefatemi/HypE, liuyuaa/GETD, migalkin/StarE, PaddlePaddle/Research (KG/ACL2021_GRAN), DimitrisAlivas/StarQE, LHRLAB/HAHE, xiongbo010/ShrinkE, bdi-lab/HyNT, LHRLAB/Text2NKG, zhiweihu1103/HKGC-HyperMono, HxyScotthuang/HYPER.
- Yu, W., Lu, Y., Yang, D. "THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs." arXiv:2602.05424, 5 Feb 2026. <https://arxiv.org/abs/2602.05424>
