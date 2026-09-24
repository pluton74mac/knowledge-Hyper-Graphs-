"""Differential check (design §8.1): original vs annotated/restructured schemas must accept exactly the same documents.
Corpus = the positive artefacts plus seeded random mutations of them (delete, retype, add a key, swap in
values of other kinds). Validity is compared under jsonschema and fastjsonschema."""
import copy, json, random, sys
from pathlib import Path
import jsonschema, fastjsonschema
from referencing import Registry, Resource

W = Path(__file__).resolve().parent.parent          # the work folder
OLD = Path(__file__).resolve().parent / "original"  # the four schemas before annotation and dispatch refactoring
HIF = json.loads((W / "hif_schema_v0.1.0.json").read_text())
REG = Registry().with_resource(HIF["$id"], Resource.from_contents(HIF))


def handlers():
    return {"https": lambda uri: HIF, "http": lambda uri: HIF}


def validators(path):
    s = json.loads(path.read_text())
    js = jsonschema.Draft7Validator(s, registry=REG)
    fj = fastjsonschema.compile(s, handlers=handlers())
    def fj_ok(x):
        try:
            fj(x); return True
        except fastjsonschema.JsonSchemaException:
            return False
    return (lambda x: js.is_valid(x)), fj_ok


SAMPLES = [None, 0, 1, -1, 1.5, "", "x", "ex:A", "_:ex", "+1643-05-14T00:00:00Z", True, False, [], [1], {}, {"x": 1},
           {"entity": "ex:A"}, {"fact": "f:x"}, {"special": "somevalue"}, {"special": "maybe"}, {"unbound": {"var": "x"}},
           {"entity": "ex:A", "literal": {"datatype": "string", "value": "a"}},
           {"literal": {"datatype": "string", "value": "a"}}, {"literal": {"datatype": "time", "time": "+2020-01-01T00:00:00Z", "precision": 9}},
           {"literal": {"datatype": "quantity", "amount": "+1", "unit": "1"}}, {"literal": {"datatype": "quantity", "amount": "+1", "unit": "1", "lower": "+0"}},
           {"literal": {"datatype": "geo", "lat": "+1", "lon": "+2", "precision": "+0.1", "globe": "wd:Q2"}},
           {"literal": {"datatype": "date"}}, {"literal": "time"}, {"literal": "date"}, {"entity": ["Gene"]}, {"fact": ["regulates"]},
           {"literal": "time", "precision_min": 11}, {"literal": "quantity", "units": ["1"]}, {"precision_min": 3},
           {"entity": [], "literal": "time"}, {"type": "quote", "exact": "a"}, {"type": "position", "start": 0, "end": 3},
           {"type": "quote", "start": 0}, {"type": "requires", "if": "a", "then": ["b"]}, {"type": "excludes", "roles": ["a", "b"]},
           {"type": "requires", "roles": ["a", "b"]}, {"model": "interval", "start": "s", "end": "e"}, {"model": "invariant"},
           {"model": "unstated", "start": "s"}, {"model": "interval"}, "head", "tail", "context", "directed", "asc"]
KEYS = ["x", "role", "roles", "khg:x", "khg:bid", "type", "datatype", "unit", "lower", "upper", "calendar", "precision",
        "unbound", "entity", "literal", "fact", "special", "direction", "model", "start", "end", "if", "then", "roles", "severity",
        "precision_min", "units", "default_attrs", "khg-x", "status_ref", "rank_reason", "closed_reason", "findings"]


def paths(x, pre=()):
    yield pre
    if isinstance(x, dict):
        for k, v in x.items():
            yield from paths(v, pre + (k,))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from paths(v, pre + (i,))


def mutate(doc, rng):
    d = copy.deepcopy(doc)
    ps = [p for p in paths(d) if p]
    p = rng.choice(ps)
    parent = d
    for k in p[:-1]:
        parent = parent[k]
    k = p[-1]
    op = rng.random()
    if op < 0.3 and isinstance(parent, dict):
        parent.pop(k)
    elif op < 0.75:
        parent[k] = copy.deepcopy(rng.choice(SAMPLES))
    else:
        tgt = parent[k]
        if isinstance(tgt, dict):
            tgt[rng.choice(KEYS)] = copy.deepcopy(rng.choice(SAMPLES))
        else:
            parent[k] = copy.deepcopy(rng.choice(SAMPLES))
    return d


def corpus(name):
    j = lambda n: json.loads((W / n).read_text())
    if name == "khg-record-1.0.0":
        return [j("fixture-directed.khg.json"), j("fixture-undirected.khg.json"), j("fixture-directed.canonical.khg.json"),
                j("kb-sample-migrated.khg.json")]
    if name == "khg-hif-1.0.0":
        return [j("fixture-directed.hif.json"), j("fixture-undirected.hif.json")]
    if name == "khg-schema-1.0.0":
        return [j("p2-gate.schema.json"), j("kb-sample.schema.json")]
    if name == "khg-queue-1.0.0":
        q = j("queue-examples.json")
        return [q["item"], q["verdict"]] + q["log"]


def main(n_mut=4000, seed=7):
    rng = random.Random(seed)
    total_bad = 0
    for name in ("khg-record-1.0.0", "khg-hif-1.0.0", "khg-schema-1.0.0", "khg-queue-1.0.0"):
        o_js, o_fj = validators(OLD / f"{name}.schema.json")
        n_js, n_fj = validators(W / f"{name}.schema.json")
        base = corpus(name)
        docs = list(base) + [mutate(rng.choice(base), rng) for _ in range(n_mut)]
        docs += [mutate(mutate(rng.choice(base), rng), rng) for _ in range(n_mut // 2)]
        bad, acc, rej = [], 0, 0
        for d in docs:
            r = (o_js(d), o_fj(d), n_js(d), n_fj(d))
            if len(set(r)) != 1:
                bad.append((r, d))
            acc += r[2]; rej += not r[2]
        total_bad += len(bad)
        print(f"{name}: {len(docs)} documents ({acc} accepted, {rej} rejected); disagreements old/new x jsonschema/fastjsonschema: {len(bad)}")
        for r, d in bad[:3]:
            print("   ", r, json.dumps(d)[:300])
        assert all(o_js(b) and n_js(b) and o_fj(b) and n_fj(b) for b in base), "a positive artefact is rejected"
    print("TOTAL DISAGREEMENTS:", total_bad)
    return total_bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
