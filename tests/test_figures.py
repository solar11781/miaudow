"""Tests for the README and submission figures (queue item 34; EVENING-AUTOPILOT row 5: no new claims, H5).

Spec: from the committed artifacts only; each figure an SVG with role="img", a <title>, a text alternative and a source
caption; past years labelled as past years, never as a forecast; a null value left out, never drawn as zero. Rice:
artifacts/risk_table.json Nghệ An rows (05-DATA-CONTRACTS section 5): the real anomaly per season and year, and the
out-of-sample estimate with its 80% range only where the artifact holds them and the season's model is shown. Rules:
the `year` rows of artifacts/hazard_labels.json (section 4b), one panel per rule. Text values as whole percent, half up
(D-95). Expected values are read from the committed artifacts and rules files.
"""

import copy
import json
import xml.etree.ElementTree as ET
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
import yaml

from fieldshift.ml.figures import rice_history_svg, rule_shares_svg

REPO = Path(__file__).resolve().parents[1]
FIGURES = REPO / "docs" / "figures"
RISK = json.loads((REPO / "artifacts" / "risk_table.json").read_text(encoding="utf-8"))
HAZARDS = json.loads((REPO / "artifacts" / "hazard_labels.json").read_text(encoding="utf-8"))
METHOD = yaml.safe_load((REPO / "rules" / "method.yaml").read_text(encoding="utf-8"))
CONDITIONS = yaml.safe_load((REPO / "rules" / "conditions.yaml").read_text(encoding="utf-8"))
SVG_NS = "{http://www.w3.org/2000/svg}"
NGHE_AN = "Nghe An"  # risk_table.json unit_id of Nghệ An (province_nso spelling)
RULES = ["heavy_rain", "heat", "drought_rain_consecutive", "drought_rain_any2", "cold"]  # rules/conditions.yaml order


def _pct(x: float) -> str:
    """Whole percent, half up (D-95); minus zero prints as 0."""
    shown = (Decimal(str(x)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return str(abs(shown) if shown == 0 else shown)


def _rice() -> str:
    return rice_history_svg(RISK, METHOD)


def _rules() -> str:
    return rule_shares_svg(HAZARDS, CONDITIONS)


def _parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)  # noqa: S314  our own generated svg, not untrusted input


def _nghe_an(doc: dict) -> list[dict]:
    return [r for r in doc["rows"] if r["unit_id"] == NGHE_AN and r["crop"] == "rice"]


def _year_rows(doc: dict) -> list[dict]:
    return [r for r in doc["rows"] if r["level"] == "year"]


def _all_text(root: ET.Element) -> str:
    return " ".join(t for el in root.iter() for t in (el.text, el.tail) if t)


def _y_of(panel: ET.Element):
    """The panel's value -> y mapping, read from two of its tick lines (data-tick = the tick's fraction)."""
    ticks = sorted(
        (float(t.get("data-tick")), float(t.get("y1"))) for t in panel.iter(f"{SVG_NS}line") if t.get("data-tick")
    )
    (v0, y0), (v1, y1) = ticks[0], ticks[-1]
    return lambda v: y0 + (v - v0) * (y1 - y0) / (v1 - v0)


def _bar_ends(rect: ET.Element) -> list[float]:
    y = float(rect.get("y"))
    return sorted([y, y + float(rect.get("height"))])


def _panel(root: ET.Element, key: str, value: str) -> ET.Element:
    (panel,) = [g for g in root.iter(f"{SVG_NS}g") if g.get(key) == value and g.get("data-year") is None]
    return panel


@pytest.mark.parametrize("build", [_rice, _rules])
def test_figure_is_an_accessible_image_with_a_title_and_a_source_caption(build) -> None:
    root = _parse(build())
    assert root.tag == f"{SVG_NS}svg"
    assert root.get("role") == "img"
    assert root[0].tag == f"{SVG_NS}title"
    assert root[0].text
    desc = root.find(f"{SVG_NS}desc")
    assert desc is not None
    assert desc.text
    assert any((t.text or "").startswith("Source: artifacts/") for t in root.iter(f"{SVG_NS}text"))
    tags = {el.tag for el in root.iter()}
    assert not tags & {f"{SVG_NS}script", f"{SVG_NS}canvas", f"{SVG_NS}animate", f"{SVG_NS}foreignObject"}


@pytest.mark.parametrize("build", [_rice, _rules])
def test_past_years_are_labelled_and_never_called_a_forecast(build) -> None:
    root = _parse(build())
    text = _all_text(root).lower()
    assert "past years" in root[0].text.lower()
    assert "past years, not a forecast" in text
    # every "forecast" in the figure is the "not a forecast" label (CLAUDE.md: past years are never forecasts)
    assert text.count("forecast") == text.count("not a forecast")
    assert "predict" not in text


def test_every_rice_bar_is_drawn_at_its_artifact_value() -> None:
    root = _parse(_rice())
    rows = _nghe_an(RISK)
    # risk_table.json: 30 Nghệ An rice years 1995-2024 for spring, summer_autumn and winter (05-DATA-CONTRACTS 5)
    assert {r["season"] for r in rows} == {"spring", "summer_autumn", "winter"}
    bars = {
        (b.get("data-season"), int(b.get("data-year"))): b for b in root.iter(f"{SVG_NS}rect") if b.get("data-year")
    }
    for season in ("spring", "summer_autumn", "winter"):
        y_of = _y_of(_panel(root, "data-season", season))
        for r in (r for r in rows if r["season"] == season and r["anom_history"] is not None):
            assert _bar_ends(bars[(season, r["year"])]) == pytest.approx(
                sorted([y_of(0.0), y_of(r["anom_history"])]), abs=0.11
            ), (season, r["year"])
    assert len(bars) == sum(r["anom_history"] is not None for r in rows)


def test_rice_estimates_and_ranges_are_drawn_only_where_the_artifact_holds_them() -> None:
    root = _parse(_rice())
    shown = {s["season"] for s in RISK["seasons"] if s["model_status"] == "shown"}
    expected = [r for r in _nghe_an(RISK) if r["season"] in shown and r["anom_oos"] is not None]
    # risk_table.json: winter is the only shown season; estimates 2016-2024 with 80% ranges (E-012)
    assert {(r["season"], r["year"]) for r in expected} == {("winter", y) for y in range(2016, 2025)}
    marks = {
        (g.get("data-season"), int(g.get("data-year"))): g for g in root.iter(f"{SVG_NS}g") if g.get("data-estimate")
    }
    assert set(marks) == {(r["season"], r["year"]) for r in expected}
    y_of = _y_of(_panel(root, "data-season", "winter"))
    for r in expected:
        g = marks[(r["season"], r["year"])]
        (dot,) = g.findall(f"{SVG_NS}circle")
        assert float(dot.get("cy")) == pytest.approx(y_of(r["anom_oos"]), abs=0.06)
        (line,) = g.findall(f"{SVG_NS}line")
        ends = sorted([float(line.get("y1")), float(line.get("y2"))])
        assert ends == pytest.approx(sorted([y_of(r["oos_low_80"]), y_of(r["oos_high_80"])]), abs=0.06)


def test_rice_text_alternative_lists_every_value_as_whole_percent() -> None:
    desc = _parse(_rice()).find(f"{SVG_NS}desc").text
    for r in _nghe_an(RISK):
        if r["anom_history"] is None:
            assert f"{r['year']} no value" in desc
        else:
            assert f"{r['year']} {_pct(r['anom_history'])}%" in desc
        if r["anom_oos"] is not None and r["season"] == "winter":
            assert (
                f"{r['year']} estimate {_pct(r['anom_oos'])}% (80% range {_pct(r['oos_low_80'])}% to"
                f" {_pct(r['oos_high_80'])}%)"
            ) in desc


def test_a_null_rice_value_is_left_out_and_an_estimate_without_a_range_has_no_line() -> None:
    doc = copy.deepcopy(RISK)
    for r in _nghe_an(doc):
        if (r["season"], r["year"]) == ("spring", 2010):
            r["anom_history"] = None
        if (r["season"], r["year"]) == ("winter", 2020):
            r["oos_low_80"] = r["oos_high_80"] = None
    root = _parse(rice_history_svg(doc, METHOD))
    years = {(b.get("data-season"), b.get("data-year")) for b in root.iter(f"{SVG_NS}rect") if b.get("data-year")}
    assert ("spring", "2010") not in years
    assert ("spring", "1995") not in years  # null in the committed artifact
    (g,) = [g for g in root.iter(f"{SVG_NS}g") if g.get("data-estimate") and g.get("data-year") == "2020"]
    assert g.findall(f"{SVG_NS}line") == []
    assert len(g.findall(f"{SVG_NS}circle")) == 1


def test_no_estimate_is_drawn_for_a_season_whose_model_is_not_shown() -> None:
    doc = copy.deepcopy(RISK)
    for s in doc["seasons"]:
        if s["season"] == "winter":
            s["model_status"] = "not_shown"
    root = _parse(rice_history_svg(doc, METHOD))
    assert [g for g in root.iter(f"{SVG_NS}g") if g.get("data-estimate")] == []


def test_every_rule_bar_is_drawn_at_its_artifact_share() -> None:
    root = _parse(_rules())
    rows = _year_rows(HAZARDS)
    # hazard_labels.json: 30 year rows (1995-2024) for each of the five rules (E-019)
    assert sorted({r["rule"] for r in rows}) == sorted(RULES)
    bars = {(b.get("data-rule"), int(b.get("data-year"))): b for b in root.iter(f"{SVG_NS}rect") if b.get("data-year")}
    for rule in RULES:
        y_of = _y_of(_panel(root, "data-rule", rule))
        for r in (r for r in rows if r["rule"] == rule):
            assert _bar_ends(bars[(rule, r["year"])]) == pytest.approx(
                sorted([y_of(0.0), y_of(r["share_farmland"])]), abs=0.11
            ), (rule, r["year"])
    assert len(bars) == len(rows)


def test_rule_panels_follow_the_rules_file_with_its_labels() -> None:
    root = _parse(_rules())
    panels = [g.get("data-rule") for g in root.iter(f"{SVG_NS}g") if g.get("data-rule") and g.get("data-year") is None]
    assert panels == [c["code"] for c in CONDITIONS]
    text = _all_text(root)
    for c in CONDITIONS:
        assert c["label"]["en"] in text


def test_rule_text_alternative_lists_every_share_as_whole_percent() -> None:
    desc = _parse(_rules()).find(f"{SVG_NS}desc").text
    for r in _year_rows(HAZARDS):
        assert f"{r['year']} {_pct(r['share_farmland'])}%" in desc


def test_a_null_share_is_left_out_not_drawn_as_zero() -> None:
    doc = copy.deepcopy(HAZARDS)
    for r in _year_rows(doc):
        if (r["rule"], r["year"]) == ("cold", 2000):
            r["share_farmland"] = None
    root = _parse(rule_shares_svg(doc, CONDITIONS))
    years = {(b.get("data-rule"), b.get("data-year")) for b in root.iter(f"{SVG_NS}rect") if b.get("data-year")}
    assert ("cold", "2000") not in years
    assert ("heat", "2000") in years
    assert "2000 no value" in root.find(f"{SVG_NS}desc").text


def test_tick_labels_are_the_whole_percent_of_their_tick() -> None:
    for svg in (_rice(), _rules()):
        for g in _parse(svg).iter(f"{SVG_NS}g"):
            if g.get("data-tick-label"):
                (label,) = g.findall(f"{SVG_NS}text")
                assert label.text == f"{_pct(float(g.get('data-tick-label')))}%"


def test_two_rows_for_one_year_fail_loudly() -> None:
    doc = copy.deepcopy(HAZARDS)
    doc["rows"].append(copy.deepcopy(_year_rows(doc)[0]))
    with pytest.raises(ValueError, match="two year rows"):
        rule_shares_svg(doc, CONDITIONS)


@pytest.mark.parametrize(("name", "build"), [("rice_anomaly_history.svg", _rice), ("farmland_rule_shares.svg", _rules)])
def test_committed_svg_equals_the_builder_output(name: str, build) -> None:
    assert (FIGURES / name).read_text(encoding="utf-8") == build()
