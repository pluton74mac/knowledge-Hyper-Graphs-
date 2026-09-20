---
title: Tensor and sparse-matrix representations of hypergraphs
type: concept
status: draft
tags: [incidence-matrix, adjacency-tensor, sparse, coo, csr, scipy, pytorch-geometric, dhg, hypergraphconv]
created: 2026-09-20
updated: 2026-09-20
---

# Tensor and sparse-matrix representations

Everything numerical done with a hypergraph starts by turning it into a matrix or a tensor. There
are three candidates, and only one of them scales. Checked 2026-09-20.

## 1. The incidence matrix — the one that works

For a hypergraph with `N` nodes and `M` hyperedges, the incidence matrix is
**H** ∈ {0,1}^(N x M) with `H[i,j] = 1` iff node `i` is in hyperedge `j`. Everything else is
derived:

- **W** = diag(w_1..w_M), hyperedge weights.
- **D_v** = diag(H W 1), weighted node degrees (an N x N diagonal).
- **D_e** = diag(H^T 1), hyperedge sizes (an M x M diagonal), written **B** in some papers.
- Clique-expansion adjacency: **A** = H W H^T − D_v (the subtraction removes self-loops).
- Normalised hypergraph Laplacian: **L** = I − D_v^(−1/2) H W D_e^(−1) H^T D_v^(−1/2).

Storage cost is exactly the number of incidences, `nnz(H) = Σ_j |e_j|`, independent of arity
distribution. This is the same quantity as the number of rows in the HIF `incidences` array and the
number of rows in the SQL incidence table
([relational-and-eav-storage.md](relational-and-eav-storage.md)) — three names for one object.

**Directed hypergraphs** need two matrices, **H_tail** and **H_head**, or one matrix with values in
{−1, 0, +1}. HIF's per-incidence `direction` field maps to the former; the sign convention is more
compact but cannot express a node that is both head and tail of the same edge.

**Roles** do not fit in a 0/1 matrix. The options are: one incidence matrix per role (R matrices,
each sparse), or an integer-valued **H** where the value is a role code (compact, but then **H** is
no longer a valid operand for the Laplacian formulas). Most hypergraph learning code silently drops
roles — a real gap between the knowledge-hypergraph and higher-order-network literatures.

## 2. The adjacency tensor — mathematically natural, practically unusable

For a **k-uniform** hypergraph, the natural object is an order-k adjacency tensor
**A** ∈ R^(N x N x ... x N) with `A[i_1..i_k] ≠ 0` iff `{i_1..i_k}` is a hyperedge. This is the
basis of hypergraph spectral theory
([Cooper and Dutle, "Spectra of uniform hypergraphs", *Linear Algebra and its Applications* 436(9),
2012, pp. 3268–3292](https://doi.org/10.1016/j.laa.2011.11.018)).

Two problems for storage:

1. **Non-uniformity.** A knowledge hypergraph has facts of arity 2, 3, 4, 7. An order-k tensor
   requires all edges to have size k. Padding with a dummy node changes the spectrum; splitting by
   arity gives you one tensor per arity, which is the same as the incidence matrix with extra steps.
2. **Dimensionality.** A dense order-k tensor is N^k. Even sparse, the index tuple per non-zero is
   k integers versus 2 for the incidence matrix, and every library operation has to be written for
   variable k.

Conclusion for this KB: adjacency tensors are a theory tool. Store the incidence matrix; build a
tensor per arity band only if a specific spectral method demands it. See
[../01-foundations/hypergraph-definitions.md](../01-foundations/hypergraph-definitions.md) for the
mathematical side.

## 3. Sparse layouts: COO, CSR, CSC

| Layout | Stores | Good for | Bad for |
|---|---|---|---|
| **COO** (triplet) | `(row, col, val)` arrays | construction, appending, conversion, interchange | random access, arithmetic |
| **CSR** | `indptr` (N+1), `indices` (nnz), `data` (nnz) | row slicing = "hyperedges of node i", SpMV | column slicing, in-place structural edits |
| **CSC** | column-compressed | column slicing = "nodes of hyperedge j" | row slicing |
| **DOK / LIL** | dict or list of lists | incremental building | everything else |

For a hypergraph you want **both** directions, so keep CSR(**H**) and CSR(**H**^T) — equivalently
CSR and CSC — and accept the 2x memory. This is the matrix form of "index the incidence table on
`(entity_id)` and on `(fact_id)`".

SciPy provides all of these in `scipy.sparse`, with the newer `sparray` API alongside the legacy
`spmatrix` one ([SciPy sparse reference](https://docs.scipy.org/doc/scipy/reference/sparse.html)).
The practical recipe from a HIF file:

```python
import json
from scipy.sparse import coo_array

hif = json.load(open("sample.hif.json"))
nodes = sorted({i["node"] for i in hif["incidences"]})
edges = sorted({i["edge"] for i in hif["incidences"]})
ni = {n: k for k, n in enumerate(nodes)}
ei = {e: k for k, e in enumerate(edges)}
rows = [ni[i["node"]] for i in hif["incidences"]]
cols = [ei[i["edge"]] for i in hif["incidences"]]
H = coo_array(([1] * len(rows), (rows, cols)), shape=(len(nodes), len(edges))).tocsr()
```

The `direction` and `attrs.role` fields are dropped by this recipe; carry them as parallel arrays
if you need them.

## 4. PyTorch Geometric: `hyperedge_index`

`torch_geometric.nn.conv.HypergraphConv` implements
[Bai, Zhang and Torr, "Hypergraph Convolution and Hypergraph Attention" (arXiv:1901.08150, 23
January 2019)](https://arxiv.org/abs/1901.08150), with the propagation rule

X' = D^(−1) H W B^(−1) H^T X Θ

where "**H** is the incidence matrix, **W** is the diagonal hyperedge weight matrix, and **D**,
**B** are degree matrices" ([PyG HypergraphConv docs](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.conv.HypergraphConv.html),
checked 2026-09-20).

The storage detail that matters: PyG does **not** take a matrix. It takes `hyperedge_index` of
shape `(2, E)` where `E` is the number of *incidences*, documented as "The hyperedge indices, i.e.
the sparse incidence matrix H ∈ {0,1}^(N x M) mapping from nodes to edges". Row 0 holds node
indices, row 1 holds hyperedge indices. Nodes `{0,1,2}` in edge 0 and `{1,2,3}` in edge 1 become:

```python
hyperedge_index = torch.tensor([[0, 1, 2, 1, 2, 3],
                                [0, 0, 0, 1, 1, 1]])
```

That is **COO with the values dropped** — and it is column-for-column the HIF `incidences` array
with the IDs integer-encoded. Optional `hyperedge_weight` (length M) supplies **W**;
`hyperedge_attr` (M x F) is required only when `use_attention=True`.

Practical consequence: the pipeline HIF -> `hyperedge_index` is a dictionary lookup and two lists.
There is no reason for a KHG project to keep a separate "ML format".

## 5. DHG (DeepHypergraph)

DHG is a PyTorch library for graph and hypergraph neural networks, version 0.9.7 released
2026-08-02 (the README's news entry, and PyPI upload date 2026-08-02). Its `Hypergraph` structure
differs from PyG in three ways worth knowing:

- **The raw store is a hyperedge list, not a matrix.** `state_dict()` returns
  `{"num_v": ..., "raw_groups": ...}`, and hyperedges are organised into named **groups** (the
  default is `main`), so several hyperedge families can coexist in one structure
  (`dhg/structure/hypergraphs/hypergraph.py`).
- **Matrices are derived and cached, as `torch.sparse_coo_tensor`.** `H`, `H_T`, `W_v`, `W_e`,
  `D_v`, `D_e`, `D_v_neg_1`, `D_v_neg_1_2` and the `*_of_group` variants are properties that build
  and memoise sparse tensors on demand, on the structure's device.
- **Persistence is pickle.** `save()` writes `{"class": "Hypergraph", "state_dict": ...}` with
  `pickle.dump`; `load()` reads it back. No interchange format — a DHG `.pkl` is readable only by
  DHG.

It also builds hypergraphs from other structures: `from_feature_kNN` (each vertex plus its k−1
nearest neighbours becomes a hyperedge), `from_graph`, `from_graph_kHop`, `from_bigraph`. Those are
*construction* methods, relevant to
[../03-construction/from-knowledge-graphs-to-hypergraphs.md](../03-construction/from-knowledge-graphs-to-hypergraphs.md).

## 6. Scalability

Let `nnz = Σ_j |e_j|` be the incidence count.

- **Memory, COO, int32 indices, float32 values:** 12 bytes/incidence, so 100M incidences ≈ 1.2 GB.
  CSR drops one index array: ≈ 8 bytes/incidence plus `4(N+1)`.
- **Keeping both directions** (CSR + CSC) doubles it.
- **Dictionary-encoding the IDs** is mandatory at scale: string IDs dominate everything else. The
  same trick Parquet applies automatically.
- **Clique expansion is the scalability trap.** Materialising `A = H W H^T` turns a hyperedge of
  size `s` into `s(s−1)/2` entries. One hyperedge of size 1,000 — a plausible "all members of
  category C" fact — produces 499,500 entries. Never materialise the clique expansion of a KHG with
  heavy-tailed edge sizes; keep it implicit as two SpMV operations.
- **Compression beyond sparse layouts.** HyperCSA is a succinct self-index over hypergraphs
  achieving "compression ratios of 26% to 79% of the original file size on real-world hypergraphs"
  while answering neighbour queries "6 to 40 times faster than both standard data structures and
  other hypergraph compression approaches"
  ([Adler, Böttcher and Hartel, arXiv:2506.05023, 5 June 2025](https://arxiv.org/abs/2506.05023)).
  Lossless *summarisation* is a different lever: HyDRA reports "a substantial reduction in storage
  cost (80–93% in some settings)" with directly queryable summaries
  ([Preti, Anagnostopoulos and Bonchi, arXiv:2606.18274, 5 June 2026](https://arxiv.org/abs/2606.18274)).
- **Sharding** a hypergraph is hypergraph partitioning, which is what the `.hgr` format and
  KaHyPar/hMETIS exist for — see
  [versioning-provenance-and-scale.md](versioning-provenance-and-scale.md).

## 7. Round-trip checklist

A KHG that must serve analysis, learning and querying should be able to go:

```
incidence table (SQL / Parquet)
   |-> HIF JSON           (interchange; schemas/sample.hif.json)
   |-> CSR + CSC          (spectral methods, SciPy)
   |-> hyperedge_index    (PyTorch Geometric)
   |-> .hgr               (partitioning / sharding; loses roles and labels)
   `-> RDF 1.2 / JSON-LD  (standards interop; schemas/sample-n-ary-fact.ttl)
```

Only the `.hgr` arrow is lossy by construction. The others are lossless if roles and direction are
carried as parallel columns.

## Sources

- Cooper, J. and Dutle, A. (2012). *Spectra of uniform hypergraphs*. Linear Algebra and its Applications 436(9), pp. 3268–3292. https://doi.org/10.1016/j.laa.2011.11.018
- Bai, S., Zhang, F. and Torr, P. H. S. (2019). *Hypergraph Convolution and Hypergraph Attention*. arXiv:1901.08150, 23 January 2019. https://arxiv.org/abs/1901.08150
- PyTorch Geometric. *HypergraphConv* API documentation (checked 2026-09-20). https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.conv.HypergraphConv.html
- SciPy. *Sparse arrays and matrices* reference (checked 2026-09-20). https://docs.scipy.org/doc/scipy/reference/sparse.html
- DHG (DeepHypergraph) repository, `dhg/structure/hypergraphs/hypergraph.py`; README news entry for v0.9.7 dated 2026-08-02; PyPI upload 2026-08-02. https://github.com/iMoonLab/DeepHypergraph — docs https://deephypergraph.readthedocs.io/
- Adler, E., Böttcher, S. and Hartel, R. (2025). *Compressing Hypergraphs using Suffix Sorting*. arXiv:2506.05023. https://arxiv.org/abs/2506.05023
- Preti, G., Anagnostopoulos, A. and Bonchi, F. (2026). *HyDRA: Lossless Hypergraph Summarization via Co-Clustering*. arXiv:2606.18274. https://arxiv.org/abs/2606.18274
- HIF-standard schema and README (for the `incidences` array structure), checked 2026-09-20. https://github.com/pszufe/HIF-standard
