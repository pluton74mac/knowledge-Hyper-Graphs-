# Knowledge Hypergraphs — exploration knowledge base

A growing, cited knowledge base on **knowledge hypergraphs (KHG)**: what they are, how they are
built, stored, queried, learned on, visualised, and applied; where the idea came from; and where the
research frontier is now. It exists to support exploration vectors and prototypes that will be
developed in `projects/`.

> Working definition. A knowledge hypergraph is a knowledge base whose atomic facts are
> **hyperedges**: relations that connect *any number* of entities at once (an n-ary fact such as
> `treats(drug, disease, dosage, population)`), possibly typed, directed, role-labelled, qualified,
> weighted, timestamped, and nested. It generalises the knowledge graph, whose facts are binary
> triples. The literature uses the term for several related but distinct formalisms; see
> `kb/02-knowledge-representation/what-is-a-knowledge-hypergraph.md`.

## Start here

| If you want to... | Go to |
|---|---|
| Get oriented in 20 minutes | [`kb/00-index/reading-paths.md`](kb/00-index/reading-paths.md) |
| See every note in one table | [`kb/00-index/map-of-content.md`](kb/00-index/map-of-content.md) |
| Look up a term | [`kb/00-index/glossary.md`](kb/00-index/glossary.md) |
| See what is unresolved | [`kb/00-index/open-questions.md`](kb/00-index/open-questions.md) |
| Understand the history and the frontier | [`kb/08-history-and-frontier/`](kb/08-history-and-frontier/) |
| Pick a file format or database | [`kb/04-storage-and-formats/format-recommendations.md`](kb/04-storage-and-formats/format-recommendations.md) |
| Start a prototype | [`projects/README.md`](projects/README.md) |

## Layout

```
kb/            The knowledge base, in ten numbered sections (00 is the index)
sources/       Bibliography, per section and merged
projects/      Exploration vectors and prototypes growing out of the KB
schemas/       Sample data-model files (HIF JSON, RDF-star Turtle, ...)
datasets/      Manifest of datasets and benchmarks (pointers only, no bulk data)
notes/         Dated research logs
tools/         Scripts: validate the KB, rebuild the index, merge the bibliography
CONVENTIONS.md How to write and organise notes so the base keeps growing cleanly
```

## Sections

| # | Section | Question it answers |
|---|---|---|
| 01 | [foundations](kb/01-foundations/) | What is a hypergraph, mathematically, and what structures sit next to it? |
| 02 | [knowledge-representation](kb/02-knowledge-representation/) | What is a *knowledge* hypergraph, and how does it relate to knowledge graphs and n-ary facts? |
| 03 | [construction](kb/03-construction/) | How are KHGs built, from text, tables, existing graphs, and by LLM pipelines? |
| 04 | [storage-and-formats](kb/04-storage-and-formats/) | How are they stored: file types, serialisations, databases, tensors? |
| 05 | [query-embeddings-reasoning](kb/05-query-embeddings-reasoning/) | How are they queried, embedded, learned on, and reasoned over? |
| 06 | [visualization](kb/06-visualization/) | How are they drawn, and with which tools? |
| 07 | [applications](kb/07-applications/) | Where are they used, and with what results? |
| 08 | [history-and-frontier](kb/08-history-and-frontier/) | Where did the idea come from and where is it going? |
| 09 | [ecosystem](kb/09-ecosystem/) | Which libraries, datasets, books, standards, and communities exist? |
| 10 | [comparative-and-critique](kb/10-comparative-and-critique/) | How does a KHG compare with neighbouring formalisms, and when should you not use one? |

## State of the base

Two research runs so far. Run 01 (2026-09-19/20) built the base: 102 content notes across ten
sections. Run 02 (2026-09-21) was a second pass seeded by an external one-shot frontier survey: six
new notes (HYPER taken apart, geometry and algebraic interfaces, skill-driven extraction, hierarchical
and planned retrieval, temporal hyperedges and editable agent memory, and a synthesis of the frontier
as one composed stack), corrections to fourteen existing notes, and a new open-question theme on
whether the layers compose. Current state: 108 content notes, about 29,600 lines, 988 distinct
sources, a 300-entry glossary, 82 open questions in eight themes, and eight candidate projects. Every
note carries inline citations and a sources section; claims that could not be checked against a
primary source are marked `[unverified]`. Run logs are in `notes/research-log/`.

## Maintaining the base

```
python tools/validate_kb.py        # front matter, links, sources sections
python tools/build_index.py        # regenerate kb/00-index/map-of-content.md
python tools/merge_sources.py      # regenerate sources/bibliography.md
```

Every research run appends a log in `notes/research-log/`. New questions go to
`kb/00-index/open-questions.md`. New projects start from `projects/_template/`.
