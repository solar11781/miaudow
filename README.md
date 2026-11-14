# MIAUDOW 2.0 — Lam Giang Golden Heritage

**Ruộng làng ta, đọc bằng dữ liệu vũ trụ.** Decision support for families on water-short rice land in Nghệ An,
Vietnam: more than 30 years of NASA weather, a second satellite rain record, vegetation from Sentinel-2 and MODIS,
and six ways of farming that were tested on this land in Lưu Sơn, Đô Lương (2020–21) — side by side, never ranked,
every number with its source. Team Miaudow, NASA Space Apps Challenge 2026 (Hà Nội, challenge Field Shift).

## What is in it

| Area | Route | For | What it does |
|---|---|---|---|
| Home | `#/` | everyone | The problem in one sentence, the four AI cores (what each does, uses, gives and cannot do yet), thirty years in one chart, the four farmer steps and the observatory |
| Farmer | `#/nong-dan` … `/phuong-an` | farmers | Four tap-only steps; plan cards with a 12-month calendar, trial profit, weather, water, land care, sourced risks and questions for the officer. No 3D, nothing stored in the browser |
| Officer | `#/can-bo` | extension officers | Evidence desk: conclusion → meaning → number → source → method and limits, the fit with a family's field, the matrix |
| Science | `#/khoa-hoc?nam=2020` | judges, researchers | WebGL observatory of the real province outline and NASA grid; one shared year across the 34-year rain strip, NASA POWER vs CHIRPS, MODIS NDVI, the closest past years and the unusual years (climate ML, with its test results), rice history and the model test |
| Earth observatory | `#/dai-quan-sat` | everyone, judges | CesiumJS globe in eight scenes from space to Lưu Sơn: NASA GIBS imagery, the missions MIAUDOW used or could not use, Sentinel-2 greenness over Đô Lương, NASA POWER cells as 3D columns, official NASA Eyes in a dialog. Part of the science area; never on farmer routes |
| Evidence | `#/bang-chung` | everyone | Claims with their evidence status, the places where sources disagree, every dataset with its real ingestion state, the data-quality report (75 checks, warnings shown), the source list |
| Copilot | `#/tro-ly` | everyone | Vietnamese-first assistant with voice input (transcript confirmed before sending), read-aloud, answer cards and a visible tool trace |

Four AI cores share one data layer (`docs/07-ARCHITECTURE-AND-CONTRACTS.md`):

1. **Climate intelligence** — `api/miaudow_api/climate.py`: complete-month aggregation, normals, anomalies, hot and
   cold days, dry spells, the official risk-level rules of QĐ 18/2021, farmland weighting. `climate_ml.py`: analog
   years and unusual-year scores, tested year by year against simple baselines (`api/eval/run_climate_ml_eval.py`).
2. **Evidence retrieval** — `api/miaudow_api/evidence.py`: hybrid lexical search over 538 passages with abstention,
   benchmarked in `api/eval/`.
3. **Crop decision support** — `api/miaudow_api/decision.py`: the six plans in study order, verified values with
   their tables, applicability, unknowns and questions; text governed by `api/rules/rotations.yaml`.
4. **Copilot** — `api/miaudow_api/copilot.py`: intents and tools; a deterministic engine without a key; Claude with
   strict tools, a JSON answer schema and a number check when a key is configured.

## Run it

Requirements: Python 3.13, Node 22+ (tested on 26), Git Bash or PowerShell on Windows.

```bash
# 1. Python environment (API, pipeline)
python -m venv .venv
.venv/Scripts/python -m pip install -r api/requirements-dev.txt       # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m pip install rasterio==1.5.2                   # only to re-fetch CHIRPS or Sentinel-2

# 2. Canonical data (already committed; rebuild after changing raw data or the rulebook)
.venv/Scripts/python pipeline/build_canonical.py                      # ~20 s, writes data/canonical/
.venv/Scripts/python pipeline/write_data_registry.py                  # regenerates docs/08-DATA-REGISTRY.md

# 3. API on :8000
cd api && ../.venv/Scripts/python -m uvicorn main:app --port 8000

# 4. Web app on :5173 (proxies /api to :8000)
cd web && npm ci && npm run dev
```

The web app also works without the API: the copilot then searches in the browser and says so.

### Claude (optional, server only)

Copy `api/.env.example` to `api/.env` and set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` (for example
`claude-opus-5-5`; the id must be enabled for your account). Load it when starting the API, e.g.
`uvicorn main:app --env-file .env`. The key is read only by the server, never logged and never sent to the
browser; `.env` is git-ignored. Without both values the copilot uses the deterministic engine and the page says so.

### Re-fetching raw data (optional)

```bash
.venv/Scripts/python pipeline/fetch_chirps_v3.py            # CHIRPS v3 final monthly, windowed COG reads
.venv/Scripts/python pipeline/fetch_modis_ndvi.py --start 2015 --end 2024
.venv/Scripts/python pipeline/fetch_documents.py            # QĐ 18/2021, NĐ 112/2024 (needs antiword)
.venv/Scripts/python pipeline/fetch_boundaries.py
.venv/Scripts/python pipeline/fetch_sentinel2.py --workers 4
.venv/Scripts/python pipeline/check_gibs.py && .venv/Scripts/python pipeline/check_gibs.py --eyes
.venv/Scripts/python pipeline/fetch_nasa_missions.py --discover    # downloads need an Earthdata Login
cd web && node pipeline/build_media.mjs                     # photographs and concept art → web/public/media
```

NASA POWER daily caches for the five cells are committed under `data/raw/power*`.

## Checks

```bash
.venv/Scripts/python -m pytest api/tests pipeline/tests -q   # 288 tests
.venv/Scripts/ruff check api pipeline scripts
cd web && npx tsc -b && npx eslint . && npx vitest run      # 39 unit tests
cd web && npm run build && npx playwright test e2e/journey.spec.ts   # 54 browser tests incl. WCAG 2.2 AA
npx impeccable@4.7.0 detect web/src                          # template-pattern audit (0 findings)
.venv/Scripts/python api/eval/run_retrieval_eval.py          # retrieval benchmark
.venv/Scripts/python api/eval/run_climate_ml_eval.py         # climate ML evaluation
.venv/Scripts/python pipeline/check_quality.py               # data-quality report
```

Results, performance measurements and the completion matrix: `docs/09-VERIFICATION-REPORT.md`.

## Honesty rules the code enforces

- No number without a source; NASA POWER, CHIRPS, MODIS and Sentinel-2 values are never called field measurements.
- Trial profits are 2020–21 results of one unreplicated plot per crop, never expected income.
- Past years are never a forecast; the copilot refuses forecasts, prices and rankings.
- Plans are listed in the study's order and never scored, ranked or sorted.
- Missing values stay missing; nothing is interpolated or filled with zero.
- Pictures carry no text; every photograph's creator and licence is in the footer list, concept art says it is an
  illustration in its alt text, and the team's unlicensed mood photographs never leave the machine they were built on.
- Nothing is stored in the browser.

## Folders

```
api/          FastAPI service: contracts, four cores, rulebook, tests, retrieval benchmark
pipeline/     data acquisition and the canonical builder (every script writes a manifest)
data/raw      fetched sources with manifests      data/canonical   the one data layer
data/rules    the team's audited rulebook          data/reference   team model artifacts
web/          React 19 + Vite 8 + TypeScript app, e2e tests, media build
assets/       photographs (licensed) and concept art, with manifests
docs/         audit, blueprint, photography, design system, decision log, architecture, data registry, verification
reference/    the original prototype and the starter app, kept for comparison
```

## Licences and credits

Code: Apache-2.0 (team Miaudow). Data: NASA POWER, NASA MODIS (LP DAAC, ORNL DAAC subsets), CHIRPS v3 (Climate
Hazards Center, CC BY 4.0), Copernicus Sentinel-2 ("Contains modified Copernicus Sentinel data 2020-2024"),
geoBoundaries (gbOpen; ADM2 under CC BY 3.0 IGO, source OCHA ROAP), NASA GIBS imagery ("We acknowledge the use of
imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and
Information System (ESDIS)"), NASA Eyes (opened, not copied), CesiumJS (Apache-2.0), Cục Thống kê (NSO Vietnam),
Vietnamese legal texts (not subject to copyright, Luật SHTT Điều 15). Photographs: see `assets/photos/PHOTO_MANIFEST.json`
and the footer of the app. Fonts: Alegreya, Be Vietnam Pro and Dancing Script (OFL-1.1). Logo: designed by member B
(`assets/brand/`). Field-condition pictures: AI-generated illustrations made for MIAUDOW (`assets/field-conditions/`). Motion: GSAP 3.15.0 and @gsap/react
2.1.2 (GSAP Standard no-charge licence, not OSI). Design references read, no code copied: cinematic-ui by
akseolabs-seo (MIT, commit 37651d0), GSAP skills by GreenSock (MIT, commit aed9cfd), Impeccable by Paul Bakaus
(Apache-2.0, commit 1995764; its detector 4.7.0 was run), React Bits by David Haz (MIT + Commons Clause, commit
cf28010). MIAUDOW is not endorsed by NASA, ESA or any data provider.
