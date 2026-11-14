"""Tests for the fold-time features of M1 and BNW (03-ML-SPEC section 4 Context group, section 6 M1).

Spec: context = rice season and province long-term climate means over the training years of each fold (past-only,
D-66; no region label, D-107); M1 has rice-season interactions. Team 2026-11-14: the climate means are the
training-years means of every stored weather feature, per province and season (the window of that season); the
interactions are a spring indicator times every weather feature. Past-only: everything is fitted on years before the
fold's test year, from each province's own weather (weather is known, the yields of the test year are not), so a
province held out in the spatial test still gets its means (as B0 does, D-146).
"""

import pandas as pd
import pytest

from fieldshift.ml.fold_features import add_context_means, add_season_terms, make_fold_transform, model_columns


def _rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "province_nso": ["A", "A", "A", "A", "B", "B"],
            "season": ["spring", "spring", "spring", "winter", "spring", "spring"],
            "year": [2010, 2011, 2012, 2010, 2010, 2012],
            "tmax_mean_c": [30.0, 32.0, 99.0, 25.0, 28.0, 26.0],
            "precip_sum_mm": [100.0, 300.0, 400.0, 50.0, 200.0, 100.0],
        }
    )


def test_context_means_use_only_years_before_the_cutoff_per_province_and_season():
    out = add_context_means(_rows(), before_year=2012, cols=["tmax_mean_c"])
    # A spring: mean of 2010, 2011 = 31 (2012's 99 is the test year); A winter: 25; B spring: 28 (only 2010)
    assert list(out["ctx_tmax_mean_c"]) == pytest.approx([31.0, 31.0, 31.0, 25.0, 28.0, 28.0])


def test_season_terms_give_each_weather_feature_a_spring_weight():
    out = add_season_terms(_rows(), cols=["tmax_mean_c"])
    assert list(out["is_spring"]) == [1.0, 1.0, 1.0, 0.0, 1.0, 1.0]
    assert list(out["tmax_mean_c_x_spring"]) == [30.0, 32.0, 99.0, 0.0, 28.0, 26.0]


def test_model_columns_keep_weather_out_of_the_no_weather_model():
    weather, context = model_columns(["tmax_mean_c"], stored=["tmax_mean_c"])
    assert context == ["is_spring", "ctx_tmax_mean_c"]
    assert weather == ["tmax_mean_c", "tmax_mean_c_x_spring"]


def test_the_fold_transform_is_past_only_and_adds_the_rain_anomaly():
    df = _rows()
    train_idx = df.index[df["year"] < 2012]
    out = make_fold_transform(["tmax_mean_c", "precip_sum_mm"])(df, train_idx)
    # rain normal of A spring over 2010-2011 = 200: 2012 has 400 -> +100%; B spring normal = 200 (2010 only)
    assert out.loc[2, "precip_anom_pct"] == pytest.approx(100.0)
    assert out.loc[5, "precip_anom_pct"] == pytest.approx(-50.0)
    assert out.loc[2, "ctx_tmax_mean_c"] == pytest.approx(31.0)
    assert out.loc[2, "precip_anom_pct_x_spring"] == pytest.approx(100.0)
    changed = df.copy()
    changed.loc[2, "tmax_mean_c"] = -5.0  # the test year's own weather never enters the means
    assert make_fold_transform(["tmax_mean_c", "precip_sum_mm"])(changed, train_idx).loc[0, "ctx_tmax_mean_c"] == 31.0


def test_a_held_out_province_gets_means_from_its_own_earlier_years():
    df = _rows()
    train_idx = df.index[(df["year"] < 2012) & (df["province_nso"] != "B")]  # B held out (spatial test)
    out = make_fold_transform(["tmax_mean_c", "precip_sum_mm"])(df, train_idx)
    assert out.loc[5, "ctx_tmax_mean_c"] == pytest.approx(28.0)
    assert out.loc[5, "precip_anom_pct"] == pytest.approx(-50.0)
