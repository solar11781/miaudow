"""GET /api/method content (UI-UX-SPEC §11 MethodResponse, §11b; 05-DATA-CONTRACTS §10).

Test years, freeze commit, metric rows, weather claims and reports from artifacts/metrics.json, gate verdicts from
artifacts/gates.json (§5b), coverage, explain terms, datasets not used (D-165), limitations and the PICSA sentence's sources (D-63) from rules/method.yaml (§7b), source facts from
rules/sources.yaml for every id used. Metric numbers stay numbers: the schema types them `number` and the page formats
them (D-160). `rain_check` comes from artifacts/rain_check.json (§5c) in whole mm and a two-decimal cc; null = not run (D-135).
"""

from __future__ import annotations

from pathlib import Path

from fieldshift.engine.rules import (
    GATES,
    METRICS,
    gates_file,
    load_method_texts,
    load_sources,
    metrics_file,
    pick_sources,
    rain_check_file,
)
from fieldshift.engine.schemas import MethodResponse, RainCheck, RainMonth, Value, source_ids_in
from fieldshift.engine.values import MM, NO_UNIT, half_up


def _rain_check(root: Path) -> RainCheck | None:
    """The satellite rain check of §5c: mm rounded half up to whole mm, cc to two decimals; every value cites the file's
    sources (the check as a whole rests on all of them)."""
    file = rain_check_file(root)
    if file is None:
        return None

    def mm(number: float) -> Value:
        return Value(value=half_up(number, 0), unit=MM, source_ids=file.source_ids)

    return RainCheck(
        months=[RainMonth(month=m.month, imerg=mm(m.imerg_mm), power=mm(m.power_mm)) for m in file.months],
        cc=Value(value=half_up(file.cc, 2), unit=NO_UNIT, source_ids=file.source_ids),
        mean_imerg=mm(file.mean_imerg_mm),
        mean_power=mm(file.mean_power_mm),
        source_ids=file.source_ids,
    )


def method(root: Path) -> MethodResponse:
    metrics = metrics_file(root)
    gates_doc = gates_file(root)
    if gates_doc.freeze_commit != metrics.freeze_commit:
        raise ValueError(
            f"artifacts/{GATES} freeze_commit {gates_doc.freeze_commit} differs from artifacts/{METRICS} "
            f"{metrics.freeze_commit}"
        )
    gates = gates_doc.gates
    texts = load_method_texts(root)
    parts = (
        *metrics.metrics,
        *gates,
        *metrics.weather_claims,
        *metrics.reports,
        *texts.coverage,
        *texts.explain_terms,
        *texts.datasets_not_used,
        texts.picsa,
    )
    rain_check = _rain_check(root)
    used = (*parts, *([rain_check] if rain_check else []))
    return MethodResponse(
        test_years=metrics.test_years,
        freeze_commit=metrics.freeze_commit,
        metrics=metrics.metrics,
        gates=gates,
        weather_claims=metrics.weather_claims,
        reports=metrics.reports,
        coverage=texts.coverage,
        explain_terms=texts.explain_terms,
        limitations=texts.limitations,
        datasets_not_used=texts.datasets_not_used,
        picsa=texts.picsa,
        rain_check=rain_check,
        sources=pick_sources(load_sources(root), source_ids_in([item.model_dump() for item in used])),
    )
