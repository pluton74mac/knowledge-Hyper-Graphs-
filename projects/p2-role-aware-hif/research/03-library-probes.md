---
title: XGI and HyperNetX HIF input and output, probed - do role-labelled incidences survive?
type: survey
status: draft
tags: [p2, hif, xgi, hypernetx, roles, incidences, loaders, round-trip, probes]
created: 2026-09-23
updated: 2026-09-23
---

# XGI and HyperNetX HIF input and output, probed (P2 research report 03)

**Question.** How do XGI and HyperNetX (HNX) read and write the Hypergraph Interchange Format (HIF), and
do role-labelled incidences (`incidences[].attrs.role`) survive a round trip? What must P2's
role-preserving loaders do beyond calling each library's own HIF reader, and what cannot be done without
changes upstream?

**Short answer.**

- **XGI 0.10.2 drops every incidence `attrs`, so it drops every role.** None of the role strings is stored
  anywhere in the loaded object (0/8 found in its whole state; 0/9 role records written back for the
  KB sample). It also drops every record-level `weight`. It keeps direction (as `DiHypergraph` tail and
  head sets), node, edge and network attributes, and id types.
- **HNX 2.4.3 keeps roles.** They go into its incidence ("cell") property store and come back out
  (9/9 for the sample). Everything around the roles is fragile, though. The first of two records for the
  same (edge, node) pair wins and the second is silently dropped. Metadata other than `name` is dropped.
  Isolated nodes and empty edges are dropped on export. `network-type` is never read. Every call needs the
  network. Failures return `None` instead of raising. And HNX cannot read its own directed output back:
  on the second generation every `direction` becomes `"nil"` and `to_hif` returns `None`.
- **Neither library can hold two incidence records for one (edge, node) pair natively.** XGI edges are
  sets. HNX indexes cells by (edge, node) and drops duplicates. The exception is one node on both the tail
  and the head of one XGI directed edge, which survives, though without its roles.
- **A loader that bypasses both HIF modules works today, with no upstream change.** It builds the objects
  through public constructors, keeps what the library cannot hold in a context object, and reconciles
  on export. Tested on 27 cases, it was exact for 24 of the 25 accepted cases through XGI, through HNX
  and along the gate's chain HIF → XGI → HIF → HNX → HIF. The 25th was merged by policy, and 2 cases were
  rejected by design. It was idempotent on all 25, deterministic across hash seeds, and used no network
  (section 7).

The findings feed the design of the loaders and the HIF `roles` convention. Report
[01](01-requirements-from-kb.md) (requirements) inferred several of these behaviours from source and
left others open. Section 8 settles them by execution. Report [02](02-hif-standard.md) covers the HIF
specification itself.

## 0. Scope, versions and method

### 0.1 Versions (checked 2026-09-23)

| Package | Version | Released (PyPI upload) | Note |
|---|---|---|---|
| `xgi` | **0.10.2** | 2026-05-15T18:30:43Z | latest on [PyPI](https://pypi.org/project/xgi/) on 2026-09-23 |
| `hypernetx` | **2.4.3** | 2026-07-23T03:49:28Z | latest on [PyPI](https://pypi.org/project/hypernetx/) on 2026-09-23; declares `pandas (<3.0.0)` |
| `pandas` | 2.3.3 | | pulled in under HNX's pin; the latest on PyPI is 3.0.6 |
| `numpy` / `jsonschema` / `fastjsonschema` / `requests` | 2.4.6 / 4.26.0 / 2.22.2 / 2.34.2 | | |
| Python | 3.11.15, Linux x86_64, preferred encoding UTF-8 | | |

The full `pip freeze` of the probe virtualenv is in
[probes/requirements-probes.txt](probes/requirements-probes.txt). The sha256 of every library source file
cited here is recorded in the `env` block of `probes/out/xgi-summary.json` and `probes/out/hnx-summary.json`.

**Line numbers are stable against upstream.** Every cited source file was fetched from GitHub at the
release tags [`xgi-org/xgi@v0.10.2`](https://github.com/xgi-org/xgi/tree/v0.10.2) and
[`pnnl/HyperNetX@v2.4.3`](https://github.com/pnnl/HyperNetX/tree/v2.4.3). All eleven XGI files and seven HNX
files cited are byte-identical to the installed wheels, so the line anchors below point at the code that ran.
The HIF modules on the development branches are byte-identical too: `xgi/convert/hif_dict.py` and
`xgi/readwrite/hif.py` on XGI `main`, `hypernetx/hif.py` on HNX `master` and `develop`, and
`hypernetx/classes/factory.py` on HNX `master`. So none of the HIF behaviour below has already been fixed
in unreleased code.

### 0.2 Evidence labels

- **[P: path]** is behaviour observed in a probe run. The path is the saved output under
  [probes/out/](probes/out/).
- **[S: file:line]** is read in the installed source, linked at the release tag.
- **[R]** is my recommendation for the design stage, not an established fact.

### 0.3 Probes (all in [probes/](probes/))

| Script | What it does | Main outputs |
|---|---|---|
| [`probe_common.py`](probes/probe_common.py) | Builds the 27 cases in [`lib-cases/`](probes/lib-cases/) (c00 is [`schemas/sample.hif.json`](../../../schemas/sample.hif.json) itself). Contains the structural HIF diff. | `lib-cases/*.hif.json`, `lib-cases/INDEX.json` |
| [`probe_xgi.py`](probes/probe_xgi.py) | `xgi.read_hif` → where each field landed → `xgi.write_hif` → diff → second generation; then 20 native operations | `out/xgi/<case>.json`, `out/xgi/<case>.out.hif.json`, `out/xgi-summary.json`, `out/xgi-ops.json` |
| [`probe_hnx.py`](probes/probe_hnx.py) | `hnx.from_hif` → placement → `hnx.to_hif` (with the input's `network-type`, and with the default) → diff → second generation; offline behaviour; 17 native operations and 3 checks of duplicate-pair handling. When `to_hif` returns `None`, it captures the would-be output with validation disabled and validates that with jsonschema. | `out/hnx/…`, `out/hnx-summary.json`, `out/hnx-offline.json`, `out/hnx-ops.json` |
| [`role_loaders_sketch.py`](probes/role_loaders_sketch.py) | Research sketch of the recommended adapters (`to_xgi`/`from_xgi`, `to_hnx`/`from_hnx`). It is not the P2 package. | — |
| [`probe_rolepreserving.py`](probes/probe_rolepreserving.py) | Runs every case through the sketch, plus 19 XGI and 16 HNX native-operation runs, with network access disabled | `out/rolepreserving-summary.json`, `out/rolepreserving-ops.json` |
| [`probe_determinism.py`](probes/probe_determinism.py) | Byte-level output under 4 `PYTHONHASHSEED` values | `out/determinism.json` |
| [`probe_invalid_inputs.py`](probes/probe_invalid_inputs.py) | Gives the 13 schema-invalid cases of the sibling schema probe ([hif-schema/cases/](probes/hif-schema/cases/), read only) to both readers | `out/invalid-inputs.json` |

Run everything with a virtualenv built from `requirements-probes.txt` (`python probe_xgi.py`, and so on).
`probe_hnx.py`, `probe_determinism.py` and `probe_invalid_inputs.py` need access to
raw.githubusercontent.com, because HNX fetches its schema on every call.

**The cases**, one question each (full descriptions in `lib-cases/INDEX.json`):

| id | case | id | case |
|---|---|---|---|
| c00 | KB sample: directed, 3 weighted edges, 9 role-labelled incidences, nested metadata | c14 | `directed` file with one incidence lacking `direction` (schema-valid) |
| c01 | sample, `undirected`, no direction fields | c15 | incidence `attrs` `{role}`, `{}` and absent |
| c02 | sample, `undirected`, direction fields kept | c16 | attrs values: lists, nested dicts, `null`, booleans, non-ASCII, `[]`, `{}`, an integer above 2^53, 1e-300 |
| c03 | sample without `network-type` | c17 | record-level `weight` on nodes, edges and incidences |
| c04 | sample as `asc` | c18 | a key named `weight` inside attrs, no record-level weight |
| c05 | **one node, two roles, one edge, both on the tail** (two records for one pair, different weights) | c19 | node and edge each declared twice with different attrs |
| c06 | **one node as tail (`regulator`) and head (`target`) of one edge** | c20 | metadata with the keys HNX interprets (`name`, `default_attrs` holding a default `role`) |
| c07 | c05 undirected | c21 | isolated node whose attrs contain the key `node` |
| c08 | isolated nodes (with and without attrs) | c22 | `NaN` in attrs (not strict JSON) |
| c09 | empty edges (with and without attrs) | c23 | integer ids at and beyond 2^53 and 2^63 |
| c10 | nested fact: edge id `f1` is also a node of edge `m1` | c24 | `{"incidences": []}` |
| c11 | integer ids; edge 0 and node 0 | c25 | plain undirected, no attrs |
| c12 | the integer `1` and the string `"1"` as distinct nodes and distinct edges | c26 | empty edge whose attrs contain `members` and `idx` |
| c13 | CJK, emoji, spaces; NFC and NFD `é` as two nodes | | |

**How the diff counts.** Ids keep their JSON type: `1` and `"1"` are different ids. Incidences are grouped
by (edge, node) and compared as multisets, so two records for one pair count separately. `attrs: {}`
equals a missing `attrs`. A missing `weight` does *not* equal `weight: 1`, because HIF defines no default.
Order is not compared, except in `probe_determinism.py`.

## 1. The APIs: exact names and signatures

**XGI 0.10.2** exports six HIF functions at top level. The same functions handle all three classes;
there is no separate "directed" reader or writer.

| Function | Signature | Source |
|---|---|---|
| `xgi.read_hif` | `(path, nodetype=None, edgetype=None)` → `Hypergraph`, `DiHypergraph` or `SimplicialComplex` | [readwrite/hif.py:93](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/readwrite/hif.py#L93) (reads with `xopen`, calls `from_hif_dict` at [:116](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/readwrite/hif.py#L116)) |
| `xgi.write_hif` | `(H, path, **kwargs)`; writes `to_hif_dict(H, convert_nans=True)` as `json.dumps(data, indent=2)` | [readwrite/hif.py:19-41](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/readwrite/hif.py#L19-L41) |
| `xgi.read_hif_collection` / `xgi.write_hif_collection` | `(path, nodetype=None, edgetype=None)` / `(H, path, collection_name="", **kwargs)` | [readwrite/hif.py:119](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/readwrite/hif.py#L119), [:44](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/readwrite/hif.py#L44) |
| `xgi.from_hif_dict` | `(data, nodetype=None, edgetype=None)` | [convert/hif_dict.py:98](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L98) |
| `xgi.to_hif_dict` | `(H, convert_nans=False)` → a `defaultdict` | [convert/hif_dict.py:13](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L13) |

`xgi.load_xgi_data` also parses HIF, through `from_hif_dict`
([readwrite/xgi_data.py:168](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/readwrite/xgi_data.py#L168)).
The deprecated `read_json`/`write_json` still exist in `xgi/readwrite/json.py`, but in 0.10.2 they are no
longer exported as `xgi.read_json`/`xgi.write_json` [P: checked with `hasattr` on 2026-09-23]. The
`DiHypergraph` docstring says "This is currently an experimental feature"
([core/dihypergraph.py:24](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/dihypergraph.py#L24)).

**HyperNetX 2.4.3** has two module-level functions, re-exported at top level
([`__init__.py:6`](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/__init__.py#L6)). There are no
`Hypergraph.from_hif`/`to_hif` methods [P: `hasattr` is False for both].

| Function | Signature | Source |
|---|---|---|
| `hnx.from_hif` | `(hif=None, filename=None)` → `hnx.Hypergraph`, **or `None`** when schema validation fails | [hif.py:116-202](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L116-L202) |
| `hnx.to_hif` | `(hg, filename=None, network_type="undirected", metadata=None)` → dict, **or `None`** when its own output fails validation | [hif.py:42-113](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L42-L113) |
| `hypernetx.hif.schema_url` | `"https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json"`, fetched on every call | [hif.py:12](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L12), [:63](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L63), [:136](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L136) |
| `hnx.Hypergraph` (what `from_hif` calls) | `(setsystem=None, default_cell_weight=1, edge_col=0, node_col=1, cell_weight_col="weight", misc_cell_properties_col=None, aggregate_by="first", properties=None, misc_properties_col=None, weight_prop_col="weight", default_weight=1, edge_properties=None, misc_edge_properties_col=None, edge_weight_prop_col="weight", default_edge_weight=1, node_properties=None, misc_node_properties_col=None, node_weight_prop_col="weight", default_node_weight=1, name=None, **kwargs)` | [classes/hypergraph.py:277-310](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hypergraph.py#L277-L310) |
| `H.get_cell_properties` | `(edge_uid, node_uid, prop_name=None)` | [classes/hypergraph.py:663](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hypergraph.py#L663) |

## 2. Where each HIF field lands

### 2.1 XGI: there is no incidence-level store

An XGI object's whole state is `_edge_uid`, `_net_attr`, `_node`, `_node_attr`, `_edge` and `_edge_attr`
([core/hypergraph.py:103-110](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/hypergraph.py#L103-L110),
[core/dihypergraph.py:110-117](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/dihypergraph.py#L110-L117)).
Membership is a set of node ids per edge; for `DiHypergraph` it is `{"in": set, "out": set}`. There is
nowhere to put a (edge, node) attribute. The reader never looks: its incidence loop reads only `node`,
`edge` and, for directed files, `direction`
([hif_dict.py:150-159](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L150-L159)).
The string `weight` does not occur in either XGI HIF module [S: grep, both files].

| HIF field | Lands in | Evidence |
|---|---|---|
| `incidences[].attrs` (incl. `role`) | **nowhere**. 0 of 8 role strings found in `H.__getstate__()` for the sample | [P: out/xgi/c00-sample-directed.json `placement.role_strings_in_object_state`] [S: hif_dict.py:150-159] |
| `incidences[].direction` | `DiHypergraph` edge sets: `tail` → `"in"`, anything else → `"out"` | [S: hif_dict.py:134](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L134), [dihypergraph.py:815-832](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/dihypergraph.py#L815-L832) |
| `incidences[].weight`, `nodes[].weight`, `edges[].weight` | **nowhere**. 0 of the 4 distinct weight values of c17 found in the object state | [P: out/xgi/c17-weights-everywhere.json] |
| `nodes[].attrs` | `H.nodes[n]` (`_node_attr`) | [S: hif_dict.py:162-173](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L162-L173) |
| `edges[].attrs` | `H.edges[e]` (`_edge_attr`) | [S: hif_dict.py:176-186](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L176-L186) |
| `metadata` | `H._net_attr` (read as `H["key"]`) | [S: hif_dict.py:147-148](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L147-L148) |
| `network-type` | the class: `directed` → `DiHypergraph`; `undirected` or missing → `Hypergraph`; `asc` → `SimplicialComplex` | [S: hif_dict.py:136-144, 188-189](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L136-L144) |

On write, `to_hif_dict` derives `network-type` from the class
([:48-53](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L48-L53)). It writes node and
edge records only for isolated nodes, empty edges and objects with attrs
([:56-82](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L56-L82)). Incidence
records carry only `edge`, `node` and, for directed hypergraphs, `direction`
([:85-94](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L85-L94)).

### 2.2 HyperNetX: three property stores, one of them per incidence

`from_hif` turns `incidences`, `nodes` and `edges` into pandas DataFrames and passes them to the
`Hypergraph` constructor. Each incidence record's `attrs` becomes the cell's `misc_properties`. Every
other incidence field (`weight`, `direction`) becomes a column
([hif.py:156-202](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L156-L202)).

| HIF field | Lands in | Evidence |
|---|---|---|
| `incidences[].attrs` (incl. `role`) | cell `misc_properties` in `H.incidences.property_store`, readable as `H.get_cell_properties(e, n, "role")`; 8/8 role strings of the sample found there | [P: out/hnx/c00-sample-directed.json `placement.role_strings_found_at`] |
| `incidences[].direction` | an ordinary cell column named `direction`; no algorithm reads it | [P: same file, `incidence_columns`] |
| `incidences[].weight` | cell column `weight`, default 1 when absent | [S: factory.py:65-80](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/factory.py#L65-L80) |
| `nodes[]` / `edges[]` | node and edge property stores: `weight` column plus `misc_properties` | [S: hif.py:179-186](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L179-L186) |
| `metadata` | only `name` (becomes `H.name`) and `default_attrs` are used. None of the five string values in the sample's metadata is found anywhere in the object | [S: hif.py:162-191](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L162-L191); [P: `metadata_string_values_found_at`] |
| `network-type` | **not read**. The string `network` occurs in `hif.py` only in `to_hif`'s parameter and output | [S: grep; hif.py:42, 104](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L104) |

Two HNX details matter for P2.

- **The accessor flattens nested attrs.** `get_cell_properties(e, n)` merges `misc_properties` into one
  flat dict recursively. For c16, the key `qualifiers` disappears and its children `since`, `certainty`
  and `deep` are hoisted to the top level. The raw `misc_properties` and the exported `attrs` stay nested
  [P: out/hnx/c16-attr-value-shapes.json `placement.cell_accessors` vs `placement.incidences`]
  [S: property_store.py:110, 288-306](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/property_store.py#L288-L306).
- **Only incident items are visible.** Views, and therefore `to_hif`, show only nodes and edges present in
  the incidence store ([hyp_view.py:122-136](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hyp_view.py#L122-L136)).
  Isolated nodes and empty edges survive in the property stores but are invisible
  [P: out/hnx/c08-isolated-nodes.json `node_ids_in_property_store_but_not_in_H.nodes` = both isolated nodes].

## 3. Feature × library: what survives a library round trip

Legend: **preserved**; **lost**; **altered** (present but changed); **added** (appears though absent from
the input); **error** (raises); **None** (returns `None` silently). XGI means `read_hif` then `write_hif`.
HNX means `from_hif` then `to_hif(network_type=<input's network-type>)`. The default `to_hif` call writes
`"undirected"`. Counts are records kept / records in the input.

| # | Feature | XGI 0.10.2 | HNX 2.4.3 | Probe | Root cause |
|---|---|---|---|---|---|
| 1 | `incidences[].attrs.role`, one record per pair | **lost** 0/9 (sample); 0/n in all 22 loadable cases that carry roles | **preserved** 9/9 (sample); n/n in all 23 loadable cases without duplicate pairs (for c14 only in the would-be output, see row 8) | c00, all | XGI: no incidence store, reader ignores `attrs` ([hif_dict.py:150-159](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L150-L159)). HNX: `attrs` → `misc_cell_properties_col` ([hif.py:195](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L195)) |
| 2 | other incidence attrs (nested values, lists, `null`, non-ASCII) | **lost** | **preserved** in output; **altered** (flattened) through `get_cell_properties` | c16 | as above; [property_store.py:288-306](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/property_store.py#L288-L306) |
| 3 | **two records for one (edge, node) pair, same direction** (node with two roles) | **lost**: 4 → 3 records, both roles and both weights gone | **lost second**: 4 → 3 records; first kept (`intervention`, weight 0.7), `background-therapy`/0.3 dropped silently | c05, c07 | XGI: members are sets ([hypergraph.py:1116](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/hypergraph.py#L1116), [dihypergraph.py:831](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/dihypergraph.py#L831)). HNX: `dfp[~dfp.index.duplicated(keep="first")]` ([factory.py:87](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/factory.py#L87)) |
| 4 | **one node as tail and head of one directed edge** | membership and both directions **preserved** (3/3); roles lost | **lost second**: 3 → 2 records; the `head`/`target` record dropped | c06 | XGI keeps separate `in`/`out` sets ([bipartite_edges.py:64-71](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/bipartite_edges.py#L64-L71)). HNX: factory.py:87 |
| 5 | `aggregate_by` for duplicate pairs | n/a | **ignored**: `aggregate_by={"weight": "sum"}` still keeps 0.7 | `out/hnx-ops.json` (last two rows) | `aggregation_methods` is accepted but never used ([factory.py:34, 163](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/factory.py#L34)) |
| 6 | `direction`, directed file | **preserved** 9/9 | **preserved** 9/9 in the first generation, **only** if `network_type="directed"` is passed; **lost** (`"nil"`, `to_hif` → None) in the second | c00 | section 4.2 |
| 7 | `direction` present, `network-type` `undirected` or absent | **lost** 0/9 (reader reads `direction` only for directed files) | **preserved** 9/9 as a cell column, in a file still labelled undirected | c02, c03 | [hif_dict.py:136-159](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L136-L159); [hif.py:187-190](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L187-L190) |
| 8 | directed file, one incidence without `direction` (schema-valid) | **error** `KeyError: 'direction'` | loads; the missing value is `NaN`; `to_hif` → **None** (the cell is written `"direction": "nil"`) | c14 | [hif_dict.py:155](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L155); [hif.py:39](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L39) `fillna("nil")`, [:107-113](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L107-L113) |
| 9 | incidence `weight` | **lost** (0/2 in c17, 0/2 in c05) | **preserved** (2/2), and **added** as `weight: 1` on every record without one (9 of 9 in the sample) | c17, c00 | XGI never reads or writes `weight`; HNX default 1 ([factory.py:65-80](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/factory.py#L65-L80), [hif.py:166, 194](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L166)) |
| 10 | node / edge `weight` | **lost** (sample edge weights 0.95, 0.80, 1.0 gone) | **preserved**; `weight: 1` **added** on every other node and edge | c00, c17 | same |
| 11 | a key named `weight` inside attrs, no record weight | preserved as an attr (nodes, edges) | **altered**: the attr value is copied up into the record-level `weight` (incidence 5, node 7, edge 9) and also kept in `attrs` | c18 | when no `weight` column exists, `grabweight` reads `misc_properties.get("weight")` ([factory.py:70-80](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/factory.py#L70-L80)) |
| 12 | node `attrs`, edge `attrs` | **preserved**, including lists, nested dicts, `null`, 2^53+1, 1e-300 | **preserved** | c00, c16 | — |
| 13 | `metadata` | **preserved**, all keys (except `asc`, row 20) | **lost**: all keys but `name`; `default_attrs` **added** | c00, c16 | [hif.py:67-73, 93-99, 162-191](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L162-L191) |
| 14 | `network-type` | **preserved** (from the class); **added** `"undirected"` when absent | not read; written from the `to_hif` argument, so a directed file comes out `"undirected"` with the default call | c00, c03 | [hif.py:104](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L104) |
| 15 | isolated node | **preserved** | **lost** on export (kept, invisibly, in the property store) | c08 | [hyp_view.py:122-136](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hyp_view.py#L122-L136) |
| 16 | empty edge | **preserved** | **lost** on export | c09 | same |
| 17 | nested fact (edge id reused as a node id) | **preserved** (node `f1` and edge `f1` keep their own attrs) | **preserved** | c10 | — |
| 18 | integer ids; `1` vs `"1"`; ids ≥ 2^53 and ≥ 2^63; CJK, emoji, NFC vs NFD | **preserved**, with types | **preserved**, with types | c11, c12, c13, c23 | — |
| 19 | duplicate node / edge declarations | **merged**: later declarations update earlier ones | **first declaration kept** | c19 | [hif_dict.py:170-173](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L170-L173); factory.py:87 |
| 20 | `network-type: asc` | **altered**: `SimplicialComplex`; 9 → 39 incidence records (30 new subface pairs, 13 new edges with integer ids); metadata **lost** (all 6 keys) | loaded as a plain hypergraph | c04 | [hif_dict.py:188-189](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L188-L189) → [simplicialcomplex.py:105](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/simplicialcomplex.py#L105) → [higher_order_network.py:195-202](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/higher_order_network.py#L195-L202) (the `Hypergraph` branch does not copy `_net_attr`; the `SimplicialComplex` branch does, at :192) |
| 21 | `NaN` in attrs (non-strict input) | **altered**: node attr `NaN` → `null`; output is strict JSON | preserved and written as a bare `NaN`: output is **not** strict JSON | c22 | [hif.py:36](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/readwrite/hif.py#L36) (`convert_nans=True`); HNX `json.dump` with the default `allow_nan=True` ([hif.py:110](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L110)) |
| 22 | attrs key `node` on an isolated node / `members`, `idx` on an empty edge | **error** `TypeError: … got multiple values for argument 'node'` / `'members'` | loads; the node or edge is then lost on export (rows 15, 16) | c21, c26 | `H.add_node(n, **attr)` [hif_dict.py:171](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L171), `H.add_edge(…, e, **attr)` [:184](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L184) |
| 23 | `metadata.default_attrs` in the input | ordinary metadata (preserved) | **interpreted**: a default `role: "participant"` is **added** to the incidence that had none | c20 | [hif.py:163-178](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L163-L178) |
| 24 | `{"incidences": []}` (valid HIF) | preserved (`network-type` added) | **error** `KeyError: "None of [Index(['edge', 'node'])] are in the [columns]"` | c24 | [hif.py:190](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L190) |
| 25 | schema-invalid input (13 files) | no validation: **10 of 13 load silently**, including extra record keys, float and boolean ids, and `"direction": "treatment"` (put in the head set); 3 raise: `null` id (`XGIError`, [utilities.py:47](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/utils/utilities.py#L47)), `network-type` outside the enum (`UnboundLocalError`, [hif_dict.py:148](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L148)), no `incidences` (`KeyError`, [:150](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L150)) | **None** for all 13, no exception | `out/invalid-inputs.json` | XGI: no schema check; [hif_dict.py:134, 141-144](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L141-L144). HNX: [hif.py:141-152](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L141-L152) |
| 26 | output validates against the HIF schema | yes, in all 24 loadable cases | yes when `to_hif` returns a dict; c14 and every second-generation directed file fail | `export.schema_errors` | — |

Evidence files: `out/xgi/<case>.json` and `out/hnx/<case>.json` (full diff per incidence, node and
edge), summarised in `out/xgi-summary.json` and `out/hnx-summary.json`. The library outputs themselves are
`out/<lib>/<case>.out.hif.json`.

## 4. Idempotence, determinism and the network

### 4.1 XGI

- **Idempotent.** Feeding XGI's output back into XGI (second generation) changes nothing structurally
  in any of the 24 loadable cases [P: `gen2_idempotent` in out/xgi-summary.json]. The first round has
  already removed everything XGI cannot hold.
- **Not byte-deterministic.** Writing the sample under four `PYTHONHASHSEED` values gave four different
  files. The order of the incidences inside an edge and of the `nodes` array changes
  [P: out/determinism.json, 4 distinct sha256]. The cause is that members are Python sets, iterated by
  `to_bipartite_edgelist`
  ([bipartite_edges.py:64-73](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/bipartite_edges.py#L64-L73)),
  and that the node and edge records come from set unions
  ([hif_dict.py:56-58, 70-72](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L56-L58)).
  HNX's output and both sketch adapters gave one output across the four seeds.

### 4.2 HyperNetX cannot read its own directed output back

`to_hif` always writes `metadata.default_attrs`, built from each property store's defaults
([hif.py:67-73](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L67-L73)). For a hypergraph
loaded from a directed file this includes `"incidences": {"weight": 1, "direction": null, "attrs": {}}`
[P: out/hnx/c00-sample-directed.out.hif.json]. On re-import, `from_hif` treats every key of
`default_attrs` other than `weight` and `attrs` as a column to pop out of each row's `attrs`, with the
default as fallback. That overwrites the real `direction` column with `None` for every row
([hif.py:163-178](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L163-L178)).
`to_hif` then turns `None` into `"nil"` (`fillna("nil")`,
[hif.py:39](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L39)), fails its own schema
check, and returns `None` without raising
([hif.py:107-113](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L107-L113)). Observed in
**every** case that carries `direction` (c00, c02, c03, c05, c06, c08–c11, c13, c15–c18, c20–c22, c26):
second-generation direction 0/n, `to_hif` → `None`. The error captured with validation disabled is
`incidences/0/direction: 'nil' is not one of ['head', 'tail']`
[P: out/hnx/c00-sample-directed.json `gen2`]. The undirected cases survive a second generation.

The same mechanism made HNX invent a role in c20, where the input's `default_attrs` declared
`role: "participant"` (row 23 of the table).

### 4.3 Network dependence of HyperNetX

With `requests.get` made to fail, `from_hif` raises `ConnectionError` at
[hif.py:136](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L136) and `to_hif` at
[hif.py:63](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L63). The public
`hnx.Hypergraph(DataFrame, …)` constructor works offline and keeps roles [P: out/hnx-offline.json]. In a
fresh interpreter whose proxy variables pointed at a closed local port, `import hypernetx` succeeded, but
`from_hif` raised `ProxyError` [P: out/hnx-offline.json, last entry]. So in 2.4.3 the failure is per call,
not at import. Issue [pnnl/HyperNetX#171](https://github.com/pnnl/HyperNetX/issues/171) ("Code Fails on
Import if Internet Connection is Disrupted", open since 2025-10-21) describes the import-time form. Its
"fails on import" did not reproduce with 2.4.3, but the underlying dependence remains. In the saved run, one
networked `from_hif` call took 0.19–0.46 s in this environment, behind a proxy (median 0.36 s over 27
calls; other runs gave similar ranges) [P: `load.seconds` in out/hnx/c*.json].

## 5. Native operations that may drop attributes

### 5.1 XGI (`out/xgi-ops.json`)

Roles are already gone after `read_hif`. The question here is what happens to node, edge and network
attributes, where a loader might stash roles.

| Operation | Effect on attrs and ids |
|---|---|
| `H.copy()`, `DH.copy()` | all node, edge and network attrs identical |
| `xgi.subhypergraph(H, nodes=…)` | induced: only edges whose members are all kept survive; attrs of survivors identical |
| `xgi.subhypergraph(DH, nodes=…)` | **error** `XGIError: Invalid ebunch format` as soon as any edge survives. It passes an undirected member set to `DiHypergraph.add_edges_from` ([globalviews.py:64-68](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/globalviews.py#L64-L68) → [dihypergraph.py:763-767](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/dihypergraph.py#L763-L767)) |
| `add_edge`, `add_node_to_edge` | new memberships; nothing else touched |
| `remove_node(n)` (weak) | edge attrs untouched, so `arity: 4` is now **stale** on a 3-member edge |
| `remove_node(n, strong=True)` | incident edges and their attrs deleted |
| `H.dual()` | node and edge attrs swap roles; `DiHypergraph` has no `dual` (`AttributeError` from `__getattr__`, [dihypergraph.py:257](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/dihypergraph.py#L257)) |
| `merge_duplicate_edges()` | the surviving edge keeps the attrs of the smallest id (`merge_rule="first"`, [hypergraph.py:1387-1389](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/hypergraph.py#L1387-L1389)); the copy's attrs are lost |
| `H.cleanup()` (defaults) | merges duplicates, drops singletons and isolates, keeps only the **largest connected component** (the `publishes` fact and its 2 nodes vanish), and relabels |
| `xgi.convert_labels_to_integers(H)` | ids become 0..n-1. The old id is written into the `label` attr, **overwriting** the KB's own `label` values ("metformin" → "drug:metformin"). The docstring says so ([utilities.py:400-402](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/utils/utilities.py#L400-L402), [:417](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/utils/utilities.py#L417)) |
| `H << H2` | edge ids renumbered 0..n-1; attrs carried to the new ids ([hypergraph.py:305-316](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/hypergraph.py#L305-L316)) |
| `xgi.Hypergraph(DH)` | direction dropped |

### 5.2 HyperNetX (`out/hnx-ops.json`, sample loaded with `from_hif`)

| Operation | Roles (cell properties) | Other effects |
|---|---|---|
| `clone()` | all 9 kept | `name` becomes `"None_clone"` ([hypergraph.py:620](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hypergraph.py#L620)) |
| `restrict_to_nodes([metformin, T2DM, insulin])` | kept on the 4 surviving cells | **n-ary facts trimmed**: `f1` keeps 2 of 4 participants and its `arity: 4` goes stale |
| `restrict_to_edges`, `remove_edges`, `remove_nodes`, `remove_incidences` | kept on surviving cells | — |
| `rename(nodes=…)` | follow the renamed node | — |
| `dual()` | follow the reversed pairs | property stores shared with the original by default (`share_properties=True`, [hypergraph.py:1217-1219](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hypergraph.py#L1217-L1219)) |
| `collapse_nodes()`, `collapse_nodes_and_edges()` | **corrupted**: `org:ADA` and `doc:guideline-2024` collapse, and the survivor `(f3, doc:guideline-2024)` gets `publisher`/`tail` instead of `publication`/`head` | aggregation defaults to `"first"` on every column, including `misc_properties` ([hypergraph.py:2806](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hypergraph.py#L2806)) |
| `collapse_edges()` (after adding a copy of `f1` with other roles) | the representative's roles kept; the copy's lost | edge weights **summed** (`f1`: 0.95 + 1 = 1.95); `_level` and `equivalence_class_size` added to edge attrs |
| `sum(H2)` | on a shared pair, `self` wins; `H2`'s role dropped | [hypergraph.py:2731-2733](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hypergraph.py#L2731-L2733) |
| `add_incidence(e, n, role=…)` with no `direction` | new cell's `direction` is `None` | **`to_hif` → None** (`'nil'`); with `direction="tail"` it exports |
| `add_edge(e, …)`, `add_node(n, …)` | — | "Does not add an incidence" ([hypergraph.py:1632-1651](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hypergraph.py#L1632-L1651)), so the new object is invisible and dropped by `to_hif` |
| `H.incidences[(e, n)].role = "…"` | updated and exported | — |

## 6. Root causes in one place

| # | Behaviour | File:line (tag) |
|---|---|---|
| X1 | XGI has no incidence-level storage | [core/hypergraph.py:103-110](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/hypergraph.py#L103-L110), [core/dihypergraph.py:110-117](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/dihypergraph.py#L110-L117) |
| X2 | reader ignores incidence `attrs` and every `weight` | [convert/hif_dict.py:150-186](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L150-L186) |
| X3 | writer emits no incidence `attrs` and no `weight` | [convert/hif_dict.py:55-95](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L55-L95) |
| X4 | directed files: `record["direction"]` unconditional (`KeyError` if missing); any value but `tail`, even `"treatment"`, becomes head | [hif_dict.py:155](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L155), [:134](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L134) |
| X5 | `**attr` splat into `add_node`/`add_edge` | [hif_dict.py:171](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L171), [:184](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L184) |
| X6 | membership is a set, so duplicate pairs collapse | [core/hypergraph.py:1110-1117](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/hypergraph.py#L1110-L1117), [core/dihypergraph.py:824-832](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/core/dihypergraph.py#L824-L832) |
| X7 | `asc` loses metadata and gains subfaces | [hif_dict.py:188-189](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L188-L189), [convert/higher_order_network.py:195-202](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/higher_order_network.py#L195-L202) |
| X8 | output order follows set iteration | [convert/bipartite_edges.py:64-73](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/bipartite_edges.py#L64-L73), [hif_dict.py:56-72](https://github.com/xgi-org/xgi/blob/v0.10.2/xgi/convert/hif_dict.py#L56-L72) |
| N1 | schema fetched over the network on every call | [hif.py:12, 63-65, 136-138](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L136-L138) |
| N2 | validation errors swallowed (`HyperNetXError(ex)` without `raise`), function returns `None` | [hif.py:107-113, 141-152](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L141-L152) |
| N3 | duplicate (edge, node) rows dropped, first kept; `aggregate_by` unused | [classes/factory.py:87](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/factory.py#L87), [:34, 163](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/factory.py#L163) |
| N4 | metadata other than `name`/`default_attrs` never stored | [hif.py:162-191](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L162-L191) |
| N5 | `default_attrs` written with `direction: null` and re-read as a column default | [hif.py:67-73, 163-178](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L163-L178) |
| N6 | missing values written as `"nil"` | [hif.py:39](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L39) |
| N7 | `network-type` not read; written from the argument (default `"undirected"`) | [hif.py:42, 104](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L42) |
| N8 | views, and so `to_hif`, drop isolated nodes and empty edges | [classes/hyp_view.py:122-136](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hyp_view.py#L122-L136) |
| N9 | `to_hif(metadata=dict)` returns `None` (`metadata = metadata.update(...)`) | [hif.py:93-94](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L93-L94) (sibling probe, [hif-schema/README.md](probes/hif-schema/README.md)) |
| N10 | `collapse_*` aggregates cell properties with `"first"` | [classes/hypergraph.py:2790-2810](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/classes/hypergraph.py#L2790-L2810) |
| N11 | empty `incidences` crashes the column selection | [hif.py:187-190](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L187-L190) |
| N12 | files opened without being closed (`json.dump(hif, open(filename, "w"))`, `json.load(open(filename, "r"))`), so every file-based call emits a `ResourceWarning` [P: `warnings` in out/hnx/*.json] | [hif.py:110](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L110), [:147](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L147) |

## 7. What a role-preserving loader must do

### 7.1 XGI: what the loader must do beyond `xgi.read_hif`

1. **Keep every incidence record outside the XGI object.** That means role, other attrs and weight,
   keyed by (edge, node, direction) plus an ordinal, so that two records for one pair stay two. XGI has
   no slot for them (X1–X3), so there is no way around this.
2. **Keep record-level weights** of nodes, edges and incidences in the same side store (X2, X3).
3. **Check `direction` before building a `DiHypergraph`.** A missing value raises `KeyError`, and any
   other string silently becomes head (X4).
4. **Never splat attrs into keyword arguments.** In practice: do not call `from_hif_dict`. Build with
   `add_node_to_edge`, `add_node(n)` and `add_edge(members, idx=e)`, then `set_node_attributes` and
   `set_edge_attributes` (X5).
5. **Refuse `asc` for knowledge records, or load it as a plain `Hypergraph`.** `SimplicialComplex`
   invents subfaces and drops metadata (X7).
6. **Write with its own serializer, never `write_hif`.** Reconcile the side records against the current
   membership: records whose membership is gone are *stale*, and memberships without a record are
   *unlabelled*. Report both, never re-attach a record to another pair, and emit in a canonical order (X8).

### 7.2 HyperNetX: what the loader must do beyond `hnx.from_hif`

1. **Do not call `hnx.from_hif` or `hnx.to_hif` at all.** They need the network (N1), return `None`
   instead of raising (N2), drop metadata (N4), invent values from `default_attrs` (N5, row 23), write
   `"nil"` (N6), ignore `network-type` (N7), drop isolated nodes and empty edges (N8), cannot read their
   own directed output (section 4.2), and crash on empty input (N11). Build the object with the public
   constructor instead:
   `hnx.Hypergraph(df, edge_col="edge", node_col="node", cell_weight_col="weight", misc_cell_properties_col="attrs", node_properties=…, edge_properties=…, misc_properties_col="attrs")`.
   This works offline and puts `role` straight into cell properties [P: out/hnx-offline.json].
2. **Pre-aggregate records that share an (edge, node) pair.** The constructor keeps the first row and
   drops the rest whatever `aggregate_by` says (N3, row 5). Put the first record in the cell natively,
   and carry records 2..k in a reserved attrs key of that cell. They then follow the cell through
   `rename`, `dual` and `restrict`.
3. **Keep outside the object what HNX has no place for:** `metadata`, `network-type`, and whether each
   weight was present in the source. HNX writes `1` everywhere (row 9).
4. **Export from the stores, not the views.** Take cells from `H.incidences.to_dataframe`. Take nodes and
   edges from `H.nodes.property_store.properties` and `H.edges.property_store.properties`, which still
   hold the isolated nodes and empty edges that the views hide. Never write `"nil"` or an invented
   `weight: 1`. Never export through `get_cell_properties`, which flattens nested attrs.
5. **Warn about operations that corrupt roles or facts:** `collapse_nodes` and
   `collapse_nodes_and_edges` (roles move to the wrong participant), and `restrict_to_nodes` (partial
   n-ary facts).

### 7.3 What is impossible without upstream changes

These are established by the probes; how to fix them upstream is my recommendation (section 7.5).

- **XGI: incidence attributes as XGI data.** No XGI API, statistic, filter or writer can see a role, and
  no XGI operation can carry one, because the data model has no (edge, node) slot (X1). Roles can live
  only beside the object (a side table) or be packed into edge or node attrs (section 7.4). XGI's own
  `read_hif`/`write_hif` can never round-trip them (X2, X3).
- **XGI: two memberships of one node in one edge with the same direction.** Edges are sets (X6). A
  `DiHypergraph` *can* hold a node once in the tail and once in the head (c06: 3/3 directions kept).
- **HNX: two cells for one (edge, node) pair.** Cells are indexed by the pair and duplicates are dropped
  in the factory (N3). The loader can carry the extra records inside one cell, but HNX's algorithms
  (incidence matrix with `weights=True`, degree) will see one incidence with one weight.
- **HNX: direction as semantics.** There is no directed hypergraph class. `direction` is an opaque
  column, and native operations ignore it (for example, `collapse_nodes` moved a `tail` value onto a
  `head` participant).
- **HNX: graph-level metadata on the object.** Only `name` exists. Everything else has to live beside
  the object.
- **Both: correct results from native operations that renumber, merge or collapse**, with roles kept
  meaningful. Relabelling (`convert_labels_to_integers`, `cleanup`), `<<`, `dual`, `merge_duplicate_edges`
  and `collapse_*` can at best be detected and reported by a loader, unless ids can be mapped back.
- **Using the libraries' own HIF functions for P2's round trip.** Every defect in section 6 needs an
  upstream fix before `xgi.read_hif`/`write_hif` or `hnx.from_hif`/`to_hif` could be used as they are.

### 7.4 Recommended approach, tested [R, with evidence]

**The design.** Own the HIF codec (parse, validate, serialize) in the P2 package. Treat the library
objects as projections built through public construction APIs. Return each together with a context
object holding what the library cannot. Reconcile on export. For HNX, also mirror roles into cell
properties so HNX users can read them natively.

```python
# XGI (from role_loaders_sketch.py, abridged)
def to_xgi(doc):
    nt = _check(doc)                       # incidences present, network-type in the enum, and every
                                           # incidence of a directed file has direction head or tail
    H = xgi.DiHypergraph() if nt == "directed" else xgi.Hypergraph()
    for k, v in doc.get("metadata", {}).items():
        H[k] = v                           # public setter for network attrs
    for r in doc["incidences"]:
        if nt == "directed":
            H.add_node_to_edge(r["edge"], r["node"], "in" if r["direction"] == "tail" else "out")
        else:
            H.add_node_to_edge(r["edge"], r["node"])
    for i, a in merged_decls(doc, "nodes"):   # never H.add_node(i, **a)
        if i not in H.nodes:
            H.add_node(i)
        H.set_node_attributes({i: a})
    ...                                    # edges alike, empty edges via add_edge(set(), idx=i)
    return H, Ctx(network_type=nt, metadata=..., incidences=[...all records...], weights=...)

def from_xgi(H, ctx):
    live = {(e, n, d) for each current membership}   # d = tail/head for DiHypergraph, None otherwise
    keep = [r for r in ctx.incidences if key(r) in live]         # all records, including 2nd roles
    stale = [r for r in ctx.incidences if key(r) not in live]    # reported, never re-attached
    bare = [membership records for live keys without any record] # reported as unlabelled
    ...  # nodes/edges from H (attrs) + ctx (weights, declaration order); metadata from H._net_attr
```

```python
# HNX: first record of a pair lives natively in the cell; records 2..k ride in a reserved key
rows = [{"edge": e, "node": n, "weight": first.get("weight", 1), "direction": first.get("direction"),
         "attrs": {**first.get("attrs", {}), **({EXTRA: rest} if rest else {})}}
        for (e, n), (first, *rest) in grouped(doc["incidences"])]
H = hnx.Hypergraph(pd.DataFrame(rows), edge_col="edge", node_col="node", cell_weight_col="weight",
                   misc_cell_properties_col="attrs", node_properties=nodes_df,
                   edge_properties=edges_df, misc_properties_col="attrs")
# export: cells from H.incidences.to_dataframe (expanding EXTRA), nodes/edges from the property
# stores; metadata, network-type and weight presence from ctx
```

**Results** [P: out/rolepreserving-summary.json, run with `requests.get` patched to raise, so no network]:

| Outcome | Cases |
|---|---|
| Rejected by design | c14 (directed file, missing `direction`) and c22 (`NaN`, not strict JSON) |
| Exact round trip through XGI, through HNX, and along the chain HIF → XGI → HIF → HNX → HIF | 24 of 25 accepted cases, including c05 (4/4 roles) and c06 (3/3 roles and directions); the libraries' own readers give XGI 0/4 and 0/3, HNX 3/4 and 2/3 |
| Not exact, by policy | c19: duplicate node and edge declarations are merged, later ones updating earlier ones |
| Idempotent (second round identical) | 25 of 25 |
| Byte-identical across 4 hash seeds (sample) | yes, both adapters [P: out/determinism.json] |

**Native operations between load and export** [P: out/rolepreserving-ops.json]. For XGI, two
placements of the records were compared. A is the side table (the sketch). B stores each edge's records
as a list in that edge's attrs. "Wrong" means a role on a pair that did not have it, after mapping
renumbered ids back where the op makes that possible.

| XGI operation (c00, c01, c05) | A: side table | B: records in edge attrs |
|---|---|---|
| `copy()`, weak `remove_node`, `add_edge`, `merge_duplicate_edges()` | all surviving roles kept, 0 wrong | same |
| strong `remove_node`, `subhypergraph` | surviving kept; dropped records **reported as stale** (7 for the strong removal on c00) | surviving kept; dropped records vanish with the edge, unreported |
| `H << H2` (edge ids renumbered) | 0/9 kept; all 9 reported stale; memberships exported bare | **9/9 kept**, because the records travel with the edge |
| `convert_labels_to_integers()` | 0 kept, 0 wrong; all stale | same. Re-keying through the `label` attr would be needed |
| `dual()` | 0 kept, 0 wrong | same |

For HNX, with native cells plus the reserved key, roles were kept on every surviving cell after `clone`,
`restrict_to_nodes`, `remove_nodes`, `remove_incidences`, `rename` (the roles follow the node), `dual`
(they follow the reversed pair) and `add_incidence`, and every output validated. The only wrong roles
came from HNX's own `collapse_nodes`: 1 on c00, and on c05 both of metformin's roles moved to insulin.

**Conclusion [R].** The P2 gate ("a record round-trips … to HIF to XGI and HyperNetX and back with roles
intact") is reachable with the current releases and no upstream change, provided the loaders never go
through `xgi.read_hif`/`write_hif` or `hnx.from_hif`/`to_hif`. The gate test should run the chain above on
the sample, c05 and c06, and assert structural equality, not byte equality.

### 7.5 Upstream changes worth proposing [R]

- **XGI** (`hif_dict.py`): read and write incidence `attrs` and every `weight`, for example as an
  optional side mapping returned alongside `H`, or a real incidence-attribute store; raise a clear error
  for a missing or invalid `direction` in directed files; stop splatting attrs into `add_node`/`add_edge`;
  copy `_net_attr` in the `Hypergraph` → `SimplicialComplex` conversion; write in a deterministic order.
- **HyperNetX** (`hif.py`): vendor the schema (as issue #171 asks) and let callers skip validation;
  `raise` the `HyperNetXError`s it already constructs; keep all `metadata`; stop writing
  `default_attrs.incidences.direction: null`, or stop reading it back as a column default; drop
  `fillna("nil")`; export isolated nodes and empty edges; read `network-type`; honour `aggregate_by` or
  document that duplicates are dropped.
- **HIF** (with report 02): say explicitly that `incidences` may repeat an (edge, node) pair, and that a
  pair's records may differ in `direction` (c06). Say that `attrs` must round-trip, so readers keep
  unknown keys.

## 8. Cross-check against report 01

| Report 01 item | What the probes show |
|---|---|
| C1-R66 ("A missing key should therefore raise `KeyError` (inferred from the source, not executed)") | **Confirmed by execution**: `KeyError: 'direction'` at hif_dict.py:155 (c14) |
| C1-R63 ("exactly one incidence record per (edge, node) pair, carrying the *list* of roles") and PF-04 | **Conflicts with c06.** HIF `direction` is one value per record, so one record cannot say that a node is both tail (`regulator`) and head (`target`) of one edge. XGI's `DiHypergraph` can represent that case, and the sketch round-trips it from two records. Keeping C1-R63 means moving direction into per-role attrs and deriving XGI's in/out sets from roles. See D2 in section 9. |
| C1-R70 ("For HyperNetX, that is incidence ("cell") properties. XGI stores attributes only for nodes, edges and the whole network, so its loader keeps an edge-level map from node to roles.") | HNX part **confirmed** (9/9). For XGI, an edge-level store (option B) works and survives `<<`, but a *map keyed by node id* would lose the id type of integer ids if ever written as JSON object keys. A list of records does not have that problem. The side table (A) reports stale records. See D1 in section 9. |
| PF-10 ("whether direction survives as an incidence property is …") | Direction **survives one HNX round trip** as a cell column when `network_type="directed"` is passed, and is **destroyed on the second** (section 4.2) |
| PF-21 (HNX defects "from source reading, not executed") | **Confirmed by execution**: network (4.3), `None` (rows 8 and 25), `"nil"` (row 8, 4.2). Also newly found: second-generation direction loss, `default_attrs` inventing a role, empty input crash, isolated nodes and empty edges dropped, `aggregate_by` ignored |
| Open: "what XGI does with a node that is both tail and head of one edge" | Keeps both memberships and both directions (c06, 3/3); roles lost |
| Open: "whether HyperNetX reorders or retypes ids" | Ids keep their JSON type in both libraries (c11, c12, c23); HNX's order was stable across hash seeds; **XGI's output order is not** (4.1) |

## 9. Decisions for the design stage

Each decision lists the options, the evidence from this report, and my recommendation [R].

| # | Decision | Options | Evidence | Recommendation [R] |
|---|---|---|---|---|
| D1 | Where the XGI adapter keeps incidence records | A: a side table returned with `H` (the sketch). B: a list of records in a reserved edge attr. C: a node → roles map in edge attrs (report 01, C1-R70). | A and B tie on identity-preserving operations. B survives `<<` (9/9 against 0/9). A reports dropped records (7 stale after a strong removal); B loses them silently with the edge. C, written as JSON object keys, turns integer node ids into strings (checked: `json.loads(json.dumps({1: "treatment"}))` gives `{'1': 'treatment'}`). B and C put P2 data into XGI's own attrs, which `xgi.write_hif` would then copy into `edges[].attrs`. | A as the source of truth, bundled with `H` in one object so the two cannot be separated, and a strict export mode that raises when records are stale or memberships unlabelled. Mirror B only if a consumer needs roles to follow renumbered edges. |
| D2 | How a node with several roles in one fact is encoded (C1 and the HIF convention) | a: one incidence record per role, repeating the pair. b: one record per pair with a list of roles (C1-R63). c: forbid, and reify instead. | b cannot express c06, a node on both tail and head of one edge, because HIF's `direction` is one value per record. Both libraries keep only one record per pair natively, so a and b both need adapter work. The sketch round-trips a exactly through both libraries (c05, c06, c07). | a, with the validator rejecting exact duplicates (same edge, node and role) and the linter flagging repeated pairs for review. If b is kept, move direction into per-role attrs and specify how XGI's in and out sets derive from it. |
| D3 | Whether the adapters call the libraries' HIF functions | a: call `xgi.read_hif`/`hnx.from_hif` and patch the result. b: build through public constructors from HIF that P2 has already validated. | Section 3 rows 1–3, 8, 13, 15–16, 22–25; sections 4.2 and 4.3. | b for both. The gate must not need the network. |
| D4 | A directed file with an incidence lacking `direction`, or with an invalid value | reject; default to tail or head; treat it as undirected | XGI raises `KeyError`; HNX writes `"nil"` and returns `None`; XGI sends any value other than `tail` to the head | Reject both in the validator, and add them to the malformed-case list. |
| D5 | Duplicate node or edge declarations | reject; merge (XGI's rule); first wins (HNX's rule) | c19: the libraries disagree | Reject, or make it a lint error, so that no library-specific merge rule decides the result. |
| D6 | Record-level `weight` | carry confidence in it; ignore it; carry it without ever inventing it | XGI drops every weight. HNX adds `1`, promotes an attr named `weight`, and `collapse_edges` sums edge weights (0.95 + 1 = 1.95). | Keep confidence in `attrs` with its scale, as report 01 (C1-R49) recommends. The exporter neither drops nor invents weights. Discourage an attrs key named `weight`. |
| D7 | `metadata` keys that HNX interprets | allow; forbid; warn | `default_attrs` made HNX invent a role (c20); `name` becomes `H.name` | Forbid `default_attrs` in P2 files; allow `name`, knowing how HNX maps it. |
| D8 | `network-type: asc` | allow; reject | XGI turns 9 incidences into 39 and drops metadata (c04) | Reject for knowledge records. |
| D9 | Native operations between load and export | allow everything and report; strict mode; a documented safe list | Section 5 and the operation tables in 7.4 | Document identity-preserving operations as safe. Flag `collapse_*`, `restrict_to_nodes` (partial facts), relabelling and `cleanup`, `<<` and `dual`. Raise in strict mode on stale or unlabelled records. Add a lint that compares each edge's declared arity or role set with its members. |
| D10 | Dependencies | hard dependencies; optional extras | HNX pins `pandas<3.0.0` while 3.0.6 is current; XGI's `DiHypergraph` is marked experimental | Optional extras (`khg-contracts[xgi]`, `khg-contracts[hypernetx]`), pinned to the probed versions, with this probe suite re-run in CI whenever a pin moves. |
| D11 | Output order | library order; canonical order | XGI's order depends on the hash seed (4 outputs from 4 seeds) | Emit in a canonical order (source order, or sorted by typed id). Tests compare structure, not bytes; `probe_common.diff_hif` can seed that check. |
| D12 | Upstream contributions | none; issues; pull requests | Section 7.5 | File the XGI and HNX issues and PRs of section 7.5, and send the HIF points to the proposal. Never make the gate depend on them. |

## 10. Licences

- **XGI 0.10.2** is under the 3-clause BSD licence: "XGI is distributed with the 3-clause BSD license",
  "Copyright (C) 2021-2025, XGI Developers". The same `LICENSE.md` also carries a 3-clause BSD notice for
  "Tensor methods for nonuniform hypergraphs", "Copyright 2023, 2024 Battelle Memorial Institute". The
  PyPI classifier is `License :: OSI Approved :: BSD License` [P: wheel `xgi-0.10.2.dist-info/licenses/LICENSE.md`
  and `METADATA`].
- **HyperNetX 2.4.3** ships `LICENSE.rst` with the 3-clause BSD text, "Copyright 2018, 2023, 2024,
  Battelle Memorial Institute". Its `License:` metadata says "3-Clause BSD license", but its classifier
  says `License :: Other/Proprietary License`, which is inconsistent metadata; the licence text itself is
  BSD-3 [P: wheel `hypernetx-2.4.3.dist-info`].
- Both are permissive and compatible with depending on them from the MIT-licensed `khg-contracts`
  package. That is the conventional reading of BSD-3; it is not a legal opinion. Nothing from either
  library is copied into this repository; the probes only import them.

## 11. Limits of this study

- Two libraries only. HypergraphX, HAT, SimpleHypergraphs.jl and Hypergraph-DB were not probed.
- 27 small synthetic cases plus the KB sample. No scale or performance tests, apart from the HNX network
  latency.
- pandas 3 was not tested, because HNX forbids it. Whether HNX's chained `DataFrame` updates in
  `normalize_dataframe` ([hif.py:37-38](https://github.com/pnnl/HyperNetX/blob/v2.4.3/hypernetx/hif.py#L37-L38))
  would survive pandas 3 is [unverified].
- The native operations probed are a sample, not every method (no XGI statistics or drawing; no HNX
  s-components or drawing).
- `role_loaders_sketch.py` is research code. It proves the approach is feasible; it is not a reviewed
  implementation.
- Upstream issue search: the GitHub API was not enabled in this session. Issues were found through
  github.com search pages (HNX #168, #171, #173 mention HIF; no XGI issue about incidence attributes
  appeared among the 5 XGI issues matching "HIF"). A complete search is [unverified].

## Sources

- XGI source, release tag v0.10.2 (byte-identical to the PyPI wheel, checked 2026-09-23):
  `xgi/readwrite/hif.py`, `xgi/convert/hif_dict.py`, `xgi/convert/bipartite_edges.py`,
  `xgi/convert/higher_order_network.py`, `xgi/core/hypergraph.py`, `xgi/core/dihypergraph.py`,
  `xgi/core/simplicialcomplex.py`, `xgi/core/globalviews.py`, `xgi/core/views.py`,
  `xgi/utils/utilities.py`, `xgi/readwrite/xgi_data.py`. XGI Developers. https://github.com/xgi-org/xgi/tree/v0.10.2
- XGI on PyPI, version 0.10.2 (uploaded 2026-05-15), licence metadata. https://pypi.org/project/xgi/0.10.2/
- Landry, N. W., Lucas, M., Iacopini, I., Petri, G., Schwarze, A., Patania, A., Torres, L. (2023). *XGI:
  A Python package for higher-order interaction networks.* Journal of Open Source Software 8(85), 5162.
  https://doi.org/10.21105/joss.05162
- HyperNetX source, release tag v2.4.3 (byte-identical to the PyPI wheel, checked 2026-09-23):
  `hypernetx/__init__.py`, `hypernetx/hif.py`, `hypernetx/classes/hypergraph.py`,
  `hypernetx/classes/factory.py`, `hypernetx/classes/property_store.py`, `hypernetx/classes/hyp_view.py`,
  `hypernetx/classes/incidence_store.py`. Battelle Memorial Institute / PNNL.
  https://github.com/pnnl/HyperNetX/tree/v2.4.3
- HyperNetX on PyPI, version 2.4.3 (uploaded 2026-07-23), dependency and licence metadata.
  https://pypi.org/project/hypernetx/2.4.3/
- pandas on PyPI (latest version 3.0.6 on 2026-09-23). https://pypi.org/project/pandas/
- HyperNetX issue #171, "Code Fails on Import if Internet Connection is Disrupted" (opened 2025-10-21, open
  on 2026-09-23). https://github.com/pnnl/HyperNetX/issues/171
- HyperNetX issues matching "hif", including #168, "Importing hypernetx freezes while loading HIF JSON
  Schema" (closed 2025-02-15), and #173, "fastjsonschema missing from dependencies in pyproject.toml"
  (opened 2026-01-27). Listing checked 2026-09-23. https://github.com/pnnl/HyperNetX/issues?q=is%3Aissue+hif
- XGI issues matching "HIF" (5 issues, none on incidence attributes; checked 2026-09-23).
  https://github.com/xgi-org/xgi/issues?q=is%3Aissue+HIF
- HIF-standard README at commit `b691a3d2ec32100c0229ebe1151e9afad015c356` (2026-03-19). Lines 30-46
  define `incidences[].attrs` as "a dictionary-like object of all the miscellaneous incidence properties"
  and say that "Isolated nodes and empty edges can be specified with entries in "nodes" and "edges" which
  are not present in the incidences". HIF development team, MIT licence.
  https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/README.md
- HIF JSON Schema as vendored, with provenance, in [probes/hif-schema/](probes/hif-schema/README.md)
  (sibling probe for report 02). https://github.com/HIF-org/HIF-standard
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P.
  (2025). *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21.
  https://doi.org/10.1017/nws.2025.10018
- P2 research report 01, *Requirements for contracts C1, C2, C3 and C5* (this repository, 2026-09-23).
  [01-requirements-from-kb.md](01-requirements-from-kb.md)
- P2 research report 02, *HIF standard* (this repository, 2026-09-23). [02-hif-standard.md](02-hif-standard.md)
- Probe code, cases and outputs for this report (this repository, run 2026-09-23 with the versions in
  section 0.1). [probes/](probes/)
