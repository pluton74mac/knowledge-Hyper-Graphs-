# P3a dump slice

`wdslice.py` cuts the Wikidata JSON dump into the slice that P3a builds its corpus from, in one streaming pass. The
dump (103 GB compressed) is too big for the container where P3a is designed; the slice is small enough to move and to
re-cut, and it carries every whole-dump statistic the P3a datasheet needs. The pass makes no corpus-design decision
that re-cutting cannot undo: statements are kept verbatim, in Wikibase JSON, the input form of P3a's reader. The
specification is [SPEC.md](SPEC.md); the tests are [test_wdslice.py](test_wdslice.py).

## What the slice holds

For the dump `wikidata-20260922-all.json.bz2` the slice is `datasets/knowledge-bases/wikidata/processed/p3a-slice-20260922/`
(gitignored, like all data).

| File | Content |
|---|---|
| `items-NNNN.jsonl.gz` | The seed items, one per line, in the pruned envelope below. About 250,000 rows per shard: a shard closes after the batch that brings it to `--shard-items` rows. |
| `index-NNNN.jsonl.gz` | One row per item and per property entity. About 10,000,000 rows per shard. |
| `properties.jsonl.gz` | Every property entity, verbatim: the dump's line without its trailing comma. |
| `stats.json` | Statement statistics over every item, over the seed items and over the property entities. |
| `run.json` | The run record: parameters, input hashes and verification, code version, counts, every output's size, sha256 and rows. |

Rows are in dump order. Each `.gz` file is a sequence of gzip members, one per batch of the pass, made with
`gzip.compress(data, compresslevel=6, mtime=0)`; `gzip.open` and `zcat` read them as one stream. The bytes do not
depend on the number of workers or on how the input was read, but a different Python or zlib may compress
differently; the decompressed text is the same everywhere.

**Seed items.** An item is a seed when its English Wikipedia sitelink (`sitelinks.enwiki.title`) names a
main-namespace article: the part of the title before the first `:` is not one of `Category, Template, Module,
Wikipedia, Portal, Help, Draft, File, Image, MediaWiki, User, TimedText, Book, Special, Project, WP, Talk` (compared
case-sensitively). `Star Wars: Episode IV` is an article, `Category:Physics` is not. There is no P31 filter:
disambiguation pages and lists stay in, and P3a filters them from the index. English Wikipedia articles give P9 its
source text and P10 natural question anchors, and the rule is one sentence in a datasheet.

**The pruned envelope** of an items row has the keys `type, id, lastrevid, modified, labels, descriptions, aliases,
sitelinks, x_sitelink_count, claims`, in that order:

- `labels` and `aliases` keep only `en` and `mul`, `descriptions` only `en`; each is present, possibly `{}`.
- `sitelinks` keeps only `enwiki`; `x_sitelink_count` is the number of sitelinks before pruning.
- `claims` is verbatim except that `hash` is removed from every qualifier snak (and from a main snak, should a future
  dump add one). References keep their `hash`. An empty map that the dump writes as `[]` is written `{}`.
- `pageid`, `ns` and `title` are dropped. Text is UTF-8, not `\u` escapes (`ensure_ascii=False`).

**Index rows** are JSON arrays: `[id, type, label, description, p31, p279, n_sitelinks, enwiki, n_statements,
n_qualified, lastrevid, modified, datatype]`. `label` is the `en` label, else the `mul` label, else null;
`description` the `en` description or null. `p31` and `p279` are the item values of P31 and P279 statements whose
main snak is a value and whose rank is not deprecated, in dump order, without duplicates. `enwiki` is the enwiki
title in any namespace, or null. `n_qualified` counts statements with at least one qualifier snak. `datatype` is a
property's datatype, null for items.

**Statistics.** `stats.json` has three scopes with the same keys: `all` (every item), `seed` (the seed items) and
`property_entities` (the statements property entities carry about themselves; `all` plus `property_entities` is the
whole dump). Per scope: entity and statement counts, ranks, snak types and datatypes of main and qualifier snaks,
qualifier and reference counters, histograms of qualifier snaks and properties per statement, reasons for deprecated
(P2241) and preferred (P7452) rank, time series (per property, the entities with two or more statements qualified by
P580, P582 or P585), P31 values, and per property: a record of counts (`statements`, `qualified`, `deprecated`,
`preferred`, `referenced`, `timed`, `multi_P580`, `multi_P582`, `multi_time`, `self_qualified` and the rank-reason
mismatches `p2241_not_deprecated`, `p7452_not_preferred` with their `_snaks`), `qualifier_pairs` (`[statements,
snaks]` per qualifier property) and `per_property_arity_wd_roles`. Keys with a zero count are left out of the
counters, except that `by_rank` and `main_snaktype` always list their three keys. A snak without a `datatype` (its
property was deleted) counts as `"<none>"`.

Three arity histograms describe statements: the subject counts 1, the main value 1 unless it is `novalue`, and each
qualifier snak 1 unless it is `novalue` (a repeated filler counts once per snak). `arity_all_hist` counts every
qualifier snak; `arity_no_interval_hist` leaves out P580 and P582; `arity_wd_roles_hist` counts only snaks in the
`qualifier` slot of the role naming `wd-roles r1` (top-level `"naming"`), which leaves out P580 and P582 (except on
the relations P580 and P582 themselves, rule 6a), P2241, P7452, P1534 and 24 `meta` properties. See Limits.

**Run record.** `run.json` is written with `status: running` when the pass starts and replaced atomically when it
ends, with `complete` or `failed` and the error. `input` holds the md5, sha1 and sha256 of the bytes read, and
`verified` (true when the size and the given hashes match, null when none was given or `--max-input-bytes` stopped
the read). `code` records the script's sha256 and the git commit; `timings.waited_s` is the time spent waiting for
the download.

## Cutting this dump

The pass follows the download: it reads what has arrived, waits 5 s when it catches up, and ends once the file has
the published size and hashes. The download itself is `datasets/knowledge-bases/wikidata/raw/fetch.sh`, a resumable
loop in which each curl run resumes from the current size (`-C -`), without curl's own `--retry`.

```sh
cd /Users/pluton/Documents/CLAUDE/KHG-memorystore
mkdir -p datasets/knowledge-bases/wikidata/processed
nohup caffeinate -i /Users/pluton/.local/bin/python3.11 projects/p3a-clean-nary-corpus/slice/wdslice.py \
    --input datasets/knowledge-bases/wikidata/raw/wikidata-20260922-all.json.bz2 \
    --out datasets/knowledge-bases/wikidata/processed/p3a-slice-20260922 \
    --follow --expect-size 103222517992 \
    --expect-md5 7f70e4a1858ba6182ea9329a1ef588c5 --expect-sha1 c5bfd59f16c6cdf906ead1190d99729108e961be \
    >> datasets/knowledge-bases/wikidata/processed/p3a-slice-20260922.log 2>&1 &
```

Every 60 s it writes one line to the log: time, compressed GB read and percent, MB/s over the minute, uncompressed
GB, entities, seeds, whether it is waiting for the download, and an ETA. The input only grows: `fetch.sh` resumes
each curl run where the file ends and never truncates it. Should the file ever shrink and grow back, the pass would
still wait for it. It fails, and says why in `run.json`, if the file does not grow for 6 hours (`--stall-timeout`),
if the file is replaced, if the input is not a valid bz2 stream or does not match the published size and hashes, if
a worker fails, or on SIGINT, SIGTERM or SIGHUP (without `nohup`). The workers never outlive the pass. It refuses to
write into a directory that holds an earlier run, and holds a lock on the output directory while it runs; to start
again, add `--force`, which removes the earlier outputs first. Once the download is complete, the same command
without `--follow` recuts the dump from the file.

When it finishes, copy `input.sha256` from `run.json` into `datasets/knowledge-bases/wikidata/MANIFEST.json`.

## Verifying a slice

`run.json` must say `"status": "complete"`, `"verified": true`, `"truncated": false` and `"bytes_read":
103222517992`, and its md5 and sha1 must be the published ones. At the end of the pass the slicer checks that its
per-batch counts agree with the statistics (items, seeds, properties, statements), and fails otherwise. To check the
files later:

```python
import hashlib, json, os
d = "datasets/knowledge-bases/wikidata/processed/p3a-slice-20260922"
run = json.load(open(os.path.join(d, "run.json")))
assert run["status"] == "complete" and run["input"]["verified"] is True and not run["input"]["truncated"]
for out in run["outputs"]:
    h = hashlib.sha256()
    with open(os.path.join(d, out["file"]), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    assert h.hexdigest() == out["sha256"], out["file"]
```

## Reading the slice

```python
import gzip, json

with gzip.open("items-0000.jsonl.gz", "rt", encoding="utf-8") as fh:
    item = json.loads(next(fh))                      # one seed item in the pruned envelope
    print(item["id"], item["labels"].get("en", {}).get("value"), item["x_sitelink_count"])
    for pid, statements in item["claims"].items():   # verbatim Wikibase statements
        print(pid, len(statements), [s["rank"] for s in statements])
with gzip.open("index-0000.jsonl.gz", "rt", encoding="utf-8") as fh:
    for line in fh:
        eid, kind, label, desc, p31, p279, n_sitelinks, enwiki, n_st, n_q, rev, modified, dtype = json.loads(line)
```

## Qualifier usage for P6

After the pass, `usage` reshapes `stats.json` into the per-relation qualifier usage that P6's observed schemas use
instead of the SQID estimates (`wd-roles` rule 9; SPEC §12). It reads no dump, only the slice, and refuses a run
that is not complete or whose files do not match the sha256 in `run.json`.

```sh
/Users/pluton/.local/bin/python3.11 projects/p3a-clean-nary-corpus/slice/wdslice.py usage \
    --run datasets/knowledge-bases/wikidata/processed/p3a-slice-20260922 \
    --out projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json
```

The file (`p3a-qualifier-usage/1`, committed) has two scopes: `all` (items and property entities) and `kept` (the
seed items). Per relation: its statements; its qualifiers under their r1 role ids (`P131:qualifier` for a
self-qualifier), with statements, snaks and slot; the time model; the statements rule 6b leaves out; self-qualified
statements; rank reasons that contradict the rank (6c); and the arity under `wd-roles r1`. Rule 8's out-of-scope
properties (best-rank P31 of Q19820110, Q21504947 or Q64846109, read from `properties.jsonl.gz`) are listed and
their usage is set apart.

## Limits

- **The seed rule is English Wikipedia's coverage.** An item without an English article is not a seed however rich
  its statements, and the seeds lean towards what English Wikipedia covers. Disambiguation and list pages are seeds;
  P3a filters them. Every item is still in the index and in the `all` statistics.
- **The statistics' arities are descriptive, not C1's arity**, which depends on the relation schema (P2 DESIGN §2.4).
  `arity_wd_roles_hist` follows `wd-roles r1` slot by slot, but it still counts statements that rule 6b or S009
  leave out of the corpus and relations that rule 8 leaves out (`per_property_arity_wd_roles` lets them be removed).
- The index's `p31` keeps every value not ranked deprecated; rule 8 reads the best rank only.
- The slice is one snapshot: `lastrevid` and `modified` date each entity, and edits made after the dump are not in it.

## Tests and performance

```sh
/Users/pluton/.local/bin/python3.11 -m unittest discover -s projects/p3a-clean-nary-corpus/slice -v
```

The tests build synthetic dumps in the shapes of the 2026-09-22 dump and check the seeds and pruning, index rows,
properties and every statistic against hand-computed values, the run record, multi-stream input, determinism across
worker counts and read sizes, follow mode on a file that grows and shrinks, truncation, hash mismatches, failure
handling (a worker that fails or is killed, SIGINT, SIGTERM, the directory lock) and the `usage` subcommand.

On this Mac (Apple M5, 4 performance and 6 efficiency cores), the first 200 MB of the dump pass at 7.1 MB/s
compressed with one worker and 9.4 MB/s (94 MB/s of JSON) with six. With six workers the reader thread is the limit:
single-threaded bz2 decompression runs at about 10.7 MB/s on this file, and less when the other cores are busy.
Following the download, the pass keeps pace with it and ends a few minutes after it.
