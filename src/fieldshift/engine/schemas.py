"""Pydantic schemas mirroring the API contract of UI-UX-SPEC §11 one to one (04-TECH-DESIGN §3).

TypeScript `T | null` is Python `T | None`. Inline object types of the contract get a model name here (routine
choice). The validators are the response checks of UI-UX-SPEC §11 ("Validation in src/api.ts"), so the engine can never
return a response the frontend rejects.
"""

from __future__ import annotations

from datetime import datetime
from itertools import pairwise
from typing import Annotated, Literal, Self, TypedDict, get_args

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictInt, model_validator, with_config

Province = Literal["nghe_an"]
Land = Literal["dry", "unsure"]
Priority = Literal["income", "stability", "water", "land"]
PlanId = Literal["usual", "usual_p03", "cc1", "cc2", "cc3", "cc4"]
SeasonCode = Literal["spring", "summer_autumn", "winter", "autumn_winter"]
RuleCode = Literal["heavy_rain", "heat", "drought_rain_consecutive", "drought_rain_any2", "cold"]
ModelStatus = Literal["shown", "not_shown", "not_modeled"]
ModelId = Literal["b0", "b2", "bnw", "m1_ridge", "m2_lgbm", "m3_rf"]
Sensitivity = Literal["no_fao_flagged", "mae_skill", "risk_level_features", "window", "centroid_points"]
CoverageAxis = Literal["money", "conditions", "rice_history", "model", "water_tcvn", "water_fao"]
ExplainKey = Literal["evapotranspiration", "soil_moisture", "ndvi", "frost", "water_balance", "data_types"]
SourceId = str

SUMMARY_MIN_YEARS = 2  # min / median / max needs 2 real values (D-95; 03-ML-SPEC §5b)
FIRST_YEAR, LAST_YEAR = 1995, 2024  # past years offered (UI-UX-SPEC §11 YearRow; 04-TECH-DESIGN §3: else HTTP 422)
REFERENCE_YEAR = 2001  # any non-leap year: "MM-DD" days are counted in a 365-day year (D-103, D-104)
ID_LISTS = ("source_ids", "values_source_ids", "principle_source_ids")  # the id fields of §11
ID_SINGLES = ("threshold_source_id", "computed_by")


def _real_day(mmdd: str) -> str:
    datetime.strptime(f"{REFERENCE_YEAR}-{mmdd}", "%Y-%m-%d")  # raises ValueError for a day that does not exist
    return mmdd


MonthDay = Annotated[str, Field(pattern=r"^\d{2}-\d{2}$"), AfterValidator(_real_day)]  # "MM-DD" (§11)

RULE_CODES: tuple[RuleCode, ...] = get_args(RuleCode)
PLAN_IDS: tuple[PlanId, ...] = get_args(PlanId)
SEASON_CODES: tuple[SeasonCode, ...] = get_args(SeasonCode)
EXPLAIN_KEYS: tuple[ExplainKey, ...] = get_args(ExplainKey)


@with_config(ConfigDict(extra="forbid"))
class Text(TypedDict):
    """Record<Lang, string>: data-dependent text, always both languages (H15)."""

    vi: str
    en: str


class Contract(BaseModel):
    """Base of every contract model: unknown fields are an error (no score or extra field slips out, H3); output uses
    the contract names (Period `from`) however it is dumped."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)


class SourceFacts(Contract):
    id: SourceId
    citation: Text
    study_type: Text
    place_years: Text
    read_status: str | None
    full_text_read: bool | None
    limitations: list[Text]
    url: str | None
    nso_credit: bool


class Value(Contract):
    value: str
    unit: Text
    source_ids: list[SourceId] = Field(min_length=1)


@with_config(ConfigDict(extra="forbid"))
class RuleShares(TypedDict):
    """Record<RuleCode, Value | null>: all five codes present."""

    heavy_rain: Value | None
    heat: Value | None
    drought_rain_consecutive: Value | None
    drought_rain_any2: Value | None
    cold: Value | None


class Season(Contract):
    code: SeasonCode
    label: Text
    window: Text
    source_ids: list[SourceId]


class Rule(Contract):
    code: RuleCode
    label: Text
    rule_text: Text
    threshold_source_id: SourceId
    values_source_ids: list[SourceId]
    computed_by: SourceId


class YearRow(Contract):
    year: int
    shares: RuleShares


class PastYearsResponse(Contract):
    province: Province
    rules: list[Rule]
    years: list[YearRow] = Field(min_length=1)
    sources: dict[SourceId, SourceFacts]
    n_cells: int

    @model_validator(mode="after")
    def _rules_in_order_years_ascending(self) -> Self:
        codes = tuple(rule.code for rule in self.rules)
        if codes != RULE_CODES:
            raise ValueError(f"rules must be {RULE_CODES} in this order, got {codes}")
        if any(a.year >= b.year for a, b in pairwise(self.years)):
            raise ValueError("years must be strictly ascending")
        _check_sources(self)
        return self


class CropSpan(Contract):
    crop_key: str
    crop_id: str
    crop: Text
    variety: Text | None
    season: SeasonCode
    sow_from: MonthDay | None
    sow_to: MonthDay | None
    harvest_from: MonthDay | None
    harvest_to: MonthDay | None
    source_ids: list[SourceId]

    @model_validator(mode="after")
    def _all_or_no_dates_in_order(self) -> Self:
        dates = [self.sow_from, self.sow_to, self.harvest_from, self.harvest_to]
        if all(d is None for d in dates):
            return self
        if any(d is None for d in dates) or dates != sorted(dates):
            raise ValueError(f"{self.crop_key}: dates must be all set or all null, in order inside one year: {dates}")
        return self


class Period(Contract):
    from_: MonthDay = Field(alias="from")
    to: MonthDay


class MoneyItem(Contract):
    crop_key: str
    crop: Text
    season: SeasonCode
    profit: Value
    cost: Value | None
    yield_: Value = Field(alias="yield")  # the study's yield per crop (UI-UX-SPEC §12d, D-163)
    price: Value
    flag: Text | None


class SeasonValue(Contract):
    season: SeasonCode
    value: Value | None  # null where the study gives no number for the season (P-03 fallow)
    page: str
    words: Text


class Money(Contract):
    items: list[MoneyItem]
    total: Value | None
    price_year: str | None
    definition: Text
    season_values: list[SeasonValue]  # P-03 per season, never summed (D-191)


class SoilWetness(Contract):
    value: Value | None
    normal: Value | None


class ExposureYear(Contract):
    year: int
    shares: RuleShares
    soil_wetness: SoilWetness


class CropExposure(Contract):
    crop_key: str
    crop: Text
    per_year: list[ExposureYear]


class Range80(Contract):
    low: Value
    high: Value


class StabilityYear(Contract):
    year: int
    real: Value | None
    oos_prediction: Value | None
    range_80: Range80 | None

    @model_validator(mode="after")
    def _range_only_with_prediction(self) -> Self:
        if self.range_80 is not None and self.oos_prediction is None:
            raise ValueError(f"{self.year}: range_80 without oos_prediction")
        return self


class Summary(Contract):
    min: Value
    median: Value
    max: Value


class Stability(Contract):
    crop_key: str
    season: SeasonCode
    label: Text
    model_status: ModelStatus
    years_count: int
    scope: Text
    per_year: list[StabilityYear]
    summary: Summary | None
    worst_years: list[int]

    @model_validator(mode="after")
    def _predictions_and_summary(self) -> Self:
        if self.model_status != "shown" and any(row.oos_prediction is not None for row in self.per_year):
            raise ValueError(f"{self.crop_key}: oos_prediction only if model_status is shown")
        real = [(row.year, row.real.value) for row in self.per_year if row.real is not None]
        if self.years_count != len(real):
            raise ValueError(f"{self.crop_key}: years_count {self.years_count} but {len(real)} real values")
        if (self.summary is None) != (len(real) < SUMMARY_MIN_YEARS):
            raise ValueError(
                f"{self.crop_key}: summary must be null exactly when fewer than {SUMMARY_MIN_YEARS} real values"
            )
        worst = [] if self.summary is None else [y for y, v in real if v == self.summary.min.value]
        if self.worst_years != sorted(worst):
            raise ValueError(f"{self.crop_key}: worst_years {self.worst_years} must be {sorted(worst)}")
        return self


class WaterFact(Contract):
    crop_key: str
    measure: Literal["to_apply", "crop_uses", "not_listed"]
    value: Value | None
    scope: Text | None
    note: Text | None


class LandCheck(Contract):
    value: Value | None
    principle_source_ids: list[SourceId]


class Legume(Contract):
    present: bool
    crops: list[Text]
    principle_source_ids: list[SourceId]


class LandCare(Contract):
    crops_in_year: LandCheck
    living_days: LandCheck
    legume: Legume


class RiskItem(Contract):
    text: Text
    source_ids: list[SourceId]


class Why(Contract):
    why: Text
    evidence: Text
    benefits: Text
    gaps: Text
    risks: list[RiskItem]


class Plan(Contract):
    id: PlanId
    name: Text
    is_usual: bool
    calendar: list[CropSpan]
    bare_periods: list[Period]
    money: Money
    exposure: list[CropExposure]
    stability: list[Stability] | None
    water: list[WaterFact]
    land: LandCare
    why: Why


def _years_ascending_in_range(years: list[int]) -> list[int]:
    ascending = all(a < b for a, b in pairwise(years))
    if not ascending or any(not FIRST_YEAR <= y <= LAST_YEAR for y in years):
        raise ValueError(f"years must be strictly ascending within {FIRST_YEAR}-{LAST_YEAR}")
    return years


# the picked past years at a trust boundary: whole numbers only, at most the 30 years of 1995-2024 (UI-UX-SPEC §11
# YearRow), never empty (§6b rules 3, 5)
Years = Annotated[
    list[StrictInt],
    Field(min_length=1, max_length=LAST_YEAR - FIRST_YEAR + 1),
    AfterValidator(_years_ascending_in_range),
]


class CompareRequest(Contract):
    province: Province
    land: Land
    years: Years
    priority: Priority


class Interval(Contract):
    value: float
    ci90_low: float
    ci90_high: float


class GateRow(Contract):
    gate: Literal["G1", "G2", "G3", "G4"]
    season: SeasonCode
    model_id: str | None
    passed: bool | None
    detail: Text
    source_ids: list[SourceId]


class YearSpan(Contract):
    first: int
    last: int


class CompareResponse(Contract):
    request: CompareRequest
    test_years: YearSpan
    n_cells: int
    seasons: list[Season]
    rules: list[Rule]
    gates: list[GateRow]
    plans: list[Plan]
    sources: dict[SourceId, SourceFacts]

    @model_validator(mode="after")
    def _plans_years_and_predictions(self) -> Self:
        ids = tuple(plan.id for plan in self.plans)
        if ids != PLAN_IDS:
            raise ValueError(f"plans must be {PLAN_IDS} in this order, got {ids}")
        first, last = self.test_years.first, self.test_years.last
        for plan in self.plans:
            blocks = [*plan.exposure, *(plan.stability or [])]
            if any([r.year for r in b.per_year] != self.request.years for b in blocks):
                raise ValueError(f"{plan.id}: every per_year must list exactly the requested years")
            for block in plan.stability or []:
                for row in block.per_year:
                    predicted = row.oos_prediction is not None or row.range_80 is not None
                    if predicted and not first <= row.year <= last:
                        raise ValueError(f"{block.crop_key} {row.year}: prediction outside test years")
        _check_sources(self)
        return self


class MetricRow(Contract):
    model_id: ModelId
    season: SeasonCode
    role: Literal["primary", "secondary", "reference"]
    scheme: Literal["rolling_origin", "spatial_holdout"]
    sensitivity: Sensitivity | None
    detail: Text | None
    subset: str
    rmse: float | None
    mae: float | None
    r2_oos: float | None
    skill_vs_b0: Interval | None
    skill_vs_b2: Interval | None
    skill_vs_bnw: Interval | None
    coverage_80: float | None
    n_rows: int
    n_test_years: int
    source_ids: list[SourceId]


class WeatherClaim(Contract):
    season: SeasonCode
    model_id: ModelId
    made: bool
    source_ids: list[SourceId]


class ReportItem(Contract):
    id: SourceId
    title: Text
    text: Text
    source_ids: list[SourceId]


class CoverageCell(Contract):
    row_key: str
    crop: Text
    axis: CoverageAxis
    text: Text
    source_ids: list[SourceId]


class ExplainTerm(Contract):
    key: ExplainKey
    title: Text
    text: Text
    source_ids: list[SourceId]


class NotUsedDataset(Contract):
    """A dataset considered and not used (UI-UX-SPEC §11b item 4b; D-165): its official facts and the reason."""

    dataset: str
    reason: Text
    source_ids: list[SourceId] = Field(min_length=1)


class RainMonth(Contract):
    month: str
    imerg: Value
    power: Value


class RainCheck(Contract):
    months: list[RainMonth]
    cc: Value
    mean_imerg: Value
    mean_power: Value
    source_ids: list[SourceId]


class MethodResponse(Contract):
    test_years: YearSpan
    freeze_commit: str
    metrics: list[MetricRow]
    gates: list[GateRow]
    weather_claims: list[WeatherClaim]
    reports: list[ReportItem]
    coverage: list[CoverageCell]
    explain_terms: list[ExplainTerm]
    limitations: list[Text]
    datasets_not_used: list[NotUsedDataset]
    rain_check: RainCheck | None
    sources: dict[SourceId, SourceFacts]

    @model_validator(mode="after")
    def _coverage_once_terms_in_order(self) -> Self:
        cells = [(c.row_key, c.axis) for c in self.coverage]
        if len(cells) != len(set(cells)):
            raise ValueError("each (row_key, axis) of coverage must occur once")
        keys = tuple(t.key for t in self.explain_terms)
        if keys != EXPLAIN_KEYS:
            raise ValueError(f"explain_terms must be {EXPLAIN_KEYS} in this order, got {keys}")
        _check_sources(self)
        return self


class ArtifactInfo(Contract):
    schema_version: str
    generated_at: str


class HealthResponse(Contract):
    status: Literal["ok"]
    artifacts: dict[str, ArtifactInfo]


def source_ids_in(node: object) -> list[SourceId]:
    """Every source id that the id fields of §11 hold inside a dumped model, in reading order."""
    if isinstance(node, list):
        return [sid for item in node for sid in source_ids_in(item)]
    if not isinstance(node, dict):
        return []
    found: list[SourceId] = []
    for key, child in node.items():
        if key in ID_LISTS:
            found += child
        elif key in ID_SINGLES:
            found.append(child)
        elif key != "sources":
            found += source_ids_in(child)
    return found


def _check_sources(response: PastYearsResponse | CompareResponse | MethodResponse) -> None:
    """§11 validation: every id used is a key of the response's `sources`, whose facts carry that id (H5)."""
    missing = sorted(set(source_ids_in(response.model_dump())) - response.sources.keys())
    if missing:
        raise ValueError(f"source ids not in sources: {missing}")
    wrong = [key for key, facts in response.sources.items() if facts.id != key]
    if wrong:
        raise ValueError(f"sources listed under another id: {wrong}")
