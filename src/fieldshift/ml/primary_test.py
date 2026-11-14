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


# ---------- artifact records (05-DATA-CONTRACTS section 5b; UI-UX-SPEC section 11) ----------
EXPERIMENT = "E-012"
APP_SEASONS = {"spring": "spring", "autumn": "summer_autumn", "winter": "winter"}  # NSO name -> UI-UX SeasonCode
MODELS = {"b0": "b0", "b2": "b2", "bnw": "bnw", "m1": "m1_ridge"}  # prediction column -> ModelId


def app_season(nso_season: str) -> str:
    """The app's season code (UI-UX-SPEC section 11 SeasonCode) of an NSO rice season name."""
    if nso_season not in APP_SEASONS:
        raise ValueError(f"unknown NSO rice season {nso_season!r}; known: {sorted(APP_SEASONS)}")
    return APP_SEASONS[nso_season]


def bilingual(vi: str, en: str) -> dict:
    """A Text value {vi, en} (UI-UX-SPEC section 11)."""
    return {"vi": vi, "en": en}


def _num(x: float) -> tuple[str, str]:
    """(vi, en) of a number with 3 decimals; Vietnamese writes a decimal comma."""
    en = f"{x:.3f}"
    return en.replace(".", ","), en


def _role(col: str, season: str, scheme: str, subset: str) -> str:
    if col in REFERENCES:
        return "reference"
    primary = season == "spring" and scheme == "rolling_origin" and subset == "national"  # the one test, D-83
    return "primary" if primary else "secondary"


def metric_records(
    pred: pd.DataFrame, spatial_pred: pd.DataFrame, pilot: tuple[str, ...], seed: int, n_boot: int = ev.BOOTSTRAP_DRAWS
) -> list[dict]:
    """MetricRow records per ML season: rolling origin (national, the three-province subset, each pilot province,
    each NSO region) and the spatial holdout (national). Frames need season, province_nso and region columns."""
    out = []
    for season in ev.ML_SEASONS:
        sp, holdout = pred[pred["season"] == season], spatial_pred[spatial_pred["season"] == season]
        runs = [("rolling_origin", "national", sp), ("rolling_origin", "na_ht_th", sp[sp["province_nso"].isin(pilot)])]
        runs += [("rolling_origin", f"unit:{p}", sp[sp["province_nso"] == p]) for p in pilot]  # unit = province key
        runs += [
            ("rolling_origin", f"region:{r.lower().replace(' ', '_')}", sp[sp["region"] == r])
            for r in sorted(sp["region"].unique())
        ]
        runs.append(("spatial_holdout", "national", holdout))
        for scheme, subset, part in runs:
            for col, model_id in MODELS.items():
                out.append(
                    {
                        "model_id": model_id,
                        "season": app_season(season),
                        "role": _role(col, season, scheme, subset),
                        "scheme": scheme,
                        "sensitivity": None,
                        "detail": None,
                        "subset": subset,
                        **metric_row(part, col, seed=seed, n_boot=n_boot),
                        "source_ids": [EXPERIMENT],
                    }
                )
    return out


def find_row(rows: list[dict], season: str, subset: str, model_id: str = "m1_ridge") -> dict:
    """The rolling-origin metric record of a model, app season and subset."""
    for r in rows:
        key = (r["model_id"], r["season"], r["scheme"], r["subset"])
        if key == (model_id, season, "rolling_origin", subset):
            return r
    raise KeyError(f"no metric record for {model_id} {season} {subset}")


def gate_detail(gate: str, national: dict, pilot: dict) -> dict:
    """Detail text of G2, G3 or G4 (drafts for the copy review; form of G2 from 03-ML-SPEC section 8)."""
    if gate == "G2":
        (v0, e0), (vl0, el0), (vh0, eh0) = (
            _num(national["skill_vs_b0"][k]) for k in ("value", "ci90_low", "ci90_high")
        )
        (v1, e1), (vl1, el1), (vh1, eh1) = (
            _num(national["skill_vs_bnw"][k]) for k in ("value", "ci90_low", "ci90_high")
        )
        return bilingual(
            f"Mức hơn dự báo trung bình nhiều năm {v0} (khoảng tin cậy 90%: {vl0} đến {vh0}); "
            f"hơn mô hình không dùng thời tiết {v1} (khoảng tin cậy 90%: {vl1} đến {vh1}).",
            f"skill {e0} (90% CI {el0} to {eh0}) against the climatology reference; "
            f"skill {e1} (90% CI {el1} to {eh1}) against the no-weather model.",
        )
    if gate == "G3":
        (v, e), (vl, el), (vh, eh) = (_num(pilot["skill_vs_b2"][k]) for k in ("value", "ci90_low", "ci90_high"))
        return bilingual(
            f"Nghệ An, Hà Tĩnh, Thanh Hóa: mức hơn dự báo bằng năm trước {v} (khoảng tin cậy 90%: {vl} đến {vh}).",
            f"Nghe An, Ha Tinh, Thanh Hoa: skill {e} (90% CI {el} to {eh}) against persistence.",
        )
    cover = f"{100 * national['coverage_80']:.0f}"
    return bilingual(
        f"Khoảng dự báo 80% chứa {cover}% kết quả của các năm kiểm tra (cần 70% đến 90%).",
        f"The 80% range covered {cover}% of the held-out outcomes (needs 70% to 90%).",
    )


def g1_detail(g: dict) -> dict:
    need = G1_MIN_PROVINCES[g["season"]]
    return bilingual(
        f"{g['years']} năm và {g['provinces']} tỉnh có số liệu dùng được "
        f"(cần ít nhất {G1_MIN_YEARS} năm và {need} tỉnh).",
        f"{g['years']} usable years and {g['provinces']} provinces (needs at least {G1_MIN_YEARS} years and {need} "
        "provinces).",
    )


def penalty_report(at_edge: dict[str, float]) -> dict:
    """ReportItem: share of test years whose chosen penalty is an end of the grid (D-110)."""
    m1, bnw = (f"{100 * at_edge[k]:.0f}%" for k in ("m1", "bnw"))
    return {
        "id": EXPERIMENT,
        "title": bilingual("Mức phạt của mô hình ở đầu thang", "Model penalty at an end of the grid"),
        "text": bilingual(
            "Mức phạt được chọn nằm ở một đầu thang mức phạt của Meroni và cộng sự 2021 (đã đổi cho hồi quy ridge) "
            f"trong {m1} số năm kiểm tra với M1 và {bnw} với mô hình không dùng thời tiết; khi đó thang có thể đã giới hạn "
            "việc chọn mức phạt tốt nhất cho mô hình ấy.",
            f"The chosen penalty was at an end of the Meroni et al. 2021 penalty grid (rescaled for ridge) in {m1} of "
            f"the test years for M1 and in {bnw} for the no-weather model; there, the grid may have limited the choice "
            "of that model's best penalty.",
        ),
        "source_ids": [EXPERIMENT],
    }
