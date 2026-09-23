"""C1 conveniences (DESIGN §5): ``khg_to_xgi`` and ``khg_to_hnx`` run ``to_hif`` and then the loader;
``xgi_to_khg`` and ``hnx_to_khg`` run the export and then ``from_hif``."""
from __future__ import annotations

from typing import Any

from .bundle import Bundle
from .hnx import export_hnx, load_hnx
from .xgi import export_xgi, load_xgi

__all__ = ["hnx_to_khg", "khg_to_hnx", "khg_to_xgi", "xgi_to_khg"]


def khg_to_xgi(container: Any, schema: Any, **to_hif_kw: Any) -> Bundle:
    """``to_hif(container, schema, **to_hif_kw)``, then ``load_xgi``."""
    from ..hif import to_hif
    return load_xgi(to_hif(container, schema, **to_hif_kw))


def khg_to_hnx(container: Any, schema: Any, **to_hif_kw: Any) -> Bundle:
    """``to_hif(container, schema, **to_hif_kw)``, then ``load_hnx``."""
    from ..hif import to_hif
    return load_hnx(to_hif(container, schema, **to_hif_kw))


def xgi_to_khg(bundle: Bundle, schema: Any, *, strict: bool = True) -> dict[str, Any]:
    """``export_xgi(bundle, strict=strict)``, then ``from_hif`` with ``schema``: the canonical C1 container."""
    from ..hif import from_hif
    return from_hif(export_xgi(bundle, strict=strict), schema)


def hnx_to_khg(bundle: Bundle, schema: Any, *, strict: bool = True) -> dict[str, Any]:
    """``export_hnx(bundle, strict=strict)``, then ``from_hif`` with ``schema``: the canonical C1 container."""
    from ..hif import from_hif
    return from_hif(export_hnx(bundle, strict=strict), schema)
