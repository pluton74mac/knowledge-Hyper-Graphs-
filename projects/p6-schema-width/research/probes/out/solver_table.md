| Instance | V/E | p6check tw / ghw / fhw / hw | BalancedGo `-exact -det` (hw) | log-k-decomp `-exact` (hw) | NewDetKDecomp `detkdecomp` k (hw) | det-k-decomp 1.0, k = 3 | HtdLEO hw / htdsmt hw | BalancedGo `-global` k (ghw) | NewDetKDecomp `balsepkdecomp` k (ghw) | HtdLEO `-g` (ghw) | fraSMT (fhw) | htd tw / GHD ub |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `berge_path` | 3/2 | 1 / 1 / 1 / 1 | 1 | 1 | 1:yes | yes | 1 / 1 | 1:yes | 1:yes | 1 | 1 | 1 / 1 |
| `berge_triangle` | 3/2 | 2 / 1 / 1 / 1 | 1 | 1 | 1:yes | yes | 1 / 1 | 1:yes | 1:yes | 1 | 1 | 2 / 1 |
| `gamma_triangle` | 3/3 | 2 / 1 / 1 / 1 | 1 | 1 | 1:yes | yes | 1 / 1 | 1:yes | 1:yes | 1 | 1 | 2 / 1 |
| `a_triangle_cover` | 3/4 | 2 / 1 / 1 / 1 | 1 | 1 | 1:yes | yes | 1 / 1 | 1:yes | 1:yes | 1 | 1 | 2 / 1 |
| `b_triangle` | 3/3 | 2 / 2 / 3/2 / 2 | 2 | 2 | 1:no 2:yes | yes | 2 / 2 | 1:no 2:yes | 1:no 2:yes | 2 | 1.5 | 2 / 2 |
| `k5` | 5/10 | 4 / 3 / 5/2 / 3 | 3 | 3 | 1:no 2:no 3:yes | yes | 3 / 3 | 1:no 2:no (4 s) 3:yes | 1:no 2:no 3:yes | 3 | 2.5 | 4 / 3 |
| `adler` | 10/8 | 4 / 2 / 2 / 3 | 3 | 3 | 1:no 2:no 3:yes | yes | 3 / 3 | 1:no 2:yes (6 s) | 1:no 2:yes | 2 |  | 4 / 3 |
| `c_grid4` | 16/24 | 4 / 3 / 3 / 3 | 3 | 3 | 1:no 2:no 3:yes | yes | 3 / 3 | 1:no 2:no 3:yes | 1:no 2:no 3:yes | 3 |  | 4 / 4 |
| `c_grid5` | 25/40 | skip: 25 ver / skip: 25 ver / skip: 25 ver / 3 | 3 | 3 | 1:no 2:no 3:yes | yes | 3 / 3 | 1:no 2:no 3:yes (2 s) | 1:no 2:no 3:yes | 3 | 3.0 (2 s) | 5 / 4 |
| `grohe_marx_3` | 20/6 | skip: 20 ver / skip: 20 ver / skip: 20 ver / 3 | 3 | 3 | 1:no 2:no 3:yes | yes | 3 / 3 | 1:no 2:t/o (300 s) 3:t/o (300 s) | 1:no 2:no 3:yes | 3 | 2.0 (3 s) | 18 / 3 |
| `c_grid2d_10` | 50/50 | skip: 50 ver / skip: 50 ver / skip: 50 ver / skip: budget | 4 (3 s) | 4 (1 s) | – | – | – / – | 1:no 2:no (7 s) | – | – | – | – / – |
