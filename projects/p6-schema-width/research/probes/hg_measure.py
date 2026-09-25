"""P6 probe helpers: statistics and an indexed GYO reduction for schema hypergraphs.

``khg_contracts.schema.is_alpha_acyclic`` is the reference. ``gyo`` below is an independent implementation of the same
two GYO operations (with a vertex -> edges index) used as a cross-check: it must return the same residue.
``crosscheck`` asserts that. (The reference turned out fast enough at 13,608 hyperedges, about 1 s.)
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping


def _edges(hg) -> list[set[str]]:
    if isinstance(hg, Mapping):
        body = hg["hyperedges"] if "hyperedges" in hg else hg
        vals: Iterable = body.values() if isinstance(body, Mapping) else body
    else:
        vals = hg
    return [set(e) for e in vals if e]


def gyo(hg) -> tuple[bool, list[frozenset]]:
    """GYO reduction: repeatedly drop vertices in exactly one hyperedge and hyperedges contained in another
    (one copy of duplicates survives). Alpha-acyclic iff nothing is left."""
    es: dict[int, set[str]] = dict(enumerate(_edges(hg)))
    inc: dict[str, set[int]] = {}
    for i, e in es.items():
        for v in e:
            inc.setdefault(v, set()).add(i)
    dirty_v = set(inc)
    dirty_e = set(es)
    while dirty_v or dirty_e:
        # rule 1: lonely vertices
        while dirty_v:
            v = dirty_v.pop()
            s = inc.get(v)
            if s is not None and len(s) == 1:
                (i,) = s
                es[i].discard(v)
                del inc[v]
                dirty_e.add(i)
        # rule 2: contained edges
        while dirty_e:
            i = dirty_e.pop()
            if i not in es:
                continue
            e = es[i]
            if not e:
                del es[i]
                continue
            rare = min(e, key=lambda v: len(inc[v]))
            cands = set(inc[rare])
            cands.discard(i)
            for v in e:
                if len(cands) == 0:
                    break
                cands &= inc[v]
            # a candidate contains e; keep the lower index among exact duplicates
            sup = [j for j in cands if len(es[j]) > len(e) or j < i]
            if sup:
                for v in e:
                    inc[v].discard(i)
                    if len(inc[v]) <= 1:
                        dirty_v.add(v)
                    for j in inc[v]:
                        dirty_e.add(j)
                del es[i]
            # else e stays. Edges only shrink, so e can become contained later only when e itself shrinks, and
            # rule 1 marks it dirty when it does.
    residue = [frozenset(e) for e in es.values()]
    return len(residue) == 0, residue


def alpha(hg) -> tuple[bool, list[frozenset]]:
    """(acyclic, residue) with khg_contracts' convention: acyclic iff the residue is empty (a last edge's
    vertices are all lonely, so a single edge reduces to nothing)."""
    return gyo(hg)


def components(hg) -> list[int]:
    """Sizes (in hyperedges) of the connected components, largest first."""
    es = _edges(hg)
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in es:
        for v in e:
            parent.setdefault(v, v)
        it = iter(e)
        a = find(next(it))
        for v in it:
            b = find(v)
            if a != b:
                parent[b] = a
    cnt = Counter(find(next(iter(e))) for e in es)
    return sorted(cnt.values(), reverse=True)


def stats(hg) -> dict:
    es = _edges(hg)
    deg = Counter(v for e in es for v in e)
    comps = components(hg)
    return {
        "edges": len(es),
        "vertices": len(deg),
        "max_edge": max((len(e) for e in es), default=0),
        "mean_edge": round(sum(len(e) for e in es) / len(es), 2) if es else 0,
        "components": len(comps),
        "largest_component_edges": comps[0] if comps else 0,
        "universal_vertices": sorted(v for v, d in deg.items() if d == len(es)) if len(es) > 1 else [],
        "top_degree": deg.most_common(8),
    }


def crosscheck(hg) -> bool:
    """Compare with khg_contracts.schema.is_alpha_acyclic (the reference) on the same input."""
    from khg_contracts.schema import is_alpha_acyclic
    ref_ok, ref_res = is_alpha_acyclic(hg)
    ok, res = alpha(hg)
    same = ref_ok == ok and sorted(map(sorted, ref_res)) == sorted(map(sorted, res))
    if not same:
        raise AssertionError(f"GYO mismatch: reference {ref_ok} ({len(ref_res)} edges) vs {ok} ({len(res)} edges)")
    return ok


if __name__ == "__main__":  # textbook cases
    cases = {
        "path": ([{"a", "b"}, {"b", "c"}, {"c", "d"}], True),
        "triangle": ([{"a", "b"}, {"b", "c"}, {"a", "c"}], False),
        "triangle+cover": ([{"a", "b"}, {"b", "c"}, {"a", "c"}, {"a", "b", "c"}], True),
        "4-cycle": ([{"a", "b"}, {"b", "c"}, {"c", "d"}, {"d", "a"}], False),
        "triangle+universal": ([{"s", "a", "b"}, {"s", "b", "c"}, {"s", "a", "c"}], False),
        "duplicates": ([{"a", "b"}, {"a", "b"}, {"b", "c"}], True),
        "single": ([{"a", "b", "c"}], True),
    }
    for name, (es, want) in cases.items():
        got = crosscheck(es)
        assert got == want, (name, got, want)
        print(f"{name}: alpha-acyclic={got} (expected {want})")
