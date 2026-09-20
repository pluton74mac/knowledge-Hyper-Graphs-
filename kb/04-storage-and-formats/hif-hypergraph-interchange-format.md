---
title: HIF — the Hypergraph Interchange Format
type: tool
status: draft
tags: [hif, interchange, json-schema, xgi, hypernetx, hypergraphx, simplehypergraphs, standard]
created: 2026-09-20
updated: 2026-09-20
---

# HIF — the Hypergraph Interchange Format

HIF is the only cross-library file format for higher-order networks that has both a published
schema and more than one independent implementation. For this knowledge base it is the default
*interchange* format; it is not, on its own, a knowledge representation (section 6 explains why).

All statements checked 2026-09-20 against the repository at
[github.com/pszufe/HIF-standard](https://github.com/pszufe/HIF-standard) (mirrored at
[github.com/HIF-org/HIF-standard](https://github.com/HIF-org/HIF-standard); the two READMEs were
byte-identical when compared on 2026-09-20).

## 1. What it is and where it came from

"The Hypergraph Interchange Format (HIF) is a standard for higher-order network data to facilitate
seamless data exchange between higher-order network libraries"
([HIF-standard README](https://github.com/pszufe/HIF-standard)).

It was produced by authors of five libraries working together and published as
[Coll, Joslyn, Landry, Lotito, Myers, Pickard, Praggastis and Szufel (2025), "HIF: The hypergraph
interchange format for higher-order networks", *Network Science* 13, e21](https://doi.org/10.1017/nws.2025.10018).
The repository also carries a Zenodo DOI, [10.5281/zenodo.15802759](https://doi.org/10.5281/zenodo.15802759).
The affiliations are worth noting because they explain the design: PNNL (HyperNetX), University of
Virginia and the XGI team, University of Trento (HypergraphX), University of Michigan (HAT), and
SGH Warsaw (SimpleHypergraphs.jl). Funding for Szufel's contribution came from the Polish National
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
incidence* — the (node, edge) pair — which is exactly where a role label belongs.

## 3. The JSON Schema

The schema is JSON Schema **draft-07**, `$id`
`https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/schema.json`, `"title":
"Hypergraph Interchange Format"`, `"version": "latest"`. Summarised:

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

Two consequences of `additionalProperties: false` everywhere:

1. **You cannot invent top-level keys.** Anything extra goes inside `metadata`.
2. **You cannot invent record keys.** All application semantics — roles, provenance, types, time —
   must go inside an `attrs` object. HIF deliberately puts no schema on `attrs`.

Note the mismatch worth flagging: the README documents `weight` on node and edge records, and the
schema allows it there; but the README's prose for `nodes` and `edges` lists only `node`/`edge` and
`attrs`. The schema is the normative artefact and it allows `weight` on all three record kinds.

## 4. Versions

The schema `CHANGELOG.md` in the repository contains exactly one entry, "**v0.0** — Initial schema
for the Hypergraph Interchange Format (HIF) standard", and the schema itself carries
`"version": "latest"` rather than a number
([schemas/CHANGELOG.md](https://github.com/pszufe/HIF-standard/blob/main/schemas/CHANGELOG.md),
checked 2026-09-20). In other words: **there has been no breaking revision since publication**, and
the standard has no version-negotiation mechanism. A file cannot declare which HIF version it
targets. If the standard ever revises, existing files will be ambiguous. This is the format's
largest structural weakness and is recorded as an open question below.

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

## 6. Validation

The README gives validators in three languages. The Python one:

```python
import fastjsonschema, json, requests
url = "https://raw.githubusercontent.com/pszufe/HIF-standard/main/schemas/hif_schema.json"
validator = fastjsonschema.compile(requests.get(url).json())
validator(json.load(open(filename)))
```

R uses `jsonvalidate::json_validator`, Julia uses `JSONSchema.Schema` + `JSONSchema.validate`. The
repository also has a `tests/` folder of "compliant and non-compliant datasets", and a separate
validators repository, `pszufe/HIF_validators` (the schema's `$id` points there).

Because the schema is plain draft-07, any conforming validator works; this KB used Python
`jsonschema` 4.26.0 rather than `fastjsonschema` and got the same result.

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

1. **No role vocabulary.** Roles are conventions inside `attrs`. Two HIF files from two producers
   will not agree on the key name, let alone the role names.
2. **No nesting.** An edge cannot be a member of an edge. You can point at an edge ID from an
   `attrs` field, but no reader will interpret that as structure. Compare RDF 1.2 triple terms
   ([rdf-star-and-semantic-web-serialisations.md](rdf-star-and-semantic-web-serialisations.md)) and
   HypergraphDB ([hypergraph-databases.md](hypergraph-databases.md)).
3. **No identifiers with global meaning.** `node` is a string; nothing says it is an IRI. Entity
   resolution is out of scope — see
   [../03-construction/entity-resolution-and-canonicalisation.md](../03-construction/entity-resolution-and-canonicalisation.md).
4. **No typing or schema.** There is no way to say "every `treats` edge must have exactly one
   `condition` incidence". TypeDB's role-typed relations do this; HIF does not.
5. **No streaming.** It is a single JSON document; a reader must hold it all. For billions of
   incidences you want Parquet or a database, see
   [relational-and-eav-storage.md](relational-and-eav-storage.md).
6. **One version, no version field.** See section 4.

None of these is an argument against HIF. They are the reason HIF is the *interchange* layer and
something else is the *storage* layer.

## Sources

- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B. and Szufel, P. (2025). *HIF: The hypergraph interchange format for higher-order networks*. Network Science 13, e21. https://doi.org/10.1017/nws.2025.10018
- HIF-standard repository: README, `schemas/hif_schema.json`, `schemas/CHANGELOG.md` (checked 2026-09-20). https://github.com/pszufe/HIF-standard
- HIF-standard mirror organisation repository (checked 2026-09-20). https://github.com/HIF-org/HIF-standard
- HIF Zenodo record. https://doi.org/10.5281/zenodo.15802759
- HIF validators repository. https://github.com/pszufe/HIF_validators
- XGI repository: `xgi/convert/hif_dict.py`, `xgi/readwrite/json.py`, `xgi/convert/hypergraph_dict.py` (XGI 0.10.2, 2026-05-15). https://github.com/xgi-org/xgi
- xgi-data repository README (checked 2026-09-20). https://github.com/xgi-org/xgi-data
- HyperNetX repository, `hypernetx/__init__.py` (version string 2.4.3). https://github.com/pnnl/HyperNetX
- HypergraphX repository, `hypergraphx/readwrite/__init__.py` (HGX 1.8.0). https://github.com/HGX-Team/hypergraphx
- Hypergraph-DB repository README, persistence section (checked 2026-09-20). https://github.com/iMoonLab/Hypergraph-DB
- *A Blue Start: A large-scale pairwise and higher-order social network dataset*. https://arxiv.org/abs/2505.11608
- *Efficient Gillespie algorithms for spreading phenomena in large and heterogeneous higher-order networks*. https://arxiv.org/abs/2509.20174
