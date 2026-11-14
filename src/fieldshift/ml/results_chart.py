"""The results chart for the method page and the slides (UI-UX-SPEC section 11b "Results chart", D-145 B; item 49).

Plain words: for each rice season, one row per model; for each of the three references one dot at the model's skill
against that reference and a line across its 90% year-bootstrap interval, with a dashed line at skill 0 (no better than
that reference). Only numbers that are already in artifacts/metrics.json are drawn and printed (no new claims).
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from fieldshift.ml.primary_test import REFERENCES

# English labels: the slides and the method page are English (item 30)
SEASON_LABELS = {"spring": "Spring rice", "winter": "Winter rice"}  # UI-UX-SPEC section 11 SeasonCode, modelled seasons
MODEL_LABELS = {"m1_ridge": "M1 ridge", "m2_lgbm": "M2 LightGBM", "m3_rf": "M3 random forest"}  # 03-ML-SPEC section 6
REFERENCE_LABELS = {  # 03-ML-SPEC section 6: B0 each series' own mean, B2 previous-year anomaly, BNW no-weather model
    "b0": "vs B0 (series mean)",
    "b2": "vs B2 (last year)",
    "bnw": "vs BNW (no weather)",
}
TITLE = "Skill of each model against the three references"
LEGEND = "Dot: skill score. Line: 90% year-bootstrap interval. Dashed line: skill 0, no better than that reference."
CAPTION = "Source: artifacts/metrics.json (E-012, E-013, E-017); 90% year-bootstrap intervals"

# colours on white: text 17.4:1, marks 8.7:1, zero line 7.0:1 (WCAG 2.1 contrast; text needs 4.5:1, UI-UX-SPEC H8)
BACKGROUND = "#ffffff"
TEXT = "#1a1a1a"
MARK = "#1f4e79"
ZERO = "#595959"
# a white outline behind each number label, so the zero and interval lines never cut through it
HALO = f' paint-order="stroke" stroke="{BACKGROUND}" stroke-width="4" stroke-linejoin="round"'

# layout in px (routine choice, D-102)
WIDTH = 960
LABEL_X = 16
COLUMN_X = 184
COLUMN_W = 256
PAD = 12
LABEL_HALF_W = 64  # about half a "-0.52 [-1.98, -0.05]" label at 12 px, so a label stays inside its column
ROW_H = 44
TOP = 76


def _fmt(x: float) -> str:
    """2 decimals (D-160); minus zero prints as 0.00, like the engine (coordinator decision 2026-11-14)."""
    text = f"{x:.2f}"
    return "0.00" if text == "-0.00" else text


def _main_model_rows(doc: dict) -> dict[str, dict[str, dict]]:
    """season -> model_id -> metric row, for the main runs of the models (not the references)."""
    out: dict[str, dict[str, dict]] = {}
    for r in doc["metrics"]:
        main = r["sensitivity"] is None and r["scheme"] == "rolling_origin" and r["subset"] == "national"
        if not main or r["model_id"] in REFERENCES:
            continue
        if r["season"] not in SEASON_LABELS or r["model_id"] not in MODEL_LABELS:
            raise ValueError(f"metrics row with no chart label: season {r['season']!r}, model {r['model_id']!r}")
        if r["model_id"] in out.get(r["season"], {}):
            raise ValueError(f"two main-run rows for {r['model_id']} {r['season']} in the metrics document")
        out.setdefault(r["season"], {})[r["model_id"]] = r
    return out


def _drawn(row: dict, ref: str) -> dict | None:
    """The skill against one reference, or None when it or its value is null (left out, never drawn as zero)."""
    skill = row[f"skill_vs_{ref}"]
    return skill if skill and skill["value"] is not None else None


def _interval(skill: dict) -> tuple[float, float] | None:
    low, high = skill["ci90_low"], skill["ci90_high"]
    return None if low is None or high is None else (low, high)


def _label(skill: dict) -> str:
    ci = _interval(skill)
    value = _fmt(skill["value"])
    return value if ci is None else f"{value} [{_fmt(ci[0])}, {_fmt(ci[1])}]"


def svg_text(x: float, y: float, content: str, extra: str = "") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}"{extra}>{escape(content)}</text>'


def _x(column: int, v: float, scale: tuple[float, float]) -> float:
    low, span = scale
    return COLUMN_X + column * COLUMN_W + PAD + (v - low) / span * (COLUMN_W - 2 * PAD)


def _scale(rows: dict[str, dict[str, dict]]) -> tuple[float, float]:
    """(lowest end, span) over 0 and every drawn value and interval end; one shared axis for all columns."""
    ends = [0.0]
    for by_model in rows.values():
        for row in by_model.values():
            for ref in REFERENCE_LABELS:
                skill = _drawn(row, ref)
                if skill:
                    ends += [skill["value"], *(_interval(skill) or ())]
    return min(ends), (max(ends) - min(ends)) or 1.0  # one mark at 0 alone: any span draws it


def _mark(key: tuple[str, str, str], skill: dict, column: int, y: float, scale: tuple[float, float]) -> str:
    """One dot, its interval line (when the interval exists) and its printed numbers, as one tagged group."""
    season, model_id, ref = key
    parts = [f'<g data-season="{season}" data-model="{model_id}" data-reference="{ref}">']
    ci = _interval(skill)
    if ci is not None:
        parts.append(
            f'<line x1="{_x(column, ci[0], scale):.1f}" y1="{y + 14:.1f}" x2="{_x(column, ci[1], scale):.1f}"'
            f' y2="{y + 14:.1f}" stroke="{MARK}" stroke-width="2"/>'
        )
    cx = _x(column, skill["value"], scale)
    parts.append(f'<circle cx="{cx:.1f}" cy="{y + 14:.1f}" r="4.5" fill="{MARK}"/>')
    left = COLUMN_X + column * COLUMN_W + LABEL_HALF_W
    label_x = min(max(cx, left), left + COLUMN_W - 2 * LABEL_HALF_W)
    parts.append(svg_text(label_x, y + 34, _label(skill), f' font-size="12" text-anchor="middle"{HALO}'))
    parts.append("</g>")
    return "".join(parts)


def _season(season: str, by_model: dict[str, dict], y: float, scale: tuple[float, float]) -> tuple[list[str], str]:
    """(svg elements, text alternative) of one season block starting at height y."""
    models = [m for m in MODEL_LABELS if m in by_model]
    out = [svg_text(LABEL_X, y + 18, SEASON_LABELS[season], ' font-size="16" font-weight="bold"')]
    bottom = y + 52 + len(models) * ROW_H
    for column, ref_label in enumerate(REFERENCE_LABELS.values()):
        centre = COLUMN_X + column * COLUMN_W + COLUMN_W / 2
        out.append(svg_text(centre, y + 42, ref_label, ' text-anchor="middle" font-weight="bold"'))
        zero = _x(column, 0.0, scale)
        out.append(
            f'<line x1="{zero:.1f}" y1="{y + 50:.1f}" x2="{zero:.1f}" y2="{bottom:.1f}" stroke="{ZERO}"'
            ' stroke-dasharray="4 3"/>'
        )
    desc = [f"{SEASON_LABELS[season]}:"]
    for i, model_id in enumerate(models):
        row_y = y + 52 + i * ROW_H
        out.append(svg_text(LABEL_X, row_y + 18, MODEL_LABELS[model_id]))
        for column, ref in enumerate(REFERENCE_LABELS):
            skill = _drawn(by_model[model_id], ref)
            if skill:
                out.append(_mark((season, model_id, ref), skill, column, row_y, scale))
                desc.append(f"{MODEL_LABELS[model_id]} {REFERENCE_LABELS[ref]} {_label(skill)};")
    return out, " ".join(desc)


def results_chart_svg(doc: dict) -> str:
    """The results chart as standalone SVG text, from a metrics document (05-DATA-CONTRACTS 5b, artifacts/metrics.json)."""
    rows = _main_model_rows(doc)
    scale = _scale(rows)
    body: list[str] = []
    desc = [f"{TITLE}, with 90% year-bootstrap intervals."]
    y = TOP
    for season in (s for s in SEASON_LABELS if s in rows):
        elements, text = _season(season, rows[season], y, scale)
        body += elements
        desc.append(text)
        y += 52 + len(rows[season]) * ROW_H + 16
    body.append(svg_text(LABEL_X, y + 12, CAPTION, ' font-size="12"'))
    return svg_document("results-chart", TITLE, " ".join(desc), [LEGEND], body, y + 24)


def svg_document(key: str, title: str, desc: str, legend: list[str], body: list[str], height: float) -> str:
    """A standalone SVG image: role="img" named by its <title> and <desc>, white background, title and legend lines."""
    lines = [svg_text(LABEL_X, 52 + 16 * i, line, ' font-size="12"') for i, line in enumerate(legend)]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}"'
            f' role="img" aria-labelledby="{key}-title {key}-desc" font-family="sans-serif"'
            f' font-size="14" fill="{TEXT}">',
            f'<title id="{key}-title">{escape(title)}</title>',
            f'<desc id="{key}-desc">{escape(desc)}</desc>',
            f'<rect width="{WIDTH}" height="{height}" fill="{BACKGROUND}"/>',
            svg_text(LABEL_X, 28, title, ' font-size="18" font-weight="bold"'),
            *lines,
            *body,
            "</svg>",
            "",
        ]
    )
