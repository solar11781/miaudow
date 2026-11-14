# Field Shift web app

Member B's React 19 + Vite 8 + TypeScript (strict) app (D-166). The farmer flow and the method page read our API
through `src/api.ts`; the extras read B's canonical data files in `data/canonical`.

```bash
npm ci
npm run dev            # http://localhost:5173, proxies /api to http://127.0.0.1:8000 (MIAUDOW_API to change)
npm run build          # type check + production bundle in dist/
npx vitest run         # unit tests
npx playwright test e2e/journey.spec.ts   # browser journeys and WCAG 2.2 AA (uses the installed Microsoft Edge)
```
