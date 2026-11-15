import { expect, test } from '@playwright/test';

// audit F3, D-187: on a slow phone the page stayed blank until the script arrived; index.html now shows a line
test('the page shows a loading line, in Vietnamese and English, before its script runs', async ({ page }) => {
  await page.route('**/*.js', (route) => route.abort());
  await page.goto('/');
  const root = page.locator('#root');
  await expect(root).toContainText('Đang tải trang, xin chờ…');
  await expect(root).toContainText('Loading the page, please wait…');
});

test('the app replaces the loading line, and the server CSP blocks nothing', async ({ page }) => {
  const blocked: string[] = [];
  page.on('console', (m) => {
    if (/Content Security Policy|Refused/i.test(m.text())) blocked.push(m.text());
  });
  await page.goto('/');
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.locator('#root')).not.toContainText('Đang tải trang, xin chờ…');
  expect(blocked).toEqual([]);
});
