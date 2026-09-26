"""Role-aware HIF: the ``role-convention`` 1.0.0 and the ``khg-hif/1.0.0`` profile (DESIGN §4).

- ``to_hif(container, schema, *, relations=None, literal_nodes="shared", schema_document=False) -> dict``: C1 to
  HIF (§4.2), with closed slices (``relations``, §4.6), literal nodes shared by value or per binding, weights and
  binding extensions on incidences, and the schema inlined on request.
- ``from_hif(hif, schema=None) -> dict``: layers J, V, H, R and P, then decoding (§4.3); ``ValidationError``, with
  D009 when there is no schema at all.
- ``decode`` (the decoding pass alone), ``select_slice``, ``canonical_order`` (the §4.2 order recomputed from node
  attrs, for the loaders), ``node_value`` and ``literal_label`` (the §4.2 literal labels).
- ``convention_findings`` (the four rules, layer R) and ``profile_findings`` (the profile's Python checks, layer
  P); the validator runs them with the vendored and profile schemas (``validate``).
- ``external_allowed`` (§4.6; ruling 19): whether a file may name entities and facts it does not hold, which a
  container that is not complete does. ``to_hif`` stamps such a file ``PROFILE_1_1`` (``khg-hif/1.1.0``) and every
  other file ``PROFILE`` (``khg-hif/1.0.0``); ``from_hif`` reads both.
"""
from __future__ import annotations

from ..record import literal_label
from .checks import profile_findings
from .convention import convention_findings, role_position
from .decode import PROFILE_STEPS, decode, from_hif
from .encode import effective_direction, to_hif
from .nodes import node_value, value_node
from .order import canonical_order, incidence_sort_key, node_sort_key
from .profile import (DECLARATION_KEYS, EDGE_FIELDS, ENTITY_FIELDS, HIF_SCHEMA_SHA256, HIF_SCHEMA_URL,
                      KIND_PREFIXES, LITERAL_NODES, METADATA, NODE_KINDS, PROFILE, PROFILE_1_1, REQUIRED_KEYS,
                      ROLE_CONVENTION, WEIGHT, external_allowed, id_ok)
from .slices import select_slice

__all__ = [
    "DECLARATION_KEYS",
    "EDGE_FIELDS",
    "ENTITY_FIELDS",
    "HIF_SCHEMA_SHA256",
    "HIF_SCHEMA_URL",
    "KIND_PREFIXES",
    "LITERAL_NODES",
    "METADATA",
    "NODE_KINDS",
    "PROFILE",
    "PROFILE_1_1",
    "PROFILE_STEPS",
    "REQUIRED_KEYS",
    "ROLE_CONVENTION",
    "WEIGHT",
    "canonical_order",
    "convention_findings",
    "decode",
    "effective_direction",
    "external_allowed",
    "from_hif",
    "id_ok",
    "incidence_sort_key",
    "literal_label",
    "node_sort_key",
    "node_value",
    "profile_findings",
    "role_position",
    "select_slice",
    "to_hif",
    "value_node",
]
