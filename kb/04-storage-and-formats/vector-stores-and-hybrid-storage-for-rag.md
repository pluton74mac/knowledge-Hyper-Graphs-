---
title: Vector stores and hybrid storage in hypergraph-RAG systems
type: survey
status: draft
tags: [rag, vector-database, nanovectordb, milvus, faiss, lightrag, hypergraphrag, hyper-rag, hybrid-storage]
created: 2026-09-20
updated: 2026-09-20
---

# Vector stores and hybrid storage for hypergraph-RAG

No hypergraph-RAG system stores its knowledge in one place. They all use the same three-or-four-way
split: a **KV store** for documents and chunks, a **vector store** for embeddings, a **graph or
hypergraph store** for structure, and (in the more mature ones) a **status store** for ingestion
bookkeeping. This note documents the actual on-disk layouts, read from the source, and what the
split costs.

All source readings checked 2026-09-20.

## 1. The shared architecture

The pattern originates in LightRAG and was inherited by both hypergraph systems that fork from it.
LightRAG names the four roles explicitly:

- **KV_STORAGE** — "llm response cache, text chunks, document information"
- **VECTOR_STORAGE** — "entities vectors, relation vectors, chunks vectors"
- **GRAPH_STORAGE** — "entity relation graph"
- **DOC_STATUS_STORAGE** — "document indexing status"

([LightRAG API server documentation](https://github.com/HKUDS/LightRAG/blob/main/docs/LightRAG-API-Server.md)).

The defaults are file-backed in-memory structures, and the documentation is unusually candid about
what that means: "**All four default storages are in-memory databases** (`JsonKVStorage`,
`NanoVectorDBStorage`, `NetworkXStorage`, `JsonDocStatusStorage`): the whole dataset resides in the
server process's memory and local files under `WORKING_DIR` serve only as persistence, so capacity
is bounded by available RAM. The defaults are therefore intended **only for small-scale testing,
evaluation, and debugging, and are not suitable for production**."

Pluggable implementations, as of the checked revision:

| Role | Implementations (default first) |
|---|---|
| KV | `JsonKVStorage`, `RedisKVStorage`, `PGKVStorage`, `MongoKVStorage`, `OpenSearchKVStorage` |
| Vector | `NanoVectorDBStorage`, `MilvusVectorDBStorage`, `PGVectorStorage`, `FaissVectorDBStorage`, `QdrantVectorDBStorage`, `MongoVectorDBStorage`, `OpenSearchVectorDBStorage` |
| Graph | `NetworkXStorage`, `Neo4JStorage`, `PGTableGraphStorage`, `PGGraphStorage`, `MongoGraphStorage`, `MemgraphStorage`, `OpenSearchGraphStorage` |
| Doc status | `JsonDocStatusStorage`, `RedisDocStatusStorage`, `PGDocStatusStorage`, `MongoDocStatusStorage`, `OpenSearchDocStatusStorage` |

For production the documentation recommends PostgreSQL as a single backend for all four roles, with
MongoDB and OpenSearch as the other single-backend options.

## 2. HyperGraphRAG — files on disk

[HyperGraphRAG](https://github.com/LHRLAB/HyperGraphRAG) (NeurIPS 2025) keeps LightRAG's storage
classes and changes the namespaces. From `hypergraphrag/hypergraphrag.py`, a working directory
contains:

| File | Class | Contents |
|---|---|---|
| `kv_store_full_docs.json` | `JsonKVStorage` | source documents |
| `kv_store_text_chunks.json` | `JsonKVStorage` | chunks with token counts and parent doc IDs |
| `kv_store_llm_response_cache.json` | `JsonKVStorage` | extraction/query LLM cache |
| `graph_chunk_entity_relation.graphml` | `NetworkXStorage` | the "hypergraph": hyperedge nodes + entity nodes + binary incidences |
| `vdb_entities.json` | `NanoVectorDBStorage` | entity embeddings, IDs `ent-<md5>` |
| `vdb_hyperedges.json` | `NanoVectorDBStorage` | **hyperedge embeddings**, IDs `rel-<md5>` |
| `vdb_chunks.json` | `NanoVectorDBStorage` | chunk embeddings |

Two details matter.

**The hyperedge is embedded as text.** `hyperedges_vdb` is upserted with
`{"content": dp["hyperedge_name"], "hyperedge_name": ...}` — and `hyperedge_name` is
`"<hyperedge>" + knowledge_fragment`, i.e. the natural-language sentence expressing the fact
(`hypergraphrag/operate.py`). So the vector index is over fact *sentences*, and retrieval finds
facts by semantic similarity to the whole fact, not to its participants. That is the actual
contribution of the system's storage design, and it is independent of whether the graph store is a
real hypergraph (it is not — see
[property-graph-emulation-patterns.md](property-graph-emulation-patterns.md)).

**The vector store is a JSON file.** `NanoVectorDBStorage` wraps
[NanoVectorDB](https://pypi.org/project/nano-vectordb/) (0.0.4.3, uploaded 2024-11-11), which keeps
all vectors in memory in a NumPy array and persists them to one JSON file, doing brute-force cosine
search with a `cosine_better_than_threshold` cut-off (default 0.2). There is no ANN index. This is
fine for a paper-scale corpus and will not survive a real one.

Alternative backends are wired but commented or lazily imported in the same file: `Neo4JStorage`,
`OracleKVStorage`/`OracleGraphStorage`/`OracleVectorDBStorage`, `MilvusVectorDBStorge`,
`MongoKVStorage`, `ChromaVectorDBStorage`, `TiDBKVStorage`/`TiDBVectorDBStorage`, plus a
commented-out ArangoDB graph storage.

## 3. Hyper-RAG — the same split with a native hypergraph store

[Hyper-RAG](https://github.com/iMoonLab/Hyper-RAG) (*Nature Communications*, 27 April 2026) keeps
the JSON KV store and NanoVectorDB, and replaces the graph layer with
[Hypergraph-DB](https://github.com/iMoonLab/Hypergraph-DB):

| File | Class | Contents |
|---|---|---|
| `kv_store_full_docs.json`, `kv_store_text_chunks.json`, `kv_store_llm_response_cache.json` | `JsonKVStorage` | as above |
| `hypergraph_chunk_entity_relation.hgdb` | `HypergraphStorage` -> `HypergraphDB.save` | **native hyperedges keyed by member set** |
| `vdb_entities.json`, `vdb_relationships.json`, `vdb_chunks.json` | `NanoVectorDBStorage` | embeddings |

`hyperrag/storage.py` shows the hypergraph layer plainly: `load_hypergraph` constructs a
`HypergraphDB()` and calls `.load(file_name)`; `index_done_callback` calls `.save(file_name)`; and
the log line reports "`Loaded hypergraph from {file} with {num_v} vertices, {num_e} hyperedges`".
In `hyperrag/operate.py`, hyperedges are addressed by an `id_set` of member entity IDs
(`has_hyperedge(id_set)`, `upsert_hyperedge(id_set, {...})`) with properties `keywords`, `weight`,
`description`, `source_id`.

The `.hgdb` file is a Python pickle. That is a real operational constraint: it is not portable, not
inspectable, not diffable, and not safe to load from an untrusted source. Hypergraph-DB's
`save_as_hif` / `load_from_hif` gives an escape hatch that Hyper-RAG does not use — a one-line
change that would make its knowledge base inspectable. Recorded as a recommendation in
[format-recommendations.md](format-recommendations.md).

## 4. Comparison

| | LightRAG | HyperGraphRAG | Hyper-RAG |
|---|---|---|---|
| Structure store | NetworkX / Neo4j / PG / Mongo / Memgraph / OpenSearch | NetworkX only (in the checked revision) | Hypergraph-DB |
| On-disk structure file | `graph_chunk_entity_relation.graphml` | `graph_chunk_entity_relation.graphml` | `hypergraph_chunk_entity_relation.hgdb` (pickle) |
| Arity in storage | 2 | n, emulated as node + binary edges | **n, native** |
| Roles | no | no | no |
| Vector store default | NanoVectorDB | NanoVectorDB | NanoVectorDB |
| Vector backends available | Milvus, Faiss, Qdrant, pgvector, Mongo, OpenSearch | Milvus, Chroma, Oracle, TiDB (lazy imports) | NanoVectorDB |
| What is embedded | entities, relations, chunks | entities, **hyperedge sentences**, chunks | entities, relations, chunks |
| Production guidance in docs | yes, detailed | no | no |

## 5. Why the split exists, and what it costs

**Why.** The three stores answer different questions. The vector store answers "what is *about*
this?" over unstructured text; the graph/hypergraph store answers "what is *connected to* this?";
the KV store holds the payload you finally put in the prompt. No single engine is good at all
three, and the embedding dimension is fixed at index time while the graph keeps changing.

**What it costs.**

1. **No transactions across stores.** A crash between the graph upsert and the vector upsert leaves
   a hyperedge with no embedding, or an embedding pointing at nothing. None of the three systems
   has a cross-store commit; they use per-store `index_done_callback` flushes.
2. **Duplicated identity.** The hyperedge exists as a node ID in the graph file, as a vector ID
   (`rel-<md5>` of the same string) in the vector file, and as text in the KV store. The md5 is the
   only link. Changing the sentence changes the ID everywhere.
3. **Re-embedding is a rebuild.** LightRAG states it directly: "The Embedding model must be
   determined before document indexing, and the same model must be used in the query phase. ...
   If changed, you will need to re-embed all text chunks, entities, and relationships. LightRAG
   does not currently provide a re-embedding tool." Some backends fix the vector dimension at table
   creation, so a model change means dropping vector tables.
4. **RAM ceiling.** The default stack is entirely in-process. The moment a KHG outgrows RAM, all
   four roles have to move at once.

## 6. What a well-designed hybrid layout looks like

Drawing on the above plus [relational-and-eav-storage.md](relational-and-eav-storage.md):

- **One system of record** — an incidence table (`fact`, `incidence`, `entity`) in PostgreSQL, with
  stable surrogate fact IDs that do not encode the text.
- **Derived indexes, all rebuildable**: a vector index (pgvector, Milvus or Faiss) keyed by the same
  fact ID; a graph or hypergraph projection for traversal; a Parquet export for analysis.
- **Embeddings versioned by model**: a `model_id` column so two embedding generations can coexist
  during a migration, which removes the "re-embedding is a rebuild" cliff.
- **HIF export as the inspection and interchange surface**, so the knowledge base can be read
  without running the system ([hif-hypergraph-interchange-format.md](hif-hypergraph-interchange-format.md)).
- **Provenance on the fact, not the chunk** — see
  [versioning-provenance-and-scale.md](versioning-provenance-and-scale.md).

None of the three systems surveyed does all of this. LightRAG's PostgreSQL path comes closest for
the binary case; nothing yet does it for hyperedges.

## Sources

- LightRAG repository and `docs/LightRAG-API-Server.md`, "Storage Types Supported"; README sections "Selecting Backend Storage" and the embedding-model note (checked 2026-09-20). https://github.com/HKUDS/LightRAG
- HyperGraphRAG repository: `hypergraphrag/hypergraphrag.py` (namespaces and storage classes), `hypergraphrag/storage.py` (`JsonKVStorage`, `NanoVectorDBStorage`, `NetworkXStorage`), `hypergraphrag/operate.py` (hyperedge naming and vector upsert), checked 2026-09-20. https://github.com/LHRLAB/HyperGraphRAG
- Luo, H. et al. (2025). *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation*. NeurIPS 2025. https://proceedings.neurips.cc/paper_files/paper/2025/hash/df55ee6e59f8ac4a625219e11fe9ddba-Abstract-Conference.html
- Hyper-RAG repository: `hyperrag/storage.py` (`HypergraphStorage`), `hyperrag/operate.py` (`upsert_hyperedge(id_set, ...)`), README (checked 2026-09-20). https://github.com/iMoonLab/Hyper-RAG
- Feng, Y. et al. (2026). *Hyper-RAG: combating LLM hallucinations using hypergraph-driven retrieval-augmented generation*. Nature Communications 17, 27 April 2026. https://doi.org/10.1038/s41467-026-71411-1
- Hypergraph-DB repository (persistence: `.hgdb`, `save_as_hif`, `load_from_hif`), checked 2026-09-20. https://github.com/iMoonLab/Hypergraph-DB
- NanoVectorDB on PyPI, version 0.0.4.3 uploaded 2024-11-11 (checked 2026-09-20). https://pypi.org/project/nano-vectordb/
- Milvus documentation. https://milvus.io/docs
- Faiss repository. https://github.com/facebookresearch/faiss
