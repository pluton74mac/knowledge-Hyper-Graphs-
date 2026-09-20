---
title: Explainability and uncertainty for n-ary link prediction
type: survey
status: draft
tags: [explainability, interpretability, uncertainty, calibration, noise, hypermln, nylon, ukge, cardinality-estimation, provenance]
created: 2026-09-20
updated: 2026-09-20
---

# Explainability and uncertainty for n-ary link prediction

The weakest part of the knowledge-hypergraph literature, and the field says so itself. This note
records what exists, what is borrowed from the binary case, and what is simply missing.

Related: [logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md),
[benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md).

---

## 1. The state of explainability, stated by the field

> "HyperMLN is the only method that explicitly addresses explainability in link prediction in NKGs"
> — [Wei, Guan, Li, Jin, Guo and Cheng, *A Survey of Link Prediction in N-ary Knowledge Graphs*,
> arXiv:2506.08970, 2025](https://arxiv.org/abs/2506.08970), §6.3

One method out of nearly fifty. The survey's recommendation is that "explainability should move
beyond rule extraction to encompass broader interpretable reasoning, such as causal attribution and
counterfactual analysis" (ibid.).

### HyperMLN

A Markov logic network adapted to n-ary facts, coupled to a knowledge-hypergraph embedding by a
variational EM loop: the E-step distils the symbolic knowledge into the embeddings, the M-step
updates the logic-rule weights and model parameters. The explanation is the set of weighted
first-order rules that fired ([Chen, Wang, Wang and Li, *Explainable Link Prediction in Knowledge
Hypergraphs*, CIKM 2022](https://doi.org/10.1145/3511808.3557316)).

Its acknowledged weakness is that it "is sensitive to the coverage and quality of the mined logic
rules", and the rules are **predefined** rather than discovered at n-ary arity — which loops back to
the missing "AMIE for hyperedges"
([logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md) §3).

## 2. Four kinds of explanation, and where each stands

| Kind | Question answered | Status for n-ary facts |
|---|---|---|
| **Rule-based** | which rule licensed this? | HyperMLN only |
| **Path/subgraph** | which existing facts support this? | none found; the natural object is a **B-hyperpath** (see below) |
| **Attribution** | which *element* of the fact drove the score? | partially, via NYLON's element confidence |
| **Counterfactual** | what would change the prediction? | none found; named as future work by the survey |

### The hyperpath opening

A derivation over Horn rules *is* a B-hyperpath, and enumerating s-t hyperpaths on a B-hypergraph
"can be solved in polynomial delay by backtracking" ([Kurita and Mann,
arXiv:2507.07528, 2025](https://arxiv.org/abs/2507.07528)). So the tractable explanation primitive
exists on the symbolic side and no one has connected it to the neural side. For graphs the analogous
connection was made by GNNExplainer, which extracts a compact subgraph plus feature subset
explaining a GNN prediction ([Ying, Bourgeois, You, Zitnik and Leskovec, *GNNExplainer: Generating
Explanations for Graph Neural Networks*, NeurIPS 2019 /
arXiv:1903.03894](https://arxiv.org/abs/1903.03894)). A "HyperedgeExplainer" — a minimal set of
hyperedges whose removal flips a prediction — appears to be an unclaimed, well-posed problem.
`[unverified — no such work found as of September 2026]`

### The role-attribution opening, specific to n-ary facts

Binary link prediction has two things to attribute to; a 6-ary fact has six, plus the relation. The
question "which qualifier made this prediction" has no analogue in the triple setting and is
directly useful — it is also, conveniently, cheap to approximate by ablating one role-value pair at a
time and re-scoring. Several models are built on machinery that would support it: ShrinkE's boxes
shrink per qualifier and HyperMono's cone angle narrows per qualifier, so the *geometric* magnitude
of each qualifier's effect is already computed
([knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md) §3). Neither
paper reports it as an explanation. That is a small, tractable piece of work.

## 3. Uncertainty

### Noisy facts: NYLON

The one model in this literature that treats confidence as a first-class output. NYLON extends GRAN
to noisy n-ary knowledge graphs, using "a Transformer with learnable edge biases to compute **fact
confidence and element confidence**", and drives "efficient selective annotation" from those
confidences — i.e. active learning: ask a human about the facts the model is least sure of
([Yu, Yang and Yang, *Robust Link Prediction over Noisy Hyper-Relational Knowledge Graphs via Active
Learning*, WWW 2024](https://doi.org/10.1145/3589334.3645686); description from
[Wei et al. 2025](https://arxiv.org/abs/2506.08970) §3.3.3).

Element-level confidence is the interesting part: it says *which participant of the fact* is likely
wrong, which is both an uncertainty estimate and an attribution.

### Uncertain knowledge bases: the binary precedent

For triples there is a developed line on knowledge bases whose facts carry confidence scores — UKGE
embeds uncertain knowledge graphs and predicts confidence rather than a binary truth value
([Chen, Chen, Shi, Sun and Zaniolo, *Embedding Uncertain Knowledge Graphs*, AAAI
2019](https://doi.org/10.1609/aaai.v33i01.33013363)). **No n-ary counterpart was found for this
note.** An uncertain knowledge hypergraph is a natural object — extraction pipelines
([construction-pipeline-overview.md](../03-construction/construction-pipeline-overview.md)) produce
confidence per fact, and n-ary facts extracted from text are *more* likely to be partially wrong
because there are more slots to get wrong. `[unverified — apparent gap]`

### Calibration

Ranking metrics say nothing about whether a score is a probability. For binary KG embeddings, Tabacof
and Costabello showed that off-the-shelf models are poorly calibrated and that Platt scaling and
isotonic regression fix much of it ([Tabacof and Costabello, *Probability Calibration for Knowledge
Graph Embedding Models*, ICLR 2020 / arXiv:1912.10000](https://arxiv.org/abs/1912.10000)).

**No calibration study of n-ary link predictors was found.** This matters more than in the binary
case for two reasons:

1. The evaluation protocol averages over *prediction tasks*, which reweights by arity
   ([benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md) §1), so an
   aggregate score can hide systematically miscalibrated high-arity predictions.
2. Downstream use is increasingly retrieval for an LLM
   ([llm-and-khg-interaction.md](llm-and-khg-interaction.md)), where a miscalibrated score becomes a
   confidently wrong generation.

`[unverified — apparent gap]`

### Uncertainty about *query answers*

A different and more tractable target: estimating how many answers a hyper-relational query has,
before running it. This is being studied as cardinality estimation ([Teng, Li, Di and Chen,
*Cardinality Estimation on Hyper-relational Knowledge Graphs*, arXiv:2405.15231,
2024](https://arxiv.org/abs/2405.15231)) and it is also the classical worst-case bound given by the
fractional edge cover of the query hypergraph
([query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md) §10.2).

## 4. Provenance is not uncertainty, and the standards keep them apart

RDF 1.2's design deliberately separates *stating that a triple exists* from *asserting it*: there is
no entailment pattern by which a reifying triple entails the reified triple
([RDF 1.2 Semantics, W3C Candidate Recommendation, 7 April
2026](https://www.w3.org/TR/rdf12-semantics/)); the same choice was made in RDF 1.1, where "a
reification of a triple does not entail the triple, and is not entailed by it"
([RDF 1.1 Semantics, 2014](https://www.w3.org/TR/rdf11-mt/)). This is exactly the hook you want for
attaching a confidence, a source and an extraction timestamp to an n-ary fact without asserting it.
Nothing in the embedding literature consumes that structure.

## 5. A short agenda

1. **Element-level attribution** by qualifier ablation, reported as a standard diagnostic — cheap,
   and the geometry is already there in ShrinkE and HyperMono.
2. **Hyperedge-level counterfactuals**: the minimal set of facts whose removal flips a prediction.
3. **Calibration curves** alongside MRR in every n-ary link-prediction paper, stratified by arity.
4. **An uncertain-KHG benchmark**: facts with confidence scores from a real extraction pipeline, with
   the task of predicting confidence rather than rank.
5. **Connect hyperpath enumeration to neural scores**, using the polynomial-delay B-hypergraph result
   as the enumeration engine and the model as the scorer.

## Open questions raised here

- Does the geometric shrinkage in ShrinkE / HyperMono correlate with a qualifier's causal
  contribution, or is it an artefact of training?
- Are n-ary link predictors *more* miscalibrated at higher arity, as the compounding of uncertain
  slots would suggest?
- Can NYLON's element confidence be repurposed as an explanation ("this fact is probably wrong *at
  this role*") and evaluated as such?
- What is the right ground truth for an n-ary explanation — a rule, a hyperpath, a set of supporting
  facts, or a role attribution? There is no agreed evaluation.

## Sources

- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs*. arXiv:2506.08970, 2025; EMNLP 2025. <https://arxiv.org/abs/2506.08970>
- Chen, Z., Wang, X., Wang, C., Li, J. "Explainable Link Prediction in Knowledge Hypergraphs" (HyperMLN). *CIKM 2022*. <https://doi.org/10.1145/3511808.3557316>
- Yu, W., Yang, J., Yang, D. "Robust Link Prediction over Noisy Hyper-Relational Knowledge Graphs via Active Learning" (NYLON). *WWW 2024*. <https://doi.org/10.1145/3589334.3645686>
- Chen, X., Chen, M., Shi, W., Sun, Y., Zaniolo, C. "Embedding Uncertain Knowledge Graphs". *AAAI 2019*. <https://doi.org/10.1609/aaai.v33i01.33013363>
- Tabacof, P., Costabello, L. *Probability Calibration for Knowledge Graph Embedding Models*. ICLR 2020; arXiv:1912.10000. <https://arxiv.org/abs/1912.10000>
- Ying, R., Bourgeois, D., You, J., Zitnik, M., Leskovec, J. *GNNExplainer: Generating Explanations for Graph Neural Networks*. NeurIPS 2019; arXiv:1903.03894. <https://arxiv.org/abs/1903.03894>
- Kurita, K., Mann, K. *On the Complexity of Hyperpath and Minimal Separator Enumeration in Directed Hypergraphs*. arXiv:2507.07528, 2025. <https://arxiv.org/abs/2507.07528>
- Teng, F., Li, H., Di, S., Chen, L. *Cardinality Estimation on Hyper-relational Knowledge Graphs*. arXiv:2405.15231, 2024. <https://arxiv.org/abs/2405.15231>
- Patel-Schneider, P., Franconi, E., Arndt, D. *RDF 1.2 Semantics*. W3C Candidate Recommendation, 7 April 2026. <https://www.w3.org/TR/rdf12-semantics/>
- Hayes, P., Patel-Schneider, P. (eds.) *RDF 1.1 Semantics*. W3C Recommendation, 25 February 2014. <https://www.w3.org/TR/rdf11-mt/>
