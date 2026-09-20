---
title: Limitations and failure modes of knowledge hypergraphs
type: survey
status: draft
tags: [limitations, failure-modes, critique, sparsity, arity, leakage, provenance, query-language, visualisation, cost, versioning, interoperability]
created: 2026-09-20
updated: 2026-09-20
---

# Limitations and failure modes

Twelve ways a knowledge hypergraph project goes wrong, each with the evidence that it is a real
problem rather than a theoretical worry, and where possible a mitigation. Ordered roughly from
"affects the data" through "affects the model" to "affects the organisation".

Balance note: none of these is a reason not to use a KHG. They are the costs that belong on the other
side of the ledger from the benefits in
[when-to-use-and-when-not.md](when-to-use-and-when-not.md).

---

## 1. N-ary facts are rarer than the motivating statistic suggests

Nearly every n-ary KG paper opens with the same justification. Wen et al. report that "in Freebase,
more than 1/3 of the entities participate in non-binary relations"
([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)), and this is widely
restated — e.g. "more than 30% of its entities are involved in such hyper-relational facts"
([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf)).

**Read it carefully: that is a statistic about *entities*, not about *facts*.** An entity
participates in one n-ary fact among hundreds of binary ones and still counts. The fact-level
proportions in the benchmarks are much lower
([Wei et al., 2025](https://arxiv.org/abs/2506.08970), Table 1):

| Dataset | Source | Entities | Roles | Arity range | **Proportion of n-ary facts** | Facts |
|---|---|---|---|---|---|---|
| JF17K | Freebase | 28,645 | 501 | 2–6 | 45.9% | 100,947 |
| WikiPeople | Wikidata | 47,765 | 193 | 2–9 | **11.6%** | 382,229 |
| WD50K | Wikidata | 47,155 | 531 | 2–67 | **13.6%** | 236,507 |

JF17K's 45.9% is the outlier, and JF17K is also the dataset with the leakage problem (§5). On the two
Wikidata-derived sets, roughly **seven facts in eight are plain triples**.

Consequences:

- The n-ary machinery earns its cost on 12–14% of the data. If your motivation is "the whole KB
  should be a hypergraph", the data may not support it.
- Benchmark scores are dominated by the binary majority. StarE's authors observe this directly of
  WikiPeople: only a small share of facts carry a qualifier, "This fact renders WikiPeople less
  sensitive to hyper-relational models as performance on triple-only facts dominates the overall
  score" ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)).

**Mitigation.** Report metrics split by arity, always. Decide whether the n-ary subset is
*important* rather than *large* — a KB where 5% of facts are n-ary but they are the clinically
decisive ones is a good candidate; one where they are trivia is not.

## 2. Sparsity worsens with arity, and it breaks learning

The data does not just have fewer n-ary facts; it has exponentially fewer as arity grows. JF17K
training tuples by arity ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137), Table 4):
36,293 at arity 2, 18,846 at arity 3, 6,772 across arities 4–6 combined. Every increment in arity
roughly halves the evidence while multiplying the space of possible tuples by |E|.

The effect on models is severe. The same table gives Hit@10 for the reification baseline r-SimplE:
0.478 at arity 2, **0.025** at arity 3, **0.017** at arities 4–6. Fatemi et al. diagnose it precisely,
and the diagnosis matters:

> "reification for the r-SimplE model does not work well; this is because the reification process
> introduces auxiliary entities for which the model does not learn appropriate embeddings because
> these auxiliary entities appear in very few facts."
> ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137))

**This is a failure of a learning method, not of a representation.** The same authors state that with
reification "the binary relations created are equivalent to the original representation and
reification does not lose information during conversion". Papers that cite the 0.025 number as
evidence that "reification loses information" are misreading their own source. See
[hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md) §4.

**Mitigation.** Share parameters across arities (HypE's position-dependent convolutions, S2S's
sparse sharing); do not train a separate model per arity; consider collapsing rare high-arity
relations to their most informative roles.

## 3. Role-position ambiguity

Two incompatible conventions coexist under the name "knowledge hypergraph".

- **Positional.** A fact is an ordered tuple `r(e₁,…,e_k)`; position *i* is the role
  ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)).
- **Role-named.** A fact is a function from named roles to entities; Wen et al. introduced this
  specifically because they judged the positional view defective: the algebraic definition of an
  n-ary relation as a subset of N^J "is incomplete, in the sense that the role of each coordinate in
  the cartesian product is not specified" ([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)).

Concrete failures of the positional convention:

- **The same entity in two positions.** `flies_between(AirCanada, Toronto, Toronto)` — is that a
  round trip, a data error, or a collapsed role? Position gives no help.
- **Symmetric roles.** `co_authors(A, B, C)` has no meaningful ordering, but a positional model will
  learn one from the data's accidental ordering and then fail on permuted inputs.
- **Optional roles.** Fatemi et al.'s arity is "fixed for each relation"; a purchase that sometimes
  records a discount code and sometimes does not needs either two relations or a null convention.
- **Schema drift.** Inserting a new argument in the middle of a positional relation invalidates every
  stored tuple. With named roles it is additive.

The third convention — an unordered set of role–value pairs (NaLP, RAM) — avoids position but,
per the 2025 survey, "fails to account for the varying importance or prominence of different entities
within the same fact" ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)).

**Mitigation.** Use named roles in storage and interchange even if a positional encoding is used
inside a model. Never let a positional order become the only record of role semantics.

## 4. Arity explosion and the typed-hyperedge blow-up

If each distinct *combination* of roles becomes its own relation type, the type system explodes.
Galkin et al. state the argument as a reason to prefer qualifiers over hyperedges:

> "Combining a certain set of main and qualifying relations into one abstract rk() would lead to a
> combinatorial explosion of typed hyperedges since, in principle, any relation could be used in a
> qualifier, and there the amount of qualifiers per fact is not limited."
> ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847))

The empirical shape of the tail: WD50K has arities from 2 to **67**
([Wei et al., 2025](https://arxiv.org/abs/2506.08970)). Any design that allocates parameters,
index structures or schema entries per arity has to cope with a 67-argument fact that occurs once.

**Mitigation.** Separate *core roles* (fixed, typed, few) from *qualifiers* (open-ended, optional) —
which is exactly the Wikidata statement design. This is the strongest practical argument for the
hyper-relational model over the flat n-ary one; see [open-debates.md](open-debates.md) §2.

## 5. Evaluation leakage

The most-used n-ary benchmark has a documented leak. Galkin et al. analysed JF17K:

> "The authors of JF17K reported the dataset to contain redundant entries. In our own analysis, we
> detected that about **44.5% of the test statements share the same main (s,r,o) triple as the train
> statements**. We consider this fact as a major data leakage which allows triple-based models to
> memorize subjects and objects appearing in the test set."
> ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847))

JF17K also has no validation split in its original release; Fatemi et al. note "For JF17K, we randomly
select 20% of the train set as validation" ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)),
so different papers' JF17K numbers are not strictly comparable. Despite all this, JF17K remains one
of the three standard benchmarks in the 2025 survey.

WD50K was built to fix this: "To eliminate test set leakages we remove all statements from train and
validation sets that share the same main triple (s,p,o) with test statements"
([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)).

The RAG side has a different leakage shape — benchmarks whose questions are generated from the indexed
corpus by the same model family that builds the index. See
[critical-reading-of-hypergraph-rag-claims.md](critical-reading-of-hypergraph-rag-claims.md) §2.2.

**Mitigation.** Prefer WD50K over JF17K, or report both and say so. For any home-grown benchmark, de-
duplicate on the *core* of the fact, not on the whole fact.

## 6. No standard query language

Of the fifteen formalisms in [formalism-comparison-matrix.md](formalism-comparison-matrix.md), the
n-ary hypergraph models are the ones with no standardised query language. Worse, the newest standard
explicitly declines the feature: GQL, ISO/IEC 39075:2024 (published 12 April 2024), standardises the
property-graph model and "does not include n-ary relationships linking more than two entities"
([Wikipedia, Graph Query Language](https://en.wikipedia.org/wiki/Graph_Query_Language), checked
2026-09-20; ISO text paywalled `[unverified]`). SPARQL is defined over triples. TypeQL is expressive
over n-ary relations but is a single vendor's language.

Practical consequences: no portable queries, no BI-tool connectors, no shared optimiser literature,
and every project writing its own traversal layer. This is the single biggest reason production
systems store bipartite encodings in a standard graph or triple store.

**Mitigation.** Define the n-ary semantics in your schema, then express queries against a *standard*
encoding (relation-instance nodes in SPARQL, event nodes in Cypher/GQL). Keep the n-ary layer in your
application model, not in a non-portable storage engine, unless the schema enforcement is worth the
lock-in.

## 7. Expansion blow-up, in both directions

Every way of getting an n-ary fact into a binary store costs something quantifiable.

| Encoding | Size cost for one arity-k fact | What breaks |
|---|---|---|
| RDF reification | 4 triples *per reified statement*; "would increase the size of the data sets by at least four times" ([Nguyen, Bodenreider, Sheth, 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4350149/)) | No formal link between the reification and the asserted triple |
| Relation-instance / intermediate node | 1 node + k edges | Query verbosity; nothing enforces the node's fact-hood |
| Star-to-clique | k(k−1)/2 edges, quadratic in arity | **Lossy**: spurious tuples become derivable ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)) |
| Clique expansion of a hypergraph | as above, per hyperedge | "hypergraph-to-graph reductions are inevitably lossy" ([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295)) |
| Tensor | an order-k tensor | Memory exponential in arity |

In the other direction, *keeping* the hypergraph costs index structures that no mainstream database
provides natively.

## 8. Extraction error compounds in LLM pipelines

An LLM-built KHG multiplies error sources relative to an LLM-built KG, because the extractor must get
the *grouping* right as well as the entities and the predicate. A binary extractor that misses one
participant produces a slightly incomplete graph; an n-ary extractor that misses one participant
produces a **wrong fact** — `treats(drug, disease)` where the truth was
`treats(drug, disease, dosage, population)`, and the dropped population qualifier may invert the
claim's applicability.

Evidence that the upstream step is already unreliable at the binary level: Han et al. report that
KG-based GraphRAG underperforms partly because of incomplete graph coverage, with entity retrieval
around 65% ([Han et al., 2025/2026](https://arxiv.org/abs/2502.11371)). Microsoft's GraphRAG needed
a "gleaning" loop — re-asking the model whether entities were missed, with "a logit bias of 100 to
force a yes/no decision" — precisely because single-pass extraction under-recalls
([Edge et al., 2024](https://arxiv.org/abs/2404.16130), as quoted in
[../03-construction/llm-based-khg-construction.md](../03-construction/llm-based-khg-construction.md)).

The hypergraph-RAG systems layer self-reported confidence on top: HyperGraphRAG attaches an
LLM-assigned score in (0,10] to each hyperedge and (0,100] to each entity
([Luo et al., 2025](https://arxiv.org/abs/2503.21322)). These are model self-assessments, not
calibrated probabilities, and treating them as weights in retrieval propagates the model's
overconfidence into the index.

**Mitigation.** Evaluate extraction separately from retrieval, with a human-annotated gold set of
n-ary facts. Measure *grouping* accuracy (did the right entities end up in the right hyperedge?), not
just entity F1. Treat LLM confidence scores as a heuristic sort key and never as a probability.
See [../03-construction/n-ary-relation-extraction-from-text.md](../03-construction/n-ary-relation-extraction-from-text.md).

## 9. Provenance is what you lose when you flatten

If a five-participant fact is stored as ten pairwise edges, the question "which source asserted
this?" no longer has a well-defined subject: the source asserted the *fact*, not the ten projections.
Attaching the citation to each edge over-claims (each pairwise edge alone was never asserted); to
one edge under-claims; to a fact node means you have reified after all.

This is why provenance requirements are one of the cleanest signals *for* a first-class fact object,
whether you call it a hyperedge, a Wikidata statement, an RDF 1.2 triple term, or an event node.
RDF 1.2's design acknowledges the distinction explicitly: triple terms "are used to *relate* to
propositions, not to state them" ([RDF 1.2 Primer, Group Note draft, 17 September 2026](https://www.w3.org/TR/rdf12-primer/)),
which is what lets you record "source X claims P" without asserting P.

Related risk: provenance loss during **entity resolution**. Merging two entities rewrites every
hyperedge that mentions them, and a naive merge destroys the record of which extraction produced
which binding. See
[../03-construction/entity-resolution-and-canonicalisation.md](../03-construction/entity-resolution-and-canonicalisation.md).

## 10. Retrieval and query cost

Hyperedge retrieval is not free. Measured costs from the hypergraph-RAG literature
([Luo et al., 2025](https://arxiv.org/abs/2503.21322), Table 3): HyperGraphRAG costs 3.084 s and
$0.0063 per 1k tokens to construct the index, then $3.184 per 1k queries against StandardRAG's
$1.016 — about **3.1× the per-query cost** plus a construction pass the vector baseline does not
need.

The general picture from the neutral benchmark is starker. Average prompt tokens per query
([Xiang et al., 2026](https://arxiv.org/abs/2506.05690), Tables 6–7): vanilla RAG 879–954;
HippoRAG2 ~1,010; Fast-GraphRAG ~4,250; HippoRAG ~7,275; MS-GraphRAG (local) ~39,000; LightRAG
~100,500; MS-GraphRAG (global) ~332,000. Their conclusion: "GraphRAG's structured pipeline incurs
non-trivial token overhead."

Structurally, the cost driver is that a hyperedge is a *set*, so "find all facts containing entities
A and B" is a set-intersection query, and "find facts sharing ≥ 2 entities with this one" — the
`s`-overlap query that makes hypergraphs interesting ([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295))
— has no index in any mainstream store.

**Mitigation.** Budget tokens and dollars per query as a first-class design constraint. Prefer
retrieval designs with compact prompts (the ~10³-token range) over community-summarisation designs.

## 11. Maintenance, versioning and identity

Four problems that only appear after the KHG is in production.

- **Hyperedge identity.** What makes two extracted hyperedges "the same fact"? If identity is the set
  of participants, adding a qualifier creates a new fact and orphans the old one's provenance and
  corrections. If identity is a surrogate key, you need an entity-resolution policy for facts, not
  just for entities.
- **Update semantics.** LightRAG-descended pipelines merge incrementally by taking "the union of the
  node sets and edge sets" (quoted in
  [../03-construction/llm-based-khg-construction.md](../03-construction/llm-based-khg-construction.md)).
  Union never retracts. A corrected source cannot remove a wrong hyperedge.
- **Schema evolution.** Adding a role to a positional relation invalidates stored tuples (§3).
- **Vendor and library lifetime.** Kùzu, a well-regarded embedded property-graph database, was
  archived by its owner on 10 October 2025 — "This repository was archived by the owner on
  Oct 10, 2025. It is now read-only" ([kuzudb/kuzu](https://github.com/kuzudb/kuzu), checked
  2026-09-20). Niche formalisms have thinner ecosystems and therefore shorter expected library
  lifetimes.

**Mitigation.** Give every hyperedge a stable surrogate identifier plus a content hash of its core
roles; keep an append-only assertion log with retraction, not a mutable graph; pin the storage format
to something you can re-read without the library that wrote it.

## 12. Interoperability gaps

There is no single interchange format for *knowledge* hypergraphs.

- The higher-order network community has one: HIF, "a standard for higher-order network data to
  facilitate seamless data exchange between higher-order network libraries", supported by XGI,
  HyperNetX, HypergraphX, HAT and SimpleHypergraphs.jl
  ([HIF-standard](https://github.com/pszufe/HIF-standard), published in *Network Science*, 2025).
  But HIF describes set systems with attributes; it has no notion of typed roles, qualifiers,
  provenance or nesting.
- The KR community has RDF 1.2, which has triple terms but by its own text can express relations over
  more than two entities "only indirectly"
  ([RDF 1.2 Concepts, W3C CR, 7 April 2026](https://www.w3.org/TR/rdf12-concepts/)).
- The n-ary embedding community has per-dataset TSV conventions.
- Atomese, TypeQL and HypergraphDB each have their own serialisation.

No published mapping connects HIF to RDF-star or to a role-based n-ary model `[unverified — none
found in the searches run here]`. Consequence: a hypergraph built for RAG cannot be loaded into XGI
for structural analysis without a bespoke converter that discards the roles, and a hypergraph analysed
in XGI cannot be published as linked data without a bespoke converter that invents them.

**Mitigation.** Store role-based n-ary facts in a schema you control (JSON-LD with a relation-instance
pattern round-trips to RDF), and generate HIF as a lossy *export* for network analysis rather than
using it as the source of truth. See
[../04-storage-and-formats/hif-hypergraph-interchange-format.md](../04-storage-and-formats/hif-hypergraph-interchange-format.md)
and [../04-storage-and-formats/property-graph-emulation-patterns.md](../04-storage-and-formats/property-graph-emulation-patterns.md).

---

## Related

- Decision framework and anti-patterns: [when-to-use-and-when-not.md](when-to-use-and-when-not.md)
- Where the field disagrees about these: [open-debates.md](open-debates.md)
- Terminology traps: [glossary-of-confusable-terms.md](glossary-of-confusable-terms.md)
- Visual complexity in detail: [../06-visualization/visual-encodings-catalogue.md](../06-visualization/visual-encodings-catalogue.md)
  — deciding whether a hypergraph admits a vertex- or hyperedge-based Venn-style diagram is
  NP-complete ([Johnson & Pollak, 1987](https://doi.org/10.1002/jgt.3190110306)), and subset-standard
  drawings degrade past roughly 5–10 hyperedges.

## Sources

- Aksoy, S., Joslyn, C., Ortiz Marrero, C., Praggastis, B., Purvine, E. "Hypernetwork science via high-order hypergraph walks." *EPJ Data Science* 9(1):16, 2020. https://arxiv.org/abs/1906.11295
- Edge, D., et al. "From Local to Global: A Graph RAG Approach to Query-Focused Summarization." arXiv:2404.16130, 2024. https://arxiv.org/abs/2404.16130
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs." EMNLP 2020. https://arxiv.org/abs/2009.10847
- Han, H., et al. "RAG vs. GraphRAG: A Systematic Evaluation and Key Insights." arXiv:2502.11371, 2025, rev. 2026. https://arxiv.org/abs/2502.11371
- HIF-standard repository (Hypergraph Interchange Format). https://github.com/pszufe/HIF-standard (checked 2026-09-20); reference paper in *Network Science*, 2025
- Johnson, D. S., Pollak, H. O. "Hypergraph planarity and the complexity of drawing Venn diagrams." *Journal of Graph Theory* 11(3):309–325, 1987. https://doi.org/10.1002/jgt.3190110306
- kuzudb/kuzu repository (archived 10 October 2025). https://github.com/kuzudb/kuzu (checked 2026-09-20)
- Luo, H., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025; arXiv:2503.21322. https://arxiv.org/abs/2503.21322
- Nguyen, V., Bodenreider, O., Sheth, A. "Don't like RDF reification? Making statements about statements using singleton property." WWW 2014. https://pmc.ncbi.nlm.nih.gov/articles/PMC4350149/
- Rosso, P., Yang, D., Cudré-Mauroux, P. "Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction." WWW 2020. https://exascale.info/assets/pdf/rosso2020www.pdf
- W3C. "RDF 1.2 Concepts and Abstract Data Model." W3C Candidate Recommendation, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. "RDF 1.2 Primer." W3C Group Note Draft, 17 September 2026. https://www.w3.org/TR/rdf12-primer/
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. "A Survey of Link Prediction in N-ary Knowledge Graphs." arXiv:2506.08970, 2025. https://arxiv.org/abs/2506.08970
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases beyond Binary Relations." IJCAI 2016. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
- Wikipedia. "Graph Query Language." https://en.wikipedia.org/wiki/Graph_Query_Language (checked 2026-09-20)
- Xiang, Z., et al. "When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation." ICLR 2026; arXiv:2506.05690. https://arxiv.org/abs/2506.05690
