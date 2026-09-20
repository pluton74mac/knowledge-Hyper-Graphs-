---
title: Privacy, licensing and governance of n-ary knowledge
type: comparison
status: draft
tags: [licensing, privacy, governance, provenance, datasheets, gdpr, ethics, datasets, critique, gap-filling]
created: 2026-09-20
updated: 2026-09-20
---

# Privacy, licensing and governance

The rest of section 10 asks whether knowledge hypergraphs *work*. This note asks whether you are
allowed to build one, whether you may redistribute what you built it from, and what you owe the
people who appear inside it.

Three claims, argued below:

1. **The benchmark licence chain is broken at the first link.** Freebase was CC-BY and Wikidata is
   CC0, but neither attribution nor licence is carried into the derived n-ary benchmarks, and two of
   the five carry no licence at all. One model repository is **non-commercial**.
2. **N-ary facts are a privacy amplifier, not a neutral container.** A triple says *X worked at Y*.
   A hyperedge says *X worked at Y as Z from T₁ to T₂ alongside W* — a richer quasi-identifier in a
   single record, harder to redact, and harder to delete without destroying the fact.
3. **The governance instruments exist and nobody in this field uses them.** Datasheets for Datasets
   (2018/2021) and Data Statements (2018) are eight years old; no n-ary knowledge-graph or
   hypergraph-RAG dataset surveyed in this KB ships either.

Context: the licence *gaps* are catalogued in
[../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md)
§9 and the fetch records in [../../datasets/README.md](../../datasets/README.md). This note supplies
the upstream terms, the privacy analysis and the governance recommendation those notes point to.

---

## 1. The upstream licences

| Source | Licence | Primary statement | Consequence for derivatives |
|---|---|---|---|
| **Wikidata** | **CC0 1.0** for data | "All structured data in the main, property and lexeme namespaces is made available under the Creative Commons CC0 License"; text in other namespaces is CC BY-SA 4.0 ([Wikidata:Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)) | No attribution obligation. Derivatives may be relicensed freely. This is why WD50K, WikiPeople and HyperRED's *facts* are clean. |
| **Freebase** | **CC-BY** | Data dumps "are distributed under the Creative Commons Attribution (aka CC-BY)"; contributing data grants permission "to access and use them under the terms and conditions of the CC-BY license, including attributions requirements that may apply" ([Freebase API Terms](https://developers.google.com/freebase/terms); [Data Dumps](https://developers.google.com/freebase)) | **Attribution is required.** JF17K, FB-AUTO and M-FB15K are Freebase derivatives redistributed with no attribution statement. |
| **Wikipedia text** (used by HyperRED) | **CC BY-SA 3.0 Unported** | HyperRED states: "Wikidata facts are under the public domain while Wikipedia texts are licensed under the Creative Commons Attribution-ShareAlike 3.0 Unported License. Hence, we are free to adapt the texts to construct our dataset, which will also be released under the same license" ([Chia, Bing, Aljunied, Si and Poria, EMNLP 2022](https://aclanthology.org/2022.emnlp-main.688/)) | **Share-alike propagates.** Anything derived from HyperRED's text inherits CC BY-SA. |
| **ACE 2005** | **LDC User Agreement**, fee-based | Distributed to "Subscription & Standard Members, and Non-Members" under the "LDC User Agreement for Non-Members" ([LDC2006T06](https://catalog.ldc.upenn.edu/LDC2006T06)) | Cannot be redistributed. An open pipeline cannot depend on it — the argument for MEE in [../03-construction/multimodal-and-multilingual-construction.md](../03-construction/multimodal-and-multilingual-construction.md) §5. |

**HyperRED is the model citizen.** It is the only n-ary dataset found in this KB that reasons about
its own licence chain in print, names both upstream licences, and states the licence it releases
under. Every other n-ary dataset should be held to that standard.

---

## 2. The break: derived benchmarks

Combining the audit in
[../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md)
§9 with the repository checks in
[../05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md](../05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md)
§4 (both dated 2026-09-20):

| Artefact | Upstream | Stated licence | Problem |
|---|---|---|---|
| JF17K | Freebase (CC-BY) | Apache-2.0 on the shipping repo (code) | Attribution obligation on the **data** is not discharged |
| FB-AUTO, M-FB15K | Freebase (CC-BY) | **none** — no licence file on either HypE repo | Legal default is all rights reserved; also fails CC-BY attribution |
| WikiPeople | Wikidata (CC0) | Apache-2.0 on the shipping repo | Clean upstream, licence stated on code only |
| WD50K family | Wikidata (CC0) | MIT on `migalkin/StarE` | Cleanest of the five |
| **HyNT code + data** | — | **CC BY-NC-SA 4.0** | **Non-commercial.** Any commercial use of HyNT is a breach; this is not flagged in any paper citing it |
| HINGE, ShrinkE, HyperMono repos | — | **none stated** | All rights reserved by default |
| Hypergraph-RAG corpora | clinical guidelines, domain texts | **unstated** | §3 |

Two points that deserve emphasis because they are routinely elided:

- **A repository licence is not a data licence.** "Apache-2.0" on a repo that ships JF17K governs
  the loader, not the Freebase-derived triples inside it. The field treats these as the same thing.
- **"CC-BY on a database" is a live legal question, not a settled one.** Creative Commons' own
  guidance distinguishes copyright in a database's structure from *sui generis* database rights and
  from the facts themselves; Wikidata sidesteps this with CC0. `[unverified]` No court has ruled on
  the status of JF17K-style Freebase derivatives, and this note does not offer legal advice.

---

## 3. The unarchived corpora problem

The hypergraph-RAG evaluation corpora are the worst governance case in the KB, and the facts are
already recorded in
[../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md)
§8 and [../../datasets/README.md](../../datasets/README.md):

- HyperGraphRAG's evaluation README directs users to **Terabox**; Hyper-RAG's to **Google Drive**
  and **Baidu Cloud**. No DOI, no checksum, no version.
- The HyperGraphRAG Medicine context is built from **copyrighted clinical guidelines**, redistributed
  with no stated licence.

Four distinct failures stack here, and they should be named separately because they have different
remedies:

| Failure | Remedy |
|---|---|
| **No archival copy** — consumer file-hosting links rot and are geo-restricted | Deposit with a DOI (Zenodo, Figshare) where the licence allows; otherwise publish checksums and a reconstruction script |
| **No integrity check** — you cannot tell whether you have the same bytes the paper used | Publish SHA-256 per file |
| **No licence** — redistribution of third-party copyrighted text | Do not redistribute; ship a fetch script and a manifest |
| **Circularity** — questions generated by an LLM from the same corpus the system indexes | Out of scope here; see [critical-reading-of-hypergraph-rag-claims.md](critical-reading-of-hypergraph-rag-claims.md) |

**Opinion.** A paper whose central claim is measured on a corpus distributed by a Terabox link has
not published a reproducible result, regardless of the quality of the method. The remedy is cheap
and the field's newest infrastructure shows it: **AHORN** ships, for each dataset, "a converted
dataset to its source, metadata, citation guidance, conversion code, and version history", with
revision-specific downloads and format validation ([Frantzen and Schaub,
arXiv:2608.03491](https://arxiv.org/abs/2608.03491), 4 Aug 2026). That is the standard now
available; see
[../08-history-and-frontier/reading-the-frontier-2026-q3.md](../08-history-and-frontier/reading-the-frontier-2026-q3.md)
§8.

---

## 4. Why n-ary facts raise the privacy stakes

This is the part of the argument that is specific to hypergraphs, and it has not been made
elsewhere in this KB.

**(a) A hyperedge is a richer quasi-identifier than a triple.** Re-identification risk grows with
the number of jointly held attributes. A reified encoding scatters *(person, employer, role, start,
end, colleague)* across six triples that a downstream consumer may or may not rejoin; a hyperedge
delivers the join **pre-computed**. The expressive advantage claimed throughout this KB — that a
hyperedge keeps a fact whole — is, from a privacy standpoint, exactly the risk.

**(b) Deletion is structurally harder.** GDPR Article 17 erasure of one participant from a triple
deletes the triple. Erasure of one participant from an n-ary fact leaves three bad options: delete
the whole fact (losing information about the other participants, who did not request erasure),
delete the incidence (leaving a fact whose arity no longer matches its relation signature), or
tombstone it (leaving a record that the person was there). No published knowledge-hypergraph system
implements any of them. The closest machinery in the literature is TOKI's bitemporal operator
algebra, which preserves "the losing fact in an audit row" ([Wang,
arXiv:2606.06240](https://arxiv.org/abs/2606.06240), 4 Jun 2026) — which is *the opposite* of
erasure, and useful precisely because it makes the tension explicit.

**(c) Unlearning research has not reached hyperedges.** KG unlearning exists — "KG unlearning is
nontrivial due to the distinctive structure of KG and the semantic relations between entities"
([Xiao, Ye, Liu, Ma and Hui, arXiv:2508.14013](https://arxiv.org/abs/2508.14013), 19 Aug 2025) —
but is defined over triples. `[unverified]` No hypergraph or n-ary equivalent was found on
2026-09-20.

**(d) The benchmarks are populated by real people.** **WikiPeople** is, by construction, a benchmark
of facts about named individuals drawn from Wikidata; JF17K and WD50K carry biographical facts
heavily. Every published MRR in
[../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md)
is a score for predicting missing attributes of real people. The field does not discuss this.

**(e) Link prediction on people *is* inference of undisclosed attributes.** The task definition —
"predict missing elements in facts" — is, applied to a person-centred hyperedge, attribute
inference. That is a recognised privacy harm even when every training fact is public.

---

## 5. What Wikidata already does, and what it shows

Wikidata is the only system at scale with a *governance* answer for facts about people, and it is
worth reading as prior art:

- Facts about living people require sourcing: "Statements that can reasonably be expected to be
  challenged should be supported by a reliable source."
- Privacy limits inclusion: information about living individuals should generally not be included
  unless it is widespread public knowledge or provided by the person themselves; non-notable
  individuals may be deleted entirely.
- There is a **removal mechanism with escalating opacity**: administrators may use revision deletion
  to hide non-public-interest material, and *oversighters* can make it inaccessible even to
  administrators.
- The burden of proof falls on the editor who adds or restores disputed material, and the policy
  covers anyone born within the past 115 years unless reliable sources confirm their death, with
  protections extending past death in sensitive cases.

([Wikidata, *Wikidata:Living people*](https://www.wikidata.org/wiki/Wikidata:Living_people), checked
2026-09-20.)

Three lessons transfer directly. **Sourcing is the enabling mechanism** — you cannot review a
contested fact you cannot trace, which is why provenance is load-bearing (finding 4 of
[../03-construction/README.md](../03-construction/README.md)). **Suppression must be distinguishable
from deletion**, with different visibility tiers. And **notability is a governance lever**: the
cheapest privacy control is not collecting the fact.

Note the asymmetry: Wikidata's licence is CC0, which grants *reusers* every freedom, while its
*policy* restricts what may be stored. Anyone rebuilding a Wikidata-derived n-ary dataset inherits
the freedom and not the policy. That is the licensing-versus-governance gap in one sentence.

---

## 6. Provenance obligations

Three obligations arrive from three different directions and point at the same field:

1. **Legal.** CC-BY requires attribution, which requires knowing the source of each fact.
2. **Scientific.** Reproducibility requires knowing which document, version and extraction run
   produced a hyperedge.
3. **Ethical.** Erasure, correction and contest all require tracing a fact to its origin.

The KB already concludes that "provenance is the load-bearing field" on engineering grounds
([../03-construction/README.md](../03-construction/README.md) finding 4). This note adds that it is
load-bearing on legal and ethical grounds too — and that the obligation attaches to the **incidence**,
not only to the hyperedge, because different participants of one n-ary fact routinely come from
different sources. The serialisation question is treated in
[../04-storage-and-formats/versioning-provenance-and-scale.md](../04-storage-and-formats/versioning-provenance-and-scale.md);
W3C **PROV-O** is the vocabulary of record.

---

## 7. Governance frameworks worth adopting

| Framework | Origin | What it asks for | Fit for a KHG |
|---|---|---|---|
| **Datasheets for Datasets** | [Gebru, Morgenstern, Vecchione, Wortman Vaughan, Wallach, Daumé III, Crawford, *CACM* 64(12), Dec 2021; arXiv:1803.09010](https://doi.org/10.1145/3458723) | Motivation, composition, collection process, recommended uses, distribution, maintenance — "by analogy [to] the electronics industry […] every dataset be accompanied with a datasheet" | **Strong.** The composition and collection-process sections are exactly where arity distribution, role vocabulary and extraction method belong |
| **Data Statements for NLP** | [Bender and Friedman, *TACL* 6:587–604, 2018](https://aclanthology.org/Q18-1041/) | Curation rationale, language variety, speaker and annotator demographics, speech situation, provenance appendix | **Strong for extracted KHGs**, weak for KG-derived ones; the annotator-demographics section is the missing piece in every instrument in [../03-construction/human-in-the-loop-annotation-and-cost.md](../03-construction/human-in-the-loop-annotation-and-cost.md) |
| **AHORN-style repository record** | [Frantzen and Schaub, arXiv:2608.03491](https://arxiv.org/abs/2608.03491), 4 Aug 2026 | Source link, metadata, citation guidance, conversion code, version history, revision-specific download, format validation | **Strong and hypergraph-native.** The only one of the three built for higher-order data |
| **HIF** | [Coll, Joslyn, Landry et al., *Network Science* 13:e21, 2025](https://doi.org/10.1017/nws.2025.10018) | A file format, not a governance framework — but the carrier for per-incidence attributes | Complementary; see [../04-storage-and-formats/hif-hypergraph-interchange-format.md](../04-storage-and-formats/hif-hypergraph-interchange-format.md) |

---

## 8. What this knowledge base should adopt

Concrete, in priority order.

1. **A ten-field dataset record** in [../../datasets/README.md](../../datasets/README.md) for every
   dataset: upstream source, upstream licence, redistribution licence, attribution text (if CC-BY),
   retrieval date, SHA-256, arity distribution, whether it contains facts about identifiable living
   people, extraction method, and contact for takedown. Five of these already exist there; the last
   five do not.
2. **Treat a missing licence as a blocker.** Already recommendation 7 of
   [../09-ecosystem/dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md);
   this note extends it to **non-commercial** licences, which are not blockers but must be flagged
   at the point of use (HyNT, §2).
3. **Discharge the Freebase attribution.** Any note or artefact here using JF17K, FB-AUTO or
   M-FB15K should carry an explicit "derived from Freebase, CC-BY" line. This is a one-line fix for
   a real obligation.
4. **Never redistribute a RAG corpus.** Ship a fetch script, a manifest and a hash; mirror only what
   the licence permits.
5. **Write a datasheet for anything this repository constructs**, using Gebru et al.'s sections plus
   two hypergraph-specific ones: *arity distribution* and *role vocabulary provenance*.
6. **Record a personal-data flag per dataset**, and do not build person-centred n-ary demonstrations
   from WikiPeople without saying so.
7. **Make provenance per-incidence** in any schema this repository publishes (§6), and keep a
   suppression tier distinct from deletion (§5).

---

## 9. Open problems

1. **What is the correct erasure semantics for an n-ary fact?** (§4b.) Nobody has defined one.
2. **Is a hyperedge measurably more re-identifying than its reification?** The experiment — k-anonymity
   or attribute-inference attack on the same facts in both encodings — has not been run.
3. **Does hypergraph unlearning differ from KG unlearning?** Open by construction (§4c).
4. **Can CC-BY attribution be discharged mechanically** at hyperedge granularity, given per-incidence
   provenance?
5. **Would an AHORN record satisfy the reproducibility requirements** this KB sets for the RAG
   corpora, or does it need a licence field it does not have? Worth checking directly.

Questions raised here belong in [../00-index/open-questions.md](../00-index/open-questions.md)
tagged `10`.

## Sources

- Wikidata. "Wikidata:Licensing." Checked 2026-09-20. <https://www.wikidata.org/wiki/Wikidata:Licensing>
- Wikidata. "Wikidata:Living people." Checked 2026-09-20. <https://www.wikidata.org/wiki/Wikidata:Living_people>
- Google. "Freebase API Terms and Conditions" and "Data Dumps," Freebase API (deprecated). Checked 2026-09-20. <https://developers.google.com/freebase/terms> ; <https://developers.google.com/freebase>
- Creative Commons. "Data and CC licenses" (wiki page on databases, sui generis database rights and CC licences). Checked 2026-09-20. <https://wiki.creativecommons.org/wiki/Data_and_CC_licenses>
- Linguistic Data Consortium. "ACE 2005 Multilingual Training Corpus," LDC2006T06; LDC User Agreement for Non-Members. Checked 2026-09-20. <https://catalog.ldc.upenn.edu/LDC2006T06>
- Chia, Y. K., Bing, L., Aljunied, S. M., Si, L., Poria, S. "A Dataset for Hyper-Relational Extraction and a Cube-Filling Approach." EMNLP 2022 (licence and ethics statements, §3 and Ethics). <https://aclanthology.org/2022.emnlp-main.688/>
- Gebru, T., Morgenstern, J., Vecchione, B., Wortman Vaughan, J., Wallach, H., Daumé III, H., Crawford, K. "Datasheets for Datasets." *Communications of the ACM* 64(12), Dec 2021; arXiv:1803.09010 (23 Mar 2018). <https://doi.org/10.1145/3458723> ; <https://arxiv.org/abs/1803.09010>
- Bender, E. M., Friedman, B. "Data Statements for Natural Language Processing: Toward Mitigating System Bias and Enabling Better Science." *TACL* 6:587–604, 2018. <https://aclanthology.org/Q18-1041/>
- Frantzen, F., Schaub, M. T. "A repository for discovery and reuse of higher-order network datasets" (AHORN). arXiv:2608.03491, 4 Aug 2026. <https://arxiv.org/abs/2608.03491>
- Wang, Z. "TOKI: A Bitemporal Operator Algebra for Contradiction Resolution in LLM-Agent Persistent Memory." arXiv:2606.06240, 4 Jun 2026. <https://arxiv.org/abs/2606.06240>
- Xiao, Y., Ye, R., Liu, B., Ma, X., Hui, B. "Efficient Knowledge Graph Unlearning with Zeroth-order Information." arXiv:2508.14013, 19 Aug 2025. <https://arxiv.org/abs/2508.14013>
- European Data Protection Board. "Effective implementation of data subjects' rights" (support-pool expert paper on rectification and erasure in AI systems), 2025. <https://www.edpb.europa.eu/system/files/2025-01/d2-ai-effective-implementation-of-data-subjects-rights_en.pdf>
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. "HIF: The hypergraph interchange format for higher-order networks." *Network Science* 13:e21, 2025. <https://doi.org/10.1017/nws.2025.10018>
- GitHub repository licence metadata for `ServiceNow/HypE`, `baharefatemi/HypE`, `bdi-lab/HyNT`, `eXascaleInfolab/HINGE_code`, `xiongbo010/ShrinkE`, `migalkin/StarE`, `liuyuaa/GETD`, `PaddlePaddle/Research`, retrieved 2026-09-20.
