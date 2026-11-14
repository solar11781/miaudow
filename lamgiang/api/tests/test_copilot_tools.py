"""Phase-2 copilot tools and intents: strict registration, tool results with units and sources, fixed-sentence answers
whose every number passes the number check, and the Claude loop with the new tools (scripted client, no key)."""

import json
from types import SimpleNamespace

import pytest

from miaudow_api import copilot
from miaudow_api.contracts import CopilotRequest

NEW_TOOLS = {
    "get_climate_anomalies",
    "find_analog_years",
    "list_climate_anomaly_years",
    "get_satellite_vegetation",
    "get_data_provenance",
    "get_map_layer_metadata",
}
RANKING_WORDS = ("tốt nhất", "nên chọn", "xếp hạng", "best plan", "we recommend", "the best")


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("những năm nào ít mưa hơn bình thường", "dry_years"),
        ("Những năm nào ít mưa hơn bình thường?", "dry_years"),
        ("nhung nam nao it mua hon binh thuong", "dry_years"),
        ("Which years were drier than normal?", "dry_years"),
        ("năm nào giống năm 2010", "analogs"),
        ("Năm nào giống năm 2010?", "analogs"),
        ("Years like 2010?", "analogs"),
        ("tại sao bản đồ có màu vàng", "map_colour"),
        ("Why is the map yellow?", "map_colour"),
        # the earlier intents keep their meaning
        ("Năm 2010 có hạn không?", "year"),
        ("Năm 2010 có ít mưa hơn bình thường không?", "year"),
        ("Năm sau có ít mưa hơn bình thường không?", "forecast"),
        ("Ruộng thiếu nước nên trồng gì?", "plans"),
        ("NASA POWER là gì?", "evidence"),
    ],
)
def test_intent(question, expected):
    assert copilot.intent(question) == expected


def test_new_tools_are_registered_strict_and_runnable():
    by_name = {t["name"]: t for t in copilot.TOOLS}
    assert set(by_name) >= NEW_TOOLS
    for name in NEW_TOOLS:
        t = by_name[name]
        assert t["strict"] is True
        assert t["input_schema"]["additionalProperties"] is False
        assert set(t["input_schema"]["required"]) == set(t["input_schema"]["properties"])
    args = {
        "get_climate_anomalies": {"year": 2010},
        "find_analog_years": {"year": 2010, "k": 2},
        "list_climate_anomaly_years": {},
        "get_satellite_vegetation": {},
        "get_data_provenance": {"dataset_id": "chirps_v3_monthly"},
        "get_map_layer_metadata": {"layer_id": "s2-ndvi:spring-2024"},
    }
    for name, a in args.items():
        out = copilot._run_tool(name, a, "vi")
        json.dumps(out, ensure_ascii=False)  # JSON-serialisable for the model
        assert out


def test_tool_results_carry_units_sources_and_limits():
    an = copilot.tool_climate_anomalies(2010, "en")
    assert len(an["months"]) == 12 and an["units"] and len(an["sources"]) == 2
    assert an["months"][0]["power_anomaly_pct"] is not None and an["months"][0]["chirps_anomaly_pct"] is not None
    assert "not a forecast" in an["note"]
    ana = copilot.tool_find_analog_years(2010, 3, "vi")
    assert len(ana["analogs"]) == 3 and ana["evaluation"]["verdict"] and ana["limitations"]
    years = copilot.tool_list_anomaly_years("en")
    assert years["n_years"] == 34 and years["n_below_normal"] == sum(1 for y in years["years"] if y["below_normal"])
    veg = copilot.tool_satellite_vegetation("vi")
    assert veg["sentinel2"]["resolution_m"] == 20 and veg["modis"]["n_dates_without_valid_pixel"] == 35
    assert veg["comparability"] and veg["limitations"]
    prov = copilot.tool_data_provenance("nasa_power_daily", "vi")
    assert prov["is_field_measurement"] is False and prov["license"]
    lyr = copilot.tool_map_layer_metadata("gibs:MODIS_Terra_CorrectedReflectance_TrueColor", "en")
    assert lyr["kind"] == "visual" and lyr["legend"] == []


def test_unknown_ids_raise_value_errors_for_the_model():
    with pytest.raises(ValueError, match="unknown dataset"):
        copilot._run_tool("get_data_provenance", {"dataset_id": "nope"}, "vi")
    with pytest.raises(ValueError, match="unknown layer"):
        copilot._run_tool("get_map_layer_metadata", {"layer_id": "nope"}, "vi")
    with pytest.raises(ValueError):
        copilot._run_tool("find_analog_years", {"year": 1980, "k": 3}, "vi")


@pytest.mark.parametrize("lang", ["vi", "en"])
@pytest.mark.parametrize(
    ("question", "tool"),
    [
        ("những năm nào ít mưa hơn bình thường", "list_climate_anomaly_years"),
        ("which years were drier than normal", "list_climate_anomaly_years"),
        ("năm nào giống năm 2010", "find_analog_years"),
        ("years like 2010", "find_analog_years"),
        ("tại sao bản đồ có màu vàng", "get_map_layer_metadata"),
        ("why is the map yellow", "get_map_layer_metadata"),
    ],
)
def test_new_answers_are_grounded_and_pass_the_number_check(question, tool, lang):
    res = copilot.answer(CopilotRequest(question=question, lang=lang))
    assert res.engine == "deterministic" and res.status == "grounded"
    assert [t.tool for t in res.tool_trace] == [tool]
    assert res.numbers.checked > 0 and res.numbers.unverified == []
    low = res.answer.lower()
    assert not any(w in low for w in RANKING_WORDS)
    if tool != "get_map_layer_metadata":
        assert ("không phải dự báo" in low) if lang == "vi" else ("not a forecast" in low)


def test_dry_years_answer_lists_the_driest_years_from_the_tool():
    data = copilot.tool_list_anomaly_years("vi")
    driest = sorted((y for y in data["years"] if y["below_normal"]), key=lambda y: y["annual_rain_anomaly_pct"])[0]
    res = copilot.answer(CopilotRequest(question="những năm nào ít mưa hơn bình thường"))
    assert str(driest["year"]) in res.answer
    assert f"{data['n_below_normal']} trong {data['n_years']} năm" in res.answer


def test_analog_answer_names_the_tool_years_and_the_honest_evaluation():
    data = copilot.tool_find_analog_years(2010, 3, "en")
    res = copilot.answer(CopilotRequest(question="years like 2010", lang="en"))
    for a in data["analogs"]:
        assert str(a["year"]) in res.answer
    assert f"{data['evaluation']['analog_hit_rate_pct']}%" in res.answer
    assert "may be chance" in res.answer


def test_map_colour_answer_explains_the_legend_and_the_visual_rule():
    res = copilot.answer(CopilotRequest(question="tại sao bản đồ có màu vàng"))
    assert "0,4" in res.answer and "NDVI" in res.answer
    assert "không đọc số từ màu" in res.answer
    assert res.cards[0].ref_id.startswith("s2-ndvi:")


def test_analog_year_outside_the_data_abstains():
    res = copilot.answer(CopilotRequest(question="năm nào giống năm 1985"))
    assert res.status == "insufficient_evidence"
    assert res.answer.startswith("Chưa đủ dữ liệu để kết luận")


# ---- Claude tool loop with the new tools (scripted client)


def block(**kw):
    return SimpleNamespace(**kw)


def reply(stop, content):
    return SimpleNamespace(stop_reason=stop, content=content, _request_id="req_test")


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        return self.script.pop(0)


def final(answer: str, years=()):
    payload = {
        "status": "grounded",
        "answer": answer,
        "passage_ids": [],
        "plan_ids": [],
        "years": list(years),
        "missing_information": [],
    }
    return reply("end_turn", [block(type="text", text=json.dumps(payload, ensure_ascii=False))])


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5-5")


def analog_call():
    return reply("tool_use", [block(type="tool_use", id="t1", name="find_analog_years", input={"year": 2010, "k": 3})])


def test_claude_answer_from_the_analog_tool_is_kept(with_key):
    data = copilot.tool_find_analog_years(2010, 3, "vi")
    first = data["analogs"][0]
    text = f"Năm {first['year']} giống năm 2010 nhất (khoảng cách {str(first['distance']).replace('.', ',')}). Không phải dự báo."
    fake = FakeClient([analog_call(), final(text, years=[2010, first["year"]])])
    res = copilot.answer(CopilotRequest(question="năm nào giống năm 2010"), client_factory=lambda key: fake)
    assert res.engine == "claude" and res.numbers.unverified == []
    assert res.tool_trace[0].tool == "find_analog_years" and res.tool_trace[0].ok
    assert all(t.get("strict") for t in fake.calls[0]["tools"])
    assert {t["name"] for t in fake.calls[0]["tools"]} >= NEW_TOOLS


def test_claude_answer_with_an_invented_number_falls_back(with_key):
    fake = FakeClient([analog_call(), final("Năm 2007 giống năm 2010 tới 97%.")])
    res = copilot.answer(CopilotRequest(question="năm nào giống năm 2010"), client_factory=lambda key: fake)
    assert res.engine == "deterministic"
    assert "97" in res.numbers.unverified
    assert res.tool_trace[0].tool == "find_analog_years"


def test_unknown_layer_goes_back_to_the_model_as_an_error(with_key):
    script = [
        reply("tool_use", [block(type="tool_use", id="t1", name="get_map_layer_metadata", input={"layer_id": "x"})]),
        final("Chưa đủ dữ liệu để kết luận."),
    ]
    fake = FakeClient(script)
    copilot.answer(CopilotRequest(question="tại sao bản đồ có màu vàng"), client_factory=lambda key: fake)
    sent = fake.calls[1]["messages"][-1]["content"][0]
    assert sent["is_error"] is True and "unknown layer" in sent["content"]
