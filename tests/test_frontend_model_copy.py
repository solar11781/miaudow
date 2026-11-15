"""The frontend's bundled model results equal the pipeline's artifacts (queue item 64, model part).

frontend/data/canonical/model.json is a static copy read by the home, data room, evidence and assistant pages; the
method page reads the artifacts through the API. A re-run of the pipeline that is not copied over fails here.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
METRIC_FIELDS = ("rmse", "mae", "r2_oos", "skill_vs_b0", "skill_vs_b2", "skill_vs_bnw", "coverage_80", "n_rows")


def _load(path: str) -> dict:
    return json.loads((REPO / path).read_text(encoding="utf-8"))


COPY = _load("frontend/data/canonical/model.json")
METRICS = _load("artifacts/metrics.json")
GATES = _load("artifacts/gates.json")
RISK = _load("artifacts/risk_table.json")


def test_same_frozen_run_and_test_years() -> None:
    assert COPY["freeze_commit"] == GATES["freeze_commit"] == METRICS["freeze_commit"] == RISK["freeze_commit"]
    assert COPY["test_years"] == METRICS["test_years"]


def test_same_season_status_gate_verdicts_and_weather_claims() -> None:
    assert COPY["seasons"] == RISK["seasons"]
    verdict = lambda gates: [(g["gate"], g["season"], g["model_id"], g["passed"]) for g in gates]  # noqa: E731
    assert verdict(COPY["gates"]) == verdict(GATES["gates"])
    claim = lambda claims: [(c["season"], c["model_id"], c["made"]) for c in claims]  # noqa: E731
    assert claim(COPY["weather_claims"]) == claim(METRICS["weather_claims"])


def test_every_copied_metric_row_has_the_artifact_values() -> None:
    key = lambda m: (m["model_id"], m["season"], m["role"], m["scheme"], m["sensitivity"], m["subset"])  # noqa: E731
    run = {key(m): m for m in METRICS["metrics"]}
    assert COPY["metrics"]
    for row in COPY["metrics"]:
        assert key(row) in run, key(row)
        for field in METRIC_FIELDS:
            assert row[field] == run[key(row)][field], (key(row), field)


def test_the_province_history_and_out_of_sample_values_are_the_risk_table_rows() -> None:
    rows = {(r["season"], r["year"]): r for r in RISK["rows"] if r["unit_id"] == "Nghe An" and r["crop"] == "rice"}
    for season, series in COPY["history"].items():
        for i, year in enumerate(COPY["years"]):
            row = rows.get((season, year))
            for field, values in series.items():
                assert values[i] == (row[field] if row else None), (season, year, field)
