---
title: "P6 implementation notes: decisions and deviations from DESIGN"
type: project
status: draft
created: 2026-09-24
---

# P6 implementation notes

What was built against [DESIGN.md](DESIGN.md) (with the director's rulings Q1–Q11) and [wd-roles.md](wd-roles.md) r1,
and every place where the implementation had to choose. Where DESIGN is specific it was followed; where it was
ambiguous the research prototypes' behaviour was preferred and the choice is listed here.

## 1. What exists

| DESIGN | Where | State |
|---|---|---|
| §4 package | `khg-width/` (pyproject, `src/khg_width/`, `tests/`, `scripts/build-solvers.sh`, MIT) | done |
| §4.5 solver build | `khg-width/scripts/build-solvers.sh` | built here (Go 1.24.7): both binaries pass the smoke test |
| §5 fixtures and tests | `khg-width/tests/` (fixture table `fixtures/expected.csv`; recorded hw `fixtures/random-hw.json`) | after the review fixes (§7): CI setting (fresh Python 3.10 venv, `[dev]` only, no solvers): 88 pass, 20 skip; with SciPy, linkml, both solvers and the committed survey results: 108 pass |
| §4.4 CI (F7) | `.github/workflows/ci.yml`, job `khg-width`, appended as given | simulated locally on Python 3.10 |
| §6 survey scripts | `survey/run_survey.py`, `hyperbench_baseline.py`, `make_figure.py`, `reproduce.sh`, `crosscheck.sh` | smoke run here; the full run is commit 5f8683d (coordinator) |
| §6.1 HyperBench manifest (Q1) | `datasets/hypergraph-benchmarks/hyperbench/MANIFEST.json`; family added to `datasets/README.md` | done |
| §6.2 schema files | `results/schemas/` (9 files with provenance) | generated; the two observed-robust Wikidata files regenerated under ruling Q10 (§7) |

The first full survey (15 rows, the HyperBench baseline and the figure) is commit 5f8683d. After the review fixes (§7)
the rows listed in `results/pending-rerun.json` wait for a re-run; the `survey` tests check every other row.

## 2. Package

**Layout.** As §4.1, plus `steps.py` (the cooperative deadline, budgets and the step log, shared by `exact`, `bounds`
and `check`), `__main__.py` (`python -m khg_width`) and `solvers/runner.py` (the process-group runner and the
classification of one solver call). `solvers/discovery.py`, `balancedgo.py`, `logk.py` and `parsers.py` are as listed.

**API.** §4.2's six functions and dataclasses, plus `check_hypergraph(h)` (class and the four widths of a `Hypergraph`
given directly; the tests use it) and the exceptions `SchemaInvalid` and `UsageError`. The public names are bound in
`__init__` after their submodules load. Lazy attribute loading was tried first and failed: importing the submodule
`khg_width.check` replaced the function `check` on the package (and `hypergraph` likewise). The eager imports are pure
Python; `test_hygiene` checks that importing loads no SciPy, linkml, matplotlib or numpy and spawns no process.

**The measured object.** Widths, α, β and γ use the set hypergraph (`Hypergraph.distinct()`: one edge per distinct
role set, named after its first relation in schema order); Berge uses the named multi-hypergraph (D4). The solvers and
the Python hw search receive the set hypergraph; every certificate is validated against H with all its named
relations. Universal roles are reported only when there are two relations or more. `components` counts H as given;
`components_without_universal` is added beside it.

**Reading files (Q5).** `.json` goes through `load_schema(path)`; `.json.gz` through gunzip, `jsonio.loads` and
`load_schema(mapping)`. A truncated or corrupt gzip stream is an I/O error (exit 2), not a J finding.

### 2.1 Classes (§3.1)

- α is `khg_contracts.schema.is_alpha_acyclic`, as specified. An indexed GYO (`acyclicity.gyo`) runs beside it and
  must return the same residue (else `InternalError`); it also records the ear links that make the join tree. The
  first version scanned whole candidate sets and took 19 s on observed-all; keeping each role's relations in an
  insertion-ordered dict and stopping at the first containing relation in schema order took it to 0.2 s with the same
  links. On the full tables `classify` takes 0.1 s (declared), 3 s (observed-all, wd-roles r1) and 2.8 s
  (observed-all, relation-local, 13,608 relations and 83,426 roles; §7 asks for under 30 s).
- The β-cycle search is the prototype's shortest-first depth-first search, rewritten with an explicit stack; the
  γ-triangle search keeps the prototype's order (lexicographic x, y, z with x < z) on the DM residue. Both budgets
  are 200,000 (extensions, triples). Every complete witness is re-checked against its definition on H.
- A disconnected α-acyclic H gives a join forest; its roots share no role and are chained under the first.
- Invariant checks that raise `InternalError`: GYO residues differ; the join tree fails running intersection; a
  witness fails its definition; two relations on the same two or more roles in a Berge-acyclic H; a lower bound above
  a validated upper bound. (Two relations with the same *single* role are Berge-acyclic; a first version of the check
  got this wrong and the random test caught it.)

### 2.2 Reductions (§3.2, Q3)

- ghw/fhw core: GYO, twin merging and universal-role removal repeated to a fixpoint on the set hypergraph, then the
  blocks of its primal graph. Every step is logged (`lonely`, `subsumed`, `empty`, `twin`, `universal`) and undone
  in reverse order when lifting; blocks are joined at cut roles through the block-cut tree.
- tw: the universal roles of H are removed with +1 each (Q3). One edge case found by the random test: when *every*
  role is universal (H is one role set), tw = |U| − 1, not tw(∅) + |U|; one universal role is then kept. Lonely roles
  go through GYO as the simplicial rule (a batch's bag is the relation before the batch, tw ≥ |e| − 1) and subsumed
  relations are dropped (the primal graph does not change); then the general simplicial rule runs on roles of degree
  up to 1,000 under the step limit; then blocks. Twins are never merged for tw (tested on a K6 primal graph).
- hw is never reduced.

### 2.3 Exact procedures (§3.3)

- Subset DP as R01, iterating subsets in numeric order and skipping a role whose predecessor value already exceeds the
  best candidate. Limits 20 roles (tw, ghw) and 16 (fhw) per block. ρ in the DP is exact search over maximal traces
  on bitmasks; ρ* is the exact rational simplex (Bland's rule on the dual, which starts feasible; primal read from the
  slack reduced costs; both checked, and their values must agree).
- hw normal-form search: separators are drawn only from relations meeting C ∪ N(C) (a relation outside it adds
  nothing to χ, and dropping it from λ keeps (1)–(4)), solved components are memoised as well as failed ones, and the
  recursion is a generator trampoline (no Python recursion limit). 3·10⁶ trials per k, ≤ 60 distinct relations, k up
  to 10. It starts from hw's own lower bound (2 when cyclic), so for `p6-qualifier-k5` it refutes k = 2 itself, as
  §4.3's example shows.

### 2.4 Bounds (§3.4)

- Clique bounds: ρ(K) exact when K has at most 60 maximal traces, else ⌈|K| / largest trace⌉; ρ\*(K) exact up to
  40 roles and 160 traces, else the dual bound |K| / largest trace (a feasible dual: certified). Enumeration is
  Bron–Kerbosch with pivoting under the step limit; the best bound found by then is kept, and the step is logged
  `timeout (partial kept)` rather than `done` (review F7; likewise the tw simplicial rule).
- Induced bounds: one set per measure, grown greedily from the highest-degree core role. For hw the set shrinks (18,
  16, …) until H[X] has at most 60 distinct traces; on the Wikidata cores this leaves small sets and weak bounds.
- Heuristic orderings: min-degree and min-fill with ties broken by a random key seeded 20260924. Min-fill recomputes
  the fill of the eliminated role's neighbours only (approximate bookkeeping; any ordering is valid) and is skipped
  above 1,500 roles. ghw upper bounds use greedy covers of the bags; fhw computes ρ\* only for bags whose greedy value
  can still raise the maximum (exact simplex on small bags, else SciPy rounded up, else greedy).
- **Added (kept by ruling Q7):** `hd-repair`. With Python alone, the only hw upper bound on a large H was the trivial |E| (1,154 on the
  declared table). One pre-order pass makes any GHD satisfy the special condition: at node t, each role of
  (∪λ_t) ∩ χ(T_t) missing from χ_t is added to χ_t and to the nodes below t whose subtree holds it, each with the
  guard of t that holds it; nodes above t are not touched again, so the pass ends with an HD. It runs on the lifted
  GHD, on the tw decomposition with greedy guards and on every GHD demoted from a solver (ruling Q11, method
  `hd-repair:<tool>-demoted`), and every result is validated. On the declared table it gives hw ≤ 52.
- **Added (kept by ruling Q7):** the lifted GHD is also validated as an HD (`ghd-is-hd`); the tw decomposition with
  greedy guards is offered as a ghw certificate (`tw-covers`), which is how ghw ≤ tw + 1 enters with a certificate.
  Both Python HDs (from the GHD and from the tw decomposition) are made before the solver bisection starts, so it
  starts from the smallest validated upper bound.
- **Propagation, one deviation.** §3.4 passes bounds through all four inequalities, while §3.6 says no upper bound is
  reported without a validated decomposition. Upper bounds therefore move only with a certificate (an HD is a GHD, a
  GHD an FHD); hw ≤ 3·ghw + 1 moves lower bounds only (ghw ≥ ⌈(hw_l − 1)/3⌉), and ghw ≤ tw + 1 enters as the
  `tw-covers` certificate above. Propagation also runs before the external-solver schedule, so that schedule starts
  at hw ≥ the ghw lower bound (the first smoke run wasted k = 2 on the declared table).

### 2.5 Solvers (§3.5, §4.5)

- **Schedule (ruling Q8, replacing §3.5's).** Bisection between hw's validated lower bound (after propagation and
  the Python search) and its validated upper bound (the smallest of the trivial HD, `ghd-is-hd`, `hd-repair` and the
  Python search). At the midpoint k of [lo, hi):
  1. *find*: BalancedGo, then log-k-decomp (under `auto`, when found), each `-width k` with
     `-t -h -g -heuristic 1`; a decomposition that validates as an HD on the unreduced H lowers hi to its width;
  2. otherwise *refute*: BalancedGo (log-k-decomp when it is the only tool) `-width k` without preprocessing; its
     "no" raises lo to k + 1 (Q2); a validated yes lowers hi;
  3. a k that neither decides (timeouts, errors, invalid output, a decomposition the tool's own check rejected) is
     left undecided and the search continues in (k, hi).
  Each attempt runs at most min(120 s, the step limit); the row's attempts, both tools together, at most 1,200 s.
  When the bounds meet at hw ≥ 2, one confirmation run without preprocessing at hw − 1 by the second-opinion tool
  (log-k-decomp under `auto`; the tool itself in single-tool modes), unless that exact run was already made. This
  replaces §3.5's second opinion, and it means a small row that Python already decided costs one solver call. The
  `-exact` path for ≤ 60 relations and k_max = 10 are gone: the bisection covers every size and range.
  `check(…, solver_attempt=120, solver_budget=1200)` sets the two limits (the CLI keeps §4.3's options).
- Every attempt is logged in the report's `solver_attempts` (k, tool, flags, limit, seconds, outcome, validated width,
  what it was used as, the command) and summarised in `solver_budget` (attempt and budget seconds, seconds used);
  the text report has a `solvers` line; the survey's `solver-log.jsonl` lists the attempts of every row, and the
  table gains `solver_attempts` and `solver_seconds` columns. `test_schedule.py` checks the schedule on p6-adler
  with a scripted stand-in for BalancedGo (bisection order, a preprocessed "no" is not a bound, an undecided k moves
  the search up, the budget caps the attempts); `test_live_bisection_from_the_trivial_bound` runs it with the real
  binaries from [2, 10] on p6-qualifier-k5.
- log-k-decomp has no `-det`; its runs are `-width k` (LogKHybrid), with the same flags when finding.
- Both tools print `Correct: false` in two cases: no decomposition (empty tree, `Width: 0`) and a decomposition
  found but rejected by their own check (a tree, and a line such as `Edge … isn't covered`). Only the first is a
  "no"; the second is the outcome `invalid` (review F1): logged in `disagreements[]` as `solver-invalid` with the
  tool's check lines, and never a bound.
- Claims are resolved at the end: a sound refutation at k contradicted by any validated HD of width ≤ k is dropped
  and logged (`refutation-contradicted`); a yes failing (4) or printing "SCV found!" is demoted: its GHD is offered
  as a ghw bound and, repaired by `hd-repair`, as an hw bound (Q11); the `demotion` entry says whether each was used
  (`ghw_bound_used`, `repaired_hd_width`, `hw_bound_used`), and so does the attempt's `used_as` (review F8). Other
  invalid ones are logged (`invalid`). These go to `disagreements[]` with `kind`, the commands, output tails and
  times (so the report needs no separate demotion list).
- Neither BalancedGo nor log-k-decomp echoes an edge count. The echoed-count check applies to any output that has one
  (fraSMT's `#hyperedges`); for these two tools, validating every decomposition on H is the guard (a decomposition of
  a misparsed graph fails condition (1)).
- `build-solvers.sh` keeps Go's module and build caches under `DEST/go` unless `GOMODCACHE`/`GOCACHE` are set,
  refuses a DEST in any git working tree (tested on the nearest existing ancestor before anything is created), and
  smoke-tests both binaries with `-exact` on the triangle. Discovery does not trust `solvers.json`'s commit for a
  binary whose sha256 differs.

### 2.6 Report and CLI

- Certificates are serialised as flat node lists (`{"nodes": [{"bag", "cover", "parent"}]}`): join trees of thousands
  of relations are too deep for nested JSON. For an α-acyclic H the hw/ghw/fhw certificates reference
  `acyclicity.join_tree` instead of repeating it.
- Extra report fields: `solver`, `seed`, `wall_seconds`, `Width.detail`, `acyclicity.gyo_residue_size`, and in
  `stats` `distinct_role_sets`, `incidences`, `components_without_universal`, `core_roles`, `core_relations`.
- The text form follows §4.3; value columns show `3`, `[2, 4]`, or `(1, 3/2]` for an exclusive fhw lower bound.
- **Format `khg-width-report/0.2.0`** (§4.2 said 0.1.0; review F9): each `widths.<m>` gains `lower_witness`, what the
  lower bound rests on, checkable against H: the clique (with ρ, or ρ* and its dual) for the clique bounds; the
  clique and the relation (rank) or the simplicial neighbourhood for tw; the block, the universal roles and the
  offset for minor-min-width; the induced set X; the refuted k with the tool and command; the inequality and the
  measure it came from; the join tree, `cyclic`, `empty` or `dp`. `test_survey` checks the 0.1.0 reports of 5f8683d
  as they are and the witnesses of every 0.2.0 report.
- `bad-json` is a truncated document (J001).

### 2.7 Tests and the gate

| Module | Gate | What it asserts |
|---|---|---|
| `test_cli.py` | G2 | every row of `fixtures/expected.csv` (12 rows: DESIGN §5.1 plus P2's `+time` variants): class, first failed test, the implied tests (`None`), witness, four exact widths with validated certificates; the §4.3 text; exit codes 0/1/2; `.json.gz` (Q5); a missing requested solver |
| `test_gate.py` | G3 | the four constructed cyclic schemas are flagged, residue equal to P2's `is_alpha_acyclic`; one fixture per boundary gives the five classes in order |
| `test_acyclicity.py` | G2, G3 | R01's 400 seeded random hypergraphs against the brute-force definitions (class split 72/118/78/31/101, as R01); witnesses; join trees; α against P2 |
| `test_widths.py` | G2 | on the same 400, the reported widths equal the truth from outside khg_width (review F2): tw, ghw and fhw by brute force over every elimination ordering of the *unreduced* H (≤ 7 roles; ρ over every set of traces, ρ* by an LP solved through its dual's vertices), hw as recorded from BalancedGo `-exact -det` and log-k-decomp `-exact` (`fixtures/random-hw.json`), also for 150 denser hypergraphs and R01's named instances; the inequalities; lifted certificates validate; bounds contain the truth at `time_limit=0.01`; Q3's +1 per universal role and no twin merging for tw; the lazy Bron–Kerbosch against brute force; partial steps logged (F7); every lower bound's witness checks out (F9) |
| `test_validate.py` | G2 | each condition's injected violation, (4) on p6-adler's width-2 GHD, demotion, a 5,000-node chain |
| `test_covers.py` | G2 | ρ\* of the triangle (3/2) and K5 (5/2) with both certificates; exact ρ; SciPy rounding (skips without SciPy) |
| `test_solver_parsers.py` | G2 | recorded outputs (built here and R01's), "SCV found!" demotion, neutral-id round trip, echoed edge counts, contradicted refutations |
| `test_schedule.py` | G2 | ruling Q8 on p6-adler with a scripted stand-in for BalancedGo: bisection order and bounds, a preprocessed "no" is no bound, an undecided k moves the search up, the budget caps all attempts; a decomposition the tool rejected itself is `invalid`, not a refutation (F1); a demoted GHD's attempt label follows what was used, and its `hd-repair` HD becomes an hw bound (F8, Q11) (always runs) |
| `test_solvers_live.py` | G2 | (`solvers`) both tools and `auto` agree with Python on every cyclic fixture; second opinion at k − 1; a timeout kills the process group; discovery order (fake binaries, always run) |
| `test_sources.py` | G1 | the mini raw set (rules 5, 6a, 8, time, meta, end cause, required, no value, deprecated, unknown ids); P3a counts in both scopes win over SQID; a wrong naming is refused; the P3a cross-check; the time model from any observed use (Q10); `manifest.verify`; Biolink rows and extraction (skips without linkml) |
| `test_survey.py` | G1 | (`survey`) as DESIGN §5.2, and every lower, upper, exact and method cell equals the report, each `survey.md` line equals one rendered from the report (F5), and the lower-bound witnesses of 0.2.0 reports check out on H (F9); rows in `pending-rerun.json` are skipped |
| `test_survey_scripts.py` | G1 | `install`: P3a-based files supersede SQID-based ones, which move with their reports to `superseded/` (F3); identical files are left untouched, provenance included (F4); other differences need `--new-snapshot`; `reproduce.sh` installs through `run_survey.py` |
| `test_hygiene.py` | — | import loads nothing heavy and spawns nothing; the API names are functions |

## 3. Sources and generation (§2.4, §2.5, §6.2)

- **Rule 8** is read as wd-roles states it: the 57 properties are out of scope *as relations*. They stay qualifier
  roles wherever they are used as qualifiers. The prototype dropped them as qualifiers of the observed tables (not of
  the declared one); wd-roles is the naming authority, so this follows it.
- **Rule 6 (ruling Q10).** "Uses" means any observed use in the source's scope: the interval model (and its two
  time usages) is decided on the unthresholded usage in every observed table, as `crosscheck_p3a` and P3a's
  `time_model` define it; the robust thresholds still choose the qualifier roles. The declared table keeps its
  allowed-qualifier constraints. The note `time_model_from_unthresholded_use` counts the relations that get the
  model only this way (observed-robust: 1,367).
- `primary {subject, object}` is written on every relation (r1 rules 2–3; the prototype wrote none). Relations are
  sorted by numeric property id. A self-qualifier role is labelled "<label> (as a qualifier of itself)"; roles of the
  relation-local control carry no labels or mappings. A required qualifier gets min 1 unless it is a time bound.
- **P3a's file (ruling Q9).** The reader follows the format the P3a session gave on 2026-09-24: top level `dump`
  (`"20260922"`, read as the counts date 2026-09-22), `naming` (must be `wd-roles r1`, else refused), `all`
  (`relations`, `out_of_scope_relations`), `kept` (`relations`), `out_of_scope`; per relation an integer
  `statements` and `qualifiers` `{role: {statements, snaks}}` keyed by r1 role ids. `P<id>:qualifier` maps back to
  the self-qualifier and `khg:end_cause` to P1534; a qualifier keyed by the relation's own id (the main-value role)
  is refused. A `format` key is not in the given top level; when present it must be `p3a-qualifier-usage/1`. The
  optional extras (`slot`, `time_model`, `left_out_6b`, `rank_reason_mismatch`, `self_qualified`, `arity`) are
  tolerated; `slot`, `time_model` (a string or `{"model": …}`), `out_of_scope` and the ids of
  `all.out_of_scope_relations` go to the cross-check (`p3a-crosscheck.json`). Scope `dump` reads `all.relations`,
  scope `slice` reads `kept.relations`. With P3a's file, the dump-scope observed files are rebuilt from it too (§2.5:
  P3a first, SQID otherwise); the SQID-based ones move to `results/superseded/`. The test fixture
  `tests/mini/wikidata/p3a-qualifier-usage-mini.json` has exactly this shape, every optional extra included.
- Biolink: ids `p6-biolink-{formal,formal-domain}-{global,relation-local}`; the extraction reproduces the probe's
  `biolink-associations.json` exactly; residues 5/18 (formal) and 5/19 (formal + domain) as R02.
- Wikidata residues under r1 (core,qualifier): declared 391/615 (R02's value exactly; 392/617 with time),
  observed-robust 748/542 (R02: 741/537), observed-all 1,441/2,012 (R02: 1,423/1,982). The differences come from rule
  5, rule 6a and the kept out-of-scope qualifiers; R02's numbers were expectations, not targets.
- Generation takes 142 s (DESIGN: about 2 minutes), dominated by `check_schema` on the large documents, and is
  deterministic: two runs gave identical bytes. The Wikidata `.json.gz` files total 3.6 MB (DESIGN: about 4 MB).
- Provenance records `git describe --dirty` (the files are generated before their commit, so it reads the previous commit with `-dirty`)
  and the sha256 of the generator sources used (`sources/wikidata.py`, `data/wd-roles-r1.json`,
  `sources/biolink.py`), which identify the generator exactly.
- `run_survey.py generate` builds into a temporary directory and installs from it (`install`, review F3/F4); a file
  counts as unchanged only when both its sha256 and its C1 schema digest match (a different zlib could change the
  gzip bytes without changing the schema), and is then left untouched, provenance included. Any other difference
  stops, unless `--new-snapshot` replaces the files, or the difference is the expected one of P3a's counts replacing
  SQID's (§4).

## 4. Survey scripts (§6)

- **Installing schema files (review F3, F4).** `install` (inside `generate`, and `run_survey.py install --from DIR`)
  handles each generated file: identical to the committed one: untouched; new: installed; an SQID-based observed
  file replaced by a P3a-based one: expected, and the SQID-based schema, its provenance and its rows' reports move to
  `results/superseded/` (DESIGN §6.6); any other difference: refused unless `--new-snapshot`. The rows of every
  installed file are listed with the reason in `results/pending-rerun.json`; `run` removes a row from it when the row
  re-runs, and the file goes when it is empty. `run_survey.py pending --add ROWS --reason TEXT` lists rows whose
  reports a checker change made stale. `reproduce.sh` step 3 is `generate` (with `--p3a-counts` and
  `--new-snapshot` passed through) followed by `pending`.
- Rows as §6.3, with ids `wd-<table>[-slice]-<naming>-<cq|cqt>` and `biolink-<qualifiers>-<naming>-cq`; `--rows`
  takes ids, fnmatch patterns and the groups `wikidata`, `biolink`, `declared`, `observed`, `slice`, `controls`,
  `headline`, `all`. Rows run as `python -m khg_width` subprocesses; `--jobs N` runs N at a time.
- Reports are compact JSON in deterministic gzip (`reports/<row>.json.gz`, mtime 0, level 9; ruling Q6). An
  indented report of a 13,608-relation row was 9 MB, compact 4 MB; gzip reduces that several-fold.
- The CSV has DESIGN's columns plus `file_sha256` (the file hash Q5 asks for; `schema_sha256` is the C1 digest).
- `hyperbench_baseline.py` reads `Run.csv` and `Type_of.csv` straight from the verified zips and reproduces R01 §3.5
  exactly (n = 1,113; hw 1/2/3 = 673/432/8; one inconsistent graph, `rand_q0135.hg`; exactness by size as R01).
- The figure is a static light-mode paper figure (matplotlib, `svg.hashsalt` fixed, no dates in metadata); its three
  colours are the first three slots of the dataviz reference palette, validated all-pairs; exactness is also encoded
  by mark shape (point against interval).
- The HyperBench manifest lives at `datasets/hypergraph-benchmarks/hyperbench/` (Q1), not at §6.1's
  `knowledge-bases/hyperbench-zenodo-7180787/`. Both files' md5 match the Zenodo record (API, 2026-09-24).

## 5. Smoke run (scratch, not `results/`)

`run_survey.py generate` (both into scratch and into `results/schemas/`: identical bytes), the three Biolink rows with
`--solver python`, `wd-declared-wd-roles-r1-cq` with `--solver auto` (BalancedGo and log-k-decomp built here) at a
30 s step limit, the HyperBench baseline, `table` and `make_figure` (byte-identical on a rerun). `test_survey`'s
Biolink and HyperBench tests pass on that directory (`KHG_WIDTH_SURVEY_RESULTS`).

| Row | Class (GYO residue) | hw | ghw | fhw | tw | Wall |
|---|---|---|---|---|---|---|
| biolink-formal-global-cq | cyclic (5 relations, 18 roles) | 2 | 2 | 2 | 19 | 0.6 s |
| biolink-formal-domain-global-cq | cyclic (5, 19) | 2 | 2 | 2 | 23 | 0.6 s |
| biolink-formal-relation-local-cq | berge | 1 | 1 | 1 | 19 | 0.7 s |
| wd-declared-wd-roles-r1-cq (30 s steps) | cyclic (391, 615) | [3, 52] | [3, 29] | [11/4, 27] | [116, 259] | 347 s |
| HyperBench non-random CQs | n = 1,113 | 1/2/3: 673/432/8 | | | | 1.3 s |

In the Wikidata row BalancedGo timed out at every k from 3 to 10 (7.5 s unflagged, then 22.5 s flagged): 240 of
the 347 s. The Python steps that used their full 30 s were min-fill (tw and ghw) and the clique enumeration.

Probes at a 5 s step limit, Python only (scratch): `wd-declared-relation-local-cq` 6 s (tw 116 exact),
`wd-observed-all-relation-local-cq` 58 s (tw 760 exact; most of it is `load_schema` of a 14 MB document),
`wd-observed-robust-wd-roles-r1-cq` 60 s (hw [3, 68], ghw [3, 29], tw [55, 145]), `wd-observed-all-wd-roles-r1-cq`
72 s. Heuristics without a limit: min-degree 0.4 s / 0.1 s / 58–64 s and min-fill 103–115 s / 10 s / skipped (over
1,500 roles) on the declared / observed-robust / observed-all blocks.

**After ruling Q8: the declared row at the survey's own settings** (`--solver auto --time-limit 600`, scratch):
2,017 s in all, 809 s of Python steps (clique enumeration 600 s, min-fill 95 s and 106 s, the rest seconds) and
exactly 1,200 s of solver attempts. The bisection started from [4, 38] (the clique bound and hd-repair) and probed
k = 21, 30, 34 and 36: every attempt, BalancedGo and log-k-decomp with preprocessing and BalancedGo without, timed
out at 120 s, so the budget ran out with hw in [4, 38]; ghw [4, 25], fhw [3, 24], tw [116, 235]; no disagreements.
The reports of this probe are 136 KB (declared) and 4–11 KB (Biolink) as `.json.gz`.

**Estimate for the full survey** (dump-scope rows, Biolink, controls, baseline; `--time-limit 600`, `--jobs 3`, 4
cores): generation 2.5 min; each wd-roles row about 30–36 min (11–14 min of Python steps plus the 20-minute solver
budget, which the Wikidata cores use in full); the 6 relation-local controls 6–60 s each (α-acyclic: no solver);
Biolink under 1 s each plus one confirming solver call; baseline, table and figure seconds. The 6 wd-roles rows
take about 3.5 h serially and about **1.25–1.5 h with `--jobs 3`** (two waves of three rows, the controls in between).
The 4 slice rows add about 1.2 h serially once P3a's counts land.

## 6. The director's rulings on these notes (2026-09-24; DESIGN §9, Q6–Q9)

| Question raised here | Ruling | What changed |
|---|---|---|
| P3a's file layout was assumed | **Q9**: the format P3a specified | `sources.wikidata.read_counts` and `crosscheck_p3a` rewritten to it; the mini fixture and `test_sources` follow it exactly (§3) |
| Report size (4 MB per large row) | **Q6**: commit reports as `.json.gz`, deterministic | `run_survey.py` writes and reads `reports/<row>.json.gz`; `test_survey` checks the gzip mtime (§4) |
| Keep `hd-repair` and the tw-based ghw certificate? | **Q7**: keep both | unchanged (§2.4) |
| Solver budget (up to 80 min per row at 600 s per k) | **Q8**: bisection, 120 s per attempt, 20 min per row | the schedule of §2.5; `test_schedule.py` |

## 7. Review fixes F1–F9 and the rulings Q10–Q11 (2026-09-24; DESIGN §9)

The review of the first full survey (5f8683d) found no wrong number in the table. It found nine defects in the
checker, its tests and the survey scripts. Each fix below has a regression test. The regression tests were run
against the source of 5f8683d: every one listed fails there. The exceptions are the test-only findings F2 and F5,
whose checks are shown differently. `test_cli`'s format assertion (0.2.0) also fails there.

| Finding | Fix | Regression test (fails before the fix) |
|---|---|---|
| **F1** `Correct: false` read as "no" | `parse_stdout` collects the tools' check-failure lines (`Decomp of different graph`, `Empty Decomp`, `Bags not subsets of edge labels`, `Edge … isn't covered`, `Vertex … doesn't span connected subtree`). "no" requires an empty tree and none of them. Otherwise the outcome is `invalid`: it is logged as `solver-invalid`, it is never a bound, and it decides nothing at its k (§2.5) | `test_schedule.py::test_self_rejected_decomposition_is_not_a_refutation`: the stand-in prints a tree, `Edge  R2  isn't covered` and `Correct: false` for the unflagged run; the old code took it as a refutation |
| **F2** widths tested against khg-width itself | `helpers.py` gains independent oracles: brute force over all elimination orderings (tw, ghw, fhw, ≤ 7 roles), ρ over every set of traces, and ρ* by an LP solved through the vertices of its dual (Fraction Gaussian elimination). hw comes from `fixtures/random-hw.json`, recorded by `tests/record_random_hw.py` with BalancedGo `-exact -det` and log-k-decomp `-exact`, which must agree: the 400 random hypergraphs (hw 1/2: 299/101), 150 denser ones (seed + 1; hw 1/2/3: 1/148/1) and R01's named instances (b_triangle 2; k5, adler, c_grid4, c_grid5, grohe_marx_3: 3). CI needs no binaries | Test-only. The reviewer's mutation (`exact.py:274`, `em[j] & scope` → `em[j] & c`) passes the old suite and fails the new one: `test_hw_matches_the_recorded_solvers` (a dense hypergraph: 3 against the recorded 2). The random 400 alone could not catch it, because none has hw 3 |
| **F3** P3a regeneration overwrote the SQID files in place | `_supersede_sqid` is gone. `generate` builds into a temporary directory, and `install` moves each SQID-based observed schema, its provenance and its rows' reports to `results/superseded/` when a P3a-based file replaces it (DESIGN §6.6). That replacement is expected; any other difference needs `--new-snapshot` (§4) | `test_survey_scripts.py::test_p3a_counts_supersede_sqid_files_and_reports`, `::test_other_differences_need_a_new_snapshot` and `::test_reproduce_installs_through_run_survey` |
| **F4** provenance rewritten when schemas match | `install` leaves identical files (file sha256 and C1 digest) untouched, provenance included | `test_survey_scripts.py::test_identical_schemas_are_left_untouched` (bytes and mtimes unchanged) |
| **F5** `check_row` compared only the upper cells | Every lower (with the `>` of an exclusive bound), upper, exact and method cell is compared with the report, and so are the stats cells. Each `survey.md` line must equal one rendered in the test from the report and the CSV row | Test-only. On a copy of `results/` (`KHG_WIDTH_SURVEY_RESULTS`), two tampered cells pass the old `test_biolink_rows` and fail the new one: `tw_lower` 19 → 18 in `survey.csv`, and the hw cell 2 → 3 in `survey.md` |
| **F6** rule 6 read against thresholded use | Ruling Q10 (below) | `test_sources.py::test_time_model_from_any_observed_use`: P31, used with P580 below the robust threshold, gets the interval model in observed-robust and observed-all under both namings |
| **F7** a step stopped at its deadline was logged `done` | `clique_bounds` returns `CliqueBounds` with `complete`, and `TwReduced` records the clique behind its bound. `StepLog.run` logs a result with `complete=False` as `timeout (partial kept)` | `test_widths.py::test_partial_steps_are_logged` |
| **F8** demoted attempts labelled "ghw upper bound" even when not used | The label follows `offer_upper`'s return value: `ghw upper bound g (demoted HD)` or `no ghw bound (…; ghw <= u already)`. Then, by Q11, it adds `hw upper bound w (hd-repair)` or `no hw bound (…)` | `test_schedule.py::test_demoted_attempt_label_and_hd_repair` and `::test_demoted_ghd_can_lower_ghw_and_hw`; `test_solver_parsers.py::test_scv_demotes_to_ghw` updated |
| **F9** lower bounds without witnesses | `Bound.raise_lower(…, witness=…)` at every site, stored as `widths.<m>.lower_witness`. The report format is now `khg-width-report/0.2.0` (§2.6) | `test_widths.py::test_lower_bound_witnesses` (a 24-ring plus K5, and every fixture, through `helpers.check_lower_witness`); `test_survey` checks the witnesses of every 0.2.0 report |

**Ruling Q10** (F6). In wd-roles r1 rule 6, "uses" means any observed use in the source's scope, with unthresholded
counts. `build()` now decides the interval model from `observed-all`'s qualifier usage for every observed table.
The declared table still uses its constraints (§3). Only `p6-wikidata-observed-robust-*` change. Under wd-roles r1,
1,367 relations get the interval model only this way: time bounds added 260 → 2,994, `slot_time` 1,612 → 4,346, and
5 end causes move from meta to the built-in. In the relation-local control, roles go from 39,587 to 42,316. Both files
and their provenance were regenerated with `run_survey.py generate --new-snapshot`. The other four Wikidata files
came out byte-identical and were left untouched (F4). The `core,qualifier` hypergraphs of both changed files are
identical to before, because only time roles changed. With time, the wd-roles r1 GYO residue goes from 755/545 to
765/552.

**Ruling Q11** (F8). A demoted GHD also goes through `hd-repair`. The repaired HD, once validated on H, is offered as an
hw upper bound (method `hd-repair:<tool>-demoted`). The `demotion` entry records `ghw_bound_used`,
`repaired_hd_width` and `hw_bound_used`.

**Rows to re-run** (`results/pending-rerun.json`; `test_survey` skips them until then):

- The six wd-roles r1 rows (declared, observed-robust and observed-all; cq and cqt). Their reports predate F1, F8,
  Q11 and F9: `wd-declared-wd-roles-r1-cqt` had a demotion that Q11 now repairs, and 0.1.0 reports carry no
  witnesses. The two observed-robust ones also have a new schema file (Q10).
- `wd-observed-robust-relation-local-{cq,cqt}`. Their schema file changed under Q10, so the table's sha256 no
  longer matches. They are α-acyclic, take seconds and make no solver calls.

The Biolink rows and the four other relation-local rows keep their 0.1.0 reports. Their numbers cannot change: the
relation-local rows make no solver calls, and each Biolink row's only call refutes k = 1 on a cyclic H, where
hw ≥ 2 holds anyway.

**Test counts after the fixes.** In a fresh Python 3.10 venv with `[dev]` only, as the CI job runs:
88 pass and 20 skip. With SciPy, linkml, both solvers and the committed results: 108 pass. `pyflakes` is clean.
