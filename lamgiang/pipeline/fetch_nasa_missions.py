"""NASA mission products that need an Earthdata Login: public discovery now, real download when credentials exist.

Products (all cloud-hosted in NASA Earthdata Cloud):
  HLSS30 / HLSL30 v2.0      Harmonized Landsat Sentinel-2 surface reflectance, 30 m        LP DAAC (LPCLOUD)
  SPL3SMP_E v006            SMAP enhanced L3 radiometer soil moisture, 9 km EASE-Grid 2.0  NSIDC DAAC
  SPL4SMGP v008             SMAP L4 surface/root-zone soil moisture, 9 km, 3-hourly        NSIDC DAAC
  GPM_3IMERGDF / M v07      GPM IMERG Final precipitation, 0.1°, daily / monthly            GES DISC
  ECO_L2T_LSTE v002         ECOSTRESS tiled land surface temperature, 70 m                  LP DAAC
  ECO_L3T_JET v002          ECOSTRESS tiled evapotranspiration (JET ensemble), 70 m         LP DAAC

Discovery (no login): NASA CMR search API, https://cmr.earthdata.nasa.gov/search/ (collections.json for the
collection record, granules.json with bounding_box + temporal; the hit count comes from the CMR-Hits header), and
CMR-STAC for HLS (https://cmr.earthdata.nasa.gov/stac/LPCLOUD). One data URL per product is then requested WITHOUT
credentials and without following the redirect, to record the honest access status (expected: HTTP 302/303 to
urs.earthdata.nasa.gov, i.e. an Earthdata Login is required). Nothing is bypassed.

Download (only with credentials): a free Earthdata Login account (https://urs.earthdata.nasa.gov/users/new), then
either the environment variables EARTHDATA_USERNAME and EARTHDATA_PASSWORD, or a ~/.netrc (Windows: %USERPROFILE%\\
_netrc or .netrc) line `machine urs.earthdata.nasa.gov login <user> password <pass>`. Some DAACs also require the
application to be authorised once in the Earthdata profile (e.g. "NASA GESDISC DATA ARCHIVE" for IMERG).
The password is sent only to urs.earthdata.nasa.gov (never to a data host); cookies set during the OAuth redirect
chain are kept in the client.

Run:   .venv\\Scripts\\python.exe pipeline\\fetch_nasa_missions.py --discover          (writes STATUS.json)
       .venv\\Scripts\\python.exe pipeline\\fetch_nasa_missions.py --download HLSS30 --limit 2
"""

from __future__ import annotations

import argparse
import base64
import json
import netrc
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "MiaudowResearch/1.0 (NASA Space Apps 2026 hackathon)"
CMR = "https://cmr.earthdata.nasa.gov/search"
CMR_STAC_LPCLOUD = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD"
URS_HOST = "urs.earthdata.nasa.gov"
GEO_FILE = ROOT / "data" / "canonical" / "geo_do_luong.json"
OUT = ROOT / "data" / "raw" / "nasa_missions" / "STATUS.json"
CACHE = ROOT / "data" / "cache" / "nasa_missions"
TEMPORAL = ("2020-01-01T00:00:00Z", "2021-12-31T23:59:59Z")
FALLBACK_BBOX = [105.219672, 18.775349, 105.485593, 19.056227]


@dataclass(frozen=True)
class Product:
    short_name: str
    version: str
    daac: str
    resolution: str
    use: str
    stac_collection: str | None = None


PRODUCTS = [
    Product(
        "HLSS30",
        "2.0",
        "LP DAAC (LPCLOUD)",
        "30 m, 2-3 day revisit with HLSL30",
        "field-scale vegetation time series (NDVI/EVI) harmonised with Landsat",
        "HLSS30_2.0",
    ),
    Product(
        "HLSL30",
        "2.0",
        "LP DAAC (LPCLOUD)",
        "30 m",
        "field-scale vegetation time series (Landsat 8/9 part)",
        "HLSL30_2.0",
    ),
    Product(
        "SPL3SMP_E",
        "006",
        "NSIDC DAAC (NSIDC_CPRD)",
        "9 km EASE-Grid 2.0, daily (AM/PM passes)",
        "surface soil moisture (top ~5 cm), coarse context only",
    ),
    Product(
        "SPL4SMGP",
        "008",
        "NSIDC DAAC (NSIDC_CPRD)",
        "9 km EASE-Grid 2.0, 3-hourly (model + assimilation)",
        "surface and root-zone soil moisture (modelled), coarse context only",
    ),
    Product("GPM_3IMERGDF", "07", "GES DISC", "0.1° x 0.1°, daily", "daily precipitation (satellite + gauge)"),
    Product("GPM_3IMERGM", "07", "GES DISC", "0.1° x 0.1°, monthly", "monthly precipitation (satellite + gauge)"),
    Product(
        "ECO_L2T_LSTE",
        "002",
        "LP DAAC (LPCLOUD)",
        "70 m, irregular ISS overpass times",
        "land surface temperature (crop heat stress context)",
    ),
    Product(
        "ECO_L3T_JET",
        "002",
        "LP DAAC (LPCLOUD)",
        "70 m, irregular ISS overpass times",
        "evapotranspiration (crop water use context)",
    ),
]


# ----------------------------------------------------------------------------------------------- credentials / auth
def credentials(netrc_path: str | None = None) -> tuple[str, str] | None:
    """(username, password) from EARTHDATA_USERNAME/EARTHDATA_PASSWORD, else a netrc entry for URS, else None."""
    user, pwd = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if user and pwd:
        return user, pwd
    candidates = (
        [netrc_path]
        if netrc_path
        else [os.environ.get("NETRC"), str(Path.home() / ".netrc"), str(Path.home() / "_netrc")]
    )
    for c in candidates:
        if c and Path(c).is_file():
            try:
                auth = netrc.netrc(c).authenticators(URS_HOST)
            except (netrc.NetrcParseError, OSError):
                continue
            if auth and auth[0] and auth[2]:
                return auth[0], auth[2]
    return None


def basic_auth_header(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode("ascii")


def needs_urs_auth(url: str) -> bool:
    """Basic credentials go only to the Earthdata Login host, never to a data host."""
    return urlparse(url).hostname == URS_HOST


def download_granule(
    url: str, dest: Path, auth: tuple[str, str], client=None, max_hops: int = 10, chunk: int = 1 << 20
) -> Path:
    """Download one Earthdata Cloud file following the URS OAuth redirect chain by hand.

    httpx would drop (correctly) the Authorization header on cross-host redirects, so redirects are followed here:
    the Basic header is attached only when the hop is urs.earthdata.nasa.gov; cookies set by the data host
    (e.g. `accessToken`, `nasa_*`) stay in the client's jar for the next hops. Resumable: an existing file of the
    advertised size is kept.
    """
    import httpx

    own = client is None
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=httpx.Timeout(60.0, read=600.0))
    try:
        cur = url
        for _ in range(max_hops):
            headers = {}
            if needs_urs_auth(cur):
                headers["Authorization"] = basic_auth_header(*auth)
            with client.stream("GET", cur, headers=headers, follow_redirects=False) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    cur = str(httpx.URL(cur).join(r.headers["location"]))
                    continue
                if r.status_code == 401:
                    raise PermissionError(f"Earthdata Login refused the credentials (HTTP 401) at {cur}")
                if r.status_code == 403:
                    raise PermissionError(
                        f"HTTP 403 at {cur}: authorise the DAAC application in your Earthdata "
                        "profile (Applications > Authorized Apps) and accept its EULA"
                    )
                r.raise_for_status()
                size = int(r.headers.get("content-length", "0") or 0)
                if dest.exists() and size and dest.stat().st_size == size:
                    return dest
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as fh:
                    for block in r.iter_bytes(chunk):
                        fh.write(block)
                if size and tmp.stat().st_size != size:
                    raise OSError(f"incomplete download {tmp.stat().st_size}/{size} B for {url}")
                tmp.replace(dest)
                return dest
        raise RuntimeError(f"too many redirects for {url}")
    finally:
        if own:
            client.close()


# ----------------------------------------------------------------------------------------------- CMR discovery
def cmr_params(product: Product, bbox, temporal=TEMPORAL, page_size: int = 10) -> dict:
    w, s, e, n = bbox
    return {
        "short_name": product.short_name,
        "version": product.version,
        "bounding_box": f"{w},{s},{e},{n}",
        "temporal": f"{temporal[0]},{temporal[1]}",
        "page_size": page_size,
        "sort_key": "start_date",
    }


def data_links(entry: dict) -> list[str]:
    """HTTPS data links of a CMR JSON granule entry (rel .../data#), excluding s3:// and metadata links."""
    out = []
    for ln in entry.get("links", []):
        href = ln.get("href", "")
        if ln.get("rel", "").endswith("/data#") and href.startswith("https://") and not ln.get("inherited"):
            out.append(href)
    return out


def _get(url, params=None, follow=True, timeout=90.0, tries=4):
    import httpx

    delay, last = 3.0, None
    for _attempt in range(tries):
        try:
            return httpx.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=follow
            )
        except httpx.HTTPError as exc:
            last = exc
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{url}: {last}")


def discover(product: Product, bbox) -> dict:
    rec = {
        "short_name": product.short_name,
        "version": product.version,
        "daac": product.daac,
        "native_resolution": product.resolution,
        "use_in_miaudow": product.use,
    }
    c = _get(f"{CMR}/collections.json", {"short_name": product.short_name, "version": product.version})
    entries = c.json()["feed"]["entry"]
    if not entries:
        rec["access_status"] = "NOT_FOUND_IN_CMR"
        return rec
    col = entries[0]
    rec.update(
        {
            "collection_concept_id": col["id"],
            "title": col.get("title"),
            "temporal_coverage": f"{col.get('time_start')} .. {col.get('time_end') or 'ongoing'}",
            "cloud_hosted": col.get("cloud_hosted"),
            "cmr_collection_url": f"{CMR}/concepts/{col['id']}.html",
        }
    )
    g = _get(f"{CMR}/granules.json", cmr_params(product, bbox))
    rec["granule_search"] = {"url": str(g.url), "status": g.status_code, "bbox": bbox, "temporal": list(TEMPORAL)}
    rec["granules_found_2020_2021"] = int(g.headers.get("CMR-Hits", "-1"))
    gent = g.json()["feed"]["entry"]
    rec["sample_granules"] = [x.get("producer_granule_id") or x.get("title") for x in gent[:3]]
    if product.stac_collection:
        try:
            w, s, e, n = bbox
            st = _get(
                f"{CMR_STAC_LPCLOUD}/search",
                {
                    "collections": product.stac_collection,
                    "bbox": f"{w},{s},{e},{n}",
                    "datetime": f"{TEMPORAL[0]}/{TEMPORAL[1]}",
                    "limit": 1,
                },
            )
            sj = st.json()
            rec["cmr_stac"] = {
                "url": str(st.url),
                "status": st.status_code,
                "numberMatched": sj.get("numberMatched", (sj.get("context") or {}).get("matched")),
            }
        except Exception as exc:  # noqa: BLE001 - optional
            rec["cmr_stac"] = {"error": str(exc)[:200]}
    links = data_links(gent[0]) if gent else []
    if not links:
        rec["access_status"] = "NO_GRANULE_OVER_AREA" if rec["granules_found_2020_2021"] == 0 else "NO_HTTPS_LINK"
        return rec
    asset = links[0]
    r = _get(asset, follow=False, timeout=60)
    loc = r.headers.get("location", "")
    probe = {"url": asset, "status": r.status_code, "redirect_host": urlparse(loc).hostname if loc else None}
    if loc and urlparse(loc).hostname == URS_HOST:
        r2 = _get(loc, follow=False, timeout=60)
        probe["urs_status_without_credentials"] = r2.status_code
    rec["unauthenticated_probe"] = probe
    if r.status_code in (301, 302, 303, 307) and probe["redirect_host"] == URS_HOST or r.status_code == 401:
        rec["access_status"] = "BLOCKED_EARTHDATA_LOGIN"
    elif r.status_code == 200:
        rec["access_status"] = "OPEN_WITHOUT_LOGIN"
    else:
        rec["access_status"] = f"BLOCKED_HTTP_{r.status_code}"
    rec["prerequisite"] = (
        "Free Earthdata Login account (https://urs.earthdata.nasa.gov/users/new); set "
        "EARTHDATA_USERNAME and EARTHDATA_PASSWORD, or a .netrc/_netrc entry 'machine "
        "urs.earthdata.nasa.gov login <user> password <pass>'"
        + ("; authorise 'NASA GESDISC DATA ARCHIVE' in the Earthdata profile" if product.daac == "GES DISC" else "")
    )
    rec["adapter"] = (
        "pipeline/fetch_nasa_missions.py: fetch(product_short_name, bbox, start, end, limit) -> "
        "list[Path]; download_granule(url, dest, auth) -> Path"
    )
    return rec


def fetch(short_name: str, bbox, start: str, end: str, limit: int = 2) -> list[Path]:
    """Download up to `limit` granules of one product over bbox/time into data/cache/nasa_missions/<short_name>/."""
    import httpx

    auth = credentials()
    if auth is None:
        raise PermissionError("credentials missing")
    product = next(p for p in PRODUCTS if p.short_name == short_name)
    g = _get(f"{CMR}/granules.json", cmr_params(product, bbox, (start, end), page_size=max(limit, 1)))
    paths = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=httpx.Timeout(60.0, read=600.0)) as client:
        for entry in g.json()["feed"]["entry"][:limit]:
            for href in data_links(entry)[:1]:
                dest = CACHE / short_name / Path(urlparse(href).path).name
                paths.append(download_granule(href, dest, auth, client=client))
                print(f"  {short_name}: {dest.relative_to(ROOT)}")
    return paths


def area_bbox() -> list[float]:
    if GEO_FILE.exists():
        return json.loads(GEO_FILE.read_text(encoding="utf-8"))["do_luong"]["bbox"]
    return FALLBACK_BBOX


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true", help="public CMR discovery; writes STATUS.json")
    ap.add_argument("--download", metavar="SHORT_NAME", help="download granules (needs Earthdata credentials)")
    ap.add_argument("--start", default="2020-06-01T00:00:00Z")
    ap.add_argument("--end", default="2021-06-30T23:59:59Z")
    ap.add_argument("--limit", type=int, default=2)
    args = ap.parse_args()
    bbox = area_bbox()
    if args.download:
        if credentials() is None:
            print(
                "credentials missing: set EARTHDATA_USERNAME and EARTHDATA_PASSWORD, or add "
                "'machine urs.earthdata.nasa.gov login <user> password <pass>' to ~/.netrc (or %USERPROFILE%\\_netrc)."
                " Nothing was downloaded."
            )
            return 0
        fetch(args.download, bbox, args.start, args.end, args.limit)
        return 0
    if not args.discover:
        ap.print_help()
        return 0
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    recs = []
    for p in PRODUCTS:
        try:
            rec = discover(p, bbox)
        except Exception as exc:  # noqa: BLE001 - recorded, others continue
            rec = {
                "short_name": p.short_name,
                "version": p.version,
                "access_status": "DISCOVERY_FAILED",
                "error": str(exc)[:300],
            }
        print(
            f"  {p.short_name} v{p.version}: {rec.get('granules_found_2020_2021')} granules, "
            f"{rec.get('access_status')} {rec.get('unauthenticated_probe', {}).get('status')}"
        )
        recs.append(rec)
        time.sleep(0.5)
    doc = {
        "generated_at": now,
        "bbox": bbox,
        "bbox_source": "data/canonical/geo_do_luong.json (Đô Lương ADM2)",
        "temporal": list(TEMPORAL),
        "discovery": f"{CMR} (public, no login)",
        "credentials_present": credentials() is not None,
        "license": "NASA Earth science data: no restrictions on reuse, sale or redistribution (NASA Earth "
        "Science Data and Information Policy); cite each product DOI",
        "products": recs,
        "note": {
            "vi": "Chỉ tìm kiếm danh mục, chưa tải dữ liệu: cần tài khoản Earthdata miễn phí.",
            "en": "Catalogue discovery only, no data downloaded: a free Earthdata account is required.",
        },
        "script": "pipeline/fetch_nasa_missions.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
