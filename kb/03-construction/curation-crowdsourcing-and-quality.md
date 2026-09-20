---
title: Curation, crowdsourcing and quality control for knowledge hypergraphs
type: survey
status: draft
tags: [hypergraph, n-ary, construction, curation, crowdsourcing, quality, constraints, validation, provenance]
created: 2026-09-20
updated: 2026-09-20
---

# Curation, crowdsourcing and quality control

Almost every n-ary fact that researchers actually train and test on was written by a human, not extracted
by a model. JF17K, WikiPeople, WD50K and FB-AUTO are all derived from Freebase and Wikidata (see
[from knowledge graphs to hypergraphs](from-knowledge-graphs-to-hypergraphs.md)), and both of those were
built by communities of editors under an explicit data model. This note covers how that curation works,
what machinery keeps it honest, and what "quality" means for a fact with more than two participants.

It is stage 8 of the [construction pipeline](construction-pipeline-overview.md).

## 1. Three curation regimes

| Regime | Example | Who writes a fact | Who checks it |
|---|---|---|---|
| Open community | Wikidata | anyone, plus bots | constraint reports, other editors, reverts |
| Closed expert | Cyc | trained knowledge engineers | internal consistency + inference |
| Domain biocuration | Gene Ontology | curators reading papers | evidence codes + review |

### Wikidata: community curation at scale

Wikidata is a collaboratively edited knowledge base whose data model was designed for exactly the
qualified, referenced statements that a KHG needs
([Vrandečić & Krötzsch, 2014](https://doi.org/10.1145/2629489), *CACM* 57(10), 78–85). A statement "may
consist of one property … one value … optionally one or more qualifiers … optionally one or more
references" ([Wikibase DataModel Primer](https://www.mediawiki.org/wiki/Wikibase/DataModel/Primer)) — so
the n-ary structure, the provenance and the ranking are all first-class and all human-maintained.

Scale, checked 2026-09-20: the project's own statistics page reports "Wikidata currently contains
123,419,051 items", "2,547,260,794 edits have been made since the project launch", and "There are currently
43,497 active users" ([Wikidata:Statistics](https://www.wikidata.org/wiki/Wikidata:Statistics); the
page carries a live counter, so a re-read the same day gave 123,419,629 items and 2,547,303,553
edits — always quote it with the timestamp). A large
share of those edits are bot edits; bots are how large imports and systematic clean-ups happen, and they
are also a documented source of systematic error.

### Cyc: expert curation with an expressive n-ary logic

Cyc is the opposite extreme and the longest-running one: the project was described to the wider community
in [Lenat, 1995](https://doi.org/10.1145/219717.219745) (*CACM* 38(11), 33–38), and the hand-authored
knowledge base is still hand-authored. Its authors state that "Cyc's knowledge base (KB) comprises tens of
millions of hand-authored assertions, almost all of which are general 'rule of thumb' axioms", and that "it
has taken a coherent team of logicians and programmers four decades, 2000 person-years, to produce the
current Cyc KB" ([Lenat & Marcus, 2023](https://arxiv.org/abs/2308.04445)).

Two features of Cyc matter directly to knowledge hypergraphs. First, CycL "includes full first order logic
(with variables, nested quantifiers, predicates, functions, etc.), and allows statements about other
statements", so n-ary predicates and nesting are native rather than reified. Second, every assertion sits
in a *context* ("also called a Microtheory") with its own domain assumptions, and "Cyc makes each such
context a first-class term in its language" — a mechanism that a modern KHG would implement as
per-hyperedge qualifiers or named graphs. The cost is the 2000 person-years.

### Biocuration: curation with explicit evidence typing

The Gene Ontology annotation model is the best-developed answer to "how do you record *why* a curated fact
is believed". Evidence codes are grouped into six categories — experimental, phylogenetic, computational,
author statements, curatorial statements, and automatically generated annotations — with individual codes
such as IDA (inferred from direct assay), IMP (inferred from mutant phenotype), ISS (inferred from sequence
or structural similarity), TAS (traceable author statement) and IEA (inferred from electronic annotation).
The manual/automatic line is drawn explicitly: "IEA-supported annotations are not manually reviewed
(although the method itself is usually subjected to various quality assessments)"
([Gene Ontology evidence codes guide](https://geneontology.org/docs/guide-go-evidence-codes/), checked
2026-09-20). A KHG that mixes LLM-extracted and human-curated hyperedges needs exactly this: an evidence
type per hyperedge, not a single confidence number.

### Freebase: crowdsourcing with a compound-value data model

Freebase was "a collaboratively created graph database for structuring human knowledge"
([Bollacker et al., 2008](https://doi.org/10.1145/1376616.1376746), SIGMOD 2008) and introduced compound
value types (CVTs) as its reification of n-ary facts — the mechanism JF17K and FB-AUTO were later mined
from. Its migration into Wikidata is documented in
[from knowledge graphs to hypergraphs](from-knowledge-graphs-to-hypergraphs.md).

## 2. Constraint checking, and why it is the n-ary story

Wikidata's property constraints are the only widely deployed constraint system that validates *qualifier
structure*, which makes them the closest thing the field has to n-ary fact validation. Constraints are
themselves statements: they use the property `property constraint (P2302)` with a constraint-type item, and
the parameters are given as qualifiers on that statement
([Help:Property constraints portal](https://www.wikidata.org/wiki/Help:Property_constraints_portal)).

The two that are directly about arity and roles:

- **required qualifier constraint** — "Statements for this property must have all of the listed
  qualifiers."
- **allowed qualifiers constraint** — "Statements for this property should not have any qualifiers other
  than the listed ones."

Together these define, per property, a permitted and a mandatory role set — i.e. a machine-readable
*schema for the n-ary part of the fact*. Other types constrain the rest: **value-type constraint** ("Values
for this property should have a certain type"), **single-value constraint** ("Items should have no more
than one statement with this property"), **distinct-values constraint**, **one-of constraint**,
**conflicts-with constraint**, **item-requires-statement constraint**. Constraints are advisory: they are
guidance for editors and admit documented exceptions rather than blocking an edit.

The system has been formalised externally. Ferranti et al. note that "Wikidata currently represents its
property constraints through its own RDF data model, which relies on Wikidata's specific reification
mechanism based on authoritative namespaces, and – partially ambiguous – natural language definitions", and
report that "the expressivity of SHACL-Core turns out to be insufficient for expressing all Wikidata
property constraint types", presenting instead "SPARQL queries to identify violations for all 32 current
Wikidata constraint types" ([Ferranti et al., 2024](https://doi.org/10.3233/SW-243611), *Semantic Web*).
That SHACL-Core is not expressive enough for constraints on qualifier structure is a useful data point for
anyone planning to validate a KHG with off-the-shelf shape languages.

Wikidata also has a second, shape-based layer: EntitySchemas, stored as Shape Expressions in ShExC syntax
by a dedicated MediaWiki extension
([Extension:EntitySchema](https://www.mediawiki.org/wiki/Extension:EntitySchema), checked 2026-09-20), used
to "automatically check the quality of Wikidata items" and to generate "reports showing which items need
fixing" ([Wikidata:Schemas](https://www.wikidata.org/wiki/Wikidata:Schemas), checked 2026-09-20).

## 3. Quality frameworks and what they measure

The reference comparison of large open KGs defines quality along eleven dimensions grouped into four
categories — intrinsic (accuracy, trustworthiness, consistency), contextual (relevancy, completeness,
timeliness), representational (ease of understanding, interoperability) and accessibility (accessibility,
license, interlinking) — and applies them to DBpedia, Freebase, OpenCyc, Wikidata and YAGO
([Färber et al., 2018](https://doi.org/10.3233/SW-170275), *Semantic Web* 9(1), 77–129). Accuracy is split
into "the syntactic validity of RDF documents", "the syntactic validity of literals" and "the semantic
validity of triples". Two of their criteria are directly n-ary-relevant:

- **Trustworthiness on statement level** is measured by "evaluating whether provenance information is
  stored for statements in the KG" — the reason Wikidata's per-statement references matter.
- Under interoperability they count *avoiding blank nodes and RDF reification* as a positive, while
  conceding that "reification is necessary for stating additional information on statement level". This is
  the representational tension that motivates knowledge hypergraphs in the first place (see
  [n-ary relations and reification](../02-knowledge-representation/n-ary-relations-and-reification.md)).

For a live, edited KB, quality can also be estimated from editing behaviour. Shenoy et al. use three
indicators — "community consensus on the currently recorded knowledge, assuming that statements that have
been removed and not added back are implicitly agreed to be of low quality", "statements that have been
deprecated", and "constraint violations in the data" — and report that combining them reveals "challenges
with duplicate entities, missing triples, violated type rules, and taxonomic distinctions"
([Shenoy et al., 2021](https://arxiv.org/abs/2107.00156)). Note that all three require version history,
which is an argument for the versioning practices in
[incremental construction](incremental-and-streaming-construction.md).

## 4. Validating *extracted* n-ary facts

Curation of extracted facts is a different job: the volume is higher and the errors are structural.
HyperRED's human-annotation protocol is the most explicit published rubric for n-ary facts. Annotators
check the triple component and the qualifier component separately, marking a fact "Invalid Qualifier" if
"the value mentioned in the text does not clearly express the qualifier meaning or is not directly related
to the triplet", and "Correct" only if neither component is wrong; the worked examples distinguish an
invalid triplet (the text does not support the base relation) from an invalid qualifier (the right value
under the wrong role) ([Chia et al., 2022](https://arxiv.org/abs/2211.10018)). The dataset design follows
the same logic: a distantly supervised training split of 39,840 sentences, and human-annotated development
(1,000 sentences) and test (4,000 sentences) splits, because "to minimize the effect of noisy samples in
evaluation, we then perform human annotation for a portion of the collected data".

The lesson generalises: **an n-ary fact has partially-correct failure modes**, so a binary
correct/incorrect verdict throws away most of the signal. At minimum, curation of a hyperedge should record
which participants and which roles were wrong.

Machine-assisted validation is now standard in production pipelines. ODKE+ places "a lightweight Grounder
[that] validates extracted facts using a second LLM" and "the Corroborator [that] ranks and normalizes
candidate facts for ingestion" after extraction, reporting "19 million high-confidence facts with 98.8%
precision" ([Khorshidi et al., 2025](https://arxiv.org/abs/2509.04696)). Multi-agent enrichment frameworks
such as KARMA make verification an explicit agent role
([Lu et al., 2025](https://arxiv.org/abs/2502.06472)). These are LLM-judging-LLM arrangements and inherit
the biases discussed in [evaluation](evaluation-of-constructed-khgs.md) §5; they raise precision and should
not be read as measurements of it.

## 5. Quality metrics for n-ary facts: a proposal

No published metric suite targets hyperedge quality specifically. The following is a synthesis (opinion),
assembled from the mechanisms above, that a KHG project can compute today:

1. **Provenance coverage** — fraction of hyperedges with at least one `source_id` / reference. Directly
   from Färber's statement-level trustworthiness.
2. **Role completeness** — fraction of hyperedges that carry every role their relation's signature marks
   mandatory. The Wikidata analogue of *required qualifier constraint*.
3. **Role conformance** — fraction of roles used that the signature permits (*allowed qualifiers
   constraint*).
4. **Arity distribution** — histogram of |e| per relation. A relation whose extracted arity is almost
   always 2 is evidence that the n-ary extraction failed, not that the world is binary.
5. **Duplicate-hyperedge rate** — fraction of hyperedges subsumed by another hyperedge over the same
   participants with more roles filled. Measures the merge failure described in
   [entity resolution](entity-resolution-and-canonicalisation.md) §4.
6. **Evidence-type mix** — the Gene Ontology move: what share of hyperedges are human-curated, model-
   extracted, or inferred.
7. **Constraint violation rate** — once a schema exists, the Wikidata-style report, computed per relation.

Items 2, 3, 5 and 7 have no published baseline numbers for any KHG. That is a gap worth filling.

## 6. Open problems

- **Quality metrics for hyperedges are unpublished.** Every metric above is computable but none is
  reported in the KHG literature.
- **Constraint languages do not cover qualifier structure well.** SHACL-Core is demonstrably insufficient
  for Wikidata's own constraint set ([Ferranti et al., 2024](https://doi.org/10.3233/SW-243611)); no shape
  language targets hypergraph incidence directly. `[unverified]` — I found no SHACL/ShEx profile for
  hypergraph data in this research run.
- **Crowdsourcing n-ary facts is harder than crowdsourcing triples**, and there is no study of inter-
  annotator agreement as a function of arity.
- **Bot-authored and LLM-authored facts are not distinguished from human ones** in most KHG datasets, so
  downstream evaluations silently mix evidence types.

## Sources

- Vrandečić, D., Krötzsch, M. "Wikidata: a free collaborative knowledgebase." Communications of the ACM 57(10), 78–85, 2014. https://doi.org/10.1145/2629489
- Wikimedia. "Wikibase/DataModel/Primer", checked 2026-09-20. https://www.mediawiki.org/wiki/Wikibase/DataModel/Primer
- Wikidata. "Wikidata:Statistics", checked 2026-09-20. https://www.wikidata.org/wiki/Wikidata:Statistics
- Wikidata. "Help:Property constraints portal", checked 2026-09-20. https://www.wikidata.org/wiki/Help:Property_constraints_portal
- Wikidata. "Wikidata:Schemas", checked 2026-09-20. https://www.wikidata.org/wiki/Wikidata:Schemas
- Wikimedia. "Extension:EntitySchema", checked 2026-09-20. https://www.mediawiki.org/wiki/Extension:EntitySchema
- Ferranti, N., De Souza, J. F., Ahmetaj, S., Polleres, A. "Formalizing and validating Wikidata's property constraints using SHACL and SPARQL." Semantic Web, 2024. https://doi.org/10.3233/SW-243611
- Lenat, D. B. "CYC: A Large-Scale Investment in Knowledge Infrastructure." Communications of the ACM 38(11), 33–38, 1995. https://doi.org/10.1145/219717.219745
- Lenat, D., Marcus, G. "Getting from Generative AI to Trustworthy AI: What LLMs might learn from Cyc." arXiv 2308.04445, 2023. https://arxiv.org/abs/2308.04445
- Gene Ontology Consortium. "Guide to GO evidence codes", checked 2026-09-20. https://geneontology.org/docs/guide-go-evidence-codes/
- Bollacker, K., Evans, C., Paritosh, P., Sturge, T., Taylor, J. "Freebase: a collaboratively created graph database for structuring human knowledge." SIGMOD 2008, 1247–1250. https://doi.org/10.1145/1376616.1376746
- Färber, M., Bartscherer, F., Menne, C., Rettinger, A. "Linked data quality of DBpedia, Freebase, OpenCyc, Wikidata, and YAGO." Semantic Web 9(1), 77–129, 2018. https://doi.org/10.3233/SW-170275
- Shenoy, K., Ilievski, F., Garijo, D., Schwabe, D., Szekely, P. "A Study of the Quality of Wikidata." Journal of Web Semantics, 2021 / arXiv 2107.00156. https://arxiv.org/abs/2107.00156
- Chia, Y. K., Bing, L., Aljunied, S. M., Si, L., Poria, S. "A Dataset for Hyper-Relational Extraction and a Cube-Filling Approach." EMNLP 2022 / arXiv 2211.10018. https://arxiv.org/abs/2211.10018
- Khorshidi, S., Nikfarjam, A., Shankar, S., Sang, Y., et al. "ODKE+: Ontology-Guided Open-Domain Knowledge Extraction with LLMs." arXiv 2509.04696, 2025. https://arxiv.org/abs/2509.04696
- Lu, Y., Wu, W., Zhao, X., Peng, R., Wang, J. "KARMA: Leveraging Multi-Agent LLMs for Automated Knowledge Graph Enrichment." NeurIPS 2025 / arXiv 2502.06472. https://arxiv.org/abs/2502.06472
