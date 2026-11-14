"""Data-quality report of the governed data layer: data/canonical/quality.json.

Run from the project root (pipeline/build_canonical.py also runs it as its last step):

    .venv\\Scripts\\python pipeline/check_quality.py

Every check has an id, a category, a status (pass | warn | fail), a bilingual detail and the evidence numbers. A fail
is written like any other result; nothing is hidden or dropped. Categories:

- integrity    sha256 of the raw files against their manifests and the catalog; composite GeoTIFFs against the
               statistics written in vegetation.json
- crs_bounds   CRS and bounds: Nghệ An outline, Đô Lương inside Nghệ An, study point inside Đô Lương, POWER cells
               inside the Nghệ An bbox, Sentinel-2 grid and composite bounds
- time         continuity and duplicates of the NASA POWER daily caches (duplicate JSON keys are detected while
               parsing), leap-year aggregation (29 February summed into February), CHIRPS months, MODIS 16-day dates,
               Sentinel-2 scene dates
- units_ranges declared units; rain >= 0; plausible temperatures; NDVI in [-1, 1]; shares in [0, 1]
- missing      fill sentinels (-999), months without totals, dates without a valid pixel, unavailable layers
- resolution   POWER 0.5° x 0.625° beside CHIRPS 0.05°, MODIS 250 m and Sentinel-2 20 m: never downscaled into fine
               weather
- licence      a licence and the required attribution for every dataset
- version      processing versions mixed or outdated (Sentinel-2 baselines, amended decrees)

Status meaning: pass = the check held; warn = the data are usable but carry a limitation a reader must see; fail =
the check did not hold (or its input is missing) and the affected values must not be trusted until fixed.
"""

from __future__ import annotations

import calendar
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "api"))

from miaudow_api.contracts import QualityCheck, QualityReport, Text  # noqa: E402

SCRIPT = "pipeline/check_quality.py"
FILL = -999.0
VIETNAM_BBOX = (102.1, 8.2, 109.6, 23.5)  # lon/lat envelope of Viet Nam, to catch swapped axes or a wrong CRS
POWER_UNITS = {
    "PRECTOTCORR": "mm/day",
    "T2M_MAX": "C",
    "T2M_MIN": "C",
    "T2M": "C",
    "RH2M": "%",
    "WS2M": "m/s",
    "ALLSKY_SFC_SW_DWN": "MJ/m^2/day",
    "GWETROOT": "1",
}
# plausible daily ranges for lowland Nghệ An (NASA POWER grid values); outside means a broken file, not weather
POWER_RANGES = {
    "PRECTOTCORR": (0.0, 600.0),
    "T2M_MAX": (-5.0, 48.0),
    "T2M_MIN": (-10.0, 40.0),
    "T2M": (-10.0, 42.0),
    "RH2M": (0.0, 100.0),
    "WS2M": (0.0, 60.0),
    "ALLSKY_SFC_SW_DWN": (0.0, 45.0),
    "GWETROOT": (0.0, 1.0),
}


def chk(
    check_id: str, category: str, dataset_id: str | None, status: str, vi: str, en: str, **evidence
) -> QualityCheck:
    return QualityCheck(
        check_id=check_id,
        category=category,
        dataset_id=dataset_id,
        status=status,
        detail=Text(vi=vi, en=en),
        evidence=evidence,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


# ---------------------------------------------------------------- integrity


def sha_check(
    check_id: str, dataset_id: str, path: Path, expected: str | None, root: Path, against: str
) -> QualityCheck:
    """A file's sha256 against the value its manifest (or the catalog) recorded."""
    if not path.exists():
        return chk(
            check_id, "integrity", dataset_id, "fail",
            f"Thiếu tệp {rel(path, root)}, không kiểm tra được.",
            f"File {rel(path, root)} is missing; it cannot be checked.",
            file=rel(path, root), expected=expected, actual=None, against=against,
        )  # fmt: skip
    actual = sha256(path)
    if expected is None:
        return chk(
            check_id, "integrity", dataset_id, "warn",
            f"{rel(path, root)}: {against} không ghi mã sha256 để so.",
            f"{rel(path, root)}: {against} records no sha256 to compare with.",
            file=rel(path, root), expected=None, actual=actual, against=against,
        )  # fmt: skip
    ok = actual == expected
    return chk(
        check_id, "integrity", dataset_id, "pass" if ok else "fail",
        f"{rel(path, root)} {'khớp' if ok else 'KHÔNG khớp'} mã sha256 trong {against}.",
        f"{rel(path, root)} {'matches' if ok else 'does NOT match'} the sha256 in {against}.",
        file=rel(path, root), expected=expected, actual=actual, against=against,
    )  # fmt: skip


def integrity_checks(root: Path, catalog: dict | None, climate: dict | None) -> list[QualityCheck]:
    raw, ref = root / "data" / "raw", root / "data" / "reference"
    out: list[QualityCheck] = []
    by_id = {d["dataset_id"]: d for d in (catalog or {}).get("datasets", [])}
    manifests = {
        "chirps_v3_monthly": (raw / "chirps_v3" / "MANIFEST.json", "files.csv", "version_sha256"),
        "modis_mod13q1_ndvi": (raw / "modis_mod13q1" / "MANIFEST.json", "files.pixels", "version_sha256"),
        "sentinel2_l2a_do_luong_vi": (raw / "sentinel2" / "MANIFEST.json", "files.scenes", "version_sha256"),
    }
    for dataset_id, (mpath, file_key, sha_key) in manifests.items():
        m = read_json(mpath)
        if m is None:
            out.append(
                chk(
                    f"integrity-{dataset_id}",
                    "integrity",
                    dataset_id,
                    "fail",
                    f"Thiếu {rel(mpath, root)}.",
                    f"{rel(mpath, root)} is missing.",
                    manifest=rel(mpath, root),
                )  # fmt: skip
            )
            continue
        node = m
        for part in file_key.split("."):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        out.append(
            sha_check(f"integrity-{dataset_id}", dataset_id, root / str(node), m.get(sha_key), root, "MANIFEST.json")
        )
        cat = by_id.get(dataset_id)
        if cat is not None and cat.get("version_sha256") not in (None, m.get(sha_key)):
            out.append(
                chk(
                    f"integrity-{dataset_id}-catalog",
                    "integrity",
                    dataset_id,
                    "fail",
                    "Mã sha256 trong catalog.json khác với MANIFEST.json: cần dựng lại dữ liệu chuẩn.",
                    "The sha256 in catalog.json differs from MANIFEST.json: rebuild the canonical data.",
                    catalog=cat.get("version_sha256"),
                    manifest=m.get(sha_key),
                )  # fmt: skip
            )
    modis = read_json(raw / "modis_mod13q1" / "MANIFEST.json")
    if modis:
        out.append(
            sha_check(
                "integrity-modis-summary",
                "modis_mod13q1_ndvi",
                root / modis["files"]["summary"],
                modis.get("summary_sha256"),
                root,
                "MANIFEST.json (summary_sha256)",
            )  # fmt: skip
        )
    adm2 = read_json(raw / "boundaries" / "do_luong_MANIFEST.json")
    if adm2:
        out.append(
            sha_check(
                "integrity-boundary-do-luong",
                "geoboundaries_vnm_adm2_do_luong",
                raw / "boundaries" / "do_luong_adm2.geojson",
                adm2.get("version_sha256"),
                root,
                "do_luong_MANIFEST.json",
            )  # fmt: skip
        )
    docs = read_json(raw / "documents" / "MANIFEST.json")
    for d in (docs or {}).get("documents", []):
        if d.get("chunks_file"):
            out.append(
                sha_check(
                    f"integrity-document-{d['doc_id']}",
                    "evidence_documents",
                    root / d["chunks_file"],
                    d.get("chunks_sha256"),
                    root,
                    "documents/MANIFEST.json",
                )  # fmt: skip
            )
    if climate is not None and climate.get("chirps", {}).get("status") == "loaded":
        ch = climate["chirps"]
        out.append(
            sha_check(
                "integrity-chirps-canonical",
                "chirps_v3_monthly",
                root / ch["file"],
                ch.get("sha256"),
                root,
                "climate.json",
            )
        )
    for dataset_id, path in (
        ("geoboundaries_adm1", raw / "boundaries" / "geoBoundaries-VNM-ADM1_simplified.geojson"),
        ("modis_farmland_weights", ref / "cell_weights_nghe_an.csv"),
        ("nso_rice_yield", ref / "risk_table.json"),
        ("e012_model", ref / "metrics.json"),
        ("e019_hazard_labels", ref / "hazard_labels.json"),
        ("e020_soil_wetness", ref / "soil_wetness.json"),
        ("study_p02", root / "api" / "rules" / "rotations.yaml"),
    ):
        expected = by_id.get(dataset_id, {}).get("version_sha256")
        out.append(sha_check(f"integrity-{dataset_id}", dataset_id, path, expected, root, "catalog.json"))
    out.append(power_sha_check(root, climate))
    return out


def power_sha_check(root: Path, climate: dict | None) -> QualityCheck:
    """The one digest over the POWER caches (same recipe as the build) against climate.json."""
    from miaudow_api.science.power import CACHE_PATTERN, sha256_of_files

    files = sorted((root / "data" / "raw" / "power").glob(CACHE_PATTERN)) + sorted(
        (root / "data" / "raw" / "power_t2m").glob(CACHE_PATTERN)
    )
    expected = (climate or {}).get("version_sha256")
    if not files:
        return chk(
            "integrity-nasa_power_daily", "integrity", "nasa_power_daily", "fail",
            "Không có tệp NASA POWER nào trong data/raw/power.", "No NASA POWER cache file in data/raw/power.",
            files=0,
        )  # fmt: skip
    actual = sha256_of_files(files)
    ok = actual == expected
    return chk(
        "integrity-nasa_power_daily", "integrity", "nasa_power_daily", "pass" if ok else "fail",
        f"{len(files)} tệp NASA POWER {'khớp' if ok else 'KHÔNG khớp'} mã sha256 ghi trong climate.json.",
        f"{len(files)} NASA POWER cache files {'match' if ok else 'do NOT match'} the sha256 recorded in climate.json.",
        files=len(files), expected=expected, actual=actual,
    )  # fmt: skip


# ---------------------------------------------------------------- NASA POWER daily caches


def load_json_with_duplicates(path: Path) -> tuple[dict, list[str]]:
    """Parse JSON and report every key that appears twice in one object (json.loads would silently keep the last)."""
    dups: list[str] = []

    def hook(pairs):
        seen: dict = {}
        for k, v in pairs:
            if k in seen:
                dups.append(k)
            seen[k] = v
        return seen

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=hook), dups


def power_file_stats(path: Path) -> dict:
    """Continuity, duplicates, fill values, ranges and units of one cached POWER daily file."""
    payload, dups = load_json_with_duplicates(path)
    header = payload.get("header", {})
    start = datetime.strptime(header.get("start", "19900101"), "%Y%m%d").date()
    end = datetime.strptime(header.get("end", "20241231"), "%Y%m%d").date()
    expected = {(start + timedelta(days=i)).strftime("%Y%m%d") for i in range((end - start).days + 1)}
    params = payload.get("properties", {}).get("parameter", {})
    units = {k: v.get("units", "") for k, v in payload.get("parameters", {}).items()}
    lon, lat = payload.get("geometry", {}).get("coordinates", [None, None])[:2]
    stats: dict = {
        "file": path.name,
        "lat": lat,
        "lon": lon,
        "api_version": (header.get("api") or {}).get("version"),
        "duplicate_keys": len(dups),
        "parameters": {},
    }
    for name, series in params.items():
        keys = set(series)
        values = [v for v in series.values() if v is not None]
        fill = sum(1 for v in values if float(v) <= FILL + 9)
        real = [float(v) for v in values if float(v) > FILL + 9]
        lo, hi = POWER_RANGES.get(name, (float("-inf"), float("inf")))
        leap_days = [f"{y}0229" for y in range(start.year, end.year + 1) if calendar.isleap(y)]
        leap_missing = [int(d[:4]) for d in leap_days if d in expected and d not in keys]
        stats["parameters"][name] = {
            "days": len(series),
            "gaps": len(expected - keys),
            "unexpected_dates": len(keys - expected),
            "fill_values": fill,
            "out_of_range": sum(1 for v in real if not lo <= v <= hi),
            "negative": sum(1 for v in real if v < 0) if name == "PRECTOTCORR" else 0,
            "min": min(real) if real else None,
            "max": max(real) if real else None,
            "unit": units.get(name),
            "unit_expected": POWER_UNITS.get(name),
            "leap_days_missing": leap_missing,
        }
    return stats


def power_checks(power_dirs: list[Path], root: Path) -> list[QualityCheck]:
    files = [f for d in power_dirs for f in sorted(d.glob("power_*.json"))]
    if not files:
        return [
            chk(
                "time-power-continuity",
                "time",
                "nasa_power_daily",
                "fail",
                "Không có tệp NASA POWER để kiểm tra.",
                "No NASA POWER file to check.",
                dirs=[rel(d, root) for d in power_dirs],
            )  # fmt: skip
        ]
    stats = [power_file_stats(f) for f in files]
    per = [(s["file"], p, v) for s in stats for p, v in s["parameters"].items()]
    gaps = {f"{f}:{p}": v["gaps"] for f, p, v in per if v["gaps"] or v["unexpected_dates"]}
    dups = {s["file"]: s["duplicate_keys"] for s in stats if s["duplicate_keys"]}
    leap = {f"{f}:{p}": v["leap_days_missing"] for f, p, v in per if v["leap_days_missing"]}
    fills = {f"{f}:{p}": v["fill_values"] for f, p, v in per if v["fill_values"]}
    bad_range = {f"{f}:{p}": [v["min"], v["max"]] for f, p, v in per if v["out_of_range"]}
    negative = {f"{f}:{p}": v["negative"] for f, p, v in per if v["negative"]}
    bad_units = {f"{f}:{p}": v["unit"] for f, p, v in per if v["unit_expected"] and v["unit"] != v["unit_expected"]}
    versions = sorted({str(s["api_version"]) for s in stats})
    n_days = sorted({v["days"] for _, _, v in per})
    out = [
        chk(
            "time-power-continuity", "time", "nasa_power_daily", "fail" if gaps or dups or leap else "pass",
            f"{len(files)} tệp NASA POWER: {'có ngày thiếu, trùng hoặc thiếu 29/2' if gaps or dups or leap else 'đủ mọi ngày, không trùng, có đủ ngày 29/2 của năm nhuận'}.",
            f"{len(files)} NASA POWER files: {'days missing, duplicated or 29 February absent' if gaps or dups or leap else 'every day present once, 29 February present in every leap year'}.",
            files=len(files), days_per_series=n_days, gaps=gaps, duplicate_keys=dups, leap_days_missing=leap,
        ),
        chk(
            "missing-power-fill-values", "missing", "nasa_power_daily", "warn" if fills else "pass",
            "Có giá trị trống -999; chúng được đọc là thiếu, không bao giờ là 0." if fills
            else "Không có giá trị trống -999 trong các tệp NASA POWER.",
            "Fill values -999 present; they are read as missing, never as 0." if fills
            else "No -999 fill value in the NASA POWER files.",
            fill_values=fills,
        ),
        chk(
            "units-power-ranges", "units_ranges", "nasa_power_daily", "fail" if bad_range or negative else "pass",
            "Có giá trị ngoài khoảng hợp lý (mưa âm hoặc nhiệt độ bất thường)." if bad_range or negative
            else "Mưa không âm; nhiệt độ, độ ẩm, gió, bức xạ và độ ẩm đất nằm trong khoảng hợp lý.",
            "Values outside plausible ranges (negative rain or implausible temperature)." if bad_range or negative
            else "Rain is never negative; temperature, humidity, wind, radiation and soil wetness are plausible.",
            ranges=POWER_RANGES, out_of_range=bad_range, negative_rain=negative,
            observed={p: [min(v["min"] for f, q, v in per if q == p and v["min"] is not None),
                          max(v["max"] for f, q, v in per if q == p and v["max"] is not None)]
                      for p in sorted({p for _, p, _ in per})},
        ),
        chk(
            "units-power-declared", "units_ranges", "nasa_power_daily", "fail" if bad_units else "pass",
            "Đơn vị do NASA POWER ghi khác với đơn vị mong đợi." if bad_units else "Đơn vị do NASA POWER ghi đúng như mong đợi (mm/ngày, °C, %, m/s, MJ/m²/ngày, 0-1).",
            "Units declared by NASA POWER differ from the expected ones." if bad_units else "Units declared by NASA POWER are the expected ones (mm/day, °C, %, m/s, MJ/m²/day, 0-1).",
            mismatched=bad_units, expected=POWER_UNITS,
        ),
        chk(
            "version-power-api", "version", "nasa_power_daily", "pass" if len(versions) == 1 else "warn",
            f"Mọi tệp NASA POWER từ cùng phiên bản API ({', '.join(versions)})." if len(versions) == 1
            else f"Các tệp NASA POWER đến từ nhiều phiên bản API: {', '.join(versions)}.",
            f"All NASA POWER files come from one API version ({', '.join(versions)})." if len(versions) == 1
            else f"NASA POWER files come from several API versions: {', '.join(versions)}.",
            versions=versions,
        ),
    ]  # fmt: skip
    return out


def leap_year_check(root: Path, climate: dict | None) -> QualityCheck:
    """February of every leap year, re-summed from the raw daily cache (29 days), against climate.json per cell."""
    from miaudow_api.science.power import load_cached_cells

    if climate is None:
        return chk("time-leap-year-aggregation", "time", "nasa_power_daily", "fail", "Thiếu climate.json.",
                   "climate.json is missing.")  # fmt: skip
    try:
        cells = load_cached_cells(root / "data" / "raw" / "power", root / "data" / "raw" / "power_t2m")
    except (FileNotFoundError, ValueError) as err:
        return chk("time-leap-year-aggregation", "time", "nasa_power_daily", "fail",
                   f"Không đọc được tệp NASA POWER: {err}", f"NASA POWER caches unreadable: {err}")  # fmt: skip
    mismatches, compared = [], 0
    leap_years = [y for y in climate["years"] if calendar.isleap(y)]
    for cell in climate["cells"]:
        cached = cells.get((round(cell["lat"], 6), round(cell["lon"], 6)))
        if cached is None:
            mismatches.append({"cell": cell["id"], "reason": "no cache"})
            continue
        rain = cached.frame["PRECTOTCORR"]
        for y in leap_years:
            feb = rain[(rain.index.year == y) & (rain.index.month == 2)]
            mine = None if len(feb) != 29 or feb.isna().any() else round(float(feb.sum()), 1)
            theirs = climate["series"]["cells"][cell["id"]][str(y)]["monthly_rain_mm"][1]
            compared += 1
            if mine is None or theirs is None or abs(mine - theirs) > 0.051:
                mismatches.append(
                    {"cell": cell["id"], "year": y, "days": len(feb), "raw_sum": mine, "canonical": theirs}
                )
    listed = sorted(climate.get("leap_years_checked", []))
    ok = not mismatches and listed == leap_years
    return chk(
        "time-leap-year-aggregation", "time", "nasa_power_daily", "pass" if ok else "fail",
        f"Tháng 2 của {len(leap_years)} năm nhuận được cộng đủ 29 ngày ở cả 5 ô ({compared} lần so khớp)." if ok
        else "Tổng tháng 2 của năm nhuận không khớp với số ngày gốc.",
        f"February of {len(leap_years)} leap years sums all 29 days in all 5 cells ({compared} comparisons match)." if ok
        else "The February total of a leap year does not match the raw days.",
        leap_years=leap_years, compared=compared, mismatches=mismatches[:20], leap_years_checked=listed,
    )  # fmt: skip


def climate_canonical_checks(climate: dict | None) -> list[QualityCheck]:
    if climate is None:
        return [chk("units-climate-canonical", "units_ranges", "nasa_power_daily", "fail", "Thiếu climate.json.",
                    "climate.json is missing.")]  # fmt: skip
    series = [("farmland_weighted", climate["series"]["farmland_weighted"])] + list(climate["series"]["cells"].items())
    negative, sum_err, missing_months = [], [], 0
    for area, rows in series:
        for y, r in rows.items():
            months = r["monthly_rain_mm"]
            missing_months += sum(1 for v in months if v is None)
            negative += [f"{area}:{y}" for v in months if v is not None and v < 0]
            complete = r["annual_rain_mm"] is not None and all(v is not None for v in months)
            if complete and abs(sum(months) - r["annual_rain_mm"]) > 0.65:  # 12 rounded months + a rounded total
                sum_err.append(
                    {"area": area, "year": y, "sum_months": round(sum(months), 1), "annual": r["annual_rain_mm"]}
                )
    years = climate["years"]
    contiguous = years == list(range(years[0], years[-1] + 1))
    return [
        chk(
            "units-climate-canonical", "units_ranges", "nasa_power_daily", "fail" if negative or sum_err else "pass",
            "Mưa tháng không âm và tổng năm bằng tổng 12 tháng (sai khác chỉ do làm tròn)." if not (negative or sum_err)
            else "Có mưa tháng âm hoặc tổng năm khác tổng 12 tháng.",
            "Monthly rain is never negative and each annual total equals its 12 months (up to rounding)." if not (negative or sum_err)
            else "A negative monthly total, or an annual total that differs from its 12 months.",
            negative=negative[:20], annual_mismatch=sum_err[:20], series_checked=len(series),
        ),
        chk(
            "missing-climate-months", "missing", "nasa_power_daily", "pass" if missing_months == 0 else "warn",
            "Không thiếu tháng nào trong climate.json." if missing_months == 0
            else f"{missing_months} tháng không có tổng (để trống, không điền).",
            "No month is missing in climate.json." if missing_months == 0
            else f"{missing_months} months have no total (left empty, not filled).",
            missing_months=missing_months,
        ),
        chk(
            "time-climate-years", "time", "nasa_power_daily", "pass" if contiguous else "fail",
            f"Các năm {years[0]}-{years[-1]} liên tục, không trùng." if contiguous else "Các năm bị thiếu hoặc trùng.",
            f"Years {years[0]}-{years[-1]} are contiguous, none duplicated." if contiguous else "Years missing or duplicated.",
            first=years[0], last=years[-1], n=len(years),
        ),
    ]  # fmt: skip


# ---------------------------------------------------------------- CHIRPS


def chirps_checks(csv_path: Path, root: Path) -> list[QualityCheck]:
    if not csv_path.exists():
        return [chk("time-chirps-months", "time", "chirps_v3_monthly", "fail", f"Thiếu {rel(csv_path, root)}.",
                    f"{rel(csv_path, root)} is missing.")]  # fmt: skip
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cell_col = next((c for c in ("cell_id", "area_id", "cell") if c in rows[0]), None) if rows else None
    keys = Counter((r.get(cell_col), r["year"], r["month"]) for r in rows) if cell_col else Counter()
    dups = [list(k) for k, n in keys.items() if n > 1]
    per_cell = Counter(r.get(cell_col) for r in rows) if cell_col else Counter()
    empty = sum(1 for r in rows if (r.get("precip_mm") or "").strip() == "")
    negative = sum(1 for r in rows if (r.get("precip_mm") or "").strip() not in ("",) and float(r["precip_mm"]) < 0)
    years = sorted({int(r["year"]) for r in rows})
    expected = (years[-1] - years[0] + 1) * 12 if years else 0
    short = {c: n for c, n in per_cell.items() if n != expected}
    return [
        chk(
            "time-chirps-months", "time", "chirps_v3_monthly", "fail" if dups or short else "pass",
            f"Mỗi vùng có đủ {expected} tháng ({years[0]}-{years[-1]}), không trùng." if not (dups or short)
            else "Có tháng bị trùng hoặc thiếu trong CHIRPS.",
            f"Every area has all {expected} months ({years[0]}-{years[-1]}), none duplicated." if not (dups or short)
            else "CHIRPS months duplicated or missing.",
            rows=len(rows), areas=dict(per_cell), duplicates=dups[:20], incomplete_areas=short,
        ),
        chk(
            "units-chirps-ranges", "units_ranges", "chirps_v3_monthly", "fail" if negative else "pass",
            "Có tổng mưa tháng âm trong CHIRPS." if negative else "Không có tổng mưa tháng âm trong CHIRPS (mm/tháng).",
            "Negative monthly rain in CHIRPS." if negative else "No negative CHIRPS monthly total (mm/month).",
            negative=negative,
        ),
        chk(
            "missing-chirps-values", "missing", "chirps_v3_monthly", "pass" if empty == 0 else "warn",
            "Không có tháng CHIRPS nào để trống." if empty == 0 else f"{empty} tháng CHIRPS để trống (không điền).",
            "No empty CHIRPS month." if empty == 0 else f"{empty} empty CHIRPS months (left empty, not filled).",
            empty=empty,
        ),
    ]  # fmt: skip


# ---------------------------------------------------------------- vegetation (Sentinel-2, MODIS)


def _in_unit(v) -> bool:
    return v is None or -1.0 <= float(v) <= 1.0


def vegetation_checks(
    veg: dict | None, scenes_csv: Path | None, manifest: dict | None, root: Path
) -> list[QualityCheck]:
    if veg is None:
        return [chk("units-sentinel2-ndvi", "units_ranges", "sentinel2_l2a_do_luong_vi", "fail",
                    "Thiếu vegetation.json.", "vegetation.json is missing.")]  # fmt: skip
    out: list[QualityCheck] = []
    bad = []
    for s in veg["scenes"]:
        for k in ("ndvi_median", "ndvi_p25", "ndvi_p75", "ndmi_median"):
            if not _in_unit(s.get(k)):
                bad.append({"scene": s["scene_id"], k: s[k]})
        if not (0.0 <= float(s.get("valid_fraction", 0)) <= 1.0):
            bad.append({"scene": s["scene_id"], "valid_fraction": s["valid_fraction"]})
    for c in veg["composites"]:
        for k in ("ndvi_median", "ndvi_p25", "ndvi_p75"):
            if not _in_unit(c.get(k)):
                bad.append({"composite": c["id"], k: c[k]})
        if not (c["ndvi_p25"] <= c["ndvi_median"] <= c["ndvi_p75"]):
            bad.append({"composite": c["id"], "order": [c["ndvi_p25"], c["ndvi_median"], c["ndvi_p75"]]})
    out.append(
        chk(
            "units-sentinel2-ndvi",
            "units_ranges",
            "sentinel2_l2a_do_luong_vi",
            "fail" if bad else "pass",
            "Có NDVI/NDMI ngoài khoảng [-1, 1] hoặc phân vị sai thứ tự."
            if bad
            else f"NDVI và NDMI của {len(veg['scenes'])} cảnh và {len(veg['composites'])} ảnh ghép đều trong [-1, 1].",
            "NDVI/NDMI outside [-1, 1] or quartiles out of order."
            if bad
            else f"NDVI and NDMI of {len(veg['scenes'])} scenes and {len(veg['composites'])} composites are all in [-1, 1].",
            problems=bad[:20],
        )  # fmt: skip
    )
    dates = [s["date"] for s in veg["scenes"]]
    dup_dates = [d for d, n in Counter(dates).items() if n > 1]
    periods = [(date(2020, 6, 1), date(2021, 6, 30)), (date(2023, 1, 1), date(2024, 12, 31))]
    outside = [d for d in dates if not any(a <= date.fromisoformat(d) <= b for a, b in periods)]
    out.append(
        chk(
            "time-sentinel2-scenes",
            "time",
            "sentinel2_l2a_do_luong_vi",
            "fail" if dup_dates or outside else "pass",
            f"{len(dates)} ngày ảnh không trùng và nằm trong hai giai đoạn đã khai báo."
            if not (dup_dates or outside)
            else "Có ngày ảnh trùng hoặc ngoài giai đoạn đã khai báo.",
            f"{len(dates)} scene dates, none duplicated, all inside the two declared periods."
            if not (dup_dates or outside)
            else "Scene dates duplicated or outside the declared periods.",
            scenes=len(dates),
            duplicated=dup_dates,
            outside_periods=outside,
            periods=[[str(a), str(b)] for a, b in periods],
        )  # fmt: skip
    )
    counts = {c["id"]: c["n_scenes"] for c in veg["composites"]}
    thin = {k: v for k, v in counts.items() if v < 4}
    out.append(
        chk(
            "missing-sentinel2-composite-scenes",
            "missing",
            "sentinel2_l2a_do_luong_vi",
            "warn" if thin else "pass",
            "Có ảnh ghép mùa chỉ dựng từ ít cảnh (mây): "
            + ", ".join(f"{k} ({v} cảnh)" for k, v in thin.items())
            + ". Không so sánh các mùa như một sự thay đổi."
            if thin
            else "Mỗi ảnh ghép mùa có ít nhất 4 cảnh.",
            "Some seasonal composites rest on few scenes (clouds): "
            + ", ".join(f"{k} ({v} scenes)" for k, v in thin.items())
            + ". Do not read differences between seasons as change."
            if thin
            else "Every seasonal composite has at least 4 scenes.",
            scenes_per_composite=counts,
            skipped_scenes=(manifest or {}).get("counts", {}).get("scenes_skipped"),
        )  # fmt: skip
    )
    baselines: dict[str, Counter] = {}
    if scenes_csv is not None and scenes_csv.exists():
        with open(scenes_csv, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("status") != "used":
                    continue
                period = "2020-2021" if r["date"] < "2022" else "2023-2024"
                for b in (r.get("processing_baselines") or "").split(";"):
                    if b:
                        baselines.setdefault(period, Counter())[b] += 1
    all_b = sorted({b for c in baselines.values() for b in c})
    if not baselines:
        out.append(
            chk(
                "version-sentinel2-baselines",
                "version",
                "sentinel2_l2a_do_luong_vi",
                "warn",
                "Không đọc được phiên bản xử lý của từng cảnh (thiếu scenes.csv).",
                "Per-scene processing baselines could not be read (scenes.csv missing).",
            )  # fmt: skip
        )
    else:
        mixed = len(all_b) > 1
        out.append(
            chk(
                "version-sentinel2-baselines",
                "version",
                "sentinel2_l2a_do_luong_vi",
                "warn" if mixed else "pass",
                f"Các cảnh dùng nhiều phiên bản xử lý ESA ({', '.join(all_b)}); 2020-21 và 2024 không so được như một "
                "thay đổi."
                if mixed
                else f"Mọi cảnh cùng một phiên bản xử lý ({all_b[0]}).",
                f"Scenes use several ESA processing baselines ({', '.join(all_b)}); 2020-21 and 2024 are not comparable "
                "as change."
                if mixed
                else f"Every scene uses one processing baseline ({all_b[0]}).",
                tiles_by_period_and_baseline={k: dict(v) for k, v in baselines.items()},
            )  # fmt: skip
        )
    return out


def composite_raster_checks(veg: dict | None, root: Path) -> list[QualityCheck]:
    """Each composite GeoTIFF: CRS and grid as declared, NDVI in [-1, 1], and its median and pixel count equal to the
    numbers in vegetation.json."""
    if veg is None:
        return []
    try:
        import numpy as np
        import rasterio
    except ImportError:
        return [chk("integrity-sentinel2-geotiffs", "integrity", "sentinel2_l2a_do_luong_vi", "warn",
                    "Chưa cài rasterio nên chưa đọc được ảnh GeoTIFF.", "rasterio is not installed; GeoTIFFs not read.")]  # fmt: skip
    grid = veg["grid"]
    problems, read = [], []
    for c in veg["composites"]:
        path = root / c["geotiff"]
        if not path.exists():
            problems.append({"composite": c["id"], "reason": "file missing"})
            continue
        with rasterio.open(path) as r:
            scale = float(r.tags().get("NDVI_SCALE", "10000"))
            band = r.read(1, masked=True).astype("float64") / scale
            crs = r.crs.to_string() if r.crs else None
            bounds = [round(v, 3) for v in r.bounds]
            res = list(r.res)
        values = band.compressed()
        median = float(np.median(values)) if values.size else None
        entry = {"composite": c["id"], "crs": crs, "res_m": res, "valid_pixels": int(values.size), "median": median}
        read.append(entry)
        if crs != grid["crs"] or res != [grid["resolution_m"]] * 2 or bounds != [round(v, 3) for v in grid["bounds"]]:
            problems.append({**entry, "reason": "grid differs from vegetation.json", "bounds": bounds})
        if values.size and (values.min() < -1 or values.max() > 1):
            problems.append(
                {**entry, "reason": "NDVI outside [-1, 1]", "min": float(values.min()), "max": float(values.max())}
            )
        if median is None or abs(median - c["ndvi_median"]) > 0.001 or values.size != c["n_pixels_with_value"]:
            problems.append(
                {
                    **entry,
                    "reason": "median or pixel count differs from vegetation.json",
                    "expected_median": c["ndvi_median"],
                    "expected_pixels": c["n_pixels_with_value"],
                }
            )
        if path.stat().st_size != c.get("geotiff_bytes"):
            problems.append(
                {
                    "composite": c["id"],
                    "reason": "file size differs",
                    "bytes": path.stat().st_size,
                    "expected": c.get("geotiff_bytes"),
                }
            )
    return [
        chk(
            "integrity-sentinel2-geotiffs",
            "integrity",
            "sentinel2_l2a_do_luong_vi",
            "fail" if problems else "pass",
            f"{len(read)} ảnh GeoTIFF: hệ tọa độ {grid['crs']}, ô {grid['resolution_m']:g} m, NDVI trong [-1, 1], trung vị và "
            "số điểm ảnh khớp vegetation.json."
            if not problems
            else "Ảnh GeoTIFF ghép mùa không khớp vegetation.json.",
            f"{len(read)} GeoTIFFs: CRS {grid['crs']}, {grid['resolution_m']:g} m pixels, NDVI in [-1, 1], median and pixel "
            "count equal to vegetation.json."
            if not problems
            else "Seasonal composite GeoTIFFs do not match vegetation.json.",
            composites=read,
            problems=problems,
        )  # fmt: skip
    ]


def modis_checks(ndvi: dict | None, manifest: dict | None) -> list[QualityCheck]:
    if ndvi is None:
        return [chk("time-modis-dates", "time", "modis_mod13q1_ndvi", "fail", "Thiếu ndvi_modis.json.",
                    "ndvi_modis.json is missing.")]  # fmt: skip
    dates = [date.fromisoformat(d) for d in ndvi["dates"]]
    dups = [str(d) for d, n in Counter(dates).items() if n > 1]
    # MOD13Q1 composites start on day 1, 17, 33, ... of each year (16-day steps restarting on 1 January)
    off_grid = [str(d) for d in dates if (d.timetuple().tm_yday - 1) % 16 != 0]
    by_year = Counter(d.year for d in dates)
    short_years = {y: n for y, n in by_year.items() if n != 23}
    bad = [
        {"date": ndvi["dates"][i], k: ndvi[k][i]}
        for k in ("median", "p25", "p75")
        for i in range(len(dates))
        if not _in_unit(ndvi[k][i])
    ]
    empty = sum(1 for v in ndvi["median"] if v is None)
    return [
        chk(
            "time-modis-dates", "time", "modis_mod13q1_ndvi", "fail" if dups or off_grid or short_years else "pass",
            f"{len(dates)} ngày MODIS theo đúng chu kỳ 16 ngày, mỗi năm 23 kỳ, không trùng." if not (dups or off_grid or short_years)
            else "Ngày MODIS bị trùng, lệch chu kỳ 16 ngày hoặc thiếu kỳ.",
            f"{len(dates)} MODIS dates on the 16-day cycle, 23 per year, none duplicated." if not (dups or off_grid or short_years)
            else "MODIS dates duplicated, off the 16-day cycle, or periods missing.",
            dates=len(dates), duplicated=dups, off_cycle=off_grid[:20], years_not_23=short_years,
        ),
        chk(
            "units-modis-ndvi", "units_ranges", "modis_mod13q1_ndvi", "fail" if bad else "pass",
            "Có NDVI MODIS ngoài [-1, 1]." if bad else "NDVI MODIS (trung vị, phân vị 25 và 75) đều trong [-1, 1].",
            "MODIS NDVI outside [-1, 1]." if bad else "MODIS NDVI (median, 25th and 75th percentiles) all in [-1, 1].",
            problems=bad[:20],
        ),
        chk(
            "missing-modis-dates", "missing", "modis_mod13q1_ndvi", "warn" if empty else "pass",
            f"{empty} trên {len(dates)} kỳ MODIS không có điểm ảnh tốt (mây); để trống, không nội suy." if empty
            else "Kỳ MODIS nào cũng có điểm ảnh tốt.",
            f"{empty} of {len(dates)} MODIS dates have no good pixel (cloud); left empty, not interpolated." if empty
            else "Every MODIS date has good pixels.",
            dates_without_valid_pixel=empty, reliability_counts=(manifest or {}).get("reliability_counts"),
        ),
        chk(
            "version-modis-collection", "version", "modis_mod13q1_ndvi",
            "pass" if "v061" in str((manifest or {}).get("source_revision", "")) else "warn",
            "MODIS MOD13Q1 bộ sưu tập 6.1 (v061)." if "v061" in str((manifest or {}).get("source_revision", ""))
            else "Không xác định được bộ sưu tập MODIS.",
            "MODIS MOD13Q1 collection 6.1 (v061)." if "v061" in str((manifest or {}).get("source_revision", ""))
            else "The MODIS collection could not be confirmed.",
            source_revision=(manifest or {}).get("source_revision"),
        ),
    ]  # fmt: skip


# ---------------------------------------------------------------- geometry


def _bbox_ok(b: list[float]) -> bool:
    w, s, e, n = b
    return VIETNAM_BBOX[0] <= w < e <= VIETNAM_BBOX[2] and VIETNAM_BBOX[1] <= s < n <= VIETNAM_BBOX[3]


def geometry_checks(
    adm1: dict | None, geo: dict | None, do_luong: dict | None, climate: dict | None, veg: dict | None
) -> list[QualityCheck]:
    from shapely.geometry import Point, Polygon, shape

    out: list[QualityCheck] = []
    nghe_an = None
    if adm1 is not None:
        crs = (adm1.get("crs") or {}).get("properties", {}).get("name", "RFC 7946 default (WGS84)")
        feat = next((f for f in adm1.get("features", []) if f["properties"].get("shapeISO") == "VN-22"), None)
        if feat is None:
            out.append(chk("crs-nghe-an-outline", "crs_bounds", "geoboundaries_adm1", "fail",
                           "Không tìm thấy Nghệ An (VN-22) trong tệp ranh giới tỉnh.", "Nghệ An (VN-22) not found in the province file."))  # fmt: skip
        else:
            nghe_an = shape(feat["geometry"])
            b = [round(v, 4) for v in nghe_an.bounds]
            ok = "CRS84" in crs or "4326" in crs
            out.append(
                chk(
                    "crs-nghe-an-outline",
                    "crs_bounds",
                    "geoboundaries_adm1",
                    "pass" if ok and _bbox_ok(b) else "fail",
                    f"Ranh giới Nghệ An ở hệ WGS84 kinh độ/vĩ độ, khung {b}, nằm trong Việt Nam.",
                    f"Nghệ An outline in WGS84 lon/lat, bbox {b}, inside Viet Nam.",
                    crs=crs,
                    bbox=b,
                    vietnam_bbox=list(VIETNAM_BBOX),
                    area_deg2=round(nghe_an.area, 4),
                )  # fmt: skip
            )
    if geo is not None and nghe_an is not None:
        gb = [round(v, 4) for v in geo["bounds"]]
        nb = [round(v, 4) for v in nghe_an.bounds]
        diff = max(abs(a - b) for a, b in zip(gb, nb, strict=True))
        out.append(
            chk(
                "crs-geo-json-bounds",
                "crs_bounds",
                "geoboundaries_adm1",
                "pass" if diff < 0.01 else "fail",
                f"Khung của geo.json khớp ranh giới Nghệ An gốc (lệch tối đa {diff:.4f}°).",
                f"geo.json bounds match the source Nghệ An outline (largest difference {diff:.4f}°).",
                geo_json_bounds=gb,
                source_bounds=nb,
                max_difference_deg=round(diff, 5),
            )  # fmt: skip
        )
    district = None
    if do_luong is not None and do_luong.get("do_luong"):
        dl = do_luong["do_luong"]
        rings = dl["outline"]
        district = Polygon(rings[0], rings[1:]) if rings and isinstance(rings[0][0], list) else Polygon(rings)
        if nghe_an is not None:
            inside = district.difference(nghe_an).area / district.area if district.area else 1.0
            out.append(
                chk(
                    "crs-do-luong-in-nghe-an",
                    "crs_bounds",
                    "geoboundaries_vnm_adm2_do_luong",
                    "pass" if inside < 0.01 else "fail",
                    f"Đô Lương nằm trong Nghệ An ({(1 - inside) * 100:.2f}% diện tích nằm trong ranh giới tỉnh).",
                    f"Đô Lương lies inside Nghệ An ({(1 - inside) * 100:.2f}% of its area inside the province outline).",
                    share_outside=round(inside, 5),
                    do_luong_bbox=dl.get("bbox"),
                )  # fmt: skip
            )
        sp = do_luong.get("study_point")
        if sp:
            ok = district.contains(Point(sp["lon"], sp["lat"]))
            out.append(
                chk(
                    "crs-study-point-in-do-luong",
                    "crs_bounds",
                    "geoboundaries_vnm_adm2_do_luong",
                    "pass" if ok else "fail",
                    "Điểm Lưu Sơn (Wikidata) nằm trong ranh giới Đô Lương."
                    if ok
                    else "Điểm Lưu Sơn nằm ngoài Đô Lương.",
                    "The Lưu Sơn point (Wikidata) lies inside the Đô Lương outline."
                    if ok
                    else "The Lưu Sơn point lies outside Đô Lương.",
                    lat=sp["lat"],
                    lon=sp["lon"],
                )  # fmt: skip
            )
    if climate is not None and nghe_an is not None:
        from shapely.geometry import box

        w, s, e, n = nghe_an.bounds
        cells = []
        for c in climate["cells"]:
            foot = box(c["lon"] - 0.3125, c["lat"] - 0.25, c["lon"] + 0.3125, c["lat"] + 0.25)
            cells.append(
                {"id": c["id"], "weight": round(c["weight"], 4),
                 "centre_in_bbox": w <= c["lon"] <= e and s <= c["lat"] <= n,
                 "centre_in_outline": nghe_an.contains(Point(c["lon"], c["lat"])),
                 "footprint_share_in_outline": round(foot.intersection(nghe_an).area / foot.area, 3)}
            )  # fmt: skip
        disjoint = [c["id"] for c in cells if c["footprint_share_in_outline"] == 0]
        centre_out = [c["id"] for c in cells if not c["centre_in_bbox"]]
        status = "fail" if disjoint else ("warn" if centre_out else "pass")
        out.append(
            chk(
                "crs-power-cells-in-bbox",
                "crs_bounds",
                "nasa_power_daily",
                status,
                ("Có ô NASA POWER không chạm tới Nghệ An: " + ", ".join(disjoint) + ".")
                if disjoint
                else (
                    "Cả 5 ô NASA POWER đều phủ một phần Nghệ An, nhưng tâm ô "
                    + ", ".join(centre_out)
                    + " nằm ngoài khung "
                    "tỉnh (ở phía nam). Giá trị của ô đó là trung bình cả ô, gồm cả đất ngoài Nghệ An; trọng số đất trồng chỉ "
                    "tính phần đất trồng trong tỉnh."
                )
                if centre_out
                else "Tâm 5 ô NASA POWER nằm trong khung Nghệ An và mỗi ô phủ một phần tỉnh.",
                ("A NASA POWER cell does not touch Nghệ An: " + ", ".join(disjoint) + ".")
                if disjoint
                else (
                    "All 5 NASA POWER cells cover part of Nghệ An, but the centre of "
                    + ", ".join(centre_out)
                    + " lies "
                    "outside the province bbox (to the south). That cell's value is a whole-cell mean that includes land "
                    "outside Nghệ An; the farmland weight counts only farmland inside the province."
                )
                if centre_out
                else "The 5 NASA POWER cell centres lie inside the Nghệ An bbox and every cell covers part of the province.",
                cells=cells,
                nghe_an_bbox=[round(v, 4) for v in nghe_an.bounds],
                weights_sum=round(sum(c["weight"] for c in climate["cells"]), 6),
            )  # fmt: skip
        )
    if veg is not None and do_luong is not None and do_luong.get("do_luong"):
        db = do_luong["do_luong"]["bbox"]
        worst = max(max(abs(a - b) for a, b in zip(c["bounds"], db, strict=True)) for c in veg["composites"])
        utm_zone = int((sum(db[0::2]) / 2 + 180) // 6) + 1
        ok = worst < 0.002 and veg["grid"]["crs"] == f"EPSG:{32600 + utm_zone}"
        out.append(
            chk(
                "crs-sentinel2-grid",
                "crs_bounds",
                "sentinel2_l2a_do_luong_vi",
                "pass" if ok else "fail",
                f"Lưới Sentinel-2 ở {veg['grid']['crs']} (UTM vùng {utm_zone}B, đúng cho Đô Lương); khung ảnh ghép lệch "
                f"khung huyện tối đa {worst:.4f}° (dưới một điểm ảnh 20 m).",
                f"Sentinel-2 grid in {veg['grid']['crs']} (UTM zone {utm_zone}N, right for Đô Lương); composite bounds "
                f"differ from the district bbox by at most {worst:.4f}° (under one 20 m pixel).",
                grid=veg["grid"],
                utm_zone=utm_zone,
                max_bounds_difference_deg=round(worst, 6),
            )  # fmt: skip
        )
    return out


# ---------------------------------------------------------------- resolution, licences, versions, availability


def resolution_checks(climate: dict | None, veg: dict | None) -> list[QualityCheck]:
    power_keys = sorted((climate or {}).get("series", {}).get("cells", {}))
    point_series = [k for k in power_keys if not k[0].isdigit()]
    weather_in_veg = [k for k in (veg or {}) if any(w in k for w in ("rain", "precip", "t2m", "temperature"))]
    ok = not point_series and not weather_in_veg
    cell_km = (0.5 * 111.0, 0.625 * 111.0 * 0.946)  # degrees to km at about 19° N (cos 19° = 0.946)
    cell_area = cell_km[0] * cell_km[1]
    return [
        chk(
            "resolution-power-not-downscaled", "resolution", "nasa_power_daily", "pass" if ok else "fail",
            "NASA POWER chỉ có ở 5 ô lưới và vùng đất trồng cân trọng số; không có chuỗi thời tiết nào được chia nhỏ "
            "xuống điểm xã hay điểm ảnh 20 m." if ok else "Có chuỗi thời tiết NASA POWER ở độ phân giải mịn hơn lưới gốc.",
            "NASA POWER exists only for the 5 grid cells and the farmland-weighted area; no weather series is "
            "downscaled to a commune point or a 20 m pixel." if ok else "A NASA POWER series appears at a finer "
            "resolution than its grid.",
            power_series=power_keys, point_series=point_series, weather_fields_in_vegetation=weather_in_veg,
        ),
        chk(
            "resolution-mismatch-note", "resolution", None, "warn",
            f"Các nguồn có độ phân giải rất khác nhau: một ô NASA POWER rộng khoảng {cell_area:,.0f} km², CHIRPS 0,05° "
            "(khoảng 5,5 km), MODIS 250 m, Sentinel-2 20 m. Chúng được đặt cạnh nhau, không bao giờ nội suy thời tiết "
            "xuống ruộng.",
            f"The sources differ greatly in resolution: one NASA POWER cell covers about {cell_area:,.0f} km², CHIRPS "
            "0.05° (about 5.5 km), MODIS 250 m, Sentinel-2 20 m. They are shown side by side; weather is never "
            "interpolated down to a field.",
            power_cell_km=[round(v, 1) for v in cell_km], power_cell_area_km2=round(cell_area),
            chirps_deg=0.05, modis_m=250, sentinel2_m=20,
            power_cell_to_sentinel2_pixel_ratio=round(cell_area * 1e6 / 400),
        ),
    ]  # fmt: skip


def licence_checks(
    catalog: dict | None, veg: dict | None, gibs: dict | None, do_luong: dict | None, docs: dict | None
) -> list[QualityCheck]:
    out: list[QualityCheck] = []
    for d in (catalog or {}).get("datasets", []):
        lic = (d.get("license") or "").strip()
        status, vi, en = "pass", f"Có giấy phép: {lic[:120]}", f"Licence recorded: {lic[:120]}"
        if not lic:
            status, vi, en = "fail", "Không ghi giấy phép.", "No licence recorded."
        elif "as recorded by the team" in lic:
            status = "warn"
            vi = (
                "Giấy phép do nhóm ghi lại; tệp ranh giới tỉnh đã lưu không mang thông tin giấy phép, trong khi lớp "
                "huyện cùng nguồn (OCHA ROAP) theo CC BY 3.0 IGO. Cần đối chiếu siêu dữ liệu geoBoundaries ADM1."
            )
            en = (
                "Licence recorded by the team; the cached province file carries no licence metadata, while the "
                "district layer of the same source (OCHA ROAP) is CC BY 3.0 IGO. Check the geoBoundaries ADM1 metadata."
            )
        out.append(chk(f"licence-{d['dataset_id']}", "licence", d["dataset_id"], status, vi, en, license=lic))
    attribution = (veg or {}).get("attribution", "")
    out.append(
        chk(
            "licence-sentinel2-attribution",
            "licence",
            "sentinel2_l2a_do_luong_vi",
            "pass" if "Contains modified Copernicus Sentinel data" in attribution else "fail",
            "Có câu ghi công bắt buộc của Copernicus."
            if attribution
            else "Thiếu câu ghi công bắt buộc của Copernicus.",
            "The required Copernicus attribution is present."
            if attribution
            else "The required Copernicus attribution is missing.",
            attribution=attribution,
        )  # fmt: skip
    )
    ack = (gibs or {}).get("acknowledgement")
    policy = ((gibs or {}).get("data_use_policy") or {}).get("fetch_status", "")
    out.append(
        chk(
            "licence-gibs-acknowledgement",
            "licence",
            "nasa_gibs",
            "warn" if ack and "403" in policy else ("pass" if ack else "fail"),
            "Có câu ghi công GIBS; trang chính sách dữ liệu của NASA trả lỗi 403 cho yêu cầu tự động nên chưa đọc lại."
            if ack and "403" in policy
            else ("Có câu ghi công GIBS." if ack else "Thiếu câu ghi công GIBS."),
            "The GIBS acknowledgement is present; NASA's data-use page answered 403 to automated requests, so it was "
            "not re-read."
            if ack and "403" in policy
            else ("The GIBS acknowledgement is present." if ack else "The GIBS acknowledgement is missing."),
            acknowledgement=ack,
            policy_fetch_status=policy,
        )  # fmt: skip
    )
    dl = (do_luong or {}).get("do_luong") or {}
    out.append(
        chk(
            "licence-do-luong-boundary",
            "licence",
            "geoboundaries_vnm_adm2_do_luong",
            "pass" if dl.get("license") else "fail",
            f"Ranh giới Đô Lương: {dl.get('license')}; ghi công geoBoundaries và OCHA ROAP.",
            f"Đô Lương outline: {dl.get('license')}; credit geoBoundaries and OCHA ROAP.",
            license=dl.get("license"),
            source=dl.get("source"),
        )  # fmt: skip
    )
    for d in (docs or {}).get("documents", []):
        if d.get("status") == "RECORDED_ONLY":
            stored = bool(d.get("chunks_file"))
            out.append(
                chk(
                    f"licence-document-{d['doc_id']}",
                    "licence",
                    "evidence_documents",
                    "fail" if stored else "pass",
                    "Bài báo P-02 không có giấy phép mở: chỉ ghi lại thông tin, không lưu toàn văn, không chia đoạn."
                    if not stored
                    else "Văn bản không có giấy phép mở nhưng lại được lưu toàn văn.",
                    "The P-02 paper has no open licence: recorded only, full text not stored, no chunks."
                    if not stored
                    else "A document without an open licence has its full text stored.",
                    document_status=d.get("status"),
                    chunks_file=d.get("chunks_file"),
                )  # fmt: skip
            )
    return out


def version_document_checks(docs: dict | None) -> list[QualityCheck]:
    out: list[QualityCheck] = []
    for d in (docs or {}).get("documents", []):
        notes = " ".join(d.get("notes", []))
        if d["doc_id"] == "nd112_2024":
            amended = "amended" in notes
            out.append(
                chk(
                    "version-document-nd112_2024",
                    "version",
                    "evidence_documents",
                    "warn" if amended else "pass",
                    "Nghị định 112/2024 được lưu theo lời văn gốc năm 2024; đã được sửa bởi NĐ 151/2025 và NĐ 226/2025. "
                    "Cần xem văn bản hợp nhất trước khi hướng dẫn thủ tục."
                    if amended
                    else "Không có ghi chú sửa đổi.",
                    "Decree 112/2024 is stored in its original 2024 wording; it was amended by Decrees 151/2025 and "
                    "226/2025. Check the consolidated text before giving procedural advice."
                    if amended
                    else "No amendment noted.",
                    legal_force=(d.get("source_metadata") or {}).get("legislationLegalForce (schema.org on the page)"),
                )  # fmt: skip
            )
        if d["doc_id"] == "qd18_2021":
            unchecked = "not re-checked" in notes
            out.append(
                chk(
                    "version-document-qd18_2021",
                    "version",
                    "evidence_documents",
                    "warn" if unchecked else "pass",
                    "Hiệu lực hiện hành của Quyết định 18/2021 chưa được kiểm tra lại trong lần tải này."
                    if unchecked
                    else "Đã kiểm tra hiệu lực.",
                    "The current legal force of Decision 18/2021 was not re-checked in this fetch."
                    if unchecked
                    else "Legal force checked.",
                    retrieved_at=d.get("retrieved_at"),
                )  # fmt: skip
            )
    return out


def availability_checks(catalog: dict | None, do_luong: dict | None) -> list[QualityCheck]:
    blocked = [d["dataset_id"] for d in (catalog or {}).get("datasets", []) if d["ingestion_status"] == "BLOCKED"]
    out = [
        chk(
            "missing-earthdata-products", "missing", None, "warn" if blocked else "pass",
            f"{len(blocked)} sản phẩm NASA Earthdata (HLS, SMAP, GPM IMERG, ECOSTRESS) đã tìm thấy nhưng chưa tải: cần "
            "tài khoản Earthdata miễn phí. Không có số nào từ chúng được hiển thị." if blocked else "Không có sản phẩm bị chặn.",
            f"{len(blocked)} NASA Earthdata products (HLS, SMAP, GPM IMERG, ECOSTRESS) were found but not downloaded: a "
            "free Earthdata Login is needed. No number from them is shown." if blocked else "No blocked product.",
            blocked=blocked,
        )
    ]  # fmt: skip
    status = (do_luong or {}).get("luu_son_status") or {}
    if status.get("status") == "UNAVAILABLE":
        out.append(
            chk(
                "missing-luu-son-boundary",
                "missing",
                "geoboundaries_vnm_adm2_do_luong",
                "warn",
                "Không có ranh giới xã Lưu Sơn (geoBoundaries không có lớp xã của Việt Nam); chỉ vẽ một điểm đánh dấu.",
                "No Lưu Sơn commune outline (geoBoundaries has no Vietnamese commune layer); only a marker point is drawn.",
                reason=status.get("reason"),
            )  # fmt: skip
        )
    return out


def share_checks(hazards: dict | None, soil: dict | None) -> list[QualityCheck]:
    bad = []
    for rule, values in (hazards or {}).get("year_level", {}).items():
        bad += [{"rule": rule, "i": i, "v": v} for i, v in enumerate(values) if v is not None and not 0 <= v <= 1]
    for crop, rules in (hazards or {}).get("crop_level", {}).items():
        for rule, values in rules.items():
            bad += [{"crop": crop, "rule": rule, "v": v} for v in values if v is not None and not 0 <= v <= 1]
    for crop, entry in (soil or {}).get("crops", {}).items():
        bad += [{"soil": crop, "v": v} for v in entry.get("values", []) if v is not None and not 0 <= v <= 1]
    return [
        chk(
            "units-shares-0-1", "units_ranges", "e019_hazard_labels", "fail" if bad else "pass",
            "Có phần đất trồng hoặc độ ẩm đất ngoài khoảng 0-1." if bad else "Mọi phần đất trồng (E-019) và độ ẩm đất (E-020) đều trong 0-1.",
            "A farmland share or soil wetness is outside 0-1." if bad else "Every farmland share (E-019) and soil wetness (E-020) is within 0-1.",
            problems=bad[:20],
        )
    ]  # fmt: skip


# ---------------------------------------------------------------- report


def run_checks(root: Path = ROOT, canonical_dir: Path | None = None) -> QualityReport:
    canon = canonical_dir or root / "data" / "canonical"
    raw = root / "data" / "raw"

    def load(name: str) -> dict | None:
        return read_json(canon / name)

    climate, catalog, veg = load("climate.json"), load("catalog.json"), load("vegetation.json")
    do_luong, gibs, ndvi = load("geo_do_luong.json"), load("gibs_layers.json"), load("ndvi_modis.json")
    docs = read_json(raw / "documents" / "MANIFEST.json")
    s2_manifest = read_json(raw / "sentinel2" / "MANIFEST.json")
    checks: list[QualityCheck] = []
    checks += integrity_checks(root, catalog, climate)
    checks += composite_raster_checks(veg, root)
    checks += power_checks([raw / "power", raw / "power_t2m"], root)
    checks.append(leap_year_check(root, climate))
    checks += climate_canonical_checks(climate)
    checks += chirps_checks(raw / "chirps_v3" / "chirps_v3_monthly_nghe_an.csv", root)
    checks += vegetation_checks(veg, raw / "sentinel2" / "scenes.csv", s2_manifest, root)
    checks += modis_checks(ndvi, read_json(raw / "modis_mod13q1" / "MANIFEST.json"))
    checks += geometry_checks(
        read_json(raw / "boundaries" / "geoBoundaries-VNM-ADM1_simplified.geojson"),
        load("geo.json"),
        do_luong,
        climate,
        veg,
    )
    checks += share_checks(load("hazards.json"), load("soil.json"))
    checks += resolution_checks(climate, veg)
    checks += licence_checks(catalog, veg, gibs, do_luong, docs)
    checks += version_document_checks(docs)
    checks += availability_checks(catalog, do_luong)
    counts = Counter(c.status for c in checks)
    return QualityReport(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        script=SCRIPT,
        counts={"pass": counts["pass"], "warn": counts["warn"], "fail": counts["fail"], "total": len(checks)},
        checks=checks,
    )


def write_report(report: QualityReport, canonical_dir: Path | None = None) -> Path:
    out = (canonical_dir or ROOT / "data" / "canonical") / "quality.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    return out


def main() -> None:
    report = run_checks()
    path = write_report(report)
    failing = [c.check_id for c in report.checks if c.status == "fail"]
    sys.stdout.write(
        f"quality: {report.counts['pass']} pass, {report.counts['warn']} warn, {report.counts['fail']} fail "
        f"-> {rel(path, ROOT)}\n" + (f"failing: {', '.join(failing)}\n" if failing else "")
    )


if __name__ == "__main__":
    main()
