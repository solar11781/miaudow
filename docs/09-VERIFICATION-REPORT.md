# MIAUDOW 2.0 — verification report and completion matrix

Date: 14 November 2026. Machine: Windows 11, Python 3.13.2, Node 26.13.1, Microsoft Edge (Playwright channel
`msedge`). Every number below was produced by a command in this repository on that day; nothing is estimated.

## Commands and results

| Check | Command (from the project root unless noted) | Result |
|---|---|---|
| Python tests (API cores, climate ML, quality checks, rules, copilot, pipeline) | `.venv\Scripts\python -m pytest api/tests pipeline/tests -q` | **288 passed** |
| Python lint and format | `.venv\Scripts\ruff check api pipeline scripts` and `ruff format --check` | clean |
| Canonical data equals the team's outputs | `pipeline/tests/test_canonical_identity.py` (inside the 288) | hazards, soil, geo, model identical value for value |
| Type check | `cd web && npx tsc -b` | clean |
| Web lint | `cd web && npx eslint .` | clean (strict typescript-eslint, react-hooks, complexity ≤ 14) |
| Web unit tests | `cd web && npx vitest run` | **39 passed** |
| Browser journeys + WCAG 2.2 AA (axe) | `cd web && npm run build && npx playwright test e2e/journey.spec.ts` (API running on :8000; for repeated local runs set `MIAUDOW_COPILOT_RATE=500/600`, the default 20 questions per 10 minutes is reached) | **47 passed, 1 skipped** (clipboard check runs on desktop only) at 360 × 740 and 1440 × 900 |
| Production build | `cd web && npm run build` | builds; largest chunks (gzip): Earth globe 1.13 MB (`/dai-quan-sat` only), science 3D 154 kB (science only), React 99 kB, app shell 92 kB |
| Retrieval benchmark | `.venv\Scripts\python api/eval/run_retrieval_eval.py` | see below |
| Climate ML evaluation | `.venv\Scripts\python api/eval/run_climate_ml_eval.py` | see below; a test checks the stored file equals a fresh run |
| Data-quality report | `.venv\Scripts\python pipeline/check_quality.py` (also the last step of the canonical build) | **75 checks: 64 pass, 11 warn, 0 fail** |

### What the browser tests prove

- A farmer finishes the four steps by tapping only; the answers live in the URL, survive a reload and the back link.
- **Nothing is written to localStorage, sessionStorage or cookies** (team rule H14).
- **Farmer routes load no 3D code and no canvas** (D-155).
- Every sourced number opens its provenance sheet; Escape closes it and focus returns.
- The language switch changes the whole interface.
- One year selected on the science page reaches the copilot through the URL, and the copilot answers about it.
- The copilot answers from data and abstains on an unrelated question; with the API running, the farmer's
  canal-end question returns the six plans in the study's order and no ranking words.
- axe finds **no WCAG 2.2 AA violation** on home, both farmer steps tested, officer, science, evidence and copilot.
- No page scrolls sideways at 360 px; **no visible text is smaller than 17 px** (team rule H6).
- **Earth observatory:** the eight scenes step forward and keep scene, year and cell in the link; the annual rain
  shown for a cell equals `data/canonical/climate.json`; under reduced motion no canvas is created and the page
  says why; NASA Eyes opens in a dialog with the official URL, and "Trở về Trái Đất" lands on the Nghệ An scene;
  the insight hands its year to the copilot, which answers about it; axe finds no violation on the insight scene.
- The climate ML section lists the closest years exactly as `climate_ml.json` holds them and moves the shared
  year; the evidence page shows the quality counts and every warning exactly as `quality.json` holds them.

### Retrieval benchmark (AI core 02), TEST split

`api/eval/retrieval_eval.jsonl` holds 73 questions (Vietnamese with and without diacritics, some English),
split into DEV (thresholds tuned here only) and TEST. Results on TEST (27 answerable, 9 unanswerable):

| Metric | Value |
|---|---|
| recall@1 / @3 / @5 | 0.481 / 0.815 / 0.889 |
| MRR | 0.651 |
| Abstention precision / recall, with the rule guard | 1.0 / 0.889 |
| Abstention precision / recall, thresholds only | 1.0 / 0.667 |
| Answerable questions wrongly refused | 0 |

The set is small and was written by the team, so the numbers are noisy and not independent. Recall@1 is weak: the
3,000-word legal articles added in this build often outrank the shorter rule passages. A browser test found that
"công thức nấu phở" was answered with legal text; an IDF-weighted coverage floor (0.3, set on DEV) now makes it
abstain without changing the TEST numbers.

### Climate ML (AI core 01, part two), leave one year out, 1992–2024

| Task | Closest year | Same as last year | Always "normal" |
|---|---|---|---|
| Same annual rain group (low / near / high) | 18/33 (55 %) | 16/33 (48 %), McNemar p = 0.75 | 9/33 (27 %), p = 0.06 |
| Drier or wetter than normal | 25/33 (76 %) | 19/33 (58 %) | 16/33 (48 %) |
| Choose by January–June, score July–December | 11/33 (33 %) | 16/33 (48 %) | 9/33 (27 %) |

The analogs are alike in the months they were chosen on, but they have no forecast skill: on the second half of the
year they lose to "same as last year". The app says so beside the analogs. The unusual-year score flags 1997, 2018
and 2022; the simple rule (annual total outside the 10th–90th percentile) flags eight years; they share only 2022
(agreement 73.5 %, kappa 0.06). There is no ground truth, so this is agreement, not accuracy.

### Field-phone performance (measured, not assumed)

Playwright on Edge, Galaxy S9+ profile at 360 × 740, 4× CPU slowdown, 1.6 Mbps / 150 ms, cache off, median of 3 cold
loads (`npx playwright test e2e/visual/perf.spec.ts --project=phone-360`). Runs vary by about ±0.4 s.

| Page | LCP median | CLS max | Target LCP ≤ 2.5 s |
|---|---|---|---|
| Farmer step 1 | 1.8–1.9 s | 0.001 | met |
| Copilot | 1.9 s | 0.001 | met |
| Evidence library | 2.1–2.2 s | 0.000 | met |
| Farmer plan cards | 2.5–2.7 s | 0.022 | borderline |
| Home | 2.8–3.2 s | 0.005 | **not met** |
| Science | 3.0–3.7 s | 0.015 | **not met** (three.js now loads after the page paints) |

Not measured on a real handset. INP was not measured. The Earth observatory was not measured: its globe chunk is
1.13 MB gzip and loads after the page paints; on a slow phone the panels are usable before the globe appears.

### Model results shown in the app (team experiment E-012, not retrained here)

Rolling-origin test 2016–2024, skill against the model without weather (BNW): spring rice 0.025 (90 % interval
−0.027 to 0.082), so no spring prediction is shown; winter rice 0.068 (0.003 to 0.134), shown with its interval;
summer-autumn failed gate G1 (too few provinces), not modelled.

## Completion matrix

### Implemented and tested

- Six areas (home, farmer, officer, science, evidence, copilot) on one design system, Vietnamese and English.
- One canonical data layer read by both the API and the web app; data registry generated from it
  (`docs/08-DATA-REGISTRY.md`).
- **Climate core:** NASA POWER 1990–2024 for the five farmland cells, complete-month aggregation, 1991–2020 normals,
  anomalies, hot and cold days, longest dry spell (CDD), official drought reading; CHIRPS v3 beside it, never merged.
- **Evidence core:** 538 passages (team rulebook, sources, climate summaries, model gates, QĐ 18/2021 and
  NĐ 112/2024 full text), hybrid lexical retrieval, abstention, benchmark above.
- **Decision core:** six plans in study order, never ranked; verified study values with table locations; derived
  totals; applicability to the farmer's water situation; what the tool cannot know; questions for the officer.
- **Copilot (deterministic engine):** intents, tools, number check, visual cards, browser voice input with
  transcript confirmation, read-aloud.
- **Copilot (Claude engine):** manual tool loop with strict tools, JSON answer schema, refusal fallback, typed
  error handling, rate limit, number check that discards an answer with an unverified number — tested with a
  scripted client (25 tests).
- WebGL observatory of the real Nghệ An outline and NASA grid, 2D fallback; shared year across map and charts.
- **Earth observatory (Phase 2):** CesiumJS globe with NASA GIBS imagery, eight scenes from space to Lưu Sơn,
  geoBoundaries outlines, Sentinel-2 NDVI over the district, NASA POWER cells as 3D columns, official NASA Eyes
  in a dialog, shared URL state, reduced-motion and no-WebGL fallbacks.
- **Climate ML (Phase 2):** analog years and unusual-year scores with leave-one-year-out evaluation against
  baselines; shown on the science page with the verdicts; six new copilot tools on the same functions.
- **Data foundation (Phase 2):** 75 automatic quality checks per build, coverage and provenance endpoints, model
  evaluation and AI capability endpoints.
- Licensed photography (14 photos, creators and licences in the footer) and labelled concept art.
- Sentinel-2 NDVI composites over the former Đô Lương district; MODIS NDVI at the study site; geoBoundaries
  district outline; 14 verified GIBS layers; 23 verified NASA Eyes deep links.

### Implemented but not fully validated

- The Claude engine against the real API: no key is configured on this machine.
- Browser speech recognition on real phones and for the Nghệ An dialect (no annotated audio; WER harness only).
- Sentinel-2 composites: greenness only, not validated against ground observations; 2020–21 and 2024 are not
  comparable as change (scene counts and processing baselines differ).
- Performance on real handsets; usability with farmers and officers (no moderated sessions yet).
- The globe on low-end phones (tested in headless Edge with SwiftShader only).
- Climate ML beyond its proxy tasks: 33 years are too few to show the analog advantage is not chance.

### Designed but requiring external data

- Field-level soil, irrigation schedules, local prices, labour and buyer contracts (the decision core lists them as
  unknown in every answer).
- The P-02 full text in the evidence library: the journal forbids copying without written consent.
- Lưu Sơn commune boundary: geoBoundaries has no Vietnamese ADM3 layer.
- Neural embeddings for retrieval: the `Embedder` interface exists; no model is installed.

### Blocked by credentials or permissions

- NASA Earthdata products (HLS, SMAP, GPM IMERG, ECOSTRESS): granules over Đô Lương found through NASA CMR; downloads
  need a free Earthdata Login (`EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD` or `.netrc`). `pipeline/fetch_nasa_missions.py`
  is ready.
- Claude: needs `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` in `api/.env` (server only).

MIAUDOW is a hackathon project of team Miaudow; it is not endorsed by NASA, ESA or any agency whose data it uses.
