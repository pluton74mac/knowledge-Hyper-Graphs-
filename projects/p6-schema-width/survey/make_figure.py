"""The survey figure (DESIGN §6.6): ``figure-widths.svg`` and ``.png`` from ``figure-data.csv``, deterministically.

(a) hw per non-control row: a point when exact, an interval bar from the lower to the upper bound when not, on a
    log scale; beside it, on the same hw axis, the shares of HyperBench's non-random CQs with hw 1, 2 and 3.
(b) GYO residue size (relations) per Wikidata source and slot set, a dot plot on a log scale.

Colours: the dataviz reference palette's first three categorical slots (validated all-pairs, light mode); the
aqua slot sits below 3:1 on the surface, so its bars carry direct labels, and ``survey.csv`` is the table view.
Exactness is encoded by mark shape too (point vs interval), not by colour alone.

    python make_figure.py [--out RESULTS]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"


def _label(r: dict) -> str:
    slots = "cq" if r["slots"] == "core,qualifier" else "cq+time"
    if r["group"] == "wikidata":
        return f"{r['table'].replace('observed-', 'obs-')}\n{slots}"
    return f"BL {r['table'].replace('formal-domain', 'formal+dom.')}\n{slots}"


def _num(x: str) -> float:
    from fractions import Fraction

    return float(Fraction(x))


def make(out: Path) -> tuple[Path, Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"svg.hashsalt": "khg-width-p6", "font.family": "DejaVu Sans", "font.size": 9,
                         "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "text.color": INK, "figure.facecolor": SURFACE,
                         "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})
    with open(out / "figure-data.csv", newline="", encoding="utf-8") as fh:
        data = list(csv.DictReader(fh))
    rows = [r for r in data if r["group"] in ("wikidata", "biolink") and r["control"] == "False"]
    hb = [r for r in data if r["group"] == "hyperbench"]

    fig = plt.figure(figsize=(9.5, 7.0))
    gs = fig.add_gridspec(2, 2, width_ratios=[4, 1], height_ratios=[1.2, 1], hspace=0.55, wspace=0.06,
                          left=0.09, right=0.97, top=0.94, bottom=0.07)
    ax = fig.add_subplot(gs[0, 0])
    axh = fig.add_subplot(gs[0, 1], sharey=ax)
    axr = fig.add_subplot(gs[1, :])

    # (a) hw per row
    for i, r in enumerate(rows):
        color = BLUE if r["group"] == "wikidata" else ORANGE
        lo, hi = _num(r["hw_lower"]), _num(r["hw_upper"])
        if r["hw_exact"] == "True":
            ax.plot([i], [hi], marker="o", ms=7, color=color, mec=SURFACE, mew=1.5, zorder=3)
        else:
            ax.vlines(i, lo, hi, color=color, lw=2, zorder=2)
            ax.plot([i, i], [lo, hi], marker="_", ms=10, mew=2, color=color, ls="none", zorder=3)
    ax.set_yscale("log")
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([_label(r) for r in rows], fontsize=7)
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.set_ylabel("hypertree width (log scale)")
    ax.set_title("(a) hw per schema: point = exact, bar = [lower, upper]", loc="left", fontsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    from matplotlib.lines import Line2D

    ax.legend(handles=[Line2D([], [], marker="o", color=BLUE, ls="none", label="Wikidata (wd-roles r1)"),
                       Line2D([], [], marker="o", color=ORANGE, ls="none", label="Biolink v4.4.5 (global)")],
              frameon=False, fontsize=7, loc="upper right")
    # HyperBench CQ shares on the same hw axis
    total = sum(float(r["residue_relations"]) for r in hb) or 1.0
    for r in hb:
        k = float(r["hw_upper"])
        share = float(r["residue_relations"]) / total
        axh.barh(k, share, height=0.18 * k, color=AQUA, edgecolor=SURFACE, lw=2)
        axh.text(share + 0.02, k, f"{share:.1%}", va="center", fontsize=7, color=INK)
    axh.set_xlim(0, 1.25)
    axh.set_xlabel("share of CQs", fontsize=8)
    axh.set_title("HyperBench CQs", loc="left", fontsize=9)
    axh.tick_params(axis="y", labelleft=False)
    for s in ("top", "right"):
        axh.spines[s].set_visible(False)

    # (b) residue size per Wikidata table and slot set
    wd = [r for r in data if r["group"] == "wikidata" and r["control"] == "False"]
    tables = []
    for r in wd:
        if r["table"] not in tables:
            tables.append(r["table"])
    # a dot plot: bars on a log axis would have no true baseline
    for j, (slots, color, label) in enumerate((("core,qualifier", BLUE, "core,qualifier"),
                                               ("core,qualifier,time", ORANGE, "core,qualifier,time"))):
        xs, ys = [], []
        for i, t in enumerate(tables):
            m = [r for r in wd if r["table"] == t and r["slots"] == slots]
            if m:
                xs.append(i + (j - 0.5) * 0.24)
                ys.append(float(m[0]["residue_relations"]))
        if not xs:
            continue
        axr.plot(xs, ys, ls="none", marker="o", ms=8, color=color, mec=SURFACE, mew=1.5, label=label, zorder=3)
        for x, y in zip(xs, ys):
            axr.text(x, y * 1.12, f"{int(y):,}", ha="center", fontsize=7, color=INK)
    axr.set_yscale("log")
    axr.set_xticks(range(len(tables)))
    axr.set_xticklabels(tables)
    axr.set_xlim(-0.6, max(2, len(tables)) - 0.4)
    lo = min((float(r["residue_relations"]) for r in wd if float(r["residue_relations"]) > 0), default=1.0)
    hi = max((float(r["residue_relations"]) for r in wd), default=10.0)
    axr.set_ylim(lo / 2, hi * 2)
    axr.set_ylabel("GYO residue (relations, log)")
    axr.set_title("(b) cyclic core of the Wikidata schemas (wd-roles r1)", loc="left", fontsize=9)
    axr.grid(axis="y", color=GRID, lw=0.8)
    axr.set_axisbelow(True)
    if axr.get_legend_handles_labels()[0]:
        axr.legend(frameon=False, fontsize=7, loc="upper left")
    for s in ("top", "right"):
        axr.spines[s].set_visible(False)

    svg, png = out / "figure-widths.svg", out / "figure-widths.png"
    fig.savefig(svg, format="svg", metadata={"Date": None, "Creator": None})
    fig.savefig(png, format="png", dpi=200, metadata={"Software": None})
    plt.close(fig)
    return svg, png


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", default=str(HERE.parent / "results"))
    a = p.parse_args(argv)
    svg, png = make(Path(a.out))
    print(svg, png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
