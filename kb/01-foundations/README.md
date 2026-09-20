---
title: 01 — Foundations
type: index
status: draft
tags: [foundations, hypergraph, mathematics, index]
created: 2026-09-20
updated: 2026-09-20
---

# 01 — Foundations

The mathematics under knowledge hypergraphs: what a hypergraph *is*, how it is encoded, what is
already known about it, and which neighbouring structures it is regularly confused with. Everything
here is about the bare combinatorial object; the *knowledge* layer starts in section
[02](../02-knowledge-representation/).

The section is written around one question: **which classical results survive when hyperedges
acquire identities, relation names and roles — and which do not?** The short answer is that the
computational theory (acyclicity, widths, joins, cuts, spectra) transfers almost intact, while the
representational theory has to be built from the database and knowledge-representation traditions
instead.

## Notes in this section

| Note | What it covers |
|---|---|
| [hypergraph-definitions.md](hypergraph-definitions.md) | The base definition and the variants that matter for KHGs: uniform, directed (Gallo et al. 1993), oriented, weighted, multi-, ordered/role-labelled, recursive (ubergraphs), attributed, temporal — with the textbook disagreements (Berge / Voloshin / Bretto) recorded rather than hidden. |
| [notation-cheatsheet.md](notation-cheatsheet.md) | The symbols used across this KB, the source each convention comes from, and a clash index for the letters the literature overloads (`H`, `W`, `r`, `m`, `d(v)`, `L`). |
| [incidence-and-matrix-representations.md](incidence-and-matrix-representations.md) | Incidence matrix, adjacency matrices, the five hypergraph Laplacians (Chung, Bolla, Rodríguez, Zhou–Huang–Schölkopf, Chan–Louis), adjacency tensors and Z/H eigenpairs, and the three graph expansions (clique, star, line) with a precise account of what each one loses. |
| [hypergraphs-vs-bipartite-vs-simplicial.md](hypergraphs-vs-bipartite-vs-simplicial.md) | The exact correspondences with bipartite (Levi/König) graphs, abstract simplicial complexes, cell and combinatorial complexes (Hajij et al. 2022), set systems and block designs — and why "a hypergraph is just a bipartite graph" is true but unhelpful. |
| [hypergraph-theory-results.md](hypergraph-theory-results.md) | Berge's programme, duality, transversals and hitting sets, the Helly property and conformality, the four degrees of acyclicity (Berge/γ/β/α, Fagin 1983), hypertree and fractional hypertree width (Gottlob et al.), colouring, and hypergraph cuts and partitioning (hMETIS, KaHyPar). |
| [random-walks-spectral-and-expansion.md](random-walks-spectral-and-expansion.md) | The natural random walk and why it collapses to the clique expansion, edge-dependent vertex weights, the non-linear Laplacian and the hypergraph Cheeger inequality `γ₂/2 ≤ φ_H ≤ 2√γ₂`, spectral sparsification, and the two distinct "hypergraph expander" traditions. |
| [higher-order-interactions.md](higher-order-interactions.md) | The complex-systems programme: Battiston et al. 2020, Bick et al. 2023, higher-order motifs, simplicial closure, the three tensor centralities (Benson 2019) and node-and-edge nonlinear centrality (Tudisco–Higham 2021), plus the field's own internal critique. |

## Reading order

1. **[hypergraph-definitions.md](hypergraph-definitions.md)** — start here; everything else assumes it.
2. **[notation-cheatsheet.md](notation-cheatsheet.md)** — skim, then keep open.
3. **[incidence-and-matrix-representations.md](incidence-and-matrix-representations.md)** — the encoding choices that constrain every downstream system.
4. **[hypergraphs-vs-bipartite-vs-simplicial.md](hypergraphs-vs-bipartite-vs-simplicial.md)** — settles the "why not just use X" objections.
5. Then, as needed: **[n-ary-relations-and-relational-algebra.md](n-ary-relations-and-relational-algebra.md)** for querying, **[hypergraph-theory-results.md](hypergraph-theory-results.md)** for combinatorics, **[random-walks-spectral-and-expansion.md](random-walks-spectral-and-expansion.md)** for spectra, **[higher-order-interactions.md](higher-order-interactions.md)** for the complex-systems view.

Also in this section: [n-ary-relations-and-relational-algebra.md](n-ary-relations-and-relational-algebra.md) — relations as sets of tuples (Codd 1970), the three different "hypergraphs of a database", join trees and the Yannakakis algorithm, the AGM size bound and worst-case optimal joins, and what relational theory does *not* give a knowledge hypergraph.

## Six things this section establishes

1. **There is no canonical matrix.** Every encoding is a choice, and each loses something specific ([incidence-and-matrix-representations.md](incidence-and-matrix-representations.md)).
2. **Clique expansion is lossy and sometimes badly so** — cut parameters can be distorted by a factor `Ω(r)` ([Chan et al., 2018](https://arxiv.org/abs/1605.01483)).
3. **The star/incidence/Levi encoding is lossless** but only if the two sides are labelled; unlabelled it confuses a hypergraph with its dual.
4. **Simplicial complexes are hypergraphs plus downward closure**, and downward closure is factually wrong for n-ary facts.
5. **No linear operator can give a Cheeger inequality for hypergraphs**; the working theory is non-linear and costs an `O(log r)` factor ([Chan et al., 2018](https://arxiv.org/abs/1605.01483)).
6. **The classical theory has no notion of a role.** Ordered and role-labelled hyperedges come from the database and KR traditions, not from Berge — which is why sections 02 and 03 exist.

## Where this section leads

- Section [02 — knowledge representation](../02-knowledge-representation/): what makes a hypergraph a *knowledge* hypergraph.
- Section [03 — construction](../03-construction/): building one from text, tables and existing graphs.
- Bibliography for this section: [../../sources/by-topic/01-foundations.md](../../sources/by-topic/01-foundations.md).
