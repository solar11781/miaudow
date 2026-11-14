"""Pre-registered sensitivity runs E-018 (a, b, c) and robustness runs E-008 (windows, centroid) (03-ML-SPEC 7).

Usage: PYTHONPATH=src python scripts/run_sensitivity.py   (after scripts/run_primary_test.py)
Each run repeats the rolling-origin test of E-012 with one change and adds its metric rows (references and M1, per
model season, national) to artifacts/metrics.json, replacing earlier sensitivity rows. Choices of the team
(2026-11-14): run c uses the farmland shares meeting the heavy-rain, heat and cold rules; the window runs move the
whole window one month earlier, one month later, and one month wider on both ends. They never replace the primary
result (D-83).
"""

import json
from pathlib import Path

import pandas as pd

from fieldshift.data.boundaries import province_geometries
from fieldshift.data.power import load_cells
from fieldshift.data.series import prepare_series
from fieldshift.features.farmland_weights import centroid_weights
from fieldshift.features.feature_table import build_cell_month_rain, build_feature_table, build_risk_level_features
from fieldshift.features.season_windows import calendar_region, nso_regions
from fieldshift.ml import evaluation as ev
from fieldshift.ml.fold_features import DROUGHT_COLS, FOLD_RAIN, make_fold_transform, model_columns
from fieldshift.ml.primary_test import MODELS, STORED_FEATURES, app_season, bilingual, metric_row, model_rows
from fieldshift.ml.runner import ALPHA_GRID, run_rolling_origin

SEED = 0  # fixed seed of the year bootstrap (python rules)
NSO_EXPORT = "data/raw/nso/E06.14.csv"
BASIC_COUNTS = ["hot_days_d", "official_heavy_rain_d", "ret_hai_d", "ret_dam_d"]  # replaced in run c (D-95)
RISK_SHARES = ["risk_heavy_rain", "risk_heat", "risk_cold"]
WINDOWS = {  # E-008 window runs: months added to the window's start and end
    (-1, -1): bilingual("Cả khung thời gian sớm hơn 1 tháng", "Whole window one month earlier"),
    (1, 1): bilingual("Cả khung thời gian muộn hơn 1 tháng", "Whole window one month later"),
    (-1, 1): bilingual("Khung thời gian rộng thêm 1 tháng ở hai đầu", "Window one month wider on both ends"),
}
METRICS = Path("artifacts/metrics.json")
region_of = nso_regions(NSO_EXPORT)


def run(table: pd.DataFrame, month_rain: pd.DataFrame, stored: list[str], drop_fao: bool = False) -> pd.DataFrame:
    """Rolling-origin predictions of the references and M1 with these features, labelled with the season."""
    rows = model_rows(table, region_of)
    if drop_fao:
        rows = rows[~rows["fao_flagged"]].reset_index(drop=True)
    weather, context = model_columns([*stored, FOLD_RAIN, *DROUGHT_COLS], stored=stored)
    pred = run_rolling_origin(
        rows, weather, context, ALPHA_GRID, fold_transform=make_fold_transform(stored, month_rain)
    )
    return pred["predictions"].assign(season=pred["predictions"]["series_id"].str.split("|").str[2])


def records(pred: pd.DataFrame, sensitivity: str, detail: dict | None, experiment: str, stat: str = "skill") -> list:
    out = []
    for season in ev.ML_SEASONS:
        part = pred[pred["season"] == season]
        for col, model_id in MODELS.items():
            out.append(
                {
                    "model_id": model_id,
                    "season": app_season(season),
                    "role": "reference" if col in ("b0", "b2", "bnw") else "secondary",
                    "scheme": "rolling_origin",
                    "sensitivity": sensitivity,
                    "detail": detail,
                    "subset": "national",
                    **metric_row(part, col, seed=SEED, stat=stat),
                    "source_ids": [experiment],
                }
            )
    return out


def rebuilt(weights: pd.DataFrame, shift: tuple[int, int] = (0, 0)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Training table and monthly cell rain rebuilt with other weights or windows (same labels and cells)."""
    table, _skipped = build_feature_table(series, weights, cells, regions, shift=shift)
    return table, build_cell_month_rain(series, weights, cells, regions, shift=shift)


table = pd.read_csv("data/processed/training_table.csv")
month_rain = pd.read_csv("data/processed/cell_month_rain.csv")
stats = pd.read_csv("data/processed/crop_stats.csv")
series, _removed = prepare_series(stats[~stats["is_preliminary"]])
series = series[series["yield_t_ha"].notna()]
weights = pd.read_csv("data/processed/cell_weights.csv")
cells, _unmatched = load_cells("data/raw/power", "data/raw/power_t2m", "power_*_19900101_20241231_*.json")
regions = {p: calendar_region(p, NSO_EXPORT) for p in sorted(set(series["province_nso"]))}

new = []
primary = pd.read_csv("data/processed/e012_predictions.csv")  # written by run_primary_test.py
new += records(primary, "mae_skill", None, "E-018", stat="mae_skill")
print("b done")
new += records(run(table, month_rain, STORED_FEATURES, drop_fao=True), "no_fao_flagged", None, "E-018")
print("a done")
risk = build_risk_level_features(series, weights, cells, regions)
with_risk = table.merge(risk, on=["province_nso", "season", "year"], how="left", validate="one_to_one")
stored_c = [c for c in STORED_FEATURES if c not in BASIC_COUNTS] + RISK_SHARES
new += records(run(with_risk, month_rain, stored_c), "risk_level_features", None, "E-018")
print("c done")
for shift, detail in WINDOWS.items():
    shifted_table, shifted_rain = rebuilt(weights, shift)
    new += records(run(shifted_table, shifted_rain, STORED_FEATURES), "window", detail, "E-008")
    print("window", shift, "done")
geoms = province_geometries(
    "data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson", "data/reference/admin_units.csv"
)
centroid_table, centroid_rain = rebuilt(centroid_weights(geoms))
new += records(run(centroid_table, centroid_rain, STORED_FEATURES), "centroid_points", None, "E-008")
print("centroid done")

doc = json.loads(METRICS.read_text(encoding="utf-8"))
doc["metrics"] = [r for r in doc["metrics"] if r["sensitivity"] is None] + new
METRICS.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
for r in new:
    if r["model_id"] == "m1_ridge":
        label = r["sensitivity"] + (f" {r['detail']['en']}" if r["detail"] else "")
        print(label, r["season"], {k: round(r[k]["value"], 3) for k in ("skill_vs_b0", "skill_vs_bnw")})
