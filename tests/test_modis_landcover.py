import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("modis_landcover", Path("scripts/modis_landcover.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_subset_indices_match_grid_convention():
    # Global grid is 3600 x 7200 at 0.05 deg; row 0 = 90 N, column 0 = 180 W.
    r0, r1, c0, c1 = mod.subset_indices(8.0, 24.0, 102.0, 110.0, 0.05)
    assert (r0, r1) == (1320, 1640)
    assert (c0, c1) == (5640, 5800)
    assert (r1 - r0, c1 - c0) == (320, 160)


def test_pixel_centre_of_first_subset_cell():
    r0, _, c0, _ = mod.subset_indices()
    lat_centre = 90 - (r0 + 0.5) * mod.CELL
    lon_centre = -180 + (c0 + 0.5) * mod.CELL
    assert abs(lat_centre - 23.975) < 1e-9
    assert abs(lon_centre - 102.025) < 1e-9


def test_pixel_index_is_consistent_between_global_grid_and_subset():
    r0, _, c0, _ = mod.subset_indices()
    for lat, lon in [(18.9, 105.6), (10.3, 105.6), (19.25, 104.95), (23.97, 102.02)]:
        gr, gc = mod.pixel_index(lat, lon)
        sr, sc = mod.pixel_index(lat, lon, lat_max=mod.LAT_MAX, lon_min=mod.LON_MIN)
        assert (gr - r0, gc - c0) == (sr, sc)


def test_border_point_goes_south():
    # 18.9 N is exactly the border between rows 1421 (18.90-18.95) and 1422 (18.85-18.90).
    assert mod.pixel_index(18.9, 105.6)[0] == 1422
