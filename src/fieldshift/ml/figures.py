"""README and submission figures from the committed artifacts (no new claims, H5).

Plain words: two charts of past years, drawn only from numbers that are already in the artifacts. (1) Nghệ An rice
yield against its normal per season and year (artifacts/risk_table.json), with the M1 out-of-sample estimate and its
80% range where the artifact holds them for a season whose model is shown. (2) The share of Nghệ An farmland where each
official rule was met per year (the `year` rows of artifacts/hazard_labels.json), one panel per rule. A null value is
left out and marked "n/a", never drawn as zero. The app itself shows numbers, not these images.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal

from fieldshift.ml.results_chart import BACKGROUND, LABEL_X, WIDTH, ZERO, svg_document, svg_text

NGHE_AN = "Nghe An"  # risk_table.json unit_id of Nghệ An (province_nso spelling, 05-DATA-CONTRACTS section 5)
RICE = "rice"
SEASONS = ("spring", "summer_autumn", "winter")  # NSO rice seasons in calendar order (rules/method.yaml season_labels)
STATUS_NOTES = {  # risk_table.json seasons[].model_status (UI-UX-SPEC section 11)
    "shown": "",
    "not_shown": "Model estimates not shown for this season; the reason is on the method page.",
    "not_modeled": "This season is not modelled; no model estimates.",
}

BAR = "#1f4e79"  # the results chart's mark colour, 8.7:1 on white
ESTIMATE = "#b04a00"  # 5.5:1 on white (WCAG 2.1 non-text contrast needs 3:1)
GRID = "#d9d9d9"  # decorative grid lines; the zero line uses ZERO

# layout in px (routine choice, D-102)
PLOT_X0 = 64
PLOT_X1 = WIDTH - 16
PANEL_HEAD = 30  # panel title line above the plot
PANEL_FOOT = 30  # year labels below the plot
RICE_STEP, RICE_PX = 10, 2.0  # ticks every 10 percentage points, 2 px per percentage point
SHARE_STEP, SHARE_PX = 50, 0.6  # ticks at 0, 50 and 100%, 0.6 px per percentage point


# mirrors engine/values.py whole_percent (D-95); a copy because the layer rules forbid ml from importing engine
def _percent(fraction: float) -> str:
    """Whole percent, half up; minus zero is "0"."""
    shown = (Decimal(str(fraction)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return str(abs(shown) if shown == 0 else shown)


def _slot(i: int, n: int) -> tuple[float, float]:
    """(left edge, width) of the i-th of n year slots across the plot."""
    width = (PLOT_X1 - PLOT_X0) / n
    return PLOT_X0 + i * width, width


def _axis(top: int, lo: int, hi: int, step: int, px: float) -> tuple[list[str], Callable[[float], float]]:
    """Grid lines with whole-percent labels from lo to hi percent, and the fraction -> y mapping of the panel."""

    def y_of(fraction: float) -> float:
        return top + (hi - fraction * 100) * px

    out = []
    for tick in range(lo, hi + 1, step):
        fraction = Decimal(tick) / 100
        y = y_of(float(fraction))
        colour = ZERO if tick == 0 else GRID
        out.append(
            f'<g data-tick-label="{fraction}"><line data-tick="{fraction}" x1="{PLOT_X0}" y1="{y:.1f}" x2="{PLOT_X1}"'
            f' y2="{y:.1f}" stroke="{colour}"/>'
            + svg_text(PLOT_X0 - 6, y + 4, f"{_percent(float(fraction))}%", ' font-size="12" text-anchor="end"')
            + "</g>"
        )
    return out, y_of


def _year_labels(years: list[int], bottom: float) -> list[str]:
    """Every fifth year and the last one under the plot."""
    out = []
    for i, year in enumerate(years):
        if year % 5 == 0 or year == years[-1]:
            left, width = _slot(i, len(years))
            out.append(svg_text(left + width / 2, bottom + 16, str(year), ' font-size="12" text-anchor="middle"'))
    return out


def _bar(attrs: str, x: float, width: float, fraction: float, y_of: Callable[[float], float]) -> str:
    """A bar from 0 to the value; both ends rounded once, so the drawn ends are the value's ends."""
    top, bottom = round(y_of(max(fraction, 0.0)), 1), round(y_of(min(fraction, 0.0)), 1)
    return f'<rect {attrs} x="{x:.1f}" y="{top:.1f}" width="{width:.1f}" height="{bottom - top:.1f}" fill="{BAR}"/>'


def _missing(x: float, y_zero: float) -> str:
    return svg_text(x, y_zero - 4, "n/a", f' font-size="10" text-anchor="middle" fill="{ZERO}"')


def _value_list(values: dict[int, float | None]) -> str:
    return ", ".join(f"{y} no value" if v is None else f"{y} {_percent(v)}%" for y, v in sorted(values.items()))


def _caption(lines: list[str], y: float) -> list[str]:
    return [svg_text(LABEL_X, y + 12 + 16 * i, line, ' font-size="12"') for i, line in enumerate(lines)]


def _body_top(legend: list[str]) -> int:
    return 52 + 16 * len(legend) + 8


def _rice_rows(risk: dict) -> dict[str, dict[int, dict]]:
    out: dict[str, dict[int, dict]] = {}
    for r in risk["rows"]:
        if (r["unit_id"], r["crop"]) != (NGHE_AN, RICE):
            continue
        if r["season"] not in SEASONS:
            raise ValueError(f"risk_table.json: unknown rice season {r['season']!r}")
        if r["year"] in out.get(r["season"], {}):
            raise ValueError(f"risk_table.json: two rows for {NGHE_AN} {r['season']} {r['year']}")
        out.setdefault(r["season"], {})[r["year"]] = r
    return out


def _estimates(by_year: dict[int, dict], status: str) -> dict[int, dict]:
    """The years with an out-of-sample estimate, only for a season whose model is shown (D-82, D-83)."""
    if status not in STATUS_NOTES:
        raise ValueError(f"risk_table.json: unknown model_status {status!r}")
    return {y: r for y, r in by_year.items() if status == "shown" and r["anom_oos"] is not None}


def _range(r: dict) -> tuple[float, float] | None:
    low, high = r["oos_low_80"], r["oos_high_80"]
    return None if low is None or high is None else (low, high)


def _estimate_text(year: int, r: dict) -> str:
    ci = _range(r)
    text = f"{year} estimate {_percent(r['anom_oos'])}%"
    return text if ci is None else f"{text} (80% range {_percent(ci[0])}% to {_percent(ci[1])}%)"


def rice_history_svg(risk: dict, method: dict) -> str:
    """Nghệ An rice yield against its normal per season and year, from risk_table.json; labels from rules/method.yaml."""
    rows = _rice_rows(risk)
    status = {s["season"]: s["model_status"] for s in risk["seasons"]}
    seasons = [s for s in SEASONS if s in rows]
    estimates = {s: _estimates(rows[s], status[s]) for s in seasons}
    years = sorted({y for s in seasons for y in rows[s]})
    values = [0.0]
    for s in seasons:
        values += [r["anom_history"] for r in rows[s].values() if r["anom_history"] is not None]
        values += [v for r in estimates[s].values() for v in (r["anom_oos"], *(_range(r) or ()))]
    lo = math.floor(min(values) * 100 / RICE_STEP) * RICE_STEP
    hi = math.ceil(max(values) * 100 / RICE_STEP) * RICE_STEP
    plot_h = round((hi - lo) * RICE_PX)

    title = f"Nghệ An rice yield against normal, per season, past years {years[0]}-{years[-1]}"
    legend = [
        "Past years, not a forecast. Bar: the NSO rice yield of the year against its past-only normal, in %. n/a: no value.",
        "Open dot: the M1 out-of-sample estimate of a test year, from a model trained on earlier years only. Line: its"
        " 80% range.",
    ]
    body: list[str] = []
    desc = [f"{title}. Past years, not a forecast."]
    y = _body_top(legend)
    for season in seasons:
        label = method["season_labels"][season]["label"]
        name = f"Rice, {label['en']} ({label['vi']})"
        note = STATUS_NOTES[status[season]]
        body.append(f'<g data-season="{season}">')
        body.append(svg_text(LABEL_X, y + 18, name, ' font-weight="bold"'))
        if note:
            body.append(svg_text(PLOT_X1, y + 18, note, ' font-size="12" text-anchor="end"'))
        top = y + PANEL_HEAD
        ticks, y_of = _axis(top, lo, hi, RICE_STEP, RICE_PX)
        body += ticks
        for i, year in enumerate(years):
            left, width = _slot(i, len(years))
            r = rows[season].get(year)
            if r is None or r["anom_history"] is None:
                body.append(_missing(left + width * 0.33, y_of(0.0)))
            else:
                attrs = f'data-season="{season}" data-year="{year}"'
                body.append(_bar(attrs, left + width * 0.12, width * 0.42, r["anom_history"], y_of))
            if year in estimates[season]:
                body.append(_estimate_mark(season, year, estimates[season][year], left + width * 0.72, y_of))
        body += _year_labels(years, top + plot_h)
        body.append("</g>")
        history = {yr: rows[season][yr]["anom_history"] for yr in rows[season]}
        text = f"{name}: {_value_list(history)}."
        if estimates[season]:
            text += (
                " Estimates: " + ", ".join(_estimate_text(yr, r) for yr, r in sorted(estimates[season].items())) + "."
            )
        desc.append(f"{text} {note}".strip())
        y = top + plot_h + PANEL_FOOT
    caption = [
        "Source: artifacts/risk_table.json, Nghệ An rows: NSO yields (R-D01), past-only normal (E-010), M1 estimates and"
        " 80% ranges (E-012).",
        f"{method['stability_scope']['en']}.",
    ]
    body += _caption(caption, y)
    desc += caption
    return svg_document("rice-history", title, " ".join(desc), legend, body, y + 16 * len(caption) + 12)


def _estimate_mark(season: str, year: int, r: dict, x: float, y_of: Callable[[float], float]) -> str:
    parts = [f'<g data-season="{season}" data-year="{year}" data-estimate="{r["model_id"]}">']
    ci = _range(r)
    if ci is not None:
        parts.append(
            f'<line x1="{x:.1f}" y1="{y_of(ci[1]):.1f}" x2="{x:.1f}" y2="{y_of(ci[0]):.1f}" stroke="{ESTIMATE}"'
            ' stroke-width="2"/>'
        )
    parts.append(
        f'<circle cx="{x:.1f}" cy="{y_of(r["anom_oos"]):.1f}" r="3.5" fill="{BACKGROUND}" stroke="{ESTIMATE}"'
        ' stroke-width="2"/>'
    )
    parts.append("</g>")
    return "".join(parts)


def _share_rows(hazards: dict, codes: list[str]) -> dict[str, dict[int, dict]]:
    out: dict[str, dict[int, dict]] = {}
    for r in hazards["rows"]:
        if r["level"] != "year":
            continue
        if r["rule"] not in codes:
            raise ValueError(f"hazard_labels.json: rule {r['rule']!r} is not in rules/conditions.yaml")
        if r["year"] in out.get(r["rule"], {}):
            raise ValueError(f"hazard_labels.json: two year rows for {r['rule']} {r['year']}")
        out.setdefault(r["rule"], {})[r["year"]] = r
    return out


def rule_shares_svg(hazards: dict, conditions: list[dict]) -> str:
    """The farmland share meeting each official rule per year (hazard_labels.json `year` rows), one panel per rule of
    rules/conditions.yaml, in its order and with its labels."""
    codes = [c["code"] for c in conditions]
    rows = _share_rows(hazards, codes)
    years = sorted({y for by_year in rows.values() for y in by_year})
    cells = {r["n_cells"] for by_year in rows.values() for r in by_year.values()}
    if len(cells) != 1:
        raise ValueError(f"hazard_labels.json: year rows name different POWER cell counts {sorted(cells)}")
    plot_h = round(100 * SHARE_PX)

    title = f"Share of Nghệ An farmland meeting each official rule, past years {years[0]}-{years[-1]}"
    legend = [
        "Past years, not a forecast. Bar: the share of Nghệ An farmland where the rule's level 1 or higher was met in"
        " that year, with the",
        "thresholds of QĐ 18/2021/QĐ-TTg (R-A01). Daily rules count the field dates of the crops of the Nghệ An field"
        " trial (R-P02);",
        "the drought rules count the calendar months from sowing to harvest, partial months included. n/a: no value.",
        f"Farmland: the {cells.pop()} NASA POWER cells with farmland in Nghệ An, weighted by the NASA MODIS farmland"
        " mask.",
    ]
    body: list[str] = []
    desc = [f"{title}. Past years, not a forecast."]
    y = _body_top(legend)
    for c in conditions:
        name = f"{c['label']['en']} ({c['article']})"
        by_year = rows.get(c["code"], {})
        body.append(f'<g data-rule="{c["code"]}">')
        body.append(svg_text(LABEL_X, y + 18, name, ' font-weight="bold"'))
        top = y + PANEL_HEAD
        ticks, y_of = _axis(top, 0, 100, SHARE_STEP, SHARE_PX)
        body += ticks
        for i, year in enumerate(years):
            left, width = _slot(i, len(years))
            r = by_year.get(year)
            if r is None or r["share_farmland"] is None:
                body.append(_missing(left + width / 2, y_of(0.0)))
            else:
                attrs = f'data-rule="{c["code"]}" data-year="{year}"'
                body.append(_bar(attrs, left + width * 0.15, width * 0.7, r["share_farmland"], y_of))
        body += _year_labels(years, top + plot_h)
        body.append("</g>")
        shares = {yr: by_year[yr]["share_farmland"] if yr in by_year else None for yr in years}
        desc.append(f"{name}: {_value_list(shares)}.")
        y = top + plot_h + PANEL_FOOT
    caption = [
        "Source: artifacts/hazard_labels.json, year rows (E-019): NASA POWER daily values (R-N01), NASA MODIS MCD12C1"
        " farmland mask (R-N02),",
        "thresholds of QĐ 18/2021/QĐ-TTg (R-A01). Our computation, not an official record; gridded values smooth"
        " extremes.",
    ]
    body += _caption(caption, y)
    desc += caption
    return svg_document("rule-shares", title, " ".join(desc), legend, body, y + 16 * len(caption) + 12)
