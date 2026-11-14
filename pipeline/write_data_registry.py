"""Write docs/08-DATA-REGISTRY.md from the canonical catalog, so the registry can never drift from the data.

Run from the project root after pipeline/build_canonical.py:

    .venv\\Scripts\\python pipeline/write_data_registry.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "data" / "canonical"
OUT = ROOT / "docs" / "08-DATA-REGISTRY.md"
ORDER = {"INGESTED": 0, "PARTIAL": 1, "CONTRACT_ONLY": 2, "BLOCKED": 3}


def cell(text: object) -> str:
    return str(text if text not in (None, "") else "—").replace("|", "/").replace("\n", " ")


def main() -> None:
    catalog = json.loads((CANON / "catalog.json").read_text(encoding="utf-8"))
    gibs = json.loads((CANON / "gibs_layers.json").read_text(encoding="utf-8")) if (CANON / "gibs_layers.json").exists() else None
    datasets = sorted(catalog["datasets"], key=lambda d: (ORDER.get(d["ingestion_status"], 9), d["dataset_id"]))
    counts: dict[str, int] = {}
    for d in datasets:
        counts[d["ingestion_status"]] = counts.get(d["ingestion_status"], 0) + 1

    lines = [
        "# MIAUDOW — data registry",
        "",
        f"Generated from `data/canonical/catalog.json` (built {catalog['generated_at']}) by `pipeline/write_data_registry.py`.",
        "Do not edit by hand: rebuild the canonical data, then rerun the script.",
        "",
        "Ingestion state: " + ", ".join(f"**{k}** {v}" for k, v in sorted(counts.items(), key=lambda kv: ORDER.get(kv[0], 9))) + ".",
        "No dataset below is a measurement on a farmer's field except the two trial studies, and those describe one",
        "unreplicated plot per crop in Lưu Sơn, Đô Lương, 2020–21.",
        "",
        "| Dataset | State | Provider | Resolution | Time span | Licence | Field measurement |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in datasets:
        lines.append(
            f"| `{d['dataset_id']}` — {cell(d['title']['en'])} | {d['ingestion_status']} | {cell(d['provider'])} | "
            f"{cell(d['spatial_resolution'])} | {cell(d['temporal_coverage'])} | {cell(d['license'])} | "
            f"{'yes' if d['is_field_measurement'] else 'no'} |"
        )
    lines += ["", "## Notes per dataset", ""]
    for d in datasets:
        lines.append(f"### `{d['dataset_id']}` — {d['title']['en']}")
        lines.append("")
        lines.append(f"- Source: {cell(d['source_url'])} (source id `{d['source_id']}`), revision {cell(d['source_revision'])}, retrieved {cell(d['retrieved_at'])}")
        lines.append(f"- Missing values: {cell(d['missing_policy'])}")
        lines.append(f"- Allowed use: {cell(d['allowed_use']['en'])}")
        if d.get("version_sha256"):
            lines.append(f"- SHA-256: `{d['version_sha256']}`")
        for n in d.get("notes", [])[:4]:
            lines.append(f"- {cell(n['en'])}")
        lines.append("")
    lines += ["## Methods", "", "| Method | What it does | Sources |", "|---|---|---|"]
    for m in catalog["methods"]:
        lines.append(f"| `{m['method_id']}` | {cell(m['description']['en'])} | {', '.join(m['source_ids'])} |")
    lines += ["", "## Displayed metrics", "", "| Metric | Unit | Method | Does not prove |", "|---|---|---|---|"]
    for mid, m in catalog["metrics"].items():
        lines.append(f"| `{mid}` — {cell(m['title']['en'])} | {cell(m['unit'])} | `{m['method_id']}` | {cell(m['does_not_prove']['en'])} |")
    if gibs:
        layers = gibs.get("layers", gibs if isinstance(gibs, list) else [])
        lines += ["", "## NASA GIBS imagery layers (visual source, not evidence)", ""]
        lines.append(f"{len(layers)} layers verified against the WMTS capabilities with one real tile request each.")
        lines.append("")
        lines += ["| Layer | Time range | Format |", "|---|---|---|"]
        for layer in layers:
            name = layer.get("identifier") or layer.get("id") or layer.get("layer")
            time = layer.get("time", {})
            span = f"{time.get('start', '')} … {time.get('end', '')}" if isinstance(time, dict) else cell(time)
            lines.append(f"| `{name}` | {cell(span)} | {cell(layer.get('format'))} |")
    lines += [
        "",
        "## Lineage",
        "",
        "`data/raw/*` (immutable fetches with a manifest each) → `pipeline/build_canonical.py` (validation, complete-month",
        "rule, rule thresholds, farmland weighting) → `data/canonical/*.json` (one copy) → `api/miaudow_api` tools and",
        "the web app (Vite alias `@data`) → charts, 3D layers, plan cards and copilot answers. A missing input stops the",
        "build; nothing is interpolated or filled with zero.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(datasets)} datasets)")


if __name__ == "__main__":
    main()
