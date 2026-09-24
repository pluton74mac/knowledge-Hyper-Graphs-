# P6 schema width survey

| row | source | naming | slots | relations / roles | class (witness) | core (relations / roles) | hw | ghw | fhw | tw |
|---|---|---|---|---|---|---|---|---|---|---|
| wd-declared-wd-roles-r1-cq | wikidata | wd-roles-r1 | core,qualifier | 1155 / 1892 | cyclic (gyo_residue 391) | 391 / 578 | [4, 38] | [4, 25] | [35/11, 24] | [116, 235] |
| wd-declared-wd-roles-r1-cqt | wikidata | wd-roles-r1 | core,qualifier,time | 1155 / 1893 | cyclic (gyo_residue 392) | 392 / 580 | [4, 43] | [4, 25] | [35/11, 24] | [118, 237] |
| wd-declared-relation-local-cq | wikidata | relation-local | core,qualifier | 1155 / 9999 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 116 |
| wd-declared-relation-local-cqt | wikidata | relation-local | core,qualifier,time | 1155 / 10815 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 118 |
| wd-observed-robust-wd-roles-r1-cq | wikidata dump | wd-roles-r1 | core,qualifier | 13608 / 13677 | cyclic (gyo_residue 748) | 748 / 527 | [4, 68] | [4, 29] | [63/19, 79/3] | [55, 131] |
| wd-observed-robust-wd-roles-r1-cqt | wikidata dump | wd-roles-r1 | core,qualifier,time | 13608 / 13677 | cyclic (gyo_residue 755) | 755 / 530 | [4, 71] | [4, 32] | [63/19, 1015/36] | [56, 134] |
| wd-observed-robust-relation-local-cq | wikidata dump | relation-local | core,qualifier | 13608 / 34472 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 33 |
| wd-observed-robust-relation-local-cqt | wikidata dump | relation-local | core,qualifier,time | 13608 / 36084 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 35 |
| wd-observed-all-wd-roles-r1-cq | wikidata dump | wd-roles-r1 | core,qualifier | 13608 / 14158 | cyclic (gyo_residue 1441) | 1441 / 1984 | [3, 61] | [3, 39] | [2, 75/2] | [760, 1248] |
| wd-observed-all-wd-roles-r1-cqt | wikidata dump | wd-roles-r1 | core,qualifier,time | 13608 / 14158 | cyclic (gyo_residue 1446) | 1446 / 1987 | [3, 61] | [3, 39] | [11/5, 75/2] | [762, 1195] |
| wd-observed-all-relation-local-cq | wikidata dump | relation-local | core,qualifier | 13608 / 83426 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 760 |
| wd-observed-all-relation-local-cqt | wikidata dump | relation-local | core,qualifier,time | 13608 / 87772 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 762 |
| biolink-formal-global-cq | biolink | global | core,qualifier | 103 / 35 | cyclic (gyo_residue 5) | 5 / 8 | 2 | 2 | 2 | 19 |
| biolink-formal-domain-global-cq | biolink | global | core,qualifier | 103 / 60 | cyclic (gyo_residue 5) | 5 / 8 | 2 | 2 | 2 | 23 |
| biolink-formal-relation-local-cq | biolink | relation-local | core,qualifier | 103 / 1020 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 19 |
| hyperbench-cq | HyperBench (Zenodo 10.5281/zenodo.7180787) | n/a | n/a | 1113 CQs | selected to be cyclic | n/a | hw 1 / 2 / 3 = 673 / 432 / 8 | | | |

Values are exact (`2`) or bounds (`[2, 4]`, `(1, 3/2]` for fhw > 1). The HyperBench row counts non-random CQs, which were selected to be cyclic; compare by structural parameter and hw (R01 §3.6).
