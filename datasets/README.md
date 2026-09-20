# Dataset manifest

**No bulk data is committed to this repository.** This directory holds *manifests* — pointers,
licences, checksums and fetch instructions — and nothing else. Everything listed here was
checked on **2026-09-20**.

Background, statistics and task descriptions live in
[../kb/09-ecosystem/datasets-and-benchmarks.md](../kb/09-ecosystem/datasets-and-benchmarks.md).
Read [../kb/09-ecosystem/dataset-quality-and-leakage-issues.md](../kb/09-ecosystem/dataset-quality-and-leakage-issues.md)
before using any of them for evaluation: several carry documented test-set leakage.

---

## 1. Local path convention

```
datasets/
  README.md                 <- this manifest (tracked)
  <family>/<dataset>/       <- untracked download target
    MANIFEST.json           <- tracked: source URL, licence, retrieval date, checksums
    raw/                    <- untracked: exactly as downloaded
    processed/              <- untracked: anything derived
```

- `<family>` is one of `n-ary-kg`, `hypergraph-learning`, `higher-order-networks`,
  `rag-corpora`, `knowledge-bases`.
- Add `datasets/**/raw/`, `datasets/**/processed/` and `datasets/**/*.zip` to `.gitignore`
  before the first download.
- `MANIFEST.json` is the only file under a dataset directory that is ever committed.

`MANIFEST.json` template:

```json
{
  "name": "wd50k",
  "family": "n-ary-kg",
  "source_url": "https://github.com/migalkin/StarE",
  "source_ref": "<git commit sha or release tag>",
  "retrieved": "2026-09-20",
  "licence": "MIT (code); underlying Wikidata data CC0-1.0",
  "files": [{"path": "raw/train.txt", "sha256": "<hash>", "bytes": 0}],
  "notes": "Leakage-filtered by construction; see kb/09-ecosystem/dataset-quality-and-leakage-issues.md"
}
```

Record `source_ref` and `sha256` **always**. The same dataset name is published with different
statistics by different papers; a name alone does not identify data.

---

## 2. Manifest

### 2.1 n-ary / hyper-relational knowledge graphs

| Dataset | Source | Licence | Local path | How to fetch |
|---|---|---|---|---|
| **WD50K**, WD50K(33/66/100) | [migalkin/StarE](https://github.com/migalkin/StarE) | MIT (repository); source data Wikidata CC0-1.0 | `n-ary-kg/wd50k/` | `git clone --depth 1 https://github.com/migalkin/StarE` then copy `data/clean/wd50k*` |
| **JF17K**, JF17K-3, JF17K-4 | [PaddlePaddle/Research › KG/ACL2021_GRAN](https://github.com/PaddlePaddle/Research/tree/master/KG/ACL2021_GRAN) | Apache-2.0 (code); source data Freebase CC-BY | `n-ary-kg/jf17k/` | sparse-checkout the `KG/ACL2021_GRAN` sub-directory |
| **WikiPeople**, WikiPeople-, -3, -4 | same GRAN directory; original release [gsp2014/NaLP](https://github.com/gsp2014/NaLP) `[unverified]` | Apache-2.0 (code); source data Wikidata CC0-1.0 | `n-ary-kg/wikipeople/` | as above |
| **FB-AUTO**, **M-FB15K** | [ServiceNow/HypE](https://github.com/ServiceNow/HypE) | **no licence file** — contact authors before redistributing | `n-ary-kg/fb-auto/`, `n-ary-kg/m-fb15k/` | `git clone --depth 1 https://github.com/ServiceNow/HypE` |
| **WD20K** (inductive) | [Ali et al., ISWC 2021](https://doi.org/10.1007/978-3-030-88361-4_5) | `[unverified]` | `n-ary-kg/wd20k/` | follow the paper's artefact link |
| **HyNT** numeric/temporal sets | [bdi-lab/HyNT](https://github.com/bdi-lab/HyNT) | GitHub metadata "Other" | `n-ary-kg/hynt/` | `git clone --depth 1 https://github.com/bdi-lab/HyNT` |

### 2.2 Hypergraph-learning benchmarks

| Dataset | Source | Licence | Local path | How to fetch |
|---|---|---|---|---|
| Cora / Citeseer / Pubmed co-citation, Cora-CA, DBLP-CA, Zoo, 20News, Mushroom, NTU2012, ModelNet40, **Yelp**, **House**, **Walmart** | AllSet release, [Chien et al., ICLR 2022](https://arxiv.org/abs/2106.13264) | `[unverified]` per-dataset; Yelp derives from the Yelp Open Dataset, whose terms restrict redistribution | `hypergraph-learning/allset/` | clone the AllSet repository named in the paper and run its data script |
| Same suite via DHG | [iMoonLab/DeepHypergraph](https://github.com/iMoonLab/DeepHypergraph) | Apache-2.0 (code) | `hypergraph-learning/dhg/` | `dhg.data.Cora()` etc. — downloads on first use |

### 2.3 Empirical higher-order networks

| Collection | Source | Licence | Local path | How to fetch |
|---|---|---|---|---|
| **XGI-DATA** (51 datasets, HIF JSON, Zenodo-hosted) | [xgi-org/xgi-data](https://github.com/xgi-org/xgi-data), [Zenodo XGI community](https://zenodo.org/communities/xgi) | repository metadata "Other"; per-record licences on Zenodo `[unverified]` | `higher-order-networks/xgi-data/` | `python -c "import xgi; xgi.load_xgi_data('email-enron', cache=True)"`, or read `index.json` and fetch the Zenodo URL directly |
| **hypergraphx-data** (136 datasets) | <https://hgx-team.github.io/hypergraphx-data/> | `[unverified]` | `higher-order-networks/hypergraphx-data/` | `from hypergraphx.readwrite import list_remote_datasets, download_remote_dataset` |
| **Benson "Data!" collection** | <https://www.cs.cornell.edu/~arb/data/> | terms stated per dataset page; cite [Benson et al., PNAS 2018](https://doi.org/10.1073/pnas.1800683115) | `higher-order-networks/benson/` | download the per-dataset archives from the individual pages |
| **SNAP** | <https://snap.stanford.edu/data/> | no explicit licence on the index page; cite `@misc{snapnets}` | `higher-order-networks/snap/` | direct download links per dataset |
| **KONECT** | <http://konect.cc/> | `[unverified]` | `higher-order-networks/konect/` | site returned **HTTP 503** on 2026-09-20; retry before relying on it |

### 2.4 Hypergraph-RAG corpora

| Corpus | Source | Licence | Local path | How to fetch |
|---|---|---|---|---|
| **HyperGraphRAG** contexts + questions (Medicine, Agriculture, CS, Legal, Mix; 512 questions each) | [LHRLAB/HyperGraphRAG › evaluation](https://github.com/LHRLAB/HyperGraphRAG/blob/main/evaluation/README.md) | code MIT; **corpus licence unstated**, and the Medicine context is built from copyrighted clinical guidelines | `rag-corpora/hypergraphrag/` | the repository directs users to a **Terabox** link — no DOI, no checksum; mirror it yourself and record a hash |
| **Hyper-RAG** datasets (NeurologyCrop + nine others) | [iMoonLab/Hyper-RAG](https://github.com/iMoonLab/Hyper-RAG) | code Apache-2.0; **corpus licence unstated** | `rag-corpora/hyper-rag/` | Google Drive / Baidu Cloud links in the README |
| **UltraDomain** (upstream of three HyperGraphRAG domains) | named in [Luo et al., 2025](https://arxiv.org/html/2503.21322v3) | `[unverified]` | `rag-corpora/ultradomain/` | `[unverified]` canonical location not confirmed in this run |

Treat everything in this sub-table as **provisional**: none of it is archived with a DOI, and
the licensing is unresolved. See section 8 of
[../kb/09-ecosystem/dataset-quality-and-leakage-issues.md](../kb/09-ecosystem/dataset-quality-and-leakage-issues.md).

### 2.5 Large knowledge bases

| Resource | Source | Licence | Local path | How to fetch |
|---|---|---|---|---|
| **Wikidata** dumps | <https://dumps.wikimedia.org/wikidatawiki/entities/> | CC0-1.0 | `knowledge-bases/wikidata/` | `curl -O https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.bz2` (very large — plan disk) |
| **YAGO 4.5** (49 M entities, 109 M facts; RDF-star "meta" facts) | <https://yago-knowledge.org/downloads/yago-4-5> | CC-BY-SA | `knowledge-bases/yago-4.5/` | Turtle files: schema, taxonomy, facts, facts-beyond-Wikipedia, meta |
| **DBpedia** | <https://www.dbpedia.org/> | CC-BY-SA | `knowledge-bases/dbpedia/` | Databus releases |
| **ConceptNet** | <https://conceptnet.io/> | CC-BY-SA 4.0 | `knowledge-bases/conceptnet/` | assertions dump from the project's GitHub releases |
| **ATOMIC 2020** | <https://allenai.org/data/atomic-2020> | CC-BY `[unverified]` | `knowledge-bases/atomic/` | AI2 download page |
| **Freebase** (final dump, 2015) | <https://developers.google.com/freebase> | CC-BY | `knowledge-bases/freebase/` | archived dump; JF17K, FB-AUTO and M-FB15K all derive from it |

---

## 3. Fetch etiquette

1. **Fetch once, hash immediately**: `sha256sum raw/* > MANIFEST.sha256`.
2. **Record the retrieval date and the upstream ref** in `MANIFEST.json`.
3. **Do not commit data.** If a file must be shared, deposit it where the licence permits
   (Zenodo with a DOI) and put the DOI in the manifest.
4. **Respect the licence.** Where the table says "no licence file", the legal default is all
   rights reserved: use locally, do not redistribute, and ask the authors.
5. **Re-check before citing.** Links rot; the Terabox, Google Drive and Baidu Cloud links in
   section 2.4 are the most fragile entries here.

---

## Sources

- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. (2020). *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020. <https://doi.org/10.18653/v1/2020.emnlp-main.596>
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. (2020). *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020. <https://doi.org/10.24963/ijcai.2020/303>
- Wang, Q., Wang, H., Lyu, Y., Zhu, Y. (2021). *Link Prediction on N-ary Relational Facts: A Graph-based Approach.* Findings of ACL-IJCNLP 2021. <https://doi.org/10.18653/v1/2021.findings-acl.35>
- Ali, M., Berrendorf, M., Galkin, M., Thost, V., Ma, T., Tresp, V., Lehmann, J. (2021). *Improving Inductive Link Prediction Using Hyper-relational Facts.* ISWC 2021. <https://doi.org/10.1007/978-3-030-88361-4_5>
- Chung, C., Lee, J., Whang, J. J. (2023). *Representation Learning on Hyper-Relational and Numeric Knowledge Graphs with Transformers.* KDD 2023. <https://doi.org/10.1145/3580305.3599490>
- Chien, E., Pan, C., Peng, J., Milenkovic, O. (2022). *You are AllSet.* ICLR 2022; arXiv:2106.13264. <https://arxiv.org/abs/2106.13264>
- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. (2018). *Simplicial closure and higher-order link prediction.* PNAS 115(48). <https://doi.org/10.1073/pnas.1800683115>
- XGI-DATA, <https://github.com/xgi-org/xgi-data> and <https://zenodo.org/communities/xgi>; hypergraphx-data, <https://hgx-team.github.io/hypergraphx-data/>; both checked 2026-09-20.
- Luo, H., E, H., Chen, G. et al. (2025). *HyperGraphRAG.* arXiv:2503.21322. <https://arxiv.org/html/2503.21322v3>
- Feng, Y., Hu, H., Ying, S. et al. (2026). *Hyper-RAG.* Nature Communications 17, 5778. <https://doi.org/10.1038/s41467-026-71411-1>
- YAGO 4.5 downloads, <https://yago-knowledge.org/downloads/yago-4-5>; ConceptNet, <https://conceptnet.io/>; SNAP, <https://snap.stanford.edu/data/>; KONECT, <http://konect.cc/>; all checked 2026-09-20.
