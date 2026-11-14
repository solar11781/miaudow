"""Independent specification tests for fieldshift.data.power (NASA POWER daily point client).

Written without reading the implementation (D-30). Every expectation cites its source.
No test calls the network: fetch_json is always a local fake.
"""

from __future__ import annotations

import datetime as dt
import math
from urllib.parse import parse_qs, urlsplit

import pandas as pd
import pytest

from fieldshift.data.power import (
    BASE_URL,
    DEFAULT_PARAMETERS,
    FILL_VALUE,
    MAX_PARAMETERS,
    PowerRequest,
    fetch_daily,
    parameter_units,
    parse_daily,
)

# Twenty real POWER daily parameter names (external fact: all exist in the POWER AG daily catalogue).
REAL_PARAMS_20 = (
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "T2M_RANGE",
    "T2MDEW",
    "T2MWET",
    "TS",
    "QV2M",
    "RH2M",
    "PRECTOTCORR",
    "PS",
    "WS2M",
    "WS2M_MAX",
    "WS2M_MIN",
    "WS10M",
    "WD2M",
    "ALLSKY_SFC_SW_DWN",
    "CLRSKY_SFC_SW_DWN",
    "ALLSKY_SFC_LW_DWN",
    "GWETROOT",
)


def _payload(values: dict[str, dict[str, float]], units: dict[str, str] | None = None) -> dict:
    """A payload shaped like the real POWER daily point JSON response."""
    units = units or {}
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [105.6, 18.9, 10.0]},
        "properties": {"parameter": values},
        "header": {"title": "NASA/POWER test fixture", "fill_value": -999.0, "start": "20240101", "end": "20240103"},
        "messages": [],
        "parameters": {name: {"units": u, "longname": name} for name, u in units.items()},
        "times": {"data": 0.1, "process": 0.01},
    }


def _req(**kw) -> PowerRequest:
    base = {"lat": 18.9, "lon": 105.6, "start": dt.date(2024, 1, 1), "end": dt.date(2024, 1, 31)}
    base.update(kw)
    return PowerRequest(**base)


# ---------------------------------------------------------------- constants


def test_base_url_is_daily_point_endpoint():
    # Source: docs/DATA-SOURCES.md nasa_power_daily row: https://power.larc.nasa.gov/api/temporal/daily/point
    assert BASE_URL.rstrip("/?") == "https://power.larc.nasa.gov/api/temporal/daily/point"


def test_fill_value_is_minus_999():
    # Source: external fact (verified, DATA-SOURCES nasa_power_daily): POWER fill value -999
    assert FILL_VALUE == -999


def test_max_parameters_is_20():
    # Source: external fact verified against the live API (D-29): max 20 parameters per request
    assert MAX_PARAMETERS == 20


def test_default_parameters_cover_core_weather_and_fit_one_request():
    # Source: 05-DATA-CONTRACTS §4 (precip_sum from PRECTOTCORR, tmax/tmin) + 20-parameter limit (D-29)
    assert {"PRECTOTCORR", "T2M_MAX", "T2M_MIN"} <= set(DEFAULT_PARAMETERS)
    assert 1 <= len(DEFAULT_PARAMETERS) <= 20
    assert len(set(DEFAULT_PARAMETERS)) == len(DEFAULT_PARAMETERS)


# ---------------------------------------------------------------- request validation


def test_valid_request_constructs():
    # Source: interface spec: PowerRequest(lat, lon, start, end, parameters=DEFAULT_PARAMETERS, community="AG")
    r = _req()
    assert r.community == "AG"
    assert tuple(r.parameters) == tuple(DEFAULT_PARAMETERS)


def test_single_day_request_is_valid():
    # Source: external fact: POWER accepts start == end (one-day request); interface: only invalid inputs raise
    _req(start=dt.date(2024, 1, 1), end=dt.date(2024, 1, 1))


@pytest.mark.parametrize("lat", [90.5, 91.0, -91.0, 180.0])
def test_latitude_out_of_range_raises(lat):
    # Source: external fact: latitude is defined only in [-90, 90]; interface: invalid inputs raise ValueError
    with pytest.raises(ValueError, match=r"invalid coordinates"):
        _req(lat=lat)


@pytest.mark.parametrize("lon", [180.5, 181.0, -181.0, 360.0])
def test_longitude_out_of_range_raises(lon):
    # Source: external fact: longitude is defined only in [-180, 180]; interface: invalid inputs raise ValueError
    with pytest.raises(ValueError, match=r"invalid coordinates"):
        _req(lon=lon)


def test_start_after_end_raises():
    # Source: interface spec "invalid inputs raise ValueError"; an empty date range is not a valid request
    with pytest.raises(ValueError, match=r"end date is before start date"):
        _req(start=dt.date(2024, 2, 1), end=dt.date(2024, 1, 1))


def test_exactly_twenty_parameters_allowed():
    # Source: external fact (D-29): the limit is 20 parameters per request, so 20 is allowed
    _req(parameters=REAL_PARAMS_20)


def test_twenty_one_parameters_raise():
    # Source: external fact (D-29): more than 20 parameters per request is rejected by POWER
    with pytest.raises(ValueError, match=r"at most 20 parameters"):
        _req(parameters=(*REAL_PARAMS_20, "GWETTOP"))


def test_empty_parameter_list_raises():
    # Source: external fact: a POWER request needs at least one parameter; interface: invalid inputs raise ValueError
    with pytest.raises(ValueError, match=r"at least one parameter is required"):
        _req(parameters=())


# ---------------------------------------------------------------- url


def _query(url: str) -> dict[str, str]:
    q = parse_qs(urlsplit(url).query)
    return {k.lower(): v[0] for k, v in q.items()}


def test_url_targets_base_url():
    # Source: DATA-SOURCES nasa_power_daily (endpoint)
    url = _req().url()
    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}".rstrip("/") == BASE_URL.rstrip("/?")


def test_url_has_coordinates_dates_and_community():
    # Source: external fact: POWER daily point API query params latitude, longitude, start/end as YYYYMMDD, community
    r = _req(lat=18.9, lon=105.6, start=dt.date(2019, 6, 1), end=dt.date(2019, 6, 30))
    q = _query(r.url())
    assert math.isclose(float(q["latitude"]), 18.9)
    assert math.isclose(float(q["longitude"]), 105.6)
    assert q["start"] == "20190601"
    assert q["end"] == "20190630"
    assert q["community"].upper() == "AG"


def test_url_lists_all_requested_parameters():
    # Source: external fact: POWER takes a comma-separated "parameters" list
    params = ("PRECTOTCORR", "T2M_MAX", "GWETROOT")
    q = _query(_req(parameters=params).url())
    assert set(q["parameters"].split(",")) == set(params)


def test_url_negative_coordinates():
    # Source: external fact: southern/western coordinates are negative decimal degrees in the POWER API
    q = _query(_req(lat=-33.5, lon=-70.25).url())
    assert math.isclose(float(q["latitude"]), -33.5)
    assert math.isclose(float(q["longitude"]), -70.25)


# ---------------------------------------------------------------- cache key


def test_cache_key_deterministic_for_equal_requests():
    # Source: interface spec: results cached on disk; equal requests must hit the same cache entry
    assert _req().cache_key() == _req().cache_key()


@pytest.mark.parametrize(
    "change",
    [
        {"lat": 19.0},
        {"lon": 105.625},
        {"start": dt.date(2024, 1, 2)},
        {"end": dt.date(2024, 2, 29)},
        {"parameters": ("PRECTOTCORR",)},
        {"community": "RE"},
    ],
)
def test_cache_key_changes_with_every_field(change):
    # Source: interface spec: a cached result must never be returned for a different request
    assert _req(**change).cache_key() != _req().cache_key()


# ---------------------------------------------------------------- parse_daily


def test_parse_daily_values_and_dates():
    # Source: external fact: properties.parameter.<NAME>.<YYYYMMDD> holds daily values
    payload = _payload(
        {
            "T2M_MAX": {"20240101": 25.5, "20240102": 26.0, "20240103": 24.25},
            "PRECTOTCORR": {"20240101": 0.0, "20240102": 12.5, "20240103": 3.1},
        }
    )
    df = parse_daily(payload)
    assert set(df.columns) == {"T2M_MAX", "PRECTOTCORR"}
    assert len(df) == 3
    idx = pd.to_datetime(pd.Index(df.index))
    by_date = df.set_axis(idx)
    assert by_date.loc[pd.Timestamp("2024-01-02"), "PRECTOTCORR"] == pytest.approx(12.5)
    assert by_date.loc[pd.Timestamp("2024-01-03"), "T2M_MAX"] == pytest.approx(24.25)
    assert by_date.loc[pd.Timestamp("2024-01-01"), "PRECTOTCORR"] == pytest.approx(0.0)


def test_parse_daily_columns_are_float():
    # Source: interface spec: "one float column per parameter"
    payload = _payload({"RH2M": {"20240101": 80, "20240102": 75}})
    df = parse_daily(payload)
    assert pd.api.types.is_float_dtype(df["RH2M"])


@pytest.mark.parametrize("fill", [-999, -999.0])
def test_parse_daily_fill_value_becomes_missing(fill):
    # Source: external fact (fill value -999) + 05-DATA-CONTRACTS conventions: missing = null, never -999
    payload = _payload({"T2M_MIN": {"20240101": 18.0, "20240102": fill, "20240103": 17.5}})
    df = parse_daily(payload)
    s = df.set_axis(pd.to_datetime(pd.Index(df.index)))["T2M_MIN"]
    assert pd.isna(s.loc[pd.Timestamp("2024-01-02")])
    assert s.loc[pd.Timestamp("2024-01-01")] == pytest.approx(18.0)
    assert not (df == -999).any().any()


def test_parse_daily_leap_day():
    # Source: external fact: calendar dates in YYYYMMDD keys include 29 February in leap years
    payload = _payload({"T2M_MAX": {"20240228": 20.0, "20240229": 21.0, "20240301": 22.0}})
    df = parse_daily(payload)
    idx = pd.to_datetime(pd.Index(df.index))
    assert pd.Timestamp("2024-02-29") in set(idx)


# ---------------------------------------------------------------- parameter_units


def test_parameter_units_from_payload():
    # Source: external fact (POWER JSON format): top-level "parameters": {NAME: {"units": ..., "longname": ...}};
    # units per DATA-SOURCES: PRECTOTCORR mm/day, T2M_MAX C, GWETROOT 0-1 ("1")
    payload = _payload(
        {"PRECTOTCORR": {"20240101": 1.0}, "T2M_MAX": {"20240101": 25.0}, "GWETROOT": {"20240101": 0.5}},
        units={"PRECTOTCORR": "mm/day", "T2M_MAX": "C", "GWETROOT": "1"},
    )
    assert parameter_units(payload) == {"PRECTOTCORR": "mm/day", "T2M_MAX": "C", "GWETROOT": "1"}


# ---------------------------------------------------------------- fetch_daily + cache


class _FakeFetch:
    def __init__(self, payload: dict):
        self.payload = payload
        self.urls: list[str] = []

    def __call__(self, url: str) -> dict:
        self.urls.append(url)
        return self.payload


def _never(url: str) -> dict:
    raise AssertionError(f"network fetch attempted for cached request: {url}")


def _sample_payload() -> dict:
    return _payload(
        {"PRECTOTCORR": {"20240101": 1.5, "20240102": -999.0}, "T2M_MAX": {"20240101": 25.0, "20240102": 26.0}},
        units={"PRECTOTCORR": "mm/day", "T2M_MAX": "C"},
    )


def test_fetch_daily_calls_fetcher_with_request_url(tmp_path):
    # Source: interface spec: fetch_daily(request, cache_dir, fetch_json: Callable[[str], dict])
    r = _req(parameters=("PRECTOTCORR", "T2M_MAX"))
    fake = _FakeFetch(_sample_payload())
    df, payload = fetch_daily(r, tmp_path, fake)
    assert fake.urls == [r.url()]
    assert payload == _sample_payload()
    pd.testing.assert_frame_equal(df, parse_daily(_sample_payload()))


def test_fetch_daily_writes_cache_on_disk(tmp_path):
    # Source: interface spec: "results must be cached on disk under cache_dir"
    r = _req(parameters=("PRECTOTCORR", "T2M_MAX"))
    fetch_daily(r, tmp_path, _FakeFetch(_sample_payload()))
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert files, "no cache file written under cache_dir"


def test_fetch_daily_second_call_uses_cache_not_network(tmp_path):
    # Source: interface spec (cache) + NFR-01/M3c: cached POWER data is reused without re-downloading
    r = _req(parameters=("PRECTOTCORR", "T2M_MAX"))
    df1, p1 = fetch_daily(r, tmp_path, _FakeFetch(_sample_payload()))
    df2, p2 = fetch_daily(_req(parameters=("PRECTOTCORR", "T2M_MAX")), tmp_path, _never)
    assert p2 == p1
    pd.testing.assert_frame_equal(df1, df2)


def test_fetch_daily_cache_keeps_missing_values(tmp_path):
    # Source: external fact (fill -999) + contract "missing = null": a cache round trip must not resurrect -999
    r = _req(parameters=("PRECTOTCORR", "T2M_MAX"))
    fetch_daily(r, tmp_path, _FakeFetch(_sample_payload()))
    df, _ = fetch_daily(r, tmp_path, _never)
    s = df.set_axis(pd.to_datetime(pd.Index(df.index)))["PRECTOTCORR"]
    assert pd.isna(s.loc[pd.Timestamp("2024-01-02")])


def test_fetch_daily_different_request_is_fetched(tmp_path):
    # Source: interface spec: cache entries are per request; a different point must not reuse another point's data
    r1 = _req(lat=18.9, parameters=("PRECTOTCORR", "T2M_MAX"))
    r2 = _req(lat=19.4, parameters=("PRECTOTCORR", "T2M_MAX"))
    fetch_daily(r1, tmp_path, _FakeFetch(_sample_payload()))
    fake2 = _FakeFetch(_sample_payload())
    fetch_daily(r2, tmp_path, fake2)
    assert fake2.urls == [r2.url()]
