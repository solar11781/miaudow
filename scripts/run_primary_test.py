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
from fieldshift.ml.normal import CHOSEN_METHOD, add_anomaly
from fieldshift.ml.primary_test import G1_MIN_PROVINCES, G1_MIN_YEARS, g1_rows, metric_row, season_gates, weather_claim
from fieldshift.ml.runner import ALPHA_GRID, run_rolling_origin, run_spatial_holdout

FREEZE_COMMIT = "ea7a60c21d1867c4096fc3b3c4822b4127b53839"  # E-010: features and cleaning frozen before this run
SCHEMA_VERSION = "0.4"  # 05-DATA-CONTRACTS section 5 example
SEED = 0  # fixed seed of the year bootstrap (python rules: randomness only with a fixed seed)
EXPERIMENT = "E-012"
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


def _text(vi: str, en: str) -> dict:
    return {"vi": vi, "en": en}


def _ci(s: dict) -> tuple[str, str, str]:
    return f"{s['value']:.2f}", f"{s['ci90_low']:.2f}", f"{s['ci90_high']:.2f}"


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
ZERO_CELLS = len(pd.read_csv("data/processed/cell_weights_zero.csv"))  # zero-weight report (03-ML-SPEC 4)

weather, context = model_columns([*STORED, FOLD_RAIN, *DROUGHT_COLS], stored=STORED)
transform = make_fold_transform(STORED, month_rain)
run = run_rolling_origin(rows, weather, context, ALPHA_GRID, fold_transform=transform)
spatial = run_spatial_holdout(rows, weather, context, ALPHA_GRID, fold_transform=transform)


def _labelled(predictions: pd.DataFrame) -> pd.DataFrame:
    parts = predictions["series_id"].str.split("|", expand=True)
    return predictions.assign(province_nso=parts[0], season=parts[2], region=parts[0].map(region_of))


def _region_id(name: str) -> str:
    return name.lower().replace(" ", "_")


pred, spatial_pred = _labelled(run["predictions"]), _labelled(spatial["predictions"])

metrics, gates, claims = [], [], []
models = {"b0": "b0", "b2": "b2", "bnw": "bnw", "m1": "m1_ridge"}
for season in ev.ML_SEASONS:
    sp = pred[pred["season"] == season]
    subsets = {"national": sp, "na_ht_th": sp[sp["province_nso"].isin(PILOT)]}
    subsets |= {f"unit:{p}": sp[sp["province_nso"] == p] for p in PILOT}  # unit key = province until the crosswalk
    subsets |= {f"region:{_region_id(r)}": sp[sp["region"] == r] for r in sorted(sp["region"].unique())}
    scored = {}
    holdout = spatial_pred[spatial_pred["season"] == season]
    runs = [("rolling_origin", subset, part) for subset, part in subsets.items()] + [
        ("spatial_holdout", "national", holdout)
    ]
    for scheme, subset, part in runs:
        for col, model_id in models.items():
            row = metric_row(part, col, seed=SEED)
            scored[(scheme, subset, col)] = row
            role = "reference" if col in ("b0", "b2", "bnw") else ("primary" if season == "spring" else "secondary")
            metrics.append(
                {
                    "model_id": model_id,
                    "season": season,
                    "role": role,
                    "scheme": scheme,
                    "sensitivity": None,
                    "detail": None,
                    "subset": subset,
                    **row,
                    "source_ids": [EXPERIMENT],
                }
            )
    national, pilot = scored[("rolling_origin", "national", "m1")], scored[("rolling_origin", "na_ht_th", "m1")]
    verdict = season_gates(national, pilot)
    s0, s0lo, s0hi = _ci(national["skill_vs_b0"])
    s1, s1lo, s1hi = _ci(national["skill_vs_bnw"])
    s2, s2lo, s2hi = _ci(pilot["skill_vs_b2"])
    cover = f"{100 * national['coverage_80']:.0f}"
    details = {
        "G2": _text(
            f"Mức hơn dự báo trung bình nhiều năm {s0} (khoảng tin cậy 90%: {s0lo} đến {s0hi}); "
            f"hơn mô hình không dùng thời tiết {s1} (khoảng tin cậy 90%: {s1lo} đến {s1hi}).",
            f"skill {s0} (90% CI {s0lo} to {s0hi}) against the climatology reference; "
            f"skill {s1} (90% CI {s1lo} to {s1hi}) against the no-weather model.",
        ),
        "G3": _text(
            f"Nghệ An, Hà Tĩnh, Thanh Hóa: mức hơn dự báo bằng năm trước {s2} (khoảng tin cậy 90%: {s2lo} đến {s2hi}).",
            f"Nghe An, Ha Tinh, Thanh Hoa: skill {s2} (90% CI {s2lo} to {s2hi}) against persistence.",
        ),
        "G4": _text(
            f"Khoảng 80% chứa {cover}% kết quả của các năm kiểm tra (cần 70% đến 90%).",
            f"The 80% range covered {cover}% of the held-out outcomes (needs 70% to 90%).",
        ),
    }
    for gate in ("G2", "G3", "G4"):
        gates.append(
            {
                "gate": gate,
                "season": season,
                "model_id": "m1_ridge",
                "passed": verdict[gate],
                "detail": details[gate],
                "source_ids": [EXPERIMENT],
            }
        )
    claims.append(
        {"season": season, "model_id": "m1_ridge", "made": weather_claim(national), "source_ids": [EXPERIMENT]}
    )

for g in g1_rows(rice):
    need = G1_MIN_PROVINCES[g["season"]]
    gates.append(
        {
            "gate": "G1",
            "season": g["season"],
            "model_id": None,
            "passed": g["passed"],
            "detail": _text(
                f"{g['years']} năm và {g['provinces']} tỉnh có số liệu dùng được "
                f"(cần ít nhất {G1_MIN_YEARS} năm và {need} tỉnh).",
                f"{g['years']} usable years and {g['provinces']} provinces "
                f"(needs at least {G1_MIN_YEARS} years and {need} provinces).",
            ),
            "source_ids": [EXPERIMENT],
        }
    )

now = datetime.now(UTC).isoformat(timespec="seconds")
head = {"schema_version": SCHEMA_VERSION, "generated_at": now, "freeze_commit": FREEZE_COMMIT}
OUT.mkdir(exist_ok=True)
metrics_doc = {
    **head,
    "test_years": {"first": min(ev.TEST_YEARS), "last": max(ev.TEST_YEARS)},
    "metrics": metrics,
    "weather_claims": claims,
    "reports": [
        {
            "id": "E-010",
            "title": _text("Cách tính năng suất bình thường", "How the normal yield is computed"),
            "text": _text(
                "Trung bình 3 năm trước được chọn, vì sai số nhỏ hơn đường xu hướng 5 năm trên các năm 2011-2015 "
                "(0,0989 so với 0,0997). Riêng vụ xuân, đường xu hướng sai số nhỏ hơn; vụ mùa thì ngược lại.",
                "The mean of the 3 previous years was chosen: its error was smaller than the 5-year trend's on "
                "2011-2015 (0.0989 against 0.0997). For spring rice alone the trend was better; "
                "for winter rice, the mean.",
            ),
            "source_ids": ["E-010"],
        },
        {
            "id": EXPERIMENT,
            "title": _text("Ô thời tiết không có đất trồng", "Weather cells without farmland"),
            "text": _text(
                f"{ZERO_CELLS} ô thời tiết NASA POWER có trọng số đất trồng bằng 0 nên không được dùng.",
                f"{ZERO_CELLS} NASA POWER weather cells have a farmland weight of zero and are not used.",
            ),
            "source_ids": [EXPERIMENT],
        },
    ],
}
(OUT / "metrics.json").write_text(json.dumps(metrics_doc, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / "gates.json").write_text(json.dumps({**head, "gates": gates}, ensure_ascii=False, indent=1), encoding="utf-8")
print("rows scored:", run["metrics"]["n_rows"], "| test years:", run["metrics"]["n_test_years"])
print("spatial holdout rows:", spatial["metrics"]["n_rows"], "| alpha at a grid end:", run["metrics"]["alpha_at_edge"])
for g in gates:
    print(g["gate"], g["season"], g["passed"], "|", g["detail"]["en"])
for c in claims:
    print("weather claim", c["season"], c["made"])
