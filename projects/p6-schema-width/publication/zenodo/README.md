@STATUS_BANNER@
# Schema width survey: Wikidata qualifier schemas and the Biolink Model (data deposit)

This deposit holds the inputs and outputs of a survey of the acyclicity class and the hypertree widths (hw, ghw,
fhw, tw) of knowledge-hypergraph relation-type schemas: the Wikidata qualifier schemas, declared (allowed-qualifier
constraints) and observed (qualifier usage), and the association classes of the Biolink Model v4.4.5. It accompanies
the note *How acyclic are knowledge-hypergraph schemas?* (`[NOTE LINK: the arXiv identifier if already assigned;
otherwise delete this parenthesis and add the link to the record's related identifiers later]`) and the checker
`khg-width` (MIT), which lives in the source repository, not here.

- Source repository: https://github.com/pluton74mac/knowledge-Hyper-Graphs-
- Commit this deposit was assembled from: `@COMMIT@`
- Optional third-party files in this copy: @OPTIONAL@
- `PROVENANCE.txt` records the commit, the options and any warnings; `SHA256SUMS` lists every file with its sha256.

**Why a deposit.** The Wikidata Query Service (WDQS) is live: querying it again returns a new snapshot, not the same
bytes. The measured schema files are committed to the repository, but the raw query results they were generated from
are not (the repository commits manifests only). This deposit keeps that snapshot, with the generated files and the
results, in one citable place.

## Contents

All paths inside the archive `khg-p6-schema-width-deposit.zip` are under `khg-p6-deposit/` and, below that, relative
to the repository root, so the archive can be copied into a checkout.

| Path | What | Files |
|---|---|---|
| `datasets/knowledge-bases/wikidata-property-schemas/raw/*.srj.json` | WDQS results (SPARQL JSON) of 2026-09-24, 09:35–10:21 UTC: every property with datatype and English label; property `instance of` classes; the allowed-qualifiers, required-qualifier, subject-type and value-type constraint statements; property scope; Wikidata's qualifier classes; and 20,000-statement usage slices of P39, P69, P108, P166 and P54 | 33 |
| `datasets/knowledge-bases/wikidata-property-schemas/raw/usage_*.wikitext` | *only with `--with-deltabot`*: the three DeltaBot count templates (main statements, qualifier uses, reference uses per property), revisions of 2026-09-23 | 3 |
| `datasets/knowledge-bases/wikidata-property-schemas/raw/sqid-*.json` | *only with `--with-sqid`*: SQID's `properties.json` and `statistics.json` (per-property qualifier counts `qs` from the Wikidata dump of 2026-08-10) | 2 |
| `datasets/knowledge-bases/biolink-model/raw/` | Biolink Model v4.4.5 (commit `a4180f818e9722c493788c5ff1f047fde64f13a7`): `biolink-model.yaml`, its local import `attributes.yaml`, and the repository's `LICENSE` | 3 |
| `datasets/**/MANIFEST.json` | the manifests: source URL, SPARQL query text, retrieval time, bytes and sha256 of every raw file; also the manifests of the Wikidata JSON dump of 2026-09-22 and of the HyperBench run data, whose files are not in this deposit | 4 |
| `projects/p6-schema-width/results/schemas/` | the 13 generated schema files (`khg-relation-schema/1.0.0`): 10 Wikidata files as deterministic `.json.gz` (declared; observed-robust and observed-all over the whole dump and over the corpus slice; each under wd-roles r1 and the relation-local control) and 3 Biolink files as `.json`, each with `<name>.provenance.json` (input sha256s, naming version `wd-roles r1`, count source, scope and dates, thresholds, generator version and source hashes, commit) | 26 |
| `projects/p6-schema-width/results/reports/` | one full `khg-width --json` report per survey row (`.json.gz`: class, witness, widths with methods, certificates, lower-bound witnesses, every solver attempt) and its run log (`.log`) | 2 per row |
| `projects/p6-schema-width/results/` | `survey.csv`, `survey.md`, `survey.json` (the table), `figure-widths.{svg,png}` and `figure-data.csv`, `hyperbench-baseline.json`, `solver-log.jsonl` (every solver attempt, disagreement and demotion), `machine.json` (platform, tool versions and binary sha256, the load each row ran under), `p3a-crosscheck.json` (the count file's own slot and time-model classification against the generator's), `README.md` | 11 |
| `projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json` | exact qualifier-usage counts per (property, qualifier), in statements and snaks, from one pass over the Wikidata JSON dump of 2026-09-22, in two scopes: every item and property entity (`all`) and the items with an English Wikipedia article (`kept`); the count source of the observed schemas | 1 |

**Not in this deposit, and why:**

- **HyperBench run data** (`parseddata_csv.zip`, `hyperbench.zip`): already on Zenodo, https://doi.org/10.5281/zenodo.7180787
  (CC BY 4.0), with a DOI. It is referenced, not copied; the manifest pins both files' sha256. Only aggregate numbers
  recomputed from it are here (`hyperbench-baseline.json` and panel (a) of the figure).
- **The Wikidata JSON dump** of 2026-09-22 (about 103 GB): public at dumps.wikimedia.org; its manifest is included.
- **The GO-CAM schema** used by one research probe: not part of the survey, and its licence file is a placeholder.
- **The checker and the survey scripts**: code, MIT, in the repository at the commit above.
- **Superseded results**: the first observed schemas, built from SQID's counts (dump of 2026-08-10), and their rows,
  replaced on 2026-09-25: in the repository under `projects/p6-schema-width/results/superseded/`.

## Licences

- **Wikidata-derived files** (the WDQS results, the qualifier-usage counts, and every generated schema, report and
  table built from them): CC0-1.0. Wikidata's structured data (main, Property, Lexeme and EntitySchema namespaces) is
  CC0 (https://www.wikidata.org/wiki/Wikidata:Copyright, read 2026-09-24), and the depositor dedicates the derived
  files to the public domain under the same terms.
- **Biolink Model v4.4.5**: the model file declares `license: https://creativecommons.org/publicdomain/zero/1.0/`
  (CC0-1.0). The Biolink repository's `LICENSE` file, included as `raw/LICENSE`, is Apache-2.0, and its Python package
  metadata says MIT. The files are redistributed unchanged, with credit: D. R. Unni et al., "Biolink Model: a
  universal schema for knowledge graphs in clinical, biomedical, and translational science", *Clinical and
  Translational Science* 15(8):1848–1855, 2022, https://doi.org/10.1111/cts.13302.
- **HyperBench** (CC BY 4.0) is referenced, not redistributed. If you use `hyperbench-baseline.json` or the figure's
  HyperBench panel, keep the attribution: W. Fischl, G. Gottlob, D. M. Longo, R. Pichler, "HyperBench: a benchmark and
  tool for hypergraphs and empirical findings", PODS 2019, https://doi.org/10.1145/3294052.3319683, and ACM JEA 26,
  2021, https://doi.org/10.1145/3440015; G. Gottlob, M. Lanzinger, C. Okulmus, R. Pichler, "Experimental data for
  log-k-decomp", Zenodo, 2023, https://doi.org/10.5281/zenodo.7180787.
- **Optional files**, present only if this copy was assembled with the flags named above:
  - DeltaBot templates: pages in Wikidata's Template namespace, which is text, not structured data. The source
    repository records them as CC BY-SA 3.0; only their numbers are used. If present, they are **not** covered by the
    CC0 dedication and are redistributed under CC BY-SA 3.0, with attribution to the Wikidata contributors of each page
    (history at the page URL in the manifest).
  - SQID files: statistics computed by SQID from Wikidata dumps. SQID's repository states that its code is
    Apache-2.0 and states no licence for these data files `[unverified]`.

## How the files were produced

1. **Fetch (2026-09-24).** `projects/p6-schema-width/research/probes/wd_fetch.py` ran each SPARQL query against
   https://query.wikidata.org/sparql (main graph) and fetched the DeltaBot templates by revision id and SQID's files;
   it wrote the manifest with query text, retrieval time and sha256. The Biolink files were fetched from GitHub at
   the pinned commit.
2. **Count (2026-09-24 to 2026-09-25).** The slicer of the companion n-ary corpus
   (`projects/p3a-clean-nary-corpus/slice/wdslice.py`, commit `a3bb518`) read `wikidata-20260922-all.json.bz2`
   once, after matching it against the published size, md5 and sha1, and wrote the qualifier-usage counts under the
   same naming, `wd-roles r1`. The file records the dump's checksums and the slicer's commit.
3. **Generate.** `projects/p6-schema-width/survey/run_survey.py generate --p3a-counts …` builds the schema files with
   `khg_width.sources.wikidata` and `khg_width.sources.biolink` under the role naming `wd-roles r1`
   (`projects/p6-schema-width/wd-roles.md`), after verifying every raw file against its manifest. The output is
   deterministic (canonical JSON; gzip with mtime 0).
4. **Measure.** `run_survey.py run` runs `khg-width FILE --slots … --time-limit 600 --solver auto --json` per row,
   with BalancedGo (commit `872c662`) and log-k-decomp (v1.1.0, `5e021dd`) built by
   `projects/p6-schema-width/khg-width/scripts/build-solvers.sh`; external-solver attempts are capped at 120 s each and
   1,200 s per row. Every upper bound in a report carries a decomposition validated on the schema hypergraph, and
   every lower bound a witness.
5. **Baseline, table, figure.** `survey/hyperbench_baseline.py` recomputes the HyperBench distribution from the
   Zenodo run data; `run_survey.py table` and `survey/make_figure.py` write the table and figure.

The observed schemas are built from those counts: scope `dump` from `all`, scope `slice` from `kept` (a property is a
relation when it has a main statement in the scope; a qualifier is a role of it with at least one use, or, for
observed-robust, at least 10 uses and 0.1 % of the property's main statements). The `counts_source`, `counts_date`
and `scope` columns of `survey.csv`, and each schema's provenance, say so. `p3a-crosscheck.json` lists where the
count file's own `slot` labels differ from the generator's: all of them are the two vocabulary differences explained
in the repository's `projects/p6-schema-width/IMPLEMENTATION-NOTES.md` §8, and none reaches a measured hypergraph.

## How to reproduce

With the repository at commit `@COMMIT@`:

```bash
git clone https://github.com/pluton74mac/knowledge-Hyper-Graphs- khg && cd khg && git checkout @COMMIT@
unzip /path/to/khg-p6-schema-width-deposit.zip -d /tmp/khg-p6
(cd /tmp/khg-p6/khg-p6-deposit && sha256sum -c SHA256SUMS)          # integrity of every file
cp -R /tmp/khg-p6/khg-p6-deposit/datasets .                          # raw files land in the gitignored raw/ folders
python3 -m venv .venv && . .venv/bin/activate
pip install . "./projects/p6-schema-width/khg-width[survey,fast]"
projects/p6-schema-width/khg-width/scripts/build-solvers.sh          # optional; needs Go; builds outside the checkout
```

- **Check one schema** (seconds for Biolink; about half an hour for a Wikidata wd-roles r1 row at the survey's
  limits): `khg-width projects/p6-schema-width/results/schemas/p6-biolink-formal-global.json --json`.
- **Re-validate every stored certificate and lower-bound witness** against the committed results:
  `cd projects/p6-schema-width/khg-width && python -m pytest -q tests/test_survey.py`.
- **Re-measure the deposited schema files** (no raw file needed), into a scratch directory, and compare with
  `survey.csv`:

  ```bash
  mkdir -p /tmp/p6-rerun && cp -R projects/p6-schema-width/results/schemas projects/p6-schema-width/results/hyperbench-baseline.json /tmp/p6-rerun/
  python projects/p6-schema-width/survey/run_survey.py run --out /tmp/p6-rerun --jobs 3 --time-limit 600 --solver auto
  python projects/p6-schema-width/survey/run_survey.py table --out /tmp/p6-rerun
  ```

  Classes, exact values and certificates must match; bounds found under time limits are machine-dependent and may
  differ. About 2 to 2.5 hours on 4 cores with both solvers.
- **Reproduce from the raw snapshot** with `projects/p6-schema-width/survey/reproduce.sh --p3a-counts
  projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json --out /tmp/p6-full --jobs 3`. The schema files depend
  only on the WDQS results and the qualifier-usage counts: rebuilt with the SQID and DeltaBot data emptied, all ten
  Wikidata files came out byte-identical (checked 2026-09-25). The scripts still *read* those files, though: step 2
  verifies **every** file listed in the Wikidata manifest (38) against its sha256, and the generator loads
  `sqid-properties.json` and `usage_main_statements.wikitext`. They are in this copy only if it was assembled with
  `--with-sqid` and `--with-deltabot` (see the line near the top). Otherwise the DeltaBot templates can be fetched
  again by the revision URLs in the manifest (identical bytes are expected but `[unverified]`), and SQID's files
  cannot, since SQID overwrites them; without them the scripts stop at step 2, and the committed schema files, whose
  sha256 is pinned in `survey.csv`, are the measured object. The HyperBench zips must be fetched from Zenodo into
  `datasets/hypergraph-benchmarks/hyperbench/raw/` (the manifest gives the URLs; Zenodo returns identical bytes).

## Citation

`[CITATION: to be filled in by the owner: the creators, the title, Zenodo, the year and this record's reserved DOI]`
