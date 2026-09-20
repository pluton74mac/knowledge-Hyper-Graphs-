---
title: Directed and typed hyperedges for knowledge — rules, events, contexts
type: concept
status: draft
tags: [directed-hypergraph, b-hypergraph, horn-clause, rules, hyperpath, events, provenance, named-graphs, gallo]
created: 2026-09-20
updated: 2026-09-20
---

# Directed and typed hyperedges for knowledge

"Directed hypergraph" means at least three different things in the knowledge literature, and the
senses are not compatible. Sorting them out is the first job of this note; the second is to show
what the *genuinely* directed sense (tail set → head set) is good for in a knowledge base — rules
and derivations — and the third is to cover two other uses of a typed hyperedge that are not facts
about entities at all: events and contexts.

## 1. Three senses of "directed"

| Sense | Definition | Typical source | What the edge means |
|---|---|---|---|
| **(D1) ordered arguments** | the hyperedge is a tuple, not a set; position i is role i | "knowledge hypergraphs are directed and labeled" ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)); "a multiset of labeled non-empty ordered subsets" ([Kok and Domingos, 2009](https://icml.cc/Conferences/2009/papers/576.pdf)) | one n-ary fact |
| **(D2) tail → head** | the hyperedge is a pair of disjoint vertex sets `(Tail(a), Head(a))` | [Gallo, Longo, Pallottino and Nguyen, 1993](https://doi.org/10.1016/0166-218X(93)90045-P); [Nguyen, Pretolani and Markenzon, 1998](https://www.numdam.org/item/ITA_1998__32_1-3_1_0.pdf) | an implication, a reaction, a transition |
| **(D3) role-labelled incidences** | each membership carries a role name; no global order | NaLP/RAM role-value pairs ([Liu et al., 2021](https://arxiv.org/abs/2104.09780)); HIF `"direction": "head"｜"tail"` on incidences ([HIF standard](https://github.com/HIF-org/HIF-standard)) | one n-ary fact, with named slots |

A knowledge hypergraph in the sense of
[what-is-a-knowledge-hypergraph.md](what-is-a-knowledge-hypergraph.md) is (D1) or (D3). The rest of
this note is mostly about (D2), because it is the sense that carries *inference* rather than
*assertion*, and because the two are often stored in the same file without a type marker.

## 2. (D2): the Gallo model

The founding reference is Gallo, Longo, Pallottino and Nguyen, *Directed Hypergraphs and
Applications*, Discrete Applied Mathematics 42(2–3):177–201, 1993. Its abstract:

> "This paper deals with directed hypergraphs as a tool to model and solve some calsses [sic] of
> problems arising in Operations Research and in Computer Science. Concepts such as connectivity,
> paths and cuts are defined. An extension of the amin [sic] duality results to a special class of
> hypergraphs is presented. Algorithms to perform visits of hypergraphs and to find optimal paths
> are studied in detail. Some applications arising in propositional logic, An-Or graphs, relational
> data bases and transportation analysis are presented."
> ([Gallo et al., 1993](https://doi.org/10.1016/0166-218X(93)90045-P), abstract as indexed)

Note the four applications named in that last sentence: **propositional logic, AND/OR graphs,
relational databases, transportation**. Three of the four are knowledge-representation problems.

The definitions, quoted from a contemporaneous paper that cites Gallo et al. for them:

> "A directed hypergraph is a pair H = (V, E) where V is the set of nodes, and E is the set of
> hyperarcs. A hyperarc a ∈ E is a pair (Tail(a), Head(a)), where Tail(a) and Head(a) are disjoint
> subsets of V. A hyperarc a is a B-arc (respectively an F-arc) if |Head(a)| ≤ 1 (respectively if
> |Tail(a)| ≤ 1). A B-graph (respectively an F-graph) is a hypergraph whose hyperarcs are B-arcs
> (respectively F-arcs). A BF-graph admits both B-arcs and F-arcs."
> ([Nguyen, Pretolani and Markenzon, 1998](https://www.numdam.org/item/ITA_1998__32_1-3_1_0.pdf),
> RAIRO — Theoretical Informatics and Applications 32(1-3):1–20)

Reachability is not ordinary reachability: a node is B-connected to `u₀` if it is `u₀`, or if some
hyperarc has it in the head and **every** node of that hyperarc's tail is B-connected to `u₀`. That
"every" is the conjunction in a rule body. The survey of algorithms on these structures is
[Ausiello and Laura, 2017](https://doi.org/10.1016/j.tcs.2016.03.016), *Theoretical Computer
Science* 658:293–306.

## 3. B-arcs are Horn clauses

The correspondence is stated exactly by Klein and Manning, who use it to unify parsing with
deduction:

> "There is also a deep connection between logic, in particular propositional satisfiability, and
> directed hypergraphs (Gallo et al. 1993)."

> "Directed hypergraphs are much like standard directed graphs. However, while standard arcs connect
> a single tail node to a single head node, hyperarcs connect a set of tail nodes to a set of head
> nodes. Often, as in the present work, multiplicity is needed only in the tail. When the head
> contains exactly one node, we call the hyperarc a B-arc."

> "It is easy to see the construction which provides the link to satisfiability. Nodes correspond to
> propositions, and directed hyperarcs ({t₁, ..., t_m}, {h₁, ..., h_n}) correspond to rules
> t₁ ∧ ... ∧ t_m → h₁ ∨ ... ∨ h_n. In the case of B-arcs, the corresponding rules are Horn clauses.
> The construction also requires two special nodes, true and false. For the Horn clause case, it
> turns out that satisfiability is equivalent to the non-existence of a certain kind of path from
> true to false."
> ([Klein and Manning, 2001](https://aclanthology.org/W01-1812/), IWPT 2001)

So, precisely:

| Logic | Directed hypergraph |
|---|---|
| proposition | node |
| Horn clause `b₁ ∧ … ∧ b_m → h` | B-arc with tail `{b₁,…,b_m}`, head `{h}` |
| general clause `b₁ ∧ … → h₁ ∨ …` | hyperarc with a multi-node head |
| fact (unit clause) | B-arc with empty tail, or an arc from `true` |
| forward chaining | B-visit / B-connection computation |
| a proof | a B-hyperpath |
| Horn satisfiability | non-existence of a B-path from `true` to `false` |

Three consequences worth stating:

1. **Rules and facts can live in one structure.** A knowledge hypergraph of facts (D1/D3) plus a
   B-graph of rules (D2) is one hypergraph with two edge types. TypeDB's rules, SPARQL CONSTRUCT and
   SHACL 1.2 Rules ([SHACL 1.2 Rules](https://www.w3.org/TR/shacl12-rules/)) all sit at this
   boundary.
2. **Inference is a path problem.** Once rules are B-arcs, "why is P derivable?" is answered by a
   hyperpath, which is also a *proof object* and therefore a natural provenance record. Shortest
   B-hyperpath algorithms give minimum-cost derivations.
3. **Weights come for free.** Klein and Manning's whole point is that "scored arcs are a central and
   well-studied concept of graph theory", so a weighted B-graph is a probabilistic derivation
   system. PSL rules — "a set of first-order logic rules with conjunctive bodies and single literal
   heads" ([Chen et al., 2019](https://arxiv.org/abs/1811.10667), describing PSL) — are literally
   weighted B-arcs over soft-truth atoms; see
   [open-world-vs-closed-world-and-uncertainty.md](open-world-vs-closed-world-and-uncertainty.md).

**AND/OR graphs** are the same structure under an older name, listed among Gallo et al.'s
applications: an AND-node with k children is a B-arc with a k-element tail. The parsing case that
Klein and Manning develop — "There is intuitively very little difference between (a) combining
subtrees to form a tree, (b) combining hypotheses to form a conclusion, and (c) visiting all tail
nodes of a hyperarc before traversing to a head node"
([Klein and Manning, 2001](https://aclanthology.org/W01-1812/)) — is worth keeping in mind whenever a
KHG is used for multi-hop reasoning: a multi-hop answer is a hyperpath, not a path.

## 4. Hyperedges as events

An event is an n-ary fact with a distinguished temporal identity. The two usable modelling routes:

- **Reify it** (the mainstream choice). The event-KG survey's formal definition makes events *nodes*
  and argument roles *edges*: "EKG G = {(s, p, o) | {s, o} ∈ N, p ∈ E, N = N_evt ∪ N_ent, ...} is a
  graph of events N_evt, entities N_ent, and their relations E"
  ([Guan et al., 2021/2022](https://arxiv.org/abs/2112.15280)). NewsReader's event-centric KGs do the
  same on top of the Simple Event Model, which "provides a generic framework to represent who did
  what when and where", supplemented by FrameNet because "SEM does not distinguish what exact role
  each participant plays" ([Rospocher et al., 2016](https://doi.org/10.1016/j.websem.2015.12.004)).
- **Make it a hyperedge with an id.** Then argument roles are incidence labels (D3), and event-event
  relations (temporal, causal, subevent) are edges *between hyperedges* — which requires nesting, as
  in [metagraphs-atomspace-and-hypergraphdb.md](metagraphs-atomspace-and-hypergraphdb.md).

Where (D2) re-enters: **causal** and **enabling** relations between events are naturally directed
hyperarcs, because a cause is usually a conjunction of conditions, not a single event. The event-KG
literature records "temporal, causal, conditional and hypernym-hyponym relations between events"
([Guan et al., 2021](https://arxiv.org/abs/2112.15280)) but represents them as binary edges between
event nodes — a conjunctive cause therefore has to be reified a second time. A directed hyperarc
whose tail is the set of contributing events expresses it in one edge. No benchmark uses this
encoding `[unverified]`.

## 5. Hyperedges as context and provenance

A hyperedge over *statements* rather than entities is a context. The semantic web already has the
construct: named graphs, proposed for "provenance and trust"
([Carroll et al., 2005](https://dl.acm.org/doi/10.1145/1060745.1060835)) and standardised as RDF
datasets, where "Each named graph is a pair consisting of an IRI or a blank node (the graph name),
and an RDF graph" ([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)). A named graph *is* a
labelled hyperedge whose members are triples.

Nanopublications push this to one fact per context: each nanopublication is an assertion graph plus
a provenance graph plus a publication-info graph
([Groth, Gibson and Velterop, 2010](https://dl.acm.org/doi/10.5555/1883685.1883690)). HypergraphDB
treats scoping and reification as the same problem, dissolved by the same generalisation: "Two other
prominent issues are contextuality (scoping) and reification ... Those and other considerations from
semantic web research disappear or find natural solutions in the model implemented by HyperGraphDB"
([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)).

**Modelling rule.** Distinguish:

- a hyperedge whose members are **entities** — an n-ary fact;
- a hyperedge whose members are **hyperedges** — a context, a provenance record, a belief state, or
  a rule instance;
- a hyperarc whose **tail** is a set and whose **head** is a set — an inference step.

A store that does not type its edges will eventually mix all three, and then neither reasoning nor
querying is well-defined.

## 6. Serialisation note

HIF already carries a direction bit: an incidence record may have `"direction"` set to `"head"` or
`"tail"`, and the format "supports multiple types of higher-order networks, including undirected
hypergraphs, directed hypergraphs, and abstract simplicial complexes"
([Coll et al., 2025](https://doi.org/10.1017/nws.2025.10018);
[HIF standard](https://github.com/HIF-org/HIF-standard), checked 2026-09-20). That gives (D2) a
portable encoding, but HIF has no place for a *role* name on the incidence except free-form
`attrs` — so (D3) still needs a KHG-specific schema
([knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md)).

## 7. Open points

- No standard vocabulary distinguishes (D1), (D2) and (D3) in a serialised file. This KB's schema
  proposal marks edge kind explicitly; nothing else consulted does `[unverified]`.
- The mathematics of directed hypergraphs is mature
  ([Gallo et al., 1993](https://doi.org/10.1016/0166-218X(93)90045-P);
  [Ausiello and Laura, 2017](https://doi.org/10.1016/j.tcs.2016.03.016)) but is almost absent from
  the KHG embedding literature, which works with (D1). Hyperpath-based explanation for n-ary link
  prediction looks like an open opportunity.
- Ubergraphs are defined only for the undirected case: "here we deal only with undirected hyper- and
  ubergraphs. Direction and/or orientation could prove very valuable, but await further
  consideration" ([Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547)). A directed,
  role-labelled, nested formalism is not, as far as this run found, defined anywhere
  `[unverified]`.

## Sources

- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. *Directed Hypergraphs and Applications.* Discrete Applied Mathematics 42(2–3):177–201, 1993. DOI 10.1016/0166-218X(93)90045-P. https://doi.org/10.1016/0166-218X(93)90045-P
- Nguyen, S., Pretolani, D., Markenzon, L. *On some path problems on oriented hypergraphs.* RAIRO — Informatique théorique et applications 32(1-3):1–20, 1998. https://www.numdam.org/item/ITA_1998__32_1-3_1_0.pdf
- Ausiello, G., Laura, L. *Directed hypergraphs: Introduction and fundamental algorithms — A survey.* Theoretical Computer Science 658:293–306, 2017. DOI 10.1016/j.tcs.2016.03.016. https://doi.org/10.1016/j.tcs.2016.03.016
- Klein, D., Manning, C. D. *Parsing and Hypergraphs.* Proc. Seventh International Workshop on Parsing Technologies (IWPT), October 2001. https://aclanthology.org/W01-1812/
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137
- Kok, S., Domingos, P. *Learning Markov Logic Network Structure via Hypergraph Lifting.* ICML 2009. https://icml.cc/Conferences/2009/papers/576.pdf
- Liu, Y., Yao, Q., Li, Y. *Role-Aware Modeling for N-ary Relational Knowledge Bases.* WWW 2021; arXiv:2104.09780. https://arxiv.org/abs/2104.09780
- Chen, X., Chen, M., Shi, W., Sun, Y., Zaniolo, C. *Embedding Uncertain Knowledge Graphs.* AAAI 2019; arXiv:1811.10667. https://arxiv.org/abs/1811.10667
- Guan, S., Cheng, X., Bai, L., Zhang, F., Li, Z., Zeng, Y., Jin, X., Guo, J. *What is Event Knowledge Graph: A Survey.* arXiv:2112.15280, 2021 (rev. 2022). https://arxiv.org/abs/2112.15280
- Rospocher, M., van Erp, M., Vossen, P., et al. *Building event-centric knowledge graphs from news.* Journal of Web Semantics 37–38:132–151, 2016. https://doi.org/10.1016/j.websem.2015.12.004
- Carroll, J. J., Bizer, C., Hayes, P., Stickler, P. *Named Graphs, Provenance and Trust.* WWW 2005. https://dl.acm.org/doi/10.1145/1060745.1060835
- W3C. *RDF 1.2 Concepts and Abstract Data Model.* Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. *SHACL 1.2 Rules.* W3C Working Draft, 2026. https://www.w3.org/TR/shacl12-rules/
- Groth, P., Gibson, A., Velterop, J. *The anatomy of a nanopublication.* Information Services & Use 30(1-2):51–56, 2010. https://dl.acm.org/doi/10.5555/1883685.1883690
- Iordanov, B. *HyperGraphDB: A Generalized Graph Database.* WAIM 2010 workshops. https://hypergraphdb.org/docs/hypergraphdb.pdf
- Joslyn, C., Nowak, K. *Ubergraphs: A Definition of a Recursive Hypergraph Structure.* arXiv:1704.05547, 2017. https://arxiv.org/abs/1704.05547
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21, 2025. https://doi.org/10.1017/nws.2025.10018
- HIF-org. *HIF-standard* repository, checked 2026-09-20. https://github.com/HIF-org/HIF-standard
