"""Read and check the rules files and artifacts the engine serves (04-TECH-DESIGN §2; 05-DATA-CONTRACTS §4-§8).

The engine reads only `rules/*.yaml` and `artifacts/*.json` under the project folder it is given (.claude/rules/python.md).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, Literal, Self, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from fieldshift.engine.schemas import (
    FIRST_YEAR,
    LAST_YEAR,
    PLAN_IDS,
    RULE_CODES,
    CoverageCell,
    ExplainTerm,
    GateRow,
    MetricRow,
    ModelStatus,
    MonthDay,
    PlanId,
    ReportItem,
    RiskItem,
    Rule,
    RuleCode,
    SeasonCode,
    SourceFacts,
    SourceId,
    Text,
    WeatherClaim,
    YearSpan,
)

HAZARD_LABELS = "hazard_labels.json"
SOIL_WETNESS = "soil_wetness.json"
RISK_TABLE = "risk_table.json"
METRICS = "metrics.json"
GATES = "gates.json"
M = TypeVar("M", bound=BaseModel)
CROP_ROW_PLANS = ("usual", "cc1", "cc2", "cc3", "cc4")  # §4b: no usual_p03 (P-03 reports no dates)
CROP_ROW_SEASONS = ("spring", "summer_autumn", "autumn_winter")  # §4b: the P-02 crop seasons
Month = Annotated[int, Field(ge=1, le=12)]


class HazardRow(BaseModel):
    """One row of artifacts/hazard_labels.json (05-DATA-CONTRACTS §4b); an artifact row, not an API type."""

    model_config = ConfigDict(extra="forbid")

    level: Literal["crop", "year"]
    plan_id: str | None
    crop_key: str | None
    season: SeasonCode | None
    months: list[Month]
    field_dates: list[tuple[MonthDay, MonthDay]]
    year: int = Field(ge=FIRST_YEAR, le=LAST_YEAR)
    rule: RuleCode
    share_farmland: float | None = Field(ge=0, le=1)
    n_cells: int = Field(ge=0)
    threshold_source_id: SourceId
    values_source_ids: list[SourceId]
    computed_by: SourceId

    @model_validator(mode="after")
    def _fields_of_its_level(self) -> Self:
        keys = (self.plan_id, self.crop_key, self.season)
        if self.level == "year" and keys != (None, None, None):
            raise ValueError(f"year row {self.year} {self.rule}: plan_id, crop_key and season must be null")
        if self.level == "crop" and (
            self.plan_id not in CROP_ROW_PLANS or self.crop_key is None or self.season not in CROP_ROW_SEASONS
        ):
            raise ValueError(f"crop row {self.crop_key} {self.year}: plan_id, crop_key or season not of a P-02 crop")
        if any(sow > harvest for sow, harvest in self.field_dates):
            raise ValueError(f"row {self.year} {self.rule}: a sowing date after its harvest date {self.field_dates}")
        return self


class SoilRow(BaseModel):
    """One row of artifacts/soil_wetness.json (05-DATA-CONTRACTS §4d)."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    crop_key: str
    season: SeasonCode
    field_dates: list[tuple[MonthDay, MonthDay]]
    year: int = Field(ge=FIRST_YEAR, le=LAST_YEAR)
    value: float | None = Field(ge=0, le=1)
    normal: float | None = Field(ge=0, le=1)
    n_cells: int = Field(ge=0)
    source_ids: list[SourceId]
    computed_by: SourceId


class RiskRow(BaseModel):
    """One row of artifacts/risk_table.json (05-DATA-CONTRACTS §5); anomalies are fractions."""

    model_config = ConfigDict(extra="forbid")

    unit_id: str
    crop: str
    season: SeasonCode
    year: int = Field(ge=FIRST_YEAR, le=LAST_YEAR)
    anom_history: float | None
    anom_history_source_ids: list[SourceId]
    anom_oos: float | None
    oos_low_80: float | None
    oos_high_80: float | None
    model_id: str | None
    anom_oos_source_ids: list[SourceId]


class RiskSeason(BaseModel):
    """One entry of `seasons` in artifacts/risk_table.json (05-DATA-CONTRACTS §5)."""

    model_config = ConfigDict(extra="forbid")

    season: SeasonCode
    model_status: ModelStatus
    model_id: str | None


def _artifact(root: Path, name: str) -> dict[str, object]:
    try:
        data = json.loads((root / "artifacts" / name).read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ValueError(f"artifacts/{name}: not valid JSON: {err}") from err
    if not isinstance(data, dict):
        raise ValueError(f"artifacts/{name}: expected an object")
    return data


def _artifact_list(root: Path, name: str, key: str, model: type[M]) -> list[M]:
    """The checked `key` list of an artifact; a bad entry fails naming the file and the field."""
    data = _artifact(root, name)
    if not isinstance(data.get(key), list):
        raise ValueError(f"artifacts/{name}: expected an object with a {key} list")
    try:
        return TypeAdapter(list[model]).validate_python(data[key])
    except ValidationError as err:
        raise ValueError(f"artifacts/{name}: {err}") from err


def hazard_rows(root: Path) -> list[HazardRow]:
    """The checked rows of artifacts/hazard_labels.json; a bad row fails naming the file and the field."""
    return _artifact_list(root, HAZARD_LABELS, "rows", HazardRow)


def soil_rows(root: Path) -> list[SoilRow]:
    """The checked rows of artifacts/soil_wetness.json."""
    return _artifact_list(root, SOIL_WETNESS, "rows", SoilRow)


def risk_rows(root: Path) -> list[RiskRow]:
    """The checked rows of artifacts/risk_table.json."""
    return _artifact_list(root, RISK_TABLE, "rows", RiskRow)


def risk_seasons(root: Path) -> dict[SeasonCode, RiskSeason]:
    """The model status of each rice season in artifacts/risk_table.json, by season."""
    entries = _artifact_list(root, RISK_TABLE, "seasons", RiskSeason)
    by_season = {e.season: e for e in entries}
    if len(by_season) != len(entries):
        raise ValueError(f"artifacts/{RISK_TABLE}: a season is listed twice in seasons")
    return by_season


class GatesFile(BaseModel):
    """artifacts/gates.json (05-DATA-CONTRACTS §5b): the gate verdicts per season."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    generated_at: str
    freeze_commit: str = Field(min_length=1)
    gates: list[GateRow]


def gates_file(root: Path) -> GatesFile:
    """The checked content of artifacts/gates.json; a bad entry fails naming the file and the field."""
    try:
        return GatesFile.model_validate(_artifact(root, GATES))
    except ValidationError as err:
        raise ValueError(f"artifacts/{GATES}: {err}") from err


def gate_rows(root: Path) -> list[GateRow]:
    """The gate verdicts of artifacts/gates.json, in file order."""
    return gates_file(root).gates


class MetricsFile(BaseModel):
    """artifacts/metrics.json (05-DATA-CONTRACTS §5b): the scored runs, weather claims and one-off reports."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    generated_at: str
    freeze_commit: str = Field(min_length=1)
    test_years: YearSpan
    metrics: list[MetricRow]
    weather_claims: list[WeatherClaim]
    reports: list[ReportItem]


def metrics_file(root: Path) -> MetricsFile:
    """The checked content of artifacts/metrics.json; a bad entry fails naming the file and the field."""
    try:
        return MetricsFile.model_validate(_artifact(root, METRICS))
    except ValidationError as err:
        raise ValueError(f"artifacts/{METRICS}: {err}") from err


def _read_yaml(root: Path, name: str) -> object:
    try:
        return yaml.safe_load((root / "rules" / name).read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        raise ValueError(f"rules/{name}: not valid YAML: {err}") from err


def _read_entries(root: Path, name: str) -> list[dict[str, object]]:
    data = _read_yaml(root, name)
    if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
        raise ValueError(f"rules/{name}: expected a list of entries")
    return data


def _read_mapping(root: Path, name: str) -> dict[str, object]:
    data = _read_yaml(root, name)
    if not isinstance(data, dict):
        raise ValueError(f"rules/{name}: expected a mapping")
    return data


def load_rules(root: Path) -> list[Rule]:
    """The five official rules of rules/conditions.yaml (§6c) in RuleCode order; `article` is not an API field."""
    by_code: dict[str, Rule] = {}
    for entry in _read_entries(root, "conditions.yaml"):
        rule = _checked("conditions.yaml", Rule, {k: v for k, v in entry.items() if k != "article"})
        if rule.code in by_code:
            raise ValueError(f"rules/conditions.yaml: {rule.code} is listed twice")
        by_code[rule.code] = rule
    missing = [code for code in RULE_CODES if code not in by_code]
    if missing:
        raise ValueError(f"rules/conditions.yaml: no entry for {missing}")
    return [by_code[code] for code in RULE_CODES]


def load_sources(root: Path) -> dict[SourceId, SourceFacts]:
    """Source facts of rules/sources.yaml (§8) by id."""
    facts: dict[SourceId, SourceFacts] = {}
    for entry in _read_entries(root, "sources.yaml"):
        item = _checked("sources.yaml", SourceFacts, entry)
        if item.id in facts:
            raise ValueError(f"rules/sources.yaml: {item.id} is listed twice")
        facts[item.id] = item
    return facts


class Entry(BaseModel):
    """Base of the rules-file entries: an unknown or misspelt key is an error."""

    model_config = ConfigDict(extra="forbid")


class CropSeason(Entry):
    """One crop of a plan's `seasons` in rules/rotations.yaml (05-DATA-CONTRACTS §7)."""

    crop_key: str
    crop_id: str
    variety: Text | None
    season: SeasonCode
    sow_from: MonthDay | None
    sow_to: MonthDay | None
    harvest_from: MonthDay | None
    harvest_to: MonthDay | None


class Economics(Entry):
    """`reported_economics` of a plan (05-DATA-CONTRACTS §7): money as the study reports it, per crop key."""

    source_id: SourceId
    definition: Text
    unit: Text | None = None
    profit_per_crop: dict[str, str] = {}
    cost_per_crop: dict[str, str] = {}
    price_year: str | None
    flags: dict[str, Text] = {}
    text_only: Text | None = None


class WhyParts(Entry):
    """The four Why parts of a plan (05-DATA-CONTRACTS §7 `why`); the Why risks are the plan's `risks`."""

    why: Text
    evidence: Text
    benefits: Text
    gaps: Text


class PlanEntry(Entry):
    """One plan of rules/rotations.yaml (05-DATA-CONTRACTS §7)."""

    id: PlanId
    name: Text
    is_usual: bool
    land_archetypes: list[str]
    provinces_studied: list[str]
    site: str
    trial_period: str
    seasons: list[CropSeason]
    reported_economics: Economics
    why: WhyParts
    risks: list[RiskItem]
    study_type: str
    limitations: list[Text]
    source_ids: list[SourceId] = Field(min_length=1)


class WaterFactEntry(Entry):
    """One cited water fact of a crop (05-DATA-CONTRACTS §6)."""

    source_id: SourceId
    measure: Literal["to_apply", "crop_uses"]
    value_text: str
    unit: Text
    scope: Text
    note: Text | None
    season: SeasonCode | None = None  # set on TCVN 8641 rows that apply to one rice season only (D-161)


class CropEntry(Entry):
    """One crop of rules/crops.yaml (05-DATA-CONTRACTS §6)."""

    crop_id: str
    name: Text
    is_legume: bool
    legume_source_ids: list[SourceId]
    water_facts: list[WaterFactEntry]


class SeasonLabel(Entry):
    label: Text
    source_ids: list[SourceId] = Field(min_length=1)


class CardTexts(BaseModel):
    """The parts of rules/method.yaml the cards use (05-DATA-CONTRACTS §7b); the other parts are the method page's."""

    model_config = ConfigDict(extra="ignore")

    stability_scope: Text
    season_labels: dict[SeasonCode, SeasonLabel]


class PrivacyTexts(Entry):
    """The privacy notice of the optional sign-in in rules/privacy.yaml (UI-UX-SPEC §12c)."""

    title: Text
    draft_note: Text
    paragraphs: list[Text] = Field(min_length=1)


class MethodTexts(BaseModel):
    """The parts of rules/method.yaml the method page uses (05-DATA-CONTRACTS §7b; UI-UX-SPEC §11b items 2, 3, 5)."""

    model_config = ConfigDict(extra="ignore")

    coverage: list[CoverageCell]
    explain_terms: list[ExplainTerm]
    limitations: list[Text] = Field(min_length=1)


class MlWindow(Entry):
    """One NSO season window of rules/calendar.yaml (05-DATA-CONTRACTS §6b): (month, year offset) at each end."""

    nso_season: Literal["spring", "autumn", "winter"]
    calendar_region: str
    start: tuple[Month, int]
    end: tuple[Month, int]
    source_ids: list[SourceId] = Field(min_length=1)


class TrialWindow(Entry):
    """The window text of a season that is not an NSO rice season (rules/calendar.yaml `trial_windows`, D-158)."""

    season: SeasonCode
    window: Text
    source_ids: list[SourceId] = Field(min_length=1)


class CalendarFile(BaseModel):
    """The window lists of rules/calendar.yaml; `excluded` is read by the pipeline only."""

    model_config = ConfigDict(extra="ignore")

    ml_windows: list[MlWindow]
    trial_windows: list[TrialWindow]


def load_plans(root: Path) -> list[PlanEntry]:
    """The six plans of rules/rotations.yaml, which must come in the canonical order (UI-UX-SPEC §11)."""
    plans = [_checked("rotations.yaml", PlanEntry, entry) for entry in _read_entries(root, "rotations.yaml")]
    ids = tuple(p.id for p in plans)
    if ids != PLAN_IDS:
        raise ValueError(f"rules/rotations.yaml: plans must be {PLAN_IDS} in this order, got {ids}")
    return plans


def load_crops(root: Path) -> dict[str, CropEntry]:
    """The crops of rules/crops.yaml by crop id."""
    crops: dict[str, CropEntry] = {}
    for entry in _read_entries(root, "crops.yaml"):
        crop = _checked("crops.yaml", CropEntry, entry)
        if crop.crop_id in crops:
            raise ValueError(f"rules/crops.yaml: {crop.crop_id} is listed twice")
        crops[crop.crop_id] = crop
    return crops


def load_card_texts(root: Path) -> CardTexts:
    return _checked("method.yaml", CardTexts, _read_mapping(root, "method.yaml"))


def load_method_texts(root: Path) -> MethodTexts:
    return _checked("method.yaml", MethodTexts, _read_mapping(root, "method.yaml"))


def load_privacy_texts(root: Path) -> PrivacyTexts:
    return _checked("privacy.yaml", PrivacyTexts, _read_mapping(root, "privacy.yaml"))


def load_calendar(root: Path) -> CalendarFile:
    return _checked("calendar.yaml", CalendarFile, _read_mapping(root, "calendar.yaml"))


def pick_sources(facts: dict[SourceId, SourceFacts], ids: Iterable[SourceId]) -> dict[SourceId, SourceFacts]:
    """The facts of exactly the ids a response uses; an id without facts fails (H5)."""
    used = sorted(set(ids))
    missing = [sid for sid in used if sid not in facts]
    if missing:
        raise ValueError(f"rules/sources.yaml: no entry for {missing}")
    return {sid: facts[sid] for sid in used}


def _checked(name: str, model: type[M], entry: dict[str, object]) -> M:
    try:
        return model.model_validate(entry)
    except ValidationError as err:
        raise ValueError(f"rules/{name}: {err}") from err
