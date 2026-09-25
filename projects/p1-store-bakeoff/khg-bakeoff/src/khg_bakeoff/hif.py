"""The HIF file store (DESIGN §3.5; research 01 §6): the store's durable state is one role-aware HIF file
(``khg-hif/1.0.0``), written with khg-contracts ``hif.to_hif`` and read back with ``hif.from_hif``.

``HifStore(schema, *, path=None, clock=None, capabilities=None, store_id="hif")`` keeps an in-memory version table
(``VersionTable``) as its index. Each write is one transaction: when it ends, the store writes the HIF file of its
snapshot, decodes that text with ``from_hif`` (a snapshot HIF cannot hold fails the write here, before the file is
touched), writes it to a temporary file, swaps it in with ``os.replace`` and **rebuilds its index from it**, so every
read is served from what HIF kept. When a write fails, the index is rebuilt from the file as it was. A file that
already holds a store is reopened.

HIF is a file format, not an engine: every read runs ``TableStore``'s logic on the in-memory index rebuilt from the
file, so its rows are labelled "file, read in memory" (the director's ruling on review 01, R-06); ``trips`` counts
its file reads and writes. HIF holds one version per id, so the store declares neither ``transaction_time`` nor
``history_export`` (ruling 3). Two facts HIF has no place for travel in the file's metadata, under ``hif:metadata`` key ``p1-store``:
whether a document header is kept (a store without one computes it, S-EXP-009) and the store's latest transaction
time. Everything else is what ``to_hif`` writes. Every write rewrites the whole file: O(size) per write, the KB's
anti-pattern for a system of record, kept here as the interchange baseline.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Iterator

from khg_contracts import hif, jsonio
from khg_contracts.store import ALL_FLAGS, format_timestamp, parse_timestamp
from khg_contracts.store.protocol import RECORD_FORMAT
from khg_contracts.store.table import Entry, TableStore, VersionTable

from .shared import AdapterMixin, Trips

__all__ = ["FLAGS", "HifStore", "HifTable", "MARKER", "factory"]

FLAGS = ALL_FLAGS - {"transaction_time", "history_export"}
#: The ``hif:metadata`` key of the store's own bookkeeping.
MARKER = "p1-store"
_METADATA = "hif:metadata"


class HifTable:
    """A ``VersionTable`` that the store can replace from the file, and that counts its writes."""

    def __init__(self, schema: Any):
        self.schema = schema
        self.inner = VersionTable(schema)
        self.writes = 0

    def replace(self, inner: VersionTable) -> None:
        self.inner = inner

    @property
    def latest(self) -> int | None:
        return self.inner.latest

    @latest.setter
    def latest(self, t: int | None) -> None:
        self.inner.latest = t

    def __contains__(self, rid: object) -> bool:
        return rid in self.inner

    def __len__(self) -> int:
        return len(self.inner)

    def ids(self) -> list[str]:
        return self.inner.ids()

    def entries(self, rid: str) -> list[Entry]:
        return self.inner.entries(rid)

    def current(self, rid: str) -> dict[str, Any] | None:
        return self.inner.current(rid)

    def entry_at(self, rid: str, as_at: int | None = None) -> Entry | None:
        return self.inner.entry_at(rid, as_at)

    def latest_version(self, rid: str) -> int:
        return self.inner.latest_version(rid)

    def add(self, record: dict[str, Any], t: int) -> Entry:
        self.writes += 1
        return self.inner.add(record, t)

    def by_node(self, node: str) -> set[str]:
        return self.inner.by_node(node)

    def by_relation(self, relation: str) -> set[str]:
        return self.inner.by_relation(relation)

    def by_key(self, relation: str, digest: str) -> set[str]:
        return self.inner.by_key(relation, digest)

    def by_ref(self, lifecycle_id: str) -> set[str]:
        return self.inner.by_ref(lifecycle_id)

    def __iter__(self) -> Iterator[str]:
        return iter(self.inner)


class HifStore(AdapterMixin, TableStore):
    """A C2 store whose durable state is one HIF file (see the module docstring)."""

    FLAGS = FLAGS
    ENGINE = "HIF file"
    KIND = "file, read in memory"
    INT64 = False  # the index is Python's; the file holds literals as written

    def __init__(self, schema: Any, *, path: str | os.PathLike | None = None, clock: Any = None,
                 capabilities: Iterable[str] | None = None, store_id: str = "hif"):
        self.trips = Trips()
        super().__init__(schema, table=HifTable, clock=clock,
                         capabilities=self.FLAGS if capabilities is None else capabilities, store_id=store_id)
        self._owned = path is None
        if path is None:
            fd, name = tempfile.mkstemp(suffix=".hif.json", dir=os.environ.get("P1_TMP") or None)
            os.close(fd)
            os.unlink(name)
            path = name
        self.path = Path(path)
        self.persist_count = 0
        if self.path.exists() and self.path.stat().st_size > 0:
            self._reload()

    def engine_version(self) -> str:
        from khg_contracts import CONTRACTS, __version__

        return f"khg-hif/{CONTRACTS['khg-hif']} (khg-contracts {__version__} to_hif/from_hif)"

    # -- the file
    def _file_header(self) -> dict[str, Any]:
        kept = self.kept_header
        if kept is not None:
            header = json.loads(json.dumps(kept))
        else:
            header = {"kind": "header", "format": RECORD_FORMAT, "document_id": f"store:{self.store_id}",
                      "schema": self.schema.header}
        ext = header.setdefault("extensions", {})
        had_metadata = _METADATA in ext
        md = ext.setdefault(_METADATA, {})
        md[MARKER] = {"header_kept": kept is not None, "extensions": kept is not None and "extensions" in kept,
                      "hif_metadata": had_metadata,
                      "latest": None if self._table.latest is None else format_timestamp(self._table.latest)}
        return header

    def _persist(self) -> None:
        """Write the snapshot as the store's HIF file, and rebuild the index from that file's text. The text is
        decoded before it replaces the file: a snapshot HIF cannot hold (a fact on a node the file would not
        declare, say) fails the write and leaves the file as it was."""
        doc = self.export("hif", header=self._file_header())
        text = jsonio.canonical(doc)
        inner, header = self._decode(json.loads(text))
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        self.trips.hit("file")
        os.replace(tmp, self.path)  # one file, rewritten whole on every write
        self.persist_count += 1
        self._table.replace(inner)
        self.kept_header = header

    def _reload(self) -> None:
        """Rebuild the index and the kept header from the file (an empty store when there is none)."""
        inner, header = VersionTable(self.schema), None
        if self.path.exists() and self.path.stat().st_size > 0:
            self.trips.hit("file")
            inner, header = self._decode(json.loads(self.path.read_text(encoding="utf-8")))
        self._table.replace(inner)
        self.kept_header = header

    def _decode(self, doc: Any) -> tuple[VersionTable, dict[str, Any] | None]:
        """The index and the kept header of one HIF file (``from_hif``; ``ValidationError`` when it is not valid)."""
        inner = VersionTable(self.schema)
        container = hif.from_hif(doc, self.schema)
        for r in container["records"]:
            if r.get("kind") in ("entity", "hyperedge"):
                inner.add(r, parse_timestamp(r["recorded_at"]))
        header: dict[str, Any] | None = {k: v for k, v in container["header"].items() if k not in ("content", "as_at")}
        ext = header.get("extensions") or {}
        md = ext.get(_METADATA) or {}
        marker = md.pop(MARKER, None) or {}
        if not marker.get("hif_metadata") and not md:
            ext.pop(_METADATA, None)
        if not marker.get("extensions") and not ext:
            header.pop("extensions", None)
        if marker.get("latest") is not None:
            inner.latest = max(inner.latest or 0, parse_timestamp(marker["latest"]))
        if not marker.get("header_kept", True):
            header = None
        return inner, header

    # -- transactions
    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        before = jsonio.canonical([self.kept_header, self.kept_documents])
        self._table.writes = 0
        try:
            yield
            if self._table.writes or jsonio.canonical([self.kept_header, self.kept_documents]) != before:
                self._persist()
        except BaseException:
            self._reload()  # the file is the durable state: drop what the failed write left in the index
            raise

    # -- fidelity number 2
    def native_bindings(self, rid: str) -> list[dict[str, Any]] | None:
        """The bindings of fact ``rid`` as ``from_hif`` decodes them from the file (the index is rebuilt from it; HIF
        has no copy of the bindings besides its incidences)."""
        r = self._table.current(rid)
        if r is None or r.get("kind") != "hyperedge":
            return None
        return json.loads(json.dumps(r.get("bindings") or []))

    def close(self) -> None:
        if self._owned:
            with contextlib.suppress(OSError):
                self.path.unlink()


def factory(schema: Any, clock: Any) -> HifStore:
    """A fresh ``HifStore`` on a temporary file (removed by ``close``)."""
    return HifStore(schema, clock=clock)
