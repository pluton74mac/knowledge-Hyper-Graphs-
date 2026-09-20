---
title: RDF-star, RDF 1.2 and the semantic-web serialisations for n-ary facts
type: survey
status: draft
tags: [rdf, rdf-star, rdf-1.2, turtle, trig, json-ld, sparql, triple-store, reification, provenance]
created: 2026-09-20
updated: 2026-09-20
---

# RDF-star, RDF 1.2 and the semantic-web serialisations

The semantic-web stack has no hyperedge. Everything it does with an n-ary fact is a way of naming a
statement and hanging the extra arguments off that name. This note is about the *file syntax* and
*store support* for doing that; the modelling argument is in
[../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md).

Everything below was checked on 2026-09-20.

## 1. Where the standard is right now

| Document | Status | Date |
|---|---|---|
| RDF 1.2 Concepts and Abstract Syntax | W3C Candidate Recommendation Snapshot | 7 April 2026 |
| RDF 1.2 Semantics | W3C Candidate Recommendation Snapshot | 7 April 2026 |
| RDF 1.2 Turtle | W3C Working Draft | 14 September 2026 |
| RDF 1.2 N-Triples | W3C Working Draft | 23 July 2026 |
| SPARQL 1.2 Query Language | W3C Working Draft | 13 September 2026 |

Only the two *data-model* documents (Concepts, Semantics) are at Candidate Recommendation Snapshot;
**all** syntaxes and the whole SPARQL 1.2 suite are still Working Drafts as of September 2026. The
RDF & SPARQL Working Group (URL short name still `rdf-star`) is **chartered until 30 April 2027**.
Full publication table in
[../09-ecosystem/standards-bodies-and-specifications.md](../09-ecosystem/standards-bodies-and-specifications.md).

RDF 1.2 Concepts states the core addition plainly: RDF 1.2 provides "the ability to use an RDF
triple as a triple term, in the object position of another triple"
([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)). A triple whose predicate is
`rdf:reifies` and whose object is a triple term is a *reifying triple*; its subject is a
**reifier**. "A reifier may denote a variety of things that are related to the triple term's
proposition, such as a statement or belief that the proposition holds" (same document).

Apache Jena's release notes are the clearest statement of what changed relative to the 2021 RDF-star
Community Group work: "There is a Model API class `StatementTerm` for RDF 1.2 triple terms. This
change reflects the W3C Working Groups decision. It is only permitted in the only in the object
position. Unlike the work of the RDF-star CG, triple terms are not valid in the subject position"
([Jena 5.5.0 release notes, 18 July 2025](https://github.com/apache/jena/blob/main/CHANGES.txt)).

**This is a breaking change for data.** Files written for the 2021 CG syntax put `<< s p o >>` in
subject position. RDF 1.2 keeps `<< >>` only as shorthand for *reified triple* (a reifier plus an
`rdf:reifies` triple), and spells the bare triple term `<<( s p o )>>`, object position only. Any
KHG stored in CG-style RDF-star before ~2025 needs a migration.

## 2. Four ways to write the same n-ary fact

The worked file is [`schemas/sample-n-ary-fact.ttl`](../../schemas/sample-n-ary-fact.ttl); it parses
cleanly with pyoxigraph 0.5.11 (32 quads, verified 2026-09-20). The fact: *metformin treats type-2
diabetes, at 500 mg twice daily, in adults, per a 2024 guideline, confidence 0.95.*

### 2a. RDF 1.1 reification (1999/2004 vocabulary)

```turtle
:f1 a rdf:Statement ;
    rdf:subject :metformin ; rdf:predicate :treats ; rdf:object :T2DM ;
    :dosage :dose-500mg-bid ; :population :adults ; :confidence 0.95 .
:metformin :treats :T2DM .    # must be asserted separately
```

Four triples of overhead per statement, and no formal link to the asserted triple — the RDF 1.1
semantics says a reification "does not entail the triple, and is not entailed by it"
([RDF 1.1 Semantics](https://www.w3.org/TR/rdf11-mt/)). Universally supported; universally disliked.

### 2b. RDF 1.2 annotation syntax (asserts the core triple *and* qualifies it)

```turtle
:metformin :treats :T2DM ~ :f1 {|
    :dosage :dose-500mg-bid ;
    :population :adults ;
    :confidence 0.95 ;
    prov:wasDerivedFrom :guideline-2024
|} .
```

`~ :f1` names the reifier; `{| ... |}` attaches properties to it. The core triple *is* asserted.
This is the form to use when the binary core is true and the other arguments are qualifiers — i.e.
the Wikidata statement shape (see
[../02-knowledge-representation/wikidata-and-freebase-data-models.md](../02-knowledge-representation/wikidata-and-freebase-data-models.md)).

### 2c. RDF 1.2 explicit reifier + triple term (does *not* assert the core triple)

```turtle
:claim-7 rdf:reifies <<( :metformin :treats :T1DM )>> ;
         :assertedBy :forum-post-123 ;
         :status     :disputed .
```

Use for claims you record without endorsing: contradicted facts, extraction candidates, beliefs
attributed to a source. This is the capability plain reification was supposed to give and never did
cleanly. For an LLM-built KHG where every fact carries an extraction confidence, this is the honest
encoding — compare [../03-construction/llm-based-khg-construction.md](../03-construction/llm-based-khg-construction.md).

### 2d. The relation-instance pattern (no reification at all)

```turtle
:fact-1 a :TreatmentFact ;
    :treatment :metformin ; :condition :T2DM ;
    :dosage :dose-500mg-bid ; :population :adults ; :confidence 0.95 ;
    prov:wasDerivedFrom :guideline-2024 .
```

Pattern 1 of the W3C n-ary relations note. No distinguished participant, every argument is a named
role, works in plain RDF 1.1 with no new syntax and no store upgrade. **This is the encoding that
maps one-to-one onto a role-labelled hyperedge**: `:fact-1` is the hyperedge ID, each role property
is an incidence with a role attribute. Round-tripping HIF <-> RDF is straightforward in this shape
and lossy in the others.

### Choosing between them

| | asserts core triple | needs RDF 1.2 store | distinguished participant | round-trips to HIF |
|---|---|---|---|---|
| 2a reification | no (assert separately) | no | yes (s/p/o) | awkward |
| 2b annotation | yes | yes | yes | lossy (core pair is privileged) |
| 2c reifier + triple term | no | yes | yes | lossy |
| 2d relation instance | n/a | no | **no** | **direct** |

## 3. Named graphs and TriG

An RDF dataset is "exactly one default graph ... zero or more named graphs", each named graph "a
pair consisting of an IRI or a blank node (the graph name), and an RDF graph"
([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)). TriG is the Turtle-family
serialisation of a dataset.

Named graphs attach context to a *set* of triples. One fact per graph gives per-fact provenance at
the cost of an explosion in graph count; this is the nanopublication design, treated in
[versioning-provenance-and-scale.md](versioning-provenance-and-scale.md).

## 4. JSON-LD for n-ary facts

JSON-LD 1.1 is a W3C Recommendation of 16 July 2020 — the only fully-Recommended member of this
family. It has **no** triple-term syntax, so the only available encoding is the relation instance
(2d). That is a feature: a JSON-LD n-ary fact is an ordinary nested JSON object.

```json
{
  "@context": {
    "@vocab": "http://example.org/khg/",
    "prov": "http://www.w3.org/ns/prov#",
    "treatment": {"@type": "@id"}, "condition": {"@type": "@id"},
    "dosage": {"@type": "@id"}, "population": {"@type": "@id"},
    "prov:wasDerivedFrom": {"@type": "@id"}
  },
  "@id": "fact-1",
  "@type": "TreatmentFact",
  "treatment": "metformin",
  "condition": "T2DM",
  "dosage": "dose-500mg-bid",
  "population": "adults",
  "confidence": 0.95,
  "prov:wasDerivedFrom": "guideline-2024"
}
```

Each key is a role; the object is the hyperedge. `@context` turns it into RDF without the producer
writing any RDF. For LLM pipelines this matters: a model emitting JSON with a fixed context is
emitting RDF, and the context can be validated separately from the payload.

Caveat: JSON-LD has no way to say "these four keys together are one fact of arity 4" beyond the
`@type`. Cardinality and role constraints need SHACL or a TypeDB-style schema on top.

## 5. SPARQL 1.2

The Working Draft of 13 September 2026 adds functions over triple terms — `TRIPLE()`, `SUBJECT()`,
`PREDICATE()`, `OBJECT()`, `isTRIPLE()` — and a `VERSION` declaration so a query can state which
syntax it needs, with labels `"1.2"`, `"1.2-basic"` (without triple terms) and `"1.1"`
([SPARQL 1.2 Query](https://www.w3.org/TR/sparql12-query/)). The documented pattern is:

```sparql
SELECT ?s ?date {
  ?s ?p ?o .
  BIND( <<( ?s ?p ?o )>> AS ?tt )
  :myreifier rdf:reifies ?tt .
}
```

Note what is *not* there: no aggregate over the members of a hyperedge, no arity predicate, no
"give me all facts in which X plays role R" without knowing R. Querying a KHG in SPARQL means
querying the encoding, not the hypergraph — the cost side of this is in
[property-graph-emulation-patterns.md](property-graph-emulation-patterns.md).

## 6. Triple-store support

| Store | RDF-star / RDF 1.2 support | Syntax accepted | Evidence, checked 2026-09-20 |
|---|---|---|---|
| **Apache Jena** | The most complete. 5.4.0 (2025-04-27) shipped an experimental RDF 1.2 preview: "Triple terms and rdf:reifies", Turtle/TriG/N-Triples/N-Quads/SPARQL parsing, no RDF/XML, no pretty-printing. 5.5.0 (2025-07-18) added the `StatementTerm` Model API. 6.1.0 (2026-05-11): "This version of Jena has support for RDF 1.2 syntax, input and output. RDF/XML support has recently been added to complete the RDF 1.2 formats. SPARQL 1.2 query, update and result set formats are up-to-date" | RDF 1.2 (`<<( )>>`, `~`, `{| |}`, `rdf:reifies`); triple terms object-position only | [jena CHANGES.txt](https://github.com/apache/jena/blob/main/CHANGES.txt) |
| **Oxigraph / pyoxigraph** | SPARQL 1.2 `VERSION` declaration in 0.5.3 (2025-12-19); RDF/XML 1.2 draft behind the `rdf-12` cargo feature in 0.5.4 (2026-01-24) covering "directional language strings and triple terms"; JSON-LD 1.1 enabled by default from 0.5.5 (2026-02-14) | RDF 1.2 Turtle with reifiers and annotation blocks parses in pyoxigraph 0.5.11 (verified here on the sample file) | [Oxigraph CHANGELOG](https://github.com/oxigraph/oxigraph/blob/main/CHANGELOG.md); pyoxigraph 0.5.11 released 2026-09-02 |
| **Ontotext GraphDB** | RDF-star and SPARQL-star supported since the 10.x line and documented through 11.5. The documentation describes embedding a triple "by enclosing the referenced triple using the strings `<<` and `>>`", implemented as "a new additional RDF type next to IRI, blank node, and literal", with star variants of the RDF and result formats each having "its own MIME type and file extension" | 2021 CG-style quoted triples. Whether 11.x also implements RDF 1.2 `rdf:reifies` / `<<( )>>` is **[unverified]** — the documentation page returned an interstitial to direct fetch on 2026-09-20 | [GraphDB 11.5 RDF-star docs](https://graphdb.ontotext.com/documentation/11.5/rdf-sparql-star.html) |
| **Stardog** | "Stardog 7.1+ supports extensions to the RDF data model and SPARQL query engine to store and query properties of RDF statements". Two notations: `<< :Pete a :Engineer >> :since 2010 .` and `:Pete a { :since 2010 } :Engineer`. Restrictions: "Only subjects of RDF triples can be triples"; "Nested edge properties are not allowed"; edge properties must sit in the same graph as the edge. Serialisations: Turtle, TriG, binary RDF, JSON-LD. The documentation itself warns the feature "has several known performance problems and is not recommended for new Knowledge Graph projects" | CG-style, subject position only, no nesting | [Stardog edge properties](https://docs.stardog.com/query-stardog/edge-properties) |
| **Eclipse RDF4J** | Supports RDF-star; GraphDB 11 is built on RDF4J 5.x | exact version that introduced it and its RDF 1.2 status: **[unverified]** | [RDF4J](https://rdf4j.org/) |
| **QLever** | No RDF-star / RDF 1.2 support found. The compliance page states only that "Each commit ... triggers an automatic conformance test against the W3C's SPARQL 1.1 test suite"; neither SPARQL 1.2 nor triple terms are mentioned | — | [QLever compliance docs](https://docs.qlever.dev/compliance/) |
| **Blazegraph** | Historic: "Reification Done Right" (RDR) and statement identifiers (SIDs) predate the CG syntax. Effectively unmaintained — last stable release 2.1.5 (19 March 2019), 2.1.6 a release candidate (3 February 2020) | pre-standard RDR | [Blazegraph RDR wiki](https://github.com/blazegraph/database/wiki/RDR) |

Reading the table: as of September 2026 exactly one open-source store (Jena) claims full RDF 1.2
input/output, one (Oxigraph) has it partly and behind a feature flag, and the two most widely
deployed commercial stores implement the *superseded* 2021 syntax with restrictions that RDF 1.2
does not have (Stardog: subject position only, no nesting; RDF 1.2: object position only, nesting
allowed). Anyone standardising a KHG on RDF-star today is choosing between two incompatible
dialects.

## 7. Practical guidance

- If the store is fixed and old, use **2d, the relation-instance pattern**. It needs no syntax
  extension, it survives every store, and it is the only shape that round-trips to a
  role-labelled hyperedge without loss.
- If you control the stack and want per-fact metadata on binary cores, use **RDF 1.2 annotation
  syntax** with Jena 6.1+ or Oxigraph, and pin the version in your data documentation.
- Do not write new data in 2021 CG `<< s p o >>` subject-position syntax.
- Keep the *canonical* store elsewhere and treat RDF as an export view if you need arity > 2 with
  roles as first-class structure; see [format-recommendations.md](format-recommendations.md).

## Sources

- W3C. *RDF 1.2 Concepts and Abstract Syntax*, Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. *RDF 1.2 Semantics*, Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-semantics/
- W3C RDF & SPARQL Working Group, group page (charter end 30 April 2027), checked 2026-09-20. https://www.w3.org/groups/wg/rdf-star/
- W3C. *RDF 1.2 Turtle*, Working Draft, 14 September 2026. https://www.w3.org/TR/rdf12-turtle/
- W3C. *RDF 1.2 N-Triples*, Working Draft, 23 July 2026. https://www.w3.org/TR/rdf12-n-triples/
- W3C. *SPARQL 1.2 Query Language*, Working Draft, 13 September 2026. https://www.w3.org/TR/sparql12-query/
- W3C. *RDF 1.1 Semantics*, Recommendation, 2014. https://www.w3.org/TR/rdf11-mt/
- W3C. *JSON-LD 1.1*, Recommendation, 16 July 2020. https://www.w3.org/TR/json-ld11/
- Noy, N. and Rector, A. (eds). *Defining N-ary Relations on the Semantic Web*, W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- Apache Jena, `CHANGES.txt` (releases 5.4.0 2025-04-27, 5.5.0 2025-07-18, 6.0.0 2026-02-04, 6.1.0 2026-05-11, 6.2.0 2026-07-31; checked 2026-09-20). https://github.com/apache/jena/blob/main/CHANGES.txt
- Oxigraph, `CHANGELOG.md` (releases 0.5.3 2025-12-19, 0.5.4 2026-01-24, 0.5.5 2026-02-14, 0.5.7 2026-04-19; checked 2026-09-20). https://github.com/oxigraph/oxigraph/blob/main/CHANGELOG.md
- pyoxigraph 0.5.11, released 2026-09-02 (PyPI metadata, checked 2026-09-20). https://pypi.org/project/pyoxigraph/
- Ontotext. *RDF-star and SPARQL-star*, GraphDB 11.5 documentation (checked 2026-09-20). https://graphdb.ontotext.com/documentation/11.5/rdf-sparql-star.html
- Stardog. *Edge Properties* documentation (checked 2026-09-20). https://docs.stardog.com/query-stardog/edge-properties
- QLever. *Compliance* documentation (checked 2026-09-20). https://docs.qlever.dev/compliance/
- Blazegraph. *RDR* wiki page and release history (checked 2026-09-20). https://github.com/blazegraph/database/wiki/RDR
- Eclipse RDF4J project site. https://rdf4j.org/
