"""AI core 03: crop decision support. Lays out the six studied plans side by side; it never ranks, scores or sorts them.

The plans always come in the study's own order: usual (CC5 of P-02), usual_p03 (the P-03 control), cc1, cc2, cc3,
cc4. The farmer's priority never reorders them; it only adds notes about which facts relate to that priority.

Records per plan:
- reported profit and cost per crop: VERIFIED, copied from P-02 (Table 13; Tables 4, 8, 12), 2020-21 prices, one
  unreplicated trial, not expected income;
- year total, crops in the year, legume count, days with a crop in the field: DERIVED by the engine (method E-022);
- farmland share meeting each official rule per crop for the requested years: DERIVED from E-019 (hazards.json).

`compare` is pure (it only reads the canonical files) and returns a JSON-serialisable DecisionResult, so the copilot
can call it as a tool. Invalid input raises ValueError (the API answers 422).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from . import canonical
from .contracts import (
    CompareRequest,
    DecisionResult,
    Geometry,
    MetricRecord,
    PlanComparison,
    RiskLine,
    SeasonRow,
    Text,
    TimeWindow,
    Uncertainty,
)

STUDY_ORDER = ("usual", "usual_p03", "cc1", "cc2", "cc3", "cc4")
YEARS = range(1995, 2025)
TRIAL_WINDOW = TimeWindow(
    start=date(2020, 6, 1),
    end=date(2021, 6, 30),
    label=Text(vi="Thử nghiệm 6/2020 - 6/2021", en="Trial 2020-06 to 2021-06"),
)
STUDY_SITE = Geometry(
    type="study_site",
    description=Text(
        vi="Ô thử nghiệm ở xã Lưu Sơn, huyện Đô Lương, Nghệ An", en="Trial plots in Lưu Sơn, Đô Lương, Nghệ An"
    ),
)
NOT_INCOME = Text(
    vi="Kết quả năm 2020-21 của một thử nghiệm không lặp lại; không phải thu nhập dự kiến.",
    en="A 2020-21 result of one unreplicated trial; not expected income.",
)
NONE = Uncertainty(
    kind="qualitative",
    note=Text(
        vi="Bài báo không báo cáo sai số; mỗi cây chỉ có một ô thử.",
        en="The paper reports no error range; one plot per crop.",
    ),
)
WATER_VI = {
    "canal_end": "ruộng ở cuối kênh",
    "high_field": "ruộng cao, khó lấy nước",
    "reliable": "ruộng đủ nước tưới",
    "water_short": "ruộng hay thiếu nước",
}
WATER_EN = {
    "canal_end": "a field at the end of the canal",
    "high_field": "a high field that is hard to water",
    "reliable": "a field with reliable irrigation",
    "water_short": "a field that is often short of water",
}


def _plans() -> dict:
    data = canonical.load("rotations.generated.json")
    return {p["id"]: p for p in data["plans"]}, {c["crop_id"]: c for c in data["crops"]}


def validate(req: CompareRequest) -> tuple[list[str], list[int]]:
    """The plan ids in study order and the years; unknown plans or years outside 1995-2024 raise ValueError."""
    if req.plan_ids is not None:
        unknown = [p for p in req.plan_ids if p not in STUDY_ORDER]
        if unknown:
            raise ValueError(f"unknown plan ids {unknown}; known: {list(STUDY_ORDER)}")
        if not req.plan_ids:
            raise ValueError("plan_ids is empty")
    plan_ids = [p for p in STUDY_ORDER if req.plan_ids is None or p in req.plan_ids]
    years = list(dict.fromkeys(req.years)) if req.years is not None else []
    bad = [y for y in years if y not in YEARS]
    if bad:
        raise ValueError(f"years {bad} outside 1995-2024")
    if req.years is not None and not years:
        raise ValueError("years is empty")
    return plan_ids, sorted(years)


def _record(
    metric_id,
    value,
    unit,
    status,
    method_id,
    source_id,
    transformation_id,
    dataset_id="study_p02",
    window=TRIAL_WINDOW,
    geometry=STUDY_SITE,
    limitations=(),
    source_url=None,
) -> MetricRecord:
    return MetricRecord(
        metric_id=metric_id,
        dataset_id=dataset_id,
        source_id=source_id,
        source_url=source_url,
        source_revision=None,
        retrieved_at=None,
        value=value,
        unit=unit,
        time_window=window,
        geometry=geometry,
        spatial_resolution="one 1,000 m2 plot per crop" if geometry.type == "study_site" else "0.5° x 0.625° grid",
        method_id=method_id,
        transformation_id=transformation_id,
        quality_flag="OK" if value is not None else "MISSING",
        missing_policy="A value the source does not give stays null.",
        uncertainty=NONE,
        validation_status=status if value is not None else "UNAVAILABLE",
        is_forecast=False,
        is_field_measurement=geometry.type == "study_site" and status == "VERIFIED",
        limitations=list(limitations),
    )


def living_days(seasons: list[dict]) -> int | None:
    """Days with a crop in the field: sowing to the last reported harvest of each season, overlaps counted once.

    Dates are month-day; 2021 (not a leap year, the year of the trial's spring season) is the reference calendar.
    None when a season has no dates (P-03 reports durations only).
    """
    days: set[date] = set()
    for s in seasons:
        if not s.get("sow_from") or not s.get("harvest_to"):
            return None
        a = date(2021, int(s["sow_from"][:2]), int(s["sow_from"][3:]))
        b = date(2021, int(s["harvest_to"][:2]), int(s["harvest_to"][3:]))
        days.update(a + timedelta(days=i) for i in range((b - a).days + 1))
    return len(days)


def _money_records(p: dict) -> list[MetricRecord]:
    econ = p["reported_economics"]
    out = []
    for row in econ["per_crop"]:
        k = row["crop_key"]
        flag = [Text(**row["flag"])] if row.get("flag") else []
        out.append(
            _record(
                "reported_profit",
                float(row["profit_value"]),
                "thousand VND/ha",
                "VERIFIED",
                "study_table_copy",
                econ["source_id"],
                f"R-P02 {row['profit_location']}; crop_key={k}",
                limitations=[NOT_INCOME, *flag],
            )
        )
        out.append(
            _record(
                "reported_cost",
                float(row["cost_value"]),
                "thousand VND/ha",
                "VERIFIED",
                "study_table_copy",
                econ["source_id"],
                f"R-P02 {row['cost_location']}; crop_key={k}",
                limitations=[NOT_INCOME, *flag],
            )
        )
    if econ["per_crop"]:
        total = float(sum(r["profit_value"] for r in econ["per_crop"]))
        inputs = ", ".join(f"{r['crop_key']}={r['profit']}" for r in econ["per_crop"])
        out.append(
            _record(
                "year_profit_total",
                total,
                "thousand VND/ha",
                "DERIVED",
                "E-022",
                "E-022",
                f"sum of reported_profit ({inputs}); inputs: R-P02 Table 13",
                limitations=[
                    NOT_INCOME,
                    Text(
                        vi="Phép cộng của ứng dụng; bài báo không nói cả cơ cấu được trồng liền trên một ruộng.",
                        en="The app's sum; the paper does not say one field carried the whole plan.",
                    ),
                ],
            )
        )
    return out


def _count_records(p: dict, crops: dict) -> list[MetricRecord]:
    seasons = p["seasons"]
    legumes = sum(1 for s in seasons if crops[s["crop_id"]]["is_legume"])
    days = living_days(seasons)
    no_dates = [
        Text(
            vi="Bài báo thứ hai không ghi ngày gieo và ngày thu hoạch.",
            en="The second paper gives no sowing or harvest dates.",
        )
    ]
    return [
        _record(
            "crops_in_year",
            float(len(seasons)),
            "crops",
            "DERIVED",
            "E-022",
            p["source_ids"][0],
            f"count of seasons with a crop in rotations.generated.json plan {p['id']}",
            limitations=[Text(vi="Không nói gì về đất tốt lên.", en="Says nothing about soil improvement.")],
        ),
        _record(
            "legume_count",
            float(legumes),
            "crops",
            "DERIVED",
            "E-022",
            "R-B01",
            f"count of seasons whose crop is in Fabaceae (GRIN-Global) in plan {p['id']}",
            source_url="https://npgsweb.ars-grin.gov/gringlobal/taxon/taxonomydetail?id=41629",
            limitations=[
                Text(
                    vi="Nguồn chỉ cho biết họ thực vật, không nói cây cố định bao nhiêu đạm.",
                    en="The source gives the plant family only, not how much nitrogen is fixed.",
                )
            ],
        ),
        _record(
            "living_days",
            None if days is None else float(days),
            "days",
            "DERIVED",
            "E-022",
            p["source_ids"][0],
            f"union of sow_from..harvest_to per season of plan {p['id']} (2021 calendar)",
            limitations=no_dates
            if days is None
            else [
                Text(
                    vi="Ngày gieo và thu hoạch chồng nhau được tính một lần.", en="Overlapping days are counted once."
                ),
                Text(
                    vi="Bài báo không nói các vụ được trồng liền trên một ruộng.",
                    en="The paper does not say the seasons followed each other on one field.",
                ),
            ],
        ),
    ]


RULE_ARTICLE = {
    "heavy_rain": "Điều 44.1",
    "heat": "Điều 47.1",
    "drought_rain_consecutive": "Điều 48.1",
    "drought_rain_any2": "Điều 48.1",
    "cold": "Điều 53.1 a, d",
}


def _hazard_records(p: dict, years: list[int]) -> list[MetricRecord]:
    """Per crop and rule: the farmland share meeting the rule in each requested year (E-019, hazards.json)."""
    if not years:
        return []
    hz = canonical.load("hazards.json")
    farmland = Geometry(
        type="farmland_weighted_area",
        cell_ids=[c["id"] for c in hz["cells"]],
        description=Text(
            vi="Đất trồng trọt của Nghệ An (5 ô lưới NASA POWER)", en="Nghệ An farmland (5 NASA POWER cells)"
        ),
    )
    out = []
    for s in p["seasons"]:
        if s["crop_key"] not in canonical.TEAM_TO_WEB:
            continue  # P-03 seasons have no dates, so no field time and no rule reading
        key = canonical.TEAM_TO_WEB[s["crop_key"]]
        sow, harvest = hz["crops"][key]["sow"], hz["crops"][key]["harvest"]
        for y in years:
            i = hz["years"].index(y)
            window = TimeWindow(
                start=date(y, int(sow[:2]), int(sow[3:])),
                end=date(y, int(harvest[:2]), int(harvest[3:])),
                label=Text(vi=f"{s['crop_name']['vi']}, năm {y}", en=f"{s['crop_name']['en']}, {y}"),
            )
            for r in hz["rules"]:
                out.append(
                    _record(
                        f"hazard_share_{r}",
                        hz["crop_level"][key][r][i],
                        "share of farmland (0-1)",
                        "DERIVED",
                        "E-019",
                        "E-019",
                        f"hazards.json:crop_level.{key}.{r}[{i}] (crop_key={s['crop_key']})",
                        dataset_id="e019_hazard_labels",
                        window=window,
                        geometry=farmland,
                        limitations=[
                            Text(
                                vi=f"Quy tắc {RULE_ARTICLE[r]} của Quyết định 18/2021, cấp độ 1 trở lên, áp cho giá trị "
                                "ô lưới NASA POWER; không phải ghi nhận chính thức.",
                                en=f"Decision 18/2021 rule {r}, level 1 or higher, applied to NASA POWER grid values; not an "
                                "official record.",
                            ),
                            Text(vi="Năm đã qua không phải dự báo.", en="A past year is not a forecast."),
                        ],
                    )
                )
    return out


def applicability(p: dict, water: str | None) -> Text:
    """The study's land type in its own words next to the farmer's answer. Never claims a match the study did not test."""
    land = p["study_land_type"]
    # D-160: user-facing text names the studies by first author and year, not by the team's ids
    who = {
        "R-P02": "Trịnh Đức Toàn và cs. (2023, Tạp chí KH&CN Nông nghiệp VN)",
        "R-P03": "Trịnh Đức Toàn và cs. (2023, Đặc san KH&CN Nghệ An)",
    }.get(land["source_id"], land["source_id"])
    who_en = {
        "R-P02": "Trịnh Đức Toàn et al. (2023, Vietnam J. Agric. Sci. Technol.)",
        "R-P03": "Trịnh Đức Toàn et al. (2023, Nghệ An S&T special issue)",
    }.get(land["source_id"], land["source_id"])
    where = re.sub(r"\s*\((tr\.|p\.) (\d+)\)", r", \1 \2", str(land["location"]).replace("Tên bài báo", "tên bài báo"))
    study = f'Nghiên cứu của {who} thử trên "{land["quote"]}" ở {p["site"]} ({where}).'
    study_en = f'The study by {who_en} was run on "{land["quote"]}" (its own words) in {p["site"]} ({where}).'
    if water is None:
        return Text(
            vi=f"{study} Bạn chưa cho biết ruộng của mình lấy nước thế nào, nên chưa thể so.",
            en=f"{study_en} You have not said how your field gets water, so no comparison is made.",
        )
    if water == "reliable":
        return Text(
            vi=f"{study} Bạn chọn: {WATER_VI[water]}. Nghiên cứu không thử trên ruộng đủ nước, nên không biết kết quả "
            "có giống trên ruộng của bạn hay không.",
            en=f"{study_en} You chose: {WATER_EN[water]}. The study did not test fields with reliable water, so it is not "
            "known whether the results hold on your field.",
        )
    return Text(
        vi=f"{study} Bạn chọn: {WATER_VI[water]}. Nghiên cứu không kiểm tra riêng loại ruộng này và chỉ có một ô thử "
        "ở một xã, nên chưa biết ruộng của bạn có giống ruộng thử hay không.",
        en=f"{study_en} You chose: {WATER_EN[water]}. The study did not test this kind of field separately and has one "
        "plot in one commune, so it is not known whether your field is like the trial field.",
    )


def questions_for_officer(p: dict) -> list[Text]:
    """Questions generated from the plan's own risk lines and limitations, one per distinct point."""
    out: list[Text] = []
    names_vi = ", ".join(s["crop_name"]["vi"].lower() for s in p["seasons"])
    names_en = ", ".join(s["crop_name"]["en"].lower() for s in p["seasons"])
    for line in p["risk_lines"]:
        sid, loc = line["source_id"], line["location"]
        if sid == "R-P02":
            out.append(
                Text(
                    vi=f"Năm nay ở xã mình, trồng {names_vi} tốn bao nhiêu tiền mỗi sào, và tôi có vay được vốn "
                    "không? (Bài báo của Trịnh Đức Toàn và cs. (2023) ghi chi phí trồng lạc và ớt có thể gấp 2-3 lần trồng lúa, tr. 48.)",
                    en=f"This year in my commune, what does growing {names_en} cost, and can I borrow the money? "
                    "(Trịnh Đức Toàn et al. 2023 say peanut and chili can cost 2-3 times as much as rice, p. 48.)",
                )
            )
        elif sid == "R-P03":
            out.append(
                Text(
                    vi=f"Ở xã mình ai mua {names_vi}, mua giá bao nhiêu? (Bài báo thứ hai của cùng nhóm tác giả (2023) ghi đậu tương, vừng khó "
                    "bán ở địa phương.)",
                    en=f"Who buys {names_en} in my commune, and at what price? (the second paper by the same team says soybean and sesame are "
                    "hard to sell locally.)",
                )
            )
        elif sid == "R-C13":
            out.append(
                Text(
                    vi="Có đơn vị nào ký hợp đồng thu mua ngô sinh khối ở xã mình không? (Lãnh đạo tỉnh nói vùng "
                    "trồng ngô sinh khối phải có hợp đồng thu mua, VietNamNet 31/08/2020.)",
                    en="Is there a buyer who signs purchase contracts for biomass maize in my commune? (The province "
                    "leadership said biomass maize areas must have purchase contracts, VietNamNet 2020-08-31.)",
                )
            )
        elif sid == "R-G06" and loc.startswith("Điều 6, khoản 1"):
            out.append(
                Text(
                    vi="Ruộng nhà tôi có nằm trong vùng quy hoạch trồng lúa năng suất, chất lượng cao không? Nếu có "
                    "thì không được chuyển đổi (Nghị định 112/2024, Điều 6, khoản 1).",
                    en="Is my field inside an area planned for high-yield, high-quality rice? If so, it may not be "
                    "converted (Decree 112/2024, Art. 6.1).",
                )
            )
        elif sid == "R-G27":
            out.append(
                Text(
                    vi="Kế hoạch chuyển đổi cơ cấu cây trồng trên đất lúa của tỉnh năm tới có cho trồng các cây "
                    "này trên ruộng nhà tôi không? (Nghị định 112/2024, Điều 7, khoản 1.)",
                    en="Does the province's plan for converting crops on rice land next year allow these crops on my "
                    "field? (Decree 112/2024, Art. 7.1.)",
                )
            )
    texts = " ".join(x["vi"] for x in p["limitations"])
    out.append(
        Text(
            vi="Đất và nguồn nước ruộng nhà tôi có giống ruộng thử ở Lưu Sơn, Đô Lương không?",
            en="Are the soil and water of my field like the trial field in Lưu Sơn, Đô Lương?",
        )
    )
    if "sớm hơn ngày thu hoạch" in texts:
        out.append(
            Text(
                vi="Ở xã mình nên gieo mỗi vụ vào lúc nào để vụ sau không phải gieo trước khi thu hoạch vụ trước?",
                en="When should each season be sown in my commune so that the next crop is not sown before the "
                "last one is harvested?",
            )
        )
    if "chi phí vật chất" in texts:
        out.append(
            Text(
                vi="Công lao động ở xã mình mỗi vụ là bao nhiêu? (Lợi nhuận trong bài báo thứ hai chưa trừ công lao động.)",
                en="What does labour cost per season in my commune? (The second paper's profit may leave out labour.)",
            )
        )
    return list({t.vi: t for t in out}.values())


MISSING_INFORMATION = [
    Text(vi="Giá bán và giá vật tư ở xã bạn năm nay.", en="This year's selling and input prices in your commune."),
    Text(
        vi="Lịch tưới và lượng nước thật sự về ruộng của bạn.",
        en="The irrigation schedule and the water that actually reaches your field.",
    ),
    Text(vi="Kết quả phân tích đất ruộng của bạn.", en="A soil test of your field."),
    Text(vi="Số người làm và tiền công trong nhà bạn.", en="The labour your household has and its cost."),
    Text(vi="Hợp đồng bao tiêu hoặc người mua chắc chắn.", en="Purchase contracts or a sure buyer."),
    Text(
        vi="Thời tiết của năm tới: ứng dụng chỉ có các năm đã qua.",
        en="Next year's weather: the app only has past years.",
    ),
]


def priority_notes(priority: str | None) -> list[Text]:
    """Which facts relate to the farmer's priority. It never changes the order of the plans."""
    common = Text(
        vi="Các phương án luôn theo thứ tự của nghiên cứu, không xếp hạng.",
        en="Plans always follow the study order; they are not ranked.",
    )
    notes = {
        "income": Text(
            vi="Về tiền: xem lãi thuần và tổng chi từng vụ (Bảng 13; Bảng 4, 8, 12 trong bài báo của Trịnh Đức Toàn và cs., 2023). Đó là kết quả "
            "năm 2020-21 của một ô thử, không phải thu nhập dự kiến; giá năm nay có thể khác.",
            en="On money: see each season's net profit and total cost (Trịnh Đức Toàn et al. 2023, Table 13; Tables 4, 8, 12). They are "
            "2020-21 results of one plot, not expected income; this year's prices may differ.",
        ),
        "stability": Text(
            vi="Về sự ổn định: xem phần đất trồng đạt từng quy tắc thời tiết trong các năm bạn chọn (E-019). "
            "Năm đã qua không phải dự báo.",
            en="On stability: see the farmland share meeting each weather rule in the years you chose "
            "(E-019). A past year is not a forecast.",
        ),
        "water": Text(
            vi="Về nước: TCVN 8641:2011 ghi lượng nước phải tưới, FAO ghi lượng nước cây dùng; hai nguồn đo hai "
            "thứ khác nhau, không so với nhau. Nhiều cây (đậu xanh, đậu đen, vừng, ớt, bí đỏ, ngô sinh khối) "
            "không có trong hai nguồn này.",
            en="On water: TCVN 8641:2011 gives water to apply, FAO gives crop water need; they measure different "
            "things and are never compared. Several crops (mung bean, black bean, sesame, chili, pumpkin, "
            "biomass maize) are listed in neither.",
        ),
        "soil": Text(
            vi="Về đất: xem số cây họ đậu trong năm (GRIN-Global). Nguồn chỉ cho biết họ thực vật, không đo đất "
            "ở Nghệ An.",
            en="On soil: see the number of legume crops in the year (GRIN-Global). The source gives the plant "
            "family only; no soil was measured in Nghệ An.",
        ),
    }
    return [common] if priority is None else [notes[priority], common]


def compare(req: CompareRequest) -> DecisionResult:
    """Tool: the requested plans side by side in study order, with sourced records, risks and open questions."""
    plan_ids, years = validate(req)
    plans, crops = _plans()
    out = []
    notes = priority_notes(req.priority)
    for pid in plan_ids:
        p = plans[pid]
        seasons = [
            SeasonRow(
                crop_key=s["crop_key"],
                crop_id=s["crop_id"],
                crop_name=Text(**s["crop_name"]),
                variety=s["variety"],
                season=s["season"],
                sow=s["sow_from"],
                harvest=s["harvest_to"],
            )
            for s in p["seasons"]
        ]
        records = _money_records(p) + _count_records(p, crops) + _hazard_records(p, years)
        out.append(
            PlanComparison(
                plan_id=pid,
                name=Text(**p["name"]),
                is_usual=p["is_usual"],
                site=p["site"],
                trial_period=p["trial_period"],
                seasons=seasons,
                records=records,
                risk_lines=[
                    RiskLine(text=Text(**r["text"]), source_id=r["source_id"], location=r["location"], quote=r["quote"])
                    for r in p["risk_lines"]
                ],
                limitations=[Text(**x) for x in p["limitations"]],
                applicability=applicability(p, req.water),
                questions_for_officer=questions_for_officer(p),
            )
        )
        text_only = p["reported_economics"].get("text_only")
        if text_only:
            notes.append(
                Text(
                    vi=f"{p['name']['vi']} (bài báo thứ hai, {text_only['location']}): {text_only['vi']}",
                    en=f"{p['name']['en']} (second paper, p. 3): {text_only['en']}",
                )
            )
    if not years:
        notes.append(
            Text(
                vi="Chọn một vài năm (1995-2024) để xem phần đất trồng đạt từng quy tắc thời tiết khi mỗi cây ở "
                "ngoài ruộng.",
                en="Choose some years (1995-2024) to see the farmland share meeting each weather rule while each "
                "crop was in the field.",
            )
        )
    return DecisionResult(request=req, plans=out, missing_information=MISSING_INFORMATION, notes=notes)


def plans() -> list[dict]:
    """Tool: the six plans as the rulebook gives them (study order), without records."""
    data, _ = _plans()
    return [
        {
            "plan_id": pid,
            "study_code": data[pid]["study_code"],
            "name": data[pid]["name"],
            "is_usual": data[pid]["is_usual"],
            "site": data[pid]["site"],
            "trial_period": data[pid]["trial_period"],
            "source_ids": data[pid]["source_ids"],
            "seasons": data[pid]["seasons"],
        }
        for pid in STUDY_ORDER
    ]
