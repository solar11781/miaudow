"""Tests for the evaluation harness (written before the code, D-29). Synthetic data only (D-80).

Spec: docs/03-ML-SPEC.md §6-§8 and D-68, D-83, D-107:
- rolling origin: test year t, train on years < t; spatial holdout: leave one region out, also years < t;
- inner folds (D-107): inside a training window, the last 30% of its years (nearest whole year, at least 1) are inner
  test years, each predicted from all years before it (Paudel et al. 2022: training always from the first year);
- references: B0 = mean anomaly of the same series in the training years (D-113); B2 = previous-year anomaly of the same series;
  spatial holdout B0 (D-146): the held-out series' own mean anomaly over its years before the test year;
- ridge penalty (D-146): the grid value a is on the lasso scale of Meroni et al. 2021 (scikit-learn Lasso minimises
  1/(2n) ||y - Xw||^2 + a ||w||_1, Ridge minimises ||y - Xw||^2 + alpha ||w||^2), so each ridge fit uses
  alpha = 2 n a with n = rows of that fit, i.e. it minimises 1/(2n) ||y - Xw||^2 + a ||w||^2;
- same rows for every model and reference;
- metrics: RMSE, MAE, skill = 1 - MSE_model / MSE_reference, MAE skill = 1 - MAE_model / MAE_reference; R2 on the
  held-out rows = 1 - SSE / sum of squares around their mean (D-114: Paudel et al. 2021, thesis eq. A.4);
- year bootstrap: whole years resampled, 10,000 resamples, expanded percentile interval (Hesterberg 2015, arXiv
  1411.5279, read 2026-11-12: "(q_{alpha'/2}, q_{1-alpha'/2}), where alpha'/2 = Phi(-sqrt(n/(n-1)) t_{alpha/2,n-1})");
- split conformal (Lei et al. 2018; Angelopoulos and Bates 2023): quantile ceil((n+1)(1-alpha))/n of the absolute
  residuals; infinite when ceil((n+1)(1-alpha)) > n; coverage = share of outcomes inside.
Expected values computed by hand.
"""

import inspect
import math

import numpy as np
import pandas as pd
import pytest

from fieldshift.ml import evaluation as ev

YEARS = np.array([2008, 2008, 2009, 2009, 2010, 2010, 2011, 2011])
REGIONS = np.array(["n", "s", "n", "s", "n", "s", "n", "s"])


def test_rolling_origin_trains_only_on_earlier_years():
    (tr0, te0), (tr1, te1) = ev.rolling_origin_splits(YEARS, test_years=[2010, 2011])
    assert list(tr0) == [0, 1, 2, 3]
    assert list(te0) == [4, 5]
    assert list(tr1) == [0, 1, 2, 3, 4, 5]
    assert list(te1) == [6, 7]


def test_region_holdout_hides_region_and_future():
    splits = ev.region_holdout_splits(YEARS, REGIONS, test_years=[2010])
    assert len(splits) == 2
    for tr, te in splits:
        assert set(REGIONS[te]).isdisjoint(REGIONS[tr])
        assert YEARS[tr].max() < 2010
        assert set(YEARS[te]) == {2010}


def test_default_test_years_are_2016_to_2024():
    assert list(ev.TEST_YEARS) == list(range(2016, 2025))  # D-69


@pytest.mark.parametrize(
    ("years", "expected"),
    [
        (range(1998, 2016), [2011, 2012, 2013, 2014, 2015]),  # 18 years x 0.3 = 5.4 -> 5
        (range(2000, 2016), [2011, 2012, 2013, 2014, 2015]),  # 16 x 0.3 = 4.8 -> 5
        (range(2011, 2016), [2014, 2015]),  # 5 x 0.3 = 1.5 -> 2 (nearest, half up)
        (range(2015, 2016), [2015]),  # at least 1
    ],
)
def test_inner_test_years_are_the_last_30_percent(years, expected):
    assert ev.inner_test_years(list(years)) == expected


def test_inner_splits_predict_each_inner_year_from_all_earlier_years():
    years = np.array([2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009])
    splits = ev.inner_splits(years)
    assert [int(years[te][0]) for _, te in splits] == [2007, 2008, 2009]
    for tr, te in splits:
        assert years[tr].min() == 2000
        assert years[tr].max() == years[te][0] - 1


def _panel():
    return pd.DataFrame(
        {
            "series_id": ["a", "a", "a", "b", "b", "b"],
            "year": [2010, 2011, 2012] * 2,
            "anom": [0.1, -0.2, 0.3, 0.0, 0.05, -0.1],
        }
    )


def test_b0_is_each_series_own_training_years_mean_anomaly():
    # D-113: climatology per series (province x season), not one national mean: the WMO/WWRP verification guide warns
    # that "Non-homegeneous samples can lead to overestimates of forecast skill" when samples are pooled.
    df = _panel()
    tr, te = df.index[df.year < 2012], df.index[df.year == 2012]
    p = ev.predict_b0(df, tr, te)
    assert list(p) == pytest.approx([(0.1 - 0.2) / 2, (0.0 + 0.05) / 2])
    new = pd.DataFrame({"series_id": ["c"], "year": [2012], "anom": [0.3]}, index=[6])
    df2 = pd.concat([df, new])
    assert np.isnan(ev.predict_b0(df2, tr, df2.index[df2.year == 2012]).loc[6])  # no training years: no reference


def test_holdout_b0_is_the_held_out_series_own_mean_before_the_test_year():
    # D-146: in the spatial holdout the held-out series has no training rows; its B0 is its own mean anomaly over the
    # years before the test year (like B2's own previous year); no future year enters.
    df = pd.concat([_panel(), pd.DataFrame({"series_id": ["a"], "year": [2013], "anom": [9.0]}, index=[6])])
    te = df.index[df.year == 2012]
    assert list(ev.predict_b0_holdout(df, te)) == pytest.approx([(0.1 - 0.2) / 2, (0.0 + 0.05) / 2])
    assert ev.predict_b0_holdout(df, df.index[df.year == 2010]).isna().all()  # no earlier year: no reference
    te13 = df.index[df.year == 2013]
    assert ev.predict_b0_holdout(df, te13).loc[6] == pytest.approx((0.1 - 0.2 + 0.3) / 3)


def test_b2_is_the_previous_year_anomaly_of_the_same_series():
    df = _panel()
    te = df.index[df.year == 2012]
    assert list(ev.predict_b2(df, te)) == pytest.approx([-0.2, 0.05])
    te0 = df.index[df.year == 2010]
    assert ev.predict_b2(df, te0).isna().all()  # no previous year: no persistence forecast


def test_same_rows_keeps_rows_every_model_can_predict():
    preds = {"b0": pd.Series([0.1, 0.1, 0.1]), "b2": pd.Series([np.nan, 0.2, 0.3]), "m1": pd.Series([0.0, np.nan, 0.1])}
    assert list(ev.same_rows(preds)) == [False, False, True]


def test_metrics_by_hand():
    y = np.array([0.0, 1.0, -1.0, 2.0])
    p = np.array([0.0, 2.0, -1.0, 0.0])  # errors 0, 1, 0, -2
    base = np.zeros(4)  # errors 0, -1, 1, -2
    assert ev.rmse(y, p) == pytest.approx(math.sqrt(5 / 4))
    assert ev.mae(y, p) == pytest.approx(3 / 4)
    assert ev.skill_score(y, p, base) == pytest.approx(1 - (5 / 4) / (6 / 4))
    assert ev.mae_skill(y, p, base) == pytest.approx(1 - (3 / 4) / (4 / 4))
    assert not hasattr(ev, "spearman")  # dropped (D-68)
    # D-114: Paudel et al. 2021, thesis eq. A.4: R2 = 1 - sum (Ytrue - Yobs)^2 / sum (Ytrue - mean(Ytrue))^2 on the test set.
    assert ev.r2_oos(y, p) == pytest.approx(1 - 5 / 5)  # mean 0.5; SST 0.25 + 0.25 + 2.25 + 2.25 = 5


def test_expanded_percentile_alpha_by_hand():
    # n = 4 years, 90% interval: t_{0.05,3} = 2.3534 (t table); sqrt(4/3) * 2.3534 = 2.7175; Phi(-2.7175) = 0.00329
    assert ev.expanded_alpha_half(4, 0.90) == pytest.approx(0.00329, abs=2e-5)
    assert ev.expanded_alpha_half(100000, 0.90) == pytest.approx(0.05, abs=1e-3)  # large n: plain percentile


def _boot_df():
    # Model perfect every year except 2011 (errors -2, +2); baseline error 1 per row. Point skill = 0.
    # With 4 years and 2011 drawn k times (Binomial(4, 1/4)): skill = 1 - k.
    return pd.DataFrame(
        {"year": YEARS, "y": [1.0, -1.0] * 4, "pred": [1.0, -1.0, 1.0, -1.0, 1.0, -1.0, -1.0, 1.0], "base": [0.0] * 8}
    )


def test_year_bootstrap_uses_whole_years_and_expanded_percentiles():
    df = _boot_df()
    # alpha'/2 = 0.00329; P(k = 4) = 0.0039 > 0.00329 so the lower limit is 1 - 4 = -3; P(k = 0) = 0.316 so the upper is 1.
    lo, hi = ev.year_bootstrap_ci(df, stat="skill", n_boot=200_000, seed=0, level=0.90)
    assert lo == pytest.approx(-3.0)
    assert hi == pytest.approx(1.0)
    assert ev.year_bootstrap_ci(df, stat="skill", n_boot=1000, seed=1) == ev.year_bootstrap_ci(
        df, stat="skill", n_boot=1000, seed=1
    )


def test_year_bootstrap_default_is_10000_resamples():

    assert inspect.signature(ev.year_bootstrap_ci).parameters["n_boot"].default == 10_000  # D-68


def test_split_conformal_quantile_and_coverage():
    res = np.arange(1, 10, dtype=float)  # n = 9, alpha 0.2: ceil(10 * 0.8) = 8 -> q = 8
    assert ev.conformal_halfwidth(res, alpha=0.2) == pytest.approx(8.0)
    assert ev.conformal_halfwidth(np.array([1.0, 2.0, 3.0]), alpha=0.2) == math.inf  # ceil(4 * 0.8) = 4 > 3
    assert ev.coverage(
        np.array([0.0, 1.0, 5.0]), np.array([-1.0, -1.0, -1.0]), np.array([1.0, 1.0, 1.0])
    ) == pytest.approx(2 / 3)


def test_ridge_pipeline_standardises_inside_the_fold():
    # 03-ML-SPEC §4: standardisation fitted on the training rows only. A test row far outside the training range must
    # be scaled with the training mean and sd (not its own).
    rng = np.random.default_rng(0)
    x_tr = rng.normal(0, 1, size=(200, 1))
    y_tr = 2.0 * x_tr[:, 0] + rng.normal(0, 0.01, 200)
    model = ev.fit_ridge(x_tr, y_tr, alpha=1e-6)
    assert model.predict(np.array([[10.0]]))[0] == pytest.approx(20.0, rel=0.02)
    mean = model.named_steps["scale"].mean_[0]
    assert mean == pytest.approx(x_tr.mean(), abs=1e-12)


def test_ridge_penalty_is_the_lasso_scale_grid_value_times_2n():
    # D-146: with a = grid value, the fit minimises 1/(2n) ||y - Xw||^2 + a ||w||^2 on the standardised training rows.
    # Closed form (centred y, standardised X): w = (X'X + 2 n a I)^-1 X'y.
    rng = np.random.default_rng(1)
    n, a = 50, 0.1
    x = rng.normal(size=(n, 3))
    y = x @ np.array([1.0, -0.5, 0.2]) + rng.normal(0, 0.5, n)
    model = ev.fit_ridge(x, y, alpha=a)
    z = (x - x.mean(axis=0)) / x.std(axis=0)
    w = np.linalg.solve(z.T @ z + 2 * n * a * np.eye(3), z.T @ (y - y.mean()))
    assert model.named_steps["ridge"].coef_ == pytest.approx(w, rel=1e-9)
    assert model.named_steps["ridge"].alpha == pytest.approx(2 * n * a)


def test_bootstrap_needs_at_least_two_years():
    # Hesterberg's alpha' uses n/(n-1) and t with n-1 degrees of freedom: undefined for one year; fail loudly.
    with pytest.raises(ValueError, match=r"at least 2 resampled years"):
        ev.expanded_alpha_half(1, 0.90)
