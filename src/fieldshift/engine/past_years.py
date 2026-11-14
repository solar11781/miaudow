"""GET /api/past-years content (UI-UX-SPEC §11 PastYearsResponse; 05-DATA-CONTRACTS §10).

Rules from rules/conditions.yaml, year rows from the `level` `year` rows of artifacts/hazard_labels.json (§4b), source
facts from rules/sources.yaml for every id used.
"""

from __future__ import annotations

from pathlib import Path

from fieldshift.engine.rules import load_rules, load_sources, pick_sources, read_artifact
from fieldshift.engine.schemas import RULE_CODES, PastYearsResponse, Province, Value, YearRow
from fieldshift.engine.values import share_value

HAZARD_LABELS = "hazard_labels.json"


def past_years(province: Province, root: Path) -> PastYearsResponse:
    rows = [row for row in read_artifact(root, HAZARD_LABELS)["rows"] if row["level"] == "year"]
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
    for year, year_shares in shares.items():
        missing = [code for code in RULE_CODES if code not in year_shares]
        if missing:
            raise ValueError(f"artifacts/{HAZARD_LABELS}: year {year} has no row for {missing}")
    rules = load_rules(root)
    used = [sid for r in rules for sid in (r.threshold_source_id, *r.values_source_ids, r.computed_by)]
    used += [sid for s in shares.values() for v in s.values() if v is not None for sid in v.source_ids]
    return PastYearsResponse(
        province=province,
        rules=rules,
        years=[YearRow.model_validate({"year": y, "shares": shares[y]}) for y in sorted(shares)],
        sources=pick_sources(load_sources(root), used),
        n_cells=cells.pop(),
    )
