"""Climate ML of AI core 01: baseline-only standardisation, no leakage in leave-one-year-out, determinism, the
honest evaluation verdict and the stored evaluation file."""

import copy
import json

import numpy as np
import pytest

from miaudow_api import canonical, climate_ml
from miaudow_api.climate import ClimateInputError


@pytest.fixture(scope="module")
def clim() -> dict:
    return copy.deepcopy(canonical.load("climate.json"))


def _with(clim: dict, year: int, **changes) -> dict:
    out = copy.deepcopy(clim)
    out["series"]["farmland_weighted"][str(year)].update(changes)
    return out


def test_zscale_uses_the_baseline_years_only(clim):
    base = climate_ml.load_table(clim)
    x = climate_ml.features_from(base.anomaly_pct, base.hot, base.dry)
    mean, std = climate_ml.zscale(x, climate_ml.baseline_mask(base.years))
    # a wild value in a year after the baseline must not move the scale
    t2 = climate_ml.load_table(_with(clim, 2024, hot_days=999.0, longest_dry_spell_days=300.0))
    x2 = climate_ml.features_from(t2.anomaly_pct, t2.hot, t2.dry)
    mean2, std2 = climate_ml.zscale(x2, climate_ml.baseline_mask(t2.years))
    assert np.allclose(mean, mean2) and np.allclose(std, std2)
    # the same change inside the baseline does move it (the test above is not vacuous)
    t3 = climate_ml.load_table(_with(clim, 2000, hot_days=999.0))
    x3 = climate_ml.features_from(t3.anomaly_pct, t3.hot, t3.dry)
    mean3, _ = climate_ml.zscale(x3, climate_ml.baseline_mask(t3.years))
    assert not np.allclose(mean, mean3)


def test_baseline_mask_and_exclusion():
    years = np.arange(1991, 2025)
    m = climate_ml.baseline_mask(years)
    assert m.sum() == 30 and years[m].min() == 1991 and years[m].max() == 2020
    assert climate_ml.baseline_mask(years, exclude=2010).sum() == 29


def test_leave_one_out_refits_without_the_held_out_year(clim):
    """Changing the held-out year's own rain must not change the normal, scale or thresholds used for it."""
    t = climate_ml.load_table(clim)
    i = int(np.flatnonzero(t.years == 2010)[0])
    case = climate_ml._loo_case(t, i, slice(0, 12), slice(0, 12), extra=True)
    wet = climate_ml.load_table(
        _with(
            clim, 2010, monthly_rain_mm=[v * 3 for v in clim["series"]["farmland_weighted"]["2010"]["monthly_rain_mm"]]
        )
    )
    case_wet = climate_ml._loo_case(wet, i, slice(0, 12), slice(0, 12), extra=True)
    assert case["tercile_thresholds_pct"] == case_wet["tercile_thresholds_pct"]
    # a change to another baseline year does change them
    other = climate_ml.load_table(
        _with(
            clim, 2000, monthly_rain_mm=[v * 3 for v in clim["series"]["farmland_weighted"]["2000"]["monthly_rain_mm"]]
        )
    )
    assert (
        climate_ml._loo_case(other, i, slice(0, 12), slice(0, 12), extra=True)["tercile_thresholds_pct"]
        != (case["tercile_thresholds_pct"])
    )
    assert case["analog"] != 2010


def test_analog_search_is_deterministic_and_well_formed():
    a = climate_ml.analog_search(2010, 3)
    b = climate_ml.analog_search(2010, 3)
    assert a.model_dump() == b.model_dump()
    assert [x.order for x in a.analogs] == [1, 2, 3]
    assert 2010 not in [x.year for x in a.analogs]
    d = [x.distance for x in a.analogs]
    assert d == sorted(d)
    assert len(a.features) == 14
    for x in a.analogs:
        assert 1 <= len(x.drivers) <= 3
        shares = [dr.share_of_distance for dr in x.drivers]
        assert shares == sorted(shares, reverse=True) and all(0 <= s <= 1 for s in shares)
        assert x.distance_unit.startswith("standard deviations")
    assert a.provenance.is_forecast is False and a.provenance.is_field_measurement is False
    assert a.baseline.start.year == 1991 and a.baseline.end.year == 2020
    assert a.median_pairwise_distance > 0


def test_analog_input_errors():
    with pytest.raises(ClimateInputError):
        climate_ml.analog_search(1980, 3)
    with pytest.raises(ClimateInputError):
        climate_ml.analog_search(2010, 0)
    with pytest.raises(ClimateInputError):
        climate_ml.analog_search(2010, 11)


def test_nearest_skips_years_with_a_missing_feature():
    z = np.array([[0.0, 0.0], [1.0, 1.0], [np.nan, 0.1], [0.2, 0.2]])
    years = np.array([2000, 2001, 2002, 2003])
    ranked = climate_ml.nearest(z, 0, np.ones(4, dtype=bool), years)
    assert [years[r] for r, _ in ranked] == [2003, 2001]


def test_mcnemar_exact():
    assert climate_ml.mcnemar_exact([True] * 5 + [False] * 5, [False] * 5 + [True] * 5) == 1.0
    assert climate_ml.mcnemar_exact([True] * 6, [False] * 6) == pytest.approx(0.0312, abs=1e-4)
    assert climate_ml.mcnemar_exact([True, False], [True, False]) == 1.0


def test_leave_one_out_evaluation_is_reproducible_and_reports_real_rates():
    a = climate_ml.evaluate_analogs()
    b = climate_ml.evaluate_analogs()
    assert a == b
    p = a["proxy_task"]
    assert p["n_cases"] == 33 and p["years_evaluated"][0] == 1992 and p["years_evaluated"][-1] == 2024
    for key, rate in p["hit_rates"].items():
        assert rate == round(p["hits"][key] / p["n_cases"], 3)
    assert set(a["out_of_sample_check"]["hit_rates"]) == set(p["hit_rates"])


def test_verdict_says_so_when_the_method_loses():
    main = {
        "hit_rates": {"analog_k1_tercile": 0.2, "climatology_tercile": 0.3, "persistence_tercile": 0.4},
        "beats_both_baselines_tercile": False,
        "difference_significant_p05": False,
    }
    oos = {"hit_rates": {"analog_k1_tercile": 0.3, "climatology_tercile": 0.3, "persistence_tercile": 0.4}}
    v = climate_ml._verdict(main, oos)
    assert "NOT" in v.en and "KHÔNG" in v.vi
    summary = climate_ml.analog_evaluation_summary()
    assert summary.beats_baselines == (
        summary.scores["proxy_analog_k1_tercile"]
        > max(summary.scores["proxy_persistence_tercile"], summary.scores["proxy_climatology_tercile"])
    )


def test_robust_score_flags_a_planted_extreme_month_and_never_scores_missing_months():
    rng = np.random.default_rng(0)
    years = np.arange(1991, 2025)
    rain = rng.uniform(50, 150, size=(len(years), 12))
    rain[years == 2022, 7] = 5000.0  # an extreme August after the baseline
    rain[years == 2023, 2] = np.nan  # a missing month
    det = climate_ml.detect(rain, years)
    flagged = years[det["flagged"]].tolist()
    assert 2022 in flagged
    assert np.isnan(det["scores"][years == 2023][0]) and 2023 not in flagged
    # the threshold comes from the baseline scores only: changing 2022 again does not move it
    rain2 = rain.copy()
    rain2[years == 2022, 7] = 9000.0
    assert climate_ml.detect(rain2, years)["threshold"] == det["threshold"]


def test_anomaly_years_and_percentile_baseline():
    res = climate_ml.anomaly_years()
    assert len(res.years) == 34
    base = [y for y in res.years if y.in_baseline]
    assert len(base) == 30
    p10, p90 = res.percentile_bounds_mm
    for y in res.years:
        if y.percentile_flag == "below_p10":
            assert y.annual_rain_mm < p10
        if y.percentile_flag == "above_p90":
            assert y.annual_rain_mm > p90
        assert y.flagged == (y.score is not None and y.score > res.threshold)
        if y.flagged:
            assert y.driving_months and abs(y.driving_months[0].robust_z) == pytest.approx(y.score, abs=0.01)
    g = res.agreement
    assert g["both"] + g["ml_only"] + g["baseline_only"] + g["neither"] == 34
    assert res.evaluation.beats_baselines is False  # agreement, not accuracy: never claimed as a win


def test_annual_anomaly_matches_the_climate_history():
    from miaudow_api import climate_series

    hist = climate_series.history("farmland_weighted", 2009, 2009)
    pct = next(s for s in hist.series if s.quantity == "annual_rain_anomaly_pct_power").values[0]
    y2009 = next(y for y in climate_ml.anomaly_years().years if y.year == 2009)
    assert y2009.annual_rain_anomaly_pct == pct


def test_stored_evaluation_equals_a_fresh_run():
    stored = climate_ml.stored_evaluation()
    assert stored is not None, f"run {climate_ml.EVAL_COMMAND}"
    fresh = json.loads(json.dumps(climate_ml.full_evaluation()))
    assert stored["model"]["metrics"] == fresh["model"]["metrics"]
    assert stored["analogs"]["proxy_task"]["hit_rates"] == fresh["analogs"]["proxy_task"]["hit_rates"]
    assert stored["model"]["version"] == climate_ml.MODEL_VERSION
    assert stored["model"]["training_years"]["baseline"] == [1991, 2020]
    assert stored["model"]["failure_cases"]["analog_category_mismatches"]
