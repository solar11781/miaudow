"""Past-only normal yield and the percent anomaly target (docs/03-ML-SPEC.md §3; D-66, D-72).

Plain words: to know whether a year was good or bad for rice in a province, we compare its yield with a "normal"
yield computed only from earlier years of the same series (no peeking at the target year or later, which would leak
information). Two published candidates (D-72):
- `mean3`: mean of years t-3 to t-1 (Iizumi and Ramankutty 2016, "three-year RM yield (year t-3 to t-1)");
- `trend5`: straight line fitted to years t-5 to t-1 and extended to year t (Paudel et al. 2021, "linear trend from a
  5-year window").
A normal exists only when all the required previous years of the series have a yield (D-72). The target is the
percent anomaly anom = yield / normal - 1 (D-66): -0.10 means 10% below normal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WINDOWS = {"mean3": 3, "trend5": 5}


def _normal_at(prev_years: np.ndarray, prev_yields: np.ndarray, year: int, method: str) -> float:
    if method == "mean3":
        return float(prev_yields.mean())
    slope, intercept = np.polyfit(prev_years.astype(float), prev_yields, 1)
    return float(slope * year + intercept)


def past_normal(df: pd.DataFrame, method: str) -> pd.Series:
    """Normal yield per row (same index as df), computed per `series_id` from earlier rows only; NaN without one."""
    if method not in WINDOWS:
        raise ValueError(f"unknown normal method {method!r}; candidates are {sorted(WINDOWS)} (D-72)")
    if not df.index.is_unique:
        raise ValueError("past_normal needs a unique row index; reset it after concatenating series")
    dup = df.duplicated(["series_id", "year"], keep=False)
    if dup.any():
        bad = df.loc[dup, ["series_id", "year"]].drop_duplicates().to_dict("records")
        raise ValueError(f"more than one row per series and year, the target year would enter its own window: {bad}")
    k = WINDOWS[method]
    out = pd.Series(np.nan, index=df.index, dtype=float)
    for _, g in df.sort_values("year").groupby("series_id", sort=False):
        years = g["year"].to_numpy()
        yields = g["yield_t_ha"].astype(float).to_numpy()
        for i in range(k, len(g)):
            py, pv = years[i - k : i], yields[i - k : i]
            if np.isnan(pv).any() or years[i] - py[0] != k:  # every one of the k previous years must have a yield
                continue
            out.loc[g.index[i]] = _normal_at(py, pv, int(years[i]), method)
    return out


def add_anomaly(df: pd.DataFrame, method: str) -> pd.DataFrame:
    """Add `normal_t_ha` and `anom` (yield / normal - 1; NaN where there is no normal or no yield)."""
    out = df.copy()
    out["normal_t_ha"] = past_normal(df, method)
    if (out["normal_t_ha"] <= 0).any():
        bad = out.loc[out["normal_t_ha"] <= 0, ["series_id", "year"]].to_dict("records")
        raise ValueError(f"normal yield <= 0, percent anomaly undefined: {bad} (ask the team)")
    out["anom"] = out["yield_t_ha"] / out["normal_t_ha"] - 1
    return out
