---
title: Human-in-the-loop annotation of n-ary facts, and what it costs
type: survey
status: draft
tags: [construction, annotation, inter-annotator-agreement, active-learning, cost, curation, human-factors, gap-filling]
created: 2026-09-20
updated: 2026-09-20
---

# Human-in-the-loop annotation and cost

[curation-crowdsourcing-and-quality.md](curation-crowdsourcing-and-quality.md) covers curation
*regimes* — who curates and under what governance.  This note covers the layer below: the
**annotation instrument** (what a person is actually shown and asked), the **agreement** that
instrument produces, the **active-learning** machinery for spending annotation effort well, and the
**money and person-time** that the whole business costs.

Three findings, argued below:

1. **The published n-ary annotation instruments are binary-judgement instruments.** HyperRED and
   the ACE-derived event corpora do not ask an annotator to *build* an n-ary fact; they ask for a
   verdict on a fact that a machine proposed, or for one span at a time. Nobody has published a
   protocol for constructing an arbitrary-arity fact from scratch.
2. **There is no study of inter-annotator agreement as a function of arity.** The closest evidence
   is per-*task* agreement in MEE (entity mentions vs. triggers vs. arguments) and a single Cohen's
   κ for HyperRED. Both are reported in §4; neither varies arity as an independent variable.
3. **Section 08's "no human-factors study found" is confirmed, not refuted.** A bounded search on
   2026-09-20 found no controlled study comparing human curation, review or debugging of an n-ary
   fact against the equivalent reified triples (§7).

---

## 1. Why annotating an n-ary fact is a different job

A binary relation-extraction annotator makes one decision per candidate pair. An n-ary annotator
faces three decisions with no binary analogue. **Membership:** which mentions belong to *this* fact
rather than a neighbouring one — the grouping problem hyperedges exist to express, and the only one
the hypergraph-RAG literature treats as solved. **Role assignment:** which slot each member fills —
ACE's *Victim* vs. *Attacker*, Wikidata's qualifier property, HyperRED's `qualifier label` — which
[README.md](README.md) records as the field's hardest unsolved step. **Arity closure:** is the fact
complete, or is a participant missing from the text? A binary annotator never has to decide how many
arguments there *should* be.

The instruments below each dodge at least one of the three.

---

## 2. The annotation instruments, one by one

### ACE 2005 — the closed-schema ancestor

The ACE 2005 Multilingual Training Corpus (LDC2006T06, released 15 February 2006) annotates
entities, relations and events over English (303,833 words / 666 files), Mandarin Chinese (334,121
characters / 687 files) and Standard Arabic (112,233 words / 433 files), ~1,800 files in total
([LDC catalogue LDC2006T06](https://catalog.ldc.upenn.edu/LDC2006T06)). "Annotation guidelines, task
definitions and other documentation" live on the LDC's ACE website rather than in the release —
which is why so many downstream papers describe the schema second-hand. The instrument is
**span-then-role**: mark the trigger, then each argument, choosing its role from a fixed
per-event-type list. Arity is bounded by the schema, so arity closure is never asked.

### HyperRED — the only published rubric for a hyper-relational fact

HyperRED is built by distant supervision "partially refined through human annotation", and its rubric
is a three-way classification, reproduced verbatim from the paper's Appendix A:

> "The task is a classification of whether each hyper-relational fact can be reasonably extracted
> from a piece of text. […] The annotator should classify each sample as 'Correct' or 'Invalid
> Triplet' or 'Invalid Qualifier'."
> — [Chia, Bing, Aljunied, Si and Poria, EMNLP 2022](https://aclanthology.org/2022.emnlp-main.688/)

The fact shown has a fixed five-slot shape `(head entity, relation label, tail entity, qualifier
label, value entity)`, and the annotator is told that "all the entities, relations, and qualifiers
exist in the Wikidata database, so annotators can refer to the relation or qualifier definition at
https://www.wikidata.org for clarification". Step 2 of the procedure checks the primary triple
first; only if the triple survives is the qualifier judged.

Three things follow. **(a)** The instrument inherits Wikidata's property definitions as the role
vocabulary, externalising annotation cost onto a pre-existing ontology. **(b)** Arity is fixed at
one qualifier, so the hardest n-ary judgement is engineered away. **(c)** The judgement is a
*verdict on a proposal*, so pipeline recall is bounded by distant supervision, not by annotators.
Outcome: 39,840 train / 1,000 dev / 4,000 test samples, 44,372 unique facts, 62 relation labels and
44 qualifier labels (ibid., Table 2).

### HyperDocRED — document-level, 2026, protocol not public

Hyper-KGGen introduces "HyperDocRED, a rigorously annotated benchmark for document-level knowledge
hypergraph extraction" ([Huang, Feng, Xue, Ying, Yong, Shi, Du and Gao,
arXiv:2602.19543](https://arxiv.org/abs/2602.19543), 23 Feb 2026). `[unverified]` The abstract
states that the benchmark is "rigorously annotated" but gives no annotator count, no rubric and no
agreement figure in the material retrieved for this note; the claim of rigour should not be
propagated without reading the full paper.

### MEE and MINION — the multilingual protocol worth copying

Both corpora use the same three-stage instrument and the same agreement discipline: "20% of text
segments for each language will be co-annotated by the annotators to measure agreement score. The
remaining 80% [is] distributed to annotators for separate annotation" ([Pouran Ben Veyseh, Ebrahimi,
Dernoncourt and Nguyen, EMNLP 2022 / arXiv:2211.05955](https://arxiv.org/abs/2211.05955) §2.2). MEE
runs the three tasks *in sequence* — entity mentions, then triggers, then arguments — each over the
output of the last, which is the closest published approximation to incremental hyperedge
construction.

MINION adds the localisation step: annotators for each language "work together to produce a
translation of the English annotation guideline/examples where language-specific annotation rules
are discussed and included in the translated guideline", verified by language experts ([Pouran Ben
Veyseh, Nguyen, Dernoncourt and Nguyen, NAACL 2022 /
arXiv:2211.05958](https://arxiv.org/abs/2211.05958) §2.2). See
[multimodal-and-multilingual-construction.md](multimodal-and-multilingual-construction.md) §5.

### Wikidata qualifier editing — the largest n-ary annotation instrument in existence

Qualifiers "allow statements to be expanded on, annotated, or contextualized beyond what can be
expressed in just a simple property-value pair" and "are used in order to further describe or refine
the value of a property given in a statement" ([Wikidata,
*Help:Qualifiers*](https://www.wikidata.org/wiki/Help:Qualifiers), checked 2026-09-20). The gesture
is five clicks: edit the statement, "add qualifier", type the property, type the value, save. One
structural rule is stated: qualifiers "should not be used to modify the values of other qualifiers
on a main statement, since this can make the meaning of the qualifier ambiguous."

That single sentence is the entire published guidance on nesting — and it is a *prohibition*, which
is why Wikidata is hyper-relational and not recursively n-ary. Compare
[../02-knowledge-representation/wikidata-and-freebase-data-models.md](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

### M²E² — the multimodal instrument

The multimedia event-extraction benchmark publishes its guideline as a standalone document
(*Multimedia Event Extraction (M2E2) Annotation Guideline V0.1*, linked from the [project
page](http://blender.cs.illinois.edu/software/m2e2/)), for 245 annotated news articles ([Li,
Zareian, Zeng, Whitehead, Lu, Ji and Chang, ACL 2020](https://aclanthology.org/2020.acl-main.230/)).
It is the only instrument here that asks an annotator to fill one event's roles from two modalities.

---

## 3. A comparison of the instruments

| Instrument | Unit shown to annotator | Roles from | Arity decided by | Agreement published |
|---|---|---|---|---|
| ACE 2005 | sentence + span | fixed per event type | schema | not in catalogue |
| HyperRED | sentence + one proposed 5-slot fact | Wikidata properties | fixed at 1 qualifier | **Cohen's κ = 0.56** |
| HyperDocRED | document `[unverified]` | `[unverified]` | `[unverified]` | none found |
| MEE | 5-sentence segment, 3 passes | ACE-derived ontology | schema | **per task, per language** |
| MINION | 5-sentence segment, triggers only | ACE-derived ontology | n/a (detection only) | **Krippendorff's α + MASI** |
| Wikidata | one statement in a UI form | any property | editor, unbounded | none (no IAA concept) |
| M²E² | article + images | ACE-derived | schema | not retrieved |

---

## 4. Agreement, and the arity question

**HyperRED.** "Each alignment sample is annotated by two professional annotators working
independently. There are 6780 sentences annotated in total and the inter-annotator agreement is
measured using Cohen's kappa with a value of **0.56**" — described by the authors as "comparable
with previous relation extraction datasets", with a third annotator adjudicating disagreements, and
**76%** of the distantly supervised samples judged "correct" ([Chia et al.,
2022](https://aclanthology.org/2022.emnlp-main.688/) §3). κ = 0.56 is "moderate" on the conventional
Landis–Koch bands; for a three-way verdict task on a pre-proposed fact, that is not high.

**MEE** is the only source in this KB that separates agreement by the *structural complexity of the
judgement*, because it runs the same annotators over three tasks. Krippendorff's α with MASI
distance, per language ([arXiv:2211.05955](https://arxiv.org/abs/2211.05955), Table 3):

| Language | #Annot. | Entity mentions (EMD) | Triggers (ED) | **Arguments (EAE)** |
|---|---|---|---|---|
| English | 10 | 0.792 | 0.834 | 0.820 |
| Spanish | 10 | 0.788 | 0.812 | 0.823 |
| Portuguese | 5 | 0.791 | 0.803 | 0.799 |
| Polish | 8 | 0.780 | 0.799 | 0.813 |
| Turkish | 10 | 0.785 | 0.813 | 0.822 |
| Hindi | 6 | 0.790 | 0.803 | 0.812 |
| Japanese | 5 | 0.793 | 0.789 | **0.780** |
| Korean | 6 | 0.802 | 0.810 | 0.825 |

**Reading.** Argument annotation — the n-ary step — is *not* systematically worse than trigger or
entity annotation: it is lower in three of eight languages and higher in five. That is the strongest
evidence available for n-ary annotation feasibility. But it is **not** arity-stratified: MEE's
events have a small, schema-bounded number of roles, and the table does not break agreement down by
how many arguments an event had. **MINION** reports α from 0.789 (Japanese) to 0.834 (English) for
event detection over the same 8 languages ([arXiv:2211.05958](https://arxiv.org/abs/2211.05958),
Table 2), confirming that the trigger task is stable across typologically distant languages.

**The gap.** No paper found in this run reports agreement as a function of the number of
participants in the fact. The experiment is cheap — re-analyse MEE's raw annotations by argument
count — and nobody has published it. This is the concrete open problem of this note.

---

## 5. Active learning: how to spend annotation effort

Active learning is the standard answer to "annotation is expensive", and event extraction is where
it has been applied closest to the n-ary case: Shen, Li and Qi introduce it "to reduce the cost of
event annotation", noting that domain-event annotation "requires the participation of experts from
corresponding domain", and propose memory-based loss-prediction sampling
([arXiv:2112.03073](https://arxiv.org/abs/2112.03073), 26 Nov 2021). Two adjacent results bound the
expected saving: in clinical information extraction active learning "achieve[s] the same
effectiveness as supervised learning while saving up to 77% of the total number of sequences
requiring manual annotation" ([Kholghi, De Vine, Sitbon, Zuccon and Nguyen,
arXiv:1607.02810](https://arxiv.org/abs/1607.02810)), while a benchmark of six deep strategies
across seven biomedical relation-extraction datasets finds the picture strategy-dependent rather
than uniformly favourable ([*PLOS ONE* 18(12):
e0292356, 2023](https://doi.org/10.1371/journal.pone.0292356)) `[unverified]` (author list not
confirmed from the publisher page in this run).

**None of these is n-ary.** An n-ary sampler has an extra degree of freedom — query the *arity* or a
*single role* of an uncertain fact rather than the whole fact — and the partial-annotation
literature ([arXiv:2305.12634](https://arxiv.org/abs/2305.12634)) is the closest existing machinery.
No published system does this for hyper-relational facts.

---

## 6. What it costs

**Expert curation (Cyc).** The canonical upper bound, from the project's founder: "it has taken a
coherent team of logicians and programmers **four decades, 2000 person-years**, to produce the
current Cyc KB", which "comprises tens of millions of hand-authored assertions, almost all of which
are general 'rule of thumb' axioms" ([Lenat and Marcus,
arXiv:2308.04445](https://arxiv.org/abs/2308.04445), 31 Jul 2023). The organisational finding
alongside it is worth more than the number: "Cycorp's experiments with larger-sized teams generally
showed a net decrease in total productivity, due to lack of coherence, deeper reporting chains, and
so on." Expert n-ary curation does not parallelise.

**Volunteer curation (Wikidata).** **123,419,629 items**, **2,547,303,553 edits** since launch,
**43,497 active users** ([*Wikidata:Statistics*, page last updated 31 August
2025](https://www.wikidata.org/wiki/Wikidata:Statistics), checked 2026-09-20) — roughly 20.6 edits
per item over the project's lifetime. An edit is not a fact, so the number bounds effort, not
output; qualifier coverage, the figure that would matter, is not published there, and the derived
benchmarks put n-ary facts at 11.6–13.6%
([../10-comparative-and-critique/limitations-and-failure-modes.md](../10-comparative-and-critique/limitations-and-failure-modes.md)).

**Paid annotation.** HyperRED alone states its labour arrangement — "we employ two professional data
annotators, and they have been fairly compensated" for 6,780 sentences ([Chia et al.,
2022](https://aclanthology.org/2022.emnlp-main.688/), Ethics). No rate is given, so **cost-per-fact
cannot be computed from any published n-ary dataset.**

**LLM extraction.** [HyperGraphRAG](https://arxiv.org/abs/2503.21322) reports **3.084 s and $0.0063
per 1k tokens** for construction
against 9.272 s for its graph-RAG comparison — recorded with its caveats in
[construction-pipeline-overview.md](construction-pipeline-overview.md) and read critically in
[../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md).
A 1-million-token corpus therefore costs about **$6.30**, three to four orders of magnitude below
any human protocol above — and yields hyperedges with the identity, role and arity defects listed in
[README.md](README.md). **The honest comparison is not cost-per-fact but cost-per-*correct*-fact**,
and nobody reports it, because nobody reports extraction precision against a human gold standard on
their own corpus.

---

## 7. Human factors: n-ary vs. reified triples

[../08-history-and-frontier/current-frontier-directions.md](../08-history-and-frontier/current-frontier-directions.md)
lists as cross-cutting gap 6: "**Human factors**: is an n-ary fact easier or harder for a person to
curate, review and debug than the equivalent reified triples? No study found."

**This note confirms it.** Searches on 2026-09-20 across the annotation, HCI and
knowledge-engineering literature surfaced no controlled study in which the *representation* is the
independent variable and human accuracy or time the dependent variable. `[unverified]` — absence of
evidence from a bounded search, not evidence of absence.

The indirect evidence points both ways. *For n-ary:* MEE's argument agreement matches its entity
agreement (§4), so filling several roles is not measurably harder than marking spans. *For
reification:* HyperRED's rubric checks "the triple first, then the qualifier" — the authors chose a
reified review order for hyper-relational data. And Wikidata's prohibition on
qualifiers-of-qualifiers (§2) is a usability decision that constitutes the field's largest natural
experiment in what editors can sustain.

**Opinion.** A within-subjects design — the same 40 facts shown as role-labelled n-ary tuples to one
arm and as reified triples to the other, measuring error rate and time-to-verdict — would settle
gap 6 in a week of participant time, and would be the most-cited thing in this corner of the
literature.

---

## 8. A protocol this repository could adopt

1. **Never annotate without a rubric document.** Copy HyperRED's three-way verdict shape, but add a
   fourth class, "incomplete — participant missing", so arity closure is recorded rather than
   silently collapsed into "correct".
2. **Co-annotate 20%**, report Krippendorff's α with MASI per the MEE/MINION discipline, **and
   stratify it by arity** — the number nobody has published.
3. **Adjudicate with a third annotator** and keep the adjudication trace as provenance on the
   hyperedge ([incremental-and-streaming-construction.md](incremental-and-streaming-construction.md)).
4. **Source role names from an existing vocabulary** (Wikidata properties): the largest available
   cost saving, and it makes alignment free
   ([schema-induction-and-ontology-alignment.md](schema-induction-and-ontology-alignment.md)).
5. **Report cost-per-correct-fact** with the sample size used to estimate precision. Without the
   precision estimate, a cost figure is not a cost figure.
6. **Use LLM extraction as the proposal stage only** — the machine proposes, the human judges. That
   bounds annotation cost at verdict cost, and it is the only n-ary annotation economics anyone has
   demonstrated at scale.

New questions from this note go to [../00-index/open-questions.md](../00-index/open-questions.md)
tagged `03`.

## Sources

- Linguistic Data Consortium. "ACE 2005 Multilingual Training Corpus," LDC2006T06, released 15 Feb 2006. <https://catalog.ldc.upenn.edu/LDC2006T06>
- Chia, Y. K., Bing, L., Aljunied, S. M., Si, L., Poria, S. "A Dataset for Hyper-Relational Extraction and a Cube-Filling Approach." EMNLP 2022, pp. 10114–10133; arXiv:2211.10018. <https://aclanthology.org/2022.emnlp-main.688/> ; code <https://github.com/declare-lab/HyperRED>
- Huang, R., Feng, Y., Xue, R., Ying, S., Yong, J.-H., Shi, C., Du, S., Gao, Y. "Hyper-KGGen: A Skill-Driven Knowledge Extractor for High-Quality Knowledge Hypergraph Generation" (introduces HyperDocRED). arXiv:2602.19543, 23 Feb 2026. <https://arxiv.org/abs/2602.19543>
- Pouran Ben Veyseh, A., Ebrahimi, J., Dernoncourt, F., Nguyen, T. H. "MEE: A Novel Multilingual Event Extraction Dataset." EMNLP 2022; arXiv:2211.05955. <https://arxiv.org/abs/2211.05955>
- Pouran Ben Veyseh, A., Nguyen, M. V., Dernoncourt, F., Nguyen, T. H. "MINION: a Large-Scale and Diverse Dataset for Multilingual Event Detection." NAACL 2022; arXiv:2211.05958. <https://aclanthology.org/2022.naacl-main.166/>
- Wikidata. "Help:Qualifiers." Checked 2026-09-20. <https://www.wikidata.org/wiki/Help:Qualifiers>
- Wikidata. "Wikidata:Statistics." Page last updated 31 Aug 2025; checked 2026-09-20. <https://www.wikidata.org/wiki/Wikidata:Statistics>
- Li, M., Zareian, A., Zeng, Q., Whitehead, S., Lu, D., Ji, H., Chang, S.-F. "Cross-media Structured Common Space for Multimedia Event Extraction." ACL 2020. <https://aclanthology.org/2020.acl-main.230/> ; annotation guideline V0.1 <http://blender.cs.illinois.edu/software/m2e2/ACL2020_M2E2_annotation.pdf>
- Shen, S., Li, Z., Qi, G. "Active Learning for Event Extraction with Memory-based Loss Prediction Model." arXiv:2112.03073, 26 Nov 2021. <https://arxiv.org/abs/2112.03073>
- Kholghi, M., De Vine, L., Sitbon, L., Zuccon, G., Nguyen, A. "The Benefits of Word Embeddings Features for Active Learning in Clinical Information Extraction." arXiv:1607.02810. <https://arxiv.org/abs/1607.02810>
- "A study of deep active learning methods to reduce labelling efforts in biomedical relation extraction." *PLOS ONE* 18(12): e0292356, 2023. <https://doi.org/10.1371/journal.pone.0292356>
- "Data-efficient Active Learning for Structured Prediction with Partial Annotation and Self-Training." arXiv:2305.12634. <https://arxiv.org/abs/2305.12634>
- Lenat, D., Marcus, G. "Getting from Generative AI to Trustworthy AI: What LLMs might learn from Cyc." arXiv:2308.04445, 31 Jul 2023. <https://arxiv.org/abs/2308.04445>
- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., Feng, Y., Kuang, Z., Song, M., Zhu, Y., Luu, A. T. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." arXiv:2503.21322; NeurIPS 2025. <https://arxiv.org/abs/2503.21322>
