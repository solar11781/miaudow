"""Tests for province-season weather features (written before the code, D-29).

Spec: D-26 (province weather = farmland-weighted daily average of POWER cells), D-37/D-38 (season windows),
D-39 and 05-DATA-CONTRACTS §4 (features: rain total; CDD = longest run of days with rain < 1 mm, ETCCDI; R20mm = days
with rain >= 20 mm, ETCCDI; Rx5day = largest 5-consecutive-day rain total, ETCCDI; mean Tmax and Tmin; TXx = highest
Tmax, ETCCDI; hot days = days with Tmax strictly above 35 C, QĐ 18/2021 Art. 5.21 "vượt quá 35°c"; GWETROOT mean and
min; mean ALLSKY_SFC_SW_DWN). Rain against a normal is not a stored feature: its normal comes from the training years of
each fold (D-66), so it is computed in the evaluation harness. §4a counts (D-72): per cell, then weighted: rain > 50 mm
(Art. 5.17), daily mean < 13 C (Art. 5.18 "dưới 13oc"), < 15 C (TT 25/2022 Art. 3.6); drought rain months against a
monthly normal passed in by the caller (training years, D-66). Expected values below are computed by hand.
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from fieldshift.features.climate import drought_rain_counts, official_counts, province_daily_weather, season_features

VARS = ["PRECTOTCORR", "T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "GWETROOT"]


def _daily(start, values: dict):
    n = len(next(iter(values.values())))
    idx = pd.date_range(start, periods=n, freq="D", name="date")
    base = {v: np.zeros(n) for v in VARS}
    base.update({k: np.asarray(v, dtype=float) for k, v in values.items()})
    return pd.DataFrame(base, index=idx)


def test_province_weather_is_weighted_average_of_cells():
    a = _daily("2010-01-01", {"PRECTOTCORR": [10, 0], "T2M_MAX": [30, 30]})
    b = _daily("2010-01-01", {"PRECTOTCORR": [0, 20], "T2M_MAX": [20, 40]})
    out = province_daily_weather({(19.0, 105.0): a, (19.5, 105.0): b}, {(19.0, 105.0): 0.75, (19.5, 105.0): 0.25})
    assert list(out.PRECTOTCORR) == [7.5, 5.0]
    assert list(out.T2M_MAX) == [27.5, 32.5]


def test_province_weather_rejects_weights_not_summing_to_one():
    a = _daily("2010-01-01", {"PRECTOTCORR": [1]})
    with pytest.raises(ValueError, match=r"weights sum to"):
        province_daily_weather({(19.0, 105.0): a}, {(19.0, 105.0): 0.5})


RAIN = [0, 0.5, 25, 0, 0, 0, 0.9, 30, 1.0, 0]  # 10 days
TMAX = [30, 36, 35, 34, 37, 33, 30, 31, 35.5, 29]


@pytest.fixture
def ten_days():
    return _daily(
        "2010-05-01",
        {
            "PRECTOTCORR": RAIN,
            "T2M_MAX": TMAX,
            "T2M_MIN": [20] * 10,
            "GWETROOT": [0.5, 0.4, 0.6, 0.5, 0.5, 0.5, 0.5, 0.5, 0.3, 0.5],
            "ALLSKY_SFC_SW_DWN": [20] * 10,
        },
    )


def test_rain_features(ten_days):
    f = season_features(ten_days, date(2010, 5, 1), date(2010, 5, 10))
    assert f["precip_sum_mm"] == pytest.approx(57.4)
    assert "rain_vs_normal_pct" not in f  # D-66: computed per fold from training years, not stored
    assert f["dry_spell_max_d"] == 4  # days 4-7: 0, 0, 0, 0.9 (< 1 mm); day 9 (1.0) is not dry
    assert f["heavy_rain_d"] == 2  # R20mm: 25 and 30
    assert f["rx5day_mm"] == pytest.approx(
        31.9
    )  # days 4-8: 0 + 0 + 0 + 0.9 + 30 = 30.9; days 6-10: 0+0.9+30+1+0 = 31.9


def test_temperature_and_other_features(ten_days):
    f = season_features(ten_days, date(2010, 5, 1), date(2010, 5, 10))
    assert f["tmax_mean_c"] == pytest.approx(np.mean(TMAX))
    assert f["tmin_mean_c"] == pytest.approx(20.0)
    assert f["txx_c"] == pytest.approx(37.0)
    assert f["gwetroot_mean"] == pytest.approx(0.48)
    assert f["gwetroot_min"] == pytest.approx(0.3)
    assert f["srad_mean_mj_m2_d"] == pytest.approx(20.0)


def test_only_days_inside_the_window_count(ten_days):
    f = season_features(ten_days, date(2010, 5, 3), date(2010, 5, 5))
    assert f["precip_sum_mm"] == pytest.approx(25.0)
    assert f["txx_c"] == pytest.approx(37.0)


def test_window_not_fully_covered_by_data_raises(ten_days):
    # Spec (no guessing): a feature over a window with missing days is undefined.
    with pytest.raises(ValueError, match=r"not fully covered by daily data"):
        season_features(ten_days, date(2010, 4, 25), date(2010, 5, 10))


def test_official_counts_per_cell_then_weighted():
    # D-72: counted in each cell, then averaged with the farmland weights (not on the averaged series).

    a = _daily("2010-05-01", {"PRECTOTCORR": [60, 50, 0], "T2M_MAX": [30] * 3})
    a["T2M"] = [12.9, 13.0, 14.9]
    b = _daily("2010-05-01", {"PRECTOTCORR": [40, 40, 40], "T2M_MAX": [30] * 3})
    b["T2M"] = [20.0, 20.0, 20.0]
    c = official_counts({(1, 1): a, (2, 2): b}, {(1, 1): 0.25, (2, 2): 0.75}, date(2010, 5, 1), date(2010, 5, 3))
    assert c["official_heavy_rain_d"] == pytest.approx(0.25 * 1)  # only 60 is above 50 (50.0 is not)
    assert c["ret_hai_d"] == pytest.approx(0.25 * 1)  # only 12.9 is below 13
    assert c["ret_dam_d"] == pytest.approx(0.25 * 3)  # 12.9, 13.0, 14.9 are below 15
    # averaging first would hide the cell extreme: weighted daily rain 45, 42.5, 30 has no day above 50


def test_drought_rain_counts_against_a_given_normal_both_readings():
    # D-58, D-66: months with rain more than 50% below the given monthly normal; consecutive and any-2 readings.

    monthly = {
        (1, 1): pd.Series([10.0, 10.0, 60.0], index=[2, 3, 4]),
        (2, 2): pd.Series([10.0, 60.0, 10.0], index=[2, 3, 4]),
    }
    normal = {(1, 1): pd.Series(100.0, index=[2, 3, 4]), (2, 2): pd.Series(100.0, index=[2, 3, 4])}
    c = drought_rain_counts(monthly, normal, {(1, 1): 0.5, (2, 2): 0.5})
    assert c["drought_rain_months"] == pytest.approx(0.5 * 2 + 0.5 * 2)
    assert c["drought_rain_consecutive"] == pytest.approx(0.5)  # only cell (1, 1) has two months in a row
    assert c["drought_rain_any2"] == pytest.approx(1.0)


def test_hot_days_are_counted_per_cell_then_weighted():
    # D-72: official hazard days are counted in each cell, then weighted ("averaging daily information ... tends to
    # dampen gridded extremes", Zhang et al. 2011; E-000k used hot days). Art. 5.21: strictly above 35 C.

    a = _daily("2010-05-01", {"PRECTOTCORR": [0, 0, 0], "T2M_MAX": [36.0, 35.0, 37.0]})
    a["T2M"] = 25.0
    b = _daily("2010-05-01", {"PRECTOTCORR": [0, 0, 0], "T2M_MAX": [30.0, 30.0, 30.0]})
    b["T2M"] = 25.0
    c = official_counts({(1, 1): a, (2, 2): b}, {(1, 1): 0.5, (2, 2): 0.5}, date(2010, 5, 1), date(2010, 5, 3))
    assert c["hot_days_d"] == pytest.approx(0.5 * 2)  # cell a: 36 and 37 (35.0 is not above 35)
    # on the averaged series (33, 32.5, 33.5) there would be no hot day at all
    f = season_features(
        province_daily_weather({(1, 1): a, (2, 2): b}, {(1, 1): 0.5, (2, 2): 0.5}), date(2010, 5, 1), date(2010, 5, 3)
    )
    assert "hot_days_d" not in f
