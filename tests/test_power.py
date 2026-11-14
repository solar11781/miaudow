import os
from datetime import date

import numpy as np
import pytest

from fieldshift.data.power import (
    PowerRequest,
    fetch_daily,
    parameter_units,
    parse_daily,
)

# Shape copied from a real response (2026-11-10, lat 18.9 lon 105.6), values shortened.
SAMPLE = {
    "type": "Feature",
    "properties": {
        "parameter": {
            "PRECTOTCORR": {"19950102": 4.12, "19950101": 3.98, "19950103": -999.0},
            "T2M_MAX": {"19950101": 22.36, "19950102": 19.6, "19950103": 21.0},
        }
    },
    "parameters": {
        "PRECTOTCORR": {"units": "mm/day", "longname": "Precipitation Corrected"},
        "T2M_MAX": {"units": "C", "longname": "Temperature at 2 Meters Maximum"},
    },
    "messages": [],
}

REQ = PowerRequest(
    lat=18.9, lon=105.6, start=date(1995, 1, 1), end=date(1995, 1, 3), parameters=("PRECTOTCORR", "T2M_MAX")
)


def test_parse_daily_sorts_dates_and_masks_fill_values():
    df = parse_daily(SAMPLE)
    assert list(df.columns) == ["PRECTOTCORR", "T2M_MAX"]
    assert df.index.is_monotonic_increasing
    assert str(df.index[0].date()) == "1995-01-01"
    assert df.loc["1995-01-01", "PRECTOTCORR"] == pytest.approx(3.98)
    assert np.isnan(df.loc["1995-01-03", "PRECTOTCORR"])  # -999 must never look like real rain


def test_parse_daily_rejects_error_payload():
    with pytest.raises(ValueError, match=r"missing 'properties'"):
        parse_daily({"messages": ["bad request"]})


def test_units_are_extracted():
    assert parameter_units(SAMPLE) == {"PRECTOTCORR": "mm/day", "T2M_MAX": "C"}


def test_url_contains_expected_query():
    url = REQ.url()
    assert "parameters=PRECTOTCORR,T2M_MAX" in url
    assert "start=19950101" in url
    assert "end=19950103" in url
    assert "community=AG" in url
    assert "format=JSON" in url


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"lat": 95, "lon": 105}, "invalid coordinates"),
        ({"lat": 18, "lon": 105, "start": date(2000, 1, 2), "end": date(2000, 1, 1)}, "end date is before start date"),
        ({"lat": 18, "lon": 105, "parameters": ()}, "at least one parameter is required"),
        ({"lat": 18, "lon": 105, "parameters": tuple(f"P{i}" for i in range(21))}, "at most 20 parameters"),
    ],
)
def test_invalid_requests_are_rejected(kwargs, message):
    base = {"start": date(2000, 1, 1), "end": date(2000, 1, 2)}
    with pytest.raises(ValueError, match=message):
        PowerRequest(**{**base, **kwargs})


def test_cache_prevents_second_download(tmp_path):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return SAMPLE

    df1, _ = fetch_daily(REQ, cache_dir=tmp_path, fetch_json=fake_fetch)
    df2, _ = fetch_daily(REQ, cache_dir=tmp_path, fetch_json=fake_fetch)
    assert len(calls) == 1
    assert df1.equals(df2)


def test_bad_response_is_not_cached(tmp_path):
    with pytest.raises(ValueError, match=r"missing 'properties'"):
        fetch_daily(REQ, cache_dir=tmp_path, fetch_json=lambda url: {"messages": ["error"]})
    assert not any(tmp_path.iterdir())


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("FIELDSHIFT_LIVE") != "1", reason="set FIELDSHIFT_LIVE=1 to call the real API")
def test_live_power_request(tmp_path):
    df, payload = fetch_daily(REQ, cache_dir=tmp_path)
    assert len(df) == 3
    assert parameter_units(payload)["PRECTOTCORR"] == "mm/day"
