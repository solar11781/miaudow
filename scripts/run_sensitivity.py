"""Pre-registered sensitivity runs E-018 (a, b, c) and robustness runs E-008 (windows, centroid) (03-ML-SPEC 7).

Usage: PYTHONPATH=src python scripts/run_sensitivity.py   (after scripts/run_primary_test.py)
Each run repeats the rolling-origin test of E-012 with one change and adds its metric rows (references and M1, per
model season, national) to artifacts/metrics.json, replacing earlier sensitivity rows. Choices of the team
(2026-11-14): run c uses the farmland shares meeting the heavy-rain, heat and cold rules; the window runs move the
whole window one month earlier, one month later, and one month wider on both ends. They never replace the primary
result (D-83).
"""

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from fieldshift.data.boundaries import province_geometries
from fieldshift.data.power import POWER_CACHE_FILES, load_cells
from fieldshift.data.series import prepare_series
from fieldshift.features.climate import OFFICIAL_COUNT_COLS
from fieldshift.features.farmland_weights import centroid_weights
from fieldshift.features.feature_table import build_cell_month_rain, build_feature_table, build_risk_level_features
from fieldshift.features.hazards import RISK_SHARE_COLS
from fieldshift.features.season_windows import calendar_region, nso_regions
from fieldshift.ml import evaluation as ev
from fieldshift.ml.fold_features import DROUGHT_COLS, FOLD_RAIN, make_fold_transform, model_columns
from fieldshift.ml.primary_test import (
    MODELS,
    REFERENCES,
    STORED_FEATURES,
    bilingual,
    label_predictions,
    metric_row,
    model_rows,
    national_record,
)
from fieldshift.ml.runner import ALPHA_GRID, LEFT_OUT, run_rolling_origin

SEED = 0  # fixed seed of the year bootstrap (python rules)
NSO_EXPORT = "data/raw/nso/E06.14.csv"
WINDOWS = {  # E-008 window runs: months added to the window's start and end
    (-1, -1): bilingual("Cả khung thời gian sớm hơn 1 tháng", "Whole window one month earlier"),
    (1, 1): bilingual("Cả khung thời gian muộn hơn 1 tháng", "Whole window one month later"),
    (-1, 1): bilingual("Khung thời gian rộng thêm 1 tháng ở hai đầu", "Window one month wider on both ends"),
}
METRICS = Path("artifacts/metrics.json")
region_of = nso_regions(NSO_EXPORT)


def run(table: pd.DataFrame, month_rain: pd.DataFrame, stored: list[str], drop_fao: bool = False) -> pd.DataFrame:
    """Rolling-origin predictions of the references and M1 with these features, labelled with the season. drop_fao:
    FAO-flagged rows are never trained on or scored, but stay for the normals and B2 (E-018 a, team 2026-11-14)."""
    rows = model_rows(table, region_of)
    if drop_fao:
        rows = rows.assign(**{LEFT_OUT: rows["fao_flagged"]})
    weather, context = model_columns([*stored, FOLD_RAIN, *DROUGHT_COLS], stored=stored)
    pred = run_rolling_origin(
        rows, weather, context, ALPHA_GRID, fold_transform=make_fold_transform(stored, month_rain)
    )
    return label_predictions(pred["predictions"], region_of)


def records(pred: pd.DataFrame, sensitivity: str, detail: dict | None, experiment: str, stat: str = "skill") -> list:
    out = []
    for season in ev.ML_SEASONS:
        part = pred[pred["season"] == season]
        for col, model_id in MODELS.items():
            role = "reference" if col in REFERENCES else "secondary"
            labels = {"role": role, "sensitivity": sensitivity, "detail": detail, "source_ids": [experiment]}
            out.append(national_record(metric_row(part, col, seed=SEED, stat=stat), model_id, season, labels))
    return out


def rebuilt(weights: pd.DataFrame, shift: tuple[int, int] = (0, 0)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Training table and monthly cell rain rebuilt with other weights or windows (same labels and cells)."""
    table, skipped = build_feature_table(series, weights, cells, regions, shift=shift)
    print(" rows skipped:", len(skipped), dict(Counter(skipped["reason"])))  # reasons named, never dropped silently
    return table, build_cell_month_rain(series, weights, cells, regions, shift=shift)


table = pd.read_csv("data/processed/training_table.csv")
month_rain = pd.read_csv("data/processed/cell_month_rain.csv")
stats = pd.read_csv("data/processed/crop_stats.csv")
series, _removed = prepare_series(stats[~stats["is_preliminary"]])
series = series[series["yield_t_ha"].notna()]
weights = pd.read_csv("data/processed/cell_weights.csv")
cells, _unmatched = load_cells("data/raw/power", "data/raw/power_t2m", POWER_CACHE_FILES)
regions = {p: calendar_region(p, NSO_EXPORT) for p in sorted(set(series["province_nso"]))}

new = []
primary = pd.read_csv("data/processed/e012_predictions.csv")  # written by run_primary_test.py
new += records(primary, "mae_skill", None, "E-018", stat="mae_skill")
print("b done")
new += records(run(table, month_rain, STORED_FEATURES, drop_fao=True), "no_fao_flagged", None, "E-018")
print("a done")
risk = build_risk_level_features(series, weights, cells, regions)
with_risk = table.merge(risk, on=["province_nso", "season", "year"], how="left", validate="one_to_one")
stored_c = [c for c in STORED_FEATURES if c not in OFFICIAL_COUNT_COLS] + list(RISK_SHARE_COLS)
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
doc["generated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
METRICS.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
for r in new:
    if r["model_id"] == "m1_ridge":
        label = r["sensitivity"] + (f" {r['detail']['en']}" if r["detail"] else "")
        print(label, r["season"], {k: round(r[k]["value"], 3) for k in ("skill_vs_b0", "skill_vs_bnw")})
