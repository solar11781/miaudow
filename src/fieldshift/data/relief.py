"""NASA SRTM shaded relief for the Nghe An data-room map (R-N12, method R-M29).

Plain words: SRTM is a height grid (one height every 3 arc seconds, about 90 m). Hill shading turns heights into a
grey picture: ground that faces the sun is light, ground that faces away is dark. The shading is Horn (1981): the
slope at a point comes from the 3 x 3 heights around it, and the grey level is how much light a matt surface with
that slope reflects. The picture shows height only; it says nothing about where water reaches.
"""

from __future__ import annotations

import io
import math
import zipfile

import numpy as np

DATASET_SOURCE_ID = "nasa_srtmgl3"  # source_id column of data/MANIFEST.csv
HGT_SAMPLES = 1201  # SRTMGL3 tile: 1 degree at 3 arc seconds, edges shared with the next tile (CMR record, 2026-11-16)
SAMPLES_PER_DEGREE = 1200
VOID = -32768  # SRTM "no data" value
# Horn (1981), Proc. IEEE 69(1):14-47: reflectance of a matt surface; 315 and 45 degrees are the conventional sun
# (GDAL gdaldem hillshade default azimuth 315).
SUN_AZIMUTH_DEG = 315.0
SUN_ALTITUDE_DEG = 45.0
EARTH_RADIUS_M = 6371008.7714  # IUGG mean radius R1 of GRS80 (Moritz 1980)
# Grid3D.tsx: the map box is the cell grid plus half a POWER cell (0.5 deg lat x 0.625 deg lon) on every side,
# and longitude is drawn scaled by cos(19.3 deg).
MARGIN_LON_DEG = 0.3125
MARGIN_LAT_DEG = 0.25
MAP_K_LON = math.cos(math.radians(19.3))
LP_DAAC_BASE = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL3.003"

Box = tuple[float, float, float, float]  # west, south, east, north in degrees


def map_box(cells: list[tuple[float, float]]) -> Box:
    """The map box for (lat, lon) cell centres, as Grid3D draws it."""
    lats = [c[0] for c in cells]
    lons = [c[1] for c in cells]
    return (
        min(lons) - MARGIN_LON_DEG,
        min(lats) - MARGIN_LAT_DEG,
        max(lons) + MARGIN_LON_DEG,
        max(lats) + MARGIN_LAT_DEG,
    )


def tile_name(lat: int, lon: int) -> str:
    """Name of the 1 degree tile whose south-west corner is (lat, lon), for example N19E105."""
    return f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}{'E' if lon >= 0 else 'W'}{abs(lon):03d}"


def tiles_for_box(box: Box) -> list[str]:
    west, south, east, north = box
    return [
        tile_name(lat, lon)
        for lat in range(math.floor(south), math.ceil(north))
        for lon in range(math.floor(west), math.ceil(east))
    ]


def tile_url(name: str) -> str:
    return f"{LP_DAAC_BASE}/{name}.SRTMGL3.hgt/{name}.SRTMGL3.hgt.zip"


def read_hgt_zip(raw: bytes, name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        return z.read(f"{name}.hgt")


def read_hgt(raw: bytes, name: str) -> np.ndarray:
    """Heights in metres, row 0 = northern edge. Fails on a wrong size or on void cells."""
    if len(raw) != HGT_SAMPLES * HGT_SAMPLES * 2:
        raise ValueError(f"tile {name}: {len(raw)} bytes, expected {HGT_SAMPLES * HGT_SAMPLES * 2}")
    grid = np.frombuffer(raw, dtype=">i2").reshape(HGT_SAMPLES, HGT_SAMPLES).astype(np.int16)
    if (grid == VOID).any():
        raise ValueError(f"tile {name}: contains void cells")
    return grid


def mosaic_crop(tiles: dict[str, np.ndarray], box: Box) -> tuple[np.ndarray, tuple[float, float]]:
    """Heights over the box plus one sample all round (for the 3 x 3 window); returns (heights, (west, north))."""
    west, south, east, north = box
    lat0, lat1 = math.floor(south), math.ceil(north) - 1
    lon0, lon1 = math.floor(west), math.ceil(east) - 1
    mosaic = np.zeros(
        ((lat1 - lat0 + 1) * SAMPLES_PER_DEGREE + 1, (lon1 - lon0 + 1) * SAMPLES_PER_DEGREE + 1), np.int16
    )
    for lat in range(lat0, lat1 + 1):
        for lon in range(lon0, lon1 + 1):
            name = tile_name(lat, lon)
            if name not in tiles:
                raise ValueError(f"tile {name} is missing for the box {box}")
            r, c = (lat1 - lat) * SAMPLES_PER_DEGREE, (lon - lon0) * SAMPLES_PER_DEGREE
            mosaic[r : r + HGT_SAMPLES, c : c + HGT_SAMPLES] = tiles[name]
    row0 = round((lat1 + 1 - north) * SAMPLES_PER_DEGREE) - 1
    row1 = round((lat1 + 1 - south) * SAMPLES_PER_DEGREE) + 1
    col0 = round((west - lon0) * SAMPLES_PER_DEGREE) - 1
    col1 = round((east - lon0) * SAMPLES_PER_DEGREE) + 1
    step = 1 / SAMPLES_PER_DEGREE
    return mosaic[row0 : row1 + 1, col0 : col1 + 1], (west - step, north + step)


def cell_size_m(lats: np.ndarray) -> tuple[float, np.ndarray]:
    """(north-south, east-west per row) spacing in metres of a 3 arc second grid at the given latitudes."""
    dy = EARTH_RADIUS_M * math.radians(1 / SAMPLES_PER_DEGREE)
    return dy, dy * np.cos(np.radians(lats))


def horn_slopes(z: np.ndarray, dx_m: np.ndarray, dy_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Horn (1981) slopes (east, north) of the interior; z rows run north to south, dx_m has one value per row of z."""
    a, b, c = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    d, f = z[1:-1, :-2], z[1:-1, 2:]
    g, h, i = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
    p = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * dx_m[1:-1, None])
    q = ((a + 2 * b + c) - (g + 2 * h + i)) / (8 * dy_m)
    return p, q


def hillshade(
    z: np.ndarray,
    dx_m: np.ndarray,
    dy_m: float,
    azimuth_deg: float = SUN_AZIMUTH_DEG,
    altitude_deg: float = SUN_ALTITUDE_DEG,
) -> np.ndarray:
    """Reflectance 0..1 of the interior (Horn 1981): dot of the surface normal and the unit vector to the sun."""
    p, q = horn_slopes(z.astype(float), dx_m, dy_m)
    az, alt = math.radians(azimuth_deg), math.radians(altitude_deg)
    sx, sy, sz = math.cos(alt) * math.sin(az), math.cos(alt) * math.cos(az), math.sin(alt)
    return np.clip((-p * sx - q * sy + sz) / np.sqrt(1 + p * p + q * q), 0.0, 1.0)


def _area_weights(n_in: int, n_out: int) -> np.ndarray:
    edges = np.linspace(0, n_in, n_out + 1)
    lo = np.maximum(edges[:-1, None], np.arange(n_in)[None, :])
    hi = np.minimum(edges[1:, None], np.arange(1, n_in + 1)[None, :])
    w = np.clip(hi - lo, 0, None)
    return w / w.sum(axis=1, keepdims=True)


def resample(a: np.ndarray, out_w: int, out_h: int) -> np.ndarray:
    """Area-average resampling to out_h rows and out_w columns."""
    return _area_weights(a.shape[0], out_h) @ a @ _area_weights(a.shape[1], out_w).T


def image_size(box: Box, width: int) -> tuple[int, int]:
    """(width, height) of the picture with the proportions Grid3D draws the box in."""
    west, south, east, north = box
    return width, round(width * (north - south) / ((east - west) * MAP_K_LON))


def to_grey(shade: np.ndarray) -> np.ndarray:
    return np.round(shade * 255).astype(np.uint8)


def manifest_row(path: str, name: str, url: str, retrieved_on: str, sha256: str) -> list[str]:
    return [
        path,
        DATASET_SOURCE_ID,
        "",
        f"SRTMGL3 v003 tile {name}",
        url,
        retrieved_on,
        "scripts/build_relief.py (Earthdata download)",
        sha256,
    ]


def relief_grey(tiles: dict[str, np.ndarray], box: Box, width: int) -> np.ndarray:
    """Greyscale hillshade of the box, `width` pixels wide."""
    z, (_, north) = mosaic_crop(tiles, box)
    lats = north - np.arange(z.shape[0]) / SAMPLES_PER_DEGREE
    dy, dx = cell_size_m(lats)
    w, h = image_size(box, width)
    return to_grey(resample(hillshade(z, dx, dy), w, h))
