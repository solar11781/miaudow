# Figures

Figures for the README and the submission. Every number in them comes from a committed artifact; the source ids
(R-..., E-...) are listed in `rules/sources.yaml`. All of them show past years, never a forecast. The app itself shows
numbers, not these images.

| File | What it shows | Source |
|---|---|---|
| `rice_anomaly_history.svg` | Nghệ An rice yield against its past-only normal, per season and year 1995-2024 (bars); for the winter season, the M1 out-of-sample estimate of each test year and its 80% range | `artifacts/risk_table.json`: NSO yields (R-D01), normal (E-010), M1 estimates (E-012) |
| `rice_anomaly_history.png` | The same figure as a PNG | render of the SVG above |
| `farmland_rule_shares.svg` | Share of Nghệ An farmland where each of the five official rules was met in each year 1995-2024, one panel per rule | `artifacts/hazard_labels.json`, year rows (E-019): NASA POWER daily values (R-N01), NASA MODIS farmland mask (R-N02), thresholds of QĐ 18/2021/QĐ-TTg (R-A01) |
| `farmland_rule_shares.png` | The same figure as a PNG | render of the SVG above |
| `results_chart.png` | Skill of each model against the three references, with 90% year-bootstrap intervals | render of `artifacts/figures/results_chart.svg`, built from `artifacts/metrics.json` (E-012, E-013, E-017) by `scripts/build_results_chart.py` |

## How they are made

The SVG files are written by `scripts/build_figures.py` (code in `src/fieldshift/ml/figures.py`), a stage of
`scripts/reproduce.sh`; `tests/test_figures.py` checks that the committed SVG files equal the builder output and that
every bar and mark sits at its artifact value.

The PNG files are renders of the SVG files at twice their size with headless Microsoft Edge 157.0.4341.46, one command
per figure, run from the repository root:

```
msedge --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size=<svg width>,<svg height> --screenshot=<png path> file:///<absolute svg path>
```

Render them again after the SVG files change.
