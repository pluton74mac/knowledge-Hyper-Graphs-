---
title: "How acyclic are knowledge-hypergraph schemas?"
subtitle: "Acyclicity class and hypertree width of Wikidata qualifier schemas and the Biolink Model"
author: "[AUTHOR: to be filled in by the owner]"
date: "Draft, 2026-09-25"
abstract: |
  A relation-type schema of a knowledge hypergraph can be read as a hypergraph whose vertices are role names and
  whose hyperedges are relations. Its acyclicity class in Fagin's hierarchy (Berge, γ, β, α) and its hypertree width
  are those of the conjunctive query that joins all relations on same-named roles. We measure both for Wikidata's
  qualifier schemas, declared (allowed-qualifier constraints, 1,155 properties) and observed (exact qualifier usage in
  the dump of 2026-09-22, 13,315 properties, and in its items with an English Wikipedia article), and for the
  association classes of the Biolink Model v4.4.5 (103 relations). A new checker reports hw, ghw, fhw and tw exactly
  or as bounds; every upper bound comes with a decomposition validated on the input, and every lower bound with a
  stored witness. Every schema whose role names are shared across relations is α-cyclic; only relation-local role
  names make the schemas acyclic, and then trivially. Biolink's association schema has hw = ghw = fhw = 2. Wikidata's
  cyclic cores have 391 to 1,458 relations, and their hypertree width lies in [4, 38] for the declared schema and in
  [4, 65] and [3, 53] for the observed ones over the whole dump: at least that of every one of HyperBench's 1,113
  non-random conjunctive queries (all hw ≤ 3), and strictly more for two of the three. The number bounds the cost of
  the universal role join, not of arbitrary queries over the data.
keywords: [hypergraph acyclicity, hypertree width, database schemes, knowledge hypergraphs, Wikidata, Biolink Model]
type: project
status: draft
created: 2026-09-25
updated: 2026-09-25
---

<!-- OWNER: a draft for the owner to release; nothing has been published from a Claude session.
     The observed rows were re-run on exact counts from the 2026-09-22 dump on 2026-09-25, and every number here is
     from results/survey.csv and the reports at that commit. Before release (RELEASE.md): fill in the author, the
     commit and the Zenodo DOI (search for "[" placeholders).
     pandoc's LaTeX writer drops HTML comments like this one. -->

# 1. The question

Fagin showed that desirable properties of database schemes "fall into several equivalence classes, each completely
characterized by the degree of acyclicity of the scheme" [1], and Beeri, Fagin, Maier and Yannakakis showed several
such properties to be equivalent to α-acyclicity [2]. Gottlob, Leone and Scarcello made the distance from acyclic
measurable: the α-acyclic conjunctive queries are exactly those of hypertree width 1, and queries of bounded
hypertree width can be evaluated in polynomial time [7].

Knowledge hypergraphs store n-ary facts. A Wikidata statement binds a subject, a main value and any number of
qualifiers [22, 23]; a Biolink association binds a subject, an object and qualifier slots [29]. A schema for such data
lists relation types and the roles each uses. Read as a database scheme with roles as attributes, it has an
acyclicity class and a width. The knowledge base this work comes from records the question as open: *where do real
knowledge-hypergraph schemas fall in the hierarchy, and what is their hypertree width?* We did not search
systematically for earlier measurements; that none exists is `[unverified]`.

The answer is easy to overstate. The width bounds the cost of one query, the join of all relations on same-named
roles (Section 2.2). The class decides scheme properties such as "pairwise consistency implies global consistency",
the side of [2] usually cited (that list was not checked against the full text of [2] `[unverified]`). Neither
predicts the cost of arbitrary queries over the data, which join facts on entity variables and have their own
hypergraphs.

# 2. What is measured

## 2.1 The role-name hypergraph

A relation-type schema *S* (here in the repository's format `khg-relation-schema/1.0.0`) declares relations and the
roles each uses, each usage in a *slot*: `core`, `qualifier`, `time` or `meta`. For a slot set σ, the hypergraph
*H(S, σ)* has one vertex per role id, whatever its slot, and one hyperedge per relation: the roles of its usages in σ.
*H* is a named multi-hypergraph. Berge-acyclicity is decided on it, so two relations with the same role set form a
Berge cycle; α, β, γ and the widths use the set hypergraph, and duplicate role sets are reported separately.

## 2.2 The universal join

The widths of *H* are those of the conjunctive query that joins every relation of *S* on same-named roles, the
universal-relation join of Fagin's setting. A join of only some relations has a partial hypergraph of *H* as its own,
and its width can be larger: dropping the covering edge from a triangle with a cover turns hw 1 into hw 2. When *H* is
β-acyclic, every partial hypergraph stays α-acyclic [3]. The Berge class reads directly for storage: reifying each
n-ary fact into a fact node with one binary edge per role turns *H* into its incidence graph, and on graphs all the
degrees coincide [3, Remark 7], so the reified encoding is acyclic exactly when the schema is Berge-acyclic.

## 2.3 Role naming

What counts as "the same role" decides the measurement, so the naming is fixed and published.

- **wd-roles r1** (Wikidata, headline). The subject role is `subject` in every relation; the main-value role is the
  property id (a P39 statement binds role `P39`); a qualifier's role is its property id, whether that property is
  used as a qualifier or as a main value elsewhere; a property that qualifies its own statements gets the role
  `P<id>:qualifier`. The 57 properties that document or constrain other properties are not relations. A companion
  Wikidata n-ary corpus uses the same naming, so the two describe the same object.
- **Biolink global** (headline). Biolink's own slot names: `subject`, `object` and each qualifier slot's name.
  `predicate` names the relation type and is not a role.
- **Relation-local** (control, both sources). Every role id is scoped to its relation (`P39:subject`, `P39:P580`).
  Hyperedges are then pairwise disjoint: Berge-acyclic, every width 1. The control shows that width comes from shared
  names.

A role in every relation, such as `subject`, changes neither the class nor hw, ghw or fhw [R02 §3.4], and raises tw by
exactly one. Naming the main value after its property joins a property's main use to its qualifier uses elsewhere
(Section 6).

## 2.4 Slots

The headline slot set is `core,qualifier`; the variant adds `time`; `meta` never enters *H*. For Wikidata, `time` is
P580 and P582 (start and end time). `meta` is 24 listed statement-metadata properties (rank and special values,
inline sources, wording in the source, support and dispute, editorial notes) plus the rank reasons P2241 and P7452;
P1534 (end cause) is a built-in lifecycle field on interval relations and `meta` elsewhere. Everything else is `qualifier`, including P585 (point in time) and P518 (applies to part).
For Biolink, `qualifier` is the slots under its `qualifier` slot ("formal"), optionally with 25 domain slots that
restrict what an association says ("formal + domain"); Biolink has no interval bounds.

## 2.5 Declared and observed schemas

- **Declared.** The 1,155 properties with a non-deprecated *allowed qualifiers* constraint (Q21510851, parameter
  P2306; "no value" means none), after removing the 57, fetched from the Wikidata Query Service (main graph) on
  2026-09-24, 09:35–09:44 UTC [24]. They carry 1.27 of the 1.79 billion main statements (71 %; DeltaBot counts of
  2026-09-23 [28]).
- **Observed.** Every property with at least one main statement in the Wikidata JSON dump of 2026-09-22 [32], minus
  the 57: 13,315 relations. A qualifier is a role of the property if it is used on its statements: *robust* means on
  at least 10 statements and at least 0.1 % of the property's main statements, *all* means on at least one. The
  counts are exact statement counts per (property, qualifier) from one pass over the dump, over every item and
  property entity, made by the companion corpus's dump slicer under the same naming.
- **Observed on the corpus slice.** The same over the 7,584,990 items that have an English Wikipedia article, the
  part of Wikidata the companion corpus keeps: 12,706 relations. These *slice* rows describe the schema of that
  corpus rather than of all of Wikidata.
- **Biolink Model v4.4.5** (commit `a4180f8`): one relation per concrete association class, 103 in all, with core
  roles `subject` and `object` [29].

# 3. Method

## 3.1 Classes, with witnesses

Berge ⊂ γ ⊂ β ⊂ α, all strict [3]. The checker tests α by GYO reduction, β by nest-point elimination, γ by the
D'Atri–Moscarini reduction [3, 6] and Berge by union–find on the incidence graph, stopping at the first failure. The
failing test gives the class and a witness: the GYO residue ("cyclic", that is, not α-acyclic), a chordless incidence
cycle of length at least six (α, not β), a γ-triangle (β, not γ) or an incidence cycle (γ, not Berge). An α-acyclic
*H* gets a join tree, checked for running intersection. The tests agreed with brute-force evaluation of the
definitions on 400 seeded random hypergraphs [R01 §1.4].

## 3.2 Widths: certificates and bounds

The checker reports hypertree width hw, generalized hypertree width ghw, fractional hypertree width fhw [7, 9] and
the treewidth tw of the primal graph, each exactly or as `[lower, upper]`, with
$\mathrm{fhw} \le \mathrm{ghw} \le \mathrm{hw} \le 3\,\mathrm{ghw} + 1$ [8, 9] and $\mathrm{ghw} \le \mathrm{tw} + 1$.

- **No upper bound without a certificate.** Each carries a decomposition validated on the unreduced *H*: coverage and
  connectedness, guards covering bags, for hw the special condition, for fhw a fractional cover in exact rationals.
- **Reductions only where sound.** GYO steps, twin merging, universal-role removal and block splitting serve ghw and
  fhw; tw uses the simplicial rule and universal roles (+1 each) but never twin merging; hw is computed on the
  unreduced *H*. A decomposition found on a reduced hypergraph is lifted back to *H* and validated there.
- **Exact procedures.** An α-acyclic *H* has hw = ghw = fhw = 1, certified by its join tree. tw, ghw and fhw are exact
  by the subset dynamic programme over elimination orderings [12] on cores of up to 20 roles (16 for fhw), with
  $\rho^*$ from an exact rational simplex whose primal and dual are both checked; hw by a det-k-decomp-style search
  [13] on up to 60 relations.
- **Lower bounds**, each with a stored witness: a cyclic *H* has hw, ghw ≥ 2 and fhw > 1 [7, 9]; ghw ≥ $\rho(K)$ and
  fhw ≥ $\rho^*(K)$ for a clique *K* of the core's primal graph; exact values on small induced subhypergraphs;
  tw ≥ rank − 1 and minor-min-width; solver refutations from runs without preprocessing.
- **Upper-bound heuristics.** Min-fill and min-degree orderings with greedy guards, and a repair pass that adds the
  roles breaking the special condition, with guards, to the bags concerned, turning a generalized hypertree
  decomposition into a hypertree decomposition.

## 3.3 External solvers and budget

BalancedGo [17] (commit `872c662`, v1.7.2-2, MIT) is the primary hw solver, log-k-decomp [18] (v1.1.0, `5e021dd`, MIT)
the second opinion. They receive *H* with neutral ids, since some tools misparse or reject names with colons, dots or
dashes [R01 §4.3]. The search bisects on *k* between the validated bounds: at each *k* both tools run with their
preprocessing flags to *find* a decomposition, validated on the unreduced *H*, and BalancedGo runs once more without
them; only a "no" from a run without preprocessing is a lower bound. Each attempt runs at most 120 s, all attempts on
one schema at most 1,200 s, and each Python step at most 600 s. Seed 20260924; Linux x86-64, 4 CPUs, Python 3.11.15,
Go 1.24.7. The observed rows ran two at a time on a machine shared with other work, and each report records the load
it ran under. The limits make the bounds machine-dependent, so every attempt is logged with command, time and
outcome.

## 3.4 Independent validation

One review round (per the project record; its working files are not in the repository) re-validated every stored
certificate with an independent validator, reproduced the lower bounds and fuzzed 4,000 random hypergraphs against
brute force. It found no wrong number and nine defects (four medium, five low), each fixed with a regression test; the
eight affected rows were re-run. The observed rows were then re-run on the exact counts of Section 2.5; the review
predates them, and they passed the same test suite, which re-validates every stored certificate and lower-bound
witness.

# 4. Results

Table 1 gives the rows that carry the findings; the deposit has the full table with rank, degree, intersection width
and run times. The core is the GYO residue with twin roles merged and universal roles removed.

| Schema | Slots | Relations / roles | Class (residue) | Core | hw | ghw | fhw | tw |
|---------------|-------|--------------|--------------|-------------|-----------|-----------|----------------------|-----------------|
| WD declared | cq | 1,155 / 1,892 | cyclic (391) | 391 / 578 | [4, 38] | [4, 25] | [35/11, 24] | [116, 235] |
| WD declared | cq+t | 1,155 / 1,893 | cyclic (392) | 392 / 580 | [4, 43] | [4, 25] | [35/11, 24] | [118, 237] |
| WD robust | cq | 13,315 / 13,391 | cyclic (751) | 751 / 530 | [4, 65] | [4, 30] | [75/23, 53/2] | [55, 139] |
| WD robust | cq+t | 13,315 / 13,391 | cyclic (767) | 767 / 539 | [4, 60] | [4, 30] | [75/23, 185/7] | [57, 140] |
| WD all | cq | 13,315 / 13,886 | cyclic (1,453) | 1,453 / 1,998 | [3, 53] | [3, 35] | [2, 269/8] | [771, 1226] |
| WD all | cq+t | 13,315 / 13,886 | cyclic (1,458) | 1,458 / 2,001 | [3, 52] | [3, 35] | [11/5, 269/8] | [773, 1228] |
| WD robust, slice | cq | 12,706 / 12,810 | cyclic (603) | 603 / 460 | [4, 48] | [4, 26] | [7/2, 250/11] | [51, 114] |
| WD robust, slice | cq+t | 12,706 / 12,810 | cyclic (613) | 613 / 466 | [4, 59] | [4, 26] | [7/2, 114/5] | [53, 116] |
| WD all, slice | cq | 12,706 / 13,189 | cyclic (1,292) | 1,292 / 1,558 | [4, 51] | [4, 36] | [8/3, 143/4] | [452, 838] |
| WD all, slice | cq+t | 12,706 / 13,189 | cyclic (1,297) | 1,297 / 1,560 | [4, 47] | [4, 36] | [8/3, 34] | [452, 852] |
| BL formal | cq | 103 / 35 | cyclic (5) | 5 / 8 | 2 | 2 | 2 | 19 |
| BL formal+dom. | cq | 103 / 60 | cyclic (5) | 5 / 8 | 2 | 2 | 2 | 23 |
| Controls | both | see text | Berge (0) | 0 / 0 | 1 | 1 | 1 | rank − 1 |
| HyperBench | | 1,113 CQs | | | 1 / 2 / 3: 673 / 432 / 8 | | | |

: Survey results. WD = Wikidata (wd-roles r1): declared, observed-robust, observed-all, over the whole dump or over
the slice (items with an English Wikipedia article); BL = Biolink v4.4.5, global slot names. cq = core and qualifier
roles, cq+t adds time roles. Class: "cyclic" = not α-acyclic, with the GYO residue's relation count. Core: relations /
roles. `[l, u]` is a bound, a single value exact.

**Controls.** With relation-local roles, Wikidata declared, observed-robust, observed-all and Biolink formal have
9,999, 34,050, 83,572 and 1,020 roles. Each is Berge-acyclic with hw = ghw = fhw = 1, and its treewidth is its
largest relation's size minus one (the rank): 116, 34, 771 and 19 (118, 36 and 773 with time roles). On the slice,
observed-robust and observed-all have 31,572 and 62,641 roles and treewidth 36 and 410 (38 and 412 with time roles).

**Where the Wikidata bounds come from.** The hw lower bounds follow from hw ≥ ghw ≥ $\rho(K)$ for a primal clique *K*
of the core: $\rho(K) = 4$ on 37 roles (declared), 4 on 18 roles (observed-robust) and 3 on 61 roles (observed-all),
and on the slice 4 on 17 roles (observed-robust) and 4 on 53 roles (observed-all). The clique enumeration finished
within its 600 s step only for the two observed-robust schemas; for the others the best bound found by then is
reported. On the slice, observed-all's bound (4) is above the dump's (3), although each of its relations is a relation
of the dump's schema with a subset of its roles: widths are not monotone under shrinking relations (Section 2.2). The
53 roles that need four slice relations to cover are covered by two in the dump, instance of (P31) and has part(s)
(P527), whose observed qualifier lists are longer there. The solvers spent their full 1,200 s on each wd-roles r1
row, and every attempt timed out at 120 s but one: a width-41 BalancedGo decomposition (declared, with time roles)
that violated the special condition; repaired to a validated width-46 hypertree decomposition, it improved neither
bound. The Wikidata upper bounds are therefore khg-width's own. A wd-roles r1 row took 1,483 to 2,534 s of wall time; a Biolink row under a
second.

![(a) hw per schema, a point when exact and a bar for [lower, upper], beside the hw distribution of HyperBench's non-random conjunctive queries; (b) GYO residue size of the Wikidata schemas. Wikidata columns: declared, then observed-robust and observed-all over the whole dump and over the slice.](../results/figure-widths.png){width=80%}

**The HyperBench baseline.** HyperBench collects hypergraphs of conjunctive queries and constraint problems [14, 15].
Recomputed from its published runs [16], its 1,113 non-random conjunctive queries have exact hw 1 (673, 60.5 %),
2 (432, 38.8 %) or 3 (8, 0.7 %). The collection is biased toward cyclic queries: its SPARQL and Wikidata subsets keep
only cyclic ones, and SQLShare only queries with at least three atoms [15]. These are *queries*, not schemes, so the
comparison is by hw and structural parameters only. In the published runs, exact hw is known for only 6 of the 23
graphs with 300 to 999 edges and for none of the 6 with 1,000 or more [R01 §3.5]: the size of the Wikidata cores.

# 5. Findings

1. **Real knowledge-hypergraph schemas are cyclic once roles are shared.** Every Wikidata schema under wd-roles r1,
   with or without time roles, and both Biolink schemas under global slot names, are α-cyclic. The research probe
   found the same under generic, property-local and typed namings, on the declared table and on observed tables built
   from SQID's earlier counts [27; R02 §3.3]. Only relation-local roles give acyclic schemas, trivially. So the class
   does not separate the variants; the width does. *Limits:* two schema families, and not every such schema is
   cyclic: GO-CAM's is α-acyclic by GYO in one pass [R02 §4.5; 31].
2. **Wikidata's cyclic core is large, and its universal-join width is at least 3 to 4 and unsettled.** The residues
   have 391 to 1,458 relations; hw lies in [4, 38] (declared), [4, 65] (observed-robust) and [3, 53]
   (observed-all), each upper bound certified and each lower bound witnessed. On the slice, the items with an English
   Wikipedia article, the cores are smaller (603 and 1,292 relations against 751 and 1,453) and so are the upper
   bounds, hw in [4, 48] and [4, 51]; the lower bounds are not. *Limits:* wide intervals; the lower bounds are clique
   bounds, three of them from an enumeration that did not finish (observed-all's on the dump, 3, is below
   observed-robust's, 4, although its schema has more roles); machine-dependent limits.
3. **Biolink's association schema is small and exactly width 2**: hw = ghw = fhw = 2 on a five-relation core, with or
   without the domain slots, inside the range of real conjunctive queries (1,105 of HyperBench's 1,113 have hw ≤ 2).
   *Limits:* one model version; the domain-slot classification is our reading of the slot descriptions.
4. **The number is the width of joining all relations on same-named roles.** It bounds the cost of that universal
   join; it does not bound joins of only some relations (Section 2.2), nor arbitrary queries. For contrast, HyperBench
   reports that of 1,915,550 CQOF+ queries in the Wikidata logs studied by Bonifati, Martens and Timm, 590,005 have
   hw 2 and the rest hw 1 ([15], quoting [21]; `[unverified]` against the original). Treewidth is the wrong
   yardstick: the declared relation-local control has hw 1 and tw 116, set by its largest relation.
5. **Declared qualifier lists overstate use.** Counted over the whole dump of 2026-09-22 (every item and property
   entity): position held (P39) allows 104 qualifiers; 333 distinct qualifiers occur on its statements and 36 pass
   the robust threshold, all of them allowed. Over the 1,134 properties with an allowed list and main statements, the
   median Jaccard similarity of the allowed and robust observed sets is 0.30 (the measure of [R02 §2.4], recomputed on
   these counts). Hence both schemas are reported. *Limits:* the observed schemas depend on the threshold, the dump
   date and the scope.

All three Wikidata schemas are at least as wide as every non-random conjunctive query in HyperBench (hw ≤ 3), and
the declared and observed-robust ones, with hw ≥ 4, are wider than all of them; so are both observed schemas of the
slice.

# 6. Limits and threats to validity

- **Bounds, not exact values, for Wikidata.** No solver decided any *k* on a Wikidata core within 120 s per attempt
  and 1,200 s per schema. Longer runs or other methods may narrow the intervals.
- **Naming dependence.** wd-roles r1 is one defensible naming among several. On the research probe (an earlier
  version of the naming, SQID's counts [27] for the observed tables), naming the main value after its property grew
  the residue by 16 % to 51 %, and typing roles by constraint classes by up to 99 % [R02 §3.4]. Only the 120 most shared
  declared and observed qualifiers were reviewed for the meta list [R02 §2.3]. The naming version is recorded in
  every file; a new version means regenerating the schemas and re-running the rows.
- **The universal-join reading.** The widths describe the role join of the scheme, not queries over the data; a query
  over an α-acyclic scheme can itself be cyclic.
- **What was counted.** The observed schemas count statements on the items and property entities of the JSON dump of
  2026-09-22. Lexemes are not in it, so 294 lexicographic properties (dictionary identifiers, sense and form links)
  that have main statements by Wikidata's own count [28] but none on items or properties are not relations here. Two
  properties used in the dump were no longer listed by the Query Service two days later and are left out.
- **A live source.** The constraints come from the live Query Service, which serves only the main graph since
  scholarly articles were split off in 2025 [R02 §1]; a refetch gives a new snapshot. The one used is deposited.
- **New software.** Mitigated by certificates validated on the input, brute-force oracles and solver agreement in the
  tests, and one independent review (Section 3.4).

# 7. Related work

**Acyclicity of schemes.** Fagin introduced the β and γ degrees beside α and characterised scheme properties by them
[1]; Beeri et al. showed several desirable scheme properties equivalent to α-acyclicity [2]. Brault-Baron re-derives
the degrees, Berge included, and their polynomial tests in one framework [3]; α-acyclicity is decidable in linear
time [4], and γ has a join-tree characterisation with disjoint branches [5, 3].

**Width measures.** Hypertree width is checkable in polynomial time for fixed *k* [7]; ghw ≤ hw ≤ 3·ghw + 1 [8];
fractional hypertree width refines both [9]. Checking ghw ≤ *k* is NP-complete for *k* ≥ 3 [10] and for *k* = 2, where
fhw ≤ 2 is too, with tractable cases such as bounded intersection [11]. Exact exponential-time computation of ghw and
fhw over elimination orderings is due to [12]; bounded submodular width characterises fixed-parameter tractability,
assuming the Exponential Time Hypothesis [30].

**Benchmarks and solvers.** HyperBench measured widths of thousands of queries and constraint problems and found every
non-random query to have hw ≤ 3 [14, 15]; its runs are published [16]. BalancedGo [17] and log-k-decomp [18] compute
hypertree decompositions in parallel; SAT and SMT encodings give exact hw, ghw [19] and fhw [20]. Seven such tools,
run on eleven instances for this work, agreed wherever each was exact, but a misparse and a "correct" output that
broke the special condition were seen [R01 §4.4–4.5]; hence every result is validated.

**The Wikidata data model.** A Wikidata statement has one main snak, zero or more qualifier snaks, references and a
rank [22, 23, 25]; constraints such as *allowed qualifiers* are statements on property entities [24], the nearest
thing Wikidata has to a declared relation-type schema. Biolink declares its qualifiers in one LinkML file [29].

# 8. Availability

**The checker.** `khg-width` 0.1.0, MIT, at `projects/p6-schema-width/khg-width/` in
https://github.com/pluton74mac/knowledge-Hyper-Graphs- (commit `[COMMIT]`). Pure Python (≥ 3.10);
`khg-width SCHEMA_FILE [--slots core,qualifier[,time]] [--time-limit S] [--solver auto|python|balancedgo|logk]
[--json]` prints the class with its witness and the four widths with their methods, and `--json` the full report with
decompositions. A script builds the optional solvers from pinned commits; without them results are Python-only and
still sound. The survey scripts regenerate the schema files and re-run every row.

**Data statement.** The Wikidata Query Service is live and cannot return the same bytes again, so the snapshot used is
deposited: Zenodo, `[DOI to be assigned]`, CC0-1.0, like Wikidata's structured data [26]. The deposit holds the raw
query results of 2026-09-24 and the Biolink v4.4.5 sources with sha256 manifests, the qualifier-usage counts from the
dump of 2026-09-22, the thirteen generated schema files with provenance, the per-row reports (certificates, lower-bound witnesses, every solver attempt), the survey table, the
figure and the solver log. HyperBench's data [16] (CC BY 4.0) is referenced, not redistributed.

<!-- OWNER: if the deposit also carries the SQID and DeltaBot files (RELEASE.md, decision D1), say so here with their
     licences. -->

# References

[1] R. Fagin. Degrees of acyclicity for hypergraphs and relational database schemes. *Journal of the ACM* 30(3):514–550, 1983. https://doi.org/10.1145/2402.322390

[2] C. Beeri, R. Fagin, D. Maier, M. Yannakakis. On the desirability of acyclic database schemes. *Journal of the ACM* 30(3):479–513, 1983. https://doi.org/10.1145/2402.322389

[3] J. Brault-Baron. Hypergraph acyclicity revisited. *ACM Computing Surveys* 49(3), 2016. https://doi.org/10.1145/2983573 ; arXiv:1403.7076

[4] R. E. Tarjan, M. Yannakakis. Simple linear-time algorithms to test chordality of graphs, test acyclicity of hypergraphs, and selectively reduce acyclic hypergraphs. *SIAM Journal on Computing* 13(3):566–579, 1984. https://doi.org/10.1137/0213035

[5] D. Duris. Some characterizations of γ and β-acyclicity of hypergraphs. *Information Processing Letters* 112(16):617–620, 2012. https://doi.org/10.1016/j.ipl.2012.05.005

[6] A. D'Atri, M. Moscarini. Acyclic hypergraphs: their recognition and top-down vs bottom-up generation. Technical Report R.29, IASI-CNR, 1982. Cited through [3]; not read `[unverified]`.

[7] G. Gottlob, N. Leone, F. Scarcello. Hypertree decompositions and tractable queries. *Journal of Computer and System Sciences* 64(3):579–627, 2002. https://doi.org/10.1006/jcss.2001.1809 ; arXiv:cs/9812022

[8] I. Adler, G. Gottlob, M. Grohe. Hypertree width and related hypergraph invariants. *European Journal of Combinatorics* 28(8):2167–2181, 2007. https://doi.org/10.1016/j.ejc.2007.04.013 (result cited through [9]; not read directly)

[9] M. Grohe, D. Marx. Constraint solving via fractional edge covers. *ACM Transactions on Algorithms* 11(1), article 4, 2014. https://doi.org/10.1145/2636918 ; arXiv:1711.04506

[10] G. Gottlob, Z. Miklós, T. Schwentick. Generalized hypertree decompositions: NP-hardness and tractable variants. *Journal of the ACM* 56(6), article 30, 2009. https://doi.org/10.1145/1568318.1568320

[11] G. Gottlob, M. Lanzinger, R. Pichler, I. Razgon. Complexity analysis of generalized and fractional hypertree decompositions. *Journal of the ACM* 68(5):1–50, 2021. https://doi.org/10.1145/3457374 ; arXiv:2002.05239

[12] L. Moll, S. Tazari, M. Thurley. Computing hypergraph width measures exactly. *Information Processing Letters* 112(6):238–242, 2012. https://doi.org/10.1016/j.ipl.2011.12.002 ; arXiv:1106.4719

[13] G. Gottlob, M. Samer. A backtracking-based algorithm for hypertree decomposition. *ACM Journal of Experimental Algorithmics* 13, 2008. https://doi.org/10.1145/1412228.1412229 ; arXiv:cs/0701083

[14] W. Fischl, G. Gottlob, D. M. Longo, R. Pichler. HyperBench: a benchmark and tool for hypergraphs and empirical findings. *PODS 2019*, pp. 464–480. https://doi.org/10.1145/3294052.3319683 ; arXiv:1811.08181

[15] W. Fischl, G. Gottlob, D. M. Longo, R. Pichler. HyperBench: a benchmark and tool for hypergraphs and empirical findings. *ACM Journal of Experimental Algorithmics* 26:1–40, 2021. https://doi.org/10.1145/3440015 ; arXiv:2009.01769

[16] G. Gottlob, M. Lanzinger, C. Okulmus, R. Pichler. Experimental data for log-k-decomp. Zenodo, version 4, 2023, CC BY 4.0. https://doi.org/10.5281/zenodo.7180787

[17] G. Gottlob, C. Okulmus, R. Pichler. Fast and parallel decomposition of constraint satisfaction problems. *Constraints* 27(3):284–326, 2022. https://doi.org/10.1007/s10601-022-09332-1 . Software: BalancedGo, commit `872c662`, https://github.com/cem-okulmus/BalancedGo

[18] G. Gottlob, M. Lanzinger, C. Okulmus, R. Pichler. Fast parallel hypertree decompositions in logarithmic recursion depth. *PODS 2022*, pp. 325–336. https://doi.org/10.1145/3517804.3524153 ; arXiv:2104.13793. Software: log-k-decomp v1.1.0, https://github.com/cem-okulmus/log-k-decomp

[19] A. Schidler, S. Szeider. Computing optimal hypertree decompositions with SAT. *Artificial Intelligence* 325:104015, 2023. https://doi.org/10.1016/j.artint.2023.104015

[20] J. K. Fichte, M. Hecher, N. Lodha, S. Szeider. An SMT approach to fractional hypertree width. *CP 2018*, LNCS, pp. 109–127. https://doi.org/10.1007/978-3-319-98334-9_8

[21] A. Bonifati, W. Martens, T. Timm. Navigating the maze of Wikidata query logs. *WWW 2019*, pp. 127–138. Figures quoted through [15], `[unverified]` against the original; no URL recorded in our sources.

[22] D. Vrandečić, M. Krötzsch. Wikidata: a free collaborative knowledgebase. *Communications of the ACM* 57(10):78–85, 2014. https://doi.org/10.1145/2629489

[23] MediaWiki. Wikibase/DataModel. Checked 2026-09-19. https://www.mediawiki.org/wiki/Wikibase/DataModel

[24] Wikidata. Help:Property constraints portal/Qualifiers (the allowed-qualifiers constraint). Read 2026-09-24. https://www.wikidata.org/wiki/Help:Property_constraints_portal/Qualifiers ; Wikidata Query Service, https://query.wikidata.org/

[25] Wikidata. Help:Qualifiers. Read 2026-09-24. https://www.wikidata.org/wiki/Help:Qualifiers

[26] Wikidata. Wikidata:Copyright (structured data under CC0). Read 2026-09-24. https://www.wikidata.org/wiki/Wikidata:Copyright

[27] SQID. Property statistics, `properties.json` (qualifier counts from the dump of 2026-08-10). https://sqid.toolforge.org/data/properties.json

[28] Wikidata. Template:Number of main statements by property, revision 2548855541 by DeltaBot, 2026-09-23. https://www.wikidata.org/wiki/Template:Number_of_main_statements_by_property

[29] D. R. Unni et al. Biolink Model: a universal schema for knowledge graphs in clinical, biomedical, and translational science. *Clinical and Translational Science* 15(8):1848–1855, 2022. https://doi.org/10.1111/cts.13302 . Model v4.4.5, commit `a4180f8`, https://github.com/biolink/biolink-model

[30] D. Marx. Tractable hypergraph properties for constraint satisfaction and conjunctive queries. *Journal of the ACM* 60(6), article 42, 2013. https://doi.org/10.1145/2535926 ; arXiv:0911.0801

[31] P. D. Thomas et al. Gene Ontology Causal Activity Modeling (GO-CAM) moves beyond GO annotations to structured descriptions of biological functions and systems. *Nature Genetics*, 2019. https://doi.org/10.1038/s41588-019-0500-1

[32] Wikimedia. Wikidata JSON dump `wikidata-20260922-all.json.bz2` (dump directory 20260921; md5 `7f70e4a1858ba6182ea9329a1ef588c5`), CC0-1.0. https://dumps.wikimedia.org/wikidatawiki/entities/20260921/wikidata-20260922-all.json.bz2

**Project documents** (in the repository at the commit above): [R01] `projects/p6-schema-width/research/01-theory-and-solvers.md`; [R02] `projects/p6-schema-width/research/02-data-sources-and-naming.md`; the naming `projects/p6-schema-width/wd-roles.md` (r1); the design `projects/p6-schema-width/DESIGN.md`.
