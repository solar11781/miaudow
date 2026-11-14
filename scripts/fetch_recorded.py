"""Download files recorded in data/MANIFEST.csv from their recorded https URL, kept only if the sha256 matches.

Usage: PYTHONPATH=src python scripts/fetch_recorded.py data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson
Used by reproduce.sh for downloads that have no script of their own (CR-07, NFR-02).
"""

import sys

from fieldshift.data.manifest import fetch_recorded

for path in sys.argv[1:]:
    print("fetched", fetch_recorded(path).as_posix())
