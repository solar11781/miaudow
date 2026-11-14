status: DRAFT

# Task queue

Drafted 2026-11-14 15:41 ICT by `/plan-queue` from the planning documents: implementation plan (06 §1, §3b, §4, §6),
02-SRS, UI-UX-SPEC, 03-ML-SPEC, 04-TECH-DESIGN, 05-DATA-CONTRACTS, TEST-PLAN and the decision log to D-159. It
replaces the planning copy as the shared queue; item numbers and done marks are kept from it.

A person approves it by changing the first line to `status: APPROVED` and merging this pull request on GitHub.
Claude never approves or merges it.

- Owners (D-130, D-154, D-159): **member A** (backend, data, ML, method page, copy, submission; every item member B
  left). **Member B** finishes the redesigned web app of pull request #27 (moving into `frontend/`), then works on
  their own extension; no autopilot runs member B's items.
- `not before`: `09:00 Sat` = team work start (D-144). Long-running work (downloads, pipeline, training) runs in the
  background as soon as its inputs exist (D-133). Feature freeze 03:00 Sun 15 Nov (D-144); after it only fixes,
  checks, documentation and results.
- No cuts (D-154): a checkpoint that is behind re-orders the work; it does not drop items.
- Progress marks: when an item merges, add `- done: <date time ICT>, pull request #<n>` under it (here by pull
  request, and in the planning copy at once). A started item gets `- in progress: <who>, branch <name>`. Every pull
  request title names its queue item.

## Done

| Item | What | Owner | Done |
|---|---|---|---|
| 0. chore/normal-merges | gate merges with `--merge`; double-checked reviews (D-152, D-124) | member A | 2026-11-14 09:23, #5; follow-ups #6, #7 |
| 51. chore/unslop-skill | unslop skill copied unchanged (D-153, R-T08) | member A | 09:57, #8 |
| 1. build/python-layout | Python project and data readers moved (04 §2; D-122, D-125; CR-07, NFR-02) | member A | 10:08, #9 |
| 2. feat/series-and-normal | series cleaning and past-only normal yield (03 §3) | member A | 10:19, #10 |
| 3. feat/farmland-and-calendar | farmland weights, season windows, calendar (03 §4; 05 §3, §6b) | member A | 10:29, #11 |
| 4. feat/climate-and-hazards | weather features, official risk-level rules, feature table (03 §4, §5a; 05 §4-§4b) | member A | 10:41, #12 |
| 5. feat/ml-harness | evaluation harness and rolling-origin runner (03 §6-§8) | member A | 10:53, #13 |
| 6. chore/data-scripts | reproduce script, download and export scripts, MANIFEST (CR-07, NFR-02) | member A | 11:19, #14 |
| 7. feat/api-skeleton | FastAPI skeleton, Dockerfile, railway.json, NOTICE; deployed (04 §1, §9, §10) | member A | 11:29, #15, #16 |
| 13. feat/training-table | real-data run, E-000g rebuild (03 §3, §4; 05 §2-§4c) | member A | 11:31, run only |
| 14. feat/normal-method-choice | 3-year mean chosen (E-010), freeze commit ea7a60c (D-72, D-83, D-107) | member A | 11:42, #17 |
| 17. feat/primary-test | B0, B2, BNW, M1, intervals, gates, metrics.json, gates.json (E-012) | member A | 12:27, #18 |
| 18. feat/risk-table-export | artifacts/risk_table.json (05 §5; D-82, D-94) | member A | 12:48, #21 |
| 31. feat/secondary-models | M2 LightGBM, M3 random forest (E-013, E-017; D-145) | member A | 13:20, #22 |
| 15. feat/rules-catalog | rules/*.yaml (05 §6-§8; D-52, D-64, D-68, D-103, D-112) | member A (D-154) | 13:52, #23 |
| 32. feat/sensitivity-runs | pre-registered runs E-018 a-c, E-008 (03 §7; D-145) | member A | 14:31, #24 |
| 16. feat/hazard-labels | artifacts/hazard_labels.json, 2,400 rows (E-019) | member A (D-154) | 14:56, #25 |
| 44a. feat/soil-wetness | artifacts/soil_wetness.json, 450 rows (E-020; 05 §4d; D-135) | member A (D-154) | 15:10, #29 |

Dropped or skipped: 11. chore/rehearsal (skipped, D-143); 12. chore/pre-event-tag (dropped, D-146).

## Member B's redesigned app (pull request #27; no autopilot runs these)

D-159: member B's app covers these items. Each is marked done when pull request #27 merges and its tests are green.

8. feat/frontend-setup: Vite, React, TypeScript, Tailwind 3 in `frontend/`, router, Back and progress, URL-fragment state, language toggle, `t()`.
   - owner: member B
   - spec: UI-UX-SPEC §3, §6, §6a-§6d, §13 items 1, 2, 4; D-102, D-123, D-155
   - tests: T1, T2, T12, T14, T31, T32, T33
   - done when: `npm test`, `npm run build`, `npm run e2e` green; CI green
   - not before: 09:00 Sat
   - team input: none
   - if blocked: park
   - covered by pull request #27 (D-159)
9. feat/frontend-components: components of UI-UX-SPEC §13 item 3 and the visual tokens of §5.
   - owner: member B
   - spec: UI-UX-SPEC §4, §5, §9a, §9b, §10, §13 item 3; D-155
   - tests: T4, T6, T7, T8, T9 (shells), T10 (shells), T20 (component), T27, T35 (components)
   - done when: tests green; CI green
   - not before: 09:00 Sat
   - team input: none
   - if blocked: park
   - covered by pull request #27 (D-159)
10. feat/frontend-contract: `src/api.ts`, the TypeScript types of §11 and placeholder fixtures.
    - owner: member B
    - spec: UI-UX-SPEC §11, §13 item 5; D-102
    - tests: T23 (validation), T34
    - done when: tests green; CI green
    - not before: 09:00 Sat
    - team input: none
    - if blocked: park
    - covered by pull request #27 (D-159)
22. feat/screen-start-field: Start, Screen 1, province line, no-plan screen.
    - owner: member B
    - spec: UI-UX-SPEC §7, §15 item 2; D-94, D-134; FR-01, FR-02
    - tests: T31, T32
    - done when: tests green; Playwright check at 360 x 740; CI green
    - not before: 09:00 Sat
    - team input: none
    - if blocked: park
    - covered by pull request #27 (D-159)
26. feat/source-sheet: Screen 5 in value, rule and source modes.
    - owner: member B
    - spec: UI-UX-SPEC §10; FR-10; H5, H19
    - tests: the sheet's three modes and the R-A01, R-N01, R-N02 blocks from fixtures (T5, T18 sheet part)
    - done when: tests green; CI green
    - not before: 09:00 Sat
    - team input: none
    - if blocked: park
    - covered by pull request #27 (D-159)
23. feat/screen-past-years: Screen 2 with legend, year list and limitation lines.
    - owner: member B
    - spec: UI-UX-SPEC §8; D-93, D-98, D-106, D-120; FR-04
    - tests: T5, T13, T18, T28
    - done when: tests green; Playwright check; CI green
    - not before: 09:00 Sat (after item 26)
    - team input: none
    - if blocked: park
    - covered by pull request #27 (D-159)
24. feat/screen-priority-cards-1: Screen 3 and the card rows header, warnings, calendar, money.
    - owner: member B
    - spec: UI-UX-SPEC §9, §9a; FR-05, FR-06, FR-07, FR-08, FR-18
    - tests: T3 (Playwright part), T16, T17, T19, T20, T21, T22
    - done when: tests green; Playwright check; CI green
    - not before: 09:00 Sat
    - team input: none
    - if blocked: park
    - covered by pull request #27 (D-159)
25. feat/cards-2: card rows stability, water (with soil wetness), land, check, why; priority highlight.
    - owner: member B
    - spec: UI-UX-SPEC §9; FR-08, FR-09, FR-17, FR-20, FR-22; D-135, D-136
    - tests: T11, T23 (render), T24, T25, T26, T30, T36, T38
    - done when: tests green; Playwright check; CI green
    - not before: 09:00 Sat
    - team input: none
    - if blocked: park
    - covered by pull request #27 (D-159)
27. feat/share-print: share link and print view.
    - owner: member B
    - spec: UI-UX-SPEC §9b; FR-14; D-99
    - tests: T35
    - done when: tests green; CI green
    - not before: 09:00 Sat
    - team input: none
    - if blocked: park
    - covered by pull request #27 (D-159)
29. feat/footer-about-sources: footer, About and Sources pages, licence notice file.
    - owner: member B
    - spec: UI-UX-SPEC §12b; D-88, D-91, D-112, D-116
    - tests: T12, T14
    - done when: tests green; CI green
    - not before: 09:00 Sat
    - team input: project email (team name Miaudow, D-134)
    - if blocked: park
    - covered by pull request #27 (D-159)

## Tier 0: end-to-end version (target Sat about 17:15, estimate; D-42, D-144)

19. feat/engine: part 2, `compare()` and `method()` with the pydantic schemas of UI-UX-SPEC §11.
    - owner: member A
    - spec: 04-TECH-DESIGN §3, §4; TEST-PLAN §3 (engine checks); UI-UX-SPEC §11; D-156, D-158
    - tests: T3 (pytest part), T23, T25; `tests/test_source_trace.py` (H5); D-156 rules (even-count median rounded once, empty `years` gets 422); D-158 (autumn-winter window from R-P02, engine numbers cite E-022)
    - done when: tests green; CI green
    - not before: pull request #31 (the plan "why" texts and two source facts, item 19 input) merged
    - team input: none (D-156, D-158 answered the open engine questions)
    - if blocked: park
    - part 1 done: 2026-11-14 12:30 ICT, pull request #19 (schemas, `past_years()`)
    - in progress: member A (Claude), part 2; input pull request #31 open
20. feat/api-endpoints: GET /api/past-years, POST /api/compare, GET /api/method; HTTP 422 on invalid input.
    - owner: member A
    - spec: UI-UX-SPEC §11; 04-TECH-DESIGN §3; D-92; NFR-01
    - tests: T34; a backend test with outbound network blocked (NFR-01)
    - done when: tests green; CI green
    - not before: item 19 merged
    - team input: none
    - if blocked: park
44b. feat/soil-wetness-field: the soil wetness field in the compare response (`CropExposure`).
    - owner: member A
    - spec: UI-UX-SPEC §9, §11 (`CropExposure`); 05-DATA-CONTRACTS §4d; D-135
    - tests: the field equals the artifact values for a fixture artifact; a null value stays null
    - done when: tests green; CI green
    - not before: item 19 merged (item 44a done)
    - team input: none
    - if blocked: park
21. ci/deploy-real: deploy the backend with the real artifacts and the built frontend (a Node build stage in the Dockerfile copies `frontend/dist` into the image); connect the domain member A bought before the event.
    - owner: member A
    - spec: 06 §4 (Sat 15:00-17:15, estimate); 04-TECH-DESIGN §9; D-25, D-129, D-150
    - tests: none
    - done when: /api/health lists every artifact on the Railway URL; `/` and `/phuong-an` return index.html there; the domain opens the app
    - not before: items 20 and 44b merged and pull request #27 merged (team, 2026-11-14 15:20: the production push waits for member B's screens; no backend-only push)
    - team input: none (domain bought by member A, D-150)
    - if blocked: park

## Tier 1: the core, polished by the 03:00 Sun freeze (D-139, D-145)

30. feat/method-page: /phuong-phap in English from the method response (grid figure and rain check sections only when items 45 and 46 are built).
    - owner: member A
    - spec: UI-UX-SPEC §11b; FR-11; D-93, D-111, D-114, D-135; team answer 2026-11-14 14:45 (metrics to 2 decimals, coverage as whole %, papers named by first author and year)
    - tests: T29
    - done when: tests green; CI green
    - not before: item 20 merged
    - team input: none
    - if blocked: park
49. docs/results-chart: one chart of each model's skill against B0, B2 and BNW with its year-bootstrap interval, for the slides and the method page.
    - owner: member A
    - spec: D-145 B; 03-ML-SPEC §6, §7; UI-UX-SPEC §11b (keys `method.resultsChart`, `method.resultsChartAlt`); H5
    - tests: every drawn value equals the value in metrics.json; no number in the chart that metrics.json does not hold
    - done when: chart file made from metrics.json; tests green; CI green
    - not before: 09:00 Sat (items 17, 31 done)
    - team input: none
    - if blocked: park
33. docs/reports: drought-readings difference (E-014), DesInventar check (E-016), zero-weight cells, normal choice; optional hourly rain check (E-015, D-78).
    - owner: member A
    - spec: 05-DATA-CONTRACTS §5b ReportItem; D-54, D-58, D-78
    - first step for E-016: download the DesInventar Viet Nam export (R-A19 URL) into data/raw/ (gitignored); never committed or republished (D-54)
    - tests: none
    - done when: reports in metrics.json `reports`
    - not before: 09:00 Sat
    - team input: none
    - if blocked: continue
28. feat/vi-en-copy: final Vietnamese and English copy for every key, glossary-consistent.
    - owner: member A
    - spec: UI-UX-SPEC §2, §15 items 1-3; FR-12
    - tests: T12
    - done when: no missing or placeholder keys; T12 green
    - not before: pull request #27 merged (the keys live in member B's app)
    - team input: none (land-type labels answered by the team 2026-11-14 14:45: the papers' own Vietnamese phrases with a plain English translation; button pictures by member B, D-134)
    - if blocked: park
53. feat/explain-simply: server endpoint for the FR-15 "explain simply" button: it rewords the shown card text in simpler words with the Claude API; off by default; the text is marked AI-generated; ANTHROPIC_API_KEY lives only in the server environment.
    - owner: member A
    - spec: 02-SRS FR-15; 01-PRD later idea 5; D-146; D-159 (`anthropic` package approved, exact pin)
    - tests: the endpoint refuses when the key is missing; it sends only the card's shown text (no personal data); the reply is marked AI-generated; no call when the feature is off
    - done when: tests green; CI green; the button itself waits for member B's screens
    - not before: 09:00 Sat
    - team input: none
    - if blocked: park
34. docs/figures: README and submission figures from metrics.json (no new claims).
    - owner: member A (team, 2026-11-14 14:29)
    - spec: the planning repository's evening autopilot plan, item 5; H5
    - tests: none
    - done when: figures in docs/figures with source captions
    - not before: 09:00 Sat
    - team input: none
    - if blocked: skip
52. chore/unslop-audit: /unslop in audit and polish mode on every farmer screen and the method page; fix only the findings that fit UI-UX-SPEC.
    - owner: member A (D-159)
    - spec: D-153, D-155; UI-UX-SPEC §3, §5 (anti-"AI look" check), H1
    - tests: existing T1-T8 and Playwright 360 x 740 stay green; one test per fixed finding where it is testable
    - done when: audit list in the pull request with each finding fixed or rejected with the spec line that rules it out
    - not before: pull request #27 merged; a person types /unslop on the morning of Sun 15 Nov (D-159); the autopilot never starts it
    - team input: the time (see open questions: D-159 says Sunday morning, 06 §4 says before the 03:00 freeze)
    - if blocked: park

## Submission (Sun 03:00 to 11:00, D-144)

35. docs/readme-final: attribution and licence table (including D-157 and D-159 packages), SI (AI) disclosure (D-140), pre-event section, reproduce steps; SI-generated code and data acknowledged (R-H15); copy the D-148 documents under their new names (PRD, SRS, ML-DESIGN, ARCHITECTURE, DATA-DICTIONARY, UI-UX-SPEC, REFERENCES, DATA-SOURCES, GLOSSARY, TEST-PLAN) into docs/ with every reference to non-copied material removed and no mention of the planning repository.
    - owner: member A
    - spec: CR-03, CR-04, CR-05, CR-06, CR-07, CR-08, CR-13, NFR-07; D-81, D-88, D-127, D-148
    - tests: `tests/test_attribution.py`
    - done when: README complete; attribution script output matches the lock file
    - not before: Sun 03:00 (after the feature freeze)
    - team input: the SI declaration text (Claude asks, the team reviews before commit, D-140); the pre-event section is written and posted by member A, Claude does not draft it (D-144)
    - if blocked: park
36. chore/fresh-clone-check: fresh clone rebuilds the artifacts; static fallback snapshot of real responses; IMERG stage skipped if item 45 is not built.
    - owner: member A (has the Earthdata login, D-150)
    - spec: 06 §4; 04-TECH-DESIGN §1; NFR-02; D-150, D-151
    - tests: none
    - done when: rebuild matches; snapshot stored
    - not before: Sun 00:00 (D-150)
    - team input: none
    - if blocked: continue
37. chore/honesty-review: every displayed number traced to REFERENCES; /final-audit and /submission-check (typed by a person).
    - owner: member A (team, 2026-11-14 14:29)
    - spec: CLAUDE.md scientific boundaries; NFR-09; FR-10; CR-13
    - tests: `tests/test_source_trace.py`
    - done when: no untraced number; checks pass
    - not before: Sun 03:00 (after the feature freeze)
    - team input: none
    - if blocked: park
38. docs/demo-slides: at most 7 slides including the cover, in English, Hanoi outline, for a 10-minute talk and 5 minutes of questions (D-147); next-step story of the country data pack (01-PRD §5 item 7, D-149); likely judge questions with short sourced answers; team name, members, challenge, project image, user experience, how NASA data make it possible; no likeness of anyone under 18; any SI-generated image watermarked (R-H15).
    - owner: member A
    - spec: D-121, D-147, D-149; CR-10, CR-11, CR-12, CR-13
    - tests: none
    - done when: link opens in a private window
    - not before: Sun 03:00 (after the feature freeze)
    - team input: none
    - if blocked: park
39. chore/submit: first submission about 04:30 (estimate) with short English form texts, the deployed app as the Final Project link and a placeholder demo link; final resubmit 10:00; tag `submitted-hanoi` at 11:00 on the last submitted commit and a frozen production branch for the Hanoi version (D-146).
    - owner: member A (Team Owner)
    - first step: a cover slide (team name, members, challenge) whose public link is the placeholder demo link; replaced when item 38 is done
    - spec: CR-01, CR-11; D-84, D-121, D-146
    - tests: none
    - done when: submitted status visible on the team page; FortiGuard web filter classification requested for the app's domain (R-H15)
    - not before: Sun 03:00 (the portal opens 09:00 Sat, R-H09)
    - team input: the reviewed SI declaration text for the form (D-140)
    - if blocked: park
43. chore/global-round: improvements for the global round on separate branches; the Hanoi version stays on the frozen production branch. First candidate: the SMAP soil-moisture check (D-135), with research, tests and validation.
    - owner: member A
    - spec: D-84, D-131, D-135, D-146; FR-16; R-H09 (global deadline 23:59)
    - tests: all tests green on each change
    - done when: global submission updated by 23:59 Sunday; after the 16:30 closing, the project page and app link switched to the improved version
    - not before: 11:00 Sun
    - team input: none
    - if blocked: skip

## Bonus (only after the core is polished, in this order; D-139, D-154, D-159)

The core is items 0-39 (without 11, 12), 44a, 44b, 49, 51, 52 and 53. Bonus items never take time from it. Order of
06 §3b, except that items 40 and 47 are built last (D-159).

45. feat/rain-check: artifacts/rain_check.json (IMERG monthly vs POWER monthly, farmland-weighted) and `rain_check` in the method response.
    - owner: member A
    - spec: 05-DATA-CONTRACTS §5c; UI-UX-SPEC §11, §11b; FR-21; D-135; E-021
    - tests: mm/hr to monthly mm on a known month length; pixel-in-cell rule at the edges; correlation on a hand-made pair; complete months only
    - done when: artifact exported; schema test green; CI green
    - not before: the core is done (D-139); IMERG months complete (69/288 at item 6)
    - team input: none
    - if blocked: park (the method page shows `method.rainNotRun`)
46. docs/grid-figure: artifacts/figures/nghe_an_grid.svg from cell_weights.csv and the geoBoundaries boundary, served by the backend.
    - owner: member A
    - spec: 05-DATA-CONTRACTS §5c; UI-UX-SPEC §11b item 4; FR-21; D-135
    - tests: one shape per Nghệ An cell; no numbers other than those in cell_weights.csv
    - done when: figure shown on /phuong-phap; CI green
    - not before: the core is done (D-139)
    - team input: none
    - if blocked: skip
48. feat/priority-line: the priority line on cards cc1..cc4 (UI-UX-SPEC §9).
    - owner: member A (D-159)
    - spec: UI-UX-SPEC §9 priority highlight; FR-23; D-136, D-139
    - tests: T37
    - done when: tests green; Playwright check; CI green
    - not before: the core is done and pull request #27 merged (built on member B's app)
    - team input: none
    - if blocked: skip
50. docs/weather-importance-research: "which weather mattered most", research first.
    - owner: member A
    - spec: D-145 C; CLAUDE.md scientific boundaries (no causal reading)
    - tests: written only after research names a published method that is stable with correlated weather columns
    - done when: research note with the method and its source; build only if the team says go
    - not before: the core is done (D-139, D-145)
    - team input: the go, after the research note
    - if blocked: skip
41. feat/sign-in: optional Google sign-in and saved answers, several saved sets per account (backend and frontend in one pull request).
    - owner: member A
    - spec: UI-UX-SPEC §12c; D-90, D-105, D-150, D-159 (Railway PostgreSQL; `google-auth` and `psycopg` approved, exact pins)
    - tests: T14 still green without sign-in; sign-in token checked on the server; delete-everything removes every saved row
    - done when: sign-in works; delete-everything works; CI green
    - not before: the core is done; pull request #27 merged
    - team input: the user creates the Google OAuth client (openid scope only) and the Railway database and sets GOOGLE_CLIENT_ID and DATABASE_URL on the miaudow service (D-159, before 16:45 Sat)
    - if blocked: skip
42. feat/price-entry: optional "your price and costs".
    - owner: member A (D-159)
    - first step: write the missing UI-UX-SPEC §12d details from cited sources: entry per ha always; per sào only with a sourced Nghệ An sào size; every number and method cited (D-159)
    - spec: UI-UX-SPEC §12d, §15 item 11; FR-13; D-94, D-159; CLAUDE.md (revenue is not profit; no profit claim without user-entered costs)
    - tests: written first from the §12d details
    - done when: tests green; CI green
    - not before: the core is done; pull request #27 merged
    - team input: none (go and method given by D-159)
    - if blocked: skip
40. feat/map-page: optional /ban-do for officers and judges: 2D SVG map of the Nghệ An cells per year and rule (D-138).
    - owner: member A (D-159)
    - first step: check member B's app (pull request #27) and their extension for a map; if one exists, build only the enhancement it lacks (D-159)
    - spec: UI-UX-SPEC §12, §15 item 4; D-74, D-138, D-155, D-159
    - tests: T15
    - done when: T15 green; CI green
    - not before: every other bonus item above done or skipped (built last, D-159)
    - team input: none (go, D-159)
    - if blocked: skip
47. feat/map-relief: NASA SRTM shaded-relief layer on /ban-do.
    - owner: member A (D-159)
    - first step: research the shading method's published source; same duplicate check as item 40
    - spec: UI-UX-SPEC §12; D-18, D-138, D-159
    - tests: written with the layer's spec (download checksum, the cited shading method on a small known grid, the `map.reliefNote` label visible)
    - done when: tests green; CI green
    - not before: item 40 done and its tests green
    - team input: none for the go (D-159); park if research finds no published shading method
    - if blocked: skip

## Coverage table

| ID | Item(s) |
|---|---|
| H1, H2 | 8, 9 (H1 as relaxed by D-155; 52 checks) |
| H3 | 19, 24 |
| H4 | 9 |
| H5 | 19, 23, 26, 37, 49 |
| H6, H7, H8, H9, H10, H11 | 9, 22-25 |
| H12 | 8 |
| H13 | 23, 24 |
| H14 | 7, 8 |
| H15, H16 | 8, 28 |
| H17 | 24 |
| H18 | 22, 24 |
| H19 | 23, 26 |
| T1, T2, T31, T32, T33 | 8 (T31, T32 also 22) |
| T12 | 8, 28, 29 |
| T14 | 7, 8, 29, 41 |
| T4, T6, T7, T8, T27 | 9 |
| T9, T10 | 9, 22-25 |
| T20 | 9, 24 |
| T35 | 9, 27 |
| T23 | 10, 19, 25 |
| T34 | 10, 20 |
| T3 | 19, 24 |
| T5, T18 | 23 (in full), 26 (sheet part), 24 (/phuong-an) |
| T13, T28 | 23 |
| T11 | 25 |
| T16, T17, T19, T21, T22 | 24 |
| T24, T26, T30 | 25 |
| T25 | 19, 25 |
| T29 | 30 (also 45, 46 when built) |
| T36 | 25, 44b |
| T38 | 25 |
| T37 | 48 |
| T15 | 40 |
| FR-01, FR-02 | 22 |
| FR-04 | 23 |
| FR-05, FR-06, FR-07, FR-18 | 24 |
| FR-08 | 24, 25 |
| FR-09, FR-17, FR-22 | 25 |
| FR-10 | 26, 37 |
| FR-11 | 30, 49 |
| FR-12 | 28 |
| FR-13 | 42 |
| FR-14 | 27 |
| FR-15 | 53 (the button on member B's screens) |
| FR-16 | 43 (SMAP check after the 11:00 Sunday submission, D-135) |
| FR-20 | 44a, 44b, 25 |
| FR-21 | 45, 46, 30 |
| FR-23 | 48 |
| DR-01, DR-02, DR-03, DR-05 | 13, 15 |
| DR-06 | NOT COVERED: done 2026-11-13 (challenge resources read); not a code item |
| NFR-01 | 20 |
| NFR-02 | 6, 36 |
| NFR-03, NFR-04, NFR-05 | 22-25 |
| NFR-06 | 7, 8 |
| NFR-07 | 35 |
| NFR-08 | 2, 5, 17, 31, 32 |
| NFR-09 | 37 |
| CR-01, CR-11 | 39 (CR-11 also 38) |
| CR-02 | 13, 16, 17 |
| CR-03 | 35 |
| CR-04, CR-05, CR-06, CR-07, CR-08 | 35 (CR-07 also 1, 6) |
| CR-09 | NOT COVERED: attendance is done by people (D-100), not code |
| CR-10 | 35, 38 |
| CR-12 | 38 |
| CR-13 | 35, 37, 38 |

## Open team questions

- Hanoi judging slot: not received yet (D-146).
- SI declaration text for the README and the form (items 35, 39; D-140).
- Item 52 time: answered by the user (2026-11-14): a person types /unslop on the morning of Sun 15 Nov (D-159); the audit only fixes findings, which fits the after-freeze rule of fixes only.
- Item 41: done (2026-11-14 before 16:45): Google OAuth client published (openid only), GOOGLE_CLIENT_ID and DATABASE_URL set, Railway PostgreSQL added.
- Item 28: the land-type label answer (2026-11-14 14:45: the papers' own phrases with a plain English translation) is D-160.
- Item 29: project email for the About page (member A creates it with the domain, D-143).
