---
title: "P6 release: the owner's steps for the note, the Zenodo deposit and the post"
type: project
status: draft
created: 2026-09-25
updated: 2026-09-25
---

# Releasing P6: the owner's steps

Nothing in this folder has been published, uploaded or submitted from a Claude session. PLAN §5 ships, for P6, a short
note with the survey table (arXiv or a workshop), the checker as a tool in the repository, and a post; ruling Q4
(DESIGN §9) adds a Zenodo deposit of the raw snapshot, prepared here and released by the owner.

| File | What it is |
|---|---|
| [note.md](note.md) | the note, Markdown for pandoc (YAML metadata, numbered sections, one table, one figure, numbered references) |
| [post.md](post.md) | the post, about 380 words |
| [zenodo/README.md](zenodo/README.md) | the deposit's README; `assemble.sh` fills in the commit, the optional files and a draft banner |
| [zenodo/metadata.json](zenodo/metadata.json) | the Zenodo deposition metadata (REST API format, top-level `metadata` key) |
| [zenodo/assemble.sh](zenodo/assemble.sh) | stages the deposit in a directory outside git and builds the two upload files; uploads nothing |

Order of release: **(1)** re-run the observed rows with P3a's counts and update the numbers (done 2026-09-25);
**(2)** reserve the Zenodo DOI; **(3)** submit the note; **(4)** publish the deposit; **(5)** publish the post.

## 0. Decisions for the owner

- **D1. SQID and DeltaBot files in the deposit** (revisited after the P3a-count re-run, 2026-09-25).
  - *What the deposit needs now.* No committed schema file depends on SQID or DeltaBot any more. The observed schemas
    are built from P3a's `projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json`, and the declared ones from
    the WDQS constraints alone. That file is statistics of the Wikidata JSON dump of 2026-09-22, derived from CC0 data
    and deposited under CC0 like the WDQS results. `assemble.sh` deposits it (item 4 of its header), and `--final`
    refuses when the observed rows use it and it is not tracked. Rebuilt with the SQID and DeltaBot data emptied, all
    ten Wikidata schema files came out byte-identical (IMPLEMENTATION-NOTES §8). So, as *data*, the SQID and DeltaBot
    files are no longer needed.
  - *What the scripts still need.* The generator still *reads* them: `khg_width.sources.wikidata.RAW_FILES` lists
    `sqid-properties.json` and `usage_main_statements.wikitext`, `run_survey.py generate` verifies them against the
    manifest, and `reproduce.sh` step 2 verifies all 38 files of the Wikidata manifest. A deposit without them can
    therefore re-validate and re-measure the committed schema files, but cannot regenerate them with the scripts as
    they stand. SQID overwrites its file, so it cannot be fetched again; the DeltaBot templates can, by revision id.
    Making the two files optional when `--p3a-counts` is given is a small change to the loader and the manifest
    check. It was not made here, because it changes a generator source whose hash every provenance file records.
  - *Why they stay out by default.* DESIGN §6.1 and `results/README.md` say SQID's statistics are "used, not
    redistributed", and SQID's repository states a licence for its code (Apache-2.0) but none for these data files
    (checked 2026-09-25). DESIGN §6.1 records the DeltaBot templates as Template-namespace text under CC BY-SA 3.0,
    which a CC0 record cannot relicense. `assemble.sh` adds them with `--with-sqid` and `--with-deltabot`.
  - *Sizes* (`assemble.sh --final` at commit `f4cb303`, 2026-09-25): default 127 files, 81.5 MB, zip 18.2 MB,
    status `final`, `SHA256SUMS` verified in the tree and inside the zip; with both flags 132 files, 166.1 MB, zip
    49.2 MB. (Before the re-run: 101 files, 60.1 MB, zip 10.6 MB.) The growth is the four slice schemas, their
    sixteen reports and logs, P3a's counts file (13.8 MB) and `p3a-crosscheck.json` (1.1 MB).
  - *The note* still cites DeltaBot's template [28] once, for the declared properties' share of main statements
    (1.27 of 1.79 billion, 71 %). P3a's counts give the same share over the 2026-09-22 dump (1.27 of 1.78 billion,
    71 %), if one count source is preferred; SQID [27] is cited only for the research probe.
  - *Options:* (a) keep the default (recommended): the deposit is complete as data, and regenerating from it alone
    needs the loader change above; (b) add the DeltaBot files, listing their CC BY-SA 3.0 in the README (the record's
    single licence field stays CC0); (c) add both after asking SQID's maintainers about terms.
- **D2. Authorship.** Name, affiliation and ORCID go in `note.md` (`author:`), `zenodo/metadata.json` (`creators`)
  and the deposit README's citation. No name or e-mail was written into any file. The repository URL in the note,
  README, metadata and post contains the GitHub account name; for a double-blind venue, replace it with an anonymous
  link.
- **D3. Venue** (section 3): arXiv cs.DB with a cs.AI cross-list now, a workshop later; no suitable workshop deadline
  is open on 2026-09-25.
- **D4. The note's licence on arXiv.** arXiv offers CC BY 4.0, CC BY-SA 4.0, CC BY-NC-SA 4.0, CC BY-NC-ND 4.0, its own
  non-exclusive licence and CC0, and the choice "is irrevocable" (info.arxiv.org/help/license, read 2026-09-25). CC BY
  4.0 matches the repository's licence for prose (`LICENSE-CONTENT.md`).
- **D5. Novelty.** No systematic literature search for earlier measurements was done; the note says so and marks the
  claim `[unverified]`, and the post makes no novelty claim. Do a short search before submitting if you want to claim
  it.
- **D6. HyperBench-derived numbers in a CC0 record.** `hyperbench-baseline.json` and the figure's HyperBench panel are
  aggregate counts recomputed from CC BY 4.0 run data; the README keeps the attribution. Keep them (recommended) or
  drop them from the deposit.
- **D7. Repository visibility.** Done: the repository was made public on 2026-09-25. The note, the deposit and the
  post link it.
- Note: DESIGN §8 named the post draft `post-draft.md`; this folder uses `post.md`, as asked.

## 1. The P3a-count re-run: done (2026-09-25, commit `c065478`)

The observed rows rested on SQID's counts (dump of 2026-08-10) over DeltaBot's (2026-09-23), and the draft marked
every number they produced with **†**. They were re-run on P3a's exact counts on 2026-09-25; the results are commit
`c065478`, the figure and deposit README `f4cb303`, the note, post and base `cb55a94`, and the rest of the base
`ace2ee6`. No † mark, PROVISIONAL box or provisional bullet is
left. The steps, kept for a repeat (IMPLEMENTATION-NOTES §8 has the details):

1. **P3a's file**: `projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json` (format `p3a-qualifier-usage/1`,
   naming `wd-roles r1`; DESIGN §2.5 and ruling Q9), committed as `13e5bdb`.
2. **Re-run the observed rows** (on a machine with the raw Wikidata files and the HyperBench zips, which step 2 of the
   script verifies):

   ```bash
   python3 -m venv .venv && . .venv/bin/activate
   pip install . "./projects/p6-schema-width/khg-width[survey,fast]"
   projects/p6-schema-width/khg-width/scripts/build-solvers.sh        # BalancedGo and log-k-decomp; needs Go
   projects/p6-schema-width/survey/reproduce.sh \
       --p3a-counts projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json --rows observed --jobs 3
   ```

   Done with `--jobs 2`, because the machine was shared with another session's database servers (each report and
   `results/machine.json` record the load): 03:33 to 05:56 UTC, 2 h 23 min, all 16 rows with status 0, 1,483 to
   2,534 s per wd-roles r1 row. The SQID-based observed files and their reports moved unchanged to
   `results/superseded/`, the P3a-based ones and the 8 slice rows were added, and `results/p3a-crosscheck.json` was
   written (its entries are two vocabulary differences, IMPLEMENTATION-NOTES §8).
3. **Check** (done): `cd projects/p6-schema-width/khg-width && python -m pytest -q` passes, 108 tests (the survey
   tests re-validate every certificate and lower-bound witness of all 23 rows); `results/pending-rerun.json` is gone;
   no row of `results/survey.csv` has `counts_source` = `SQID`.
4. **Update the numbers** (done). This prints the observed rows:

   ```bash
   python3 - <<'EOF'
   import csv
   for r in csv.DictReader(open("projects/p6-schema-width/results/survey.csv")):
       if r["row_id"].startswith("wd-observed"):
           print(r["row_id"], r["counts_source"], r["relations"], r["roles"], "residue", r["witness_size"],
                 "core", r["core_relations"], r["core_roles"],
                 *(f"{m}=[{r[m + '_lower']}, {r[m + '_upper']}]" for m in ("hw", "ghw", "fhw", "tw")), r["wall_seconds"])
   EOF
   ```

   | Where | Number now | Source |
   |---|---|---|
   | abstract, §2.5, Table 1 | 13,315 and 12,706 relations; roles | `relations`, `roles` |
   | abstract, Table 1, finding 2 | 391 to 1,458 residue relations; hw [4, 65], [3, 53] (dump), [4, 48], [4, 51] (slice) | `witness_size`; `hw_lower`, `hw_upper` |
   | Table 1 | core, ghw, fhw, tw | `core_relations`, `core_roles`, `{ghw,fhw,tw}_{lower,upper}` |
   | Controls paragraph | 34,050, 83,572, 31,572 and 62,641 roles; tw 34, 771, 36, 410 (36, 773, 38, 412 with time) | the relation-local rows' `roles`, `tw_lower` |
   | bounds paragraph | cliques of 18, 61, 17 and 53 roles; "finished only for the two observed-robust schemas" | `reports/<row>.json.gz`: `widths.ghw.lower_witness` (`roles`, `rho`, `complete`) |
   | bounds paragraph | 1,483 to 2,534 s | `wall_seconds`, min and max over the wd-roles r1 rows |
   | finding 5 | 333, 36, 1,134, 0.30 | recomputed from P3a's file, scope `dump` (`all`), with R02 §2.4's method; the same code gives R02's 328, 34, 1,149, 0.29 on SQID's counts |
   | abstract ("strictly more for two of the three"), end of §5 | still true: hw ≥ 4 for declared and observed-robust, ≥ 3 for observed-all; ≥ 4 for both slice schemas | the hw lower bounds |
   | figure | regenerated; `make_figure.py` now labels each column on three short lines so that twelve fit | `results/figure-widths.png` |

5. **Base update** (done), per the gate log's "What remains": the P6 README, the "Measured" subsection of
   `kb/01-foundations/hypergraph-theory-results.md` and the register entries [01.3], [01.6] and [02.6]; the run log
   is `notes/research-log/2026-09-25-p6-rerun.md`.
6. **Commit.** The commit the owner releases from (after the DOI and the author are filled in) is the one the note
   (`[COMMIT]`) and the deposit name.

## 2. The Zenodo deposit

1. **Reserve the DOI first**, so the note can cite it: New upload on https://zenodo.org, answer "No" to "Do you
   already have a DOI?", click "Get a DOI now!", save the draft
   (https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/, read 2026-09-25). A reserved DOI is lost if
   the draft is deleted. Put it in `note.md` (Data statement) and in `zenodo/README.md` (Citation), and commit.
2. **Assemble** from a clean checkout of that commit, on the machine that holds the raw files:

   ```bash
   projects/p6-schema-width/publication/zenodo/assemble.sh --final [--with-deltabot] [--with-sqid]   # per D1
   ```

   `--final` refuses when an observed row still uses SQID counts, rows wait for a re-run, or a deposited file differs
   from the commit. It verifies every raw file against its manifest's sha256, copies exactly the listed files into
   `/tmp/khg-p6-zenodo/files/khg-p6-deposit/` (default `--dest`), writes `SHA256SUMS` and `PROVENANCE.txt`, and builds
   `/tmp/khg-p6-zenodo/upload/README.md` and `khg-p6-schema-width-deposit.zip`. `--list` prints the expected files.
   Check that `PROVENANCE.txt` says `status: final` and the README has no DRAFT banner.
3. **Upload** the two files in `upload/` to the draft. Zenodo does not keep folders, hence the zip.
4. **Metadata.** Copy `zenodo/metadata.json` into the form, or send it through the REST API
   (https://developers.zenodo.org/; try https://sandbox.zenodo.org/ first). Replace the `creators` placeholder. The
   field names and the ids `cc0-1.0`, `dataset`, `software`, `publication-article` and `publication-conferencepaper`
   were checked against Zenodo's API documentation and vocabularies on 2026-09-25; if the API rejects one, set it in
   the web form. If the DeltaBot files are included (D1), the licence field still says CC0; the README states the
   exception.
5. **Publish** after the note is submitted (section 3), then add the arXiv identifier as a related identifier
   (`isSupplementTo`, resource type `publication-preprint`). Metadata can be edited after publishing; files need a new
   version.

## 3. The note: PDF and where to submit

**PDF.** Tested on 2026-09-25 with pandoc 3.9 and tectonic 0.15 (XeTeX, TeX Live fonts):

```bash
cd projects/p6-schema-width/publication
pandoc note.md -s -o note.tex -V geometry:margin=1in -V fontsize=10pt \
  -V mainfont=FreeSerif.otf -V mainfontoptions="BoldFont=FreeSerifBold.otf" \
  -V mainfontoptions="ItalicFont=FreeSerifItalic.otf" -V mainfontoptions="BoldItalicFont=FreeSerifBoldItalic.otf"
xelatex note.tex && xelatex note.tex          # or: pandoc note.md -o note.pdf --pdf-engine=xelatex (same -V options)
```

- The text uses Unicode (α, β, γ, ρ, ≤, ⊂), so use XeLaTeX; pdfLaTeX will fail on it. Fonts are named by file
  (`FreeSerif.otf`, or `DejaVuSerif.ttf`, both in TeX Live) because arXiv's XeLaTeX finds TeX Live fonts only by file
  name ("practically no fonts are registered with fontconfig", info.arxiv.org/help/faq/texlive.html, read
  2026-09-25).
- Run from this folder so `../results/figure-widths.png` resolves; for arXiv, copy the figure next to `note.tex` and
  fix the path.
- The `<!-- OWNER -->` comments disappear in LaTeX output.
- **Length.** In this single-column layout, after the re-run (with the eight slice rows in Table 1): 9 pages, the
  body on 6 of them and the top of page 7 (the end of §7 and §8, about 300 words), and the references from page 7 (pandoc 3.9 and tectonic, 2026-09-25). Before the re-run it was 8.
  A two-column build of that earlier draft (0.75 in margins, without the table, which pandoc's `longtable` cannot
  place in two columns) came to 6 pages with references. A venue template will change this; to cut, shorten §3.4, the Controls paragraph and the
  "Benchmarks and solvers" paragraph first.

**arXiv (recommended now).**

- **Primary category cs.DB**, defined by arXiv as covering "database management, datamining, and data processing":
  the question is Fagin's database-scheme acyclicity and the hypertree width of conjunctive queries, and the
  comparison literature (HyperBench, the decomposition solvers) is database theory (PODS, ACM JEA).
- **Cross-list cs.AI**, whose description "includes … Knowledge Representation": the objects are knowledge-graph
  schemas (Wikidata, Biolink) and that audience reads cs.AI. cs.DM (combinatorics, graph theory) and cs.DS
  (algorithms) are possible but weaker: the note proves nothing new and contributes no algorithm.
  (Category descriptions from https://arxiv.org/category_taxonomy, read 2026-09-25.)
- Submit the **TeX source**: "a PDF file created from a TeX/LaTeX file will typically be rejected"
  (info.arxiv.org/help/submit_pdf.html); choose the `xelatex` processor, which arXiv supports (TeX Live 2025 by
  default).
- A first submission to a category needs an endorsement: arXiv requires "that users be endorsed before submitting
  their first paper to arXiv or a new category" (info.arxiv.org/help/endorsement.html).
- Comments field, for example: "N pages, 1 figure, 1 table. Data: Zenodo DOI …; checker (MIT): repository URL".

**Workshops** (checked 2026-09-25; none is open now):

- **Wikidata Workshop** (6th edition at ISWC 2026, Bari, October 2026): the best topical fit (data modeling,
  querying). Its 2026 papers were due 31 July 2026; short papers 3–5 pages excluding references, CEUR-ART format; it
  also had a track for previously published work (https://wikidataworkshop.github.io/2026/). A 2027 edition was not
  announced: *a suggestion to check*.
- **AMW** (Alberto Mendelzon International Workshop; 17th edition, Arequipa, 9–13 November 2026): database theory;
  short papers up to 5 pages; 2026 submissions closed on 15 July 2026 (https://databasetheory.org/node/157). AMW 2027
  was not announced: *a suggestion to check*.
- **GRADES-NDA** (graph data management, held with SIGMOD/PODS; SIGMOD/PODS 2027 is 13–19 June 2027 in Huntington
  Beach, per https://2027.sigmod.org/): no 2027 call found: *a suggestion to check*.

Suggested path: arXiv as soon as section 1 is done; then the next Wikidata Workshop's short-paper track (or its
previously-published track, if it keeps one).

## 4. The post

After the note is on arXiv and the deposit is published: fill in the three links and delete the `<!-- OWNER -->`
comment. The numbers were updated after the re-run (section 1). Where to post is the owner's choice (PLAN §5: "The post is the owner's").

## 5. After release

- Add the arXiv identifier to the Zenodo record (section 2, step 5).
- Record the publication date on the PLAN §9 status board (the orchestrator's) and link the note, the record and the
  post from the P6 README ("Publication").
