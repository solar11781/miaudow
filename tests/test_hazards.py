"""Tests for the displayed official risk-level rules (03-ML-SPEC §5a; written before the code, D-29).

Expectations come from QĐ 18/2021/QĐ-TTg (R-A01, quoted in research/evidence-audit-findings.md):
- heavy rain, Art. 44.1: "lượng mưa từ 100 mm ... trong 24 giờ" -> a day with >= 100 mm (100 included);
- heat, Art. 47.1 a-d: "đợt nắng nóng với nhiệt độ cao nhất trong ngày từ 35°c đến 37°c, kéo dài từ 3 ngày trở lên",
  "từ trên 37oc đến 39°c", "từ trên 39°c đến 41 °C", "trên 41°C", each "kéo dài từ 3 ngày" -> word for word (team,
  D-146, as D-120 for cold): >= 3 consecutive days with Tmax inside one band [35.0, 37.0], (37, 39], (39, 41], > 41
  (D-96: consecutive, 35.0 included; D-104: every such spell is level 1 or higher); a run that crosses bands is not one
  "đợt" of either band;
- cold, Art. 53.1 a/d (plains wording for every Nghệ An cell, D-96): "từ trên 8°c đến 13°c, kéo dài từ trên 5 ngày" and
  "từ 8°c trở xuống, kéo dài từ 3 ngày" -> word for word (team, D-120): >= 6 consecutive days with daily mean above 8.0
  and at or below 13.0, or >= 3 consecutive days at or below 8.0; a spell whose days fall in both bands is not
  classified by the decree and is not counted;
- drought rain part, Art. 48.1: "thiếu hụt tổng lượng mưa tháng trên 50% so với trung bình nhiều năm, kéo dài từ 2
  tháng" -> monthly rain < 50% of the 1991-2020 same-month mean, both readings (D-58);
- field time (D-97): daily rules over the days from sowing to the first reported harvest date; drought over the
  calendar months from the sowing month to the harvest month; share = sum of farmland weights where met (D-79).
"""

import numpy as np
import pandas as pd
import pytest

from fieldshift.features import hazards as hz


def _series(values, start="2010-01-01"):
    return pd.Series(np.asarray(values, dtype=float), index=pd.date_range(start, periods=len(values), freq="D"))


def test_heavy_rain_day_from_100_mm_included():
    assert hz.heavy_rain(_series([0, 99.9, 50])) is False
    assert hz.heavy_rain(_series([0, 100.0, 0])) is True


def test_heat_needs_three_consecutive_days_from_35_included():
    assert hz.heat(_series([35.0, 35.0, 35.0])) is True
    assert hz.heat(_series([36, 36, 34.9, 36, 36])) is False  # broken run: consecutive days (D-96)
    assert hz.heat(_series([34.9] * 10)) is False


def test_heat_spell_counts_only_inside_one_band_of_art_47_1():
    # D-146: Art. 47.1 a "từ 35°c đến 37°c", b "từ trên 37oc đến 39°c", c "từ trên 39°c đến 41 °C", d "trên 41°C";
    # a spell counts only as >= 3 consecutive days inside one band.
    assert hz.heat(_series([37.0, 37.0, 37.0])) is True  # band a, 37.0 included
    assert hz.heat(_series([37.1, 38, 39.0])) is True  # band b, 39.0 included
    assert hz.heat(_series([39.1, 40, 41.0])) is True  # band c, 41.0 included
    assert hz.heat(_series([41.1, 42, 45])) is True  # band d
    assert hz.heat(_series([36, 36, 38])) is False  # crosses bands a and b: not one "đợt" of either
    assert hz.heat(_series([38, 40, 38, 40])) is False  # alternates b and c
    assert hz.heat(_series([36, 38, 38, 38, 36])) is True  # 3 days inside band b
    assert hz.heat(_series([36, 36, 36, 42, 42])) is True  # 3 days inside band a
    assert hz.heat(_series([37.0, 38, 38])) is False  # 37.0 is band a, not "trên 37"
    assert hz.heat(_series([39.0, 40, 40])) is False  # 39.0 is band b, not "trên 39"
    assert hz.heat(_series([41.0, 42, 42])) is False  # 41.0 is band c, not "trên 41"
    assert hz.heat(_series([40, 42, 42])) is False  # crosses bands c and d


def test_cold_rules_plains_wording_and_mixed_spell():
    assert hz.cold(_series([13.0] * 6)) is True  # 53.1 a: more than 5 days, 13.0 included
    assert hz.cold(_series([13.0] * 5)) is False  # 5 days: not "trên 5 ngày"
    assert hz.cold(_series([8.0, 8.0, 8.0])) is True  # 53.1 d: 3 days at 8.0 or below
    assert hz.cold(_series([8.0, 8.1, 8.0, 8.0])) is False  # neither rule: 4 days, not 3 at <= 8 in a row
    assert hz.cold(_series([10, 10, 10, 10, 7, 7])) is False  # mixed spell: not classified, not counted (D-120)
    assert hz.cold(_series([8.5] * 6)) is True  # all six days in the band above 8, at most 13
    assert hz.cold(_series([13.1, 12, 12, 12, 12, 12])) is False  # only 5 days at or below 13


def test_drought_month_flags_strictly_more_than_half_deficit():
    rain = pd.Series([40.0, 50.0, 49.9, 100.0], index=[1, 2, 3, 4])
    clim = pd.Series([100.0, 100.0, 100.0, 100.0], index=[1, 2, 3, 4])
    assert list(hz.drought_months(rain, clim)) == [True, False, True, False]  # 50% deficit exactly is not "trên 50%"


def test_drought_two_readings():
    assert hz.drought_consecutive([True, True, False]) is True
    assert hz.drought_consecutive([True, False, True]) is False
    assert hz.drought_any2([True, False, True]) is True
    assert hz.drought_any2([True, False, False]) is False


def test_monthly_climatology_uses_1991_2020_only():
    idx = pd.date_range("1990-01-01", "2021-12-31", freq="D")
    pr = pd.Series(1.0, index=idx)
    pr[pr.index.year == 1990] = 100.0
    pr[pr.index.year == 2021] = 100.0
    clim = hz.monthly_climatology(pr)
    assert clim[1] == pytest.approx(31.0)
    assert clim[2] == pytest.approx((28 * 22 + 29 * 8) / 30)  # 8 leap years in 1991-2020


def _cell(year=2010, rain=0.0, tmax=30.0, tmean=20.0):
    idx = pd.date_range("1990-01-01", f"{max(year, 2020)}-12-31", freq="D")  # climatology needs 1991-2020
    return pd.DataFrame({"PRECTOTCORR": rain, "T2M_MAX": tmax, "T2M": tmean}, index=idx)


def test_daily_rules_use_only_the_field_days():
    c = _cell()
    c.loc["2010-03-10", "PRECTOTCORR"] = 150.0  # inside 17/1 - 17/5
    c.loc["2010-06-01", "PRECTOTCORR"] = 150.0  # outside
    c.loc["2010-05-17":"2010-05-19", "T2M_MAX"] = 36.0  # spell starts on the last field day: only 1 day inside
    clim = hz.monthly_climatology(c["PRECTOTCORR"])
    r = hz.cell_rules(c, year=2010, field_dates=[("01-17", "05-17")], months=[1, 2, 3, 4, 5], clim=clim)
    assert r["heavy_rain"] is True
    assert r["heat"] is False
    r2 = hz.cell_rules(c, year=2010, field_dates=[("06-06", "08-25")], months=[6, 7, 8], clim=clim)
    assert r2["heavy_rain"] is False  # 1 June is before 6 June


def test_daily_rules_join_the_days_of_several_crops():
    c = _cell()
    c.loc["2010-08-28":"2010-08-30", "T2M_MAX"] = 36.0  # 28-30 Aug: inside the second crop only
    clim = hz.monthly_climatology(c["PRECTOTCORR"])
    r = hz.cell_rules(
        c, year=2010, field_dates=[("01-17", "05-17"), ("08-15", "12-10")], months=list(range(1, 13)), clim=clim
    )
    assert r["heat"] is True


def test_drought_uses_the_months_and_both_readings():
    c = _cell(rain=1.0)
    c.loc["2010-02-01":"2010-02-28", "PRECTOTCORR"] = 0.0
    c.loc["2010-04-01":"2010-04-30", "PRECTOTCORR"] = 0.0
    clim = hz.monthly_climatology(c["PRECTOTCORR"])
    r = hz.cell_rules(c, year=2010, field_dates=[("01-17", "05-17")], months=[1, 2, 3, 4, 5], clim=clim)
    assert r["drought_rain_consecutive"] is False
    assert r["drought_rain_any2"] is True


def test_missing_weather_in_field_time_raises():
    c = _cell()
    c.loc["2010-03-01", "T2M_MAX"] = np.nan
    with pytest.raises(ValueError, match=r"weather missing inside the field time"):
        hz.cell_rules(
            c,
            year=2010,
            field_dates=[("01-17", "05-17")],
            months=[1, 2, 3, 4, 5],
            clim=hz.monthly_climatology(c["PRECTOTCORR"]),
        )


def test_farmland_share_sums_weights_where_met():
    met = {(19.0, 105.0): True, (19.0, 105.625): False, (18.5, 105.625): True}
    w = {(19.0, 105.0): 0.2, (19.0, 105.625): 0.5, (18.5, 105.625): 0.3}
    assert hz.farmland_share(met, w) == pytest.approx(0.5)
    with pytest.raises(KeyError):
        hz.farmland_share({(19.0, 105.0): True}, w)  # every weighted cell must be evaluated


def test_drought_consecutive_means_calendar_adjacent_months():
    # Art. 48.1 "kéo dài từ 2 tháng" read as consecutive (D-58 reading 1): months 5 and 8 are not consecutive even if
    # they are neighbours in a list with a gap (year-level union of field months, D-95).
    assert hz.drought_consecutive({5: True, 8: True}) is False
    assert hz.drought_consecutive({5: True, 6: True}) is True


def test_drought_reading_uses_month_numbers_in_cell_rules():
    c = _cell(rain=1.0)
    for m in ("2010-05", "2010-08"):
        c.loc[m, "PRECTOTCORR"] = 0.0
    clim = hz.monthly_climatology(c["PRECTOTCORR"])
    r = hz.cell_rules(c, year=2010, field_dates=[("05-01", "05-31"), ("08-01", "08-31")], months=[5, 8], clim=clim)
    assert r["drought_rain_consecutive"] is False
    assert r["drought_rain_any2"] is True


def test_incomplete_month_or_climatology_fails_loudly():
    # No guessing (CLAUDE.md): a month with a missing day has no monthly total; a climatology needs every day 1991-2020.
    c = _cell(rain=1.0)
    clim = hz.monthly_climatology(c["PRECTOTCORR"])
    c.loc["2010-02-10", "PRECTOTCORR"] = np.nan
    with pytest.raises(ValueError, match=r"rain missing in 2010-02"):
        hz.cell_rules(c, year=2010, field_dates=[("01-17", "01-31")], months=[1, 2], clim=clim)
    gap = c["PRECTOTCORR"].copy()
    gap.loc["2000-06-01"] = np.nan
    with pytest.raises(ValueError, match=r"daily rain incomplete"):
        hz.monthly_climatology(gap)
