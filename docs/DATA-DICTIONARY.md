# Data Dictionary

This file defines the data contracts: the tables, the artifacts and the rules files. It is PROVISIONAL, but its file
paths and keys match the files that exist. Its change history is in git. "(routine)" marks a routine technical choice
that Claude made.

Columns use snake_case and carry their units in the column name. Dates are ISO 8601 in tables and "MM-DD" for the
year-less trial dates. A missing value is null, never 0 or -999. Numbers are JSON numbers, never strings (routine). The
API JSON and the canonical identifiers (province, plan ids, season codes, crop keys, source ids, rule codes) are
defined once, in docs/UI-UX-SPEC.md §11; this file defines the tables, artifacts and rules files that feed it. Source
ids are either REFERENCES ids (`R-` ids of docs/REFERENCES.md, e.g. `R-P02`) or, for our own computations,
computation ids: `E-` followed by three digits and an optional lowercase letter, each with its entry in
rules/sources.yaml (routine).

## 1. Administrative units: `data/processed/admin_units.csv` (target; the current file is data/reference/admin_units.csv)

This table is not built yet. Until the crosswalk exists, the reference table `data/reference/admin_units.csv`
(columns `province_nso, name_vi, valid_from_year, valid_to_year, status_2025, unit_2025_vi, source_id, notes`; sources
in data/reference/SOURCES.md) holds the NSO names, and every table keys its units by `province_nso` (§2, §3, §4c).

| Column | Type | Notes |
|---|---|---|
| unit_id | str | our stable id for the **historical** NSO unit, e.g. `VN-NA` (Nghệ An), `VN-HT` (Hà Tĩnh), `VN-HTAY` (Hà Tây) |
| province_code | str / null | the API `Province` value of UI-UX-SPEC §11 for units offered in the app: `nghe_an` for `VN-NA`; null for all other units (routine) |
| name_nso_en | str | exactly as in NSO English tables (e.g. "Nghe An") |
| name_vi | str | Vietnamese name with diacritics |
| nso_code_pre2025 | str | historical NSO code (Nghệ An 40, Hà Tĩnh 42, Thanh Hóa 38; to verify) |
| region_nso | str | NSO region (e.g. "North Central and Central coastal areas") |
| region_id | str | stable id of the NSO region, used in `MetricRow.subset` `region:<region_id>` (routine; values set when the table is built) |
| valid_from_year / valid_to_year | int / null | e.g. Hà Tây valid_to 2007 |
| status_2025 | str | `unchanged` / `merged_into:<unit>` per Resolution 202/2025/QH15 |

Training joins use `unit_id` only. Never join on post-2025 names or codes. The API's `province=nghe_an` is mapped to
`unit_id` `VN-NA` through `province_code` only.

## 2. Crop statistics: `data/processed/crop_stats.csv`

| Column | Type | Notes |
|---|---|---|
| unit_id | str | FK admin_units (until the crosswalk exists, `province_nso` holds the NSO English name, e.g. "Nghe An") |
| year | int | 1995..2025 |
| is_preliminary | bool | true for "Prel. 2025" |
| crop | str | `rice`, `maize`, `peanut` |
| season | str | NSO season names as parsed [DATA]: `spring`, `autumn`, `winter`, `annual`. Every artifact and the API use the canonical codes (UI-UX-SPEC §11): NSO `spring` -> `spring`, NSO `autumn` -> `summer_autumn`, NSO `winter` -> `winter`; `annual` is not a season code. The mapping is applied at export |
| planted_area_ha | float | NSO publishes thousand ha for some tables; convert and record |
| yield_t_ha | float | NSO yield (quintal/ha in VN tables -> divide by 10); for peanut derived = production/area, flag |
| production_t | float | |
| yield_derived | bool | true if computed from production/area (peanut only; official blank rice/maize yields stay blank) |
| source_table | str | e.g. `E06.17` |
| retrieved_on | date | |

Series cleaning (ML-DESIGN.md §3) adds the columns `series_id` (unit | crop | season | segment number), `segment`,
`break_here` and `fao_flagged`. `break_here` is true on the first year of each new segment after the first. A new
segment starts at a named 2004 break, an area jump of more than 50%, a change from 0 ha to more than 0 ha, or a gap
year.

The QA helper `consistency_ratio(df)` computes production / (area x yield) over the rows that have all three values,
area > 0, yield > 0 and `yield_derived` False (derived rows equal 1 by construction). We use it to check units.

## 3. Farmland weights per POWER cell: `data/processed/cell_weights.csv`

One farmland mask is used for all years. For each pixel it takes the minimum MODIS cropland percent over 2001-2015,
and it counts class 12 (croplands, "At least 60%" cultivated) at 80%, the middle of 60-100%, and class 14 (mosaics,
40-60% cultivation) at 50% (R-K10, R-K12; ML-DESIGN.md §4).

| Column | Type | Notes |
|---|---|---|
| province_nso | str | NSO English unit name (the `unit_id` key replaces it when the crosswalk exists, as in §2) |
| cell_id | str | POWER cell id (routine: built from the cell-centre latitude and longitude) |
| lat, lon | float | POWER cell centre |
| farmland_weight | float 0..1 | share of the unit's farmland (fixed mask) inside this cell; the weights of a unit sum to 1 |
| method | str | `farmland_weighted` (main) or `centroid` (the centroid sensitivity run of ML-DESIGN.md §7: one point at the unit centroid, weight 1) |

The weights are fixed for all years, and the file is committed. POWER cells inside the unit whose weight is zero are
listed in data/processed/cell_weights_zero.csv (scripts/build_cell_weights.py) before the freeze commit (ML-DESIGN.md
§4), and the method page shows them as a `ReportItem` (UI-UX-SPEC §11).

## 4. Season climate features (columns of `data/processed/training_table.csv`, §4c)

scripts/build_training_table.py writes the §4 and §4a columns into the training table; there is no separate
climate_season_features.csv. Until the crosswalk exists, the unit key is `province_nso` (§1).

All rows use the farmland weights in `cell_weights.csv` (§3). The feature list and the cleaning rules are frozen in a
recorded commit before the first model run, and standardisation is fitted inside each fold (ML-DESIGN.md §4). The
ETCCDI, heat, soil-water and radiation columns use the farmland-weighted province series. The exceptions are the
hot-day count `hot_days_d` and the official-condition count columns of §4a, which are counted per cell and then
weighted.

| Column | Unit | Notes |
|---|---|---|
| unit_id, year, crop, season | | key |
| window_start, window_end | date | from rules/calendar.yaml (§6b) |
| precip_sum_mm | mm | POWER PRECTOTCORR summed (daily mm/day) |
| precip_anom_pct | % | computed in the evaluation harness per fold, not stored (`ml/runner.add_precip_anom`): vs the same unit and season's mean over the **training years only**; the 1991-2020 normal is used only in §4b |
| dry_spell_max_d | days | longest run < 1 mm (ETCCDI CDD) |
| heavy_rain_d | days | >= 20 mm (ETCCDI R20mm); ML feature only, not the official heavy-rain definition (§4b) |
| rx5day_mm | mm | wettest 5 consecutive days (ETCCDI Rx5day, ML-DESIGN.md §4) |
| tmax_mean_c, tmin_mean_c | C | |
| hot_days_d | days | counted per cell, then weighted (§4a): Tmax strictly above 35 C (QĐ 18/2021 Art. 5.21 "vượt quá 35°c", R-A01; 35.0 C is not counted), over the whole season window: flowering dates are not sourced |
| gwetroot_mean, gwetroot_min | 0-1 | MERRA-2 modeled root-zone wetness |
| srad_mean_mj_m2_d | MJ/m2/day | POWER ALLSKY_SFC_SW_DWN (unit "MJ/m^2/day" in the cached API responses, checked 2026-11-12) |
| txx_c | C | hottest day of the window (ETCCDI TXx) |
| n_points | int | cells aggregated |

### 4a. Official-condition counts used as ML features

These columns are in the same file and have the same key as §4 (unit_id, year, crop, season), with the NSO season
window as in §4. They apply the basic definitions of QĐ 18/2021/QĐ-TTg Art. 5 and TT 25/2022/TT-BTNMT to NASA POWER
data. Each count is made per POWER cell and then weighted with the farmland weights; it is not computed on the
weighted province series. These columns are model features only, and the displayed labels are in §4b. The heat-day
count `hot_days_d` is counted the same way, per cell and then weighted; a descriptive comparison of the two ways of
counting measured the difference on hot days.

| Column | Unit | Definition |
|---|---|---|
| official_heavy_rain_d | days | rain > 50 mm in 24 h (QĐ 18/2021 Art. 5.17). Computed from POWER daily totals in local solar time (API header "time_standard": "LST"): a calendar-day total above 50 mm satisfies the definition, but an event split across two days can be missed. Optional, only if time allows: measure the miss rate with POWER hourly data (available from 2001) using the maximum of any 24 hours; if skipped, the site states "daily totals can miss rain events that cross midnight" |
| drought_rain_months | months | computed in the evaluation harness per fold (not stored); months with rain more than 50% below the same month's mean over the training years only, recomputed per fold (ML-DESIGN.md §4); the 1991-2020 normal is used only in §4b |
| drought_rain_consecutive | share 0..1 | farmland-weighted share of cells meeting reading 1 of "kéo dài từ 2 tháng đến 3 tháng" (QĐ 18/2021 Art. 48, rain part only; the surface-water part is not computable from POWER): at least 2 consecutive such months in the season |
| drought_rain_any2 | share 0..1 | farmland-weighted share of cells meeting reading 2: any 2 such months in the season; the site shows the rule's wording and both readings, and the pipeline reports how often they differ in 1995-2024 |
| ret_hai_d | days | daily mean temperature strictly below 13 C (QĐ 18/2021 Art. 5.18 "dưới 13oc", R-A01), POWER T2M |
| ret_dam_d | days | daily mean temperature strictly below 15 C (TT 25/2022 Art. 3.6), POWER T2M |

### 4b. Displayed risk-level labels per past year: `artifacts/hazard_labels.json`

The labels apply QĐ 18/2021 Art. 44 (heavy rain), Art. 47 (heat), the rain part of Art. 48 (drought, both readings)
and Art. 53 (damaging cold). The rules are quoted verbatim in rules/conditions.yaml (§6c) and summarised in
ML-DESIGN.md §5a. Each label is computed per POWER cell for each year 1995-2024 over the P-02 field time (Tables 1, 5,
9). The daily rules use the exact days from the sowing date to the first reported harvest date (`harvest_from`). The
monthly drought rule uses the calendar months from the sowing month to the harvest month, partial months included.
P-02 reports one sowing date per crop, and the harvest month is the month of the first reported harvest date
(ML-DESIGN.md §5a). The value is the share of Nghệ An farmland (fixed farmland mask, §3) where the rule was met at
level 1 or higher.

The file is an object `{schema_version, generated_at, freeze_commit, rows: [...]}` with one row per level x crop x year
x rule:

| Field | Type | Notes |
|---|---|---|
| level | str | `crop` (one P-02 crop of one plan; feeds `CropExposure`) or `year` (all P-02 crops of that calendar year; feeds `YearRow.shares` on Screen 2) (routine) |
| plan_id | str / null | `usual`, `cc1`..`cc4` for `level` `crop` (no `usual_p03`: P-03 reports no dates); null for `level` `year` |
| crop_key | str / null | crop key of UI-UX-SPEC §11 (`<plan id>_<season code>_<crop id>`, e.g. `cc1_spring_peanut`) for `level` `crop`; null for `level` `year` |
| season | str / null | canonical season code (`spring`, `summer_autumn`, `autumn_winter`) for `level` `crop`; null for `level` `year` |
| months | int[] | `crop`: calendar months from the sowing month to the harvest month (P-02); `year`: the union of those months over all P-02 crops in that calendar year |
| field_dates | [str, str][] | `MM-DD` pairs of sowing date and first reported harvest date (P-02): one pair for `crop`; the pairs of all P-02 crops in that calendar year for `year` (daily rules count the union of their days) |
| year | int | 1995..2024 |
| rule | str | `heavy_rain`, `heat`, `drought_rain_consecutive`, `drought_rain_any2`, `cold` |
| share_farmland | float 0..1 / null | sum of farmland weights of the cells where the rule was met; null = not computed |
| n_cells | int | POWER cells with farmland weight in Nghệ An |
| threshold_source_id | str | `R-A01` |
| values_source_ids | str[] | `["R-N01", "R-N02"]` |
| computed_by | str | computation id (format above) |

API conversion (the rounding mode is routine): the engine shows `share_farmland` as a whole percent. `Value.value` is
the share x 100 rounded half up to an integer (Python `decimal.ROUND_HALF_UP`), `unit` is "%" in both languages, and
`source_ids` is [`threshold_source_id`, `values_source_ids`..., `computed_by`]. A null stays null.

Rule details (ML-DESIGN.md §5a). A spell ("đợt") is a run of consecutive days inside one band of Art. 47.1 (heat) or
Art. 53.1 (cold); a run that crosses bands is not one spell of either band. The heat threshold includes 35.0 C and the
cold threshold includes 13.0 C. Every Nghệ An cell uses the Bắc Trung Bộ wording, level 1 or higher counts as met, and
harvest ranges use the first reported date. The site shows this limitation: issued levels weigh more factors than the
tables do (R-K03), and ours is a mechanical reading.

The site also states the limitation "we apply the official thresholds to NASA's 50 km grid values; gridded values
smooth extremes (Zhang et al. 2011, abstract)" (UI-UX-SPEC key `years.gridNote`). Each value is shown with two sources
and the words "our computation, not an official record" (UI-UX-SPEC H19).

### 4c. Training table: `data/processed/training_table.csv`

scripts/build_training_table.py built this table before the event without the target; `anom` is added during the
event once the normal method is chosen (ML-DESIGN.md §3). The table has one row per unit x rice season x year (the
model rows of ML-DESIGN.md §3). Each row holds the key `unit_id, year, season` (`province_nso` until the crosswalk
exists, §1; `ml/runner.add_precip_anom` groups by it); the target `anom` (ML-DESIGN.md §3; null for a year without a
normal, which is never a training or test row); `fao_flagged` (bool, the low-yield flag of ML-DESIGN.md §3); the
feature columns of §4 and §4a for `crop` = `rice`; and the context features of ML-DESIGN.md §4 (rice season and
province long-term climate means, with no region label; the long-term means are taken over the training years of each
fold, and the column names are fixed in the freeze commit, ML-DESIGN.md §4). The file is gitignored and reproducible.

### 4d. Soil wetness per plan crop and past year: `artifacts/soil_wetness.json`

The input is POWER daily GWETROOT (R-N01; 0 = completely dry soil, 1 = completely saturated soil, R-W12) for the
Nghệ An cells of §3, 1990-2024, stored in data/raw/power. The values are computed for each `level` `crop` row of
`hazard_labels.json` (same plan, crop and field dates) and each year 1995-2024. For each cell we take the mean of daily
GWETROOT over the field days (the sowing date to the first reported harvest date, both included). `value` is the
farmland-weighted mean of these cell means (§3 weights). `normal` is, for each cell, the mean of that field-day mean
over the years 1991-2020, then farmland-weighted (WMO standard normal, R-A15; the same period as the rain normal,
R-K15). A cell with a missing day in a window gives no value for that year (null, never filled), and a normal needs
all 30 years.

The file is an object `{schema_version, generated_at, freeze_commit, rows: [...]}` with one row per plan crop x year:

| Field | Type | Notes |
|---|---|---|
| plan_id, crop_key, season, field_dates | as in §4b | same keys as the `crop` rows of §4b |
| year | int | 1995..2024 |
| value | float 0..1 / null | farmland-weighted field-day mean |
| normal | float 0..1 / null | farmland-weighted 1991-2020 average of the same field-day mean |
| n_cells | int | cells with farmland weight in Nghệ An |
| source_ids | str[] | `["R-N01", "R-W12", "R-N02", "R-A15"]` |
| computed_by | str | computation id |

API conversion: `value` and `normal` are multiplied by 100 and rounded half up to a whole percent (the convention of
§4b), with unit "%". A null stays null. The site labels these values "NASA model value (MERRA-2), not a measurement"
(UI-UX-SPEC §9, key `water.soilModelled`).

## 5. App artifact: `artifacts/risk_table.json`

```json
{
  "schema_version": "0.4",
  "generated_at": "YYYY-MM-DDTHH:MM:SS+07:00",
  "freeze_commit": "<hash>",
  "data_versions": {"crop_stats": "sha256:...", "climate": "sha256:..."},
  "seasons": [
    {"season": "spring", "model_status": "shown", "model_id": "m1_ridge"}
  ],
  "rows": [
    {"unit_id": "VN-NA", "crop": "rice", "season": "spring", "year": 2010,
     "anom_history": -0.07, "anom_history_source_ids": ["R-D01", "<normal-method computation id>"],
     "anom_oos": null, "oos_low_80": null, "oos_high_80": null,
     "model_id": null, "anom_oos_source_ids": []}
  ]
}
```
The example shows the format only; its numbers are placeholders, not results. There is one row per province x rice
season x past year.
- `anom_history` (number / null) is the real NSO anomaly as a fraction, that is, the percent anomaly against a
  past-only normal (-0.07 means 7% below normal). It is null for a year without a normal, and the app shows that year
  as "not available". `anom_history_source_ids` holds the NSO table source and the computation id of the normal-method
  choice.
- `anom_oos` (number / null) is the out-of-sample prediction. It is filled only for the test years 2016-2024, only for
  spring and winter rice, and only where that season's own test passed. It is null otherwise, and always null for
  1995-2015 and for summer-autumn rice (G1 fail).
- `oos_low_80` and `oos_high_80` (number / null) are the model's 80% interval (ML-DESIGN.md §6). They are filled only
  together with `anom_oos` and only where G4 passed for that season, and they are null otherwise.
- `model_id` (str / null) is the model that produced `anom_oos` for that row, and it is null when `anom_oos` is null.
  `anom_oos_source_ids` holds the computation id of that model run, or [] when `anom_oos` is null.
- `seasons[]` gives each rice season's `model_status` (`shown`, `not_shown`, `not_modeled`, UI-UX-SPEC §11) and
  `model_id`. The export step sets them from `gates.json` by the pass rules of ML-DESIGN.md §8. The cards use M1 for
  every season; M2 and M3 are method-page results only (ML-DESIGN.md §10).

The engine shows anomalies as whole percent (fraction x 100, rounded half up). It summarises the picked years as the
min, median and max of the non-null `anom_history` values with the worst years named, or it lists each year when fewer
than 2 values are non-null (ML-DESIGN.md §5b). The median of an even number of years is the mean of the two middle
exact values, rounded once to a whole percent (half up); the years are never rounded first. Source facts are looked up
by id in `rules/sources.yaml` (§8). The gate verdicts for each season are in `artifacts/gates.json` (§5b).

## 5b. Method artifacts: `artifacts/metrics.json`, `artifacts/gates.json`

`metrics.json` is an object:
`{schema_version, generated_at, freeze_commit, test_years: {first, last}, metrics: [MetricRow...],
weather_claims: [WeatherClaim...], reports: [ReportItem...]}` (types in UI-UX-SPEC §11).
- A `MetricRow` has these fields: model_id (`b0`, `b2`, `bnw`, `m1_ridge`, `m2_lgbm`, `m3_rf`), season, role
  (`primary` = M1 spring rice only; `secondary`; `reference` = b0, b2, bnw), scheme (`rolling_origin`,
  `spatial_holdout` = the six-region blocks of ML-DESIGN.md §7), sensitivity (null; pre-registered `no_fao_flagged`,
  `mae_skill`, `risk_level_features`; robustness runs `window` (one row per window change, described in `detail`) and
  `centroid_points`), detail, subset (`national`; `na_ht_th`; `unit:<unit_id>` for the per-province pilot report;
  `region:<region_id>` for the report by region, ML-DESIGN.md §7), rmse, mae, r2_oos (Paudel 2021 eq. A.4),
  skill_vs_b0 / skill_vs_b2 / skill_vs_bnw as {value, ci90_low, ci90_high} (year bootstrap, 10,000 resamples; with
  `mae_skill` the skill is 1 - MAE_model / MAE_reference), coverage_80, n_rows, n_test_years, source_ids (the
  computation id). All models and references are scored on the same rows (ML-DESIGN.md §6).
- A `WeatherClaim` records, for each season, whether the claim "NASA weather improves the prediction" is made. The
  pipeline decides this by the rule of ML-DESIGN.md §8; the frontend never decides it.
- A `ReportItem` holds a one-off result with its computation id. The reports are the normal-method choice, the
  drought-readings difference, the heavy-rain day split miss rate (if measured, §4a), the DesInventar check, and the
  zero-weight cells (§3).

`gates.json` is an object `{schema_version, generated_at, freeze_commit, gates: [GateRow...]}`. Each GateRow has gate
(`G1`..`G4`), season, model_id (null for G1), passed (true / false / null = not run), detail text and source_ids. The
gates are given per season.

`GET /api/method` serves both files together with `rules/method.yaml` (§7b), and `POST /api/compare` carries the gate
rows of the seasons it shows (UI-UX-SPEC §11).

## 5c. Satellite rain check: `artifacts/rain_check.json`

This artifact was planned and is not in the built code: the IMERG download stopped at 194 of 288 monthly files, so the
rain check was not run, and `GET /api/method` returns `rain_check` as null.

The inputs are NASA GPM IMERG Final monthly V07 (GPM_3IMERGM, 0.1 deg, R-N05) for a box around the Nghệ An cells,
cached in data/raw/imerg_monthly (DATA-SOURCES, MANIFEST), and POWER daily PRECTOTCORR (R-N01) for the same cells, for
the months 2001-01..2024-12. The IMERG monthly total (mm) is `precipitation` (mm/hr, file attribute) x 24 x the days in
the month. For each POWER cell it is the mean over the IMERG pixels whose centres lie inside the cell (centre +-0.25 deg
latitude, +-0.3125 deg longitude; lower edge included, upper edge excluded; routine). The POWER total is the sum of the
month's daily values, for complete months only. Both series are farmland-weighted with the same §3 weights. A month
missing in either series is dropped from both and counted in `n_dropped`.

The file is `{schema_version, generated_at, freeze_commit, months: [{month: "YYYY-MM", imerg_mm, power_mm}], cc,
mean_imerg_mm, mean_power_mm, n_months, n_dropped, source_ids, computed_by}`. `cc` is the Pearson correlation
coefficient of the monthly totals (Roversi et al. 2024, Table 5, R-M23). `source_ids` is `["R-N05", "R-N01", "R-N02",
"R-M23", "R-N06"]`. There is no pass or fail field, because no source gives a threshold for this use. The check is
served in `GET /api/method` as `rain_check` (UI-UX-SPEC §11), with values in mm rounded half up to whole mm and `cc`
rounded to two decimals (routine).

A script draws the grid figure `artifacts/figures/nghe_an_grid.svg` from §3 and the geoBoundaries boundary; the figure
carries no new numbers.

## 6. Crops and water facts: `rules/crops.yaml`

The file has one entry per crop id (routine): `rice`, `peanut`, `mung_bean`, `maize_grain`, `maize_biomass`,
`soybean`, `sweet_potato`, `black_bean`, `black_sesame`, `chili`, `pumpkin` (the crops of the UI-UX-SPEC §11b coverage
table). Each crop has the fields `crop_id`, `name` {vi, en}, `is_legume` (bool) with `legume_source_ids`, and
`water_facts`.

`water_facts` is a list of {source_id, measure, value_text, unit, scope {vi, en}, note {vi, en} | null}. Each fact is
cited on its own and is present only where the source lists the crop. `measure` is `to_apply` (TCVN 8641:2011, "nước
phải tưới vào ruộng", m3/ha) or `crop_uses` (FAO Training Manual 3 Table 14, "nước cây dùng", mm, "rough estimate"),
and the UI names the measure on every line. `scope` holds the TCVN region, season and method of a row. The engine maps
each fact to a `WaterFact` (UI-UX-SPEC §11: `value` from value_text, unit and source_id; `scope`; `note`) for every plan
crop with that crop id. A rice crop gets only the TCVN 8641 rows of its own season, and the season of each row is taken
from the standard's own row label. A crop with no fact in either source gets one `WaterFact` with `measure`
`not_listed` and `value` null; the engine generates it, and it is never stored. The values in use are:
- TCVN 8641:2011 (R-W15): maize 2,000-2,500 m3/ha whole season; peanut about 2,000; soybean about 2,000; sweet potato
  1,200-1,400; rice maintenance (land preparation excluded), all region rows shown because the standard does not place
  Nghệ An: Trung bộ transplanted spring 6,500-7,500, summer-autumn 6,000-7,000; Trung bộ direct-seeded spring
  6,500-7,500, summer-autumn 5,700-7,000; Bắc bộ spring 6,000-7,000, mùa 4,500-5,500 m3/ha.
- FAO TM3 Table 14 (R-M02): rice paddy 450-700, maize 500-800, peanut 500-700, soybean 450-700 mm.
- Not listed in these sources: mung bean, black bean, black sesame, chili, pumpkin, biomass maize. No value is
  borrowed from another crop, and the two sources are never compared. There is no water-deficit artifact.

## 6b. Season calendar: `rules/calendar.yaml`

The file has three lists, `ml_windows`, `excluded` and `trial_windows` (the layout is routine). There is no separate
`seasons` list. The API `Season.label` comes from `season_labels` in rules/method.yaml (§7b), and `Season.window` comes
from the `ml_windows` entry of Nghệ An's calendar region (NSO crop calendar, R-V05), or from `trial_windows` for a
season that is not an NSO rice season.
- `ml_windows` has one entry per NSO rice season and calendar region, because the windows differ by region. Each entry
  has `nso_season`, `calendar_region` (`red_river_delta`, `northern_mountains`, `north_central`, `central_coast`,
  `highlands_southeast`, `mekong`), `start` and `end` as (month, year offset; -1 = previous year), and `source_ids`
  (the NSO "Phụ lục 1" calendar, 2019). The values are as implemented in `features/season_windows.py`: a window runs
  from the first day of the first sowing month to the last day of the last harvest month, and Mekong summer-autumn is
  excluded. Provinces map to calendar regions by their NSO region, and the NSO "North Central and Central coastal
  areas" region is split into the six North Central provinces and the eight South Central coast provinces.
- `excluded` lists the (NSO season, calendar region) pairs that have no window, each with its `reason` (Mekong
  summer-autumn); `season_windows.season_window` raises that reason.
- `trial_windows` holds the window text of a season that is not an NSO season, with the fields `season`, `window`
  {vi, en} and `source_ids`. `autumn_winter` (vụ Thu Đông) takes the P-02 Table 5 dates, "gieo 15/8 - 10/9, thu hoạch
  21/11 - 22/12" / "sown 15/8 - 10/9, harvested 21/11 - 22/12" (R-P02).
`features/season_windows.py` reads this file; since the tests-first refactor, no window is written in code.

## 6c. Official rules: `rules/conditions.yaml`

The file has one entry per rule code, with the fields `code`, `label` {vi, en}, `rule_text` {vi, en} (the quoted
article text of QĐ 18/2021; the English side is a translation marked as ours), `article` (e.g. "Art. 47"),
`threshold_source_id` (`R-A01`), `values_source_ids` (`["R-N01", "R-N02"]`) and `computed_by` (computation id). It
feeds the API `Rule`.

## 7. Rules: `rules/rotations.yaml` (hand-curated)

```yaml
# Format example only (P-02 structure CC1). The final values come from the P-02 full text (Table 13 and the dates).
- id: cc1                  # canonical plan ids: usual (CC5), usual_p03, cc1..cc4 (UI-UX-SPEC §11)
  name: {vi: "Lạc L20 - Đậu xanh D22 - Ngô hạt VN5885", en: "Peanut L20 - mung bean D22 - grain maize VN5885"}
  is_usual: false          # true for usual and usual_p03
  land_archetypes: [drought_prone_paddy]   # the land type the study tested; documents scope, not used to filter
  provinces_studied: [VN-NA]
  site: "Lưu Sơn, Đô Lương"
  trial_period: "2020-06 to 2021-06"
  seasons:   # Table 13 order: spring 2021 / summer-autumn 2020 / autumn-winter 2020
    - {crop_key: cc1_spring_peanut, crop_id: peanut, variety: L20, season: spring,
       sow_from: TBD, sow_to: TBD, harvest_from: TBD, harvest_to: TBD}   # "MM-DD" from P-02 Table 9
    - {crop_key: cc1_summer_autumn_mung_bean, crop_id: mung_bean, variety: D22, season: summer_autumn,
       sow_from: TBD, sow_to: TBD, harvest_from: TBD, harvest_to: TBD}   # P-02 Table 1 (harvest is a range)
    - {crop_key: cc1_autumn_winter_maize_grain, crop_id: maize_grain, variety: VN5885, season: autumn_winter,
       sow_from: TBD, sow_to: TBD, harvest_from: TBD, harvest_to: TBD}   # P-02 Table 5
  # water facts come from rules/crops.yaml per crop id; no plan-level water rule (no plan is hidden)
  reported_economics: {source_id: R-P02,
                       definition: {vi: TBD, en: TBD},   # "lợi nhuận thuần (RVAC) = GR - TVC", labour included
                       profit_per_crop: TBD,     # P-02 Table 13 "Lãi thuần", per crop_key
                       cost_per_crop: TBD,       # P-02 Tables 4, 8, 12 "Tổng chi", per crop_key; null if not reported
                       price_year: "2020-21",    # "Giá bán theo giá thị trường tại thời điểm thu hoạch"; null if not stated
                       flags: TBD}               # {vi, en} per crop_key, e.g. identical Table 4 rows (CC1 mung bean, CC5 black bean)
  # whole-year total = our arithmetic (sum of profit_per_crop), computed by the engine, never stored here
  why: {why: {vi: TBD, en: TBD}, evidence: {vi: TBD, en: TBD},
        benefits: {vi: TBD, en: TBD}, gaps: {vi: TBD, en: TBD}}
  risks: TBD                # list of {text: {vi, en}, source_ids: [...]}: quoted market facts (P-03, R-C13) and,
                            # for plans without rice, Nghị định 112/2024 (R-G06, R-G27)
  study_type: field_trial_each_crop_in_its_season_unreplicated   # never "tested whole-year sequence"
  limitations: [single site, one year, single unreplicated 1000 m2 plots,
                plot layout unknown: whether one field carried the whole structure,
                reported date overlaps,
                P-02 methods text (p.44) lists CC2-CC4 differently from the results tables,
                Table 4 rows for CC1 mung bean and CC5 black bean are identical]
  source_ids: [R-P02]
```

Within one crop the dates satisfy `sow_from <= sow_to <= harvest_from <= harvest_to`, all inside one calendar year,
because no P-02 window crosses 31 December (ML-DESIGN.md §5a). When the source gives one date, the from and to dates
are equal. The engine derives `bare_periods` (UI-UX-SPEC §11 `Period`) as the days of the year covered by no span from
`sow_from` to `harvest_to`. A bare period that runs over 31 December is one `Period` with `from` later than `to`.

The P-03 entry (`usual_p03`) has `sow_from` .. `harvest_to` = null (P-03 reports durations only, "Thời vụ ... được điều
chỉnh tùy vào điều kiện thực tế") and `reported_economics.text_only` {vi, en} with the P-03 profit definition ("Lợi
nhuận = GR - Tổng chi phí vật chất"); it has no per-crop money list. Its `price_year` is "2020-21" (P-03 p.3: GR =
yield x price at harvest; trial June 2020 - June 2021).

The catalog holds P-02 CC1-CC4, the farmers' usual structure CC5 (rice - black bean - sweet potato), and the P-03 local
control (rice - rice - fallow) as a second description of local practice. It has no assembled plans. The engine
derives the land-care checks from `seasons` and `rules/crops.yaml`, and they are never hand-entered. The first check is
the number of different crop ids. The second is the days with a living crop out of 365, which is 365 minus the days of
the plan's `bare_periods` (spans from `sow_from` to `harvest_to`, as drawn on the calendar), so living and bare days
always add up to 365 and no partial-month rule is needed (null for `usual_p03`). Hazard counting uses the stricter
field days to the first harvest date. The third check is whether a legume is grown (`is_legume`). The principles behind
the checks come from FAO Conservation Agriculture (R-E13), NRCS Soil Health on Cropland (R-E12) and Witcombe and
Tiemann 2022 (R-E06).

Every rule must have source_ids, land_archetypes, study_type and limitations, and its source facts come from
`rules/sources.yaml` by id.

## 7b. Method page content: `rules/method.yaml`

The file is hand-curated and cited (routine). It holds `coverage` (a list of `CoverageCell`: row_key, crop {vi, en},
axis, text {vi, en}, source_ids; one cell per row_key and axis, checked by a test against `rotations.yaml`,
`crops.yaml` and the gates), `explain_terms` (the six `ExplainTerm` entries of UI-UX-SPEC §11b item 3 with
source_ids), `datasets_not_used` (the datasets considered and not used, each with the dataset, why it was not used and
its source; its own field in the method response, UI-UX-SPEC §11b item 4b), `limitations` (a list of {vi, en}),
`stability_scope` {vi, en} (the card scope text, ML-DESIGN.md §5b, with no number) and `season_labels` ({vi, en} with
source_ids for each season code). The engine copies `stability_scope` into `Stability.scope` and `season_labels` into
`Season.label`. `GET /api/method` serves this content.

## 8. Rules: `rules/sources.yaml`

The file has one entry for each source id that a displayed value uses. The fields are those of `SourceFacts` in
UI-UX-SPEC §11: `id` (REFERENCES or computation-id format above), `citation` {vi, en}, `study_type` {vi, en},
`place_years` {vi, en}, `read_status` (the REFERENCES status cell copied as written, e.g. "READ", "ABSTRACT", "READ
(full text, VJOL copy 167049)"; null for computation ids), `full_text_read` (set by hand per source in this file; a test
fails if it is true while `read_status` names an abstract, title, summary, metadata or secondary reading; null for
computation ids), `limitations` [{vi, en}], `url` and `nso_credit` (true for NSO statistics sources, R-J10). A test
checks every `read_status` against docs/REFERENCES.md. There is no grade field.

## 9. Prices

There is no price artifact. Study money comes from P-02 Table 13 only, with no FAOSTAT prices and no inflation
adjustment. The optional "your price and costs" entry (FR-13; UI-UX-SPEC §12d) multiplies the study yield by the
farmer's price, and it gives a net margin only when the farmer enters costs. Entry is per hectare only (sale price per
kg, and costs in thousand đồng per ha, the unit of the study's numbers on the cards), as whole numbers of at most 9
digits, and the sums are computed in the phone's browser. The typed numbers stay in the page address, or, for a
signed-in farmer who saves the answers, in the saved answers. The computed revenue and margin cite the study yield and
the engine-computation source.

## 10. API responses

The JSON returned to the frontend is specified in docs/UI-UX-SPEC.md §11, which is authoritative. The endpoints are
`GET /api/past-years?province=nghe_an`, `POST /api/compare` (JSON body `CompareRequest`: province, land, years,
priority), `GET /api/method` and `GET /api/health`. The backend maps `province` to `unit_id` through `admin_units.csv`
`province_code` (§1).
- Past years: `rules` comes from `rules/conditions.yaml` (§6c), `years` from the `level` `year` rows of
  `artifacts/hazard_labels.json` (§4b), and `sources` from `rules/sources.yaml` for every id used.
- Compare: the engine function `compare(province, land, years, priority)` builds the response from
  `artifacts/risk_table.json` (§5), the `level` `crop` rows of `artifacts/hazard_labels.json` (§4b),
  `artifacts/gates.json` (§5b), `rules/crops.yaml` (§6), `rules/calendar.yaml` (§6b), `rules/conditions.yaml` (§6c),
  `rules/rotations.yaml` (§7) and `rules/sources.yaml` (§8). `land` and `priority` are checked and echoed in
  `request`; they change no number, order or content. An empty years list, or years outside 1995-2024 or not strictly
  ascending, are rejected with HTTP 422. The engine derives the bare periods from the crop date spans (§7); they are
  never hand-entered.
- Method: the response is built from `artifacts/metrics.json`, `artifacts/gates.json` (§5b), `rules/method.yaml` (§7b)
  and `rules/sources.yaml`.
- Health: the response gives the `schema_version` and `generated_at` of each artifact file.
