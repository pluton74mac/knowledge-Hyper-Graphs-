---
title: "Releasing khg-contracts 1.0.0 to PyPI (W14; DESIGN §11.2)"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# Releasing khg-contracts 1.0.0 to PyPI

**Nothing has been published.** The repository owner owns the PyPI project `khg-contracts` and publishes it (the
director's ruling 2 on DESIGN §14: "Nothing is published or filed from a Claude session. W14 ends at 'ready for the
owner'"). This file gives the exact steps. DESIGN §11.2 sets the rule: 1.0.0 goes to PyPI once G1-G3 pass, and P2
cuts every release.

## What was checked on 2026-09-23

- **The name is free.** `https://pypi.org/pypi/khg-contracts/json` and `https://test.pypi.org/pypi/khg-contracts/json`
  both answered 404.
- **The six CI jobs of DESIGN §10.6 pass locally** on the commit that adds this file (details in
  [../impl-notes/W13-W14.md](../impl-notes/W13-W14.md)): core-3.10, gate-3.11, core-3.13, wheel, examples and
  evidence. That run predates the director's rulings (commit f99a8af): from there until the review round
  re-copied the P7 sequence, `tests/consumers/test_verbatim.py::test_the_copy_is_verbatim[P7]` failed in the three
  test jobs. Run the six jobs again on the release commit; step 5.4 waits for them on the pull request.
- **Steps 5.1 and 5.3 were rehearsed** on a copy of the tree: with the version at 1.0.0 and the README below, the
  build succeeds, `twine check --strict` passes on the sdist and the wheel, and the 1.0.0 wheel, installed alone with
  the `dev` extra, passes the packaging, consumer and CLI tests (292 passed, 1 skipped: P5 without xgi).
- **Without step 5.3,** `twine check` passes with two warnings (`long_description` missing), and the PyPI page has no
  description.

## Choices made here

Change any of them before step 2; the trusted-publisher fields must match the workflow exactly.

| Choice | Value |
|---|---|
| Tag | `khg-contracts-v1.0.0` (the repository holds more than the package, so the tag names it) |
| Workflow | `.github/workflows/release.yml` (step 4) |
| GitHub environments | `pypi`, and `testpypi` for the optional dry run |
| Credentials | trusted publishing (OpenID Connect): no API token is stored anywhere |

## 1. Accounts (once)

- A PyPI account with two-factor authentication: https://pypi.org/account/register/
- Optional, for the dry run: a TestPyPI account, which is separate: https://test.pypi.org/account/register/

## 2. The trusted publisher on PyPI (once)

On https://pypi.org/manage/account/publishing/, under "Add a new pending publisher", choose GitHub and enter:

| Field | Value |
|---|---|
| PyPI Project Name | `khg-contracts` |
| Owner | `pluton74mac` |
| Repository name | `knowledge-Hyper-Graphs-` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

A pending publisher does not reserve the name: the project is created by the first upload through it. For the dry
run, do the same on https://test.pypi.org/manage/account/publishing/ with the environment name `testpypi`.

## 3. The GitHub environments (once)

In the repository, Settings → Environments → New environment:

- **`pypi`**
  - Deployment protection rules: **Required reviewers**, the owner. Every publish then waits for an approval.
  - Deployment branches and tags: **Selected branches and tags**, with the tag rule `khg-contracts-v*`.
- **`testpypi`** (optional): Required reviewers, the owner; deployment branches limited to `main`.

## 4. The release workflow (once)

Add this file as `.github/workflows/release.yml` on `main`. It builds the sdist and the wheel once, repeats the CI
`wheel` job's checks on the wheel, checks that the tag names the package version, and publishes the same files: to
TestPyPI when started by hand, to PyPI when a `khg-contracts-v*` tag is pushed.

```yaml
# Publishes khg-contracts with PyPI trusted publishing (OIDC); no API token is stored.
# A pushed tag khg-contracts-vX.Y.Z publishes to PyPI; "Run workflow" publishes to TestPyPI (a dry run).
name: release

on:
  push:
    tags:
      - "khg-contracts-v*"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    name: build and check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Build the sdist and the wheel
        run: |
          python -m pip install --upgrade build twine
          python -m build --outdir dist .
          python -m twine check dist/*
      - name: Install the wheel into a clean venv
        run: |
          python -m venv "$RUNNER_TEMP/venv"
          "$RUNNER_TEMP/venv/bin/python" -m pip install dist/*.whl
      - name: The tag names the package version
        if: github.event_name == 'push'
        run: |
          VERSION=$("$RUNNER_TEMP/venv/bin/python" -c "import khg_contracts; print(khg_contracts.__version__)")
          test "khg-contracts-v$VERSION" = "$GITHUB_REF_NAME"
      - name: The wheel job's checks (package-data hashes, khg-validate, khg-conformance)
        working-directory: ${{ runner.temp }}
        run: |
          PY="$RUNNER_TEMP/venv/bin/python"
          "$PY" -m khg_contracts.data --check
          FIXTURE=$("$PY" -c "import khg_contracts.data as d; print(d.path('fixture/fixture.c1.json'))")
          SCHEMA=$("$PY" -c "import khg_contracts.data as d; print(d.path('fixture/fixture.relation-schema.json'))")
          "$RUNNER_TEMP/venv/bin/khg-validate" "$FIXTURE" --kind container --schema "$SCHEMA"
          "$RUNNER_TEMP/venv/bin/khg-conformance" --factory khg_contracts.store:memory_factory
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          if-no-files-found: error

  testpypi:
    name: publish to TestPyPI (dry run)
    if: github.event_name == 'workflow_dispatch'
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: testpypi
      url: https://test.pypi.org/project/khg-contracts/
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/
          skip-existing: true

  pypi:
    name: publish to PyPI
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/khg-contracts-v')
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/project/khg-contracts/
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Optional hardening: pin each action to a commit SHA instead of a tag.

## 5. The release commit

On a branch from `main`:

1. **The version, 1.0.0.dev0 → 1.0.0.** The version lives in `src/khg_contracts/__init__.py` (hatchling reads it,
   `[tool.hatch.version]`), and two W0 tests pin it:

   ```sh
   sed -i 's/__version__ = "1.0.0.dev0"/__version__ = "1.0.0"/' src/khg_contracts/__init__.py
   sed -i 's/__version__ == "1.0.0.dev0"/__version__ == "1.0.0"/' tests/packaging/test_api.py
   sed -i 's/out\["version"\] == "1.0.0.dev0"/out["version"] == "1.0.0"/' tests/packaging/test_import_hygiene.py
   git grep -n "1.0.0.dev0" -- src tests pyproject.toml      # nothing left
   ```

2. **The classifier (optional).** `pyproject.toml` says `Development Status :: 3 - Alpha`. For a 1.0.0 that consumers
   pin, `Development Status :: 5 - Production/Stable` is the usual signal.
3. **The PyPI page (recommended).** Add `README-khg-contracts.md` at the repository root with the text below, and the
   line `readme = "README-khg-contracts.md"` under `[project]` in `pyproject.toml`, after `description`. Hatchling
   puts the file in the sdist by itself.

   ````markdown
   # khg-contracts

   The shared contracts of the knowledge-hypergraph programme, as one Python package:

   - **C1** `khg-record/1.0.0`: n-ary facts as hyperedges with role bindings, typed literals, keys, valid and
     transaction time, lifecycle and evidence, in `.khg.json` and `.khg.jsonl` containers;
   - **role-aware HIF**: the `role-convention` 1.0.0 for incidence attributes and the `khg-hif/1.0.0` profile, with
     loaders for XGI and HyperNetX that keep every role;
   - **C2** `khg-store/1.0.0`: the store interface, a reference in-memory store and a 114-scenario conformance suite;
   - **C3** `khg-queue/1.0.0`: candidate queues and action logs with replay;
   - **C5** `khg-scorers/1.0.0`: extraction, stability, completion, retrieval and memory scorers;
   - a layered validator with stable error codes, and four command-line tools: `khg-validate`, `khg-convert`,
     `khg-migrate` and `khg-conformance`.

   ```
   pip install khg-contracts                # the core: jsonschema and fastjsonschema only
   pip install "khg-contracts[xgi,hnx]"     # the XGI and HyperNetX loaders
   ```

   The design is `projects/p2-role-aware-hif/DESIGN.md` in
   https://github.com/pluton74mac/knowledge-Hyper-Graphs- . MIT licence; the vendored HIF schema keeps its own MIT
   notice (`HIF-LICENSE.txt`, Copyright (c) 2024-2025 HIF development team).
   ````

4. Commit, open a pull request, wait for the six CI jobs to pass, and merge it into `main`.

## 6. Dry run on TestPyPI (optional)

1. Actions → release → Run workflow, on `main`. Approve the `testpypi` deployment when asked.
2. Check https://test.pypi.org/project/khg-contracts/ , then install from it in a clean virtual environment (the
   dependencies come from PyPI):

   ```sh
   python -m venv /tmp/khg-test && . /tmp/khg-test/bin/activate
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ khg-contracts==1.0.0
   khg-conformance --factory khg_contracts.store:memory_factory     # 114 passed
   ```

TestPyPI keeps a version once uploaded; `skip-existing` lets the dry run be repeated.

## 7. Tag and publish

```sh
git switch main && git pull
git tag -a khg-contracts-v1.0.0 -m "khg-contracts 1.0.0"
git push origin khg-contracts-v1.0.0
```

The push starts the workflow. Approve the `pypi` deployment when asked. The release is at
https://pypi.org/project/khg-contracts/1.0.0/ .

## 8. Check the published package

In a clean virtual environment:

```sh
python -m venv /tmp/khg-1.0.0 && . /tmp/khg-1.0.0/bin/activate
pip install khg-contracts==1.0.0
cd "$(mktemp -d)"
python -m khg_contracts.data --check                                  # package-data hashes
FIXTURE=$(python -c "import khg_contracts.data as d; print(d.path('fixture/fixture.c1.json'))")
SCHEMA=$(python -c "import khg_contracts.data as d; print(d.path('fixture/fixture.relation-schema.json'))")
khg-validate "$FIXTURE" --kind container --schema "$SCHEMA"           # valid, 2 designed warnings (S024, L008)
khg-conformance --factory khg_contracts.store:memory_factory          # 114 passed, 0 failed
pip install "khg-contracts[xgi,hnx]==1.0.0"                           # the pinned extras resolve
```

## 9. After the release

1. **A GitHub release** for the tag, pointing at DESIGN.md and the gate (G1-G3).
2. **Main moves on to 1.1.0.dev0:** the three lines of step 5.1, with `1.0.0` → `1.1.0.dev0`, so that `main` never
   carries a released version number.
3. **The upstream items**, in this order ([hif-issue.md](hif-issue.md), [xgi-issue.md](xgi-issue.md),
   [hypernetx-issue.md](hypernetx-issue.md), [hif-fixture-pr.md](hif-fixture-pr.md)): the HIF issue first; the XGI
   and HyperNetX issues the same day; the fixture PR once the HIF maintainers have answered. Their links point at the
   tag `khg-contracts-v1.0.0`.
4. **Consumers** pin `khg-contracts==1.0.0` and record `khg_contracts.CONTRACTS` (DESIGN §11.1).

## If something goes wrong

- **`invalid-publisher` in the publish step.** The owner, repository, workflow file name or environment name
  differs from the pending publisher of step 2. Fix either side and re-run the job.
- **The tag check fails.** The tag and `__version__` disagree. Delete the tag
  (`git push --delete origin khg-contracts-v1.0.0` and `git tag -d khg-contracts-v1.0.0`), fix, and tag again.
- **A broken release.** PyPI never accepts a second upload of one version. Yank it (the project's Manage → Releases
  page on PyPI) and release 1.0.1 (a patch, DESIGN §11.2).
