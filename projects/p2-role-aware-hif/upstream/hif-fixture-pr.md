---
title: "Draft: the HIF fixture PR with the five role-convention files (DESIGN §12.3)"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# Draft: the HIF fixture PR (W14; DESIGN §12.3)

**Nothing here has been pushed or opened.** The repository owner opens the PR from their own fork (the director's
ruling 2 on DESIGN §14). This file holds the PR text, the five files and the exact branch recipe, which was run on a
local clone of HIF-standard at `b691a3d` (2026-09-23): the branch equals the recipe's result, and HIF-standard's own
test suite passes on it (35 tests: its 30 and the 5 new ones).

## For the owner

- **When:** after the HIF issue ([hif-issue.md](hif-issue.md)) has an answer, as the issue announces. If the
  maintainers ask for other file names or another location, only the recipe's target names change.
- **Where:** a fork of https://github.com/HIF-org/HIF-standard, branch `role-convention-fixtures`, a PR against
  `main`.
- **Scope:** fixtures and tests only. No schema change, no README change (the README text is the issue's question;
  a paragraph for it is at the end, for use only if the maintainers ask for it in the same PR).

## The five files

They are the package's files, copied byte for byte (`src/khg_contracts/data/role-convention/`, mirrored in
`design-examples/role-convention/`). Each is valid against the vendored `hif_schema_v0.1.0.json` under jsonschema and
fastjsonschema, passes layer R, and round-trips through both loaders in source order (DESIGN §1.4).

| Upstream name (`tests/test_files/HIF-compliant/`) | Source | sha256 | What it shows |
|---|---|---|---|
| `role_convention_basic.json` | `basic.hif.json` | `7b3dae4b0c93151029e47351bc27407c5e0a637e58f84aa1e985059edb561ba4` | one role per incidence; the optional `role-vocabulary` |
| `role_convention_two_roles.json` | `two-roles.hif.json` | `0f84cebde01b474ee670d8be749006b90bc6410662dfa2d0c0b322c37233528c` | one node with two roles in one edge: a repeated pair that differs in `role` |
| `role_convention_tail_head.json` | `tail-head.hif.json` | `a2b222f2ed89328b2b625bf7344ae27a39c2b92d5ab4242dbcf1016333961d89` | one node in the tail and the head of a directed edge: a repeated pair that differs in `direction` and `role` |
| `role_convention_ordered.json` | `ordered.hif.json` | `1b7f8e306595e98c435211e3c47bf3d608d66ea96a1fab9d42dafbb9a477ea9a` | `role-position` (rule 4): one node at positions 1 and 3 of an ordered role |
| `role_convention_undirected.json` | `undirected.hif.json` | `b15a4b9ce556d543397f9918fc75c27f893aad9447cc8478286512fb8541a33b` | native directions kept on some incidences of an undirected file, beside an edge without any |

## The recipe

Run in the fork's checkout, with this repository checked out at the release tag next to it (`KHG` below):

```sh
git switch -c role-convention-fixtures
KHG=../knowledge-Hyper-Graphs-/src/khg_contracts/data/role-convention
for n in basic two-roles tail-head ordered undirected; do
  cp "$KHG/$n.hif.json" "tests/test_files/HIF-compliant/role_convention_${n//-/_}.json"
done
git apply role-convention-tests.patch     # the patch below, saved to a file
python -m pytest -q tests                 # 35 passed at b691a3d (pytest, fastjsonschema)
sha256sum tests/test_files/HIF-compliant/role_convention_*.json   # the five hashes above
git add -A && git commit -m "Add role-convention fixtures (compliant; no schema change)"
```

The commit adds 7 files and 245 lines: the five fixtures, 33 lines in `tests/conftest.py` and 26 in
`tests/test_compliant_files_against_schema.py`. HIF-standard lists every fixture and every test by name, so both
files need the additions:

```diff
diff --git a/tests/conftest.py b/tests/conftest.py
index 900a1b3..e120522 100644
--- a/tests/conftest.py
+++ b/tests/conftest.py
@@ -203,3 +203,36 @@ def missing_required_fields_with_direction():
 def extra_fields_with_direction():
     """Fixture for incidences with extra fields."""
     return json.load(open(f"{bad_json_dir}/extra_fields_with_direction.json", "r"))
+
+
+### Role convention (role-convention 1.0.0): roles in incidence attrs, no schema change
+
+
+@pytest.fixture
+def role_convention_basic():
+    """One role per incidence, with the optional role vocabulary in metadata."""
+    return json.load(open(f"{good_json_dir}/role_convention_basic.json", "r"))
+
+
+@pytest.fixture
+def role_convention_two_roles():
+    """One node with two roles in one edge: two incidence records for one (edge, node) pair."""
+    return json.load(open(f"{good_json_dir}/role_convention_two_roles.json", "r"))
+
+
+@pytest.fixture
+def role_convention_tail_head():
+    """One node in the tail and the head of one directed edge, with a role on each record."""
+    return json.load(open(f"{good_json_dir}/role_convention_tail_head.json", "r"))
+
+
+@pytest.fixture
+def role_convention_ordered():
+    """An ordered role: role-position orders its fillers, and one node fills two positions."""
+    return json.load(open(f"{good_json_dir}/role_convention_ordered.json", "r"))
+
+
+@pytest.fixture
+def role_convention_undirected():
+    """Directions kept on some incidences of an undirected file, beside an edge without any."""
+    return json.load(open(f"{good_json_dir}/role_convention_undirected.json", "r"))
diff --git a/tests/test_compliant_files_against_schema.py b/tests/test_compliant_files_against_schema.py
index d029b1e..a10559c 100644
--- a/tests/test_compliant_files_against_schema.py
+++ b/tests/test_compliant_files_against_schema.py
@@ -72,3 +72,29 @@ def test_valid_direction_tail(validator, valid_direction_tail):
 def test_missing_direction(validator, missing_direction):
     """Test a valid incidence without the direction field."""
     validator(missing_direction)
+
+
+# test the role convention (roles in incidence attrs; repeated (edge, node) pairs)
+
+
+def test_role_convention_basic(validator, role_convention_basic):
+    validator(role_convention_basic)
+
+
+def test_role_convention_two_roles(validator, role_convention_two_roles):
+    """Two records for one (edge, node) pair, which differ in role."""
+    validator(role_convention_two_roles)
+
+
+def test_role_convention_tail_head(validator, role_convention_tail_head):
+    """Two records for one (edge, node) pair, which differ in direction and role."""
+    validator(role_convention_tail_head)
+
+
+def test_role_convention_ordered(validator, role_convention_ordered):
+    """Two records for one (edge, node) pair, which differ in role-position."""
+    validator(role_convention_ordered)
+
+
+def test_role_convention_undirected(validator, role_convention_undirected):
+    validator(role_convention_undirected)
```

## PR title

Add role-convention fixtures (compliant; no schema change)

## PR description

Paste everything inside the fence; replace `#NN` with the issue's number.

````markdown
Follow-up to #NN, as offered there. This PR adds five **compliant** test files that use the proposed role
convention, and their tests. It changes no schema and no README.

| File | What it shows |
|---|---|
| `role_convention_basic.json` | one role per incidence, with the optional `role-vocabulary` in metadata |
| `role_convention_two_roles.json` | one node with two roles in one edge: two records for one (edge, node) pair, differing in `role` |
| `role_convention_tail_head.json` | one node in the tail and the head of one directed edge: two records for one pair, differing in `direction` and `role` |
| `role_convention_ordered.json` | an ordered role: `role-position` 1, 2, 3, with one node at positions 1 and 3 |
| `role_convention_undirected.json` | directions kept on some incidences of an undirected file, beside an edge without any |

Every file declares `metadata["role-convention"] = "1.0.0"` and puts roles only in `incidences[].attrs`, so all
five are valid against `schemas/hif_schema.json` as it is. `python -m pytest -q tests` gives 35 passed on this
branch (the 30 existing tests and the 5 new ones). The files are byte-identical to the fixtures of the
`khg-contracts` package, which also checks them against the four rules of the convention and round-trips them
through XGI and HyperNetX.

Three of the files repeat an (edge, node) pair, as `duplicated_nodes_edges.json` does. If the group decides that
incidences must be unique, the question in #NN applies, and we will rework the files to match.
````

## A README paragraph, if the maintainers ask for it

Only if the discussion on the issue asks for it in this PR, under the README's **Notes**:

```markdown
* `incidences` may contain several records for the same (edge, node) pair. The records of one pair may differ in
  `direction` (a node in both the tail and the head of an edge) and in `attrs` (a node with two roles). Readers
  should keep every record and round-trip `attrs`, including keys they do not know.
```
