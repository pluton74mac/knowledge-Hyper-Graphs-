---
title: From knowledge graphs to hypergraphs — lifting Wikidata qualifiers, Freebase CVTs and tables into n-ary facts
type: howto
status: draft
tags: [hypergraph, n-ary, wikidata, qualifiers, freebase, cvt, reification, star-to-clique, datasets, WD50K, JF17K, WikiPeople, FB-AUTO]
created: 2026-09-19
updated: 2026-09-20
---

# From knowledge graphs to hypergraphs

Most benchmark knowledge hypergraphs were not extracted from text. They were *lifted* from existing
knowledge bases whose data model already encodes n-ary facts in a binary-looking form: Wikidata statements
with qualifiers, and Freebase compound value types. This note documents how the standard datasets were
built, what the reverse operations (reification, star-to-clique) lose, and how tables and event logs can be
lifted the same way.

## 1. Where n-ary facts hide in binary KGs

### Wikidata: statements with qualifiers

In the Wikibase data model "A statement may consist of one property (in the example, 'population') one
value (3,5 M) optionally one or more qualifiers (in this example, 'as of 2011' is one of the qualifiers)
optionally one or more references"; the claim is "the property, value, and qualifiers together"
([Wikibase DataModel Primer](https://www.mediawiki.org/wiki/Wikibase/DataModel/Primer)). Qualifiers "allow
statements to be expanded on, annotated, or contextualized beyond what can be expressed in just a simple
property-value pair" ([Wikidata Help:Qualifiers](https://www.wikidata.org/wiki/Help:Qualifiers)); the help
page's examples are exactly n-ary facts: Louis XIV *position held* King of France and Navarre with *start
time* 14 May 1643 and *end time* 1 September 1715; Berlin *population* 3,500,000 with *point in time* 2005; a
mayor's position with *applies to jurisdiction* Rochefourchat. A statement with k qualifiers is a
hyper-relational fact `((s, p, o), {(q_i, v_i)}_{i=1..k})`, arity k+2.

### Freebase: compound value types

"Freebase uses Compound Value Types (CVTs) to represent n-ary relations with n > 2, e.g., values like
geographic coordinates, political positions held with a start and an end date …, or actors playing a
character in a movie. CVT values are just objects, i.e., they have a mid and can have types"
([Pellissier Tanon et al., 2016](https://research.google.com/pubs/archive/44818.pdf)). A CVT node is a
reified n-ary fact: one property links the topic to the CVT, and the CVT's properties point to the component
values. The Freebase-to-Wikidata migration had to *un*-reify: "In order to map a CVT to a statement, we have
to know which of the CVT's properties should be used as the main value of the statement, with the others being
mapped to qualifiers", and "For CVTs that include sources, we map the property that links the CVT to the
source as a Wikidata reference instead of a qualifier" (same source). This is the general recipe for turning
a reified node into a hyperedge: collect all binary edges incident to the mediator node, pick one as the main
relation (or none, for a role-based fact), treat the rest as roles.

### Why plain triple datasets lost this

The standard benchmark FB15K was derived from Freebase by converting mediator structures into triples.
[Wen et al., 2016](https://arxiv.org/abs/1604.08642) show that this "S2C conversion" (star-to-clique)
produces "a collection of entity-predicate-entity triples" and that "after applying S2C conversions to a graph,
in general, the graph is no longer recoverable": one can no longer tell which pairwise edges belonged to the
same fact. [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137) describe both inverse operations:
*reification* — "we form k new binary relations, one for each position in this relation, and a new entity e
for this tuple and connect e to each of the k entities" — which is lossless but introduces entities that
"the model never encounters during training"; and *star-to-clique*, "which converts a tuple defined on k
entities into C(k,2) tuples with distinct relations between all pairwise entities", which is lossy.
[Guan et al., 2019](https://dl.acm.org/doi/10.1145/3308558.3313414) put it directly: decomposition into
triples "may cause loss of structural information".

## 2. How the benchmark KHGs were built

### JF17K (Freebase, 2016)

Wen et al. propose the canonical *role–value* representation of a multi-fold relation — each instance is "a
function t: M(R) → N" from roles to entities — and build JF17K from the Freebase RDF dump by removing
entities with very few triples, dropping String/Enumeration and Number values, keeping facts from
meta-relations, and sampling at most 10,000 facts per large relation, yielding "17,629 entities, 181 relation
types, 139,997 instances in training data" ([Wen et al., 2016](https://arxiv.org/abs/1604.08642); numbers
as extracted from the paper via ar5iv). Two defects were later found: it "proposed" no validation set (Fatemi
et al. "randomly select 20% of the train set as validation") and it leaks — "about 44.5% of the test
statements share the same main (s,r,o) triple as the train statements", "a major data leakage which allows
triple-based models to memorize subjects and objects appearing in the test set"
([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)). The 2025 survey reports 28,645 entities, 501
roles, arity 2–6, 45.9% n-ary facts, 100,947 facts for the version now in circulation
([Wei et al., 2025](https://arxiv.org/abs/2506.08970)).

### WikiPeople (Wikidata, 2019)

Built from the Wikidata dump of 20 November 2017 by taking facts about entities of type human, removing
"facts containing element related to image" and facts with "unknown value" or "no values", keeping elements
with at least 30 mentions, and splitting 80/10/10. Each line is "a set of ('role id': 'value id/list of value
ids') and the arity information in form of ('N': arity)"; ids ending in `_h`/`_t` are the dataset's own
subject/object roles, other ids are Wikidata property ids
([WikiPeople repository](https://github.com/gsp2014/WikiPeople); [Guan et al., 2019](https://dl.acm.org/doi/10.1145/3308558.3313414)).
Training: 305,725 facts (270,179 binary, 35,546 n-ary), i.e. **11.6% n-ary facts** over the whole release
(44,315 of 382,229) — the same figure the 2025 survey reports
([Wei et al., 2025](https://arxiv.org/abs/2506.08970)). That is the share of *n-ary facts in the release as
published*. After literals are removed — the version HINGE and StarE evaluate on — a different quantity
applies: Galkin et al. report that "less than 3% of the remaining statements contain any qualifier pairs. Out
of those, about 80% possess only one qualifier", and Rosso et al.'s Table 1 puts the same quantity at **2.6%**
hyper-relational facts. So results on the filtered WikiPeople are dominated by plain triples. The three
numbers are reconciled in
[../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md) §3.

### FB-AUTO and M-FB15K (Freebase, 2019/2020)

Fatemi et al. inverse-reify Freebase: "Remove the facts that have relations defined on a single entity, or
that contain numbers or enumeration as entities", "Join the triples in Freebase that have the same subject and
actual relation, and the same entity", then "Create the FB-auto dataset by selecting the facts … whose subject
is 'automotive'" (3,410 entities, 8 relations, 6,778/2,255/2,180 train/valid/test) and M-FB15K by selecting
"facts … that pertain to entities present in the Wikilinks database" (10,314 entities, 71 relations,
415,375/39,348/38,797) ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)).

### WD50K (Wikidata, 2020)

The most carefully documented lift. From "the Wikidata RDF dump of August 2019": seed nodes are FB15K-237
entities with a Freebase-ID (P646) mapping to Wikidata; extract "all statements whose main object and qualifier
values correspond to wikibase:Item", removing "all literals in object position" and from qualifiers; drop
entities "mentioned less than twice"; split; then "remove all statements from train and validation sets that
share the same main triple (s,p,o) with test statements" to prevent the JF17K leak
([Galkin et al., 2020](https://arxiv.org/abs/2009.10847); [StarE data README](https://github.com/migalkin/StarE/blob/master/data/clean/README.md)).
Format: `s, r, o, qr_1, qv_1, qr_2, qv_2 ...`. Statistics:

| Dataset | Statements | With qualifiers | Entities | Relations | Train / Valid / Test |
|---|---|---|---|---|---|
| WD50K | 236,507 | 13.6% | 47,156 | 532 | 166,435 / 23,913 / 46,159 |
| WD50K(33) | 102,107 | 31.2% | 38,124 | 475 | 73,406 / 10,568 / 18,133 |
| WD50K(66) | 49,167 | 64.5% | 27,347 | 494 | 35,968 / 5,154 / 8,045 |
| WD50K(100) | 31,314 | 100% | 18,792 | 279 | 22,738 / 3,279 / 5,297 |

The survey lists WD50K arity as 2–67 ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)), i.e. some
statements carry dozens of qualifier pairs.

### HINGE's view of the same data

[Rosso, Yang & Cudré-Mauroux, 2020](https://dl.acm.org/doi/10.1145/3366423.3380257) treat each fact as a
triple plus key–value pairs and note the balance in JF17K: "57.8% triple facts vs 42.2% hyper-relational
facts in the training dataset and 42.4% triple facts vs 57.6% hyper-relational facts in the test dataset"
(as reported in a secondary summary of the paper; the ACM full text was not accessible in this run
[unverified numbers]).

## 3. A general lifting procedure

Distilled from the four datasets above:

1. **Pick the statement model.** Wikidata: statement = main snak + qualifiers; Freebase: topic → CVT →
   components; RDF: reified node or blank node with n properties (the W3C note "Defining N-ary Relations on
   the Semantic Web" describes "a new class and n new properties to represent an n-ary relation"
   ([Noy & Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/))).
2. **Decide the target schema**: hyper-relational (keep the main triple), role-based (all components are
   roles, as WikiPeople's `_h`/`_t` trick shows), or hypergraph-based (drop roles; order encodes position).
3. **Filter values**: literals (dates, numbers, strings, images) are usually dropped because embedding
   models cannot handle them (WD50K, WikiPeople, FB-AUTO all do this), which removes precisely the temporal
   qualifiers that make many facts n-ary. A KHG intended for reasoning rather than embedding should keep them.
4. **Filter entities by frequency** (≥ 2 in WD50K, ≥ 30 in WikiPeople) and remove `unknown value` /
   `no value` snaks.
5. **Split without leakage**: remove train/valid statements sharing the main triple with test statements.
6. **Record provenance**: Wikidata references and ranks ("Preferred", "Normal", "Deprecated") exist in the
   source and are discarded by all four datasets; keeping the reference URLs would let the KHG carry
   provenance for free.

## 4. Tables, relational databases and logs

A row in a relational table is a hyperedge over the values it joins; the table schema itself is a hypergraph
whose nodes are attributes and whose edges are relation schemes — the object studied by
[Beeri, Fagin, Maier & Yannakakis, 1983](https://dl.acm.org/doi/10.1145/2402.322389) and
[Fagin, 1983](https://dl.acm.org/doi/10.1145/2402.322390) under the name of acyclic database schemes (titles
and venue confirmed; the classical result that a scheme is acyclic iff its hypergraph is α-acyclic is stated
from general knowledge of these papers and is [unverified] against the full text in this run). Two concrete
lifts:

- **Row → hyperedge.** Each row of a fact table becomes a hyperedge connecting the entities referenced by its
  foreign keys, with the remaining columns as attributes of the hyperedge (or as roles, in the role-based
  schema). This is the tabular analogue of a CVT.
- **Foreign keys → binary graph.** The alternative taken by relational deep learning represents a database as
  "a temporal, heterogeneous graph, with a node for each row in each table, and edges specified by
  primary-foreign key links" ([Fey et al., 2023](https://arxiv.org/abs/2312.04615)) — i.e. every row is
  reified as a node. Star-to-clique would instead connect all foreign-key targets pairwise and lose the row.

Event logs (one line per event with several participants) lift like fact tables: an event is a hyperedge over
its participants with a timestamp attribute; this is exactly the "timestamped simplices" model of
[Benson et al., 2018](https://arxiv.org/abs/1802.06916) discussed in
[hypergraph construction from data](hypergraph-construction-from-data.md).

## 5. Practical notes

- Wikidata is the richest open source of ready-made n-ary facts, but qualifier density is low (13.6% of
  WD50K statements after filtering), and the choice of seed entities shapes the result.
- Freebase is frozen (read-only since 31 March 2015, per Pellissier Tanon et al.); its CVTs survive in
  Wikidata as qualifiers and references only where the migration mapped them.
- Every lifted benchmark discarded literals, references and ranks — features a knowledge hypergraph for
  reasoning or provenance would want to keep.

## Sources

- Wikimedia. "Wikibase/DataModel/Primer", checked 2026-09-19. https://www.mediawiki.org/wiki/Wikibase/DataModel/Primer
- Wikidata. "Help:Qualifiers", checked 2026-09-19. https://www.wikidata.org/wiki/Help:Qualifiers
- Pellissier Tanon, T., Vrandečić, D., Schaffert, S., Steiner, T., Pintscher, L. "From Freebase to Wikidata: The Great Migration." WWW 2016. https://research.google.com/pubs/archive/44818.pdf
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the representation and embedding of knowledge bases beyond binary relations." IJCAI 2016 / arXiv 1604.08642. https://arxiv.org/abs/1604.08642
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." IJCAI 2020 / arXiv 1906.00137. https://arxiv.org/abs/1906.00137
- Guan, S., Jin, X., Wang, Y., Cheng, X. "Link Prediction on N-ary Relational Data." The Web Conference 2019. https://dl.acm.org/doi/10.1145/3308558.3313414
- gsp2014. WikiPeople repository ("An n-ary relational dataset derived from Wikidata"), checked 2026-09-19. https://github.com/gsp2014/WikiPeople
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs." EMNLP 2020 / arXiv 2009.10847. https://arxiv.org/abs/2009.10847
- migalkin. StarE repository, `data/clean/README.md` (WD50K description), checked 2026-09-19. https://github.com/migalkin/StarE/blob/master/data/clean/README.md
- Rosso, P., Yang, D., Cudré-Mauroux, P. "Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction." The Web Conference 2020. https://dl.acm.org/doi/10.1145/3366423.3380257
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. "A Survey of Link Prediction in N-ary Knowledge Graphs." arXiv 2506.08970, 2025. https://arxiv.org/abs/2506.08970
- Noy, N., Rector, A. (eds.). "Defining N-ary Relations on the Semantic Web." W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- Beeri, C., Fagin, R., Maier, D., Yannakakis, M. "On the Desirability of Acyclic Database Schemes." Journal of the ACM 30(3), 1983. https://dl.acm.org/doi/10.1145/2402.322389
- Fagin, R. "Degrees of acyclicity for hypergraphs and relational database schemes." Journal of the ACM 30(3), 1983. https://dl.acm.org/doi/10.1145/2402.322390
- Fey, M., Hu, W., Huang, K., Lenssen, J. E., et al. "Relational Deep Learning: Graph Representation Learning on Relational Databases." arXiv 2312.04615, 2023. https://arxiv.org/abs/2312.04615
- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. "Simplicial closure and higher-order link prediction." PNAS 115(48), 2018 / arXiv 1802.06916. https://arxiv.org/abs/1802.06916
