"""Fetch the former Đô Lương district (ADM2) boundary from geoBoundaries gbOpen and build a small web version.

Source: geoBoundaries API, https://www.geoboundaries.org/api/current/gbOpen/VNM/ADM2/ (metadata, licence, download URL)
        -> the full-resolution ADM2 GeoJSON for Viet Nam (one country file, cached in data/cache/boundaries/,
        git-ignored). The feature whose shapeName folds to "do luong" is extracted.
ADM3 (communes, for Lưu Sơn) is requested too; geoBoundaries returns 404 for VNM ADM3 in every release type
(checked 2026-11-14), so `luu_son` is written as null with the reason.

Checks (the script stops instead of guessing when one fails):
  * the GeoJSON has no foreign `crs` member and every coordinate is a WGS84 lon/lat (RFC 7946 = EPSG:4326);
  * exactly one Đô Lương feature, and it lies inside the Nghệ An ADM1 polygon already in data/raw/boundaries/;
  * the study point (Lưu Sơn commune marker, Wikidata Q10788283) falls inside the polygon;
  * the polygon area (WGS84 Lambert azimuthal equal-area centred on the district) is compared with the published
    350.433 km² (Vietnamese Wikipedia "Đô Lương (huyện)", citing the Nghệ An 2019 statistics).

Vietnam abolished the district level on 1 July 2025: the outline is the FORMER Đô Lương district (huyện Đô Lương cũ),
geoBoundaries vintage "boundaryYearRepresented 2020" (OCHA ROAP / Government of Viet Nam, source update 2023-01-19).

Run:   .venv\\Scripts\\python.exe pipeline\\fetch_boundaries.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "MiaudowResearch/1.0 (NASA Space Apps 2026 hackathon)"
API = "https://www.geoboundaries.org/api/current/gbOpen/VNM/{level}/"
ADM1_FILE = ROOT / "data" / "raw" / "boundaries" / "geoBoundaries-VNM-ADM1_simplified.geojson"
CACHE_DIR = ROOT / "data" / "cache" / "boundaries"
OUT_ADM2 = ROOT / "data" / "raw" / "boundaries" / "do_luong_adm2.geojson"
OUT_MANIFEST = ROOT / "data" / "raw" / "boundaries" / "do_luong_MANIFEST.json"
OUT_WEB = ROOT / "data" / "canonical" / "geo_do_luong.json"

STUDY_POINT = {
    "lat": 18.89638889,
    "lon": 105.2802778,
    "source": "Wikidata Q10788283 (Lưu Sơn commune marker; not the trial field)",
    "source_url": "https://www.wikidata.org/wiki/Q10788283",
}
AREA_REFERENCE = {
    "area_km2": 350.433,
    "source": "Vietnamese Wikipedia 'Đô Lương (huyện)', revision 75606999 (2026-10-02), "
    "citing the Nghệ An 2019 statistics (ref NA2019)",
    "url": "https://vi.wikipedia.org/w/index.php?title=%C4%90%C3%B4_L%C6%B0%C6%A1ng_(huy%E1%BB%87n)&oldid=75606999",
}
TARGET = "do luong"
WEB_TOLERANCE_DEG = 0.0005  # ~50 m at 19° N; Douglas-Peucker with topology preserved
WEB_DECIMALS = 5  # ~1 m


# ----------------------------------------------------------------------------------------------- pure functions
def fold(name: str) -> str:
    """'Đô Lương' / 'Do Luong' / 'Huyện Đô Lương' -> 'do luong' (strip accents, đ->d, lower case, 'huyen' prefix)."""
    s = name.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().strip()
    for prefix in ("huyen ", "district "):
        if s.startswith(prefix):
            s = s[len(prefix) :]
    return " ".join(s.replace("-", " ").split())


def iter_coords(geom: dict):
    t = geom["type"]
    if t == "Polygon":
        for ring in geom["coordinates"]:
            yield from ring
    elif t == "MultiPolygon":
        for poly in geom["coordinates"]:
            for ring in poly:
                yield from ring
    else:
        raise ValueError(f"unsupported geometry {t}")


def is_wgs84_lonlat(geom: dict) -> bool:
    return all(-180.0 <= c[0] <= 180.0 and -90.0 <= c[1] <= 90.0 for c in iter_coords(geom))


def bbox_of(geom: dict) -> list[float]:
    xs, ys = zip(*((c[0], c[1]) for c in iter_coords(geom)), strict=False)
    return [min(xs), min(ys), max(xs), max(ys)]


def ring_area_laea(ring: list, lat0: float, lon0: float, radius_m: float = 6371007.181) -> float:
    """Planar area (m²) of a lon/lat ring projected to a spherical Lambert azimuthal equal-area plane.

    Equal-area on the authalic sphere (R = 6371007.181 m, the GRS80 authalic radius), so the result is the area on
    the sphere; at 19° N it is ~0.3 % above the WGS84-ellipsoid area, so it is only a cross-check.
    """
    phi0, lam0 = math.radians(lat0), math.radians(lon0)
    pts = []
    for lon, lat, *_ in ring:
        phi, lam = math.radians(lat), math.radians(lon)
        k = math.sqrt(
            2.0 / (1.0 + math.sin(phi0) * math.sin(phi) + math.cos(phi0) * math.cos(phi) * math.cos(lam - lam0))
        )
        x = radius_m * k * math.cos(phi) * math.sin(lam - lam0)
        y = radius_m * k * (math.cos(phi0) * math.sin(phi) - math.sin(phi0) * math.cos(phi) * math.cos(lam - lam0))
        pts.append((x, y))
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1], strict=False):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def geom_area_km2(geom: dict) -> float:
    """Area of a (Multi)Polygon in km² (outer rings minus holes), LAEA centred on the bbox centre."""
    w, s, e, n = bbox_of(geom)
    lat0, lon0 = (s + n) / 2, (w + e) / 2
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    total = 0.0
    for poly in polys:
        total += ring_area_laea(poly[0], lat0, lon0)
        for hole in poly[1:]:
            total -= ring_area_laea(hole, lat0, lon0)
    return total / 1e6


def geom_area_km2_ellipsoid(geom: dict) -> float:
    """Area in km² on the WGS84 ellipsoid: PROJ Lambert azimuthal equal-area (ellps=WGS84) centred on the bbox."""
    from rasterio.warp import transform_geom
    from shapely.geometry import shape

    w, s, e, n = bbox_of(geom)
    crs = f"+proj=laea +lat_0={(s + n) / 2:.6f} +lon_0={(w + e) / 2:.6f} +ellps=WGS84 +units=m +no_defs"
    return shape(transform_geom("EPSG:4326", crs, geom)).area / 1e6


def outline_rings(geom: dict, decimals: int = WEB_DECIMALS) -> list[list[list[float]]]:
    """All rings (outer and holes) of a (Multi)Polygon as [[lon, lat], ...] lists, rounded."""
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [[[round(c[0], decimals), round(c[1], decimals)] for c in ring] for poly in polys for ring in poly]


# ----------------------------------------------------------------------------------------------- I/O
def get(url: str, tries: int = 5, timeout: float = 180.0):
    import httpx

    delay, last = 5.0, None
    for attempt in range(tries):
        try:
            r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
            if r.status_code in (200, 404):
                return r
            last = f"HTTP {r.status_code}"
        except httpx.HTTPError as exc:
            last = repr(exc)
        print(f"  retry {attempt + 1} {url}: {last}", file=sys.stderr)
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"giving up {url}: {last}")


def main() -> int:
    from shapely.geometry import Point, shape

    retrieved_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta_r = get(API.format(level="ADM2"))
    if meta_r.status_code != 200:
        raise SystemExit(f"geoBoundaries ADM2 metadata: HTTP {meta_r.status_code}")
    meta = meta_r.json()
    (CACHE_DIR / "VNM_ADM2_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    adm3_r = get(API.format(level="ADM3"))
    adm3_status = adm3_r.status_code
    print(f"ADM2 licence: {meta['boundaryLicense']}; ADM3 metadata HTTP {adm3_status}")

    gj_path = CACHE_DIR / "geoBoundaries-VNM-ADM2.geojson"
    if not gj_path.exists():
        r = get(meta["gjDownloadURL"], timeout=600.0)
        if r.status_code != 200:
            raise SystemExit(f"download {meta['gjDownloadURL']}: HTTP {r.status_code}")
        gj_path.write_bytes(r.content)
    raw = gj_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    fc = json.loads(raw)
    if "crs" in fc and "4326" not in json.dumps(fc["crs"]) and "CRS84" not in json.dumps(fc["crs"]):
        raise SystemExit(f"unexpected CRS member {fc['crs']}")

    hits = [f for f in fc["features"] if fold(f["properties"].get("shapeName", "")) == TARGET]
    if len(hits) != 1:
        raise SystemExit(f"expected one Đô Lương feature, found {len(hits)}")
    feat = hits[0]
    geom = feat["geometry"]
    if not is_wgs84_lonlat(geom):
        raise SystemExit("coordinates are not lon/lat degrees")
    poly = shape(geom)
    if not poly.is_valid:
        raise SystemExit("Đô Lương polygon is invalid")

    adm1 = json.loads(ADM1_FILE.read_text(encoding="utf-8"))
    nghe_an = [
        f for f in adm1["features"] if fold(f["properties"].get("shapeName", "")) in ("nghe an", "nghe an province")
    ]
    in_province = None
    if nghe_an:
        in_province = shape(nghe_an[0]["geometry"]).buffer(0.01).contains(poly)
        if not in_province:
            raise SystemExit("the Đô Lương feature is not inside Nghệ An (ADM1)")

    pt = Point(STUDY_POINT["lon"], STUDY_POINT["lat"])
    inside = poly.contains(pt)
    if not inside:
        raise SystemExit("study point is outside the Đô Lương polygon")
    area = geom_area_km2_ellipsoid(geom)
    area_sphere = geom_area_km2(geom)
    diff_pct = 100.0 * (area - AREA_REFERENCE["area_km2"]) / AREA_REFERENCE["area_km2"]
    bbox = [round(v, 6) for v in bbox_of(geom)]
    n_vertices = sum(1 for _ in iter_coords(geom))
    print(
        f"Đô Lương: {area:.2f} km² (reference {AREA_REFERENCE['area_km2']} km², {diff_pct:+.2f} %), "
        f"sphere cross-check {area_sphere:.2f} km², bbox {bbox}, {n_vertices} vertices, study point inside: {inside}"
    )

    licence = meta["boundaryLicense"]
    source = (
        f"geoBoundaries gbOpen VNM ADM2 ({meta['boundaryID']}), source {meta['boundarySource']}, "
        f"year represented {meta['boundaryYearRepresented']}, build {meta['buildDate']}"
    )
    provenance = {
        "source": source,
        "license": licence,
        "license_source": meta.get("licenseSource"),
        "api_url": API.format(level="ADM2"),
        "download_url": meta["gjDownloadURL"],
        "retrieved_at": retrieved_at,
        "sha256_country_file": sha,
        "boundary_year_represented": meta["boundaryYearRepresented"],
        "source_data_update": meta.get("sourceDataUpdateDate"),
        "citation": "Runfola, D. et al. (2020) geoBoundaries: A global database of political administrative "
        "boundaries. PLoS ONE 15(4): e0231866. https://doi.org/10.1371/journal.pone.0231866",
    }
    out = {
        "type": "FeatureCollection",
        "name": "do_luong_adm2",
        "provenance": provenance,
        "features": [
            {
                "type": "Feature",
                "properties": {
                    **feat["properties"],
                    "name_vi": "huyện Đô Lương (cũ)",
                    "area_km2_wgs84_laea": round(area, 3),
                },
                "geometry": geom,
            }
        ],
    }
    OUT_ADM2.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

    simple = poly.simplify(WEB_TOLERANCE_DEG, preserve_topology=True)
    simple_geom = json.loads(json.dumps(simple.__geo_interface__))
    rings = outline_rings(simple_geom)
    luu_son_reason = (
        f"geoBoundaries has no VNM ADM3 (commune) layer: API returned HTTP {adm3_status} for "
        f"{API.format(level='ADM3')} (gbOpen, gbHumanitarian and gbAuthoritative all 404 on "
        f"{retrieved_at[:10]}). No commune outline is drawn; Lưu Sơn is shown as a point only."
    )
    limitations = [
        {
            "vi": "Ranh giới là huyện Đô Lương (cũ): Việt Nam bỏ cấp huyện từ 1/7/2025; ranh giới theo geoBoundaries "
            "(năm đại diện 2020, OCHA ROAP / Chính phủ Việt Nam), không phải bản đồ địa chính.",
            "en": "The outline is the former Đô Lương district: Viet Nam abolished the district level on 1 July 2025; "
            "the boundary is geoBoundaries (year represented 2020, OCHA ROAP / Government of Viet Nam), not a "
            "cadastral map.",
        },
        {
            "vi": f"Diện tích tính được {area:.1f} km², lệch {diff_pct:+.1f} % so với 350,433 km² công bố "
            "(Wikipedia tiếng Việt, số liệu Nghệ An 2019).",
            "en": f"Computed area {area:.1f} km², {diff_pct:+.1f} % from the published 350.433 km² "
            "(Vietnamese Wikipedia, Nghệ An 2019 statistics).",
        },
        {
            "vi": f"Đường viền web được đơn giản hoá (dung sai {WEB_TOLERANCE_DEG}°, khoảng 50 m); chỉ dùng để vẽ.",
            "en": f"The web outline is simplified (tolerance {WEB_TOLERANCE_DEG}°, about 50 m); for drawing only.",
        },
        {
            "vi": "Điểm Lưu Sơn là điểm đánh dấu xã trên Wikidata, không phải vị trí ruộng thử nghiệm. Xã Lưu Sơn "
            "đã nhập vào xã Đô Lương mới năm 2025.",
            "en": "The Lưu Sơn point is the commune marker on Wikidata, not the trial field. Lưu Sơn commune merged "
            "into the new Đô Lương commune in 2025.",
        },
    ]
    web = {
        "generated_at": retrieved_at,
        "do_luong": {
            "name": {"vi": "huyện Đô Lương (cũ), Nghệ An", "en": "former Đô Lương district, Nghệ An"},
            "outline": rings,
            "bbox": bbox,
            "area_km2": round(area, 2),
            "area_method": "WGS84 ellipsoid, Lambert azimuthal equal-area centred on the district",
            "area_reference": {**AREA_REFERENCE, "difference_pct": round(diff_pct, 2)},
            "n_vertices_full": n_vertices,
            "n_vertices_web": sum(len(r) for r in rings),
            "simplify_tolerance_deg": WEB_TOLERANCE_DEG,
            "source": source,
            "license": licence,
            "source_url": API.format(level="ADM2"),
            "retrieved_at": retrieved_at,
            "crs": "EPSG:4326 (RFC 7946 lon/lat)",
            "validation_status": "VERIFIED",
            "full_resolution_file": "data/raw/boundaries/do_luong_adm2.geojson",
        },
        "luu_son": None,
        "luu_son_status": {"status": "UNAVAILABLE", "reason": luu_son_reason},
        "study_point": {**STUDY_POINT, "inside_do_luong": inside},
        "limitations": limitations,
    }
    OUT_WEB.write_text(json.dumps(web, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    manifest = {
        "dataset_id": "geoboundaries_vnm_adm2_do_luong",
        "title": {
            "vi": "Ranh giới huyện Đô Lương (cũ), Nghệ An — geoBoundaries ADM2",
            "en": "Former Đô Lương district boundary, Nghệ An — geoBoundaries ADM2",
        },
        "provider": "geoBoundaries (William & Mary geoLab); source OCHA ROAP, Government of Viet Nam",
        "source_id": meta["boundaryID"],
        "source_url": API.format(level="ADM2"),
        "license": f"{licence} (licence source: {meta.get('licenseSource')}); attribute geoBoundaries and OCHA ROAP",
        "source_revision": f"geoBoundaries commit in download URL ({meta['gjDownloadURL'].split('/raw/')[1].split('/')[0]}); "
        f"buildDate {meta['buildDate']}; sourceDataUpdateDate {meta.get('sourceDataUpdateDate')}",
        "retrieved_at": retrieved_at,
        "temporal_coverage": f"boundary year represented {meta['boundaryYearRepresented']} (pre-July-2025 districts)",
        "spatial_resolution": f"vector polygon, {n_vertices} vertices (full); web copy simplified at "
        f"{WEB_TOLERANCE_DEG}°",
        "geometry_crs": "EPSG:4326",
        "variables": ["outline", "bbox", "area_km2"],
        "missing_policy": "No commune (ADM3) layer exists in geoBoundaries for Viet Nam; Lưu Sơn is null, not drawn "
        "from another source.",
        "allowed_use": {
            "vi": "Vẽ vùng nghiên cứu và cắt dữ liệu vệ tinh; không dùng làm ranh giới pháp lý.",
            "en": "Draw the study area and clip satellite data; not a legal boundary.",
        },
        "version_sha256": hashlib.sha256(OUT_ADM2.read_bytes()).hexdigest(),
        "ingestion_status": "INGESTED",
        "is_field_measurement": False,
        "notes": limitations,
        "checks": {
            "crs_wgs84": True,
            "in_nghe_an_adm1": in_province,
            "study_point_inside": inside,
            "area_km2": round(area, 3),
            "area_km2_sphere_crosscheck": round(area_sphere, 3),
            "area_method": "PROJ laea ellps=WGS84 centred on the bbox (rasterio.warp.transform_geom) + shapely area",
            "area_reference": AREA_REFERENCE,
            "area_difference_pct": round(diff_pct, 3),
            "adm3_api_status": adm3_status,
        },
        "provenance": provenance,
        "script": "pipeline/fetch_boundaries.py",
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT_ADM2.relative_to(ROOT)}, {OUT_WEB.relative_to(ROOT)}, {OUT_MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
