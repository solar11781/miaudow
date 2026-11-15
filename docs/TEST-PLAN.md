# Test plan

This plan says what is tested, how, when and by whom. The detailed test lists are kept next to the specification of
each behaviour, and this plan links to them.

## 1. Rules for every test
- Tests come first: the test is written from the specification, run and seen to fail, and only then is the code
  written (team rule).
- Expected values come from the specification, real data or an external source, never from the code under test.
- Tests on real data run when the cached data is present. On a fresh clone they are skipped, and the skip gives the
  reason.
- We never use random row splits; all splits are time-based (ML-DESIGN.md §7).

## 2. Test levels

| Level | What it checks | Tool | Defined in | Runs |
|---|---|---|---|---|
| Unit (Python) | data readers, cleaning, normal yield, farmland weights, official hazard rules, features, evaluation harness, engine | pytest | the areas in §3 below | every pull request into main (each push), when that side changed |
| Independent spec tests | the same modules, written only from the spec by a separate pass | pytest (`tests/independent/`) | ML-DESIGN.md, DATA-DICTIONARY.md | every pull request into main (each push), when that side changed |
| API contract | response shapes and validation of `/api/past-years`, `/api/compare`, `/api/method`, `/api/health`; HTTP 422 on invalid input; `index.html` for every frontend route | pytest + FastAPI test client | UI-UX-SPEC §11 | every pull request into main (each push), when that side changed |
| Frontend unit and component | components, the `t()` helper, language files, fragment rules, response validation | vitest + Testing Library | UI-UX-SPEC §14 (T-tests marked "now") | every pull request into main (each push), when that side changed |
| End-to-end and accessibility | the farmer flow at 360 x 740: font size, tap targets, contrast, zoom, no horizontal scroll, no personal data, highlight, source sheet | Playwright | UI-UX-SPEC §14 (T1-T38) | every pull request into main (each push), when the frontend changed |
| Model validation | rolling-origin test 2016-2024, region holdout, references B0, B2, BNW, intervals, gates G1-G4 | the evaluation harness | ML-DESIGN.md §6-§8, model card §10b | once per frozen run at the event |
| Reproducibility | a fresh clone rebuilds the result files from the scripts | `scripts/reproduce.sh` | SRS.md NFR-02 | once, from Sunday 00:00, done by the 03:00-05:00 slot |
| Manual | phone check at 360 px; walkthrough as a first-time farmer (an expert-method review, not user testing); load time; demo-day runbook | people with Claude | UI-UX-SPEC §14, SRS.md NFR-03, ARCHITECTURE.md §9 | before a screen counts as done; before judging |

## 3. What each area checks

| Area | Tests |
|---|---|
| Splits / normal | test year never in training indices; normal for year t uses only years < t; ML rain normal from training years only |
| Official conditions | QĐ 18/2021 risk-level rules (Art. 44, 47, 48 rain part, 53; R-A01) on hand-made daily series per cell; both drought readings; per-crop field days for the daily rules and field months for the drought rule; farmland share from the fixed farmland mask; ML feature counts per cell then weighted |
| Rules | YAML schema validation (DATA-DICTIONARY.md §6-§8); every rule has source, study type, place, years, limitations; every water value has a source id; every `read_status` matches REFERENCES.md and `full_text_read` (set per source in rules/sources.yaml) is never true for an abstract, title, summary, metadata or secondary reading; crop keys follow `<plan id>_<season code>_<crop id>`; coverage cells agree with the rules files |
| Engine | no plan hidden; no score or order in the output; output identical for every land and priority except the `request` echo (UI-UX-SPEC T3); no out-of-sample value or range outside the test years; range only where G4 passed; null anomaly without a normal; summary only from 2 non-null values; bare periods derived from spans, including one wrapping period; total = sum of profit values; every source id in a response is in its `sources` map; rounding half up to whole percent |
| ML | same rows for all models; standardisation, normals and fold-time features fitted inside every outer and inner fold (ML-DESIGN.md §4); B0 = each series' own training-years mean anomaly; primary test flagged |
| App | the frontend tests of UI-UX-SPEC §14; FastAPI returns `index.html` for every frontend route and the API shapes of UI-UX-SPEC §11 (FR-10) |
| Data | NSO parser: units, missing symbols, historical-unit ids; row-count snapshot; 2004 named breaks; FAO +-30% flag |

## 4. Continuous integration (every pull request)
CI runs on every pull request into main, and it can also be started by hand. Every run includes the safety hook and
allow-list checker tests, the architecture, source-trace and attribution tests, and a secret scan of the whole history.
When Python-side or CI files changed, the run adds Python lint, format, tests and dependency audit. When frontend or
CI files changed, it adds the frontend dependency allow-list, lint, format, type check, unit tests, build, dependency
audit and browser tests at 360 x 740.

## 5. Entry and exit criteria
- A pull request merges only when every CI check passes, the branch contains the latest main, and the spec review and
  security review found no open issue (merge gate).
- A screen counts as done only after its Playwright check at 360 x 740 and the first-time-farmer walkthrough.
- The model's predictions appear on the cards only for a season whose test passes its gates (ML-DESIGN.md §8); the
  method page reports every result, pass or fail.
- After the feature freeze (Sunday 03:00), the team works only on fixes, checks, documentation and results. Features
  started before the freeze are finished through the same reviews.

## 6. Known limits
- There is no test with real farmers or extension officers, because none is available. The walkthrough is an expert
  review only.
- Tests that call live external services (for example the NASA POWER API) are skipped unless `FIELDSHIFT_LIVE=1` is set.
