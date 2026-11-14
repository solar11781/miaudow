"""Tests for farmland weights per NASA POWER cell (written before the code, D-29).

Spec: D-26 (weight of a POWER cell for a province = farmland in province AND cell / farmland in province),
D-27, D-107 and D-146 (farmland = MODIS IGBP class 12 percent at 80%, the middle of the MCD12 user guide's "At least
60%" cultivated, i.e. 60-100%, plus class 14 percent at 50%, the middle of its "small-scale cultivation 40-60%"), D-106 (one fixed mask for all years: per pixel, the minimum over 2001-2015),
DATA-SOURCES nasa_power_grid (cells centred on multiples of 0.5 deg lat and 0.625 deg lon, verified 2026-11-11),
MODIS subset layout (D-27: 0.05 deg pixels, top-left corner lat_max/lon_min). Routine choices documented in D-36:
a pixel is assigned by its centre; pixels are weighted by ground area (cos latitude). Zero farmland raises an error.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from fieldshift.data.boundaries import province_geometries
from fieldshift.features.farmland_weights import (
    build_cell_weights,
    centroid_weights,
    farmland_fraction,
    fixed_farmland_mask,
    power_cell_centre,
    province_cell_weights,
    zero_weight_cells,
)


def test_power_cell_centre_matches_verified_api_probe():
    # Source: API probe 2026-11-11: lat 19.20 and 19.30 fell in different cells (edge 19.25);
    # lon 105.25 and 105.35 fell in different cells (edge 105.3125).
    assert power_cell_centre(19.20, 105.0) == (19.0, 105.0)
    assert power_cell_centre(19.30, 105.0) == (19.5, 105.0)
    assert power_cell_centre(19.1, 105.25) == (19.0, 105.0)
    assert power_cell_centre(19.1, 105.35) == (19.0, 105.625)


def test_farmland_fraction_counts_class_12_at_80_and_class_14_at_half():
    # Source: D-146: class 12 at 80%; D-107: class 14 at 50%; other classes (e.g. 10 grasslands) not at all.
    p = np.zeros((1, 4, 17), dtype=np.uint8)
    p[0, 0, 12] = 40
    p[0, 0, 14] = 40
    p[0, 0, 10] = 20
    p[0, 1, 14] = 100
    p[0, 2, 10] = 100
    p[0, 3, 12] = 100
    assert farmland_fraction(p) == pytest.approx(np.array([[0.8 * 0.4 + 0.5 * 0.4, 0.5, 0.0, 0.8]]))


def _year_grid(frac12):
    p = np.zeros((1, 2, 17), dtype=np.uint8)
    p[0, :, 12] = frac12
    return {"percent": p, "lat_max": 19.1, "lon_min": 105.0, "cell": 0.05}


def test_fixed_mask_is_minimum_over_2001_2015():
    # Source: D-106: farmland present in every year = per-pixel minimum over 2001-2015; D-146: class 12 at 80%.
    grids = {y: _year_grid([60, 30]) for y in range(2001, 2016)}
    grids[2007] = _year_grid([20, 80])
    mask = fixed_farmland_mask(grids)
    assert mask["farmland"] == pytest.approx(np.array([[0.8 * 0.2, 0.8 * 0.3]]))
    assert (mask["lat_max"], mask["lon_min"], mask["cell"]) == (19.1, 105.0, 0.05)


def test_fixed_mask_refuses_other_years():
    # Source: D-106 and plan review A3: a map from 2016 or later would use test-period information.
    grids = {y: _year_grid([60, 30]) for y in range(2001, 2017)}
    with pytest.raises(ValueError, match=r"exactly the land-cover years 2001-2015"):
        fixed_farmland_mask(grids)
    with pytest.raises(ValueError, match=r"exactly the land-cover years 2001-2015"):
        fixed_farmland_mask({y: _year_grid([60, 30]) for y in range(2002, 2016)})


GRID_ROWS, GRID_COLS = 4, 12  # every synthetic subset below has this size


def _grid(lat_max, lon_min, farm_pixels, cls=12, pct=100):
    """Synthetic MODIS subset: percent array (rows, cols, 17) with farmland in the given (row, col) pixels."""
    p = np.zeros((GRID_ROWS, GRID_COLS, 17), dtype=np.uint8)
    p[:, :, 0] = 100  # water elsewhere
    for r, c in farm_pixels:
        p[r, c, 0] = 100 - pct
        p[r, c, cls] = pct
    return {"percent": p, "lat_max": lat_max, "lon_min": lon_min, "cell": 0.05}


def test_all_farmland_in_one_cell_gets_weight_one():
    # Province spans two POWER cells (edge at lon 105.3125); farmland only west of the edge.
    prov = box(105.0, 19.0, 105.6, 19.2)
    g = _grid(19.2, 105.0, farm_pixels=[(1, 1), (2, 3)])  # pixel centres ~105.075, 105.175
    w = province_cell_weights(prov, g)
    assert w == pytest.approx({(19.0, 105.0): 1.0})


def test_equal_farmland_split_equally_and_weights_sum_to_one():
    prov = box(105.0, 19.0, 105.6, 19.2)
    g = _grid(19.2, 105.0, farm_pixels=[(1, 1), (1, 10)])  # one pixel each side of 105.3125
    w = province_cell_weights(prov, g)
    assert sum(w.values()) == pytest.approx(1.0)
    assert w[(19.0, 105.0)] == pytest.approx(0.5, abs=1e-9)
    assert w[(19.0, 105.625)] == pytest.approx(0.5, abs=1e-9)


def test_farmland_outside_province_is_ignored():
    prov = box(105.0, 19.0, 105.3, 19.2)
    g = _grid(19.2, 105.0, farm_pixels=[(1, 1), (1, 10)])  # (1, 10) centre lon 105.525: outside
    assert province_cell_weights(prov, g) == pytest.approx({(19.0, 105.0): 1.0})


def test_class_14_counts_and_other_classes_do_not():
    # Source: D-27, D-107: classes 12 and 14 are farmland (14 at half); e.g. class 10 (grasslands) is not.
    prov = box(105.0, 19.0, 105.6, 19.2)
    g = _grid(19.2, 105.0, farm_pixels=[(1, 1)], cls=14)
    g["percent"][1, 10, 0] = 0
    g["percent"][1, 10, 10] = 100  # grassland pixel east of the edge
    assert province_cell_weights(prov, g) == pytest.approx({(19.0, 105.0): 1.0})


def test_partial_percentages_weight_proportionally():
    prov = box(105.0, 19.0, 105.6, 19.2)
    g = _grid(19.2, 105.0, farm_pixels=[(1, 1)], pct=30)
    g["percent"][1, 10, 0] = 10
    g["percent"][1, 10, 14] = 90
    w = province_cell_weights(prov, g)
    # D-146: 30% class 12 -> 0.24; D-107: 90% class 14 -> 0.45
    assert w[(19.0, 105.0)] == pytest.approx(0.24 / 0.69, rel=1e-3)
    assert w[(19.0, 105.625)] == pytest.approx(0.45 / 0.69, rel=1e-3)


def test_zero_farmland_raises():
    # Spec (no assumptions): weights are undefined without farmland; fail loudly, ask the team.
    prov = box(105.0, 19.0, 105.6, 19.2)
    with pytest.raises(ValueError, match=r"no farmland pixels"):
        province_cell_weights(prov, _grid(19.2, 105.0, farm_pixels=[]))


MODIS_DIR = Path("data/interim/modis_vn")
GEOJSON = Path("data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson")
HAVE_REAL = all((MODIS_DIR / f"MCD12C1_{y}_vn.npz").exists() for y in range(2001, 2016)) and GEOJSON.exists()


def _real_mask():
    grids = {}
    for y in range(2001, 2016):
        z = np.load(MODIS_DIR / f"MCD12C1_{y}_vn.npz")
        grids[y] = {
            "percent": z["percent"],
            "lat_max": float(z["lat_max"]),
            "lon_min": float(z["lon_min"]),
            "cell": float(z["cell"]),
        }
    return fixed_farmland_mask(grids)


@pytest.mark.skipif(not HAVE_REAL, reason="real data not present")
def test_nghe_an_fixed_mask_matches_exploration_e000m():
    # Source: EXPERIMENTS E-000m (follow-up 2026-11-13, real MODIS data): with the D-106 mask, class 12 at 80% (D-146) and
    # class 14 at 50% (D-107), Nghe An has 5 cells:
    # (19.0, 105.625) 0.473, (18.5, 105.625) 0.196, (19.5, 105.625) 0.158, (19.0, 105.0) 0.136, (19.5, 105.0) 0.038.

    geom = province_geometries(GEOJSON, "data/reference/admin_units.csv")["Nghe An"]
    w = province_cell_weights(geom, _real_mask())
    expected = {
        (19.0, 105.625): 0.473,
        (18.5, 105.625): 0.196,
        (19.5, 105.625): 0.158,
        (19.0, 105.0): 0.136,
        (19.5, 105.0): 0.038,
    }
    assert set(w) == set(expected)
    for k, v in expected.items():
        assert w[k] == pytest.approx(v, abs=0.001)


@pytest.mark.skipif(not HAVE_REAL, reason="real data not present")
def test_committed_cell_weights_match_the_current_code_for_nghe_an():
    # 05-DATA-CONTRACTS §3: data/processed/cell_weights.csv is the committed output of this code; a stale file must fail.

    geom = province_geometries(GEOJSON, "data/reference/admin_units.csv")["Nghe An"]
    w = province_cell_weights(geom, _real_mask())
    rows = pd.read_csv("data/processed/cell_weights.csv").query("province_nso == 'Nghe An'")
    committed = {(r.lat, r.lon): r.farmland_weight for r in rows.itertuples()}
    assert set(committed) == set(w)
    for k, v in w.items():
        assert committed[k] == pytest.approx(v, abs=1e-12)


def test_cell_weight_table_one_row_per_province_cell_sums_to_one():
    # Source: 05-DATA-CONTRACTS §3: fixed for all years; columns as the contract; weights of a unit sum to 1;
    # provinces without farmland are reported, never filled.

    geoms = {"A": box(105.0, 19.0, 105.6, 19.2), "Empty": box(105.0, 19.0, 105.05, 19.05)}
    g = _grid(19.2, 105.0, farm_pixels=[(1, 1), (1, 10)])
    mask = {
        "farmland": np.asarray(g["percent"][:, :, 12], dtype=float) / 100.0,
        "lat_max": 19.2,
        "lon_min": 105.0,
        "cell": 0.05,
    }
    table, missing = build_cell_weights(geoms, mask)
    assert list(table.columns) == ["province_nso", "cell_id", "lat", "lon", "farmland_weight", "method"]
    assert table.groupby("province_nso").farmland_weight.sum().round(9).eq(1.0).all()
    assert set(table.method) == {"farmland_weighted"}
    assert missing == ["Empty"]
    assert set(table.cell_id) == {"19.0_105.0", "19.0_105.625"}


def test_zero_weight_cells_are_listed():
    # Source: 03-ML-SPEC §4: list any POWER cell inside the unit whose farmland weight is zero; no silent fallback.

    prov = box(105.0, 19.0, 105.6, 19.2)
    g = _grid(19.2, 105.0, farm_pixels=[(1, 1)])
    mask = {
        "farmland": np.asarray(g["percent"][:, :, 12], dtype=float) / 100.0,
        "lat_max": 19.2,
        "lon_min": 105.0,
        "cell": 0.05,
    }
    assert zero_weight_cells(prov, mask) == [(19.0, 105.625)]


def test_centroid_weights_give_each_province_the_power_cell_of_its_centre():
    # Source: E-008 (03-ML-SPEC section 7): "centroid vs farmland-weighted cells"; a 1 x 1 degree box centred on
    # 19.0 N 105.0 E lies in the POWER cell centred there (0.5 x 0.625 degree grid)
    table = centroid_weights({"P": box(104.5, 18.5, 105.5, 19.5)})
    assert table.to_dict("records") == [
        {
            "province_nso": "P",
            "cell_id": "19.0_105.0",
            "lat": 19.0,
            "lon": 105.0,
            "farmland_weight": 1.0,
            "method": "centroid",
        }
    ]
