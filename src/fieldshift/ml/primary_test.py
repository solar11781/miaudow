"""Metrics, gates G1-G4 and the weather claim of the primary test (03-ML-SPEC sections 6-8; 05-DATA-CONTRACTS 5b).

Plain words: every model and reference is scored on the same held-out rows; "skill" is how much smaller a model's
squared error is than a reference's (1 = perfect, 0 = no better), with a 90% range from resampling whole years. The
gates then decide, per rice season, whether the model's predictions may appear in the app at all.
"""

from __future__ import annotations

import pandas as pd

from fieldshift.ml import evaluation as ev

REFERENCES = ("b0", "b2", "bnw")
G1_MIN_YEARS = 20  # D-71
G1_MIN_PROVINCES = {"spring": 40, "winter": 40, "autumn": 25}  # D-71; summer-autumn rice: 25 provinces
G4_COVERAGE = (0.70, 0.90)  # G4: the 80% interval covers 70-90% of held-out outcomes (team choice, D-48)


def _skill(pred: pd.DataFrame, model: str, ref: str, seed: int, n_boot: int) -> dict:
    value = ev.skill_score(pred["y"], pred[model], pred[ref])
    frame = pd.DataFrame({"year": pred["year"], "y": pred["y"], "pred": pred[model], "base": pred[ref]})
    low, high = ev.year_bootstrap_ci(frame, "skill", n_boot=n_boot, seed=seed)
    return {"value": value, "ci90_low": low, "ci90_high": high}


def metric_row(pred: pd.DataFrame, model: str, seed: int, n_boot: int = ev.BOOTSTRAP_DRAWS) -> dict:
    """Errors, out-of-sample R2, skill against each reference with its year-bootstrap 90% CI, and interval coverage.

    pred: one row per scored test row with year, y and the predictions of every model and reference (same rows).
    """
    with_interval = model == "m1"
    return {
        "rmse": ev.rmse(pred["y"], pred[model]),
        "mae": ev.mae(pred["y"], pred[model]),
        "r2_oos": ev.r2_oos(pred["y"], pred[model]),
        **{f"skill_vs_{ref}": None if ref == model else _skill(pred, model, ref, seed, n_boot) for ref in REFERENCES},
        "coverage_80": ev.coverage(pred["y"], pred["lo80"], pred["hi80"]) if with_interval else None,
        "n_rows": len(pred),
        "n_test_years": int(pred["year"].nunique()),
    }


def _beats(skill: dict | None) -> bool:
    """Skill above 0 with a 90% CI that excludes 0 (G2)."""
    return skill is not None and skill["value"] > 0 and skill["ci90_low"] > 0


def season_gates(m1_national: dict, m1_pilot: dict) -> dict[str, bool]:
    """G2, G3 and G4 of one season from M1's national and three-province metric rows (03-ML-SPEC section 8)."""
    lo, hi = G4_COVERAGE
    return {
        "G2": _beats(m1_national["skill_vs_b0"]) and _beats(m1_national["skill_vs_bnw"]),
        "G3": m1_pilot["skill_vs_b2"]["ci90_high"] >= 0,
        "G4": lo <= m1_national["coverage_80"] <= hi,
    }


def weather_claim(m1_national: dict) -> bool:
    """The claim "NASA weather improves the prediction": only if M1 beats the no-weather model BNW (D-93, D-99)."""
    return _beats(m1_national["skill_vs_bnw"])


def g1_rows(model_rows: pd.DataFrame) -> list[dict]:
    """G1 per season: usable years and provinces among the rows with an anomaly, after cleaning (D-71)."""
    out = []
    for season, g in model_rows.groupby("season"):
        years, provinces = g["year"].nunique(), g["province_nso"].nunique()
        passed = years >= G1_MIN_YEARS and provinces >= G1_MIN_PROVINCES[season]
        out.append({"season": season, "years": int(years), "provinces": int(provinces), "passed": bool(passed)})
    return out
