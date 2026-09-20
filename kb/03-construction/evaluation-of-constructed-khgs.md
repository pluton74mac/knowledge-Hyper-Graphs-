---
title: Evaluating constructed knowledge hypergraphs
type: survey
status: draft
tags: [hypergraph, n-ary, construction, evaluation, benchmarks, metrics, datasets, llm-as-judge]
created: 2026-09-20
updated: 2026-09-20
---

# Evaluating constructed knowledge hypergraphs

"Is this a good knowledge hypergraph?" decomposes into three questions that are measured differently and
often confused: are the extracted n-ary facts *correct*, does the hypergraph *cover* the source, and does
it *help* downstream. Hyper-KGGen states the decomposition explicitly, evaluating "along three
complementary axes, covering n-ary relation extraction, fact coverage, and downstream utility"
([Huang et al., 2026](https://arxiv.org/abs/2602.19543)). This note surveys the metrics and the datasets
for each, and what none of them measure.

## 1. Intrinsic: exact-match precision and recall over n-ary facts

The supervised n-ary extraction literature uses micro-averaged precision/recall/F1 with a **strict**
correctness rule. HyperRED: "For a predicted hyper-relational fact to be considered correct, the whole fact
f = (e_head, r, e_tail, q, e_value) must match the ground-truth fact in terms of relation label, qualifier
label and entity bounds" ([Chia et al., 2022](https://arxiv.org/abs/2211.10018)). Text2NKG uses the same
rule for arbitrary arity: "For a predicted n-ary relational fact to be considered correct, the entire fact
must match the ground facts completely" ([Luo et al., 2024](https://arxiv.org/abs/2310.05185)).

Two consequences:

- **Scores are low and comparisons are sharp.** CubeRE reports test P/R/F1 of 66.39 / 67.12 / 66.75 on
  HyperRED at the large model size, against 67.17 / 64.56 / 65.84 for a generative baseline
  ([Chia et al., 2022](https://arxiv.org/abs/2211.10018)). Reporting a *triplet-only* variant alongside the
  full-fact score, as that paper does (71.01 F1 for CubeRE when "considering only the triplet component"),
  is good practice: it separates "found the relation" from "found the roles".
- **Partial credit is discarded.** A hyperedge with nine of ten correct participants scores zero. For
  fixed-schema, short facts that is tolerable; for open hyperedges it is not.

## 2. Soft matching for open, description-valued hyperedges

LLM-built KHGs emit hyperedges as natural-language descriptions with no relation vocabulary (see
[LLM-based KHG construction](llm-based-khg-construction.md)), so exact match is undefined. Hyper-KGGen
gives the first published protocol for this case and states the problem well: "Evaluating n-ary relations
is significantly more challenging than binary relations due to their fuzzy boundaries and multi-argument
complexity. Hard matching often fails to capture partial successes (e.g., extracting 9 out of 10 nodes).
Therefore, we introduce a soft evaluation metric based on semantic distance."

The pipeline: "relation descriptions are encoded with [a sentence-embedding model]. We then compute a
cosine-similarity matrix and apply the Hungarian algorithm to find the optimal global matching between
predicted and ground-truth relations" ([Huang et al., 2026](https://arxiv.org/abs/2602.19543)). Global
assignment matters — greedy nearest-neighbour matching lets one gold hyperedge absorb several predictions
and inflates recall.

This is the right shape for open-schema KHG evaluation, with two caveats: the score inherits whatever
similarity biases the embedding model has, and description similarity can be high while the *participant
set* is wrong. A participant-set Jaccard term alongside the description similarity would separate the two;
no published metric does this.

## 3. Datasets used to evaluate n-ary extraction

| Dataset | Unit | Size | Notes |
|---|---|---|---|
| ACE 2005 | typed events with argument roles | multilingual corpus, LDC2006T06 | The closed-schema ancestor; see the [extraction note](n-ary-relation-extraction-from-text.md) |
| SciERC | entities, relations, coreference in abstracts | EMNLP 2018 | Multi-task scientific IE; the KG-construction framing of document IE ([Luan et al., 2018](https://arxiv.org/abs/1808.09602)) |
| DocRED | document-level binary relations | ACL 2019 | "at least 40.7% relational facts can only be extracted from multiple sentences" ([Yao et al., 2019](https://arxiv.org/abs/1906.06127)) |
| Re-DocRED | re-annotated DocRED | 4,053 documents re-annotated | Fixes false negatives; models gain ≈13 F1 ([Tan et al., 2022](https://arxiv.org/abs/2205.12696)) |
| HyperRED | sentence-level hyper-relational facts | train 39,840 sent. / 39,978 facts (distant), dev 1,000 / 1,220 (human), test 4,000 / 4,796 (human) | The main supervised n-ary benchmark ([Chia et al., 2022](https://arxiv.org/abs/2211.10018)) |
| HyperDocRED | document-level n-ary hyperedges | train 50 samples / 1,016 entities / 636 correlations (326 low-order, 310 high-order); test 100 / 2,127 / 1,371 (758 / 613) | Built by manually restructuring Re-DocRED into n-ary relations ([Huang et al., 2026](https://arxiv.org/abs/2602.19543)) |
| MINE | fact coverage over articles | 100 articles, 15 gold facts each | From KGGen ([Mo et al., 2025](https://arxiv.org/abs/2502.09956)) |
| UltraDomain | long-document QA corpora | "428 college textbooks", 18 domains | From MemoRAG ([Qian et al., 2024](https://arxiv.org/abs/2409.05591)); the corpus behind LightRAG's and HyperGraphRAG's domain evaluations |
| Text2KGBench | ontology-driven KG generation | Wikidata-TekGen: 10 ontologies / 13,474 sentences; DBpedia-WebNLG: 19 ontologies / 4,860 sentences | Adds ontology-conformance and hallucination metrics ([Mihindukulasooriya et al., 2023](https://arxiv.org/abs/2308.02357)) |

**The false-negative problem is the dominant measurement error, and n-ary makes it worse.** Re-DocRED
exists because "the annotation of DocRED is incomplete, with false negative samples being prevalent"; the
fix — re-annotating 4,053 documents by adding missed relation triples — moved state-of-the-art models by
around 13 F1 points ([Tan et al., 2022](https://arxiv.org/abs/2205.12696)). An n-ary annotation has
strictly more opportunities to be incomplete (a missing participant, a missing qualifier, a missing whole
fact), so reported recall on any n-ary benchmark should be read as a lower bound, and precision as
optimistic wherever unannotated-but-true facts are counted as errors. HyperRED's own mitigation is to train
on distant supervision but evaluate only on human-annotated splits.

**HyperDocRED is small.** 150 documents total is enough to rank systems and not enough to train them; it is
the only document-level n-ary hyperedge benchmark found in this research run, which makes it both important
and a single point of failure for the field.

**Schema-level evaluation is separate.** Where the pipeline induces a schema rather than consuming one (see
[schema induction](schema-induction-and-ontology-alignment.md)), the schema itself needs a score.
AutoSchemaKG reports "92% semantic alignment with human-crafted schemas with zero manual intervention"
([Bai et al., 2025](https://arxiv.org/abs/2505.23628)); Text2KGBench measures ontology conformance and
hallucination against a *given* ontology. Neither measures whether the induced relation and role names are
usable for querying or constraint checking.

## 4. Coverage and downstream utility

*Coverage* asks whether the constructed graph retains the information in the source. Hyper-KGGen's protocol
on MINE: "we formulate a fact-verification task with 15 ground-truth facts per article. For each query
fact, we retrieve the top 5 nodes with the highest semantic similarity and expand each retrieved node to
its 2-hop neighborhood to construct a candidate subgraph. The retrieved contexts are provided to an LLM,
which performs binary fact-checking conditioned on the assembled context evidence (1 if the retrieved
context supports the fact, 0 otherwise)" ([Huang et al., 2026](https://arxiv.org/abs/2602.19543)). This
measures graph + retrieval jointly, not the graph alone.

*Downstream utility* is measured by QA. HyperGraphRAG evaluates with three metrics: word-level **F1**
against a gold answer "following FlashRAG"; **Retrieval Similarity (R-S)**, "inspired by RAGAS", the cosine
similarity between concatenated retrieved knowledge and concatenated gold knowledge; and **Generation
Evaluation (G-E)**, which "uses [an LLM judge] to evaluate generation quality along seven dimensions:
Correctness, Relevance, Factuality, Comprehensiveness, Knowledgeability, Logical Coherence, and Diversity",
averaging the seven 0–10 dimension scores and then averaging that with the question's F1 — a deliberate
choice that "encourages alignment between LLM-judged quality and factual correctness"
([Luo et al., 2025](https://arxiv.org/abs/2503.21322)). Its evaluation set is 512 questions per domain over
five domains, sampled to contrast binary-source and n-ary-source questions; it reports gains over standard
RAG of "+7.45 (F1), +7.62 (R-S), and +3.69 (G-E)". Broken down by question type: "For Binary Source, it
improves F1, R-S, and G-E by +8.6, +8.8, and +4.4; for N-ary Source, the improvements are +5.3, +6.4, and
+2.9" — i.e. the *smaller* margin is on the n-ary questions, which cuts against the intuitive story and is
worth noticing.

Two honest caveats about downstream evaluation of a *construction* method:

- It confounds construction, retrieval and generation. Hyper-KGGen says so of its own results: "the gap
  between Hyper-KGGen and baselines is modest, since the graph mainly serves retrieval while the generation
  relies on raw text chunks".
- Ablations are the only way to attribute gains to the hypergraph. HyperGraphRAG's are informative:
  removing hyperedge retrieval drops F1 from 35.4 to 26.4, more than removing entity retrieval (to 29.8) or
  chunk retrieval (to 29.2).

## 5. LLM-as-judge: what it buys and what it costs

Head-to-head LLM judging became standard through GraphRAG, which adopted it "given the lack of gold
standard answers to our activity-based sensemaking questions" and scores four criteria:
**Comprehensiveness** ("How much detail does the answer provide to cover all aspects and details of the
question?"), **Diversity** ("How varied and rich is the answer in providing different perspectives and
insights on the question?"), **Empowerment** ("How well does the answer help the reader understand and make
informed judgments about the topic?") and, as "a 'control criterion'", **Directness** ("How specifically
and clearly does the answer address the question?")
([Edge et al., 2024](https://arxiv.org/abs/2404.16130)).

Three methodological points from that paper are worth copying:

1. **Use a control criterion.** Directness "is effectively in opposition to comprehensiveness and
   diversity, so we would not expect any method to win across all four criteria" — a method that wins
   everything is evidence of judge bias, not of quality.
2. **Cross-check with a mechanical measure.** They validate with claim-based metrics: comprehensiveness as
   "the average number of claims extracted from the answers", diversity as the average number of clusters
   those claims fall into.
3. **Report the agreement.** When they compared the LLM verdict with the claim-based verdict, they had to
   restrict to non-tie cases, "representing 33% and 39% of pairwise comparisons for comprehensiveness and
   diversity" — i.e. the two measures are only comparable on a minority of comparisons.

The known failure modes are documented: LLM judges exhibit "position, verbosity, and self-enhancement
biases, as well as limited reasoning ability", even though strong judges "can match both controlled and
crowdsourced human preferences well, achieving over 80% agreement"
([Zheng et al., 2023](https://arxiv.org/abs/2306.05685)). For *construction* evaluation specifically the
self-enhancement bias is acute: the same model family often extracts the graph and judges the answer.

## 6. Stability and reproducibility as metrics

An underused axis. Hyper-KGGen turns run-to-run variation into a training signal — "extraction stability
serves as a relative reward signal to induce high-quality skills from unstable traces and missed
predictions", with gold relations partitioned by how often K parallel extraction runs recover them
([Huang et al., 2026](https://arxiv.org/abs/2602.19543)). ATOM reports "stability" as a headline number
alongside "exhaustivity", claiming roughly 33% better stability and ~18% higher exhaustivity than its
baselines ([Lairgi et al., 2026](https://arxiv.org/abs/2510.22590)).

This deserves to be a standard reported metric: run the extractor K times on the same corpus and report the
Jaccard overlap of the resulting hyperedge sets. A pipeline whose output changes materially between runs
cannot support the incremental merging described in
[incremental construction](incremental-and-streaming-construction.md), regardless of its F1.

## 7. A recommended protocol (opinion)

For a paper or a project claiming a better KHG constructor:

1. **Strict n-ary F1** on a human-annotated set (HyperRED for sentences, HyperDocRED for documents), with
   the triplet-only or relation-only score reported alongside.
2. **Soft, globally-matched F1** (Hungarian assignment over description embeddings) if hyperedges are
   open-vocabulary, plus participant-set overlap.
3. **Arity-stratified scores.** Report F1 at |e| = 2, 3, 4, ≥5 separately. Aggregate scores on corpora
   dominated by binary facts hide exactly the capability being claimed. No published KHG paper does this.
4. **Coverage** against a fact list (MINE-style), reported separately from retrieval settings.
5. **Downstream QA** with ablations that remove the hyperedge structure, not just the whole graph.
6. **Stability** over K runs.
7. **Cost**: time and money per 1k tokens of corpus, as HyperGraphRAG reports.

## 8. Open problems

- **No arity-stratified results anywhere.** The central claim of the field — that n-ary representation
  helps — is not measured as a function of n.
- **No metric for hyperedge structure.** Precision/recall treat a hyperedge as a string or a tuple; nothing
  measures whether the *incidence structure* (which entities share which hyperedges) matches a gold
  hypergraph.
- **Provenance is never evaluated.** Every system attaches `source_id`s; no benchmark checks whether they
  are right.
- **One document-level n-ary benchmark** (HyperDocRED, 150 documents) and one open-extraction coverage
  benchmark (MINE, 100 articles). Both are small and both are new.
- **Judge and extractor are usually from the same model family**, which no current KHG evaluation controls
  for.

## Sources

- Huang, R., Feng, Y., Xue, R., Ying, S., Yong, J.-H., Shi, C., Du, S., Gao, Y. "Hyper-KGGen: A Skill-Driven Knowledge Extractor for High-Quality Knowledge Hypergraph Generation." arXiv 2602.19543, 2026 (v2, 5 July 2026). https://arxiv.org/abs/2602.19543
- Chia, Y. K., Bing, L., Aljunied, S. M., Si, L., Poria, S. "A Dataset for Hyper-Relational Extraction and a Cube-Filling Approach." EMNLP 2022 / arXiv 2211.10018. https://arxiv.org/abs/2211.10018
- Luo, H., E, H., Yang, Y., Yao, T., et al. "Text2NKG: Fine-Grained N-ary Relation Extraction for N-ary relational Knowledge Graph Construction." NeurIPS 2024 / arXiv 2310.05185. https://arxiv.org/abs/2310.05185
- Yao, Y., Ye, D., Li, P., Han, X., et al. "DocRED: A Large-Scale Document-Level Relation Extraction Dataset." ACL 2019 / arXiv 1906.06127. https://arxiv.org/abs/1906.06127
- Tan, Q., Xu, L., Bing, L., Ng, H. T., Aljunied, S. M. "Revisiting DocRED — Addressing the False Negative Problem in Relation Extraction." EMNLP 2022 / arXiv 2205.12696. https://arxiv.org/abs/2205.12696
- Luan, Y., He, L., Ostendorf, M., Hajishirzi, H. "Multi-Task Identification of Entities, Relations, and Coreference for Scientific Knowledge Graph Construction." EMNLP 2018 / arXiv 1808.09602. https://arxiv.org/abs/1808.09602
- Linguistic Data Consortium. "ACE 2005 Multilingual Training Corpus", LDC2006T06, 2006. https://catalog.ldc.upenn.edu/LDC2006T06
- Mo, B., Yu, K., Kazdan, J., Cabezas, J., et al. "KGGen: Extracting Knowledge Graphs from Plain Text with Language Models." arXiv 2502.09956, 2025 (rev. November 2025). https://arxiv.org/abs/2502.09956
- Qian, H., Liu, Z., Zhang, P., Mao, K., Lian, D., Dou, Z., Huang, T. "MemoRAG: Boosting Long Context Processing with Global Memory-Enhanced Retrieval Augmentation." The Web Conference 2025 / arXiv 2409.05591, 2024. https://arxiv.org/abs/2409.05591
- Mihindukulasooriya, N., Tiwari, S., Enguix, C. F., Lata, K. "Text2KGBench: A Benchmark for Ontology-Driven Knowledge Graph Generation from Text." ISWC 2023 / arXiv 2308.02357. https://arxiv.org/abs/2308.02357
- Luo, H., E, H., Chen, G., Zheng, Y., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025; arXiv:2503.21322 (v3, 21 October 2025). https://arxiv.org/abs/2503.21322
- Edge, D., Trinh, H., Cheng, N., Bradley, J., et al. "From Local to Global: A Graph RAG Approach to Query-Focused Summarization." arXiv 2404.16130, 2024 (rev. 2025). https://arxiv.org/abs/2404.16130
- Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., et al. "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." NeurIPS 2023 Datasets and Benchmarks / arXiv 2306.05685. https://arxiv.org/abs/2306.05685
- Lairgi, Y., Moncla, L., Benabdeslem, K., Cazabet, R., Cléau, P. "ATOM: AdapTive and OptiMized dynamic temporal knowledge graph construction using LLMs." EACL 2026 / arXiv 2510.22590, 2025 (rev. January 2026). https://arxiv.org/abs/2510.22590
- Bai, J., Fan, W., Hu, Q., Zong, Q., et al. "AutoSchemaKG: Autonomous Knowledge Graph Construction through Dynamic Schema Induction from Web-Scale Corpora." arXiv 2505.23628, 2025. https://arxiv.org/abs/2505.23628
