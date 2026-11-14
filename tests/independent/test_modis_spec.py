"""Independent specification tests for scripts/modis_landcover.py (MODIS MCD12C1 Vietnam subsets).

Written without reading the implementation (D-30). Every expectation cites its source.
Grid facts (external, MCD12C1 v061): global 0.05 deg grid, 3600 rows x 7200 columns, row 0 starts at 90 N,
column 0 starts at 180 W; Land_Cover_Type_1_Percent has 17 layers (IGBP classes 0-16) in percent;
layer 12 = croplands, layer 14 = cropland/natural vegetation mosaic.
"""

from __future__ import annotations

import csv
import importlib.util
import math
import re
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "modis_landcover.py"
SUBSET_DIR = ROOT / "data" / "interim" / "modis_vn"
MANIFEST = ROOT / "data" / "MANIFEST.csv"
NPZ_FILES = sorted(SUBSET_DIR.glob("MCD12C1_*_vn.npz")) if SUBSET_DIR.exists() else []
needs_npz = pytest.mark.skipif(not NPZ_FILES, reason="MODIS Vietnam subsets not present")


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("modis_landcover_under_test", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- constants


def test_vietnam_box_constants(mod):
    # Source: D-27: Vietnam box 8-24 N, 102-110 E; MCD12C1 cell 0.05 deg (external fact)
    assert pytest.approx(8.0) == mod.LAT_MIN
    assert pytest.approx(24.0) == mod.LAT_MAX
    assert pytest.approx(102.0) == mod.LON_MIN
    assert pytest.approx(110.0) == mod.LON_MAX
    assert pytest.approx(0.05) == mod.CELL


# ---------------------------------------------------------------- subset_indices


def test_subset_indices_vietnam_box(mod):
    # Source: grid fact: row = (90 - lat)/0.05, col = (lon + 180)/0.05 -> 24 N: 1320, 8 N: 1640, 102 E: 5640, 110 E: 5800
    assert tuple(int(v) for v in mod.subset_indices(8.0, 24.0, 102.0, 110.0, 0.05)) == (1320, 1640, 5640, 5800)


def test_subset_indices_from_module_constants(mod):
    # Source: D-27 box + grid fact (same numbers as above, through the module's own constants)
    got = mod.subset_indices(mod.LAT_MIN, mod.LAT_MAX, mod.LON_MIN, mod.LON_MAX, mod.CELL)
    assert tuple(int(v) for v in got) == (1320, 1640, 5640, 5800)


def test_subset_indices_whole_globe(mod):
    # Source: grid fact: 3600 x 7200 global grid
    assert tuple(int(v) for v in mod.subset_indices(-90.0, 90.0, -180.0, 180.0, 0.05)) == (0, 3600, 0, 7200)


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        # Nghe An-sized box: 18-20 N, 104-106 E -> rows (90-20)/0.05=1400 .. (90-18)/0.05=1440; cols 5680 .. 5720
        ((18.0, 20.0, 104.0, 106.0), (1400, 1440, 5680, 5720)),
        # decimal-literal edges that are not exact in binary: 10.3 N .. 19.25 N, 105.3 E .. 105.65 E
        ((10.3, 19.25, 105.3, 105.65), (1415, 1594, 5706, 5713)),
        # southern/western hemisphere: 10 S .. 0, 70 W .. 60 W
        ((-10.0, 0.0, -70.0, -60.0), (1800, 2000, 2200, 2400)),
    ],
)
def test_subset_indices_grid_aligned_boxes(mod, box, expected):
    # Source: grid fact (row 0 at 90 N, col 0 at 180 W, 0.05 deg); edges on grid lines must give exact integers
    lat_min, lat_max, lon_min, lon_max = box
    got = tuple(int(v) for v in mod.subset_indices(lat_min, lat_max, lon_min, lon_max, 0.05))
    assert got == expected


def test_subset_shape_matches_box_size(mod):
    # Source: grid fact: a 16 x 8 degree box at 0.05 deg is 320 rows x 160 columns
    r0, r1, c0, c1 = (int(v) for v in mod.subset_indices(8.0, 24.0, 102.0, 110.0, 0.05))
    assert (r1 - r0, c1 - c0) == (320, 160)


# ---------------------------------------------------------------- pixel_index (interior points)


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (89.99, -179.99, (0, 0)),  # first pixel: top-left corner of the globe
        (-89.99, 179.99, (3599, 7199)),  # last pixel: bottom-right corner
        (18.92, 105.63, (1421, 5712)),  # Nghe An: (90-18.92)/0.05 = 1421.6, (285.63)/0.05 = 5712.6
        (0.02, 0.02, (1799, 3600)),  # just north-east of (0, 0)
        (-0.02, -0.02, (1800, 3599)),  # just south-west of (0, 0)
        (10.31, 105.61, (1593, 5712)),  # Mekong Delta: 79.69/0.05 = 1593.8, 285.61/0.05 = 5712.2
    ],
)
def test_pixel_index_global_interior(mod, lat, lon, expected):
    # Source: grid fact: row = floor((90 - lat)/0.05), col = floor((lon + 180)/0.05) for points inside a pixel
    assert tuple(int(v) for v in mod.pixel_index(lat, lon)) == expected


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (23.99, 102.01, (0, 0)),  # top-left pixel of the Vietnam box
        (8.01, 109.99, (319, 159)),  # bottom-right pixel of the Vietnam box
        (18.92, 105.63, (101, 72)),  # (24-18.92)/0.05 = 101.6, (105.63-102)/0.05 = 72.6
    ],
)
def test_pixel_index_in_subset_grid(mod, lat, lon, expected):
    # Source: interface spec: grid with top-left corner (lat_max, lon_min); grid fact for the D-27 box
    got = mod.pixel_index(lat, lon, lat_max=24.0, lon_min=102.0, cell=0.05)
    assert tuple(int(v) for v in got) == expected


@pytest.mark.parametrize(
    ("lat", "lon"), [(18.92, 105.63), (10.31, 105.61), (21.03, 105.83), (12.24, 109.17), (8.6, 104.7)]
)
def test_pixel_index_subset_equals_global_minus_offset(mod, lat, lon):
    # Source: D-27 (subset is a slice of the global array) + grid fact
    r0, _, c0, _ = (int(v) for v in mod.subset_indices(8.0, 24.0, 102.0, 110.0, 0.05))
    gr, gc = (int(v) for v in mod.pixel_index(lat, lon))
    sr, sc = (int(v) for v in mod.pixel_index(lat, lon, lat_max=24.0, lon_min=102.0, cell=0.05))
    assert (sr, sc) == (gr - r0, gc - c0)


# ---------------------------------------------------------------- pixel_index (points exactly on pixel borders)
# Which side owns a border point is not stated in the docs (spec gap). D-27 only says pixel_index() "uses one
# documented rule". So these tests only require: (a) the answer is one of the two touching pixels and (b) the same
# side is chosen at every border, whatever floating-point error the decimal literal carries.


def _border_lats():
    # decimal literals as a user would type them, e.g. 19.25, 10.3, every 0.05 deg line inside the D-27 box
    return [round(24.0 - k * 0.05, 2) for k in range(1, 320)]


def _border_lons():
    return [round(102.0 + k * 0.05, 2) for k in range(1, 160)]


def test_pixel_index_lat_border_rule_is_consistent(mod):
    # Source: D-27 ("one documented rule" for border points) + grid fact (border k separates rows k-1 and k)
    sides = set()
    for k, lat in enumerate(_border_lats(), start=1):
        r, _ = (int(v) for v in mod.pixel_index(lat, 105.63, lat_max=24.0, lon_min=102.0, cell=0.05))
        assert r in (k - 1, k), (lat, r)
        sides.add(r - k)
    assert len(sides) == 1, f"inconsistent border rule across latitudes: {sides}"


def test_pixel_index_lon_border_rule_is_consistent(mod):
    # Source: D-27 ("one documented rule" for border points) + grid fact (border k separates cols k-1 and k)
    sides = set()
    for k, lon in enumerate(_border_lons(), start=1):
        _, c = (int(v) for v in mod.pixel_index(18.92, lon, lat_max=24.0, lon_min=102.0, cell=0.05))
        assert c in (k - 1, k), (lon, c)
        sides.add(c - k)
    assert len(sides) == 1, f"inconsistent border rule across longitudes: {sides}"


def test_pixel_index_global_border_rule_is_consistent(mod):
    # Source: D-27 + grid fact, on the global grid (lines 24 N .. 8 N are borders 1320 .. 1640)
    sides = set()
    for lat in _border_lats():
        k = round((90.0 - lat) / 0.05)
        r, _ = (int(v) for v in mod.pixel_index(lat, 105.63))
        assert r in (k - 1, k), (lat, r)
        sides.add(r - k)
    assert len(sides) == 1


# ---------------------------------------------------------------- real subsets


def _npz_year(path: Path) -> int:
    return int(re.search(r"MCD12C1_(\d{4})_vn\.npz$", path.name).group(1))


def _manifest_sha_by_year() -> dict[int, str]:
    out = {}
    if not MANIFEST.exists():
        return out
    with MANIFEST.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["source_id"] == "modis_mcd12c1":
                m = re.search(r"\.A(\d{4})001\.", row["table"])
                if m:
                    out[int(m.group(1))] = row["sha256"]
    return out


@needs_npz
@pytest.mark.parametrize("path", NPZ_FILES, ids=lambda p: p.name)
def test_npz_contents(path):
    # Source: interface spec (arrays percent (rows, cols, 17) uint8, layer_names, lat_max, lon_min, cell, year,
    # source_sha256) + D-27 box (320 x 160 at 0.05 deg)
    z = np.load(path, allow_pickle=False)
    for key in ["percent", "layer_names", "lat_max", "lon_min", "cell", "year", "source_sha256"]:
        assert key in z.files, key
    p = z["percent"]
    assert p.dtype == np.uint8
    assert p.shape == (320, 160, 17)
    assert float(z["lat_max"]) == pytest.approx(24.0)
    assert float(z["lon_min"]) == pytest.approx(102.0)
    assert float(z["cell"]) == pytest.approx(0.05)
    assert int(z["year"]) == _npz_year(path)
    assert len(z["layer_names"]) == 17


@needs_npz
@pytest.mark.parametrize("path", NPZ_FILES, ids=lambda p: p.name)
def test_npz_percent_layers_sum_to_100(path):
    # Source: external fact: Land_Cover_Type_1_Percent gives the percent of each of the 17 IGBP classes per pixel
    s = np.load(path, allow_pickle=False)["percent"].astype(int).sum(axis=2)
    assert np.all(np.abs(s - 100) <= 1)


@needs_npz
@pytest.mark.parametrize("path", NPZ_FILES, ids=lambda p: p.name)
def test_npz_layer_names_follow_igbp_order(path):
    # Source: external fact (IGBP legend): class 0 water, 12 croplands, 13 urban, 14 cropland/natural vegetation mosaic
    names = [str(n).lower() for n in np.load(path, allow_pickle=False)["layer_names"]]
    assert "water" in names[0]
    assert "crop" in names[12]
    assert "urban" in names[13]
    assert "crop" in names[14]
    assert "mosaic" in names[14]


@needs_npz
@pytest.mark.parametrize("path", NPZ_FILES, ids=lambda p: p.name)
def test_npz_sha256_matches_manifest(path):
    # Source: D-27: each yearly global file's sha256 is recorded in data/MANIFEST.csv
    shas = _manifest_sha_by_year()
    year = _npz_year(path)
    if year not in shas:
        pytest.skip(f"no MANIFEST row for {year}")
    assert str(np.load(path, allow_pickle=False)["source_sha256"]) == shas[year]


def _subset_pixel(lat, lon):
    # computed here from the grid fact (not with pixel_index) so these data checks do not depend on the code under
    # test; all points used are pixel interiors, so floor() is unambiguous
    return math.floor((24.0 - lat) / 0.05), math.floor((lon - 102.0) / 0.05)


@needs_npz
@pytest.mark.parametrize("path", NPZ_FILES, ids=lambda p: p.name)
@pytest.mark.parametrize(("lat", "lon"), [(9.52, 108.03), (16.52, 109.53), (12.02, 109.83)])
def test_npz_open_sea_is_water(path, lat, lon):
    # Source: external geographic fact: these points lie in the South China Sea, far off the Vietnamese coast
    # (also checks north-south and east-west orientation of the stored array)
    r, c = _subset_pixel(lat, lon)
    assert np.load(path, allow_pickle=False)["percent"][r, c, 0] >= 95


@needs_npz
@pytest.mark.parametrize("path", NPZ_FILES, ids=lambda p: p.name)
@pytest.mark.parametrize(("lat", "lon"), [(22.52, 108.03), (16.02, 102.53), (20.02, 103.03)])
def test_npz_inland_points_are_land(path, lat, lon):
    # Source: external geographic fact: Guangxi (22.5 N 108 E), north-east Thailand (16.0 N 102.5 E) and northern Laos
    # (20 N 103 E) are inland; with the sea points above (9.5 N 108 E vs 22.5 N 108 E) a flipped array fails
    r, c = _subset_pixel(lat, lon)
    assert np.load(path, allow_pickle=False)["percent"][r, c, 0] <= 20


def _load_2024():
    path = SUBSET_DIR / "MCD12C1_2024_vn.npz"
    if not path.exists():
        pytest.skip("2024 subset missing")
    return np.load(path, allow_pickle=False)["percent"].astype(int)


@needs_npz
def test_npz_2024_e000b_mekong_test_pixel():
    # Source: E-000b [DATA]: the Mekong Delta rice test pixel (10.3 N, 105.6 E) is 99% class 14 in 2024.
    # 10.3 N and 105.6 E are both pixel borders (rows 273/274, cols 71/72 of the subset), and the border rule is not
    # documented, so the finding must hold for at least one of the four touching pixels.
    p = _load_2024()
    best = max(p[r, c, 14] for r in (273, 274) for c in (71, 72))
    assert best >= 95


@needs_npz
def test_npz_2024_mekong_delta_rice_land_is_farmland():
    # Source: external fact: the Long Xuyen Quadrangle (10.0 N 105.2 E), Plain of Reeds (10.6 N 105.9 E) and
    # Hau Giang/Soc Trang (9.6 N 105.8 E) are intensive rice areas; farmland = classes 12 + 14 (D-27)
    p = _load_2024()
    shares = []
    for lat, lon in [(10.02, 105.22), (10.62, 105.92), (9.62, 105.82)]:
        r, c = _subset_pixel(lat, lon)
        shares.append(p[r, c, 12] + p[r, c, 14])
    assert np.mean(shares) >= 50
