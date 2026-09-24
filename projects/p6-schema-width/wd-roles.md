---
title: "wd-roles: role naming for Wikidata statements (P3a and P6)"
type: project
status: reviewed
created: 2026-09-24
updated: 2026-09-24
---

# wd-roles: role naming for Wikidata statements

The single naming P3a uses when it turns Wikidata statements into C1 records
(`khg-relation-schema/1.0.0`, [P2 DESIGN §2–§3](../p2-role-aware-hif/DESIGN.md)) and P6 uses when it builds
the schema hypergraphs it measures. Both record the version they used. The measurements behind it are in
[research/02-data-sources-and-naming.md](research/02-data-sources-and-naming.md) §3.

| Version | Date | Change |
|---|---|---|
| r0 | 2026-09-24 | Proposed by P6 (research report 02 §5) |
| **r1** | 2026-09-24 | Adopted by P3a with three amendments (rules 6a, 6b, 6c below), accepted by the director |

## Rules (r1)

1. **Relation id** = the property id, e.g. `P39`. The English label goes in the schema's `label`, and
   `{"wikidata": "P39"}` in `mappings`. Labels are never ids.
2. **Subject role** = `subject` in every relation: core, min 1, max 1, direction `tail`, and `primary.subject`.
3. **Main-value role** = the property id itself (the position in a P39 statement binds role `P39`): core,
   min 1, max 1, direction `head`, and `primary.object`. `somevalue` and `novalue` are allowed.
4. **Qualifier roles** = the qualifier's property id (`P580`, `P1365`, `P2937` …). One global role per
   property, whether it appears as a qualifier or as a main value elsewhere.
5. **Self-qualifier.** When a statement of property P carries P itself as a qualifier, the role is
   `P<id>:qualifier` (e.g. `P131:qualifier`), so each role is used once per relation (M002).
6. **Slot classes.**
   - `time`: P580 and P582. A relation that allows or uses either gets
     `time: {"model": "interval", "start": "P580", "end": "P582"}`, both as time usages with min 0, max 1.
     P585 point in time is always `qualifier`.
   - **6a (r1). Relations P580 and P582 get no time model.** Their P580 and P582 qualifiers are `qualifier`
     usages; the one that repeats the relation's own property takes the rule-5 form (`P580:qualifier`,
     `P582:qualifier`). Otherwise rule 3 (the main value is role `P580`) and the interval model (whose start
     is role `P580`) collide, and the schema fails M002 or M007.
   - **6b (r1). Duplicate time bounds.** A statement with two P580 values, or two P582 values, on a relation
     with the interval model is left out of the corpus and counted per relation in the datasheet. No value is
     picked silently.
   - **6c (r1). Rank reasons.** P2241 (reason for deprecated rank) goes to `rank_reason` only on a deprecated
     statement, and P7452 (reason for preferred rank) only on a preferred one. A reason on any other rank is a
     `meta` binding under its property id, and is counted in the datasheet. So `rank_reason` never holds a
     reason that contradicts the rank, and a mismatched reason keeps its property.
   - P1534 end cause becomes the built-in `khg:end_cause` on relations with the interval model, and `meta`
     otherwise.
   - `meta`: P8327, P13589, P1810, P14457, P1932, P4970, P813, P854, P248, P1065, P2960, P143, P4656, P887,
     P3452, P1683, P5017, P3680, P1310, P805, P2916, P6607, P9570, P7528.
   - `qualifier`: everything else, including P5102, P1480, P585, P1319, P1326, P8554, P8555, P12506, P518 and
     P3831.
7. **References** are evidence, not bindings. A source property that appears as a qualifier follows rule 6.
8. **Out of scope as relations**: properties that document or constrain other properties (instances of
   Q19820110, Q21504947 or Q64846109, e.g. P1855, P2302, P360, P4224); 57 on 2026-09-24.
9. **Counts P3a records**, per relation, over the whole dump and over the part kept: the qualifier properties
   used, in statements and in snaks, before and after slot classing; statements left out under 6b; mismatched
   rank reasons under 6c; self-qualified statements; the arity under wd-roles; and the naming version
   (`wd-roles r1`).

## What P6 takes from P3a

P6's observed schemas use P3a's exact qualifier counts from the 2026-09-22 dump when they are committed,
replacing the SQID estimates (report 02 §2). Until then the observed rows of the survey are labelled with the
SQID source and date. The declared schemas do not depend on P3a.

## Not part of the naming

C1 refuses a statement whose start is after its end (S009). P3a leaves such statements out and counts them.
