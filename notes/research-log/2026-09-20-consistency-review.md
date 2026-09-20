---
title: Consistency and fact-check review of kb/ (cross-section pass)
type: log
status: reviewed
tags: [log, review, consistency, fact-check, contradictions, unverified]
created: 2026-09-20
updated: 2026-09-20
---

# Consistency and fact-check review — 2026-09-20

A single reviewer pass over `kb/` after ten section authors wrote in parallel. Goal: make claims that
appear in more than one section agree with each other and with their primary sources, fix
misattributions, and record what could not be settled.

## Method

1. Read every section `README.md`; read the claim-dense notes in full (sections 02, 04, 08, 09, 10
   and the RAG notes in 03 and 07); used targeted search over the remaining notes for every
   repeated numeric claim, date, venue and attribution.
2. Built a frequency index of every percentage, version string and author-year token in `kb/`, and
   inspected every value that occurs in two or more sections.
3. Fetched primary sources where two notes disagreed and neither cited a fetched source
   (`Wikidata:Statistics`, `arXiv:2608.22135`).
4. Made surgical edits in place; bumped `updated:` to 2026-09-20 on every file touched.
5. Re-ran `python3 tools/validate_kb.py --strict`.

**39 `kb/` files edited**, plus `tools/build_index.py`, the regenerated `kb/00-index/map-of-content.md`, and this log.

---

## Part A — Contradictions found and how they were resolved

### A1. JF17K 44.5% test leakage — attribution

Checked all 16 occurrences of `44.5%`. **No note misattributed the figure**: every occurrence already
credits Galkin, Trivedi, Maheshwari, Usbeck and Lehmann (StarE, EMNLP 2020), and
`kb/09-ecosystem/dataset-quality-and-leakage-issues.md` §1 carries the explicit correction (the HINGE
full text was searched on 2026-09-20 for `leak` and `redundan`; neither occurs). One note hedged the
result unnecessarily:

- `kb/08-history-and-frontier/machine-learning-era.md`
  - old: "the *specific* flaws are discussed in the paper rather than the abstract, so attribute the
    detailed leakage claims to the full text, not to the abstract `[unverified]` in this run."
  - new: states that the flaws are in §5 of the body, quotes the two decisive figures (44.5%; "less
    than 3%"), cross-links the section-09 verification, and adds: "the 44.5% result is **Galkin et
    al.'s (StarE, EMNLP 2020)**, not Rosso et al.'s (HINGE, WWW 2020)." `[unverified]` removed.

### A2. Fact-level proportion of n-ary / hyper-relational facts

The three WikiPeople numbers are three *different quantities on three different files*. Sections 02
and 09 already reconciled them; sections 03, 05 and 10 quoted one number each without saying which.

- `kb/10-comparative-and-critique/limitations-and-failure-modes.md` §1 — added a paragraph naming
  each quantity: **11.6%** = share of n-ary facts in WikiPeople as released (Wei et al. 2025,
  Table 1); **2.6%** = share of hyper-relational facts in the literal-filtered release (Rosso et al.
  2020, Table 1: 7,389/287,918 train, 971/37,586 test); **"less than 3% of the remaining statements
  contain any qualifier pairs"** = Galkin et al.'s prose for that same post-filtering quantity, so
  2.6% and "<3%" agree while 11.6% is a different file. WD50K's **13.6%** = 32,167/236,507 statements
  with at least one qualifier (Galkin et al., Table 1), the figure their prose rounds to "about 14%".
- `kb/03-construction/from-knowledge-graphs-to-hypergraphs.md`
  - old: `n-ary facts are "less than 12%" of the data.`
  - new: `**11.6% n-ary facts** over the whole release (44,315 of 382,229) — the same figure the 2025
    survey reports`, followed by an explicit contrast with the 2.6% / "<3%" post-literal-filtering
    quantity and a link to the section-09 reconciliation.
- `kb/07-applications/applications-overview.md`
  - old: "236,507 Wikidata statements, about 14 % of which carry at least one qualifier pair"
  - new: "236,507 Wikidata statements, 32,167 of which (**13.6 %**, the figure Galkin et al. round to
    'about 14%' in prose) carry at least one qualifier pair"
- `kb/02-knowledge-representation/wikidata-and-freebase-data-models.md` §4
  - old: bare bullets `Freebase: "more than 1/3 of the entities …"` and `in WD50K "about 14% of
    statements …"`.
  - new: each bullet is labelled with the quantity it measures — **"measured over entities, not
    facts"** vs **"measured over statements"** — the Freebase figure is additionally attributed to
    Wen et al. 2016, Rosso et al. 2020 and Fatemi et al. 2020, and the note now states that an
    entity-level share does not bound the fact-level share, linking to `10/limitations` §1.
    (Fatemi et al. 2020 added to that note's `## Sources`.)
- `kb/00-index/README.md`
  - old: `The motivating "one third of facts are n-ary" statistic is misread.`
  - new: `The motivating "more than one third" statistic is about **entities that participate in a
    non-binary relation**, not about facts, and is routinely misread as the latter; the fact-level
    shares are 11.6–13.6% in the Wikidata-derived benchmarks.`

### A3. "Reification loses information" — false per Fatemi et al. 2020

- `kb/05-query-embeddings-reasoning/README.md`, finding 3
  - old: `**Reification is measurably lossy.** r-SimplE scores JF17K MRR 0.102 against HypE's 0.494 …`
  - new: `**Reification is information-preserving but learning-hostile.**` — quotes Fatemi et al.
    ("the binary relations created are equivalent to the original representation and reification does
    not lose information during conversion"), keeps the measured learning cost, and states that
    *star-to-clique*, not reification, is the lossy conversion, with a link to `10/limitations` §2.

All other occurrences were already correct (`10/formalism-comparison-matrix.md` row "Lossless as a
representation"; `10/limitations-and-failure-modes.md` §2 "This is a failure of a learning method,
not of a representation"; `02/hyper-relational-vs-n-ary-vs-hypergraph.md` §2;
`10/hypergraph-vs-bipartite-graph-debate.md` §4).

### A4. HYPER (Huang, Galkin, Bronstein, Ceylan 2025) — ambiguous venue

Section 08 hedged correctly (NeurIPS 2025 "New Perspectives in Graph Machine Learning" workshop
presentation; the authors' repository states ICLR 2026). Four other mentions gave a bare year. All
now carry the same hedge.

- `kb/05-query-embeddings-reasoning/inductive-and-few-shot-settings.md`, `.../hypergraph-neural-networks.md`
  - old: `arXiv:2506.12362, 2025.`
  - new: `arXiv:2506.12362, 14 Jun 2025. Venue: presented at the NeurIPS 2025 "New Perspectives in
    Graph Machine Learning" workshop …; the authors' repository states ICLR 2026 …. Cite it as an
    arXiv preprint until one of the two is confirmed.`
- `kb/08-history-and-frontier/timeline.md` — the 2025 (Jun) row and the source line now both say
  "NeurIPS 2025 workshop presentation; repository states ICLR 2026 — venue unsettled".
- `kb/08-history-and-frontier/research-groups-and-people.md`
  - old: `HYPER (2025).`  new: `HYPER (arXiv, Jun 2025; NeurIPS 2025 workshop presentation,
    repository states ICLR 2026).`

### A5. Hyper-RAG publication

Canonical form: **arXiv:2504.08758, 30 Mar 2025; *Nature Communications* 17(1):5778, 27 April 2026,
DOI 10.1038/s41467-026-71411-1** (verified by section 08 via Crossref). Thirteen bibliographic
entries gave partial forms ("arXiv 2025" only, "Nature Communications, 2026", "Nature Communications
17", "17:5778, 2026"). All normalised in:
`02/what-is-a-knowledge-hypergraph.md`, `03/llm-based-khg-construction.md`,
`03/construction-pipeline-overview.md`, `03/schema-induction-and-ontology-alignment.md`,
`04/property-graph-emulation-patterns.md`, `07/applications-overview.md`,
`07/retrieval-augmented-generation.md`, `07/case-studies.md`, `07/biomedical-and-life-sciences.md`,
`07/finance-legal-and-compliance.md`, `08/timeline.md`, `08/research-groups-and-people.md`,
`09/datasets-and-benchmarks.md`, `09/dataset-quality-and-leakage-issues.md`,
`10/open-debates.md`. In `10/critical-reading-of-hypergraph-rag-claims.md` the venue cell
- old: `arXiv, submitted 30 Mar 2025`
- new: `arXiv, submitted 30 Mar 2025; published as *Nature Communications* 17(1):5778, 27 Apr 2026`.

The duplicate "arXiv" + "Nature Communications" source pairs in three section-07 notes were merged
into one entry each.

### A6. HyperGraphRAG

Venue (**NeurIPS 2025**), arXiv id (**2503.21322**), per-domain gains (+7.45 F1 / +7.62 R-S / +3.69
G-E over StandardRAG; +8.6 binary vs +5.3 n-ary) and cost figures (3.084 s and $0.0063 per 1k tokens;
$3.184 per 1k queries) were already consistent across sections 02–10. Four source lines said only
"arXiv 2503.21322, 2025"; they now say "NeurIPS 2025; arXiv:2503.21322":
`03/hypergraph-construction-from-data.md`, `03/incremental-and-streaming-construction.md`,
`03/evaluation-of-constructed-khgs.md`, `03/schema-induction-and-ontology-alignment.md`.

### A7. PRoH figure and year

- `kb/08-history-and-frontier/timeline.md` — old `+19.7% F1 over HyperGraphRAG` → new `+19.73% F1`
  (the paper's own figure, as quoted in five other notes).
- `kb/07-applications/applications-overview.md` — old `[Zai et al., 2026]` → new `[Zai et al., 2025]`
  (arXiv:2510.12434 is 14 Oct 2025; every other note says 2025), and the source line now gives the
  arXiv date alongside WWW 2026.

### A8. RDF 1.2 status

Canonical form: Concepts **and Semantics** at Candidate Recommendation **Snapshot**, 7 April 2026;
all syntaxes and the whole SPARQL 1.2 suite still Working Drafts as of September 2026; WG chartered
to 2027-04-30.

- `kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md` §1 — added the missing
  **RDF 1.2 Semantics** row, a sentence stating that only the two data-model documents are at CR
  Snapshot, and the **charter end 30 April 2027**; added the Semantics and WG group page to `## Sources`.
- `kb/09-ecosystem/standards-bodies-and-specifications.md` — old `**Candidate Recommendation**` (two
  table rows and the summary row) → new `**Candidate Recommendation Snapshot**`.
- `kb/08-history-and-frontier/standards-convergence.md` summary table — old "Concepts + Semantics at
  **Candidate Recommendation**, 7 Apr 2026; syntaxes and SPARQL 1.2 Query still Working Drafts" →
  new "…**Candidate Recommendation Snapshot**…; all syntaxes and SPARQL 1.2 still Working Drafts as
  of Sep 2026; WG chartered to 2027-04-30".
- `kb/08-history-and-frontier/README.md` and `kb/02-knowledge-representation/README.md` — same
  wording fix ("CR, April 2026" → "Candidate Recommendation Snapshot, 7 April 2026").

### A9. GQL and SQL/PGQ

ISO/IEC 39075:2024 published 12 April 2024, property graphs without n-ary relationships; SQL/PGQ =
ISO/IEC 9075-16:2023, Part 16 of SQL:2023. Checked all mentions in sections 04, 08, 09 and 10.
**No contradictions found; nothing changed.**

### A10. HIF — schema version

- `kb/08-history-and-frontier/standards-convergence.md` summary table
  - old: `v1 schema; paper in *Network Science* 13:e21, 2025`
  - new: `schema **v0.0** (the only \`CHANGELOG.md\` entry; the schema itself carries
    \`"version": "latest"\`, so files cannot declare a version); paper in *Network Science* 13:e21, 2025`
  This matches the verified statement in `09/standards-bodies-and-specifications.md` §4,
  `09/software-libraries.md` caveat 2 and `04/hif-hypergraph-interchange-format.md` §4.
- `kb/04-storage-and-formats/hif-hypergraph-interchange-format.md` — repository naming harmonised
  with section 09 (HIF-org is the current home, `pszufe` the earlier one, several tools still fetch
  the `pszufe` schema URLs), and the round-trip finding imported: **only XGI 0.10.2 preserves
  `direction`**; HyperNetX 2.4.3 drops it; Hypergraphx 1.8.0 re-indexes node ids to integers. Coll
  et al. 2025, *Network Science* 13:e21 is cited identically in all six notes that mention it.

### A11. Phil Chodrow is not an XGI core developer

`08/research-groups-and-people.md` already carries the verified correction. One other mention listed
him in the same breath as the XGI team:

- `kb/08-history-and-frontier/current-frontier-directions.md` §7
  - old: `Maxime Lucas, Leo Torres and the XGI team; Phil Chodrow (Middlebury College);`
  - new: `… Phil Chodrow (Middlebury College — a separate node in the same community, **not** an XGI
    author or core developer);`

(The same "Who" line previously gave Nicholas Landry's affiliation as University of Vermont against
University of Virginia in `research-groups-and-people.md`; it read *Virginia* by the time this pass
reached it, so no edit was needed.)

### A12. DocTrace

`07/software-engineering-and-code-knowledge.md` §3 carries the verified correction (multi-agent
long-document QA with on-demand hypergraph working memory, not repository-level code RAG). Checked
all eight other mentions (`07/ai-agents-memory-and-planning.md`, `07/applications-overview.md`
matrix, `08/timeline.md`, `08/llm-era-2023-2026.md`, `08/current-frontier-directions.md`,
`08/research-groups-and-people.md`, `kb/00-index/glossary.md`, `sources/by-topic/`). **All describe
it correctly; nothing changed.**

### A13. GrOIL — previously flagged unverified, now verified

Verified by web search plus a fetch of the arXiv abstract page on 2026-09-20.

- `kb/07-applications/applications-overview.md`
  - old matrix cell: `◐ GrOIL (insurance contracts)`, no citation, no source entry.
  - new: `◐ GrOIL (life-insurance contracts)` plus a note under the matrix — a seven-stage pipeline
    inducing an OWL TBox and ABox from life-insurance contract documents, encoding each document as a
    "Unified Discourse-Hypergraph (UDH)" first; **ontology induction over a document hypergraph, not
    an n-ary fact store** — and a new `## Sources` entry: Mridul, M. A., Talukder, A., Seneviratne,
    O. *GrOIL: Graph-Grounded Domain Ontology Induction with Constrained LLM Mediation.*
    arXiv:2608.22135, 22 Aug 2026.

### A14. Berge book dates

Canonical: 1970 *Graphes et hypergraphes* (Dunod); 1973 *Graphs and Hypergraphs* (North-Holland,
trans. Minieka); 1987 *Hypergraphes: combinatoire des ensembles finis* (Gauthier-Villars); 1989
*Hypergraphs: Combinatorics of Finite Sets* (North-Holland Mathematical Library 45).

- `kb/08-history-and-frontier/timeline.md`
  - old: `| 1969–1970 | Claude Berge, *Graphes et hypergraphes*, Dunod (Paris) |`
  - new: `| 1970 | Claude Berge, *Graphes et hypergraphes*, Dunod (Paris); the idea itself dates from
    "around 1960" by Berge's own account |` (matches `origins-hypergraph-theory.md` §1.1–1.2).
  - old: `… North-Holland, 1989 \`[unverified]\` year of English edition …` and the French title
    spelled *combinatoires*.
  - new: `… North-Holland Mathematical Library 45, **1989**)` with the title spelled *combinatoire*
    (as in `origins-hypergraph-theory.md`) and the Internet Archive catalogue record cited;
    `[unverified]` removed, because section 08 verified the imprint and the "Translation of:
    Hypergraphes" statement.

Sections 01 and 09 already used 1970/1973/1989 consistently.

### A15. Wikidata statistics

Three different item counts were in circulation. `Wikidata:Statistics` was fetched on 2026-09-20:
123,419,629 items, 2,547,303,553 edits, 43,497 active users.

- `kb/02-knowledge-representation/wikidata-and-freebase-data-models.md`
  - old: `On 31 August 2025 it reported 123,378,383 items`
  - new: the live-counter reading of 2026-09-20 with all three figures, a note that
    `03/curation-crowdsourcing-and-quality.md` records 123,419,051 items from a read a few hours
    earlier, and an explicit statement that the "31 August 2025" date could not be re-verified and
    has been replaced. Source line updated to "live counter, read 2026-09-20".
- `kb/04-storage-and-formats/versioning-provenance-and-scale.md`
  - old: `123,411,810 items (figure dated 31 August 2025 on the statistics page, checked 2026-09-20)`
  - new: `~123.4 million items (live counter read 2026-09-20: 123,419,629 items, 2,547,303,553 edits,
    43,497 active users; a dated snapshot table on the same page read 123,411,810, whose stated date
    could not be confirmed \`[unverified]\`)`.
- `kb/03-construction/curation-crowdsourcing-and-quality.md` — verbatim quote kept, with a note that
  the counter is live and a same-day re-read gave 123,419,629 / 2,547,303,553.

### A16. WD50K(33) validation-split size

- `kb/03-construction/from-knowledge-graphs-to-hypergraphs.md`
  - old: `| WD50K(33) | 102,107 | 31.2% | 38,124 | 475 | 73,406 / 10,668 / 18,133 |`
  - new: `… 73,406 / 10,568 / 18,133`. 73,406 + 10,568 + 18,133 = 102,107 (the stated total);
    10,668 does not sum. Matches Galkin et al., Table 1 as transcribed in
    `02/benchmarks-derived-from-freebase-and-wikidata.md` and `09/datasets-and-benchmarks.md`.

### A17. Section 05 README stale statement

- `kb/05-query-embeddings-reasoning/README.md`
  - old: `Storage and indexing … belong to section 04, which is empty as of writing.`
  - new: links to section 04, which now has ten notes.

### A18. Section README completeness (task item 4)

- `kb/02-knowledge-representation/README.md` did not list
  `metagraphs-atomspace-and-hypergraphdb.md`, which is present. A table row was added.
- `kb/00-index/README.md` listed `map-of-content.md`, `glossary.md` and `open-questions.md`, none of
  which existed when the pass began; `glossary.md` and `open-questions.md` were written during the
  pass by the index author, and `map-of-content.md` was generated with the repository's own
  `tools/build_index.py` rather than removed from the index, since the README documents it as a
  generated file.
- All other nine section READMEs list exactly the notes present in their directory, and nothing
  absent. Verified mechanically by diffing each README's relative `*.md` link targets against the
  directory listing.

### A18b. `tools/build_index.py` produced an invalid index

Running the generator as-is produced eight broken links and one missing-`## Sources` warning: it
copies a note's opening paragraph verbatim into `kb/00-index/`, where a relative link such as
`(visual-encodings-catalogue.md)` no longer resolves. Two surgical fixes to the script:

- added `flatten_links()`, which reduces an inline Markdown link in a copied summary to its link
  text, so the index keeps the label and drops the unresolvable target;
- the generated file now ends with a `## Sources` section stating that it is generated and that each
  listed note carries its own citations.

`python3 tools/build_index.py` now emits a `map-of-content.md` that passes `--strict`.

### A19. Terminology (task item 3)

Checked "knowledge hypergraph (KHG)", "hyper-relational knowledge graph", "n-ary fact", "hyperedge",
"incidence", "role" and "qualifier" against
`02/hyper-relational-vs-n-ary-vs-hypergraph.md` and `01/notation-cheatsheet.md`. Searched for the
usual drift spellings (`hyperrelational`, `hyper relational`, `nary`, `n ary`, `hyper edge`,
`hyper-edge`): **zero hits**. The abbreviation `KHG` is introduced on first use in every note that
uses it. **No terminology edits were needed.**

### A20. AI model names used as authorship (task item 5)

`grep -rniE "claude|anthropic|gpt-4|gpt-5|openai|gemini|sonnet|opus" kb sources schemas datasets`
returns 8 lines, all of which are **Claude Berge** (the mathematician) in sections 08 and 09 and in
`sources/by-topic/08-history-and-frontier.md`. No AI model name is used as an author anywhere, and no
mention of a model as an experimental subject needed removing. **Nothing removed.**

---

## Part B — Claims left as explicit disagreement

1. **The "31 August 2025" Wikidata snapshot date.** Two notes carried a dated snapshot
   (123,378,383 and 123,411,810 items) that implies almost no growth over thirteen months against a
   live count of 123,419,629 on 2026-09-20. The snapshot date is probably a misreading, but the page
   does carry a dated table, so the figure is retained in
   `04/versioning-provenance-and-scale.md` marked `[unverified]` beside the live reading rather than
   deleted.
2. **JF17K relation counts: 322 vs 327 vs 501.** Recorded as a genuine disagreement between Rosso et
   al. 2020, Fatemi et al. 2020 and Wei et al. 2025, with the relations-vs-roles explanation, in
   `02/benchmarks-derived-from-freebase-and-wikidata.md` §0 and `09/dataset-quality-and-leakage-issues.md`
   §4. Not resolvable without re-deriving the datasets. Left as stated disagreement.
3. **WD50K entity/relation off-by-one (47,156/532 vs 47,155/531).** Unexplained in the sources
   consulted; left `[unverified]` in `02/benchmarks-derived-from-freebase-and-wikidata.md` §0.
4. **HYPER's venue.** NeurIPS 2025 workshop page and the authors' repository ("ICLR 2026") both
   verified and both retained; the KB now says so identically in all six places rather than choosing
   one. Re-check after the ICLR 2026 proceedings appear.
5. **Elsevier's 1984 publication date for *Hypergraphs: Combinatorics of Finite Sets*.** Contradicts
   every library record and the 1987 French original; kept in
   `08/origins-hypergraph-theory.md` as an explicitly flagged publisher metadata error.
6. **Does decomposition to binary cost accuracy?** Fatemi et al. 2020 say yes, Wang et al. (CIKM
   2025) find decomposed standard models competitive. Both are cited side by side in
   `02/hyper-relational-vs-n-ary-vs-hypergraph.md` §2 and in `kb/00-index/open-questions.md` [02.4];
   the JF17K leak confounds it. Left open, not reconciled.
7. **`email-Enron` (148 vs 84,172 nodes) and `walmart-trips` (65,979 vs 69,906 hyperedges).**
   Catalogue-level disagreement between XGI-DATA, hypergraphx-data and AllSet, recorded as such in
   `09/dataset-quality-and-leakage-issues.md` §4.

---

## Part C — Remaining `[unverified]` items by section

Counted as occurrences of the literal marker `[unverified]` after this pass (223 in 73 files).

| Section | `[unverified]` markers | Files carrying at least one |
|---|---|---|
| 00-index | 0 | 0 |
| 01-foundations | 35 | 8 |
| 02-knowledge-representation | 13 | 6 |
| 03-construction | 7 | 6 |
| 04-storage-and-formats | 9 | 4 |
| 05-query-embeddings-reasoning | 9 | 6 |
| 06-visualization | 48 | 9 |
| 07-applications | 14 | 9 |
| 08-history-and-frontier | 30 | 7 |
| 09-ecosystem | 31 | 7 |
| 10-comparative-and-critique | 27 | 8 |
| **Total** | **223** | **70** |

Heaviest single files: `06/tools-and-libraries.md` (18 — mostly unfetched version dates for
commercial and LaTeX tooling), `08/research-groups-and-people.md` (17 — affiliations not confirmed
from personal pages), `09/datasets-and-benchmarks.md` (11 — licences and dataset provenance),
`10/critical-reading-of-hypergraph-rag-claims.md` (10 — ACM pages that returned HTTP 403, and
experiments the papers do not report).

Two markers were **removed** in this pass because another section had verified the claim: the Berge
1989 English edition (`08/timeline.md`) and the StarE leakage-claim location
(`08/machine-learning-era.md`). One marker was **added**: the Wikidata snapshot date in
`04/versioning-provenance-and-scale.md`. The GrOIL cell in `07/applications-overview.md` moved from
unflagged-and-uncited to verified-and-cited.

---

## Part D — Files edited (39)

`kb/00-index/README.md` ·
`kb/02-knowledge-representation/README.md` ·
`kb/02-knowledge-representation/what-is-a-knowledge-hypergraph.md` ·
`kb/02-knowledge-representation/wikidata-and-freebase-data-models.md` ·
`kb/03-construction/construction-pipeline-overview.md` ·
`kb/03-construction/curation-crowdsourcing-and-quality.md` ·
`kb/03-construction/evaluation-of-constructed-khgs.md` ·
`kb/03-construction/from-knowledge-graphs-to-hypergraphs.md` ·
`kb/03-construction/hypergraph-construction-from-data.md` ·
`kb/03-construction/incremental-and-streaming-construction.md` ·
`kb/03-construction/llm-based-khg-construction.md` ·
`kb/03-construction/schema-induction-and-ontology-alignment.md` ·
`kb/04-storage-and-formats/hif-hypergraph-interchange-format.md` ·
`kb/04-storage-and-formats/property-graph-emulation-patterns.md` ·
`kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md` ·
`kb/04-storage-and-formats/versioning-provenance-and-scale.md` ·
`kb/05-query-embeddings-reasoning/README.md` ·
`kb/05-query-embeddings-reasoning/hypergraph-neural-networks.md` ·
`kb/05-query-embeddings-reasoning/inductive-and-few-shot-settings.md` ·
`kb/07-applications/applications-overview.md` ·
`kb/07-applications/biomedical-and-life-sciences.md` ·
`kb/07-applications/case-studies.md` ·
`kb/07-applications/finance-legal-and-compliance.md` ·
`kb/07-applications/retrieval-augmented-generation.md` ·
`kb/08-history-and-frontier/README.md` ·
`kb/08-history-and-frontier/current-frontier-directions.md` ·
`kb/08-history-and-frontier/machine-learning-era.md` ·
`kb/08-history-and-frontier/research-groups-and-people.md` ·
`kb/08-history-and-frontier/standards-convergence.md` ·
`kb/08-history-and-frontier/timeline.md` ·
`kb/09-ecosystem/dataset-quality-and-leakage-issues.md` ·
`kb/09-ecosystem/datasets-and-benchmarks.md` ·
`kb/09-ecosystem/standards-bodies-and-specifications.md` ·
`kb/10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md` ·
`kb/10-comparative-and-critique/limitations-and-failure-modes.md` ·
`kb/10-comparative-and-critique/open-debates.md`

Plus `tools/build_index.py` (two fixes, see A18b), `kb/00-index/map-of-content.md` (regenerated) and this log.

---

## Validation

```
$ python3 tools/build_index.py
wrote kb/00-index/map-of-content.md (100 notes)

$ python3 tools/validate_kb.py --strict
checked 111 files: 0 errors, 0 warnings
```

Also re-checked at the end of the pass:

- every `kb/*/README.md` lists exactly the notes present in its directory (no missing, no absent);
- the four `kb/00-index/` targets referenced from the root `README.md` all exist;
- `grep -rniE "claude|anthropic|gpt-4|gpt-5|openai|gemini|sonnet|opus" kb sources schemas datasets`
  returns 10 lines, **all** of them the mathematician **Claude Berge**; nothing removed.

## Sources

Fetched during this review (all 2026-09-20):

- Wikidata. *Wikidata:Statistics* (live counter: 123,419,629 items; 2,547,303,553 edits; 43,497 active users). https://www.wikidata.org/wiki/Wikidata:Statistics
- Mridul, M. A., Talukder, A., Seneviratne, O. *GrOIL: Graph-Grounded Domain Ontology Induction with Constrained LLM Mediation.* arXiv:2608.22135, submitted 22 August 2026 (abstract page). https://arxiv.org/abs/2608.22135

Every other claim in this log is sourced from the note it corrects or from the note whose verified
statement was used as the reference; those notes carry the primary citations.
