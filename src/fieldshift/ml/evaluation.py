"""Validation harness (docs/03-ML-SPEC.md §6-§8; D-68, D-69, D-83, D-107).

Plain words: we only ever test a model on years it has not seen, training on the past (rolling origin); for the
spatial check we also hide a whole region. Inside each training window, the last 30% of years are "inner" test years
used for tuning, the error range and the normal-method choice. Uncertainty is estimated by resampling whole years,
because all provinces in the same year share weather and are not independent samples.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TEST_YEARS = range(2016, 2025)  # D-69
INNER_SHARE = 0.3  # D-107: same 70/30 rule as the outer split
MIN_RESAMPLED_YEARS = 2  # the t quantile below needs n - 1 >= 1 degrees of freedom


# ---------- splits ----------
def rolling_origin_splits(years, test_years=TEST_YEARS):
    years = np.asarray(years)
    return [(np.flatnonzero(years < t), np.flatnonzero(years == t)) for t in test_years]


def region_holdout_splits(years, regions, test_years=TEST_YEARS):
    years, regions = np.asarray(years), np.asarray(regions)
    splits = []
    for t in test_years:
        for r in sorted(set(regions[years == t])):
            splits.append((np.flatnonzero((years < t) & (regions != r)), np.flatnonzero((years == t) & (regions == r))))
    return splits


def inner_test_years(train_years) -> list[int]:
    """The last 30% of the distinct training years (nearest whole year, half up; at least 1), D-107."""
    ys = sorted({int(y) for y in train_years})
    n = max(1, math.floor(INNER_SHARE * len(ys) + 0.5))
    return ys[-n:]


def inner_splits(train_years):
    """Inner folds inside one training window: each inner test year predicted from all earlier years (Paudel 2022)."""
    years = np.asarray(train_years)
    return [(np.flatnonzero(years < u), np.flatnonzero(years == u)) for u in inner_test_years(years)]


# ---------- references ----------
def predict_b0(df: pd.DataFrame, train_idx, test_idx) -> pd.Series:
    """B0: each series' own mean anomaly over its training rows (climatology reference, refit per fold; D-83, D-113).

    Per series, not pooled: pooling non-homogeneous samples "can lead to overestimates of forecast skill" (WMO/WWRP
    JWGFVR verification guide). NaN for a series without training rows (removed by same_rows).
    """
    means = df.loc[train_idx].groupby("series_id")["anom"].mean()
    return pd.Series(df.loc[test_idx, "series_id"].map(means).to_numpy(dtype=float), index=test_idx)


def predict_b0_holdout(df: pd.DataFrame, test_idx) -> pd.Series:
    """Spatial-holdout B0 (D-146): each held-out series' own mean anomaly over its years before the test row's year.

    A held-out region has no training rows, so the per-series training mean is undefined; like B2, the reference uses
    the same series' own past only. NaN for a series without an earlier year (removed by same_rows).
    """
    out = []
    for i in test_idx:
        sid, year = df.at[i, "series_id"], df.at[i, "year"]
        past = df.loc[(df["series_id"] == sid) & (df["year"] < year), "anom"]
        out.append(past.mean() if len(past) else np.nan)
    return pd.Series(out, index=test_idx, dtype=float)


def predict_b2(df: pd.DataFrame, test_idx) -> pd.Series:
    """B2: the same series' anomaly in the previous year (persistence reference); NaN where it does not exist."""
    prev = df.set_index(["series_id", "year"])["anom"]
    keys = list(zip(df.loc[test_idx, "series_id"], df.loc[test_idx, "year"] - 1, strict=True))
    return pd.Series([prev.get(k, np.nan) for k in keys], index=test_idx, dtype=float)


def same_rows(preds: dict) -> pd.Series:
    """True for rows that every model and reference can predict (plan review A3)."""
    frame = pd.DataFrame(preds)
    return frame.notna().all(axis=1)


# ---------- metrics ----------
def rmse(y, p):
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def mae(y, p):
    return float(np.mean(np.abs(np.asarray(y) - np.asarray(p))))


def skill_score(y, p, base):
    """1 - MSE(model) / MSE(reference): 1 = perfect, 0 = no better than the reference, < 0 = worse."""
    y, p, base = map(np.asarray, (y, p, base))
    return float(1 - np.mean((y - p) ** 2) / np.mean((y - base) ** 2))


def mae_skill(y, p, base):
    """1 - MAE(model) / MAE(reference) (pre-registered sensitivity (b), D-83)."""
    y, p, base = map(np.asarray, (y, p, base))
    return float(1 - np.mean(np.abs(y - p)) / np.mean(np.abs(y - base)))


def r2_oos(y, p):
    """R2 on held-out rows: 1 - sum (y - p)^2 / sum (y - mean(y))^2 (Paudel et al. 2021, thesis eq. A.4; D-114)."""
    y, p = np.asarray(y), np.asarray(p)
    return float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2))


# ---------- year bootstrap (Hesterberg 2015) ----------
def expanded_alpha_half(n_units: int, level: float) -> float:
    """alpha'/2 = Phi(-sqrt(n/(n-1)) t_{alpha/2, n-1}) for the expanded percentile interval (Hesterberg 2015)."""

    if n_units < MIN_RESAMPLED_YEARS:
        raise ValueError("the expanded percentile interval needs at least 2 resampled years")
    alpha = 1 - level
    t = stats.t.ppf(1 - alpha / 2, n_units - 1)
    return float(stats.norm.cdf(-math.sqrt(n_units / (n_units - 1)) * t))


def _year_sums(df: pd.DataFrame) -> pd.DataFrame:
    e_m, e_b = df["y"] - df["pred"], df["y"] - df["base"]
    return (
        pd.DataFrame({"year": df["year"], "sse_m": e_m**2, "sse_b": e_b**2, "sae_m": e_m.abs(), "sae_b": e_b.abs()})
        .groupby("year")
        .sum()
    )


def year_bootstrap_ci(df: pd.DataFrame, stat: str = "skill", n_boot: int = 10_000, seed: int = 0, level: float = 0.90):
    """Expanded percentile CI of a skill statistic, resampling whole years with replacement.

    df columns: year, y, pred, base. stat: "skill" (MSE based) or "mae_skill". Deterministic for a given seed.
    """
    sums = _year_sums(df)
    num, den = {"skill": ("sse_m", "sse_b"), "mae_skill": ("sae_m", "sae_b")}[stat]
    n = len(sums)
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(n, np.full(n, 1.0 / n), size=n_boot)  # how often each year is drawn
    reps = 1 - (counts @ sums[num].to_numpy()) / (counts @ sums[den].to_numpy())
    a = expanded_alpha_half(n, level)
    return float(np.quantile(reps, a)), float(np.quantile(reps, 1 - a))


# ---------- split conformal ----------
def conformal_halfwidth(abs_residuals, alpha: float = 0.2) -> float:
    """Half-width q: the ceil((n+1)(1-alpha))-th smallest absolute residual; inf when that rank exceeds n."""
    r = np.sort(np.abs(np.asarray(abs_residuals, dtype=float)))
    k = math.ceil((len(r) + 1) * (1 - alpha))
    return math.inf if k > len(r) else float(r[k - 1])


def coverage(y, lo, hi) -> float:
    y, lo, hi = map(np.asarray, (y, lo, hi))
    return float(np.mean((y >= lo) & (y <= hi)))


# ---------- models ----------
def fit_ridge(x, y, alpha: float):
    """M1 / BNW: ridge regression with standardisation fitted on the training rows only (03-ML-SPEC §4, §6).

    alpha is a value of the lasso-scale grid (D-110); the fit converts it, the caller reports it unchanged.
    """

    # D-146: sklearn Lasso divides the squared error by 2n and Ridge does not, so the grid value becomes 2 n alpha
    return Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=2 * len(y) * alpha))]).fit(x, y)
