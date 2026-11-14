"""Append rows to data/MANIFEST.csv once per file version (CR-07).

A row whose path and sha256 are already recorded is skipped, so a re-download of an identical file keeps its first
retrieval date (nso.retrieval_dates needs exactly one date per file version). Paths are stored with "/" on every
system, so a download on Windows records the same text as one on Linux.
"""

from __future__ import annotations

import csv
from pathlib import Path

PATH_COL, SHA_COL = 0, 7  # column order: path, source_id, table, title, url, retrieved_on, method, sha256


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
