"""Primary test E-012: references B0, B2, BNW and M1 ridge, rolling origin 2016-2024 (03-ML-SPEC sections 6-8).

Usage: PYTHONPATH=src python scripts/run_primary_test.py
Reads data/processed/training_table.csv and cell_month_rain.csv; writes artifacts/metrics.json and artifacts/gates.json
(05-DATA-CONTRACTS section 5b). Runs after the freeze commit only (D-83). Gate and report texts are drafts for the copy
review (vi and en).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from fieldshift.features.season_windows import nso_regions
from fieldshift.ml import evaluation as ev
from fieldshift.ml.fold_features import DROUGHT_COLS, FOLD_RAIN, make_fold_transform, model_columns
from fieldshift.ml.normal import CHOSEN_METHOD, add_anomaly, compare_normal_methods
from fieldshift.ml.primary_test import (
    EXPERIMENT,
    app_season,
    bilingual,
    find_row,
    g1_detail,
    g1_rows,
    gate_detail,
    metric_records,
    penalty_report,
    season_gates,
    weather_claim,
)
from fieldshift.ml.runner import ALPHA_GRID, run_rolling_origin, run_spatial_holdout

FREEZE_COMMIT = "ea7a60c21d1867c4096fc3b3c4822b4127b53839"  # E-010: features and cleaning frozen before this run
SCHEMA_VERSION = "0.4"  # 05-DATA-CONTRACTS section 5 example
SEED = 0  # fixed seed of the year bootstrap (python rules: randomness only with a fixed seed)
PILOT = ("Nghe An", "Ha Tinh", "Thanh Hoa")  # G3 subset and the per-province pilot report (D-48)
STORED = [  # 03-ML-SPEC section 4 feature list, as stored in the training table (05-DATA-CONTRACTS section 4)
    "precip_sum_mm",
    "dry_spell_max_d",
    "heavy_rain_d",
    "rx5day_mm",
    "tmax_mean_c",
    "tmin_mean_c",
    "txx_c",
    "hot_days_d",
    "official_heavy_rain_d",
    "ret_hai_d",
    "ret_dam_d",
    "gwetroot_mean",
    "gwetroot_min",
    "srad_mean_mj_m2_d",
]
OUT = Path("artifacts")
NSO_EXPORT = "data/raw/nso/E06.14.csv"  # region rows of the NSO export: the six spatial blocks (03-ML-SPEC 7.2)


table = pd.read_csv("data/processed/training_table.csv")
rice = add_anomaly(table[table["crop"] == "rice"].reset_index(drop=True), CHOSEN_METHOD)
rice = rice[rice["anom"].notna()]
rows = rice[rice["season"].isin(ev.ML_SEASONS)].reset_index(drop=True)
region_of = nso_regions(NSO_EXPORT)
rows["region"] = rows["province_nso"].map(region_of)
if rows["region"].isna().any():
    raise ValueError(
        f"provinces without an NSO region: {sorted(rows.loc[rows['region'].isna(), 'province_nso'].unique())}"
    )
month_rain = pd.read_csv("data/processed/cell_month_rain.csv")
zero = pd.read_csv("data/processed/cell_weights_zero.csv")  # zero-weight report (03-ML-SPEC section 4)
ZERO_CELLS, ZERO_PAIRS = len(zero[["lat", "lon"]].drop_duplicates()), len(zero)

weather, context = model_columns([*STORED, FOLD_RAIN, *DROUGHT_COLS], stored=STORED)
transform = make_fold_transform(STORED, month_rain)
run = run_rolling_origin(rows, weather, context, ALPHA_GRID, fold_transform=transform)
spatial = run_spatial_holdout(rows, weather, context, ALPHA_GRID, fold_transform=transform)


def _labelled(predictions: pd.DataFrame) -> pd.DataFrame:
    parts = predictions["series_id"].str.split("|", expand=True)
    return predictions.assign(province_nso=parts[0], season=parts[2], region=parts[0].map(region_of))


pred, spatial_pred = _labelled(run["predictions"]), _labelled(spatial["predictions"])

metrics = metric_records(pred, spatial_pred, pilot=PILOT, seed=SEED)
gates, claims = [], []
for season in ev.ML_SEASONS:
    code = app_season(season)
    national, pilot = find_row(metrics, code, "national"), find_row(metrics, code, "na_ht_th")
    verdict = season_gates(national, pilot)
    gates += [
        {
            "gate": gate,
            "season": code,
            "model_id": "m1_ridge",
            "passed": verdict[gate],
            "detail": gate_detail(gate, national, pilot),
            "source_ids": [EXPERIMENT],
        }
        for gate in ("G2", "G3", "G4")
    ]
    claims.append({"season": code, "model_id": "m1_ridge", "made": weather_claim(national), "source_ids": [EXPERIMENT]})
gates += [
    {
        "gate": "G1",
        "season": app_season(g["season"]),
        "model_id": None,
        "passed": g["passed"],
        "detail": g1_detail(g),
        "source_ids": [EXPERIMENT],
    }
    for g in g1_rows(rice)
]
choice = compare_normal_methods(table[table["season"].isin(ev.ML_SEASONS)].reset_index(drop=True), min(ev.TEST_YEARS))
m3e, t5e = (f"{choice['mse'][m]:.4f}" for m in ("mean3", "trend5"))
m3v, t5v = m3e.replace(".", ","), t5e.replace(".", ",")  # Vietnamese decimal comma
reports = [
    {
        "id": "E-010",
        "title": bilingual("Cách tính năng suất bình thường", "How the normal yield is computed"),
        "text": bilingual(
            f"Trung bình 3 năm trước được chọn, vì sai số nhỏ hơn đường xu hướng 5 năm trên các năm 2011-2015 "
            f"({m3v} so với {t5v}). Riêng vụ xuân, đường xu hướng sai số nhỏ hơn; vụ mùa thì ngược lại.",
            f"The mean of the 3 previous years was chosen: its error was smaller than the 5-year trend's on "
            f"2011-2015 ({m3e} against {t5e}). For spring rice alone the trend was better; for winter rice, the mean.",
        ),
        "source_ids": ["E-010"],
    },
    {
        "id": EXPERIMENT,
        "title": bilingual("Ô thời tiết không có đất trồng", "Weather cells without farmland"),
        "text": bilingual(
            f"{ZERO_CELLS} ô thời tiết NASA POWER ({ZERO_PAIRS} cặp tỉnh và ô) có trọng số đất trồng bằng 0 nên không "
            "được dùng.",
            f"{ZERO_CELLS} NASA POWER weather cells ({ZERO_PAIRS} province and cell pairs) have a farmland weight of "
            "zero and are not used.",
        ),
        "source_ids": [EXPERIMENT],
    },
    penalty_report(run["metrics"]["alpha_at_edge"]),
]

now = datetime.now(UTC).isoformat(timespec="seconds")
head = {"schema_version": SCHEMA_VERSION, "generated_at": now, "freeze_commit": FREEZE_COMMIT}
OUT.mkdir(exist_ok=True)
metrics_doc = {
    **head,
    "test_years": {"first": min(ev.TEST_YEARS), "last": max(ev.TEST_YEARS)},
    "metrics": metrics,
    "weather_claims": claims,
    "reports": reports,
}
for name, doc in (("metrics.json", metrics_doc), ("gates.json", {**head, "gates": gates})):
    (OUT / name).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("rows scored:", run["metrics"]["n_rows"], "| test years:", run["metrics"]["n_test_years"])
print("spatial holdout rows:", spatial["metrics"]["n_rows"], "| alpha at a grid end:", run["metrics"]["alpha_at_edge"])
for g in gates:
    print(g["gate"], g["season"], g["passed"], "|", g["detail"]["en"])
for c in claims:
    print("weather claim", c["season"], c["made"])
