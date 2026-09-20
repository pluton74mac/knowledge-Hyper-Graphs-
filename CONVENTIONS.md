# Conventions for this knowledge base

This repository is a growing knowledge base (KB) on **knowledge hypergraphs (KHG)**.
It is meant to be read by humans and by agents, and to spawn prototypes and projects.
Follow these rules so the base stays navigable as it grows.

## Layout

```
kb/                        The knowledge base proper, numbered sections (see kb/00-index)
  00-index/                Maps of content, glossary, reading paths, open questions
  01-foundations/          Mathematics of hypergraphs and related structures
  02-knowledge-representation/  From knowledge graphs to knowledge hypergraphs; n-ary facts
  03-construction/         How KHGs are built (extraction, curation, schema, LLM pipelines)
  04-storage-and-formats/  Serialization formats, file types, databases, tensor storage
  05-query-embeddings-reasoning/  Query languages, embeddings, hypergraph neural nets, reasoning
  06-visualization/        Visual encodings, drawing algorithms, tools
  07-applications/         Domain applications and case studies
  08-history-and-frontier/ Development history and current research frontier
  09-ecosystem/            Libraries, datasets, benchmarks, groups, venues, communities
  10-comparative-and-critique/  KHG vs. neighbouring formalisms; limitations; open debates
sources/                   Bibliography. `by-topic/` is written per section, merged into bibliography.md
projects/                  Exploration vectors and prototypes that grow out of the KB
notes/research-log/        Dated logs of research runs (what was searched, what was found, gaps)
schemas/                   Data-model drafts and sample files (HIF, JSON-LD, RDF-star, ...)
datasets/                  Manifests and pointers to datasets (no bulk data committed)
tools/                     Scripts and utilities for the KB (conversion, validation, indexing)
```

## Files

- One topic per Markdown file. Kebab-case names: `hyper-relational-knowledge-graphs.md`.
- Every `kb/` file starts with YAML front matter:

```yaml
---
title: Human readable title
type: concept | survey | tool | paper-note | dataset | timeline | comparison | question | howto
status: draft | reviewed | stable
tags: [hypergraph, n-ary, ...]
created: 2026-09-19
updated: 2026-09-19
---
```

- Each `kb/` section has a `README.md` that lists and summarises the files in that section.
- Prefer many focused notes over one huge file. Link between notes with relative Markdown links.

## Evidence and citations

- Cite as you write: `[Author, Year](URL)` inline, and a `## Sources` section at the end of each file
  listing every source with title, authors, venue or publisher, year, and URL.
- Prefer primary sources: papers (arXiv or DOI), specifications, official documentation, repositories.
- Give dates. A tool note states the version or the date checked. A history note states years.
- Mark anything you could not verify as `[unverified]`. Never invent a citation, a number, or a quote.
- Distinguish clearly between: established results, active research, and opinion.

## Growth

- New exploration vectors go in `projects/<slug>/` starting from `projects/_template/`.
- Questions that arise during research go into `kb/00-index/open-questions.md`, tagged with the section
  that raised them.
- Each research run appends a dated log to `notes/research-log/`.
- When a note changes materially, bump `updated:` and, if it was `stable`, drop it back to `reviewed`.
