# MIAUDOW — Evidence-first agricultural intelligence architecture

## Objective

Four AI pillars, **one governed data fabric**. No separate LLM should hallucinate its own weather, field economics or crop suitability. System of record is a curated, versioned data product layer whose units, grids, timestamps, missingness, provenance and validity conditions are explicit.

## Data-source strategy (verified official entry points)

| Tier | Data product | Actual role | Spatial/temporal caveat | Canonical entry point |
|---|---|---|---|---|
| Core | NASA POWER daily | Temperature / rainfall estimates for historical climate exploration | Meteorology from assimilation models; original source grid often coarse; not a farm station | https://power.larc.nasa.gov/docs/services/api/temporal/daily/ |
| Core | CHIRPS v3 | 1981–near-present rainfall anomalies, dry spells, climatology | 0.05° gridded satellite + station rainfall estimate; daily product timing caveats | https://www.nature.com/articles/s41597-026-07096-4 |
| Satellite | Sentinel-2 L2A | Vegetation indices, surface reflectance, land cover dynamics | 10/20/60 m bands; clouds and masks, NDVI not a diagnosis | https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html |
| Satellite | NASA HLS v2 | Multi-sensor consistent crop temporal series | 30m; no direct plot moisture measurement; temporal and cloud gaps | https://hls.gsfc.nasa.gov/data-products/ |
| Context | NSO Việt Nam | Provincial/district production benchmarks | Official aggregates do not support field-level causal inference | https://www.nso.gov.vn/so-lieu-thong-ke/ |
| Ground | Original P-02 / P-03 full texts + tabular trials | Economics, crop rotation validation, study population | **NOT PROVIDED HERE**. Unverified profitability, calendars and prescriptions must stay blocked. | User-held primary study required |
| Ground | Irrigation service, soil maps, GPS boundaries, farm interviews, local prices | Field-scale suitability and economics | Needs explicit consent, local validation and maintenance | Partner agency / farmer data source required |

### Data quality gates

Each dataset must carry `dataset_id`, `source_url`, `source_revision`, `retrieved_at`, `license`, `temporal_coverage`, `spatial_resolution`, `geometry_crs`, `variables`, `unit`, `missing_policy`, `quality_flags`, `transformation_id`, `allowed_use`, and `version_sha256`.

**Never** join NASA POWER 0.5° weather to Sentinel-2 10m land without recording a grid-footprint mismatch. Reprojection is a computational convenience, **not** the creation of 10m meteorological truth. Use polygon aggregation, explicit area weighting and uncertainty, with spatial-resolution badges near the visual.

### 01 — Climate Intelligence

Input: daily NASA POWER + CHIRPS v3 + metadata, optional verified rain gauges. Pipeline: geospatial AOI validation → source cache → consistency QC → unit harmonization → climate baseline → 30-year percentile / standard anomaly → dry spell classification → spatial uncertainty → 2D/3D visualization.

- Useful metrics: monthly rain total, number of days above a *documented* heat threshold, baseline-relative anomaly, consecutive dry days with precise threshold, rainfall percentiles.
- Must publish baseline years, thresholds, spatial unit, fraction of missing days and expected model uncertainty.
- Avoid conditional warning badges without a verified threshold. Historical risk != future forecast.
- Real current implementation: `/api/climate` fetches NASA POWER daily on demand; aggregates only complete months, displays null on missing. CHIRPS joining is an **integration contract, not a completed connection**.

### 02 — Evidence-grounded RAG

Input: approved study PDFs, authoritative regulations, original study tables, per-claim documents. Pipeline: document OCR / extraction where required → normalization → table-to-record extraction → page-level provenance → embeddings + keyword retrieval → reranking → citation constraint → grounded LLM response → factuality checks.

Knowledge unit example:

```json
{
  "fact_id": "trial-p02-profit-1",
  "status": "PENDING_SOURCE_VALIDATION",
  "claim": null,
  "value": null,
  "unit": "million_VND_per_ha_per_year",
  "study_period": "2020-2021",
  "trial_location": "Lưu Sơn, Đô Lương, Nghệ An",
  "source_document_id": "P02",
  "source_page": null,
  "table_id": null,
  "quote": null,
  "applicability": null,
  "limitations": ["not independently verified", "not a farm prediction"]
}
```

- Answer only from verified units with a URL / page. Review all numeric quotations with deterministic parser.
- Current implementation: small set of source **fact cards** with lexical matching and optional Claude synthesis. Not full document RAG; no embedding index or P-02/P-03 full-text ingested.
- Upgrade: multilingual Vietnamese embeddings, chunking strategy preserving tables, hybrid search, retrieval benchmarks, answer abstention and human feedback.

### 03 — Crop Decision Support

Input: field water situation, validated crop calendars, local irrigation, weather distributions, trial plot outcomes, NSO benchmarks, market prices, labor, transport, source validity. Rulebook: `/api/rules/rotations.yaml`.

Algorithm sequence:
1. **Eligibility rules**: legal/season/soil/water constraints, proven validity ranges.
2. **Multi-objective comparison**: profit, water demand, stability, soil stewardship — no single optimization score without disclosed weighting and independent verification.
3. **Scenario evaluation**: change rice price, labor cost, irrigation accessibility, climate stress. Include confidence ranges, uncertainty, source period.
4. **Human decision**: display trade-offs and questions to ask extension officers.

- Do NOT present 2020–21 plot profit as future profit.
- Source unverified risk copy remains EMPTY in YAML; build script refuses risk lines without cited verified source, page and quotation.
- Current UI displays candidate rotation **names and tentative calendars only**, explicitly unverified. No agronomic ranking or invented risk.

### 04 — Vietnamese Voice Copilot

Frontend: voice input if browser supports Web Speech; text fallback; optional browser speech output. Orchestrator: ASR transcript → recognized intent → retrieval → optional data calculation → evidence gate → Claude with documents → structured response → citations + interactive visual recommendation only when supported.

- Do not claim robustness for Nghệ An dialect until evaluated on local annotated audio.
- Do not upload private audio to unapproved providers without consent and policy disclosure.
- `ANTHROPIC_API_KEY` strictly server-side; never `VITE_ANTHROPIC_API_KEY`.
- Response categories: `grounded`, `reference_only`, `insufficient_evidence`, and provider errors. No invented fallback.
- Browser voice availability differs by browser; current implementation is browser-native prototype, not a verified production Vietnamese ASR.

## Canonical API contract and card contract

```json
{
  "metric_id":"monthly_rainfall_total",
  "value":null,
  "unit":"mm",
  "time_window":{"start":"2024-01-01","end":"2024-01-31"},
  "geometry":{"type":"grid_cell","lat":18.97,"lon":105.35,"footprint_km":null},
  "source_id":"NASA_POWER",
  "method_id":"sum_daily_precip_complete_month",
  "quality_flag":"NOT_LOADED",
  "is_forecast":false,
  "is_field_measurement":false,
  "visual":"seasonal-waterfall",
  "description_vi":"Tổng lượng mưa tháng tại ô lưới khí tượng",
  "limitations_vi":"Không đo trực tiếp trên ruộng"
}
```

Every chart, 3D tooltip and AI text must use the **same canonical metric record**. Decorative hero imagery must never be visually interpreted as source imagery.

## Data tests and model evaluation

- Data: units, missing sentinels, leap days, timezone, boundary shapes, duplicates, temporal coverage, reference integrity, source terms and calculations.
- Climate models: climatology baseline, persistence baseline, blocked time split, spatial block validation, uncertainty calibration and hindcasting.
- Crop models: out-of-region holdout, temporal shift, MAE/RMSE, uncertainty, comparison to agronomist rules and naive baseline.
- Retrieval: source recall, hallucination rate, answer faithfulness, citation accuracy, numeric QA, invalid-document injection, missing-evidence abstention.
- Voice: WER by dialect, noise condition, device and demographic segment, ASR fallback effectiveness. Do not declare a target accuracy before benchmark.

## Deployment and governance priorities

1. Secure a legally shareable P-02/P-03 dataset and document full methods.
2. Define actual geographic study AOI (district, commune, plot) with official boundary geometry.
3. Build reproducible geospatial ETL (GeoParquet/PostGIS/COG, task queue, dataset snapshot hashes).
4. Implement source refresh schedules, data availability status, retries and provenance registry.
5. Wire Claude API behind FastAPI with rate limit, audit logs, monitoring, authentication and provider model configured.
6. Have agricultural experts verify the recommendation rulebook.
7. Perform user testing with farmers; ensure the beautiful UI still works in field conditions.

## Clear completeness statement

This delivery is a **production-minded UI foundation and constrained AI/data API skeleton**, not a finished Earth-observation AI model. It does **not** contain actual Nghệ An satellite raster imagery, trained models, full trial PDFs, validated agronomic rankings or deployed Claude credentials. Those cannot be represented as complete without ingesting and testing the real source data.
