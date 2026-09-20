---
title: Question answering over n-ary facts and qualifiers
type: survey
status: draft
tags: [hypergraph, n-ary, question-answering, KGQA, qualifiers, temporal, complex-query-answering]
created: 2026-09-20
updated: 2026-09-20
---

# Question answering over n-ary facts and qualifiers

Question answering is the application where the cost of decomposing an n-ary fact into triples is most
directly measurable: if the question asks *which* of several co-participants satisfies a condition, a
representation that loses the grouping cannot answer it without guessing.

Three distinct threads live here and are often confused:

1. **Natural-language KGQA over an n-ary KG** — the question is text, the KB has n-ary facts.
2. **Complex (logical) query answering** — the question is a formal conjunctive/logical query, answered
   approximately by embeddings; qualifiers narrow the answer set.
3. **Temporal and event QA** — a special case where the extra arguments are times, places or roles, and
   where modern KGs already store them as qualifiers.

## 1. Natural-language KGQA over n-ary facts

**WikiPeopleQA** is the first KGQA dataset whose *background KB* is itself n-ary. It is built over the
WikiPeople KG (derived from Wikidata, person-centric), with 33 question templates covering up to three
combined facts ([Zhang et al., 2022](https://arxiv.org/abs/2108.08297), Findings of ACL 2022). The
canonical example — *"Marie Curie received the Nobel Prize in Chemistry in 1911"* — is a single fact
with a main predicate plus qualifiers, not three triples.

The result that matters for this KB: baselines forced to split the n-ary facts into triples via dummy
entities reached **10.9 %–24.9 % accuracy**, whereas the fact-tree reasoning method that keeps facts
intact reached **54.4 %** ([Zhang et al., 2022](https://arxiv.org/abs/2108.08297)). This is the
cleanest published demonstration in this KB that reification-by-decomposition costs answers, not just
elegance. The dataset size is 4,491 QA pairs over a KG with 557 n-ary relation types.

Caveats. WikiPeopleQA is template-generated, so the questions are syntactically narrow; the ~30-point
gap is against baselines that were not designed for n-ary input; and the comparison conflates
"keeps facts intact" with "uses a different reasoning architecture".

## 2. Complex query answering with qualifiers

Here the question is a formal query graph, and the hyper-relational structure appears inside the query
as well as inside the KB.

- **StarQE** ([Alivanistos, Berrendorf, Cochez, Galkin, 2022](https://arxiv.org/abs/2106.08166),
  ICLR 2022; [code](https://github.com/DimitrisAlivas/StarQE)) was the first to pose multi-hop logical
  query answering over *hyper-relational* KGs. It uses StarE as the encoder and message passing over
  qualified statements, and introduces **WD50K-QE**, a query dataset generated from a hyper-relational
  Wikidata subset with a range of logical query patterns. The paper's summary claim is that
  "qualifiers improve query answering on a diverse set of query patterns"; specific MRR deltas are in
  the full paper rather than the abstract. [unverified: exact MRR/HITS figures not read in this run]
- **NQE** ([Luo et al., 2023](https://arxiv.org/abs/2211.13469), AAAI 2023) generalises this to n-ary
  query embedding, handling projection, conjunction, disjunction and negation over hyper-relational
  facts using fuzzy-logic operators.
- **LKHGT** ([Tsang, Wang, Song, 2025](https://arxiv.org/abs/2504.16537)) moves from hyper-relational
  (one main triple + qualifiers) to *knowledge hypergraph* queries proper, with a Projection Encoder,
  a Logical Encoder and a Type-Aware Bias. It contributes two CQA datasets, **JF17k-HCQA** and
  **M-FB15k-HCQA**, with projection, negation, conjunction and disjunction query types, and reports
  state-of-the-art results plus generalisation to out-of-distribution query types.

Note the lineage: WD50K → WD50K-QE → JF17k/M-FB15k variants. All of them are carved out of Freebase and
Wikidata, whose data models are described in
[wikidata-and-freebase-data-models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).
That means the "n-ary QA" literature inherits Freebase's CVT conventions and Wikidata's qualifier
conventions, including their idiosyncrasies.

## 3. Temporal and event QA

Most temporal information in modern KGs is stored *as qualifiers on statements*, not as separate
entities — a Wikidata position-held statement carries `start time` and `end time` qualifiers. So
temporal QA is n-ary QA whether or not it says so.

- **TempQuestions** is the early benchmark, about 1,271 questions; it is superseded by
  **TimeQuestions** with 16,181 questions ([Jia et al., 2021](https://arxiv.org/abs/2109.08935),
  CIKM 2021; project page [EXAQT](https://exaqt.mpi-inf.mpg.de/)).
- **EXAQT** is described by its authors as the first end-to-end system for complex temporal questions
  with multiple entities, predicates and temporal conditions. It works in two stages: compute a
  question-relevant compact subgraph (Group Steiner Trees plus a fine-tuned language model, tuned for
  recall), then rank with a relational graph convolutional network augmented with time-aware entity
  embeddings and attention over temporal relations ([Jia et al., 2021](https://arxiv.org/abs/2109.08935);
  [code](https://github.com/zhenjia2017/EXAQT)).
- **CronQuestions** is a further temporal QA dataset over temporal KGs; downstream models such as
  TwiRGCN ([Sharma et al., 2022](https://arxiv.org/abs/2210.06281)) and time-aware fusion networks
  ([Xiao et al., 2023](https://arxiv.org/abs/2302.12529)) target it.

The terminology tangle here is unpicked in
[hyper-relational-vs-n-ary-vs-hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md).
The connection to hypergraphs is usually implicit: these systems keep the qualifier attached to the
statement rather than reifying it, which is exactly the hyper-relational move, but they rarely use the
word "hypergraph". This is a naming gap rather than a technical one — see
[n-ary-relations-and-reification](../02-knowledge-representation/n-ary-relations-and-reification.md).

## 4. Document-level n-ary QA and extraction-then-QA

A separate route to the same place: extract n-ary facts from text, then answer over them.
**SciREX** ([Jain, van Zuylen, Hajishirzi, Beltagy, 2020](https://arxiv.org/abs/2005.00512), ACL 2020)
annotates document-level n-ary relations in scientific papers over entity types *Method, Metric, Task,
Material* plus *Score* ([repo](https://github.com/allenai/SciREX)). The README flags a caveat that
matters for anyone reusing it: about 50 % of annotated relations contain at least one entity with no
textual mention, because they occur in tables that were discarded.

**HyperDocRED** ([Huang et al., 2026](https://arxiv.org/abs/2602.19543)) is the 2026 equivalent for
knowledge hypergraphs, restructuring Re-DocRED into n-ary relations with 50 seed training documents and
100 test documents; on it, the extraction step of a leading hypergraph-RAG system reached only 0.3828
precision / 0.1072 recall, which bounds how good downstream QA over such a hypergraph can be.

## 5. Where this connects

- Retrieval-based QA over hypergraph indexes is in [retrieval-augmented-generation](retrieval-augmented-generation.md).
- The embedding and reasoning machinery sits in
  [knowledge-hypergraph-embedding-models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md)
  and [hypergraph-neural-networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md);
  query languages in [query-languages-for-hypergraphs](../05-query-embeddings-reasoning/query-languages-for-hypergraphs.md);
  evaluation protocols in [benchmarks-and-evaluation-protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).
- Benchmarks derived from Wikidata and Freebase are the shared substrate:
  [wikidata-and-freebase-data-models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

## Sources

- Zhang, Y., Li, P., Liang, H., Jatowt, A., Yang, Z. *Fact-Tree Reasoning for N-ary Question Answering over Knowledge Graphs.* Findings of ACL 2022; arXiv:2108.08297. https://arxiv.org/abs/2108.08297
- Alivanistos, D., Berrendorf, M., Cochez, M., Galkin, M. *Query Embedding on Hyper-relational Knowledge Graphs.* ICLR 2022; arXiv:2106.08166. https://arxiv.org/abs/2106.08166
- Alivanistos, D. *StarQE* (code), GitHub, checked 2026-09-20. https://github.com/DimitrisAlivas/StarQE
- Luo, H., E, H., Yang, Y., Zhou, G., Guo, Y., Yao, T., Tang, Z., Lin, X., Wan, K. *NQE: N-ary Query Embedding for Complex Query Answering over Hyper-Relational Knowledge Graphs.* AAAI 2023; arXiv:2211.13469 (v1 24 Nov 2022). https://arxiv.org/abs/2211.13469
- Tsang, H. T., Wang, Z., Song, Y. *Transformers for Complex Query Answering over Knowledge Hypergraphs.* arXiv:2504.16537, 23 Apr 2025. https://arxiv.org/abs/2504.16537
- Jia, Z., Pramanik, S., Saha Roy, R., Weikum, G. *Complex Temporal Question Answering on Knowledge Graphs.* CIKM 2021; arXiv:2109.08935. https://arxiv.org/abs/2109.08935
- EXAQT project page, Max Planck Institute for Informatics, checked 2026-09-20. https://exaqt.mpi-inf.mpg.de/
- EXAQT code repository, GitHub, checked 2026-09-20. https://github.com/zhenjia2017/EXAQT
- Sharma, A., Saxena, A., Gupta, C., Kazemi, S. M., Talukdar, P., Chakrabarti, S. *TwiRGCN: Temporally Weighted Graph Convolution for Question Answering over Temporal Knowledge Graphs.* arXiv:2210.06281. https://arxiv.org/abs/2210.06281
- Xiao, Y. et al. *Time-aware Multiway Adaptive Fusion Network for Temporal Knowledge Graph Question Answering.* arXiv:2302.12529. https://arxiv.org/abs/2302.12529
- Jain, S., van Zuylen, M., Hajishirzi, H., Beltagy, I. *SciREX: A Challenge Dataset for Document-Level Information Extraction.* ACL 2020; arXiv:2005.00512. https://arxiv.org/abs/2005.00512
- AllenAI. *SciREX* (code and data), GitHub, checked 2026-09-20. https://github.com/allenai/SciREX
- Huang, R., Feng, Y., Xue, R., Ying, S., Yong, J.-H., Shi, C., Du, S., Gao, Y. *Hyper-KGGen: A Skill-Driven Knowledge Extractor for High-Quality Knowledge Hypergraph Generation.* arXiv:2602.19543, 2026. https://arxiv.org/abs/2602.19543
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020; arXiv:2009.10847. https://arxiv.org/abs/2009.10847
