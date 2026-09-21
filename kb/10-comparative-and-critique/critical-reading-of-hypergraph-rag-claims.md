---
title: A critical reading of hypergraph-RAG claims
type: comparison
status: draft
tags: [rag, hypergraph-rag, HyperGraphRAG, Hyper-RAG, HyperRAG, PRoH, GraphRAG, LightRAG, evaluation, reproducibility, benchmark, scepticism]
created: 2026-09-20
updated: 2026-09-21
---

# A critical reading of hypergraph-RAG claims

Since March 2025 a cluster of systems has claimed that representing retrieval corpora as knowledge
hypergraphs beats binary-graph RAG (GraphRAG, LightRAG, PathRAG, HippoRAG) and plain vector RAG.
The reported gains are large. This note reads the primary evidence closely and separates what is
**demonstrated**, what is **plausible but untested**, and what is **an artefact of how the
experiments were built**.

Summary judgement up front, stated as opinion and marked as such:

> **Opinion.** The n-ary extraction idea is sound and the engineering is real, but the published
> evidence for "hypergraph RAG beats graph RAG" is weaker than the headline numbers suggest. The
> two flagship 2025 systems use self-generated question sets, LLM-as-judge metrics, no variance
> reporting, and do not cite or compare against each other. The one large independent benchmark
> (GraphRAG-Bench, ICLR 2026) does not include any hypergraph method at all. Treat the claims as
> promising and unreplicated.

What the systems actually do — prompts, storage, merging — is described in
[../03-construction/llm-based-khg-construction.md](../03-construction/llm-based-khg-construction.md);
this note is about the evaluation.

---

## 1. The four systems and what they claim

| System | Venue / date | Claim |
|---|---|---|
| **HyperGraphRAG** ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)) | NeurIPS 2025; arXiv Mar 2025 | Over StandardRAG: "+7.45 (F1), +7.62 (R-S), and +3.69 (G-E)" averaged over five domains |
| **Hyper-RAG** ([Feng et al., 2025](https://arxiv.org/abs/2504.08758)) | arXiv, submitted 30 Mar 2025; published as *Nature Communications* 17(1):5778, 27 Apr 2026 ([DOI](https://doi.org/10.1038/s41467-026-71411-1)) | "improves accuracy by an average of 12.3% over direct LLM use and outperforms Graph RAG and Light RAG by 6.3% and 6.0%"; "a 35.5% performance improvement over Light RAG using a selection-based assessment" |
| **HyperRAG** (WWW 2026) | ACM Web Conference 2026, [DOI 10.1145/3774904.3792710](https://dl.acm.org/doi/10.1145/3774904.3792710) | "Reasoning N-ary Facts over Hypergraphs for Retrieval Augmented Generation" — metadata only; the ACM page returned HTTP 403 and was not read `[unverified]` |
| **PRoH** ([Zai et al., 2025](https://arxiv.org/abs/2510.12434)) | WWW 2026; arXiv Oct 2025, rev. Feb 2026 | "surpassing the prior SOTA model HyperGraphRAG by an average of 19.73% in F1 and 8.41% in Generation Evaluation (G-E) score" |

Note the shape of the ladder: each system's principal comparison is to the previous one, on the
previous one's own benchmark. That is normal in a young subfield and is also exactly the condition
under which benchmark-specific overfitting is invisible.

---

## 2. HyperGraphRAG, read closely

### 2.1 What is solid

- The baseline set is broad and current: NaiveGeneration, StandardRAG, GraphRAG, LightRAG, PathRAG,
  HippoRAG2 ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)).
- The same generation prompt is used for all methods — "To ensure fairness, we use the same
  generation prompt". Prompt parity is often skipped in this literature; here it is not.
- Code is public ([LHRLAB/HyperGraphRAG](https://github.com/LHRLAB/HyperGraphRAG)), so the results
  are in principle reproducible.
- Cost is reported honestly and unflatteringly (see §2.4).

### 2.2 The evaluation is built from the corpus it evaluates

> "For each of the five domains, we sample knowledge fragments one, two, and three hops away to
> construct questions with ground-truth answers verified by human annotators. We then categorize the
> questions into **Binary Source** and **N-ary Source**, based on whether the sampled knowledge of
> the question contains facts among n entities (n > 2)."
> ([Luo et al., 2025](https://arxiv.org/abs/2503.21322))

Three consequences.

1. **The questions are generated from the same corpus the system indexes.** This is standard practice
   in RAG papers and it is not fraud, but it means the benchmark measures *retrieval of the
   construction units*, not question answering as a user would pose it. The hop structure of the
   questions mirrors the hop structure of the index.
2. **The "N-ary Source" split is defined by the proposed method's own inductive bias.** A question is
   labelled n-ary if the fragment it was sampled from involves more than two entities — i.e. if it
   matches the unit HyperGraphRAG extracts. Baselines that do not extract that unit are being scored
   on a partition defined by their opponent's representation.
3. **One metric measures alignment with the question-construction process.** R-S "assesses the
   semantic similarity between the retrieved knowledge and the ground-truth knowledge used to
   construct the question". A method whose retrieval unit *is* the construction unit has a structural
   advantage on this metric that has nothing to do with answer quality. The +7.62 R-S gain should be
   heavily discounted; the +7.45 F1 (word overlap with an answer) and +3.69 G-E (LLM judge) are the
   informative numbers.

### 2.3 The internal result that cuts against the paper's thesis

The paper reports gains over StandardRAG split by source type:

> "For Binary Source, it improves F1, R-S, and G-E by +8.6, +8.8, and +4.4; for N-ary Source, the
> improvements are +5.3, +6.4, and +2.9, confirming its robustness."
> ([Luo et al., 2025](https://arxiv.org/abs/2503.21322))

**The gain is larger on binary questions than on n-ary questions.** If the mechanism were "n-ary
representation captures n-ary facts that binary representations fragment", the ordering should be
the other way round. The paper reads this as robustness; it is at least as consistent with the gain
coming from something other than arity — for example better chunk-plus-entity fusion, longer
retrieved context, or the confidence-weighted hyperedge descriptions acting as a summarisation layer.
The ablation (removing entity retrieval, hyperedge retrieval, chunk-retrieval fusion) is reported,
but I did not find an ablation that isolates *arity* — e.g. the same pipeline with every extracted
n-ary fragment split into pairwise edges `[unverified]`. That is the experiment the thesis needs.

### 2.4 Cost

From Table 3 ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)), construction cost per 1k
tokens and generation cost per 1k queries:

| Method | Construction time /1k tok | Construction $ /1k tok | Time /query | $ /1k queries |
|---|---|---|---|---|
| NaiveGeneration | 0 s | $0 | 0.131 s | $0.059 |
| StandardRAG | 0 s | $0 | 0.147 s | $1.016 |
| GraphRAG | 9.272 s | $0.0058 | 0.221 s | $1.836 |
| LightRAG | 5.168 s | $0.0081 | 0.359 s | $3.359 |
| PathRAG | 5.168 s | $0.0081 | 0.436 s | $3.496 |
| HippoRAG2 | 2.758 s | $0.0056 | 0.240 s | $3.438 |
| **HyperGraphRAG** | **3.084 s** | **$0.0063** | **0.256 s** | **$3.184** |

So the headline "+7.45 F1 over StandardRAG" comes with roughly **3.1× the query cost** ($3.184 vs
$1.016 per 1k queries) plus a construction pass StandardRAG does not need at all. Whether that trade
is worth it is a deployment question the paper does not attempt to answer, and the answer will differ
by corpus size and query volume.

### 2.5 A rhetorical issue worth flagging

The paper states three numbered **Propositions** with **Proofs**, and one of the proofs is:

> "Proposition 3. Retrieving knowledge on a knowledge hypergraph improves retrieval efficiency
> compared to methods based on ordinary binary graphs, leading to gains in generation quality.
> Proof. We provide experimental results in Sections 5.5 and 5.6 and proofs in Appendix B.3."
> ([Luo et al., 2025](https://arxiv.org/abs/2503.21322))

An empirical generalisation about LLM pipelines is not the kind of statement that admits a proof.
Labelling it a proposition with a proof lends deductive weight to an inductive claim. This is a
presentation choice, not a data problem, but it colours how the rest is read.

Meanwhile **Proposition 2** — "A bipartite graph can losslessly preserve and query a knowledge
hypergraph" — is true, provable, and concedes the sceptic's main point. The system stores its
hypergraph as a bipartite graph. See
[hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md) §1.

---

## 3. Hyper-RAG, read closely

Hyper-RAG's evaluation is weaker than HyperGraphRAG's on every axis I could check.

- **Question set: 50, LLM-generated.** "Prior to the experiments, 50 unique questions are randomly
  sampled from different chunks using the large models, ensuring that each LLM and augmentation
  strategy is evaluated on an identical set of queries" ([Feng et al., 2025](https://arxiv.org/abs/2504.08758)).
  Fifty open-ended questions is a small sample for a 12.3% claim, and no confidence intervals are
  reported.
- **No ground-truth answers, by design.** The paper argues existing closed-ended evaluation "remains
  inherently limited and somewhat biased" and proposes Scoring-Based Assessment (an LLM assigns
  0–100 on five dimensions) and Selection-Based Assessment (an LLM votes pairwise on eight metrics).
  Both are LLM-as-judge. The much-quoted "35.5% performance improvement over Light RAG" is a
  **pairwise win-rate**, not an accuracy delta, and win-rates are not comparable to accuracy
  percentages even though they share a "%" sign.
- **LLM-as-judge with LLM-generated questions and LLM-extracted knowledge** closes a loop in which
  the same family of models defines the task, produces the knowledge and grades the answers.
- The +12.3% headline is relative to *direct LLM answering*, not to a RAG baseline. Against LightRAG
  and GraphRAG the claimed margins are 6.0% and 6.3%.

What the paper does well: it evaluates across six different base LLMs, which is more model diversity
than most RAG papers manage, and it reports a lightweight variant with an honest speed/quality
trade-off.

---

## 4. The literature does not talk to itself

Checked mechanically on the full texts of the two arXiv PDFs (2026-09-20):

- occurrences of "HyperGraphRAG" in the Hyper-RAG paper: **0**
- occurrences of "Hyper-RAG" in the HyperGraphRAG paper: **0**

Two systems, posted within a month of each other (2503.21322 and 2504.08758), both claiming
hypergraph-structured RAG, with overlapping baselines and no mutual comparison and no shared
benchmark. There is, as of this writing, **no published head-to-head evaluation of HyperGraphRAG
against Hyper-RAG** that I could find `[unverified — absence of evidence from the searches run in
this session, not a proof of absence]`.

This is the clearest structural weakness of the subfield: four systems, four benchmarks, four metric
suites, one direction of comparison (downwards, to binary-graph baselines).

Addendum (2026-09-21): there is a *fifth* system that predates all four and is cited by none of
them. **EbmKG / IdepRAG** ([Dou et al., 2025](https://arxiv.org/abs/2503.16530)) was posted on 18 March 2025, nine
days before HyperGraphRAG v1; its hyperedges are medical evidence units under topic hyperedges,
retrieved by random walk plus LLM-scored ranking. Its baselines are VectorRAG and Microsoft GraphRAG
only, its six test sets are its own, and — the detail worth keeping — **GraphRAG comes out below
no retrieval at all** on both Qwen2.5-72B (76.3 vs 79.1) and GPT-4o (74.2 vs 77.6). That is the same
direction as the Han et al. and GraphRAG-Bench findings in §5, from a group with no stake in the
hypergraph-versus-graph question beyond its own system. It also has no hypergraph-versus-graph
ablation, the same gap as the others (checklist item 3), and its data link was dead when checked.

---

## 5. The independent evidence: GraphRAG-Bench (ICLR 2026)

[Xiang et al., 2025/2026](https://arxiv.org/abs/2506.05690) ("When to use Graphs in RAG",
accepted at ICLR 2026) is the largest neutral benchmark in this area. It is not a hypergraph paper,
which is exactly why it matters.

**It does not evaluate any hypergraph method.** The seven graph-RAG systems in its main table are
MS-GraphRAG, HippoRAG, HippoRAG2, LightRAG, Fast-GraphRAG, RAPTOR and Lazy-GraphRAG, compared against
basic RAG with and without reranking (Table 3); further systems (KGP, StructRAG, KET-RAG) appear in
the appendix `[unverified — appendix not read]`. So the hypergraph claims remain untested by the field's most careful
external evaluation.

Its findings nevertheless bear directly on them.

**Finding 1 — plain RAG is not the pushover the hypergraph papers imply.** Accuracy (ACC) from
Table 3 ([Xiang et al., 2026](https://arxiv.org/abs/2506.05690)):

| Task | Novel: basic RAG (w/ rerank) | Novel: best GraphRAG | Medical: basic RAG (w/ rerank) | Medical: best GraphRAG |
|---|---|---|---|---|
| Fact retrieval (L1) | **60.92** | HippoRAG2 60.14 | 64.73 | HippoRAG2 **66.28** |
| Complex reasoning (L2) | 42.93 | HippoRAG2 **53.38** | 58.64 | HippoRAG2 **61.98** |
| Contextual summarize (L3) | 51.30 | MS-GraphRAG **64.40** | 65.75 | Fast-GraphRAG **67.88** |
| Creative generation (L4) | 38.26 | HippoRAG2 **48.28** | 60.61 | HippoRAG2 **68.05** |

Their Obs.1: "basic RAG is comparable to or outperforms GraphRAG in simple fact retrieval tasks that
does not require complex reasoning across connected concepts". Obs.2: "GraphRAG models show a clear
advantage in complex reasoning, Contextual Summarize, and creative generation."

This *corroborates* an odd result in the HyperGraphRAG paper — there, GraphRAG, LightRAG, PathRAG and
HippoRAG2 all scored **below** StandardRAG overall, which the authors attribute to "knowledge
fragmentation, sparsified retrieval, and incomplete context reconstruction". Two independent papers
finding that graph RAG under-performs vector RAG on fact-style questions is real signal. But it also
weakens the hypergraph pitch: if the right comparison for a knowledge-hypergraph system is *plain
vector RAG* rather than GraphRAG, then a +7.45 F1 at 3× the cost is a much less exciting result than
"beats all graph baselines".

**Finding 2 — the token bill is the real story.** Average prompt tokens (Tables 6–7):

| | V-RAG | MS-GraphRAG (local) | MS-GraphRAG (global) | HippoRAG2 | LightRAG | Fast-GraphRAG | RAPTOR | HippoRAG |
|---|---|---|---|---|---|---|---|---|
| Novel | 879 | 38,707 | 331,375 | 1,008 | 100,832 | 4,204 | 3,441 | 7,208 |
| Medical | 954 | 39,821 | 332,881 | 1,020 | 100,310 | 4,298 | 3,510 | 7,342 |

Their Obs.8 describes MS-GraphRAG(global) as reaching "up to 4×10⁴ tokens" and LightRAG "≈10⁴", which
does not match their own Tables 6–7 (3.3×10⁵ and 1.0×10⁵ respectively); Obs.9 gives a range of
"7,800 to 40,000 tokens". The prose and tables appear to be measuring different things, or one of
them contains an error — flagged here because the discrepancy is an order of magnitude and readers
quoting the text will get the wrong number `[unverified — I could not determine which figure is
intended]`. Either way the direction is unambiguous: structured RAG costs 4×–350× the prompt tokens
of vector RAG.

**Finding 3 — latency.** The paper cites a report that GraphRAG "introduces 2.3 × higher latency on
average (Zhou et al., 2025)" ([Xiang et al., 2026](https://arxiv.org/abs/2506.05690)); the underlying
source was not consulted here `[unverified]`.

Complementary evidence, same direction: [Han et al., 2025/2026](https://arxiv.org/abs/2502.11371)
("RAG vs. GraphRAG: A Systematic Evaluation and Key Insights") find that RAG "excels on detailed
single-hop queries" while GraphRAG methods "excel on multi-hop queries"; and an AAAI'26 paper argues
pre-built graphs are often unnecessary because "the pre-built graph may not align with these required
structures, resulting in ineffective knowledge retrieval"
([arXiv:2508.06105](https://arxiv.org/abs/2508.06105)).

---

## 6. Reproducibility status

| | Code public | Data public | Seeds / variance reported | Independent replication found |
|---|---|---|---|---|
| HyperGraphRAG | Yes ([GitHub](https://github.com/LHRLAB/HyperGraphRAG)) | Datasets derived from UltraDomain + a hypertension guideline; construction scripts in repo | **No variance, error bars or repeated runs found in the paper** | None found `[unverified]` |
| Hyper-RAG | Yes ([GitHub](https://github.com/iMoonLab/Hyper-RAG)) | NeurologyCrop + nine further corpora | Scores are averages over five metrics, not over runs | None found `[unverified]` |
| HyperRAG (WWW 2026) | Not checked (ACM page 403) `[unverified]` | — | — | — |
| PRoH | arXiv preprint; repository not checked `[unverified]` | — | — | — |
| GraphRAG-Bench | Yes ([GitHub](https://github.com/GraphRAG-Bench/GraphRAG-Benchmark)); "the evaluation code is standardized across all frameworks to ensure fair comparison" | Yes (Gutenberg novels + NCCN clinical guidelines) | Not checked | It *is* the independent evaluation |

The single highest-value missing artefact is an entry for HyperGraphRAG (and Hyper-RAG) on
GraphRAG-Bench's leaderboard. Until that exists, the claim "hypergraph RAG > graph RAG" rests
entirely on self-reported benchmarks.

---

## 8. Second-pass additions (2026-09-21)

Four things found on a second reading of the primary sources, all bearing on §1's "ladder".

**8.1 PRoH's headline is percentage points, not per cent.** The v2 full text gives the per-domain F1
behind "19.73%": Medicine 35.35 → 52.94, Agriculture 33.89 → 56.67, CS 31.30 → 54.15, Legal
43.81 → 58.81, Mix 48.71 → 69.16 ([Zai et al., 2025/2026](https://arxiv.org/abs/2510.12434), Table 1).
The mean difference is 19.73 **F1 points**; read as a relative gain it would be ~56 %. The same
applies to "+8.41% in G-E". This KB's earlier phrasing has been corrected in
[../07-applications/retrieval-augmented-generation.md](../07-applications/retrieval-augmented-generation.md) §5.

**8.2 PRoH's strongest number comes from a split the paper itself adds, and the split is easier.**
The "+44.87% in F1 in the CS domain" is measured on **200 generated questions per domain sampled
3–6 hops away**, introduced in the same paper. On that split HyperGraphRAG scores 52.40 in
Agriculture and 64.55 in Mix, against 33.89 and 48.71 on the main 1–3 hop split — i.e. *both* systems
do better on the nominally harder questions, so hop distance in the extracted hypergraph is not
tracking difficulty. No human verification of the long-range split is described `[unverified]`.
Checklist item 1 (§7) applies with extra force when the benchmark extension and the claim ship
together.

**8.3 Efficiency is reported for a configuration the headline does not use.** PRoH's Table 4 compares
tokens per question for **PRoH-L** — an embedding-only-EWO variant that drops the LLM entity scorer —
against HyperGraphRAG (−34.82 % in CS, −30.07 % Agriculture, but **+30.54 % in Legal**). The token
cost of **full PRoH**, which produces every accuracy number quoted above, is not reported against
HyperGraphRAG; only a module-wise breakdown (Figure 6) and no latency or LLM-call count. This is
still the best cost accounting in the subfield, which is the problem: checklist item 6 has not been
met by anyone. Nobody has plotted accuracy against a token budget, so every "X beats Y" compares two
points on two unknown curves.

**8.4 The reference baseline has been superseded by its own authors, and papers keep beating the old
one.** **Graph-R1** ([Luo et al., 2025/2026](https://arxiv.org/abs/2507.21892), ICML 2026) is by the
HyperGraphRAG team: same style of extracted knowledge hypergraph, but an RL-trained
think–query–retrieve agent (GRPO, format + token-F1 reward). It reports average F1 **57.82** against
HyperGraphRAG's **29.40** on six open-domain datasets with Qwen2.5-7B. Two consequences. First, this
is the field's first substantial *internal* falsification: the gain came from the retrieval policy,
not the representation, which is precisely the confound §2.3 flagged. Second, a 2026 paper whose
contribution is stated as "beats HyperGraphRAG" — including H²RAG at PAKDD 2026
([Yang, Huang, Chen and Cai, 2026](https://doi.org/10.1007/978-981-92-1468-6_14)), which reports
20.33 % EM / 14.61 % F1 / 11.53 % Generalized Score over HyperGraphRAG and HiRAG but does not compare
against PRoH or Graph-R1 — is beating a baseline its own community retired. Add to the checklist:
**9. Which version of the ladder is the baseline?**

A fuller treatment of the planned and hierarchical systems, with their cost tables, is in
[../07-applications/hierarchical-and-planned-hypergraph-retrieval.md](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md).

---

## 7. A checklist for reading the next hypergraph-RAG paper

1. **Who wrote the questions?** If the authors generated them from the indexed corpus, the benchmark
   measures index-alignment, not QA.
2. **Is there a metric that rewards retrieving the construction unit?** (R-S and its relatives.)
   Discount it.
3. **Is there an arity ablation?** Same pipeline, hyperedges split into pairwise edges. Without it,
   "n-ary helps" is unsupported by the experiment.
4. **Is plain vector RAG in the baseline table, tuned, with reranking?** Both GraphRAG-Bench and
   HyperGraphRAG's own results show it is the baseline to beat.
5. **Variance.** Any LLM pipeline evaluated once, with no seeds and no intervals, on ≤ a few hundred
   questions, is reporting noise plus effect.
6. **Cost per query and tokens per query, next to the accuracy.**
7. **Does it compare against the other hypergraph systems?** So far, none do.
8. **Is "hypergraph" doing work, or is it a storage detail?** If the system stores a bipartite graph
   (HyperGraphRAG does, by its own Proposition 2), the contribution is the *extraction unit*, not
   the data structure — and it should be evaluated as such.

Related: [limitations-and-failure-modes.md](limitations-and-failure-modes.md) §5 (evaluation
leakage), §8 (extraction error compounding), [open-debates.md](open-debates.md) §3 (are the gains
robust?), and
[../03-construction/llm-based-khg-construction.md](../03-construction/llm-based-khg-construction.md)
for the pipelines themselves.

## Sources

- Feng, Y., Hu, H., Hou, X., Liu, S., Ying, S., Du, S., Hu, H., Gao, Y. "Hyper-RAG: Combating LLM Hallucinations using Hypergraph-Driven Retrieval-Augmented Generation." arXiv:2504.08758, submitted 30 March 2025; *Nature Communications* 17(1):5778, 27 Apr 2026. https://arxiv.org/abs/2504.08758 ; https://doi.org/10.1038/s41467-026-71411-1 ; code https://github.com/iMoonLab/Hyper-RAG
- Han, H., Ma, L., Wang, Y., Shomer, H., Lei, Y., Qi, Z., Guo, K., Hua, Z., Long, B., Liu, H., Aggarwal, C. C., Tang, J. "RAG vs. GraphRAG: A Systematic Evaluation and Key Insights." arXiv:2502.11371, 17 Feb 2025, rev. 4 Mar 2026. https://arxiv.org/abs/2502.11371
- Dou, C., Zhang, Y., Jin, Z., Jiao, W., Zhao, H., Zhao, Y., Tao, Z. "Enhancing LLM Generation with Knowledge Hypergraph for Evidence-Based Medicine." arXiv:2503.16530, 18 Mar 2025. https://arxiv.org/abs/2503.16530 — Table 1 read in the HTML full text; the paper cites neither HyperGraphRAG nor Hyper-RAG, and neither cites it (checked mechanically on the arXiv full texts of all three — HyperGraphRAG v3, Hyper-RAG latest, this paper v1 — on 2026-09-21; the Nature Communications version of Hyper-RAG not checked).
- Luo, H., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025; arXiv:2503.21322. https://arxiv.org/abs/2503.21322 ; code https://github.com/LHRLAB/HyperGraphRAG
- "PRoH: Dynamic Planning and Reasoning over Knowledge Hypergraphs for Retrieval-Augmented Generation." Zai, X., Tan, X., Wang, X., Liu, Q., Xu, X., Zhang, W. arXiv:2510.12434, 14 Oct 2025, rev. 18 Feb 2026; ACM Web Conference 2026, DOI 10.1145/3774904.3792611. https://arxiv.org/abs/2510.12434
- "HyperRAG: Reasoning N-ary Facts over Hypergraphs for Retrieval Augmented Generation." *Proceedings of the ACM Web Conference 2026*. DOI 10.1145/3774904.3792710. https://dl.acm.org/doi/10.1145/3774904.3792710 (metadata only; page returned HTTP 403)
- Xiang, Z., Wu, C., Zhang, Q., Chen, S., Hong, Z., Huang, X., Su, J. "When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation." ICLR 2026; arXiv:2506.05690, June 2025. https://arxiv.org/abs/2506.05690 ; benchmark https://github.com/GraphRAG-Bench/GraphRAG-Benchmark
- "You Don't Need Pre-built Graphs for RAG" (LogicRAG), AAAI 2026. arXiv:2508.06105. https://arxiv.org/abs/2508.06105
- Yang, H., Huang, L., Chen, M., Cai, J. "H²RAG: A Hierarchical Knowledge and Hypergraph Reasoning Framework for Retrieval-Augmented Generation." PAKDD 2026, Lecture Notes in Computer Science vol. 16600, pp. 238–250, Springer Singapore, first online 9 June 2026. https://doi.org/10.1007/978-981-92-1468-6_14 (abstract and publisher metadata only; full text paywalled, checked 2026-09-21)
- Luo, H., E, H., Chen, G., Lin, Q., Guo, Y., Xu, F., Kuang, Z., Song, M., Wu, X., Zhu, Y., Luu, A. T. "Graph-R1: Towards Agentic GraphRAG Framework via End-to-end Reinforcement Learning." ICML 2026; arXiv:2507.21892, 29 Jul 2025 (rev. 2 Jun 2026); code https://github.com/LHRLAB/Graph-R1. https://arxiv.org/abs/2507.21892
- Huang, H., Huang, Y., Yang, J., Pan, Z., Chen, Y., Ma, K., Chen, H., Cheng, J. "Retrieval-Augmented Generation with Hierarchical Knowledge" (HiRAG). EMNLP 2025 Findings; arXiv:2503.10150. https://arxiv.org/abs/2503.10150
