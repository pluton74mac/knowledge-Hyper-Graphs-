"""Re-wrap prose items (paragraphs or list items) that have a line longer than WIDTH, in the doc-*.md templates.

Code blocks, tables, headings and placeholder lines are left alone. Used only to tidy the design text."""
import re
import sys
import textwrap

WIDTH = 116
ITEM = re.compile(r"^(- |\d+\. )")


def items_of(par):
    out = []
    for ln in par:
        if ITEM.match(ln) or not out:
            out.append([ln])
        else:
            out[-1].append(ln)
    return out


def rewrap(item):
    m = ITEM.match(item[0])
    lead = m.group(1) if m else ""
    indent = " " * len(lead) if m else ""
    words = " ".join(ln.strip() if i else ln[len(lead):].strip() for i, ln in enumerate(item))
    return textwrap.wrap(words, width=WIDTH, initial_indent=lead, subsequent_indent=indent,
                         break_long_words=False, break_on_hyphens=False)


def fix(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    out, par, code, changed = [], [], False, 0

    def flush():
        nonlocal changed
        for it in items_of(par):
            if any(len(ln) > WIDTH for ln in it):
                out.extend(rewrap(it))
                changed += 1
            else:
                out.extend(it)
        par.clear()

    for ln in lines:
        if ln.startswith("```"):
            flush()
            code = not code
            out.append(ln)
            continue
        if code or not ln.strip() or ln.startswith(("|", "#", "<<", "---")):
            flush()
            out.append(ln)
            continue
        par.append(ln)
    flush()
    open(path, "w", encoding="utf-8").write("\n".join(out))
    return changed


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, fix(p))
