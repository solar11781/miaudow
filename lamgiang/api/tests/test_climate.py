"""Core 01: the starter's NASA POWER tests (moved here) and the canonical climate records."""

import asyncio
import json

import httpx
import numpy as np
import pandas as pd
import pytest

from miaudow_api import canonical, climate
from miaudow_api.paths import RAW
from miaudow_api.science import power


def test_power_missing_sentinel_is_null():
    assert climate.valid_value(-999.0) is None
    assert climate.valid_value(None) is None
    assert climate.valid_value("x") is None
    assert climate.valid_value(0.0) == 0.0


def test_no_invented_months():
    months = climate.monthly_aggregation({"PRECTOTCORR": {"20240101": 12}, "T2M_MAX": {"20240101": 31}}, 2024)
    assert len(months) == 12
    assert months[0]["precipitation_mm"] is None
    assert months[0]["temp_max_c"] is None
    assert months[1]["precipitation_mm"] is None


def test_full_month_exact_aggregation():
    r = {f"202402{i:02}": 2 for i in range(1, 30)}
    t = {f"202402{i:02}": 30 + i / 10 for i in range(1, 30)}
    row = climate.monthly_aggregation({"PRECTOTCORR": r, "T2M_MAX": t}, 2024)[1]
    assert row["precipitation_mm"] == 58.0
    assert row["day_count"] == 29
    assert row["temp_max_c"] == 31.5


def test_february_of_a_non_leap_year_needs_28_days_only():
    r = {f"202302{i:02}": 1 for i in range(1, 29)}
    row = climate.monthly_aggregation({"PRECTOTCORR": r, "T2M_MAX": r}, 2023)[1]
    assert row["precipitation_mm"] == 28.0


def test_parse_daily_turns_fill_values_into_nan_never_zero():
    payload = {"properties": {"parameter": {"PRECTOTCORR": {"19950102": 4.1, "19950101": 3.9, "19950103": -999.0}}}}
    df = power.parse_daily(payload)
    assert df.index.is_monotonic_increasing
    assert np.isnan(df.loc["1995-01-03", "PRECTOTCORR"])
    with pytest.raises(ValueError, match="missing 'properties'"):
        power.parse_daily({"messages": ["bad request"]})


def test_calendar_check_counts_leap_days():
    full = pd.date_range("1991-01-01", "1992-12-31", freq="D")
    assert power.check_calendar(full, 1991, 1992) == []
    assert power.days_in_month(1996, 2) == 29
    assert power.days_in_month(2100, 2) == 28


def test_cached_power_cells_load_with_t2m_joined():
    cells = power.load_cached_cells(RAW / "power", RAW / "power_t2m")
    assert len(cells) == 5
    one = next(iter(cells.values()))
    assert {"PRECTOTCORR", "T2M_MAX", "T2M", "GWETROOT"} <= set(one.frame.columns)
    assert pd.Timestamp("2024-02-29") in one.frame.index


def test_year_summary_records_carry_provenance_and_are_never_forecasts():
    recs = climate.year_summary(2024)
    annual = next(r for r in recs if r.metric_id == "annual_rain_total")
    data = canonical.load("climate.json")
    assert annual.value == data["series"]["farmland_weighted"]["2024"]["annual_rain_mm"]
    assert annual.dataset_id == "nasa_power_daily"
    assert annual.source_id == "R-N01"
    assert annual.geometry.type == "farmland_weighted_area"
    for r in recs:
        assert r.is_forecast is False
        assert r.is_field_measurement is False
        assert r.method_id
        assert r.transformation_id
    assert {r.metric_id for r in recs} >= {
        "hot_days",
        "cold_days",
        "longest_dry_spell",
        "drought_rain_months",
        "hazard_share_heat",
    }


def test_monthly_records_for_one_cell_include_normal_and_anomaly():
    recs = climate.monthly(2020, "19.0_105.625")
    totals = [r for r in recs if r.metric_id == "monthly_rain_total"]
    assert len(totals) == 12
    assert totals[1].time_window.end.day == 29  # February 2020
    assert totals[0].geometry.type == "grid_cell"
    assert any(r.metric_id == "monthly_rain_anomaly_pct" for r in recs)


def test_unknown_cell_or_year_is_rejected():
    with pytest.raises(climate.ClimateInputError):
        climate.monthly(2020, "nowhere")
    with pytest.raises(climate.ClimateInputError):
        climate.year_summary(1980)


def test_hazard_shares_accept_both_crop_key_styles():
    a = climate.hazard_shares(2010, "cc2_spring_chili")
    b = climate.hazard_shares(2010, "cc2_chili")
    assert [r.value for r in a] == [r.value for r in b]
    hz = canonical.load("hazards.json")
    assert a[1].value == hz["crop_level"]["cc2_chili"]["heat"][2010 - 1995]


def test_soil_wetness_matches_soil_json():
    recs = climate.soil_wetness(2005, "usual_spring_rice")
    soil = canonical.load("soil.json")
    assert recs[0].value == soil["crops"]["cc5_rice"]["values"][10]
    assert recs[1].value == soil["crops"]["cc5_rice"]["normal_1991_2020"]


def test_live_power_aggregates_complete_months_only():
    days = pd.date_range("2023-01-01", "2023-12-31", freq="D")
    rain = {d.strftime("%Y%m%d"): 1.0 for d in days}
    rain["20230315"] = -999.0
    payload = {"properties": {"parameter": {"PRECTOTCORR": rain, "T2M_MAX": dict.fromkeys(rain, 30.0)}}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["community"] == "AG"
        return httpx.Response(200, content=json.dumps(payload))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await climate.live_power(19.0, 105.6, 2023, client=client)

    out = asyncio.run(run())
    assert out["months"][2]["precipitation_mm"] is None  # March has a fill value
    assert out["months"][0]["precipitation_mm"] == 31.0
    assert out["is_field_measurement"] is False


def test_live_power_failure_is_not_replaced_by_data():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await climate.live_power(19.0, 105.6, 2023, client=client)

    with pytest.raises(climate.PowerUnavailable):
        asyncio.run(run())
