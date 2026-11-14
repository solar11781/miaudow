"""Tests for the Nghệ An grid figure of the method page (UI-UX-SPEC section 11b item 4; D-135 (3); 05-DATA-CONTRACTS 5c).

Spec: the Nghệ An boundary (geoBoundaries, R-D04) and the NASA POWER cells it overlaps (0.5 x 0.625 degrees,
farmland_weights.POWER_DLAT and POWER_DLON), each cell shaded by its farmland weight from
data/processed/cell_weights.csv (05-DATA-CONTRACTS section 3: Nghệ An rows, method farmland_weighted); no new numbers
(D-135, 05 section 5c); an image with a text alternative (UI-UX-SPEC H1 and section 11b: alt text and caption).
Tests on the committed SVG run without the boundary file (data/raw is not in the repository); the test that rebuilds
it from the real boundary is skipped when the file is not downloaded.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import box

from fieldshift.data.boundaries import province_geometries
from fieldshift.ml.grid_figure import grid_figure_svg

REPO = Path(__file__).resolve().parents[1]
COMMITTED = REPO / "artifacts" / "figures" / "nghe_an_grid.svg"
WEIGHTS = pd.read_csv(REPO / "data" / "processed" / "cell_weights.csv")
NGHE_AN = WEIGHTS[(WEIGHTS["province_nso"] == "Nghe An") & (WEIGHTS["method"] == "farmland_weighted")]
GEOJSON = REPO / "data" / "raw" / "boundaries" / "geoBoundaries-VNM-ADM1_simplified.geojson"
ADMIN = REPO / "data" / "reference" / "admin_units.csv"
SVG_NS = "{http://www.w3.org/2000/svg}"
DECIMAL = re.compile(r"\d+\.\d+")
# The cells of Nghệ An with farmland weight 0: the five of data/processed/cell_weights_zero.csv (written by
# scripts/build_cell_weights.py, read 2026-11-14) and 19.0_103.75, whose rectangle overlaps the boundary only in a sliver
# that holds no MODIS pixel centre (measured 2026-11-14 with shapely: 0.26% of the cell area).
ZERO_CELLS = {"18.5_105.0", "19.0_104.375", "19.5_103.75", "19.5_104.375", "20.0_105.0", "19.0_103.75"}


def _parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)  # noqa: S314  our own generated svg, not untrusted input


def _cells(root: ET.Element) -> dict[str, ET.Element]:
    return {g.get("data-cell"): g for g in root.iter(f"{SVG_NS}g") if g.get("data-cell") is not None}


def _label(g: ET.Element) -> str | None:
    texts = g.findall(f"{SVG_NS}text")
    return texts[0].text if texts else None


@pytest.fixture(scope="module")
def committed() -> ET.Element:
    return _parse(COMMITTED.read_text(encoding="utf-8"))


def test_every_weighted_cell_is_drawn_with_its_weight_from_the_table(committed: ET.Element) -> None:
    cells = _cells(committed)
    assert len(NGHE_AN) == 5  # D-106: Nghệ An keeps 5 POWER cells under the fixed mask
    for row in NGHE_AN.itertuples():
        g = cells[row.cell_id]
        assert _label(g) == f"{row.farmland_weight:.2f}", row.cell_id
        assert float(g.get("data-weight")) == row.farmland_weight


def test_the_overlapping_cells_without_farmland_are_outlines_without_a_number(committed: ET.Element) -> None:
    cells = _cells(committed)
    assert set(cells) == set(NGHE_AN["cell_id"]) | ZERO_CELLS
    for cell_id in ZERO_CELLS:
        (rect,) = cells[cell_id].findall(f"{SVG_NS}rect")
        assert rect.get("fill") == "none"
        assert _label(cells[cell_id]) is None


def test_every_cell_is_one_power_cell_of_0_5_by_0_625_degrees(committed: ET.Element) -> None:
    # farmland_weights.POWER_DLAT, POWER_DLON (verified 2026-11-11): every drawn rectangle has the same size
    sizes = {(r.get("width"), r.get("height")) for g in _cells(committed).values() for r in g.findall(f"{SVG_NS}rect")}
    assert len(sizes) == 1


def test_the_printed_weights_sum_to_1_within_rounding(committed: ET.Element) -> None:
    printed = [float(t) for g in _cells(committed).values() if (t := _label(g)) is not None]
    assert len(printed) == 5
    assert abs(sum(printed) - 1) <= 0.005 * len(printed)  # 05 section 3: the weights of a unit sum to 1


def test_no_number_other_than_the_table_and_the_cell_size(committed: ET.Element) -> None:
    allowed = {f"{w:.2f}" for w in NGHE_AN["farmland_weight"]} | {"0.5", "0.625"}
    allowed |= {str(float(part)) for cell_id in set(NGHE_AN["cell_id"]) | ZERO_CELLS for part in cell_id.split("_")}
    printed = DECIMAL.findall(" ".join(committed.itertext()))
    assert printed
    assert set(printed) <= allowed


def test_svg_is_an_accessible_image_with_a_text_alternative(committed: ET.Element) -> None:
    assert committed.tag == f"{SVG_NS}svg"
    assert committed.get("role") == "img"
    assert committed[0].tag == f"{SVG_NS}title"
    assert committed[0].text
    desc = committed.find(f"{SVG_NS}desc")
    assert desc is not None
    for row in NGHE_AN.itertuples():
        assert f"{row.lat} N, {row.lon} E: {row.farmland_weight:.2f}" in desc.text
    for cell_id in ZERO_CELLS:
        lat, lon = cell_id.split("_")
        assert f"{lat} N, {lon} E" in desc.text
    tags = {el.tag for el in committed.iter()}
    assert not tags & {f"{SVG_NS}script", f"{SVG_NS}foreignObject", f"{SVG_NS}image", f"{SVG_NS}animate"}


def test_the_caption_names_the_sources_and_the_drawing_method(committed: ET.Element) -> None:
    text = " ".join(committed.itertext())
    for source in ("R-N01", "R-N02", "R-D04", "D-106", "D-146", "geoBoundaries", "cos"):
        assert source in text, source


@pytest.mark.skipif(not GEOJSON.exists(), reason="boundary file not downloaded")
def test_committed_svg_matches_the_builder_output() -> None:
    boundary = province_geometries(GEOJSON, ADMIN)["Nghe An"]
    assert COMMITTED.read_text(encoding="utf-8") == grid_figure_svg(WEIGHTS, boundary)


# ---- the builder on a hand-made boundary: two cells side by side, 18.75-19.25 N and 104.6875-105.9375 E


def _table(rows: list[tuple[str, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [("Nghe An", f"{la}_{lo}", la, lo, w, "farmland_weighted") for _, la, lo, w in rows]
        + [("Nghe An", "19.0_105.0", 19.0, 105.0, 1.0, "centroid"), ("Ha Tinh", "18.0_106.25", 18.0, 106.25, 1.0, "x")],
        columns=["province_nso", "cell_id", "lat", "lon", "farmland_weight", "method"],
    )


SQUARE = box(104.7, 18.8, 105.9, 19.2)  # inside the two cells 19.0_105.0 and 19.0_105.625


def test_builder_reads_only_the_farmland_weighted_rows_of_nghe_an() -> None:
    cells = _cells(_parse(grid_figure_svg(_table([("", 19.0, 105.0, 0.25), ("", 19.0, 105.625, 0.75)]), SQUARE)))
    assert {k: _label(g) for k, g in cells.items()} == {"19.0_105.0": "0.25", "19.0_105.625": "0.75"}


def test_builder_draws_an_overlapping_cell_without_weight_as_an_outline() -> None:
    cells = _cells(_parse(grid_figure_svg(_table([("", 19.0, 105.625, 1.0)]), SQUARE)))
    assert set(cells) == {"19.0_105.0", "19.0_105.625"}
    assert _label(cells["19.0_105.0"]) is None


def test_builder_refuses_a_weighted_cell_that_does_not_overlap_the_boundary() -> None:
    with pytest.raises(ValueError, match=r"20\.0_105\.0"):
        grid_figure_svg(_table([("", 19.0, 105.0, 0.5), ("", 20.0, 105.0, 0.5)]), SQUARE)


def test_builder_refuses_weights_that_do_not_sum_to_1() -> None:
    with pytest.raises(ValueError, match="sum"):
        grid_figure_svg(_table([("", 19.0, 105.0, 0.5)]), SQUARE)


def test_builder_refuses_a_table_without_nghe_an_rows() -> None:
    with pytest.raises(ValueError, match="Nghe An"):
        grid_figure_svg(_table([]), SQUARE)
