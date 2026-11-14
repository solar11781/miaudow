"""Rows of artifacts/soil_wetness.json: root-zone soil wetness per P-02 plan crop and past year (05-DATA-CONTRACTS
§4d; D-97, D-135).

Plain words: NASA POWER's GWETROOT (a MERRA-2 model value, 0 = completely dry soil, 1 = saturated) averaged over the
days each crop of the P-02 trial plans was in the field, weighted by farmland, next to its 1991-2020 average.
"""

from collections.abc import Iterable

import pandas as pd

from fieldshift.features.hazard_labels import YEARS
from fieldshift.features.hazards import CLIM_YEARS, field_days

SOURCE_IDS = ["R-N01", "R-W12", "R-N02", "R-A15"]  # §4d: POWER, GWETROOT meaning, MODIS farmland, WMO normal
COMPUTED_BY = "E-020"  # EXPERIMENTS: the computation of soil_wetness.json


def _field_day_mean(daily: pd.DataFrame, year: int, field_dates: list) -> float | None:
    """Mean daily GWETROOT over the field days; None when a day is missing (never filled, §4d)."""
    values = daily["GWETROOT"].reindex(field_days(year, field_dates))
    return None if values.isna().any() else float(values.mean())


def _weighted(per_cell: dict, weights: dict) -> float | None:
    """Farmland-weighted mean of the cell values; None when any weighted cell has none."""
    if any(per_cell[c] is None for c in weights):
        return None
    return float(sum(w * per_cell[c] for c, w in weights.items()))


def soil_wetness_rows(
    crops: list[dict], cells: dict[tuple, pd.DataFrame], weights: dict[tuple, float], years: Iterable[int] = YEARS
) -> list[dict]:
    """One row per plan crop x year: the field-day mean (value) and its 1991-2020 normal; cells: daily GWETROOT."""
    normal_years = range(CLIM_YEARS[0], CLIM_YEARS[1] + 1)
    rows = []
    for crop in crops:
        dates = crop["field_dates"]
        means = {c: {y: _field_day_mean(cells[c], y, dates) for y in set(years) | set(normal_years)} for c in weights}
        normal_of = {
            c: None if any(m[y] is None for y in normal_years) else sum(m[y] for y in normal_years) / len(normal_years)
            for c, m in means.items()
        }
        normal = _weighted(normal_of, weights)
        for year in years:
            rows.append(
                {
                    **{k: crop[k] for k in ("plan_id", "crop_key", "season")},
                    "field_dates": [list(pair) for pair in dates],
                    "year": year,
                    "value": _weighted({c: means[c][year] for c in weights}, weights),
                    "normal": normal,
                    "n_cells": len(weights),
                    "source_ids": SOURCE_IDS,
                    "computed_by": COMPUTED_BY,
                }
            )
    return rows
