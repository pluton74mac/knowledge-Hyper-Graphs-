---
title: Classical hypergraph theory results
type: concept
status: draft
tags: [hypergraph, berge, duality, transversal, hitting-set, helly, acyclicity, hypertree-width, generalized-hypertree-width, fractional-hypertree-width, schema-width, wikidata, biolink, colouring, partitioning, kahypar, hmetis]
created: 2026-09-20
updated: 2026-09-25
---

# Classical hypergraph theory results

The combinatorial theory of hypergraphs is older and larger than the knowledge-representation use
of them. This note collects the results that a knowledge-hypergraph practitioner actually meets:
duality, transversals, the Helly property, the acyclicity hierarchy, width parameters, colouring,
and cuts. Each section states the result and then why it matters downstream.

Definitions used here are in [hypergraph-definitions.md](hypergraph-definitions.md) and
[notation-cheatsheet.md](notation-cheatsheet.md).

## 1. Berge and the founding texts

Berge introduced hypergraphs "as a means to generalize the graph approach" in the 1960s and early
1970s ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). The canonical references are *Graphes
et hypergraphes* (Dunod, 1970), translated as *Graphs and Hypergraphs* (North-Holland, 1973)
([Berge, 1973](https://archive.org/details/graphshypergraph0000berg)), and *Hypergraphs:
Combinatorics of Finite Sets* (North-Holland, 1989)
([Berge, 1989](https://archive.org/details/hypergraphscombi0000berg)). Berge's convention — a
hyperedge family `(e_j)` covering `V`, with no empty hyperedge — is recorded in
[hypergraph-definitions.md](hypergraph-definitions.md), Section 1.

## 2. Duality

**Definition.** The **dual** `H*` has one vertex per hyperedge of `H` and one hyperedge per vertex
of `H`: "creating one vertex `e_j` in `V(H*)` for each hyperedge `E_j ∈ E(H)`, and one hyperedge
`A_i` in `E(H*)` for each vertex `a_i ∈ V(H)`, defined as `A_i = {e_j : a_i ∈ E_j}`"
([Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/)).
Ouvrard states it as: the hyperedges of `H*` are the vertices of `H`, incidence linking each
vertex to its **star** `H(v)` — the family of hyperedges containing `v`
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)).

**Consequences.** `H** = H` for hypergraphs with distinguishable vertices and hyperedges; in matrix
terms duality is transposition of the incidence matrix (see
[incidence-and-matrix-representations.md](incidence-and-matrix-representations.md)); duality of
hypergraphs is a covariant functor `d : Hyp → Hyp`
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). Many results come in dual pairs, the most
useful being **Helly ⟷ conformal** (Section 4).

**Why it matters for KHGs.** Every query over entities has a dual query over facts. Asking "which
facts mention these entities" is the dual of "which entities does this fact mention"; a system
that indexes one should index the other, because the theory says they are the same object viewed
twice.

## 3. Transversals, hitting sets, matchings

- A **transversal** (vertex cover, hitting set) is a set `T ⊆ V` meeting every hyperedge; the
  **transversal number** `τ(H)` is the minimum size of one
  ([Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/)).
- A **matching** is a family of pairwise disjoint hyperedges; `ν(H)` is the maximum size. Always
  `ν(H) ≤ τ(H)`; graphs with equality for all partial hypergraphs are the *König* case, and the
  general failure of equality is what makes hypergraphs harder than bipartite graphs `[unverified]`
  (the inequality itself is immediate; the König terminology is stated here from general
  background rather than from a fetched source).
- A hypergraph is **τ-critical** when removing any hyperedge lowers `τ`
  ([Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/)).

**Complexity.** Hitting set and set covering are both among the 21 problems Karp proved NP-complete
([Karp, 1972](https://www.cs.umd.edu/~gasarch/BLOGPAPERS/Karp.pdf)). The approximation threshold is
tight: Feige proved that `(1 − o(1)) ln n` "is a threshold below which set cover cannot be
approximated efficiently, unless NP has slightly superpolynomial time algorithms", matching the
greedy algorithm ([Feige, 1998](https://dl.acm.org/doi/10.1145/285055.285059)).

**Why it matters.** "Which minimal set of entities touches every fact in this subgraph?" is a
transversal question, and it is the shape of provenance-minimisation, of sampling a covering set
of facts for human review, and of feature selection over a KHG. The theory says: do not expect an
exact answer; expect `ln n`.

## 4. The Helly property and conformality

**Definition.** "A family of subsets has the Helly property when every subfamily thereof, formed
by pairwise intersecting subsets, contains a common element"
([Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/)).
The name traces to Eduard Helly's 1923 theorem on convex sets, which the same survey restates:
in `d`-dimensional Euclidean space, if in a finite collection of `n > d` convex sets any `d + 1`
have a common point, then all do.

**Generalisation.** `H` is **p-Helly** if every partial `p`-intersecting sub-family has non-empty
core (`core(H) = E₁ ∩ … ∩ E_m`)
([Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/)).

**Duality.** "A hypergraph is `k`-conformal if and only if its dual is `k`-Helly"
([Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/),
Theorem 4.1), where `k`-conformality asks that every maximal vertex set inducing a complete
`k`-section be an actual hyperedge.

**Complexity.** For fixed `p`, `p`-Helly is decidable in `O(m(n + p) n^{p+1})` time by checking
every `(p+1)`-subset; when `p` is variable the problem is NP-hard, and several bounded variants are
co-NP-complete
([Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/)).

**Related classes.** An **interval hypergraph** embeds its vertices on a line with hyperedges as
intervals; a **hypertree** (arboreal hypergraph) is a hypergraph whose hyperedges induce subtrees
of some tree on `V(H)`; "a hypergraph `H` is a hypertree if and only if `H` is Helly and its line
graph is chordal"; a hypergraph is **balanced** if it has no odd special cycle, **totally balanced**
if it has no special cycle at all, and **normal** if it is Helly with a perfect line graph
([Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/)).
The same survey notes that "the dual of a hypertree is a concept employed in the theory of
relational databases" — the link to Section 5.

## 5. Acyclicity: four degrees

Graph acyclicity splits into several inequivalent notions on hypergraphs. Fagin's 1983 paper is
the reference point: it introduces "three degrees of acyclicity ... in increasing order of
generality: gamma acyclicity, beta acyclicity, and alpha acyclicity"
([Fagin, 1983](https://dl.acm.org/doi/10.1145/2402.322390), *Journal of the ACM* 30:514–550).
Brault-Baron's survey re-derives all the characterisations
([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076)).

- **Berge acyclicity** (most restrictive). "A hypergraph `H` is Berge acyclic when the graph
  `G = {{x, e} : x ∈ e and e ∈ H}` is acyclic" — that is, when the incidence graph is a forest
  ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076), attributing the definition to Berge
  1985). Brault-Baron argues it is "not an actual hypergraph notion, but rather a multi-hypergraph
  notion", because the multiset `[{x,y}, {x,y}]` fails it while the set `{{x,y}}` does not; Fagin
  discarded it as too restrictive.
- **γ-acyclicity**. No γ-cycles; characterised by DM (D'Atri–Moscarini) reducibility using
  singleton vertex removal, singleton edge removal and linearization, and by the condition that
  "for any e ∈ H, H has a rooted join tree with disjoint branches whose root is labelled e"
  ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076), characterisation (γ2c), after
  [Duris, 2012](https://doi.org/10.1016/j.ipl.2012.05.005)). The words "with disjoint branches"
  carry the condition: labels of two tree nodes with no ancestor relation must be disjoint sets.
  Without them the condition says nothing new, since a join tree of any α-acyclic hypergraph can
  be rooted at any of its nodes (corrected 2026-09-25, [P6](../../projects/p6-schema-width/)
  research report 01 §1.5).
- **β-acyclicity**. "Every subset of `H` is alpha acyclic"; equivalently every subset is cycle-free,
  equivalently `H` admits a β-elimination order, equivalently `H` reduces to `∅` by repeatedly
  removing nest points. Notably, β-acyclicity "does not seem to admit a simple characterization in
  terms of join tree". A β-acyclic hypergraph on `n` vertices has at most `n(n+1)/2` hyperedges,
  the bound attained by the interval hypergraph
  ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076)).
- **α-acyclicity** (most general). Three equivalent characterisations
  ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076)):
  - an α-elimination order exists;
  - `H` is **GYO-reducible**: the Graham–Yu–Özsoyoğlu operations are *included edge removal* and
    *singleton vertex removal*, and `H` reduces to the empty hypergraph by a sequence of them;
  - `H` **has a join tree**: a tree `T` with an injective labelling `L` onto `E` satisfying the
    *join property* — for all `x, y` with `L(x) ∩ L(y) ≠ ∅` there is a path from `x` to `y` every
    vertex `v` of which satisfies `L(x) ∩ L(y) ⊆ L(v)`.

  α-acyclicity is not closed under taking sub-hypergraphs (that closure is exactly β-acyclicity),
  and α-acyclic hypergraphs can have exponentially many hyperedges: the full hypergraph
  `{e ⊆ {1,…,n} : e ≠ ∅}` is α-acyclic
  ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076)).

Beeri, Fagin, Maier and Yannakakis showed that "several desirable properties that have been
studied by other researchers in very different terms are all shown to be equivalent to acyclicity"
([Beeri et al., 1983](https://dl.acm.org/doi/10.1145/2402.322389), *JACM* 30(3):479–513).

**Why it matters.** α-acyclicity is the first tractable class of joins, not the boundary of
tractability. A conjunctive query is acyclic "if and only if hw(Q) = 1"
([Gottlob, Leone and Scarcello, 2002](https://arxiv.org/abs/cs/9812022), Theorem 4.4), and
tractability extends to every class of bounded hypertree, generalized hypertree or fractional
hypertree width: constraint problems of bounded fractional hypertree width are solvable in
polynomial time when a decomposition is given in the input
([Grohe and Marx, 2014](https://arxiv.org/abs/1711.04506), abstract; see Section 6). Where the
boundary lies depends on the setting:

- *Unbounded arity, fixed-parameter tractability* (parameterised by the number of variables):
  bounded **submodular width**, which is strictly more general than bounded fractional hypertree
  width, gives fixed-parameter tractability; if it is unbounded, the problem "is not
  fixed-parameter tractable (and hence not polynomial-time solvable), unless the Exponential Time
  Hypothesis (ETH) fails" ([Marx, 2013](https://arxiv.org/abs/0911.0801), abstract).
- *Bounded arity:* "bounded tree-width completely describes this setting", assuming
  FPT ≠ W[1] ([Moll, Tazari and Thurley, 2012](https://arxiv.org/abs/1106.4719), introduction,
  citing Grohe 2007).

For a KHG, the acyclicity of the **schema** is a statement about one query: the join of all its
relations on shared role names (Fagin's database-scheme setting). It does not make queries over
the schema cheap. A query can be cyclic over an acyclic schema, for example a triangle over one
binary relation, or any pattern that joins facts on entity variables; the cost of a query is set
by that query's own hypergraph (see
[n-ary-relations-and-relational-algebra.md](n-ary-relations-and-relational-algebra.md), Section 2).
Where the schema is cyclic, the width parameters of Section 6 measure how far off it is; the
measured values for real schemas are at the end of Section 6. (This paragraph was corrected on
2026-09-25: it had called α-acyclicity "exactly the boundary of tractable join evaluation" and said
that queries over an α-acyclic schema are cheap; [P6](../../projects/p6-schema-width/) research
report 01 §1.5.)

## 6. Width parameters: treewidth, hypertree width and its relatives

For cyclic instances, the question becomes "how close to acyclic". Gottlob, Leone and Scarcello
introduced **hypertree width**, showing that "Boolean queries of constant hypertree width can be
efficiently evaluated", that bounded hypertree width is polynomial-time recognisable (unlike the
earlier *query width*, whose recognition is NP-complete), and that "the class of queries with query
width bounded by `k` is properly contained in the class of queries whose hypertree width is
bounded by `k`" ([Gottlob et al., 1999/2002](https://arxiv.org/abs/cs/9812022); *Journal of
Computer and System Sciences* 64(3):579–627, 2002).

Three widths, in increasing generality — hypertree width `hw`, generalized hypertree width `ghw`,
fractional hypertree width `fhw` — are tied by

`fhw(H) ≤ ghw(H) ≤ hw(H) ≤ 3 · ghw(H) + 1` and `ghw(H) ≤ tw(H) + 1`,

where `tw` is the treewidth of the primal graph; the upper bound on `hw` is due to Adler, Gottlob
and Grohe ([Grohe and Marx, 2014](https://arxiv.org/abs/1711.04506), §4, citing
[Adler et al., 2007](https://doi.org/10.1016/j.ejc.2007.04.013)). Some introductions print the
upper bound with the variables swapped, among them the arXiv version of Gottlob, Lanzinger,
Pichler and Razgon, whose later section states "hw(H) ≤ 3 · ghw(H) + 1"
([Gottlob et al., 2021](https://arxiv.org/abs/2002.05239)).

The three differ sharply in recognisability. `hw(H) ≤ k` can be checked in polynomial time for
fixed `k` ([Gottlob, Leone and Scarcello, 2002](https://arxiv.org/abs/cs/9812022)). Checking
`ghw(H) ≤ k` is NP-complete for every fixed `k ≥ 3`
([Gottlob, Miklós and Schwentick, 2009](https://doi.org/10.1145/1568318.1568320)). Gottlob,
Lanzinger, Pichler and Razgon close the case `k = 2`: deciding `fhw(H) ≤ 2` is NP-complete, which
settled a decade-old open problem, and so is deciding `ghw(H) ≤ 2`. They also prove tractable
cases ([Gottlob et al., 2021](https://arxiv.org/abs/2002.05239), *Journal of the ACM* 68(5), Main
Results 1–5):

- `ghw ≤ k` is tractable for every constant `k` on classes with the bounded intersection or bounded
  multi-intersection property (BIP, BMIP);
- `fhw ≤ k` is tractable on classes of bounded degree or with the BIP;
- under the BMIP an FHD of width at most `k + ε` can be computed in polynomial time, and bounded
  VC-dimension gives another polynomial-time approximation.

So `hw` is the only one of the three whose check is polynomial for every fixed `k` on all
hypergraphs, but not the only one that is tractable to check. (Corrected 2026-09-25: this
paragraph had said that "only `hw` is tractable to check" and credited `ghw ≤ 2` alone to Gottlob
et al.; [P6](../../projects/p6-schema-width/) research report 01 §1.5.) Fractional hypertree width derives
from the fractional edge cover bound of Atserias, Grohe and Marx
([Atserias et al., 2013](https://dblp.org/rec/journals/siamcomp/AtseriasGM13.html)); it was
introduced by Grohe and Marx in "Constraint solving via fractional edge covers", *ACM Transactions
on Algorithms* 11(1), article 4, 2014 ([Grohe and Marx, 2014](https://arxiv.org/abs/1711.04506);
volume and article number from reference [34] of Gottlob et al. 2021 and from
[OpenAlex](https://api.openalex.org/works/doi:10.1145/2636918)).

**Treewidth** of the hypergraph's primal (2-section) graph is the older parameter and is strictly
weaker here: a query can have unbounded treewidth and bounded hypertree width, which is the whole
point of the hypertree notion ([Gottlob et al., 1999/2002](https://arxiv.org/abs/cs/9812022)).

### Measured: where real KHG schemas fall (P6, 2026-09-25)

Project [P6](../../projects/p6-schema-width/) measured the acyclicity class and the four widths
of real relation-type schemas with its checker `khg-width`
([projects/p6-schema-width/khg-width/](../../projects/p6-schema-width/khg-width/)). The full
table is [results/survey.md](../../projects/p6-schema-width/results/survey.md).

**What was measured.** The schema hypergraph has one vertex per role and one hyperedge per
relation (the roles of its core and qualifier usages). Its width is the width of the conjunctive
query that joins *all* relations of the schema on same-named roles: the universal join of Fagin's
database-scheme setting. It is not the width of arbitrary queries over the knowledge hypergraph,
which join facts on entity variables and have their own hypergraphs
([P6 DESIGN §2.1](../../projects/p6-schema-width/DESIGN.md); research report 01 §2.5). The Berge
class has a direct storage reading: the reified encoding (one fact node, one binary edge per role)
is acyclic exactly when the schema is Berge-acyclic, because the reified form is the incidence
graph ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076), Remark 7: on graphs all the degrees
coincide).

**Results** (core and qualifier roles; adding time roles leaves every class unchanged). A value in brackets is a `[lower, upper]` bound; each upper bound comes with a
decomposition validated on the schema hypergraph, and each lower bound with a stored witness.

| Schema | Relations | Class (GYO residue, relations) | hw | ghw | fhw |
|---|---|---|---|---|---|
| Wikidata, declared allowed-qualifier constraints (WDQS, 2026-09-24), wd-roles r1 naming | 1,155 | α-cyclic (391) | [4, 38] | [4, 25] | [35/11, 24] |
| Wikidata, observed qualifiers with ≥ 10 uses and ≥ 0.1 % (SQID counts), wd-roles r1 | 13,608 | α-cyclic (748) | [4, 68] | [4, 29] | [63/19, 79/3] |
| Wikidata, every observed qualifier (SQID counts), wd-roles r1 | 13,608 | α-cyclic (1,441) | [3, 61] | [3, 39] | [2, 75/2] |
| Each Wikidata schema with relation-local roles (control) | as above | Berge-acyclic (0) | 1 | 1 | 1 |
| Biolink Model v4.4.5 associations, global slot names | 103 | α-cyclic (5) | 2 | 2 | 2 |
| Baseline: HyperBench, 1,113 non-random conjunctive queries | | | 1 / 2 / 3 for 673 / 432 / 8 queries | | |

- **Real KHG schemas are cyclic once roles are shared.** Under every naming with global roles,
  every Wikidata schema (declared or observed) is α-cyclic, with or without time roles: the survey
  measured this under wd-roles r1, and P6's research probe under generic, property-local and typed
  namings too ([research report 02](../../projects/p6-schema-width/research/02-data-sources-and-naming.md)
  §3.3). Only relation-local roles make it acyclic, and trivially: their hyperedges are pairwise
  disjoint, so every width is 1. The class therefore does not separate the variants; the width
  does. Not every KHG schema is cyclic: GO-CAM's schema (one central relation class) is α-acyclic
  by GYO in one pass ([P6 research report 02](../../projects/p6-schema-width/research/02-data-sources-and-naming.md),
  finding 9).
- **Wikidata's universal-join width is at least 3 or 4 and is not settled.** Across the six
  wd-roles r1 rows, the cyclic cores have 391 to 1,446 relations. HyperBench has exact hw for only 6 of its 23 graphs with 300 to 999
  edges (research report 01 §3.5), and the external solvers (BalancedGo and log-k-decomp) used
  their full 20-minute budget per row without deciding a width. With time roles the declared
  schema's bound becomes [4, 43].
- **Biolink's association schema is exactly hw = ghw = fhw = 2**, with a five-relation core,
  within the range of real conjunctive queries (1,105 of HyperBench's 1,113 non-random queries have
  hw ≤ 2). Every non-random HyperBench query has hw ≤ 3
  ([Fischl et al., 2021](https://doi.org/10.1145/3440015)), so the lower bound of 4 already puts
  the declared and robust-observed Wikidata schemas beyond all of them. The comparison is by hw
  only: HyperBench holds queries collected with a bias toward cyclic ones (its SPARQL and Wikidata
  subsets hold only cyclic queries), while these are schemas.
- **Primal treewidth overstates.** The relation-local control of the declared schema has hw 1 but
  treewidth 116, set by its largest relation (117 roles); the declared wd-roles r1 schema has
  treewidth in [116, 235].

**Limits.** The Wikidata widths are bounds, not exact values. The observed rows rest on SQID usage
counts (dump of 2026-08-10) over DeltaBot main-statement counts of 2026-09-23. They are to be
replaced by P3a's exact counts from the 2026-09-22 dump, when those rows are rerun and P3a's
corpus-slice rows are added (DESIGN §6.6). The numbers depend on the role naming: wd-roles r1
([wd-roles.md](../../projects/p6-schema-width/wd-roles.md), shared with P3a) names a property's
main-value role after the property, which joins its main use to its uses as a qualifier elsewhere
and enlarges the cyclic core by 16 % to 51 % over a property-local naming (research report 02
§3.4). The WDQS snapshot is live and cannot be refetched byte for byte; the measured schema files
are committed. For the query side, HyperBench reports that of 1,915,550 CQOF+ queries in the
Wikidata logs, 590,005 have hw 2 and the rest hw 1 (Bonifati, Martens and Timm, as quoted by
[Fischl et al., 2021](https://doi.org/10.1145/3440015); not checked against the original
`[unverified]`). So real Wikidata queries are far narrower than the universal join of the schema.

## 7. Colouring

The basic notion generalises graph colouring the weak way: "A proper hypergraph coloring is a
mapping of a vertex of `V` to a color number taken in `⟦λ⟧` ... such that for every hyperedge there
are at least two vertices of different colors. The minimum value of `λ` for which a proper coloring
exists is called the chromatic number of the hypergraph `H` and written `χ(H)`"
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), summarising the Bujtás et al. survey). Berge's
own formulation is the 2-colour case: no hyperedge other than a singleton is monochromatic
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Berge 1967/1973). Seymour called a
hypergraph that is not 2-colourable but all of whose proper subsets are a **condenser**, and showed
condensers are the minimal non-2-colourable hypergraphs; the odd cycle
`{{1,2},{2,3},…,{n,1}}` and `{{1,…,n}} ∪ {{0,i} : 1 ≤ i ≤ n}` are examples
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Seymour 1974).

Voloshin's **mixed hypergraphs** partition the hyperedge family into two sub-families
("hyperedges" and "anti-hyperedges"), one demanding a repeated colour and the other a distinct
one, which produces a *chromatic spectrum* rather than a single chromatic number
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Voloshin 1993/2002; see also
V. Voloshin, *Coloring Mixed Hypergraphs: Theory, Algorithms and Applications*, Fields Institute
Monographs 17, AMS, 2002 — not consulted directly `[unverified]`).

**Why it matters.** Colouring is the combinatorial shell of constraint satisfaction and of
conflict detection: "no fact may have all its participants in the same equivalence class" is a
proper-colouring constraint, and mixed hypergraphs are the natural home for schemas that carry both
"must differ" and "must agree" constraints over an n-ary fact.

## 8. Cuts and partitioning

A hyperedge is **cut** by `(S, V \ S)` when it meets both sides. Two objectives dominate practice:

- **Cut-net**: count (or weigh) the hyperedges that are cut.
- **Connectivity (λ−1) metric**: charge each hyperedge `(λ(e) − 1) · w(e)`, where `λ(e)` is the
  number of blocks it touches. Schlag and co-authors call it "the most commonly used connectivity
  metric" ([Schlag et al., 2021/2022](https://arxiv.org/abs/2106.08696)).
- Zhou, Huang and Schölkopf's **normalized hypergraph cut**, weighting each cut hyperedge by
  `w(e)|e ∩ S||e ∩ Sᶜ|/δ(e)` — the clique-expansion reading of a cut
  ([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)).

The problem is NP-hard ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Garey & Johnson),
so the field is algorithm engineering:

- **hMETIS** — Karypis, Aggarwal, Kumar and Shekhar's multilevel algorithm: coarsen the hypergraph
  through a sequence of smaller hypergraphs, bisect the smallest, then project and refine back up;
  its contribution was new coarsening schemes giving consistent quality
  (*IEEE Transactions on VLSI Systems* 7(1):69–79, 1999; bibliographic details and description from
  the publisher listing and from [Ouvrard, 2020](https://arxiv.org/abs/2002.05014); full text not
  fetched `[unverified]`).
- **KaHyPar** — Schlag, Heuer, Gottesbüren, Akhremtsev, Schulz and Sanders take the multilevel idea
  to "one level for (almost) every vertex" (n-level), add LSH-based pin sparsification and Louvain
  community detection as preprocessing, and combine "highly-localized direct k-way local search and
  flow-based techniques that take a more global view", with an optional memetic layer
  ([Schlag et al., 2021/2022](https://arxiv.org/abs/2106.08696); published as "High-Quality
  Hypergraph Partitioning", *ACM Journal of Experimental Algorithmics*, 2022 —
  https://dl.acm.org/doi/10.1145/3529090, publisher page returned HTTP 403 when fetched, so volume
  and article number are `[unverified]`).

**Why it matters.** Partitioning a KHG is how it is sharded across machines, and the objective
chosen decides what "a fact spans two shards" costs. The connectivity metric is the right default
because a fact touching `λ` shards costs roughly `λ − 1` extra messages.

## Sources

- Berge, C. *Graphs and Hypergraphs*. North-Holland, 1973 (translation of *Graphes et hypergraphes*, Dunod, 1970). https://archive.org/details/graphshypergraph0000berg
- Berge, C. *Hypergraphs: Combinatorics of Finite Sets*. North-Holland, 1989. https://archive.org/details/hypergraphscombi0000berg
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014
- Dourado, M. C., Protti, F., Szwarcfiter, J. L. "Complexity Aspects of the Helly Property: Graphs and Hypergraphs." *Electronic Journal of Combinatorics*, Dynamic Survey DS17, 2009. https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/
- Karp, R. M. "Reducibility Among Combinatorial Problems." In R. E. Miller and J. W. Thatcher (eds.), *Complexity of Computer Computations*, Plenum Press, 1972, pp. 85–103. https://www.cs.umd.edu/~gasarch/BLOGPAPERS/Karp.pdf
- Feige, U. "A Threshold of ln n for Approximating Set Cover." *Journal of the ACM* 45(4):634–652, 1998. https://dl.acm.org/doi/10.1145/285055.285059
- Fagin, R. "Degrees of acyclicity for hypergraphs and relational database schemes." *Journal of the ACM* 30(3):514–550, 1983. https://dl.acm.org/doi/10.1145/2402.322390
- Beeri, C., Fagin, R., Maier, D., Yannakakis, M. "On the Desirability of Acyclic Database Schemes." *Journal of the ACM* 30(3):479–513, 1983. https://dl.acm.org/doi/10.1145/2402.322389
- Brault-Baron, J. "Hypergraph Acyclicity Revisited." *ACM Computing Surveys* 49(3), 2016 (arXiv:1403.7076, 2014). https://arxiv.org/abs/1403.7076
- Gottlob, G., Leone, N., Scarcello, F. "Hypertree Decompositions and Tractable Queries." arXiv:cs/9812022, 1998; *Journal of Computer and System Sciences* 64(3):579–627, 2002. https://arxiv.org/abs/cs/9812022
- Gottlob, G., Lanzinger, M., Pichler, R., Razgon, I. "Complexity Analysis of Generalized and Fractional Hypertree Decompositions." arXiv:2002.05239, 2020; *Journal of the ACM* 68(5):1–50, 2021. https://arxiv.org/abs/2002.05239 and https://doi.org/10.1145/3457374 (arXiv full text read 2026-09-25)
- Gottlob, G., Miklós, Z., Schwentick, T. "Generalized hypertree decompositions: NP-hardness and tractable variants." *Journal of the ACM* 56(6), article 30, 2009. https://doi.org/10.1145/1568318.1568320 (result as stated in Gottlob et al. 2021)
- Grohe, M., Marx, D. "Constraint Solving via Fractional Edge Covers." *ACM Transactions on Algorithms* 11(1), article 4, 2014. https://doi.org/10.1145/2636918 ; arXiv:1711.04506, https://arxiv.org/abs/1711.04506 (arXiv full text read 2026-09-25; volume and article number from OpenAlex and reference [34] of Gottlob et al. 2021)
- Adler, I., Gottlob, G., Grohe, M. "Hypertree width and related hypergraph invariants." *European Journal of Combinatorics* 28(8):2167–2181, 2007. https://doi.org/10.1016/j.ejc.2007.04.013 (result cited through Grohe and Marx 2014; not read directly)
- Marx, D. "Tractable Hypergraph Properties for Constraint Satisfaction and Conjunctive Queries." *Journal of the ACM* 60(6), article 42, 2013 (preliminary version STOC 2010). https://doi.org/10.1145/2535926 ; arXiv:0911.0801, https://arxiv.org/abs/0911.0801 (abstract read 2026-09-25)
- Moll, L., Tazari, S., Thurley, M. "Computing hypergraph width measures exactly." *Information Processing Letters* 112(6):238–242, 2012. https://doi.org/10.1016/j.ipl.2011.12.002 ; arXiv:1106.4719, https://arxiv.org/abs/1106.4719 (introduction read 2026-09-25)
- Duris, D. "Some characterizations of γ and β-acyclicity of hypergraphs." *Information Processing Letters* 112(16):617–620, 2012. https://doi.org/10.1016/j.ipl.2012.05.005 (content as stated in Brault-Baron 2016)
- Atserias, A., Grohe, M., Marx, D. "Size Bounds and Query Plans for Relational Joins." *SIAM Journal on Computing* 42(4):1737–1767, 2013. https://dblp.org/rec/journals/siamcomp/AtseriasGM13.html
- Fischl, W., Gottlob, G., Longo, D. M., Pichler, R. "HyperBench: A Benchmark and Tool for Hypergraphs and Empirical Findings." *PODS 2019*, pp. 464–480, https://doi.org/10.1145/3294052.3319683 ; extended version *ACM Journal of Experimental Algorithmics* 26:1–40, 2021, https://doi.org/10.1145/3440015 (arXiv:2009.01769, https://arxiv.org/abs/2009.01769)
- Gottlob, G., Lanzinger, M., Okulmus, C., Pichler, R. "Experimental Data for log-k-decomp." Zenodo, 2023, CC BY 4.0 (the HyperBench instances and every published decomposition run; P6's baseline is recomputed from it). https://doi.org/10.5281/zenodo.7180787
- Bonifati, A., Martens, W., Timm, T. "Navigating the Maze of Wikidata Query Logs." *WWW 2019*, pp. 127–138. Figures quoted through Fischl et al. 2021 `[unverified]` against the original.
- BalancedGo, commit `872c662` (v1.7.2-2), MIT. https://github.com/cem-okulmus/BalancedGo ; Gottlob, G., Okulmus, C., Pichler, R. "Fast and parallel decomposition of constraint satisfaction problems." *Constraints* 27(3):284–326, 2022. https://doi.org/10.1007/s10601-022-09332-1
- log-k-decomp, v1.1.0 (commit `5e021dd`), MIT. https://github.com/cem-okulmus/log-k-decomp ; Gottlob, G., Lanzinger, M., Okulmus, C., Pichler, R. "Fast Parallel Hypertree Decompositions in Logarithmic Recursion Depth." *PODS 2022*, pp. 325–336. https://doi.org/10.1145/3517804.3524153
- Biolink Model v4.4.5 (commit `a4180f8`, 2026-09-18), model licence CC0-1.0. https://github.com/biolink/biolink-model ; Unni, D., et al. "Biolink Model: A universal schema for knowledge graphs in clinical, biomedical, and translational science." *Clinical and Translational Science* 15(8):1848–1855, 2022. https://doi.org/10.1111/cts.13302
- Wikidata Query Service (property constraints, fetched 2026-09-24), https://query.wikidata.org/ ; SQID property statistics (dump of 2026-08-10), https://sqid.toolforge.org/data/properties.json ; Wikidata data licence CC0-1.0, https://www.wikidata.org/wiki/Wikidata:Copyright
- Project P6, "Schema width survey": survey table [results/survey.md](../../projects/p6-schema-width/results/survey.md) (commit 7c58957, 2026-09-25), [DESIGN.md](../../projects/p6-schema-width/DESIGN.md), research reports [01, theory and solvers](../../projects/p6-schema-width/research/01-theory-and-solvers.md) and [02, data sources and naming](../../projects/p6-schema-width/research/02-data-sources-and-naming.md), the naming [wd-roles r1](../../projects/p6-schema-width/wd-roles.md), and the checker [khg-width](../../projects/p6-schema-width/khg-width/) (MIT).
- Zhou, D., Huang, J., Schölkopf, B. "Learning with Hypergraphs: Clustering, Classification, and Embedding." *NIPS 2006*. https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html
- Schlag, S., Heuer, T., Gottesbüren, L., Akhremtsev, Y., Schulz, C., Sanders, P. "High-Quality Hypergraph Partitioning." arXiv:2106.08696, 2021; *ACM Journal of Experimental Algorithmics*, 2022. https://arxiv.org/abs/2106.08696 and https://dl.acm.org/doi/10.1145/3529090
- Karypis, G., Aggarwal, R., Kumar, V., Shekhar, S. "Multilevel Hypergraph Partitioning: Applications in VLSI Domain." *IEEE Transactions on Very Large Scale Integration (VLSI) Systems* 7(1):69–79, 1999. Publisher listing consulted; full text not fetched `[unverified]`. https://dl.acm.org/doi/pdf/10.1145/266021.266273
- Voloshin, V. I. *Coloring Mixed Hypergraphs: Theory, Algorithms and Applications*. Fields Institute Monographs 17, American Mathematical Society, 2002. Cited via Ouvrard 2020; not consulted directly `[unverified]`.
