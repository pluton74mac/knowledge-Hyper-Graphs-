# P6 schema width survey

| row | source | naming | slots | relations / roles | class (witness) | core (relations / roles) | hw | ghw | fhw | tw |
|---|---|---|---|---|---|---|---|---|---|---|
| wd-declared-wd-roles-r1-cq | wikidata | wd-roles-r1 | core,qualifier | 1155 / 1892 | cyclic (gyo_residue 391) | 391 / 578 | [4, 38] | [4, 25] | [35/11, 24] | [116, 235] |
| wd-declared-wd-roles-r1-cqt | wikidata | wd-roles-r1 | core,qualifier,time | 1155 / 1893 | cyclic (gyo_residue 392) | 392 / 580 | [4, 43] | [4, 25] | [35/11, 24] | [118, 237] |
| wd-declared-relation-local-cq | wikidata | relation-local | core,qualifier | 1155 / 9999 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 116 |
| wd-declared-relation-local-cqt | wikidata | relation-local | core,qualifier,time | 1155 / 10815 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 118 |
| wd-observed-robust-wd-roles-r1-cq | wikidata dump | wd-roles-r1 | core,qualifier | 13315 / 13391 | cyclic (gyo_residue 751) | 751 / 530 | [4, 65] | [4, 30] | [75/23, 53/2] | [55, 139] |
| wd-observed-robust-wd-roles-r1-cqt | wikidata dump | wd-roles-r1 | core,qualifier,time | 13315 / 13391 | cyclic (gyo_residue 767) | 767 / 539 | [4, 60] | [4, 30] | [75/23, 185/7] | [57, 140] |
| wd-observed-robust-relation-local-cq | wikidata dump | relation-local | core,qualifier | 13315 / 34050 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 34 |
| wd-observed-robust-relation-local-cqt | wikidata dump | relation-local | core,qualifier,time | 13315 / 38436 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 36 |
| wd-observed-all-wd-roles-r1-cq | wikidata dump | wd-roles-r1 | core,qualifier | 13315 / 13886 | cyclic (gyo_residue 1453) | 1453 / 1998 | [3, 53] | [3, 35] | [2, 269/8] | [771, 1226] |
| wd-observed-all-wd-roles-r1-cqt | wikidata dump | wd-roles-r1 | core,qualifier,time | 13315 / 13886 | cyclic (gyo_residue 1458) | 1458 / 2001 | [3, 52] | [3, 35] | [11/5, 269/8] | [773, 1228] |
| wd-observed-all-relation-local-cq | wikidata dump | relation-local | core,qualifier | 13315 / 83572 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 771 |
| wd-observed-all-relation-local-cqt | wikidata dump | relation-local | core,qualifier,time | 13315 / 87958 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 773 |
| wd-observed-robust-slice-wd-roles-r1-cq | wikidata slice | wd-roles-r1 | core,qualifier | 12706 / 12810 | cyclic (gyo_residue 603) | 603 / 460 | [4, 48] | [4, 26] | [7/2, 250/11] | [51, 114] |
| wd-observed-robust-slice-wd-roles-r1-cqt | wikidata slice | wd-roles-r1 | core,qualifier,time | 12706 / 12810 | cyclic (gyo_residue 613) | 613 / 466 | [4, 59] | [4, 26] | [7/2, 114/5] | [53, 116] |
| wd-observed-robust-slice-relation-local-cq | wikidata slice | relation-local | core,qualifier | 12706 / 31572 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 36 |
| wd-observed-robust-slice-relation-local-cqt | wikidata slice | relation-local | core,qualifier,time | 12706 / 35006 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 38 |
| wd-observed-all-slice-wd-roles-r1-cq | wikidata slice | wd-roles-r1 | core,qualifier | 12706 / 13189 | cyclic (gyo_residue 1292) | 1292 / 1558 | [4, 51] | [4, 36] | [8/3, 143/4] | [452, 838] |
| wd-observed-all-slice-wd-roles-r1-cqt | wikidata slice | wd-roles-r1 | core,qualifier,time | 12706 / 13189 | cyclic (gyo_residue 1297) | 1297 / 1560 | [4, 47] | [4, 36] | [8/3, 34] | [452, 852] |
| wd-observed-all-slice-relation-local-cq | wikidata slice | relation-local | core,qualifier | 12706 / 62641 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 410 |
| wd-observed-all-slice-relation-local-cqt | wikidata slice | relation-local | core,qualifier,time | 12706 / 66075 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 412 |
| biolink-formal-global-cq | biolink | global | core,qualifier | 103 / 35 | cyclic (gyo_residue 5) | 5 / 8 | 2 | 2 | 2 | 19 |
| biolink-formal-domain-global-cq | biolink | global | core,qualifier | 103 / 60 | cyclic (gyo_residue 5) | 5 / 8 | 2 | 2 | 2 | 23 |
| biolink-formal-relation-local-cq | biolink | relation-local | core,qualifier | 103 / 1020 | berge (join tree) | 0 / 0 | 1 | 1 | 1 | 19 |
| hyperbench-cq | HyperBench (Zenodo 10.5281/zenodo.7180787) | n/a | n/a | 1113 CQs | biased toward cyclic | n/a | hw 1 / 2 / 3 = 673 / 432 / 8 | | | |

Values are exact (`2`) or bounds (`[2, 4]`, `(1, 3/2]` for fhw > 1). The HyperBench row counts non-random CQs, a collection biased toward cyclic queries (673 of them still have hw 1); compare by structural parameter and hw (R01 §3.6).
