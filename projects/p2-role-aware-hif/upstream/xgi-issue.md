---
title: "Draft: the XGI issue on HIF round trips (DESIGN §12.4)"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# Draft: the XGI issue (W14; DESIGN §12.4)

**Nothing here has been filed.** The repository owner files it from their own account (the director's ruling 2 on
DESIGN §14).

## For the owner

- **Where:** https://github.com/xgi-org/xgi/issues/new
- **When:** after khg-contracts 1.0.0 is on PyPI and the HIF issue is filed ([RELEASE.md](RELEASE.md),
  [hif-issue.md](hif-issue.md)); replace `<HIF issue>` with its link.
- **Attach** `tests/evidence/library-hif-evidence.json` from the tag `khg-contracts-v1.0.0` (DESIGN §12.4: every
  library issue attaches it). If GitHub refuses the upload, the permalink in the text is enough.
- **Checked on 2026-09-23:** every output below comes from xgi 0.10.2 (Python 3.11.15, Linux), run offline; every
  line reference was read in the installed 0.10.2 source, which [research/03-library-probes.md](../research/03-library-probes.md)
  §0.1 found byte-identical to the tag `v0.10.2` and to `main`. Re-run the reproducer before filing if XGI has
  released since.
- **Scope.** The five points of DESIGN §12.4 for XGI: incidence `attrs` and weights; repeated records; clear
  direction errors; no splatting of `attrs`; deterministic order. The loaders of `khg-contracts` never call
  `read_hif` or `write_hif` (F1), so nothing in the package waits for a fix.

## Title

HIF round trip drops incidence attrs, weights and repeated incidence records (read_hif / write_hif, 0.10.2)

## Body

Paste everything inside the fence.

````markdown
Thank you for XGI and for supporting HIF. We use HIF to exchange knowledge hypergraphs (n-ary facts), where each
incidence carries the role its node plays in its edge, in `incidences[].attrs.role`, and a node may appear in one
edge under two roles. We proposed this as a convention to HIF, with no schema change (<HIF issue>). With xgi 0.10.2,
`xgi.read_hif` followed by `xgi.write_hif` loses most of it. Here are five points, each with a reproducer below and
the line it comes from (line numbers at tag `v0.10.2`; `main` has the same HIF modules).

**Evidence file.** `library-hif-evidence.json` (attached; also at
https://github.com/pluton74mac/knowledge-Hyper-Graphs-/blob/khg-contracts-v1.0.0/tests/evidence/library-hif-evidence.json)
records `read_hif` then `write_hif` on four role-carrying files: incidence records in → out, and roles kept.

| File | Class | Records | Roles kept |
|---|---|---|---|
| a 59-incidence knowledge-hypergraph test file | `Hypergraph` | 59 → 56 | 0 of 59 |
| its directed slice | `DiHypergraph` | 52 → 51 | 0 of 52 |
| `tail-head` (one node in the tail and the head of one edge) | `DiHypergraph` | 3 → 3 | 0 of 3 |
| `ordered` (one node at two positions of a route) | `Hypergraph` | 4 → 3 | 0 of 4 |

### 1. Incidence `attrs` and every record-level `weight` are dropped

`tail-head` comes back with 3 records and no `attrs`; a file with a node weight, an edge weight and an incidence
weight comes back with none. The reader's incidence loop reads only `node`, `edge` and `direction`
(`xgi/convert/hif_dict.py` 150-159), the writer emits only those (85-94), and the string `weight` does not occur in
either HIF module. HIF defines `weight` on nodes, edges and incidences and `attrs` on incidences.

*Ask:* round-trip incidence `attrs` and weights, for example with an optional incidence-attribute mapping returned
beside the hypergraph, or an incidence-attribute store; at least, document that they are dropped.

### 2. Repeated incidence records collapse

The HIF schema accepts several records for one (edge, node) pair, and the repository's own compliant
`duplicated_nodes_edges.json` has one; whether the formal model's incidence set allows it is asked in
<HIF issue>. `ordered` loses its second `YYZ` stop (4 → 3), and a node with two roles in one edge loses one (3 → 2).
Members are sets (`xgi/core/hypergraph.py` 1110-1117). A `DiHypergraph` does keep one node in both `"in"` and
`"out"` (`tail-head` 3 → 3), so only the undirected case, and the same-direction case, collapse.

*Ask:* keep repeated records together with point 1, or document that a pair is kept once.

### 3. Direction errors are unclear or silent

In a directed file, an incidence without `direction` raises `KeyError: 'direction'` (`hif_dict.py` 155), and any
value other than `"tail"`, such as a typo, silently becomes head (`hif_dict.py` 134).

*Ask:* raise a clear error naming the incidence when `direction` is missing or not `"head"`/`"tail"`.

### 4. `attrs` are splatted into keyword arguments

A node whose `attrs` has a key `node`, or an edge whose `attrs` has `members` or `idx`, cannot be read:
`TypeError: Hypergraph.add_node() got multiple values for argument 'node'` (`hif_dict.py` 171:
`H.add_node(n, **attr)`; 184: `H.add_edge(..., e, **attr)`). These are ordinary attribute names in other
libraries' data.

*Ask:* add the node or edge, then set its attributes from the dict (for example with `set_node_attributes`).

### 5. The output order depends on `PYTHONHASHSEED`

Writing one 24-incidence file under `PYTHONHASHSEED` 0, 1, 2 and 3 gives four different files. The incidences come
from set iteration (`xgi/convert/bipartite_edges.py` 64-73), and the node and edge records from set unions
(`hif_dict.py` 56-72).

*Ask:* write in a deterministic order (the input order, or sorted), so that files can be diffed and hashed.

### Reproducer

```python
import hashlib, json, os, subprocess, sys, tempfile
import xgi

def roundtrip(doc):
    with tempfile.TemporaryDirectory() as d:
        src, out = os.path.join(d, "in.json"), os.path.join(d, "out.json")
        with open(src, "w") as fh:
            json.dump(doc, fh)
        H = xgi.read_hif(src)
        xgi.write_hif(H, out)
        with open(out) as fh:
            return H, json.load(fh)

tail_head = {"network-type": "directed", "metadata": {"role-convention": "1.0.0"}, "incidences": [
    {"edge": "reg-1", "node": "TP53", "direction": "tail", "attrs": {"role": "regulator"}},
    {"edge": "reg-1", "node": "TP53", "direction": "head", "attrs": {"role": "target"}},
    {"edge": "reg-1", "node": "HeLa", "direction": "tail", "attrs": {"role": "context"}}]}
H, out = roundtrip(tail_head)
print(type(H).__name__, len(out["incidences"]), [i.get("attrs") for i in out["incidences"]])
# DiHypergraph 3 [None, None, None]

weights = {"nodes": [{"node": "TP53", "weight": 3}], "edges": [{"edge": "reg-1", "weight": 0.5}],
           "incidences": [{"edge": "reg-1", "node": "TP53", "weight": 0.25}, {"edge": "reg-1", "node": "HeLa"}]}
H, out = roundtrip(weights)
print(sum("weight" in r for k in ("nodes", "edges", "incidences") for r in out.get(k, [])))
# 0

ordered = {"incidences": [
    {"edge": "route-1", "node": "AC", "attrs": {"role": "carrier"}},
    {"edge": "route-1", "node": "YYZ", "attrs": {"role": "stop", "role-position": 1}},
    {"edge": "route-1", "node": "YUL", "attrs": {"role": "stop", "role-position": 2}},
    {"edge": "route-1", "node": "YYZ", "attrs": {"role": "stop", "role-position": 3}}]}
two_roles = {"incidences": [
    {"edge": "sale-2", "node": "alice", "attrs": {"role": "buyer"}},
    {"edge": "sale-2", "node": "alice", "attrs": {"role": "payer"}},
    {"edge": "sale-2", "node": "bob", "attrs": {"role": "seller"}}]}
print(len(roundtrip(ordered)[1]["incidences"]), len(roundtrip(two_roles)[1]["incidences"]))
# 3 2

for doc in ({"network-type": "directed", "incidences": [
                {"edge": "e1", "node": "a", "direction": "tail"}, {"edge": "e1", "node": "b"}]},
            {"nodes": [{"node": "iso", "attrs": {"node": "x"}}], "incidences": [{"edge": "e1", "node": "a"}]},
            {"edges": [{"edge": "empty", "attrs": {"members": ["x"], "idx": 7}}],
             "incidences": [{"edge": "e1", "node": "a"}]}):
    try:
        roundtrip(doc)
    except Exception as e:
        print(type(e).__name__, e)
# KeyError 'direction'
# TypeError Hypergraph.add_node() got multiple values for argument 'node'
# TypeError Hypergraph.add_edge() got multiple values for argument 'members'

H, out = roundtrip({"network-type": "directed", "incidences": [
    {"edge": "e1", "node": "a", "direction": "tail"}, {"edge": "e1", "node": "b", "direction": "treatment"}]})
print(H.edges.dimembers("e1"))
# ({'a'}, {'b'})

big = {"incidences": [{"edge": "e1", "node": f"n{k}"} for k in range(12)]
       + [{"edge": "e2", "node": f"m{k}"} for k in range(12)]}
code = ("import json, os, tempfile, hashlib, xgi\n"
        "d = tempfile.mkdtemp(); src, out = os.path.join(d, 'in.json'), os.path.join(d, 'out.json')\n"
        f"json.dump({big!r}, open(src, 'w'))\n"
        "xgi.write_hif(xgi.read_hif(src), out)\n"
        "print(hashlib.sha256(open(out, 'rb').read()).hexdigest()[:16])\n")
print({s: subprocess.run([sys.executable, "-c", code], env=dict(os.environ, PYTHONHASHSEED=s),
                         capture_output=True, text=True).stdout.strip() for s in "0123"})
# four different digests
```

Environment: xgi 0.10.2, Python 3.11.15, Linux. The evidence file is written by
`tests/evidence/test_library_hif_io.py` of https://github.com/pluton74mac/knowledge-Hyper-Graphs- (khg-contracts
1.0.0), which builds XGI objects with the public constructors instead (`add_node`, `add_edge`, `add_node_to_edge`,
`set_*_attributes`) and keeps incidence records beside the hypergraph. We are glad to help with a PR for any of
these.
````
