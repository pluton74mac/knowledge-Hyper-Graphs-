"""P6 probe: fetch Wikidata's property schemas (datatype, qualifier constraints, type constraints, usage counts).

Runs a fixed list of SPARQL queries against the Wikidata Query Service, one at a time, with a descriptive
User-Agent and a retry on HTTP 429 / 5xx (honouring Retry-After), and fetches three DeltaBot usage-count
templates through index.php?action=raw. Everything is saved exactly as returned under

    datasets/knowledge-bases/wikidata-property-schemas/raw/

(gitignored), and MANIFEST.json beside it (tracked) records every query text, URL, retrieval time, byte count
and sha256.

Run from the repository root:  python projects/p6-schema-width/research/probes/wd_fetch.py [--only NAME ...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import http.client
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "datasets" / "knowledge-bases" / "wikidata-property-schemas"
RAW = OUT / "raw"
UA = ("khg-kb-research/0.2 (P6 schema width survey, low volume, one query at a time; "
      "https://github.com/pluton74mac/knowledge-Hyper-Graphs-) python-urllib")
WDQS = "https://query.wikidata.org/sparql"
RAW_PAGE = "https://www.wikidata.org/w/index.php?title={title}&action=raw"
API = "https://www.wikidata.org/w/api.php"

PREFIX = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX wdno: <http://www.wikidata.org/prop/novalue/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

# name -> query body. Each constraint query returns one row per (statement, parameter value) and keeps the
# statement's rank and constraint status so that deprecated or suggestion-only constraints can be filtered later.
QUERIES: dict[str, str] = {
    "properties": """
SELECT ?p ?type ?label WHERE {
  ?p wikibase:propertyType ?type .
  OPTIONAL { ?p rdfs:label ?label . FILTER(LANG(?label) = "en") }
}""",
    "property_instance_of": """
SELECT ?p ?class ?classLabel WHERE {
  ?p wikibase:propertyType ?type ; wdt:P31 ?class .
  OPTIONAL { ?class rdfs:label ?classLabel . FILTER(LANG(?classLabel) = "en") }
}""",
    "allowed_qualifiers": """
SELECT ?p ?st ?rank ?q ?novalue ?status WHERE {
  ?p p:P2302 ?st .
  ?st ps:P2302 wd:Q21510851 ; wikibase:rank ?rank .
  OPTIONAL { ?st pq:P2306 ?q }
  OPTIONAL { ?st a wdno:P2306 . BIND(true AS ?novalue) }
  OPTIONAL { ?st pq:P2316 ?status }
}""",
    "required_qualifiers": """
SELECT ?p ?st ?rank ?q ?status WHERE {
  ?p p:P2302 ?st .
  ?st ps:P2302 wd:Q21510856 ; wikibase:rank ?rank .
  OPTIONAL { ?st pq:P2306 ?q }
  OPTIONAL { ?st pq:P2316 ?status }
}""",
    "subject_type_constraints": """
SELECT ?p ?st ?rank ?class ?rel ?status WHERE {
  ?p p:P2302 ?st .
  ?st ps:P2302 wd:Q21503250 ; wikibase:rank ?rank .
  OPTIONAL { ?st pq:P2308 ?class }
  OPTIONAL { ?st pq:P2309 ?rel }
  OPTIONAL { ?st pq:P2316 ?status }
}""",
    "value_type_constraints": """
SELECT ?p ?st ?rank ?class ?rel ?status WHERE {
  ?p p:P2302 ?st .
  ?st ps:P2302 wd:Q21510865 ; wikibase:rank ?rank .
  OPTIONAL { ?st pq:P2308 ?class }
  OPTIONAL { ?st pq:P2309 ?rel }
  OPTIONAL { ?st pq:P2316 ?status }
}""",
    "property_scope": """
SELECT ?p ?st ?rank ?scope ?status WHERE {
  ?p p:P2302 ?st .
  ?st ps:P2302 wd:Q53869507 ; wikibase:rank ?rank .
  OPTIONAL { ?st pq:P5314 ?scope }
  OPTIONAL { ?st pq:P2316 ?status }
}""",
}

# Wikidata's own qualifier classes (restrictive Q61719275, non-restrictive Q61719274, either Q122233685, generic
# Wikidata qualifier Q15720608) and source properties (Q18608359), closed under subclass of (P279).
QUERIES["qualifier_classes"] = """
SELECT ?p ?kind WHERE {
  VALUES ?kind { wd:Q61719275 wd:Q61719274 wd:Q122233685 wd:Q15720608 wd:Q18608359 wd:Q113558322 }
  ?p wikibase:propertyType ?t ; wdt:P31/wdt:P279* ?kind .
}"""

# Observed qualifier usage on a few high-use properties. A full GROUP BY over all statements of these properties
# times out on WDQS (HTTP 504 / Blazegraph TimeoutException on 2026-09-24), and so does a single
# (property, qualifier) COUNT. So: the exact statement count (a fast range count), plus four slices of 20,000
# statements each at fixed offsets of the p:Pxx index (index order, not a random sample), with the query optimiser
# off so that Blazegraph evaluates the slice first. Main graph only (scholarly articles are served separately).
USAGE_SAMPLE = ["P39", "P69", "P108", "P166", "P54"]
USAGE_OFFSETS = [0, 450000, 900000, 1350000]
USAGE_SLICE = 20000
for _p in USAGE_SAMPLE:
    QUERIES[f"usage_{_p}_statements"] = f"""
SELECT (COUNT(*) AS ?statements) WHERE {{ ?item p:{_p} ?st . }}"""
    for _o in USAGE_OFFSETS:
        QUERIES[f"usage_{_p}_slice{_o}"] = f"""
PREFIX hint: <http://www.bigdata.com/queryHints#>
SELECT ?q (COUNT(*) AS ?snaks) (COUNT(DISTINCT ?st) AS ?statements) WHERE {{
  hint:Query hint:optimizer "None" .
  {{ SELECT ?st WHERE {{ ?item p:{_p} ?st }} OFFSET {_o} LIMIT {USAGE_SLICE} }}
  ?st ?pq ?v .
  ?q wikibase:qualifier ?pq .
}} GROUP BY ?q"""

# Plain HTTP sources other than Wikidata itself.
HTTP = {
    "sqid-properties.json": "https://sqid.toolforge.org/data/properties.json",
    "sqid-statistics.json": "https://sqid.toolforge.org/data/statistics.json",
}

TEMPLATES = {
    "usage_main_statements": "Template:Number_of_main_statements_by_property",
    "usage_as_qualifier": "Template:Number_of_qualifiers_by_property",
    "usage_in_references": "Template:Number_of_references_by_property",
}


def _get(req: urllib.request.Request, tries: int = 6) -> bytes:
    delay = 10.0
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                wait = float(e.headers.get("Retry-After") or delay)
                print(f"  HTTP {e.code}; retrying in {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
                delay *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError, http.client.IncompleteRead) as e:
            if attempt < tries - 1:
                print(f"  {e!r}; retrying in {delay:.0f}s", file=sys.stderr)
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("unreachable")


def sparql(query: str) -> bytes:
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(WDQS, data=data, method="POST", headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"})
    return _get(req)


def page_revision(title: str) -> dict:
    q = urllib.parse.urlencode({"action": "query", "prop": "revisions", "rvprop": "ids|timestamp|user",
                                "titles": title, "format": "json", "formatversion": "2"})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    page = json.loads(_get(req))["query"]["pages"][0]
    return page["revisions"][0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="fetch only these names")
    ap.add_argument("--force", action="store_true", help="re-fetch files that already exist")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    man_path = OUT / "MANIFEST.json"
    manifest = json.loads(man_path.read_text()) if man_path.exists() else {
        "name": "wikidata-property-schemas",
        "family": "knowledge-bases",
        "source_url": WDQS,
        "source_ref": "live Wikidata Query Service (main graph) and Wikidata templates; see per-file retrieved and revid",
        "retrieved": dt.date.today().isoformat(),
        "licence": "CC0-1.0 (Wikidata structured data and the DeltaBot count templates' data; "
                   "https://www.wikidata.org/wiki/Wikidata:Copyright)",
        "files": [],
        "notes": "",
    }
    files = {f["path"]: f for f in manifest["files"]}

    def save() -> None:
        manifest["files"] = sorted(files.values(), key=lambda f: f["path"])
        man_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")

    def mtime(path: Path) -> str:
        return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")

    wanted = set(args.only or list(QUERIES) + list(TEMPLATES) + list(HTTP))
    for name, body in QUERIES.items():
        if name not in wanted:
            continue
        path = RAW / f"{name}.srj.json"
        took = None
        if path.exists() and not args.force:
            blob = path.read_bytes()
            print(f"SPARQL {name}: kept existing file", file=sys.stderr)
        else:
            print(f"SPARQL {name} ...", file=sys.stderr)
            t0 = time.time()
            blob = sparql(PREFIX + body)
            took = round(time.time() - t0, 1)
            json.loads(blob)  # fail loudly on a truncated body
            path.write_bytes(blob)
            time.sleep(5)
        rows = len(json.loads(blob)["results"]["bindings"])
        files[f"raw/{path.name}"] = {
            "path": f"raw/{path.name}", "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
            "rows": rows, "retrieved": mtime(path), "source_url": WDQS,
            "method": "POST, Accept: application/sparql-results+json", "query": PREFIX + body, "seconds": took}
        print(f"  {rows} rows, {len(blob)} bytes, {took}s", file=sys.stderr)
        save()
    for name, url in HTTP.items():
        if name not in wanted:
            continue
        path = RAW / name
        if not path.exists() or args.force:
            print(f"GET {url} ...", file=sys.stderr)
            path.write_bytes(_get(urllib.request.Request(url, headers={"User-Agent": UA})))
        blob = path.read_bytes()
        files[f"raw/{name}"] = {"path": f"raw/{name}", "sha256": hashlib.sha256(blob).hexdigest(),
                                "bytes": len(blob), "retrieved": mtime(path), "source_url": url,
                                "licence": "SQID statistics derived from Wikidata dumps (CC0-1.0); tool "
                                           "https://sqid.toolforge.org, code Apache-2.0 [unverified]"}
        if name == "sqid-statistics.json":
            st = json.loads(blob)
            files[f"raw/{name}"]["sqid_dumpDate"] = st.get("dumpDate")
            files[f"raw/{name}"]["sqid_propertyUpdate"] = st.get("propertyUpdate")
        save()
    for name, title in TEMPLATES.items():
        if name not in wanted:
            continue
        path = RAW / f"{name}.wikitext"
        if path.exists() and not args.force and f"raw/{path.name}" in files:
            continue
        print(f"template {title} ...", file=sys.stderr)
        rev = page_revision(title)
        url = RAW_PAGE.format(title=title) + f"&oldid={rev['revid']}"
        blob = _get(urllib.request.Request(url, headers={"User-Agent": UA}))
        path.write_bytes(blob)
        files[f"raw/{path.name}"] = {
            "path": f"raw/{path.name}", "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
            "retrieved": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source_url": url, "page": title, "revid": rev["revid"], "rev_timestamp": rev["timestamp"],
            "rev_user": rev["user"]}
        save()
        time.sleep(2)
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
