"""Canonical contracts shared by the four AI cores, the API and the web app (docs/07-ARCHITECTURE-AND-CONTRACTS.md).

Every number the product shows travels as a MetricRecord: the value plus where it came from, how it was computed,
what it covers and what it does not prove. Charts, 3D tooltips and copilot answers read the same records.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ValidationStatus = Literal["VERIFIED", "DERIVED", "ESTIMATED", "ILLUSTRATIVE", "PENDING_VERIFICATION", "UNAVAILABLE"]
QualityFlag = Literal["OK", "INCOMPLETE", "MISSING", "NOT_LOADED", "SUSPECT"]
IngestionStatus = Literal["INGESTED", "PARTIAL", "CONTRACT_ONLY", "BLOCKED"]
GeometryType = Literal["grid_cell", "farmland_weighted_area", "province", "point", "study_site"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Text(Strict):
    """A sentence in both languages; Vietnamese is the primary language."""

    vi: str
    en: str


class TimeWindow(Strict):
    start: date
    end: date
    label: Text | None = None


class Geometry(Strict):
    type: GeometryType
    lat: float | None = None
    lon: float | None = None
    cell_ids: list[str] | None = None
    description: Text


class Uncertainty(Strict):
    kind: Literal["interval", "range", "qualitative", "none_reported"]
    low: float | None = None
    high: float | None = None
    level: float | None = None  # e.g. 0.9 for a 90% interval
    note: Text | None = None


class MetricRecord(Strict):
    """One displayed value with its full provenance (02-DATA-AND-AI-BLUEPRINT, canonical card contract)."""

    metric_id: str
    dataset_id: str
    source_id: str
    source_url: str | None
    source_revision: str | None
    retrieved_at: str | None
    value: float | bool | None
    unit: str
    time_window: TimeWindow
    geometry: Geometry
    spatial_resolution: str
    method_id: str
    transformation_id: str
    quality_flag: QualityFlag
    missing_policy: str
    uncertainty: Uncertainty
    validation_status: ValidationStatus
    is_forecast: bool = False
    is_field_measurement: bool = False
    limitations: list[Text] = Field(default_factory=list)


class Dataset(Strict):
    dataset_id: str
    title: Text
    provider: str
    source_id: str
    source_url: str | None
    license: str
    source_revision: str | None
    retrieved_at: str | None
    temporal_coverage: str
    spatial_resolution: str
    geometry_crs: str | None
    variables: list[str]
    missing_policy: str
    allowed_use: Text
    version_sha256: str | None
    ingestion_status: IngestionStatus
    is_field_measurement: bool
    notes: list[Text] = Field(default_factory=list)


class MethodDef(Strict):
    method_id: str
    title: Text
    description: Text
    source_ids: list[str]


class SourceFact(Strict):
    """A source as the team's rules/sources.yaml describes it; facts about the source only, no grade."""

    id: str
    citation: Text
    study_type: Text | None = None
    place_years: Text | None = None
    read_status: str | None = None
    full_text_read: bool | None = None
    limitations: list[Text] = Field(default_factory=list)
    url: str | None = None


# ---- Evidence (AI core 02) ----

PassageKind = Literal["regulation", "study", "standard", "dataset", "computation", "model", "team_note"]


class Passage(Strict):
    passage_id: str
    doc_id: str
    source_id: str
    kind: PassageKind
    title: Text
    text: Text
    location: str | None  # page, table or article in the source document; None only for our own computations
    validation_status: ValidationStatus
    url: str | None = None


class SearchHit(Strict):
    passage: Passage
    score: float
    coverage: float
    matched_terms: list[str]


class SearchResult(Strict):
    query: str
    hits: list[SearchHit]
    abstained: bool
    reason: str | None = None


# ---- Crop decision support (AI core 03) ----

WaterSituation = Literal["canal_end", "high_field", "reliable", "water_short"]
Priority = Literal["income", "stability", "water", "soil"]


class CompareRequest(Strict):
    water: WaterSituation | None = None
    priority: Priority | None = None
    plan_ids: list[str] | None = None
    years: list[int] | None = None


class RiskLine(Strict):
    text: Text
    source_id: str
    location: str
    quote: str


class SeasonRow(Strict):
    crop_key: str
    crop_id: str
    crop_name: Text
    variety: str | None
    season: str
    sow: str | None
    harvest: str | None


class PlanComparison(Strict):
    plan_id: str
    name: Text
    is_usual: bool
    site: str
    trial_period: str
    seasons: list[SeasonRow]
    records: list[MetricRecord]  # profits, costs, year total, living days, legume count, hazard shares
    risk_lines: list[RiskLine]
    limitations: list[Text]
    applicability: Text
    questions_for_officer: list[Text]


class DecisionResult(Strict):
    request: CompareRequest
    plans: list[PlanComparison]  # always in the study's own order (CC5, P-03, CC1-CC4); never ranked or sorted
    missing_information: list[Text]
    notes: list[Text]


# ---- Copilot (AI core 04) ----

CopilotStatus = Literal["grounded", "reference_only", "insufficient_evidence", "provider_error", "not_configured"]


class CopilotRequest(Strict):
    question: str = Field(min_length=2, max_length=1200)
    mode: Literal["simple", "technical"] = "simple"
    lang: Literal["vi", "en"] = "vi"
    water: WaterSituation | None = None


class Citation(Strict):
    passage_id: str
    source_id: str
    title: Text
    location: str | None
    url: str | None


class AnswerCard(Strict):
    kind: Literal["plan", "year", "metric", "passage"]
    ref_id: str
    title: Text
    records: list[MetricRecord] = Field(default_factory=list)


class ToolCall(Strict):
    tool: str
    input: dict
    ok: bool


class NumberCheck(Strict):
    checked: int
    unverified: list[str]


class CopilotResponse(Strict):
    status: CopilotStatus
    engine: Literal["claude", "deterministic"]
    model: str | None
    answer: str
    citations: list[Citation]
    cards: list[AnswerCard]
    tool_trace: list[ToolCall]
    numbers: NumberCheck
    missing_information: list[Text] = Field(default_factory=list)
