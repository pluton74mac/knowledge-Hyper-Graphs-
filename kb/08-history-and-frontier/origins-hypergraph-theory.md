---
title: Origins — Berge, the mathematical lineage, and the first applications
type: survey
status: draft
tags: [hypergraph, history, berge, acyclicity, databases, vlsi, directed-hypergraph]
created: 2026-09-20
updated: 2026-09-20
---

# Origins: where the hypergraph came from, and what it was first used for

This note covers the period **c. 1960 – 1993**: the invention of the hypergraph as a mathematical
object by Claude Berge, its consolidation into two canonical books, and the three application areas
that first made it an engineering tool — relational database theory, VLSI/parallel-computing
partitioning, and directed hypergraphs for logic and flow problems. The dated one-line version is in
[timeline.md](timeline.md). The formal definitions live in
[../01-foundations/hypergraph-definitions.md](../01-foundations/hypergraph-definitions.md).

The point of the note for this knowledge base: **none of this early work was about "knowledge."**
Hypergraphs entered computing as a *combinatorial* and later a *structural* device — a way to talk
about set systems, about which queries are tractable, and about how to cut a circuit. The
"knowledge hypergraph" reading, in which a hyperedge is a *fact*, is grafted on much later (see
[knowledge-representation-lineage.md](knowledge-representation-lineage.md)). The one early strand
that already carries the fact-reading is Fagin's: *a relational database is a hypergraph*, and a
tuple of a relation is a hyperedge.

## 1. Berge and the naming of the object (c. 1960 – 1989)

### 1.1 The idea

Claude Berge (1926–2002), of the CNRS and the Centre d'analyse et de mathématique sociales in Paris,
is the person who named and systematised the hypergraph. He dates the idea himself, in the preface
to the 1989 English edition:

> "The idea of looking at a family of sets from this standpoint took shape around 1960. In regarding
> each set as a 'generalised edge' and in calling the family itself a 'hypergraph', the initial idea
> was to try to extend certain classical results of Graph Theory such as the theorems of Turán and
> König."
> ([Berge, *Hypergraphs*, North-Holland, 1989, publisher's description](https://shop.elsevier.com/books/hypergraphs/berge/978-0-444-87489-4))

Two things in that sentence matter for us. First, the motivation was *unification*: Berge continues
that the generalisation "often led to simplification; moreover, one single statement, sometimes
remarkably simple, could unify several theorems on graphs" (same source). Hypergraphs were invented
as an abstraction that makes several graph theorems instances of one theorem — exactly the argument
that KHG papers make sixty years later about n-ary facts versus triples. Second, the definition is
*set-theoretic and undirected*: an edge is a subset of vertices. Direction, labels, roles, ordering
and nesting — everything a knowledge hypergraph needs — are later additions by other people.

### 1.2 The books

| Work | Year | Publisher | Note |
|---|---|---|---|
| *Graphes et hypergraphes* | 1970 | Dunod, Paris (Monographies universitaires de mathématiques 37), 502 pp. | The book that put "hypergraphe" into circulation ([Open Library record](https://openlibrary.org/books/OL5096671M/Graphes_et_hypergraphes.); [WorldCat](https://search.worldcat.org/title/graphes-et-hypergraphes/oclc/301677997)) |
| *Graphs and Hypergraphs* | 1973 | North-Holland Mathematical Library vol. 6, xiv+528 pp., trans. Edward Minieka | The standard English reference ([Internet Archive](https://archive.org/details/graphshypergraph0000berg)) |
| *Hypergraphes: combinatoire des ensembles finis* | 1987 | Gauthier-Villars, Paris | Second part of the 1970 book, rewritten and expanded ([Google Books record](https://books.google.com/books/about/Hypergraphes.html?id=sfTuAAAAMAAJ)) |
| *Hypergraphs: Combinatorics of Finite Sets* | 1989 | North-Holland Mathematical Library vol. 45, ix+255 pp., ISBN 0-444-87489-5 | Explicitly "translation of: *Hypergraphes*" ([Internet Archive catalogue record](https://archive.org/details/hypergraphscombi0000berg)) |

The timeline note marked the 1989 English edition `[unverified]`; it is now verified from the
Internet Archive catalogue record, which carries both the 1989 imprint and the
"Translation of: Hypergraphes" statement. One caveat: Elsevier's own shop page for volume 45 prints
a publication date of **1 May 1984**, which contradicts every library record and the existence of
the 1987 French original; treat the Elsevier date as a metadata error `[unverified]`
([Elsevier shop page](https://shop.elsevier.com/books/hypergraphs/berge/978-0-444-87489-4)).

A common secondary claim, that "hypergraphs were introduced in 1973," comes from reading the
English translation date as the origin ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). The
1970 French edition is the better citation, and Berge's own dating is "around 1960."

### 1.3 What Berge's theory actually gives a KHG builder

Berge's programme was to lift graph theorems: colourings, matchings, transversals (hitting sets),
Helly-type properties, balanced and normal hypergraphs, and the hypergraph versions of König's and
Turán's theorems. The practical residue for knowledge work is a vocabulary — *incidence*, *dual
hypergraph*, *transversal*, *line graph*, *2-section/clique expansion*, *host graph* — that
reappears constantly in later machine-learning and database papers, usually without attribution.
The clique expansion in particular (replace each hyperedge by a clique on its vertices) is Berge's
"2-section"; a large 2026 expressivity result is essentially a theorem about exactly how much that
expansion destroys ([Jiang et al., 2026](https://arxiv.org/abs/2605.13690), see
[machine-learning-era.md](machine-learning-era.md)).

## 2. Databases: a relational schema *is* a hypergraph (1981–1983)

The first large-scale reading of a knowledge base as a hypergraph is in relational database theory.
The construction: take the attributes of a database as vertices, and each relation schema as a
hyperedge containing its attributes. Questions about join processing then become questions about
the shape of that hypergraph.

The two companion papers, both in *Journal of the ACM* 30(3), July 1983, are the canonical
statements:

- Beeri, Fagin, Maier and Yannakakis, "On the Desirability of Acyclic Database Schemes,"
  *JACM* 30(3):479–513 ([DOI 10.1145/2402.322389](https://doi.org/10.1145/2402.322389)). This paper
  proves the equivalence of a long list of apparently unrelated "good behaviour" properties of a
  database scheme — among them that the join dependency is equivalent to a set of multivalued
  dependencies, that every join is computable by semijoins, and that the scheme has a join tree —
  with one structural property of the associated hypergraph: **acyclicity**.
- Fagin, "Degrees of Acyclicity for Hypergraphs and Relational Database Schemes," *JACM*
  30(3):514–550 ([DOI 10.1145/2402.322390](https://doi.org/10.1145/2402.322390)). Fagin's point is
  that "unlike ordinary graphs, there are several natural, non-equivalent notions of acyclicity for
  hypergraphs," and he separates them into the now-standard **α-, β- and γ-acyclicity** hierarchy
  (α weakest/most general, γ strongest), each equivalent to its own bundle of database properties.

Two consequences carry forward into knowledge hypergraphs:

1. **Tractability is a property of the hypergraph, not of the data.** This is the ancestor of every
   later "structural decomposition" result. It runs through hypertree decompositions
   ([Gottlob, Leone, Scarcello, arXiv Dec 1998](https://arxiv.org/abs/cs/9812022); *JCSS* 64(3),
   2002), which give a width measure under which conjunctive-query answering is polynomial, and it
   reappears in 2026 as the index of a hypergraph-neural-network expressivity hierarchy
   ([Jiang et al., 2026](https://arxiv.org/abs/2605.13690)).
2. **An n-ary fact is a hyperedge with named roles.** A relation `Booking(passenger, flight, seat,
   date)` is precisely the object that KHG papers rediscover as `r(e1,…,ek)` or as a role–value set.
   The relational model had it, with a type system, forty years earlier. The modern question is not
   "can we represent n-ary facts" — SQL always could — but "can we do open-world inference,
   embedding and retrieval over them," which is the subject of
   [machine-learning-era.md](machine-learning-era.md).

A useful modern re-reading of the acyclicity zoo is Brault-Baron's survey
([*ACM Computing Surveys* 49(3), 2016, DOI 10.1145/2983573](https://dl.acm.org/doi/10.1145/2983573)).

## 3. Engineering: partitioning (1997–1999)

The second early application made hypergraphs industrial. In VLSI circuit design a *net* connects
an arbitrary number of pins, so a circuit is natively a hypergraph and only unnaturally a graph;
minimising the number of nets cut when a circuit is split across chips or regions is the
**hypergraph partitioning** problem.

- Karypis, Aggarwal, Kumar and Shekhar, "Multilevel hypergraph partitioning: applications in VLSI
  domain," *IEEE Transactions on VLSI Systems* 7(1):69–79, March 1999
  ([DOI 10.1109/92.748202](https://doi.org/10.1109/92.748202)) — the multilevel coarsen/partition/
  refine scheme behind **hMETIS**.
- Çatalyürek and Aykanat, "Hypergraph-partitioning-based decomposition for parallel sparse-matrix
  vector multiplication," *IEEE Transactions on Parallel and Distributed Systems* 10(7):673–693,
  July 1999 ([DOI 10.1109/71.780863](https://doi.org/10.1109/71.780863)) — the result behind
  **PaToH**, and the paper that showed hypergraph partitioning models communication volume in
  parallel sparse linear algebra *exactly*, where graph partitioning only approximates it.

Why this matters here: partitioning is the reason robust, scalable hypergraph code existed at all
before 2019, and it fixed the default computational idioms — incidence matrices, coarsening,
multilevel refinement — that hypergraph learning libraries later inherited. It is also the clearest
historical case of the general argument for hypergraphs: the graph reduction (each net becomes a
clique) gives the *wrong objective function*, not merely a less convenient one.

Scheduling and timetabling are usually named as a third early application area (a set of
simultaneously-conflicting events is a hyperedge, so timetabling is hypergraph colouring). This is
real but the literature is diffuse and the canonical citation is Berge's own colouring chapters
rather than a landmark applied paper; treat any single "first scheduling application" attribution
as `[unverified]`.

## 4. Direction: Gallo et al. and the rule-shaped hyperedge (1993)

Berge's hyperedges are undirected sets. A *fact* often is not: `treats(drug, disease, dose)` has
argument positions, and a *rule* has premises and a conclusion. The standard reference that supplies
direction is:

> Giorgio Gallo, Giustino Longo, Stefano Pallottino, Sang Nguyen, "Directed hypergraphs and
> applications," *Discrete Applied Mathematics* 42(2–3):177–201, April 1993
> ([DOI 10.1016/0166-218X(93)90045-P](https://doi.org/10.1016/0166-218X%2893%2990045-P))

A directed hyperedge (hyperarc) is an ordered pair `(T, H)` of a tail set and a head set.
Specialisations: a **B-arc** has a singleton head, an **F-arc** a singleton tail, a **BF-arc**
neither. The paper develops paths, hyperpaths, cuts and shortest-hyperpath algorithms, and points
at the application areas that make it relevant to knowledge work:

- **Horn clauses / propositional logic.** A Horn clause `a1 ∧ … ∧ an → b` is exactly a B-arc
  `({a1,…,an}, {b})`, and forward chaining is a shortest-hyperpath computation. This is the direct
  formal link between a *directed hypergraph* and a *rule base*.
- **AND–OR graphs and problem reduction**, i.e. planning and search.
- **Relational databases** and functional dependencies.
- Flow and transit-network problems, which is where the authors came from.

So the modern KHG literature inherits two different directed models with different ancestors:
Gallo's `(tail, head)` hyperarc, which is rule-shaped, and the *ordered-tuple* hyperedge
`r(e1,…,ek)` of the embedding literature, which is relation-shaped and comes from the relational
model. They are not the same thing, and conflating them is a recurring source of confusion; see
[../02-knowledge-representation/what-is-a-knowledge-hypergraph.md](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md).

## 5. What the origins period did *not* settle

Open at the end of 1993, and in several cases still open:

- **No agreed notion of a typed, role-labelled, directed hyperedge.** Berge gives sets, Gallo gives
  tail/head, the relational model gives named attributes. A single formalism covering all three is
  still being argued over in 2026.
- **No serialisation.** There was no interchange format for hypergraphs for another thirty years;
  see [standards-convergence.md](standards-convergence.md) on HIF (2024–2025).
- **No open-world semantics.** Database hypergraphs are closed-world; knowledge bases are not.
- **No statistical/learning layer.** That arrives in 2006 (see
  [machine-learning-era.md](machine-learning-era.md)).

## Sources

- Berge, C. *Graphes et hypergraphes*. Dunod, Paris, 1970, 502 pp. https://openlibrary.org/books/OL5096671M/Graphes_et_hypergraphes. ; WorldCat record https://search.worldcat.org/title/graphes-et-hypergraphes/oclc/301677997
- Berge, C. *Graphs and Hypergraphs*. North-Holland Mathematical Library vol. 6, 1973. https://archive.org/details/graphshypergraph0000berg
- Berge, C. *Hypergraphes: combinatoire des ensembles finis*. Gauthier-Villars, Paris, 1987. https://books.google.com/books/about/Hypergraphes.html?id=sfTuAAAAMAAJ
- Berge, C. *Hypergraphs: Combinatorics of Finite Sets*. North-Holland Mathematical Library vol. 45, 1989, ix+255 pp. Catalogue record (states "Translation of: Hypergraphes"): https://archive.org/details/hypergraphscombi0000berg ; publisher page with preface text: https://shop.elsevier.com/books/hypergraphs/berge/978-0-444-87489-4
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 12 Feb 2020. https://arxiv.org/abs/2002.05014
- Beeri, C., Fagin, R., Maier, D., Yannakakis, M. "On the Desirability of Acyclic Database Schemes." *Journal of the ACM* 30(3):479–513, July 1983. https://doi.org/10.1145/2402.322389
- Fagin, R. "Degrees of Acyclicity for Hypergraphs and Relational Database Schemes." *Journal of the ACM* 30(3):514–550, July 1983. https://doi.org/10.1145/2402.322390
- Brault-Baron, J. "Hypergraph Acyclicity Revisited." *ACM Computing Surveys* 49(3), 2016. https://dl.acm.org/doi/10.1145/2983573
- Gottlob, G., Leone, N., Scarcello, F. "Hypertree Decompositions and Tractable Queries." arXiv:cs/9812022, Dec 1998; *Journal of Computer and System Sciences* 64(3):579–627, 2002. https://arxiv.org/abs/cs/9812022
- Karypis, G., Aggarwal, R., Kumar, V., Shekhar, S. "Multilevel hypergraph partitioning: applications in VLSI domain." *IEEE Transactions on VLSI Systems* 7(1):69–79, 1999. https://doi.org/10.1109/92.748202
- Çatalyürek, Ü. V., Aykanat, C. "Hypergraph-partitioning-based decomposition for parallel sparse-matrix vector multiplication." *IEEE Transactions on Parallel and Distributed Systems* 10(7):673–693, 1999. https://doi.org/10.1109/71.780863
- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. "Directed hypergraphs and applications." *Discrete Applied Mathematics* 42(2–3):177–201, April 1993. https://doi.org/10.1016/0166-218X%2893%2990045-P
- Jiang, F., Li, Y., Feng, Y., Zheng, K., Niu, L., Ramasubramanian, B., Alomair, B., Bushnell, L., Poovendran, R. "The WidthWall: A Strict Expressivity Hierarchy for Hypergraph Neural Networks." arXiv:2605.13690, 13 May 2026. https://arxiv.org/abs/2605.13690
