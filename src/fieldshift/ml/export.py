"""The app artifact artifacts/risk_table.json (05-DATA-CONTRACTS section 5; 03-ML-SPEC section 10).

Plain words: for every province, rice season and past year, the real anomaly against its normal (always shown) and,
only for the test years of a season whose own test passed, the model's out-of-sample prediction with its 80% range
(the range only where the coverage gate G4 passed). The app never runs the model; it reads this file.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pandas as pd

from fieldshift.ml.evaluation import TEST_YEARS
from fieldshift.ml.primary_test import APP_SEASONS, EXPERIMENT, app_season

SCHEMA_VERSION = "0.4"  # 05-DATA-CONTRACTS section 5
MODEL_ID = "m1_ridge"  # the cards use M1 for every season (03-ML-SPEC section 10, D-102)
HISTORY_SOURCES = ["R-D01", "E-010"]  # NSO PX-Web E06 tables; the normal method
KEY = ["province_nso", "season", "year"]


def _status(gates: list[dict]) -> dict[str, dict]:
    """Per app season: model_status and whether the interval may be shown (03-ML-SPEC section 8, D-94)."""
    verdict = {(g["gate"], g["season"]): g["passed"] for g in gates}
    out = {}
    for season in APP_SEASONS.values():
        if not verdict.get(("G1", season)):
            out[season] = {"model_status": "not_modeled", "model_id": None, "interval": False}
            continue
        shown = bool(verdict.get(("G2", season)) and verdict.get(("G3", season)))
        out[season] = {
            "model_status": "shown" if shown else "not_shown",
            "model_id": MODEL_ID,
            "interval": shown and bool(verdict.get(("G4", season))),
        }
    return out


def _num(x: float) -> float | None:
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else float(x)


def risk_table(
    history: pd.DataFrame, predictions: pd.DataFrame, gates: list[dict], freeze_commit: str, data_versions: dict
) -> dict:
    """history: province_nso, season (NSO name), year, anom; predictions: the same key with m1, lo80, hi80 (E-012)."""
    status = _status(gates)
    pred = predictions.set_index(KEY)
    rows = []
    for rec in history.sort_values(KEY).itertuples(index=False):
        season = app_season(rec.season)
        key = (rec.province_nso, rec.season, rec.year)
        shown = status[season]["model_status"] == "shown" and rec.year in TEST_YEARS and key in pred.index
        p = pred.loc[key] if shown else None
        interval = shown and status[season]["interval"]
        rows.append(
            {
                "unit_id": rec.province_nso,  # NSO name until the unit_id crosswalk exists (05 section 2)
                "crop": "rice",
                "season": season,
                "year": int(rec.year),
                "anom_history": _num(rec.anom),
                "anom_history_source_ids": HISTORY_SOURCES,
                "anom_oos": float(p["m1"]) if shown else None,
                "oos_low_80": float(p["lo80"]) if interval else None,
                "oos_high_80": float(p["hi80"]) if interval else None,
                "model_id": MODEL_ID if shown else None,
                "anom_oos_source_ids": [EXPERIMENT] if shown else [],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "freeze_commit": freeze_commit,
        "data_versions": data_versions,
        "seasons": [
            {"season": s, "model_status": v["model_status"], "model_id": v["model_id"]} for s, v in status.items()
        ],
        "rows": rows,
    }
