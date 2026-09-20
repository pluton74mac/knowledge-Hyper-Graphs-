---
title: "Every hypergraph is a bipartite graph — so why bother?"
type: comparison
status: draft
tags: [bipartite, incidence-graph, levi-graph, hypergraph, debate, clique-expansion, 2-section, null-models, random-walks]
created: 2026-09-20
updated: 2026-09-20
---

# The hypergraph-vs-bipartite-graph debate

This is the sharpest objection to the whole enterprise, and it deserves a straight answer rather
than a slogan. The objection runs:

> A hypergraph `H = (V, E)` is *exactly* its incidence structure. Put the vertices on one side, the
> hyperedges on the other, join `v` to `e` iff `v ∈ e`, and you have a bipartite graph that contains
> every bit of information the hypergraph did. Bipartite graphs are graphs. Graphs have fifty years
> of algorithms, a dozen mature databases, two ISO/W3C query languages and every GNN library. So the
> hypergraph adds a word, not a capability.

The objection is **formally correct and practically incomplete**. This note separates those two
halves.

## 1. The formal claim is true, and everyone in the field concedes it

Battiston et al.'s review is the standard reference for higher-order network representations, and it
states the equivalence without hedging: choosing the two node sets to be the original vertex set and
the set of interactions, "the links in the bipartite graph connect a node (in V) to the interactions
(of arbitrary order) in which it takes part", and "It is easy to see that the entire information in
our toy model is preserved when interactions are described as a bipartite graph. In fact, this
representation is very general and can indeed well mimic most interaction structures"
([Battiston et al., 2020](https://arxiv.org/abs/2006.01764)). The same review notes that the
hypergraph incidence matrix "can also be seen as the adjacency matrix of a bipartite graph with two
node sets one of size n and one of size m".

Aksoy et al. make it a theorem: "there is a bijection between hypergraphs and bicolored graphs"
([Aksoy, Joslyn, Ortiz Marrero, Praggastis, Purvine, 2020](https://arxiv.org/abs/1906.11295)).

And the concession appears inside the hypergraph-RAG literature itself. HyperGraphRAG's
**Proposition 2 is literally "A bipartite graph can losslessly preserve and query a knowledge
hypergraph"** ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)) — the system stores its
"knowledge hypergraph" as a bipartite graph `G_B` over `V ∪ E_H`. So the strongest recent advocacy
paper proves the sceptic's premise and then argues from it.

**Do not, therefore, argue that a bipartite encoding loses information. It does not.**

## 2. One technical correction the objection usually gets wrong

A hypergraph is *not* in bijection with a bipartite graph. It is in bijection with a **bicolored**
graph — a bipartite graph *together with a chosen bipartition*. Aksoy et al.:

> "bicolored graphs specify a fixed bicoloring f and differ from bipartite graphs, which are graphs
> admitting some bicoloring. Accordingly, a bipartite graph with k connected components has 2^k
> possible bicolorings, each of which may correspond to a distinct hypergraph."
> ([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295))

This matters more than it sounds. If you hand someone a bipartite graph with no labelling of which
side is "elements" and which is "groups", they cannot reconstruct your hypergraph — and with k
components there are 2^k candidate reconstructions. In a knowledge setting the two sides are entities
and facts; confusing them is a category error, not a relabelling. The hypergraph formalism carries
that distinction in its type; the bipartite formalism carries it in a convention.

The dual point follows: "which class of objects one designates as 'vertices' versus 'hyperedges' in a
hypernetwork may also be arbitrarily chosen. However, hypergraph properties and methods may be
vertex-based or edge-based, and hence differ depending on which choice is made"
([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295)). Hypergraph *duality* is a first-class
operation; there is no equally natural operation on an un-bicolored bipartite graph.

## 3. What is genuinely gained — five arguments, ranked by strength

### 3.1 Some computations do not reduce (strongest argument)

This is the only argument that is a *theorem-shaped* claim rather than an ergonomics claim. Benson,
Gleich and Higham state both directions crisply. Reduction works for some problems:

> "Even problems posed on hypergraphs may reduce to a graph computation; for instance, one can find
> the connected components of a hypergraph by computing connected components of a related bipartite
> graph." ([Benson, Gleich, Higham, 2021](https://arxiv.org/abs/2103.05031))

And fails for others. Consider a random walk that hops node → hyperedge → node:

> "This process is equivalent to a random walk on the bipartite network that represents the
> hypergraph where we 'ignore' or 'censor' the nodes representing the hyperedges. This, in turn,
> corresponds to a random walk on a weighted graph with the same node set as the hypergraph, and the
> process is Markovian on the state space of the nodes. In this case, the questions about the process
> can then be answered via existing graph-based and matrix-based techniques."

Now change one thing — require consecutive hyperedges to share **two** nodes rather than one:

> "This new procedure defines an edge process that cannot easily be represented using traditional
> graph and matrix techniques, as there is no notion of 'where' the walk is that admits a
> simplification. The process is no longer Markovian on the state space of the nodes but more complex
> machinery will compute probabilities associated with the process via a related Markov chain."
> ([Benson, Gleich, Higham, 2021](https://arxiv.org/abs/2103.05031))

That is the crux. The *width* of an incidence — how much two groups overlap — is a hypergraph-native
quantity that has no analogue in a bipartite adjacency structure treated as an ordinary graph. Aksoy
et al. build a whole framework (`s`-walks, `s`-connected components, `s`-betweenness,
`s`-clustering coefficients) on it: "High-order s-walks (s > 1) are possible on hypergraphs whereas
for graphs, all walks are 1-walks" ([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295)).

In a knowledge setting the analogue is direct: "which facts share at least two entities?" is the
hyperedge-overlap question that drives multi-hop retrieval, and it is awkward to express as a
node-level walk.

### 3.2 Standard graph statistics are undefined or misleading on the bipartite encoding

Bipartite graphs have no odd cycles, so every triangle-based measure vanishes. Battiston et al.:
"This concept does not generalize well to bipartite graphs, because triangles — as any other odd
cycle — do not exist in bipartite graphs" ([Battiston et al., 2020](https://arxiv.org/abs/2006.01764)).
Aksoy et al. make the same point as a reductio of the "it's just a graph" position:

> "interpreting this in light of the fact that bicolored graphs are graphs does not mean graph
> theoretic methods suffice for studying hypergraphs. … An obvious example is triadic measures like
> the graph clustering coefficient: these cannot be applied to bicolored graphs since (by definition)
> bicolored graphs have no triangles."
> ([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295))

So "use graph tools on the bipartite encoding" is not actually available for a large class of graph
tools. You need bipartite-specific or hypergraph-specific analogues either way — and at that point
the question is only which vocabulary you prefer.

The escape hatch — project the bipartite graph to one mode — is worse, not better. Battiston et al.:
"Each interaction becomes then a fully connected subgraph among the nodes belonging to the
interaction, losing the group structure in the same way as in the simple graph case. In addition, it
is usually impossible to translate the information contained in the standard graph operators (e.g.
Laplacian) defined on a bipartite graph into the ones corresponding to the unipartite projections."

### 3.3 Null models and statistics differ

Randomising a bipartite graph and randomising a hypergraph are not the same experiment. The bipartite
configuration model fixes the two degree sequences; hypergraph configuration models fix the node
degree sequence *and* the edge dimension (size) sequence — Chodrow's construction generalises "the
classical dyadic configuration model" to hypergraphs with an MCMC sampler
([Chodrow, 2019](https://arxiv.org/abs/1902.09302)).
Chodrow's abstract states the consequence directly, for two textbook statistics:

> "We start with two classical network topics -- triadic clustering and degree-assortativity. In each,
> we emphasize the importance of randomizing over hypergraph space rather than projected graph space,
> showing that this choice can dramatically alter statistical inference and study findings."
> ([Chodrow, 2019](https://arxiv.org/abs/1902.09302))

This is the one place where the bipartite/hypergraph choice provably changes an *answer* rather than
an ergonomic. Note the precise scope: the comparison is hypergraph space vs. **projected graph**
space, not hypergraph space vs. bipartite space. Whether a bipartite configuration model and a
hypergraph configuration model disagree in the same way is a narrower question, and I did not find a
published head-to-head comparison `[unverified]`. Still, the modelling choices differ — whether the
number of hyperedges is fixed or random, whether repeated hyperedges are allowed, whether a vertex
may appear twice in one hyperedge — and the bipartite encoding fixes several of them silently by
convention.

### 3.4 Type safety and modelling discipline (a real but non-mathematical benefit)

Battiston et al. put the ergonomic cost plainly:

> "at difference with other multilayer graph formulations, in a bipartite graph the nodes of the
> original system do not interact directly with each other anymore. Rather, their relation is always
> mediated by the interaction layer, which is of a different nature from the node layer itself. This
> implies that any measure or dynamic process define on the bipartite representation needs to take
> into account this additional complexity."
> ([Battiston et al., 2020](https://arxiv.org/abs/2006.01764))

In a knowledge base this is the difference between a schema in which "entity" and "fact" are distinct
kinds, and one in which both are nodes and the distinction lives in a `:Fact` label that nothing
enforces. Neo4j's own advice — replace the hyperedge with an "employment event" node
([Neo4j, Modeling designs](https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/)) —
produces a graph where a query that forgets to filter by label silently walks *through* facts as if
they were entities. That is a genuine class of bug, and it is a typing problem, not a graph-theory
problem.

Aksoy et al. state the preference honestly as a preference: "gearing our exposition towards
hypergraphs rather than bicolored graphs is more natural because our approach is set-theoretic."

### 3.5 Tooling now exists on the hypergraph side (weakest, and time-limited)

XGI, HyperNetX, HypergraphX, HAT and SimpleHypergraphs.jl now interoperate through the Hypergraph
Interchange Format, "a standard for higher-order network data to facilitate seamless data exchange
between higher-order network libraries" ([HIF-standard](https://github.com/pszufe/HIF-standard),
published in *Network Science*, 2025). This is a real argument today and a weak one in principle: it
says the ecosystem has caught up a little, not that the formalism is better. Against it stands the
fact that no hypergraph query language is standardised, while GQL became ISO/IEC 39075 on
12 April 2024 — for property graphs, explicitly without n-ary relationships
([Wikipedia, Graph Query Language](https://en.wikipedia.org/wiki/Graph_Query_Language), checked
2026-09-20).

## 4. What is *not* gained (arguments to stop making)

- **"Hypergraphs are more expressive."** Not in the information-theoretic sense. The bijection is
  exact. HyperGraphRAG's own Proposition 2 says so. What differs is which operations are primitive.
- **"You lose information by flattening to bipartite."** You do not. You lose information by
  flattening to a *2-section / clique expansion* — a different and genuinely lossy operation
  ("such hypergraph-to-graph reductions are inevitably lossy", [Aksoy et al., 2020](https://arxiv.org/abs/1906.11295)).
  Conflating the two is the single most common error in hypergraph advocacy, including in
  peer-reviewed papers. See [critical-reading-of-hypergraph-rag-claims.md](critical-reading-of-hypergraph-rag-claims.md) §4.
- **"Hypergraph neural networks beat GNNs because hypergraphs are richer."** Many hypergraph NNs are
  provably message-passing on the incidence bipartite graph. When they win, it is usually because of
  the aggregation scheme or the training regime, not because of the formalism. Treat any such claim
  as requiring a bipartite-GNN baseline. `[unverified]` — asserted here as an evaluation principle,
  not as a surveyed empirical result.

## 5. The honest summary

The dispute is not about expressivity; it is about **which structure is primitive in your
vocabulary**, and therefore about which questions you find easy to ask, which invariants your type
system enforces, and which null model you randomise against. Torres et al. reach the same conclusion
about formalism choice generally, and add a warning that applies verbatim here:

> "The fact that a method of interest might currently intake only one particular formalism does not
> justify the use of that formalism in representing our data. … Generally, a result is unlikely to
> offer fruitful insight into a system if the calculation was performed on a representation that
> itself is ill-suited for the system."
> ([Torres, Blevins, Bassett, Eliassi-Rad, 2021](http://www.eliassi.org/papers/torres-blevins-sirev-2021.pdf))

Read the other way round, that sentence also cuts against hypergraph enthusiasm: adopting a
hypergraph because hypergraph tools exist is the same error as adopting a graph because graph tools
exist.

**Practical rule.** Model in hypergraph vocabulary; store in whatever the database gives you,
usually bipartite; and never let the storage choice leak into the semantics. That is what
HyperGraphRAG does, and on this point it is right.

Related: [formalism-comparison-matrix.md](formalism-comparison-matrix.md) §4 (translation table),
[open-debates.md](open-debates.md) §4,
[../06-visualization/visual-encodings-catalogue.md](../06-visualization/visual-encodings-catalogue.md) §1.1
(the bipartite drawing as a visual encoding).

## Sources

- Aksoy, S., Joslyn, C., Ortiz Marrero, C., Praggastis, B., Purvine, E. "Hypernetwork science via high-order hypergraph walks." *EPJ Data Science* 9(1):16, 2020. https://arxiv.org/abs/1906.11295
- Battiston, F., Cencetti, G., Iacopini, I., Latora, V., Lucas, M., Patania, A., Young, J.-G., Petri, G. "Networks beyond pairwise interactions: structure and dynamics." *Physics Reports* 874:1–92, 2020. https://arxiv.org/abs/2006.01764
- Benson, A. R., Gleich, D. F., Higham, D. J. "Higher-order Network Analysis Takes Off, Fueled by Classical Ideas and New Data." arXiv:2103.05031, 8 March 2021 (based on an article in *SIAM News*). https://arxiv.org/abs/2103.05031
- Chodrow, P. S. "Configuration Models of Random Hypergraphs." arXiv:1902.09302, submitted 25 Feb 2019, revised 13 Dec 2019. https://arxiv.org/abs/1902.09302
- HIF-standard repository (Hypergraph Interchange Format). https://github.com/pszufe/HIF-standard (checked 2026-09-20)
- Luo, H., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025; arXiv:2503.21322. https://arxiv.org/abs/2503.21322
- Neo4j. "Modeling designs." Neo4j Getting Started documentation. https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/ (checked 2026-09-20)
- Torres, L., Blevins, A. S., Bassett, D. S., Eliassi-Rad, T. "The why, how, and when of representations for complex systems." *SIAM Review* 63(3):435–485, 2021. DOI 10.1137/20M1355896. Preprint: http://www.eliassi.org/papers/torres-blevins-sirev-2021.pdf
- Wikipedia. "Graph Query Language." https://en.wikipedia.org/wiki/Graph_Query_Language (checked 2026-09-20)
