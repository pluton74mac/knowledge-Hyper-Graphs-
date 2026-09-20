---
title: AI agents — memory and planning over hypergraphs
type: survey
status: draft
tags: [hypergraph, LLM-agents, memory, planning, AND-OR-graph, HTN, AtomSpace, skills, tool-use]
created: 2026-09-20
updated: 2026-09-20
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

Four 2026 systems, all preprints unless noted:

- **HyperMem** ([Yue, Hu, Sheng, Zhou, Zhang, Liu, Guo, Deng, 2026](https://arxiv.org/abs/2604.08256)).
  Long-term conversational memory organised hierarchically across **topics, episodes and facts**, with
  hyperedges grouping related episodes and their facts into coherent units instead of pairwise links.
  Reports state-of-the-art on the LoCoMo benchmark at **92.73 % LLM-as-a-judge accuracy**.
- **HyperSkill** ([Xu, Yang, Huang, 2026](https://arxiv.org/abs/2608.16114)). Procedural memory as a
  hypergraph with **two node types — subtask steps and reusable skills — and one hyperedge per
  trajectory** linking the subtasks and skills it used. Retrieval is dual-path (query at both subtask and
  trajectory level), ranking skills by co-occurrence across retrieved trajectories. The framing question
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
