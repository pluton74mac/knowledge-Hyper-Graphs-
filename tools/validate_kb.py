#!/usr/bin/env python3
"""Validate the knowledge base.

Checks, for every Markdown file under kb/:
  * YAML front matter is present and has the required keys
  * `status` and `type` use allowed values
  * relative Markdown links resolve to existing files
  * a `## Sources` section exists for content notes (not README.md)

Usage:  python tools/validate_kb.py [--strict]
Exit code 1 when problems are found (with --strict also on warnings).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "kb"
REQUIRED = {"title", "type", "status", "tags", "created", "updated"}
TYPES = {"concept", "survey", "tool", "paper-note", "dataset", "timeline",
         "comparison", "question", "howto", "index", "glossary", "log", "project"}
STATUSES = {"draft", "reviewed", "stable"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def front_matter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    block = text[4:end]
    data: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            data[k.strip()] = v.strip()
    return data


def main(strict: bool) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    files = sorted(KB.rglob("*.md"))
    for f in files:
        rel = f.relative_to(ROOT)
        text = f.read_text(encoding="utf-8", errors="replace")
        fm = front_matter(text)
        if fm is None:
            errors.append(f"{rel}: missing front matter")
        else:
            missing = REQUIRED - fm.keys()
            if missing:
                errors.append(f"{rel}: front matter missing {sorted(missing)}")
            if fm.get("type") and fm["type"] not in TYPES:
                warnings.append(f"{rel}: unknown type '{fm['type']}'")
            if fm.get("status") and fm["status"] not in STATUSES:
                errors.append(f"{rel}: unknown status '{fm['status']}'")
        if f.name != "README.md" and "## Sources" not in text and "## sources" not in text.lower():
            warnings.append(f"{rel}: no '## Sources' section")
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0]
            if not path:
                continue
            resolved = (f.parent / path).resolve()
            if not resolved.exists():
                errors.append(f"{rel}: broken link -> {target}")
    print(f"checked {len(files)} files: {len(errors)} errors, {len(warnings)} warnings")
    for e in errors:
        print("ERROR  ", e)
    for w in warnings:
        print("WARN   ", w)
    if errors or (strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--strict" in sys.argv))
