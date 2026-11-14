"""Assemble the training table: one row per cleaned rice label with its weather features (D-37, D-38, D-39, D-72).

Rain against a normal and the drought rain months need a normal from each fold's training years (D-66), so they are
computed in the evaluation harness, not stored here.

Rows that cannot be built (no calendar window, e.g. Mekong summer-autumn, D-37) are returned in `skipped` with the
reason; missing inputs (weights, cell data, days) raise instead of being filled.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from fieldshift.features.climate import official_counts, province_daily_weather, season_features
from fieldshift.features.hazards import risk_level_shares
from fieldshift.features.season_windows import season_window

RICE_SEASONS = ("spring", "autumn", "winter")
WEIGHT_METHODS = ("farmland_weighted", "centroid")  # D-106 fixed mask; E-008 centroid cells (one table per run)


def _covers(frame: pd.DataFrame, start: date, end: date) -> bool:
    """True when the daily frame holds every day of [start, end] at its ends (a shifted window can pass the data)."""
    return frame.index.min() <= pd.Timestamp(start) and frame.index.max() >= pd.Timestamp(end)


def _window(season: str, region: str, year: int, shift: tuple[int, int]) -> tuple[date, date]:
    """The NSO season window, its start and end moved by whole months (E-008 robustness; (0, 0) = the window)."""
    start, end = season_window(season, region, year)
    s = (pd.Timestamp(start) + pd.DateOffset(months=shift[0])).replace(day=1)
    e = (pd.Timestamp(end).replace(day=1) + pd.DateOffset(months=shift[1])) + pd.offsets.MonthEnd(0)
    return s.date(), e.date()


def build_feature_table(
    labels: pd.DataFrame, weights: pd.DataFrame, cell_frames: dict, regions: dict, shift: tuple[int, int] = (0, 0)
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # D-106: one fixed farmland mask for all years (cell_weights.csv, 05-DATA-CONTRACTS §3)
    # iter(): a GroupBy has a non-callable .keys attribute, so dict() alone would treat it as a mapping
    w_index = dict(iter(weights[weights["method"].isin(WEIGHT_METHODS)].groupby("province_nso")))
    daily_cache: dict = {}

    def daily(province: str) -> pd.DataFrame:
        if province not in daily_cache:
            if province not in w_index:
                raise KeyError(f"no farmland weights for {province}")
            g = w_index[province]
            wts = {(la, lo): wt for la, lo, wt in zip(g["lat"], g["lon"], g["farmland_weight"], strict=True)}
            daily_cache[province] = province_daily_weather({c: cell_frames[c] for c in wts}, wts)
        return daily_cache[province]

    def cell_weights(province: str) -> dict:
        g = w_index[province]
        return {(la, lo): wt for la, lo, wt in zip(g["lat"], g["lon"], g["farmland_weight"], strict=True)}

    rows, skipped = [], []
    lab = labels[(labels["crop"] == "rice") & labels["season"].isin(RICE_SEASONS)]
    for rec in lab.itertuples(index=False):
        region = regions[rec.province_nso]
        try:
            start, end = _window(rec.season, region, rec.year, shift)
        except ValueError as err:
            skipped.append(
                {"province_nso": rec.province_nso, "season": rec.season, "year": rec.year, "reason": str(err)}
            )
            continue
        if not _covers(daily(rec.province_nso), start, end):
            reason = f"the daily weather data do not cover the window {start}..{end}"
            skipped.append({"province_nso": rec.province_nso, "season": rec.season, "year": rec.year, "reason": reason})
            continue
        feats = season_features(daily(rec.province_nso), start, end)
        feats.update(official_counts(cell_frames, cell_weights(rec.province_nso), start, end))
        feats["n_points"] = len(cell_weights(rec.province_nso))  # 05 §4: cells aggregated
        rows.append(
            {
                **rec._asdict(),
                "calendar_region": region,
                "window_start": pd.Timestamp(start),
                "window_end": pd.Timestamp(end),
                **feats,
            }
        )
    skipped_df = pd.DataFrame(skipped, columns=["province_nso", "season", "year", "reason"])
    return pd.DataFrame(rows), skipped_df


def build_cell_month_rain(
    labels: pd.DataFrame, weights: pd.DataFrame, cell_frames: dict, regions: dict, shift: tuple[int, int] = (0, 0)
) -> pd.DataFrame:
    """Monthly rain of every weighted cell over each rice row's season window (05-DATA-CONTRACTS section 4a).

    The ML drought months compare these totals with the same month's mean over the training years of each fold, so
    the comparison itself happens in the fold (D-66); rows without a window (D-37) are left out, as in the table.
    """
    w = weights[weights["method"].isin(WEIGHT_METHODS)]
    rows = []
    lab = labels[(labels["crop"] == "rice") & labels["season"].isin(RICE_SEASONS)]
    for rec in lab.itertuples(index=False):
        try:
            start, end = _window(rec.season, regions[rec.province_nso], rec.year, shift)
        except ValueError:  # no window for this pair: the feature table lists it as skipped with its reason
            continue
        cells = w.loc[w["province_nso"] == rec.province_nso, ["lat", "lon", "farmland_weight"]]
        if not all(
            _covers(cell_frames[(la, lo)], start, end) for la, lo in zip(cells["lat"], cells["lon"], strict=True)
        ):
            continue  # listed as skipped with its reason by build_feature_table
        for la, lo, wt in cells.itertuples(index=False):
            rain = cell_frames[(la, lo)]["PRECTOTCORR"].loc[pd.Timestamp(start) : pd.Timestamp(end)]
            for month, total in rain.groupby(rain.index.strftime("%Y-%m")).sum().items():
                rows.append((rec.province_nso, rec.season, rec.year, la, lo, wt, month, float(total)))
    cols = ["province_nso", "season", "year", "lat", "lon", "farmland_weight", "month", "rain_mm"]
    return pd.DataFrame(rows, columns=cols)


def build_risk_level_features(
    labels: pd.DataFrame, weights: pd.DataFrame, cell_frames: dict, regions: dict
) -> pd.DataFrame:
    """Per rice row, the farmland shares meeting the heavy-rain, heat and cold risk-level rules over its season window
    (sensitivity run c of 03-ML-SPEC section 7; team 2026-11-14). Rows without a window (D-37) are left out."""
    w = weights[weights["method"].isin(WEIGHT_METHODS)]
    rows = []
    lab = labels[(labels["crop"] == "rice") & labels["season"].isin(RICE_SEASONS)]
    for rec in lab.itertuples(index=False):
        try:
            start, end = season_window(rec.season, regions[rec.province_nso], rec.year)
        except ValueError:  # no window for this pair: the feature table lists it as skipped with its reason
            continue
        g = w[w["province_nso"] == rec.province_nso]
        wts = {(la, lo): wt for la, lo, wt in zip(g["lat"], g["lon"], g["farmland_weight"], strict=True)}
        shares = risk_level_shares(cell_frames, wts, start, end)
        rows.append({"province_nso": rec.province_nso, "season": rec.season, "year": rec.year, **shares})
    return pd.DataFrame(rows)
