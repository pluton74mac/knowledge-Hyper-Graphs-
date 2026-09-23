"""The library-evidence test (DESIGN §5, §12.4; marker ``evidence``, not the gate).

It runs the libraries' own HIF functions, which the loaders never call (F1), on four role-aware files: XGI's
``read_hif`` then ``write_hif``, and HyperNetX's ``from_hif`` then ``to_hif`` (twice, for the second generation).
It runs offline: HyperNetX fetches the HIF schema on every call, so ``requests.get`` serves the vendored copy. The
result documents what the libraries drop, and is written to ``library-hif-evidence.json`` next to this file, the
file the XGI and HyperNetX issues attach:

- ``fixture.hif.json``: XGI gives a ``Hypergraph``, 59 -> 56 records, 0 of 59 roles kept; HyperNetX's ``to_hif``
  returns None (``fillna("nil")`` breaks mixed-direction files);
- the directed slice: XGI gives a ``DiHypergraph``, 52 -> 51, 0 of 52 roles; HyperNetX gives 52 -> 50 records, loses
  all 12 metadata keys, adds ``default_attrs``, and its second generation is None;
- ``role-convention/tail-head.hif.json``: XGI 3 -> 3, 0 of 3 roles; HyperNetX 3 -> 2 (the repeated pair collapsed),
  with ``default_attrs`` added;
- ``role-convention/ordered.hif.json``: XGI 4 -> 3 (the repeated pair collapsed), 0 of 4 roles; HyperNetX 4 -> 3.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import data

xgi = pytest.importorskip("xgi")
hypernetx = pytest.importorskip("hypernetx")
requests = pytest.importorskip("requests")

pytestmark = [pytest.mark.evidence, pytest.mark.libs,
              pytest.mark.filterwarnings("ignore:Downcasting object dtype arrays:FutureWarning")]  # in hnx.to_hif

OUTPUT = Path(__file__).resolve().parent / "library-hif-evidence.json"
FILES = {"fixture.hif.json": "fixture/fixture.hif.json",
         "fixture.directed-slice.hif.json": "fixture/fixture.directed-slice.hif.json",
         "role-convention/tail-head.hif.json": "role-convention/tail-head.hif.json",
         "role-convention/ordered.hif.json": "role-convention/ordered.hif.json"}


class _SchemaResponse:
    """What ``requests.get`` returns for HyperNetX's schema URL: the vendored HIF schema."""

    status_code = 200

    def __init__(self) -> None:
        self._schema = data.hif_schema()
        self.text = json.dumps(self._schema)

    def json(self) -> dict[str, Any]:
        return copy.deepcopy(self._schema)


def _summary(src: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    """What survived: records in and out, roles kept, metadata lost and added, weights, isolated nodes kept."""
    roles = sum(1 for i in out["incidences"] if (i.get("attrs") or {}).get("role"))
    weights = sum(1 for k in ("nodes", "edges", "incidences") for x in src.get(k, []) if "weight" in x)
    isolated = {n["node"] for n in src.get("nodes", [])} - {i["node"] for i in src["incidences"]}
    return {"incidences": [len(src["incidences"]), len(out["incidences"])],
            "roles_kept": [roles, len(src["incidences"])],
            "metadata_lost": sorted(set(src.get("metadata", {})) - set(out.get("metadata", {}))),
            "metadata_added": sorted(set(out.get("metadata", {})) - set(src.get("metadata", {}))),
            "weights_in_source": weights,
            "isolated_nodes_kept": sorted({n["node"] for n in out.get("nodes", [])} & isolated)}


def _xgi_row(src: dict[str, Any], tmp: Path) -> dict[str, Any]:
    source, target = tmp / "in.json", tmp / "out.json"
    source.write_text(json.dumps(src, ensure_ascii=False), encoding="utf-8")
    try:
        graph = xgi.read_hif(str(source))
        xgi.write_hif(graph, str(target))
        return {"class": type(graph).__name__, **_summary(src, json.loads(target.read_text(encoding="utf-8")))}
    except Exception as e:  # noqa: BLE001 - a library failure is evidence too
        return {"error": f"{type(e).__name__}: {str(e)[:120]}"}


def _hnx_row(src: dict[str, Any]) -> dict[str, Any]:
    network_type = src.get("network-type", "undirected")
    try:
        graph = hypernetx.from_hif(copy.deepcopy(src))
        if graph is None:
            return {"from_hif": None}
        out = hypernetx.to_hif(graph, network_type=network_type)
        if out is None:
            return {"to_hif": None}
        row = _summary(src, out)
        again = hypernetx.from_hif(out)
        row["second_generation"] = None if again is None else "dict"
        if again is not None:
            out2 = hypernetx.to_hif(again, network_type=network_type)
            row["second_generation"] = None if out2 is None else len(out2["incidences"])
        return row
    except Exception as e:  # noqa: BLE001 - a library failure is evidence too
        return {"error": f"{type(e).__name__}: {str(e)[:120]}"}


@pytest.fixture(scope="module")
def evidence(tmp_path_factory) -> dict[str, Any]:
    """Run the libraries' HIF functions on the four files, offline, and write ``library-hif-evidence.json``."""
    patch = pytest.MonkeyPatch()
    patch.setattr(requests, "get", lambda url, *args, **kwargs: _SchemaResponse())
    try:
        rows = []
        for name, rel in FILES.items():
            src = data.load_json(rel)
            rows.append({"file": name, "network-type": src.get("network-type"),
                         "xgi": _xgi_row(src, tmp_path_factory.mktemp("xgi")), "hnx": _hnx_row(src)})
    finally:
        patch.undo()
    doc = {"format": "khg-library-evidence/1.0.0", "xgi": xgi.__version__, "hypernetx": hypernetx.__version__,
           "rows": rows}
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return doc


def _row(evidence: dict[str, Any], name: str) -> dict[str, Any]:
    return next(r for r in evidence["rows"] if r["file"] == name)


def test_the_evidence_names_the_probed_library_versions(evidence):
    assert (evidence["xgi"], evidence["hypernetx"]) == ("0.10.2", "2.4.3")
    assert [r["file"] for r in evidence["rows"]] == list(FILES)
    assert not any("error" in r["xgi"] or "error" in r["hnx"] for r in evidence["rows"])


def test_xgi_keeps_no_role_and_collapses_repeated_pairs(evidence):
    want = {"fixture.hif.json": ("Hypergraph", [59, 56]), "fixture.directed-slice.hif.json": ("DiHypergraph", [52, 51]),
            "role-convention/tail-head.hif.json": ("DiHypergraph", [3, 3]),
            "role-convention/ordered.hif.json": ("Hypergraph", [4, 3])}
    for name, (cls, counts) in want.items():
        x = _row(evidence, name)["xgi"]
        assert (x["class"], x["incidences"]) == (cls, counts)
        assert x["roles_kept"] == [0, counts[0]]  # XGI cannot hold incidence attrs
        assert x["metadata_lost"] == [] and x["metadata_added"] == []
    assert _row(evidence, "fixture.hif.json")["xgi"]["isolated_nodes_kept"] == ["ex:Mazarin"]


def test_hypernetx_returns_none_for_the_mixed_direction_fixture(evidence):
    assert _row(evidence, "fixture.hif.json")["hnx"] == {"to_hif": None}  # fillna("nil") on missing directions


def test_hypernetx_drops_metadata_and_repeated_records_and_cannot_read_its_directed_output(evidence):
    s = _row(evidence, "fixture.directed-slice.hif.json")["hnx"]
    assert s["incidences"] == [52, 50] and s["roles_kept"] == [50, 52]
    assert len(s["metadata_lost"]) == 12 and "khg-profile" in s["metadata_lost"]
    assert s["metadata_added"] == ["default_attrs"]
    assert s["second_generation"] is None  # the default_attrs direction: null is read back as a column
    t = _row(evidence, "role-convention/tail-head.hif.json")["hnx"]
    assert t["incidences"] == [3, 2] and t["metadata_added"] == ["default_attrs"]
    assert t["metadata_lost"] == ["role-convention"] and t["second_generation"] is None
    o = _row(evidence, "role-convention/ordered.hif.json")["hnx"]
    assert o["incidences"] == [4, 3] and o["second_generation"] == 3


def test_the_written_file_is_the_evidence_the_issues_attach(evidence, repo_root):
    text = OUTPUT.read_text(encoding="utf-8")
    assert json.loads(text) == evidence and text.endswith("\n")
    committed = repo_root / "projects" / "p2-role-aware-hif" / "design-examples" / "library-hif-evidence.json"
    if committed.is_file():  # a repository checkout: the verified evidence of the design, byte for byte
        assert text == committed.read_text(encoding="utf-8")
