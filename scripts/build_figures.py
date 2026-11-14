"""Write the README and submission figures docs/figures/*.svg from the committed artifacts (queue item 34).

Usage: PYTHONPATH=src python scripts/build_figures.py   (after scripts/export_crop_exposure.py)
The PNG copies are headless browser renders of these SVGs; docs/figures/README.md gives the command.
"""

import json
from pathlib import Path

import yaml

from fieldshift.ml.figures import rice_history_svg, rule_shares_svg


def _load(path: str) -> object:
    text = Path(path).read_text(encoding="utf-8")
    return yaml.safe_load(text) if path.endswith(".yaml") else json.loads(text)


figures = {
    "rice_anomaly_history.svg": rice_history_svg(_load("artifacts/risk_table.json"), _load("rules/method.yaml")),
    "farmland_rule_shares.svg": rule_shares_svg(_load("artifacts/hazard_labels.json"), _load("rules/conditions.yaml")),
}
out = Path("docs/figures")
out.mkdir(parents=True, exist_ok=True)
for name, svg in figures.items():
    (out / name).write_text(svg, encoding="utf-8", newline="\n")
    print("wrote", out / name, "|", svg.count("<rect ") - 1, "bars")
