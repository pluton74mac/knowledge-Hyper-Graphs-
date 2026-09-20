---
title: What is a knowledge hypergraph? Competing definitions in the literature
type: concept
status: draft
tags: [hypergraph, knowledge-hypergraph, n-ary, hyper-relational, definition, terminology]
created: 2026-09-19
updated: 2026-09-19
---

# What is a knowledge hypergraph?

**Short answer.** There is no single agreed definition. The phrase "knowledge hypergraph" (KHG)
and its neighbours ("hyper-relational knowledge graph", "n-ary knowledge graph", "hypergraph
knowledge base", "metagraph") are used by at least five research communities, and they do not
mean the same thing. All of them share one idea: *a fact may involve more than two things at once,
so the unit of knowledge is a hyperedge rather than a binary edge.* They differ on whether the
hyperedge is ordered, typed, decorated with qualifiers, nested, weighted, or described in natural
language.

This note collects the definitions verbatim where possible, then compares them in a table. The
practical consequences of the choice are worked out in
[hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md) and
[knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md).

## 0. The mathematical baseline

A hypergraph is a pair (X, E) where X is a set of vertices and E a set of subsets of X; a directed
hypergraph has edges that are pairs (D, C) of vertex subsets, a tail set and a head set
([Wikipedia, Hypergraph](https://en.wikipedia.org/wiki/Hypergraph)). In machine learning use the
hyperedges are often taken as *ordered* tuples: Kok and Domingos define a hypergraph as "a pair
(V, E) where V is a set of nodes, and E is a multiset of labeled non-empty ordered subsets of V
called hyperedges" and note that "A database can be viewed as a hypergraph with constants as
nodes, and true ground atoms as hyperedges. Each hyperedge is labeled with a predicate symbol"
([Kok and Domingos, 2009](https://icml.cc/Conferences/2009/papers/576.pdf)). That sentence is, in
effect, the earliest crisp statement of definition (a) below, though the paper does not use the term
"knowledge hypergraph". The mathematics is covered in `kb/01-foundations/`.

## 1. Definition (a): a KHG is a set of n-ary facts r(e1, ..., en)

The paper that popularised the term in the embedding community is *Knowledge Hypergraphs:
Prediction Beyond Binary Relations* ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137),
IJCAI 2020). Its definition:

> "A world consists of a finite set of entities E, a finite set of relations R, and a set of tuples τ
> where each tuple in τ is of the form r(e1, e2, . . . , ek) where r ∈ R is a relation and each ei ∈ E is
> an entity, for all i = 1, 2, . . . , k. The arity |r| of a relation r is the number of arguments that the
> relation takes and is fixed for each relation. A world specifies what is true: all the tuples in τ are
> true, and the tuples that are not in τ are false. A knowledge hypergraph consists of a subset of the
> tuples τ′ ⊆ τ."

Properties of this definition: hyperedges are **labeled** (by r), **ordered** (position i carries the
role), of **fixed arity per relation**, and the paper states that "knowledge hypergraphs are directed
and labeled" as opposed to the undirected hypergraphs of most hypergraph learning work
([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)). Truth is closed-world at the level of the
"world" τ, with the KHG an incomplete observed subset; see
[open-world-vs-closed-world-and-uncertainty.md](open-world-vs-closed-world-and-uncertainty.md).

The same structure, without the word "hypergraph", appears four years earlier in
[Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf) (IJCAI 2016, the m-TransH
paper). Wen et al. argue that the algebraic definition of an n-ary relation as a subset of N^J "is
incomplete, in the sense that the role of each coordinate in the cartesian product is not specified",
and define instead: "Let M be a set of roles in the KB, and a multi-fold relation, or simply, relation,
R on N with roles M is a subset of N^M", i.e. an instance is a *function from roles to entities*.
Their motivating statistic: "in Freebase, more than 1/3 of the entities participate in non-binary
relations" ([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)). This is
the source that later papers cite as "more than 30% of its entities are involved in such
hyper-relational facts" ([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf)).

A 2025 survey calls this the **hyperedge formalization**: "A hyperedge connects all entities in an
n-ary fact (Wen et al., 2016), e.g., (H, e1, ..., en) ... Each position in the hyperedge represents a
fixed role" ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)).

## 2. Definition (b): a hyper-relational KG is a set of triples with qualifiers

A second community starts from Wikidata's statement model rather than from relational algebra.
HINGE ([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf), WWW 2020)
describes "hyper-relational data (a.k.a. multi-fold or n-ary relational data), where each fact
contains multiple relations and entities", and gives the example of Marie Curie's education from
Wikidata: "it contains a base triplet: (h, r, t) {Marie Curie, educated at, University of Paris}, as well
as further information associated with the triplet, represented as key-value (relation-entity) pairs
(k, v) including {academic major, physics}, {academic degree, Master of Science}, etc."

StarE ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847), EMNLP 2020) formalises
hyper-relational facts as a main triple plus a set of qualifier pairs and, importantly, argues that
this is **not** the same thing as a knowledge hypergraph:

> "We deem hyper-relational graphs and hypergraphs are conceptually different. As hyperedges
> contain multiple nodes, such hyperedges are closer to n-ary relations r(e1, . . . , en) with one
> abstract relation. The attribution of entities to the main triple or qualifiers is lost, and qualifying
> relations are not defined. Combining a certain set of main and qualifying relations into one abstract
> rk() would lead to a combinatorial explosion of typed hyperedges since, in principle, any relation
> could be used in a qualifier, and there the amount of qualifiers per fact is not limited."
> ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847))

The 2025 survey names this the **hyper-relational formalization**: "An n-ary fact is formulated as
a primary triple coupled with a set of qualifier role-value pairs ... ((h, r, t), {ri : vi})" and adds
the caveat that "when there is no clear subject (i.e., head entity) or object (i.e., tail entity) in the
facts, it is not appropriate to use the hyper-relational formalization"
([Wei et al., 2025](https://arxiv.org/abs/2506.08970)).

A third, intermediate formalisation treats a fact as an **unordered set of role-value pairs** with no
distinguished triple (NaLP, [Guan et al., 2019](https://dblp.org/rec/conf/www/GuanJWC19.html);
RAM, [Liu et al., 2021](https://arxiv.org/abs/2104.09780)). The survey notes it "offers flexibility in
specifying the roles of entities" but "fails to account for the varying importance or prominence of
different entities within the same fact" ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)).

## 3. Definition (c): the KHG of the LLM / RAG literature

Since 2025 the term has been re-used by retrieval-augmented generation work, with a looser
structure. HyperGraphRAG ([Luo et al., 2025](https://arxiv.org/abs/2503.21322), NeurIPS 2025)
defines a knowledge hypergraph G_H = (V, E_H) whose hyperedges are n-ary relational facts
(n ≥ 2) extracted from text by an LLM. Each hyperedge carries "a natural language description
e_i^text, and a confidence score e_i^score ∈ (0,10]", and each entity carries "entity name, type,
explanation, and confidence score v_j^score ∈ (0,100]"; the hypergraph is stored as a bipartite
graph G_B with V_B = V ∪ E_H ([Luo et al., 2025](https://arxiv.org/html/2503.21322)). Hyper-RAG
([Feng et al., 2025](https://arxiv.org/abs/2504.08758)) similarly speaks of hypergraphs capturing
"both pairwise and beyond-pairwise correlations in domain-specific knowledge".

Key differences from (a) and (b): hyperedges are **untyped** (no relation symbol, only free text),
**unordered** (no positional roles), **weighted** by an LLM-assigned confidence, and there is
no schema. From the point of view of (a) this is a set-system with text labels; from the point of
view of (b) it has neither primary triple nor qualifiers.

## 4. Definition (d): hypergraph-structured knowledge in cognitive architectures

The OpenCog AtomSpace describes itself as "an in-RAM knowledge representation (KR) database
with an associated query engine and graph-re-writing system" and as "a kind of in-RAM
generalized hypergraph (metagraph) database" whose Atoms are "immutable, globally unique,
typed s-expressions" ([OpenCog AtomSpace README](https://github.com/opencog/atomspace),
checked 2026-09-19). The theoretical companion text gives the definitions:

> "Formally, a hypergraph is: A set of vertexes V ... A set of hyperedges E ... where each hyperedge
> ek is an ordered list of vertexes drawn from the set V. ... A metagraph is very nearly the same: A
> set of nodes V ... A set of links E ... where each hyperedge ek is an ordered list of nodes, or other
> links, or a mixture. They are arranged to be acyclic (to form a directed acyclic graph)."
> ([Vepštas, 2020–2023](https://github.com/opencog/atomspace/blob/master/opencog/sheaf/docs/ram-cpu.pdf))

So a metagraph is a hypergraph in which hyperedges may contain hyperedges: **nesting** is the
defining feature. HyperGraphDB, which implements "a generalized hypergraph model independently
proposed by Harold Boley and Ben Goertzel", makes the same move: "each atom has an associated
tuple of atoms called its target set. The size of the target set is called the atom's arity. Atoms of
arity 0 are called nodes and atoms of arity > 0 are called links", and "This generalization
automatically reifies every entity expressed in the database"
([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)). See
[metagraphs-atomspace-and-hypergraphdb.md](metagraphs-atomspace-and-hypergraphdb.md).

## 5. Definition (e): the semantic-network / conceptual-graph tradition

Before "knowledge graph" was a common phrase, hypergraphs were already proposed as a KR
language. Boley's 1977 paper introduces *directed recursive labelnode hypergraphs* (DRLHs) as "a
new representation-language combining 3 generalizations of directed labeled graphs"
([Boley, 1977](https://www.sciencedirect.com/science/article/abs/pii/0004370277900145),
*Artificial Intelligence* 9(1):49–85; abstract only consulted). Sowa's conceptual graphs (first
paper 1976, book 1984) are bipartite graphs of concept nodes and *n-adic* conceptual relation
nodes, e.g. "The between relation (Betw) is a triadic relation"
([Sowa, conceptual graph examples](https://www.jfsowa.com/cg/cgexampw.htm);
[Wikipedia, Conceptual graph](https://en.wikipedia.org/wiki/Conceptual_graph)). A bipartite graph
of relation nodes and argument nodes is exactly the incidence graph of a hypergraph, so a
conceptual graph *is* a knowledge hypergraph in sense (a) drawn differently; see
[semantic-web-hypergraph-view.md](semantic-web-hypergraph-view.md).

The RDF community also observed that RDF itself is a hypergraph: "RDF Graphs can be represented
naturally by hypergraphs, and hypergraphs can be represented naturally by bipartite graphs"
([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf)). There
each *triple* is a 3-uniform ordered hyperedge, so the hyperedges have fixed arity 3 and fixed roles
(subject, predicate, object). This is a different use of "hypergraph" again.

## 6. Comparison table

| Family | Canonical sources | A hyperedge is... | Ordered / roles | Typed by a relation symbol | Qualifiers on the edge | Nesting (edges over edges) | Weights / confidence | Schema |
|---|---|---|---|---|---|---|---|---|
| (a) n-ary fact KHG | [Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf); [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137) | a tuple r(e1..ek), or a role→entity function | yes, positional (Fatemi) or named roles (Wen) | yes, fixed arity per relation | no (would need a new relation) | no | no (closed-world truth) | implicit (relation arities) |
| (b) hyper-relational KG | [Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf); [Galkin et al., 2020](https://arxiv.org/abs/2009.10847); Wikidata | a primary triple (h,r,t) plus a set of (key,value) qualifiers | primary triple ordered; qualifiers unordered, keyed | yes (r), qualifiers keyed by properties | yes, open-ended | in Wikidata: references attach to statements | Wikidata ranks, no probabilities | Wikidata property constraints |
| (b') role-value set | [Guan et al., 2019](https://dblp.org/rec/conf/www/GuanJWC19.html); [Liu et al., 2021](https://arxiv.org/abs/2104.09780) | an unordered set {role: value} | named roles, no primary triple | relation implicit in the role set | roles and qualifiers indistinguishable | no | no | none |
| (c) LLM/RAG KHG | [Luo et al., 2025](https://arxiv.org/abs/2503.21322); [Feng et al., 2025](https://arxiv.org/abs/2504.08758) | a set of entities plus a natural-language description | unordered | no relation symbol; free text | no | no | yes, LLM-assigned scores | none |
| (d) metagraph / generalized hypergraph | [Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf); [OpenCog AtomSpace](https://github.com/opencog/atomspace); [Vepštas, 2020–2023](https://github.com/opencog/atomspace/blob/master/opencog/sheaf/docs/ram-cpu.pdf) | a typed Link whose ordered outgoing list may contain Nodes or other Links | ordered list | yes, Link/Atom types | via nested links and attached Values | yes, defining feature | yes (Values / truth values attached to atoms) | type system |
| (e) conceptual graphs, DRLH, RDF-as-hypergraph | [Boley, 1977](https://www.sciencedirect.com/science/article/abs/pii/0004370277900145); [Sowa](https://www.jfsowa.com/cg/cgexampw.htm); [Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf) | a relation node with n numbered arcs (CG); a triple as a 3-edge (RDF) | yes, numbered arcs / s-p-o | yes | via contexts (CG) or reification (RDF) | CG contexts, DRLH recursion | no (classical logic) | CG canon / RDFS |

## 7. A working definition for this KB (proposal, not established usage)

The KB needs one vocabulary. The following is a synthesis and should be read as this project's
convention, not as a claim about the literature:

> A **knowledge hypergraph** is a set of typed hyperedges over a set of entities. A hyperedge has a
> relation type, a binding of the relation's named roles to entities (or literals), and optionally a set
> of qualifier bindings, provenance, temporal validity and a confidence. Hyperedges may themselves
> fill roles of other hyperedges.

This is deliberately a superset: definition (a) is the case with no qualifiers and positional roles;
(b) is the case where one binary role pair (subject, object) is marked primary and the rest are
qualifiers; (c) is the case with a single untyped relation and free-text labels; (d) is the case with
nesting. The schema is worked out in
[knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md).

## 8. Where the definitions disagree in practice

- **Are qualifiers part of the fact or metadata about it?** In (a) everything in the tuple is the fact.
  In (b) the primary triple is the fact and qualifiers restrict it; HyperMono states the resulting
  property: "by attaching more qualifier pairs to a main triple, we may only narrow down the answer
  set, but never enlarge it" ([Hu et al., 2024](https://arxiv.org/abs/2404.09848)). Wikidata
  references, by contrast, are metadata about the statement, not part of its content.
- **Is the arity fixed?** Fixed per relation in (a); open-ended in (b) and (c).
- **Can a fact be about another fact?** No in (a)–(c) without reification; yes natively in (d), in
  TypeDB, and in RDF 1.2 triple terms (see
  [n-ary-relations-and-reification.md](n-ary-relations-and-reification.md)).
- **Does conversion to binary lose information?** Fatemi et al. argue yes: "star-to-clique conversion
  loses information", because a clique over {Air Canada, New York, Los Angeles} cannot say which
  tuples hold ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)). A 2025 study finds that
  after decomposition standard KG embedding models perform comparably to specialised
  hyper-relational models, while cautioning that decomposition "alter[s] the original HKG topology
  and fail[s] to fully preserve HKG information" ([Wang et al., 2025](https://arxiv.org/abs/2508.03280)).
  This is an active research question, not settled.

## Sources

- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020. https://arxiv.org/abs/1906.00137
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. *On the Representation and Embedding of Knowledge Bases Beyond Binary Relations.* IJCAI 2016. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
- Rosso, P., Yang, D., Cudré-Mauroux, P. *Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction.* The Web Conference (WWW) 2020. https://exascale.info/assets/pdf/rosso2020www.pdf (DOI 10.1145/3366423.3380257)
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020. https://arxiv.org/abs/2009.10847
- Guan, S., Jin, X., Wang, Y., Cheng, X. *Link Prediction on N-ary Relational Data.* WWW 2019. https://dblp.org/rec/conf/www/GuanJWC19.html
- Liu, Y., Yao, Q., Li, Y. *Role-Aware Modeling for N-ary Relational Knowledge Bases.* WWW 2021. https://arxiv.org/abs/2104.09780
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs.* arXiv, 2025. https://arxiv.org/abs/2506.08970
- Hu, Z., Gutiérrez-Basulto, V., Xiang, Z., Li, R., Pan, J. Z. *HyperMono: A Monotonicity-aware Approach to Hyper-Relational Knowledge Representation.* arXiv, 2024. https://arxiv.org/abs/2404.09848
- Wang, Y., Di, S., Wang, Z., Li, H., Teng, F., Xin, H., Chen, L. *Understanding the Embedding Models on Hyper-relational Knowledge Graph.* CIKM 2025. https://arxiv.org/abs/2508.03280
- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., Feng, Y., Kuang, Z., Song, M., Zhu, Y., Luu, A. T. *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation.* NeurIPS 2025. https://arxiv.org/abs/2503.21322
- Feng, Y., Hu, H., Hou, X., Liu, S., Ying, S., Du, S., Hu, H., Gao, Y. *Hyper-RAG: Combating LLM Hallucinations using Hypergraph-Driven Retrieval-Augmented Generation.* arXiv, 2025. https://arxiv.org/abs/2504.08758
- OpenCog Foundation. *AtomSpace README.* GitHub, checked 2026-09-19. https://github.com/opencog/atomspace
- Vepštas, L. *Graphs, Metagraphs, RAM, CPU.* OpenCog technical text, versions 2020–2023. https://github.com/opencog/atomspace/blob/master/opencog/sheaf/docs/ram-cpu.pdf
- Iordanov, B. *HyperGraphDB: A Generalized Graph Database.* WAIM 2010 workshops, Springer LNCS. https://hypergraphdb.org/docs/hypergraphdb.pdf
- Boley, H. *Directed recursive labelnode hypergraphs: A new representation-language.* Artificial Intelligence 9(1):49–85, 1977. https://www.sciencedirect.com/science/article/abs/pii/0004370277900145
- Sowa, J. F. *Conceptual Graphs Examples.* jfsowa.com (1999 copyright notice). https://www.jfsowa.com/cg/cgexampw.htm
- Wikipedia. *Conceptual graph.* https://en.wikipedia.org/wiki/Conceptual_graph
- Hayes, J., Gutierrez, C. *Bipartite Graphs as Intermediate Model for RDF.* ISWC 2004, LNCS 3298. https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf
- Kok, S., Domingos, P. *Learning Markov Logic Network Structure via Hypergraph Lifting.* ICML 2009. https://icml.cc/Conferences/2009/papers/576.pdf
- Wikipedia. *Hypergraph.* https://en.wikipedia.org/wiki/Hypergraph
