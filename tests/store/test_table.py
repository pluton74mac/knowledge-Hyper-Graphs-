"""Ruling 17: the public version-table interface (``store.table``) and ``TableStore``, the reference store over any
version table. ``JournalTable`` below stands for a backend: it keeps each version as canonical JSON text and builds
a fresh ``Entry`` on every read, and its store rolls a failed write back from a snapshot."""
from __future__ import annotations

import contextlib
import copy
import json
from typing import Any

import pytest

from khg_contracts import jsonio
from khg_contracts.errors import CapabilityMissing, ValidationError
from khg_contracts.store import ALL_FLAGS, MemoryStore, ScenarioClock, compare_containers, conformance
from khg_contracts.store.table import (MEMBERS, Entry, TableStore, VersionTable, VersionTableProtocol,
                                       bound_nodes)


class JournalTable:
    """A version table over JSON text: versions by id, and the four indexes as sorted lists."""

    def __init__(self, schema: Any):
        self.schema = schema
        self.state: dict[str, Any] = {"latest": None, "versions": {}, "node": {}, "relation": {}, "key": {},
                                      "ref": {}}
        self.fail_on: str | None = None  # add() raises for this id: a backend failing in the middle of a write

    @property
    def latest(self) -> int | None:
        return self.state["latest"]

    @latest.setter
    def latest(self, t: int | None) -> None:
        self.state["latest"] = t

    def __contains__(self, rid: object) -> bool:
        return rid in self.state["versions"]

    def __len__(self) -> int:
        return len(self.state["versions"])

    def ids(self) -> list[str]:
        return sorted(self.state["versions"])

    def entries(self, rid: str) -> list[Entry]:
        return [Entry(json.loads(text), t, self.schema) for text, t in self.state["versions"].get(rid, [])]

    def current(self, rid: str) -> dict[str, Any] | None:
        es = self.entries(rid)
        return es[-1].record if es else None

    def entry_at(self, rid: str, as_at: int | None = None) -> Entry | None:
        es = [e for e in self.entries(rid) if as_at is None or e.t <= as_at]
        return es[-1] if es else None

    def latest_version(self, rid: str) -> int:
        es = self.entries(rid)
        return es[-1].record["version"] if es else 0

    def _index(self, name: str, key: str, rid: str) -> None:
        ids = self.state[name].setdefault(key, [])
        if rid not in ids:
            ids.append(rid)
            ids.sort()

    def add(self, record: dict[str, Any], t: int) -> Entry:
        rid = record["id"]
        if rid == self.fail_on:
            raise RuntimeError(f"the backend failed while writing {rid}")
        self.state["versions"].setdefault(rid, []).append((jsonio.canonical(record), t))
        e = Entry(json.loads(jsonio.canonical(record)), t, self.schema)
        if e.is_edge:
            for _, _, node in bound_nodes(record):
                self._index("node", node, rid)
            self._index("relation", record["relation"], rid)
            if e.key_digest is not None:
                self._index("key", jsonio.canonical([record["relation"], e.key_digest]), rid)
            if isinstance(record.get("status_ref"), str):
                self._index("ref", record["status_ref"], rid)
        self.latest = t if self.latest is None else max(self.latest, t)
        return e

    def by_node(self, node: str) -> set[str]:
        return set(self.state["node"].get(node, []))

    def by_relation(self, relation: str) -> set[str]:
        return set(self.state["relation"].get(relation, []))

    def by_key(self, relation: str, digest: str) -> set[str]:
        return set(self.state["key"].get(jsonio.canonical([relation, digest]), []))

    def by_ref(self, lifecycle_id: str) -> set[str]:
        return set(self.state["ref"].get(lifecycle_id, []))


class JournalStore(TableStore):
    """``TableStore`` over ``JournalTable``: each write is one transaction, rolled back from a snapshot."""

    def __init__(self, schema: Any, *, refuse: frozenset[str] = frozenset(), **kwargs: Any):
        super().__init__(schema, table=JournalTable, store_id="journal", **kwargs)
        self.refuse = refuse
        self.log: list[str] = []

    @contextlib.contextmanager
    def transaction(self):
        snapshot = copy.deepcopy(self.table.state)
        self.log.append("begin")
        try:
            yield
        except BaseException:
            self.table.state = snapshot
            self.log.append("rollback")
            raise
        self.log.append("commit")

    def cannot_hold(self, record):
        if record.get("id") in self.refuse:
            return {"reason": "test", "id": record["id"]}
        return None


def journal(schema, clock):
    return JournalStore(schema, clock=clock)


# ------------------------------------------------------------------------------------------------ the interface


def test_the_protocol_names_the_thirteen_members():
    assert len(MEMBERS) == len(set(MEMBERS)) == 13
    assert "latest" in VersionTableProtocol.__annotations__
    for m in MEMBERS[1:]:
        assert callable(getattr(VersionTableProtocol, m, None)), m


def test_both_tables_satisfy_the_protocol(schema):
    assert isinstance(VersionTable(schema), VersionTableProtocol)
    assert isinstance(JournalTable(schema), VersionTableProtocol)
    assert not isinstance(object(), VersionTableProtocol)


def test_memory_store_is_the_table_store_over_the_in_memory_table(schema):
    s = MemoryStore(schema)
    assert isinstance(s, TableStore) and isinstance(s.table, VersionTable)
    assert repr(s).startswith("MemoryStore(") and s.store_id == "memory"
    t = TableStore(schema)
    assert isinstance(t.table, VersionTable) and t.store_id == "store" and repr(t).startswith("TableStore(")
    assert isinstance(JournalStore(schema).table, JournalTable)


def test_entry_computes_on_first_use(schema, fixture_doc):
    king = next(r for r in fixture_doc["records"] if r["id"] == "f:king-14")
    e = Entry(king, 5, schema)
    assert e.t == 5 and e.is_edge and e.record is king
    assert e.key_digest == "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96"
    assert e.bounds.kind == "period" and e.bounds.s_hi < e.bounds.e_lo
    assert len(e.idents) == len(king["bindings"])
    entity = Entry({"kind": "entity", "id": "ex:X", "types": ["Person"]}, 1, schema)
    assert (entity.is_edge, entity.key_digest, entity.bounds) == (False, None, None)
    assert bound_nodes(king) == [(1, "entity", "ex:LouisXIV"), (2, "entity", "ex:KingOfFrance"),
                                 (3, "entity", "ex:LouisXIII")]


# ------------------------------------------------------------------------------------------------ the full suite


def test_the_suite_passes_over_another_table():
    report = conformance.run(journal)
    assert report["summary"]["passed"] == 114 and report["summary"]["failed"] == 0, [
        (a["test"]["identifier"], a["result"].get("info")) for a in report["@graph"]
        if a["result"]["outcome"] != "passed"]


def test_the_journal_store_equals_the_memory_store_on_the_fixture(schema, fixture_doc):
    a, b = MemoryStore(schema, clock=ScenarioClock()), JournalStore(schema, clock=ScenarioClock())
    a.load(copy.deepcopy(fixture_doc))
    b.load(copy.deepcopy(fixture_doc))
    assert compare_containers(a.export("khg-json"), b.export("khg-json")) == []
    assert [jsonio.canonical(r) for r in a.iter_records()] == [jsonio.canonical(r) for r in b.iter_records()]


# ------------------------------------------------------------------------------------------------ transaction()


def test_each_write_is_one_transaction(schema, fixture_doc, rec, cur):
    s = JournalStore(schema, clock=ScenarioClock())
    s.load(fixture_doc)
    assert s.log == ["begin", "commit"]
    s.log.clear()
    s.put(rec("f:reg-1", add_evidence=[dict(cur, id="e2")]), actor="t")
    s.put(rec("f:reg-1", add_evidence=[dict(cur, id="e2")]), actor="t")  # content equal to the latest: a no-op
    s.apply({"op": "add_evidence", "target": "f:reg-1", "evidence": [dict(cur, id="e3")]}, actor="t")
    assert s.log == ["begin", "commit"] * 3
    assert s.get("f:reg-1")["version"] == 3


def test_a_failed_write_rolls_back(schema, fixture_doc, rec):
    s = JournalStore(schema, clock=ScenarioClock())
    s.load(fixture_doc)
    before = s.export("khg-jsonl")
    s.log.clear()
    with pytest.raises(ValidationError):  # refused before anything is written
        s.put([rec("f:reg-1", set={"rank": "preferred"}), rec("f:king-14", set={"relation": "nope"})], actor="t")
    s.table.fail_on = "f:reg-1"  # the backend fails after the first record of the batch is written
    with pytest.raises(RuntimeError):
        s.put([rec("f:loop-yyz", set={"rank": "preferred"}), rec("f:reg-1", set={"rank": "preferred"})], actor="t")
    assert s.log == ["begin", "rollback"] * 2 and s.export("khg-jsonl") == before
    s.table.fail_on = None
    assert s.put(rec("f:loop-yyz", set={"rank": "preferred"}), actor="t")["records"] == [("f:loop-yyz", 2,
                                                                                          "versioned")]


def test_writing_is_reentrant(schema):
    s = JournalStore(schema)
    with s.writing():
        with s.writing():
            assert s.log == ["begin"]
    assert s.log == ["begin", "commit"]
    with pytest.raises(RuntimeError), s.writing():
        raise RuntimeError("boom")
    assert s.log == ["begin", "commit", "begin", "rollback"]


def test_the_memory_store_opens_no_backend_transaction(schema):
    assert isinstance(MemoryStore(schema).transaction(), contextlib.nullcontext)


# ------------------------------------------------------------------------------------------------ cannot_hold()


def test_put_refuses_what_the_backend_cannot_hold_after_every_c2_check(schema, entities, rec):
    s = JournalStore(schema, clock=ScenarioClock(), refuse=frozenset({"f:reg-1", "f:loop-yyz"}))
    s.put(entities, actor="t")
    with pytest.raises(ValidationError) as e:
        s.put(rec("f:reg-1"), actor="t")
    assert e.value.codes == () and e.value.code is None
    assert e.value.info == {"id": "f:reg-1", "cannot_hold": {"reason": "test", "id": "f:reg-1"}}
    assert s.get("f:reg-1") is None and s.log[-1] == "rollback"
    with pytest.raises(ValidationError) as e:  # an invalid record gets its C2 code first
        s.put(rec("f:loop-yyz", set={"relation": "nope"}), actor="t")
    assert e.value.code == "KHG-S001"


def test_load_raises_or_skips_what_the_backend_cannot_hold(schema, fixture_doc):
    s = JournalStore(schema, clock=ScenarioClock(), refuse=frozenset({"f:born-louis14-paris"}))
    with pytest.raises(ValidationError) as e:
        s.load(copy.deepcopy(fixture_doc))
    assert e.value.codes == () and e.value.info["cannot_hold"]["reason"] == "test"
    assert list(s.iter_records()) == [] and s.info()["header"] is None
    report = s.load(copy.deepcopy(fixture_doc), on_missing="skip")
    assert report["skipped"] == ["f:born-louis14-paris", "f:claim-1"]  # and the fact that nests it
    assert report["records"] == 38 and s.get("f:claim-1") is None


def test_a_missing_flag_comes_before_what_the_backend_cannot_hold(schema, fixture_doc):
    s = JournalStore(schema, clock=ScenarioClock(), capabilities=ALL_FLAGS - {"goals"},
                     refuse=frozenset({"g:who-1774"}))
    with pytest.raises(CapabilityMissing):
        s.load(copy.deepcopy(fixture_doc))
    assert s.load(copy.deepcopy(fixture_doc), on_missing="skip")["skipped"] == ["g:who-1774"]
