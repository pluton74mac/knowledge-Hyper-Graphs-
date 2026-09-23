---
title: Prior art for the C5 scorers (extraction, completion, retrieval, memory) and the question-set shapes they need
type: survey
status: draft
tags: [p2, c5, scorers, evaluation, extraction, completion, retrieval, memory, question-sets, calibration, stability, supersession]
created: 2026-09-23
updated: 2026-09-23
---

# Prior art for the C5 scorers and the question sets P3a must fill (P2 research report 05)

Contract **C5** is four scorers: extraction, completion, retrieval and memory. P2 owns it, and P3a fills
the question sets it reads (PLAN §7). This report surveys how each of the four abilities is scored in the
literature. For each one it fixes what C5 must define: the metric formulas, the inputs the scorer needs
(and so the shape of the records and question-set items), recommended defaults, and known pitfalls. It
closes each section with a proposed JSON shape and a list of unit-test cases whose expected values can be
computed by hand.

The requirements already written for C5 in report 01 (§5, C5-R01 to C5-R25, and decision D-21) are the
starting point. This report does not repeat them. It adds what the literature and the reference code
actually do, and where they disagree.

## 0. How to read this report

**Evidence labels.**

- **Verified 2026-09-23**: I read it today in the primary source (paper PDF, evaluation script at a named
  commit, or dataset file). Code-level facts cite the file and commit.
- **KB**: stated in a KB note, which carries its own primary sources.
- **Derived**: my inference from verified material. It is not stated as such in the source.
- **Recommendation**: a proposal for the design stage. It is not an established result.
- `[unverified]`: I could not check it.

**Key-to-path table** (KB notes cited by key):

| Key | Path |
|---|---|
| BEP | `kb/05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md` |
| RNP | `kb/05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md` |
| XAI | `kb/05-query-embeddings-reasoning/explainability-and-uncertainty.md` |
| EVC | `kb/03-construction/evaluation-of-constructed-khgs.md` |
| NXT | `kb/03-construction/n-ary-relation-extraction-from-text.md` |
| SKL | `kb/03-construction/skill-driven-extraction-and-the-scenario-gap.md` |
| RAG | `kb/07-applications/retrieval-augmented-generation.md` |
| CRH | `kb/10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md` |
| TMP | `kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md` |
| AGT | `kb/07-applications/ai-agents-memory-and-planning.md` |
| CST | `kb/08-history-and-frontier/composed-stack-and-research-bets.md` |
| LIM | `kb/10-comparative-and-critique/limitations-and-failure-modes.md` |
| SCH | `kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md` |
| R01 | `projects/p2-role-aware-hif/research/01-requirements-from-kb.md` (C5-R*, D-*) |
| R04 | `projects/p2-role-aware-hif/research/04-prior-art-modelling.md` (M5 status lifecycle) |

**JSON examples** use illustrative values. Where a value comes from a unit test, it is that test's
expected value; the rest are placeholders, not results.

**Probe.** Every expected value in the unit-test tables was computed by hand and then recomputed by
[probes/scorers/c5_reference_cases.py](probes/scorers/c5_reference_cases.py) (standard library only,
deterministic). Its output is [probes/scorers/c5_reference_cases.out.json](probes/scorers/c5_reference_cases.out.json).
The probe is a check on the arithmetic, not the C5 implementation.

**Notation.** A fact (hyperedge) is `f = (r, B)`: relation type `r` and a set `B` of bindings `(ρ, v)`,
where `ρ` is a role and `v` a canonical value (entity id, typed literal, hyperedge id), as in R01 C1-R06
and C1-R12. `vals(f)` is the multiset of values of `f`. `|f|` is its arity under the C1 definition (R01
D-06). For precision, recall and F1: `P = TP/|pred|`, `R = TP/|gold|`, `F1 = 2PR/(P+R)`.

---

## Summary of findings

1. **No scorer in the n-ary literature measures what the P9 gate asks for.** Supervised n-ary
   extraction is scored by strict whole-fact match ([Chia et al., 2022](https://arxiv.org/abs/2211.10018);
   [Luo et al., 2024](https://arxiv.org/abs/2310.05185)). LLM hypergraph extraction is scored by soft
   description matching that ignores the participant set (SKL §5; verified in
   [Huang et al., 2026](https://arxiv.org/abs/2602.19543) §5.1.3). Neither reports role accuracy. The
   machinery for role accuracy exists in event extraction (argument *identification* versus
   *classification*, [Li, Ji and Huang, 2013](https://aclanthology.org/P13-1008/)). The machinery for
   partial credit across arity exists in template filling (MUC-4 slot scoring,
   [Chinchor, 1992](https://aclanthology.org/M92-1002/)) and in the matching framework of
   [Chen et al., 2023](https://arxiv.org/abs/2310.13793). C5 has to assemble them.
2. **The unit of a "fact" differs between the two main n-ary extraction benchmarks.** HyperRED scores
   quintuplets `(head, relation, tail, qualifier, value)`, so a statement with *k* qualifiers counts *k*
   times (verified in the paper §4.1 and in `scoring.py`). Text2NKG merges quintuplets into one fact per
   main triple before comparing. The two "strict F1" numbers are not the same measurement.
3. **Reference scorers count duplicates and compare serialisations.** HyperRED's scorer counts every equal
   (prediction, gold) pair in a nested loop over lists. A duplicated prediction is therefore counted
   twice (the probe reproduces recall 2.0). Text2NKG compares facts as JSON strings, which depend on key
   and list order (verified in code, §2.1.1 and §2.5). C5 must deduplicate by content key and match 1:1.
4. **Tie handling differs across the three n-ary codebases, and it changes numbers.** HypE and HYPER count
   ties against the target (pessimistic rank). StarE breaks ties by sort order. PyKEEN defaults to the
   realistic rank. [Sun et al., 2020](https://aclanthology.org/2020.acl-main.489/) show reported MRR
   falling from 0.396 to 0.243 (ConvKB) once ties are broken at random. C5 needs a declared rank
   convention plus presets that reproduce each original (§3.1.3).
5. **"Realistic rank" is not the expected reciprocal rank.** With a four-way tie at the top, `1/realistic`
   gives RR 0.4 and Hits@1 = 0. The exact expectation under random tie-breaking is RR 25/48 ≈ 0.521 and
   Hits@1 = 0.25 (unit test C3). PyKEEN computes MRR and Hits@k from realistic ranks (verified in code).
6. **Filtering is under-specified for qualifiers and for time.** The standard filter removes only
   corruptions that exactly match a known fact. Two published refinements change it. Time-aware
   filtering ([Han et al., 2021](https://arxiv.org/abs/2012.15537)) is used by the n-ary temporal
   extrapolation line, with a point-timestamp rule ([Hou et al., 2025](https://arxiv.org/abs/2505.12788)
   §5.1). The qualifier-monotonicity entailment of [Xiong et al., 2023](https://aclanthology.org/2023.acl-long.743/)
   implies that a known fact with a superset of qualifiers also answers the query. No n-ary filter that
   applies it was found [bounded search], and no filter handles validity *intervals*.
7. **No calibration study of n-ary link predictors exists** (XAI §3; re-searched 2026-09-23). The binary
   precedents disagree on what the probability is about. [Tabacof and Costabello, 2020](https://arxiv.org/abs/1912.10000)
   calibrate per triple and require a stated base rate. [Safavi et al., 2020](https://arxiv.org/abs/2004.01168)
   calibrate top-1 predictions with 10-bin ECE. C5 must choose, and the choice decides what "calibration
   by arity" means for P3b.
8. **Retrieval evaluation with alternative support sets has a precedent, and one of its metrics misleads.**
   KILT treats each gold provenance set as one rank position and gates answer credit on finding a complete
   set ([Petroni et al., 2021](https://arxiv.org/abs/2009.02252)). Its recall@k divides by the number of
   *alternative* sets, so finding one of two sufficient sets scores 0.5 (unit test R2).
9. **The benchmark P4 must run is not self-describing.** Two different benchmarks are called
   GraphRAG-Bench ([Xiang et al., ICLR 2026](https://arxiv.org/abs/2506.05690);
   [Xiao et al., 2025](https://arxiv.org/abs/2506.02404)). In Xiang et al.'s code, answer accuracy is
   0.75 × an LLM-judged statement F1 plus 0.25 × `(cos+1)/2`. The paper states plain cosine. Evidence
   recall is also LLM-judged, and failed judgements are dropped by `nanmean` (verified in code, §4.1.4).
10. **The agent-memory benchmarks that test supersession do not penalise hedged answers.** LongMemEval
    has 78 knowledge-update questions in the cleaned release (counted 2026-09-23). Its GPT-4o judge
    accepts "previous information along with an updated answer" (`evaluate_qa.py`), and its gold record
    stores only the new value, so a stale answer cannot be detected without the judge. MemoryAgentBench's
    FactConsolidation scores by character-substring match, which any answer that mentions the new value
    passes. EvolvingQA scores the prediction against the OUTDATED answer as well as the UPDATED one
    ([Kim et al., 2024](https://aclanthology.org/2024.naacl-long.302/)). That is the deterministic design
    C5 should copy.
11. **LoCoMo has no knowledge-update category, and its numeric category ids do not follow the order of
    its paper.** LongMemEval's comparison table marks LoCoMo as lacking KU. In the released data, id 1 is
    multi-hop (95 % of its questions have evidence in more than one session) and id 4 is single-hop,
    whereas the paper's numbered list starts with single-hop, then multi-hop (profiled 2026-09-23,
    §5.1.2). The released data is CC BY-NC 4.0.
12. **Stability has two published operationalisations and no order-sensitivity metric.** ATOM reports the
    Jaccard similarity of each run against run 1, with 0.552 for atomic-fact input against 0.212 for
    paragraphs ([Lairgi et al., 2026](https://arxiv.org/abs/2510.22590)). Hyper-KGGen partitions *gold*
    relations by how many of K runs recover them (SKL §4). No published metric for insertion-order
    sensitivity of KG extraction was found [bounded search].

---

## 1. Conventions shared by all four scorers

These are the choices that, left implicit, make two numbers from the same scorer incomparable. Each is a
**Recommendation** unless it cites a source.

1. **Deterministic by default.** No scorer calls an LLM. An LLM-judged metric is an adapter with a named
   judge, a pinned prompt and temperature, and a reported agreement sample (R01 C5-R05). LongMemEval and
   Mem0 are the precedents: a named judge at temperature 0, and repeated judge runs with dispersion
   ([Chhikara et al., 2025](https://arxiv.org/abs/2504.19413) §3.2 report 10 judge runs, mean ± 1 sd).
2. **Canonical values, not strings.** Entities match by canonical id. Literals match by typed comparison
   (§2.2.1). Strings enter only in answer-text metrics (§4), through SQuAD normalisation
   ([Rajpurkar et al., 2016](https://arxiv.org/abs/1606.05250) §6.1).
3. **Empty-set conventions, written down.** `|pred| = 0` gives P = 0 with a `no_predictions` flag, as in
   HotpotQA's `update_sp`. `|gold| = 0` gives R = 0 with a `no_gold` flag. `|pred| = |gold| = 0` gives
   P = R = F1 = 1 with a `both_empty` flag. HotpotQA's script instead gives EM = 1 but P = R = 0 in that
   case (verified, `hotpot_evaluate_v1.py`), so the convention must be stated. Micro-averaged corpus
   scores are unaffected, because empty documents add nothing to any count.
4. **Three averages, never one.** Micro over the scoring units, macro over relation types (as GenIE,
   [Josifoski et al., 2022](https://aclanthology.org/2022.naacl-main.342/) App. C), and macro over arity
   bins {2, 3, 4, ≥5} (R01 C5-R02). Name the denominator in the output key.
5. **Arity-stratified precision and recall need different arities.** Recall is stratified by *gold* arity
   and precision by *predicted* arity. When they differ, an aligned pair contributes to recall in the
   gold bin and to precision in the predicted bin (**Derived**; no source stratifies extraction by arity,
   EVC §7).
6. **Per-item outputs keyed by stable ids,** each listing the gold hyperedge ids it depends on, so P8 can
   join the four abilities per fact (R01 C5-R03; **Recommendation** on the join key).
7. **Dispersion.** Report K ≥ 3 runs where the system is stochastic, plus a percentile bootstrap over
   scoring units (documents, queries, questions) with a fixed seed. Use the paired bootstrap for system
   comparisons ([Koehn, 2004](https://aclanthology.org/W04-3250/)). GenIE reports a 1-sd interval from
   50 bootstrap samples. **Recommendation:** 1,000 resamples, 95 % percentile interval.
8. **Version stamps** on every output: C1 schema id, C5 version, C4 corpus and question-set versions,
   split, and the scorer configuration (R01 C5-R01).

---

## 2. Extraction (and extraction stability)

### 2.1 What the literature does

#### 2.1.1 Strict whole-fact matching (the n-ary benchmarks)

- **HyperRED** (Verified 2026-09-23, arXiv:2211.10018 §4.1): "For a predicted hyper-relational fact to be
  considered correct, the whole fact f = (e_head, r, e_tail, q, e_value) must match the ground-truth fact
  in terms of relation label, qualifier label and entity bounds". The metric is micro F1. The fact is
  defined with **one** qualifier (§2.1, "Hyper-Relational Alignment"). The scorer's `QuintupletScorer`
  emits one tuple per qualifier of a relation (`scoring.py`, commit `17ba7b6`, 2022-12-13). A Wikidata
  statement with three qualifiers is therefore three scoring units. CubeRE also reports a triplet-only
  score (71.01 F1 against 66.75 full; EVC §1).
- **Text2NKG** (NXT §5; code verified): "the entire fact must match the ground facts completely". In
  `run_re.py` (commit `f538a99`, 2025-08-18), `compaction` merges predicted quintuplets that share
  relation, subject and object into one fact. `statistic` then compares facts as `json.dumps` strings
  and records arity histograms of predictions and gold (`N_of_pred_comp`, `N_of_ans_comp`).
- **Closed IE over KB identifiers** (GenIE, Verified, App. C): "A fact is regarded as correct if the
  relation and the two corresponding entities are all correct". Micro scores sum `|P_d ∩ G_d|` over
  documents. Macro scores are aggregated per relation type. This is the canonical-id analogue of strict
  F1, and the right template for scoring Wikidata-linked output.
- **Leak-aware variant.** DocRED reports "Ign F1", which excludes "relational facts shared by the training
  and dev/test sets" ([Yao et al., 2019](https://aclanthology.org/P19-1074/) §5, Verified).

#### 2.1.2 Partial credit and arity mismatch

- **MUC-4** (Verified, page image of [Chinchor, 1992](https://aclanthology.org/M92-1002/), Tables 1–2).
  Each slot fill is classed correct (COR), partial (PAR), incorrect (INC), missing (MIS), spurious (SPU)
  or non-committal. POS = COR + PAR + INC + MIS and ACT = COR + PAR + INC + SPU. Then
  `recall = (COR + 0.5·PAR)/POS`, `precision = (COR + 0.5·PAR)/ACT` and `over-generation = SPU/ACT`.
  This is slot-level credit after templates are aligned, which is exactly how an arity-3 prediction of an
  arity-4 gold fact should earn 3 of 4.
- **The unified matching view** (Verified, [Chen et al., 2023](https://arxiv.org/abs/2310.13793) §2–§3,
  §6). A metric is a normalised score over a constrained optimal matching of substructures. The
  constraint is 1:1 (Hungarian), N:1, 1:N or N:N, and the normalisation is P, R, F or Jaccard. Their
  rendering of the SciREX n-ary metric is `F↔_relations[⟦F↔_args[φ_RFE] = 1⟧]`, all arguments or
  nothing. Role-filler
  entity extraction (CEAF-REE) is `F↔_args[δ_role × φ_⊆]`, and the authors call its entity similarity
  "unduly harsh". SMATCH handles unlinked variables by maximising over 1:1 variable mappings. The
  reference library `metametric` has **no licence file and no licence metadata** (commit `532afe5`,
  2025-11-03; PyPI 0.2.1 lists none, checked 2026-09-23), so C5 cannot depend on it.
- **SciREX** (Verified, [Jain et al., 2020](https://aclanthology.org/2020.acl-main.670/) §5.1). Predicted
  clusters map to gold clusters when `|P∩G|/|P| > 0.5`. Mentions match when their Jaccard exceeds 0.5.
  4-ary relations are scored all-or-nothing under that mapping. SciREX also reports binary F1 by
  "splitting each 4-ary relation into six binary ones". That is a published **pairwise-projection** form
  of partial credit.
- **Soft matching for open descriptions** (Verified, [Huang et al., 2026](https://arxiv.org/abs/2602.19543)
  §5.1.3 and §5.3.1). Descriptions are embedded with all-MiniLM-L6-v2, then a cosine matrix and "the
  Hungarian algorithm to find the optimal global matching", with thresholds 0.65, 0.70 and 0.75 in a
  sensitivity study. The participant set does not enter the match (SKL §5 caution 1). EVC §2 recommends
  adding a participant-set Jaccard term, and no published metric does.
- **The KB's open problem stands.** "No shared metric handles partial credit for hyperedges that differ
  in arity from the gold fact" (NXT, open problems). What exists is general-purpose machinery (MUC slot
  scoring, Chen et al.'s framework, SciREX's pairwise split) that no n-ary KG benchmark applies.

#### 2.1.3 Role identification versus role classification (the ACE conventions)

- **Standard criteria** (Verified, [Li, Ji and Huang, 2013](https://aclanthology.org/P13-1008/) §4.1,
  following Ji and Grishman 2008): "An argument is correctly identified if its event subtype and offsets
  match those of any of the reference argument mentions. An argument is correctly identified and
  classified if its event subtype, offsets and argument role match". The two are reported as Arg-I and
  Arg-C ([Li, Ji and Han, 2021](https://aclanthology.org/2021.naacl-main.69/), tables).
- **Mention granularity changes the number.** WikiEvents reports **Head F1** and **Coref F1** ("full credit
  if the extracted argument is coreferential with the gold-standard argument"). It adds *informative*
  argument extraction, because pronoun fillers are useless for KB construction (Li, Ji and Han 2021 §3.1,
  Verified).
- **Evaluation pitfalls in event extraction**, quantified (Verified,
  [Peng et al., 2023](https://arxiv.org/abs/2306.06918) §3). Three preprocessing scripts of ACE 2005
  differ in head versus full mentions, multi-token triggers, time and value expressions, and pronouns;
  63 % of the surveyed papers do not say which they used. Swapping the script changed one model's EAE F1
  by 15.2 points (PAIE, Table 4). Three "unclear mappings" arise from span overlap, multiple predictions
  for one gold span, and generated strings without positions for non-unique spans. Standardising outputs
  moved scores by up to +2.8 ED precision and −3.5 EAE recall (Table 5). Evaluating argument extraction
  with gold triggers hides pipeline error.
- **Strict versus Boundaries in end-to-end RE** (Verified,
  [Taillé et al., 2020](https://aclanthology.org/2020.emnlp-main.301/) §3–§5). Scoring without entity
  type (Boundaries) and comparing against Strict results overestimates ACE05 by 2.5 to 3 F1.

#### 2.1.4 Matching entity mentions to canonical ids

- **Entity-level scoring with gold clusters.** DocRED's facts are over entity ids, and "Each named entity
  mention is associated with a Wikidata item candidate set" (NXT §4).
- **Name ambiguity breaks string matching.** 2WikiMultiHopQA scores evidence triples; human evidence F1
  was 78.8 against the model's 16.7. The authors attribute the low scores to "the ambiguity in the names
  of Wikidata ... We use only one name in the ground truth, while the workers can use other names"
  (Verified, [Ho et al., 2020](https://aclanthology.org/2020.coling-main.580/) §5.3).
- **Fact synsets.** BenchIE's gold "consists of fact synsets, clusters in which we exhaustively list all
  acceptable surface forms of the same fact", and existing OIE systems come out "significantly less
  effective than indicated by existing OIE benchmarks"
  ([Gashteovski et al., 2022](https://aclanthology.org/2022.acl-long.307/), abstract, Verified).
- **Unlinked predicted nodes** can be scored by an optimal 1:1 mapping of variables, as SMATCH does
  (Chen et al. 2023 §4). The general problem is a search, not an assignment. **Derived.**

#### 2.1.5 Stability across runs and insertion orders

- **ATOM** (Verified, [Lairgi et al., 2026](https://arxiv.org/abs/2510.22590) §4.1–§4.4). Stability is
  `S_r = |s(1) ∩ s(r)| / |s(1) ∪ s(r)|` over the 5-tuple sets of run 1 and run r, for r = 2, 3. The
  anchor is run 1, not all pairs. With gpt-4.1-2025-04-14, Run 2 scored 0.552 ± 0.124 on atomic facts
  and 0.212 ± 0.181 on lead paragraphs (Table 1).
- **Hyper-KGGen.** K rollouts at non-zero temperature. *Gold* relations are partitioned into Stable
  (recovered in all K), Unstable (some) and Miss (none). This is stability relative to gold, not
  self-consistency (SKL §4).
- **Churn.** "The churn between two models [is] the expected percent of diffs sampled from the test
  distribution" (Verified, [Milani Fard et al., 2016](https://proceedings.neurips.cc/paper/2016/hash/dc5c768b5dc76a084531934b34601977-Abstract.html) §1.2).
- **Determinism at temperature 0 is not guaranteed.** Five LLMs "configured to be deterministic" varied
  in accuracy by up to 15 % across 10 runs. The authors define TARr@N (agreement of raw outputs) and
  TARa@N (agreement of parsed answers) ([Atil et al., 2024/2025](https://arxiv.org/abs/2408.04667),
  abstract, Verified).
- **Insertion order.** No paper measuring the order sensitivity of KG or hypergraph extraction was found
  (web search 2026-09-23). SKL §8 records the same absence for consistency guarantees.

### 2.2 Metric definitions for the C5 extraction scorer (Recommendation)

Inputs per document `d`: gold facts `G_d` and predicted facts `P_d`, both canonicalised under C1 (entity
ids, typed literals, role ids) and deduplicated by full content key. The number of duplicates removed is
reported. All scores are micro over documents unless stated.

| Id | Metric | Definition |
|---|---|---|
| E-M1 | **Strict fact P/R/F1** | `TP_d = |P_d ∩ G_d|` under fact equality: same relation and equal binding sets, with literal equality per §2.2.1 and any listed gold alternative accepted. `P = ΣTP_d/Σ|P_d|`, `R = ΣTP_d/Σ|G_d|`. |
| E-M2 | **Core (key-role) P/R/F1** | Replace each fact by `core(f) = (r, {(ρ,v) ∈ B : ρ ∈ K(r)})`, where `K(r)` is the declared key or core role set (R01 C1-R17, C1-R28). Then apply E-M1 to the sets of cores. This is the analogue of HyperRED's triplet-only and StarE's subject/object view. |
| E-M3 | **Fact alignment** | One 1:1 alignment `A_d ⊆ P_d × G_d` per document. It maximises `Σ_{(p,g)∈A_d} w(p,g)` with `w = 0` when `r_p ≠ r_g`, else `w = (N+1)·ν(p,g) + β(p,g)`. Here `ν = |vals(p) ⊓ vals(g)|` (multiset intersection: shared values, role ignored), `β = |B_p ∩ B_g|` (shared role-value bindings) and `N` = maximum arity. Solved with the Hungarian algorithm, ties broken by lexicographic fact ids. |
| E-M4 | **Argument identification (Arg-I)** | `TP_I = Σ_{A_d} ν(p,g)`, `P_I = ΣTP_I / Σ_p |B_p|`, `R_I = ΣTP_I / Σ_g |B_g|`. |
| E-M5 | **Argument classification (Arg-C) = binding F1** | `TP_C = Σ_{A_d} β(p,g)`, with P and R as in E-M4. It handles arity mismatch: an arity-3 prediction that is a subset of an arity-4 gold fact gives P = 1, R = 0.75. |
| E-M6 | **Role accuracy** | `RA = ΣTP_C / ΣTP_I`: of the participants found in the right fact, the share given the right role. This is the P9 gate's "role accuracy" (R01 C5-R08) made unambiguous. |
| E-M7 | **Pooled bindings and grouping gap** | `U(X) = {(r, ρ, v)}` pooled over a document. P/R/F1 are computed on `U(P_d)` against `U(G_d)`. `grouping_gap = F1_pooled − F1_ArgC` measures participants found but grouped into the wrong fact (LIM §8, "Measure grouping accuracy"). |
| E-M8 | **Pairwise projection F1** | `π(f) = {(r, b_i, b_j) : b_i < b_j ∈ B_f}`, the role-typed pairs. P/R/F1 are computed over `∪π`. This is SciREX's split generalised, and gives partial credit for arity mismatch that is comparable with binary extractors. |
| E-M9 | **Participant-set match** | `vals(p) = vals(g)`, with relation and roles ignored. Also mean Jaccard over the alignment. It scores role-free extractors (HyperGraphRAG-style) on the same data. |
| E-M10 | **Arity profile** | Histograms of predicted and gold arity; count of aligned pairs by (predicted arity, gold arity); per-bin P (by predicted arity) and R (by gold arity). |
| E-M11 | **Ign variant** | E-M1 to E-M6 recomputed after removing gold facts, and matching predictions, whose core key is in a declared `seen` set (few-shot exemplars, skill-acquisition seeds). This follows DocRED's Ign F1. |
| E-M12 | **Soft F1** (optional, off by default) | Hungarian matching on `s(p,g) = λ·cos(desc_p, desc_g) + (1−λ)·J(vals(p), vals(g))` with threshold τ. The embedding model and its version are pinned. It is reported beside, never instead of, E-M1. |

#### 2.2.1 Literal and entity equality (Recommendation)

- **Dates** use Wikidata precision codes: "9 - year, 10 - month, 11 - day"
  ([Wikibase DataModel](https://www.mediawiki.org/wiki/Wikibase/DataModel), checked 2026-09-23).
  Rule `truncate_to_gold`: a prediction matches when it is at least as precise as the gold value and
  agrees after truncation to the gold precision. A coarser prediction fails. Rule `exact` is available
  for reproduction.
- **Quantities** match when the amount lies within the gold `[lowerBound, upperBound]` if bounds exist,
  and otherwise by exact decimal equality in the same unit. Unit conversion is out of scope for v1.
- **Entities** match by canonical id, or by a declared alias or redirect table (Wikidata merges redirect,
  R04 M5).
- **`somevalue` and `novalue`** match only themselves (R01 C1-R08).

#### 2.2.2 Stability metrics (Recommendation)

Runs `1..K` produce fact-key sets `S_i`, over the whole corpus or per document with the per-document
results averaged. Everything is computed twice: on the full content key and on the core key.

| Id | Metric | Definition |
|---|---|---|
| S-M1 | Mean pairwise Jaccard | `J(i,j) = |S_i ∩ S_j| / |S_i ∪ S_j|` (1 if both empty); mean over all `C(K,2)` pairs. ATOM's run-1 anchor is a special case, reported only for comparison. |
| S-M2 | Core ratio | `|∩_i S_i| / |∪_i S_i|` |
| S-M3 | Support histogram, unstable fraction | `s_k` = number of runs containing fact k; histogram of `s_k`; share of facts with `0 < s_k < K`. |
| S-M4 | Fact churn (per-fact flip rate) | `δ_k = s_k (K − s_k) / C(K,2)`: the probability that two distinct random runs disagree on k. Report the mean over `∪S_i` and the histogram. |
| S-M5 | Gold-conditioned partition | Share of gold facts matched (E-M1 or E-M2) in all, some or none of the K runs, as in Hyper-KGGen. |
| S-M6 | Score dispersion | Mean, sd, minimum and maximum over runs of E-M1, E-M5 and E-M6. |
| S-M7 | Order effect | Runs carry `(order_id, seed)`. `J_within` is the mean J over pairs with the same order, `J_between` the mean over pairs with different orders, and `Δ_order = J_within − J_between`. For the P9 design (3 runs × 2 orders) there are 6 within-order and 9 between-order pairs. |

### 2.3 Inputs the extraction scorer needs

From C4 (P3a): documents with gold facts in C1 form. Each carries an **evidence span**, an optional list
of **alternatives**, the **core key**, an **arity** computed by C1's rule, an **exhaustiveness flag**
for the annotation, and optionally a **seen** list of core keys. From the system: C3 candidate records
carrying `run_id`, `order_id`, `seed`, model and version, and the document id. From C1's schema: key and
core role sets per relation, literal datatypes and precisions.

### 2.4 Defaults (Recommendation)

- Report E-M1, E-M2, E-M4, E-M5, E-M6, E-M7 and E-M8 always. E-M9 and E-M11 when requested, E-M12 only
  as an opt-in.
- P9's gate numbers: "precision, recall" = E-M1 (with E-M5 beside it), and "role accuracy" = E-M6.
- Micro over documents as headline, macro over relation types and over arity bins beside it.
- Stability: S-M1, S-M5 and S-M7 on the full content key, with S-M1 also on the core key.

### 2.5 Pitfalls (extraction)

1. **Unit of scoring.** Quintuplets (HyperRED) versus whole facts (Text2NKG) versus bindings. Always name
   it in the output key.
2. **Duplicates and non-1:1 counting.** Nested-loop counting over lists (HyperRED `StrictScorer` and
   `QuintupletScorer`, Text2NKG `statistic`) credits a duplicated correct prediction twice. The probe
   reproduces TP = 2 with one gold fact (unit test E6).
3. **Serialisation equality.** Text2NKG compares `json.dumps` strings. Dict key order follows insertion
   order, so two equal facts whose qualifiers were emitted in different orders compare unequal
   (**Derived** from the code; not measured on data).
4. **Greedy alignment.** It lets one gold fact absorb a better-matching prediction and inflates or
   deflates binding scores (EVC §2). On unit test E8, greedy gives binding F1 0.50 and Hungarian gives
   0.667.
5. **Alignment that uses roles cannot measure role errors.** If facts are aligned by shared (role, value)
   pairs, a prediction with swapped roles aligns to nothing and role accuracy is undefined. The first
   version of the probe failed exactly this way. Hence E-M3's value-first weight.
6. **Gold incompleteness.** False negatives dominate n-ary evaluation, so recall is a lower bound and
   precision is pessimistic wherever true but unannotated facts count as errors. Re-DocRED moved models
   by about 13 F1 (EVC §3). For distant-supervision gold (P3a from Wikidata), split false positives into
   `contradicts_gold` (same key, different value), `in_kb_not_annotated` (true in the KB, absent from
   this document's gold) and `unknown` (**Recommendation**).
7. **Mention and preprocessing conventions.** Boundaries against Strict: 2.5 to 3 F1 on ACE05 (Taillé et
   al.). Switching ACE preprocessing scripts: up to 15.2 EAE F1 (Peng et al., Table 4). C5 avoids this by
   scoring canonical ids. The linking step must then be scored separately, or linking errors become
   extraction errors.
8. **Soft scores measure prose similarity, not participants** (SKL §5). Hyper-KGGen's 0.80 precision
   means that paraphrases matched.
9. **Stability depends on canonicalisation.** A lossy content key under-reports instability, and an
   over-strict one over-reports it. Report both keys.
10. **Temperature 0 is not determinism** (Atil et al.). Record the seed, temperature, model version and
    provider for every run.

### 2.6 JSON shapes (extraction)

Gold document item (P3a fills it, C4 carries it). The value encoding follows SCH §6.2 and R01 C1-R06. The
final record shape is set by the C1 design.

```json
{
  "doc_id": "p3a-doc-000017",
  "split": "test",
  "text": "Albert Einstein received the 1921 Nobel Prize in Physics from the Royal Swedish Academy of Sciences.",
  "text_sha256": "sha256:0f1e...",
  "annotation": {"method": "distant+human", "exhaustive": false, "annotators": 2},
  "gold": [
    {
      "fact_id": "khg:stmt-0001",
      "relation": "award_received",
      "bindings": [
        {"role": "recipient", "value": {"entity": "Q937"}},
        {"role": "award", "value": {"entity": "Q38104"}},
        {"role": "conferrer", "value": {"entity": "Q193592"}},
        {"role": "point_in_time", "value": {"literal": "1921", "datatype": "date", "precision": "year"}}
      ],
      "core_key": "sha256:9a41...",
      "arity": 4,
      "evidence": [{"start": 0, "end": 99}],
      "alternatives": []
    }
  ],
  "entity_aliases": {"Q193592": ["Royal Swedish Academy of Sciences"]},
  "seen_core_keys": []
}
```

Scorer input: configuration plus one prediction file per run.

```json
{
  "config": {
    "match": {"entity": "canonical_id", "literal_rule": "truncate_to_gold", "use_alternatives": true},
    "alignment": {"method": "hungarian", "weight": "value_then_binding", "same_relation": true, "tie_break": "lexicographic_ids"},
    "levels": ["strict", "core", "arg_i", "arg_c", "pooled", "pairwise"],
    "core_roles_from": "schema.key_roles",
    "averaging": ["micro_doc", "macro_relation", "macro_arity"],
    "arity_bins": ["2", "3", "4", "5+"],
    "ign_seen": false,
    "soft": null,
    "stability": {"keys": ["content_key", "core_key"], "gold_conditioned": true},
    "bootstrap": {"unit": "doc", "resamples": 1000, "seed": 0, "ci": 0.95}
  },
  "runs": [
    {
      "run_id": "p9-2026-10-01-a",
      "order_id": "order-A",
      "seed": 13,
      "system": {"name": "extractor-x", "version": "0.3.1", "model": "model-y", "temperature": 0.0},
      "predictions": [
        {
          "doc_id": "p3a-doc-000017",
          "candidate_id": "c3:cand-000981",
          "relation": "award_received",
          "bindings": [
            {"role": "recipient", "value": {"entity": "Q937"}},
            {"role": "award", "value": {"entity": "Q38104"}},
            {"role": "point_in_time", "value": {"literal": "1921", "datatype": "date", "precision": "year"}}
          ],
          "evidence": [{"start": 0, "end": 60}]
        }
      ]
    }
  ]
}
```

Scorer output: the aggregate, then items (abridged).

```json
{
  "c5_version": "0.1.0",
  "scorer": "extraction",
  "versions": {"c1_schema": "khg-record/1.0.0", "c4_corpus": "p3a/1.0.0", "config_sha256": "sha256:77c2..."},
  "aggregate": {
    "strict": {"p": 0.0, "r": 0.0, "f1": 0.0, "tp": 0, "n_pred": 1, "n_gold": 1},
    "core": {"p": 1.0, "r": 1.0, "f1": 1.0},
    "arg_i": {"p": 1.0, "r": 0.75, "f1": 0.857143},
    "arg_c": {"p": 1.0, "r": 0.75, "f1": 0.857143},
    "role_accuracy": 1.0,
    "pooled": {"p": 1.0, "r": 0.75, "f1": 0.857143},
    "grouping_gap_f1": 0.0,
    "pairwise": {"p": 1.0, "r": 0.5, "f1": 0.666667},
    "n_duplicates_removed": 0,
    "fp_breakdown": {"contradicts_gold": 0, "in_kb_not_annotated": 0, "unknown": 0}
  },
  "by_arity": {"4": {"recall_strict_by_gold_arity": 0.0, "recall_arg_c_by_gold_arity": 0.75}, "3": {"precision_strict_by_pred_arity": 0.0, "precision_arg_c_by_pred_arity": 1.0}},
  "stability": {"content_key": {"mean_pairwise_jaccard": 0.666667, "core_ratio": 0.5, "unstable_fraction": 0.5, "mean_fact_churn": 0.333333}, "order_effect": {"J_within": 1.0, "J_between": 0.333333, "delta_order": 0.666667}, "gold_partition": {"stable": 0.333333, "unstable": 0.333333, "miss": 0.333333}},
  "items": [
    {"fact_id": "khg:stmt-0001", "doc_id": "p3a-doc-000017", "gold_arity": 4, "aligned_candidate": "c3:cand-000981", "pred_arity": 3, "strict": false, "arg_i_tp": 3, "arg_c_tp": 3, "runs_matched": 3}
  ]
}
```

### 2.7 Unit tests (extraction and stability)

Relation `r`; roles `A–E`, `Q`; values `a–e`, `q`, `z`. All expected values are recomputed by the probe.

| Test | Gold | Prediction | Expected |
|---|---|---|---|
| E1 perfect | `r(A:a,B:b,C:c,D:d)` | same | strict, Arg-I, Arg-C, pairwise P = R = F1 = 1; RA = 1 |
| E2 no predictions | as E1 | none | all P = R = F1 = 0, flag `no_predictions`; RA undefined (null) |
| E3 both empty | none | none | P = R = F1 = 1, flag `both_empty` |
| E4 arity 3 vs 4 | `r(A:a,B:b,C:c,D:d)`, key roles {A,B} | `r(A:a,B:b,C:c)` | strict F1 = 0; core F1 = 1; Arg-C P = 1, R = 0.75, F1 = 6/7 ≈ 0.857143; pairwise P = 1, R = 3/6 = 0.5, F1 = 2/3 |
| E5 role swap | `r(A:a,B:b)` | `r(A:b,B:a)` | strict 0; Arg-I F1 = 1; Arg-C F1 = 0; RA = 0 |
| E5b partial swap | `r(A:a,B:b,C:c)` | `r(A:b,B:a,C:c)` | Arg-I F1 = 1; Arg-C P = R = 1/3; RA = 1/3; pairwise F1 = 0 |
| E5c wrong relation | `r(A:a,B:b)` | `s(A:a,B:b)` | strict, Arg-I and Arg-C all 0 (no alignment across relations); participant-set match = 1 |
| E6 duplicate | `r(A:a,B:b)` | same, twice | after dedup P = R = 1, `n_duplicates_removed` = 1; nested-loop counting gives TP = 2, R = 2.0 (the pitfall) |
| E7 one prediction, two gold | `r(A:a,B:b,C:c)`, `r(A:a,B:b,C:d)` | `r(A:a,B:b,C:c)` | strict P = 1, R = 0.5, F1 = 2/3; Arg-C P = 1, R = 3/6, F1 = 2/3; pooled P = 1, R = 3/4, F1 = 6/7; grouping gap = 6/7 − 2/3 = 4/21 ≈ 0.190476; pairwise P = 1, R = 3/5, F1 = 0.75 |
| E8 Hungarian vs greedy | `r(A:a,B:b,C:c,E:e)`, `r(A:a,B:b,D:d)` | `r(A:a,B:b,C:c)`, `r(C:c,E:e)` | overlap matrix [[3,2],[2,0]]; Hungarian total 4 gives Arg-C P = 4/5, R = 4/7, F1 = 2/3; greedy total 3 gives P = 3/5, R = 3/7, F1 = 0.5 |
| E9 date precision | `point_in_time` 1921 (year) | 1921-05-02 (day) | `truncate_to_gold` match; `exact` no match; year prediction against day gold: no match |
| E10 core vs strict | `r(A:a,B:b,Q:q)`, key {A,B} | `r(A:a,B:b,Q:z)` | strict 0; core 1; Arg-C P = R = 2/3; pairwise P = R = 1/3 |
| E11 per-arity recall | `r2(A:a,B:b)`, `r4(A:a,B:b,C:c,D:d)` | `r2(A:a,B:b)` | micro R = 0.5; R(arity 2) = 1; R(arity 4) = 0; macro-over-arity R = 0.5 |
| S1 three runs | — | `{a,b,c}`, `{a,b,d}`, `{a,b,c}` | pairwise J = 0.5, 1, 0.5, mean 2/3; core ratio 2/4 = 0.5; support {a:3, b:3, c:2, d:1}; unstable fraction 0.5; mean churn (0 + 0 + 2/3 + 2/3)/4 = 1/3 |
| S2 all empty | — | ∅, ∅, ∅ | mean J = 1 by convention, flagged; churn 0 |
| S3 order effect | — | order O1: `{a,b}` × 3 runs; O2: `{a,c}` × 3 runs | 6 within pairs, J = 1; 9 between pairs, J = 1/3; Δ_order = 2/3 |
| S4 gold partition | g1, g2, g3 | matched per run: `{g1,g2}`, `{g1}`, `{g1}` | stable 1/3, unstable 1/3, miss 1/3 |

---

## 3. Completion (n-ary link prediction)

### 3.1 What the literature does

#### 3.1.1 Filtered ranking

- **Origin** (Verified, [Bordes et al., 2013](https://papers.nips.cc/paper_files/paper/2013/hash/1cecc7a77928ca8133fa24680a88d2f9-Abstract.html) §4.2):
  "we propose to remove from the list of corrupted triplets all the triplets that appear either in the
  training, validation or test set (except the test triplet of interest)". MRR and Hits@K are defined in
  BEP §2.
- **HypE** (code verified, `tester.py`, ServiceNow/HypE commit `2fecf70`, 2022-07-15). For each test tuple
  and each position `j ≤ arity`, the corruptions `(r, …, i, …)` for every entity `i` are built. With
  `fil`, `set(queries) - self.all_facts_as_set_of_tuples` removes every corruption that equals a known
  7-tuple (relation plus six padded positions). The normalizer adds one per (fact, position), so the
  average is **per prediction task**, as BEP §1 states. Per-arity evaluation exists (`test_by_arity`).
- **StarE** (code verified, `loops/evaluation.py`, commit `b294b9e`, 2023-12-01). The filter index is
  keyed on `(s, r, *quals)` when qualifiers are on, so an object is filtered only when a known statement
  has the same subject, relation and the same *ordered* qualifier sequence. Subject and object prediction
  are computed separately and averaged. The paper says the same (§5, Verified): "The metrics are computed
  for subject and object prediction separately and are then averaged". For WD50K the candidate universe
  excludes entities that never occur in a subject or object position (`ENT_POS_FILTERED`,
  `gather_missing_entities`). It is off for JF17K and WikiPeople (`run.py`).
- **HYPER** (code verified, `hyper/tasks.py`, commit `14697d8`, 2026-03-25). `strict_negative_mask` masks
  every known hyperedge that agrees with the query on the other `k−1` positions and the relation.
  Filtered rank is `sum((pos_pred <= pred) & mask) + 1`. The paper states the all-positions protocol
  (BEP §1).
- **Which positions are predicted** (Verified, [Wang et al., 2021](https://arxiv.org/abs/2105.08476)
  §4.4 and Table 2). GRAN reports two settings, "predicting all entities s, o, v1, …, vm" and "predicting
  only the subject s and object o". On JF17K, GRAN-hete scores MRR 0.656 on all entities and 0.617 on
  subject/object. The two numbers are different tasks (BEP §5 pitfall 1).

#### 3.1.2 Filtering refinements: time and qualifiers

- **Time-aware filtering** (Verified, [Han et al., 2021](https://arxiv.org/abs/2012.15537) §5): "The
  time-aware filtering scheme only filters out triples that are genuine at the query time while the
  filtering scheme applied in prior work ... filters all triples that occurred in history". The same
  paper found that one baseline's code "does not perform subject prediction". The n-ary temporal line
  adopted it: MT-Path, "Following Hou et al. (2023), ... perform[s] time-aware filtering where only the
  facts occurring at the same timestamp as the query are filtered" (Verified,
  [Hou et al., 2025](https://arxiv.org/abs/2505.12788) §5.1). HypeTKG instead follows "the filtering
  setting used in previous HKG reasoning works (Galkin et al., 2020)" (Verified,
  [Ding et al., 2024](https://arxiv.org/abs/2307.10219) §5.1). For queries with an as-of time, answers
  valid at another time are wrong, not filterable. With validity *intervals* (Wikidata start and end
  qualifiers), "valid at the query time" replaces "same timestamp" (**Derived**).
- **Qualifier monotonicity** (Verified, [Xiong et al., 2023](https://aclanthology.org/2023.acl-long.743/)
  §3, Definition 3): for queries that share the primal triple with `Q1 ⊆ Q2`, "QA(q2; KG) ⊆ QA(q1; KG)".
  "If a fact is true, then all its partial facts must also be true". It may fail for "semantically opaque
  contexts" (§8). Consequence (**Derived**): under monotonicity, a known fact `(h, r, x, Q')` with
  `Q' ⊇ Q` also answers the query `(h, r, ?, Q)`. The exact-match filters of HypE, StarE and HYPER do not
  remove such `x`, so they count true answers as errors.

#### 3.1.3 Tie handling

- **Protocols** (Verified, [Sun et al., 2020](https://arxiv.org/abs/1911.03903) §4): TOP ("the correct
  triplet is inserted in the beginning"), BOTTOM (at the end) and RANDOM. "RANDOM is the best evaluation
  technique which is both rigorous and fair". On FB15k-237, reported MRR against RANDOM MRR was 0.396 →
  0.243 for ConvKB, 0.523 → 0.150 for CapsE and 0.518 → 0.157 for KBAT (the last after a leakage fix;
  Table 2).
- **Rank taxonomy** (Verified, [Berrendorf et al., 2020](https://arxiv.org/abs/2002.06914) §3).
  Optimistic `rank⁺ = |{β > α}| + 1`, pessimistic `rank⁻ = |{β ≥ α}|` (the candidate set includes the
  target), non-deterministic (sort-order dependent), and realistic `(rank⁺ + rank⁻)/2`, "the average over
  all valid ranks". The authors recommend realistic because random ranks "are not always reproducible".
- **PyKEEN** (code verified, commit `fb81ffe`, version 1.11.2-dev). Default rank type is realistic
  (`normalize_rank_type(None)`). MRR is `mean(1/rank)` and Hits@k is `mean(rank ≤ k)`, both applied to the
  realistic rank. Adjusted metrics normalise by the expectation under random scoring:
  `E[1/r] = H(C)/C`, `E[Hits@k] = min(k/C, 1)`, reindexed `(M − E[M])/(1 − E[M])`, and AMR `= MR/E[MR]`
  ([Hoyt et al., 2022](https://arxiv.org/abs/2203.07544)).
- **What the n-ary codebases do** (code verified above). HypE: `(sim_scores >= sim_scores[0]).sum()`, so
  pessimistic. HYPER filtered branch: pessimistic. StarE:
  `1 + argsort(argsort(pred, descending=True))[obj]`, so non-deterministic in Berrendorf's taxonomy.

#### 3.1.4 Calibration

- **ECE** (Verified, [Guo et al., 2017](https://arxiv.org/abs/1706.04599) §2). Predictions are grouped
  into M bins `I_m = ((m−1)/M, m/M]`, and
  `ECE = Σ_m (|B_m|/n)·|acc(B_m) − conf(B_m)|` ([Naeini et al., 2015](https://ojs.aaai.org/index.php/AAAI/article/view/9602)).
  Tables use M = 15.
- **ECE's flaws** (Verified, [Nixon et al., 2019](https://arxiv.org/abs/1904.01685), abstract): "the rank
  ordering of recalibration methods is drastically impacted by the choice of calibration measure". The
  authors recommend class-conditioning, the L2 norm and adaptive bins.
- **KG embeddings, per triple** (Verified, [Tabacof and Costabello, 2020](https://arxiv.org/abs/1912.10000)
  §3–§5, App. A.1): Brier `B = (1/n)Σ(y_i − p̂_i)²`, log loss, reliability diagrams, and calibration with
  synthetic negatives weighted to a user-given base rate. "It is not possible to calibrate a model
  without implicit or explicit base rate". At base rate 0.5, predicting the base rate gives Brier 0.25
  and log loss 0.69.
- **KG embeddings, top-1** (Verified, [Safavi et al., 2020](https://arxiv.org/abs/2004.01168) §4.1). ECE
  with 10 bins over queries, with accuracy "the proportion of top-ranked predicted relations that
  correctly answer each query". The paper evaluates under both the closed-world and the open-world
  assumption.
- **N-ary**: "No calibration study of n-ary link predictors was found" (XAI §3). A web search on
  2026-09-23 found none either.

### 3.2 Metric definitions for the C5 completion scorer (Recommendation)

A **query** `q` is a test fact `f` with one binding position masked: a role `ρ`, a slot class (core or
qualifier), and for repeated roles an index. The target is `a`, the candidate universe `C_q` and the known
answers `K_q`.

| Id | Metric | Definition |
|---|---|---|
| C-M1 | Known answers (filter) | `exact`: `K_q = {c : f[ρ←c] ∈ Train ∪ Valid ∪ Test}` with all other bindings equal as a set, not a sequence. `monotone`: also every `c` for which a known fact has the same relation and core bindings and a superset of `f`'s qualifiers. `time_aware`: restricted to facts valid at the query's as-of time. |
| C-M2 | Ranks | Over `C' = C_q \ (K_q \ {a})`: `o = 1 + |{c ∈ C'\{a} : s(c) > s(a)}|`, `p = 1 + |{c ∈ C'\{a} : s(c) ≥ s(a)}|`, realistic `(o+p)/2`. |
| C-M3 | Tie-exact expectations | Under uniformly random tie-breaking (Sun et al.'s RANDOM, taken in expectation, so deterministic): `E[RR] = (1/(p−o+1))·Σ_{r=o..p} 1/r` and `E[Hits@k] = max(0, min(k,p) − o + 1)/(p − o + 1)`; `E[rank]` = realistic. |
| C-M4 | MRR, Hits@{1,3,10}, MR | Reported with three denominators: **per task** (mean over queries, literature-compatible), **per fact** (mean over facts of the mean over their queries), **macro over arity** (mean over bins of the per-fact mean). |
| C-M5 | Breakdowns | By arity bin, by role, by slot class (core or qualifier), by position preset (StarE s/o, GRAN all entities), and by seen or unseen entities (inductive). |
| C-M6 | Adjusted (optional) | Adjusted Hits@k `= (H − E[H])/(1 − E[H])` with `E[H] = mean_q min(k/|C'_q|, 1)`; AMRI `= (MR − E[MR])/(1 − E[MR])` with `E[MR] = mean_q (|C'_q|+1)/2`. |
| C-M7 | Top-1 calibration | `ŷ_q = argmax_{c∈C_q} P(c)`, unfiltered. It is correct iff `ŷ_q ∈ K_q ∪ {a}` (any known-true filler). Confidence is `P(ŷ_q)`. Report ECE with 15 equal-width bins, ECE with 15 equal-mass bins, Brier `mean_q (conf_q − correct_q)²`, the reliability table (count, accuracy and confidence per bin), and all of it per arity bin. |
| C-M8 | Per-candidate calibration (optional) | Tabacof and Costabello's binary form: `(q, c)` pairs labelled by `c ∈ K_q ∪ {a}`, under the closed-world assumption, with a declared base rate. Brier and log loss. |

Where the model does not emit probabilities, the mapping from scores to probabilities (softmax
temperature, Platt, isotonic) is part of the submission, fitted on validation, and declared. Calibration
is then a property of the model *plus* that mapping.

### 3.3 Inputs the completion scorer needs

- **From C4:** query items (§3.6); the three splits for the filter index; per-fact arity, slot classes
  and validity intervals; the candidate universe per query (all entities, entities seen in that
  position, or the inference-graph entities in inductive settings).
- **From the model:** full score vectors are impractical (tens of thousands of candidates per query).
  **Recommendation:** C5 ships the filter index and a rank counter, following PyKEEN's `RankBuilder` that
  accumulates `larger` and `not_smaller` counts. Model code emits per query `n_candidates`,
  `n_filtered_out`, `n_greater`, `n_equal`, the target probability, and the top-1 id with its
  probability. That is enough for C-M2 to C-M8.

### 3.4 Defaults (Recommendation)

- Filter `exact`, positions = all roles (per-role breakdown), rank = tie-exact expectation (C-M3), and all
  three averages (C-M4). Headline for new findings is macro over arity. Headline for replication is per
  task.
- **Replication presets for P3b.** `hype` (all positions, pessimistic ties, full-tuple filter, per-task
  average). `stare` (subject and object averaged, sort-order ties, `(s, r, quals)` filter, WD50K universe
  restricted to entities seen as subject or object). `hyper` (all positions, pessimistic ties). The P3b
  gate ("reproduced within stated tolerance") is otherwise at the mercy of tie conventions.
- Calibration: C-M7 with M = 15, both binnings, and bin counts. Suppress per-arity ECE for bins with fewer
  than 100 queries and report counts (**Recommendation**; the threshold is a guess to be tuned).
- Also report `monotone` and `time_aware` results whenever qualifiers or validity intervals exist. The
  difference from `exact` measures false errors.

### 3.5 Pitfalls (completion)

1. Position protocol (all entities against s/o): 0.656 against 0.617 for the same model (GRAN Table 2).
2. Denominator: per task reweights by arity (BEP §5.5). Unit test C4 gives 0.40 per task against 0.55 per
   fact on the same ranks.
3. Tie conventions change the MRR of models that emit tied scores (Sun et al.).
4. **`1/realistic` is not `E[1/rank]`** (unit test C3). State which one is reported.
5. Filter index keyed on *ordered* qualifier sequences (StarE) makes equal statements unequal when their
   qualifiers are listed in different orders (**Derived** from the code).
6. Exact-match filtering ignores qualifier-entailed and time-valid answers (§3.1.2).
7. Candidate universe: restricting to entities seen in a position (StarE on WD50K) raises scores. Record
   it.
8. Literals are usually dropped (BEP §5.4). A literal-valued masked slot needs its own universe and its
   own match rule (§2.2.1), or is excluded and counted.
9. Calibration depends on the score-to-probability map and, per triple, on the base rate (Tabacof and
   Costabello). Equal-width ECE is unstable in sparse bins (Nixon et al.), which is the normal case at
   arity ≥ 5.
10. Leakage (BEP §4): 44.5 % of JF17K test statements share the main triple with training. P3a's
    leak-check output should be attachable to the completion report (R01 C5-R24).

### 3.6 JSON shapes (completion)

Query item (P3a builds these from test facts, or C5 derives them from facts plus a position preset).

```json
{
  "qid": "p3a-cq-004211",
  "split": "test",
  "fact_id": "khg:stmt-0001",
  "relation": "award_received",
  "arity": 4,
  "target": {"role": "conferrer", "index": 0, "slot_class": "core", "value": {"entity": "Q193592"}},
  "context": [
    {"role": "recipient", "value": {"entity": "Q937"}},
    {"role": "award", "value": {"entity": "Q38104"}},
    {"role": "point_in_time", "value": {"literal": "1921", "datatype": "date", "precision": "year"}}
  ],
  "as_of": null,
  "candidate_universe": "all_entities",
  "inductive": {"unseen_context_entities": 0, "unseen_relation": false}
}
```

Model output per query (rank statistics, not score vectors):

```json
{
  "qid": "p3a-cq-004211",
  "n_candidates": 47156,
  "n_filtered_out": 2,
  "n_greater": 2,
  "n_equal": 0,
  "target_prob": 0.18,
  "top1": {"value": {"entity": "Q42"}, "prob": 0.41},
  "prob_map": {"kind": "softmax", "temperature": 1.0, "fitted_on": "valid"}
}
```

Scorer output (abridged):

```json
{
  "scorer": "completion",
  "config": {"filter": "exact", "positions": "all_roles", "rank": "tie_exact_expectation", "preset": null},
  "aggregate": {
    "per_task": {"mrr": 0.4, "hits@1": 0.25, "hits@3": 0.5, "hits@10": 0.75, "mr": 12.5},
    "per_fact": {"mrr": 0.55},
    "macro_arity": {"mrr": 0.55},
    "rank_audit": {"optimistic_mrr": 0.41, "pessimistic_mrr": 0.39, "realistic_inverse_mrr": 0.4}
  },
  "by_arity": {"2": {"mrr": 1.0, "n_queries": 2}, "4": {"mrr": 0.1, "n_queries": 4}},
  "by_role": {"conferrer": {"mrr": 0.1}},
  "calibration": {"ece_equal_width_15": 0.13, "ece_equal_mass_15": 0.12, "brier_top1": 0.1965, "n": 10, "reliability": [{"bin": 10, "n": 4, "acc": 0.75, "conf": 0.95}]},
  "calibration_by_arity": {"2": {"ece_equal_width_15": 0.25, "n": 5}, "4": {"ece_equal_width_15": 0.19, "n": 5}},
  "filter_sensitivity": {"exact_mrr": 0.4, "monotone_mrr": 0.43, "time_aware_mrr": 0.39}
}
```

### 3.7 Unit tests (completion)

| Test | Setup | Expected |
|---|---|---|
| C1 no ties | scores t 0.5, x 0.9, y 0.8, z 0.1 | rank 3; RR 1/3; Hits@1 0, Hits@3 1 |
| C2 filtering | e1 0.9 (known true), e3 0.7 (target), e2 0.2, e4 0.1, e5 0.05 | raw rank 2 (RR 0.5); filtered rank 1 (RR 1) |
| C3 four-way tie | t, a, b, c all 0.8; d 0.1 | o = 1, p = 4, realistic 2.5; `1/realistic` = 0.4, Hits@1 (realistic) = 0, Hits@3 (realistic) = 1; tie-exact E[RR] = (1 + 1/2 + 1/3 + 1/4)/4 = 25/48 ≈ 0.520833, E[Hits@1] = 0.25, E[Hits@3] = 0.75 |
| C4 denominators | fact F1 (arity 2) RRs (1, 1); fact F2 (arity 4) RRs (0.1 × 4) | per task (2 + 0.4)/6 = 0.40; per fact (1 + 0.1)/2 = 0.55; macro over arity 0.55 |
| C5 time-aware filter | o1 valid 2010–2015 (0.9), o2 valid 2016– (target, 0.8), o3 (0.1); query as of 2020 | time-agnostic filter removes o1: rank 1; time-aware keeps o1: rank 2, RR 0.5 |
| C6 monotone filter | query `(s, r, ?, {deg: BSc})`, target ETH 0.6; known `(s, r, UZH, {deg: BSc, year: 1900})` scores 0.7 | exact filter: rank 2; monotone filter removes UZH: rank 1 |
| C7 calibration | 10 queries: conf 0.95 × 4 (3 correct), 0.55 × 4 (2 correct), 0.15 × 2 (0 correct); M = 10 | ECE = 0.4·0.20 + 0.4·0.05 + 0.2·0.15 = 0.13; Brier = (3·0.0025 + 0.9025 + 2·0.2025 + 2·0.3025 + 2·0.0225)/10 = 0.1965; accuracy 0.5; mean confidence 0.63 |
| C8 ECE by arity | C7's first five items are arity 2, last five arity 4 | arity 2: 0.8·0.20 + 0.2·0.45 = 0.25; arity 4: 0.6·(0.55 − 1/3) + 0.4·0.15 = 0.19 |

---

## 4. Retrieval for question answering over hypergraphs

### 4.1 What the literature does

#### 4.1.1 Ranking metrics over evidence

- **MRR** originates in the TREC-8 QA track (Verified,
  [Voorhees and Tice, 2000](http://www.lrec-conf.org/proceedings/lrec2000/pdf/26.pdf) §3): "the
  reciprocal of the rank at which the first correct response was returned, or 0 if none of the five
  responses contained a correct answer". That is a *cut-off* MRR. Link prediction's MRR ranks every
  candidate and never scores 0.
- **KILT** (Verified, [Petroni et al., 2021](https://arxiv.org/abs/2009.02252) §5; code at
  facebookresearch/KILT commit `2664322`). **R-precision** is `r/R` over the top-R pages for each
  provenance set, and "We report the maximum value among all provenance sets". **Recall@k** is `w/n`,
  with "n ... the number of distinct provenance sets" and "w ... the number of complete provenance sets
  among the top-k". For multi-page sets the lowest-ranked page fixes the set's position and the set's
  other pages are removed from the rank (`get_rank`). **KILT scores** award EM, F1, accuracy or
  ROUGE-L "only if the R-precision is 1". The script also has `answer_in_context@k` (a normalised gold
  answer is a substring of a retrieved passage) and `success_rate@k`.
- **LongMemEval** retrieval (code verified, `src/retrieval/eval_utils.py`, commit `9e0b455`). It reports
  `recall_any@k`, `recall_all@k` and nDCG@k, where DCG is `rel_1 + Σ_{i≥2} rel_i / log2(i)`. That differs
  from the `1/log2(i+1)` discount of scikit-learn 1.9.1 (checked 2026-09-23). On unit test R1 the two
  give 0.75 and 0.651. The same file calls `np.asfarray`, removed in NumPy 2.0: under NumPy 2.4.6 it
  raises `AttributeError` (run 2026-09-23).

#### 4.1.2 Supporting facts and joint scores

- **HotpotQA** (Verified, [Yang et al., 2018](https://arxiv.org/abs/1809.09600) §5.2, and
  `hotpot_evaluate_v1.py`, commit `3635853`). Supporting-fact EM and F1 are computed over sets of
  (title, sentence id). Joint scores use `P_joint = P_ans·P_sup` and `R_joint = R_ans·R_sup`, and "Joint EM
  is 1 only if both tasks achieve an exact match". The answer F1 returns zero when either side normalises
  to `yes`, `no` or `noanswer` and the two differ. Missing predictions count as 0 in the average.
- **2WikiMultiHopQA** (Verified, [Ho et al., 2020](https://aclanthology.org/2020.coling-main.580/) §2.1,
  §5.3). The evidence is "a set of triples". The joint score multiplies answer, supporting-fact and
  evidence precision and recall. Name ambiguity caps evidence scores (§2.1.4 above).
- **Answer EM and F1** (Verified, SQuAD §6.1): both "ignore punctuations and articles (a, an, the)", with
  maximum F1 over ground truths. **Answer sets**: GrailQA reports "the F1 score based on the predicted
  and gold answer sets", which "gives partial credits to imperfect answers" (Verified,
  [Gu et al., 2021](https://arxiv.org/abs/2011.07743) §5.1).

#### 4.1.3 What the hypergraph-RAG papers measure

- HyperGraphRAG: word-level F1, R-S (similarity of retrieved text to the construction unit) and G-E (an
  LLM judge over seven dimensions averaged with F1), with a Binary-Source/N-ary-Source split (EVC §4,
  RAG §2). CRH §2.2 shows why R-S should be discounted.
- Cost: seconds and dollars per 1k construction tokens and per query (RAG §2, CRH §2.4); prompt tokens per
  query in GraphRAG-Bench (CRH §5); PRoH reports tokens only for a lightweight variant (CRH §8.3).
- Mem0 reports p50 and p95 latency separately for search and for end-to-end response (Verified,
  [Chhikara et al., 2025](https://arxiv.org/abs/2504.19413), Table 2).
- CRH §7 item 6 and CST §4 bet 7: nobody plots accuracy against a token budget.

#### 4.1.4 GraphRAG-Bench, both of them

- **Xiang et al.**, "When to use Graphs in RAG", ICLR 2026
  ([arXiv:2506.05690](https://arxiv.org/abs/2506.05690); repo GraphRAG-Bench/GraphRAG-Benchmark, MIT,
  commit `fdbab59`, 2026-06-07). This is the one the KB and PLAN mean. Verified in paper App. F and code:
  - Context Relevance and Evidence Recall, both LLM-judged. Evidence Recall (Eq. 4) is the share of
    reference claims that an LLM judges supported by the retrieved context. The code truncates the
    context to 20,000 characters and returns NaN when the judge output does not parse.
  - Answer Accuracy `AC = α·FC + (1−α)·SS` with `α = 0.75` and `FC` a statement-level F1 from an LLM
    classification into TP, FP and FN. The paper gives `SS = cos(...)`; the code returns
    `(cos + 1)/2`, which sets a floor. A factually empty answer with cosine 0.5 scores
    `0.25 × 0.75 = 0.1875`.
  - ROUGE-L with stemming; Faithfulness; Evidence Coverage.
  - Metrics per question type (`generation_eval.py`): Fact Retrieval and Complex Reasoning use ROUGE-L
    and Answer Accuracy; Contextual Summarize uses Answer Accuracy and Coverage; Creative Generation uses
    Answer Accuracy, Coverage and Faithfulness. Aggregation is `np.nanmean`.
- **Xiao et al.**, "GraphRAG-Bench: Challenging Domain-Specific Reasoning for Evaluating Graph
  Retrieval-Augmented Generation" ([arXiv:2506.02404](https://arxiv.org/abs/2506.02404), v3 2025-06-20;
  repo jeremycp3/GraphRAG-Bench). A different benchmark. LLM-judged Accuracy for open-ended and
  fill-in-the-blank questions, 1/0 for multiple-choice and true/false, 1/0.5/0 for multi-select, a
  rationale score R and an AR metric, plus construction time, tokens and "non-isolated nodes ratio"
  (Verified, §3).

### 4.2 Metric definitions for the C5 retrieval scorer (Recommendation)

Question `q` has alternative minimal support sets `𝒮_q = {S_1, …, S_m}` of gold hyperedge ids and a typed
gold answer. The system returns a ranked list `L` of units. Each unit maps to the hyperedge ids it derives
from, through back-pointers for pairwise projections and sentence chunks (R01 §1, P4 row). It may also
return an unranked claimed support set `Ŝ`, an answer and a cost record.

| Id | Metric | Definition |
|---|---|---|
| R-M1 | `hit@k` | `1[L[:k] ∩ ∪_i S_i ≠ ∅]` (LongMemEval `recall_any`) |
| R-M2 | `support_success@k` | `1[∃ i : S_i ⊆ hyperedges(L[:k])]`: a complete sufficient set was found (LongMemEval `recall_all`, generalised to alternatives) |
| R-M3 | `support_recall@k` | `max_i |S_i ∩ hyperedges(L[:k])| / |S_i|` |
| R-M4 | `mrr@k` | `1/rank` of the first unit containing any `h ∈ ∪S_i`, 0 if none in the top k (TREC-8 style) |
| R-M5 | `r_precision` | `max_i |S_i ∩ hyperedges(L[:|S_i|])| / |S_i|` (KILT) |
| R-M6 | `ndcg@k` | Binary relevance; `DCG = Σ_i rel_i / log2(i+1)`; ideal over `min(|S*|, k)`; maximum over sets. The discount is named in the output. |
| R-M7 | `support_p/r/f1/em` | For `Ŝ` against the best-matching set (maximum F1), HotpotQA-style |
| R-M8 | `binding_coverage@k` | `max_i |B(S_i) ∩ B(L[:k])| / |B(S_i)|`: of the gold bindings `(r, ρ, v)` of the support, the share recoverable from retrieved units. It compares hyperedge, pairwise and chunk conditions on one scale (P4). |
| R-M9 | Answer metrics | `single` mode: `EM = 1[â ∈ A]` on ids or typed literals, and for text SQuAD-normalised EM and token F1, maximum over the aliases of each gold value. `set` mode: `P = |Â∩A|/|Â|`, `R = |Â∩A|/|A|`, set F1, set EM. `hits@1` when a ranked answer list is returned. |
| R-M10 | Joint and gated | `P_joint = P_ans·P_sup`, `R_joint = R_ans·R_sup`, joint F1 and joint EM (HotpotQA); `gated_em = EM·1[r_precision = 1]` (KILT) |
| R-M11 | Abstention | On unanswerable items: abstention precision and recall |
| R-M12 | Cost | Per question: prompt and completion tokens, LLM calls, retrieval calls, hyperedges visited, retrieval and end-to-end wall-clock (ms), and USD with a dated price table. Aggregates: mean, median, p90, p95 and total. Accuracy against a token budget as a curve (answer EM at cumulative-token cut-offs). |

### 4.3 Inputs the retrieval scorer needs

- **From C4:** the question item (§4.6) with alternative support sets, required edge, hop count, arity of
  the required edge, source class (binary or n-ary), typed answer with aliases, answerability, and as-of
  time.
- **From C1:** the bindings of each gold hyperedge (for R-M8) and back-pointers from projected units.
- **From the system:** the response record, with a mandatory `cost` block and retrieval list.

### 4.4 Defaults (Recommendation)

- k ∈ {1, 3, 5, 10, 20}. Headline retrieval metrics are `support_success@10` and `mrr@10`. Headline
  answer metric is EM on canonical ids, then token F1 on text.
- Everything broken down by hops, by arity of the required edge, and by source class (EVC §4, CRH §2.3).
- The external GraphRAG-Bench adapter reports Xiang et al.'s native metrics under their own names, never
  merged with C5's. Pin the arXiv id and the repository commit.

### 4.5 Pitfalls (retrieval)

1. KILT recall divides by the number of *alternative* sets (unit test R2: 0.5 for a fully sufficient
   retrieval). Use `support_success` for "found enough".
2. KILT's rank compresses multi-page sets into one slot, so KILT recall@3 can be 1 while the set is only
   complete at raw position 4 (unit test R1). It is not comparable with raw `recall_all@k`.
3. nDCG discount variants (R1: 0.75 against 0.651).
4. Cut-off MRR against full-rank MRR.
5. Token F1 rewards wrong short answers. Mem0's example: "Alice was born in March" against "Alice is born
   in July" scores high on lexical overlap (§3.2). Canonical-id EM is the primary metric for
   entity-valued answers.
6. Retrieval similarity to the construction unit (R-S) favours systems whose unit *is* that unit (CRH
   §2.2). C5 does not compute it.
7. Question sets built from the indexed corpus measure index alignment (CRH §2.2, §7). Record the
   generator and verification in each item.
8. LLM-judged evidence recall with silent NaN dropping and truncation (GraphRAG-Bench code): the
   denominators vary per metric.
9. Duplicate hyperedges with different ids: a retrieved duplicate of a gold edge should count. That
   needs the content-key equivalence of C1, or back-pointers.
10. Cost figures from different accounting (context tokens against dollars) cannot be compared (RAG §6).

### 4.6 JSON shapes (retrieval)

Question item (P3a fills it):

```json
{
  "qid": "p3a-rq-000123",
  "qset_version": "p3a-qs-retrieval/1.0.0",
  "split": "test",
  "type": "retrieval_qa",
  "text": "Which organisation awarded Albert Einstein the 1921 Nobel Prize in Physics?",
  "template_id": "award_received/conferrer/v1",
  "answer": {"mode": "single", "values": [{"entity": "Q193592"}]},
  "aliases": {"Q193592": ["Royal Swedish Academy of Sciences", "Kungliga Vetenskapsakademien"]},
  "support": {"sets": [["khg:stmt-0001"]]},
  "required_edge": {"fact_id": "khg:stmt-0001", "relation": "award_received", "arity": 4, "roles_used": ["recipient", "award", "point_in_time", "conferrer"]},
  "hops": 1,
  "source_class": "n-ary",
  "as_of": null,
  "answerable": true,
  "provenance": {"generator": "template", "generator_version": "1.0.0", "verified": "human", "verifiers": 2}
}
```

System response:

```json
{
  "qid": "p3a-rq-000123",
  "answer": {"values": [{"entity": "Q193592"}], "text": "The Royal Swedish Academy of Sciences.", "abstained": false},
  "retrieved": [
    {"rank": 1, "unit_id": "khg:stmt-0001", "unit_kind": "hyperedge", "hyperedge_ids": ["khg:stmt-0001"]},
    {"rank": 2, "unit_id": "pair:0001:recipient-award", "unit_kind": "pair", "hyperedge_ids": ["khg:stmt-0001"]}
  ],
  "support_claimed": ["khg:stmt-0001"],
  "cost": {"prompt_tokens": 1830, "completion_tokens": 42, "llm_calls": 3, "retrieval_calls": 2, "hyperedges_visited": 11, "retrieval_ms": 310, "wall_ms": 2140, "usd": 0.0041, "price_table": "prices-2026-09-01"}
}
```

Scorer output (abridged):

```json
{
  "scorer": "retrieval",
  "aggregate": {
    "hit@10": 0.91, "support_success@10": 0.84, "support_recall@10": 0.9, "mrr@10": 0.71, "r_precision": 0.66, "ndcg@10": {"value": 0.74, "discount": "log2(i+1)"},
    "support": {"p": 0.8, "r": 0.85, "f1": 0.82, "em": 0.6},
    "answer": {"em": 0.62, "f1": 0.7, "set_f1": 0.66},
    "joint": {"f1": 0.55, "em": 0.41}, "gated_em": 0.52,
    "abstention": {"precision": 0.9, "recall": 0.75}
  },
  "cost": {"prompt_tokens": {"mean": 1790, "median": 1710, "p90": 2400, "p95": 2710, "total": 895000}, "wall_ms": {"median": 2010, "p95": 4300}, "usd_total": 2.05, "price_table": "prices-2026-09-01"},
  "by_hops": {"1": {"answer_em": 0.7}, "2": {"answer_em": 0.51}},
  "by_required_arity": {"2": {"answer_em": 0.68}, "4": {"answer_em": 0.55}},
  "by_source_class": {"binary": {"answer_em": 0.66}, "n-ary": {"answer_em": 0.58}},
  "budget_curve": [{"max_prompt_tokens": 1000, "answer_em": 0.31}, {"max_prompt_tokens": 2000, "answer_em": 0.55}]
}
```

### 4.7 Unit tests (retrieval)

| Test | Setup | Expected |
|---|---|---|
| R1 one support set | gold `{h1, h2}`; ranked `[h3, h1, h4, h2]` | hit@1 0, hit@2 1; success@2 0, success@4 1; support_recall@2 0.5; mrr 0.5; R-precision 0.5; KILT recall@2 0, @3 1, @4 1; nDCG@4 with `log2(i+1)`: (1/log2 3 + 1/log2 5)/(1 + 1/log2 3) ≈ 0.650921; LongMemEval variant: (1 + 0.5)/2 = 0.75 |
| R2 alternative sets | sets `{h1,h2}` or `{h5}`; ranked `[h5, h1, h9]` | R-precision 1 (via `{h5}`); success@1 1; KILT recall@1 = 1/2 = 0.5 |
| R3 answer text | gold "Royal Swedish Academy of Sciences" | "the Royal Swedish Academy of Sciences." gives EM 1; "Swedish Academy" gives P 1, R 2/5, F1 4/7 ≈ 0.571429 |
| R4 entity set | gold {Q1, Q2}; predicted {Q1, Q3} | P = R = F1 = 0.5; set EM 0 |
| R5 joint | answer P 1, R 0.4 (R3); support P 0.5, R 0.5 | joint P 0.5, joint R 0.2, joint F1 = 0.2/0.7 ≈ 0.285714 |
| R6 gated EM | EM 1 with R-precision 0.5; EM 1 with R-precision 1 | gated 0; gated 1 |
| R7 cost | prompt tokens [100, 300, 200] | mean 200; median 200; p90 (nearest rank) 300 |
| R8 substring trap | gold "5"; prediction "15 items" | character-substring match (MemoryAgentBench SubEM) 1; token containment 0; C5 default 0 |

---

## 5. Memory with supersession

### 5.1 What the literature does

#### 5.1.1 LongMemEval

Verified 2026-09-23: paper [Wu et al., ICLR 2025](https://arxiv.org/abs/2410.10813), repo commit
`9e0b455` (MIT), cleaned data `longmemeval_oracle.json` from Hugging Face (dataset card licence MIT, last
modified 2025-09-19).

- **Abilities and counts.** The five abilities include "Knowledge Updates (KU): Ability to recognize the
  changes in the user's personal information and update the knowledge of the user dynamically over time"
  and "Temporal Reasoning (TR)". Counted in the cleaned oracle file: 500 questions. By type:
  temporal-reasoning 133, multi-session 133, knowledge-update 78, single-session-user 70,
  single-session-assistant 56, single-session-preference 30. 30 abstention items carry an `_abs` suffix.
- **Record shape.** `question_id`, `question_type`, `question`, `answer`, `question_date`,
  `haystack_session_ids`, `haystack_dates`, `haystack_sessions` (turns with `has_answer: true` on
  evidence turns) and `answer_session_ids`. The **gold stores only the new value**. In KU item
  `6a1eabeb`, session 1 says "a time of 27:12", session 2 says "my personal best time of 25:50", and the
  answer field is "25 minutes and 50 seconds (or 25:50)". The superseded value appears only in the
  haystack text.
- **Scoring.** A GPT-4o judge (`gpt-4o-2024-08-06` asserted in `print_qa_metrics.py`), temperature 0,
  `max_tokens` 10. The label is `'yes' in response.lower()`. The prompts are per type. For KU: "If the
  response contains some previous information along with an updated answer, the response should be
  considered as correct as long as the updated answer is the required answer." For TR: "do not penalize
  off-by-one errors for the number of days". For abstention: correct if the model "correctly identifies
  the question as unanswerable". The judge agreed with experts on 30/30 KU items and 0.98 on average
  (Table 6). Outputs are task-averaged accuracy, overall accuracy and abstention accuracy.
- **Retrieval** metrics are Recall@k and NDCG@k against evidence sessions or turns (§4.1.1). The authors
  note that KU retrieval is judged "failed" when only the updated session is retrieved. Their "strict
  retrieval evaluation criteria" require both old and new evidence (§E.5, Verified).

#### 5.1.2 LoCoMo

Verified 2026-09-23: paper [Maharana et al., 2024](https://arxiv.org/abs/2402.17753) §4.1; repo commit
`3eb6f2c` (licence CC BY-NC 4.0); data `locomo10.json`.

- The paper defines five categories. Answers are scored with "the F1 score for exact matches" after
  normalisation, and "the F1 partial match metric". TMP §6: the temporal category concerns dates, and
  nothing requires a fact to have been replaced. LongMemEval's Table 1 marks LoCoMo without KU.
- **Released data ≠ paper data.** The README says "This release is a subset ... The initial release
  contained 50 conversations". The file has 10 conversations and 1,986 QA items: ids 1 = 282, 2 = 321,
  3 = 96, 4 = 841, 5 = 446.
- **Category ids do not follow the paper's list order.** The paper lists (1) single-hop, (2) multi-hop,
  (3) temporal, (4) open-domain, (5) adversarial. In the data, 95 % of id-1 questions have evidence in
  more than one session and 77 % of id-2 questions start with "When". The evaluation code treats id 1 as
  multi-hop (comma-split partial F1) and ids 2, 3, 4 with plain F1. **Derived:** id 1 is multi-hop, 2 is
  temporal, 3 is open-domain, 4 is single-hop, 5 is adversarial.
- `evaluation.py` normalises by removing commas and the words a, an, the and *and*, and applies Porter
  stemming before F1. Category 3 keeps only the text before `;`. Category 5 scores 1 if the output
  contains "no information available" or "not mentioned".
- Mem0 excluded category 5 "because ground truth answers were unavailable" and used an LLM judge, with 10
  runs, mean ± sd (Verified, §3.1–§3.2). AGT and TMP §6 show that strict-judge and LLM-judge LoCoMo
  numbers are not comparable.

#### 5.1.3 MemoryAgentBench

Verified 2026-09-23: [Hu, Wang and McAuley, ICLR 2026](https://arxiv.org/abs/2507.05257) (v4, 28 Jun 2026);
repo HUST-AI-HYZ/MemoryAgentBench commit `fe1735d` (MIT).

- Competency 4 is **Selective Forgetting** ("revise, overwrite, or remove previously stored information
  when faced with contradictory evidence"). It was called *conflict resolution* in v1 (7 Jul 2025).
- **FactConsolidation** is built from MQuAKE counterfactual edit pairs. The rewritten fact is placed after
  the original, pairs are concatenated to 6K–262K tokens, and there are single-hop (SH) and multi-hop
  (MH) questions. Agents "are prompted to prioritize later information in case of conflict". The metric
  is SubEM. In the code it is `normalize_answer(ground_truth) in normalize_answer(prediction)`, a
  **character** substring after SQuAD-style normalisation. All methods reach at most 28 % on multi-hop.
- There is no stale-answer measurement. An answer that mentions both values passes SubEM.

#### 5.1.4 Benchmarks that score the outdated answer explicitly

- **EvolvingQA** (Verified, [Kim et al., NAACL 2024](https://aclanthology.org/2024.naacl-long.302/)
  §2.2, §3.3). Each edited QA instance has "an OUTDATED answer, and an UPDATED answer". EM and F1 are reported
  against both, and "the performance of OUTDATED should be as close to zero as possible". In a
  two-option multiple-choice variant, models selected the OUTDATED answer more than 50 % of the time.
- **CounterFact** (Verified, [Meng et al., 2022](https://arxiv.org/abs/2202.05262) §3.3). "Efficacy
  Score (ES) is the portion of cases for which we have P[o∗] > P[o^c]", and Efficacy Magnitude is the
  mean difference. This is a pairwise, score-based test of "the new value beats the old".
- **TempLAMA** (Verified, [Dhingra et al., 2022](https://arxiv.org/abs/2106.15110) §2.1–§2.2). From the
  November 2020 Wikidata snapshot: facts "which have either a start or an end date after 2010";
  "a separate query for each year in that interval"; "When intervals for the object entities overlap, we
  add all of them to the list of correct answers"; 50,310 queries; token F1, with the maximum over
  multiple targets. This is the closest published recipe for P3a's as-of questions from Wikidata
  qualifiers.
- **SituatedQA** (Verified, abstract, [Zhang and Choi, EMNLP 2021](https://arxiv.org/abs/2109.06157)):
  answers depend on temporal or geographical context. Models trained on past data lose about 15 points
  on present-day answers even with an updated corpus.

#### 5.1.5 Other context

- Zep/Graphiti, HyperMem and EdgeMem results and their protocols: TMP §2, §4 and §6; AGT. "No published
  experiment isolates supersession as the dependent variable for a hypergraph memory" (TMP §6).
- LongMemEval-V2 (arXiv:2605.12493, 12 May 2026) has 451 questions over web-agent trajectories. Its
  abilities include "Dynamic state tracking", and per its README (commit `2cc8c54`) "evaluation targets
  both answer accuracy and query latency". Scoring details were not read `[unverified]`.
- R04 M5 distinguishes a fact that *ended in the world* (closed valid-time interval) from a record that
  was *superseded as belief* (retraction or correction). A memory scorer that has one "stale" bucket
  conflates them.

### 5.2 Metric definitions for the C5 memory scorer (Recommendation)

A memory question has a key `(r, κ, ρ)`: a relation, a binding of its key roles (R01 C1-R28), and the
queried role. It also has an as-of valid time `t` (default: the end of the trace) and an as-at transaction
time `τ` (default: after the full trace). The trace fixes three value sets:

- `V_cur`: values of `ρ` in hyperedges with key `κ`, valid at `t` and believed at `τ`.
- `V_old`: values valid only before `t` (`expired`), or believed before `τ` and later retracted
  (`retracted`).
- `V_fut`: values valid only after `t`. This set is non-empty only for as-of-past questions.

The system returns a structured answer set `Â` (ids or typed literals), optional text, an abstain flag,
and optionally scores per value.

| Id | Outcome for one item | Rule |
|---|---|---|
| O1 `current` | correct | `Â ∩ V_cur ≠ ∅`, `Â ∩ (V_old ∪ V_fut) = ∅`; set-valued questions also need `Â ⊇ V_cur` (else score set F1) |
| O2 `hedged` | lenient-correct, strict-wrong | `Â ∩ V_cur ≠ ∅` and `Â ∩ (V_old ∪ V_fut) ≠ ∅` (LongMemEval's KU judge accepts this) |
| O3 `stale` (split `expired` / `retracted`) | wrong | `Â ∩ V_cur = ∅`, `Â ∩ V_old ≠ ∅` |
| O4 `anachronistic` | wrong | `Â ∩ V_cur = ∅`, `Â ∩ V_fut ≠ ∅` |
| O5 `wrong` | wrong | anything else |
| O6 `abstained` | wrong on answerable items | abstain flag or empty `Â` |
| O7 `correct_abstention` / `hallucinated` | on unanswerable items | abstained / answered |

| Id | Metric | Definition |
|---|---|---|
| M-M1 | Strict accuracy | `#O1 / N` over answerable items (plus correct abstentions if they are pooled; declare which) |
| M-M2 | Lenient accuracy | `(#O1 + #O2) / N` (LongMemEval-compatible) |
| M-M3 | Stale rate | `#O3 / N`, split into expired and retracted; also `stale share of errors = #O3 / (N − #O1)` |
| M-M4 | Anachronism rate, hedge rate, abstention rate | `#O4/N`, `#O2/N`, `#O6/N` |
| M-M5 | Abstention quality | precision and recall of abstaining on unanswerable items |
| M-M6 | Ranked efficacy (optional) | `mean 1[score(v_cur) > max_{v ∈ V_old} score(v)]` (CounterFact ES) when the system exposes scores |
| M-M7 | Support retrieval | `support_success@k` (R-M2) against **current** support only; history recall (superseded hyperedges plus supersession record) reported separately, not required |
| M-M8 | Temporal tolerance | Numeric answers (durations, counts of days) carry a per-item tolerance, default 0; ±1 day reproduces LongMemEval's TR rule |

Breakdowns: by subtype (current value, past value, change detection, count of changes, abstention), by
number of supersessions on the key, by arity of the keyed relation, and by distance in steps between the
last update and the question.

**Text-only systems** (for example, P7's flat vector-store baseline). Map the answer text to `Â` by
normalised alias match against `V_cur ∪ V_old ∪ V_fut`. When both a current and an old value are
mentioned, the item is `hedged` unless a declared final-answer extractor isolates one. An LLM-judge
adapter (LongMemEval's KU prompt, named judge) is available and reported separately.

### 5.3 Inputs the memory scorer needs

- **Trace:** timestamped events that assert facts, end validity, or retract. Each event carries its C1
  fact with valid time, its transaction time, and optional source text for systems that ingest text.
- **Question:** key, as-of and as-at times, `V_cur`, `V_old` (with kind), `V_fut`, support (current and
  history), answerability and tolerance.
- **Response:** structured answer, text, abstain flag, optional per-value scores, retrieved hyperedges
  and cost.

### 5.4 Defaults (Recommendation)

- Strict accuracy as headline, lenient beside it, stale rate always reported. That answers the P7 gate's
  "memory comparison ... on the superseding-fact question set" in the form R01 C5-R18 and C5-R19 require.
- Only keyed (functional-at-an-instant) relations generate current-value questions. Multi-valued
  relations get set questions scored by set F1 (TMP §1(b): without a key, supersession is undefined).
- The external LongMemEval KU adapter runs on the 78 KU items and reports the judge's numbers under
  LongMemEval's names.

### 5.5 Pitfalls (memory)

1. Stored gold without the superseded value (LongMemEval) forces an LLM judge. Store `V_old`.
2. Hedged answers pass lenient judges (LongMemEval KU prompt) and substring metrics (SubEM). Report
   `hedged` as its own outcome.
3. Character-substring matching accepts "15" for gold "5" (unit test R8).
4. Retrieval that demands both old and new evidence (LongMemEval) penalises a memory that correctly
   discards history. Separate required and history support.
5. LoCoMo's temporal category does not test supersession, its category ids need remapping, and its data
   licence is non-commercial.
6. Judge protocol differences make numbers incomparable (TMP §6: strict-judge 61.01 against LLM-judge
   92.73 on LoCoMo).
7. Valid-time change and belief revision are different errors (R04 M5). A single "stale" bucket hides
   which one the system fails.
8. The as-of time must be explicit. "Current" relative to the end of the trace, to the question date
   (LongMemEval's `question_date`) or to wall-clock time differ.

### 5.6 JSON shapes (memory)

Trace:

```json
{
  "trace_id": "p3a-mt-0007",
  "qset_version": "p3a-qs-memory/1.0.0",
  "split": "test",
  "events": [
    {"step": 1, "tx_time": "2026-01-10T09:00:00Z", "op": "assert", "text": "Alice became CEO of Acme in May 2019.",
     "fact": {"fact_id": "h1", "relation": "position_held",
              "bindings": [{"role": "holder", "value": {"entity": "Qalice"}}, {"role": "position", "value": {"entity": "Qceo_acme"}}],
              "valid_time": {"start": "2019-05-01", "end": null}}},
    {"step": 2, "tx_time": "2026-02-02T09:00:00Z", "op": "assert", "text": "Bob took over as CEO of Acme on 1 January 2026.",
     "fact": {"fact_id": "h2", "relation": "position_held",
              "bindings": [{"role": "holder", "value": {"entity": "Qbob"}}, {"role": "position", "value": {"entity": "Qceo_acme"}}],
              "valid_time": {"start": "2026-01-01", "end": null}}},
    {"step": 2, "tx_time": "2026-02-02T09:00:00Z", "op": "end_validity", "target": "h1", "end": "2025-12-31", "end_cause": "replaced"}
  ]
}
```

Question:

```json
{
  "qid": "p3a-mq-0042",
  "trace_id": "p3a-mt-0007",
  "ask_after_step": 2,
  "subtype": "current_value",
  "text": "Who is the CEO of Acme now?",
  "as_of": "end_of_trace",
  "as_at": "after_step",
  "key": {"relation": "position_held", "key_bindings": [{"role": "position", "value": {"entity": "Qceo_acme"}}], "target_role": "holder"},
  "answer": {"mode": "single", "values": [{"entity": "Qbob"}]},
  "stale_values": [{"value": {"entity": "Qalice"}, "fact_id": "h1", "kind": "expired"}],
  "future_values": [],
  "support": {"current": ["h2"], "history": ["h1"]},
  "aliases": {"Qbob": ["Bob"], "Qalice": ["Alice"]},
  "answerable": true,
  "tolerance": null,
  "keyed_relation_arity": 2,
  "n_supersessions_on_key": 1
}
```

System response (a text-only system leaves `values` empty and the scorer maps `text` through `aliases`):

```json
{
  "qid": "p3a-mq-0042",
  "system": {"name": "hypergraph-memory", "version": "0.1.0"},
  "answer": {"values": [{"entity": "Qbob"}], "text": "Bob is the CEO now (Alice held the post until the end of 2025).", "abstained": false},
  "value_scores": [{"value": {"entity": "Qbob"}, "score": 0.93}, {"value": {"entity": "Qalice"}, "score": 0.41}],
  "retrieved": [{"rank": 1, "hyperedge_ids": ["h2"]}, {"rank": 2, "hyperedge_ids": ["h1"]}],
  "cost": {"prompt_tokens": 950, "completion_tokens": 30, "llm_calls": 1, "wall_ms": 820}
}
```

The text of this response names both holders. Scored on `values` it is `current`. Scored on the text
alone, by alias matching, it would be `hedged`, which is why D-C5-13 asks systems for structured answers.

Scorer output (abridged):

```json
{
  "scorer": "memory",
  "aggregate": {"n": 10, "acc_strict": 0.6, "acc_lenient": 0.6, "stale_rate": 0.3, "stale_expired_rate": 0.3, "stale_retracted_rate": 0.0,
                "anachronism_rate": 0.0, "hedge_rate": 0.0, "abstain_rate": 0.1, "stale_share_of_errors": 0.75,
                "abstention": {"precision": null, "recall": null}, "ranked_efficacy": null},
  "support": {"current_success@10": 0.8, "history_recall@10": 0.4},
  "by_subtype": {"current_value": {"acc_strict": 0.6}},
  "by_n_supersessions": {"1": {"acc_strict": 0.7}, "3+": {"acc_strict": 0.4}},
  "items": [{"qid": "p3a-mq-0042", "outcome": "current", "strict": 1, "lenient": 1}]
}
```

### 5.7 Unit tests (memory)

| Test | Setup | Expected |
|---|---|---|
| M1 current | `V_cur` {Qnew}, `V_old` {Qold}; answer {Qnew} | `current`; strict 1, lenient 1 |
| M2 stale | answer {Qold} | `stale`; 0, 0 |
| M3 hedged | answer {Qold, Qnew} | `hedged`; strict 0, lenient 1 |
| M4 abstention | unanswerable; abstains / answers Qx | `correct_abstention` 1 / `hallucinated` 0 |
| M5 as-of past | `V_cur` {o1} (valid at t), `V_fut` {o2}; answer {o2} | `anachronistic`; 0 |
| M6 aggregate | 10 items: 6 current, 3 stale, 1 abstained | strict 0.6, stale 0.3, abstain 0.1, stale share of errors 3/4 = 0.75 |
| M7 ranked efficacy | scores Qnew 0.7, Qold 0.6 | ES = 1 |
| M8 tolerance | gold 18 days; answer 19 | strict 0; with tolerance 1: 1 |

---

## 6. What P3a's question sets must contain

This is the consolidated list of fields C5 needs. The shapes are in §2.6, §3.6, §4.6 and §5.6.

| Field | Extraction doc | Completion query | Retrieval question | Memory question | Why (consumer) |
|---|---|---|---|---|---|
| stable id, split, set version | ✓ | ✓ | ✓ | ✓ | per-item join (P8), R01 C5-R01 |
| gold facts in C1 form, core key, arity | ✓ | fact ref | required edge | key + values | per-arity scoring (C5-R02) |
| evidence span per fact | ✓ | | | source text per event | provenance scoring; P4 chunk condition |
| alternatives / fact synsets | ✓ | | alternative support sets | | BenchIE, KILT |
| entity aliases, redirects | ✓ | | ✓ | ✓ | text-answer matching |
| annotation exhaustiveness | ✓ | | | | FP breakdown (§2.5 item 6) |
| seen / leak flags | ✓ | ✓ | | | Ign variant; DocRED, BEP §4 |
| target role, slot class, context | | ✓ | | | position presets |
| candidate universe; inductive flags | | ✓ | | | HYPER, StarE |
| validity intervals of facts | | ✓ | ✓ | ✓ | time-aware filter; as-of |
| typed answer + mode (single, set) | | ✓ | ✓ | ✓ | EM, set F1 |
| hops, required-edge arity, source class | | | ✓ | | EVC §4, CRH §2.3, P4 |
| generator, verification | | | ✓ | ✓ | CRH §7 item 1 |
| `V_old` (with kind), `V_fut`, current and history support | | | | ✓ | stale detection |
| answerability, tolerance | | | ✓ | ✓ | abstention; TR rule |

---

## 7. Cross-cutting pitfalls

1. **Name a dataset by version and a scorer by commit.** GraphRAG-Bench names two benchmarks; LoCoMo's
   released data is not the paper's (BEP §5.2 makes the same point for JF17K).
2. **External scripts rot.** LongMemEval's retrieval metrics fail under NumPy ≥ 2.0. Adapters pin their
   environments.
3. **Licences travel with fixtures.** Do not vendor LoCoMo (CC BY-NC 4.0) or `metametric` (no licence).
   GraphRAG-Benchmark, LongMemEval, MemoryAgentBench, StarE, HYPER and Text2NKG are MIT (checked
   2026-09-23). HyperRED's repository has no licence file.
4. **Deterministic tie-breaking everywhere:** in the Hungarian alignment, the ranks and the bootstrap.
5. **Headline choice is a decision, not a default.** Every scorer here has at least two legitimate
   headline numbers that disagree by more than the effects being claimed (C4: 0.40 against 0.55).

---

## 8. Decisions for the design

Each gives options and a **Recommendation**. The structured summary returns the same list.

- **D-C5-01 Extraction scoring unit.** Options: whole fact (Text2NKG), quintuplet (HyperRED), binding
  (MUC-style). **Rec:** whole fact for E-M1, bindings under one alignment for Arg-I, Arg-C and role
  accuracy, and quintuplets only as a HyperRED preset.
- **D-C5-02 Alignment.** Options: none (pooled), greedy, Hungarian on binding overlap, Hungarian on value
  overlap with binding tie-break. **Rec:** the last one (E-M3), with lexicographic tie-breaks. The
  pooled score is kept as the grouping diagnostic.
- **D-C5-03 Entity matching.** Options: strings; canonical ids; SMATCH-style mapping of unlinked nodes.
  **Rec:** canonical ids required; linking scored as its own step; a mapping mode deferred to a minor
  version.
- **D-C5-04 Literal equality.** Options: exact; truncate-to-gold; partial credit for coarser values.
  **Rec:** truncate-to-gold default, exact as a preset, no partial credit in v1.
- **D-C5-05 Stability key and statistic.** Options: ATOM's run-1 anchor; mean pairwise Jaccard;
  gold-conditioned partition; churn. **Rec:** mean pairwise Jaccard, fact churn, gold partition and
  Δ_order, each on both the content key and the core key.
- **D-C5-06 Rank convention.** Options: optimistic, pessimistic, realistic, random with seeds, tie-exact
  expectation. **Rec:** tie-exact expectation as the C5 default, with the other three as an audit, and
  per-model presets for replication.
- **D-C5-07 MRR denominator.** **Rec:** report per task, per fact and macro-over-arity. Replication uses
  per task; new findings (P3b calibration, P8) lead with macro-over-arity.
- **D-C5-08 Filter semantics.** Options: exact; monotone; time-aware. **Rec:** exact default; monotone and
  time-aware reported whenever qualifiers or validity exist; set equality of bindings, never sequence
  equality.
- **D-C5-09 Calibration target.** Options: per triple with base rate (Tabacof); top-1 (Safavi); full
  distribution NLL. **Rec:** top-1 set-correctness ECE (15 bins, equal-width and equal-mass) plus Brier,
  per arity, with the score-to-probability map declared; per-triple Brier as an option.
- **D-C5-10 Model-to-scorer interface for completion.** Options: full score vectors; top-k lists; rank
  statistics. **Rec:** rank statistics produced with C5's filter index (§3.3).
- **D-C5-11 Retrieval unit and cross-condition comparability (P4).** **Rec:** units carry hyperedge
  back-pointers, and `binding_coverage@k` is the common scale across hyperedge, pair and chunk
  conditions.
- **D-C5-12 Support alternatives.** **Rec:** support is a list of alternative minimal sets; headline
  `support_success@k`; KILT recall only in the adapter.
- **D-C5-13 Answer typing.** **Rec:** systems return structured answers (ids and typed literals) plus
  text; deterministic scoring of the structured part; the LLM judge is only an adapter.
- **D-C5-14 Memory outcomes.** **Rec:** the O1 to O7 taxonomy, strict headline, lenient for
  LongMemEval comparability, stale split into expired and retracted (R04 M5).
- **D-C5-15 Question-set record shapes.** **Rec:** the §6 field list as the C4 question-set contract, with
  P3a filling it; `V_old` and `V_fut` mandatory on memory items.
- **D-C5-16 External adapters.** **Rec:** GraphRAG-Bench (Xiang et al., arXiv id and commit pinned), the
  LongMemEval KU subset, and LoCoMo run in place, not vendored. Native metrics are reported under
  native names.
- **D-C5-17 Assignment solver dependency.** Options: `metametric` (no licence); SciPy
  `linear_sum_assignment` (BSD); a small pure-Python Hungarian. **Rec:** a pure-Python implementation
  with SciPy optional for speed, and brute-force cross-checks in tests.
- **D-C5-18 Dispersion.** **Rec:** K ≥ 3 runs, a percentile bootstrap (1,000 resamples, fixed seed) over
  documents or items, and the paired bootstrap for comparisons.

---

## 9. Risks

1. **The P2 gate does not exercise C5** (R01 §1: the P2 row needs no C5). C5 can pass review untested and
   fail its first consumer. Mitigation: ship the §2.7, §3.7, §4.7 and §5.7 tables as the C5 test suite
   in P2.
2. **P3b's gate can fail on conventions, not models.** A C5 default (tie-exact expectation, set-based
   filter) will not reproduce published numbers that used pessimistic ties or ordered-qualifier filters.
   Presets are required.
3. **The arity definition drifts.** If C1's arity rule (R01 D-06), P3a's histogram and C5's bins differ,
   every per-arity number is incomparable.
4. **Gold incompleteness** makes P9's precision pessimistic and its role accuracy computed on a biased
   subset (only the aligned facts).
5. **The linking step dominates.** If extractors emit strings, extraction scores measure the linker.
6. **Calibration may be ill-posed.** Many n-ary models emit unnormalised scores, and calibration then
   depends on a temperature someone chose.
7. **Memory scoring of text-only baselines** falls back to alias matching or an LLM judge, which weakens
   P7's comparison exactly where the flat baseline is involved.
8. **Question-set bias.** Templated questions from the same corpus measure index alignment (CRH §2.2).
   Without human verification and generator metadata, P4 and P10 inherit the hypergraph-RAG literature's
   weakness.
9. **External benchmarks shift.** LongMemEval was re-cleaned in September 2025, and LoCoMo's release
   shrank from 50 to 10 conversations. Numbers without a data version are not reproducible.

---

## 10. Open questions raised (proposed for the register; not added)

- [05.x] Does qualifier-monotone filtering change the ranking of n-ary link predictors, and how many
  "errors" on WD50K are entailed true answers?
- [05.x] Is n-ary link prediction worse calibrated at higher arity once probabilities come from a fitted
  map rather than a raw softmax?
- [03.x] How much of LLM n-ary extraction instability is order sensitivity (Δ_order) rather than sampling
  noise (J_within)?
- [03.x] What share of role errors are swaps within the same fact (Arg-I correct, Arg-C wrong) against
  wrong fillers?
- [07.x] Do memory systems fail supersession more by staleness (valid time) or by uncorrected belief
  (retraction), and does a key-role declaration reduce either?

---

## Sources

### Knowledge-base notes and project reports (this repository, read 2026-09-23)

- `kb/05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md` (BEP)
- `kb/05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md` (RNP)
- `kb/05-query-embeddings-reasoning/explainability-and-uncertainty.md` (XAI)
- `kb/03-construction/evaluation-of-constructed-khgs.md` (EVC)
- `kb/03-construction/n-ary-relation-extraction-from-text.md` (NXT)
- `kb/03-construction/skill-driven-extraction-and-the-scenario-gap.md` (SKL)
- `kb/07-applications/retrieval-augmented-generation.md` (RAG)
- `kb/10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md` (CRH)
- `kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md` (TMP)
- `kb/07-applications/ai-agents-memory-and-planning.md` (AGT)
- `kb/08-history-and-frontier/composed-stack-and-research-bets.md` (CST)
- `kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md` (SCH §6.2, value encoding)
- `kb/10-comparative-and-critique/limitations-and-failure-modes.md` (LIM §8, grouping accuracy)
- `projects/p2-role-aware-hif/research/01-requirements-from-kb.md` (R01)
- `projects/p2-role-aware-hif/research/04-prior-art-modelling.md` (R04)

### Extraction and stability

- Chia, Y. K., Bing, L., Aljunied, S. M., Si, L., Poria, S. "A Dataset for Hyper-Relational Extraction and a Cube-Filling Approach." EMNLP 2022; arXiv:2211.10018. https://arxiv.org/abs/2211.10018 — code: declare-lab/HyperRED, `scoring.py`, commit `17ba7b6` (2022-12-13). https://github.com/declare-lab/HyperRED
- Luo, H., E, H., Yang, Y., Yao, T., et al. "Text2NKG: Fine-Grained N-ary Relation Extraction for N-ary relational Knowledge Graph Construction." NeurIPS 2024; arXiv:2310.05185. https://arxiv.org/abs/2310.05185 — code: LHRLAB/Text2NKG, `run_re.py`, commit `f538a99` (2025-08-18). https://github.com/LHRLAB/Text2NKG
- Josifoski, M., De Cao, N., Peyrard, M., Petroni, F., West, R. "GenIE: Generative Information Extraction." NAACL 2022, pp. 4626–4643. https://aclanthology.org/2022.naacl-main.342/
- Yao, Y., Ye, D., Li, P., Han, X., et al. "DocRED: A Large-Scale Document-Level Relation Extraction Dataset." ACL 2019. https://aclanthology.org/P19-1074/
- Chinchor, N. "MUC-4 Evaluation Metrics." Fourth Message Understanding Conference (MUC-4), 1992. https://aclanthology.org/M92-1002/
- Chen, Y., Gantt, W., Chen, T., White, A. S., Van Durme, B. "A Unified View of Evaluation Metrics for Structured Prediction." EMNLP 2023; arXiv:2310.13793. https://arxiv.org/abs/2310.13793 — library wanmok/metametric, commit `532afe5` (2025-11-03), no licence file (checked 2026-09-23). https://github.com/wanmok/metametric
- Jain, S., van Zuylen, M., Hajishirzi, H., Beltagy, I. "SciREX: A Challenge Dataset for Document-Level Information Extraction." ACL 2020, pp. 7506–7516. https://aclanthology.org/2020.acl-main.670/
- Huang, R., Feng, Y., Xue, R., Ying, S., Yong, J.-H., Shi, C., Du, S., Gao, Y. "Hyper-KGGen: A Skill-Driven Knowledge Extractor for High-Quality Knowledge Hypergraph Generation." arXiv:2602.19543, 2026. https://arxiv.org/abs/2602.19543
- Li, Q., Ji, H., Huang, L. "Joint Event Extraction via Structured Prediction with Global Features." ACL 2013, pp. 73–82. https://aclanthology.org/P13-1008/
- Li, S., Ji, H., Han, J. "Document-Level Event Argument Extraction by Conditional Generation." NAACL 2021, pp. 894–908. https://aclanthology.org/2021.naacl-main.69/
- Peng, H., Wang, X., Yao, F., Zeng, K., Hou, L., Li, J., Liu, Z., Shen, W. "The Devil is in the Details: On the Pitfalls of Event Extraction Evaluation." Findings of ACL 2023; arXiv:2306.06918. https://arxiv.org/abs/2306.06918
- Taillé, B., Guigue, V., Scoutheeten, G., Gallinari, P. "Let's Stop Incorrect Comparisons in End-to-end Relation Extraction!" EMNLP 2020, pp. 3689–3701. https://aclanthology.org/2020.emnlp-main.301/
- Ho, X., Duong Nguyen, A.-K., Sugawara, S., Aizawa, A. "Constructing A Multi-hop QA Dataset for Comprehensive Evaluation of Reasoning Steps." COLING 2020, pp. 6609–6625. https://aclanthology.org/2020.coling-main.580/
- Gashteovski, K., Yu, M., Kotnis, B., Lawrence, C., Niepert, M., Glavaš, G. "BenchIE: A Framework for Multi-Faceted Fact-Based Open Information Extraction Evaluation." ACL 2022. https://aclanthology.org/2022.acl-long.307/
- Lairgi, Y., Moncla, L., Benabdeslem, K., Cazabet, R., Cléau, P. "ATOM: AdapTive and OptiMized dynamic temporal knowledge graph construction using LLMs." EACL 2026; arXiv:2510.22590. https://arxiv.org/abs/2510.22590
- Milani Fard, M., Cormier, Q., Canini, K., Gupta, M. "Launch and Iterate: Reducing Prediction Churn." NeurIPS 2016, pp. 3171–3179. https://proceedings.neurips.cc/paper/2016/hash/dc5c768b5dc76a084531934b34601977-Abstract.html
- Atil, B., Aykent, S., Chittams, A., Fu, L., Passonneau, R. J., et al. "Non-Determinism of 'Deterministic' LLM Settings." arXiv:2408.04667 (v5, 2 Apr 2025). https://arxiv.org/abs/2408.04667
- Wikibase DataModel (time precision and quantity), MediaWiki, checked 2026-09-23. https://www.mediawiki.org/wiki/Wikibase/DataModel

### Completion and calibration

- Bordes, A., Usunier, N., Garcia-Durán, A., Weston, J., Yakhnenko, O. "Translating Embeddings for Modeling Multi-relational Data." NIPS 2013. https://papers.nips.cc/paper_files/paper/2013/hash/1cecc7a77928ca8133fa24680a88d2f9-Abstract.html
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137 — code: ServiceNow/HypE, `tester.py` and `measure.py`, commit `2fecf70` (2022-07-15). https://github.com/ServiceNow/HypE
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs." EMNLP 2020; arXiv:2009.10847. https://arxiv.org/abs/2009.10847 — code: migalkin/StarE, `loops/evaluation.py`, `run.py`, `data_loaders/data_manager.py`, commit `b294b9e` (2023-12-01). https://github.com/migalkin/StarE
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. "HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs." ICLR 2026; arXiv:2506.12362. https://arxiv.org/abs/2506.12362 — code: HxyScotthuang/HYPER, `hyper/tasks.py`, commit `14697d8` (2026-03-25). https://github.com/HxyScotthuang/HYPER
- Wang, Q., Wang, H., Lyu, Y., Zhu, Y. "Link Prediction on N-ary Relational Facts: A Graph-based Approach." Findings of ACL 2021; arXiv:2105.08476. https://arxiv.org/abs/2105.08476
- Han, Z., Chen, P., Ma, Y., Tresp, V. "Explainable Subgraph Reasoning for Forecasting on Temporal Knowledge Graphs" (xERTE). ICLR 2021; arXiv:2012.15537. https://arxiv.org/abs/2012.15537
- Hou, Z., Su, M., Jin, X., Li, Z., Bai, L., Guo, J., Cheng, X. "Mixture Policy based Multi-Hop Reasoning over N-tuple Temporal Knowledge Graphs" (MT-Path). arXiv:2505.12788, 19 May 2025. https://arxiv.org/abs/2505.12788
- Ding, Z., Wu, J., Wu, J., Xia, Y., Tresp, V. "Temporal Fact Reasoning over Hyper-Relational Knowledge Graphs" (HypeTKG). Findings of EMNLP 2024; arXiv:2307.10219. https://arxiv.org/abs/2307.10219
- Xiong, B., Nayyeri, M., Pan, S., Staab, S. "Shrinking Embeddings for Hyper-Relational Knowledge Graphs." ACL 2023, pp. 13306–13320. https://aclanthology.org/2023.acl-long.743/
- Sun, Z., Vashishth, S., Sanyal, S., Talukdar, P., Yang, Y. "A Re-evaluation of Knowledge Graph Completion Methods." ACL 2020, pp. 5516–5522; arXiv:1911.03903. https://aclanthology.org/2020.acl-main.489/
- Berrendorf, M., Faerman, E., Vermue, L., Tresp, V. "On the Ambiguity of Rank-Based Evaluation of Entity Alignment or Link Prediction Methods" (earlier title: "Interpretable and Fair Comparison of Link Prediction or Entity Alignment Methods with Adjusted Mean Rank"). arXiv:2002.06914 (rev. 19 Sep 2023). https://arxiv.org/abs/2002.06914
- Hoyt, C. T., Berrendorf, M., Galkin, M., Tresp, V., Gyori, B. M. "A Unified Framework for Rank-based Evaluation Metrics for Link Prediction in Knowledge Graphs." GLB Workshop @ WebConf 2022; arXiv:2203.07544. https://arxiv.org/abs/2203.07544
- PyKEEN, `src/pykeen/evaluation/ranks.py`, `src/pykeen/metrics/ranking.py`, `src/pykeen/typing.py`, commit `fb81ffe` (version 1.11.2-dev), read 2026-09-23. https://github.com/pykeen/pykeen ; docs https://pykeen.readthedocs.io/en/stable/tutorial/understanding_evaluation.html
- Guo, C., Pleiss, G., Sun, Y., Weinberger, K. Q. "On Calibration of Modern Neural Networks." ICML 2017; arXiv:1706.04599. https://arxiv.org/abs/1706.04599
- Pakdaman Naeini, M., Cooper, G., Hauskrecht, M. "Obtaining Well Calibrated Probabilities Using Bayesian Binning." AAAI 2015, 29(1):2901–2907 (metadata checked; text not read). https://ojs.aaai.org/index.php/AAAI/article/view/9602
- Nixon, J., Dusenberry, M., Jerfel, G., Nguyen, T., Liu, J., Zhang, L., Tran, D. "Measuring Calibration in Deep Learning." arXiv:1904.01685 (rev. 7 Aug 2020). https://arxiv.org/abs/1904.01685
- Tabacof, P., Costabello, L. "Probability Calibration for Knowledge Graph Embedding Models." ICLR 2020; arXiv:1912.10000. https://arxiv.org/abs/1912.10000
- Safavi, T., Koutra, D., Meij, E. "Evaluating the Calibration of Knowledge Graph Embeddings for Trustworthy Link Prediction." EMNLP 2020; arXiv:2004.01168. https://arxiv.org/abs/2004.01168
- Brier, G. W. "Verification of forecasts expressed in terms of probability." Monthly Weather Review 78(1):1–3, 1950 (metadata checked; text not accessible). https://journals.ametsoc.org/view/journals/mwre/78/1/1520-0493_1950_078_0001_vofeit_2_0_co_2.xml

### Retrieval and answers

- Voorhees, E. M., Tice, D. M. "The TREC-8 Question Answering Track." LREC 2000. http://www.lrec-conf.org/proceedings/lrec2000/pdf/26.pdf
- Petroni, F., Piktus, A., Fan, A., Lewis, P., Yazdani, M., De Cao, N., Thorne, J., Jernite, Y., Karpukhin, V., Maillard, J., Plachouras, V., Rocktäschel, T., Riedel, S. "KILT: a Benchmark for Knowledge Intensive Language Tasks." NAACL 2021; arXiv:2009.02252 (v4). https://arxiv.org/abs/2009.02252 — code: facebookresearch/KILT, `kilt/eval_retrieval.py`, `kilt/eval_downstream.py`, commit `2664322`. https://github.com/facebookresearch/KILT
- Yang, Z., Qi, P., Zhang, S., Bengio, Y., Cohen, W. W., Salakhutdinov, R., Manning, C. D. "HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering." EMNLP 2018; arXiv:1809.09600. https://arxiv.org/abs/1809.09600 — script: hotpotqa/hotpot, `hotpot_evaluate_v1.py`, commit `3635853`. https://github.com/hotpotqa/hotpot
- Rajpurkar, P., Zhang, J., Lopyrev, K., Liang, P. "SQuAD: 100,000+ Questions for Machine Comprehension of Text." EMNLP 2016; arXiv:1606.05250. https://arxiv.org/abs/1606.05250
- Gu, Y., Kase, S., Vanni, M., Sadler, B., Liang, P., Yan, X., Su, Y. "Beyond I.I.D.: Three Levels of Generalization for Question Answering on Knowledge Bases" (GrailQA). WWW 2021; arXiv:2011.07743. https://arxiv.org/abs/2011.07743
- Xiang, Z., Wu, C., Zhang, Q., Chen, S., Hong, Z., Huang, X., Su, J. "When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation." ICLR 2026; arXiv:2506.05690. https://arxiv.org/abs/2506.05690 — code: GraphRAG-Bench/GraphRAG-Benchmark (MIT), `Evaluation/metrics/*.py`, `Evaluation/generation_eval.py`, commit `fdbab59` (2026-06-07). https://github.com/GraphRAG-Bench/GraphRAG-Benchmark
- Xiao, Y., Dong, J., Zhou, C., Dong, S., Zhang, Q., Yin, D., Sun, X., Huang, X. "GraphRAG-Bench: Challenging Domain-Specific Reasoning for Evaluating Graph Retrieval-Augmented Generation." arXiv:2506.02404 (v3, 20 Jun 2025). https://arxiv.org/abs/2506.02404
- Koehn, P. "Statistical Significance Tests for Machine Translation Evaluation." EMNLP 2004, pp. 388–395 (metadata checked). https://aclanthology.org/W04-3250/
- scikit-learn 1.9.1, `sklearn.metrics._ranking._dcg_sample_scores` (discount `1/log2(i+1)`), inspected 2026-09-23. https://scikit-learn.org/

### Memory

- Wu, D., Wang, H., Yu, W., Zhang, Y., Chang, K.-W., Yu, D. "LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory." ICLR 2025; arXiv:2410.10813. https://arxiv.org/abs/2410.10813 — code: xiaowu0162/LongMemEval (MIT), `src/evaluation/evaluate_qa.py`, `print_qa_metrics.py`, `src/retrieval/eval_utils.py`, commit `9e0b455` (2026-05-11). https://github.com/xiaowu0162/LongMemEval — data: `longmemeval_oracle.json`, Hugging Face `xiaowu0162/longmemeval-cleaned` (card licence MIT, last modified 2025-09-19), downloaded 2026-09-23. https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned
- Wu, D., Ji, Z., Kawatkar, A., Kwan, B., Gu, J.-C., Peng, N., Chang, K.-W. "LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues." arXiv:2605.12493, 12 May 2026 (abstract and README only). https://arxiv.org/abs/2605.12493 ; https://github.com/xiaowu0162/LongMemEval-V2
- Maharana, A., Lee, D.-H., Tulyakov, S., Bansal, M., Barbieri, F., Fang, Y. "Evaluating Very Long-Term Conversational Memory of LLM Agents" (LoCoMo). arXiv:2402.17753, 2024. https://arxiv.org/abs/2402.17753 — code and data: snap-research/locomo, `task_eval/evaluation.py`, `data/locomo10.json`, commit `3eb6f2c` (2024-08-12), licence CC BY-NC 4.0. https://github.com/snap-research/locomo
- Hu, Y., Wang, Y., McAuley, J. "Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions" (MemoryAgentBench). ICLR 2026; arXiv:2507.05257 (v1 7 Jul 2025; v4 28 Jun 2026). https://arxiv.org/abs/2507.05257 — code: HUST-AI-HYZ/MemoryAgentBench (MIT), `utils/eval_other_utils.py`, commit `fe1735d` (2026-08-20). https://github.com/HUST-AI-HYZ/MemoryAgentBench
- Kim, Y., Yoon, J., Ye, S., Bae, S., Ho, N., Hwang, S. J., Yun, S.-Y. "Carpe Diem: On the Evaluation of World Knowledge in Lifelong Language Models" (EvolvingQA). NAACL 2024, pp. 5401–5415; arXiv:2311.08106. https://aclanthology.org/2024.naacl-long.302/
- Meng, K., Bau, D., Andonian, A., Belinkov, Y. "Locating and Editing Factual Associations in GPT" (ROME, CounterFact). NeurIPS 2022; arXiv:2202.05262. https://arxiv.org/abs/2202.05262
- Dhingra, B., Cole, J. R., Eisenschlos, J. M., Gillick, D., Eisenstein, J., Cohen, W. W. "Time-Aware Language Models as Temporal Knowledge Bases" (TempLAMA). TACL 2022; arXiv:2106.15110. https://arxiv.org/abs/2106.15110
- Zhang, M. J. Q., Choi, E. "SituatedQA: Incorporating Extra-Linguistic Contexts into QA." EMNLP 2021; arXiv:2109.06157. https://arxiv.org/abs/2109.06157
- Chhikara, P., Khant, D., Aryan, S., Singh, T., Yadav, D. "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory." arXiv:2504.19413, 2025. https://arxiv.org/abs/2504.19413
