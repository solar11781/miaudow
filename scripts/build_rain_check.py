"""Write artifacts/rain_check.json: the satellite rain check of NASA IMERG against NASA POWER (05-DATA-CONTRACTS §5c).

Usage: PYTHONPATH=src python scripts/build_rain_check.py   (after scripts/download_imerg_monthly.py and download_power.py)
Reads data/raw/imerg_monthly (288 monthly replies), data/raw/power and the farmland weights of data/processed.
"""

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from fieldshift.data import imerg
from fieldshift.data.power import POWER_CACHE_FILES, load_cells
from fieldshift.features import rain_check
from fieldshift.ml.primary_test import SCHEMA_VERSION

PROVINCE = "Nghe An"  # province_nso spelling of cell_weights.csv
IMERG_DIR = Path("data/raw/imerg_monthly")

weights_table = pd.read_csv("data/processed/cell_weights.csv")  # fixed farmland mask, D-106
in_mask = (weights_table["province_nso"] == PROVINCE) & (weights_table["method"] == "farmland_weighted")
weights = {
    (round(r.lat, 6), round(r.lon, 6)): float(r.farmland_weight)
    for r in weights_table[in_mask & (weights_table["farmland_weight"] > 0)].itertuples()
}
cells, _unmatched = load_cells("data/raw/power", "data/raw/power_t2m", POWER_CACHE_FILES)
missing = [c for c in weights if c not in cells]
if missing:
    raise ValueError(f"cached POWER series missing for the weighted {PROVINCE} cells {missing}")
power_mm = {c: rain_check.power_monthly_totals(cells[c]["PRECTOTCORR"]) for c in weights}

box = imerg.box_for_cells(weights)
files = sorted(IMERG_DIR.glob("*.ascii"))
texts = {imerg.file_month(f.name): f.read_text(encoding="utf-8") for f in files}
if len(texts) != len(files):
    raise SystemExit(f"two IMERG files for one month in {IMERG_DIR}: {len(files)} files, {len(texts)} months")
print(f"IMERG monthly files read: {len(files)}")
imerg_mm = rain_check.imerg_cell_months(texts, box, weights)

months = rain_check.months_between(rain_check.FIRST_YEAR, rain_check.LAST_YEAR)
body = rain_check.rain_check(imerg_mm, power_mm, weights, months)
git = shutil.which("git")
if git is None:
    raise RuntimeError("git not found: the artifact records the commit it was made from")
head = subprocess.run([git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True)  # noqa: S603  fixed arguments
doc = {
    "schema_version": SCHEMA_VERSION,
    "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    "freeze_commit": head.stdout.strip(),
    **body,
}
Path("artifacts", "rain_check.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8", newline="\n")
print(f"rain_check.json: {body['n_months']} months, {body['n_dropped']} dropped, cc {body['cc']:.4f}")
