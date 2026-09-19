#!/usr/bin/env python3
"""Merge sources/by-topic/*.md into sources/bibliography.md.

Each by-topic file is a Markdown list or table of sources. This script concatenates them under
per-section headings and lists URLs that appear in more than one section, so cross-cutting
sources are easy to spot. It does not try to parse citation fields.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources" / "by-topic"
OUT = ROOT / "sources" / "bibliography.md"
URL_RE = re.compile(r"https?://[^\s)\]>|]+")


def main() -> None:
    parts = ["# Bibliography", "",
             "Merged from `sources/by-topic/*.md` by `tools/merge_sources.py`. Edit the by-topic files, not this one.", ""]
    seen: dict[str, set[str]] = defaultdict(set)
    for f in sorted(SRC.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for url in URL_RE.findall(text):
            seen[url.rstrip(".,;")].add(f.stem)
        body = re.sub(r"^# .*\n", "", text, count=1).strip()
        parts += [f"## {f.stem}", "", body, ""]
    shared = {u: s for u, s in seen.items() if len(s) > 1}
    parts += ["## Sources cited in more than one section", ""]
    for url, secs in sorted(shared.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        parts.append(f"- {url} — {', '.join(sorted(secs))}")
    parts.append("")
    parts.append(f"_{len(seen)} distinct URLs; {len(shared)} shared across sections._")
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(seen)} urls, {len(shared)} shared")


if __name__ == "__main__":
    main()
