# Decisions

Each entry: what was decided, the alternative, why. Dated. Later entries can reverse earlier ones.

## 2026-09-21

**D1. The hypergraph is the source of truth; notes are rendered views.**
Alternative: keep Markdown notes primary and derive a hypergraph index for lint and retrieval.
Reason: the owner wants many agents contributing to one structure of facts, with a linting agent
resolving conflicts. That only works if writers submit facts, not pages. The derived-index option is
easier but leaves the page-merge problem in place.

**D2. Extraction is a separate pass after research, never done by the research agent inline.**
Alternative: research agents emit hyperedges as they write.
Reason: extraction quality is the weak link in every published system. A separate pass with its own
prompt and its own validation is the gate that keeps a bad run from corrupting the accepted graph.

**D3. Conflict policy v0: research first, then most specific, then most recent, escalate on low confidence.**
Alternative: most specific and most recent immediately, or owner decides everything.
Reason: many conflicts are a missing role, not a contradiction. Asking for one more round of evidence
before resolving catches those. The policy is configuration and is expected to evolve.

**D4. Conflicts the rules cannot settle go to a review queue for the owner.**
Reason: the owner wants the last word on genuine disputes, and a queue keeps the linter from
guessing.

**D5. First target corpus is the EEG device example, not the existing knowledge-hypergraph base.**
Alternative: extract the existing 108-note base into hyper-base.
Reason: the property to prove is that disciplines connect through goal hyperedges. The EEG example
is multi-discipline by construction and small. The existing base is single-discipline.

**D6. Walker is a policy over a code-owned traverser; the judgment model scores legal moves only.**
Alternative: the model generates the next query or walks freely.
Reason: closed choices with probabilities compose with beam search and cannot invent structure. A
general LLM runs behind the interface first; Jev is swapped in behind the same interface in M4.

**D7. v0 storage is JSONL files in git, with HIF export.**
Alternative: a hypergraph or property-graph database from day one.
Reason: scale is small, diffs are reviewable, and the format bake-off is a separate candidate project.

**D8. Project lives in `projects/hyper-base/` of the knowledge-hypergraph repo until its own repo exists.**
Reason: repo creation through the GitHub App failed with 403. The folder is self-contained and moves
with one `git subtree split`.

**D9. Name: hyper-base.**
Alternatives considered: hyperbase (an existing product name), hyperledge (too close to Hyperledger),
incidence. Reason: the owner's suggestion says what it is, and a GitHub rename is cheap if a better
name appears.
