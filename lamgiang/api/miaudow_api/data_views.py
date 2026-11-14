"""Read-only views of the governed data layer for the Phase-2 API: data quality, coverage, places, map layers, satellite
vegetation, research documents, AI capabilities and model evaluations.

Everything is read from data/canonical/ (and, for coverage and documents, from the fetch manifests in data/raw/). A
file that was not built gives an explicit unavailable state with the command that would build it; nothing is invented
to fill the gap. Imagery is labelled kind="visual" and never offered as evidence.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from . import canonical, climate_ml, climate_series
from .contracts import (
    AiCapability,
    Credential,
    DatasetCoverage,
    LegendStop,
    MapLayer,
    ModelEvaluation,
    NdviComposite,
    Place,
    Provenance,
    QualityReport,
    QualityResponse,
    Region,
    ResearchDocument,
    SatelliteScene,
    SatelliteScenes,
    SatelliteVegetation,
    Series,
    Text,
    TimeWindow,
    Unavailable,
)
from .paths import BUILD_COMMAND, RAW, ROOT

QUALITY_COMMAND = r".venv\Scripts\python pipeline/check_quality.py"
RETRIEVAL_RESULTS = ROOT / "api" / "eval" / "results" / "retrieval_2026-11-14.json"
SEASON_EN = {"spring": "Spring", "summer_autumn": "Summer-autumn", "autumn_winter": "Autumn-winter"}
SEASON_VI = {"spring": "Xuân", "summer_autumn": "Hè Thu", "autumn_winter": "Thu Đông"}


class NotFound(LookupError):
    """An unknown dataset or layer id (the API answers 404; the copilot sends the error back to the model)."""


def _manifest(*parts: str) -> dict | None:
    path = RAW.joinpath(*parts)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


# ---------------------------------------------------------------- quality


def quality() -> QualityResponse:
    q = canonical.load_optional("quality.json")
    if q is None:
        return QualityResponse(
            status="unavailable",
            report=None,
            unavailable=Unavailable(
                what="quality.json",
                reason=Text(
                    vi="Chưa có báo cáo chất lượng dữ liệu; hãy chạy bước kiểm tra.",
                    en="No data-quality report yet; run the check.",
                ),
                how_to_fix=QUALITY_COMMAND,
            ),
        )
    return QualityResponse(status="available", report=QualityReport(**q), unavailable=None)


# ---------------------------------------------------------------- places


def nghe_an_place() -> Place:
    geo = canonical.load("geo.json")
    return Place(
        place_id="nghe_an",
        kind="province",
        name=Text(vi="Tỉnh Nghệ An", en="Nghệ An province"),
        bbox=[round(v, 4) for v in geo["bounds"]],
    )


def do_luong_place() -> Place | None:
    dl = (canonical.load_optional("geo_do_luong.json") or {}).get("do_luong")
    if not dl:
        return None
    return Place(
        place_id="do_luong",
        kind="district",
        name=Text(vi=dl["name"]["vi"], en=dl["name"]["en"]),
        bbox=dl["bbox"],
    )


def modis_place() -> Place:
    geo = canonical.load_optional("geo_do_luong.json") or {}
    sp = geo.get("study_point") or {}
    return Place(
        place_id="modis_9x9_luu_son",
        kind="pixel_block",
        name=Text(
            vi="9 x 9 điểm ảnh MODIS 250 m (khoảng 2 km x 2 km) quanh điểm xã Lưu Sơn",
            en="9 x 9 MODIS 250 m pixels (about 2 km x 2 km) around the Lưu Sơn commune point",
        ),
        lat=sp.get("lat"),
        lon=sp.get("lon"),
    )


def regions() -> list[Region]:
    """Nghệ An outline, Đô Lương outline, the 5 weighted NASA POWER cells, the study point and the commune status."""
    geo = canonical.load("geo.json")
    clim = canonical.load("climate.json")
    cat = {d["dataset_id"]: d for d in canonical.load("catalog.json")["datasets"]}
    adm1 = cat.get("geoboundaries_adm1", {})
    out = [
        Region(
            region_id="nghe_an",
            kind="province",
            name=Text(vi="Tỉnh Nghệ An", en="Nghệ An province"),
            status="available",
            geometry={"type": "Polygon", "coordinates": geo["outline"]},
            bbox=[round(v, 6) for v in geo["bounds"]],
            weight=None,
            source="geoBoundaries gbOpen VNM ADM1 (simplified)",
            source_url=adm1.get("source_url"),
            licence=adm1.get("license", ""),
            validation_status="VERIFIED",
            notes=[
                Text(
                    vi="Đường viền đã đơn giản hóa, chỉ dùng để vẽ; không phải ranh giới pháp lý.",
                    en="A simplified outline for drawing only; not a legal boundary.",
                )
            ],
        )
    ]
    dlj = canonical.load_optional("geo_do_luong.json")
    if dlj and dlj.get("do_luong"):
        dl = dlj["do_luong"]
        out.append(
            Region(
                region_id="do_luong",
                kind="district",
                name=Text(vi=dl["name"]["vi"], en=dl["name"]["en"]),
                status="available",
                geometry={"type": "Polygon", "coordinates": dl["outline"]},
                bbox=dl["bbox"],
                weight=None,
                source=dl["source"],
                source_url=dl.get("source_url"),
                licence=dl["license"],
                validation_status=dl.get("validation_status", "VERIFIED"),
                notes=[Text(**x) for x in dlj.get("limitations", [])],
            )
        )
    else:
        out.append(
            Region(
                region_id="do_luong",
                kind="district",
                name=Text(vi="Huyện Đô Lương (cũ)", en="Former Đô Lương district"),
                status="unavailable",
                geometry=None,
                bbox=None,
                weight=None,
                source="geoBoundaries gbOpen VNM ADM2",
                source_url=None,
                licence="",
                validation_status="UNAVAILABLE",
                notes=[Text(vi="Chưa tải ranh giới huyện.", en="The district outline was not fetched.")],
            )
        )
    weights = cat.get("modis_farmland_weights", {})
    for c in clim["cells"]:
        lat, lon = c["lat"], c["lon"]
        out.append(
            Region(
                region_id=c["id"],
                kind="grid_cell",
                name=Text(vi=f"Ô lưới NASA POWER {lat}° B, {lon}° Đ", en=f"NASA POWER cell {lat}° N, {lon}° E"),
                status="available",
                geometry={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon - 0.3125, lat - 0.25],
                            [lon + 0.3125, lat - 0.25],
                            [lon + 0.3125, lat + 0.25],
                            [lon - 0.3125, lat + 0.25],
                            [lon - 0.3125, lat - 0.25],
                        ]
                    ],
                },
                bbox=[lon - 0.3125, lat - 0.25, lon + 0.3125, lat + 0.25],
                weight=round(c["weight"], 6),
                source="NASA POWER grid (R-N01); farmland weight from MODIS land cover (R-N02)",
                source_url=clim["source_url"],
                licence=weights.get("license", "NASA open data"),
                validation_status="DERIVED",
                notes=[
                    Text(
                        vi="Trọng số là phần đất trồng của Nghệ An nằm trong ô này (tổng 5 ô bằng 1).",
                        en="The weight is the share of Nghệ An farmland inside this cell (the 5 weights sum to 1).",
                    ),
                    Text(
                        vi="Giá trị thời tiết của ô là trung bình cả ô, kể cả phần ngoài tỉnh.",
                        en="A cell's weather value is a whole-cell mean, including land outside the province.",
                    ),
                ],
            )
        )
    sp = (dlj or {}).get("study_point")
    if sp:
        out.append(
            Region(
                region_id="luu_son_point",
                kind="study_point",
                name=Text(vi="Điểm xã Lưu Sơn (cũ)", en="Lưu Sơn commune point (former)"),
                status="available",
                geometry={"type": "Point", "coordinates": [sp["lon"], sp["lat"]]},
                bbox=None,
                weight=None,
                source=sp["source"],
                source_url=sp.get("source_url"),
                licence="Wikidata (CC0 1.0)",
                validation_status="VERIFIED",
                notes=[
                    Text(
                        vi="Điểm đánh dấu xã trên Wikidata, không phải vị trí ruộng thử nghiệm.",
                        en="The commune marker on Wikidata, not the trial field.",
                    )
                ],
            )
        )
    status = (dlj or {}).get("luu_son_status") or {}
    out.append(
        Region(
            region_id="luu_son_commune",
            kind="district",
            name=Text(vi="Ranh giới xã Lưu Sơn", en="Lưu Sơn commune outline"),
            status="unavailable",
            geometry=None,
            bbox=None,
            weight=None,
            source="geoBoundaries (no VNM ADM3 layer)",
            source_url=None,
            licence="",
            validation_status="UNAVAILABLE",
            notes=[
                Text(
                    vi="Không có lớp ranh giới xã của Việt Nam trong geoBoundaries; không vẽ ranh giới xã.",
                    en=status.get("reason")
                    or "geoBoundaries has no Vietnamese commune layer; no commune outline is drawn.",
                )
            ],
        )
    )
    return out


# ---------------------------------------------------------------- layers


NDVI_RAMP = re.compile(
    r"NDVI <= ([-\d.]+) (#[0-9A-Fa-f]{6}), ([-\d.]+) (#[0-9A-Fa-f]{6}), >= ([-\d.]+) (#[0-9A-Fa-f]{6})"
)
LEGEND_WORDS = (
    Text(
        vi="Nâu đất: đất trống, đường, nhà, hoặc mặt nước (sông, ao, ruộng ngập)",
        en="Terracotta: bare soil, roads, houses, or water (river, ponds, flooded paddies)",
    ),
    Text(
        vi="Vàng: cây thưa hoặc lẫn đất (lúa mới cấy, ruộng vừa gặt, cây bụi)",
        en="Yellow: sparse plants or plants mixed with soil (young rice, freshly harvested fields, scrub)",
    ),
    Text(
        vi="Xanh đậm: cây dày, xanh tốt (lúa đứng, rừng)", en="Dark green: dense green plants (standing rice, forest)"
    ),
)


def ndvi_legend(veg: dict) -> list[LegendStop]:
    m = NDVI_RAMP.search(veg.get("formulas", {}).get("web_png", ""))
    if not m:
        return []
    vals = [(float(m.group(1)), m.group(2)), (float(m.group(3)), m.group(4)), (float(m.group(5)), m.group(6))]
    return [LegendStop(value=v, colour=c.upper(), label=w) for (v, c), w in zip(vals, LEGEND_WORDS, strict=True)]


def _season_window(veg: dict, season: str, year: int) -> TimeWindow:
    a, b = veg["seasons"][season].split("..")
    label_vi = f"{SEASON_VI.get(season, season)} {year}"
    return TimeWindow(
        start=date(year, int(a[:2]), int(a[3:])),
        end=date(year, int(b[:2]), int(b[3:])),
        label=Text(vi=label_vi, en=f"{SEASON_EN.get(season, season)} {year}"),
    )


def layers() -> list[MapLayer]:
    out: list[MapLayer] = []
    gibs = canonical.load_optional("gibs_layers.json")
    if gibs:
        use = Text(**gibs["use"])
        for lyr in gibs["layers"]:
            proj = lyr["projections"].get("epsg4326") or next(iter(lyr["projections"].values()))
            t = proj.get("time")
            out.append(
                MapLayer(
                    layer_id=f"gibs:{lyr['identifier']}",
                    title=Text(vi=lyr.get("title", lyr["identifier"]), en=lyr.get("title", lyr["identifier"])),
                    kind="visual",
                    group="gibs",
                    provider="NASA Global Imagery Browse Services (GIBS)",
                    licence=gibs["data_use_policy"]["statement"],
                    attribution=gibs["acknowledgement"],
                    source_url=gibs["capabilities"]["epsg4326"],
                    url_template=proj.get("rest_template"),
                    image_url=None,
                    bounds=None,
                    crs="EPSG:4326",
                    time=None if t is None else {k: t.get(k) for k in ("default", "first", "last")},
                    unit=None,
                    legend=[],
                    validation_status="ILLUSTRATIVE",
                    use=use,
                    limitations=[
                        Text(
                            vi=f"Vai trò: {lyr.get('role', '')}. Màu ảnh không phải số đo; không đọc giá trị từ màu.",
                            en=f"Role: {lyr.get('role', '')}. Tile colours are not measurements; never read values "
                            "from them.",
                        )
                    ],
                )
            )
    veg = canonical.load_optional("vegetation.json")
    if veg:
        legend = ndvi_legend(veg)
        for c in veg["composites"]:
            out.append(
                MapLayer(
                    layer_id=f"s2-ndvi:{c['id']}",
                    title=Text(
                        vi=f"Độ xanh NDVI Sentinel-2, {c['season_label_vi']} {c['year']}",
                        en=f"Sentinel-2 NDVI greenness, {SEASON_EN.get(c['season'], c['season'])} {c['year']}",
                    ),
                    kind="data",
                    group="sentinel2_ndvi",
                    provider="ESA Copernicus Sentinel-2 L2A, composited by MIAUDOW",
                    licence=veg["license"],
                    attribution=veg["attribution"],
                    source_url=veg.get("license_url"),
                    url_template=None,
                    image_url="/" + c["png"],
                    bounds=c["bounds"],
                    crs="EPSG:4326 (image rows north to south; source grid EPSG:32648, 20 m)",
                    time=_season_window(veg, c["season"], c["year"]).model_dump(mode="json")
                    | {"n_scenes": c["n_scenes"]},
                    unit="NDVI (unitless, -1 to 1)",
                    legend=legend,
                    validation_status="DERIVED",
                    use=Text(
                        vi=f"Độ xanh theo mùa trên toàn huyện; trung vị NDVI {str(c['ndvi_median']).replace('.', ',')} từ "
                        f"{c['n_scenes']} cảnh.",
                        en=f"Seasonal greenness over the district; median NDVI {c['ndvi_median']} from {c['n_scenes']} "
                        "scenes.",
                    ),
                    limitations=[Text(**veg["limitations"])],
                )
            )
    clim = canonical.load("climate.json")
    cells = clim["cells"]
    out.append(
        MapLayer(
            layer_id="power-grid:cells",
            title=Text(vi="5 ô lưới NASA POWER có đất trồng", en="The 5 NASA POWER farmland cells"),
            kind="data",
            group="power_grid",
            provider="NASA POWER (R-N01); farmland weights from MODIS (R-N02)",
            licence="NASA open data (no restriction on use; credit NASA POWER)",
            attribution="NASA POWER",
            source_url=clim["source_url"],
            url_template=None,
            image_url=None,
            bounds=[
                min(c["lon"] for c in cells) - 0.3125,
                min(c["lat"] for c in cells) - 0.25,
                max(c["lon"] for c in cells) + 0.3125,
                max(c["lat"] for c in cells) + 0.25,
            ],
            crs="EPSG:4326",
            time={"first_year": clim["years"][0], "last_year": clim["years"][-1]},
            unit=None,
            legend=[],
            validation_status="DERIVED",
            use=Text(
                vi="Mỗi ô mang số liệu mưa và nhiệt của nó; xem /api/climate/history?cell=... để có số và nguồn.",
                en="Each cell carries its rain and temperature values; see /api/climate/history?cell=... for numbers "
                "and source.",
            ),
            limitations=[climate_series.POWER_LIMIT],
        )
    )
    for r in regions():
        if r.kind in ("province", "district") and r.status == "available":
            out.append(
                MapLayer(
                    layer_id=f"boundary:{r.region_id}",
                    title=r.name,
                    kind="data",
                    group="boundary",
                    provider=r.source,
                    licence=r.licence,
                    attribution=r.source,
                    source_url=r.source_url,
                    url_template=None,
                    image_url=None,
                    bounds=r.bbox,
                    crs="EPSG:4326",
                    time=None,
                    unit=None,
                    legend=[],
                    validation_status=r.validation_status,
                    use=Text(vi="Đường ranh giới để định hướng.", en="An outline for orientation."),
                    limitations=r.notes,
                )
            )
    return out


def layer(layer_id: str) -> MapLayer:
    found = next((x for x in layers() if x.layer_id == layer_id), None)
    if found is None:
        raise NotFound(f"unknown layer {layer_id!r}; known: {', '.join(x.layer_id for x in layers())}")
    return found


# ---------------------------------------------------------------- satellite


def _s2_provenance(veg: dict) -> Provenance:
    return Provenance(
        dataset_id="sentinel2_l2a_do_luong_vi",
        source_id="X-SENTINEL2-L2A",
        source_url="https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a",
        source_revision=None,
        method_id="sentinel2_scl_masked_ndvi",
        transformation_id="vegetation.json (pipeline/fetch_sentinel2.py)",
        spatial_resolution="20 m (10 m bands block-averaged), EPSG:32648",
        validation_status=veg.get("validation_status", "DERIVED"),
        missing_policy="Cloud, shadow and no-data pixels are left out, never filled; scenes with under 20 % valid "
        "pixels in the district are skipped.",
        limitations=[Text(**veg["limitations"])],
    )


S2_UNAVAILABLE = Unavailable(
    what="vegetation.json",
    reason=Text(vi="Chưa có số liệu Sentinel-2.", en="No Sentinel-2 data yet."),
    how_to_fix=r".venv\Scripts\python pipeline/fetch_sentinel2.py --workers 4",
)


def satellite_scenes() -> SatelliteScenes:
    veg = canonical.load_optional("vegetation.json")
    if veg is None:
        return SatelliteScenes(
            status="unavailable",
            reason=S2_UNAVAILABLE.reason,
            place=None,
            time_window=None,
            units={},
            scenes=[],
            counts={},
            provenance=None,
            attribution=None,
            limitations=[],
        )
    scenes = [
        SatelliteScene(
            scene_id=s["scene_id"],
            date=date.fromisoformat(s["date"]),
            season=s["season"],
            season_year=s["season_year"],
            cloud_cover_tile_pct=s.get("cloud"),
            cloud_fraction_district=s.get("cloud_district_scl"),
            valid_fraction=s.get("valid_fraction"),
            ndvi_median=s.get("ndvi_median"),
            ndvi_p25=s.get("ndvi_p25"),
            ndvi_p75=s.get("ndvi_p75"),
            evi_median=s.get("evi_median"),
            ndmi_median=s.get("ndmi_median"),
        )
        for s in veg["scenes"]
    ]
    manifest = _manifest("sentinel2", "MANIFEST.json") or {}
    counts = {k: int(v) for k, v in (manifest.get("counts") or {}).items() if isinstance(v, int)}
    dates = sorted(s.date for s in scenes)
    return SatelliteScenes(
        status="available",
        reason=None,
        place=do_luong_place(),
        time_window=TimeWindow(
            start=dates[0],
            end=dates[-1],
            label=Text(vi="2020-2021 và 2023-2024", en="2020-2021 and 2023-2024"),
        ),
        units={
            "cloud_cover_tile_pct": "% of the tile (ESA metadata)",
            "cloud_fraction_district": "share of the district (0-1, SCL classes)",
            "valid_fraction": "share of district pixels kept (0-1)",
            "ndvi_median": "NDVI (unitless, -1 to 1), median over the district",
            "ndvi_p25": "NDVI, 25th percentile over the district",
            "ndvi_p75": "NDVI, 75th percentile over the district",
            "evi_median": "EVI (unitless), median over the district",
            "ndmi_median": "NDMI (unitless, -1 to 1), median over the district",
        },
        scenes=scenes,
        counts={"scenes_used": len(scenes), **counts},
        provenance=_s2_provenance(veg),
        attribution=veg.get("attribution"),
        limitations=[Text(**veg["limitations"])],
    )


COMPARABILITY = [
    Text(
        vi="Ảnh ghép 2020-21 và 2024 không so sánh được như một sự thay đổi: số cảnh và phiên bản xử lý của ESA khác "
        "nhau, và mây làm mất nhiều ngày trong mùa mưa.",
        en="The 2020-21 and 2024 composites are not comparable as change: scene counts and ESA processing baselines "
        "differ, and clouds remove many rainy-season dates.",
    ),
    Text(
        vi="Sentinel-2 (20 m, cả huyện) và MODIS (250 m, quanh một điểm) đo ở hai quy mô khác nhau; không trộn.",
        en="Sentinel-2 (20 m, whole district) and MODIS (250 m, around one point) work at different scales; never "
        "merged.",
    ),
]


def satellite_vegetation() -> SatelliteVegetation:
    veg = canonical.load_optional("vegetation.json")
    ndvi = canonical.load_optional("ndvi_modis.json")
    unavailable: list[Unavailable] = []
    composites: list[NdviComposite] = []
    if veg is None:
        unavailable.append(S2_UNAVAILABLE)
    else:
        for c in veg["composites"]:
            composites.append(
                NdviComposite(
                    composite_id=c["id"],
                    season=c["season"],
                    season_label=Text(
                        vi=c["season_label_vi"],
                        en=f"{SEASON_EN.get(c['season'], c['season'])} ({veg['seasons'][c['season']]})",
                    ),
                    year=c["year"],
                    time_window=_season_window(veg, c["season"], c["year"]),
                    n_scenes=c["n_scenes"],
                    scene_dates=[date.fromisoformat(d) for d in c["scene_dates"]],
                    ndvi_median=c["ndvi_median"],
                    ndvi_p25=c["ndvi_p25"],
                    ndvi_p75=c["ndvi_p75"],
                    unit="NDVI (unitless, -1 to 1), over the district",
                    coverage_fraction=c["coverage_fraction"],
                    n_pixels_with_value=c["n_pixels_with_value"],
                    image_url="/" + c["png"],
                    bounds=c["bounds"],
                )
            )
    modis: list[Series] = []
    if ndvi is None:
        unavailable.append(
            Unavailable(
                what="ndvi_modis.json",
                reason=Text(vi="Chưa có chuỗi NDVI MODIS.", en="No MODIS NDVI series yet."),
                how_to_fix=r".venv\Scripts\python pipeline/fetch_modis_ndvi.py --start 2015 --end 2024, then "
                + BUILD_COMMAND,
            )
        )
    else:
        dates = [date.fromisoformat(d) for d in ndvi["dates"]]
        win = TimeWindow(
            start=dates[0],
            end=min(dates[-1] + timedelta(days=15), date(dates[-1].year, 12, 31)),
            label=Text(vi="Các kỳ 16 ngày", en="16-day periods"),
        )
        prov = Provenance(
            dataset_id="modis_mod13q1_ndvi",
            source_id="X-MODIS-MOD13Q1",
            source_url=ndvi.get("source_url"),
            source_revision="MOD13Q1 v061",
            method_id="modis_ndvi_block_statistics",
            transformation_id="ndvi_modis.json (pipeline/fetch_modis_ndvi.py)",
            spatial_resolution=ndvi.get("spatial_resolution", "250 m"),
            validation_status="DERIVED",
            missing_policy="Only pixels with reliability 0 or 1; a date without a valid pixel stays null, never "
            "interpolated.",
            limitations=[Text(**ndvi["limitations"])],
        )
        place = modis_place()
        for key, title, unit in (
            ("median", Text(vi="NDVI MODIS, trung vị", en="MODIS NDVI, median"), "NDVI (unitless, -1 to 1)"),
            ("p25", Text(vi="NDVI MODIS, phân vị 25", en="MODIS NDVI, 25th percentile"), "NDVI (unitless, -1 to 1)"),
            ("p75", Text(vi="NDVI MODIS, phân vị 75", en="MODIS NDVI, 75th percentile"), "NDVI (unitless, -1 to 1)"),
            ("n_valid", Text(vi="Số điểm ảnh tốt (trên 81)", en="Valid pixels (of 81)"), "pixels"),
        ):
            modis.append(
                Series(
                    quantity=f"modis_ndvi_{key}",
                    title=title,
                    unit=unit,
                    periods=ndvi["dates"],
                    values=[None if v is None else float(v) for v in ndvi[key]],
                    place=place,
                    time_window=win,
                    provenance=prov,
                )
            )
    return SatelliteVegetation(
        sentinel2_status="available" if veg else "unavailable",
        sentinel2_place=do_luong_place() if veg else None,
        composites=composites,
        sentinel2_provenance=_s2_provenance(veg) if veg else None,
        modis_status="available" if ndvi else "unavailable",
        modis=modis,
        comparability=COMPARABILITY,
        unavailable=unavailable,
        limitations=[Text(**veg["limitations"])] if veg else [],
    )


# ---------------------------------------------------------------- coverage


def _window(a: date, b: date) -> TimeWindow:
    return TimeWindow(start=a, end=b)


def coverage() -> list[DatasetCoverage]:
    """Per catalog dataset: time span, footprint, row and scene counts, missing counts, and where they were read."""
    cat = canonical.load("catalog.json")
    clim = canonical.load("climate.json")
    veg = canonical.load_optional("vegetation.json")
    ndvi = canonical.load_optional("ndvi_modis.json")
    hz = canonical.load("hazards.json")
    soil = canonical.load("soil.json")
    model = canonical.load("model.json")
    status = _manifest("nasa_missions", "STATUS.json") or {}
    products = {f"nasa_{p['short_name'].lower()}": p for p in status.get("products", [])}
    farm = climate_series.farmland_place()
    nghe_an = nghe_an_place()
    district = do_luong_place()
    out = []
    for d in cat["datasets"]:
        did = d["dataset_id"]
        span, res, foot, counts, missing, read = (
            None,
            d["temporal_coverage"],
            None,
            {},
            {},
            ["data/canonical/catalog.json"],
        )
        if did == "nasa_power_daily":
            rows = [r for cell in clim["series"]["cells"].values() for r in cell.values()]
            files = sorted((RAW / "power").glob("power_*.json")) + sorted((RAW / "power_t2m").glob("power_*.json"))
            span, res, foot = (
                _window(date(1990, 1, 1), date(2024, 12, 31)),
                "daily (monthly and annual in canonical)",
                farm,
            )
            counts = {"cache_files": len(files), "cells": len(clim["cells"]), "canonical_years": len(clim["years"]),
                      "canonical_cell_years": len(rows)}  # fmt: skip
            missing = {
                "missing_months": sum(1 for r in rows for v in r["monthly_rain_mm"] if v is None),
                "missing_days_rain": sum(r["missing_days"]["PRECTOTCORR"] for r in rows),
                "missing_days_t2m_max": sum(r["missing_days"]["T2M_MAX"] for r in rows),
            }
            read += ["data/canonical/climate.json", "data/raw/power/", "data/raw/power_t2m/"]
        elif did == "chirps_v3_monthly":
            m = _manifest("chirps_v3", "MANIFEST.json") or {}
            span, res, foot = _window(date(1991, 1, 1), date(2024, 12, 31)), "monthly", farm
            counts = {"rows": m.get("row_count", 0), "areas": len((clim.get("chirps") or {}).get("cells", {})),
                      **{f"pixels_{k}": v for k, v in (m.get("pixels_per_cell") or {}).items()}}  # fmt: skip
            missing = {"rows_with_empty_precip": m.get("rows_with_empty_precip", 0),
                       "pixels_missing": m.get("selected_pixels_missing_total", 0),
                       "files_absent": len(m.get("absent_files", [])), "files_failed": len(m.get("failed_files", []))}  # fmt: skip
            read += ["data/raw/chirps_v3/MANIFEST.json", "data/canonical/climate.json"]
        elif did == "modis_mod13q1_ndvi":
            m = _manifest("modis_mod13q1", "MANIFEST.json") or {}
            if ndvi:
                span = _window(date.fromisoformat(ndvi["dates"][0]), date.fromisoformat(ndvi["dates"][-1]))
            res, foot = "16-day composites", modis_place()
            counts = {"dates": m.get("row_count_dates", 0), "pixel_rows": m.get("row_count_pixels", 0)}
            missing = {"pixels_invalid": m.get("pixels_invalid", 0),
                       "dates_without_valid_pixel": m.get("dates_without_valid_pixel", 0),
                       "dates_not_retrieved": len(m.get("dates_not_retrieved", []))}  # fmt: skip
            read += ["data/raw/modis_mod13q1/MANIFEST.json", "data/canonical/ndvi_modis.json"]
        elif did == "sentinel2_l2a_do_luong_vi":
            m = _manifest("sentinel2", "MANIFEST.json") or {}
            if veg:
                dates = sorted(s["date"] for s in veg["scenes"])
                span = _window(date.fromisoformat(dates[0]), date.fromisoformat(dates[-1]))
                counts = {"composites": len(veg["composites"])}
            res, foot = "per scene (5-day revisit, cloud-screened) and seasonal composites", district
            counts |= {k: v for k, v in (m.get("counts") or {}).items() if isinstance(v, int)}
            missing = {"scenes_skipped": len(m.get("skipped", []))}
            read += ["data/raw/sentinel2/MANIFEST.json", "data/canonical/vegetation.json"]
        elif did in ("geoboundaries_vnm_adm2_do_luong",):
            dl = (canonical.load_optional("geo_do_luong.json") or {}).get("do_luong") or {}
            res, foot = "static (boundary year 2020)", district
            counts = {"vertices_full": dl.get("n_vertices_full", 0), "vertices_web": dl.get("n_vertices_web", 0)}
            missing = {"commune_outlines": 1}
            read += ["data/canonical/geo_do_luong.json"]
        elif did == "geoboundaries_adm1":
            res, foot = "static", nghe_an
            counts = {"outline_rings": len(canonical.load("geo.json")["outline"])}
            read += ["data/canonical/geo.json"]
        elif did == "modis_farmland_weights":
            res, foot = "one fixed map", farm
            counts = {
                "weighted_cells": len(clim["cells"]),
                "grid_cells_in_geo": len(canonical.load("geo.json")["grid"]),
            }
            read += ["data/canonical/geo.json"]
        elif did == "e019_hazard_labels":
            span, res, foot = _window(date(hz["years"][0], 1, 1), date(hz["years"][-1], 12, 31)), "annual", farm
            counts = {"years": len(hz["years"]), "rules": len(hz["rules"]), "crops": len(hz["crops"])}
            missing = {"null_year_values": sum(1 for v in hz["year_level"].values() for x in v if x is None)}
            read += ["data/canonical/hazards.json"]
        elif did == "e020_soil_wetness":
            span, res, foot = _window(date(soil["years"][0], 1, 1), date(soil["years"][-1], 12, 31)), "annual", farm
            counts = {"years": len(soil["years"]), "crops": len(soil["crops"])}
            missing = {"null_values": sum(1 for c in soil["crops"].values() for x in c["values"] if x is None)}
            read += ["data/canonical/soil.json"]
        elif did == "e012_model":
            t = model["test_years"]
            span, res, foot = _window(date(t["first"], 1, 1), date(t["last"], 12, 31)), "annual", nghe_an
            counts = {"metric_rows": len(model["metrics"]), "gates": len(model["gates"])}
            read += ["data/canonical/model.json"]
        elif did == "nso_rice_yield":
            span, res, foot = _window(date(1995, 1, 1), date(2024, 12, 31)), "annual, per season", nghe_an
            read += ["data/reference/risk_table.json"]
        elif did in ("study_p02", "study_p03"):
            span, res = _window(date(2020, 6, 1), date(2021, 6, 30)), "one trial year"
            counts = {"plans": len(canonical.load("rotations.generated.json")["plans"])}
            read += ["data/canonical/rotations.generated.json"]
        elif did in products:
            p = products[did]
            res = p.get("native_resolution", d["spatial_resolution"])
            foot = district
            counts = {"granules_found_2020_2021": int(p.get("granules_found_2020_2021") or 0), "downloaded": 0}
            read += ["data/raw/nasa_missions/STATUS.json"]
        out.append(
            DatasetCoverage(
                dataset_id=did,
                title=Text(**d["title"]),
                ingestion_status=d["ingestion_status"],
                time_span=span,
                temporal_resolution=res,
                footprint=foot,
                spatial_resolution=d["spatial_resolution"],
                counts={k: int(v) for k, v in counts.items()},
                missing={k: int(v) for k, v in missing.items()},
                read_from=read,
                notes=[Text(**n) for n in d.get("notes", [])],
            )
        )
    return out


# ---------------------------------------------------------------- research documents


def research_documents() -> list[ResearchDocument]:
    passages = canonical.load("passages.json")["passages"]
    by_doc: dict[str, list[dict]] = {}
    for p in passages:
        by_doc.setdefault(p["doc_id"], []).append(p)
    cat = canonical.load("catalog.json")
    datasets = {d["dataset_id"]: d for d in cat["datasets"]}
    sources = {s["id"]: s for s in cat["sources"]}
    manifest = _manifest("documents", "MANIFEST.json") or {}
    full = {d["doc_id"]: d for d in manifest.get("documents", [])}
    out: list[ResearchDocument] = []
    for doc_id, ps in by_doc.items():
        first = ps[0]
        kinds = Counter(p["kind"] for p in ps)
        if doc_id in full and full[doc_id].get("status") == "INGESTED":
            d = full[doc_id]
            out.append(
                ResearchDocument(
                    doc_id=doc_id,
                    source_id=d["source_id"],
                    title=Text(vi=d["title"], en=d["title"]),
                    kind=kinds.most_common(1)[0][0],
                    status="full_text",
                    licence_basis=d["license"],
                    chunk_count=int(d.get("chunk_count") or 0),
                    passage_count=len(ps),
                    url=d.get("source_url"),
                    retrieved_at=d.get("retrieved_at"),
                    notes=[Text(vi=n, en=n) for n in d.get("notes", [])],
                )
            )
            continue
        if doc_id == "R-P02":
            continue  # listed once below with its recorded-only status
        if doc_id in datasets:
            d = datasets[doc_id]
            title, licence, status, url = Text(**d["title"]), d["license"], "generated", d.get("source_url")
        elif doc_id in sources and not doc_id.startswith("R-"):
            s = sources[doc_id]
            title, url = Text(**s["citation"]), s.get("url")
            licence, status = "Apache-2.0 (team-written description or computation)", "generated"
        elif doc_id in sources:
            s = sources[doc_id]
            title = Text(**s["citation"])
            licence = "Short quotations with their location, from the team rulebook (data/rules/sources.yaml)"
            status, url = "quotes_only", s.get("url")
        else:
            title = Text(**first["title"])
            licence = "Apache-2.0 (team computations and notes)"
            status, url = "generated", first.get("url")
        out.append(
            ResearchDocument(
                doc_id=doc_id,
                source_id=first["source_id"],
                title=title,
                kind=kinds.most_common(1)[0][0],
                status=status,
                licence_basis=licence,
                chunk_count=0,
                passage_count=len(ps),
                url=url,
                retrieved_at=None,
                notes=[],
            )
        )
    p02 = full.get("p02")
    if p02 is not None:
        out.append(
            ResearchDocument(
                doc_id="p02",
                source_id=p02["source_id"],
                title=Text(vi=p02["title"], en=p02["title"]),
                kind="study",
                status="recorded_only",
                licence_basis=p02["license"],
                chunk_count=0,
                passage_count=len(by_doc.get("R-P02", [])),
                url=p02.get("article_page"),
                retrieved_at=None,
                notes=[
                    Text(
                        vi="Toàn văn không được lưu vì tạp chí không cho phép sao chép; chỉ có các trích dẫn ngắn kèm "
                        "bảng và trang trong sổ quy tắc của nhóm.",
                        en="The full text is not stored because the journal does not allow copying; only short quotes "
                        "with their table and page from the team rulebook.",
                    )
                ],
            )
        )
    order = {"full_text": 0, "recorded_only": 1, "quotes_only": 2, "generated": 3}
    return sorted(out, key=lambda d: (order[d.status], d.doc_id))


# ---------------------------------------------------------------- AI capabilities


def _present(name: str) -> bool:
    return bool(os.getenv(name))


def capabilities() -> list[AiCapability]:
    """Each core's status. Environment variables are checked for presence only; values are never read out."""
    claude = _present("ANTHROPIC_API_KEY") and _present("ANTHROPIC_MODEL")
    netrc = any((Path.home() / n).exists() for n in (".netrc", "_netrc"))
    earthdata = (_present("EARTHDATA_USERNAME") and _present("EARTHDATA_PASSWORD")) or netrc
    ml_eval = climate_ml.EVAL_FILE.exists()
    return [
        AiCapability(
            core_id="climate",
            title=Text(vi="Lõi 01: khí hậu và học máy khí hậu", en="Core 01: climate intelligence and climate ML"),
            status="working",
            module="api/miaudow_api/climate.py, climate_series.py, climate_ml.py",
            can=[
                Text(
                    vi="Số liệu mưa, nắng nóng, rét, đợt khô của từng năm 1991-2024 kèm nguồn.",
                    en="Rain, heat, cold and dry-spell records of every year 1991-2024 with their source.",
                ),
                Text(
                    vi="Đặt mưa NASA POWER và CHIRPS cạnh nhau theo tháng.",
                    en="Show NASA POWER and CHIRPS monthly rain side by side.",
                ),
                Text(
                    vi="Tìm những năm đã qua giống một năm, và những năm có tháng mưa bất thường"
                    + ("" if ml_eval else " (chưa chạy bước đánh giá)")
                    + ".",
                    en="Find past years like a given year, and years with unusual rain months"
                    + ("" if ml_eval else " (evaluation not run yet)")
                    + ".",
                ),
            ],
            cannot=[
                Text(vi="Không dự báo thời tiết hay mùa vụ.", en="No weather or season forecast."),
                Text(
                    vi="Không có số đo tại ruộng; không chia nhỏ lưới NASA POWER xuống ruộng.",
                    en="No field measurement; the NASA POWER grid is never downscaled to a field.",
                ),
            ],
            credentials=[],
        ),
        AiCapability(
            core_id="evidence",
            title=Text(vi="Lõi 02: tìm bằng chứng", en="Core 02: evidence retrieval"),
            status="working",
            module="api/miaudow_api/evidence.py",
            can=[
                Text(
                    vi="Tìm đoạn văn trong quy định, nghiên cứu và số liệu của nhóm; từ chối khi không đủ liên quan.",
                    en="Find passages in regulations, studies and team data; abstains when nothing is relevant enough.",
                )
            ],
            cannot=[
                Text(
                    vi="Chưa có mô hình nhúng câu (tìm theo nghĩa); chỉ tìm theo từ.",
                    en="No sentence-embedding model (semantic search); lexical search only.",
                ),
                Text(
                    vi="Không có toàn văn bài báo P-02 (không được phép sao chép).",
                    en="No full text of the P-02 paper (copying not permitted).",
                ),
            ],
            credentials=[],
        ),
        AiCapability(
            core_id="decision",
            title=Text(vi="Lõi 03: so sánh cách trồng", en="Core 03: crop plan comparison"),
            status="working",
            module="api/miaudow_api/decision.py",
            can=[
                Text(
                    vi="Đặt sáu cách trồng đã thử ở Lưu Sơn cạnh nhau, theo thứ tự của nghiên cứu.",
                    en="Lay out the six plans tried in Lưu Sơn side by side, in the study's order.",
                )
            ],
            cannot=[
                Text(
                    vi="Không xếp hạng, không chấm điểm, không chọn thay gia đình.",
                    en="No ranking, no scoring, no choice made for the family.",
                ),
                Text(
                    vi="Không biết đất, nước, giá bán và nhân công của từng ruộng.",
                    en="Does not know each field's soil, water, prices or labour.",
                ),
            ],
            credentials=[],
        ),
        AiCapability(
            core_id="copilot",
            title=Text(vi="Lõi 04: trợ lý hỏi đáp", en="Core 04: copilot"),
            status="working" if claude else "deterministic",
            module="api/miaudow_api/copilot.py",
            can=[
                Text(
                    vi="Trả lời từ các công cụ dữ liệu; mọi con số được kiểm tra lại với kết quả công cụ.",
                    en="Answers from the data tools; every number is checked against the tool results.",
                ),
                Text(
                    vi="Claude viết câu trả lời."
                    if claude
                    else "Ghép câu trả lời bằng câu cố định (chưa cấu hình Claude).",
                    en="Claude writes the answer."
                    if claude
                    else "Assembles answers from fixed sentences (Claude not configured).",
                ),
            ],
            cannot=[
                Text(
                    vi="Không dự báo, không báo giá hôm nay, không xếp hạng.",
                    en="No forecast, no current price, no ranking.",
                ),
            ],
            credentials=[
                Credential(
                    env_var="ANTHROPIC_API_KEY",
                    present=_present("ANTHROPIC_API_KEY"),
                    purpose=Text(vi="Khóa Claude, chỉ ở máy chủ.", en="Claude key, server only."),
                ),
                Credential(
                    env_var="ANTHROPIC_MODEL",
                    present=_present("ANTHROPIC_MODEL"),
                    purpose=Text(vi="Mã mô hình Claude được bật.", en="The enabled Claude model id."),
                ),
            ],
        ),
        AiCapability(
            core_id="satellite_missions",
            title=Text(
                vi="Sản phẩm NASA Earthdata (HLS, SMAP, GPM IMERG, ECOSTRESS)",
                en="NASA Earthdata products (HLS, SMAP, GPM IMERG, ECOSTRESS)",
            ),
            status="working" if earthdata else "blocked",
            module="pipeline/fetch_nasa_missions.py",
            can=[
                Text(
                    vi="Đã tìm thấy các tệp phủ Đô Lương qua NASA CMR.",
                    en="Granules over Đô Lương were found through NASA CMR.",
                )
            ],
            cannot=[
                Text(
                    vi="Chưa tải về nên chưa dùng số nào từ các sản phẩm này.",
                    en="Not downloaded, so no number from these products is used.",
                )
            ],
            credentials=[
                Credential(
                    env_var="EARTHDATA_USERNAME",
                    present=_present("EARTHDATA_USERNAME"),
                    purpose=Text(vi="Tài khoản Earthdata miễn phí.", en="Free Earthdata Login account."),
                ),
                Credential(
                    env_var="EARTHDATA_PASSWORD",
                    present=_present("EARTHDATA_PASSWORD"),
                    purpose=Text(vi="Mật khẩu Earthdata.", en="Earthdata password."),
                ),
                Credential(
                    env_var=".netrc",
                    present=netrc,
                    purpose=Text(
                        vi="Hoặc một dòng urs.earthdata.nasa.gov trong tệp .netrc.",
                        en="Or a urs.earthdata.nasa.gov entry in a .netrc file.",
                    ),
                ),
            ],
        ),
    ]


# ---------------------------------------------------------------- model evaluations


def _e012_summary(model: dict) -> dict:
    rows = [
        {k: m[k] for k in ("model_id", "season", "role", "rmse", "mae", "r2_oos", "skill_vs_b0", "skill_vs_bnw",
                           "coverage_80", "n_rows", "n_test_years")}
        for m in model["metrics"]
        if m["model_id"] == "m1_ridge" and m["scheme"] == "rolling_origin" and m["subset"] == "national"
    ]  # fmt: skip
    return {
        "freeze_commit": model["freeze_commit"],
        "test_years": model["test_years"],
        "seasons": model["seasons"],
        "gates": [{k: g[k] for k in ("gate", "season", "model_id", "passed", "detail")} for g in model["gates"]],
        "primary_model_rolling_origin_national": rows,
        "units": {"rmse": "yield anomaly (share of normal yield)", "skill": "1 - MSE_model / MSE_reference"},
    }


def model_evaluations() -> list[ModelEvaluation]:
    out: list[ModelEvaluation] = []
    model = canonical.load("model.json")
    out.append(
        ModelEvaluation(
            evaluation_id="E-012",
            core="climate",
            title=Text(
                vi="Mô hình năng suất lúa theo thời tiết (E-012), thử trên các năm 2016-2024",
                en="Weather-based rice yield model (E-012), tested on 2016-2024",
            ),
            status="available",
            source_file="data/canonical/model.json",
            summary=_e012_summary(model),
            verdict=Text(
                vi="Vụ đông xuân: không hiển thị dự đoán (không hơn mô hình không dùng thời tiết). Vụ mùa: hiển thị "
                "kèm khoảng tin cậy. Vụ hè thu: không đủ số liệu để làm mô hình.",
                en="Spring: no prediction shown (no skill over the no-weather model). Winter: shown with its interval. "
                "Summer-autumn: not modelled (too little data).",
            ),
            limitations=[
                Text(
                    vi="Kết quả của nhóm, không huấn luyện lại ở đây.",
                    en="Team results, not retrained here.",
                )
            ],
        )
    )
    if RETRIEVAL_RESULTS.exists():
        r = json.loads(RETRIEVAL_RESULTS.read_text(encoding="utf-8"))
        test = r["test"]
        out.append(
            ModelEvaluation(
                evaluation_id="retrieval_2026-11-14",
                core="evidence",
                title=Text(vi="Đánh giá tìm bằng chứng (phần TEST)", en="Evidence retrieval benchmark (TEST split)"),
                status="available",
                source_file=_rel(RETRIEVAL_RESULTS),
                summary={
                    "n_questions": r["n_questions"],
                    "method": r["method"],
                    "thresholds_in_use": r["thresholds_in_use"],
                    "ranking": {k: v for k, v in test["ranking"].items() if k != "misses_at_3"},
                    "abstention_with_guard": {k: v for k, v in test["abstention_with_guard"].items() if k != "errors"},
                    "abstention_without_guard": {
                        k: v for k, v in test["abstention_without_guard"].items() if k != "errors"
                    },
                },
                verdict=None,
                limitations=[
                    Text(
                        vi="Bộ câu hỏi nhỏ do nhóm viết, nên số liệu còn nhiễu.",
                        en="A small question set written by the team, so the numbers are noisy.",
                    )
                ],
            )
        )
    else:
        out.append(
            _missing_eval(
                "retrieval_2026-11-14",
                "evidence",
                RETRIEVAL_RESULTS,
                r".venv\Scripts\python api/eval/run_retrieval_eval.py",
            )
        )
    stored = climate_ml.stored_evaluation()
    if stored is None:
        out.append(_missing_eval("climate_ml_2026-11-14", "climate", climate_ml.EVAL_FILE, climate_ml.EVAL_COMMAND))
    else:
        metrics = stored["model"]["metrics"]
        out.append(
            ModelEvaluation(
                evaluation_id="climate_ml_2026-11-14",
                core="climate",
                title=Text(
                    vi="Học máy khí hậu: năm tương tự và năm bất thường",
                    en="Climate ML: analog years and unusual years",
                ),
                status="available",
                source_file=_rel(climate_ml.EVAL_FILE),
                summary={
                    "version": stored["model"]["version"],
                    "inputs": stored["model"]["inputs"],
                    "training_years": stored["model"]["training_years"],
                    "analogs_proxy": metrics["analogs_proxy"],
                    "analogs_out_of_sample": metrics["analogs_out_of_sample"],
                    "anomalies_agreement_all_years": metrics["anomalies_agreement_all_years"],
                    "anomalies_chirps_cross_check": metrics["anomalies_chirps_cross_check"],
                    "analog_beats_baselines": stored["analog_summary"]["beats_baselines"],
                },
                verdict=Text(**stored["analog_summary"]["verdict"]),
                limitations=[Text(**x) for x in stored["model"]["limitations"]],
            )
        )
    return out


def _missing_eval(eid: str, core: str, path: Path, command: str) -> ModelEvaluation:
    return ModelEvaluation(
        evaluation_id=eid,
        core=core,
        title=Text(vi="Chưa có kết quả đánh giá", en="No evaluation result yet"),
        status="unavailable",
        source_file=_rel(path),
        summary={"how_to_fix": command},
        verdict=None,
        limitations=[],
    )


# ---------------------------------------------------------------- provenance (copilot tool)


def dataset(dataset_id: str) -> dict:
    cat = canonical.load("catalog.json")
    found = next((d for d in cat["datasets"] if d["dataset_id"] == dataset_id), None)
    if found is None:
        raise NotFound(f"unknown dataset {dataset_id!r}; known: {', '.join(d['dataset_id'] for d in cat['datasets'])}")
    return found
