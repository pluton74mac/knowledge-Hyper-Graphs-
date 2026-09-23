| MC01 | zero-byte file (R02 case 34) | J | `KHG-J001` |
| MC02 | not JSON: truncated document | J | `KHG-J001` |
| MC03 | duplicate key inside one attrs object (R02 case 36) | J | `KHG-J003` |
| MC04 | NaN literal (R02 case 35, R03 c22, R01 V19) | J | `KHG-J004` |
| MC05 | lone surrogate escape in a string | J | `KHG-J005` |
| MC06 | no incidences (R01 V01, R02 case 31) | H | `KHG-H001` |
| MC07 | top-level 'version' key (R01 V02, R02 case 04) | H | `KHG-H002` |
| MC08 | top-level 'roles' vocabulary (R02 case 05) | H | `KHG-H002` |
| MC09 | top-level '$schema' (R02 case 06) | H | `KHG-H002` |
| MC10 | record-level 'role' on an incidence (R01 V03, R02 case 11) | H | `KHG-H003` |
| MC11 | record-level 'relation' on an edge (R02 case 13) | H | `KHG-H003` |
| MC12 | record-level 'type' on a node (R02 case 14) | H | `KHG-H003` |
| MC13 | incidence attrs is a string (R02 case 10) | H | `KHG-H004` |
| MC14 | direction 'treatment' (R01 V05, R02 case 12) | H | `KHG-H005` |
| MC15 | incidence without node (R01 V04) | H | `KHG-H006` |
| MC16 | id of type float 1.5 (R02 case 18) | H | `KHG-H007` |
| MC17 | id of type boolean (R02 case 19) | H | `KHG-H007` |
| MC18 | id null (R02 case 20) | H | `KHG-H007` |
| MC19 | network-type 'knowledge-hypergraph' (R02 case 26) | H | `KHG-H008` |
| MC20 | metadata without the khg-profile declaration (R01 V07) | P | `KHG-P001` |
| MC21 | no metadata at all | P | `KHG-P001` |
| MC22 | integer ids (R02 cases 15-17, 22) | P | `KHG-P002` |
| MC23 | empty-string id (R02 case 21) | P | `KHG-P003` |
| MC24 | incidence of a fact without a role (R01 V08) | P | `KHG-P005` |
| MC25 | list-valued role (R01 V09, R02 case 09) | P | `KHG-P006` |
| MC26 | empty role string (R01 V09) | P | `KHG-P006` |
| MC27 | legacy 'roles' key beside 'role' (R01 V20) | P | `KHG-P014` |
| MC28 | network-type 'asc' (R03 D8, c04) | P | `KHG-P007` |
| MC29 | metadata.default_attrs (R03 D7, c20) | P | `KHG-P008` |
| MC30 | directed file, an incidence without direction (R01 V12, R02 case 23, R03 c14) | P | `KHG-P010` |
| MC31 | undirected file carrying record-level direction (R01 V13, R02 cases 24-25) | P | `KHG-P011` |
| MC32 | fact edge without khg:relation (R01 V14) | P | `KHG-P012` |
| MC33 | edge without khg:kind (R01 V40) | P | `KHG-P013` |
| MC34 | unknown khg: key in incidence attrs | P | `KHG-P014` |
| MC35 | literal node whose id lacks the _: prefix | P | `KHG-P004` |
| MC36 | entity node id using the reserved _: prefix | P | `KHG-P004` |
| MC37 | hif-schema pinned to the moving 'main' URL | P | `KHG-P009` |
| MC38 | role-position 0 | P | `KHG-P015` |
| MC39 | node declared twice (R01 V16, R03 c19) | D (decode) | `KHG-D001` |
| MC40 | edge declared twice (R01 V16) | D (decode) | `KHG-D001` |
| MC41 | incidence names an undeclared node (R01 V17, R02 case 28) | D (decode) | `KHG-D002` |
| MC42 | incidence names an undeclared edge (R02 case 29) | D (decode) | `KHG-D003` |
| MC43 | literal node id does not match its value | D (decode) | `KHG-D005` |
| MC44 | schema hash in metadata does not match the schema | D (decode) | `KHG-D009` |
| MC45 | incidence direction contradicts the role's declared direction (R01 V38) | S (at decode) | `KHG-S016` |
| MC46 | fact-ref node pointing to a missing edge (R01 V18) | D | `KHG-D002` |
| MC47 | binding value with two kinds (entity and literal) | C | `KHG-C001` |
| MC48 | status outside the lifecycle enum (R01 V36) | C | `KHG-C002` |
| MC49 | confidence as a bare number (R01 V32) | C | `KHG-C003` |
| MC50 | quantity without unit (R01 V26) | C | `KHG-C004` |
| MC51 | time precision 15 | C | `KHG-C004` |
| MC52 | UNBOUND value in a fact (R01 V34) | C | `KHG-C005` |
| MC53 | status superseded without status_ref (R01 V37) | C | `KHG-C006` |
| MC54 | extracted evidence without selectors and activity (R01 V47, record side) | C | `KHG-C007` |
| MC55 | rank deprecated without rank_reason | C | `KHG-C008` |
| MC56 | span selector with a negative start | C | `KHG-C007` |
| MC57 | record-level key outside the format (e.g. 'weight') | C | `KHG-C009` |
| MC58 | relation not declared (R01 V21) | S | `KHG-S001` |
| MC59 | role not allowed for the relation (R01 V22) | S | `KHG-S002` |
| MC60 | required role missing on an asserted fact (R01 V23) | S | `KHG-S003` |
| MC61 | role bound more often than max (R01 V24) | S | `KHG-S004` |
| MC62 | entity of the wrong type (R01 V25) | S | `KHG-S005` |
| MC63 | literal where an entity is expected (R01 V25) | S | `KHG-S005` |
| MC64 | time literal with month 13 (R01 V26) | S | `KHG-S006` |
| MC65 | day set below year precision (R01 V26) | S | `KHG-S006` |
| MC66 | fact with no bindings (R01 V27) | S | `KHG-S007` |
| MC67 | fact reference in a role that takes no facts (R01 V29) | S | `KHG-S005` |
| MC68 | valid time starts after it ends (R01 V30) | S | `KHG-S009` |
| MC69 | confidence scale not declared (R01 V32) | S | `KHG-S010` |
| MC70 | confidence outside its scale (R01 V32) | S | `KHG-S010` |
| MC71 | asserted fact with no evidence (R01 V33) | S | `KHG-S011` |
| MC72 | novalue and a concrete value in one role (R01 V35) | S | `KHG-S013` |
| MC73 | the same filler twice in an unordered role (set semantics) | S | `KHG-S014` |
| MC74 | ordered role with a gap in positions | S | `KHG-S015` |
| MC75 | position on an unordered role | S | `KHG-S015` |
| MC76 | goal omits a required role instead of leaving it unbound | S | `KHG-S018` |
| MC77 | one unbound variable used twice in a goal | S | `KHG-S019` |
| MC78 | id not in Unicode NFC | S | `KHG-S020` |
| MC79 | evidence supports an unknown binding id | S | `KHG-S022` |
| MC80 | precision below the role's precision_min | S | `KHG-S023` |
| MC81 | unit not allowed for the role | S | `KHG-S023` |
| MC82 | the same binding id twice in one fact | S | `KHG-S025` |
| MC83 | somevalue where the role forbids it | S | `KHG-S005` |
| MC84 | nesting cycle (R01 V28) | D | `KHG-D008` |
| MC85 | status_ref points at a record of the wrong kind (R01 V37) | D | `KHG-D010` |
| MC86 | supersession cycle (R01 V37) | D | `KHG-D012` |
| MC87 | correction between facts of different relations (R01 V37) | D | `KHG-D011` |
| MC88 | two asserted facts, same key binding, overlapping valid time (R01 V42) | D | `KHG-D016` |
| MC89 | stored derived fields disagree with the bindings (R01 V15) | D | `KHG-D015` |
| MC90 | a candidate inside a store document (queue boundary, F9) | D | `KHG-D017` |
| MC91 | entity referenced but not declared in a complete document (R01 V17) | D | `KHG-D002` |
| MC92 | one id names both an entity and a fact | D | `KHG-D007` |
| MC93 | relation with no roles (R01 V43) | M | `KHG-M001` |
| MC94 | a role used twice in one relation (R01 V44) | M | `KHG-M002` |
| MC95 | key names a role the relation does not use (R01 V44) | M | `KHG-M003` |
| MC96 | key built on a time-slot role | M | `KHG-M003` |
| MC97 | schema version not semver (R01 V45) | M | `KHG-M004` |
| MC98 | unknown datatype (R01 V46) | M | `KHG-M006` |
| MC99 | unknown entity type in a filler (R01 V46) | M | `KHG-M005` |
| MC100 | complete: true on an optional role | M | `KHG-M014` |
| MC101 | time model names a role that is not a time slot | M | `KHG-M007` |
| MC102 | user schema declares a relation in the reserved khg: namespace | M | `KHG-M008` |
| MC103 | temporal key on a relation without an interval time model | M | `KHG-M011` |