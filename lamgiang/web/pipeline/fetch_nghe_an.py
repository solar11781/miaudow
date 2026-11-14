"""Download (or reuse) NASA POWER daily data for the five farmland-weighted Nghe An cells.

Run from the repository root with its virtual environment:
    PYTHONPATH=src .venv/Scripts/python web/pipeline/fetch_nghe_an.py
Uses the same request (1990-01-01..2024-12-31, community AG) and cache folders as scripts/download_power.py,
so the files are shared with the main pipeline. Nothing is filled in when a request fails.
"""

import csv
import sys
from datetime import date

from fieldshift.data.power import PowerRequest, fetch_daily

with open("data/processed/cell_weights.csv", newline="") as f:
    cells = sorted({(float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f) if r["province_nso"] == "Nghe An"})

failed = 0
for lat, lon in cells:
    for params, folder in ((None, "data/raw/power"), (("T2M",), "data/raw/power_t2m")):
        req = PowerRequest(lat, lon, date(1990, 1, 1), date(2024, 12, 31), **({"parameters": params} if params else {}))
        try:
            daily, _ = fetch_daily(req, folder)
            sys.stdout.write(f"ok {lat} {lon} {folder} rows={len(daily)}\n")
        except Exception as exc:  # report and continue; no value is invented
            failed += 1
            sys.stdout.write(f"FAILED {lat} {lon} {folder}: {exc}\n")
sys.exit(1 if failed else 0)
