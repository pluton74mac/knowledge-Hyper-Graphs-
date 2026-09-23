"""Running the scenarios (DESIGN §6.4): ``factory(schema, clock)`` gives an empty store per scenario, with a
``ScenarioClock`` (2026-10-01T00:00:00Z, one second per write; a step's ``at`` is passed to the write).

A scenario is **inapplicable** when its ``requires`` holds a flag the store does not declare (``info()``), or that
``capabilities`` leaves out: only a declared-absent flag makes a scenario inapplicable (the director's ruling on
§14). Otherwise its ``given`` steps run (``put`` steps one call each, one record per call for a store without
``atomic_writes``; ``apply`` one event; ``load`` one container), then each ``when`` step and its ``then`` clauses:

- **passed**: every step behaved as stated;
- **failed**: a clause did not hold, a call raised what the step did not expect, or the store raised
  ``CapabilityMissing`` for a flag it declares;
- **cantTell**: the store raised ``CapabilityMissing`` for a flag it lacks that the scenario does not list, or the
  scenario asks for a projection or clause this runner does not know.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from ... import jsonio
from ...errors import CapabilityMissing, KHGError
from ...validate import validate_hif
from ..clocks import ScenarioClock
from ..flags import capabilities as _capabilities
from ..where import Where
from . import checks
from .checks import Failed, Unknown
from .suite import Suite, select, suite

__all__ = ["ACTOR", "ARGS", "OUTCOMES", "Outcome", "call", "run_given", "run_scenario", "run_suite"]

OUTCOMES = ("passed", "failed", "inapplicable", "cantTell")
#: The ``recorded_by`` of every write the runner makes.
ACTOR = "scenario"
#: The arguments each operation takes in a scenario step.
ARGS: Mapping[str, frozenset[str]] = {
    "put": frozenset({"records", "expect"}),
    "apply": frozenset({"event"}),
    "get": frozenset({"id", "as_at", "version"}),
    "history": frozenset({"id"}),
    "get_many": frozenset({"ids", "as_at"}),
    "incident": frozenset({"node", "role", "relation", "where", "limit", "after"}),
    "degree": frozenset({"node", "role", "relation", "where"}),
    "find": frozenset({"relation", "pattern", "match", "where", "limit", "after"}),
    "find_by_key": frozenset({"relation", "key", "where"}),
    "supersession_walk": frozenset({"id", "direction", "as_at"}),
    "export": frozenset({"format", "content", "as_at", "relations", "header", "literal_nodes"}),
}

Factory = Callable[[Any, Any], Any]


@dataclass
class Outcome:
    """The result of one scenario."""

    id: str
    title: str
    requires: list[str]
    outcome: str
    info: str = ""
    missing: list[str] = field(default_factory=list)


def _options(args: Mapping[str, Any], *names: str) -> dict[str, Any]:
    return {n: args[n] for n in names if n in args}


def call(store: Any, step: Mapping[str, Any], s: Suite) -> Any:
    """Run one ``when`` step's operation on ``store``."""
    op, args = step.get("op"), dict(step.get("args", {}))
    if not isinstance(op, str) or op not in ARGS:
        raise Unknown(f"unknown operation {op!r}")
    extra = sorted(set(args) - ARGS[op])
    if extra:
        raise Unknown(f"{op}: unknown arguments {extra}")
    if "where" in args:
        args["where"] = Where.of(args["where"])
    at = step.get("at")
    if op == "put":
        return store.put(s.flat(args["records"]), actor=ACTOR, at=at, **_options(args, "expect"))
    if op == "apply":
        return store.apply(s.resolve(args["event"]), actor=ACTOR, at=at)
    if op in ("get", "history", "supersession_walk"):
        rest = _options(args, "as_at", "version", "direction")
        return getattr(store, op)(args["id"], **rest)
    if op == "get_many":
        return store.get_many(args["ids"], **_options(args, "as_at"))
    if op in ("incident", "degree"):
        return getattr(store, op)(args["node"], **_options(args, "role", "relation", "where", "limit", "after"))
    if op == "find":
        return store.find(args["relation"], s.resolve(args["pattern"]),
                          **_options(args, "match", "where", "limit", "after"))
    if op == "find_by_key":
        return store.find_by_key(args["relation"], s.resolve(args["key"]), **_options(args, "where"))
    rest = _options(args, "content", "as_at", "relations", "literal_nodes")
    if "header" in args:
        rest["header"] = s.resolve(args["header"])
    return store.export(args.get("format", "khg-jsonl"), **rest)


def run_given(store: Any, steps: Iterable[Mapping[str, Any]], s: Suite, flags: frozenset[str]) -> None:
    """Run the ``given`` steps."""
    for g in steps:
        if "load" in g:
            store.load(s.resolve(g["load"]))
        elif "put" in g:
            records = s.flat(g["put"])
            if "atomic_writes" in flags or len(records) <= 1:
                store.put(records, actor=ACTOR, at=g.get("at"))
            else:
                for i, r in enumerate(records):
                    store.put(r, actor=ACTOR, at=g.get("at") if i == 0 else None)
        elif "apply" in g:
            store.apply(s.resolve(g["apply"]), actor=ACTOR, at=g.get("at"))
        else:
            raise Unknown(f"unknown given step {sorted(g)}")


def _expected(value: Any, store_id: str, s: Suite) -> Any:
    if isinstance(value, str) and value.startswith("@"):
        return checks.canonical_no_store(s.resolve(value))
    if isinstance(value, str) and "{store_id}" in value:
        return value.replace("{store_id}", store_id)
    return value


def _then(then: Mapping[str, Any], result: Any, store: Any, step: Mapping[str, Any], scenario: Mapping[str, Any],
          s: Suite, factory: Factory, flags: frozenset[str]) -> None:
    unknown = sorted(set(then) - set(checks.CLAUSES))
    if unknown:
        raise Unknown(f"unknown then clauses {unknown}")
    op = step.get("op")
    if "select" in then:
        got = checks.project(result, then["select"], s.schema)
        want = _expected(then.get("equals"), str(store.info()["store_id"]), s)
        if not checks.same(got, want):
            raise Failed(f"{op} {then['select']}: got {checks.text(got)}, want {checks.text(want)}")
    if "container_equals" in then:
        diffs = checks.container_differences(s.resolve(then["container_equals"]), result, list(then.get("ignore", [])))
        if diffs:
            raise Failed(f"{op}: the export differs from {then['container_equals']}: {checks.text(diffs[:2], 600)}")
    if then.get("hif_valid"):
        report = validate_hif(result, schema=s.schema)
        if not report["ok"]:
            errors = [f for f in report["findings"] if f["severity"] == "error"]
            raise Failed(f"{op}: the HIF export is not valid: {checks.text(errors[:3], 600)}")
    if "equals_file" in then:
        ignore = list(then.get("ignore", []))
        if not checks.same(checks.strip_attrs(result, ignore), checks.strip_attrs(s.file(then["equals_file"]), ignore)):
            raise Failed(f"{op}: the export differs from {then['equals_file']}")
    if then.get("reload_equal"):
        lines = jsonio.loads_lines(result)
        again = factory(s.schema, ScenarioClock())
        try:
            again.load({"header": lines[0], "records": lines[1:]})
            args = {k: v for k, v in step.get("args", {}).items() if k != "header"}
            if again.export(args.pop("format", "khg-jsonl"), **args) != result:
                raise Failed(f"{op}: loading the export into a fresh store and exporting again gives other text")
        finally:
            _close(again)
    if then.get("deterministic"):
        again = factory(s.schema, ScenarioClock())
        try:
            run_given(again, scenario["given"], s, flags)
            if not checks.same(call(again, step, s), result):
                raise Failed(f"{op}: two fresh runs give different results")
        finally:
            _close(again)


def _close(store: Any) -> None:
    try:
        store.close()
    except Exception:  # noqa: BLE001 - closing never changes an outcome
        pass


def _code(e: BaseException) -> str:
    return (e.code or type(e).__name__) if isinstance(e, KHGError) else type(e).__name__


def _steps(store: Any, scenario: Mapping[str, Any], s: Suite, factory: Factory, flags: frozenset[str]) -> None:
    try:
        run_given(store, scenario["given"], s, flags)
    except (CapabilityMissing, Unknown):
        raise
    except Exception as e:  # noqa: BLE001 - any failure of a given step fails the scenario
        raise Failed(f"given: unexpected {_code(e)}: {e}") from e
    for n, step in enumerate(scenario["when"], 1):
        then = step.get("then", {})
        where = f"step {n} ({step.get('op')})"
        if "error" in then:
            try:
                call(store, step, s)
            except (CapabilityMissing, Unknown):
                raise
            except KHGError as e:
                if then["error"] not in e.codes:
                    raise Failed(f"{where}: raised {_code(e)} ({e}), want {then['error']}") from e
                if "info" in then and not checks.subset(then["info"], e.info):
                    raise Failed(f"{where}: info {checks.text(e.info, 600)} does not match "
                                 f"{checks.text(then['info'], 600)}") from e
                continue
            except Exception as e:  # noqa: BLE001
                raise Failed(f"{where}: raised {type(e).__name__} ({e}), want {then['error']}") from e
            raise Failed(f"{where}: did not raise {then['error']}")
        try:
            result = call(store, step, s)
        except (CapabilityMissing, Unknown):
            raise
        except Exception as e:  # noqa: BLE001
            raise Failed(f"{where}: unexpected {_code(e)}: {e}") from e
        try:
            _then(then, result, store, step, scenario, s, factory, flags)
        except Failed as e:
            raise Failed(f"{where}: {e}") from e


def run_scenario(factory: Factory, scenario: Mapping[str, Any] | str, *, capabilities: Iterable[str] | None = None,
                 s: Suite | None = None) -> Outcome:
    """Run one scenario (or the scenario with that id) on a fresh store; ``capabilities`` are the flags the store
    is tested with (default: the flags a fresh store declares)."""
    s = s or suite()
    sc = s.scenarios[scenario] if isinstance(scenario, str) else scenario
    requires = list(sc.get("requires", []))
    out = Outcome(sc["id"], sc.get("title", ""), requires, "passed")
    flags: frozenset[str] = frozenset()
    if capabilities is not None:
        flags = _capabilities(capabilities)
        missing = sorted(set(requires) - flags)
        if missing:
            out.outcome, out.missing, out.info = "inapplicable", missing, f"needs {', '.join(missing)}"
            return out
    try:
        store = factory(s.schema, ScenarioClock())
    except Exception as e:  # noqa: BLE001
        out.outcome, out.info = "failed", f"the factory raised {type(e).__name__}: {e}"
        return out
    try:
        declared = frozenset(store.info()["capabilities"])
        flags = declared if capabilities is None else declared & _capabilities(capabilities)
        missing = sorted(set(requires) - flags)
        if missing:
            out.outcome, out.missing, out.info = "inapplicable", missing, f"needs {', '.join(missing)}"
            return out
        _steps(store, sc, s, factory, flags)
    except CapabilityMissing as e:
        if e.flag in flags:
            out.outcome, out.info = "failed", f"the store declares {e.flag} but raised CapabilityMissing: {e}"
        else:
            out.outcome, out.missing = "cantTell", [e.flag]
            out.info = f"the store lacks {e.flag}, which the scenario does not list in requires: {e}"
    except Unknown as e:
        out.outcome, out.info = "cantTell", str(e)
    except Failed as e:
        out.outcome, out.info = "failed", str(e)
    except Exception as e:  # noqa: BLE001 - a crash fails the scenario, never the run
        out.outcome, out.info = "failed", f"raised {type(e).__name__}: {e}"
    finally:
        _close(store)
    return out


def run_suite(factory: Factory, *, only: str | Iterable[str] | None = None,
              capabilities: Iterable[str] | None = None) -> tuple[list[Outcome], dict[str, Any], frozenset[str]]:
    """Every selected scenario, in code-point id order: (outcomes, the store's ``info()``, the flags tested)."""
    s = suite()
    probe = factory(s.schema, ScenarioClock())
    try:
        info = dict(probe.info())
    finally:
        _close(probe)
    declared = frozenset(info["capabilities"])
    flags = declared if capabilities is None else declared & _capabilities(capabilities)
    outcomes = [run_scenario(factory, s.scenarios[i], capabilities=flags, s=s) for i in select(s.scenarios, only)]
    return outcomes, info, flags
