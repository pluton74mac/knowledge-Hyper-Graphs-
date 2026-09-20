---
title: Benchmarks derived from Freebase and Wikidata — JF17K, WikiPeople, FB-AUTO, M-FB15K, WD50K
type: dataset
status: draft
tags: [benchmarks, datasets, jf17k, wikipeople, fb-auto, m-fb15k, wd50k, freebase, wikidata, leakage, arity]
created: 2026-09-20
updated: 2026-09-20
---

# Benchmarks derived from Freebase and Wikidata

Almost every published number about n-ary or hyper-relational link prediction comes from five
datasets, and all five are carved out of two sources: **Freebase** (JF17K, FB-AUTO, M-FB15K) and
**Wikidata** (WikiPeople, WD50K). Their construction choices determine what the numbers mean, and
two of them have documented defects that invalidate naive comparisons. This note records, for each:
who built it, from what, by which procedure, what its arity distribution is, and what is known to be
wrong with it.

The source data models are described in
[wikidata-and-freebase-data-models.md](wikidata-and-freebase-data-models.md); the lifting operations
are in [../03-construction/from-knowledge-graphs-to-hypergraphs.md](../03-construction/from-knowledge-graphs-to-hypergraphs.md).

## 0. Warning: the published statistics disagree with each other

The same dataset name denotes different files in different papers. Before comparing any two results,
check which row you are reading:

| Dataset | Entities | Relations / roles | Facts | Reported by |
|---|---|---|---|---|
| JF17K (original train split) | 17,629 | 181 instance types | 139,997 instances | [Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf) |
| JF17K (HINGE/StarE version) | 28,645 | 322 relations | 100,947 | [Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf); [Galkin et al., 2020](https://arxiv.org/abs/2009.10847) |
| JF17K (Fatemi version) | 29,177 | 327 relations | 102,648 (77,733 + 24,915) | [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137) |
| JF17K (survey) | 28,645 | **501 roles** | 100,947 | [Wei et al., 2025](https://arxiv.org/abs/2506.08970) |
| WikiPeople (as released) | — | — | 382,229 | [WikiPeople repo](https://github.com/gsp2014/WikiPeople) |
| WikiPeople (survey) | 47,765 | 193 | 382,229 | [Wei et al., 2025](https://arxiv.org/abs/2506.08970) |
| WikiPeople (literal-filtered) | 34,839 | 375 relations | 369,866 | [Galkin et al., 2020](https://arxiv.org/abs/2009.10847) |
| WD50K | 47,156 | 532 relations | 236,507 | [Galkin et al., 2020](https://arxiv.org/abs/2009.10847) |
| WD50K (survey) | 47,155 | 531 | 236,507 | [Wei et al., 2025](https://arxiv.org/abs/2506.08970) |

The 322-vs-501 gap for JF17K is not an error: one counts *relations*, the other counts *roles*,
which is exactly the positional-vs-named distinction of
[hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md).
The off-by-one in WD50K is unexplained in the sources consulted `[unverified]`.

## 1. JF17K (Wen et al., IJCAI 2016)

The first n-ary benchmark, built to show that FB15K's star-to-clique encoding throws away structure.

**Construction**, verbatim:

> "The full Freebase data in RDF format was downloaded. Entities involved in very few triples and
> the triples involving String, Enumeration Type and Numbers were removed. A fact representation was
> recovered from the remaining triples. Facts from meta-relations having only a single role were
> removed. From each meta-relation containing more than 10000 facts, 10000 facts were randomly
> selected. ... Further filtering was applied to T(F) such that each entity is involved in at least
> 5 instances."
> ([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf))

Three consistent views were released: `G` (instance representation), `G_id` (with fact-ID entities)
and `G_s2c` (star-to-clique). Original statistics:

| Split | entities | instance/triple types | instances/triples |
|---|---|---|---|
| train `G` / `G_id` | 17,629 | 181 | 139,997 |
| train `G_s2c` | 17,629 | 381 | 254,366 |
| test `G` / `G_id` | 12,282 | 159 | 22,076 |
| test `G_s2c` | 12,282 | 336 | 52,933 |

(The "17K" in the name is the 17,629 training entities.) Note the effect of S2C alone: relation
types go 181 → 381, facts 139,997 → 254,366. Wen et al. also remark that "JF17K contains no Mediator
vertices, hence 'cleaner'" than raw Freebase.

**Arity distribution** (from the re-derived version):

| arity | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|
| tuples | 56,322 | 34,550 | 9,509 | 2,230 | 37 |

([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137), Table 5.) 45.9% of facts are n-ary
([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf);
[Wei et al., 2025](https://arxiv.org/abs/2506.08970)) — by construction, since JF17K was
"filtered from Freebase to have a significant presence of hyper-relational facts"
([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf)).

**Known problems.**

1. **No validation split.** "as no validation set is proposed for JF17K, we randomly select 20% of
   the train set as validation" ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)) — so
   hyper-parameter tuning is not comparable across papers.
2. **Test leakage.** The decisive finding:

   > "The authors of JF17K reported the dataset to contain redundant entries. In our own analysis,
   > we detected that about 44.5% of the test statements share the same main (s, r, o) triple as the
   > train statements. We consider this fact as a major data leakage which allows triple-based
   > models to memorize subjects and objects appearing in the test set."
   > ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847))

   Any JF17K result that compares a qualifier-aware model against a triple-only baseline is
   confounded by this: the triple baseline can memorise nearly half the test main triples.
3. **Redundancy acknowledged upstream.** Galkin et al. cite the dataset page itself for the
   redundancy report (`http://www.site.uottawa.ca/~yymao/JF17K/`).

## 2. WikiPeople (Guan et al., WWW 2019)

**Construction**, from the release repository: facts about entities of type *human* were extracted
from a Wikidata dump dated **20 November 2017**; image-related facts were filtered and facts
containing "unknown value" or "no value" elements removed; elements with fewer than 30 mentions were
excluded along with their facts; each fact was parsed into role-value pairs; the result was split
80/10/10 ([WikiPeople repository](https://github.com/gsp2014/WikiPeople), checked 2026-09-20).

**Statistics as released** (same source):

| Split | binary | n-ary | total |
|---|---|---|---|
| train | 270,179 | 35,546 | 305,725 |
| valid | 33,845 | 4,378 | 38,223 |
| test | 33,890 | 4,391 | 38,281 |
| **total** | 337,914 | 44,315 | **382,229** |

so about 12% of facts are n-ary; the survey reports 47,765 entities, 193 roles, arity 2–9 and 11.6%
n-ary ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)). The distribution is *not* curated for
n-ary density: "WikiPeople is extracted from Wikidata and focuses on entities of type human without
any specific filtering to improve the presence of hyper-relational facts"
([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf)).

Format: three JSON files (`n-ary_train.json`, `n-ary_valid.json`, `n-ary_test.json`), one fact per
line as role-value pairs plus an `"N"` arity field, with Wikidata ids and WikiPeople-specific ids
suffixed `_h` / `_t` for the head and tail positions
([WikiPeople repository](https://github.com/gsp2014/WikiPeople)).

**Known problem: the qualifiers are mostly literals.**

> "In WikiPeople, about 13% of statements contain at least one literal. Literals (e.g. numeric
> values, date-time instances or other strings, etc) in KGs are conventionally ignored by embedding
> approaches ... However, after removing statements with literals, less than 3% of the remaining
> statements contain any qualifier. This fact renders WikiPeople less sensitive to hyper-relational
> models as performance on triple-only facts dominates the overall score."
> ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847))

The literal-filtered version that HINGE and StarE actually evaluate on is therefore almost a plain
triple dataset:

| | train | test |
|---|---|---|
| triple-only facts | 280,520 (97.4%) | 36,597 (97.4%) |
| hyper-relational facts | 7,389 (2.6%) | 971 (2.6%) |
| total | 287,918 | 37,586 |

([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf), Table 1; Galkin et al.
report the same 2.6% over 369,866 statements.)

A second consequence, noted in
[open-world-vs-closed-world-and-uncertainty.md](open-world-vs-closed-world-and-uncertainty.md):
dropping "unknown value" and "no value" facts also drops Wikidata's only explicit existential and
negative statements.

Variants `WikiPeople-0bi`, `WikiPeople-50bi` and `WikiPeople-100bi` vary the share of binary facts
(0%, 50%, 100%) ([WikiPeople repository](https://github.com/gsp2014/WikiPeople)).

## 3. FB-AUTO and M-FB15K (Fatemi et al., IJCAI 2020)

Both come from an explicit **inverse reification** of Freebase, described step by step:

> "1. From FREEBASE, remove the facts that have relations defined on a single entity, or that
> contain numbers or enumeration as entities. 2. Join the triples in FREEBASE that have the same
> subject and actual relation, and the same entity. The role (the 3rd part of the relation) provides
> the position is [sic] the resulting relation. ... 3. Create the FB-AUTO dataset by selecting the
> facts from H whose subject is 'automotive' (first part of relation names is 'automative' [sic]).
> 4. Create the M-FB15K dataset by following a strategy similar to that proposed by [Bordes et al.,
> 2013]: select the facts in H that pertain to entities present in the Wikilinks database [Singh et
> al., 2012]. 5. Split the facts in each of FB-AUTO and M-FB15K randomly into train, test, and
> validation sets."
> ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137))

Step 2 is the key operation: three Freebase triples such as `film.performance.actor`,
`film.performance.character`, `film.performance.film` on a shared mediator collapse into one ternary
fact `film.performance(actor, character, movie)`, with the last component of the relation name
becoming the argument position.

**Statistics** ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137), Tables 2 and 5):

| Dataset | \|E\| | \|R\| | train | valid | test | arity 2 | arity 3 | arity 4 | arity 5 | arity 6 |
|---|---|---|---|---|---|---|---|---|---|---|
| FB-AUTO | 3,410 | 8 | 6,778 | 2,255 | 2,180 | 3,786 | 0 | 215 | 7,212 | 0 |
| M-FB15K | 10,314 | 71 | 415,375 | 39,348 | 38,797 | 82,247 | 400,027 | 26 | 11,220 | 0 |
| JF17K (their version) | 29,177 | 327 | 77,733 | — | 24,915 | 56,322 | 34,550 | 9,509 | 2,230 | 37 |

Two features to be aware of:

- **The arity distributions are extremely lumpy.** FB-AUTO has *no* ternary facts and is dominated
  by arity 5 (7,212 of 11,213); M-FB15K is dominated by arity 3 (400,027 of 493,520). Neither looks
  like a general n-ary knowledge base, so "average over arities" scores on them say little.
- **FB-AUTO is small and domain-specific** (8 relations, automotive), which makes it a sanity check
  rather than a benchmark.

Fatemi et al. also break results down by arity bin ("bins of arity 2, 3, and 4-5-6 in JF17K")
because "the number of test tuples in higher arities (4-5-6) is much less than in smaller arities
(2-3)" — a practice worth copying.

**Background statistic** motivating these datasets: "in the original FREEBASE more than 1/3rd of the
entities participate in non-binary relations ... 61% of the relations in the original Freebase are
non-binary" ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)).

## 4. WD50K and its variants (Galkin et al., EMNLP 2020)

Built explicitly to repair the JF17K and WikiPeople defects.

**Construction**, verbatim:

> "We begin with a set of seed nodes corresponding to entities from FB15K-237 having a direct
> mapping in Wikidata (P646 'Freebase ID'). Then, for each seed node, all statements whose main
> object and qualifier values correspond to `wikibase:Item` are extracted. This step results in the
> removal of all literals in object position. Similarly, all literals are filtered out from the
> qualifiers of the obtained statements. To increase the connectivity in the statements graph, all
> the entities mentioned less than twice are dropped. All the statements of WD50K are randomly split
> into the train, test, and validation sets. To eliminate test set leakages we remove all statements
> from train and validation sets that share the same main triple (s, p, o) with test statements.
> Finally, we remove statements from the test set that contain entities and relations not present in
> the train or validation sets."
> ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847))

Source dump: Wikidata RDF dump of **August 2019** (`wikidatawiki/20190801`). Released at
[Zenodo record 4036498](https://zenodo.org/record/4036498).

**Statistics** ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847), Table 1):

| Dataset | statements | with qualifiers | entities | relations | entities only in qualifiers | relations only in qualifiers | train | valid | test |
|---|---|---|---|---|---|---|---|---|---|
| WD50K | 236,507 | 32,167 (13.6%) | 47,156 | 532 | 5,460 | 45 | 166,435 | 23,913 | 46,159 |
| WD50K (33) | 102,107 | 31,866 (31.2%) | 38,124 | 475 | 6,463 | 47 | 73,406 | 10,568 | 18,133 |
| WD50K (66) | 49,167 | 31,696 (64.5%) | 27,347 | 494 | 7,167 | 53 | 35,968 | 5,154 | 8,045 |
| WD50K (100) | 31,314 | 31,314 (100%) | 18,792 | 279 | 7,862 | 75 | 22,738 | 3,279 | 5,297 |

The three variants hold the qualified statements roughly fixed (≈31–32k) and vary how many
triple-only statements accompany them, so a model's sensitivity to qualifier density can be measured
directly. Arity ranges from **2 to 67** ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)) — the
widest of any dataset here, and the concrete reason a fixed-arity relation symbol per role
combination is impractical
([hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md)).

The "entities only in qualifiers" column is the most interesting design feature: 5,460 entities in
full WD50K appear *only* as qualifier values, rising to 7,862 in WD50K (100). A model that ignores
qualifiers cannot represent them at all.

**Caveats.** WD50K inherits Wikidata's coverage biases through the FB15K-237 seed set (so it is
Freebase-shaped despite being Wikidata-sourced), drops all literals, and — like every dataset here
— was built from a dump that is now years old.

## 5. Summary comparison

| | JF17K | WikiPeople | FB-AUTO | M-FB15K | WD50K |
|---|---|---|---|---|---|
| source | Freebase RDF | Wikidata dump 2017-11-20 | Freebase | Freebase | Wikidata dump 2019-08-01 |
| introduced | [Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf) | [Guan et al., 2019](https://dl.acm.org/doi/10.1145/3308558.3313414) | [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137) | [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137) | [Galkin et al., 2020](https://arxiv.org/abs/2009.10847) |
| formalisation | role-value / positional tuple | role-value pairs | positional tuple | positional tuple | primary triple + qualifiers |
| arity range | 2–6 | 2–9 | 2, 4, 5 | 2–5 | 2–67 |
| share n-ary / qualified | 45.9% | 11.6% (2.6% after literal filtering) | ~66% | ~83% | 13.6% (up to 100% in variants) |
| validation split | none originally | yes | yes | yes | yes |
| leakage controlled | **no** (44.5% main-triple overlap) | not reported | not reported | not reported | **yes**, by construction |
| literals kept | no | yes (dropped by most users) | no | no | no |

## 6. Guidance

1. **Do not report JF17K numbers without the leakage caveat**
   ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)). If a comparison with triple-only
   baselines is the point, JF17K cannot make it.
2. **Do not read WikiPeople as a hyper-relational benchmark** after literal filtering: 97.4% of its
   facts are plain triples ([Rosso et al., 2020](https://exascale.info/assets/pdf/rosso2020www.pdf)).
3. **Report per-arity breakdowns**, as Fatemi et al. do, because the arity distributions are so
   skewed that aggregate MRR is dominated by arity 2 or 3.
4. **Prefer WD50K and its 33/66/100 variants** for qualifier-sensitivity experiments — they are the
   only family here designed to isolate that variable.
5. **State the dump date.** Every dataset here is frozen against a dump from 2016–2019; conclusions
   about "what Wikidata looks like" drawn from them are out of date.
6. **There is no nested, no temporal-native and no uncertain n-ary benchmark** in this family; see
   the open questions in
   [metagraphs-atomspace-and-hypergraphdb.md](metagraphs-atomspace-and-hypergraphdb.md) and
   [open-world-vs-closed-world-and-uncertainty.md](open-world-vs-closed-world-and-uncertainty.md).

## Sources

- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. *On the Representation and Embedding of Knowledge Bases Beyond Binary Relations.* IJCAI 2016. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
- Guan, S., Jin, X., Wang, Y., Cheng, X. *Link Prediction on N-ary Relational Data.* WWW 2019. https://dl.acm.org/doi/10.1145/3308558.3313414
- Guan, S., et al. *WikiPeople: An n-ary relational dataset derived from Wikidata.* GitHub repository, checked 2026-09-20. https://github.com/gsp2014/WikiPeople
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137
- Rosso, P., Yang, D., Cudré-Mauroux, P. *Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction.* WWW 2020. https://exascale.info/assets/pdf/rosso2020www.pdf
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020; arXiv:2009.10847. https://arxiv.org/abs/2009.10847
- Galkin, M., et al. *WD50K dataset.* Zenodo record 4036498, 2020. https://zenodo.org/record/4036498
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs.* arXiv:2506.08970, 2025. https://arxiv.org/abs/2506.08970
- Singh, S., Subramanya, A., Pereira, F., McCallum, A. *Wikilinks: A large-scale cross-document coreference corpus labeled via links to Wikipedia.* University of Massachusetts Amherst, Technical Report UM-CS-2012-015, 2012. Cited via [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137). `[unverified]`
- Bordes, A., Usunier, N., Garcia-Duran, A., Weston, J., Yakhnenko, O. *Translating Embeddings for Modeling Multi-relational Data.* NIPS 2013. Cited via [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137) for the FB15K sampling strategy. `[unverified]`
