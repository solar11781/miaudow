"""Fold-time features of M1 and BNW (03-ML-SPEC section 4 Context group, section 6 M1; team 2026-11-14).

Plain words: some model inputs depend on which years count as "the past" in a fold, so they are rebuilt in every fold
from years before its test year only. Context: for every stored weather feature, the province's mean over those years
in the same season (its "usual" climate); the no-weather model BNW sees only these and the season. Interactions: every
weather feature also enters multiplied by a spring indicator, so spring and winter rice get their own weather weights
while sharing one pooled model. Means use each province's own weather (known), never yields, so a province held out
in the spatial test still gets them.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from fieldshift.features.climate import drought_rain_counts
from fieldshift.ml.runner import add_precip_anom

SPRING = "spring"
UNIT_SEASON = ["province_nso", "season"]  # unit key until the unit_id crosswalk exists (05-DATA-CONTRACTS section 2)
FOLD_RAIN = "precip_anom_pct"  # season rain vs the training-years mean (D-66), built by runner.add_precip_anom
DROUGHT_COLS = ["drought_rain_months", "drought_rain_consecutive", "drought_rain_any2"]  # 05-DATA-CONTRACTS 4a
ROW_KEY = ["province_nso", "season", "year"]
CELL = ["lat", "lon"]


def add_context_means(df: pd.DataFrame, before_year: int, cols: list[str]) -> pd.DataFrame:
    """ctx_<col> = the province and season mean of <col> over the years before `before_year`."""
    out = df.copy()
    means = df[df["year"] < before_year].groupby(UNIT_SEASON)[cols].mean()
    key = pd.MultiIndex.from_frame(df[UNIT_SEASON])
    for c in cols:
        out[f"ctx_{c}"] = means[c].reindex(key).to_numpy()
    return out


def add_drought_months(df: pd.DataFrame, month_rain: pd.DataFrame, before_year: int) -> pd.DataFrame:
    """Drought rain months of each row against every cell's same-month mean over the years before `before_year`.

    month_rain: the cell monthly rain of features.feature_table.build_cell_month_rain. A row without that table's
    months, or with a month that has no earlier year, gets no value (not scored).
    """
    mr = month_rain.assign(moy=month_rain["month"].str[5:])
    key = [*UNIT_SEASON, *CELL, "moy"]
    normal = mr[mr["year"] < before_year].groupby(key)["rain_mm"].mean()
    mr = mr.assign(normal=normal.reindex(pd.MultiIndex.from_frame(mr[key])).to_numpy())
    values = {}
    for row_key, g in mr.groupby(ROW_KEY, sort=False):
        if g["normal"].isna().any():
            continue
        cells = {c: part.sort_values("month") for c, part in g.groupby(CELL)}
        values[row_key] = drought_rain_counts(
            {c: part["rain_mm"].reset_index(drop=True) for c, part in cells.items()},
            {c: part["normal"].reset_index(drop=True) for c, part in cells.items()},
            {c: float(part["farmland_weight"].iloc[0]) for c, part in cells.items()},
        )
    found = pd.DataFrame.from_dict(values, orient="index", columns=DROUGHT_COLS)
    found.index = pd.MultiIndex.from_tuples(found.index, names=ROW_KEY) if len(found) else found.index
    keys = pd.MultiIndex.from_frame(df[ROW_KEY])
    out = df.copy()
    for c in DROUGHT_COLS:
        out[c] = found[c].reindex(keys).to_numpy() if len(found) else np.nan
    return out


def add_season_terms(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """is_spring (1 or 0) and <col>_x_spring = <col> times is_spring."""
    out = df.copy()
    out["is_spring"] = (df["season"] == SPRING).astype(float)
    for c in cols:
        out[f"{c}_x_spring"] = df[c] * out["is_spring"]
    return out


def model_columns(weather: list[str], stored: list[str]) -> tuple[list[str], list[str]]:
    """(weather columns of M1, context columns of M1 and BNW) for the given weather features."""
    return [*weather, *(f"{c}_x_spring" for c in weather)], ["is_spring", *(f"ctx_{c}" for c in stored)]


def make_fold_transform(stored: list[str]) -> Callable[[pd.DataFrame, pd.Index], pd.DataFrame]:
    """The runner's fold_transform: rain anomaly, context means and season terms, all from years before the fold."""

    def transform(df: pd.DataFrame, train_idx: pd.Index) -> pd.DataFrame:
        before_year = int(df.loc[train_idx, "year"].max()) + 1
        past = df.index[df["year"] < before_year]
        out = add_precip_anom(df, past)
        out = add_context_means(out, before_year, stored)
        weather = [c for c in [*stored, FOLD_RAIN] if c in out.columns]
        return add_season_terms(out, weather).replace([np.inf, -np.inf], np.nan)

    return transform
