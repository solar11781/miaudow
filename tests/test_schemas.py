"""Tests for the engine schemas (written before the code). They mirror the API contract of UI-UX-SPEC §11 one to one
(04-TECH-DESIGN §3; .claude/rules/python.md); the invariants are the §11 validation rules, so the engine can never
return what the frontend rejects. Field lists below are copied from UI-UX-SPEC §11. Placeholder values only.
"""

import pytest
from pydantic import ValidationError

from fieldshift.engine import schemas as s

# UI-UX-SPEC §11, field names in contract order
CONTRACT_FIELDS = {
    "SourceFacts": [
        "id",
        "citation",
        "study_type",
        "place_years",
        "read_status",
        "full_text_read",
        "limitations",
        "url",
        "nso_credit",
    ],
    "Value": ["value", "unit", "source_ids"],
    "Season": ["code", "label", "window", "source_ids"],
    "Rule": ["code", "label", "rule_text", "threshold_source_id", "values_source_ids", "computed_by"],
    "YearRow": ["year", "shares"],
    "PastYearsResponse": ["province", "rules", "years", "sources", "n_cells"],
    "CropSpan": [
        "crop_key",
        "crop_id",
        "crop",
        "variety",
        "season",
        "sow_from",
        "sow_to",
        "harvest_from",
        "harvest_to",
        "source_ids",
    ],
    "Period": ["from", "to"],
    "MoneyItem": ["crop_key", "crop", "season", "profit", "cost", "flag"],
    "Money": ["items", "total", "price_year", "definition", "text_only"],
    "CropExposure": ["crop_key", "crop", "per_year"],
    "StabilityYear": ["year", "real", "oos_prediction", "range_80"],
    "Stability": [
        "crop_key",
        "season",
        "label",
        "model_status",
        "years_count",
        "scope",
        "per_year",
        "summary",
        "worst_years",
    ],
    "WaterFact": ["crop_key", "measure", "value", "scope", "note"],
    "LandCheck": ["value", "principle_source_ids"],
    "LandCare": ["crops_in_year", "living_days", "legume"],
    "RiskItem": ["text", "source_ids"],
    "Why": ["why", "evidence", "benefits", "gaps", "risks"],
    "Plan": [
        "id",
        "name",
        "is_usual",
        "calendar",
        "bare_periods",
        "money",
        "exposure",
        "stability",
        "water",
        "land",
        "why",
    ],
    "CompareRequest": ["province", "land", "years", "priority"],
    "Interval": ["value", "ci90_low", "ci90_high"],
    "GateRow": ["gate", "season", "model_id", "passed", "detail", "source_ids"],
    "CompareResponse": ["request", "test_years", "n_cells", "seasons", "rules", "gates", "plans", "sources"],
    "MetricRow": [
        "model_id",
        "season",
        "role",
        "scheme",
        "sensitivity",
        "detail",
        "subset",
        "rmse",
        "mae",
        "r2_oos",
        "skill_vs_b0",
        "skill_vs_b2",
        "skill_vs_bnw",
        "coverage_80",
        "n_rows",
        "n_test_years",
        "source_ids",
    ],
    "WeatherClaim": ["season", "model_id", "made", "source_ids"],
    "ReportItem": ["id", "title", "text", "source_ids"],
    "CoverageCell": ["row_key", "crop", "axis", "text", "source_ids"],
    "ExplainTerm": ["key", "title", "text", "source_ids"],
    "NotUsedDataset": ["dataset", "reason", "source_ids"],  # D-165 (UI-UX-SPEC §11b item 4b)
    "MethodResponse": [
        "test_years",
        "freeze_commit",
        "metrics",
        "gates",
        "weather_claims",
        "reports",
        "coverage",
        "explain_terms",
        "limitations",
        "datasets_not_used",  # D-165
        "rain_check",
        "sources",
    ],
    "RainCheck": ["months", "cc", "mean_imerg", "mean_power", "source_ids"],
    "HealthResponse": ["status", "artifacts"],
    # inline object types of §11, named here
    "SoilWetness": ["value", "normal"],
    "ExposureYear": ["year", "shares", "soil_wetness"],
    "Range80": ["low", "high"],
    "Summary": ["min", "median", "max"],
    "Legume": ["present", "crops", "principle_source_ids"],
    "YearSpan": ["first", "last"],
    "RainMonth": ["month", "imerg", "power"],
    "ArtifactInfo": ["schema_version", "generated_at"],
}
RULE_CODES = ["heavy_rain", "heat", "drought_rain_consecutive", "drought_rain_any2", "cold"]  # §11 RuleCode order
PLAN_IDS = ["usual", "usual_p03", "cc1", "cc2", "cc3", "cc4"]  # §11 canonical plan order
EXPLAIN_KEYS = ["evapotranspiration", "soil_moisture", "ndvi", "frost", "water_balance", "data_types"]  # §11 order
T = {"vi": "[x]", "en": "[x]"}
PCT = {"vi": "%", "en": "%"}


def val(v: str = "xx") -> dict:
    return {"value": v, "unit": PCT, "source_ids": ["E-019"]}


@pytest.mark.parametrize(("name", "fields"), CONTRACT_FIELDS.items())
def test_every_model_has_exactly_the_contract_fields(name: str, fields: list[str]) -> None:
    model = getattr(s, name)
    assert [f.alias or key for key, f in model.model_fields.items()] == fields


def test_text_needs_both_languages() -> None:
    with pytest.raises(ValidationError):
        s.RiskItem.model_validate({"text": {"vi": "[x]"}, "source_ids": []})


def test_a_value_needs_at_least_one_source() -> None:
    # §11: Value.source_ids ">= 1 id"; H5: numbers without a source must not be shown
    with pytest.raises(ValidationError):
        s.Value.model_validate({"value": "xx", "unit": PCT, "source_ids": []})


def test_unknown_fields_and_enum_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        s.Value.model_validate({**val(), "score": 1})  # H3: no score in the output
    with pytest.raises(ValidationError):
        s.CompareRequest.model_validate(
            {"province": "nghe_an", "land": "irrigated", "years": [2000], "priority": "income"}
        )


def test_period_uses_the_contract_key_from() -> None:
    assert s.Period.model_validate({"from": "11-01", "to": "01-31"}).model_dump(by_alias=True) == {
        "from": "11-01",
        "to": "01-31",
    }


def test_shares_need_all_five_rule_codes() -> None:
    # §11 validation: every `shares` has the five codes
    full = dict.fromkeys(RULE_CODES)
    assert s.YearRow.model_validate({"year": 2000, "shares": full}).shares == full
    with pytest.raises(ValidationError):
        s.YearRow.model_validate({"year": 2000, "shares": dict.fromkeys(RULE_CODES[:4])})


def span(**dates: str | None) -> dict:
    base = {"sow_from": "02-01", "sow_to": "02-01", "harvest_from": "05-01", "harvest_to": "06-01"}
    return {
        "crop_key": "cc1_spring_peanut",
        "crop_id": "peanut",
        "crop": T,
        "variety": None,
        "season": "spring",
        **base,
        **dates,
        "source_ids": ["R-P02"],
    }


def test_crop_span_dates_are_all_set_or_all_null_and_in_order() -> None:
    # §11 CropSpan: all four set, or all four null; sow_from <= sow_to <= harvest_from <= harvest_to
    s.CropSpan.model_validate(span())
    s.CropSpan.model_validate(span(sow_from=None, sow_to=None, harvest_from=None, harvest_to=None))
    with pytest.raises(ValidationError):
        s.CropSpan.model_validate(span(harvest_to=None))
    with pytest.raises(ValidationError):
        s.CropSpan.model_validate(span(harvest_from="01-15"))
    with pytest.raises(ValidationError):
        s.CropSpan.model_validate(span(harvest_to="6-01"))  # not "MM-DD"
    for not_a_day in ("13-01", "04-31", "02-29"):  # no such day in a 365-day year (D-103)
        with pytest.raises(ValidationError):
            s.CropSpan.model_validate(span(harvest_to=not_a_day))
    with pytest.raises(ValidationError):
        s.Period.model_validate({"from": "00-10", "to": "01-31"})


def source(sid: str) -> dict:
    return {
        "id": sid,
        "citation": T,
        "study_type": T,
        "place_years": T,
        "read_status": None,
        "full_text_read": None,
        "limitations": [],
        "url": None,
        "nso_credit": False,
    }


def rule(code: str) -> dict:
    return {
        "code": code,
        "label": T,
        "rule_text": T,
        "threshold_source_id": "R-A01",
        "values_source_ids": ["R-N01", "R-N02"],
        "computed_by": "E-019",
    }


RULE_SOURCES = {sid: source(sid) for sid in ("R-A01", "R-N01", "R-N02", "E-019")}  # the ids rule() uses


def past_years(years: list[int], codes: list[str] = RULE_CODES) -> dict:
    return {
        "province": "nghe_an",
        "rules": [rule(c) for c in codes],
        "years": [{"year": y, "shares": dict.fromkeys(RULE_CODES)} for y in years],
        "sources": RULE_SOURCES,
        "n_cells": 0,
    }


def test_past_years_needs_the_five_rules_in_order_and_ascending_years() -> None:
    # §11 validation: rules has the five codes in order; years non-empty and strictly ascending
    s.PastYearsResponse.model_validate(past_years([1995, 1996]))
    for bad in (
        past_years([]),
        past_years([1996, 1995]),
        past_years([1995, 1995]),
        past_years([1995], RULE_CODES[::-1]),
    ):
        with pytest.raises(ValidationError):
            s.PastYearsResponse.model_validate(bad)


def stability(reals: list[str | None], summary: dict | None, worst: list[int], years_count: int) -> dict:
    return {
        "crop_key": "usual_spring_rice",
        "season": "spring",
        "label": T,
        "model_status": "not_shown",
        "years_count": years_count,
        "scope": T,
        "per_year": [
            {"year": 2000 + i, "real": None if r is None else val(r), "oos_prediction": None, "range_80": None}
            for i, r in enumerate(reals)
        ],
        "summary": summary,
        "worst_years": worst,
    }


def test_summary_only_from_two_real_values_t25() -> None:
    # §11 Stability: summary null when fewer than 2 non-null real values; worst_years [] when summary is null;
    # years_count = picked years with a non-null real value (D-95, T25)
    one = stability(["-1", None], None, [], 1)
    assert s.Stability.model_validate(one).summary is None
    two = stability(["-1", "-2"], {"min": val("-2"), "median": val("-1"), "max": val("-1")}, [2001], 2)
    s.Stability.model_validate(two)
    for bad in (
        stability(["-1", None], {"min": val("-1"), "median": val("-1"), "max": val("-1")}, [2000], 1),
        stability(["-1", "-2"], None, [], 2),
        stability(["-1", None], None, [2000], 1),
        stability(["-1", None], None, [], 2),
    ):
        with pytest.raises(ValidationError):
            s.Stability.model_validate(bad)


def test_worst_years_are_the_years_equal_to_the_minimum() -> None:
    # §11: years whose real value equals summary.min, ties give more than one, ascending
    tie = stability(["-2", "-1", "-2"], {"min": val("-2"), "median": val("-2"), "max": val("-1")}, [2000, 2002], 3)
    s.Stability.model_validate(tie)
    for worst in ([2000], [2002, 2000], [2001]):
        with pytest.raises(ValidationError):
            s.Stability.model_validate({**tie, "worst_years": worst})


def empty_plan(pid: str) -> dict:
    land = {"value": None, "principle_source_ids": []}
    return {
        "id": pid,
        "name": T,
        "is_usual": False,
        "calendar": [],
        "bare_periods": [],
        "money": {"items": [], "total": None, "price_year": None, "definition": T, "text_only": None},
        "exposure": [],
        "stability": None,
        "water": [],
        "land": {
            "crops_in_year": land,
            "living_days": land,
            "legume": {"present": False, "crops": [], "principle_source_ids": []},
        },
        "why": {"why": T, "evidence": T, "benefits": T, "gaps": T, "risks": []},
    }


def compare(plans: list[dict], years: list[int] | None = None) -> dict:
    return {
        "request": {"province": "nghe_an", "land": "dry", "years": years or [2010, 2020], "priority": "income"},
        "test_years": {"first": 2016, "last": 2024},
        "n_cells": 0,
        "seasons": [],
        "rules": [rule(c) for c in RULE_CODES],
        "gates": [],
        "plans": plans,
        "sources": RULE_SOURCES,
    }


def test_compare_holds_the_six_plans_in_canonical_order() -> None:
    # §11 validation: plans holds exactly the six plan ids in canonical order (H3: order is final)
    s.CompareResponse.model_validate(compare([empty_plan(p) for p in PLAN_IDS]))
    for ids in (PLAN_IDS[::-1], PLAN_IDS[:5]):
        with pytest.raises(ValidationError):
            s.CompareResponse.model_validate(compare([empty_plan(p) for p in ids]))


def with_rice_years(rows: list[dict], years: list[int] | None = None) -> dict:
    plans = [empty_plan(p) for p in PLAN_IDS]
    block = stability([None] * len(rows), None, [], 0)
    block["per_year"] = rows
    block["model_status"] = "shown"  # predictions appear only for a shown model
    plans[0]["stability"] = [block]
    return compare(plans, years or [r["year"] for r in rows])


def test_no_prediction_or_range_outside_the_test_years_t23() -> None:
    # §11 validation (T23, D-82): no prediction and no range outside test_years; a range only with a
    # prediction, D-94
    rng = {"low": val("-3"), "high": val("3")}
    inside = {"year": 2016, "real": None, "oos_prediction": val(), "range_80": rng}
    s.CompareResponse.model_validate(with_rice_years([inside]))
    for bad in (
        {"year": 2015, "real": None, "oos_prediction": val(), "range_80": None},
        {"year": 2015, "real": None, "oos_prediction": None, "range_80": rng},
        {"year": 2016, "real": None, "oos_prediction": None, "range_80": rng},
    ):
        with pytest.raises(ValidationError):
            s.CompareResponse.model_validate(with_rice_years([bad]))


def test_every_per_year_lists_exactly_the_requested_years() -> None:
    # §11 validation: every `per_year` lists exactly the requested years
    row = {"year": 2010, "real": None, "oos_prediction": None, "range_80": None}
    s.CompareResponse.model_validate(with_rice_years([row]))
    with pytest.raises(ValidationError):
        s.CompareResponse.model_validate(with_rice_years([row], years=[2010, 2020]))
    plans = [empty_plan(p) for p in PLAN_IDS]
    plans[2]["exposure"] = [{"crop_key": "cc1_spring_peanut", "crop": T, "per_year": []}]
    with pytest.raises(ValidationError):
        s.CompareResponse.model_validate(compare(plans, [2010]))


def method(coverage: list[tuple[str, str]], keys: list[str] = EXPLAIN_KEYS) -> dict:
    return {
        "test_years": {"first": 2016, "last": 2024},
        "freeze_commit": "[hash]",
        "metrics": [],
        "gates": [],
        "weather_claims": [],
        "reports": [],
        "coverage": [{"row_key": r, "crop": T, "axis": a, "text": T, "source_ids": []} for r, a in coverage],
        "explain_terms": [{"key": k, "title": T, "text": T, "source_ids": []} for k in keys],
        "datasets_not_used": [],
        "limitations": [],
        "rain_check": None,
        "sources": {},
    }


def test_method_coverage_cells_are_unique_and_explain_terms_ordered() -> None:
    # §11 validation: each (row_key, axis) of coverage occurs once; explain_terms has the six keys in order
    s.MethodResponse.model_validate(method([("rice", "money"), ("rice", "model")]))
    for bad in (method([("rice", "money"), ("rice", "money")]), method([], EXPLAIN_KEYS[::-1])):
        with pytest.raises(ValidationError):
            s.MethodResponse.model_validate(bad)


def test_a_dataset_not_used_needs_at_least_one_source() -> None:
    # D-165: each dataset considered and not used gives its source; H5: nothing shown without a source
    with pytest.raises(ValidationError):
        s.NotUsedDataset.model_validate({"dataset": "[x]", "reason": T, "source_ids": []})


def test_source_facts_shape_round_trips() -> None:
    assert s.SourceFacts.model_validate(source("R-A01")).model_dump() == source("R-A01")


def test_every_source_id_is_a_key_of_the_responses_sources() -> None:
    # §11 validation: every id in any source_ids, threshold_source_id, values_source_ids or computed_by (and
    # principle_source_ids, LandCheck) is a key of the same response's `sources`
    for field in ("threshold_source_id", "computed_by"):
        bad = past_years([1995])
        bad["rules"][0][field] = "R-X01"
        with pytest.raises(ValidationError, match="R-X01"):
            s.PastYearsResponse.model_validate(bad)
    bad = past_years([1995])
    bad["years"][0]["shares"]["heat"] = val()
    bad["sources"] = {k: v for k, v in RULE_SOURCES.items() if k != "E-019"}
    with pytest.raises(ValidationError, match="E-019"):
        s.PastYearsResponse.model_validate(bad)
    plans = [empty_plan(p) for p in PLAN_IDS]
    plans[2]["land"]["crops_in_year"]["principle_source_ids"] = ["R-E13"]
    with pytest.raises(ValidationError, match="R-E13"):
        s.CompareResponse.model_validate(compare(plans))
    bad_method = method([("rice", "money")])
    bad_method["coverage"][0]["source_ids"] = ["R-P02"]
    with pytest.raises(ValidationError, match="R-P02"):
        s.MethodResponse.model_validate(bad_method)


def test_facts_must_carry_the_id_they_are_listed_under() -> None:
    bad = past_years([1995])
    bad["sources"] = {**RULE_SOURCES, "R-A01": source("R-N01")}
    with pytest.raises(ValidationError, match="R-A01"):
        s.PastYearsResponse.model_validate(bad)


@pytest.mark.parametrize("years", [[1994], [2025], [2001, 2000], [2000, 2000]])
def test_compare_request_years_are_ascending_inside_1995_2024(years: list[int]) -> None:
    # 04-TECH-DESIGN §3, 05-DATA-CONTRACTS §10: years not strictly ascending or outside 1995-2024 are rejected (422)
    with pytest.raises(ValidationError):
        s.CompareRequest.model_validate({"province": "nghe_an", "land": "dry", "years": years, "priority": "income"})


def test_compare_request_accepts_the_range_ends() -> None:
    s.CompareRequest.model_validate({"province": "nghe_an", "land": "dry", "years": [1995, 2024], "priority": "land"})


def test_the_record_types_have_exactly_their_keys() -> None:
    # §11: Text = Record<Lang, string>; shares = Record<RuleCode, Value | null>
    assert list(s.Text.__annotations__) == ["vi", "en"]
    assert list(s.RuleShares.__annotations__) == RULE_CODES


def test_period_serializes_its_from_key_in_json() -> None:
    # §11 Period { from, to }: the JSON key is `from` however the model is dumped
    assert (
        s.Period.model_validate({"from": "11-01", "to": "01-31"}).model_dump_json() == '{"from":"11-01","to":"01-31"}'
    )


@pytest.mark.parametrize("years", ['["2000"]', "[2000.0]"])
def test_compare_request_takes_years_only_as_json_integers(years: str) -> None:
    # 04-TECH-DESIGN §3: invalid input gets HTTP 422; years are whole years 1995-2024, not text or fractions
    body = f'{{"province": "nghe_an", "land": "dry", "years": {years}, "priority": "income"}}'
    with pytest.raises(ValidationError):
        s.CompareRequest.model_validate_json(body)


@pytest.mark.parametrize("status", ["not_shown", "not_modeled"])
def test_no_prediction_unless_the_model_is_shown(status: str) -> None:
    # §11 StabilityYear: oos_prediction "only if model_status is 'shown'" (D-82, D-83)
    block = stability([None], None, [], 0)
    block["model_status"] = status
    block["per_year"][0]["oos_prediction"] = val()
    with pytest.raises(ValidationError):
        s.Stability.model_validate(block)
    s.Stability.model_validate({**block, "model_status": "shown"})


def request(years: list[int]) -> dict:
    return {"province": "nghe_an", "land": "dry", "years": years, "priority": "income"}


def test_compare_request_takes_at_most_the_30_years_of_1995_2024() -> None:
    # UI-UX-SPEC §11 YearRow: years 1995..2024, so a pick holds at most 30 years; the body is a trust boundary
    s.CompareRequest.model_validate(request(list(range(1995, 2025))))
    with pytest.raises(ValidationError) as err:
        s.CompareRequest.model_validate(request(list(range(1995, 2026))))
    assert err.value.errors()[0]["type"] == "too_long"


def test_a_huge_year_list_gives_a_short_error() -> None:
    # security review: an unbounded list made a 16.9 MB error message
    with pytest.raises(ValidationError) as err:
        s.CompareRequest.model_validate(request([2000] * 100_000))
    assert len(str(err.value)) < 2_000


@pytest.mark.parametrize("years", [[2001, 2000], [1994, 2000]])
def test_a_year_rule_error_names_the_rule_not_the_list(years: list[int]) -> None:
    with pytest.raises(ValidationError) as err:
        s.CompareRequest.model_validate(request(years))
    message = err.value.errors()[0]["msg"]
    assert "years must be strictly ascending within 1995-2024" in message
    assert str(years) not in message


def test_compare_request_needs_at_least_one_year() -> None:
    # UI-UX-SPEC §6b rule 3: /phuong-an needs land, years and priority; rule 5 sends missing or dropped years back to
    # /nam, so no compare request is made without years; python.md: invalid API input returns HTTP 422
    with pytest.raises(ValidationError) as err:
        s.CompareRequest.model_validate(request([]))
    assert err.value.errors()[0]["type"] == "too_short"
