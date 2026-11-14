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
// a stand-in for https://accounts.google.com/gsi/client: Google's API with a plain button that signs in with a fake
// token, and Google's stylesheet link, as the real script adds one
const FAKE_GSI = `let done = () => {};
window.google = { accounts: { id: {
  initialize(c) { done = c.callback; }, disableAutoSelect() {},
  renderButton(el) {
    const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = 'https://accounts.google.com/gsi/style';
    document.head.append(css);
    const b = document.createElement('button'); b.textContent = 'Google'; b.onclick = () => done({ credential: 'fake' });
    el.append(b);
  },
} } };`;

async function signInOn(page: Page): Promise<string[]> {
  const google: string[] = [];
  await page.route('**/api/account/config', (route) =>
    route.fulfill({ json: { available: true, client_id: 'test.apps.googleusercontent.com' } }),
  );
  await page.route(/^https:\/\/([a-z0-9-]+\.)*google\.com\//, (route) => {
    google.push(route.request().url());
    const css = route.request().url().endsWith('/gsi/style');
    return route.fulfill(
      css ? { contentType: 'text/css', body: '' } : { contentType: 'text/javascript', body: FAKE_GSI },
    );
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
  // the script, then the stylesheet it adds, both allowed by the CSP
  expect(google).toEqual(['https://accounts.google.com/gsi/client', 'https://accounts.google.com/gsi/style']);
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

test('T14 after signing in, the plan cards hold no Google script or stylesheet and the pending save is made', async ({
  page,
}) => {
  await signInOn(page);
  const saved: unknown[] = [];
  await page.route('**/api/account/sign-in', (route) => route.fulfill({ status: 204 }));
  await page.route('**/api/account/saved', (route) => {
    saved.push(route.request().postDataJSON());
    return route.fulfill({ status: 201, json: { id: 1, land: 'canal_end', years: [2010, 2020], priority: 'income' } });
  });
  await page.goto(PLANS_URL);
  await page.getByRole('link', { name: 'Đăng nhập để lưu các câu trả lời này' }).click();
  await page.getByRole('button', { name: 'Tôi đã đọc, đăng nhập bằng Google' }).click();
  await page.getByTestId('google-button').getByRole('button', { name: 'Google' }).click();
  await expect(page.getByText('Đã lưu các câu trả lời này.')).toBeVisible();
  expect(saved).toEqual([{ land: 'canal_end', years: [2010, 2020], priority: 'income' }]);
  await expect(page).toHaveURL(/#\/nong-dan\/phuong-an\?/);
  await expect(page).not.toHaveURL(/luu=1/);
  const left = await page.evaluate(() => ({
    tags: document.querySelectorAll('script[src*="accounts.google.com"], link[href*="accounts.google.com"]').length,
    api: 'google' in window,
  }));
  expect(left).toEqual({ tags: 0, api: false });
});

test('T10 /dang-nhap does not scroll sideways once the Google button is shown', async ({ page }) => {
  await signInOn(page);
  await page.goto('/#/dang-nhap');
  await page.getByRole('button', { name: 'Tôi đã đọc, đăng nhập bằng Google' }).click();
  await expect(page.getByTestId('google-button').getByRole('button', { name: 'Google' })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test('UI-UX-SPEC 12c the saved answers page is reachable from the menu, the footer and the farmer start page', async ({
  page,
}, info) => {
  await signInOn(page);
  await page.goto('/#/nong-dan');
  await page.getByRole('main').getByRole('link', { name: 'Câu trả lời đã lưu' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Câu trả lời đã lưu' })).toBeVisible();
  await page.goto('/#/can-bo');
  await expect(page.locator('footer').getByRole('link', { name: 'Câu trả lời đã lưu' })).toBeVisible();
  if (info.project.name === 'phone-360') {
    await page.getByRole('button', { name: 'Mở menu' }).click();
    await page.getByRole('dialog').getByRole('link', { name: 'Câu trả lời đã lưu' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Câu trả lời đã lưu' })).toBeVisible();
  }
});

test('UI-UX-SPEC 12c sign-in off: no saved answers link anywhere', async ({ page }) => {
  for (const url of ['/#/nong-dan', '/#/can-bo']) {
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('link', { name: 'Câu trả lời đã lưu' })).toHaveCount(0);
  }
});

test('/da-luu with sign-in off says it is not available and offers no sign-in', async ({ page }) => {
  await page.goto('/#/da-luu');
  await expect(page.getByText('Hiện chưa đăng nhập được', { exact: false })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Đăng nhập' })).toHaveCount(0);
});

test('UI-UX-SPEC 12c home shows the saved answers link under the main button while sign-in is on', async ({ page }) => {
  await signInOn(page);
  await page.goto('/#/');
  const main = page.getByRole('link', { name: 'Tìm hiểu ruộng nhà mình' }).first(); // the hero's, the first on the page
  const saved = page.getByRole('main').getByRole('link', { name: 'Câu trả lời đã lưu' });
  await expect(saved).toBeVisible();
  const [a, b] = [await main.boundingBox(), await saved.boundingBox()];
  expect(b && a && b.y >= a.y + a.height - 1).toBe(true);
  expect(b && b.height >= 44 && b.width >= 44).toBe(true);
});

test('UI-UX-SPEC 12c a saved set cannot be saved twice, and new answers can be saved again', async ({ page }) => {
  await signInOn(page);
  const saved: unknown[] = [];
  await page.route('**/api/account/sign-in', (route) => route.fulfill({ status: 204 }));
  await page.route('**/api/account/saved', (route) => {
    saved.push(route.request().postDataJSON());
    return route.fulfill({
      status: 201,
      json: { id: saved.length, land: 'canal_end', years: [2010], priority: 'income' },
    });
  });
  await page.goto(PLANS_URL);
  await page.getByRole('link', { name: 'Đăng nhập để lưu các câu trả lời này' }).click();
  await page.getByRole('button', { name: 'Tôi đã đọc, đăng nhập bằng Google' }).click();
  await page.getByTestId('google-button').getByRole('button', { name: 'Google' }).click();
  await expect(page.getByRole('button', { name: 'Đã lưu ✓' })).toBeDisabled();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole('link', { name: /Quay lại/ }).click();
  await page.getByRole('radio', { name: /Tiết kiệm nước/ }).click();
  await page.getByRole('link', { name: 'Xem các cách trồng' }).click();
  await page.getByRole('button', { name: 'Lưu các câu trả lời này' }).click();
  await expect(page.getByRole('button', { name: 'Đã lưu ✓' })).toBeDisabled();
  expect(saved).toHaveLength(2);
});

test('UI-UX-SPEC 12c the delete confirm buttons are not in the main button style', async ({ page }) => {
  await signInOn(page);
  await page.route('**/api/account/sign-in', (route) => route.fulfill({ status: 204 }));
  await page.route('**/api/account/saved', (route) =>
    route.fulfill({ json: { saved: [{ id: 1, land: 'canal_end', years: [2010], priority: 'income' }] } }),
  );
  await page.goto('/#/dang-nhap');
  await page.getByRole('button', { name: 'Tôi đã đọc, đăng nhập bằng Google' }).click();
  await page.getByTestId('google-button').getByRole('button', { name: 'Google' }).click();
  await page.getByRole('button', { name: /^Xóa: / }).click();
  await page.getByRole('button', { name: 'Xóa tài khoản và mọi câu trả lời đã lưu' }).click();
  for (const name of ['Có, xóa', 'Có, xóa hết']) {
    await expect(page.getByRole('button', { name, exact: true })).not.toHaveClass(/_primary_/);
  }
});
