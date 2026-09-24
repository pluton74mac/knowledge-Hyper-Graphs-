---
title: "P6 design: the khg-width checker and the schema width survey"
type: project
status: draft
created: 2026-09-24
---

# P6 design: the khg-width checker and the schema width survey

This is the design for P6 ([README](README.md); [PLAN §3–§5](../PLAN.md)). It rests on two research reports, cited
as [R01] ([theory and solvers](research/01-theory-and-solvers.md)) and [R02]
([data and naming](research/02-data-sources-and-naming.md)), and on the role naming in [wd-roles.md](wd-roles.md). It
adopts R01's D1–D12 under the director's F1–F8, and consumes C1 `khg-relation-schema/1.0.0`
([P2 DESIGN §3](../p2-role-aware-hif/DESIGN.md)). **Objections to F1–F8: none.** Two readings of F1 are raised as
Q2 and Q3 (§9).

## 1. Summary and the gate

P6 ships three things:

- **`khg-width`**, a small MIT package in `projects/p6-schema-width/khg-width/`. For a relation-schema file it reports:
  - the acyclicity class (Berge, γ, β, α or cyclic) with a witness;
  - hw, ghw, fhw and tw, each exact or as `[lower, upper]`, with its method and a decomposition validated in Python.

  The core is pure Python on top of khg-contracts. BalancedGo and log-k-decomp are optional: a script builds them
  outside git, and the checker calls them when present.
- **The survey.** 12 Wikidata rows (3 sources × 2 namings × 2 slot sets), 3 Biolink rows and a HyperBench baseline.
  `results/` holds the table, a figure, the measured schema files and a reproduce script.
- **A short note** (§8). The owner publishes it; nothing is published from this session.

| Gate clause (PLAN §4) | How it is met | Test that proves it |
|---|---|---|
| "Survey table for the Wikidata qualifier schemas" | `results/survey.{md,csv}`: the 12 rows of §6.3 | `test_survey.py::test_wikidata_rows`: all rows present; each file reloads with a matching sha256; class and core recomputed; every stored decomposition re-validated |
| "…and the biomedical schema" | 3 Biolink v4.4.5 rows | `test_survey.py::test_biolink_rows`: recomputed with `--solver python` and compared |
| "the checker reports class and width for a given schema file" | `khg-width SCHEMA_FILE` (§4.3) | `test_cli.py::test_fixture_table`: class, witness and four exact widths for every §5.1 fixture. `test_cli.py::test_exit_codes` |
| "…and flags a constructed cyclic case" | class `cyclic`, with the GYO residue as witness | `test_gate.py::test_constructed_cyclic` (P2 `cyclic`, P2 `wikidata-shaped`, `p6-qualifier-k5`, `p6-adler`). `test_gate.py::test_one_per_boundary`: the five classes are told apart |

The survey tests carry the marker `survey`. They skip ("survey not run") until `results/survey.csv` exists; from then
on CI runs them. A cyclic schema is flagged in the report, by its class and witness. The exit status stays 0, as F4
fixes it.

Where R01's decisions land: D1 and D4 in §2.1, D2 in §2.3, D3 in §2.4, D5 in §3, D6 in §4.5, D7 in §3.7, D8 in §3.2,
D9 in §5, D10 in §6.4, D11 in §3.6, D12 in §3.3–§3.4.

## 2. The measured object

### 2.1 Which hypergraph (D1, D4)

**H(S, σ) = `schema_hypergraph(S, slots=σ)`**, for a schema S and a slot set σ.
- Vertices are global role ids. Each relation gives one edge: the roles of its usages in σ.
- A role is one vertex whatever its slot.
- Lifecycle relations and relations with no usage in σ are left out.

H is kept as a **named multi-hypergraph**, keyed by relation id. The measures read it in two ways:
- **Berge** is computed on the multi-hypergraph, where two relations with the same role set form a cycle.
- **α, β, γ and the widths** are computed on the set hypergraph. Duplicate role sets are reported as their own
  finding.

**What the number means.** It is the width of the query that joins all relations on same-named roles (Fagin's
scheme setting). It is not the width of arbitrary KHG queries, which join on entities ([R01 §2.5]). Berge reads
directly for stores: the reified encoding is acyclic exactly when H is Berge-acyclic ([R01 §1.3]).

### 2.2 From a relation-schema file to H

1. **Read.**
   - `.json`: `load_schema(path)`, which runs layers J, V and M.
   - `.json.gz`: gunzip, then `jsonio.loads` (J), then `load_schema(mapping)` (V and M).

   Any error finding gives exit 1.
2. **Identify.** The report records:
   - the schema's `id` and `version`;
   - `sha256`, which is `Schema.sha256`, the `khg-schema/1` digest that C1 headers pin;
   - `file_sha256`, the hash of the file's bytes.
3. **Build and describe.** `schema_hypergraph` gives H. The report adds counts, rank, maximum degree, BIP, duplicate
   groups, components, and the **universal roles**: those in every relation, such as `subject` under wd-roles.
   Degree and BIP are computed without universal roles.
4. **Neutral ids for solvers.** Relations become `R<i>` and roles `V<j>`, and a mapping is kept.
   - BalancedGo panics when an edge and a vertex share a name, and wd-roles gives relation `P39` a role `P39`.
   - Other tools reject or drop names containing `-`, `.` or `:` ([R01 §4.3]).

### 2.3 Slots (D2)

- **Headline:** `core,qualifier`.
- **Variant:** `core,qualifier,time`. It turns P2's fixture from Berge into γ.
- **`meta` is refused** with exit 2, so `khg:end_cause`, P2241 and P7452 never enter H.
- `core` is required in every slot set.

### 2.4 Role naming (D3, F2)

**Wikidata uses `wd-roles r1`**, whose authoritative text is [wd-roles.md](wd-roles.md).
- P6 proposed it as r0 ([R02 §5]). P3a adopted it with amendments 6a–6c, and the director accepted them.
- Every survey row and every schema file's provenance records `wd-roles r1`.
- The rules sit in one data file, `khg_width/data/wd-roles-r1.json`: the meta list, the time bounds, the excluded
  classes, the datatype map and the thresholds.

| Naming | Subject | Main value | Qualifier | Self-qualifier |
|---|---|---|---|---|
| **wd-roles r1** (headline) | `subject` | property id (`P39`) | property id (`P580`) | `P131:qualifier` (rule 5; R02's probe dropped it) |
| **relation-local** (control) | `P39:subject` | `P39:value` | `P39:P580` | `P131:P131` |
| **Biolink global** (headline) | `subject` | `object` | slot name (`object_aspect_qualifier`) | n/a |
| **Biolink relation-local** (control) | `<Class>:subject` | `<Class>:object` | `<Class>:<slot>` | n/a |

**The controls** keep the slot rules of their headline naming (6a included) and scope every role id to its relation.
Their edges are then pairwise disjoint: Berge-acyclic, every width 1. This shows that width comes from shared names.

**The r1 rules that shape a schema file:**
- `primary {subject: "subject", object: <P>}`.
- `time` is P580 and P582. A relation that allows or uses either gets the interval model.
- `meta` is the 24 listed properties, plus P2241 and P7452. Under 6c those two are meta bindings when they do not
  match the rank.
- Everything else is `qualifier`.
- P1534 becomes `khg:end_cause` on interval relations.
- **6a:** relations P580 and P582 get no time model.
  - Their P580 and P582 qualifiers become `qualifier` usages.
  - The one repeating the relation's own property becomes `P580:qualifier` or `P582:qualifier`.
  - Under r0 these relations failed M007; a generator test covers them.
- A required-qualifier constraint gives `min: 1`.
- The 57 properties that document or constrain other properties are excluded.

Rules 6b and 9 concern the corpus. Two rules move R02's numbers:
- **Self-qualifier roles** lie in one edge. GYO removes them, so the class and the residue do not change; R02
  counted 9, 14 and 441 such relations.
- **6a can change the residue.** Under `core,qualifier` it puts P582 into relation P580's edge and P580 into
  P582's.

R02's residues are therefore expectations, not targets.

### 2.5 Sources, counts and dates (F2, F6)

| Source | Relations | Qualifiers per relation |
|---|---|---|
| **declared** | 1,155 properties with a non-deprecated allowed-qualifiers constraint (Q21510851/P2306; statements united; "no value" = none) | the allowed list. WDQS main graph, 2026-09-24 09:35–09:44 UTC |
| **observed-robust** | properties with ≥ 1 main statement, minus the 57 (13,608 under SQID) | **≥ 10 uses and ≥ 0.1 %** of the property's main statements |
| **observed-all** | same | ≥ 1 use |

**Where the observed counts come from.** The column `counts_source` and the row's date record which source was used.
1. **P3a's exact counts**, when committed with their manifest ([wd-roles.md](wd-roles.md), "What P6 takes from P3a").
   They cover the whole **2026-09-22** dump.
   - Uses are statements carrying the qualifier.
   - The denominator is the relation's statement count from the same file, so both share one date.
2. **Otherwise, SQID `qs`** from the **2026-08-10** dump, with DeltaBot main-statement counts (revision 2548855541,
   **2026-09-23**). The two dates differ, which is a stated limit.

Unknown qualifier ids are dropped and counted.

R02's sizes (r0, SQID) as expectations:

| Source | Roles (cq) | Largest edge | GYO residue cq (edges/roles) | +time |
|---|---|---|---|---|
| declared | 1,883 | 117 | 391 / 615 | 392 / 617 |
| observed-robust | 13,655 | 34 | 741 / 537 | 748 / 540 |
| observed-all | 13,690 | 749 | 1,423 / 1,982 | 1,428 / 1,987 |
| Biolink formal, global | 35 (103 relations) | 20 | 5 / 18 | n/a |

**Biolink** is v4.4.5 (commit `a4180f8`), with one relation per concrete association class.
- The core is `subject` and `object`. `predicate` is the relation type, not a role.
- *Formal* qualifiers are the slots under `qualifier`. *Formal + domain* adds the 25 truth-changing slots of R02's
  `DOMAIN_TRUTH_CHANGING`.
- Meta slots are not generated.
- Biolink has no interval bounds, so it has no `+time` rows.

## 3. Algorithms, witnesses and validation

### 3.1 Acyclicity classes

Berge ⊂ γ ⊂ β ⊂ α. The tests run from α down and stop at the first failure:

1. **α** by `khg_contracts.schema.is_alpha_acyclic` (the C1 GYO). If it fails, the class is **cyclic** and the
   witness is the GYO residue. The stricter tests are *implied false* and not run, so the Wikidata tables take
   seconds.
2. **β** by indexed nest-point elimination. If it fails, the class is **α** and the witness is a **β-cycle**: a
   chordless incidence cycle x₁E₁…x_kE_k with k ≥ 3.
   - It is searched in the β residue by budgeted iterative deepening; a cycle of H[residue] lifts to H.
   - If the budget runs out, the residue is the witness, flagged.
3. **γ** by the indexed D'Atri–Moscarini reduction. If it fails, the class is **β** and the witness is a
   **γ-triangle**.
   - It is searched in the DM residue, which is β-acyclic but not γ-acyclic, so it contains one.
4. **Berge** by union–find on the incidence graph of the multi-hypergraph, in linear time. If it fails, the class is
   **γ** and the witness is the cycle v₁R₁…v_kR_k. Otherwise the class is **berge**.

When H is α-acyclic, a join tree (ear removal, R01's `p6check.gyo`) is checked for running intersection and serves
as the width-1 HD. A result that contradicts the hierarchy stops the run with an internal error.

### 3.2 Reductions (D8, F1)

A reduction serves a measure only where the table allows it. Every upper bound found on a reduced hypergraph is
**lifted back to H and validated there** (§3.6), so no certificate rests on a reduction theorem.

| Reduction | ghw, fhw | tw | hw | Lifting |
|---|---|---|---|---|
| **Lonely role** (v in one edge e) | sound ([R01 §5.2]) | only as the simplicial rule, tw = max(\|e\|−1, tw(H−v)); an edge of size r forces tw ≥ r−1 | no | a leaf with bag e and guard {e} |
| **Subsumed edge** (e ⊆ f) | sound | sound (the primal graph is unchanged) | no | none |
| **Twin merge** | sound | **unsound** (K_n has tw n−1) | no | add the twin wherever its partner is |
| **Universal role** | sound ([R02 §3.4]) | exact: +1 per role | no | add it to every bag |
| **Block split** | sound: the maximum over blocks | sound | no | join at the cut role |

**hw is computed on the unreduced H** (F1).
- Solvers receive H itself.
- Their internal `-g -t -h` preprocessing may be used to *find* an HD, which must then pass all four HD conditions
  on H (Q2).
- The *core* is H after GYO, twin merging and universal-role removal.
- The report lists every reduction, what it removed and which measures it served.

Two points depart from F1's wording, and are raised as Q3:
- For tw, GYO is applied only in its sound form (the simplicial rule) and twins are never merged.
- Universal-role removal is added.

### 3.3 Exact procedures

- **α-acyclic, non-empty:** hw = ghw = fhw = 1, certified by the join tree. An empty H has all widths 0.
- **tw, ghw, fhw** by the subset DP over elimination orderings ([R01 §4.6]; Moll, Tazari and Thurley):
  F(S) = min_v max(F(S∖v), f({v} ∪ Q(S∖v, v))).
  - The bag cost f is \|B\|−1 for tw, ρ(B) for ghw and ρ\*(B) for fhw.
  - It runs per core block, on up to 20 roles (16 for fhw).
  - ρ is found by exact search over maximal traces.
  - ρ\* comes from an **exact rational simplex**, whose primal and dual solutions are both checked.
  - The ordering yields the decomposition that is lifted.
- **hw** by the det-k-decomp-style normal-form search for k = 1, 2, … (Gottlob and Samer).
  - It runs on the unreduced H when H has ≤ 60 relations, with 3·10⁶ separator trials per k.
  - A "no" is exhaustive, so it counts as a refutation.

### 3.4 Bounds

**Lower bounds** are sound and labelled by method:
- **cyclic:** hw, ghw ≥ 2 and fhw > 1, the last reported as `lower_exclusive`.
- **Clique bounds:** ghw ≥ ρ(K) and fhw ≥ ρ\*(K) for primal cliques K of the core, enumerated by Bron–Kerbosch.
- **Induced bounds.** All four measures are monotone under H ↦ H[X] = {e ∩ X}: restricting bags and guards to X
  keeps every condition, the special condition included. So an exact value on a small H[X] is a lower bound.
  - X is grown greedily from high-degree core roles, from several seeds.
  - X has ≤ 18 roles (16 for fhw).
  - The methods are `induced-dp` and `induced-hd-search`, and X is recorded.
- **tw:** max(rank − 1, simplicial, minor-min-width), plus the universal offset.
- **Solver refutations** count only from runs **without** preprocessing flags, and only if no other tool contradicts
  them.

**Upper bounds:**
- **Heuristic tree decompositions** (min-fill and min-degree, seeded) of each core block.
  - The bags give tw.
  - Greedy covers of the bags give ghw.
  - ρ\* of the bags gives fhw, by the exact simplex on small bags. With the `fast` extra, SciPy's LP rounded up to
    an exactly feasible rational cover; otherwise the greedy cover.
- **Solver HDs** give hw, and so ghw ≤ hw. They also give fhw ≤ max ρ\*(χ_t) (ImproveHD).
- **A trivial bound always exists:** hw ≤ \|E\|, from one node holding every guard.

**Propagation.** Bounds pass through fhw ≤ ghw ≤ hw ≤ 3·ghw+1, ghw ≤ tw+1 and ⌈fhw⌉ ≤ ghw until nothing changes, each
labelled `inequality`. A measure is **exact** when its lower bound (not exclusive) equals its upper bound.

### 3.5 External solvers (D6, F3)

- **BalancedGo** is primary, in DetK mode (`-det`), for hw only. It reports through `-json FILE`.
- **log-k-decomp** is the second opinion. It reports through `-gml FILE`, or the stdout tree as a fallback.

**Schedule for hw.** For k from the lower bound up to k_max = 10, stopping at the first validated "yes":
1. `-width k -det` **without flags**, for a quarter of the step limit T. A "no" is a refutation.
2. After a timeout, `-width k -det -t -h -g -heuristic 1` for the rest of T. These flags turned 300 s into 0.9 s on a
   418-edge instance ([R01 §4.5]). A "no" here is logged but not used as a bound.
3. With ≤ 60 relations, `-exact -det` replaces the loop.

**Second opinion.** Under `auto`, log-k-decomp reruns k_yes, and k_yes − 1 when that value was refuted.
- Every disagreement goes to `disagreements[]` with both commands, outputs and times: solver against solver, and
  solver against the Python search.
- A decomposition validated on H beats a refutation.
- A refutation that is contradicted is dropped from the lower bound.
- Nothing is discarded silently.

**Not used:**
- BalancedGo's `-local` and `-balDet` modes, which were not probed.
- HtdLEO, htdsmt and fraSMT as dependencies. They are manual cross-checks (`survey/crosscheck.sh`, output in
  `results/crosschecks/`).
- NewDetKDecomp and det-k-decomp, which have no licence.

### 3.6 Validation (D11)

`validate(H, D, kind)` checks a decomposition D against **H as given**:

| Kind | Conditions | Width |
|---|---|---|
| TD | (1) every edge lies in a bag; (2) the bags holding a role form a subtree | max\|χ_t\|−1 |
| GHD | TD, plus (3) χ_t ⊆ ⋃λ_t with λ_t ⊆ E(H) | max\|λ_t\| |
| HD | GHD, plus (4) the special condition (⋃λ_t) ∩ χ(T_t) ⊆ χ_t, computed bottom-up in linear time | max\|λ_t\| |
| FHD | TD, plus a cover with Σ_{e∋v} λ_t(e) ≥ 1 on χ_t, in exact rationals | max Σλ_t |

Rules:
- No upper bound is reported without a decomposition that validated.
- An HD that fails (4), or whose output says "SCV found!", is **demoted** to a ghw bound, and the demotion is logged.
- An echoed edge count that differs from H's is an error, which catches fraSMT-style silent misparses.
- Certificates are stored in role and relation names.

### 3.7 Time limits (D7)

`--time-limit T` bounds **each step**: a DP, a clique enumeration, an induced search, an hw-search level, or a solver
call at one k. The default is 60 s; the survey uses 600 s.
- Python steps check a cooperative deadline. Solvers run in their own process group and are killed when T runs out.
- Each step is logged with its measure, method, tool, k, limit, time and outcome (`yes`, `no`, `timeout`,
  `budget`, `error`).
- The class tests are polynomial and have no cap. The seed is 20260924.
- The survey records CPU and tool versions, since limits make results machine-dependent.

## 4. Package, API, CLI, dependencies, solver build

### 4.1 Layout

```
projects/p6-schema-width/khg-width/
  pyproject.toml  LICENSE (MIT)  README.md  scripts/build-solvers.sh
  src/khg_width/
    __init__.py  hypergraph.py  acyclicity.py  reduce.py  covers.py  decomposition.py
    exact.py  bounds.py  check.py  report.py  cli.py
    solvers/   discovery, balancedgo.py, logk.py, parsers (JSON, GML, text tree)
    sources/   wikidata.py, biolink.py (lazy linkml import), manifest.py
    data/wd-roles-r1.json
  tests/       fixtures/, recorded solver outputs, mini raw inputs
projects/p6-schema-width/survey/    reproduce.sh, run_survey.py, hyperbench_baseline.py, make_figure.py, crosscheck.sh
projects/p6-schema-width/results/   (§6.6)
```

### 4.2 Public API

```python
check(schema: str | os.PathLike | Mapping | Schema, *, slots: Sequence[str] = ("core", "qualifier"),
      time_limit: float = 60.0, solver: str = "auto", seed: int = 20260924) -> WidthReport
hypergraph(schema, *, slots=("core", "qualifier")) -> Hypergraph
classify(h: Hypergraph, *, budget: int = 200_000) -> Acyclicity
width(h, measure: Literal["hw", "ghw", "fhw", "tw"], *, time_limit=60.0, solver="auto") -> Width
validate(h, d: Decomposition, *, kind: Literal["td", "ghd", "hd", "fhd"]) -> Validation
find_solvers() -> dict[str, SolverInfo]      # path, commit, binary sha256, how found
```

The API types are frozen dataclasses:
- `Hypergraph(edges: Mapping[str, frozenset[str]])`, with `.induced(X)`, `.stats()` and `.neutral()`.
- `Acyclicity(cls, tests, first_failed, witness, join_tree)`. In `tests`, `None` marks a test implied and not run.
- `Witness(kind, value, complete)`, where `kind` is one of `berge_cycle`, `gamma_triangle`, `beta_cycle`,
  `beta_residue` or `gyo_residue`.
- `Width(measure, lower, upper, lower_exclusive, lower_method, upper_method, certificate, validation, steps)`, with
  `.exact`.
- `Decomposition(bag, cover: Mapping[str, Fraction], children)`.
- `WidthReport(format="khg-width-report/0.1.0", schema, slots, stats, acyclicity, widths, reductions, disagreements,
  tools, time_limit)`, with `.to_json()` and `.to_text()`.

Fractions are serialised as strings (`"3/2"`). P11 calls `check`.

### 4.3 CLI (F4)

`khg-width SCHEMA_FILE [--slots core,qualifier[,time]] [--time-limit SECONDS] [--solver auto|python|balancedgo|logk] [--json]`

- **`--solver`:**
  - `auto`: BalancedGo, then log-k-decomp as second opinion, when found; otherwise Python.
  - `python`: no external tool.
  - `balancedgo` or `logk`: that tool alone. Exit 2 if it is missing.
- **`--json`** prints the full `WidthReport`.
- **Exits** follow khg-contracts' conventions (results on stdout, diagnostics on stderr):
  - **0** when a report is produced, whatever the class.
  - **1** for an invalid schema. Every error finding of `load_schema` is printed (`code path message`): M codes, and
    J or V for malformed JSON or format.
  - **2** for usage or I/O errors: a missing file, bad `--slots` (`meta`, or no `core`), a bad limit, or a missing
    solver that was asked for.

```
schema      p6-qualifier-k5/0.1.0  sha256:3f…  file 9c…  slots core,qualifier
hypergraph  25 roles, 10 relations, rank 4, max degree 4, BIP 1, duplicates 0, universal none
class       cyclic (alpha fails)  witness: GYO residue, 10 relations on 5 roles
hw   3      exact  python hd-search on the input: k=2 no, k=3 yes; HD validated
ghw  3      exact  subset DP on core (5 roles); GHD lifted and validated
fhw  5/2    exact  subset DP + exact LP on core; FHD lifted and validated
tw   4      exact  subset DP after simplicial rule
reductions  gyo -20 roles [ghw,fhw]; twins 0; universal 0; blocks 1; simplicial 20 [tw]
tools       khg-width 0.1.0; khg-contracts 1.0.0; python 3.11; BalancedGo, log-k-decomp not found
```

### 4.4 Dependencies

- Build: hatchling, `license = "MIT"`, `requires-python = ">=3.10"`.
- Core: `khg-contracts>=1.0.0.dev0,<2`, the package at the repository root.
- Extras:
  - `fast`: SciPy ≥ 1.10;
  - `survey`: `linkml-runtime==1.11.1`, `pyyaml`, `matplotlib`;
  - `dev`: pytest ≥ 8.
- Console script: `khg-width = "khg_width.cli:main"`.
- Importing `khg_width` loads none of SciPy, linkml or matplotlib, and a test checks it.

### 4.5 Solver build and discovery (F3)

**`scripts/build-solvers.sh [DEST]`** builds the two solvers into a cache.
- `DEST` defaults to `${XDG_CACHE_HOME:-~/.cache}/khg-width/solvers`. The script **refuses a DEST inside the git
  working tree**.
- It needs git and Go (1.24.7 probed; `GOTOOLCHAIN=local`).
- It checks out the pinned commits:
  - BalancedGo `872c662c9f409aeb7386f963d2f16b88523ff4bf` (v1.7.2-2, MIT);
  - log-k-decomp `5e021dd442b028099c30deecc316a906a49a8cb3` (v1.1.0, MIT).
- It builds with `go build -trimpath -mod=readonly` into `DEST/bin/`, and smoke-tests `b_triangle` (width 2) on both.
- It writes `DEST/solvers.json`: commit, `git describe`, Go version, binary sha256 and licence.

**Discovery order:**
1. `KHG_WIDTH_BALANCEDGO` and `KHG_WIDTH_LOGK`;
2. `KHG_WIDTH_SOLVERS`, which names a DEST;
3. the default DEST;
4. `PATH`.

The `tools` block reports path, commit and sha256 (the commit is "unknown" when found on PATH). Without solvers,
§3.3–§3.4 still give results.

## 5. Fixtures and tests

### 5.1 Gate fixtures (F5)

The fixtures are in `tests/fixtures/`, with their expected values in `expected.csv`, which the tests read.
- The five `p6-*` boundary files come from R01's `probes/schemas/`.
- `p6-duplicate-role-set` and `p6-adler` are new; `p6-adler` is converted from `probes/instances/adler.hg`.
- P2's schemas come through `khg_contracts.data.path`.

The values are from R01's probes, where BalancedGo agreed on hw.

| Fixture | Slots | Class | First failed: witness | hw | ghw | fhw | tw |
|---|---|---|---|---|---|---|---|
| `p6-berge-path` | cq | berge | none (join tree) | 1 | 1 | 1 | 1 |
| `p6-duplicate-role-set` | cq | gamma | Berge: cycle through the duplicate pair | 1 | 1 | 1 | 1 |
| `p6-gamma-not-berge` | cq | gamma | Berge: seller–sale–buyer–brokered_sale | 1 | 1 | 1 | 2 |
| `p6-beta-not-gamma` | cq | beta | γ-triangle (broker, seller, buyer) | 1 | 1 | 1 | 2 |
| `p6-alpha-not-beta` | cq | alpha | β-cycle broker–brokerage–seller–sale–buyer–referral | 1 | 1 | 1 | 2 |
| P2 `fixture` | cq / +time | berge / gamma | none / Berge: start_time–position_held–end_time–married | 1 | 1 | 1 | 7 |
| P2 `cyclic` | cq | **cyclic** | residue = the triangle | 2 | 2 | 3/2 | 2 |
| P2 `wikidata-shaped` | cq / +time | **cyclic** | residue = qualifier triangle / 3 time+qualifier edges | 2 | 2 | 3/2 | 4 / 5 |
| `p6-qualifier-k5` (width 3) | cq | **cyclic** | residue = K5 on 5 qualifiers | 3 | 3 | 5/2 | 4 |
| `p6-adler` | cq | **cyclic** | GYO residue | **3** | **2** | 2 | 4 |

`p6-adler` is the only fixture with ghw < hw, so it tests condition (4).

The invalid inputs:
- `bad-m002`, where a role is used twice: exit 1, `KHG-M002`.
- `bad-json`: exit 1, a J code.
- A missing file, `--slots core,meta` and `--slots qualifier`: exit 2.

### 5.2 Tests

| Module | Checks | Gate |
|---|---|---|
| `test_cli.py` | `test_fixture_table` (`--json --solver python` on every §5.1 row), `test_exit_codes`, text smoke | G2 |
| `test_gate.py` | `test_constructed_cyclic` (the residue equals P2's), `test_one_per_boundary` | G3 |
| `test_acyclicity.py` | 400 seeded random hypergraphs against the brute-force definitions (port of `probe_theory.py`); every witness meets its definition; join trees; α agrees with P2 | G2, G3 |
| `test_widths.py` | the inequalities on the random set; every certificate validates on H; **bounds contain the truth** on the fixtures at `--time-limit 0.01`; lifted decompositions validate | G2 |
| `test_validate.py` | each condition's injected violation is caught, including (4) on `p6-adler`'s width-2 GHD; demotion | G2 |
| `test_covers.py` | exact ρ\* (triangle 3/2, K5 5/2) with both certificates; SciPy rounding (skips without SciPy) | G2 |
| `test_solver_parsers.py` | R01's recorded BalancedGo and log-k-decomp outputs parsed; "SCV found!" demotes; neutral-id round trip; edge-count check | G2 |
| `test_solvers_live.py` (`solvers`; skips without binaries) | both tools agree with Python on the fixtures; disagreement log; schedule and timeouts | G2 |
| `test_sources.py` | the Wikidata builder on a 7-property mini raw set (time model, meta, required qualifier, `P131:qualifier`, P580 and P582 under 6a, an excluded property, novalue) passes `check_schema`; P3a counts preferred to SQID; `manifest.verify`; Biolink (skips without linkml) | G1 |
| `test_survey.py` (`survey`) | §1 rows, files, hashes, recomputed class and core, re-validated certificates, bound consistency, naming version | G1 |
| `test_hygiene.py` | import hygiene | — |

**CI (F7).** One job is appended to `.github/workflows/ci.yml`, and the existing jobs are unchanged. Their `pytest`
runs from the repository root with `testpaths = ["tests"]`, so it never collects these tests.

```yaml
  khg-width:
    name: khg-width
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          cache: pip
          cache-dependency-path: |
            pyproject.toml
            projects/p6-schema-width/khg-width/pyproject.toml
      - name: Install khg-contracts and khg-width (no external solvers)
        run: python -m pip install . "./projects/p6-schema-width/khg-width[dev]"
      - name: khg-width tests (solver tests skip)
        working-directory: projects/p6-schema-width/khg-width
        run: python -m pytest -q
```

## 6. Survey protocol

### 6.1 Inputs, manifests and licences

Every input is pinned by a tracked `MANIFEST.json`, and the raw files stay untracked. `sources.manifest.verify`
checks every sha256 before generation and refuses on a mismatch.

| Dataset | Content | Licence (checked 2026-09-24) |
|---|---|---|
| `datasets/knowledge-bases/wikidata-property-schemas/` | 8 WDQS result files, 3 DeltaBot templates, 2 SQID files | **CC0-1.0.** *Wikidata:Copyright* (read today): "All structured data from the main, Property, Lexeme, and EntitySchema namespaces is available under the … CC0 License". The templates are Template-namespace text (CC BY-SA 3.0); only their numbers are used, and nothing of them is redistributed. SQID's tool licence is unverified; its statistics are not redistributed |
| `datasets/knowledge-bases/biolink-model/` | `biolink-model.yaml` (sha256 `7a0e3b3b…`), `attributes.yaml`, `LICENSE`, at v4.4.5 | **CC0-1.0**, by the model's own `license:` field (checked in the raw file). The repository `LICENSE` is Apache-2.0, so the results credit Biolink by name and version |
| P3a's qualifier counts (2026-09-22 dump), under P3a's manifest | statements and snaks per (relation, qualifier) | CC0 (statistics of Wikidata). Used when present |
| **new:** `datasets/knowledge-bases/hyperbench-zenodo-7180787/` (Q1) | `parseddata_csv.zip`, `hyperbench.zip` (Zenodo v4) | **CC BY 4.0**; cite the HyperBench papers |

WDQS is live, so a refetch gives a *new* snapshot. The committed schema files keep the measured object reproducible
from the repository. The 2026-09-24 raw snapshot (CC0, about 130 MB) should go to Zenodo with the note (Q4).

### 6.2 Generating the schema files

**Wikidata:** `sources.wikidata.build(raw_dir, table, naming, counts=None)` ports `load`, `tables` and
`build_schema` from `wd_schema_survey.py`, with the r1 changes of §2.4.
- Ids are `p6-wikidata-<table>-<naming>`, version `1.0.0`. M004 allows no build metadata, so the date goes in the
  label and the provenance.
- All four slots are written, so the file documents the naming.

**Biolink:** `sources.biolink.build(yaml, qualifiers, naming)` ports `biolink_extract.py` and `biolink_survey.py`.

**Every file:**
- is canonical JSON and passes `check_schema` with no findings;
- goes to `results/schemas/` with `<name>.provenance.json`, which holds the manifest hashes, the naming version
  (`wd-roles r1`), the count source and date, the thresholds, the generator version and the commit.

The Wikidata files are written as deterministic `.json.gz` (mtime 0), about 4 MB instead of about 40 MB (Q5).

### 6.3 The rows

| Source | Naming | Slots | Rows |
|---|---|---|---|
| Wikidata: declared, observed-robust, observed-all | wd-roles r1; relation-local | cq; cq+time | 12 |
| Biolink v4.4.5 | global formal; global formal+domain; relation-local formal | cq | 3 |
| HyperBench | non-random CQs, from the published runs | n/a | 1 |

Each schema row runs `khg-width FILE --slots … --time-limit 600 --solver auto --json` and writes
`results/reports/<row>.json`, with its decompositions and steps.
- `run_survey.py --jobs N` runs rows in parallel.
- Each solver gets `-cpu 2`.

### 6.4 HyperBench baseline (D10)

`survey/hyperbench_baseline.py` ports R01's probe to Run.csv and Type_of.csv. For each graph:
- the upper bound is the smallest K with a correct decomposition;
- the lower bound is 1 plus the largest K refuted without timeout.

The row is **non-random CQs, n = 1,113, hw 1 / 2 / 3 = 673 / 432 / 8** ([R01 §3.5]). Its note says that these are
queries selected to be cyclic, so the comparison is by structural parameter and hw ([R01 §3.6]).

### 6.5 Table columns

**CSV:**
- the row's identity: `row_id`, `source`, `counts_source`, `counts_date`, `naming`, `naming_version`, `slots`,
  `schema_id`, `schema_sha256`, `file`;
- structure: `relations`, `roles`, `rank`, `max_degree`, `bip`, `duplicate_groups`, `universal_roles`, `components`;
- class: `class`, `first_failed`, `witness_kind`, `witness_size`, `core_roles`, `core_relations`;
- widths: `{hw,ghw,fhw,tw}_{lower,upper,exact,method}`;
- run: `validated`, `disagreements`, `tools`, `time_limit`, `wall_seconds`.

**Markdown** shows source, naming, slots, size, class (witness), core and the four widths. A width reads `2` when
exact and `[2, 4]` when bounded.

### 6.6 Figure, outputs, reproduction, run time

**Figure.** `survey/make_figure.py` (matplotlib) writes a deterministic `results/figure-widths.{svg,png}` from
`figure-data.csv`:
- (a) hw per non-control row, as a point when exact and a bar when bounded, beside the HyperBench CQ shares;
- (b) GYO residue size per Wikidata source and slot set, on a log scale.

**`results/`** holds:
- `survey.{md,csv,json}`;
- `reports/`, `schemas/` (with provenance) and `crosschecks/`;
- `hyperbench-baseline.json`;
- `solver-log.jsonl`, with the disagreements and demotions;
- `machine.json`;
- `README.md`, with licences, attribution and how to reproduce.

**`survey/reproduce.sh`:**
1. Check the venv (`khg-width[survey,fast]`) and the solvers.
2. Verify the manifests. If a file is missing, print its fetch command: Biolink and Zenodo return identical bytes;
   WDQS gives a new snapshot.
3. Generate the schemas, preferring P3a's counts when present, and compare their sha256 with the committed files.
   A mismatch stops the run unless `--new-snapshot` is given.
4. Run the rows.
5. Compute the baseline.
6. Write the table and the figure.

**Run time on 4 cores:**
- generation takes about 2 minutes, mostly parsing SQID;
- the Biolink and control rows take under 1 minute each;
- each wd-roles row takes up to about 2.5 hours: 30 minutes of Python bounds, plus at most 9 k values × 600 s and 2
  second-opinion runs.

That is about 15 hours serial, or about 5 hours with `--jobs 3`. Without solvers the survey takes about 1 hour, with
bounds only.

When P3a's corpus exists, a later row (not a gate row) adds the corpus-observed schema.

## 7. Implementation plan

| # | Step | Port from | Tests |
|---|---|---|---|
| 1 | Skeleton, CI job, `hypergraph.py` | `probe_schemas.to_hyperbench`, `hg_measure.stats` | hygiene |
| 2 | `acyclicity.py`, indexed | `p6check`: `berge`, `gyo`, `check_join_tree`, `beta`, `beta_cycle`, `gamma`, `gamma_triangle`, `classify`; oracle `brute_force_class` | `test_acyclicity` |
| 3 | `decomposition.py` | `p6check.validate_hd` | `test_validate` |
| 4 | `covers.py` (rational simplex) | `p6check.rho`, `rho_star` | `test_covers` |
| 5 | `reduce.py`, with lifting | `p6check.reduce_core`, `treewidth` | `test_widths` |
| 6 | `exact.py` | `p6check.f_width`, `hd_search` | `test_widths` |
| 7 | `bounds.py` | new | bounds contain the truth |
| 8 | fixtures, `check.py`, `report.py`, `cli.py` | `probe_schemas.main` | `test_cli`, `test_gate` (**G2 and G3 pass here**) |
| 9 | `solvers/`, `build-solvers.sh` | `run_solvers.sh`, `scale_probe.sh` | parsers, live |
| 10 | `sources/` | `wd_schema_survey.py`, `biolink_extract.py`, `biolink_survey.py` | `test_sources` |
| 11 | `survey/`, HyperBench manifest | `hyperbench_baseline.py`, R01's HtdLEO shims | — |
| 12 | Run the survey; commit `results/`; one review | — | `test_survey` (**G1 passes here**) |
| 13 | Note, post draft, base update (§10) | — | — |

The prototype's naive loops are rewritten with indices. They must classify observed-all under relation-local naming
(13,608 relations, 83,030 roles) in under 30 s.

## 8. Publication outline

**Working title:** *How acyclic are knowledge-hypergraph schemas? Acyclicity class and hypertree width of Wikidata
qualifier schemas and the Biolink Model.*
- 4–6 pages, for arXiv (cs.DB) or a database or KG-schema workshop.
- The owner submits it. The post draft goes in `post-draft.md`.

1. **Question** ([01.3]), and what the number measures:
   - the width of the role-join, not of arbitrary queries;
   - Berge acyclicity is acyclicity of the reified encoding.
2. **Objects:** the sources and their count sources, Biolink, wd-roles r1 (shared with P3a) and the controls, the
   slots, and the licences.
3. **Method:**
   - the class tests with witnesses;
   - the four widths, with certificates validated on the input;
   - the sound bounds and the reductions;
   - the solvers and the second-opinion rule;
   - the time limits and reproducibility.
4. **Table and figure.**
5. **Findings:**
   - class and hw of each non-control schema;
   - what the control shows;
   - the effect of the time slots;
   - declared against observed;
   - hw against tw (tw ≥ 116 on the declared table);
   - the position against HyperBench's CQs, all of which have hw ≤ 3.
6. **Limits:**
   - the role-join reading;
   - a live snapshot and differing count dates;
   - a meta list drawn by judgement;
   - the naming version;
   - bounds that are not exact;
   - machine-dependent time limits.
7. **Artefacts:** khg-width, the schema files, the manifests and the reproduce script.

## 9. Risks and open questions

**Risks**
1. **The naming may change.** A later amendment of wd-roles (r2) would mean regenerating the files and rerunning 6
   rows, which takes hours. `test_survey` checks the naming version.
2. **Wikidata widths may stay bounds.** The residues lie where HyperBench has exact hw for only 6 of 23 graphs, and
   the lower bounds may be just 2. That is still a finding, published as such (PLAN §8).
3. **Unflagged refutations may never finish** on the large inputs. Then hw's lower bound comes from the ghw side.
4. **The data is live.** WDQS cannot be refetched byte-identically. Until P3a's counts arrive, the observed rows rest
   on SQID, whose `qs` meaning is unverified and whose dates are mixed. The rows are rerun when the counts land.
5. **The meta list is judgement.** Only the top 120 declared and top 120 observed qualifiers were reviewed
   ([R02 §2.3]).
6. **Build risk.** Pinned commits and Go sums pin the solvers. Without Go, the run is Python-only and still valid.
7. **Licences.** Only numbers come from the DeltaBot templates. Biolink's model file says CC0 while its repository
   says Apache-2.0, so attribution is given in any case.

**Questions for the director**
- **Q1.** HyperBench is not a knowledge base, yet F6 names `datasets/knowledge-bases/`. Keep its manifest there, or
  add a family such as `benchmarks/`?
- **Q2.** Is this the intended reading of F1: solvers get the unreduced H and may preprocess internally to *find* an
  HD, which is validated on H, while their flagged refutations are not used as bounds?
- **Q3.** Twin merging is unsound for tw, and lonely-role removal is sound only as the simplicial rule. Universal-role
  removal is added: exact for tw, sound for ghw and fhw, not used for hw. Agree?
- **Q4.** Deposit the CC0 raw Wikidata snapshot on Zenodo with the note?
- **Q5.** Commit the Wikidata schema files as `.json.gz` (about 4 MB) instead of plain JSON (about 40 MB)?

## 10. KB corrections at base-update time

From R01 §1.5, applied in the same commit as the register update, together with the PLAN §9 row and the run log.

| Note | Claim | Correction |
|---|---|---|
| [hypergraph-theory-results](../../kb/01-foundations/hypergraph-theory-results.md) §5 | α is "exactly the boundary of tractable join evaluation" | **Wrong.** α ⇔ hw = 1 (GLS, Thm 4.4). Bounded hw, ghw and fhw are tractable, and submodular width characterises FPT under the ETH |
| same | α-acyclic schema ⇒ "queries over it are cheap" | **Imprecise.** It concerns the role-join. A query's cost comes from its own hypergraph |
| same, γ | "rooted join tree for every hyperedge" | Add "with disjoint branches" (Duris) |
| same, §6 | "only hw is tractable to check" | **Imprecise.** ghw ≤ k is NP-complete for k ≥ 3 (GMS 2009) and for k = 2 (GLPR), which also give tractable cases |
| same, §6 | Grohe–Marx TALG `[unverified]` | *ACM TALG* 11(1):4, 2014 |
| same, §6 | missing | fhw ≤ ghw ≤ hw ≤ 3·ghw+1; ghw ≤ tw+1 |
| [n-ary-relations-and-relational-algebra](../../kb/01-foundations/n-ary-relations-and-relational-algebra.md) §2 | α-acyclic ⇒ tractable "whatever the instance" | **Wrong**, as above. The claim is about combined complexity |
| same, §2 | Fagin and BFMY "are about the first two" | **Imprecise.** Both are about schemes; the query use comes via Yannakakis and GLS |
| same, §3 | "most interesting [schemas] are cyclic" | **Unsupported.** Replace with the survey result |
| same, §4 | pairwise planning "provably suboptimal on cyclic queries" | **Overstated.** It holds for specific queries on worst-case instances; cite AGM or NPRR |
| [query-languages-for-hypergraphs](../../kb/05-query-embeddings-reasoning/query-languages-for-hypergraphs.md) §10.2 | ghw "recognition is NP-hard (GMS 2009)" | NP-complete for k ≥ 3 (GMS) and k = 2 (GLPR); hw ≤ k is polynomial |
| same, §10.2 | ghw "used most in machine learning" | **Unsupported.** Source it or remove it |
| same, §10.3 | reification raises width by "multiplying atoms" | **Wrong mechanism.** The incidence graph is acyclic iff H is Berge-acyclic |
| [open-questions](../../kb/00-index/open-questions.md) [01.3] | "predicts query cost directly" | Narrow to role-aligned joins (R01 §2.5). Then mark the item closed or narrowed, with a link to this folder |

## Sources

- [R01] [research/01-theory-and-solvers.md](research/01-theory-and-solvers.md), with its probes: `p6check.py`, `probe_theory.py`, `probe_schemas.py`, `run_solvers.sh`, `scale_probe.sh`, `hyperbench_baseline.py`.
- [R02] [research/02-data-sources-and-naming.md](research/02-data-sources-and-naming.md), with its probes: `wd_fetch.py`, `wd_schema_survey.py`, `biolink_extract.py`, `biolink_survey.py`, `hg_measure.py`.
- [wd-roles.md](wd-roles.md), version r1 (2026-09-24), the authoritative Wikidata naming.
- P2 [DESIGN.md](../p2-role-aware-hif/DESIGN.md) §2.4, §3 and §10; `khg_contracts.schema` and `khg_contracts.jsonio`.
- Fagin, R. Degrees of acyclicity for hypergraphs and relational database schemes. *JACM* 30(3), 1983. https://doi.org/10.1145/2402.322390
- Brault-Baron, J. Hypergraph acyclicity revisited. *ACM Computing Surveys* 49(3), 2016. https://arxiv.org/abs/1403.7076
- Gottlob, G., Leone, N., Scarcello, F. Hypertree decompositions and tractable queries. *JCSS* 64(3), 2002. https://arxiv.org/abs/cs/9812022
- Grohe, M., Marx, D. Constraint solving via fractional edge covers. *ACM TALG* 11(1):4, 2014. https://arxiv.org/abs/1711.04506
- Adler, I., Gottlob, G., Grohe, M. Hypertree width and related hypergraph invariants. *Eur. J. Combin.* 28(8), 2007. https://doi.org/10.1016/j.ejc.2007.04.013
- Gottlob, G., Lanzinger, M., Pichler, R., Razgon, I. Complexity analysis of generalized and fractional hypertree decompositions. *JACM* 68(5), 2021. https://arxiv.org/abs/2002.05239
- Moll, L., Tazari, S., Thurley, M. Computing hypergraph width measures exactly. *IPL* 112(6), 2012. https://arxiv.org/abs/1106.4719
- Gottlob, G., Samer, M. A backtracking-based algorithm for hypertree decomposition. *ACM JEA* 13, 2008. https://doi.org/10.1145/1412228.1412229
- Fischl, W., Gottlob, G., Longo, D. M., Pichler, R. HyperBench. *PODS 2019*, https://doi.org/10.1145/3294052.3319683; *ACM JEA* 26, 2021, https://doi.org/10.1145/3440015
- Gottlob, G., Lanzinger, M., Okulmus, C., Pichler, R. Experimental data for log-k-decomp. Zenodo v4, CC BY 4.0. https://doi.org/10.5281/zenodo.7180787
- BalancedGo (MIT), https://github.com/cem-okulmus/BalancedGo; Gottlob, Okulmus, Pichler, *Constraints* 27(3), 2022, https://doi.org/10.1007/s10601-022-09332-1
- log-k-decomp (MIT), https://github.com/cem-okulmus/log-k-decomp; Gottlob, Lanzinger, Okulmus, Pichler, *PODS 2022*, https://doi.org/10.1145/3517804.3524153
- Wikidata:Copyright, https://www.wikidata.org/wiki/Wikidata:Copyright (read 2026-09-24). SQID data, https://sqid.toolforge.org/data/. DeltaBot, https://www.wikidata.org/wiki/Template:Number_of_main_statements_by_property
- Biolink Model v4.4.5, https://github.com/biolink/biolink-model (commit a4180f818e9722c493788c5ff1f047fde64f13a7); Unni, D. R., et al., *Clinical and Translational Science*, 2022, https://doi.org/10.1111/cts.13302
