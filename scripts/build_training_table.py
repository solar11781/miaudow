"""Build data/processed/training_table.csv from the cleaned NSO labels, farmland weights and cached NASA POWER data.

Usage: PYTHONPATH=src python scripts/build_training_table.py
All steps are tested library functions; this script only wires them together and writes provenance counts.
"""

import pandas as pd

from fieldshift.data.power import POWER_CACHE_FILES, load_cells
from fieldshift.data.series import prepare_series
from fieldshift.features.feature_table import build_cell_month_rain, build_feature_table
from fieldshift.features.season_windows import calendar_region

NSO_EXPORT = "data/raw/nso/E06.14.csv"

labels = pd.read_csv("data/processed/crop_stats.csv")
series, removed = prepare_series(labels[~labels["is_preliminary"]])
series = series[series["yield_t_ha"].notna()]
weights = pd.read_csv("data/processed/cell_weights.csv")  # fixed mask, D-106 (scripts/build_cell_weights.py)

# daily mean T2M (D-72 cold counts) joins from its own cache
cells, unmatched_t2m = load_cells("data/raw/power", "data/raw/power_t2m", POWER_CACHE_FILES)

provinces = sorted(set(series["province_nso"]))
regions = {p: calendar_region(p, NSO_EXPORT) for p in provinces}
table, skipped = build_feature_table(series, weights, cells, regions)
table.to_csv("data/processed/training_table.csv", index=False)
skipped.to_csv("data/processed/training_table_skipped.csv", index=False)
# monthly cell rain for the per-fold drought months of the model (05-DATA-CONTRACTS section 4a, D-66)
month_rain = build_cell_month_rain(series, weights, cells, regions)
month_rain.to_csv("data/processed/cell_month_rain.csv", index=False)
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
print("T2M files without a POWER cell (not used):", len(unmatched_t2m), sorted(unmatched_t2m))
print("skipped:", len(skipped), skipped["reason"].value_counts().to_dict())
print("cell month rain rows:", len(month_rain))
print("feature NaNs:", int(table.filter(like="_").isna().sum().sum()))
