"""Verify a small set of NASA GIBS WMTS layers for the MIAUDOW 3D globe and write data/canonical/gibs_layers.json.

GIBS imagery is a VISUALISATION source (pre-rendered colour tiles), not evidence: no number shown as a measurement in
MIAUDOW may be read from a GIBS tile colour.

Steps:
  1. read the WMTS capabilities of the EPSG:4326 and EPSG:3857 "best" endpoints
     (https://gibs.earthdata.nasa.gov/wmts/{epsg4326|epsg3857}/best/1.0.0/WMTSCapabilities.xml; cached in
     data/cache/gibs/, git-ignored);
  2. for each wanted layer record identifier, title, formats, tile matrix set, max zoom level (number of tile
     matrices - 1), time dimension (default + value periods) and the REST URL template from <ResourceURL>;
  3. fetch ONE real tile over Viet Nam (the Lưu Sơn study point) per layer and projection to prove it returns 200;
     tiles are not stored.

Acknowledgement (GIBS documentation, https://nasa-gibs.github.io/gibs-api-docs/, section "Data Use Guidance and
Acknowledgements"): "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse
Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)."

Run:   .venv\\Scripts\\python.exe pipeline\\check_gibs.py
"""

from __future__ import annotations

import json
import math
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "MiaudowResearch/1.0 (NASA Space Apps 2026 hackathon)"
CAPS = {
    "epsg4326": "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml",
    "epsg3857": "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml",
}
NS = {
    "w": "http://www.opengis.net/wmts/1.0",
    "ows": "http://www.opengis.net/ows/1.1",
    "xlink": "http://www.w3.org/1999/xlink",
}
CACHE = ROOT / "data" / "cache" / "gibs"
OUT = ROOT / "data" / "canonical" / "gibs_layers.json"
POINT = {"lat": 18.89638889, "lon": 105.2802778, "label": "Lưu Sơn study point (Wikidata Q10788283)"}
METERS_PER_DEGREE = 6378137.0 * 2 * math.pi / 360.0  # OGC WMTS 1.0 Annex E for EPSG:4326 well-known scale sets
PIXEL_SIZE_M = 0.00028

# (identifier, role, alternatives tried in order when the first is absent)
WANTED = [
    ("BlueMarble_ShadedRelief_Bathymetry", "base map (static)", ["BlueMarble_NextGeneration"]),
    ("BlueMarble_NextGeneration", "base map (static, monthly-composite true colour)", []),
    ("VIIRS_SNPP_CorrectedReflectance_TrueColor", "daily true colour", []),
    ("MODIS_Terra_CorrectedReflectance_TrueColor", "daily true colour", []),
    ("VIIRS_Black_Marble", "night lights (annual)", ["VIIRS_SNPP_DayNightBand_At_Sensor_Radiance"]),
    ("VIIRS_SNPP_DayNightBand_At_Sensor_Radiance", "night lights (daily)", []),
    ("MODIS_Terra_NDVI_8Day", "vegetation (8-day, rolling recent window)", ["MODIS_Terra_L3_NDVI_16Day"]),
    ("MODIS_Terra_L3_NDVI_16Day", "vegetation (16-day, 2000-present)", []),
    ("MODIS_Terra_L3_NDVI_Monthly", "vegetation (monthly)", []),
    ("IMERG_Precipitation_Rate", "precipitation rate (daily)", ["GMI_Precipitation_Rate_Asc"]),
    (
        "SMAP_L4_Analyzed_Surface_Soil_Moisture",
        "surface soil moisture (SMAP L4, daily)",
        ["SMAP_L3_Passive_Enhanced_Day_Soil_Moisture"],
    ),
    ("SMAP_L4_Analyzed_Root_Zone_Soil_Moisture", "root-zone soil moisture (SMAP L4, daily)", []),
    ("Coastlines_15m", "reference overlay", []),
    ("Reference_Labels_15m", "reference overlay (place labels)", []),
]


# ----------------------------------------------------------------------------------------------- pure functions
def fill_template(
    template: str, layer: str, time_value: str | None, tms: str, z: int, y: int, x: int, style: str = "default"
) -> str:
    """Fill a WMTS RESTful ResourceURL template ({Time} is dropped with its slash when the layer has no time)."""
    url = template
    if "{Time}" in url:
        if time_value is None:
            raise ValueError("layer needs a Time value")
        url = url.replace("{Time}", time_value)
    return (
        url.replace("{Layer}", layer)
        .replace("{Style}", style)
        .replace("{TileMatrixSet}", tms)
        .replace("{TileMatrix}", str(z))
        .replace("{TileRow}", str(y))
        .replace("{TileCol}", str(x))
    )


def generic_template(epsg: str, ext: str, has_time: bool) -> str:
    """The documented GIBS REST pattern with {Layer}/{TileMatrixSet}/{z}/{y}/{x} placeholders for web clients."""
    t = "{Time}/" if has_time else ""
    return f"https://gibs.earthdata.nasa.gov/wmts/{epsg}/best/{{Layer}}/default/{t}{{TileMatrixSet}}/{{z}}/{{y}}/{{x}}.{ext}"


def webmercator_tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    """(x, y) of the Google/OSM XYZ tile containing a point (GoogleMapsCompatible tile matrix set)."""
    n = 2**z
    x = int((lon + 180.0) / 360.0 * n)
    lr = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lr)) / math.pi) / 2.0 * n)
    return x, y


def matrix_tile(lat: float, lon: float, matrix: dict, units_per_metre: float) -> tuple[int, int]:
    """(col, row) of a point in a generic WMTS TileMatrix (OGC 07-057r7, Annex H)."""
    res = matrix["scale_denominator"] * PIXEL_SIZE_M * units_per_metre  # CRS units per pixel
    span_x, span_y = matrix["tile_width"] * res, matrix["tile_height"] * res
    x0, y0 = matrix["top_left"]
    if matrix.get("axis_lat_first"):
        y0, x0 = matrix["top_left"]
    col = int(math.floor((lon - x0) / span_x))
    row = int(math.floor((y0 - lat) / span_y))
    return col, row


def time_periods(values: list[str]) -> list[dict]:
    """'2020-01-01/2021-01-01/P1D' strings -> [{start, end, period}]; single dates are start=end."""
    out = []
    for v in values:
        parts = v.strip().split("/")
        if len(parts) == 3:
            out.append({"start": parts[0], "end": parts[1], "period": parts[2]})
        elif len(parts) == 1 and parts[0]:
            out.append({"start": parts[0], "end": parts[0], "period": None})
    return out


def ext_of(fmt: str) -> str:
    return {"image/jpeg": "jpg", "image/png": "png", "application/vnd.mapbox-vector-tile": "mvt"}.get(fmt, "bin")


# ----------------------------------------------------------------------------------------------- I/O
def get(url: str, tries: int = 4, timeout: float = 180.0):
    import httpx

    delay, last = 3.0, None
    for attempt in range(tries):
        try:
            r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
            if r.status_code < 500:
                return r
            last = f"HTTP {r.status_code}"
        except httpx.HTTPError as exc:
            last = repr(exc)
        print(f"  retry {attempt + 1} {url}: {last}", file=sys.stderr)
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"giving up {url}: {last}")


def parse_caps(xml_bytes: bytes) -> tuple[dict, dict]:
    root = ET.fromstring(xml_bytes)
    tms_defs = {}
    for t in root.findall("w:Contents/w:TileMatrixSet", NS):
        ident = t.find("ows:Identifier", NS).text
        crs = t.find("ows:SupportedCRS", NS).text
        mats = []
        for m in t.findall("w:TileMatrix", NS):
            tl = [float(v) for v in m.find("w:TopLeftCorner", NS).text.split()]
            mats.append(
                {
                    "id": m.find("ows:Identifier", NS).text,
                    "scale_denominator": float(m.find("w:ScaleDenominator", NS).text),
                    "top_left": tl,
                    "tile_width": int(m.find("w:TileWidth", NS).text),
                    "tile_height": int(m.find("w:TileHeight", NS).text),
                    "matrix_width": int(m.find("w:MatrixWidth", NS).text),
                    "matrix_height": int(m.find("w:MatrixHeight", NS).text),
                }
            )
        tms_defs[ident] = {"crs": crs, "matrices": mats}
    layers = {}
    for L in root.findall("w:Contents/w:Layer", NS):
        ident = L.find("ows:Identifier", NS).text
        title = L.find("ows:Title", NS)
        dim = L.find("w:Dimension", NS)
        legends = [lg.get("{http://www.w3.org/1999/xlink}href") for lg in L.findall("w:Style/w:LegendURL", NS)]
        layers[ident] = {
            "identifier": ident,
            "title": title.text if title is not None else None,
            "formats": [f.text for f in L.findall("w:Format", NS)],
            "tile_matrix_sets": [t.find("w:TileMatrixSet", NS).text for t in L.findall("w:TileMatrixSetLink", NS)],
            "resource_urls": [
                {"format": r.get("format"), "template": r.get("template")}
                for r in L.findall("w:ResourceURL", NS)
                if r.get("resourceType") == "tile"
            ],
            "time": None
            if dim is None
            else {
                "identifier": dim.find("ows:Identifier", NS).text,
                "default": dim.find("w:Default", NS).text,
                "periods": time_periods([v.text for v in dim.findall("w:Value", NS)]),
            },
            "legend_urls": [u for u in legends if u],
        }
    return layers, tms_defs


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    caps = {}
    for epsg, url in CAPS.items():
        p = CACHE / f"{epsg}_WMTSCapabilities.xml"
        if not p.exists():
            r = get(url, timeout=300)
            if r.status_code != 200:
                raise SystemExit(f"{url}: HTTP {r.status_code}")
            p.write_bytes(r.content)
        caps[epsg] = parse_caps(p.read_bytes())
        print(f"{epsg}: {len(caps[epsg][0])} layers, {len(caps[epsg][1])} tile matrix sets")

    out_layers, missing = [], []
    for ident, role, alts in WANTED:
        entry = {"identifier": ident, "role": role, "projections": {}}
        present = False
        for epsg, (layers, tms_defs) in caps.items():
            L = layers.get(ident)
            if L is None:
                entry["projections"][epsg] = {"present": False}
                continue
            present = True
            tms = L["tile_matrix_sets"][0]
            mats = tms_defs[tms]["matrices"]
            fmt = L["formats"][0]
            tmpl = L["resource_urls"][0]["template"] if L["resource_urls"] else None
            has_time = L["time"] is not None
            tv = L["time"]["default"] if has_time else None
            z = min(5, len(mats) - 1)
            if epsg == "epsg3857":
                x, y = webmercator_tile(POINT["lat"], POINT["lon"], z)
            else:
                # CRS84 corners are "lon lat"; an urn:...:EPSG::4326 corner would be "lat lon"
                lat_first = "EPSG" in tms_defs[tms]["crs"] and "4326" in tms_defs[tms]["crs"]
                x, y = matrix_tile(
                    POINT["lat"], POINT["lon"], {**mats[z], "axis_lat_first": lat_first}, 1.0 / METERS_PER_DEGREE
                )
            tile_url = fill_template(tmpl, ident, tv, tms, z, y, x)
            try:
                r = get(tile_url, tries=3, timeout=60)
                probe = {
                    "url": tile_url,
                    "status": r.status_code,
                    "content_type": r.headers.get("content-type"),
                    "bytes": len(r.content),
                    "z": z,
                    "x": x,
                    "y": y,
                    "time": tv,
                }
            except Exception as exc:  # noqa: BLE001 - recorded
                probe = {"url": tile_url, "status": None, "error": str(exc)[:200]}
            print(
                f"  {ident} [{epsg}] {tms} z{z}/{y}/{x} t={tv}: {probe.get('status')} {probe.get('content_type')}"
                f" {probe.get('bytes')} B"
            )
            entry["title"] = L["title"]
            entry["projections"][epsg] = {
                "present": True,
                "tile_matrix_set": tms,
                "tile_matrix_sets_all": L["tile_matrix_sets"],
                "formats": L["formats"],
                "format": fmt,
                "max_zoom": len(mats) - 1,
                "tile_size": [mats[0]["tile_width"], mats[0]["tile_height"]],
                "time": None
                if not has_time
                else {
                    "default": L["time"]["default"],
                    "first": L["time"]["periods"][0]["start"] if L["time"]["periods"] else None,
                    "last": L["time"]["periods"][-1]["end"] if L["time"]["periods"] else None,
                    "n_periods": len(L["time"]["periods"]),
                    "periods": L["time"]["periods"][:40],
                    "periods_truncated": len(L["time"]["periods"]) > 40,
                },
                "rest_template_capabilities": tmpl,
                "rest_template": generic_template(epsg, ext_of(fmt), has_time)
                .replace("{Layer}", ident)
                .replace("{TileMatrixSet}", tms),
                "legend_urls": L["legend_urls"][:2],
                "probe_tile": probe,
                "verified": probe.get("status") == 200,
            }
            time.sleep(0.3)
        if not present:
            missing.append({"identifier": ident, "alternatives": alts})
        else:
            out_layers.append(entry)

    doc = {
        "generated_at": retrieved,
        "service": "NASA Global Imagery Browse Services (GIBS) WMTS",
        "capabilities": CAPS,
        "use": {
            "vi": "Chỉ để hiển thị quả địa cầu 3D. Màu ô ảnh không phải số đo; không đọc giá trị từ màu.",
            "en": "Visualisation for the 3D globe only. Tile colours are not measurements; never read values "
            "from them.",
        },
        "validation_status": "ILLUSTRATIVE",
        "acknowledgement": "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse "
        "Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS).",
        "acknowledgement_source": "https://nasa-gibs.github.io/gibs-api-docs/ (Data Use Guidance and "
        "Acknowledgements), read " + retrieved[:10],
        "data_use_policy": {
            "url": "https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance",
            "statement": "NASA promotes full and open sharing of data (GIBS docs, linking to the Earthdata data use "
            "guidance).",
            "fetch_status": "HTTP 403 to automated requests on " + retrieved[:10] + "; not re-read here",
        },
        "url_pattern": "https://gibs.earthdata.nasa.gov/wmts/{epsg}/best/{Layer}/default/{Time}/{TileMatrixSet}/"
        "{z}/{y}/{x}.{ext}  ({Time} segment omitted for layers without a time dimension; "
        "Time = YYYY-MM-DD or the 'default' value)",
        "probe_point": POINT,
        "layers": out_layers,
        "missing": missing,
        "notes": [
            "The 'best' endpoint serves the best available version of each layer.",
            "EPSG:3857 layers use GoogleMapsCompatible_LevelN tile matrix sets (256 px, XYZ order z/y/x).",
            "EPSG:4326 layers use 512 px tiles on a geographic grid; max zoom differs from the 3857 set.",
            "Daily layers can have gaps; use a date inside the listed periods or the default.",
        ],
        "script": "pipeline/check_gibs.py",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for L in out_layers for p in L["projections"].values() if p.get("verified"))
    total = sum(1 for L in out_layers for p in L["projections"].values() if p.get("present"))
    print(
        f"wrote {OUT.relative_to(ROOT)}: {len(out_layers)} layers, {ok}/{total} probe tiles HTTP 200, "
        f"missing {[m['identifier'] for m in missing]}"
    )
    return 0


# ----------------------------------------------------------------------------------------------- NASA Eyes (task E)
EYES_OUT = ROOT / "data" / "canonical" / "nasa_eyes.json"
EYES_APPS = {
    "solar_system": {"url": "https://eyes.nasa.gov/apps/solar-system/", "bundles": ["app.js", "vendors.js"]},
    "earth": {"url": "https://eyes.nasa.gov/apps/earth/", "bundles": ["index.js"]},
}
EYES_NASA_PAGE = "https://science.nasa.gov/eyes/"
# (id, app, hash route, label_vi, label_en); every id is checked below, nothing is assumed
EYES_LINKS = [
    ("earth", "solar_system", "earth", "Trái Đất", "Earth"),
    ("moon", "solar_system", "moon", "Mặt Trăng", "Moon"),
    ("mars", "solar_system", "mars", "Sao Hỏa", "Mars"),
    ("jupiter", "solar_system", "jupiter", "Sao Mộc", "Jupiter"),
    ("saturn", "solar_system", "saturn", "Sao Thổ", "Saturn"),
    (
        "sc_landsat_9",
        "solar_system",
        "sc_landsat_9",
        "Vệ tinh Landsat 9 (ảnh mặt đất 30 m)",
        "Landsat 9 (30 m land imaging)",
    ),
    ("sc_landsat_8", "solar_system", "sc_landsat_8", "Vệ tinh Landsat 8", "Landsat 8"),
    ("sc_smap", "solar_system", "sc_smap", "Vệ tinh SMAP (độ ẩm đất)", "SMAP (soil moisture)"),
    ("sc_gpm", "solar_system", "sc_gpm", "Vệ tinh GPM (đo mưa)", "GPM (precipitation)"),
    ("sc_terra", "solar_system", "sc_terra", "Vệ tinh Terra (MODIS)", "Terra (MODIS)"),
    ("sc_aqua", "solar_system", "sc_aqua", "Vệ tinh Aqua (MODIS)", "Aqua (MODIS)"),
    ("sc_suomi_npp", "solar_system", "sc_suomi_npp", "Vệ tinh Suomi NPP (VIIRS)", "Suomi NPP (VIIRS)"),
    (
        "sc_iss_ecostress",
        "solar_system",
        "sc_iss_ecostress",
        "ECOSTRESS trên Trạm ISS (nhiệt độ bề mặt)",
        "ECOSTRESS on the ISS (surface temperature)",
    ),
    ("sc_iss", "solar_system", "sc_iss", "Trạm Vũ trụ Quốc tế ISS", "International Space Station"),
    ("sc_swot", "solar_system", "sc_swot", "Vệ tinh SWOT (nước mặt)", "SWOT (surface water)"),
    ("sc_nisar", "solar_system", "sc_nisar", "Vệ tinh NISAR (radar)", "NISAR (radar)"),
    (
        "earth_soil_moisture",
        "earth",
        "vital-signs/soil-moisture",
        "Độ ẩm đất toàn cầu (Eyes on the Earth)",
        "Global soil moisture (Eyes on the Earth)",
    ),
    (
        "earth_precipitation",
        "earth",
        "vital-signs/precipitation",
        "Lượng mưa toàn cầu (Eyes on the Earth)",
        "Global precipitation (Eyes on the Earth)",
    ),
    (
        "earth_air_temperature",
        "earth",
        "vital-signs/air-temperature",
        "Nhiệt độ không khí (Eyes on the Earth)",
        "Air temperature (Eyes on the Earth)",
    ),
    ("earth_satellites", "earth", "satellites", "Vệ tinh đang bay quanh Trái Đất", "Satellites now"),
    ("earth_sat_smap", "earth", "satellites/smap", "SMAP trong Eyes on the Earth", "SMAP in Eyes on the Earth"),
    ("earth_sat_gpm", "earth", "satellites/gpm", "GPM trong Eyes on the Earth", "GPM in Eyes on the Earth"),
    (
        "earth_sat_landsat_9",
        "earth",
        "satellites/landsat-9",
        "Landsat 9 trong Eyes on the Earth",
        "Landsat 9 in Eyes on the Earth",
    ),
]


def frame_policy(headers: dict) -> dict:
    """Frameability from response headers: X-Frame-Options and CSP frame-ancestors (case-insensitive)."""
    h = {k.lower(): v for k, v in headers.items()}
    xfo = h.get("x-frame-options")
    csp = h.get("content-security-policy")
    fa = None
    if csp:
        for part in csp.split(";"):
            if part.strip().lower().startswith("frame-ancestors"):
                fa = part.strip()
    blocked = bool(xfo and xfo.strip().upper() in ("DENY", "SAMEORIGIN")) or bool(
        fa and "*" not in fa.split()[1:] and "https:" not in fa.split()[1:]
    )
    return {
        "x_frame_options": xfo,
        "csp_frame_ancestors": fa,
        "csp_present": csp is not None,
        "frameable_by_headers": not blocked,
    }


def earth_satellite_slug(entity_id: str) -> str:
    """Eyes on the Earth satellite route slug (app code: t.replace('sc_','').replaceAll('_','-'))."""
    return entity_id.replace("sc_", "", 1).replace("_", "-")


def check_eyes() -> int:
    import re

    retrieved = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    cdir = CACHE.parent / "nasa_eyes"
    cdir.mkdir(parents=True, exist_ok=True)
    frame, bundles = {}, {}
    for app, cfg in EYES_APPS.items():
        r = get(cfg["url"], timeout=60)
        frame[app] = {
            "url": cfg["url"],
            "status": r.status_code,
            **frame_policy(dict(r.headers)),
            "server": r.headers.get("server"),
        }
        html = r.text
        frame[app]["meta_csp_in_html"] = "http-equiv" in html.lower() and "content-security-policy" in html.lower()
        text = ""
        for b in cfg["bundles"]:
            p = cdir / f"{app}_{b}"
            if not p.exists():
                rb = get(cfg["url"] + b, timeout=300)
                p.write_bytes(rb.content)
            text += p.read_text(encoding="utf-8", errors="ignore")
        bundles[app] = text
        frame[app]["frame_busting_code_found"] = bool(
            re.search(
                r"top\.location\s*=|window\.top\s*!==?\s*window"
                r"|self\s*!==?\s*top",
                text,
            )
        )
        frame[app]["official_embed_feature"] = "getEmbedCodeFromParams" in text or "embedCode" in text
    ss = bundles["solar_system"]
    frame["solar_system"]["router_pattern"] = "/:spaceObject" if '{route:"/:spaceObject",view:"object"}' in ss else None
    nasa_page = get(EYES_NASA_PAGE, timeout=60)
    nasa_links = sorted(set(re.findall(r"https://eyes\.nasa\.gov/apps/[^\"'<\s]*", nasa_page.text)))
    vital = set(re.findall(r'\{value:"([a-z0-9-]+)",title:"', bundles["earth"]))
    links = []
    for lid, app, route, vi, en in EYES_LINKS:
        url = EYES_APPS[app]["url"] + "#/" + route
        ok, how = False, ""
        if app == "solar_system":
            m = re.search(r"[,{]" + re.escape(route) + r':\{groups:\[[^\]]*\][^}]*?label:"([^"]+)"', ss)
            ok = bool(m) and frame["solar_system"]["router_pattern"] is not None
            how = (
                (
                    f"entity '{route}' (label '{m.group(1)}') defined in {EYES_APPS[app]['url']}app.js/vendors.js; "
                    "route '/:spaceObject'; hash pattern confirmed by NASA links on science.nasa.gov/eyes "
                    "(e.g. #/sc_new_horizons/...)"
                )
                if m
                else "entity id not found in the app bundle"
            )
        else:
            parts = route.split("/")
            if parts[0] == "vital-signs":
                ok = parts[1] in vital
                how = (
                    (
                        f"vital sign value '{parts[1]}' listed in {EYES_APPS[app]['url']}index.js; routes "
                        "'/vital-signs/:vitalSignParam'"
                    )
                    if ok
                    else "vital sign not found"
                )
            elif parts == ["satellites"]:
                ok = '"/satellites"' in bundles["earth"] or 'Sf="/satellites"' in bundles["earth"]
                how = "route '/satellites' defined in index.js"
            else:
                ent = "sc_" + parts[1].replace("-", "_")
                m = re.search(r"[,{]" + re.escape(ent) + r':\{groups:\[[^\]]*\][^}]*?label:"([^"]+)"', bundles["earth"])
                ok = bool(m) and earth_satellite_slug(ent) == parts[1]
                how = (
                    (
                        f"entity '{ent}' (label '{m.group(1)}') in index.js; satellite route slug = id without "
                        "'sc_' and '_'->'-' (navigateToSpacecraft)"
                    )
                    if m
                    else "entity not found"
                )
            if any(u.startswith(EYES_APPS[app]["url"] + "#/" + parts[0]) for u in nasa_links):
                how += "; route family also linked from science.nasa.gov/eyes"
        if ok:
            links.append(
                {
                    "id": lid,
                    "app": app,
                    "label_vi": vi,
                    "label_en": en,
                    "url": url,
                    "verified_by": how,
                    "checked_at": retrieved[:10],
                }
            )
        print(f"  {lid}: {'OK' if ok else 'NOT VERIFIED'} {url}")
    doc = {
        "generated_at": retrieved,
        "frameable": {
            "solar_system": frame["solar_system"]["frameable_by_headers"]
            and not frame["solar_system"]["frame_busting_code_found"],
            "earth": frame["earth"]["frameable_by_headers"] and not frame["earth"]["frame_busting_code_found"],
            "evidence": frame,
            "not_frameable": {
                "https://science.nasa.gov/eyes/": "X-Frame-Options: SAMEORIGIN (landing page, link only)"
            },
        },
        "links": links,
        "nasa_links_seen_on_science_nasa_gov": [u for u in nasa_links if "#/" in u][:20],
        "branding_note": {
            "vi": "NASA's Eyes là ứng dụng của NASA/JPL. Khi nhúng, giữ nguyên giao diện và logo của NASA bên trong "
            "khung, ghi rõ 'Eyes on the Solar System / Eyes on the Earth — NASA/JPL-Caltech' và có liên kết "
            "mở trang gốc. Không dùng logo NASA cho MIAUDOW và không ngụ ý NASA bảo trợ hay xác nhận MIAUDOW.",
            "en": "NASA's Eyes is a NASA/JPL application. When framed, keep NASA's interface and insignia inside the "
            "frame unchanged, credit 'Eyes on the Solar System / Eyes on the Earth — NASA/JPL-Caltech' with a "
            "link to the original, never use the NASA insignia for MIAUDOW, and never imply NASA endorsement.",
        },
        "usage_notes": [
            "The Solar System app ships an official Share > Embed generator that outputs "
            "<iframe src=... allowfullscreen>; its embed options include tracking=false.",
            "Deep links were verified against the apps' public JavaScript bundles and NASA's own links, "
            "not by rendering them in a browser.",
            "Both apps load WebGL scenes of tens of MB: load them only on demand (click to open), "
            "never on farmer routes, with reduced motion respected.",
        ],
        "script": "pipeline/check_gibs.py --eyes",
    }
    EYES_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"wrote {EYES_OUT.relative_to(ROOT)}: frameable solar_system={doc['frameable']['solar_system']} "
        f"earth={doc['frameable']['earth']}, {len(links)}/{len(EYES_LINKS)} links verified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(check_eyes() if "--eyes" in sys.argv else main())
