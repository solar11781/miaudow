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

// roleplay audit 2026-11-16 (farmer on a slow link): the loading line itself waited for the stylesheet, because a
// stylesheet in the head holds back all drawing; the line must be drawn while the stylesheet is still on its way
test('the loading line is drawn before the stylesheet arrives', async ({ page }) => {
  await page.route('**/*.js', (route) => route.abort());
  await page.route('**/*.css', async (route) => {
    await new Promise((done) => setTimeout(done, 3000));
    await route.continue();
  });
  await page.goto('/', { waitUntil: 'commit' });
  const painted = await page.evaluate(
    () =>
      new Promise<number>((resolve) => {
        const read = () => performance.getEntriesByName('first-contentful-paint')[0]?.startTime;
        const tick = () => (read() !== undefined ? resolve(read() as number) : setTimeout(tick, 50));
        tick();
      }),
  );
  expect(painted).toBeLessThan(2000);
  await expect(page.locator('#root')).toContainText('Đang tải trang, xin chờ…');
});
