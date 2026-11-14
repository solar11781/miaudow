"""Read and check the rules files and artifacts the engine serves (04-TECH-DESIGN §2; 05-DATA-CONTRACTS §5-§8).

The engine reads only `rules/*.yaml` and `artifacts/*.json` under the project folder it is given (.claude/rules/python.md).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import yaml

from fieldshift.engine.schemas import RULE_CODES, Rule, SourceFacts, SourceId


def read_artifact(root: Path, name: str) -> dict:
    data = json.loads((root / "artifacts" / name).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise ValueError(f"artifacts/{name}: expected an object with a rows list")
    return data


def _read_entries(root: Path, name: str) -> list[dict]:
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
