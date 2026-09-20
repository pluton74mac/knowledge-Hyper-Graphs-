---
title: Awesome lists, GitHub topics and communities
type: survey
status: draft
tags: [ecosystem, community, awesome-list, github-topics, working-group, workshops]
created: 2026-09-20
updated: 2026-09-20
---

# Awesome lists, GitHub topics and communities

Where the people are. Everything below was **checked on 2026-09-20**; claims that could not be
confirmed from a primary page are marked `[unverified]` rather than dropped, because the absence
of a channel is itself information.

---

## 1. The size of the field, measured

GitHub topic counts (repository search API, 2026-09-20):

| Topic | Public repositories |
|---|---|
| `knowledge-graph` | 8,906 |
| `hypergraph` | 194 |
| `hypergraph-neural-networks` | 35 |
| `higher-order-networks` | 13 |

Knowledge-graph repositories outnumber hypergraph repositories by roughly **46 : 1**. Any plan
that assumes a ready-made hypergraph ecosystem should be re-read with that ratio in mind. The
equivalent ratio for research output is not measured here `[unverified]`.

---

## 2. Curated "awesome" lists

| List | Scope | Stars | Last commit | Licence | URL |
|---|---|---|---|---|---|
| **Awesome-Hypergraph-Network** | hypergraph learning, theory, datasets and tools; the most complete of the three | 337 | 2025-02-03 | none declared | [gzcsudo/Awesome-Hypergraph-Network](https://github.com/gzcsudo/Awesome-Hypergraph-Network) |
| **awesome-hypergraph-learning** | frameworks, libraries and software only | 25 | 2023-10-06 | CC0-1.0 | [giuliacassara/awesome-hypergraph-learning](https://github.com/giuliacassara/awesome-hypergraph-learning) |
| **Awesome-Hypergraph-Learning** | papers on hypergraphs and related ideas | 20 | — | none declared | [LeslieHoloway/Awesome-Hypergraph-Learning](https://github.com/LeslieHoloway/Awesome-Hypergraph-Learning) |

**All three are stale.** The most active has not been updated since February 2025; the second
since October 2023. None of them covers n-ary knowledge graphs, HIF, or the 2025–2026
hypergraph-RAG literature.

**No "awesome" list for n-ary / hyper-relational knowledge graphs was found.** A GitHub search
for `awesome n-ary knowledge graph in:name,description` returned **0 results** (2026-09-20).
This is a concrete, low-cost gap that this knowledge base could fill — see
[README.md](README.md) for how the section is organised.

---

## 3. Library communities

| Project | Channels verified 2026-09-20 | Notes |
|---|---|---|
| **XGI** | GitHub Discussions enabled on the repository; mailing-list sign-up linked from the docs home page (`http://eepurl.com/igE6ez`); social account `@xginets`; the repository's `SUPPORT.md` credits **Zulip** as an infrastructure sponsor | The most deliberately community-run of the hypergraph libraries: contributor guide, code of conduct, JOSS paper, and a Zenodo community for its datasets |
| **HyperNetX** | GitHub Discussions enabled; issue tracker; documentation at `hypernetx.readthedocs.io` | Maintained at Pacific Northwest National Laboratory |
| **Hypergraphx (HGX)** | GitHub Discussions enabled; project site `hgx-team.github.io/hypergraphx`; dataset site `hgx-team.github.io/hypergraphx-data` | |
| **DHG / DeepHypergraph** | GitHub Discussions enabled; site `deephypergraph.com` | Tsinghua iMoonLab |
| **TypeDB** | `[unverified]` — `https://typedb.com/community` returned HTTP 404 when checked; the project historically ran a Discord and a forum | Repository issues are active (309 open) |
| **OpenCog / AtomSpace** | GitHub Discussions enabled on `opencog/atomspace`; the OpenCog wiki hosts the long-running documentation | `[unverified]` mailing-list status |
| **Hyperon / MeTTa** | documentation and language site `metta-lang.dev` | `[unverified]` chat channels |
| **RDF / SPARQL stack** (rdflib, Jena, RDF4J, Oxigraph) | GitHub Discussions enabled on all four; Apache Jena also runs `users@jena.apache.org` and `dev@jena.apache.org` mailing lists `[unverified]` exact addresses | The oldest and best-established communities in this list |

---

## 4. The HIF working group

HIF is the one genuinely cross-project body in the hypergraph world. It is not a formal
standards organisation but an eight-person author group drawn from several institutions
(Pacific Northwest National Laboratory, University of Virginia, University of Michigan, SGH
Warsaw School of Economics and others), who published the format in *Network Science*:
Martín Coll, Cliff A. Joslyn, Nicholas W. Landry, Quintino Francesco Lotito, Audun Myers,
Joshua Pickard, Brenda Praggastis and Przemysław Szufel
([Coll et al., 2025](https://doi.org/10.1017/nws.2025.10018)).

- Home: [HIF-org/HIF-standard](https://github.com/HIF-org/HIF-standard) (MIT, 36 stars, last
  commit 2026-03-19, 7 open issues).
- Governance is by GitHub issue and pull request against the schema; the schema `CHANGELOG.md`
  lists a single version, `v0.0`.
- Five libraries implement it (HypergraphX, HyperNetX, HAT, SimpleHypergraphs.jl, XGI) — the
  same set of projects whose maintainers wrote the paper.

**Analysis.** HIF's strength is that its authors are the maintainers of the implementations, so
adoption was immediate. Its weakness is the same fact: the working group has no members from the
knowledge-representation, database or LLM communities, which is visible in the format — it has
no notion of a relation type, a role, or a schema. See
[standards-bodies-and-specifications.md](standards-bodies-and-specifications.md).

---

## 5. Venues and workshop series

**Verified (2026-09-20):**

- **Dagstuhl Seminar 26411, "Large Language Models Meet Knowledge Graphs"**, 4–9 October 2026,
  organised by Angela Bonifati, Jan-Christoph Kalo, Jeff Z. Pan, Simon Razniewski and Luke
  Zettlemoyer (<https://www.dagstuhl.de/en/seminars/seminar-calendar>).
- **No Dagstuhl seminar on hypergraphs or higher-order networks** is listed in the current
  seminar calendar.
- **Zenodo XGI community** — the archival home of XGI-DATA:
  <https://zenodo.org/communities/xgi>.
- **Graph Data Council** (formerly the Linked Data Benchmark Council, renamed in 2025) — the
  body behind the graph benchmarks and the LEX (Extended GQL Schema) working group:
  <https://ldbcouncil.org/>.

**Where the work actually appears**, judged from the venues of the papers cited across this
section: NeurIPS, ICLR, KDD, WWW, EMNLP/ACL and IJCAI for the learning and knowledge side;
*Physics Reports*, *Nature Physics*, *Nature Communications*, *SIAM Review*, *PNAS*, *Journal of
Complex Networks* and *Network Science* for the higher-order-networks side; IEEE VIS for the
drawing side.

**`[unverified]`** — frequently referenced but not confirmed against a programme in this run, and
therefore not listed as fact: the "Higher-Order Networks" satellite sessions at NetSci and
Conference on Complex Systems; hypergraph or n-ary KG workshops co-located with ISWC, KDD or
NeurIPS; the Topological Deep Learning challenge series associated with TopoX.

---

## 6. Practical advice for keeping up

1. **Watch the five HIF-implementing repositories**, not the awesome lists. The lists are stale;
   the repositories are not.
2. **Follow releases, not stars.** The PyPI release feeds for `xgi`, `hypernetx`, `hypergraphx`
   and `dhg` are a better signal than any curated list.
3. **Subscribe to the arXiv listings** `cs.SI` + `physics.soc-ph` for higher-order networks and
   `cs.AI` + `cs.CL` for n-ary knowledge graphs; the two surveys in
   [books-surveys-and-courses.md](books-surveys-and-courses.md) are the current entry points.
4. **Track the W3C RDF & SPARQL Working Group publication page** for RDF 1.2 — the timeline is in
   [standards-bodies-and-specifications.md](standards-bodies-and-specifications.md).

---

## Sources

- GitHub repository search API, queried 2026-09-20, for topic counts (`topic:hypergraph`, `topic:higher-order-networks`, `topic:hypergraph-neural-networks`, `topic:knowledge-graph`), for the absence of an n-ary "awesome" list, and for stars/last-commit/licence of each repository linked above.
- gzcsudo. *Awesome-Hypergraph-Network.* <https://github.com/gzcsudo/Awesome-Hypergraph-Network>, checked 2026-09-20.
- Cassarà, G. *awesome-hypergraph-learning.* <https://github.com/giuliacassara/awesome-hypergraph-learning>, checked 2026-09-20.
- LeslieHoloway. *Awesome-Hypergraph-Learning.* <https://github.com/LeslieHoloway/Awesome-Hypergraph-Learning>, checked 2026-09-20.
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. (2025). *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21. <https://doi.org/10.1017/nws.2025.10018>
- HIF-standard repository README and `schemas/CHANGELOG.md`. <https://github.com/HIF-org/HIF-standard>, checked 2026-09-20.
- XGI documentation home page and `SUPPORT.md`. <https://xgi.readthedocs.io/en/stable/index.html>, <https://github.com/xgi-org/xgi/blob/main/SUPPORT.md>, checked 2026-09-20.
- Schloss Dagstuhl seminar calendar. <https://www.dagstuhl.de/en/seminars/seminar-calendar>, checked 2026-09-20.
- Graph Data Council (formerly LDBC). <https://ldbcouncil.org/>, checked 2026-09-20.
- Zenodo XGI community. <https://zenodo.org/communities/xgi>, checked 2026-09-20.
