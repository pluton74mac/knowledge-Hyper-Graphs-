"""The C1 record format ``khg-record/1.0.0`` (DESIGN §2).

Values and literals (``windows``, ``values``), refinement (``refine``), the canonical form (``canonical``), valid
time (``validity``), the derived block and the three keys (``derive``), evidence (``evidence``), redirects
(``entities``), container I/O (``container``), ``render_text`` (``render``), the derived node ids (``nodes``) and
the projections (``project``). The names of DESIGN §10.2:

- ``read_container``, ``iter_jsonl``, ``write_container``, ``container_sha256``;
- ``normalize``, ``derive``, ``content_key``, ``core_key``, ``key_digest``, ``arity``, ``valid_time``;
- ``value_identity``, ``window``; ``resolve_redirects``, ``supported_values``; ``render_text``;
- ``project.position_map``, ``positional``, ``hyper_relational``, ``role_value_set``, ``rdf_relation_instance``,
  ``from_rdf_relation_instance``, ``incidence_rows``, ``from_incidence_rows``.

Two submodules hold the rules the store and the validator share: ``lifecycle`` (the four axes, the transition table,
the version rule, the lifecycle pointers, supersessions and nesting cycles) and ``keys`` (the key invariant, L008 and
the ``KeyCollision`` info).
"""
from __future__ import annotations

from . import keys, lifecycle, project
from ._common import SPECIALS, VALUE_KINDS, value_kind
from .canonical import (KIND_ORDER, STORE_FIELDS, binding_sort_key, canonical_container, decision_view, normalize,
                        record_sort_key)
from .container import (FORMATS, check_container, container_sha256, iter_jsonl, read_container, serialize,
                        write_container)
from .derive import (CONTENT_SLOTS, arity, arity_bin, content_bindings, content_key, core_key, derive, key_digest,
                     with_derived)
from .entities import resolve_redirects
from .evidence import (ACTIVITY_FIELDS, EVENT_TYPES, event_hash, selected_text, span_selectors, stamp_event_hashes,
                       supported_values, text_sha256)
from .nodes import NONE_ID, literal_binding_node_id, literal_node_id, ref_node_id, special_node_id
from .refine import fact_refines, injective_match, value_refines
from .render import RENDER_FORMAT, render_text, render_value
from .validity import VALID_MODES, Bounds, bounds, definite_overlap, possible_overlap, valid_time
from .values import (DATATYPES, canonical_literal, canonical_value, decimal, identity_key, literal_identity,
                     literal_label, value_identity, values_equal)
from .windows import (CALENDARS, NEG_INF, POS_INF, TimeParts, astronomical_year, format_instant, gregorian_from_jdn,
                      julian_day_number, parse_instant, parse_time, window, window_seconds)

FORMAT = "khg-record/1.0.0"

__all__ = [
    "ACTIVITY_FIELDS",
    "Bounds",
    "CALENDARS",
    "CONTENT_SLOTS",
    "DATATYPES",
    "EVENT_TYPES",
    "FORMAT",
    "FORMATS",
    "KIND_ORDER",
    "NEG_INF",
    "NONE_ID",
    "POS_INF",
    "RENDER_FORMAT",
    "SPECIALS",
    "STORE_FIELDS",
    "TimeParts",
    "VALID_MODES",
    "VALUE_KINDS",
    "arity",
    "arity_bin",
    "astronomical_year",
    "binding_sort_key",
    "bounds",
    "canonical_container",
    "canonical_literal",
    "canonical_value",
    "check_container",
    "container_sha256",
    "content_bindings",
    "content_key",
    "core_key",
    "decimal",
    "decision_view",
    "definite_overlap",
    "derive",
    "event_hash",
    "fact_refines",
    "format_instant",
    "gregorian_from_jdn",
    "identity_key",
    "injective_match",
    "iter_jsonl",
    "julian_day_number",
    "key_digest",
    "keys",
    "lifecycle",
    "literal_binding_node_id",
    "literal_identity",
    "literal_label",
    "literal_node_id",
    "normalize",
    "parse_instant",
    "parse_time",
    "possible_overlap",
    "project",
    "read_container",
    "record_sort_key",
    "ref_node_id",
    "render_text",
    "render_value",
    "resolve_redirects",
    "selected_text",
    "serialize",
    "span_selectors",
    "special_node_id",
    "stamp_event_hashes",
    "supported_values",
    "text_sha256",
    "valid_time",
    "value_identity",
    "value_kind",
    "value_refines",
    "values_equal",
    "window",
    "window_seconds",
    "with_derived",
    "write_container",
]
