"""GET /api/past-years content (UI-UX-SPEC §11 PastYearsResponse; 05-DATA-CONTRACTS §10).

Rules from rules/conditions.yaml, year rows from the `level` `year` rows of artifacts/hazard_labels.json (§4b), source
facts from rules/sources.yaml for every id used.
"""

from __future__ import annotations

from pathlib import Path

from fieldshift.engine.rules import load_rules, load_sources, pick_sources, read_artifact
from fieldshift.engine.schemas import RULE_CODES, PastYearsResponse, Province, Value, YearRow, source_ids_in
from fieldshift.engine.values import share_value

HAZARD_LABELS = "hazard_labels.json"
LEVELS = {"crop", "year"}  # 05-DATA-CONTRACTS §4b


def past_years(province: Province, root: Path) -> PastYearsResponse:
    all_rows = read_artifact(root, HAZARD_LABELS)["rows"]
    levels = {row["level"] for row in all_rows} - LEVELS
    if levels:
        raise ValueError(f"artifacts/{HAZARD_LABELS}: unknown level {sorted(levels)}")
    rows = [row for row in all_rows if row["level"] == "year"]
    if not rows:
        raise ValueError(f"artifacts/{HAZARD_LABELS}: no level year rows")
    cells = {row["n_cells"] for row in rows}
    if len(cells) != 1:
        raise ValueError(f"artifacts/{HAZARD_LABELS}: year rows disagree on n_cells: {sorted(cells)}")
    shares: dict[int, dict[str, Value | None]] = {}
    for row in rows:
        year_shares = shares.setdefault(row["year"], {})
        if row["rule"] in year_shares:
            raise ValueError(f"artifacts/{HAZARD_LABELS}: year {row['year']} has two {row['rule']} rows")
        year_shares[row["rule"]] = share_value(row)
    for year, year_shares in shares.items():  # YearRow also checks this; here the error names the year
        missing = [code for code in RULE_CODES if code not in year_shares]
        if missing:
            raise ValueError(f"artifacts/{HAZARD_LABELS}: year {year} has no row for {missing}")
    rules = load_rules(root)
    years = [YearRow.model_validate({"year": y, "shares": shares[y]}) for y in sorted(shares)]
    used = source_ids_in([item.model_dump() for item in (*rules, *years)])
    return PastYearsResponse(
        province=province,
        rules=rules,
        years=years,
        sources=pick_sources(load_sources(root), used),
        n_cells=cells.pop(),
    )
