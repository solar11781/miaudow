import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';

// The browser tests run against the real FastAPI server serving the built app (frontend/dist), so the API, the
// fallback routes and the security headers are the deployed ones. Locally Playwright uses the installed Microsoft
// Edge; CI installs Chromium. Locally set PYTHON to the interpreter that has the requirements, e.g. the repo's venv.
const repo = fileURLToPath(new URL('..', import.meta.url));
const python = process.env.PYTHON ?? 'python';
const baseURL = 'http://127.0.0.1:8000/';
const channel = process.env.CI ? {} : { channel: 'msedge' };

export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: { baseURL, locale: 'vi-VN', ...channel },
  webServer: {
    command: `npm run build && "${python}" -m uvicorn fieldshift.api.app:app --port 8000 --no-access-log --no-server-header`,
    url: `${baseURL}api/health`,
    // GOOGLE_CLIENT_ID stays unset, so sign-in is off: no secret and no database
    env: { FIELDSHIFT_ROOT: repo, PYTHONPATH: `${repo}src` },
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
  projects: [
    { name: 'phone-360', use: { ...devices['Galaxy S9+'], viewport: { width: 360, height: 740 }, ...channel } },
    { name: 'desktop-1440', use: { viewport: { width: 1440, height: 900 }, ...channel } },
  ],
});
