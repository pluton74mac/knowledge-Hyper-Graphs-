# P6 results

The measured objects and the survey's outputs (DESIGN §6.6). The first full run is commit 5f8683d; the rows the
review touched were re-run in 7c58957, and the observed rows on P3a's exact counts on 2026-09-25
([IMPLEMENTATION-NOTES](../IMPLEMENTATION-NOTES.md) §8). Rows listed in `pending-rerun.json`, when it exists, wait for
a re-run: their schema file changed, or the checker changed after they ran (§7). `run_survey.py run` removes each row
from the list when it re-runs, and the `survey` tests skip the listed rows until then. No row waits now.

## Schemas

`schemas/`: the 13 generated schema files, each with `<name>.provenance.json` (input sha256s, naming version,
count source, scope and dates, thresholds, generator version and source hashes, git commit):

| File | Relations | Source |
|---|---|---|
| `p6-wikidata-declared-{wd-roles-r1,relation-local}.json.gz` | 1,155 | allowed-qualifiers constraints, WDQS 2026-09-24 |
| `p6-wikidata-observed-robust-{wd-roles-r1,relation-local}.json.gz` | 13,315 | P3a's exact counts, scope `dump` (`all`: every item and property entity of the Wikidata JSON dump of 2026-09-22); qualifiers on >= 10 statements and >= 0.1 % of the property's main statements; the time model from any use (ruling Q10) |
| `p6-wikidata-observed-all-{wd-roles-r1,relation-local}.json.gz` | 13,315 | the same, >= 1 statement |
| `p6-wikidata-observed-{robust,all}-slice-{wd-roles-r1,relation-local}.json.gz` | 12,706 | the same two tables, scope `slice` (`kept`: the items with an English Wikipedia article) |
| `p6-biolink-{formal,formal-domain}-global.json`, `p6-biolink-formal-relation-local.json` | 103 | Biolink Model v4.4.5 (commit a4180f8) |

The Wikidata files are canonical JSON in deterministic gzip (mtime 0, ruling Q5); `run_survey.py generate` rebuilds
them byte for byte from the manifested raw files, and installs them only where they differ: identical files are
left untouched, provenance included. The observed files are built from P3a's
`projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json` (`reproduce.sh --p3a-counts PATH`). The first observed
files, built from SQID's counts (dump of 2026-08-10) over DeltaBot's main-statement counts (2026-09-23), are in
`superseded/` with their provenance and their rows' reports and logs. `p3a-crosscheck.json` compares the count file's
own slot and time-model labels with the generator's; every entry in it is one of two vocabulary differences that do
not reach a measured hypergraph (IMPLEMENTATION-NOTES §8).

## Survey outputs

`survey.{csv,md,json}`, `reports/<row>.json.gz` (full `khg-width --json` reports with decompositions, steps and
every external-solver attempt; compact JSON in deterministic gzip, ruling Q6),
`hyperbench-baseline.json`, `figure-data.csv`, `figure-widths.{svg,png}`, `solver-log.jsonl` (every solver
attempt, disagreement and demotion), `machine.json` (platform, tools, and the load each row ran under),
`crosschecks/` (manual, `survey/crosscheck.sh`; none so far) and `p3a-crosscheck.json`. Reproduce with `../survey/reproduce.sh` (see its header for the steps and run time).

## Licences and attribution

- **Wikidata**: CC0-1.0 (*Wikidata:Copyright*: structured data of the main, Property, Lexeme and EntitySchema
  namespaces); P3a's counts are statistics of the CC0 dump. The superseded files took numbers from the DeltaBot
  count templates (Template namespace, CC BY-SA 3.0) and SQID's statistics, which are used, not redistributed.
- **Biolink Model** v4.4.5: CC0-1.0 by the model's `license:` field; the repository's `LICENSE` is Apache-2.0, so the
  model is credited by name and version: Unni et al., *Clin. Transl. Sci.* 2022, https://doi.org/10.1111/cts.13302.
- **HyperBench** (baseline): Zenodo 10.5281/zenodo.7180787, CC BY 4.0; cite Fischl, Gottlob, Longo and Pichler,
  PODS 2019 (https://doi.org/10.1145/3294052.3319683) and ACM JEA 26 (https://doi.org/10.1145/3440015).
- The generated schema files are derived data under the same terms; khg-width itself is MIT.
