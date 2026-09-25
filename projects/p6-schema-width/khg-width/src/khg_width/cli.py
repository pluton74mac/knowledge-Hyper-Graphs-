"""``khg-width SCHEMA_FILE [--slots core,qualifier[,time]] [--time-limit SECONDS]
[--solver auto|python|balancedgo|logk] [--json]`` (DESIGN §4.3, F4).

Exit status, as khg-contracts' commands:

- **0** a report is produced, whatever the class (a cyclic schema is flagged by its class and witness);
- **1** the schema is invalid: every ``load_schema`` error finding is printed (M, or J/V for malformed JSON or format);
- **2** a usage or I/O error: a missing or unreadable file, ``--slots`` with ``meta`` or without ``core``, a bad
  limit, a requested solver that is missing.

``python -m khg_width`` runs the same command.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, NoReturn, Sequence

__all__ = ["main", "OK", "INVALID", "USAGE"]

OK, INVALID, USAGE = 0, 1, 2


class _Exit(Exception):
    def __init__(self, status: int):
        super().__init__(status)
        self.status = status


class _Parser(argparse.ArgumentParser):
    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if message:
            sys.stderr.write(message)
        raise _Exit(status)


def _parser() -> _Parser:
    p = _Parser(prog="khg-width", allow_abbrev=False,
                description="Acyclicity class (Berge, gamma, beta, alpha, cyclic) with a witness, and hw, ghw, fhw and "
                            "tw (exact or bounded, each with a validated decomposition) of a khg-relation-schema/1.0.0 "
                            "file (.json or .json.gz).",
                epilog="Exit status: 0 when a report is produced (whatever the class), 1 when the schema is invalid, "
                       "2 on a usage or I/O error.")
    p.add_argument("schema", metavar="SCHEMA_FILE", help="a relation-type schema, .json or .json.gz")
    p.add_argument("--slots", default="core,qualifier",
                   help="slots whose usages enter H: core,qualifier (default) or core,qualifier,time; meta is refused")
    p.add_argument("--time-limit", dest="time_limit", default="60", metavar="SECONDS",
                   help="limit of each step: a DP, a clique enumeration, an induced search, an hw-search level or a "
                        "solver call at one k (default 60)")
    p.add_argument("--solver", default="auto", choices=("auto", "python", "balancedgo", "logk"),
                   help="auto: BalancedGo with log-k-decomp as second opinion when found, else Python; python: no "
                        "tool; balancedgo or logk: that tool alone (exit 2 when missing)")
    p.add_argument("--json", action="store_true", help="print the WidthReport as JSON")
    return p


def _finding(f: dict[str, Any]) -> str:
    line = f"{f.get('severity', 'error')} {f.get('code', '')}"
    if f.get("path"):
        line += f" at {f['path']}"
    msg = str(f.get("message") or "").replace("\n", " ")
    return f"{line}: {msg}" if msg else line


def main(argv: Sequence[str] | None = None) -> int:
    from .check import check
    from .hypergraph import SchemaInvalid, UsageError, check_slots

    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except _Exit as e:
        return e.status
    try:
        slots = check_slots(args.slots)
        try:
            limit = float(args.time_limit)
        except ValueError:
            raise UsageError(f"--time-limit {args.time_limit!r} is not a number") from None
        report = check(args.schema, slots=slots, time_limit=limit, solver=args.solver)
    except UsageError as e:
        sys.stderr.write(f"khg-width: {e}\n")
        return USAGE
    except SchemaInvalid as e:
        errors = [f for f in e.findings if f.get("severity", "error") == "error"]
        for f in errors or e.findings:
            sys.stdout.write(f"{args.schema}: {_finding(f)}\n")
        sys.stdout.write(f"{args.schema}: invalid ({len(errors)} error finding(s))\n")
        return INVALID
    except OSError as e:
        sys.stderr.write(f"khg-width: cannot read {args.schema}: {e.strerror or e}\n")
        return USAGE
    if args.json:
        sys.stdout.write(json.dumps(report.to_json(), ensure_ascii=False, indent=1) + "\n")
    else:
        sys.stdout.write(report.text() + "\n")
    return OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
