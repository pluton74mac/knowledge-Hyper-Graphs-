"""W5: keys, the key invariant, L008 and the ``KeyCollision`` info (DESIGN §2.5, §2.6).

The §2.5 action table row by row, classes and shapes on the fixture, the invariant judged per instant on definite
windows, the possible-overlap warning, and the collision info that the S-KEY scenarios expect, recomputed from their
records with ``record.keys.collisions`` (the store of W8 raises it).
"""
from __future__ import annotations

import copy
import itertools
import random

import pytest

from khg_contracts import data
from khg_contracts.errors import KeyCollision
from khg_contracts.record import bounds, key_digest, keys, lifecycle
from khg_contracts.record.keys import Violation
from khg_contracts.schema import Schema, load_schema

SCHEMA_DOC = data.load_json("fixture/fixture.relation-schema.json")
S = load_schema(SCHEMA_DOC)
C1 = data.load_json("fixture/fixture.c1.json")
FIX = {r["id"]: r for r in C1["records"]}
ENTITIES = [r for r in C1["records"] if r["kind"] == "entity"]
KD_POSITION = "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96"
KD_MARIA = "sha256:951a7bba11cca1f6c84ede16cd78c9502d08b7ab45060ff462b2ba4f0eea045c"


def T(time: str, precision: int = 11) -> dict:
    return {"literal": {"datatype": "time", "time": time, "precision": precision}}


def fact(fid: str, new_id: str | None = None, *, drop=(), rank=None, **values) -> dict:
    """A fixture fact, optionally renamed, with bindings dropped or their values replaced (by bid)."""
    f = copy.deepcopy(FIX[fid])
    if new_id:
        f["id"] = new_id
    f["bindings"] = [b for b in f["bindings"] if b["bid"] not in drop]
    for b in f["bindings"]:
        if b["bid"] in values:
            b["value"] = values[b["bid"]]
    for e in f.get("evidence", []):
        e["supports"] = [x for x in e.get("supports", []) if x not in drop]
    if rank is not None:
        f["rank"] = rank
        f.pop("rank_reason", None)
    return f


# ------------------------------------------------------------------------------------------------ scenario records


def resolve(x):
    """A scenario record reference (``khg-scenario/1.0.0``: ``@id``, ``@entities``, or ``{"@": id, set, drop,
    set_binding, drop_bindings, set_evidence, add_evidence}``), as the conformance runner resolves it."""
    if isinstance(x, str) and x.startswith("@"):
        return copy.deepcopy(ENTITIES) if x == "@entities" else copy.deepcopy(FIX[x[1:]])
    if isinstance(x, dict) and "@" in x:
        r = resolve("@" + x["@"])
        r.update(copy.deepcopy(x.get("set", {})))
        for k in x.get("drop", []):
            r.pop(k, None)
        by_bid = {b["bid"]: b for b in r.get("bindings", [])}
        for bid, value in x.get("set_binding", {}).items():
            by_bid[bid]["value"] = copy.deepcopy(value)
        for bid in x.get("drop_bindings", []):
            r["bindings"] = [b for b in r["bindings"] if b["bid"] != bid]
            for e in r.get("evidence", []):
                if "supports" in e:
                    e["supports"] = [s for s in e["supports"] if s != bid]
        by_eid = {e["id"]: e for e in r.get("evidence", [])}
        for eid, fields in x.get("set_evidence", {}).items():
            by_eid[eid].update(copy.deepcopy(fields))
        r.setdefault("evidence", []).extend(copy.deepcopy(x.get("add_evidence", [])))
        return r
    return copy.deepcopy(x)


def records_of(refs) -> list[dict]:
    out = []
    for ref in refs:
        got = resolve(ref)
        out.extend(got if isinstance(got, list) else [got])
    return out


def scenario(sid: str) -> dict:
    return data.load_json(f"scenarios/{sid}.json")


def put_state(sc: dict) -> dict[str, dict]:
    """The current records after a scenario's ``given`` put steps."""
    state: dict[str, dict] = {}
    for step in sc["given"]:
        assert set(step) == {"put"}, step
        for r in records_of(step["put"]):
            state[r["id"]] = r
    return state


def subset(expected, got) -> bool:
    """The scenario rule for ``info``: objects match on their listed keys, lists element-wise with equal length."""
    if isinstance(expected, dict):
        return isinstance(got, dict) and all(k in got and subset(v, got[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(got, list) and len(expected) == len(got) and all(map(subset, expected, got))
    return expected == got


def disputed_state() -> dict[str, dict]:
    """S-KEY-010 and S-KEY-017's given: Warszawa stored, then a transition disputing it together with the Kraków
    claim (m:dis-1), built with ``lifecycle.with_status``."""
    warszawa = FIX["f:born-skłodowska-warszawa"]
    krakow = resolve({"@": "f:born-skłodowska-kraków", "set": {"status": "asserted"}, "drop": ["status_ref"]})
    dispute = {"kind": "hyperedge", "id": "m:dis-1", "relation": "khg:disputes", "status": "asserted",
               "reason": "key_conflict", "bindings": [
                   {"bid": "b1", "role": "khg:disputed", "value": {"fact": warszawa["id"]}},
                   {"bid": "b2", "role": "khg:disputed", "value": {"fact": krakow["id"]}}],
               "evidence": [{"id": "e9", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:scenario"}}]}
    state = {e["id"]: e for e in ENTITIES}
    state[warszawa["id"]] = lifecycle.with_status(warszawa, "disputed", "m:dis-1")
    state[krakow["id"]] = lifecycle.with_status(krakow, "disputed", "m:dis-1")
    state["m:dis-1"] = dispute
    assert lifecycle.pointer_problems(state) == []
    return state


# ------------------------------------------------------------------------------------------------ the action table


#: DESIGN §2.5, the action table: (classes, policies, shapes) -> action. None is the shape of a non-temporal key.
ACTION_TABLE = [
    (keys.MERGE_CLASSES, keys.POLICIES, keys.SHAPES + (None,), "merge"),
    (("distinct",), ("close_older",), ("succession",), "close_older"),
    (("distinct",), ("close_older",), ("backfill",), "close_incoming"),
    (("distinct",), ("close_older",), ("same_start", "overlap_after_end"), "dispute"),
    (("distinct",), ("dispute",), keys.SHAPES + (None,), "dispute"),
    (("distinct",), ("supersede",), (None,), "supersede"),
    (("distinct",), ("reject",), keys.SHAPES + (None,), "reject"),
]


def test_the_vocabularies():
    assert keys.POLICIES == ("close_older", "supersede", "dispute", "reject")
    assert keys.SHAPES == ("succession", "backfill", "overlap_after_end", "same_start")
    assert keys.CLASSES == ("duplicate", "refines", "generalises", "distinct")
    assert set(keys.ACTIONS) == {row[3] for row in ACTION_TABLE}


@pytest.mark.parametrize(("classes", "policies", "shapes", "action"), ACTION_TABLE)
def test_the_action_table_row_by_row(classes, policies, shapes, action):
    for cls, policy, shape in itertools.product(classes, policies, shapes):
        assert keys.action_for(policy, cls, shape) == action, (cls, policy, shape)


def test_the_combinations_outside_the_table():
    # close_older needs time: on a non-temporal key a distinct conflict is a dispute
    assert keys.action_for("close_older", "distinct", None) == "dispute"
    # supersede on a temporal key is refused by the schema (M017); the action stays the policy
    assert {keys.action_for("supersede", "distinct", s) for s in keys.SHAPES} == {"supersede"}
    covered = {(c, p, s) for cs, ps, ss, _ in ACTION_TABLE for c, p, s in itertools.product(cs, ps, ss)}
    every = set(itertools.product(keys.CLASSES, keys.POLICIES, keys.SHAPES + (None,)))
    assert every - covered == {("distinct", "close_older", None)} | {("distinct", "supersede", s) for s in keys.SHAPES}


@pytest.mark.parametrize("args", [("merge", "distinct", None), ("dispute", "same", None),
                                  ("dispute", "distinct", "undated")])
def test_action_for_refuses_unknown_values(args):
    with pytest.raises(ValueError):
        keys.action_for(*args)


# ------------------------------------------------------------------------------------------------ class and shape


def test_classes_come_from_refinement():
    k14 = FIX["f:king-14"]
    assert keys.classify(fact("f:king-14", "f:king-14x"), k14, S) == "duplicate"
    # the Julian writing of one day is one value: still a duplicate
    julian = fact("f:king-14", "f:king-14j", b3={"literal": {"datatype": "time", "time": "+1643-05-04T00:00:00Z",
                                                            "precision": 11, "calendar": "julian"}})
    assert keys.classify(julian, k14, S) == "duplicate"
    open_ended = fact("f:king-14", "f:king-14o", drop=("b4",))
    assert keys.classify(k14, open_ended, S) == "refines"
    assert keys.classify(open_ended, k14, S) == "generalises"
    assert keys.classify(FIX["f:king-13"], k14, S) == "distinct"
    # meta bindings never change the class
    caused = fact("f:king-14", "f:king-14c")
    caused["bindings"].append({"bid": "b6", "role": "khg:end_cause", "value": {"entity": "ex:Mazarin"}})
    assert keys.classify(caused, k14, S) == "duplicate"


def test_shapes_on_a_temporal_key():
    k13_open = fact("f:king-13", drop=("b4",))
    k14_open = fact("f:king-14", drop=("b4",))
    k14_1640 = fact("f:king-14", "f:king-14b", b3=T("+1640-01-01T00:00:00Z"))
    # the stored fact is earlier and still holds
    assert keys.shape_of(FIX["f:king-14"], k13_open, S) == "succession"
    # the incoming fact is earlier and still holds
    assert keys.shape_of(k13_open, k14_open, S) == "backfill"
    # the earlier fact has an end that overlaps the later start (stored or incoming)
    assert keys.shape_of(k14_1640, FIX["f:king-13"], S) == "overlap_after_end"
    assert keys.shape_of(FIX["f:king-13"], k14_1640, S) == "overlap_after_end"
    # neither start window lies before the other
    same = fact("f:king-13", b3=T("+1643-05-14T00:00:00Z"), drop=("b4",))
    assert keys.shape_of(k14_open, same, S) == "same_start"
    # a year-precision start overlapping a day-precision one: same start
    assert keys.shape_of(fact("f:king-14", b3=T("+1643-00-00T00:00:00Z", 9)), same, S) == "same_start"


def test_two_starts_since_forever_are_the_same_start():
    forever = {"special": "novalue"}
    a = fact("f:king-13", b3=forever, drop=("b4",))
    b = fact("f:king-14", b3=forever, drop=("b4",))
    assert bounds(a, S).s_hi == bounds(a, S).s_lo == float("-inf")
    assert keys.shape_of(a, b, S) == keys.shape_of(b, a, S) == "same_start"
    # held since forever beside a dated start: the novalue start is the earlier one
    assert keys.shape_of(FIX["f:king-14"], a, S) == "succession"
    assert keys.shape_of(a, fact("f:king-14", drop=("b4",)), S) == "backfill"


def test_a_non_temporal_key_has_no_shape():
    assert keys.shape_of(FIX["f:born-skłodowska-kraków"], FIX["f:born-skłodowska-warszawa"], S) is None
    assert keys.shape_of(FIX["f:pop-łódź-2019"], FIX["f:pop-łódź-2019-dep"], S) is None


# ------------------------------------------------------------------------------------------------ the invariant


def test_the_fixture_keeps_the_invariant():
    assert keys.key_invariant_violations(FIX, S) == []
    groups = keys.key_groups(FIX, S)
    assert groups[("position_held", KD_POSITION)] == [FIX["f:king-13"], FIX["f:king-14"]]
    # deprecated, superseded, quoted and goal facts and lifecycle records are not in any group; f:born-scribe is
    # (its key role, person, holds an entity: the somevalue birthplace is not a key role)
    grouped = {r["id"] for rs in groups.values() for r in rs}
    assert grouped == {"f:king-13", "f:king-14", "f:pop-łódź-2019", "f:born-skłodowska-warszawa", "f:born-scribe"}


def test_definitely_overlapping_holders_break_it_at_the_first_shared_instant():
    state = dict(FIX, **{"f:king-14": fact("f:king-14", b3=T("+1640-01-01T00:00:00Z"))})  # MC126
    assert keys.key_invariant_violations(state, S) == [
        Violation("position_held", KD_POSITION, True, ("f:king-13", "f:king-14"), "+1640-01-02T00:00:00Z")]
    # a novalue end means "still holds" (MC129)
    state = dict(FIX, **{"f:king-13": fact("f:king-13", b4={"special": "novalue"})})
    assert [v.ids for v in keys.key_invariant_violations(state, S)] == [("f:king-13", "f:king-14")]


def test_one_preferred_fact_may_stand_beside_normal_ones_but_not_two():
    pref = fact("f:pop-łódź-2019", rank="preferred")
    normal = fact("f:pop-łódź-2019-dep", rank="normal")
    third = fact("f:pop-łódź-2019-dep", "f:pop-łódź-2019-c", rank="normal")
    assert keys.key_invariant_violations([pref, normal], S) == []  # S-KEY-004
    # judged per instant: a preferred fact beside two normal ones is valid (B's pairwise check refused it)
    assert keys.key_invariant_violations([pref, normal, third], S) == []
    both = fact("f:pop-łódź-2019-dep", rank="preferred")  # MC127
    [v] = keys.key_invariant_violations([pref, both], S)
    assert (v.temporal, v.ids, v.at) == (False, ("f:pop-łódź-2019", "f:pop-łódź-2019-dep"), None)
    # two normal facts and no preferred one
    assert [v.ids for v in keys.key_invariant_violations([normal, third], S)] == [
        ("f:pop-łódź-2019-c", "f:pop-łódź-2019-dep")]


def test_the_judgement_is_made_where_a_window_ends_too():
    """A preferred holder ends while two normal ones go on: from that instant the invariant is broken, although it
    holds at every instant where a window starts (the prototype checked only those)."""
    a = fact("f:king-13", "f:a", b3=T("+1700-01-01T00:00:00Z"), b4=T("+1800-01-01T00:00:00Z"))
    b = fact("f:king-14", "f:b", b3=T("+1700-01-01T00:00:00Z"), b4=T("+1800-01-01T00:00:00Z"))
    c = fact("f:king-13", "f:c", b3=T("+1700-01-01T00:00:00Z"), b4=T("+1750-01-01T00:00:00Z"), rank="preferred")
    assert keys.key_invariant_violations([a, b, c], S) == [
        Violation("position_held", KD_POSITION, True, ("f:a", "f:b"), "+1750-01-01T00:00:00Z")]
    [coll] = keys.collisions({"f:a": a, "f:c": c}, [b], S)
    assert [x["id"] for x in coll["conflicts"]] == ["f:a"]


def test_facts_without_definite_validity_never_break_it():
    undated = fact("f:king-13", drop=("b3", "b4"))
    assert keys.key_invariant_violations([undated, FIX["f:king-14"]], S) == []  # S-KEY-012
    assert keys.key_invariant_violations([undated, fact("f:king-14", drop=("b3", "b4"))], S) == []  # S-KEY-013
    ended_unknown = fact("f:king-13", b4={"special": "somevalue"})
    assert bounds(ended_unknown, S).definite is None
    assert keys.key_invariant_violations([ended_unknown, FIX["f:king-14"]], S) == []


def test_a_special_value_in_a_key_role_exempts_the_fact():
    x1 = fact("f:born-scribe", "f:born-x1", b1={"special": "somevalue"}, b2={"entity": "ex:Paris"})
    x2 = fact("f:born-scribe", "f:born-x2", b1={"special": "somevalue"}, b2={"entity": "ex:Kraków"})
    assert key_digest(x1, S) is None
    assert keys.key_groups([x1, x2], S) == {} and keys.key_invariant_violations([x1, x2], S) == []  # S-KEY-011


def test_key_literals_compare_by_value_identity_with_their_precision():
    q2 = fact("f:pop-łódź-2019", "f:pop-q2", b3=T("+2019-06-30T00:00:00Z"),
              b2={"literal": {"datatype": "quantity", "amount": "+682000", "unit": "1"}})
    assert key_digest(q2, S) != key_digest(FIX["f:pop-łódź-2019"], S)  # S-KEY-019: precision is identity
    assert keys.key_invariant_violations([q2, FIX["f:pop-łódź-2019"]], S) == []
    assert len(keys.key_groups([q2, FIX["f:pop-łódź-2019"]], S)) == 2
    # the calendar is not: the Julian writing of 30 June 2019 is the same key
    june_17 = {"datatype": "time", "time": "+2019-06-17T00:00:00Z", "precision": 11, "calendar": "julian"}
    julian = fact("f:pop-łódź-2019", "f:pop-q2j", b3={"literal": june_17})
    assert key_digest(julian, S) == key_digest(q2, S)
    assert [v.ids for v in keys.key_invariant_violations([q2, julian], S)] == [("f:pop-q2", "f:pop-q2j")]


def test_quoted_disputed_and_deprecated_facts_are_outside_the_invariant():
    paris = fact("f:born-skłodowska-warszawa", "f:born-paris", b2={"entity": "ex:Paris"})
    for status in ("quoted", "disputed"):
        other = dict(paris, status=status)
        assert keys.key_invariant_violations([FIX["f:born-skłodowska-warszawa"], other], S) == []
    deprecated = dict(paris, rank="deprecated", rank_reason=["wd:Q41755623"])
    assert keys.key_invariant_violations([FIX["f:born-skłodowska-warszawa"], deprecated], S) == []
    assert keys.key_invariant_violations([FIX["f:born-skłodowska-warszawa"], paris], S) != []  # MC128


def test_key_groups_can_be_restricted():
    state = dict(FIX, **{"f:king-14": fact("f:king-14", b3=T("+1640-01-01T00:00:00Z"))})
    assert keys.key_invariant_violations(state, S, keys={("born_in", KD_MARIA)}) == []
    assert list(keys.key_groups(FIX, S, statuses=("superseded",))) == [("born_in", KD_MARIA)]


def _brute_force(rs):
    """The invariant at a sample of every constant piece of the timeline (both ends and the middle of each gap)."""
    ws = {r["id"]: bounds(r, S) for r in rs}
    edges = sorted({x for b in ws.values() for x in (b.s_hi, b.e_lo) if abs(x) != float("inf")})
    samples = set(edges) | {x - 1 for x in edges} | {(a + b) // 2 for a, b in zip(edges[:-1], edges[1:], strict=True)}
    bad = set()
    for t in samples:
        held = [r for r in rs if ws[r["id"]].s_hi <= t < ws[r["id"]].e_lo]
        if len(held) > 1 and sum(r.get("rank") == "preferred" for r in held) != 1:
            bad.add(tuple(sorted(r["id"] for r in held)))
    return bad


def test_the_invariant_agrees_with_a_brute_force_sample_on_random_timelines():
    rng = random.Random(20260923)
    for trial in range(200):
        rs = []
        for n in range(rng.randint(2, 5)):
            y0 = rng.randint(1700, 1710)
            start = T(f"+{y0:04d}-00-00T00:00:00Z", 9) if rng.random() < 0.5 else T(f"+{y0:04d}-06-01T00:00:00Z")
            y1 = y0 + rng.randint(0, 4)
            end = rng.choice([None, T(f"+{y1:04d}-00-00T00:00:00Z", 9), T(f"+{y1 + 1:04d}-03-01T00:00:00Z"),
                              {"special": "novalue"}])
            r = fact("f:king-13", f"f:x{n}", b3=start, drop=() if end else ("b4",),
                     rank=rng.choice(["normal", "normal", "preferred"]))
            if end:
                r["bindings"][0]["value"] = end
            if bounds(r, S).s_lo < bounds(r, S).e_hi:
                rs.append(r)
        got = {v.ids for v in keys.key_invariant_violations(rs, S)}
        assert got == _brute_force(rs), trial


# ------------------------------------------------------------------------------------------------ L008


def test_the_fixture_handover_is_a_possible_only_overlap():
    assert keys.possible_only_overlaps(FIX, S) == [("f:king-13", "f:king-14")]
    assert keys.l008_warnings(FIX, S) == [{"code": "KHG-L008", "ids": ["f:king-13", "f:king-14"]}]
    assert keys.l008_warnings(FIX, S, ids=["f:king-14"]) == keys.l008_warnings(FIX, S)
    assert keys.l008_warnings(FIX, S, ids=["f:reg-1"]) == []


@pytest.mark.parametrize("sid", ["S-KEY-009", "S-KEY-012", "S-KEY-013"])
def test_the_receipt_warnings_of_the_scenarios(sid):
    sc = scenario(sid)
    state = put_state(sc)
    [step] = sc["when"]
    batch = records_of(step["args"]["records"])
    assert keys.collisions(state, batch, S) == []
    after = dict(state, **{r["id"]: r for r in batch})
    assert step["then"]["select"] == "receipt.warnings"
    assert keys.l008_warnings(after, S, ids=[r["id"] for r in batch]) == step["then"]["equals"]


def test_definite_overlaps_are_not_warnings():
    state = dict(FIX, **{"f:king-14": fact("f:king-14", b3=T("+1640-01-01T00:00:00Z"))})
    assert keys.possible_only_overlaps(state, S) == []


# ------------------------------------------------------------------------------------------------ collisions


def test_the_section_2_5_example_exactly():
    """S-KEY-018: the store holds f:king-13 and Warszawa; one put writes Kraków as asserted and f:king-14b."""
    sc = scenario("S-KEY-018")
    state = put_state(sc)
    batch = records_of(sc["when"][0]["args"]["records"])
    assert keys.collisions(state, batch, S) == [
        {"record": "f:born-skłodowska-kraków", "relation": "born_in", "key_digest": KD_MARIA, "policy": "dispute",
         "conflicts": [{"id": "f:born-skłodowska-warszawa", "in_batch": False, "shape": None, "class": "distinct",
                        "action": "dispute"}]},
        {"record": "f:king-14b", "relation": "position_held", "key_digest": KD_POSITION, "policy": "close_older",
         "conflicts": [{"id": "f:king-13", "in_batch": False, "shape": "overlap_after_end", "class": "distinct",
                        "action": "dispute"}]}]


@pytest.mark.parametrize("sid", ["S-KEY-001", "S-KEY-006", "S-KEY-007", "S-KEY-014", "S-KEY-015", "S-KEY-016",
                                 "S-KEY-018"])
def test_the_collision_info_of_the_scenarios(sid):
    sc = scenario(sid)
    state = put_state(sc)
    step = sc["when"][0]
    assert step["op"] == "put" and step["then"]["error"] == "KHG-D016"
    found = keys.collisions(state, records_of(step["args"]["records"]), S)
    assert subset(step["then"]["info"], {"collisions": found})
    error = keys.key_collision(found)
    assert isinstance(error, KeyCollision) and error.codes == ("KHG-D016",) and error.info == {"collisions": found}


@pytest.mark.parametrize(("sid", "step"), [("S-KEY-004", 0), ("S-KEY-011", 0), ("S-KEY-019", 0), ("S-KEY-015", 1)])
def test_the_scenario_puts_that_are_accepted(sid, step):
    sc = scenario(sid)
    state = put_state(sc)
    batch = records_of(sc["when"][step]["args"]["records"])
    assert keys.collisions(state, batch, S) == []


def test_after_the_caller_acts_the_put_is_accepted():
    # S-KEY-007: end_validity closes f:king-13 at the new start, then f:king-14 is written
    closed = {e["id"]: e for e in ENTITIES} | {"f:king-13": FIX["f:king-13"]}
    assert keys.collisions(closed, [FIX["f:king-14"]], S) == []
    # S-KEY-016: the merge writes the refining content as a new version of the stored fact
    sc = scenario("S-KEY-016")
    state = put_state(sc)
    assert keys.collisions(state, records_of(sc["when"][1]["args"]["records"]), S) == []


def test_a_new_claim_on_a_disputed_key_joins_the_dispute():
    sc = scenario("S-KEY-017")
    step = sc["when"][0]
    found = keys.collisions(disputed_state(), records_of(step["args"]["records"]), S)
    assert subset(step["then"]["info"], {"collisions": found})
    assert found[0]["policy"] == "dispute"
    # a transition writes records without the rule (the dispute event joins them)
    assert keys.collisions(disputed_state(), records_of(step["args"]["records"]), S, disputed_rule=False) == []


def test_a_transition_back_to_asserted_rechecks_the_key():
    """S-KEY-010: Warszawa is asserted again; then asserting Kraków collides with it."""
    state = disputed_state()
    state["f:born-skłodowska-warszawa"] = lifecycle.with_status(state["f:born-skłodowska-warszawa"], "asserted")
    krakow = lifecycle.with_status(state["f:born-skłodowska-kraków"], "asserted")
    post = dict(state, **{krakow["id"]: krakow})
    found = keys.collisions(state, [krakow], S, post=post, disputed_rule=False)
    expected = scenario("S-KEY-010")["when"][2]["then"]["info"]
    assert subset(expected, {"collisions": found})


def test_an_undo_that_restores_a_corrected_fact_collides():
    """S-LIFE-013: retracting m:sup-1 without resolving the superseding fact restores Kraków beside Warszawa."""
    state = {i: r for i, r in FIX.items() if i in ("f:born-skłodowska-kraków", "f:born-skłodowska-warszawa",
                                                     "m:sup-1")}
    restored = lifecycle.with_status(state["f:born-skłodowska-kraków"], "asserted")
    post = dict(state, **{restored["id"]: restored,
                          "m:sup-1": lifecycle.with_status(state["m:sup-1"], "retracted", "m:ret-9")})
    found = keys.collisions(state, [restored], S, post=post, disputed_rule=False)
    assert [(c["record"], [x["id"] for x in c["conflicts"]]) for c in found] == [
        ("f:born-skłodowska-kraków", ["f:born-skłodowska-warszawa"])]


def test_conflicts_inside_one_batch():
    k14b = fact("f:king-14", "f:king-14b", b3=T("+1640-01-01T00:00:00Z"))
    found = keys.collisions({}, [FIX["f:king-13"], k14b], S)
    assert [(c["record"], c["conflicts"][0]["id"], c["conflicts"][0]["in_batch"], c["conflicts"][0]["shape"])
            for c in found] == [("f:king-13", "f:king-14b", True, "overlap_after_end"),
                                ("f:king-14b", "f:king-13", True, "overlap_after_end")]


def test_a_refining_claim_is_a_merge_whatever_the_policy():
    open_ended = fact("f:king-14", drop=("b4",))
    for policy in keys.POLICIES:
        doc = copy.deepcopy(SCHEMA_DOC)
        for rel in doc["relations"]:
            if rel["id"] == "position_held":
                rel["key"]["on_collision"] = policy
        schema = Schema(doc)  # supersede on a temporal key is M017: used unchecked here
        [coll] = keys.collisions({"f:king-14": open_ended}, [fact("f:king-14", "f:king-14b")], schema)
        assert (coll["policy"], coll["conflicts"][0]["class"], coll["conflicts"][0]["action"]) == (
            policy, "refines", "merge")


def test_what_never_collides():
    paris = fact("f:born-skłodowska-warszawa", "f:born-paris", b2={"entity": "ex:Paris"})
    stored = {"f:born-skłodowska-warszawa": FIX["f:born-skłodowska-warszawa"]}
    assert keys.collisions(stored, [dict(paris, status="quoted")], S) == []
    assert keys.collisions(stored, [dict(paris, rank="deprecated", rank_reason=["wd:Q41755623"])], S) == []
    # a deprecated claim does not join a dispute either, and a lifecycle record has no key
    assert keys.collisions(disputed_state(), [dict(paris, rank="deprecated", rank_reason=["x"])], S) == []
    assert keys.collisions(FIX, [FIX["m:sup-1"]], S) == []
    assert keys.collisions(stored, [paris], S) != []


def test_collisions_do_not_depend_on_input_order():
    sc = scenario("S-KEY-018")
    state = list(put_state(sc).values())
    batch = records_of(sc["when"][0]["args"]["records"])
    want = keys.collisions(state, batch, S)
    rng = random.Random(7)
    for _ in range(5):
        rng.shuffle(state)
        rng.shuffle(batch)
        assert keys.collisions(state, batch, S) == want
        assert keys.collisions({r["id"]: r for r in state}, batch, S) == want


def test_the_key_collision_error():
    found = keys.collisions({"f:king-13": FIX["f:king-13"]},
                            [fact("f:king-14", "f:king-14b", b3=T("+1640-01-01T00:00:00Z"))], S)
    error = keys.key_collision(found)
    assert error.code == "KHG-D016" and "f:king-14b" in str(error)
    assert keys.key_collision(found, "custom").message == "custom"
