---
title: HIF — the Hypergraph Interchange Format
type: tool
status: draft
tags: [hif, interchange, json-schema, xgi, hypernetx, hypergraphx, simplehypergraphs, standard, roles, role-convention, versioning]
created: 2026-09-20
updated: 2026-09-24
---

# HIF — the Hypergraph Interchange Format

HIF is the only cross-library file format for higher-order networks that has both a published
schema and more than one independent implementation. For this knowledge base it is the default
*interchange* format; it is not, on its own, a knowledge representation (section 9 explains why,
and section 10 describes the role convention project P2 built on top of it).

First checked 2026-09-20 against the HIF repository. Re-checked 2026-09-23 by project P2 from a
full clone of the repository, the schema files, the paper, the Zenodo archives and the issue
tracker ([P2 report 02](../../projects/p2-role-aware-hif/research/02-hif-standard.md)). On
2026-09-24 sections 0, 1, 3, 4, 6 and 7 were corrected from that report and from P2's library
probes, sections 5 and 9 were extended, and section 10 was added.

## 0. One repository under three names

The canonical home is [github.com/HIF-org/HIF-standard](https://github.com/HIF-org/HIF-standard).
`pszufe/HIF_validators`, `pszufe/HIF-standard` and `HIF-org/HIF-standard` are **the same GitHub
repository**. It started as `pszufe/HIF_validators` (initial commit `b4e1b35`, 2024-07-17), was
renamed to `pszufe/HIF-standard` after issue
[#2](https://github.com/HIF-org/HIF-standard/issues/2) (2024-07-26), and was later transferred to
the `HIF-org` organisation, whose profile repository was first committed on 2026-01-09; the exact
transfer date is `[unverified]`. Cloning any of the three names gives the same 139 commits and the
same HEAD, `b691a3d` (2026-03-19)
([P2 report 02 §2.1](../../projects/p2-role-aware-hif/research/02-hif-standard.md)).

The older names work only through GitHub's redirects, yet the repository's own files still use
them: the README's validation snippets, `CITATION.cff`, both schema `$id`s and the Zenodo related
identifiers. GitHub documents that such redirects stop if a repository is later created at the old
name ([GitHub Docs, renaming a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository);
[transferring a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository)).
Several tools still fetch the schema from the `pszufe` paths (section 7, and
[../09-ecosystem/standards-bodies-and-specifications.md](../09-ecosystem/standards-bodies-and-specifications.md) §4).

## 1. What it is and where it came from

"The Hypergraph Interchange Format (HIF) is a standard for higher-order network data to facilitate
seamless data exchange between higher-order network libraries"
([HIF-standard README](https://github.com/HIF-org/HIF-standard)).

It was produced by authors of five libraries working together and published as
[Coll, Joslyn, Landry, Lotito, Myers, Pickard, Praggastis and Szufel (2025), "HIF: The hypergraph
interchange format for higher-order networks", *Network Science* 13, e21](https://doi.org/10.1017/nws.2025.10018),
online 2025-12-11 under CC BY 4.0 (Crossref metadata); preprint
[arXiv:2507.11520](https://arxiv.org/abs/2507.11520) (v1 2025-07-15, v2 2026-01-30). The
repository's releases are archived on Zenodo under the concept DOI
[10.5281/zenodo.15802759](https://doi.org/10.5281/zenodo.15802759) (section 4).

The affiliations explain the design. Per Crossref, checked 2026-09-24: Coll, University of Buenos
Aires; Joslyn, PNNL and Binghamton University; Landry (corresponding author), University of
Virginia and University of Vermont; Lotito, University of Trento and Central European University;
Myers and Praggastis, PNNL; Pickard, Broad Institute of MIT and Harvard (the arXiv v2 PDF also
lists the University of Michigan); Szufel, SGH Warsaw School of Economics. The libraries behind
them include HyperNetX (PNNL), XGI (Landry), HypergraphX (Lotito), HAT (Pickard) and
SimpleHypergraphs.jl (Szufel). Funding for Szufel's contribution came from the Polish National
Science Centre, grant 2021/41/B/HS4/03349.

## 2. The structure

Five top-level keys, one of them required:

| Key | Required | Values |
|---|---|---|
| `network-type` | no | `"undirected"`, `"directed"`, `"asc"` (abstract simplicial complex) |
| `metadata` | no | any JSON object — network-level attributes |
| `incidences` | **yes** | array of incidence records |
| `nodes` | no | array of node records |
| `edges` | no | array of edge records |

An **incidence** record requires `node` and `edge` (each a string or integer) and may carry
`weight` (number), `direction` (`"head"` or `"tail"`) and `attrs` (object). A **node** record
requires `node` and may carry `weight` and `attrs`. An **edge** record requires `edge` and may carry
`weight` and `attrs`.

The README states the rules that the schema alone does not make obvious:

- "All fields are optional except for `incidences`."
- "If a hypergraph is directed, the edge direction will be contained in the incidences record with
  keyword `direction`."
- "Isolated nodes and empty edges can be specified with entries in `nodes` and `edges` which are not
  present in the incidences."
- "This schema explicitly describes all items in the schema using JSON objects and typing. This is a
  verbose presentation making it faster to instantiate than list-based schemas requiring a parser."

That last point is the core design decision: HIF is **incidence-list-first**, not
hyperedge-list-first. A hyperedge is not a JSON array of member IDs; it is the set of incidence
records that share an `edge` value. This is what lets weights and attributes live *on the
incidence* — the (node, edge) pair — which is exactly where a role label belongs. The paper says so
itself: "Incidences can also have properties, which indicate hyperedge-dependent nodal attributes
… e.g., {"edge": 1, "node": 3, "attrs": {"role": "PI"}} might indicate node 3's role as a PI on
project 1" ([Coll et al., 2025](https://arxiv.org/abs/2507.11520), arXiv v2 p. 7, quoted in
[P2 report 02 §3](../../projects/p2-role-aware-hif/research/02-hif-standard.md)).

## 3. The JSON Schema

The repository holds **two schema files with identical validation rules**
([P2 report 02 §4.2](../../projects/p2-role-aware-hif/research/02-hif-standard.md), checked on
commit-pinned copies, sha256 recorded):

| File | `"version"` | `$id` | sha256 |
|---|---|---|---|
| `schemas/hif_schema.json` | `"latest"` | `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/schema.json` (**404**, see section 4) | `3f49e6cb…89c11b2e` |
| `schemas/hif_schema_v0.1.0.json` | `"0.1.0"` | `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json` (200 via redirect) | `639466b7…4c9b2196` |

The two differ only in `$id` and `version`, and their validation keywords have not changed since
commit `de5f89f` (2024-10-03). Both are JSON Schema **draft-07** with `"title": "Hypergraph
Interchange Format"`. Summarised:

```jsonc
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "network-type": { "enum": ["undirected", "directed", "asc"] },
    "metadata":     { "type": "object" },
    "incidences":   { "type": "array", "items": {
        "properties": {
          "edge":      { "type": ["string", "integer"] },
          "node":      { "type": ["string", "integer"] },
          "weight":    { "type": "number" },
          "direction": { "enum": ["head", "tail"] },
          "attrs":     { "type": "object" } },
        "required": ["edge", "node"],
        "additionalProperties": false, "unevaluatedProperties": false } },
    "nodes":        { "type": "array", "items": {
        "properties": { "node": {...}, "weight": {...}, "attrs": {...} },
        "required": ["node"], "additionalProperties": false } },
    "edges":        { "type": "array", "items": {
        "properties": { "edge": {...}, "weight": {...}, "attrs": {...} },
        "required": ["edge"], "additionalProperties": false } }
  },
  "required": ["incidences"],
  "additionalProperties": false, "unevaluatedProperties": false
}
```

`unevaluatedProperties` is a draft 2019-09 keyword, so a draft-07 validator relies on
`additionalProperties` alone ([JSON Schema 2019-09 release notes](https://json-schema.org/draft/2019-09/release-notes)).
Two consequences of `additionalProperties: false` everywhere:

1. **You cannot invent top-level keys.** Anything extra goes inside `metadata`. A top-level
   `version`, `roles` or `$schema` key fails validation.
2. **You cannot invent record keys.** All application semantics — roles, provenance, types, time —
   must go inside an `attrs` object. A record-level `role`, `relation` or `type` key fails. HIF
   deliberately puts no schema on `attrs`.

The schema also checks none of the following: uniqueness of node, edge or incidence records; that
incidences name declared nodes and edges; whether a node id may equal an edge id; or consistency
between `direction` and `network-type`. The paper leaves these to libraries, which "are
ultimately responsible for reading and writing datasets" (all four established by validating 36
edge-case files against every schema snapshot,
[P2 report 02 §5](../../projects/p2-role-aware-hif/research/02-hif-standard.md)).

Three mismatches between the documents, as facts:

- The README's prose for `nodes` and `edges` lists only `node`/`edge` and `attrs`. The schema and
  the paper's Table 1 also allow `weight`, and the schema is the normative artefact.
- The paper's formal model makes the incidence set I ⊆ V × E a *set*, yet says a node may be in both
  the tail and the head of a directed edge. Because `direction` is single-valued, the only
  schema-valid way to write that is two records for the same (edge, node) pair. Upstream's own
  compliant test `tests/test_files/HIF-compliant/duplicated_nodes_edges.json` repeats a pair, and
  its test says "Expect to pass unless uniqueness is enforced". Whether repeated pairs are part of
  the standard is therefore ambiguous; see section 10 and open question [04.6].
- The formal model requires V and E to be non-empty; the schema accepts `{"incidences": []}`.

## 4. Versions

The version labels in circulation contradict each other
([P2 report 02 §4.1](../../projects/p2-role-aware-hif/research/02-hif-standard.md); Zenodo versions
re-checked through the Zenodo API on 2026-09-24):

| Where | Label |
|---|---|
| `schemas/CHANGELOG.md` | `v0.0`, "Initial schema …", the only entry. It read `v0.1.0` until PR [#34](https://github.com/HIF-org/HIF-standard/pull/34) (2025-05-02) changed it; a reviewer on that PR noted that "`0.0` doesn't follow semver" |
| `schemas/hif_schema_v0.1.0.json` | `"version": "0.1.0"` |
| `schemas/hif_schema.json` | `"version": "latest"` |
| git tags and Zenodo | [v0.1.0](https://doi.org/10.5281/zenodo.15802760) (2025-07-04), [v0.1.1](https://doi.org/10.5281/zenodo.17251025) (2025-10-02), [v0.1.2](https://doi.org/10.5281/zenodo.17257719) (2025-10-03); both schema files are byte-identical at all three tags |
| `CITATION.cff` | `version: "0.1.0"` |
| maintainers, issue [#55](https://github.com/HIF-org/HIF-standard/issues/55) (2025-12-09) | "v1 released with support for Directed and Undirected Hypergraphs. HIF v2, in current development, will focus on supporting Temporal Hypergraphs and providing a performant Columnar Format" |

What this means:

- **No breaking revision since publication.** The validation rules have been unchanged since
  2024-10-03. Before that, the same file path `schemas/hif_schema_v0.1.0.json` carried four
  different rule sets between 2024-08-13 and 2024-10-03, including the breaking rename of `attr` to
  `attrs` and the closing of record keys.
- **A breaking revision is now planned.** Issue [#51](https://github.com/HIF-org/HIF-standard/issues/51)
  lists "JSON Schema v2 with support for temporal networks" and a columnar format among the goals.
  No v2 schema draft was found on 2026-09-23.
- **The release process moves `latest` silently.** The paper's §3.3 says each release copies the
  schema to `hif_schema_<version>.json`, adds a CHANGELOG section and uploads to Zenodo, while
  "The hif_schema.json schema will always have version "latest"". Every tool that fetches
  `hif_schema.json` at run time, including the README's Python, R and Julia snippets, will switch
  rules on a breaking release without notice.
- **Data files carry no version marker, and cannot at the top level.** `"version"` in a schema file
  is not a JSON Schema keyword and describes the schema document only. A top-level version key in a
  data file fails validation, so a declaration can live only in `metadata`. No upstream issue or
  pull request has proposed one, going by GitHub search (report §9).
- **The `$id` 404 is a slip, not a fourth standard.** Commit `58447e4` created
  `schemas/schema.json` with that `$id` at 12:52 on 2025-05-02; `6ffdb48` renamed the file to
  `hif_schema.json` at 13:13, and `c8e2d4f` corrected the `$id` of the *other* file only.
- **Which document is normative.** The paper (Table 1 and §3) and the schema agree; the README lags
  on `weight`. The most immutable reference to the current rules is the Zenodo v0.1.2 archive, which
  the paper calls "the stable schema", or a commit-pinned raw URL such as
  `https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json`.

Open question [04.1] was reframed on 2026-09-24 from these findings; see
[../00-index/open-questions.md](../00-index/open-questions.md).

## 5. Full worked example

The repository does not ship a canonical knowledge-hypergraph example, so this KB carries one:
[`schemas/sample.hif.json`](../../schemas/sample.hif.json). It encodes three n-ary biomedical facts
as directed hyperedges with role-labelled incidences. It was validated against the published schema
with `jsonschema` 4.26.0 (Draft-07 validator) on 2026-09-20: **0 errors**.

The shape, abbreviated:

```json
{
  "network-type": "directed",
  "metadata": { "title": "...", "schema": "https://raw.githubusercontent.com/pszufe/HIF-standard/main/schemas/hif_schema.json",
                "conventions": { "incidence.attrs.role": "the role the node plays in the fact" } },
  "nodes": [ {"node": "drug:metformin", "attrs": {"type": "Drug", "label": "metformin"}} ],
  "edges": [ {"edge": "f1", "weight": 0.95,
              "attrs": {"relation": "treats", "arity": 4, "source": "doc:guideline-2024",
                        "valid-from": "2024-01-01"}} ],
  "incidences": [
    {"edge": "f1", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "treatment"}},
    {"edge": "f1", "node": "disease:T2DM",   "direction": "head", "attrs": {"role": "condition"}},
    {"edge": "f1", "node": "dose:500mg-bid", "direction": "tail", "attrs": {"role": "dosage"}},
    {"edge": "f1", "node": "pop:adults",     "direction": "tail", "attrs": {"role": "population"}}
  ]
}
```

Reading it: the fact `f1` is one directed hyperedge of arity 4. The relation name lives in
`edge.attrs.relation`, the confidence in `edge.weight`, the provenance in `edge.attrs.source`, and
the per-participant role in `incidence.attrs.role`. Nothing in HIF enforces any of this — the file
documents its own conventions in `metadata.conventions`, which is the best a HIF producer can do.

Its `metadata.schema` points at the moving `latest` file through a redirect, so the file is not
reproducible against a fixed rule set. P2 left the file unchanged as its v0 fixture and migrated it
to [`schemas/sample.khg.hif.json`](../../schemas/sample.khg.hif.json), which follows the role
convention of section 10 and pins the schema by commit URL and sha256; the migration report is
[`schemas/sample.migration-report.json`](../../schemas/sample.migration-report.json).

## 6. Validation

The README gives validators in three languages. The Python one:

```python
import fastjsonschema, json, requests
url = "https://raw.githubusercontent.com/pszufe/HIF-standard/main/schemas/hif_schema.json"
validator = fastjsonschema.compile(requests.get(url).json())
validator(json.load(open(filename)))
```

R uses `jsonvalidate::json_validator`, Julia uses `JSONSchema.Schema` + `JSONSchema.validate`. The
repository also has a `tests/` folder of "compliant and non-compliant datasets": 15 compliant and 16
non-compliant files, which behave as upstream intends under both published schema files (P2 report
02 §5). There is no separate validators repository: `pszufe/HIF_validators` is the original name of
the same repository (section 0).

Because the schema is plain draft-07, any conforming validator works; this KB used Python
`jsonschema` 4.26.0 rather than `fastjsonschema` and got the same result, and P2's probes found the
two agreeing on every case. All three README snippets fetch the moving `latest` file at run time
(section 4). The safer practice, which P2 follows, is to vendor `hif_schema_v0.1.0.json`, check its
sha256 and validate offline.

## 7. Which libraries read and write it

| Library | Language | API | Version checked (2026-09-20) |
|---|---|---|---|
| **XGI** | Python | `xgi.write_hif` / `xgi.read_hif`; internals in `xgi/convert/hif_dict.py` (`to_hif_dict`, `from_hif_dict`). The older `write_json`/`read_json` is deprecated: its docstring says "This function is deprecated in favor of the `write_hif()` function" | 0.10.2 (released 2026-05-15) |
| **HyperNetX** | Python | `hypernetx.to_hif` / `from_hif`, exported at package top level from `hypernetx/hif.py` | 2.4.3 (2026-07-23) |
| **HypergraphX** | Python | `hypergraphx.readwrite.read_hif` / `write_hif` (in `hypergraphx/readwrite/hif.py`, re-exported from `readwrite/__init__.py`) | 1.8.0 (2026-05-18) |
| **HAT** (Hypergraph Analysis Toolbox) | Python | listed as a represented library in the HIF README | [unverified] — API not checked |
| **SimpleHypergraphs.jl** | Julia | listed as a represented library in the HIF README | [unverified] — no `src/io/hif.jl` found at the path probed |
| **Hypergraph-DB** | Python | `hg.save_as_hif("my_hypergraph.hif.json")` and `hg.load_from_hif(...)`, alongside its native `.hgdb` pickle | 0.3.0 (PyPI 2025-10-14) |

XGI's `to_hif_dict` shows how the `network-type` value is derived: `SimplicialComplex` -> `"asc"`,
`Hypergraph` -> `"undirected"`, `DiHypergraph` -> `"directed"`, with a `convert_nans` option that
rewrites float `NaN` attribute values to `null` because JSON has no NaN.

Hypergraph-DB is the interesting case for this KB: it is a *database* (see
[hypergraph-databases.md](hypergraph-databases.md)) that treats HIF as an import/export format
rather than its storage format, which is the pattern to copy.

**A HIF round-trip is not lossless across libraries.** Loading this KB's own
[`schemas/sample.hif.json`](../../schemas/sample.hif.json) into the three Python libraries on
2026-09-20: only **XGI 0.10.2** honours `"direction"` structurally (it returns a `DiHypergraph`).
HyperNetX 2.4.3 has no directed class: it returns an undirected `Hypergraph` and keeps `direction`
only as an opaque incidence column that no algorithm reads (corrected 2026-09-24; the earlier
reading said it dropped direction). Hypergraphx 1.8.0 reads into an undirected `Hypergraph` and
re-indexes node ids to integers, keeping the original HIF ids only in per-node metadata.

**Neither library's own HIF functions round-trip roles reliably** (P2 probes, 2026-09-23, 27 cases plus
the sample; [P2 report 03](../../projects/p2-role-aware-hif/research/03-library-probes.md)). XGI
0.10.2 drops every incidence `attrs`, and so every role, and every record-level `weight`.
HyperNetX 2.4.3 keeps roles as incidence ("cell") properties, but it silently drops the second
record of a repeated (edge, node) pair, drops metadata other than `name`, fetches the schema over
the network on every call, returns `None` instead of raising, and cannot re-read its own directed
output. Loaders that build the library objects through public constructors, and never call either
library's HIF functions, round-trip roles exactly (section 10). Detail and the per-feature table are
in [../09-ecosystem/software-libraries.md](../09-ecosystem/software-libraries.md) §1.

## 8. HIF in the wild

**xgi-data**, the reference dataset collection, has migrated: "All datasets are stored in
[Hypergraph Interchange Format (HIF)]" and are hosted on Zenodo in the XGI community
([xgi-data README](https://github.com/xgi-org/xgi-data), checked 2026-09-20). The listing there has
over fifty datasets — co-authorship (`coauth-dblp`, `coauth-mag-geology`), contact networks
(`contact-high-school`, `hospital-lyon`), legislative co-sponsorship (`congress-bills`,
`senate-committees`), tags and threads from Stack Exchange, drug data (`ndc-substances`, `dawn`),
plant–pollinator networks, and `hyperbard`. They load with `xgi.load_xgi_data("<name>")`.

The HIF README lists two projects using the format: *A Blue Start: A large-scale pairwise and
higher-order social network dataset* ([arXiv:2505.11608](https://arxiv.org/abs/2505.11608)) and
*Efficient Gillespie algorithms for spreading phenomena in large and heterogeneous higher-order
networks* ([arXiv:2509.20174](https://arxiv.org/abs/2509.20174)).

## 9. What HIF does not do

For a *knowledge* hypergraph, these are the gaps:

1. **No role vocabulary in the standard.** Roles are conventions inside `attrs`. Two HIF files from
   two producers will not agree on the key name, let alone the role names. Section 10 describes a
   convention that closes part of this gap without a schema change.
2. **No nesting.** An edge cannot be a member of an edge. You can point at an edge ID from an
   `attrs` field, but no reader will interpret that as structure. A node id equal to an edge id has
   no structural meaning either, and upstream's own tutorial data reuses ids across nodes and edges
   ([P2 report 02 §5](../../projects/p2-role-aware-hif/research/02-hif-standard.md), case 03).
   Compare RDF 1.2 triple terms
   ([rdf-star-and-semantic-web-serialisations.md](rdf-star-and-semantic-web-serialisations.md)) and
   HypergraphDB ([hypergraph-databases.md](hypergraph-databases.md)).
3. **No identifiers with global meaning.** `node` is a string or integer; nothing says it is an IRI.
   The schema accepts `1` and `"1"` as two ids and `1.0` as an integer. Entity resolution is out of
   scope — see
   [../03-construction/entity-resolution-and-canonicalisation.md](../03-construction/entity-resolution-and-canonicalisation.md).
4. **No typing or schema.** There is no way to say "every `treats` edge must have exactly one
   `condition` incidence". TypeDB's role-typed relations do this; HIF does not.
5. **No streaming.** It is a single JSON document; a reader must hold it all. For billions of
   incidences you want Parquet or a database, see
   [relational-and-eav-storage.md](relational-and-eav-storage.md). A columnar format is on the v2
   agenda (section 4).
6. **No version field in data files, and conflicting version labels.** See section 4.

None of these is an argument against HIF. They are the reason HIF is the *interchange* layer and
something else is the *storage* layer.

## 10. A role convention on incidence attributes (P2, 2026-09-24)

Project P2 ([projects/p2-role-aware-hif/](../../projects/p2-role-aware-hif/)) defined a role
convention that is valid HIF today, and a profile for this repository's own files. Its gate passed
on 2026-09-24. What follows is P2's design decision, with the reasons; the design is in
[DESIGN.md §4](../../projects/p2-role-aware-hif/DESIGN.md).

**`role-convention` 1.0.0**, four rules:

1. Every incidence of a role-carrying edge has `attrs.role`, one non-empty string. An edge is
   role-carrying when at least one of its incidences has `attrs.role`.
2. A node with k roles in one edge appears in **k incidence records**. The records of one
   (edge, node) pair may differ in `direction`, and must differ in `role` or in `role-position`.
   An exact repeat of (edge, node, role, role-position) is malformed.
3. `metadata["role-convention"] = "1.0.0"` declares the convention. `metadata["role-vocabulary"]`
   is optional and maps each role to `{label?, ...}`.
4. `attrs["role-position"]`, an integer ≥ 1, orders the fillers of one role (for example the
   stops of a route, where one airport can appear at two positions).

**Why `attrs.role`.** A record-level `role` fails validation and `direction` accepts only `head` or
`tail`, so `attrs` is the only carrier (section 3). The bare key `role` matches the paper's own
example, `{"role": "PI"}`, and upstream's compliant test `single_incidence_with_attrs.json`, which
holds `{"role": "PI", "age": 42}`.

**Why one incidence per role binding, with repeated pairs.** HIF gives each incidence one
`direction`, so a node that is both regulator (tail) and target (head) of one fact needs two
records; a list-valued `role` in one record cannot say that. The schema accepts repeated pairs, and
upstream's compliant `duplicated_nodes_edges.json` repeats one (section 3). The cost is that neither
library keeps two records for one pair natively: XGI edges are sets, and HyperNetX indexes cells by
(edge, node) and keeps the first. P2's loaders therefore keep the records themselves: in a context
object beside the XGI object, and, for HyperNetX, the first record in the cell with records 2..k
under a reserved cell key.

**Why a metadata declaration.** A reader has to be able to tell this `role` from someone else's
`"PI"`, and the only legal place for a file-level declaration is `metadata` (section 4). The
repository's own files add a profile, `khg-hif/1.0.0`, with flat dash-case `khg-*` keys for its
record bookkeeping, and pin the schema: `hif-schema` is the commit-pinned URL of
`hif_schema_v0.1.0.json` and `hif-schema-sha256` its digest. The profile never adds top-level or
record-level keys.

**What the gate showed** (P2 README and DESIGN §1.2). A 59-incidence fixture with three repeated
pairs, and its directed slice, run C1 record → HIF → XGI 0.10.2 → HIF → HyperNetX 2.4.3 → HIF → C1
with every intermediate HIF canonically identical and roles intact, identically under five
`PYTHONHASHSEED` settings, offline. The five convention fixtures prepared for upstream round-trip
exactly through both libraries. The libraries' own HIF functions, on the same files, keep 0 of 59
roles (XGI) or return `None` (HyperNetX)
([library evidence](../../tests/evidence/library-hif-evidence.json)).

**Upstream status.** An issue proposing the convention, with no schema change, and a follow-up PR
of five compliant fixtures are drafted in
[projects/p2-role-aware-hif/upstream/](../../projects/p2-role-aware-hif/upstream/) and **not yet
filed**; the repository owner files them. The issue asks one question upstream must settle: may
`incidences` repeat an (edge, node) pair (open question [04.6])? It also offers two v2 asks: a
record-level `role` field and a data-file version marker. No upstream issue or pull request
had proposed a role convention or a data-file version marker as of 2026-09-23, going by GitHub
search; not every issue comment thread could be read (P2 report 02 §1, §9).

## Sources

- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B. and Szufel, P. (2025). *HIF: The hypergraph interchange format for higher-order networks*. Network Science 13, e21. Cambridge University Press. https://doi.org/10.1017/nws.2025.10018 (Crossref metadata, affiliations and licence checked 2026-09-24: https://api.crossref.org/works/10.1017/nws.2025.10018)
- Same authors. *HIF: The hypergraph interchange format for higher-order networks*. arXiv:2507.11520, v1 2025-07-15, v2 2026-01-30. https://arxiv.org/abs/2507.11520
- HIF development team. HIF-standard repository, HEAD `b691a3d2ec32100c0229ebe1151e9afad015c356` (2026-03-19): README, `schemas/hif_schema.json`, `schemas/hif_schema_v0.1.0.json`, `schemas/CHANGELOG.md`, `CITATION.cff`, `tests/`. First checked 2026-09-20; cloned in full 2026-09-23. https://github.com/HIF-org/HIF-standard (the same repository is reachable, by redirect, as https://github.com/pszufe/HIF-standard and https://github.com/pszufe/HIF_validators)
- HIF-standard issues #2, #51 and #55, and pull request #34. https://github.com/HIF-org/HIF-standard/issues/2 ; https://github.com/HIF-org/HIF-standard/issues/51 ; https://github.com/HIF-org/HIF-standard/issues/55 ; https://github.com/HIF-org/HIF-standard/pull/34 (read 2026-09-23)
- HIF Zenodo records: concept DOI https://doi.org/10.5281/zenodo.15802759; v0.1.0 https://doi.org/10.5281/zenodo.15802760 (2025-07-04); v0.1.1 https://doi.org/10.5281/zenodo.17251025 (2025-10-02); v0.1.2 https://doi.org/10.5281/zenodo.17257719 (2025-10-03). Version list re-checked through the Zenodo API 2026-09-24
- GitHub Docs. *Renaming a repository*; *Transferring a repository*. https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository ; https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository (read 2026-09-23)
- JSON Schema draft 2019-09 release notes (`unevaluatedProperties`). https://json-schema.org/draft/2019-09/release-notes
- XGI repository: `xgi/convert/hif_dict.py`, `xgi/readwrite/json.py`, `xgi/convert/hypergraph_dict.py` (XGI 0.10.2, 2026-05-15). https://github.com/xgi-org/xgi
- xgi-data repository README (checked 2026-09-20). https://github.com/xgi-org/xgi-data
- HyperNetX repository, `hypernetx/__init__.py`, `hypernetx/hif.py` (version 2.4.3). https://github.com/pnnl/HyperNetX
- HypergraphX repository, `hypergraphx/readwrite/__init__.py` (HGX 1.8.0). https://github.com/HGX-Team/hypergraphx
- Hypergraph-DB repository README, persistence section (checked 2026-09-20). https://github.com/iMoonLab/Hypergraph-DB
- *A Blue Start: A large-scale pairwise and higher-order social network dataset*. https://arxiv.org/abs/2505.11608
- *Efficient Gillespie algorithms for spreading phenomena in large and heterogeneous higher-order networks*. https://arxiv.org/abs/2509.20174
- P2 research report 02, *What the HIF standard says today, from primary sources* (this repository, 2026-09-23), with its vendored schema snapshots and probe cases. [projects/p2-role-aware-hif/research/02-hif-standard.md](../../projects/p2-role-aware-hif/research/02-hif-standard.md)
- P2 research report 03, *XGI and HyperNetX HIF input and output, probed* (this repository, 2026-09-23). [projects/p2-role-aware-hif/research/03-library-probes.md](../../projects/p2-role-aware-hif/research/03-library-probes.md)
- P2 design, §1.2 (the gate), §4 (`role-convention` 1.0.0 and the `khg-hif/1.0.0` profile), §5 (loaders), §12.3 (the upstream proposal) (this repository, 2026-09-23/24). [projects/p2-role-aware-hif/DESIGN.md](../../projects/p2-role-aware-hif/DESIGN.md)
- P2 library evidence, `library-hif-evidence.json` (XGI 0.10.2 and HyperNetX 2.4.3 own HIF functions on four role-carrying files; this repository). [tests/evidence/library-hif-evidence.json](../../tests/evidence/library-hif-evidence.json)
