---
title: Scientific knowledge and scholarly graphs
type: survey
status: draft
tags: [hypergraph, n-ary, scholarly, co-authorship, ORKG, SciREX, materials-science, higher-order-link-prediction]
created: 2026-09-20
updated: 2026-09-20
---

# Scientific knowledge and scholarly graphs

Science produces two kinds of higher-order structure: the *social* structure of who worked with whom on
what (co-authorship, citation, collaboration), and the *epistemic* structure of what a paper actually
claims (a method achieving a score on a metric for a task on a material). Both are n-ary; the literature
treats them almost entirely separately.

## 1. Co-authorship and collaboration as hyperedges

A paper with five authors is one hyperedge over five people, not ten pairwise edges. The canonical
study is [Benson, Abebe, Schaub, Jadbabaie and Kleinberg, 2018](https://www.pnas.org/doi/10.1073/pnas.1800683115)
(*PNAS* 115(48):E11221–E11230), which analyses **19 datasets** from biology, medicine, social networks
and the web, characterises how higher-order structure emerges, and proposes *higher-order link
prediction* — predicting which groups will appear as a simplex in the future — as the evaluation task
for higher-order models. Their **simplicial closure** framing asks how open triangles (and larger open
groups) close into full simplices over time, and they show the closure rates differ systematically
across domains. Data and code are published alongside
([Benson data page](https://www.cs.cornell.edu/~arb/)).

Why this is a strong case: the ground truth is unambiguous (a paper either has those five authors or it
does not), the prediction task is well-posed, and the pairwise baseline is a genuine competitor rather
than a straw man. It is the closest thing this KB has found to a *clean* higher-order benchmark.

Why it is limited for knowledge hypergraphs: a co-authorship hyperedge has no roles and no direction;
it is sense **B**. It tells us that group structure is predictable, not that role-labelled n-ary facts
are.

## 2. Scholarly claims as n-ary facts

**ORKG** (Open Research Knowledge Graph) is the largest attempt to represent *contributions* rather than
metadata: each paper contributes a structured description of research problem, materials, methods and
results, curated through expert crowdsourcing and exposed as machine-actionable **comparisons** across
papers in a domain ([ORKG](https://orkg.org/); NFDI4ING [overview](https://nfdi4ing.de/orkg/)). ORKG is
built on RDF, so a contribution with four dimensions is represented by reification — a contribution
resource with several properties — which is Pattern 1 of the W3C n-ary note, not a native hyperedge
(see [n-ary-relations-and-reification](../02-knowledge-representation/n-ary-relations-and-reification.md)).
A comparison table in ORKG is, structurally, an n-ary relation displayed as a matrix.

**SciERC** ([Luan, He, Ostendorf, Hajishirzi, 2018](https://nlp.cs.washington.edu/sciIE/), EMNLP 2018)
is the standard scientific IE dataset: 500 annotated abstracts for entity, relation and coreference
extraction, extended to a knowledge graph over roughly 110,000 abstracts from 12 AI conferences. Its
relations are **binary**. This is worth stating because SciERC is frequently cited in hypergraph papers
as motivation; it is in fact evidence that the mainstream scientific-IE pipeline is pairwise.

The n-ary counterpart is **SciREX** ([Jain, van Zuylen, Hajishirzi, Beltagy, 2020](https://arxiv.org/abs/2005.00512),
ACL 2020), which annotates document-level n-ary relations over *Method, Metric, Task, Material* and
*Score* ([repo](https://github.com/allenai/SciREX)). Two honest caveats from the repository itself:
about 50 % of annotated relations contain at least one entity with no textual mention because it appears
only in a table, and the authors remove such relations at evaluation time, which they note artificially
affects precision. Document-level n-ary scientific extraction remains hard: the 2026 knowledge-hypergraph
extraction benchmark **HyperDocRED** reports leading extractors at 0.38 precision / 0.11 recall for one
system and 0.80 / 0.43 for the best ([Huang et al., 2026](https://arxiv.org/abs/2602.19543)).

## 3. Concept hypergraphs for discovery

The most concrete recent work is [Stewart and Buehler, 2026](https://arxiv.org/abs/2601.04878), which
builds a hypergraph knowledge representation over roughly 1,100 biocomposite-scaffold manuscripts,
yielding **161,172 nodes and 320,201 hyperedges** with a scale-free topology organised around highly
connected conceptual hubs. Agents equipped with hypergraph traversal tools using node-intersection
constraints bridge semantically distant concepts — their worked example links cerium oxide and PCL
scaffolds through chitosan intermediates — and the authors argue the hypergraph prevents the
combinatorial explosion that pairwise expansion would produce, with the topology itself acting as a
verification signal in a "teacherless" agentic loop. Related code is published as
[lamm-mit/HyperGraphReasoning](https://github.com/lamm-mit/HyperGraphReasoning).

The same group's pairwise-graph predecessors are worth reading as the baseline this is arguing against:
generative knowledge extraction with multimodal graph reasoning
([Buehler, 2024](https://iopscience.iop.org/article/10.1088/2632-2153/ad7228), *Machine Learning:
Science and Technology*) and in-situ graph reasoning with Graph-PRefLexOR
([Buehler, 2025](https://advanced.onlinelibrary.wiley.com/doi/abs/10.1002/aidi.202500006)).

A parallel line predicts research directions from *concept graphs* rather than hypergraphs
([Predicting New Research Directions in Materials Science using Large Language Models and Concept
Graphs, 2025](https://arxiv.org/pdf/2506.16824)), and agentic cross-domain materials design over KGs
appears in [GraphAgents, 2026](https://arxiv.org/html/2602.07491v1). Neither is evaluated against the
hypergraph variant, so the comparative question — does the hyperedge buy anything for discovery beyond
better bookkeeping? — is open.

**Assessment.** The discovery claims in this area are, as of 2026, demonstrations rather than
evaluations: a hypergraph is built, an agent traverses it, and a plausible hypothesis comes out. There
is no held-out benchmark of *correct* novel hypotheses, and no ablation against a pairwise graph built
from the same corpus. That does not make the work uninteresting — the topology statistics are real
measurements — but the causal claim is unproven.

## 4. Materials science data

Materials data has its own n-ary shape: a *processing–structure–property–performance* record is a
four-or-more-way fact, and a synthesis recipe is a directed transformation with a set of precursors, so
the chemistry formalism in [chemistry-and-reaction-networks](chemistry-and-reaction-networks.md) applies
directly. [unverified: this research run did not find a widely adopted materials database that stores
these records as native hyperedges rather than as records in a relational or document schema]

## Sources

- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. *Simplicial closure and higher-order link prediction.* PNAS 115(48):E11221–E11230, 2018. https://www.pnas.org/doi/10.1073/pnas.1800683115
- Benson, A. R. Data and code page, Cornell University, checked 2026-09-20. https://www.cs.cornell.edu/~arb/
- Open Research Knowledge Graph (ORKG), checked 2026-09-20. https://orkg.org/
- NFDI4ING. *ORKG* overview page, checked 2026-09-20. https://nfdi4ing.de/orkg/
- Luan, Y., He, L., Ostendorf, M., Hajishirzi, H. *Multi-Task Identification of Entities, Relations, and Coreference for Scientific Knowledge Graph Construction* (SciERC). EMNLP 2018; project page checked 2026-09-20. https://nlp.cs.washington.edu/sciIE/
- Jain, S., van Zuylen, M., Hajishirzi, H., Beltagy, I. *SciREX: A Challenge Dataset for Document-Level Information Extraction.* ACL 2020; arXiv:2005.00512. https://arxiv.org/abs/2005.00512
- AllenAI. *SciREX* repository, GitHub, checked 2026-09-20. https://github.com/allenai/SciREX
- Huang, R. et al. *Hyper-KGGen: A Skill-Driven Knowledge Extractor for High-Quality Knowledge Hypergraph Generation.* arXiv:2602.19543, 2026. https://arxiv.org/abs/2602.19543
- Stewart, I. A., Buehler, M. J. *Higher-Order Knowledge Representations for Agentic Scientific Reasoning.* arXiv:2601.04878, 8 Jan 2026. https://arxiv.org/abs/2601.04878
- LAMM-MIT. *HyperGraphReasoning* repository, GitHub, checked 2026-09-20. https://github.com/lamm-mit/HyperGraphReasoning
- Buehler, M. J. *Accelerating scientific discovery with generative knowledge extraction, graph-based representation, and multimodal intelligent graph reasoning.* Machine Learning: Science and Technology, 2024. https://iopscience.iop.org/article/10.1088/2632-2153/ad7228
- Buehler, M. J. *In Situ Graph Reasoning and Knowledge Expansion Using Graph-PRefLexOR.* Advanced Intelligent Discovery, 2025. https://advanced.onlinelibrary.wiley.com/doi/abs/10.1002/aidi.202500006
- *Predicting New Research Directions in Materials Science using Large Language Models and Concept Graphs.* arXiv:2506.16824, 2025. https://arxiv.org/pdf/2506.16824
- *GraphAgents: Knowledge Graph–Guided Agentic AI for Cross-Domain Materials Design.* arXiv:2602.07491, 2026. https://arxiv.org/html/2602.07491v1
