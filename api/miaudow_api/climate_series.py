"""Climate series for the Phase-2 API: annual history and one year's monthly anomalies, NASA POWER and CHIRPS side by
side (AI core 01, read-only views of data/canonical/climate.json).

Rules kept here:
- NASA POWER (MERRA-2 reanalysis) and CHIRPS v3 (satellite + station blend) are two separate sources. They are shown
  next to each other and never averaged into one number.
- The CHIRPS 1991-2020 normal and the CHIRPS farmland-weighted values are computed here (DERIVED, named methods below):
  the normal is the mean of the 30 baseline years of the same month and is null when any of those 30 values is null;
  the farmland-weighted value uses the same MODIS farmland weights as POWER and is null when any cell is null.
- Nothing is interpolated or zero-filled; past years are not a forecast; none of it is a field measurement.
"""

from __future__ import annotations

from datetime import date

from . import canonical
from .climate import FARMLAND, ClimateInputError
from .contracts import (
    AnomalyArea,
    ClimateAnomalies,
    ClimateHistory,
    Place,
    Provenance,
    Series,
    Text,
    TimeWindow,
    Unavailable,
)

BASELINE = (1991, 2020)
SITE = "site_luu_son"
CHIRPS_URL = "https://www.chc.ucsb.edu/data/chirps3"
POWER_RES = "0.5° x 0.625° NASA POWER (MERRA-2) grid"
CHIRPS_RES = "0.05° CHIRPS v3 pixels averaged over the POWER cell"

METHODS = {
    "chirps_normal_1991_2020": Text(
        vi="Chuẩn CHIRPS 1991-2020: trung bình 30 năm của cùng tháng; để trống nếu thiếu một năm nào.",
        en="CHIRPS 1991-2020 normal: the 30-year mean of the same month; empty when any year is missing.",
    ),
    "chirps_farmland_weighted_mean": Text(
        vi="Giá trị CHIRPS của 5 ô nhân với trọng số đất trồng MODIS (như NASA POWER); để trống nếu thiếu một ô.",
        en="CHIRPS values of the 5 cells times the MODIS farmland weights (as for NASA POWER); empty when a cell is "
        "missing.",
    ),
    "annual_anomaly_vs_1991_2020_normal": Text(
        vi="Tổng mưa năm so với tổng 12 chuẩn tháng 1991-2020, tính bằng %.",
        en="Annual rain total against the sum of the twelve 1991-2020 monthly normals, in %.",
    ),
}

PAST = Text(vi="Năm đã qua không phải dự báo.", en="A past year is not a forecast.")
POWER_LIMIT = Text(
    vi="NASA POWER là giá trị mô hình trên ô lưới lớn, không phải số đo tại ruộng.",
    en="NASA POWER is a model value on a large grid cell, not a field measurement.",
)
CHIRPS_LIMIT = Text(
    vi="CHIRPS là ước tính mưa từ vệ tinh và trạm đo, không phải số đo tại ruộng; đặt cạnh NASA POWER, không trộn.",
    en="CHIRPS is a satellite-and-station rain estimate, not a field measurement; kept beside NASA POWER, never merged.",
)
SIDE_BY_SIDE = Text(
    vi="Hai nguồn mưa (NASA POWER và CHIRPS) được đặt cạnh nhau; khi chúng khác nhau, cả hai đều được giữ nguyên.",
    en="Two rain sources (NASA POWER and CHIRPS) are shown side by side; where they differ, both are kept as they are.",
)


def _climate() -> dict:
    return canonical.load("climate.json")


def r1(v: float | None) -> float | None:
    return None if v is None else round(float(v), 1)


# ---------------------------------------------------------------- places


def cell_place(cell: dict) -> Place:
    lat, lon = cell["lat"], cell["lon"]
    return Place(
        place_id=cell["id"],
        kind="grid_cell",
        name=Text(
            vi=f"Ô lưới NASA POWER tâm {lat}° B, {lon}° Đ",
            en=f"NASA POWER cell centred at {lat}° N, {lon}° E",
        ),
        lat=lat,
        lon=lon,
        bbox=[lon - 0.3125, lat - 0.25, lon + 0.3125, lat + 0.25],
        cell_ids=[cell["id"]],
    )


def farmland_place() -> Place:
    return Place(
        place_id=FARMLAND,
        kind="farmland_weighted_area",
        name=Text(
            vi="Đất trồng trọt của Nghệ An: 5 ô lưới, cân theo phần đất trồng (MODIS)",
            en="Nghệ An farmland: 5 grid cells weighted by farmland share (MODIS)",
        ),
        cell_ids=[c["id"] for c in _climate()["cells"]],
    )


def site_place() -> Place:
    geo = canonical.load_optional("geo_do_luong.json") or {}
    point = geo.get("study_point") or {}
    return Place(
        place_id=SITE,
        kind="study_point",
        name=Text(
            vi="Điểm xã Lưu Sơn (cũ), Đô Lương: điểm ảnh CHIRPS 0,05° chứa điểm đánh dấu xã",
            en="Lưu Sơn commune point (former), Đô Lương: the 0.05° CHIRPS pixel holding the commune marker",
        ),
        lat=point.get("lat"),
        lon=point.get("lon"),
    )


def area_ids() -> list[str]:
    return [FARMLAND, *[c["id"] for c in _climate()["cells"]], SITE]


def _place(area: str) -> Place:
    if area == FARMLAND:
        return farmland_place()
    if area == SITE:
        return site_place()
    cell = next((c for c in _climate()["cells"] if c["id"] == area), None)
    if cell is None:
        raise ClimateInputError(f"unknown cell {area!r}; known: {', '.join(area_ids())}")
    return cell_place(cell)


# ---------------------------------------------------------------- CHIRPS arithmetic (DERIVED, see METHODS)


def chirps_block() -> dict | None:
    ch = _climate().get("chirps")
    return ch if ch and ch.get("status") == "loaded" else None


def _weighted(values: list[float | None], weights: list[float]) -> float | None:
    if any(v is None for v in values):
        return None
    return sum(w * v for w, v in zip(weights, values, strict=True)) / sum(weights)


def chirps_monthly(area: str) -> dict[int, list[float | None]] | None:
    """CHIRPS monthly totals {year: 12 values} for a cell, the study site, or the farmland-weighted area."""
    ch = chirps_block()
    if ch is None:
        return None
    if area != FARMLAND:
        raw = ch["cells"].get(area)
        return None if raw is None else {int(y): list(v) for y, v in raw.items()}
    cells = _climate()["cells"]
    if any(c["id"] not in ch["cells"] for c in cells):
        return None
    weights = [c["weight"] for c in cells]
    years = sorted(set.intersection(*[{int(y) for y in ch["cells"][c["id"]]} for c in cells]))
    return {y: [_weighted([ch["cells"][c["id"]][str(y)][m] for c in cells], weights) for m in range(12)] for y in years}


def chirps_normal(series: dict[int, list[float | None]]) -> list[float | None]:
    out: list[float | None] = []
    for m in range(12):
        vals = [series.get(y, [None] * 12)[m] for y in range(BASELINE[0], BASELINE[1] + 1)]
        out.append(None if any(v is None for v in vals) else sum(vals) / len(vals))
    return out


def _anoms(values: list[float | None], normal: list[float | None]) -> tuple[list, list]:
    mm = [None if v is None or n is None else r1(v - n) for v, n in zip(values, normal, strict=True)]
    pct = [None if v is None or not n else r1((v - n) / n * 100.0) for v, n in zip(values, normal, strict=True)]
    return mm, pct


# ---------------------------------------------------------------- provenance


def power_provenance(method_id: str, transformation_id: str, area: str) -> Provenance:
    c = _climate()
    return Provenance(
        dataset_id=c["dataset_id"],
        source_id=c["source_id"],
        source_url=c["source_url"],
        source_revision=c.get("source_revision"),
        method_id=method_id,
        transformation_id=transformation_id,
        spatial_resolution=POWER_RES + ("; 5 cells weighted by MODIS farmland share" if area == FARMLAND else ""),
        validation_status="DERIVED",
        missing_policy="A month with any missing day has no total; nothing is interpolated or zero-filled.",
        limitations=[POWER_LIMIT, PAST],
    )


def chirps_provenance(method_id: str, transformation_id: str, area: str) -> Provenance:
    extra = [METHODS[method_id]] if method_id in METHODS else []
    if area == FARMLAND:
        extra.append(METHODS["chirps_farmland_weighted_mean"])
    return Provenance(
        dataset_id="chirps_v3_monthly",
        source_id="X-CHIRPS-V3",
        source_url=CHIRPS_URL,
        source_revision="CHIRPS v3.0 final monthly",
        method_id=method_id,
        transformation_id=transformation_id,
        spatial_resolution="one 0.05° CHIRPS v3 pixel" if area == SITE else CHIRPS_RES,
        validation_status="DERIVED",
        missing_policy="A missing month stays null; a normal or weighted value with any missing input stays null.",
        limitations=[CHIRPS_LIMIT, PAST, *extra],
    )


def _months(year: int) -> list[str]:
    return [f"{year}-{m:02d}" for m in range(1, 13)]


def _year_window(year: int) -> TimeWindow:
    return TimeWindow(start=date(year, 1, 1), end=date(year, 12, 31), label=Text(vi=f"Năm {year}", en=f"Year {year}"))


BASELINE_WINDOW = TimeWindow(
    start=date(BASELINE[0], 1, 1),
    end=date(BASELINE[1], 12, 31),
    label=Text(vi="Chuẩn 1991-2020", en="1991-2020 normal"),
)

TITLES = {
    "rain_total": Text(vi="Tổng mưa tháng", en="Monthly rain total"),
    "rain_normal_1991_2020": Text(vi="Mưa trung bình 1991-2020 của tháng", en="1991-2020 mean of the month"),
    "rain_anomaly": Text(vi="Chênh lệch so với trung bình", en="Difference from the mean"),
    "rain_anomaly_pct": Text(vi="Chênh lệch so với trung bình (%)", en="Difference from the mean (%)"),
}


# ---------------------------------------------------------------- one year's monthly anomalies


def anomalies(year: int) -> ClimateAnomalies:
    """Per-cell, farmland-weighted and study-site monthly rain anomalies of one year; POWER and CHIRPS side by side."""
    c = _climate()
    if year not in c["years"]:
        raise ClimateInputError(f"year {year} outside {min(c['years'])}-{max(c['years'])}")
    win = _year_window(year)
    areas = []
    for area in area_ids():
        place = _place(area)
        series: list[Series] = []
        missing: list[Unavailable] = []
        # NASA POWER
        if area == SITE:
            missing.append(
                Unavailable(
                    what="nasa_power_daily",
                    reason=Text(
                        vi="NASA POWER chỉ có ô lưới 0,5° x 0,625°; không chia nhỏ xuống điểm xã, nên không có chuỗi riêng "
                        "cho Lưu Sơn.",
                        en="NASA POWER exists only on its 0.5° x 0.625° grid; it is never split down to a commune "
                        "point, so Lưu Sơn has no series of its own.",
                    ),
                )
            )
        else:
            row = (
                c["series"]["farmland_weighted"][str(year)]
                if area == FARMLAND
                else c["series"]["cells"][area][str(year)]
            )
            normal = c["normal_mm"]["farmland_weighted"] if area == FARMLAND else c["normal_mm"]["cells"][area]
            base = f"climate.json:series.{area}.{year}"
            for quantity, values, unit, method, tid in (
                (
                    "rain_total",
                    row["monthly_rain_mm"],
                    "mm",
                    "sum_daily_precip_complete_month",
                    f"{base}.monthly_rain_mm",
                ),
                (
                    "rain_normal_1991_2020",
                    normal,
                    "mm",
                    "anomaly_vs_1991_2020_normal",
                    f"climate.json:normal_mm.{area}",
                ),
                ("rain_anomaly", row["anomaly_mm"], "mm", "anomaly_vs_1991_2020_normal", f"{base}.anomaly_mm"),
                ("rain_anomaly_pct", row["anomaly_pct"], "%", "anomaly_vs_1991_2020_normal", f"{base}.anomaly_pct"),
            ):
                series.append(
                    Series(
                        quantity=f"{quantity}_power",
                        title=Text(vi=TITLES[quantity].vi + " (NASA POWER)", en=TITLES[quantity].en + " (NASA POWER)"),
                        unit=unit,
                        periods=_months(year),
                        values=list(values),
                        place=place,
                        time_window=BASELINE_WINDOW if quantity == "rain_normal_1991_2020" else win,
                        provenance=power_provenance(method, tid, area),
                    )
                )
        # CHIRPS
        ch = chirps_monthly(area)
        if ch is None or year not in ch:
            missing.append(
                Unavailable(
                    what="chirps_v3_monthly",
                    reason=Text(
                        vi="Chưa có số liệu CHIRPS cho vùng và năm này trong dữ liệu đã dựng.",
                        en="No CHIRPS values for this area and year in the built data.",
                    ),
                    how_to_fix=r".venv\Scripts\python pipeline/fetch_chirps_v3.py, then pipeline/build_canonical.py",
                )
            )
        else:
            normal = chirps_normal(ch)
            values = [r1(v) for v in ch[year]]
            mm, pct = _anoms(ch[year], normal)
            tid = (
                f"climate.json:chirps.cells.{area}.{year}"
                if area != FARMLAND
                else f"climate.json:chirps.cells.*.{year}"
            )
            for quantity, vals, unit, method in (
                ("rain_total", values, "mm", "chirps_monthly_cell"),
                ("rain_normal_1991_2020", [r1(v) for v in normal], "mm", "chirps_normal_1991_2020"),
                ("rain_anomaly", mm, "mm", "chirps_normal_1991_2020"),
                ("rain_anomaly_pct", pct, "%", "chirps_normal_1991_2020"),
            ):
                series.append(
                    Series(
                        quantity=f"{quantity}_chirps",
                        title=Text(vi=TITLES[quantity].vi + " (CHIRPS)", en=TITLES[quantity].en + " (CHIRPS)"),
                        unit=unit,
                        periods=_months(year),
                        values=vals,
                        place=place,
                        time_window=BASELINE_WINDOW if quantity == "rain_normal_1991_2020" else win,
                        provenance=chirps_provenance(method, tid, area),
                    )
                )
        areas.append(AnomalyArea(place=place, series=series, unavailable=missing))
    return ClimateAnomalies(
        year=year, time_window=win, baseline=BASELINE_WINDOW, areas=areas, notes=[SIDE_BY_SIDE, PAST]
    )


# ---------------------------------------------------------------- annual history


def _annual_anomaly_pct(total: float | None, normal: list[float | None]) -> float | None:
    if total is None or any(n is None for n in normal):
        return None
    ref = sum(normal)
    return r1((total - ref) / ref * 100.0) if ref else None


def history(area: str = FARMLAND, first: int | None = None, last: int | None = None) -> ClimateHistory:
    """Annual series of one area: POWER rain, its anomaly, hot and cold days, longest dry spell, drought-rain months,
    and the CHIRPS annual rain beside it."""
    c = _climate()
    years_all = c["years"]
    first = years_all[0] if first is None else first
    last = years_all[-1] if last is None else last
    if first > last:
        raise ClimateInputError(f"from {first} is after to {last}")
    if first < years_all[0] or last > years_all[-1]:
        raise ClimateInputError(f"years must be within {years_all[0]}-{years_all[-1]}")
    place = _place(area)
    years = list(range(first, last + 1))
    win = TimeWindow(
        start=date(first, 1, 1), end=date(last, 12, 31), label=Text(vi=f"{first}-{last}", en=f"{first}-{last}")
    )
    periods = [str(y) for y in years]
    series: list[Series] = []
    missing: list[Unavailable] = []
    if area == SITE:
        missing.append(
            Unavailable(
                what="nasa_power_daily",
                reason=Text(
                    vi="NASA POWER không có chuỗi riêng cho điểm xã; xem ô lưới chứa điểm này.",
                    en="NASA POWER has no series for the commune point; see the grid cell that holds it.",
                ),
            )
        )
    else:
        rows = c["series"]["farmland_weighted"] if area == FARMLAND else c["series"]["cells"][area]
        power_normal = c["normal_mm"]["farmland_weighted"] if area == FARMLAND else c["normal_mm"]["cells"][area]
        base = f"climate.json:series.{area}"
        weighted_note = " (farmland-weighted mean of 5 cells)" if area == FARMLAND else ""
        for quantity, title, unit, method, getter in (
            (
                "annual_rain_total",
                Text(vi="Tổng mưa cả năm (NASA POWER)", en="Annual rain total (NASA POWER)"),
                "mm",
                "sum_complete_months",
                lambda r: r["annual_rain_mm"],
            ),
            (
                "annual_rain_anomaly_pct",
                Text(
                    vi="Mưa cả năm so với chuẩn 1991-2020 (NASA POWER)",
                    en="Annual rain vs the 1991-2020 normal (NASA POWER)",
                ),
                "%",
                "annual_anomaly_vs_1991_2020_normal",
                lambda r: _annual_anomaly_pct(r["annual_rain_mm"], power_normal),
            ),
            (
                "hot_days",
                Text(vi="Số ngày từ 35 °C", en="Days at 35 °C or more"),
                "days",
                "count_days_t2m_max_ge_35",
                lambda r: r["hot_days"],
            ),
            (
                "cold_days",
                Text(vi="Số ngày từ 13 °C trở xuống", en="Days at 13 °C or less"),
                "days",
                "count_days_t2m_le_13",
                lambda r: r["cold_days"],
            ),
            (
                "longest_dry_spell",
                Text(vi="Đợt khô dài nhất", en="Longest dry spell"),
                "days",
                "etccdi_cdd_calendar_year",
                lambda r: r["longest_dry_spell_days"],
            ),
            (
                "drought_rain_months",
                Text(vi="Số tháng thiếu mưa quá nửa", en="Months with under half the usual rain"),
                "months",
                "art48_drought_rain_month",
                lambda r: float(len(r["drought_rain_months"])),
            ),
        ):
            prov = power_provenance(method, f"{base}.{{year}}.{quantity}{weighted_note}", area)
            if method in METHODS:
                prov = prov.model_copy(update={"limitations": [*prov.limitations, METHODS[method]]})
            series.append(
                Series(
                    quantity=f"{quantity}_power",
                    title=title,
                    unit=unit,
                    periods=periods,
                    values=[getter(rows[str(y)]) for y in years],
                    place=place,
                    time_window=win,
                    provenance=prov,
                )
            )
    ch = chirps_monthly(area)
    if ch is None:
        missing.append(
            Unavailable(
                what="chirps_v3_monthly",
                reason=Text(vi="Chưa có số liệu CHIRPS cho vùng này.", en="No CHIRPS values for this area."),
                how_to_fix=r".venv\Scripts\python pipeline/fetch_chirps_v3.py, then pipeline/build_canonical.py",
            )
        )
    else:
        normal = chirps_normal(ch)

        def total(y: int) -> float | None:
            vals = ch.get(y)
            return None if vals is None or any(v is None for v in vals) else sum(vals)

        series.append(
            Series(
                quantity="annual_rain_total_chirps",
                title=Text(vi="Tổng mưa cả năm (CHIRPS)", en="Annual rain total (CHIRPS)"),
                unit="mm",
                periods=periods,
                values=[r1(total(y)) for y in years],
                place=place,
                time_window=win,
                provenance=chirps_provenance("chirps_monthly_cell", f"climate.json:chirps.cells.{area}", area),
            )
        )
        series.append(
            Series(
                quantity="annual_rain_anomaly_pct_chirps",
                title=Text(
                    vi="Mưa cả năm so với chuẩn 1991-2020 (CHIRPS)", en="Annual rain vs the 1991-2020 normal (CHIRPS)"
                ),
                unit="%",
                periods=periods,
                values=[_annual_anomaly_pct(total(y), normal) for y in years],
                place=place,
                time_window=win,
                provenance=chirps_provenance("chirps_normal_1991_2020", f"climate.json:chirps.cells.{area}", area),
            )
        )
    return ClimateHistory(
        place=place, time_window=win, years=years, series=series, unavailable=missing, notes=[SIDE_BY_SIDE, PAST]
    )
