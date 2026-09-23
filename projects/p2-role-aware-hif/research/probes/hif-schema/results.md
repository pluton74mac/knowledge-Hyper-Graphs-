# HIF probe results

jsonschema 4.26.0 (validator class chosen from each schema's $schema: ['Draft7Validator']), fastjsonschema 2.22.2, Python 3.11.15.

Cells read `valid` / `invalid` when both validators agree; otherwise `js:<jsonschema> / fjs:<fastjsonschema>`.
`strict JSON` flags NaN/Infinity literals and duplicate object keys, which Python's json module accepts.

Schemas:

- **S0 2024-08-05 c58b153**: `history/2024-08-05_c58b153_hif_schema.json` (initial list-based draft, superseded; Draft7Validator)
- **S1 2024-08-13 e5c868b**: `history/2024-08-13_e5c868b_hif_schema_v0.1.0.json` (first object-record schema; key 'attr'; Draft7Validator)
- **S2 2024-08-21 53a8a93**: `history/2024-08-21_53a8a93_hif_schema_v0.1.0.json` (+ top-level additionalProperties:false; Draft7Validator)
- **S3 2024-09-26 7aefda6**: `history/2024-09-26_7aefda6_hif_schema_v0.1.0.json` ('attr' renamed 'attrs'; Draft7Validator)
- **S4 2024-10-03 de5f89f**: `history/2024-10-03_de5f89f_hif_schema_v0.1.0.json` (+ record-level additionalProperties:false; Draft7Validator)
- **v0.1.0 (HEAD b691a3d)**: `hif_schema_v0.1.0.json` (published, version 0.1.0; Draft7Validator)
- **latest (HEAD b691a3d)**: `hif_schema.json` (published, version latest; Draft7Validator)

### P2 cases and the KB sample

| case | strict JSON | S0 2024-08-05 c58b153 | S1 2024-08-13 e5c868b | S2 2024-08-21 53a8a93 | S3 2024-09-26 7aefda6 | S4 2024-10-03 de5f89f | v0.1.0 (HEAD b691a3d) | latest (HEAD b691a3d) |
|---|---|---|---|---|---|---|---|---|
| `../../../../../schemas/sample.hif.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/01-baseline-role-in-incidence-attrs.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/02-same-edge-node-pair-twice-different-roles.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/03-node-id-equals-edge-id-nesting.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/04-top-level-version-key.json` | ok | invalid | valid | invalid | invalid | invalid | invalid | invalid |
| `cases/05-top-level-roles-vocabulary.json` | ok | invalid | valid | invalid | invalid | invalid | invalid | invalid |
| `cases/06-top-level-dollar-schema-key.json` | ok | invalid | valid | invalid | invalid | invalid | invalid | invalid |
| `cases/07-metadata-version-declaration.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/08-metadata-roles-vocabulary.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/09-incidence-attrs-varied-shapes.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/10-incidence-attrs-not-object.json` | ok | invalid | valid | valid | invalid | invalid | invalid | invalid |
| `cases/11-incidence-record-level-role-key.json` | ok | invalid | valid | valid | valid | invalid | invalid | invalid |
| `cases/12-direction-value-used-as-role.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `cases/13-edge-record-level-relation-key.json` | ok | invalid | valid | valid | valid | invalid | invalid | invalid |
| `cases/14-node-record-level-type-key.json` | ok | invalid | valid | valid | valid | invalid | invalid | invalid |
| `cases/15-integer-ids.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/16-mixed-id-types.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/17-integral-float-id.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/18-non-integral-float-id.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `cases/19-boolean-id.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `cases/20-null-id.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `cases/21-empty-string-id.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/22-integer-id-beyond-2e53.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/23-directed-network-missing-direction.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/24-undirected-network-with-direction.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/25-no-network-type-with-direction.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/26-network-type-not-in-enum.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `cases/27-edge-declared-without-incidences.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/28-incidence-undeclared-node.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/29-incidence-undeclared-edge.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/30-weight-on-all-record-kinds.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/31-empty-object.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `cases/32-minimal-empty-incidences.json` | ok | valid | valid | valid | valid | valid | valid | valid |
| `cases/33-metadata-dollar-schema-key.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `cases/34-empty-file-zero-bytes.json` | not JSON | parse-error | parse-error | parse-error | parse-error | parse-error | parse-error | parse-error |
| `cases/35-nan-literal-in-attrs.json` | non-standard JSON constant NaN | invalid | valid | valid | valid | valid | valid | valid |
| `cases/36-duplicate-json-key-in-attrs.json` | duplicate object key 'role' | invalid | valid | valid | valid | valid | valid | valid |

First error reported by jsonschema under `latest (HEAD b691a3d)` (empty = valid):

- `cases/04-top-level-version-key.json`: (root): Additional properties are not allowed ('version' was unexpected)
- `cases/05-top-level-roles-vocabulary.json`: (root): Additional properties are not allowed ('roles' was unexpected)
- `cases/06-top-level-dollar-schema-key.json`: (root): Additional properties are not allowed ('$schema' was unexpected)
- `cases/10-incidence-attrs-not-object.json`: incidences/0/attrs: 'treatment' is not of type 'object'
- `cases/11-incidence-record-level-role-key.json`: incidences/0: Additional properties are not allowed ('role' was unexpected)
- `cases/12-direction-value-used-as-role.json`: incidences/0/direction: 'treatment' is not one of ['head', 'tail']
- `cases/13-edge-record-level-relation-key.json`: edges/0: Additional properties are not allowed ('relation' was unexpected)
- `cases/14-node-record-level-type-key.json`: nodes/0: Additional properties are not allowed ('type' was unexpected)
- `cases/18-non-integral-float-id.json`: incidences/0/node: 1.5 is not of type 'string', 'integer'
- `cases/19-boolean-id.json`: incidences/0/node: True is not of type 'string', 'integer'
- `cases/20-null-id.json`: incidences/0/node: None is not of type 'string', 'integer'
- `cases/26-network-type-not-in-enum.json`: network-type: 'knowledge-hypergraph' is not one of ['undirected', 'directed', 'asc']
- `cases/31-empty-object.json`: (root): 'incidences' is a required property
- `cases/34-empty-file-zero-bytes.json`: JSON parse error: Expecting value: line 1 column 1 (char 0)

### Upstream calibration files (tests/test_files)

| case | strict JSON | S0 2024-08-05 c58b153 | S1 2024-08-13 e5c868b | S2 2024-08-21 53a8a93 | S3 2024-09-26 7aefda6 | S4 2024-10-03 de5f89f | v0.1.0 (HEAD b691a3d) | latest (HEAD b691a3d) |
|---|---|---|---|---|---|---|---|---|
| `HIF-compliant/duplicated_nodes_edges.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/empty_arrays.json` | ok | valid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/empty_hypergraph.json` | ok | valid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/metadata_with_deeply_nested_attributes.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/metadata_with_nested_attributes.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/missing_direction.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/single_edge.json` | ok | valid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/single_edge_with_attrs.json` | ok | valid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/single_incidence.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/single_incidence_with_attrs.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/single_incidence_with_weights.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/single_node.json` | ok | valid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/single_node_with_attrs.json` | ok | valid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/valid_incidence_head.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `HIF-compliant/valid_incidence_tail.json` | ok | invalid | valid | valid | valid | valid | valid | valid |
| `HIF-non-compliant/bad_edge_field.json` | ok | valid | valid | valid | valid | invalid | invalid | invalid |
| `HIF-non-compliant/bad_edge_without_id.json` | ok | valid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/bad_incidence_field.json` | ok | invalid | valid | valid | valid | invalid | invalid | invalid |
| `HIF-non-compliant/bad_network_type.json` | ok | valid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/bad_node_field.json` | ok | valid | valid | valid | valid | invalid | invalid | invalid |
| `HIF-non-compliant/bad_node_float.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/bad_node_without_id.json` | ok | valid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/bad_top_level_field.json` | ok | valid | valid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/empty.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/extra_fields_with_direction.json` | ok | invalid | valid | valid | valid | invalid | invalid | invalid |
| `HIF-non-compliant/invalid_direction_value.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/metadata_as_list.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/missing_required_field_incidence.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/missing_required_fields_with_direction.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/single_incidence_with_direction_not_in_enum.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |
| `HIF-non-compliant/single_incidence_with_weight_as_string.json` | ok | invalid | invalid | invalid | invalid | invalid | invalid | invalid |

First error reported by jsonschema under `latest (HEAD b691a3d)` (empty = valid):

- `HIF-non-compliant/bad_edge_field.json`: edges/0: Additional properties are not allowed ('test' was unexpected)
- `HIF-non-compliant/bad_edge_without_id.json`: edges/0: 'edge' is a required property
- `HIF-non-compliant/bad_incidence_field.json`: incidences/0: Additional properties are not allowed ('test' was unexpected)
- `HIF-non-compliant/bad_network_type.json`: network-type: 'badnt' is not one of ['undirected', 'directed', 'asc']
- `HIF-non-compliant/bad_node_field.json`: nodes/0: Additional properties are not allowed ('test' was unexpected)
- `HIF-non-compliant/bad_node_float.json`: nodes/0/node: 1.23 is not of type 'string', 'integer'
- `HIF-non-compliant/bad_node_without_id.json`: nodes/0: 'node' is a required property
- `HIF-non-compliant/bad_top_level_field.json`: (root): Additional properties are not allowed ('test' was unexpected)
- `HIF-non-compliant/empty.json`: (root): 'incidences' is a required property
- `HIF-non-compliant/extra_fields_with_direction.json`: incidences/0: Additional properties are not allowed ('extra_field' was unexpected)
- `HIF-non-compliant/invalid_direction_value.json`: incidences/0/direction: 'invalid_value' is not one of ['head', 'tail']
- `HIF-non-compliant/metadata_as_list.json`: metadata: [0, 1, 2] is not of type 'object'
- `HIF-non-compliant/missing_required_field_incidence.json`: incidences/0: 'node' is a required property
- `HIF-non-compliant/missing_required_fields_with_direction.json`: incidences/0: 'edge' is a required property
- `HIF-non-compliant/single_incidence_with_direction_not_in_enum.json`: incidences/0/direction: 'side' is not one of ['head', 'tail']
- `HIF-non-compliant/single_incidence_with_weight_as_string.json`: incidences/0/weight: 'hello' is not of type 'number'
