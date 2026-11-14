"""Read and check the rules files and artifacts the engine serves (04-TECH-DESIGN §2; 05-DATA-CONTRACTS §5-§8).

The engine reads only `rules/*.yaml` and `artifacts/*.json` under the project folder it is given (.claude/rules/python.md).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from fieldshift.engine.schemas import (
    FIRST_YEAR,
    LAST_YEAR,
    RULE_CODES,
    MonthDay,
    Rule,
    RuleCode,
    SeasonCode,
    SourceFacts,
    SourceId,
)

HAZARD_LABELS = "hazard_labels.json"


class HazardRow(BaseModel):
    """One row of artifacts/hazard_labels.json (05-DATA-CONTRACTS §4b); an artifact row, not an API type."""

    model_config = ConfigDict(extra="forbid")

    level: Literal["crop", "year"]
    plan_id: str | None
    crop_key: str | None
    season: SeasonCode | None
    months: list[int]
    field_dates: list[tuple[MonthDay, MonthDay]]
    year: int = Field(ge=FIRST_YEAR, le=LAST_YEAR)
    rule: RuleCode
    share_farmland: float | None = Field(ge=0, le=1)
    n_cells: int
    threshold_source_id: SourceId
    values_source_ids: list[SourceId]
    computed_by: SourceId


def hazard_rows(root: Path) -> list[HazardRow]:
    """The checked rows of artifacts/hazard_labels.json; a bad row fails naming the file and the field."""
    data = json.loads((root / "artifacts" / HAZARD_LABELS).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise ValueError(f"artifacts/{HAZARD_LABELS}: expected an object with a rows list")
    try:
        return TypeAdapter(list[HazardRow]).validate_python(data["rows"])
    except ValidationError as err:
        raise ValueError(f"artifacts/{HAZARD_LABELS}: {err}") from err


def _read_entries(root: Path, name: str) -> list[dict[str, object]]:
    data = yaml.safe_load((root / "rules" / name).read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
        raise ValueError(f"rules/{name}: expected a list of entries")
    return data


def load_rules(root: Path) -> list[Rule]:
    """The five official rules of rules/conditions.yaml (§6c) in RuleCode order; `article` is not an API field."""
    by_code: dict[str, Rule] = {}
    for entry in _read_entries(root, "conditions.yaml"):
        rule = Rule.model_validate({k: v for k, v in entry.items() if k != "article"})
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
        item = SourceFacts.model_validate(entry)
        if item.id in facts:
            raise ValueError(f"rules/sources.yaml: {item.id} is listed twice")
        facts[item.id] = item
    return facts


def pick_sources(facts: dict[SourceId, SourceFacts], ids: Iterable[SourceId]) -> dict[SourceId, SourceFacts]:
    """The facts of exactly the ids a response uses; an id without facts fails (H5)."""
    used = sorted(set(ids))
    missing = [sid for sid in used if sid not in facts]
    if missing:
        raise ValueError(f"rules/sources.yaml: no entry for {missing}")
    return {sid: facts[sid] for sid in used}
