"""data/MANIFEST.csv rows are recorded once per file version (CR-07; audit pass 3, 2026-11-13).

A fresh clone re-downloads files that are already recorded; an identical file (same path and sha256) must not get a
second row with a later date, or the retrieval date of the data becomes ambiguous (nso.retrieval_dates refuses it).
"""

import csv

from fieldshift.data.manifest import append_rows

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
