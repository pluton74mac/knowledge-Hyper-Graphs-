"""W0: the package surface: version, CONTRACTS, the error hierarchy, lazy subpackages and the console scripts
(DESIGN §10.2, §10.4, §11)."""
from __future__ import annotations

import importlib.metadata as md

import pytest

import khg_contracts
from khg_contracts import errors
from khg_contracts.errors import (CapabilityMissing, ConcurrencyError, KeyCollision, KHGError, LoaderError, NotFound,
                                  ValidationError, VersionError, make_finding)

SECTION_11_1 = {
    "khg-record": "1.1.0", "khg-relation-schema": "1.1.0", "khg-hif": "1.1.0", "role-convention": "1.0.0",
    "khg-queue": "1.1.0", "khg-store": "1.0.0", "khg-scenario": "1.0.0", "khg-scorers": "1.1.0",
    "khg-c5-io": "1.0.0", "khg-c4-items": "0.2.0", "khg-render": "1", "khg-migration-report": "1.0.0",
    "khg-codes": "1.1.0", "khg-malformed-cases": "1.0.0",
}
HASH_DOMAINS = ["khg-content-key", "khg-core-key", "khg-key-digest", "khg-event", "khg-literal-node",
                "khg-literal-binding", "khg-special-node", "khg-schema", "khg-decision", "khg-timed"]


def test_version_matches_the_distribution_metadata():
    assert khg_contracts.__version__ == "1.0.0.dev2"
    assert md.version("khg-contracts") == khg_contracts.__version__


def test_contracts_maps_every_format_id_and_hash_domain():
    c = khg_contracts.CONTRACTS
    assert {k: c[k] for k in SECTION_11_1} == SECTION_11_1
    assert all(c[d] == "1" for d in HASH_DOMAINS)
    assert set(c) == set(SECTION_11_1) | set(HASH_DOMAINS)
    with pytest.raises(TypeError):
        c["khg-record"] = "2.0.0"  # read-only
    assert dict(c)["khg-c4-items"] == "0.2.0"  # ruling 20


def test_the_migration_report_is_a_contract():
    """§14 ruling 6: ``khg-migration-report/1.0.0`` is a format id (§11.1), listed in ``CONTRACTS``; the migration
    stamps it, and the packaged report golden carries it."""
    from khg_contracts import data, migrate

    stamp = "khg-migration-report/" + khg_contracts.CONTRACTS["khg-migration-report"]
    assert migrate.REPORT_FORMAT == stamp == "khg-migration-report/1.0.0"
    assert data.load_json("sample/sample.migration-report.json")["format"] == stamp


def test_the_error_hierarchy():
    for cls in (ValidationError, KeyCollision, VersionError, ConcurrencyError, NotFound, CapabilityMissing,
                LoaderError):
        assert issubclass(cls, KHGError)
    assert issubclass(ValidationError, ValueError) and issubclass(LoaderError, ValueError)
    assert issubclass(NotFound, LookupError)
    assert set(errors.__all__) >= {"KHGError", "ValidationError", "KeyCollision", "VersionError", "ConcurrencyError",
                                   "NotFound", "CapabilityMissing", "LoaderError"}


def test_errors_carry_codes_and_info():
    e = KeyCollision("key invariant violated", codes=["KHG-D016"], info={"collisions": [{"record": "f:king-14b"}]})
    assert e.codes == ("KHG-D016",) and e.code == "KHG-D016"
    assert e.info["collisions"][0]["record"] == "f:king-14b"
    assert str(e) == "KHG-D016: key invariant violated"
    assert KHGError().codes == () and KHGError().code is None and KHGError().info == {}
    c = CapabilityMissing("valid_time")
    assert c.flag == "valid_time" and c.info == {"flag": "valid_time"} and "valid_time" in str(c)


def test_validation_error_from_findings():
    fs = [make_finding("KHG-L008", "/records/3", "possible overlap", severity="warning"),
          make_finding("KHG-S004", "/records/5", "max"), make_finding("KHG-S003", "/records/6", "min"),
          make_finding("KHG-S004", "/records/7", "max")]
    e = ValidationError.from_findings(fs)
    assert e.codes == ("KHG-S004", "KHG-S003")
    assert e.info["findings"] == fs
    assert str(e).startswith("KHG-S004 at /records/5: max") and "(and 2 more)" in str(e)
    assert make_finding("KHG-J003") == {"code": "KHG-J003", "severity": "error", "layer": "J", "path": "",
                                        "message": ""}


def test_subpackages_are_attributes():
    assert khg_contracts.jsonio.digest("khg-timed/1", {}) .startswith("sha256:")
    assert khg_contracts.schema.load_schema is not None
    with pytest.raises(AttributeError):
        khg_contracts.no_such_module  # noqa: B018
    with pytest.raises(AttributeError):
        khg_contracts._private  # noqa: B018


def test_the_four_console_scripts_are_declared():
    eps = {ep.name: ep for ep in md.entry_points(group="console_scripts") if ep.value.startswith("khg_contracts.")}
    assert sorted(eps) == ["khg-conformance", "khg-convert", "khg-migrate", "khg-validate"]
    assert all(ep.value.startswith("khg_contracts.cli:") and callable(ep.load()) for ep in eps.values())
