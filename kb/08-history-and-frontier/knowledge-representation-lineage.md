---
title: The knowledge-representation lineage — semantic nets to hyper-relational KGs
type: survey
status: draft
tags: [history, knowledge-representation, semantic-networks, frames, conceptual-graphs, description-logic, owl, knowledge-graph, n-ary, reification]
created: 2026-09-20
updated: 2026-09-20
---

# The knowledge-representation lineage, and the recurring flattening of n-ary facts

This note follows the *other* ancestry of the knowledge hypergraph: not the mathematics of set
systems ([origins-hypergraph-theory.md](origins-hypergraph-theory.md)) but the sixty-year attempt to
write down what a machine knows. Dated events are in [timeline.md](timeline.md). The formalisms
themselves are compared in
[../02-knowledge-representation/what-is-a-knowledge-hypergraph.md](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md)
and the encoding patterns in
[../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md).

The thesis of this note is a single repeated pattern:

> **Every generation of knowledge representation starts with n-ary structures, because that is what
> the world looks like; and every generation then flattens them to binary links, because that is
> what the exchange format, the index, or the algorithm wants. The flattening is then rediscovered
> as a problem by the next generation.**

## 1. Semantic networks (1956–1968): binary from the start

The first machine-readable "concept + typed link" structures are Richens's semantic nets at the
Cambridge Language Research Unit, used as a machine-translation interlingua from 1956
([Wikipedia, Semantic network](https://en.wikipedia.org/wiki/Semantic_network), secondary source).
The canonical cognitive-science model is Quillian's, in his 1966 dissertation and in the 1968
chapter "Semantic Memory" in Minsky's *Semantic Information Processing* (MIT Press, pp. 227–270)
([Quillian 1968 summary](https://www.jimdavies.org/summaries/quillian1968.html);
[PhilPapers record](https://philpapers.org/rec/QUISN)).

Quillian's network has *type nodes* and *token nodes*, superordinate ("isa") links, and modifier
and disjunctive/conjunctive structures; retrieval works by **spreading activation** from two
concepts until the search fronts intersect. Structurally, the primitive is a labelled pointer from
one node to another: a **binary** edge. Everything that is not binary — a three-place event, a
qualified assertion — has to be encoded as an auxiliary node with several pointers hanging off it.

That auxiliary node is the first appearance of what will later be called reification, a mediator, a
compound value type, a statement node, or a reifier. It is the same trick every time.

## 2. Frames (1974): the n-ary record returns

Minsky's "A Framework for Representing Knowledge" (MIT AI Memo 306, June 1974;
[MIT DSpace](https://dspace.mit.edu/entities/publication/0eca0164-cb5f-42de-8c86-43f54b23306d))
proposes the *frame*: a data structure for a stereotyped situation, with **slots** that are filled
by values, defaults, or other frames, and attached procedures.

A frame is, formally, an n-ary record with named fields — `Buy(buyer, seller, object, price, date)`
— with defaults and inheritance on top. So the very first reaction against pure semantic nets was
to restore n-ary structure. Frame systems (KRL, FRL, KEE, and later the frame-based ontology
editors) kept it. But a frame instance is also, read another way, exactly the "new class for the
relation" reification pattern: the frame *is* the mediating node, and its slots *are* binary
properties. The ambiguity between "an n-ary fact" and "an object whose binary properties encode an
n-ary fact" is present from 1974 onward and is never resolved; it is the same ambiguity that makes
"knowledge hypergraph" mean different things to different communities today.

## 3. Conceptual graphs (1976, 1984): explicit n-ary relation nodes

Sowa's conceptual graphs are the first mainstream KR formalism in which arbitrary arity is a
first-class, drawn, syntactic feature.

> Sowa, J. F. "Conceptual Graphs for a Data Base Interface," *IBM Journal of Research and
> Development* 20(4):336–357, July 1976
> ([DOI 10.1147/rd.204.0336](https://doi.org/10.1147/rd.204.0336)); book-length treatment in
> *Conceptual Structures: Information Processing in Mind and Machine*, Addison-Wesley, 1984
> ([Open Library](https://openlibrary.org/books/OL3500479M/Conceptual_structures)).

A conceptual graph is **bipartite**: *concept* nodes and *relation* nodes, with arcs from a relation
node to each of its arguments, numbered by argument position. A relation node of arity k with k
numbered arcs is, literally, a drawing of a labelled, ordered hyperedge — the bipartite incidence
representation of a hypergraph. Sowa's 1976 setting is also telling: a natural-language interface
to a *relational database*, i.e. the same n-ary world as Fagin's.

Conceptual graphs carried a Peircean existential-graph logic, were given an ISO common-logic
dialect much later, and remained a minority formalism. But the representational move — draw the
relation as a node, connect it to any number of arguments, number the arcs — is exactly what
Freebase, Wikidata, the W3C n-ary note, and modern KHG papers all re-derive.

## 4. Description logics and OWL (1980s–2004): binary by design, on purpose

Description logics grew out of the effort to give frame systems a formal semantics and decidable
reasoning. The tractability results that made DLs attractive depend on a *restricted* syntax, and
the central restriction is that **roles are binary**: `ALC` and its descendants describe concepts in
terms of binary relations (`∃hasChild.Person`). N-ary description logics were developed — the `DLR`
family is the usual reference, aimed at reasoning over conceptual and entity–relationship schemas —
but they never entered the Web stack `[unverified]` (no primary source checked in this run; treat
the attribution of `DLR` as needing verification before reuse).

The Web stack inherited the binary restriction wholesale. RDF's 1999 Recommendation fixes the
subject–predicate–object triple ([W3C, 22 Feb 1999](https://www.w3.org/TR/1999/REC-rdf-syntax-19990222/)),
and the 2004 RDF/OWL suite builds description-logic ontologies on top of it
([RDF Concepts, 10 Feb 2004](https://www.w3.org/TR/2004/REC-rdf-concepts-20040210/);
[OWL Reference](https://www.w3.org/TR/owl-ref/)).

The reason is not oversight. Binary relations give you: a uniform serialisation (a triple is three
terms), a uniform index (three permutations of SPO), a uniform query algebra (basic graph patterns),
and decidable fragments. Arity is the price paid for all four. Every KHG system pays that price back
in some form — see [standards-convergence.md](standards-convergence.md).

## 5. The 2006 W3C note: flattening, codified

By 2006 the gap was official. The W3C Semantic Web Best Practices group published:

> Noy, N., Rector, A. (eds.), "Defining N-ary Relations on the Semantic Web," W3C Working Group
> Note, **12 April 2006** ([www.w3.org/TR/swbp-n-aryRelations](https://www.w3.org/TR/swbp-n-aryRelations/))

Its opening statement of the problem is blunt: "In Semantic Web languages, such as RDF and OWL, a
property is a *binary* relation: it is used to link two individuals or an individual and a value."
The note then gives the two patterns that the whole subsequent field uses:

1. **Introduce a new class for the relation** — create an individual of a "relation class" and hang
   binary properties off it for each participant and each extra attribute. Presented with three use
   cases: (a) additional attributes describing a relation, (b) different aspects of the same
   relation, (c) an n-ary relation with no distinguished participant.
2. **Use lists / sequences for the arguments** when the arguments have no distinct roles and form an
   ordered collection. The note itself warns that "using the `rdf:List` vocabulary in OWL would have
   put the ontology in OWL Full" — i.e. the pattern costs you decidability.

This is the 1968 auxiliary node, the 1974 frame, and the 1976 relation node, restated as a
best-practice pattern for a triple store. It is still normative: the RDF 1.2 Candidate
Recommendation of April 2026 still says that "relations that involve more than two entities can only
be indirectly expressed in RDF" and points at this 2006 note
([RDF 1.2 Concepts, CR Snapshot 7 Apr 2026](https://www.w3.org/TR/rdf12-concepts/)).

## 6. Freebase CVTs (2007): flattening at web scale

Metaweb announced Freebase on 3 March 2007
([Wikipedia, Freebase](https://en.wikipedia.org/wiki/Freebase_(database))). Freebase's schema had to
express things like "X was married to Y from 1997 to 2004 in location Z" and "actor A played
character C in film F." Its answer was the **Compound Value Type (CVT)**, also called a *mediator*:
a typed, usually anonymous node that holds the several properties of one complex fact
([Houle, "Compound Value Types in RDF"](https://database_animals.silvrback.com/compound-value-types-in-rdf)).

Pattern 1 of the W3C note, at a scale of millions of facts. Two lasting consequences:

- Google acquired Metaweb on 16 July 2010 and Freebase became an input to the Google Knowledge
  Graph; Freebase's shutdown was announced 16 December 2014 and it went offline by 2 May 2016, with
  data migrated toward Wikidata (same Wikipedia source).
- **Every major n-ary benchmark descends from the Freebase dump.** JF17K (from
  [Wen et al., IJCAI 2016](https://arxiv.org/abs/1604.08642)) and FB-AUTO/FB15k-derived n-ary sets
  are built by *un-flattening* CVTs back into n-ary tuples. The field's evaluation data is therefore
  a reconstruction of a reification, frozen in 2015. See
  [machine-learning-era.md](machine-learning-era.md) for what that costs.

## 7. Wikidata qualifiers (2012–2013): flattening, but principled

Wikidata launched 29 October 2012, and statement editing — property–value pairs with **qualifiers**,
**references** and **ranks** — went live with "phase 2" on **4 February 2013**
([Wikimedia Deutschland blog, 4 Feb 2013](https://blog.wikimedia.de/2013/02/04/first-parts-of-phase-2-of-wikidata-going-live/);
[Help:Qualifiers](https://www.wikidata.org/wiki/Help:Qualifiers);
[Vrandečić & Krötzsch, *CACM* 57(10):78–85, 2014](https://doi.org/10.1145/2629489)).

A Wikidata statement is not a symmetric n-ary tuple. It is a **main triple plus a set of key–value
qualifiers**: an asymmetric shape in which one relation is primary and the rest are annotation. That
shape is what the literature later names **hyper-relational**
([Rosso, Yang, Cudré-Mauroux, WWW 2020](https://doi.org/10.1145/3366423.3380257)), in contrast with
the symmetric **n-ary tuple** `r(e1,…,ek)` of
[Fatemi et al., IJCAI 2020](https://doi.org/10.24963/ijcai.2020/303). The distinction is not
cosmetic: it decides what a model can predict (a missing qualifier value? a missing core entity?),
what "arity" means, and whether relations have fixed arity.

Wikidata's own RDF export flattens statements into reified statement nodes yet again — the same 1968
trick, third time around — which is why Wikidata is simultaneously the largest public source of
n-ary data and a standing demonstration that triple stores cannot hold it natively. Details in
[../02-knowledge-representation/wikidata-and-freebase-data-models.md](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

## 8. "Knowledge graph" as a brand (2012), and the return of the hypergraph (2016–2020)

Google's 16 May 2012 announcement ("things, not strings", 500 million objects, 3.5 billion facts)
made *knowledge graph* the industry term
([Google blog](https://blog.google/products-and-platforms/products/search/introducing-knowledge-graph-things-not/)).
The academic embedding literature that grew around it (TransE and successors) took the triple as
the atom, and with it the binary restriction.

The counter-movement arrives in three steps:

1. **2016 — m-TransH.** Wen, Li, Mao, Chen, Zhang, "On the Representation and Embedding of Knowledge
   Bases Beyond Binary Relations," IJCAI 2016 ([arXiv:1604.08642](https://arxiv.org/abs/1604.08642)).
   Shows that converting an n-ary Freebase fact into a star of binary triples (or a clique) loses
   information, and gives the first n-ary embedding model plus the JF17K dataset.
2. **2019 — role–value pairs.** Guan, Jin, Wang, Cheng, "Link Prediction on N-ary Relational Data,"
   WWW 2019, pp. 583–593 ([DOI 10.1145/3308558.3313414](https://doi.org/10.1145/3308558.3313414)):
   an n-ary fact as a set of role–value pairs, which is Minsky's frame with a scoring function.
3. **2019/2020 — the name.** Fatemi, Taslakian, Vazquez, Poole, "Knowledge Hypergraphs: Prediction
   Beyond Binary Relations" ([arXiv:1906.00137](https://arxiv.org/abs/1906.00137), 1 June 2019;
   IJCAI 2020, pp. 2191–2197, [DOI 10.24963/ijcai.2020/303](https://doi.org/10.24963/ijcai.2020/303)).
   This is where the mathematical lineage and the KR lineage finally join: the object that Berge
   named is proposed as the atom of a knowledge base.

## 9. Why the flattening keeps happening — five structural reasons

Not a moral failing; each is a real engineering constraint.

| Reason | Consequence |
|---|---|
| **Serialisation** wants a fixed-width record. A triple is three slots; a hyperedge is variable-length. | Line-based formats (N-Triples), fixed-arity tensors, and columnar stores all prefer triples. |
| **Indexing** wants a small, fixed set of permutations. SPO/POS/OSP covers a triple store; a k-ary edge has k! access patterns. | Native hyperedge indexes are still a research topic; see [current-frontier-directions.md](current-frontier-directions.md). |
| **Decidability** in description logics depends on binary roles. | OWL profiles stayed binary; n-ary DLs stayed academic. |
| **Algorithms** — message passing, random walks, spectral methods — were defined on graphs first. | Clique/star expansion is the cheap way to reuse them, and it is lossy. |
| **Ecosystem gravity.** Tooling, query languages, benchmarks and tutorials exist for triples. | Each new n-ary formalism must rebuild the whole stack, which is why so few survive. |

The 2024–2026 wave is the first time all five are being attacked at once: interchange format (HIF),
query standards (GQL, SPARQL 1.2), native storage (higher-order graph databases), expressivity
theory, and foundation models that transfer across arities. Whether it sticks this time is the open
question of [current-frontier-directions.md](current-frontier-directions.md).

## 10. What to take from the lineage

- The n-ary/binary tension is **not** a knowledge-hypergraph question; it is *the* knowledge
  representation question, restated every fifteen years or so.
- Any claim that "KHGs are new" should be read against Sowa 1976 and Fagin 1983.
- The *asymmetric* (triple + qualifiers) and *symmetric* (n-ary tuple) readings have different
  ancestors — Wikidata/RDF versus frames/relational — and produce mutually incompatible benchmarks.
  Check which one a paper means before comparing numbers.

## Sources

- Wikipedia. "Semantic network." https://en.wikipedia.org/wiki/Semantic_network (secondary)
- Quillian, M. R. "Semantic Memory." In M. Minsky (ed.), *Semantic Information Processing*, MIT Press, 1968, pp. 227–270. https://philpapers.org/rec/QUISN ; summary: https://www.jimdavies.org/summaries/quillian1968.html
- Minsky, M. "A Framework for Representing Knowledge." MIT AI Laboratory Memo 306, June 1974. https://dspace.mit.edu/entities/publication/0eca0164-cb5f-42de-8c86-43f54b23306d
- Sowa, J. F. "Conceptual Graphs for a Data Base Interface." *IBM Journal of Research and Development* 20(4):336–357, July 1976. https://doi.org/10.1147/rd.204.0336
- Sowa, J. F. *Conceptual Structures: Information Processing in Mind and Machine*. Addison-Wesley, 1984. https://openlibrary.org/books/OL3500479M/Conceptual_structures
- W3C. "Resource Description Framework (RDF) Model and Syntax Specification." Recommendation, 22 Feb 1999. https://www.w3.org/TR/1999/REC-rdf-syntax-19990222/
- W3C. "RDF Concepts and Abstract Syntax." Recommendation, 10 Feb 2004. https://www.w3.org/TR/2004/REC-rdf-concepts-20040210/
- W3C. "OWL Web Ontology Language Reference." Recommendation, 10 Feb 2004. https://www.w3.org/TR/owl-ref/
- Noy, N., Rector, A. (eds.). "Defining N-ary Relations on the Semantic Web." W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- W3C. "RDF 1.2 Concepts and Abstract Data Model." Candidate Recommendation Snapshot, 7 April 2026. Editors: O. Hartig, P.-A. Champin, A. Seaborne. https://www.w3.org/TR/rdf12-concepts/
- Wikipedia. "Freebase (database)." https://en.wikipedia.org/wiki/Freebase_(database)
- Houle, P. "Compound Value Types in RDF." https://database_animals.silvrback.com/compound-value-types-in-rdf
- Wikimedia Deutschland. "First parts of phase 2 of Wikidata going live." Blog, 4 Feb 2013. https://blog.wikimedia.de/2013/02/04/first-parts-of-phase-2-of-wikidata-going-live/
- Wikidata. "Help:Qualifiers." https://www.wikidata.org/wiki/Help:Qualifiers
- Vrandečić, D., Krötzsch, M. "Wikidata: a free collaborative knowledgebase." *Communications of the ACM* 57(10):78–85, 2014. https://doi.org/10.1145/2629489
- Google. "Introducing the Knowledge Graph: things, not strings." 16 May 2012. https://blog.google/products-and-platforms/products/search/introducing-knowledge-graph-things-not/
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases Beyond Binary Relations." IJCAI 2016. https://arxiv.org/abs/1604.08642
- Guan, S., Jin, X., Wang, Y., Cheng, X. "Link Prediction on N-ary Relational Data." WWW 2019, pp. 583–593. https://doi.org/10.1145/3308558.3313414
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." arXiv:1906.00137, 1 June 2019; IJCAI 2020, pp. 2191–2197. https://doi.org/10.24963/ijcai.2020/303
- Rosso, P., Yang, D., Cudré-Mauroux, P. "Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction." WWW 2020, pp. 1885–1896. https://doi.org/10.1145/3366423.3380257
