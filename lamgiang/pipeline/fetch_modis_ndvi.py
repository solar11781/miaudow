"""Fetch MODIS MOD13Q1 v061 NDVI (250 m, 16-day) around the Lưu Sơn study site from the ORNL DAAC subset API.

Source: ORNL DAAC MODIS/VIIRS Land Product Subsets REST API, https://modis.ornl.gov/rst/api/v1/
Product: MOD13Q1 v061 (doi:10.5067/MODIS/MOD13Q1.061), bands 250m_16_days_NDVI and 250m_16_days_pixel_reliability,
         kmAboveBelow=1, kmLeftRight=1 around the study point (a small block of 250 m pixels).
The API allows at most 10 composite dates per request; every response is cached as JSON in
data/cache/modis_mod13q1/ (git-ignored) so a rerun resumes.

Scaling: NDVI = raw * 0.0001. A pixel is valid only when its reliability is 0 (good) or 1 (marginal) and its raw NDVI
is not the fill value -3000 and within -2000..10000. Invalid pixels stay in the CSV with an empty ndvi and
valid=false; they are never dropped silently and never filled.

Run:   .venv\\Scripts\\python.exe pipeline\\fetch_modis_ndvi.py [--start 2015 --end 2024]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://modis.ornl.gov/rst/api/v1/"
PRODUCT = "MOD13Q1"
BAND_NDVI = "250m_16_days_NDVI"
BAND_REL = "250m_16_days_pixel_reliability"
USER_AGENT = "MiaudowResearch/1.0 (NASA Space Apps 2026 hackathon)"
SITE = {"lat": 18.89638889, "lon": 105.2802778, "source_url": "https://www.wikidata.org/wiki/Q10788283"}
KM = 1
SCALE = 0.0001
NDVI_FILL = -3000
NDVI_VALID_RANGE = (-2000, 10000)
VALID_RELIABILITY = {0, 1}
CACHE_DIR = ROOT / "data" / "cache" / "modis_mod13q1"
OUT_DIR = ROOT / "data" / "raw" / "modis_mod13q1"
OUT_PIXELS = OUT_DIR / "ndvi_study_site.csv"
OUT_SUMMARY = OUT_DIR / "ndvi_study_site_summary.csv"
MANIFEST = OUT_DIR / "MANIFEST.json"


# ----------------------------------------------------------------------------------------------- pure functions
def scale_ndvi(raw: int | float | None) -> float | None:
    """Raw MOD13Q1 NDVI integer to NDVI; fill or out-of-range values give None."""
    if raw is None:
        return None
    r = float(raw)
    if r == NDVI_FILL or not (NDVI_VALID_RANGE[0] <= r <= NDVI_VALID_RANGE[1]):
        return None
    return round(r * SCALE, 4)


def pixel_record(raw_ndvi, reliability) -> tuple[float | None, bool]:
    """(ndvi or None, valid): valid only for reliability 0/1 and an in-range NDVI; otherwise NDVI is reported missing."""
    ndvi = scale_ndvi(raw_ndvi)
    rel_ok = reliability is not None and int(reliability) in VALID_RELIABILITY
    if not rel_ok or ndvi is None:
        return None, False
    return ndvi, True


def percentile(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolation percentile (numpy 'linear' method) of an already sorted list."""
    if not sorted_vals:
        raise ValueError("empty")
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def summarise(values: list[float | None]) -> dict:
    valid = sorted(v for v in values if v is not None)
    if not valid:
        return {"n_valid": 0, "n_total": len(values), "ndvi_median": "", "ndvi_p25": "", "ndvi_p75": ""}
    return {
        "n_valid": len(valid),
        "n_total": len(values),
        "ndvi_median": round(statistics.median(valid), 4),
        "ndvi_p25": round(percentile(valid, 0.25), 4),
        "ndvi_p75": round(percentile(valid, 0.75), 4),
    }


def doy_of(modis_date: str) -> int:
    """'A2020177' -> 177."""
    return int(modis_date[5:])


def chunks(seq: list, n: int) -> list[list]:
    return [seq[i : i + n] for i in range(0, len(seq), n)]


# ----------------------------------------------------------------------------------------------- I/O
def get_json(url: str, params: dict, tries: int = 6, timeout: float = 300.0) -> dict:
    import httpx

    delay = 10.0
    last = None
    for attempt in range(tries):
        try:
            r = httpx.get(
                url, params=params, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=timeout
            )
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code not in (429, 500, 502, 503, 504):
                raise RuntimeError(last)
        except (httpx.HTTPError, ValueError) as exc:
            last = repr(exc)
        print(f"  retry {attempt + 1} for {url} {params.get('startDate', '')}: {last}", file=sys.stderr)
        time.sleep(delay)
        delay = min(delay * 2, 120)
    raise RuntimeError(f"giving up: {url} {params}: {last}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def fetch(start_year: int, end_year: int) -> tuple[list[str], list[str]]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dates_cache = CACHE_DIR / "dates.json"
    if not dates_cache.exists():
        d = get_json(API + f"{PRODUCT}/dates", {"latitude": SITE["lat"], "longitude": SITE["lon"]})
        dates_cache.write_text(json.dumps(d), encoding="utf-8")
    all_dates = json.loads(dates_cache.read_text(encoding="utf-8"))["dates"]
    wanted = [d["modis_date"] for d in all_dates if start_year <= int(d["modis_date"][1:5]) <= end_year]
    failed = []
    groups = chunks(wanted, 10)
    # the trial years 2020-2021 first, so an interrupted run still has them
    groups.sort(key=lambda g: (not any(m[1:5] in ("2020", "2021") for m in g), g[0]))
    for group in groups:
        for band in (BAND_NDVI, BAND_REL):
            out = CACHE_DIR / f"{band}_{group[0]}_{group[-1]}.json"
            if out.exists():
                continue
            params = {
                "latitude": SITE["lat"],
                "longitude": SITE["lon"],
                "band": band,
                "startDate": group[0],
                "endDate": group[-1],
                "kmAboveBelow": KM,
                "kmLeftRight": KM,
            }
            try:
                data = get_json(API + f"{PRODUCT}/subset", params)
                out.write_text(json.dumps(data), encoding="utf-8")
                print(f"  {band} {group[0]}..{group[-1]}: {len(data.get('subset', []))} dates")
            except Exception as exc:  # noqa: BLE001 - keep going; the gap is reported
                failed.append(f"{band} {group[0]}..{group[-1]}: {exc}")
                print(f"FAILED {band} {group[0]}..{group[-1]}: {exc}", file=sys.stderr)
            time.sleep(1.0)
    return wanted, failed


def load_band(band: str) -> tuple[dict[str, dict], dict]:
    by_date: dict[str, dict] = {}
    header: dict = {}
    for f in sorted(CACHE_DIR.glob(f"{band}_A*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        header = {
            k: d.get(k)
            for k in (
                "xllcorner",
                "yllcorner",
                "cellsize",
                "nrows",
                "ncols",
                "latitude",
                "longitude",
                "header",
                "units",
                "scale",
            )
        }
        for s in d.get("subset", []):
            by_date[s["modis_date"]] = s
    return by_date, header


def build(wanted: list[str], failed: list[str]) -> dict:
    ndvi, hdr_n = load_band(BAND_NDVI)
    rel, hdr_r = load_band(BAND_REL)
    if (
        hdr_n
        and hdr_r
        and (hdr_n["nrows"], hdr_n["ncols"], hdr_n["xllcorner"], hdr_n["yllcorner"])
        != (hdr_r["nrows"], hdr_r["ncols"], hdr_r["xllcorner"], hdr_r["yllcorner"])
    ):
        raise SystemExit("NDVI and reliability grids differ; refusing to pair them")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pix_rows, sum_rows = [], []
    missing_dates = []
    proc_dates = set()
    for md in wanted:
        if md not in ndvi or md not in rel:
            missing_dates.append(md)
            continue
        sn, sr = ndvi[md], rel[md]
        if len(sn["data"]) != len(sr["data"]):
            raise SystemExit(f"{md}: NDVI and reliability pixel counts differ")
        proc_dates.add(sn.get("proc_date"))
        vals = []
        for i, (raw, r) in enumerate(zip(sn["data"], sr["data"], strict=True)):
            v, ok = pixel_record(raw, r)
            vals.append(v)
            pix_rows.append(
                {
                    "date": sn["calendar_date"],
                    "doy": doy_of(md),
                    "pixel_index": i,
                    "ndvi": "" if v is None else f"{v:.4f}",
                    "reliability": r,
                    "valid": str(ok).lower(),
                }
            )
        sum_rows.append({"date": sn["calendar_date"], **summarise(vals)})
    with open(OUT_PIXELS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["date", "doy", "pixel_index", "ndvi", "reliability", "valid"], lineterminator="\n"
        )
        w.writeheader()
        w.writerows(pix_rows)
    with open(OUT_SUMMARY, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["date", "n_valid", "n_total", "ndvi_median", "ndvi_p25", "ndvi_p75"], lineterminator="\n"
        )
        w.writeheader()
        w.writerows(sum_rows)
    return {
        "pix_rows": pix_rows,
        "sum_rows": sum_rows,
        "missing_dates": missing_dates,
        "header": hdr_n,
        "proc_dates": sorted(p for p in proc_dates if p),
        "failed": failed,
    }


def write_manifest(res: dict, start_year: int, end_year: int) -> None:
    pix, summ = res["pix_rows"], res["sum_rows"]
    n_invalid = sum(1 for r in pix if r["valid"] == "false")
    rel_counts: dict[str, int] = {}
    for r in pix:
        rel_counts[str(r["reliability"])] = rel_counts.get(str(r["reliability"]), 0) + 1
    no_valid_dates = [r["date"] for r in summ if r["n_valid"] == 0]
    dates = [r["date"] for r in summ]
    status = "INGESTED" if not res["missing_dates"] and not res["failed"] else ("PARTIAL" if pix else "BLOCKED")
    h = res["header"] or {}
    manifest = {
        "dataset_id": "modis_mod13q1_ndvi_study_site",
        "title": {
            "vi": "Chỉ số NDVI MODIS MOD13Q1 (250 m, 16 ngày) quanh điểm xã Lưu Sơn, Đô Lương",
            "en": "MODIS MOD13Q1 NDVI (250 m, 16-day) around the Lưu Sơn, Đô Lương study point",
        },
        "provider": "NASA LP DAAC (MOD13Q1 v061), subset served by ORNL DAAC MODIS/VIIRS Land Product Subsets",
        "source_id": "MOD13Q1.061",
        "source_url": API + f"{PRODUCT}/subset",
        "license": (
            "No restrictions on reuse, sale or redistribution under the NASA Earth Science Data and "
            "Information Policy (https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance); "
            "cite the product DOI and the ORNL DAAC subset tool"
        ),
        "source_revision": f"MOD13Q1 collection 6.1 (v061); processing dates reported by the API: "
        f"{res['proc_dates'][0] if res['proc_dates'] else '?'} to "
        f"{res['proc_dates'][-1] if res['proc_dates'] else '?'}",
        "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temporal_coverage": f"{dates[0] if dates else '?'} to {dates[-1] if dates else '?'} "
        f"(16-day composites, requested years {start_year}-{end_year})",
        "spatial_resolution": "250 m (231.66 m sinusoidal grid cell)",
        "geometry_crs": "MODIS Sinusoidal (SR-ORG:6974); point given in EPSG:4326",
        "variables": [
            "ndvi (unitless, raw x 0.0001)",
            "reliability (0 good, 1 marginal, 2 snow/ice, 3 cloudy, -1 fill)",
            "valid",
        ],
        "missing_policy": (
            "NDVI is reported only for pixels with reliability 0 or 1 and raw NDVI within -2000..10000 "
            "(fill -3000 excluded). Every other pixel is kept with an empty ndvi and valid=false; "
            "nothing is filled or interpolated. Per-date statistics use valid pixels only and are "
            "empty when a date has no valid pixel."
        ),
        "allowed_use": {
            "vi": "Mô tả độ xanh của mặt đất theo thời gian quanh điểm nghiên cứu; không phải chẩn đoán sức khỏe cây trồng.",
            "en": "Describe the greenness of the land surface over time around the study point; not a crop-health diagnosis.",
        },
        "version_sha256": sha256_file(OUT_PIXELS),
        "summary_sha256": sha256_file(OUT_SUMMARY),
        "ingestion_status": status,
        "is_field_measurement": False,
        "files": {
            "pixels": OUT_PIXELS.relative_to(ROOT).as_posix(),
            "summary": OUT_SUMMARY.relative_to(ROOT).as_posix(),
            "script": "pipeline/fetch_modis_ndvi.py",
        },
        "request": {
            "product": PRODUCT,
            "bands": [BAND_NDVI, BAND_REL],
            "latitude": SITE["lat"],
            "longitude": SITE["lon"],
            "kmAboveBelow": KM,
            "kmLeftRight": KM,
            "site_source_url": SITE["source_url"],
        },
        "grid": {k: h.get(k) for k in ("nrows", "ncols", "cellsize", "xllcorner", "yllcorner")},
        "row_count_pixels": len(pix),
        "row_count_dates": len(summ),
        "pixels_invalid": n_invalid,
        "reliability_counts": rel_counts,
        "dates_without_valid_pixel": len(no_valid_dates),
        "dates_not_retrieved": res["missing_dates"],
        "failed_requests": res["failed"],
        "citations": [
            "Didan, K. (2021). MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061. NASA EOSDIS Land "
            "Processes Distributed Active Archive Center. https://doi.org/10.5067/MODIS/MOD13Q1.061",
            "ORNL DAAC. 2018. MODIS and VIIRS Land Products Global Subsetting and Visualization Tool. ORNL DAAC, "
            "Oak Ridge, Tennessee, USA. https://doi.org/10.3334/ORNLDAAC/1379",
        ],
        "notes": [
            {
                "vi": "NDVI cho biết độ xanh của mặt đất; nó không phải là chẩn đoán sức khỏe cây trồng, sâu bệnh hay độ ẩm đất. Một điểm ảnh 250 m gộp nhiều thửa ruộng (và cả nhà, đường, cây lâu năm).",
                "en": "NDVI shows the greenness of the land surface; it is not a diagnosis of crop health, disease or soil moisture. A 250 m pixel mixes several fields (and houses, roads, perennial trees).",
            },
            {
                "vi": "Vị trí là điểm đánh dấu xã Lưu Sơn trên Wikidata (Q10788283), không phải ruộng thử nghiệm; ô ±1 km quanh điểm đó.",
                "en": "The location is the Lưu Sơn commune marker on Wikidata (Q10788283), not the trial field; the block is +/-1 km around it.",
            },
            {
                "vi": "Ngày trong tệp là ngày bắt đầu của kỳ tổng hợp 16 ngày; ngày quan sát thật của mỗi điểm ảnh có thể là bất kỳ ngày nào trong kỳ.",
                "en": "The date is the first day of the 16-day composite period; each pixel's actual observation day can be any day in that period.",
            },
            {
                "vi": "Độ tin cậy 0 = tốt, 1 = tạm dùng, 2 = tuyết/băng, 3 = mây; chỉ 0 và 1 được coi là hợp lệ. Mùa mưa nhiều mây nên nhiều kỳ có ít điểm ảnh hợp lệ.",
                "en": "Reliability 0 = good, 1 = marginal, 2 = snow/ice, 3 = cloudy; only 0 and 1 count as valid. The cloudy wet season leaves many periods with few valid pixels.",
            },
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=int, default=2015)
    ap.add_argument("--end", type=int, default=2024)
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    if args.no_fetch:
        dates = json.loads((CACHE_DIR / "dates.json").read_text(encoding="utf-8"))["dates"]
        wanted = [d["modis_date"] for d in dates if args.start <= int(d["modis_date"][1:5]) <= args.end]
        failed: list[str] = []
    else:
        wanted, failed = fetch(args.start, args.end)
    res = build(wanted, failed)
    write_manifest(res, args.start, args.end)
    print(
        f"wrote {OUT_PIXELS} ({len(res['pix_rows'])} rows), {OUT_SUMMARY} ({len(res['sum_rows'])} dates); "
        f"missing dates {len(res['missing_dates'])}, failed requests {len(failed)}"
    )


if __name__ == "__main__":
    main()
