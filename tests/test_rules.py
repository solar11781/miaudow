"""Tests for reading the rules files and artifacts (written before the code change). Placeholder fixtures only.

Spec: 05-DATA-CONTRACTS §4b (hazard_labels.json: an object with `rows`; `level` is `crop` or `year`; `year`
1995..2024; `rule` one of the five codes; `share_farmland` float 0..1 or null), §6c (one entry per rule code), §8 (one
entry per source id); .claude/rules/python.md: unknown data symbols fail loudly, errors name the input.
"""

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from fieldshift.engine.rules import hazard_rows, load_privacy_texts, load_rules, load_sources, pick_sources

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


def crop_row(**changes: object) -> dict:
    row = json.loads((FIX / "artifacts" / "hazard_labels.json").read_text(encoding="utf-8"))["rows"][0]
    return {**row, **changes}


@pytest.mark.parametrize(
    "row",
    [
        a_row(plan_id="cc1"),  # level year: plan_id, crop_key and season are null (§4b)
        a_row(crop_key="cc1_spring_peanut"),
        a_row(season="spring"),
        crop_row(plan_id="usual_p03"),  # level crop: usual, cc1..cc4 (P-03 reports no dates)
        crop_row(plan_id=None),
        crop_row(crop_key=None),
        crop_row(season="winter"),  # crop seasons: spring, summer_autumn, autumn_winter
        crop_row(season=None),
        a_row(months=[13]),  # calendar months
        a_row(months=[0]),
        a_row(n_cells=-1),  # a count of cells
        a_row(field_dates=[["03-01", "02-01"]]),  # sowing date, then first harvest date, inside one year
    ],
)
def test_a_hazard_row_against_its_level_fails(root: Path, row: dict) -> None:
    write_rows(root, [row])
    with pytest.raises(ValueError, match=r"hazard_labels\.json"):
        hazard_rows(root)


def test_a_valid_crop_row_is_read(root: Path) -> None:
    write_rows(root, [crop_row()])
    assert hazard_rows(root)[0].crop_key == "cc1_spring_peanut"


@pytest.mark.parametrize(("name", "load"), [("conditions.yaml", load_rules), ("sources.yaml", load_sources)])
def test_a_bad_entry_fails_naming_the_file(root: Path, name: str, load: Callable[[Path], object]) -> None:
    path = root / "rules" / name
    path.write_text(
        path.read_text(encoding="utf-8").replace("citation:", "citaton:", 1).replace("label:", "lable:", 1),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=name.replace(".", r"\.")):
        load(root)


@pytest.mark.parametrize(
    ("path", "text", "load"),
    [
        ("artifacts/hazard_labels.json", "{rows", hazard_rows),
        ("rules/conditions.yaml", "- [unclosed", load_rules),
        ("rules/sources.yaml", "- {unclosed", load_sources),
    ],
)
def test_a_file_with_broken_syntax_fails_naming_the_file(
    root: Path, path: str, text: str, load: Callable[[Path], object]
) -> None:
    (root / path).write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=path.split("/")[1].replace(".", r"\.")):
        load(root)


def test_a_privacy_notice_without_paragraphs_or_english_fails_naming_the_file(root: Path) -> None:
    # H15: every shown text has both languages; a notice with nothing to say must not start the app
    path = root / "rules" / "privacy.yaml"
    head = "title: {vi: a, en: b}\ndraft_note: {vi: c, en: d}\n"
    for text in (head + "paragraphs: []\n", head + "paragraphs: [{vi: e}]\n"):
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError, match=r"privacy\.yaml"):
            load_privacy_texts(root)
