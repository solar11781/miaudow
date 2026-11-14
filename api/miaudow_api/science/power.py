"""Read the cached NASA POWER daily files (data/raw/power, data/raw/power_t2m) into daily tables.

Plain words: NASA POWER gives one value per day for one grid cell. These values come from a model fitted to satellite
and station data (MERRA-2 reanalysis); they are never a measurement on a farm. The fill value -999 means "no value"
and becomes NaN, never 0, so a missing day can never look like a dry day.

`parse_daily` and `parameter_units` are ported from the Miaudow repository src/fieldshift/data/power.py (Apache-2.0,
Copyright 2026 the Miaudow contributors). The loader below reads the cache by the coordinates written inside each file,
so it does not depend on the cache file name.
"""

from __future__ import annotations

import calendar
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

FILL_VALUE = -999.0
CACHE_PATTERN = "power_*_19900101_20241231_*.json"  # the cached 1990-2024 daily series per cell
SOURCE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


def parse_daily(payload: dict) -> pd.DataFrame:
    """Turn a POWER daily JSON payload into a DataFrame indexed by date, one column per parameter.

    Fill values (-999) become NaN so that missing data can never be mistaken for a real measurement.
    """
    try:
        params = payload["properties"]["parameter"]
    except KeyError as err:
        raise ValueError(f"unexpected POWER payload, missing {err}; messages: {payload.get('messages')}") from err
    frame = pd.DataFrame({name: pd.Series(values, dtype="float64") for name, values in params.items()})
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d")
    frame.index.name = "date"
    frame = frame.sort_index().replace(FILL_VALUE, np.nan)
    return frame


def parameter_units(payload: dict) -> dict[str, str]:
    """Units as reported by the API, e.g. {'PRECTOTCORR': 'mm/day'}. Stored alongside features for provenance."""
    return {name: meta.get("units", "") for name, meta in payload.get("parameters", {}).items()}


@dataclass(frozen=True)
class CachedCell:
    lat: float
    lon: float
    frame: pd.DataFrame
    files: tuple[Path, ...]
    api_version: str | None
    sources: tuple[str, ...]
    units: dict


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _key(payload: dict) -> tuple[float, float]:
    lon, lat = payload["geometry"]["coordinates"][:2]
    return round(float(lat), 6), round(float(lon), 6)


def load_cached_cells(
    main_dir: Path, t2m_dir: Path, pattern: str = CACHE_PATTERN
) -> dict[tuple[float, float], CachedCell]:
    """Cached POWER cells {(lat, lon): CachedCell}; daily mean T2M is joined from its own cache (inner join on dates).

    Raises when a T2M file has no main file or a main file has no T2M file: no cell is used half-loaded.
    """
    main = {}
    for f in sorted(Path(main_dir).glob(pattern)):
        payload = _read(f)
        main[_key(payload)] = (f, payload)
    t2m = {}
    for f in sorted(Path(t2m_dir).glob(pattern)):
        payload = _read(f)
        t2m[_key(payload)] = (f, payload)
    if not main:
        raise FileNotFoundError(f"no cached POWER files matching {pattern} in {main_dir}")
    if set(main) != set(t2m):
        raise ValueError(
            f"POWER caches do not pair up: main only {sorted(set(main) - set(t2m))}, "
            f"T2M only {sorted(set(t2m) - set(main))}"
        )
    cells = {}
    for key, (f, payload) in main.items():
        tf, tpayload = t2m[key]
        frame = parse_daily(payload).join(parse_daily(tpayload)[["T2M"]], how="inner")
        header = payload.get("header", {})
        cells[key] = CachedCell(
            lat=key[0],
            lon=key[1],
            frame=frame,
            files=(f, tf),
            api_version=(header.get("api") or {}).get("version"),
            sources=tuple(header.get("sources", [])),
            units={**parameter_units(payload), **parameter_units(tpayload)},
        )
    return cells


def sha256_of_files(files: list[Path]) -> str:
    """One digest over the sorted files' bytes, so the catalog can say which exact cache was used."""
    digest = hashlib.sha256()
    for f in sorted(files, key=lambda p: p.name):
        digest.update(f.name.encode())
        digest.update(f.read_bytes())
    return digest.hexdigest()


def days_in_month(year: int, month: int) -> int:
    """Calendar days of a month; February has 29 days in leap years (1992, 1996, ..., 2024)."""
    return calendar.monthrange(year, month)[1]


def check_calendar(index: pd.DatetimeIndex, first_year: int, last_year: int) -> list[str]:
    """Problems with the daily index between 1 January of first_year and 31 December of last_year.

    Returns a list of messages (empty when every calendar day is present exactly once, leap days included).
    """
    problems = []
    if index.has_duplicates:
        problems.append(f"{int(index.duplicated().sum())} duplicated days")
    for year in range(first_year, last_year + 1):
        n = int((index.year == year).sum())
        expected = 366 if calendar.isleap(year) else 365
        if n != expected:
            problems.append(f"{year}: {n} days, expected {expected}")
        if calendar.isleap(year) and pd.Timestamp(year, 2, 29) not in index:
            problems.append(f"{year}: 29 February missing")
    return problems
