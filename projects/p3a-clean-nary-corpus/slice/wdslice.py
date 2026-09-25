#!/usr/bin/env python3
"""One streaming pass over a Wikidata JSON dump (``.json.bz2``) that writes the P3a slice (``SPEC.md`` here).

Outputs, all in ``--out`` (SPEC §1):

- ``items-NNNN.jsonl.gz``: the seed items (§2) in the pruned envelope (§3), claims verbatim but for qualifier-snak
  hashes. A shard closes after the batch that brings it to ``--shard-items`` rows.
- ``index-NNNN.jsonl.gz``: one JSON array per item and property (§4); shards close at ``--index-shard-rows``.
- ``properties.jsonl.gz``: every property entity, the dump's line bytes without the trailing comma.
- ``stats.json``: statement statistics over every item (``all``), the seed items (``seed``) and the claims of the
  property entities (``property_entities``) (§5), among them three arity histograms: every qualifier snak, without
  P580 and P582, and under the ``wd-roles r1`` naming.
- ``run.json``: the run record (§6), written with ``status: running`` at the start and replaced atomically at the end.

Every ``.gz`` file is a concatenation of gzip members, one per batch, each ``gzip.compress(data, 6, mtime=0)``; rows
are in dump order. Keys with a zero count are left out of the counters in ``stats.json``, except that ``by_rank`` and
``main_snaktype`` always list their three keys; a snak without a ``datatype`` (its property was deleted) counts as
``"<none>"`` in the datatype counters.

Pipeline (§7). A reader thread reads the input in 8 MiB chunks, hashes it (md5, sha1, sha256), decompresses it
(multi-stream bz2) and cuts the text into batches, each ending at the first newline at offset ``--batch-bytes`` or
later from its start, so that batch boundaries depend only on the text. ``--workers`` processes (spawn) parse the lines,
keep their statistics locally and return per batch one gzip member per output kind; on the stop sentinel each sends
its statistics. The main thread writes the members in batch order, rotates shards at batch boundaries, merges the
statistics once at the end, writes ``stats.json``, then ``run.json``. The task queue holds at most ``2 x workers``
batches, and at most ``4 x workers`` batches are in flight between the reader and the writer, which bounds memory
however unevenly the workers finish.

With ``--follow`` (which needs ``--expect-size``) the input may still be growing: a read that returns nothing before
``--expect-size`` bytes waits 5 s and retries at the same offset, so the file may also shrink and grow back (as
``curl --retry`` does when it truncates a failed attempt). The run fails when the file does not grow for
``--stall-timeout`` seconds. Without ``--follow`` the end of the file ends the input. ``--max-input-bytes N`` stops
after N compressed bytes and implies ``--allow-truncated``; the hashes are then those of the prefix read and
``verified`` is null. An input that ends inside a bz2 stream fails the run as truncated unless ``--allow-truncated``
is given, in which case the trailing partial line is dropped.

Exit status: 0 when the run is complete; 1 when it fails (``run.json`` then has ``status: failed`` and the error,
also on an interrupt or SIGTERM); 2 on a usage error (a bad option, a missing input, an output directory that holds
an earlier run without ``--force``, or one that another run is writing to). A running pass holds an exclusive
``flock`` on the output directory. Progress goes to stderr, one line every 60 s. ``wdslice.py run OPTIONS`` is the
same command as ``wdslice.py OPTIONS``.

``wdslice.py usage --run DIR --out FILE`` (§12) reshapes the ``stats.json`` of a complete pass into the per-relation
qualifier usage that P6 reads (``p3a-qualifier-usage/1``): roles, slots and time model under ``wd-roles r1``, the
statements rule 6b leaves out, rank-reason mismatches (6c) and the arity, over the whole dump and over the seed
items, with rule 8's out-of-scope properties (from the property entities' best-rank P31) set apart.

Standard library only; Python 3.9 or later.
"""
from __future__ import annotations

import argparse
import bz2
import contextlib
import gzip
import hashlib
import json
import multiprocessing
import multiprocessing.connection
import os
import platform
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import traceback
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import fcntl
except ImportError:  # not POSIX: the output directory is not locked
    fcntl = None  # type: ignore[assignment]

FORMAT_STATS = "p3a-wd-slice-stats/1"
FORMAT_RUN = "p3a-wd-slice-run/1"

#: Compressed bytes per read (§7).
READ_CHUNK = 8 << 20
#: Upper bound on the output of one decompressor call (§7).
MAX_OUTPUT = 64 << 20
#: Idle wait in follow mode when the reader has caught up with the download (§7).
FOLLOW_SLEEP_S = 5.0
#: Interval between progress lines (§7).
PROGRESS_S = 60.0
GZIP_LEVEL = 6

DEFAULT_BATCH_BYTES = 16 << 20
DEFAULT_SHARD_ITEMS = 250_000
DEFAULT_INDEX_SHARD_ROWS = 10_000_000
DEFAULT_STALL_TIMEOUT = 21_600.0

#: The namespace names (and aliases) of enwiki whose titles are not main-namespace articles (§2).
NON_ARTICLE_NAMESPACES = frozenset((
    "Category", "Template", "Module", "Wikipedia", "Portal", "Help", "Draft", "File", "Image", "MediaWiki", "User",
    "TimedText", "Book", "Special", "Project", "WP", "Talk"))
#: The languages the pruned envelope keeps (§3).
LABEL_LANGUAGES = ("en", "mul")
DESCRIPTION_LANGUAGES = ("en",)
#: The fields of a ``per_property`` record, in the order a worker keeps them (§5).
PER_PROPERTY_FIELDS = ("statements", "qualified", "deprecated", "preferred", "referenced", "timed", "multi_P580",
                       "multi_P582", "multi_time", "self_qualified", "p2241_not_deprecated",
                       "p2241_not_deprecated_snaks", "p7452_not_preferred", "p7452_not_preferred_snaks")
#: The role naming of the ``wd_roles`` counters (§5; ``projects/p6-schema-width/wd-roles.md``, rule 6), and the
#: qualifier properties outside its ``qualifier`` slot, whose snaks those counters leave out: ``time`` (except on the
#: relations P580 and P582 themselves, rule 6a), ``rank_reason`` or ``meta`` (6c), end cause, and ``meta``.
WD_ROLES_NAMING = "wd-roles r1"
WD_ROLES_TIME = ("P580", "P582")
WD_ROLES_RANK_REASON = ("P2241", "P7452")
WD_ROLES_END_CAUSE = ("P1534",)
WD_ROLES_META = ("P8327", "P13589", "P1810", "P14457", "P1932", "P4970", "P813", "P854", "P248", "P1065", "P2960",
                 "P143", "P4656", "P887", "P3452", "P1683", "P5017", "P3680", "P1310", "P805", "P2916", "P6607",
                 "P9570", "P7528")
NOT_QUALIFIER_SLOT = frozenset(WD_ROLES_TIME + WD_ROLES_RANK_REASON + WD_ROLES_END_CAUSE + WD_ROLES_META)
#: Rule 8: properties whose best-rank P31 values include one of these document or constrain other properties.
OUT_OF_SCOPE_CLASSES = frozenset(("Q19820110", "Q21504947", "Q64846109"))
FORMAT_USAGE = "p3a-qualifier-usage/1"
#: The counts of ``run.json`` (§6), in the order of a batch's counts tuple.
COUNT_KEYS = ("entities", "items", "properties", "other", "seeds", "index_rows", "statements_all",
              "statements_seed", "lines", "uncompressed_bytes")
#: The sitelink count from which ``sitelinks_hist`` has one bucket, ``"500+"``.
SITELINKS_TOP = 500
#: The key of a counter for a snak without a ``datatype``, a statement without a reason qualifier, and special snaks.
NONE, SOMEVALUE, NOVALUE = "<none>", "<somevalue>", "<novalue>"
#: The prefix of an entity id by entity type, for a value that has only a ``numeric-id`` (older dumps).
ID_PREFIX = {"item": "Q", "property": "P", "lexeme": "L"}

_SCOPE_INTS = ("entities", "items_with_enwiki_article", "statements", "qualified_statements",
               "referenced_statements", "references")
_SCOPE_COUNTERS = ("sitelinks_hist", "by_rank", "main_snaktype", "main_datatype", "qualifier_snaks_hist",
                   "qualifier_props_hist", "qualifier_snaktype", "qualifier_datatype", "qualifier_property",
                   "arity_all_hist", "arity_no_interval_hist", "arity_wd_roles_hist", "reference_property",
                   "deprecated_reasons", "preferred_reasons", "time_series", "p31")
#: Per-property maps of a scope: pid -> record, pid -> {qualifier pid: [statements, snaks]}, pid -> {arity: n}.
_SCOPE_MAPS = ("per_property", "qualifier_pairs", "per_property_arity_wd_roles")
#: Counters that always list these keys (zero included).
_DENSE = {"by_rank": ("preferred", "normal", "deprecated"), "main_snaktype": ("value", "somevalue", "novalue")}

_OUTPUT_NAME = re.compile(r"(?:items|index)-\d{4,}\.jsonl\.gz|properties\.jsonl\.gz|stats\.json|run\.json"
                          r"|\.(?:run|stats)\.json\.tmp")
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")

# ------------------------------------------------------------------------------------------------ seed rule


def is_article(title: str) -> bool:
    """True when an enwiki title names a main-namespace article (§2): it has no ``:``, or the part before the first
    ``:`` is not one of ``NON_ARTICLE_NAMESPACES`` (compared case-sensitively)."""
    head, colon, _ = title.partition(":")
    return not colon or head not in NON_ARTICLE_NAMESPACES


# ------------------------------------------------------------------------------------------------ worker side


class Scope:
    """The statistics of one scope (§5) as a worker accumulates them: integers, counters and three per-property
    maps, ``per_property`` (pid -> list in ``PER_PROPERTY_FIELDS`` order), ``qualifier_pairs`` (pid -> qualifier
    pid -> [statements, snaks]) and ``per_property_arity_wd_roles`` (pid -> arity -> statements)."""

    __slots__ = _SCOPE_INTS + _SCOPE_COUNTERS + _SCOPE_MAPS

    def __init__(self) -> None:
        for name in _SCOPE_INTS:
            setattr(self, name, 0)
        for name in _SCOPE_COUNTERS:
            setattr(self, name, defaultdict(int))
        self.per_property: Dict[str, List[int]] = {}
        self.qualifier_pairs: Dict[str, Dict[str, List[int]]] = {}
        self.per_property_arity_wd_roles: Dict[str, Dict[int, int]] = {}

    def export(self) -> Dict[str, Any]:
        """The scope as plain dicts, lists and integers (what crosses the process boundary)."""
        out: Dict[str, Any] = {name: getattr(self, name) for name in _SCOPE_INTS}
        for name in _SCOPE_COUNTERS:
            out[name] = dict(getattr(self, name))
        out["per_property"] = {pid: list(v) for pid, v in self.per_property.items()}
        out["qualifier_pairs"] = {pid: {q: list(n) for q, n in v.items()} for pid, v in self.qualifier_pairs.items()}
        out["per_property_arity_wd_roles"] = {pid: dict(v) for pid, v in self.per_property_arity_wd_roles.items()}
        return out


def _entity_id(snak: Dict[str, Any]) -> Optional[str]:
    """The id of an entity value snak, or None when the snak holds no entity."""
    datavalue = snak.get("datavalue")
    if not datavalue or datavalue.get("type") != "wikibase-entityid":
        return None
    value = datavalue.get("value")
    if type(value) is not dict:
        return None
    ident = value.get("id")
    if ident is None and value.get("numeric-id") is not None:
        ident = ID_PREFIX.get(value.get("entity-type", "item"), "Q") + str(value["numeric-id"])
    return ident


def _class_ids(statements: Any) -> List[str]:
    """The ids of the item values of value statements not ranked deprecated, in order, without duplicates (§4)."""
    out: List[str] = []
    for s in statements or ():
        if s.get("rank") == "deprecated":
            continue
        snak = s.get("mainsnak") or {}
        if snak.get("snaktype") != "value":
            continue
        datavalue = snak.get("datavalue") or {}
        value = datavalue.get("value")
        if type(value) is dict and value.get("entity-type", "item") != "item":
            continue
        ident = _entity_id(snak)
        if ident is not None and ident not in out:
            out.append(ident)
    return out


def _reasons(qualifiers: Any, prop: str, counter: Dict[str, int]) -> None:
    """Counts a statement's reasons (§5): each distinct ``prop`` qualifier value once, ``<somevalue>`` and
    ``<novalue>`` for special snaks, and ``<none>`` when the statement has no ``prop`` qualifier."""
    snaks = qualifiers.get(prop) if qualifiers else None
    if not snaks:
        counter[NONE] += 1
        return
    keys = set()
    for snak in snaks:
        snaktype = snak.get("snaktype")
        if snaktype == "value":
            ident = _entity_id(snak)
            if ident is not None:
                keys.add(ident)
        elif snaktype == "somevalue":
            keys.add(SOMEVALUE)
        elif snaktype == "novalue":
            keys.add(NOVALUE)
    for key in keys:
        counter[key] += 1


def _add_statements(claims: Dict[str, Any], sc: Scope) -> Tuple[int, int]:
    """Adds an entity's statements to scope ``sc`` (§5); returns (statements, statements with a qualifier snak).

    Arity (§5): the subject counts 1, the main value 1 unless it is ``novalue``, and each qualifier snak 1 unless it
    is ``novalue``; ``arity_no_interval`` leaves out P580 and P582 snaks, ``arity_wd_roles`` the snaks of every
    property in ``NOT_QUALIFIER_SLOT``, except P580 and P582 on the relations P580 and P582 (rule 6a). A property
    "carried" as a qualifier has at least one snak. Statements without a qualifier snak are counted in locals and
    added to the histograms once per property. ``record`` indices follow ``PER_PROPERTY_FIELDS``."""
    main_snaktype = sc.main_snaktype
    main_datatype = sc.main_datatype
    by_rank = sc.by_rank
    q_snaks_hist = sc.qualifier_snaks_hist
    q_props_hist = sc.qualifier_props_hist
    q_snaktype = sc.qualifier_snaktype
    q_datatype = sc.qualifier_datatype
    q_property = sc.qualifier_property
    arity_all = sc.arity_all_hist
    arity_no_interval = sc.arity_no_interval_hist
    arity_wd_roles = sc.arity_wd_roles_hist
    ref_property = sc.reference_property
    per_property = sc.per_property
    per_property_wd = sc.per_property_arity_wd_roles
    pairs = sc.qualifier_pairs
    not_slot = NOT_QUALIFIER_SLOT
    n_statements = n_qualified = n_referenced = n_references = 0
    plain = plain_novalue = 0  # statements without a qualifier snak, by whether the main snak is novalue
    for pid, statements in claims.items():
        record = per_property.get(pid)
        if record is None:
            record = per_property[pid] = [0] * len(PER_PROPERTY_FIELDS)
        wd_hist = per_property_wd.get(pid)
        if wd_hist is None:
            wd_hist = per_property_wd[pid] = defaultdict(int)
        record[0] += len(statements)
        n_statements += len(statements)
        time_outside = pid != "P580" and pid != "P582"  # rule 6a: on P580 and P582 both are in the qualifier slot
        timed = group_plain = group_plain_novalue = 0
        for s in statements:
            snak = s["mainsnak"]
            snaktype = snak["snaktype"]
            main_snaktype[snaktype] += 1
            main_datatype[snak.get("datatype", NONE)] += 1
            rank = s["rank"]
            by_rank[rank] += 1
            qualifiers = s.get("qualifiers")
            n_snaks = 0
            if qualifiers:
                # n_values: qualifier snaks that are not novalue; n_interval and n_outside: those of them whose
                # property is P580 or P582, or outside the qualifier slot of wd-roles
                n_props = n_values = n_interval = n_outside = 0
                pair = pairs.get(pid)
                if pair is None:
                    pair = pairs[pid] = {}
                for qpid, qsnaks in qualifiers.items():
                    k = len(qsnaks)
                    if not k:
                        continue
                    n_snaks += k
                    n_props += 1
                    q_property[qpid] += k
                    counts = pair.get(qpid)
                    if counts is None:
                        pair[qpid] = [1, k]
                    else:
                        counts[0] += 1
                        counts[1] += k
                    values = k
                    for qsnak in qsnaks:
                        qtype = qsnak["snaktype"]
                        q_snaktype[qtype] += 1
                        q_datatype[qsnak.get("datatype", NONE)] += 1
                        if qtype == "novalue":
                            values -= 1
                    n_values += values
                    if qpid in not_slot:
                        if qpid == "P580" or qpid == "P582":
                            n_interval += values
                            if time_outside:
                                n_outside += values
                        else:
                            n_outside += values
                if n_snaks:
                    n_qualified += 1
                    record[1] += 1
                    arity = (1 if snaktype == "novalue" else 2) + n_values
                    arity_all[arity] += 1
                    arity_no_interval[arity - n_interval] += 1
                    arity_wd_roles[arity - n_outside] += 1
                    wd_hist[arity - n_outside] += 1
                    q_snaks_hist[n_snaks] += 1
                    q_props_hist[n_props] += 1
                    start = qualifiers.get("P580")
                    end = qualifiers.get("P582")
                    if start or end or qualifiers.get("P585"):
                        record[5] += 1
                        timed += 1
                        if start and len(start) >= 2:
                            record[6] += 1
                        if end and len(end) >= 2:
                            record[7] += 1
                        if (start and len(start) >= 2) or (end and len(end) >= 2):
                            record[8] += 1
                    if qualifiers.get(pid):
                        record[9] += 1
                    if rank != "deprecated":
                        reasons = qualifiers.get("P2241")
                        if reasons:
                            record[10] += 1
                            record[11] += len(reasons)
                    if rank != "preferred":
                        reasons = qualifiers.get("P7452")
                        if reasons:
                            record[12] += 1
                            record[13] += len(reasons)
            if not n_snaks:
                if snaktype == "novalue":
                    group_plain_novalue += 1
                else:
                    group_plain += 1
            references = s.get("references")
            if references:
                n_referenced += 1
                record[4] += 1
                n_references += len(references)
                for reference in references:
                    rsnaks = reference.get("snaks")
                    if rsnaks:
                        for rpid, rs in rsnaks.items():
                            ref_property[rpid] += len(rs)
            if rank == "deprecated":
                record[2] += 1
                _reasons(qualifiers, "P2241", sc.deprecated_reasons)
            elif rank == "preferred":
                record[3] += 1
                _reasons(qualifiers, "P7452", sc.preferred_reasons)
        if group_plain:
            wd_hist[2] += group_plain
            plain += group_plain
        if group_plain_novalue:
            wd_hist[1] += group_plain_novalue
            plain_novalue += group_plain_novalue
        if timed >= 2:
            sc.time_series[pid] += 1
    for arity, n in ((2, plain), (1, plain_novalue)):
        if n:
            q_snaks_hist[0] += n
            q_props_hist[0] += n
            arity_all[arity] += n
            arity_no_interval[arity] += n
            arity_wd_roles[arity] += n
    sc.statements += n_statements
    sc.qualified_statements += n_qualified
    sc.referenced_statements += n_referenced
    sc.references += n_references
    return n_statements, n_qualified


def _add_entity(sc: Scope, n_sitelinks: int, p31: List[str]) -> None:
    """Adds one entity's own counts to scope ``sc``: ``entities``, ``sitelinks_hist`` and ``p31`` (§5)."""
    sc.entities += 1
    sc.sitelinks_hist[n_sitelinks if n_sitelinks < SITELINKS_TOP else SITELINKS_TOP] += 1
    counter = sc.p31
    for cls in p31:
        counter[cls] += 1


def _strip_qualifier_hashes(claims: Dict[str, Any]) -> None:
    """Removes ``hash`` from every qualifier snak and main snak, in place (§3), and writes an empty ``qualifiers``
    serialised as ``[]`` as ``{}``. References are left as they are."""
    for statements in claims.values():
        for s in statements:
            snak = s.get("mainsnak")
            if snak and "hash" in snak:
                del snak["hash"]
            qualifiers = s.get("qualifiers")
            if qualifiers:
                for qsnaks in qualifiers.values():
                    for qsnak in qsnaks:
                        qsnak.pop("hash", None)
            elif qualifiers == []:
                s["qualifiers"] = {}


def _pick(mapping: Dict[str, Any], keys: Sequence[str]) -> Dict[str, Any]:
    return {k: mapping[k] for k in keys if k in mapping}


def _value(mapping: Dict[str, Any], *languages: str) -> Optional[str]:
    """The ``value`` of the first of ``languages`` present in a labels or descriptions map, else None."""
    for language in languages:
        entry = mapping.get(language)
        if entry:
            return entry.get("value")
    return None


#: ``json.dumps(obj, ensure_ascii=False, separators=(",", ":"))`` (§3), made once; parsed JSON holds no cycles.
_dumps = json.JSONEncoder(ensure_ascii=False, separators=(",", ":"), check_circular=False).encode


def _encode(obj: Any) -> bytes:
    """``obj`` as one row of JSON text in UTF-8 (§3). A lone surrogate (valid JSON, not encodable) is written as
    its ``\\uXXXX`` escape, which decodes to the same string."""
    text = _dumps(obj)
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError:
        return _LONE_SURROGATE.sub(lambda m: "\\u%04x" % ord(m.group()), text).encode("utf-8")


def _member(rows: List[bytes]) -> bytes:
    """One gzip member holding ``rows``, one per line (§1); ``b""`` when there are none."""
    if not rows:
        return b""
    return gzip.compress(b"\n".join(rows) + b"\n", compresslevel=GZIP_LEVEL, mtime=0)


class WorkerState:
    """A worker's statistics across all its batches: the seed scope, the other items (``rest``; the ``all`` scope
    is their sum), the property entities, property datatypes and the counts of other entity types."""

    def __init__(self) -> None:
        self.seed = Scope()
        self.rest = Scope()
        self.props = Scope()
        self.property_count = 0
        self.property_datatype: Dict[str, int] = defaultdict(int)
        self.other_types: Dict[str, int] = defaultdict(int)

    def export(self) -> Dict[str, Any]:
        return {"seed": self.seed.export(), "rest": self.rest.export(), "property_entities": self.props.export(),
                "properties": {"count": self.property_count, "datatype": dict(self.property_datatype)},
                "other_types": dict(self.other_types)}


def process_batch(blob: bytes, state: WorkerState, seq: int = 0) -> Tuple[bytes, bytes, bytes, Tuple[int, ...]]:
    """Processes one batch of dump lines: returns the items, index and properties gzip members (``b""`` when a
    kind has no rows) and the batch's counts in ``COUNT_KEYS`` order. Statistics go to ``state``.

    A line is stripped of trailing white space and one trailing comma; empty lines and the lines ``[`` and ``]``
    are skipped. An error names the batch, the line in it, and the entity id when it is known."""
    item_rows: List[bytes] = []
    index_rows: List[bytes] = []
    property_lines: List[bytes] = []
    n_entities = n_items = n_properties = n_other = n_seeds = n_all = n_seed_statements = 0
    lines = blob.split(b"\n")
    n_lines = len(lines) - 1 if blob.endswith(b"\n") else len(lines)
    for lineno, raw in enumerate(lines, 1):
        raw = raw.rstrip()
        if raw.endswith(b","):
            raw = raw[:-1]
        if not raw or raw == b"[" or raw == b"]":
            continue
        ent: Any = None
        try:
            ent = json.loads(raw)
            kind = ent.get("type")
            n_entities += 1
            if kind == "item":
                n_items += 1
                sitelinks = ent.get("sitelinks") or {}
                n_sitelinks = len(sitelinks)
                enwiki = sitelinks.get("enwiki")
                title = enwiki.get("title") if enwiki else None
                seed = title is not None and is_article(title)
                claims = ent.get("claims") or {}
                sc = state.seed if seed else state.rest
                n_statements, n_qualified = _add_statements(claims, sc)
                p31 = _class_ids(claims.get("P31"))
                p279 = _class_ids(claims.get("P279"))
                _add_entity(sc, n_sitelinks, p31)
                labels = ent.get("labels") or {}
                descriptions = ent.get("descriptions") or {}
                n_all += n_statements
                index_rows.append(_encode([
                    ent["id"], kind, _value(labels, "en", "mul"), _value(descriptions, "en"), p31, p279,
                    n_sitelinks, title, n_statements, n_qualified, ent.get("lastrevid"), ent.get("modified"), None]))
                if seed:
                    n_seeds += 1
                    sc.items_with_enwiki_article += 1
                    n_seed_statements += n_statements
                    _strip_qualifier_hashes(claims)
                    item_rows.append(_encode({
                        "type": kind, "id": ent["id"], "lastrevid": ent.get("lastrevid"),
                        "modified": ent.get("modified"), "labels": _pick(labels, LABEL_LANGUAGES),
                        "descriptions": _pick(descriptions, DESCRIPTION_LANGUAGES),
                        "aliases": _pick(ent.get("aliases") or {}, LABEL_LANGUAGES), "sitelinks": {"enwiki": enwiki},
                        "x_sitelink_count": n_sitelinks, "claims": claims}))
            elif kind == "property":
                n_properties += 1
                claims = ent.get("claims") or {}
                n_statements, n_qualified = _add_statements(claims, state.props)
                p31 = _class_ids(claims.get("P31"))
                sitelinks = ent.get("sitelinks") or {}
                enwiki = sitelinks.get("enwiki")
                _add_entity(state.props, len(sitelinks), p31)
                datatype = ent.get("datatype")
                state.property_count += 1
                state.property_datatype[datatype if datatype is not None else NONE] += 1
                index_rows.append(_encode([
                    ent["id"], kind, _value(ent.get("labels") or {}, "en", "mul"),
                    _value(ent.get("descriptions") or {}, "en"), p31, _class_ids(claims.get("P279")),
                    len(sitelinks), enwiki.get("title") if enwiki else None, n_statements, n_qualified,
                    ent.get("lastrevid"), ent.get("modified"), datatype]))
                property_lines.append(raw)
            else:
                n_other += 1
                state.other_types[kind if isinstance(kind, str) else NONE] += 1
        except Exception as e:
            ident = ent.get("id") if isinstance(ent, dict) else None
            where = f"entity {ident}" if ident else f"text {bytes(raw[:80])!r}"
            raise ValueError(f"batch {seq}, line {lineno}, {where}: {type(e).__name__}: {e}") from e
    counts = (n_entities, n_items, n_properties, n_other, n_seeds, n_items + n_properties, n_all,
              n_seed_statements, n_lines, len(blob))
    return _member(item_rows), _member(index_rows), _member(property_lines), counts


def _worker_main(wid: int, tasks: Any, conn: Any) -> None:
    """Entry point of a worker process (spawn). Takes ``(seq, blob)`` tasks until the ``None`` sentinel, sends
    ``("batch", seq, items, index, properties, counts)`` per task and then ``("stats", wid, statistics)``. An
    exception is sent as ``("error", wid, traceback)``. SIGINT is ignored: the main process ends the workers. A
    worker whose parent has died exits at its next idle second."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    state = WorkerState()
    parent = multiprocessing.parent_process()
    try:
        while True:
            try:
                task = tasks.get(timeout=1.0)
            except queue.Empty:
                if parent is not None and not parent.is_alive():
                    return
                continue
            if task is None:
                break
            seq, blob = task
            conn.send(("batch", seq) + process_batch(blob, state, seq))
        conn.send(("stats", wid, state.export()))
    except BaseException:
        with contextlib.suppress(BaseException):
            conn.send(("error", wid, traceback.format_exc()))
    finally:
        with contextlib.suppress(Exception):
            conn.close()


# ------------------------------------------------------------------------------------------------ statistics


def _merge(dst: Dict[Any, Any], src: Dict[Any, Any]) -> None:
    """Adds nested counters ``src`` into ``dst``: integers add, dicts merge, lists add element-wise."""
    for key, value in src.items():
        if isinstance(value, dict):
            _merge(dst.setdefault(key, {}), value)
        elif isinstance(value, list):
            have = dst.get(key)
            dst[key] = list(value) if have is None else [a + b for a, b in zip(have, value)]
        else:
            dst[key] = dst.get(key, 0) + value


def _scope_json(scope: Dict[str, Any]) -> Dict[str, Any]:
    """A merged scope as ``stats.json`` writes it: string keys, zero counts left out (``_DENSE`` aside),
    ``per_property`` records with named fields, ``qualifier_pairs`` values as ``[statements, snaks]``."""
    out: Dict[str, Any] = {name: scope.get(name, 0) for name in _SCOPE_INTS}
    for name in _SCOPE_COUNTERS:
        counter = scope.get(name, {})
        if name == "sitelinks_hist":  # the workers count every n >= SITELINKS_TOP under SITELINKS_TOP
            out[name] = {(f"{k}+" if k == SITELINKS_TOP else str(k)): n for k, n in counter.items() if n}
        else:
            out[name] = {str(k): n for k, n in counter.items() if n}
        for key in _DENSE.get(name, ()):
            out[name].setdefault(key, 0)
    out["per_property"] = {pid: dict(zip(PER_PROPERTY_FIELDS, v)) for pid, v in scope.get("per_property", {}).items()}
    pairs = {pid: {q: n for q, n in v.items() if n[0]} for pid, v in scope.get("qualifier_pairs", {}).items()}
    out["qualifier_pairs"] = {pid: v for pid, v in pairs.items() if v}
    arities = {pid: {str(a): n for a, n in v.items() if n}
               for pid, v in scope.get("per_property_arity_wd_roles", {}).items()}
    out["per_property_arity_wd_roles"] = {pid: v for pid, v in arities.items() if v}
    return out


def build_stats(exports: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """``stats.json`` (§5) from the workers' exports; ``all`` is the seed scope plus the other items."""
    seed: Dict[str, Any] = {}
    property_entities: Dict[str, Any] = {}
    properties: Dict[str, Any] = {"count": 0, "datatype": {}}
    other: Dict[str, int] = {}
    for export in exports:
        _merge(seed, export["seed"])
        _merge(property_entities, export["property_entities"])
        _merge(properties, export["properties"])
        _merge(other, export["other_types"])
    everything: Dict[str, Any] = {}
    _merge(everything, seed)
    for export in exports:
        _merge(everything, export["rest"])
    return {"format": FORMAT_STATS, "naming": WD_ROLES_NAMING,
            "scopes": {"all": _scope_json(everything), "seed": _scope_json(seed),
                       "property_entities": _scope_json(property_entities)},
            "properties": {"count": properties["count"],
                           "datatype": {k: n for k, n in properties["datatype"].items() if n}},
            "other_types": {k: n for k, n in other.items() if n}}


# ------------------------------------------------------------------------------------------------ qualifier usage


#: The two scopes of the qualifier-usage file (§12).
USAGE_SCOPES = {"all": "every entity in the dump: items and property entities",
                "kept": "the seed items of the slice: items with an English Wikipedia article (SPEC §2)"}
_META = frozenset(WD_ROLES_META)
_ROLE_ID = re.compile(r"P(\d+)(:qualifier)?")
_DUMP_NAME = re.compile(r"wikidata-(\d{8})-all\.json\.bz2")


def _id_order(key: str) -> Tuple[Any, ...]:
    """Numeric property-id order: P2 before P10, ``P<id>:qualifier`` right after ``P<id>``; other keys last."""
    m = _ROLE_ID.fullmatch(key)
    return (0, int(m.group(1)), m.group(2) is not None, "") if m else (1, 0, False, key)


def _slot(relation: str, qualifier: str, time_model: Optional[str]) -> str:
    """The slot of ``qualifier`` on ``relation`` under wd-roles r1: rule 6 with 6a. P2241 and P7452 are
    ``rank_reason`` here; the part that rule 6c makes ``meta`` is counted apart."""
    if qualifier in WD_ROLES_TIME:
        return "qualifier" if relation in WD_ROLES_TIME else "time"
    if qualifier in WD_ROLES_RANK_REASON:
        return "rank_reason"
    if qualifier in WD_ROLES_END_CAUSE:
        return "end_cause" if time_model == "interval" else "meta"
    return "meta" if qualifier in _META else "qualifier"


def _usage_relations(scope: Dict[str, Any], out_of_scope: Any) -> Dict[str, Any]:
    """The relations of one scope of ``stats.json`` as the qualifier-usage file writes them (§12)."""
    per_property = scope.get("per_property", {})
    pairs = scope.get("qualifier_pairs", {})
    arities = scope.get("per_property_arity_wd_roles", {})
    relations: Dict[str, Any] = {}
    excluded: Dict[str, Any] = {}
    for pid in sorted(per_property, key=_id_order):
        record = per_property[pid]
        used = pairs.get(pid, {})
        interval = pid not in WD_ROLES_TIME and any(q in used for q in WD_ROLES_TIME)
        time_model = "interval" if interval else None
        roles = {(f"{q}:qualifier" if q == pid else q): q for q in used}  # rules 5 and 6a
        qualifiers = {role: {"statements": used[q][0], "snaks": used[q][1], "slot": _slot(pid, q, time_model)}
                      for role, q in sorted(roles.items(), key=lambda kv: _id_order(kv[0]))}
        arity = arities.get(pid, {})
        entry = {
            "statements": record["statements"],
            "qualifiers": qualifiers,
            "time_model": time_model,
            "left_out_6b": record["multi_time"] if interval else 0,
            "self_qualified": record["self_qualified"],
            "rank_reason_mismatch": {
                "P2241": {"statements": record["p2241_not_deprecated"], "snaks": record["p2241_not_deprecated_snaks"]},
                "P7452": {"statements": record["p7452_not_preferred"], "snaks": record["p7452_not_preferred_snaks"]}},
            "arity": {a: arity[a] for a in sorted(arity, key=int)},
        }
        (excluded if pid in out_of_scope else relations)[pid] = entry
    return {"relations": relations, "out_of_scope_relations": excluded}


def out_of_scope_properties(lines: Any) -> List[str]:
    """Rule 8 from the dump's property entities (JSON lines): the properties whose best-rank P31 values, the
    preferred statements if there are any, else the normal ones, include one of ``OUT_OF_SCOPE_CLASSES``; in
    numeric id order."""
    found = []
    for line in lines:
        if not line.strip():
            continue
        ent = json.loads(line)
        statements = (ent.get("claims") or {}).get("P31") or []
        best = [s for s in statements if s.get("rank") == "preferred"] or \
            [s for s in statements if s.get("rank") == "normal"]
        if {_entity_id(s.get("mainsnak") or {}) for s in best} & OUT_OF_SCOPE_CLASSES:
            found.append(ent["id"])
    return sorted(found, key=_id_order)


def build_usage(record: Dict[str, Any], stats: Dict[str, Any], stats_sha256: str,
                out_of_scope: List[str]) -> Dict[str, Any]:
    """The qualifier-usage document (§12) from a complete run: ``all`` adds up the ``all`` and
    ``property_entities`` scopes of ``stats.json``, ``kept`` is its ``seed`` scope."""
    scopes = stats["scopes"]
    everything: Dict[str, Any] = {}
    for name in ("all", "property_entities"):
        _merge(everything, {key: scopes[name].get(key, {}) for key in _SCOPE_MAPS})
    source = record.get("input") or {}
    dump_file = os.path.basename(source.get("path") or "")
    name = _DUMP_NAME.fullmatch(dump_file)
    excluded = frozenset(out_of_scope)
    return {"format": FORMAT_USAGE, "dump": name.group(1) if name else None, "naming": stats["naming"],
            "source": {"dump_file": dump_file, "md5": source.get("md5"), "sha1": source.get("sha1"),
                       "sha256": source.get("sha256"), "slicer_commit": (record.get("code") or {}).get("git_commit"),
                       "stats_sha256": stats_sha256},
            "scopes": dict(USAGE_SCOPES),
            "out_of_scope": list(out_of_scope),
            "all": _usage_relations(everything, excluded),
            "kept": _usage_relations(scopes["seed"], excluded)}


def usage_text(doc: Dict[str, Any]) -> str:
    """The qualifier-usage document as §12 lays it out: indented by one space as ``indent=1`` writes it, except that
    each relation map holds one relation per line, ``"P39": {...}`` in compact JSON; ``ensure_ascii=False``. The
    text is one JSON document, and ``json.loads`` gives back ``doc``, key order included."""
    shell = dict(doc)
    maps: Dict[str, Dict[str, Any]] = {}
    for scope in ("all", "kept"):
        shell[scope] = {}
        for name, relations in doc[scope].items():
            token = f"\0{scope}/{name}\0"  # written as "\u0000...\u0000": no real key or value looks like it
            shell[scope][name] = token
            maps[json.dumps(token)] = relations
    text = json.dumps(shell, ensure_ascii=False, indent=1)
    for token, relations in maps.items():
        lines = [f"   {json.dumps(pid, ensure_ascii=False)}: "
                 f"{json.dumps(entry, ensure_ascii=False, separators=(',', ':'))}" for pid, entry in relations.items()]
        text = text.replace(token, "{\n" + ",\n".join(lines) + "\n  }" if lines else "{}", 1)
    return text + "\n"


def usage_main(argv: Sequence[str]) -> int:
    """``wdslice.py usage --run DIR --out FILE`` (§12)."""
    parser = argparse.ArgumentParser(
        prog="wdslice.py usage", allow_abbrev=False,
        description="Write the per-relation qualifier usage (p3a-qualifier-usage/1) of a complete pass: reshapes "
                    "DIR/stats.json, and takes rule 8's out-of-scope properties from DIR/properties.jsonl.gz.",
        epilog="Exit status: 0 when the file is written, 1 when the run cannot be used (not complete, another "
               "statistics format or naming, or outputs that do not match run.json), 2 on a usage or I/O error.")
    parser.add_argument("--run", required=True, metavar="DIR", help="the output directory of a complete pass")
    parser.add_argument("--out", required=True, metavar="FILE", help="the file to write (replaced atomically)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)

    def error(status: int, message: str) -> int:
        sys.stderr.write(f"wdslice.py usage: error: {message}\n")
        return status

    try:
        with open(os.path.join(args.run, "run.json"), encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, ValueError) as e:
        return error(2, f"cannot read the run in {args.run}: {e}")
    if record.get("status") != "complete":
        return error(1, f"the run in {args.run} is not complete (status {record.get('status')!r})")
    try:
        with open(os.path.join(args.run, "stats.json"), "rb") as fh:
            stats_bytes = fh.read()
        with open(os.path.join(args.run, "properties.jsonl.gz"), "rb") as fh:
            properties_gz = fh.read()
        stats = json.loads(stats_bytes)
        lines = gzip.decompress(properties_gz).splitlines()
    except (OSError, ValueError, EOFError) as e:
        return error(2, f"cannot read the run in {args.run}: {e}")
    if stats.get("format") != FORMAT_STATS or stats.get("naming") != WD_ROLES_NAMING:
        return error(1, f"stats.json has format {stats.get('format')!r} and naming {stats.get('naming')!r}; "
                        f"this code reads {FORMAT_STATS!r} with {WD_ROLES_NAMING!r}")
    listed = {o.get("file"): o.get("sha256") for o in record.get("outputs") or []}
    for name, data in (("stats.json", stats_bytes), ("properties.jsonl.gz", properties_gz)):
        if listed.get(name) != hashlib.sha256(data).hexdigest():
            return error(1, f"{name} does not match the sha256 that run.json lists for it")
    source = record.get("input") or {}
    if source.get("truncated") or source.get("verified") is not True:
        _say(f"warning: the run read an input that is {'truncated' if source.get('truncated') else 'not verified'}")
    try:
        doc = build_usage(record, stats, hashlib.sha256(stats_bytes).hexdigest(), out_of_scope_properties(lines))
    except (ValueError, KeyError, TypeError) as e:
        return error(1, f"cannot reshape the statistics: {type(e).__name__}: {e}")
    out = os.path.abspath(args.out)
    try:
        _write_atomic(os.path.dirname(out), os.path.basename(out), usage_text(doc))
    except OSError as e:
        return error(2, f"cannot write {out}: {e}")
    _say(f"wrote {out}: {len(doc['all']['relations']):,} relations in all, {len(doc['kept']['relations']):,} kept, "
         f"{len(doc['out_of_scope'])} properties out of scope")
    return 0


# ------------------------------------------------------------------------------------------------ main process


class RunFailed(Exception):
    """Ends the run with ``status: failed``; the message goes to ``run.json``."""


class _Signal(BaseException):
    """Raised in the main thread by the SIGTERM and SIGHUP handlers."""


def _utc(t: Optional[float] = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _say(line: str) -> None:
    """A progress or diagnostic line on stderr."""
    with contextlib.suppress(Exception):
        sys.stderr.write(f"wdslice {_utc()}: {line}\n")
        sys.stderr.flush()


class _Reader:
    """The reader thread (§7): reads the input, hashes and decompresses it, and hands batches to the workers."""

    def __init__(self, run: "_Run") -> None:
        args = run.args
        self.run = run
        self.follow: bool = args.follow
        self.expected_size: Optional[int] = args.expect_size
        self.limit: Optional[int] = args.max_input_bytes
        self.allow_truncated: bool = args.allow_truncated or args.max_input_bytes is not None
        self.batch_bytes: int = args.batch_bytes
        self.stall_timeout: float = args.stall_timeout
        self.bytes_read = 0
        self.decompressed = 0
        self.batched = 0
        self.batches = 0
        self.streams = 0
        self.waiting = False
        self.waited_s = 0.0
        self.truncated = False
        self.cut = False
        self.finished = False
        self.file_size = 0
        self.hashes = {"md5": hashlib.md5(usedforsecurity=False), "sha1": hashlib.sha1(usedforsecurity=False),
                       "sha256": hashlib.sha256()}
        self._decompressor = bz2.BZ2Decompressor()
        self._in_stream = False
        self._parts: List[bytes] = []
        self._pending = 0
        self.thread = threading.Thread(target=self._main, name="wdslice-reader", daemon=True)

    def _main(self) -> None:
        try:
            self._read()
            self.finished = True
        except RunFailed as e:
            self.run.fail(str(e))
        except BaseException:
            self.run.fail("reader: " + traceback.format_exc().rstrip())

    def _read(self) -> None:
        run = self.run
        stop = run.stop
        with open(run.input_path, "rb", buffering=0) as f:
            st = os.fstat(f.fileno())
            self.file_size = st.st_size
            if self.expected_size is not None and st.st_size > self.expected_size:
                raise RunFailed(f"the input has {st.st_size} bytes, more than --expect-size {self.expected_size}")
            last_size, last_growth = st.st_size, time.monotonic()
            pos = 0
            while not stop.is_set():
                want = READ_CHUNK
                if self.limit is not None:
                    want = min(want, self.limit - pos)
                    if want <= 0:
                        self.cut = (pos < self.expected_size) if self.follow else os.fstat(f.fileno()).st_size > pos
                        break
                if self.follow:
                    want = min(want, self.expected_size - pos)
                    if want <= 0:
                        break
                data = f.read(want)
                if not data:
                    if not self.follow:
                        break
                    # caught up with the download: wait, then retry at the same offset
                    self.waiting = True
                    started = time.monotonic()
                    st = os.fstat(f.fileno())
                    if st.st_size > last_size:
                        last_growth = started
                    last_size = st.st_size
                    with contextlib.suppress(FileNotFoundError):
                        now = os.stat(run.input_path)
                        if (now.st_ino, now.st_dev) != (st.st_ino, st.st_dev):
                            raise RunFailed(f"the input was replaced by another file after {pos} bytes")
                    if started - last_growth >= self.stall_timeout:
                        raise RunFailed(f"the input did not grow for {self.stall_timeout:g} s "
                                        f"({pos} of {self.expected_size} bytes read)")
                    stop.wait(FOLLOW_SLEEP_S)
                    self.waited_s += time.monotonic() - started
                    f.seek(pos)
                    continue
                self.waiting = False
                last_growth = time.monotonic()
                pos += len(data)
                for h in self.hashes.values():
                    h.update(data)
                self.bytes_read = pos
                self._feed(data)
            if stop.is_set():
                return
            self._finish()

    def _feed(self, data: bytes) -> None:
        """Decompresses ``data``; starts a new decompressor on the unused data at the end of a stream."""
        d = self._decompressor
        while True:
            if data:
                self._in_stream = True
            try:
                out = d.decompress(data, MAX_OUTPUT)
            except OSError as e:
                raise RunFailed(f"invalid bz2 data in stream {self.streams + 1} "
                                f"(within the first {self.bytes_read} bytes): {e}") from None
            data = b""
            if out:
                self._add(out)
            if d.eof:
                data = d.unused_data
                self._decompressor = d = bz2.BZ2Decompressor()
                self._in_stream = False
                self.streams += 1
                if not data:
                    return
            elif not out and d.needs_input:
                return

    def _add(self, out: bytes) -> None:
        """Adds decompressed text; cuts every batch that is complete. A batch ends at the first newline at offset
        ``batch_bytes`` or later from its start, so it holds whole lines and more than ``batch_bytes`` bytes."""
        self.decompressed += len(out)
        self._parts.append(out)
        self._pending += len(out)
        if self._pending <= self.batch_bytes:
            return
        buf = self._parts[0] if len(self._parts) == 1 else b"".join(self._parts)
        start = 0
        while len(buf) - start > self.batch_bytes:
            end = buf.find(b"\n", start + self.batch_bytes)
            if end < 0:
                break
            self._submit(buf[start:end + 1])
            start = end + 1
        rest = buf[start:] if start else buf
        self._parts = [rest] if rest else []
        self._pending = len(rest)

    def _submit(self, blob: bytes) -> None:
        """Hands one batch to the workers; blocks while the in-flight window or the task queue is full."""
        run = self.run
        while not run.window.acquire(timeout=0.5):
            if run.stop.is_set():
                raise RunFailed("stopped")
        task = (self.batches, blob)
        while True:
            try:
                run.tasks.put(task, timeout=0.5)
                break
            except queue.Full:
                if run.stop.is_set():
                    raise RunFailed("stopped") from None
        self.batches += 1
        self.batched += len(blob)

    def _finish(self) -> None:
        """End of input: truncation, the last batch, verification, the workers' stop sentinels."""
        if self.bytes_read == 0:
            raise RunFailed("the input is empty")
        tail = b"".join(self._parts)
        self._parts, self._pending = [], 0
        if self._in_stream:
            if not self.allow_truncated:
                raise RunFailed(f"the input ends inside a bz2 stream after {self.bytes_read} bytes (truncated); "
                                "--allow-truncated accepts it")
            self.truncated = True
            tail = tail[:tail.rfind(b"\n") + 1]  # the trailing partial line is dropped
        if tail:
            self._submit(tail)
        self.run.verify(self)
        for _ in range(self.run.n_workers):
            while True:
                try:
                    self.run.tasks.put(None, timeout=0.5)
                    break
                except queue.Full:
                    if self.run.stop.is_set():
                        raise RunFailed("stopped") from None


class _Sink:
    """One output kind: shard files ``pattern.format(n)`` of at most about ``limit`` rows, or one file when
    ``limit`` is None. The first file exists from the start; later shards open when their first rows arrive."""

    def __init__(self, directory: str, pattern: str, limit: Optional[int]) -> None:
        self.directory = directory
        self.pattern = pattern
        self.limit = limit
        self.number = 0
        self.done: List[Dict[str, Any]] = []
        self._fh: Any = None
        self._open()

    def _open(self) -> None:
        name = self.pattern.format(self.number)
        self._fh = open(os.path.join(self.directory, name), "xb")
        self._record: Dict[str, Any] = {"file": name, "bytes": 0, "sha256": None, "rows": 0}
        self._hash = hashlib.sha256()

    def add(self, member: bytes, rows: int) -> None:
        if not rows:
            return
        if self._fh is None:
            self._open()
        self._fh.write(member)
        self._hash.update(member)
        self._record["bytes"] += len(member)
        self._record["rows"] += rows
        if self.limit is not None and self._record["rows"] >= self.limit:
            self._close(sync=True)
            self.number += 1

    def _close(self, sync: bool) -> None:
        fh, self._fh = self._fh, None
        try:
            fh.flush()
            if sync:
                os.fsync(fh.fileno())
        finally:
            fh.close()
        self._record["sha256"] = self._hash.hexdigest()
        self.done.append(self._record)

    def close(self, sync: bool = True) -> None:
        if self._fh is not None:
            self._close(sync)

    def records(self) -> List[Dict[str, Any]]:
        """The files written so far; an open one with the hash of what it holds."""
        out = list(self.done)
        if self._fh is not None:
            out.append(dict(self._record, sha256=self._hash.hexdigest()))
        return out


def _write_atomic(directory: str, name: str, text: str) -> None:
    """Writes ``name`` in ``directory`` through a temporary file, fsync and rename, then fsyncs the directory
    (where the file system allows it)."""
    tmp = os.path.join(directory, f".{name}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, os.path.join(directory, name))
    with contextlib.suppress(OSError):
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _code_info() -> Dict[str, Any]:
    """The script's sha256, the git commit of its checkout, whether the script differs from that commit (or is
    untracked), and the Python version; null where it cannot be found out."""
    info: Dict[str, Any] = {"script_sha256": None, "git_commit": None, "git_dirty": None,
                            "python": platform.python_version()}
    script = os.path.abspath(__file__)
    with contextlib.suppress(OSError):
        with open(script, "rb") as fh:
            info["script_sha256"] = hashlib.sha256(fh.read()).hexdigest()
    here = os.path.dirname(script)
    with contextlib.suppress(Exception):
        head = subprocess.run(["git", "-C", here, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20)
        if head.returncode == 0:
            info["git_commit"] = head.stdout.strip()
            status = subprocess.run(["git", "-C", here, "status", "--porcelain", "--", os.path.basename(script)],
                                    capture_output=True, text=True, timeout=20)
            if status.returncode == 0:
                info["git_dirty"] = bool(status.stdout.strip())
    return info


class _Run:
    """One pass: the output directory, the workers, the reader thread and the writer (the main thread)."""

    def __init__(self, args: argparse.Namespace, n_workers: int) -> None:
        self.args = args
        self.n_workers = n_workers
        self.input_path = os.path.abspath(args.input)
        self.out = os.path.abspath(args.out)
        self.stop = threading.Event()
        self.error: Optional[str] = None
        self._error_lock = threading.Lock()
        self.window = threading.Semaphore(4 * n_workers)
        self.verified: Optional[bool] = None
        self.counts = [0] * len(COUNT_KEYS)
        self.started = time.time()
        self.t0 = time.monotonic()
        self.sinks: List[_Sink] = []
        self.stats_record: Optional[Dict[str, Any]] = None
        self.code: Dict[str, Any] = {"script_sha256": None, "git_commit": None, "git_dirty": None,
                                     "python": platform.python_version()}
        self.tasks: Any = None
        self.procs: List[Any] = []
        self.conns: List[Any] = []
        self.reader: Optional[_Reader] = None

    # ---- failure

    def fail(self, message: str) -> None:
        """Records the first error and asks every part of the pass to stop."""
        with self._error_lock:
            if self.error is None:
                self.error = message
        self.stop.set()

    def verify(self, reader: _Reader) -> None:
        """Compares the input with ``--expect-*`` once it is read (§6); a mismatch fails the run. Nothing is
        compared when ``--max-input-bytes`` stopped the read early."""
        args = self.args
        if reader.cut:
            return
        mismatches = []
        checked = False
        if args.expect_size is not None:
            checked = True
            size = os.stat(self.input_path).st_size if args.follow else reader.bytes_read
            if reader.bytes_read != args.expect_size or size != args.expect_size:
                mismatches.append(f"size: expected {args.expect_size} bytes, read {reader.bytes_read}, "
                                  f"the file has {size}")
        for name, expected in (("md5", args.expect_md5), ("sha1", args.expect_sha1)):
            if expected is not None:
                checked = True
                got = reader.hashes[name].hexdigest()
                if got != expected:
                    mismatches.append(f"{name}: expected {expected}, got {got}")
        if checked:
            self.verified = not mismatches
        if mismatches:
            raise RunFailed("the input does not match: " + "; ".join(mismatches))

    # ---- run.json

    def record(self, status: str) -> Dict[str, Any]:
        args, reader = self.args, self.reader
        params = {k: v for k, v in vars(args).items()}
        params["workers"] = self.n_workers
        finished = None if status == "running" else _utc()
        hashes = {name: None for name in ("md5", "sha1", "sha256")}
        if reader is not None and reader.bytes_read:
            hashes = {name: h.hexdigest() for name, h in reader.hashes.items()}
        outputs = [r for sink in self.sinks for r in sink.records()]
        if self.stats_record is not None:
            outputs.append(self.stats_record)
        return {
            "format": FORMAT_RUN, "status": status, "error": self.error if status == "failed" else None,
            "started": _utc(self.started), "finished": finished, "params": params,
            "input": {"path": self.input_path, "expected_size": args.expect_size,
                      "bytes_read": reader.bytes_read if reader else 0, **hashes,
                      "expected_md5": args.expect_md5, "expected_sha1": args.expect_sha1,
                      "verified": self.verified, "truncated": reader.truncated if reader else False},
            "code": self.code,
            "counts": dict(zip(COUNT_KEYS, self.counts)),
            "outputs": outputs,
            "timings": {"wall_s": round(time.monotonic() - self.t0, 3),
                        "waited_s": round(reader.waited_s, 3) if reader else 0.0},
        }

    def write_record(self, status: str) -> None:
        _write_atomic(self.out, "run.json", json.dumps(self.record(status), indent=1))

    # ---- the pass

    def execute(self) -> None:
        ctx = multiprocessing.get_context("spawn")
        self.sinks = [_Sink(self.out, "items-{:04d}.jsonl.gz", self.args.shard_items),
                      _Sink(self.out, "index-{:04d}.jsonl.gz", self.args.index_shard_rows),
                      _Sink(self.out, "properties.jsonl.gz", None)]
        self.tasks = ctx.Queue(maxsize=2 * self.n_workers)
        for wid in range(self.n_workers):
            receiver, sender = ctx.Pipe(duplex=False)
            proc = ctx.Process(target=_worker_main, args=(wid, self.tasks, sender), name=f"wdslice-worker-{wid}",
                               daemon=True)
            proc.start()
            sender.close()  # the worker holds the only sending end, so its exit reads as EOF here
            self.procs.append(proc)
            self.conns.append(receiver)
        self.reader = _Reader(self)
        self.reader.thread.start()
        self._write_loop()

    def _write_loop(self) -> None:
        reader = self.reader
        assert reader is not None
        pending: Dict[int, Tuple[Any, ...]] = {}
        exports: Dict[int, Dict[str, Any]] = {}
        live = dict(zip(self.conns, range(self.n_workers)))
        next_seq = 0
        last_t, last_bytes = time.monotonic(), 0
        while True:
            if self.stop.is_set():
                raise RunFailed(self.error or "stopped")
            if reader.finished and next_seq == reader.batches and len(exports) == self.n_workers:
                break
            for conn in multiprocessing.connection.wait(list(live), timeout=0.5):
                wid = live[conn]
                try:
                    msg = conn.recv()
                except (EOFError, OSError):
                    del live[conn]
                    if wid not in exports:
                        code = self.procs[wid].exitcode
                        self.procs[wid].join(1.0)
                        code = self.procs[wid].exitcode if code is None else code
                        raise RunFailed(f"worker {wid} exited unexpectedly (exit code {code})") from None
                    continue
                if msg[0] == "batch":
                    pending[msg[1]] = msg
                    while next_seq in pending:
                        _, _, items, index, props, counts = pending.pop(next_seq)
                        self.sinks[0].add(items, counts[4])
                        self.sinks[1].add(index, counts[5])
                        self.sinks[2].add(props, counts[2])
                        self.counts = [a + b for a, b in zip(self.counts, counts)]
                        next_seq += 1
                        self.window.release()
                elif msg[0] == "stats":
                    exports[wid] = msg[2]
                else:
                    raise RunFailed(f"worker {wid} failed:\n{msg[2].rstrip()}")
            now = time.monotonic()
            if now - last_t >= PROGRESS_S:
                self._progress(now - last_t, reader.bytes_read - last_bytes)
                last_t, last_bytes = now, reader.bytes_read
        self._complete([exports[w] for w in sorted(exports)])

    def _progress(self, interval: float, delta: int) -> None:
        reader = self.reader
        assert reader is not None
        total = self.args.expect_size or reader.file_size
        if self.args.max_input_bytes is not None:
            total = min(total, self.args.max_input_bytes) if total else self.args.max_input_bytes
        total = max(total, reader.bytes_read)
        rate = delta / interval if interval > 0 else 0.0
        remaining = total - reader.bytes_read
        if remaining <= 0:
            eta = "ETA now"
        elif rate > 0:
            seconds = remaining / rate
            eta = f"ETA {time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(time.time() + seconds))} " \
                  f"(in {seconds / 3600:.1f} h)"
        else:
            eta = "ETA unknown"
        pct = 100.0 * reader.bytes_read / total if total else 0.0
        _say(f"read {reader.bytes_read / 1e9:.3f} GB ({pct:.2f}% of {total / 1e9:.3f} GB) at {rate / 1e6:.2f} MB/s; "
             f"{reader.decompressed / 1e9:.2f} GB uncompressed; {self.counts[0]:,} entities, "
             f"{self.counts[4]:,} seeds; {'waiting for the download' if reader.waiting else 'reading'}; {eta}")

    def _complete(self, exports: List[Dict[str, Any]]) -> None:
        for proc in self.procs:
            proc.join(30.0)
        for sink in self.sinks:
            sink.close(sync=True)
        stats = build_stats(exports)
        scopes = stats["scopes"]
        expected = {"items": scopes["all"]["entities"], "seeds": scopes["seed"]["entities"],
                    "properties": stats["properties"]["count"], "other": sum(stats["other_types"].values()),
                    "statements_all": scopes["all"]["statements"], "statements_seed": scopes["seed"]["statements"]}
        counts = dict(zip(COUNT_KEYS, self.counts))
        wrong = {k: (counts[k], v) for k, v in expected.items() if counts[k] != v}
        if scopes["property_entities"]["entities"] != counts["properties"]:
            wrong["property_entities"] = (counts["properties"], scopes["property_entities"]["entities"])
        if wrong:
            raise RunFailed(f"internal error: batch counts and statistics disagree: {wrong}")
        text = json.dumps(stats, sort_keys=True, indent=1)
        _write_atomic(self.out, "stats.json", text)
        data = text.encode("utf-8")
        self.stats_record = {"file": "stats.json", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                             "rows": None}

    def shutdown(self, failed: bool) -> None:
        """Stops the reader thread and the workers (SIGTERM, then SIGKILL): no worker outlives the pass."""
        if failed:
            self.stop.set()
        if self.reader is not None and self.reader.thread.is_alive():
            self.reader.thread.join(10.0)
        for proc in self.procs:
            if proc.is_alive():
                with contextlib.suppress(Exception):
                    proc.terminate()
        for proc in self.procs:
            proc.join(5.0)
            if proc.is_alive():
                with contextlib.suppress(Exception):
                    proc.kill()
                proc.join(5.0)
        for conn in self.conns:
            with contextlib.suppress(Exception):
                conn.close()
        if self.tasks is not None:
            if failed:
                # take the batches still queued, so that the queue's feeder thread is not left blocked on a full
                # pipe; in a helper thread, as a worker killed while reading a task can leave a partial message
                def drain() -> None:
                    with contextlib.suppress(Exception):
                        while True:
                            self.tasks.get(timeout=0.2)
                helper = threading.Thread(target=drain, name="wdslice-drain", daemon=True)
                helper.start()
                helper.join(2.0)
                self.tasks.cancel_join_thread()
            with contextlib.suppress(Exception):
                self.tasks.close()
            if not failed:
                with contextlib.suppress(Exception):
                    self.tasks.join_thread()
        for sink in self.sinks:
            with contextlib.suppress(Exception):
                sink.close(sync=not failed)


# ------------------------------------------------------------------------------------------------ command line


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1: {text!r}")
    return value


def _positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not value > 0 or value == float("inf"):
        raise argparse.ArgumentTypeError(f"must be a positive number: {text!r}")
    return value


def _hex_digest(length: int):
    def parse(text: str) -> str:
        if not re.fullmatch(f"[0-9a-fA-F]{{{length}}}", text):
            raise argparse.ArgumentTypeError(f"not {length} hexadecimal digits: {text!r}")
        return text.lower()
    return parse


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wdslice.py [run]", allow_abbrev=False,
        description="Cut a Wikidata JSON dump (.json.bz2) into the P3a slice in one streaming pass (SPEC.md). "
                    "'wdslice.py usage --help' describes the qualifier-usage subcommand.",
        epilog="Exit status: 0 when the run is complete, 1 when it fails (run.json says why), 2 on a usage error.")
    p.add_argument("--input", required=True, help="the dump, .json.bz2 (single- or multi-stream)")
    p.add_argument("--out", required=True, help="the output directory (created if missing)")
    p.add_argument("--follow", action="store_true",
                   help="the input is still being downloaded: wait for it until it has --expect-size bytes")
    p.add_argument("--expect-size", type=_positive_int, metavar="N", help="the input's size in bytes")
    p.add_argument("--expect-md5", type=_hex_digest(32), metavar="H", help="the input's published md5")
    p.add_argument("--expect-sha1", type=_hex_digest(40), metavar="H", help="the input's published sha1")
    p.add_argument("--workers", type=_positive_int, metavar="N",
                   help="worker processes (default: the number of CPUs minus 2, at least 1)")
    p.add_argument("--batch-bytes", type=_positive_int, default=DEFAULT_BATCH_BYTES, metavar="N",
                   help="a batch ends at the first newline at or after N bytes from its start (default 16 MiB)")
    p.add_argument("--shard-items", type=_positive_int, default=DEFAULT_SHARD_ITEMS, metavar="N",
                   help="close an items shard after the batch that brings it to N rows (default 250,000)")
    p.add_argument("--index-shard-rows", type=_positive_int, default=DEFAULT_INDEX_SHARD_ROWS, metavar="N",
                   help="close an index shard after the batch that brings it to N rows (default 10,000,000)")
    p.add_argument("--max-input-bytes", type=_positive_int, metavar="N",
                   help="stop after N compressed bytes (implies --allow-truncated)")
    p.add_argument("--allow-truncated", action="store_true",
                   help="accept an input that ends inside a bz2 stream; its trailing partial line is dropped")
    p.add_argument("--stall-timeout", type=_positive_float, default=DEFAULT_STALL_TIMEOUT, metavar="S",
                   help="in follow mode, fail when the input does not grow for S seconds (default 21,600)")
    p.add_argument("--force", action="store_true",
                   help="remove the outputs of an earlier run in --out first")
    return p


def _prepare_out(out: str, force: bool) -> int:
    """Creates and locks the output directory; refuses one that holds an earlier run's outputs unless ``force``,
    which removes them. Returns the locked directory descriptor."""
    os.makedirs(out, exist_ok=True)
    fd = os.open(out, os.O_RDONLY)
    try:
        if fcntl is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise _Usage(f"another run is writing to {out}") from None
            except OSError:
                pass  # a file system without flock: the lock is a safeguard, not a requirement
        old = sorted(name for name in os.listdir(out) if _OUTPUT_NAME.fullmatch(name))
        if old and not force:
            what = "run.json" if "run.json" in old else ", ".join(old[:3]) + (", ..." if len(old) > 3 else "")
            raise _Usage(f"{out} holds the outputs of an earlier run ({what}); --force removes them")
        for name in old:
            os.remove(os.path.join(out, name))
    except BaseException:
        os.close(fd)
        raise
    return fd


class _Usage(Exception):
    """A usage error: exit 2 before anything is written."""


def _raise_signal(signum: int, frame: Any) -> None:
    raise _Signal(signum)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """``wdslice.py [run] OPTIONS`` runs the pass (§8; ``run`` may be left out); ``wdslice.py usage --run DIR --out
    FILE`` writes the qualifier usage of a complete pass (§12)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["usage"]:
        return usage_main(args[1:])
    return run_main(args[1:] if args[:1] == ["run"] else args)


def run_main(argv: Sequence[str]) -> int:
    """The pass (§7, §8)."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    if args.follow and args.expect_size is None:
        parser.print_usage(sys.stderr)
        sys.stderr.write("wdslice.py: error: --follow requires --expect-size\n")
        return 2
    if not os.path.isfile(args.input):
        sys.stderr.write(f"wdslice.py: error: no such file: {args.input}\n")
        return 2
    if os.path.exists(args.out) and not os.path.isdir(args.out):
        sys.stderr.write(f"wdslice.py: error: not a directory: {args.out}\n")
        return 2
    n_workers = args.workers or max(1, (os.cpu_count() or 1) - 2)
    try:
        lock_fd = _prepare_out(os.path.abspath(args.out), args.force)
    except (_Usage, OSError) as e:
        sys.stderr.write(f"wdslice.py: error: {e}\n")
        return 2

    # SIGTERM and SIGHUP (unless ignored, as under nohup) end the pass like SIGINT does; all three are ignored
    # while the pass winds up, so that run.json always says how it ended
    signals = [s for s in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGHUP", None)) if s is not None]
    original = {}
    if threading.current_thread() is threading.main_thread():
        original = {s: signal.getsignal(s) for s in signals}
        for s in signals[1:]:
            if original[s] == signal.SIG_DFL:
                signal.signal(s, _raise_signal)
    run = _Run(args, n_workers)
    status = "failed"
    try:
        run.code = _code_info()
        run.write_record("running")
        _say(f"reading {run.input_path} with {n_workers} workers into {run.out}"
             + (f"; following the download to {args.expect_size:,} bytes" if args.follow else ""))
        run.execute()
        status = "complete"
    except RunFailed as e:
        run.fail(str(e))
    except KeyboardInterrupt:
        run.fail("interrupted (SIGINT)")
    except _Signal as e:
        run.fail(f"terminated (signal {e.args[0]})")
    except BaseException:
        run.fail("writer: " + traceback.format_exc().rstrip())
    finally:
        for s in original:
            signal.signal(s, signal.SIG_IGN)
        try:
            run.shutdown(failed=status != "complete")
            if status == "complete" and run.error is not None:  # a late failure, e.g. from the reader
                status = "failed"
            run.write_record(status)
        except BaseException as e:
            status = "failed"
            _say(f"could not write run.json: {e!r}")
        finally:
            for s, handler in original.items():
                signal.signal(s, handler)
            os.close(lock_fd)
    if status == "complete":
        c = dict(zip(COUNT_KEYS, run.counts))
        _say(f"complete: {c['entities']:,} entities, {c['seeds']:,} seeds, {c['index_rows']:,} index rows "
             f"in {time.monotonic() - run.t0:.1f} s")
        return 0
    _say("failed: " + (run.error or "unknown error").splitlines()[0])
    return 1


if __name__ == "__main__":
    sys.exit(main())
