---
title: Standards bodies and specifications relevant to knowledge hypergraphs
type: survey
status: draft
tags: [ecosystem, standards, W3C, RDF-1.2, SPARQL-1.2, GQL, SQL-PGQ, HIF, LDBC, PG-Schema, openCypher]
created: 2026-09-20
updated: 2026-09-24
---

# Standards bodies and specifications

Status **as of 2026-09-20**. Standards move; every row records where it was read and when.

The short version: **no standards body is standardising hypergraphs.** Two bodies are
standardising things that get used *instead of* hypergraphs — W3C (RDF 1.2, statement
annotation) and ISO/IEC JTC 1/SC 32 (GQL and SQL/PGQ, property graphs) — and one small
community group is standardising an interchange file format (HIF). The n-ary
knowledge-representation problem is being solved, in every standards track, by *reification*
rather than by first-class n-ary edges. See
[../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md).

---

## 1. W3C — RDF 1.2 and SPARQL 1.2

The group is chartered as the **RDF & SPARQL Working Group** (its short name and URL are still
`rdf-star`). **Chartered until 30 April 2027**
(<https://www.w3.org/groups/wg/rdf-star/>, checked 2026-09-20). Its remit: "update and maintain
the set of RDF and SPARQL related recommendations, extending them with the ability to concisely
represent and query statements about statements."

Publication status from the group's own publications page
(<https://www.w3.org/groups/wg/rdf-star/publications/>, checked 2026-09-20):

| Specification | Maturity | Latest version |
|---|---|---|
| RDF 1.2 Concepts and Abstract Data Model | **Candidate Recommendation Snapshot** | 2026-04-07 |
| RDF 1.2 Semantics | **Candidate Recommendation Snapshot** | 2026-04-07 |
| RDF 1.2 TriG | Working Draft | 2026-09-15 |
| RDF 1.2 Turtle | Working Draft | 2026-09-14 |
| RDF 1.2 XML Syntax | Working Draft | 2026-09-14 |
| SPARQL 1.2 Query Language | Working Draft | 2026-09-13 |
| SPARQL 1.2 Query Results JSON Format | Working Draft | 2026-08-13 |
| RDF 1.2 N-Quads | Working Draft | 2026-07-23 |
| RDF 1.2 N-Triples | Working Draft | 2026-07-23 |
| SPARQL 1.2 Protocol | Working Draft | 2026-07-23 |
| SPARQL 1.2 Query Results CSV and TSV Formats | Working Draft | 2026-07-23 |
| SPARQL 1.2 Update | Working Draft | 2026-06-12 |
| SPARQL 1.2 Federated Query | Working Draft | 2026-04-23 |
| SPARQL 1.2 Service Description | Working Draft | 2026-04-23 |
| SPARQL 1.2 Entailment Regimes | Working Draft | 2026-04-09 |
| RDF 1.2 Schema | Working Draft | 2026-03-28 |
| SPARQL 1.2 Query Results XML Format | Working Draft | 2024-12-27 |
| SPARQL 1.2 Graph Store Protocol | Working Draft | 2024-12-19 |
| RDF 1.2 Primer | Draft Note | 2026-09-17 |
| RDF 1.2 Interoperability | Draft Note | 2026-07-23 |
| What's New in RDF 1.2 | Draft Note | 2026-07-14 |
| What's New in SPARQL 1.2 | Draft Note | 2026-07-14 |

**Reading of the status.** The two *data-model* documents reached Candidate Recommendation in
April 2026; every *syntax* and every *SPARQL* document is still a Working Draft, several revised
within the last two weeks. The model is settling; the syntaxes and the query language are not.
Anyone building on RDF 1.2 triple terms today is building on a moving target for at least
another year.

**What RDF 1.2 does and does not give a knowledge hypergraph.** It gives a compact way to say
something *about a triple* (a triple term / annotation). It does **not** give an n-ary edge: a
4-ary fact still has to be decomposed into a base triple plus qualifiers, which is exactly the
hyper-relational model of WD50K, not the knowledge-hypergraph model of FB-AUTO. See
[../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md)
and [../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md](../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md).

**Implementation reality check (verified 2026-09-20).** In a clean virtualenv, `rdflib==7.6.0`
cannot parse RDF-star/RDF 1.2 triple terms in any syntax (`turtle-star` is not a registered
plugin; `<< … >>` and `{| … |}` both raise `BadSyntax`). Jena, RDF4J and Oxigraph do support
RDF-star. Details in [software-libraries.md](software-libraries.md).

---

## 2. ISO/IEC JTC 1/SC 32 — GQL and SQL/PGQ

| Standard | Title | Published | Notes |
|---|---|---|---|
| **ISO/IEC 39075:2024** | Information technology — Database languages — **GQL** | **2024-04-12** | the first new ISO database language since SQL; a Technical Corrigendum 1 is listed with a 2025-12-15 stage date |
| **ISO/IEC 9075-16:2023** | Information technology — Database languages SQL — Part 16: **SQL Property Graph Queries (SQL/PGQ)** | 2023 | graph pattern matching over relational tables |

Source for the numbers and dates: the ISO catalogue entry for GQL returned **HTTP 403** to an
automated fetch on 2026-09-20, so these were read from the Wikipedia article *Graph Query
Language* (<https://en.wikipedia.org/wiki/Graph_Query_Language>, checked 2026-09-20), which
cites the ISO pages directly. Treat the exact corrigendum date as `[unverified]`.

**Both standards are property-graph standards.** A property graph edge connects exactly two
nodes. Neither GQL nor SQL/PGQ has a hyperedge or an n-ary relationship construct. An n-ary fact
in GQL must be modelled as a node with edges to its participants — reification again. This is
the central point of
[../10-comparative-and-critique/property-graph-vs-typedb-vs-rdf-star.md](../10-comparative-and-critique/property-graph-vs-typedb-vs-rdf-star.md).

---

## 3. openCypher

<https://opencypher.org/>, checked 2026-09-20. "An open source specification of Cypher", driven
by Neo4j, now explicitly positioned as a migration path: "the purpose of openCypher is to pave
the road to GQL for openCypher implementers", with oversight moving to ISO/IEC JTC1 SC32 WG3.
The site references "openCypher 9" but does not state a current specification version or date
on the landing page.

**There is no mention of hyperedges or n-ary relationships anywhere on the openCypher landing
page** (checked 2026-09-20). `[unverified]` Whether any openCypher Improvement Proposal (CIP)
has ever proposed hyperedges was not established in this run; the CIP archive was not searched.
This is a specific, answerable question for a future research run.

---

## 4. HIF — the Hypergraph Interchange Format

The only interchange standard that treats a hyperedge as primitive.

**Structure** (from the [HIF-standard README](https://github.com/HIF-org/HIF-standard), checked
2026-09-20). A HIF file is a JSON object with:

- `"network-type"` (optional): `"asc"`, `"directed"` or `"undirected"`;
- `"metadata"` (optional): network-level attributes;
- `"incidences"` (**required**): records with `"node"`, `"edge"` (both required) and optional
  `"weight"`, `"direction"` (`"head"`/`"tail"`) and `"attrs"`;
- `"nodes"` (optional) and `"edges"` (optional): records with the id plus optional `"attrs"`,
  allowing isolated nodes and empty edges.

**Governance and versioning.** Published as
[Coll et al., *Network Science* 13, e21 (2025)](https://doi.org/10.1017/nws.2025.10018);
archived on Zenodo ([10.5281/zenodo.15802759](https://doi.org/10.5281/zenodo.15802759));
maintained by pull request at [HIF-org/HIF-standard](https://github.com/HIF-org/HIF-standard)
(MIT, 36 stars, last commit 2026-03-19). The schema `CHANGELOG.md` lists exactly one entry,
**v0.0**, "Initial schema for the Hypergraph Interchange Format (HIF) standard". The other version
labels disagree with it: the versioned schema file says `0.1.0`, `CITATION.cff` says `0.1.0`, the
Zenodo releases are v0.1.0, v0.1.1 and v0.1.2 (2025-07-04 to 2025-10-03), and the maintainers call
the current state "v1" and are planning a "v2" for temporal hypergraphs and a columnar format
(issue [#55](https://github.com/HIF-org/HIF-standard/issues/55); all checked 2026-09-23 by P2,
[report 02 §4](../../projects/p2-role-aware-hif/research/02-hif-standard.md)).

**The schema URLs, corrected 2026-09-24.** The 2026-09-20 reading of this section counted three
schema URLs plus a fourth, 404, `$id` as competing identities. P2's full clone of the repository
showed that they are one repository under three names and two files with identical rules
([report 02 §2.1, §4.4](../../projects/p2-role-aware-hif/research/02-hif-standard.md)):

| URL | HTTP (2026-09-23) | What it is |
|---|---|---|
| `https://raw.githubusercontent.com/HIF-org/HIF-standard/main/schemas/hif_schema.json` | 200 | the moving `latest` file under the current name |
| `https://raw.githubusercontent.com/pszufe/HIF-standard/main/schemas/hif_schema.json` | 200, same bytes | the same file through GitHub's rename and transfer redirect; used by the README's validator snippets and this repository's [../../schemas/sample.hif.json](../../schemas/sample.hif.json) |
| `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json` | 200 | the *versioned* file (`"version": "0.1.0"`) under the repository's original name; fetched at run time by `hypernetx.hif.schema_url` in HyperNetX 2.4.3 |
| `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/schema.json` | 404 | the `$id` of `hif_schema.json`: a path that existed for about 21 minutes on 2025-05-02, before a rename; the other file's `$id` was corrected and this one was not |

`hif_schema.json` and `hif_schema_v0.1.0.json` differ only in `$id` and `version`, and their
validation rules have not changed since 2024-10-03. The `version` value is an annotation, not a
JSON Schema keyword, so it describes the schema document and has no effect on validation.

**Analysis.** The format itself is sound and genuinely cross-library, and its current rules are
stable. The identity problem is narrower than it first looked, but real. `hif_schema.json` is by
design the moving `latest` file, so every tool that fetches it will change rules silently when v2
ships. The old names resolve only through GitHub redirects. And a data file cannot say which
version it follows: a top-level `version` key fails validation, so under the current rules a
declaration can live only in `metadata`. Until upstream adds a data-file version marker (a v2
ask in P2's drafted proposal), a pipeline should vendor `hif_schema_v0.1.0.json`, pin it by commit
URL and sha256, and validate offline, which is what P2's package does. Full discussion in
[../04-storage-and-formats/hif-hypergraph-interchange-format.md](../04-storage-and-formats/hif-hypergraph-interchange-format.md) §0, §3 and §4.

**What HIF does not model.** No relation type, no role, no schema or type system, no provenance
model. Roles can only live in `incidences[].attrs` by convention — the convention this repository
uses in [../../schemas/sample.hif.json](../../schemas/sample.hif.json). The paper's own example of
an incidence attribute is a role, `{"role": "PI"}`, but no library interprets roles: XGI 0.10.2
drops them on read and HyperNetX 2.4.3 keeps them as opaque cell properties
([software-libraries.md](software-libraries.md) §1). Project P2 has defined `role-convention`
1.0.0, a v1-compatible convention (role in `attrs.role`, one incidence record per role binding,
a `metadata` declaration), with loaders that keep roles through both libraries; the upstream
proposal is drafted and not yet filed
([../04-storage-and-formats/hif-hypergraph-interchange-format.md](../04-storage-and-formats/hif-hypergraph-interchange-format.md) §10;
[projects/p2-role-aware-hif/](../../projects/p2-role-aware-hif/)).

---

## 5. Graph Data Council (formerly LDBC)

<https://ldbcouncil.org/>, checked 2026-09-20. The Linked Data Benchmark Council has operated
"under the name **Graph Data Council (GDC)**" since **2025**. It defines graph database
benchmarks and participates in graph query language standardisation (GQL, SQL/PGQ, RDF/SPARQL),
and runs a **LEX (Extended GQL Schema) Working Group** on schema standards.

Benchmarks listed: **Social Network Benchmark (SNB)** (Interactive and Business Intelligence
workloads), **Financial Benchmark (FinBench)**, **Graphalytics**, **Semantic Publishing
Benchmark (SPB)**.

**n-ary coverage: none.** All the GDC benchmarks are property-graph or RDF-triple workloads. No
benchmark in the suite models hyperedges or n-ary relationships, and the benchmark pages checked
here state no version numbers or release dates `[unverified]`.

**Analysis.** This is the clearest single indicator of where the database industry's attention
is. If n-ary data mattered commercially, a benchmark for it would exist. Conversely, a credible
n-ary benchmark is a thing the research community could contribute to GDC.

---

## 6. PG-Schema

[Angles, Bonifati, Dumbrava, Fletcher, Green, Hidders, Li, Libkin, Marsault, Martens, Murlak,
Plantikow, Savković, Schmidt, Sequeda, Staworko, Tomaszuk, Voigt, Vrgoč, Wu,
Živković (2023). *PG-Schema: Schemas for Property Graphs.* Proc. ACM Manag. Data,
10.1145/3589778](https://doi.org/10.1145/3589778); preprint arXiv:2211.10962.

Defines PG-Types (flexible type definitions with multiple inheritance) and PG-Keys-style
constraints for property graphs. It is the schema-language input to the GQL standardisation
effort. **It does not address n-ary relationships or hyperedges** (checked against the
paper's abstract and metadata, 2026-09-20).

---

## 7. Summary: what a knowledge hypergraph has to borrow

| Need | Standard that covers it | Standard that does not |
|---|---|---|
| serialise a hypergraph between tools | **HIF** (schema 0.1.0, labelled v0.0 in its CHANGELOG; JSON Schema) | RDF, GQL, SQL/PGQ |
| say something *about* a fact | **RDF 1.2** triple terms (CR Snapshot, 2026-04-07) | GQL, SQL/PGQ |
| n-ary fact with named roles as a primitive | **none** — TypeQL is a vendor language, not a standard | RDF 1.2, GQL, SQL/PGQ, openCypher, PG-Schema |
| schema / type system over n-ary facts | **none** | HIF (no types at all), PG-Schema (binary only) |
| a benchmark with n-ary workloads | **none** | GDC/LDBC suite |

Three of the five rows read "none". That is the honest state of standardisation for knowledge
hypergraphs in 2026, and it is why so much of the field ships bespoke JSON. Related timeline in
[../08-history-and-frontier/standards-convergence.md](../08-history-and-frontier/standards-convergence.md).

---

## Sources

- W3C RDF & SPARQL Working Group (short name `rdf-star`). Group page and publications list. <https://www.w3.org/groups/wg/rdf-star/>, <https://www.w3.org/groups/wg/rdf-star/publications/>, both checked 2026-09-20.
- *Graph Query Language* (Wikipedia), used as a secondary source for ISO/IEC 39075:2024 (published 2024-04-12) and ISO/IEC 9075-16:2023, because <https://www.iso.org/standard/76120.html> returned HTTP 403 to an automated fetch. <https://en.wikipedia.org/wiki/Graph_Query_Language>, checked 2026-09-20.
- openCypher. <https://opencypher.org/>, checked 2026-09-20.
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. (2025). *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21. <https://doi.org/10.1017/nws.2025.10018>
- HIF-standard repository: README, `schemas/hif_schema.json`, `schemas/CHANGELOG.md`, Zenodo DOI badge. <https://github.com/HIF-org/HIF-standard>, checked 2026-09-20. Schema URL resolution (three HTTP 200s, one 404 for the `$id`) tested with `curl` on 2026-09-20.
- HyperNetX 2.4.3, `hypernetx.hif.schema_url`, inspected in a local virtualenv on 2026-09-20.
- HIF-standard issue #55 (v1/v2 wording, 2025-12-09). <https://github.com/HIF-org/HIF-standard/issues/55> (read 2026-09-23)
- HIF Zenodo releases v0.1.0 <https://doi.org/10.5281/zenodo.15802760>, v0.1.1 <https://doi.org/10.5281/zenodo.17251025>, v0.1.2 <https://doi.org/10.5281/zenodo.17257719> (version list checked through the Zenodo API 2026-09-24)
- P2 research report 02, *What the HIF standard says today, from primary sources* (this repository, 2026-09-23): full clone of the HIF repository, schema history, URL status. [projects/p2-role-aware-hif/research/02-hif-standard.md](../../projects/p2-role-aware-hif/research/02-hif-standard.md)
- Graph Data Council (formerly Linked Data Benchmark Council). <https://ldbcouncil.org/> and <https://ldbcouncil.org/benchmarks/>, checked 2026-09-20.
- Angles, R., Bonifati, A., Dumbrava, S. et al. (2023). *PG-Schema: Schemas for Property Graphs.* Proc. ACM Manag. Data 1(2). <https://doi.org/10.1145/3589778>; preprint <https://arxiv.org/abs/2211.10962>, checked 2026-09-20.
