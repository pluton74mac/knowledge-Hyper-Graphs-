# khg-width

The acyclicity class and the hypertree widths of a relation-type schema (`khg-relation-schema/1.0.0`, the C1
format of [khg-contracts](../../../README.md)). Built for P6, the schema width survey
([DESIGN](../DESIGN.md)); consumed by P11. MIT.

For a schema file it reports:

- the **acyclicity class** of H(S, σ) (roles as vertices, one edge per relation): `berge`, `gamma`, `beta`, `alpha`
  or `cyclic`, with a **witness** for the first test that fails: a Berge cycle, a γ-triangle, a β-cycle or the GYO
  residue (and the join tree when α-acyclic);
- **hw, ghw, fhw and tw**, each exact or as `[lower, upper]`, each lower bound labelled with its method and each
  upper bound backed by a decomposition validated on H (the four HD conditions, the special condition included).

```
$ khg-width tests/fixtures/p6-qualifier-k5.relation-schema.json --solver python
schema      p6-qualifier-k5/0.1.0  sha256:047260…  file 4db729cfb1…  slots core,qualifier
class       cyclic (alpha fails)  witness: GYO residue, 10 relations on 5 roles
hw   3      exact  hd-search (python hd-search on the input: k=2 no, k=3 yes); HD validated
ghw  3      exact  dp (core 5 roles, 10 relations, 1 blocks); GHD validated
fhw  5/2    exact  dp (core 5 roles, 10 relations, 1 blocks); FHD validated
tw   4      exact  dp (subset DP after the simplicial rule); TD validated
```

## Install

```bash
pip install .                                          # khg-contracts, from the repository root
pip install "./projects/p6-schema-width/khg-width[dev]"  # extras: fast (SciPy), survey (linkml, pyyaml, matplotlib), dev
```

Pure Python on khg-contracts. Importing `khg_width` loads no SciPy, linkml or matplotlib and starts no solver.

## Command line

`khg-width SCHEMA_FILE [--slots core,qualifier[,time]] [--time-limit SECONDS] [--solver auto|python|balancedgo|logk] [--json]`

- `SCHEMA_FILE` is `.json` or `.json.gz`.
- `--slots`: `core,qualifier` (default) or `core,qualifier,time`; `meta` is refused and `core` is required.
- `--time-limit` bounds **each step** (a DP, a clique enumeration, an induced search, an hw-search level, a solver call
  at one k); default 60 s. The class tests are polynomial and uncapped.
- `--solver auto` uses BalancedGo with log-k-decomp as a second opinion when they are found, else Python; `python`
  uses no tool; `balancedgo` or `logk` uses that tool alone.
- Exit status: **0** a report is produced (whatever the class), **1** the schema is invalid (every `load_schema`
  error finding is printed), **2** a usage or I/O error (missing file, bad slots or limit, missing requested solver).

## Python API

```python
from khg_width import check, hypergraph, classify, width, validate, find_solvers
report = check("schema.json", slots=("core", "qualifier"), time_limit=60.0, solver="auto")
report.acyclicity.cls, report.acyclicity.witness, report.widths["hw"].show(), report.to_json()
```

## Optional solvers

`scripts/build-solvers.sh [DEST]` builds BalancedGo (`872c662c`, v1.7.2-2) and log-k-decomp (`5e021dd4`, v1.1.0),
both MIT, with Go (`GOTOOLCHAIN=local`) into `DEST/bin` (default `~/.cache/khg-width/solvers`; a DEST inside a git
working tree is refused) and writes `DEST/solvers.json`. They are found through `KHG_WIDTH_BALANCEDGO` /
`KHG_WIDTH_LOGK`, `KHG_WIDTH_SOLVERS=DEST`, the default DEST, then `PATH`. hw is then bisected between its
validated bounds: at each k, BalancedGo (then log-k-decomp) runs with the preprocessing flags to find a
decomposition, and a run without them to refute k; only such a "no" raises the lower bound. Each attempt runs at most
120 s (and at most `--time-limit`), all of a schema's attempts at most 20 minutes; every attempt is in the report's
`solver_attempts`. Every decomposition they return is validated in Python; a special-condition violation demotes it
to a ghw bound; disagreements are kept in the report.

## Tests

```bash
cd projects/p6-schema-width/khg-width && python -m pytest -q
```

Tests marked `solvers` skip without both binaries; tests marked `survey` skip until
`projects/p6-schema-width/results/survey.csv` exists (`KHG_WIDTH_SURVEY_RESULTS` points them at another run).
