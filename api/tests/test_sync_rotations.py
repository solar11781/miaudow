"""The rulebook build refuses unsourced or unknown-source risk lines, approvals and any other order of plans."""

import copy
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sync_rotations", ROOT / "scripts" / "sync_rotations.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

RULEBOOK = yaml.safe_load((ROOT / "api" / "rules" / "rotations.yaml").read_text(encoding="utf-8"))


def _build(tmp_path, data):
    path = tmp_path / "rotations.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return sync.build(path, sync.SOURCES)


def _with_line(line):
    data = copy.deepcopy(RULEBOOK)
    data["rotations"][2]["risk_lines"].append(line)
    return data


GOOD = {
    "text": {"vi": "Một dòng có nguồn.", "en": "A sourced line."},
    "source_id": "R-P02",
    "location": "tr. 48",
    "location_precision": "page",
    "quote": "Tổng chi phí trồng lạc và ớt chỉ thiên F1 thường cao gấp 2 - 3 lần so với trồng lúa.",
}


def test_the_committed_rulebook_builds():
    out = sync.build()
    assert [p["id"] for p in out["plans"]] == sync.STUDY_ORDER
    assert all(d["approved_for_recommendation"] is False for d in out["source_documents"])
    assert all(line["quote"] and line["location"] for p in out["plans"] for line in p["risk_lines"])


@pytest.mark.parametrize("missing", ["source_id", "location", "quote"])
def test_risk_line_without_source_location_or_quote_fails(tmp_path, missing):
    line = {**GOOD, missing: ""}
    with pytest.raises(sync.RulebookError, match=f"unsourced risk line, missing {missing}"):
        _build(tmp_path, _with_line(line))


def test_risk_line_without_text_fails(tmp_path):
    with pytest.raises(sync.RulebookError, match="text needs both vi and en"):
        _build(tmp_path, _with_line({**GOOD, "text": {"vi": "", "en": "x"}}))


def test_plain_string_risk_line_fails(tmp_path):
    with pytest.raises(sync.RulebookError, match="must be structured"):
        _build(tmp_path, _with_line("Cây này rủi ro."))


def test_risk_line_with_a_source_not_in_sources_yaml_fails(tmp_path):
    with pytest.raises(sync.RulebookError, match="not in data/rules/sources.yaml"):
        _build(tmp_path, _with_line({**GOOD, "source_id": "R-X99"}))


def test_unknown_location_precision_fails(tmp_path):
    with pytest.raises(sync.RulebookError, match="location_precision"):
        _build(tmp_path, _with_line({**GOOD, "location_precision": "somewhere"}))


def test_a_document_approved_for_recommendation_fails(tmp_path):
    data = copy.deepcopy(RULEBOOK)
    data["source_documents"][0]["approved_for_recommendation"] = True
    with pytest.raises(sync.RulebookError, match="approved_for_recommendation: false"):
        _build(tmp_path, data)


def test_plans_in_another_order_fail(tmp_path):
    data = copy.deepcopy(RULEBOOK)
    data["rotations"] = list(reversed(data["rotations"]))
    with pytest.raises(sync.RulebookError, match="study order"):
        _build(tmp_path, data)


def test_money_must_be_a_grouped_number(tmp_path):
    data = copy.deepcopy(RULEBOOK)
    data["rotations"][2]["reported_economics"]["per_crop"][0]["profit"] = "about 26 million"
    with pytest.raises(sync.RulebookError, match="not a number"):
        _build(tmp_path, data)
