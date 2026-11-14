import { expect, test } from '@playwright/test';

// The content security policy is set by the FastAPI server (src/fieldshift/api/app.py), not by vite preview, so this
// file runs only against that server: FIELDSHIFT_URL=http://127.0.0.1:8000 npx playwright test e2e/csp.spec.ts
const server = process.env.FIELDSHIFT_URL;

test.describe('under the server CSP', () => {
  test.skip(!server, 'FIELDSHIFT_URL is not set: start uvicorn fieldshift.api.app:app with the built frontend');

  test('the observatory draws its 3D globe', async ({ page }) => {
    const blocked: string[] = [];
    page.on('console', (m) => {
      if (/Content Security Policy|Refused/i.test(m.text())) blocked.push(m.text());
    });
    page.on('pageerror', (e) => blocked.push(e.message));
    await page.goto(`${server ?? ''}/#/dai-quan-sat?canh=nghe-an`);
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 30_000 });
    expect(blocked).toEqual([]);
  });
});
