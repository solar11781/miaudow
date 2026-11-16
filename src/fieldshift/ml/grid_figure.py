"""The Nghệ An grid figure of the method page (UI-UX-SPEC section 11b item 4; D-135 (3); 05-DATA-CONTRACTS 5c).

Plain words: the province boundary drawn over its NASA POWER weather cells. Each cell with farmland is shaded by its
farmland weight (its share of the province's farmland, D-26) and the weight is printed in it; a cell of the province
that holds no farmland in the fixed mask is an outline only. Both lists come from the pipeline, so the figure cannot
disagree with it: the weights of data/processed/cell_weights.csv and the zero-weight cells of
data/processed/cell_weights_zero.csv (scripts/build_cell_weights.py); the figure adds no number (D-135). No map projection and no base map: longitude and
latitude are drawn as a plain grid, longitude scaled by the cosine of the middle latitude so a degree of longitude
is about as long on screen as on the ground.
"""

from __future__ import annotations

import math
import textwrap

import pandas as pd
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry

from fieldshift.features.farmland_weights import POWER_DLAT, POWER_DLON
from fieldshift.ml.results_chart import BACKGROUND, MARK, TEXT, ZERO, svg_header, svg_text

PROVINCE = "Nghe An"  # NSO unit name in cell_weights.csv (05-DATA-CONTRACTS section 3)
METHOD = "farmland_weighted"  # the main weights, not the E-008 centroid rows (05-DATA-CONTRACTS section 3)
WEIGHT_SUM_TOLERANCE = 1e-9  # the weights of a unit sum to 1 (05-DATA-CONTRACTS section 3); float error only

# English like the results chart (slides) and Vietnamese for the Vietnamese page; the page adds method.gridAlt and
# method.gridCaption. Sources are named as the app's source lists name them: no decision or register ids, no file paths.
TEXTS = {
    "en": {
        "title": "NASA POWER weather cells over Nghe An, shaded by farmland weight",
        "weighted": "Farmland weight, printed in the cell; darker is larger",
        "zero": "Cell with Nghe An land pixels but farmland weight 0",
        "boundary": "Nghe An boundary",
        "caption": (
            "Sources: NASA POWER cells of {dlat} x {dlon} degrees. Farmland weights from NASA MODIS land"
            " cover MCD12C1 with the fixed farmland mask. Boundary: geoBoundaries gbOpen VNM ADM1 (Runfola et al."
            " 2020). Drawn as plain longitude and latitude, longitude scaled by cos(latitude) at the middle latitude;"
            " no base map. Weights rounded to 2 decimals, so the printed values may not sum to exactly 1."
        ),
        "desc_intro": (
            "The {boundary} drawn over the {n} NASA POWER cells that hold the province's MODIS land pixels. Farmland"
            " weight of each cell, by its centre:"
        ),
        "desc_zero": "cells with farmland weight 0:",
        "coords": "{lat} N, {lon} E",
    },
    "vi": {
        "title": "Các ô lưới thời tiết NASA POWER phủ Nghệ An, tô theo trọng số đất trồng",
        "weighted": "Trọng số đất trồng, in trong ô; càng đậm càng lớn",
        "zero": "Ô có điểm ảnh đất Nghệ An nhưng trọng số đất trồng bằng 0",
        "boundary": "Ranh giới tỉnh Nghệ An",
        "caption": (
            "Nguồn: ô lưới NASA POWER rộng {dlat} x {dlon} độ. Trọng số đất trồng lấy từ lớp phủ mặt đất"
            " NASA MODIS MCD12C1 với mặt nạ đất trồng cố định. Ranh giới: geoBoundaries gbOpen VNM ADM1 (Runfola và"
            " cộng sự, 2020). Vẽ theo kinh độ và vĩ độ thẳng, kinh độ nhân với cos(vĩ độ) ở vĩ độ giữa; không có bản"
            " đồ nền. Trọng số làm tròn đến 2 chữ số thập phân, nên các số in ra có thể không cộng đúng bằng 1."
        ),
        "desc_intro": (
            "{boundary} vẽ trên {n} ô lưới NASA POWER có điểm ảnh đất của tỉnh theo MODIS. Trọng số đất trồng của"
            " từng ô, theo tâm ô:"
        ),
        "desc_zero": "các ô có trọng số đất trồng bằng 0:",
        "coords": "{lat} độ Bắc, {lon} độ Đông",
    },
}
DECIMAL_SEPARATOR = {"en": ".", "vi": ","}  # Vietnamese writes decimals with a comma (vi.ts, GLOSSARY)

# layout in px (routine choice, D-102): narrow, so the labels stay readable when a phone scales the figure down
WIDTH = 400
SIDE = 16
DEGREE = 150  # px per degree of latitude
TITLE_CHARS = 38
CAPTION_CHARS = 56
SHADE_MAX = 0.85  # fill opacity of the largest weight; the white label box keeps the number readable on it
LEGEND_CHARS = 54  # characters of a legend line at 13 px that fit beside the swatch in WIDTH
LEGEND_LINE = 16  # px between wrapped lines of one legend item
LABEL_BOX = (44, 21)  # px around a 17 px bold "0.47"


def _weights(table: pd.DataFrame) -> dict[tuple[float, float], float]:
    rows = table[(table["province_nso"] == PROVINCE) & (table["method"] == METHOD)]
    if rows.empty:
        raise ValueError(f"no {METHOD} rows for {PROVINCE} in the cell weights table")
    total = float(rows["farmland_weight"].sum())
    if abs(total - 1) > WEIGHT_SUM_TOLERANCE:
        raise ValueError(f"the {PROVINCE} farmland weights sum to {total}, not 1")
    return {(float(r.lat), float(r.lon)): float(r.farmland_weight) for r in rows.itertuples()}


def _cell(lat: float, lon: float) -> Polygon:
    return box(lon - POWER_DLON / 2, lat - POWER_DLAT / 2, lon + POWER_DLON / 2, lat + POWER_DLAT / 2)


def _zero_cells(zero_table: pd.DataFrame) -> set[tuple[float, float]]:
    rows = zero_table[zero_table["province_nso"] == PROVINCE]
    return {(float(r.lat), float(r.lon)) for r in rows.itertuples()}


def _cell_id(lat: float, lon: float) -> str:
    return f"{lat}_{lon}"  # the cell_id of cell_weights.csv (scripts/build_cell_weights.py)


def _rings(boundary: BaseGeometry) -> list:
    polygons = getattr(boundary, "geoms", [boundary])
    return [ring for p in polygons for ring in (p.exterior, *p.interiors)]


def _legend(y: float, items: list[str]) -> tuple[list[str], float]:
    """The three legend items from y down (a long one wraps onto more lines) and the height they use."""
    lines = [textwrap.wrap(item, LEGEND_CHARS) for item in items]
    tops = [y + 22 * i + LEGEND_LINE * sum(len(prev) - 1 for prev in lines[:i]) for i in range(3)]
    swatches = [
        f'<rect x="{SIDE}" y="{tops[0] - 12}" width="22" height="14" fill="{MARK}" fill-opacity="{SHADE_MAX / 2}"'
        f' stroke="{ZERO}"/>',
        f'<rect x="{SIDE}" y="{tops[1] - 12}" width="22" height="14" fill="none" stroke="{ZERO}"'
        ' stroke-dasharray="5 4"/>',
        f'<line x1="{SIDE}" y1="{tops[2] - 5}" x2="{SIDE + 22}" y2="{tops[2] - 5}" stroke="{TEXT}" stroke-width="2"/>',
    ]
    texts = [
        svg_text(SIDE + 30, top + LEGEND_LINE * k, line, ' font-size="13"')
        for top, item in zip(tops, lines, strict=True)
        for k, line in enumerate(item)
    ]
    return [*swatches, *texts], tops[2] + LEGEND_LINE * (len(lines[2]) - 1) - y


def grid_figure_svg(table: pd.DataFrame, zero_table: pd.DataFrame, boundary: BaseGeometry, lang: str = "en") -> str:
    """The figure as standalone SVG text in "en" or "vi", from the cell weights table and the zero-weight cell list
    (05 section 3) and the Nghệ An boundary. The drawing and every number are the same in both languages."""
    if lang not in TEXTS:
        raise ValueError(f"lang must be one of {sorted(TEXTS)}, not {lang!r}")
    text = TEXTS[lang]

    def num(value: str) -> str:
        return value.replace(".", DECIMAL_SEPARATOR[lang])

    weights = _weights(table)
    zero_cells = _zero_cells(zero_table)
    both = sorted(zero_cells & set(weights))
    if both:
        raise ValueError(f"cells listed both with a weight and with weight 0: {[_cell_id(*c) for c in both]}")
    cells = sorted(set(weights) | zero_cells)
    outside = [c for c in cells if _cell(*c).intersection(boundary).area <= 0]
    if outside:
        raise ValueError(f"cells that do not overlap the {PROVINCE} boundary: {[_cell_id(*c) for c in outside]}")
    west, south, east, north = (
        min(lo for _, lo in cells) - POWER_DLON / 2,
        min(la for la, _ in cells) - POWER_DLAT / 2,
        max(lo for _, lo in cells) + POWER_DLON / 2,
        max(la for la, _ in cells) + POWER_DLAT / 2,
    )
    x_scale = DEGREE * math.cos(math.radians((south + north) / 2))
    title_lines = textwrap.wrap(text["title"], TITLE_CHARS)
    top = 16 + 24 * len(title_lines)
    left = (WIDTH - (east - west) * x_scale) / 2

    def xy(lon: float, lat: float) -> tuple[float, float]:
        return left + (lon - west) * x_scale, top + (north - lat) * DEGREE

    def cell(lat: float, lon: float) -> str:
        x0, y0 = xy(lon - POWER_DLON / 2, lat + POWER_DLAT / 2)
        rect = f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{POWER_DLON * x_scale:.1f}" height="{POWER_DLAT * DEGREE:.1f}"'
        weight = weights.get((lat, lon))
        if weight is None:
            return (
                f'<g data-cell="{_cell_id(lat, lon)}">{rect} fill="none" stroke="{ZERO}" stroke-dasharray="5 4"/></g>'
            )
        shade = SHADE_MAX * weight / max(weights.values())
        return (
            f'<g data-cell="{_cell_id(lat, lon)}">{rect} fill="{MARK}" fill-opacity="{shade:.3f}" stroke="{ZERO}"/></g>'
        )

    def label(lat: float, lon: float) -> str:
        """The printed weight on a white box, drawn after the boundary so the line never crosses it."""
        cx, cy = xy(lon, lat)
        w, h = LABEL_BOX
        return (
            f'<g data-label="{_cell_id(lat, lon)}"><rect x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w}"'
            f' height="{h}" rx="3" fill="{BACKGROUND}"/>'
            + svg_text(
                cx, cy + 6, num(f"{weights[lat, lon]:.2f}"), ' font-size="17" font-weight="bold" text-anchor="middle"'
            )
            + "</g>"
        )

    path = " ".join(
        "M " + " L ".join("{:.1f},{:.1f}".format(*xy(lon, lat)) for lon, lat in ring.coords) + " Z"
        for ring in _rings(boundary)
    )
    legend_y = top + round((north - south) * DEGREE) + 28
    legend, legend_height = _legend(legend_y, [text["weighted"], text["zero"], text["boundary"]])
    caption = text["caption"].format(dlat=num(str(POWER_DLAT)), dlon=num(str(POWER_DLON)))
    caption_lines = textwrap.wrap(caption, CAPTION_CHARS)
    caption_y = legend_y + legend_height + 28
    height = caption_y + 17 * len(caption_lines)

    def coords(lat: float, lon: float) -> str:
        return text["coords"].format(lat=num(str(lat)), lon=num(str(lon)))

    weighted = [
        f"{coords(lat, lon)}: {num(f'{weights[lat, lon]:.2f}')};" for lat, lon in cells if (lat, lon) in weights
    ]
    zero = [f"{coords(lat, lon)};" for lat, lon in cells if (lat, lon) not in weights]
    desc = " ".join(
        [
            text["desc_intro"].format(boundary=text["boundary"], n=len(cells)),
            *weighted,
            text["desc_zero"],
            *zero,
            caption,
        ]
    )
    return "\n".join(
        [
            *svg_header("grid-figure", text["title"], desc, (WIDTH, height), SIDE, title_lines),
            # outlines first, so the solid edges of the weighted cells are drawn over the shared dashed edges
            *(cell(*c) for c in sorted(cells, key=lambda c: c in weights)),
            f'<path d="{path}" fill="none" stroke="{TEXT}" stroke-width="2" stroke-linejoin="round"/>',
            *(label(*c) for c in cells if c in weights),
            *legend,
            *(svg_text(SIDE, caption_y + 17 * i, t, ' font-size="12"') for i, t in enumerate(caption_lines)),
            "</svg>",
            "",
        ]
    )
