"""P1's deliverables state what the runs measured (review 01: R-08, R-11, R-12, R-13, R-14). These tests read the
project's files from the repository checkout and skip where there is none (an sdist)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
P1 = HERE.parents[1]
REPO = HERE.parents[3]
ROWS = {"postgres": "PostgreSQL", "sqlite": "SQLite", "oxigraph": "Oxigraph", "neo4j": "Neo4j", "typedb": "TypeDB",
        "hif": "HIF file"}


def read(path: Path) -> str:
    if not path.is_file():
        pytest.skip(f"{path.name} is not available (not a repository checkout)")
    return path.read_text(encoding="utf-8")


def gate_rows() -> dict[str, list[str]]:
    """The README's gate table: the cells of each backend's row."""
    text = read(P1 / "README.md").split("## Results and findings", 1)[1]
    out = {}
    for line in text.splitlines():
        if not line.startswith("| ") or line.startswith("| Backend") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split(" | ")]
        name = next(n for n, engine in ROWS.items() if cells[1].startswith(engine) or cells[0].startswith(engine))
        out[name] = cells
    return out


def _cell1(ds: dict) -> str:
    parts = []
    for d in ("fixture", "history", "edge"):
        e = ds[d]
        parts.append(f"{e['round_trip']['skipped']}, {e['round_trip']['silent']}" if e.get("loaded")
                     else "not loaded")
    return " / ".join(parts)


def _cell3(ds: dict) -> str:
    parts = []
    for d in ("fixture", "history", "edge"):
        e = ds[d]
        if not e.get("loaded"):
            parts.append("–")
            continue
        a = e["answers"]
        parts.append(f"{a['same']}/{a['compared']}" + (f" ({a['n/a']} n/a)" if a.get("n/a") else ""))
    return ", ".join(parts)


def test_r08_the_readme_gate_table_states_what_fidelity_measured():
    """R-08: the README's columns 1 to 3 are the numbers of ``results/fidelity.json`` (HIF's silent loss of an
    entity's recorded_by included), and finding 2 no longer says that nothing is lost silently."""
    fidelity = json.loads(read(P1 / "results" / "fidelity.json"))
    rows = gate_rows()
    assert set(rows) == set(ROWS)
    for name, cells in rows.items():
        ds = fidelity["backends"][name]["datasets"]
        n = ds["fixture"]["native"]
        assert cells[4] == _cell1(ds), name
        assert cells[5] == f"{n['bid_kept']}/{n['bindings']}; {n['literal_as_written_kept']}/{n['literals']}", name
        assert cells[6] == _cell3(ds), name
        assert cells[2].replace("–", "-") == fidelity["backends"][name]["kind"], name  # README writes an en dash
    readme = read(P1 / "README.md")
    assert "No backend loses anything silently" not in readme
    assert rows["hif"][4] == "0, 22 / not loaded / 0, 20"


def test_r11_p2_design_65_keeps_the_key_constraint_to_preferred_facts():
    design = read(REPO / "projects" / "p2-role-aware-hif" / "DESIGN.md")
    section = design.split("### 6.5 How P1's backends implement C2", 1)[1].split("\n## 7.", 1)[0]
    assert "Rank exceptions are handled in code" not in section
    incidence = next(line for line in section.splitlines() if line.startswith("| Incidence table"))
    assert "**preferred**" in incidence and "stays in code" in incidence
    assert "SVL41" in section and "IMPLEMENTATION-NOTES" in section


def test_r12_every_engine_and_client_has_its_licence_stated():
    readme = read(P1 / "khg-bakeoff" / "README.md")
    table = readme.split("## Licences", 1)[1]
    for component, licence in (("PostgreSQL (server)", "PostgreSQL Licence"), ("psycopg", "LGPL-3.0"),
                               ("Neo4j Community", "GPL v3"), ("neo4j Python driver", "Apache-2.0"),
                               ("TypeDB CE", "MPL 2.0"), ("typedb-driver", "Apache-2.0"),
                               ("pyoxigraph", "MIT or Apache-2.0"), ("SQLite", "public domain")):
        row = next((line for line in table.splitlines() if line.startswith(f"| {component}")), None)
        assert row is not None and licence in row, component
    header = read(P1 / "start-servers.sh").split("set -euo pipefail", 1)[0]
    for licence in ("PostgreSQL Licence", "GPL v3", "MPL 2.0", "LGPL-3.0", "Apache-2.0", "public domain"):
        assert licence in header, licence


def test_r13_typedb_listens_on_the_loopback_address_only():
    script = read(P1 / "start-servers.sh")
    config = script.split('cat > "$dir/config.yml" <<EOF', 1)[1].split("\nEOF", 1)[0]
    monitoring = config.split("monitoring:", 1)[1].split("reporting:", 1)[0]
    assert re.search(r"enabled:\s*false", monitoring), monitoring
    addresses = re.findall(r"listen-address:\s*(\S+)", config)
    assert addresses and all(a.startswith("127.0.0.1:") for a in addresses), addresses


def test_r14_ci_pins_postgres_and_imports_every_adapter():
    ci = read(REPO / ".github" / "workflows" / "ci.yml")
    job = ci.split("\n  khg-bakeoff:", 1)[1]
    image = re.search(r"image:\s*(\S+)", job).group(1)
    assert re.fullmatch(r"postgres:\d+\.\d+(-\w+)?(@sha256:[0-9a-f]{64})?", image), image
    assert "import khg_bakeoff.neo4j, khg_bakeoff.typedb" in job
    assert (HERE / "test_offline.py").is_file()
