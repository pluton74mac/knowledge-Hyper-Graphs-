# First target: an EEG device that spans four disciplines

The device idea is not written as a note. It is a set of goal hyperedges with unbound roles. Four
discipline agents and one integrator bind the roles with evidence until the termination criterion
in [design.md](design.md) §8 holds. This document is the owner-facing brief: the goals, the
disciplines, what each is expected to contribute, the cross-discipline facts that make the project
connect, and one worked conflict.

Everything below is a sketch to be replaced by evidence during the run. Values given are the
textbook ranges the owner and the assistant expect to find; none is cited yet and none should be
accepted into the graph without a source.

## 1. Goal hyperedges

```
measures      (device: EEG-1, signal: ?, band: ?, amplitude_range: ?, sensor: ?)
acquires      (device: EEG-1, sensor: ?, front_end: ?, sample_rate: ?, resolution: ?)
rejects       (device: EEG-1, interference: ?, mechanism: ?, required_attenuation: ?)
safe_for      (device: EEG-1, population: ?, standard: ?, leakage_limit: ?)
places        (device: EEG-1, electrode_scheme: ?, channel_count: ?)
```

Machine-readable form: [`../examples/eeg/goals.jsonl`](../examples/eeg/goals.jsonl).

## 2. Discipline briefs

Each agent receives the goal set, its own brief, the unbound-role report, and the current conflict
report. It writes evidence documents, not hyperedges.

| Brief | Expected to bind | Expected facts (to be sourced) |
|---|---|---|
| Neuroscience and medicine | `signal`, `band`, `amplitude_range`, `electrode_scheme`, `population` | Scalp EEG arises from summed postsynaptic potentials of cortical pyramidal neurons, not action potentials. Scalp amplitude roughly 10 to 100 µV. Clinical bands delta, theta, alpha, beta, gamma with their frequency ranges. The 10-20 electrode system and its extensions. Clinical versus research use cases. |
| Physiology and biology | `sensor` (skin side), impedance conditions, artifact sources | Skull conductivity far below scalp and cerebrospinal fluid, so scalp potentials are spatially blurred. Skin-electrode impedance depends on preparation: gel versus dry, abrasion, hair. Sweat, eye movement, muscle and pulse produce artifacts with known spectral signatures. |
| Physics | `mechanism`, `interference`, the sampling rule | Quasi-static approximation of Maxwell's equations justifies volume-conduction models. Mains at 50 or 60 Hz couples capacitively through the body. Nyquist bounds the sample rate by the highest band of interest. Shielding and cable geometry. |
| Electronics | `sensor` (electrode side), `front_end`, `sample_rate`, `resolution`, `required_attenuation`, `leakage_limit` | Instrumentation amplifier with high common-mode rejection ratio. Driven-right-leg circuit to lower common-mode voltage. Delta-sigma ADC, 24-bit typical. Input-referred noise below 1 µV rms. Input impedance above 1 GΩ. Patient isolation and leakage limits per IEC 60601-1 and 60601-2-26. |
| Integrator | none directly | Reads only the cross-discipline report. Proposes hyperedges that bind entities from two or more briefs, and flags goal roles that no brief can bind alone. |

## 3. Cross-discipline hyperedges

These are the facts no single brief owns. They are the point of the project. Expected shape:

```
snr_constraint   (signal_amplitude: 10-100 µV       [medicine],
                  amplifier_noise:  <1 µV rms        [electronics],
                  required_ratio:   >20 dB,
                  evidence: ...)

sample_rate_rule (band_of_interest: gamma to 100 Hz  [medicine],
                  rule:             Nyquist          [physics],
                  minimum_rate:     250 Hz,
                  margin_rate:      500 Hz,
                  use_case:         clinical)

interference_path(source:           mains 50/60 Hz   [physics],
                  coupling:         capacitive via body [physics],
                  countermeasure:   CMRR + driven right leg [electronics],
                  residual_target:  ...)

impedance_budget (skin_prep:        gel              [physiology],
                  electrode_impedance: ~5 kΩ         [physiology],
                  input_impedance_needed: >1 GΩ      [electronics],
                  ratio_rule:       ...)
```

The integrator's stop condition is that every goal role is bound and each of these has no
unresolved conflict.

## 4. A worked conflict: the sample rate

Round 1. The medicine agent's evidence yields `sample_rate_rule(band: gamma ≤100 Hz, minimum_rate:
250 Hz)`. A physics or research-oriented source yields `sample_rate_rule(band: high gamma ≤500 Hz,
minimum_rate: 1000 Hz)`. If the schema's key for `sample_rate_rule` were `{band_of_interest}` alone,
these are two different facts and there is no conflict. If the key omitted `band_of_interest`, they
are a contradiction.

This is the case the conflict policy's "research first" step exists for. The linter emits a research
task: "two sample-rate rules with different values; is there a condition that separates them?" The
round-2 evidence shows the condition is `use_case` (clinical versus high-gamma research). The schema
gains a `use_case` role on `sample_rate_rule`, both hyperedges survive with it bound, and the goal
hyperedge `acquires` binds `sample_rate` to whichever use case the owner's goal declares.

A binary knowledge graph would have stored two contradictory `EEG —recommended_sample_rate→` edges.
The n-ary form stores two compatible facts. This is the concrete reason arity matters for this
project.

## 5. What a run should produce

- An accepted graph in `graph/` with every goal role bound.
- A rendered view per discipline and one integrated view for the device, regenerated from the graph.
- A report of conflicts detected, how each was resolved, and which went to review.
- Counts for the evaluation table in design.md §10.

## 6. Evidence rules for this run

- Prefer standards, textbooks and datasheets over blog posts.
- Every value node needs a unit and a source.
- A range is one value node (`10-100 µV`), not two.
- Quote the passage that supports the fact as the evidence node. No paraphrase in evidence.
