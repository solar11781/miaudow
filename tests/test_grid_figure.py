"""Tests for the Nghệ An grid figure of the method page (UI-UX-SPEC section 11b item 4; D-135 (3); 05-DATA-CONTRACTS 5c).

Spec: the Nghệ An boundary (geoBoundaries, R-D04) and its NASA POWER cells (0.5 x 0.625 degrees,
farmland_weights.POWER_DLAT and POWER_DLON), each cell shaded by its farmland weight from
data/processed/cell_weights.csv (05-DATA-CONTRACTS section 3: Nghệ An rows, method farmland_weighted); the cells with
weight 0 are the pipeline's own list, data/processed/cell_weights_zero.csv (05 section 3), so Nghệ An has the 10 cells
of D-26; no new numbers (D-135, 05 section 5c); an image with a text alternative (UI-UX-SPEC H1 and section 11b).
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
WEIGHTS = pd.read_csv(REPO / "data" / "processed" / "cell_weights.csv", float_precision="round_trip")
NGHE_AN = WEIGHTS[(WEIGHTS["province_nso"] == "Nghe An") & (WEIGHTS["method"] == "farmland_weighted")]
GEOJSON = REPO / "data" / "raw" / "boundaries" / "geoBoundaries-VNM-ADM1_simplified.geojson"
ADMIN = REPO / "data" / "reference" / "admin_units.csv"
SVG_NS = "{http://www.w3.org/2000/svg}"
DECIMAL = re.compile(r"\d+\.\d+")
ZERO_TABLE = pd.read_csv(REPO / "data" / "processed" / "cell_weights_zero.csv", float_precision="round_trip")
ZERO_CELLS = {f"{r.lat}_{r.lon}" for r in ZERO_TABLE[ZERO_TABLE["province_nso"] == "Nghe An"].itertuples()}


def _parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)  # noqa: S314  our own generated svg, not untrusted input


def _cells(root: ET.Element) -> dict[str, ET.Element]:
    return {g.get("data-cell"): g for g in root.iter(f"{SVG_NS}g") if g.get("data-cell") is not None}


def _labels(root: ET.Element) -> dict[str, ET.Element]:
    return {g.get("data-label"): g for g in root.iter(f"{SVG_NS}g") if g.get("data-label") is not None}


def _label_texts(root: ET.Element) -> dict[str, str]:
    return {cell_id: g.find(f"{SVG_NS}text").text for cell_id, g in _labels(root).items()}


def _luminance(hex_colour: str) -> float:
    """WCAG 2.1 relative luminance of an sRGB colour #rrggbb."""
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


@pytest.fixture(scope="module")
def committed() -> ET.Element:
    return _parse(COMMITTED.read_text(encoding="utf-8"))


def test_every_weighted_cell_is_drawn_with_its_weight_from_the_table(committed: ET.Element) -> None:
    labels = _label_texts(committed)
    assert len(NGHE_AN) == 5  # D-106: Nghệ An keeps 5 POWER cells under the fixed mask
    assert set(labels) == set(NGHE_AN["cell_id"])
    for row in NGHE_AN.itertuples():
        (rect,) = _cells(committed)[row.cell_id].findall(f"{SVG_NS}rect")
        assert rect.get("fill") != "none"
        assert labels[row.cell_id] == f"{row.farmland_weight:.2f}", row.cell_id


def test_every_label_sits_on_a_white_box_drawn_after_the_boundary(committed: ET.Element) -> None:
    children = list(committed)
    boundary = next(i for i, el in enumerate(children) if el.tag == f"{SVG_NS}path")
    for cell_id, g in _labels(committed).items():
        assert children.index(g) > boundary, cell_id  # the boundary line never crosses a number
        box_, text = list(g)
        assert box_.tag == f"{SVG_NS}rect"
        assert box_.get("fill") == committed.find(f"{SVG_NS}rect").get("fill")  # the background colour
        assert text.tag == f"{SVG_NS}text"


def test_label_text_contrast_is_at_least_4_5_to_1_on_its_box(committed: ET.Element) -> None:
    for g in _labels(committed).values():
        box_, text = list(g)
        fill = text.get("fill") or committed.get("fill")
        lighter, darker = sorted((_luminance(fill), _luminance(box_.get("fill"))), reverse=True)
        # WCAG 2.1 success criterion 1.4.3: contrast (L1 + 0.05) / (L2 + 0.05) at least 4.5:1 (UI-UX-SPEC H8)
        assert (lighter + 0.05) / (darker + 0.05) >= 4.5


def test_the_cells_are_the_weighted_cells_and_the_pipeline_zero_weight_cells(committed: ET.Element) -> None:
    cells = _cells(committed)
    # D-26: 10 cells, the cells that hold Nghệ An's MODIS land pixels; D-106: 5 of them hold farmland
    assert len(ZERO_CELLS) == 5
    assert set(cells) == set(NGHE_AN["cell_id"]) | ZERO_CELLS
    for cell_id in ZERO_CELLS:
        (rect,) = cells[cell_id].findall(f"{SVG_NS}rect")
        assert rect.get("fill") == "none"
    assert not set(_labels(committed)) & ZERO_CELLS


def test_every_cell_is_one_power_cell_of_0_5_by_0_625_degrees(committed: ET.Element) -> None:
    # farmland_weights.POWER_DLAT, POWER_DLON (verified 2026-11-11): every drawn rectangle has the same size
    sizes = {(r.get("width"), r.get("height")) for g in _cells(committed).values() for r in g.findall(f"{SVG_NS}rect")}
    assert len(sizes) == 1


def test_the_printed_weights_sum_to_1_within_rounding(committed: ET.Element) -> None:
    printed = [float(t) for t in _label_texts(committed).values()]
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
    for source in (
        "R-N01",
        "R-N02",
        "D-106",
        "D-146",
        "Boundary: geoBoundaries gbOpen VNM ADM1 (Runfola et al. 2020; R-D04)",  # REFERENCES R-D04; DATA-SOURCES credit
        "cos",
        "rounded to 2 decimals",
    ):
        assert source in text, source


def test_the_text_alternative_and_legend_state_the_pipeline_rule_not_overlap(committed: ET.Element) -> None:
    # the boundary also grazes an 11th cell that holds none of its MODIS pixels, so "overlaps" would be wrong
    text = " ".join(committed.itertext())
    assert "the 10 NASA POWER cells that hold the province's MODIS land pixels" in text
    assert "Cell with Nghệ An land pixels but farmland weight 0" in text
    assert "overlap" not in text


@pytest.mark.skipif(not GEOJSON.exists(), reason="boundary file not downloaded")
def test_committed_svg_matches_the_builder_output() -> None:
    boundary = province_geometries(GEOJSON, ADMIN)["Nghe An"]
    assert COMMITTED.read_text(encoding="utf-8") == grid_figure_svg(WEIGHTS, ZERO_TABLE, boundary)


# ---- the builder on a hand-made boundary: two cells side by side, 18.75-19.25 N and 104.6875-105.9375 E


def _table(rows: list[tuple[str, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [("Nghe An", f"{la}_{lo}", la, lo, w, "farmland_weighted") for _, la, lo, w in rows]
        + [("Nghe An", "19.0_105.0", 19.0, 105.0, 1.0, "centroid"), ("Ha Tinh", "18.0_106.25", 18.0, 106.25, 1.0, "x")],
        columns=["province_nso", "cell_id", "lat", "lon", "farmland_weight", "method"],
    )


SQUARE = box(104.7, 18.8, 105.9, 19.2)  # inside the two cells 19.0_105.0 and 19.0_105.625
NO_ZERO = pd.DataFrame(columns=["province_nso", "lat", "lon"])


def _zero(*cells: tuple[float, float]) -> pd.DataFrame:
    return pd.DataFrame(
        [("Nghe An", la, lo) for la, lo in cells] + [("Ha Tinh", 19.0, 105.0)], columns=["province_nso", "lat", "lon"]
    )


def test_builder_reads_only_the_farmland_weighted_rows_of_nghe_an() -> None:
    table = _table([("", 19.0, 105.0, 0.25), ("", 19.0, 105.625, 0.75)])
    assert _label_texts(_parse(grid_figure_svg(table, _zero(), SQUARE))) == {
        "19.0_105.0": "0.25",
        "19.0_105.625": "0.75",
    }


def test_builder_draws_the_listed_zero_weight_cells_of_nghe_an_as_outlines_and_no_other_cell() -> None:
    root = _parse(grid_figure_svg(_table([("", 19.0, 105.625, 1.0)]), _zero((19.0, 105.0)), SQUARE))
    assert set(_cells(root)) == {"19.0_105.0", "19.0_105.625"}
    assert set(_labels(root)) == {"19.0_105.625"}
    assert set(_cells(_parse(grid_figure_svg(_table([("", 19.0, 105.625, 1.0)]), NO_ZERO, SQUARE)))) == {"19.0_105.625"}


def test_builder_refuses_a_cell_listed_both_as_weighted_and_as_zero_weight() -> None:
    with pytest.raises(ValueError, match=r"19\.0_105\.625"):
        grid_figure_svg(_table([("", 19.0, 105.625, 1.0)]), _zero((19.0, 105.625)), SQUARE)


def test_builder_refuses_a_zero_weight_cell_that_does_not_overlap_the_boundary() -> None:
    with pytest.raises(ValueError, match=r"20\.0_105\.0"):
        grid_figure_svg(_table([("", 19.0, 105.625, 1.0)]), _zero((20.0, 105.0)), SQUARE)


def test_builder_refuses_a_weighted_cell_that_does_not_overlap_the_boundary() -> None:
    with pytest.raises(ValueError, match=r"20\.0_105\.0"):
        grid_figure_svg(_table([("", 19.0, 105.0, 0.5), ("", 20.0, 105.0, 0.5)]), NO_ZERO, SQUARE)


def test_builder_refuses_weights_that_do_not_sum_to_1() -> None:
    with pytest.raises(ValueError, match="sum"):
        grid_figure_svg(_table([("", 19.0, 105.0, 0.5)]), NO_ZERO, SQUARE)


def test_builder_refuses_a_table_without_nghe_an_rows() -> None:
    with pytest.raises(ValueError, match="Nghe An"):
        grid_figure_svg(_table([]), NO_ZERO, SQUARE)
