"""W0: ``python -m khg_contracts.examples`` writes design-examples/ from the packaged data, byte for byte
(DESIGN §10.1, §10.6)."""
from __future__ import annotations

import subprocess
import sys

from khg_contracts import data, examples


def _tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_the_mirror_map_covers_146_packaged_files():
    m = examples.example_map()
    assert len(m) == 146
    assert set(m.values()) <= set(data.iter_files())
    assert "schemas/hif_schema_v0.1.0.json" not in m and "schemas/khg-relation-schema-1.0.0.schema.json" not in m
    assert m["conformance-scenarios/index.json"] == "scenarios/index.json"
    assert m["fixture.c1.json"] == "fixture/fixture.c1.json" and m["sample.khg.json"] == "sample/sample.khg.json"


def test_the_examples_equal_design_examples_byte_for_byte(tmp_path, examples_dir, repo_root):
    result = examples.write_examples(tmp_path / "out", tests_dir=repo_root / "tests")
    got, want = _tree(tmp_path / "out"), _tree(examples_dir)
    assert len(want) == 151
    assert result["missing"] == []  # the five test-only files, the evidence file included (W7)
    assert set(got) == set(want)
    assert [k for k in got if got[k] != want[k]] == []


def test_the_examples_without_the_test_files(tmp_path):
    result = examples.write_examples(tmp_path)
    assert result == {"written": sorted(examples.example_map()), "missing": []}
    assert (tmp_path / "schemas" / "khg-record-1.0.0.schema.json").read_bytes() == \
        data.read_bytes("schemas/khg-record-1.0.0.schema.json")
    assert not (tmp_path / "golden-sha256.json").exists()


def test_the_test_only_files_live_under_tests(repo_root, examples_dir):
    assert len(examples.TEST_ONLY) == 5
    for name, rel in examples.TEST_ONLY.items():
        assert (repo_root / "tests" / rel).read_bytes() == (examples_dir / name).read_bytes()


def test_the_command(tmp_path, repo_root):
    r = subprocess.run([sys.executable, "-m", "khg_contracts.examples", str(tmp_path / "x"), "--tests",
                        str(repo_root / "tests")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "x" / "golden-sha256.json").is_file()
    assert (tmp_path / "x" / "conformance-scenarios" / "S-KEY-018.json").is_file()
    assert examples.main([]) == 2
    assert examples.main([str(tmp_path / "y"), "--tests"]) == 2
