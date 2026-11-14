import { expect, test } from '@playwright/test';

// The FastAPI server sets the content security policy (src/fieldshift/api/app.py); the tests run against it.
test('T1 the observatory, outside the farmer routes, draws its 3D globe under the server CSP', async ({ page }) => {
  const blocked: string[] = [];
  page.on('console', (m) => {
    if (/Content Security Policy|Refused/i.test(m.text())) blocked.push(m.text());
  });
  page.on('pageerror', (e) => blocked.push(e.message));
  const res = await page.goto('/#/dai-quan-sat?canh=nghe-an');
  expect(res?.headers()['content-security-policy']).toContain("frame-ancestors 'none'");
  await expect(page.locator('canvas').first()).toBeVisible({ timeout: 30_000 });
  expect(blocked).toEqual([]);
});
