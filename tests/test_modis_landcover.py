import hashlib
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("modis_landcover", Path("scripts/modis_landcover.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_subset_indices_match_grid_convention():
    # Global grid is 3600 x 7200 at 0.05 deg; row 0 = 90 N, column 0 = 180 W.
    r0, r1, c0, c1 = mod.subset_indices(8.0, 24.0, 102.0, 110.0, 0.05)
    assert (r0, r1) == (1320, 1640)
    assert (c0, c1) == (5640, 5800)
    assert (r1 - r0, c1 - c0) == (320, 160)


def test_pixel_centre_of_first_subset_cell():
    r0, _, c0, _ = mod.subset_indices()
    lat_centre = 90 - (r0 + 0.5) * mod.CELL
    lon_centre = -180 + (c0 + 0.5) * mod.CELL
    assert abs(lat_centre - 23.975) < 1e-9
    assert abs(lon_centre - 102.025) < 1e-9


def test_pixel_index_is_consistent_between_global_grid_and_subset():
    r0, _, c0, _ = mod.subset_indices()
    for lat, lon in [(18.9, 105.6), (10.3, 105.6), (19.25, 104.95), (23.97, 102.02)]:
        gr, gc = mod.pixel_index(lat, lon)
        sr, sc = mod.pixel_index(lat, lon, lat_max=mod.LAT_MAX, lon_min=mod.LON_MIN)
        assert (gr - r0, gc - c0) == (sr, sc)


def test_border_point_goes_south():
    # 18.9 N is exactly the border between rows 1421 (18.90-18.95) and 1422 (18.85-18.90).
    assert mod.pixel_index(18.9, 105.6)[0] == 1422


class _Reply:
    """A download reply: Content-Length says 10 bytes; `body` is what the server really sends before closing."""

    def __init__(self, body: bytes, length: int = 10) -> None:
        self.headers = {"Content-Type": "application/octet-stream", "Content-Length": str(length)}
        self._body = body

    def read(self, _n: int) -> bytes:
        out, self._body = self._body, b""
        return out

    def geturl(self) -> str:
        return "https://data.lpdaac.earthdatacloud.nasa.gov/x.hdf"

    def __enter__(self) -> "_Reply":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class _Opener:
    def __init__(self, reply: _Reply) -> None:
        self.reply, self.addheaders = reply, []

    def open(self, _url: str, timeout: float) -> _Reply:
        return self.reply


def test_a_cut_off_download_fails_and_leaves_no_file(tmp_path, monkeypatch):
    # Source: a reply that ends before its Content-Length is incomplete (RFC 9110 section 8.6); data are never guessed
    monkeypatch.setattr(mod, "earthdata_opener", lambda: _Opener(_Reply(b"12345")))
    dest = tmp_path / "x.hdf"
    with pytest.raises(RuntimeError, match="5 of 10 bytes"):
        mod.download("https://data.lpdaac.earthdatacloud.nasa.gov/x.hdf", dest)
    assert list(tmp_path.iterdir()) == []


def test_a_full_download_returns_its_sha256(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "earthdata_opener", lambda: _Opener(_Reply(b"0123456789")))
    dest = tmp_path / "x.hdf"
    assert (
        mod.download("https://data.lpdaac.earthdatacloud.nasa.gov/x.hdf", dest)
        == hashlib.sha256(b"0123456789").hexdigest()
    )
    assert dest.read_bytes() == b"0123456789"


def test_a_reused_raw_file_must_match_its_manifest_row(tmp_path):
    # Source: data/MANIFEST.csv records the sha256 of every original download (CR-07); a reused file must match it
    raw = tmp_path / "x.hdf"
    raw.write_bytes(b"changed")
    manifest = tmp_path / "MANIFEST.csv"
    manifest.write_text(
        "path,source_id,table,title,url,retrieved_on,method,sha256\n"
        f"{raw.as_posix()},modis_mcd12c1,g,t,u,2026-11-14,m,{hashlib.sha256(b'original').hexdigest()}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="sha256"):
        mod.reused_sha256(raw, manifest)
    raw.write_bytes(b"original")
    assert mod.reused_sha256(raw, manifest) == hashlib.sha256(b"original").hexdigest()
