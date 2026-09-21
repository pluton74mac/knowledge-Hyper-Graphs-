---
title: Skill-driven extraction and the scenario gap (Hyper-KGGen, HyperDocRED, Hyper-Extract)
type: paper-note
status: draft
tags: [hypergraph, n-ary, construction, extraction, llm, skills, benchmark, incremental, Hyper-KGGen, HyperDocRED, Hyper-Extract]
created: 2026-09-21
updated: 2026-09-21
---

# Skill-driven extraction and the scenario gap

Extraction is the narrow part of the knowledge-hypergraph stack. Every retrieval, embedding and reasoning
result downstream is computed over a hypergraph that some LLM pipeline guessed at, and the one published
measurement of how good that guess is puts the reference systems at **micro precision 0.38 / recall 0.11**
([Huang et al., 2026](https://arxiv.org/abs/2602.19543), Table 6). This note reads the two 2026 artefacts
that attack the problem directly — the Hyper-KGGen paper with its HyperDocRED benchmark, and the
Hyper-Extract tool — against their primary sources and their code, and then asks the question neither
answers: can an extractor be *incremental and consistent* at the same time?

It extends [LLM-based KHG construction](llm-based-khg-construction.md) §5 (which lists Hyper-KGGen among
the 2026 follow-ups), [n-ary relation extraction from text](n-ary-relation-extraction-from-text.md) §5
(supervised extractors), [incremental and streaming construction](incremental-and-streaming-construction.md)
(the four update problems) and [evaluation of constructed KHGs](evaluation-of-constructed-khgs.md) (the
metric and the benchmark table). Read those first; this note does not repeat them.

## 1. What is now verified about the paper

The KB previously recorded Hyper-KGGen as a 2026 arXiv preprint with no venue. The v2 HTML states the
venue on its first page: **KDD '26**, "Proceedings of the 32nd ACM SIGKDD Conference on Knowledge Discovery
and Data Mining V.2 (KDD '26), August 09–13, 2026, Jeju Island, Republic of Korea", DOI
`10.1145/3770855.3818198`, ISBN 979-8-4007-2259-2, licence **CC BY 4.0**
([arXiv:2602.19543v2](https://arxiv.org/html/2602.19543v2), v1 23 Feb 2026, v2 5 Jul 2026). The repository
README says "Accepted by *KDD 2026*" ([Rizrock/Hyper-KGGen](https://github.com/Rizrock/Hyper-KGGen),
checked 2026-09-21). Rizhuo Huang (Xi'an Jiaotong) and Yifan Feng (Tsinghua) "contributed equally";
Shaoyi Du and Yue Gao are corresponding. Feng and Gao are also the Hyper-RAG authors, and Feng is the
author of Hyper-Extract (§7) — construction, retrieval and tooling here are one group's programme, which
is worth keeping in mind when reading the baseline comparisons.

## 2. The scenario gap

The claimed obstacle is not model capacity but prompt–domain alignment: "generic extraction models struggle
to generalize across diverse domains (e.g., biomedical, legal, financial) due to the presence of industry
jargon, implicit logic, and domain-specific boundaries … while generic prompts yield suboptimal
performance, manually optimizing prompts for specific domains significantly boosts extraction quality.
This observation confirms that the model possesses the latent capability to handle domain tasks but lacks
the explicit Skill to align with scenario-specific constraints." Hand-writing a prompt per domain "is
unscalable", so the skills must be learned.

*Critique.* The "preliminary analysis" that motivates the whole framework is shown only as Figure 1, an
illustration of one KGGen extraction with a generic versus a domain prompt. No quantitative
prompt-sensitivity study is reported. The framing is plausible and matches the prompt-optimisation
literature cited in [LLM-based KHG construction](llm-based-khg-construction.md) §6, but it is asserted here,
not measured.

## 3. Coarse-to-fine: skeleton first, details later

The forward pass is four stages: adaptive chunking at sentence/paragraph boundaries with an overlap window;
entity extraction per chunk (name, fine-grained type, description); coarse-to-fine hyperedge extraction;
and global deduplication by "cross-chunk coreference resolution" plus merging of "hyperedges that share
identical semantic meanings", with descriptions synthesised across instances.

The hyperedge stage is the contribution. Three granularities are extracted in order:

| Level | Paper's name | Content |
|---|---|---|
| Coarsest | **Binary Relations (The Skeleton)** | "fundamental pairwise links between entities (e.g., *Subject-Predicate-Object*) … providing the basic connectivity without complex constraints" |
| Middle | **Qualified Binary Relations (Contextual Augmentation)** | binary links plus "qualifying arguments such as time, location, or specific conditions" |
| Finest | **General N-ary Relations (Event Details)** | "entire events or story plots, where multiple participants jointly instantiate a coherent scenario" |

This is the hyper-relational/event/hypergraph schema ladder of Text2NKG walked in one pipeline (see
[schema induction](schema-induction-and-ontology-alignment.md) §2), with the stated purpose of reducing
"cognitive load" rather than of producing a typed schema.

**The failure mode it is built against is asserted, not measured.** The motivating claim is that existing
hypergraph extractors "often exhibit weakness in capturing fundamental low-order pairwise associations,
leading to a 'top-heavy' structure that lacks foundational connectivity". No arity histogram of any
baseline's output is reported anywhere in the paper, and Table 6 is arity-agnostic (one micro and one macro
P/R/F1 per system). The HyperDocRED statistics split *gold* relations into "low-order" and "high-order"
(§6) but nothing splits *predictions* that way. So the paper's second headline problem — structural
imbalance — is at present an unquantified diagnosis. An arity-stratified version of Table 6 would settle it
and is cheap to produce from the released code; this is open question **[03.2]** in a new dress.

**The hyperedge type in the released code is role-free.** `skill_acquisition/schema.py` defines an edge as
`reasoning_trajectory` (a free-text implication chain), `linked_nodes: list[str]` with `min_length=2`, a
free-string `type` label defaulting to `related_to`, and a `description`. A validator strips and
de-duplicates participants, and the field documentation says outright: "Order has no semantics. Do not
repeat the same node name." So the only structural constraint on a hyperedge is **arity ≥ 2 with distinct
participants**. There is no role inventory, no per-type arity signature, no identity rule. The
qualifiers that the coarse-to-fine ladder is designed to capture (time, location, amount, count) enter as
ordinary participants of an unordered set, recoverable only from the prose description. That is the same
role-free hyperedge criticised in [what is a knowledge hypergraph](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md),
reached by a more careful route.

## 4. The Global Skill Library and the stability reward

The backward pass freezes the LLM and optimises an external semantic memory `S`, initialised empty:
`Ĝ = f(D, S; θ)`.

1. **Parallel rollout.** `K` independent samples at non-zero temperature `T` probe "the model's capability
   boundaries". So instability is measured by *resampling*, not by input perturbation.
2. **Stability-based relative reward.** Each sample is soft-matched to the gold hypergraph `G*`, and the
   **gold** relations are partitioned by retrieval frequency: **Stable** (recovered in all K samples,
   "General Knowledge"), **Unstable** (some samples, "Scenario-Specific Knowledge"), **Miss** (none,
   "Domain-Exclusive Knowledge or deep reasoning gaps").
3. **Reflective computation.** Stable relations are ignored. *Path induction* summarises the reasoning path
   from the successful trajectories of an unstable relation. *Hindsight reasoning* injects the gold relation
   "into the context as a posterior condition" so the model "backtracks through the document, locates
   overlooked evidence, and constructs a logical chain from scratch".
4. **Library controller.** Proposals are consolidated by ADD / MODIFY / MERGE / KEEP operations; at
   inference "relevant skills from `S` are dynamically retrieved and injected into the prompt".

**Skills are free text, in a fixed two-slot shape.** The released `skill_acquisition/prompts.py` stores each
skill as `{"trigger": …, "action": …}` (ids `E0, E1, …` in `experiences.json`). The reflection prompt
demands "exactly ONE `<Insight>` block", where "TRIGGER describes the textual/discourse condition that
activates the rule" and "ACTION describes what the extractor should bind into ONE hyperedge using Known
nodes only", "preferably <= 70 words"; the controller prompt caps a stored skill at "`trigger + action`
within 50 words total" and explicitly rejects schema paraphrase: "SKIP items whose trigger/action merely
rephrase a relation schema (slot listing or '… instantiate `<edge_type>`') without transferable cue or
disambiguation". This is a deliberate design choice, and it is the opposite of a typed schema algebra: the
library is prevented by prompt from containing arity constraints, role inventories or identity rules.

Three things the paper does not foreground, verified from the repository (checked 2026-09-21, latest commit
2026-06-07 "refactor project structure"):

- **Skill acquisition is supervised.** `_find_critique_relations` partitions *ground-truth* relations by
  how many rollouts missed them; hindsight reasoning injects `G*` directly. The "stability" signal is
  therefore stability *relative to an annotated gold graph*, not self-consistency. A new scenario needs
  annotated seed documents before it can acquire skills — which is a substantial part of the cost the
  scenario-gap framing set out to avoid. Contrast the pure self-consistency route of
  [Khrouf et al., 2026](https://arxiv.org/abs/2607.20506) (APIA 2026), which needs no gold data and is
  correspondingly weaker as a signal.
- **The released code does not implement hindsight reasoning.** `ExperienceUpdater.run` computes both
  `hard_cases` (the Miss Set) and `reflection_cases` (the Unstable Set), prints and serialises both, then
  distils skills from `reflection_cases` only. `prompts.py` contains `REFLECTION_CASE_CRITIQUE_TEMPLATE`
  and `BATCH_EXPERIENCE_UPDATE_TEMPLATE` and no hindsight template. The controller's operations in code are
  **ADD / MERGE / SKIP / DELETE**, not the paper's ADD / MODIFY / MERGE / KEEP.
- **The skill-distilling model is hard-coded** as `gpt-5-mini` at temperature 0.5, independent of the
  extraction backbone that Table 3 varies.

## 5. Numbers, and what the metric actually measures

n-ary relation extraction on the HyperDocRED test split (Table 6; all systems on GPT-4o-mini):

| System | Micro P | Micro R | Micro F1 | Macro P | Macro R | Macro F1 |
|---|---|---|---|---|---|---|
| HyperGraphRAG | 0.3828 | 0.1072 | 0.1675 | 0.4018 | 0.1208 | 0.1710 |
| HyperRAG | 0.2439 | 0.2050 | 0.2228 | 0.2486 | 0.2224 | 0.2196 |
| CogRAG | 0.2884 | 0.1794 | 0.2212 | 0.2926 | 0.1933 | 0.2243 |
| Hyper-KGGen | 0.8327 | 0.3140 | 0.4560 | 0.8436 | 0.3552 | 0.4806 |
| **Hyper-KGGen+** | 0.8024 | **0.4300** | **0.5600** | 0.8142 | 0.4609 | 0.5736 |

Fact verification on MINE (100 LLM-written articles, 15 gold facts each, from KGGen): Hyper-KGGen+ 0.8367
with GPT-4o-mini, 0.7133 Gemini-2.5-Flash, 0.8473 Qwen3, 0.8020 DeepSeek-V3.2, against KGGen 0.7540 /
0.6113 / 0.7527 / 0.7273 (Table 3). Downstream RAG on UltraDomain (Table 2, five LLM-judged dimensions):
average 85.10 (Mix) and 86.72 (Pathology) for Hyper-KGGen+, against 84.32 / 86.03 for Hyper-RAG and
83.76 / 85.84 for HyperGraphRAG. Rollout ablation (Table 4): K = 2 → 8 moves HyperDocRED recall
0.4126 → 0.4769 and MINE accuracy 0.8314 → 0.8422 while precision falls 0.8232 → 0.8078.

Four cautions:

1. **The match is soft.** Relation descriptions are embedded with `all-MiniLM-L6-v2`, a cosine-similarity
   matrix is built and the Hungarian algorithm finds "the optimal global matching between predicted and
   ground-truth relations", at thresholds of 0.65/0.70/0.75. Participant sets are not required to agree. A
   precision of 0.80 therefore means "its prose paraphrases a gold fact's prose", not "it recovered the
   right entity set with the right relation". This is the soft-F1 protocol recommended in
   [evaluation](evaluation-of-constructed-khgs.md) §7 step 2, used *without* the strict score of step 1.
2. **Recall is the story.** The best published document-level n-ary recall is 0.43. More than half of the
   annotated facts in a 100-document benchmark are still missed by the system that wins on it.
3. **Skills cost precision.** Hyper-KGGen+ trades 0.8327 → 0.8024 precision for 0.3140 → 0.4300 recall, and
   Table 4 shows the same trade widening with K. The paper's own reading is that "more unstable or
   low-confidence candidates may enter the skill acquisition stage and introduce additional noise into the
   skill library".
4. **The downstream claim is correctly hedged by the authors themselves.** "Improving the hypergraph
   substrate can boost utility even with simple retrieval, highlighting that high-quality hypergraph
   construction is a primary driver of downstream utility" is followed immediately by "the gap between
   Hyper-KGGen and baselines is modest, since the graph mainly serves retrieval while the generation relies
   on raw text chunks. With sufficient retrieval budget, baselines tend to retrieve highly overlapping text,
   narrowing the quality gap." A 2.5× improvement in extraction F1 buys about 0.8 points of LLM-judged
   answer quality. That ratio is the most important number in the paper and it argues *against* treating
   answer quality as evidence about graph quality — the confound named in
   [evaluation](evaluation-of-constructed-khgs.md) §4.

## 6. HyperDocRED: small, useful, and not actually released

Statistics (Table 1) are already recorded in [evaluation](evaluation-of-constructed-khgs.md) §3 and are
confirmed here: train 50 documents / 1,016 entities / 636 correlations (326 low-order, 310 high-order);
test 100 / 2,127 / 1,371 (758 / 613). Construction: "we construct the HyperDocRED Bench based on the widely
used Re-DocRED corpus … We manually restructure the original binary annotations into n-ary relations …
Specifically, we target explicit and complete n-ary relations as expressed in the text, preserving each
relation as an integral semantic unit rather than fragmenting it into multiple binary triples." The 50
training documents exist "as the seed source for skill acquisition".

What is missing, as of 2026-09-21:

- **The data.** The paper says "we also construct and release HyperDocRED". The repository contains
  `hyper_kggen/` and `skill_acquisition/` only; its README instructs the user to point `DATA_DIR` at a
  directory containing `processed_data.json` and `processed_data_test.json`, which are not in the
  repository and are not linked from it. No Zenodo, HuggingFace or supplementary link appears in the paper
  or the README. Code licence MIT; the benchmark has no licence because it has no distribution. Re-DocRED
  upstream would have to be re-checked for its own terms before redistribution.
- **The annotation protocol.** One sentence of target definition, no annotator count, no guidelines, no
  adjudication procedure, no inter-annotator agreement. This is the gap already flagged in
  [human-in-the-loop annotation and cost](human-in-the-loop-annotation-and-cost.md) §"HyperDocRED"; nothing
  in v2 or the repository closes it.
- **An arity histogram.** "Low-order" and "high-order" are counted but never defined; no distribution over
  arity 2, 3, 4, 5+ is given, so the benchmark cannot support arity-stratified analysis even though its
  whole point is arity.

Until the files appear, HyperDocRED numbers are not reproducible by third parties, and a field with exactly
one document-level n-ary benchmark has zero available ones.

## 7. Hyper-Extract: the same pipeline family, shipped

**Verified facts** (repository `yifanfeng97/hyper-extract`, cloned and inspected 2026-09-21; commit
`395039e` of 2026-09-20, "bump version to 0.10.3"):

- Licence **Apache-2.0** (an `Apache License Version 2.0` file at the repository root, and an Apache-2.0
  badge and statement in the README). This **corrects** the KB's software-libraries row, which recorded the
  licence as GitHub metadata "Other (`NOASSERTION`)".
- Distributed on PyPI as `hyperextract`, version **0.10.3** published 2026-09-20, 19 releases, Python 3.11+.
  Repository has moved to the lower-case path `yifanfeng97/hyper-extract`; roughly 4,000 stars and 458
  forks, 533 commits on `main`.
- **Nine "auto-types"**, the strongly typed output structures, exactly as the source tree shows
  (`hyperextract/types/`): Model, List, Set, Graph, **Hypergraph**, Temporal Graph, Spatial Graph,
  Spatio-Temporal Graph, Document corpus.
- **Ten extraction engines**, not the README's "11+": `chunk_rag`, `graph_rag`, `light_rag`, `hyper_rag`,
  `hypergraph_rag`, `cog_rag`, `itext2kg`, `itext2kg_star`, `kg_gen`, `atom` (`methods/registry.py`). Three
  of the ten are hypergraph-typed (`hyper_rag`, `hypergraph_rag`, `cog_rag`).
- **Forty domain templates**, not 80: `hyperextract/templates/presets/` holds 40 YAML files across
  `general`, `finance`, `legal`, `medicine`, `tcm`, `industry`, `education`, and every one declares
  `language: [zh, en]`. The README's "80+ YAML Templates" counts language variants of the same 40.
- An MCP server (`he-mcp`) exposing read/export tools only, and exports to Obsidian, GraphML, CSV, JSON-LD
  and Cypher.

**Schema and identity are declared, per template.** Each YAML carries an `identifiers:` block — for the
general hypergraph preset, `entity_id: name`, `relation_id: '{name}|{type}'`, `relation_members:
participants` — and a validator (`utils/template_engine/validator.py`) enforces diagnostic codes HE-T001…
HE-T009: identifier expressions must reference declared fields (HE-T003), `relation_members` must have the
right shape for the auto-type (HE-T004), temporal and spatial types must declare `time_field` /
`location_field` (HE-T006), both languages must be complete (HE-T007), and a record may not exceed five
fields (HE-T008). This is more discipline than any research KHG-RAG pipeline in the KB applies.

**But the role slots exist only for the binary family.** `BINARY_GRAPH_TYPES` — graph, temporal_graph,
spatial_graph, spatio_temporal_graph — "requires `relation_members` to be a dict mapping roles to edge
field names", with `source` and `target` both mandatory. The hypergraph type instead "requires a string or
list of list-typed relation fields, not a dict": one unordered list of participant names. Roles are
enforced at arity 2 and disappear at arity 3. That is the field's central representational problem
reproduced inside a single tool's type system.

## 8. Incremental extraction, and why nobody is consistent yet

Hyper-Extract is the first tool in this survey to treat incremental ingestion as a product feature rather
than a side effect. Its declared behaviour: "Feed new documents anytime — every source is attributed and the
index updates incrementally; audit (`he info --sources`), roll back (`he remove --document`), or upsert
updated versions as your sources change", with `he feed ./ka/ contract-v2.md --source contract-v1`
re-feeding under an existing source id so that "old facts roll back automatically". In code, both node and
edge memories are constructed with `track_sources=True`, annotated "source ledger for per-document rollback
(#84)".

Three mechanisms actively work towards consistency, and each has a limit:

| Mechanism | What it does | Where it breaks |
|---|---|---|
| **Known-node injection** | the hyperedge prompt receives the chunk's already-extracted node keys as `known_nodes`, so participants are drawn from an existing vocabulary | the vocabulary is per chunk plus long-term memory keys; a new document is free to coin a variant name |
| **Strict dangling-edge pruning** | `_prune_dangling_edges` drops any hyperedge with a participant absent from the node set *or* long-term memory: "Strict mode: ALL participants must exist" | it enforces referential integrity, not identity: a forked entity satisfies it perfectly |
| **Keyed merge with an LLM merger** | node and edge memories are `OMem` instances (the author's `ontomem`, Apache-2.0) whose default strategy is `MergeStrategy.LLM.BALANCED` | identity is exact string equality on the key; what happens *after* a key collision is an LLM call, so merging is non-deterministic and unauditable |

The two failure modes named in the brief both survive:

- **Entity forking.** Identity is `entity_id: name`. "Nikola Tesla" and "Tesla" are two nodes; a subsequent
  document that mentions only the short form grows a parallel subgraph. The template guideline asks the
  model to "maintain consistent naming for the same node throughout the text" — *within* a text. Nothing
  reconciles across insertions. See [entity resolution and canonicalisation](entity-resolution-and-canonicalisation.md) §4.
- **Silent arity change.** The general hypergraph preset's `relation_id` is `'{name}|{type}'` — the
  participant list is *not* part of the key. Two extractions of "Founding of SpaceX" with type
  `founding` collide even if one has participants {Musk, SpaceX} and the other {Musk, SpaceX, 2002,
  Hawthorne}; the LLM merger then reconciles them into one record. A binary edge can thereby be promoted to
  n-ary — or an n-ary edge quietly demoted — by an insertion, with no conflict raised and no version
  recorded. The alternative convention is in the library's own docstring, where the example edge key is
  `f"{x.label}_{sorted(x.participants)}"`; that choice makes arity part of identity and so forks instead of
  merging. **Neither convention is right**, which is precisely open question **[03.1]**: whether `r(a,b)`
  and `r(a,b,t)` are the same fact is a modelling decision that the identity expression silently makes.

Nothing else in the 2026 literature does better for hypergraphs. Searches on 2026-09-21 (WebSearch for
consistent/incremental knowledge-hypergraph extraction, arity conflict and entity forking; arXiv listing
sweeps) surfaced **no paper proposing consistency guarantees for incremental knowledge-hypergraph
extraction**. The nearest work is all binary or all refinement-without-identity:

- **RAKG** ([Zhang et al., 2025](https://arxiv.org/abs/2504.09823)) — a Hyper-KGGen baseline — extracts
  "pre-entities from text chunks and utilizes these pre-entities as queries for RAG", with a graph-structure
  retrieval step whose stated purpose is consistency with the graph built so far. Binary triples only, and
  the consistency is a retrieval heuristic, not a constraint.
- **iText2KG** and **ATOM** (already covered in
  [incremental construction](incremental-and-streaming-construction.md) §4–§5) are incremental by design and
  binary/temporal in output; ATOM's "stability" is the same resampling idea as Hyper-KGGen's, used as a
  metric rather than as a reward.
- **Hyper-M2RAG**'s anchor-driven refinement rebuilds local hyper-topology after an append but makes no
  identity claim about what it rebuilds.
- **Hyper-KGGen itself has no insert path at all.** It is a batch document-to-hypergraph function;
  deduplication is global and runs once. The skill library is the only thing that persists across runs, and
  a skill acquired from one scenario changes what the extractor produces for documents already ingested —
  so the *extractor* is non-stationary even where the merge logic is deterministic. Re-running after skill
  acquisition and merging the results is exactly the arity-conflict case above, unhandled.

**Absence claim, dated 2026-09-21:** no published system enforces, or claims, that inserting a document
cannot fork an entity or change an existing hyperedge's arity.

## 9. Does any extractor enforce a typed schema algebra?

| System | Arity constraint | Roles | Identity rule | Skill/guidance format |
|---|---|---|---|---|
| HyperGraphRAG | none (fragment + entity list) | none | upper-cased exact name | fixed prompt |
| Hyper-RAG | low-order = 2, high-order ≥ 2 by prompt | none | exact name | fixed prompt |
| Hyper-KGGen | `min_length=2`, distinct participants, order has no semantics (pydantic validator) | none | none stated; "identical semantic meaning" merge | free-text `{trigger, action}` ≤ 50 words, schema paraphrase explicitly rejected |
| Hyper-Extract | none beyond "list of participants"; ≤ 5 fields per record (HE-T008) | **binary family only** (`source`/`target` mandatory; `time_field`/`location_field` for temporal/spatial) | declarative per template: `entity_id`, `relation_id`, `relation_members` | YAML template + guideline prose |
| Text2NKG (contrast) | per-schema, fixed | yes, typed | dataset-defined | n/a (supervised) |

So: **no**. Hyper-Extract has the most machinery — declared identity expressions, a nine-code validator, a
typed record schema per template — and still expresses no arity bound, no role inventory for hyperedges and
no cross-document identity policy. Hyper-KGGen's skills are free text by design. The schema algebra
proposed in [schema induction](schema-induction-and-ontology-alignment.md) §6 remains unimplemented, and
[03.5] (a shape language for hypergraph incidence) is the formal version of the same gap.

## 10. Assessment (opinion)

Hyper-KGGen is the most serious construction paper in the 2026 hypergraph-RAG line, and its real
contributions are two negative results it does not advertise: that the field's reference extractors recover
about one gold fact in ten at document level, and that fixing this raises LLM-judged answer quality by under
a point. Both undercut the "hypergraph structure helps RAG" narrative more effectively than any critique in
[the critical reading note](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md).

The skill library is a good idea aimed slightly past the problem. It buys recall (+0.116 micro) at some
precision, which is worth having; but because the stability signal is computed against gold annotations, it
is a data-efficient supervised adaptation method, not an escape from annotation. Reported honestly as "50
annotated documents per scenario buys you these skills", it would be a strong result. Framed as bridging a
"scenario gap … without human intervention", it overclaims: the intervention has moved from prompt-writing
to annotation, and the released code implements only the unstable-case half of the loop.

Hyper-Extract is the more consequential artefact for practitioners: Apache-2.0, packaged, typed, provenance-
tracked, ten engines behind one CLI, and roughly nine times HyperGraphRAG's adoption. It is also the first
place where the field's unsolved identity problem becomes an operational bug rather than a philosophical
one, because it is the only tool people actually re-feed documents into. The next useful piece of work in
this area is not a better prompt: it is a hyperedge identity specification — what the key is, what happens
on arity change, and what gets versioned — plus a benchmark that inserts documents in two different orders
and checks the graphs agree.

## Open questions raised here

- **[03.7]** Is the "top-heavy" failure mode real? No paper reports the arity distribution of an extractor's
  output against gold; an arity-stratified Table 6 on HyperDocRED would test Hyper-KGGen's own motivating
  claim.
- **[03.8]** Does order of insertion change the graph? Feed the same corpus to an incremental extractor in
  two permutations and measure hyperedge-set agreement — the obvious confluence test, and nobody has run it.
- **[03.9]** What does a skill have to be, to be checkable? Hyper-KGGen's free-text `{trigger, action}`
  skills cannot be validated, composed or transferred with guarantees; a typed skill (arity signature, role
  inventory, identity rule) would be, but nothing has tried.

## Sources

- Huang, R., Feng, Y., Xue, R., Ying, S., Yong, J.-H., Shi, C., Du, S., Gao, Y. "Hyper-KGGen: A Skill-Driven Knowledge Extractor for High-Quality Knowledge Hypergraph Generation." KDD '26 (32nd ACM SIGKDD, Jeju Island, 9–13 August 2026), DOI 10.1145/3770855.3818198; arXiv:2602.19543, v1 23 Feb 2026, v2 5 July 2026, CC BY 4.0. Full v2 HTML read 2026-09-21 (Sections 1–6, Tables 1–6, Appendices A–C). https://arxiv.org/html/2602.19543v2
- Rizrock. Hyper-KGGen repository (`hyper_kggen/schema.py`, `hyper_kggen/prompts.py`, `skill_acquisition/experience.py`, `skill_acquisition/prompts.py`, `skill_acquisition/schema.py`, README). MIT licence; 9 stars; latest commit 2026-06-07. Cloned and inspected 2026-09-21. https://github.com/Rizrock/Hyper-KGGen
- Feng, Y. Hyper-Extract repository (README.md, `hyperextract/types/hypergraph.py`, `hyperextract/types/base.py`, `hyperextract/methods/registry.py`, `hyperextract/templates/presets/`, `hyperextract/utils/template_engine/validator.py`, LICENSE). Apache-2.0; commit `395039e` of 2026-09-20; ~4,000 stars / 458 forks. Cloned and inspected 2026-09-21. https://github.com/yifanfeng97/hyper-extract
- PyPI. `hyperextract` 0.10.3, Apache-2.0, uploaded 2026-09-20; 19 releases. Checked 2026-09-21. https://pypi.org/project/hyperextract/
- PyPI. `ontomem` 0.6.0, Apache-2.0, "a self-consolidating memory layer for AI agents with schema-first design, intelligent merging, and hybrid search capabilities" — the merge/identity layer under Hyper-Extract. Checked 2026-09-21. https://pypi.org/project/ontomem/
- Zhang, H., Si, J., Yan, G., Qi, B., Cai, P., Mao, S., Wang, D., Shi, B. "RAKG: Document-level Retrieval Augmented Knowledge Graph Construction." arXiv:2504.09823, 14 April 2025. https://arxiv.org/abs/2504.09823
- Khrouf, H., Fillastre, P., Correia, S. "Optimizing Hypergraph-Based RAG: Toward Better Fact Extraction and Chunk Retrieval." APIA 2026 / arXiv:2607.20506, 2 July 2026. https://arxiv.org/abs/2607.20506
- Tan, Q., Xu, L., Bing, L., Ng, H. T., Aljunied, S. M. "Revisiting DocRED — Addressing the False Negative Problem in Relation Extraction." EMNLP 2022 / arXiv:2205.12696. Upstream corpus of HyperDocRED, as cited by Huang et al. `[unverified]` licence terms for redistribution. https://arxiv.org/abs/2205.12696
- Lairgi, Y., Moncla, L., Cazabet, R., Benabdeslem, K., Cléau, P. "iText2KG: Incremental Knowledge Graphs Construction Using Large Language Models." WISE 2024 / arXiv:2409.03284. https://arxiv.org/abs/2409.03284
- Chen, S., Xu, Y., Han, X., Xue, R., Wu, D., Gao, Y., Yan, C., Gao, Y. "Hypergraph-based Multimodal Retrieval-Augmented Generation with Incremental Refinement." ACM MM 2026 / arXiv:2608.16628. https://arxiv.org/abs/2608.16628
- Searches for 2026 work on consistent incremental knowledge-hypergraph extraction (WebSearch, three queries on entity forking, arity conflict and incremental consistency), run 2026-09-21: no paper found that proposes or claims consistency guarantees for incremental KHG extraction.
