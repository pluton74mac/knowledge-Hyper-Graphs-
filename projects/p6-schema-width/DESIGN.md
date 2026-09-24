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

  Pure Python on khg-contracts; BalancedGo and log-k-decomp are optional, built outside git and called if present.
- **The survey.** 12 Wikidata rows (3 sources × 2 namings × 2 slot sets), plus 8 on P3a's slice once P3a's counts
  land; 3 Biolink rows; a HyperBench baseline.
  `results/` holds the table, a figure, the measured schema files and a reproduce script.
- **A short note** (§8). The owner publishes it; nothing is published from this session.

| Gate clause (PLAN §4) | How it is met | Test that proves it |
|---|---|---|
| "Survey table for the Wikidata qualifier schemas" | `results/survey.{md,csv}`, rows of §6.3 | `test_survey.py::test_wikidata_rows`: rows present, file sha256s match, class and core recomputed, stored decompositions re-validated |
| "…and the biomedical schema" | 3 Biolink v4.4.5 rows | `test_survey.py::test_biolink_rows`: recomputed with `--solver python` |
| "the checker reports class and width for a given schema file" | `khg-width SCHEMA_FILE` (§4.3) | `test_cli.py::test_fixture_table` (class, witness, four exact widths per §5.1 fixture); `test_exit_codes` |
| "…and flags a constructed cyclic case" | class `cyclic`, GYO residue as witness | `test_gate.py::test_constructed_cyclic` (P2 `cyclic`, `wikidata-shaped`, `p6-qualifier-k5`, `p6-adler`); `test_one_per_boundary` |

Tests marked `survey` skip until `results/survey.csv` exists; then CI runs them. A cyclic schema is flagged by its
class and witness; the exit status stays 0 (F4).

Where R01's decisions land: D1 and D4 in §2.1, D2 in §2.3, D3 in §2.4, D5 in §3, D6 in §4.5, D7 in §3.7, D8 in §3.2,
D9 in §5, D10 in §6.4, D11 in §3.6, D12 in §3.3–§3.4.

## 2. The measured object

### 2.1 Which hypergraph (D1, D4)

**H(S, σ) = `schema_hypergraph(S, slots=σ)`**: vertices are global role ids (one per role, whatever its slot); each
relation gives one edge, the roles of its usages in σ; lifecycle relations and relations with no usage in σ are left
out. H is a **named multi-hypergraph**. **Berge** is computed on it, so two relations with the same role set form a
cycle. **α, β, γ and the widths** use the set hypergraph, and duplicate role sets are reported as a finding.

**What the number means.** It is the width of the query that joins all relations on same-named roles (Fagin's
scheme setting). It is not the width of arbitrary KHG queries, which join on entities ([R01 §2.5]). Berge reads
directly for stores: the reified encoding is acyclic exactly when H is Berge-acyclic ([R01 §1.3]).

### 2.2 From a relation-schema file to H

1. **Read.**
   - `.json`: `load_schema(path)`, which runs layers J, V and M.
   - `.json.gz`: gunzip, then `jsonio.loads` (J), then `load_schema(mapping)` (V and M).

   Any error finding gives exit 1.
2. **Identify.** The report records `id`, `version`, `sha256` (`Schema.sha256`, the digest C1 headers pin) and
   `file_sha256`, the hash of the file's bytes.
3. **Build and describe.** `schema_hypergraph` gives H. The report adds counts, rank, maximum degree, BIP, duplicate
   groups, components, and the **universal roles**: those in every relation, such as `subject` under wd-roles.
   Degree and BIP are computed without universal roles.
4. **Neutral ids for solvers.** Relations become `R<i>` and roles `V<j>`, and a mapping is kept. BalancedGo panics
   when an edge and a vertex share a name (wd-roles gives relation `P39` a role `P39`); other tools reject or drop
   names containing `-`, `.` or `:` ([R01 §4.3]).

### 2.3 Slots (D2)

- **Headline:** `core,qualifier`.
- **Variant:** `core,qualifier,time`. It turns P2's fixture from Berge into γ.
- **`meta` is refused** with exit 2, so `khg:end_cause`, P2241 and P7452 never enter H.
- `core` is required in every slot set.

### 2.4 Role naming (D3, F2)

**Wikidata uses `wd-roles r1`**, whose authoritative text is [wd-roles.md](wd-roles.md).
- P6 proposed it as r0 ([R02 §5]). P3a adopted it with amendments 6a–6c, which the director accepted.
- Every row and every file's provenance records `wd-roles r1`. The rules sit in `khg_width/data/wd-roles-r1.json`.

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
- **Slots.** `time` is P580 and P582, and a relation that allows or uses either gets the interval model. `meta` is
  the 24 listed properties plus P2241 and P7452, which are meta bindings under 6c when they do not match the rank.
  Everything else is `qualifier`. P1534 is `khg:end_cause` on interval relations.
- **6a.** Relations P580 and P582 get no time model. Their P580 and P582 qualifiers are `qualifier` usages, and the
  self one is `P580:qualifier` or `P582:qualifier`. Under r0 these relations failed M007; a generator test covers
  them.
- A required-qualifier constraint gives `min: 1`. The 57 properties that document or constrain properties are
  excluded.

Rules 6b and 9 concern the corpus. Self-qualifier roles lie in one edge, so GYO removes them and leaves class and
residue unchanged (R02 counted 9, 14 and 441 such relations). 6a can change the residue: under `core,qualifier` it
puts P582 into relation P580's edge and P580 into P582's. R02's residues are expectations, not targets.

### 2.5 Sources, counts and dates (F2, F6)

| Source | Relations | Qualifiers per relation |
|---|---|---|
| **declared** | 1,155 properties with a non-deprecated allowed-qualifiers constraint (Q21510851/P2306; statements united; "no value" = none) | the allowed list. WDQS main graph, 2026-09-24 09:35–09:44 UTC |
| **observed-robust** | properties with ≥ 1 main statement, minus the 57 (13,608 under SQID) | **≥ 10 uses and ≥ 0.1 %** of the property's main statements |
| **observed-all** | same | ≥ 1 use |

Each observed source has a **scope**:
- **`dump`**: all entities. This is the gate scope.
- **`slice`**: P3a's `kept` items, those with an English Wikipedia article, counted before the 6b/S009 removals.
  These are the corpus-observed rows that R02 §2.5 asked for.

**Count sources.** The columns `counts_source`, `counts_date` and `scope` say which was used.
1. **P3a's file**, [wd-roles.md](wd-roles.md) "What P6 takes from P3a":
   `projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json`, format `p3a-qualifier-usage/1`, from one pass over
   `wikidata-20260922-all.json.bz2` (md5 `7f70e4a1858ba6182ea9329a1ef588c5`). It is expected on branch
   `claude/p3a-wikidata-slice` after about 06:10 UTC on 2026-09-25.
   - Scope `dump` reads `all.relations`, and scope `slice` reads `kept`. Per relation, uses =
     `qualifiers[role].statements` and the denominator = `statements`, both from one date. Roles are r1 ids, so
     `P<id>:qualifier` maps back to the self-qualifier.
   - The generator refuses a file whose `naming` is not `wd-roles r1`.
   - P3a's optional `slot` and `time_model` fields and its `out_of_scope` list are compared with P6's own r1
     classification. Mismatches go to `results/p3a-crosscheck.json`.
2. **Otherwise, SQID `qs`**, scope `dump` only: the **2026-08-10** dump, with DeltaBot main-statement counts
   (revision 2548855541, **2026-09-23**). The two dates differ, which is a stated limit.

Unknown qualifier ids are dropped and counted.

R02's sizes (r0, SQID) as expectations:

| Source | Roles (cq) | Largest edge | GYO residue cq (edges/roles) | +time |
|---|---|---|---|---|
| declared | 1,883 | 117 | 391 / 615 | 392 / 617 |
| observed-robust | 13,655 | 34 | 741 / 537 | 748 / 540 |
| observed-all | 13,690 | 749 | 1,423 / 1,982 | 1,428 / 1,987 |
| Biolink formal, global | 35 (103 relations) | 20 | 5 / 18 | n/a |

**Biolink** v4.4.5 (commit `a4180f8`) gives one relation per concrete association class, with core `subject` and
`object` (`predicate` is the relation type, not a role). *Formal* qualifiers are the slots under `qualifier`;
*formal + domain* adds R02's 25 `DOMAIN_TRUTH_CHANGING` slots. Meta slots are not generated. With no interval bounds,
Biolink has no `+time` rows.

## 3. Algorithms, witnesses and validation

### 3.1 Acyclicity classes

Berge ⊂ γ ⊂ β ⊂ α. The tests run from α down and stop at the first failure:

1. **α** by `khg_contracts.schema.is_alpha_acyclic` (the C1 GYO). If it fails, the class is **cyclic** and the
   witness is the GYO residue. The stricter tests are *implied false* and not run, so the Wikidata tables take
   seconds.
2. **β** by indexed nest-point elimination. If it fails, the class is **α** and the witness is a **β-cycle**
   (chordless incidence cycle, k ≥ 3), searched with a budget in the β residue; a cycle of H[residue] lifts to H.
   When the budget runs out, the residue is the witness, flagged.
3. **γ** by the indexed D'Atri–Moscarini reduction. If it fails, the class is **β** and the witness is a
   **γ-triangle**, searched in the DM residue (β-acyclic but not γ-acyclic, so it contains one).
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

**hw is computed on the unreduced H** (F1). Solvers receive H itself; their internal `-g -t -h` preprocessing may
*find* an HD, which must then pass all four conditions on H (Q2). The *core* is H after GYO, twin merging and
universal-role removal. The report lists every reduction, what it removed and which measures it served. Two points
depart from F1's wording (Q3): for tw, GYO is used only as the simplicial rule and twins are never merged; and
universal-role removal is added.

### 3.3 Exact procedures

- **α-acyclic, non-empty:** hw = ghw = fhw = 1, certified by the join tree. An empty H has all widths 0.
- **tw, ghw, fhw** by the subset DP over elimination orderings ([R01 §4.6]; Moll, Tazari and Thurley):
  F(S) = min_v max(F(S∖v), f({v} ∪ Q(S∖v, v))).
  The bag cost is \|B\|−1, ρ(B) or ρ\*(B), per block of the hypergraph reduced for that measure (§3.2), up to 20 roles (16 for fhw). ρ comes from exact search
  over maximal traces; ρ\* from an **exact rational simplex** whose primal and dual solutions are both checked. The
  ordering yields the decomposition that is lifted.
- **hw** by the det-k-decomp-style normal-form search, k = 1, 2, … (Gottlob and Samer), on the unreduced H when it
  has ≤ 60 relations, with 3·10⁶ separator trials per k. A "no" is exhaustive, so it is a refutation.

### 3.4 Bounds

**Lower bounds** are sound and labelled by method:
- **cyclic:** hw, ghw ≥ 2 and fhw > 1, the last reported as `lower_exclusive`.
- **Clique bounds:** ghw ≥ ρ(K) and fhw ≥ ρ\*(K) for primal cliques K of the core, enumerated by Bron–Kerbosch.
- **Induced bounds.** All four measures are monotone under H ↦ H[X] = {e ∩ X}: restricting bags and guards to X
  keeps every condition, the special condition included. So an exact value on a small H[X] (≤ 18 roles, 16 for fhw,
  grown greedily from high-degree core roles) is a lower bound, labelled `induced-dp` or `induced-hd-search`.
- **tw:** max(rank − 1, simplicial, minor-min-width), plus the universal offset.
- **Solver refutations**, only from unflagged runs that no other tool contradicts.

**Upper bounds:**
- **Heuristic tree decompositions** (min-fill, min-degree, seeded) of each reduced block. Their bags give tw, greedy
  covers give ghw, and ρ\* gives fhw: exact on small bags; else SciPy's LP (`fast` extra) rounded up to an exactly
  feasible rational cover; else the greedy cover.
- **Solver HDs** give hw, and so ghw ≤ hw. They also give fhw ≤ max ρ\*(χ_t) (ImproveHD).
- **Trivial:** hw ≤ \|E\| (one node holding every guard), so an upper bound always exists.

**Propagation.** Bounds pass through fhw ≤ ghw ≤ hw ≤ 3·ghw+1, ghw ≤ tw+1 and ⌈fhw⌉ ≤ ghw until nothing changes, each
labelled `inequality`. A measure is **exact** when its lower bound (not exclusive) equals its upper bound.

### 3.5 External solvers (D6, F3)

- **BalancedGo** is primary, in DetK mode (`-det`), for hw only. It reports through `-json FILE`.
- **log-k-decomp** is the second opinion. It reports through `-gml FILE`, or the stdout tree as a fallback.

**Schedule for hw.** For k from the lower bound up to k_max = 10, stopping at the first validated "yes":
1. `-width k -det` **without flags**, for a quarter of the step limit T. A "no" is a refutation.
2. After a timeout, `-width k -det -t -h -g -heuristic 1` for the rest of T (300 s became 0.9 s on a 418-edge
   instance, [R01 §4.5]). A "no" here is logged, not used as a bound.
3. With ≤ 60 relations, `-exact -det` replaces the loop.

**Second opinion.** Under `auto`, log-k-decomp reruns k_yes, and k_yes − 1 when that value was refuted. Every
disagreement (solver against solver or against the Python search) goes to `disagreements[]` with both commands,
outputs and times. A decomposition validated on H beats a refutation; a contradicted refutation is dropped from the
lower bound; nothing is discarded silently.

**Not used:** BalancedGo's unprobed `-local` and `-balDet` modes. HtdLEO, htdsmt and fraSMT are manual cross-checks
only (`survey/crosscheck.sh` → `results/crosschecks/`). NewDetKDecomp and det-k-decomp have no licence.

### 3.6 Validation (D11)

`validate(H, D, kind)` checks a decomposition D against **H as given**:

| Kind | Conditions | Width |
|---|---|---|
| TD | (1) every edge lies in a bag; (2) the bags holding a role form a subtree | max\|χ_t\|−1 |
| GHD | TD, plus (3) χ_t ⊆ ⋃λ_t with λ_t ⊆ E(H) | max\|λ_t\| |
| HD | GHD, plus (4) the special condition (⋃λ_t) ∩ χ(T_t) ⊆ χ_t, computed bottom-up in linear time | max\|λ_t\| |
| FHD | TD, plus a cover with Σ_{e∋v} λ_t(e) ≥ 1 on χ_t, in exact rationals | max Σλ_t |

No upper bound is reported without a validated decomposition. An HD failing (4), or printed with "SCV found!", is
**demoted** to a ghw bound and logged. An echoed edge count that differs from H's is an error (fraSMT-style silent
misparse). Certificates are stored in role and relation names.

### 3.7 Time limits (D7)

`--time-limit T` bounds **each step**: a DP, a clique enumeration, an induced search, an hw-search level, or a solver
call at one k. The default is 60 s; the survey uses 600 s.
Python steps check a cooperative deadline; solvers run in their own process group and are killed at T. Each step
is logged (measure, method, tool, k, limit, time, outcome). The class tests are polynomial and uncapped. The seed is
20260924. The survey records CPU and tool versions, since limits make results machine-dependent.

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

Frozen dataclasses: `Hypergraph(edges)` (`.induced`, `.stats`, `.neutral`); `Acyclicity(cls, tests,
first_failed, witness, join_tree)`, where a `None` test was implied and not run; `Witness(kind, value, complete)`;
`Width(measure, lower, upper, lower_exclusive, lower_method, upper_method, certificate, validation, steps)`;
`Decomposition(bag, cover, children)`; `WidthReport(format="khg-width-report/0.1.0", schema, slots, stats,
acyclicity, widths, reductions, disagreements, tools, time_limit)`. Fractions serialise as `"3/2"`. P11 calls
`check`.

### 4.3 CLI (F4)

`khg-width SCHEMA_FILE [--slots core,qualifier[,time]] [--time-limit SECONDS] [--solver auto|python|balancedgo|logk] [--json]`

- `--solver auto` uses BalancedGo with log-k-decomp as second opinion when found, else Python; `python` uses no
  tool; `balancedgo` or `logk` uses that tool alone (exit 2 if missing). `--json` prints the `WidthReport`.
- **Exits** (khg-contracts' conventions): **0** when a report is produced, whatever the class; **1** for an invalid
  schema, printing every `load_schema` error finding (M, or J/V for malformed JSON or format); **2** for usage or I/O
  errors (missing file, `--slots` with `meta` or without `core`, bad limit, missing requested solver).

```
schema      p6-qualifier-k5/0.1.0  sha256:3f…  file 9c…  slots core,qualifier
class       cyclic (alpha fails)  witness: GYO residue, 10 relations on 5 roles
hw   3      exact  python hd-search on the input: k=2 no, k=3 yes; HD validated
ghw  3      exact  subset DP on core (5 roles); GHD lifted and validated
fhw  5/2    exact  subset DP + exact LP on core; FHD lifted and validated
tw   4      exact  subset DP after simplicial rule
reductions  gyo -20 roles [ghw,fhw]; twins 0; universal 0; blocks 1; simplicial 20 [tw]
```

### 4.4 Dependencies

Hatchling, `license = "MIT"`, `requires-python = ">=3.10"`. Core: `khg-contracts>=1.0.0.dev0,<2` (the repository
package). Extras: `fast` (SciPy ≥ 1.10), `survey` (`linkml-runtime==1.11.1`, `pyyaml`, `matplotlib`), `dev` (pytest
≥ 8). Script: `khg-width = "khg_width.cli:main"`. Importing `khg_width` loads no SciPy, linkml or matplotlib (tested).

### 4.5 Solver build and discovery (F3)

**`scripts/build-solvers.sh [DEST]`** (DEST defaults to `${XDG_CACHE_HOME:-~/.cache}/khg-width/solvers`, and a DEST
inside the git working tree is **refused**) needs git and Go (1.24.7 probed, `GOTOOLCHAIN=local`). It checks out
BalancedGo `872c662c9f409aeb7386f963d2f16b88523ff4bf` (v1.7.2-2, MIT) and log-k-decomp
`5e021dd442b028099c30deecc316a906a49a8cb3` (v1.1.0, MIT), builds with `go build -trimpath -mod=readonly` into
`DEST/bin/`, smoke-tests `b_triangle` (width 2), and writes `DEST/solvers.json` (commit, describe, Go version,
binary sha256, licence).

**Discovery:** `KHG_WIDTH_BALANCEDGO` / `KHG_WIDTH_LOGK`, then `KHG_WIDTH_SOLVERS` (a DEST), then the default
DEST, then `PATH`. The `tools` block gives path, commit ("unknown" from PATH) and sha256. Without solvers, §3.3–§3.4
still give results.

## 5. Fixtures and tests

### 5.1 Gate fixtures (F5)

The fixtures are in `tests/fixtures/`, with expected values in `expected.csv`, which the tests read. The five
boundary files come from R01's `probes/schemas/`; `p6-duplicate-role-set` and `p6-adler` (from `adler.hg`) are new;
P2's come through `khg_contracts.data.path`. Values are from R01's probes, where BalancedGo agreed on hw.

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

Invalid inputs: `bad-m002` (a role used twice) exits 1 with `KHG-M002`; `bad-json` exits 1 with a J code; a
missing file, `--slots core,meta` and `--slots qualifier` exit 2.

### 5.2 Tests

| Module | Checks | Gate |
|---|---|---|
| `test_cli.py` | `test_fixture_table` (`--json --solver python` on every §5.1 row), `test_exit_codes`, text smoke | G2 |
| `test_gate.py` | `test_constructed_cyclic` (the residue equals P2's), `test_one_per_boundary` | G3 |
| `test_acyclicity.py` | 400 seeded random hypergraphs against the brute-force definitions (`probe_theory.py`); witnesses; join trees; α agrees with P2 | G2, G3 |
| `test_widths.py` | the inequalities on the random set; certificates (lifted ones too) validate on H; **bounds contain the truth** at `--time-limit 0.01` | G2 |
| `test_validate.py` | each condition's injected violation is caught, including (4) on `p6-adler`'s width-2 GHD; demotion | G2 |
| `test_covers.py` | exact ρ\* (triangle 3/2, K5 5/2) with both certificates; SciPy rounding (skips without SciPy) | G2 |
| `test_solver_parsers.py` | R01's recorded outputs parse; "SCV found!" demotes; neutral ids round-trip; edge counts checked | G2 |
| `test_solvers_live.py` (`solvers`; skips without binaries) | tools agree with Python on the fixtures; log; timeouts | G2 |
| `test_sources.py` | a 7-property mini raw set (time, meta, required, `P131:qualifier`, P580/P582 under 6a, excluded, novalue) builds a schema passing `check_schema`; a mini `p3a-qualifier-usage/1` file (both scopes) wins over SQID; a wrong `naming` is refused; `manifest.verify`; Biolink (skips without linkml) | G1 |
| `test_survey.py` (`survey`) | §1 rows (slice rows present iff `counts_source` is P3a), files, hashes, recomputed class and core, re-validated certificates, bound consistency, naming version | G1 |

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

Tracked `MANIFEST.json` files pin every input; raw files stay untracked. `sources.manifest.verify` refuses any
sha256 mismatch before generation.

| Dataset | Content | Licence (checked 2026-09-24) |
|---|---|---|
| `datasets/knowledge-bases/wikidata-property-schemas/` | 8 WDQS result files, 3 DeltaBot templates, 2 SQID files | **CC0-1.0**: *Wikidata:Copyright* (read today) reads "All structured data from the main, Property, Lexeme, and EntitySchema namespaces is available under the … CC0 License". The DeltaBot templates are Template-namespace text (CC BY-SA 3.0); only their numbers are used. SQID's statistics are not redistributed |
| `datasets/knowledge-bases/biolink-model/` | `biolink-model.yaml` (sha256 `7a0e3b3b…`), `attributes.yaml`, `LICENSE`, at v4.4.5 | **CC0-1.0**, by the model's own `license:` field (checked in the raw file). The repository `LICENSE` is Apache-2.0, so the results credit Biolink by name and version |
| `projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json` (tracked by P3a; §2.5) | statements and snaks per (relation, role), scopes `all` and `kept`, from the dump of 2026-09-22 | CC0 (statistics of Wikidata). The path, git commit and sha256 go into the provenance |
| **new:** `datasets/knowledge-bases/hyperbench-zenodo-7180787/` (Q1) | `parseddata_csv.zip`, `hyperbench.zip` (Zenodo v4) | **CC BY 4.0**; cite the HyperBench papers |

WDQS is live, so a refetch gives a *new* snapshot. The committed schema files keep the measured object reproducible
from the repository. The 2026-09-24 raw snapshot (CC0, about 130 MB) should go to Zenodo with the note (Q4).

### 6.2 Generating the schema files

**Wikidata:** `sources.wikidata.build(raw_dir, table, naming, counts=None)` ports `load`, `tables` and
`build_schema` from `wd_schema_survey.py`, with the r1 changes of §2.4. Ids are `p6-wikidata-<table>[-slice]-<naming>`,
version `1.0.0` (M004 allows no build metadata; the date goes in the label and provenance). All four slots are
written, so the file documents the naming.

**Biolink:** `sources.biolink.build(yaml, qualifiers, naming)` ports `biolink_extract.py` and `biolink_survey.py`.

**Every file** is canonical JSON, passes `check_schema` with no findings, and goes to `results/schemas/` with
`<name>.provenance.json`: the input hashes, `wd-roles r1`, the count source, scope and date, the thresholds, the
generator version and the commit.

The Wikidata files are written as deterministic `.json.gz` (mtime 0), about 4 MB instead of about 40 MB (Q5).

### 6.3 The rows

| Source | Naming | Slots | Rows |
|---|---|---|---|
| Wikidata: declared, observed-robust, observed-all (scope `dump`) | wd-roles r1; relation-local | cq; cq+time | 12 |
| Wikidata: observed-robust, observed-all (scope `slice`), when P3a's file is present | same | same | 8 |
| Biolink v4.4.5 | global formal; global formal+domain; relation-local formal | cq | 3 |
| HyperBench | non-random CQs, from the published runs | n/a | 1 |

Each row runs `khg-width FILE --slots … --time-limit 600 --solver auto --json` into `results/reports/<row>.json`
(with decompositions and steps); `run_survey.py --jobs N` runs rows in parallel, each solver with `-cpu 2`.

### 6.4 HyperBench baseline (D10)

`survey/hyperbench_baseline.py` ports R01's probe: per graph, the upper bound is the smallest K with a correct
decomposition, the lower bound 1 plus the largest K refuted without timeout.

The row is **non-random CQs, n = 1,113, hw 1 / 2 / 3 = 673 / 432 / 8** ([R01 §3.5]). Its note says that these are
queries selected to be cyclic, so the comparison is by structural parameter and hw ([R01 §3.6]).

### 6.5 Table columns

**CSV:**
- the row's identity: `row_id`, `source`, `scope`, `counts_source`, `counts_date`, `naming`, `naming_version`, `slots`,
  `schema_id`, `schema_sha256`, `file`;
- structure: `relations`, `roles`, `rank`, `max_degree`, `bip`, `duplicate_groups`, `universal_roles`, `components`;
- class: `class`, `first_failed`, `witness_kind`, `witness_size`, `core_roles`, `core_relations`;
- widths: `{hw,ghw,fhw,tw}_{lower,upper,exact,method}`;
- run: `validated`, `disagreements`, `tools`, `time_limit`, `wall_seconds`.

The Markdown shows source, naming, slots, size, class (witness), core and widths, as `2` (exact) or `[2, 4]`.

### 6.6 Figure, outputs, reproduction, run time

**Figure.** `survey/make_figure.py` (matplotlib) writes a deterministic `results/figure-widths.{svg,png}` from
`figure-data.csv`: (a) hw per non-control row, a point when exact and a bar when bounded, beside the HyperBench CQ
shares; (b) GYO residue size per Wikidata source and slot set, log scale.

**`results/`** holds `survey.{md,csv,json}`, `reports/`, `schemas/` (with provenance), `crosschecks/`,
`hyperbench-baseline.json`, `solver-log.jsonl` (disagreements and demotions), `machine.json` and a `README.md` with
licences, attribution and how to reproduce.

**`survey/reproduce.sh`:**
1. Check the venv (`khg-width[survey,fast]`) and the solvers.
2. Verify the manifests. A missing file gets its fetch command: Biolink and Zenodo return identical bytes, and WDQS
   a new snapshot.
3. Generate the schemas from P3a's file when present (`--p3a-counts PATH`), else from SQID, and compare their
   sha256 with the committed files. A mismatch stops the run unless `--new-snapshot` is given.
4. Run the rows, then the baseline, then the table and the figure.

**Run time on 4 cores:** generation about 2 minutes; Biolink and control rows under 1 minute each; each wd-roles
row up to about 2.5 hours (30 minutes of Python bounds, at most 9 k values × 600 s, 2 second-opinion runs). So about
25 hours serial for the 10 wd-roles rows (4 on the slice), about 8 hours with `--jobs 3`, and about 1 hour without
solvers (bounds only).

**When P3a's file lands**, `run_survey.py --rows observed` regenerates and reruns only the observed rows; SQID-based
rows already run move to `results/superseded/`.

## 7. Implementation plan

| # | Step | Port from | Tests |
|---|---|---|---|
| 1 | Skeleton, CI job, `hypergraph.py` | `probe_schemas.to_hyperbench`, `hg_measure.stats` | hygiene |
| 2 | `acyclicity.py`, indexed | `p6check` class tests and witnesses; oracle `brute_force_class` | `test_acyclicity` |
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

The prototype's loops are rewritten with indices: observed-all under relation-local naming (13,608 relations, 83,030
roles) must classify in under 30 s.

## 8. Publication outline

**Working title:** *How acyclic are knowledge-hypergraph schemas? Acyclicity class and hypertree width of Wikidata
qualifier schemas and the Biolink Model.* 4–6 pages, arXiv (cs.DB) or a database or KG-schema workshop; the owner
submits it. The post draft goes in `post-draft.md`.

1. **Question** ([01.3]), and what the number measures: the role-join's width, not arbitrary queries'; Berge is
   acyclicity of the reified encoding.
2. **Objects:** the sources and their count sources, Biolink, wd-roles r1 (shared with P3a) and the controls, the
   slots, and the licences.
3. **Method:** class tests with witnesses; four widths with certificates validated on the input; sound bounds and
   reductions; the solvers and second opinions; time limits; reproducibility.
4. **Table and figure.**
5. **Findings:** class and hw of each non-control schema; the control; the time slots; declared against observed,
   dump against slice; hw against tw (tw ≥ 116 on the declared table); the position against HyperBench's CQs (all hw
   ≤ 3).
6. **Limits:** the role-join reading; a live snapshot and differing count dates; a meta list drawn by judgement; the
   naming version; bounds that are not exact; machine-dependent time limits.
7. **Artefacts:** khg-width, the schema files, the manifests and the reproduce script.

## 9. Risks and open questions

**Risks**
1. **The naming may change.** An r2 of wd-roles means regenerating the Wikidata files and rerunning their rows
   (hours). `test_survey` checks the naming version.
2. **Wikidata widths may stay bounds.** The residues lie where HyperBench has exact hw for 6 of 23 graphs, and
   unflagged refutations may never finish, so lower bounds may be just 2. That is a finding too (PLAN §8).
3. **P3a's file is not yet pushed.** Until it lands, the observed rows rest on SQID (`qs` meaning unverified, mixed
   dates) and are rerun when it lands (§6.6). WDQS itself cannot be refetched byte-identically.
4. **The meta list is judgement.** Only the top 120 declared and top 120 observed qualifiers were reviewed
   ([R02 §2.3]).
5. **Build.** Commits and Go sums pin the solvers; without Go the run is Python-only and still valid.
6. **Licences.** Only numbers come from the DeltaBot templates; Biolink's model says CC0 and its repository
   Apache-2.0, so attribution is given anyway.

**Questions for the director**
- **Q1.** F6 names `datasets/knowledge-bases/`, but HyperBench is not a knowledge base: keep its manifest there, or
  add a `benchmarks/` family?
- **Q2.** Is this the intended reading of F1: solvers get the unreduced H and may preprocess internally to *find* an
  HD, which is validated on H, while their flagged refutations are not used as bounds?
- **Q3.** Twin merging is unsound for tw, and lonely-role removal is sound only as the simplicial rule. Universal-role
  removal is added: exact for tw, sound for ghw and fhw, not used for hw. Agree?
- **Q4.** Deposit the CC0 raw Wikidata snapshot on Zenodo with the note?
- **Q5.** Commit the Wikidata schema files as `.json.gz` (about 4 MB) instead of plain JSON (about 40 MB)?

**Director's rulings (2026-09-24).**
- **Q1.** Add a dataset family `hypergraph-benchmarks` to `datasets/README.md` and put HyperBench's manifest under
  `datasets/hypergraph-benchmarks/hyperbench/`.
- **Q2.** Yes. A solver may preprocess to find a decomposition, which is then validated on the unreduced H. Only
  refutations from runs without preprocessing, or from preprocessing proven sound for that width, count as lower
  bounds.
- **Q3.** Agreed. Twin merging is not used for tw. Universal-role removal is used where it is exact or sound as
  stated, with the +1 for tw applied and tested.
- **Q4.** Not from a session: a Zenodo deposit is the owner's release step. Prepare the upload (the raw SPARQL
  snapshots, the generated schema files, the manifests and a README), and recommend it in the note's data
  statement, because WDQS results cannot be refetched byte-identically.
- **Q5.** Yes. Commit the Wikidata schema files as `.json.gz`, with their sha256 in the survey table; the checker
  reads `.json` and `.json.gz`. Biolink and the fixtures stay plain JSON.

## 10. KB corrections at base-update time

From R01 §1.5, applied in the same commit as the register update, together with the PLAN §9 row and the run log.

- [hypergraph-theory-results](../../kb/01-foundations/hypergraph-theory-results.md):
  - §5: "α is exactly the boundary of tractable join evaluation" is **wrong**. α ⇔ hw = 1 (GLS, Thm 4.4); bounded
    hw, ghw and fhw are tractable; submodular width characterises FPT under the ETH.
  - "α-acyclic ⇒ queries cheap" is **imprecise**: it concerns the role-join, and a query's cost comes from its own
    hypergraph.
  - The γ characterisation needs "with disjoint branches" (Duris).
  - §6: "only hw is tractable to check" is **imprecise**. ghw ≤ k is NP-complete for k ≥ 3 (GMS) and k = 2 (GLPR),
    with tractable cases. Add fhw ≤ ghw ≤ hw ≤ 3·ghw+1 and ghw ≤ tw+1, and resolve Grohe–Marx as *TALG* 11(1):4.
- [n-ary-relations-and-relational-algebra](../../kb/01-foundations/n-ary-relations-and-relational-algebra.md):
  - §2: "tractable whatever the instance" is **wrong**, for the same reason (combined complexity). Fagin and BFMY
    are about schemes, not "the first two" hypergraphs.
  - §3: "most interesting [schemas] are cyclic" becomes the survey result.
  - §4: "provably suboptimal on cyclic queries" is **overstated**. It holds for specific queries on worst-case
    instances; cite AGM or NPRR.
- [query-languages-for-hypergraphs](../../kb/05-query-embeddings-reasoning/query-languages-for-hypergraphs.md):
  - §10.2: ghw is NP-complete for k ≥ 3 and k = 2, and hw ≤ k is polynomial. The "used most in ML" claim is
    unsupported.
  - §10.3: reification raises width because the incidence graph is acyclic iff H is Berge-acyclic, not because atoms
    multiply.
- [open-questions](../../kb/00-index/open-questions.md) [01.3]: narrow "predicts query cost directly" to role-aligned joins (R01 §2.5), then mark the
  item closed or narrowed with a link to this folder.

## Sources

- [R01] [research/01-theory-and-solvers.md](research/01-theory-and-solvers.md) and [R02] [research/02-data-sources-and-naming.md](research/02-data-sources-and-naming.md), with their probes in [research/probes/](research/probes/).
- [wd-roles.md](wd-roles.md), version r1 (2026-09-24), the authoritative Wikidata naming.
- P2 [DESIGN.md](../p2-role-aware-hif/DESIGN.md) §2.4, §3 and §10; `khg_contracts.schema` and `khg_contracts.jsonio`.
- Fagin, *JACM* 30(3), 1983, https://doi.org/10.1145/2402.322390. Brault-Baron, *ACM CSUR* 49(3), 2016, https://arxiv.org/abs/1403.7076
- Gottlob, Leone, Scarcello, *JCSS* 64(3), 2002, https://arxiv.org/abs/cs/9812022. Grohe, Marx, *ACM TALG* 11(1):4, 2014, https://arxiv.org/abs/1711.04506
- Adler, Gottlob, Grohe, *Eur. J. Combin.* 28(8), 2007, https://doi.org/10.1016/j.ejc.2007.04.013. Gottlob, Lanzinger, Pichler, Razgon, *JACM* 68(5), 2021, https://arxiv.org/abs/2002.05239
- Moll, Tazari, Thurley, *IPL* 112(6), 2012, https://arxiv.org/abs/1106.4719. Gottlob, Samer, *ACM JEA* 13, 2008, https://doi.org/10.1145/1412228.1412229
- Fischl, Gottlob, Longo, Pichler, HyperBench, *PODS 2019*, https://doi.org/10.1145/3294052.3319683, and *ACM JEA* 26, 2021, https://doi.org/10.1145/3440015. Run data: Zenodo, https://doi.org/10.5281/zenodo.7180787 (CC BY 4.0)
- BalancedGo, https://github.com/cem-okulmus/BalancedGo, and *Constraints* 27(3), 2022, https://doi.org/10.1007/s10601-022-09332-1. log-k-decomp, https://github.com/cem-okulmus/log-k-decomp, and *PODS 2022*, https://doi.org/10.1145/3517804.3524153
- Wikidata:Copyright, https://www.wikidata.org/wiki/Wikidata:Copyright (read 2026-09-24); SQID, https://sqid.toolforge.org/data/
- Biolink Model v4.4.5, https://github.com/biolink/biolink-model; Unni et al., *Clin. Transl. Sci.*, 2022, https://doi.org/10.1111/cts.13302
