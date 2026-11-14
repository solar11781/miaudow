"""Core 03: plans in study order whatever the input, sourced records, and refusal of invalid input."""

import pytest

from miaudow_api import decision
from miaudow_api.contracts import CompareRequest

ORDER = ["usual", "usual_p03", "cc1", "cc2", "cc3", "cc4"]


@pytest.mark.parametrize("priority", [None, "income", "stability", "water", "soil"])
def test_plans_always_come_in_the_study_order(priority):
    res = decision.compare(CompareRequest(priority=priority, plan_ids=list(reversed(ORDER))))
    assert [p.plan_id for p in res.plans] == ORDER


def test_subset_keeps_the_study_order():
    res = decision.compare(CompareRequest(plan_ids=["cc4", "usual", "cc1"], priority="income"))
    assert [p.plan_id for p in res.plans] == ["usual", "cc1", "cc4"]


@pytest.mark.parametrize(
    "req",
    [
        {"plan_ids": ["cc9"]},
        {"plan_ids": []},
        {"years": [1994]},
        {"years": [2025]},
        {"years": []},
    ],
)
def test_invalid_input_raises(req):
    with pytest.raises(ValueError):
        decision.compare(CompareRequest(**req))


def test_money_records_are_verified_copies_and_the_total_is_derived():
    res = decision.compare(CompareRequest(plan_ids=["cc2"]))
    recs = res.plans[0].records
    profits = [r for r in recs if r.metric_id == "reported_profit"]
    assert [r.value for r in profits] == [21100.0, 16700.0, 15865.0]
    assert all(r.validation_status == "VERIFIED" and "Bảng 13" in r.transformation_id for r in profits)
    total = next(r for r in recs if r.metric_id == "year_profit_total")
    assert total.value == 53665.0
    assert total.validation_status == "DERIVED"
    assert total.method_id == "E-022"
    assert all(r.is_forecast is False for r in recs)


def test_counts_and_living_days():
    res = decision.compare(CompareRequest(plan_ids=["usual", "usual_p03", "cc1"]))
    by = {p.plan_id: {r.metric_id: r for r in p.records} for p in res.plans}
    assert by["cc1"]["legume_count"].value == 2.0  # peanut and mung bean (GRIN-Global Fabaceae)
    assert by["cc1"]["crops_in_year"].value == 3.0
    # 18/1-12/5 (115 days) + 10/6-3/9 (86 days) + 1/9-22/12 (113 days) - 3 overlapping days (1-3/9)
    assert by["cc1"]["living_days"].value == 115 + 86 + 113 - 3
    assert by["usual_p03"]["living_days"].value is None  # P-03 gives no dates
    assert by["usual_p03"]["living_days"].quality_flag == "MISSING"
    assert by["usual_p03"]["crops_in_year"].value == 2.0


def test_hazard_records_for_requested_years_come_from_e019():
    res = decision.compare(CompareRequest(plan_ids=["cc2"], years=[2010, 2020]))
    hz = [r for r in res.plans[0].records if r.metric_id.startswith("hazard_share_")]
    assert len(hz) == 3 * 2 * 5  # crops x years x rules
    assert all(r.method_id == "E-019" and r.validation_status == "DERIVED" for r in hz)


def test_applicability_never_claims_a_match():
    for water in (None, "canal_end", "high_field", "reliable", "water_short"):
        res = decision.compare(CompareRequest(water=water))
        for p in res.plans:
            text = p.applicability.vi
            assert "đất lúa kém hiệu quả" in text
            assert "phù hợp với ruộng" not in text
            assert "giống ruộng thử" in text or "chưa thể so" in text or "không biết" in text


def test_biomass_maize_plans_ask_about_purchase_contracts():
    res = decision.compare(CompareRequest(plan_ids=["cc2", "cc4", "cc3"]))
    asks = {p.plan_id: " ".join(q.vi for q in p.questions_for_officer) for p in res.plans}
    assert "hợp đồng thu mua ngô sinh khối" in asks["cc2"]
    assert "hợp đồng thu mua ngô sinh khối" in asks["cc4"]
    assert "hợp đồng thu mua ngô sinh khối" not in asks["cc3"]


def test_every_risk_line_has_source_location_and_quote():
    for p in decision.compare(CompareRequest()).plans:
        for line in p.risk_lines:
            assert line.source_id and line.location and line.quote


def test_priority_only_adds_notes():
    a = decision.compare(CompareRequest(priority="water"))
    b = decision.compare(CompareRequest())
    assert [p.model_dump() for p in a.plans] == [p.model_dump() for p in b.plans]
    assert any("TCVN" in n.vi for n in a.notes)
    assert a.missing_information
