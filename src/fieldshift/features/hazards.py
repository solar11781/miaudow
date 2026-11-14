"""Displayed official risk-level rules per NASA POWER cell (docs/03-ML-SPEC.md §5a; D-79, D-96, D-97, D-104, D-120).

Plain words: Vietnam's disaster decree QĐ 18/2021/QĐ-TTg (R-A01) says when heavy rain, heat, damaging cold and the rain
part of drought reach risk level 1. We apply those thresholds to each NASA POWER weather cell over the days (or, for
drought, months) when a crop of the P-02 trial was in the field, then report the share of the province's farmland
where a rule was met. This is a mechanical reading of the tables, not an official record (R-K03).
"""

from __future__ import annotations

import itertools
from datetime import date

import numpy as np
import pandas as pd

HEAVY_RAIN_MM = 100.0  # Art. 44.1 "từ 100 mm ... trong 24 giờ" (daily totals; the 12-hour branch is not computable)
HEAT_C, HEAT_DAYS = 35.0, 3  # Art. 47.1 a "từ 35°c đến 37°c, kéo dài từ 3 ngày trở lên" (D-96, D-104)
HEAT_TOP_A = 37.0  # Art. 47.1 a "từ 35°c đến 37°c" (both ends included)
HEAT_BANDS_BCD = (
    (37.0, 39.0),
    (39.0, 41.0),
    (41.0, np.inf),
)  # 47.1 b-d "từ trên 37 ... đến 39", "trên 39 ... 41", "trên 41"
COLD_C, COLD_DAYS = 13.0, 6  # Art. 53.1 a "từ trên 8°c đến 13°c, kéo dài từ trên 5 ngày" (plains wording, D-96)
SEVERE_COLD_C, SEVERE_COLD_DAYS = 8.0, 3  # Art. 53.1 d "từ 8°c trở xuống, kéo dài từ 3 ngày"
DROUGHT_DEFICIT = 0.5  # Art. 48.1 "thiếu hụt tổng lượng mưa tháng trên 50%"
DROUGHT_MONTHS = 2  # D-58 second reading: any 2 drought months in the season
CLIM_YEARS = (1991, 2020)  # "trung bình nhiều năm": NCHMF rainfall TBNN period 1991-2020 (R-K15, D-118; WMO R-A15)
RULES = ("heavy_rain", "heat", "drought_rain_consecutive", "drought_rain_any2", "cold")


def _longest_run(mask) -> int:
    best = run = 0
    for flag in np.asarray(mask, dtype=bool):
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def heavy_rain(rain: pd.Series) -> bool:
    return bool((rain >= HEAVY_RAIN_MM).any())


def heat(tmax: pd.Series) -> bool:
    """Word for word (D-146, as D-120 for cold): >= 3 consecutive days with the daily maximum inside one band of Art.
    47.1: [35.0, 37.0], (37.0, 39.0], (39.0, 41.0] or above 41.0 C. A run that crosses bands is not one "đợt" of
    either band; a qualifying run inside one band counts, also inside a longer hot spell."""
    bands = [(tmax >= HEAT_C) & (tmax <= HEAT_TOP_A)] + [(tmax > lo) & (tmax <= hi) for lo, hi in HEAT_BANDS_BCD]
    return any(_longest_run(b) >= HEAT_DAYS for b in bands)


def cold(tmean: pd.Series) -> bool:
    """Word for word (D-120, D-146): >= 6 consecutive days with daily mean above 8.0 C and at or below 13.0 C (Art. 53.1
    a), or >= 3 consecutive days at or below 8.0 C (Art. 53.1 d). A spell counts only as a run inside one band; a run
    that crosses bands is not one "đợt" of either band; a qualifying run inside one band counts, also inside a longer
    cold spell that touches the other band."""
    band_a = (tmean > SEVERE_COLD_C) & (tmean <= COLD_C)
    return _longest_run(band_a) >= COLD_DAYS or _longest_run(tmean <= SEVERE_COLD_C) >= SEVERE_COLD_DAYS


def monthly_climatology(rain: pd.Series) -> pd.Series:
    """Mean monthly rain total per calendar month (1..12) over 1991-2020; every day of 1991-2020 must be present."""
    need = pd.date_range(f"{CLIM_YEARS[0]}-01-01", f"{CLIM_YEARS[1]}-12-31", freq="D")
    if rain.reindex(need).isna().any():
        raise ValueError("daily rain incomplete in 1991-2020: no climatology (no guessing)")
    monthly = rain.reindex(need).resample("MS").sum()
    m = monthly[(monthly.index.year >= CLIM_YEARS[0]) & (monthly.index.year <= CLIM_YEARS[1])]
    return m.groupby(m.index.month).mean()


def drought_months(month_rain: pd.Series, clim: pd.Series) -> pd.Series:
    """True where the month's rain is more than 50% below the climatological mean (deficit strictly above 50%)."""
    return (month_rain < (1 - DROUGHT_DEFICIT) * clim.reindex(month_rain.index)).astype(bool)


def drought_consecutive(flags) -> bool:
    """Two drought months in a row. A dict {month: flag} uses calendar adjacency (5 and 8 are not in a row); a list
    is taken as consecutive months in order."""
    if isinstance(flags, dict):
        return any(flags[m] and flags.get(m + 1, False) for m in flags)
    f = list(flags)
    return any(a and b for a, b in itertools.pairwise(f))


def drought_any2(flags) -> bool:
    return sum(bool(x) for x in flags) >= DROUGHT_MONTHS


def _field_days(year: int, field_dates) -> pd.DatetimeIndex:
    days = set()
    for start, end in field_dates:
        a = date(year, int(start[:2]), int(start[3:]))
        b = date(year, int(end[:2]), int(end[3:]))
        if b < a:
            raise ValueError(f"field dates {start}..{end} cross 31 December (no P-02 window does, 03-ML-SPEC §5a)")
        days.update(pd.date_range(a, b, freq="D"))
    return pd.DatetimeIndex(sorted(days))


def _runs_rule(series: pd.Series, days: pd.DatetimeIndex, rule) -> bool:
    """Apply a spell rule within each block of consecutive field days (a spell never jumps a gap between crops)."""
    s = series.reindex(days)
    block = (days.to_series().diff() != pd.Timedelta(days=1)).cumsum()
    return any(rule(g) for _, g in s.groupby(block.to_numpy()))


def cell_rules(daily: pd.DataFrame, year: int, field_dates, months, clim: pd.Series) -> dict:
    """Rule results for one cell and year. daily: PRECTOTCORR, T2M_MAX, T2M by date. Raises if field data are missing."""
    days = _field_days(year, field_dates)
    win = daily.reindex(days)[["PRECTOTCORR", "T2M_MAX", "T2M"]]
    if win.isna().any().any():
        raise ValueError(f"weather missing inside the field time of {year}")
    totals = {}
    for m in sorted(months):
        mdays = pd.date_range(pd.Timestamp(year, m, 1), pd.Timestamp(year, m, 1) + pd.offsets.MonthEnd(0), freq="D")
        vals = daily["PRECTOTCORR"].reindex(mdays)
        if vals.isna().any():
            raise ValueError(f"rain missing in {year}-{m:02d}: no monthly total (no guessing)")
        totals[m] = float(vals.sum())
    flags = drought_months(pd.Series(totals), clim).to_dict()
    return {
        "heavy_rain": heavy_rain(win["PRECTOTCORR"]),
        "heat": _runs_rule(daily["T2M_MAX"], days, heat),
        "cold": _runs_rule(daily["T2M"], days, cold),
        "drought_rain_consecutive": drought_consecutive(flags),
        "drought_rain_any2": drought_any2(flags.values()),
    }


def farmland_share(met: dict, weights: dict) -> float:
    """Sum of farmland weights of the cells where the rule was met; every weighted cell must have a result."""
    missing = [c for c in weights if c not in met]
    if missing:
        raise KeyError(f"no rule result for weighted cells {missing}")
    return float(sum(w for c, w in weights.items() if met[c]))
