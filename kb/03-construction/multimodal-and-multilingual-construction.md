---
title: Multimodal and multilingual construction of knowledge hypergraphs
type: survey
status: draft
tags: [construction, multimodal, multilingual, cross-lingual, images, video, tables, event-extraction, rag, gap-filling]
created: 2026-09-20
updated: 2026-09-20
---

# Multimodal and multilingual construction

Every extraction method in
[n-ary-relation-extraction-from-text.md](n-ary-relation-extraction-from-text.md) and
[llm-based-khg-construction.md](llm-based-khg-construction.md) assumes two things that the rest of
the world does not supply: the input is **text**, and the text is **English**. This note covers
what exists when either assumption is dropped, and — more usefully — states precisely what does
**not** exist.

Two summary judgements, argued below:

1. **Multimodal knowledge hypergraphs are an active 2026 research line with no fact-level
   benchmark.** Six or more systems now build hyperedges spanning images, tables and text; none of
   them is evaluated on whether the *hyperedges* are correct. They are evaluated on downstream QA.
2. **Cross-lingual n-ary knowledge extraction is, as of 2026-09-20, empty.** Multilingual **event**
   extraction resources exist and are good; multilingual **n-ary knowledge-graph** resources
   (HyperRED-style, hyper-relational, or knowledge-hypergraph) do not. Every benchmark in
   [../09-ecosystem/datasets-and-benchmarks.md](../09-ecosystem/datasets-and-benchmarks.md) is
   English-only at the text layer.

---

## 1. Why multimodality is a hyperedge problem and not a graph problem

The stated motivation is uniform across the 2026 papers: a fact drawn from a document page is not a
pair. Hyper-M2RAG puts it as the failure of "the binary connectivity paradigm of traditional simple
graphs, which fails to capture the intricate, high-order correlations among heterogeneous entities,
such as the N-ary relationships between a visual chart, its scattered textual descriptions, and
underlying numerical data" ([Chen, Xu, Han, Xue, Wu, Gao, Yan and Gao,
arXiv:2608.16628](https://arxiv.org/abs/2608.16628), 17 Aug 2026).

That is the same argument as §1 of
[../02-knowledge-representation/what-is-a-knowledge-hypergraph.md](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md),
transported to page layout. Whether it is *true* — whether a chart/caption/number triple-of-
modalities behaves like an n-ary fact or merely like a co-location group — is the open question of
§7 of [hypergraph-construction-from-data.md](hypergraph-construction-from-data.md), and none of the
papers below tests it.

---

## 2. Multimodal hypergraph RAG, 2026

| System | Date / id | Modalities | Hyperedge is… | Evaluated on |
|---|---|---|---|---|
| **Hyper-M2RAG** | 17 Aug 2026, [2608.16628](https://arxiv.org/abs/2608.16628) | page image, OCR text, figure and table patches | "unified semantic container" over a multimodal page | document QA |
| **VizRAG** | 22 Jul 2026, [2607.19830](https://arxiv.org/abs/2607.19830) | text + a *rendered picture of the hypergraph* | text hyperedge, plus its visual depiction fed to an MLLM | RAG QA |
| **EvoGraph-R1** | 14 Jul 2026, [2607.12764](https://arxiv.org/abs/2607.12764) | text + images | agent-editable multimodal hyperedge | agentic retrieval QA |
| **HyperGVL** | 17 Apr 2026, [2604.15648](https://arxiv.org/abs/2604.15648) | 12 textual and visual hypergraph encodings | the benchmark's object, not a built artefact | 12 structural-reasoning tasks |
| **H2Table** | 1 Sep 2026, [2609.01216](https://arxiv.org/abs/2609.01216) | tables (cells + headers) | header-as-hyperedge over cell nodes | table QA |
| **HyperClaim** | 30 Jul 2026, [2607.28375](https://arxiv.org/abs/2607.28375) | video + text | cross-modal claim hyperedge | video misinformation detection |
| **MAGE** | 30 Aug 2026, [2608.29678](https://arxiv.org/abs/2608.29678) | agent messages, tools, documents, evidence | heterogeneous temporal hyperedge | multi-agent memory tasks |

Two of these deserve separate reading.

**VizRAG** is the only system whose hyperedge is *drawn* rather than serialised: it claims to be
"the first RAG system to support visual hypergraph structure awareness" ([Wei, Chen, Gan, Liu, Fu,
Kang, Lu, Liu, Zhang and Kwok, arXiv:2607.19830](https://arxiv.org/abs/2607.19830), 22 Jul 2026).
It is from the same group as HyperGVL, which is the systematic comparison of hypergraph encodings
for vision-language models ([Wei, Kang, Li, Che, Chen et al.,
arXiv:2604.15648](https://arxiv.org/abs/2604.15648), 17 Apr 2026). This pair is the only evidence in
the KB that a *picture* of a hypergraph can be a better model input than a serialisation, and it is
one group's work. See
[../06-visualization/visual-encodings-catalogue.md](../06-visualization/visual-encodings-catalogue.md).

**H2Table** is the table case, which matters because tables are the one modality where n-ary
structure is *given* rather than inferred: a row of a relational table is already an n-ary fact
(see [../01-foundations/n-ary-relations-and-relational-algebra.md](../01-foundations/n-ary-relations-and-relational-algebra.md)).
H2Table represents "complex tables as hierarchical nested hypergraphs" with headers as hyperedges
over cells ([Ling, Wang, Tang, Tan, Yang, Guan and Jiang,
arXiv:2609.01216](https://arxiv.org/abs/2609.01216), 1 Sep 2026). It is a *reasoning* method, not a
KHG constructor — the hypergraph is an encoder input, discarded after the answer.

---

## 3. Scene hypergraphs: the computer-vision lineage

Independently of the knowledge-graph community, video understanding arrived at hyperedges through
scene-graph generation. **HyperGLM** proposes "Multimodal LLMs on a Scene HyperGraph […] promoting
reasoning about multi-way interactions and higher-order relationships", integrating an entity scene
graph with a procedural graph of causal transitions, and introduces the **VSGR** dataset of 1.9
million video frames across third-person, egocentric and drone views ([Nguyen, Nguyen, Cothren,
Yilmaz and Luu, arXiv:2411.18042](https://arxiv.org/abs/2411.18042), 27 Nov 2024; CVPR 2025).

This is worth flagging as a terminology hazard. A "scene hypergraph" is a **spatial/temporal
grouping** structure; it has no role labels, no relation vocabulary shared with Wikidata, and no
provenance. Under the five-question test in
[hypergraph-construction-from-data.md](hypergraph-construction-from-data.md) §7 it is a
co-occurrence hypergraph, not a knowledge hypergraph. The same caution applies to the 2026 crop of
cross-modal hypergraph learners such as prototype hypergraphs for multimodal intent
([2608.04054](https://arxiv.org/abs/2608.04054), 4 Aug 2026) and hypergraph-regularised multimodal
retrieval ([2609.15320](https://arxiv.org/abs/2609.15320), 14 Sep 2026): the hyperedge is a
learning device, not a fact. See
[../10-comparative-and-critique/glossary-of-confusable-terms.md](../10-comparative-and-critique/glossary-of-confusable-terms.md).

---

## 4. Multimodal event extraction: the one *fact-level* multimodal tradition

The genuinely fact-level multimodal line is **multimedia event extraction (M²E²)**, and it predates
the hypergraph wave. Li, Zareian, Zeng, Whitehead, Lu, Ji and Chang define the task of extracting
events and their arguments jointly from text and images, release a benchmark of **245 multimedia
news articles** containing **6,167 sentences and 1,014 images**, and propose Weakly Aligned
Structured Embedding (WASE), reporting gains of 4.0 and 9.8 absolute F₁ over unimodal baselines on
text argument-role labelling and visual event extraction respectively ([*Cross-media Structured
Common Space for Multimedia Event Extraction*, ACL
2020](https://aclanthology.org/2020.acl-main.230/); [project
page](http://blender.cs.illinois.edu/software/m2e2/)).

An event with roles filled from two modalities *is* an n-ary fact whose incidences carry
modality-typed sources — exactly the object this KB is about. Nobody in the hypergraph-RAG line
cites it.

**The 2026 correction.** Seeberger, Freisinger, Bocklet and Riedhammer give "the first systematic
analysis of evaluation pitfalls in multimedia event extraction", identifying "three major sources of
issues: inconsistent data processing, inconsistent task assumptions, and overly relaxed evaluation
setti[ngs]" ([arXiv:2606.26775](https://arxiv.org/abs/2606.26775), 25 Jun 2026; accepted to ACL
2026). This is the multimodal analogue of the benchmark critique in
[../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md),
and it arrived *before* the multimodal hypergraph systems had any benchmark of their own to
criticise.

---

## 5. Non-English and cross-lingual n-ary extraction: the resources that exist

Everything usable here is **event extraction**, not n-ary KG extraction.

| Resource | Year | Languages | Size | Annotation basis | Access |
|---|---|---|---|---|---|
| **ACE 2005 Multilingual Training Corpus** (LDC2006T06) | 2006 | English, Mandarin Chinese, Standard Arabic | EN 303,833 words / 666 files; ZH 334,121 characters / 687 files; AR 112,233 words / 433 files; ~1,800 files total | ACE entity/relation/event guidelines | LDC User Agreement; fee-based |
| **MEE** | 2022 | English, Spanish, Portuguese, Polish, Turkish, Hindi, Japanese, Korean | 31,226 segments; 415,975 entities; 50,011 triggers; 38,748 arguments | ACE-derived type ontology, Wikipedia source | public |
| **MINION** | 2022 | same 8 languages | 13,000 EN segments; 1,499–4,480 per other language | ACE-style event definition, event **detection** only | public |
| **MultiHumES** | 2021 | multilingual humanitarian documents | — | extractive-summarisation snippets, **not** n-ary facts | public |

**ACE 2005** is the ancestor of all closed-schema n-ary extraction, and it is multilingual by
design — English, Chinese and Arabic, released 15 February 2006 ([LDC catalogue
LDC2006T06](https://catalog.ldc.upenn.edu/LDC2006T06)). It is also the licensing outlier: it is
distributed under the "LDC User Agreement for Non-Members" with fees, so it cannot be redistributed
and cannot be used in an open KB pipeline. See
[../10-comparative-and-critique/privacy-licensing-and-governance.md](../10-comparative-and-critique/privacy-licensing-and-governance.md).

**MEE** is the best free multilingual resource with **arguments** (i.e. the n-ary part): "annotation
for more than 50K event mentions in 8 typologically different languages […] comprehensively
annotates data for entity mentions, event triggers and event arguments" ([Pouran Ben Veyseh,
Ebrahimi, Dernoncourt and Nguyen, EMNLP 2022 /
arXiv:2211.05955](https://arxiv.org/abs/2211.05955), Table 2). Its per-language argument counts are
wildly uneven — Portuguese 12,329 arguments against Spanish 802 — so it is not a balanced
cross-lingual argument benchmark despite being a balanced trigger benchmark.

**MINION** covers the same 8 languages for event *detection* only, explicitly because "5 of them
have not been supported by existing multilingual datasets" ([Pouran Ben Veyseh, Nguyen, Dernoncourt
and Nguyen, NAACL 2022 / arXiv:2211.05958](https://arxiv.org/abs/2211.05958)). Its method is the one
to copy: annotators for each language "work together to produce a translation of the English
annotation guideline/examples where language-specific annotation rules are discussed and included in
the translated guideline", verified by language experts (§2.2).

**MultiHumES** ([Yela-Bello, Oglethorpe and Rekabsaz, EACL
2021](https://aclanthology.org/2021.eacl-main.146/)) is multilingual and humanitarian but the task
is **extractive summarisation**, not n-ary extraction; it is not a substitute. `[unverified]` A
dataset named **"XL-Event"** could not be located in any primary source in this run: searches
returned XL-Sum (summarisation) and generic cross-lingual event-argument transfer papers, not a
corpus of that name. It should be treated as non-existent until someone produces a citation.

---

## 6. What does not exist

Stated flatly, because the absence is the finding.

1. **No multilingual n-ary knowledge-graph extraction dataset.** HyperRED is English Wikipedia
   ([Chia, Bing, Aljunied, Si and Poria, EMNLP 2022](https://aclanthology.org/2022.emnlp-main.688/));
   Text2NKG is evaluated on HyperRED ([Luo, E, Yang, Yao, Guo, Tang et al., NeurIPS 2024 /
   arXiv:2310.05185](https://arxiv.org/abs/2310.05185)); HyperDocRED, the 2026 document-level
   benchmark, is introduced alongside Hyper-KGGen with no stated non-English portion ([Huang, Feng,
   Xue, Ying, Yong, Shi, Du and Gao, arXiv:2602.19543](https://arxiv.org/abs/2602.19543), 23 Feb
   2026). JF17K, WikiPeople, WD50K, FB-AUTO and M-FB15K carry no text at all, so "language" for them
   means only the language of the entity labels.
2. **No cross-lingual n-ary evaluation protocol.** There is no zero-shot transfer split for
   hyper-relational extraction analogous to the cross-lingual event-argument transfer literature.
3. **No multimodal n-ary *fact* benchmark.** HyperGVL tests reasoning *about* hypergraph structure;
   Hyper-M2RAG, VizRAG and EvoGraph-R1 are scored on downstream QA. No paper reports precision and
   recall of the extracted multimodal hyperedges themselves — the metric problem of
   [evaluation-of-constructed-khgs.md](evaluation-of-constructed-khgs.md) §2, unsolved and now
   inherited by a second modality.
4. **No cross-modal entity resolution study for hyperedges.** Identifying that the person in the
   photograph is the person named in the caption is the multimodal form of
   [entity-resolution-and-canonicalisation.md](entity-resolution-and-canonicalisation.md); it is
   listed as an open problem in
   [../08-history-and-frontier/current-frontier-directions.md](../08-history-and-frontier/current-frontier-directions.md)
   §11 and has no dedicated paper in this KB's coverage.
5. **No non-Latin-script evaluation of LLM hyperedge extraction.** The extraction prompts catalogued
   in [llm-based-khg-construction.md](llm-based-khg-construction.md) are English prompts over English
   corpora; MEE and MINION show that even trigger annotation needs language-specific rules (Turkish
   *Convict*/*Sentence* collapse into one verb sense, MEE §2), so the prompts are unlikely to port
   unchanged.

---

## 7. What to do about it in this KB

- **Adopt MEE, not ACE, as the multilingual reference.** It is free, it has arguments, and its
  per-language IAA is published (see
  [human-in-the-loop-annotation-and-cost.md](human-in-the-loop-annotation-and-cost.md) §4).
- **Copy MINION's guideline-translation protocol** for any multilingual annotation this repository
  commissions: translate-and-localise the guideline first, verify with a language expert, then
  co-annotate 20% for agreement.
- **Treat tables as the cheapest multimodal source.** A table row is an n-ary fact with named roles
  already; extracting from tables avoids the role-induction problem of
  [schema-induction-and-ontology-alignment.md](schema-induction-and-ontology-alignment.md).
- **Do not report multimodal hyperedge quality as downstream QA.** If this KB builds a multimodal
  KHG, report hyperedge precision/recall against a hand-checked sample, and say the sample size.
- **Record the modality of every incidence, not just of the hyperedge.** HIF's incidence attributes
  can carry it — see
  [../04-storage-and-formats/hif-hypergraph-interchange-format.md](../04-storage-and-formats/hif-hypergraph-interchange-format.md).

Open questions raised by this note belong in
[../00-index/open-questions.md](../00-index/open-questions.md) tagged `03`.

## Sources

- Chen, S., Xu, Y., Han, X., Xue, R., Wu, D., Gao, Y., Yan, C., Gao, Y. "Hypergraph-based Multimodal Retrieval-Augmented Generation with Incremental Refinement" (Hyper-M2RAG). arXiv:2608.16628, 17 Aug 2026. <https://arxiv.org/abs/2608.16628>
- Wei, Y., Chen, Y., Gan, R., Liu, Z., Fu, X., Kang, C., Lu, N., Liu, R., Zhang, Y., Kwok, J. "VizRAG: Enhancing Retrieval-Augmented Generation with Hypergraph Visualization." arXiv:2607.19830, 22 Jul 2026. <https://arxiv.org/abs/2607.19830>
- Wei, Y., Kang, C., Li, S., Che, H., Chen, Y. et al. "HyperGVL: Benchmarking and Improving Large Vision-Language Models in Hypergraph Understanding and Reasoning." arXiv:2604.15648, 17 Apr 2026 (under review). <https://arxiv.org/abs/2604.15648>
- Lin, J., Jiang, C., Lin, X., Zhang, R., Zhu, X., Liu, J. et al. "EvoGraph-R1: Self-Evolving Multimodal Knowledge Hypergraphs for Agentic Retrieval." arXiv:2607.12764, 14 Jul 2026. <https://arxiv.org/abs/2607.12764>
- Ling, J., Wang, Y., Tang, C., Tan, H., Yang, Y., Guan, Y., Jiang, J. "H2Table: Hierarchical Hypergraph-Enhanced Large Language Models for Complex Table Reasoning." arXiv:2609.01216, 1 Sep 2026. <https://arxiv.org/abs/2609.01216>
- Wang, X., Zhang, J., Yu, X., Lei, L., Zhang, D. C. "HyperClaim: Fine-Grained Cross-Modal Hypergraph Reasoning for Video Misinformation Detection." arXiv:2607.28375, 30 Jul 2026. <https://arxiv.org/abs/2607.28375>
- Feng, Y., Zhang, R., Luo, H., Lin, Z., Yang, C., Luu, A. T. "Diachronic Hypergraphs for Orchestrated Multi-Agent Multimodal Memory Curation" (MAGE). arXiv:2608.29678, 30 Aug 2026. <https://arxiv.org/abs/2608.29678>
- Raj, M., Kumar, S., Chattopadhayay, S., Adak, C., Dutta, A. "Modality Agreement- and Conflict-Aware Prototype Hypergraph Learning for Multimodal Intent Understanding." arXiv:2608.04054, 4 Aug 2026. <https://arxiv.org/abs/2608.04054>
- Nag, A., Mehrish, A., Vascon, S. "Hypergraph-Regularized Gramian Volumes for Multimodal Retrieval." arXiv:2609.15320, 14 Sep 2026. <https://arxiv.org/abs/2609.15320>
- Nguyen, T.-T., Nguyen, P., Cothren, J., Yilmaz, A., Luu, K. "HyperGLM: HyperGraph for Video Scene Graph Generation and Anticipation." arXiv:2411.18042, 27 Nov 2024; CVPR 2025. <https://arxiv.org/abs/2411.18042>
- Li, M., Zareian, A., Zeng, Q., Whitehead, S., Lu, D., Ji, H., Chang, S.-F. "Cross-media Structured Common Space for Multimedia Event Extraction." ACL 2020, pp. 2557–2568. <https://aclanthology.org/2020.acl-main.230/> ; project page and annotation guideline <http://blender.cs.illinois.edu/software/m2e2/>
- Seeberger, P., Freisinger, S., Bocklet, T., Riedhammer, K. "Evaluation Pitfalls and Challenges in Multimedia Event Extraction." arXiv:2606.26775, 25 Jun 2026; accepted to ACL 2026. <https://arxiv.org/abs/2606.26775>
- Linguistic Data Consortium. "ACE 2005 Multilingual Training Corpus," LDC2006T06, released 15 Feb 2006. <https://catalog.ldc.upenn.edu/LDC2006T06>
- Pouran Ben Veyseh, A., Ebrahimi, J., Dernoncourt, F., Nguyen, T. H. "MEE: A Novel Multilingual Event Extraction Dataset." EMNLP 2022; arXiv:2211.05955. <https://arxiv.org/abs/2211.05955>
- Pouran Ben Veyseh, A., Nguyen, M. V., Dernoncourt, F., Nguyen, T. H. "MINION: a Large-Scale and Diverse Dataset for Multilingual Event Detection." NAACL 2022; arXiv:2211.05958. <https://arxiv.org/abs/2211.05958> ; <https://aclanthology.org/2022.naacl-main.166/>
- Yela-Bello, J. P., Oglethorpe, E., Rekabsaz, N. "MultiHumES: Multilingual Humanitarian Dataset for Extractive Summarization." EACL 2021. <https://aclanthology.org/2021.eacl-main.146/>
- Chia, Y. K., Bing, L., Aljunied, S. M., Si, L., Poria, S. "A Dataset for Hyper-Relational Extraction and a Cube-Filling Approach" (HyperRED, CubeRE). EMNLP 2022; arXiv:2211.10018. <https://aclanthology.org/2022.emnlp-main.688/>
- Luo, H., E, H., Yang, Y., Yao, T., Guo, Y., Tang, Z. et al. "Text2NKG: Fine-Grained N-ary Relation Extraction for N-ary relational Knowledge Graph Construction." NeurIPS 2024; arXiv:2310.05185. <https://arxiv.org/abs/2310.05185>
- Huang, R., Feng, Y., Xue, R., Ying, S., Yong, J.-H., Shi, C., Du, S., Gao, Y. "Hyper-KGGen: A Skill-Driven Knowledge Extractor for High-Quality Knowledge Hypergraph Generation" (introduces HyperDocRED). arXiv:2602.19543, 23 Feb 2026. <https://arxiv.org/abs/2602.19543>
- arXiv API queries for `all:hypergraph`, `all:"n-ary"` and `abs:"higher-order network"` restricted to `submittedDate:[202606010000 TO 202609202359]`, run 2026-09-20; 404 unique records retrieved. <https://export.arxiv.org/api/query>
