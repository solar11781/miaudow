"""The satellite rain check: monthly rain of NASA IMERG against NASA POWER over the Nghe An cells (05-DATA-CONTRACTS
§5c, D-135).

Plain words: for every month 2001-2024 we compare two NASA rain numbers for the same cells. POWER's is the sum of its
daily values; IMERG's is a satellite rain rate times the hours of the month. Both are averaged over the cells with the
farmland weights. The Pearson correlation of the two monthly series is the result. Neither series is the truth, and no
source gives a threshold, so there is no pass or fail.
"""

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

from fieldshift.data import imerg
from fieldshift.features.soil_wetness import weighted_mean

SOURCE_IDS = ["R-N05", "R-N01", "R-N02", "R-M23", "R-N06"]  # §5c: IMERG, POWER, MODIS farmland, Pearson CC, POWER rain
COMPUTED_BY = "E-021"  # the satellite rain check in the team's experiment register (queue item 45)
FIRST_YEAR, LAST_YEAR = 2001, 2024  # §5c: the months 2001-01..2024-12
MIN_MONTHS = 2  # a correlation needs at least two points

Cell = tuple[float, float]


def months_between(first_year: int, last_year: int) -> list[str]:
    """Every "YYYY-MM" from January of the first year to December of the last."""
    return [f"{y}-{m:02d}" for y in range(first_year, last_year + 1) for m in range(1, 13)]


def power_monthly_totals(daily: pd.Series) -> dict[str, float]:
    """Sum of a POWER daily rain series (mm/day) per month, for complete months only (§5c)."""
    periods = daily.index.to_period("M")
    grouped = daily.groupby(periods).agg(["count", "sum"])  # count skips NaN, so a missing day shows
    return {
        str(period): float(row["sum"]) for period, row in grouped.iterrows() if row["count"] == period.days_in_month
    }


def imerg_cell_months(
    texts: Mapping[tuple[int, int], str], box: tuple[int, int, int, int], cells: Iterable[Cell]
) -> dict[Cell, dict[str, float]]:
    """Monthly mm per POWER cell from the monthly replies {(year, month): text}; a cell with a missing pixel has no
    value for that month."""
    cells = list(cells)
    out: dict[Cell, dict[str, float]] = {cell: {} for cell in cells}
    for (year, month), text in texts.items():
        grid = imerg.parse_monthly(text, box)
        for cell in cells:
            rate = imerg.cell_mean(grid, box, *cell)
            if not np.isnan(rate):
                out[cell][f"{year}-{month:02d}"] = imerg.monthly_mm(rate, year, month)
    return out


def rain_check(
    imerg_mm: Mapping[Cell, Mapping[str, float]],
    power_mm: Mapping[Cell, Mapping[str, float]],
    weights: Mapping[Cell, float],
    months: list[str],
) -> dict:
    """The check body of §5c: the kept months, their correlation and means, and how many months were dropped.

    A month missing in either weighted series (a weighted cell without a value) is dropped from both.
    """
    kept = []
    for month in months:
        i = weighted_mean({c: imerg_mm[c].get(month) for c in weights}, dict(weights))
        p = weighted_mean({c: power_mm[c].get(month) for c in weights}, dict(weights))
        if i is not None and p is not None:
            kept.append({"month": month, "imerg_mm": i, "power_mm": p})
    if not kept:
        raise ValueError("no month has both an IMERG and a POWER value")
    x = np.array([m["imerg_mm"] for m in kept])
    y = np.array([m["power_mm"] for m in kept])
    if len(kept) < MIN_MONTHS or x.std() == 0 or y.std() == 0:
        raise ValueError(f"cc is undefined: {len(kept)} months, or a constant series")
    return {
        "months": kept,
        "cc": float(np.corrcoef(x, y)[0, 1]),
        "mean_imerg_mm": float(x.mean()),
        "mean_power_mm": float(y.mean()),
        "n_months": len(kept),
        "n_dropped": len(months) - len(kept),
        "source_ids": SOURCE_IDS,
        "computed_by": COMPUTED_BY,
    }
