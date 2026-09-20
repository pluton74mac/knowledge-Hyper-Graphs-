---
title: Open world, closed world and uncertainty in knowledge hypergraphs
type: survey
status: draft
tags: [open-world, closed-world, pca, lcwa, uncertainty, probabilistic, markov-logic, psl, ukge, confidence, negation]
created: 2026-09-20
updated: 2026-09-20
---

# Open world, closed world and uncertainty

A knowledge hypergraph is a set of facts asserted to hold. Two questions follow immediately and are
answered inconsistently across the literature:

- **What does the absence of a hyperedge mean?** Nothing (open world), falsity (closed world), or
  falsity only in a restricted region (local closed world / partial completeness)?
- **What does a number attached to a hyperedge mean?** A probability, a degree of truth, a
  retrieval score, an editorial preference — or nothing comparable across systems?

This note collects the answers with citations, shows where hypergraph structure enters the
probabilistic-logic formalisms (Markov logic networks, probabilistic soft logic), and flags what is
*not* settled for n-ary data specifically. The schema-level consequences are in
[knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md).

## 1. The three assumptions

**Closed world assumption (CWA).** A fact not present is false. Standard in databases; standard in
MLN weight learning: "We make a closed world assumption (Genesereth & Nilsson, 1987): if a ground
atom is not in the database, it is assumed to be false"
([Richardson and Domingos, 2006](https://doi.org/10.1007/s10994-006-5833-1)).

**Open world assumption (OWA).** A fact not present is unknown. This is what RDF-based KBs do, and
AMIE states the consequence crisply:

> "Under the OWA, a statement that is not contained in the KB is not necessarily false; it is just
> unknown. This is a crucial difference to many standard database settings that operate under the
> Closed World Assumption (CWA). Consider an example KB that does not contain the information that a
> particular person is married. Under CWA we can conclude that the person is not married. Under OWA,
> however, the person could be either married or single."
> ([Galárraga et al., 2013](https://luisgalarraga.de/docs/amie.pdf), WWW 2013)

AMIE also notes why OWA is a problem for learning: "they usually require negative statements as
counter-examples. Semantic KBs, however, usually do not contain negative statements. The semantics
of RDF are too weak to deduce negative evidence from the facts in a KB" (same source). RDF's
entailment regimes are required to be monotonic — "All entailment regimes MUST be monotonic
extensions of the simple entailment regime" ([RDF 1.1 Semantics](https://www.w3.org/TR/rdf11-mt/))
— so adding facts never retracts a conclusion, and absence can never be read as negation.

**Partial completeness assumption (PCA), a.k.a. local closed world.** AMIE's middle ground:

> "We propose to generate negative evidence by the partial completeness assumption (PCA). This is
> the assumption that if r(x, y) ∈ KB_true for some x, y, then ∀y′ : r(x, y′) ∈ KB_true ∪ NEW_true
> ⇒ r(x, y′) ∈ KB_true. In other words, we assume that if the database knows some r-attribute of x,
> then it knows all r-attributes of x."
> ([Galárraga et al., 2013](https://luisgalarraga.de/docs/amie.pdf))

PCA confidence normalises "not by the entire set of facts, but by the set of facts of which we know
that they are true, together with the facts of which we assume that they are false" (same source).

**Open question for hypergraphs.** PCA is stated for binary `r(x, y)`. Its n-ary generalisation is
ambiguous: if the KB knows one binding of a role set for a subject, does it know *all* bindings of
*that* role set, or of any superset? No formulation of PCA for n-ary or hyper-relational facts was
found in a primary source during this research run `[unverified]`.

## 2. What the KHG embedding literature actually assumes

The canonical n-ary formulation is explicitly closed-world *at the level of an idealised world*, and
open-world at the level of the observed graph:

> "A world specifies what is true: all the tuples in τ are true, and the tuples that are not in τ
> are false. A knowledge hypergraph consists of a subset of the tuples τ′ ⊆ τ."
> ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137))

So the task "knowledge hypergraph completion" is: recover τ from τ′. Training uses negative sampling
(corrupt one argument of a true tuple), which is a *local* closed-world device: the corrupted tuple
is assumed false because it is absent. Evaluation uses the "filtered" protocol, removing other known
true tuples from the candidate ranking.

Two consequences specific to hyperedges:

1. **Negative sampling is position-dependent.** Corrupting the `recipient` role of an
   `award_received` fact and corrupting its `point_in_time` qualifier are not equally informative,
   and papers differ in whether qualifier positions are corrupted at all. StarE, for example, "only
   focuses on modeling part of n-ary relational facts" and "fails to predict the missing role-entity
   pairs" ([Liu, Yao and Li, 2021](https://arxiv.org/abs/2104.09780)).
2. **Monotonicity gives a principled asymmetry.** Adding qualifiers "may only narrow down the answer
   set, but never enlarge it" ([Hu et al., 2024](https://arxiv.org/abs/2404.09848)). A model that
   respects this cannot treat a longer fact as a fresh unrelated tuple.

**Genuinely open-world completion** — predicting facts about entities never seen in training — was
posed for binary KGs by ConMask, which "relax[es] the closed-world assumption to develop an
Open-World Knowledge Graph Completion model capable of predicting relationships involving unseen
entities", borrowing "the idea of open-world assumption from probabilistic database literature"
([Shi and Weninger, 2018](https://arxiv.org/abs/1711.03438), AAAI 2018). Its definition adds a
superset `E_i ⊇ E` of entities and asks for triples over `E_i`. The n-ary analogue would have to
handle unseen *roles* as well as unseen entities; inductive n-ary link prediction is an active area
rather than a solved one.

## 3. Explicit negative and existential knowledge

Wikidata is the only large KB in this note that stores negation and existential claims as first-class
data. Its snak types are:

- `PropertyValueSnak` — "describes that an Entity has a certain Property with a given Value";
- `PropertySomeValueSnak` — "has some value for a certain Property, without saying anything about
  this value";
- `PropertyNoValueSnak` — "has no values for a certain Property".
  ([Wikibase/DataModel](https://www.mediawiki.org/wiki/Wikibase/DataModel), checked 2026-09-19)

A no-value snak is a closed-world statement *for one subject and one property*, asserted by an
editor rather than inferred from absence — effectively a hand-curated local closed world. Note that
the hyper-relational benchmarks throw this away: WikiPeople's construction removed "facts containing
'unknown value' or 'no value' elements" ([WikiPeople repository](https://github.com/gsp2014/WikiPeople),
checked 2026-09-20), so the benchmark is strictly less expressive than its source.

Wikidata **ranks** are also not truth values: "The preferred rank is assigned to the most current
statement or statements that best represent consensus", "The normal rank is assigned to all
statements by default", and "The deprecated rank is used for statements that are known to include
errors ... or that represent outdated knowledge"
([Help:Ranking](https://www.wikidata.org/wiki/Help:Ranking)). Deprecated ≠ false; it means recorded
and disfavoured.

## 4. Uncertain knowledge graphs

Some KBs attach a number to every fact. UKGE names the two families:

> "(i) Deterministic KGs, such as YAGO and FreeBase, consist of deterministic relation facts that
> describe semantic relations between entities; (ii) Uncertain KGs including ProBase, ConceptNet and
> NELL associate every relation fact with a confidence score that represents the likelihood of the
> relation fact to be true."
> ([Chen et al., 2019](https://arxiv.org/abs/1811.10667), AAAI 2019)

and defines the object:

> "An uncertain KG represents knowledge as a set of relations (R) defined over a set of entities
> (E). It consists of a set of weighted triples G = {(l, s_l)}. For each pair (l, s_l),
> l = (h, r, t) is a triple representing a relation fact ... and s_l ∈ [0,1]"
> ([Chen et al., 2019](https://arxiv.org/abs/1811.10667))

The central difficulty is exactly the open-world one, restated quantitatively:

> "Deterministic KG embedding methods assume that all unseen relation facts are false beliefs, and
> use negative sampling to add some of these false relations into training. One major challenge of
> learning embeddings for uncertain KGs, however, is to properly estimate the uncertainty of unseen
> triples, as simply treating their confidence score as 0 can no longer capture the subtle
> uncertainty." ([Chen et al., 2019](https://arxiv.org/abs/1811.10667))

UKGE's answer is to propagate confidence with PSL rules (§6). Its three datasets are all **binary**
([Chen et al., 2019](https://arxiv.org/abs/1811.10667), Table 1):

| Dataset | Source | Entities | Relations | Uncertain facts | Mean confidence |
|---|---|---|---|---|---|
| CN15k | ConceptNet | 15,000 | 36 | 241,158 | 0.629 |
| NL27k | NELL | 27,221 | 404 | 175,412 | 0.797 |
| PPI5k | STRING protein-protein interactions | 4,999 | 7 | 271,666 | 0.415 |

Note that the scores needed rescaling to be read as probabilities at all: "The original scores in
ConceptNet vary from 0.1 to 22 ... we first bound confidence scores to x ∈ [0.1, 3.0], and then
applied the min-max normalization on log x to map them into [0.1, 1.0]" (same source). An equivalent
uncertain *n-ary* benchmark was not found in this research run `[unverified]`.

Confidence on hyperedges does appear in the RAG-oriented knowledge hypergraphs: HyperGraphRAG gives
each hyperedge "a natural language description e_i^text, and a confidence score e_i^score ∈ (0,10]"
and each entity a score in `(0,100]`, both assigned by the extracting model
([Luo et al., 2025](https://arxiv.org/abs/2503.21322)). These are extraction-quality scores, not
calibrated probabilities, and should not be mixed with UKGE-style `[0,1]` values without a stated
mapping.

## 5. Markov logic networks: the hypergraph reading

An MLN attaches weights to first-order formulas, softening logical constraints:

> "A first-order KB can be seen as a set of hard constraints on the set of possible worlds: if a
> world violates even one formula, it has zero probability. The basic idea in MLNs is to soften
> these constraints: when a world violates one formula in the KB it is less probable, but not
> impossible."
> ([Richardson and Domingos, 2006](https://doi.org/10.1007/s10994-006-5833-1))

> "DEFINITION 4.1. A Markov logic network L is a set of pairs (F_i, w_i), where F_i is a formula in
> first-order logic and w_i is a real number. Together with a finite set of constants
> C = {c_1, c_2, ..., c_|C|}, it defines a Markov network M_{L,C} as follows: 1. M_{L,C} contains one
> binary node for each possible grounding of each predicate appearing in L ... 2. M_{L,C} contains
> one feature for each possible grounding of each formula F_i in L."
> ([Richardson and Domingos, 2006](https://doi.org/10.1007/s10994-006-5833-1))

The hypergraph enters through the *data*, not the model. Kok and Domingos state it directly:

> "A database can be viewed as a hypergraph with constants as nodes, and true ground atoms as
> hyperedges. Each hyperedge is labeled with a predicate symbol. Nodes (constants) are linked by a
> hyperedge (true ground atom) if and only if they appear as arguments in the hyperedge."
> ([Kok and Domingos, 2009](https://icml.cc/Conferences/2009/papers/576.pdf), ICML 2009)

with the hypergraph itself defined as "a pair (V, E) where V is a set of nodes, and E is a multiset
of labeled non-empty ordered subsets of V called hyperedges" — that is, definition (a) of
[what-is-a-knowledge-hypergraph.md](what-is-a-knowledge-hypergraph.md), a decade before the term
"knowledge hypergraph" was popularised for it by
[Fatemi et al., 2020](https://arxiv.org/abs/1906.00137). Their LHL algorithm *lifts* the hypergraph by "jointly
clustering the constants to form higher-level concepts", finds paths of hyperedges sharing nodes,
and variabilises those paths into candidate clauses
([Kok and Domingos, 2009](https://icml.cc/Conferences/2009/papers/576.pdf)).

So: a ground relational database **is** a labelled, ordered knowledge hypergraph; an MLN is a
weighted set of *patterns over* that hypergraph; and structure learning is hyperpath mining. This is
the closest thing the field has to a probabilistic semantics for n-ary facts, and it predates the
KHG embedding literature entirely.

**Caveat.** MLN weights are not probabilities of individual facts. A weight is a log-linear
parameter: "the higher the weight, the greater the difference in log probability between a world
that satisfies the formula and one that does not, other things being equal"
([Richardson and Domingos, 2006](https://doi.org/10.1007/s10994-006-5833-1)). Reading a hyperedge
weight as a confidence is a category error unless the model says otherwise.

## 6. Probabilistic soft logic and hinge-loss MRFs

PSL replaces Boolean truth with `[0,1]` degrees:

> "A PSL program consists of a set of first-order logic rules with conjunctive bodies and single
> literal heads. PSL takes the confidence from interval [0, 1] as the soft truth values for every
> atom. It uses Lukasiewics t-norm to determine to which degree a rule is satisfied."
> ([Chen et al., 2019](https://arxiv.org/abs/1811.10667), summarising PSL)

The underlying formalism is hinge-loss Markov random fields:

> "we introduce two new formalisms for modeling structured data ... The first, hinge-loss Markov
> random fields (HL-MRFs), is a new kind of probabilistic graphical model that generalizes different
> approaches to convex inference. ... The second new formalism, probabilistic soft logic (PSL), is a
> probabilistic programming language that makes HL-MRFs easy to define using a syntax based on
> first-order logic."
> ([Bach, Broecheler, Huang and Getoor, 2017](https://jmlr.org/papers/v18/15-631.html), JMLR 18(109):1–67)

Why this matters for KHGs: PSL rules are exactly directed hyperedges over atoms (conjunctive body →
single head; see
[directed-and-typed-hyperedges-for-knowledge.md](directed-and-typed-hyperedges-for-knowledge.md)),
and MAP inference is convex, so a soft-truth knowledge hypergraph can be reasoned over at scale.
UKGE uses PSL for precisely the open-world gap: "PSL is a framework for confidence reasoning that
propagates confidence of existing knowledge to unseen triples using soft logic"
([Chen et al., 2019](https://arxiv.org/abs/1811.10667)).

## 7. Comparison

| Formalism | Absence of a fact means | Number on a fact means | Native arity |
|---|---|---|---|
| RDF / OWL KB | unknown (OWA, monotonic) ([RDF 1.1 Semantics](https://www.w3.org/TR/rdf11-mt/)) | — | binary |
| Wikidata | unknown, unless a `novalue` snak says otherwise ([Wikibase/DataModel](https://www.mediawiki.org/wiki/Wikibase/DataModel)) | rank: editorial preference, not probability ([Help:Ranking](https://www.wikidata.org/wiki/Help:Ranking)) | statement + qualifiers |
| KHG completion (HypE, StarE, …) | false in the ideal world τ; missing in the observed τ′ ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)) | model score, uncalibrated | n-ary |
| Rule mining with PCA | false *within the known role region* ([Galárraga et al., 2013](https://luisgalarraga.de/docs/amie.pdf)) | PCA confidence of a rule | binary (n-ary generalisation open) |
| Uncertain KG (UKGE) | unknown; score must be *inferred*, not set to 0 ([Chen et al., 2019](https://arxiv.org/abs/1811.10667)) | likelihood of truth, `[0,1]` | binary |
| MLN | false, for weight learning ([Richardson and Domingos, 2006](https://doi.org/10.1007/s10994-006-5833-1)) | log-linear weight on a *formula*, not a fact | n-ary predicates |
| PSL / HL-MRF | soft truth value, default unobserved | degree of truth `[0,1]` ([Bach et al., 2017](https://jmlr.org/papers/v18/15-631.html)) | n-ary predicates |
| LLM-extracted KHG | unknown, no negative evidence | extraction confidence `(0,10]` ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)) | n-ary |

## 8. Practical guidance

1. **Record the semantics of the number with the number.** `{"value": 0.7, "scale": "probability"}`
   and `{"value": 7, "scale": "llm-extraction-0-10"}` are not the same field.
2. **Do not store inferred absence as a fact.** Store the assumption instead (which role sets are
   believed complete for which subjects), so PCA-style evaluation is reproducible.
3. **Distinguish "no value" from "not recorded".** Wikidata's `novalue` snak is the only widely
   deployed precedent; a KHG schema that lacks it cannot represent "this reaction has no catalyst".
4. **Beware benchmark leakage when measuring uncertainty.** JF17K's 44.5% test/train main-triple
   overlap ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)) inflates any confidence
   calibration measured on it; see
   [benchmarks-derived-from-freebase-and-wikidata.md](benchmarks-derived-from-freebase-and-wikidata.md).

## 9. Open problems

- A PCA/local-closed-world definition for n-ary and hyper-relational facts `[unverified]` — none
  found in the sources consulted.
- A public **uncertain n-ary** benchmark with calibrated confidences; existing uncertain KGs
  (ConceptNet, NELL-derived NL27k, ProBase) are binary
  ([Chen et al., 2019](https://arxiv.org/abs/1811.10667)).
- Whether qualifier monotonicity ([Hu et al., 2024](https://arxiv.org/abs/2404.09848)) can be turned
  into a *probabilistic* constraint (a longer fact's probability bounded by the shorter one's).
- Whether MLN-style semantics can be attached to hyper-relational facts where qualifiers are
  metadata rather than arguments — i.e. what a weight on a *reifier* would mean.

## Sources

- Galárraga, L., Teflioudi, C., Hose, K., Suchanek, F. M. *AMIE: Association Rule Mining under Incomplete Evidence in Ontological Knowledge Bases.* WWW 2013. DOI 10.1145/2488388.2488425. https://luisgalarraga.de/docs/amie.pdf
- W3C. *RDF 1.1 Semantics.* W3C Recommendation, 25 February 2014. https://www.w3.org/TR/rdf11-mt/
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137
- Shi, B., Weninger, T. *Open-World Knowledge Graph Completion.* AAAI 2018; arXiv:1711.03438. https://arxiv.org/abs/1711.03438
- Liu, Y., Yao, Q., Li, Y. *Role-Aware Modeling for N-ary Relational Knowledge Bases.* WWW 2021; arXiv:2104.09780. https://arxiv.org/abs/2104.09780
- Hu, Z., Gutiérrez-Basulto, V., Xiang, Z., Li, R., Pan, J. Z. *HyperMono: A Monotonicity-aware Approach to Hyper-Relational Knowledge Representation.* arXiv:2404.09848, 2024. https://arxiv.org/abs/2404.09848
- MediaWiki. *Wikibase/DataModel*, checked 2026-09-19. https://www.mediawiki.org/wiki/Wikibase/DataModel
- Wikidata. *Help:Ranking.* https://www.wikidata.org/wiki/Help:Ranking
- Guan, S., Jin, X., Wang, Y., Cheng, X. *WikiPeople: An n-ary relational dataset derived from Wikidata.* GitHub repository, checked 2026-09-20. https://github.com/gsp2014/WikiPeople
- Chen, X., Chen, M., Shi, W., Sun, Y., Zaniolo, C. *Embedding Uncertain Knowledge Graphs.* AAAI 2019; arXiv:1811.10667. https://arxiv.org/abs/1811.10667
- Luo, H., E, H., Chen, G., et al. *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation.* NeurIPS 2025; arXiv:2503.21322. https://arxiv.org/abs/2503.21322
- Richardson, M., Domingos, P. *Markov logic networks.* Machine Learning 62(1–2):107–136, 2006. DOI 10.1007/s10994-006-5833-1. https://doi.org/10.1007/s10994-006-5833-1
- Kok, S., Domingos, P. *Learning Markov Logic Network Structure via Hypergraph Lifting.* ICML 2009. https://icml.cc/Conferences/2009/papers/576.pdf
- Bach, S. H., Broecheler, M., Huang, B., Getoor, L. *Hinge-Loss Markov Random Fields and Probabilistic Soft Logic.* Journal of Machine Learning Research 18(109):1–67, 2017. https://jmlr.org/papers/v18/15-631.html
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020; arXiv:2009.10847. https://arxiv.org/abs/2009.10847
