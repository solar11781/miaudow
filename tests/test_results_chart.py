"""Tests for the results chart of the method page and the slides (UI-UX-SPEC section 11b "Results chart"; item 49).

Spec: per season the main runs only (sensitivity null, scheme rolling_origin, subset national); one row per model, not
the references b0, b2, bnw; for skill_vs_b0, skill_vs_b2 and skill_vs_bnw one mark at value with a line from ci90_low
to ci90_high, a zero line, the numbers beside each mark; inline SVG with role="img", a <title> and a text alternative,
no script, no canvas; a null interval or value is left out, never drawn as zero; 2 decimals (D-160). Expected values
are read from the committed artifacts/metrics.json (E-012, E-013, E-017).
"""

import copy
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from fieldshift.ml.results_chart import results_chart_svg

REPO = Path(__file__).resolve().parents[1]
METRICS = json.loads((REPO / "artifacts" / "metrics.json").read_text(encoding="utf-8"))
SVG_NS = "{http://www.w3.org/2000/svg}"
SKILLS = {"b0": "skill_vs_b0", "b2": "skill_vs_b2", "bnw": "skill_vs_bnw"}
NUMBER = re.compile(r"-?\d+\.\d+")


def _two(x: float) -> str:
    """2 decimals (D-160); minus zero prints as 0.00, like the engine (coordinator decision 2026-11-14)."""
    text = f"{x:.2f}"
    return "0.00" if text == "-0.00" else text


def _main_model_rows(doc: dict) -> list[dict]:
    return [
        r
        for r in doc["metrics"]
        if r["sensitivity"] is None
        and r["scheme"] == "rolling_origin"
        and r["subset"] == "national"
        and r["model_id"] not in SKILLS
    ]


def _parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)  # noqa: S314  our own generated svg, not untrusted input


def _marks(svg: str) -> dict[tuple[str, str, str], ET.Element]:
    root = _parse(svg)
    return {
        (g.get("data-season"), g.get("data-model"), g.get("data-reference")): g
        for g in root.iter(f"{SVG_NS}g")
        if g.get("data-reference") is not None
    }


def _numbers(element: ET.Element) -> list[str]:
    return NUMBER.findall("".join(element.itertext()))


def test_svg_is_an_accessible_image_without_script_or_canvas() -> None:
    root = _parse(results_chart_svg(METRICS))
    assert root.tag == f"{SVG_NS}svg"
    assert root.get("role") == "img"
    assert root[0].tag == f"{SVG_NS}title"
    assert root[0].text
    desc = root.find(f"{SVG_NS}desc")
    assert desc is not None
    assert desc.text
    tags = {el.tag for el in root.iter()}
    assert not tags & {f"{SVG_NS}script", f"{SVG_NS}canvas", f"{SVG_NS}animate", f"{SVG_NS}foreignObject"}


def test_every_main_model_run_has_its_three_marks_with_its_own_numbers() -> None:
    marks = _marks(results_chart_svg(METRICS))
    rows = _main_model_rows(METRICS)
    # metrics.json: m1_ridge, m2_lgbm, m3_rf for spring and winter (E-012, E-013, E-017)
    assert {(r["season"], r["model_id"]) for r in rows} == {
        (s, m) for s in ("spring", "winter") for m in ("m1_ridge", "m2_lgbm", "m3_rf")
    }
    for r in rows:
        for ref, key in SKILLS.items():
            skill = r[key]
            g = marks[(r["season"], r["model_id"], ref)]
            expected = [_two(skill[k]) for k in ("value", "ci90_low", "ci90_high")]
            assert _numbers(g) == expected, (r["season"], r["model_id"], ref)
            assert len(g.findall(f"{SVG_NS}circle")) == 1
            assert len(g.findall(f"{SVG_NS}line")) == 1
    assert len(marks) == 3 * len(rows)


def test_no_reference_row_is_drawn() -> None:
    marks = _marks(results_chart_svg(METRICS))
    assert not {model for _, model, _ in marks} & set(SKILLS)


def test_every_printed_number_is_a_main_model_number_at_two_decimals() -> None:
    allowed = {
        _two(r[key][k])
        for r in _main_model_rows(METRICS)
        for key in SKILLS.values()
        for k in r[key]
        if r[key][k] is not None
    }
    root = _parse(results_chart_svg(METRICS))
    printed = _numbers(root)
    assert printed
    assert set(printed) <= allowed


def test_only_seasons_with_model_rows_appear() -> None:
    doc = copy.deepcopy(METRICS)
    doc["metrics"] = [r for r in doc["metrics"] if not (r["season"] == "winter" and r["model_id"] not in SKILLS)]
    seasons = {season for season, _, _ in _marks(results_chart_svg(doc))}
    assert seasons == {"spring"}


def _one_row_doc(skill_vs_b0: dict | None, skill_vs_b2: dict | None) -> dict:
    row = {
        "model_id": "m1_ridge",
        "season": "spring",
        "role": "primary",
        "scheme": "rolling_origin",
        "sensitivity": None,
        "subset": "national",
        "skill_vs_b0": skill_vs_b0,
        "skill_vs_b2": skill_vs_b2,
        "skill_vs_bnw": None,
    }
    return {"metrics": [row]}


def test_a_null_interval_gives_a_mark_without_an_interval_line() -> None:
    doc = _one_row_doc({"value": 0.25, "ci90_low": None, "ci90_high": None}, None)
    marks = _marks(results_chart_svg(doc))
    g = marks[("spring", "m1_ridge", "b0")]
    assert len(g.findall(f"{SVG_NS}circle")) == 1
    assert g.findall(f"{SVG_NS}line") == []
    assert _numbers(g) == ["0.25"]


def test_a_null_value_or_null_skill_gives_no_mark() -> None:
    doc = _one_row_doc({"value": None, "ci90_low": None, "ci90_high": None}, None)
    marks = _marks(results_chart_svg(doc))
    assert ("spring", "m1_ridge", "b0") not in marks
    assert ("spring", "m1_ridge", "b2") not in marks
    assert ("spring", "m1_ridge", "bnw") not in marks


def test_committed_svg_matches_the_committed_metrics() -> None:
    committed = (REPO / "artifacts" / "figures" / "results_chart.svg").read_text(encoding="utf-8")
    assert committed == results_chart_svg(METRICS)


def _luminance(hex_colour: str) -> float:
    """WCAG 2.1 relative luminance of an sRGB colour #rrggbb."""
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def test_text_contrast_is_at_least_4_5_to_1_on_the_background() -> None:
    root = _parse(results_chart_svg(METRICS))
    background = root.find(f"{SVG_NS}rect").get("fill")
    for text in root.iter(f"{SVG_NS}text"):
        fill = text.get("fill") or root.get("fill")
        lighter, darker = sorted((_luminance(fill), _luminance(background)), reverse=True)
        # WCAG 2.1 success criterion 1.4.3: contrast (L1 + 0.05) / (L2 + 0.05) at least 4.5:1 (UI-UX-SPEC H8)
        assert (lighter + 0.05) / (darker + 0.05) >= 4.5, text.text


def test_minus_zero_prints_as_zero() -> None:
    doc = _one_row_doc({"value": -0.001, "ci90_low": -0.004, "ci90_high": 0.02}, None)
    svg = results_chart_svg(doc)
    assert _numbers(_marks(svg)[("spring", "m1_ridge", "b0")]) == ["0.00", "0.00", "0.02"]
    assert "-0.00" not in svg


def test_committed_svg_has_no_minus_zero() -> None:
    assert "-0.00" not in (REPO / "artifacts" / "figures" / "results_chart.svg").read_text(encoding="utf-8")


def test_every_number_label_sits_on_a_white_rectangle_so_no_line_shows_through_it() -> None:
    marks = _marks(results_chart_svg(METRICS))
    for key, g in marks.items():
        (label,) = g.findall(f"{SVG_NS}text")
        (box,) = g.findall(f"{SVG_NS}rect")
        children = list(g)
        assert children.index(box) < children.index(label), key  # drawn first, so it lies behind the text
        assert box.get("fill") == "#ffffff", key
        x, y, w, h = (float(box.get(k)) for k in ("x", "y", "width", "height"))
        tx, ty = float(label.get("x")), float(label.get("y"))
        assert x + w / 2 == pytest.approx(tx, abs=0.11), key  # centred on the middle-anchored label
        # Arial at 12 px: digits advance 0.556 em, capitals rise 0.716 em, brackets drop 0.21 em (Arial font metrics)
        assert w >= len(label.text) * 0.556 * 12, key
        assert y <= ty - 0.716 * 12, key
        assert y + h >= ty + 0.21 * 12, key
        dot = g.find(f"{SVG_NS}circle")
        assert y >= float(dot.get("cy")) + float(dot.get("r")), key  # the rectangle never hides the dot
