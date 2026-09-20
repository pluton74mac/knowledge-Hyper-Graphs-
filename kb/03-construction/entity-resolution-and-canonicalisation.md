---
title: Entity resolution, canonicalisation and hyperedge deduplication
type: survey
status: draft
tags: [hypergraph, n-ary, entity-linking, entity-resolution, coreference, canonicalisation, deduplication, wikidata, umls]
created: 2026-09-19
updated: 2026-09-19
---

# Entity resolution, canonicalisation and hyperedge deduplication

Extraction produces *mentions*; a knowledge hypergraph needs *entities* and *canonical hyperedges*. This
stage decides when two mentions are the same thing, when two relation or role phrases mean the same, and
when two extracted n-ary facts are the same fact. It is the stage most often skipped by current LLM-based
KHG pipelines.

## 1. Three levels of identity

| Level | Question | Classical tools | KHG-specific twist |
|---|---|---|---|
| Mention → entity | Do "Obama", "Barack Obama", "the president" corefer, and which KB item is it? | coreference resolution, entity linking | one hyperedge often mixes linked and unlinkable participants (values, dates) |
| Phrase → relation/role | Are "educated at" and "studied at" the same relation? Is "end time" the same role as "until"? | Open-KB canonicalisation, schema alignment | roles must be canonical *within* a relation, not just globally |
| Fact → fact | Are two extracted n-ary facts the same fact? | triple dedup | facts may differ in arity (one lacks a date) or in participant order |

## 2. Mention-level: coreference and entity linking

**Coreference.** Document-level extraction pipelines resolve coreference before relation extraction: DocRED's
annotation "with coreference resolution" and HyperRED's alignment pipeline (entities extracted and linked,
"coreference resolution", then matching head, tail and value mentions) both do so
([Yao et al., 2019](https://arxiv.org/abs/1906.06127); [Chia et al., 2022](https://arxiv.org/abs/2211.10018)).
End-to-end neural coreference — "the first end-to-end coreference resolution model" considering all spans as
candidate mentions ([Lee et al., 2017](https://arxiv.org/abs/1707.07045)) — is the standard architecture.

**Entity linking to a reference KB.**

- *Wikidata/Wikipedia.* DocRED associates each mention with "a Wikidata item candidate set"; BLINK links
  zero-shot with "a bi-encoder that independently embeds the mention context and the entity descriptions" and
  "a cross-encoder, that concatenates the mention and entity text", reaching "5.9 million candidates in 2
  milliseconds" and state of the art on zero-shot benchmarks ([Wu et al., 2020](https://arxiv.org/abs/1911.03814)).
  Because "Each entity is defined only by a short textual description", the same recipe applies to any
  in-house entity catalogue.
- *Biomedical (UMLS).* The UMLS "brings together many health and biomedical vocabularies and standards";
  its Metathesaurus holds "Terms and codes from many vocabularies, including CPT, ICD-10-CM, LOINC, MeSH,
  RxNorm, and SNOMED CT" ([NLM, UMLS](https://www.nlm.nih.gov/research/umls/index.html)). scispaCy
  provides "robust, practical, publicly available models" for biomedical text including entity linking
  ([Neumann et al., 2019](https://arxiv.org/abs/1902.07669)); SPIRES grounds extracted elements to
  ontology identifiers as part of extraction ([Caufield et al., 2024](https://arxiv.org/abs/2304.02711));
  the 2026 clinical pipeline maps attributes to "SNOMED CT, LOINC, RxNorm, ICD, GO"
  ([Das et al., 2026](https://arxiv.org/html/2601.01844v1)).

**What the hypergraph RAG systems do instead.** HyperGraphRAG identifies entities by
`clean_str(record_attributes[1].upper())` and merges on exact string equality; the code shows "no similarity
thresholds or semantic deduplication" ([HyperGraphRAG `operate.py`](https://github.com/LHRLAB/HyperGraphRAG),
checked 2026-09-19). Hyper-RAG, GraphRAG and LightRAG behave the same way (LightRAG's dedup "identifies and
merges identical entities", [Guo et al., 2024](https://arxiv.org/abs/2410.05779)). Upper-casing merges case
variants only; "U.S." and "United States" stay separate, and two people called "John Smith" merge.

**Embedding-threshold matching.** iText2KG keeps a global entity set and, for each new document's local
entities, "searches for a similar entity in ℰ using a cosine similarity measure with a predefined threshold";
from 1,500 labelled entity pairs (mean cosine 0.6 ± 0.12) and 500 relation pairs (0.56 ± 0.1) they chose 0.7
"to ensure high precision" ([Lairgi et al., 2024](https://arxiv.org/abs/2409.03284)). This is a cheap middle
ground between exact match and full entity linking, and the paper's *false discovery rate* — "the proportion
of unresolved (false positive) entities or relations among the total extracted" — is a usable metric for it.

**Big-data entity resolution.** When the sources are records rather than text, the database community's
end-to-end ER pipelines (indexing/blocking, matching, clustering) apply; see the survey by
[Christophides et al., 2020](https://arxiv.org/abs/1905.06397), which frames ER as identifying "different
descriptions that refer to the same real-world entity" under "loose structuredness, extreme diversity, high
speed and large scale".

## 3. Phrase-level: canonicalising relations and roles

Open IE output is uncanonical by construction: "the noun phrases (NPs) and relation phrases in such Open KBs
are not canonicalized, leading to the storage of redundant and ambiguous facts"
([Vashishth et al., 2018](https://arxiv.org/abs/1902.00172)). CESI learns embeddings of noun phrases and
relation phrases jointly with side information (entity linking, morphological normalisation, paraphrase
databases) and clusters them; each cluster is one entity or relation.

The LLM-era equivalent is Extract–Define–Canonicalize ([Zhang & Soh, 2024](https://arxiv.org/abs/2404.03868)):
after open extraction, "we prompt the LLMs to provide a natural language definition for each component of the
schema induced by the open KG" (e.g. `bornOn` → "The subject entity was born on the date specified by the
object entity"), then canonicalise either against a target schema ("searching for potential consolidation
candidates through vector similarity and LLM verification") or in *self-canonicalisation* mode where
"semantically similar components are consolidated into canonical forms, with non-transformable elements added
to expand the schema". The definition step is what makes role names comparable: two roles with the same
definition are the same role even if the surface phrases differ.

**Roles need relation-local canonicalisation.** In the role-based schema a fact is `{(k_i, v_i)}`; the same
key ("location") may be a different role in different relations. Wikidata handles this socially — qualifier
properties are global (P580 *start time*, P582 *end time*, P585 *point in time*, P1001 *applies to
jurisdiction*), and property constraints state which qualifiers each property allows or requires ("Statements
for this property should not have any qualifiers other than the listed ones"; "must have all of the listed
qualifiers") ([Wikidata property constraints portal](https://www.wikidata.org/wiki/Help:Property_constraints_portal)).
A KHG built from text can borrow this: map extracted role phrases to a small set of global role properties and
maintain per-relation allowed-role lists as constraints.

## 4. Fact-level: deduplicating and merging hyperedges

Binary systems merge identical `(s, r, o)`; GraphRAG makes "the number of duplicates for a given relationship"
the edge weight ([Edge et al., 2024](https://arxiv.org/abs/2404.16130)). For hyperedges the problem is
harder and the literature is thin:

- **Same fact, different arity.** "Louis XIV held the position King of France" and "Louis XIV held the position
  King of France from 1643 to 1715" are the same statement with different qualifier sets. A merge rule that
  subsumes a hyperedge whose participant set is a subset of another's *under the same relation* is natural
  but is not implemented in any system inspected here.
- **Same participants, different description.** HyperGraphRAG's hyperedge id is the fragment text, so two
  paraphrases of one fact yield two hyperedges; Hyper-RAG keys high-order hyperedges on the vertex tuple and
  sums weights, so paraphrases merge but different facts over the same entity set also merge.
- **Order and roles.** In the plain hypergraph schema participant order is the only role information;
  Text2NKG's *hetero-ordered merging* handles this at extraction time by combining the six orderings of a
  span triple ([Luo et al., 2024](https://arxiv.org/abs/2310.05185)).
- **Conflicts.** Multi-agent enrichment adds a conflict-resolution agent; KARMA reports "reducing conflict
  edges by 18.6% through multi-layer assessments" ([Lu et al., 2025](https://arxiv.org/abs/2502.06472)).
  Wikidata expresses unresolved conflicts with ranks (preferred/normal/deprecated) rather than by deleting.

**Description merging** is the one fact-level operation all LLM pipelines perform: descriptions of the same
entity or edge are concatenated with a separator and, past a token budget (500 tokens in Hyper-RAG's
`entity_summary_to_max_tokens`), summarised by the LLM with an instruction to resolve contradictions
([Hyper-RAG `operate.py`](https://github.com/iMoonLab/Hyper-RAG); [HyperGraphRAG `prompt.py`](https://github.com/LHRLAB/HyperGraphRAG)).
This improves retrieval text but does not change identity.

## 5. Recommended minimal stack (opinion)

1. Coreference within each document before extraction.
2. Entity linking against a reference KB where one exists (Wikidata, UMLS); otherwise embedding-threshold
   matching with a validated threshold and a tracked false-discovery rate.
3. Define-then-canonicalise for relation and role phrases; keep definitions as metadata.
4. Hyperedge merge keyed on (canonical relation, canonical participant-role set), with subset subsumption
   flagged for review rather than applied blindly.
5. Never destroy provenance on merge — concatenate `source_id`s, as the RAG systems already do.

## Sources

- Yao, Y., et al. "DocRED: A Large-Scale Document-Level Relation Extraction Dataset." ACL 2019 / arXiv 1906.06127. https://arxiv.org/abs/1906.06127
- Chia, Y. K., et al. "A Dataset for Hyper-Relational Extraction and a Cube-Filling Approach." EMNLP 2022 / arXiv 2211.10018. https://arxiv.org/abs/2211.10018
- Lee, K., He, L., Lewis, M., Zettlemoyer, L. "End-to-end Neural Coreference Resolution." EMNLP 2017 / arXiv 1707.07045. https://arxiv.org/abs/1707.07045
- Wu, L., Petroni, F., Josifoski, M., Riedel, S., Zettlemoyer, L. "Scalable Zero-shot Entity Linking with Dense Entity Retrieval." EMNLP 2020 / arXiv 1911.03814. https://arxiv.org/abs/1911.03814
- U.S. National Library of Medicine. "Unified Medical Language System (UMLS)", checked 2026-09-19. https://www.nlm.nih.gov/research/umls/index.html
- Neumann, M., King, D., Beltagy, I., Ammar, W. "ScispaCy: Fast and Robust Models for Biomedical Natural Language Processing." BioNLP 2019 / arXiv 1902.07669. https://arxiv.org/abs/1902.07669
- Caufield, J. H., et al. "SPIRES: A method for populating knowledge bases using zero-shot learning." Bioinformatics 2024 / arXiv 2304.02711. https://arxiv.org/abs/2304.02711
- Das, U., et al. "Clinical Knowledge Graph Construction and Evaluation with Multi-LLMs via Retrieval-Augmented Generation." arXiv 2601.01844, 2026. https://arxiv.org/html/2601.01844v1
- LHRLAB. HyperGraphRAG repository (`operate.py`, `prompt.py`), checked 2026-09-19. https://github.com/LHRLAB/HyperGraphRAG
- iMoonLab. Hyper-RAG repository (`operate.py`), checked 2026-09-19. https://github.com/iMoonLab/Hyper-RAG
- Guo, Z., et al. "LightRAG: Simple and Fast Retrieval-Augmented Generation." arXiv 2410.05779, 2024. https://arxiv.org/abs/2410.05779
- Lairgi, Y., Moncla, L., Cazabet, R., Benabdeslem, K., Cléau, P. "iText2KG: Incremental Knowledge Graphs Construction Using Large Language Models." WISE 2024 / arXiv 2409.03284. https://arxiv.org/abs/2409.03284
- Christophides, V., Efthymiou, V., Palpanas, T., Papadakis, G., Stefanidis, K. "An Overview of End-to-End Entity Resolution for Big Data." ACM Computing Surveys 53(6), 2020 / arXiv 1905.06397. https://arxiv.org/abs/1905.06397
- Vashishth, S., Jain, P., Talukdar, P. "CESI: Canonicalizing Open Knowledge Bases using Embeddings and Side Information." WWW 2018 / arXiv 1902.00172. https://arxiv.org/abs/1902.00172
- Zhang, B., Soh, H. "Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction." EMNLP 2024 / arXiv 2404.03868. https://arxiv.org/abs/2404.03868
- Wikidata. "Help:Property constraints portal", checked 2026-09-19. https://www.wikidata.org/wiki/Help:Property_constraints_portal
- Edge, D., et al. "From Local to Global: A Graph RAG Approach to Query-Focused Summarization." arXiv 2404.16130, 2024. https://arxiv.org/abs/2404.16130
- Luo, H., et al. "Text2NKG: Fine-Grained N-ary Relation Extraction for N-ary relational Knowledge Graph Construction." NeurIPS 2024 / arXiv 2310.05185. https://arxiv.org/abs/2310.05185
- Lu, Y., Wu, W., Zhao, X., Peng, R., Wang, J. "KARMA: Leveraging Multi-Agent LLMs for Automated Knowledge Graph Enrichment." NeurIPS 2025 / arXiv 2502.06472. https://arxiv.org/abs/2502.06472
