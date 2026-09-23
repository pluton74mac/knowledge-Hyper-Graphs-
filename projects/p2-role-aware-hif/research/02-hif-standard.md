---
title: What the HIF standard says today, from primary sources
type: survey
status: draft
created: 2026-09-23
---

# What the HIF standard says today, from primary sources

This is P2 research report 02. It covers the Hypergraph Interchange Format (HIF) as it stands on
2026-09-23, working from the repository history, the schema files, the paper, the release archives
and the issue tracker. It also reports probes that validate 36 edge-case files and this
repository's `schemas/sample.hif.json` against every schema snapshot. P2 needs four things from this
report: what a role-aware HIF file may legally contain today, where a vocabulary and a version can
live, how stable the target is, and how to take a proposal upstream.

Evidence levels used below. **[git]** means verified in a full clone of the repository (commit SHAs
given). **[file]** means verified on downloaded bytes (sha256 recorded). **[run]** means executed
here. **[web]** means read through the WebFetch tool, which passes pages through a model. For the
load-bearing [web] quotes I fetched the page twice with different prompts and got the same text,
but they are not byte-verified. **[unverified]** means I could not check it. Sections 1–10 are
findings. Section 11 is recommendation and is labelled as such.

Probe artefacts: [probes/hif-schema/](probes/hif-schema/) holds the vendored schema snapshots with
provenance, the cases, `validate_cases.py`, `results.md` and `hnx_validation_probe.py`.

## Summary

- **One repository, three names.** `pszufe/HIF_validators`, `pszufe/HIF-standard` and
  `HIF-org/HIF-standard` are the same GitHub repository. It was renamed and then transferred, and
  GitHub redirects the old names. Cloning any of the three gives the same 139 commits and the same
  HEAD `b691a3d` (2026-03-19) [git]. This settles most of open question [04.1] (section 4.4).
- **Two schema files with identical validation rules.** `schemas/hif_schema.json`
  (`"version": "latest"`) and `schemas/hif_schema_v0.1.0.json` (`"version": "0.1.0"`) differ only in
  `$id` and `version`. Their validation keywords have not changed since commit `de5f89f`
  (2024-10-03), 720 days before this check [git].
- **The version labels contradict each other.** The CHANGELOG says `v0.0`, one schema file says
  `0.1.0`, the other says `latest`, the releases are `v0.1.0`–`v0.1.2`, and a maintainer calls the
  current release "v1". A "v2" is being planned (section 4.1).
- **The schema is strict about keys and loose about content.** Only `incidences` is required at the
  top level, and only `edge` and `node` in an incidence. `additionalProperties: false` applies at
  the top level and on all three record kinds. `attrs` and `metadata` are unconstrained objects
  [file].
- **Roles fit today only inside `attrs`, and a vocabulary or version only inside `metadata`.** A
  role in `incidences[].attrs.role` validates. So does a vocabulary or version block inside
  `metadata`. A top-level `version`, `roles` or `$schema` key fails, and so does a record-level
  `role`, `relation` or `type` key [run].
- **The paper's own example of an incidence attribute is a role:**
  `{"edge": 1, "node": 3, "attrs": {"role": "PI"}}`. An upstream compliant test file uses the same
  key [file]. Nobody upstream has proposed a role convention or a file-level version declaration
  (section 9).
- **The schema checks none of the semantics P2 cares about.** There is no uniqueness check, no
  check that referenced nodes and edges are declared, no rule on whether a node id may equal an
  edge id, and no consistency check between `direction` and `network-type`. The paper says libraries "are
  ultimately responsible" for these [file].
- **HyperNetX 2.4.3 is the only one of the three Python libraries that validates.** It fetches the
  schema at run time from the oldest repository name. On a schema-invalid file `from_hif` returns
  `None` without raising, and `to_hif(metadata=<dict>)` returns `None` [run].
- **Upstream is quiet but responsive.** The last commit was 2026-03-19, with none in the six
  months since. Recent external PRs got a first reply within a day. There are no contribution
  guidelines. Design decisions are taken at group meetings and on Discord (section 8).

## 1. Method and limits

- **Repository.** Full clones of `https://github.com/HIF-org/HIF-standard`,
  `https://github.com/pszufe/HIF-standard` and `https://github.com/pszufe/HIF_validators`, plus the
  organisation profile repository `https://github.com/HIF-org/.github`. PR heads for #14, #21 and
  #34 were fetched with `git fetch origin pull/N/head`. Clones went to a scratch directory, not
  this repository.
- **Files.** Schema snapshots were downloaded from commit-pinned `raw.githubusercontent.com` URLs
  and checked against their git blob ids ([probes/hif-schema/README.md](probes/hif-schema/README.md)).
- **Paper.** Metadata came from the Crossref API for DOI 10.1017/nws.2025.10018. The text came from
  arXiv:2507.11520 v1 and v2 (PDFs). The v2 PDF is typeset in the journal template ("Network
  Science (2025), 0, 1–21"), and page numbers below refer to it. I did not read the Cambridge
  version of record, so identical wording is [unverified].
- **Zenodo.** Read through the Zenodo REST API. The v0.1.2 archive was downloaded and hashed.
- **Issues and PRs.** `api.github.com` refused this repository under the session's egress policy
  (HTTP 403, "GitHub access to this repository is not enabled for this session"). The GitHub MCP
  tools are scoped to this project's own repository, and `github.com` HTML is 403 to `curl`. I
  therefore read the tracker through WebFetch. PR pages render their conversations. Issue pages
  render only the opening post: the fetcher also saw no comments on microsoft/vscode#519, which has
  many. **Issue comment threads are therefore unread [unverified].** To find out whether
  particular words appear in comments, I used GitHub search result snippets, since search indexes
  comments. The issue and PR inventory was completed by fetching #1–#7 individually, because the
  list pages came back truncated.
- **Libraries.** I grepped the PyPI wheels of xgi 0.10.2, hypernetx 2.4.3 and hypergraphx 1.8.0,
  the latest releases on 2026-09-23. I ran HyperNetX 2.4.3 in a separate virtual environment.
  Loader behaviour on roles is outside this report.

## 2. Where HIF lives

### 2.1 One repository under three names [git, web]

| Name | Status | Evidence |
|---|---|---|
| `pszufe/HIF_validators` | original name. The initial commit `b4e1b35` (2024-07-17) has the README title `# HIF_validators` and the subtitle "Hypergraph Exchange Format (HIF) definition and validator libraries" | `git show b4e1b35:README.md` |
| `pszufe/HIF-standard` | renamed after issue [#2](https://github.com/HIF-org/HIF-standard/issues/2) (2024-07-26, "I wonder if `HIF-standard` or `HIF-specification` would be more appropriate of a name for the repo."). The README switched its URLs from `HIF_validators` to `HIF-standard` in `e69edd4` (2024-10-03) | `git show e69edd4` |
| `HIF-org/HIF-standard` | current home. The organisation's profile repository was first committed on 2026-01-09 (`384e4c3`). The exact transfer date is [unverified] | clone of `HIF-org/.github` |

All three URLs clone to HEAD `b691a3d2ec32100c0229ebe1151e9afad015c356` with 139 commits.
WebFetch of `https://github.com/pszufe/HIF_validators` renders the page "HIF-org / HIF-standard".
The files in the repository still point at the old names: the README validation snippets (lines 57,
73, 90) and the issue link (line 145), `CITATION.cff` (`repository-code`), both schema `$id`s, the
Zenodo related identifiers, and the paper's footnote 8. They resolve only through GitHub's
redirects. GitHub documents that redirects stop if a repository is later created at the old
location: "If you create a new repository or fork at the previous repository location, the
redirects to the transferred repository will be permanently deleted"
([GitHub Docs, transferring a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository)).
For renames the docs say: "If you create a new repository under your account in the future, do not
reuse the original name of the renamed repository. If you do, redirects to the renamed repository
will no longer work"
([GitHub Docs, renaming a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository)).
Both pages were read 2026-09-23 [web].

The organisation `HIF-org` has no public members and two repositories, `HIF-standard` (36 stars,
9 forks) and `.github` [web, 2026-09-23]. Discussions are not enabled (the `/discussions` page
returns 404).

### 2.2 Releases and archives [git, web, file]

| Release | Tag commit | Zenodo record | Zenodo date | Release note (Zenodo) |
|---|---|---|---|---|
| v0.1.0 | `8a97237` (2025-07-03) | [10.5281/zenodo.15802760](https://doi.org/10.5281/zenodo.15802760) | 2025-07-04 | "The Hypergraph Interchange Format (HIF) standard … Initial release v0.1.0" |
| v0.1.1 | `fbbf27b` (2025-10-02) | [10.5281/zenodo.17251025](https://doi.org/10.5281/zenodo.17251025) | 2025-10-02 | "Added details about the collection and postprocessing of the publication dataset." |
| v0.1.2 | `c013910` (2025-10-03) | [10.5281/zenodo.17257719](https://doi.org/10.5281/zenodo.17257719) | 2025-10-03 | "Fix issues related to nx_hif and improved the figure quality." |

The concept DOI [10.5281/zenodo.15802759](https://doi.org/10.5281/zenodo.15802759) resolves to the
latest version. The Zenodo related identifier for every version is
`https://github.com/pszufe/HIF-standard/tree/<tag>`. Both schema files have the same blobs at all
three tags and at HEAD. The v0.1.2 archive, `pszufe/HIF-standard-v0.1.2.zip` (md5
`6d8e90b23647d844473e1e3c6f1aa2c9`, matching Zenodo's own checksum), contains both schema files
byte-identical to HEAD. The paper cites this record as "the stable schema" (Data Availability
Statement and reference list, arXiv v2 p.17) [file].

### 2.3 The paper [web, file]

Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B. and
Szufel, P. "HIF: The hypergraph interchange format for higher-order networks." *Network Science*
13, e21, Cambridge University Press. Crossref gives 2025-12-11 as the online publication date and
the licence as CC BY 4.0 ([doi:10.1017/nws.2025.10018](https://doi.org/10.1017/nws.2025.10018)).
Preprint: [arXiv:2507.11520](https://arxiv.org/abs/2507.11520), v1 2025-07-15, v2 2026-01-30.
Author list and venue agree across Crossref, arXiv, the README BibTeX and `CITATION.cff`.
Affiliations per Crossref and the v2 PDF:

- Coll: University of Buenos Aires.
- Joslyn: Pacific Northwest National Laboratory (PNNL) and Binghamton University.
- Landry: University of Virginia and University of Vermont. Landry is the corresponding author.
- Lotito: University of Trento and Central European University.
- Myers and Praggastis: PNNL.
- Pickard: Broad Institute and University of Michigan.
- Szufel: SGH Warsaw School of Economics.

### 2.4 Licence and project files [git]

The licence is MIT, "Copyright (c) 2024-2025 HIF development team" (`LICENSE`, blob `5997fb9`).
`CITATION.cff` says `version: "0.1.0"` and `date-released: 2025-07-07`. The repository has no
CONTRIBUTING, CODE_OF_CONDUCT, GOVERNANCE, CODEOWNERS or issue/PR templates. The organisation's
`.github` repository contains only `profile/README.md`. The only instruction to outsiders is
README line 145: to list a project, "open a GitHub issue."

## 3. What the standard says (normative text)

There are three documents: the paper (§2–3, Table 1), the schema file and the README. The paper
and the schema agree everywhere I checked. The README's field list is the odd one out (see
"Documented inconsistencies" below).

Structure (paper Table 1, arXiv v2 p.6):

- Top level: `network-type` (optional, enum "directed", "undirected" or "asc"), `metadata`
  (optional object), `incidences` (required array), `nodes` (optional array) and `edges`
  (optional array).
- Incidence record: `edge` (required, "string or integer", "an edge ID"), `node` (required, "a node
  ID belonging to that edge"), `weight` (optional number), `direction` (optional, "head" or "tail")
  and `attrs` (optional object, "library-specific non-structural attributes").
- Node record: `node` ("a global node ID"), `weight` and `attrs`.
- Edge record: `edge` ("a global hyperedge ID"), `weight` and `attrs`.

The statements that matter for P2 (arXiv v2):

- **Formal model (p.3).** "a *hypergraph* is a system H = (V, E, I) where V … is a finite,
  non-empty set of vertices …, E … is a finite, non-empty set of edges …, and I ⊆ V×E is a set of
  *incidences*." The edge collection "would be a multiset or bag of hyperedges, and so possibly
  containing duplicates."
- **Direction (p.3–4).** A directed hyperedge is an ordered pair e = (t, h). "While the tail and
  head cover the hyperedge in that t ∪ h = e, … here we generalize this framework and allow nodes
  to belong to both the tail and head." An incidence property "can be used to encode whether v is
  in the tail v ∈ t, the head v ∈ h, or in both."
- **Incidence attributes are the role slot (p.4, p.7).** "a node v ∈ V can have one property when
  associated with an incidence (v, e) … but could have quite a different property when associated
  with a different incidence (v, f)". Also: "Incidences can also have properties, which indicate
  hyperedge-dependent nodal attributes. All of these attributes are bundled as dictionary-like
  objects in each incidence record under the `attrs` field, e.g., {"edge": 1, "node": 3, "attrs":
  {"role": "PI"}} might indicate node 3's role as a PI on project 1." The same example is in v1.
- **Nodes and edges are distinct objects (p.4).** The bipartite view is built on "the disjoint
  union of the nodes V and hyperedges E". The paper does not talk about ids. My inference is that a
  node id equal to an edge id does not make that node the edge.
- **network-type (p.7).** "When using the "directed" keyword, this indicates that the library
  should expect the "direction" field …. When the network-type is not specified, it is assumed
  that the type is an undirected hypergraph."
- **metadata (p.7).** "The schema allows any object in the metadata property, including deeply
  nested structures. Dataset authors are encouraged to use a flat object and to use only lowercase
  characters and hyphens, a convention commonly known as "dash case"."
- **What validation does not cover (§3.2, p.8).** "independent software packages which utilize
  this standard are ultimately responsible for reading and writing datasets". "while end users are
  able to, in principle, specify the direction keyword for network datasets even if the
  network-type keyword is not directed and to omit the direction keyword even when network-type is
  directed, for simplicity, we simply say that direction field is optional."
- **Versioning process (§3.3, p.8; also in v1).** "1. Decide on the new version number based on the
  changes made since the last version and the Semantic Versioning guidelines … 2. Copy the schema
  in the hif_schema.json file to a file named hif_schema_<version>.json … 3. Add the changes made
  since the last release to CHANGELOG.md in a section with the new version as the name. 4. Upload
  the new stable version to Zenodo as a persistent reference. The hif_schema.json schema will
  always have version "latest" and all unit tests are based on this schema."
- **Extensions (§6, p.17).** Signed, multilayer and temporal hypergraphs are "implicitly supported"
  in that the structural information "can be stored in the attrs field, but the schema excludes
  these as expected JSON fields. In the future, adding explicit support for these fields will
  improve compatibility". JSONL and database formats are mentioned as possible "future iterations
  of HIF".

Documented inconsistencies (facts, not judgements):

1. The README (lines 36–41) lists only `node`/`attrs` and `edge`/`attrs` for node and edge records.
   The schema and the paper's Table 1 also allow `weight`.
2. The formal model makes I a *set* of (v, e) pairs, and says a node may be in both tail and head.
   But `direction` is single-valued, so the only schema-valid way to put a node in both is two
   incidence records for the same (edge, node) pair. An upstream compliant test,
   `tests/test_files/HIF-compliant/duplicated_nodes_edges.json`, repeats exactly such a pair. Its
   test says "Expect to pass unless uniqueness is enforced"
   (`tests/test_compliant_files_against_schema.py`).
3. The formal model requires V and E to be non-empty. The schema and the upstream test
   `empty_hypergraph.json` accept `{"incidences": []}`.

## 4. Schema files and versions

### 4.1 Version labels in circulation [git, web]

| Where | Label | Source |
|---|---|---|
| `schemas/CHANGELOG.md` | `## v0.0` "Initial schema …" (the only entry) | blob `cb61bc9` |
| `schemas/hif_schema_v0.1.0.json` | `"version": "0.1.0"` | blob `e2105bb` |
| `schemas/hif_schema.json` | `"version": "latest"` | blob `5651f07` |
| git tags and Zenodo | `v0.1.0`, `v0.1.1`, `v0.1.2` | section 2.2 |
| `CITATION.cff` | `version: "0.1.0"` | HEAD |
| issue [#55](https://github.com/HIF-org/HIF-standard/issues/55) (2025-12-09) | "HIF is a standard for higher-order network data, with v1 released with support for Directed and Undirected Hypergraphs. HIF v2, in current development, will focus on supporting Temporal Hypergraphs and providing a performant Columnar Format for all network types." | [web] |
| issue [#51](https://github.com/HIF-org/HIF-standard/issues/51) (2025-11-21) | goals include "JSON Schema v2 with support for temporal networks" | [web] |

How the CHANGELOG came to say `v0.0` [git, web]:

- The CHANGELOG was added on 2024-09-26 in PR #16 (`7aefda6`) with the heading `## v0.1.0`.
- The squash-merge of PR [#34](https://github.com/HIF-org/HIF-standard/pull/34) ("Split schema
  title and version", 2025-05-02, `58447e4`) changed the heading to `## v0.0`.
- In that PR's review, colltoaction wrote: "Note that `0.0` doesn't follow
  [semver](https://semver.org/) but the rest looks good. Consider reverting to `0.1.0`." The
  author replied "Fixed!"
- The schema file ended at `0.1.0` and the CHANGELOG stayed at `v0.0`. My reading is that the
  CHANGELOG change was an oversight, but that is an inference.

The version keyword itself: `"version"` is not a JSON Schema keyword. Draft-07 says "Unknown
keywords SHOULD be ignored"
([JSON Schema core, draft-07](https://json-schema.org/draft-07/json-schema-core.html)). So the label
describes the schema document and has no effect on validation. There is no field in a HIF *data*
file that states which version it targets, and one cannot be added at the top level (section 5).

### 4.2 The published schema, level by level [file]

Both files are at commit `b691a3d2ec32100c0229ebe1151e9afad015c356` (2026-03-19).

| Item | `schemas/hif_schema.json` | `schemas/hif_schema_v0.1.0.json` |
|---|---|---|
| Pinned URL | `https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema.json` | same commit, `…/schemas/hif_schema_v0.1.0.json` |
| Last changed | `6ffdb48` 2025-05-02 (rename) | `c8e2d4f` 2025-05-02 (`$id` fix) |
| git blob / sha256 | `5651f07b…` / `3f49e6cb4bf1ff5c41e6f4bfe95da35d258436aa1ece92e54993e77389c11b2e` | `e2105bb8…` / `639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196` |
| `$schema` | `http://json-schema.org/draft-07/schema#` | same |
| `$id` | `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/schema.json` (**404**) | `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json` (200 via redirect) |
| `title` / `version` | "Hypergraph Interchange Format" / `latest` | same / `0.1.0` |

The validation keywords are identical in both files:

| Level | `required` | `additionalProperties` | Properties and types |
|---|---|---|---|
| top level (`type: object`) | `["incidences"]` | `false` (also `unevaluatedProperties: false`, which draft-07 ignores) | `network-type` enum `["undirected","directed","asc"]`, with no `type`; `metadata` `{type: object}` with no other constraint; `incidences`, `nodes`, `edges` arrays |
| `incidences[]` (`type: object`) | `["edge","node"]` | `false` (+ `unevaluatedProperties: false`) | `edge`, `node`: `["string","integer"]`; `weight`: `number`; `direction`: enum `["head","tail"]`; `attrs`: `{type: object}` with no other constraint |
| `nodes[]` (`type: object`) | `["node"]` | `false` (+ same) | `node`: `["string","integer"]`; `weight`: `number`; `attrs`: object |
| `edges[]` (`type: object`) | `["edge"]` | `false` (+ same) | `edge`: `["string","integer"]`; `weight`: `number`; `attrs`: object |

The schema has none of these: `minItems`, `uniqueItems`, id `pattern`/`format`/`minLength`,
`default`, `dependencies`/`if-then`, or any constraint inside `attrs` or `metadata`.
`unevaluatedProperties` was introduced in draft 2019-09
([release notes](https://json-schema.org/draft/2019-09/release-notes): "**new** | Similar to
`additionalProperties`, but can "see" into subschemas"). A draft-07 validator therefore relies on
`additionalProperties` alone. Draft-07 defines `"integer"` as matching "any number with a zero
fractional part" (§6.1.1 of
[the validation spec](https://json-schema.org/draft-07/json-schema-validation.html)), so `1.0` is a
valid id (case 17).

### 4.3 Every schema version, and what each allows and forbids [git, run]

| Snapshot | Commit (how it landed) | Record form | `attrs` key | Extra top-level keys | Extra record keys | `network-type` | `direction` |
|---|---|---|---|---|---|---|---|
| S0 2024-08-05 `hif_schema.json` (repo root) | `c58b153` "Initial JSONSchema" (Coll, direct) | incidences are arrays `[edge, node, {attrs}]`; `nodes`/`edges` use `prefixItems`, a 2020-12 keyword that draft-07 ignores | positional object | allowed | n/a | any string | none |
| (2024-08-07 `hif_schema1.json`, `hif_schema2.json`) | `0a15910` "initial proposal" (Szufel) | not valid JSON; deleted 2024-08-13 | — | — | — | — | — |
| S1 2024-08-13 `schemas/hif_schema_v0.1.0.json` | `e212654`…`e5c868b` (Praggastis, direct) | object records, `required` ids | `attr` | allowed | allowed. `unevaluatedProperties:false` was placed *inside* `properties`, where it has no effect | enum | enum head/tail |
| S2 2024-08-21 | `53a8a93` "fix bad_top_level_field" (Coll, direct) | same | `attr` | **forbidden** | allowed | enum | enum |
| S3 2024-09-26 | `7aefda6`, PR #16, fixes issue #15 | same | **`attrs`** (breaking rename) | forbidden | allowed | enum | enum |
| S4 2024-10-03 | `de5f89f`, PR #18 (merged 2024-10-07) | same | `attrs` | forbidden | **forbidden** (`additionalProperties:false` on all three records) | enum | enum |
| published 2025-05-02 | `58447e4` PR #34, then `6ffdb48` and `c8e2d4f` (direct) | identical rules to S4. Adds a `version` annotation, splits the file into `latest` and `0.1.0`, and renames `schema*.json` to `hif_schema*.json` | `attrs` | forbidden | forbidden | enum | enum |

So the file path `schemas/hif_schema_v0.1.0.json` has served four sets of validation rules (S1–S4)
between 2024-08-13 and 2024-10-03 under the same version name. That was before the §3.3 process
existed, and the name has been stable since. One PR tried to loosen S4:
[#21](https://github.com/HIF-org/HIF-standard/pull/21) (Praggastis, 2024-11-04) would have allowed
record-level extra properties with scalar values (`"additionalProperties": {"type": ["string",
"integer", "number", "boolean"]}` on all three record kinds, commit `bfc6467` on the PR head). It
was closed unmerged on 2024-11-06 (section 9).

### 4.4 The four URLs of question [04.1], resolved [file, git]

| URL | HTTP (2026-09-23) | What it is |
|---|---|---|
| `…/HIF-org/HIF-standard/main/schemas/hif_schema.json` | 200 | the moving `latest` file under the current name |
| `…/pszufe/HIF-standard/main/schemas/hif_schema.json` (README snippets; this repository's `schemas/sample.hif.json`) | 200, same bytes | the same file via the rename/transfer redirect |
| `…/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json` (HyperNetX 2.4.3 `schema_url`) | 200 | the *other* file (`0.1.0`), under the oldest name |
| `…/pszufe/HIF_validators/main/schemas/schema.json` (the `$id` of `hif_schema.json`) | 404 | a path that existed for about 21 minutes on 2025-05-02 |

The 404 comes from a same-day rename. `58447e4` (12:52 −04:00) created `schemas/schema.json` with
that `$id`. `6ffdb48` (13:13, "rename to fix HNX error") renamed it to `hif_schema.json`.
`c8e2d4f` (13:16, "fix broken links") then corrected the `$id` of the *other* file only. So [04.1]
is not about four standards. It is one repository with two files that apply the same rules, and one
stale `$id`. The live risks are the moving `latest` URL (by design, §3.3), dependence on GitHub
redirects, and the lack of any version marker in data files.

## 5. Validation results [run]

Setup: Python 3.11.15, jsonschema 4.26.0 (Draft7Validator, chosen from `$schema`) and fastjsonschema
2.22.2, which is the validator in the upstream README and tests. Every file was validated against
seven snapshots (S0–S4 and both published files). The two validators agreed on every cell.
Calibration: under both published files, all 15 upstream `HIF-compliant` test files validated and
all 16 `HIF-non-compliant` files failed, as upstream intends. Upstream's test
`metadata_with_deeply_nested_attributes` never runs, because the function lacks the `test_` prefix
(`tests/test_compliant_files_against_schema.py`); our harness validates that file (valid). Full
matrix: [probes/hif-schema/results.md](probes/hif-schema/results.md).

"Published" below means both `hif_schema.json` and `hif_schema_v0.1.0.json`, which always agree.
Among these cases, S0 rejects every object-record file and accepts only `{"incidences": []}`, so
it is omitted from the notes.

| Case (`probes/hif-schema/cases/`) | Published | Differs in history | What the standard says, and notes |
|---|---|---|---|
| this repository's `schemas/sample.hif.json` | **valid** | — | roles in `incidences[].attrs.role`, conventions in `metadata.conventions` |
| 01 role in incidence `attrs` | **valid** | — | the paper's own example uses `attrs.role` |
| 02 same (edge, node) pair twice, roles `regulator`/tail and `target`/head | **valid** | — | the only way to write a node that is in both tail and head (p.4). The formal model treats I as a set, so the standard is ambiguous here (§3, inconsistency 2) |
| 03 node id equal to an edge id (`f1` used as a member of `f2`) | **valid** | — | no structural meaning, as far as the text goes. The paper keeps nodes and edges as distinct objects (p.4, a "disjoint union"); reading that as "ids live in separate spaces" is my inference. Upstream's own data reuses ids across the two: every one of the 148 node ids in `tutorials/data/email-enron.json` is also an edge id, and 327 of 327 in `contacts_high_school.hif.json`. Issue [#27](https://github.com/HIF-org/HIF-standard/issues/27) raised this and was closed 2025-01-24. Both files were last changed on 2025-01-13, before the issue, and still reuse ids |
| 04 top-level `"version"` | **invalid** ("Additional properties are not allowed ('version' was unexpected)") | valid in S1 | — |
| 05 top-level `"roles"` vocabulary block | **invalid** | valid in S1 | — |
| 06 top-level `"$schema"` | **invalid** | valid in S1 | the common JSON self-description key is unavailable in HIF |
| 07 `metadata.hif-version` + `metadata.hif-schema` | **valid** | — | metadata is unconstrained |
| 08 `metadata.khg-conventions` with a roles vocabulary | **valid** | — | allowed, although the paper encourages a flat, dash-case metadata object |
| 09 incidence `attrs` with a list-valued `role`, a namespaced key `khg:role`, a nested object and `null` | **valid** | — | `attrs` is unconstrained |
| 10 incidence `attrs` as a string | **invalid** | valid in S1, S2 (the key was then `attr`) | — |
| 11 record-level `"role"` on an incidence | **invalid** | valid in S1–S3 | record keys are closed |
| 12 `"direction": "treatment"` | **invalid** | — | `direction` accepts only head or tail |
| 13 record-level `"relation"` on an edge | **invalid** | valid in S1–S3 | — |
| 14 record-level `"type"` on a node | **invalid** | valid in S1–S3 | — |
| 15 integer ids throughout | **valid** | — | — |
| 16 mixed ids: node `1` and node `"1"`, edge `10` and edge `"10"` | **valid** | — | the schema cannot say whether these are the same entity. Upstream's `tutorials/data/diseasome.json` mixes int and str edge ids |
| 17 id `1.0` | **valid** | — | draft-07 treats `1.0` as an integer. In Python `1 == 1.0` and both hash alike, so a dict keyed by id merges them |
| 18 id `1.5` | **invalid** | — | mirrors upstream `bad_node_float.json` |
| 19 id `true` | **invalid** | — | — |
| 20 id `null` | **invalid** | — | — |
| 21 id `""` | **valid** | — | — |
| 22 id `9007199254740993` (2^53 + 1) | **valid** | — | outside the range RFC 8259 calls interoperable, [−(2^53)+1, (2^53)−1]; a float64 reader gets …992 |
| 23 `directed` network, no `direction` on any incidence | **valid** | — | §3.2 says direction is optional. Mirrors upstream `missing_direction.json` |
| 24 `undirected` network with `direction` values | **valid** | — | §3.2 |
| 25 no `network-type`, with `direction` values | **valid** | — | absent means undirected (p.7) |
| 26 `"network-type": "knowledge-hypergraph"` | **invalid** | — | there is no way to declare a knowledge hypergraph |
| 27 edge in `edges` with no incidences | **valid** | — | README: "empty edges can be specified with entries in … "edges" which are not present in the incidences" |
| 28 incidence names a node missing from `nodes` | **valid** | — | the schema checks no references. Upstream's `metadata_with_deeply_nested_attributes.json` does the same |
| 29 incidence names an edge missing from `edges` | **valid** | — | same. In upstream's `diseasome.json`, 500 distinct edge ids used in incidences are not declared in `edges` |
| 30 `weight` on node, edge and incidence records | **valid** | — | the README omits it; the schema and Table 1 allow it |
| 31 `{}` | **invalid** ("'incidences' is a required property") | — | — |
| 32 `{"incidences": []}` | **valid** | — | the smallest valid HIF file |
| 33 `metadata["$schema"]` | **valid** | — | a self-description pointer can live in metadata |
| 34 zero-byte file | **not JSON** (parse error before validation) | — | — |
| 35 `NaN` literal in `weight` and `attrs` | **valid** for Python validators; not strict JSON | — | RFC 8259: "Infinity and NaN … are not permitted". Python's `json` accepts NaN, so a schema check alone passes it. See upstream issue [#10](https://github.com/HIF-org/HIF-standard/issues/10) on NaNs |
| 36 duplicate `"role"` key inside one `attrs` | **valid** for Python validators; not interoperable | — | RFC 8259: "the behavior of software that receives such an object is unpredictable". Python keeps the last value |

## 6. How a role convention can travel without breaking validation today

Facts established above:

1. **The carrier must be `attrs`.** A record-level `role` fails validation (case 11). `direction`
   cannot hold a role (case 12). `incidences[].attrs.role` validates as a string, a list or
   alongside namespaced keys (cases 01, 02, 09).
2. **There is precedent for exactly this key.** The paper's example is `{"role": "PI"}` (p.7). The
   upstream compliant test `tests/test_files/HIF-compliant/single_incidence_with_attrs.json`
   contains `{"edge": "abcd", "node": 42, "attrs": {"role": "PI", "age": 42}}`. It was added in
   `6fe88e9` (2024-10-03) and is at HEAD.
3. **There is precedent for extensions in attrs.** ASH writes temporal presence as `attrs._presence`
   on node and edge records and declares nothing at file level (`ash_model/readwrite/io.py` at
   `21124454`, 2025-11-20, lines 331 and 340). Its reader raises `NotImplementedError` unless
   `network-type` is `"undirected"` (line 357–358). Issue
   [#44](https://github.com/HIF-org/HIF-standard/issues/44) (2025-09-22) proposes taking this into
   the schema: "custom attributes are used to describe temporal presence and time‐varying
   attributes as intervals". Upstream's own `contacts_high_school.hif.json` carries a per-incidence
   `attrs.time`.
4. **Multi-role participation has two valid encodings.** One is repeated incidence records for the
   same pair (case 02). The other is a list-valued `role` in a single record (case 09). Only the
   first can also express a node that is in both tail and head.
5. **A role and `direction` can coexist on one record** (cases 01 and 02). `direction` is the only
   structural per-incidence field HIF defines.
6. **The file will pass HyperNetX's gate.** HyperNetX's `from_hif` accepts cases 01 and 08
   (returns a `Hypergraph`) and returns `None` for cases 04 and 11 ([run], §7). Whether XGI and
   HyperNetX *keep* `attrs.role`, `direction` and repeated pairs is the loader report's question.

## 7. Where a vocabulary, convention or version declaration can legally live

| Location | Valid under the published schema? | Read by any library today? | Notes |
|---|---|---|---|
| new top-level key (`version`, `roles`, `hif-version`, `$schema`) | **no** (cases 04–06) | — | HyperNetX 2.4.3 `from_hif` returns `None` on such a file [run] |
| `metadata.<key>` (flat or nested) | **yes** (cases 07, 08, 33) | no library reads our keys. HyperNetX writes and reads its own `metadata.default_attrs` (`hypernetx/hif.py` lines 94–96, 163) | the paper encourages "a flat object" with dash-case keys (p.7). Several upstream tutorial files carry a nested `default_attrs` |
| `edges[].attrs`, `nodes[].attrs`, `incidences[].attrs` | **yes** | libraries treat them as opaque attributes | per-record: relation type on the edge, role on the incidence, entity type on the node |
| an external document referenced from `metadata` by URL | **yes** | — | the only way to point at a versioned vocabulary or schema without inlining it |
| the schema file's own `version` | — | — | describes the schema document, not the data file |

Two practical constraints:

- HyperNetX 2.4.3 cannot add caller metadata. `to_hif(hg, metadata=<dict>)` returns `None`,
  because line 94 does `metadata = metadata.update(...)`, and it mutates the caller's dict
  [run]. With a named hypergraph, line 98 should raise `TypeError` instead; that path comes from
  reading the source, not from a run. An exporter that wants a declaration block must write it
  after the library call, or write HIF itself.
- HyperNetX fetches the schema over the network on every `to_hif` and `from_hif` call (lines 63 and
  136), from the oldest repository name. That URL works today only through GitHub's redirect, so
  anything that runs HyperNetX's loader needs network access and a live redirect.

## 8. Upstream process, maintainers and activity

**Process as documented.** There are no contribution guidelines. The only written process is the
paper's §3.3 versioning steps, which the maintainers carry out. The README asks outsiders to open
an issue to have a project listed.

**Process as practised [git, web].**

- Early schema changes were committed straight to `main`: S1 on 2024-08-13 (Praggastis) and S2 on
  2024-08-21 (Coll, `53a8a93` is on the first-parent line of `main`).
- From September 2024, schema changes arrived through PRs reviewed by another core author: #16
  (attr→attrs), #18 (record-level `additionalProperties:false`, merged by FraLotito) and #34
  (version split, merged by nwlandry).
- Decisions go through meetings. On PR #21, Landry wrote: "Based on the past group meetings, this
  schema is not what we decided upon. … I think we should all discuss at our meeting on Monday to
  see if this makes sense for the whole group."
- Planning for v2 happens in a meeting-notes issue (#51) and a survey thread (#55). The #51 notes
  also say "The group now has a [HIF Discord server](https://discord.gg/CAZwX5cXYc)" and that a
  second meeting would come "not before next year". Whether it took place is [unverified].
- One external code PR, [#14](https://github.com/HIF-org/HIF-standard/pull/14) (Cobord, 2024),
  was closed. The maintainer asked for it to be split into smaller pieces and wrote: "the repo is
  only set up around the schema and unit tests will solely focus on that (not integration tests
  with other libraries, for example)."

**Maintainers as listed on GitHub.**

- `HIF-org` shows no public members, and the repository has no CODEOWNERS.
- The README "Contributors" section names the eight paper authors.
- The two merges in the last 12 months that I could attribute were done by `colltoaction` (Coll,
  #53) and `nwlandry` (Landry, #57). Earlier merge commits were made by Szufel (#3, #9), Coll (#13)
  and Lotito (#18). Releases were published by `pszufe`
  (v0.1.0) and `nwlandry` (v0.1.1, v0.1.2).
- Commits, all time and excluding merges: Landry 53 (49 + 4 under "nwlandry"), Coll 24, Praggastis
  22, Szufel 14 (12 + 1 + 1 under spelling variants), Lotito 11, Myers 4, Pickard 2, external 2.

**Activity (checked 2026-09-23).**

| Measure | Value |
|---|---|
| last commit | `b691a3d`, 2026-03-19 (188 days before this check) |
| commits in the last 12 months / 6 months | 16 / 0 |
| last change to a schema file / to validation rules | 2025-05-02 (509 days) / 2024-10-03 (720 days) |
| issues | 25 in total: 7 open (#44, #49, #51, #52, #55, #56, #58) and 18 closed |
| PRs | 33 in total, none open: 30 merged and 3 closed unmerged (#14, #21, #50) |
| issue authors | all 25 issues were opened by five core accounts (nwlandry, pszufe, brendapraggastis, colltoaction, FraLotito). No outsider has ever filed an issue |
| newest issue | #58, 2026-07-25, "Add participating packages to the homepage" (nwlandry) |

Response times:

- External PRs got a first maintainer reply the same day or the next: #50 was opened 2025-11-05
  and answered 2025-11-05. #53 was opened 2025-12-08, answered 2025-12-09, and merged 2026-02-02
  after waiting for an EasyGraph release. #57 was opened 2026-03-18 and merged 2026-03-19. #14 was
  opened 2024-08-27 and answered 2024-08-30.
- Response times on issues could not be measured, because comments were unreadable (section 1)
  [unverified]. Search snippets show that at least #27 and #49 have replies. The seven open issues
  are all maintainer-authored trackers and planning threads.

**v2.** Issue #51's goals were "JSON Schema v2 with support for temporal networks", a "Columnar
format compatible with JSON (#52)" and "Exploration of multilayer networks". One participant
suggested "encoding multilayer as attributes". Issue #55 says v2 "will focus on supporting Temporal
Hypergraphs and providing a performant Columnar Format". I found no v2 schema draft. `main` is the
only branch upstream. The branch names of eight forks and remotes (listed via `git ls-remote`)
contain nothing v2-, role- or version-related. The one `dev` branch, in brendapraggastis's fork,
carries the same strict schema.

## 9. Has anyone proposed roles or versioning upstream?

**Roles: no.**

- GitHub search for `role` in this repository's issues matches only
  [#27](https://github.com/HIF-org/HIF-standard/issues/27) "Repeated edge and node ids". The match
  is in a comment (snippet: "If the hypergraph was directed to begin with you would probably need
  to add their _role_ in the hyperedge to the data."). The thread is about node/edge id collisions
  when converting to a NetworkX bipartite graph.
- `roles` in issues returns 0 results, and `role` in pull requests returns 0.
- The nearest structural precedent is PR [#21](https://github.com/HIF-org/HIF-standard/pull/21),
  which was closed unmerged. It would have allowed scalar record-level properties. Its argument
  included "we already are getting requests to place edge specific orderings on incidences. It
  would be a convenience to have a property `index` on every incidence without having to place it
  in attrs." Landry's objection gives the design rule the group follows: "separate structural
  information (node, edge, weight, direction) from metadata (name, timestamp, etc.) by putting
  metadata in `attrs`."
- The other attribute-based extension on the table is temporal presence
  ([#44](https://github.com/HIF-org/HIF-standard/issues/44)).

**Versioning of data files: no.**

- Schema versioning was settled by PR [#34](https://github.com/HIF-org/HIF-standard/pull/34),
  merged 2025-05-02. Its description reads: "This PR creates two fields from the title to specify
  the name and the version. In addition, the file has been renamed, so that by default, users will
  always pull from the most recent version." The paper's §3.3 describes the same scheme.
- Issue [#40](https://github.com/HIF-org/HIF-standard/issues/40) (2025-07-03) asked for the first
  Zenodo release, "corresponding to v0.1.0".
- Nothing proposes a version marker inside HIF files. `semver` in issues returns 0 results. The
  `version` matches in issues are unrelated (#46 on nx_hif, and #49's "Our private version is
  columnar and built on top of Apache Arrow").

A P2 proposal would therefore be the first on both topics. It would also be the first issue filed
by anyone outside the author group.

## 10. Answer to [04.1], and corrections for the knowledge base

**[04.1] "What happens on the first breaking revision, and which document is normative?"**

- The paper defines the release process (§3.3): a new `hif_schema_<version>.json`, a CHANGELOG
  section and a Zenodo upload. `hif_schema.json` stays `latest`, so every tool that fetches it
  switches silently on a breaking release. That includes the README's Python, R and Julia snippets.
- A breaking revision is now planned (v2, temporal and columnar). Data files carry no version
  marker.
- The v1 schema's closed records mean any v2 file that adds record-level or top-level fields will
  fail v1 validators. That is accidental version detection. v1 files will stay valid under v2 only
  if v2 keeps every v1 field.
- On which document is normative: the paper (Table 1 and §3) and the schema agree; the README
  lags on `weight`. The most immutable reference to the current rules is the Zenodo v0.1.2 archive
  (DOI 10.5281/zenodo.17257719), which the paper calls "the stable schema", or a commit-pinned raw
  URL.

**Corrections for [kb/04-storage-and-formats/hif-hypergraph-interchange-format.md](../../../kb/04-storage-and-formats/hif-hypergraph-interchange-format.md)
and [kb/09-ecosystem/standards-bodies-and-specifications.md](../../../kb/09-ecosystem/standards-bodies-and-specifications.md) §4.**
This report does not edit them; these are for the orchestrator.

1. `pszufe/HIF_validators` is not "a separate validators repository". It is the original name of
   the same repository. `HIF-org/HIF-standard` is the canonical home, not a "mirror organisation
   repository"; the `pszufe` URLs are redirects.
2. §4 "Versions" is incomplete. There is also `hif_schema_v0.1.0.json` with `"version": "0.1.0"`.
   The CHANGELOG said `v0.1.0` until PR #34 changed it to `v0.0`. There are three releases
   (v0.1.0–v0.1.2) on Zenodo, and maintainers call the current state "v1" and are planning "v2".
   "No breaking revision since publication" is true: the validation rules have been unchanged since
   2024-10-03. But the same versioned file name carried four different rule sets in 2024.
3. The affiliation list omits Coll's University of Buenos Aires affiliation. Pickard is listed by
   the paper under both the Broad Institute and the University of Michigan.
4. The `$id` 404 has a precise cause (section 4.4) and is not a fourth standard.
5. `schemas/sample.hif.json` records `metadata.schema` as the moving `…/main/schemas/hif_schema.json`.
   A pinned URL would make the file reproducible.

## 11. Recommendations for the P2 design (opinion)

These follow from the facts above but are my judgement, not established results.

1. **Target and vendor the schema.** Target `hif_schema_v0.1.0.json`, blob `e2105bb`, sha256
   `639466b7…`, which is the same bytes as in the Zenodo v0.1.2 archive. Vendor it in the package
   and validate offline. Never fetch `latest` at run time.
2. **Validate in two layers.**
   - (a) The HIF schema unchanged.
   - (b) A KHG profile schema that `allOf`-includes the HIF schema and constrains only the contents
     of `attrs` and `metadata`. That guarantees profile-valid implies HIF-valid.
   - (c) Procedural checks for what JSON Schema cannot express: references resolve, no duplicate
     node or edge declarations, duplicate (edge, node) pairs only when their roles differ,
     `direction` consistent with the relation's role schema, strict JSON (no NaN, no duplicate
     keys), and the id policy.
   The malformed-case list for the P2 gate can start from cases 04–06, 10–14, 16–22, 28–29 and
   34–36.
3. **Role key.** Use a bare `role` in `incidences[].attrs`. It matches the paper's example and the
   upstream test, which gives the best chance of upstream adoption. Declare in `metadata` that
   `role` follows a named vocabulary, so a reader can tell it from someone else's "PI".
4. **Multi-role encoding.** Prefer one incidence record per (edge, node, role), allowing repeated
   pairs, over list-valued roles. It is the only encoding that can also place a node in both tail
   and head. Make this conditional on the loader probes showing that XGI and HyperNetX keep
   repeated pairs. If they collapse them, fall back to a list-valued `role`.
5. **Declarations.** Use flat dash-case `metadata` keys: `hif-schema` (pinned URL),
   `hif-schema-sha256`, a profile identifier with a semver (`khg-profile`), and a relation-type
   schema id. Put the vocabulary inline under one nested key, or reference it by URL. Never use top
   level. Write the block after any library export call, because HyperNetX's `to_hif(metadata=…)`
   is broken.
6. **Identifiers.** In the profile, allow string ids only, with a pattern. Loaders should still
   accept integer ids from foreign files and canonicalise them. This removes the `1` / `"1"` /
   `1.0` / 2^53 hazards (cases 16, 17 and 22).
7. **Facts about facts.** Refer to an edge explicitly from `attrs` (a reserved key). Never infer
   nesting from id equality. HIF gives equal node and edge ids no structural meaning (section 3 and
   case 03), and upstream data reuses ids across nodes and edges as a matter of course.
8. **Upstream route.**
   - Open an issue first, not a PR. Frame it as a v1-compatible convention: `attrs.role`, a
     metadata declaration and compliant test fixtures, with no schema change.
   - Cite the paper's `{"role": "PI"}` example, #44 (the attribute-first extension precedent), #21
     (the "structural vs attrs" rule) and #55/#51 (v2 planning).
   - Offer the v2 asks separately: a structural `role` field that generalises `direction`, and a
     data-file version marker.
   - Follow up with a PR limited to README text and test fixtures, because the core team has
     accepted such PRs quickly.
   - Do not make the P2 gate depend on upstream acceptance. The repository has had no commits in
     six months.

## Sources

- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. (2025). *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21. Cambridge University Press. https://doi.org/10.1017/nws.2025.10018 (Crossref metadata read 2026-09-23 via https://api.crossref.org/works/10.1017/nws.2025.10018)
- Same authors. *HIF: The hypergraph interchange format for higher-order networks.* arXiv:2507.11520, v1 2025-07-15, v2 2026-01-30. https://arxiv.org/abs/2507.11520 (PDFs of v1 and v2 read 2026-09-23; page numbers refer to v2)
- HIF development team. HIF-standard repository, HEAD `b691a3d2ec32100c0229ebe1151e9afad015c356` (2026-03-19): `README.md`, `LICENSE`, `CITATION.cff`, `schemas/hif_schema.json`, `schemas/hif_schema_v0.1.0.json`, `schemas/CHANGELOG.md`, `tests/`, `tutorials/data/`, full history of 139 commits. https://github.com/HIF-org/HIF-standard (cloned 2026-09-23; the same repository is reachable as https://github.com/pszufe/HIF-standard and https://github.com/pszufe/HIF_validators)
- Historical schema snapshots at commits `c58b153` (2024-08-05), `e5c868b` (2024-08-13), `53a8a93` (2024-08-21), `7aefda6` (2024-09-26), `de5f89f` (2024-10-03), `58447e4`, `6ffdb48`, `c8e2d4f` (2025-05-02), same repository. Vendored with hashes in [probes/hif-schema/](probes/hif-schema/)
- HIF-org organisation profile repository: first commit `384e4c3` (2026-01-09), `main` at `7f9c77b` (2026-01-09), plus branch `readme` at `2bd9118` (2026-01-14). https://github.com/HIF-org/.github
- HIF-standard issues [#1](https://github.com/HIF-org/HIF-standard/issues/1), [#2](https://github.com/HIF-org/HIF-standard/issues/2), [#4](https://github.com/HIF-org/HIF-standard/issues/4), [#5](https://github.com/HIF-org/HIF-standard/issues/5), [#6](https://github.com/HIF-org/HIF-standard/issues/6), [#7](https://github.com/HIF-org/HIF-standard/issues/7), [#10](https://github.com/HIF-org/HIF-standard/issues/10), [#12](https://github.com/HIF-org/HIF-standard/issues/12), [#15](https://github.com/HIF-org/HIF-standard/issues/15), [#22](https://github.com/HIF-org/HIF-standard/issues/22), [#25](https://github.com/HIF-org/HIF-standard/issues/25), [#27](https://github.com/HIF-org/HIF-standard/issues/27), [#39](https://github.com/HIF-org/HIF-standard/issues/39), [#40](https://github.com/HIF-org/HIF-standard/issues/40), [#44](https://github.com/HIF-org/HIF-standard/issues/44), [#49](https://github.com/HIF-org/HIF-standard/issues/49), [#51](https://github.com/HIF-org/HIF-standard/issues/51), [#52](https://github.com/HIF-org/HIF-standard/issues/52), [#55](https://github.com/HIF-org/HIF-standard/issues/55), [#56](https://github.com/HIF-org/HIF-standard/issues/56), [#58](https://github.com/HIF-org/HIF-standard/issues/58); issue list pages and GitHub search. Read via WebFetch 2026-09-23; opening posts only
- HIF-standard pull requests [#3](https://github.com/HIF-org/HIF-standard/pull/3), [#14](https://github.com/HIF-org/HIF-standard/pull/14), [#16](https://github.com/HIF-org/HIF-standard/pull/16), [#18](https://github.com/HIF-org/HIF-standard/pull/18), [#21](https://github.com/HIF-org/HIF-standard/pull/21), [#28](https://github.com/HIF-org/HIF-standard/pull/28), [#34](https://github.com/HIF-org/HIF-standard/pull/34), [#50](https://github.com/HIF-org/HIF-standard/pull/50), [#53](https://github.com/HIF-org/HIF-standard/pull/53), [#57](https://github.com/HIF-org/HIF-standard/pull/57); PR list pages. Read via WebFetch 2026-09-23, conversations included; heads of #14, #21 and #34 fetched with git
- Zenodo records for HIF, concept DOI 10.5281/zenodo.15802759; versions 15802760 (v0.1.0), 17251025 (v0.1.1), 17257719 (v0.1.2); archive `pszufe/HIF-standard-v0.1.2.zip`. https://doi.org/10.5281/zenodo.15802759 (Zenodo API read 2026-09-23)
- GitHub Docs. *Renaming a repository* and *Transferring a repository*. https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository ; https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository (read 2026-09-23)
- JSON Schema draft-07: core (unknown keywords) and validation (§6.1.1 `type`, §6.5.6 `additionalProperties`). https://json-schema.org/draft-07/json-schema-core.html ; https://json-schema.org/draft-07/json-schema-validation.html ; draft 2019-09 release notes (`unevaluatedProperties`), https://json-schema.org/draft/2019-09/release-notes (read 2026-09-23)
- Bray, T. (ed.) (2017). RFC 8259, *The JavaScript Object Notation (JSON) Data Interchange Format*. IETF. https://www.rfc-editor.org/rfc/rfc8259
- HyperNetX 2.4.3 (PyPI, uploaded 2026-07-23), `hypernetx/hif.py`. https://pypi.org/project/hypernetx/2.4.3/ ; https://github.com/pnnl/HyperNetX (wheel sha256 `0304e569…`; executed 2026-09-23)
- XGI 0.10.2 (PyPI, uploaded 2026-05-15), `xgi/convert/hif_dict.py`, `xgi/readwrite/hif.py`. https://pypi.org/project/xgi/0.10.2/ (source grep only)
- HypergraphX 1.8.0 (PyPI, uploaded 2026-05-18), `hypergraphx/readwrite/hif.py`. https://pypi.org/project/hypergraphx/1.8.0/ (source grep only)
- Rossetti, G. et al. ASH (Attributed Stream Hypergraphs) repository, `ash_model/readwrite/io.py` at `21124454edbe16e65e17ad35018fce87a4131699` (2025-11-20), and issue #1. https://github.com/GiulioRossetti/ASH ; https://github.com/GiulioRossetti/ASH/issues/1
- jsonschema 4.26.0 and fastjsonschema 2.22.2 (PyPI), used as validators, 2026-09-23. https://pypi.org/project/jsonschema/ ; https://pypi.org/project/fastjsonschema/
