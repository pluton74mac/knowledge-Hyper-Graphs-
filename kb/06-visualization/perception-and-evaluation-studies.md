---
title: Perception and evaluation studies for hypergraph and set visualisation
type: survey
status: draft
tags: [hypergraph, visualization, user-study, evaluation, readability, scalability, perception]
created: 2026-09-20
updated: 2026-09-20
---

# Perception and evaluation studies for hypergraph and set visualisation

What is actually *known*, from controlled experiments, about which hypergraph encoding a person can
read? Much less than the number of published encodings suggests. Alsallakh et al.'s state-of-the-art
report already flagged "a clear lack of empirical user studies that assess the effectiveness of
different techniques in performing different tasks"
([Alsallakh, Micallef, Aigner, Hauser, Miksch & Rodgers, 2016](https://doi.org/10.1111/cgf.12722)),
and five years later Wallinger et al. judged that "the observation of Alsallakh et al. … that there
is a lack of empirical studies assessing the effectiveness of set visualization techniques, remains
valid" ([Wallinger, Jacobsen, Kobourov & Nöllenburg, 2021](https://doi.org/10.1109/TVCG.2021.3074615)).

Almost all of the evidence is about **set** visualisation, not about hypergraphs with labelled,
directed or nested hyperedges. That gap is the single biggest caveat on everything below.

---

## 1. The task vocabulary everyone uses

Alsallakh et al. give a taxonomy of **26 general tasks in three categories**
([Alsallakh et al., 2016](https://doi.org/10.1111/cgf.12722), as summarised by
[Wallinger et al., 2021](https://doi.org/10.1109/TVCG.2021.3074615)):

1. **Element-based** — about specific elements and their set memberships
   ("What genre(s) does *Van Halen* belong to?");
2. **Set-based** — about relations between sets, ignoring individual elements
   ("Which genres overlap with *Rock*?");
3. **Attribute-based** — about attributes of elements and how they distribute across memberships
   ("Do artists in the *Rock* genre sell more?").

Any evaluation that reports only one category is not comparable with one that reports another. For a
KHG, category 1 maps to "which facts is this entity in?", category 2 to "which facts share
arguments?", and category 3 to "how do confidence/time/provenance distribute?" — and category 3 is
the least studied.

---

## 2. The headline study: abstract set visualisations (Wallinger et al. 2021)

The most complete controlled comparison of abstract (non-embedded) set visualisations
([Wallinger, Jacobsen, Kobourov & Nöllenburg, 2021](https://doi.org/10.1109/TVCG.2021.3074615),
IEEE TVCG 27(6):2821–2832; preprint [arXiv:2101.08155](https://arxiv.org/abs/2101.08155)).

- **Systems:** EulerView (Euler diagrams), LineSets (overlay), MetroSets (metro-map/node-link).
- **Participants:** 120 completed instances, recruited online via social media; 18+, no known colour
  vision deficiency; 53% under 30, 73% post-secondary education, mean self-rated visualisation
  familiarity 2.7/5. A pilot with 4 experts and 6 lay people reshaped the design — notably the study
  had to be **split in two** because running all tasks at both sizes took ~45 minutes and tired
  participants.
- **Data:** Spotify artist–genre data. **Small** `|U| = 30, |E| = 6`; **large** `|U| = 60, |E| = 8`.
  The authors bound the study deliberately: their focus "limits the size of datasets to less than ten
  sets and fewer than a hundred elements. Datasets larger than that require interaction and
  navigation (e.g., filtering, zooming, panning)."
- **Tasks:** six static tasks, three element-based (T1 find elements of a set; T2 find sets
  containing an element; T3 find elements by joint membership) and three set-based (T4 analyse
  intersection relation; T5 which sets overlap a given set; T6 compare intersection cardinalities).
  T1–T5 were scored correct only if *every* subtask was right.
- **Design:** 3 systems × 6 tasks = 18 trials per participant; five phases (consent, demographics,
  tutorial, study, questionnaire).

Selected accuracy means (E = EulerView, L = LineSets, M = MetroSets; 30/60 = dataset size):

| Task | E30 | L30 | M30 | E60 | L60 | M60 |
|---|---|---|---|---|---|---|
| T1 find elements of a set | 0.97 | 0.97 | 1.00 | 0.74 | 0.98 | 0.95 |
| T2 find sets containing an element | 0.33 | 0.69 | 0.95 | 0.88 | 0.93 | 0.83 |
| T3 elements by joint membership | 0.86 | 0.97 | 0.83 | **0.16** | 0.95 | 0.98 |
| T4 analyse intersection relation | 0.33 | 0.97 | 0.93 | 0.55 | 0.95 | 0.91 |

(Table 1 of [Wallinger et al., 2021](https://arxiv.org/abs/2101.08155).)

**Findings.** Post-hoc testing confirmed significant differences on all six tasks. The scalability
result is the one to remember: "For all of the tasks except T5, MetroSets' performance did not
significantly degrade" as the dataset grew, whereas EulerView collapsed (T3 falls from 0.86 to 0.16).
The conclusion: "MetroSets scales better and performs more consistently than EulerView or LineSets,
and is also better-liked" (ibid.).

**Caveat for KHGs.** These are *static, non-interactive* stimuli, on sets of ≤ 8, with no roles, no
direction, no attributes. A knowledge hypergraph is heavier on every axis. The result transfers as a
*warning about Euler diagrams*, not as an endorsement of MetroSets for KHGs.

---

## 3. Spatial / embedded set visualisation: the overlay studies

These test overlays on *pre-embedded* points (map or scatter positions fixed), which is the
Bubble Sets / LineSets / KelpFusion family.

| Study | Systems | N | Data | Result |
|---|---|---|---|---|
| [Alper, Riche, Ramos & Czerwinski, 2011](https://doi.org/10.1109/TVCG.2011.186) | LineSets vs Bubble Sets | 12 | 3–5 sets, 50–200 elements, spatial + social-network; 4 tasks | LineSets better for detailed tasks and preference; otherwise no significant differences |
| [Meulemans, Riche, Speckmann, Alper & Dwyer, 2013](https://doi.org/10.1109/TVCG.2013.76) | KelpFusion vs LineSets vs Bubble Sets | 13 | geographic, 4–5 sets, 12–49 elements; 4 tasks | no significant difference between KelpFusion and LineSets; **both outperformed Bubble Sets** |
| [Rodgers et al.](https://doi.org/10.1109/TVCG.2021.3074615) (reported by Wallinger et al.) | Bubble Sets, LineSets, KelpFusion, EulerView, SetNet | crowdsourced | 11–64 elements, 3–7 sets, 42–162 network edges; combined set+network tasks | SetNet and EulerView **significantly outperform** the other three |
| [Baimagambetov et al.](https://doi.org/10.1109/TVCG.2021.3074615) (reported by Wallinger et al.) | SetNet, Bubble Sets, WebCola | quantitative, not human | 2–8 sets, 10–100 elements, 40–170 edges | Bubble Sets least inaccurate; no clear winner on ineffectiveness |

Two things follow. First, **the ranking flips with the task**: EulerView is worst in the abstract
study and among the best when set *and* network structure must be read together. Second, sizes in
this whole literature are tiny — the largest is 200 elements and 8 sets.

`[unverified]` The exact bibliographic details of the Rodgers et al. (SetNet) and Baimagambetov et
al. studies were taken from Wallinger et al.'s related-work section and were not independently
fetched.

---

## 4. Diagrams without individual elements

Where sets are shown but members are not, only set-based tasks apply.

- **Linear diagrams beat Euler diagrams.** Chapman et al. compared diagram types empirically and
  found linear diagrams "superior to prominent set visualization techniques, namely Euler and Venn
  diagrams" ([Chapman, Stapleton, Rodgers, Micallef & Blake, 2014](https://doi.org/10.1007/978-3-662-44043-8_18)).
  Wallinger et al. summarise the broader picture: "linear diagrams outperformed Euler diagrams and
  were on par with mosaic diagrams" ([Wallinger et al., 2021](https://doi.org/10.1109/TVCG.2021.3074615)).
- **Design principles for linear diagrams** come from seven crowdsourced studies with 1,760
  participants ([Rodgers, Stapleton & Chapman, 2015](https://doi.org/10.1145/2810012), ACM TOCHI
  22(6)).
- **Which Euler well-formedness properties matter** was tested directly: not all of the classical
  properties help readers, and the paper says which to enforce
  ([Rodgers, Zhang & Purchase, 2012](https://doi.org/10.1109/TVCG.2011.143)).

---

## 5. Studies on hypergraph-specific (not set-specific) techniques

There are only a handful, and none is a large controlled comparison.

| Technique | Evaluation | Strength of evidence |
|---|---|---|
| **PAOH** | formative usability study, **9 participants**, publication data, plus two digital-humanities case studies; participants could interpret the display "without training" ([Valdivia, Buono, Plaisant, Dufournaud & Fekete, 2021](https://doi.org/10.1109/TVCG.2019.2933196)) | formative, single-condition; establishes learnability, not superiority |
| **HyperStorylines** | comparative study against **PAOHVis** with data-journalism-inspired tasks; HyperStorylines "takes some practice to master" but performed better for identifying and characterising relationships, and was preferred ([Peña-Araya, Xue, Pietriga, Amsaleg & Bezerianos, 2022](https://doi.org/10.1177/14738716211045007)) | the only head-to-head comparison of two dynamic-hypergraph techniques found |
| **TimeSets** | case study and user study; reported as outperforming KelpFusion ([Nguyen, Xu, Walker & Wong, 2016](https://doi.org/10.1177/1473871615605347)) | single-paper evidence |
| **Radial hypergraph layout** | "evaluated in a small user study" ([Kerren & Jusufi, 2013](https://doi.org/10.2312/PE.EuroVisShort.EuroVisShort2013.025-029), as characterised by [Fischer et al., 2021](https://arxiv.org/abs/2107.13936)) | small |
| **Extra-node vs clique expansion** | qualitative *and* quantitative demonstration that extra-nodes retain more information and induce less clutter ([Ouvrard, Le Goff & Marchand-Maillet, 2017](https://arxiv.org/abs/1707.00115)) | algorithmic metrics, no human subjects |
| **Hyper-Matrix** | case study and formative evaluation with law-enforcement domain experts ([Fischer, Arya, Streeb, Seebacher, Keim & Worring, 2021](https://doi.org/10.1109/TVCG.2020.3030408)) | formative |
| **Hypergraph→graph conversion** | multi-metric evaluation of how the conversion affects a cooperative-work visualisation ([Xiong, Mu, Yang, Xie & Lu, 2024](https://doi.org/10.1007/978-981-99-9637-7_15)) | metric-based |

Fischer et al.'s survey scores evaluation across all 14 catalogued approaches and observes that
"only a few approaches provide no evaluation at all", that many are case studies rather than user
studies, and that a *quantitative* study is rare
([Fischer, Frings, Keim & Seebacher, 2021](https://arxiv.org/abs/2107.13936)).

---

## 6. Bipartite vs subset: what is and is not known

This is the decision that matters most for a KHG, and it is **not** settled by human-subjects
evidence. What exists:

- **For bipartite/extra-node:** the information-theoretic and clutter argument
  ([Ouvrard et al., 2017](https://arxiv.org/abs/1707.00115)); the linear cost `n` links versus
  `n(n−1)/2` for the clique ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)); linear-time
  planarity via Zykov; and universal adoption in KHG systems
  ([knowledge-hypergraph-specific-visualization.md](knowledge-hypergraph-specific-visualization.md)).
- **For subset/region:** it matches how people sketch sets, and every element-based accuracy result
  above was obtained on region or line encodings — but on ≤ 8 sets.
- **Against both:** Fischer et al. rate node-link approaches as supporting "few (Venn diagram) up to
  several dozens" of hyperedges, and matrix/timeline approaches as reaching "several hundred nodes
  and hyperedges" ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

`[unverified]` This KB found **no controlled study that compares a bipartite/extra-node drawing of a
hypergraph against a subset-standard drawing of the same hypergraph on the same tasks.** That is a
concrete, cheap, publishable experiment and it is listed as an open question in the section
[README.md](README.md).

---

## 7. Scalability limits per encoding

Combining the survey's bands ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936): very low
< 10, low 10–50, medium 50–200, high 200–1000, very high > 1000 nodes or hyperedges) with the
per-paper statements:

| Encoding | Practical ceiling | Evidence |
|---|---|---|
| Venn diagram | < 10 sets | very low band ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)) |
| Euler diagram / EulerView | ~6–8 sets before accuracy collapses | T3 accuracy 0.86 → 0.16 from 6 to 8 sets ([Wallinger et al., 2021](https://arxiv.org/abs/2101.08155)) |
| Bubble Sets, Kelp Diagrams | low band, 10–50 | [Fischer et al., 2021](https://arxiv.org/abs/2107.13936) |
| LineSets | ≤ 8 sets, ≤ 60 elements tested | [Wallinger et al., 2021](https://doi.org/10.1109/TVCG.2021.3074615) |
| Colour-coded hyperedge lines | ~a dozen hyperedges (colour exhaustion) | "traditional representations often use color to distinguish between hyperedges, [so] their scalability is severely limited" ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)) |
| MetroSets | ≤ 10 sets, ~100 elements; degrades gracefully in that range | [Wallinger et al., 2021](https://doi.org/10.1109/TVCG.2021.3074615) |
| Radial layout | medium, 50–200 | [Fischer et al., 2021](https://arxiv.org/abs/2107.13936) |
| Extra-node / bipartite | high, 200–1000 — the highest-rated node-link approach in the survey | [Fischer et al., 2021](https://arxiv.org/abs/2107.13936) (Ouvrard rated ■■■■□) |
| PAOH | 50–500 vertices by design; implementation handles hundreds of vertices and thousands of hyperedges | [Valdivia et al., 2021](https://doi.org/10.1109/TVCG.2019.2933196) |
| Set Streams | several hundred elements | [Agarwal & Beck, 2020](https://doi.org/10.1111/cgf.13988) |
| Hyper-Matrix / matrix views | high band; "do not support more than around thousand entities" | [Fischer et al., 2021](https://arxiv.org/abs/2107.13936) |
| Polygon metaphor + simplification | "thousands of hyperedges" | [Oliver, Zhang & Zhang, 2024](https://doi.org/10.1109/TVCG.2023.3326599) |
| Any single global view | fails at 10⁴ hyperedges | HyperGraphRAG's figures at 26,902 hyperedges are texture, not structure ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)); see [large-scale-and-interactive-exploration.md](large-scale-and-interactive-exploration.md) |

---

## 8. What a KHG project should conclude

1. **Do not use Euler/Venn above ~6 sets.** This is the best-supported negative result in the field.
2. **Colour cannot carry hyperedge identity** beyond about a dozen hyperedges.
3. **Interaction is not optional above ~100 elements** — Wallinger et al. explicitly scoped their
   static study below that line because larger data "require interaction and navigation".
4. **Prefer matrix or timeline views for anything in the hundreds**, on the survey's evidence.
5. **Treat the bipartite recommendation in this KB as argued, not measured.** It rests on
   information-theoretic, algorithmic and adoption arguments, plus one quantitative (non-human)
   comparison against clique expansion — not on a controlled readability study.
6. **Report the task category** whenever you claim an encoding "works": element-based, set-based and
   attribute-based results do not transfer to each other.

## Sources

- Alsallakh, B., Micallef, L., Aigner, W., Hauser, H., Miksch, S., Rodgers, P. "The State-of-the-Art of Set Visualization." Computer Graphics Forum 35(1):234–260, 2016. https://doi.org/10.1111/cgf.12722
- Wallinger, M., Jacobsen, B., Kobourov, S., Nöllenburg, M. "On the Readability of Abstract Set Visualizations." IEEE TVCG 27(6):2821–2832, 2021. https://doi.org/10.1109/TVCG.2021.3074615 ; preprint with Tables 1–2 https://arxiv.org/abs/2101.08155
- Alper, B., Riche, N., Ramos, G., Czerwinski, M. "Design Study of LineSets, a Novel Set Visualization Technique." IEEE TVCG 17(12):2259–2267, 2011. https://doi.org/10.1109/TVCG.2011.186
- Meulemans, W., Riche, N. H., Speckmann, B., Alper, B., Dwyer, T. "KelpFusion: A Hybrid Set Visualization Technique." IEEE TVCG 19(11):1846–1858, 2013. https://doi.org/10.1109/TVCG.2013.76
- Chapman, P., Stapleton, G., Rodgers, P., Micallef, L., Blake, A. "Visualizing Sets: An Empirical Comparison of Diagram Types." Diagrams 2014, LNCS 8578, pp. 146–160. https://doi.org/10.1007/978-3-662-44043-8_18
- Rodgers, P., Stapleton, G., Chapman, P. "Visualizing Sets with Linear Diagrams." ACM TOCHI 22(6):1–39, 2015. https://doi.org/10.1145/2810012
- Rodgers, P., Zhang, L., Purchase, H. "Wellformedness Properties in Euler Diagrams: Which Should Be Used?" IEEE TVCG 18(7):1089–1100, 2012. https://doi.org/10.1109/TVCG.2011.143
- Valdivia, P., Buono, P., Plaisant, C., Dufournaud, N., Fekete, J.-D. "Analyzing Dynamic Hypergraphs with Parallel Aggregated Ordered Hypergraph Visualization." IEEE TVCG 27(1):1–13, 2021. https://doi.org/10.1109/TVCG.2019.2933196
- Peña-Araya, V., Xue, T., Pietriga, E., Amsaleg, L., Bezerianos, A. "HyperStorylines: Interactively untangling dynamic hypergraphs." Information Visualization 21(1):38–62, 2022. https://doi.org/10.1177/14738716211045007
- Nguyen, P. H., Xu, K., Walker, R., Wong, B. L. W. "TimeSets: Timeline visualization with set relations." Information Visualization 15(3):253–269, 2016. https://doi.org/10.1177/1473871615605347
- Kerren, A., Jusufi, I. "A Novel Radial Visualization Approach for Undirected Hypergraphs." EuroVis Short Papers, 2013. https://doi.org/10.2312/PE.EuroVisShort.EuroVisShort2013.025-029
- Ouvrard, X., Le Goff, J.-M., Marchand-Maillet, S. "Networks of Collaborations: Hypergraph Modeling and Visualisation." arXiv:1707.00115, 2017. https://arxiv.org/abs/1707.00115
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014
- Fischer, M. T., Frings, A., Keim, D. A., Seebacher, D. "Towards a Survey on Static and Dynamic Hypergraph Visualizations." IEEE VIS 2021 short papers, pp. 81–85. https://arxiv.org/abs/2107.13936
- Fischer, M. T., Arya, D., Streeb, D., Seebacher, D., Keim, D. A., Worring, M. "Visual Analytics for Temporal Hypergraph Model Exploration." IEEE TVCG 27(2):550–560, 2021. https://doi.org/10.1109/TVCG.2020.3030408
- Xiong, Z., Mu, R., Yang, C., Xie, W., Lu, Q. "How Hypergraph-to-Graph Conversion Affects Cooperative Working Visualization: A Multi-metric Evaluation." CCIS, Springer, 2024, pp. 208–221. https://doi.org/10.1007/978-981-99-9637-7_15
- Agarwal, S., Beck, F. "Set Streams: Visual Exploration of Dynamic Overlapping Sets." Computer Graphics Forum 39(3):383–391, 2020. https://doi.org/10.1111/cgf.13988
- Oliver, P., Zhang, E., Zhang, Y. "Scalable Hypergraph Visualization." IEEE TVCG 30(1):595–605, 2024. https://doi.org/10.1109/TVCG.2023.3326599
- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025. https://arxiv.org/abs/2503.21322
