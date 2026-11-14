"""Download (or reuse the cache of) GPM IMERG Final monthly V07 for a box around the Nghệ An POWER cells, 2001-2024.

Usage: PYTHONPATH=src python scripts/download_imerg_monthly.py
Set FIELDSHIFT_SKIP_IMERG=1 to skip this stage while the rain check is not built (team, 2026-11-14).
Raw OPeNDAP ASCII replies go unchanged to data/raw/imerg_monthly/ (gitignored); each new file gets a row in
data/MANIFEST.csv. Needs the Earthdata token (network secret for urs.earthdata.nasa.gov). Failures are reported,
never filled (D-135; 05-DATA-CONTRACTS §5c).
"""

import csv
import hashlib
import http.cookiejar
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from fieldshift.data import imerg
from fieldshift.data.manifest import append_rows

OUT = Path("data/raw/imerg_monthly")
MANIFEST = Path("data/MANIFEST.csv")
YEARS = range(2001, 2025)

if os.environ.get("FIELDSHIFT_SKIP_IMERG") == "1":
    print("IMERG stage skipped: FIELDSHIFT_SKIP_IMERG is set")
    sys.exit(0)

with open("data/processed/cell_weights.csv", newline="") as f:
    cells = [(float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f) if r["province_nso"] == "Nghe An"]
box = imerg.box_for_cells(cells)
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def get(url: str, retries: int = 4) -> str:
    delay = 5.0
    for attempt in range(retries + 1):
        try:
            with opener.open(url, timeout=120) as resp:
                return resp.read().decode()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries:
                raise
        time.sleep(delay)
        delay *= 2
    raise RuntimeError("unreachable")


OUT.mkdir(parents=True, exist_ok=True)
failed = []
for year in YEARS:
    try:
        listing = get(f"{imerg.BASE_URL}/{year}/contents.html")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as err:  # reported below; the batch continues
        failed.append((year, None, repr(err)))
        continue
    for month in range(1, 13):
        try:
            name = imerg.month_file(listing, year, month)
            path = OUT / f"{name}.ascii"
            if path.exists():
                continue
            url = imerg.subset_url(year, name, box)
            text = get(url)
            imerg.check_response(text, box)
            raw = text.encode()
            path.write_bytes(raw)  # as received: write_text would turn the line ends into CRLF on Windows
            row = [
                path.as_posix(),
                "gpm_imerg_monthly",
                "",
                f"GPM_3IMERGM V07 {year}-{month:02d}, box {box}",
                url,
                datetime.now(UTC).date().isoformat(),
                "scripts/download_imerg_monthly.py (OPeNDAP ASCII)",
                hashlib.sha256(raw).hexdigest(),
            ]
            append_rows(MANIFEST, [row])
            time.sleep(1.0)
        except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError) as err:  # reported; batch continues
            failed.append((year, month, repr(err)))
done = len(list(OUT.glob("*.ascii")))
print(f"box {box} | files {done} of {len(YEARS) * 12} | failed {len(failed)}")
for row in failed:
    print("failed:", row)
sys.exit(1 if failed else 0)
