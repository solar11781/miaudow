import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/#/');
  await page.evaluate(() => window.localStorage.clear());
});

test('a farmer completes the four steps by tapping only', async ({ page }) => {
  await page.goto('/#/nong-dan');
  await page.getByRole('link', { name: 'Bắt đầu', exact: false }).last().click();
  await expect(page.getByRole('heading', { level: 1, name: 'Ruộng nhà mình thế nào?' })).toBeVisible();
  await page.getByRole('radio', { name: /Ruộng cao, cuối kênh/ }).click();
  await expect(page.getByRole('radio', { name: /Ruộng cao, cuối kênh/ })).toHaveAttribute('aria-checked', 'true');
  await page.getByRole('link', { name: 'Tiếp tục' }).click();

  await expect(page.getByRole('heading', { level: 1, name: 'Những năm trước ra sao?' })).toBeVisible();
  await page.getByRole('button', { name: '2005', exact: true }).click();
  await expect(page.getByRole('heading', { level: 2, name: '2005' })).toBeVisible();
  await page.getByRole('link', { name: 'Tiếp tục' }).click();

  await page.getByRole('radio', { name: /Tiết kiệm nước/ }).click();
  await page.getByRole('link', { name: 'Xem các cách trồng' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'So sánh 6 cách trồng' })).toBeVisible();
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await expect(page).toHaveURL(/ruong=dry/);
  await expect(page).toHaveURL(/uutien=water/);

  // answers survive a reload (URL state) and the back link keeps them
  await page.reload();
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole('link', { name: /Quay lại/ }).click();
  await expect(page.getByRole('radio', { name: /Tiết kiệm nước/ })).toHaveAttribute('aria-checked', 'true');
});

test('every sourced number opens its provenance sheet and Escape closes it', async ({ page }) => {
  await page.goto('/#/nong-dan/phuong-an?ruong=dry&nam=2010,2020&uutien=income');
  const firstValue = page.locator('#the-cc1 [data-value]').first();
  await firstValue.click();
  const sheet = page.getByRole('dialog');
  await expect(sheet).toBeVisible();
  await expect(sheet).toContainText('Có thể không đúng khi');
  await page.keyboard.press('Escape');
  await expect(sheet).toBeHidden();
  await expect(firstValue).toBeFocused();
});

test('share copies the link of that exact card', async ({ page, context, browserName }, info) => {
  test.skip(info.project.name !== 'desktop-1440' || browserName !== 'chromium', 'clipboard check on desktop only');
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/#/nong-dan/phuong-an?ruong=dry&nam=2010,2020&uutien=income');
  await page.locator('#the-cc3').getByRole('button', { name: 'Gửi thẻ này' }).click();
  await expect(page.locator('#the-cc3')).toContainText('Đã chép liên kết của thẻ này');
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toContain('#/nong-dan/phuong-an?');
  expect(copied).toContain('the=cc3');
  await page.goto(copied);
  await expect(page.locator('#the-cc3')).toBeInViewport();
});

test('language switch changes the whole interface', async ({ page }) => {
  await page.goto('/#/khoa-hoc');
  await expect(page.getByRole('heading', { level: 1, name: 'Nghệ An qua 30 mùa vụ' })).toBeVisible();
  const lang = page.getByRole('button', { name: 'Switch to English' });
  if (await lang.isVisible()) await lang.click();
  else { await page.getByRole('button', { name: 'Mở menu' }).click(); await page.getByRole('dialog').getByRole('button', { name: 'Switch to English' }).click(); }
  await expect(page.getByRole('heading', { level: 1, name: 'Nghệ An across 30 seasons' })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('the evidence assistant answers from data and abstains otherwise', async ({ page }) => {
  await page.goto('/#/hoi');
  await page.getByRole('button', { name: 'Năm 2010 có hạn không?' }).click();
  await expect(page.locator('ol[aria-live] li').first()).toContainText('Năm 2010');
  await page.getByLabel('Câu hỏi của bạn').fill('công thức nấu phở');
  await page.getByRole('button', { name: 'Hỏi', exact: true }).click();
  await expect(page.locator('ol[aria-live] > li').last()).toContainText('chưa có bằng chứng');
});

for (const url of ['/#/', '/#/nong-dan/ruong', '/#/nong-dan/phuong-an?ruong=dry&nam=2010,2020&uutien=water', '/#/can-bo', '/#/khoa-hoc', '/#/hoi']) {
  test(`no WCAG 2.2 AA violations on ${url}`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    const result = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0]).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
    const summary = result.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join(' | ')}`);
    expect(summary).toEqual([]);
  });
}

test('the page never scrolls sideways', async ({ page }) => {
  for (const url of ['/#/', '/#/nong-dan/phuong-an?ruong=dry&nam=2010,2020', '/#/can-bo', '/#/khoa-hoc', '/#/hoi']) {
    await page.goto(url);
    await page.waitForTimeout(400);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, url).toBeLessThanOrEqual(0);
  }
});
