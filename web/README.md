# MIAUDOW web app

React 19 + Vite 8 + TypeScript (strict). How to run, test and build it, and how it reads the canonical data and the
API, is in the project README (`../README.md`) and `../docs/07-ARCHITECTURE-AND-CONTRACTS.md`.

```bash
npm ci
npm run dev            # http://localhost:5173, proxies /api to http://127.0.0.1:8000 (MIAUDOW_API to change)
npm run build          # type check + production bundle in dist/
npx vitest run         # unit tests
npx playwright test e2e/journey.spec.ts   # browser journeys and WCAG 2.2 AA (uses the installed Microsoft Edge)
node pipeline/build_media.mjs             # photographs and concept art from ../assets
```
