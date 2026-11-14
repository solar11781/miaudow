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


# ---- Phase 2: data layer views, climate ML, data quality (added at the end; every model above is unchanged) ----

PlaceKind = Literal["province", "district", "grid_cell", "farmland_weighted_area", "study_point", "pixel_block"]
Availability = Literal["available", "unavailable"]
QualityStatus = Literal["pass", "warn", "fail"]
QualityCategory = Literal[
    "integrity", "crs_bounds", "time", "units_ranges", "missing", "resolution", "licence", "version"
]
LayerKind = Literal["visual", "data"]
CapabilityStatus = Literal["working", "deterministic", "blocked"]


class Place(Strict):
    """The geography a value describes. Unlike Geometry it can name a district (Đô Lương) and a pixel block."""

    place_id: str
    kind: PlaceKind
    name: Text
    lat: float | None = None
    lon: float | None = None
    bbox: list[float] | None = None  # [west, south, east, north], EPSG:4326 degrees
    cell_ids: list[str] | None = None


class Provenance(Strict):
    """Where an array of values came from (one record per series instead of one MetricRecord per value)."""

    dataset_id: str
    source_id: str
    source_url: str | None
    source_revision: str | None = None
    method_id: str
    transformation_id: str
    spatial_resolution: str
    validation_status: ValidationStatus
    missing_policy: str
    is_forecast: bool = False
    is_field_measurement: bool = False
    limitations: list[Text] = Field(default_factory=list)


class Series(Strict):
    """One quantity over periods (the months of one year, or years). A null stays null; nothing is filled."""

    quantity: str
    title: Text
    unit: str
    periods: list[str]
    values: list[float | None]
    place: Place
    time_window: TimeWindow
    provenance: Provenance


class Unavailable(Strict):
    """An honest empty state: what is missing, why, and the command that would produce it (if any)."""

    what: str
    reason: Text
    how_to_fix: str | None = None


class ClimateHistory(Strict):
    place: Place
    time_window: TimeWindow
    years: list[int]
    series: list[Series]
    unavailable: list[Unavailable]
    notes: list[Text]


class AnomalyArea(Strict):
    place: Place
    series: list[Series]  # NASA POWER and CHIRPS side by side, each with its own source; never merged
    unavailable: list[Unavailable]


class ClimateAnomalies(Strict):
    year: int
    time_window: TimeWindow
    baseline: TimeWindow
    areas: list[AnomalyArea]
    notes: list[Text]


# ---- Climate ML (AI core 01)


class MethodEvaluation(Strict):
    """How a method did on its proxy task, against simple baselines; the verdict is stated even when it is a loss."""

    task: Text
    n_cases: int
    scores: dict[str, float | None]
    beats_baselines: bool
    verdict: Text
    source_file: str | None


class FeatureDriver(Strict):
    feature: str
    label: Text
    unit: str
    target_value: float | None
    other_value: float | None
    z_difference: float
    share_of_distance: float  # share of the squared distance, 0-1


class AnalogYear(Strict):
    year: int
    order: int  # 1 = most similar; similarity of past weather, not a ranking of plans or a forecast
    distance: float
    distance_unit: str
    annual_rain_anomaly_pct: float | None
    drivers: list[FeatureDriver]


class AnalogResult(Strict):
    target_year: int
    k: int
    analogs: list[AnalogYear]
    excluded_years: list[int]
    median_pairwise_distance: float  # what two unrelated years typically show, for context
    features: list[str]
    place: Place
    time_window: TimeWindow
    baseline: TimeWindow
    provenance: Provenance
    evaluation: MethodEvaluation
    limitations: list[Text]


class MonthDriver(Strict):
    month: int
    robust_z: float
    rain_mm: float
    baseline_median_mm: float
    direction: Literal["wetter", "drier"]


class AnomalyYear(Strict):
    year: int
    in_baseline: bool
    score: float | None
    flagged: bool
    driving_months: list[MonthDriver]
    annual_rain_mm: float | None
    annual_rain_anomaly_pct: float | None
    percentile_flag: Literal["below_p10", "above_p90"] | None


class AnomalyYearsResult(Strict):
    place: Place
    time_window: TimeWindow
    baseline: TimeWindow
    score_unit: str
    threshold: float
    threshold_rule: Text
    percentile_bounds_mm: list[float]  # [p10, p90] of the 1991-2020 annual totals
    years: list[AnomalyYear]
    agreement: dict[str, float | int | list[int]]
    provenance: Provenance
    evaluation: MethodEvaluation
    limitations: list[Text]


# ---- Data quality, coverage, places, layers, documents, capabilities


class QualityCheck(Strict):
    check_id: str
    category: QualityCategory
    dataset_id: str | None
    status: QualityStatus
    detail: Text
    evidence: dict


class QualityReport(Strict):
    generated_at: str
    script: str
    counts: dict[str, int]
    checks: list[QualityCheck]


class DatasetCoverage(Strict):
    dataset_id: str
    title: Text
    ingestion_status: IngestionStatus
    time_span: TimeWindow | None
    temporal_resolution: str
    footprint: Place | None
    spatial_resolution: str
    counts: dict[str, int]
    missing: dict[str, int]
    read_from: list[str]
    notes: list[Text]


class Region(Strict):
    region_id: str
    kind: PlaceKind
    name: Text
    status: Availability
    geometry: dict | None  # GeoJSON geometry, EPSG:4326 lon/lat (RFC 7946)
    bbox: list[float] | None
    weight: float | None
    source: str
    source_url: str | None
    licence: str
    validation_status: ValidationStatus
    notes: list[Text]


class LegendStop(Strict):
    value: float
    colour: str
    label: Text


class MapLayer(Strict):
    """A map layer. kind="visual" is imagery to look at (never evidence); kind="data" carries values with a source."""

    layer_id: str
    title: Text
    kind: LayerKind
    group: Literal["gibs", "sentinel2_ndvi", "power_grid", "boundary"]
    provider: str
    licence: str
    attribution: str | None
    source_url: str | None
    url_template: str | None
    image_url: str | None
    bounds: list[float] | None
    crs: str
    time: dict | None
    unit: str | None
    legend: list[LegendStop]
    validation_status: ValidationStatus
    use: Text
    limitations: list[Text]


class ResearchDocument(Strict):
    doc_id: str
    source_id: str
    title: Text
    kind: str
    status: Literal["full_text", "quotes_only", "recorded_only", "generated"]
    licence_basis: str
    chunk_count: int
    passage_count: int
    url: str | None
    retrieved_at: str | None
    notes: list[Text]


class Credential(Strict):
    env_var: str
    present: bool  # presence only; the value is never read into a response
    purpose: Text


class AiCapability(Strict):
    core_id: str
    title: Text
    status: CapabilityStatus
    module: str
    can: list[Text]
    cannot: list[Text]
    credentials: list[Credential]


class ModelEvaluation(Strict):
    evaluation_id: str
    core: str
    title: Text
    status: Availability
    source_file: str
    summary: dict
    verdict: Text | None
    limitations: list[Text]


# ---- Satellite vegetation (Sentinel-2 over Đô Lương, MODIS at the study site)


class SatelliteScene(Strict):
    scene_id: str
    date: date
    season: str
    season_year: int
    cloud_cover_tile_pct: float | None
    cloud_fraction_district: float | None
    valid_fraction: float | None
    ndvi_median: float | None
    ndvi_p25: float | None
    ndvi_p75: float | None
    evi_median: float | None
    ndmi_median: float | None


class SatelliteScenes(Strict):
    status: Availability
    reason: Text | None
    place: Place | None
    time_window: TimeWindow | None
    units: dict[str, str]
    scenes: list[SatelliteScene]
    counts: dict[str, int]
    provenance: Provenance | None
    attribution: str | None
    limitations: list[Text]


class NdviComposite(Strict):
    composite_id: str
    season: str
    season_label: Text
    year: int
    time_window: TimeWindow
    n_scenes: int
    scene_dates: list[date]
    ndvi_median: float
    ndvi_p25: float
    ndvi_p75: float
    unit: str
    coverage_fraction: float
    n_pixels_with_value: int
    image_url: str
    bounds: list[float]


class SatelliteVegetation(Strict):
    sentinel2_status: Availability
    sentinel2_place: Place | None
    composites: list[NdviComposite]
    sentinel2_provenance: Provenance | None
    modis_status: Availability
    modis: list[Series]
    comparability: list[Text]
    unavailable: list[Unavailable]
    limitations: list[Text]


class QualityResponse(Strict):
    status: Availability
    report: QualityReport | None
    unavailable: Unavailable | None
