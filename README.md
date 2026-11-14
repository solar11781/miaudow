# Miaudow

## Demo fallback

1. Before the demo, with internet: `cd frontend && npm ci && npm run build:snapshot` (writes `frontend/dist-snapshot/`).
2. Offline: `npm run preview -- --outDir dist-snapshot` (or `python -m http.server 4173 -d dist-snapshot`), then open http://localhost:4173.
3. It answers only the saved choices in `frontend/public/snapshot/index.json`; opening `index.html` by file:// does not work (the browser blocks module scripts).
