"""Tests for the rolling-origin experiment runner (03-ML-SPEC §6-§8; D-68, D-83, D-107). Synthetic data only (D-80).

Spec: per outer test year: tune the penalty on the inner folds only; fit on all training years; predict the test year;
B0, B2 and BNW (same algorithm and settings minus the weather columns, D-93) on the same rows; conformal half-width from
the inner-fold residuals (D-107); fold-time features (rain vs the training-years mean, D-66) use training rows only,
refit inside every inner split too (03-ML-SPEC §4 "fitted on the training years of each fold only"; audit 2026-11-13).
Unit key: `province_nso` until the unit_id crosswalk exists (05-DATA-CONTRACTS §2, §4c).
"""

from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fieldshift.ml import evaluation as ev
from fieldshift.ml.runner import (
    ALPHA_GRID,
    _tune,
    add_precip_anom,
    run_rolling_origin,
    run_secondary,
    run_spatial_holdout,
)


def _synthetic(n_series=30, years=range(1998, 2025), seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n_series):
        for y in years:
            x = rng.normal()
            rows.append(
                {
                    "series_id": f"s{s}",
                    "province_nso": f"u{s}",
                    "season": "spring",
                    "year": y,
                    "x": x,
                    "ctx": float(s % 3),
                    "anom": 0.1 * x + rng.normal(0, 0.02),
                }
            )
    return pd.DataFrame(rows)


ALPHAS = [1e-3, 1e-1, 10.0]


def test_weather_model_beats_references_on_synthetic_signal():
    out = run_rolling_origin(_synthetic(), weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)
    m = out["metrics"]
    assert m["skill_vs_b0"] > 0.8
    assert m["skill_vs_bnw"] > 0.8
    assert m["n_test_years"] == 9


def test_all_models_scored_on_the_same_rows():
    out = run_rolling_origin(_synthetic(), weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)
    p = out["predictions"]
    assert p[["m1", "bnw", "b0", "b2"]].notna().all().all()
    assert out["metrics"]["n_rows"] == len(p)


def test_test_year_outcomes_never_change_predictions():
    df = _synthetic()
    a = run_rolling_origin(df, weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)["predictions"]
    df2 = df.copy()
    df2.loc[df2.year == 2020, "anom"] += 5.0  # change only the outcomes of test year 2020
    b = run_rolling_origin(df2, weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)["predictions"]
    pa = a[a.year == 2020].set_index("series_id")["m1"]
    pb = b[b.year == 2020].set_index("series_id")["m1"]
    assert np.allclose(pa, pb)


def test_interval_coverage_is_near_80_percent_on_exchangeable_noise():
    out = run_rolling_origin(_synthetic(n_series=60), weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)
    assert out["metrics"]["coverage_80"] == pytest.approx(0.8, abs=0.08)


def test_precip_anom_uses_training_rows_only():
    df = pd.DataFrame(
        {
            "province_nso": ["u"] * 3,
            "season": ["spring"] * 3,
            "year": [2000, 2001, 2002],
            "precip_sum_mm": [100.0, 300.0, 900.0],
        }
    )
    out = add_precip_anom(df, train_idx=df.index[df.year < 2002])
    assert out.loc[2, "precip_anom_pct"] == pytest.approx((900 / 200 - 1) * 100)
    assert out.loc[0, "precip_anom_pct"] == pytest.approx((100 / 200 - 1) * 100)


def test_default_grid_is_meroni_2021_and_edge_choices_are_reported():
    # Source: D-110 (team): Meroni et al. 2021 grid, 13 log-spaced points from 1e-5 to 1; report when the chosen
    # penalty is at an end of the grid.

    assert len(ALPHA_GRID) == 13
    assert ALPHA_GRID[0] == pytest.approx(1e-5)
    assert ALPHA_GRID[-1] == pytest.approx(1.0)
    assert np.allclose(np.diff(np.log10(ALPHA_GRID)), 5 / 12)
    out = run_rolling_origin(
        _synthetic(n_series=10), weather_cols=["x"], context_cols=["ctx"], alphas=[1e-3, 1e-1, 10.0]
    )
    edge = out["metrics"]["alpha_at_edge"]
    assert set(edge) == {"m1", "bnw"}
    assert all(0.0 <= v <= 1.0 for v in edge.values())
    # D-146: the reported penalty stays in grid units (each fit converts it to 2 n a), so the edge report still works
    p = out["predictions"]
    assert set(p["alpha_m1"]) | set(p["alpha_bnw"]) <= {1e-3, 1e-1, 10.0}


def test_rows_without_an_anomaly_are_refused():
    # 03-ML-SPEC §3: years without a normal are not training or test rows; the caller must drop them first.
    df = _synthetic(n_series=5)
    df.loc[0, "anom"] = np.nan
    with pytest.raises(ValueError, match=r"rows without an anomaly"):
        run_rolling_origin(df, weather_cols=["x"], context_cols=["ctx"], alphas=[1.0])


def test_precip_anom_runs_on_the_training_table_columns():
    # 05-DATA-CONTRACTS §4c: the real table (scripts/build_training_table.py) keys units by province_nso.
    path = Path("data/processed/training_table.csv")
    if not path.exists():
        pytest.skip("training table not built (gitignored; scripts/build_training_table.py)")
    df = pd.read_csv(path, nrows=200)
    out = add_precip_anom(df, train_idx=df.index[df.year < 2010])
    assert "precip_anom_pct" in out


def test_fold_transform_is_refit_inside_every_inner_split():
    # 03-ML-SPEC §4: every fitted transformation is fitted on the training years of each fold only, so the inner
    # test years used for tuning and the interval (§7, D-107) must not enter their own fold-time features.
    df = _synthetic(n_series=4)
    seen = []

    def spy(data, train_idx):
        seen.append(frozenset(data.loc[train_idx, "year"]))
        return add_precip_anom(data.assign(precip_sum_mm=100.0), train_idx)

    run_rolling_origin(df, weather_cols=["x"], context_cols=["ctx"], alphas=[1.0], fold_transform=spy)
    for t in ev.TEST_YEARS:
        train_years = sorted(y for y in set(df.year) if y < t)
        assert frozenset(train_years) in seen  # outer fit
        for u in ev.inner_test_years(train_years):
            assert frozenset(y for y in train_years if y < u) in seen  # each inner split


def test_inner_folds_skip_test_rows_without_fold_time_features():
    # 03-ML-SPEC §3-4: a row without a past normal is not scored. A series that starts inside an inner test year has
    # no inner training rows, so its rain anomaly is missing there; tuning must skip it, not turn every MSE into NaN.

    df = _synthetic(n_series=6).assign(precip_sum_mm=100.0)
    train_years = sorted(y for y in set(df.year) if y < ev.TEST_YEARS[0])
    u = ev.inner_test_years(train_years)[0]
    late = df[(df.series_id == "s0") & (df.year >= u)].assign(series_id="late", province_nso="late")
    df = pd.concat([df, late], ignore_index=True)
    train_idx = df.index[df["year"] < ev.TEST_YEARS[0]]
    _, res = _tune(df, train_idx, ["x", "ctx", "precip_anom_pct"], ALPHAS, add_precip_anom)
    assert len(res) > 0
    assert np.isfinite(res).all()


def test_the_decided_penalty_grid_runs():
    # Source: D-110 (Meroni et al. 2021 grid): the runner must accept ALPHA_GRID itself, a numpy array
    out = run_rolling_origin(
        _synthetic(n_series=8, years=range(2006, 2025)), weather_cols=["x"], context_cols=["ctx"], alphas=ALPHA_GRID
    )
    assert out["predictions"]["alpha_m1"].isin(ALPHA_GRID).all()


def test_test_row_without_a_past_rain_normal_is_not_scored():
    # Source: 03-ML-SPEC section 3 and D-66: the rain normal comes from training rows only; a unit seen first in the
    # test year has none, so that row is not scored; one year later it has one and is scored
    df = _synthetic(n_series=8, years=range(2006, 2025))
    df["precip_sum_mm"] = 100.0 + df["x"]
    new = df[(df.series_id == "s0") & (df.year >= 2020)].assign(series_id="new", province_nso="u_new")
    df = pd.concat([df, new], ignore_index=True)
    out = run_rolling_origin(
        df, weather_cols=["precip_anom_pct"], context_cols=["ctx"], alphas=ALPHAS, fold_transform=add_precip_anom
    )
    p = out["predictions"]
    assert not ((p.series_id == "new") & (p.year == 2020)).any()
    assert ((p.series_id == "new") & (p.year == 2021)).any()


def test_duplicate_series_year_rows_fail_loudly():
    # Source: 03-ML-SPEC section 6: one row per series and year; python rules: unknown data fails loudly
    df = _synthetic(n_series=3, years=range(2010, 2025))
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match=r"s0.*2010"):
        run_rolling_origin(df, weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)


def test_missing_input_feature_fails_loudly():
    # Source: python rules "unknown data fails loudly": only fold-time features may be missing (03-ML-SPEC section 3)
    df = _synthetic(n_series=3, years=range(2010, 2025))
    df.loc[(df.series_id == "s1") & (df.year == 2020), "x"] = np.nan
    with pytest.raises(ValueError, match=r"\['x'\]"):
        run_rolling_origin(df, weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)


def _with_regions(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(region=df["province_nso"].map(lambda u: f"r{int(u[1:]) % 3}"))  # three blocks of provinces


def test_spatial_holdout_predicts_each_region_from_the_other_regions_only():
    # Source: 03-ML-SPEC section 7.2: blocks = regions, trained only on years < t; a held-out region's labels never
    # train the model that predicts it (Roberts et al. 2017); B0 = the held-out series' own earlier mean (D-146)
    df = _with_regions(_synthetic(n_series=12, years=range(2004, 2025)))
    out = run_spatial_holdout(df, weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)
    p = out["predictions"]
    assert set(p["region"]) == {"r0", "r1", "r2"}
    assert sorted(p["year"].unique()) == list(range(2016, 2025))
    changed = df.copy()
    held = (df["region"] == "r1") & (df["year"] < 2020)
    changed.loc[held, "anom"] += 3.0  # only the held-out region's own earlier labels change
    q = run_spatial_holdout(changed, weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)
    a = p[(p.year == 2020) & (p.region == "r1")].set_index("series_id")["m1"]
    b = q["predictions"][(q["predictions"].year == 2020) & (q["predictions"].region == "r1")].set_index("series_id")[
        "m1"
    ]
    assert np.allclose(a, b)


def test_spatial_holdout_b0_is_each_series_own_earlier_mean():
    df = _with_regions(_synthetic(n_series=6, years=range(2010, 2025)))
    p = run_spatial_holdout(df, weather_cols=["x"], context_cols=["ctx"], alphas=ALPHAS)["predictions"]
    row = p[(p.series_id == "s1") & (p.year == 2016)].iloc[0]
    assert row["b0"] == pytest.approx(df[(df.series_id == "s1") & (df.year < 2016)]["anom"].mean())


@pytest.mark.parametrize(("fit", "grid"), [(ev.fit_lgbm, ev.M2_GRID[:2]), (ev.fit_rf, ev.M3_GRID[:2])])
def test_secondary_models_use_the_same_folds_and_never_the_test_years_outcomes(fit, grid):
    # Source: 03-ML-SPEC sections 6-7 and D-145: M2 and M3 on the same rows and folds as M1, tuned on earlier
    # years only (inner folds, D-107); outcomes of a test year never change its predictions
    df = _synthetic(n_series=6, years=range(2004, 2025))
    a = run_secondary(df, weather_cols=["x"], context_cols=["ctx"], model=(partial(fit, seed=0), grid))
    assert sorted(a["year"].unique()) == list(range(2016, 2025))
    assert set(a["param"]) <= set(range(len(grid)))
    changed = df.copy()
    changed.loc[changed.year == 2020, "anom"] += 5.0
    b = run_secondary(changed, weather_cols=["x"], context_cols=["ctx"], model=(partial(fit, seed=0), grid))
    pa = a[a.year == 2020].set_index("series_id")["pred"]
    pb = b[b.year == 2020].set_index("series_id")["pred"]
    assert np.allclose(pa, pb)


def test_secondary_models_are_reproducible_with_a_fixed_seed():
    # Source: python rules: randomness only with a fixed seed passed in
    df = _synthetic(n_series=4, years=range(2008, 2025))
    for fit, grid in ((ev.fit_lgbm, ev.M2_GRID[:1]), (ev.fit_rf, ev.M3_GRID[:1])):
        one = run_secondary(df, weather_cols=["x"], context_cols=["ctx"], model=(partial(fit, seed=7), grid))
        two = run_secondary(df, weather_cols=["x"], context_cols=["ctx"], model=(partial(fit, seed=7), grid))
        assert np.allclose(one["pred"], two["pred"])


def test_left_out_rows_are_never_trained_on_or_scored_but_stay_the_last_year_of_b2():
    # Source: E-018 run (a) as the team read it (2026-11-14): FAO-flagged rows are left out of training and scoring
    # only; the normals and B2's last-year lookup stay as in the primary test (one change per sensitivity run)
    df = _synthetic(n_series=6, years=range(2008, 2025))
    df["left_out"] = (df.series_id == "s1") & df.year.isin([2012, 2017])
    p = run_rolling_origin(df, ["x"], ["ctx"], ALPHAS)["predictions"]
    assert not ((p.series_id == "s1") & (p.year == 2017)).any()  # a flagged test row is not scored
    row = p[(p.series_id == "s1") & (p.year == 2018)].iloc[0]
    assert row["b2"] == pytest.approx(df[(df.series_id == "s1") & (df.year == 2017)]["anom"].iloc[0])
    trained = df[(df.series_id == "s1") & (df.year < 2018) & ~df.left_out]
    assert row["b0"] == pytest.approx(trained["anom"].mean())  # B0 is fit without the flagged rows
    assert len(p) == 6 * 9 - 1  # every other series-year of 2016-2024 is scored
