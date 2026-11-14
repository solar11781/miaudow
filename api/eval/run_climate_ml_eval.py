"""Evaluation of the climate ML of AI core 01 (api/miaudow_api/climate_ml.py).

Run from the project root:

    .venv\\Scripts\\python api/eval/run_climate_ml_eval.py

What it measures (all deterministic, no randomness):
- Analog years, leave-one-year-out on 1992-2024: the normal, the z-score scale and the tercile thresholds are refitted
  on 1991-2020 without the held-out year. Hit rates of the nearest analog's annual rain category (terciles) and sign
  against climatology ("near normal" / majority sign) and persistence (previous year), with exact McNemar p-values.
  An out-of-sample check picks analogs from January-June and scores July-December.
- Anomalous years: agreement of the robust monthly score (flag above the 95th percentile of 1991-2020) with the rule
  "annual total outside the 10th-90th percentile of 1991-2020", and a cross-check of the same detector on CHIRPS.
Writes api/eval/results/climate_ml_2026-11-14.json; /api/models/evaluations serves it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

from miaudow_api import climate_ml  # noqa: E402

DATE = "2026-11-14"


def build() -> dict:
    return {
        "date": DATE,
        "script": "api/eval/run_climate_ml_eval.py",
        "command": climate_ml.EVAL_COMMAND,
        **climate_ml.full_evaluation(),
    }


def main() -> None:
    result = build()
    out = climate_ml.EVAL_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    proxy = result["analogs"]["proxy_task"]
    oos = result["analogs"]["out_of_sample_check"]
    agree = result["model"]["metrics"]["anomalies_agreement_all_years"]
    lines = [
        f"analogs, leave-one-year-out ({proxy['n_cases']} years), annual rain tercile hit rate:",
        f"  analog {proxy['hit_rates']['analog_k1_tercile']}  persistence {proxy['hit_rates']['persistence_tercile']}"
        f"  climatology {proxy['hit_rates']['climatology_tercile']}  (McNemar p vs persistence "
        f"{proxy['mcnemar_p']['tercile_analog_vs_persistence']}, vs climatology "
        f"{proxy['mcnemar_p']['tercile_analog_vs_climatology']})",
        f"  out of sample (Jan-Jun -> Jul-Dec): analog {oos['hit_rates']['analog_k1_tercile']}  persistence "
        f"{oos['hit_rates']['persistence_tercile']}  climatology {oos['hit_rates']['climatology_tercile']}",
        f"anomalous years: monthly method {agree['ml_years']}, percentile rule {agree['baseline_years']}, "
        f"agreement {agree['percent_agreement']}%, kappa {agree['cohen_kappa']}",
        f"written {out.relative_to(ROOT)}",
    ]
    sys.stdout.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
