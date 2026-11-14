"""AI core 01: climate intelligence as MetricRecords built from data/canonical/ (climate, hazards, soil).

Every record says where its number came from: NASA POWER daily values are MERRA-2 model (reanalysis) values on a
0.5° x 0.625° grid, never "measured on the farm" (is_field_measurement=False), and a past year is never a forecast
(is_forecast=False). A missing value stays None with quality_flag MISSING; nothing is filled.

`live_power` keeps the starter's on-demand NASA POWER fetch and its complete-month aggregation.

All public functions are pure (they only read the canonical files) and return JSON-serialisable models, so the
copilot can call them as tools.
"""

from __future__ import annotations

import calendar
import datetime as dt
from collections import defaultdict
from datetime import date

import httpx

from . import canonical
from .contracts import Geometry, MetricRecord, Text, TimeWindow, Uncertainty

POWER_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_DOCS = "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"
FARMLAND = "farmland_weighted"
STUDY_YEARS = range(1995, 2025)
GRID_RES = "0.5° x 0.625° NASA POWER (MERRA-2) grid; 5 cells weighted by MODIS farmland share"

GRID_LIMIT = Text(
    vi="Giá trị mô hình theo ô lưới lớn, làm mờ các giá trị cực đoan; không phải số đo tại ruộng.",
    en="A model value on a large grid cell that smooths extremes; not measured at the field.",
)
PAST_LIMIT = Text(vi="Năm đã qua không phải dự báo.", en="A past year is not a forecast.")
GRID_UNCERTAINTY = Uncertainty(
    kind="qualitative",
    note=Text(
        vi="NASA không công bố khoảng sai số cho từng ngày của ô lưới này.",
        en="NASA publishes no per-day error range for this grid cell.",
    ),
)
NONE_REPORTED = Uncertainty(kind="none_reported")


class ClimateInputError(ValueError):
    """An unknown cell, year, crop or variable (the API answers 422)."""


def _climate() -> dict:
    return canonical.load("climate.json")


def _geometry(cell: str) -> Geometry:
    c = _climate()
    if cell == FARMLAND:
        return Geometry(
            type="farmland_weighted_area",
            cell_ids=[x["id"] for x in c["cells"]],
            description=Text(
                vi="Đất trồng trọt của Nghệ An: 5 ô lưới NASA POWER, cân theo phần đất trồng (MODIS)",
                en="Nghệ An farmland: 5 NASA POWER cells weighted by farmland share (MODIS)",
            ),
        )
    found = next((x for x in c["cells"] if x["id"] == cell), None)
    if found is None:
        raise ClimateInputError(f"unknown cell {cell!r}; known: {FARMLAND}, " + ", ".join(x["id"] for x in c["cells"]))
    return Geometry(
        type="grid_cell",
        lat=found["lat"],
        lon=found["lon"],
        cell_ids=[cell],
        description=Text(
            vi=f"Một ô lưới NASA POWER, tâm {found['lat']}° B, {found['lon']}° Đ",
            en=f"One NASA POWER cell centred at {found['lat']}° N, {found['lon']}° E",
        ),
    )


def _power_record(
    metric_id, value, unit, window, geometry, method_id, transformation_id, limitations=()
) -> MetricRecord:
    c = _climate()
    return MetricRecord(
        metric_id=metric_id,
        dataset_id=c["dataset_id"],
        source_id=c["source_id"],
        source_url=c["source_url"],
        source_revision=c.get("source_revision"),
        retrieved_at=None,
        value=value,
        unit=unit,
        time_window=window,
        geometry=geometry,
        spatial_resolution=GRID_RES if geometry.type == "farmland_weighted_area" else "0.5° x 0.625°",
        method_id=method_id,
        transformation_id=transformation_id,
        quality_flag="OK" if value is not None else "MISSING",
        missing_policy="A month with any missing day has no total; nothing is interpolated or zero-filled.",
        uncertainty=GRID_UNCERTAINTY,
        validation_status="DERIVED",
        is_forecast=False,
        is_field_measurement=False,
        limitations=[GRID_LIMIT, PAST_LIMIT, *limitations],
    )


def _check_year(year: int, years) -> None:
    if year not in years:
        raise ClimateInputError(f"year {year} outside {min(years)}-{max(years)}")


def _row(cell: str, year: int) -> dict:
    c = _climate()
    _check_year(year, c["years"])
    if cell == FARMLAND:
        return c["series"]["farmland_weighted"][str(year)]
    if cell not in c["series"]["cells"]:
        _geometry(cell)  # raises with the list of known cells
    return c["series"]["cells"][cell][str(year)]


def year_summary(year: int, cell: str = FARMLAND) -> list[MetricRecord]:
    """Tool: one year's annual rain, hot days, cold days, longest dry spell, drought-rain months (+ rule shares)."""
    row = _row(cell, year)
    geo = _geometry(cell)
    win = TimeWindow(start=date(year, 1, 1), end=date(year, 12, 31), label=Text(vi=f"Năm {year}", en=f"Year {year}"))
    base = f"climate.json:series.{cell}.{year}"
    weighted = (
        [Text(vi="Trung bình có trọng số đất trồng của 5 ô.", en="Farmland-weighted mean of 5 cells.")]
        if cell == FARMLAND
        else []
    )
    out = [
        _power_record(
            "annual_rain_total", row["annual_rain_mm"], "mm", win, geo, "sum_complete_months", f"{base}.annual_rain_mm"
        ),
        _power_record(
            "hot_days", row["hot_days"], "days", win, geo, "count_days_t2m_max_ge_35", f"{base}.hot_days", weighted
        ),
        _power_record(
            "cold_days", row["cold_days"], "days", win, geo, "count_days_t2m_le_13", f"{base}.cold_days", weighted
        ),
        _power_record(
            "longest_dry_spell",
            row["longest_dry_spell_days"],
            "days",
            win,
            geo,
            "etccdi_cdd_calendar_year",
            f"{base}.longest_dry_spell_days",
            weighted,
        ),
        _power_record(
            "drought_rain_months",
            float(len(row["drought_rain_months"])),
            "months",
            win,
            geo,
            "art48_drought_rain_month",
            f"{base}.drought_rain_months",
            [
                Text(
                    vi="Các tháng: " + ", ".join(str(m) for m in row["drought_rain_months"])
                    if row["drought_rain_months"]
                    else "Không có tháng nào.",
                    en="Months: " + ", ".join(str(m) for m in row["drought_rain_months"])
                    if row["drought_rain_months"]
                    else "No month.",
                )
            ],
        ),
    ]
    if cell == FARMLAND and year in STUDY_YEARS:
        out.extend(hazard_shares(year))
    return out


def monthly(year: int, cell: str = FARMLAND) -> list[MetricRecord]:
    """Tool: 12 monthly rain totals with their 1991-2020 normal and anomaly (mm and %), plus CHIRPS when loaded."""
    row = _row(cell, year)
    geo = _geometry(cell)
    c = _climate()
    normals = c["normal_mm"]["farmland_weighted"] if cell == FARMLAND else c["normal_mm"]["cells"][cell]
    base = f"climate.json:series.{cell}.{year}"
    out = []
    for m in range(1, 13):
        win = TimeWindow(start=date(year, m, 1), end=date(year, m, calendar.monthrange(year, m)[1]))
        i = m - 1
        out.append(
            _power_record(
                "monthly_rain_total",
                row["monthly_rain_mm"][i],
                "mm",
                win,
                geo,
                "sum_daily_precip_complete_month",
                f"{base}.monthly_rain_mm[{i}]",
            )
        )
        out.append(
            _power_record(
                "monthly_rain_normal",
                normals[i],
                "mm",
                win,
                geo,
                "anomaly_vs_1991_2020_normal",
                f"climate.json:normal_mm.{cell}[{i}]",
                [Text(vi="Trung bình của cùng tháng trong 1991-2020.", en="Mean of the same month in 1991-2020.")],
            )
        )
        out.append(
            _power_record(
                "monthly_rain_anomaly_mm",
                row["anomaly_mm"][i],
                "mm",
                win,
                geo,
                "anomaly_vs_1991_2020_normal",
                f"{base}.anomaly_mm[{i}]",
            )
        )
        out.append(
            _power_record(
                "monthly_rain_anomaly_pct",
                row["anomaly_pct"][i],
                "%",
                win,
                geo,
                "anomaly_vs_1991_2020_normal",
                f"{base}.anomaly_pct[{i}]",
            )
        )
    chirps = c.get("chirps")
    if chirps and chirps.get("status") == "loaded" and cell != FARMLAND:
        values = chirps["cells"].get(cell, {}).get(str(year))
        if values:
            for m in range(1, 13):
                win = TimeWindow(start=date(year, m, 1), end=date(year, m, calendar.monthrange(year, m)[1]))
                v = values[m - 1]
                out.append(
                    MetricRecord(
                        metric_id="monthly_rain_total_chirps",
                        dataset_id="chirps_v3_monthly",
                        source_id="X-CHIRPS-V3",
                        source_url="https://www.chc.ucsb.edu/data/chirps3",
                        source_revision=None,
                        retrieved_at=None,
                        value=v,
                        unit="mm",
                        time_window=win,
                        geometry=geo,
                        spatial_resolution="0.05° CHIRPS v3 aggregated to the POWER cell",
                        method_id="chirps_monthly_cell",
                        transformation_id=f"climate.json:chirps.cells.{cell}.{year}[{m - 1}]",
                        quality_flag="OK" if v is not None else "MISSING",
                        missing_policy="A missing month stays null.",
                        uncertainty=NONE_REPORTED,
                        validation_status="DERIVED",
                        limitations=[
                            Text(
                                vi="Nguồn mưa thứ hai, đặt cạnh NASA POWER, không trộn.",
                                en="A second rain source, kept beside NASA POWER, never merged.",
                            ),
                            PAST_LIMIT,
                        ],
                    )
                )
    return out


RULES_VI = {
    "heavy_rain": "mưa lớn (Điều 44.1)",
    "heat": "nắng nóng (Điều 47.1)",
    "drought_rain_consecutive": "hạn hán, phần mưa, 2 tháng liền nhau (Điều 48.1)",
    "drought_rain_any2": "hạn hán, phần mưa, 2 tháng bất kỳ (Điều 48.1)",
    "cold": "rét hại (Điều 53.1 a, d)",
}


def _hazard_record(rule: str, value: float, year: int, crop: str | None, window: TimeWindow) -> MetricRecord:
    target = f"crop_level.{crop}.{rule}" if crop else f"year_level.{rule}"
    return MetricRecord(
        metric_id=f"hazard_share_{rule}",
        dataset_id="e019_hazard_labels",
        source_id="E-019",
        source_url=None,
        source_revision=None,
        retrieved_at=None,
        value=value,
        unit="share of farmland (0-1)",
        time_window=window,
        geometry=_geometry(FARMLAND),
        spatial_resolution=GRID_RES,
        method_id="E-019",
        transformation_id=f"hazards.json:{target}[{year - 1995}]",
        quality_flag="OK",
        missing_policy="The build stops when a weighted cell misses a day in the field time.",
        uncertainty=GRID_UNCERTAINTY,
        validation_status="DERIVED",
        limitations=[
            Text(
                vi=f"Quy tắc {RULES_VI[rule]} của Quyết định 18/2021 (R-A01), cấp độ 1 trở lên.",
                en=f"Rule {rule} of Decision 18/2021 (R-A01), level 1 or higher.",
            ),
            Text(
                vi="Cách đọc máy móc trên số liệu quá khứ, không phải ghi nhận thiên tai chính thức.",
                en="A mechanical reading on past values, not an official disaster record.",
            ),
            GRID_LIMIT,
            PAST_LIMIT,
        ],
    )


def hazard_shares(year: int, crop: str | None = None) -> list[MetricRecord]:
    """Tool: farmland share meeting each official rule in one year, over all P-02 crops' field time or one crop's.

    `crop` accepts the team crop_key (e.g. "cc2_spring_chili") or the web key (e.g. "cc2_chili").
    """
    hz = canonical.load("hazards.json")
    _check_year(year, hz["years"])
    i = hz["years"].index(year)
    if crop is None:
        window = TimeWindow(
            start=date(year, 1, 1),
            end=date(year, 12, 31),
            label=Text(vi="Thời gian có cây của mọi cơ cấu P-02", en="Field time of every P-02 plan"),
        )
        return [_hazard_record(r, hz["year_level"][r][i], year, None, window) for r in hz["rules"]]
    try:
        key = canonical.web_crop_key(crop)
    except ValueError as err:
        raise ClimateInputError(str(err)) from err
    sow, harvest = hz["crops"][key]["sow"], hz["crops"][key]["harvest"]
    window = TimeWindow(
        start=date(year, int(sow[:2]), int(sow[3:])),
        end=date(year, int(harvest[:2]), int(harvest[3:])),
        label=Text(
            vi=f"Từ ngày gieo {sow} đến ngày thu hoạch đầu {harvest} (P-02)",
            en=f"From sowing {sow} to the first harvest {harvest} (P-02)",
        ),
    )
    return [_hazard_record(r, hz["crop_level"][key][r][i], year, key, window) for r in hz["rules"]]


def soil_wetness(year: int, crop: str) -> list[MetricRecord]:
    """Tool: root-zone soil wetness (GWETROOT, 0-1) while one crop was in the field, and its 1991-2020 normal."""
    soil = canonical.load("soil.json")
    _check_year(year, soil["years"])
    try:
        key = canonical.web_crop_key(crop)
    except ValueError as err:
        raise ClimateInputError(str(err)) from err
    entry = soil["crops"][key]
    hz = canonical.load("hazards.json")
    sow, harvest = hz["crops"][key]["sow"], hz["crops"][key]["harvest"]
    window = TimeWindow(
        start=date(year, int(sow[:2]), int(sow[3:])), end=date(year, int(harvest[:2]), int(harvest[3:]))
    )
    limits = [
        Text(
            vi="Giá trị mô hình MERRA-2, không phải số đo; không có ngưỡng tốt xấu.",
            en="A MERRA-2 model value, not a measurement; no good or bad threshold.",
        ),
        PAST_LIMIT,
    ]

    def rec(metric_id, value, transformation):
        return MetricRecord(
            metric_id=metric_id,
            dataset_id="e020_soil_wetness",
            source_id="E-020",
            source_url=None,
            source_revision=None,
            retrieved_at=None,
            value=value,
            unit="0-1",
            time_window=window,
            geometry=_geometry(FARMLAND),
            spatial_resolution=GRID_RES,
            method_id="E-020",
            transformation_id=transformation,
            quality_flag="OK" if value is not None else "MISSING",
            missing_policy="The build stops when a weighted cell misses a day.",
            uncertainty=GRID_UNCERTAINTY,
            validation_status="DERIVED",
            limitations=limits,
        )

    i = soil["years"].index(year)
    return [
        rec("soil_wetness", entry["values"][i], f"soil.json:crops.{key}.values[{i}]"),
        rec("soil_wetness_normal_1991_2020", entry["normal_1991_2020"], f"soil.json:crops.{key}.normal_1991_2020"),
    ]


def catalog() -> dict:
    """Tool: datasets, methods, sources and metric definitions (data/canonical/catalog.json)."""
    return canonical.load("catalog.json")


# ---------------------------------------------------------------- live NASA POWER (starter, kept)


def valid_value(v) -> float | None:
    """A POWER value, or None for the -999 fill value, junk or absurd magnitudes (never 0)."""
    if v is None:
        return None
    try:
        v = float(v)
    except (ValueError, TypeError):
        return None
    if v <= -990 or v >= 1e6:  # noqa: PLR2004 - POWER fill value -999 and absurd magnitudes
        return None
    return v


def monthly_aggregation(parameters: dict, year: int) -> list[dict]:
    """Daily NASA POWER PRECTOTCORR totals; daily T2M_MAX arithmetic mean. Missing remains null."""
    groups: dict = defaultdict(lambda: {"rains": [], "temps": []})
    rain = parameters.get("PRECTOTCORR", {})
    tmax = parameters.get("T2M_MAX", {})
    for mon in range(1, 13):
        for day in range(1, calendar.monthrange(year, mon)[1] + 1):
            k = f"{year}{mon:02}{day:02}"
            r = valid_value(rain.get(k))
            t = valid_value(tmax.get(k))
            if r is not None:
                groups[mon]["rains"].append(r)
            if t is not None:
                groups[mon]["temps"].append(t)
    out = []
    for mon in range(1, 13):
        row = groups[mon]
        total_days = calendar.monthrange(year, mon)[1]
        out.append(
            {
                "month": mon,
                "precipitation_mm": round(sum(row["rains"]), 1) if len(row["rains"]) == total_days else None,
                "temp_max_c": round(sum(row["temps"]) / len(row["temps"]), 1)
                if len(row["temps"]) == total_days
                else None,
                "day_count": len(row["rains"]),
            }
        )
    return out


class PowerUnavailable(RuntimeError):
    """NASA POWER could not be reached or answered without the variables; no substitute data is generated."""


async def live_power(lat: float, lon: float, year: int, client: httpx.AsyncClient | None = None) -> dict:
    """Tool: fetch one year of NASA POWER daily values for a point now and aggregate complete months only."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):  # noqa: PLR2004 - geographic limits
        raise ClimateInputError("invalid coordinates")
    if year < 1981 or year >= dt.date.today().year:  # noqa: PLR2004 - POWER daily starts in 1981
        raise ClimateInputError("year must be a complete past year from 1981; future years are not observations")
    q = {
        "parameters": "PRECTOTCORR,T2M_MAX",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": f"{year}0101",
        "end": f"{year}1231",
        "format": "JSON",
        "time-standard": "LST",
    }
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as c:
                r = await c.get(POWER_ENDPOINT, params=q)
        else:
            r = await client.get(POWER_ENDPOINT, params=q)
        r.raise_for_status()
        payload = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise PowerUnavailable("NASA POWER unavailable; no substitute data generated") from e
    params = payload.get("properties", {}).get("parameter", {})
    if not params or "PRECTOTCORR" not in params or "T2M_MAX" not in params:
        raise PowerUnavailable("NASA POWER response is missing requested variables")
    return {
        "provider": "NASA POWER",
        "year": year,
        "lat": lat,
        "lon": lon,
        "source_type": "model_assimilation_gridded",
        "source_url": POWER_DOCS,
        "method_id": "live_power_complete_month",
        "is_forecast": False,
        "is_field_measurement": False,
        "months": monthly_aggregation(params, year),
        "caveat": {
            "vi": "Giá trị trên ô lưới mô hình, không phải đo trực tiếp trên thửa ruộng. Tổng mưa theo tháng không "
            "công bố khi thiếu ngày. Năm đã qua không phải dự báo.",
            "en": "Values on a model grid cell, not measured on the field. Monthly totals are withheld when a day is "
            "missing. A past year is not a forecast.",
        },
    }
