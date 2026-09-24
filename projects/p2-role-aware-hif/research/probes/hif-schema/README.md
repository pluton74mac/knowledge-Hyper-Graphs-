# HIF schema probe (P2 research, 2026-09-23)

Vendored copies of every Hypergraph Interchange Format (HIF) JSON Schema snapshot that matters to P2,
a set of edge-case files, and a script that validates them. The findings are written up in
[../../02-hif-standard.md](../../02-hif-standard.md).

## Provenance

Retrieved 2026-09-23 (UTC) with `curl` from `raw.githubusercontent.com`, using commit-pinned URLs.
Every file was then checked against its git blob id with `git hash-object`, and the ids match
the blobs in a full clone of `https://github.com/HIF-org/HIF-standard` at HEAD
`b691a3d2ec32100c0229ebe1151e9afad015c356` (2026-03-19, "Update README.md (#57)").

The repository has had three names: `pszufe/HIF_validators` (original), then `pszufe/HIF-standard`,
then `HIF-org/HIF-standard`. GitHub redirects the older names, so the same bytes are served under
all three owner/name pairs. The commit SHAs below are the same whichever name is used.

| File here | Upstream path @ commit | Commit date | git blob | sha256 |
|---|---|---|---|---|
| `hif_schema.json` | `schemas/hif_schema.json` @ `b691a3d2ec32100c0229ebe1151e9afad015c356` | 2026-03-19 (file last changed 2025-05-02, `6ffdb48`) | `5651f07b93a67b04ec4b5dbe628a57f5c35b0ba0` | `3f49e6cb4bf1ff5c41e6f4bfe95da35d258436aa1ece92e54993e77389c11b2e` |
| `hif_schema_v0.1.0.json` | `schemas/hif_schema_v0.1.0.json` @ `b691a3d2ec32100c0229ebe1151e9afad015c356` | 2026-03-19 (file last changed 2025-05-02, `c8e2d4f`) | `e2105bb87bbb726a86e55433f9db15d91cdcbfe0` | `639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196` |
| `CHANGELOG.upstream.md` | `schemas/CHANGELOG.md` @ `b691a3d…` | 2026-03-19 (file last changed 2025-05-02, `58447e4`) | `cb61bc9bfb660b7f75d57145d45c93f90d699e4c` | `301a4a10a18a0f5f6875650fd3f8544d0e0f7e992b8a27eaabd7bac46c489999` |
| `UPSTREAM-LICENSE.txt` | `LICENSE` @ `b691a3d…` | 2026-03-19 | `5997fb9be170fd806461d95bb820870263196d43` | `bfec44796db963653bcb367f176b8197ee0aca95b914ddcf638413ed431b2ddd` |
| `history/2024-08-05_c58b153_hif_schema.json` | `hif_schema.json` @ `c58b153` ("Initial JSONSchema") | 2024-08-05 | `ac857a9c2c040865e32bd004175289fc45402a79` | `78f3aa84c50dbb196624d266b6e1beeb3f8fc24afd99a9069410cf0108bd9a49` |
| `history/2024-08-13_e5c868b_hif_schema_v0.1.0.json` | `schemas/hif_schema_v0.1.0.json` @ `e5c868bf6b70b882f194a1fe8a6bec9fc72a6059` | 2024-08-13 | `af8045c365b2078c77b0754b6a130c186881ac3c` | `121f457fe2e81f2779c1318fe082f40d98e71c0c3cb14ee4ddebd1263c9da5a8` |
| `history/2024-08-21_53a8a93_hif_schema_v0.1.0.json` | same path @ `53a8a937de79d1c7f2e3a6acc60a06e622d45025` | 2024-08-21 | `77c669e7a0a5859b5cdb29509d4efd2af0c9f634` | `7b0366048e108c9ebe27a4ce928c0ef7d4b9c8cdd9f3c2f8d1c9f4bc776b58db` |
| `history/2024-09-26_7aefda6_hif_schema_v0.1.0.json` | same path @ `7aefda6874afee94c0993839b5a052d21156561b` | 2024-09-26 | `e2675b2888ee4a62e57ce4938afbc2f1faea0200` | `d43caac0272ea076d8e3aebc946c7a59b7a65d41409b166e8978c14d3fc8879c` |
| `history/2024-10-03_de5f89f_hif_schema_v0.1.0.json` | same path @ `de5f89fad8e5bbb2c4eb37743f7bb64cd7b7c96a` | 2024-10-03 | `f12354bcc55187d59b12f09b6ddfaac35689bc12` | `2022a1e3209dbc528f472a004a5b4d48a899d77773f376584067a83c023b47da` |

Commit-pinned download URL pattern:
`https://raw.githubusercontent.com/HIF-org/HIF-standard/<commit>/<path>`.

The two published files differ only in `$id` and in the non-standard `version` annotation
(`"latest"` vs `"0.1.0"`); their validation keywords are identical, and have been since `de5f89f`
(2024-10-03). The Zenodo archive of release v0.1.2
([10.5281/zenodo.17257719](https://doi.org/10.5281/zenodo.17257719), file
`pszufe/HIF-standard-v0.1.2.zip`, md5 `6d8e90b23647d844473e1e3c6f1aa2c9`, commit `c013910`)
contains both files byte-identical to the copies here (same sha256).

Status of the URLs in circulation, checked with `curl` on 2026-09-23T06:47Z:

| URL | HTTP | Bytes served |
|---|---|---|
| `https://raw.githubusercontent.com/HIF-org/HIF-standard/main/schemas/hif_schema.json` | 200 | = `hif_schema.json` |
| `https://raw.githubusercontent.com/pszufe/HIF-standard/main/schemas/hif_schema.json` (README snippets) | 200 | = `hif_schema.json` |
| `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json` (HyperNetX 2.4.3 `schema_url`) | 200 | = `hif_schema_v0.1.0.json` |
| `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/schema.json` (the `$id` of `hif_schema.json`) | 404 | none |

The files are MIT-licensed, "Copyright (c) 2024-2025 HIF development team"; the licence text is in
`UPSTREAM-LICENSE.txt`.

## Cases

`cases/` holds 36 hand-made files, one question each. The file name states the question. They are
all built from the same small role-labelled directed fact unless the case needs something else.
`34-empty-file-zero-bytes.json` is deliberately empty. `35-nan-literal-in-attrs.json` and
`36-duplicate-json-key-in-attrs.json` are deliberately not strict JSON.

## Running

```bash
python3 -m venv venv-hif && venv-hif/bin/pip install jsonschema fastjsonschema
venv-hif/bin/python validate_cases.py \
    --upstream-tests /path/to/HIF-standard/tests/test_files   # optional calibration
```

The script validates every case, and this repository's `schemas/sample.hif.json`, against the
seven schema snapshots. It uses two validators: `jsonschema` (the Draft-07 validator is chosen from
the schema's `$schema`) and `fastjsonschema` (the validator named in the upstream README and used in
the upstream tests). It writes `results.md` and `results.json`.

It was last run on 2026-09-23 with Python 3.11.15, jsonschema 4.26.0 and fastjsonschema 2.22.2.
The two validators agreed on every cell. As calibration, all 15 upstream `HIF-compliant` files
validated and all 16 `HIF-non-compliant` files failed under both published schemas, which matches
what upstream expects.

## HyperNetX schema gate (`hnx_validation_probe.py`)

HyperNetX is the only one of XGI 0.10.2, HyperNetX 2.4.3 and HypergraphX 1.8.0 that imports a JSON
Schema validator (checked by grepping the three PyPI wheels on 2026-09-23). On every call,
`hypernetx/hif.py` fetches `schema_url` (line 12), which is the oldest repository name. It then
compiles the schema with fastjsonschema in both `to_hif` (lines 63–65) and `from_hif` (lines 136–138).

Output of the probe, run 2026-09-23 with hypernetx 2.4.3 in a separate venv:

```
hypernetx 2.4.3 | schema_url: https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json
from_hif(01-baseline-role-in-incidence-attrs) -> Hypergraph
from_hif(04-top-level-version-key) -> NoneType
from_hif(08-metadata-roles-vocabulary) -> Hypergraph
from_hif(11-incidence-record-level-role-key) -> NoneType
to_hif(metadata=None) -> dict; metadata keys: ['default_attrs']
to_hif(metadata=dict) -> NoneType; metadata keys: None
```

- A schema-invalid file makes `from_hif` return `None` without raising. Lines 144–145 and 151–152
  create `HyperNetXError(ex)` but never raise it.
- `to_hif(metadata=<dict>)` returns `None`, because line 94 assigns the result of `dict.update`,
  which is `None`, and validation then fails silently at lines 108–113. The caller's dict is still
  mutated: `default_attrs` gets added to it. This was observed for a hypergraph with no name. If
  `hg.name` is set, line 98 (`metadata["name"] = hg.name`) should raise `TypeError` instead. That
  second path comes from reading the source; I did not run it.

The probe checks only the schema gate. It does not test whether roles survive the round trip.
