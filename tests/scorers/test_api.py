"""The scorers' public surface (DESIGN §9.2, §10.2): the §1.3 import line, the configurations with their defaults,
and the documented signatures (keyword-only arguments included). The memory scorer's tests belong to step W11a."""
from __future__ import annotations

import dataclasses
import inspect
import subprocess
import sys

import khg_contracts
from khg_contracts import scorers
from khg_contracts.scorers import completion, extraction, memory, retrieval, stability  # the §1.3 import line

Bootstrap = scorers.Bootstrap


def _defaults(cls):
    return {f.name: f.default for f in dataclasses.fields(cls)}


def test_format_and_package():
    assert scorers.FORMAT == "khg-scorers/1.0.0" == "khg-scorers/" + khg_contracts.CONTRACTS["khg-scorers"]
    assert khg_contracts.scorers.completion is completion and khg_contracts.scorers.memory is memory
    assert {"completion", "extraction", "memory", "retrieval", "stability", "bootstrap"} <= set(
        dir(khg_contracts.scorers))


def test_configurations_and_their_defaults():
    assert _defaults(Bootstrap) == {"resamples": 1000, "seed": 0, "alpha": 0.05}
    assert _defaults(extraction.ExtractionConfig) == {
        "preset": None, "literal_match": "truncate_to_gold", "calendar": "strict", "core_roles": "slot",
        "seen": frozenset(), "bootstrap": Bootstrap()}
    assert _defaults(completion.CompletionConfig) == {
        "preset": None, "filter": "exact", "rank": "tie_exact", "hits": (1, 3, 10), "ece_bins": 15,
        "min_bin_queries": 100, "bootstrap": Bootstrap()}
    assert _defaults(retrieval.RetrievalConfig) == {
        "ks": (1, 3, 5, 10, 20), "headline_k": 10, "ndcg_discount": "log2", "answer_mode": "single",
        "bootstrap": Bootstrap()}
    for cls in (Bootstrap, extraction.ExtractionConfig, completion.CompletionConfig, retrieval.RetrievalConfig):
        assert cls.__dataclass_params__.frozen


def _params(fn):
    return {n: (p.kind.name, p.default) for n, p in inspect.signature(fn).parameters.items()}


def test_the_documented_signatures():
    kw = "KEYWORD_ONLY"
    e = _params(extraction.score)
    assert list(e)[:2] == ["gold", "predictions"] and e["schema"][0] == kw and e["config"][0] == kw
    s = _params(stability.score)
    assert s["unit"] == (kw, "run") and s["keys"] == (kw, ("content_key", "core_key")) and s["gold"] == (kw, None)
    b = _params(completion.build_queries)
    assert list(b)[:2] == ["facts", "schema"]
    assert b["slots"] == (kw, ("core", "qualifier")) and b["literal_targets"] == (kw, "exclude")
    assert b["universe"] == (kw, "entities_of_type")
    r = _params(completion.rank_stats)
    assert list(r)[:3] == ["query", "scores", "index"]
    assert all(r[n] == (kw, None) for n in ("universe", "target_prob", "top1", "prob_map", "model_rank"))
    c = _params(completion.score)
    assert list(c)[:2] == ["queries", "outputs"] and c["config"][0] == kw
    assert _params(completion.FilterIndex.from_records)["splits"][0] == "VAR_POSITIONAL"
    q = _params(retrieval.score)
    assert list(q)[:2] == ["questions", "responses"] and q["facts"] == (kw, None) and q["config"][0] == kw


def test_importing_the_scorers_loads_nothing_heavy():
    code = ("import sys\nfrom khg_contracts.scorers import completion, extraction, retrieval, stability\n"
            "print(sorted(m for m in sys.modules if m.split('.')[0] in "
            "('scipy', 'numpy', 'pandas', 'xgi', 'hypernetx')))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"
