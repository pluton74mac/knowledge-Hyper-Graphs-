---
title: N-ary relations, relational algebra and the query hypergraph
type: concept
status: draft
tags: [n-ary, relational-model, codd, join-tree, yannakakis, acyclicity, agm-bound, worst-case-optimal-join, conjunctive-query, schema-width]
created: 2026-09-20
updated: 2026-09-25
---

# N-ary relations, relational algebra and the query hypergraph

The oldest and best-developed theory of n-ary facts is not in graph theory but in relational
database theory, where a fact *is* a tuple and a hypergraph is the standard tool for reasoning
about schemas and queries. This note establishes the correspondence — which is exact — and imports
the results that a knowledge hypergraph inherits for free.

See also [hypergraph-theory-results.md](hypergraph-theory-results.md) (acyclicity and width) and
[../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md)
(how the same facts are encoded in RDF-style knowledge graphs).

## 1. Relations are sets of tuples

Codd's 1970 paper introduces a data model "based on n-ary relations, a normal form for data base
relations, and the concept of a universal data sublanguage"
([Codd, 1970](https://dl.acm.org/doi/10.1145/362384.362685), *Communications of the ACM*
13(6):377–387). The standard set-theoretic content is: given domains `S₁, …, S_n`, a relation `R`
of **degree** (arity) `n` is a subset `R ⊆ S₁ × … × S_n`; each element is a tuple
`(v₁, …, v_n)`. Attributes name the positions, so a tuple can equivalently be written as a function
from attribute names to values.

This is precisely the "ordered hyperedge" and "role-labelled hyperedge" of Section 6 of
[hypergraph-definitions.md](hypergraph-definitions.md): positions ↔ ordered tuples, attributes ↔
roles. Fatemi, Taslakian, Vazquez and Poole's knowledge-hypergraph tuples `r(e₁, …, e_k)` are
relations in Codd's sense with entities as the domain
([Fatemi et al., 2020](https://doi.org/10.24963/ijcai.2020/303)); Wen and co-authors' multi-fold
relations `R ⊆ N^{M(R)}` are the attribute-indexed form
([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)).

**The claim "an n-ary fact is a hyperedge" is therefore two claims**, and they should be kept
apart:

- *Weak claim (true, and trivial):* the set of entities mentioned by a fact is a subset of the
  entity set, hence a hyperedge.
- *Strong claim (what a KHG actually needs):* the fact is an **ordered or labelled** hyperedge with
  its own identity, so that arity, roles, and repeated participation are preserved.

The weak claim loses the relation name, the roles, and the distinction between two facts over the
same entities. Codd's model never had that problem because a tuple always lives in a named
relation.

## 2. Three different hypergraphs of a database

The literature uses "the hypergraph of a database" for at least three different objects. Confusing
them is a common source of error.

| Name | Vertices | Hyperedges | Used for |
|---|---|---|---|
| **Schema hypergraph** | attributes | relation schemas | acyclicity of a database design, normalisation |
| **Query hypergraph** | query variables | query atoms | join evaluation, hypertree width, AGM bound |
| **Instance / fact hypergraph** | domain values (entities) | individual tuples | the knowledge hypergraph |

Fagin's degrees of acyclicity and Beeri–Fagin–Maier–Yannakakis's desirability results are about
the first, the **schema**: both papers study database schemes, which "can be viewed as
hypergraphs" ([Fagin, 1983](https://dl.acm.org/doi/10.1145/2402.322390), abstract;
[Beeri et al., 1983](https://dl.acm.org/doi/10.1145/2402.322389), abstract; both abstracts read via
OpenAlex). The same acyclicity notion reaches the second, the query hypergraph, through
Yannakakis's algorithm for acyclic queries and Gottlob, Leone and Scarcello's hypertree width
([Gottlob et al., 2002](https://arxiv.org/abs/cs/9812022), Theorem 4.4: a conjunctive query is
acyclic if and only if its hypertree width is 1). A KHG is the third.

What transfers to a KHG through its schema is narrower than it looks. The schema hypergraph of a
KHG (roles as vertices, relations as hyperedges) is the hypergraph of one query: the join of *all*
relations on same-named roles. If it is α-acyclic, that universal join can be evaluated in time
polynomial in the sizes of the input and the output, counting the query as part of the input
(combined complexity), which is the sense of "tractable" here (Section 3). If it is β-acyclic, the
same holds for the join of *any subset* of the relations on shared role names, because every
subset of a β-acyclic hypergraph is α-acyclic
([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076)). Conjunctive query evaluation in general
is "well-known to be NP-complete"
([Gottlob, Lanzinger, Pichler and Razgon, 2021](https://arxiv.org/abs/2002.05239), §1). An acyclic
schema does not make the queries over it tractable: a query can be cyclic whatever the schema, for
example a triangle over one binary relation or a cycle of facts joined on entity variables, and its
cost is set by its own hypergraph. Acyclicity is a property of the query or schema, never of the instance.
(Corrected 2026-09-25. This section had said that Fagin's and BFMY's results are about "the first
two" hypergraphs, and that "if the schema of a fact base is α-acyclic, queries over it are
tractable, whatever the instance looks like"; [P6](../../projects/p6-schema-width/) research
report 01 §1.5.)

## 3. Acyclic schemas and the Yannakakis algorithm

A query hypergraph is **α-acyclic** exactly when it has a **join tree** — a tree labelled by the
atoms in which, for any two nodes, every node on the path between them contains their shared
attributes ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076); see
[hypergraph-theory-results.md](hypergraph-theory-results.md), Section 5). The join tree is
computable by GYO reduction: repeatedly remove a contained hyperedge or a vertex that appears in
only one hyperedge ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076), citing Graham 1979 and
Yu & Özsoyoğlu 1979).

Given a join tree, Yannakakis's algorithm evaluates the query in two passes of **semi-joins** —
bottom-up to remove dangling tuples, top-down to propagate — followed by the actual joins
(M. Yannakakis, "Algorithms for Acyclic Database Schemes", *VLDB 1981*, pp. 82–94,
https://dl.acm.org/doi/10.5555/1286831.1286840; venue and pages from the publisher listing, full
text not fetched `[unverified]`). Beeri, Fagin, Maier and Yannakakis's result is the reason this
matters: "several desirable properties that have been studied by other researchers in very
different terms are all shown to be equivalent to acyclicity"
([Beeri et al., 1983](https://dl.acm.org/doi/10.1145/2402.322389)). Acyclicity is not one nice
property among many; it is the property.

**Reading for KHG design.** A knowledge hypergraph whose relation schemas form an α-acyclic
hypergraph admits linear-ish evaluation of the join of its relations on shared role names; other
queries are governed by their own hypergraphs (Section 2). When the schema is cyclic, the cost of
that join is governed by the width parameters of
[hypergraph-theory-results.md](hypergraph-theory-results.md), Section 6.

Whether real schemas are cyclic was measured on 2026-09-25 by project
[P6](../../projects/p6-schema-width/) ([survey table](../../projects/p6-schema-width/results/survey.md)).
Once role names are shared across relations, every Wikidata qualifier schema measured is
α-cyclic: 1,155 relations from the declared allowed-qualifier constraints, and 13,315 from the
qualifiers observed in use in the 2026-09-22 dump (P3a's exact counts; 12,706 in P3a's slice). So is the Biolink Model v4.4.5 association schema (103 relations).
The Wikidata cores have hypertree width at least 3 or 4, known only as bounds (for example
[4, 38] for the declared schema); Biolink's is exactly 2. Relation-local role names make every
schema acyclic, trivially. Not every KHG schema is cyclic: GO-CAM's, with one central relation
class, is α-acyclic ([P6 research report 02](../../projects/p6-schema-width/research/02-data-sources-and-naming.md),
finding 9). The numbers, their measured object and their limits are in
[hypergraph-theory-results.md](hypergraph-theory-results.md), end of Section 6. (This replaces the
unsupported aside "and most interesting ones are [cyclic]", 2026-09-25.)

## 4. Size bounds and worst-case optimal joins

Atserias, Grohe and Marx bound the output size of a full conjunctive query in terms of a
**fractional edge cover** of the query hypergraph, so the hypergraph structure alone predicts how
large a join can be ([Atserias et al., 2013](https://dblp.org/rec/journals/siamcomp/AtseriasGM13.html),
*SIAM Journal on Computing* 42(4):1737–1767). Ngo, Porat, Ré and Rudra then give an algorithm
matching that bound: their work "describes a novel algorithm to process these queries optimally in
terms of worst-case data complexity", building directly on the AGM bound
(H. Q. Ngo, E. Porat, C. Ré, A. Rudra, "Worst-case Optimal Join Algorithms", *PODS 2012*,
pp. 37–48, and *Journal of the ACM* 65(3):16:1–16:40, 2018,
https://dl.acm.org/doi/10.1145/3180143; bibliographic details of the published versions from the
publisher listing `[unverified]`; the quoted description and the statements below read on
2026-09-25 in the [arXiv version](https://arxiv.org/abs/1203.1952)).

The lesson generalises beyond databases: **the arity structure, not the data, determines the
worst case.** What is proved about pairwise plans is specific. For the triangle query
`R(a,b), S(b,c), T(a,c)` with every relation of size N, the AGM bound on the output is N^{3/2}, yet
there are instances on which "both AGM's algorithm and any join-only plan take Ω(N²)-time"
([Ngo, Porat, Ré and Rudra, arXiv:1203.1952](https://arxiv.org/abs/1203.1952), §1). They also give
a sufficient syntactic condition on a query under which, for each k ≥ 2, instances exist where any
binary-join plan needs Ω(N²/k²) time while the fractional cover bound is O(N^{1+1/(k−1)}) (same
source). So a KHG engine that plans joins pairwise is provably slower than worst-case optimal on
some cyclic queries (the triangle among them), on worst-case instances; this is not a claim about
every cyclic query or every instance. It remains the strongest technical argument in this KB for
treating n-ary facts natively rather than decomposing them into binary edges. (Corrected
2026-09-25 from "provably suboptimal on cyclic queries", which overstated the result;
[P6](../../projects/p6-schema-width/) research report 01 §1.5.)

## 5. Directed hyperedges as dependencies and rules

Gallo, Longo, Pallottino and Nguyen list relational databases among the applications of directed
hypergraphs, alongside propositional logic and And–Or graphs
([Gallo et al., 1993](https://doi.org/10.1016/0166-218x(93)90045-p)). The correspondence is the
**B-arc**, a hyperarc with a single head: `X → a` with `X ⊆ V` is simultaneously a functional
dependency, a Horn clause `x₁ ∧ … ∧ x_k → a`, and a production rule
(see [hypergraph-definitions.md](hypergraph-definitions.md), Section 3). Closure under functional
dependencies is reachability in the corresponding B-hypergraph, which is why B-hypergraph
reachability is linear-time while the F-hypergraph analogues are not
([Gil Pons et al., 2022](https://arxiv.org/abs/2201.04799)).

So a knowledge hypergraph has room for two kinds of hyperedge that should not be conflated:

- **Fact hyperedges**: ordered/role-labelled, undirected in the Gallo sense, one per tuple.
- **Rule hyperedges**: directed B-arcs over *relations* or over *facts*, expressing dependencies
  and inferences.

## 6. What relational theory does *not* give a KHG

- **Open-world semantics.** The relational model is closed-world; a knowledge base usually is not.
- **Fact identity and provenance.** A tuple in Codd's model has no identity beyond its content, so
  two identical tuples are one. A KHG needs hyperedge identities (Section 5 of
  [hypergraph-definitions.md](hypergraph-definitions.md)) to attach source, time and confidence.
- **Statements about statements.** Nothing in relational algebra quotes a tuple; that is the
  recursive-hypergraph or reification problem
  ([../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md)).
- **Schema fluidity.** Relational schemas are fixed and few; KHG relation vocabularies are large,
  sparse and open.

The honest summary is that relational theory solves the *computational* half of the n-ary problem
completely and the *representational* half not at all.

## Sources

- Codd, E. F. "A relational model of data for large shared data banks." *Communications of the ACM* 13(6):377–387, 1970. https://dl.acm.org/doi/10.1145/362384.362685
- Fagin, R. "Degrees of acyclicity for hypergraphs and relational database schemes." *Journal of the ACM* 30(3):514–550, 1983. https://dl.acm.org/doi/10.1145/2402.322390
- Beeri, C., Fagin, R., Maier, D., Yannakakis, M. "On the Desirability of Acyclic Database Schemes." *Journal of the ACM* 30(3):479–513, 1983. https://dl.acm.org/doi/10.1145/2402.322389
- Brault-Baron, J. "Hypergraph Acyclicity Revisited." *ACM Computing Surveys* 49(3), 2016 (arXiv:1403.7076). https://arxiv.org/abs/1403.7076
- Yannakakis, M. "Algorithms for Acyclic Database Schemes." *Proceedings of the 7th International Conference on Very Large Data Bases (VLDB)*, pp. 82–94, 1981. Venue and pages from the publisher listing; full text not fetched `[unverified]`. https://dl.acm.org/doi/10.5555/1286831.1286840
- Atserias, A., Grohe, M., Marx, D. "Size Bounds and Query Plans for Relational Joins." *SIAM Journal on Computing* 42(4):1737–1767, 2013. https://dblp.org/rec/journals/siamcomp/AtseriasGM13.html
- Ngo, H. Q., Porat, E., Ré, C., Rudra, A. "Worst-case Optimal Join Algorithms." *PODS 2012*, pp. 37–48; *Journal of the ACM* 65(3):16:1–16:40, 2018. Bibliographic details of the two published versions from the publisher listing `[unverified]`. https://dl.acm.org/doi/10.1145/3180143 ; the arXiv version (arXiv:1203.1952, revision dated 27 November 2024) was read on 2026-09-25 for the statements in Section 4: https://arxiv.org/abs/1203.1952
- Gottlob, G., Lanzinger, M., Pichler, R., Razgon, I. "Complexity Analysis of Generalized and Fractional Hypertree Decompositions." *Journal of the ACM* 68(5):1–50, 2021; arXiv:2002.05239. https://arxiv.org/abs/2002.05239 (§1 read 2026-09-25)
- Project P6, "Schema width survey" (2026-09-24 to 2026-09-25): [survey table](../../projects/p6-schema-width/results/survey.md), [research report 01, theory and solvers](../../projects/p6-schema-width/research/01-theory-and-solvers.md) (§1.5 lists the corrections applied here), [research report 02, data sources and naming](../../projects/p6-schema-width/research/02-data-sources-and-naming.md).
- Gottlob, G., Leone, N., Scarcello, F. "Hypertree Decompositions and Tractable Queries." arXiv:cs/9812022, 1998; *JCSS* 64(3):579–627, 2002. https://arxiv.org/abs/cs/9812022
- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. "Directed hypergraphs and applications." *Discrete Applied Mathematics* 42(2–3):177–201, 1993. https://doi.org/10.1016/0166-218x(93)90045-p
- Gil Pons, R., Ward, M., Miller, L. "Finding (s,d)-Hypernetworks in F-Hypergraphs is NP-Hard." arXiv:2201.04799, 2022. https://arxiv.org/abs/2201.04799
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." *IJCAI 2020*, pp. 2191–2197. https://doi.org/10.24963/ijcai.2020/303
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases Beyond Binary Relations." *IJCAI 2016*, pp. 1300–1307. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
