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

from fieldshift.ml.results_chart import results_chart_svg

REPO = Path(__file__).resolve().parents[1]
METRICS = json.loads((REPO / "artifacts" / "metrics.json").read_text(encoding="utf-8"))
SVG_NS = "{http://www.w3.org/2000/svg}"
SKILLS = {"b0": "skill_vs_b0", "b2": "skill_vs_b2", "bnw": "skill_vs_bnw"}
NUMBER = re.compile(r"-?\d+\.\d+")


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
            expected = [f"{skill[k]:.2f}" for k in ("value", "ci90_low", "ci90_high")]
            assert _numbers(g) == expected, (r["season"], r["model_id"], ref)
            assert len(g.findall(f"{SVG_NS}circle")) == 1
            assert len(g.findall(f"{SVG_NS}line")) == 1
    assert len(marks) == 3 * len(rows)


def test_no_reference_row_is_drawn() -> None:
    marks = _marks(results_chart_svg(METRICS))
    assert not {model for _, model, _ in marks} & set(SKILLS)


def test_every_printed_number_is_a_main_model_number_at_two_decimals() -> None:
    allowed = {
        f"{r[key][k]:.2f}"
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
