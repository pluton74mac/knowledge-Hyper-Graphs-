# Projects and exploration vectors

Prototypes and investigations that grow out of the knowledge base. Each project lives in its own
folder, created from `_template/`, and links back to the `kb/` notes it depends on.

| Project | Status | One-line goal |
|---|---|---|
| _(none yet)_ | | |

## Candidate vectors (to be confirmed with the repository owner)

These are directions the first research run suggested. None is started. Promote one by copying
`_template/` to a new folder and adding a row above.

1. **Format bake-off** — represent the same small KHG in HIF, RDF-star, TypeQL, and a property-graph
   emulation; measure round-trip fidelity and query ergonomics. Depends on `kb/04-storage-and-formats/`.
2. **Text-to-KHG pipeline** — reproduce an LLM-based n-ary extraction pipeline on a small corpus and
   evaluate hyperedge precision. Depends on `kb/03-construction/`.
3. **Hypergraph RAG replication** — replicate a hypergraph-RAG result against a GraphRAG and naive-RAG
   baseline on one domain. Depends on `kb/07-applications/`, `kb/10-comparative-and-critique/`.
4. **Visual encoding study** — render one KHG in bipartite, PAOH, and Euler-style encodings and
   compare readability. Depends on `kb/06-visualization/`.
5. **Link prediction baseline** — run one n-ary embedding model on JF17K or WD50K to get a feel for the
   benchmark protocol. Depends on `kb/05-query-embeddings-reasoning/`, `kb/09-ecosystem/`.
6. **KHG as agent memory** — prototype a hypergraph memory for a small agent and compare with a flat
   vector store. Depends on `kb/07-applications/ai-agents-memory-and-planning.md`.
