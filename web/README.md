# Miaudow · Đồng lúa Nghệ An (React + Vite edition)

Decision support for households on water-short rice land in Nghệ An, Vietnam. Farmers compare six ways of farming
that were tested on this land type, next to 30 years of NASA weather read with Vietnam's official risk-level rules.
Every number opens its source. The app never ranks plans and never forecasts.

Three experiences share one design system:

| Route | For | What it does |
|---|---|---|
| `#/` | everyone | Editorial home: the problem, the four steps, the honest model result, Vietnam's farming heritage |
| `#/nong-dan` … `#/nong-dan/phuong-an` | farmers | Four tap-only steps; answers live in the URL (shareable, survive reload) |
| `#/can-bo` | extension officers | Evidence matrix, study scope, data lineage, how to talk about it, gaps, source registry |
| `#/khoa-hoc` | judges, researchers | 3D NASA POWER grid on the real Nghệ An outline, 30-year timeline, rice history, model skill, gates |
| `#/hoi` | everyone | Evidence assistant: answers only from checked passages and computed data, abstains otherwise |

## Run

```bash
npm install
npm run dev          # http://localhost:5173
npm run build        # type check + production bundle in dist/
npm run preview      # serves dist/ on http://localhost:4173
npm test             # unit and component tests (Vitest)
npm run lint         # ESLint (typescript-eslint strict, react-hooks)
npm run e2e          # journeys + WCAG 2.2 AA checks (Playwright, uses the installed Microsoft Edge)
npm run e2e:shots    # review screenshots and the field-phone performance check (written to review-shots/)
```

Node 22 or newer. Playwright drives the installed Edge (`channel: 'msedge'`), so no browser download is needed.

## Where every number comes from

Evidence kinds are never mixed silently; each sourced number carries a kind badge and a red source seal:
**data → derived (Miaudow's arithmetic) → study / standard → model → assistant text**.

| Shown | Kind | Source |
|---|---|---|
| Share of Nghệ An farmland meeting a risk rule, per year and per crop | derived | NASA POWER daily data for the 5 farmland-weighted cells, 1990–2024, thresholds of QĐ 18/2021/QĐ-TTg (Art. 44, 47, 48, 53) applied with the team's `fieldshift.features.hazards.cell_rules`, weighted by NASA MODIS farmland |
| Measured amounts in the 3D grid (wettest day, hot days, cold days, dry months) | derived | same NASA POWER series, over the P-02 field time |
| NASA soil wetness per crop | derived (model value) | POWER `GWETROOT` (MERRA-2), farmland-weighted, against 1991–2020 |
| Rice yield against normal, Nghệ An | data | NSO yields; normal = mean of the 3 previous years (E-010); from the team's `risk_table.json` |
| Winter-rice out-of-sample predictions 2016–2024 | model | primary test E-012 (`metrics.json`, `gates.json`, frozen at commit ea7a60c); spring predictions are hidden because the spring model did not beat its no-weather twin |
| Crop dates, profit, cost, price | study | P-02 (VAAS 2023, Tables 1, 5, 9, 4, 8, 12, 13); P-03 for the second description of current practice |
| Yearly plan profit | derived | sum of the P-02 per-crop profits |
| Irrigation amounts | standard | TCVN 8641:2011; FAO Training Manual 3, Table 14 |
| Province outline | data | geoBoundaries gbOpen VNM ADM1 (public domain per its metadata), simplified |

Rebuild the generated data from the repository root (the root provides the `fieldshift` package, the cached POWER
files, the committed farmland weights and the model artifacts):

```bash
PYTHONPATH=src .venv/Scripts/python web/pipeline/fetch_nghe_an.py      # NASA POWER, 10 requests, cached in data/raw
PYTHONPATH=src .venv/Scripts/python scripts/fetch_recorded.py data/raw/boundaries/geoBoundaries-VNM-ADM1_simplified.geojson
PYTHONPATH=src .venv/Scripts/python web/pipeline/build_data.py web/src/data/generated
cd web && npm run photos -- <folder with the team photos>               # responsive WebP + blur placeholders
```

`build_data.py` stops on any missing value instead of filling it.

## The AI core, honestly

No API key or language-model provider is configured, and a key must never sit in a Vite bundle. The assistant
(`src/features/ai`) is therefore a grounded, deterministic pipeline:

1. **Normalise** Vietnamese (accents kept when the question has them, so “máy bay” never matches “máy móc”; stripped
   for questions typed without accents and for English) plus farmer synonyms (“lời”, “tiền” → profit).
2. **Intent**: a year → look up the computed shares and NSO rice anomaly; a crop → P-02 table; “what should I grow” →
   a refusal to rank with each plan's evidence; “tomorrow / next season” → the no-forecast answer.
3. **Retrieve** with BM25 over an evidence base built from the sources above (plan and model passages are generated
   from the data, so they cannot drift).
4. **Abstain** unless the best passage has both a score ≥ 4.5 and covers ≥ 50% of the question's terms.

`src/features/ai/languageModel.ts` defines the integration point (`ExplanationModel`): a server-side model may only
rephrase the passages it is given. The default is `notConnected`, and the UI says so.

Tests (`ai.test.ts`): retrieval relevance for Vietnamese with and without accents and for English, exact numeric
consistency of year answers with the data, refusal to rank, forecast handling, abstention on unrelated questions.

## Architecture

```
src/app/            router (hash), layout, header, footer, settings (language, lite mode, theme)
src/design-system/  icons, buttons, photo with blur-up, scroll reveal
src/styles/         tokens (palette, type, space, elevation, data colours, light/dark), global CSS
src/domain/         pure logic: plans (P-02), calendar, hazards, rice, farmer URL state, sources, provenance
src/data/           typed access to generated JSON; photo catalogue
src/features/       home, farmer, officer, science (3D grid), charts, provenance (sheet, seal), ai
src/i18n/           vi.ts (primary) and en.ts; the type makes a missing English key a build error
pipeline/           data and photo build scripts
e2e/                journeys + axe checks; e2e/visual: review shots and performance profile
archive/            the original single-file HTML prototype
```

Design system: palette from the rice field (forest, young rice, harvest gold, terracotta, bamboo, mist, canal water,
rice paper, ink) as semantic tokens with light and dark values; Noto Serif Display for editorial headings, Be Vietnam
Pro for the interface, JetBrains Mono for data, all self-hosted with the Vietnamese subsets. The 3D grid is plain CSS
3D transforms (11 cells do not justify a WebGL library); it falls back to 2D in lite mode and under reduced motion.

## Verified results (14 Nov 2026, this machine)

- `tsc -b`, `eslint .`: clean. Vitest: 35 tests passed.
- Playwright (Edge, 360 × 740 and 1440 × 900): farmer journey, provenance sheet with Escape and focus return, card
  share link, language switch, assistant, no horizontal scroll, and axe WCAG 2.2 AA on six routes: all passed
  (the clipboard check runs on desktop only).
- Field-phone profile (4× CPU, 1.6 Mbps / 150 ms, cache off, median of 3 cold loads): LCP 1.86 s home, 1.75 s land
  step, 2.04 s plans, 2.03 s science; CLS ≤ 0.063. Measured locally, not on a real handset.

## Photographs

`pipeline/build_photos.mjs` uses 11 of the 22 team-supplied photos. Excluded: a duplicate, one photo of a child, and
nine photos that carry other photographers' or a newspaper's watermarks (watermarks are never cropped away). Mountain
terraces appear only in the heritage section and are labelled “northern mountains, not Nghệ An”. The team confirmed
permission on 14 Nov 2026; confirm the rights of each photo before public submission.

## Not done / needs the team

- This folder sits next to `frontend/` on a draft branch. Moving it into the app goes through the queue and `/task` gate; the UI spec currently forbids
  3D, transitions, web fonts and this palette; the team must update the spec and the dependency allow-list first.
- No language model is connected (see above).
- Real-handset testing and a cognitive walkthrough with farmers have not been done.
