"""``khg-bakeoff``: the conformance and fidelity runs of P1's first half (DESIGN §4, §5).

    khg-bakeoff conformance [BACKEND ...] [--out DIR]     # EARL reports, summary.json, summary.md
    khg-bakeoff fidelity [BACKEND ...] [--out DIR] [--conformance DIR/summary.json]   # fidelity.json, fidelity.md

``BACKEND`` is one of sqlite, postgres, oxigraph, neo4j, typedb, hif (default: all). The server backends read their
endpoints from ``KHG_BAKEOFF_POSTGRES``, ``KHG_BAKEOFF_NEO4J`` and ``KHG_BAKEOFF_TYPEDB``. Exit 0 when every backend
passes (no applicable scenario failed), 1 otherwise, 2 on a usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .backends import BACKENDS, available
from .provenance import provenance

__all__ = ["main"]

ORDER = ("sqlite", "postgres", "oxigraph", "neo4j", "typedb", "hif")


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def conformance_md(summary: dict[str, Any]) -> str:
    prov = summary["provenance"]
    lines = ["# P1 conformance runs (first half)", "",
             f"khg-contracts {prov['khg_contracts']['version']} at commit `{prov['khg_contracts']['commit']}`; "
             f"{prov['contracts']['C1']}, {prov['contracts']['C2']}, {prov['contracts']['scenarios']} (114 "
             "scenarios); khg-contracts' own runner (`conformance.run`). A backend passes when no applicable "
             "scenario fails (PLAN §7); every inapplicable scenario is a fidelity loss, listed by flag.", "",
             "| Backend | Engine | Kind | Applicable | Passed | Failed | cantTell | Inapplicable (losses) | Passes |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, b in summary["backends"].items():
        lines.append(f"| {name} | {b['engine']} {b['version']} | {b['kind']} | {b['applicable']} | {b['passed']} | "
                     f"{b['failed']} | {b['cantTell']} | {b['inapplicable']} | {'yes' if b['passes'] else 'no'} |")
    lines += ["", "## Losses by flag", ""]
    for name, b in summary["backends"].items():
        if not b["losses_by_flag"]:
            lines.append(f"- **{name}**: none.")
            continue
        lines.append(f"- **{name}** (flags declared absent: {', '.join(b['absent_flags'])}):")
        for flag, ids in b["losses_by_flag"].items():
            lines.append(f"  - `{flag}` ({len(ids)}): {', '.join(ids)}")
    return "\n".join(lines) + "\n"


def _pct(kept: int, total: int) -> str:
    return "–" if total == 0 else f"{kept}/{total}"


def fidelity_md(result: dict[str, Any]) -> str:
    prov = result["provenance"]
    lines = ["# P1 fidelity (first half)", "",
             f"khg-contracts {prov['khg_contracts']['version']} at commit `{prov['khg_contracts']['commit']}`; "
             f"{prov['contracts']['C1']}, {prov['contracts']['C2']}. Data sets: P2's `fixture.c1.json` (40 records) "
             "and `fixture.history.c1.json` (10 versions), and P1's `fixtures/edge.c1.json` (41 records). The four "
             "numbers of research 01 D5 (DESIGN §5); number 3 on the hand queries only (the query set is frozen in "
             "the second half). No timings.", "",
             "**1. Container round trip**: records that differ after `load(on_missing=\"skip\")` → `export`, as "
             "skipped/silent, per data set (fixture, history, edge); store fields that differ from `MemoryStore` "
             "holding the same records. **2. Native layer** (fixture; edge): bids, literals as written, "
             "positions, extensions and role–value multisets kept without the record-level copies. **3. Answers**: "
             "same as `MemoryStore` / compared (fixture hand queries; history transaction-time checks; edge "
             "queries). **4. Inapplicable scenarios** (losses by flag, from the conformance run).", "",
             "| Backend | Engine | Kind | 1. Round trip: fixture / history / edge | 1. Store fields: fixture / history / edge | "
             "2. Native: bids, literals, positions, extensions, multisets (fixture; edge) | "
             "3. Answers: fixture / history / edge | 4. Inapplicable |",
             "|---|---|---|---|---|---|---|---|"]
    for name, b in result["backends"].items():
        ds = b["datasets"]
        rt, store_fields, nat, ans = [], [], [], []
        for d in ("fixture", "history", "edge"):
            e = ds.get(d, {})
            if not e.get("loaded"):
                rt.append("not loaded (no history_export)")
                store_fields.append("–")
                ans.append("–")
                continue
            r = e["round_trip"]
            rt.append(f"{r['skipped']} skipped, {len(r['other_differences'])} silent")
            store_fields.append(str(len(r["store_field_differences"])))
            ans.append(f"{e['answers']['same']}/{e['answers']['compared']}")
            if d != "history":
                n = e["native"]
                nat.append(", ".join([_pct(n["bid_kept"], n["bindings"]), _pct(n["literal_as_written_kept"],
                                                                               n["literals"]),
                                      _pct(n["position_kept"], n["positions"]),
                                      _pct(n["extensions_kept"], n["extensions"]),
                                      _pct(n["multiset_kept"], n["facts"])]))
        inap = b.get("conformance", {})
        losses = inap.get("losses_by_flag") or {}
        four = f"{inap.get('inapplicable', '?')}" + (f" ({', '.join(f'{k} {len(v)}' for k, v in losses.items())})"
                                                     if losses else "")
        lines.append(f"| {name} | {b['engine']} {b['version']} | {b['kind']} | {' / '.join(rt)} | "
                     f"{' / '.join(store_fields)} | "
                     f"{'; '.join(nat)} | {' / '.join(ans)} | {four} |")
    lines += ["", "## What each backend lost", ""]
    for name, b in result["backends"].items():
        lines.append(f"### {name}")
        lines.append("")
        any_loss = False
        for d, e in b["datasets"].items():
            if not e.get("loaded"):
                lines.append(f"- {d}: not loaded: {e['reason']} ({e['records_in']} versions).")
                any_loss = True
                continue
            r = e["round_trip"]
            for rid, why in r["skip_reasons"].items():
                any_loss = True
                lines.append(f"- {d}: `{rid}` skipped: {json.dumps(why, ensure_ascii=False)}")
            for path in r["other_differences"]:
                any_loss = True
                lines.append(f"- {d}: `{path}` differs after the round trip")
            if r["store_field_differences"]:
                any_loss = True
                fields = sorted({f for fs in r["store_field_differences"].values() for f in (fs or [])})
                lines.append(f"- {d}: store fields differ from `MemoryStore` on {len(r['store_field_differences'])} "
                             f"records ({', '.join(fields)})")
            for kind, where in e.get("native", {}).get("lost", {}).items():
                any_loss = True
                lines.append(f"- {d}, native layer: {kind} lost on {len(where)}: {', '.join(where)}")
            for label, diff in e["answers"].get("differ", {}).items() if isinstance(e["answers"].get("differ"),
                                                                                    dict) else []:
                any_loss = True
                lines.append(f"- {d}, answer differs: {label}")
            for label in e["answers"].get("differ", []) if isinstance(e["answers"].get("differ"), list) else []:
                any_loss = True
                lines.append(f"- {d}, answer differs: {label}")
        if not any_loss:
            lines.append("- nothing.")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="khg-bakeoff", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("conformance", "fidelity"):
        p = sub.add_parser(cmd)
        p.add_argument("backends", nargs="*", metavar="BACKEND")
        p.add_argument("--out", type=Path, default=None)
        if cmd == "fidelity":
            p.add_argument("--conformance", type=Path, default=None,
                           help="summary.json of a conformance run, for number 4")
    args = parser.parse_args(argv)
    names = args.backends or [n for n in ORDER if available(n)]
    unknown = [n for n in names if n not in BACKENDS]
    if unknown:
        parser.error(f"unknown backends {unknown}; the backends are {', '.join(ORDER)}")
    missing = [n for n in names if not available(n)]
    if missing:
        parser.error(f"not available here (client or endpoint missing): {', '.join(missing)}")
    if args.command == "conformance":
        from . import conformance

        summary = conformance.run(names, args.out)
        if args.out is not None:
            _write_json(args.out / "summary.json", summary)
            (args.out / "summary.md").write_text(conformance_md(summary), encoding="utf-8")
        for name, b in summary["backends"].items():
            print(f"{name}: applicable {b['applicable']}, passed {b['passed']}, failed {b['failed']}, "
                  f"cantTell {b['cantTell']}, inapplicable {b['inapplicable']}")
        return 0 if all(b["passes"] for b in summary["backends"].values()) else 1
    from khg_contracts.store import ScenarioClock

    from . import fidelity
    from .backends import factory

    conf = json.loads(args.conformance.read_text(encoding="utf-8"))["backends"] if args.conformance else {}
    result: dict[str, Any] = {"provenance": provenance(), "backends": {}}
    for name in names:
        probe = factory(name)(fidelity.load_schema(fidelity.datasets()["fixture"][1]), ScenarioClock())
        try:
            engine = probe.engine()
        finally:
            probe.close()
        c = conf.get(name, {})
        result["backends"][name] = {
            "backend": name, "layout": BACKENDS[name].layout, **engine,
            "datasets": fidelity.measure(name),
            "conformance": {k: c.get(k) for k in ("applicable", "passed", "failed", "inapplicable", "losses_by_flag")}
            if c else {}}
        print(f"{name}: measured")
    if args.out is not None:
        _write_json(args.out / "fidelity.json", result)
        (args.out / "fidelity.md").write_text(fidelity_md(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
