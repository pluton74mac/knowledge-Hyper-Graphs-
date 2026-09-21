---
title: AI agents — memory and planning over hypergraphs
type: survey
status: draft
tags: [hypergraph, LLM-agents, memory, planning, AND-OR-graph, HTN, AtomSpace, skills, tool-use, locomo, longmemeval, evograph-r1, edgemem, mage]
created: 2026-09-20
updated: 2026-09-21
---

# AI agents — memory and planning over hypergraphs

Two quite different lineages meet here. **Planning** has used directed hypergraphs since the 1990s,
because an AND/OR graph *is* a directed hypergraph. **Agent memory** discovered hypergraphs in 2026, as
a way to stop storing episodes as isolated rows. The planning side is settled mathematics; the memory
side is a burst of preprints whose claims should be read as early results.

## 1. Planning: AND/OR graphs are directed hypergraphs

[Gallo, Longo, Pallottino and Nguyen, 1993](https://doi.org/10.1016/0166-218X(93)90045-P) list AND/OR
graphs among the canonical applications of directed hypergraphs. In an AND/OR graph an OR node offers
alternative decompositions and an AND node requires all of its children; encoding a decomposition as a
hyperedge from one node to the *set* of its subgoals makes the AND explicit and turns plan search into
**hyperpath** search, with the shortest-hyperpath machinery (B-connectivity, minimal hyperpaths) applying
directly. The same structure underlies hierarchical task network (HTN) planning, where a method
decomposes a task into a set of subtasks that must all be achieved, and it is the same object as a
retrosynthesis AND/OR tree ([chemistry-and-reaction-networks](chemistry-and-reaction-networks.md)) and
an exploit rule ([cybersecurity-and-it-operations](cybersecurity-and-it-operations.md)).

The practical consequence for LLM agents: any planner that decomposes a goal into subgoals that must
*all* succeed is walking a directed hypergraph, whether or not it says so, and the cost of a plan is a
hyperpath cost (sum or max over a set), not a path cost.

## 2. Tool use as a schema hypergraph

**HyperAgent** ([Zhai, Tan, Zou, Wang, Zhang, 2026](https://arxiv.org/abs/2608.02650)) makes this
explicit for tool-using agents: tools are hyperedges **from their required input-schema nodes to their
output-schema nodes**, so the tool graph is a directed hypergraph over schema types rather than a list of
API descriptions in a prompt. The agent builds a task-relevant context graph, generates a schema-aware
task DAG, and expands a state-conditioned tool support graph by *deficit-oriented expansion* —
identifying unresolved schema requirements and retrieving producer tools for them. Evaluated on
AppWorld, it reports improved task completion with fewer redundant API calls, LLM calls and tokens.
[unverified: specific numerical comparisons were not stated in the abstract read in this run]

This is the most direct instance in the KB of planning-as-hyperpath applied to LLM agents: finding a
tool chain that produces a required output type from available inputs is exactly a minimal-hyperpath
query.

## 3. Memory as a hypergraph

Four 2026 systems, all preprints unless noted (details verified against the abstracts and, where
noted, the arXiv HTML, on 2026-09-21):

- **HyperMem** ([Yue, Hu, Sheng, Zhou, Zhang, Liu, Guo, Deng, 2026](https://arxiv.org/abs/2604.08256)).
  Long-term conversational memory organised hierarchically across **topics, episodes and facts**, with
  hyperedges grouping related episodes and their facts into coherent units instead of pairwise links.
  Concretely, hyperedges `ℰᴱ` "connect all episode nodes within the same topic" and `ℰᶠ` "connect all
  fact nodes belonging to the same episode", each with a node weight `w ∈ [0,1]`. Reports
  state-of-the-art on the LoCoMo benchmark at **92.73 % LLM-as-a-judge accuracy**; per category
  (Table 1 of [arXiv:2604.08256v2](https://arxiv.org/html/2604.08256v2)) single-hop 96.08, multi-hop
  93.62, **temporal 89.72**, open domain 70.83, against HyperGraphRAG at 90.61 / 80.85 / 85.36 /
  70.83 (86.49 overall) and Zep at 61.70 / 41.35 / 49.31 / **76.60** (65.99 overall). Temporal is the
  weakest reasoning category, which is consistent with hyperedges that carry weights but no temporal
  semantics — see
  [temporal-hyperedges-and-editable-agent-memory](temporal-hyperedges-and-editable-agent-memory.md).
- **HyperSkill** ([Xu, Yang, Huang, 2026](https://arxiv.org/abs/2608.16114)). Procedural memory as a
  hypergraph with **two node types — subtask steps and reusable skills — and one hyperedge per
  trajectory** linking the subtasks and skills it used. Retrieval is dual-path (query at both subtask and
  trajectory level), ranking skills by co-occurrence across retrieved trajectories. Evolution is
  "periodic structure-informed maintenance [that] prunes low-utility nodes and merges redundant skills
  via quality-weighted propagation" — a utility criterion, not a validity one. Evaluated on **xBench,
  GAIA and WebWalkerQA** with GPT-4o and Qwen3-30B-A3B against ten memory baselines, with gains of
  **up to +11.51 on GAIA and +11.18 on WebWalkerQA**. The framing question
  is the useful part: what to store, how to structure and retrieve it, and how memory evolves — existing
  systems store trajectories as isolated entries and discard the compositional relations.
- **DocTrace** ([*Trace Only What You Need*, 2026](https://arxiv.org/abs/2606.10921)). Multi-agent
  long-document QA with an **on-demand** hypergraph working memory built during reasoning rather than
  precomputed, plus a graph-structured experience memory of successful plans. Best on three of four
  long-document QA datasets, beating the strongest baseline by up to **8.85 % F1 and 4.40 % EM while
  reducing overall computational cost by 53.32 %**. The on-demand construction is the notable design
  choice: it attacks the "costly query-agnostic knowledge organisation" cost that dominates
  [retrieval-augmented-generation](retrieval-augmented-generation.md).
- **HKVM-RAG** ([arXiv:2606.07218](https://arxiv.org/pdf/2606.07218)), key–value-separated hypergraph
  evidence organisation for multi-hop RAG, is an adjacent design in the same family.

Three more, found in the second research pass:

- **EvoGraph-R1** ([Lin et al., CVPR 2026](https://arxiv.org/abs/2607.12764)). The hypergraph is not
  an index but an **environment**: the state is `sₜ = (𝒢ₜ, ℋₜ, q)` — current hypergraph, action
  history, query — and the agent chooses among **GraphRetrieve, WebSearch, GraphEdit** (Insert /
  Update / Delete) and **Answer**. The trajectory reward adds a structural well-formedness term
  `min(1.0, η·Σ 𝕀_valid(t))` with `η = 0.5`, an F1-style answer term gated on that term reaching 1.0,
  and a per-action cost penalty `−λ·Σ c(aₜ)`
  ([HTML read of v1, 2026-09-21](https://arxiv.org/html/2607.12764v1)). Reported: 68.5 F1 on
  2WikiMultiHopQA, 65.4 on HotpotQA, 56.8 on Natural Questions, 43.6 on E-VQA, 68.6 on OK-VQA, 42.3
  on InfoSeek. It is the only system here with an explicit retraction action — and the Delete
  destroys history rather than invalidating it, with nothing in the reward for retracting correctly.
  Whether edits persist across queries rather than within an episode is not stated `[unverified]`.
- **EdgeMem** ([Cui, Cao, Wen, Yuan, Feng and Chen, arXiv:2609.05553, 3 Sep
  2026](https://arxiv.org/abs/2609.05553)). **LLM-free** construction: "preserve original interaction
  turns and organize them through complementary content, temporal, and episodic cues" via a
  multi-anchor hypergraph. LoCoMo **61.01** strict-judge against 58.70 for the second best of seven
  reproduced systems; LongMemEval-S R@3 81.49 and NDCG@3 90.49 against MemGAS at 78.51 / 86.83, at
  ~3.2k tokens per question against 8.2–9.0k. Note that a *strict-judge* 61.01 and HyperMem's
  *LLM-as-a-judge* 92.73 are not the same measurement.
- **MAGE** ([Feng, Zhang, Luo, Lin, Yang and Luu, *Diachronic Hypergraphs for Orchestrated
  Multi-Agent Multimodal Memory Curation*, arXiv:2608.29678, 30 Aug
  2026](https://arxiv.org/abs/2608.29678)). A hypergraph *database* as a multi-agent memory engine,
  storing "agents, messages, tools, errors, procedures, documents, entities, decisions, and evidence
  in a heterogeneous temporal hypergraph", with "decision driven updates, role aware retrieval,
  validation, lifecycle management, and budget bounded context packing". Whether the lifecycle
  machinery is bitemporal could not be verified this run `[unverified]`.

**What none of them models.** Time in all eight systems is a *retrieval cue* — episode segmentation
by dialogue gap (HyperMem), calendar-month anchors (EdgeMem), recency weighting — never a *truth
condition* on the hyperedge. No hypergraph memory system found carries valid time, invalidation or
supersession, although the binary systems they are benchmarked against (Zep/Graphiti) have carried
all three since 2025. The taxonomy that the 2026 survey of graph-based agent memory uses makes the
split structural: "temporal graph structure" and "hypergraph structure" are sibling storage
categories, and only the first is bitemporal ([Yang et al., arXiv:2602.05665, 5 Feb
2026](https://arxiv.org/abs/2602.05665)). Full treatment, with the design requirements, in
[temporal-hyperedges-and-editable-agent-memory](temporal-hyperedges-and-editable-agent-memory.md).

**Benchmarks.** LoCoMo is 50 conversations averaging 304.9 turns and 9,209.2 tokens over up to 35
sessions, with 7,512 questions split single-hop 2,705, multi-hop 1,104, temporal reasoning 1,547,
open-domain 285, adversarial 1,871 ([Maharana et al.,
arXiv:2402.17753](https://arxiv.org/abs/2402.17753)). Its temporal category is about ordering and
dates, not about facts being replaced. LongMemEval is the benchmark that tests replacement: its five
abilities are information extraction, multi-session reasoning, temporal reasoning, **knowledge
updates** and abstention ([Wu, Wang, Yu, Zhang, Chang and Yu, ICLR 2025 /
arXiv:2410.10813](https://arxiv.org/abs/2410.10813)). Of the hypergraph systems above only EdgeMem
reports LongMemEval-S, and not per ability.

Read together, the memory papers converge on one claim: the unit of agent memory should be a *group*
(an episode with its facts, a trajectory with its skills, a query-triggered evidence set), and the
retrieval index should respect that grouping. That is a reasonable claim and the results are consistent
with it — but every evaluation above is either LLM-judged or on a benchmark the authors selected, and
none ablates the hypergraph against a strong "store the whole episode as one chunk" baseline, which is
the obvious cheap alternative.

## 4. The long precedent: AtomSpace

**OpenCog AtomSpace** ([opencog/atomspace](https://github.com/opencog/atomspace)) has represented
knowledge this way for far longer than any of the above. Its README describes it as "an in-RAM knowledge
representation (KR) database with an associated query engine and graph-re-writing system" and, crucially,
as "a kind of in-RAM generalized hypergraph (metagraph) database". The data model: "the AtomSpace stores
immutable, globally unique, typed s-expressions. Each s-expression is called 'an Atom'", with a mutable
key-value store of **Values** attached to each Atom — so it is "a database-of-databases; each atom is a
key-value database; the atoms are related to one-another as a graph". Atoms are indexed for search;
Values hold fast-changing data and are not.

AtomSpace and HypergraphDB are covered as data models in
[metagraphs-atomspace-and-hypergraphdb](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md).
Two things are worth extracting for this KB. First, the project deliberately moved from *hypergraph* to
*metagraph* language, because a Link whose members are themselves Links is nesting, not just arity —
the distinction discussed in
[what-is-a-knowledge-hypergraph](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md).
Second, the Atom/Value split anticipates a design problem the 2026 memory systems have not solved:
which parts of a hyperedge are stable, indexed knowledge and which are volatile state. The repository
remains actively developed (tens of thousands of commits on master as of 2026-09-20).

## 5. Assessment

| Claim | Status |
|---|---|
| AND/OR and HTN planning are directed-hypergraph search | Established since 1993 |
| Tool-chaining is a minimal-hyperpath problem over schemas | Argued and implemented once (HyperAgent, 2026) |
| Grouped memory beats per-episode rows for long-horizon agents | Consistent early results, no strong ablation |
| Hypergraph/metagraph memory is a new idea | False — AtomSpace predates it by well over a decade |
| Hypergraph memory models when a fact stops being true | False — none of the eight systems does; the bitemporal work is all binary |

The most useful open experiment: take any of the 2026 memory hypergraphs and compare against (a) a
flat chunk store of whole episodes and (b) a binary knowledge graph built from the same extractions,
with a non-LLM metric. None of the papers found here does both.

## Sources

- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. *Directed hypergraphs and applications.* Discrete Applied Mathematics 42(2–3):177–201, 1993. https://doi.org/10.1016/0166-218X(93)90045-P
- Zhai, Z., Tan, X., Zou, G., Wang, X., Zhang, W. *HyperAgent: Planning and Acting over Tool-Schema Hypergraphs for Tool-Use LLM Agents.* arXiv:2608.02650, 31 Jul 2026. https://arxiv.org/abs/2608.02650
- Yue, J., Hu, C., Sheng, J., Zhou, Z., Zhang, W., Liu, T., Guo, L., Deng, Y. *HyperMem: Hypergraph Memory for Long-Term Conversations.* arXiv:2604.08256, 9 Apr 2026. https://arxiv.org/abs/2604.08256
- Xu, R., Yang, T., Huang, W.-C. *HyperSkill: Self-Evolving LLM Agents via Hypergraph-Structured Skill Memory.* arXiv:2608.16114, Aug 2026. https://arxiv.org/abs/2608.16114
- *Trace Only What You Need: Structure-Aware On-Demand Hypergraph Memory for Long-Document Question Answering* (DocTrace). arXiv:2606.10921, 2026. https://arxiv.org/abs/2606.10921
- *HKVM-RAG: Key-Value-Separated Hypergraph Evidence Organization for Multi-Hop RAG.* arXiv:2606.07218, 2026. https://arxiv.org/pdf/2606.07218
- OpenCog. *AtomSpace* repository and README, GitHub, checked 2026-09-20. https://github.com/opencog/atomspace
- Lin, J., Jiang, C., Lin, X., Zhang, R., Zhu, X., Liu, J., Tang, C., Du, Y., Gao, S., Ning, J., Liu, L., Huang, Z., Li, T., Ye, J., He, J. *EvoGraph-R1: Self-Evolving Multimodal Knowledge Hypergraphs for Agentic Retrieval.* CVPR 2026; arXiv:2607.12764, 14 Jul 2026. https://arxiv.org/abs/2607.12764
- Cui, Z., Cao, J., Wen, Z., Yuan, B., Feng, J., Chen, S. *EdgeMem: LLM-Free Agent Memory Construction and Retrieval via Evidence-Preserving Multi-Anchor Hypergraph.* arXiv:2609.05553, 3 Sep 2026. https://arxiv.org/abs/2609.05553
- Feng, Y., Zhang, R., Luo, H., Lin, Z., Yang, C., Luu, A. T. *Diachronic Hypergraphs for Orchestrated Multi-Agent Multimodal Memory Curation* (MAGE). arXiv:2608.29678, 30 Aug 2026. https://arxiv.org/abs/2608.29678
- Yang, C., Zhou, C., Xiao, Y., Dong, S., Zhuang, L., Zhang, Y., Wang, Z., Hong, Z., Yuan, Z., Xiang, Z., Chen, S., Zhou, H., Zhang, Q., Liu, N., Su, J., Wang, X., Chang, Y., Huang, X. *Graph-based Agent Memory: Taxonomy, Techniques, and Applications.* arXiv:2602.05665, 5 Feb 2026. https://arxiv.org/abs/2602.05665
- Maharana, A., Lee, D.-H., Tulyakov, S., Bansal, M., Barbieri, F., Fang, Y. *Evaluating Very Long-Term Conversational Memory of LLM Agents* (LoCoMo). arXiv:2402.17753, 27 Feb 2024. https://arxiv.org/abs/2402.17753
- Wu, D., Wang, H., Yu, W., Zhang, Y., Chang, K.-W., Yu, D. *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory.* ICLR 2025; arXiv:2410.10813, 14 Oct 2024. https://arxiv.org/abs/2410.10813
