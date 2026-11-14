"""Secondary models E-013 (M2 LightGBM) and E-017 (M3 random forest), rolling origin 2016-2024 (03-ML-SPEC 6-7).

Usage: PYTHONPATH=src python scripts/run_secondary_models.py   (after scripts/run_primary_test.py)
Same rows, columns, folds and inner tuning as M1 (E-012); scored against the E-012 references on the rows both have.
Adds their metric rows (role secondary) to artifacts/metrics.json and replaces earlier m2_lgbm and m3_rf rows.
"""

import json
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

import pandas as pd

from fieldshift.features.season_windows import nso_regions
from fieldshift.ml import evaluation as ev
from fieldshift.ml.fold_features import DROUGHT_COLS, FOLD_RAIN, make_fold_transform, model_columns
from fieldshift.ml.primary_test import STORED_FEATURES, metric_row, model_rows, national_record
from fieldshift.ml.runner import run_secondary

SEED = 0  # fixed seed for the trees and the year bootstrap (python rules)
MODELS = {  # model id -> (fit, grid, experiment id)
    "m2_lgbm": (ev.fit_lgbm, ev.M2_GRID, "E-013"),
    "m3_rf": (ev.fit_rf, ev.M3_GRID, "E-017"),
}
METRICS = Path("artifacts/metrics.json")

table = pd.read_csv("data/processed/training_table.csv")
rows = model_rows(table, nso_regions("data/raw/nso/E06.14.csv"))
month_rain = pd.read_csv("data/processed/cell_month_rain.csv")
weather, context = model_columns([*STORED_FEATURES, FOLD_RAIN, *DROUGHT_COLS], stored=STORED_FEATURES)
transform = make_fold_transform(STORED_FEATURES, month_rain)
references = pd.read_csv("data/processed/e012_predictions.csv")  # written by run_primary_test.py

doc = json.loads(METRICS.read_text(encoding="utf-8"))
doc["metrics"] = [r for r in doc["metrics"] if r["model_id"] not in MODELS]
for model_id, (fit, grid, experiment) in MODELS.items():
    pred = run_secondary(rows, weather, context, (partial(fit, seed=SEED), grid), fold_transform=transform)
    both = references.merge(pred[["series_id", "year", "pred"]], on=["series_id", "year"], how="inner")
    if len(both) != len(references):  # same rows as M1 (03-ML-SPEC section 6)
        raise ValueError(f"{model_id} covers {len(both)} of the {len(references)} E-012 rows")
    print(model_id, "rows:", len(pred), "| on the E-012 rows:", len(both))
    for season in ev.ML_SEASONS:
        part = both[both["season"] == season].rename(columns={"pred": model_id})
        row = metric_row(part, model_id, seed=SEED)
        doc["metrics"].append(national_record(row, model_id, season, {"role": "secondary", "source_ids": [experiment]}))
        print(" ", season, {k: round(v["value"], 3) for k, v in row.items() if k.startswith("skill_vs") and v})
doc["generated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
METRICS.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
