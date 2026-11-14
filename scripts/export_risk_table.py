"""Write artifacts/risk_table.json from the cleaned history, the E-012 predictions and the gates (05 section 5).

Usage: PYTHONPATH=src python scripts/export_risk_table.py   (after scripts/run_primary_test.py)
"""

import hashlib
import json
from pathlib import Path

import pandas as pd

from fieldshift.data.series import prepare_series
from fieldshift.ml.export import risk_table
from fieldshift.ml.normal import CHOSEN_METHOD, add_anomaly

FREEZE_COMMIT = "ea7a60c21d1867c4096fc3b3c4822b4127b53839"  # E-010
RICE_SEASONS = ("spring", "autumn", "winter")  # NSO rice seasons of the history (05-DATA-CONTRACTS section 2)


def _sha(path: str) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


stats = pd.read_csv("data/processed/crop_stats.csv")
series, _removed = prepare_series(stats[~stats["is_preliminary"]])
rice = series[(series["crop"] == "rice") & series["season"].isin(RICE_SEASONS) & series["yield_t_ha"].notna()]
history = add_anomaly(rice.reset_index(drop=True), CHOSEN_METHOD)
pred = pd.read_csv("data/processed/e012_predictions.csv")
gates = json.loads(Path("artifacts/gates.json").read_text(encoding="utf-8"))["gates"]
table = risk_table(
    history,
    pred,
    gates,
    freeze_commit=FREEZE_COMMIT,
    data_versions={
        "crop_stats": _sha("data/processed/crop_stats.csv"),
        "climate": _sha("data/processed/training_table.csv"),
    },
)
Path("artifacts/risk_table.json").write_text(
    json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
)
print("rows:", len(table["rows"]), "| seasons:", table["seasons"])
print("rows with a prediction:", sum(r["anom_oos"] is not None for r in table["rows"]))
