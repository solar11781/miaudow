import { expect, test } from '@playwright/test';

// D-174: every page also has an English path that opens the same page in English; the Vietnamese paths stay the main
// ones, and the answers after "?" in the fragment are kept exactly.
const ANSWERS = '?ruong=canal_end&nam=2010,2020&uutien=income';
const ENGLISH = [
  '/#/home',
  '/#/farmer',
  '/#/farmer/field',
  '/#/farmer/years?ruong=canal_end',
  '/#/farmer/priority?ruong=canal_end&nam=2010',
  `/#/farmer/plans${ANSWERS}`,
  '/#/officer',
  '/#/science',
  '/#/method',
  '/#/observatory',
  '/#/evidence',
  '/#/assistant',
  '/#/sign-in',
  '/#/saved',
];

test('T33 an English path opens the plan cards in English with the answers kept', async ({ page }) => {
  await page.goto(`/#/farmer/plans${ANSWERS}`);
  await expect(page.getByRole('heading', { level: 1, name: 'Compare 6 ways of farming' })).toBeVisible();
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  // links inside the app use the English paths and keep the answers
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole('link', { name: /Back/ }).first().click();
  await expect(page).toHaveURL(/#\/farmer\/priority\?ruong=canal_end&nam=2010%2C2020&uutien=income$/);
  await expect(page.getByRole('heading', { level: 1, name: 'What matters most to your family?' })).toBeVisible();
});

test('T33 the language switch opens the same page under the other path with the answers kept', async ({ page }) => {
  await page.goto(`/#/nong-dan/phuong-an${ANSWERS}`);
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await page.getByRole('button', { name: /Switch to English/ }).click();
  await expect(page).toHaveURL(new RegExp(`#/farmer/plans\\${ANSWERS}$`));
  await expect(page.getByRole('heading', { level: 1, name: 'Compare 6 ways of farming' })).toBeVisible();
  await page.getByRole('button', { name: /Chuyển sang tiếng Việt/ }).click();
  await expect(page).toHaveURL(new RegExp(`#/nong-dan/phuong-an\\${ANSWERS}$`));
  await expect(page.getByRole('heading', { level: 1, name: 'So sánh 6 cách trồng' })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'vi');
});

test('T33 every English path opens its page in English', async ({ page }) => {
  for (const url of ENGLISH) {
    await page.goto(url);
    await expect(page.getByRole('heading', { level: 1 }).first(), url).toBeVisible();
    await expect(page.getByText('This page was not found.'), url).toHaveCount(0);
    await expect(page.locator('html'), url).toHaveAttribute('lang', 'en');
  }
});

test('T14 English paths: no third-party request and nothing stored', async ({ page, baseURL }) => {
  const own = new URL(baseURL ?? 'http://127.0.0.1:8000/').origin;
  const outside: string[] = [];
  const local = (u: URL) => u.hostname.endsWith('.kaspersky-labs.com'); // a team laptop's antivirus, not the app
  page.on('request', (r) => {
    const u = new URL(r.url());
    if (/^https?:$/.test(u.protocol) && u.origin !== own && !local(u)) outside.push(r.url());
  });
  // /observatory carries the D-167 NASA exception, as /dai-quan-sat does
  for (const url of ENGLISH.filter((u) => u !== '/#/observatory')) {
    await page.goto(url);
    await page.waitForLoadState('networkidle');
  }
  expect(outside).toEqual([]);
  const stored = await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie.length]);
  expect(stored).toEqual([0, 0, 0]);
});

test('T32 the Vietnamese paths stay as they are in Vietnamese', async ({ page }) => {
  await page.goto(`/#/nong-dan/phuong-an${ANSWERS}`);
  await expect(page.getByRole('heading', { level: 1, name: 'So sánh 6 cách trồng' })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page
    .getByRole('link', { name: /Quay lại/ })
    .first()
    .click();
  await expect(page).toHaveURL(/#\/nong-dan\/uu-tien\?/);
});
