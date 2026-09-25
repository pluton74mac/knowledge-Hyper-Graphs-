"""TypeDB 3.x feature probe for P1 (research 01): which TypeQL constructs the C2 mapping could use.

Needs a TypeDB CE server on 127.0.0.1:1729 (admin/password, TLS off) and typedb-driver 3.13.6.
Each probe defines a small schema in a fresh database and reports whether the server accepts it.
"""
from __future__ import annotations

import sys

from typedb.driver import Credentials, DriverOptions, DriverTlsConfig, TransactionType, TypeDB

ADDR = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:1729"
driver = TypeDB.driver(ADDR, Credentials("admin", "password"), DriverOptions(DriverTlsConfig.disabled()))


def fresh(name: str) -> str:
    if driver.databases.contains(name):
        driver.databases.get(name).delete()
    driver.databases.create(name)
    return name


def run(db: str, kind: TransactionType, query: str) -> str:
    try:
        with driver.transaction(db, kind) as tx:
            ans = tx.query(query).resolve()
            out = "ok"
            if ans.is_concept_rows():
                rows = list(ans.as_concept_rows())
                out = f"ok, {len(rows)} rows"
            elif ans.is_concept_documents():
                out = f"ok, docs {list(ans.as_concept_documents())}"
            if kind != TransactionType.READ:
                tx.commit()
            return out
    except Exception as e:  # noqa: BLE001 - the probe reports every refusal
        return "REFUSED: " + " ".join(str(e).split())[:300]


PROBES = [
    ("ordered role list (relates stop[])",
     "define entity airport, plays route:stop; relation route, relates stop[];"),
    ("owned attribute list (owns name[])",
     "define attribute name, value string; entity station, owns name[];"),
    ("struct value type",
     "define struct time-literal: time value string, precision value integer, calendar value string;"),
    ("attribute plays a role",
     "define attribute code, value string, plays tagged:tag; relation tagged, relates tag;"),
    ("relation plays a role (nesting)",
     "define entity person, plays claims:claimant; relation born-in, relates person, plays claims:claim;"
     " relation claims, relates claimant, relates claim; person plays born-in:person;"),
    ("relation owns attribute (literal as owned attribute)",
     "define attribute quantity-amount, value decimal; relation population, relates place, owns quantity-amount;"
     " entity place, plays population:place;"),
    ("role with @card(0..) (repeated role)",
     "define entity drug, plays coadmin:agent; relation coadmin, relates agent @card(2..);"),
    ("same role name in two relations (scoped roles)",
     "define entity p, plays r1:holder, plays r2:holder; relation r1, relates holder; relation r2, relates holder;"),
]

for title, q in PROBES:
    db = fresh("probe")
    print(f"{title}: {run(db, TransactionType.SCHEMA, q)}")

# Data-level probes on one schema
db = fresh("probe")
schema = """define
  attribute fid, value string;
  entity person, owns fid @key, plays married:spouse, plays goal:holder;
  relation married, relates spouse @card(0..2), owns fid @key;
  relation goal, relates holder @card(0..1), relates position @card(0..1), owns fid @key;
  entity position, owns fid @key, plays goal:position;
"""
print("data schema:", run(db, TransactionType.SCHEMA, schema))
print("insert relation with two players:", run(db, TransactionType.WRITE,
      'insert $a isa person, has fid "ex:A"; $b isa person, has fid "ex:B"; '
      '$m isa married (spouse: $a, spouse: $b), has fid "f:m1";'))
print("insert relation with no role player:", run(db, TransactionType.WRITE,
      'insert $g isa goal, has fid "g:empty";'))
print("read back the player-less relation:", run(db, TransactionType.READ,
      'match $g isa goal, has fid "g:empty";'))
print("insert same player twice in one role (multiset):", run(db, TransactionType.WRITE,
      'match $a isa person, has fid "ex:A"; insert $m isa married (spouse: $a, spouse: $a), has fid "f:m2";'))
print("count role players of f:m2:", run(db, TransactionType.READ,
      'match $m isa married, has fid "f:m2"; $m links (spouse: $p);'))
driver.close()
