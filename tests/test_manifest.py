"""data/MANIFEST.csv rows are recorded once per file version (CR-07; audit pass 3, 2026-11-13).

A fresh clone re-downloads files that are already recorded; an identical file (same path and sha256) must not get a
second row with a later date, or the retrieval date of the data becomes ambiguous (nso.retrieval_dates refuses it).
"""

import csv
from hashlib import sha256
from pathlib import Path

import pytest

from fieldshift.data.manifest import append_rows, fetch_recorded

HEADER = ["path", "source_id", "table", "title", "url", "retrieved_on", "method", "sha256"]


def _write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        w.writerows(rows)


def _read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def test_identical_file_is_not_recorded_twice(tmp_path):
    m = tmp_path / "MANIFEST.csv"
    _write(m, [["data/raw/a.csv", "s", "A", "t", "u", "2026-11-10", "m", "abc"]])
    added = append_rows(m, [["data/raw/a.csv", "s", "A", "t", "u", "2026-11-14", "m", "abc"]])
    assert added == 0
    assert [r["retrieved_on"] for r in _read(m)] == ["2026-11-10"]


def test_changed_or_new_files_are_recorded(tmp_path):
    m = tmp_path / "MANIFEST.csv"
    _write(m, [["data/raw/a.csv", "s", "A", "t", "u", "2026-11-10", "m", "abc"]])
    added = append_rows(
        m,
        [
            ["data/raw/a.csv", "s", "A", "t", "u", "2026-11-14", "m", "def"],
            ["data/raw/b.csv", "s", "B", "t", "u", "2026-11-14", "m", "ghi"],
        ],
    )
    assert added == 2
    assert [(r["path"], r["sha256"]) for r in _read(m)] == [
        ("data/raw/a.csv", "abc"),
        ("data/raw/a.csv", "def"),
        ("data/raw/b.csv", "ghi"),
    ]


def test_windows_paths_are_recorded_with_forward_slashes(tmp_path):
    # CR-07 provenance: all 315 committed rows (2026-11-13) use repository-relative paths with "/", and
    # nso.retrieval_dates looks files up by that text; a download on Windows gave "data\raw\..." (team laptop, 2026-11-14)
    m = tmp_path / "MANIFEST.csv"
    _write(m, [])
    added = append_rows(m, [[r"data\raw\power\p.json", "s", "", "t", "u", "2026-11-14", "m", "abc"]])
    assert added == 1
    assert [r["path"] for r in _read(m)] == ["data/raw/power/p.json"]


def test_a_windows_path_of_a_recorded_file_is_not_recorded_twice(tmp_path):
    m = tmp_path / "MANIFEST.csv"
    _write(m, [["data/raw/a.csv", "s", "A", "t", "u", "2026-11-10", "m", "abc"]])
    added = append_rows(m, [[r"data\raw\a.csv", "s", "A", "t", "u", "2026-11-14", "m", "abc"]])
    assert added == 0
    assert [r["retrieved_on"] for r in _read(m)] == ["2026-11-10"]


def test_committed_manifest_has_one_row_per_file_version():
    # Source: the rule above (one row per path and sha256), applied to the committed data/MANIFEST.csv itself
    with open("data/MANIFEST.csv", encoding="utf-8", newline="") as f:
        pairs = [(r["path"], r["sha256"]) for r in csv.DictReader(f)]
    repeated = sorted({p for p in pairs if pairs.count(p) > 1})
    assert repeated == []


class _Reply:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> "_Reply":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class _Opener:
    def __init__(self, body: bytes) -> None:
        self.body, self.urls = body, []

    def open(self, url: str, timeout: float) -> _Reply:
        self.urls.append(url)
        return _Reply(self.body)


def _recorded(tmp_path, url="https://example.org/b.geojson", body=b"boundary"):
    manifest = tmp_path / "MANIFEST.csv"
    _write(
        manifest,
        [["data/raw/b.geojson", "geoboundaries", "t", "t", url, "2026-11-11", "curl", sha256(body).hexdigest()]],
    )
    return manifest


def test_fetch_recorded_downloads_the_manifest_url_and_checks_its_sha256(tmp_path, monkeypatch):
    # Source: CR-07, NFR-02: a fresh clone re-downloads the recorded file and verifies it against its recorded sha256
    monkeypatch.chdir(tmp_path)
    manifest, opener = _recorded(tmp_path), _Opener(b"boundary")
    assert fetch_recorded("data/raw/b.geojson", manifest, opener) == Path("data/raw/b.geojson")
    assert Path("data/raw/b.geojson").read_bytes() == b"boundary"
    assert opener.urls == ["https://example.org/b.geojson"]


def test_fetch_recorded_refuses_a_changed_file_an_unknown_path_and_http(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="sha256"):
        fetch_recorded("data/raw/b.geojson", _recorded(tmp_path), _Opener(b"changed upstream"))
    assert not Path("data/raw/b.geojson").exists()
    with pytest.raises(ValueError, match="no manifest row"):
        fetch_recorded("data/raw/other.geojson", _recorded(tmp_path), _Opener(b"boundary"))
    two = tmp_path / "TWO.csv"
    _write(
        two,
        [
            ["data/raw/b.geojson", "g", "t", "t", "https://example.org/b.geojson", "2026-11-11", "curl", "a" * 64],
            ["data/raw/b.geojson", "g", "t", "t", "https://example.org/b.geojson", "2026-11-12", "curl", "b" * 64],
        ],
    )
    with pytest.raises(ValueError, match="several versions"):
        fetch_recorded("data/raw/b.geojson", two, _Opener(b"boundary"))
    with pytest.raises(ValueError, match="https"):
        fetch_recorded(
            "data/raw/b.geojson", _recorded(tmp_path, url="http://example.org/b.geojson"), _Opener(b"boundary")
        )
