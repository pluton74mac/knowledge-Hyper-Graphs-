---
title: "P6 research 02: data sources and role naming (Wikidata qualifier schemas, Biolink Model)"
type: survey
status: draft
tags: [p6, schema, acyclicity, gyo, wikidata, qualifiers, property-constraints, biolink, linkml, role-naming, p3a]
created: 2026-09-24
updated: 2026-09-24
---

# P6 research 02: data sources and role naming

This report gathers the data P6 needs and measures how the choice of role names changes the schema hypergraph
(vertices are roles, hyperedges are relations; P2 [DESIGN §3](../../p2-role-aware-hif/DESIGN.md)). It covers
Wikidata's qualifier schemas, the Biolink Model, and a fallback biomedical schema. It ends with a role-naming rule
that P3a and P6 should share (§5, written to be sent to P3a verbatim).

Evidence tags: **[run]** measured by a probe in [probes/](probes/) on 2026-09-24; **[read]** read in the cited
source on 2026-09-24; **[derived]** reasoning from the above; **[unverified]** not checked.

## Findings in brief

1. **Few properties declare a qualifier schema, but they are the heavily used ones.** Wikidata has 13,928
   properties. 1,168 carry a non-deprecated *allowed qualifiers* constraint; 1,155 remain after removing 57
   properties that document or constrain other properties. They hold 1.27 of the 1.79 billion main statements
   (71 %), and 56 of the 100 most used properties have one [run].
2. **The most widely allowed qualifiers are statement metadata.** The most shared are `reason for deprecated rank`
   (P2241, on 719 lists), `reason for preferred rank` (P7452, 614) and `subject named as` (P1810, 541). Only then
   come start time (P580, 396), end time (P582, 362), applies to part (P518, 305) and point in time (P585, 303)
   [run]. §2.3 gives a rule and a 27-property list for the `meta` slot.
3. **The declared lists are generous. What is actually used is a small subset of them.** `position held` (P39)
   allows 104 qualifiers. The 2026-08-10 dump shows 328 distinct qualifiers on it. Only 34 pass a noise threshold,
   and all 34 are allowed. Across the five sampled properties, 0.005 % to 0.53 % of qualifier uses fall outside the
   allowed list [run]. The survey should report both schemas: the declared one and the observed one (§2.5).
4. **Every naming with global roles gives an α-cyclic schema.** This holds on all three tables (declared,
   observed-robust, observed-all), with or without metadata and time. Only relation-local roles give an α-acyclic
   schema, and they do so trivially [run]. So the survey's informative number will be the width, not the
   acyclicity class.
5. **Generic `subject`/`value` hubs do not change the result.** They change neither the class nor the GYO residue.
   Property-local main roles leave exactly the same residue hyperedges; the generic naming only adds the two hub
   vertices to them [run]. A vertex that lies in every hyperedge, or in only one, cannot change α-acyclicity or any
   hypertree-width measure [derived, §3.4]. The hubs change only descriptive statistics, such as 1 connected
   component instead of 154.
6. **The main-value role and typing are what change the cyclic core.**
   - Naming the main-value role after its property (`P39`) joins a property's main use to its uses as a qualifier.
     This enlarges the GYO residue by 15 % to 44 % [run].
   - Typing the main roles by constraint classes enlarges it by 25 % to 83 %, and depends on constraints that 35 %
     of properties lack [run].
7. **Recommended naming for P3a and P6 (§3.5, §5).** The subject role is `subject`. The main value's role is the
   property id. Each qualifier's role is its property id. Slot classes follow P2: `time` for P580/P582 (a
   relation that allows either gets the interval model), `meta` for the 27 listed properties, `qualifier`
   otherwise. Under this naming the declared schema has 1,155 relations and 1,884 core-and-qualifier roles. It is
   α-cyclic, with a GYO residue of 401 hyperedges on 618 vertices. The generated schema file passes
   `khg_contracts.schema.check_schema` with 0 findings [run].
8. **Biolink Model v4.4.5 is a usable n-ary biomedical schema.**
   - It has 107 association classes (103 concrete) and 44 qualifier slots, of which 33 are used [run].
   - Under Biolink's own global slot names it is α-cyclic with a small cyclic core: 5 residue hyperedges, drawn
     from the chemical–gene, gene–disease, expression and coexpression families [run].
   - Typing `subject`/`object` by range raises the residue to 53 hyperedges [run].
9. **The fallback, GO-CAM, is weaker.** It is n-ary but has one central relation class, and its schema is
   α-acyclic by GYO in one pass [run]. Hetionet is binary (11 node types, 24 edge types) [read].
10. **The main risk to the gate is width, not data.** The cyclic cores have hundreds of hyperedges, and residue
    hyperedges reach 103 vertices. An exact hypertree width may not be computable for the Wikidata tables, so the
    checker should be ready to report bounds (§6).

---

## 1. What was fetched

Everything below is under `datasets/knowledge-bases/`. Raw files sit in `raw/`, which is gitignored. Each dataset
has a tracked `MANIFEST.json` with the source URL, the query text, the retrieval time, the byte count, the sha256
and the licence. The probes that fetched and parsed the data are in [probes/](probes/).

| Dataset directory | Content | Source and ref | Licence |
|---|---|---|---|
| `wikidata-property-schemas/` | 8 SPARQL result files. They cover every property with its datatype and English label; property `instance of` classes; the allowed-qualifiers, required-qualifier, subject-type, value-type and property-scope constraint statements with their parameters, rank and status; and Wikidata's qualifier classes. Plus per-property usage slices for 5 properties. | [WDQS](https://query.wikidata.org/) main graph, live, 2026-09-24 | CC0-1.0 ([Wikidata:Copyright](https://www.wikidata.org/wiki/Wikidata:Copyright)) |
| same | DeltaBot usage-count templates: main statements, qualifier uses and reference uses per property | [Template:Number of main statements by property](https://www.wikidata.org/wiki/Template:Number_of_main_statements_by_property) and its two siblings, revisions of 2026-09-23 (revid in the manifest) | CC0-1.0 |
| same | SQID `properties.json` and `statistics.json`, which give per-property qualifier usage (`qs`) from the dump of 2026-08-10 | [sqid.toolforge.org/data/](https://sqid.toolforge.org/data/properties.json); `Last-Modified` 2026-09-24 08:37 GMT | data derived from Wikidata (CC0-1.0); tool licence [unverified] |
| `biolink-model/` | `biolink-model.yaml`, its local import `attributes.yaml`, and `LICENSE` | [biolink/biolink-model](https://github.com/biolink/biolink-model) tag **v4.4.5**, commit `a4180f8…` (2026-09-18) | model CC0-1.0 (the file's `license:` field); repository `LICENSE` Apache-2.0; package metadata MIT |
| `gocam-schema/` | `gocam.yaml` (LinkML) | [geneontology/gocam-py](https://github.com/geneontology/gocam-py) tag v0.12.0, commit `e6f824a…` (2026-07-27) | `LICENSE` is BSD-3-Clause text naming the placeholder holder "My Name" [read]; intended licence [unverified] |

**Wikidata's query service holds only the main graph.** Since the split on 9 May 2025, scholarly articles have
been served by a separate endpoint, `query-scholarly.wikidata.org`
([WDQS graph split](https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/WDQS_graph_split)) [read].
- The constraint statements live on property entities, so this does not affect them.
- It does affect live usage counts for properties used mainly on articles, such as P50 and P2860.
- The DeltaBot and SQID counts come from full data [unverified for DeltaBot's method].

**Queries were polite.** Each ran on its own, with a descriptive User-Agent and a retry on HTTP 429 or 5xx that
honours `Retry-After`. The service was under load: several queries returned 502, 503 or 504 and were retried. Two
kinds of query could not be run at all:
- a full `GROUP BY` of qualifier usage over all P39 statements;
- a single `(property, qualifier)` count such as P166 with P585.

Both timed out (HTTP 504 and Blazegraph `TimeoutException`) [run]. §2.4 therefore uses SQID's dump-based counts
for all properties, and checks them against live slices of 20,000 statements.

---

## 2. Wikidata qualifier schemas

### 2.1 What was extracted

- **Properties.** Each property's datatype comes from `wikibase:propertyType`, and its English label is fetched
  too [run].
- **Allowed qualifiers constraint** (`Q21510851`) and its parameter `property` (`P2306`). The help page describes
  it thus: it "specifies that only a certain set of qualifiers may be used with a property"
  ([Help:Property constraints portal/Qualifiers](https://www.wikidata.org/wiki/Help:Property_constraints_portal/Qualifiers))
  [read].
  - Constraint statements with deprecated rank are dropped: 200 of the 11,979 rows [run].
  - A property with several constraint statements (4 properties) gets the union of their lists.
  - A `P2306` of *no value* means that no qualifiers are allowed. 23 properties declare only that [run].
- **Constraint status** (`P2316`). The status is recorded but not used as a filter. Among the properties with the
  constraint, 106 mark it mandatory (`Q21502408`), 35 mark it as a suggestion (`Q62026391`) and the rest give no
  status [run].
- **Required qualifier constraint** (`Q21510856`, parameter `P2306`).
  [Help:Property constraints portal/Required qualifiers](https://www.wikidata.org/wiki/Help:Property_constraints_portal/Required_qualifiers)
  is the target of the "Mandatory qualifiers" redirect [read].
- **Subject type** (`Q21503250`) and **value-type** (`Q21510865`) constraints, with their classes (`P2308`) and
  their relation (`P2309`). The relation "Must be `Q21503252`, `Q21514624`, or `Q30208840`", meaning instance of,
  subclass of, or either
  ([Help:Property constraints portal/Subject class](https://www.wikidata.org/wiki/Help:Property_constraints_portal/Subject_class))
  [read]. The value-type page is the counterpart; it returned HTTP 429 when fetched [unverified].
- **Property scope** (`Q53869507`, `P5314`): whether a property may be used as a main value, as a qualifier or as
  a reference. It is fetched for later use; this report does not use it.
- **Qualifier classes.** Wikidata itself classifies qualifiers as *restrictive* (`Q61719275`: "always restricts or
  modifies the statement, without which the statement may be inaccurate or meaningless") and *non-restrictive*
  (`Q61719274`: "does not restrict or modify the statement, but merely adds information. The removal of a
  non-restrictive qualifier leaves a valid statement"). A third class, `Q122233685`, covers qualifiers that can be
  either. There is also a class for properties that indicate a source (`Q18608359`). All were fetched with their
  `P279*` closure [read, run].
- **Usage.**
  - DeltaBot's switch templates give per property the number of main statements, of uses as a qualifier, and of
    uses in references (revisions of 2026-09-23) [run].
  - SQID's `properties.json` gives, per property, the qualifiers used on its statements with a count (`qs`) [run].
  - SQID's other count fields are not usable. P31's `s` is 76.6 billion, larger than all of Wikidata's 1.77 billion
    item statements in SQID's own `statistics.json`. Only `qs` was used [run]. Whether `qs` counts statements or
    snaks is [unverified]; the live slices in §2.4 agree with it in order of magnitude.

### 2.2 Counts

All counts are [run] as of 2026-09-24.

| Quantity | Value |
|---|---|
| Properties | 13,928 (ExternalId 10,606; WikibaseItem 1,784; Quantity 695; String 358; Url 124; other 361) |
| Excluded as relations (they document or constrain properties: instances of `Q19820110`, `Q21504947` or `Q64846109`, e.g. P1855 property example, P360 is a list of, P2302 property constraint) | 57 (13 of them have an allowed-qualifiers constraint) |
| With an allowed-qualifiers constraint (non-deprecated, after exclusion) | **1,155** (ExternalId 584, WikibaseItem 278, Quantity 129, String 54, other 110) |
| of which "no qualifiers allowed" only | 23 |
| Main statements on these properties | 1,272,951,360 of 1,789,552,674 (71 %) |
| Top 100 / top 1,000 properties by use that have the constraint | 56 / 264 |
| Allowed-list size (qualifiers per property) | mean 10.0, median 6, max 129 (P31); bins: 0: 23, 1: 115, 2–3: 217, 4–7: 304, 8–15: 289, 16–31: 141, 32–63: 56, ≥64: 10 |
| Largest lists | P31 instance of 129, P18 image 106, P39 position held 104, P106 occupation 80, P1344 participant in 80, P1476 title 79, P856 official website 74, P166 award received 73 |
| Distinct allowed qualifiers | 989 |
| Most shared allowed qualifiers | P2241 719, P7452 614, P1810 541, P580 396, P582 362, P518 305, P585 303, P3831 236, P1326 231, P1319 229, P8554 223, P8555 217, P5102 172, P1552 171, P1480 169, P407 167, P1932 159, P805 157 |
| Relations that allow P580 or P582 (so get the interval time model) | 408 (350 allow both, 46 only P580, 12 only P582) |
| Allowed lists containing at least one metadata qualifier (§2.3) | 958 of 1,155 (mean 2.7 per list) |
| With a required-qualifier constraint | 542 (most required: P585 116, P9675 90, P407 51, P580 32); 1 required qualifier is missing from its property's allowed list |
| With a subject-type constraint | 9,012; relation instance of 7,510, either 1,368, subclass of 159, and one invalid value (`Q33002955`) |
| Subject-type classes per property | 1 class: 5,059; 2: 1,683; 3: 738; ≥4: 1,532 (max 92) |
| Most common subject classes | Q5 human 2,808; Q43229 organization 744; Q16334295 group of humans 438; Q7889 video game 419; Q16521 taxon 364 |
| Item-valued properties with a value-type constraint | 1,194 of 1,784 (67 %) |
| Properties with main statements (DeltaBot), after exclusion | 13,608; 8,574 of them have at least one qualifier in SQID's dump |
| Distinct qualifiers in use: any / robust (≥ 10 uses and ≥ 0.1 % of the property's main statements) | 2,556 / 800 |
| Robust observed set size | 9,272 properties with none, 2,038 with 1, 1,337 with 2–3, 661 with 4–7, 250 with 8–15, 46 with 16–31, 4 with ≥ 32 (max 37) |
| Most shared robust qualifiers | P1810 2,036; P580 750; P585 621; P2241 606; P582 602; P518 492; P407 393; P3831 296; P1932 207; P1545 197 |

### 2.3 Statement metadata: a rule and a list

**What Wikidata says.** A qualifier is used "to further describe or refine the value of a property given in a
statement", and "a statement should still provide useful data even without a qualifier"
([Help:Qualifiers](https://www.wikidata.org/wiki/Help:Qualifiers)) [read]. Ranks are annotated with qualifiers:
"It is often useful to indicate the reason for a deprecation with a P2241 qualifier", and likewise "the reason for
a preferred rank with a P7452 qualifier" ([Help:Ranking](https://www.wikidata.org/wiki/Help:Ranking)) [read]. The
same page separates these from time qualifiers: correct historical values "should instead be annotated with the
appropriate P580/P582 qualifiers" [read].

**Wikidata's restrictive/non-restrictive split is not the metadata line.** The non-restrictive class contains
qualifiers that name participants: `object of statement has role` (P3831), `subject has role` (P2868),
`together with` (P1706) and `series ordinal` (P1545). It also contains true metadata such as P805 and P3680
[run, from `qualifier_classes`]. P2's slot classes draw the line differently
([DESIGN §2.4](../../p2-role-aware-hif/DESIGN.md)):
- `meta` holds bindings that "never change truth conditions";
- epistemic modifiers (P5102 nature of statement, P1480 sourcing circumstances) stay `qualifier`;
- P1534 end cause becomes the built-in `khg:end_cause`;
- P2241 and P7452 become the record's `rank_reason` (DESIGN §3).

**Rule (proposed).** A qualifier is statement metadata when its value describes the statement *as a record* and
not the state of affairs. That covers:
- the statement's rank or special value;
- the statement's source, cited inline;
- how the source worded the subject or the value;
- what supports, disputes or describes the statement;
- an editorial or display note;
- its lifecycle (end cause).

Removing or changing such a qualifier cannot change what the statement says about the world. Every other
qualifier is `qualifier`. The exception is P580 and P582, which are always `time`: a relation that allows (or, in an
observed schema, uses) either of them gets the interval model with both as its bounds.

**The list the survey used** (`META` in [wd_schema_survey.py](probes/wd_schema_survey.py)). Descriptions are
Wikidata's English descriptions, fetched 2026-09-24 [read].

| Category | Properties | Evidence |
|---|---|---|
| rank and special values | P2241 reason for deprecated rank; P7452 reason for preferred rank; P8327 intended subject of deprecated statement; P13589 reason for no value | Help:Ranking; P13589 is described as a "qualifier property to be used with statements having the object 'no value'" |
| wording in the source | P1810 subject named as; P14457 subject named as (monolingual text); P1932 object named as ("how the object's value was given in the source"); P4970 alternative name ("given for a subject in a database entry") | property descriptions |
| inline citation | P813 retrieved; P854 reference URL; P248 stated in; P1065 archive URL; P2960 archive date; P143 imported from Wikimedia project; P4656 Wikimedia import URL; P887 based on heuristic; P3452 inferred from; P1683 quotation; P5017 last update | [Help:Sources](https://www.wikidata.org/wiki/Help:Sources); all are instances of `Q18608359` "Wikidata property to indicate a source" [run] |
| support, dispute, reification | P3680 statement supported by; P1310 statement disputed by; P805 statement is subject of ("item that describes the relation identified in this statement") | property descriptions |
| editorial and display notes | P2916 syntax clarification; P6607 constraint clarification; P9570 scope note; P7528 statement or content of identifier is regarded as spoiler for | property descriptions |
| lifecycle | P1534 end cause | P2 DESIGN §2.4 (`khg:end_cause`) |

**Deliberately not in the list:**
- P5102 and P1480. P2 keeps them as qualifiers.
- P585 point in time, and the date-uncertainty bounds P1319, P1326, P8554, P8555 and P12506. They change what is
  asserted.
- P407 language of work or name, P577 publication date, P50 author, P304 page(s) and P958 section. Wikidata also
  lists these as source properties, but as qualifiers they usually refine the value.
- P4390 mapping relation type. It changes the mapping claim.

Anything not listed is `qualifier` by default. The list was drawn up by reviewing the union of the 120 most shared
declared qualifiers and the 120 most shared observed ones. The long tail (989 declared and 2,556 observed
qualifiers) was not reviewed one by one; a property there that is really metadata stays in `qualifier` until
someone adds it to the list.

### 2.4 Declared versus observed qualifiers

**From the dump.** SQID `qs` counts from the 2026-08-10 dump are compared with the allowed lists. "Robust" means
at least 10 uses and at least 0.1 % of the property's main statements [run].

| Property | Allowed | Observed, any | Observed, robust | Robust and allowed | Allowed, never used | Robust, not allowed | Qualifier uses outside the allowed list |
|---|---|---|---|---|---|---|---|
| P39 position held | 104 | 328 | 34 | 34 | 1 | — | 4,338 of 4,918,049 (0.09 %) |
| P69 educated at | 57 | 136 | 6 | 6 | 1 | — | 1,471 of 3,519,076 (0.04 %) |
| P108 employer | 55 | 210 | 11 | 11 | 0 | — | 923 of 2,806,429 (0.03 %) |
| P166 award received | 73 | 274 | 20 | 19 | 0 | P393 edition number | 5,677 of 1,064,710 (0.53 %) |
| P54 member of sports team | 31 | 100 | 12 | 12 | 0 | — | 199 of 3,878,290 (0.005 %) |

Across all 1,149 properties that have both an allowed list and main use, the median Jaccard similarity between the
allowed set and the robust observed set is **0.29**. The median share of qualifier uses outside the allowed list is
**0.42 %** [run].

**The pattern.** The declared lists are supersets of use: they are written to admit every legitimate qualifier. Use
concentrates on a few:
- P39: P580 1.28 M, P582 0.97 M, P2937 parliamentary term 0.69 M, P1365/P1366 replaces/replaced by 0.33 M/0.30 M;
- P54: P580, P582, then P1351 (points or goals scored) and P1350 (matches played), about 0.68 M each;
- P69: P582, P512 academic degree, P580.

Observed use outside the lists is rare. It is not always noise: P166's P393 edition number passes the robust
threshold without being allowed [run].

**Live check (WDQS, 2026-09-24).** For each property, four slices of 20,000 statements were read at fixed offsets
of the `p:Pxx` index. This is index order, not a random sample. <!--SLICES-->

### 2.5 Declared, observed, or both

**Declared (constraint) schemas**
- For:
  - They are the schema as the community designed it.
  - They are reproducible from one query, and cover 71 % of main statements.
  - They are what a "schema file" means for the checker.
- Against:
  - Only 8 % of properties have one.
  - The lists are inflated: P39's is three times its robust use.
  - They put metadata on almost every list.

**Observed (usage) schemas**
- For:
  - They cover all 13,608 used properties.
  - They reflect the joins that queries over the data actually meet.
- Against:
  - They depend on a threshold and a dump date.
  - They depend on SQID, a third-party tool whose other count fields are unreliable.
  - Without a threshold, noise makes P31 a 769-qualifier hyperedge.

**Recommendation.** Report both, side by side, under the same naming:
- the declared schema is the headline row;
- the robust observed schema is the "schema in use" row;
- the unthresholded observed schema appears only as a sensitivity row.

When P3a's corpus exists, P6 should add a row for the schema observed *in the corpus*, under the same naming, so
that the survey and the corpus describe the same thing [derived].

---

## 3. Role-naming variants, measured

### 3.1 Mapping a property to a relation

Each property becomes one relation of a `khg-relation-schema/1.0.0` document (probe:
[wd_schema_survey.py](probes/wd_schema_survey.py)). The relation id is the property id, with `mappings.wikidata`
and the English label.
- **Core usages.**
  - Subject role: min 1, max 1, direction tail, filler `wd:Item`.
  - Main-value role: min 1, max 1, direction head, filler by datatype. WikibaseItem becomes an entity. Time,
    Quantity, Monolingualtext, Url and GlobeCoordinate become the literals `time`, `quantity`, `lang_string`,
    `iri` and `geo`. Every other datatype becomes `string`.
- **Qualifier usages.** One usage per qualifier property in the table's list. The slot class follows §2.3. The
  minimum is 1 when the property has a required-qualifier constraint for that qualifier, and 0 otherwise. The
  maximum is unbounded, except for time usages, which have max 1.
- **Time.** A relation that allows P580 or P582 gets `time: {model: interval, start: P580, end: P582}`, with both
  as time usages (the missing one is added with min 0). P1534 is then covered by the built-in `khg:end_cause`.

This follows DESIGN §3's mapping of Wikidata constraints. Keys (from single-value constraints) are not generated,
since they do not affect the hypergraph. The hypergraph is `khg_contracts.schema.schema_hypergraph(doc, slots)`.
α-acyclicity is `khg_contracts.schema.is_alpha_acyclic`, the GYO reduction. An independent indexed GYO in
[hg_measure.py](probes/hg_measure.py) cross-checks it, and returned identical residues on every hypergraph, on 7
textbook cases and on 3,000 random ones [run].

**Three qualifier treatments:**
- **naive**: every qualifier is a `qualifier` role, which is what an importer without slot classes would produce;
- **core+qualifier+time**: P2 slot classes, with time bounds included;
- **core+qualifier**: P2's default for P6 (DESIGN §1.3), which leaves out time and meta.

**Three tables:**
- **declared**: 1,155 relations;
- **observed-robust**: 13,608 relations, qualifiers passing the §2.4 threshold;
- **observed-all**: 13,608 relations, every qualifier seen at least once.

### 3.2 The naming variants

| Variant | Subject role | Main-value role | Qualifier roles |
|---|---|---|---|
| **a generic** | `subject` (shared by all) | `value` (shared by all) | property id, global |
| **b property-local** | `P39:subject` | `P39:value` | property id, global |
| **c typed** | `subject:<classes of the subject-type constraint>`; falls back to b when absent | `value:<classes of the value-type constraint>` for item-valued properties; falls back to b | property id, global |
| **d property-named** (recommended) | `subject` (shared by all) | the property id, `P39`: one role with its uses as a qualifier elsewhere | property id, global |
| **e relation-local** (control) | `P39:subject` | `P39:value` | `P39:P580`, … (scoped like TypeDB roles) |

In variant d, a property that is allowed as its own qualifier would use one role twice, which M002 forbids. This
happens in 9 declared, 14 robust and 441 unthresholded relations (e.g. P131, P17, P276). The probe dropped the
qualifier use in these cases; §5 gives P3a a separate role for it.

### 3.3 Results

Every hypergraph was built through `schema_hypergraph` and tested with `is_alpha_acyclic` [run]. The full table,
with all treatments, is [out/wd-survey.md](probes/out/wd-survey.md).

The columns below are:
- vertices, max edge and components, all for core+qualifier;
- α-acyclicity;
- the GYO residue as hyperedges/vertices under core+qualifier, core+qualifier+time and naive.

| Table | Variant | Vertices | Max edge | Components | α-acyclic | Residue, core+qualifier | Residue, +time | Residue, naive |
|---|---|---|---|---|---|---|---|---|
| declared (1,155 edges) | a generic | 966 | 117 | 1 | no | 350 / 524 | 340 / 524 | 386 / 552 |
| | b property-local | 3,274 | 117 | 154 | no | 350 / 522 | 340 / 522 | 386 / 550 |
| | c typed | 3,073 | 117 | 99 | no | 438 / 563 | 422 / 563 | 476 / 591 |
| | **d property-named** | 1,884 | 117 | 1 | no | **401 / 618** | 393 / 617 | 435 / 645 |
| | e relation-local | 10,057 | 117 | 1,155 | **yes** | 0 / 0 | 0 / 0 | 0 / 0 |
| observed-robust (13,608 edges) | a generic | 779 | 34 | 1 | no | 622 / 400 | 596 / 396 | 733 / 427 |
| | b property-local | 27,993 | 34 | 11,018 | no | 622 / 398 | 596 / 394 | 733 / 425 |
| | c typed | 22,585 | 34 | 6,168 | no | 908 / 522 | 900 / 526 | 1,142 / 593 |
| | **d property-named** | 13,655 | 34 | 1 | no | **779 / 543** | 754 / 542 | 893 / 582 |
| | e relation-local | 34,713 | 34 | 13,608 | **yes** | 0 / 0 | 0 / 0 | 0 / 0 |
| observed-all (13,608 edges) | a generic | 2,532 | 750 | 1 | no | 1,120 / 1,653 | 942 / 1,649 | 994 / 1,676 |
| | b property-local | 29,746 | 750 | 7,662 | no | 1,120 / 1,651 | 942 / 1,647 | 994 / 1,674 |
| | c typed | 24,338 | 750 | 4,029 | no | 2,047 / 1,952 | 1,926 / 1,953 | 2,243 / 2,043 |
| | **d property-named** | 13,690 | 749 | 1 | no | **1,609 / 2,026** | 1,428 / 1,987 | 1,520 / 2,050 |
| | e relation-local | 83,625 | 750 | 13,608 | **yes** | 0 / 0 | 0 / 0 | 0 / 0 |

**What is left in the cyclic core.** For the declared table under variant d (core+qualifier), the most frequent
residue vertices after `subject` are:
- P518 applies to part (201 residue hyperedges);
- P585 point in time (180);
- P3831 object has role (176);
- the date-uncertainty bounds P1319 and P1326 (156 each), P8554 (147) and P8555 (144);
- P5102 (142) and P1480 (127).

The largest residue hyperedge has 103 vertices. The robust observed core is led by P585, P518, P3831 and P1545,
and its largest residue hyperedge has 33 vertices [run].

### 3.4 Reading

1. **The subject naming cannot matter.** Suppose a vertex *s* lies in every hyperedge. While two or more hyperedges
   remain, *s* is never lonely, and *e* ∪ {*s*} ⊆ *f* ∪ {*s*} holds exactly when *e* ⊆ *f*. So GYO runs in lockstep
   with and without *s*. The same *s* can be added to, or removed from, every bag of a tree decomposition without
   breaking a cover: every hyperedge contains *s*, and the special condition of hypertree decompositions is
   preserved. So α-acyclicity, hypertree width, generalized hypertree width and fractional hypertree width are all
   unchanged [derived]. A vertex in only one hyperedge is removed in GYO's first round.

   The measurements agree. Variants a and b have identical residue hyperedge counts in all nine
   (table × treatment) cells, and a's residues have exactly two more vertices [run]. This settles D-04's worry
   ([P2 research 01](../../p2-role-aware-hif/research/01-requirements-from-kb.md)) and P2 report 04 §8.2's reading.
   Generic hubs distort only descriptive statistics:
   - component count (1 against 154);
   - vertex degree (`subject` and `value` sit in all 1,155 hyperedges);
   - anything computed on the 2-section graph, such as treewidth of the primal graph, which a hub makes a clique
     partner of everything. P6 should not report primal-graph measures under a hub naming [derived].
2. **The main-value role is where naming changes the measurement.** Naming it after its property (d) joins P39's
   main value to P39 used as a qualifier elsewhere. This is the universal-relation reading: one attribute name, one
   meaning, as Wikidata intends a property to have. It grows the residue relative to b by 15 % (declared), 25 %
   (robust) and 44 % (all). Typing (c) grows it by 25 %, 46 % and 83 %.

   Typing also creates vertices such as `subject:Q5` that stand for a class rather than a role, and it depends on
   constraints that are incomplete: 35 % of properties have no subject-type constraint, and 33 % of item-valued
   properties have no value-type constraint. 3,953 properties list more than one class, and the variant turns each
   class list into one role name. Typing is closer to an ER diagram of classes than to a role schema [derived].
3. **Metadata and time do not move the class, but they do move the core, in either direction.** α-acyclicity is not
   monotone under adding vertices, so there is no fixed direction:
   - Naive import (metadata as roles) *enlarges* the residue in the declared (350 → 386) and robust (622 → 733)
     tables.
   - It *shrinks* it in the unthresholded table (1,120 → 994), where metadata vertices sit on so many hyperedges
     that they nest edges that were not nested before.
   - Adding the time bounds shrinks the residue everywhere, by 1 % to 16 % (e.g. 350 → 340 declared, 1,120 → 942
     unthresholded).

   So the survey must fix and publish its slot classes and qualifier list. They are part of the measured object,
   not noise [derived].
4. **Only relation-local roles make the schema acyclic, and then trivially.** The schema becomes a disjoint union
   of hyperedges. This matches P2 report 04 §8.2 on the 17-property sample and extends it to the full property set
   [run].

### 3.5 Recommendation

Use **variant d** in both P3a and P6, with P2's slot classes and the §2.3 list:
- subject role `subject`;
- main-value role = the property id;
- qualifier roles = the qualifier property ids.

Why d:
1. It is deterministic from Wikidata alone. It needs no human names and no constraint classes.
2. It gives each role one meaning across relations, which is the reading under which the schema hypergraph
   predicts join cost.
3. Its only hub is the universal `subject`, which provably cannot bias the class or any width.
4. It keeps P2's decisions: global roles with usages, `primary {subject, object}`, time bounds as `time`,
   `rank_reason` for P2241/P7452, and `khg:end_cause` for P1534.
5. The generated declared schema passes `check_schema` with 0 findings (1,155 relations, 1,909 roles, all four
   slots) [run].

**Consequences for the survey:**
- The headline is "α-cyclic; width = …" for every non-trivial table.
- Report core+qualifier (P2's default) and core+qualifier+time; they differ slightly.
- Report the naive treatment only to show the effect of metadata.
- Keep variant b as the sensitivity row. It shows what naming the value after its property adds, and it has the
  smallest non-trivial core (350 / 522 declared).
- Remove `subject` before reporting degree or component statistics.
- The width computation should start from the GYO residue. It is smaller, and has the same width as the whole
  schema whenever the schema is cyclic [derived]. Each GYO step can be undone without raising the width: a removed
  lonely vertex goes back in a new leaf bag covered by its one hyperedge, and a removed contained hyperedge is
  already covered by the bag of its superset. Whether a given decomposition tool does this preprocessing itself is
  [unverified].

---

## 4. The biomedical schema: Biolink Model

### 4.1 Release and licence

The candidate is Biolink Model **v4.4.5**, tag `v4.4.5`, commit `a4180f818e9722c493788c5ff1f047fde64f13a7`, committed
2026-09-18. It is the latest tag on 2026-09-24, and `master` points at the same commit [run].
- The schema declares `license: https://creativecommons.org/publicdomain/zero/1.0/`.
- The repository's `LICENSE` file is Apache-2.0.
- `pyproject.toml` says MIT [read].

The model is described in [Unni et al., 2022](https://doi.org/10.1111/cts.13302), the repository's
`CITATION.cff` reference. It was parsed with LinkML's `SchemaView` (linkml-runtime 1.11.1), which resolves `is_a`,
mixins and `slot_usage` into induced slots. The probe is [biolink_extract.py](probes/biolink_extract.py) [run].

### 4.2 How an association class maps to a relation with roles

**What an association is.** Biolink's root `association` is "a typed association between two entities, supported
by evidence". Its slots include `subject`, `predicate`, `object`, `negated` and `qualifier` [read]. Qualifier
slots descend from the grouping slot `qualifier`, which is "useful for testing compliance with association
classes" [read].

**What a qualifier does.** The `qualified predicate` note gives the reading. The core triple is `subject:ChemX,
predicate:affects, object:GeneY`. The *full statement* is `subject:ChemX, qualified_predicate:causes, object:GeneY,
object_aspect: expression, object_direction:increased` [read]. The qualifiers are therefore truth-changing
participants of an n-ary fact, which is P2's `qualifier` slot.

**The mapping** (probe: [biolink_survey.py](probes/biolink_survey.py)):
- **Relation.** One per concrete association class. Its id is the class's CURIE local name, e.g.
  `ChemicalAffectsGeneAssociation`. Biolink ids with spaces fail the `vocab_id` pattern, so CURIE local names are
  required.
- **Core.** `subject` and `object`, with the class's `slot_usage` range as the type. Under Biolink's own naming they
  are global slots, which is variant a.
- **`predicate` is not a role.** It is the edge type, chosen from the predicates the class admits. A stricter
  mapping would make one relation per (class, predicate) pair. This does not change role sets.
- **Qualifier.** The class's slots under `qualifier`, with snake_case ids such as `object_aspect_qualifier`. Two
  grouping slots are left out: `qualifier` itself and the deprecated bag `qualifiers`.
- **Domain.** 25 class-specific association slots restrict what the statement says but are not under
  `qualifier`: `expression site`, `stoichiometry`, `reaction side`, `has zygosity`, `allelic requirement`,
  `has count`/`has total`/`has percentage`/`has quotient`, `phase`, `strand`, `genome build`, and others. They are
  `qualifier` in the "formal + domain" treatment. This classification is the probe's reading of the slot
  descriptions [derived].
- **Meta.** Every other slot: provenance (`primary knowledge source`, `knowledge level`, `agent type`,
  `publications`, `has evidence`), statistics and scores (`p value`, `has confidence score`, database-specific
  scores), denormalised closures (`subject closure`, `object category`, …) and node slots (`id`, `name`,
  `category`).

### 4.3 Counts [run]

| Quantity | Value |
|---|---|
| Association classes (`association` and its `is_a` descendants) | 107: 103 concrete, 4 abstract, 0 mixins |
| Qualifier slots defined under `qualifier` | 44, of which 33 are used by at least one association and 11 are unused grouping slots (e.g. `aspect qualifier`, `context qualifier`, `statement qualifier`) |
| Qualifier slots on the root `association` (so on every class) | 3: `association basis qualifier`, `species context qualifier`, `statistical significance qualifier` |
| Qualifier slots per concrete class | 3 slots: 52 classes; 4–8: 11; 14–18: 40 (max 18, `gene affects chemical association`) |
| Most shared (excluding the root's 3) | object direction 44, qualified predicate 43, object aspect 42, subject aspect 41, subject direction 39, anatomical context 36, population context 31, frequency 30, object specialization 30, disease context 29, subject specialization 29 |
| Domain slots (the probe's classification), classes using them | has count / total / percentage / quotient 11 each, allelic requirement 7, clinical approval status 3, max research phase 3, number of cases 3, quantifier qualifier 3; 16 more on 1–2 classes |
| Slots on the root `association` | 57 |
| Most common subject ranges | gene or gene product 13, named thing 12, chemical entity 9, genotype 6, sequence variant 6 |
| Most common object ranges | disease 16, gene or gene product 11, anatomical entity 8, phenotypic feature 8, named thing 6 |

### 4.4 α-acyclicity quick check [run]

All schema documents pass `check_schema` with 0 findings. Residues come from `is_alpha_acyclic`, and the indexed
GYO agrees.

| Variant | Qualifier set | Vertices | Max edge | α-acyclic | GYO residue (edges / vertices) |
|---|---|---|---|---|---|
| a generic (Biolink's own global `subject`/`object`) | formal | 35 | 20 | no | 5 / 18 |
| | formal + domain | 60 | 24 | no | 5 / 19 |
| | all slots (meta included) | 117 | 74 | no | 7 / 74 |
| b class-local core | formal | 239 | 20 | no | 5 / 16 |
| c typed (`subject:GeneOrGeneProduct`, …) | formal | 98 | 20 | no | 53 / 59 |
| | formal + domain | 123 | 24 | no | 53 / 73 |
| e relation-local (control) | formal | 1,020 | 20 | yes | 0 / 0 |

**The core is small under Biolink's own naming.** The five residue hyperedges are qualifier sets drawn from five
families:
- the chemical-affects-gene family (`ChemicalAffectsGeneAssociation`, `GeneAffectsChemicalAssociation`, …, with 13
  qualifiers);
- the gene-to-disease family (`CorrelatedGeneToDiseaseAssociation`, …);
- `GeneToExpressionSiteAssociation`;
- `GeneToGeneCoexpressionAssociation`;
- `NamedThingAssociatedWithLikelihoodOfNamedThingAssociation`.

They are tied by `stage_qualifier`, `object_specialization_qualifier`, `population_context_qualifier` and
`object_context_qualifier`, which are shared in patterns that do not nest [run].

**Typing breaks it open.** It turns the core into 53 hyperedges, because range-typed subject and object roles
overlap across families. The naming lesson is the same as for Wikidata: keep Biolink's global slot names (variant
a or b) and do not type the core roles [derived]. Biolink is a good second survey subject. It is n-ary, its
qualifiers are declared in one file, it is pinned and CC0, and its core is small enough that an exact width is
likely computable [derived].

### 4.5 Fallback and why it is weaker

**GO-CAM's LinkML schema** is the fallback (gocam-py v0.12.0; [Thomas et al., 2019](https://doi.org/10.1038/s41588-019-0500-1);
probe [gocam_quickcheck.py](probes/gocam_quickcheck.py)). It is genuinely n-ary. An `Activity` binds
`enabled_by`, `molecular_function`, `occurs_in`, `part_of`, `happens_during`, and molecular and causal
associations. But it has one central relation class, and 12 small association classes with one or two role slots
each (`term`, `part_of`, `has_part`, `predicate` with `molecule` or `downstream_activity`). Its schema hypergraph
has 13 hyperedges on 12 vertices, with a largest edge of 7. It is α-acyclic, and GYO empties it [run]. So it can
only confirm the checker on an easy case, not measure a real schema's width. Its licence file is a template with a
placeholder holder [read].

**Hetionet** is weaker still. Version 1.0 has "47,031 nodes of 11 types and 2,250,197 relationships of 24 types"
([hetio/hetionet README](https://github.com/hetio/hetionet), commit `8a6cc0c`) [read]. All relationships are
binary with no qualifiers.
- With generic source and target roles, every relation type is the same two-vertex hyperedge, so the schema is
  trivially acyclic.
- With type-named roles it is a graph, α-acyclic only if it is a forest [derived].

Either way it says nothing about qualifier structure. SemMedDB predications are also subject–predicate–object
triples [unverified for the 2026 release]. **INDRA's** statement types are n-ary with named roles (P2 report 04),
but the schema file this probe expected (`indra/resources/statements_schema.json` at v1.4.1) returned HTTP 404
[run]. INDRA is not evaluated here.

---

## 5. For P3a: the Wikidata role naming to adopt

*This section is written to be sent to the P3a session verbatim.*

> **P3a ⇄ P6 role naming for Wikidata statements (proposal `wd-roles`, 2026-09-24).** P6 measures the schema
> hypergraph over role ids. P3a's corpus must use exactly the same ids, or the survey and the corpus describe
> different objects. Please adopt the following when converting a Wikidata statement *(s, P, v, qualifiers,
> rank)* into a C1 hyperedge record under `khg-relation-schema/1.0.0`.
>
> 1. **Relation id** = the property id, e.g. `P39`. Put the English label in the schema's `label` and
>    `{"wikidata": "P39"}` in `mappings`. Do not use human-readable ids: labels change, and ids must not.
> 2. **Subject role** = `subject` for every relation. It is a core usage, min 1, max 1, direction `tail`. It is
>    also `primary.subject`.
> 3. **Main-value role** = the property id itself, e.g. the position in a P39 statement binds role `P39`. It is a
>    core usage, min 1, max 1, direction `head`. It is also `primary.object`. `somevalue` and `novalue` stay allowed
>    (P2 defaults).
> 4. **Qualifier roles** = the qualifier's property id, e.g. `P580`, `P1365`, `P2937`. It is one global role,
>    whether the property appears as a qualifier or as a main value elsewhere.
> 5. **Self-qualifier.** When a statement of property P carries P itself as a qualifier, use role
>    `P<id>:qualifier`, e.g. `P131:qualifier`. This keeps M002 (one usage per role) and happens on 9 to 441
>    properties depending on how usage is counted.
> 6. **Slot classes:**
>    - `time`: P580 and P582, always. A relation whose statements may carry either (allowed by its constraint, or
>      seen in the corpus) gets `time: {"model": "interval", "start": "P580", "end": "P582"}` with both as time
>      usages (min 0, max 1). A statement with two P580 values cannot fit max 1; please count such statements in
>      the datasheet. P585 point in time is always `qualifier`.
>    - `meta`, or a record field instead of a binding:
>      - P2241 and P7452 go to `rank_reason` (DESIGN §3), not to bindings;
>      - P1534 end cause becomes the built-in `khg:end_cause` on interval relations, and `meta` otherwise;
>      - these are `meta`: P8327, P13589, P1810, P14457, P1932, P4970, P813, P854, P248, P1065, P2960, P143, P4656,
>        P887, P3452, P1683, P5017, P3680, P1310, P805, P2916, P6607, P9570, P7528.
>    - `qualifier`: everything else, including P5102 nature of statement, P1480 sourcing circumstances, P585,
>      P1319, P1326, P8554, P8555, P12506, P518 and P3831.
> 7. **References** (the statement's sources) are evidence, not bindings. A source property that appears as a
>    *qualifier* follows rule 6.
> 8. **Out of scope as relations.** Properties that document or constrain other properties (instances of
>    `Q19820110`, `Q21504947` or `Q64846109`, e.g. P1855, P2302, P360, P4224). There are 57 as of 2026-09-24.
> 9. **Please record, per relation in the corpus**, the qualifier properties used and their counts, before and
>    after slot classing. P6 will measure the corpus-observed schema with them, next to the Wikidata-declared one.
>    Also record the list version: this is `wd-roles` 2026-09-24, and the meta list is part of it.
>
> Why: a `subject` role shared by all relations cannot change the acyclicity class or any hypertree width.
> Property-scoped or relation-local roles make every schema trivially acyclic. Naming the main value after its
> property gives each role one meaning across relations. Measurements:
> `projects/p6-schema-width/research/02-data-sources-and-naming.md` §3.

---

## 6. Risks to the P6 gate

1. **Width, not class, is the result, and it may be hard to compute exactly.** The Wikidata cores are large:
   - declared, d: 401 hyperedges on 618 vertices, with residue edges up to 103 vertices;
   - robust: 779 on 543.

   Checking hypertree width ≤ *k* is polynomial for fixed *k*, but the degree grows with *k*. Checking generalized
   or fractional hypertree width ≤ 2 is already NP-complete ([Gottlob et al., 2020](https://arxiv.org/abs/2002.05239);
   [hypergraph theory results](../../../kb/01-foundations/hypergraph-theory-results.md) §6). The gate says "the checker reports class and width". The checker should report an upper bound (a
   decomposition it found) and a lower bound, and call the width exact only when they meet. Biolink's 5-edge core
   is the likely place for an exact number [derived].
2. **The measured object depends on choices.** The naming, the slot classes, the metadata list and the robust
   threshold all shift the residue by up to about 80 % (§3.4). They must be fixed, versioned and shared with P3a
   before the survey runs.
3. **Data drift and third-party counts.**
   - The constraints are live (2026-09-24), the SQID counts come from the 2026-08-10 dump, and DeltaBot's from
     2026-09-23.
   - SQID's non-`qs` fields are inconsistent, and the meaning of `qs` (statements or snaks) is [unverified].
   - WDQS could not aggregate qualifier usage for high-use properties at all.
   - The survey should pin the files in the manifests, and later recompute observed schemas from a dump or from
     P3a's corpus.
4. **The metadata list is judgement.** It covers the top of the frequency distribution, not all 2,556 observed
   qualifiers.
5. **Licences are fine for measurement.** Wikidata and Biolink are CC0. GO-CAM's licence file is a placeholder;
   do not redistribute it without asking.

## 7. Reproduction

All commands run from the repository root; the venv paths are the session's.

```
python projects/p6-schema-width/research/probes/wd_fetch.py              # SPARQL, templates, SQID -> raw/ + MANIFEST
python projects/p6-schema-width/research/probes/wd_schema_survey.py      # tables, variants, out/wd-survey.{json,md}
python projects/p6-schema-width/research/probes/biolink_extract.py       # needs pyyaml + linkml-runtime
python projects/p6-schema-width/research/probes/biolink_survey.py        # out/biolink-survey.json
PYTHONPATH=src python projects/p6-schema-width/research/probes/gocam_quickcheck.py
python projects/p6-schema-width/research/probes/hg_measure.py            # GYO cross-check on textbook cases
```

The declared schema under variant d is written to
`datasets/knowledge-bases/wikidata-property-schemas/processed/wd-declared-d_property.relation-schema.json`, which is
gitignored and regenerated by the survey probe.

## Sources

**Wikidata** (all read or queried 2026-09-24):
- Wikidata Query Service (main graph), <https://query.wikidata.org/sparql>.
- *Wikidata:SPARQL query service/WDQS graph split*, <https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/WDQS_graph_split>.
- *Help:Qualifiers*, <https://www.wikidata.org/wiki/Help:Qualifiers>.
- *Help:Ranking*, <https://www.wikidata.org/wiki/Help:Ranking>.
- *Help:Sources*, <https://www.wikidata.org/wiki/Help:Sources>.
- *Help:Property constraints portal/Qualifiers* (allowed qualifiers constraint), <https://www.wikidata.org/wiki/Help:Property_constraints_portal/Qualifiers>.
- *Help:Property constraints portal/Required qualifiers*, <https://www.wikidata.org/wiki/Help:Property_constraints_portal/Required_qualifiers>.
- *Help:Property constraints portal/Subject class*, <https://www.wikidata.org/wiki/Help:Property_constraints_portal/Subject_class>.
- *Help:Property constraints portal/Value class*, <https://www.wikidata.org/wiki/Help:Property_constraints_portal/Value_class> [unverified: HTTP 429 when fetched].
- Wikidata items Q61719275 (restrictive qualifier), Q61719274 (non-restrictive qualifier), Q122233685, Q15720608, Q18608359 and Q115429021, read through `wbgetentities`, <https://www.wikidata.org/w/api.php>.
- Property descriptions of the §2.3 list, read through `wbgetentities`.
- DeltaBot templates *Number of main statements by property*, *Number of qualifiers by property* and *Number of references by property*, revisions of 2026-09-23, <https://www.wikidata.org/wiki/Template:Number_of_main_statements_by_property>.
- *Wikidata:Copyright*, <https://www.wikidata.org/wiki/Wikidata:Copyright> (CC0 for structured data) [unverified in this run; per datasets/README.md].
- SQID data files, <https://sqid.toolforge.org/data/properties.json> and <https://sqid.toolforge.org/data/statistics.json> (dump date 2026-08-10).

**Biomedical schemas:**
- Unni, D. R., Moxon, S. A. T., Bada, M., et al. (2022). *Biolink Model: A universal schema for knowledge graphs in clinical, biomedical, and translational science.* Clinical and Translational Science 15(8). <https://doi.org/10.1111/cts.13302>. Title and DOI from the repository's CITATION.cff; volume from memory [unverified].
- Biolink Model repository, tag v4.4.5, commit a4180f818e9722c493788c5ff1f047fde64f13a7, <https://github.com/biolink/biolink-model>.
- LinkML runtime 1.11.1 (`SchemaView`), <https://pypi.org/project/linkml-runtime/>.
- Thomas, P. D., Hill, D. P., Mi, H., et al. (2019). *Gene Ontology Causal Activity Modeling (GO-CAM) moves beyond GO annotations to structured descriptions of biological functions and systems.* Nature Genetics. <https://doi.org/10.1038/s41588-019-0500-1>.
- gocam-py, tag v0.12.0, commit e6f824a5cc2d50ad1fa12081bec0ca5c945c5199, <https://github.com/geneontology/gocam-py>.
- Hetionet repository README, commit 8a6cc0c, <https://github.com/hetio/hetionet>. The paper is Himmelstein, D. S., et al. (2017), *Systematic integration of biomedical knowledge prioritizes drugs for repurposing*, eLife 6:e26726, <https://doi.org/10.7554/eLife.26726> [DOI resolves; text not read].

**Theory and project context:**
- Fagin, R. (1983). *Degrees of acyclicity for hypergraphs and relational database schemes.* JACM 30(3). <https://dl.acm.org/doi/10.1145/2402.322390>.
- Beeri, C., Fagin, R., Maier, D., Yannakakis, M. (1983). *On the Desirability of Acyclic Database Schemes.* JACM 30(3). <https://dl.acm.org/doi/10.1145/2402.322389>.
- Gottlob, G., Leone, N., Scarcello, F. (2002). *Hypertree Decompositions and Tractable Queries.* JCSS 64(3). <https://arxiv.org/abs/cs/9812022>.
- Gottlob, G., Lanzinger, M., Pichler, R., Razgon, I. (2020). *Complexity Analysis of Generalized and Fractional Hypertree Decompositions.* <https://arxiv.org/abs/2002.05239>.
- The KB note [hypergraph theory results](../../../kb/01-foundations/hypergraph-theory-results.md) holds these four results.
- P2 [DESIGN.md](../../p2-role-aware-hif/DESIGN.md) §1.3, §2.4 and §3.
- P2 research [01](../../p2-role-aware-hif/research/01-requirements-from-kb.md) (D-04) and [04](../../p2-role-aware-hif/research/04-prior-art-modelling.md) §8.2, with its probe [wikidata_schema_hypergraph_probe.py](../../p2-role-aware-hif/research/probes/prior-art/wikidata_schema_hypergraph_probe.py).
