"""POST /api/compare content (UI-UX-SPEC §9, §11 CompareResponse; 05-DATA-CONTRACTS §10; 04-TECH-DESIGN §4).

Plans from rules/rotations.yaml in the canonical order, crop names, legume flags and water facts from rules/crops.yaml,
exposure from the `crop` rows of artifacts/hazard_labels.json and artifacts/soil_wetness.json, rice stability from
artifacts/risk_table.json and gates.json, season labels and windows from rules/method.yaml and rules/calendar.yaml,
source facts from rules/sources.yaml for every id used. `land` and `priority` are echoed and change nothing else
(D-56 c, D-57).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fieldshift.engine.bare_periods import bare_periods, living_days
from fieldshift.engine.rules import (
    HAZARD_LABELS,
    SOIL_WETNESS,
    CalendarFile,
    CardTexts,
    CropEntry,
    HazardRow,
    PlanEntry,
    SeasonLabel,
    SoilRow,
    gate_rows,
    hazard_rows,
    load_calendar,
    load_card_texts,
    load_crops,
    load_plans,
    load_rules,
    load_sources,
    load_test_years,
    pick_sources,
    risk_rows,
    risk_seasons,
    soil_rows,
)
from fieldshift.engine.schemas import (
    RULE_CODES,
    SEASON_CODES,
    CompareRequest,
    CompareResponse,
    CropExposure,
    CropSpan,
    ExposureYear,
    LandCare,
    LandCheck,
    Legume,
    Money,
    MoneyItem,
    Plan,
    Province,
    Season,
    SeasonCode,
    SoilWetness,
    SourceId,
    Text,
    Value,
    WaterFact,
    Why,
    source_ids_in,
)
from fieldshift.engine.stability import RICE, RiceHistory, rice_history, stability
from fieldshift.engine.values import ENGINE_ID, percent_value, share_value

CALENDAR_REGIONS: dict[Province, str] = {"nghe_an": "north_central"}  # Nghệ An's NSO calendar region (D-38, D-156)
NSO_SEASONS: dict[SeasonCode, str] = {"spring": "spring", "summer_autumn": "autumn", "winter": "winter"}  # §11
MONTHS_EN = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
CROPS_UNIT: Text = {"vi": "loại cây", "en": "crops"}  # LandCare.crops_in_year unit (D-156)
DAYS_UNIT: Text = {"vi": "ngày", "en": "days"}  # LandCare.living_days unit (D-156)
# land-care principle sources (05-DATA-CONTRACTS §7; D-56 b, D-66): FAO Conservation Agriculture, NRCS Soil Health,
# Witcombe and Tiemann 2022
CROPS_PRINCIPLE, LIVING_PRINCIPLE, LEGUME_PRINCIPLE = ["R-E13"], ["R-E12"], ["R-E06"]
AMOUNT = re.compile(r"^\d{1,3}(,\d{3})*$")  # a whole amount with the digit grouping of rules/rotations.yaml (§6)

CropRows = dict[tuple[str | None, int], dict[str, Value | None]]  # (crop key, year) -> rule code -> share


@dataclass(frozen=True)
class Inputs:
    """What every plan card is built from: the rules files and artifacts read once, and the picked years."""

    crops: dict[str, CropEntry]
    texts: CardTexts
    years: list[int]
    shares: CropRows
    soil: dict[tuple[str, int], SoilRow]
    history: RiceHistory


def compare(request: CompareRequest, root: Path) -> CompareResponse:
    texts = load_card_texts(root)
    gates = gate_rows(root)
    years = load_test_years(root)
    crop_rows = [row for row in hazard_rows(root) if row.level == "crop"]
    history = rice_history(request.province, risk_rows(root), risk_seasons(root), gates, years, texts.stability_scope)
    inputs = Inputs(load_crops(root), texts, request.years, _shares(crop_rows), _soil(soil_rows(root)), history)
    built = [_plan(plan, inputs) for plan in load_plans(root)]
    used = sorted({span.season for p in built for span in p.calendar}, key=SEASON_CODES.index)
    calendar = load_calendar(root)
    seasons = [_season(code, texts, calendar, request.province) for code in used]
    rules = load_rules(root)
    stability_seasons = {block.season for p in built for block in p.stability or []}
    shown_gates = [g for g in gates if g.season in stability_seasons]
    ids = source_ids_in([item.model_dump() for item in (*seasons, *rules, *shown_gates, *built)])
    return CompareResponse(
        request=request,
        test_years=years,
        n_cells=_n_cells(crop_rows),
        seasons=seasons,
        rules=rules,
        gates=shown_gates,
        plans=built,
        sources=pick_sources(load_sources(root), ids),
    )


def _n_cells(rows: list[HazardRow]) -> int:
    cells = {row.n_cells for row in rows}
    if len(cells) != 1:
        raise ValueError(f"artifacts/{HAZARD_LABELS}: crop rows disagree on n_cells: {sorted(cells)}")
    return cells.pop()


def _shares(rows: list[HazardRow]) -> CropRows:
    found: CropRows = {}
    for row in rows:
        year_shares = found.setdefault((row.crop_key, row.year), {})
        if row.rule in year_shares:
            raise ValueError(f"artifacts/{HAZARD_LABELS}: {row.crop_key} {row.year} has two {row.rule} rows")
        year_shares[row.rule] = share_value(row)
    return found


def _soil(rows: list[SoilRow]) -> dict[tuple[str, int], SoilRow]:
    found: dict[tuple[str, int], SoilRow] = {}
    for row in rows:
        if (row.crop_key, row.year) in found:
            raise ValueError(f"artifacts/{SOIL_WETNESS}: two rows for {row.crop_key} {row.year}")
        found[(row.crop_key, row.year)] = row
    return found


def _season(code: SeasonCode, texts: CardTexts, calendar: CalendarFile, province: Province) -> Season:
    """Label from rules/method.yaml; window from the NSO calendar of the province's region, or for a season that is
    not an NSO rice season from rules/calendar.yaml `trial_windows` (D-156, D-158)."""
    label = _season_label(texts, code)
    region = CALENDAR_REGIONS[province]
    if code in NSO_SEASONS:
        found = [w for w in calendar.ml_windows if (w.nso_season, w.calendar_region) == (NSO_SEASONS[code], region)]
        if len(found) != 1:
            raise ValueError(f"rules/calendar.yaml: {len(found)} ml_windows for {NSO_SEASONS[code]} {region}")
        (start, start_offset), (end, end_offset) = found[0].start, found[0].end
        if start_offset or end_offset:
            raise ValueError(f"rules/calendar.yaml: no window text for a year offset ({code} {region})")
        window: Text = {"vi": f"tháng {start} - tháng {end}", "en": f"{MONTHS_EN[start - 1]} - {MONTHS_EN[end - 1]}"}
        window_ids = found[0].source_ids
    else:
        trial = [w for w in calendar.trial_windows if w.season == code]
        if len(trial) != 1:
            raise ValueError(f"rules/calendar.yaml: {len(trial)} trial_windows for {code}")
        window, window_ids = trial[0].window, trial[0].source_ids
    return Season(
        code=code,
        label=label.label,
        window=window,
        source_ids=list(dict.fromkeys([*label.source_ids, *window_ids])),
    )


def _season_label(texts: CardTexts, code: SeasonCode) -> SeasonLabel:
    if code not in texts.season_labels:
        raise ValueError(f"rules/method.yaml: no season label for {code}")
    return texts.season_labels[code]


def _crop(crops: dict[str, CropEntry], crop_id: str) -> CropEntry:
    if crop_id not in crops:
        raise ValueError(f"rules/crops.yaml: no entry for crop id {crop_id}")
    return crops[crop_id]


def _plan(plan: PlanEntry, inputs: Inputs) -> Plan:
    calendar = [
        CropSpan(**span.model_dump(), crop=_crop(inputs.crops, span.crop_id).name, source_ids=plan.source_ids)
        for span in plan.seasons
    ]
    rice = [span for span in calendar if span.crop_id == RICE]
    years = inputs.years
    return Plan(
        id=plan.id,
        name=plan.name,
        is_usual=plan.is_usual,
        calendar=calendar,
        bare_periods=bare_periods(calendar),
        money=_money(plan, calendar),
        exposure=_exposure(calendar, years, inputs.shares, inputs.soil),
        stability=[stability(s, _stability_label(s, inputs.texts), years, inputs.history) for s in rice] or None,
        water=_water(calendar, inputs.crops),
        land=_land(plan, calendar, inputs.crops),
        why=Why(**plan.why.model_dump(), risks=plan.risks),
    )


def _stability_label(span: CropSpan, texts: CardTexts) -> Text:
    """The crop name and the season label, "Lúa, vụ Đông Xuân" / "Rice, spring season" (D-156, D-158)."""
    season = _season_label(texts, span.season).label
    return {lang: f"{span.crop[lang]}, {season[lang][:1].lower()}{season[lang][1:]}" for lang in ("vi", "en")}


def _amount(text: str, where: str) -> int:
    if not AMOUNT.match(text):
        raise ValueError(f"rules/rotations.yaml: {where}: {text!r} is not a whole amount like '16,200'")
    return int(text.replace(",", ""))


def _money(plan: PlanEntry, calendar: list[CropSpan]) -> Money:
    """Money as the study reports it per crop; the total is our sum of the profit values (05-DATA-CONTRACTS §7)."""
    econ = plan.reported_economics
    keys = [span.crop_key for span in calendar]
    named = (("profit_per_crop", econ.profit_per_crop.keys()), ("cost_per_crop", econ.cost_per_crop.keys()))
    for field, crop_keys in (*named, ("flags", econ.flags.keys())):
        unknown = sorted(set(crop_keys) - set(keys))
        if unknown:
            raise ValueError(f"rules/rotations.yaml: {plan.id} {field} names crops not in the plan: {unknown}")
    items: list[MoneyItem] = []
    if econ.profit_per_crop:  # P-03 reports money as text only (§7)
        missing = [key for key in keys if key not in econ.profit_per_crop]
        if missing or econ.unit is None:
            raise ValueError(f"rules/rotations.yaml: {plan.id} needs a unit and a profit for every crop: {missing}")
        unit, ids = econ.unit, [econ.source_id]
        for span in calendar:
            cost = econ.cost_per_crop.get(span.crop_key)
            items.append(
                MoneyItem(
                    crop_key=span.crop_key,
                    crop=span.crop,
                    season=span.season,
                    profit=Value(value=econ.profit_per_crop[span.crop_key], unit=unit, source_ids=ids),
                    cost=None if cost is None else Value(value=cost, unit=unit, source_ids=ids),
                    flag=econ.flags.get(span.crop_key),
                )
            )
    total = None
    if items:
        amount = sum(_amount(i.profit.value, f"{plan.id} {i.crop_key} profit") for i in items)
        total = Value(value=f"{amount:,}", unit=items[0].profit.unit, source_ids=[econ.source_id, ENGINE_ID])
    return Money(
        items=items,
        total=total,
        price_year=econ.price_year,
        definition=econ.definition,
        text_only=econ.text_only,
    )


def _exposure(
    calendar: list[CropSpan], years: list[int], shares: CropRows, soil: dict[tuple[str, int], SoilRow]
) -> list[CropExposure]:
    """Per crop with field dates and per picked year: the five rule shares and the soil wetness (§4b, §4d)."""
    exposure = []
    for span in calendar:
        if span.sow_from is None:
            continue  # P-03 reports no dates, so nothing was counted (§4b)
        per_year = []
        for year in years:
            year_shares = shares.get((span.crop_key, year), {})
            missing = [code for code in RULE_CODES if code not in year_shares]
            if missing:
                raise ValueError(f"artifacts/{HAZARD_LABELS}: no {missing} rows for {span.crop_key} {year}")
            if (span.crop_key, year) not in soil:
                raise ValueError(f"artifacts/{SOIL_WETNESS}: no row for {span.crop_key} {year}")
            row = soil[(span.crop_key, year)]
            ids = [*row.source_ids, row.computed_by]
            wetness = SoilWetness(value=percent_value(row.value, ids), normal=percent_value(row.normal, ids))
            per_year.append(ExposureYear(year=year, shares=year_shares, soil_wetness=wetness))
        exposure.append(CropExposure(crop_key=span.crop_key, crop=span.crop, per_year=per_year))
    return exposure


def _water(calendar: list[CropSpan], crops: dict[str, CropEntry]) -> list[WaterFact]:
    """Every cited water fact of each crop's id; one `not_listed` fact where neither source lists it (§6)."""
    water = []
    for span in calendar:
        facts = crops[span.crop_id].water_facts
        if not facts:
            water.append(WaterFact(crop_key=span.crop_key, measure="not_listed", value=None, scope=None, note=None))
        for fact in facts:
            value = Value(value=fact.value_text, unit=fact.unit, source_ids=[fact.source_id])
            water.append(
                WaterFact(crop_key=span.crop_key, measure=fact.measure, value=value, scope=fact.scope, note=fact.note)
            )
    return water


def _land(plan: PlanEntry, calendar: list[CropSpan], crops: dict[str, CropEntry]) -> LandCare:
    """The three land-care checks (05-DATA-CONTRACTS §7; D-56 b, D-103); values cite the study and E-022 (D-156)."""
    ids: list[SourceId] = [*plan.source_ids, ENGINE_ID]
    crop_ids = list(dict.fromkeys(span.crop_id for span in calendar))
    days = living_days(calendar)
    legumes = [crops[c].name for c in crop_ids if crops[c].is_legume]
    return LandCare(
        crops_in_year=LandCheck(
            value=Value(value=str(len(crop_ids)), unit=CROPS_UNIT, source_ids=ids),
            principle_source_ids=CROPS_PRINCIPLE,
        ),
        living_days=LandCheck(
            value=None if days is None else Value(value=str(days), unit=DAYS_UNIT, source_ids=ids),
            principle_source_ids=LIVING_PRINCIPLE,
        ),
        legume=Legume(present=bool(legumes), crops=legumes, principle_source_ids=LEGUME_PRINCIPLE),
    )
