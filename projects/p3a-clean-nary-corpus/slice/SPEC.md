# P3a dump slicer: specification

Director's brief for the build, 2026-09-24. The implementation is `wdslice.py` in this folder; its tests are
`test_wdslice.py`; the user-facing description is `README.md`.

## 0. Context

P3a ([PLAN §3](../../PLAN.md)) builds the clean n-ary corpus from recent Wikidata. The JSON dump is too big for the
cloud container where P3a is designed, so it is cut on the owner's Mac. This tool is that cut: **one streaming pass**
over the dump that writes (a) a slice small enough to move and re-cut, and (b) every whole-dump statistic the P3a
datasheet needs. It makes no corpus-design decision that re-cutting from its output cannot undo: statements are kept
verbatim (Wikibase JSON, the input form of P3a's reader in `tests/consumers/test_p3a.py`).

**Input.** `wikidata-20260922-all.json.bz2`, 103,222,517,992 bytes, from
`https://dumps.wikimedia.org/wikidatawiki/entities/20260921/`. Published checksums:
md5 `7f70e4a1858ba6182ea9329a1ef588c5`, sha1 `c5bfd59f16c6cdf906ead1190d99729108e961be`. It is being downloaded into
`datasets/knowledge-bases/wikidata/raw/` over a link that gives about 1.5 MB/s (first under a 1.2 MB/s cap, then
uncapped at the owner's request), which takes most of a day. The slicer runs while the file grows (follow mode, §7)
and finishes shortly after the download does.

**Dump layout (observed in this dump).** One bz2 stream (other dumps are multi-stream; handle both). The first line
is `[`, then one entity per line, each ending in `,` except the last, and a final line `]`. Top-level entity keys:
`type, id, labels, descriptions, aliases, claims, sitelinks, pageid, ns, title, lastrevid, modified`. Types in this
dump: `item`, `property` (lexemes have their own dump; count and skip any other type). Labels include the `mul`
language. Main snaks carry no `hash`; qualifier snaks carry `hash`; reference blocks carry `hash`, `snaks`,
`snaks-order`; reference snaks carry no `hash`.

## 1. Outputs

All in `<out>/` (for this dump `datasets/knowledge-bases/wikidata/processed/p3a-slice-20260922/`, gitignored):

| File | Content |
|---|---|
| `items-NNNN.jsonl.gz` | Seed items (§2), one per line: pruned envelope (§3), claims verbatim except qualifier-snak hashes. A new shard starts after the batch that brings the current shard to `--shard-items` (default 250,000) items. |
| `index-NNNN.jsonl.gz` | One row per entity, items and properties, as a JSON array (§4). Rotates at `--index-shard-rows` (default 10,000,000) the same way. |
| `properties.jsonl.gz` | Every property entity, verbatim: the dump's line bytes without the trailing comma. |
| `stats.json` | Whole-dump and seed-scope statistics (§5). |
| `run.json` | The run record (§6). |

`NNNN` is zero-padded from `0000`. Every `.gz` file is a concatenation of gzip members, each made with
`gzip.compress(data, compresslevel=6, mtime=0)`, so the bytes are deterministic; `gzip.open` reads multi-member
files. Rows are written in dump order.

## 2. Seed rule

An entity is a **seed** iff its type is `item` and `sitelinks.enwiki.title` exists and names a main-namespace
article: the part before the first `:` is not one of `Category, Template, Module, Wikipedia, Portal, Help, Draft,
File, Image, MediaWiki, User, TimedText, Book, Special, Project, WP, Talk` (compare case-sensitively, as enwiki
namespace names are written). There is no P31 filter at slice time: disambiguation and list pages stay, and P3a filters
them from the index. Reason: enwiki articles give P9 its source text and P10 natural question anchors, and the rule is
one sentence in a datasheet.

## 3. Pruned item envelope (items files)

Keys in this order: `type, id, lastrevid, modified, labels, descriptions, aliases, sitelinks, x_sitelink_count, claims`.

- `labels` keeps only `en` and `mul`; `descriptions` only `en`; `aliases` only `en` and `mul`. Each is verbatim and
  present (possibly `{}`).
- `sitelinks` keeps only `enwiki`, verbatim. `x_sitelink_count` is the number of sitelinks before pruning.
- `claims` is verbatim, except that the key `hash` is removed from every qualifier snak, and from the main snak if a
  future dump adds one. References are untouched, including the reference-level `hash`.
- `pageid`, `ns` and `title` are dropped.
- Serialised with `json.dumps(obj, ensure_ascii=False, separators=(",", ":"))`, UTF-8.

## 4. Index rows (index files)

A JSON array, one per entity (items and properties):
`[id, type, label, description, p31, p279, n_sitelinks, enwiki, n_statements, n_qualified, lastrevid, modified, datatype]`

- `label`: `labels.en.value`, else `labels.mul.value`, else `null`. `description`: `descriptions.en.value` or `null`.
- `p31`, `p279`: ids of the item values of P31 and P279 statements with `snaktype` `value` and rank not
  `deprecated`, in dump order, without duplicates.
- `n_sitelinks`: the count of sitelinks. `enwiki`: `sitelinks.enwiki.title` in any namespace, or `null`.
- `n_statements`: all statements. `n_qualified`: statements with at least one qualifier snak.
- `datatype`: the property's datatype; `null` for items.
- Same serialisation as §3.

## 5. Statistics (`stats.json`)

Top level: `{"format": "p3a-wd-slice-stats/1", "naming": "wd-roles r1", "scopes": {"all": ..., "seed": ...,
"property_entities": ...}, "properties": {"count", "datatype"}, "other_types": {...}}`. `all` covers every item,
`seed` the seed items, and `property_entities` the statements that property entities carry about themselves (so
that `all` plus `property_entities` is the whole dump). Every counter is a JSON object whose keys are strings (ids,
or integers written as strings). The whole file is `json.dumps(..., sort_keys=True, indent=1)`.

Per scope (the three scopes have the same keys; in `property_entities`, `items_with_enwiki_article`,
`sitelinks_hist`, `time_series` and `p31` describe property entities and may simply be empty or zero):

| Key | Meaning |
|---|---|
| `entities` | entities in scope |
| `items_with_enwiki_article` | items that meet the seed rule (equals `entities` in `seed`) |
| `sitelinks_hist` | entities by `n_sitelinks`: keys `"0"` to `"499"`, then `"500+"` |
| `statements` | statements |
| `by_rank` | `preferred`, `normal`, `deprecated` |
| `main_snaktype` | `value`, `somevalue`, `novalue` |
| `main_datatype` | main-snak `datatype` counter |
| `qualified_statements` | statements with at least one qualifier snak |
| `qualifier_snaks_hist` | statements by number of qualifier snaks (`"0"` included) |
| `qualifier_props_hist` | statements by number of distinct qualifier properties |
| `qualifier_snaktype`, `qualifier_datatype`, `qualifier_property` | counters over qualifier snaks |
| `arity_all_hist`, `arity_no_interval_hist` | statements by the arities defined below |
| `referenced_statements` | statements with at least one reference |
| `references` | reference blocks |
| `reference_property` | counter over reference snaks, by property |
| `deprecated_reasons` | over deprecated statements: each P2241 qualifier value id counts once; `"<none>"` when the statement has no P2241; `"<somevalue>"` and `"<novalue>"` for special snaks |
| `preferred_reasons` | the same over preferred statements with P7452 |
| `per_property` | `{pid: {"statements", "qualified", "deprecated", "preferred", "referenced", "timed", "multi_P580", "multi_P582", "multi_time", "self_qualified", "p2241_not_deprecated", "p2241_not_deprecated_snaks", "p7452_not_preferred", "p7452_not_preferred_snaks"}}`; `timed` counts statements with any P580, P582 or P585 qualifier; `multi_P580` and `multi_P582` count statements with two or more P580 (P582) qualifier snaks, and `multi_time` statements with either (rule 6b's count, without double counting); `self_qualified` counts statements that carry their own property as a qualifier; `p2241_not_deprecated` counts statements with a P2241 qualifier whose rank is not `deprecated` and `p2241_not_deprecated_snaks` their P2241 snaks; `p7452_not_preferred` and `p7452_not_preferred_snaks` the same for P7452 on statements whose rank is not `preferred` (rule 6c) |
| `qualifier_pairs` | `{main pid: {qualifier pid: [statements, snaks]}}`: the statements that carry the qualifier at least once, and its snaks |
| `time_series` | `{pid: number of (item, pid) groups with at least 2 timed statements}` |
| `p31` | counter of the index's `p31` values: each item counts once per distinct value |
| `arity_wd_roles_hist` | statements by their arity under the `wd-roles` naming (below) |
| `per_property_arity_wd_roles` | `{pid: {arity: statements}}` under the same naming, so relations can be left out afterwards |

The top-level `"naming": "wd-roles r1"` names the naming the two `wd_roles` counters use.

**Arity for statistics.** These are descriptive, not C1's arity, which depends on the relation schema
([DESIGN §2.4](../../p2-role-aware-hif/DESIGN.md)). The subject counts 1. The main value counts 1 unless it is
`novalue`. Each qualifier snak counts 1 unless it is `novalue`, and a repeated filler counts once per snak.
`arity_all` counts every qualifier snak. `arity_no_interval` leaves out P580 and P582 snaks, C1's interval time
bindings.

**Arity under `wd-roles` r1.** This is the role naming P3a and P6 share, version r1: the authoritative text is
`projects/p6-schema-width/wd-roles.md` on branch `claude/confident-volta-85edr2`. Under it, C1's arity
(DESIGN §2.4) of a mapped statement is: the subject counts 1; the main value counts 1 unless it is `novalue`; each
qualifier snak counts 1 unless it is `novalue` or its property is not in the `qualifier` slot. The properties outside
that slot are:
- `time`: P580, P582, except on relations P580 and P582 themselves, which have no time model; there both are
  `qualifier` (rule 6a) and count;
- `rank_reason`, or `meta` when the rank does not match (rule 6c): P2241, P7452; neither counts;
- end cause (`khg:end_cause` or `meta`): P1534;
- `meta`: P8327, P13589, P1810, P14457, P1932, P4970, P813, P854, P248, P1065, P2960, P143, P4656, P887, P3452,
  P1683, P5017, P3680, P1310, P805, P2916, P6607, P9570, P7528.

A self-qualifier (P131 on a P131 statement) takes the role `P131:qualifier` (rule 5) and the slot of its property:
it counts unless its property is outside the `qualifier` slot. Statements that rule 6b or S009 will leave out of the
corpus are still counted here. The properties that `wd-roles` leaves out as relations (rule 8) are not removed here;
`per_property_arity_wd_roles` lets them be removed afterwards.

## 6. Run record (`run.json`)

```json
{"format": "p3a-wd-slice-run/1", "status": "running | complete | failed", "error": null,
 "started": "UTC ISO-8601", "finished": "UTC ISO-8601 | null",
 "params": {"...every CLI option...": "..."},
 "input": {"path": "...", "expected_size": 0, "bytes_read": 0, "md5": "...", "sha1": "...", "sha256": "...",
           "expected_md5": "...", "expected_sha1": "...", "verified": true, "truncated": false},
 "code": {"script_sha256": "...", "git_commit": "...", "git_dirty": false, "python": "3.11.15"},
 "counts": {"entities": 0, "items": 0, "properties": 0, "other": 0, "seeds": 0, "index_rows": 0,
            "statements_all": 0, "statements_seed": 0, "lines": 0, "uncompressed_bytes": 0},
 "outputs": [{"file": "items-0000.jsonl.gz", "bytes": 0, "sha256": "...", "rows": 0}],
 "timings": {"wall_s": 0.0, "waited_s": 0.0}}
```

It is written at the start with `status: running`, and atomically replaced (write a temp file, then rename) at the
end. `verified` is `true` when every given expected hash matches and the size equals `--expect-size`, `false` on a
mismatch (which also fails the run), and `null` when nothing was given. `waited_s` is the time spent idle waiting for
the download in follow mode.

## 7. Pipeline

- **Reader** (a thread in the main process): reads the input in 8 MiB chunks and updates md5, sha1 and sha256 on the
  compressed bytes. In follow mode (`--follow`, which requires `--expect-size`), a read that returns nothing before
  `expected_size` bytes sleeps 5 s, seeks back to its position and retries. If the file does not grow for
  `--stall-timeout` seconds (default 21,600), the run fails. Without `--follow`, end of file ends the input.
  `--max-input-bytes N` stops after N compressed bytes and implies `--allow-truncated`.
- **Decompression**: `bz2.BZ2Decompressor`. On `eof`, start a new decompressor on `unused_data` (multi-stream). Bound
  each call's output (`max_length` 64 MiB). If the input ends inside a stream, the run fails as truncated, unless
  `--allow-truncated`, in which case the trailing partial line is dropped and `input.truncated` is `true`.
- **Batches**: a batch ends at the first newline at or after `--batch-bytes` (default 16 MiB) from its start, so
  batch boundaries do not depend on how reads or decompression were chunked. Batches carry a sequence number.
- **Workers**: `--workers` processes (default `max(1, os.cpu_count() - 2)`), multiprocessing with the `spawn`
  context. The task queue is bounded at `2 × workers`, which is the backpressure. A worker parses each line with
  `json.loads` (skipping `[` and `]`, stripping the trailing `,`), keeps its statistics locally across all its batches,
  and returns per batch `(seq, items member, index member, properties member, counts)`, each member a gzip member or
  empty. On the stop sentinel it sends its statistics and exits.
- **Writer** (the main thread): a reorder buffer by `seq`; appends members in `seq` order; rotates shards at batch
  boundaries; merges the workers' statistics at the end; writes `stats.json`, then `run.json`; fsyncs the outputs.
- **Failure**: any worker exception (sent back with its traceback), reader error, truncation or hash mismatch sets
  `status: failed` with the error, stops the workers, and exits non-zero.
- **Progress**: every 60 s one line to stderr: UTC time, compressed GB read and percent of `expected_size`, compressed
  MB/s over the interval, uncompressed GB, entities, seeds, whether it is waiting for the download, and an ETA.
- **Memory** stays bounded: about `(2 × workers + reorder buffer) × batch size`.

## 8. Command line

```
python3.11 wdslice.py --input PATH --out DIR [--follow] [--expect-size N] [--expect-md5 H] [--expect-sha1 H]
    [--workers N] [--batch-bytes N] [--shard-items N] [--index-shard-rows N] [--max-input-bytes N]
    [--allow-truncated] [--stall-timeout S] [--force]
```

It refuses to write into a directory that holds `run.json` unless `--force` is given; `--force` removes the old
outputs first. Standard library only; code compatible with Python 3.9 and later. In practice it runs under
`/Users/pluton/.local/bin/python3.11`.

## 9. Tests (`test_wdslice.py`, `unittest`)

Run with `python3.11 -m unittest discover -s projects/p3a-clean-nary-corpus/slice -v`. The tests build a synthetic dump
from realistic entity JSON (the shapes in §0), then check:

1. **Seeds and pruning.** Items: (a) an enwiki article with a P39 statement qualified by P580, P582 and P1365 and
   carrying a reference; P31 Q5; two P1082 statements with P585 (a time series); a deprecated statement with P2241
   Q41755623; a preferred statement with P7452; a `somevalue` main snak; a `novalue` qualifier; (b) an item whose
   enwiki title is `Category:…`; (c) an item with no enwiki sitelink; (d) a main-namespace enwiki item whose P31 is
   Q4167410. Also (e) property P39. Exactly (a) and (d) are seeds. Pruning keeps the reference `hash`, drops the
   qualifier-snak `hash`, keeps only `en` and `mul`, keeps only the `enwiki` sitelink, and leaves the claims otherwise
   equal to the input.
2. **Index rows, properties and statistics** equal hand-computed values: the arity histograms (including
   `wd-roles`), reasons, time series, qualifier pairs (statements and snaks), `p31`, and the `per_property` counts
   `multi_P580`, `multi_P582`, `self_qualified`, `p2241_not_deprecated` and `p7452_not_preferred`. The synthetic dump
   therefore also needs a statement with two P580 snaks, a P131 statement qualified by P131, a normal-rank statement
   with P2241, a statement with a `meta` qualifier (P1810) and one with P1534.
3. **Run record**: counts, and md5, sha1 and sha256 equal to `hashlib` on the synthetic `.bz2`.
4. **Multi-stream**: the same dump as two concatenated bz2 streams gives byte-identical outputs.
5. **Determinism**: `--workers 1` and `--workers 3`, with a tiny `--batch-bytes` and `--shard-items 1`, give
   byte-identical outputs (`run.json` aside).
6. **Follow mode**: a thread appends the `.bz2` in pieces with delays; the run finishes with `--expect-size` and matches
   the non-follow output.
7. **Truncation**: a cut `.bz2` fails without `--allow-truncated` (non-zero exit, `status: failed`) and succeeds with it.
8. **Hash mismatch**: a wrong `--expect-md5` fails the run.

## 10. Benchmark (report only)

Run on the real, still-growing file without `--follow`, with `--max-input-bytes 200000000`, once at `--workers 1`
and once at `--workers 6`, writing under the scratchpad, never under `datasets/`. Report compressed and uncompressed
MB/s, entities/s, the seed share of entities and of bytes, the output sizes, and a projection for the whole dump,
both paced by the download and as a rerun on the complete file. Do not run on the whole file.

## 11. Documentation

`README.md` in this folder: what the slice is for; what it contains and why (§1–§5, written for a reader of the
slice); the follow-mode command used for this dump; how to verify; a ten-line Python snippet that reads an items shard
and an index shard; the limits (the enwiki seed rule, and that the statistics' arity is not C1's arity).

## 12. Qualifier usage for P6 (the `usage` subcommand)

After the pass, `python3.11 wdslice.py usage --run DIR --out FILE` reads `DIR/stats.json`, `DIR/run.json` and
`DIR/properties.jsonl.gz`, and writes the per-relation qualifier usage that P6's observed-schema rows use in place of
the SQID estimates (`wd-roles` rule 9). For this dump the file is
`projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json`, and it is committed. It only reshapes `stats.json`;
it reads no dump.

```json
{"format": "p3a-qualifier-usage/1", "dump": "20260922", "naming": "wd-roles r1",
 "source": {"dump_file": "wikidata-20260922-all.json.bz2", "md5": "...", "sha1": "...", "sha256": "...",
            "slicer_commit": "...", "stats_sha256": "..."},
 "scopes": {"all": "every entity in the dump: items and property entities",
            "kept": "the seed items of the slice: items with an English Wikipedia article (SPEC §2)"},
 "out_of_scope": ["P1855", "..."],
 "all":  {"relations": {"P39": {}}, "out_of_scope_relations": {}},
 "kept": {"relations": {"P39": {}}, "out_of_scope_relations": {}}}
```

One relation, keyed by its property id:

```json
"P39": {"statements": 2000000,
        "qualifiers": {"P580": {"statements": 1280000, "snaks": 1281000, "slot": "time"},
                       "P2241": {"statements": 10, "snaks": 10, "slot": "rank_reason"}},
        "time_model": "interval",
        "left_out_6b": 12, "self_qualified": 0,
        "rank_reason_mismatch": {"P2241": {"statements": 2, "snaks": 2}, "P7452": {"statements": 0, "snaks": 0}},
        "arity": {"2": 500000, "3": 700000}}
```

- `statements`: the relation's main statements in the scope, all ranks.
- `qualifiers`: keyed by the r1 role id, which is the qualifier's property id, or `P<id>:qualifier` when the qualifier
  repeats the relation's own property (rules 5 and 6a). `statements` and `snaks` come from `qualifier_pairs`: the
  usage before slot classing. `slot` is the class after slot classing: `time`, `qualifier`, `meta`, `rank_reason` or
  `end_cause`, by rule 6 with 6a. For P2241 and P7452 the slot is `rank_reason`; the part that rule 6c makes `meta`
  is given in `rank_reason_mismatch`.
- `time_model`: `interval` when the relation uses P580 or P582 in this scope and is not itself P580 or P582 (rule 6 as
  observed; the declared constraints are not read here), else `null`. P1534's slot is `end_cause` under `interval`
  and `meta` otherwise.
- `left_out_6b`: `multi_time` when `time_model` is `interval`, else 0. `self_qualified`: as in `per_property`.
- `rank_reason_mismatch`: from `p2241_not_deprecated`(`_snaks`) and `p7452_not_preferred`(`_snaks`).
- `arity`: `per_property_arity_wd_roles`.
- `all` adds up the `all` and `property_entities` scopes of `stats.json`; `kept` is the `seed` scope.
- `out_of_scope`: rule 8's properties, computed from the dump's own property entities, sorted by numeric id: those
  whose best-rank P31 values include Q19820110, Q21504947 or Q64846109. Best rank means the preferred statements if
  there are any, else the normal ones, which is the `wdt:P31` reading P6 used. Their usage goes to
  `out_of_scope_relations`, in the same shape, and not to `relations`.
- Relations, and the roles inside `qualifiers`, are written in numeric property-id order (P2 before P10; a
  `P<id>:qualifier` role right after the plain role it derives from), and the keys of each relation in the order shown
  above. Layout: one relation per line, `"P39": {…}` in compact JSON (`separators=(",", ":")`), with everything
  around the relation maps indented by one space. The file stays one valid JSON document, deterministic, with
  `ensure_ascii=False`. On the 200 MB benchmark prefix, `indent=1` gave 7.7 MB; the whole dump has more relations,
  and P6 asked for a small file that a reader can still diff by relation.

Tests: on the synthetic dump, every field is checked against hand-computed values, including rule 6a on a P580
relation that carries P580 and P582 qualifiers, rule 6c mismatches on both properties, rule 5, P1534 under both time
models, and the rule-8 set from a synthetic documentation property entity.
