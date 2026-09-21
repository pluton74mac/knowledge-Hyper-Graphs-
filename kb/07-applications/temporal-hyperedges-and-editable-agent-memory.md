---
title: Time on the hyperedge, and hypergraphs as editable agent memory
type: survey
status: draft
tags: [temporal, bitemporal, valid-time, agent-memory, graphiti, zep, hypermem, hyperskill, evograph-r1, edgemem, mage, toki, extrapolation, supersession, retraction, locomo, longmemeval]
created: 2026-09-21
updated: 2026-09-21
---

# Time on the hyperedge, and hypergraphs as editable agent memory

An agent memory that answers "who owns the project?" with last year's owner, at full confidence, has
not failed at retrieval. It has failed at representation: the store has no place to record that a
fact *stopped being true*. This note is about that missing place, and about why the hypergraph
literature and the agent-memory literature have each solved half of it.

The two halves, stated plainly:

- **Binary temporal KGs and binary agent memory** have solved *when*: bitemporal edges, validity
  intervals, invalidation-not-deletion, continuous-time dynamics. All of it on edges of arity two.
- **Knowledge hypergraphs** have solved *what*: role-labelled n-ary facts that survive update without
  reification damage. Almost none of it carries a validity interval on the hyperedge.

Nothing found in this run does both. Companion notes:
[temporal-and-dynamic-khgs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md) (the
n-ary temporal models),
[ai-agents-memory-and-planning](ai-agents-memory-and-planning.md) (the memory systems),
[incremental-and-streaming-construction](../03-construction/incremental-and-streaming-construction.md)
(§5, the two clocks at construction time).

---

## 1. What "valid time on the hyperedge" would have to mean

Take the KB's working hyperedge: a relation `r` with a set of role-bindings,
`e = (r, {(ρ₁, v₁), …, (ρₙ, vₙ)})`
([hypergraph-definitions](../01-foundations/hypergraph-definitions.md) §10). Four things have to be
added, and only the first is common in the literature.

**(a) Two intervals, not one timestamp.** Valid time `τᵥ(e) = [t_valid, t_invalid)` — when the fact
held in the world — and transaction time `τₜ(e) = [t_created, t_expired)` — when the store believed
it. This is the standard bitemporal pair, and its use in agent memory is settled practice on binary
edges (§2). Half-open intervals matter: `t_invalid` is usually unknown at write time and must be
representable as `+∞`.

**(b) A key, so that contradiction is even definable.** On a binary edge, "the same fact updated"
means same `(subject, relation)`, different object; the functional dependency is implicit in the
relation. On an n-ary fact there is no such default. `employment(person: A, employer: B, role: C,
salary: D)` can be superseded by a salary change, a role change, or neither. Detecting supersession
requires declaring a **key role set** `K ⊆ roles(r)` such that at most one hyperedge with a given
binding of `K` is valid at any instant. No n-ary model or schema language surveyed in this KB
declares one ([knowledge-hypergraph-schema-design](../02-knowledge-representation/knowledge-hypergraph-schema-design.md)
treats qualifiers as narrowing, not as keys). This is the sharpest formal gap in the area.

**(c) Per-role validity, or not.** A genuinely n-ary question with no binary analogue: is validity a
property of the whole hyperedge, or of each role-binding? If a committee gains a member, one
role-binding changed and the rest did not; closing the whole hyperedge and opening a near-copy
duplicates `n−1` bindings per change. Nothing found attaches intervals below hyperedge granularity.

**(d) Supersession as an edge between hyperedges.** Graphiti's answer to the retraction problem is
not to delete but to set `t_invalid` and keep the row ([Rasmussen et al.,
2025](https://arxiv.org/abs/2501.13956)); TOKI's is to keep the losing fact in an audit row
([Wang, 2026](https://arxiv.org/abs/2606.06240)). Either way the history is a second-order
structure — hyperedges about hyperedges — which is exactly where a metagraph is the natural home
([metagraphs-atomspace-and-hypergraphdb](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md)).

## 2. The binary precedent is mature

**Bitemporal agent memory.** Zep/Graphiti is the reference implementation and the KB already quotes
its four timestamps ([incremental-and-streaming-construction](../03-construction/incremental-and-streaming-construction.md)
§5). The paper states the model directly: "Zep implements a bi-temporal model, where timeline T
represents the chronological ordering of events, and timeline T′ represents the transactional order
of Zep's data ingestion", and contradictions are resolved by "invalidat[ing] the affected edges by
setting their t_invalid to the t_valid of the invalidating edge"
([Rasmussen, Paliychuk, Beauvais, Ryan and Chalef, arXiv:2501.13956,
2025](https://arxiv.org/abs/2501.13956)). Reported: 94.8% vs MemGPT's 93.4% on Deep Memory
Retrieval, and 15.2–18.5% accuracy gains with ~90% latency reduction on LongMemEval.

By August 2026 this is a small genre, and all of it is binary:

| System | Date / id | What it adds | Arity |
|---|---|---|---|
| Zep / Graphiti | Jan 2025, [2501.13956](https://arxiv.org/abs/2501.13956) | four timestamps, LLM contradiction check on insert | binary edges |
| **TOKI** | 4 Jun 2026, [2606.06240](https://arxiv.org/abs/2606.06240) | types the four production heuristics (last-writer-wins, evidence-weighted merge, await-confirmation, per-rule policy) as bitemporal operators with isolation preconditions; audit row for the losing fact; fold operators extended "to n-ary conflict sets" | dual-row relational |
| **Bitemporal memory store** | 29 Jul 2026, [2607.26520](https://arxiv.org/abs/2607.26520) | immutable identity node + versioned content nodes, "two closed-open time intervals: valid time … and transaction time"; point-in-time semantic retrieval | binary property graph |
| **Quipu** | 17 Aug 2026, [2608.16813](https://arxiv.org/abs/2608.16813) | "data, trust labels, verdicts, and the rules themselves are bitemporal"; gated writes; audit as a query | named graphs |

TOKI is the closest thing to an n-ary result: its *conflict sets* are n-ary, but the facts in them
are still relational rows, not role-labelled hyperedges. That is a different n than this note's.

**Continuous time.** The binary TKG literature left discrete snapshots years ago. Know-Evolve models
facts as "a multivariate point process whose intensity function is modulated by the score for that
fact" ([Trivedi, Dai, Wang and Song, arXiv:1705.05742, 2017](https://arxiv.org/abs/1705.05742);
ICML 2017 `[unverified]`), and TANGO extends neural ODEs to multi-relational GCNs to keep
"continuous-time dynamic embeddings", with a graph transition layer for "edge formation and
dissolution" ([Han, Ding, Ma, Gu and Tresp, EMNLP 2021, pp. 8352–8364](https://aclanthology.org/2021.emnlp-main.658/)).
No n-ary or hyper-relational continuous-time model was found (§3).

## 3. The n-ary state of the art, and the two words it turns on

The temporal KG field splits its tasks: **interpolation** "estimates and predicts the missing
elements … through the relevant available information" at timestamps inside the observed range, and
**extrapolation** "typically focuses on continuous TKGs and predicts future events"
([Wang, Wang, Qiu, Pan, Xiong, Liu, Luo, Liu, Hu, Yin and Gao, *A Survey on Temporal Knowledge Graph
Completion*, arXiv:2308.02457, 2023](https://arxiv.org/abs/2308.02457)). For agent memory only
extrapolation-adjacent behaviour matters: "who owns it *now*" is a query at a timestamp beyond every
one in the store.

Sorting the n-ary temporal models by that axis corrects a conflation in
[temporal-and-dynamic-khgs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md) §3, whose
results table puts HypeTKG and NE-Net in the same column:

| Model | Setting | Time representation |
|---|---|---|
| **NE-Net** ([Findings of EMNLP 2023](https://aclanthology.org/2023.findings-emnlp.77/)) | **extrapolation** — "reasoning tasks at future timestamps can be realized via task-specific decoders" | discrete timestamp per n-tuple |
| **MT-Path** ([Hou, Su, Jin, Li, Bai, Guo and Cheng, arXiv:2505.12788, 19 May 2025](https://arxiv.org/abs/2505.12788)) | **extrapolation**, RL multi-hop over history | discrete timestamp per n-tuple |
| **HypeTKG** ([Ding, Wu, Wu, Xia and Tresp, Findings of EMNLP 2024](https://arxiv.org/abs/2307.10219)) | **interpolation only** — "we only focus on the interpolated LP on HTKGs and leave extrapolation for future work" | timestamp; "We decompose time periods into a series of timestamps" |
| **VITA** ([Un, Lu, Yang and Yang, arXiv:2505.11803, 17 May 2025](https://arxiv.org/abs/2505.11803)) | **interpolation** — "This paper focuses on the interpolation setting" | *time triplet* `(c, t₁, t₂)`, `c ∈ {Since, Until, Period, Invariant}` |
| **HTKGH** ([Ahrabian, Boxer and Pujara, arXiv:2601.00430, 1 Jan 2026](https://arxiv.org/abs/2601.00430)) | **forecasting**, LLM-prompted | timestamp on a generalized hyperedge |

Three readings follow.

**VITA is the closest existing thing to valid time on a hyper-relational fact, and it is pointed the
wrong way.** Its time triplet is exactly an interval algebra — `(Since, t₁, +∞)`, `(Until, −∞, t₂)`,
`(Period, t₁, t₂)`, `(Invariant, −∞, +∞)` — which is what §1(a) asks for, including the infinite
upper bound that an open-ended fact needs. But it is evaluated by interpolation on Wiki, YAGO,
Wikipeople and ICEWS14, i.e. on filling holes in history, not on answering as-of-now. Lifting VITA's
representation to the extrapolation protocol is a small, well-defined experiment and appears not to
have been run.

**MT-Path is the current n-ary extrapolation leader and is missing from the KB.** On the two N-TKG
datasets it reports MRR 80.69 on NWIKI against NE-Net's 72.03, and 49.91 on NICE against 48.98
([arXiv:2505.12788](https://arxiv.org/abs/2505.12788); the NE-Net figure matches the 0.720 already
recorded in [temporal-and-dynamic-khgs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md) §3,
which is a useful cross-check on both).

**HTKGH is the first n-ary *forecasting* formalism, and it is a benchmark rather than a model.**
Ahrabian et al. name the exact gap: "One of the critical limitations of HTKGs is a lack of support
for more than two primary entities in temporal facts, which commonly occur in real-world events."
They formalise Hyper-Relational Temporal Knowledge *Generalized Hypergraphs*, show backward
compatibility with HTKGs, release `htkgh-polecat` from the POLECAT event database, and benchmark
LLMs on it ([arXiv:2601.00430](https://arxiv.org/abs/2601.00430), v2 17 Mar 2026). It is still a
*timestamped event* model: no validity interval, no invalidation, no supersession.

**Absence, dated 2026-09-21.** An arXiv full-text API search returns **zero** abstracts containing
the exact phrase "temporal knowledge hypergraph"; zero for `"valid time" AND "hyperedge"`; zero for
`"n-ary" AND "extrapolation"` (control query `"knowledge hypergraph"` returns results normally).
The seed premise that valid-time-on-the-hyperedge has not been lifted from the binary case survives
verification — but with the correction that n-ary *extrapolation* does exist (NE-Net 2023, MT-Path
2025, HTKGH 2026); what does not exist is n-ary **valid time, retraction and supersession**.

## 4. The consumers: hypergraph agent memory, and what it does not model

Five systems, all 2026, all verified against their abstracts or HTML this run.

| System | Structure | Benchmarks | Time model |
|---|---|---|---|
| **HyperMem** ([Yue et al., ACL 2026 Main](https://arxiv.org/abs/2604.08256)) | topics → episodes → facts; `ℰᴱ` links episodes in a topic, `ℰᶠ` links facts in an episode, each with a weight `w ∈ [0,1]` | LoCoMo, **92.73%** LLM-as-a-judge | none on the hyperedge; "the time gap between consecutive dialogues" used only for episode segmentation `[unverified beyond the HTML read]` |
| **HyperSkill** ([Xu, Yang and Huang, arXiv:2608.16114, 17 Aug 2026](https://arxiv.org/abs/2608.16114)) | two node types (subtask steps, reusable skills), one hyperedge per trajectory | **xBench, GAIA, WebWalkerQA**, GPT-4o and Qwen3-30B-A3B, ten baselines; **+11.51 GAIA**, **+11.18 WebWalkerQA** | none; evolution is "periodic structure-informed maintenance [that] prunes low-utility nodes and merges redundant skills via quality-weighted propagation" — utility, not validity |
| **EvoGraph-R1** ([Lin et al., CVPR 2026](https://arxiv.org/abs/2607.12764)) | multimodal hypergraph as an MDP environment | 2WikiMultiHopQA, HotpotQA, NQ, E-VQA, OK-VQA, InfoSeek | none |
| **EdgeMem** ([Cui, Cao, Wen, Yuan, Feng and Chen, arXiv:2609.05553, 3 Sep 2026](https://arxiv.org/abs/2609.05553)) | LLM-free multi-anchor hypergraph over preserved original turns | LoCoMo **61.01** strict-judge (2nd best 58.70); LongMemEval-S R@3 81.49, NDCG@3 90.49 | calendar-**month** anchor keyed off the transcript date; no validity window |
| **MAGE** ([Feng, Zhang, Luo, Lin, Yang and Luu, arXiv:2608.29678, 30 Aug 2026](https://arxiv.org/abs/2608.29678)) | "heterogeneous temporal hypergraph" of agents, messages, tools, errors, procedures, documents, entities, decisions, evidence | "various memory baselines" — numbers not extracted `[unverified]` | claims "lifecycle management" and "decision driven updates"; whether these are bitemporal fields could not be verified this run |

**EvoGraph-R1 in detail**, since the KB has only a one-line row for it. The state is
`sₜ = (𝒢ₜ, ℋₜ, q)` — current hypergraph, action history, query — and the action set is
**GraphRetrieve / WebSearch / GraphEdit / Answer**, with GraphEdit decomposing into Insert, Update
and Delete. The trajectory reward combines a structural term
`min(1.0, η·Σ 𝕀_valid(t))` with `η = 0.5`, an F1-style answer term, and a per-action cost penalty
`−λ·Σ c(aₜ)`, with the answer term gated on the structural term reaching 1.0
([HTML read of arXiv:2607.12764v1, 2026-09-21](https://arxiv.org/html/2607.12764v1)). So the agent
*can* Update and Delete — the only system here with an explicit retraction action — but the reward
is answer-F1 plus well-formedness, with nothing rewarding a correct *invalidation*, and whether
edits persist across queries rather than within an episode is not stated in the paper
`[unverified]`. Editable is not the same as versioned: a Delete here destroys history, where
Graphiti's invalidation preserves it.

**The pattern.** Every hypergraph memory system above treats time as a retrieval *cue* — segment
episodes by gaps, group turns by month, rank by recency — and none treats it as a *truth condition*
on the hyperedge. The one system in the comparison tables that does model validity, Zep, is binary.

## 5. The survey confirms the split is structural

The one 2025–2026 graph-based agent-memory survey found is Yang, Zhou, Xiao, Dong, Zhuang, Zhang,
Wang, Hong, Yuan, Xiang, Chen, Zhou, Zhang, Liu, Su, Wang, Chang and Huang, *Graph-based Agent
Memory: Taxonomy, Techniques, and Applications*
([arXiv:2602.05665, 5 Feb 2026](https://arxiv.org/abs/2602.05665); resource list at
[DEEP-PolyU/Awesome-GraphMemory](https://github.com/DEEP-PolyU/Awesome-GraphMemory), checked
2026-09-21). It organises the field by lifecycle — extraction, storage, retrieval, evolution — and
under **storage** its categories are: knowledge-graph structure, hierarchical memory structure,
**temporal graph structure**, **hypergraph structure**, hybrid graph architectures.

That taxonomy is the finding. Hypergraphs are indeed a first-class option, with the trade-off stated
as expected — "Hypergraphs address this by employing hyperedges that can connect an arbitrary number
of nodes, preserving the integrity of n-ary relations", against binary graphs that "suffer from
information loss when representing complex, multi-entity interactions". But *temporal* and
*hypergraph* are **siblings, not composable dimensions**: the temporal row is the quadruple
`(s, r, o, t)` with bi-temporal valid/transaction time and contradiction resolution "through
temporal invalidation rather than overwrites", and the hypergraph row is untimed. A reader following
this survey's design space cannot pick both. (A second, later survey — Nguyen, Qiu, Chen and Liew,
*Graph-Based Personalized Memory for LLM Agents*, [arXiv:2609.08599, 8 Sep 2026](https://arxiv.org/abs/2609.08599)
— is lifecycle-organised too; whether it has a hypergraph row could not be confirmed from the
abstract page `[unverified]`.)

## 6. Do the benchmarks even test supersession?

Partly, and the split matters for anyone claiming a temporal contribution.

**LongMemEval** does test it directly. Its five abilities are information extraction, multi-session
reasoning, temporal reasoning, **knowledge updates** and abstention, over 500 questions in scalable
chat histories ([Wu, Wang, Yu, Zhang, Chang and Yu, *LongMemEval*, ICLR 2025 /
arXiv:2410.10813](https://arxiv.org/abs/2410.10813)). "Knowledge updates" is the supersession
category. Of the hypergraph systems in §4, only EdgeMem reports LongMemEval-S, and it reports
session-level retrieval and overall accuracy, not the per-ability breakdown.

**LoCoMo** tests temporal *reasoning*, which is not the same thing. Its 50 conversations average
~300 turns and ~9K tokens over up to 35 sessions, and its 7,512 questions split into single-hop
(2,705), multi-hop (1,104), temporal reasoning (1,547), open-domain knowledge (285) and adversarial
(1,871) ([Maharana, Lee, Tulyakov, Bansal, Barbieri and Fang, arXiv:2402.17753, 2024](https://arxiv.org/abs/2402.17753)).
Temporal-reasoning questions ask about ordering and dates; nothing in the category definition
requires a fact to have been *replaced*.

HyperMem's per-category LoCoMo numbers are the most informative single table found this run
([HTML read of arXiv:2604.08256v2, 2026-09-21](https://arxiv.org/html/2604.08256v2), Table 1,
LLM-as-a-judge %):

| Method | Single-hop | Multi-hop | Temporal | Open domain | Overall |
|---|---|---|---|---|---|
| HyperMem | 96.08 | 93.62 | **89.72** | 70.83 | **92.73** |
| HyperGraphRAG | 90.61 | 80.85 | 85.36 | 70.83 | 86.49 |
| Zep | 61.70 | 41.35 | 49.31 | **76.60** | 65.99 |

Two observations. First, **temporal is HyperMem's weakest reasoning category** (89.72 against 96.08
single-hop) — consistent with a structure that has no temporal semantics. Second, the bitemporal
system in the table is beaten everywhere except open domain, where it wins; that is a reproduction by
a competitor, on a benchmark whose temporal category is about dates rather than updates, and should
not be read as evidence that bitemporal modelling does not pay. The honest statement is that
**no published experiment isolates supersession as the dependent variable for a hypergraph memory.**

Note also that EdgeMem's LoCoMo *strict-judge* 61.01 and HyperMem's *LLM-as-a-judge* 92.73 are not
comparable numbers; the judge protocol differs. Cross-paper LoCoMo tables in this KB should carry
the protocol.

## 7. Design sketch: what a temporal knowledge hypergraph needs

Minimum data model, assembled from what the binary systems already ship plus §1:

1. **Hyperedge record** `⟨id, r, {(ρᵢ, vᵢ)}, τᵥ, τₜ, prov⟩` with `τᵥ = [t_valid, t_invalid)` and
   `τₜ = [t_created, t_expired)`, both half-open, `t_invalid` defaulting to `+∞`. Adopt VITA's
   `(c, t₁, t₂)` triplet as the surface syntax so `Since`/`Until`/`Period`/`Invariant` are explicit
   rather than encoded by sentinel values.
2. **Key declaration per relation**: `key(r) = K ⊆ roles(r)`. Without it, supersession is undecidable
   and "who owns the project *now*" has no defined answer. This is the piece no existing n-ary schema
   language provides.
3. **Invalidate, never delete** (Graphiti) *plus* an audit row for the loser (TOKI). A `supersedes`
   hyperedge carrying the adjudicating evidence, so retraction is itself a first-class fact.
4. **Two query modes**: as-of `t` on the valid axis (what was true) and as-at `t′` on the transaction
   axis (what we believed), composable — the point-in-time retrieval that
   [arXiv:2607.26520](https://arxiv.org/abs/2607.26520) implements on binary edges.
5. **Confidence that decays with staleness at read time.** Returning a fact whose `t_invalid` is
   `+∞` but whose `t_valid` is two years old should not be indistinguishable from a fact confirmed
   yesterday. None of the five hypergraph systems in §4 exposes such a signal.
6. **An extrapolation evaluation**, not an interpolation one: hold out the tail of the timeline and
   ask as-of-now questions. `htkgh-polecat` is the nearest existing harness; LongMemEval's
   knowledge-update slice is the nearest agent-side one.

The 2026–27 paper the seed predicts is therefore narrower than "a temporal knowledge hypergraph":
it is **VITA's interval representation + a declared key + Graphiti's invalidation semantics,
evaluated under NE-Net/MT-Path's extrapolation protocol and on LongMemEval's knowledge-update
slice.** Every component exists; no paper has assembled them.

## Open questions raised here

- What is the right granularity for validity on an n-ary fact — the whole hyperedge, or each
  role-binding — and does per-role validity avoid the `n−1` duplicated bindings that whole-edge
  closure forces on every single-role change?
- Can a *key role set* be induced from data rather than declared, so that supersession is detectable
  in an extracted (rather than schema-designed) knowledge hypergraph?
- Does VITA's time triplet, re-evaluated under an extrapolation split, beat timestamp-per-n-tuple
  models such as MT-Path, or does the interval representation only help interpolation?
- Would adding Graphiti-style invalidation to HyperMem move its LoCoMo temporal column (89.72) or
  its LongMemEval knowledge-update score, and is either the right measurement?
- Is there any continuous-time (point-process or neural-ODE) model of n-ary facts, as Know-Evolve
  and TANGO are for binary ones? None was found on 2026-09-21.
- EvoGraph-R1 has Insert/Update/Delete but rewards only answer F1 and well-formedness. What reward
  would make an agent retract correctly, and can it be measured without a ground-truth timeline?

## Sources

- Rasmussen, P., Paliychuk, P., Beauvais, T., Ryan, J., Chalef, D. *Zep: A Temporal Knowledge Graph Architecture for Agent Memory.* arXiv:2501.13956, 20 Jan 2025. <https://arxiv.org/abs/2501.13956>
- Wang, Z. *TOKI: A Bitemporal Operator Algebra for Contradiction Resolution in LLM-Agent Persistent Memory.* arXiv:2606.06240, 4 Jun 2026. <https://arxiv.org/abs/2606.06240>
- Niksarli, A., Baheti, G. *A Graph-Native Bitemporal Memory Store for Conversational AI Agents.* arXiv:2607.26520, 29 Jul 2026. <https://arxiv.org/abs/2607.26520>
- Brown, S. *Quipu: A Governed Bitemporal Knowledge Graph Store.* arXiv:2608.16813, 17 Aug 2026. <https://arxiv.org/abs/2608.16813>
- Trivedi, R., Dai, H., Wang, Y., Song, L. *Know-Evolve: Deep Temporal Reasoning for Dynamic Knowledge Graphs.* arXiv:1705.05742, 2017. <https://arxiv.org/abs/1705.05742>
- Han, Z., Ding, Z., Ma, Y., Gu, Y., Tresp, V. "Learning Neural Ordinary Equations for Forecasting Future Links on Temporal Knowledge Graphs" (TANGO). *EMNLP 2021*, pp. 8352–8364. <https://aclanthology.org/2021.emnlp-main.658/>
- Wang, J., Wang, B., Qiu, M., Pan, S., Xiong, B., Liu, H., Luo, L., Liu, T., Hu, Y., Yin, B., Gao, W. *A Survey on Temporal Knowledge Graph Completion: Taxonomy, Progress, and Prospects.* arXiv:2308.02457, 4 Aug 2023. <https://arxiv.org/abs/2308.02457>
- Hou, Z., Jin, X., Li, Z., Bai, L., Guan, S., Zeng, Y., Guo, J., Cheng, X. "Temporal Knowledge Graph Reasoning Based on N-tuple Modeling" (NE-Net). *Findings of EMNLP 2023*. <https://aclanthology.org/2023.findings-emnlp.77/>
- Hou, Z., Su, M., Jin, X., Li, Z., Bai, L., Guo, J., Cheng, X. *Mixture Policy based Multi-Hop Reasoning over N-tuple Temporal Knowledge Graphs* (MT-Path). arXiv:2505.12788, 19 May 2025. <https://arxiv.org/abs/2505.12788>
- Ding, Z., Wu, Jingcheng, Wu, Jingpei, Xia, Y., Tresp, V. *Temporal Fact Reasoning over Hyper-Relational Knowledge Graphs* (HypeTKG). Findings of EMNLP 2024; arXiv:2307.10219. <https://arxiv.org/abs/2307.10219>
- Un, C., Lu, Y., Yang, T., Yang, D. *VITA: Versatile Time Representation Learning for Temporal Hyper-Relational Knowledge Graphs.* arXiv:2505.11803, 17 May 2025. <https://arxiv.org/abs/2505.11803>
- Ahrabian, K., Boxer, E., Pujara, J. *Toward Better Temporal Structures for Geopolitical Events Forecasting.* arXiv:2601.00430, 1 Jan 2026 (v2, 17 Mar 2026). <https://arxiv.org/abs/2601.00430>
- Yue, J., Hu, C., Sheng, J., Zhou, Z., Zhang, W., Liu, T., Guo, L., Deng, Y. *HyperMem: Hypergraph Memory for Long-Term Conversations.* ACL 2026 Main; arXiv:2604.08256, 9 Apr 2026 (v2, 10 Apr 2026). <https://arxiv.org/abs/2604.08256> ; <https://aclanthology.org/2026.acl-long.1627/>
- Xu, R., Yang, T., Huang, W.-C. *HyperSkill: Self-Evolving LLM Agents via Hypergraph-Structured Skill Memory.* arXiv:2608.16114, 17 Aug 2026. <https://arxiv.org/abs/2608.16114>
- Lin, J., Jiang, C., Lin, X., Zhang, R., Zhu, X., Liu, J., Tang, C., Du, Y., Gao, S., Ning, J., Liu, L., Huang, Z., Li, T., Ye, J., He, J. *EvoGraph-R1: Self-Evolving Multimodal Knowledge Hypergraphs for Agentic Retrieval.* CVPR 2026; arXiv:2607.12764, 14 Jul 2026. <https://arxiv.org/abs/2607.12764>
- Cui, Z., Cao, J., Wen, Z., Yuan, B., Feng, J., Chen, S. *EdgeMem: LLM-Free Agent Memory Construction and Retrieval via Evidence-Preserving Multi-Anchor Hypergraph.* arXiv:2609.05553, 3 Sep 2026. <https://arxiv.org/abs/2609.05553>
- Feng, Y., Zhang, R., Luo, H., Lin, Z., Yang, C., Luu, A. T. *Diachronic Hypergraphs for Orchestrated Multi-Agent Multimodal Memory Curation* (MAGE). arXiv:2608.29678, 30 Aug 2026. <https://arxiv.org/abs/2608.29678>
- Yang, C., Zhou, C., Xiao, Y., Dong, S., Zhuang, L., Zhang, Y., Wang, Z., Hong, Z., Yuan, Z., Xiang, Z., Chen, S., Zhou, H., Zhang, Q., Liu, N., Su, J., Wang, X., Chang, Y., Huang, X. *Graph-based Agent Memory: Taxonomy, Techniques, and Applications.* arXiv:2602.05665, 5 Feb 2026. <https://arxiv.org/abs/2602.05665>
- DEEP-PolyU. *Awesome-GraphMemory* repository, GitHub, checked 2026-09-21. <https://github.com/DEEP-PolyU/Awesome-GraphMemory>
- Nguyen, D. D. A., Qiu, Z., Chen, S., Liew, A. W.-C. *Graph-Based Personalized Memory for LLM Agents: Representation, Evolution, Retrieval, and Evaluation.* arXiv:2609.08599, 8 Sep 2026. <https://arxiv.org/abs/2609.08599>
- Wu, D., Wang, H., Yu, W., Zhang, Y., Chang, K.-W., Yu, D. *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory.* ICLR 2025; arXiv:2410.10813, 14 Oct 2024. <https://arxiv.org/abs/2410.10813>
- Maharana, A., Lee, D.-H., Tulyakov, S., Bansal, M., Barbieri, F., Fang, Y. *Evaluating Very Long-Term Conversational Memory of LLM Agents* (LoCoMo). arXiv:2402.17753, 27 Feb 2024. <https://arxiv.org/abs/2402.17753>
