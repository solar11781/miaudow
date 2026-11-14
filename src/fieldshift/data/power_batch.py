"""Download NASA POWER daily data for many cells, politely and with a failure report (D-26, D-36).

One request per POWER cell at the cell centre; responses are cached by fetch_daily (raw JSON kept for provenance);
cached cells are not requested again; failures are returned in the report, never skipped silently or filled.
Each report row names its file and request URL, so the caller can write the data/MANIFEST.csv row (manifest_row).
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from fieldshift.data.power import DEFAULT_PARAMETERS, PowerRequest, _http_fetch_json, fetch_daily

PAUSE_S = 1.0  # routine pacing after each new request; not a documented POWER limit


def download_cells(
    cells,
    period: tuple[date, date],
    cache_dir: Path | str,
    fetch_json: Callable[[str], dict] = _http_fetch_json,
    sleep: Callable[[float], None] = time.sleep,
    parameters: tuple[str, ...] = DEFAULT_PARAMETERS,
) -> list[dict]:
    """Return one report dict per cell: cell_lat, cell_lon, status ('ok' or 'failed'), days, error, cached, path, url.

    period is the (first day, last day) of the request.
    """
    start, end = period
    cache_dir = Path(cache_dir)
    report = []
    for lat, lon in cells:
        req = PowerRequest(lat=lat, lon=lon, start=start, end=end, parameters=parameters)
        path = cache_dir / req.cache_key()
        cached = path.exists()
        where = {"path": str(path), "url": req.url()}
        try:
            df, _ = fetch_daily(req, cache_dir=cache_dir, fetch_json=fetch_json)
            report.append(dict(cell_lat=lat, cell_lon=lon, status="ok", days=len(df), error="", cached=cached, **where))
        except Exception as err:  # recorded and reported; the batch continues
            report.append(
                dict(cell_lat=lat, cell_lon=lon, status="failed", days=0, error=repr(err), cached=cached, **where)
            )
        if not cached:
            sleep(PAUSE_S)
    return report


def manifest_row(report_row: dict, source_id: str, retrieved_on: str, method: str) -> list[str]:
    """data/MANIFEST.csv row for one downloaded file: path, source_id, table, title, url, retrieved_on, method, sha256."""
    digest = hashlib.sha256(Path(report_row["path"]).read_bytes()).hexdigest()
    title = f"NASA POWER daily point {report_row['cell_lat']:.4f} N {report_row['cell_lon']:.4f} E"
    return [report_row["path"], source_id, "", title, report_row["url"], retrieved_on, method, digest]
