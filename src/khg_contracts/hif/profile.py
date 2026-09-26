"""The ``role-convention`` 1.0.0 declaration and the ``khg-hif`` profile vocabulary (DESIGN §4.1-§4.6).

- The metadata declaration block of §4.5: which keys exist, which are required, and the pinned values.
- How C1 fields map onto node and edge ``attrs`` (§4.2): flat dash-case ``khg-*`` keys plus the generic
  ``relation`` on edges and ``label`` on nodes.
- The derived node kinds and their reserved ``_:`` prefixes, and the id grammar of the profile (P003).
- The profile versions and the one rule 1.1.0 adds (§4.6, §14 ruling 19): a file that is not complete may name
  entities and facts it does not hold (``external_allowed``).
"""
from __future__ import annotations

import re
from types import MappingProxyType
from typing import Any, Mapping

from .. import data

__all__ = [
    "DECLARATION_KEYS",
    "EDGE_FIELDS",
    "ENTITY_FIELDS",
    "HIF_SCHEMA_SHA256",
    "HIF_SCHEMA_URL",
    "INCIDENCE_KHG_KEYS",
    "KIND_PREFIXES",
    "LITERAL_NODES",
    "MAX_ID",
    "METADATA",
    "NODE_KINDS",
    "PROFILE",
    "PROFILE_1_1",
    "REF_PREFIX",
    "REQUIRED_KEYS",
    "ROLE_CONVENTION",
    "WEIGHT",
    "external_allowed",
    "id_ok",
    "id_key",
]

#: The version of the upstream convention this package reads and writes (R003).
ROLE_CONVENTION = "1.0.0"
#: The profile id written to ``metadata["khg-profile"]``. Writers stamp the lowest version whose features a file uses
#: (§11.2): ``PROFILE`` (1.0.0), or ``PROFILE_1_1`` for a file that names an entity or fact it does not hold where
#: 1.0.0 allowed none: an entity node without a node record, or an external fact reference outside a slice (§4.6;
#: ruling 19). The reader accepts both; ``CONTRACTS["khg-hif"]`` is the newer.
PROFILE = "khg-hif/1.0.0"
PROFILE_1_1 = "khg-hif/1.1.0"
#: The raw URL of the vendored HIF schema, pinned at commit b691a3d, and its digest (P009).
HIF_SCHEMA_URL = data.HIF_SCHEMA_URL
HIF_SCHEMA_SHA256 = data.HIF_SCHEMA_SHA256
#: The C1 extension that carries a HIF weight on entities, hyperedges and bindings (§4.2).
WEIGHT = "hif:weight"
#: The C1 header extension that holds the HIF metadata keys outside the declaration block (§4.5).
METADATA = "hif:metadata"
#: The values of ``khg-literal-nodes`` and of ``to_hif(literal_nodes=...)``.
LITERAL_NODES = ("shared", "per_binding")

#: The keys of the declaration block (§4.5), in the order ``to_hif`` writes them. Decoding never passes them
#: through to ``hif:metadata``.
DECLARATION_KEYS = (
    "role-convention", "role-vocabulary", "hif-schema", "hif-schema-sha256", "khg-profile", "khg-record",
    "khg-schema", "khg-schema-sha256", "khg-document-id", "khg-literal-nodes", "khg-complete", "khg-slice",
    "khg-schema-document",
)
#: The declaration keys the profile requires (P001; ``role-convention`` is R003).
REQUIRED_KEYS = ("hif-schema", "hif-schema-sha256", "khg-profile", "khg-record", "khg-schema", "khg-schema-sha256",
                 "khg-document-id", "khg-literal-nodes")

#: C1 entity field -> node ``attrs`` key (§4.2); ``extensions["hif:weight"]`` becomes the node weight.
ENTITY_FIELDS = (("label", "label"), ("types", "khg-types"), ("aliases", "khg-aliases"),
                 ("redirect_to", "khg-redirect-to"), ("version", "khg-version"), ("recorded_at", "khg-recorded-at"),
                 ("extensions", "khg-extensions"))
#: C1 hyperedge field -> edge ``attrs`` key (§4.2); ``extensions["hif:weight"]`` becomes the edge weight.
EDGE_FIELDS = (("relation", "relation"), ("status", "khg-status"), ("status_ref", "khg-status-ref"),
               ("rank", "khg-rank"), ("rank_reason", "khg-rank-reason"), ("visibility", "khg-visibility"),
               ("evidence", "khg-evidence"), ("confidence", "khg-confidence"), ("source_text", "khg-source-text"),
               ("goal", "khg-goal"), ("reason", "khg-reason"), ("note", "khg-note"),
               ("typed_under", "khg-typed-under"), ("version", "khg-version"), ("recorded_at", "khg-recorded-at"),
               ("recorded_by", "khg-recorded-by"), ("extensions", "khg-extensions"))
#: The ``khg-*`` keys an incidence's ``attrs`` may hold beside ``role`` and ``role-position`` (P014).
INCIDENCE_KHG_KEYS = ("khg-bid", "khg-extensions")

#: The values of a node's ``attrs["khg-kind"]`` (P013).
NODE_KINDS = ("entity", "literal", "somevalue", "novalue", "unbound", "fact-ref")
REF_PREFIX = "_:ref:"
#: The id prefixes of the derived node kinds (P004); an entity id never starts with ``_:``.
KIND_PREFIXES: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "literal": ("_:lit:", "_:litb:"), "somevalue": ("_:sv:",), "novalue": ("_:nv:",), "unbound": ("_:var:",),
    "fact-ref": (REF_PREFIX,)})

#: The longest id in code points; a ``_:ref:`` node id may be ``len("_:ref:")`` longer (P003).
MAX_ID = 512
_BAD_ID_CHAR = re.compile(r"[\s\x00-\x1f\x7f]")


def id_ok(i: Any) -> bool:
    """True when ``i`` is a profile id (P003): 1 to 512 code points (518 for a ``_:ref:`` node) without white
    space or control characters."""
    if not isinstance(i, str):
        return False
    limit = MAX_ID + len(REF_PREFIX) if i.startswith(REF_PREFIX) else MAX_ID
    return 1 <= len(i) <= limit and not _BAD_ID_CHAR.search(i)


def external_allowed(metadata: Any) -> bool:
    """True when a file may name entities and facts it does not hold (§4.6; ruling 19): it is not complete
    (``khg-complete`` absent or false), or it is a slice (``khg-slice``; ``to_hif`` writes every slice with
    ``khg-complete: false``). Such an entity is an incidence node without a node record; such a fact is a
    ``khg-external`` fact reference. In any other file both are refused (D002, P017)."""
    md = metadata if isinstance(metadata, Mapping) else {}
    return md.get("khg-complete") is not True or "khg-slice" in md


def id_key(i: Any) -> tuple[str, str]:
    """A hashable key for a HIF id that keeps JSON types apart (``1`` and ``"1"`` are two ids)."""
    return (type(i).__name__, i if isinstance(i, str) else repr(i))
