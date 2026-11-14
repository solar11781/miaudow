import { expect, test, type Page } from '@playwright/test';

// UI-UX-SPEC §12c and H14: the optional Google sign-in. The test server runs with sign-in off (playwright.config.ts);
// the "on" tests answer /api/account/config in the browser and stand in for Google's script, so Google is never called.
const PLANS_URL = '/#/nong-dan/phuong-an?ruong=canal_end&nam=2010,2020&uutien=income';
const OTHER_ROUTES = [
  '/#/',
  '/#/nong-dan',
  '/#/nong-dan/ruong',
  '/#/nong-dan/nam?ruong=canal_end&nam=2010',
  '/#/nong-dan/uu-tien?ruong=canal_end&nam=2010',
  PLANS_URL,
  '/#/phuong-phap',
  '/#/can-bo',
  '/#/khoa-hoc',
  '/#/bang-chung',
  '/#/tro-ly',
];
// a stand-in for https://accounts.google.com/gsi/client: Google's API with a plain button
const FAKE_GSI = `window.google = { accounts: { id: {
  initialize() {}, disableAutoSelect() {},
  renderButton(el) { const b = document.createElement('button'); b.textContent = 'Google'; el.append(b); },
} } };`;

async function signInOn(page: Page): Promise<string[]> {
  const google: string[] = [];
  await page.route('**/api/account/config', (route) =>
    route.fulfill({ json: { available: true, client_id: 'test.apps.googleusercontent.com' } }),
  );
  await page.route(/^https:\/\/([a-z0-9-]+\.)*google\.com\//, (route) => {
    google.push(route.request().url());
    return route.fulfill({ contentType: 'text/javascript', body: FAKE_GSI });
  });
  return google;
}

test('T14 sign-in off: the sign-in page says it is not available', async ({ page }) => {
  await page.goto('/#/dang-nhap');
  await expect(page.getByText('Hiện chưa đăng nhập được', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Tôi đã đọc, đăng nhập bằng Google' })).toHaveCount(0);
});

test('T14 sign-in off: the plan cards show no save button', async ({ page }) => {
  await page.goto(PLANS_URL);
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('button', { name: 'Lưu các câu trả lời này' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Đăng nhập để lưu các câu trả lời này' })).toHaveCount(0);
});

test('T14 sign-in on: no route but /dang-nhap and /da-luu asks google.com for anything', async ({ page }) => {
  const google = await signInOn(page);
  for (const url of [...OTHER_ROUTES, '/#/da-luu']) {
    await page.goto(url);
    await page.waitForLoadState('networkidle');
  }
  // the save button is there while sign-in is on, and it only links to the sign-in page
  await page.goto(PLANS_URL);
  await expect(page.getByRole('link', { name: 'Đăng nhập để lưu các câu trả lời này' })).toBeVisible();
  expect(google).toEqual([]);
  // UI-UX-SPEC H14: no localStorage, sessionStorage or cookies
  const stored = await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie.length]);
  expect(stored).toEqual([0, 0, 0]);
});

test('T14 sign-in on: /dang-nhap shows the notice first and loads Google only after the tap, under the CSP', async ({
  page,
}) => {
  const google = await signInOn(page);
  const blocked: string[] = [];
  page.on('console', (m) => {
    if (/Content Security Policy|Refused/i.test(m.text())) blocked.push(m.text());
  });
  await page.goto('/#/dang-nhap');
  await expect(page.getByRole('heading', { name: 'Đọc trước khi đăng nhập' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Đọc đầy đủ về quyền riêng tư' })).toHaveAttribute(
    'href',
    '/quyen-rieng-tu',
  );
  await page.waitForLoadState('networkidle');
  expect(google).toEqual([]);
  await page.getByRole('button', { name: 'Tôi đã đọc, đăng nhập bằng Google' }).click();
  await expect(page.getByTestId('google-button').getByRole('button', { name: 'Google' })).toBeVisible();
  expect(google).toEqual(['https://accounts.google.com/gsi/client']);
  expect(blocked).toEqual([]);
});

test('H6 H7 the sign-in pages use 17 px text and 44 px taps', async ({ page }) => {
  await signInOn(page);
  for (const url of ['/#/dang-nhap', '/#/da-luu', PLANS_URL]) {
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    const found = await page.evaluate(() => {
      const main = document.querySelector('main');
      if (!main) return ['no main'];
      const out: string[] = [];
      for (const el of main.querySelectorAll<HTMLElement>('a, button')) {
        const r = el.getBoundingClientRect();
        if (!r.width || el.closest('article')) continue; // the plan cards have their own tests
        if (r.height < 43.99 || r.width < 43.99) out.push(`tap ${r.width}x${r.height} ${el.textContent?.trim()}`);
      }
      for (const el of main.querySelectorAll<HTMLElement>('h1, h2, p, li, a, button')) {
        if (el.closest('article') || !el.getBoundingClientRect().width) continue;
        const px = parseFloat(getComputedStyle(el).fontSize);
        if (px < 16.995) out.push(`text ${px}px ${el.textContent?.trim().slice(0, 30)}`);
      }
      return out;
    });
    expect(found, url).toEqual([]);
  }
});
