# MIAUDOW — Lam Giang Golden Heritage 2.0

**A tangible art-direction + React/Vite source + constrained climate/AI API starter**, based on the user's screenshots and `Miaudow Đồng Lúa.html`.

## Deliverables

- `web/` — React + Vite + TypeScript UI for **Home / Farmer / Officer / Science / Evidence / Vietnamese Copilot**; highly cinematic home, accessible mobile farmer journey, CSS-3D scientific illustration and real on-demand climate chart API contract.
- `api/` — FastAPI with NASA POWER live daily fetch + monthly aggregation, source facts and optional server-side Claude API integration.
- `assets/concept-original/` — 16 original AI-generated **concept illustrations**, NOT photos of actual Nghệ An.
- `assets/concept-graded/` — the same 16 with a coherent Golden Heritage grade.
- `assets/previews/` — visual contact sheet and static preview screenshots.
- `assets/references/REAL_NGHE_AN_SOURCEBOOK.csv` — 21 real image references with source URLs, photographer/license where verified. Real photos were **not embedded** because download access was blocked and editorial images require rights clearance.
- `docs/` — screenshot audit, design system, data/AI blueprint, real image sourcebook, decision log, Claude execution prompt.
- `preview/` — offline static art-direction samples (not the React app).
- `reference/original-prototype.html` — original user file retained for comparison.

## Run the front end (in an environment with npm registry access)

```bash
cd web
npm install
npm run dev
# production checks:
npm run check
npm run build
```

## Run the backend

```bash
cd api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# optionally export ANTHROPIC_API_KEY and ANTHROPIC_MODEL securely
uvicorn main:app --reload --host 127.0.0.1 --port 8000
pytest tests -q
```

`web/vite.config.ts` proxies `/api` to localhost port 8000. No full production ingestion service is included. Without NASA network connectivity, science says **no data loaded**; without Claude credentials, the API returns *cited source facts only* for eligible questions. These are deliberate safeguards.

## Regenerate crop fixtures after editing the YAML rulebook

```bash
python scripts/sync_rotations.py
```

Requires PyYAML on the authoring machine; it is not a runtime web dependency. The generator rejects crop-risk lines without verified source references and page details. Frontend data currently shows tentative calendars only.

## Asset authenticity

The illustrations depict imagined agricultural scenery. **Do not use them with captions claiming actual Đô Lương photo documentation.** Use the `REAL_NGHE_AN_SOURCEBOOK.csv` as a rights-cleared acquisition guide; no unpublished editorial photos are included. See `docs/03-PHOTOGRAPHY-AND-ART-LICENSES.md`.

## Verification completed in this environment

- 16 distinct concept images cropped, graded and exported in two variants.
- Static home/science previews rendered with Chromium using injected local CSS/images; desktop and mobile screenshots saved.
- 4 Python tests passed for missingness, leap-year aggregation and retrieval abstention.
- TypeScript JSX source transpiled with zero syntax diagnostics using the locally installed TypeScript tool.
- **Not completed**: npm dependency install, full React production build, real NASA POWER request, actual Claude API request, real tile-based geospatial data, E2E usability and security testing.

## Important methodology caveat

The original prototype contains simulated climate hazard cells and demonstration model results. They were **not copied into live-data cards**. On the new interface all unverified agronomic claims are clearly marked as needing primary-source verification. The exact district-level study boundaries and original trial tables are necessary before using crop comparisons for actionable advice.
