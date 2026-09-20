---
title: Benchmarks and evaluation protocols for n-ary link prediction
type: survey
status: draft
tags: [benchmark, evaluation, link-prediction, jf17k, wikipeople, fb-auto, m-fb15k, wd50k, wd20k, mrr, hits-at-k, leakage, protocol]
created: 2026-09-20
updated: 2026-09-20
---

# Benchmarks and evaluation protocols for n-ary link prediction

Two models reporting "MRR on JF17K" are often not measuring the same thing. This note pins down the
datasets, the ranking protocols, and the five ways the comparison goes wrong.

Companion to [knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md).

---

## 1. The task, precisely

Given a fact with one element removed, the model scores every candidate for that slot and the
candidates are ranked. Three things vary between papers, and all three change the number:

1. **Which slots are predicted.** Hyperedge-formalisation papers predict *every entity position* in
   the tuple. Hyper-relational papers usually predict only the **object of the primary triple**;
   some also predict qualifier values or the relation.
2. **What counts as a corruption.** All entities, or only entities of the right type, or only
   entities that appeared in that position.
3. **What is filtered out.** The "filtered" setting removes corrupted facts that appear anywhere in
   train/valid/test before ranking.

HYPER states the protocol in the form most usable for knowledge hypergraphs: "for each query
q(u₁,…,u_k) […] and for each position t ≤ k, we replace the t-th position by all other entities such
that the resulting hyperedges does not appear in training, validation, or testing knowledge
hypergraphs" ([Huang, Galkin, Bronstein and Ceylan, arXiv:2506.12362,
2025](https://arxiv.org/abs/2506.12362), §5.1).

HypE states the arity-aware version and, importantly, the *denominator*: for each test tuple
r(e₁,…,e_k) and each position i, |E| − 1 corrupted tuples are generated, and MRR is averaged over
K = Σ |r| **prediction tasks**, not over test facts ([Fatemi, Taslakian, Vazquez and Poole, IJCAI
2020 / arXiv:1906.00137](https://arxiv.org/abs/1906.00137), §5.3). A 6-ary fact therefore contributes
six ranking tasks and a binary fact two — which means **a dataset's arity distribution silently
reweights its own metric.**

## 2. Metrics

$$\mathrm{MRR}=\frac{1}{|Q|}\sum_{q\in Q}\frac{1}{\mathrm{rank}_q},\qquad
\mathrm{Hits@}K=\frac{|\{q\in Q:\mathrm{rank}_q\le K\}|}{|Q|}$$

with Q the set of queries; both in [0, 1], higher better; common K are 1, 3, 5, 10
([Wei, Guan, Li, Jin, Guo and Cheng, *A Survey of Link Prediction in N-ary Knowledge Graphs*,
arXiv:2506.08970, 2025](https://arxiv.org/abs/2506.08970), §4.2 and Appendix G.2).

MRR is dominated by the head of the ranking; Hits@1 is the metric to read when you care whether the
model is *right*, and the gap between them is informative — in the survey's table HAHE has WD50K
MRR 0.402 but Hits@1 0.327, i.e. roughly a third of queries are answered correctly.

## 3. The datasets

### 3.1 General setting

From [Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 1 ("statistics are based on the
original paper"); #E entities, #R roles, N = proportion of n-ary facts:

| Dataset | Source KB | #E | #R | Arity | N | #Facts | Introduced by |
|---|---|---|---|---|---|---|---|
| JF17K | Freebase | 28,645 | 501 | 2–6 | 45.9% | 100,947 | [Wen et al. 2016](https://arxiv.org/abs/1604.08642) |
| WikiPeople | Wikidata | 47,765 | 193 | 2–9 | 11.6% | 382,229 | [Guan et al. WWW 2019](https://doi.org/10.1145/3308558.3313414) |
| WD50K | Wikidata | 47,155 | 531 | 2–67 | 13.6% | 236,507 | [Galkin et al. EMNLP 2020](https://arxiv.org/abs/2009.10847) |

From the HypE paper's own Table 2 ([Fatemi et al. 2020](https://arxiv.org/abs/1906.00137)):

| Dataset | #E | #R | #train | #valid | #test |
|---|---|---|---|---|---|
| JF17K | 29,177 | 327 | 77,733 | – | 24,915 |
| FB-AUTO | 3,410 | 8 | 6,778 | 2,255 | 2,180 |
| M-FB15K | 10,314 | 71 | 415,375 | 39,348 | 38,797 |

FB-AUTO is built "by selecting the facts from [Freebase] whose subject is 'automotive'"; M-FB15K by
selecting facts about entities present in the Wikilinks database, following the FB15k recipe
([Fatemi et al. 2020](https://arxiv.org/abs/1906.00137), appendix). **Note the two JF17K rows
disagree** (28,645/501 vs. 29,177/327): different preprocessing of the same source. This is the
single most common source of confusion in the literature.

And from the StarE paper's Table 1 ([Galkin et al. 2020](https://arxiv.org/abs/2009.10847)), which
counts *statements* and separates qualifier vocabulary:

| Dataset | Statements | w/ quals | Entities | Relations | E in quals | R in quals | Train | Valid | Test |
|---|---|---|---|---|---|---|---|---|---|
| WD50K | 236,507 | 32,167 (13.6%) | 47,156 | 532 | 5,460 | 45 | 166,435 | 23,913 | 46,159 |
| WD50K (33) | 102,107 | 31,866 (31.2%) | 38,124 | 475 | 6,463 | 47 | 73,406 | 10,568 | 18,133 |
| WD50K (66) | 49,167 | 31,696 (64.5%) | 27,347 | 494 | 7,167 | 53 | 35,968 | 5,154 | 8,045 |
| WD50K (100) | 31,314 | 31,314 (100%) | 18,792 | 279 | 7,862 | 75 | 22,738 | 3,279 | 5,297 |
| WikiPeople | 369,866 | 9,482 (2.6%) | 34,839 | 375 | 416 | 35 | 294,439 | 37,715 | 37,712 |
| JF17K | 100,947 | 46,320 (45.9%) | 28,645 | 322 | 3,652 | 180 | 76,379 | – | 24,568 |

The WD50K (33/66/100) ladder is the useful design here: the same source with a controlled fraction
of qualified statements, so a model's dependence on qualifiers becomes measurable rather than
asserted.

### 3.2 Special settings

**Temporal** — NWIKI, NICE ([Hou et al., Findings of EMNLP
2023](https://doi.org/10.18653/v1/2023.findings-emnlp.77)); Wiki-hy, YAGO-hy (Ding et al. 2023),
statistics from [Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 6:

| Dataset | #Entities | #Timestamps | Interval | N | #Train | #Valid | #Test |
|---|---|---|---|---|---|---|---|
| NWIKI | 17,481 | 205 | 1 year | 81.9% | 108,397 | 14,370 | 15,591 |
| NICE | 10,860 | 4,017 | 24 hours | 97.5% | 368,868 | 5,268 | 46,159 |
| Wiki-hy | 11,140 | 507 | 1 year | 9.5% | 111,252 | 13,900 | 13,926 |
| YAGO-hy | 10,026 | 188 | 1 year | 6.9% | 51,193 | 10,973 | 10,977 |

**Few-shot** — WikiAnimals, WikiCompanies, WD50K-Few (Zhang et al. 2022); F-WikiPeople, F-JF17K,
F-WD50K ([Wei et al., COLING 2024](https://arxiv.org/abs/2305.06104)); statistics in
[Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 7. WikiAnimals is by far the largest
(2,925,278 entities, 5,964,839 facts, 49.7% n-ary, 49 tasks).

**Inductive** — WD20K(25), WD20K(100) V1, WD20K(100) V2 ([Ali et al., ISWC
2021](https://doi.org/10.1007/978-3-030-88361-4_5)); JF-Ext, WIKI-Ext, WD-Ext (Wei et al. 2024).
The V1/V2 split matters: both provide textual descriptions *and* an inference graph containing
unseen entities, while WD20K(25) provides descriptions only, "requiring the model to rely solely on
text features". Sizes from [Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 8:

| Dataset | Train (N) | Valid (N) | Test (N) | Inference (N) |
|---|---|---|---|---|
| WD20K(25) | 39,819 (30.0%) | 4,252 (25.0%) | 3,453 (22.0%) | 0 |
| WD20K(100) V1 | 7,785 (100%) | 295 (100%) | 364 (100%) | 2,667 (100%) |
| WD20K(100) V2 | 4,146 (100%) | 538 (100%) | 678 (100%) | 4,274 (100%) |
| JF-Ext | 3,305 (54.0%) | 1,061 (30.0%) | 1,283 (21.0%) | 5,012 (28.1%) |
| WIKI-Ext | 3,905 (2.1%) | 6,480 (2.5%) | 4,733 (2.9%) | 4,880 (6.6%) |
| WD-Ext | 5,112 (1.0%) | 2,610 (3.6%) | 3,053 (2.0%) | 3,382 (6.1%) |

**Relation-inductive** — HYPER derives JF-25/50/75/100, WP-*, MFB-*, WD-* from JF17K, WikiPeople,
M-FB15K and WD50K, where the number is the percentage of test tuples containing previously unseen
relations, following the InGram methodology ([Huang et al.
2025](https://arxiv.org/abs/2506.12362), §5.2). WD50K is converted to a knowledge hypergraph "by
hashing the main relation and predicates in canonical order" — a conversion worth remembering when
comparing against hyper-relational numbers on the same name.

## 4. Leakage and design flaws — the StarE critique

This is the most consequential methodological result in the area, and it is quantified.

**JF17K leaks.** "The authors of JF17K reported the dataset to contain redundant entries. In our own
analysis, we detected that about **44.5% of the test statements share the same main (s, r, o) triple
as the train statements.** We consider this fact as a major data leakage which allows triple-based
models to memorize subjects and objects appearing in the test set"
([Galkin et al. 2020](https://arxiv.org/abs/2009.10847), §5).

**WikiPeople is barely hyper-relational.** "In WikiPeople, about 13% of statements contain at least
one literal […] However, after removing statements with literals, less than 3% of the remaining
statements contain any qualifier pairs. Out of those, about 80% possess only one qualifier. This
fact renders WikiPeople less sensitive to hyper-relational models as performance on triple-only
facts dominates the overall score" ([Galkin et al. 2020](https://arxiv.org/abs/2009.10847), §5).
Note the consequence: **a "gain" on WikiPeople is mostly a gain on ordinary triples.**

**WD50K was built to fix both**: "To eliminate test set leakages we remove all statements from train
and validation sets that share the same main triple (s,p,o) with test statements"
([Galkin et al. 2020](https://arxiv.org/abs/2009.10847), §5).

Consequences for reading the literature: numbers on JF17K published before 2020 (and many after)
include a memorisation component; numbers on WikiPeople measure qualifier handling only weakly; and
the two effects push in opposite directions, so "model X wins on JF17K but loses on WikiPeople" is
frequently an artefact.

## 5. Six pitfalls, in the order they bite

1. **Protocol mismatch.** All-positions vs. object-only prediction. HypE's JF17K MRR 0.494 and
   StarE's 0.574 are different tasks ([Fatemi et al. 2020](https://arxiv.org/abs/1906.00137);
   [Galkin et al. 2020](https://arxiv.org/abs/2009.10847)).
2. **Dataset version mismatch.** JF17K appears with 501, 327 and 322 relations in three respected
   sources (see §3.1). Always record the preprocessing script, not just the dataset name.
3. **Leakage.** §4.
4. **Literal handling.** Most models "conventionally ignore" literals
   ([Galkin et al. 2020](https://arxiv.org/abs/2009.10847)); HyNT is the exception
   ([Chung, Lee and Whang, KDD 2023](https://doi.org/10.1145/3580305.3599490)). Dropping literals
   changes the effective dataset, and papers do not always say whether they did.
5. **Arity reweighting.** Because MRR averages over prediction tasks, datasets with many high-arity
   facts weight those facts more heavily. Report **per-arity breakdowns**; HypE does this
   ([Fatemi et al. 2020](https://arxiv.org/abs/1906.00137), Table 4, Hits@10 for arity bins 2, 3 and
   4–5–6).
6. **Single-split, single-run reporting.** Most of this literature reports one number on one split.
   HYPER is a welcome exception, reporting "averaged results for three runs […] with the standard
   deviation" ([Huang et al. 2025](https://arxiv.org/abs/2506.12362), §5.1).

## 6. A checklist for reporting a new result

- State the formalisation (hyperedge / role-value / hyper-relational) and the *positions predicted*.
- State the filtering rule and the corruption universe.
- Name the dataset **version** and link the preprocessing code.
- Report MRR **and** Hits@1 and Hits@10, plus a per-arity breakdown.
- Report multiple seeds with dispersion.
- If JF17K is used, say what was done about the 44.5% main-triple overlap.
- Prefer WD50K(33/66/100) when the claim is specifically about qualifiers.

## Open questions raised here

- Is there a leakage audit of WD50K, WD20K and the Ext/Few families comparable to StarE's audit of
  JF17K? None was found for this note.
- Should the community move to an arity-stratified metric (macro-averaged over arity) rather than
  the current task-averaged MRR?
- No benchmark yet measures *calibration* of n-ary link predictors; see
  [explainability-and-uncertainty.md](explainability-and-uncertainty.md).

## Sources

- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs*. arXiv:2506.08970, 2025; EMNLP 2025. <https://arxiv.org/abs/2506.08970>
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs". *EMNLP 2020*; arXiv:2009.10847. <https://arxiv.org/abs/2009.10847>
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations*. IJCAI 2020; arXiv:1906.00137. <https://arxiv.org/abs/1906.00137>
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. *On the representation and embedding of knowledge bases beyond binary relations*. IJCAI 2016; arXiv:1604.08642. <https://arxiv.org/abs/1604.08642>
- Guan, S., Jin, X., Wang, Y., Cheng, X. "Link Prediction on N-ary Relational Data". *WWW 2019*. <https://doi.org/10.1145/3308558.3313414>
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. *HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs*. arXiv:2506.12362, 2025. <https://arxiv.org/abs/2506.12362>
- Chung, C., Lee, J., Whang, J. J. "Representation Learning on Hyper-Relational and Numeric Knowledge Graphs with Transformers". *KDD 2023*. <https://doi.org/10.1145/3580305.3599490>
- Ali, M., Berrendorf, M., Galkin, M., Thost, V., Ma, T., Tresp, V., Lehmann, J. "Improving Inductive Link Prediction Using Hyper-relational Facts". *ISWC 2021*. <https://doi.org/10.1007/978-3-030-88361-4_5>
- Hou, Z., Jin, X., Li, Z., Bai, L., Guan, S., Zeng, Y., Guo, J., Cheng, X. "Temporal Knowledge Graph Reasoning Based on N-tuple Modeling". *Findings of EMNLP 2023*. <https://doi.org/10.18653/v1/2023.findings-emnlp.77>
- Wei, J., Guan, S., Jin, X., Guo, J., Cheng, X. *Few-shot Link Prediction on N-ary Facts*. COLING 2024; arXiv:2305.06104. <https://arxiv.org/abs/2305.06104>
