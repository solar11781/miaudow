"""Tests for reading the rules files and artifacts (written before the code change). Placeholder fixtures only.

Spec: 05-DATA-CONTRACTS §4b (hazard_labels.json: an object with `rows`; `level` is `crop` or `year`; `year`
1995..2024; `rule` one of the five codes; `share_farmland` float 0..1 or null), §6c (one entry per rule code), §8 (one
entry per source id); .claude/rules/python.md: unknown data symbols fail loudly, errors name the input.
"""

import json
import shutil
from pathlib import Path

import pytest

from fieldshift.engine.rules import hazard_rows, load_rules, load_sources, pick_sources

FIX = Path(__file__).resolve().parent / "fixtures" / "engine"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    shutil.copytree(FIX, tmp_path / "root")
    return tmp_path / "root"


def write_rows(root: Path, rows: object) -> None:
    (root / "artifacts" / "hazard_labels.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")


def a_row(**changes: object) -> dict:
    row = json.loads((FIX / "artifacts" / "hazard_labels.json").read_text(encoding="utf-8"))["rows"][1]
    return {**row, **changes}


def test_hazard_rows_are_read_with_their_fields() -> None:
    rows = hazard_rows(FIX)
    assert len(rows) == 11  # fixture: 1 crop row + 2 years x 5 rules
    assert (rows[1].level, rows[1].year, rows[1].rule, rows[1].share_farmland) == ("year", 1996, "heavy_rain", 0.005)


@pytest.mark.parametrize(
    ("change", "named"),
    [
        ({"level": "Year"}, "level"),
        ({"rule": "rain"}, "rule"),
        ({"year": 1994}, "year"),
        ({"year": 2025}, "year"),
        ({"share_farmland": 1.5}, "share_farmland"),
        ({"share_farmland": -0.1}, "share_farmland"),
    ],
)
def test_a_bad_hazard_row_fails_naming_the_field(root: Path, change: dict, named: str) -> None:
    write_rows(root, [a_row(**change)])
    with pytest.raises(ValueError, match=named):
        hazard_rows(root)


def test_a_hazard_file_without_rows_fails_naming_the_file(root: Path) -> None:
    (root / "artifacts" / "hazard_labels.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match=r"hazard_labels.json"):
        hazard_rows(root)


def test_a_rules_file_that_is_not_a_list_fails_naming_the_file(root: Path) -> None:
    (root / "rules" / "conditions.yaml").write_text("cold: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"conditions.yaml"):
        load_rules(root)


def test_a_rule_listed_twice_or_missing_fails(root: Path) -> None:
    path = root / "rules" / "conditions.yaml"
    entries = path.read_text(encoding="utf-8").split("\n- ")
    path.write_text("\n- ".join([*entries, entries[1]]), encoding="utf-8")
    with pytest.raises(ValueError, match="cold is listed twice"):
        load_rules(root)
    path.write_text("\n- ".join(entries[:-1]), encoding="utf-8")
    with pytest.raises(ValueError, match="drought_rain_any2"):
        load_rules(root)


def test_a_source_listed_twice_fails(root: Path) -> None:
    path = root / "rules" / "sources.yaml"
    entries = path.read_text(encoding="utf-8").split("\n- ")
    path.write_text("\n- ".join([*entries, entries[1]]), encoding="utf-8")
    with pytest.raises(ValueError, match="R-A01 is listed twice"):
        load_sources(root)


def test_pick_sources_keeps_only_the_ids_used_and_names_a_missing_one() -> None:
    facts = load_sources(FIX)
    assert list(pick_sources(facts, ["R-N01", "R-A01", "R-N01"])) == ["R-A01", "R-N01"]
    with pytest.raises(ValueError, match="R-X01"):
        pick_sources(facts, ["R-X01"])
