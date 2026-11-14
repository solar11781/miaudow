"""Unit tests for the pure functions of the acquisition scripts (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fetch_chirps_v3 as ch  # noqa: E402
import fetch_documents as fd  # noqa: E402
import fetch_modis_ndvi as mo  # noqa: E402

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]],
}


# ---------------------------------------------------------------- point in polygon
def test_point_in_polygon_inside_outside_and_hole():
    assert ch.point_in_polygon(1, 1, SQUARE)
    assert not ch.point_in_polygon(11, 1, SQUARE)
    assert not ch.point_in_polygon(5, 5, SQUARE)  # inside the hole
    assert ch.point_in_polygon(7, 5, SQUARE)


def test_point_in_multipolygon_and_concave_ring():
    concave = [[0, 0], [4, 0], [4, 4], [2, 1], [0, 4], [0, 0]]  # a "V" notch from the top
    multi = {"type": "MultiPolygon", "coordinates": [[concave], [[[10, 10], [12, 10], [12, 12], [10, 12]]]]}
    assert ch.point_in_polygon(1, 0.5, multi)
    assert not ch.point_in_polygon(2, 3, multi)  # in the notch
    assert ch.point_in_polygon(11, 11, multi)
    with pytest.raises(ValueError):
        ch.point_in_polygon(0, 0, {"type": "Point", "coordinates": [0, 0]})


# ---------------------------------------------------------------- footprint selection
def test_footprint_is_half_power_cell():
    assert ch.footprint(19.0, 105.625) == (18.75, 19.25, 105.3125, 105.9375)


def test_select_pixels_counts_005_degree_centres_in_power_cell():
    # 0.05 deg global grid, window starting at lon 104.6, lat 19.5 (north-up)
    t = (0.05, 0.0, -180.0, 0.0, -0.05, 60.0)
    row_off, col_off = int(round((60 - 19.5) / 0.05)), int(round((104.6 + 180) / 0.05))
    lats, lons = ch.pixel_centres(t, row_off, col_off, 40, 40)
    assert lats[0, 0] == pytest.approx(19.475)
    assert lons[0, 0] == pytest.approx(104.625)
    mask = ch.select_pixels(lats, lons, ch.footprint(19.0, 105.0), None)
    # lat 18.75-19.25 -> 10 rows; lon 104.6875-105.3125 -> centres 104.725..105.275 -> 12 columns
    assert mask.sum() == 10 * 12
    poly = {"type": "Polygon", "coordinates": [[[104.0, 18.0], [105.0, 18.0], [105.0, 20.0], [104.0, 20.0]]]}
    mask2 = ch.select_pixels(lats, lons, ch.footprint(19.0, 105.0), poly)
    assert mask2.sum() == 10 * 6  # only centres west of lon 105.0


def test_pixel_containing_site():
    t = (0.05, 0.0, -180.0, 0.0, -0.05, 60.0)
    r, c = ch.pixel_containing(t, 18.89638889, 105.2802778)
    assert -180 + c * 0.05 <= 105.2802778 < -180 + (c + 1) * 0.05
    assert 60 - (r + 1) * 0.05 <= 18.89638889 < 60 - r * 0.05


def test_aggregate_counts_missing_and_never_fills():
    vals = np.array([[10.0, -9999.0], [20.0, np.nan]])
    mask = np.ones_like(vals, dtype=bool)
    mean, n, miss = ch.aggregate(vals, mask)
    assert (mean, n, miss) == (15.0, 4, 2)
    mean, n, miss = ch.aggregate(np.array([[-9999.0]]), np.array([[True]]))
    assert mean is None and n == 1 and miss == 1


def test_power_monthly_totals_skips_incomplete_or_filled_months():
    daily = {f"202001{d:02d}": 1.0 for d in range(1, 32)}
    daily.update({f"202002{d:02d}": 2.0 for d in range(1, 30)})
    daily["20200215"] = -999.0
    daily.update({f"202003{d:02d}": 1.0 for d in range(1, 30)})  # 29 of 31 days
    out = ch.power_monthly_totals(daily)
    assert out == {(2020, 1): 31.0}


def test_parse_listing():
    html = (
        '<tr><td class="link"><a href="chirps-v3.0.1991.01.cog" title="x">chirps-v3.0.1991.01.cog</a></td>'
        '<td class="size">28.0 MiB</td><td class="date">2025-Feb-25 18:27</td></tr>'
    )
    assert ch.parse_listing(html) == {"chirps-v3.0.1991.01.cog": "2025-Feb-25 18:27"}


# ---------------------------------------------------------------- NDVI scaling and reliability
def test_scale_ndvi():
    assert mo.scale_ndvi(5000) == 0.5
    assert mo.scale_ndvi(-2000) == -0.2
    assert mo.scale_ndvi(-3000) is None  # fill
    assert mo.scale_ndvi(10001) is None
    assert mo.scale_ndvi(None) is None


def test_reliability_mask_reports_missing_not_dropped():
    assert mo.pixel_record(7000, 0) == (0.7, True)
    assert mo.pixel_record(7000, 1) == (0.7, True)
    assert mo.pixel_record(7000, 2) == (None, False)
    assert mo.pixel_record(7000, 3) == (None, False)
    assert mo.pixel_record(7000, -1) == (None, False)
    assert mo.pixel_record(-3000, 0) == (None, False)
    s = mo.summarise([0.2, None, 0.4, 0.6, None])
    assert s["n_valid"] == 3 and s["n_total"] == 5 and s["ndvi_median"] == 0.4
    assert s["ndvi_p25"] == pytest.approx(0.3) and s["ndvi_p75"] == pytest.approx(0.5)
    assert mo.summarise([None, None])["ndvi_median"] == ""


def test_doy_and_chunks():
    assert mo.doy_of("A2020177") == 177
    assert [len(c) for c in mo.chunks(list(range(23)), 10)] == [10, 10, 3]


# ---------------------------------------------------------------- chunking by Điều
LAW = [
    "QUYẾT ĐỊNH",
    "Căn cứ Luật ...;",
    "Chương I",
    "NHỮNG QUY ĐỊNH CHUNG",
    "Điều 1. Phạm vi điều chỉnh",
    "Quyết định này quy định về dự báo.",
    "Điều 2. Cấp độ rủi ro",
    "1. Rủi ro thiên tai cấp độ 1 gồm các trường hợp sau:",
    "a) Dự báo lượng mưa từ 100 mm;",
    "b) Dự báo khác.",
    "2. Rủi ro thiên tai cấp độ 2 khi dự báo 400 mm.",
    "Chương II",
    "ĐIỀU KHOẢN THI HÀNH",
    "Mục 1. TRÁCH NHIỆM",
    "Điều 3. Hiệu lực thi hành",
    "Quyết định này có hiệu lực từ ngày 1/7/2021.",
    "Nơi nhận:\n- Như Điều 3;",
    "PHỤ LỤC I",
    "Điều 99. không phải điều",
]


def test_chunk_by_article_splits_dieu_and_khoan_and_keeps_points():
    chunks = fd.chunk_by_article(LAW)
    locs = [c["location"] for c in chunks]
    assert locs == ["Điều 1", "Điều 2, khoản 1", "Điều 2, khoản 2", "Điều 3"]
    assert chunks[1]["text"] == (
        "1. Rủi ro thiên tai cấp độ 1 gồm các trường hợp sau:\na) Dự báo lượng mưa từ 100 mm;\nb) Dự báo khác."
    )
    assert chunks[1]["heading"] == "Điều 2. Cấp độ rủi ro"
    assert chunks[0]["chapter"] == "Chương I NHỮNG QUY ĐỊNH CHUNG"
    assert chunks[3]["chapter"] == "Chương II ĐIỀU KHOẢN THI HÀNH / Mục 1. TRÁCH NHIỆM"
    assert all("Nơi nhận" not in c["text"] for c in chunks)


def test_chunk_by_article_keep_range_and_wording_unchanged():
    chunks = fd.chunk_by_article(LAW, keep=(2, 2))
    assert {c["article"] for c in chunks} == {2}
    joined = "\n".join(c["text"] for c in chunks)
    for p in LAW[7:11]:
        assert p in joined


def test_html_to_paragraphs_strips_tags_only():
    html = (
        '<p class="prov-article"><strong>Điều 1. Phạm vi&nbsp;điều chỉnh </strong></p>'
        "<p>Nghị định này   quy định về <em>đất</em> trồng lúa.</p><p>Chương I<br>\n QUY ĐỊNH CHUNG</p>"
    )
    assert fd.html_to_paragraphs(html) == [
        "Điều 1. Phạm vi điều chỉnh",
        "Nghị định này quy định về đất trồng lúa.",
        "Chương I\nQUY ĐỊNH CHUNG",
    ]


def test_flight_text_reference():
    payload = '0:{"a":1}\n2b:T5,héllo{"documentContent":{"id":"1","title":null,"content":"$2b"}}'
    # 'héllo' is 6 UTF-8 bytes, so a T5 row ends after 'héll'
    assert fd.resolve_text_ref(payload, "$2b") == "héll"
    assert fd.vbpl_content(payload) == "héll"
