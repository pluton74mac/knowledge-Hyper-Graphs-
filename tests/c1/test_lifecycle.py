"""W5: the lifecycle rules (DESIGN §2.6, §2.7, §2.9, §6.2): the four axes, the transition table (D014), the version
rule (D013), history containers (D001, D018), the pointer rule (D010), supersession constraints (D011), cycles (D012,
D008), transaction times and the errors a store raises for them."""
from __future__ import annotations

import copy
import itertools

import pytest

from khg_contracts import data, record
from khg_contracts.errors import ValidationError, VersionError
from khg_contracts.record import lifecycle
from khg_contracts.record.lifecycle import Problem
from khg_contracts.schema import load_schema

S = load_schema(data.path("fixture/fixture.relation-schema.json"))
C1 = data.load_json("fixture/fixture.c1.json")
FIX = {r["id"]: r for r in C1["records"]}
HISTORY = data.load_json("fixture/fixture.history.c1.json")


def T(time: str, precision: int = 11) -> dict:
    return {"literal": {"datatype": "time", "time": time, "precision": precision}}


def fact(fid: str, **changes) -> dict:
    f = copy.deepcopy(FIX[fid])
    f.update(changes)
    return f


def with_binding(record: dict, bid: str, value) -> dict:
    r = copy.deepcopy(record)
    for b in r["bindings"]:
        if b["bid"] == bid:
            b["value"] = value
    return r


def codes(problems) -> list[str]:
    return [p.code for p in problems]


# ------------------------------------------------------------------------------------------------ axes and table


def test_the_four_axes():
    assert dict(lifecycle.AXES) == {"belief": "status", "world": "valid_time", "editorial": "rank",
                                    "display": "visibility"}
    axes = lifecycle.axes(FIX["f:king-14"], S)
    assert {k: axes[k] for k in ("belief", "editorial", "display")} == {
        "belief": "asserted", "editorial": "normal", "display": "visible"}
    assert axes["world"] == record.valid_time(FIX["f:king-14"], S)
    world = axes["world"]
    assert (world["kind"], world["definite"], world["possible"]) == (
        "period", ["+1643-05-15T00:00:00Z", "+1715-09-01T00:00:00Z"],
        ["+1643-05-14T00:00:00Z", "+1715-09-02T00:00:00Z"])
    dep = lifecycle.axes(FIX["f:pop-łódź-2019-dep"], S)
    assert (dep["belief"], dep["editorial"], dep["world"]["kind"]) == ("asserted", "deprecated", "invariant")
    with pytest.raises(ValueError):
        lifecycle.axes(FIX["ex:Paris"], S)


def test_the_statuses_and_the_transition_table():
    assert lifecycle.STATUSES == ("candidate", "asserted", "disputed", "superseded", "retracted", "quoted", "goal")
    assert lifecycle.PUT_STATUSES == ("asserted", "quoted", "goal")
    assert dict(lifecycle.LIFECYCLE_ROLE) == {"disputed": ("khg:disputes", "khg:disputed"),
                                              "superseded": ("khg:supersedes", "khg:superseded"),
                                              "retracted": ("khg:retracts", "khg:retracted")}
    assert len(lifecycle.TABLE) == 9
    assert [(r.sources, r.targets, r.how, r.record) for r in lifecycle.TABLE[:3]] == [
        (("new",), ("asserted", "quoted", "goal"), "put", None),
        (("new",), ("asserted",), "supersede", "khg:supersedes"),
        (("new",), ("disputed",), "transition", "khg:disputes")]
    assert lifecycle.TRANSITIONS == {
        ("asserted", "superseded"), ("disputed", "superseded"),
        ("asserted", "disputed"), ("disputed", "disputed"),
        ("asserted", "retracted"), ("disputed", "retracted"), ("goal", "retracted"), ("quoted", "retracted"),
        ("disputed", "asserted"), ("quoted", "asserted"), ("goal", "asserted"), ("superseded", "asserted")}


@pytest.mark.parametrize(("old", "new"), list(itertools.product(lifecycle.STATUSES, repeat=2)))
def test_every_status_move_of_a_fact(old, new):
    p = lifecycle.transition_problem(old, new, relation="born_in", id="f:x", version=2)
    if old == new or (old, new) in lifecycle.TRANSITIONS:
        assert p is None
    else:
        assert p == Problem("KHG-D014", "f:x", "/status", p.message, 2)
        assert ("terminal" in p.message) == (old == "retracted")


def test_lifecycle_records_are_only_retracted_and_khg_retracts_not_even_that():
    assert lifecycle.transition_problem("asserted", "retracted", relation="khg:supersedes") is None
    assert lifecycle.transition_problem("asserted", "retracted", relation="khg:disputes") is None
    assert lifecycle.transition_problem("asserted", "retracted", relation="khg:retracts").code == "KHG-D014"
    for relation in ("khg:supersedes", "khg:disputes"):
        assert lifecycle.transition_problem("asserted", "disputed", relation=relation).code == "KHG-D014"
        assert lifecycle.transition_problem("asserted", "superseded", relation=relation).code == "KHG-D014"


def test_what_put_refuses():
    assert lifecycle.put_problem(fact("f:reg-1", status="candidate")).code == "KHG-D017"
    assert lifecycle.put_problem(FIX["m:sup-1"]).code == "KHG-D014"  # S-PUT, lifecycle records by events only
    assert lifecycle.put_problem(FIX["f:born-skłodowska-kraków"]).code == "KHG-D014"  # S-LIFE-005
    for status in lifecycle.PUT_STATUSES:
        assert lifecycle.put_problem(fact("f:reg-1", status=status)) is None
    assert lifecycle.put_problem(fact("f:reg-1", status="quoted"), FIX["f:reg-1"]).code == "KHG-D014"
    assert lifecycle.put_problem(FIX["f:reg-1"], FIX["f:reg-1"]) is None
    assert lifecycle.put_problem(FIX["ex:Paris"]) is None


def test_with_status_sets_and_drops_the_pointer_and_the_goal_block():
    stored = fact("f:reg-1", version=3, recorded_at="2026-10-01T00:00:03Z", recorded_by="x", derived={"arity": 3})
    disputed = lifecycle.with_status(stored, "disputed", "m:dis-1")
    assert (disputed["status"], disputed["status_ref"]) == ("disputed", "m:dis-1")
    assert not {"version", "recorded_at", "recorded_by", "derived"} & set(disputed)
    back = lifecycle.with_status(disputed, "asserted")
    assert back["status"] == "asserted" and "status_ref" not in back  # S-KEY-010, S-LIFE-007
    goal = lifecycle.with_status(FIX["g:who-1774"], "asserted")
    assert "goal" not in goal and "goal" in FIX["g:who-1774"]
    # a goal block exists only in status goal (C012), so a retracted goal loses it too
    assert "goal" not in lifecycle.with_status(FIX["g:who-1774"], "retracted", "m:ret-1")
    for bad in (("disputed", None), ("asserted", "m:x"), ("unknown", None)):
        with pytest.raises(ValueError):
            lifecycle.with_status(FIX["f:reg-1"], *bad)


# ------------------------------------------------------------------------------------------------ the version rule


def test_a_refinement_is_a_valid_new_version():
    open_ended = copy.deepcopy(FIX["f:king-13"])
    open_ended["bindings"] = [b for b in open_ended["bindings"] if b["bid"] != "b4"]
    open_ended["evidence"][0]["supports"] = ["b1", "b2", "b3"]
    closed = copy.deepcopy(FIX["f:king-13"])
    closed["evidence"][0]["supports"] = ["b1", "b2", "b3"]
    closed["evidence"].append({"id": "e9", "type": "curated", "mode": "manual", "source": {"doc_id": "d"},
                               "supports": ["b4"]})
    assert lifecycle.version_problems(open_ended, closed, S) == []  # S-VER-003
    assert lifecycle.version_problems(FIX["f:king-13"], copy.deepcopy(FIX["f:king-13"]), S) == []
    witness = with_binding(FIX["f:born-scribe"], "b2", {"entity": "ex:Paris"})
    assert lifecycle.version_problems(FIX["f:born-scribe"], witness, S) == []  # S-VER-007
    day = with_binding(FIX["f:pop-łódź-2019"], "b3", T("+2019-06-30T00:00:00Z"))
    assert lifecycle.version_problems(FIX["f:pop-łódź-2019"], day, S) == []  # a refined key literal
    bound_goal = with_binding(FIX["g:who-1774"], "b1", {"entity": "ex:LouisXIV"})
    bound_goal["goal"] = {"brief": "Who became King of France on 10 May 1774?", "owner": "agent:other"}
    assert lifecycle.version_problems(FIX["g:who-1774"], bound_goal, S) == []  # S-LIFE-008; goal may change


def test_what_breaks_the_version_rule():
    k13 = FIX["f:king-13"]
    bob = with_binding(k13, "b1", {"entity": "ex:LouisXIV"})  # S-VER-003, the Bob-for-Alice probe
    [p] = lifecycle.version_problems(k13, bob, S)
    assert (p.code, p.id, p.pointer) == ("KHG-D013", "f:king-13", "/bindings/1/value")
    removed = copy.deepcopy(k13)
    removed["bindings"] = removed["bindings"][1:]
    assert codes(lifecycle.version_problems(k13, removed, S)) == ["KHG-D013"]
    moved = copy.deepcopy(k13)
    moved["bindings"][1]["role"] = "replaces"
    assert codes(lifecycle.version_problems(k13, moved, S)) == ["KHG-D013"]
    positioned = copy.deepcopy(FIX["f:route-1"])
    positioned["bindings"][1]["position"], positioned["bindings"][2]["position"] = 2, 1
    assert codes(lifecycle.version_problems(FIX["f:route-1"], positioned, S)) == ["KHG-D013", "KHG-D013"]
    coarser = with_binding(k13, "b3", T("+1610-00-00T00:00:00Z", 9))
    assert codes(lifecycle.version_problems(k13, coarser, S)) == ["KHG-D013"]
    other_relation = fact("f:king-13", relation="married")
    assert [p.pointer for p in lifecycle.version_problems(k13, other_relation, S)] == ["/relation"]
    typed = fact("f:king-13", typed_under="p2-gate/1.0.0")
    assert [p.pointer for p in lifecycle.version_problems(k13, typed, S)] == ["/typed_under"]
    assert lifecycle.version_problems(k13, FIX["ex:LouisXIII"], S)[0].pointer == "/kind"


def test_only_the_editorial_fields_change_freely():
    edited = fact("f:reg-1", rank="deprecated", rank_reason=["wd:Q41755623"], visibility="suppressed",
                  confidence={"value": 0.5, "scale": "probability"}, source_text="TP53 regulates itself.",
                  extensions={"ex:note": 1})
    assert lifecycle.version_problems(FIX["f:reg-1"], edited, S) == []
    # the goal block changes only while the status is goal
    asserted = copy.deepcopy(FIX["f:reg-1"])
    asserted["goal"] = {"brief": "x"}
    assert codes(lifecycle.version_problems(FIX["f:reg-1"], asserted, S)) == ["KHG-D013"]
    renoted = fact("m:sup-1", note="another note")
    assert [p.pointer for p in lifecycle.version_problems(FIX["m:sup-1"], renoted, S)] == ["/note"]


def test_a_novalue_end_is_replaced_only_by_end_validity():
    open_end = with_binding(FIX["f:king-13"], "b4", {"special": "novalue"})
    ended = copy.deepcopy(FIX["f:king-13"])
    ended["bindings"].append({"bid": "b5", "role": "khg:end_cause", "value": {"entity": "ex:LouisXIV"}})
    assert codes(lifecycle.version_problems(open_end, ended, S)) == ["KHG-D013"]
    assert lifecycle.version_problems(open_end, ended, S, allow_novalue_end=True) == []  # S-VER-009
    # only the end role: a novalue elsewhere stays a refinement question
    nv = with_binding(FIX["f:cat-7"], "b2", {"special": "novalue"})
    catalyst = with_binding(FIX["f:cat-7"], "b2", {"entity": "ex:insulin"})
    assert codes(lifecycle.version_problems(nv, catalyst, S, allow_novalue_end=True)) == ["KHG-D013"]


def test_bindings_are_added_only_where_the_role_is_not_complete():
    more = copy.deepcopy(FIX["f:king-14"])
    more["bindings"].append({"bid": "b6", "role": "replaces", "value": {"entity": "ex:Mazarin"}})
    assert lifecycle.version_problems(FIX["f:king-14"], more, S) == []
    third = copy.deepcopy(FIX["f:married-curie"])
    third["bindings"].append({"bid": "b5", "role": "spouse", "value": {"entity": "ex:LouisXIV"}})
    [p] = lifecycle.version_problems(FIX["f:married-curie"], third, S)
    assert (p.code, p.pointer) == ("KHG-D013", "/bindings/4") and "complete" in p.message
    stop = copy.deepcopy(FIX["f:route-1"])
    stop["bindings"].append({"bid": "b5", "role": "stop", "value": {"entity": "ex:YUL"}, "position": 4})
    assert codes(lifecycle.version_problems(FIX["f:route-1"], stop, S)) == ["KHG-D013"]


def test_earlier_evidence_stays_as_written():
    reg = FIX["f:reg-1"]
    rewritten = copy.deepcopy(reg)
    rewritten["evidence"][0]["source"] = {"doc_id": "doc:other"}  # S-VER-004
    [p] = lifecycle.version_problems(reg, rewritten, S)
    assert (p.code, p.pointer) == ("KHG-D013", "/evidence/0")
    dropped = fact("f:reg-1", evidence=[])
    assert [p.pointer for p in lifecycle.version_problems(reg, dropped, S)] == ["/evidence"]
    k14 = FIX["f:king-14"]
    rehashed = copy.deepcopy(k14)
    rehashed["evidence"][1]["event_hash"] = "sha256:" + "0" * 64
    assert codes(lifecycle.version_problems(k14, rehashed, S)) == ["KHG-D013"]
    appended = copy.deepcopy(reg)
    appended["evidence"].append({"id": "e2", "type": "curated", "mode": "manual", "source": {"doc_id": "d"}})
    assert lifecycle.version_problems(reg, appended, S) == []
    # supports written out equal the default (every bid of the version that carries the evidence)
    implicit = copy.deepcopy(reg)
    del implicit["evidence"][0]["supports"]
    assert lifecycle.version_problems(implicit, reg, S) == lifecycle.version_problems(reg, implicit, S) == []


def test_superseded_and_retracted_facts_are_frozen():
    krakow = FIX["f:born-skłodowska-kraków"]
    more = copy.deepcopy(krakow)
    more["evidence"].append({"id": "e2", "type": "curated", "mode": "manual", "source": {"doc_id": "d"}})
    [p] = lifecycle.version_problems(krakow, more, S)
    assert p.code == "KHG-D013" and "frozen" in p.message
    retracted = lifecycle.with_status(FIX["f:reg-1"], "retracted", "m:ret-1")
    assert codes(lifecycle.version_problems(retracted, dict(retracted, visibility="suppressed"), S)) == ["KHG-D013"]


def test_the_entity_version_rule():
    louis = FIX["ex:LouisXIV"]
    renamed = dict(louis, label="Louis XIV of France", aliases=["the Sun King"], extensions={"ex:a": 1})
    assert lifecycle.version_problems(louis, renamed, S) == []  # S-VER-008
    assert lifecycle.version_problems(louis, dict(louis, types=["Person", "Agent"]), S) == []
    assert [p.pointer for p in lifecycle.version_problems(louis, dict(louis, types=["Agent"]), S)] == ["/types"]
    paris = FIX["ex:Paris"]
    redirected = dict(paris, redirect_to="ex:Warszawa")
    assert lifecycle.version_problems(paris, redirected, S) == []
    assert codes(lifecycle.version_problems(redirected, dict(paris, redirect_to="ex:Kraków"), S)) == ["KHG-D013"]
    assert codes(lifecycle.version_problems(redirected, paris, S)) == ["KHG-D013"]
    assert [p.pointer for p in lifecycle.version_problems(paris, dict(paris, note="x"), S)] == ["/note"]


# ------------------------------------------------------------------------------------------------ histories


def versions(rid: str) -> list[dict]:
    return [copy.deepcopy(r) for r in HISTORY["records"] if r["id"] == rid]


@pytest.mark.parametrize("rid", sorted({r["id"] for r in HISTORY["records"]}))
def test_the_history_fixture_keeps_every_rule(rid):
    assert lifecycle.history_problems(versions(rid), S, as_at=HISTORY["header"]["as_at"]) == []


def test_history_rules():
    v1, v2 = versions("f:king-13")
    assert codes(lifecycle.history_problems([v1, with_binding(v2, "b1", {"entity": "ex:LouisXIV"})], S)) == [
        "KHG-D013"]  # MC136
    early = dict(v2, recorded_at="2026-10-01T00:00:01Z")  # MC139
    [p] = lifecycle.history_problems([early, v1], S)
    assert (p.code, p.version, p.pointer) == ("KHG-D018", 2, "/recorded_at")
    late = lifecycle.history_problems([v1, v2], S, as_at="2026-10-01T00:00:03Z")
    assert [(p.code, p.version) for p in late] == [("KHG-D018", 2)]
    assert codes(lifecycle.history_problems([v1, dict(v2, version=3)], S)) == ["KHG-D001"]
    assert codes(lifecycle.history_problems([v1, dict(v1)], S)) == ["KHG-D001", "KHG-D018"]
    r1, r2 = versions("f:reg-1")
    again = lifecycle.with_status(r2, "asserted") | {"version": 3, "recorded_at": "2026-10-01T00:00:06Z"}
    assert [(p.code, p.version) for p in lifecycle.history_problems([r1, r2, again], S)] == [("KHG-D014", 3)]  # MC138


def test_history_transitions_check_the_content_too():
    goal = copy.deepcopy(FIX["g:who-1774"]) | {"version": 1, "recorded_at": "2026-10-01T00:00:01Z"}
    bound = with_binding(goal, "b1", {"entity": "ex:LouisXIV"}) | {"version": 2, "recorded_at": "2026-10-01T00:00:02Z"}
    done = lifecycle.with_status(bound, "asserted") | {"version": 3, "recorded_at": "2026-10-01T00:00:03Z"}
    done["evidence"] = [{"id": "e9", "type": "curated", "mode": "manual", "source": {"doc_id": "d"}, "supports": []}]
    assert lifecycle.history_problems([goal, bound, done], S) == []
    changed = with_binding(done, "b2", {"entity": "ex:Paris"})
    assert codes(lifecycle.history_problems([goal, bound, changed], S)) == ["KHG-D013"]
    k = FIX["f:born-skłodowska-kraków"] | {"version": 2, "recorded_at": "2026-10-01T00:00:02Z"}
    undone = lifecycle.with_status(k, "asserted") | {"version": 3, "recorded_at": "2026-10-01T00:00:03Z"}
    assert lifecycle.history_problems([k, undone], S)[0].code == "KHG-D001"  # versions 2, 3: only the numbering
    assert codes(lifecycle.history_problems([dict(k, version=1), dict(undone, version=2)], S)) == []


# ------------------------------------------------------------------------------------------------ lifecycle records


def test_the_fixture_pointers_supersessions_and_nesting_are_valid():
    assert lifecycle.pointer_problems(FIX) == []
    assert lifecycle.supersession_problems(FIX, S) == []
    assert lifecycle.supersession_cycle(FIX) is None
    assert lifecycle.nesting_cycle(FIX) is None
    assert lifecycle.pointer_problems(C1["records"]) == []  # records given as a list


def test_the_pointer_rule():
    wrong = dict(FIX, **{"f:born-skłodowska-kraków": fact("f:born-skłodowska-kraków", status_ref="f:king-14")})
    [p] = lifecycle.pointer_problems(wrong)  # MC119
    assert (p.code, p.id, p.pointer) == ("KHG-D010", "f:born-skłodowska-kraków", "/status_ref")
    dangling = dict(FIX, **{"f:reg-1": fact("f:reg-1", status="disputed", status_ref="m:none")})  # MC120
    assert [(p.id, "names no record" in p.message) for p in lifecycle.pointer_problems(dangling)] == [
        ("f:reg-1", True)]
    moved = copy.deepcopy(FIX["m:sup-1"])
    moved["bindings"][0]["value"] = {"fact": "f:born-scribe"}  # MC121
    found = lifecycle.pointer_problems(dict(FIX, **{"m:sup-1": moved}))
    assert [(p.id, p.pointer) for p in found] == [("f:born-skłodowska-kraków", "/status_ref"),
                                                   ("m:sup-1", "/bindings/0/value")]
    retracted_lc = dict(FIX, **{"m:sup-1": lifecycle.with_status(FIX["m:sup-1"], "retracted", "m:ret-1")})
    assert {p.id for p in lifecycle.pointer_problems(retracted_lc)} == {"f:born-skłodowska-kraków", "m:sup-1"}


def test_a_dispute_record_may_outlive_its_dispute():
    dispute = {"kind": "hyperedge", "id": "m:dis-1", "relation": "khg:disputes", "status": "asserted",
               "reason": "curator", "bindings": [
                   {"bid": "b1", "role": "khg:disputed", "value": {"fact": "f:king-13"}},
                   {"bid": "b2", "role": "khg:disputed", "value": {"fact": "f:king-14"}}]}
    assert lifecycle.pointer_problems(dict(FIX, **{"m:dis-1": dispute})) == []


def _sup(reason: str, superseding: str, superseded: str) -> dict:
    return {"kind": "hyperedge", "id": "m:sup-9", "relation": "khg:supersedes", "status": "asserted",
            "reason": reason, "bindings": [
                {"bid": "b1", "role": "khg:superseding", "value": {"fact": superseding}},
                {"bid": "b2", "role": "khg:superseded", "value": {"fact": superseded}}]}


def test_the_supersession_constraints():
    def problems(reason, a, b):
        return lifecycle.supersession_problems(dict(FIX, **{"m:sup-9": _sup(reason, a, b)}), S)

    assert codes(problems("correction", "f:king-14", "f:born-skłodowska-kraków")) == ["KHG-D011"]  # MC123
    assert codes(problems("correction", "f:born-scribe", "f:born-skłodowska-kraków")) == ["KHG-D011"]  # MC124
    assert codes(problems("duplicate", "f:born-skłodowska-warszawa", "f:born-skłodowska-kraków")) == [
        "KHG-D011"]  # MC125
    assert problems("correction", "f:born-skłodowska-warszawa", "f:born-skłodowska-kraków") == []
    open_ended = fact("f:king-14", id="f:king-14o")
    open_ended["bindings"] = [b for b in open_ended["bindings"] if b["bid"] != "b4"]
    both = dict(FIX, **{"f:king-14o": open_ended})
    assert lifecycle.supersession_problems(dict(both, **{"m:sup-9": _sup("refinement", "f:king-14", "f:king-14o")}),
                                           S) == []
    assert codes(lifecycle.supersession_problems(
        dict(both, **{"m:sup-9": _sup("refinement", "f:king-14o", "f:king-14")}), S)) == ["KHG-D011"]
    for reason in ("conflation", "schema_migration", "other"):
        assert problems(reason, "f:king-14", "f:born-skłodowska-kraków") == []
    # the put check: only the supersessions that bind a written id (S-LIFE-014)
    bad = dict(FIX, **{"m:sup-9": _sup("duplicate", "f:reg-1", "f:loop-yyz")})
    assert codes(lifecycle.supersession_problems(bad, S, ids=["f:reg-1"])) == ["KHG-D011"]
    assert lifecycle.supersession_problems(bad, S, ids=["f:king-13"]) == []


def test_the_supersede_event_preconditions():
    warszawa, krakow = FIX["f:born-skłodowska-warszawa"], FIX["f:born-skłodowska-kraków"]
    assert lifecycle.supersede_problems([warszawa], [dict(krakow, status="asserted")], "correction", S) == []
    # the superseding fact must be asserted: events cannot form a cycle (S-LIFE-004)
    assert codes(lifecycle.supersede_problems([krakow], [warszawa], "correction", S)) == ["KHG-D011"]
    assert codes(lifecycle.supersede_problems([warszawa], [krakow], "correction", S)) == ["KHG-D014"]
    found = lifecycle.supersede_problems([warszawa], [dict(FIX["f:king-13"])], "correction", S, event_id="m:sup-2")
    assert [(p.code, p.id) for p in found] == [("KHG-D011", "m:sup-2")]


def test_supersession_cycles():
    back = _sup("correction", "f:born-skłodowska-kraków", "f:born-skłodowska-warszawa")  # MC122
    p = lifecycle.supersession_cycle(dict(FIX, **{"m:sup-9": back}))
    # reported at the supersession whose edge the search meets last (deterministic), naming both records
    assert (p.code, p.id, p.pointer) == ("KHG-D012", "m:sup-1", "")
    assert p.message == ("supersession cycle f:born-skłodowska-kraków -> f:born-skłodowska-warszawa -> "
                         "f:born-skłodowska-kraków (through m:sup-1, m:sup-9)")
    # a chain A -> B -> C is valid (S-LIFE-012)
    chain = dict(FIX, **{"m:sup-9": _sup("correction", "f:born-scribe", "f:born-skłodowska-warszawa")})
    assert lifecycle.supersession_cycle(chain) is None
    # a retracted supersession no longer counts
    retracted = dict(FIX, **{"m:sup-9": dict(back, status="retracted", status_ref="m:ret-9")})
    assert lifecycle.supersession_cycle(retracted) is None


def test_nesting_cycles():
    self_claim = copy.deepcopy(FIX["f:claim-1"])
    self_claim["bindings"][0]["value"] = {"fact": "f:claim-1"}  # MC118
    p = lifecycle.nesting_cycle(dict(FIX, **{"f:claim-1": self_claim}))
    assert (p.code, p.id, p.pointer) == ("KHG-D008", "f:claim-1", "/bindings/0/value")
    a = copy.deepcopy(FIX["f:claim-1"])
    a["id"], a["bindings"][0]["value"] = "f:claim-a", {"fact": "f:claim-b"}
    b = copy.deepcopy(FIX["f:claim-1"])
    b["id"], b["bindings"][0]["value"] = "f:claim-b", {"fact": "f:claim-a"}
    p = lifecycle.nesting_cycle([a, b])
    assert p.message.endswith("f:claim-a -> f:claim-b -> f:claim-a")
    # lifecycle records bind facts without nesting them
    assert lifecycle.nesting_cycle(dict(FIX, **{"m:sup-9": _sup("other", "f:reg-1", "f:reg-1")})) is None


# ------------------------------------------------------------------------------------------------ times and errors


def test_transaction_times():
    t = lifecycle.parse_timestamp
    assert t("2026-10-01T00:00:02Z") < t("2026-10-01T00:00:02.5Z") < t("2026-10-01T00:00:02.500001Z") < t(
        "2026-10-01T00:00:03Z")
    assert t("2026-10-01T00:00:02.5Z") - t("2026-10-01T00:00:02Z") == 500_000
    assert t("2026-10-02T00:00:00Z") - t("2026-10-01T00:00:00Z") == 86_400_000_000
    for bad in ("2026-10-01 00:00:00Z", "2026-13-01T00:00:00Z", "2026-02-29T00:00:00Z", "2026-10-01T00:00:00+00:00",
                "2026-10-01T00:00:00.1234567Z", "+2026-10-01T00:00:00Z", "2026-10-01T24:00:00Z", 20261001, None):
        with pytest.raises(ValidationError) as e:
            t(bad)
        assert e.value.codes == ("KHG-C011",)


def test_the_errors_a_store_raises():
    version = [Problem("KHG-D013", "f:x", "/bindings/0/value", "not refined", 2),
               Problem("KHG-D011", "m:s", "", "constraint")]
    e = lifecycle.error_for(version)
    assert isinstance(e, VersionError) and e.codes == ("KHG-D013", "KHG-D011")
    assert e.info["problems"][0] == {"code": "KHG-D013", "id": "f:x", "pointer": "/bindings/0/value",
                                     "message": "not refined", "version": 2}
    for code in ("KHG-D012", "KHG-D014", "KHG-D018"):
        assert type(lifecycle.error_for([Problem(code, "f:x", "", "m")])) is VersionError
    v = lifecycle.error_for([Problem("KHG-D010", "f:x", "/status_ref", "dangling"),
                             Problem("KHG-D008", "f:y", "", "cycle")])
    assert isinstance(v, ValidationError) and v.codes == ("KHG-D010", "KHG-D008")
    assert v.info["findings"][0]["path"] == "/status_ref" and len(v.info["problems"]) == 2
    with pytest.raises(ValueError):
        lifecycle.error_for([])
