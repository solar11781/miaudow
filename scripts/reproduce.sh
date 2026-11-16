#!/usr/bin/env bash
# Rebuild every derived table from the original public downloads (CR-07, NFR-02). Run from the repository root.
set -euo pipefail
export PYTHONPATH=src
export PYTHONUTF8=1  # Windows consoles default to cp1252; the reports print Vietnamese names

pip install -r requirements-dev.lock

# 1. NSO crop statistics: one PX-Web web-form export per table (the JSON API does not expose the agriculture DB).
for t in E06.13 E06.14 E06.15 E06.16 E06.17 E06.18 E06.19 E06.20 E06.21 E06.22 E06.23 E06.24 E06.25 E06.26 E06.27 E06.34 E06.35; do
  [ -f "data/raw/nso/$t.csv" ] || python scripts/nso_export.py "$t" "data/raw/nso/$t.csv"   # adds a MANIFEST row
done
python scripts/build_crop_stats.py   # retrieval dates from data/MANIFEST.csv (sha256 match)

# 2. Province boundaries (recorded URL and sha256 in data/MANIFEST.csv), NASA MODIS land cover 2001-2015
#    (Earthdata login: EARTHDATA_TOKEN) and the fixed farmland mask.
BOUNDARIES=data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson
[ -f "$BOUNDARIES" ] || python scripts/fetch_recorded.py "$BOUNDARIES"
pip install pyhdf==0.11.7
python scripts/modis_landcover.py 2001 2015
python scripts/build_cell_weights.py
python scripts/build_grid_figure.py   # artifacts/figures/nghe_an_grid.svg for the method page (D-135)

# 3. NASA POWER daily data for every weighted cell (cached files are reused), then the training feature table.
python scripts/download_power.py
python scripts/download_power.py t2m
python scripts/build_training_table.py
python scripts/choose_normal.py   # E-010: the normal-yield method, before the freeze commit
python scripts/run_primary_test.py   # E-012: references and M1, writes artifacts/metrics.json and gates.json
python scripts/export_risk_table.py   # artifacts/risk_table.json for the app (05-DATA-CONTRACTS section 5)
python scripts/export_crop_exposure.py   # E-019 hazard_labels.json and E-020 soil_wetness.json per P-02 crop and year
python scripts/run_secondary_models.py   # E-013 M2 LightGBM, E-017 M3 random forest (secondary, method page)
python scripts/run_sensitivity.py   # E-018 sensitivity runs a-c, E-008 windows and centroid cells
DESINVENTAR=data/raw/desinventar/DI_export_vnm.zip   # R-A19, for the E-016 check only; never committed (D-54)
[ -f "$DESINVENTAR" ] || python scripts/fetch_recorded.py "$DESINVENTAR"
python scripts/run_method_reports.py   # method page reports: E-012/E-018 winter claim, setup choices, E-014, E-016
python scripts/build_results_chart.py   # artifacts/figures/results_chart.svg for the slides and the method page
python scripts/build_figures.py   # docs/figures: rice yield history and farmland rule shares for the README and submission

# 3b. NASA GPM IMERG Final monthly for the Nghệ An box (Earthdata token; satellite rain check, D-135, 05 §5c).
#     FIELDSHIFT_SKIP_IMERG=1 skips the download; without the 288 files the next step stops.
python scripts/download_imerg_monthly.py
python scripts/build_rain_check.py   # artifacts/rain_check.json, IMERG against POWER monthly rain (05 §5c)

# 3c. Static snapshot of real API answers for the offline demo build (frontend/snapshot/, D-150).
python scripts/build_snapshot.py

# 3d. The docs/figures PNGs and png_sources.json are rendered by hand from the committed SVGs with headless Edge
#     (command in docs/figures/README.md); no script does it.

# 4. Tests.
pytest -q
