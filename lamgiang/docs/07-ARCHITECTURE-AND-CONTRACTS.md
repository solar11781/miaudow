# MIAUDOW 2.0 — architecture and shared contracts

One governed data layer feeds four AI cores, one FastAPI service and one React app. No core keeps its own copy of a
number: the web app and the API both read the files in `data/canonical/`, which the pipeline builds from the raw
caches in `data/raw/`, the team rulebook in `data/rules/` and the team's model artifacts in `data/reference/`.

```
data/raw/          NASA POWER daily caches (5 farmland-weighted Nghệ An cells, 1990-2024), geoBoundaries ADM1,
                   further sources as they are acquired (CHIRPS v3, MODIS NDVI) with a manifest each
data/reference/    team artifacts copied from the miaudow repository: model metrics and gates (E-012), NSO rice
                   anomaly table, hazard labels (E-019), soil wetness (E-020), farmland weights of the 5 cells
data/rules/        the team's audited rulebook (sources, rotations, crops, conditions, method, calendar)
data/canonical/    BUILT by pipeline/build_canonical.py; read by api/ and web/ (Vite alias `@data`)
pipeline/          reproducible builders; every builder stops on a missing value instead of filling it
api/               FastAPI service `miaudow_api` (contracts, catalog, climate, evidence, decision, copilot, voice)
api/rules/rotations.yaml   the single source of plan text and risk lines (scripts/sync_rotations.py validates it)
web/               React 19 + Vite + TypeScript app (six areas)
reference/         the original prototype, the starter app and previews, kept for comparison
```

## The canonical record

`api/miaudow_api/contracts.py` defines `MetricRecord` with the fields of the data blueprint: `metric_id`,
`dataset_id`, `source_id`, `source_url`, `source_revision`, `retrieved_at`, `value`, `unit`, `time_window`,
`geometry`, `spatial_resolution`, `method_id`, `transformation_id`, `quality_flag`, `missing_policy`, `uncertainty`,
`validation_status`, `is_forecast`, `is_field_measurement`, `limitations`.

Validation status means what the evidence is, not how it looks:

| Status | Meaning in MIAUDOW |
|---|---|
| VERIFIED | Read in a primary source by the team and copied with its location (page, table, article) |
| DERIVED | Our arithmetic on verified or retrieved inputs (shares, totals, anomalies); the method is named |
| ESTIMATED | A model output (E-012 predictions, NASA POWER reanalysis values themselves) |
| ILLUSTRATIVE | Art or geometry that shows an idea, not a measurement (concept images, the illustrative 3D stage) |
| PENDING_VERIFICATION | Found but not yet checked against its source; never used for advice |
| UNAVAILABLE | The contract exists, the data does not; the UI shows an honest empty state |

`is_field_measurement` is false for every NASA POWER, CHIRPS and MODIS value: none of them is measured on a farm.

## Core interfaces (Python)

| Core | Module | Entry points |
|---|---|---|
| 01 Climate intelligence | `miaudow_api.climate` | `catalog()`, `monthly(cell, variable, year)`, `year_summary(year)`, `hazard_shares(year, crop)` → `MetricRecord`s |
| 02 Evidence RAG | `miaudow_api.evidence` | `search(query, k)` → `SearchResult` (abstains below its thresholds), `passage(id)` |
| 03 Crop decision support | `miaudow_api.decision` | `compare(CompareRequest)` → `DecisionResult` (study order, never ranked) |
| 04 Voice copilot | `miaudow_api.copilot` | `answer(CopilotRequest)` → `CopilotResponse`; Claude via tools that call cores 01-03 |

HTTP: `GET /api/health`, `GET /api/catalog`, `GET /api/climate/year/{year}`, `GET /api/climate/monthly`,
`GET /api/climate/live` (on-demand NASA POWER), `POST /api/evidence/search`, `GET /api/decision/plans`,
`POST /api/decision/compare`, `POST /api/copilot`, `GET /api/voice/benchmark`.

### Phase 2 additions

| Core | Module | Entry points |
|---|---|---|
| 01 Climate ML | `miaudow_api.climate_ml` | `analog_search(year, k)` → `AnalogResult`; `anomaly_years()` → `AnomalyYearsResult`; `full_evaluation()` (leave-one-year-out against persistence and climatology, stored in `api/eval/results/`) |
| 01 Climate series | `miaudow_api.climate_series` | yearly and monthly NASA POWER and CHIRPS series side by side, never averaged |
| Data views | `miaudow_api.data_views` | quality report, dataset coverage, regions, map layers, satellite scenes and vegetation, documents, AI capabilities, model evaluations |

HTTP added: `GET /api/data/catalog`, `/api/data/quality`, `/api/data/coverage`, `/api/climate/history`,
`/api/climate/anomalies`, `/api/climate/analogs`, `/api/climate/anomaly-years`, `/api/geo/regions`, `/api/geo/layers`,
`/api/satellite/scenes`, `/api/satellite/vegetation`, `/api/research/documents`, `POST /api/research/search`,
`POST /api/crop/compare`, `GET /api/ai/capabilities` (credentials checked for presence only), `/api/models/evaluations`.
An optional file that is not built answers 200 with an explicit unavailable state; a missing core file answers 503.

The copilot gained six strict tools on the same cores: `get_climate_anomalies`, `find_analog_years`,
`list_climate_anomaly_years`, `get_satellite_vegetation`, `get_data_provenance`, `get_map_layer_metadata`.

New canonical files: `climate_ml.json` (analogs for every year, unusual-year scores, both evaluations; written by
the build from `climate_ml.py`) and `quality.json` (75 checks from `pipeline/check_quality.py`, run last).

## The Earth observatory (web, `/dai-quan-sat`)

One page, eight scenes, one state in the URL (`canh`, `nam`, `lop`, `mua`, `o`):

| Scene | Camera | Shows | Panel |
|---|---|---|---|
| cosmos | 62,000 km over the western Pacific | Earth among the stars | planets in NASA Eyes |
| earth | 17,000 km over Viet Nam | Blue Marble, lit for 21 June 2020 | GIBS credit |
| satellites | 24,000 km | illustrative orbit rings of six missions | what MIAUDOW used from each, what is blocked |
| vietnam | 2,900 km | place names, Nghệ An and Đô Lương outlines | — |
| nghe-an | 240 km, tilted | province outline, district, Lưu Sơn | year, layer (Sentinel-2 data or GIBS imagery) |
| do-luong | 34 km, tilted | Sentinel-2 seasonal NDVI over the district | season |
| analysis | 200 km, tilted | five NASA POWER cells as columns (height = rain, colour = against 1991–2020) | cell, sourced values |
| insight | same | same | one plain sentence, link to the copilot with the year |

`web/src/features/earth/globe.ts` is the only file that imports Cesium (`createGlobe` → `goTo`, `setYear`,
`setOverlay`, `setSelected`, `setOrbits`, `stopFlight`, `dispose`); the panels read the same canonical files without
it, so the page works with the globe off (reduced motion, no WebGL, load failure).

## Rules carried over from the team (UI-UX-SPEC H1-H19, D-155)

3D, WebGL and canvas only outside the farmer routes and code-split; every animation off under reduced motion and
pausable when it runs by itself for more than 5 s; no sliders; no scores, ranks or sorting of plans; no free text on
farmer routes; no text under 17 px; 44 px targets; no localStorage, sessionStorage or cookies; past years always say
they are not a forecast; every sourced number opens its source in one tap; plan cards carry their own warnings.
