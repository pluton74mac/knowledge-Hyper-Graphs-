---
title: "Acyclicity degrees, width measures and hypertree-decomposition solvers for the P6 schema checker, probed"
type: survey
status: draft
tags: [p6, acyclicity, fagin, gyo, berge, beta-acyclic, gamma-acyclic, hypertree-width, generalized-hypertree-width, fractional-hypertree-width, treewidth, hyperbench, balancedgo, log-k-decomp, newdetkdecomp, htdleo, frasmt, htd, probes]
created: 2026-09-24
updated: 2026-09-24
---

# Acyclicity degrees, width measures and solvers for the P6 checker (P6 research report 01)

**Question.** What exactly must P6's checker compute to place a relation-type schema in Fagin's acyclicity
hierarchy and to give its width? Which algorithms decide each class, which width measures should the survey
report, what is the published baseline to compare against, and which solvers work here, today, on real input?

**Short answer.**

- **The four degrees and their tests are settled and cheap.** Berge ⊂ γ ⊂ β ⊂ α, all strict. Berge: the
  incidence graph is a forest (linear). α: GYO reduction (linear by Tarjan and Yannakakis). β: remove nest points
  (β-leaves) until empty. γ: D'Atri–Moscarini reduction (singleton vertex, singleton edge, linearization). Greedy
  application is sound for all three reductions ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076)). A
  pure-Python implementation with witnesses agreed with brute-force evaluation of the definitions on all 400 seeded
  random hypergraphs (0 mismatches; section 1.4).
- **Widths: report hw exactly, ghw and fhw exactly when cheap and as bounds otherwise, and tw for contrast.**
  fhw ≤ ghw ≤ hw ≤ 3·ghw + 1 ([Grohe and Marx, 2014](https://arxiv.org/abs/1711.04506), citing Adler, Gottlob and
  Grohe 2007). Checking hw ≤ k is polynomial for fixed k. Checking ghw ≤ k is NP-complete for k ≥ 2, and so is
  fhw ≤ k ([Gottlob et al., 2021](https://arxiv.org/abs/2002.05239)). hw is the measure with a polynomial check, a
  decomposition as certificate and a published baseline.
- **The GYO residue determines ghw and fhw.** Removing a degree-1 vertex, a subsumed edge or a twin vertex changes
  neither width when it is ≥ 1 (proof in 5.2). Exact ghw and fhw therefore cost only as much as the residue is
  large. On P2's packaged schemas the residue is empty or a triangle.
- **Baseline: HyperBench.** The venues check out: PODS 2019, pp. 464–480, then ACM JEA 26 (2021).
  All non-random CQs in it have hw ≤ 3. Recomputing from the published run data (Zenodo, CC BY 4.0), the 1,113 CQs
  have exact hw 1 (673), 2 (432) or 3 (8). By construction, the SPARQL and Wikidata subsets hold only cyclic queries
  (section 3).
- **Solvers, probed.** Seven tools were built and run on 11 instances: BalancedGo, log-k-decomp, NewDetKDecomp,
  det-k-decomp 1.0, htd, HtdLEO/htdsmt and fraSMT. They agree wherever each is exact (section 4.4). Wikidata
  residues have hundreds of edges, so in-process search stops being enough there. **Recommendation: call
  BalancedGo (MIT, Go, one static binary, JSON decompositions) for hw, with log-k-decomp (MIT) as the second opinion.
  Keep a pure-Python core for classes, witnesses, reductions, exact ghw/fhw on cores of ≤ 16–18 vertices and exact
  hw on small inputs.** Do not vendor NewDetKDecomp or det-k-decomp (no licence), nor fraSMT (GPL-3 plus
  IBM CPLEX).
- **One conceptual caveat decides what the numbers mean.** P2's `schema_hypergraph` has roles as vertices and
  relations as edges. Its width is the width of the query that joins *all relations on same-named roles*, which is
  Fagin's database-scheme setting. It is not the width of arbitrary KHG queries, which join on entities (section
  2.5). Berge-acyclicity has a direct KHG reading here: the reified (incidence-graph) encoding is acyclic exactly when
  the schema is Berge-acyclic (section 1.3).

Scope: theory and tools. The data sources (Wikidata property constraints, a biomedical schema) and role naming are
the subject of the parallel P6 research on data; this report uses only P2's packaged schemas and constructed ones.

---

## 1. Fagin's hierarchy of acyclicity

### 1.1 Definitions

Conventions follow Brault-Baron's survey, which re-derives every characterisation in one framework
([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076), *ACM Computing Surveys* 49(3)). A hypergraph *H* is a
set of non-empty edges over a vertex set. For S ⊆ V, the induced hypergraph H[S] is {e ∩ S : e ∈ H} with the empty
sets dropped. A *subset* of H is a set of its edges (a partial hypergraph). M(H) keeps the inclusion-maximal edges.
The *incidence graph* is the bipartite graph of vertices and edges with v–e whenever v ∈ e.

Fagin's paper is the origin of the three degrees. In its own words it considers "various desirable properties of
database schemes and it is shown that they fall into several equivalence classes, each completely characterized by
the degree of acyclicity of the scheme". It also notes that "the original notion of acyclicity has the
counterintuitive property that a subhypergraph of an acyclic hypergraph can be cyclic. This strange behavior does
not occur for the new degrees" ([Fagin, 1983](https://dl.acm.org/doi/10.1145/2402.322390), *JACM* 30(3):514–550;
abstract read via [OpenAlex](https://api.openalex.org/works/doi:10.1145/2402.322390), OCR errors corrected; the
full text returned HTTP 403, so Fagin's own cycle definitions were not read `[unverified]`). The formal definitions
below are Brault-Baron's, quoted from the arXiv version:

- **Cycle, cycle-free, conformal.** "A tuple (t₁, …, tₙ) of n pairwise distinct vertices is a cycle of a
  hypergraph H" when M(H[{t₁,…,tₙ}]) is the graph cycle {t₁t₂, …, tₙ₋₁tₙ, tₙt₁}. H is *cycle-free* when it has no
  cycle, and *conformal* "if each of its cliques is included in an edge" (cliques of the primal graph).
- **α-acyclic.** "A hypergraph H is alpha acyclic, iff it is both conformal and cycle-free."
  Equivalently: H is GYO-reducible (repeated *included edge removal* and *singleton vertex removal* empties it), or
  H has a join tree (Brault-Baron, Characterization 15).
- **β-acyclic.** "A hypergraph H is beta acyclic, iff all its subsets are alpha acyclic." Equivalently, every
  subset is cycle-free ("we cannot get a usual graph cycle from H by removing vertices and/or edges";
  Characterizations 2 and 16). A third equivalent form: the incidence graph is *chordal bipartite*, meaning it has no
  induced cycle on six or more vertices. This one is due to Tarjan and Yannakakis
  ([Ordyniak, Paulusma and Szeider, 2013](https://arxiv.org/abs/1104.4279), Proposition 2, citing
  [Tarjan and Yannakakis, 1984](https://doi.org/10.1137/0213035)).
- **γ-acyclic.** "A hypergraph H is gamma acyclic, iff it is beta acyclic and we cannot find x, y, z such that
  {{x, y}, {y, z}, {x, y, z}} ⊆ H[{x, y, z}]". Brault-Baron proves this equivalent to "H is cycle-free and we cannot
  find x, y, z such that {{x, y}, {x, z}, {x, y, z}} ⊆ H[{x, y, z}]", which he labels "Definition 3 of gamma
  acyclicity in [Fag83]" (Characterizations 3 and 4). The excluded pattern is the **γ-triangle**.
- **Berge-acyclic.** "A hypergraph H is Berge acyclic when the graph G = {{x, e} : x ∈ e and e ∈ H} is acyclic",
  that is, the incidence graph is a forest (Brault-Baron §4.1, citing Berge 1985). Brault-Baron adds that Berge
  acyclicity is "not an actual hypergraph notion, but rather a multi-hypergraph notion". The multiset
  [{x, y}, {x, y}] is Berge-cyclic, while the set {{x, y}} is not.

**The hierarchy.** Berge-acyclic ⇒ γ-acyclic ⇒ β-acyclic ⇒ α-acyclic, and no converse holds
([Ordyniak et al., 2013](https://arxiv.org/abs/1104.4279), chain (1); Brault-Baron, Figure 2, gives a separating
example for each step). α-acyclicity alone is not closed under taking subsets of edges; β and γ are. On graphs
(all edges of size ≤ 2), acyclicity, cycle-freedom, α, β and γ all coincide (Brault-Baron, Remark 7).

### 1.2 Deciding each degree, with a witness

| Degree | Test | Cost | Soundness of greedy application | Witness when the test fails |
|---|---|---|---|---|
| Berge | union–find over the incidence graph (each named edge its own node) | linear in Σ\|e\| | n/a | a cycle v₁, e₁, …, v_k, e_k (k ≥ 2) |
| γ | **DM reduction** (D'Atri and Moscarini, 1982): singleton vertex removal (vertex in one edge), singleton edge removal (edge of size 1), linearization (drop x when some y ≠ x lies in exactly the same edges) until none applies; γ-acyclic iff the result is empty (Brault-Baron, Def. 8, Characterization 17) | polynomial (Brault-Baron, Corollary 11) | γ-acyclicity is invariant under each DM operation (Lemma 6), so any maximal sequence decides | the DM residue; if β-acyclic, a γ-triangle (x, y, z), found in O(n³·m) |
| β | **β-leaf (nest point) elimination**: repeatedly delete a vertex whose edges form a chain under ⊆; β-acyclic iff this empties H (Brault-Baron, Def. 4, Corollary 10; the existence of a nest point is Brouwer and Kolen 1980) | polynomial (Corollary 11); equivalently chordal-bipartite recognition of the incidence graph | leaf removal preserves β-acyclicity in both directions (Lemma 1) | a chordless incidence cycle x₁, E₁, …, x_k, E_k, k ≥ 3 (a "β-cycle"), and the residue |
| α | **GYO** (Graham 1979; Yu and Özsoyoğlu 1979): remove vertices in one edge and edges contained in another | linear by [Tarjan and Yannakakis, 1984](https://doi.org/10.1137/0213035) (Brault-Baron: "alpha acyclicity is even linear-time decidable") | confluent (Lemma 1 for α-leaves) | the GYO residue (what `khg_contracts.schema.is_alpha_acyclic` already returns) |

When the test succeeds, the α case yields a join tree. The prototype records it as the (ear, witness) links of
Graham's ear removal and checks the running-intersection property independently. The γ case also has a join-tree
form: for every edge e, H has "a rooted join tree with disjoint branches whose root is labelled e" (Duris, cited in
Brault-Baron (γ2c), Characterization 18). β "does not seem to admit a simple characterization in terms of join
tree" (Brault-Baron, §3.2).

### 1.3 What each degree buys, read for a KHG schema

- **α (database schemes).** Beeri, Fagin, Maier and Yannakakis show that "several desirable properties that have
  been studied by other researchers in very different terms are all shown to be equivalent to acyclicity"
  ([Beeri et al., 1983](https://dl.acm.org/doi/10.1145/2402.322389); abstract via OpenAlex). The properties usually
  cited from that paper were not checked against its full text `[unverified]`: join trees, semijoin full reducers,
  "pairwise consistent implies globally consistent", and a join dependency equivalent to its MVDs. For queries,
  α-acyclic conjunctive queries are exactly those of hypertree width 1
  ([Gottlob, Leone and Scarcello, 2002](https://arxiv.org/abs/cs/9812022), Theorem 4.4), and Yannakakis's algorithm
  evaluates them in polynomial time.
- **β.** Every sub-schema (any subset of the relations) is again α-acyclic. So a query that joins *any* subset of
  the relations on shared role names stays acyclic, which α alone does not promise (the triangle-with-cover schema
  is α-acyclic, but dropping the cover leaves a cyclic triangle). β is also the boundary for some problems with
  negation: SAT is polynomial on β-acyclic CNF ([Ordyniak et al., 2013](https://arxiv.org/abs/1104.4279)), and
  Brault-Baron's CSL 2012 paper is titled "A Negative Conjunctive Query is Easy if and only if it is Beta-Acyclic"
  (reference list of Brault-Baron 2016; the paper itself not read `[unverified]`).
- **γ.** Fagin characterises further scheme properties by γ-acyclicity (abstract above). Which properties they are
  was not verified from the primary text `[unverified]`.
- **Berge (a KHG-specific reading, derived here).** Reifying each n-ary fact into a fact node with one binary edge
  per role turns the hypergraph into its incidence graph. On graphs all degrees coincide (Brault-Baron, Remark 7).
  Hence **the reified (property-graph, RDF-reification) encoding of a schema is acyclic exactly when the schema is
  Berge-acyclic**. The probe confirms it (`out/reification.json`). The β-acyclic γ-triangle has hw 1 as an n-ary
  hypergraph and hw 2 once reified. The α-acyclic triangle-with-cover goes from hw 1 to hw 2. K5 goes from hw 3 to
  hw 4. This is the concrete reason for the survey to report the Berge class too, not only α.

### 1.4 Worked examples that separate adjacent classes

Each example is Brault-Baron's canonical counter-example (his Figure 2). They were computed by
`probes/p6check.py` and checked against brute-force evaluation of the definitions
(`probes/probe_theory.py`, `out/probe_theory.json`):

| Instance (`probes/instances/`) | Edges | Berge | γ | β | α | hw | ghw | fhw | Witness produced |
|---|---|---|---|---|---|---|---|---|---|
| `berge_path` | {a,b}, {b,c} | ✓ | ✓ | ✓ | ✓ | 1 | 1 | 1 | join tree E1–E2 |
| `berge_triangle` ("Berge triangle") | {x,y}, {x,y,z} | ✗ | ✓ | ✓ | ✓ | 1 | 1 | 1 | Berge cycle y–E1–x–E2 |
| `gamma_triangle` ("gamma triangle") | {x,y}, {y,z}, {x,y,z} | ✗ | ✗ | ✓ | ✓ | 1 | 1 | 1 | γ-triangle (x, y, z) |
| `a_triangle_cover` ("beta triangle") | {a,b}, {b,c}, {a,c}, {a,b,c} | ✗ | ✗ | ✗ | ✓ | 1 | 1 | 1 | β-cycle a–E1–b–E2–c–E3; join tree E1,E2,E3 → E4 |
| `b_triangle` (triangle) | {a,b}, {b,c}, {a,c} | ✗ | ✗ | ✗ | ✗ | 2 | 2 | 3/2 | GYO residue = all three edges |

**Cross-check.** 400 random hypergraphs, seeded 20260924, with 3–7 vertices and 2–7 edges. By class they split
Berge 72, γ 118, β 78, α 31, cyclic 101. The polynomial tests and the brute-force definitions (α1a, β1b, γ1a and
the incidence-graph definition of Berge) agreed on all 400 (0 mismatches). On the same inputs every width
invariant of section 2.2 held, and every hypertree decomposition found passed the four-condition validator (0
violations).

### 1.5 The knowledge base, checked

| Where | Claim | Verdict | Correction |
|---|---|---|---|
| [hypergraph-theory-results.md](../../../kb/01-foundations/hypergraph-theory-results.md) §5, "Why it matters" | "α-acyclicity is exactly the boundary of tractable join evaluation" | **Wrong** | α-acyclic ⇔ hw = 1 (GLS 2002, Thm 4.4). Tractability extends to bounded hw, ghw and fhw ([Grohe and Marx, 2014](https://arxiv.org/abs/1711.04506)), and bounded submodular width characterises fixed-parameter tractability, the hardness side assuming the Exponential Time Hypothesis ([Marx, 2009/2013](https://arxiv.org/abs/0911.0801)). For bounded arity, tractability is characterised by bounded treewidth ([Moll et al., 2012](https://arxiv.org/abs/1106.4719), introduction, citing Grohe 2007) |
| same, same paragraph | "Where a KHG schema is α-acyclic, queries over it are cheap" | **Imprecise** | Schema acyclicity concerns the join of the schema's relations on shared role names. A query over an α-acyclic schema can itself be cyclic, for example a triangle over one binary relation or joins on entity variables. Query cost is set by the query's hypergraph (section 2.5) |
| same, §5, γ bullet | γ is characterised "by the existence of a rooted join tree for every hyperedge" | **Imprecise** | Every α-acyclic hypergraph has a join tree that can be rooted anywhere. The γ condition is "a rooted join tree **with disjoint branches** whose root is labelled e" (Brault-Baron (γ2c), after Duris) |
| same, §6 | GLPR "prove that only hw is tractable to check … and that ghw(H) ≤ 2 is NP-complete too" | **Imprecise** | NP-completeness of ghw ≤ k for k ≥ 3 is Gottlob, Miklós and Schwentick (JACM 2009). GLPR add k = 2 for ghw and fhw, and prove **tractable** cases: ghw under the BIP/BMIP, fhw under bounded degree or the BIP, plus approximations ([Gottlob et al., 2021](https://arxiv.org/abs/2002.05239), Main Results 1–6). "Only hw" is too strong |
| same, §6 | Grohe–Marx TALG details `[unverified]` | **Resolvable** | *ACM Transactions on Algorithms* 11(1), article 4, 2014 (reference [34] of GLPR; [OpenAlex](https://api.openalex.org/works/doi:10.1145/2636918)) |
| same, §6 | the width inequalities | **Missing** | Add fhw ≤ ghw ≤ hw ≤ 3·ghw + 1 and ghw ≤ tw + 1 (Grohe and Marx 2014, §4, citing Adler, Gottlob and Grohe 2007) |
| [n-ary-relations-and-relational-algebra.md](../../../kb/01-foundations/n-ary-relations-and-relational-algebra.md) §2 | "if the schema of a fact base is α-acyclic, queries over it are tractable, whatever the instance looks like" | **Wrong** | As in row 2. Also, "tractable" must mean combined complexity. CQ answering "is well-known to be NP-complete" in general (GLPR §1), and the instance never matters for acyclicity |
| same, §2 | Fagin and BFMY "are about the first two" (schema and query hypergraphs) | **Imprecise** | Both papers are about database schemes (Fagin's abstract: "Database schemes … can be viewed as hypergraphs"). The query-hypergraph use comes through Yannakakis 1981 and GLS |
| same, §3 | "When the schema is cyclic — and most interesting ones are" | **Unsupported** | This is exactly the open measurement [01.3]. P2's fixture schema is Berge-acyclic with core+qualifier slots (section 5.5), and cyclicity appears once qualifier roles are shared across relations |
| same, §4 | "Any KHG query engine that plans joins pairwise is provably suboptimal on cyclic queries" | **Overstated** | The known result is about specific cyclic queries (the triangle) and worst-case instances. The exact statement should be taken from AGM 2013 or NPRR, which were not verified here `[unverified]` |
| [query-languages-for-hypergraphs.md](../../../kb/05-query-embeddings-reasoning/query-languages-for-hypergraphs.md) §10.2 | ghw "recognition is NP-hard (GMS 2009)" | **Imprecise** | NP-complete for every fixed k ≥ 3 (GMS 2009) and for k = 2 (GLPR 2021). Recognising hw ≤ k is polynomial |
| same, §10.2 | ghw "is the variant used most in machine learning today" | **Unsupported** `[unverified]` | No source given |
| same, §10.3 item 2 | "Reification multiplies the number of atoms, which raises the width" | **Right conclusion, wrong mechanism** | Width is not a function of atom count. Reification replaces the hypergraph by its incidence graph, which is acyclic iff the original is Berge-acyclic. Width rises when an n-ary atom covered a cycle (probe: hw 1 → 2 for the triangle with a cover) |
| [hypergraph-theory-results.md](../../../kb/01-foundations/hypergraph-theory-results.md) §5 | β-acyclic: at most n(n+1)/2 edges, attained by the interval hypergraph | **Correct** | Brault-Baron, Remark 13 |

The open-questions register entry [01.3] says the number "predicts query cost directly". It should be qualified as in
section 2.5.

---

## 2. Width measures

### 2.1 Definitions

Following [Grohe and Marx, 2014](https://arxiv.org/abs/1711.04506) and
[Gottlob, Leone and Scarcello, 2002](https://arxiv.org/abs/cs/9812022):

- A **tree decomposition** (T, (B_t)) of H has every edge inside some bag, and the bags containing any one vertex
  form a subtree. **tw(H)** = min over decompositions of max |B_t| − 1. This is the treewidth of the primal
  (Gaifman) graph.
- A **generalised hypertree decomposition** (GHD) adds guards λ_t ⊆ E(H) with B_t ⊆ ⋃λ_t. Its width is max |λ_t|,
  so **ghw(H) ≤ r** iff some tree decomposition has ρ(B_t) ≤ r for every bag, where ρ is the edge-cover number
  (Grohe and Marx, §4).
- A **hypertree decomposition** (HD) is a GHD with the *special condition*: "(⋃C_t) ∩ ⋃_{u∈V(T_t)} B_u ⊆ B_t for all
  t", where C_t is the guard and T_t the subtree rooted at t (Grohe and Marx, quoting GLS). Its width is
  **hw(H)**.
- A **fractional hypertree decomposition** (FHD) replaces guards by fractional edge covers: "fhw(H) ≤ r if H has a
  tree decomposition where ρ*(B_t) ≤ r for every bag" (Grohe and Marx, §4). The measure was introduced by Grohe and
  Marx (SODA 2006; *ACM TALG* 11(1), 2014).

### 2.2 Relations, and instances where each is strict

- **fhw ≤ ghw ≤ hw ≤ 3·ghw + 1.** "It has been proved in [Adler et al. 2007] that ghw(H) ≤ hw(H) ≤ 3 · ghw(H) + 1",
  and "fhw(H) ≤ ghw(H)" (Grohe and Marx, §4; Adler, Gottlob and Grohe, *European Journal of Combinatorics*
  28(8):2167–2181, 2007, [DOI](https://doi.org/10.1016/j.ejc.2007.04.013), not read directly). Beware: the JEA
  HyperBench text (p. 3) and the GLPR arXiv text (p. 2) both print "ghw(H) ≤ 3 · hw(H) + 1", with the variables
  swapped. The PODS 2019 HyperBench text has the correct "hw ≤ 3 · ghw + 1".
- **ghw ≤ tw + 1**, and a hypergraph with V(H) ∈ E(H) has ghw = 1 but tw = |V| − 1 (Grohe and Marx, §4).
- **hw = 1 ⇔ ghw = 1 ⇔ fhw = 1 ⇔ α-acyclic** (GLS, Theorem 4.4; Grohe and Marx: "fhw(H) = 1 ⇐⇒ ghw(H) = 1").
- **fhw ≤ ρ*(H)** (Grohe and Marx). The family H_n of their Example 4.2 has ρ* = 2 and hw = n.

Strictness on the probe instances (section 4.4 has the solver-by-solver table):

| Instance | V / E | tw | fhw | ghw | hw | What it shows |
|---|---|---|---|---|---|---|
| `b_triangle` | 3 / 3 | 2 | 3/2 | 2 | 2 | fhw < ghw |
| `k5` (K5 as binary edges) | 5 / 10 | 4 | 5/2 | 3 | 3 | fhw < ghw = hw < tw + 1 |
| `adler` (Adler's example, HyperBench id 1) | 10 / 8 | 4 | 2 | 2 | 3 | **ghw < hw** (HyperBench lists hw = 3, ghw ≤ 2, fhw ≤ 2 for it) |
| `grohe_marx_3` (Example 4.2, n = 3) | 20 / 6 | 18 | 2 (fraSMT; ρ* = 2) | 3 | 3 | fhw < ghw, and tw far above both |
| `c_grid4` (4×4 grid) | 16 / 24 | 4 | 3 | 3 | 3 | ghw meets the graph lower bound ⌈(tw+1)/2⌉: some bag has tw + 1 vertices, and binary edges cover at most two each |
| `c_grid5` (5×5 grid) | 25 / 40 | ≤ 5 (htd) | 3 (fraSMT) | 3 | 3 | as above |
| `c_grid2d_10` (Samer's Grid2D, gate case (c) scaled up) | 50 / 50 | ≤ 13 (htd) | 4 (fraSMT) | 4 | 4 | the first instance where solver choice matters (4.4) |

### 2.3 Complexity of checking and computing

| Problem | Complexity | Source |
|---|---|---|
| hw ≤ k, fixed k | polynomial; in LOGCFL | [GLS, 2002](https://arxiv.org/abs/cs/9812022) ("checking whether hw(Q) ≤ k is in the parallel complexity class LOGCFL") |
| ghw ≤ k | NP-complete for every fixed k ≥ 3 | [Gottlob, Miklós and Schwentick, 2009](https://doi.org/10.1145/1568318.1568320) (via GLPR) |
| ghw ≤ 2, fhw ≤ 2 | NP-complete (fhw: "can be extended to … arbitrarily large k") | [Gottlob, Lanzinger, Pichler and Razgon, 2021](https://arxiv.org/abs/2002.05239) (*JACM* 68(5); extends Fischl, Gottlob and Pichler, PODS 2018, pp. 17–32) |
| ghw ≤ k under the BIP or BMIP | polynomial, and FPT in the intersection bound | GLPR, Main Result 3 |
| fhw ≤ k under bounded degree or the BIP | polynomial | GLPR, Main Result 4 |
| fhw approximation | O(k³) in general ([Marx, 2010](https://doi.org/10.1145/1721837.1721845)); k + ε under the BMIP; O(k log k) under bounded VC-dimension | GLPR, Main Result 5 |
| fhw, ghw, hw approximation for unbounded width | polynomial time, fhw O(ω log n log ω); hence O(log² n log ω)-approximations of ghw and hw | [Korchemna et al., 2024](https://arxiv.org/abs/2409.20172) (abstract read) |
| exact ghw, fhw (exponential) | O*(2ⁿ) and O(1.734601ⁿ · m) | [Moll, Tazari and Thurley, 2012](https://arxiv.org/abs/1106.4719), Theorem 1 |

The last row matters for P6. Moll, Tazari and Thurley show that any "monotone f-width" (ghw with f = ρ, fhw with
f = ρ*) is a minimum over tree decompositions of the primal graph. The prototype's subset DP over elimination
orderings is the simplest instance of that idea (section 4.6).

### 2.4 What each measure predicts for evaluation cost

- **hw or ghw = k.** Given a width-k decomposition, each node becomes the join of at most k relations projected on
  its bag. The result is "a join tree JT of an acyclic query Q′ over database DB′ of size O(nᵏ), where n is the input
  size", on which Yannakakis-style evaluation runs (GLS, §4). The exponent is the width; the base is the relation
  size, not the domain.
- **fhw = r.** Each bag has at most ‖I‖^ρ* solutions, and they can be listed in ‖I‖^{ρ*+O(1)} (Grohe and Marx,
  Theorem 3.5). With a width-r FHD in hand, the CSP is solvable in time C·‖I‖^{O(1)}, where C bounds the solutions
  per bag (Lemma 4.9), that is ‖I‖^{r+O(1)}. fhw is therefore the sharpest of the three exponents. The AGM bound
  and worst-case-optimal joins are the per-bag engine (already in the KB).
- **tw = k.** This is the right measure only for bounded arity: "in the case of bounded arities … bounded tree-width
  completely describes this setting" (Moll et al., introduction, citing Grohe 2007). With unbounded arity, tw
  overstates cost: `grohe_marx_3` has tw 18 but ghw 3.
- Beyond these: **submodular width** characterises fixed-parameter tractability for unbounded arity: bounded
  submodular width gives FPT, and unbounded width rules it out "unless the Exponential Time Hypothesis fails"
  ([Marx, 2009/2013](https://arxiv.org/abs/0911.0801)). **Soft hypertree width** (shw ≤ hw, with a tractable check)
  targets practical planning ([Lanzinger et al., 2024](https://arxiv.org/abs/2412.11669)). Neither has a solver
  probed here.

### 2.5 What a schema survey should report, and why

**What the number is a number of.** P2's `schema_hypergraph` puts one vertex per global role and one edge per
relation (DESIGN §3, F4). That is Fagin's database-scheme hypergraph with roles as attributes. Its width is the width
of **the conjunctive query that joins all relations on same-named roles** (the universal-relation join). It is also
the width of every query that joins some of them in that way; β-acyclicity makes that robust to taking subsets
(1.3). It is **not** the width of arbitrary KHG queries. Those join facts on entity variables, and their hypergraph
is the query's, not the schema's. For real Wikidata SPARQL logs the query-side answer is already published: of
1,915,550 CQOF+ queries, 590,005 have hw 2 and the rest hw 1, and HyperBench's 354 distinct cyclic Wikidata
hypergraphs all have hw 2 (section 3.4). The survey is still meaningful. It measures how entangled the
shared-role structure (mainly the qualifiers) is. That entanglement bounds the cost of role-aligned joins, and it
decides whether pairwise checks suffice for global consistency, which is the BFMY side. The claim "predicts query
cost directly" should be narrowed to that.

**Recommended columns per schema and variant:**

1. **Class**: Berge / γ / β / α / cyclic, each with its witness (1.2).
2. **hw**, exact where the solvers finish, otherwise [lower, upper]. Reasons: it has a polynomial check and a
   checkable certificate (an HD), and it is what HyperBench and the SPARQL-log studies report, so it is directly
   comparable. On HyperBench, when both are known, hw = ghw in 99.2% of cases (3.4).
3. **ghw**, exact on small residues (DP) or via BalancedGo's GHD mode, otherwise bounds. hw ≤ 3·ghw + 1 makes any
   hw bound a ghw bound.
4. **fhw**, exact on small residues (DP + LP), otherwise an upper bound max_t ρ*(B_t) over the HD found (HyperBench's
   "ImproveHD" idea) and a clique lower bound (5.3). It gives the sharpest cost exponent (2.4).
5. **tw of the primal graph**, for contrast with graph-based work and to show how much arity matters.
6. The structural parameters HyperBench tabulates, for comparability: vertices, edges, rank (max arity), degree,
   BIP (max pairwise intersection), and the GYO-residue size.

---

## 3. HyperBench: the baseline

### 3.1 Venues, verified

- W. Fischl, G. Gottlob, D. M. Longo, R. Pichler, "HyperBench: A Benchmark and Tool for Hypergraphs and Empirical
  Findings", **PODS 2019**, pp. 464–480, [DOI 10.1145/3294052.3319683](https://doi.org/10.1145/3294052.3319683)
  (pages via OpenAlex; arXiv [1811.08181](https://arxiv.org/abs/1811.08181)).
- Extended version: same authors and title, ***ACM Journal of Experimental Algorithmics* 26 (2021)**, pp. 1–40,
  [DOI 10.1145/3440015](https://doi.org/10.1145/3440015) (arXiv [2009.01769](https://arxiv.org/abs/2009.01769),
  which states it is "an extended and enhanced version of the paper … presented at PODS 2019").

### 3.2 The collection (JEA version, Table 1)

3,648 hypergraphs. CQs: SPARQL 70 (out of 26,157,880), Wikidata 354 (out of 273,947), LUBM 14, iBench 40, Doctors
14, Deep 41, JOB (IMDB) 33, TPC-H 29, TPC-DS 228, SQLShare 290 (out of 15,170), Random 500. CSPs: Application
1,090, Random 863, Other 82. The "hw ≥ 2" column sums to 2,939. **The collection is biased toward cyclic
instances on purpose.** Of the SPARQL logs, "we have only included CQs, which were detected as having hw ≥ 2". The
Wikidata set is the 354 distinct hypergraphs of the unique cyclic queries. SQLShare keeps only queries "not trivially
acyclic (i.e., they have at least 3 atoms)". (The paper gives the Wikidata query count as 273,947 in Table 1 and
273,974 in the text.) The CSPs come mostly from XCSP; "CSP Other" holds Daimler-Chrysler, ISCAS and Grid2D
hypergraphs from earlier det-k-decomp studies.

### 3.3 The tool, the data, and their licences

| Artefact | Where | What was checked (2026-09-24) | Terms |
|---|---|---|---|
| Web interface | [hyperbench.dbai.tuwien.ac.at](http://hyperbench.dbai.tuwien.ac.at/) | front page reports "3071 hypergraphs"; each has hw/ghw/fhw bounds and GML decompositions; "Download All" per category | "The HyperBench benchmark may be used freely. However, if results obtained with this benchmark are published, we request authors to cite the papers [1] - [5]" (front page) |
| Full download | `http://hyperbench.dbai.tuwien.ac.at/download/type` | 2,262,992-byte zip, 3,071 `.hg` files, sha256 `6bab8750…f727` (in scratch, not in the repo) | as above |
| Format manual | [downloads/manual.pdf](http://hyperbench.dbai.tuwien.ac.at/downloads/manual.pdf) (Fischl, 24 Jan 2018) | `Hyperedge (v1, v2, …),` lines, `.` at the end, `%` comments | – |
| Instances + all runs of the log-k-decomp study | [Zenodo 10.5281/zenodo.7180787](https://zenodo.org/records/7180787), v4, 9 Oct 2023 | `hyperbench.zip` (2,411,098 bytes, sha256 `995afdf6…dbec8`); `parseddata_csv.zip` with `Run.csv` (200,402 runs over 3,649 graphs: DetK, NewDetK, LogKDecomp, LogKHybrid, htdLEO, htdSMT) | **CC BY 4.0** |
| Decomposition software of the paper | NewDetKDecomp, [github.com/dmlongo/newdetkdecomp](https://github.com/dmlongo/newdetkdecomp) (the JEA text names it; the PODS text names the identical `TUfischl/newdetkdecomp`) | built, section 4 | **no licence file** |

For a citable, licensed baseline, **use the Zenodo copy** (CC BY 4.0). The website's 3,071 differs from the paper's
3,648 and Zenodo's 3,649; the per-category counts were not reconciled `[unverified]`.

### 3.4 Empirical findings (quoted from the JEA version)

- "all non-random CQs have hw ≤ 3 and over 60% of CSPs stemming from applications have hw ≤ 5."
- "In total, including random CQs, 2,427 (66.5%) out of 3,648 instances have hw ≤ 5."
- hw against ghw: "if we consider the fully solved cases …, then hw and ghw coincide in 99.2% of the cases (1,968
  of 1,984)"; in 16 cases ghw was one less (hw 6 → ghw 5).
- The restrictions that make GHD and FHD checking easier, "BIP, BMIP, bounded degree, and bounded VC-dimension",
  are "astonishingly realistic" on application instances.
- On SPARQL logs, as reported by HyperBench: "Out of 6,959,510 CQs of arity 3, only 86 … turned out to have hw = 2
  and 8 queries had hw = 3". For the Wikidata logs, "590,005 queries have hw = 2, while the rest has hw = 1" out of
  1,915,550 CQOF+ queries (Bonifati, Martens and Timm, PVLDB 2017 and WWW 2019, both read only through HyperBench
  `[unverified]` against the originals).

### 3.5 The baseline, recomputed from the published runs

`probes/hyperbench_baseline.py` reads Zenodo's `Run.csv`. Every algorithm in it computes HDs. Per graph, the upper
bound is the smallest K with a correct decomposition, and the lower bound is 1 + the largest K refuted without
timeout. Output: `out/hyperbench_hw.json`.

| Group (Type_of.csv) | n | exact hw (count) | upper bound only | share hw ≤ 2 | ≤ 3 | ≤ 5 |
|---|---|---|---|---|---|---|
| CQ (all non-random) | 1,113 | 1: 673 · 2: 432 · 3: 8 | – | 99.3% | 100% | 100% |
| of which SPARQL | 70 | 2: 62 · 3: 8 | – | 88.6% | 100% | 100% |
| of which SQLShare | 290 | 1: 289 · 2: 1 | – | 100% | 100% | 100% |
| CQ Random | 500 | 1–10 (spread) | 11 | 21.0% | 34.8% | 57.8% |
| CSP Application | 1,090 | 2–7 | 242 | 2.7% | 13.3% | 61.4% |
| CSP Random | 863 | 2–9 | 10 | 5.5% | 18.3% | 39.6% |
| CSP Other | 82 | 2–8 | 33 (+1 with none) | 23.2% | 29.3% | 45.1% |

One graph (`rand_q0135.hg`) is inconsistent in the published runs: BalancedGo's DetK 1.04 reports a decomposition
at K = 1, but every tool refutes K = 2 and succeeds at K = 3. Treat such runs as errors. This is one more reason
for P6 to validate every decomposition it is handed (5.3).

**Size matters for P6.** With the instance files from the same Zenodo record, exactness falls off with size
(`exactness_by_edges` in `out/hyperbench_hw.json`). Exact hw is known for 1,884 of 2,010 graphs with fewer than 50
edges, 1,302 of 1,418 with 50–99, 136 of 160 with 100–149, 24 of 32 with 150–299, **6 of 23 with 300–999** and
**0 of 6 with 1,000 or more**. The large ones keep wide bounds: `grid2d_75` (2,812 edges) [3, 48], `s1423` (731
edges) [4, 25], `s1488` (659 edges) [4, 75]; `s5378` (2,958 edges) has no upper bound at all.

The parallel P6 data probe's draft table (`probes/out/wd-survey.md`, generated by `wd_schema_survey.py`; not checked
here) lists Wikidata schema hypergraphs of 1,155 to 13,608 relations. Their GYO residues keep about 340 to 2,250
edges under every role-naming variant except the fully relation-local one, and the largest edges have 34 to 771
roles. That is the 300-to-1,000+ edge band, where HyperBench has exact hw for 6 of 29 graphs. **So the survey must
expect bounds, not exact values, for Wikidata, unless the width turns out small.**

### 3.6 How to compare KHG schemas against HyperBench

Compare distributions with care. HyperBench hypergraphs are *queries* and *constraint networks* selected to be
cyclic. KHG schema hypergraphs are *schemes*. The honest comparison is by structural parameter (rank, degree, BIP,
residue size) and by hw. A schema whose hw far exceeds 3 is unlike any real CQ in HyperBench and more like its
application CSPs.

---

## 4. Solvers, probed

All builds and runs were made in this container on 2026-09-24 (Linux x86-64, 4 cores, Go 1.24.7, OpenJDK 21,
GCC 13.3, CMake 3.28, Python 3.11.15). Installs and sources live under the session scratchpad (`…/scratchpad/p6/`),
not in the repository. Raw outputs, each with the exact command on its first line, are in
`probes/out/solvers/<tool>/`. The summary is `probes/out/solvers/summary.tsv`.

### 4.1 The tools

| Tool | Repository / source, version probed | Licence | Language, deps | Computes | Exact? | Input |
|---|---|---|---|---|---|---|
| **BalancedGo** | [github.com/cem-okulmus/BalancedGo](https://github.com/cem-okulmus/BalancedGo), commit `872c662` (`v1.7.2-2-g872c662`, 2023-07-11) | **MIT** | Go ≥ 1.12; 4 Go modules | HD (`-det`, DetKDecomp), GHD (`-global`, `-local`, `-balDet` hybrids), approximations (`-approx`) | `-exact -det` iterates k = 1, 2, … → exact hw | HyperBench; PACE 2019 (`-pace`) |
| **log-k-decomp** | [github.com/cem-okulmus/log-k-decomp](https://github.com/cem-okulmus/log-k-decomp), `v1.1.0` (`5e021dd`, 2022-12-02) | **MIT** | Go ≥ 1.14; imports BalancedGo v1.7.0 | HD (log-k hybrid) | `-exact` → exact hw | HyperBench; `-pace` |
| **NewDetKDecomp** | [github.com/dmlongo/newdetkdecomp](https://github.com/dmlongo/newdetkdecomp) `c06232d` (2019-03-12; `TUfischl/newdetkdecomp` has the same HEAD) | **none stated** | C++14, COIN-OR Cbc/Clp | `detkdecomp` (HD), `globalbipkdecomp`, `localbipkdecomp`, `balsepkdecomp` (GHD), `fracimprovehd`, `rankfhdecomp` (FHD upper bounds), `hg-stats` (degree, BIP, VC-dim) | per-k yes/no; fhw tools give upper bounds | HyperBench (no `-` or `.` in names) |
| det-k-decomp 1.0 | [github.com/daajoe/detkdecomp](https://github.com/daajoe/detkdecomp) `277d593` (2018; Gottlob and Samer's code) | none on the C++ sources (the Python wrapper is GPL-3) | ANSI C++ | HD, per k | per-k yes/no | HyperBench |
| **htd** | [github.com/mabseher/htd](https://github.com/mabseher/htd) `ee52054` (`1.2-9`, `htd_main 1.2.0`) | **GPL-3** | C++, CMake | tree decompositions (min-fill etc., `--opt width`), heuristic "hypertree" decompositions (TD + covers) | no: upper bounds | `gr`, `hgr` (`p tw n m` + one vertex list per line), `lp` |
| **HtdLEO** | [Zenodo 10.5281/zenodo.4742100](https://zenodo.org/records/4742100) (`htdleo.zip`, 2021-05-07, sha256 `13d2b89f…268b26c`) | CC BY 4.0 (Zenodo record); bundles `htd_validate` (GPL-3) and a static `uwrmaxsat` binary | Python; PySAT, networkx, z3 | exact hw (SAT, LEO encoding); `-g` exact ghw | yes | HyperBench or PACE-like |
| htdsmt | [github.com/ASchidler/htdsmt](https://github.com/ASchidler/htdsmt) `97eb64a` (2021-12-29), successor of HtdLEO | GPL-3 | as HtdLEO | exact hw, ghw | yes | as HtdLEO |
| **fraSMT** | [github.com/daajoe/frasmt](https://github.com/daajoe/frasmt) `eb995ca` (2020-07-18) | GPL-3 | Python; clingo, z3 (binary), **IBM CPLEX Python API** | exact fhw (SMT) | yes | HyperBench |

Not probed: *Ralph*, an LP-based fhw/ghw upper- and lower-bound method evaluated on HyperBench
([PACMMOD 2025, DOI 10.1145/3725296](https://doi.org/10.1145/3725296); code availability not found `[unverified]`).
*Rerootable* HDs ([Jiang et al., 2026](https://arxiv.org/abs/2608.17853)) and shw are about planning, not
measurement. **No Python package for hypertree decompositions exists on PyPI under the obvious names.** Probed on
2026-09-24: `hypertree` is a decision-tree package, `htd` parses time deltas, `hyperbench` is a hyperspectral
benchmark, and `hypertree-decomposition`, `hypertree-width`, `pyhtd`, `htd-validate`, `detkdecomp`, `balancedgo`,
`ghd`, `fhtd`, `frasmt` and `treewidth` do not exist. HtdLEO, htdsmt and fraSMT are Python research code, not
packages.

### 4.2 Build steps that worked

```bash
# Go tools (GOPATH and GOCACHE pointed into the scratchpad)
git clone https://github.com/cem-okulmus/BalancedGo && (cd BalancedGo && go build -o BalancedGo .)        # 9 s
git clone https://github.com/cem-okulmus/log-k-decomp && (cd log-k-decomp && go build -o log-k-decomp .)
# NewDetKDecomp: the stock Makefile fails on GCC 13 (missing <iostream>/<cstring> includes); force them
apt-get install -y --no-install-recommends coinor-libcbc-dev coinor-libclp-dev    # Cbc 2.10.11, Clp 1.17.9
git clone https://github.com/dmlongo/newdetkdecomp && cd newdetkdecomp && \
  make -j4 CXXFLAGS="-std=c++14 -O2 -I/usr/include/coin -include iostream -include cstring -include algorithm -include limits"
# det-k-decomp 1.0
git clone https://github.com/daajoe/detkdecomp && cd detkdecomp/sources && \
  g++ -O2 -include iostream -include cstring -include cstdlib -o detkdecomp *.cpp
# htd
git clone https://github.com/mabseher/htd && mkdir htd/build && cd htd/build && \
  cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF && make -j4 htd_main      # -> bin/htd_main-1.2.0
# Python side (one venv): python-sat 1.9.dev15, networkx 3.6.1, z3-solver 5.1.0.0 (ships a z3 binary), scipy 1.17.1,
# clingo 5.8.2, cplex 22.2.0.1 (IBM Community Edition), numpy, lxml, psutil
curl -L -o htdleo.zip "https://zenodo.org/records/4742100/files/htdleo.zip?download=1" && unzip htdleo.zip -d htdleo
git clone https://github.com/ASchidler/htdsmt
git clone https://github.com/daajoe/frasmt && (cd frasmt && git submodule update --init lib/htd_validate)
```

Two runtime shims, both in `probes/`, make the Python tools run unmodified:

- `run_htdleo.py` aliases `pysat.solvers.Cadical` to `Cadical153`. PySAT 1.9 dropped the old name; the README pins
  "PySAT 1.6.0".
- `run_frasmt.py` restores `collections.Iterable`, which Python 3.10 removed. fraSMT also fails with a bare
  `ImportError` until clingo and CPLEX are importable. It uses CPLEX for its fractional-cover preprocessing, and the
  pip `cplex` package is IBM's size-limited Community Edition, proprietary.

### 4.3 Input formats and naming pitfalls

- **HyperBench format** (all tools except htd): `E1 (a, b),` … `En (x, y).`, with `%` comments. The manual says names
  "may consist of any combination of lower- and uppercase letters, numbers, underscore, colon, etc." In practice:
  1. **BalancedGo panics if a relation id equals a role id** ("Edge names not unique, not a valid hypergraph!"),
     for example relation `population` with role `population`. NewDetKDecomp accepts the clash.
  2. **NewDetKDecomp rejects `-` and `.` in names** ("Illegal character"). BalancedGo accepts them. Colons pass both.
  3. **fraSMT silently read 0 edges** from Samer's `grid2d_10` (ids like `C0:1`) and reported fhw 1. After renaming the
     ids it returned 4.0 (4.4).
  4. Hence **P6 should emit neutral ids (`R<i>` for relations, `V<j>` for roles) plus a mapping file**, as
     `probes/probe_schemas.py` does, map decompositions back, and check that the edge count the tool echoes matches.
- **PACE 2019** (`p htd <n> <m>`, then `<edge-id> <v> …`, 1-based integers; the
  [PACE 2019 spec](https://pacechallenge.org/2019/htd/htd_format/)): BalancedGo `-pace` gave the same widths as on
  HyperBench input.
- **htd `hgr`**: `p tw <n> <m>` then one line of vertex ids per edge, with no edge ids and no blank lines.
- **Outputs.** BalancedGo `-json f` writes `{"Root": {"Bag": [...], "Cover": [...], "Children": [...]}}`, the
  easiest format to validate. log-k-decomp and NewDetKDecomp write GML. HtdLEO and htdsmt print
  `Result: k  Valid: True  SP: True  GHTD: True`. fraSMT prints a JSON record with `"width"`.

### 4.4 Runs on the test instances

Case (a) is `a_triangle_cover` (α-acyclic, hw 1), (b) `b_triangle` (cyclic, hw 2), (c) the grids. A cell holds the
width reported, with seconds in parentheses where they exceeded 1. "k:no/yes" lists the per-k answers. A dash
means not run.

SOLVER_TABLE_PLACEHOLDER

### 4.5 Scaling to the size of Wikidata residues

`probes/scale_probe.sh` ran on three large HyperBench instances (timeout 300 s, 4 cores, other probes running).
Output: `probes/out/scale/`.

SCALE_TABLE_PLACEHOLDER

### 4.6 The pure-Python fallback, and how small is small

`probes/p6check.py` (standard library; scipy only for ρ*) implements:

- the four class tests and their witnesses (1.2);
- **exact tw, ghw, fhw** by the subset DP over elimination orderings,
  F(S) = min_{v∈S} max(F(S∖{v}), f({v} ∪ Q(S∖{v}, v))). Here Q(S, v) is the set of vertices outside S ∪ {v}
  reachable from v through S, and f = |B| − 1, ρ(B) or ρ*(B). It runs on the reduced core (5.2) and is exact by Moll
  et al.'s monotone-f-width argument;
- **exact hw** by a k-decomp / det-k-decomp style search over normal-form HDs, for k = 1, 2, …. The state is a
  [χ]-component C with connector N(C). A separator is any ≤ k edges covering N(C) and meeting C, with χ = ⋃λ ∩
  (C ∪ N(C)). Failed components are memoised (GLS 2002, §5; [Gottlob and Samer, 2008](https://doi.org/10.1145/1412228.1412229)).
  Every HD it returns is re-checked against the four conditions.

Measured costs (single core, Python 3.11; `out/dp_limits.json`, `out/probe_theory.json`):

| Computation | Instance (core size) | Result | Time |
|---|---|---|---|
| tw DP | `c_grid4` (16 vertices) | 4 | 1 s |
| ghw DP | `c_grid4` (16 vertices) | 3 | 2 s |
| fhw DP (one LP per bag) | `c_grid4` (16 vertices) | 3 | 57 s |
| fhw DP | `adler` (10 vertices) | 2 | 2 s |
| tw DP | `grohe_marx_3` (20 vertices) | 18 | 24 s |
| ghw DP | `grohe_marx_3` (20 vertices) | 3 | 42 s |
| hw search | `c_grid5` (25 vertices, 40 edges) | 3, validated | 0.2 s |
| hw search | `grohe_marx_3` (20 vertices, 6 edges) | 3, validated | < 0.1 s |
| hw search | `c_grid2d_10` (50 vertices, 50 edges; hw 4) | budget of 3·10⁶ separator trials exhausted | 1 s |

**How small.** Exact ghw via the DP is practical up to a **core of about 16–20 vertices**: time and memory grow as
2ⁿ, and 20 vertices took 42 s. fhw is practical up to **about 16**, where the LPs dominate. The hw search depends on
m^k rather than n. It was instant on 40 edges at k = 3 but gave up on 50 edges at k = 4, which BalancedGo solved
in 3 s. So the external solvers should take over once m exceeds ~40 or k exceeds 3. These limits apply to the *GYO residue*, not the whole schema. P2's fixture
(30 roles, 11 relations) has an empty residue, so its widths are trivial whatever its size.

### 4.7 Recommendation

1. **Primary external solver: BalancedGo** (MIT, a single static Go binary, both input formats, JSON output).
   Use `-exact -det` for hw. For ghw use the GHD modes one k at a time: `-width k -global`, or `-local` /
   `-balDet d`. Do not use `-global -exact`: the subedges are computed for the `-width` flag value, not per
   iteration (read from `balanced.go`). `-approx` is weak: it returned width 12 in 60 s on `bridge_99`, whose hw is 2.
2. **Second opinion for hw: log-k-decomp** (MIT, same authors, same formats). It and BalancedGo disagreed on nothing
   in 4.4.
3. **In-process (vendored in P6's Python):** the class tests, witnesses, reductions, exact DP for small cores, the
   small-hw search, an FHD upper bound max ρ*(B_t) over the HD returned, and the validator for any decomposition.
4. **Cross-validation only, not dependencies:** HtdLEO/htdsmt (exact hw and ghw by SAT; GPL-3 or CC BY with GPL
   parts), fraSMT for exact fhw on small cores (GPL-3; needs proprietary CPLEX), htd for fast tw and GHD upper
   bounds (GPL-3). **Do not vendor** NewDetKDecomp or det-k-decomp: they carry no licence.
5. **For large residues, report bounds.** Upper bound: the best of BalancedGo/log-k-decomp at increasing k under a
   time limit, htd's TD + cover heuristic, and FHD improvement. Lower bound: the largest k refuted without timeout,
   ghw ≥ max over primal cliques K of ρ(K), and fhw ≥ max ρ*(K). A clique of the primal graph must fit in one bag of
   every tree decomposition, so these hold; fraSMT uses clique bounds in its preprocessing too.

---

## 5. Implementation notes for the checker

### 5.1 From a P2 schema to solver input

1. `load_schema(path)` (layers J, V, M), then `schema_hypergraph(schema, slots=…)`
   (`src/khg_contracts/schema/hypergraph.py`). The result is `{"vertices": [roles], "hyperedges": {relation:
   [roles]}}`: roles sorted, relations in schema order, lifecycle relations never included, and relations with no
   usage in the chosen slots dropped. A role is one vertex whatever its slot (F4).
2. **Slots are a survey variable.** With `("core", "qualifier")` the P2 fixture is Berge-acyclic. With `time` added
   it drops to γ: `married` and `position_held` then share `start_time` and `end_time`, two edges with two common
   vertices (5.5).
3. **Duplicates.** Two relations with the same role set are one edge of the set hypergraph (Fagin's setting) but
   two in the multi-hypergraph. α, β and γ ignore the difference. Berge does not: the multiset [{x,y},{x,y}] is
   Berge-cyclic. Recommendation: compute Berge on the multi-hypergraph (named relations) and report duplicate
   role-sets as their own finding.
4. **Components.** tw, ghw and fhw of a hypergraph are the maximum over the blocks (biconnected components) of its
   primal graph. Every edge's vertices form a clique, which lies in one block, and decompositions glue at cut
   vertices. Splitting first is safe for these measures and speeds up the DP. For hw, splitting was not verified
   here; BalancedGo's `-h` hinge option is the tool's own route `[unverified]`.
5. **Emit** HyperBench text with neutral ids plus a mapping JSON (4.3). Call the solver with a timeout and parse
   `Width:` / `Correct:` and the `-json` tree. **Validate the returned decomposition in Python** (four HD conditions,
   or three for a GHD) before reporting it, then map ids back to relation and role names.

### 5.2 Reductions that preserve ghw and fhw (and why)

Let H′ be obtained from H by one operation, and assume the width is ≥ 1.

- **Remove a vertex v that lies in exactly one edge e.** A decomposition of H′ has a bag ⊇ e∖{v}. Hang a new leaf
  with bag e and guard {e} below it. Coverage and connectivity hold, and the width does not grow. Conversely, the
  width is monotone under induced subhypergraphs.
- **Remove an edge e ⊆ f.** Every bag covering f covers e, and any guard using e can use f instead.
- **Remove a twin y** (the same edges as some x). Add y to every bag that contains x. Any guard covering x covers y.

GYO consists of the first two operations. So **ghw(H) = fhw(H) = 1 iff the core is empty (α-acyclic); otherwise ghw(H) = ghw(core) and fhw(H) =
fhw(core)**, the core being the GYO residue with twins merged. This is P6's biggest practical saving. None of
this is claimed for hw: the special condition interacts with guard replacement, so the prototype computes hw on the
input as given. BalancedGo and log-k-decomp offer `-g` (a GYÖ reduct) and `-t` (a "type collapse", i.e. twin
merging) as preprocessing. The code then restores the decomposition (`RestoreGYÖ`, `RestoreTypes` in
`lib/preprocessing.go`) and panics if the restored result fails its check. That is the tools' own safeguard, not a
theorem `[unverified]` for hw.

### 5.3 What to report

Per schema × variant (slots, role naming):

- counts: roles, relations, rank, degree, BIP, duplicate role-sets, core size (vertices/edges);
- **class** ∈ {Berge, γ, β, α, cyclic}, with the witness for the first degree that fails: an incidence cycle, a
  γ-triangle, a β-cycle (chordless incidence cycle of length ≥ 6), or the GYO residue. For α-acyclic schemas also the
  join tree;
- **hw**: exact, or [lb, ub], with the HD as JSON (bag, guard and children, in role and relation names) and the
  validator verdict;
- **ghw** and **fhw**: exact, or bounds, each labelled with the method (DP, BalancedGo GHD, clique bound,
  ρ*-improvement);
- **tw** of the primal graph (DP after the simplicial rule, or htd's upper bound);
- provenance: tool, version or commit, command, time limit, wall time.

Mind the witness semantics. P2's `is_alpha_acyclic` residue (vertex-and-edge GYO) is what the prototype reports as
`gyo_residue`, and the two agree on every packaged schema. The β-cycle and γ-triangle are new witnesses that P2 does
not compute.

### 5.4 The constructed cases for the gate, one per class boundary

The gate asks that the checker "flags a constructed cyclic case". Use one schema per boundary, so the gate also shows
the classes are told apart. `probes/schemas/*.relation-schema.json` are valid `khg-relation-schema/1.0.0` documents
(they pass `load_schema`), each written as a small trade or Wikidata-like story:

| File | Relations (roles) | Class | hw / ghw / fhw | Flag raised |
|---|---|---|---|---|
| `p6-berge-path` | employment(employee, employer), headquartered_in(employer, city) | Berge | 1 / 1 / 1 | none |
| `p6-gamma-not-berge` | sale(buyer, seller), brokered_sale(buyer, seller, broker) | γ | 1 / 1 / 1 | Berge cycle |
| `p6-beta-not-gamma` | sale(buyer, seller), brokerage(seller, broker), brokered_sale(buyer, seller, broker) | β | 1 / 1 / 1 | γ-triangle |
| `p6-alpha-not-beta` | sale, brokerage, referral(broker, buyer), brokered_sale | α | 1 / 1 / 1 | β-cycle |
| P2 `cyclic.relation-schema.json` | sale, brokerage, referral | **cyclic** | 2 / 2 / 3/2 | GYO residue = triangle |
| P2 `wikidata-shaped.relation-schema.json` | position_held, award_received, member_of_sports_team | **cyclic** | 2 / 2 / 3/2 | residue = qualifier triangle {replaces, series_ordinal, point_in_time} |
| `p6-qualifier-k5` | 10 relations, each with private subject/object roles and 2 of 5 shared qualifiers (start_time, end_time, point_in_time, series_ordinal, replaces) | **cyclic** | **3 / 3 / 5/2** | residue = K5 on the qualifiers |

The last case shows width growing with qualifier sharing, which is exactly the mechanism the Wikidata survey
measures. BalancedGo returned the same hw on all seven.

### 5.5 Results on the packaged P2 schemas (`probes/out/probe_schemas.json`)

| Schema | Slots | Roles / relations | Class | Core | tw | ghw | fhw | hw (prototype = BalancedGo) |
|---|---|---|---|---|---|---|---|---|
| fixture | core+qualifier | 30 / 11 | Berge | empty | 7 | 1 | 1 | 1 |
| fixture | +time | 32 / 11 | γ | empty | 7 | 1 | 1 | 1 |
| sample | core+qualifier | 8 / 3 | Berge | empty | 3 | 1 | 1 | 1 |
| cyclic | either | 3 / 3 | cyclic | 3 / 3 | 2 | 2 | 3/2 | 2 |
| wikidata-shaped | core+qualifier | 10 / 3 | cyclic | 3 / 3 | 4 | 2 | 3/2 | 2 |
| wikidata-shaped | +time | 12 / 3 | cyclic | 3 / 3 | 5 | 2 | 3/2 | 2 |

The wikidata-shaped rows are the qualifier effect in miniature. Core roles are private to their relation and vanish
under GYO. What stays is the triangle that the three shared qualifiers form.

---

## 6. Design decisions P6 must make

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Which hypergraph is surveyed | (a) role-name schema hypergraph (P2's); (b) plus its reified or incidence form; (c) a query workload | (a) as the primary object, stating plainly that it is the universal-join width (2.5). Report Berge because it answers (b) exactly. Leave (c) to HyperBench's Wikidata numbers, cited |
| D2 | Slots | core+qualifier; +time; +meta | core+qualifier as the headline, +time as a variant (it moves the fixture from Berge to γ). Leave meta out (`khg:end_cause` is a built-in on every interval relation and would add a universal-looking vertex) |
| D3 | Role naming (agree with P3a) | global roles (P2 F4); relation-local core roles; typed roles; Wikidata property as role | Survey at least global-qualifier with local core roles (P2's default) against fully relation-local roles. The fully local variant is trivially Berge-acyclic, so it is the control that shows the width comes from shared names |
| D4 | Set or multi-hypergraph | – | Set hypergraph for α, β, γ and the widths; multi-hypergraph for Berge; report duplicate role-sets |
| D5 | Width measures | hw only; hw + ghw + fhw + tw | All four, each labelled exact or bounded with its method (2.5, 5.3). hw is the headline (comparable with HyperBench) |
| D6 | Solver architecture | pure Python; vendor C++/Go; call binaries | Pure-Python core (classes, witnesses, reductions, small exact DP, validator) inside P6. **BalancedGo as the called binary** (MIT), log-k-decomp as a second opinion; binaries fetched and built by a script with pinned commits, not committed |
| D7 | Exactness policy | exact or nothing; bounds | Bounds with explicit methods and time limits (e.g. 600 s per k). Wikidata residues are in the size class where HyperBench itself has only bounds (3.5) |
| D8 | Reductions | none; GYO + twins; + block split | GYO + twins + block split for ghw, fhw and tw (proved safe in 5.2 and 5.1). hw on the unreduced hypergraph unless a proof or the tool's documented `-g` option is adopted |
| D9 | Gate fixtures | one cyclic case; one per boundary | One per boundary plus a width-3 qualifier case (5.4); keep P2's `cyclic` and `wikidata-shaped` |
| D10 | Baseline data | website zip; Zenodo | Zenodo 10.5281/zenodo.7180787 (CC BY 4.0), with the recomputed distribution (3.5); cite papers [1]–[5] as the website asks |
| D11 | Trust in solver output | accept; validate | Validate every decomposition (four conditions) and log disagreements. The published run data contains at least one wrong "yes" (3.5) |
| D12 | fhw exactness | fraSMT; DP; upper bound only | DP on small cores, otherwise the upper bound max ρ*(B_t) over the HD found plus a clique lower bound. fraSMT only for manual cross-checks |

---

## Probes and outputs

All under [probes/](probes/). Run with a Python venv containing scipy (and PySAT, networkx, z3, clingo and cplex for
the SAT and SMT tools), and `PYTHONPATH=<repo>/src` for the schema probes.

| File | What it does |
|---|---|
| `instances.py` | the test hypergraphs, written as `.hg`, `.pace.hgr` and `.htd.hgr` into `instances/`. The Samer Grid2D instance is read from `P6_GRID2D` and written to scratch only (its source repository has no licence) |
| `p6check.py` | the reference prototype: classes, witnesses, reductions, exact DP widths, hw search, HD validator |
| `probe_theory.py` | brute-force cross-check on 400 random hypergraphs, plus widths of the named instances → `out/probe_theory.json` |
| `probe_schemas.py` | the prototype end to end on P2's packaged schemas and the constructed ones, compared with `is_alpha_acyclic` and BalancedGo → `out/probe_schemas.json`, `out/hg/*.hg` (+ id maps) |
| `run_solvers.sh` | every external tool on every instance → `out/solvers/` |
| `run_htdleo.py`, `run_frasmt.py` | compatibility shims (4.2) |
| `scale_probe.sh` | large HyperBench instances → `out/scale/` |
| `hyperbench_baseline.py` | the hw distribution from Zenodo's `Run.csv` → `out/hyperbench_hw.json` |
| `schemas/*.relation-schema.json` | the constructed boundary cases (5.4) |
| `out/reification.json` | n-ary against reified widths (1.3) |

Other files in `probes/` (`wd_*`, `biolink_*`, `gocam_*`, `hg_measure.py`) belong to the parallel P6 data research
and are not described here.

---

## Sources

- Fagin, R. "Degrees of acyclicity for hypergraphs and relational database schemes." *Journal of the ACM* 30(3):514–550, 1983. https://dl.acm.org/doi/10.1145/2402.322390 (abstract via OpenAlex: https://api.openalex.org/works/doi:10.1145/2402.322390; full text not accessible, HTTP 403)
- Beeri, C., Fagin, R., Maier, D., Yannakakis, M. "On the Desirability of Acyclic Database Schemes." *Journal of the ACM* 30(3):479–513, 1983. https://dl.acm.org/doi/10.1145/2402.322389 (abstract via OpenAlex)
- Brault-Baron, J. "Hypergraph Acyclicity Revisited." *ACM Computing Surveys* 49(3), 2016, pp. 1–26. https://doi.org/10.1145/2983573 ; arXiv:1403.7076, https://arxiv.org/abs/1403.7076 (read in full)
- Tarjan, R. E., Yannakakis, M. "Simple Linear-Time Algorithms to Test Chordality of Graphs, Test Acyclicity of Hypergraphs, and Selectively Reduce Acyclic Hypergraphs." *SIAM Journal on Computing* 13(3):566–579, 1984. https://doi.org/10.1137/0213035 (metadata via OpenAlex; cited through Brault-Baron and Ordyniak et al.)
- Ordyniak, S., Paulusma, D., Szeider, S. "Satisfiability of acyclic and almost acyclic CNF formulas." *Theoretical Computer Science* 481:85–99, 2013. arXiv:1104.4279, https://arxiv.org/abs/1104.4279
- Duris, D. "Some characterizations of γ and β-acyclicity of hypergraphs." *Information Processing Letters* 112(16):617–620, 2012. https://doi.org/10.1016/j.ipl.2012.05.005 (metadata via OpenAlex; content via Brault-Baron)
- D'Atri, A., Moscarini, M. "Acyclic hypergraphs: their recognition and top-down vs bottom-up generation." Technical Report R.29, IASI-CNR, 1982 (cited through Brault-Baron; not read `[unverified]`)
- Gottlob, G., Leone, N., Scarcello, F. "Hypertree Decompositions and Tractable Queries." *Journal of Computer and System Sciences* 64(3):579–627, 2002. https://doi.org/10.1006/jcss.2001.1809 ; arXiv:cs/9812022, https://arxiv.org/abs/cs/9812022
- Adler, I., Gottlob, G., Grohe, M. "Hypertree width and related hypergraph invariants." *European Journal of Combinatorics* 28(8):2167–2181, 2007. https://doi.org/10.1016/j.ejc.2007.04.013 (result cited through Grohe and Marx 2014; not read directly)
- Grohe, M., Marx, D. "Constraint Solving via Fractional Edge Covers." *ACM Transactions on Algorithms* 11(1), article 4, 2014. https://doi.org/10.1145/2636918 ; arXiv:1711.04506, https://arxiv.org/abs/1711.04506
- Gottlob, G., Miklós, Z., Schwentick, T. "Generalized hypertree decompositions: NP-hardness and tractable variants." *Journal of the ACM* 56(6), article 30, 2009. https://doi.org/10.1145/1568318.1568320
- Fischl, W., Gottlob, G., Pichler, R. "General and Fractional Hypertree Decompositions: Hard and Easy Cases." *PODS 2018*, pp. 17–32. https://doi.org/10.1145/3196959.3196962
- Gottlob, G., Lanzinger, M., Pichler, R., Razgon, I. "Complexity Analysis of Generalized and Fractional Hypertree Decompositions." *Journal of the ACM* 68(5), 2021, pp. 1–50. https://doi.org/10.1145/3457374 ; arXiv:2002.05239, https://arxiv.org/abs/2002.05239
- Marx, D. "Approximating fractional hypertree width." *ACM Transactions on Algorithms* 6(2), article 29, 2010. https://doi.org/10.1145/1721837.1721845 (result cited through GLPR)
- Marx, D. "Tractable hypergraph properties for constraint satisfaction and conjunctive queries." arXiv:0911.0801, 2009 (JACM 2013). https://arxiv.org/abs/0911.0801 (abstract read)
- Moll, L., Tazari, S., Thurley, M. "Computing hypergraph width measures exactly." *Information Processing Letters* 112(6):238–242, 2012. https://doi.org/10.1016/j.ipl.2011.12.002 ; arXiv:1106.4719, https://arxiv.org/abs/1106.4719
- Lanzinger, M., Okulmus, C., Pichler, R., Selzer, A., Gottlob, G. "Soft and Constrained Hypertree Width." arXiv:2412.11669, 2024. https://arxiv.org/abs/2412.11669 (abstract read)
- Jiang, Z., Koch, C., Lindner, P., Pichler, R., Wang, Q. "Rerootable Hypertree Decompositions." arXiv:2608.17853, 2026. https://arxiv.org/abs/2608.17853 (abstract read)
- Fischl, W., Gottlob, G., Longo, D. M., Pichler, R. "HyperBench: A Benchmark and Tool for Hypergraphs and Empirical Findings." *PODS 2019*, pp. 464–480. https://doi.org/10.1145/3294052.3319683 ; arXiv:1811.08181, https://arxiv.org/abs/1811.08181
- Fischl, W., Gottlob, G., Longo, D. M., Pichler, R. "HyperBench: A Benchmark and Tool for Hypergraphs and Empirical Findings." *ACM Journal of Experimental Algorithmics* 26, 2021, pp. 1–40. https://doi.org/10.1145/3440015 ; arXiv:2009.01769, https://arxiv.org/abs/2009.01769
- HyperBench web interface, TU Wien DBAI, checked 2026-09-24. http://hyperbench.dbai.tuwien.ac.at/ ; manual: http://hyperbench.dbai.tuwien.ac.at/downloads/manual.pdf
- Gottlob, G., Lanzinger, M., Okulmus, C., Pichler, R. "Experimental Data for log-k-decomp." Zenodo, v4, 2023, CC BY 4.0. https://doi.org/10.5281/zenodo.7180787
- Gottlob, G., Lanzinger, M., Okulmus, C., Pichler, R. "Fast Parallel Hypertree Decompositions in Logarithmic Recursion Depth." *PODS 2022*, pp. 325–336. https://doi.org/10.1145/3517804.3524153 ; arXiv:2104.13793, https://arxiv.org/abs/2104.13793 (the TODS extended version named in the Zenodo README was not looked up `[unverified]`)
- Gottlob, G., Okulmus, C., Pichler, R. "Fast and parallel decomposition of constraint satisfaction problems." *Constraints* 27(3):284–326, 2022. https://doi.org/10.1007/s10601-022-09332-1 (BalancedGo; metadata via OpenAlex)
- Gottlob, G., Samer, M. "A backtracking-based algorithm for hypertree decomposition." *ACM Journal of Experimental Algorithmics* 13, 2008. https://doi.org/10.1145/1412228.1412229 ; arXiv:cs/0701083
- Schidler, A., Szeider, S. "Computing optimal hypertree decompositions with SAT." *IJCAI 2021* (per the Zenodo record) and *Artificial Intelligence* 325:104015, 2023. https://doi.org/10.1016/j.artint.2023.104015 ; code: https://zenodo.org/records/4742100 and https://github.com/ASchidler/htdsmt
- Fichte, J. K., Hecher, M., Lodha, N., Szeider, S. "An SMT Approach to Fractional Hypertree Width." *CP 2018*, LNCS, pp. 109–127. https://doi.org/10.1007/978-3-319-98334-9_8 ; code: https://github.com/daajoe/frasmt
- "Fast Hypertree Decompositions via Linear Programming: Fractional and Generalized" (Ralph). *Proceedings of the ACM on Management of Data*, 2025. https://doi.org/10.1145/3725296 (search-result description only; authors and code not verified `[unverified]`)
- PACE 2019 hypertree decomposition format. https://pacechallenge.org/2019/htd/htd_format/
- Solver repositories probed: https://github.com/cem-okulmus/BalancedGo · https://github.com/cem-okulmus/log-k-decomp · https://github.com/dmlongo/newdetkdecomp · https://github.com/TUfischl/newdetkdecomp · https://github.com/daajoe/detkdecomp · https://github.com/mabseher/htd · https://github.com/ASchidler/htdsmt · https://github.com/daajoe/frasmt
- Wikipedia, "Hypergraph" (acyclicity section), checked 2026-09-24. https://en.wikipedia.org/wiki/Hypergraph (used only as a cross-check of the hierarchy and of the linear-time claims)
- Korchemna, V., Lokshtanov, D., Saurabh, S., Surianarayanan, V., Xue, J. "Efficient Approximation of Fractional Hypertree Width." arXiv:2409.20172, 2024. https://arxiv.org/abs/2409.20172 (abstract read)
- PyPI JSON API, package names probed 2026-09-24. https://pypi.org/pypi/<name>/json
