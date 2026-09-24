# P6 results

The measured objects and, once the survey has run, its outputs (DESIGN §6.6).

## What is here now

`schemas/`: the 9 generated schema files, each with `<name>.provenance.json` (input sha256s, naming version,
count source, scope and dates, thresholds, generator version and source hashes, git commit):

| File | Relations | Source |
|---|---|---|
| `p6-wikidata-declared-{wd-roles-r1,relation-local}.json.gz` | 1,155 | allowed-qualifiers constraints, WDQS 2026-09-24 |
| `p6-wikidata-observed-robust-{wd-roles-r1,relation-local}.json.gz` | 13,608 | SQID `qs` (dump 2026-08-10) over DeltaBot main-statement counts (2026-09-23); >= 10 uses and >= 0.1 % |
| `p6-wikidata-observed-all-{wd-roles-r1,relation-local}.json.gz` | 13,608 | the same, >= 1 use |
| `p6-biolink-{formal,formal-domain}-global.json`, `p6-biolink-formal-relation-local.json` | 103 | Biolink Model v4.4.5 (commit a4180f8) |

The Wikidata files are canonical JSON in deterministic gzip (mtime 0, ruling Q5); `run_survey.py generate` rebuilds
them byte for byte from the manifested raw files. The observed files rest on SQID until P3a's
`qualifier-usage-20260922.json` lands (`reproduce.sh --p3a-counts PATH`); the SQID-based rows then move to
`superseded/` and 8 slice rows are added.

## What the survey adds

`survey.{csv,md,json}`, `reports/<row>.json` (full `khg-width --json` reports with decompositions and steps),
`hyperbench-baseline.json`, `figure-data.csv`, `figure-widths.{svg,png}`, `solver-log.jsonl` (disagreements and
demotions), `machine.json`, `crosschecks/` (manual, `survey/crosscheck.sh`) and, with P3a's counts,
`p3a-crosscheck.json`. Reproduce with `../survey/reproduce.sh` (see its header for the steps and run time).

## Licences and attribution

- **Wikidata**: CC0-1.0 (*Wikidata:Copyright*: structured data of the main, Property, Lexeme and EntitySchema
  namespaces). Only numbers are taken from the DeltaBot count templates (Template namespace, CC BY-SA 3.0). SQID's
  statistics are used, not redistributed.
- **Biolink Model** v4.4.5: CC0-1.0 by the model's `license:` field; the repository's `LICENSE` is Apache-2.0, so the
  model is credited by name and version: Unni et al., *Clin. Transl. Sci.* 2022, https://doi.org/10.1111/cts.13302.
- **HyperBench** (baseline): Zenodo 10.5281/zenodo.7180787, CC BY 4.0; cite Fischl, Gottlob, Longo and Pichler,
  PODS 2019 (https://doi.org/10.1145/3294052.3319683) and ACM JEA 26 (https://doi.org/10.1145/3440015).
- The generated schema files are derived data under the same terms; khg-width itself is MIT.
