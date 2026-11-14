"""Province-season weather features from NASA POWER (DECISION-LOG D-26, D-37, D-38, D-39).

Plain words: for each province we first build one daily weather series as the farmland-weighted average of its NASA
POWER cells (D-26). For each rice season and year we then summarise that series over the season window into a few
numbers (features), using standard climate-extreme definitions (ETCCDI) where they exist.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from fieldshift.features.hazards import drought_any2, drought_consecutive

DRY_DAY_MM = 1.0  # ETCCDI CDD: dry day = precipitation < 1 mm
RX5_DAYS = 5  # ETCCDI Rx5day: highest total over 5 consecutive days
HEAVY_RAIN_MM = 20.0  # ETCCDI R20mm: precipitation >= 20 mm
HOT_DAY_C = 35.0  # QĐ 18/2021 Art. 5.21 "vượt quá 35°c": strictly above 35 C (R-A01, D-96)
OFFICIAL_RAIN_MM = 50.0  # Art. 5.17: rain above 50 mm in 24 h
RET_HAI_C = 13.0  # Art. 5.18 "dưới 13oc": daily mean strictly below 13 C
RET_DAM_C = 15.0  # TT 25/2022/TT-BTNMT Art. 3.6: daily mean strictly below 15 C
DROUGHT_DEFICIT = 0.5  # Art. 48 rain part: monthly rain more than 50% below the normal


def province_daily_weather(cell_frames: dict, weights: dict) -> pd.DataFrame:
    """Farmland-weighted daily average of POWER cell frames (same columns and dates). Weights must sum to 1."""
    total = sum(weights.values())
    if not np.isclose(total, 1.0):
        raise ValueError(f"weights sum to {total}, expected 1")
    out = None
    for cell, w in weights.items():
        part = cell_frames[cell] * w
        out = part if out is None else out.add(part, fill_value=np.nan)
    return out


def _longest_run(mask: np.ndarray) -> int:
    best = run = 0
    for flag in mask:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def season_features(daily: pd.DataFrame, start: date, end: date) -> dict:
    """ETCCDI, heat, soil-water and radiation features over [start, end] on the farmland-weighted province series.

    Column names follow 05-DATA-CONTRACTS §4. Rain against a normal is not computed here: its normal comes from the
    training years of each fold (D-66). Raises ValueError if any day in the window is missing.
    """
    days = pd.date_range(start, end, freq="D")
    win = daily.reindex(days)
    if win[["PRECTOTCORR", "T2M_MAX", "T2M_MIN", "GWETROOT", "ALLSKY_SFC_SW_DWN"]].isna().any().any():
        raise ValueError(f"window {start}..{end} is not fully covered by daily data")
    rain = win["PRECTOTCORR"].to_numpy()
    rx5 = float(pd.Series(rain).rolling(RX5_DAYS).sum().max()) if len(rain) >= RX5_DAYS else float("nan")
    return {
        "precip_sum_mm": float(rain.sum()),
        "dry_spell_max_d": _longest_run(rain < DRY_DAY_MM),
        "heavy_rain_d": int((rain >= HEAVY_RAIN_MM).sum()),
        "rx5day_mm": rx5,
        "tmax_mean_c": float(win["T2M_MAX"].mean()),
        "tmin_mean_c": float(win["T2M_MIN"].mean()),
        "txx_c": float(win["T2M_MAX"].max()),
        "gwetroot_mean": float(win["GWETROOT"].mean()),
        "gwetroot_min": float(win["GWETROOT"].min()),
        "srad_mean_mj_m2_d": float(win["ALLSKY_SFC_SW_DWN"].mean()),
    }


def official_counts(cell_frames: dict, weights: dict, start: date, end: date) -> dict:
    """§4a counts incl. hot days (D-72): counted in each POWER cell over [start, end], then averaged with the farmland weights."""
    days = pd.date_range(start, end, freq="D")
    out = {"hot_days_d": 0.0, "official_heavy_rain_d": 0.0, "ret_hai_d": 0.0, "ret_dam_d": 0.0}
    for cell, w in weights.items():
        win = cell_frames[cell].reindex(days)
        if win[["PRECTOTCORR", "T2M_MAX", "T2M"]].isna().any().any():
            raise ValueError(f"cell {cell}: window {start}..{end} is not fully covered by daily data")
        out["hot_days_d"] += w * int((win["T2M_MAX"] > HOT_DAY_C).sum())
        out["official_heavy_rain_d"] += w * int((win["PRECTOTCORR"] > OFFICIAL_RAIN_MM).sum())
        out["ret_hai_d"] += w * int((win["T2M"] < RET_HAI_C).sum())
        out["ret_dam_d"] += w * int((win["T2M"] < RET_DAM_C).sum())
    return out


def drought_rain_counts(cell_monthly: dict, cell_normal: dict, weights: dict) -> dict:
    """Drought rain months per cell against the given monthly normal (training years, D-66), then weighted (D-72).

    cell_monthly / cell_normal: {cell: Series indexed by the season's months in order}. Returns the weighted number of
    drought months and the weighted shares meeting each reading (consecutive months; any 2 months; D-58).
    """
    out = {"drought_rain_months": 0.0, "drought_rain_consecutive": 0.0, "drought_rain_any2": 0.0}
    for cell, w in weights.items():
        rain, normal = cell_monthly[cell], cell_normal[cell].reindex(cell_monthly[cell].index)
        if rain.isna().any() or normal.isna().any():
            raise ValueError(f"cell {cell}: monthly rain or normal missing")
        flags = list(rain < (1 - DROUGHT_DEFICIT) * normal)
        out["drought_rain_months"] += w * sum(flags)
        out["drought_rain_consecutive"] += w * drought_consecutive(flags)
        out["drought_rain_any2"] += w * drought_any2(flags)
    return out
