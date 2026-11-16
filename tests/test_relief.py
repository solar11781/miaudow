"""Tests for the SRTM hillshade (fieldshift.data.relief).

Expected values: Horn (1981), Proc. IEEE 69(1):14-47, doi:10.1109/PROC.1981.11918 (slope from the 3 x 3 neighbourhood
with weights 1-2-1, reflectance of a Lambertian surface); the tile naming and 3 arc second spacing of NASA SRTMGL3 v003
(CMR record read 2026-11-16: tile files N19E105.SRTMGL3.hgt.zip, 1201 x 1201 big-endian int16); the map box of
frontend/src/features/science/Grid3D.tsx (cell centre +-0.3125 deg longitude, +-0.25 deg latitude).
"""

import math

import numpy as np
import pytest

from fieldshift.data import relief

SIN45 = math.sin(math.radians(45))


def test_flat_ground_has_the_sine_of_the_sun_altitude() -> None:
    # Horn 1981: a flat surface (p = q = 0) reflects sin(altitude); sin 45 degrees = 0.70710678
    shade = relief.hillshade(np.zeros((5, 5)), dx_m=np.full(5, 90.0), dy_m=90.0)
    assert shade.shape == (3, 3)
    assert np.allclose(shade, SIN45)


def test_slope_toward_the_light_is_brighter_than_away_from_it() -> None:
    # sun at azimuth 315 (north-west), altitude 45; x east, y north, rows run north to south.
    # z = column index: rises to the east, so the surface faces west: p = 1, normal (-1, 0, 1)/sqrt2.
    # sun vector (cos45 sin315, cos45 cos315, sin45) = (-0.5, 0.5, 0.70711): dot = (0.5 + 0.70711)/sqrt2 = 0.85355
    cols = np.tile(np.arange(5.0), (5, 1))
    toward = relief.hillshade(cols, dx_m=np.full(5, 1.0), dy_m=1.0)
    away = relief.hillshade(-cols, dx_m=np.full(5, 1.0), dy_m=1.0)
    assert np.allclose(toward, 0.85355339)
    # normal (1, 0, 1)/sqrt2: dot = (-0.5 + 0.70711)/sqrt2 = 0.14644661
    assert np.allclose(away, 0.14644661)
    assert toward.mean() > away.mean()


def test_slope_uses_horns_one_two_one_weights() -> None:
    # 3 x 3 worked by hand, rows north to south, spacing 10 m:
    #   a b c     10 12 13
    #   d e f  =  11 15 17
    #   g h i     14 16 20
    # dz/dx = ((c + 2f + i) - (a + 2d + g)) / (8 dx) = ((13 + 34 + 20) - (10 + 22 + 14)) / 80 = 21 / 80 = 0.2625
    # dz/dy (north) = ((a + 2b + c) - (g + 2h + i)) / (8 dy) = ((10 + 24 + 13) - (14 + 32 + 20)) / 80 = -19 / 80 = -0.2375
    z = np.array([[10.0, 12, 13], [11, 15, 17], [14, 16, 20]])
    p, q = relief.horn_slopes(z, dx_m=np.full(3, 10.0), dy_m=10.0)
    assert p[0, 0] == pytest.approx(0.2625)
    assert q[0, 0] == pytest.approx(-0.2375)
    # shade = (-p * (-0.5) - q * 0.5 + 0.70711) / sqrt(1 + p^2 + q^2) = 0.957107 / 1.060807 = 0.902244
    assert relief.hillshade(z, dx_m=np.full(3, 10.0), dy_m=10.0)[0, 0] == pytest.approx(0.902244, abs=1e-5)


def test_steep_slope_facing_away_is_clipped_to_zero() -> None:
    cols = np.tile(np.arange(5.0), (5, 1))
    assert np.all(relief.hillshade(-10 * cols, dx_m=np.full(5, 1.0), dy_m=1.0) == 0.0)


def test_cell_size_in_metres_at_this_latitude() -> None:
    # 3 arc seconds = 1/1200 degree; IUGG mean radius 6371008.7714 m: north-south 6371008.7714 * pi/180 / 1200 = 92.66 m
    dy, dx = relief.cell_size_m(np.array([19.0]))
    assert dy == pytest.approx(92.6624, abs=1e-3)
    # east-west shrinks by cos(latitude): 92.6624 * cos(19 deg) = 87.6 m
    assert dx[0] == pytest.approx(92.6624 * math.cos(math.radians(19.0)), abs=1e-3)


def test_tile_names_follow_the_srtm_convention() -> None:
    assert relief.tile_name(19, 105) == "N19E105"
    assert relief.tile_name(18, 103) == "N18E103"


def test_tiles_cover_the_nghe_an_map_box() -> None:
    # box of the 11 POWER cells (lat 18.5-20.0, lon 103.75-105.625) plus the Grid3D margins
    box = relief.map_box([(18.5, 103.75), (20.0, 105.625), (19.0, 105.0)])
    assert box == pytest.approx((103.4375, 18.25, 105.9375, 20.25))
    tiles = relief.tiles_for_box(box)
    assert tiles == [f"N{la}E{lo}" for la in (18, 19, 20) for lo in (103, 104, 105)]


def test_tile_url_is_the_lp_daac_granule_path() -> None:
    # pattern read from the CMR granule record of N18E104 on 2026-11-16
    assert relief.tile_url("N18E104") == (
        "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL3.003/N18E104.SRTMGL3.hgt/"
        "N18E104.SRTMGL3.hgt.zip"
    )


def test_read_hgt_is_big_endian_int16_and_rejects_other_sizes() -> None:
    raw = (np.arange(1201 * 1201, dtype=">i2") % 1000).astype(">i2").tobytes()
    grid = relief.read_hgt(raw, "N18E104")
    assert grid.shape == (1201, 1201)
    assert grid[0, 1] == 1
    with pytest.raises(ValueError, match="N18E104"):
        relief.read_hgt(b"\x00\x01", "N18E104")


def test_void_cells_fail_loudly() -> None:
    raw = np.full(1201 * 1201, -32768, dtype=">i2").tobytes()
    with pytest.raises(ValueError, match="void"):
        relief.read_hgt(raw, "N18E104")


def test_mosaic_crop_has_the_box_edges_and_one_cell_of_margin() -> None:
    tiles = {
        relief.tile_name(la, lo): np.full((1201, 1201), la * 1000 + lo, dtype=np.int16)
        for la in (18, 19)
        for lo in (103, 104)
    }
    z, origin = relief.mosaic_crop(tiles, (103.5, 18.5, 104.5, 19.5))
    # 1 degree = 1200 intervals, so 1201 samples on each edge; one extra sample all round for the 3 x 3 window
    assert z.shape == (1203, 1203)
    assert origin == pytest.approx((103.5 - 1 / 1200, 19.5 + 1 / 1200))


def test_resample_keeps_the_mean_of_a_block() -> None:
    a = np.array([[0.0, 2.0, 4.0, 6.0], [0.0, 2.0, 4.0, 6.0]])
    assert np.allclose(relief.resample(a, 2, 1), [[1.0, 5.0]])


def test_image_height_follows_the_map_projection() -> None:
    # Grid3D draws longitude scaled by cos(19.3 deg): width 2.5 * cos(19.3) = 2.3596, height 2.0
    assert relief.image_size((103.4375, 18.25, 105.9375, 20.25), 900) == (900, 763)


def test_manifest_row_has_the_eight_manifest_columns() -> None:
    row = relief.manifest_row(
        "data/raw/srtm/N18E104.SRTMGL3.hgt.zip", "N18E104", "https://x/y.zip", "2026-11-16", "ab" * 32
    )
    assert row[0] == "data/raw/srtm/N18E104.SRTMGL3.hgt.zip"
    assert row[1] == "nasa_srtmgl3"
    assert len(row) == 8
    assert row[4] == "https://x/y.zip"
    assert row[7] == "ab" * 32


def test_to_grey_scales_zero_to_one_onto_bytes() -> None:
    assert relief.to_grey(np.array([[0.0, 0.5, 1.0]])).tolist() == [[0, 128, 255]]
