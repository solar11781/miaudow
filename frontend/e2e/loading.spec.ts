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

// the stylesheet is dark until the app's script sets the theme, so on a phone set to light the loading line must not
// follow the phone's setting on its own: its dark text would sit on the stylesheet's dark page
test('the loading line stays readable on a light-mode phone after the stylesheet has arrived', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.route('**/*.js', (route) => route.abort());
  await page.goto('/');
  await page.waitForFunction(() => document.styleSheets.length > 1);
  const ratios = await page.evaluate(() => {
    const channel = (v: number) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
    const luminance = (colour: string) => {
      const [r = 0, g = 0, b = 0] = (colour.match(/[\d.]+/g) ?? []).map((n) => channel(Number(n) / 255));
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const page = luminance(getComputedStyle(document.body).backgroundColor);
    return [...document.querySelectorAll('.boot, .boot span')].map((el) => {
      const text = luminance(getComputedStyle(el).color);
      return (Math.max(text, page) + 0.05) / (Math.min(text, page) + 0.05);
    });
  });
  expect(ratios).toHaveLength(2);
  for (const ratio of ratios) expect(ratio).toBeGreaterThanOrEqual(4.5);
});
