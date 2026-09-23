---
title: "Draft: the HIF issue proposing the role convention (DESIGN §12.3)"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# Draft: the HIF issue (W14; DESIGN §12.3)

**Nothing here has been filed.** The repository owner files it from their own account (the director's ruling 2 on
DESIGN §14). This file holds the text, ready to paste, and what to check first.

## For the owner

- **Where:** https://github.com/HIF-org/HIF-standard/issues/new
- **When:** first of the four upstream actions, after khg-contracts 1.0.0 is on PyPI ([RELEASE.md](RELEASE.md)),
  because the links point at the tag `khg-contracts-v1.0.0`. The fixture PR ([hif-fixture-pr.md](hif-fixture-pr.md))
  follows once the maintainers have answered, and the XGI and HyperNetX issues ([xgi-issue.md](xgi-issue.md),
  [hypernetx-issue.md](hypernetx-issue.md)) can go out the same day.
- **Attach** `tests/evidence/library-hif-evidence.json` from the tag. If GitHub refuses the upload, the permalink in
  the text is enough.
- **Check the links.** They assume the repository is public and the tag exists. If the repository is private,
  attach the five fixture files as well and drop the links.
- **Afterwards,** once the XGI and HyperNetX issues are filed, add a comment on this issue with their links, as
  its body announces.
- **Context** ([research/02-hif-standard.md](../research/02-hif-standard.md) §8, §9, checked 2026-09-23): no one
  outside the author group has filed an issue before; decisions are taken in the group's meetings; the last commit
  was on 2026-03-19. The P2 gate never depends on the answer (§12.3).
- **The khg bookkeeping stays out.** The issue proposes no `khg-*` key and no `hif-*` name (graft [J-std]).

## Title

A `role` convention for incidence attributes (no schema change), with compliant fixtures

## Body

Paste everything inside the fence.

````markdown
## Summary

HIF already lets an incidence say which role its node plays in its edge: `incidences[].attrs` is the place the paper
gives for "hyperedge-dependent nodal attributes". We would like to write down how to do this so that files and
readers agree. The proposal is a four-rule **role convention**. It needs **no schema change**: every file that
follows it is valid against `hif_schema_v0.1.0.json` as it is. We also offer five compliant fixtures in a follow-up
PR, and we ask one question about repeated incidences.

## Why

- **The paper's own example.** "{"edge": 1, "node": 3, "attrs": {"role": "PI"}} might indicate node 3's role as a
  PI on project 1" (Coll et al. 2025, *Network Science* 13, e21, p. 7; https://doi.org/10.1017/nws.2025.10018).
- **The repository's own compliant test.** `tests/test_files/HIF-compliant/single_incidence_with_attrs.json` holds
  `{"edge": "abcd", "node": 42, "attrs": {"role": "PI", "age": 42}}` (added in 6fe88e9).
- **The group's rule.** On #21 the group kept structural fields (node, edge, weight, direction) apart from everything
  else, which goes in `attrs`. #44 takes the same attribute-first route for temporal presence. A role convention
  follows that rule.
- **Our use.** We store n-ary facts (knowledge hypergraphs) as HIF, where each participant has a role:
  `regulates(regulator: TP53, target: TP53, context: HeLa)`, a flight route with ordered stops, a marriage with two
  spouses. Without a shared convention, a reader cannot tell our `role` from any other `role` key, and the libraries
  do not keep it (see "Evidence").

## The convention (`role-convention` 1.0.0)

1. **Every incidence of a role-carrying edge has `attrs.role`**, one non-empty string. An edge is role-carrying when
   at least one of its incidences has `attrs.role`.
2. **A node with k roles in one edge appears in k incidence records.** The records of one (edge, node) pair may
   differ in `direction`, and must differ in `role` or in `role-position`. Exact repeats of
   (edge, node, role, role-position) are malformed.
3. **`metadata["role-convention"] = "1.0.0"` declares the convention.** `metadata["role-vocabulary"]` is optional
   and maps each role to `{label?, ...}`.
4. **`attrs["role-position"]`**, an integer ≥ 1, orders the fillers of one role.

Any other key in `attrs` passes through. Nothing is added at the top level or at record level. Rule 2 is also how a
node gets into both the tail and the head of a directed edge, which the paper allows (p. 3-4) and a single
`direction` cannot say:

```json
{"network-type": "directed",
 "metadata": {"role-convention": "1.0.0"},
 "incidences": [
  {"edge": "reg-1", "node": "TP53", "direction": "tail", "attrs": {"role": "regulator"}},
  {"edge": "reg-1", "node": "TP53", "direction": "head", "attrs": {"role": "target"}},
  {"edge": "reg-1", "node": "HeLa", "direction": "tail", "attrs": {"role": "context"}}]}
```

Rule 4 is what makes a route expressible, with one airport at two positions:

```json
{"network-type": "undirected",
 "metadata": {"role-convention": "1.0.0"},
 "incidences": [
  {"edge": "route-1", "node": "AC", "attrs": {"role": "carrier"}},
  {"edge": "route-1", "node": "YYZ", "attrs": {"role": "stop", "role-position": 1}},
  {"edge": "route-1", "node": "YUL", "attrs": {"role": "stop", "role-position": 2}},
  {"edge": "route-1", "node": "YYZ", "attrs": {"role": "stop", "role-position": 3}}]}
```

**A reference check.** The four rules are the checks R001-R004 of the MIT-licensed Python package `khg-contracts`
(https://pypi.org/project/khg-contracts/): R001 a missing or non-string role on a role-carrying edge; R002 an exact
repeat of (edge, node, role, role-position); R003 a missing or unknown `metadata.role-convention`; R004 a
`role-position` that is not an integer ≥ 1. `khg-validate FILE --kind role-convention` runs the HIF schema, offline,
and then these four checks. The specification is §4.1 of our design:
https://github.com/pluton74mac/knowledge-Hyper-Graphs-/blob/khg-contracts-v1.0.0/projects/p2-role-aware-hif/DESIGN.md#41-two-layers-and-the-contested-choice

## One question: may `incidences` repeat an (edge, node) pair?

The formal model makes the incidence set I ⊆ V × E a *set* (p. 3). Yet `duplicated_nodes_edges.json` in
`tests/test_files/HIF-compliant/` repeats a pair, and its test says "Expect to pass unless uniqueness is enforced".
The convention needs repeated pairs, for a node with two roles and for a node in both the tail and the head. We would
like to ask:

- that the README say that `incidences` may repeat an (edge, node) pair, and that the records of one pair may differ
  in `direction` and in `attrs`;
- that readers keep every incidence record and round-trip `attrs`, unknown keys included.

## Evidence: what readers do with such files today

`library-hif-evidence.json` (attached; also at
https://github.com/pluton74mac/knowledge-Hyper-Graphs-/blob/khg-contracts-v1.0.0/tests/evidence/library-hif-evidence.json)
records the libraries' own HIF functions on four role-carrying files: XGI 0.10.2 `read_hif` then `write_hif`, and
HyperNetX 2.4.3 `from_hif` then `to_hif` (run offline, with HyperNetX's schema download served from the same schema
file). Records in and out:

| File | XGI | HyperNetX |
|---|---|---|
| `tail-head` above (3 records) | `DiHypergraph`; 3 → 3; 0 of 3 roles kept | 3 → 2: the repeated pair collapsed; `role-convention` metadata lost; `default_attrs` added; its own output cannot be read back and written again (`None`) |
| `ordered` above (4 records) | 4 → 3: the repeated pair collapsed; 0 of 4 roles kept | 4 → 3 |
| our 59-incidence test file, 52 incidences with a direction | `Hypergraph`; 59 → 56; 0 of 59 roles kept | `to_hif` returns `None` |
| its directed slice (52 records) | `DiHypergraph`; 52 → 51; 0 of 52 roles kept | 52 → 50; all 12 metadata keys lost; `None` on the second round |

We are raising these with the XGI and HyperNetX maintainers and will link those issues here. Our own loaders build
the library objects through their public constructors and round-trip all five fixture files exactly through both
libraries, so the convention works today; the question above is about what the standard promises.

## What we offer

A follow-up PR with five compliant fixtures and their tests, and no schema change:

- `role_convention_basic.json`: one role per incidence, with the optional `role-vocabulary`;
- `role_convention_two_roles.json`: one node with two roles in one edge;
- `role_convention_tail_head.json`: the tail-and-head file above;
- `role_convention_ordered.json`: the route above;
- `role_convention_undirected.json`: directions kept on some incidences of an undirected file, beside an edge without
  any.

All five pass the repository's test suite unchanged (35 tests, with the five new ones).

## For v2 (#51, #55)

Two asks, separate from this v1 convention:

- a record-level `role` on incidences, a structural field next to `direction` (as #21 discussed for an `index`);
- a version marker in data files, naming the HIF version a file follows.

We are happy to adjust the key names or the wording to whatever the group prefers.
````
