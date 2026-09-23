---
title: "Draft: the HyperNetX issue on HIF round trips (DESIGN §12.4)"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# Draft: the HyperNetX issue (W14; DESIGN §12.4)

**Nothing here has been filed.** The repository owner files it from their own account (the director's ruling 2 on
DESIGN §14).

## For the owner

- **Where:** https://github.com/pnnl/HyperNetX/issues/new
- **When:** after khg-contracts 1.0.0 is on PyPI and the HIF issue is filed ([RELEASE.md](RELEASE.md),
  [hif-issue.md](hif-issue.md)); replace `<HIF issue>` with its link.
- **Attach** `tests/evidence/library-hif-evidence.json` from the tag `khg-contracts-v1.0.0` (DESIGN §12.4). If GitHub
  refuses the upload, the permalink in the text is enough.
- **Checked on 2026-09-23:** every output below comes from hypernetx 2.4.3 with pandas 2.3.3 (Python 3.11.15, Linux).
  The runs were offline: `requests.get` returned the vendored `hif_schema_v0.1.0.json` (sha256 `639466b7…2196`), the
  file HyperNetX's `schema_url` resolved to on that day ([research/02-hif-standard.md](../research/02-hif-standard.md)
  §4). Every line reference was read in the installed 2.4.3 source, which
  [research/03-library-probes.md](../research/03-library-probes.md) §0.1 found byte-identical to the tag `v2.4.3`
  and to `master` and `develop`. Re-run the reproducer before filing if HyperNetX has released since.
- **Related issues:** #171 (network access; open on 2026-09-23), #168 and #173 mention HIF. Check for duplicates
  first.
- **Scope.** The nine points of DESIGN §12.4 for HyperNetX, plus `rename`, which W7 found also loses the isolated
  node (impl-notes/W7.md, "Observations"). The loaders of `khg-contracts` never call `from_hif` or `to_hif` (F1) and
  work around the rest, so nothing in the package waits for a fix.

## Title

HIF import/export: repeated incidences, metadata and isolated nodes lost; directed files cannot be read back; errors return None (2.4.3)

## Body

Paste everything inside the fence.

````markdown
Thank you for HyperNetX and for supporting HIF, and for keeping incidence `attrs` as cell properties: of the libraries
we tried, HyperNetX is the one that keeps roles. We exchange knowledge hypergraphs (n-ary facts) as HIF, where each
incidence carries the role its node plays in its edge (`incidences[].attrs.role`), a node may have two roles in one
edge, and one node may be in both the tail and the head of an edge. We proposed this as a convention to HIF, with no
schema change (<HIF issue>). With hypernetx 2.4.3, `from_hif` and `to_hif` lose or break several parts of such
files. Nine points follow, each with a reproducer below and the line it comes from (at tag `v2.4.3`).

**Evidence file.** `library-hif-evidence.json` (attached; also at
https://github.com/pluton74mac/knowledge-Hyper-Graphs-/blob/khg-contracts-v1.0.0/tests/evidence/library-hif-evidence.json)
records `from_hif` then `to_hif` (then both again) on four role-carrying files:

| File | Records in → out | Metadata | Second round |
|---|---|---|---|
| a 59-incidence knowledge-hypergraph test file; 52 incidences have a direction | `to_hif` returns `None` | | |
| its directed slice | 52 → 50 | all 12 keys lost; `default_attrs` added | `None` |
| `tail-head` (one node in the tail and the head of one edge) | 3 → 2 | `role-convention` lost; `default_attrs` added | `None` |
| `ordered` (one node at two positions of a route) | 4 → 3 | `role-convention` lost; `default_attrs` added | 3 |

### 1. The schema is downloaded on every call (#171)

`from_hif` and `to_hif` fetch `schema_url` with `requests.get` each time (`hypernetx/hif.py` 63, 136), so neither
works offline: they raise `ConnectionError`. *Ask:* ship the schema with the package (it is MIT-licensed), as #171
suggests, and let callers skip validation.

### 2. Validation errors are constructed, not raised

On a schema-invalid input `from_hif` returns `None`, and when its own output fails the schema `to_hif` returns `None`,
with no exception and no message: `HyperNetXError(ex)` is created without `raise` (`hif.py` 107-113, 141-152).
*Ask:* `raise` it.

### 3. `metadata` is dropped

Every metadata key except `name` is lost on import: the directed slice loses all 12 of its keys, and the two small
files lose `role-convention` (`hif.py` 162-191 reads only `name` and `default_attrs`). *Ask:* keep `metadata` and
write it back.

### 4. `default_attrs` with `direction: null` breaks the second round

`to_hif` always writes `metadata.default_attrs`, which for a directed file includes
`"incidences": {"weight": 1, "direction": null, "attrs": {}}` (`hif.py` 67-73). On re-import `from_hif` treats every
key of `default_attrs` other than `weight` and `attrs` as a column default and overwrites the real `direction` of
every row with `None` (`hif.py` 163-178). So HyperNetX cannot read its own directed output back: the second `to_hif`
returns `None` (points 2 and 5). *Ask:* do not write a `null` direction default, or do not read `default_attrs` keys
over existing columns.

### 5. `fillna("nil")` makes mixed files invalid

HIF allows `direction` on some incidences of a file and not on others. The missing values become the string `"nil"`
(`hif.py` 39), which the schema refuses, so `to_hif` returns `None` for any file with some directions missing, like
our 59-incidence file. *Ask:* drop `fillna("nil")` and omit `direction` where it is missing.

### 6. Isolated nodes and empty edges are not exported

HIF says isolated nodes and empty edges are written as `nodes` and `edges` entries without incidences. `from_hif`
keeps them in the property stores, but the views (`hypernetx/classes/hyp_view.py` 122-136), and so `to_hif`, show
only incident items: a node `iso` and an edge `empty` disappear. *Ask:* export them from the property stores.

### 7. Repeated incidence records are dropped

HIF allows several records for one (edge, node) pair (the standard's own compliant `duplicated_nodes_edges.json` has
one). The factory keeps the first row of a pair (`hypernetx/classes/factory.py` 87:
`dfp[~dfp.index.duplicated(keep="first")]`), whatever `aggregate_by` says: `tail-head` 3 → 2 (the `head`/`target`
record of TP53 goes), `ordered` 4 → 3, and a node with two roles keeps one. *Ask:* keep the other records, for
example in a reserved cell property, or document that a pair keeps its first record.

### 8. `misc_node_properties_col` and `misc_edge_properties_col` are silently ignored

`Hypergraph(...)` accepts both keywords (`hypernetx/classes/hypergraph.py` 300, 305), but nothing reads them: with
`misc_node_properties_col="attrs"` the node attrs stay in a plain `attrs` column and `misc_properties` stays empty,
exactly as with no keyword. Only the shared `misc_properties_col` works. *Ask:* honour them, or remove them and say
that `misc_properties_col` applies to nodes and edges.

### 9. `clone()`, `rename()` and `sum()` lose isolated nodes

An isolated node declared in `node_properties` is in the node property store, but `clone()`, `rename(...)` and
`sum(...)` return hypergraphs whose store no longer has it. *Ask:* carry the property stores over whole.

### Reproducer

Run with network access (point 1 is shown last, by cutting it).

```python
import pandas as pd
import requests
import hypernetx as hnx

tail_head = {"network-type": "directed", "metadata": {"role-convention": "1.0.0"}, "incidences": [
    {"edge": "reg-1", "node": "TP53", "direction": "tail", "attrs": {"role": "regulator"}},
    {"edge": "reg-1", "node": "TP53", "direction": "head", "attrs": {"role": "target"}},
    {"edge": "reg-1", "node": "HeLa", "direction": "tail", "attrs": {"role": "context"}}]}
ordered = {"network-type": "undirected", "metadata": {"role-convention": "1.0.0"}, "incidences": [
    {"edge": "route-1", "node": "AC", "attrs": {"role": "carrier"}},
    {"edge": "route-1", "node": "YYZ", "attrs": {"role": "stop", "role-position": 1}},
    {"edge": "route-1", "node": "YUL", "attrs": {"role": "stop", "role-position": 2}},
    {"edge": "route-1", "node": "YYZ", "attrs": {"role": "stop", "role-position": 3}}]}
mixed = {"network-type": "undirected", "incidences": [
    {"edge": "cause-1", "node": "metformin", "direction": "tail", "attrs": {"role": "agent"}},
    {"edge": "cause-1", "node": "hypoglycaemia", "direction": "head", "attrs": {"role": "effect"}},
    {"edge": "marriage-1", "node": "maria", "attrs": {"role": "spouse"}},
    {"edge": "marriage-1", "node": "pierre", "attrs": {"role": "spouse"}}]}
isolated = {"nodes": [{"node": "a"}, {"node": "iso"}], "edges": [{"edge": "e1"}, {"edge": "empty"}],
            "incidences": [{"edge": "e1", "node": "a"}]}

out = hnx.to_hif(hnx.from_hif(tail_head), network_type="directed")
print(len(out["incidences"]), sorted(out["metadata"]), out["metadata"]["default_attrs"]["incidences"])
# 2 ['default_attrs'] {'weight': 1, 'direction': None, 'attrs': {}}
print(hnx.to_hif(hnx.from_hif(out), network_type="directed"))
# None
print(len(hnx.to_hif(hnx.from_hif(ordered))["incidences"]))
# 3
print(hnx.to_hif(hnx.from_hif(mixed)))
# None
print(hnx.from_hif({"incidences": [{"edge": "e1", "node": "a"}], "version": "1.0"}))
# None
out = hnx.to_hif(hnx.from_hif(isolated))
print([n["node"] for n in out["nodes"]], [e["edge"] for e in out["edges"]])
# ['a'] ['e1']

cells = pd.DataFrame([{"edge": "e1", "node": "a", "attrs": {"role": "r1"}}])
nodes = pd.DataFrame([{"node": "a", "attrs": {"label": "A"}}])
for kw in ({"misc_properties_col": "attrs"}, {"misc_node_properties_col": "attrs"}):
    h = hnx.Hypergraph(cells, edge_col="edge", node_col="node", misc_cell_properties_col="attrs",
                       node_properties=nodes, **kw)
    print(kw, h.nodes.property_store.properties.loc["a"].to_dict())
# {'misc_properties_col': 'attrs'} {'weight': 1, 'misc_properties': {'label': 'A'}}
# {'misc_node_properties_col': 'attrs'} {'weight': 1, 'attrs': {'label': 'A'}, 'misc_properties': {}}

def graph():
    return hnx.Hypergraph(pd.DataFrame([{"edge": "e1", "node": "a"}, {"edge": "e1", "node": "b"}]),
                          edge_col="edge", node_col="node",
                          node_properties=pd.DataFrame([{"node": "a"}, {"node": "b"}, {"node": "iso"}]))

def held(h):
    return sorted(h.nodes.property_store.properties.index)

subset = hnx.Hypergraph(pd.DataFrame([{"edge": "e1", "node": "a"}]), edge_col="edge", node_col="node")
print(held(graph()), held(graph().clone()), held(graph().rename(nodes={"a": "a2"})), held(graph().sum(subset)))
# ['a', 'b', 'iso'] ['a', 'b'] ['a2', 'b'] ['a', 'b']

def no_network(*args, **kwargs):
    raise requests.exceptions.ConnectionError("no network")

requests.get = no_network
try:
    hnx.from_hif(tail_head)
except Exception as e:
    print(type(e).__name__, e)
# ConnectionError no network
```

Environment: hypernetx 2.4.3, pandas 2.3.3, Python 3.11.15, Linux. The evidence file is written by
`tests/evidence/test_library_hif_io.py` of https://github.com/pluton74mac/knowledge-Hyper-Graphs- (khg-contracts
1.0.0), which builds HyperNetX objects with the public constructor instead (offline, the first record of a pair in
the cell and the others in a reserved cell property). We are glad to help with a PR for any of these.
````
