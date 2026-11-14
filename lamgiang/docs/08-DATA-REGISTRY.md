# MIAUDOW — data registry

Generated from `data/canonical/catalog.json` (built 2026-11-14T11:44:59+00:00) by `pipeline/write_data_registry.py`.
Do not edit by hand: rebuild the canonical data, then rerun the script.

Ingestion state: **INGESTED** 13, **BLOCKED** 8.
No dataset below is a measurement on a farmer's field except the two trial studies, and those describe one
unreplicated plot per crop in Lưu Sơn, Đô Lương, 2020–21.

| Dataset | State | Provider | Resolution | Time span | Licence | Field measurement |
|---|---|---|---|---|---|---|
| `chirps_v3_monthly` — CHIRPS v3 monthly rainfall | INGESTED | Climate Hazards Center, UC Santa Barbara | 0.05° | 1981/near present | CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); CHC also states a public-domain waiver - see notes | no |
| `e012_model` — Model test results E-012 | INGESTED | Miaudow team | province | test years 2016/2024 | Apache-2.0 (team artifacts) | no |
| `e019_hazard_labels` — Farmland share meeting each official rule (E-019) | INGESTED | Miaudow team | farmland-weighted province area (5 POWER cells) | 1995/2024 | Apache-2.0 (team artifacts) | no |
| `e020_soil_wetness` — Root-zone soil wetness while each crop was in the field (E-020) | INGESTED | Miaudow team, from NASA POWER GWETROOT (MERRA-2) | farmland-weighted province area (5 POWER cells) | 1995/2024, normal 1991-2020 | Apache-2.0 (team artifacts) | no |
| `geoboundaries_adm1` — Province boundaries (geoBoundaries ADM1, simplified) | INGESTED | geoBoundaries (William & Mary geoLab) | simplified polygon | static | gbOpen: public domain per the file metadata, as recorded by the team | no |
| `geoboundaries_vnm_adm2_do_luong` — Former Đô Lương district boundary, Nghệ An — geoBoundaries ADM2 | INGESTED | geoBoundaries (William & Mary geoLab); source OCHA ROAP, Government of Viet Nam | vector polygon, 658 vertices (full); web copy simplified at 0.0005° | boundary year represented 2020 (pre-July-2025 districts) | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) (licence source: data.humdata.org/dataset/viet-nam-administrative-boundaries-polygon-polyline); attribute geoBoundaries and OCHA ROAP | no |
| `modis_farmland_weights` — Farmland weight per grid cell (MODIS MCD12C1) | INGESTED | NASA LP DAAC (MODIS); weights computed by the Miaudow team | 0.05° land cover aggregated to 5 POWER cells | 2001/2015 (one fixed map) | NASA open data | no |
| `modis_mod13q1_ndvi` — MODIS MOD13Q1 16-day NDVI | INGESTED | NASA LP DAAC | 250 m | 2000/near present | No restrictions on reuse, sale or redistribution under the NASA Earth Science Data and Information Policy (https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance); cite the product DOI and the ORNL DAAC subset tool | no |
| `nasa_power_daily` — NASA POWER daily (5 farmland cells of Nghệ An) | INGESTED | NASA Langley Research Center, POWER Project | 0.5° x 0.625° (MERRA-2 grid) | 1990-01-01/2024-12-31 | NASA open data (no restriction on use; credit NASA POWER) | no |
| `nso_rice_yield` — Province rice yield anomalies (NSO, risk table) | INGESTED | Cục Thống kê (NSO Vietnam); anomalies computed by the Miaudow team (E-010) | province | 1995/2024 | NSO terms; credit Cục Thống kê | no |
| `sentinel2_l2a_do_luong_vi` — Sentinel-2 L2A vegetation indices (NDVI, EVI, NDMI, 20 m) over the former Đô Lương district | INGESTED | ESA Copernicus (producer); Sinergise and Element 84 (COG conversion, Earth Search STAC); AWS Open Data (host) | 20 m (10 m bands block-averaged), EPSG:32648 | 2020-06-01..2021-06-30 and 2023-01-01..2024-12-31 (dates with eo:cloud_cover < 60) | Copernicus Sentinel data: free, full and open access under Regulation (EU) No 377/2014 and Commission Delegated Regulation (EU) No 1159/2013; notice required: 'Contains modified Copernicus Sentinel data 2020-2024' (https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice) | no |
| `study_p02` — P-02 trial results (the paper's tables) | INGESTED | Trịnh Đức Toàn et al. (2023); values transcribed by the Miaudow team | one 1,000 m2 trial plot per crop and season, Lưu Sơn, Đô Lương | 2020-06/2021-06 | Journal article; values quoted with citation | yes |
| `study_p03` — P-03 trial results (the paper's text) | INGESTED | Trịnh Đức Toàn et al. (2023); text transcribed by the Miaudow team | one 1,000 m2 trial plot per crop, Lưu Sơn, Đô Lương | 2020-06/2021-06 | Journal article; text quoted with citation | yes |
| `nasa_eco_l2t_lste` — NASA ECOSTRESS land surface temperature (ECO_L2T_LSTE) | BLOCKED | LP DAAC (LPCLOUD) | 70 m, irregular ISS overpass times | 2018-07-09T00:00:00.000Z .. ongoing | NASA open data (Earthdata Login required to download) | no |
| `nasa_eco_l3t_jet` — NASA ECOSTRESS evapotranspiration (ECO_L3T_JET) | BLOCKED | LP DAAC (LPCLOUD) | 70 m, irregular ISS overpass times | 2018-07-10T00:00:00.000Z .. ongoing | NASA open data (Earthdata Login required to download) | no |
| `nasa_gpm_3imergdf` — NASA GPM IMERG daily rain (GPM_3IMERGDF) | BLOCKED | GES DISC | 0.1° x 0.1°, daily | 1998-01-01T00:00:00.000Z .. 2025-09-30T23:59:59.999Z | NASA open data (Earthdata Login required to download) | no |
| `nasa_gpm_3imergm` — NASA GPM IMERG monthly rain (GPM_3IMERGM) | BLOCKED | GES DISC | 0.1° x 0.1°, monthly | 1998-01-01T00:00:00.000Z .. 2025-09-30T23:59:59.999Z | NASA open data (Earthdata Login required to download) | no |
| `nasa_hlsl30` — NASA HLS Landsat 30 m (HLSL30 v2.0) | BLOCKED | LP DAAC (LPCLOUD) | 30 m | 2013-04-11T00:00:00.000Z .. ongoing | NASA open data (Earthdata Login required to download) | no |
| `nasa_hlss30` — NASA HLS Sentinel-2 30 m (HLSS30 v2.0) | BLOCKED | LP DAAC (LPCLOUD) | 30 m, 2-3 day revisit with HLSL30 | 2015-11-28T00:00:00.000Z .. ongoing | NASA open data (Earthdata Login required to download) | no |
| `nasa_spl3smp_e` — NASA SMAP surface soil moisture 9 km (SPL3SMP_E) | BLOCKED | NSIDC DAAC (NSIDC_CPRD) | 9 km EASE-Grid 2.0, daily (AM/PM passes) | 2015-03-31T00:00:00.000Z .. ongoing | NASA open data (Earthdata Login required to download) | no |
| `nasa_spl4smgp` — NASA SMAP L4 soil moisture (SPL4SMGP) | BLOCKED | NSIDC DAAC (NSIDC_CPRD) | 9 km EASE-Grid 2.0, 3-hourly (model + assimilation) | 2015-03-31T00:00:00.000Z .. ongoing | NASA open data (Earthdata Login required to download) | no |

## Notes per dataset

### `chirps_v3_monthly` — CHIRPS v3 monthly rainfall

- Source: https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs/ (source id `X-CHIRPS-V3`), revision CHIRPS v3.0 final monthly global COGs (version 3.0 released 2025-01-01); directory listing dates of the 408 files used range 2025-Feb-25 18:27 to 2025-Feb-25 18:49; per-file dates in source_files, retrieved 2026-11-14T09:25:18Z
- Missing values: Kept beside NASA POWER, never merged; a missing month stays null.
- Allowed use: A second rain source beside NASA POWER. A satellite and station estimate, not measured at the field.
- SHA-256: `6dab8f962a4d54f7d4d4b3762be7b4cad58035b89795634661c22aeac9545aea`
- Status read from the MANIFEST.json of the fetch step.
- Licence: https://www.chc.ucsb.edu/data/chirps3 states verbatim: 'CHIRPS3 is in the public domain, as registered with Creative Commons, and is licensed under a Creative Commons Attribution 4.0 International License. To the extent possible under the law, the Climate Hazards Center has waived all copyright and related or neighboring rights to CHIRPS3.' The README states no licence. We record CC BY 4.0 and always attribute.
- Citation: CHIRPS3 Data Repository, https://doi.org/10.15780/G2JQ0P (2025); Funk, C. et al. (2026) The Climate Hazards Center Infrared Precipitation with Stations, Version 3. Sci Data 13, 718, https://doi.org/10.1038/s41597-026-07096-4.
- Only the final monthly/global/cogs directory is used, never prelim/; no month in 1991-2024 is a preliminary value.

### `e012_model` — Model test results E-012

- Source: — (source id `E-012`), revision freeze commit ea7a60c21d1867c4096fc3b3c4822b4127b53839, retrieved —
- Missing values: Copied unchanged.
- Allowed use: Tells whether the model is good enough to show.
- SHA-256: `f09b1b08380da4266f6853dcb5c0e1b4d8fbd940edbfcfa56f195bdaef1dfb82`

### `e019_hazard_labels` — Farmland share meeting each official rule (E-019)

- Source: — (source id `E-019`), revision hazard_labels.json schema 0.4, retrieved —
- Missing values: Copied unchanged.
- Allowed use: A mechanical reading of the Decision 18/2021 thresholds on past values; not an official record.
- SHA-256: `46ac61504f52c5dfab4b58a3ba39ea9c6d8f0dc14687871e3579c8b4614b29c1`

### `e020_soil_wetness` — Root-zone soil wetness while each crop was in the field (E-020)

- Source: — (source id `E-020`), revision soil_wetness.json schema 0.4, retrieved —
- Missing values: Copied unchanged.
- Allowed use: A model value, not a measurement; no good or bad threshold.
- SHA-256: `3ad4c7cc2ce06fd4891c567205a96b32761044c98477d410315a0babbc0cc48e`

### `geoboundaries_adm1` — Province boundaries (geoBoundaries ADM1, simplified)

- Source: https://www.geoboundaries.org/ (source id `X-GEOBOUNDARIES`), revision —, retrieved —
- Missing values: The build stops when Nghệ An is not in the file.
- Allowed use: Draw the province outline. Not a legal boundary.
- SHA-256: `010bff8d3244064bc8001033ba79acc1215a1fb6e568f6f8a90da7ecec2c2fc5`

### `geoboundaries_vnm_adm2_do_luong` — Former Đô Lương district boundary, Nghệ An — geoBoundaries ADM2

- Source: https://www.geoboundaries.org/api/current/gbOpen/VNM/ADM2/ (source id `VNM-ADM2-81297802`), revision geoBoundaries commit in download URL (9469f09); buildDate Dec 12, 2023; sourceDataUpdateDate Thu Jan 19 07:31:04 2023, retrieved 2026-11-14T10:29:56Z
- Missing values: No commune (ADM3) layer exists in geoBoundaries for Viet Nam; Lưu Sơn is null, not drawn from another source.
- Allowed use: Draw the study area and clip satellite data; not a legal boundary.
- SHA-256: `3217828a5154376ce026134aac2e6b04997a9dcaa6a91b68b32f3ae8da56a633`
- The outline is the former Đô Lương district: Viet Nam abolished the district level on 1 July 2025; the boundary is geoBoundaries (year represented 2020, OCHA ROAP / Government of Viet Nam), not a cadastral map.
- Computed area 354.2 km², +1.1 % from the published 350.433 km² (Vietnamese Wikipedia, Nghệ An 2019 statistics).
- The web outline is simplified (tolerance 0.0005°, about 50 m); for drawing only.
- The Lưu Sơn point is the commune marker on Wikidata, not the trial field. Lưu Sơn commune merged into the new Đô Lương commune in 2025.

### `modis_farmland_weights` — Farmland weight per grid cell (MODIS MCD12C1)

- Source: https://cmr.earthdata.nasa.gov/search/granules.json?short_name=MCD12C1&version=061 (source id `R-N02`), revision MCD12C1 v061, years 2001-2015, retrieved —
- Missing values: The build stops when Nghệ An has no weighted cell.
- Allowed use: Weight grid cells by their farmland share.
- SHA-256: `e16b06c6844655eda7aabed5fe52117dc7eedfb6185cedcc2e563eb746e58fef`
- One fixed map; misses later land-cover change.

### `modis_mod13q1_ndvi` — MODIS MOD13Q1 16-day NDVI

- Source: https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset (source id `X-MODIS-MOD13Q1`), revision MOD13Q1 collection 6.1 (v061); processing dates reported by the API: 2020286133559 to 2025006015707, retrieved 2026-11-14T09:43:44Z
- Missing values: Cloud-flagged pixels stay missing.
- Allowed use: Look at vegetation greenness. NDVI is not a crop diagnosis and is not a model input.
- SHA-256: `8626b5c78a929ca1000bd10f835fdded81bdb362881463d63f1038d988da8701`
- Status read from the MANIFEST.json of the fetch step.
- NDVI shows the greenness of the land surface; it is not a diagnosis of crop health, disease or soil moisture. A 250 m pixel mixes several fields (and houses, roads, perennial trees).
- The location is the Lưu Sơn commune marker on Wikidata (Q10788283), not the trial field; the block is +/-1 km around it.
- The date is the first day of the 16-day composite period; each pixel's actual observation day can be any day in that period.

### `nasa_power_daily` — NASA POWER daily (5 farmland cells of Nghệ An)

- Source: https://power.larc.nasa.gov/api/temporal/daily/point (source id `R-N01`), revision POWER Daily API v2.10.3, retrieved —
- Missing values: Fill value -999 read as missing; a month with any missing day has no total; the build stops when a weighted cell misses a day.
- Allowed use: Look back at past weather per model grid cell. Not measured at the field. A past year is not a forecast.
- SHA-256: `59bacd1a389ee5449835a534a2709f4842339557237a64075120d848c4bc0e81`
- The cached files in data/raw/power and data/raw/power_t2m do not record a download date, so retrieved_at is empty.

### `nso_rice_yield` — Province rice yield anomalies (NSO, risk table)

- Source: https://pxweb.nso.gov.vn/pxweb/en/ (source id `R-D01`), revision risk_table.json schema 0.4, retrieved —
- Missing values: Years without an NSO value stay null.
- Allowed use: Look at past province rice yields. Not the yield of one field.
- SHA-256: `ee4d8b314564cadcbf5161c29d75dca64b0179a41ceb1791a71ff52ed68b9c4f`

### `sentinel2_l2a_do_luong_vi` — Sentinel-2 L2A vegetation indices (NDVI, EVI, NDMI, 20 m) over the former Đô Lương district

- Source: https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a (source id `sentinel-2-l2a (Earth Search v1)`), revision processing baselines used: 02.14;05.00, 03.00, 03.00;05.00, 05.00, 05.00;05.00, 05.09, 05.09;05.09, 05.10, 05.10;05.10, 05.11, 05.11;05.11, retrieved 2026-11-14T10:30:05Z
- Missing values: Pixels outside SCL classes 4/5/6, with any band nodata, or with an undefined index are excluded, never filled; scenes with < 20 % valid pixels in the district are skipped and listed with the reason; composite pixels without any valid scene are transparent.
- Allowed use: Describe seasonal greenness across the former Đô Lương district; not a per-field diagnosis.
- SHA-256: `289844d8d679c3ffe76abfaca7b5613772776918eafc0be6c704da2af8a3b15b`
- 20 m pixels mix fields; NDVI is greenness, not yield, disease or soil moisture.
- Pre-2022 dates use the N05.00 reprocessing when it exists (same processor family as 2023-2024).
- Seasons do not overlap: September is split at day 15.
- The area is the former Đô Lương district (districts abolished July 2025).

### `study_p02` — P-02 trial results (the paper's tables)

- Source: https://vjol.info.vn/vaas/vi/article/download/167049/143292/289735 (source id `R-P02`), revision Tạp chí KH&CN Nông nghiệp Việt Nam 04(146): 43-51, retrieved —
- Missing values: A value the paper does not give stays absent.
- Allowed use: Reported results of one unreplicated trial at 2020-21 prices. Not expected income.
- SHA-256: `a916c75cb13a9ee393aadfa1a5b6fcb03b3b3aaf60ff08fb94fd516acc62bae3`
- Measured on the Lưu Sơn trial plots in 2020-21, not on your field.

### `study_p03` — P-03 trial results (the paper's text)

- Source: https://ngheandost.gov.vn/tap-chi-chuyen-san/tap-chi-kh-cn-nghe-an/dac-san-kh-cn-nghe-an-so-2-2023-112.html?download=1&id=0 (source id `R-P03`), revision Đặc san KH&CN Nghệ An 2/2023, retrieved —
- Missing values: No sowing or harvest dates are reported; they stay absent.
- Allowed use: Reported results, as text only; profit subtracts material costs only.
- SHA-256: `a916c75cb13a9ee393aadfa1a5b6fcb03b3b3aaf60ff08fb94fd516acc62bae3`

### `nasa_eco_l2t_lste` — NASA ECOSTRESS land surface temperature (ECO_L2T_LSTE)

- Source: https://cmr.earthdata.nasa.gov/search/concepts/C2076090826-LPCLOUD.html (source id `X-NASA-EARTHDATA`), revision 002, retrieved 2026-11-14T10:32:21Z
- Missing values: Not downloaded; nothing is shown from it.
- Allowed use: land surface temperature (crop heat stress context)
- 190 granules over Đô Lương for 2020–2021 found through NASA CMR, but downloading needs a free Earthdata Login; none is configured, so nothing is used.

### `nasa_eco_l3t_jet` — NASA ECOSTRESS evapotranspiration (ECO_L3T_JET)

- Source: https://cmr.earthdata.nasa.gov/search/concepts/C2076106409-LPCLOUD.html (source id `X-NASA-EARTHDATA`), revision 002, retrieved 2026-11-14T10:32:21Z
- Missing values: Not downloaded; nothing is shown from it.
- Allowed use: evapotranspiration (crop water use context)
- 86 granules over Đô Lương for 2020–2021 found through NASA CMR, but downloading needs a free Earthdata Login; none is configured, so nothing is used.

### `nasa_gpm_3imergdf` — NASA GPM IMERG daily rain (GPM_3IMERGDF)

- Source: https://cmr.earthdata.nasa.gov/search/concepts/C2723754864-GES_DISC.html (source id `X-NASA-EARTHDATA`), revision 07, retrieved 2026-11-14T10:32:21Z
- Missing values: Not downloaded; nothing is shown from it.
- Allowed use: daily precipitation (satellite + gauge)
- 731 granules over Đô Lương for 2020–2021 found through NASA CMR, but downloading needs a free Earthdata Login; none is configured, so nothing is used.

### `nasa_gpm_3imergm` — NASA GPM IMERG monthly rain (GPM_3IMERGM)

- Source: https://cmr.earthdata.nasa.gov/search/concepts/C2723754851-GES_DISC.html (source id `X-NASA-EARTHDATA`), revision 07, retrieved 2026-11-14T10:32:21Z
- Missing values: Not downloaded; nothing is shown from it.
- Allowed use: monthly precipitation (satellite + gauge)
- 24 granules over Đô Lương for 2020–2021 found through NASA CMR, but downloading needs a free Earthdata Login; none is configured, so nothing is used.

### `nasa_hlsl30` — NASA HLS Landsat 30 m (HLSL30 v2.0)

- Source: https://cmr.earthdata.nasa.gov/search/concepts/C2021957657-LPCLOUD.html (source id `X-NASA-EARTHDATA`), revision 2.0, retrieved 2026-11-14T10:32:21Z
- Missing values: Not downloaded; nothing is shown from it.
- Allowed use: field-scale vegetation time series (Landsat 8/9 part)
- 119 granules over Đô Lương for 2020–2021 found through NASA CMR, but downloading needs a free Earthdata Login; none is configured, so nothing is used.

### `nasa_hlss30` — NASA HLS Sentinel-2 30 m (HLSS30 v2.0)

- Source: https://cmr.earthdata.nasa.gov/search/concepts/C2021957295-LPCLOUD.html (source id `X-NASA-EARTHDATA`), revision 2.0, retrieved 2026-11-14T10:32:21Z
- Missing values: Not downloaded; nothing is shown from it.
- Allowed use: field-scale vegetation time series (NDVI/EVI) harmonised with Landsat
- 200 granules over Đô Lương for 2020–2021 found through NASA CMR, but downloading needs a free Earthdata Login; none is configured, so nothing is used.

### `nasa_spl3smp_e` — NASA SMAP surface soil moisture 9 km (SPL3SMP_E)

- Source: https://cmr.earthdata.nasa.gov/search/concepts/C2938664763-NSIDC_CPRD.html (source id `X-NASA-EARTHDATA`), revision 006, retrieved 2026-11-14T10:32:21Z
- Missing values: Not downloaded; nothing is shown from it.
- Allowed use: surface soil moisture (top ~5 cm), coarse context only
- 731 granules over Đô Lương for 2020–2021 found through NASA CMR, but downloading needs a free Earthdata Login; none is configured, so nothing is used.

### `nasa_spl4smgp` — NASA SMAP L4 soil moisture (SPL4SMGP)

- Source: https://cmr.earthdata.nasa.gov/search/concepts/C3480440870-NSIDC_CPRD.html (source id `X-NASA-EARTHDATA`), revision 008, retrieved 2026-11-14T10:32:21Z
- Missing values: Not downloaded; nothing is shown from it.
- Allowed use: surface and root-zone soil moisture (modelled), coarse context only
- 5849 granules over Đô Lương for 2020–2021 found through NASA CMR, but downloading needs a free Earthdata Login; none is configured, so nothing is used.

## Methods

| Method | What it does | Sources |
|---|---|---|
| `sum_daily_precip_complete_month` | Sum of daily PRECTOTCORR over every day of the month. A month with a missing day stays empty; nothing is guessed. | R-N01 |
| `sum_complete_months` | Sum of the 12 monthly totals; empty when a month is empty. | R-N01 |
| `anomaly_vs_1991_2020_normal` | Monthly total minus the 1991-2020 mean of the same month (mm), and divided by that mean (%). | R-N01, R-A15 |
| `count_days_t2m_max_ge_35` | Count of days with T2M_MAX at or above 35 °C, the lower bound of Decision 18/2021 Art. 47.1 a. A day count, not a heat spell under the rule. | R-A01, R-N01 |
| `count_days_t2m_le_13` | Count of days with daily mean T2M at or below 13 °C, the upper bound of Art. 53.1 a. A day count, not a cold spell under the rule. | R-A01, R-N01 |
| `etccdi_cdd_calendar_year` | The longest run of consecutive days in the calendar year with rain below 1 mm (ETCCDI CDD index). A spell is cut at 1 January. | R-A10, R-N01 |
| `art48_drought_rain_month` | A month whose rain total is more than 50% below the 1991-2020 mean of that month (rain part of Art. 48.1 only; the surface-water part cannot be computed). | R-A01, R-N01, R-A15 |
| `farmland_weighted_mean` | The 5 cell values times their MODIS farmland weights, divided by the weight sum. Empty when any cell is empty. | R-N02 |
| `E-019` | Apply the level-1 thresholds of Decision 18/2021 to each grid cell over the crop's field time, then add the farmland weights of the cells that meet them. | E-019, R-A01, R-N01, R-N02 |
| `E-020` | Farmland-weighted mean GWETROOT over the crop's field time, next to its 1991-2020 mean. | E-020, R-W12, R-N01 |
| `E-012` | Ridge regression (M1) and gates G1-G4 on the test years 2016-2024. | E-012, E-010, R-D01 |
| `E-022` | Sum of the season profits of a plan, counts of crops, legumes and days with a crop in the field, from cited values. | E-022, R-P02, R-B01 |
| `study_table_copy` | A number copied unchanged from the paper's table, with table and page. | R-P02, R-P03 |
| `live_power_complete_month` | Fetch daily values for one point from the NASA POWER API; monthly totals and mean maximum temperature only for complete months. | R-N01 |
| `chirps_monthly_cell` | CHIRPS v3 monthly total per NASA POWER cell, kept beside POWER, never merged. | X-CHIRPS-V3 |

## Displayed metrics

| Metric | Unit | Method | Does not prove |
|---|---|---|---|
| `monthly_rain_total` — Monthly rain total | mm | `sum_daily_precip_complete_month` | A model grid value does not tell the rain or temperature on your field. |
| `monthly_rain_anomaly_mm` — Monthly rain anomaly (mm) | mm | `anomaly_vs_1991_2020_normal` | A past year is not a forecast. |
| `monthly_rain_anomaly_pct` — Monthly rain anomaly (%) | % | `anomaly_vs_1991_2020_normal` | A past year is not a forecast. |
| `monthly_rain_normal` — 1991-2020 monthly rain normal | mm | `anomaly_vs_1991_2020_normal` | A model grid value does not tell the rain or temperature on your field. |
| `annual_rain_total` — Annual rain total | mm | `sum_complete_months` | A model grid value does not tell the rain or temperature on your field. |
| `hot_days` — Hot days at or above 35 °C | days | `count_days_t2m_max_ge_35` | Not the number of heat spells under Decision 18/2021. |
| `cold_days` — Cold days at or below 13 °C | days | `count_days_t2m_le_13` | Not the number of cold spells under Decision 18/2021. |
| `longest_dry_spell` — Longest dry spell | days | `etccdi_cdd_calendar_year` | Does not tell whether the field had irrigation water. |
| `drought_rain_months` — Drought-rain months under Art. 48 | months | `art48_drought_rain_month` | Not an official drought declaration; the surface-water part of Art. 48 cannot be computed. |
| `hazard_share` — Farmland share meeting a rule | share 0-1 | `E-019` | Not an official disaster record; does not say your field was affected. |
| `soil_wetness` — Root-zone soil wetness | 0-1 | `E-020` | Not a field moisture measurement; no good or bad threshold. |
| `reported_profit` — Reported net profit | thousand VND/ha | `study_table_copy` | A 2020-21 result of one unreplicated plot; not expected income. |
| `reported_cost` — Reported total cost | thousand VND/ha | `study_table_copy` | 2020-21 prices; this year's cost may differ. |
| `year_profit_total` — Whole-year profit (sum) | thousand VND/ha | `E-022` | The paper does not say one field carried the whole plan. |
| `crops_in_year` — Crops in the year | crops | `E-022` | Says nothing about soil improvement. |
| `legume_count` — Legume crops | crops | `E-022` | Does not say how much nitrogen is fixed in a field. |
| `living_days` — Days with a crop in the field | days | `E-022` | The paper does not say the seasons followed each other on one field. |

## NASA GIBS imagery layers (visual source, not evidence)

14 layers verified against the WMTS capabilities with one real tile request each.

| Layer | Time range | Format |
|---|---|---|
| `BlueMarble_ShadedRelief_Bathymetry` |  …  | — |
| `BlueMarble_NextGeneration` |  …  | — |
| `VIIRS_SNPP_CorrectedReflectance_TrueColor` |  …  | — |
| `MODIS_Terra_CorrectedReflectance_TrueColor` |  …  | — |
| `VIIRS_Black_Marble` |  …  | — |
| `VIIRS_SNPP_DayNightBand_At_Sensor_Radiance` |  …  | — |
| `MODIS_Terra_NDVI_8Day` |  …  | — |
| `MODIS_Terra_L3_NDVI_16Day` |  …  | — |
| `MODIS_Terra_L3_NDVI_Monthly` |  …  | — |
| `IMERG_Precipitation_Rate` |  …  | — |
| `SMAP_L4_Analyzed_Surface_Soil_Moisture` |  …  | — |
| `SMAP_L4_Analyzed_Root_Zone_Soil_Moisture` |  …  | — |
| `Coastlines_15m` |  …  | — |
| `Reference_Labels_15m` |  …  | — |

## Lineage

`data/raw/*` (immutable fetches with a manifest each) → `pipeline/build_canonical.py` (validation, complete-month
rule, rule thresholds, farmland weighting) → `data/canonical/*.json` (one copy) → `api/miaudow_api` tools and
the web app (Vite alias `@data`) → charts, 3D layers, plan cards and copilot answers. A missing input stops the
build; nothing is interpolated or filled with zero.
