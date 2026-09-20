---
title: Hypergraph construction from structured data — and when it is "knowledge"
type: survey
status: draft
tags: [hypergraph, construction, tables, relational-databases, co-occurrence, event-logs, datasets, higher-order]
created: 2026-09-20
updated: 2026-09-20
---

# Hypergraph construction from structured data

Most hypergraphs in the wild were never extracted from text. They fall out of data that is *already*
group-structured: papers with several authors, baskets with several items, table rows with several cells,
database joins over several keys, events touching several objects. This note catalogues those sources, the
standard construction for each, and then argues about the question that matters for this knowledge base:
**when does such a hypergraph deserve the label "knowledge hypergraph", and when is it merely an
interaction hypergraph?**

It is the second alternative entry point in the
[construction pipeline](construction-pipeline-overview.md); the first, lifting an existing KG, is covered
in [from knowledge graphs to hypergraphs](from-knowledge-graphs-to-hypergraphs.md).

## 1. The distinction, stated up front

| | Interaction hypergraph | Knowledge hypergraph |
|---|---|---|
| Node | one kind of thing (authors, items, tags) | typed entities, canonicalised |
| Hyperedge | an *observed group* | an *asserted fact* |
| Relation type | none, or one implicit type | named, from a schema |
| Roles | none — participants are interchangeable | each participant has a role or position |
| Truth | the group happened | the fact is claimed to hold |
| Provenance | the record it came from | required, per fact |

Fatemi et al.'s definition of the target is a set of tuples "of the form r(e1, e2, ..., ek)"
([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)) — note the `r`. A co-authorship hyperedge has no
`r`, or rather has exactly one, `coauthored`, which is why it is a degenerate KHG: a knowledge hypergraph
with a single relation type and no roles. That is not a criticism; it is a statement of what you get and
what you have to add.

The higher-order-networks literature is explicit that the representation is a modelling *choice*, not a
property of the data, and that the choice changes the conclusions
([Torres et al., 2020](https://arxiv.org/abs/2006.02870); [Battiston et al., 2020](https://arxiv.org/abs/2006.01764)).
Their worked examples are co-authorship and email — precisely the sources below.

## 2. Co-occurrence and group-membership data

The canonical public collection is Austin Benson's hypergraph dataset page, assembled for the
simplicial-closure work ([Benson et al., 2018](https://arxiv.org/abs/1802.06916)). The constructions are
worth reading as a list, because each is a different answer to "what is a group here"
([hypergraph datasets](https://www.cs.cornell.edu/~arb/data/), checked 2026-09-20):

- **coauth-DBLP / coauth-MAG-Geology / coauth-MAG-History** — nodes are authors, hyperedges are "sets of
  co-authors on papers".
- **tags-stack-overflow / tags-math-sx / tags-ask-ubuntu** — nodes are tags, hyperedges are "sets of tags
  applied to questions".
- **threads-stack-overflow / threads-math-sx / threads-ask-ubuntu** — nodes are users, hyperedges are
  "sets of users asking and answering questions on threads".
- **NDC-substances** — nodes are substances, hyperedges are "sets of substances making up drugs";
  **NDC-classes** — "sets of classifications applied to drugs".
- **DAWN** — nodes are drugs, hyperedges are "sets of drugs used by patients recorded in emergency room
  visits".
- **congress-bills** — nodes are congresspersons, hyperedges are "sets of congresspersons cosponsoring
  bills".
- **email-Enron / email-Eu** — nodes are email addresses, hyperedges are "sets of email addresses on
  emails".
- **contact-high-school / contact-primary-school** — nodes are people, hyperedges are "groups of people in
  contact".

Three observations. (i) All are *temporal* — each hyperedge has a timestamp — which makes them the natural
testbed for the dynamic constructions in
[incremental construction](incremental-and-streaming-construction.md). (ii) Several have a latent role
structure that the representation discards: an email hyperedge has a sender and recipients; a thread has
an asker and answerers; a bill has a sponsor and cosponsors. Recovering that is exactly the step from
interaction hypergraph to knowledge hypergraph. (iii) Substances-in-a-drug and drugs-in-a-visit are
genuinely unordered sets with no roles — those are interaction hypergraphs all the way down, and trying to
impose roles would be a mistake.

**Market baskets** are the same construction: nodes are products, a hyperedge is one transaction. NDC-
substances and DAWN are the published stand-ins. The classical data-mining reading of such data —
frequent itemsets — is a question about dense sub-hypergraphs, which belongs to the analysis sections
rather than here.

## 3. Tables: rows (and columns) as hyperedges

A table row joins several cell values; treating the row as a hyperedge over its cells is the obvious
construction, and HYTREL shows it is also the one with the right invariances: the model "captures the
permutation invariances and three more structural properties of tabular data by using hypergraphs — where
the table cells make up the nodes and the cells occurring jointly together in each row, column, and the
entire table are used to form three different types of hyperedges"
([Chen et al., 2023](https://arxiv.org/abs/2307.08623), NeurIPS 2023). Three hyperedge types (row, column,
whole table) rather than one is the detail most ad-hoc table-to-hypergraph code gets wrong.

A row-hyperedge is not yet knowledge: the cells are strings, the columns are unnamed, and the relation
between them is implicit. Supplying the missing parts is the **semantic table interpretation** task, run
as the SemTab challenge, whose three annotation subtasks are defined as
([SemTab 2020 challenge page](https://www.cs.ox.ac.uk/isg/challenges/sem-tab/2020/), checked 2026-09-20):

- **CEA** — "Matching a cell to a KG entity" → gives node identity;
- **CTA** — "Assigning a semantic type (e.g., a KG class) to a column" → gives argument types;
- **CPA** — "Assigning a KG property to the relationship between two columns" → gives relation names.

CEA + CTA + CPA over a row is, structurally, exactly the schema of an n-ary fact: canonical entities, typed
positions, a named relation. A table plus its SemTab annotations *is* a knowledge hypergraph; a table alone
is not.

## 4. Relational databases

Two different hypergraphs come out of a relational database, and they are routinely confused.

**The schema hypergraph.** Nodes are attributes, hyperedges are relation schemes. This is the object of
classical database theory, where acyclicity of that hypergraph governs whether joins behave well
([Beeri et al., 1983](https://dl.acm.org/doi/10.1145/2402.322389);
[Fagin, 1983](https://dl.acm.org/doi/10.1145/2402.322390)). It carries schema-level knowledge, not facts.

**The data hypergraph.** Nodes are tuples or key values, and a hyperedge is one row, or one row of a join
across foreign keys. This is the KHG-relevant one: a row of `prescription(patient, drug, dose, date)` is a
4-ary fact with named roles supplied by the column names — i.e. a relational database with a well-designed
schema is *already* a knowledge hypergraph whose relation names are table names and whose roles are column
names. The modern ML framing of this is relational deep learning, which builds a graph over rows linked by
primary–foreign key relationships ([Fey et al., 2023](https://arxiv.org/abs/2312.04615)); the hypergraph
reading — a multi-way join result as one hyperedge — is the higher-order version of the same idea.

The practical consequence for KHG construction is worth stating plainly: **if your source is a relational
database, do not extract text from it and re-extract facts with an LLM.** Map tables to relation types and
columns to roles. The n-ary structure is already there, with exact identity and exact provenance.

## 5. Event logs and object-centric process data

An event in a business process touches several objects at once — an order, several items, an invoice, a
customer — which is a hyperedge with roles. The OCEL 2.0 standard makes this explicit: relative to its
predecessor "it can depict changes in objects, provide information on object relationships, and qualify
these relationships to other objects or specific events", and it ships "three exchange formats: a
relational database (SQLite), XML, and JSON format"
([Berti et al., 2024](https://arxiv.org/abs/2403.01975)). *Qualified* event-to-object relationships are
role labels in the sense of this knowledge base — OCEL 2.0 is, in effect, a serialisation format for
timestamped n-ary facts with roles, developed independently of the KHG literature. Anyone building a
temporal KHG over operational data should look at it before inventing a format.

## 6. Feature-based construction: hypergraphs as a modelling device

A fourth family constructs hyperedges where no groups were observed at all, by neighbourhood in a feature
space. The hypergraph-learning literature treats this as a standard preprocessing step
([Gao et al., 2022](https://doi.org/10.1109/TPAMI.2020.3039374), *IEEE TPAMI*), and the DHG library exposes
it as constructors on the `Hypergraph` class (version 0.9.7, checked 2026-09-20):

- `from_feature_kNN(features, k)` — "Construct the hypergraph from the feature matrix. Each hyperedge in
  the hypergraph is constructed by the central vertex an[d] its k-1 neighbor vertices", yielding a
  k-uniform hypergraph with as many hyperedges as vertices;
- `from_graph(graph)` — "Each edge in the graph is treated as a hyperedge", giving a 2-uniform hypergraph;
- `from_graph_kHop(graph, k)` — "Each hyperedge ... is constructed by the central vertex and its k-Hop
  neighbor vertices";
- `from_bigraph(bigraph)` — vertices of one side become vertices, vertices of the other become hyperedges
  ([DHG API documentation](https://deephypergraph.readthedocs.io/en/latest/api/dhg.html)).

These are emphatically **not** knowledge hypergraphs. Nothing is asserted; the hyperedges encode similarity
chosen by the modeller. `from_bigraph` is worth flagging separately because it is the inverse of the
bipartite encoding that KHG-RAG systems use for *storage* (HyperGraphRAG stores `V_B = V ∪ E_H`; see
[LLM-based KHG construction](llm-based-khg-construction.md)) — the same transformation, used in opposite
directions for opposite reasons.

## 7. A test: is this a knowledge hypergraph?

Five questions. Each "no" is a construction step you still owe.

1. **Identity** — do nodes denote canonical entities, or raw strings? (If raw: see
   [entity resolution](entity-resolution-and-canonicalisation.md).)
2. **Relation type** — does each hyperedge carry a named relation from a vocabulary? (If not: see
   [schema induction](schema-induction-and-ontology-alignment.md).)
3. **Roles** — does each incidence carry a role or a meaningful position?
4. **Assertion** — does the hyperedge claim something is true, such that it could be wrong?
5. **Provenance** — can you say where the hyperedge came from and when it was believed?

Applying it:

| Source | Identity | Relation type | Roles | Assertion | Provenance |
|---|---|---|---|---|---|
| Co-authorship | partly (author disambiguation is hard) | one implicit | no | yes (the paper exists) | yes (the paper) |
| Tags on questions | yes (tags are controlled) | one implicit | no | weakly | yes |
| Market basket / DAWN | yes | one implicit | no | yes | yes |
| Table row, un-annotated | no | no | column names only | yes | yes |
| Table row + SemTab annotations | yes | yes | yes | yes | yes |
| Relational DB row | yes (keys) | yes (table) | yes (columns) | yes | yes |
| OCEL 2.0 event | yes | yes (activity) | yes (qualifiers) | yes | yes (timestamp) |
| kNN feature hypergraph | n/a | no | no | **no** | no |
| LLM-extracted knowledge fragment | weak | no (open text) | no | yes | yes |

Two conclusions fall out. First, **the structured sources beat the text sources on four of five criteria** —
a relational database or an OCEL log gives you identity, types, roles and provenance for free, and only
lacks the open-ended coverage that text has. Second, the LLM-extracted hyperedge that the current KHG-RAG
literature produces scores *worse* than a database row on identity, relation type and roles. That is the
honest summary of where the field is: the expressive representation is being populated by the weakest
available source.

## 8. Open problems

- **No standard interchange between the two worlds.** Interaction hypergraph datasets ship as incidence
  lists; KHGs need relation types and roles. A converter needs a convention for "one implicit relation, no
  roles", and there is none.
- **Role recovery from interaction data.** Email senders, thread askers, bill sponsors are recoverable from
  the raw sources, yet the standard datasets discard them. A role-annotated re-release of the Benson
  collection would be a genuinely useful artefact.
- **Multi-way joins as hyperedges are unexplored in ML.** Relational deep learning works over row-level
  graphs; the higher-order version is a natural and (as far as this research run found) unpublished step.
- `[unverified]` — no published pipeline was found that constructs a KHG directly from OCEL 2.0 logs,
  despite the structural fit.

## Sources

- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." IJCAI 2020 / arXiv 1906.00137. https://arxiv.org/abs/1906.00137
- Torres, L., Blevins, A. S., Bassett, D. S., Eliassi-Rad, T. "The why, how, and when of representations for complex systems." arXiv 2006.02870, 2020. https://arxiv.org/abs/2006.02870
- Battiston, F., Cencetti, G., Iacopini, I., Latora, V., et al. "Networks beyond pairwise interactions: structure and dynamics." Physics Reports, 2020 / arXiv 2006.01764. https://arxiv.org/abs/2006.01764
- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. "Simplicial closure and higher-order link prediction." PNAS 115(48), 2018 / arXiv 1802.06916. https://arxiv.org/abs/1802.06916
- Benson, A. R. "Data" (hypergraph datasets: coauth-DBLP, tags-*, threads-*, NDC-*, DAWN, congress-bills, email-*, contact-*), checked 2026-09-20. https://www.cs.cornell.edu/~arb/data/
- Chen, P., Sarkar, S., Lausen, L., Srinivasan, B., Zha, S., Huang, R., Karypis, G. "HYTREL: Hypergraph-enhanced Tabular Data Representation Learning." NeurIPS 2023 / arXiv 2307.08623. https://arxiv.org/abs/2307.08623
- Srinivas, K., Jiménez-Ruiz, E., Hassanzadeh, O., Chen, J., Efthymiou, V., Cutrona, V. (organisers). "SemTab 2020: Semantic Web Challenge on Tabular Data to Knowledge Graph Matching" (CEA/CTA/CPA task definitions), collocated with ISWC 2020, checked 2026-09-20. https://www.cs.ox.ac.uk/isg/challenges/sem-tab/2020/
- Beeri, C., Fagin, R., Maier, D., Yannakakis, M. "On the Desirability of Acyclic Database Schemes." Journal of the ACM 30(3), 1983. https://dl.acm.org/doi/10.1145/2402.322389
- Fagin, R. "Degrees of acyclicity for hypergraphs and relational database schemes." Journal of the ACM 30(3), 1983. https://dl.acm.org/doi/10.1145/2402.322390
- Fey, M., Hu, W., Huang, K., Lenssen, J. E., et al. "Relational Deep Learning: Graph Representation Learning on Relational Databases." arXiv 2312.04615, 2023. https://arxiv.org/abs/2312.04615
- Berti, A., Koren, I., Adams, J. N., Park, G., et al. "OCEL (Object-Centric Event Log) 2.0 Specification." arXiv 2403.01975, 2024. https://arxiv.org/abs/2403.01975
- Gao, Y., Zhang, Z., Lin, H., Zhao, X., Du, S., Zou, C. "Hypergraph Learning: Methods and Practices." IEEE Transactions on Pattern Analysis and Machine Intelligence, 2022. https://doi.org/10.1109/TPAMI.2020.3039374
- iMoonLab. DHG (DeepHypergraph) API documentation, `Hypergraph` constructors, version 0.9.7, checked 2026-09-20. https://deephypergraph.readthedocs.io/en/latest/api/dhg.html
- Luo, H., E, H., Chen, G., Zheng, Y., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." arXiv 2503.21322, 2025. https://arxiv.org/abs/2503.21322
