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

## Rules carried over from the team (UI-UX-SPEC H1-H19, D-155)

3D, WebGL and canvas only outside the farmer routes and code-split; every animation off under reduced motion and
pausable when it runs by itself for more than 5 s; no sliders; no scores, ranks or sorting of plans; no free text on
farmer routes; no text under 17 px; 44 px targets; no localStorage, sessionStorage or cookies; past years always say
they are not a forecast; every sourced number opens its source in one tap; plan cards carry their own warnings.
