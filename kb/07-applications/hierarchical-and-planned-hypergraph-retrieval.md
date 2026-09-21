---
title: Hierarchical and planned retrieval over knowledge hypergraphs
type: survey
status: draft
tags: [hypergraph, RAG, retrieval, planning, PRoH, H2RAG, HiRAG, Graph-R1, reinforcement-learning, community-detection, cost, token-budget, evaluation]
created: 2026-09-21
updated: 2026-09-21
---

# Hierarchical and planned retrieval over knowledge hypergraphs

[retrieval-augmented-generation](retrieval-augmented-generation.md) surveys hypergraph-RAG systems
one by one. This note reads the same literature *along the retrieval axis*: what the system does
between receiving a question and assembling a context window. Three designs are now distinguishable,
and they arrived roughly in order.

| | Retrieval design | Representative systems | What is being optimised |
|---|---|---|---|
| **G1** (2024–2025) | one-shot k-NN over a flat bipartite store, fused with chunks | HyperGraphRAG, Hyper-RAG, OG-RAG | the *unit* that is embedded |
| **G2** (late 2025–2026) | multi-step traversal with a plan — prompted or learned | PRoH, HyperRAG (beam), Graph-R1, HyperGraphPro | *which* hyperedges get read, and when to stop |
| **G3** (2025–2026) | a summary layer above the hyperedges: communities, clusters, layers | HiRAG, H²RAG, HHS-RAG, EEG-MedRAG | *what exists to retrieve* above the fact level |

The generations are cumulative, not exclusive — H²RAG is a G3 index queried with a G1-style dual-layer
scorer, and PRoH traverses a G1 index. The useful claim is only that the *locus of the contribution*
moved: first the extraction unit, then the search procedure, then the index hierarchy.

---

## 1. Generation 1, and the argument it rests on

HyperGraphRAG's query path is a single pass: embed the question, retrieve top-k entities and top-k
hyperedges from two vector bases, fuse with chunk retrieval, generate. Nothing about the question
changes what is looked up second, because there is no second look-up. The mechanism and the numbers
are in [retrieval-augmented-generation §2](retrieval-augmented-generation.md#2-hypergraphrag-neurips-2025).

Its justification is three **Propositions** ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)).
Propositions 2 and 3 are discussed elsewhere in this KB
([hypergraph-vs-bipartite-graph-debate](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md) §1;
[critical-reading-of-hypergraph-rag-claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md) §2.5).
The first one, and the quantity behind it, are recorded here for completeness:

> **Proposition 1.** "Hypergraph-structured knowledge representation is more comprehensive than
> binary." The proof is information-theoretic: for an n-ary fact with n ≥ 3, the hypergraph encoding
> φ_H satisfies H(X | φ_H(X)) = 0 while the binary encoding φ_B gives H(X | φ_B(X)) > 0.

The supporting definition is an **information density** η_⋆ = I(X; Y_⋆) / ℒ_⋆ — mutual information
between the fact and its encoding, divided by expected code length under optimal encoding — with the
claim that η_H > η_B whenever n-ary facts are present ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)).

Two observations. First, Proposition 1 is a statement about *one particular* binary encoding — the
one that drops the joint membership of the participants. A reified binary encoding
(see [n-ary-relations-and-reification](../02-knowledge-representation/n-ary-relations-and-reification.md))
also has H(X | φ(X)) = 0, which is exactly what Proposition 2 concedes when it proves the bipartite
image lossless. The propositions are therefore not in tension only if "binary" means "projected",
and the paper does not say so. Second, η is never measured. No system in this literature reports
I(X; Y) or ℒ for its own index, so the density claim does the rhetorical work of a theorem while
remaining an assumption. The empirical proxy — tokens of context per correct answer — is what §5
below is about, and almost nobody reports it either.

---

## 2. Generation 2a: prompted planning — PRoH

**PRoH** ([Zai, Tan, Wang, Liu, Xu and Zhang, 2025/2026](https://arxiv.org/abs/2510.12434), WWW 2026,
[DOI](https://dl.acm.org/doi/10.1145/3774904.3792611); code announced at
`github.com/zaixjun/PRoH`, which returned HTTP 403 through this session's proxy on 2026-09-21, so
its contents are `[unverified]`) is the clearest statement of the G2 design. Three parts:

1. **Context-aware planning.** Before decomposition, PRoH builds a **plan context graph**: entities
   and hyperedges within d_p hops of the topic entities and the target hyperedges. The LLM plans
   against this sketch rather than against the question alone, so the plan is "structurally grounded"
   — it can only propose steps the index can actually serve.
2. **A live sub-question DAG.** Sub-questions are nodes of a DAG encoding logical dependency.
   Reasoning is posed as a **state-space search** where a state is (DAG, completion level); a
   transition fires when every sub-question at the current level resolves, and new sub-questions may
   be added as evidence arrives. Up to **K = 2** solution trajectories are carried concurrently.
   Note: the paper describes *multi-trajectory exploration and iterative DAG refinement*, not an
   explicit backtracking operator — the KB should not describe PRoH as "backtracking" `[unverified]`.
3. **Entity-Weighted Overlap (EWO) path retrieval.** Candidate next hyperedges are scored by their
   overlap with the current hyperedge, weighted by entity relevance:
   `EWO(e' | q_j, e) = AGG({ EW(v | q_j) : v ∈ V(e) ∩ V(e') })`, where an entity above an embedding
   similarity threshold θ_emb is scored by the LLM and others score zero, and AGG combines the mean
   (overall relevance) with the maximum (salient entity). This is the G2 analogue of PageRank-style
   diffusion: a *local*, query-conditioned edge weight rather than a global one.

**Numbers, stated correctly.** The headline "+19.73 % F1" is **percentage points of F1, not a
relative gain** — it is the mean of the per-domain differences below, on the KHQA benchmark
(HyperGraphRAG's own five-domain question set, GPT-4o-mini backbone, text-embedding-3-small):

| Domain | HyperGraphRAG F1 | PRoH-L F1 | PRoH F1 | Δ (PRoH) |
|---|---|---|---|---|
| Medicine | 35.35 | 45.63 | 52.94 | +17.59 |
| Agriculture | 33.89 | 50.47 | 56.67 | +22.78 |
| CS | 31.30 | 46.61 | 54.15 | +22.85 |
| Legal | 43.81 | 51.40 | 58.81 | +15.00 |
| Mix | 48.71 | 53.81 | 69.16 | +20.45 |

G-E (the LLM-judge score) moves by +8.41 points on average — e.g. Medicine 67.35 vs 59.35, CS 66.79
vs 57.94. Ablations on Agriculture: removing EWO guidance costs 5.27 F1, removing the planning
context 4.79, removing target-hyperedge matching 5.22 — i.e. the three components are of comparable
weight and none of them is the whole effect.

**The 3–6 hop claim needs care.** PRoH adds **200 generated questions per domain using knowledge
fragments 3–6 hops away**, and reports an average +26.68 F1 with a maximum of **+44.87 in the CS
domain** (PRoH 74.83 vs HyperGraphRAG 29.95). But look at the same table across the two question
sets: HyperGraphRAG scores 52.40 on long-range Agriculture against 33.89 on 1–3 hop Agriculture, and
64.55 on long-range Mix against 48.71 on 1–3 hop Mix. **Both systems do better on the supposedly
harder set.** Whatever the 3–6 hop questions measure, it is not increasing difficulty, and no human
verification of this split is described (unlike the 1–3 hop KHQA set, whose answers are stated to be
human-verified) `[unverified]`. The +44.87 figure should be quoted as "on a self-generated long-range
split that both systems find easier than the main split", or not quoted at all.

**Cost.** PRoH is the first hypergraph-RAG paper to put a token table next to its accuracy table —
and the table is for **PRoH-L**, a lighter variant with a fully embedding-based EWO (no LLM entity
scoring) that uses only path hyperedges as generation context:

| Domain | HyperGraphRAG tokens/question | PRoH-L tokens/question | Change |
|---|---|---|---|
| Medicine | 21,112 | 19,732 | −6.54 % |
| Agriculture | 17,914 | 12,528 | −30.07 % |
| CS | 18,666 | 12,166 | −34.82 % |
| Legal | 22,086 | 28,831 | **+30.54 %** |
| Mix | 13,856 | 9,687 | −30.09 % |

**The token consumption of the full PRoH — the configuration all the accuracy headlines come from —
is not reported against HyperGraphRAG.** The paper gives only a module-wise breakdown (Figure 6,
"highly skewed distribution toward the Answer and Path Retrieval module", the module that calls the
LLM once per candidate entity), and no wall-clock latency or LLM-call counts. So the honest reading
is: PRoH-L buys ~+15 F1 for roughly −25 % tokens outside Legal, and full PRoH buys ~+20 F1 for an
unreported number of tokens. That is a Pareto *point*, not a Pareto *curve*, and it is the best
cost accounting this subfield has.

Adjacent prompted-search systems: **HyperRAG**'s HyperMemory does a width-3 depth-3 beam search over
n-ary facts guided by the LLM's parametric knowledge
([Lien et al., 2026](https://arxiv.org/abs/2602.14470)); **HyperProve** carries intermediate answers
*and their supporting hyperedges* as retrieval state
([2609.13768](https://arxiv.org/abs/2609.13768), see
[reading-the-frontier-2026-q3](../08-history-and-frontier/reading-the-frontier-2026-q3.md) §2).

---

## 3. Generation 2b: learned traversal policies

If the plan can be prompted it can also be trained. Four systems do this over a hypergraph; only one
of them is well known in this KB.

**Graph-R1** ([Luo, E, Chen, Lin, Guo, Xu, Kuang, Song, Wu, Zhu and Luu, 2025/2026](https://arxiv.org/abs/2507.21892),
**ICML 2026**, code [LHRLAB/Graph-R1](https://github.com/LHRLAB/Graph-R1)) is by the HyperGraphRAG
authors and is the direct RL successor to it. The environment is a lightweight knowledge hypergraph
built by n-ary extraction; the agent loops *think → query → retrieve n-ary facts → rethink → answer*,
with dual-path retrieval (entity-based and direct hyperedge similarity) merged by **reciprocal rank
aggregation over hyperedges**. Training is **GRPO** with a two-part trajectory reward: a format
reward (0.5 per well-formed step, capped at 1.0) and an answer reward (token-level F1), with
correctness rewarded only when the format is valid. Reported average F1 **57.82** with Qwen2.5-7B
across six open-domain datasets (2WikiMultiHopQA, HotpotQA, MuSiQue, NQ, PopQA, TriviaQA), against
**29.40** for HyperGraphRAG and 46.19 for Search-R1; 2.3–2.5 interaction turns per query, ~7.0 s per
query, and construction at 5.69 s per 1k tokens against 8.04 s for GraphRAG.

That number deserves emphasis: **the HyperGraphRAG group's own follow-up nearly doubles
HyperGraphRAG's F1 on open-domain multi-hop QA by changing only the retrieval policy** — the index is
the same kind of object. It is the strongest available evidence that in G1 the bottleneck was the
search, not the representation. It also means any 2026 paper still benchmarking against
HyperGraphRAG alone is benchmarking against a superseded baseline.

**HyperGraphPro** ([Park, Lee, Khan, Kim and Kim, 2026](https://arxiv.org/abs/2601.17755), v1 25 Jan
2026, v2 12 Apr 2026, "in progress", no code found) targets two weaknesses of Graph-R1: similarity-only
retrieval and sparse outcome-level rewards. Retrieval mixes semantic relevance with a
**structure-guided distinctiveness** term, `log(1 + |{e ∈ E(q_t) : v ∈ V_e}| / |{e ∈ E : v ∈ V_e}|)`,
which downweights entities that appear in everything — an IDF over hyperedge incidence. Training is
**StepGRPO**: the advantage at each step is modulated by a *progress* reward
`P(y* | s≤t, G≤t) − P(y* | s<t, G<t)` (how much the retrieval reduced uncertainty about the gold
answer) plus a structure reward for connectivity to the previous state and answer reachability.
With Qwen2.5-7B: 69.75 F1 on 2Wiki (Graph-R1 65.04), 67.57 HotpotQA (62.69), 49.47 MuSiQue (46.17),
50.71 NQ (49.87), in 2.56 turns against Graph-R1's 2.72.

> **Correction to record.** arXiv:2601.17755 v1 is titled *"ProGraph-R1: Progress-aware Reinforcement
> Learning for Graph Retrieval Augmented Generation"*; v2 is *"HyperGraphPro: Progress-Aware
> Reinforcement Learning for Structure-Guided Hypergraph RAG"*. Same five authors (Park, Lee, Khan,
> Kim, Kim). Citations to "ProGraph-R1" and to "HyperGraphPro" are the same paper, and the
> hypergraph framing was adopted at revision.

Two further learned walkers, both domain-bound: **EvoGraph-R1**
([Lin et al., 2026](https://arxiv.org/abs/2607.12764), CVPR 2026) treats a multimodal knowledge
hypergraph as an environment the agent *edits* rather than only reads; **HyperWalker**
([Yang, Wang, Peng, Kim and Bi, 2026](https://arxiv.org/abs/2601.13919), 20 Jan 2026) replaces
attention-based retrieval in a medical VLM with an RL policy over a clinical hypergraph, with a
reward balancing evidence relevance, diversity and traversal depth, reporting 70.43 % VQA accuracy on
EHRXQA and 4.66 s inference against 86.56 s for a competing approach. Neither is a general-purpose
KHG retriever, but both confirm the pattern: the hyperedge set is an action space.

**What is *not* learned anywhere.** No system in this group learns *hyperedge weights for a
particular corpus* (the EWO analogue); the policy is learned, the index scoring function is not.
And no paper reports the RL training cost — GPU hours, rollouts, or the token bill of training —
against the inference savings it buys.

---

## 4. Generation 3: hierarchy and community summaries

The hierarchy idea is inherited, not invented, in the hypergraph line. Microsoft's GraphRAG built
Leiden communities and LLM community reports; **ArchRAG**
([Wang, Fang, Zhou, Liu and Ma, 2025/2026](https://arxiv.org/abs/2502.09891), AAAI 2026, 40(19):15868–15876)
made the community index itself hierarchical and attributed, claiming better accuracy *and* token
cost. **HiRAG** is the version everyone in the hypergraph line benchmarks against.

### 4.1 HiRAG (EMNLP 2025 Findings) — the hierarchy baseline

[Huang, Huang, Yang, Pan, Chen, Ma, Chen and Cheng, 2025](https://arxiv.org/abs/2503.10150)
(v1 13 Mar 2025, v3 26 Sep 2025; code [hhy-huang/HiRAG](https://github.com/hhy-huang/HiRAG), returned
HTTP 403 through this session's proxy on 2026-09-21 `[unverified]`). Not a hypergraph system — it is
the hierarchical *graph* RAG that H²RAG and others treat as the hierarchy baseline, and it is worth
stating precisely because the hypergraph papers cite it without describing it.

- **HiIndex.** Entities are clustered layer by layer with **Gaussian Mixture Models**; each cluster
  is summarised by an LLM into a **summary entity** in the layer above; layer construction stops when
  the cluster-sparsity change rate falls below 5 %. The effect is a set of *shortcuts* between
  entities that are semantically close but far apart in the extracted graph.
- **HiRetrieval.** Three levels combined into one context: **local** (top-20 entities by similarity),
  **global** (Leiden community reports attached to those entities), and **bridge** — shortest paths
  connecting key entities *across* communities. The bridge level is the part the hypergraph papers
  do not replicate.
- **Datasets.** Four UltraDomain corpora: Mix (61 docs, 625,948 tokens), CS (10 docs, 2,210,894),
  Legal (94 docs, 5,279,400), Agriculture (12 docs, 2,028,496). Baselines NaiveRAG, GraphRAG,
  LightRAG, FastGraphRAG, KAG.
- **Evaluation is pairwise LLM win rate**, GPT-4o judging comprehensiveness, empowerment, diversity
  and overall, with answer order alternated. On Mix: 87.6 % overall against NaiveRAG, 64.1 % against
  GraphRAG, 65.9 % against LightRAG, 99.2 % against FastGraphRAG. **No EM or F1 in the main table.**
- **Cost is where the hierarchy shows up.** Indexing the 625,948-token Mix corpus: HiRAG
  **21,898,765 tokens / 17,208 s**, against GraphRAG 8,507,697 / 6,696, LightRAG 3,849,030 / 3,342,
  KAG 6,440,668 / 8,530. That is roughly **35 LLM tokens consumed per corpus token**, 2.6× GraphRAG
  and 5.7× LightRAG. Retrieval tokens are reported as 0 for HiRAG (no LLM call at retrieval time).

A hierarchy is therefore an *indexing-time* bet: pay a large one-off summarisation bill, hope to win
it back on every query. Nobody in this literature computes the break-even query volume.

### 4.2 H²RAG (PAKDD 2026) — the hypergraph version, and it is real

The seed summary's "H²RAG" **exists**, and is not on arXiv. Verified 2026-09-21 against the
publisher record and Crossref metadata:

> **H²RAG: A Hierarchical Knowledge and Hypergraph Reasoning Framework for Retrieval-Augmented
> Generation.** Haodong Yang, Liangju Huang, Mengzhu Chen, Jia Cai (Guangdong University of Finance
> and Economics — School of Statistics and Data Science, and School of Big Data and Artificial
> Intelligence). In *Advances in Knowledge Discovery and Data Mining* (PAKDD 2026, Hong Kong,
> 9–12 June 2026), Lecture Notes in Computer Science vol. 16600, pp. 238–250. Springer Singapore.
> [doi:10.1007/978-981-92-1468-6_14](https://doi.org/10.1007/978-981-92-1468-6_14). First online
> 9 June 2026. 16 references. Keywords: hierarchical knowledge, hypergraph reasoning,
> retrieval-augmented generation.

Mechanism, from the abstract ([Yang et al., 2026](https://doi.org/10.1007/978-981-92-1468-6_14)):
the problem named is **"semantic dilution among distantly related yet semantically similar
entities"** — the same problem HiRAG's shortcuts attack. H²RAG "models higher-order relationships
through hypergraphs, applies the **Kumar community detection algorithm with bounded recursion** to
regulate community size, and integrates a **hierarchical summary layer**". Retrieval is
**dual-layer**: hyperedge similarity, node–entity matching, community probing and summary alignment.

Results, quoted verbatim from the abstract:

> "Experiments on the UltraDomain dataset across Agriculture, Computer Science, Legal, and Mix
> domains demonstrate that H²RAG surpasses strong baselines such as HyperGraphRAG and HiRAG,
> achieving average improvements of 20.33 % in Exact Match, 14.61 % in F1, and 11.53 % in
> Generalized Score."

What is and is not established. The paper is a **13-page PAKDD short/regular chapter with 16
references**, behind a paywall; the body was not readable in this session, so the per-domain numbers,
the baseline configuration, the judge for "Generalized Score", whether the improvements are points or
relative, and whether code exists are all `[unverified]` as of 2026-09-21. No preprint or repository
was found. Three things can be said anyway:

1. It is the **first system to benchmark a hypergraph index against a hierarchical-graph index**
   (HiRAG) on the same corpora, which is the comparison the field needs — G3-with-hyperedges versus
   G3-without.
2. It does **not** compare against PRoH or Graph-R1, so the G2-versus-G3 question is untouched.
3. Bounded-recursion community detection over hyperedges is the one genuinely new mechanism: HiRAG
   clusters entity *embeddings* with a GMM, H²RAG partitions the incidence structure. Whether
   community detection on hyperedges beats clustering on entity vectors is an empirical question
   nobody has isolated.

### 4.3 Other hierarchical hypergraph systems

- **HHS-RAG** (Tianci Zhang, Jianbin Wu, Yueguang Kang, *Journal of Intelligent Information Systems*,
  published online 29 July 2026, [doi:10.1007/s10844-026-01077-0](https://doi.org/10.1007/s10844-026-01077-0)):
  "hierarchical hypergraph retrieval-augmented generation with hyperbolic contrastive learning and
  subgraph-level decision". Its hierarchical hypergraph integrates document hierarchies, topic
  abstractions and high-order multi-entity co-occurrences, with structure representation learned in
  **hyperbolic** space — the only system here to take the tree-likeness of a hierarchy seriously as
  geometry. Paywalled; abstract only, everything beyond the above is `[unverified]` (checked
  2026-09-21).
- **EEG-MedRAG** ([Wang, Luo, Meng, Jia, Zhou and Wen, 2025](https://arxiv.org/abs/2508.13735),
  v1 19 Aug 2025, v2 11 Oct 2025): a **three-layer** hypergraph — EEG domain knowledge, individual
  patient cases, and a large-scale repository — unified into "a traversable n-ary relational
  hypergraph" with joint semantic–temporal retrieval, plus a cross-disease, cross-role EEG clinical
  QA benchmark. Baselines TimeRAG and HyperGraphRAG. Here the hierarchy is *given* by the domain
  rather than induced, which sidesteps the clustering question entirely.
- **Cog-RAG** ([Hu et al., 2026](https://arxiv.org/abs/2511.13201), AAAI 2026) is best read as a
  two-layer G3 system: a theme hypergraph over chunks above an entity hypergraph, with top-down
  alignment. See [retrieval-augmented-generation §5](retrieval-augmented-generation.md#5-other-20252026-systems).

---

## 5. What the cost numbers actually say

Collected from the primary sources above; the accounting differs per row, so these are **not**
directly comparable — which is itself the finding.

| System | Indexing cost reported | Query cost reported | Accuracy/cost trade shown |
|---|---|---|---|
| HyperGraphRAG | 3.084 s, $0.0063 per 1k tokens | 0.256 s, $3.184 per 1k queries | yes, as a table; no curve |
| HiRAG | 21.9M tokens / 17,208 s on a 626k-token corpus | 0 retrieval tokens | no |
| PRoH | not reported | tokens/question for **PRoH-L only** | one point (PRoH-L), not the headline config |
| Graph-R1 | 5.69 s per 1k tokens | 2.3–2.5 turns, ~7.0 s per query | turns reported, tokens not |
| HyperGraphPro | not reported | 2.56 turns | turns only |
| H²RAG | not reported `[unverified]` | not reported `[unverified]` | — |
| EHRAG | "linear indexing complexity and **zero token consumption** for construction" | not reported | cost is the contribution |

The outlier is worth naming. **EHRAG** ([Song, Tao, Yang, Luo and Tang, 2026](https://arxiv.org/abs/2604.17458),
ACL 2026 Findings, v1 19 Apr 2026) builds its hypergraph *without an LLM*: structural hyperedges from
sentence-level entity co-occurrence via NER, semantic hyperedges from clustering entity embeddings,
retrieval by structure–semantic hybrid diffusion with topic-aware scoring and personalised PageRank.
If a zero-token index is competitive, then most of the indexing bill in G1 and G3 is buying LLM
*summaries*, not hyperedges — and the hierarchy papers, which spend the most, owe the clearest
ablation.

Nothing in this literature plots accuracy against a token budget. Every system reports its own
operating point. Until someone sweeps k, hop depth, beam width, hierarchy depth and community size
on a fixed corpus and plots the frontier, "system X beats system Y" is a statement about two points
on two unknown curves. This is the single most valuable missing experiment, and it is cheap.

---

## 6. Critique

Everything in
[critical-reading-of-hypergraph-rag-claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md)
applies; four things are specific to G2 and G3.

1. **Percentage points are being read as percentages.** PRoH's "+19.73 % in F1" is 19.73 F1 *points*
   averaged over five domains (35.35 → 52.94 and so on). H²RAG's "20.33 % in Exact Match" is
   ambiguous in the abstract and `[unverified]` either way. A relative reading inflates PRoH's gain
   by a factor of about three and deflates it for high-scoring domains. Quote the per-domain table,
   not the headline.
2. **The benchmark grows with the claim.** PRoH's long-range split is 200 generated questions per
   domain, added by the paper making the long-range claim, on which both systems score *higher* than
   on the main split (§2). Self-built benchmarks were already the field's weak point; self-built
   *extensions used for the paper's strongest single number* are worse.
3. **LLM judging is now two deep.** HiRAG's main results are GPT-4o pairwise win rates with no EM or
   F1 at all; H²RAG then reports EM/F1/"Generalized Score" against HiRAG as a baseline. A system
   tuned on win rates and re-scored on exact match is being evaluated on a metric its baseline never
   optimised. That direction of comparison flatters the challenger.
4. **Retrieval still assumes the index is complete.** Every planner here treats a missing hyperedge
   as a retrieval failure to route around, not as a fact to infer. PRoH's EWO can only follow edges
   that exist; Graph-R1's agent can only retrieve what was extracted; H²RAG's community probe can
   only summarise what is in a community. Given that HyperGraphRAG's own extractor was measured at
   0.1072 micro-recall on HyperDocRED ([Huang et al., 2026](https://arxiv.org/abs/2602.19543), see
   [retrieval-augmented-generation §5](retrieval-augmented-generation.md#5-other-20252026-systems)),
   the planner is planning over a graph that is mostly missing. **No system combines inductive
   hypergraph completion with retrieval over an extracted hypergraph** — searches on 2026-09-21 for
   HYPER-style inductive completion ([Huang, Galkin, Bronstein and Ceylan](https://arxiv.org/abs/2506.12362))
   used inside any RAG pipeline returned nothing, and no hypergraph-RAG paper cites an inductive
   link predictor `[unverified — absence from the searches run on 2026-09-21, not a proof]`.
   Predicted-edge retrieval, with the prediction shown to the reader, is the obvious next system and
   nobody has built it.

And one point in the field's favour: **the ladder is finally being climbed downwards as well as
upwards.** Graph-R1 (§3) shows the reference system's authors improving on it by ~28 F1 points with a
different retrieval policy over the same kind of index. That is the sort of internal falsification
the subfield was accused of lacking.

---

## Open questions raised here

- Does a hierarchy beat a better search? H²RAG (G3) and PRoH/Graph-R1 (G2) have never been compared
  on the same corpus, and the two designs cost very differently.
- What is the break-even query volume for a hierarchical index that costs 35 LLM tokens per corpus
  token to build (HiRAG on Mix)?
- Is community detection over hyperedges better than GMM clustering over entity embeddings, holding
  the summary layer and the reader fixed?
- Why do both PRoH and HyperGraphRAG score *higher* on PRoH's 3–6 hop split than on the 1–3 hop
  split? If hop distance in an extracted hypergraph does not track question difficulty, hop-sampled
  benchmarks measure something else.
- What would a learned *index* scoring function (corpus-specific hyperedge weights) add on top of a
  learned traversal policy?
- Would retrieval over an inductively completed hypergraph beat retrieval over the extracted one, and
  can the completion be made visible enough to be auditable?

## Sources

- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., Feng, Y., Kuang, Z., Song, M., Zhu, Y., Luu, A. T. *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation.* NeurIPS 2025; arXiv:2503.21322 (v1 27 Mar 2025, v3 21 Oct 2025). https://arxiv.org/abs/2503.21322
- Zai, X., Tan, X., Wang, X., Liu, Q., Xu, X., Zhang, W. *PRoH: Dynamic Planning and Reasoning over Knowledge Hypergraphs for Retrieval-Augmented Generation.* The Web Conference 2026; arXiv:2510.12434 (v1 14 Oct 2025, v2 18 Feb 2026); ACM DOI 10.1145/3774904.3792611. https://arxiv.org/abs/2510.12434 — v2 HTML read 2026-09-21 for §2 (EWO, plan context graph, DAG state search, Tables 1–4, Figure 6).
- Luo, H., E, H., Chen, G., Lin, Q., Guo, Y., Xu, F., Kuang, Z., Song, M., Wu, X., Zhu, Y., Luu, A. T. *Graph-R1: Towards Agentic GraphRAG Framework via End-to-end Reinforcement Learning.* ICML 2026; arXiv:2507.21892 (v1 29 Jul 2025, v2 2 Jun 2026); code https://github.com/LHRLAB/Graph-R1. https://arxiv.org/abs/2507.21892
- Park, J., Lee, S., Khan, O. Z., Kim, H. J., Kim, J.-K. *HyperGraphPro: Progress-Aware Reinforcement Learning for Structure-Guided Hypergraph RAG.* arXiv:2601.17755 (v1 25 Jan 2026 as *ProGraph-R1: Progress-aware Reinforcement Learning for Graph Retrieval Augmented Generation*; v2 12 Apr 2026, retitled). https://arxiv.org/abs/2601.17755
- Huang, H., Huang, Y., Yang, J., Pan, Z., Chen, Y., Ma, K., Chen, H., Cheng, J. *Retrieval-Augmented Generation with Hierarchical Knowledge* (HiRAG). EMNLP 2025 Findings; arXiv:2503.10150 (v1 13 Mar 2025, v3 26 Sep 2025); code https://github.com/hhy-huang/HiRAG. https://arxiv.org/abs/2503.10150
- Yang, H., Huang, L., Chen, M., Cai, J. *H²RAG: A Hierarchical Knowledge and Hypergraph Reasoning Framework for Retrieval-Augmented Generation.* In *Advances in Knowledge Discovery and Data Mining*, PAKDD 2026, Hong Kong, 9–12 June 2026; Lecture Notes in Computer Science vol. 16600, pp. 238–250, Springer Singapore, first online 9 June 2026. https://doi.org/10.1007/978-981-92-1468-6_14 — abstract and publisher metadata read 2026-09-21; Crossref record checked the same day. Full text paywalled.
- Zhang, T., Wu, J., Kang, Y. *HHS-RAG: Hierarchical hypergraph retrieval-augmented generation with hyperbolic contrastive learning and subgraph-level decision.* *Journal of Intelligent Information Systems*, published online 29 July 2026. https://doi.org/10.1007/s10844-026-01077-0 — abstract only; full text paywalled (checked 2026-09-21).
- Wang, S., Fang, Y., Zhou, Y., Liu, X., Ma, Y. *ArchRAG: Attributed Community-based Hierarchical Retrieval-Augmented Generation.* AAAI 2026, 40(19):15868–15876; arXiv:2502.09891 (v1 14 Feb 2025, v4 11 May 2026). https://arxiv.org/abs/2502.09891
- Wang, Y., Luo, H., Meng, L., Jia, Z., Zhou, X., Wen, Q. *EEG-MedRAG: Enhancing EEG-based Clinical Decision-Making via Hierarchical Hypergraph Retrieval-Augmented Generation.* arXiv:2508.13735 (v1 19 Aug 2025, v2 11 Oct 2025). https://arxiv.org/abs/2508.13735
- Song, Y., Tao, X., Yang, Z., Luo, Y., Tang, J. *EHRAG: Bridging Semantic Gaps in Lightweight GraphRAG via Hybrid Hypergraph Construction and Retrieval.* ACL 2026 Findings; arXiv:2604.17458 (v1 19 Apr 2026, v2 21 Apr 2026). https://arxiv.org/abs/2604.17458
- Yang, Y., Wang, H., Peng, Y., Kim, J., Bi, L. *HyperWalker: Dynamic Hypergraph-Based Deep Diagnosis for Multi-Hop Clinical Modeling across EHR and X-Ray in Medical VLMs.* arXiv:2601.13919, 20 Jan 2026. https://arxiv.org/abs/2601.13919
- Lin, J., Jiang, C., Lin, X., Zhang, R., Zhu, X., Liu, J. et al. *EvoGraph-R1: Self-Evolving Multimodal Knowledge Hypergraphs for Agentic Retrieval.* CVPR 2026; arXiv:2607.12764, 14 Jul 2026. https://arxiv.org/abs/2607.12764
- Lien, W.-S., Chan, Y.-K., Hsiao, H.-L., Ruan, B.-K., Chiang, M.-F., Chen, C.-A., Yeh, Y.-R., Shuai, H.-H. *HyperRAG: Reasoning N-ary Facts over Hypergraphs for Retrieval Augmented Generation.* WWW 2026; arXiv:2602.14470, 16 Feb 2026. https://arxiv.org/abs/2602.14470
- Hu, H., Feng, Y., Li, R., Xue, R., Hou, X., Tian, Z., Gao, Y., Du, S. *Cog-RAG: Cognitive-Inspired Dual-Hypergraph with Theme Alignment Retrieval-Augmented Generation.* AAAI 2026; arXiv:2511.13201. https://arxiv.org/abs/2511.13201
- Huang, R., Feng, Y., Xue, R., Ying, S., Yong, J.-H., Shi, C., Du, S., Gao, Y. *Hyper-KGGen: A Skill-Driven Knowledge Extractor for High-Quality Knowledge Hypergraph Generation.* arXiv:2602.19543, 23 Feb 2026. https://arxiv.org/abs/2602.19543
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. *HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs.* arXiv:2506.12362, 14 Jun 2025 (rev. 8 May 2026); code https://github.com/HxyScotthuang/HYPER. https://arxiv.org/abs/2506.12362
- Nguyen Phu, Nguyen Quang, Luu, Ngo Van, Le, Nguyen. *HyperProve.* arXiv:2609.13768, 12 Sep 2026. https://arxiv.org/abs/2609.13768
