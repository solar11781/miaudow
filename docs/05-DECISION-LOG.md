# MIAUDOW — decisions and dependency ledger

All visual and scientific compromises must be explicit before merge. Record new changes as a new D-number rather than editing away the reasons.

| ID | Decision | Implementation / follow-up |
|---|---|---|
| D-001 | Cinematic concept art is not a documentary photo | All bundled concept images declared AI-generated and non-geolocated in `ASSET_MANIFEST.json` and on UI caption. Replace with cleared Nghệ An photos before publish. |
| D-002 | No redistributed editorial photos | Real-image Sourcebook has author, license and source URLs; newspaper photos excluded from archive. |
| D-003 | No fabricated climate values | Existing `Math.sin` weather synth data not migrated; climate panel fetches real NASA POWER on demand and shows no numbers when unavailable. |
| D-004 | NASA POWER distinction | `source_type=model_assimilation_gridded`, label never “measured at farm”. |
| D-005 | P02 and P03 not verified | No trial profit displayed as expected farm profit. Data and calendar remain illustrative pending full-text review. |
| D-006 | Rulebook is source of crop text | `api/rules/rotations.yaml` → `scripts/sync_rotations.py` → `web/src/rotations.generated.json`. Risk lines are blocked unless supported by verified page-level source. |
| D-007 | Avoid claim “never grown together on one plot” | Use “paper does not say” if complete article remains ambiguous. |
| D-008 | Privacy | No `localStorage` in this prototype. If added, record retained fields, explicit consent, expiry and data governance before merge. |
| D-009 | 3D current scope | CSS 3D field is manipulable **conceptual geometry**, not a real Nghệ An geo-layer. Needs authorized AOI and data products before map claims. |
| D-010 | Claude connection | Only server-side environment keys; `ANTHROPIC_MODEL` must be explicitly set to an enabled model. No API key shipped. |
| D-011 | Browser voice | Web Speech prototype; device compatibility and Nghệ An dialect accuracy unverified. |
| D-012 | Static checks vs complete build | API tests ran locally. React syntax transpilation tested; full production build/browser E2E blocked by missing npm registry access. No claim of CI green. |
| D-013 | Location | Main geographic study focus: Đô Lương rice land. Other districts including Con Cuông/Thanh Chương are broader culture and geography only. |
| D-014 | Research-first narration | “Lowland and midland Nghệ An” where appropriate; do not replace the study geography with mountain terraces. |
| D-015 | Missing data | No climatological interpolations or silent zero-filling; monthly metrics withheld if incomplete. |
| D-016 | Evidence status | Verified source metadata != retrieved and evaluated source dataset or validated crop recommendation. |

## New runtime packages and licences

Versions in package manifests are **declared / intended**. They have not been installed or build-tested against a live registry in this environment.

| Package | Declared version | License | Purpose |
|---|---|---|---|
| react | ^19.2.0 | MIT | Component/state runtime |
| react-dom | ^19.2.0 | MIT | DOM rendering |
| lucide-react | ^0.468.0 | ISC | Consistent icons |
| vite | ^7.2.0 | MIT | Dev/build system |
| @vitejs/plugin-react | ^5.1.0 | MIT | Vite React transform |
| typescript | ^5.9.0 | Apache-2.0 | Type checking |
| @types/react | ^19.2.0 | MIT | Type declarations |
| @types/react-dom | ^19.2.0 | MIT | Type declarations |
| fastapi | 0.115.12 | MIT | Python API server |
| uvicorn | 0.34.2 | BSD-3-Clause | ASGI server |
| httpx | 0.28.1 | BSD-3-Clause | Async HTTPS calls |
| pydantic | 2.11.4 | MIT | Request/response validation |
| pytest | 8.3.5 | MIT | Tests |

## Offline asset and validation tooling (local only, not web dependencies)

| Package | Used local version | License | Purpose |
|---|---|---|---|
| Pillow | 12.3.0 | HPND | Image crop, grade and export |
| numpy | 2.3.5 | BSD-3-Clause | Efficient color grading |
| PyYAML | 6.0.3 | MIT | Compile audited crop YAML into frontend JSON |
| Playwright | 1.57.0 | Apache-2.0 | Offline static screenshot inspection |

**Release checklist:** confirm current package versions against official registry, review licenses and CVEs, run lockfile install + CI allowlist + dependency scan + build + E2E in connected CI. Deployment remains owned by the team with production credentials and infrastructure.


## Decisions of the 2.0 build (14 Nov 2026)

The starter above was built without the team's sources. The 2.0 build brings in the team's audited rulebook and
data, so some starter decisions are superseded; each supersession is recorded here instead of editing the rows above.

| ID | Decision | Implementation / follow-up |
|---|---|---|
| D-017 | The tested React app from the miaudow repository is the web foundation; the starter app is kept for comparison | `reference/starter-web/` holds the starter's `App.tsx`, styles and previews unchanged. |
| D-018 | One governed data layer | `pipeline/build_canonical.py` writes `data/canonical/*.json`; the API reads it, the web app imports the same files through the Vite alias `@data`. A test proves the hazards, soil, geo and model files equal the team's outputs value for value. |
| D-019 | P-02 and P-03 values are **verified study results** (supersedes D-005) | The team read both papers in full (`data/rules/sources.yaml`: "READ (full text …)"). Values keep their table and page; they are shown as one-plot, one-year 2020–21 results, never as expected income. The full text of P-02 is **not** redistributed: the journal forbids copying without written consent, so it is not in the evidence library. |
| D-020 | `api/rules/rotations.yaml` carries the team rulebook | Risk lines are structured (`text`, `source_id`, `location`, `quote`, `location_precision`); `scripts/sync_rotations.py` rejects a risk line without them or with an unknown source. Plan cards, the officer desk and the copilot read only this text (plus the decision core's own sentences, exported to `decision.json`). |
| D-021 | Studies are named by first author and year in user-facing text | Team decision D-160. Internal ids (P-02, R-P02) stay in code and data. |
| D-022 | No browser storage (supersedes D-008's "if added") | Team rule H14. Farmer answers live only in the URL; settings live in memory; the starting language follows the browser (H16). A browser test asserts localStorage, sessionStorage and cookies stay empty. |
| D-023 | Text floor 17 px everywhere, 44 px targets | Team rules H6, H7. Charts draw at their real pixel width so SVG labels stay 17 px on phones; a browser test walks every visible text node. |
| D-024 | 3D only off the farmer routes, rendered on demand, 2D fallback | Team decision D-155. three.js loads only with the science page; the scene draws a frame only while the camera moves or a column grows; lite mode, reduced motion and missing WebGL show the 2D map. A browser test asserts no 3D code and no canvas on farmer routes. |
| D-025 | Real photographs only with creator, licence and place; team photos without that record are not used | 14 Wikimedia Commons photographs (9 CC0, 5 CC BY-SA) in `assets/photos/PHOTO_MANIFEST.json`; credits with licence and source links in the footer. Concept art stays labelled "Illustration" wherever it appears. Only two photos are in Đô Lương and none in Lưu Sơn. |
| D-026 | Four water situations in the farmer's first step | High field, canal end, often short of water, reliable water (plus "ask the officer"): the decision core's own ids. Old links (`ruong=dry`, `ruong=wet`) still open. |
| D-027 | Second rainfall source kept separate | CHIRPS v3 final monthly (never preliminary), averaged over each POWER cell's Nghệ An pixels, shown beside NASA POWER, never merged. Monthly correlation per cell 0.83–0.96 (diagnostic, not validation). |
| D-028 | Retrieval is hybrid lexical, not neural | BM25 with accent-kept and accent-stripped indexes plus character 3-gram TF-IDF, fused by reciprocal rank; an `Embedder` protocol is ready but no model is used. Abstention: a rule guard (forecasts, prices, ranking) plus a coverage floor (0.45) and an IDF-weighted coverage floor (0.3) set on DEV only. |
| D-029 | The copilot answers deterministically until a key is configured | Without `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` the copilot composes answers from tool results with fixed sentences and says so. With them, Claude runs a manual tool loop with strict tools and a JSON answer schema; every number in its answer must match a tool result (unit change and rounding only), otherwise the answer is discarded for the deterministic one. Server-side refusal fallback (`fallbacks: "default"`) is on for models that support it; set `MIAUDOW_CLAUDE_FALLBACKS=off` to disable. |
| D-030 | Model id is configuration, never a default | `ANTHROPIC_MODEL` must be set explicitly (supersedes nothing; confirms D-010). `api/.env.example` names `claude-opus-5-5` as a valid current id. |
| D-031 | Voice stays browser-native and unclaimed | Web Speech recognition fills the text box for the user to read and correct before sending; speech synthesis reads answers aloud. The WER/CER harness exists (`api/miaudow_api/voice.py`) but no annotated Nghệ An audio does, so no accuracy is claimed (confirms D-011). |
| D-032 | Earthdata products are discovered, not used | HLS, SMAP, GPM IMERG and ECOSTRESS granules over Đô Lương were found through NASA CMR; downloading needs an Earthdata Login, so the catalog lists them as BLOCKED and nothing is shown from them. `pipeline/fetch_nasa_missions.py` downloads once credentials are set. |
| D-033 | Sentinel-2 through the open Earth Search COGs | Windowed reads over the former Đô Lương district, SCL classes 4/5/6 kept, 20 m grid; the double-offset trap of `boa_offset_applied` items is checked per tile. Composites are greenness only; 2020–21 and 2024 are not compared as change. |
| D-034 | The study site is a commune marker, not a field | Lưu Sơn at 18.8964 N, 105.2803 E (Wikidata Q10788283). The commune merged into xã Đô Lương in 2025; the district boundary is geoBoundaries ADM2 (2020 vintage, CC BY 3.0 IGO). |

### Packages of the 2.0 build

Exact pins, each published at least two weeks before use. Runtime packages of the web app are the team-approved
ones (team decision D-157) plus three.js.

| Package | Version | Licence | Purpose | Bundle / performance | Alternatives considered | Security |
|---|---|---|---|---|---|---|
| react, react-dom | 19.3.1 | MIT | UI runtime | shared `react` chunk ~314 kB (≈ 100 kB gzip) | — | none known |
| react-router-dom | 7.18.5 | MIT | hash routing, lazy areas, view transitions | in the main chunk | hand-made router | none known |
| three | 0.186.1 | MIT | WebGL observatory of the real Nghệ An outline and NASA grid | only in the science chunk (≈ 635 kB, ≈ 165 kB gzip); never on farmer routes | CSS 3D (kept as fallback), deck.gl/MapLibre (heavier, needs tiles), Cesium (planned for the globe, Phase 2) | renders local data only |
| @fontsource/be-vietnam-pro, noto-serif-display, jetbrains-mono | 5.3.0 | OFL-1.1 | self-hosted fonts with the Vietnamese subset | only imported weights ship | Google Fonts CDN (rejected: third-party request) | none |
| fastapi | 0.162.5 | MIT | API | server only | — | CORS allow-list from env |
| uvicorn[standard] | 0.54.0 | BSD-3-Clause | ASGI server | server only | — | — |
| pydantic | 2.13.5 | MIT | contracts | server only | — | — |
| httpx | 0.28.1 | BSD-3-Clause | NASA POWER live fetch | server only | — | — |
| numpy, pandas | 2.5.3, 3.0.5 | BSD-3-Clause | climate aggregation | server and pipeline | — | — |
| PyYAML | 6.0.3 | MIT | rulebook sync | build only | — | `safe_load` only |
| anthropic | 2.3.0 | Apache-2.0 (2.x line) | server-side Claude calls | server only; imported only when a key is set | raw HTTP (rejected: the SDK handles retries and typed errors) | key read from env, never logged, never sent to the browser |
| shapely | 2.2.0 | BSD-3-Clause | outline simplification in the canonical build | build only | — | — |
| rasterio | 1.5.2 (with affine 3.0.1) | BSD-3-Clause | CHIRPS and Sentinel-2 windowed COG reads | pipeline only | full downloads (rejected: gigabytes) | reads public COGs over HTTPS |
| pytest, ruff | 9.2.0, 0.17.4 | MIT | tests and lint | dev only | — | — |
| Dev (web): vite 8.3.5, typescript 5.9.3, vitest 5.0.5, jsdom 30.1.3, @playwright/test 1.64.1, @axe-core/playwright 4.14.0, eslint 10.14.0, typescript-eslint 8.72.1, eslint-plugin-react-hooks 7.1.1, @types/three 0.186.0, sharp 0.35.5 | as listed | MIT / Apache-2.0 / MPL-2.0 (axe) / LGPL-3.0 (libvips in sharp) | build, tests, image pipeline | never shipped | — | — |

The starter's "declared / intended" table above (react ^19.2.0, vite ^7.2.0, lucide-react …) is superseded by these
exact pins; lucide-react is not used (the app has its own icon set).
