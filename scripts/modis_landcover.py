"""Download NASA MODIS MCD12C1 v061 yearly land cover, keep a Vietnam subset, delete the global file.

Why: farmland-weighted province weather (D-26, D-27) needs the cropland share per 0.05 deg square for every
harvest year. Each global file is about 1.24 GB; we keep only a box around Vietnam (all 17 IGBP percent layers), so the
whole 2001-2024 series fits in a few MB. Provenance (granule id, URL, sha256 of the original file) is appended to
data/MANIFEST.csv so anyone can re-download and verify.

Auth: Earthdata Login. Set EARTHDATA_TOKEN to an Earthdata user token (fieldshift.data.earthdata sends it only to NASA
Earthdata hosts over https); without it, only a network that adds the login itself works.

Usage: python -I scripts/modis_landcover.py 2001 2024
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np

from fieldshift.data.earthdata import earthdata_opener
from fieldshift.data.manifest import append_rows

try:
    from pyhdf.SD import SD, SDC
except ImportError:  # pyhdf is installed only for the download step (reproduce.sh); the tests import the rest
    SD = SDC = None

CMR = (
    "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=MCD12C1&version=061"
    "&temporal={y}-01-01T00:00:00Z,{y}-01-01T23:59:59Z&page_size=5"
)
# Vietnam bounding box with margin (degrees). Grid: 0.05 deg, row 0 at 90 N, column 0 at 180 W (verified 2026-11-11).
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 8.0, 24.0, 102.0, 110.0
CELL = 0.05
RAW_DIR = Path("data/raw/modis")
OUT_DIR = Path("data/interim/modis_vn")
MANIFEST = Path("data/MANIFEST.csv")


def subset_indices(
    lat_min: float = LAT_MIN,
    lat_max: float = LAT_MAX,
    lon_min: float = LON_MIN,
    lon_max: float = LON_MAX,
    cell: float = CELL,
) -> tuple[int, int, int, int]:
    """Row/column slice bounds of the global 0.05 deg grid covering the box (row 0 = 90 N, col 0 = 180 W)."""
    r0 = round((90 - lat_max) / cell)
    r1 = round((90 - lat_min) / cell)
    c0 = round((lon_min + 180) / cell)
    c1 = round((lon_max + 180) / cell)
    return r0, r1, c0, c1


def pixel_index(
    lat: float, lon: float, lat_max: float = 90.0, lon_min: float = -180.0, cell: float = CELL
) -> tuple[int, int]:
    """Row/col of the pixel containing (lat, lon) in a grid whose top-left corner is (lat_max, lon_min).

    A point exactly on a pixel border belongs to the pixel south/east of it. A small epsilon removes floating-point
    noise such as (90 - 18.9) / 0.05 = 1421.9999999999998, which caused a one-pixel mismatch on 2026-11-11.
    """
    eps = 1e-9
    return int(np.floor((lat_max - lat) / cell + eps)), int(np.floor((lon - lon_min) / cell + eps))


def _require_https(url: str) -> None:
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError(f"only https URLs are allowed, got {url!r}")


def granule_url(year: int) -> tuple[str, str]:
    url = CMR.format(y=year)
    _require_https(url)
    with urllib.request.build_opener().open(url, timeout=60) as resp:
        feed = json.load(resp)["feed"]["entry"]
    if len(feed) != 1:
        raise RuntimeError(f"expected 1 granule for {year}, found {len(feed)}")
    entry = feed[0]
    urls = [
        link["href"] for link in entry["links"] if link["href"].startswith("https") and link["href"].endswith(".hdf")
    ]
    return entry["producer_granule_id"] if "producer_granule_id" in entry else entry["title"], urls[0]


def download(url: str, dest: Path) -> str:
    """Download through the Earthdata Login redirect (cookies kept), return sha256 of the file.

    A reply that ends before its Content-Length is refused and leaves no file (data are never guessed).
    """
    opener = earthdata_opener()
    opener.addheaders = [("User-Agent", "fieldshift-research/0.1")]
    h = hashlib.sha256()
    tmp = dest.with_suffix(".part")
    try:
        with opener.open(url, timeout=600) as resp, open(tmp, "wb") as fh:
            host = urllib.parse.urlparse(resp.geturl()).hostname  # the full URL may carry a one-time login code
            if "html" in resp.headers.get("Content-Type", ""):
                raise RuntimeError(f"got an HTML page instead of data from {host} (login failed?)")
            expected, size = resp.headers.get("Content-Length"), 0
            while chunk := resp.read(1 << 20):
                h.update(chunk)
                fh.write(chunk)
                size += len(chunk)
        if expected is not None and size != int(expected):
            raise RuntimeError(f"download cut off: {size} of {expected} bytes from {host}")
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(dest)
    return h.hexdigest()


def reused_sha256(raw: Path, manifest: Path = MANIFEST) -> str:
    """sha256 of a raw file already on disk; it must match a data/MANIFEST.csv row for its path (CR-07)."""
    sha = hashlib.sha256(raw.read_bytes()).hexdigest()
    with open(manifest, encoding="utf-8", newline="") as f:
        recorded = {r["sha256"] for r in csv.DictReader(f) if r["path"] == raw.as_posix()}
    if sha not in recorded:
        raise ValueError(f"{raw.as_posix()}: sha256 {sha[:12]} is not in {manifest} (re-download it)")
    return sha


def extract_vietnam(hdf_path: Path) -> tuple[np.ndarray, dict]:
    if SD is None:
        raise ImportError("pyhdf is needed to read the HDF4 files: pip install pyhdf==0.11.7")
    ds = SD(str(hdf_path), SDC.READ).select("Land_Cover_Type_1_Percent")
    r0, r1, c0, c1 = subset_indices()
    data = np.asarray(ds[r0:r1, c0:c1, :], dtype=np.uint8)
    attrs = ds.attributes()
    layers = {i: attrs[f"Layer {i}"] for i in range(data.shape[2])}
    return data, layers


def process_year(year: int, keep_raw: bool = False) -> None:
    out = OUT_DIR / f"MCD12C1_{year}_vn.npz"
    if out.exists():
        print(f"{year}: subset exists, skipping")
        return
    granule, url = granule_url(year)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = RAW_DIR / Path(url).name
    sha = download(url, raw) if not raw.exists() else reused_sha256(raw)
    data, layers = extract_vietnam(raw)
    r0, r1, c0, c1 = subset_indices()
    part = out.with_name(out.stem + ".part.npz")  # written in full first, so a stop never leaves a half subset
    np.savez_compressed(
        part,
        percent=data,
        layer_names=np.array([layers[i] for i in sorted(layers)]),
        lat_max=LAT_MAX,
        lon_min=LON_MIN,
        cell=CELL,
        rows=(r0, r1),
        cols=(c0, c1),
        year=year,
        source_sha256=sha,
        granule=granule,
    )
    part.replace(out)
    row = [
        raw.as_posix(),
        "modis_mcd12c1",
        granule,
        f"MCD12C1 v061 {year} (global; Vietnam subset in {out.as_posix()})",
        url,
        date.today().isoformat(),
        "scripts/modis_landcover.py",
        sha,
    ]
    append_rows(MANIFEST, [row])
    if not keep_raw:
        raw.unlink()
    print(f"{year}: {data.shape} saved to {out}; sha256 {sha[:12]}")


if __name__ == "__main__":
    first, last = int(sys.argv[1]), int(sys.argv[2])
    for y in range(first, last + 1):
        process_year(y)
