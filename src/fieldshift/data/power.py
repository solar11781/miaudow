"""NASA POWER daily point client with an on-disk cache.

What this is for (plain words): NASA POWER returns daily weather (rain, temperature, humidity, wind,
sunshine, modeled root-zone soil wetness) for one latitude/longitude. We need about 30 years of it for a
few points in every province, so every response is cached on disk and never downloaded twice. That keeps
the pipeline reproducible and polite to the API, and lets it run offline after the first download.

API reference: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
Verified 2026-11-10: community AG, JSON format, fill value -999, radiation available from 1984-01-01.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from http import HTTPStatus
from pathlib import Path

import numpy as np
import pandas as pd

BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FILL_VALUE = -999.0
MAX_LAT, MAX_LON = 90.0, 180.0  # limits of geographic latitude and longitude in degrees
MAX_PARAMETERS = 20  # POWER point requests accept at most 20 parameters

# Parameters used by the feature pipeline (see docs/05-DATA-CONTRACTS.md section 4).
DEFAULT_PARAMETERS = (
    "PRECTOTCORR",  # precipitation, mm/day
    "T2M_MAX",  # daily max air temperature at 2 m, C
    "T2M_MIN",  # daily min air temperature at 2 m, C
    "RH2M",  # relative humidity at 2 m, %
    "WS2M",  # wind speed at 2 m, m/s
    "ALLSKY_SFC_SW_DWN",  # incoming solar radiation at the surface (unit reported by the API)
    "GWETROOT",  # modeled root-zone soil wetness, 0-1 (MERRA-2)
)

FetchJson = Callable[[str], dict]


@dataclass(frozen=True)
class PowerRequest:
    lat: float
    lon: float
    start: date
    end: date
    parameters: tuple[str, ...] = DEFAULT_PARAMETERS
    community: str = "AG"

    def __post_init__(self) -> None:
        if not -MAX_LAT <= self.lat <= MAX_LAT or not -MAX_LON <= self.lon <= MAX_LON:
            raise ValueError(f"invalid coordinates: {self.lat}, {self.lon}")
        if self.end < self.start:
            raise ValueError("end date is before start date")
        if not self.parameters:
            raise ValueError("at least one parameter is required")
        if len(self.parameters) > MAX_PARAMETERS:
            raise ValueError(f"POWER accepts at most {MAX_PARAMETERS} parameters per request")

    def url(self) -> str:
        query = {
            "parameters": ",".join(self.parameters),
            "community": self.community,
            "latitude": f"{self.lat:.4f}",
            "longitude": f"{self.lon:.4f}",
            "start": self.start.strftime("%Y%m%d"),
            "end": self.end.strftime("%Y%m%d"),
            "format": "JSON",
        }
        return f"{BASE_URL}?{urllib.parse.urlencode(query, safe=',')}"

    def cache_key(self) -> str:
        digest = hashlib.sha256(self.url().encode()).hexdigest()[:12]
        return f"power_{self.lat:.4f}_{self.lon:.4f}_{self.start:%Y%m%d}_{self.end:%Y%m%d}_{digest}.json"


def _http_fetch_json(url: str, retries: int = 4, timeout: float = 120.0) -> dict:
    """GET a URL and decode JSON, retrying transient failures with exponential backoff (2, 4, 8, 16 s)."""
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError(f"only https URLs are allowed, got {url!r}")
    delay = 2.0
    for attempt in range(retries + 1):
        try:
            with urllib.request.build_opener().open(url, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as err:
            transient = err.code == HTTPStatus.TOO_MANY_REQUESTS or err.code >= HTTPStatus.INTERNAL_SERVER_ERROR
            if not transient or attempt == retries:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries:
                raise
        time.sleep(delay)
        delay *= 2
    raise RuntimeError("unreachable")


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


def fetch_daily(
    request: PowerRequest,
    cache_dir: Path | str = Path("data/raw/power"),
    fetch_json: FetchJson = _http_fetch_json,
) -> tuple[pd.DataFrame, dict]:
    """Return (daily DataFrame, raw payload) for a request, using the on-disk cache when present.

    The raw payload is cached unchanged (including its header and messages) so provenance is preserved.
    """
    cache_dir = Path(cache_dir)
    cache_file = cache_dir / request.cache_key()
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        payload = fetch_json(request.url())
        parse_daily(payload)  # validate before caching, so a bad response is never stored
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = cache_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        tmp.replace(cache_file)
    return parse_daily(payload), payload


POWER_CACHE_FILES = "power_*_19900101_20241231_*.json"  # the cached 1990-2024 daily series per cell


def load_cells(main_dir: Path | str, t2m_dir: Path | str, pattern: str) -> tuple[dict, list]:
    """Cached POWER cells {(lat, lon): daily frame}, with daily mean T2M joined from its own cache (D-72).

    Returns the cells and the T2M cells that have no main cell (reported by the caller, not used).
    """
    cells: dict = {}
    for f in sorted(Path(main_dir).glob(pattern)):
        payload = json.loads(f.read_text(encoding="utf-8"))
        lon, lat = payload["geometry"]["coordinates"][:2]
        cells[(round(lat, 6), round(lon, 6))] = parse_daily(payload)
    unmatched = []
    for f in sorted(Path(t2m_dir).glob(pattern)):
        payload = json.loads(f.read_text(encoding="utf-8"))
        lon, lat = payload["geometry"]["coordinates"][:2]
        key = (round(lat, 6), round(lon, 6))
        if key in cells:
            cells[key] = cells[key].join(parse_daily(payload)[["T2M"]], how="left")
        else:
            unmatched.append(key)
    return cells, unmatched
