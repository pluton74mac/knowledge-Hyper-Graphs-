"""The C1 record format ``khg-record/1.1.0`` (DESIGN §2; 1.1 is ruling 22). The reader takes 1.0.x and 1.1.x; a
writer stamps the lowest version whose features a container uses (``required_format``: 1.1.0 only for a
``khg:disputes`` record whose reason is ``bound_conflict``).

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

from typing import Any, Iterable, Mapping

from . import keys, lifecycle, project
from ._common import SPECIALS, VALUE_KINDS, value_kind
from .canonical import (KIND_ORDER, STORE_FIELDS, binding_sort_key, canonical_container, carried_supports,
                        decision_view, normalize, record_sort_key, resolve_supports)
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
from .values import (DATATYPES, canonical_decimal, canonical_literal, canonical_value, decimal, identity_key,
                     literal_identity, literal_label, value_identity, values_equal)
from .windows import (CALENDARS, NEG_INF, POS_INF, TimeParts, astronomical_year, format_instant, gregorian_from_jdn,
                      julian_day_number, parse_instant, parse_time, window, window_seconds)

#: The stamp of a container without 1.1 features, and the stamp of one with them (§11.2: the lowest that fits).
FORMAT = "khg-record/1.0.0"
FORMAT_1_1 = "khg-record/1.1.0"


def required_format(records_or_container: Any) -> str:
    """The lowest ``khg-record`` stamp a writer puts on a container of these records (a container or an iterable of
    records): ``FORMAT_1_1`` when a ``khg:disputes`` record gives the 1.1 reason ``bound_conflict`` (a 1.0 reader
    would refuse it, S026), else ``FORMAT``. The 1.1 schema features (``separators``, ``monotone``) are stamped on the
    schema document (``schema.required_format``)."""
    records = records_or_container.get("records") if isinstance(records_or_container, Mapping) else \
        records_or_container
    for r in records if isinstance(records, Iterable) else ():
        if isinstance(r, Mapping) and r.get("relation") == "khg:disputes" and r.get("reason") == "bound_conflict":
            return FORMAT_1_1
    return FORMAT


__all__ = [
    "ACTIVITY_FIELDS",
    "Bounds",
    "CALENDARS",
    "CONTENT_SLOTS",
    "DATATYPES",
    "EVENT_TYPES",
    "FORMAT",
    "FORMAT_1_1",
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
    "canonical_decimal",
    "canonical_literal",
    "canonical_value",
    "carried_supports",
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
    "required_format",
    "resolve_redirects",
    "resolve_supports",
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
