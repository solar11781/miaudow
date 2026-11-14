"""Tests for the batch NASA POWER downloader (written before the code, D-29).

Spec (D-26/D-36 output: 136 POWER cells; ML-SPEC section 4: 1991-2020 climatology and 1995-2024 training, so
1991-01-01..2024-12-31; DATA-CONTRACTS provenance): one request per cell at the cell centre, results cached on disk,
a failure is recorded and reported (never silently skipped or filled), and requests to NASA are paced.
Provenance (04-TECH-DESIGN §2, 02-SRS CR-07): every downloaded file gets a data/MANIFEST.csv row
(path, source_id, table, title, url, retrieved_on, method, sha256 of the file bytes), as the IMERG script does.
"""

import hashlib
from datetime import date

from fieldshift.data.power import PowerRequest
from fieldshift.data.power_batch import PAUSE_S, download_cells, manifest_row

PAYLOAD = {
    "properties": {"parameter": {"PRECTOTCORR": {"19910101": 1.0, "19910102": 2.0}}},
    "parameters": {"PRECTOTCORR": {"units": "mm/day"}},
    "messages": [],
}
CELLS = [(19.0, 105.625), (18.5, 105.0)]


def test_one_request_per_cell_at_cell_centre(tmp_path):
    urls = []
    res = download_cells(
        CELLS,
        (date(1991, 1, 1), date(1991, 1, 2)),
        tmp_path,
        fetch_json=lambda u: urls.append(u) or PAYLOAD,
        sleep=lambda s: None,
    )
    assert len(urls) == 2
    assert "latitude=19.0000" in urls[0]
    assert "longitude=105.6250" in urls[0]
    assert [r["status"] for r in res] == ["ok", "ok"]
    assert all(r["days"] == 2 for r in res)


def test_cached_cells_are_not_requested_again_and_not_paced(tmp_path):
    download_cells(
        CELLS, (date(1991, 1, 1), date(1991, 1, 2)), tmp_path, fetch_json=lambda u: PAYLOAD, sleep=lambda s: None
    )
    calls, pauses = [], []
    res = download_cells(
        CELLS,
        (date(1991, 1, 1), date(1991, 1, 2)),
        tmp_path,
        fetch_json=lambda u: calls.append(u) or PAYLOAD,
        sleep=pauses.append,
    )
    assert calls == []
    assert pauses == []
    assert [r["status"] for r in res] == ["ok", "ok"]


def test_failure_is_recorded_and_other_cells_continue(tmp_path):
    def fetch(url):
        if "latitude=19.0000" in url:
            raise RuntimeError("server error")
        return PAYLOAD

    res = download_cells(CELLS, (date(1991, 1, 1), date(1991, 1, 2)), tmp_path, fetch_json=fetch, sleep=lambda s: None)
    assert res[0]["status"] == "failed"
    assert "server error" in res[0]["error"]
    assert res[1]["status"] == "ok"


def test_requests_are_paced(tmp_path):
    pauses = []
    download_cells(
        CELLS,
        (date(1991, 1, 1), date(1991, 1, 2)),
        tmp_path,
        fetch_json=lambda u: PAYLOAD,
        sleep=pauses.append,
    )
    assert pauses == [PAUSE_S, PAUSE_S]


def test_report_names_the_cached_file_and_the_request_url(tmp_path):
    res = download_cells(
        CELLS[:1], (date(1991, 1, 1), date(1991, 1, 2)), tmp_path, fetch_json=lambda u: PAYLOAD, sleep=lambda s: None
    )
    req = PowerRequest(lat=19.0, lon=105.625, start=date(1991, 1, 1), end=date(1991, 1, 2))
    assert res[0]["url"] == req.url()
    assert res[0]["path"] == str(tmp_path / req.cache_key())


def test_manifest_row_has_url_date_and_the_checksum_of_the_file(tmp_path):
    res = download_cells(
        CELLS[:1], (date(1991, 1, 1), date(1991, 1, 2)), tmp_path, fetch_json=lambda u: PAYLOAD, sleep=lambda s: None
    )
    row = manifest_row(
        res[0], source_id="nasa_power_cache", retrieved_on="2026-11-13", method="scripts/download_power.py"
    )
    with open(res[0]["path"], "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    assert row == [
        res[0]["path"],
        "nasa_power_cache",
        "",
        "NASA POWER daily point 19.0000 N 105.6250 E",
        res[0]["url"],
        "2026-11-13",
        "scripts/download_power.py",
        digest,
    ]
