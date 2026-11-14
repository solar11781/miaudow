"""Every displayed number has a known source (hard rule H5; UI-UX-SPEC section 11 validation rules).

Written before source_trace.py. Run: pytest tests/test_source_trace.py
"""

import json
from pathlib import Path

import pytest

from source_trace import check_response, known_ids_from

REPO = Path(__file__).resolve().parents[1]


def facts(source_id: str) -> dict:
    return {"id": source_id, "citation": {"vi": "c", "en": "c"}}


def good() -> dict:
    return {
        "rules": [{"threshold_source_id": "R-A01", "values_source_ids": ["R-N01"], "computed_by": "E-011"}],
        "years": [{"value": {"value": "12", "unit": {"vi": "%", "en": "%"}, "source_ids": ["E-011"]}}],
        "sources": {"R-A01": facts("R-A01"), "R-N01": facts("R-N01"), "E-011": facts("E-011")},
    }


def test_a_complete_response_passes() -> None:
    assert check_response(good(), {"R-A01", "R-N01", "E-011"}) == []


def test_a_value_without_a_source_fails() -> None:
    resp = good()
    resp["years"][0]["value"]["source_ids"] = []
    assert any("no source" in p for p in check_response(resp, None))


def test_an_id_missing_from_the_sources_map_fails() -> None:
    resp = good()
    resp["years"][0]["value"]["source_ids"] = ["R-P02"]
    assert any("R-P02" in p for p in check_response(resp, None))


def test_every_id_field_of_the_contract_is_checked() -> None:
    for field, value in [
        ("threshold_source_id", "R-X99"),
        ("values_source_ids", ["R-X99"]),
        ("computed_by", "E-999"),
        ("principle_source_ids", ["R-X99"]),
    ]:
        resp = good()
        resp["rules"][0][field] = value
        assert check_response(resp, None), field


def test_facts_must_carry_their_own_id() -> None:
    resp = good()
    resp["sources"]["R-A01"] = facts("R-N01")
    assert any("R-A01" in p for p in check_response(resp, None))


def test_ids_must_exist_in_the_registers() -> None:
    assert any("R-N01" in p for p in check_response(good(), {"R-A01", "E-011"}))


def test_known_ids_are_read_from_the_registers() -> None:
    refs = "| ID | Citation |\n|---|---|\n| R-N01 | NASA POWER |\n| R-A01 | QD 18 |\ntext R-Z99 in prose\n"
    exps = "| ID | Question |\n|---|---|\n| E-000 | variance |\n| E-000a | detail |\n"
    assert known_ids_from(refs, exps) == {"R-N01", "R-A01", "E-000", "E-000a"}


def test_this_repositorys_fixtures_trace_every_number() -> None:
    files = sorted((REPO / "tests" / "fixtures").glob("*.json")) + sorted(
        (REPO / "frontend" / "public" / "fixtures").glob("*.json")
    )
    if not files:
        pytest.skip("no response fixtures yet")
    registers = [REPO / "docs" / "REFERENCES.md", REPO / "docs" / "EXPERIMENTS.md"]
    known = (
        known_ids_from(*(p.read_text(encoding="utf-8") for p in registers))
        if all(p.exists() for p in registers)
        else None
    )
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "sources" in data:
            assert check_response(data, known) == [], path.name
