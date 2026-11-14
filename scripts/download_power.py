"""Download (or reuse the cache of) NASA POWER daily data for every weighted cell in data/processed/cell_weights.csv.

Usage: PYTHONPATH=src python scripts/download_power.py [t2m]
Default: the main daily parameters into data/raw/power; "t2m": daily mean T2M into data/raw/power_t2m (D-72 cold
counts). Cached cells are not requested again; failures are reported, never filled (power_batch.download_cells).
Each newly downloaded file gets a data/MANIFEST.csv row (url, date, sha256), as in download_imerg_monthly.py.
"""

import csv
import sys
from datetime import UTC, date, datetime

from fieldshift.data.manifest import append_rows
from fieldshift.data.power_batch import download_cells, manifest_row

# cell_weights.csv is committed (05-DATA-CONTRACTS §3), so a fresh clone has the cell list.
with open("data/processed/cell_weights.csv", newline="") as f:
    cells = sorted({(float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f)})
t2m = len(sys.argv) > 1 and sys.argv[1] == "t2m"
report = download_cells(
    cells,
    (date(1990, 1, 1), date(2024, 12, 31)),
    "data/raw/power_t2m" if t2m else "data/raw/power",
    **({"parameters": ("T2M",)} if t2m else {}),
)
new = [r for r in report if r["status"] == "ok" and not r["cached"]]
today = datetime.now(UTC).date().isoformat()
added = append_rows(
    "data/MANIFEST.csv",
    [
        manifest_row(
            r,
            "nasa_power_t2m" if t2m else "nasa_power_cache",
            today,
            "scripts/download_power.py (POWER daily API JSON)",
        )
        for r in new
    ],
)
print(
    "ok:",
    sum(r["status"] == "ok" for r in report),
    "| new manifest rows:",
    added,
    "| failed:",
    [r for r in report if r["status"] != "ok"],
)
