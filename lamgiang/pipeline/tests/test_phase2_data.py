"""Unit tests for the pure functions of the Phase-2 geospatial scripts (no network)."""

from __future__ import annotations

import struct
import sys
import zlib
from datetime import date
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_gibs as gb  # noqa: E402
import fetch_boundaries as fb  # noqa: E402
import fetch_nasa_missions as nm  # noqa: E402
import fetch_sentinel2 as s2  # noqa: E402


# ---------------------------------------------------------------- SCL masking
def test_scl_mask_keeps_vegetation_soil_water_only():
    scl = np.arange(12, dtype=np.uint8)
    keep = s2.scl_keep_mask(scl)
    assert keep.tolist() == [c in (4, 5, 6) for c in range(12)]
    for dropped in (0, 1, 2, 3, 7, 8, 9, 10, 11):
        assert not keep[dropped]


# ---------------------------------------------------------------- reflectance and offset
def test_reflectance_applies_boa_offset_for_new_baselines():
    dn = np.array([0, 1000, 1500, 4000], dtype=np.uint16)
    new = s2.dn_to_reflectance(dn, 0.0001, -0.1)  # processing baseline >= 04.00
    assert np.isnan(new[0])  # nodata
    assert new[1:] == pytest.approx([0.0, 0.05, 0.3], abs=1e-6)
    old = s2.dn_to_reflectance(np.array([500, 3000], dtype=np.uint16), 0.0001, 0.0)
    assert old == pytest.approx([0.05, 0.3], abs=1e-6)


def test_effective_offset_respects_earth_search_flag():
    assert s2.effective_offset("05.00", True) == 0.0  # Earth Search already applied BOA_ADD_OFFSET to pixels
    assert s2.effective_offset("05.11", True) == 0.0
    assert s2.effective_offset("04.00", False) == -0.1  # raw ESA DN still carries +1000
    assert s2.effective_offset("03.00", False) == 0.0
    assert s2.effective_offset("02.14", None) == 0.0


def test_offset_guard_rejects_contradictions():
    s2.check_offset(520.0, 0.0)
    s2.check_offset(1520.0, -0.1)
    s2.check_offset(None, 0.0)
    with pytest.raises(RuntimeError):
        s2.check_offset(1520.0, 0.0)  # offset still in the DNs but not removed
    with pytest.raises(RuntimeError):
        s2.check_offset(520.0, -0.1)  # offset removed twice (the first-run bug: NDVI > 1)


def test_haze_test_skips_bright_vegetation_only():
    s2.check_vegetation_red(0.045)
    s2.check_vegetation_red(None)
    with pytest.raises(s2.SceneQualityError):
        s2.check_vegetation_red(0.166)  # S2B 2024-04-22: SCL 'vegetation' red 0.17 under haze


def test_same_surface_gives_same_ndvi_across_baselines():
    # a vegetated pixel: red 0.05, NIR 0.30 -> DN 500/3000 (old) or 1500/4000 (with +1000 offset)
    old = s2.ndvi(s2.dn_to_reflectance(np.array([500]), 1e-4, 0), s2.dn_to_reflectance(np.array([3000]), 1e-4, 0))
    new = s2.ndvi(
        s2.dn_to_reflectance(np.array([1500]), 1e-4, -0.1), s2.dn_to_reflectance(np.array([4000]), 1e-4, -0.1)
    )
    assert old[0] == pytest.approx(new[0], abs=1e-6) == pytest.approx(0.25 / 0.35, abs=1e-6)
    # forgetting the offset would bias NDVI low
    wrong = s2.ndvi(np.array([0.15]), np.array([0.40]))
    assert wrong[0] < new[0] - 0.2


# ---------------------------------------------------------------- index formulas
def test_ndvi_evi_ndmi_formulas():
    blue, red, nir, swir = np.array([0.04]), np.array([0.05]), np.array([0.30]), np.array([0.20])
    assert s2.ndvi(red, nir)[0] == pytest.approx((0.30 - 0.05) / (0.30 + 0.05), rel=1e-6)
    assert s2.evi(blue, red, nir)[0] == pytest.approx(2.5 * 0.25 / (0.30 + 0.30 - 0.30 + 1.0), rel=1e-6)
    assert s2.ndmi(nir, swir)[0] == pytest.approx(0.10 / 0.50, rel=1e-6)


def test_indices_undefined_where_denominator_not_positive():
    assert np.isnan(s2.ndvi(np.array([0.0]), np.array([0.0]))[0])
    assert np.isnan(s2.ndvi(np.array([-0.02]), np.array([0.01]))[0])
    assert np.isnan(s2.evi(np.array([0.5]), np.array([0.0]), np.array([0.0]))[0])  # 1 - 3.75 < 0
    assert np.isnan(s2.ndmi(np.array([np.nan]), np.array([0.2]))[0])


def test_block_mean_2x2_and_nodata_propagation():
    a = np.array([[1, 3, 10, 10], [5, 7, 10, 0], [2, 2, 4, 4], [2, 2, 4, 4]], dtype=np.uint16)
    m = s2.block_mean_2x2(a)
    assert m.shape == (2, 2)
    assert m[0, 0] == pytest.approx(4.0)
    assert np.isnan(m[0, 1])  # one of four sub-pixels is nodata
    assert m[1, 0] == pytest.approx(2.0) and m[1, 1] == pytest.approx(4.0)
    with pytest.raises(ValueError):
        s2.block_mean_2x2(np.ones((3, 4)))


# ---------------------------------------------------------------- polygon clip statistics
def test_masked_stats_uses_only_inside_finite_values():
    vals = np.array([[0.1, 0.2, 0.9], [0.3, np.nan, 0.4]])
    inside = np.array([[True, True, False], [True, True, True]])
    st = s2.masked_stats(vals, inside)
    assert st["n"] == 4  # 0.9 is outside, NaN is skipped
    assert st["median"] == pytest.approx(0.25)
    assert st["p25"] == pytest.approx(np.percentile([0.1, 0.2, 0.3, 0.4], 25))
    assert st["p75"] == pytest.approx(np.percentile([0.1, 0.2, 0.3, 0.4], 75))
    empty = s2.masked_stats(vals, np.zeros_like(inside))
    assert empty == {"median": None, "p25": None, "p75": None, "n": 0}


def test_grid_mask_counts_pixel_centres_inside_polygon():
    from rasterio.features import geometry_mask
    from rasterio.transform import from_origin

    tf = from_origin(0, 100, 20, 20)  # 5x5 pixels of 20 m
    poly = {"type": "Polygon", "coordinates": [[[0, 100], [45, 100], [45, 55], [0, 55], [0, 100]]]}
    m = geometry_mask([poly], out_shape=(5, 5), transform=tf, invert=True)
    assert m.sum() == 4  # centres (10,90),(30,90),(10,70),(30,70); the 50 m centres fall outside
    touched = geometry_mask([poly], out_shape=(5, 5), transform=tf, invert=True, all_touched=True)
    assert touched.sum() == 9  # all_touched would also take the partly covered pixels (not used)


def test_snap_bounds_expands_to_20m_grid():
    assert s2.snap_bounds((523112.7, 2075984.9, 551177.3, 2107119.6)) == (523100.0, 2075980.0, 551180.0, 2107120.0)


# ---------------------------------------------------------------- seasons
@pytest.mark.parametrize(
    "d,expected",
    [
        (date(2021, 1, 1), ("spring", 2021)),
        (date(2021, 5, 31), ("spring", 2021)),
        (date(2020, 6, 1), ("summer_autumn", 2020)),
        (date(2020, 9, 15), ("summer_autumn", 2020)),
        (date(2020, 9, 16), ("autumn_winter", 2020)),
        (date(2024, 12, 31), ("autumn_winter", 2024)),
    ],
)
def test_season_assignment_is_non_overlapping(d, expected):
    assert s2.season_of(d) == expected


# ---------------------------------------------------------------- STAC item handling
def _item(day, tile, baseline, seq, platform="sentinel-2b"):
    return {
        "id": f"S2B_{tile}_{day.replace('-', '')}_{seq}_L2A",
        "properties": {
            "datetime": f"{day}T03:42:46Z",
            "grid:code": f"MGRS-{tile}",
            "platform": platform,
            "s2:processing_baseline": baseline,
            "s2:sequence": str(seq),
        },
    }


def test_dedupe_prefers_highest_baseline_and_groups_by_date():
    items = [
        _item("2021-06-27", "48QWG", "03.00", 0),
        _item("2021-06-27", "48QWG", "05.00", 1),
        _item("2021-06-27", "48QWF", "03.00", 0),
        _item("2021-06-17", "48QWF", "05.00", 1),
    ]
    d = s2.dedupe_items(items)
    assert len(d) == 3
    assert {i["properties"]["s2:processing_baseline"] for i in d if "WG" in i["id"]} == {"05.00"}
    groups = s2.group_scenes(d)
    assert list(groups) == ["S2B_20210617", "S2B_20210627"]
    assert len(groups["S2B_20210627"]) == 2


# ---------------------------------------------------------------- colour ramp and PNG
def test_ndvi_ramp_endpoints_mid_and_transparency():
    nd = np.array([[-0.3, 0.0, 0.4], [0.8, 1.0, np.nan]])
    rgba = s2.ndvi_rgba(nd)
    assert tuple(rgba[0, 0]) == (0xB5, 0x62, 0x3E, 255)  # clamped low
    assert tuple(rgba[0, 1]) == (0xB5, 0x62, 0x3E, 255)
    assert tuple(rgba[0, 2]) == (0xE9, 0xBC, 0x57, 255)
    assert tuple(rgba[1, 0]) == (0x2F, 0x5A, 0x37, 255)
    assert tuple(rgba[1, 1]) == (0x2F, 0x5A, 0x37, 255)  # clamped high
    assert rgba[1, 2, 3] == 0  # NaN transparent
    clipped = s2.ndvi_rgba(nd, alpha_mask=np.zeros(nd.shape, bool))
    assert (clipped[..., 3] == 0).all()


def test_png_encoder_roundtrip():
    rgba = np.zeros((3, 2, 4), dtype=np.uint8)
    rgba[1, 1] = (1, 2, 3, 255)
    png = s2.encode_png(rgba)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", png[16:24])
    assert (w, h) == (2, 3)
    idat_len = struct.unpack(">I", png[33:37])[0]
    raw = zlib.decompress(png[41 : 41 + idat_len])
    assert len(raw) == 3 * (1 + 2 * 4) and raw[9 + 1 + 4 : 9 + 1 + 8] == bytes([1, 2, 3, 255])


def test_png_grid_square_ground_pixels():
    w, h = s2.png_grid((105.2, 18.77, 105.5, 19.06), 1024)
    assert max(w, h) == 1024
    assert w / h == pytest.approx(0.30 * np.cos(np.radians(18.915)) / 0.29, rel=0.01)


# ---------------------------------------------------------------- boundaries
def test_fold_name_variants():
    for n in ("Đô Lương", "Do Luong", "Huyện Đô Lương", "do  luong", "Đô-Lương"):
        assert fb.fold(n) == "do luong"
    assert fb.fold("Đông Hà") != "do luong"


def test_area_of_known_square_and_hole():
    # a 0.1° x 0.1° square at the equator is ~ 11.13 km x 11.06 km on the sphere
    sq = {"type": "Polygon", "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]}
    a = fb.geom_area_km2(sq)
    assert a == pytest.approx((6371.007181 * np.radians(0.1)) ** 2, rel=2e-3)
    holed = {
        "type": "Polygon",
        "coordinates": sq["coordinates"] + [[[0.02, 0.02], [0.04, 0.02], [0.04, 0.04], [0.02, 0.04], [0.02, 0.02]]],
    }
    assert fb.geom_area_km2(holed) == pytest.approx(a * (1 - 0.04), rel=2e-3)
    assert fb.geom_area_km2_ellipsoid(sq) == pytest.approx(a, rel=1e-2)


def test_bbox_and_wgs84_check():
    g = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[105, 18], [106, 18], [106, 19], [105, 18]]],
            [[[104, 17], [104.5, 17], [104.5, 17.5], [104, 17]]],
        ],
    }
    assert fb.bbox_of(g) == [104, 17, 106, 19]
    assert fb.is_wgs84_lonlat(g)
    assert not fb.is_wgs84_lonlat({"type": "Polygon", "coordinates": [[[523112, 2075984], [0, 0], [1, 1]]]})


# ---------------------------------------------------------------- GIBS URL templating
def test_gibs_template_with_and_without_time():
    tmpl = (
        "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_L3_NDVI_16Day/default/{Time}/"
        "{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png"
    )
    url = gb.fill_template(tmpl, "MODIS_Terra_L3_NDVI_16Day", "2020-11-16", "GoogleMapsCompatible_Level9", 5, 14, 25)
    assert url.endswith("/default/2020-11-16/GoogleMapsCompatible_Level9/5/14/25.png")
    with pytest.raises(ValueError):
        gb.fill_template(tmpl, "X", None, "T", 0, 0, 0)
    static = gb.generic_template("epsg3857", "jpg", has_time=False)
    assert "{Time}" not in static and static.endswith("{TileMatrixSet}/{z}/{y}/{x}.jpg")
    assert "/default/{Time}/" in gb.generic_template("epsg4326", "png", has_time=True)


def test_webmercator_and_geographic_tile_over_vietnam():
    assert gb.webmercator_tile(18.89638889, 105.2802778, 5) == (25, 14)
    assert gb.webmercator_tile(0.0, 0.0, 1) == (1, 1)
    # GIBS EPSG:4326 level 5 of a 512 px set: 0.5625/32 deg/px -> 9 deg tiles from (-180, 90)
    mat = {
        "scale_denominator": 223632905.6114871 / 32,
        "tile_width": 512,
        "tile_height": 512,
        "top_left": [-180.0, 90.0],
    }
    assert gb.matrix_tile(18.89638889, 105.2802778, mat, 1.0 / gb.METERS_PER_DEGREE) == (31, 7)


def test_time_periods_parsing():
    p = gb.time_periods(["2000-03-05/2000-12-18/P16D", "2016-01-01"])
    assert p == [
        {"start": "2000-03-05", "end": "2000-12-18", "period": "P16D"},
        {"start": "2016-01-01", "end": "2016-01-01", "period": None},
    ]


# ---------------------------------------------------------------- NASA Eyes and Earthdata helpers
def test_frame_policy():
    assert gb.frame_policy({"Server": "AmazonS3"})["frameable_by_headers"]
    assert not gb.frame_policy({"X-Frame-Options": "SAMEORIGIN"})["frameable_by_headers"]
    assert not gb.frame_policy({"Content-Security-Policy": "default-src 'self'; frame-ancestors 'self'"})[
        "frameable_by_headers"
    ]
    assert gb.frame_policy({"content-security-policy": "frame-ancestors *"})["frameable_by_headers"]
    assert gb.earth_satellite_slug("sc_landsat_9") == "landsat-9"


def test_earthdata_credentials_env_netrc_and_auth_host(tmp_path, monkeypatch):
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    monkeypatch.setenv("NETRC", str(tmp_path / "none"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert nm.credentials() is None
    rc = tmp_path / ".netrc"
    rc.write_text("machine urs.earthdata.nasa.gov login demo password secret\n", encoding="utf-8")
    assert nm.credentials(str(rc)) == ("demo", "secret")
    monkeypatch.setenv("EARTHDATA_USERNAME", "u")
    monkeypatch.setenv("EARTHDATA_PASSWORD", "p")
    assert nm.credentials() == ("u", "p")
    assert nm.needs_urs_auth("https://urs.earthdata.nasa.gov/oauth/authorize?x=1")
    assert not nm.needs_urs_auth("https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/x.tif")
    assert nm.basic_auth_header("u", "p") == "Basic dTpw"


def test_cmr_params_and_data_links():
    p = nm.cmr_params(nm.PRODUCTS[0], [105.2, 18.7, 105.5, 19.1])
    assert p["bounding_box"] == "105.2,18.7,105.5,19.1" and p["short_name"] == "HLSS30" and p["version"] == "2.0"
    entry = {
        "links": [
            {"rel": "http://esipfed.org/ns/fedsearch/1.1/data#", "href": "https://x/a.tif"},
            {"rel": "http://esipfed.org/ns/fedsearch/1.1/s3#", "href": "s3://x/a.tif"},
            {"rel": "http://esipfed.org/ns/fedsearch/1.1/data#", "href": "https://x/c", "inherited": True},
            {"rel": "http://esipfed.org/ns/fedsearch/1.1/metadata#", "href": "https://x/m.xml"},
        ]
    }
    assert nm.data_links(entry) == ["https://x/a.tif"]
