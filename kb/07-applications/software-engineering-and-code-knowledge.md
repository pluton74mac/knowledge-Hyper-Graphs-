---
title: Software engineering and code knowledge
type: survey
status: draft
tags: [hypergraph, software-engineering, dependency-resolution, build-systems, code-knowledge-graph, RAG]
created: 2026-09-20
updated: 2026-09-20
---

# Software engineering and code knowledge

Software engineering has one fully worked, peer-reviewed hypergraph application (dependency resolution),
one structural case that is universally implemented but rarely named (build graphs), and a fast-moving
area where the hypergraph claim is mostly aspirational (code knowledge graphs for LLM agents). Keeping
these apart matters, because the first two are strong and the third is not yet.

## 1. Dependency resolution: HyperRes

The strongest result here is **HyperRes**
([Gibb, Ferris, Allsopp, Dales, Elvers, Gazagnaire, Jaffer, Leonard, Ludlam, Madhavapeddy, 2025](https://arxiv.org/abs/2506.10803),
SPLASH 2025; author's copy at [anil.recoil.org](https://anil.recoil.org/papers/2025-hyperres)). It gives
a formal system for versioned dependency resolution over a **hypergraph**, expressive enough to model
many packaging ecosystems and to resolve constraints *across* them.

The pipeline is three-stage: **parsing** translates package metadata into a resolution hypergraph;
**resolution** maps that hypergraph to a resolved graph of selected package versions; **deployment**
installs from the resolved graph. Resolution is NP-hard and is discharged with a custom SAT-based
solver — each package-version pair is a boolean variable, dependencies and conflicts become clauses —
with cost functions steering the search. The paper reports translations from dozens of existing package
managers into HyperRes, which is the evidence for the expressiveness claim.

Why the hypergraph is not decoration here: a dependency constraint is a disjunction over a *set* of
admissible versions, and a conflict is a constraint over a set; both are naturally hyperedges, and
flattening them to pairwise edges loses exactly the structure the solver needs. A readable survey of the
alternatives (pubgrub, backtracking, SAT, MaxSAT) is
[Nesbitt, 2026](https://nesbitt.io/2026/02/06/dependency-resolution-methods.html); a formal model of
dependency resolution across package managers appears in
[arXiv:2602.18602, 2026](https://arxiv.org/pdf/2602.18602). The earlier SAT-for-dependencies line is
[Le Berre and Parrain, *On SAT Technologies for Dependency Management and Beyond*](https://www.researchgate.net/publication/220789757_On_SAT_Technologies_for_Dependency_Management_and_Beyond).

## 2. Build graphs are directed hypergraphs

A build rule consumes a set of inputs and produces a set of outputs. That is a directed hyperedge with
stoichiometry-free multiset semantics — the same object as a chemical reaction in
[chemistry-and-reaction-networks](chemistry-and-reaction-networks.md) and the same AND semantics as an
exploit in [cybersecurity-and-it-operations](cybersecurity-and-it-operations.md). Every correct build
system already implements hyperedge traversal: a target is buildable only when *all* its inputs are
available, and incremental rebuild is a hyperpath computation from changed sources.

This is a case where the formalism is universally implemented and almost never named, which is worth
noting in a KB about knowledge hypergraphs: hyperedges are far more common in deployed software than
the "hypergraph databases are niche" framing suggests.
[unverified: this research run found no build-system paper that presents its dependency model explicitly
as a directed hypergraph; the equivalence above is a structural argument]

## 3. Code knowledge graphs for LLM agents — and what is *not* a hypergraph

Repository-level retrieval for code generation moved to graph structures in 2025:

- **RepoGraph** (ICLR 2025) builds a repository-level code graph for AI software engineering.
- **CodexGraph** bridges LLMs and repositories through a code graph database
  ([record](https://www.researchgate.net/publication/392505894_CodexGraph_Bridging_Large_Language_Models_and_Code_Repositories_via_Code_Graph_Databases)).
- Knowledge-graph-based repository-level code generation ([arXiv:2505.14394, 2025](https://arxiv.org/html/2505.14394v1)).
- **RANGER**, a repository-level agent for graph-enhanced retrieval ([arXiv:2509.25257](https://arxiv.org/pdf/2509.25257)).
- **LARGER**, lexically anchored repository graph exploration ([arXiv:2605.16352](https://arxiv.org/pdf/2605.16352)).
- Programming knowledge graphs for context-augmented code generation ([arXiv:2601.20810](https://arxiv.org/pdf/2601.20810)),
  and tree-sitter-derived code knowledge graphs served over MCP ([arXiv:2603.27277](https://arxiv.org/pdf/2603.27277)).

**All of these are binary graphs.** Calls, imports, inherits and defines are pairwise relations, and the
retrieval methods are graph traversals. This research run found **no** peer-reviewed repository-level
code RAG system built on a knowledge hypergraph.

One correction worth recording, because it circulates: **DocTrace** is sometimes described as a
repository-level code RAG system with hypergraphs. It is not. DocTrace
([*Trace Only What You Need*, 2026](https://arxiv.org/abs/2606.10921)) is a multi-agent framework for
**long-document question answering**: it keeps a lightweight document structural tree index, builds an
agent-shared **hypergraph-structured working memory on demand during reasoning**, and stores successful
reasoning plans in a graph-structured experience memory for reuse. Reported results are on four
long-document QA datasets, best on three, beating the strongest baseline by up to **8.85 % F1 and
4.40 % EM while cutting overall computational cost by 53.32 %**. It belongs in
[ai-agents-memory-and-planning](ai-agents-memory-and-planning.md), not here.

## 4. Where a code hypergraph would actually help

The structural argument, stated so it can be tested:

- **Change sets.** A commit touches a set of files to accomplish one intent; co-change is a hyperedge,
  not a clique. Mining co-change as cliques inflates coupling counts combinatorially.
- **Call sites with context.** `caller → callee` loses the arguments, the feature flag and the version.
  A four-way fact *(caller, callee, config, version)* is exactly a qualified n-ary fact in the sense of
  [n-ary-relations-and-reification](../02-knowledge-representation/n-ary-relations-and-reification.md).
- **Test-to-code evidence.** A failing test implicates a set of changed components jointly.
- **Build and deploy.** Covered in §2.

None of these is demonstrated in a published system found here. The honest summary for section 07 is
that software engineering has *excellent* directed-hypergraph practice in tooling and *no*
knowledge-hypergraph practice in code understanding.

## Sources

- Gibb, R., Ferris, P., Allsopp, D., Dales, M. W., Elvers, M., Gazagnaire, T., Jaffer, S., Leonard, T., Ludlam, J., Madhavapeddy, A. *Solving Package Management via Hypergraph Dependency Resolution.* SPLASH 2025; arXiv:2506.10803, 12 Jun 2025. https://arxiv.org/abs/2506.10803
- Madhavapeddy, A. et al. *Solving Package Management via Hypergraph Dependency Resolution* (author copy), 2025. https://anil.recoil.org/papers/2025-hyperres
- Nesbitt, A. *Dependency Resolution Methods*, 6 February 2026. https://nesbitt.io/2026/02/06/dependency-resolution-methods.html
- *Package Managers à la Carte: A Formal Model of Dependency Resolution.* arXiv:2602.18602, 2026. https://arxiv.org/pdf/2602.18602
- Le Berre, D., Parrain, A. *On SAT Technologies for Dependency Management and Beyond.* https://www.researchgate.net/publication/220789757_On_SAT_Technologies_for_Dependency_Management_and_Beyond
- *Knowledge Graph Based Repository-Level Code Generation.* arXiv:2505.14394, 2025. https://arxiv.org/html/2505.14394v1
- *CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases.* https://www.researchgate.net/publication/392505894_CodexGraph_Bridging_Large_Language_Models_and_Code_Repositories_via_Code_Graph_Databases
- *RANGER — Repository-Level Agent for Graph-Enhanced Retrieval.* arXiv:2509.25257. https://arxiv.org/pdf/2509.25257
- *LARGER: Lexically Anchored Repository Graph Exploration and Retrieval.* arXiv:2605.16352. https://arxiv.org/pdf/2605.16352
- *Context-Augmented Code Generation Using Programming Knowledge Graphs.* arXiv:2601.20810. https://arxiv.org/pdf/2601.20810
- *Codebase-Memory: Tree-Sitter-Based Knowledge Graphs for LLM Code Exploration via MCP.* arXiv:2603.27277. https://arxiv.org/pdf/2603.27277
- *Trace Only What You Need: Structure-Aware On-Demand Hypergraph Memory for Long-Document Question Answering* (DocTrace). arXiv:2606.10921, 2026. https://arxiv.org/abs/2606.10921
