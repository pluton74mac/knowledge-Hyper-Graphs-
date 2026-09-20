---
title: N-ary relation and event extraction from text
type: survey
status: draft
tags: [hypergraph, n-ary, relation-extraction, event-extraction, openie, semantic-roles, document-level]
created: 2026-09-19
updated: 2026-09-19
---

# N-ary relation and event extraction from text

The extraction stage is where a knowledge hypergraph gets its hyperedges. This note surveys the lineages
of text-to-n-ary-fact extraction that predate LLM prompting, and the supervised n-ary extractors that were
built specifically for n-ary knowledge graph construction. LLM-prompted pipelines are treated separately in
[llm-based-khg-construction.md](llm-based-khg-construction.md).

## 1. Event extraction with fixed schemas (ACE 2005)

The closest established precursor of KHG extraction is *event extraction*: an event mention is a trigger word
plus a set of typed arguments, i.e. an n-ary fact with named roles. The ACE 2005 English guidelines define
"Event participants and Event attributes" collectively as "Event arguments" and state that "Only Entities and
Values within the extent of an Event are permissible arguments" ([LDC, ACE English Annotation Guidelines for
Events v5.4.3, 2005](https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/english-events-guidelines-v5.4.3.pdf)).
The guideline's type inventory has 8 types — LIFE, MOVEMENT, TRANSACTION, BUSINESS, CONFLICT, CONTACT,
PERSONNEL, JUSTICE — with 33 subtypes (e.g. LIFE: Be-Born, Marry, Divorce, Injure, Die; JUSTICE has 13
subtypes from Arrest-Jail to Pardon). One ACE restriction matters for KHG design: "we will not allow Events to
act as arguments in other Events", so ACE events are flat hyperedges over entities, not nested ones. The
corpus itself covers "English, Arabic, and Chinese" with roughly 1,800 files
([LDC2006T06](https://catalog.ldc.upenn.edu/LDC2006T06)).

Event-centric KGs generalise this. The survey by [Guan et al., 2022](https://arxiv.org/abs/2112.15280)
defines an event knowledge graph with event nodes, entity nodes and three edge families
(event–event, event–entity, entity–entity), and lists four acquisition tasks: event extraction ("event
triggers with types and arguments with roles"), event relation extraction ("temporal and causal relations"),
event coreference resolution and event argument completion. Each event with its role-labelled arguments is a
role-based n-ary fact; the event–event edges are relations *between* hyperedges, which plain hypergraph
schemas cannot express without reification.

## 2. Semantic role labelling as generic n-ary extraction

PropBank ([Palmer, Gildea & Kingsbury, 2005](https://aclanthology.org/J05-1004/)) and FrameNet
([Baker, Fillmore & Lowe, 1998](https://aclanthology.org/P98-1013/)) supply predicate–argument structures:
a verb (or frame-evoking word) with numbered (PropBank Arg0, Arg1, …) or named (FrameNet frame element)
roles. A semantic-role-labelled sentence is therefore already a set of n-ary propositions. Open IE systems
have used this directly: OpenIE 5's SRLIE component is "semantic role labeling-based"
([OpenIE-standalone repository](https://github.com/dair-iitd/OpenIE-standalone)). The limitation for KHG
construction is that SRL roles are predicate-specific and sentence-local; turning them into a corpus-level
hypergraph still needs entity resolution and role canonicalisation.

## 3. Open information extraction and n-ary tuples

Open IE extracts relation tuples without a predefined schema.

- **Stanford OpenIE** ([Angeli, Premkumar & Manning, 2015](https://aclanthology.org/P15-1034/)) splits
  sentences into clauses and uses natural-logic entailment to shorten them; its output is triples —
  "a subject, a relation, and the object of the relation", e.g. `born-in(Barack Obama, Hawaii)`
  ([CoreNLP OpenIE docs](https://stanfordnlp.github.io/CoreNLP/openie.html)). Optional arguments are
  dropped, so n-ary facts are lost or spread over several triples.
- **ClausIE** ([Del Corro & Gemulla, 2013](https://dl.acm.org/doi/10.1145/2488388.2488420)) detects clauses
  and their grammatical type first, then decides how to represent them as extractions. The original paper
  describes generating n-ary propositions in addition to triples [unverified — the PDF could not be fetched
  during this run; only title/venue were confirmed].
- **OpenIE 5.x** combines "SRLIE (semantic role labeling-based), RelNoun (noun-mediated relations), BONIE
  (numerical sentence extraction), CALMIE (conjunctive sentence handling)" and attaches context/attribution to
  extractions, e.g. `Some people say:(Barack Obama, was born in, Kenya)`
  ([OpenIE-standalone repository](https://github.com/dair-iitd/OpenIE-standalone)). Conjunctions are expanded
  into multiple tuples (Jack and Jill visited India, Japan and South Korea → six extractions), which is the
  opposite of what a KHG wants: the joint fact (Jack, Jill, visited, {India, Japan, South Korea}) is
  flattened.
- **OpenIE6** ([Kolluru et al., 2020](https://arxiv.org/abs/2010.03147)) treats "OpenIE as a 2-D grid
  labeling task" with a coordination analyser and reports about 4 F1 points over prior systems on CaRB while
  being "10x faster".

Evaluation of Open IE uses CaRB, "the first crowdsourced Open IE dataset" with revised tuple-matching
([Bhardwaj, Aggarwal & Mausam, 2019](https://aclanthology.org/D19-1651/)). Because Open IE phrases are not
canonical, an Open KB needs a canonicalisation step (CESI, [Vashishth et al., 2018](https://arxiv.org/abs/1902.00172));
see [entity resolution](entity-resolution-and-canonicalisation.md).

## 4. Cross-sentence and document-level n-ary extraction

**Peng et al. (2017)** is the canonical cross-sentence n-ary work. The task is a ternary
drug–gene–mutation interaction, "broadly construed as an association between the drug efficacy and the
mutation in the given gene". They build a *document graph* over "linear context (adjacent words), syntactic
dependencies, and discourse relations", run a graph LSTM over it, and train with distant supervision from the
Gene Drug Knowledge Database and CIViC over "approximately one million full-text articles" from PubMed
Central. Distant supervision yielded "3,462 ternary relation instances" from only 59 unique KB triples.
Cross-sentence extraction reached 80.7% accuracy vs 77.9% single-sentence, and at corpus scale with
probability ≥ 0.9 produced 1,461 unique interactions vs 530 for single-sentence extraction
([Peng et al., 2017](https://arxiv.org/abs/1708.03743)). Two lessons carry over to KHGs: n-ary facts need
cross-sentence context, and distant supervision from an existing n-ary KB is a practical way to bootstrap
training data.

**DocRED** ([Yao et al., 2019](https://arxiv.org/abs/1906.06127)) generalised document-level RE to
Wikipedia: 5,053 human-annotated documents, 96 relation types, 56,354 relational facts, plus 101,873
distantly supervised documents. Its annotation pipeline — distant supervision from Wikidata, human NER and
coreference, entity linking ("Each named entity mention is associated with a Wikidata item candidate set"),
then relation and evidence-sentence annotation — is a template for building n-ary gold data as well. DocRED
facts are binary, but the evidence-sentence annotation shows how far apart participants of one fact sit.

## 5. Supervised extractors built for n-ary knowledge graphs

### HyperRED and CubeRE (2022)

[Chia et al., 2022](https://arxiv.org/abs/2211.10018) introduced *hyper-relational extraction*: extract a
triple together with qualifiers, e.g. (Leonard Parker, Educated At, Harvard University) with (End Time,
1967). HyperRED was built by distant supervision between English Wikipedia and Wikidata — entities are
extracted and linked, coreference is resolved, and a sentence is kept when head, tail and qualifier value all
appear — followed by human labelling of a subset as "correct", "invalid triplet" or "invalid qualifier"
(Cohen's kappa 0.56). Statistics: 39,840 distantly supervised training sentences, 1,000 dev and 4,000 test
human-annotated sentences, 62 relation labels, 44 qualifier labels
([Chia et al., 2022](https://arxiv.org/abs/2211.10018); the [repository](https://github.com/declare-lab/HyperRED)
summarises it as "44k sentences with 62 relation types and 44 qualifier types"). CubeRE is a
"cube-filling model inspired by table-filling approaches" that "explicitly considers the interaction between
relation triplets and qualifiers". A fact counts as correct only when "the whole fact f=(e_head, r, e_tail, q,
e_value) must match the ground-truth fact in terms of relation label, qualifier label and entity bounds".

### Text2NKG (2024)

[Luo et al., 2024](https://arxiv.org/abs/2310.05185) is the first extractor that targets all four n-ary KG
schemas. It formulates *fine-grained n-ary relation extraction*: given a sentence with entity spans, perform
"multi-label classification of one of the ordered span-tuple" over entity triples, using packed levitated
markers to cut complexity "from O(m³) to O(m)". Two merging steps then build facts of arbitrary arity:
*hetero-ordered merging* combines the six orderings of a span triple into one label set, and *output
merging* "merge[s] the output 3-ary relational facts to form higher-arity facts" using schema-specific
grouping rules. They extended HyperRED to the four schemas (Table 1: 40,293 entities; 44,840 train, 1,000
dev, 4,000 test sentences) and report F1 of 83.63 (test, hyper-relational, base encoder) — "improved by
… 18.60 percentage points in the test set" over CubeRE — and 84.19 / 83.76 / 85.89 on the event-based,
role-based and hypergraph-based schemas with a large encoder. The evaluation is strict: "the entire fact must
match the ground facts completely".

### Zero-shot LLM baselines on the same task

[Datta et al., 2024](https://arxiv.org/abs/2403.11786) tried "a zero-shot prompt-based method" for
hyper-relational extraction and reached "a recall of 0.77" but note that "precision is currently lower".
[Zhu et al., 2026](https://link.springer.com/article/10.1007/s40747-026-02475-1) (HKG-MLLM) use several
lightweight open-source LLMs with automatically optimised prompts plus an "HRKG correction" module on
HyperRED and report gains "in precision, recall, and F1 score compared to existing methods based on LLM".
Text2NKG's own comparison found unsupervised prompting of large commercial models far below the supervised
model on this benchmark ([Luo et al., 2024](https://arxiv.org/abs/2310.05185), Appendix D). The pattern —
high recall, weaker precision, strict-match F1 well below supervised extractors — recurs in
[LLM-based construction](llm-based-khg-construction.md).

## 6. Comparison

| Family | Schema | Arity | Roles | Cross-sentence | Typical output |
|---|---|---|---|---|---|
| ACE event extraction | closed (8 types / 33 subtypes) | variable | named roles | no (sentence) | event mention + arguments |
| SRL (PropBank/FrameNet) | per-predicate | variable | numbered / frame elements | no | predicate–argument structure |
| Stanford OpenIE | open | 2 | none | no | triples |
| OpenIE 5/6 | open | 2 + context | none | no | tuples with attribution |
| Peng et al. 2017 | closed (1 relation) | 3 | fixed positions | yes (document graph) | ternary instances |
| DocRED | closed (96 relations) | 2 | s/o | yes (document) | triples + evidence |
| CubeRE / HyperRED | hyper-relational (62 rel., 44 qual.) | 3–5 | qualifier keys | no | triple + qualifiers |
| Text2NKG | 4 schemas | any (merged) | keys / order | no | facts of any arity |

## Open problems

- Sentence-level supervision dominates the KHG-specific benchmarks (HyperRED, Text2NKG), while the facts that
  most need hyperedges are cross-sentence (DocRED's 40.7%). A document-level n-ary benchmark with gold
  hyperedges was not found.
- Nested facts (events as arguments of events) are excluded by ACE and by all four Text2NKG schemas.
- No shared metric handles partial credit for hyperedges that differ in arity from the gold fact.

## Sources

- Linguistic Data Consortium. "ACE (Automatic Content Extraction) English Annotation Guidelines for Events, Version 5.4.3", 2005-07-01. https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/english-events-guidelines-v5.4.3.pdf
- Linguistic Data Consortium. "ACE 2005 Multilingual Training Corpus", LDC2006T06, 2006. https://catalog.ldc.upenn.edu/LDC2006T06
- Guan, S., Cheng, X., Bai, L., Zhang, F., et al. "What is Event Knowledge Graph: A Survey." IEEE TKDE 2022 / arXiv 2112.15280. https://arxiv.org/abs/2112.15280
- Palmer, M., Gildea, D., Kingsbury, P. "The Proposition Bank: An Annotated Corpus of Semantic Roles." Computational Linguistics 31(1), 2005. https://aclanthology.org/J05-1004/
- Baker, C. F., Fillmore, C. J., Lowe, J. B. "The Berkeley FrameNet Project." ACL-COLING 1998. https://aclanthology.org/P98-1013/
- Angeli, G., Premkumar, M. J., Manning, C. D. "Leveraging Linguistic Structure For Open Domain Information Extraction." ACL-IJCNLP 2015. https://aclanthology.org/P15-1034/
- Stanford NLP. "Open Information Extraction" (CoreNLP documentation), checked 2026-09-19. https://stanfordnlp.github.io/CoreNLP/openie.html
- Del Corro, L., Gemulla, R. "ClausIE: clause-based open information extraction." WWW 2013. https://dl.acm.org/doi/10.1145/2488388.2488420
- dair-iitd. "OpenIE-standalone" (Open IE 5.1) repository, checked 2026-09-19. https://github.com/dair-iitd/OpenIE-standalone
- Kolluru, K., Adlakha, V., Aggarwal, S., Mausam, Chakrabarti, S. "OpenIE6: Iterative Grid Labeling and Coordination Analysis for Open Information Extraction." EMNLP 2020 / arXiv 2010.03147. https://arxiv.org/abs/2010.03147
- Bhardwaj, S., Aggarwal, S., Mausam. "CaRB: A Crowdsourced Benchmark for Open IE." EMNLP-IJCNLP 2019. https://aclanthology.org/D19-1651/
- Vashishth, S., Jain, P., Talukdar, P. "CESI: Canonicalizing Open Knowledge Bases using Embeddings and Side Information." WWW 2018 / arXiv 1902.00172. https://arxiv.org/abs/1902.00172
- Peng, N., Poon, H., Quirk, C., Toutanova, K., Yih, W. "Cross-Sentence N-ary Relation Extraction with Graph LSTMs." TACL 5, 2017. https://arxiv.org/abs/1708.03743
- Yao, Y., Ye, D., Li, P., Han, X., et al. "DocRED: A Large-Scale Document-Level Relation Extraction Dataset." ACL 2019 / arXiv 1906.06127. https://arxiv.org/abs/1906.06127
- Chia, Y. K., Bing, L., Aljunied, S. M., Si, L., Poria, S. "A Dataset for Hyper-Relational Extraction and a Cube-Filling Approach." EMNLP 2022 / arXiv 2211.10018. https://arxiv.org/abs/2211.10018
- declare-lab. HyperRED repository, checked 2026-09-19. https://github.com/declare-lab/HyperRED
- Luo, H., E, H., Yang, Y., Yao, T., et al. "Text2NKG: Fine-Grained N-ary Relation Extraction for N-ary relational Knowledge Graph Construction." NeurIPS 2024 / arXiv 2310.05185. https://arxiv.org/abs/2310.05185
- Datta, P., Vitiugin, F., Chizhikova, A., Sawhney, N. "Construction of Hyper-Relational Knowledge Graphs Using Pre-Trained Large Language Models." arXiv 2403.11786, 2024. https://arxiv.org/abs/2403.11786
- Zhu, Q., Wei, X., Wang, Q., Yan, Y., Yuan, H., Shen, T. "Multi-LLM collaborative hyper-relational knowledge graph construction with automatic prompt optimization." Complex & Intelligent Systems, 2026. https://link.springer.com/article/10.1007/s40747-026-02475-1
