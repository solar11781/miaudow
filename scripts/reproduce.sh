#!/usr/bin/env bash
# Rebuild every derived table from the original public downloads (CR-07, NFR-02). Run from the repository root.
# Stages written during the event (hazard labels, models, artifacts) are added here then.
set -euo pipefail
export PYTHONPATH=src

pip install -r requirements-dev.lock

# 1. NSO crop statistics: one PX-Web web-form export per table (the JSON API does not expose the agriculture DB).
for t in E06.13 E06.14 E06.15 E06.16 E06.17 E06.18 E06.19 E06.20 E06.21 E06.22 E06.23 E06.24 E06.25 E06.26 E06.27 E06.34 E06.35; do
  [ -f "data/raw/nso/$t.csv" ] || python scripts/nso_export.py "$t" "data/raw/nso/$t.csv"   # adds a MANIFEST row
done
python scripts/build_crop_stats.py   # retrieval dates from data/MANIFEST.csv (sha256 match)

# 2. NASA MODIS land cover 2001-2015 (Earthdata login) and the fixed farmland mask.
pip install pyhdf==0.11.7
python scripts/modis_landcover.py 2001 2015
python scripts/build_cell_weights.py

# 3. NASA POWER daily data for every weighted cell (cached files are reused), then the training feature table.
python scripts/download_power.py
python scripts/download_power.py t2m
python scripts/build_training_table.py

# 3b. NASA GPM IMERG Final monthly for the Nghệ An box (Earthdata token; satellite rain check, D-135, 05 §5c).
#     FIELDSHIFT_SKIP_IMERG=1 skips it while the rain check is not built.
python scripts/download_imerg_monthly.py

# 4. Tests.
pytest -q
