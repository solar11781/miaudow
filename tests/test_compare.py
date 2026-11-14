"""Tests for the compare response (written before the code), on the real rules files and artifacts.

Spec: UI-UX-SPEC §9 (card rows), §11 (CompareResponse, Plan and every sub-type); 05-DATA-CONTRACTS §4b, §4d (API
conversion: x 100 rounded half up to whole percent, unit "%", null stays null), §5, §6, §7, §10; 04-TECH-DESIGN §4;
TEST-PLAN §3 (engine checks); D-95, D-97, D-103, D-156, D-158 (team, 2026-11-14: autumn-winter window from P-02
Table 5; engine arithmetic cites its inputs plus E-022). Expected values are the real values of the cited files,
worked out by hand (percent = fraction x 100 rounded half up).
"""

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from fieldshift.engine.compare import compare
from fieldshift.engine.schemas import PLAN_IDS, CompareRequest
from source_trace import check_response

REPO = Path(__file__).resolve().parents[1]
YEARS = [1995, 2007, 2013, 2020]
PCT = {"vi": "%", "en": "%"}
SHARE_IDS = ["R-A01", "R-N01", "R-N02", "E-019"]  # hazard_labels.json crop rows: threshold, values, computed_by
SOIL_IDS = ["R-N01", "R-W12", "R-N02", "R-A15", "E-020"]  # soil_wetness.json rows: source_ids, computed_by
REAL_IDS = ["R-D01", "E-010"]  # risk_table.json anom_history_source_ids
P02_UNIT = {"vi": "nghìn đồng/ha", "en": "thousand đ/ha"}  # rules/rotations.yaml reported_economics.unit
WHY_PARTS = ("why", "evidence", "benefits", "gaps")


def request(years: list[int] = YEARS, land: str = "dry", priority: str = "income") -> CompareRequest:
    return CompareRequest(province="nghe_an", land=land, years=years, priority=priority)


def edit_yaml(root: Path, name: str, change: Callable[[list[dict]], object]) -> None:
    path = root / "rules" / name
    entries = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(entries)
    path.write_text(yaml.safe_dump(entries, allow_unicode=True, sort_keys=False), encoding="utf-8")


def edit_json(root: Path, name: str, change: Callable[[dict], object]) -> None:
    path = root / "artifacts" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture(scope="module")
def real() -> Path:
    """The repository root: the real rules files and artifacts."""
    return REPO


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A copy of the real rules files and artifacts that one test may change."""
    for folder in ("rules", "artifacts"):
        shutil.copytree(REPO / folder, tmp_path / "root" / folder)
    return tmp_path / "root"


@pytest.fixture(scope="module")
def resp(real: Path) -> dict:
    return compare(request(), real).model_dump(by_alias=True)


def plan(resp: dict, plan_id: str) -> dict:
    return next(p for p in resp["plans"] if p["id"] == plan_id)


def pct(value: str, ids: list[str]) -> dict:
    return {"value": value, "unit": PCT, "source_ids": ids}


# ---- response level


def test_plans_come_in_the_canonical_order(resp: dict) -> None:
    assert tuple(p["id"] for p in resp["plans"]) == PLAN_IDS  # UI-UX-SPEC §11: order is final (H3)
    assert [p["is_usual"] for p in resp["plans"]] == [True, True, False, False, False, False]


def test_land_and_priority_change_nothing_but_the_echo_t3(real: Path, resp: dict) -> None:
    # UI-UX-SPEC T3; 05-DATA-CONTRACTS §10: land and priority are echoed and change no number, order or content
    base = {k: v for k, v in resp.items() if k != "request"}
    for land in ("dry", "unsure"):
        for priority in ("income", "stability", "water", "land"):
            out = compare(request(land=land, priority=priority), real).model_dump(by_alias=True)
            assert out["request"] == {"province": "nghe_an", "land": land, "years": YEARS, "priority": priority}
            assert {k: v for k, v in out.items() if k != "request"} == base


def test_test_years_cells_and_rules(resp: dict) -> None:
    assert resp["test_years"] == {"first": 2016, "last": 2024}  # artifacts/metrics.json test_years
    assert resp["n_cells"] == 5  # artifacts/hazard_labels.json n_cells
    assert [r["code"] for r in resp["rules"]] == [
        "heavy_rain",
        "heat",
        "drought_rain_consecutive",
        "drought_rain_any2",
        "cold",
    ]


def test_seasons_label_every_season_code_used_in_plans(resp: dict) -> None:
    assert resp["seasons"] == [
        {  # rules/method.yaml season_labels; rules/calendar.yaml ml_windows spring north_central [2, 0] to [6, 0]
            "code": "spring",
            "label": {"vi": "Vụ Đông Xuân", "en": "Spring season"},
            "window": {"vi": "tháng 2 - tháng 6", "en": "February - June"},
            "source_ids": ["R-P02", "R-D01", "R-V05"],
        },
        {  # NSO "autumn" rice is the summer-autumn season (UI-UX-SPEC §11); north_central [5, 0] to [9, 0]
            "code": "summer_autumn",
            "label": {"vi": "Vụ Hè Thu", "en": "Summer-autumn season"},
            "window": {"vi": "tháng 5 - tháng 9", "en": "May - September"},
            "source_ids": ["R-P02", "R-D01", "R-V05"],
        },
        {  # not an NSO season: the P-02 Table 5 dates (D-158)
            "code": "autumn_winter",
            "label": {"vi": "Vụ Thu Đông", "en": "Autumn-winter season"},
            "window": {
                "vi": "gieo 15/8 - 10/9, thu hoạch 21/11 - 22/12",
                "en": "sown 15/8 - 10/9, harvested 21/11 - 22/12",
            },
            "source_ids": ["R-P02"],
        },
    ]


def test_gates_are_those_of_the_seasons_with_a_stability_block(resp: dict) -> None:
    # stability blocks: spring (usual, usual_p03) and summer_autumn (usual_p03); artifacts/gates.json in file order
    assert [(g["gate"], g["season"], g["passed"]) for g in resp["gates"]] == [
        ("G2", "spring", False),
        ("G3", "spring", True),
        ("G4", "spring", True),
        ("G1", "summer_autumn", False),
        ("G1", "spring", True),
    ]


def test_sources_hold_exactly_the_ids_used_and_every_id_traces(resp: dict) -> None:
    assert sorted(resp["sources"]) == sorted(
        [
            *("R-P02", "R-P03", "R-D01", "R-V05", "E-012"),  # calendar, money, seasons, gates
            *SHARE_IDS,
            *("R-W12", "R-A15", "E-020"),  # soil wetness
            *("E-010", "E-022"),  # NSO anomaly normal; engine arithmetic (D-158)
            *("R-W15", "R-M02"),  # water facts
            *("R-E13", "R-E12", "R-E06"),  # land-care principles
            *("R-G06", "R-G27", "R-C13"),  # risks
        ]
    )
    assert check_response(resp, None) == []


# ---- calendar


def test_calendar_spans_are_the_reported_dates_with_their_study(resp: dict) -> None:
    usual = plan(resp, "usual")
    assert usual["name"]["vi"] == "Lúa Khang dân - Đậu đen xanh lòng VT1 - Khoai lang Chiêm Dâu"
    assert usual["calendar"][0] == {  # rules/rotations.yaml usual (P-02 Table 9); crop name from rules/crops.yaml
        "crop_key": "usual_spring_rice",
        "crop_id": "rice",
        "crop": {"vi": "Lúa", "en": "Rice"},
        "variety": {"vi": "Khang dân", "en": "Khang dân"},
        "season": "spring",
        "sow_from": "01-17",
        "sow_to": "01-17",
        "harvest_from": "05-17",
        "harvest_to": "05-17",
        "source_ids": ["R-P02"],
    }
    assert [s["crop_key"] for s in usual["calendar"]] == [
        "usual_spring_rice",
        "usual_summer_autumn_black_bean",
        "usual_autumn_winter_sweet_potato",
    ]
    p03 = plan(resp, "usual_p03")
    assert [(s["crop_id"], s["sow_from"], s["source_ids"]) for s in p03["calendar"]] == [
        ("rice", None, ["R-P03"]),
        ("rice", None, ["R-P03"]),
    ]


def test_bare_periods_are_derived_from_the_spans(resp: dict) -> None:
    # usual: 01-17..05-17, 06-06..08-25, 08-15..12-10 leave 05-18..06-05 and 12-11..01-16 (over 31 December)
    assert plan(resp, "usual")["bare_periods"] == [{"from": "05-18", "to": "06-05"}, {"from": "12-11", "to": "01-16"}]
    assert plan(resp, "usual_p03")["bare_periods"] == []  # no dates reported in P-03


# ---- money


def test_money_items_are_the_reported_profit_and_cost_per_crop(resp: dict) -> None:
    money = plan(resp, "usual")["money"]
    assert [(i["crop_key"], i["profit"]["value"], i["cost"]["value"]) for i in money["items"]] == [
        ("usual_spring_rice", "5,149", "32,426"),  # P-02 Table 13 "Lãi thuần", Tables 4, 8, 12 "Tổng chi"
        ("usual_summer_autumn_black_bean", "16,200", "25,000"),
        ("usual_autumn_winter_sweet_potato", "9,450", "40,800"),
    ]
    first = money["items"][0]
    assert (first["crop"], first["season"]) == ({"vi": "Lúa", "en": "Rice"}, "spring")
    assert first["profit"] == {"value": "5,149", "unit": P02_UNIT, "source_ids": ["R-P02"]}
    assert first["flag"] is None
    assert money["items"][1]["flag"]["en"].startswith("In Table 4 of the paper, the CC1 mung bean row")
    assert money["price_year"] == "2020-21"
    assert money["definition"]["vi"] == (
        "lợi nhuận thuần (RVAC) = GR - TVC; TVC gồm vật tư, công lao động, năng lượng và lãi vay"
    )
    assert money["text_only"] is None


@pytest.mark.parametrize(
    ("plan_id", "total"),
    [  # sums of the P-02 Table 13 profits in rules/rotations.yaml
        ("usual", "30,799"),  # 5,149 + 16,200 + 9,450
        ("cc1", "53,380"),  # 25,980 + 16,200 + 11,200
        ("cc2", "53,665"),  # 21,100 + 16,700 + 15,865
        ("cc3", "55,360"),  # 12,420 + 12,500 + 30,440
        ("cc4", "58,765"),  # 18,925 + 19,450 + 20,390
    ],
)
def test_the_total_is_our_sum_of_the_profit_values(resp: dict, plan_id: str, total: str) -> None:
    assert plan(resp, plan_id)["money"]["total"] == {"value": total, "unit": P02_UNIT, "source_ids": ["R-P02", "E-022"]}


def test_p03_money_is_text_only_with_its_own_definition(resp: dict) -> None:
    money = plan(resp, "usual_p03")["money"]
    assert (money["items"], money["total"], money["price_year"]) == ([], None, "2020-21")
    assert money["definition"]["vi"] == "Lợi nhuận = GR - Tổng chi phí vật chất"
    assert money["text_only"]["vi"].startswith("Lúa vụ Đông Xuân 2021 (đối chứng): hiệu quả kinh tế 5,36 triệu đồng/ha")


def test_a_cost_the_source_does_not_report_is_null(root: Path) -> None:
    def drop_cost(plans: list[dict]) -> None:
        del plans[0]["reported_economics"]["cost_per_crop"]["usual_spring_rice"]

    edit_yaml(root, "rotations.yaml", drop_cost)
    money = plan(compare(request(), root).model_dump(by_alias=True), "usual")["money"]
    assert money["items"][0]["cost"] is None  # UI-UX-SPEC §11 MoneyItem.cost: null when the source reports none
    assert money["total"]["value"] == "30,799"  # the total sums the profit values only


def test_a_crop_without_a_profit_fails_naming_it(root: Path) -> None:
    def drop_profit(plans: list[dict]) -> None:
        del plans[0]["reported_economics"]["profit_per_crop"]["usual_spring_rice"]

    edit_yaml(root, "rotations.yaml", drop_profit)
    with pytest.raises(ValueError, match="usual_spring_rice"):
        compare(request(), root)


# ---- exposure


def test_exposure_per_picked_year_from_the_crop_rows_and_soil_wetness(resp: dict) -> None:
    exposure = plan(resp, "usual")["exposure"]
    assert [e["crop_key"] for e in exposure] == [s["crop_key"] for s in plan(resp, "usual")["calendar"]]
    rice = exposure[0]
    assert rice["crop"] == {"vi": "Lúa", "en": "Rice"}
    assert [row["year"] for row in rice["per_year"]] == YEARS
    assert rice["per_year"][0] == {
        "year": 1995,  # hazard_labels.json usual_spring_rice 1995: heat and cold 0.1733941621552288, the rest 0.0
        "shares": {
            "heavy_rain": pct("0", SHARE_IDS),
            "heat": pct("17", SHARE_IDS),
            "drought_rain_consecutive": pct("0", SHARE_IDS),
            "drought_rain_any2": pct("0", SHARE_IDS),
            "cold": pct("17", SHARE_IDS),
        },
        # soil_wetness.json usual_spring_rice 1995: value 0.6922447136548893, normal 0.6457472057197924
        "soil_wetness": {"value": pct("69", SOIL_IDS), "normal": pct("65", SOIL_IDS)},
    }
    year_2007 = rice["per_year"][1]  # heat 0.3692202130099066, cold 0.0; soil 0.6279554452044767
    assert (year_2007["shares"]["heat"]["value"], year_2007["shares"]["cold"]["value"]) == ("37", "0")
    assert year_2007["soil_wetness"]["value"]["value"] == "63"


def test_p03_has_no_exposure_and_every_p02_crop_has_one(resp: dict) -> None:
    assert plan(resp, "usual_p03")["exposure"] == []  # hazard_labels.json has no usual_p03 rows (P-03: no dates)
    for plan_id in ("cc1", "cc2", "cc3", "cc4"):
        assert len(plan(resp, plan_id)["exposure"]) == 3


def test_a_missing_soil_wetness_row_fails_naming_the_crop_and_year(root: Path) -> None:
    def drop(data: dict) -> None:
        data["rows"] = [r for r in data["rows"] if (r["crop_key"], r["year"]) != ("usual_spring_rice", 2007)]

    edit_json(root, "soil_wetness.json", drop)
    with pytest.raises(ValueError, match=r"usual_spring_rice.*2007"):
        compare(request(), root)


def test_a_null_soil_wetness_stays_null(root: Path) -> None:
    def null(data: dict) -> None:
        for r in data["rows"]:
            if (r["crop_key"], r["year"]) == ("usual_spring_rice", 1995):
                r["value"] = None

    edit_json(root, "soil_wetness.json", null)
    rice = plan(compare(request(), root).model_dump(by_alias=True), "usual")["exposure"][0]
    assert rice["per_year"][0]["soil_wetness"] == {"value": None, "normal": pct("65", SOIL_IDS)}


# ---- stability


def test_stability_only_for_rice_crops(resp: dict) -> None:
    for plan_id in ("cc1", "cc2", "cc3", "cc4"):
        assert plan(resp, plan_id)["stability"] is None  # UI-UX-SPEC §11: null = no rice in plan
    assert [s["crop_key"] for s in plan(resp, "usual")["stability"]] == ["usual_spring_rice"]
    assert [(s["season"], s["model_status"]) for s in plan(resp, "usual_p03")["stability"]] == [
        ("spring", "not_shown"),  # artifacts/risk_table.json seasons
        ("summer_autumn", "not_modeled"),
    ]


def test_stability_of_spring_rice_from_the_nso_anomalies(resp: dict) -> None:
    block = plan(resp, "usual")["stability"][0]
    # risk_table.json Nghe An spring rice: 1995 null, 2007 -0.0896..., 2013 -0.0442..., 2020 -1.1e-16
    assert block["label"] == {"vi": "Lúa, vụ Đông Xuân", "en": "Rice, spring season"}  # D-156, D-158
    assert block["scope"] == {
        "vi": "Trung bình của tỉnh; phần lớn là lúa có tưới",
        "en": "Province average; mostly irrigation-served rice",
    }  # rules/method.yaml
    assert [(r["year"], r["real"] and r["real"]["value"]) for r in block["per_year"]] == [
        (1995, None),
        (2007, "-9"),
        (2013, "-4"),
        (2020, "0"),
    ]
    assert block["per_year"][1]["real"] == pct("-9", REAL_IDS)
    assert all(r["oos_prediction"] is None and r["range_80"] is None for r in block["per_year"])  # not_shown
    assert block["years_count"] == 3
    ids = [*REAL_IDS, "E-022"]
    assert block["summary"] == {"min": pct("-9", ids), "median": pct("-4", ids), "max": pct("0", ids)}
    assert block["worst_years"] == [2007]


def test_summer_autumn_rice_worst_year(resp: dict) -> None:
    block = plan(resp, "usual_p03")["stability"][1]
    # risk_table.json Nghe An summer_autumn: 2007 0.0786..., 2013 0.0768..., 2020 0.00374...
    assert block["label"] == {"vi": "Lúa, vụ Hè Thu", "en": "Rice, summer-autumn season"}
    assert [v["value"] for v in block["summary"].values()] == ["0", "8", "8"]
    assert block["worst_years"] == [2020]


def test_the_median_of_an_even_count_is_rounded_once(real: Path) -> None:
    # D-156: 1998 0.07565789473684204 and 1999 0.09090909090909127 -> exact mean 0.08328... -> 8 (rounding first: 9)
    block = plan(compare(request([1998, 1999]), real).model_dump(by_alias=True), "usual")["stability"][0]
    assert [v["value"] for v in block["summary"].values()] == ["8", "8", "9"]


def test_no_summary_from_fewer_than_two_real_values(real: Path) -> None:
    block = plan(compare(request([1995, 2007]), real).model_dump(by_alias=True), "usual")["stability"][0]
    assert (block["years_count"], block["summary"], block["worst_years"]) == (1, None, [])  # D-95; 1995 has no normal


def show_spring(data: dict, passed_g4: bool = True) -> None:
    """risk_table.json with spring shown and placeholder predictions for 2010 (outside the test years) and 2016."""
    data["seasons"] = [{**s, "model_status": "shown"} if s["season"] == "spring" else s for s in data["seasons"]]
    for r in data["rows"]:
        if (r["unit_id"], r["season"]) == ("Nghe An", "spring") and r["year"] in (2010, 2016):
            r.update(anom_oos=0.0123, oos_low_80=-0.02, oos_high_80=0.0456, model_id="m1_ridge")
            r["anom_oos_source_ids"] = ["E-012"]


def test_a_prediction_only_in_test_years_and_its_range_only_where_g4_passed(root: Path) -> None:
    edit_json(root, "risk_table.json", show_spring)
    rows = plan(compare(request([2010, 2016]), root).model_dump(by_alias=True), "usual")["stability"][0]["per_year"]
    assert (rows[0]["oos_prediction"], rows[0]["range_80"]) == (None, None)  # 2010 is before test_years (D-82)
    assert rows[1]["oos_prediction"] == pct("1", ["E-012"])  # 0.0123 -> 1.23 -> 1
    assert rows[1]["range_80"] == {"low": pct("-2", ["E-012"]), "high": pct("5", ["E-012"])}  # gates.json G4 spring


def test_no_range_where_g4_failed(root: Path) -> None:
    edit_json(root, "risk_table.json", show_spring)

    def fail_g4(data: dict) -> None:
        for g in data["gates"]:
            if (g["gate"], g["season"]) == ("G4", "spring"):
                g["passed"] = False

    edit_json(root, "gates.json", fail_g4)
    row = plan(compare(request([2016]), root).model_dump(by_alias=True), "usual")["stability"][0]["per_year"][0]
    assert (row["oos_prediction"]["value"], row["range_80"]) == ("1", None)  # D-94


def test_a_missing_risk_row_fails_naming_the_season_and_year(root: Path) -> None:
    def drop(data: dict) -> None:
        data["rows"] = [
            r for r in data["rows"] if (r["unit_id"], r["season"], r["year"]) != ("Nghe An", "spring", 2007)
        ]

    edit_json(root, "risk_table.json", drop)
    with pytest.raises(ValueError, match=r"spring.*2007"):
        compare(request(), root)


# ---- water


def test_water_facts_come_from_crops_yaml_per_crop(resp: dict) -> None:
    water = plan(resp, "usual")["water"]
    rice = [w for w in water if w["crop_key"] == "usual_spring_rice"]
    assert rice[0] == {  # rules/crops.yaml rice, first TCVN 8641:2011 row
        "crop_key": "usual_spring_rice",
        "measure": "to_apply",
        "value": {"value": "6,500-7,500", "unit": {"vi": "m3/ha", "en": "m3/ha"}, "source_ids": ["R-W15"]},
        "scope": {"vi": "Trung bộ, lúa cấy, vụ xuân", "en": "Trung bộ, transplanted rice, spring season"},
        "note": {
            "vi": "Chỉ nước tưới dưỡng, không kể nước làm đất. Tiêu chuẩn không nói Nghệ An thuộc Trung bộ hay Bắc bộ.",
            "en": "Maintenance irrigation only, land preparation not included. The standard does not say whether "
            "Nghệ An belongs to Trung bộ or Bắc bộ.",
        },
    }
    # every fact of the crop id (05-DATA-CONTRACTS §6; D-68: all region rows, the standard does not place Nghệ An)
    assert [(w["measure"], w["value"]["value"]) for w in rice] == [
        ("to_apply", "6,500-7,500"),
        ("to_apply", "6,000-7,000"),
        ("to_apply", "6,500-7,500"),
        ("to_apply", "5,700-7,000"),
        ("to_apply", "6,000-7,000"),
        ("to_apply", "4,500-5,500"),
        ("crop_uses", "450-700"),
    ]
    assert rice[-1]["value"]["source_ids"] == ["R-M02"]
    assert [w for w in water if w["crop_key"] == "usual_summer_autumn_black_bean"] == [
        {  # black bean is listed in neither source: one not_listed fact (05-DATA-CONTRACTS §6)
            "crop_key": "usual_summer_autumn_black_bean",
            "measure": "not_listed",
            "value": None,
            "scope": None,
            "note": None,
        }
    ]
    sweet_potato = [w for w in water if w["crop_key"] == "usual_autumn_winter_sweet_potato"]
    assert [(w["measure"], w["value"]["value"], w["note"]) for w in sweet_potato] == [("to_apply", "1,200-1,400", None)]


def test_every_crop_of_every_plan_has_water_facts(resp: dict) -> None:
    for p in resp["plans"]:
        assert {w["crop_key"] for w in p["water"]} == {s["crop_key"] for s in p["calendar"]}, p["id"]


# ---- land care


CROPS_UNIT = {"vi": "loại cây", "en": "crops"}  # D-156
DAYS_UNIT = {"vi": "ngày", "en": "days"}  # D-156


def test_land_care_of_the_usual_plan(resp: dict) -> None:
    assert plan(resp, "usual")["land"] == {
        "crops_in_year": {  # rice, black bean, sweet potato
            "value": {"value": "3", "unit": CROPS_UNIT, "source_ids": ["R-P02", "E-022"]},
            "principle_source_ids": ["R-E13"],
        },
        "living_days": {  # 365 - 19 bare days (05-18..06-05) - 37 bare days (12-11..01-16)
            "value": {"value": "309", "unit": DAYS_UNIT, "source_ids": ["R-P02", "E-022"]},
            "principle_source_ids": ["R-E12"],
        },
        "legume": {  # rules/crops.yaml is_legume: black bean only
            "present": True,
            "crops": [{"vi": "Đậu đen xanh lòng", "en": "Black bean"}],
            "principle_source_ids": ["R-E06"],
        },
    }


def test_land_care_of_p03_and_cc4(resp: dict) -> None:
    p03 = plan(resp, "usual_p03")["land"]
    assert p03["crops_in_year"]["value"] == {"value": "1", "unit": CROPS_UNIT, "source_ids": ["R-P03", "E-022"]}
    assert p03["living_days"] == {"value": None, "principle_source_ids": ["R-E12"]}  # no dates in P-03
    assert (p03["legume"]["present"], p03["legume"]["crops"]) == (False, [])
    cc4 = plan(resp, "cc4")["land"]
    assert cc4["crops_in_year"]["value"]["value"] == "2"  # biomass maize twice, sweet potato
    assert cc4["living_days"]["value"]["value"] == "240"  # 79 (01-17..04-05) + 72 (06-10..08-20) + 89 (09-05..12-02)
    cc1 = plan(resp, "cc1")["land"]["legume"]
    assert cc1["crops"] == [{"vi": "Lạc", "en": "Peanut"}, {"vi": "Đậu xanh", "en": "Mung bean"}]


# ---- why and risks


def test_why_parts_and_risks_come_from_rotations_yaml(resp: dict) -> None:
    why = plan(resp, "usual_p03")["why"]
    # rules/rotations.yaml usual_p03 why (quoted from P-03 with page, team 2026-11-14)
    assert (
        why["evidence"]["en"] == "One year, June 2020 to June 2021; one unreplicated plot of 1000 m2 per crop (p. 2)."
    )
    assert why["benefits"]["en"] == "The paper states no benefit of this control structure."
    assert all(why[part]["vi"] and why[part]["en"] for part in WHY_PARTS)
    # cc1 risks: the P-02 cost line, the P-03 market fact, Decree 112/2024 Art. 6.1, 6.4 and 7.1
    risks = plan(resp, "cc1")["why"]["risks"]
    assert [r["source_ids"] for r in risks] == [["R-P02"], ["R-P03"], ["R-G06"], ["R-G06"], ["R-G27"]]
    assert risks[1]["text"]["en"].startswith("Another trial by the same team in the same commune")
    assert plan(resp, "usual")["why"]["risks"] == []


# ---- the rules files


def test_plans_out_of_order_fail_naming_the_file(root: Path) -> None:
    edit_yaml(root, "rotations.yaml", lambda plans: plans.reverse())
    with pytest.raises(ValueError, match=r"rotations\.yaml"):
        compare(request(), root)
