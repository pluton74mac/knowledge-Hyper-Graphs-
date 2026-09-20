---
title: 09 — Ecosystem
type: index
status: draft
tags: [ecosystem, software, datasets, benchmarks, standards, community, index]
created: 2026-09-20
updated: 2026-09-20
---

# 09 — Ecosystem

The practical layer: **what already exists, whether it works, and whether you may use it.**
Sections [01](../01-foundations/) to [08](../08-history-and-frontier/) say what a knowledge
hypergraph *is*; this section says what you can actually install, download, cite and join today.

Every figure in this section carries a "checked 2026-09-20" date and a named source — a GitHub
API response, a PyPI or Maven record, a paper table, or a page fetch. Where a number could not
be confirmed it is marked `[unverified]` rather than filled in.

## The four findings this section exists to record

1. **Hypergraph tooling and knowledge-hypergraph tooling barely overlap.** The network-science
   libraries model a hyperedge as an unlabelled vertex set; the knowledge stack models a fact as
   a role-indexed tuple. **No surveyed library exposes incidence roles as a first-class concept**,
   even though HIF permits them and this repository's own sample file uses them.
2. **The benchmarks are damaged.** JF17K leaks 44.5% of its test statements into training and has
   no official validation split; WikiPeople is under 3% hyper-relational; the same dataset name is
   published with statistics that differ by a factor of two.
3. **Nothing is being standardised for hypergraphs except a file format.** W3C is standardising
   statement annotation (RDF 1.2), ISO is standardising property graphs (GQL, SQL/PGQ), and HIF —
   the only hypergraph-native standard — is still at schema version `v0.0` with four competing
   schema URLs in circulation.
4. **Adoption follows packaging, not representation.** Binary-edge GraphRAG has ~40k stars against
   ~450 for hypergraph RAG; but a one-command hypergraph *extraction* tool reached ~4k stars in
   eight months. The bottleneck is developer experience, not expressiveness.

## Notes in this section

| Note | What it covers |
|---|---|
| [software-libraries.md](software-libraries.md) | Seven tables covering ~40 tools — analysis, learning, storage/query, KG embedding, LLM pipelines, KG tooling, interchange and visualisation — with language, purpose, hyperedge model, formats read/written, licence, stars, latest release and last commit, all dated. Includes locally verified findings: only XGI preserves HIF `direction`; Hypergraphx re-indexes node ids; rdflib 7.6.0 cannot parse RDF-star. |
| [datasets-and-benchmarks.md](datasets-and-benchmarks.md) | The four benchmark traditions and their datasets, with statistics attributed paper-by-paper: JF17K, WikiPeople, WD50K(+33/66/100), FB-AUTO, M-FB15K, JF17K-3/4, WikiPeople-, WD20K, the temporal n-ary sets, the AllSet learning suite, XGI-DATA (51 datasets), hypergraphx-data (136 datasets), Benson's collection, SNAP, KONECT, and the hypergraph-RAG corpora. |
| [dataset-quality-and-leakage-issues.md](dataset-quality-and-leakage-issues.md) | The JF17K leak and its correct attribution (Galkin et al. 2020, not Rosso et al. 2020 — verified by full-text search); the missing JF17K validation split; WikiPeople's literals and 2.6% density; how WD50K filters leakage and what that costs; benchmark saturation; RAG-corpus provenance, archiving and circularity; licensing gaps; eight recommendations. |
| [books-surveys-and-courses.md](books-surveys-and-courses.md) | Berge 1973/1989, Voloshin 2002/2009, Bretto 2013, Battiston & Petri 2022, Dai & Gao 2023; the higher-order-network, hypergraph-learning and n-ary KG surveys 2020–2026; a five-step reading path; and an honest account of how little verified teaching material exists. |
| [awesome-lists-and-communities.md](awesome-lists-and-communities.md) | GitHub topic counts (`knowledge-graph` 8,906 vs `hypergraph` 194); three stale awesome lists and the missing n-ary one; per-library community channels; the HIF working group and its composition; venues, and Dagstuhl Seminar 26411. |
| [standards-bodies-and-specifications.md](standards-bodies-and-specifications.md) | W3C RDF 1.2 / SPARQL 1.2 document-by-document status as of 2026-09-20; ISO/IEC 39075:2024 GQL and ISO/IEC 9075-16:2023 SQL/PGQ; openCypher; HIF's structure, governance and four-URL versioning problem; the Graph Data Council (ex-LDBC) and PG-Schema; a table of what no standard covers. |
| [getting-started-toolchain.md](getting-started-toolchain.md) | A verified install (Python 3.11.15, `hypernetx` 2.4.3, `xgi` 0.10.2, `hypergraphx` 1.8.0, `rdflib` 7.6.0), a runnable `hello_hif.py` that loads [../../schemas/sample.hif.json](../../schemas/sample.hif.json) into all three libraries plus RDF, its actual output, and four lessons the output teaches. |
| [courses-tutorials-and-workshops.md](courses-tutorials-and-workshops.md) | Verified teaching material as of 2026-09-20: university courses (UNC DATA 890, KAIST AI607), the two KAIST-led conference tutorials that ran at seven venues 2022–2025, the ICML topological-deep-learning challenge series, Dagstuhl 21352/22372/25291/26411, and the XGI / HyperNetX / HIF notebook tutorials. Corrects the `[unverified]` list in books-surveys-and-courses.md §8. |

Dataset fetch instructions and licence records are in the manifest at
[../../datasets/README.md](../../datasets/README.md). The bibliography for this section is
[../../sources/by-topic/09-ecosystem.md](../../sources/by-topic/09-ecosystem.md).

## Reading order

1. **[getting-started-toolchain.md](getting-started-toolchain.md)** — twenty minutes, and you
   have hyperedges on screen. Start here.
2. **[software-libraries.md](software-libraries.md)** — pick your stack, and see what each choice
   costs you.
3. **[datasets-and-benchmarks.md](datasets-and-benchmarks.md)** then
   **[dataset-quality-and-leakage-issues.md](dataset-quality-and-leakage-issues.md)** — in that
   order, and do not skip the second.
4. **[standards-bodies-and-specifications.md](standards-bodies-and-specifications.md)** — before
   committing to a serialisation.
5. **[books-surveys-and-courses.md](books-surveys-and-courses.md)** and
   **[awesome-lists-and-communities.md](awesome-lists-and-communities.md)** — for going deeper
   and for keeping up.

## Where this section connects

- Formats and stores: [../04-storage-and-formats/hif-hypergraph-interchange-format.md](../04-storage-and-formats/hif-hypergraph-interchange-format.md), [../04-storage-and-formats/hypergraph-databases.md](../04-storage-and-formats/hypergraph-databases.md)
- Representation choices the tools force: [../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md)
- Models trained on these benchmarks: [../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md)
- Drawing: [../06-visualization/visual-encodings-catalogue.md](../06-visualization/visual-encodings-catalogue.md)
- The RAG pipelines that generated most of the 2025–2026 activity: [../07-applications/retrieval-augmented-generation.md](../07-applications/retrieval-augmented-generation.md)
- Standards timeline: [../08-history-and-frontier/standards-convergence.md](../08-history-and-frontier/standards-convergence.md)
- The "is a hypergraph worth it" argument these numbers feed: [../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md)

## Maintenance

Star counts, versions and specification statuses in this section decay fast. The cheapest
refresh is to re-run the checks named in each note's `## Sources` block: the GitHub repository
search API, the PyPI/crates.io/Maven JSON endpoints, the W3C publications page, and the
`hello_hif.py` script in [getting-started-toolchain.md](getting-started-toolchain.md). If the
script's output changes shape, an interchange assumption has broken and the tables need a full
re-check.
