import { expect, test } from '@playwright/test';

// The offline demo build (npm run build:snapshot; 04-TECH-DESIGN section 9 runbook, D-150), run by
// playwright.snapshot.config.ts against a static server: no backend exists, so any /api call would be a live answer.
const SAVED = '/nong-dan/phuong-an?ruong=water_short&nam=2003,2009,2013,2020&uutien=water';
const ROUTES = [
  '/',
  '/nong-dan',
  '/nong-dan/ruong',
  '/nong-dan/nam',
  '/nong-dan/uu-tien',
  SAVED,
  '/can-bo',
  '/khoa-hoc',
  '/phuong-phap',
  '/dai-quan-sat',
  '/bang-chung',
  '/tro-ly',
  '/khong-co-trang-nay',
];

test('D-150 every route of the offline copy shows the offline notice and calls no api', async ({ page }) => {
  const calls: string[] = [];
  page.on('request', (r) => {
    if (new URL(r.url()).pathname.startsWith('/api/')) calls.push(r.url());
  });
  for (const route of ROUTES) {
    // a fresh page load per route, so each route's own requests finish before the check
    await page.goto('about:blank');
    await page.goto(`/#${route}`, { waitUntil: 'networkidle' });
    await expect(page.getByTestId('snapshot-notice'), route).toContainText('Bản lưu ngoại tuyến');
  }
  expect(calls).toEqual([]);
});

test('D-150 saved choices open the six saved plan cards', async ({ page }) => {
  await page.goto(`/#${SAVED}`);
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await expect(page.locator('#the-cc1 [data-highlighted="true"]')).toHaveCount(1);
});

test('D-150 a choice outside the saved set lists the saved choices and shows no plan card', async ({ page }) => {
  await page.goto('/#/nong-dan/phuong-an?ruong=water_short&nam=2005&uutien=income');
  await expect(page.getByTestId('snapshot-miss')).toContainText('2003, 2009, 2013, 2020');
  await expect(page.locator('article[id^="the-"]')).toHaveCount(0);
});
