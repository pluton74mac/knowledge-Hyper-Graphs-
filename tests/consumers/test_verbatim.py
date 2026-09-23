"""The consumer tests copy the DESIGN §1.3 sequences verbatim (W13).

The §1.3 code block of DESIGN.md is a prologue (two imports and the schema line), then one block per consumer, each
starting with a ``# P…:`` comment and separated by blank lines. Every ``test_<project>.py`` holds its block between
the lines ``# >>> DESIGN §1.3`` and ``# <<< DESIGN §1.3``, and ``conftest.py`` holds the prologue's schema line. These
tests check that each marked copy, dedented, equals the design's block line for line, that the prologue's imports
run as written, and that every block of the design has its test file. They read DESIGN.md from the repository
checkout and skip where there is none (an sdist).
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

import khg_contracts

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent.parent / "projects" / "p2-role-aware-hif" / "DESIGN.md"
BEGIN, END = "# >>> DESIGN §1.3", "# <<< DESIGN §1.3"
FILES = {"P1": "test_p1.py", "P3a": "test_p3a.py", "P3b": "test_p3b.py", "P5": "test_p5.py", "P6": "test_p6.py",
         "P7": "test_p7.py", "P9": "test_p9.py", "P10": "test_p10.py"}


@pytest.fixture(scope="module")
def design() -> dict[str, list[str]]:
    """The §1.3 code block of DESIGN.md: ``prologue`` and one entry per consumer, as lists of lines."""
    if not DESIGN.is_file():
        pytest.skip("DESIGN.md is not available (not a repository checkout)")
    section = DESIGN.read_text(encoding="utf-8").split("### 1.3 Consumer call sequences", 1)[1]
    section = section.split("\n### ", 1)[0]
    code = section.split("```python\n", 1)[1].split("\n```", 1)[0]
    blocks = [block.splitlines() for block in code.split("\n\n")]
    out = {"prologue": blocks[0]}
    for block in blocks[1:]:
        m = re.match(r"# (P\w+): ", block[0])
        assert m, f"a §1.3 block that does not start with '# P…:': {block[0]!r}"
        out[m.group(1)] = block
    return out


def marked(path: Path) -> list[list[str]]:
    """The dedented blocks between the marker lines of a test file."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == BEGIN:
            assert current is None, f"{path.name}: nested marker"
            current = []
        elif line.strip() == END:
            assert current is not None, f"{path.name}: an end marker without a start"
            blocks.append(textwrap.dedent("\n".join(current)).splitlines())
            current = None
        elif current is not None:
            current.append(line)
    assert current is None, f"{path.name}: a start marker without an end"
    return blocks


def test_every_sequence_of_the_design_has_its_test(design):
    assert set(design) == {"prologue", *FILES}
    assert all((HERE / name).is_file() for name in FILES.values())


@pytest.mark.parametrize("project", sorted(FILES))
def test_the_copy_is_verbatim(design, project):
    assert marked(HERE / FILES[project]) == [design[project]]


def test_the_prologue(design):
    imports, load = design["prologue"][:2], design["prologue"][2:]
    assert load and load[0].startswith("S = sch.load_schema(")
    assert marked(HERE / "conftest.py") == [load]
    namespace: dict[str, object] = {}
    exec("\n".join(imports), namespace)  # the two import lines, as written
    names = ("hif", "identity", "loaders", "queue", "record", "sch", "store", "validate", "completion",
             "extraction", "memory", "retrieval", "stability")
    assert {n: getattr(namespace[n], "__name__", None) for n in names} == {
        **{n: f"khg_contracts.{n}" for n in ("hif", "identity", "loaders", "queue", "record", "store", "validate")},
        "sch": "khg_contracts.schema",
        **{n: f"khg_contracts.scorers.{n}" for n in ("completion", "extraction", "memory", "retrieval",
                                                    "stability")}}
    assert namespace["store"] is khg_contracts.store
