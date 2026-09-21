# Sources — 05 Query, embeddings, reasoning

Bibliography for `kb/05-query-embeddings-reasoning/`. Compiled 2026-09-20. Grouped by topic; every
entry is cited from at least one note in the section. Entries marked `[unverified]` were identified
from a search result, a publisher listing or another paper's reference list, but the full text was
not fetched during this research run; the bibliographic fields are reported as found. Repository
URLs were resolved through the GitHub API on 2026-09-20.

## Surveys and taxonomies of the field

- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. "A Survey of Link Prediction in N-ary Knowledge Graphs." arXiv:2506.08970, 10 June 2025; EMNLP 2025 main conference. https://arxiv.org/abs/2506.08970 · https://doi.org/10.18653/v1/2025.emnlp-main.1451 · companion repository https://github.com/JiyaoWei/LP_NKGs
- Lu, X., Tupikina, L., Alam, M. "Two-Dimensional Taxonomy for n-Ary Knowledge Representation Learning Methods." *IEEE Transactions on Knowledge and Data Engineering*, 2026; arXiv:2506.05626. https://arxiv.org/abs/2506.05626 · https://doi.org/10.1109/tkde.2026.3731554
- Kim, S., Lee, S. Y., Gao, Y., Antelmi, A., Polato, M., Shin, K. "A Survey on Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide." KDD 2024; arXiv:2404.01039 (v3). https://arxiv.org/abs/2404.01039

## Query languages and specifications

- Seaborne, A. et al. *SPARQL 1.2 Query Language*. W3C Working Draft, 13 September 2026. https://www.w3.org/TR/sparql12-query/
- Harris, S., Seaborne, A. (eds.) *SPARQL 1.1 Query Language*. W3C Recommendation, 21 March 2013. https://www.w3.org/TR/sparql11-query/
- Seaborne, A., Kellogg, G., Hartig, O., Champin, P.-A. *RDF 1.2 Concepts and Abstract Data Model*. W3C Candidate Recommendation, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- Patel-Schneider, P., Franconi, E., Arndt, D. *RDF 1.2 Semantics*. W3C Candidate Recommendation, 7 April 2026. https://www.w3.org/TR/rdf12-semantics/
- Hayes, P., Patel-Schneider, P. (eds.) *RDF 1.1 Semantics*. W3C Recommendation, 25 February 2014. https://www.w3.org/TR/rdf11-mt/
- Noy, N., Rector, A. (eds.) *Defining N-ary Relations on the Semantic Web*. W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- TypeDB. *TypeQL Reference — Data and query model* (TypeDB 3.x). Checked 20 September 2026. https://typedb.com/docs/typeql-reference/data-model/
- TypeDB. *TypeDB Academy, Lesson 7.2: Relation patterns*. Checked 20 September 2026. https://typedb.com/docs/academy/7-understanding-query-patterns/7.2-relation-patterns
- GQL Standards Committee. *GQL* — ISO/IEC 39075:2024, *Information technology — Database languages — GQL*, published 17 April 2024. https://www.gqlstandards.org/
- Apache TinkerPop. *TinkerPop 3.8.2 Reference Documentation*. Checked 20 September 2026. https://tinkerpop.apache.org/docs/current/reference/
- Ceri, S., Gottlob, G., Tanca, L. "What you always wanted to know about Datalog (and never dared to ask)." *IEEE Transactions on Knowledge and Data Engineering* 1(1), 1989. https://doi.org/10.1109/69.43410
- Goertzel, B. et al. "OpenCog Hyperon: A Framework for AGI at the Human Level and Beyond." arXiv:2310.18318, 2023. https://arxiv.org/abs/2310.18318
- trueagi-io. *Minimal MeTTa specification* (hyperon-experimental). Checked 20 September 2026. https://github.com/trueagi-io/hyperon-experimental/blob/main/docs/minimal-metta.md
- HypergraphDB project. *Working with Queries and Results* (wiki). Checked 20 September 2026. https://github.com/hypergraphdb/hypergraphdb/wiki/QueriesAndResults
- Teng, F., Li, H., Di, S., Chen, L. "Cardinality Estimation on Hyper-relational Knowledge Graphs." arXiv:2405.15231, 2024. https://arxiv.org/abs/2405.15231

## Query complexity, conjunctive queries, decompositions

- Yannakakis, M. "Algorithms for acyclic database schemes." *VLDB* 1981. No open DOI; bibliographic record verified via OpenAlex.
- Gottlob, G., Leone, N., Scarcello, F. "The complexity of acyclic conjunctive queries." *Journal of the ACM* 48(3), 2001. https://doi.org/10.1145/382780.382783
- Gottlob, G., Leone, N., Scarcello, F. "Hypertree Decompositions and Tractable Queries." arXiv:cs/9812022, 1998; *Journal of Computer and System Sciences* 64(3), 2002. https://arxiv.org/abs/cs/9812022 · https://doi.org/10.1006/jcss.2001.1809
- Gottlob, G., Leone, N., Scarcello, F. "Hypertree Decompositions: A Survey." *MFCS 2001*, LNCS 2136. https://doi.org/10.1007/3-540-44683-4_5
- Gottlob, G., Miklós, Z., Schwentick, T. "Generalized hypertree decompositions: NP-hardness and tractable variants." *Journal of the ACM* 56(6), 2009 (earlier version PODS 2007). https://doi.org/10.1145/1568318.1568320
- Atserias, A., Grohe, M., Marx, D. "Size Bounds and Query Plans for Relational Joins." *FOCS 2008*; *SIAM Journal on Computing* 42(4), 2013. https://doi.org/10.1137/110859440
- Wikipedia. "Subgraph isomorphism problem." Checked 20 September 2026. https://en.wikipedia.org/wiki/Subgraph_isomorphism_problem

## Knowledge hypergraph and n-ary embedding models

- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the representation and embedding of knowledge bases beyond binary relations" (m-TransH, JF17K). IJCAI 2016; arXiv:1604.08642. https://arxiv.org/abs/1604.08642
- Zhang, R., Li, J., Mei, J., Mao, Y. "Scalable Instance Reconstruction in Knowledge Bases via Relatedness Affiliated Embedding" (RAE). *WWW 2018*. https://doi.org/10.1145/3178876.3186017
- Guan, S., Jin, X., Wang, Y., Cheng, X. "Link Prediction on N-ary Relational Data" (NaLP, WikiPeople). *WWW 2019*. https://doi.org/10.1145/3308558.3313414 · code https://github.com/gsp2014/NaLP
- Guan, S., Jin, X., Guo, J., Wang, Y., Cheng, X. "Link Prediction on N-ary Relational Data Based on Relatedness Evaluation" (t-NaLP). *IEEE TKDE*, 2021. https://doi.org/10.1109/tkde.2021.3073483
- Rosso, P., Yang, D., Cudré-Mauroux, P. "Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction" (HINGE). *WWW 2020*. https://doi.org/10.1145/3366423.3380257 · code https://github.com/eXascaleInfolab/HINGE_code
- Guan, S., Jin, X., Guo, J., Wang, Y., Cheng, X. "NeuInfer: Knowledge Inference on N-ary Facts." *ACL 2020*. https://doi.org/10.18653/v1/2020.acl-main.546
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations" (HypE, HSimplE, FB-AUTO, M-FB15K). IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137 · code https://github.com/ServiceNow/HypE and https://github.com/baharefatemi/HypE
- Liu, Y., Yao, Q., Li, Y. "Generalizing Tensor Decomposition for N-ary Relational Knowledge Bases" (GETD). *WWW 2020*. https://doi.org/10.1145/3366423.3380188 · code https://github.com/liuyuaa/GETD
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs" (StarE, WD50K). *EMNLP 2020*; arXiv:2009.10847. https://doi.org/10.18653/v1/2020.emnlp-main.596 · https://arxiv.org/abs/2009.10847 · code https://github.com/migalkin/StarE
- Liu, Y., Yao, Q., Li, Y. "Role-Aware Modeling for N-ary Relational Knowledge Bases" (RAM). *WWW 2021*. https://doi.org/10.1145/3442381.3449874
- Wang, Q., Wang, H., Lyu, Y., Zhu, Y. "Link Prediction on N-ary Relational Facts: A Graph-based Approach" (GRAN). *Findings of ACL 2021*. https://doi.org/10.18653/v1/2021.findings-acl.35
- Yu, D., Yang, Y. "Improving Hyper-Relational Knowledge Graph Completion" (Hy-Transformer / HyTransformer). arXiv:2104.08167, 2021. https://arxiv.org/abs/2104.08167
- Shomer, H., Jin, W., Li, J., Ma, Y., Liu, H. "Learning Representations for Hyper-Relational Knowledge Graphs" (QUAD). 2023. https://doi.org/10.1145/3625007.3627591
- Xiong, B., Nayyeri, M., Pan, S., Staab, S. "Shrinking Embeddings for Hyper-relational Knowledge Graphs" (ShrinkE). *ACL 2023*; arXiv:2306.02199. https://doi.org/10.18653/v1/2023.acl-long.743 · code https://github.com/xiongbo010/ShrinkE
- Wang, C., Wang, X., Li, Z., Chen, Z., Li, J. "HyConvE: A Novel Embedding Model for Knowledge Hypergraph Link Prediction with Convolutional Neural Networks." *WWW 2023*. https://doi.org/10.1145/3543507.3583256
- Chung, C., Lee, J., Whang, J. J. "Representation Learning on Hyper-Relational and Numeric Knowledge Graphs with Transformers" (HyNT). *KDD 2023*; arXiv:2305.18256. https://doi.org/10.1145/3580305.3599490 · code https://github.com/bdi-lab/HyNT
- Luo, H., E, H., Yang, Y., Guo, Y., Sun, M., Yao, T., Tang, Z., Wan, K., Song, M., Lin, W. "HAHE: Hierarchical Attention for Hyper-Relational Knowledge Graphs in Global and Local Level." *ACL 2023*; arXiv:2305.06588. https://doi.org/10.18653/v1/2023.acl-long.450 · code https://github.com/LHRLAB/HAHE
- Yu, W., Yang, J., Yang, D. "Robust Link Prediction over Noisy Hyper-Relational Knowledge Graphs via Active Learning" (NYLON). *WWW 2024*. https://doi.org/10.1145/3589334.3645686
- Hu, Z., Gutiérrez-Basulto, V., Xiang, Z., Li, R., Pan, J. Z. "HyperMono: A Monotonicity-aware Approach to Hyper-Relational Knowledge Representation." arXiv:2404.09848, 2024; journal version "Monotonicity-aware knowledge fusion for hyper-relational knowledge representation", *Information Fusion*, 2026. https://arxiv.org/abs/2404.09848 · https://doi.org/10.1016/j.inffus.2026.104643
- Li, Z., Wang, X., Zhao, J., Feng, F., Chen, Z., Li, J. "HySAE: An Efficient Semantic-Enhanced Representation Learning Model for Knowledge Hypergraph Link Prediction." 2025. https://doi.org/10.1145/3696410.3714549
- Liu, Z. et al. "UniHR: Hierarchical Representation Learning for Unified Knowledge Graph Link Prediction." arXiv:2411.07019, 2024. https://arxiv.org/abs/2411.07019
- Yan, S. et al. "Hyper2: Hyperbolic embedding for hyper-relational link prediction." *Neurocomputing*, 2022. `[unverified]` — cited via Wei et al. 2025.
- Yan, S. et al. "PolygonE: Modeling n-ary relational data as gyro-polygons in hyperbolic space." *AAAI 2022*. `[unverified]` — cited via Wei et al. 2025.
- Yan, S. et al. "Modeling n-ary relational data as gyro-polygons with learnable gyro-centroid" (WPolygonE+). *Knowledge-Based Systems*, 2022. `[unverified]` — cited via Wei et al. 2025.
- Di, S., Yao, Q., Chen, L. "Searching to sparsify tensor decomposition for n-ary relational data" (S2S). 2021. `[unverified]` — cited via Wei et al. 2025.
- Hu, Z., Gutiérrez-Basulto, V., Xiang, Z., Li, R., Pan, J. Z. "HyperFormer." 2023. `[unverified]` — cited via Wei et al. 2025.
- Lu, Y., Yu, W., Jing, X., Yang, D. "HyperCL: A contrastive learning framework for hyper-relational knowledge graph embedding." 2024. `[unverified]` — cited via Wei et al. 2025.
- Lu, Y., Rosso, P., Yang, D., Cudré-Mauroux, P. "Schema-aware hyper-relational knowledge graph embeddings for link prediction" (HELIOS). *IEEE TKDE*, 2023. `[unverified]` — cited via Wei et al. 2025.
- Li, Z. et al. "HyCubE" and "HJE." 2024. `[unverified]` — cited via Wei et al. 2025.

## Expressivity, theory, foundation models

- Huang, X., Romero Orth, M., Barceló, P., Bronstein, M. M., Ceylan, İ. İ. "Link Prediction with Relational Hypergraphs" (HCNet). *TMLR* 2025; arXiv:2402.04062. https://arxiv.org/abs/2402.04062
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. "HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs." arXiv:2506.12362, 14 June 2025. https://arxiv.org/abs/2506.12362 · code https://github.com/HxyScotthuang/HYPER (described there as ICLR 2026)
- Jiang, F., Li, Y., Feng, Y., Zheng, K., Niu, L., Ramasubramanian, B., Alomair, B., Bushnell, L., Poovendran, R. "The WidthWall: A Strict Expressivity Hierarchy for Hypergraph Neural Networks." arXiv:2605.13690, 13 May 2026. https://arxiv.org/abs/2605.13690
- Yu, W., Lu, Y., Yang, D. "THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs." arXiv:2602.05424, 5 February 2026. https://arxiv.org/abs/2602.05424

## Hypergraph neural networks and libraries

- Feng, Y., You, H., Zhang, Z., Ji, R., Gao, Y. "Hypergraph Neural Networks." *AAAI 2019*. https://doi.org/10.1609/aaai.v33i01.33013558
- Yadati, N., Nimishakavi, M., Yadav, P., Nitin, V., Louis, A., Talukdar, P. "HyperGCN: A New Method of Training Graph Convolutional Networks on Hypergraphs." NeurIPS 2019; arXiv:1809.02589. https://arxiv.org/abs/1809.02589
- Dong, Y., Sawin, W., Bengio, Y. "HNHN: Hypergraph Networks with Hyperedge Neurons." ICML 2020 Graph Representation Learning workshop; arXiv:2006.12278. https://arxiv.org/abs/2006.12278
- Huang, J., Yang, J. "UniGNN: a Unified Framework for Graph and Hypergraph Neural Networks." *IJCAI 2021*; arXiv:2105.00956. https://doi.org/10.24963/ijcai.2021/353
- Chien, E., Pan, C., Peng, J., Milenkovic, O. "You are AllSet: A Multiset Function Framework for Hypergraph Neural Networks." ICLR 2022; arXiv:2106.13264. https://arxiv.org/abs/2106.13264 · code https://github.com/jianhao2016/AllSet
- Wang, P., Yang, S., Liu, Y., Wang, Z., Li, P. "Equivariant Hypergraph Diffusion Neural Operators" (ED-HNN). ICLR 2023. https://openreview.net/pdf?id=RiTjKoscnNd · code https://github.com/Graph-COM/ED-HNN
- Gao, Y., Feng, Y., Ji, S., Ji, R. "HGNN+: General Hypergraph Neural Networks." *IEEE TPAMI*, 2022. https://doi.org/10.1109/tpami.2022.3182052
- Jiang, J., Wei, Y., Feng, Y., Cao, J., Gao, Y. "Dynamic Hypergraph Neural Networks." *IJCAI 2019*. https://doi.org/10.24963/ijcai.2019/366
- iMoonLab. *DeepHypergraph (DHG)*. Checked 20 September 2026. https://github.com/iMoonLab/DeepHypergraph · https://deephypergraph.readthedocs.io/
- Pacific Northwest National Laboratory. *HyperNetX*. Checked 20 September 2026. https://github.com/pnnl/HyperNetX
- pyt-team. *TopoNetX — Computing on Topological Domains*. Checked 20 September 2026. https://github.com/pyt-team/TopoNetX
- Li, F., Wang, X., Zhang, W., Zhang, Y., Lin, X. "DHG-Bench: A Comprehensive Benchmark for Deep Hypergraph Learning." arXiv:2508.12244, 2025. https://arxiv.org/abs/2508.12244 · code https://github.com/Coco-Hut/DHG-Bench

## Reasoning, rules, complex query answering

- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. "Directed hypergraphs and applications." *Discrete Applied Mathematics* 42(2–3), 1993. https://doi.org/10.1016/0166-218x(93)90045-p
- Ausiello, G., Laura, L. "Directed hypergraphs: Introduction and fundamental algorithms — A survey." *Theoretical Computer Science*, 2016. https://doi.org/10.1016/j.tcs.2016.03.016
- Dowling, W. F., Gallier, J. "Linear-time algorithms for testing the satisfiability of propositional Horn formulae." *Journal of Logic Programming* 1(3), 1984. https://doi.org/10.1016/0743-1066(84)90014-1
- Kurita, K., Mann, K. "On the Complexity of Hyperpath and Minimal Separator Enumeration in Directed Hypergraphs." arXiv:2507.07528, 10 July 2025. https://arxiv.org/abs/2507.07528
- Galárraga, L., Teflioudi, C., Hose, K., Suchanek, F. "AMIE: Association Rule Mining under Incomplete Evidence in Ontological Knowledge Bases." *WWW 2013*. https://doi.org/10.1145/2488388.2488425
- Chen, Z., Wang, X., Wang, C., Li, J. "Explainable Link Prediction in Knowledge Hypergraphs" (HyperMLN). *CIKM 2022*. https://doi.org/10.1145/3511808.3557316
- Alivanistos, D., Berrendorf, M., Cochez, M., Galkin, M. "Query Embedding on Hyper-relational Knowledge Graphs" (StarQE, WD50K-QE). ICLR 2022; arXiv:2106.08166. https://arxiv.org/abs/2106.08166 · code https://github.com/DimitrisAlivas/StarQE
- Luo, H., E, H., Yang, Y., Zhou, G., Guo, Y., Yao, T., Tang, Z., Lin, X., Wan, K. "NQE: N-ary Query Embedding for Complex Query Answering over Hyper-Relational Knowledge Graphs." AAAI 2023; arXiv:2211.13469. https://arxiv.org/abs/2211.13469 · code https://github.com/LHRLAB/NQE
- Bai, J., Zheng, T., Song, Y. "Sequential Query Encoding for Complex Query Answering on Knowledge Graphs" (SQE). *TMLR* 2023; arXiv:2302.13114. https://arxiv.org/abs/2302.13114
- Tsang, H. T., Wang, Z., Song, Y. "Transformers for Complex Query Answering over Knowledge Hypergraphs" (LKHGT). arXiv:2504.16537, 23 April 2025. https://arxiv.org/abs/2504.16537

## Hypergraph algorithms

- Aksoy, S. G., Joslyn, C., Ortiz Marrero, C., Praggastis, B., Purvine, E. "Hypernetwork science via high-order hypergraph walks." *EPJ Data Science* 9, 2020; arXiv:1906.11295. https://doi.org/10.1140/epjds/s13688-020-00231-0 · https://arxiv.org/abs/1906.11295
- Chitra, U., Raphael, B. J. "Random Walks on Hypergraphs with Edge-Dependent Vertex Weights." ICML 2019; arXiv:1905.08287. https://arxiv.org/abs/1905.08287
- Takai, Y., Miyauchi, A., Ikeda, M., Yoshida, Y. "Hypergraph Clustering Based on PageRank." *KDD 2020*; arXiv:2006.08302. https://doi.org/10.1145/3394486.3403248 · https://arxiv.org/abs/2006.08302
- Hayashi, K., Aksoy, S. G., Park, C. H., Park, H. "Hypergraph Random Walks, Laplacians, and Clustering." *CIKM 2020*. https://doi.org/10.1145/3340531.3412034
- Kamiński, B., Poulin, V., Prałat, P., Szufel, P., Théberge, F. "Clustering via hypergraph modularity." *PLOS ONE* 14(11), 2019. https://doi.org/10.1371/journal.pone.0224307
- Kamiński, B., Misiorek, P., Prałat, P., Théberge, F. "Modularity based community detection in hypergraphs." *Journal of Complex Networks*, 2024. https://doi.org/10.1093/comnet/cnae041
- Lotito, Q. F., Musciotto, F., Montresor, A., Battiston, F. "Higher-order motif analysis in hypergraphs." *Communications Physics* 5, 2022. https://doi.org/10.1038/s42005-022-00858-7
- Nielsen, L. R., Andersen, K. A., Pretolani, D. "Finding the K shortest hyperpaths." *Computers & Operations Research* 32(6), 2005. https://doi.org/10.1016/j.cor.2003.11.014
- Eiter, T., Makino, K., Gottlob, G. "Computational aspects of monotone dualization: A brief survey." *Discrete Applied Mathematics* 156(11), 2008. https://doi.org/10.1016/j.dam.2007.04.017
- Karp, R. M. "Reducibility among Combinatorial Problems." In *Complexity of Computer Computations*, 1972. https://doi.org/10.1007/978-1-4684-2001-2_9

## Inductive, few-shot, temporal

- Ali, M., Berrendorf, M., Galkin, M., Thost, V., Ma, T., Tresp, V., Lehmann, J. "Improving Inductive Link Prediction Using Hyper-relational Facts" (QBLP, WD20K). *ISWC 2021*; arXiv:2107.04894. https://doi.org/10.1007/978-3-030-88361-4_5
- Yin, G., Zhang, H., Yang, Y., Luo, Y. "Inductive Link Prediction on N-ary Relational Facts via Semantic Hypergraph Reasoning" (HART). KDD 2025; arXiv:2503.20676. https://arxiv.org/abs/2503.20676
- Wei, J., Guan, S., Jin, X., Guo, J., Cheng, X. "Inductive link prediction in n-ary knowledge graphs" (MetaNIR). COLING 2025. `[unverified]` — cited via Wei et al. 2025.
- Wei, J., Guan, S., Jin, X., Guo, J., Cheng, X. "Few-shot Link Prediction on N-ary Facts" (MetaRH). COLING 2024; arXiv:2305.06104. https://arxiv.org/abs/2305.06104
- Zhang, et al. "HANCL" — few-shot link prediction on n-ary facts, 2022. `[unverified]` — cited via Wei et al. 2025.
- Hou, Z., Jin, X., Li, Z., Bai, L., Guan, S., Zeng, Y., Guo, J., Cheng, X. "Temporal Knowledge Graph Reasoning Based on N-tuple Modeling" (NE-Net, NWIKI, NICE). *Findings of EMNLP 2023*. https://doi.org/10.18653/v1/2023.findings-emnlp.77
- Ding, Z., Wu, Jingcheng, Wu, Jingpei, Xia, Y., Tresp, V. "Temporal Fact Reasoning over Hyper-Relational Knowledge Graphs" (HypeTKG, Wiki-hy, YAGO-hy). Findings of EMNLP 2024; arXiv:2307.10219. https://arxiv.org/abs/2307.10219
- Behrouz, A., Hashemi, F., Sadeghian, S., Seltzer, M. "CAT-Walk: Inductive Hypergraph Learning via Set Walks." NeurIPS 2023; arXiv:2306.11147. https://arxiv.org/abs/2306.11147
- Mancastroppa, M., Iacopini, I., Petri, G., Barrat, A. "The structural evolution of temporal hypergraphs through the lens of hyper-cores." *EPJ Data Science* 13:50, 2024; arXiv:2402.06485. https://arxiv.org/abs/2402.06485
- Mancastroppa, M., Cencetti, G., Barrat, A. "Emerging Activity Temporal Hypergraph: a model for generating realistic time-varying hypergraphs." *Physical Review E* 112, 054305, 2025; arXiv:2507.01124. https://arxiv.org/abs/2507.01124
- Liu, H., Jiao, P., Gao, M., Chen, C., Jin, D. "Heterogeneous Temporal Hypergraph Neural Network." IJCAI 2025; arXiv:2506.17312. https://arxiv.org/abs/2506.17312
- Liu, Y., Ma, J., Li, P. "Neural Predicting Higher-order Patterns in Temporal Networks." arXiv:2106.06039, 2021. https://arxiv.org/abs/2106.06039

## LLMs and knowledge hypergraphs

- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., Feng, Y., Kuang, Z., Song, M., Zhu, Y., Tuan, L. A. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025; arXiv:2503.21322. https://arxiv.org/abs/2503.21322 · code https://github.com/LHRLAB/HyperGraphRAG
- Feng, Y., Hu, H., Hou, X., Liu, S., Ying, S., Du, S., Hu, H., Gao, Y. "Hyper-RAG: Combating LLM Hallucinations using Hypergraph-Driven Retrieval-Augmented Generation." arXiv:2504.08758, 2025; *Nature Communications*, 27 April 2026. https://arxiv.org/abs/2504.08758 · https://doi.org/10.1038/s41467-026-71411-1 · code https://github.com/iMoonLab/Hyper-RAG
- Zai, X., Tan, X., Wang, X., Liu, Q., Xu, X., Zhang, W. "PRoH: Dynamic Planning and Reasoning over Knowledge Hypergraphs for Retrieval-Augmented Generation." The Web Conference 2026; arXiv:2510.12434. https://arxiv.org/abs/2510.12434
- Lien, W.-S., Chan, Y.-K., Hsiao, H.-L., Ruan, B.-K., Chiang, M.-F., Chen, C.-A., Yeh, Y.-R., Shuai, H.-H. "HyperRAG: Reasoning N-ary Facts over Hypergraphs for Retrieval Augmented Generation." The Web Conference 2026; arXiv:2602.14470. https://arxiv.org/abs/2602.14470
- Park, J., Lee, S., Khan, O. Z., Kim, H. J., Kim, J.-K. "HyperGraphPro: Progress-Aware Reinforcement Learning for Structure-Guided Hypergraph RAG." arXiv:2601.17755, 2026. https://arxiv.org/abs/2601.17755
- Wang, C., Deng, W., Guan, W., Lu, Q., Jiang, N. "Cross-Granularity Hypergraph Retrieval-Augmented Generation for Multi-hop Question Answering." arXiv:2508.11247, 2025. https://arxiv.org/abs/2508.11247
- Yue, J., Hu, C., Sheng, J., Zhou, Z., Zhang, W., Liu, T., Guo, L., Deng, Y. "HyperMem: Hypergraph Memory for Long-Term Conversations." ACL 2026 main; arXiv:2604.08256. https://arxiv.org/abs/2604.08256
- Lei, M., Xie, G., Ying, S., Du, S., Yong, J.-H., Shi, C., Tian, L., Li, S., Gao, Y. "Hypergraph as Language." arXiv:2605.21858, 21 May 2026 (v2, 15 August 2026). https://arxiv.org/abs/2605.21858
- Huang, S., Li, H., Gu, Y., Hu, X., Li, Q., Xu, G. "HyperG: Hypergraph-Enhanced LLMs for Structured Knowledge." arXiv:2502.18125, 2025. https://arxiv.org/abs/2502.18125
- "HyperGVL: Benchmarking and Improving Large Vision-Language Models in Hypergraph Understanding and Reasoning." arXiv:2604.15648, 2026. https://arxiv.org/abs/2604.15648 `[unverified]` — author list not confirmed.
- Kosten, C., Cudré-Mauroux, P., Stockinger, K. "Spider4SPARQL: A Complex Benchmark for Evaluating Knowledge Graph Question Answering Systems." IEEE BigData 2023; arXiv:2309.16248. https://arxiv.org/abs/2309.16248
- Diallo, P. A. K. K., Reyd, S., Zouaq, A. "A Comprehensive Evaluation of Neural SPARQL Query Generation from Natural Language Questions." arXiv:2304.07772, 2023. https://arxiv.org/abs/2304.07772
- Sharma, A., Pal, C. J., Zouaq, A. "Reducing Hallucinations in Language Model-based SPARQL Query Generation Using Post-Generation Memory Retrieval." arXiv:2502.13369, 2025. https://arxiv.org/abs/2502.13369

## Explainability, uncertainty, calibration

- Chen, X., Chen, M., Shi, W., Sun, Y., Zaniolo, C. "Embedding Uncertain Knowledge Graphs." *AAAI 2019*. https://doi.org/10.1609/aaai.v33i01.33013363
- Tabacof, P., Costabello, L. "Probability Calibration for Knowledge Graph Embedding Models." ICLR 2020; arXiv:1912.10000. https://arxiv.org/abs/1912.10000
- Ying, R., Bourgeois, D., You, J., Zitnik, M., Leskovec, J. "GNNExplainer: Generating Explanations for Graph Neural Networks." NeurIPS 2019; arXiv:1903.03894. https://arxiv.org/abs/1903.03894

## Added in gap-filling pass (2026-09-20)

Sources for [`reproducibility-of-n-ary-link-prediction.md`](../../kb/05-query-embeddings-reasoning/reproducibility-of-n-ary-link-prediction.md).
GitHub figures were read from repository pages and Atom commit feeds fetched on 2026-09-20 (the
GitHub REST API was not reachable from this session).

### Replication and re-evaluation studies (triples)

- Ruffinelli, D., Broscheit, S., Gemulla, R. "You CAN Teach an Old Dog New Tricks! On Training Knowledge Graph Embeddings." ICLR 2020. https://dblp.org/rec/conf/iclr/RuffinelliBG20.html
- Ali, M., Berrendorf, M., Hoyt, C. T., Vermue, L., Galkin, M., Sharifzadeh, S., Fischer, A., Tresp, V., Lehmann, J. "Bringing Light Into the Dark: A Large-Scale Evaluation of Knowledge Graph Embedding Models Under a Unified Framework." IEEE TPAMI, 2021/2022; 21 models, four datasets, 24,804 GPU hours. https://doi.org/10.1109/TPAMI.2021.3124805 ; benchmarking code https://github.com/pykeen/benchmarking
- Ali, M. et al. "PyKEEN 1.0: A Python Library for Training and Evaluating Knowledge Graph Embeddings." arXiv 2007.14175. https://arxiv.org/abs/2007.14175

### The nearest n-ary equivalent

- Wang, Y., Di, S., Wang, Z., Li, H., Teng, F., Xin, H., Chen, L. "Understanding the Embedding Models on Hyper-relational Knowledge Graph." CIKM 2025 / arXiv 2508.03280, 5 August 2025. Three decompositions of HKGs to KG format; "some KGE models achieve performance comparable to that of HKGE models"; proposes FormerGNN. https://arxiv.org/abs/2508.03280

### Framework support (checked 2026-09-20)

- PyKEEN model reference documentation — all models documented as scoring a triple (h, r, t); no qualifier or n-ary model listed. https://pykeen.readthedocs.io/en/stable/reference/models.html
- LibKGE (uma-pi1/kge) — 835 stars, MIT, 1,325 commits, not archived; README describes triple-based KGE only. https://github.com/uma-pi1/kge

### Code audit of the section-05 model table (all checked 2026-09-20)

- gsp2014/NaLP — exists; 14 stars, 5 forks, 22 commits, no licence stated. https://github.com/gsp2014/NaLP
- eXascaleInfolab/HINGE_code — exists; 38 stars, 12 forks, 11 commits, no licence stated; last commit 2020-07-15. https://github.com/eXascaleInfolab/HINGE_code
- ServiceNow/HypE — exists; 33 stars, 11 forks, 33 commits, GPL-3.0; last commit 2022-07-15. https://github.com/ServiceNow/HypE
- baharefatemi/HypE — exists; 24 stars, 12 forks, 31 commits, GPL-3.0. https://github.com/baharefatemi/HypE
- liuyuaa/GETD — exists; 11 stars, 2 forks, **1 commit**, MIT; last commit 2020-01-17. https://github.com/liuyuaa/GETD
- migalkin/StarE — exists; 90 stars, 16 forks, 26 commits, MIT; last commit 2023-12-01. https://github.com/migalkin/StarE
- PaddlePaddle/Research, `KG/ACL2021_GRAN` — exists; Apache-2.0; ships code and a `download_data.sh` for JF17K, WikiPeople and the -3/-4 subsets. https://github.com/PaddlePaddle/Research/tree/master/KG/ACL2021_GRAN
- DimitrisAlivas/StarQE — exists; 33 stars, 4 forks, 10 commits, MIT. https://github.com/DimitrisAlivas/StarQE
- LHRLAB/HAHE — exists; 28 stars, 31 commits, MIT; last commit 2025-08-18. https://github.com/LHRLAB/HAHE
- xiongbo010/ShrinkE — exists; 6 stars, 0 forks, 17 commits, no licence stated; last commit 2024-07-05. https://github.com/xiongbo010/ShrinkE
- bdi-lab/HyNT — exists; 36 stars, 20 forks, 39 commits, **CC BY-NC-SA 4.0**; last commit 2025-05-27. https://github.com/bdi-lab/HyNT
- LHRLAB/Text2NKG — exists; 37 stars, 5 forks, 91 commits, MIT. https://github.com/LHRLAB/Text2NKG
- zhiweihu1103/HKGC-HyperMono — exists; 0 stars, 0 forks, 21 commits, no licence stated. https://github.com/zhiweihu1103/HKGC-HyperMono
- HxyScotthuang/HYPER — exists; 21 stars, 2 forks, 6 commits, MIT; last commit 2026-03-25; README states ICLR 2026 and notes HCNet inference support. https://github.com/HxyScotthuang/HYPER
- `[unverified]` No public implementation located on 2026-09-20 for m-TransH, RAE, NeuInfer, S2S, THOR or FormerGNN.

### Supporting

- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. "A Survey of Link Prediction in N-ary Knowledge Graphs." EMNLP 2025 / arXiv 2506.08970. Table 2 figures are copied from Di et al. 2021 and Luo et al. 2023, not re-run. https://arxiv.org/abs/2506.08970
- Lu, X., Tupikina, L., Alam, M. "Two-Dimensional Taxonomy for n-Ary Knowledge Representation Learning Methods." IEEE TKDE 2026 / arXiv 2506.05626. https://arxiv.org/abs/2506.05626
- Gebru, T., Morgenstern, J., Vecchione, B., Wortman Vaughan, J., Wallach, H., Daumé III, H., Crawford, K. "Datasheets for Datasets." CACM 64(12), December 2021 / arXiv 1803.09010. https://doi.org/10.1145/3458723
- Yu, W., Lu, Y., Yang, D. "THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs." arXiv 2602.05424, 5 February 2026. https://arxiv.org/abs/2602.05424

## Added in run 02 (2026-09-21) — HYPER anatomy, HCNet, and the binary KGFM precursors

### HYPER (venue settled: ICLR 2026)

- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. "HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs." **ICLR 2026**. arXiv:2506.12362 — v1 14 Jun 2025, v2 13 Feb 2026, **v3 8 May 2026 (cite this one)**. https://arxiv.org/abs/2506.12362 ; v3 HTML https://arxiv.org/html/2506.12362v3
  - Venue confirmed 2026-09-21: the OpenReview PDF at https://openreview.net/pdf?id=YLTQbMoAaX carries the header "Published as a conference paper at ICLR 2026"; the repository BibTeX gives `booktitle={International Conference on Learning Representations}, year={2026}`. The OpenReview HTML and api2 endpoints were behind a bot challenge on that date, so the forum page itself could not be read directly. The NeurIPS 2025 "New Perspectives in Graph Machine Learning" workshop appearance (https://neurips.cc/virtual/2025/127653) is a separate, earlier event.
  - **Numbers changed between v1 and v3.** v1 Table 2 (node-inductive) ULTRA†(50KG) = 0.346 / 0.286 / 0.149; v3 Table 3 ULTRA‡(50KG) = 0.007 / 0.029 / 0.026. v1 Table 1 ULTRA†(50KG) at the 100% columns = 0.111 / 0.262 / 0.065 / 0.150; v3 Table 2 = 0.001 / 0.190 / 0.004 / 0.001. v1: ULTRA(50KG) "performs only marginally better than the version trained on just 3"; v3: "performs much worse". HYPER's own rows are unchanged. v3 also adds ULTRA‡(4HG) and ULTRA‡(3KG+2HG) baselines and a second reification scheme (†).
  - Key v3 locations: Table 1 capability matrix (§2); relation graph and `Enc_PI` (§4); Theorem 4.1 informal, formalised as Theorem C.2 with Proposition C.1 (equivariance) in Appendix C; sparse-matmul relation-graph construction in Appendix B; compute (single H100, 4 days pretraining; Triton kernel halving time and cutting memory ~5×, O(k|E|) → O(|V|)) in Appendix D; complexity and the FB15k-237 scalability table (ULTRA 1.19 s/batch, 12.87 GB; HCNet 2.64, 18.03; HYPER 4.51, 25.30; 225,409 parameters) in Appendix F; architecture, training objective and the KG-ICL comparison in Appendix G.
- HYPER implementation, checked 2026-09-21 by direct fetch: https://github.com/HxyScotthuang/HYPER — MIT; README states ICLR 2026; **three public checkpoints** `ckpts/HYPER-3KG.pth` (2,833,802 B), `HYPER-4HG.pth` (2,834,222 B), `HYPER-3KG+2HG.pth` (2,833,802 B); **datasets shipped in-repo** under `hypergraph_dataset/` (verified `JF-100/train.txt` 148,593 B, `JF-IND/train.txt` 95,639 B, `JF17K/train.txt` 3,368,397 B); Triton `rspmm` at `hyper/rspmm/triton_rspmm.py` (class `HyperRelConvSumAggr`), enabled via `use_triton` (Python default `False`, but `config/pretrain/pretrain_3KG+2HG.yaml` sets `use_triton: yes` for both encoders); engine acknowledged as adapted from the ULTRA PyG implementation.

### Neural substrate

- Huang, X., Romero Orth, M., Barceló, P., Bronstein, M. M., Ceylan, İ. İ. "Link Prediction with Relational Hypergraphs" (HC-MPNN / HCNet). *Transactions on Machine Learning Research*, 2025 (repository states TMLR 2025/05). arXiv:2402.04062, v3 9 Jun 2025. https://arxiv.org/abs/2402.04062 ; code https://github.com/HxyScotthuang/HC-MPNN
  - HCNet message: `σ(W⁽ˡ⁾[h⁽ˡ⁾_{v|q} ‖ Σ_{(e,i)∈E(v)} g_{ρ(e),q}⁽ˡ⁾(⊙_{j≠i}(α⁽ˡ⁾h⁽ˡ⁾_{e(j)|q} + (1−α⁽ˡ⁾)p_j))] + b⁽ˡ⁾)`, α a learnable scalar, p_j sinusoidal.
  - §6.3: HCNet is evaluated **without inverse-relation augmentation** and still reaches the top 3 on 7 of 8 GraIL splits; "Theorem G.4 implies that all current models based on conditional message passing, including NBFNets, need inverse relation augmentation to match the expressive power of HCNet".

### Binary KG foundation-model precursors

- Cui, Y., Sun, Z., Hu, W. "A Prompt-Based Knowledge Graph Foundation Model for Universal In-Context Reasoning" (KG-ICL). *NeurIPS 2024*; arXiv:2410.12288. Prompt graph centred on a query-related example fact, unified tokeniser, two MPNNs; 43 KGs, transductive and inductive. https://arxiv.org/abs/2410.12288 ; code and datasets https://github.com/nju-websoft/KG-ICL (released 2024-10-14; uses the same `rspmm` kernel family, `use_rspmm` defaulted to False on 2025-03-22). In HYPER v3 Table 12, zero-shot average MRR over the 16 new datasets: KG-ICL 4/5/6-layer = 0.139 / 0.048 / 0.143, against HYPER (3KG+2HG) 0.236 and ULTRA‡ (3KG+2HG) 0.183; KG-ICL's own pretraining mix is FB-v1, NL-v1, CoDEx-Small.
- Galkin, M., Yuan, X., Mostafa, H., Tang, J., Zhu, Z. "Towards Foundation Models for Knowledge Graph Reasoning" (ULTRA). *ICLR 2024*; arXiv:2310.04562. https://arxiv.org/abs/2310.04562
- Lee, J., Chung, C., Whang, J. J. "InGram: Inductive Knowledge Graph Embedding via Relation Graphs." *ICML 2023*; arXiv:2305.19987. Source of the relation graph and of HYPER's 25/50/75/100% unseen-relation split protocol. https://arxiv.org/abs/2305.19987
- Zhu, Z., Zhang, Z., Xhonneux, L.-P., Tang, J. "Neural Bellman-Ford Networks: A General Graph Neural Network Framework for Link Prediction" (NBFNet). *NeurIPS 2021*; arXiv:2106.06935. https://arxiv.org/abs/2106.06935
- Zhu, Z., Yuan, X., Galkin, M., Xhonneux, S., Zhang, M., Gazeau, M., Tang, J. "A*Net: A Scalable Path-based Reasoning Approach for Knowledge Graphs." *NeurIPS 2023*; arXiv:2206.04798. https://arxiv.org/abs/2206.04798
- Teru, K. K., Denis, E., Hamilton, W. L. "Inductive Relation Prediction by Subgraph Reasoning" (GraIL). *ICML 2020*; arXiv:1911.06962. https://arxiv.org/abs/1911.06962
- Yadati, N. "Neural Message Passing for Multi-Relational Ordered and Recursive Hypergraphs" (G-MPNN). *NeurIPS 2020*. https://proceedings.neurips.cc/paper/2020/hash/217eedd1ba8c592db97d0dbe54c7adfc-Abstract.html ; code https://github.com/naganandy/G-MPNN-R

### Training-objective ancestry

- Sun, Z., Deng, Z.-H., Nie, J.-Y., Tang, J. "RotatE: Knowledge Graph Embedding by Relational Rotation in Complex Space." *ICLR 2019*; arXiv:1902.10197. Source of the self-adversarial negative-sampling loss HYPER optimises (512 negatives in pretraining, 256 for fine-tuning; adversarial temperature 1). https://arxiv.org/abs/1902.10197
- Galárraga, L. A., Teflioudi, C., Hose, K., Suchanek, F. "AMIE: Association Rule Mining under Incomplete Evidence in Ontological Knowledge Bases." *WWW 2013*. Source of the partial completeness assumption under which HYPER masks one slot per k-ary fact. https://doi.org/10.1145/2488388.2488425

### n-ary pretraining corpora (the whole supply, as of 2026-09-21)

- HYPER v3 Table 16 gives the only n-ary pretraining corpora anyone has used: M-FB15K (415,375 train facts, max arity 5), WikiPeople (305,725, max arity 9), JF17K (61,104, max arity 6), FB-AUTO (6,778, max arity 5). The best checkpoint (3KG+2HG) sees ≈0.91 M facts in total, of which the higher-arity part is on the order of 90 k. No larger n-ary corpus was located on 2026-09-21.

## Added in run 02 (2026-09-21) — temporal n-ary models, interpolation vs extrapolation

- Un, C., Lu, Y., Yang, T., Yang, D. "VITA: Versatile Time Representation Learning for Temporal Hyper-Relational Knowledge Graphs." arXiv:2505.11803, 17 May 2025. https://arxiv.org/abs/2505.11803
- Hou, Z., Su, M., Jin, X., Li, Z., Bai, L., Guo, J., Cheng, X. "Mixture Policy based Multi-Hop Reasoning over N-tuple Temporal Knowledge Graphs" (MT-Path). arXiv:2505.12788, 19 May 2025. https://arxiv.org/abs/2505.12788
- Ahrabian, K., Boxer, E., Pujara, J. "Toward Better Temporal Structures for Geopolitical Events Forecasting" (HTKGH, htkgh-polecat). arXiv:2601.00430, 1 January 2026 (v2, 17 March 2026). https://arxiv.org/abs/2601.00430
- Wang, J., Wang, B., Qiu, M., Pan, S., Xiong, B., Liu, H., Luo, L., Liu, T., Hu, Y., Yin, B., Gao, W. "A Survey on Temporal Knowledge Graph Completion: Taxonomy, Progress, and Prospects." arXiv:2308.02457, 4 August 2023. https://arxiv.org/abs/2308.02457
- Trivedi, R., Dai, H., Wang, Y., Song, L. "Know-Evolve: Deep Temporal Reasoning for Dynamic Knowledge Graphs." arXiv:1705.05742, 2017. https://arxiv.org/abs/1705.05742
- Han, Z., Ding, Z., Ma, Y., Gu, Y., Tresp, V. "Learning Neural Ordinary Equations for Forecasting Future Links on Temporal Knowledge Graphs" (TANGO). EMNLP 2021, pp. 8352–8364. https://aclanthology.org/2021.emnlp-main.658/

## Added in run 02 (2026-09-21) — geometry and algebraic interfaces

### Hyperbolic / multi-curvature models for n-ary facts

- Yan, S., Zhang, Z., Sun, X., Xu, G., Jin, L., Li, S. "HYPER²: Hyperbolic embedding for hyper-relational link prediction." *Neurocomputing* 492:440–451, July 2022. DOI 10.1016/j.neucom.2022.04.026. Preprint: "HYPER^2: Hyperbolic Poincare Embedding for Hyper-Relational Link Prediction", arXiv:2104.09871, 20 April 2021. Verified via Crossref and the arXiv API on 2026-09-21 (supersedes the earlier `[unverified]` entry). https://arxiv.org/abs/2104.09871
- Yan, S., Zhang, Z., Sun, X., Xu, G., Li, S., Liu, Q., Liu, N., Wang, S. "PolygonE: Modeling N-ary Relational Data as Gyro-Polygons in Hyperbolic Space." *Proceedings of the AAAI Conference on Artificial Intelligence* 36(4):4308–4317, 2022. DOI 10.1609/aaai.v36i4.20351. Verified via the AAAI OJS record and Crossref on 2026-09-21 (supersedes the earlier `[unverified]` entry). https://doi.org/10.1609/aaai.v36i4.20351 · PDF https://cdn.aaai.org/ojs/20351/20351-13-24364-1-2-20220628.pdf
- Yan, S., Zhang, Z., Xu, G., Sun, X., Li, S., Wang, S. "Modeling N-ary relational data as gyro-polygons with learnable gyro-centroid." *Knowledge-Based Systems* 251:109164, September 2022. DOI 10.1016/j.knosys.2022.109164. This is the paper the literature refers to as "WPolygonE+". Verified via Crossref on 2026-09-21 (supersedes the earlier `[unverified]` entry). https://doi.org/10.1016/j.knosys.2022.109164
- Li, M., Shi, X., Qiao, C., Zhang, T., Jin, H. "Hyperbolic Hypergraph Neural Networks for Multi-Relational Knowledge Hypergraph Representation" (H²GNN). arXiv:2412.12158, 11 December 2024. Preprint only: one version, no journal reference, no DOI and no code repository named, as of 2026-09-21. Hyper-star message passing (position-typed star expansion) plus Lorentz-space aggregation; node classification on DBLP/Cora/PubMed/Citeseer, link prediction on JF17K and FB-AUTO. https://arxiv.org/abs/2412.12158
- Cao, Z., Xu, Q., Yang, Z., He, Y., Cao, X., Huang, Q. "GAHE: Geometry-aware embedding for hyper-relational knowledge graph representation." *ACM Transactions on Multimedia Computing, Communications and Applications*, 2025. Multi-curvature (Euclidean + hyperbolic + spherical) position-aware tensor factorisation. `[unverified]` — bibliographic details taken from the reference list of Lu, Tupikina and Alam 2026; full text not read.

### ReAlE and the relational-algebra interface

- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraph Embedding Meets Relational Algebra" (ReAlE). *Journal of Machine Learning Research* 24(105):1–34, 2023; ICML 2023 journal-track poster (https://icml.cc/virtual/2023/poster/25671); preprint arXiv:2102.09557, 18 February 2021. The published venue, not previously recorded in this KB. Primitives represented: renaming, projection, set union, selection, **set difference** (not join; Cartesian product is not claimed). https://www.jmlr.org/papers/v24/22-063.html · https://arxiv.org/abs/2102.09557
- Patel, L., Jha, S., Pan, M., Gupta, H., Asawa, P., Guestrin, C., Zaharia, M. "Semantic Operators: A Declarative Model for Rich, AI-based Data Processing." arXiv:2407.11418. Journal version: "Semantic Operators and Their Optimization", *PVLDB* 18, pp. 4171ff. Implemented in the LOTUS engine, https://github.com/lotus-data/lotus. Relational-algebra-shaped operators (sem_filter, sem_join, sem_agg, sem_topk) over tables with natural-language predicates; the closest existing analogue to an algebraic planner interface, but not over an embedding store or n-ary facts. https://arxiv.org/abs/2407.11418 · https://www.vldb.org/pvldb/vol18/p4171-patel.pdf

### Taxonomy and adjacent geometry

- Lu, X., Tupikina, L., Alam, M. "Two-dimensional Taxonomy for N-ary Knowledge Representation Learning Methods." *IEEE Transactions on Knowledge and Data Engineering*, accepted 29 August 2026 (manuscript received 27 June 2025, revised 8 June 2026); author's accepted manuscript, 20 pp.; arXiv:2506.05626 v3. Axis labels verified from v3: methodology (translation / tensor factorisation / deep neural network / logic rule / hyperedge expansion) × semantic awareness (position-aware / role-aware / **aware-less**). Table II covers 49 models. https://arxiv.org/abs/2506.05626
- Xin, L., Nayyeri, M., Makki Nayeri, Z., Staab, S. "Geometric Structural Knowledge Graph Foundation Model." arXiv:2512.22931, 28 December 2025. Geometry (real / complex / split-complex / dual transformations) combined with an ULTRA-style relation graph — binary knowledge graphs only, not hyperbolic. `[unverified]` beyond the abstract. https://arxiv.org/abs/2512.22931

### Absence claims, dated 2026-09-21

- arXiv API full-text search (`export.arxiv.org/api/query`): `"knowledge hypergraph" AND hyperbolic` → 1 result (H²GNN, 2412.12158); `"hyper-relational" AND hyperbolic` → 3 (H²GNN, HYPER², NestE 2312.09219); `"n-ary" AND hyperbolic` → 1 (HYPER²); `"relational hypergraph" AND "foundation model"` → 0. No paper combines hyperbolic geometry with a HYPER/ULTRA-style relation graph over knowledge hypergraphs.
- No δ-hyperbolicity / Gromov-hyperbolicity measurement published for JF17K, FB-AUTO, M-FB15K, WikiPeople or WD50K; none of the five hyperbolic n-ary papers reports one.
- No system located that exposes relational-algebra primitives over a knowledge-hypergraph embedding store as planner-callable operations for an LLM. Nearest neighbours: LOTUS semantic operators (tables, not embeddings), StarQE/NQE/SQE/LKHGT (operators internal to the model), agentic GraphRAG frameworks (topological, not algebraic actions).
- Lu, Tupikina and Alam 2026 (v3) does not index HCNet, HART, THOR, HYPER², PolygonE or the gyro-centroid follow-up; "gyro" does not occur in the paper.
