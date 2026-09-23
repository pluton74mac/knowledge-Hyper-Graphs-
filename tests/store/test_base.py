"""W8: ``StoreBase`` derives the six derived methods from the nine core ones (DESIGN §6.1): a backend that only
implements the core passes the whole suite; and the public surface of ``khg_contracts.store`` (§10.2)."""
from __future__ import annotations

import subprocess
import sys

import pytest

from khg_contracts import errors
from khg_contracts import store as store_module
from khg_contracts.store import (ALL_FLAGS, CORE_METHODS, DERIVED_METHODS, FLAGS, MemoryStore, ScenarioClock,
                                 Store, StoreBase, conformance)


class CoreOnly(StoreBase):
    """A backend with the nine core methods only (delegated to a MemoryStore); StoreBase gives the rest."""

    def __init__(self, schema, *, clock=None, capabilities=None):
        super().__init__(schema, clock=clock, capabilities=capabilities, store_id="core-only")
        self.inner = MemoryStore(schema, clock=clock, capabilities=capabilities, store_id="core-only")
        self.closed = False

    def info(self):
        return self.inner.info()

    def put(self, records, **kw):
        return self.inner.put(records, **kw)

    def apply(self, event, **kw):
        return self.inner.apply(event, **kw)

    def load(self, container, **kw):
        return self.inner.load(container, **kw)

    def get(self, id, **kw):
        return self.inner.get(id, **kw)

    def history(self, id):
        return self.inner.history(id)

    def incident(self, node, **kw):
        return self.inner.incident(node, **kw)

    def find(self, relation, pattern, **kw):
        return self.inner.find(relation, pattern, **kw)

    def iter_records(self, **kw):
        return self.inner.iter_records(**kw)

    def close(self):
        self.closed = True


def test_a_core_only_backend_passes_the_suite():
    report = conformance.run(lambda schema, clock: CoreOnly(schema, clock=clock))
    assert report["summary"] == {"passed": 114, "failed": 0, "inapplicable": 0, "cantTell": 0, "total": 114}
    typedb = ALL_FLAGS - {"ordered_roles", "special_values", "goals", "transaction_time", "history_export"}
    limited = conformance.run(lambda schema, clock: CoreOnly(schema, clock=clock, capabilities=typedb))
    assert limited["summary"]["passed"] == 70 and limited["summary"]["failed"] == 0


def test_store_base_is_abstract_and_shares_the_basics(schema):
    with pytest.raises(TypeError):
        StoreBase(schema)  # the nine core methods are abstract
    s = CoreOnly(schema, capabilities=["goals"])
    assert isinstance(s, Store) and s.capabilities == frozenset({"goals"}) and s.store_id == "core-only"
    with pytest.raises(errors.CapabilityMissing) as e:
        s.need("nesting")
    assert e.value.flag == "nesting" and "core-only" in str(e.value)
    with CoreOnly(schema) as ctx:
        assert not ctx.closed
    assert ctx.closed


def test_the_derived_methods_through_the_core(schema, fixture_doc):
    s = CoreOnly(schema, clock=ScenarioClock())
    s.load(fixture_doc)
    assert list(s.get_many(["f:reg-1", "ex:HeLa", "f:nope"])) == ["ex:HeLa", "f:reg-1"]
    assert s.degree("ex:YYZ") == len(s.incident("ex:YYZ")) == 2
    walk = s.supersession_walk("f:born-skłodowska-warszawa", direction="backward")
    assert walk == {"start": "f:born-skłodowska-warszawa", "direction": "backward",
                    "steps": [{"depth": 1, "via": "m:sup-1", "reason": "correction",
                               "from": "f:born-skłodowska-warszawa", "to": "f:born-skłodowska-kraków"}],
                    "terminal": [{"id": "f:born-skłodowska-kraków", "status": "superseded"}]}
    assert s.supersession_walk("f:nope")["terminal"] == [{"id": "f:nope", "status": None}]
    with pytest.raises(ValueError):
        s.supersession_walk("f:reg-1", direction="sideways")
    for fmt in ("khg-json", "khg-jsonl", "hif"):
        assert s.export(fmt) == s.inner.export(fmt)
    assert s.export("khg-json")["header"]["document_id"] == "p2-gate-fixture"


def test_the_walk_branches_and_ends_on_chains(ms, entities, rec, cur):
    ms.put(entities, actor="t")
    ms.put(rec("f:coadmin-1", set={"id": "f:coadmin-0"}, drop=["confidence"]), actor="t")
    lactic = {"kind": "entity", "id": "ex:lactic_acidosis", "types": ["Outcome"], "label": "lactic acidosis"}
    ms.put(lactic, actor="t")
    ms.apply({"op": "supersede", "id": "m:sup-9", "superseded": ["f:coadmin-0"], "reason": "conflation",
              "records": [rec("f:coadmin-1"), rec("f:coadmin-1", set={"id": "f:coadmin-2"}, drop=["confidence"],
                                                  set_binding={"b3": {"entity": "ex:lactic_acidosis"}})],
              "evidence": [cur]}, actor="t")
    walk = ms.supersession_walk("f:coadmin-0")
    assert [(s["depth"], s["to"]) for s in walk["steps"]] == [(1, "f:coadmin-1"), (1, "f:coadmin-2")]
    assert walk["terminal"] == [{"id": "f:coadmin-1", "status": "asserted"},
                                {"id": "f:coadmin-2", "status": "asserted"}]
    before = ms.supersession_walk("f:coadmin-0", as_at="2026-10-01T00:00:02Z")
    assert before["steps"] == [] and before["terminal"] == [{"id": "f:coadmin-0", "status": "asserted"}]


def test_the_public_surface_of_section_10_2():
    for name in ("Store", "StoreBase", "MemoryStore", "memory_factory", "Timed", "Where", "SystemClock",
                 "ScenarioClock", "compare_containers", "conformance"):
        assert hasattr(store_module, name), name
    assert callable(store_module.conformance.run)
    for name in ("ValidationError", "KeyCollision", "VersionError", "ConcurrencyError", "NotFound",
                 "CapabilityMissing"):
        assert getattr(store_module, name) is getattr(errors, name)
    assert len(CORE_METHODS) == 9 and len(DERIVED_METHODS) == 6 and len(FLAGS) == 10
    assert all(callable(getattr(Store, m)) for m in CORE_METHODS + DERIVED_METHODS)
    assert set(store_module.__all__) <= set(dir(store_module)) | {"conformance"}
    with pytest.raises(AttributeError):
        store_module.no_such_name  # noqa: B018


def test_importing_the_store_loads_neither_the_runner_nor_an_engine():
    code = ("import json, sys\nimport khg_contracts.store\n"
            "print(json.dumps(sorted(m for m in sys.modules if m.startswith(('khg_contracts.store.conformance', "
            "'jsonschema', 'fastjsonschema', 'xgi', 'hypernetx', 'pandas', 'numpy', 'scipy')))))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "[]"
