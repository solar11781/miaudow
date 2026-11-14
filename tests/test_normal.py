"""Tests for the past-only normal yield and the percent anomaly target (03-ML-SPEC §3).

Expectations come from the cited definitions: Iizumi and Ramankutty 2016 "three-year RM yield (year t-3 to t-1)";
Paudel et al. 2021 "linear trend from a 5-year window", past-only ("would cause information leakage" otherwise);
target anom = yield / normal - 1 (D-66); no normal without that many past years (D-72).
"""

import math

import pandas as pd
import pytest

from fieldshift.ml.normal import add_anomaly, compare_normal_methods, past_normal, pick_normal_method


def _s(yields, start=2000, sid="A|rice|spring|0"):
    return pd.DataFrame({"series_id": sid, "year": list(range(start, start + len(yields))), "yield_t_ha": yields})


def test_three_year_mean_uses_t_minus_3_to_t_minus_1():
    n = past_normal(_s([4.0, 5.0, 6.0, 7.0, 9.0]), "mean3")
    assert n.iloc[:3].isna().all()
    assert n.iloc[3] == pytest.approx(5.0)
    assert n.iloc[4] == pytest.approx(6.0)


def test_five_year_trend_is_linear_fit_on_previous_five_years():
    n = past_normal(_s([1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 0.0]), "trend5")
    assert n.iloc[:5].isna().all()
    assert n.iloc[5] == pytest.approx(6.0)  # line through 1..5 extended one year
    # year 6 uses 2, 3, 4, 5, 10: OLS slope 18 / 10 = 1.8, mean 4.8 at the middle year, so value at t = 4.8 + 3 * 1.8 = 10.2
    assert n.iloc[6] == pytest.approx(10.2)


def test_normal_never_uses_the_target_year_or_later():
    a = past_normal(_s([4.0, 5.0, 6.0, 7.0, 8.0, 9.0]), "trend5")
    b = past_normal(_s([4.0, 5.0, 6.0, 7.0, 8.0, 99.0]), "trend5")
    assert a.iloc[5] == pytest.approx(b.iloc[5])
    c = past_normal(_s([4.0, 5.0, 6.0, 70.0]), "mean3")
    assert c.iloc[3] == pytest.approx(5.0)


def test_missing_yield_in_window_gives_no_normal():
    n = past_normal(_s([4.0, None, 6.0, 7.0, 8.0, 9.0, 10.0]), "mean3")
    assert n.iloc[3:5].isna().all()  # windows that contain the missing year
    assert n.iloc[5] == pytest.approx(7.0)


def test_absent_year_in_window_gives_no_normal():
    # Source: 03-ML-SPEC section 3 and D-72: "a normal exists only when that many past years exist";
    # mean3 needs t-3 to t-1
    df = pd.DataFrame(
        {"series_id": "A|0", "year": [2000, 2002, 2003, 2004, 2005], "yield_t_ha": [4.0, 5.0, 6.0, 7.0, 8.0]}
    )
    n = past_normal(df, "mean3")
    assert n.iloc[:4].isna().all()  # 2003 and 2004 lack 2001 in their windows
    assert n.iloc[4] == pytest.approx(6.0)  # 2005: mean of 2002, 2003, 2004


def test_duplicate_series_year_or_index_fails_loudly():
    # Source: 03-ML-SPEC section 3 (normal from years before the target year only): a second row of the same year would
    # enter its own window; python rules: unknown data fails loudly
    dup_year = pd.DataFrame(
        {"series_id": "A|0", "year": [2000, 2001, 2002, 2003, 2003], "yield_t_ha": [4.0, 5.0, 6.0, 7.0, 9.0]}
    )
    with pytest.raises(ValueError, match=r"A\|0.*2003"):
        past_normal(dup_year, "mean3")
    dup_index = pd.concat([_s([4.0, 5.0, 6.0, 7.0], sid="A|0"), _s([1.0, 1.0, 1.0, 1.0], sid="B|0")])
    with pytest.raises(ValueError, match="index"):
        past_normal(dup_index, "mean3")


def test_normal_restarts_in_each_series():
    df = pd.concat([_s([5.0, 5.0, 5.0], sid="A|0"), _s([8.0, 8.0, 8.0, 8.0], start=2003, sid="A|1")], ignore_index=True)
    n = past_normal(df, "mean3")
    assert n.iloc[:6].isna().all()
    assert n.iloc[6] == pytest.approx(8.0)


def test_anomaly_is_yield_over_normal_minus_one_and_null_without_normal():
    out = add_anomaly(_s([4.0, 5.0, 6.0, 7.0]), "mean3")
    assert out["anom"].iloc[:3].isna().all()
    assert out["anom"].iloc[3] == pytest.approx(7.0 / 5.0 - 1)
    assert math.isclose(out["normal_t_ha"].iloc[3], 5.0)


def test_unknown_method_and_non_positive_normal_fail_loudly():
    with pytest.raises(ValueError, match=r"unknown normal method"):
        past_normal(_s([1.0, 2.0, 3.0]), "mm_trend")
    with pytest.raises(ValueError, match=r"normal yield <= 0"):
        add_anomaly(_s([5.0, 4.0, 3.0, 2.0, 1.0, 1.0]), "trend5")  # trend reaches 0 at year 5: no percent anomaly


def _seasons(yields_by_season: dict[str, list[float]], start: int = 2000) -> pd.DataFrame:
    return pd.concat(
        [
            _s(ys, start=start, sid=f"A|rice|{season}|0").assign(season=season)
            for season, ys in yields_by_season.items()
        ],
        ignore_index=True,
    )


def test_normal_choice_scores_both_methods_by_squared_error_on_the_inner_years():
    # Source: 03-ML-SPEC section 3 (chosen by skill on years before the test period: the inner test years of the first
    # outer fold, only where both have a normal; D-107 inner years = last 30%, half up); team 2026-11-14: score = mean
    # squared error of yield minus normal, one pick. Yields 1..16 over 2000-2015 rise by 1 a year: the 5-year trend is
    # exact (error 0); the 3-year mean of t-3..t-1 is 2 below (error 2, squared 4). Both exist from 2005: 11 years,
    # 30% of 11 = 3.3 -> 3 inner years 2013-2015. 2016 is a test year and is never used.
    df = _seasons({"spring": [float(v) for v in range(1, 18)]})
    out = compare_normal_methods(df, before_year=2016)
    assert out["years"] == [2013, 2014, 2015]
    assert out["mse"] == {"mean3": pytest.approx(4.0), "trend5": pytest.approx(0.0)}
    assert out["n_rows"] == 3
    assert out["choice"] == "trend5"


def test_normal_choice_reports_each_season_separately():
    # Source: team 2026-11-14: per-season errors are reported. Spring rises by 1 a year (mean3 error 2, squared 4;
    # trend5 exact), winter is flat (both exact); pooled over the 3 + 3 inner rows: mean3 (4 * 3 + 0) / 6 = 2, trend5 0
    df = _seasons({"spring": [float(v) for v in range(1, 17)], "winter": [4.0] * 16})
    out = compare_normal_methods(df, before_year=2016)
    assert out["mse_by_season"] == {
        "spring": {"mean3": pytest.approx(4.0), "trend5": pytest.approx(0.0)},
        "winter": {"mean3": pytest.approx(0.0), "trend5": pytest.approx(0.0)},
    }
    assert out["mse"] == {"mean3": pytest.approx(2.0), "trend5": pytest.approx(0.0)}


def test_errors_equal_to_3_decimals_keep_the_3_year_mean():
    # Source: team 2026-11-14: a tie at 3 decimals keeps the 3-year mean; otherwise the lower error wins
    assert pick_normal_method({"mean3": 0.1004, "trend5": 0.0996}) == "mean3"  # both 0.100
    assert pick_normal_method({"mean3": 0.1006, "trend5": 0.0994}) == "trend5"  # 0.101 vs 0.099
    assert pick_normal_method({"mean3": 0.0994, "trend5": 0.1006}) == "mean3"
