"""Sentinel-2 L2A vegetation indices over the former Đô Lương district (Nghệ An) from public COGs on AWS.

Discovery: Element 84 Earth Search STAC API v1, https://earth-search.aws.element84.com/v1, collection
           `sentinel-2-l2a` (COGs in s3://sentinel-cogs, public, no authentication; AWS Open Data Registry
           "Sentinel-2 Cloud-Optimized GeoTIFFs"). Optional cross-check of the same acquisitions in the Copernicus
           Data Space STAC (https://stac.dataspace.copernicus.eu/v1/) - discovery only; downloading assets there
           needs a free CDSE account, which this script does not use.
Licence:   Copernicus Sentinel data, free, full and open under Regulation (EU) No 377/2014 and Commission Delegated
           Regulation (EU) No 1159/2013 (Legal notice on the use of Copernicus Sentinel Data and Service
           Information, https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice).
           Required notice for derived products: "Contains modified Copernicus Sentinel data 2020-2024".

Acquisition (bounded, no full-scene download):
  * search bbox = the Đô Lương ADM2 bbox from data/canonical/geo_do_luong.json (fallback: 15 km box around the
    study point), periods 2020-06-01..2021-06-30 (trial year) and 2023-01-01..2024-12-31, eo:cloud_cover < 60;
  * one item per (date, MGRS tile): the highest processing baseline wins (the 2021 reprocessing N05.00 replaces
    the original N02.14/N03.00 item of the same acquisition), so the series uses one processor version per date;
  * the district straddles MGRS tiles 48QWF and 48QWG; a "scene" is one acquisition date mosaicked on a common
    20 m grid in EPSG:32648 (UTM 48N, aligned with the Sentinel-2 20 m grid), tile by tile, first tile wins where
    both have data (same acquisition, same radiometry);
  * per tile only the window over the district is read with HTTP range requests (GDAL /vsicurl/);
  * screening: SCL (20 m) is read first; a scene with < 20 % kept pixels inside the district is skipped before any
    reflectance band is read;
  * bands: B02 blue, B04 red, B08 NIR (10 m) and B11 SWIR-1 (20 m) + SCL (20 m). The 10 m bands are brought to
    20 m by the arithmetic mean of each aligned 2x2 block of digital numbers; a 20 m pixel is missing if any of its
    four 10 m pixels is nodata (0).

Reflectance: rho = DN * scale + offset, scale from each asset's `raster:bands` (0.0001). Offset: ESA adds
  BOA_ADD_OFFSET = -1000 (DN +1000) from processing baseline 04.00, but Earth Search items flagged
  `earthsearch:boa_offset_applied: true` already carry offset-corrected pixel values even though `raster:bands`
  still declares offset -0.1 (applying it again gave NDVI > 1 in a first run). Applied offset: 0 when the flag is
  true, -0.1 for baseline >= 04.00 without the flag, 0 for older baselines; each tile is checked against its own
  data (1st percentile of red DN < 1000 with offset 0, > 1000 with -0.1). Negative reflectances are kept.
Haze test: a tile whose SCL-vegetation pixels have median red reflectance > 0.10 is skipped (thin cloud or haze
  that SCL missed; clear vegetation is ~0.02-0.08).

Indices (reflectance 0..1):
  NDVI = (NIR - Red) / (NIR + Red)                                   undefined where NIR + Red <= 0
  EVI  = 2.5 * (NIR - Red) / (NIR + 6 * Red - 7.5 * Blue + 1)        undefined where the denominator <= 0
  NDMI = (NIR - SWIR1) / (NIR + SWIR1)  (B08 and B11)                undefined where NIR + SWIR1 <= 0

SCL classes kept: 4 vegetation, 5 not vegetated (bare soil), 6 water (flooded paddies are real surface state).
Dropped: 0 no data, 1 saturated/defective, 2 dark area/topographic shadow, 3 cloud shadow, 7 unclassified (in
  baselines < 04.00 this class is "cloud low probability"), 8 cloud medium probability, 9 cloud high probability,
  10 thin cirrus, 11 snow/ice.

Statistics: median, 25th and 75th percentile (numpy linear) over kept pixels whose centre is inside the Đô Lương
  polygon; valid_fraction = kept pixels with all bands present / pixels inside the polygon.
Seasons (non-overlapping; the brief's Jun-Sep and Sep-Dec windows overlap, September is split at day 15):
  spring = 1 Jan - 31 May; summer_autumn = 1 Jun - 15 Sep; autumn_winter = 16 Sep - 31 Dec.
Composites: per-pixel median NDVI of the used scenes of a season (missing where no scene has a valid pixel),
  for summer_autumn 2020, autumn_winter 2020, spring 2021 (trial year) and the three seasons of 2024.

Everything fetched is cached in data/cache/sentinel2/ (git-ignored), so a rerun resumes.

Run:   .venv\\Scripts\\python.exe pipeline\\fetch_sentinel2.py [--max-scenes 60] [--workers 3]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "MiaudowResearch/1.0 (NASA Space Apps 2026 hackathon)"
STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
CDSE_STAC_URL = "https://stac.dataspace.copernicus.eu/v1"
LICENSE = (
    "Copernicus Sentinel data: free, full and open access under Regulation (EU) No 377/2014 and Commission "
    "Delegated Regulation (EU) No 1159/2013; notice required: 'Contains modified Copernicus Sentinel data "
    "2020-2024'"
)
LICENSE_URL = "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice"
CITE_AS = "https://doi.org/10.5270/S2_-742ikth"
PERIODS = [("trial_year", "2020-06-01", "2021-06-30"), ("recent", "2023-01-01", "2024-12-31")]
CLOUD_MAX = 60.0
MIN_VALID = 0.20
DST_CRS = "EPSG:32648"
RES = 20.0
SCL_KEEP = (4, 5, 6)
SCL_NAMES = {
    0: "no_data",
    1: "saturated_defective",
    2: "dark_area_or_topographic_shadow",
    3: "cloud_shadow",
    4: "vegetation",
    5: "not_vegetated",
    6: "water",
    7: "unclassified",
    8: "cloud_medium_probability",
    9: "cloud_high_probability",
    10: "thin_cirrus",
    11: "snow_ice",
}
SCL_CLOUD = (3, 8, 9, 10)
BANDS = {"blue": ("blue", 10), "red": ("red", 10), "nir": ("nir", 10), "swir16": ("swir16", 20)}
SEASONS = {"spring": "Xuân (tháng 1-5)", "summer_autumn": "Hè Thu (1/6-15/9)", "autumn_winter": "Thu Đông (16/9-12)"}
COMPOSITES = [
    ("summer_autumn", 2020),
    ("autumn_winter", 2020),
    ("spring", 2021),
    ("spring", 2024),
    ("summer_autumn", 2024),
    ("autumn_winter", 2024),
]
RAMP = [(0.0, (0xB5, 0x62, 0x3E)), (0.4, (0xE9, 0xBC, 0x57)), (0.8, (0x2F, 0x5A, 0x37))]
PNG_MAX = 1024
NDVI_SCALE = 10000  # cached NDVI arrays are int16 x 10000
I16_NODATA = -32768

GEO_FILE = ROOT / "data" / "canonical" / "geo_do_luong.json"
ADM2_FILE = ROOT / "data" / "raw" / "boundaries" / "do_luong_adm2.geojson"
CACHE = ROOT / "data" / "cache" / "sentinel2"
OUT_DIR = ROOT / "data" / "raw" / "sentinel2"
OUT_SCENES = OUT_DIR / "scenes.csv"
OUT_ITEMS = OUT_DIR / "stac_items.json"
OUT_MANIFEST = OUT_DIR / "MANIFEST.json"
OUT_VEG = ROOT / "data" / "canonical" / "vegetation.json"
PNG_DIR = ROOT / "web" / "public" / "media" / "sat"
COG_TRACKED_DIR = OUT_DIR / "composites"
COG_CACHE_DIR = CACHE / "composites"
COG_TRACK_LIMIT = 5 * 1024 * 1024

GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_USERAGENT": USER_AGENT,
    "GDAL_HTTP_MULTIRANGE": "YES",
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "GDAL_HTTP_MAX_RETRY": "4",
    "GDAL_HTTP_RETRY_DELAY": "3",
    "VSI_CACHE": "TRUE",
    "VSI_CACHE_SIZE": "50000000",
}


# ----------------------------------------------------------------------------------------------- pure functions
def scl_keep_mask(scl: np.ndarray, keep=SCL_KEEP) -> np.ndarray:
    """True where the scene classification is one of the kept classes."""
    return np.isin(scl, np.asarray(keep, dtype=scl.dtype))


def dn_to_reflectance(dn: np.ndarray, scale: float, offset: float, nodata: float = 0) -> np.ndarray:
    """Digital numbers to surface reflectance (rho = DN * scale + offset); nodata and NaN become NaN."""
    dn = np.asarray(dn, dtype=np.float64)
    out = dn * scale + offset
    out[(dn == nodata) | ~np.isfinite(dn)] = np.nan
    return out.astype(np.float32)


def block_mean_2x2(a: np.ndarray, nodata: float = 0) -> np.ndarray:
    """10 m -> 20 m: mean of each aligned 2x2 block; NaN when any of the four values is nodata or NaN.

    The input must have even dimensions (the caller reads 10 m windows aligned to the 20 m grid).
    """
    if a.shape[0] % 2 or a.shape[1] % 2:
        raise ValueError(f"odd shape {a.shape}")
    f = np.asarray(a, dtype=np.float64).copy()
    f[(f == nodata) | ~np.isfinite(f)] = np.nan
    blocks = f.reshape(a.shape[0] // 2, 2, a.shape[1] // 2, 2)
    return blocks.mean(axis=(1, 3)).astype(np.float32)  # NaN propagates: any missing sub-pixel -> NaN


def _safe_div(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    num = np.asarray(num, dtype=np.float64)
    den = np.asarray(den, dtype=np.float64)
    out = np.full(np.broadcast(num, den).shape, np.nan)
    ok = np.isfinite(num) & np.isfinite(den) & (den > 0)
    np.divide(num, den, out=out, where=ok)
    return out.astype(np.float32)


def ndvi(red, nir):
    """NDVI = (NIR - Red) / (NIR + Red); NaN where NIR + Red <= 0."""
    red, nir = np.asarray(red, np.float64), np.asarray(nir, np.float64)
    return _safe_div(nir - red, nir + red)


def evi(blue, red, nir):
    """EVI = 2.5 (NIR - Red) / (NIR + 6 Red - 7.5 Blue + 1); NaN where the denominator <= 0."""
    blue, red, nir = (np.asarray(x, np.float64) for x in (blue, red, nir))
    return _safe_div(2.5 * (nir - red), nir + 6.0 * red - 7.5 * blue + 1.0)


def ndmi(nir, swir1):
    """NDMI = (NIR - SWIR1) / (NIR + SWIR1); NaN where NIR + SWIR1 <= 0."""
    nir, swir1 = np.asarray(nir, np.float64), np.asarray(swir1, np.float64)
    return _safe_div(nir - swir1, nir + swir1)


def masked_stats(values: np.ndarray, mask: np.ndarray, decimals: int = 4) -> dict:
    """Median / p25 / p75 / n over finite values where mask is True; empty dict values when none."""
    v = np.asarray(values, dtype=np.float64)[np.asarray(mask, bool)]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"median": None, "p25": None, "p75": None, "n": 0}
    p25, med, p75 = np.percentile(v, [25, 50, 75])
    return {
        "median": round(float(med), decimals),
        "p25": round(float(p25), decimals),
        "p75": round(float(p75), decimals),
        "n": int(v.size),
    }


def season_of(d: date) -> tuple[str, int]:
    """(season, year) with non-overlapping seasons; September is split at day 15 (see module docstring)."""
    if d.month <= 5:
        return "spring", d.year
    if d.month <= 8 or (d.month == 9 and d.day <= 15):
        return "summer_autumn", d.year
    return "autumn_winter", d.year


def snap_bounds(bounds, res: float = RES) -> tuple[float, float, float, float]:
    """Expand (left, bottom, right, top) outward to multiples of res (the Sentinel-2 20 m grid is aligned to 20 m
    in UTM: tile origins such as x=499980, y=2200020 are multiples of 20)."""
    left, b, r, t = bounds
    return (math.floor(left / res) * res, math.floor(b / res) * res, math.ceil(r / res) * res, math.ceil(t / res) * res)


def baseline_key(item: dict) -> tuple:
    p = item["properties"]
    return (float(p.get("s2:processing_baseline") or 0), int(p.get("s2:sequence") or 0))


def dedupe_items(items: list[dict]) -> list[dict]:
    """One item per (acquisition date, MGRS tile): the highest processing baseline (then sequence) wins."""
    best: dict[tuple, dict] = {}
    for it in items:
        p = it["properties"]
        key = (p["datetime"][:10], p.get("grid:code") or it["id"].split("_")[1])
        if key not in best or baseline_key(it) > baseline_key(best[key]):
            best[key] = it
    return sorted(best.values(), key=lambda i: (i["properties"]["datetime"], i["id"]))


def group_scenes(items: list[dict]) -> dict[str, list[dict]]:
    """scene id 'S2A_20210627' -> its tile items (one acquisition date and platform)."""
    groups: dict[str, list[dict]] = {}
    for it in items:
        p = it["properties"]
        sid = f"{p['platform'].replace('sentinel-', 'S').upper()}_{p['datetime'][:10].replace('-', '')}"
        groups.setdefault(sid, []).append(it)
    return dict(sorted(groups.items(), key=lambda kv: kv[0].split("_")[1]))


def ndvi_rgba(nd: np.ndarray, alpha_mask: np.ndarray | None = None, ramp=RAMP) -> np.ndarray:
    """NDVI -> RGBA uint8 with a piecewise-linear ramp; values below/above the end stops are clamped to the end
    colours; NaN (or alpha_mask False) -> fully transparent."""
    nd = np.asarray(nd, dtype=np.float64)
    xs = [s for s, _ in ramp]
    rgba = np.zeros(nd.shape + (4,), dtype=np.uint8)
    finite = np.isfinite(nd)
    v = np.clip(np.where(finite, nd, xs[0]), xs[0], xs[-1])
    for ch in range(3):
        rgba[..., ch] = np.round(np.interp(v, xs, [c[ch] for _, c in ramp])).astype(np.uint8)
    visible = finite if alpha_mask is None else (finite & np.asarray(alpha_mask, bool))
    rgba[..., 3] = np.where(visible, 255, 0)
    rgba[~visible, :3] = 0
    return rgba


def encode_png(rgba: np.ndarray) -> bytes:
    """Minimal PNG encoder (8-bit RGBA, no filter) - no imaging library needed."""
    h, w, c = rgba.shape
    if c != 4 or rgba.dtype != np.uint8:
        raise ValueError("need HxWx4 uint8")
    raw = b"".join(b"\x00" + rgba[y].tobytes() for y in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def png_grid(bounds_ll, max_px: int = PNG_MAX) -> tuple[int, int]:
    """(width, height) of a lon/lat grid over bounds whose pixels are square on the ground, longest side max_px."""
    w, s, e, n = bounds_ll
    lat0 = math.radians((s + n) / 2)
    gx, gy = (e - w) * math.cos(lat0), (n - s)
    if gx >= gy:
        return max_px, max(1, round(max_px * gy / gx))
    return max(1, round(max_px * gx / gy)), max_px


# ----------------------------------------------------------------------------------------------- I/O helpers
def http_json(method: str, url: str, body: dict | None = None, tries: int = 5, timeout: float = 120.0) -> dict:
    import httpx

    delay, last = 3.0, None
    for attempt in range(tries):
        try:
            r = httpx.request(
                method,
                url,
                json=body,
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json, application/json"},
            )
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code not in (429, 500, 502, 503, 504):
                raise RuntimeError(last)
        except (httpx.HTTPError, ValueError) as exc:
            last = repr(exc)
        print(f"  retry {attempt + 1} {url}: {last}", file=sys.stderr)
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"giving up {url}: {last}")


def stac_search(bbox, start: str, end: str) -> list[dict]:
    feats, body = (
        [],
        {
            "collections": [COLLECTION],
            "bbox": bbox,
            "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
            "limit": 100,
            "query": {"eo:cloud_cover": {"lt": CLOUD_MAX}},
        },
    )
    url = f"{STAC_URL}/search"
    while True:
        d = http_json("POST", url, body)
        feats.extend(d.get("features", []))
        nxt = next((ln for ln in d.get("links", []) if ln.get("rel") == "next"), None)
        if not nxt:
            return feats
        url, body = nxt["href"], nxt.get("body", body)
        time.sleep(0.5)


def load_area():
    """(polygon geojson in lon/lat, bbox, source) from task A, or a 15 km box around the study point."""
    if GEO_FILE.exists() and ADM2_FILE.exists():
        geo = json.loads(GEO_FILE.read_text(encoding="utf-8"))
        feat = json.loads(ADM2_FILE.read_text(encoding="utf-8"))["features"][0]
        return feat["geometry"], geo["do_luong"]["bbox"], "Đô Lương ADM2 polygon (geoBoundaries)", geo
    lat, lon, half = 18.89638889, 105.2802778, 7.5
    dlat, dlon = half / 111.32, half / (111.32 * math.cos(math.radians(lat)))
    ring = [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
        [lon - dlon, lat - dlat],
    ]
    return (
        {"type": "Polygon", "coordinates": [ring]},
        [lon - dlon, lat - dlat, lon + dlon, lat + dlat],
        "15 km box around the study point (fallback)",
        None,
    )


class Grid:
    def __init__(self, poly_ll: dict):
        from rasterio.features import geometry_mask
        from rasterio.transform import from_origin
        from rasterio.warp import transform_geom
        from shapely.geometry import shape

        self.poly_utm = transform_geom("EPSG:4326", DST_CRS, poly_ll)
        self.bounds = snap_bounds(shape(self.poly_utm).bounds)
        left, b, r, t = self.bounds
        self.width, self.height = int(round((r - left) / RES)), int(round((t - b) / RES))
        self.transform = from_origin(left, t, RES, RES)
        self.inside = geometry_mask(
            [self.poly_utm],
            out_shape=(self.height, self.width),
            transform=self.transform,
            invert=True,
            all_touched=False,
        )


def read_tile_window(href: str, grid: Grid, native_res: int):
    """Read the part of one tile COG that overlaps the grid. Returns (row0, col0, array at 20 m) or None.

    For 10 m assets the window is read at 10 m and block-averaged to 20 m (DN; NaN for nodata)."""
    import rasterio
    from rasterio.windows import Window, from_bounds

    last = None
    for attempt in range(4):
        try:
            with rasterio.Env(**GDAL_ENV), rasterio.open("/vsicurl/" + href) as src:
                if src.crs.to_epsg() != 32648:
                    raise RuntimeError(f"unexpected CRS {src.crs} for {href}")
                left, b, r, t = grid.bounds
                il, ib = max(left, src.bounds.left), max(b, src.bounds.bottom)
                ir, it = min(r, src.bounds.right), min(t, src.bounds.top)
                if il >= ir or ib >= it:
                    return None
                win = from_bounds(il, ib, ir, it, transform=src.transform)
                win = Window(
                    int(round(win.col_off)), int(round(win.row_off)), int(round(win.width)), int(round(win.height))
                )
                a = src.read(1, window=win)
            a = block_mean_2x2(a) if native_res == 10 else a.astype(np.float32) if a.dtype != np.uint8 else a
            row0, col0 = int(round((t - it) / RES)), int(round((il - left) / RES))
            return row0, col0, a
        except Exception as exc:  # noqa: BLE001 - retried, then raised
            last = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"read failed {href}: {last}")


def asset_scale_offset(item: dict, key: str) -> tuple[float, float]:
    """(scale, offset) as DECLARED in the asset's raster:bands."""
    rb = (item["assets"][key].get("raster:bands") or [{}])[0]
    if "scale" not in rb:
        raise RuntimeError(f"{item['id']}/{key}: no raster:bands scale; refusing to guess")
    return float(rb["scale"]), float(rb.get("offset", 0.0))


def effective_offset(processing_baseline, boa_offset_applied) -> float:
    """Reflectance offset to apply to Earth Search `sentinel-2-l2a` DNs.

    ESA adds BOA_ADD_OFFSET = -1000 (DN +1000) from processing baseline 04.00. In Earth Search v1 the item flag
    `earthsearch:boa_offset_applied: true` means the offset has ALREADY been applied to the COG pixel values (they
    are on the pre-04.00 scale), although `raster:bands` still declares offset -0.1. Verified on our own data:
    the median red DN over SCL-vegetation pixels of 05.xx items is ~350-720, on the same scale as 03.00 items
    (offset 0); a +1000 offset would put it above 1000. So: flag true -> 0; baseline >= 04.00 without the flag
    -> -0.1; older baselines -> 0.
    """
    if boa_offset_applied is True:
        return 0.0
    if processing_baseline is not None and float(processing_baseline) >= 4.0:
        return -0.1
    return 0.0


class SceneQualityError(RuntimeError):
    """The scene is readable but its kept pixels are not trustworthy (reason in the message)."""


VEG_RED_MAX = 0.10  # red reflectance; clear green vegetation is ~0.02-0.08


def check_offset(red_dn_p1: float | None, offset: float) -> None:
    """Offset consistency from the data itself: with the +1000 offset still in the DNs, even the darkest surfaces
    (water, shadow) have DN > 1000, so the 1st percentile of all valid red DNs is > 1000; without it the darkest
    1 % is well below 1000. Raise when the chosen offset contradicts this."""
    if red_dn_p1 is None:
        return
    if offset == 0.0 and red_dn_p1 > 1000:
        raise RuntimeError(f"1st percentile of red DN is {red_dn_p1:.0f} > 1000: offset still in the DNs but 0 chosen")
    if offset < 0 and red_dn_p1 < 1000:
        raise RuntimeError(
            f"1st percentile of red DN is {red_dn_p1:.0f} < 1000: offset already removed, "
            f"{offset} would be applied twice"
        )


def check_vegetation_red(median_red_reflectance_veg: float | None, threshold: float = VEG_RED_MAX) -> None:
    """Haze test: SCL 'vegetation' pixels whose median red reflectance exceeds the threshold are not clear
    vegetation (thin cloud or haze missed by SCL). Raise SceneQualityError so the scene is skipped with that reason."""
    if median_red_reflectance_veg is not None and median_red_reflectance_veg > threshold:
        raise SceneQualityError(
            f"haze or thin cloud missed by SCL: median red reflectance over SCL vegetation "
            f"{median_red_reflectance_veg:.3f} > {threshold}"
        )


def screen_scene(sid: str, items: list[dict], grid: Grid) -> dict:
    """Read SCL of every tile, mosaic, return kept fraction inside the polygon (cached)."""
    path = CACHE / "screen" / f"{sid}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    scl = np.zeros((grid.height, grid.width), dtype=np.uint8)
    for it in items:
        res = read_tile_window(it["assets"]["scl"]["href"], grid, 20)
        if res is None:
            continue
        r0, c0, a = res
        sub = scl[r0 : r0 + a.shape[0], c0 : c0 + a.shape[1]]
        take = (sub == 0) & (a > 0)
        sub[take] = a[take]
    inside = grid.inside
    n_in = int(inside.sum())
    counts = {SCL_NAMES[k]: int(((scl == k) & inside).sum()) for k in SCL_NAMES}
    out = {
        "scene_id": sid,
        "kept_fraction": round(float((scl_keep_mask(scl) & inside).sum()) / n_in, 4),
        "cloud_fraction_scl": round(float(np.isin(scl, SCL_CLOUD)[inside].sum()) / n_in, 4),
        "nodata_fraction": round(float((scl == 0)[inside].sum()) / n_in, 4),
        "scl_counts": counts,
        "n_inside": n_in,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out), encoding="utf-8")
    return out


def process_scene(sid: str, items: list[dict], grid: Grid) -> dict:
    """Read all bands of every tile, mosaic reflectance, compute indices and polygon statistics (cached)."""
    jpath, npath = CACHE / "scenes" / f"{sid}.json", CACHE / "scenes" / f"{sid}.npz"
    if jpath.exists() and npath.exists():
        return json.loads(jpath.read_text(encoding="utf-8"))
    shape = (grid.height, grid.width)
    scl = np.zeros(shape, dtype=np.uint8)
    refl = {k: np.full(shape, np.nan, dtype=np.float32) for k in BANDS}
    used_offsets = {}
    raw_red_veg = []
    for it in items:
        tile = {}
        res = read_tile_window(it["assets"]["scl"]["href"], grid, 20)
        if res is None:
            continue
        r0, c0, tscl = res
        props = it["properties"]
        offset = effective_offset(props.get("s2:processing_baseline"), props.get("earthsearch:boa_offset_applied"))
        raw = {}
        for key, (asset, native) in BANDS.items():
            scale, declared = asset_scale_offset(it, asset)
            used_offsets[f"{it['id']}:{asset}"] = {
                "scale": scale,
                "declared_offset": declared,
                "applied_offset": offset,
            }
            rr = read_tile_window(it["assets"][asset]["href"], grid, native)
            if rr is None or rr[0] != r0 or rr[1] != c0 or rr[2].shape != tscl.shape:
                raise RuntimeError(f"{it['id']}: {asset} window does not match SCL window")
            raw[key] = (rr[2], scale)
        red_dn, red_scale = raw["red"]
        valid = np.isfinite(red_dn) & (tscl > 0)
        p1 = float(np.percentile(red_dn[valid], 1)) if valid.sum() >= 1000 else None
        veg = (tscl == 4) & np.isfinite(red_dn)
        med_red = float(np.median(red_dn[veg])) if veg.sum() >= 100 else None
        raw_red_veg.append(med_red)
        check_offset(p1, offset)
        check_vegetation_red(None if med_red is None else med_red * red_scale + offset)
        for key, (dn, scale) in raw.items():
            tile[key] = dn_to_reflectance(dn, scale, offset)
        sl = (slice(r0, r0 + tscl.shape[0]), slice(c0, c0 + tscl.shape[1]))
        take = (scl[sl] == 0) & (tscl > 0)
        scl[sl][take] = tscl[take]
        for key in BANDS:
            refl[key][sl][take] = tile[key][take]
    bands_ok = np.all([np.isfinite(refl[k]) for k in BANDS], axis=0)
    kept = scl_keep_mask(scl) & bands_ok & grid.inside
    n_in = int(grid.inside.sum())
    idx = {
        "ndvi": ndvi(refl["red"], refl["nir"]),
        "evi": evi(refl["blue"], refl["red"], refl["nir"]),
        "ndmi": ndmi(refl["nir"], refl["swir16"]),
    }
    stats = {k: masked_stats(v, kept) for k, v in idx.items()}
    nd_i16 = np.where(kept & np.isfinite(idx["ndvi"]), np.round(idx["ndvi"] * NDVI_SCALE), I16_NODATA).astype(np.int16)
    npath.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(npath, ndvi=nd_i16)
    out = {
        "scene_id": sid,
        "valid_fraction": round(float(kept.sum()) / n_in, 4),
        "n_valid": int(kept.sum()),
        "n_inside": n_in,
        "stats": stats,
        "scale_offset": used_offsets,
        "raw_red_dn_median_vegetation": raw_red_veg,
    }
    jpath.write_text(json.dumps(out), encoding="utf-8")
    return out


def trim_item(it: dict) -> dict:
    keep_props = [
        "datetime",
        "platform",
        "eo:cloud_cover",
        "s2:processing_baseline",
        "s2:sequence",
        "earthsearch:boa_offset_applied",
        "s2:product_uri",
        "grid:code",
        "proj:epsg",
        "s2:nodata_pixel_percentage",
        "s2:reflectance_conversion_factor",
        "view:sun_elevation",
    ]
    return {
        "id": it["id"],
        "collection": it.get("collection"),
        "bbox": it.get("bbox"),
        "properties": {k: it["properties"].get(k) for k in keep_props},
        "assets": {
            k: {"href": it["assets"][k]["href"], "raster:bands": it["assets"][k].get("raster:bands")}
            for k in ("blue", "red", "nir", "swir16", "scl")
        },
        "self": f"{STAC_URL}/collections/{COLLECTION}/items/{it['id']}",
    }


def cdse_confirm(scenes: list[dict], bbox, n: int = 5) -> dict:
    """Look up a few used acquisitions in the Copernicus Data Space STAC (discovery only)."""
    out = {
        "endpoint": CDSE_STAC_URL,
        "checked": [],
        "note": "Discovery only; downloading CDSE assets requires a free "
        "Copernicus Data Space Ecosystem account (OAuth token), not used here.",
    }
    for sc in scenes[:n]:
        d = sc["date"]
        try:
            res = http_json(
                "POST",
                f"{CDSE_STAC_URL}/search",
                {
                    "collections": ["sentinel-2-l2a"],
                    "bbox": bbox,
                    "datetime": f"{d}T00:00:00Z/{d}T23:59:59Z",
                    "limit": 20,
                },
                tries=2,
                timeout=60,
            )
            ids = [f["id"] for f in res.get("features", [])]
            out["checked"].append({"date": d, "found": len(ids), "ids": ids[:6]})
        except Exception as exc:  # noqa: BLE001 - optional cross-check
            out["checked"].append({"date": d, "error": str(exc)[:200]})
    return out


def write_composite(season: str, year: int, members: list[dict], grid: Grid, poly_ll: dict) -> dict | None:
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.transform import from_bounds as tf_from_bounds
    from rasterio.warp import Resampling, reproject, transform_bounds

    if not members:
        return None
    stack = []
    for m in members:
        a = np.load(CACHE / "scenes" / f"{m['scene_id']}.npz")["ndvi"].astype(np.float32)
        a[a == I16_NODATA] = np.nan
        stack.append(a / NDVI_SCALE)
    st = np.stack(stack)
    nobs = np.isfinite(st).sum(axis=0)
    with np.errstate(all="ignore"):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            comp = np.nanmedian(st, axis=0).astype(np.float32)
    comp[nobs == 0] = np.nan
    cid = f"{season}-{year}"
    in_poly = grid.inside & np.isfinite(comp)
    stats = masked_stats(comp, grid.inside)
    # GeoTIFF (COG) on the native 20 m UTM grid: band 1 NDVI x 10000, band 2 number of observations
    i16 = np.where(np.isfinite(comp), np.round(comp * NDVI_SCALE), I16_NODATA).astype(np.int16)
    cog_name = f"{season.replace('_', '-')}-{year}-ndvi.tif"
    tmp = CACHE / "composites" / cog_name
    tmp.parent.mkdir(parents=True, exist_ok=True)
    prof = {
        "driver": "COG",
        "width": grid.width,
        "height": grid.height,
        "count": 2,
        "dtype": "int16",
        "crs": DST_CRS,
        "transform": grid.transform,
        "nodata": I16_NODATA,
        "compress": "DEFLATE",
        "predictor": 2,
        "blocksize": 512,
    }
    with rasterio.Env(), rasterio.open(tmp, "w", **prof) as dst:
        dst.write(i16, 1)
        dst.write(np.minimum(nobs, 32767).astype(np.int16), 2)
        dst.update_tags(
            NDVI_SCALE=str(NDVI_SCALE),
            SOURCE="Contains modified Copernicus Sentinel data",
            SEASON=season,
            YEAR=str(year),
            SCENES=",".join(m["scene_id"] for m in members),
            METHOD="per-pixel median of SCL-masked scene NDVI (classes 4,5,6), 20 m",
        )
        dst.set_band_description(1, "NDVI median x10000")
        dst.set_band_description(2, "valid observations")
    size = tmp.stat().st_size
    if size <= COG_TRACK_LIMIT:
        COG_TRACKED_DIR.mkdir(parents=True, exist_ok=True)
        final = COG_TRACKED_DIR / cog_name
        final.write_bytes(tmp.read_bytes())
        tmp.unlink()
    else:
        final = tmp
    # web PNG: reproject to a lon/lat grid (average), clip to the district polygon
    left, b, r, t = grid.bounds
    ll = transform_bounds(DST_CRS, "EPSG:4326", left, b, r, t, densify_pts=21)
    pw, ph = png_grid(ll)
    dst_tf = tf_from_bounds(*ll, pw, ph)
    out = np.full((ph, pw), np.nan, dtype=np.float32)
    reproject(
        comp,
        out,
        src_transform=grid.transform,
        src_crs=DST_CRS,
        dst_transform=dst_tf,
        dst_crs="EPSG:4326",
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=Resampling.average,
    )
    inside_ll = geometry_mask([poly_ll], out_shape=(ph, pw), transform=dst_tf, invert=True, all_touched=False)
    png = encode_png(ndvi_rgba(out, inside_ll))
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    png_name = f"{season.replace('_', '-')}-{year}-ndvi.png"
    (PNG_DIR / png_name).write_bytes(png)
    return {
        "id": cid,
        "season": season,
        "season_label_vi": SEASONS[season],
        "year": year,
        "png": f"media/sat/{png_name}",
        "png_size_px": [pw, ph],
        "bounds": [round(v, 6) for v in ll],
        "bounds_crs": "EPSG:4326 (lon/lat), image rows north to south",
        "n_scenes": len(members),
        "scene_ids": [m["scene_id"] for m in members],
        "scene_dates": [m["date"] for m in members],
        "ndvi_median": stats["median"],
        "ndvi_p25": stats["p25"],
        "ndvi_p75": stats["p75"],
        "n_pixels_with_value": int(in_poly.sum()),
        "coverage_fraction": round(float(in_poly.sum()) / float(grid.inside.sum()), 4),
        "geotiff": str(final.relative_to(ROOT)).replace("\\", "/"),
        "geotiff_bytes": size,
        "geotiff_git_ignored": final.is_relative_to(CACHE),
    }


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ----------------------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-scenes", type=int, default=60)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--no-cdse", action="store_true")
    args = ap.parse_args()
    os.environ.update(GDAL_ENV)
    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    poly_ll, bbox, area_source, geo = load_area()
    grid = Grid(poly_ll)
    print(f"area: {area_source}; grid {grid.width}x{grid.height} @20 m, {int(grid.inside.sum())} pixels inside")

    # 1. discovery (cached)
    CACHE.mkdir(parents=True, exist_ok=True)
    all_items = []
    found = {}
    for name, start, end in PERIODS:
        cp = CACHE / f"stac_{name}_{start}_{end}.json"
        if not cp.exists():
            cp.write_text(json.dumps(stac_search(bbox, start, end)), encoding="utf-8")
        items = json.loads(cp.read_text(encoding="utf-8"))
        found[name] = len(items)
        all_items.extend(items)
    items = dedupe_items(all_items)
    scenes = group_scenes(items)
    print(f"STAC items found {sum(found.values())} ({found}); after dedupe {len(items)}; scenes (dates) {len(scenes)}")

    # 2. screening with SCL only
    screens = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(screen_scene, sid, its, grid): sid for sid, its in scenes.items()}
        for f in as_completed(futs):
            sid = futs[f]
            try:
                screens[sid] = f.result()
            except Exception as exc:  # noqa: BLE001 - recorded as skipped
                screens[sid] = {"scene_id": sid, "error": str(exc)[:300]}
            s = screens[sid]
            print(f"  screen {sid}: kept {s.get('kept_fraction')} cloud {s.get('cloud_fraction_scl')}")

    def period_of(sid: str) -> str:
        d = sid.split("_")[1]
        return "trial_year" if d <= "20210630" else "recent"

    def priority(sid: str) -> tuple:
        d = sid.split("_")[1]
        tier = 0 if period_of(sid) == "trial_year" else (1 if d.startswith("2024") else 2)
        return (tier, -screens[sid].get("kept_fraction", 0))

    passing = [sid for sid in scenes if "error" not in screens[sid] and screens[sid]["kept_fraction"] >= MIN_VALID]
    chosen = sorted(passing, key=priority)[: args.max_scenes]
    skipped = {}
    for sid in scenes:
        s = screens[sid]
        if "error" in s:
            skipped[sid] = f"read error during SCL screening: {s['error']}"
        elif s["kept_fraction"] < MIN_VALID:
            skipped[sid] = (
                f"kept SCL pixels {s['kept_fraction']:.1%} < {MIN_VALID:.0%} inside the district "
                f"(cloud/shadow/cirrus {s['cloud_fraction_scl']:.1%}, no data {s['nodata_fraction']:.1%})"
            )
        elif sid not in chosen:
            skipped[sid] = f"over the scene budget ({args.max_scenes}); lower priority (2023, lower kept fraction)"
    print(f"screen: {len(passing)} pass, {len(chosen)} chosen, {len(skipped)} skipped")

    # 3. full processing of chosen scenes
    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_scene, sid, scenes[sid], grid): sid for sid in chosen}
        for f in as_completed(futs):
            sid = futs[f]
            try:
                results[sid] = f.result()
                r = results[sid]
                print(f"  {sid}: valid {r['valid_fraction']:.2f} NDVI {r['stats']['ndvi']['median']}")
            except SceneQualityError as exc:
                skipped[sid] = f"quality: {exc}"
                print(f"  SKIPPED {sid}: {exc}", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001
                skipped[sid] = f"read error during band processing: {str(exc)[:300]}"
                print(f"  FAILED {sid}: {exc}", file=sys.stderr)
    for sid, r in list(results.items()):
        if r["valid_fraction"] < MIN_VALID:
            skipped[sid] = f"valid pixels with all bands {r['valid_fraction']:.1%} < {MIN_VALID:.0%}"
            del results[sid]

    # 4. tables
    rows = []
    for sid in sorted(scenes, key=lambda s: s.split("_")[1]):
        its = scenes[sid]
        p0 = its[0]["properties"]
        d = date.fromisoformat(p0["datetime"][:10])
        season, syear = season_of(d)
        s = screens.get(sid, {})
        r = results.get(sid)
        row = {
            "scene_id": sid,
            "date": d.isoformat(),
            "datetime_utc": p0["datetime"],
            "platform": p0["platform"],
            "tiles": ";".join(i["properties"].get("grid:code", "") for i in its),
            "item_ids": ";".join(i["id"] for i in its),
            "processing_baselines": ";".join(i["properties"].get("s2:processing_baseline", "") for i in its),
            "boa_offset_applied": ";".join(str(i["properties"].get("earthsearch:boa_offset_applied")) for i in its),
            "cloud_cover_tile_pct": round(sum(i["properties"]["eo:cloud_cover"] for i in its) / len(its), 2),
            "cloud_fraction_scl_district": s.get("cloud_fraction_scl", ""),
            "kept_fraction_scl": s.get("kept_fraction", ""),
            "season": season,
            "season_year": syear,
            "status": "used" if r else "skipped",
            "skip_reason": skipped.get(sid, ""),
        }
        if r:
            row["valid_fraction"] = r["valid_fraction"]
            row["n_valid_pixels"] = r["n_valid"]
            for k in ("ndvi", "evi", "ndmi"):
                for q in ("median", "p25", "p75"):
                    row[f"{k}_{q}"] = r["stats"][k][q]
        rows.append(row)
    cols = [
        "scene_id",
        "date",
        "datetime_utc",
        "platform",
        "tiles",
        "item_ids",
        "processing_baselines",
        "boa_offset_applied",
        "cloud_cover_tile_pct",
        "cloud_fraction_scl_district",
        "kept_fraction_scl",
        "valid_fraction",
        "n_valid_pixels",
        "ndvi_median",
        "ndvi_p25",
        "ndvi_p75",
        "evi_median",
        "evi_p25",
        "evi_p75",
        "ndmi_median",
        "ndmi_p25",
        "ndmi_p75",
        "season",
        "season_year",
        "status",
        "skip_reason",
    ]
    import csv

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_SCENES, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({c: ("" if row.get(c) is None else row.get(c, "")) for c in cols})
    used_items = [trim_item(i) for sid in results for i in scenes[sid]]
    OUT_ITEMS.write_text(
        json.dumps(
            {
                "stac_api": STAC_URL,
                "collection": COLLECTION,
                "search_bbox": bbox,
                "periods": PERIODS,
                "query": {"eo:cloud_cover": {"lt": CLOUD_MAX}},
                "retrieved_at": started,
                "items": used_items,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    # offset sanity check: raw red DN over SCL vegetation by baseline group (+1000 expected for >= 04.00)
    dn_check = {"lt_04": [], "ge_04": []}
    for sid, r in results.items():
        for it, v in zip(scenes[sid], r["raw_red_dn_median_vegetation"], strict=False):
            grp = "ge_04" if float(it["properties"]["s2:processing_baseline"]) >= 4 else "lt_04"
            if v is not None:
                dn_check[grp].append(v)
    dn_summary = {g: (round(float(np.median(v)), 1) if v else None) for g, v in dn_check.items()}
    offsets_seen = sorted(
        {
            (v["scale"], v["declared_offset"], v["applied_offset"])
            for r in results.values()
            for v in r["scale_offset"].values()
        }
    )

    # 5. composites
    used_rows = [r for r in rows if r["status"] == "used"]
    composites = []
    for season, year in COMPOSITES:
        members = [r for r in used_rows if r["season"] == season and r["season_year"] == year]
        c = write_composite(season, year, members, grid, poly_ll)
        if c:
            composites.append(c)
            print(
                f"composite {c['id']}: {c['n_scenes']} scenes, NDVI median {c['ndvi_median']} "
                f"(p25 {c['ndvi_p25']}, p75 {c['ndvi_p75']}), coverage {c['coverage_fraction']:.0%}"
            )
        else:
            composites.append(
                {
                    "id": f"{season}-{year}",
                    "season": season,
                    "year": year,
                    "png": None,
                    "n_scenes": 0,
                    "ndvi_median": None,
                    "status": "UNAVAILABLE",
                    "reason": "no used scene in this season",
                }
            )
            print(f"composite {season}-{year}: no scene")

    cdse = None if args.no_cdse else cdse_confirm(used_rows, bbox)

    formulas = {
        "reflectance": "rho = DN * 0.0001 + offset; offset 0 when earthsearch:boa_offset_applied is true (pixel "
        "values already offset-corrected; raster:bands still declares -0.1), -0.1 for baseline >= "
        "04.00 without that flag, 0 for older baselines",
        "ndvi": "(B08 - B04) / (B08 + B04)",
        "evi": "2.5 * (B08 - B04) / (B08 + 6 * B04 - 7.5 * B02 + 1)",
        "ndmi": "(B08 - B11) / (B08 + B11)",
        "resampling": "B02, B04, B08 (10 m): mean of each aligned 2x2 block of DN -> 20 m; missing if any sub-pixel "
        "is nodata",
        "undefined": "an index is undefined (not computed) where its denominator <= 0",
        "composite": "per-pixel median of the season's used scene NDVI; median/p25/p75 then taken over the district",
        "web_png": f"composite reprojected to EPSG:4326 with average resampling (<= {PNG_MAX} px), ramp NDVI <= 0.0 "
        "#B5623E, 0.4 #E9BC57, >= 0.8 #2F5A37 (linear in sRGB), transparent outside the district or "
        "where no valid pixel; water (river, ponds, flooded paddies) has NDVI <= 0 and shares the terracotta colour "
        "of bare soil",
    }
    limitations = {
        "vi": "Pixel 20 m trộn nhiều thửa ruộng, bờ, đường và nhà. NDVI chỉ đo độ xanh của mặt đất; không phải năng "
        "suất, bệnh hay độ ẩm đất. Mây và bóng mây làm mất nhiều ngày trong mùa mưa. Ảnh của ngày có mây che "
        "một phần chỉ đại diện cho phần nhìn thấy. Mặt nước (sông, ao, ruộng ngập) có NDVI thấp nên cùng màu đất trống. Không phải số đo tại ruộng.",
        "en": "20 m pixels mix fields, bunds, roads and houses. NDVI is greenness of the land surface, not yield, "
        "disease or soil moisture. Clouds and shadows remove many rainy-season dates; a partly cloudy date "
        "describes only the visible part. Water (river, ponds, flooded paddies) has low NDVI and shares the bare-soil "
        "colour. Not a field measurement.",
    }
    veg = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": f"Copernicus Sentinel-2 MSI Level-2A via Element 84 Earth Search ({STAC_URL}, collection "
        f"{COLLECTION}), COGs on AWS Open Data (s3://sentinel-cogs)",
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "cite_as": CITE_AS,
        "attribution": "Contains modified Copernicus Sentinel data 2020-2024",
        "area": area_source,
        "bbox": bbox,
        "grid": {
            "crs": DST_CRS,
            "resolution_m": RES,
            "bounds": grid.bounds,
            "width": grid.width,
            "height": grid.height,
        },
        "validation_status": "DERIVED",
        "is_field_measurement": False,
        "scenes": [
            {
                "scene_id": r["scene_id"],
                "date": r["date"],
                "cloud": r["cloud_cover_tile_pct"],
                "cloud_district_scl": r["cloud_fraction_scl_district"],
                "valid_fraction": r["valid_fraction"],
                "ndvi_median": r["ndvi_median"],
                "ndvi_p25": r["ndvi_p25"],
                "ndvi_p75": r["ndvi_p75"],
                "evi_median": r["evi_median"],
                "ndmi_median": r["ndmi_median"],
                "season": r["season"],
                "season_year": r["season_year"],
            }
            for r in used_rows
        ],
        "composites": composites,
        "formulas": formulas,
        "scl_kept": [{"class": k, "name": SCL_NAMES[k]} for k in SCL_KEEP],
        "scl_dropped": [{"class": k, "name": SCL_NAMES[k]} for k in SCL_NAMES if k not in SCL_KEEP],
        "seasons": {"spring": "01-01..05-31", "summer_autumn": "06-01..09-15", "autumn_winter": "09-16..12-31"},
        "limitations": limitations,
    }
    OUT_VEG.write_text(json.dumps(veg, ensure_ascii=False, indent=1), encoding="utf-8")

    n_found = sum(found.values())
    manifest = {
        "dataset_id": "sentinel2_l2a_do_luong_vi",
        "title": {
            "vi": "Chỉ số thực vật Sentinel-2 L2A (NDVI, EVI, NDMI, 20 m) trên huyện Đô Lương (cũ)",
            "en": "Sentinel-2 L2A vegetation indices (NDVI, EVI, NDMI, 20 m) over the former Đô Lương district",
        },
        "provider": "ESA Copernicus (producer); Sinergise and Element 84 (COG conversion, Earth Search STAC); AWS "
        "Open Data (host)",
        "source_id": "sentinel-2-l2a (Earth Search v1)",
        "source_url": f"{STAC_URL}/collections/{COLLECTION}",
        "license": f"{LICENSE} ({LICENSE_URL})",
        "source_revision": "processing baselines used: "
        + ", ".join(sorted({r["processing_baselines"] for r in used_rows})),
        "retrieved_at": started,
        "temporal_coverage": "2020-06-01..2021-06-30 and 2023-01-01..2024-12-31 (dates with eo:cloud_cover < 60)",
        "spatial_resolution": "20 m (10 m bands block-averaged), EPSG:32648",
        "geometry_crs": DST_CRS,
        "variables": ["ndvi", "evi", "ndmi", "valid_fraction", "cloud_cover"],
        "missing_policy": "Pixels outside SCL classes 4/5/6, with any band nodata, or with an undefined index are "
        "excluded, never filled; scenes with < 20 % valid pixels in the district are skipped and "
        "listed with the reason; composite pixels without any valid scene are transparent.",
        "allowed_use": {
            "vi": "Mô tả độ xanh theo mùa trên toàn huyện Đô Lương (cũ); không chẩn đoán từng ruộng.",
            "en": "Describe seasonal greenness across the former Đô Lương district; not a per-field diagnosis.",
        },
        "version_sha256": sha256_file(OUT_SCENES),
        "ingestion_status": "INGESTED" if all(c.get("png") for c in composites) else "PARTIAL",
        "is_field_measurement": False,
        "notes": [
            {
                "vi": "Pixel 20 m trộn nhiều thửa ruộng; NDVI là độ xanh, không phải năng suất, bệnh hay độ ẩm đất.",
                "en": "20 m pixels mix fields; NDVI is greenness, not yield, disease or soil moisture.",
            },
            {
                "vi": "Ảnh trước 2022 lấy bản xử lý lại N05.00 khi có (cùng thuật toán với 2023-2024).",
                "en": "Pre-2022 dates use the N05.00 reprocessing when it exists (same processor family as 2023-2024).",
            },
            {
                "vi": "Mùa tách không chồng lấn: tháng 9 chia ở ngày 15.",
                "en": "Seasons do not overlap: September is split at day 15.",
            },
            {
                "vi": "Vùng là huyện Đô Lương cũ (bỏ cấp huyện từ 7/2025).",
                "en": "The area is the former Đô Lương district (districts abolished July 2025).",
            },
        ],
        "counts": {
            "stac_items_found": n_found,
            "stac_items_by_period": found,
            "items_after_dedupe": len(items),
            "scenes_found": len(scenes),
            "scenes_passing_screen": len(passing),
            "scenes_used": len(results),
            "scenes_skipped": len(scenes) - len(results),
            "max_scenes": args.max_scenes,
        },
        "offset_check": {
            "scale_declared_applied_seen": offsets_seen,
            "median_raw_red_dn_over_scl_vegetation_by_baseline": dn_summary,
            "finding": "Earth Search items with earthsearch:boa_offset_applied=true already have the "
            "-1000 BOA offset applied to their pixel values although raster:bands declares "
            "offset -0.1; applying it again drove red reflectance to ~0 and NDVI above 1 in a "
            "first run. The applied offset is therefore 0 for those items (checked per tile: "
            "1st percentile of red DN must be < 1000 when offset 0 is used).",
            "haze_test": "tiles whose SCL-vegetation median red reflectance > 0.10 are skipped",
        },
        "cdse_cross_check": cdse,
        "files": {
            "scenes": "data/raw/sentinel2/scenes.csv",
            "stac_items": "data/raw/sentinel2/stac_items.json",
            "canonical": "data/canonical/vegetation.json",
            "pngs": [c.get("png") for c in composites],
            "geotiffs": [c.get("geotiff") for c in composites],
            "script": "pipeline/fetch_sentinel2.py",
        },
        "skipped": [{"scene_id": sid, "reason": rsn} for sid, rsn in sorted(skipped.items())],
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"done: {len(results)} used, {len(scenes) - len(results)} skipped; offset check {dn_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
