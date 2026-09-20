---
title: Cybersecurity and IT operations
type: survey
status: draft
tags: [hypergraph, directed-hypergraph, security, attack-graph, STIX, threat-intelligence, provenance, CMDB]
created: 2026-09-20
updated: 2026-09-20
---

# Cybersecurity and IT operations

Security modelling has used directed hypergraphs since long before the term "knowledge hypergraph"
existed, because the central object — an *exploit* — is a rule with a set of preconditions and a set of
postconditions. That is a directed hyperedge in the sense of
[Gallo, Longo, Pallottino and Nguyen, 1993](https://doi.org/10.1016/0166-218X(93)90045-P). What is new
since roughly 2024 is the use of hypergraphs for *knowledge* about attacks — threat intelligence,
technique taxonomies, and provenance — rather than for reachability computation.

## 1. Attack graphs are directed hypergraphs

An attack graph consists of privilege nodes, exploit/action nodes and fact nodes: a privilege node is
access or information the attacker holds, an exploit node is an action requiring a vulnerability. The
standard construction is deliberately bipartite so that an exploit's several preconditions all feed one
action node — which is precisely the bipartite incidence encoding of a directed hyperedge, described in
[hypergraph-definitions](../01-foundations/hypergraph-definitions.md).

The AND semantics is the whole point: an exploit fires only when *every* precondition holds. Treat the
attack graph as an ordinary directed graph and reachability becomes OR-reachability, which
systematically over-estimates what an attacker can do — the same failure mode that
[Franzese et al., 2019](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1007384)
quantify for biological pathways (see [biomedical-and-life-sciences](biomedical-and-life-sciences.md)).
Recognising attack-graph analysis as hyperpath finding rather than path finding is the single most
useful cross-domain transfer in this note.

Explicit hypergraph framings include *Attack Hypergraph: A Framework for Modeling Multi-stage Attacks*
([Springer, 2024](https://link.springer.com/chapter/10.1007/978-3-031-75157-8_2)) and
hypergraph-driven mitigation of cyber-attacks ([2018](https://www.researchgate.net/publication/323697624_Hypergraph-driven_Mitigation_of_Cyber-Attacks)).
The motivating argument in these works is that multi-phase attacks have high-order interactions,
concurrency and unpredictable timing that a directed graph cannot express; kill-chain stages become
nodes and hyperedges group them logically and temporally.

## 2. Threat intelligence: HAG

**Hyper Attack Graph (HAG)** ([*Hyper attack graph*, 2024](https://www.sciencedirect.com/science/article/abs/pii/S0167404824004991),
*Computers & Security* 149:104194, [DOI](https://dl.acm.org/doi/10.1016/j.cose.2024.104194)) is
described by its authors as the first application of hypergraph data structures to cyber threat
intelligence analysis. It uses a joint extraction model with a multi-head selection mechanism to pull
*multiple* relations among security entities out of a report at once, then displays tactics and
techniques as a hypergraph. Evaluated on **685 real-world CTI reports**, it reports an **11.12 %
increase in F1 for security-entity extraction and 6.71 % for relation extraction** over prior methods.

This is one of the few security results in this KB where the hypergraph is used for *knowledge
representation* rather than reachability, and where the gain is measured against extraction baselines
rather than by LLM judgement. Related work includes hypergraph-based adversary threat intelligence
analysis ([Springer, 2025](https://link.springer.com/chapter/10.1007/978-3-031-94855-8_17)) and
multi-source aggregation into attack-technique knowledge graphs
([MultiKG, 2024](https://arxiv.org/pdf/2411.08359)).

## 3. STIX: a standard with one genuine n-ary relationship

STIX 2.1 ([OASIS, Committee Specification 01, 20 March 2020](https://docs.oasis-open.org/cti/stix/v2.1/cs01/stix-v2.1-cs01.html))
states its model plainly: "STIX is a connected graph of nodes and edges. STIX Domain Objects and STIX
Cyber-observable Objects define the graph nodes and STIX relationships ... define the edges." The
generic `relationship` SRO is binary.

The exception is worth knowing. **Sighting** is a separate SRO precisely because it carries properties
the generic relationship cannot, including `count`, and it references three groups of objects:

- `sighting_of_ref` — what was seen,
- `observed_data_refs` — the supporting observed data,
- `where_sighted_refs` — the identities or locations where it was seen.

A Sighting therefore connects more than two objects in one record: it is an n-ary fact with named roles
living inside an otherwise binary standard. That makes it the security world's analogue of a Wikidata
qualified statement (see
[wikidata-and-freebase-data-models](../02-knowledge-representation/wikidata-and-freebase-data-models.md)),
and a natural anchor point for anyone mapping CTI into a knowledge hypergraph.

## 4. Provenance graphs

System-level provenance graphs — processes, files and sockets as nodes, causal events (fork, read,
write) as edges — are the substrate of modern intrusion detection and investigation
([Zipperle et al., 2020, survey](https://arxiv.org/pdf/2006.01722);
[Kairos, 2023](https://arxiv.org/pdf/2308.05034);
[PROGQL, 2025](https://arxiv.org/pdf/2510.22400)). The dominant practical problem is scale: audit logs
produce enormous graphs, driving compression work such as CSCProv
([Cybersecurity, 2026](https://link.springer.com/article/10.1186/s42400-026-00648-6)).

Hypergraph approaches here group behaviour rather than represent facts: anomaly detection selects seed
nodes, overlapping behavioural communities are discovered by node aggregation, and each community is
encoded as a hyperedge to capture high-order interaction for APT detection. [unverified: this research
run did not confirm a specific citation, venue and results for a hypergraph-attention APT detector; the
description above summarises search-result text rather than a paper read directly]

The structural observation that *is* safe: a provenance event with multiple inputs and outputs (a
process reading several files and writing several others in one syscall group) is a directed hyperedge,
and provenance compression is, formally, hypergraph summarisation.

## 5. IT operations and CMDBs

Configuration management databases model services, hosts, containers, network segments and their
dependencies. The recurring modelling pain is identical to the attack-graph one: "service A is available
*iff* replicas on hosts B, C and D are healthy *and* the dependency on datastore E holds" is an AND over
a set, i.e. a directed hyperedge, and impact analysis over a binary dependency graph over-estimates blast
radius for the same reason OR-reachability over-estimates attacker reach. Deployment and build systems
have the same shape — see [software-engineering-and-code-knowledge](software-engineering-and-code-knowledge.md),
where dependency resolution has an explicit hypergraph formalisation.
[unverified: this research run found no published CMDB or observability product that exposes an n-ary
dependency primitive; the claim above is a structural argument, not a report of practice]

## 6. Assessment

- **Established:** attack graphs are directed hypergraphs; the AND semantics is load-bearing; the
  bipartite encoding is already standard practice even where the word is not used.
- **Demonstrated once, credibly:** hypergraph representation of CTI improves entity and relation
  extraction (HAG, 685 reports).
- **Structural but unevidenced here:** CMDB/IT dependency modelling, provenance-as-hypergraph at scale.
- **Standards gap:** STIX is binary except for Sighting; anyone wanting n-ary CTI facts must extend it
  or reify, with the trade-offs in
  [n-ary-relations-and-reification](../02-knowledge-representation/n-ary-relations-and-reification.md).

## Sources

- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. *Directed hypergraphs and applications.* Discrete Applied Mathematics 42(2–3):177–201, 1993. https://doi.org/10.1016/0166-218X(93)90045-P
- *Attack Hypergraph: A Framework for Modeling Multi-stage Attacks.* Springer, 2024. https://link.springer.com/chapter/10.1007/978-3-031-75157-8_2
- *Hypergraph-driven Mitigation of Cyber-Attacks*, 2018. https://www.researchgate.net/publication/323697624_Hypergraph-driven_Mitigation_of_Cyber-Attacks
- *Hyper attack graph: Constructing a hypergraph for cyber threat intelligence analysis.* Computers & Security 149:104194, 2024. [author initials not verified in this run] https://www.sciencedirect.com/science/article/abs/pii/S0167404824004991
- *Hyper attack graph* (ACM DL record). https://dl.acm.org/doi/10.1016/j.cose.2024.104194
- *Hypergraph-Based Model for Adversary Threat Intelligence Analysis.* Springer, 2025. https://link.springer.com/chapter/10.1007/978-3-031-94855-8_17
- *MultiKG: Multi-Source Threat Intelligence Aggregation for High-Quality Knowledge Graph Representation of Attack Techniques.* arXiv:2411.08359, 2024. https://arxiv.org/pdf/2411.08359
- OASIS. *STIX Version 2.1*, Committee Specification 01, 20 March 2020. https://docs.oasis-open.org/cti/stix/v2.1/cs01/stix-v2.1-cs01.html
- *Threat Detection and Investigation with System-level Provenance Graphs: A Survey.* arXiv:2006.01722, 2020. https://arxiv.org/pdf/2006.01722
- *Kairos: Practical Intrusion Detection and Investigation using Whole-system Provenance.* arXiv:2308.05034, 2023. https://arxiv.org/pdf/2308.05034
- *PROGQL: A Provenance Graph Query System for Cyber Attack Investigation.* arXiv:2510.22400, 2025. https://arxiv.org/pdf/2510.22400
- *CSCProv: causal-semantic consistent provenance graph compression for attack detection.* Cybersecurity, 2026. https://link.springer.com/article/10.1186/s42400-026-00648-6
- Franzese, N., Groce, A., Murali, T. M., Ritz, A. *Hypergraph-based connectivity measures for signaling pathway topologies.* PLoS Computational Biology 15(10):e1007384, 2019. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1007384
