---
title: Metagraphs, ubergraphs, AtomSpace and HypergraphDB — edges that contain edges
type: survey
status: draft
tags: [metagraph, ubergraph, nesting, opencog, atomspace, hyperon, metta, hypergraphdb, recursive, meta-knowledge]
created: 2026-09-20
updated: 2026-09-20
---

# Metagraphs, ubergraphs and hypergraph databases

A plain hypergraph lets a fact involve many entities. It does **not** let a fact be *about* another
fact: `E ⊆ 𝒫(V)` draws a hard line between vertices and edges. Three traditions independently
removed that line — one mathematical (ubergraphs), one from cognitive architecture (OpenCog's
metagraph), one from database engineering (HypergraphDB) — and arrived at almost the same object:
**an edge whose members may be other edges**. This note collects their definitions, compares them,
and says what nesting buys a knowledge hypergraph.

The n-ary side of the story is in
[hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md); the
RDF-side equivalent (triple terms and reifiers) is in
[n-ary-relations-and-reification.md](n-ary-relations-and-reification.md).

## 1. Ubergraphs (Joslyn and Nowak, 2017): the mathematics

The cleanest formalisation is a nine-page note from Pacific Northwest National Laboratory, written
"Partly in service of exploring the formal basis for Georgetown University's AvesTerra database
structure" ([Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547), arXiv:1704.05547,
PNNL-26402). The framing sentence:

> "As hypergraphs generalize graphs by allowing edges to have more than two vertices, ubergraphs
> generalize hypergraphs by allowing edges to contain other edges as vertices. Thus, all graphs are
> hypergraphs and all hypergraphs are ubergraphs."

and the motivation, which is exactly the KHG motivation:

> "The ability to do indirection in graph data structures by 'quoting' or 'pointing to' edges is
> absolutely central in graph-based data science, and is accomplished in such systems by a variety
> of ad hoc mechanisms such as reification. Hypergraphs are frequently used as part of that
> armamentarium, but ubergraphs are a more robust representation framwork [sic]."

The definition is by iterated power set. With `P₀ = X` and `Pᵢ = 𝒫(⋃_{j<i} P_j)`:

> "**Definition 4.** A depth k ubergraph U is a pair (V, E) where V is a set of fundamental vertices
> and E ⊆ 𝒫(V)_k is a finite set of uberedges. Additionally, if s ∉ V belongs to an edge, we require
> that s is itself an edge."
> ([Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547))

with "**Note 2.** Every hypergraph is a depth 0 ubergraph." Their worked example,
`E = {{1}, {1,3}, {1,3,e₁}, {2,e₂}, {1,e₄}}`, is a fact that contains a fact that contains a fact.

Two structural results matter for implementers:

- **The incidence structure becomes a DAG.** They generalise the Levi (incidence) graph to the
  *uber-Levi graph*, with "a directed edge from x to y if x is a member of y in U", and observe:
  "**Note 3.** The uber-Levi graph is a directed acyclic graph (DAG). The roots (vertices with no
  in-neighbors) correspond to the fundamental vertices of U ... Moreover, every DAG yields an
  ubergraph." So a nested knowledge hypergraph *is* a DAG over atoms, and can be stored as one.
- **Self-reference costs you set theory.** Dropping the requirement that non-vertices in an edge be
  edges admits cycles: "Allowing (ultimately) expressions like e = {e}, and thus arbitrary cycles in
  the uber-Levi graph, violates the axiom of foundation. The vertex set is no longer well defined,
  and non-well-founded sets would need to be invoked"
  ([Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547)).

The paper is explicit that it treats only **undirected** ubergraphs: "Direction and/or orientation
could prove very valuable, but await further consideration" — a gap, since knowledge hyperedges are
usually ordered or role-labelled.

## 2. The OpenCog metagraph

OpenCog's companion text defines the pair side by side:

> "Formally, a hypergraph is: A set of vertexes V ... A set of hyperedges E ... where each hyperedge
> ek is an ordered list of vertexes drawn from the set V. ... A metagraph is very nearly the same: A
> set of nodes V ... A set of links E ... where each hyperedge ek is an ordered list of nodes, or
> other links, or a mixture. They are arranged to be acyclic (to form a directed acyclic graph)."
> ([Vepštas, 2020–2023](https://github.com/opencog/atomspace/blob/master/opencog/sheaf/docs/ram-cpu.pdf))

The differences from an ubergraph are deliberate and both matter for knowledge:

| | ubergraph ([Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547)) | metagraph ([Vepštas](https://github.com/opencog/atomspace/blob/master/opencog/sheaf/docs/ram-cpu.pdf)) |
|---|---|---|
| membership | **set** — unordered, no repeats | **ordered list** — order and repetition carry meaning |
| acyclicity | a consequence of foundation, optional | imposed by construction (DAG) |
| labels | none in the base definition | Atom types, plus attached Values |

Ordered lists are what let a metagraph carry positional roles directly; a set-based uberedge cannot
distinguish `r(a,b)` from `r(b,a)`.

Goertzel's Hyperon overview restates the hierarchy in one sentence, quoting Alexey Potapov:

> "While ordinary graphs can be described as a collection of triples, and hypergraphs are
> collections of tuples, metagraphs are collections of trees, i.e., each edge is a tree-like
> connection of nodes or, alternatively, each edge is a tuple connecting any number of nodes and
> other edges. This representation is crucial for representing complex statements and arbitrary
> knowledge, and it is also convenient to represent program code."
> ([Goertzel et al., 2023](https://arxiv.org/abs/2310.18318))

and gives the historical note that the AtomSpace "was a structure originally called a 'generalized
hypergraph', a verbiage later tweaked to 'Metagraph'. Basically: a graph with links that can span
multiple nodes, and links that can point to links or larger subgraphs, and both nodes and links can
be labeled with various more or less complex weights or structures ... Nodes and links in this
framework are both referred to as Atoms" (same source).

The same passage contains the practical argument against encoding metagraphs in a graph store:
"While metagraphs can be encoded in simpler data structures like ordinary graphs, their traversal,
indexing and retrieval algorithms are not optimized for metagraph encodings. The latter requires
introducing auxiliary nodes, which should be treated specially in indexing and traversal"
([Goertzel et al., 2023](https://arxiv.org/abs/2310.18318)). That is the nesting-specific version of
the reification complaint.

## 3. AtomSpace: Atoms and Values

The AtomSpace README describes itself as "an in-RAM knowledge representation (KR) database with an
associated query engine and graph-re-writing system" and "a kind of in-RAM generalized hypergraph
(metagraph) database" ([OpenCog AtomSpace README](https://github.com/opencog/atomspace), checked
2026-09-20). Its central modelling decision is a split that KHG schemas should copy:

- **Atoms** are "immutable, globally unique, typed s-expressions", indexed for search — the stable
  graph structure.
- **Values** hold "rapidly-changing data, including streaming data", including truth values and
  probabilities, and are *not* indexed.
  ([OpenCog AtomSpace README](https://github.com/opencog/atomspace), checked 2026-09-20)

In KHG terms: the hyperedge identity and its role bindings are Atoms; confidence, counts and
timestamps are Values. The README's justification for the whole design is that "a metagraph store is
literally just-plain better than a graph store" — opinion, but a well-argued one, and the query
engine claims capabilities absent from conventional graph databases (inverted pattern search,
meet/join, negation, for-all predicates).

**Atomese** is the language of Atom types; it "comprises structural primitives meant to describe
structural relationships" and includes executable constructs, functioning "as abstract syntax trees
for computation" (same source). A knowledge hypergraph and a program are the same kind of object
here — which is the point of the next section.

## 4. Hyperon and MeTTa

OpenCog Hyperon is the current rewrite. Its own description of itself: "Hyperon is a new, mostly
from-the-ground-up rewrite/redesign of the OpenCog AGI framework"
([Goertzel et al., 2023](https://arxiv.org/abs/2310.18318), arXiv:2310.18318, submitted 19 September
2023). The two core constructs:

> "The core construct of Hyperon, like that of OpenCog and Novamente Cognition Engine before it, is
> the Atomspace, a metagraph comprised of nodes and links with complex interlinkage structures. This
> metagraph is highly versatile and allows for labeling nodes and links with various kinds of data,
> including subgraphs. This labeling mechanism can also facilitate the embedding of complex type
> systems in the metagraph."

> "A new ingredient of Hyperon ... is the programming language called MeTTa. MeTTa programs are
> sub-metagraphs in Atomspace, and are interpretable as procedures for rewriting portions of
> Atomspace into modified or additional portions of Atomspace."
> ([Goertzel et al., 2023](https://arxiv.org/abs/2310.18318))

MeTTa is "an 'Atomese 2' language called MeTTa (Meta Type Talk)" designed as "a successor to the
OpenCog Classic Atomese language with clear semantics supporting meta-language features, different
types of inference" ([hyperon-experimental README](https://github.com/trueagi-io/hyperon-experimental),
checked 2026-09-20), which also states the project is "currently at an active pre-alpha stage of
development and experimentation" — so treat it as research infrastructure, not a production store.

The formal programme behind it is metagraph rewriting: MeTTa is "designed as a meta-language with
very basic and general facilities for handling symbols, groundings, variables, types, substitutions
and pattern matching", formalised "as a system of metagraph rewrite rules ... given that the
latter's core component is a distributed metagraph knowledge store (the Atomspace)", and "The
metagraph rewrite rules constituting MeTTa programs can also be represented as metagraphs, giving a
natural model for MeTTa reflection and self-modifying code"
([Goertzel, 2021](https://arxiv.org/abs/2112.08272), arXiv:2112.08272).

Typing is not built in but built *within*: MeTTa "does not possess types as it is fundamentally just
rewrite rules on the metagraph that are embedded within the metagraph. However, since types are
merely portions of the metagraph that are attached to selected nodes and links, type systems can be
built within it" ([Goertzel et al., 2023](https://arxiv.org/abs/2310.18318)). The cost is admitted
in the same paragraph: "The challenge remains in writing efficient type checkers for these elaborate
types."

## 5. HypergraphDB (Iordanov, 2010)

The database-engineering instance. Its abstract:

> "We present HyperGraphDB, a novel graph database based on generalized hypergraphs where hyperedges
> can contain other hyperedges. This generalization automatically reifies every entity expressed in
> the database thus removing many of the usual difficulties in dealing with higher-order
> relationships."
> ([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf))

The data model, in four sentences:

> "In the HyperGraphDB data model, the basic representational unit is called an atom. Each atom has
> an associated tuple of atoms called its target set. The size of the target set is called the
> atom's arity. Atoms of arity 0 are called nodes and atoms of arity > 0 are called links. The
> incidence set of an atom x is the set of atoms that have x as a member of their target set (i.e.
> the set of links pointing to x)."
> ([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf))

with the deliberate choice of **tuples over sets**: "The use of tuples instead of sets for an atom's
target set is not the only possible choice; both can be supported, but we have focused on the former
as the most practical by far" — the same choice Vepštas's metagraph makes, and the opposite of
Joslyn and Nowak's.

Orthogonally, "each atom has an associated strongly typed value. Values are of arbitrary types, and
types themselves are atoms ... Atoms are the semantic entities that form the hypergraph structure,
while values are typed data that may be structured or not" — again the Atoms/Values split, here with
types reified as atoms (the "extensible type tower").

Iordanov credits the model: "the implementation of a generalized hypergraph model independently
proposed by Harold Boley [4] and Ben Goertzel [5]", which ties HypergraphDB back to Boley's 1977
directed recursive labelnode hypergraphs
([Boley, 1977](https://www.sciencedirect.com/science/article/abs/pii/0004370277900145)) and to
OpenCog. He is also explicit about the semantic-web motivation:

> "One common criticism of RDF stores is the limited expressiveness of binary predicates, a problem
> solved by HyperGraphDB's n-ary relationships. Two other prominent issues are contextuality
> (scoping) and reification. ... In this transformation a single triplet yields 4 triplets, which is
> unnatural, breaks algorithms relying on the original representation, and suffers from both time
> and space inefficiencies."
> ([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf))

He notes the set-theoretic subtlety that Joslyn and Nowak also hit: including hyperedges in the
vertex universe means "a set theoretic formalization becomes harder because the foundation axiom no
longer holds. Such hypergraphs are isomorphic to general (i.e. allowing cycles) directed graphs and
they have been studied from a set-theoretic perspective by P. Az[c]el" — the same non-well-founded
set theory that MeTTa has been used to implement
([Goertzel et al., 2023](https://arxiv.org/abs/2310.18318)).

**Status.** HypergraphDB is "a general purpose, extensible, portable, distributed, embeddable,
open-source data storage mechanism ... a graph database designed specifically for artificial
intelligence and semantic web projects", Java, Apache-2.0
([hypergraphdb/hypergraphdb](https://github.com/hypergraphdb/hypergraphdb), checked 2026-09-20).
Its published javadoc is for version 1.3-SNAPSHOT
([HypergraphDB API docs](https://hypergraphdb.org/docs/javadoc/org/hypergraphdb/HyperGraph.html),
checked 2026-09-20); no 2024–2026 release announcement was found in a primary source during this
research run `[unverified]`. Treat it as a long-lived, lightly maintained reference implementation.

## 6. Comparison

| | Ubergraph | OpenCog metagraph / AtomSpace | HypergraphDB |
|---|---|---|---|
| primary reference | [Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547) | [Vepštas, 2020–2023](https://github.com/opencog/atomspace/blob/master/opencog/sheaf/docs/ram-cpu.pdf); [Goertzel et al., 2023](https://arxiv.org/abs/2310.18318) | [Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf) |
| edge members | sets of vertices and edges | ordered lists of Atoms | tuple of atoms (the *target set*) |
| nesting depth | explicit parameter `k` | unbounded, acyclic | unbounded |
| node/edge distinction | fundamental vertices vs uberedges | none — both are Atoms | none — arity 0 is a node, arity > 0 a link |
| types | none | Atom type system, extensible; MeTTa types built in-graph | extensible type tower, types are atoms |
| mutable annotations | none | Values (truth values, streams), unindexed | atom values, immutable, replaceable |
| cycles | violate foundation; excluded | excluded (DAG) | allowed; needs non-well-founded sets |
| implementation | none (a definition) | C++/Scheme AtomSpace; Rust/Python Hyperon (pre-alpha) | Java, BerkeleyDB, Apache-2.0 |

## 7. What nesting buys a knowledge hypergraph

1. **Free reification.** "This generalization automatically reifies every entity expressed in the
   database" ([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)). Every fact has an
   identity, so provenance, confidence and disagreement attach without a pattern.
2. **Meta-knowledge as ordinary knowledge.** "X says that P", "P was retracted in 2024", "rule R
   derived P from Q" are facts whose arguments include facts. In RDF this needs triple terms and
   reifiers; in a metagraph it needs nothing new.
3. **Rules as data.** MeTTa programs are sub-metagraphs, so inference rules live in the same store as
   the facts they rewrite ([Goertzel, 2021](https://arxiv.org/abs/2112.08272)). Compare directed
   hyperedges-as-Horn-clauses in
   [directed-and-typed-hyperedges-for-knowledge.md](directed-and-typed-hyperedges-for-knowledge.md).
4. **Contexts and scoping.** Iordanov lists contextuality alongside reification as the RDF problems
   the model dissolves ([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)); a context
   is just a link whose target set is a set of links.

## 8. Costs and caveats

- **No benchmarks.** None of the standard n-ary link-prediction datasets contains nested facts; the
  benchmark landscape in
  [benchmarks-derived-from-freebase-and-wikidata.md](benchmarks-derived-from-freebase-and-wikidata.md)
  is entirely flat. Claims about the value of nesting for learning are therefore untested at the
  level the flat models are tested.
- **Foundations.** Unrestricted self-reference leaves standard set theory
  ([Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547);
  [Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)). Most practical schemas should
  require acyclicity, as the metagraph definition does.
- **Maturity.** Hyperon is self-described as pre-alpha
  ([hyperon-experimental](https://github.com/trueagi-io/hyperon-experimental), checked 2026-09-20);
  HypergraphDB's public version is a 1.3 snapshot. TypeDB's nested relations are the closest thing
  to a maintained, schema-checked implementation of the same idea; see
  [ontologies-and-schemas-for-n-ary-knowledge.md](ontologies-and-schemas-for-n-ary-knowledge.md).
- **AGI framing.** The OpenCog literature argues for metagraphs as a substrate for general
  intelligence. That is a research programme, not an established result, and the KR claims should be
  read separately from the AGI claims.

## Sources

- Joslyn, C., Nowak, K. *Ubergraphs: A Definition of a Recursive Hypergraph Structure.* arXiv:1704.05547, 18 April 2017; PNNL-26402. https://arxiv.org/abs/1704.05547
- Vepštas, L. *Graphs, Metagraphs, RAM, CPU.* OpenCog technical text, versions 2020–2023. https://github.com/opencog/atomspace/blob/master/opencog/sheaf/docs/ram-cpu.pdf
- OpenCog Foundation. *AtomSpace README.* GitHub, checked 2026-09-20. https://github.com/opencog/atomspace
- Goertzel, B., Bogdanov, V., Duncan, M., Duong, D., Goertzel, Z., Horlings, J., Iklé, M., Meredith, L. G., Potapov, A., de Senna, A. L., Seid Andres Suarez, H., Vandervorst, A., Werko, R. *OpenCog Hyperon: A Framework for AGI at the Human Level and Beyond.* arXiv:2310.18318, 19 September 2023. https://arxiv.org/abs/2310.18318
- Goertzel, B. *Reflective Metagraph Rewriting as a Foundation for an AGI "Language of Thought".* arXiv:2112.08272, 12 December 2021. https://arxiv.org/abs/2112.08272
- TrueAGI. *hyperon-experimental README.* GitHub, checked 2026-09-20. https://github.com/trueagi-io/hyperon-experimental
- Iordanov, B. *HyperGraphDB: A Generalized Graph Database.* WAIM 2010 workshops, Springer LNCS. https://hypergraphdb.org/docs/hypergraphdb.pdf
- HypergraphDB project. *hypergraphdb/hypergraphdb* repository (Apache-2.0), checked 2026-09-20. https://github.com/hypergraphdb/hypergraphdb
- HypergraphDB project. *HyperGraph (HyperGraphDB Core 1.3-SNAPSHOT API).* Javadoc, checked 2026-09-20. https://hypergraphdb.org/docs/javadoc/org/hypergraphdb/HyperGraph.html
- Boley, H. *Directed recursive labelnode hypergraphs: A new representation-language.* Artificial Intelligence 9(1):49–85, 1977. https://www.sciencedirect.com/science/article/abs/pii/0004370277900145
