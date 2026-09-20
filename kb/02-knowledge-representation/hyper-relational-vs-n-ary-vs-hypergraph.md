---
title: Hyper-relational vs n-ary vs hypergraph — a terminology and decision guide
type: comparison
status: draft
tags: [terminology, n-ary, hyper-relational, qualifiers, roles, star-to-clique, events, frames, nalp, ram, hinge, stare]
created: 2026-09-20
updated: 2026-09-20
---

# Hyper-relational vs n-ary vs hypergraph

Four or five names circulate for what looks like the same thing: *n-ary fact*, *hyper-relational
fact*, *multi-fold relation*, *hyperedge*, *event*, *frame instance*. They are **not**
interchangeable. Each fixes a different answer to three questions:

1. **How is an argument identified?** By position, by a named role, or by a qualifier property.
2. **Is one pair of arguments privileged?** A primary (subject, object) pair, or are all peers?
3. **Is the arity bounded and fixed per relation?**

This note pins the definitions down with quotations, gives the standard conversions between them
(including what each conversion loses), places event and frame representations on the same map, and
closes with a decision table. The competing *definitions of a knowledge hypergraph* are catalogued
separately in [what-is-a-knowledge-hypergraph.md](what-is-a-knowledge-hypergraph.md); the RDF-side
workarounds are in [n-ary-relations-and-reification.md](n-ary-relations-and-reification.md).

## 1. The three formalisations, as the survey literature names them

The 2025 survey of link prediction in n-ary knowledge graphs is the cleanest statement of the
three-way split. It defines an **NKG** as "a set of facts, each of which may contain more than two
entities, which is also referred to as an n-ary fact", and then lists "hyperedge, role-value pair,
and hyper-relation formalizations" ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)).

### (1) Hyperedge formalisation — positional roles

> "A hyperedge connects all entities in an n-ary fact (Wen et al., 2016), e.g., (H, e1, ..., en),
> where e∗ is the ∗-th entity and hyperedge H indicates the role of each entity in the fact. ...
> Note that under the hyperedge formalization, the entities in the formalized fact are ordered with
> a fixed number of entities. Each position in the hyperedge represents a fixed role."
> ([Wei et al., 2025](https://arxiv.org/abs/2506.08970))

Worked example from the same source:
`(educated_with_degree_major, Einstein, Uni. Zurich, PhD, Physics)`.

This is the formalisation used by [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)
(`r(e1, ..., ek)`, arity fixed per relation) and, in a role-function variant, by
[Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf), who explicitly reject bare
positions: they argue the algebraic definition of an n-ary relation as a subset of `N^J` "is
incomplete, in the sense that the role of each coordinate in the cartesian product is not
specified", and define a relation instead as "a subset of N^M" for a role set M — i.e. an instance
is a *function from roles to entities*.

Note the price of the relation symbol carrying the role assignment: every distinct combination of
roles needs its own relation. `educated_with_degree_major` and `educated_with_degree` are two
different relations, not one relation observed with different arities.

### (2) Role-value pair formalisation — named roles, no privileged pair

> "An n-ary fact is formulated as multiple role-value pairs (Guan et al., 2019), such as
> {ri : vi}ⁿ_{i=1}, where value vi is an entity and plays the role ri in the fact ... Note that in
> the role-value pair formalization, the role-value pairs within a fact are unordered and may
> involve an arbitrary number of entities. This representation offers flexibility in specifying the
> roles of entities in n-ary facts. However, it fails to account for the varying importance or
> prominence of different entities within the same fact."
> ([Wei et al., 2025](https://arxiv.org/abs/2506.08970))

Same fact: `{person: Einstein, institution: Uni. Zurich, degree: PhD, major: Physics}`.

This is NaLP's representation ([Guan et al., 2019](https://dl.acm.org/doi/10.1145/3308558.3313414),
WWW 2019) and the one that RAM builds on. RAM's motivation is worth quoting because it is the
strongest *empirical* argument for named roles over positions:

> "in an n-ary relational fact, the involved entities play different roles, e.g., the ternary
> relation PlayCharacterIn consists of three roles, Actor, Character and Movie. ... we start from
> the role level, and propose a Role-Aware Modeling, RAM for short ... RAM explores a latent space
> that contains basis vectors, and represents roles by linear combinations of these vectors. This
> way encourages semantically related roles to have close representations."
> ([Liu, Yao and Li, 2021](https://arxiv.org/abs/2104.09780))

and the observation that justifies sharing role embeddings across arities:

> "A key observation on n-ary relational dataset WikiPeople [15] is that over 80% roles in
> beyond-ternary relations also appear in lower-arity relations."
> ([Liu, Yao and Li, 2021](https://arxiv.org/abs/2104.09780))

RAM also notes where the vocabulary of "roles" comes from: "World Wide Web Consortium (W3C) and
Schema.org introduce the semantic property of role for n-ary relations"
([Liu, Yao and Li, 2021](https://arxiv.org/abs/2104.09780)) — that is,
[Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/) and
[schema.org Role](https://schema.org/Role). See
[ontologies-and-schemas-for-n-ary-knowledge.md](ontologies-and-schemas-for-n-ary-knowledge.md).

### (3) Hyper-relational formalisation — primary triple + qualifiers

> "An n-ary fact is formulated as a primary triple coupled with a set of qualifier role-value pairs
> (Rosso et al., 2020; Guan et al., 2020), i.e., ((h, r, t), {ri : vi}ⁿ⁻²_{i=1}) ... Note that when
> there is no clear subject (i.e., head entity) or object (i.e., tail entity) in the facts, it is
> not appropriate to use the hyper-relational formalization."
> ([Wei et al., 2025](https://arxiv.org/abs/2506.08970))

Same fact: `((Einstein, educated, Uni. Zurich), {major: Physics, degree: PhD})`.

HINGE describes the underlying data as "hyper-relational data (a.k.a. multi-fold or n-ary
relational data), where each fact contains multiple relations and entities" and decomposes a
Wikidata statement into "a base triplet: (h, r, t)" plus "key-value (relation-entity) pairs (k, v)"
([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf)). StarE goes further and
argues the two families are *conceptually* distinct:

> "We deem hyper-relational graphs and hypergraphs are conceptually different. As hyperedges contain
> multiple nodes, such hyperedges are closer to n-ary relations r(e1, . . . , en) with one abstract
> relation. The attribution of entities to the main triple or qualifiers is lost, and qualifying
> relations are not defined. Combining a certain set of main and qualifying relations into one
> abstract rk() would lead to a combinatorial explosion of typed hyperedges since, in principle, any
> relation could be used in a qualifier, and there the amount of qualifiers per fact is not limited."
> ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847))

That combinatorial-explosion argument is the practical reason Wikidata-derived data resists the
hyperedge formalisation: WD50K contains statements of arity 2 through 67
([Wei et al., 2025](https://arxiv.org/abs/2506.08970)), and a fixed-arity relation symbol per role
combination is not viable at that spread.

The primary-triple choice buys a semantic property the other two do not have. HyperMono states it:
"by attaching more qualifier pairs to a main triple, we may only narrow down the answer set, but
never enlarge it" ([Hu et al., 2024](https://arxiv.org/abs/2404.09848)). Qualifiers *restrict*;
peer roles in a tuple do not obviously do anything of the kind.

## 2. Conversions and what each loses

### Star-to-clique (S2C)

Defined precisely by [Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf):

> "On an edge labelled graph G, let (u, r, v) denote the labelled edge connecting vertices u and v
> with label r, and let N(v) denote the set of all adjacent vertices of v. Then the star-to-clique
> conversion on a vertex s is defined by the following procedure. (1) For every x1, x2 ∈ N(s)
> forming two labelled edges (x1, r1, s) and (x2, r2, s) where r1 ≠ r2, add a labelled edge
> (x1, r1.r2, x2) to G. (2) Delete s and all edges connecting to s."

Wen et al. point out that FB15K was built this way and that "This procedure can be verified to be
irreversible, which causes a loss of structural information in the multi-fold relations". A k-ary
fact becomes C(k,2) binary facts with compound relation labels `r1.r2`.

Fatemi et al. give the concrete failure: after S2C on `flies_between(Air Canada, New York, Los
Angeles)` and its siblings, the clique over {Air Canada, New York, Los Angeles} "might" or might not
correspond to a real tuple — "star-to-clique conversion loses information"
([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)). Decomposition also multiplies the
relation vocabulary: JF17K's 322–327 relations become 381 "triple types" in the S2C version, and
the number of triples roughly doubles (254,366 vs 139,997 instances in the training split)
([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)).

### Reification (star form)

> "In order to reify a tuple having a relation defined on k entities e1, ..., ek, we form k new
> binary relations, one for each position in this relation, and a new entity e for this tuple and
> connect e to each of the k entities that are part of the given tuple using the k binary relations."
> ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137))

Reification is information-preserving — "the binary relations created are equivalent to the original
representation and reification does not lose information during conversion" — but Fatemi et al.
identify the *learning* failure: "because we introduce new entities that the model never encounters
during training, we do not have a learned embedding for these entities". A reified node is a fresh
identifier with no history.

Whether decomposition actually costs accuracy is **not settled**. A 2025 study finds that after
decomposition standard KG embedding models perform comparably to specialised hyper-relational
models, while cautioning that decomposition "alter[s] the original HKG topology and fail[s] to fully
preserve HKG information" ([Wang et al., 2025](https://arxiv.org/abs/2508.03280)).

### Conversion table

| From → To | Procedure | Lossless? | What is lost or added |
|---|---|---|---|
| tuple `r(e1..ek)` → role-value set | pair each position with the role name for that position | yes, if the schema names positions | nothing, if role names exist; otherwise roles must be invented |
| role-value set → tuple | fix an order on roles; mint one relation per role set | yes, per role set | one relation symbol per *combination* of roles: combinatorial blow-up ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)) |
| hyper-relational → role-value set | drop the primary/qualifier distinction | no | subject/object attribution, and the monotonicity property ([Hu et al., 2024](https://arxiv.org/abs/2404.09848)) |
| role-value set → hyper-relational | elect one role pair as (h, r, t) | no (arbitrary) | the choice is a modelling decision; Freebase→Wikidata had to make it ([Pellissier Tanon et al., 2016](https://dl.acm.org/doi/10.1145/2872427.2874809)) |
| n-ary → reified star | new node + k role edges | yes structurally | fresh identifier with no embedding/history ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)) |
| n-ary → clique (S2C) | C(k,2) compound-labelled edges | **no**, irreversible ([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)) | which tuples actually co-occur; relation vocabulary inflates |
| hyper-relational → triples only | keep the main triple, drop qualifiers | no | all qualifiers; HINGE measures the remaining signal and finds base triplets still dominate ([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf)) |

## 3. Event-centric representations

Events are n-ary by nature ("who did what, when and where"), but the event community usually
*reifies* rather than uses hyperedges. The event-KG survey defines:

> "EKG G = {(s, p, o) | {s, o} ∈ N, p ∈ E, N = N_evt ∪ N_ent, E = E_evt-evt ∪ E_evt-ent ∪
> E_ent-ent} is a graph of events N_evt, entities N_ent, and their relations E"
> ([Guan et al., 2021/2022](https://arxiv.org/abs/2112.15280))

— i.e. an event is a *node*, its arguments hang off it by role edges, and the whole thing is still a
triple store. The same survey notes that "an event has its own components, each consisting of an
argument and the argument role that the argument plays in the event". Structurally that is Pattern 1
of the W3C n-ary note, or the incidence graph of a role-value-pair hyperedge.

The NewsReader event-centric knowledge graphs are built on the Simple Event Model plus the Grounded
Annotation Framework: "GAF provides links between events and the sources where they are mentioned
and SEM models the events themselves, their participants, location and time" and "SEM provides a
generic framework to represent who did what when and where"
([Rospocher et al., 2016](https://doi.org/10.1016/j.websem.2015.12.004)). Importantly, SEM's four
generic slots are *coarser* than roles: "SEM does not distinguish what exact role each participant
plays", which is why the pipeline additionally links events to FrameNet frames and to the Event and
Situation Ontology (same source).

**Reading**: an event node is a hyperedge that has been given an identity. Whether you call it an
event or a hyperedge is a question of whether the identity is needed (for coreference, provenance,
subevent links) — see
[directed-and-typed-hyperedges-for-knowledge.md](directed-and-typed-hyperedges-for-knowledge.md).

## 4. Semantic frames

Frame semantics supplies the oldest large inventory of named roles. In FrameNet, "the role names
(called frame elements or FEs) are local to particular conceptual structures (frames); some of these
are quite general, while others are specific to a small family of lexical items"
([Baker, Fillmore and Lowe, 1998](https://aclanthology.org/P98-1013/)). The example given is the
TRANSPORTATION frame, which "provides MOVERS, MEANS of transportation, and PATHS"; the paper also
introduces **Frame Element Groups (FEGs)**, "Some combinations of frame elements ... for some real
corpus sentences" — which is precisely the observation that one frame is realised at several
arities, i.e. the same fact that RAM measures as 80% role reuse across arities.

The correspondence is close enough to be a design rule:

| KHG term | Frame-semantics term |
|---|---|
| relation type | frame |
| role | frame element (core FE ≈ required role) |
| n-ary fact / hyperedge | frame instance (annotated target + FEs) |
| observed arity variation | frame element group |

The caveat is that frames are *lexical*: a frame is evoked by a word, and the FE inventory was built
to explain syntactic realisation, not to be a database schema. Wikidata property constraints and
TypeDB role declarations do the schema job instead
([ontologies-and-schemas-for-n-ary-knowledge.md](ontologies-and-schemas-for-n-ary-knowledge.md)).

## 5. Decision table

| If your data looks like this | Use | Why | Watch out for |
|---|---|---|---|
| fixed-shape records, every field always present, e.g. `performance(actor, character, film)` | **positional n-ary tuple** | arity and roles are implicit in the relation symbol; tensor-friendly; smallest encoding | a missing or extra field needs a *new relation*; role names are lost unless recorded separately |
| the same situation shows up with 3, 5 or 8 participants, and no participant is obviously "the subject" — a purchase, a clinical trial arm, a chemical reaction | **role-value set** | roles are explicit and shared across arities ([Liu et al., 2021](https://arxiv.org/abs/2104.09780)); this is W3C n-ary use case 3 ([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)) | no privileged pair means no cheap "triple view", no monotonicity property, and harder alignment to triple-based tools |
| a binary fact with context: valid time, source, unit, determination method | **primary triple + qualifiers** | matches Wikidata natively; degrades gracefully to a triple; qualifiers only narrow the answer set ([Hu et al., 2024](https://arxiv.org/abs/2404.09848)) | electing the main value is an arbitrary modelling decision when several fields are peers |
| facts about facts, rules, nested contexts | **nested hyperedges / metagraph** | edges may contain edges ([Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547); [Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)) | very little tooling, and few benchmarks; see [metagraphs-atomspace-and-hypergraphdb.md](metagraphs-atomspace-and-hypergraphdb.md) |
| narrative text with participants, time, place, coreference across documents | **event nodes (reified)** | events need identity for coreference, subevent and causal links ([Guan et al., 2021](https://arxiv.org/abs/2112.15280); [Rospocher et al., 2016](https://doi.org/10.1016/j.websem.2015.12.004)) | you are back to reification; roles come from a frame inventory that may not match your schema |
| rules, implications, derivations | **directed hyperedge (tail → head)** | a B-arc *is* a Horn clause ([Klein and Manning, 2001](https://aclanthology.org/W01-1812/)) | this is a different use of "hyperedge" from an n-ary fact; do not mix the two in one edge set without a type marker |
| you must interoperate with RDF tooling today | **RDF 1.2 triple terms + reifiers**, or the 2006 Pattern 1 | standardised, queryable with SPARQL 1.2 | RDF 1.2 gives no first-class n-ary predicate ([n-ary-relations-and-reification.md](n-ary-relations-and-reification.md)) |

**Rule of thumb.** Ask "is there a fact here that would still be a fact if you deleted the extra
arguments?" If yes, you have a triple with qualifiers. If deleting an argument destroys the fact,
you have a genuine n-ary tuple or role-value set.

## Sources

- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs.* arXiv:2506.08970, 2025. https://arxiv.org/abs/2506.08970
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. *On the Representation and Embedding of Knowledge Bases Beyond Binary Relations.* IJCAI 2016. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137
- Guan, S., Jin, X., Wang, Y., Cheng, X. *Link Prediction on N-ary Relational Data.* WWW 2019. https://dl.acm.org/doi/10.1145/3308558.3313414
- Liu, Y., Yao, Q., Li, Y. *Role-Aware Modeling for N-ary Relational Knowledge Bases.* WWW 2021; arXiv:2104.09780. https://arxiv.org/abs/2104.09780
- Rosso, P., Yang, D., Cudré-Mauroux, P. *Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction.* WWW 2020. https://exascale.info/assets/pdf/rosso2020www.pdf
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020; arXiv:2009.10847. https://arxiv.org/abs/2009.10847
- Hu, Z., Gutiérrez-Basulto, V., Xiang, Z., Li, R., Pan, J. Z. *HyperMono: A Monotonicity-aware Approach to Hyper-Relational Knowledge Representation.* arXiv:2404.09848, 2024. https://arxiv.org/abs/2404.09848
- Wang, Y., Di, S., Wang, Z., Li, H., Teng, F., Xin, H., Chen, L. *Understanding the Embedding Models on Hyper-relational Knowledge Graph.* CIKM 2025; arXiv:2508.03280. https://arxiv.org/abs/2508.03280
- Pellissier Tanon, T., Vrandečić, D., Schaffert, S., Steiner, T., Pintscher, L. *From Freebase to Wikidata: The Great Migration.* WWW 2016. https://dl.acm.org/doi/10.1145/2872427.2874809
- Noy, N., Rector, A. (eds). *Defining N-ary Relations on the Semantic Web.* W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- schema.org. *Role.* Version 30.1, 16 September 2026 (checked 2026-09-20). https://schema.org/Role
- Guan, S., Cheng, X., Bai, L., Zhang, F., Li, Z., Zeng, Y., Jin, X., Guo, J. *What is Event Knowledge Graph: A Survey.* arXiv:2112.15280, 2021 (rev. 2022). https://arxiv.org/abs/2112.15280
- Rospocher, M., van Erp, M., Vossen, P., Fokkens, A., Aldabe, I., Rigau, G., Soroa, A., Ploeger, T., Bogaard, T. *Building event-centric knowledge graphs from news.* Journal of Web Semantics 37–38:132–151, 2016. https://doi.org/10.1016/j.websem.2015.12.004
- Baker, C. F., Fillmore, C. J., Lowe, J. B. *The Berkeley FrameNet Project.* COLING-ACL 1998. https://aclanthology.org/P98-1013/
- Klein, D., Manning, C. D. *Parsing and Hypergraphs.* International Workshop on Parsing Technologies (IWPT) 2001. https://aclanthology.org/W01-1812/
- Joslyn, C., Nowak, K. *Ubergraphs: A Definition of a Recursive Hypergraph Structure.* arXiv:1704.05547, 2017. https://arxiv.org/abs/1704.05547
- Iordanov, B. *HyperGraphDB: A Generalized Graph Database.* WAIM 2010 workshops, Springer LNCS. https://hypergraphdb.org/docs/hypergraphdb.pdf
