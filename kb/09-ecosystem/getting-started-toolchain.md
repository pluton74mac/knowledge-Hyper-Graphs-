---
title: Getting started - a recommended toolchain for this knowledge base
type: howto
status: draft
tags: [ecosystem, howto, toolchain, HIF, python, rdflib, xgi, hypernetx, hypergraphx]
created: 2026-09-20
updated: 2026-09-20
---

# Getting started: a recommended toolchain

A minimal, **actually executed** setup for working with knowledge hypergraphs in this
repository. Everything below was run on **2026-09-20** on Linux with CPython **3.11.15**; the
exact versions resolved are recorded so a future reader can tell whether behaviour changed
because of the code or because of the dependencies.

---

## 1. The recommendation in one paragraph

Use **Python** for everything analytical. Install `xgi`, `hypernetx` and `hypergraphx` together —
they are small, pure-Python and complementary, and all three read HIF. Add `rdflib` for the
semantic-web bridge and `fastjsonschema` to validate HIF files. Add `dhg` and `torch-geometric`
only when you actually need to train something, because they pull in PyTorch. For JavaScript
visualisation use **D3** directly. For a database, choose **Oxigraph** if your facts fit
RDF-with-qualifiers, or **TypeDB** if you need genuine n-ary relations with named roles; the
trade-off is set out in
[../10-comparative-and-critique/property-graph-vs-typedb-vs-rdf-star.md](../10-comparative-and-critique/property-graph-vs-typedb-vs-rdf-star.md).

---

## 2. Core install (verified)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install hypernetx xgi hypergraphx rdflib fastjsonschema jsonschema
```

Resolved on 2026-09-20 with Python 3.11.15. Direct dependencies:

| Package | Version |
|---|---|
| `hypernetx` | 2.4.3 |
| `xgi` | 0.10.2 |
| `hypergraphx` | 1.8.0 |
| `rdflib` | 7.6.0 |
| `fastjsonschema` | 2.22.2 |
| `jsonschema` | 4.26.0 |

Pulled in transitively (the ones worth pinning): `networkx` 3.6.1, `numpy` 2.4.6, `scipy` 1.17.1,
`pandas` 2.3.3, `matplotlib` 3.11.2, `scikit-learn` 1.9.1, `igraph` 1.0.0, `requests` 2.34.2.
Resulting virtualenv size: **559 MB** (dominated by SciPy, scikit-learn and matplotlib).

No compiler is required and nothing is fetched from a non-PyPI source.

### Optional: learning stack

```bash
pip install dhg                 # 0.9.7 (2026-08-02); pulls in PyTorch
pip install torch-geometric     # 2.8.0.post1 (2026-07-20); needs torch installed first
pip install toponetx topoembedx # 0.4.0, 0.3.0
pip install git+https://github.com/pyt-team/TopoModelX   # PyPI still shows 0.0.1 from 2024-10-20
```

These were **not** installed in the verification run (PyTorch is multi-gigabyte); the versions
above come from the PyPI JSON API on 2026-09-20. Details in
[software-libraries.md](software-libraries.md).

### Optional: databases

```bash
pip install pyoxigraph          # 0.5.11 (2026-09-02) - embedded SPARQL store, supports RDF-star
# or run the server:
docker run --rm -p 7878:7878 ghcr.io/oxigraph/oxigraph serve --location /data
```

For TypeDB, use the official distribution and the `typedb-driver` package for your language
(crate 3.12.3, 2026-08-11; server releases page shows 3.13.0).

---

## 3. Vendor the HIF schema — do not fetch it at run time

```bash
mkdir -p schemas
curl -sSL -o schemas/hif_schema.json \
  https://raw.githubusercontent.com/HIF-org/HIF-standard/main/schemas/hif_schema.json
```

Three different URLs for "the" HIF schema are in circulation and the published schema declares
`"version": "latest"` rather than a version number; HyperNetX fetches a fourth URL at import
time. See [standards-bodies-and-specifications.md](standards-bodies-and-specifications.md).
Vendoring the schema is the only way to make validation reproducible. (The file is *not*
committed to this repository; fetch it into an untracked `schemas/hif_schema.json` when you
need it.)

---

## 4. Hello, hyperedges

Save as `hello_hif.py` in the repository root and run
`python hello_hif.py schemas/sample.hif.json`. It reads
[../../schemas/sample.hif.json](../../schemas/sample.hif.json), validates it, loads it into all
three libraries and bridges it into RDF.

```python
#!/usr/bin/env python3
"""Load a HIF file with three hypergraph libraries, print its hyperedges, and
bridge it into RDF.  Usage:  python hello_hif.py schemas/sample.hif.json"""
import json
import sys
from pathlib import Path

HIF = Path(sys.argv[1] if len(sys.argv) > 1 else "schemas/sample.hif.json")
raw = json.loads(HIF.read_text(encoding="utf-8"))

# -- 0. the file itself: hyperedges with roles, no library needed ------------
print(f"# {HIF}  network-type={raw.get('network-type')}")
print(f"# {len(raw.get('nodes', []))} nodes, {len(raw.get('edges', []))} edges, "
      f"{len(raw['incidences'])} incidences\n")
roles, edge_attrs = {}, {e["edge"]: e.get("attrs", {}) for e in raw.get("edges", [])}
for inc in raw["incidences"]:
    roles.setdefault(inc["edge"], []).append(
        (inc["node"], inc.get("direction", "-"), inc.get("attrs", {}).get("role", "-")))
for eid, members in roles.items():
    print(f"{eid}  relation={edge_attrs.get(eid, {}).get('relation', '?')}  "
          f"arity={len(members)}")
    for node, direction, role in members:
        print(f"    [{direction:>4}] {role:<12} {node}")
print()

# -- 1. validate against a vendored copy of the HIF schema ------------------
import fastjsonschema
SCHEMA = Path("schemas/hif_schema.json")
if SCHEMA.exists():
    try:
        fastjsonschema.compile(json.loads(SCHEMA.read_text()))(raw)
        print("HIF validation: OK")
    except Exception as exc:                      # noqa: BLE001
        print(f"HIF validation: FAILED - {exc}")
else:
    print(f"HIF validation: skipped (vendor the schema at {SCHEMA})")

# -- 2. XGI -----------------------------------------------------------------
import xgi
Hx = xgi.read_hif(HIF)
print(f"\nxgi         {xgi.__version__}: {type(Hx).__name__}, "
      f"{Hx.num_nodes} nodes, {Hx.num_edges} edges")
for eid, members in Hx.edges.members(dtype=dict).items():
    print(f"    {eid}: {sorted(members)}")

# -- 3. HyperNetX -----------------------------------------------------------
import hypernetx as hnx
Hn = hnx.from_hif(filename=str(HIF))
print(f"hypernetx   {hnx.__version__}: {type(Hn).__name__}, "
      f"{len(Hn.nodes)} nodes, {len(Hn.edges)} edges")
for eid in Hn.edges:
    print(f"    {eid}: {sorted(Hn.edges[eid])}")

# -- 4. Hypergraphx ---------------------------------------------------------
import hypergraphx
from hypergraphx.readwrite import read_hif
Hg = read_hif(str(HIF))
print(f"hypergraphx {hypergraphx.__version__}: {type(Hg).__name__}, "
      f"{Hg.num_nodes()} nodes, {Hg.num_edges()} edges "
      f"(node ids re-indexed to integers; originals in metadata)")
for e in Hg.get_edges():
    labels = [Hg.get_node_metadata(n)["node"] for n in e]
    print(f"    {e} -> {labels}")

# -- 5. rdflib bridge: one hyperedge -> role-per-predicate reification ------
import rdflib
from rdflib import Graph, Namespace, Literal, RDF, URIRef
KHG = Namespace("https://example.org/khg#")
g = Graph(); g.bind("khg", KHG)
for eid, members in roles.items():
    fact = KHG[eid]
    g.add((fact, RDF.type, KHG.Fact))
    g.add((fact, KHG.relation, Literal(edge_attrs.get(eid, {}).get("relation", "?"))))
    for node, _direction, role in members:
        g.add((fact, KHG[role], URIRef("https://example.org/khg/" + node.replace(":", "/"))))
print(f"rdflib      {rdflib.__version__}: {len(g)} triples from {len(roles)} hyperedges")
```

### Actual output (2026-09-20)

```text
# schemas/sample.hif.json  network-type=directed
# 8 nodes, 3 edges, 9 incidences

f1  relation=treats  arity=4
    [tail] treatment    drug:metformin
    [head] condition    disease:T2DM
    [tail] dosage       dose:500mg-bid
    [tail] population   pop:adults
f2  relation=co-administration-causes  arity=3
    [tail] agent        drug:metformin
    [tail] agent        drug:insulin
    [head] effect       effect:hypoglycemia
f3  relation=publishes  arity=2
    [tail] publisher    org:ADA
    [head] publication  doc:guideline-2024

HIF validation: OK

xgi         0.10.2: DiHypergraph, 8 nodes, 3 edges
    f1: ['disease:T2DM', 'dose:500mg-bid', 'drug:metformin', 'pop:adults']
    f2: ['drug:insulin', 'drug:metformin', 'effect:hypoglycemia']
    f3: ['doc:guideline-2024', 'org:ADA']
hypernetx   2.4.3: Hypergraph, 8 nodes, 3 edges
    f1: ['disease:T2DM', 'dose:500mg-bid', 'drug:metformin', 'pop:adults']
    f2: ['drug:insulin', 'drug:metformin', 'effect:hypoglycemia']
    f3: ['doc:guideline-2024', 'org:ADA']
hypergraphx 1.8.0: Hypergraph, 8 nodes, 3 edges (node ids re-indexed to integers; originals in metadata)
    (0, 1, 2, 3) -> ['drug:metformin', 'disease:T2DM', 'dose:500mg-bid', 'pop:adults']
    (0, 4, 5) -> ['drug:metformin', 'drug:insulin', 'effect:hypoglycemia']
    (6, 7) -> ['org:ADA', 'doc:guideline-2024']
rdflib      7.6.0: 15 triples from 3 hyperedges
```

---

## 5. What the output teaches, before you write any real code

1. **Only XGI preserves direction.** The sample file declares `"network-type": "directed"` and
   carries `head`/`tail` on every incidence. XGI returns a `DiHypergraph`; HyperNetX and
   Hypergraphx both return an undirected `Hypergraph`. If your facts are directed, XGI is the
   only one of the three that will not silently lose that.
2. **Roles survive nowhere.** All three libraries load the hyperedges; none of them exposes the
   `incidences[].attrs.role` values that make these facts n-ary rather than just sets. Section 0
   of the script reads them from the raw JSON because there is no library API for it. This is the
   single biggest practical gap between "hypergraph library" and "knowledge hypergraph library".
3. **Identifiers are not stable across libraries.** Hypergraphx re-indexes nodes to integers;
   the original ids live in `get_node_metadata(n)["node"]`. Any cross-library pipeline needs an
   explicit id mapping.
4. **The RDF bridge loses the hyperedge.** Fifteen triples for three facts: each n-ary fact
   becomes a reification node with one predicate per role. That round-trips, but the "one fact =
   one edge" property is gone, which is precisely the argument in
   [../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md).

---

## 6. Suggested working pattern for this repository

| Task | Tool |
|---|---|
| author or hand-edit a small knowledge hypergraph | HIF JSON, validated with the vendored schema |
| structural analysis, centrality, communities, motifs | `hypergraphx` |
| directed hypergraphs, generative models, quick drawings | `xgi` |
| property-rich hypergraphs, `s`-line-graph analysis | `hypernetx` |
| RDF / SPARQL export and interchange | `rdflib` for parsing and serialising; `pyoxigraph`, Jena or RDF4J when RDF-star is needed (`rdflib` 7.6.0 cannot parse it) |
| learning | `dhg` for HGNN-family models; `torch-geometric` when the rest of the pipeline is already PyG |
| browser visualisation | D3 with the encodings catalogued in [../06-visualization/visual-encodings-catalogue.md](../06-visualization/visual-encodings-catalogue.md) |
| datasets | manifests in [../../datasets/README.md](../../datasets/README.md); catalogues in [datasets-and-benchmarks.md](datasets-and-benchmarks.md) |

---

## 7. Reproducibility checklist

- Pin the six direct dependencies above and record the Python version.
- Vendor the HIF schema; never validate against a `main`-branch URL.
- Record a checksum for every dataset file you load — see
  [dataset-quality-and-leakage-issues.md](dataset-quality-and-leakage-issues.md).
- Run a leakage check before reporting any link-prediction number.
- Re-run this note's script after any dependency bump: if the three library types in the output
  change, an interchange assumption has broken.

---

## Sources

- Local execution log, 2026-09-20: CPython 3.11.15 virtualenv, `pip install hypernetx xgi hypergraphx rdflib fastjsonschema jsonschema`, resolved versions and `pip list` output as tabulated above; `hello_hif.py` output reproduced verbatim.
- HIF schema, <https://raw.githubusercontent.com/HIF-org/HIF-standard/main/schemas/hif_schema.json>, retrieved 2026-09-20 and used for the validation step.
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. (2025). *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21. <https://doi.org/10.1017/nws.2025.10018>
- PyPI JSON API and crates.io API, queried 2026-09-20, for the optional-stack version numbers (`dhg` 0.9.7, `torch-geometric` 2.8.0.post1, `toponetx` 0.4.0, `topoembedx` 0.3.0, `topomodelx` 0.0.1, `pyoxigraph` 0.5.11, `typedb-driver` 3.12.3).
- XGI documentation, <https://xgi.readthedocs.io>; HyperNetX documentation, <https://hypernetx.readthedocs.io>; Hypergraphx documentation, <https://hypergraphx.readthedocs.io>; all checked 2026-09-20.
