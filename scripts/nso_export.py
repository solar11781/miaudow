"""Export one NSO PX-Web table (all values of every variable) as CSV through the public web form.

Usage: python -I scripts/nso_export.py E06.26 data/raw/nso/E06.26.csv
The web form is the download mechanism NSO provides; the PX-Web JSON API does not expose the agriculture DB.
Each export gets a data/MANIFEST.csv row (url, date, sha256); scripts/build_crop_stats.py reads its date from there.
"""

import hashlib
import html
import http.cookiejar
import re
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from fieldshift.data.manifest import append_rows

BASE = (
    "https://pxweb.nso.gov.vn/pxweb/en/E%2006.%20Agriculture%2C%20Forestry%20and%20Fishing/"
    "E%2006.%20Agriculture%2C%20Forestry%20and%20Fishing__Px_E_06/{table}.px/"
)
UA = "fieldshift-research/0.1 (NASA Space Apps 2026 student project)"


def export(table: str, fmt: str = "FileTypeCsvWithHeadingAndComma") -> bytes:
    url = BASE.format(table=table)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    opener.addheaders = [("User-Agent", UA)]
    page = opener.open(url, timeout=90).read().decode("utf-8", "replace")
    data = []
    for tag in re.findall(r"<input[^>]*>", page):
        name = re.search(r'name="([^"]+)"', tag)
        if not name:
            continue
        name = name.group(1)
        value = re.search(r'value="([^"]*)"', tag)
        value = html.unescape(value.group(1)) if value else ""
        if 'type="hidden"' in tag:
            data.append((name, value))
    selected_counts = {}
    for name, body in re.findall(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', page, flags=re.S):
        values = [html.unescape(v) for v in re.findall(r'<option[^>]*value="([^"]*)"', body)]
        if name.endswith("ValuesListBox"):
            data += [(name, v) for v in values]
            selected_counts[name.replace("ValuesListBox", "NumberValuesSelected")] = str(len(values))
        elif name.endswith("OutputFormatDropDownList"):
            if fmt not in values:
                raise ValueError(f"format {fmt} not offered: {values}")
            data.append((name, fmt))
        elif name.endswith("cboSelectLanguages"):
            data.append((name, "en"))
    data += list(selected_counts.items())
    data.append(("ctl00$ContentPlaceHolderMain$VariableSelector1$VariableSelector1$ButtonViewTable", "Continue"))
    resp = opener.open(url, urllib.parse.urlencode(data).encode(), timeout=180)
    body = resp.read()
    ctype = resp.headers.get("Content-Type", "")
    if "html" in ctype:
        raise RuntimeError(f"expected a file, got HTML from {resp.geturl()} ({len(body)} bytes)")
    return body


if __name__ == "__main__":
    table, out = sys.argv[1], sys.argv[2]
    content = export(table)
    with open(out, "wb") as fh:
        fh.write(content)
    title = content.decode("utf-8", "replace").splitlines()[0].strip().strip('"')  # first CSV line = table title
    append_rows(
        "data/MANIFEST.csv",
        [
            [
                out,
                "nso_e06",
                table,
                title,
                BASE.format(table=table),
                datetime.now(UTC).date().isoformat(),
                "scripts/nso_export.py (all values, csv with heading and comma)",
                hashlib.sha256(content).hexdigest(),
            ]
        ],
    )
    print(f"{table}: {len(content)} bytes -> {out}")
