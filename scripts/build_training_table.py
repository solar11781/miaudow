"""Build data/processed/training_table.csv from the cleaned NSO labels, farmland weights and cached NASA POWER data.

Usage: PYTHONPATH=src python scripts/build_training_table.py
All steps are tested library functions; this script only wires them together and writes provenance counts.
"""

import glob
import json

import pandas as pd

from fieldshift.data.power import parse_daily
from fieldshift.data.series import prepare_series
from fieldshift.features.feature_table import build_feature_table
from fieldshift.features.season_windows import calendar_region

NSO_EXPORT = "data/raw/nso/E06.14.csv"

labels = pd.read_csv("data/processed/crop_stats.csv")
series, removed = prepare_series(labels[~labels["is_preliminary"]])
series = series[series["yield_t_ha"].notna()]
weights = pd.read_csv("data/processed/cell_weights.csv")  # fixed mask, D-106 (scripts/build_cell_weights.py)

cells = {}
for f in glob.glob("data/raw/power/power_*_19900101_20241231_*.json"):
    with open(f) as fh:
        payload = json.load(fh)
    lon, lat = payload["geometry"]["coordinates"][:2]
    cells[(round(lat, 6), round(lon, 6))] = parse_daily(payload)
for f in glob.glob("data/raw/power_t2m/power_*_19900101_20241231_*.json"):  # daily mean T2M (D-72 cold counts)
    with open(f) as fh:
        payload = json.load(fh)
    lon, lat = payload["geometry"]["coordinates"][:2]
    key = (round(lat, 6), round(lon, 6))
    if key in cells:
        cells[key] = cells[key].join(parse_daily(payload)[["T2M"]], how="left")

provinces = sorted(set(series["province_nso"]))
regions = {p: calendar_region(p, NSO_EXPORT) for p in provinces}
table, skipped = build_feature_table(series, weights, cells, regions)
table.to_csv("data/processed/training_table.csv", index=False)
skipped.to_csv("data/processed/training_table_skipped.csv", index=False)
print(
    "rows:",
    len(table),
    "| by season:",
    table.groupby("season").size().to_dict(),
    "| provinces:",
    table["province_nso"].nunique(),
    "| years:",
    table["year"].min(),
    "-",
    table["year"].max(),
)
print("skipped:", len(skipped), skipped["reason"].value_counts().to_dict())
print("feature NaNs:", int(table.filter(like="_").isna().sum().sum()))
