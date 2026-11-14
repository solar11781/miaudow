import { defineConfig, devices } from '@playwright/test';

// Uses the Microsoft Edge already installed on the machine (no browser download). Start `npm run preview` first,
// or let Playwright start it.
export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: { baseURL: 'http://localhost:4173/', channel: 'msedge', locale: 'vi-VN' },
  webServer: { command: 'npm run preview', url: 'http://localhost:4173/', reuseExistingServer: true, timeout: 60_000 },
  projects: [
    { name: 'phone-360', use: { ...devices['Galaxy S9+'], viewport: { width: 360, height: 740 }, channel: 'msedge' } },
    { name: 'desktop-1440', use: { viewport: { width: 1440, height: 900 }, channel: 'msedge' } },
  ],
});
