"""TypeDB 3.x data-level probe for P1: role-player lists, attribute lists, structs, repeated players.

Needs the server of typedb_features.py. Prints what each insert and read returns.
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


def run(db: str, kind: TransactionType, query: str, show: bool = False) -> str:
    try:
        with driver.transaction(db, kind) as tx:
            ans = tx.query(query).resolve()
            out = "ok"
            if ans.is_concept_rows():
                rows = list(ans.as_concept_rows())
                out = f"ok, {len(rows)} rows"
                if show:
                    out += " " + str([{c: str(r.get(c)) for c in r.column_names()} for r in rows])[:600]
            elif ans.is_concept_documents():
                out = f"ok, docs {list(ans.as_concept_documents())}"[:800]
            if kind != TransactionType.READ:
                tx.commit()
            return out
    except Exception as e:  # noqa: BLE001
        return "REFUSED: " + " ".join(str(e).split())[:400]


db = fresh("lists")
print("schema:", run(db, TransactionType.SCHEMA, """define
  attribute fid, value string;
  attribute name, value string;
  struct tlit: time value string, precision value integer, calendar value string;
  attribute opened, value tlit;
  entity airport, owns fid @key, plays route:stop, plays pair:member;
  relation route, relates stop[], owns fid @key;
  relation pair, relates member @card(0..), owns fid @key;
  entity station, owns fid @key, owns name[];
"""))
print("insert airports:", run(db, TransactionType.WRITE,
      'insert $a isa airport, has fid "ex:YYZ"; $b isa airport, has fid "ex:YUL";'))
print("insert route with stop list [YYZ, YUL, YYZ]:", run(db, TransactionType.WRITE,
      'match $a isa airport, has fid "ex:YYZ"; $b isa airport, has fid "ex:YUL"; '
      'insert $r isa route (stop: [$a, $b, $a]), has fid "f:route-1";'))
print("read route stops:", run(db, TransactionType.READ,
      'match $r isa route, has fid "f:route-1"; $r links (stop: $s); $s has fid $id;', show=True))
print("read route stop list:", run(db, TransactionType.READ,
      'match $r isa route, has fid "f:route-1"; $r links (stop[]: $l);', show=True))
print("insert pair with YYZ twice:", run(db, TransactionType.WRITE,
      'match $a isa airport, has fid "ex:YYZ"; insert $p isa pair (member: $a, member: $a), has fid "f:loop";'))
print("read pair members (rows):", run(db, TransactionType.READ,
      'match $p isa pair, has fid "f:loop"; $p links (member: $m); $m has fid $id;', show=True))
print("fetch pair members:", run(db, TransactionType.READ,
      'match $p isa pair, has fid "f:loop"; fetch { "members": [ match $p links (member: $m); $m has fid $id; fetch { "id": $id }; ] };'))
print("insert station names list:", run(db, TransactionType.WRITE,
      'insert $s isa station, has fid "ex:tokyo", has name ["東京駅", "Tokyo Station"];'))
print("read station names:", run(db, TransactionType.READ,
      'match $s isa station, has fid "ex:tokyo", has name[] $n;', show=True))
print("insert struct attribute:", run(db, TransactionType.SCHEMA,
      'define entity event, owns fid @key, owns opened;'))
print("insert struct value:", run(db, TransactionType.WRITE,
      'insert $e isa event, has fid "e1", has opened { time: "+1914-12-20T00:00:00Z", precision: 11, calendar: "gregorian" };'))
driver.close()

# Is a repeated role player stored twice? Two links constraints must match two role-player instances.
driver = TypeDB.driver(ADDR, Credentials("admin", "password"), DriverOptions(DriverTlsConfig.disabled()))
print("pair links (member: $x, member: $y) with $x is $y:", run(db, TransactionType.READ,
      'match $p isa pair, has fid "f:loop"; $p links (member: $x, member: $y); $x is $y;', show=True))
print("pair links (member: $x, member: $y) any:", run(db, TransactionType.READ,
      'match $p isa pair, has fid "f:loop"; $p links (member: $x, member: $y);', show=True))
driver.close()

driver = TypeDB.driver(ADDR, Credentials("admin", "password"), DriverOptions(DriverTlsConfig.disabled()))
print("insert pair with YYZ and YUL:", run(db, TransactionType.WRITE,
      'match $a isa airport, has fid "ex:YYZ"; $b isa airport, has fid "ex:YUL"; '
      'insert $p isa pair (member: $a, member: $b), has fid "f:two";'))
print("pair f:two links (member: $x, member: $y):", run(db, TransactionType.READ,
      'match $p isa pair, has fid "f:two"; $p links (member: $x, member: $y);', show=False))
print("pair f:loop member count (reduce):", run(db, TransactionType.READ,
      'match $p isa pair, has fid "f:loop"; $p links (member: $m); reduce $c = count;', show=True))
driver.close()
