"""Append rows to data/MANIFEST.csv once per file version (CR-07).

A row whose path and sha256 are already recorded is skipped, so a re-download of an identical file keeps its first
retrieval date (nso.retrieval_dates needs exactly one date per file version). Paths are stored with "/" on every
system, so a download on Windows records the same text as one on Linux.
"""

from __future__ import annotations

import csv
import hashlib
import urllib.parse
import urllib.request
from pathlib import Path

PATH_COL, SHA_COL = 0, 7  # column order: path, source_id, table, title, url, retrieved_on, method, sha256
MANIFEST = Path("data/MANIFEST.csv")
FETCH_TIMEOUT_S = 120


def append_rows(manifest: Path | str, rows: list[list[str]]) -> int:
    """Append the rows not yet recorded; return how many were added."""
    manifest = Path(manifest)
    with open(manifest, newline="", encoding="utf-8") as f:
        seen = {(r["path"], r["sha256"]) for r in csv.DictReader(f)}
    new = []
    for given in rows:
        row = [given[PATH_COL].replace("\\", "/"), *given[PATH_COL + 1 :]]
        key = (row[PATH_COL], row[SHA_COL])
        if key not in seen:
            seen.add(key)
            new.append(row)
    with open(manifest, "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(new)
    return len(new)


def _recorded(path: str, manifest: Path | str) -> tuple[str, str]:
    """(url, sha256) of the one recorded version of `path`."""
    with open(manifest, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["path"] == path]
    if len({(r["url"], r["sha256"]) for r in rows}) != 1:
        raise ValueError(f"{path}: no manifest row, or several versions, in {manifest}")
    return rows[0]["url"], rows[0]["sha256"]


def check_recorded(path: str, manifest: Path | str = MANIFEST) -> Path:
    """The file at `path`, used only if its sha256 is the recorded one (a changed or replaced download is refused)."""
    _url, sha = _recorded(path, manifest)
    got = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if got != sha:
        raise ValueError(f"{path}: sha256 {got[:12]} does not match the manifest ({sha[:12]})")
    return Path(path)


def fetch_recorded(
    path: str, manifest: Path | str = MANIFEST, opener: urllib.request.OpenerDirector | None = None
) -> Path:
    """Download a file recorded in the manifest from its recorded https URL; keep it only if its sha256 matches."""
    url, sha = _recorded(path, manifest)
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError(f"{path}: recorded URL is not https: {url}")
    with (opener or urllib.request.build_opener()).open(url, timeout=FETCH_TIMEOUT_S) as resp:
        body = resp.read()
    got = hashlib.sha256(body).hexdigest()
    if got != sha:
        raise ValueError(f"{path}: sha256 {got[:12]} does not match the manifest ({sha[:12]}); file not kept")
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return dest
