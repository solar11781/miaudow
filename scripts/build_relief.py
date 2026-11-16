"""Build the NASA SRTM shaded relief picture for the Nghe An data-room map (R-N12; method Horn 1981, R-M29).

Usage: PYTHONPATH=src python scripts/build_relief.py
Downloads the SRTMGL3 v003 tiles that cover the map box from NASA Earthdata (token in EARTHDATA_TOKEN, sent only to
NASA Earthdata hosts: fieldshift.data.earthdata) into data/raw/srtm/ (gitignored), records each in data/MANIFEST.csv,
then writes frontend/public/media/relief/nghe-an-relief.webp and nghe-an-relief.json. A failed download stops the
script; nothing is filled from another source.
"""

import hashlib
import json
import time
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from fieldshift.data import relief
from fieldshift.data.earthdata import earthdata_opener
from fieldshift.data.manifest import append_rows

RAW = Path("data/raw/srtm")
MANIFEST = Path("data/MANIFEST.csv")
GEO = Path("frontend/data/canonical/geo.json")
OUT = Path("frontend/public/media/relief")
IMAGE_WIDTH_PX = 900  # the map is shown at most about 900 px wide (Grid3D stage)
WEBP_QUALITY = 80

# the same cell list the data-room map draws (Grid3D.tsx reads it)
cells = [(c["lat"], c["lon"]) for c in json.loads(GEO.read_text(encoding="utf-8"))["grid"]]
box = relief.map_box(cells)
opener = earthdata_opener()


def get(url: str, retries: int = 4) -> bytes:
    delay = 5.0
    for attempt in range(retries + 1):
        try:
            with opener.open(url, timeout=180) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries:
                raise
        time.sleep(delay)
        delay *= 2
    raise RuntimeError("unreachable")


RAW.mkdir(parents=True, exist_ok=True)
tiles = {}
checksums = {}
for name in relief.tiles_for_box(box):
    path = RAW / f"{name}.SRTMGL3.hgt.zip"
    url = relief.tile_url(name)
    if not path.exists():
        path.write_bytes(get(url))
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    row = relief.manifest_row(path.as_posix(), name, url, datetime.now(UTC).date().isoformat(), sha)
    append_rows(MANIFEST, [row])
    tiles[name] = relief.read_hgt(relief.read_hgt_zip(raw, name), name)
    checksums[name] = {"url": url, "bytes": len(raw), "sha256": sha}

grey = relief.relief_grey(tiles, box, IMAGE_WIDTH_PX)
OUT.mkdir(parents=True, exist_ok=True)
image = OUT / "nghe-an-relief.webp"
Image.fromarray(grey, mode="L").save(image, quality=WEBP_QUALITY, method=6)
west, south, east, north = box
meta = {
    "bbox": {"west": west, "south": south, "east": east, "north": north},
    "size_px": {"width": grey.shape[1], "height": grey.shape[0]},
    "dataset": (
        "NASA JPL (2013). NASA Shuttle Radar Topography Mission Global 3 arc second V003 [SRTMGL3]. "
        "NASA Land Processes Distributed Active Archive Center. doi:10.5067/MEaSUREs/SRTM/SRTMGL3.003"
    ),
    "method": (
        "Horn, B.K.P. (1981). Hill shading and the reflectance map. Proceedings of the IEEE 69(1): 14-47. "
        "doi:10.1109/PROC.1981.11918"
    ),
    "sun": {"azimuth_deg": relief.SUN_AZIMUTH_DEG, "altitude_deg": relief.SUN_ALTITUDE_DEG},
    "earth_radius_m": relief.EARTH_RADIUS_M,
    "tiles": checksums,
}
(OUT / "nghe-an-relief.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
print(f"box {box} | tiles {len(tiles)} | image {grey.shape[1]}x{grey.shape[0]} | {image.stat().st_size} bytes")
