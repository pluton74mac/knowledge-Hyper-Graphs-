"""Tests of the P3a dump slicer ``wdslice.py`` (SPEC §9), with ``unittest``.

Run from the repository root: ``python3.11 -m unittest discover -s projects/p3a-clean-nary-corpus/slice -v``.

The tests build synthetic dumps from entity JSON in the shapes of the 20260922 dump (SPEC §0): the top-level keys in
the dump's order, statements as ``mainsnak, type, qualifiers, qualifiers-order, id, rank, references``, qualifier
snaks with a ``hash``, main and reference snaks without, reference blocks with ``hash, snaks, snaks-order``, and
non-ASCII text written as ``\\u`` escapes, as the dump writes it. The expected statistics of ``MAIN`` are computed by
hand in the comments of ``EXPECTED_STATS``. Most runs call ``wdslice.main`` in this process (the workers are spawned
processes); the signal tests run the script in a child process.
"""
from __future__ import annotations

import _thread
import bz2
import contextlib
import copy
import gzip
import hashlib
import io
import json
import multiprocessing
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
import zlib
from collections import defaultdict
from typing import Any, Dict, List, Optional
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "wdslice.py")
#: Seconds after which an in-process run is interrupted; every run here takes well under one second.
WATCHDOG_S = 60.0
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import wdslice  # noqa: E402

CALENDAR = "http://www.wikidata.org/entity/Q1985727"
DATATYPE = {"wikibase-entityid": "wikibase-item", "time": "time", "quantity": "quantity",
            "monolingualtext": "monolingualtext", "string": "string"}
ENVELOPE_KEYS = ["type", "id", "lastrevid", "modified", "labels", "descriptions", "aliases", "sitelinks",
                 "x_sitelink_count", "claims"]

# ------------------------------------------------------------------------------------------------ entity JSON


def item_value(qid: str) -> Dict[str, Any]:
    return {"value": {"entity-type": "item", "numeric-id": int(qid[1:]), "id": qid}, "type": "wikibase-entityid"}


def time_value(t: str) -> Dict[str, Any]:
    return {"value": {"time": t, "timezone": 0, "before": 0, "after": 0, "precision": 11,
                      "calendarmodel": CALENDAR}, "type": "time"}


def quantity_value(amount: str) -> Dict[str, Any]:
    return {"value": {"amount": amount, "unit": "1"}, "type": "quantity"}


def text_value(text: str, language: str) -> Dict[str, Any]:
    return {"value": {"text": text, "language": language}, "type": "monolingualtext"}


def string_value(s: str) -> Dict[str, Any]:
    return {"value": s, "type": "string"}


def snak(prop: str, value: Optional[Dict[str, Any]] = None, snaktype: str = "value",
         datatype: Optional[str] = None, qualifier: bool = False) -> Dict[str, Any]:
    """A snak in the dump's key order; only a qualifier snak carries a ``hash``."""
    s: Dict[str, Any] = {"snaktype": snaktype, "property": prop}
    if qualifier:
        s["hash"] = hashlib.sha1(json.dumps([prop, snaktype, value], sort_keys=True).encode()).hexdigest()
    if value is not None:
        s["datavalue"] = value
    s["datatype"] = datatype or DATATYPE[value["type"]]  # type: ignore[index]
    return s


def qual(prop: str, value: Optional[Dict[str, Any]] = None, snaktype: str = "value",
         datatype: Optional[str] = None) -> Dict[str, Any]:
    return snak(prop, value, snaktype, datatype, qualifier=True)


def reference(*snaks: Dict[str, Any]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for s in snaks:
        grouped.setdefault(s["property"], []).append(s)
    return {"hash": hashlib.sha1(json.dumps(grouped, sort_keys=True).encode()).hexdigest(), "snaks": grouped,
            "snaks-order": list(grouped)}


_statement_numbers = iter(range(1, 1 << 30))


def statement(subject: str, mainsnak: Dict[str, Any], rank: str = "normal", qualifiers: Any = (),
              references: Any = ()) -> Dict[str, Any]:
    s: Dict[str, Any] = {"mainsnak": mainsnak, "type": "statement"}
    if qualifiers:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for q in qualifiers:
            grouped.setdefault(q["property"], []).append(q)
        s["qualifiers"] = grouped
        s["qualifiers-order"] = list(grouped)
    s["id"] = f"{subject}${uuid.UUID(int=next(_statement_numbers))}"
    s["rank"] = rank
    if references:
        s["references"] = list(references)
    return s


def claims(*statements: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for s in statements:
        out.setdefault(s["mainsnak"]["property"], []).append(s)
    return out


def terms(values: Dict[str, str]) -> Dict[str, Any]:
    return {lang: {"language": lang, "value": v} for lang, v in values.items()}


def alias_terms(values: Dict[str, List[str]]) -> Dict[str, Any]:
    return {lang: [{"language": lang, "value": v} for v in vs] for lang, vs in values.items()}


def sitelink_map(values: Dict[str, str]) -> Dict[str, Any]:
    return {site: {"site": site, "title": title, "badges": []} for site, title in values.items()}


def item(qid: str, n: int, labels: Dict[str, str], descriptions: Dict[str, str], aliases: Dict[str, List[str]],
         claim_map: Dict[str, Any], sitelinks: Dict[str, str]) -> Dict[str, Any]:
    return {"type": "item", "id": qid, "labels": terms(labels), "descriptions": terms(descriptions),
            "aliases": alias_terms(aliases), "claims": claim_map, "sitelinks": sitelink_map(sitelinks),
            "pageid": 100 + n, "ns": 0, "title": qid, "lastrevid": 2400000000 + n,
            "modified": f"2026-09-2{n % 10}T12:00:0{n % 10}Z"}


def dump_text(entities: List[Dict[str, Any]], final_newline: bool = True) -> bytes:
    """The dump as the 20260922 file writes it: ``[``, one entity per line with a trailing comma but the last,
    ``]``; ASCII, non-ASCII as ``\\u`` escapes."""
    lines = [json.dumps(e, separators=(",", ":")).encode("ascii") for e in entities]
    return b"[\n" + b",\n".join(lines) + b"\n]" + (b"\n" if final_newline else b"")


def prop(pid: str, n: int, datatype: str, label: str, claim_map: Dict[str, Any]) -> Dict[str, Any]:
    """A property entity in the dump's key order (no sitelinks)."""
    return {"type": "property", "datatype": datatype, "id": pid, "labels": terms({"en": label}), "descriptions": {},
            "aliases": {}, "claims": claim_map, "pageid": 100 + n, "ns": 120, "title": f"Property:{pid}",
            "lastrevid": 2400000000 + n, "modified": f"2026-09-2{n % 10}T12:00:0{n % 10}Z"}


def build_main() -> List[Dict[str, Any]]:
    """The entities of SPEC §9.1: (a) to (e), plus (f) a class without an enwiki sitelink, (g) a lexeme, and three
    more property entities for rule 8 of wd-roles: (h) P1855 and (i) P2302 are out of scope by their best-rank P31,
    (j) P1647 is not (its preferred P31 hides the normal Q19820110). (a) also has what §9.2 and §12 ask for: two P580
    snaks (S11), a P131 statement qualified by P131 (S12), a normal-rank statement with P2241 (S13), a meta
    qualifier P1810 (S11), P1534 on a relation with the interval model (S14) and on one without (S10), and a P580
    statement qualified by P580 and twice by P582 (S15, rule 6a: multi_time but nothing left out under 6b); S16
    comes before S11, so the pair (P108, P580) recurs with two snaks; S13 has two P2241 snaks. (f) has a
    normal-rank statement with two P7452 snaks (F6) and one with two P580 and two P582 snaks (F7)."""
    a = "Q1001"
    s1 = statement(a, snak("P31", item_value("Q5")), references=[
        reference(snak("P248", item_value("Q36578")), snak("P813", time_value("+2026-09-01T00:00:00Z")))])
    s2 = statement(a, snak("P39", item_value("Q30185")), qualifiers=[
        qual("P580", time_value("+1990-01-01T00:00:00Z")), qual("P582", time_value("+1998-01-01T00:00:00Z")),
        qual("P1365", item_value("Q1010"))], references=[reference(snak("P143", item_value("Q328")))])
    s3 = statement(a, snak("P1082", quantity_value("+1000")),
                   qualifiers=[qual("P585", time_value("+2019-01-01T00:00:00Z"))])
    s4 = statement(a, snak("P1082", quantity_value("+1200")), rank="preferred", qualifiers=[
        qual("P585", time_value("+2020-01-01T00:00:00Z")), qual("P7452", item_value("Q98386534"))])
    s5 = statement(a, snak("P569", time_value("+1950-01-02T00:00:00Z")), rank="deprecated",
                   qualifiers=[qual("P2241", item_value("Q41755623"))])
    s6 = statement(a, snak("P569", time_value("+1950-02-01T00:00:00Z")),
                   references=[reference(snak("P248", item_value("Q36578")))])
    s7 = statement(a, snak("P22", snaktype="somevalue", datatype="wikibase-item"))
    s8 = statement(a, snak("P26", item_value("Q1011")), qualifiers=[
        qual("P580", time_value("+1980-06-01T00:00:00Z")), qual("P582", snaktype="novalue", datatype="time")])
    s9 = statement(a, snak("P40", snaktype="novalue", datatype="wikibase-item"))
    s10 = statement(a, snak("P166", item_value("Q1012")), qualifiers=[
        qual("P1027", item_value("Q1013")), qual("P1027", item_value("Q1014")),
        qual("P1534", item_value("Q1021"))], references=[
        reference(snak("P248", item_value("Q36578")),
                  snak("P854", string_value("https://example.org/awards/1990"), datatype="url"))])
    s11 = statement(a, snak("P108", item_value("Q1015")), qualifiers=[
        qual("P580", time_value("+2000-01-01T00:00:00Z")), qual("P580", time_value("+2001-01-01T00:00:00Z")),
        qual("P582", time_value("+2005-01-01T00:00:00Z")), qual("P1810", string_value("Kowalska A."))])
    s12 = statement(a, snak("P131", item_value("Q1016")), qualifiers=[qual("P131", item_value("Q1017"))])
    s13 = statement(a, snak("P106", item_value("Q170790")), qualifiers=[
        qual("P2241", item_value("Q41755623")), qual("P2241", item_value("Q25895909"))])
    s14 = statement(a, snak("P39", item_value("Q30187")), qualifiers=[
        qual("P580", time_value("+1998-01-01T00:00:00Z")), qual("P582", time_value("+2002-01-01T00:00:00Z")),
        qual("P1534", item_value("Q1018"))])
    s15 = statement(a, snak("P580", time_value("+1990-06-01T00:00:00Z")), qualifiers=[
        qual("P580", time_value("+1990-01-01T00:00:00Z")), qual("P582", time_value("+1991-01-01T00:00:00Z")),
        qual("P582", time_value("+1992-01-01T00:00:00Z"))])
    s16 = statement(a, snak("P108", item_value("Q1020")),
                    qualifiers=[qual("P580", time_value("+1995-01-01T00:00:00Z"))])
    ent_a = item(a, 1, {"en": "Ada Kowalska", "mul": "Ada Kowalska", "fr": "Ada Kowalska",
                        "pl": "Ada Kowalska-Łęcka"},
                 {"en": "Polish-born mathematician (1950–2020)", "fr": "mathématicienne polonaise"},
                 {"en": ["A. Kowalska"], "mul": ["Ada K."], "de": ["Ada Kowalska-Łęcka"]},
                 claims(s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s16, s11, s12, s13, s14, s15),
                 {"enwiki": "Ada Kowalska", "frwiki": "Ada Kowalska", "plwiki": "Ada Kowalska-Łęcka"})
    ent_b = item("Q1002", 2, {"en": "Category:Fictional mathematicians", "de": "Kategorie:Fiktive Mathematiker"},
                 {"en": "Wikimedia category"}, {},
                 claims(statement("Q1002", snak("P31", item_value("Q4167836")))),
                 {"enwiki": "Category:Fictional mathematicians", "commonswiki": "Category:Fictional mathematicians"})
    c = "Q1003"
    ent_c = item(c, 3, {"mul": "Łucja Nowak", "pl": "Łucja Nowak", "de": "Łucja Nowak"},
                 {"pl": "polska matematyczka"}, {"pl": ["Lucja Nowak"]},
                 claims(statement(c, snak("P31", item_value("Q5")),
                                  references=[reference(snak("P143", item_value("Q48183")))]),
                        statement(c, snak("P31", item_value("Q5"))),
                        statement(c, snak("P31", item_value("Q215627")), rank="deprecated"),
                        statement(c, snak("P31", snaktype="somevalue", datatype="wikibase-item")),
                        statement(c, snak("P1449", text_value("Łucja", "pl")), rank="preferred",
                                  qualifiers=[qual("P7452", snaktype="somevalue", datatype="wikibase-item")])),
                 {"dewiki": "Łucja Nowak", "plwiki": "Łucja Nowak"})
    d = "Q1004"
    ent_d = item(d, 4, {"en": "Lovelace", "fr": "Lovelace"},
                 {"en": "Wikimedia disambiguation page", "fr": "page d'homonymie de Wikimedia"}, {},
                 claims(statement(d, snak("P31", item_value("Q4167410"))),
                        statement(d, snak("P1889", item_value("Q1001")), rank="deprecated", qualifiers=[
                            qual("P2241", item_value("Q41755623")),
                            qual("P2241", snaktype="novalue", datatype="wikibase-item")])),
                 {"enwiki": "Lovelace (disambiguation)"})
    ent_e = {"type": "property", "datatype": "wikibase-item", "id": "P39",
             "labels": terms({"en": "position held", "de": "Position"}),
             "descriptions": terms({"en": "subject currently or formerly holds the object position or public "
                                          "office"}),
             "aliases": alias_terms({"en": ["office held"]}),
             "claims": claims(statement("P39", snak("P31", item_value("Q18608871"))),
                              statement("P39", snak("P1855", item_value("Q1001")),
                                        qualifiers=[qual("P39", item_value("Q30185"))])),
             "pageid": 105, "ns": 120, "title": "Property:P39", "lastrevid": 2400000005,
             "modified": "2026-09-25T12:00:05Z"}
    f = "Q1005"
    ent_f = item(f, 6, {"de": "Testklasse"}, {}, {},
                 claims(statement(f, snak("P31", item_value("Q16889133"))),
                        statement(f, snak("P279", item_value("Q1006"))),
                        statement(f, snak("P279", item_value("Q1007")), rank="preferred"),
                        statement(f, snak("P279", item_value("Q1006"))),
                        statement(f, snak("P279", item_value("Q1008")), rank="deprecated",
                                  qualifiers=[qual("P2241", item_value("Q14946528"))]),
                        statement(f, snak("P279", item_value("Q1009")),
                                  qualifiers=[qual("P7452", item_value("Q71536040")),
                                              qual("P7452", item_value("Q71533355"))]),
                        statement(f, snak("P793", item_value("Q1019")), qualifiers=[
                            qual("P580", time_value("+1999-01-01T00:00:00Z")),
                            qual("P580", time_value("+2000-01-01T00:00:00Z")),
                            qual("P582", time_value("+2001-01-01T00:00:00Z")),
                            qual("P582", time_value("+2002-01-01T00:00:00Z"))])),
                 {"commonswiki": "Category:Test classes"})
    ent_g = {"type": "lexeme", "id": "L7", "lemmas": terms({"en": "house"}), "lexicalCategory": "Q1084",
             "language": "Q1860", "claims": {}, "forms": [], "senses": [], "pageid": 107, "ns": 146,
             "title": "Lexeme:L7", "lastrevid": 2400000007, "modified": "2026-09-27T12:00:07Z"}
    ent_h = prop("P1855", 8, "wikibase-item", "Wikidata property example",
                 claims(statement("P1855", snak("P31", item_value("Q19820110")))))
    ent_i = prop("P2302", 9, "wikibase-item", "property constraint",
                 claims(statement("P2302", snak("P31", item_value("Q19820110")), rank="deprecated"),
                        statement("P2302", snak("P31", item_value("Q21504947")), rank="preferred")))
    ent_j = prop("P1647", 10, "wikibase-property", "subproperty of",
                 claims(statement("P1647", snak("P31", item_value("Q19820110"))),
                        statement("P1647", snak("P31", item_value("Q18616576")), rank="preferred")))
    return [ent_a, ent_b, ent_c, ent_d, ent_e, ent_f, ent_g, ent_h, ent_i, ent_j]


MAIN = build_main()
MAIN_TEXT = dump_text(MAIN)


def row(ident: str, kind: str, label: Any, description: Any, p31: List[str], p279: List[str], n_sitelinks: int,
        enwiki: Any, n_statements: int, n_qualified: int, n: int, datatype: Any = None) -> List[Any]:
    ent = next(e for e in MAIN if e["id"] == ident)
    return [ident, kind, label, description, p31, p279, n_sitelinks, enwiki, n_statements, n_qualified,
            2400000000 + n, ent["modified"], datatype]


EXPECTED_INDEX = [
    row("Q1001", "item", "Ada Kowalska", "Polish-born mathematician (1950–2020)", ["Q5"], [], 3,
        "Ada Kowalska", 16, 12, 1),  # qualified: all but S1, S6, S7, S9
    row("Q1002", "item", "Category:Fictional mathematicians", "Wikimedia category", ["Q4167836"], [], 2,
        "Category:Fictional mathematicians", 1, 0, 2),
    # no en label: the mul label; no en description; the duplicate, deprecated and somevalue P31 are left out
    row("Q1003", "item", "Łucja Nowak", None, ["Q5"], [], 2, None, 5, 1, 3),
    row("Q1004", "item", "Lovelace", "Wikimedia disambiguation page", ["Q4167410"], [], 1,
        "Lovelace (disambiguation)", 2, 1, 4),
    row("P39", "property", "position held",
        "subject currently or formerly holds the object position or public office", ["Q18608871"], [], 0, None,
        2, 1, 5, "wikibase-item"),
    # P279: the duplicate Q1006 and the deprecated Q1008 are left out; the preferred Q1007 stays
    row("Q1005", "item", None, None, ["Q16889133"], ["Q1006", "Q1007", "Q1009"], 1, None, 7, 3, 6),
    row("P1855", "property", "Wikidata property example", None, ["Q19820110"], [], 0, None, 1, 0, 8,
        "wikibase-item"),
    row("P2302", "property", "property constraint", None, ["Q21504947"], [], 0, None, 2, 0, 9, "wikibase-item"),
    # the index keeps every P31 value not ranked deprecated; rule 8 reads only the best rank (preferred here)
    row("P1647", "property", "subproperty of", None, ["Q19820110", "Q18616576"], [], 0, None, 2, 0, 10,
        "wikibase-property"),
]


def pp(statements: int, qualified: int, deprecated: int, preferred: int, referenced: int, timed: int,
       multi_P580: int = 0, multi_P582: int = 0, multi_time: int = 0, self_qualified: int = 0,
       p2241_not_deprecated: int = 0, p2241_not_deprecated_snaks: int = 0, p7452_not_preferred: int = 0,
       p7452_not_preferred_snaks: int = 0) -> Dict[str, int]:
    return {"statements": statements, "qualified": qualified, "deprecated": deprecated, "preferred": preferred,
            "referenced": referenced, "timed": timed, "multi_P580": multi_P580, "multi_P582": multi_P582,
            "multi_time": multi_time, "self_qualified": self_qualified, "p2241_not_deprecated": p2241_not_deprecated,
            "p2241_not_deprecated_snaks": p2241_not_deprecated_snaks, "p7452_not_preferred": p7452_not_preferred,
            "p7452_not_preferred_snaks": p7452_not_preferred_snaks}


# Seed scope: (a) Q1001 with S1-S16 and (d) Q1004 with D1-D2, 18 statements. Per statement: its qualifier snaks,
# and its arity all / no_interval / wd_roles. The subject counts 1, the main value 1 unless novalue, each qualifier
# snak 1 unless novalue; no_interval leaves out P580 and P582; wd_roles (r1) leaves out P580 and P582 except on the
# relations P580 and P582 (rule 6a), and always P2241, P7452, P1534 and meta properties such as P1810.
#   S1  P31                                          0 snaks   2/2/2   referenced (P248, P813)
#   S2  P39   +P580 +P582 +P1365                     3         5/3/3   referenced (P143)
#   S14 P39   +P580 +P582 +P1534                     3         5/3/2
#   S3  P1082 +P585                                  1         3/3/3
#   S4  P1082 preferred +P585 +P7452                 2         4/4/3
#   S5  P569  deprecated +P2241 Q41755623            1         3/3/2
#   S6  P569                                         0         2/2/2   referenced (P248)
#   S7  P22   somevalue                              0         2/2/2
#   S8  P26   +P580 +P582 novalue                    2         3/2/2
#   S9  P40   novalue                                0         1/1/1
#   S10 P166  +P1027 +P1027 +P1534                   3         5/5/4   referenced (P248, P854)
#   S16 P108  +P580                                  1         3/2/2
#   S11 P108  +P580 +P580 +P582 +P1810               4         6/3/2   multi_P580, multi_time
#   S12 P131  +P131                                  1         3/3/3   self_qualified
#   S13 P106  normal +P2241 +P2241                   2         4/4/2   p2241_not_deprecated (2 snaks)
#   S15 P580  +P580 +P582 +P582                      3         5/2/5   rule 6a; self_qualified; multi_time
#   D1  P31                                          0         2/2/2
#   D2  P1889 deprecated +P2241 Q41755623 +P2241 novalue   2   3/3/2
EXPECTED_SEED = {
    "entities": 2, "items_with_enwiki_article": 2,
    "sitelinks_hist": {"3": 1, "1": 1},
    "statements": 18,
    "by_rank": {"preferred": 1, "normal": 15, "deprecated": 2},  # S4 / the others / S5, D2
    "main_snaktype": {"value": 16, "somevalue": 1, "novalue": 1},  # S7 somevalue, S9 novalue
    "main_datatype": {"wikibase-item": 13, "quantity": 2, "time": 3},  # S3, S4 / S5, S6, S15
    "qualified_statements": 13,  # all but S1, S6, S7, S9, D1
    "qualifier_snaks_hist": {"0": 5, "1": 4, "2": 4, "3": 4, "4": 1},
    "qualifier_props_hist": {"0": 5, "1": 6, "2": 4, "3": 3},  # S10, S11, S13, S15 and D2 repeat a property
    "qualifier_snaktype": {"value": 26, "novalue": 2},
    "qualifier_datatype": {"time": 15, "wikibase-item": 12, "string": 1},
    "qualifier_property": {"P580": 7, "P582": 6, "P1365": 1, "P585": 2, "P7452": 1, "P2241": 5, "P1027": 2,
                           "P1534": 2, "P1810": 1, "P131": 1},
    "arity_all_hist": {"1": 1, "2": 4, "3": 6, "4": 2, "5": 4, "6": 1},
    "arity_no_interval_hist": {"1": 1, "2": 7, "3": 7, "4": 2, "5": 1},
    "arity_wd_roles_hist": {"1": 1, "2": 11, "3": 4, "4": 1, "5": 1},
    "referenced_statements": 4, "references": 4,  # S1, S2, S6, S10
    "reference_property": {"P248": 3, "P813": 1, "P143": 1, "P854": 1},
    "deprecated_reasons": {"Q41755623": 2, "<novalue>": 1},  # S5, D2; S13 is not deprecated
    "preferred_reasons": {"Q98386534": 1},  # S4
    "per_property": {"P31": pp(2, 0, 0, 0, 1, 0), "P39": pp(2, 2, 0, 0, 1, 2), "P1082": pp(2, 2, 0, 1, 0, 2),
                     "P569": pp(2, 1, 1, 0, 1, 0), "P22": pp(1, 0, 0, 0, 0, 0), "P26": pp(1, 1, 0, 0, 0, 1),
                     "P40": pp(1, 0, 0, 0, 0, 0), "P166": pp(1, 1, 0, 0, 1, 0),
                     "P108": pp(2, 2, 0, 0, 0, 2, multi_P580=1, multi_time=1),
                     "P131": pp(1, 1, 0, 0, 0, 0, self_qualified=1),
                     "P106": pp(1, 1, 0, 0, 0, 0, p2241_not_deprecated=1, p2241_not_deprecated_snaks=2),
                     "P580": pp(1, 1, 0, 0, 0, 1, multi_P582=1, multi_time=1, self_qualified=1),
                     "P1889": pp(1, 1, 1, 0, 0, 0)},
    "qualifier_pairs": {"P39": {"P580": [2, 2], "P582": [2, 2], "P1365": [1, 1], "P1534": [1, 1]},
                        "P1082": {"P585": [2, 2], "P7452": [1, 1]}, "P569": {"P2241": [1, 1]},
                        "P26": {"P580": [1, 1], "P582": [1, 1]}, "P166": {"P1027": [1, 2], "P1534": [1, 1]},
                        "P108": {"P580": [2, 3], "P582": [1, 1], "P1810": [1, 1]}, "P131": {"P131": [1, 1]},
                        "P106": {"P2241": [1, 2]}, "P580": {"P580": [1, 1], "P582": [1, 2]},
                        "P1889": {"P2241": [1, 2]}},
    "per_property_arity_wd_roles": {"P31": {"2": 2}, "P39": {"3": 1, "2": 1}, "P1082": {"3": 2}, "P569": {"2": 2},
                                    "P22": {"2": 1}, "P26": {"2": 1}, "P40": {"1": 1}, "P166": {"4": 1},
                                    "P108": {"2": 2}, "P131": {"3": 1}, "P106": {"2": 1}, "P580": {"5": 1},
                                    "P1889": {"2": 1}},
    "time_series": {"P39": 1, "P1082": 1, "P108": 1},  # two timed statements each; P26 and P580 have one
    "p31": {"Q5": 1, "Q4167410": 1},
}

# All items: the seed scope plus (b) Q1002 (B1), (c) Q1003 (C1-C5) and (f) Q1005 (F1-F7), 13 statements:
#   B1 P31 2/2/2. C1-C3 P31 2/2/2 (C1 referenced, C3 deprecated without P2241); C4 P31 somevalue 2/2/2;
#   C5 P1449 preferred +P7452 somevalue 3/3/2. F1 P31, F2-F4 P279 2/2/2 (F3 preferred without P7452);
#   F5 P279 deprecated +P2241 Q14946528 3/3/2; F6 P279 normal +P7452 +P7452 4/4/2 (p7452_not_preferred,
#   2 snaks); F7 P793 +P580 +P580 +P582 +P582 6/2/2 (multi_P580, multi_P582, multi_time once, timed).
EXPECTED_ALL = {
    "entities": 5, "items_with_enwiki_article": 2,
    "sitelinks_hist": {"1": 2, "2": 2, "3": 1},
    "statements": 31,
    "by_rank": {"preferred": 3, "normal": 24, "deprecated": 4},
    "main_snaktype": {"value": 28, "somevalue": 2, "novalue": 1},
    "main_datatype": {"wikibase-item": 25, "quantity": 2, "time": 3, "monolingualtext": 1},
    "qualified_statements": 17,
    "qualifier_snaks_hist": {"0": 14, "1": 6, "2": 5, "3": 4, "4": 2},
    "qualifier_props_hist": {"0": 14, "1": 9, "2": 5, "3": 3},
    "qualifier_snaktype": {"value": 33, "novalue": 2, "somevalue": 1},
    "qualifier_datatype": {"time": 19, "wikibase-item": 16, "string": 1},
    "qualifier_property": {"P580": 9, "P582": 8, "P1365": 1, "P585": 2, "P7452": 4, "P2241": 6, "P1027": 2,
                           "P1534": 2, "P1810": 1, "P131": 1},
    "arity_all_hist": {"1": 1, "2": 13, "3": 8, "4": 3, "5": 4, "6": 2},
    "arity_no_interval_hist": {"1": 1, "2": 17, "3": 9, "4": 3, "5": 1},
    "arity_wd_roles_hist": {"1": 1, "2": 24, "3": 4, "4": 1, "5": 1},
    "referenced_statements": 5, "references": 5,
    "reference_property": {"P248": 3, "P813": 1, "P143": 2, "P854": 1},
    "deprecated_reasons": {"Q41755623": 2, "<novalue>": 1, "<none>": 1, "Q14946528": 1},  # + C3, F5
    "preferred_reasons": {"Q98386534": 1, "<somevalue>": 1, "<none>": 1},  # + C5, F3; F6 is not preferred
    "per_property": dict(EXPECTED_SEED["per_property"], P31=pp(8, 0, 1, 0, 2, 0), P1449=pp(1, 1, 0, 1, 0, 0),
                         P279=pp(5, 2, 1, 1, 0, 0, p7452_not_preferred=1, p7452_not_preferred_snaks=2),
                         P793=pp(1, 1, 0, 0, 0, 1, multi_P580=1, multi_P582=1, multi_time=1)),
    "qualifier_pairs": dict(EXPECTED_SEED["qualifier_pairs"], P1449={"P7452": [1, 1]},
                            P279={"P2241": [1, 1], "P7452": [1, 2]}, P793={"P580": [1, 2], "P582": [1, 2]}),
    "per_property_arity_wd_roles": dict(EXPECTED_SEED["per_property_arity_wd_roles"], P31={"2": 8},
                                        P1449={"2": 1}, P279={"2": 5}, P793={"2": 1}),
    "time_series": {"P39": 1, "P1082": 1, "P108": 1},
    "p31": {"Q5": 2, "Q4167410": 1, "Q4167836": 1, "Q16889133": 1},
}

# Property entities (e) P39, (h) P1855, (i) P2302 and (j) P1647, 7 statements, none referenced:
#   P39: P31 Q18608871; P1855 Q1001 +P39 (3/3/3). P1855: P31 Q19820110. P2302: P31 Q19820110 deprecated,
#   P31 Q21504947 preferred. P1647: P31 Q19820110, P31 Q18616576 preferred. All but the P1855 statement are 2/2/2.
EXPECTED_PROPERTY_ENTITIES = {
    "entities": 4, "items_with_enwiki_article": 0,
    "sitelinks_hist": {"0": 4},
    "statements": 7,
    "by_rank": {"preferred": 2, "normal": 4, "deprecated": 1},
    "main_snaktype": {"value": 7, "somevalue": 0, "novalue": 0},
    "main_datatype": {"wikibase-item": 7},
    "qualified_statements": 1,
    "qualifier_snaks_hist": {"0": 6, "1": 1},
    "qualifier_props_hist": {"0": 6, "1": 1},
    "qualifier_snaktype": {"value": 1}, "qualifier_datatype": {"wikibase-item": 1}, "qualifier_property": {"P39": 1},
    "arity_all_hist": {"2": 6, "3": 1},
    "arity_no_interval_hist": {"2": 6, "3": 1},
    "arity_wd_roles_hist": {"2": 6, "3": 1},
    "referenced_statements": 0, "references": 0, "reference_property": {},
    "deprecated_reasons": {"<none>": 1},
    "preferred_reasons": {"<none>": 2},
    "per_property": {"P31": pp(6, 0, 1, 2, 0, 0), "P1855": pp(1, 1, 0, 0, 0, 0)},
    "qualifier_pairs": {"P1855": {"P39": [1, 1]}},
    "per_property_arity_wd_roles": {"P31": {"2": 6}, "P1855": {"3": 1}},
    "time_series": {},
    "p31": {"Q18608871": 1, "Q19820110": 2, "Q21504947": 1, "Q18616576": 1},
}

EXPECTED_STATS = {"format": "p3a-wd-slice-stats/1", "naming": "wd-roles r1",
                  "scopes": {"all": EXPECTED_ALL, "seed": EXPECTED_SEED,
                             "property_entities": EXPECTED_PROPERTY_ENTITIES},
                  "properties": {"count": 4, "datatype": {"wikibase-item": 3, "wikibase-property": 1}},
                  "other_types": {"lexeme": 1}}

EXPECTED_COUNTS = {"entities": 10, "items": 5, "properties": 4, "other": 1, "seeds": 2, "index_rows": 9,
                   "statements_all": 31, "statements_seed": 18, "lines": 12, "uncompressed_bytes": len(MAIN_TEXT)}


def without_qualifier_hashes(claim_map: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(claim_map)
    for statements in out.values():
        for s in statements:
            for qsnaks in (s.get("qualifiers") or {}).values():
                for q in qsnaks:
                    q.pop("hash", None)
    return out


def filler(n: int, start: int = 2000) -> List[Dict[str, Any]]:
    """``n`` further items of varied shape: every third one a seed, others with a Template: enwiki title or none;
    qualifiers, references, ranks and non-ASCII text vary with the number."""
    out = []
    for i in range(n):
        qid = f"Q{start + i}"
        stmts = [statement(qid, snak("P31", item_value("Q5" if i % 2 else "Q13442814")),
                           references=[reference(snak("P248", item_value("Q5188229")))] if i % 4 == 0 else ())]
        if i % 5 == 0:
            stmts.append(statement(qid, snak("P1082", quantity_value(f"+{1000 + i}")),
                                   qualifiers=[qual("P585", time_value(f"+20{10 + i % 10}-01-01T00:00:00Z"))]))
            stmts.append(statement(qid, snak("P1082", quantity_value(f"+{900 + i}")), rank="deprecated",
                                   qualifiers=[qual("P585", time_value("+2009-01-01T00:00:00Z")),
                                               qual("P2241", item_value("Q25895909"))]))
        if i % 7 == 0:
            stmts.append(statement(qid, snak("P2093", string_value(f"Autorów {i}")),
                                   qualifiers=[qual("P1545", string_value(str(i % 3 + 1)))]))
        sitelinks = {"dewiki": f"Artikel {i} ü"}
        if i % 3 == 0:
            sitelinks["enwiki"] = f"Article {i}: a subtitle"
        elif i % 3 == 1:
            sitelinks["enwiki"] = f"Template:Box {i}"
        out.append(item(qid, start + i, {"en": f"Item {i}", "ja": f"項目 {i}"},
                        {"en": f"test item number {i}"}, {"en": [f"alias {i}"]} if i % 2 else {},
                        claims(*stmts), sitelinks))
    return out


BIG = MAIN[:4] + filler(40) + MAIN[4:]
BIG_TEXT = dump_text(BIG)


def line_middle(text: bytes, n: int) -> int:
    """The offset of the middle of line ``n`` (from 0) of ``text``."""
    start = 0
    for _ in range(n):
        start = text.index(b"\n", start) + 1
    return (start + text.index(b"\n", start)) // 2


#: Offsets in BIG_TEXT at which the truncation tests start a new bz2 stream: inside lines 5 (the first filler item,
#: after Q1001 to Q1004), 12, 20 and 30.
CUTS = [line_middle(BIG_TEXT, n) for n in (5, 12, 20, 30)]


def multi_stream(text: bytes, cuts: List[int], level: int = 9) -> bytes:
    """``text`` as consecutive bz2 streams, cut at the given offsets (which may fall inside a line)."""
    bounds = [0] + list(cuts) + [len(text)]
    return b"".join(bz2.compress(text[a:b], level) for a, b in zip(bounds, bounds[1:]))


# ------------------------------------------------------------------------------------------------ helpers


def read_gz_lines(path: str) -> List[bytes]:
    with gzip.open(path, "rb") as fh:
        return fh.read().splitlines()


def read_rows(path: str) -> List[Any]:
    return [json.loads(line) for line in read_gz_lines(path)]


def gzip_members(data: bytes) -> List[bytes]:
    """The decompressed content of each gzip member of ``data``, in order."""
    out = []
    while data:
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        out.append(d.decompress(data))
        assert d.eof, "a truncated gzip member"
        data = d.unused_data
    return out


def output_files(out: str) -> Dict[str, bytes]:
    """Every output but run.json, by name."""
    result = {}
    for name in sorted(os.listdir(out)):
        if name != "run.json":
            with open(os.path.join(out, name), "rb") as fh:
                result[name] = fh.read()
    return result


def children_of(pid: int) -> List[Any]:
    """(pid, command) of the live child processes of ``pid``."""
    text = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,stat=,command="], capture_output=True, text=True).stdout
    found = []
    for line in text.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4 and int(parts[1]) == pid and not parts[2].startswith("Z"):
            found.append((int(parts[0]), parts[3]))
    return found


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    text = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(text) and not text.startswith("Z")


def wait_for(predicate: Any, timeout: float = 30.0, step: float = 0.05) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(step)
    raise AssertionError("timed out waiting")


class SliceTest(unittest.TestCase):
    """Runs of the slicer on synthetic dumps in a fresh directory."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="wdslice-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def path(self, name: str) -> str:
        return os.path.join(self.tmp, name)

    def write(self, name: str, data: bytes) -> str:
        with open(self.path(name), "wb") as fh:
            fh.write(data)
        return self.path(name)

    def slice(self, src: str, out: str, *extra: str, expect: Optional[int] = 0) -> Dict[str, Any]:
        """Runs ``wdslice.main`` in this process; returns run.json, with the exit status and stderr added. A run
        that takes longer than ``WATCHDOG_S`` is interrupted (as by SIGINT), so a hang fails instead of blocking."""
        err = io.StringIO()
        watchdog = threading.Timer(WATCHDOG_S, _thread.interrupt_main)
        watchdog.start()
        try:
            with contextlib.redirect_stderr(err):
                code = wdslice.main(["--input", src, "--out", self.path(out), *extra])
        finally:
            watchdog.cancel()
        self.assert_clean()
        if expect is not None:
            self.assertEqual(code, expect, err.getvalue())
        record: Dict[str, Any] = {}
        if os.path.exists(os.path.join(self.path(out), "run.json")):
            with open(os.path.join(self.path(out), "run.json"), encoding="utf-8") as fh:
                record = json.load(fh)
        record["_exit"] = code
        record["_stderr"] = err.getvalue()
        return record

    def assert_clean(self) -> None:
        """No worker process and no reader thread outlive a run."""
        self.assertEqual(multiprocessing.active_children(), [])
        self.assertFalse([t for t in threading.enumerate() if t.name == "wdslice-reader" and t.is_alive()])


# ------------------------------------------------------------------------------------------------ SPEC §9


class SeedsAndPruning(SliceTest):
    """§9.1: exactly (a) and (d) are seeds; the pruned envelope."""

    def test_seeds_and_pruning(self) -> None:
        run = self.slice(self.write("d.json.bz2", bz2.compress(MAIN_TEXT)), "out", "--workers", "2")
        self.assertEqual(run["status"], "complete")
        rows = read_rows(os.path.join(self.path("out"), "items-0000.jsonl.gz"))
        self.assertEqual([r["id"] for r in rows], ["Q1001", "Q1004"])
        a, d = rows
        src_a, src_d = MAIN[0], MAIN[3]
        for r in rows:
            self.assertEqual(list(r), ENVELOPE_KEYS)
        self.assertEqual(a["labels"], {k: src_a["labels"][k] for k in ("en", "mul")})
        self.assertEqual(a["descriptions"], {"en": src_a["descriptions"]["en"]})
        self.assertEqual(a["aliases"], {k: src_a["aliases"][k] for k in ("en", "mul")})
        self.assertEqual(a["sitelinks"], {"enwiki": src_a["sitelinks"]["enwiki"]})
        self.assertEqual(a["x_sitelink_count"], 3)
        self.assertEqual((a["type"], a["lastrevid"], a["modified"]),
                         (src_a["type"], src_a["lastrevid"], src_a["modified"]))
        # claims: verbatim but for the qualifier-snak hashes; reference hashes stay
        self.assertEqual(a["claims"], without_qualifier_hashes(src_a["claims"]))
        self.assertNotEqual(a["claims"], src_a["claims"])
        p39 = a["claims"]["P39"][0]
        self.assertTrue(all("hash" not in q for qs in p39["qualifiers"].values() for q in qs))
        self.assertEqual(p39["references"], src_a["claims"]["P39"][0]["references"])
        self.assertIn("hash", p39["references"][0])
        self.assertEqual(p39["qualifiers-order"], ["P580", "P582", "P1365"])
        # (d): no mul label, no aliases: present and empty
        self.assertEqual((d["labels"], d["aliases"], d["x_sitelink_count"]),
                         ({"en": src_d["labels"]["en"]}, {}, 1))
        self.assertEqual(d["claims"], without_qualifier_hashes(src_d["claims"]))
        # UTF-8, not \\u escapes, as json.dumps(ensure_ascii=False, separators=(",", ":")) writes it
        raw = read_gz_lines(os.path.join(self.path("out"), "items-0000.jsonl.gz"))
        self.assertEqual(raw[0], json.dumps(a, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        self.assertIn("(1950–2020)".encode("utf-8"), raw[0])
        self.assertNotIn(b"\\u2013", raw[0])

    def test_seed_rule(self) -> None:
        article = ["Ada Kowalska", "Star Wars: Episode IV", "ISO 3166-2:PL", "category:lower case", ":Leading",
                   "Talk show", "Portal (video game)", "UTC+01:00"]
        other = ["Category:X", "Template:X", "Module:X", "Wikipedia:X", "Portal:X", "Help:X", "Draft:X", "File:X",
                 "Image:X", "MediaWiki:X", "User:X", "TimedText:X", "Book:X", "Special:X", "Project:X", "WP:X",
                 "Talk:X", "Category:Star Wars: Episode IV"]
        self.assertEqual([t for t in article if not wdslice.is_article(t)], [])
        self.assertEqual([t for t in other if wdslice.is_article(t)], [])


class IndexPropertiesStats(SliceTest):
    """§9.2: index rows, properties and statistics equal the hand-computed values."""

    def test_index_properties_and_stats(self) -> None:
        run = self.slice(self.write("d.json.bz2", bz2.compress(MAIN_TEXT)), "out", "--workers", "3",
                         "--batch-bytes", "700")
        out = self.path("out")
        self.assertEqual(run["status"], "complete")
        self.assertEqual(read_rows(os.path.join(out, "index-0000.jsonl.gz")), EXPECTED_INDEX)
        # properties.jsonl.gz: the dump's line without the trailing comma
        property_lines = [line.rstrip(b",") for line in MAIN_TEXT.split(b"\n")
                          if line.startswith(b'{"type":"property"')]
        self.assertEqual(len(property_lines), 4)
        self.assertEqual(read_gz_lines(os.path.join(out, "properties.jsonl.gz")), property_lines)
        with open(os.path.join(out, "stats.json"), encoding="utf-8") as fh:
            text = fh.read()
        stats = json.loads(text)
        for scope in ("seed", "all", "property_entities"):
            for key, expected in EXPECTED_STATS["scopes"][scope].items():  # type: ignore[index]
                self.assertEqual(stats["scopes"][scope][key], expected, f"{scope}.{key}")
        self.assertEqual(stats, EXPECTED_STATS)
        self.assertEqual(text, json.dumps(stats, sort_keys=True, indent=1))

    def test_reasons_count_each_value_once(self) -> None:
        counter: Dict[str, int] = defaultdict(int)
        qualifiers = {"P2241": [qual("P2241", item_value("Q41755623")), qual("P2241", item_value("Q41755623")),
                                qual("P2241", snaktype="somevalue", datatype="wikibase-item"),
                                qual("P2241", snaktype="somevalue", datatype="wikibase-item")]}
        wdslice._reasons(qualifiers, "P2241", counter)
        wdslice._reasons({"P580": [qual("P580", time_value("+2000-01-01T00:00:00Z"))]}, "P2241", counter)
        wdslice._reasons(None, "P2241", counter)
        self.assertEqual(dict(counter), {"Q41755623": 1, "<somevalue>": 1, "<none>": 2})


class RunRecord(SliceTest):
    """§9.3: counts, and md5, sha1 and sha256 equal to hashlib on the synthetic .bz2."""

    def test_run_record(self) -> None:
        data = bz2.compress(MAIN_TEXT)
        src = self.write("d.json.bz2", data)
        run = self.slice(src, "out", "--workers", "2", "--expect-size", str(len(data)),
                         "--expect-md5", hashlib.md5(data).hexdigest().upper(),
                         "--expect-sha1", hashlib.sha1(data).hexdigest())
        self.assertEqual(run["format"], "p3a-wd-slice-run/1")
        self.assertEqual((run["status"], run["error"]), ("complete", None))
        self.assertEqual(run["counts"], EXPECTED_COUNTS)
        inp = run["input"]
        self.assertEqual((inp["md5"], inp["sha1"], inp["sha256"]),
                         (hashlib.md5(data).hexdigest(), hashlib.sha1(data).hexdigest(),
                          hashlib.sha256(data).hexdigest()))
        self.assertEqual((inp["path"], inp["bytes_read"], inp["expected_size"], inp["verified"], inp["truncated"]),
                         (src, len(data), len(data), True, False))
        self.assertEqual(inp["expected_md5"], hashlib.md5(data).hexdigest())
        with open(SCRIPT, "rb") as fh:
            self.assertEqual(run["code"]["script_sha256"], hashlib.sha256(fh.read()).hexdigest())
        self.assertEqual(run["code"]["python"], ".".join(map(str, sys.version_info[:3])))
        self.assertEqual(set(run["params"]), {"input", "out", "follow", "expect_size", "expect_md5", "expect_sha1",
                                              "workers", "batch_bytes", "shard_items", "index_shard_rows",
                                              "max_input_bytes", "allow_truncated", "stall_timeout", "force"})
        self.assertEqual(run["params"]["workers"], 2)
        # every output is listed with its size, sha256 and rows
        listed = {o["file"]: o for o in run["outputs"]}
        self.assertEqual(set(listed), set(output_files(self.path("out"))))
        for name, content in output_files(self.path("out")).items():
            self.assertEqual((listed[name]["bytes"], listed[name]["sha256"]),
                             (len(content), hashlib.sha256(content).hexdigest()), name)
        self.assertEqual({k: v["rows"] for k, v in listed.items()},
                         {"items-0000.jsonl.gz": 2, "index-0000.jsonl.gz": 9, "properties.jsonl.gz": 4,
                          "stats.json": None})
        self.assertTrue(run["started"].endswith("Z") and run["finished"].endswith("Z"))
        self.assertGreaterEqual(run["timings"]["wall_s"], 0.0)
        self.assertEqual(run["timings"]["waited_s"], 0.0)

    def test_nothing_to_verify(self) -> None:
        run = self.slice(self.write("d.json.bz2", bz2.compress(MAIN_TEXT)), "out", "--workers", "1")
        self.assertIsNone(run["input"]["verified"])


class MultiStream(SliceTest):
    """§9.4: the same dump as concatenated bz2 streams gives byte-identical outputs."""

    def test_two_streams(self) -> None:
        cut = MAIN_TEXT.index(b'"Q1003"') + 5  # inside the line of (c)
        self.slice(self.write("one.json.bz2", bz2.compress(MAIN_TEXT)), "one", "--workers", "2")
        run = self.slice(self.write("two.json.bz2", multi_stream(MAIN_TEXT, [cut])), "two", "--workers", "2")
        self.assertEqual(output_files(self.path("two")), output_files(self.path("one")))
        self.assertEqual(run["counts"], EXPECTED_COUNTS)

    def test_many_small_streams(self) -> None:
        cuts = list(range(97, len(BIG_TEXT), 997))
        self.slice(self.write("one.json.bz2", bz2.compress(BIG_TEXT)), "one", "--workers", "2",
                   "--batch-bytes", "5000")
        self.slice(self.write("many.json.bz2", multi_stream(BIG_TEXT, cuts)), "many", "--workers", "2",
                   "--batch-bytes", "5000")
        self.assertEqual(output_files(self.path("many")), output_files(self.path("one")))


class Determinism(SliceTest):
    """§9.5: outputs do not depend on the worker count, the read chunking or the decompressor's output chunking."""

    def test_workers_and_chunking(self) -> None:
        src = self.write("d.json.bz2", multi_stream(BIG_TEXT, [len(BIG_TEXT) // 3]))
        opts = ["--batch-bytes", "300", "--shard-items", "1", "--index-shard-rows", "7"]
        first = self.slice(src, "w1", "--workers", "1", *opts)
        self.slice(src, "w3", "--workers", "3", *opts)
        with mock.patch.object(wdslice, "READ_CHUNK", 13), mock.patch.object(wdslice, "MAX_OUTPUT", 17):
            self.slice(src, "chunked", "--workers", "3", *opts)
        reference_files = output_files(self.path("w1"))
        self.assertEqual(output_files(self.path("w3")), reference_files)
        self.assertEqual(output_files(self.path("chunked")), reference_files)
        # one items shard per batch that has a seed, index shards of at least 7 rows
        seeds = first["counts"]["seeds"]
        self.assertEqual(len([n for n in reference_files if n.startswith("items-")]), seeds)
        self.assertGreater(len([n for n in reference_files if n.startswith("index-")]), 3)
        self.assertEqual([n for n in reference_files if n.startswith("items-")][-1], f"items-{seeds - 1:04d}.jsonl.gz")
        # the shards, read in name order, hold the rows of a one-batch run, in dump order
        self.slice(src, "whole", "--workers", "2")
        for kind in ("items", "index"):
            names = sorted(n for n in reference_files if n.startswith(kind))
            rows = [r for n in names for r in read_rows(os.path.join(self.path("w1"), n))]
            self.assertEqual(rows, read_rows(os.path.join(self.path("whole"), f"{kind}-0000.jsonl.gz")))
        with open(os.path.join(self.path("w1"), "stats.json"), "rb") as fh:
            stats_w1 = fh.read()
        with open(os.path.join(self.path("whole"), "stats.json"), "rb") as fh:
            self.assertEqual(fh.read(), stats_w1)

    def test_batch_rule(self) -> None:
        """A batch ends at the first newline at offset --batch-bytes or later from its start (SPEC §7), and each
        batch that has index rows is one gzip member (level 6, mtime 0) of the index file."""
        by_id = {r[0]: json.dumps(r, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
                 for r in EXPECTED_INDEX}

        def expected(n: int) -> bytes:
            members, start = [], 0
            while start < len(MAIN_TEXT):
                end = MAIN_TEXT.find(b"\n", start + n)
                end = len(MAIN_TEXT) - 1 if end < 0 else end
                ids = [json.loads(line.rstrip(b","))["id"] for line in MAIN_TEXT[start:end + 1].split(b"\n")
                       if line.startswith(b"{")]
                rows = b"".join(by_id[i] for i in ids if i in by_id)
                if rows:
                    members.append(gzip.compress(rows, compresslevel=6, mtime=0))
                start = end + 1
            return b"".join(members)

        src = self.write("d.json.bz2", bz2.compress(MAIN_TEXT))
        end_a = MAIN_TEXT.index(b"\n", 2)  # the newline after (a): offset end_a from the start of the text
        members: Dict[int, List[List[str]]] = {}
        for n in (1, end_a, end_a + 1, 3000, 10 ** 9):
            self.slice(src, f"out{n}", "--workers", "2", "--batch-bytes", str(n))
            with open(os.path.join(self.path(f"out{n}"), "index-0000.jsonl.gz"), "rb") as fh:
                data = fh.read()
            self.assertEqual(data, expected(n), f"--batch-bytes {n}")
            members[n] = [[json.loads(line)[0] for line in m.splitlines()] for m in gzip_members(data)]
        ids = [r[0] for r in EXPECTED_INDEX]
        self.assertEqual(members[1], [[i] for i in ids])  # one member per entity with an index row
        self.assertEqual(members[10 ** 9], [ids])
        # a newline at offset n ends the batch; a newline at offset n - 1 does not
        self.assertEqual(members[end_a][0], ["Q1001"])
        self.assertEqual(members[end_a + 1][0], ["Q1001", "Q1002"])


class Follow(SliceTest):
    """§9.6: follow mode on a file that grows (and shrinks back, as curl --retry makes it) matches the
    non-follow output."""

    def grow(self, path: str, data: bytes, steps: List[Any], delay: float = 0.03) -> threading.Thread:
        """Replays ``steps`` on ``path`` in a thread: an int appends the data up to that offset, a negative
        int truncates the file to minus that size."""
        def run() -> None:
            written = 0
            for step in steps:
                time.sleep(delay)
                if step < 0:
                    os.truncate(path, -step)
                    written = -step
                else:
                    with open(path, "ab") as fh:
                        fh.write(data[written:step])
                    written = step
        thread = threading.Thread(target=run)
        thread.start()
        self.addCleanup(thread.join)
        return thread

    def check_follow(self, data: bytes, steps: List[Any], opts: List[str]) -> Dict[str, Any]:
        self.slice(self.write("whole.json.bz2", data), "plain", "--workers", "2", *opts)
        src = self.write("growing.json.bz2", b"")
        with mock.patch.object(wdslice, "FOLLOW_SLEEP_S", 0.02):
            self.grow(src, data, steps)
            run = self.slice(src, "follow", "--workers", "2", "--follow", "--expect-size", str(len(data)),
                             "--expect-md5", hashlib.md5(data).hexdigest(), *opts)
        self.assertEqual(output_files(self.path("follow")), output_files(self.path("plain")))
        self.assertEqual((run["input"]["verified"], run["input"]["bytes_read"]), (True, len(data)))
        self.assertGreater(run["timings"]["waited_s"], 0.0)
        return run

    def test_growing_file(self) -> None:
        # streams that end inside lines, appended in pieces that end inside streams
        data = multi_stream(BIG_TEXT, [1000, 5003, 12011, 20000, len(BIG_TEXT) - 50])
        steps = sorted(set(list(range(0, len(data), 1733)) + [len(data)]))[1:]
        self.check_follow(data, steps, ["--batch-bytes", "400"])

    def test_file_shrinks_and_grows_back(self) -> None:
        data = multi_stream(BIG_TEXT, [3000, 9000, 15000])
        n = len(data)
        steps = [n * 6 // 10, n * 7 // 10, -(n * 2 // 10), n * 5 // 10, n * 8 // 10, n]
        self.check_follow(data, steps, ["--batch-bytes", "400"])

    def test_stall_timeout(self) -> None:
        data = bz2.compress(MAIN_TEXT)
        src = self.write("stalled.json.bz2", data[: len(data) // 2])
        with mock.patch.object(wdslice, "FOLLOW_SLEEP_S", 0.02), mock.patch.object(wdslice, "PROGRESS_S", 0.1):
            run = self.slice(src, "out", "--workers", "1", "--follow", "--expect-size", str(len(data)),
                             "--stall-timeout", "1", expect=1)
        self.assertEqual(run["status"], "failed")
        self.assertIn("did not grow for 1 s", run["error"])
        self.assertGreater(run["timings"]["waited_s"], 0.5)
        # progress lines: time, compressed GB and percent, MB/s, uncompressed GB, entities, seeds, state, ETA
        self.assertRegex(run["_stderr"], r"wdslice \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ: read 0\.000 GB \(49\.\d\d% of "
                                         r"0\.000 GB\) at 0\.00 MB/s; 0\.00 GB uncompressed; 0 entities, 0 seeds; "
                                         r"waiting for the download; ETA unknown\n")

    def test_replaced_file(self) -> None:
        data = bz2.compress(MAIN_TEXT)
        src = self.write("replaced.json.bz2", data[:100])
        opened = threading.Event()

        def tracking_open(path: Any, *args: Any, **kwargs: Any) -> Any:
            if os.fspath(path) == src:
                opened.set()
            return open(path, *args, **kwargs)

        def replace() -> None:
            opened.wait(30)  # only once the pass has the old file open
            time.sleep(0.1)
            other = self.write("other.json.bz2", data)
            os.replace(other, src)
        thread = threading.Thread(target=replace)
        thread.start()
        self.addCleanup(thread.join)
        with mock.patch.object(wdslice, "FOLLOW_SLEEP_S", 0.02), \
                mock.patch.object(wdslice, "open", tracking_open, create=True):
            run = self.slice(src, "out", "--workers", "1", "--follow", "--expect-size", str(len(data)), expect=1)
        self.assertTrue(opened.is_set())
        self.assertIn("replaced", run["error"])


class Truncation(SliceTest):
    """§9.7: a cut .bz2 fails without --allow-truncated and succeeds with it."""

    def test_cut_input(self) -> None:
        data = multi_stream(BIG_TEXT, CUTS)
        full = self.slice(self.write("full.json.bz2", data), "full", "--workers", "2")
        cut = len(bz2.compress(BIG_TEXT[:CUTS[0]])) + len(bz2.compress(BIG_TEXT[CUTS[0]:CUTS[1]])) \
            + len(bz2.compress(BIG_TEXT[CUTS[1]:CUTS[2]])) // 2  # inside the third stream
        src = self.write("cut.json.bz2", data[:cut])
        failed = self.slice(src, "strict", "--workers", "2", expect=1)
        self.assertEqual(failed["status"], "failed")
        self.assertIn("truncated", failed["error"])
        run = self.slice(src, "lenient", "--workers", "2", "--allow-truncated")
        self.assertEqual((run["status"], run["input"]["truncated"]), ("complete", True))
        # the first two streams hold the text up to CUTS[1]: every complete line in it is processed, no more
        complete = BIG_TEXT[:CUTS[1]][: BIG_TEXT[:CUTS[1]].rfind(b"\n") + 1]
        self.assertEqual(run["counts"]["uncompressed_bytes"], len(complete))
        self.assertEqual(run["counts"]["lines"], complete.count(b"\n"))
        self.assertLess(run["counts"]["entities"], full["counts"]["entities"])
        for kind in ("items", "index"):
            got = read_rows(os.path.join(self.path("lenient"), f"{kind}-0000.jsonl.gz"))
            whole = read_rows(os.path.join(self.path("full"), f"{kind}-0000.jsonl.gz"))
            self.assertTrue(got)
            self.assertEqual(got, whole[: len(got)])

    def test_max_input_bytes_implies_allow_truncated(self) -> None:
        data = multi_stream(BIG_TEXT, CUTS)
        limit = len(bz2.compress(BIG_TEXT[:CUTS[0]])) + 10  # inside the second stream
        run = self.slice(self.write("full.json.bz2", data), "out", "--workers", "2", "--max-input-bytes",
                         str(limit), "--expect-md5", hashlib.md5(data).hexdigest())
        self.assertEqual((run["status"], run["input"]["truncated"], run["input"]["bytes_read"]),
                         ("complete", True, limit))
        self.assertIsNone(run["input"]["verified"])  # a prefix: nothing to compare
        self.assertEqual(run["input"]["md5"], hashlib.md5(data[:limit]).hexdigest())
        self.assertEqual(run["counts"]["uncompressed_bytes"], BIG_TEXT[:CUTS[0]].rfind(b"\n") + 1)
        self.assertEqual(run["counts"]["entities"], 4)  # Q1001 to Q1004 end before CUTS[0]

    def test_empty_and_garbage(self) -> None:
        run = self.slice(self.write("empty.json.bz2", b""), "empty", "--workers", "1", expect=1)
        self.assertIn("empty", run["error"])
        run = self.slice(self.write("junk.json.bz2", bz2.compress(MAIN_TEXT) + b"\0junk"), "junk", "--workers", "1",
                         expect=1)
        self.assertIn("invalid bz2 data in stream 2", run["error"])


class HashMismatch(SliceTest):
    """§9.8: a wrong --expect-md5 (or size, or sha1) fails the run."""

    def test_wrong_md5(self) -> None:
        data = bz2.compress(MAIN_TEXT)
        run = self.slice(self.write("d.json.bz2", data), "out", "--workers", "2", "--expect-md5", "0" * 32,
                         "--expect-sha1", hashlib.sha1(data).hexdigest(), expect=1)
        self.assertEqual((run["status"], run["input"]["verified"]), ("failed", False))
        self.assertIn(f"md5: expected {'0' * 32}, got {hashlib.md5(data).hexdigest()}", run["error"])
        self.assertNotIn("sha1", run["error"])
        self.assertTrue(run["finished"].endswith("Z"))

    def test_wrong_size_and_sha1(self) -> None:
        data = bz2.compress(MAIN_TEXT)
        run = self.slice(self.write("d.json.bz2", data), "out", "--workers", "1", "--expect-size",
                         str(len(data) + 1), "--expect-sha1", "f" * 40, expect=1)
        self.assertIn("size: expected", run["error"])
        self.assertIn("sha1: expected", run["error"])
        self.assertFalse(run["input"]["verified"])


# ------------------------------------------------------------------------------------------------ SPEC §12


def q(statements: int, snaks: int, slot: str) -> Dict[str, Any]:
    return {"statements": statements, "snaks": snaks, "slot": slot}


def rel(statements: int, qualifiers: Dict[str, Any], time_model: Optional[str], left_out_6b: int, self_qualified: int,
        arity: Dict[str, int], p2241: Any = (0, 0), p7452: Any = (0, 0)) -> Dict[str, Any]:
    return {"statements": statements, "qualifiers": qualifiers, "time_model": time_model, "left_out_6b": left_out_6b,
            "self_qualified": self_qualified,
            "rank_reason_mismatch": {"P2241": {"statements": p2241[0], "snaks": p2241[1]},
                                     "P7452": {"statements": p7452[0], "snaks": p7452[1]}},
            "arity": arity}


# The seed scope of EXPECTED_STATS reshaped by hand (§12), in numeric id order. time_model is interval where the
# relation uses P580 or P582 and is not itself P580 or P582; P1534 is end_cause on P39 (interval), meta on P166;
# P580 is rule 6a (its P580 qualifier takes the rule-5 role P580:qualifier; its multi_time statement is not left
# out, as it has no time model); P131 is rule 5; P108 leaves one statement out under 6b (S11); P106 has a 6c
# mismatch on P2241 with two snaks.
KEPT_RELATIONS = {
    "P22": rel(1, {}, None, 0, 0, {"2": 1}),
    "P26": rel(1, {"P580": q(1, 1, "time"), "P582": q(1, 1, "time")}, "interval", 0, 0, {"2": 1}),
    "P31": rel(2, {}, None, 0, 0, {"2": 2}),
    "P39": rel(2, {"P580": q(2, 2, "time"), "P582": q(2, 2, "time"), "P1365": q(1, 1, "qualifier"),
                   "P1534": q(1, 1, "end_cause")}, "interval", 0, 0, {"2": 1, "3": 1}),
    "P40": rel(1, {}, None, 0, 0, {"1": 1}),
    "P106": rel(1, {"P2241": q(1, 2, "rank_reason")}, None, 0, 0, {"2": 1}, p2241=(1, 2)),
    "P108": rel(2, {"P580": q(2, 3, "time"), "P582": q(1, 1, "time"), "P1810": q(1, 1, "meta")}, "interval", 1, 0,
                {"2": 2}),
    "P131": rel(1, {"P131:qualifier": q(1, 1, "qualifier")}, None, 0, 1, {"3": 1}),
    "P166": rel(1, {"P1027": q(1, 2, "qualifier"), "P1534": q(1, 1, "meta")}, None, 0, 0, {"4": 1}),
    "P569": rel(2, {"P2241": q(1, 1, "rank_reason")}, None, 0, 0, {"2": 2}),
    "P580": rel(1, {"P580:qualifier": q(1, 1, "qualifier"), "P582": q(1, 2, "qualifier")}, None, 0, 1, {"5": 1}),
    "P1082": rel(2, {"P585": q(2, 2, "qualifier"), "P7452": q(1, 1, "rank_reason")}, None, 0, 0, {"3": 2}),
    "P1889": rel(1, {"P2241": q(1, 2, "rank_reason")}, None, 0, 0, {"2": 1}),
}
# all = the all scope plus the property entities: P31 gains their 6 statements; P279 has a 6c mismatch on P7452
# (F6, two snaks); P793 leaves F7 out under 6b once, although both of its bounds repeat; P1855 is out of scope
# (rule 8).
ALL_RELATIONS = dict(
    KEPT_RELATIONS, P31=rel(14, {}, None, 0, 0, {"2": 14}),
    P279=rel(5, {"P2241": q(1, 1, "rank_reason"), "P7452": q(1, 2, "rank_reason")}, None, 0, 0, {"2": 5},
             p7452=(1, 2)),
    P793=rel(1, {"P580": q(1, 2, "time"), "P582": q(1, 2, "time")}, "interval", 1, 0, {"2": 1}),
    P1449=rel(1, {"P7452": q(1, 1, "rank_reason")}, None, 0, 0, {"2": 1}))
ALL_ORDER = ["P22", "P26", "P31", "P39", "P40", "P106", "P108", "P131", "P166", "P279", "P569", "P580", "P793",
             "P1082", "P1449", "P1889"]
KEPT_ORDER = [p for p in ALL_ORDER if p in KEPT_RELATIONS]
RELATION_KEYS = ["statements", "qualifiers", "time_model", "left_out_6b", "self_qualified", "rank_reason_mismatch",
                 "arity"]


class QualifierUsage(SliceTest):
    """§12: ``wdslice.py usage`` reshapes a complete run into ``p3a-qualifier-usage/1``."""

    def usage(self, run: str, out: str, expect: int = 0) -> str:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = wdslice.main(["usage", "--run", self.path(run), "--out", self.path(out)])
        self.assertEqual(code, expect, err.getvalue())
        return err.getvalue()

    def complete_run(self) -> Dict[str, Any]:
        os.makedirs(self.path("raw"))
        data = bz2.compress(MAIN_TEXT)
        src = self.write(os.path.join("raw", "wikidata-20260922-all.json.bz2"), data)
        run = self.slice(src, "out", "--workers", "2", "--expect-size", str(len(data)),
                         "--expect-md5", hashlib.md5(data).hexdigest())
        run["_data"] = data
        return run

    def test_usage(self) -> None:
        run = self.complete_run()
        data = run["_data"]
        self.assertIn("wrote", self.usage("out", "usage.json"))
        with open(self.path("usage.json"), encoding="utf-8") as fh:
            text = fh.read()
        doc = json.loads(text)
        with open(os.path.join(self.path("out"), "stats.json"), "rb") as fh:
            stats_sha256 = hashlib.sha256(fh.read()).hexdigest()
        expected = {
            "format": "p3a-qualifier-usage/1", "dump": "20260922", "naming": "wd-roles r1",
            "source": {"dump_file": "wikidata-20260922-all.json.bz2", "md5": hashlib.md5(data).hexdigest(),
                       "sha1": hashlib.sha1(data).hexdigest(), "sha256": hashlib.sha256(data).hexdigest(),
                       "slicer_commit": run["code"]["git_commit"], "stats_sha256": stats_sha256},
            "scopes": {"all": "every entity in the dump: items and property entities",
                       "kept": "the seed items of the slice: items with an English Wikipedia article (SPEC §2)"},
            # rule 8 by best rank: P1855 (normal Q19820110), P2302 (preferred Q21504947); not P1647, whose
            # preferred Q18616576 hides its normal Q19820110
            "out_of_scope": ["P1855", "P2302"],
            "all": {"relations": ALL_RELATIONS,
                    "out_of_scope_relations": {"P1855": rel(1, {"P39": q(1, 1, "qualifier")}, None, 0, 0,
                                                            {"3": 1})}},
            "kept": {"relations": KEPT_RELATIONS, "out_of_scope_relations": {}},
        }
        for scope in ("all", "kept"):
            for pid, entry in expected[scope]["relations"].items():  # type: ignore[index]
                self.assertEqual(doc[scope]["relations"].get(pid), entry, f"{scope} {pid}")
        self.assertEqual(doc, expected)
        # the order: top-level keys, relations and roles by numeric id, the keys of each relation
        self.assertEqual(list(doc), list(expected))
        self.assertEqual(list(doc["all"]["relations"]), ALL_ORDER)
        self.assertEqual(list(doc["kept"]["relations"]), KEPT_ORDER)
        for scope in ("all", "kept"):
            for pid, entry in doc[scope]["relations"].items():
                self.assertEqual(list(entry), RELATION_KEYS)
                self.assertEqual(list(entry["qualifiers"]), list(ALL_RELATIONS[pid]["qualifiers"]))
        self.assertEqual(text, wdslice.usage_text(doc))
        self.assertIn("(SPEC §2)", text)  # ensure_ascii=False
        # deterministic
        self.usage("out", "again.json")
        with open(self.path("again.json"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), text)

    def test_usage_layout(self) -> None:
        """§12's layout: one relation per line in compact JSON, everything around it indented by one space; one
        JSON document that reads back to the same object."""
        self.complete_run()
        self.usage("out", "usage.json")
        with open(self.path("usage.json"), encoding="utf-8") as fh:
            text = fh.read()
        doc = json.loads(text)
        self.assertEqual(wdslice.usage_text(doc), text)  # the round trip gives the same object and the same text
        self.assertEqual(json.loads(wdslice.usage_text(doc)), doc)

        def compact(value: Any) -> str:
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

        expected = ["{"]
        for i, (key, value) in enumerate(doc.items()):
            comma = "," if i < len(doc) - 1 else ""
            if key not in ("all", "kept"):
                expected.append(f' "{key}": ' + json.dumps(value, ensure_ascii=False, indent=1).replace("\n", "\n ")
                                + comma)
                continue
            expected.append(f' "{key}": {{')
            for j, (name, relations) in enumerate(value.items()):
                comma2 = "," if j < len(value) - 1 else ""
                if not relations:
                    expected.append(f'  "{name}": {{}}{comma2}')
                    continue
                expected.append(f'  "{name}": {{')
                expected += [f'   "{pid}": {compact(entry)}' + ("," if n < len(relations) - 1 else "")
                             for n, (pid, entry) in enumerate(relations.items())]
                expected.append("  }" + comma2)
            expected.append(" }" + comma)
        expected.append("}")
        self.assertEqual(text, "\n".join(expected) + "\n")
        # each relation is one line, which parses on its own to that relation, in document order
        relation_lines = [line for line in text.splitlines() if line.startswith('   "')]
        relations = [(pid, entry) for scope in ("all", "kept") for m in doc[scope].values() for pid, entry in m.items()]
        self.assertEqual(len(relations), len(ALL_ORDER) + 1 + len(KEPT_ORDER))  # + P1855, out of scope
        self.assertEqual([next(iter(json.loads("{" + line.strip().rstrip(",") + "}").items()))
                          for line in relation_lines], relations)

    def test_id_order(self) -> None:
        keys = ["P10", "P2", "P131:qualifier", "P1", "P580:qualifier", "P582", "P131", "P1534"]
        self.assertEqual(sorted(keys, key=wdslice._id_order),
                         ["P1", "P2", "P10", "P131", "P131:qualifier", "P580:qualifier", "P582", "P1534"])

    def test_refusals(self) -> None:
        self.complete_run()
        self.usage("missing", "u.json", expect=2)
        stats = os.path.join(self.path("out"), "stats.json")
        with open(stats, "ab") as fh:
            fh.write(b" ")  # no longer the file that run.json lists
        self.assertIn("does not match", self.usage("out", "u.json", expect=1))
        lines = MAIN_TEXT.split(b"\n")
        broken = b"\n".join(lines[:2] + [b"{"] + lines[2:])
        self.slice(self.write("broken.json.bz2", bz2.compress(broken)), "failed", "--workers", "1", expect=1)
        self.assertIn("not complete", self.usage("failed", "u.json", expect=1))
        self.assertFalse(os.path.exists(self.path("u.json")))

    def test_run_word_is_optional(self) -> None:
        src = self.write("d.json.bz2", bz2.compress(MAIN_TEXT))
        self.slice(src, "plain", "--workers", "1")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = wdslice.main(["run", "--input", src, "--out", self.path("with-run"), "--workers", "1"])
        self.assertEqual(code, 0, err.getvalue())
        self.assertEqual(output_files(self.path("with-run")), output_files(self.path("plain")))


# ------------------------------------------------------------------------------------------------ edge cases


class EdgeCases(SliceTest):
    """Empty maps written as ``[]``, the last line without a newline, non-ASCII, lone surrogates, long lines."""

    def test_php_empty_arrays_and_text(self) -> None:
        seed = {"type": "item", "id": "Q3001", "labels": [], "descriptions": [], "aliases": [],
                "claims": {"P31": [{"mainsnak": snak("P31", item_value("Q5")), "type": "statement",
                                    "qualifiers": [], "qualifiers-order": [], "id": "Q3001$1", "rank": "normal",
                                    "references": [{"hash": "abc", "snaks": [], "snaks-order": []}]}]},
                "sitelinks": sitelink_map({"enwiki": "Edge case"}), "pageid": 1, "ns": 0, "title": "Q3001",
                "lastrevid": 7, "modified": "2026-09-01T00:00:00Z"}
        bare = {"type": "item", "id": "Q3002", "labels": [], "descriptions": [], "aliases": [], "claims": [],
                "sitelinks": [], "pageid": 2, "ns": 0, "title": "Q3002", "lastrevid": 8,
                "modified": "2026-09-01T00:00:00Z"}
        text = item("Q3003", 9, {"en": "Grinning \U0001F600 face", "mul": "Łódź"},
                    {"en": "lone \udc80 surrogate"}, {}, {}, {"enwiki": "Łódź"})
        big = item("Q3004", 10, {"en": "Long"}, {}, {},
                   claims(*[statement("Q3004", snak("P2093", string_value(f"author {i:04d} é")),
                                      qualifiers=[qual("P1545", string_value(str(i)))]) for i in range(1500)]),
                   {"enwiki": "Long entity"})
        dump = dump_text([seed, bare, text, big], final_newline=False)
        self.assertGreater(max(map(len, dump.split(b"\n"))), 500_000)
        run = self.slice(self.write("d.json.bz2", bz2.compress(dump)), "out", "--workers", "2",
                         "--batch-bytes", "1000")
        self.assertEqual(run["counts"]["lines"], 6)  # the final "]" has no newline
        out = self.path("out")
        items = read_rows(os.path.join(out, "items-0000.jsonl.gz"))
        self.assertEqual([r["id"] for r in items], ["Q3001", "Q3003", "Q3004"])
        first = items[0]
        self.assertEqual((first["labels"], first["descriptions"], first["aliases"], first["x_sitelink_count"]),
                         ({}, {}, {}, 1))
        statement0 = first["claims"]["P31"][0]
        self.assertEqual((statement0["qualifiers"], statement0["qualifiers-order"]), ({}, []))
        self.assertEqual(statement0["references"], [{"hash": "abc", "snaks": [], "snaks-order": []}])
        self.assertEqual(items[1]["labels"]["en"]["value"], "Grinning \U0001F600 face")
        self.assertEqual(items[1]["descriptions"]["en"]["value"], "lone \udc80 surrogate")
        self.assertEqual(len(items[2]["claims"]["P2093"]), 1500)
        raw = b"\n".join(read_gz_lines(os.path.join(out, "items-0000.jsonl.gz")))
        raw.decode("utf-8")  # strict UTF-8
        self.assertIn("\U0001F600".encode("utf-8"), raw)
        self.assertIn(b"lone \\udc80 surrogate", raw)
        index = read_rows(os.path.join(out, "index-0000.jsonl.gz"))
        self.assertEqual(index[1], ["Q3002", "item", None, None, [], [], 0, None, 0, 0, 8, "2026-09-01T00:00:00Z",
                                    None])
        self.assertEqual(index[2][2], "Grinning \U0001F600 face")
        with open(os.path.join(out, "stats.json"), encoding="utf-8") as fh:
            stats = json.load(fh)
        self.assertEqual((stats["scopes"]["all"]["entities"], stats["scopes"]["all"]["statements"],
                          stats["scopes"]["all"]["qualified_statements"], stats["scopes"]["seed"]["entities"]),
                         (4, 1501, 1500, 3))
        self.assertEqual(stats["scopes"]["all"]["qualifier_snaks_hist"], {"0": 1, "1": 1500})
        self.assertEqual(stats["scopes"]["all"]["sitelinks_hist"], {"0": 1, "1": 3})

    def test_sitelink_histogram_top_bucket(self) -> None:
        many = [item(f"Q300{n}", n, {"en": "Many"}, {}, {}, {},
                     dict({f"x{i}wiki": f"T{i}" for i in range(n_sitelinks - 1)}, enwiki=f"Many {n}"))
                for n, n_sitelinks in ((5, 499), (6, 500), (7, 530))]
        run = self.slice(self.write("d.json.bz2", bz2.compress(dump_text(many + MAIN[:1]))), "out",
                         "--workers", "1")
        self.assertEqual(run["status"], "complete")
        with open(os.path.join(self.path("out"), "stats.json"), encoding="utf-8") as fh:
            stats = json.load(fh)
        self.assertEqual(stats["scopes"]["seed"]["sitelinks_hist"], {"499": 1, "500+": 2, "3": 1})
        self.assertEqual([r[6] for r in read_rows(os.path.join(self.path("out"), "index-0000.jsonl.gz"))],
                         [499, 500, 530, 3])


# ------------------------------------------------------------------------------------------------ failures


class Failures(SliceTest):
    """A worker exception fails the run with its traceback and leaves no process behind; usage errors."""

    def test_worker_exception(self) -> None:
        lines = MAIN_TEXT.split(b"\n")
        broken = b"\n".join(lines[:2] + [b'{"type":"item","id":"Q4001","labels":{,'] + lines[2:])
        run = self.slice(self.write("d.json.bz2", bz2.compress(broken)), "out", "--workers", "3", expect=1)
        self.assertEqual(run["status"], "failed")
        self.assertIn("batch 0, line 3", run["error"])
        self.assertIn("JSONDecodeError", run["error"])
        self.assertIn("Traceback", run["error"])
        self.assertFalse(os.path.exists(os.path.join(self.path("out"), "stats.json")))

    def test_failure_with_a_full_task_queue(self) -> None:
        """The failure comes while the reader has filled the task queue: the pass still ends promptly, and no
        worker, reader, queue feeder or drain thread is left behind."""
        lines = BIG_TEXT.split(b"\n")
        broken = b"\n".join(lines[:2] + [b"not json,"] + lines[2:] * 30)
        src = self.write("d.json.bz2", bz2.compress(broken))
        before = set(threading.enumerate())
        started = time.monotonic()
        run = self.slice(src, "out", "--workers", "2", "--batch-bytes", "100", expect=1)
        # the shutdown's own bound: reader 10 s, workers 5 s and 5 s, drain 2 s; it takes about a second
        self.assertLess(time.monotonic() - started, 45.0)
        self.assertIn("batch 1, line 1, text b'not json'", run["error"])
        wait_for(lambda: not [t for t in threading.enumerate() if t not in before and t.is_alive()
                              and t.name in ("QueueFeederThread", "wdslice-drain")], timeout=10)

    def test_missing_key_names_the_entity(self) -> None:
        bad = copy.deepcopy(MAIN[1])
        del bad["claims"]["P31"][0]["mainsnak"]
        run = self.slice(self.write("d.json.bz2", bz2.compress(dump_text([MAIN[0], bad]))), "out", "--workers", "1",
                         "--batch-bytes", "1", expect=1)
        self.assertIn("batch 2, line 1, entity Q1002: KeyError: 'mainsnak'", run["error"])

    def test_refuses_an_earlier_run(self) -> None:
        src = self.write("d.json.bz2", bz2.compress(MAIN_TEXT))
        first = self.slice(src, "out", "--workers", "1")
        before = output_files(self.path("out"))
        run = self.slice(src, "out", "--workers", "1", expect=2)
        self.assertIn("--force", run["_stderr"])
        self.assertEqual(output_files(self.path("out")), before)
        self.assertEqual(run["started"], first["started"])  # run.json is still the first run's
        # --force removes the earlier outputs, stale shards included; other files stay
        stale = os.path.join(self.path("out"), "items-0042.jsonl.gz")
        self.write(os.path.join("out", "items-0042.jsonl.gz"), b"stale")
        self.write(os.path.join("out", "notes.txt"), b"keep")
        run = self.slice(src, "out", "--workers", "1", "--force")
        self.assertEqual(run["status"], "complete")
        self.assertFalse(os.path.exists(stale))
        self.assertTrue(os.path.exists(os.path.join(self.path("out"), "notes.txt")))
        self.assertEqual(output_files(self.path("out")), dict(before, **{"notes.txt": b"keep"}))

    def test_usage_errors(self) -> None:
        src = self.write("d.json.bz2", bz2.compress(MAIN_TEXT))
        self.assertEqual(self.slice(src, "a", "--follow", expect=2)["_exit"], 2)
        self.assertEqual(self.slice(self.path("missing.bz2"), "b", expect=2)["_exit"], 2)
        self.assertEqual(self.slice(src, "c", "--workers", "0", expect=2)["_exit"], 2)
        self.assertEqual(self.slice(src, "d", "--expect-md5", "xyz", expect=2)["_exit"], 2)
        self.assertEqual([n for n in "abcd" if os.path.exists(self.path(n))], [])


class Signals(SliceTest):
    """The script in a child process: SIGINT (Ctrl-C to the process group), SIGTERM, a killed worker, and the
    output-directory lock. Each run waits in follow mode for a download that does not come."""

    def start(self, out: str, workers: int = 2) -> Any:
        data = bz2.compress(BIG_TEXT)
        src = self.write("partial.json.bz2", data[: len(data) // 2])
        proc = subprocess.Popen([sys.executable, SCRIPT, "--input", src, "--out", self.path(out), "--follow",
                                 "--expect-size", str(len(data)), "--workers", str(workers)],
                                stderr=subprocess.PIPE, text=True, start_new_session=True)
        self.addCleanup(self.reap, proc)

        def worker_pids() -> Optional[List[int]]:
            pids = [pid for pid, command in children_of(proc.pid) if "spawn_main" in command]
            return pids if len(pids) >= workers else None
        pids = wait_for(worker_pids)
        self.assertEqual(len(pids), workers)
        wait_for(lambda: os.path.exists(os.path.join(self.path(out), "run.json")))
        return proc, pids

    def reap(self, proc: Any) -> None:
        if proc.poll() is None:
            proc.kill()
        proc.wait(30)
        if proc.stderr:
            proc.stderr.close()

    def finish(self, proc: Any, pids: List[int], out: str) -> Dict[str, Any]:
        proc.wait(30)
        stderr = proc.stderr.read()
        self.assertEqual(proc.returncode, 1, stderr)
        wait_for(lambda: not any(alive(p) for p in pids), timeout=15)
        with open(os.path.join(self.path(out), "run.json"), encoding="utf-8") as fh:
            record = json.load(fh)
        self.assertEqual(record["status"], "failed")
        record["_stderr"] = stderr
        return record

    def test_ctrl_c(self) -> None:
        proc, pids = self.start("out")
        os.killpg(proc.pid, signal.SIGINT)  # as Ctrl-C does: the workers get it too and ignore it
        record = self.finish(proc, pids, "out")
        self.assertEqual(record["error"], "interrupted (SIGINT)")
        self.assertIn("failed: interrupted", record["_stderr"])

    def test_sigterm(self) -> None:
        proc, pids = self.start("out")
        os.kill(proc.pid, signal.SIGTERM)
        record = self.finish(proc, pids, "out")
        self.assertEqual(record["error"], f"terminated (signal {int(signal.SIGTERM)})")

    def test_killed_worker(self) -> None:
        proc, pids = self.start("out", workers=3)
        os.kill(pids[1], signal.SIGKILL)
        record = self.finish(proc, pids, "out")
        self.assertRegex(record["error"], r"^worker \d exited unexpectedly \(exit code -9\)$")

    def test_directory_lock(self) -> None:
        proc, pids = self.start("out")
        run = self.slice(self.write("d.json.bz2", bz2.compress(MAIN_TEXT)), "out", "--force", expect=2)
        self.assertIn("another run is writing to", run["_stderr"])
        self.assertTrue(os.path.exists(os.path.join(self.path("out"), "index-0000.jsonl.gz")))
        os.kill(proc.pid, signal.SIGINT)
        self.finish(proc, pids, "out")


if __name__ == "__main__":
    unittest.main()
