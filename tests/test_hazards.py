"""Tests for the displayed official risk-level rules (03-ML-SPEC §5a; written before the code, D-29).

Expectations come from QĐ 18/2021/QĐ-TTg (R-A01):
- heavy rain, Art. 44.1: "lượng mưa từ 100 mm ... trong 24 giờ" -> a day with >= 100 mm (100 included);
- heat, Art. 47.1 a-d: "đợt nắng nóng với nhiệt độ cao nhất trong ngày từ 35°c đến 37°c, kéo dài từ 3 ngày trở lên",
  "từ trên 37oc đến 39°c", "từ trên 39°c đến 41 °C", "trên 41°C", each "kéo dài từ 3 ngày" -> word for word (team,
  D-146, as D-120 for cold): >= 3 consecutive days with Tmax inside one band [35.0, 37.0], (37, 39], (39, 41], > 41
  (D-96: consecutive, 35.0 included; D-104: every such spell is level 1 or higher); a run that crosses bands is not one
  "đợt" of either band;
- cold, Art. 53.1 a/d (plains wording for every Nghệ An cell, D-96): "từ trên 8°c đến 13°c, kéo dài từ trên 5 ngày" and
  "từ 8°c trở xuống, kéo dài từ 3 ngày" -> word for word (team, D-120): >= 6 consecutive days with daily mean above 8.0
  and at or below 13.0, or >= 3 consecutive days at or below 8.0; a run that crosses bands is not one "đợt" of either
  band, while a qualifying run inside one band counts also inside a longer cold spell (D-146);
- drought rain part, Art. 48.1: "thiếu hụt tổng lượng mưa tháng trên 50% so với trung bình nhiều năm, kéo dài từ 2
  tháng" -> monthly rain < 50% of the 1991-2020 same-month mean, both readings (D-58);
- field time (D-97): daily rules over the days from sowing to the first reported harvest date; drought over the
  calendar months from the sowing month to the harvest month; share = sum of farmland weights where met (D-79).
"""

from datetime import date

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


def test_cold_examples_of_the_spec_and_the_8_c_edge():
    # Source: 03-ML-SPEC section 5a (D-146): "6 days at 10 C followed by 3 days at 7 C: each part meets its own band's
    # rule, so the label is met"; Art. 53.1 d "từ 8°c trở xuống": 8.0 C belongs to band d, not to band a
    assert hz.cold(_series([10] * 6 + [7] * 3)) is True
    assert hz.cold(_series([8.0] + [9] * 5)) is False  # band a has only 5 days, band d only 1


def test_spell_never_joins_across_the_gap_between_field_blocks():
    # Source: 03-ML-SPEC section 5a: "a spell is counted only inside one block of consecutive field days"; 15-18 May are
    # hot, but 17 May is not a field day, so the blocks hold 2 days (15-16) and 1 day (18)
    c = _cell()
    c.loc["2010-05-15":"2010-05-18", "T2M_MAX"] = 36.0
    clim = hz.monthly_climatology(c["PRECTOTCORR"])
    r = hz.cell_rules(c, year=2010, field_dates=[("05-01", "05-16"), ("05-18", "06-30")], months=[5, 6], clim=clim)
    assert r["heat"] is False


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


def test_drought_month_without_a_climatology_value_fails_loudly():
    # Source: Art. 48.1 compares with "trung bình nhiều năm"; without that normal the month has no reading (no guessing)
    month_rain = pd.Series([10.0, 10.0], index=[5, 6])
    clim = pd.Series([100.0], index=[5])
    with pytest.raises(ValueError, match=r"\[6\]"):
        hz.drought_months(month_rain, clim)


def test_risk_level_shares_weight_the_cells_that_meet_each_rule_in_a_window():
    # Source: 03-ML-SPEC section 7 sensitivity (c) with section 5a rules (team 2026-11-14: the farmland share meeting
    # each rule over the NSO season window): cell A (weight 0.6) has a 120 mm day, cell B (0.4) 3 days at 36 C and
    # 6 days at 12 C mean; heavy rain 0.6, heat 0.4, cold 0.4; a 100 mm day outside the window does not count
    a, b = _cell(), _cell()
    a.loc["2010-03-05", "PRECTOTCORR"] = 120.0
    a.loc["2010-08-01", "PRECTOTCORR"] = 100.0  # outside the window
    b.loc["2010-04-01":"2010-04-03", "T2M_MAX"] = 36.0
    b.loc["2010-02-10":"2010-02-15", "T2M"] = 12.0
    shares = hz.risk_level_shares(
        {"A": a, "B": b}, {"A": 0.6, "B": 0.4}, date(2010, 2, 1), date(2010, 6, 30), cold_rule=hz.cold
    )
    assert shares == {
        "risk_heavy_rain": pytest.approx(0.6),
        "risk_heat": pytest.approx(0.4),
        "risk_cold": pytest.approx(0.4),
    }


def test_risk_level_shares_refuse_missing_weather_in_the_window():
    c = _cell()
    c.loc["2010-03-05", "T2M_MAX"] = np.nan
    with pytest.raises(ValueError, match="missing"):
        hz.risk_level_shares({"A": c}, {"A": 1.0}, date(2010, 2, 1), date(2010, 6, 30), cold_rule=hz.cold)


def _days(*runs: tuple[float, int]) -> pd.Series:
    """Daily means made of (temperature, number of days) runs, between mild 20 C days."""
    values = [20.0]
    for temp, n in runs:
        values += [temp] * n + [20.0]
    return pd.Series(values, index=pd.date_range("2010-01-01", periods=len(values), freq="D"))


@pytest.mark.parametrize(
    ("runs", "met"),
    [
        # Art. 53.1 a, "vùng núi, trung du Bắc Bộ": "từ trên 8°c đến 13°c ... kéo dài trên 10 ngày"
        ([(10.0, 10)], False),
        ([(10.0, 11)], True),
        ([(13.0, 11)], True),  # 13.0 included ("đến 13°c")
        # Art. 53.1 b: "từ trên 4°c đến 8°c, kéo dài từ trên 5 ngày đến 10 ngày"
        ([(6.0, 5)], False),
        ([(6.0, 6)], True),
        ([(8.0, 6)], True),  # 8.0 is in band b ("đến 8°c"), not band a ("từ trên 8°c")
        # Art. 53.1 c: "từ 0°c đến 4°c, kéo dài từ 3 ngày đến 5 ngày"
        ([(2.0, 2)], False),
        ([(2.0, 3)], True),
        ([(0.0, 3)], True),
        # Art. 53.2 đ (level 2): "dưới 0°c, kéo dài từ 3 ngày đến 5 ngày"
        ([(-1.0, 3)], True),
        ([(-1.0, 2)], False),
    ],
)
def test_cold_rule_of_the_northern_mountains_follows_art_53(runs, met):
    assert hz.cold_mountains(_days(*runs)) is met


def test_a_long_spell_at_or_below_4_c_counts_in_the_mountains_although_it_swaps_bands_daily():
    # Art. 53.3 b "từ 4°c trở xuống, kéo dài trên 10 ngày": 11 days alternating 1 C and -1 C; no 3-day run stays
    # inside band c (0-4 C) or band đ (below 0 C), yet the whole run is at or below 4 C for more than 10 days
    temps = [20.0] + [1.0 if i % 2 == 0 else -1.0 for i in range(11)] + [20.0]
    series = pd.Series(temps, index=pd.date_range("2010-01-01", periods=len(temps), freq="D"))
    assert hz.cold_mountains(series)
    assert not hz.cold_mountains(series.drop(series.index[11]))  # 10 such days


def test_a_plains_spell_is_not_a_mountain_spell():
    # Art. 53.1 a: 6 days at 8-13 C meet the plains wording (more than 5 days) but not the mountain one (more than 10)
    six = _days((10.0, 6))
    assert hz.cold(six)
    assert not hz.cold_mountains(six)


@pytest.mark.parametrize(
    ("province", "region", "rule"),
    [
        ("Lao Cai", "northern_mountains", "mountains"),  # NSO "Northern midlands and mountain areas" (team 2026-11-14)
        ("Ha Noi", "red_river_delta", "plains"),  # "đồng bằng Bắc Bộ"
        ("Quang Ninh", "red_river_delta", "plains"),  # NSO Red River Delta
        ("Nghe An", "north_central", "plains"),  # QĐ 18/2021 Phụ lục II "Khu vực Bắc Trung Bộ"
        ("Quang Ngai", "central_coast", "plains"),  # Phụ lục II "Khu vực Trung Trung Bộ"
        ("Binh Dinh", "central_coast", None),  # Phụ lục II "Khu vực Nam Trung Bộ": Art. 53 names no rule
        ("Gia Lai", "highlands_southeast", None),  # Tây Nguyên: no rule
        ("Can Tho", "mekong", None),  # Nam Bộ: no rule
    ],
)
def test_each_province_gets_the_cold_wording_of_its_art_53_region(province, region, rule):
    expected = {"mountains": hz.cold_mountains, "plains": hz.cold, None: None}[rule]
    assert hz.cold_rule_of(province, region) is expected


def test_risk_level_shares_use_the_given_cold_rule_and_zero_where_none_applies():
    # Art. 53: 7 days at 10 C meet the plains wording, not the mountain one; a region without a cold rule meets none
    c = _cell()
    c.loc["2010-02-10":"2010-02-16", "T2M"] = 10.0
    window = (date(2010, 2, 1), date(2010, 6, 30))
    assert hz.risk_level_shares({"A": c}, {"A": 1.0}, *window, cold_rule=hz.cold)["risk_cold"] == 1.0
    assert hz.risk_level_shares({"A": c}, {"A": 1.0}, *window, cold_rule=hz.cold_mountains)["risk_cold"] == 0.0
    assert hz.risk_level_shares({"A": c}, {"A": 1.0}, *window, cold_rule=None)["risk_cold"] == 0.0


def test_risk_level_shares_refuse_a_window_with_days_missing_from_the_data():
    # Python rules: missing data fail loudly; a dropped day must not join two spells into one
    c = _cell().drop(pd.Timestamp("2010-03-05"))
    with pytest.raises(ValueError, match="missing"):
        hz.risk_level_shares({"A": c}, {"A": 1.0}, date(2010, 2, 1), date(2010, 6, 30), cold_rule=hz.cold)
    short = _cell().loc[:"2010-03-31"]
    with pytest.raises(ValueError, match="missing"):
        hz.risk_level_shares({"A": short}, {"A": 1.0}, date(2010, 2, 1), date(2010, 6, 30), cold_rule=hz.cold)


@pytest.mark.parametrize(("province", "region"), [("Ha Noi", "red_river"), ("Da Nang City", "central_coast")])
def test_an_unknown_region_or_central_coast_province_fails_loudly(province, region):
    # Python rules: unknown data symbols fail loudly; a renamed region must not silently drop the cold rule
    with pytest.raises(ValueError, match=province):
        hz.cold_rule_of(province, region)


def _monthly_rain(totals: dict[str, float]) -> pd.Series:
    """Daily rain whose month totals are `totals` ({"YYYY-MM": mm}), spread evenly over the days of each month."""
    parts = []
    for month, total in totals.items():
        days = pd.date_range(f"{month}-01", pd.Timestamp(f"{month}-01") + pd.offsets.MonthEnd(0), freq="D")
        parts.append(pd.Series(total / len(days), index=days))
    return pd.concat(parts)


def test_season_drought_readings_follow_the_window_months_in_order_across_the_year_end():
    # E-014 (D-58): both readings over an NSO season window of whole months; Art. 48.1 "thiếu hụt ... trên 50%": 40 of
    # a 100 mm normal is a drought month, 60 is not. December and January are consecutive months although 12 + 1 != 1.
    clim = pd.Series(100.0, index=range(1, 13))
    split = _monthly_rain({"2009-11": 40.0, "2009-12": 60.0, "2010-01": 40.0, "2010-02": 60.0})
    assert hz.season_drought_readings(split, date(2009, 11, 1), date(2010, 2, 28), clim) == (False, True)
    joined = _monthly_rain({"2009-11": 60.0, "2009-12": 40.0, "2010-01": 40.0, "2010-02": 60.0})
    assert hz.season_drought_readings(joined, date(2009, 11, 1), date(2010, 2, 28), clim) == (True, True)
    one = _monthly_rain({"2009-11": 40.0, "2009-12": 60.0, "2010-01": 60.0, "2010-02": 60.0})
    assert hz.season_drought_readings(one, date(2009, 11, 1), date(2010, 2, 28), clim) == (False, False)


def test_season_drought_readings_refuse_a_partial_month_or_a_missing_day():
    # Art. 48.1 uses "tổng lượng mưa tháng": a window that cuts a month, or a missing day, has no monthly total
    clim = pd.Series(100.0, index=range(1, 13))
    rain = _monthly_rain({"2010-01": 40.0, "2010-02": 40.0})
    with pytest.raises(ValueError, match="whole months"):
        hz.season_drought_readings(rain, date(2010, 1, 5), date(2010, 2, 28), clim)
    with pytest.raises(ValueError, match="rain missing"):
        hz.season_drought_readings(rain.drop(pd.Timestamp("2010-02-10")), date(2010, 1, 1), date(2010, 2, 28), clim)
