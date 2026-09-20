---
title: Glossary of confusable terms — hypergraph, hypernetwork, hyper-relational, higher-order, multiplex, metagraph, ubergraph
type: glossary
status: draft
tags: [glossary, terminology, disambiguation, hypernetwork, hyper-relational, higher-order, multiplex, multilayer, heterogeneous, metagraph, hypernode-graph, ubergraph]
created: 2026-09-20
updated: 2026-09-20
---

# Glossary of confusable terms

Eleven terms that get used interchangeably and mean different things, plus six adjacent terms that
are routinely misapplied. Each entry gives: the definition, who uses it, what it is **not**, and the
mistake it is usually confused with.

This is the disambiguation companion to
[../02-knowledge-representation/what-is-a-knowledge-hypergraph.md](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md),
which catalogues the competing definitions of "knowledge hypergraph" itself.

**A quick triage question for any paper you read:** *what is the atomic object, and is it ordered,
typed, and closed downward?* Four bits of information separate almost all of the terms below.

---

## 1. Hypergraph

**Definition.** A pair `H = (V, E)` where `E` is a family of non-empty subsets of `V`. Each hyperedge
may contain any number of vertices. A graph is the 2-uniform case.

**Who uses it.** Everyone, in at least three incompatible refinements:

| Refinement | Hyperedge is | Used by |
|---|---|---|
| Plain (Berge) | an unordered, unlabelled subset | higher-order network science; XGI, HyperNetX |
| Ordered and labelled | a multiset of "labeled non-empty ordered subsets of V" ([Kok and Domingos, 2009](https://icml.cc/Conferences/2009/papers/576.pdf)) | ML on relational data; knowledge hypergraphs |
| Directed | a pair (tail set, head set) | flow, reaction networks, directed hypergraph algorithms |

**Not.** A hypergraph is not the same object as its 2-section/clique expansion (which is lossy), nor
the same *typed* object as its incidence bipartite graph (which is a lossless re-encoding but loses
the vertex/edge distinction unless the bicoloring is kept — see §14).

**Confusion to avoid.** "Hypergraph" in the network-science sense carries no relation symbol and no
roles. Almost no result from that literature applies unmodified to a role-labelled knowledge
hyperedge.

## 2. Hypernetwork — four different things

This is the worst term in the field. It means at least four unrelated things.

1. **Johnson's hypernetworks** (social/complex systems). Built on *relational simplices*: an ordered
   set of vertices together with an explicit relation symbol, so that structure and relation are
   carried together, and organised into multilevel systems
   ([Johnson, 2009](https://link.springer.com/chapter/10.1007/978-3-642-02466-5_35); the book
   *Hypernetworks in the Science of Complex Systems*, Imperial College Press). The key difference
   from a plain hypergraph: Johnson insists the relation is part of the object, not a label on it,
   and that *order matters* — ⟨a,b,c;R⟩ and ⟨b,a,c;R⟩ are distinct. `[unverified — only
   abstract-level metadata and secondary descriptions were consulted for Johnson's formal
   definitions in this research run.]`
2. **"Hypernetwork" as a synonym for hypergraph-structured data.** PNNL's usage: "hypernetworks" are
   real-world systems with hypergraph structure, by analogy with "network" being a graph that
   represents a system ([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295), which coins
   "hypernetwork science").
3. **Directed-hypergraph hypernetworks.** In F-hypergraph theory an (s,d)-hypernetwork is a
   minimal sub-hypergraph connecting s to d; finding one is NP-hard
   ([Gil Pons, Ward, Miller, 2022](https://arxiv.org/abs/2201.04799)).
4. **Hypernetworks in deep learning.** A neural network that generates the weights of another neural
   network. Completely unrelated to hypergraphs. `[unverified — no primary source consulted here;
   flagged because the collision is common in search results.]`

**Rule.** Never use "hypernetwork" without saying which sense. Prefer "hypergraph-structured data"
for sense 2.

## 3. Hyper-relational

**Definition.** A fact consisting of a **primary triple** `(h, r, t)` plus a set of **qualifier**
key–value pairs. Wikidata's statement model is the canonical instance; HINGE and StarE are the
canonical models ([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf);
[Galkin et al., 2020](https://arxiv.org/abs/2009.10847)).

**Not** a hypergraph. The StarE authors are explicit: "We deem hyper-relational graphs and
hypergraphs are conceptually different. … The attribution of entities to the main triple or
qualifiers is lost, and qualifying relations are not defined"
([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)).

**Confusion to avoid.** Papers that say "hyper-relational (a.k.a. n-ary)" are eliding a real
distinction that changes what is expressible and what a model learns. See
[open-debates.md](open-debates.md) §2 and
[../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).

## 4. N-ary / arity / multi-fold

**Definition.** *Arity* is the number of arguments a relation takes. An *n-ary* fact has n > 2
participants. "Multi-fold relation" is Wen et al.'s term for the same thing with named roles: "a
multi-fold relation … on N with roles M is a subset of N^M"
([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)).

**Two sub-conventions that are *not* interchangeable:**
- **Positional**: `r(e₁,…,e_k)`, role = position, arity "fixed for each relation"
  ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)).
- **Role-named**: a function from named roles to entities. Wen et al. introduced this precisely
  because they judged the positional definition "incomplete, in the sense that the role of each
  coordinate in the cartesian product is not specified".

**Confusion to avoid.** "Arity" in the hyper-relational literature sometimes counts the primary
triple's two entities plus qualifier values, and sometimes counts only entities. Check the paper's
convention before comparing arity distributions across datasets.

## 5. Higher-order — three different things

1. **Higher-order network / higher-order interaction** (network science): a relation among three or
   more units, encoded as a simplex or hyperedge ([Battiston et al., 2020](https://arxiv.org/abs/2006.01764)).
2. **Higher-order Markov chain / higher-order model of pathways**: *memory* over sequences, nothing
   to do with group size. Benson, Gleich and Higham describe researchers reaching "for new types of
   higher-order stochastic processes with more memory, namely higher-order and variable-order Markov
   chains" ([Benson, Gleich, Higham, 2021](https://arxiv.org/abs/2103.05031)).
3. **Higher-order tensor**: an array of order ≥ 3.

**Confusion to avoid.** A paper titled "higher-order X" may be about group interactions, about
sequence memory, or about tensor order. These are three literatures.

**Also note the off-by-one.** In simplicial language a *k*-simplex has *k+1* vertices, so a
"2-interaction" is a triangle among three nodes. Battiston et al. warn about this explicitly when
discussing cliques ("we use size for cliques to avoid confusion, since a k-clique usually encodes an
interaction of order k−1").

## 6. Multi-relational

**Definition.** A graph with several *types* of binary edge — the standard knowledge-graph setting.
`(subject, predicate, object)` with many predicates is multi-relational.

**Not** n-ary. Multi-relational is about the *number of relation types*; n-ary is about the *number
of arguments per fact*. A KG with 10,000 predicates and only triples is maximally multi-relational
and entirely binary.

**Confusion to avoid.** Tensor factorisation papers (RESCAL and descendants) say "multi-relational"
and model an order-3 tensor `entity × entity × relation`
([Nickel, Tresp, Kriegel, 2011](https://icml.cc/Conferences/2011/papers/438_icmlpaper.pdf)). That is
binary facts, stacked — not n-ary facts.

## 7. Multilayer network

**Definition.** A network whose nodes and/or edges are distributed over several layers, with
intra-layer and inter-layer edges. The umbrella term; Kivelä et al. provide "a dictionary of
terminology to relate the numerous existing concepts to each other" — multiplex networks,
interdependent networks, networks of networks and others
([Kivelä, Arenas, Barthelemy, Gleeson, Moreno, Porter, 2014](https://arxiv.org/abs/1309.7233),
*Journal of Complex Networks* 2(3):203–271).

**Not** a hypergraph. Layers are about *contexts or edge types*, not about group size. A multilayer
network with 50 layers still has binary edges within each layer.

## 8. Multiplex network

**Definition.** The special case of a multilayer network in which every layer has the *same* node
set and inter-layer edges connect only a node to its own copies. "Multiplex" ≈ "the same actors,
several kinds of tie".

**Confusion to avoid.** Multiplex ≠ multi-relational ≠ n-ary. Multiplex is a multilayer structure;
multi-relational is an edge-labelling; n-ary is an arity. All three are orthogonal.

## 9. Heterogeneous (information) graph

**Definition.** A graph with typed nodes *and* typed edges, where the type schema matters (e.g.
author–paper–venue). Standard in GNN work (metapath-based models, R-GCN, HGT).

**Not** a hypergraph, and not the same as multi-relational: heterogeneity includes *node* types.

**Confusion to avoid.** A heterogeneous graph with a "fact" node type is an incidence encoding of a
hypergraph. Many heterogeneous-GNN papers are, structurally, hypergraph papers that do not say so —
and vice versa. Compare against a heterogeneous-GNN baseline before attributing a win to
"hypergraph structure". See [hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md) §4.

## 10. Metagraph — two different things

1. **Generalised hypergraph with nesting** (the sense used in this KB). A hypergraph in which a
   hyperedge may contain other hyperedges. HypergraphDB: "each atom has an associated tuple of atoms
   called its target set. … Atoms of arity 0 are called nodes and atoms of arity > 0 are called
   links", and "This generalization automatically reifies every entity expressed in the database"
   ([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)). OpenCog's AtomSpace calls
   itself "a kind of in-RAM generalized hypergraph (metagraph) database"
   ([OpenCog AtomSpace](https://github.com/opencog/atomspace)). **Nesting is the defining feature.**
2. **Metapath template** (heterogeneous-graph mining). A small schema-level pattern such as
   author→paper→venue used to define similarity. Confusingly also called a metagraph or
   meta-structure in some papers. `[unverified — no primary source consulted; flagged as a naming
   collision.]`

**Confusion to avoid.** Sense 1 is about the data; sense 2 is about queries over the schema.

See [../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md](../02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md).

## 11. Hypernode graph

**Definition.** A structure in which the *endpoints* of an edge are sets of nodes rather than single
nodes — i.e. a "binary relation over sets", with signed weights supporting a spectral (Laplacian)
theory. Introduced for spectral learning by Ricatte, Gilleron and Tommasi, ECML PKDD 2014
`[unverified — I could not retrieve a primary source for this citation during this research run;
title, authors and venue are reported as commonly cited and should be checked before reuse.]`

**Not** a hypergraph: a hyperedge is one set; a hypernode edge is a *pair* of sets with weights.
Closer to a weighted directed hypergraph than to an undirected one.

**Confusion to avoid.** "Hypernode" also appears in unrelated senses (a node that contains a
subgraph, in some visualisation and modelling tools).

## 12. Ubergraph

**Definition.** A recursive hypergraph structure in which an edge may contain vertices *or other
edges*, with a notion of depth. "Partly in service of exploring the formal basis for Georgetown
University's AvesTerra database structure, we formalize a recursive hypergraph data structure, which
we call an ubergraph" ([Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547), submitted
18 April 2017). A depth-k ubergraph is a pair (V, E) where V is a set of fundamental vertices and E
a finite set of uberedges; anything in an edge that is not in V must itself be an edge.

**Attribution note.** This paper is often mis-cited as "Joslyn and Aksoy". The authors are **Cliff
Joslyn and Kathleen Nowak** (Sinan Aksoy is a co-author on the *later* PNNL hypergraph-walks work).

**Relation to other terms.** An ubergraph is essentially a metagraph (sense 1) given a careful
combinatorial definition; both are nested hypergraphs. The AtomSpace metagraph is additionally
required to be acyclic.

---

## 13. Adjacent terms that are routinely misapplied

**Simplicial complex.** A family of subsets closed downward: if σ is in the complex, so is every
subset of σ. This *derivation* is the point — and it is almost always wrong for knowledge, because
`married(Alice, Bob, 2011)` does not entail `married(Alice, Bob)` as an independently asserted fact
with the same meaning. Hypergraphs impose no such closure
([Battiston et al., 2020](https://arxiv.org/abs/2006.01764)).

**Cell complex / combinatorial complex.** Combinatorial complexes were designed to have it both
ways: they "generalize and combine useful traits of both hypergraphs and cell complexes", imposing
"no constraints on the set of relations" while permitting "hierarchical higher-order relations"
([Hajij et al., 2022](https://arxiv.org/abs/2206.00606)). The added structure over a hypergraph is a
*rank* function, not downward closure.

**Factor graph.** A bipartite graph representing the factorisation of a function, with variable
nodes and factor nodes ([Kschischang, Frey, Loeliger, 2001](https://en.wikipedia.org/wiki/Factor_graph)).
Structurally identical to a hypergraph incidence graph; semantically it denotes a *product of
functions*, not a set of asserted facts. Use "factor graph" only when the sum–product semantics is
intended.

**Incidence graph / Levi graph / König graph / bipartite representation.** Four names for the same
construction: one node per vertex, one node per hyperedge, an edge for each membership. Lossless.

**2-section / clique expansion / one-mode projection / line graph.** The *lossy* reduction: connect
every pair of vertices that share a hyperedge. "Such hypergraph-to-graph reductions are inevitably
lossy" ([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295)). Do not confuse with the incidence
graph.

**Bicolored graph.** A bipartite graph *with a fixed choice of which side is which*. Hypergraphs are
in bijection with bicolored graphs, not with bipartite graphs: "a bipartite graph with k connected
components has 2^k possible bicolorings, each of which may correspond to a distinct hypergraph"
([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295)). See
[hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md) §2.

**Reification.** Making a statement into an addressable object. In RDF 1.1 it is the four-triple
`rdf:Statement` vocabulary; in RDF 1.2 it is `rdf:reifies` with a triple term; in a property graph it
is an intermediate node; in the W3C n-ary note it is a "relation instance". These have different
semantics — RDF reification is deliberately non-committal: "A reification of a triple does not entail
the triple, and is not entailed by it" ([RDF 1.1 Semantics](https://www.w3.org/TR/rdf11-mt/), as
quoted in [../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md)).

**Superhypergraph / n-superhypergraph.** Appears in a body of recent preprint literature extending
hypergraphs recursively over power sets. Not established in the mainstream higher-order network or
KR literature and not used in this KB. `[unverified — flagged so readers recognise the term, not
endorsed.]`

---

## 14. Disambiguation table

| Term | Atomic object | Ordered? | Typed/labelled? | Downward-closed? | Nesting? |
|---|---|---|---|---|---|
| Hypergraph (plain) | subset of V | no | no | no | no |
| Hypergraph (Kok–Domingos / KHG) | labelled ordered subset | yes | yes | no | no |
| Directed hypergraph | (tail set, head set) | by role | often | no | no |
| Simplicial complex | simplex | no | no | **yes** | no |
| Combinatorial complex | ranked cell | no | by rank | no (hierarchy instead) | no |
| Hyper-relational fact | triple + qualifier pairs | triple yes, qualifiers keyed | yes | n/a | via nesting in RDF 1.2 |
| Multi-relational graph | typed binary edge | yes | yes | n/a | no |
| Multilayer / multiplex | binary edge in a layer | yes | by layer | n/a | no |
| Heterogeneous graph | typed binary edge between typed nodes | yes | yes | n/a | no |
| Metagraph / ubergraph | edge over vertices *or edges* | yes | yes | no | **yes** |
| Hypernode graph | pair of node sets | — | weighted | no | no |
| Factor graph | factor node + variable nodes | no | function-valued | n/a | no |
| Johnson hypernetwork | relational simplex ⟨v₁…v_n; R⟩ | **yes** | **yes** | no | multilevel |

## Sources

- Aksoy, S., Joslyn, C., Ortiz Marrero, C., Praggastis, B., Purvine, E. "Hypernetwork science via high-order hypergraph walks." *EPJ Data Science* 9(1):16, 2020. https://arxiv.org/abs/1906.11295
- Battiston, F., Cencetti, G., Iacopini, I., Latora, V., Lucas, M., Patania, A., Young, J.-G., Petri, G. "Networks beyond pairwise interactions: structure and dynamics." *Physics Reports* 874:1–92, 2020. https://arxiv.org/abs/2006.01764
- Benson, A. R., Gleich, D. F., Higham, D. J. "Higher-order Network Analysis Takes Off, Fueled by Classical Ideas and New Data." arXiv:2103.05031, 2021. https://arxiv.org/abs/2103.05031
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs." EMNLP 2020. https://arxiv.org/abs/2009.10847
- Gil Pons, R., Ward, M., Miller, L. "Finding (s,d)-Hypernetworks in F-Hypergraphs is NP-Hard." arXiv:2201.04799, 2022. https://arxiv.org/abs/2201.04799
- Hajij, M., et al. "Topological Deep Learning: Going Beyond Graph Data." arXiv:2206.00606, 2022. https://arxiv.org/abs/2206.00606
- Iordanov, B. "HyperGraphDB: A Generalized Graph Database." 2010. https://hypergraphdb.org/docs/hypergraphdb.pdf
- Johnson, J. "Hypernetworks of Complex Systems." In *Complex Sciences*, Springer LNICST, 2009. https://link.springer.com/chapter/10.1007/978-3-642-02466-5_35
- Joslyn, C., Nowak, K. "Ubergraphs: A Definition of a Recursive Hypergraph Structure." arXiv:1704.05547, 18 April 2017. https://arxiv.org/abs/1704.05547
- Kivelä, M., Arenas, A., Barthelemy, M., Gleeson, J. P., Moreno, Y., Porter, M. A. "Multilayer Networks." *Journal of Complex Networks* 2(3):203–271, 2014; arXiv:1309.7233. https://arxiv.org/abs/1309.7233
- Kok, S., Domingos, P. "Learning Markov Logic Network Structure via Hypergraph Lifting." ICML 2009. https://icml.cc/Conferences/2009/papers/576.pdf
- Kschischang, F. R., Frey, B. J., Loeliger, H.-A. "Factor Graphs and the Sum-Product Algorithm." *IEEE Transactions on Information Theory* 47(2):498–519, 2001. Summarised via https://en.wikipedia.org/wiki/Factor_graph (checked 2026-09-20)
- Nickel, M., Tresp, V., Kriegel, H.-P. "A Three-Way Model for Collective Learning on Multi-Relational Data." ICML 2011. https://icml.cc/Conferences/2011/papers/438_icmlpaper.pdf
- OpenCog AtomSpace repository. https://github.com/opencog/atomspace
- Rosso, P., Yang, D., Cudré-Mauroux, P. "Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction." WWW 2020. https://exascale.info/assets/pdf/rosso2020www.pdf
- W3C. "RDF 1.1 Semantics." W3C Recommendation, 2014. https://www.w3.org/TR/rdf11-mt/
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases beyond Binary Relations." IJCAI 2016. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
