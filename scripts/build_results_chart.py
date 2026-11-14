"""Write artifacts/figures/results_chart.svg from artifacts/metrics.json (UI-UX-SPEC section 11b results chart; item 49).

Usage: PYTHONPATH=src python scripts/build_results_chart.py   (after scripts/run_sensitivity.py)
"""

import json
from pathlib import Path

from fieldshift.ml.results_chart import results_chart_svg

doc = json.loads(Path("artifacts/metrics.json").read_text(encoding="utf-8"))
out = Path("artifacts/figures/results_chart.svg")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(results_chart_svg(doc), encoding="utf-8", newline="\n")
print("wrote", out, "|", out.read_text(encoding="utf-8").count("<circle"), "marks")
