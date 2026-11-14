"""Validate the audited plan rulebook (api/rules/rotations.yaml) and write data/canonical/rotations.generated.json.

Run from the project root:  .venv\\Scripts\\python scripts/sync_rotations.py

The build refuses (RulebookError) when:
- a risk line lacks text (vi and en), source_id, location or quote, or names an unknown location_precision;
- any source_id (risk line, plan, season dates, money, crop facts) is not in data/rules/sources.yaml or not listed in
  the rulebook's source_documents;
- a source document is approved for recommendation (nothing is: these are reported study results only);
- plan_order is not the study order (usual, usual_p03, cc1, cc2, cc3, cc4) or the plans are listed in another order;
- a season names an unknown crop, or a profit or cost is not a plain number with digit grouping.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULEBOOK = ROOT / "api" / "rules" / "rotations.yaml"
SOURCES = ROOT / "data" / "rules" / "sources.yaml"
OUT = ROOT / "data" / "canonical" / "rotations.generated.json"
STUDY_ORDER = ["usual", "usual_p03", "cc1", "cc2", "cc3", "cc4"]
PRECISIONS = {"document", "section", "table", "page", "article"}
NUMBER = re.compile(r"^\d{1,3}(,\d{3})*$")


class RulebookError(ValueError):
    """The rulebook breaks one of the audit rules; nothing is written."""


def _text(value, where: str) -> dict:
    if not isinstance(value, dict) or not str(value.get("vi") or "").strip() or not str(value.get("en") or "").strip():
        raise RulebookError(f"{where}: text needs both vi and en")
    return {"vi": str(value["vi"]).strip(), "en": str(value["en"]).strip()}


def _number(value: str, where: str) -> int:
    if not isinstance(value, str) or not NUMBER.match(value):
        raise RulebookError(f"{where}: {value!r} is not a number written with digit grouping (e.g. '16,200')")
    return int(value.replace(",", ""))


def validate_risk_line(line, where: str, known_sources: set[str]) -> dict:
    """A risk line must say what, from which source, where in it, and quote it word for word."""
    if not isinstance(line, dict):
        raise RulebookError(f"{where}: a risk line must be structured, not {type(line).__name__}")
    text = _text(line.get("text"), where)
    for key in ("source_id", "location", "quote"):
        if not str(line.get(key) or "").strip():
            raise RulebookError(f"{where}: unsourced risk line, missing {key}")
    if line["source_id"] not in known_sources:
        raise RulebookError(f"{where}: source {line['source_id']!r} is not in data/rules/sources.yaml")
    precision = line.get("location_precision")
    if precision is not None and precision not in PRECISIONS:
        raise RulebookError(f"{where}: location_precision {precision!r} not in {sorted(PRECISIONS)}")
    return {
        "text": text,
        "source_id": line["source_id"],
        "location": str(line["location"]).strip(),
        "location_precision": precision,
        "quote": " ".join(str(line["quote"]).split()),
    }


def _check_source(sid: str, where: str, known: set[str], listed: set[str]) -> None:
    if sid not in known:
        raise RulebookError(f"{where}: source {sid!r} is not in data/rules/sources.yaml")
    if sid not in listed:
        raise RulebookError(f"{where}: source {sid!r} is not listed in source_documents")


def _plan(r: dict, crops: dict, known: set[str], listed: set[str]) -> dict:
    pid = r["id"]
    for sid in r.get("source_ids") or []:
        _check_source(sid, f"{pid}.source_ids", known, listed)
    land = r["study_land_type"]
    _check_source(land["source_id"], f"{pid}.study_land_type", known, listed)
    seasons = []
    for s in r["seasons"]:
        if s["crop_id"] not in crops:
            raise RulebookError(f"{pid}.{s['crop_key']}: unknown crop {s['crop_id']!r}")
        _check_source(s["dates_source_id"], f"{pid}.{s['crop_key']}.dates", known, listed)
        seasons.append({**s, "crop_name": crops[s["crop_id"]]["name"], "is_legume": crops[s["crop_id"]]["is_legume"]})
    econ = r["reported_economics"]
    _check_source(econ["source_id"], f"{pid}.reported_economics", known, listed)
    keys = {s["crop_key"] for s in seasons}
    per_crop = []
    for row in econ.get("per_crop") or []:
        if row["crop_key"] not in keys:
            raise RulebookError(f"{pid}: money row for unknown crop key {row['crop_key']!r}")
        for loc in ("profit_location", "cost_location"):
            if not str(row.get(loc) or "").strip():
                raise RulebookError(f"{pid}.{row['crop_key']}: missing {loc}")
        per_crop.append(
            {
                **row,
                "profit_value": _number(row["profit"], f"{pid}.{row['crop_key']}.profit"),
                "cost_value": _number(row["cost"], f"{pid}.{row['crop_key']}.cost"),
            }
        )
    if not per_crop and not econ.get("text_only"):
        raise RulebookError(f"{pid}: reported_economics needs per_crop rows or text_only")
    risks = [validate_risk_line(x, f"{pid}.risk_lines[{i}]", known) for i, x in enumerate(r.get("risk_lines") or [])]
    for line in risks:
        _check_source(line["source_id"], f"{pid}.risk_lines", known, listed)
    return {
        **r,
        "seasons": seasons,
        "reported_economics": {**econ, "per_crop": per_crop},
        "risk_lines": risks,
        "limitations": [_text(x, f"{pid}.limitations") for x in r.get("limitations") or []],
        "why": {k: _text(v, f"{pid}.why.{k}") for k, v in (r.get("why") or {}).items()},
    }


def build(rulebook: Path = RULEBOOK, sources: Path = SOURCES) -> dict:
    """Validate the rulebook and return the generated structure (no file is written)."""
    data = yaml.safe_load(Path(rulebook).read_text(encoding="utf-8"))
    known = {s["id"] for s in yaml.safe_load(Path(sources).read_text(encoding="utf-8"))}
    docs = data.get("source_documents") or []
    for d in docs:
        if d["id"] not in known:
            raise RulebookError(f"source_documents: {d['id']!r} is not in data/rules/sources.yaml")
        if d.get("approved_for_recommendation") is not False:
            raise RulebookError(f"source_documents: {d['id']} must have approved_for_recommendation: false")
    listed = {d["id"] for d in docs}
    if data.get("plan_order") != STUDY_ORDER:
        raise RulebookError(f"plan_order must be the study order {STUDY_ORDER}")
    ids = [r["id"] for r in data["rotations"]]
    if ids != STUDY_ORDER:
        raise RulebookError(f"rotations must be listed in the study order {STUDY_ORDER}, got {ids}")
    crops = {c["crop_id"]: c for c in data["crops"]}
    for c in crops.values():
        for sid in c.get("legume_source_ids") or []:
            _check_source(sid, f"crop {c['crop_id']}", known, listed)
        for f in c.get("water_facts") or []:
            _check_source(f["source_id"], f"crop {c['crop_id']} water fact", known, listed)
    plans = [_plan(r, crops, known, listed) for r in data["rotations"]]
    return {
        "schema_version": data["schema_version"],
        "ruleset_status": data["ruleset_status"],
        "plan_order": STUDY_ORDER,
        "source_documents": docs,
        "crops": list(crops.values()),
        "plans": plans,
    }


def main() -> None:
    out = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), **out}
    OUT.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    n_risks = sum(len(p["risk_lines"]) for p in out["plans"])
    sys.stdout.write(f"rotations.generated.json: {len(out['plans'])} plans, {n_risks} sourced risk lines\n")


if __name__ == "__main__":
    main()
