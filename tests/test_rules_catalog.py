"""Checks of the real rules catalog files (written before the files): rules/conditions.yaml, sources.yaml, crops.yaml,
rotations.yaml and method.yaml.

Spec: 05-DATA-CONTRACTS §6 (crops and cited water facts, D-64, D-68), §6c (conditions), §7 (rotations), §7b (method
page content), §8 (sources); UI-UX-SPEC §11 (canonical ids, crop keys, season windows), §8 (money flags, plan risks),
§11b (coverage table, explain terms); hard rule H5 (every id used has its source facts). Expected values are copied
from those spec lines or from the cited source, never from the files under test.
"""

import json
import re
from pathlib import Path
from typing import get_args

import pytest
import yaml
from pydantic import TypeAdapter

from fieldshift.engine.rules import load_rules, load_sources
from fieldshift.engine.schemas import EXPLAIN_KEYS, PLAN_IDS, RULE_CODES, CropSpan, SeasonCode, Text
from source_trace import known_ids_from

REPO = Path(__file__).resolve().parents[1]
RULES = REPO / "rules"
REFERENCES = REPO / "docs" / "REFERENCES.md"
EXPERIMENTS = REPO / "docs" / "EXPERIMENTS.md"
TEXT = TypeAdapter(Text)
SEASON_CODES = get_args(SeasonCode)  # UI-UX-SPEC §11 SeasonCode, in contract order
# 05-DATA-CONTRACTS §6: one entry per crop id (the crops of the UI-UX-SPEC §11b coverage table)
CROP_IDS = (
    "rice",
    "peanut",
    "mung_bean",
    "maize_grain",
    "maize_biomass",
    "soybean",
    "sweet_potato",
    "black_bean",
    "black_sesame",
    "chili",
    "pumpkin",
)
ID_KEYS = ("source_ids", "values_source_ids", "principle_source_ids", "legume_source_ids")
ID_SINGLE_KEYS = ("source_id", "threshold_source_id", "computed_by")
LAND_CARE_PRINCIPLES = {"R-E13", "R-E12", "R-E06"}  # 05-DATA-CONTRACTS §7: principle sources of the land-care checks
SOURCE_ID = re.compile(r"^(R-[A-Z]+\d+[a-z]?|E-\d{3}[a-z]?)$")  # UI-UX-SPEC §11 canonical source ids
NOT_FULL_TEXT = re.compile(r"abstract|title|summary|metadata|secondary", re.IGNORECASE)  # 05-DATA-CONTRACTS §8


def read(name: str) -> object:
    return yaml.safe_load((RULES / name).read_text(encoding="utf-8"))


def ids_in(node: object) -> set[str]:
    """Every source id held by an id field anywhere inside a rules file."""
    if isinstance(node, list):
        return {sid for item in node for sid in ids_in(item)}
    if not isinstance(node, dict):
        return set()
    found: set[str] = set()
    for key, child in node.items():
        if key in ID_KEYS and isinstance(child, list):
            found |= set(child)
        elif key in ID_SINGLE_KEYS and isinstance(child, str):
            found.add(child)
        else:
            found |= ids_in(child)
    return found


def is_text(value: object) -> bool:
    TEXT.validate_python(value)
    return all(isinstance(v, str) and v.strip() for v in value.values())


def by_id(entries: list[dict], key: str) -> dict[str, dict]:
    return {entry[key]: entry for entry in entries}


# ---- conditions.yaml (05-DATA-CONTRACTS §6c; 03-ML-SPEC §5a)

# fragments of the quoted QĐ 18/2021 level-1 text per rule, as 03-ML-SPEC §5a quotes them
RULE_QUOTES = {
    "heavy_rain": [
        "lượng mưa từ 100 mm đến 200 mm trong 24 giờ hoặc từ 50 mm đến 100 mm trong 12 giờ, kéo dài từ 1 ngày đến 2 ngày"
    ],
    "heat": ["đợt nắng nóng với nhiệt độ cao nhất trong ngày từ 35°c đến 37°c, kéo dài từ 3 ngày trở lên"],
    "drought_rain_consecutive": [
        "thiếu hụt tổng lượng mưa tháng trên 50% so với trung bình nhiều năm, kéo dài từ 2 tháng đến 3 tháng"
    ],
    "drought_rain_any2": [
        "thiếu hụt tổng lượng mưa tháng trên 50% so với trung bình nhiều năm, kéo dài từ 2 tháng đến 3 tháng"
    ],
    "cold": [
        "nhiệt độ không khí trung bình ngày từ trên 8°c đến 13°c, kéo dài từ trên 5 ngày đến 10 ngày ở vùng đồng bằng "
        "Bắc Bộ, Bắc Trung Bộ, Trung Trung Bộ hoặc kéo dài trên 10 ngày ở vùng núi, trung du Bắc Bộ",
        "từ 8°c trở xuống, kéo dài từ 3 ngày đến 5 ngày ở vùng đồng bằng Bắc Bộ, Bắc Trung Bộ, Trung Trung Bộ",
    ],
}
RULE_ARTICLES = {
    "heavy_rain": "44",
    "heat": "47",
    "drought_rain_consecutive": "48",
    "drought_rain_any2": "48",
    "cold": "53",
}


def test_the_five_rules_load_in_code_order_with_their_fixed_sources() -> None:
    rules = load_rules(REPO)
    assert tuple(rule.code for rule in rules) == RULE_CODES
    for rule in rules:
        assert rule.threshold_source_id == "R-A01"  # §6c
        assert rule.values_source_ids == ["R-N01", "R-N02"]  # §6c
        assert rule.computed_by == "E-019"  # EXPERIMENTS E-019: `computed_by` of the risk-level labels


def test_each_rule_quotes_its_article() -> None:
    for entry in read("conditions.yaml"):
        code = entry["code"]
        assert is_text(entry["label"])
        assert is_text(entry["rule_text"])
        assert f"Art. {RULE_ARTICLES[code]}" in entry["article"], code
        for quote in RULE_QUOTES[code]:
            assert quote in entry["rule_text"]["vi"], code
        assert entry["rule_text"]["en"] != entry["rule_text"]["vi"]  # §6c: the English side is our translation


# ---- crops.yaml (05-DATA-CONTRACTS §6; 03-ML-SPEC §4b; D-64, D-68)

TCVN, FAO = "R-W15", "R-M02"
# 05-DATA-CONTRACTS §6 "Values in use": (measure, value_text) per crop id
WATER_VALUES = {
    "rice": sorted(
        [
            ("to_apply", v)
            for v in ("6,500-7,500", "6,000-7,000", "6,500-7,500", "5,700-7,000", "6,000-7,000", "4,500-5,500")
        ]
        + [("crop_uses", "450-700")]
    ),
    "maize_grain": [("crop_uses", "500-800"), ("to_apply", "2,000-2,500")],
    "peanut": [("crop_uses", "500-700"), ("to_apply", "2,000")],
    "soybean": [("crop_uses", "450-700"), ("to_apply", "2,000")],
    "sweet_potato": [("to_apply", "1,200-1,400")],
    # not listed in these sources (D-68): no fact is stored
    "mung_bean": [],
    "black_bean": [],
    "black_sesame": [],
    "chili": [],
    "pumpkin": [],
    "maize_biomass": [],
}


def test_crops_are_the_eleven_crop_ids() -> None:
    crops = read("crops.yaml")
    assert tuple(c["crop_id"] for c in crops) == CROP_IDS
    for crop in crops:
        assert is_text(crop["name"]), crop["crop_id"]
        assert crop["is_legume"] in (True, False, None), crop["crop_id"]
        if crop["is_legume"]:
            assert crop["legume_source_ids"], crop["crop_id"]


# USDA GRIN-Global taxon pages (R-B01): Fabaceae is the legume family; every other family is not
CROP_FAMILIES = {
    "rice": "Poaceae",  # Oryza sativa, id 26077
    "peanut": "Fabaceae",  # Arachis hypogaea, id 3785
    "mung_bean": "Fabaceae",  # Vigna radiata, id 41629
    "maize_grain": "Poaceae",  # Zea mays, id 42207
    "maize_biomass": "Poaceae",  # Zea mays, id 42207
    "soybean": "Fabaceae",  # Glycine max, id 17711
    "sweet_potato": "Convolvulaceae",  # Ipomoea batatas, id 20142
    "black_bean": "Fabaceae",  # Vigna unguiculata Biflora Group, id 467840; name from Đỗ Tất Lợi (R-B02)
    "black_sesame": "Pedaliaceae",  # Sesamum indicum, id 33749
    "chili": "Solanaceae",  # Capsicum annuum 8904, Capsicum frutescens 8913
    "pumpkin": "Cucurbitaceae",  # Cucurbita moschata, id 12601
}


def test_legume_flags_follow_the_grin_family_and_cite_it() -> None:
    for crop in read("crops.yaml"):
        assert crop["is_legume"] is (CROP_FAMILIES[crop["crop_id"]] == "Fabaceae"), crop["crop_id"]
        assert "R-B01" in crop["legume_source_ids"], crop["crop_id"]
    assert "R-B02" in by_id(read("crops.yaml"), "crop_id")["black_bean"]["legume_source_ids"]


def test_water_facts_are_the_cited_values_only() -> None:
    for crop in read("crops.yaml"):
        facts = crop["water_facts"]
        assert sorted((f["measure"], f["value_text"]) for f in facts) == WATER_VALUES[crop["crop_id"]], crop["crop_id"]
        for fact in facts:
            assert fact["source_id"] == {"to_apply": TCVN, "crop_uses": FAO}[fact["measure"]]
            assert (
                fact["unit"]
                == {"to_apply": {"vi": "m3/ha", "en": "m3/ha"}, "crop_uses": {"vi": "mm", "en": "mm"}}[fact["measure"]]
            )
            assert is_text(fact["scope"])
            assert fact["note"] is None or is_text(fact["note"])
    rice = by_id(read("crops.yaml"), "crop_id")["rice"]["water_facts"]
    scopes = " ".join(f["scope"]["vi"] for f in rice if f["measure"] == "to_apply")
    assert "Trung bộ" in scopes
    assert "Bắc bộ" in scopes


def test_fao_facts_are_marked_rough_estimates() -> None:
    for crop in read("crops.yaml"):
        for fact in crop["water_facts"]:
            if fact["measure"] == "crop_uses":
                assert "rough estimate" in fact["note"]["en"]  # FAO TM3: "provide a rough estimate"


# ---- rotations.yaml (05-DATA-CONTRACTS §7; UI-UX-SPEC §8, §11)

# UI-UX-SPEC §11 season codes: the P-02 sowing and harvest ranges per season ("MM-DD")
P02_WINDOWS = {
    "spring": (("01-17", "01-18"), ("04-05", "06-25")),
    "summer_autumn": (("06-06", "06-10"), ("08-20", "09-12")),
    "autumn_winter": (("08-15", "09-10"), ("11-21", "12-22")),
}
# P-02 abstract (R-P02): spring peanut 25.98, summer-autumn biomass maize 19.45, autumn-winter pumpkin 30.44 million
# VND/ha, i.e. Table 13 values in thousand VND/ha
P02_ABSTRACT_PROFITS = {
    ("cc1", "cc1_spring_peanut"): "25,980",
    ("cc4", "cc4_summer_autumn_maize_biomass"): "19,450",
    ("cc3", "cc3_autumn_winter_pumpkin"): "30,440",
}
# P-02 (R-P02) per crop key: crop id, sowing date, first and last harvest date (Tables 1, 5, 9), Table 13 "Lãi thuần"
# and Tables 4, 8, 12 "Tổng chi" (thousand VND/ha), as recorded in the research notes of the full text
P02_CROPS = {
    "usual_spring_rice": ("rice", "01-17", "05-17", "05-17", "5,149", "32,426"),
    "usual_summer_autumn_black_bean": ("black_bean", "06-06", "08-25", "08-25", "16,200", "25,000"),
    "usual_autumn_winter_sweet_potato": ("sweet_potato", "08-15", "12-10", "12-10", "9,450", "40,800"),
    "cc1_spring_peanut": ("peanut", "01-18", "05-12", "05-12", "25,980", "83,500"),
    "cc1_summer_autumn_mung_bean": ("mung_bean", "06-10", "08-30", "09-03", "16,200", "25,000"),
    "cc1_autumn_winter_maize_grain": ("maize_grain", "09-01", "12-22", "12-22", "11,200", "29,900"),
    "cc2_spring_chili": ("chili", "01-17", "06-25", "06-25", "21,100", "113,100"),
    "cc2_summer_autumn_soybean": ("soybean", "06-10", "09-09", "09-12", "16,700", "26,500"),
    "cc2_autumn_winter_maize_biomass": ("maize_biomass", "09-10", "11-26", "11-26", "15,865", "27,400"),
    "cc3_spring_maize_grain": ("maize_grain", "01-17", "05-04", "05-04", "12,420", "29,100"),
    "cc3_summer_autumn_black_sesame": ("black_sesame", "06-10", "09-04", "09-04", "12,500", "23,500"),
    "cc3_autumn_winter_pumpkin": ("pumpkin", "09-05", "11-21", "11-21", "30,440", "48,200"),
    "cc4_spring_maize_biomass": ("maize_biomass", "01-17", "04-05", "04-05", "18,925", "27,400"),
    "cc4_summer_autumn_maize_biomass": ("maize_biomass", "06-10", "08-20", "08-20", "19,450", "27,300"),
    "cc4_autumn_winter_sweet_potato": ("sweet_potato", "09-05", "12-02", "12-02", "20,390", "63,200"),
}
NO_RICE_PLANS = ("cc1", "cc2", "cc3", "cc4")  # UI-UX-SPEC §8 check row: plans without rice get the land-law quotes


def plans() -> dict[str, dict]:
    return by_id(read("rotations.yaml"), "id")


INTERNAL_LABEL = re.compile(r"\b[DP]-\d")  # our decision and paper note ids never show on a farmer screen


def test_plans_are_the_six_canonical_ids_in_order() -> None:
    entries = read("rotations.yaml")
    assert tuple(p["id"] for p in entries) == PLAN_IDS
    for plan in entries:
        assert plan["is_usual"] is (plan["id"] in ("usual", "usual_p03"))
        assert is_text(plan["name"])
        for field in ("source_ids", "land_archetypes", "limitations"):  # §7: every rule has these
            assert plan[field], (plan["id"], field)
        for line in plan["limitations"]:
            assert is_text(line), plan["id"]  # UI-UX-SPEC §11: displayed text is a Text in both languages
            assert not INTERNAL_LABEL.search(line["vi"] + line["en"]), line
        assert plan["study_type"]


def test_crop_keys_ids_and_dates() -> None:
    crop_ids = {c["crop_id"] for c in read("crops.yaml")}
    for plan_id, plan in plans().items():
        keys = [s["crop_key"] for s in plan["seasons"]]
        assert len(keys) == len(set(keys))
        for span in plan["seasons"]:
            assert span["crop_key"] == f"{plan_id}_{span['season']}_{span['crop_id']}"  # UI-UX-SPEC §11 crop keys
            assert span["crop_id"] in crop_ids
            assert span["season"] in SEASON_CODES
            dates = [span["sow_from"], span["sow_to"], span["harvest_from"], span["harvest_to"]]
            CropSpan.model_validate({**span, "crop": {"vi": "x", "en": "x"}, "variety": None, "source_ids": ["R-P02"]})
            if plan_id == "usual_p03":
                assert dates == [None] * 4  # §7: P-03 reports durations only
                continue
            (sow_lo, sow_hi), (harvest_lo, harvest_hi) = P02_WINDOWS[span["season"]]
            assert sow_lo <= span["sow_from"] <= span["sow_to"] <= sow_hi, span["crop_key"]
            assert harvest_lo <= span["harvest_from"] <= span["harvest_to"] <= harvest_hi, span["crop_key"]
            assert span["variety"] is None or is_text(span["variety"])


# P-03 running text, pp. [4] and [5]: the authors' term, season name and units for the rice control
P03_CONTROL_TEXT = (
    "Lúa vụ Đông Xuân 2021 (đối chứng): hiệu quả kinh tế 5,36 triệu đồng/ha",  # season name of the copy glossary
    "gần như không có lợi nhuận, hiệu quả kinh tế chỉ đạt 1,16 triệu/ha",
)


def test_p02_money_per_crop() -> None:
    for plan_id, plan in plans().items():
        money = plan["reported_economics"]
        assert is_text(money["definition"])
        assert money["price_year"] == "2020-21"  # §7 (P-02 trial 2020-21); D-103 (P-03)
        if plan_id == "usual_p03":
            assert money["source_id"] == "R-P03"
            assert "Lợi nhuận = GR - Tổng chi phí vật chất" in money["definition"]["vi"]  # P-03 p.3
            assert is_text(money["text_only"])
            for fragment in P03_CONTROL_TEXT:
                assert fragment in " ".join(money["text_only"]["vi"].split()), fragment
            assert "profit 5.36" not in money["text_only"]["en"].lower()  # the article's term is economic return
            assert "profit_per_crop" not in money  # §7: no per-crop money list for P-03
            continue
        assert money["source_id"] == "R-P02"
        assert "lợi nhuận thuần (RVAC) = GR - TVC" in money["definition"]["vi"]  # P-02, §7
        keys = {s["crop_key"] for s in plan["seasons"]}
        assert set(money["profit_per_crop"]) == keys
        assert set(money["cost_per_crop"]) == keys
        assert is_text(money["unit"])
        for flag in money["flags"].values():
            assert is_text(flag)
        assert set(money["flags"]) <= keys
    for (plan_id, key), value in P02_ABSTRACT_PROFITS.items():
        assert plans()[plan_id]["reported_economics"]["profit_per_crop"][key] == value
    assert "cc1_summer_autumn_mung_bean" in plans()["cc1"]["reported_economics"]["flags"]  # §7, UI-UX-SPEC §8
    assert "usual_summer_autumn_black_bean" in plans()["usual"]["reported_economics"]["flags"]


def test_p02_crops_dates_and_money_are_the_reported_values() -> None:
    found = {}
    for plan_id, plan in plans().items():
        if plan_id == "usual_p03":
            continue
        money = plan["reported_economics"]
        for span in plan["seasons"]:
            key = span["crop_key"]
            found[key] = (
                span["crop_id"],
                span["sow_from"],
                span["harvest_from"],
                span["harvest_to"],
                money["profit_per_crop"][key],
                money["cost_per_crop"][key],
            )
            assert span["sow_to"] == span["sow_from"]  # P-02 gives one sowing date per crop
    assert found == P02_CROPS
    assert [s["crop_id"] for s in plans()["usual_p03"]["seasons"]] == ["rice", "rice"]  # P-03 "Lúa - lúa - bỏ hoang"


SHORT_SPRING = re.compile(r"(?<!Đông )\b[Vv]ụ Xuân")  # GLOSSARY.md: the spring season is "Vụ Đông Xuân"


def test_spring_season_is_named_as_the_glossary_names_it() -> None:
    for name in ("rotations.yaml", "method.yaml"):
        text = (RULES / name).read_text(encoding="utf-8")
        assert not SHORT_SPRING.search(text), name


def test_plan_risks() -> None:
    for plan_id, plan in plans().items():
        cited = set()
        for risk in plan["risks"]:
            assert is_text(risk["text"])
            assert not INTERNAL_LABEL.search(risk["text"]["vi"] + risk["text"]["en"]), risk
            cited |= set(risk["source_ids"])
        assert ("R-G06" in cited) is (plan_id in NO_RICE_PLANS), plan_id


# R-C13, VietNamNet 31/08/2020, words of Hoàng Nghĩa Hiếu, vice chair of the Nghệ An People's Committee
R_C13_QUOTE = (
    "Chúng tôi chủ trương những vùng trồng ngô sinh khối làm thức ăn xanh cho bò phải có hợp đồng thu mua với các đơn "
    "vị bao tiêu sản phẩm."
)


def test_the_fodder_contract_risk_quotes_its_source() -> None:
    risks = [r for plan in plans().values() for r in plan["risks"] if "R-C13" in r["source_ids"]]
    assert risks
    for risk in risks:
        assert R_C13_QUOTE in " ".join(risk["text"]["vi"].split()), risk
        assert "our translation" in risk["text"]["en"]


# ---- method.yaml (05-DATA-CONTRACTS §7b; UI-UX-SPEC §11b)

COVERAGE_AXES = ("money", "conditions", "rice_history", "model", "water_tcvn", "water_fao")  # UI-UX-SPEC §11
# UI-UX-SPEC §11b coverage table: the crops of each row and, for rice, its season
COVERAGE_ROWS = {
    "rice_spring": (["rice"], "spring"),
    "rice_summer_autumn": (["rice"], "summer_autumn"),
    "peanut_maize_grain_soybean": (["peanut", "maize_grain", "soybean"], None),
    "sweet_potato": (["sweet_potato"], None),
    "not_listed_crops": (["mung_bean", "black_bean", "black_sesame", "chili", "pumpkin", "maize_biomass"], None),
}


def method() -> dict:
    return read("method.yaml")


def test_method_has_the_five_parts() -> None:
    assert set(method()) == {"coverage", "explain_terms", "limitations", "stability_scope", "season_labels"}
    assert is_text(method()["stability_scope"])
    assert method()["limitations"]
    assert all(is_text(line) for line in method()["limitations"])


def test_explain_terms_are_the_six_keys_in_order() -> None:
    terms = method()["explain_terms"]
    assert tuple(t["key"] for t in terms) == EXPLAIN_KEYS
    for term in terms:
        assert is_text(term["title"])
        assert is_text(term["text"])


def test_season_labels_cover_every_season_code() -> None:
    labels = method()["season_labels"]
    assert tuple(labels) == SEASON_CODES
    for entry in labels.values():
        assert is_text(entry["label"])
        assert entry["source_ids"]


def test_coverage_has_each_row_and_axis_once() -> None:
    cells = method()["coverage"]
    pairs = [(c["row_key"], c["axis"]) for c in cells]
    assert len(pairs) == len(set(pairs))
    assert set(pairs) == {(row, axis) for row in COVERAGE_ROWS for axis in COVERAGE_AXES}
    for cell in cells:
        assert is_text(cell["crop"])
        assert is_text(cell["text"])


def in_plans(plan_ids: set[str], crops: list[str], season: str | None) -> bool:
    spans = [s for p in plans().values() if p["id"] in plan_ids for s in p["seasons"]]
    return any(s["crop_id"] in crops and season in (None, s["season"]) for s in spans)


def test_coverage_agrees_with_the_rules_files() -> None:
    water = {c["crop_id"]: {f["source_id"] for f in c["water_facts"]} for c in read("crops.yaml")}
    gates = json.loads((REPO / "artifacts" / "gates.json").read_text(encoding="utf-8"))["gates"]
    g1 = {g["season"]: g["passed"] for g in gates if g["gate"] == "G1"}
    p02 = set(PLAN_IDS) - {"usual_p03"}
    for cell in method()["coverage"]:
        crops, season = COVERAGE_ROWS[cell["row_key"]]
        is_rice = crops == ["rice"]
        if cell["axis"] == "money":
            assert ("R-P02" in cell["source_ids"]) is in_plans(p02, crops, season), cell["row_key"]
            assert ("R-P03" in cell["source_ids"]) is in_plans({"usual_p03"}, crops, season), cell["row_key"]
        if cell["axis"] == "conditions":  # labels need P-02 dates (03-ML-SPEC §5a); P-03 gives none
            assert ("E-019" in cell["source_ids"]) is in_plans(p02, crops, season), cell["row_key"]
        if cell["axis"] == "model" and is_rice:  # G1 fails: never a model (D-66)
            assert cell["text"]["en"].startswith("Never") is (g1[season] is False), cell["row_key"]
        if cell["axis"] in ("water_tcvn", "water_fao"):
            source = TCVN if cell["axis"] == "water_tcvn" else FAO
            listed = all(source in water[c] for c in crops)
            assert ("not listed" not in cell["text"]["en"].lower()) is listed, (cell["row_key"], cell["axis"])
            assert cell["source_ids"] == [source]
        if cell["axis"] == "rice_history":
            assert ("R-D01" in cell["source_ids"]) is is_rice  # NSO rice history only for rice
        if cell["axis"] == "model":
            assert ("E-012" in cell["source_ids"]) is is_rice  # non-rice crops: study values only, no ML


# ---- sources.yaml (05-DATA-CONTRACTS §8; H5)

CATALOG = ("calendar.yaml", "conditions.yaml", "crops.yaml", "rotations.yaml", "method.yaml")


def artifact_ids() -> set[str]:
    return set(
        re.findall(
            r'"((?:R-[A-Z]+\d+[a-z]?)|(?:E-\d{3}[a-z]?))"',
            " ".join(p.read_text(encoding="utf-8") for p in sorted((REPO / "artifacts").glob("*.json"))),
        )
    )


def test_every_id_used_has_its_source_facts_and_no_entry_is_unused() -> None:
    facts = load_sources(REPO)
    used = set().union(*(ids_in(read(name)) for name in CATALOG)) | LAND_CARE_PRINCIPLES
    assert used - facts.keys() == set()  # H5
    assert facts.keys() - used - artifact_ids() == set()  # §8: one entry per id used by a displayed value


def test_source_facts_are_facts_only() -> None:
    for sid, item in load_sources(REPO).items():
        assert SOURCE_ID.match(sid), sid
        assert item.study_type["en"], sid  # TEST-PLAN §3: every source has its study type, place, years, limitations
        assert item.place_years["en"], sid
        assert item.limitations, sid
        if sid.startswith("E-"):
            assert (item.read_status, item.full_text_read) == (None, None), sid  # §8: null for EXPERIMENTS ids
            continue
        assert item.read_status, sid
        assert item.full_text_read is not None, sid
        if NOT_FULL_TEXT.search(item.read_status):
            assert item.full_text_read is False, sid  # §8, D-102
        assert item.nso_credit is (sid == "R-D01"), sid  # D-88: true for NSO statistics (R-D01, the NSO PX-Web tables)


def reference_status(references_md: str) -> dict[str, str]:
    """The Status cell per id from the REFERENCES tables whose last column is Status."""
    status: dict[str, str] = {}
    in_status_table = False
    for line in references_md.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.startswith("|"):
            in_status_table = False
        elif cells[0] in ("ID", "id"):
            in_status_table = cells[-1] == "Status"
        elif in_status_table and SOURCE_ID.match(cells[0].split()[0]):
            status.setdefault(cells[0].split()[0], cells[-1])
    return status


def test_reference_status_reads_the_status_column() -> None:
    text = "| ID | Citation | Status |\n|---|---|---|\n| R-P02 (P-02) | x | READ (full text) |\n\n| id | terms |\n| R-W15 | y |\n"
    assert reference_status(text) == {"R-P02": "READ (full text)"}


def test_read_status_matches_the_references() -> None:
    if not REFERENCES.exists() or not EXPERIMENTS.exists():
        pytest.skip(
            "docs/REFERENCES.md and docs/EXPERIMENTS.md are copied into this repository at the end of the event"
        )
    references = REFERENCES.read_text(encoding="utf-8")
    status = reference_status(references)
    known = known_ids_from(references, EXPERIMENTS.read_text(encoding="utf-8"))
    for sid, item in load_sources(REPO).items():
        assert sid in known, sid
        if sid.startswith("R-"):
            assert item.read_status == status[sid], sid
