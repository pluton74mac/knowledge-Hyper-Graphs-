# Tools

Utilities for maintaining the knowledge base. Pure Python 3, no dependencies.

| Script | Purpose |
|---|---|
| `validate_kb.py` | Check front matter, allowed `type`/`status` values, `## Sources` sections, and relative links across `kb/`. Run `python tools/validate_kb.py` (add `--strict` to fail on warnings). |
| `build_index.py` | Regenerate `kb/00-index/map-of-content.md` from the front matter of every note. |
| `merge_sources.py` | Merge `sources/by-topic/*.md` into a deduplicated `sources/bibliography.md`. |

Planned: converters between HIF, RDF-star, and TypeQL for the sample files in `schemas/`; a link
checker for external URLs; a script that lists notes whose `status` is still `draft`.
