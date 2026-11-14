"""Fetch CHIRPS v3.0 monthly rainfall for the 5 farmland-weighted NASA POWER cells of Nghệ An and the study site.

Source: Climate Hazards Center, UC Santa Barbara, CHIRPS v3.0 final monthly global Cloud-Optimized GeoTIFFs
        https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs/
Access: HTTP range requests through GDAL /vsicurl/ (rasterio); only the one 512x512 tile that covers the study
        window is read from each ~29 MiB global file. The small window arrays are cached in data/cache/chirps_v3/
        (git-ignored) so a rerun resumes where it stopped.

Per POWER cell (centre lat, lon; footprint lat +/- 0.25 deg, lon +/- 0.3125 deg) the monthly value is the mean of all
CHIRPS 0.05 deg pixels whose centres fall inside the footprint AND inside the Nghệ An ADM1 polygon
(geoBoundaries, simplified). Missing pixels (CHIRPS -9999 or any negative / non-finite value) are never filled:
they are counted in n_missing and left out of the mean; a month with no valid pixel has an empty precip_mm.

Run:   .venv\\Scripts\\python.exe pipeline\\fetch_chirps_v3.py            (fetch + build CSV + manifest)
       .venv\\Scripts\\python.exe pipeline\\fetch_chirps_v3.py --no-fetch (rebuild from cache only)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs/"
README_URL = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/README-CHIRPSv3.0.txt"
USER_AGENT = "MiaudowResearch/1.0 (NASA Space Apps 2026 hackathon)"
YEARS = range(1991, 2025)
CACHE_DIR = ROOT / "data" / "cache" / "chirps_v3"
OUT_DIR = ROOT / "data" / "raw" / "chirps_v3"
OUT_CSV = OUT_DIR / "chirps_v3_monthly_nghe_an.csv"
MANIFEST = OUT_DIR / "MANIFEST.json"
CELLS_CSV = ROOT / "data" / "reference" / "cell_weights_nghe_an.csv"
BOUNDARY = ROOT / "data" / "raw" / "boundaries" / "geoBoundaries-VNM-ADM1_simplified.geojson"
POWER_DIR = ROOT / "data" / "raw" / "power"

HALF_LAT = 0.25  # POWER grid is 0.5 deg lat x 0.625 deg lon
HALF_LON = 0.3125
# Study site: Lưu Sơn commune (Đô Lương district before the 2025 merger), Wikidata Q10788283, P625
# (value imported from Vietnamese Wikipedia). Commune marker, not the trial field.
SITE = {
    "area_id": "site_luu_son",
    "lat": 18.89638889,
    "lon": 105.2802778,
    "source_url": "https://www.wikidata.org/wiki/Q10788283",
    "source_revision": "Wikidata revision 2511038945 (modified 2026-06-27T09:41:17Z)",
}
# Window read from every file: union of the 5 footprints (and contains the site), padded by one pixel.
WINDOW = {"lat_min": 18.25 - 0.05, "lat_max": 19.75 + 0.05, "lon_min": 104.6875 - 0.05, "lon_max": 105.9375 + 0.05}
CSV_COLUMNS = ["area_id", "lat", "lon", "year", "month", "precip_mm", "n_pixels", "n_missing", "source_file"]


# ----------------------------------------------------------------------------------------------- pure functions
def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    """Even-odd ray casting for one closed or open ring of [x, y] vertices."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_polygon(x: float, y: float, geometry: dict) -> bool:
    """GeoJSON Polygon or MultiPolygon; holes are respected (point inside the outer ring and outside every hole)."""
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError(f"unsupported geometry type {geometry['type']}")
    for rings in polygons:
        if not rings or not point_in_ring(x, y, rings[0]):
            continue
        if any(point_in_ring(x, y, hole) for hole in rings[1:]):
            continue
        return True
    return False


def footprint(lat: float, lon: float) -> tuple[float, float, float, float]:
    """(lat_min, lat_max, lon_min, lon_max) of the POWER cell centred at lat, lon."""
    return (lat - HALF_LAT, lat + HALF_LAT, lon - HALF_LON, lon + HALF_LON)


def pixel_centres(transform: tuple[float, ...], row_off: int, col_off: int, height: int, width: int):
    """Centre lat and lon arrays (height, width) for a window of a north-up affine (a, b, c, d, e, f) grid."""
    a, b, c, d, e, f = transform[:6]
    if b != 0 or d != 0:
        raise ValueError("rotated grids are not supported")
    cols = np.arange(col_off, col_off + width) + 0.5
    rows = np.arange(row_off, row_off + height) + 0.5
    lons = c + a * cols
    lats = f + e * rows
    return np.broadcast_to(lats[:, None], (height, width)), np.broadcast_to(lons[None, :], (height, width))


def select_pixels(
    lats: np.ndarray, lons: np.ndarray, bounds: tuple[float, float, float, float], geometry: dict | None
) -> np.ndarray:
    """Boolean mask of pixels whose centre lies inside the half-open box [min, max) and inside the polygon."""
    lat_min, lat_max, lon_min, lon_max = bounds
    mask = (lats >= lat_min) & (lats < lat_max) & (lons >= lon_min) & (lons < lon_max)
    if geometry is not None:
        for r, c in zip(*np.nonzero(mask), strict=True):
            if not point_in_polygon(float(lons[r, c]), float(lats[r, c]), geometry):
                mask[r, c] = False
    return mask


def pixel_containing(transform: tuple[float, ...], lat: float, lon: float) -> tuple[int, int]:
    """Global (row, col) of the pixel whose area contains the point."""
    a, _, c, _, e, f = transform[:6]
    return int(math.floor((lat - f) / e)), int(math.floor((lon - c) / a))


def is_missing(values: np.ndarray) -> np.ndarray:
    """CHIRPS nodata is -9999; any negative or non-finite rainfall is treated as missing, never as zero."""
    v = np.asarray(values, dtype="float64")
    return ~np.isfinite(v) | (v < 0)


def aggregate(values: np.ndarray, mask: np.ndarray) -> tuple[float | None, int, int]:
    """Mean of the valid selected pixels, number of selected pixels, number of missing selected pixels."""
    sel = np.asarray(values, dtype="float64")[mask]
    miss = is_missing(sel)
    n_pixels = int(sel.size)
    n_missing = int(miss.sum())
    valid = sel[~miss]
    mean = float(valid.mean()) if valid.size else None
    return mean, n_pixels, n_missing


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3:
        return None
    xa, ya = np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64")
    if xa.std() == 0 or ya.std() == 0:
        return None
    return float(np.corrcoef(xa, ya)[0, 1])


def power_monthly_totals(daily: dict[str, float], fill: float = -999.0) -> dict[tuple[int, int], float]:
    """Monthly sums of daily mm; a month with any fill day or any absent calendar day is left out (not filled)."""
    by_month: dict[tuple[int, int], list[float]] = {}
    for key, v in daily.items():
        by_month.setdefault((int(key[:4]), int(key[4:6])), []).append(v)
    out = {}
    for (y, m), vals in by_month.items():
        ndays = (datetime(y + (m == 12), m % 12 + 1, 1) - datetime(y, m, 1)).days
        if len(vals) != ndays or any(v == fill or v is None or (isinstance(v, float) and math.isnan(v)) for v in vals):
            continue
        out[(y, m)] = float(sum(vals))
    return out


def parse_listing(html: str) -> dict[str, str]:
    """{file name: listing date} from the CHC nginx fancy-index page."""
    out = {}
    for m in re.finditer(r'href="(chirps-v3\.0\.\d{4}\.\d{2}\.cog)".*?<td class="date">([^<]+)</td>', html, re.S):
        out[m.group(1)] = m.group(2).strip()
    if not out:  # fallback: plain text after tag stripping
        text = re.sub(r"<[^>]+>", " ", html)
        for m in re.finditer(
            r"(chirps-v3\.0\.\d{4}\.\d{2}\.cog)\s+[\d.]+\s+\w+\s+(\d{4}-\w{3}-\d{2} \d{2}:\d{2})", text
        ):
            out[m.group(1)] = m.group(2)
    return out


def file_name(year: int, month: int) -> str:
    return f"chirps-v3.0.{year}.{month:02d}.cog"


# ----------------------------------------------------------------------------------------------- I/O
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cells() -> list[dict]:
    with open(CELLS_CSV, encoding="utf-8") as fh:
        return [{"area_id": r["cell_id"], "lat": float(r["lat"]), "lon": float(r["lon"])} for r in csv.DictReader(fh)]


def load_nghe_an() -> dict:
    g = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    for f in g["features"]:
        if f["properties"].get("shapeISO") == "VN-22":
            return f["geometry"]
    raise SystemExit("Nghệ An (VN-22) not found in the boundary file")


def http_get_text(url: str, tries: int = 6) -> str:
    import httpx

    delay = 5.0
    for _attempt in range(tries):
        try:
            r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)
            if r.status_code == 200:
                return r.text
            if r.status_code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {r.status_code} for {url}")
        except httpx.HTTPError as exc:  # network error: retry
            print(f"  {url}: {exc!r}", file=sys.stderr)
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"giving up on {url}")


def gdal_env() -> dict:
    return {
        "GDAL_HTTP_USERAGENT": USER_AGENT,
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".cog",
        "GDAL_HTTP_MAX_RETRY": "6",
        "GDAL_HTTP_RETRY_DELAY": "5",
        "GDAL_INGESTED_BYTES_AT_OPEN": "32768",
        "VSI_CACHE": "FALSE",
    }


def fetch_window(year: int, month: int, tries: int = 5) -> Path:
    """Read the study window of one monthly COG and cache it as .npz; returns the cache path."""
    import rasterio
    from rasterio.windows import from_bounds

    out = CACHE_DIR / f"{file_name(year, month)}.window.npz"
    if out.exists():
        return out
    url = BASE_URL + file_name(year, month)
    delay = 10.0
    last: Exception | None = None
    for attempt in range(tries):
        try:
            with rasterio.Env(**gdal_env()), rasterio.open("/vsicurl/" + url) as ds:
                win = (
                    from_bounds(
                        WINDOW["lon_min"], WINDOW["lat_min"], WINDOW["lon_max"], WINDOW["lat_max"], ds.transform
                    )
                    .round_offsets()
                    .round_lengths()
                )
                arr = ds.read(1, window=win)
                t = ds.transform
                tags = ds.tags()
                np.savez_compressed(
                    out.with_suffix(".tmp.npz"),
                    data=arr,
                    transform=np.array([t.a, t.b, t.c, t.d, t.e, t.f]),
                    row_off=int(win.row_off),
                    col_off=int(win.col_off),
                    nodata=np.array(np.nan if ds.nodata is None else ds.nodata),
                    tiff_datetime=np.array(tags.get("TIFFTAG_DATETIME", "")),
                    width=ds.width,
                    height=ds.height,
                )
            os.replace(out.with_suffix(".tmp.npz"), out)
            return out
        except Exception as exc:  # noqa: BLE001 - network / GDAL errors: back off and retry
            last = exc
            print(f"  {file_name(year, month)} attempt {attempt + 1}: {exc}", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"failed {url}: {last}")


def fetch_all(workers: int = 2) -> list[str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    todo = [(y, m) for y in YEARS for m in range(1, 13) if not (CACHE_DIR / f"{file_name(y, m)}.window.npz").exists()]
    print(f"{len(todo)} monthly files to read ({len(YEARS) * 12 - len(todo)} already cached)")
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {}
        for y, m in todo:
            futs[pool.submit(fetch_window, y, m)] = (y, m)
            time.sleep(0.5)  # stagger the submissions: polite request rate
        for i, fut in enumerate(as_completed(futs), 1):
            y, m = futs[fut]
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                failed.append(file_name(y, m))
                print(f"FAILED {file_name(y, m)}: {exc}", file=sys.stderr)
            if i % 24 == 0:
                print(f"  {i}/{len(todo)} done")
    return failed


# ----------------------------------------------------------------------------------------------- build
def build(listing: dict[str, str]) -> dict:
    cells = load_cells()
    geom = load_nghe_an()
    rows: list[dict] = []
    masks: dict[str, np.ndarray] | None = None
    ref_transform = None
    site_rc = None
    tiff_dates = []
    absent = []
    for y in YEARS:
        for m in range(1, 13):
            fname = file_name(y, m)
            path = CACHE_DIR / f"{fname}.window.npz"
            if not path.exists():
                absent.append(fname)
                for area in cells + [SITE]:
                    rows.append(
                        {
                            "area_id": area["area_id"],
                            "lat": area["lat"],
                            "lon": area["lon"],
                            "year": y,
                            "month": m,
                            "precip_mm": "",
                            "n_pixels": 0,
                            "n_missing": "",
                            "source_file": "",
                        }
                    )
                continue
            z = np.load(path)
            data = z["data"]
            transform = tuple(float(v) for v in z["transform"])
            row_off, col_off = int(z["row_off"]), int(z["col_off"])
            tiff_dates.append(str(z["tiff_datetime"]))
            key = (transform, row_off, col_off, data.shape)
            if ref_transform is None:
                ref_transform = key
                lats, lons = pixel_centres(transform, row_off, col_off, *data.shape)
                masks = {c["area_id"]: select_pixels(lats, lons, footprint(c["lat"], c["lon"]), geom) for c in cells}
                gr, gc = pixel_containing(transform, SITE["lat"], SITE["lon"])
                site_rc = (gr - row_off, gc - col_off)
                site_lat, site_lon = float(lats[site_rc]), float(lons[site_rc])
            elif key != ref_transform:
                raise SystemExit(f"{fname}: grid differs from the first file; refusing to mix grids")
            for c in cells:
                mean, n_pix, n_miss = aggregate(data, masks[c["area_id"]])
                rows.append(
                    {
                        "area_id": c["area_id"],
                        "lat": c["lat"],
                        "lon": c["lon"],
                        "year": y,
                        "month": m,
                        "precip_mm": "" if mean is None else f"{mean:.3f}",
                        "n_pixels": n_pix,
                        "n_missing": n_miss,
                        "source_file": fname,
                    }
                )
            v = float(data[site_rc])
            miss = bool(is_missing(np.array([v]))[0])
            rows.append(
                {
                    "area_id": SITE["area_id"],
                    "lat": round(site_lat, 4),
                    "lon": round(site_lon, 4),
                    "year": y,
                    "month": m,
                    "precip_mm": "" if miss else f"{v:.3f}",
                    "n_pixels": 1,
                    "n_missing": int(miss),
                    "source_file": fname,
                }
            )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return {
        "rows": rows,
        "cells": cells,
        "masks": masks,
        "absent": absent,
        "tiff_dates": tiff_dates,
        "site_pixel": (site_lat, site_lon) if site_rc else None,
    }


def power_diagnostics(rows: list[dict], cells: list[dict]) -> list[dict]:
    out = []
    for c in cells:
        files = sorted(POWER_DIR.glob(f"power_{c['lat']:.4f}_{c['lon']:.4f}_*.json"))
        if not files:
            out.append({"cell": c["area_id"], "error": "no POWER cache"})
            continue
        d = json.loads(files[0].read_text(encoding="utf-8"))
        fill = float(d.get("header", {}).get("fill_value", -999.0))
        pw = power_monthly_totals(d["properties"]["parameter"]["PRECTOTCORR"], fill)
        ch = {
            (r["year"], r["month"]): float(r["precip_mm"])
            for r in rows
            if r["area_id"] == c["area_id"] and r["precip_mm"] != ""
        }
        keys = sorted(k for k in ch if k in pw and 1991 <= k[0] <= 2024)
        x, yv = [ch[k] for k in keys], [pw[k] for k in keys]
        r = pearson(x, yv)
        out.append(
            {
                "cell": c["area_id"],
                "power_file": files[0].name,
                "n_months": len(keys),
                "pearson_r_monthly": None if r is None else round(r, 3),
                "chirps_mean_annual_mm": round(sum(x) / (len(keys) / 12), 1) if keys else None,
                "power_mean_annual_mm": round(sum(yv) / (len(keys) / 12), 1) if keys else None,
            }
        )
    return out


def write_manifest(result: dict, listing: dict[str, str], diag: list[dict], failed: list[str]) -> None:
    rows = result["rows"]
    n_rows = len(rows)
    n_empty = sum(1 for r in rows if r["precip_mm"] == "")
    n_px_missing = sum(int(r["n_missing"]) for r in rows if r["n_missing"] != "")
    used = [file_name(y, m) for y in YEARS for m in range(1, 13)]
    dates = sorted((listing[f] for f in used if listing.get(f)), key=lambda s: datetime.strptime(s, "%Y-%b-%d %H:%M"))
    pixel_counts = (
        {c["area_id"]: int(result["masks"][c["area_id"]].sum()) for c in result["cells"]} if result["masks"] else {}
    )
    status = "INGESTED" if not result["absent"] and n_empty == 0 else ("PARTIAL" if n_rows > n_empty else "BLOCKED")
    diag_txt = "; ".join(
        f"{d['cell']}: r={d.get('pearson_r_monthly')} over n={d.get('n_months')} months, mean annual CHIRPS "
        f"{d.get('chirps_mean_annual_mm')} mm vs POWER {d.get('power_mean_annual_mm')} mm"
        for d in diag
    )
    site_lat, site_lon = result["site_pixel"] or (None, None)
    manifest = {
        "dataset_id": "chirps_v3_monthly",
        "title": {
            "vi": "Lượng mưa tháng CHIRPS v3.0 cho 5 ô lưới NASA POWER ở Nghệ An và điểm nghiên cứu Lưu Sơn",
            "en": "CHIRPS v3.0 monthly rainfall for the 5 NASA POWER cells in Nghệ An and the Lưu Sơn study site",
        },
        "provider": "Climate Hazards Center, University of California, Santa Barbara",
        "source_id": "CHIRPS-v3.0",
        "source_url": BASE_URL,
        "license": "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); CHC also states a public-domain waiver - see notes",
        "source_revision": (
            f"CHIRPS v3.0 final monthly global COGs (version 3.0 released 2025-01-01); directory listing "
            f"dates of the {len(used)} files used range {dates[0] if dates else '?'} to "
            f"{dates[-1] if dates else '?'}; per-file dates in source_files"
        ),
        # when the window reads were made (cache file times), not when this manifest was rebuilt
        "retrieved_at": max(
            (datetime.fromtimestamp(p.stat().st_mtime, UTC) for p in CACHE_DIR.glob("*.window.npz")),
            default=datetime.now(UTC),
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest_built_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temporal_coverage": "1991-01 to 2024-12 (monthly)",
        "spatial_resolution": "0.05°",
        "geometry_crs": "EPSG:4326",
        "variables": ["precip_mm (monthly total precipitation, mm/month)", "n_pixels", "n_missing"],
        "missing_policy": (
            "A CHIRPS pixel with value -9999 or any negative/non-finite value is missing. Missing pixels "
            "are counted in n_missing and left out of the mean; nothing is filled, interpolated or set "
            "to zero. A month with no valid pixel, or whose file could not be read, has an empty "
            "precip_mm."
        ),
        "allowed_use": {
            "vi": "Mô tả lượng mưa tháng trong quá khứ ở quy mô ô lưới; không phải số đo tại ruộng, không phải dự báo.",
            "en": "Describe past monthly rainfall at grid scale; not a field measurement, not a forecast.",
        },
        "version_sha256": sha256_file(OUT_CSV),
        "ingestion_status": status,
        "is_field_measurement": False,
        "files": {"csv": OUT_CSV.relative_to(ROOT).as_posix(), "script": "pipeline/fetch_chirps_v3.py"},
        "row_count": n_rows,
        "rows_with_empty_precip": n_empty,
        "selected_pixels_missing_total": n_px_missing,
        "pixels_per_cell": pixel_counts,
        "absent_files": result["absent"],
        "failed_files": failed,
        "study_site": {
            "area_id": SITE["area_id"],
            "point_lat": SITE["lat"],
            "point_lon": SITE["lon"],
            "pixel_centre_lat": round(site_lat, 4),
            "pixel_centre_lon": round(site_lon, 4),
            "source_url": SITE["source_url"],
            "source_revision": SITE["source_revision"],
        },
        "power_comparison": diag,
        "source_files": {f: listing.get(f) for f in used},
        "notes": [
            {
                "vi": "Giấy phép: trang https://www.chc.ucsb.edu/data/chirps3 ghi nguyên văn: 'CHIRPS3 is in the public domain, as registered with Creative Commons, and is licensed under a Creative Commons Attribution 4.0 International License. To the extent possible under the law, the Climate Hazards Center has waived all copyright and related or neighboring rights to CHIRPS3.' Tệp README không nêu giấy phép. Chúng tôi ghi CC BY 4.0 và luôn trích dẫn nguồn.",
                "en": "Licence: https://www.chc.ucsb.edu/data/chirps3 states verbatim: 'CHIRPS3 is in the public domain, as registered with Creative Commons, and is licensed under a Creative Commons Attribution 4.0 International License. To the extent possible under the law, the Climate Hazards Center has waived all copyright and related or neighboring rights to CHIRPS3.' The README states no licence. We record CC BY 4.0 and always attribute.",
            },
            {
                "vi": "Trích dẫn: CHIRPS3 Data Repository, https://doi.org/10.15780/G2JQ0P (2025); Funk, C. et al. (2026) The Climate Hazards Center Infrared Precipitation with Stations, Version 3. Sci Data 13, 718, https://doi.org/10.1038/s41597-026-07096-4.",
                "en": "Citation: CHIRPS3 Data Repository, https://doi.org/10.15780/G2JQ0P (2025); Funk, C. et al. (2026) The Climate Hazards Center Infrared Precipitation with Stations, Version 3. Sci Data 13, 718, https://doi.org/10.1038/s41597-026-07096-4.",
            },
            {
                "vi": "Chỉ dùng thư mục bản cuối monthly/global/cogs, không dùng thư mục prelim; không có tháng nào trong 1991-2024 là bản sơ bộ.",
                "en": "Only the final monthly/global/cogs directory is used, never prelim/; no month in 1991-2024 is a preliminary value.",
            },
            {
                "vi": "Giá trị ô lưới là trung bình các điểm ảnh CHIRPS 0,05 độ có tâm nằm trong ô POWER (vĩ độ ±0,25, kinh độ ±0,3125) và trong ranh giới Nghệ An (geoBoundaries ADM1 giản lược). Điểm ảnh ngoài mặt nạ đất liền của CHIRPS (gần bờ biển) được đếm là thiếu.",
                "en": "A cell value is the mean of CHIRPS 0.05 deg pixels whose centres are inside the POWER cell (lat +/-0.25, lon +/-0.3125) and inside Nghệ An (geoBoundaries ADM1 simplified). Pixels outside the CHIRPS land mask (near the coast) count as missing.",
            },
            {
                "vi": f"Điểm nghiên cứu: một điểm ảnh CHIRPS chứa tọa độ xã Lưu Sơn ({SITE['lat']}, {SITE['lon']}) theo Wikidata Q10788283; đó là điểm đánh dấu của xã, không phải vị trí ruộng thử nghiệm. Xã Lưu Sơn đã nhập vào xã Đô Lương mới năm 2025 (Nghị quyết 1678/NQ-UBTVQH15).",
                "en": f"Study site: the one CHIRPS pixel containing the Lưu Sơn commune point ({SITE['lat']}, {SITE['lon']}) from Wikidata Q10788283; it is the commune marker, not the trial field. Lưu Sơn merged into the new Đô Lương commune in 2025 (Resolution 1678/NQ-UBTVQH15).",
            },
            {
                "vi": "So sánh với NASA POWER PRECTOTCORR (tổng tháng, chỉ tháng đủ ngày) chỉ là chẩn đoán, không kiểm định sản phẩm nào: "
                + diag_txt,
                "en": "Comparison with NASA POWER PRECTOTCORR (monthly totals, complete months only) is a diagnostic, not a validation of either product: "
                + diag_txt,
            },
            {
                "vi": "CHIRPS là ước tính từ vệ tinh và trạm đo; không phải số đo tại ruộng. v3.0 ẩm hơn v2.0 do hiệu chỉnh hứng thiếu của vũ kế (README).",
                "en": "CHIRPS is a satellite-plus-station estimate, not a field measurement. v3.0 is wetter than v2.0 because of the gauge-undercatch correction (README).",
            },
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-fetch", action="store_true", help="build only from the cache")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    listing_cache = CACHE_DIR / "cogs_listing.html"
    if not listing_cache.exists():
        listing_cache.write_text(http_get_text(BASE_URL), encoding="utf-8")
    listing = parse_listing(listing_cache.read_text(encoding="utf-8"))
    failed = [] if args.no_fetch else fetch_all(args.workers)
    result = build(listing)
    diag = power_diagnostics(result["rows"], result["cells"])
    write_manifest(result, listing, diag, failed)
    print(json.dumps(diag, indent=1))
    print(f"wrote {OUT_CSV} ({len(result['rows'])} rows) and {MANIFEST}")


if __name__ == "__main__":
    main()
