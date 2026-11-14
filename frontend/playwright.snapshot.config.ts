import { defineConfig, devices } from '@playwright/test';

// Browser tests of the offline demo build (e2e/snapshot.spec.ts): a plain static server, no backend, like the laptop
// on demo day. Locally Playwright uses the installed Microsoft Edge; CI installs Chromium.
const baseURL = 'http://127.0.0.1:4174/';
const channel = process.env.CI ? {} : { channel: 'msedge' };

export default defineConfig({
  testDir: './e2e',
  testMatch: 'snapshot.spec.ts',
  timeout: 45_000,
  workers: 1,
  reporter: [['list']],
  use: { baseURL, locale: 'vi-VN', ...channel },
  webServer: {
    command:
      'npm run build:snapshot && npx vite preview --outDir dist-snapshot --host 127.0.0.1 --port 4174 --strictPort',
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
  projects: [
    { name: 'phone-360', use: { ...devices['Galaxy S9+'], viewport: { width: 360, height: 740 }, ...channel } },
  ],
});
