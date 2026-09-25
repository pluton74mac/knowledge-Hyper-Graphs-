"""Backend 5, HIF files: a C2 store whose durable state is one role-aware HIF file (khg-hif/1.0.0), written after
every write with ``export("hif")`` (``hif.to_hif``) and read back with ``hif.from_hif``; ``MemoryStore`` is the
in-memory index. To test what the file really keeps, the index is rebuilt from the file after every write, so
every read is served from what HIF preserved. HIF holds one version per id (a snapshot), so the store declares
neither ``transaction_time`` nor ``history_export``.

Runs the full 114-scenario suite (writes included) and a close-and-reopen check. Writes out/hif.json.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from common import fixture, write_out
from khg_contracts import hif, jsonio
from khg_contracts.store import ALL_FLAGS, MemoryStore, ScenarioClock, compare_containers, conformance
from khg_contracts.store._table import VersionTable
from khg_contracts.store.clocks import parse_timestamp

FLAGS = ALL_FLAGS - {"transaction_time", "history_export"}
TMP = Path(os.environ.get("P1_TMP", tempfile.gettempdir()))


class HifStore(MemoryStore):
    """MemoryStore persisted as one HIF file, reloaded from it after every write."""

    def __init__(self, schema: Any, *, path: str | os.PathLike | None = None, clock: Any = None,
                 capabilities: Any = None, store_id: str = "hif"):
        super().__init__(schema, clock=clock, capabilities=FLAGS if capabilities is None else capabilities,
                         store_id=store_id)
        self.path = Path(path) if path is not None else Path(tempfile.mkstemp(suffix=".hif.json", dir=TMP)[1])
        self.writes = 0
        self.persist_seconds = 0.0
        if self.path.exists() and self.path.stat().st_size > 0:
            self._reload()

    def _persist(self) -> None:
        started = time.perf_counter()
        doc = self.export("hif")
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(jsonio.canonical(doc), encoding="utf-8")
        os.replace(tmp, self.path)  # one file, rewritten whole on every write
        self._reload()
        self.persist_seconds += time.perf_counter() - started
        self.writes += 1

    def _reload(self) -> None:
        container = hif.from_hif(json.loads(self.path.read_text(encoding="utf-8")), self.schema)
        latest = self._table.latest
        table = VersionTable(self.schema)
        for r in container["records"]:
            if r.get("kind") in ("entity", "hyperedge"):
                table.add(r, parse_timestamp(r["recorded_at"]))
        table.latest = latest if latest is not None else table.latest
        self._table = table
        self._header = {k: v for k, v in container["header"].items() if k not in ("content", "as_at")}

    def _commit(self, *a: Any, **k: Any) -> Any:
        receipt = super()._commit(*a, **k)
        self._persist()
        return receipt

    def load(self, *a: Any, **k: Any) -> Any:
        report = super().load(*a, **k)
        self._persist()
        return report

    def close(self) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass


def main() -> None:
    container, schema = fixture()
    result: dict[str, Any] = {"backend": "hif", "flags": sorted(FLAGS)}
    # load, close, reopen from the file alone
    path = TMP / "p1-hif-probe.hif.json"
    if path.exists():
        path.unlink()
    s1 = HifStore(schema, path=path, clock=ScenarioClock())
    s1.load(container)
    size = path.stat().st_size
    s2 = HifStore(schema, path=path, clock=ScenarioClock())
    result["file_bytes"] = size
    result["reopen_export_differences"] = len(compare_containers(container, s2.export("khg-json")))
    result["hif_valid"] = __import__("khg_contracts").validate.validate_hif(
        json.loads(path.read_text(encoding="utf-8")), schema=schema)["ok"]
    try:
        s2.get("f:king-14", as_at="2026-10-01T00:00:00Z")
        result["as_at after reopen"] = "answered"
    except Exception as e:  # noqa: BLE001
        result["as_at after reopen"] = f"{type(e).__name__}: {e}"
    s2.close()
    started = time.perf_counter()
    report = conformance.run(lambda sch, clock: HifStore(sch, clock=clock))
    result["conformance_seconds"] = round(time.perf_counter() - started, 2)
    result["conformance_summary"] = report["summary"]
    result["not_passed"] = {a["test"]["identifier"]: a["result"].get("info", "")[:300] or a["result"]["outcome"]
                            for a in report["@graph"] if a["result"]["outcome"] not in ("passed", "inapplicable")}
    result["inapplicable"] = sorted(a["test"]["identifier"] for a in report["@graph"]
                                    if a["result"]["outcome"] == "inapplicable")
    print(result["conformance_summary"], "reopen diffs:", result["reopen_export_differences"], "valid:",
          result["hif_valid"], "bytes:", size, "as_at:", result["as_at after reopen"][:80])
    write_out("hif", result)


if __name__ == "__main__":
    main()
