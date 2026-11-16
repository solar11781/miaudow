"""Tests for the satellite rain check (05-DATA-CONTRACTS §5c; queue item 45), written before the code.

Expected values are worked by hand from the contract: POWER monthly totals are sums of the daily values for complete
months only; both series are farmland-weighted with the §3 weights; a month missing in either series is dropped from
both and counted in n_dropped; cc is the Pearson correlation (Roversi et al. 2024, Table 5, R-M23).
"""

import numpy as np
import pandas as pd
import pytest

from fieldshift.features import rain_check

A, B = (19.0, 105.0), (19.5, 105.0)
WEIGHTS = {A: 0.25, B: 0.75}
MONTHS = ["2001-01", "2001-02", "2001-03", "2001-04", "2001-05"]


def daily(first: str, last: str, value: float = 1.0) -> pd.Series:
    return pd.Series(value, index=pd.date_range(first, last), dtype="float64")


def test_power_total_is_the_sum_of_the_days_of_a_complete_month():
    totals = rain_check.power_monthly_totals(daily("2001-01-01", "2001-02-28", 2.0))
    assert totals == {"2001-01": 62.0, "2001-02": 56.0}  # 31 x 2 and 28 x 2


def test_a_leap_february_needs_its_29th_day():
    assert rain_check.power_monthly_totals(daily("2000-02-01", "2000-02-28")) == {}
    assert rain_check.power_monthly_totals(daily("2000-02-01", "2000-02-29")) == {"2000-02": 29.0}


def test_a_month_with_a_missing_day_or_a_cut_end_is_not_used():
    series = daily("2001-01-01", "2001-03-15")  # March is cut at the 15th
    series["2001-02-10"] = np.nan  # February has a missing day (a -999 fill becomes NaN in parse_daily)
    assert rain_check.power_monthly_totals(series) == {"2001-01": 31.0}


# Hand-made series. Weights A 0.25, B 0.75. Months 2001-01..2001-05; 2001-04 is missing for IMERG cell B and 2001-05
# for POWER cell A, so both are dropped from both series: n_months 3, n_dropped 2.
IMERG = {
    A: {"2001-01": 100.0, "2001-02": 200.0, "2001-03": 300.0, "2001-04": 400.0, "2001-05": 500.0},
    B: {"2001-01": 200.0, "2001-02": 200.0, "2001-03": 300.0, "2001-05": 500.0},
}
POWER = {
    A: {"2001-01": 120.0, "2001-02": 180.0, "2001-03": 330.0, "2001-04": 400.0},
    B: {"2001-01": 100.0, "2001-02": 200.0, "2001-03": 300.0, "2001-04": 400.0, "2001-05": 500.0},
}


@pytest.fixture(scope="module")
def result() -> dict:
    return rain_check.rain_check(IMERG, POWER, WEIGHTS, MONTHS)


def test_months_are_farmland_weighted_and_a_month_missing_in_either_series_is_dropped_from_both(result):
    # IMERG: .25 x 100 + .75 x 200 = 175; .25 x 200 + .75 x 200 = 200; .25 x 300 + .75 x 300 = 300
    # POWER: .25 x 120 + .75 x 100 = 105; .25 x 180 + .75 x 200 = 195; .25 x 330 + .75 x 300 = 307.5
    assert result["months"] == [
        {"month": "2001-01", "imerg_mm": 175.0, "power_mm": 105.0},
        {"month": "2001-02", "imerg_mm": 200.0, "power_mm": 195.0},
        {"month": "2001-03", "imerg_mm": 300.0, "power_mm": 307.5},
    ]
    assert (result["n_months"], result["n_dropped"]) == (3, 2)


def test_means_are_over_the_kept_months(result):
    assert result["mean_imerg_mm"] == pytest.approx(225.0)  # (175 + 200 + 300) / 3
    assert result["mean_power_mm"] == pytest.approx(202.5)  # (105 + 195 + 307.5) / 3


def test_cc_is_the_pearson_correlation_of_the_kept_months(result):
    # x = 175, 200, 300 (mean 225): dx = -50, -25, 75.  y = 105, 195, 307.5 (mean 202.5): dy = -97.5, -7.5, 105.
    # Sxy = 4875 + 187.5 + 7875 = 12937.5; Sxx = 2500 + 625 + 5625 = 8750; Syy = 9506.25 + 56.25 + 11025 = 20587.5
    # cc = 12937.5 / sqrt(8750 x 20587.5) = 12937.5 / 13421.7 = 0.96392
    assert result["cc"] == pytest.approx(0.96392, abs=1e-5)


def test_the_result_has_exactly_the_fields_of_the_contract_and_its_sources(result):
    assert set(result) == {
        "months",
        "cc",
        "mean_imerg_mm",
        "mean_power_mm",
        "n_months",
        "n_dropped",
        "source_ids",
        "computed_by",
    }
    assert result["source_ids"] == ["R-N05", "R-N01", "R-N02", "R-M23", "R-N06"]  # §5c


def test_no_month_in_common_fails_loudly():
    with pytest.raises(ValueError, match="no month"):
        rain_check.rain_check({A: {}, B: {}}, POWER, WEIGHTS, MONTHS)


def test_a_constant_series_has_no_correlation_and_fails_loudly():
    flat = {c: dict.fromkeys(MONTHS, 100.0) for c in (A, B)}
    with pytest.raises(ValueError, match="constant"):
        rain_check.rain_check(flat, POWER, WEIGHTS, MONTHS)


def test_months_between_gives_every_month_of_the_period():
    got = rain_check.months_between(2001, 2024)
    assert (len(got), got[0], got[-1]) == (288, "2001-01", "2024-12")  # 24 years x 12 months


def test_imerg_cell_months_converts_each_file_to_mm_per_cell():
    box = (1087, 1091, 2847, 2852)  # exactly the pixels of cell (19.0, 105.0)
    lines = "\n".join(f"precipitation[0][{j}], " + ", ".join(["0.5"] * 5) for j in range(6))
    got = rain_check.imerg_cell_months({(2023, 2): lines}, box, [(19.0, 105.0)])
    assert got == {(19.0, 105.0): {"2023-02": pytest.approx(0.5 * 24 * 28)}}  # 0.5 mm/hr x 24 h x 28 days
