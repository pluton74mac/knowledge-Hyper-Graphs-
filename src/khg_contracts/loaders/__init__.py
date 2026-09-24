"""Library loaders for XGI and HyperNetX (DESIGN §5).

- ``load_xgi(hif, *, validate="profile") -> Bundle`` and ``load_hnx(...)`` build the library objects with public
  constructors only; the libraries' own HIF functions are never called (F1). ``hif`` is a parsed document or a path.
  ``validate`` is ``"profile"`` (J, V, H, R, P), ``"convention"`` (H, R) or ``"none"``; every mode refuses duplicate
  declarations (D001), ``asc`` files (P007) and directed files with an incidence without direction (P010).
- ``export_xgi(bundle, *, strict=True) -> dict`` and ``export_hnx(...)`` reconcile the library object with the
  context and write HIF again: profile files in the §4.2 order, other files in source order. The report of the last
  export is ``bundle.report`` (an ``ExportReport``); ``strict=True`` raises ``LoaderError`` (P005) on an unlabelled
  membership, a partial fact or a non-injective move.
- ``khg_to_xgi``, ``xgi_to_khg``, ``khg_to_hnx`` and ``hnx_to_khg`` go through ``to_hif`` and ``from_hif``.
- ``Bundle`` holds ``graph``, ``context`` (a ``Context``) and ``report``, with ``records``, ``roles``, ``derive`` and
  ``label``.

xgi, hypernetx and pandas are imported on first use, never by ``import khg_contracts.loaders``.
"""
from __future__ import annotations

from ..errors import LoaderError
from ._common import EXTRA, VALIDATE_MODES
from .bundle import Bundle
from .context import Context
from .convert import hnx_to_khg, khg_to_hnx, khg_to_xgi, xgi_to_khg
from .hnx import HNX_KEYWORDS, export_hnx, load_hnx
from .report import REPORT_KEYS, ExportReport
from .xgi import export_xgi, load_xgi

__all__ = [
    "EXTRA",
    "HNX_KEYWORDS",
    "REPORT_KEYS",
    "VALIDATE_MODES",
    "Bundle",
    "Context",
    "ExportReport",
    "LoaderError",
    "export_hnx",
    "export_xgi",
    "hnx_to_khg",
    "khg_to_hnx",
    "khg_to_xgi",
    "load_hnx",
    "load_xgi",
    "xgi_to_khg",
]
