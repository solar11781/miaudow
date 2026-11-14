"""Build data/processed/crop_stats.csv from the NSO PX-Web exports in data/raw/nso (05-DATA-CONTRACTS §2).

Usage: PYTHONPATH=src python scripts/build_crop_stats.py
retrieved_on per table comes from the data/MANIFEST.csv row whose sha256 matches the export (nso.retrieval_dates).
"""

from fieldshift.data.nso import build_crop_stats, retrieval_dates

table = build_crop_stats("data/raw/nso", retrieved_on=retrieval_dates("data/MANIFEST.csv", "data/raw/nso"))
table.to_csv("data/processed/crop_stats.csv", index=False)
print(
    "rows:",
    len(table),
    "| crops:",
    sorted(table["crop"].unique()),
    "| retrieved_on:",
    sorted(table["retrieved_on"].unique()),
)
