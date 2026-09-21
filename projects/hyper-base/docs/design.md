# hyper-base design

Status: draft v0, 2026-09-21. This is the formalisation of an idea developed in conversation. It
records what the system is, what it is not, and what would show that it works. Everything here is
open to revision; the decisions already taken are listed in [decisions.md](decisions.md).

## 1. Problem

The llm-wiki pattern (a folder of Markdown pages plus an index, read and written by an agent) works
well for straightforward information. Under iterative research use, where each run extends and
revises the base, it degrades with size. The observed symptoms:

- Later runs only know what is in the index. Re-ingesting the whole base each run stops being
  possible at some size.
- Pages that should link do not, because the writer did not know the other page existed.
- The same fact is stated in several pages, in different words, and drifts apart.
- One new fact can require rewriting many pages, and finding those pages requires reading all of them.
- Update time grows with the size of the base rather than with the size of the change.

All of these are one missing thing: the base holds no explicit record of which statements depend on
which facts. The index is a table of contents, not a dependency structure.

## 2. Thesis

Make the fact structure primary and the prose derived. Represent each fact as a hyperedge that binds
the entities it is about, the sources that support it, and the roles each plays. Then:

- **Retrieval is traversal.** A question seeds entities; the answer is a connected set of hyperedges
  around them, found by a walker, not by reading pages.
- **Lint is shape.** A dangling entity, an unbound role, a fact with no source, two facts with the
  same key and different values, a note citing a superseded fact: each is a pattern on the incidence
  structure and is found without reading prose.
- **Update is local.** A changed fact touches the hyperedges and rendered views incident to it. Cost
  scales with the neighbourhood, not with the base.
- **Many agents can write.** Because writers submit candidate hyperedges through a gate rather than
  editing shared pages, contributions from independent agents compose without merge conflicts in
  prose.

The n-ary structure earns its place where facts genuinely bind three or more things. In a research
base they do: a claim binds at least an assertion, a source, a status, and a run, and most
domain facts (a sample-rate rule, a safety limit, a treatment) bind several domain entities plus
conditions.

## 3. Data model

### 3.1 Nodes

| Kind | Examples | Identity |
|---|---|---|
| `entity` | `signal:scalp-eeg`, `component:instrumentation-amplifier`, `standard:iec-60601-1` | Namespaced slug. One canonical node per real-world thing; aliases recorded on the node. |
| `value` | `10-100 µV`, `250 Hz`, `>1 GΩ` | Literal with unit. Values are nodes so that facts can share them and lint can compare them. |
| `source` | a paper, a datasheet, a standard, a textbook chapter | Locator (DOI, URL, ISBN + section). Sources are nodes so that "which facts rest on this source" is a query. |
| `evidence` | a quoted passage or table cell from a source | Points at one source; carries the text. Attached to hyperedges, never cited on its own. |
| `agent-run` | `run:2026-09-21/physics-agent` | Who produced the candidate and when. |

### 3.2 Hyperedges

A hyperedge is one fact. It carries:

- `relation`: a relation type declared in the schema (§3.3).
- `bindings`: a map from role to node. Every role the schema declares as required must be bound
  for the hyperedge to be `accepted`. Unbound required roles are allowed only in `goal` hyperedges.
- `status`: `goal | candidate | accepted | superseded | retracted | rejected`.
- `evidence`: list of evidence node ids. Empty only for `goal`.
- `confidence`: 0 to 1, assigned by the linter, not by the writer.
- `created_by`: agent-run id. `created_at`: timestamp.
- `superseded_by`: hyperedge id, set when status becomes `superseded`.
- `valid_from`, `valid_to`: optional, only for relation types the schema marks `temporal`.
- `gloss`: one line of text for humans and for the walker's candidate list.

Hyperedges can bind other hyperedges (a `supports`, `contradicts`, or `derived_from` relation whose
roles are hyperedge ids). This is the metagraph layer and is where supersession history and
cross-discipline links live.

### 3.3 Schema

`schema/relation-types.yaml` declares each relation type with:

- `roles`: name, whether required, and the node kind or value unit allowed.
- `key`: the subset of roles that identifies *the thing the fact is about*. Two accepted hyperedges
  of the same relation with equal key bindings and different non-key bindings are a conflict. This
  is the field that makes conflict definable; without it duplicate and contradiction are the same
  pattern.
- `temporal`: whether valid-time applies.
- `owner_disciplines`: which agent briefs are expected to produce it. Advisory only.

The schema is versioned and edited by hand or through the review queue, never by a research agent.

### 3.4 Goal hyperedges

A project (an idea to develop) is expressed as a set of hyperedges with `status: goal` and some
required roles unbound. Unbound roles are the work queue. An agent's job is to bind roles with
evidence. The project is connected (§8) when every goal role is bound by an accepted hyperedge.

## 4. Pipeline

```
owner writes goal hyperedges + discipline briefs
        │
        ▼
[1] research agents (one per discipline, plus an integrator)
        │   evidence documents: prose + quoted passages + source locators
        ▼
[2] extraction pass (separate agent, separate prompt, runs after research)
        │   candidate hyperedges + evidence nodes + proposed entity nodes
        ▼
[3] candidate queue (append-only, on disk)
        │
        ▼
[4] linter
        │   structural checks → entity resolution → duplicate merge → conflict policy
        ├──► accepted graph
        └──► review queue (owner)
        │
        ▼
[5] views: rendered notes, unbound-role report, conflict report
        │
        └──► next round of briefs (write-back)
```

Rules that keep this safe with many writers:

- Research agents never write hyperedges. They write evidence documents.
- The extraction pass never writes to the accepted graph. It appends to the candidate queue.
- Only the linter writes to the accepted graph, and every write is one of: accept, merge into
  existing, supersede existing, reject, escalate.
- Every write is logged with the rule that produced it.

## 5. Linter

### 5.1 Structural lint (deterministic, no model)

- Candidate references a node that does not exist and is not proposed in the same batch: reject.
- Required role unbound on a non-goal candidate: reject.
- No evidence on a non-goal candidate: reject.
- Evidence node points at no source: reject.
- Value node without a unit where the role requires one: reject.
- Accepted entity with no incident accepted hyperedge: report as orphan.
- Accepted hyperedge whose evidence quotes a source marked retracted: report.

### 5.2 Entity resolution (model-assisted)

Proposed entity nodes are matched against existing nodes by alias, by embedding over label and
gloss, and by a judgment question ("same real-world thing?") over the shortlist. Matches merge, with
the new label added as alias. Non-matches become new nodes. Low-confidence matches go to review.

### 5.3 Duplicate merge

Two candidates, or a candidate and an accepted hyperedge, with the same relation, equal key
bindings, and equal non-key bindings (after value normalisation) are one fact. Merge: union the
evidence, keep the earlier id, log the merge.

### 5.4 Conflict policy v0

Same relation, equal key bindings, different non-key bindings. Ordered:

1. **Research first.** On first detection, do not resolve. Emit a research task to the discipline
   brief that owns the relation, asking for evidence that either reconciles the two (often a missing
   role, in which case the schema is extended and both survive as different facts) or settles them.
   Mark both hyperedges `disputed`.
2. **After one research round, most specific wins.** The hyperedge with more bound roles, or
   whose evidence names the narrower condition, is accepted. The other becomes `superseded` with
   `superseded_by` set.
3. **Then most recent source wins.** Ties on specificity are broken by source date.
4. **Low confidence escalates.** If the linter's confidence on steps 2 or 3 is below a threshold,
   both go to the review queue with the evidence side by side. The owner decides.

The owner has said this policy will evolve. It is a configuration, not a fixed part of the design.

## 6. Walker

The walker retrieves a subgraph for a question or a task. It follows the policy-over-traverser
pattern: code owns the graph and enumerates legal moves, a judgment model only scores them.

```
question / task
  → entity linking + embedding → seed nodes
  → loop:
        enumerate incident accepted hyperedges (graph code)
        pre-rank to top-k by embedding over gloss (k = 16 to 64)
        judgment model answers, in one call:
            next hyperedge?      choice over the k candidates
            enough evidence?     yes/no, conditioned on task type
            path still on task?  score 0 to 1
        beam update: expand top-b, drop paths below a log-probability cut-off
  → subgraph + evidence passages
  → separate generator writes the answer, or a template renders a view
```

The judgment interface is `state text in, typed answer out` (choice with probabilities, yes/no with
probability, score with distribution). M4 runs a general LLM behind it first, then TypeSafe's Jev
behind the same interface, and compares cost, latency and retrieval quality. Jev is a
choice/score/yes-no model with schema-locked outputs launched in September 2026; public write-ups
quote 70 to 500 ms per call ([Pydantic docs](https://pydantic.dev/docs/ai/models/typesafe/),
[Requesty](https://www.requesty.ai/blog/typesafe-jev-explained)). It cannot propose a node or a
relation, which is what we want from a walker.

The stop question carries the task type, because "enough to answer" differs from "enough to render
a note" and from "enough to bind this goal role".

The same judgment interface serves the linter for the "same thing?", "duplicate?", "contradicts?"
and "which source is more authoritative?" questions.

## 7. Supersession

Supersession is one fact replacing another fact about the same thing. Nothing is deleted. It
requires three things, and all three are in the model above:

- A **key** per relation type, so that "the same thing" is defined (§3.3).
- A **status lifecycle** with a pointer: `accepted → superseded`, `superseded_by` set.
- A **run stamp** on every hyperedge, so that "what did the base believe at run N" is answerable.

Two clocks exist. A fact can stop being true in the world (a standard is revised) or the base can
stop believing it (a better source arrived). v0 records only the second clock, via run stamps and
supersession. Valid-time intervals are enabled per relation type where the domain needs them, and
are absent elsewhere. The KB's memory note records that no published n-ary system carries
valid-time with supersession semantics; this project does not try to solve that in general, only to
use the minimal form.

Rendered views must show a superseded fact as superseded, with a link to its successor, wherever it
was cited. That is the property that fixes "one new fact rewrites many pages": the pages are views,
and the view logic handles it.

## 8. Termination: when the disciplines connect

A project run is complete when all of the following hold on the accepted graph:

1. Every required role of every goal hyperedge is bound.
2. Every binding is supported by at least one accepted hyperedge with evidence.
3. Every cross-discipline hyperedge (one whose bindings come from two or more discipline briefs)
   has no unresolved conflict.
4. The review queue is empty or contains only items the owner has deferred.

If a round produces no new bindings and the queue is empty, the run has stalled. The unbound-role
report says where.

An agent that produces facts binding nothing in the goal set is off task. The linter can see this in
the shape and reports it per agent-run.

## 9. Storage

v0: plain files in git.

- `graph/nodes.jsonl`, `graph/hyperedges.jsonl`, `graph/evidence.jsonl`: the accepted graph.
- `queue/candidates.jsonl`: append-only.
- `queue/review.jsonl`: items awaiting the owner.
- `runs/<date>/<agent>/`: evidence documents as written.
- `views/`: rendered notes, regenerated, not edited.

Export to HIF (with roles on incidence attributes, per candidate project P2) for analysis libraries.
Move to a database only when file scans become the bottleneck. The KB's format-recommendations note
supports this ordering for small graphs.

## 10. Evaluation

What would show that the thesis holds, measured on the EEG run and on an llm-wiki baseline built from
the same evidence documents:

| Measure | hyper-base | llm-wiki baseline |
|---|---|---|
| Update locality | hyperedges and views touched per changed fact | pages that mention the fact, found by grep |
| Duplication | facts merged by the linter per run | same claim in two or more pages, counted by hand on a sample |
| Dangling references | orphan report | broken or missing links |
| Conflict handling | conflicts detected, resolved by rule, escalated | contradictions found by hand on a sample |
| Retrieval | answer quality on 20 questions with known answers, subgraph size, walker calls | same questions, index-then-read |
| Ingestion cost | tokens per accepted hyperedge | tokens per page written |
| Connection | rounds to termination, roles left unbound | not defined |

## 11. Non-goals for v0

- Training or fine-tuning any model.
- Inductive completion (predicting missing hyperedges). Layer C of the composed stack is out of scope.
- A general bitemporal model. Valid-time is per relation type and opt-in.
- A database. Files first.
- A user interface beyond rendered Markdown and reports.
- Solving extraction quality in general. The gate limits the damage; it does not remove the problem.

## 12. Open questions

1. What is the right granularity of an evidence node: a sentence, a paragraph, a table row?
2. How should the schema be extended when a conflict turns out to be a missing role (the sample-rate
   case in the EEG example)? Automatically with review, or owner-only?
3. Should discipline agents see the accepted graph, or only the unbound-role report and their own
   brief? Less context is cheaper and reduces anchoring; more context reduces duplicates.
4. What confidence threshold sends a conflict to review, and does it depend on relation type?
5. When Jev is behind the judgment interface, does pre-ranking by embedding lose candidates that a
   general LLM would have picked? Measure in M4.
6. Does the walker need typed edges between hyperedges (the metagraph layer) to plan across
   disciplines, or is entity overlap enough?

## 13. Relation to the knowledge-hypergraph base

hyper-base implements layers B (living store), E (planner/walker) and G (write-back) of the composed
stack, with A (extraction) present but treated as a gated input. It is candidate project P7 pointed
at a research base instead of a conversational agent, and it uses P2's role-aware HIF as its export
format. It does not touch C (completion) or D (algebra).
