---
title: Wikidata and Freebase data models as hyper-relational knowledge
type: concept
status: draft
tags: [wikidata, freebase, cvt, qualifiers, statements, hyper-relational, wikibase, rdf]
created: 2026-09-19
updated: 2026-09-20
---

# Wikidata and Freebase data models

The two largest collaboratively built general knowledge bases both broke with plain triples, in
different ways. Freebase used *Compound Value Types* (CVTs): anonymous intermediate objects.
Wikidata uses *statements* with a main value, qualifiers, references and a rank. Most of the
benchmark datasets for n-ary and hyper-relational link prediction are carved out of these two
sources (see [benchmarks-derived-from-freebase-and-wikidata.md](benchmarks-derived-from-freebase-and-wikidata.md)),
so their data models shape what "knowledge hypergraph" means in practice.

## 1. Freebase (2007–2016)

**Timeline.** Freebase was launched on 3 March 2007 by Metaweb Technologies, acquired by Google
on 16 July 2010, and shut down on 2 May 2016, with its data offered to Wikidata; in January 2014 it
held about 44 million topics and 2.4 billion facts ([Wikipedia, Freebase](https://en.wikipedia.org/wiki/Freebase_(database))).
The SIGMOD 2008 paper describes it as "a practical, scalable tuple database used to structure
general human knowledge" with, at the time, more than 125 million tuples, 4,000 types and 7,000
properties, queried through MQL ([Bollacker et al., 2008](https://research.google/pubs/freebase-a-collaboratively-created-graph-database-for-structuring-human-knowledge/)).

**Compound Value Types.** Freebase's developer documentation defines: "A Compound Value Type is
a Type within Freebase which is used to represent data where each entry consists of multiple
fields", giving the example of a city's population, which needs a number and a date together; CVT
instances are topics with GUIDs but no display names, and their properties act as disambiguation
fields ([Google, Freebase basic concepts](https://developers.google.com/freebase/guide/basic_concepts),
checked 2026-09-19). The Google/Wikimedia migration paper states the purpose directly: "Freebase
uses Compound Value Types (CVTs) to represent n-ary relations with n > 2, e.g., values like
geographic coordinates, political positions held with a start and an end date ..., or actors
playing a character in a movie. CVT values are just objects, i.e., they have a mid and can have
types" ([Pellissier Tanon et al., 2016](https://dl.acm.org/doi/10.1145/2872427.2874809)).

A CVT is therefore Pattern 1 of the W3C n-ary note
([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)) applied at scale: the
hyperedge is a node, each role is a property from that node, and the subject is linked to the CVT by
one more property. Wen et al. call the recovered structure a "fact representation" and note that
"manipulating multi-fold relational data into triples (as in Freebase) results in an heterogeneity of
the predicates, unfavourable for embedding" ([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)).

## 2. Wikidata (2012–)

**Timeline and size.** Wikidata launched on 29 October 2012 ([Wikipedia, Wikidata](https://en.wikipedia.org/wiki/Wikidata)).
Checked 2026-09-20, the project's own statistics page reports **123,419,629 items**,
**2,547,303,553 edits since launch** and **43,497 active users**
([Wikidata:Statistics](https://www.wikidata.org/wiki/Wikidata:Statistics)); the same page was read a
few hours earlier for [../03-construction/curation-crowdsourcing-and-quality.md](../03-construction/curation-crowdsourcing-and-quality.md),
which records 123,419,051 items — the counter is live, so quote it with the timestamp. An earlier
draft of this note gave 123,378,383 items "on 31 August 2025"; that date could not be re-verified
and has been replaced. Wikipedia cites about 1.65 billion statements in early 2025
([Wikipedia, Wikidata](https://en.wikipedia.org/wiki/Wikidata)).
In December 2014 Google announced it would discontinue Freebase in favour of Wikidata
([Wikipedia, Wikidata](https://en.wikipedia.org/wiki/Wikidata)).

**The Wikibase data model.** From the specification
([Wikibase/DataModel](https://www.mediawiki.org/wiki/Wikibase/DataModel), checked 2026-09-19):

- "Snaks are the basic information structures used to describe Entities in Wikidata. They are an
  integral part of each Statement." A snak is one of: PropertyValueSnak ("describes that an Entity
  has a certain Property with a given Value"), PropertySomeValueSnak ("has some value for a certain
  Property, without saying anything about this value"), PropertyNoValueSnak ("has no values for a
  certain Property").
- "There is always one main Snak that forms the most important part of the statement."
- "there can be zero or more additional PropertySnaks that describe the Statement in more detail.
  These qualifier Snaks (or 'qualifiers' for short) store additional information."
- "ReferenceRecords are intended to store information about some source, represented as a set of
  Snaks."
- "The ranks provide a simple selection/filtering criterion in cases where there are many Statements
  for some property."

The help pages add the user-facing definitions: "qualifiers allow statements to be expanded on,
annotated, or contextualized beyond what can be expressed in just a simple property-value pair"
([Help:Qualifiers](https://www.wikidata.org/wiki/Help:Qualifiers), page last updated 12 September 2026),
with examples such as population qualified by point in time (P585) and determination method
(P459), spouse qualified by start time (P580) and end time (P582), and position held qualified by
start/end time. A *claim* is "the core part of a statement without references and ranks"
([Help:Statements](https://www.wikidata.org/wiki/Help:Statements), last modified 5 June 2025).
Ranks: "The preferred rank is assigned to the most current statement or statements that best
represent consensus"; "The normal rank is assigned to all statements by default"; "The deprecated
rank is used for statements that are known to include errors ... or that represent outdated
knowledge"; a *best rank* statement is "a statement with preferred rank, if there is none: a
statement with normal rank" ([Help:Ranking](https://www.wikidata.org/wiki/Help:Ranking)).

**Structure as a hyperedge.** A Wikidata statement is a hyperedge whose members are the subject
item, the main value, and all qualifier values, labelled by the main property and keyed by the
qualifier properties; references and rank are metadata attached to the hyperedge. This is exactly
what the embedding literature calls a *hyper-relational fact* ([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf);
[Galkin et al., 2020](https://arxiv.org/abs/2009.10847)); see
[hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md).
The no-value and some-value snaks are explicit negative and existential knowledge, unusual in KGs;
see [open-world-vs-closed-world-and-uncertainty.md](open-world-vs-closed-world-and-uncertainty.md).

**RDF mapping.** The Wikibase RDF dump format exposes both views
([Wikibase RDF Dump Format](https://www.mediawiki.org/wiki/Wikibase/Indexing/RDF_Dump_Format), checked 2026-09-19):

| Layer | Prefix / predicate | Meaning |
|---|---|---|
| truthy | `wdt:Pnn` | subject → simple value, only for best-rank non-deprecated statements; qualifiers dropped |
| statement node | `p:Pnn` → `wds:<statement id>` | item to statement node |
| main value | `ps:Pnn` (simple), `psv:` (value node) | statement node to main value |
| qualifiers | `pq:Pnn`, `pqv:Pnn` | statement node to qualifier value |
| references | `prov:wasDerivedFrom` → `wdref:`; `pr:`, `prv:` | statement node to reference node and its snaks |
| rank | `wikibase:rank` = `wikibase:PreferredRank` / `NormalRank` / `DeprecatedRank`; `wikibase:BestRank` type | rank |

The statement node `wds:` is the reification of the hyperedge in plain RDF 1.1, without using the
rdf:Statement vocabulary; it plays the same structural role as an RDF 1.2 reifier
([n-ary-relations-and-reification.md](n-ary-relations-and-reification.md)).

## 3. Freebase CVT vs Wikidata statement: the migration mapping

The migration paper spells out the structural mismatch: "the CVT is linked to the subject topic by one
property and has properties pointing to its component values, whereas the Wikidata statement has a
main property value group that is qualified by other such groups. In order to map a CVT to a
statement, we have to know which of the CVT's properties should be used as the main value of the
statement, with the others being mapped to qualifiers"
([Pellissier Tanon et al., 2016](https://dl.acm.org/doi/10.1145/2872427.2874809)). The example is
Barack Obama's presidency: `/politician/government_positions_held` maps to position held (P39),
office holder becomes the main value and dates become qualifiers; sources attached to CVTs map to
Wikidata references.

The comparison is the clearest real-world statement of the difference between the **n-ary tuple**
view (CVT: all fields are peers) and the **hyper-relational** view (statement: one main value, the
rest qualify it). Choosing the main value is a modelling decision that the CVT did not have to make.
The same paper also measures the cost of the CVT encoding: "to encode that Barack Obama is the
president of the United States since January 20, 2009, Freebase requires more than six facts",
and a Freebase-style encoding of Wikidata would inflate it to "110 million facts, i.e. an increase of
167% over the raw number of statements" ([Pellissier Tanon et al., 2016](https://dl.acm.org/doi/10.1145/2872427.2874809)).

## 4. How much of these KBs is genuinely n-ary?

- Freebase, **measured over entities, not facts**: "more than 1/3 of the entities participate in
  non-binary relations" ([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf));
  re-cited as "more than 30% of its entities" by
  [Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf), and restated as "in the
  original FREEBASE more than 1/3rd of the entities participate in non-binary relations ... 61% of
  the relations in the original Freebase are non-binary" by
  [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137). An entity that takes part in one n-ary
  fact among hundreds of binary ones still counts, so this number does **not** bound the share of
  n-ary *facts*; see [../10-comparative-and-critique/limitations-and-failure-modes.md](../10-comparative-and-critique/limitations-and-failure-modes.md) §1.
- Wikidata, sampled, **measured over statements**: in WD50K 32,167 of 236,507 statements
  (**13.6%**, Galkin et al., Table 1 — "about 14% of statements have at least one qualifier pair"
  in their prose)
  ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)); in WikiPeople, after removing literals,
  "less than 3% of the remaining statements contain any qualifier pairs. Out of those, about 80%
  possess only one qualifier" ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)), and HINGE
  reports "97.4% triple facts vs 2.6%" hyper-relational facts in its filtered WikiPeople
  ([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf)).
- A whole-Wikidata figure for the share of statements with qualifiers was not found in a primary
  source during this research run `[unverified]`; the `cui-ke/wikidata-qualifiers` repository provides
  tooling to compute qualifier frequencies from dumps
  ([GitHub, cui-ke/wikidata-qualifiers](https://github.com/cui-ke/wikidata-qualifiers)).

The discrepancy between "one third of entities" (Freebase) and "a few percent of statements"
(Wikidata samples) is partly an artefact of what is counted (entities vs statements), partly
because literal-valued qualifiers such as dates are removed before embedding, and partly because
WikiPeople was not filtered to favour n-ary facts ([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf)).

## Sources

- Wikipedia. *Freebase (database).* https://en.wikipedia.org/wiki/Freebase_(database)
- Bollacker, K., Evans, C., Paritosh, P., Sturge, T., Taylor, J. *Freebase: a collaboratively created graph database for structuring human knowledge.* SIGMOD 2008. https://research.google/pubs/freebase-a-collaboratively-created-graph-database-for-structuring-human-knowledge/
- Google Developers. *Freebase API: Basic Concepts* (Compound Value Types), checked 2026-09-19. https://developers.google.com/freebase/guide/basic_concepts
- Pellissier Tanon, T., Vrandečić, D., Schaffert, S., Steiner, T., Pintscher, L. *From Freebase to Wikidata: The Great Migration.* WWW 2016. https://dl.acm.org/doi/10.1145/2872427.2874809
- Noy, N., Rector, A. (eds). *Defining N-ary Relations on the Semantic Web.* W3C Working Group Note, 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. *On the Representation and Embedding of Knowledge Bases Beyond Binary Relations.* IJCAI 2016. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137
- Wikipedia. *Wikidata.* https://en.wikipedia.org/wiki/Wikidata
- Wikidata. *Wikidata:Statistics*, live counter, read 2026-09-20 (123,419,629 items; 2,547,303,553 edits; 43,497 active users). https://www.wikidata.org/wiki/Wikidata:Statistics
- Wikidata. *Wikidata:Data model.* https://www.wikidata.org/wiki/Wikidata:Data_model
- MediaWiki. *Wikibase/DataModel*, checked 2026-09-19. https://www.mediawiki.org/wiki/Wikibase/DataModel
- Wikidata. *Help:Statements*, last modified 5 June 2025. https://www.wikidata.org/wiki/Help:Statements
- Wikidata. *Help:Qualifiers*, last updated 12 September 2026. https://www.wikidata.org/wiki/Help:Qualifiers
- Wikidata. *Help:Ranking.* https://www.wikidata.org/wiki/Help:Ranking
- MediaWiki. *Wikibase/Indexing/RDF Dump Format*, checked 2026-09-19. https://www.mediawiki.org/wiki/Wikibase/Indexing/RDF_Dump_Format
- Rosso, P., Yang, D., Cudré-Mauroux, P. *Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction.* WWW 2020. https://exascale.info/assets/pdf/rosso2020www.pdf
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020. https://arxiv.org/abs/2009.10847
- GitHub. *cui-ke/wikidata-qualifiers: Models and tools for analyzing wikidata qualifiers.* https://github.com/cui-ke/wikidata-qualifiers
