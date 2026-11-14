"""GET /api/method content (UI-UX-SPEC §11 MethodResponse, §11b; 05-DATA-CONTRACTS §10).

Test years, freeze commit, metric rows, weather claims and reports from artifacts/metrics.json, gate verdicts from
artifacts/gates.json (§5b), coverage, explain terms, datasets not used (D-165) and limitations from rules/method.yaml (§7b), source facts from
rules/sources.yaml for every id used. Metric numbers stay numbers: the schema types them `number` and the page formats
them (D-160). `rain_check` is null until the satellite rain check is built (D-135: null = not run).
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
)
from fieldshift.engine.schemas import MethodResponse, source_ids_in


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
    )
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
        rain_check=None,
        sources=pick_sources(load_sources(root), source_ids_in([item.model_dump() for item in parts])),
    )
