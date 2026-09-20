---
title: Logical reasoning and rules over n-ary facts
type: survey
status: draft
tags: [reasoning, rules, datalog, horn, b-hypergraph, hyperpath, owl, rdf-star, rdf-1.2, rule-mining, complex-query-answering, starqe, nqe, sqe, lkhgt, neuro-symbolic]
created: 2026-09-20
updated: 2026-09-20
---

# Logical reasoning and rules over n-ary facts

Three traditions meet here, and they are usually written about separately:

- **Symbolic deduction** — Datalog and Horn rules over n-ary predicates, which is a solved and
  well-understood problem that the KHG literature mostly ignores.
- **Ontological reasoning** — OWL, RDF and now RDF 1.2 triple terms, where n-ary support is weak
  by design.
- **Learned reasoning** — complex query answering (CQA), where a neural model answers a first-order
  query over an incomplete hypergraph. This is where the recent work is.

Related: [query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md),
[knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md),
[hypergraph-algorithms-for-knowledge.md](hypergraph-algorithms-for-knowledge.md).

---

## 1. Horn rules *are* hyperedges

The cleanest structural fact in this note. A **directed hypergraph** has hyperarcs with a tail set
and a head set; a **B-arc** (backward arc) has a single head, and a **B-hypergraph** contains only
B-arcs ([Gallo, Longo, Pallottino and Nguyen, *Directed hypergraphs and applications*, *Discrete
Applied Mathematics* 42(2–3), 1993](https://doi.org/10.1016/0166-218x(93)90045-p); survey:
[Ausiello and Laura, *Directed hypergraphs: Introduction and fundamental algorithms — A survey*,
*Theoretical Computer Science*, 2016](https://doi.org/10.1016/j.tcs.2016.03.016)).

A definite Horn clause

```
h ← b₁ ∧ b₂ ∧ … ∧ b_k
```

is exactly a B-arc with tail {b₁,…,b_k} and head h. Therefore:

- **Forward chaining = B-connectivity.** The set of atoms derivable from a set of facts is the set of
  vertices B-reachable from them.
- **A proof is a B-hyperpath.** The minimal set of rule applications justifying a conclusion is a
  hyperpath, which is why "explain this inference" and "find a minimal hyperpath" are the same
  question. See [explainability-and-uncertainty.md](explainability-and-uncertainty.md).
- **Propositional Horn satisfiability is linear time**
  ([Dowling and Gallier, *Journal of Logic Programming* 1(3),
  1984](https://doi.org/10.1016/0743-1066(84)90014-1)) — i.e. the reachability side of this
  correspondence is cheap.

What is *not* cheap is enumerating or optimising over hyperpaths. The sharpest recent statement:
"there are no output-polynomial time algorithms for the enumeration of induced s-t hyperpaths and
minimal s-t separators unless P = NP", and if s-t hyperpath enumeration were output-polynomial on
BF-hypergraphs then minimal transversal enumeration would be too — "an open problem for over 45
years". The positive result: "the s-t hyperpath enumeration for a B-hypergraph can be solved in
polynomial delay by backtracking" ([Kurita and Mann, *On the Complexity of Hyperpath and Minimal
Separator Enumeration in Directed Hypergraphs*, arXiv:2507.07528,
2025](https://arxiv.org/abs/2507.07528)).

**Reading:** enumerating *all* justifications of an n-ary inference is intractable in general, but in
the Horn (B-hypergraph) case — which is where rule-based KHG reasoning lives — it is polynomial
delay. That is a genuinely useful licence for building an explanation engine.

## 2. Datalog and existential rules over n-ary facts

Datalog needs no adaptation: its atoms are n-ary already, and a rule body is a conjunctive query
([Ceri, Gottlob and Tanca, *IEEE TKDE* 1(1), 1989](https://doi.org/10.1109/69.43410)). A knowledge
hypergraph in the labelled-tuple formalisation *is* a Datalog EDB. Rules can quantify over roles
that a triple-based encoding would have had to reify:

```prolog
% an n-ary rule that a binary KG cannot state without reification
co_supervised(S, A, B) :-
    thesis(S, _Title, A, _Year), thesis(S, _Title2, B, _Year2), A \= B.
```

Three practical points:

- **Recursion gives hyperedge closure.** Transitive reachability over hyperedges is a two-line
  Datalog program; no embedding model computes it.
- **Existential rules / Datalog±** extend this with existentials in rule heads, which is the natural
  logic for "there exists an n-ary fact relating these entities"; its decidable fragments are
  controlled by, among other things, guardedness — again a hypergraph-structural condition.
- **Combined complexity is governed by hypertree width**, exactly as for conjunctive queries
  ([query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md) §10.2).

The gap: essentially no KHG *system* exposes Datalog over its n-ary facts. TypeDB has rules,
HypergraphDB has none, and the embedding literature treats rules as an afterthought.

## 3. Rule mining over n-ary facts

**Binary:** AMIE mines Horn rules from incomplete knowledge bases under the partial-completeness
assumption ([Galárraga, Teflioudi, Hose and Suchanek, *AMIE: Association Rule Mining under
Incomplete Evidence in Ontological Knowledge Bases*, WWW 2013](https://doi.org/10.1145/2488388.2488425)).
It, and its successors, operate on triples.

**N-ary:** this is a real hole. The only model in the survey that mines and uses logic rules over
n-ary facts is **HyperMLN**: "the only method that explicitly addresses explainability in link
prediction in NKGs", using "predefined first-order logic rules" in a Markov logic network coupled to
KHG embeddings by variational EM — the E-step distils knowledge into the embeddings, the M-step
updates rule weights ([Chen, Wang, Wang and Li, *Explainable Link Prediction in Knowledge
Hypergraphs*, CIKM 2022](https://doi.org/10.1145/3511808.3557316); characterisation from
[Wei, Guan, Li, Jin, Guo and Cheng, arXiv:2506.08970, 2025](https://arxiv.org/abs/2506.08970) §6.3).
Note the word **predefined**: HyperMLN weights rules, it does not discover them at n-ary arity.

So: *there is no AMIE for n-ary facts.* The combinatorics are worse — a rule over k-ary atoms has a
much larger search space of variable-role bindings — but nothing in principle blocks it.

## 4. Ontological reasoning: OWL, RDF-star, RDF 1.2

Three facts, each with a consequence.

**RDF reification has deliberately weak semantics.** "A reification of a triple does not entail the
triple, and is not entailed by it. … The reification only says that the triple token exists and what
it is about, not that it is true" ([RDF 1.1 Semantics, W3C Recommendation,
2014](https://www.w3.org/TR/rdf11-mt/)). So reified n-ary facts carry no inferential weight.

**RDF 1.2 keeps that separation.** Triple terms denote propositions — "if E is a ground triple term,
then I(E) = IT(I(E.s), I(E.p), I(E.o))", with an RDFS range constraint "rdf:reifies rdfs:range
rdfs:Proposition" — but the specification defines **no entailment pattern** by which asserting
`ex:a rdf:reifies <<( ex:s ex:p ex:o )>>` entails `ex:s ex:p ex:o` ([RDF 1.2 Semantics, W3C Candidate
Recommendation, 7 April 2026](https://www.w3.org/TR/rdf12-semantics/)). This is a design choice, and
the right one for provenance and attribution; it does mean that a reasoner will not chain through
qualified facts unless you add rules that do so.

**OWL has no n-ary predicates.** The W3C's own guidance is the relation-instance pattern — introduce
a class for the relation and one property per participant ([Noy and Rector, *Defining N-ary Relations
on the Semantic Web*, W3C Working Group Note, 12 April
2006](https://www.w3.org/TR/swbp-n-aryRelations/)); see
[n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md).
Consequence: OWL reasoning over a knowledge hypergraph reasons about *relation instances*, and
cardinality or disjointness constraints have to be expressed on those instances, not on the n-ary
relation. Constraints like "a delivery has exactly one destination" become subclass axioms on the
`Delivery` class — workable, verbose, and easy to get wrong.

## 5. Complex query answering over hyper-relational graphs and knowledge hypergraphs

This is the live research line: answer a first-order query over an **incomplete** hypergraph, where
the answer requires links the graph does not contain. Four systems, in order.

### StarQE (2022) — hyper-relational conjunctive queries

The first hyper-relational query-embedding model, built on a StarE GNN encoder, with the **WD50K-QE**
dataset of "hyper-relational variants of 7 well-studied query patterns". Its headline finding is
that "qualifiers help in obtaining more accurate answers compared to triple-only graphs" — i.e.
context that restricts a fact also restricts a query and therefore helps
([Alivanistos, Berrendorf, Cochez and Galkin, *Query Embedding on Hyper-relational Knowledge Graphs*,
ICLR 2022 / arXiv:2106.08166](https://arxiv.org/abs/2106.08166); code
<https://github.com/DimitrisAlivas/StarQE>).

### NQE (2023) — full n-ary FOL

NQE extends this to the full existential fragment: "a dual-heterogeneous Transformer encoder and
fuzzy logic theory to satisfy all n-ary FOL queries, including existential quantifiers (∃),
conjunction (∧), disjunction (∨), and negation (¬)", with the **WD50K-NFOL** dataset
([Luo, E, Yang, Zhou, Guo, Yao, Tang, Lin and Wan, *NQE: N-ary Query Embedding for Complex Query
Answering over Hyper-relational Knowledge Graphs*, AAAI 2023 /
arXiv:2211.13469](https://arxiv.org/abs/2211.13469); code <https://github.com/LHRLAB/NQE>). The use
of **fuzzy logic** for the connectives, rather than geometric operators, is the design decision that
makes negation tractable.

### SQE (2023) — linearise the query

Sequential Query Encoding takes the opposite route: linearise the query into a token sequence and
let a sequence encoder handle it, rather than recursing over the query's computation graph
([Bai, Zheng and Song, *Sequential Query Encoding for Complex Query Answering on Knowledge Graphs*,
TMLR 2023 / arXiv:2302.13114](https://arxiv.org/abs/2302.13114)). SQE is defined for knowledge
graphs; it is the baseline that hypergraph CQA models are compared against.

### LKHGT (2025) — CQA over genuine knowledge hypergraphs

Tsang, Wang and Song make the case that hyper-relational graphs still cannot represent "relationships
of varying arity that contain entities with equal contributions", and move to knowledge hypergraphs
proper. They sample two new datasets, **JF17k-HCQA** and **M-FB15k-HCQA**, each containing
"projection, negation, conjunction, and disjunction" query types, and propose the **Logical Knowledge
Hypergraph Transformer (LKHGT)**: a *Projection Encoder* for atomic projection plus a *Logical
Encoder* for the logical operations, both carrying a **Type Aware Bias (TAB)** for token
interactions. They report state of the art on knowledge-hypergraph CQA and generalisation "to
out-of-distribution query types" ([Tsang, Wang and Song, *Transformers for Complex Query Answering
over Knowledge Hypergraphs*, arXiv:2504.16537, 23 April 2025](https://arxiv.org/abs/2504.16537)).

### The pattern across all four

| System | Year | Data model | Logical operators | Mechanism |
|---|---|---|---|---|
| StarQE | 2022 | hyper-relational | ∃, ∧ | GNN (StarE) query encoder |
| NQE | 2023 | hyper-relational | ∃, ∧, ∨, ¬ | dual-heterogeneous Transformer + fuzzy logic |
| SQE | 2023 | triple KG | ∃, ∧, ∨, ¬ | linearised query, sequence encoder |
| LKHGT | 2025 | knowledge hypergraph | ∃, ∧, ∨, ¬ | two-stage Transformer with type-aware bias |

Every one of them replaces *inference* with *ranking*: the answer is a ranked entity list, not a
derivation. That is the correct trade for incomplete data and the wrong one when you need a
justification — which is why §1's hyperpath view and §3's rule mining still matter.

## 6. Neuro-symbolic middle ground

HyperMLN (§3) is the one model in the n-ary literature that couples a symbolic layer to an embedding
layer. Its reported weakness is instructive: it "is sensitive to the coverage and quality of the
mined logic rules". The survey's recommendation for the field is to go further — "explainability
should move beyond rule extraction to encompass broader interpretable reasoning, such as causal
attribution and counterfactual analysis" ([Wei et al.
2025](https://arxiv.org/abs/2506.08970) §6.3).

## Open questions raised here

- Is there a rule-mining algorithm for n-ary facts — an "AMIE for hyperedges" — and what is the right
  language bias (fixed arity? role-typed? qualifier-aware)?
- Can the polynomial-delay B-hypergraph hyperpath enumeration of
  [Kurita and Mann 2025](https://arxiv.org/abs/2507.07528) be used directly as an explanation engine
  for rule-based KHG inference?
- CQA systems answer but do not justify. Can a hyperpath be extracted post hoc from a query
  embedding model, as subgraph explanations are for GNNs?
- RDF 1.2 deliberately does not entail the reified triple. What is the minimal rule set that gives
  qualified facts *useful* entailment behaviour without breaking provenance?

## Sources

- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. "Directed hypergraphs and applications". *Discrete Applied Mathematics* 42(2–3), 1993. <https://doi.org/10.1016/0166-218x(93)90045-p>
- Ausiello, G., Laura, L. "Directed hypergraphs: Introduction and fundamental algorithms — A survey". *Theoretical Computer Science*, 2016. <https://doi.org/10.1016/j.tcs.2016.03.016>
- Dowling, W. F., Gallier, J. "Linear-time algorithms for testing the satisfiability of propositional Horn formulae". *Journal of Logic Programming* 1(3), 1984. <https://doi.org/10.1016/0743-1066(84)90014-1>
- Kurita, K., Mann, K. *On the Complexity of Hyperpath and Minimal Separator Enumeration in Directed Hypergraphs*. arXiv:2507.07528, 10 July 2025. <https://arxiv.org/abs/2507.07528>
- Ceri, S., Gottlob, G., Tanca, L. "What you always wanted to know about Datalog (and never dared to ask)". *IEEE TKDE* 1(1), 1989. <https://doi.org/10.1109/69.43410>
- Galárraga, L., Teflioudi, C., Hose, K., Suchanek, F. "AMIE: Association Rule Mining under Incomplete Evidence in Ontological Knowledge Bases". *WWW 2013*. <https://doi.org/10.1145/2488388.2488425>
- Chen, Z., Wang, X., Wang, C., Li, J. "Explainable Link Prediction in Knowledge Hypergraphs" (HyperMLN). *CIKM 2022*. <https://doi.org/10.1145/3511808.3557316>
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs*. arXiv:2506.08970, 2025; EMNLP 2025. <https://arxiv.org/abs/2506.08970>
- Hayes, P., Patel-Schneider, P. (eds.) *RDF 1.1 Semantics*. W3C Recommendation, 25 February 2014. <https://www.w3.org/TR/rdf11-mt/>
- Patel-Schneider, P., Franconi, E., Arndt, D. *RDF 1.2 Semantics*. W3C Candidate Recommendation, 7 April 2026. <https://www.w3.org/TR/rdf12-semantics/>
- Noy, N., Rector, A. (eds.) *Defining N-ary Relations on the Semantic Web*. W3C Working Group Note, 12 April 2006. <https://www.w3.org/TR/swbp-n-aryRelations/>
- Alivanistos, D., Berrendorf, M., Cochez, M., Galkin, M. *Query Embedding on Hyper-relational Knowledge Graphs*. ICLR 2022; arXiv:2106.08166. <https://arxiv.org/abs/2106.08166>
- Luo, H., E, H., Yang, Y., Zhou, G., Guo, Y., Yao, T., Tang, Z., Lin, X., Wan, K. *NQE: N-ary Query Embedding for Complex Query Answering over Hyper-Relational Knowledge Graphs*. AAAI 2023; arXiv:2211.13469. <https://arxiv.org/abs/2211.13469>
- Bai, J., Zheng, T., Song, Y. *Sequential Query Encoding for Complex Query Answering on Knowledge Graphs*. TMLR 2023; arXiv:2302.13114. <https://arxiv.org/abs/2302.13114>
- Tsang, H. T., Wang, Z., Song, Y. *Transformers for Complex Query Answering over Knowledge Hypergraphs*. arXiv:2504.16537, 23 April 2025. <https://arxiv.org/abs/2504.16537>
