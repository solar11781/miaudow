"""Static snapshot of real API answers for the demo-day fallback (04-TECH-DESIGN section 9 runbook, D-150; no recorded
demo video, D-151).

Usage: PYTHONPATH=src python scripts/build_snapshot.py
Loads the API in-process (FastAPI TestClient on create_app, as tests/test_api.py does; no network) and writes
frontend/snapshot/ (copied into the build only by `npm run build:snapshot`): past-years.json, method.json, figures/nghe_an_grid.svg and nghe_an_grid.vi.svg, one compare/<land>-<priority>-<years>.json
per demo answer set, and index.json (the saved answer sets, the commit and the time made). tests/test_build_snapshot.py fails when a file differs from what the API answers now.

Demo answer set, chosen from the past-years response with no threshold of our own:
- land: both API land types, dry and unsure; priority: each of the four;
- years A: the 3 years with the largest share of the stricter drought rule (drought_rain_consecutive), the latest
  first on ties, plus the year with the largest cold share; years B: the latest past year alone.
That is 2 x 4 x 2 = 16 compare files.
"""

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from fieldshift.api.app import create_app

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "frontend" / "snapshot"
LANDS = ("dry", "unsure")  # UI-UX-SPEC section 11 CompareRequest.land
PRIORITIES = ("income", "stability", "water", "land")  # UI-UX-SPEC section 11 CompareRequest.priority


def _share(row: dict, code: str) -> int:
    value = row["shares"][code]
    return -1 if value is None else int(value["value"])


def demo_years(past: dict) -> list[list[int]]:
    """The two year picks of the module docstring, each ascending as the app sends them."""
    rows = past["years"]
    drought = sorted(rows, key=lambda r: (_share(r, "drought_rain_consecutive"), r["year"]), reverse=True)[:3]
    cold = max(rows, key=lambda r: (_share(r, "cold"), r["year"]))
    picks = sorted({r["year"] for r in [*drought, cold]})
    return [picks, [max(r["year"] for r in rows)]]


def demo_set(past: dict) -> list[dict]:
    """Every saved answer combination with its file name inside the snapshot folder."""
    return [
        {
            "land": land,
            "priority": priority,
            "years": years,
            "file": f"compare/{land}-{priority}-{'_'.join(map(str, years))}.json",
        }
        for years in demo_years(past)
        for land in LANDS
        for priority in PRIORITIES
    ]


def _write_json(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")


def build(out: Path = OUT) -> list[dict]:
    client = TestClient(create_app(root=REPO))
    past = client.get("/api/past-years", params={"province": "nghe_an"}).raise_for_status().json()
    if out.exists():
        shutil.rmtree(out)
    _write_json(out / "past-years.json", past)
    _write_json(out / "method.json", client.get("/api/method").raise_for_status().json())
    (out / "figures").mkdir(parents=True)
    for figure in ("nghe_an_grid.svg", "nghe_an_grid.vi.svg"):
        (out / "figures" / figure).write_bytes(client.get(f"/api/figures/{figure}").raise_for_status().content)
    saved = demo_set(past)
    for entry in saved:
        body = {"province": "nghe_an", "land": entry["land"], "years": entry["years"], "priority": entry["priority"]}
        _write_json(out / entry["file"], client.post("/api/compare", json=body).raise_for_status().json())
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git not found: the snapshot index records the commit it was made from")
    commit = subprocess.run([git, "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True)  # noqa: S603  fixed arguments
    made_at = datetime.now(UTC).isoformat(timespec="seconds")
    _write_json(out / "index.json", {"commit": commit.stdout.strip(), "made_at": made_at, "compare": saved})
    return saved


if __name__ == "__main__":
    for entry in build():
        print(entry["file"])
