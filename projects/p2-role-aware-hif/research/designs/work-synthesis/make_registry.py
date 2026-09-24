"""Writes design-examples/error-codes.json: the stable code registry of the synthesised design."""
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1])

LAYERS = {
    "J": "strict JSON parse (stdlib json with hooks); runs on every input; a J finding stops later layers",
    "V": "version gate: reads format and profile ids and selects the schemas; a V finding stops later layers",
    "H": "the vendored HIF schema hif_schema_v0.1.0.json (blob e2105bb), unchanged; HIF inputs only",
    "R": "role-convention 1.0.0 (four rules), no khg requirements; HIF inputs, alone or inside the profile",
    "P": "the khg-hif/1.0.0 profile of HIF: khg-hif-1.0.0.schema.json (allOf the vendored schema) plus Python checks",
    "D": "decoding (HIF to C1), cross-record, container, history and store rules (Python)",
    "C": "the C1 record schema khg-record-1.0.0.schema.json (draft-07, x-khg-code annotations, if/then dispatch)",
    "S": "one record against its relation-type schema (Python)",
    "M": "relation-type schema documents: khg-relation-schema-1.0.0 plus Python checks",
    "Q": "C3 queue files: khg-queue-1.0.0 plus the state fold, key recomputation and replay (Python)",
    "I": "C4 items: khg-c4-items-0.1.0.schema.json (draft-07) plus the memory-gold check",
    "L": "lint findings; never make a file invalid (v1 ships only L008, the store's possible-overlap warning)",
    "F": "migration report entries (v1: the v0-sample migration)",
}
PIPELINES = {
    "c1": "J V C S D",
    "hif": "J V H R P D C S (D first runs as decoding; the cross-record D checks run after S)",
    "role-convention": "J H R",
    "relation-schema": "J V M",
    "queue": "J V Q C S D (C and S on payloads; S003 is a warning on candidates)",
    "c4": "J V I (embedded C1 records and values report C and S findings nested under I003)",
}
RULE = ("A finding's layer is the letter of its code. A validation step may emit another layer's code (decoding emits "
        "S016; the S pass emits D002). The first rejecting layer of an input is the earliest letter, in its kind's "
        "pipeline order, among its error findings. J and V findings stop later layers.")

E, W, I = "error", "warning", "info"
CODES = [
    # J
    ("KHG-J001", "J", E, "not JSON, empty input, or truncated", "B J001; A J001; C J-PARSE"),
    ("KHG-J002", "J", E, "byte-order mark or invalid UTF-8", "B J002; C J-ENCODING"),
    ("KHG-J003", "J", E, "duplicate object key", "B J003; A J002; C J-DUP-KEY"),
    ("KHG-J004", "J", E, "NaN or +/-Infinity", "B J004; A J003; C J-NAN"),
    ("KHG-J005", "J", E, "lone surrogate in a string", "B J005; A J004; C J-SURROGATE"),
    ("KHG-J006", "J", E, "integer outside +/-(2^53-1)", "A J005 (graft I12)"),
    ("KHG-J007", "J", E, "top level (or a JSONL line) is not an object", "C J-NOT-OBJECT"),
    # V
    ("KHG-V001", "V", E, "format or profile id unknown, a major version the reader does not support, or a minor newer "
                         "than the reader (writers stamp the lowest version whose features a document uses): khg-record, "
                         "khg-hif, khg-relation-schema, khg-queue, khg-c4-items", "B D009 (version part); A P002; C R-FORMAT"),
    # H
    ("KHG-H001", "H", E, "HIF: no incidences", "B H001; A H001"),
    ("KHG-H002", "H", E, "HIF: extra top-level key", "B H002; A H002"),
    ("KHG-H003", "H", E, "HIF: extra record-level key", "B H003; A H002"),
    ("KHG-H004", "H", E, "HIF: attrs or metadata not an object", "B H004"),
    ("KHG-H005", "H", E, "HIF: direction not head or tail", "B H005; A H004"),
    ("KHG-H006", "H", E, "HIF: record missing edge or node", "B H006; A H001"),
    ("KHG-H007", "H", E, "HIF: id of the wrong JSON type", "B H007; A H003"),
    ("KHG-H008", "H", E, "HIF: network-type outside the HIF enum", "B H008; A H004"),
    ("KHG-H009", "H", E, "HIF: another member of the wrong JSON type", "B H009"),
    # R: role-convention 1.0.0
    ("KHG-R001", "R", E, "an incidence of a role-carrying edge (an edge with at least one attrs.role) has no role, or "
                         "its role is not one non-empty string", "critique UPSTREAM; was P005 (role part) and P006"),
    ("KHG-R002", "R", E, "two incidence records repeat the same (edge, node, role, role-position)", "critique UPSTREAM; was P016 (exact duplicates)"),
    ("KHG-R003", "R", E, "metadata role-convention missing or not a known version (1.0.0)", "critique UPSTREAM; was P001 (role part)"),
    ("KHG-R004", "R", E, "role-position not an integer >= 1", "critique UPSTREAM; was P015"),
    # P
    ("KHG-P001", "P", E, "a khg-hif declaration missing (hif-schema, hif-schema-sha256, khg-profile, khg-record, "
                         "khg-schema, khg-schema-sha256, khg-document-id, khg-literal-nodes), or no metadata", "B P001; A P001"),
    ("KHG-P002", "P", E, "non-string id (the profile allows string ids only, F10)", "B P002; A P003"),
    ("KHG-P003", "P", E, "id grammar: empty, control character, white space, over 512 code points (518 for a _:ref: node)",
     "B P003; A P003; critique GL-16"),
    ("KHG-P004", "P", E, "reserved _: prefix misused: an entity id using it, or a derived node id without its kind's "
                         "prefix (_:lit:, _:litb:, _:sv:, _:nv:, _:var:, _:ref:)", "B P004"),
    ("KHG-P005", "P", E, "incidence without attrs, role or khg-bid, or a malformed khg-bid", "B P005; A P004"),
    ("KHG-P006", "P", E, "reserved: moved to KHG-R001 before 1.0", "B P006; A P004"),
    ("KHG-P007", "P", E, "network-type asc (refused by the profile, R03 D8)", "B P007; A P006"),
    ("KHG-P008", "P", E, "forbidden metadata key: default_attrs, or an unknown khg-* key", "B P008; A P007"),
    ("KHG-P009", "P", E, "declaration value malformed or not the pinned one (hif-schema, hif-schema-sha256, "
                         "khg-literal-nodes)", "B P009; A P001"),
    ("KHG-P010", "P", E, "directed document with an incidence lacking direction", "B P010; A P005"),
    ("KHG-P011", "P", E, "network-type contradicts the direction rule (directed iff every incidence has a direction)", "synthesis (replaces B P011)"),
    ("KHG-P012", "P", E, "edge without attrs, relation or khg-status, or a malformed khg-* edge attribute", "B P012; A P009"),
    ("KHG-P013", "P", E, "node without attrs or khg-kind, unknown khg-kind, or the kind's payload missing "
                         "(khg-literal, khg-unbound, khg-ref)", "B P013; A P008"),
    ("KHG-P014", "P", E, "unknown khg-* incidence attrs key (khg-bid and khg-extensions are allowed), or the legacy "
                         "key roles next to role", "B P014; critique GL-07"),
    ("KHG-P015", "P", E, "reserved: moved to KHG-R004 before 1.0", "B P015"),
    ("KHG-P016", "P", E, "two incidence records of one edge share a khg-bid", "rulings; B S025"),
    ("KHG-P017", "P", E, "khg-external fact reference outside a slice, or an external reference to a fact the file holds",
     "critique CONS-14"),
    # D
    ("KHG-D001", "D", E, "node, edge or record declared twice (same id, or same id and version)", "B D001; A P011, S026"),
    ("KHG-D002", "D", E, "unresolved reference: incidence to an undeclared node, entity absent from a complete document "
                         "or from the store, fact reference to a missing hyperedge. Vocabulary ids (units, globes, "
                         "rank reasons, schema units) are never references", "B D002; A P012, S013; C C-ENTITY-REF"),
    ("KHG-D003", "D", E, "incidence names an undeclared edge", "B D003; A P012"),
    ("KHG-D004", "D", E, "reserved", "B D004"),
    ("KHG-D005", "D", E, "derived HIF node id does not match its value, (record id, bid) or reference", "B D005; A P010; C P-LITERAL-ID"),
    ("KHG-D006", "D", E, "reserved", "B D006"),
    ("KHG-D007", "D", E, "one id names both an entity and a hyperedge", "B D007; C C-DUP-ID"),
    ("KHG-D008", "D", E, "nesting cycle among fact references", "B D008; A S014; C C-NESTING-CYCLE"),
    ("KHG-D009", "D", E, "relation-type schema id, version or sha256 does not match the one declared (container header, "
                         "HIF metadata, queue header), or no schema supplied and none inlined", "B D009; C C-SCHEMA-REF"),
    ("KHG-D010", "D", E, "lifecycle pointer inconsistent: status_ref dangling, of the wrong relation, or not naming the "
                         "record; a fact bound by an asserted khg:supersedes (as superseded) or khg:retracts record "
                         "without that status", "B D010; A S022; C C-SUPERSESSION"),
    ("KHG-D011", "D", E, "supersession constraint: a superseding fact not asserted when the supersede event runs; "
                         "correction across relations or key digests; duplicate with different content keys; refinement "
                         "where the superseding fact does not refine the superseded one (checked at the event, on a put "
                         "of a new version of a bound fact, and on containers)", "B D011; A S023; critique SEM-11, SEM-20"),
    ("KHG-D012", "D", E, "supersession cycle", "B D012"),
    ("KHG-D013", "D", E, "version rule: a new version is not a refinement of the current one, changes the relation, "
                         "mutates earlier evidence (event_hash included), or breaks the entity rule (types only grow; "
                         "redirect_to is set once)", "B D013; A S031; critique CONS-28"),
    ("KHG-D014", "D", E, "status transition not in the transition table: put creating a record in a status other than "
                         "asserted, quoted or goal; put writing a lifecycle record; put changing the status of an existing "
                         "id; an event outside the table; consecutive versions of a history container", "B D014; A S030; C TransitionError"),
    ("KHG-D015", "D", E, "a stored derived block disagrees with recomputation", "B D015; A M41; C R-DERIVED"),
    ("KHG-D016", "D", E, "key invariant violated (raised as KeyCollision; info.collisions lists every colliding record "
                         "with its policy and, per conflict, shape, class and action)", "B D016; A S029; C C-KEY-COLLISION; critique CONS-13"),
    ("KHG-D017", "D", E, "status candidate outside a queue payload", "B D017; A S028; C C-STATUS-CANDIDATE"),
    ("KHG-D018", "D", E, "transaction time not after the store's latest (put or apply at, load); in a history container, "
                         "a version not after the previous version of its id, or after the header's as_at",
     "A S032; C C-TX-ORDER; critique SEM-14"),
    ("KHG-D019", "D", E, "store: optimistic-concurrency expectation not met (expect)", "B ConcurrencyError"),
    ("KHG-D020", "D", E, "a value names an entity that has redirect_to (redirects are rewritten in 1.2)", "critique SEM-16"),
    # C
    ("KHG-C001", "C", E, "value not exactly one kind (entity, literal, fact, special, unbound)", "B C001; A P014; C R-VALUE"),
    ("KHG-C002", "C", E, "enum violation (kind, status, rank, visibility, datatype, direction, evidence type or mode, "
                         "selector type, content)", "B C002; C R-STATUS"),
    ("KHG-C003", "C", E, "confidence not {value, scale, scorer?}", "B C003; A M39"),
    ("KHG-C004", "C", E, "literal structure: unit, precision range, calendar, bound pairs, lexical pattern", "B C004; A P015; C R-LIT-*"),
    ("KHG-C005", "C", E, "unbound value in a hyperedge whose status is not goal", "B C005; A S008; C S-UNBOUND"),
    ("KHG-C006", "C", E, "status disputed, superseded or retracted without status_ref, or status_ref with any other status",
     "B C006; A P016; critique SEM-10"),
    ("KHG-C007", "C", E, "evidence structure: extracted without doc_sha256, activity or selectors; selectors without "
                         "doc_sha256; inferred without inference; inference.from empty unless rule is model and activity "
                         "names model and model_version; malformed selector", "B C007; A P017; C R-EVIDENCE-DOC-HASH; critique CONS-29"),
    ("KHG-C008", "C", E, "rank deprecated without a rank_reason list (import writes [\"unspecified\"] when the source gives none)",
     "B C008; critique CONS-22"),
    ("KHG-C009", "C", E, "unknown field", "B C009; A P018"),
    ("KHG-C010", "C", E, "required field missing, wrong JSON type or out of range (includes a retraction event without "
                         "its record id)", "B C010"),
    ("KHG-C011", "C", E, "identifier, bid, timestamp, hash, version or extension key not in its lexical form; a JSON "
                         "number where C1 requires a decimal string; an as_of instant outside [+-]YYYY-MM-DDThh:mm:ssZ",
     "B C011; C R-ID; critique CONS-04"),
    ("KHG-C012", "C", E, "field allowed only on some records: reason or note outside a lifecycle record (relation khg:*), "
                         "reason missing on one; goal outside status goal", "synthesis"),
    # S
    ("KHG-S001", "S", E, "relation not declared", "B S001; A S001; C S-RELATION"),
    ("KHG-S002", "S", E, "role not allowed for the relation", "B S002; A S002; C S-ROLE"),
    ("KHG-S003", "S", E, "required role missing (error for asserted, disputed, superseded, retracted, quoted; warning for "
                         "candidates)", "B S003; A S003; C S-ROLE-MIN"),
    ("KHG-S004", "S", E, "role bound more often than max", "B S004; A S004; C S-ROLE-MAX"),
    ("KHG-S005", "S", E, "filler kind, entity type, datatype or special value not allowed (includes a fact reference "
                         "where no fact is accepted); run only on resolved entities", "B S005; A S005, S006, S015; C S-FILLER, S-NESTING"),
    ("KHG-S006", "S", E, "literal value out of range for its lexical form: calendar date, components below the precision, "
                         "year 0, a date before 1583 without calendar", "B S006; A S007; C R-LIT-DATE; critique CONS-01, CONS-12"),
    ("KHG-S007", "S", E, "hyperedge with no bindings", "B S007; A P014; C S-NO-BINDINGS"),
    ("KHG-S008", "S", E, "reserved (merged into S005)", "B S008"),
    ("KHG-S009", "S", E, "possible validity empty (start window not before end window)", "B S009; A S020; C R-VALID-TIME"),
    ("KHG-S010", "S", E, "confidence scale undeclared or value outside the scale", "B S010; A S021; C S-CONFIDENCE"),
    ("KHG-S011", "S", E, "asserted fact without supporting (non-negated) evidence", "B S011; A S016; C S-EVIDENCE-MISSING"),
    ("KHG-S012", "S", E, "reserved", "B S012"),
    ("KHG-S013", "S", E, "novalue together with another filler of the same role", "B S013; A S009; C S-NOVALUE-MIXED"),
    ("KHG-S014", "S", E, "duplicate filler in an unordered role, or two somevalue fillers of one role", "B S014; A S012; C S-DUP-BINDING"),
    ("KHG-S015", "S", E, "positions: missing on an ordered role, present on an unordered one, or not contiguous 1..n", "B S015; A S010; C S-POSITION"),
    ("KHG-S016", "S", E, "direction contradicts the role usage's declared direction", "B S016; A S011; C S-DIRECTION"),
    ("KHG-S018", "S", E, "goal omits a required role instead of leaving it unbound", "B S018"),
    ("KHG-S019", "S", E, "one unbound variable used twice in a goal", "B S019"),
    ("KHG-S020", "S", E, "id or string not in Unicode NFC", "B S020; A S027; C R-ID-NFC"),
    ("KHG-S021", "S", E, "span empty or reversed, or quote differs from text[start:end] (code points, NFC; needs the "
                         "document text)", "B S021; A S018; C R-SELECTOR-SPAN"),
    ("KHG-S022", "S", E, "evidence supports an unknown bid", "B S022; A S017; C R-EVIDENCE-REF"),
    ("KHG-S023", "S", E, "literal below the usage's precision_min, or a unit not allowed", "B S023"),
    ("KHG-S024", "S", E, "co-occurrence constraint violated (severity from the schema: error or warning)", "B S024; C S-CONSTRAINT"),
    ("KHG-S025", "S", E, "duplicate bid in one hyperedge", "B S025; C R-DUP-BID"),
    ("KHG-S026", "S", E, "lifecycle reason outside its relation's reason list", "synthesis (A M53)"),
    # M
    ("KHG-M001", "M", E, "relation with no roles", "B M001; A D001; C D-NO-ROLES"),
    ("KHG-M002", "M", E, "role used twice in one relation", "B M002; C D-DUP-USAGE"),
    ("KHG-M003", "M", E, "bad key: role not used by the relation, or a time/meta-slot key role", "B M003; A D003; C D-KEY"),
    ("KHG-M004", "M", E, "schema version not semver", "B M004; C D-SEMVER"),
    ("KHG-M005", "M", E, "unknown entity type or relation in a filler", "B M005; A D002; C D-TYPE"),
    ("KHG-M006", "M", E, "unknown datatype", "B M006; A D001"),
    ("KHG-M007", "M", E, "bad time model or time-slot declaration (model outside interval, invariant, timeless; max != 1; "
                         "a filler other than one time literal; start/end not time-slot usages)", "B M007; critique SEM-15"),
    ("KHG-M008", "M", E, "user schema uses the reserved khg: namespace", "B M008; A D006"),
    ("KHG-M009", "M", E, "usage names a role missing from the global vocabulary", "B M009; C D-ROLE-UNDECLARED"),
    ("KHG-M010", "M", E, "max < min", "B M010; A D004; C D-CARDINALITY"),
    ("KHG-M011", "M", E, "temporal key on a relation without an interval time model", "B M011"),
    ("KHG-M012", "M", E, "primary does not name two core usages with max 1", "B M012; C D-PRIMARY"),
    ("KHG-M013", "M", E, "duplicate relation, role or entity-type id", "B M013"),
    ("KHG-M014", "M", E, "complete on a role with min 0", "B M014"),
    ("KHG-M015", "M", E, "other structural violation of a schema document (including a constraint severity outside error "
                         "and warning, and relation kind rule before 1.1)", "B M015; C D-SCHEMA; critique GL-01"),
    ("KHG-M016", "M", E, "entity-type parents cycle or unknown parent", "C D-TYPE"),
    ("KHG-M017", "M", E, "on_collision supersede on a temporal key (a succession is not a belief revision)", "critique SEM-04"),
    # Q
    ("KHG-Q001", "Q", E, "hyperedge item lacks extraction fields (run.run_id, run.order_id, run.position, submitted_by, "
                         "doc) or evidence", "B Q001; A S019; C Q-PAYLOAD, Q-RUN"),
    ("KHG-Q002", "Q", E, "payload status not candidate, or payload id not cand:<queue_id>.<seq>", "B Q002; A Q001; C Q-PAYLOAD"),
    ("KHG-Q003", "Q", E, "unknown line kind, item kind (v1: hyperedge) or log action (v1: lint, accept, reject, flag, "
                         "verdict, withdraw)", "B Q003; A Q001; C Q-LOG-ACTION"),
    ("KHG-Q004", "Q", E, "lint entry without rule_set, findings or outcome", "B Q004; C Q-SCHEMA"),
    ("KHG-Q005", "Q", E, "log entry does not follow the state fold (wrong state_before, forbidden move, decision after a "
                         "terminal state, accept with an open error finding)", "B Q005; A Q005, Q006; C Q-TRANSITION"),
    ("KHG-Q006", "Q", E, "replay mismatch: the recomputed decision_hash or the written [id, version] differs", "B Q006"),
    ("KHG-Q007", "Q", E, "log entry names a missing item or a parent that is not the item's previous entry", "B Q007; A Q004; C Q-LOG-TARGET"),
    ("KHG-Q008", "Q", E, "other structural violation of a queue file (header missing or repeated, verdict other without "
                         "note, ...)", "B Q008; A Q002; C Q-SCHEMA"),
    ("KHG-Q009", "Q", E, "extracted evidence does not point at the item's doc (doc_id or doc_sha256)", "C Q-DOC-HASH"),
    ("KHG-Q010", "Q", E, "item keys or an evidence event_hash disagree with recomputation from the payload", "A Q003; critique SEM-12"),
    ("KHG-Q011", "Q", E, "a payload names an entity that neither item.entities, the queue's base nor the linter's store "
                         "resolves", "critique CONS-10"),
    ("KHG-Q012", "Q", E, "the base supplied for replay or lint does not match the header's base {document_id, sha256}",
     "critique G3-ACCEPT-REPLAY"),
    # I
    ("KHG-I001", "I", E, "unknown C4 item kind", "C I-*"),
    ("KHG-I002", "I", E, "C4 item structure (draft schema) violated", "C I-*"),
    ("KHG-I003", "I", E, "embedded C1 record or value invalid (the C, S or D finding is attached as nested)", "C I-*"),
    ("KHG-I004", "I", E, "memory question without its stale_values or future_values array (mandatory, R05 D-C5-15)", "R05 §5.5"),
    ("KHG-I005", "I", E, "memory question gold disagrees with derive_memory_gold replayed from its trace", "B C5-E001"),
    # L (v1: only the store's possible-overlap warning)
    ("KHG-L008", "L", W, "only a possible (not definite) overlap on a temporal key (put receipts, validate_container)", "B L-I-008"),
    # F (v1: the v0-sample migration)
    ("KHG-F006", "F", I, "record weight kept as extensions hif:weight, never read as confidence", "B IMPORT-I01"),
    ("KHG-F015", "F", I, "migration: stored arity checked against the C1 rule and dropped", "B MIGRATE-I02"),
    ("KHG-F016", "F", I, "migration: metadata conventions/schema replaced by the declaration block", "B MIGRATE-I01"),
    ("KHG-F017", "F", W, "migration: valid-from turned into a start_time binding under a generated interval time model", "B MIGRATE-W01"),
]
RESERVED = {"KHG-D004", "KHG-D006", "KHG-S008", "KHG-S012", "KHG-P006", "KHG-P015"}

# Planned codes: provisional ids of later versions; NOT registered in 1.0 (critique SCOPE-F13). They may change
# before the version that ships them registers them.
PLANNED = [
    ("KHG-S017", "S", E, "rule relation: a binding without direction, or tail and head share a value", "1.1 (rule relations)"),
    ("KHG-L001", "L", I, "candidate duplicates a stored fact: propose merge (add evidence)", "1.1 (identity lints)"),
    ("KHG-L002", "L", I, "candidate refines a stored fact: propose merge (new version of the target)", "1.1 (identity lints)"),
    ("KHG-L003", "L", I, "candidate generalises a stored fact: propose merge (evidence appended, supports mapped)", "1.1 (identity lints)"),
    ("KHG-L004", "L", W, "ambiguous: two or more stored targets of one class", "1.1 (identity lints)"),
    ("KHG-L005", "L", W, "key collision with a distinct current fact: propose the declared policy's action", "1.1 (identity lints)"),
    ("KHG-L006", "L", W, "negation conflict: propose dispute (wins over L005 on the same pair)", "1.1 (identity lints)"),
    ("KHG-L007", "L", W, "candidate matches a superseded or retracted fact; a quoted match proposes quoted to asserted", "1.1 (identity lints)"),
    ("KHG-L009", "L", I, "the same stored event_hash already reached the store", "1.1 (identity lints)"),
    ("KHG-L101", "L", I, "evidence coverage below 1", "1.1 (quality lints)"),
    ("KHG-L102", "L", I, "incomplete key: exempt from collisions", "1.1 (quality lints)"),
    ("KHG-L103", "L", W, "a role that looks like provenance", "1.1 (quality lints)"),
    ("KHG-L104", "L", W, "a filler added to a repeated core role of a dated fact (a later joiner is end_validity plus a new fact)", "1.1 (quality lints)"),
    ("KHG-L105", "L", I, "arity outlier for the relation", "1.1 (quality lints)"),
    ("KHG-L106", "L", W, "a quoted fact that no fact references", "1.1 (quality lints)"),
    ("KHG-L107", "L", W, "an attrs key named weight (HyperNetX promotes it)", "1.1 (quality lints)"),
    ("KHG-L108", "L", I, "one node in several roles of one hyperedge", "1.1 (quality lints)"),
    ("KHG-L110", "L", W, "a key literal refines or overlaps another key literal of the same relation", "1.1 (critique SEM-13)"),
    ("KHG-F001", "F", I, "integer id converted to its decimal string", "1.1 (foreign import)"),
    ("KHG-F002", "F", E, "integer id collides with an equal string id", "1.1 (foreign import)"),
    ("KHG-F003", "F", W, "list-valued role expanded to one binding per role", "1.1 (foreign import)"),
    ("KHG-F004", "F", W, "incidence without role: role member assigned", "1.1 (foreign import)"),
    ("KHG-F005", "F", W, "edge without relation: relation untyped assigned", "1.1 (foreign import)"),
    ("KHG-F007", "F", W, "attrs key collides with a profile key: renamed <key>@hif", "1.1 (foreign import)"),
    ("KHG-F008", "F", W, "metadata default_attrs renamed default_attrs@hif", "1.1 (foreign import)"),
    ("KHG-F009", "F", W, "empty HIF edge reported and not imported", "1.1 (foreign import)"),
    ("KHG-F010", "F", W, "edge id equals a node id: edge remapped to hif-edge:<id>", "1.1 (foreign import)"),
    ("KHG-F011", "F", E, "directed file with an incidence lacking direction", "1.1 (foreign import)"),
    ("KHG-F012", "F", E, "network-type asc refused", "1.1 (foreign import)"),
    ("KHG-F013", "F", E, "duplicate node or edge declarations refused", "1.1 (foreign import)"),
    ("KHG-F014", "F", E, "id not in NFC refused", "1.1 (foreign import)"),
]

reg = {"format": "khg-codes/1.0.0",
       "rule": "codes are stable across minor versions; a new check gets a new code; a code is never reused or "
               "renumbered; messages are not part of the contract; reserved codes are never emitted",
       "layer_rule": RULE, "layers": LAYERS, "pipelines": PIPELINES,
       "codes": [dict(code=c, layer=l, severity=s, status="reserved" if c in RESERVED else "active", meaning=m, merges=src)
                 for c, l, s, m, src in CODES],
       "planned": [dict(code=c, layer=l, severity=s, meaning=m, version=v) for c, l, s, m, v in PLANNED]}
assert len({c[0] for c in CODES}) == len(CODES)
assert not {c[0] for c in CODES} & {c[0] for c in PLANNED}
(OUT / "error-codes.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
act = [c for c in reg["codes"] if c["status"] == "active"]
print(len(CODES), "registered codes,", len(act), "active,", len(RESERVED), "reserved,", len(PLANNED), "planned (not registered)")
