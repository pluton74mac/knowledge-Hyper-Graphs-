# EEG example records

Illustrative records in the v0 format. They show the shape, not real evidence: the one candidate
hyperedge cites a placeholder source and must not be accepted as is.

| File | Contents |
|---|---|
| `goals.jsonl` | The five goal hyperedges with unbound roles (`null`) |
| `nodes.jsonl` | Entity, value, source, evidence and agent-run nodes referenced by the examples |
| `hyperedges.jsonl` | One candidate hyperedge, the clinical sample-rate rule from the worked conflict |

Validate a hyperedge record against `../../schema/hyperedge.schema.json`; validate `relation` and
`bindings` against `../../schema/relation-types.yaml` (M1 delivers the validator).
