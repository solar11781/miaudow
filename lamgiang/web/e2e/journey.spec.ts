import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const PLANS_URL = '/#/nong-dan/phuong-an?ruong=canal_end&nam=2010,2020&uutien=income';

async function apiUp(page: Page): Promise<boolean> {
  const res = await page.request.get('/api/health').catch(() => null);
  return !!res && res.ok();
}

test('a farmer completes the four steps by tapping only, and nothing is stored in the browser', async ({ page }) => {
  await page.goto('/#/nong-dan');
  await page.getByRole('link', { name: 'Bắt đầu', exact: false }).last().click();
  await expect(page.getByRole('heading', { level: 1, name: 'Ruộng nhà mình thế nào?' })).toBeVisible();
  await expect(page.getByRole('radio')).toHaveCount(5);
  await page.getByRole('radio', { name: /Ruộng ở cuối kênh/ }).click();
  await expect(page.getByRole('radio', { name: /Ruộng ở cuối kênh/ })).toHaveAttribute('aria-checked', 'true');
  await page.getByRole('link', { name: 'Tiếp tục' }).click();

  await expect(page.getByRole('heading', { level: 1, name: 'Những năm trước ra sao?' })).toBeVisible();
  await page.getByRole('button', { name: '2005', exact: true }).click();
  await expect(page.getByRole('heading', { level: 2, name: '2005' })).toBeVisible();
  await page.getByRole('link', { name: 'Tiếp tục' }).click();

  await page.getByRole('radio', { name: /Tiết kiệm nước/ }).click();
  await page.getByRole('link', { name: 'Xem các cách trồng' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'So sánh 6 cách trồng' })).toBeVisible();
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await expect(page).toHaveURL(/ruong=canal_end/);
  await expect(page).toHaveURL(/uutien=water/);
  // the card relates the study land to this farmer's answer, from the decision core
  await expect(page.locator('#the-cc1')).toContainText('ruộng ở cuối kênh');

  // UI-UX-SPEC H14: no localStorage, sessionStorage or cookies
  const stored = await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie.length]);
  expect(stored).toEqual([0, 0, 0]);

  // answers survive a reload (URL state) and the back link keeps them
  await page.reload();
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole('link', { name: /Quay lại/ }).click();
  await expect(page.getByRole('radio', { name: /Tiết kiệm nước/ })).toHaveAttribute('aria-checked', 'true');
});

test('links shared before the four water situations still open', async ({ page }) => {
  await page.goto('/#/nong-dan/phuong-an?ruong=dry&nam=2010');
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
});

test('the farmer route loads no WebGL and no 3D code', async ({ page }) => {
  const scripts: string[] = [];
  page.on('request', (r) => { if (r.resourceType() === 'script') scripts.push(r.url()); });
  await page.goto(PLANS_URL);
  await page.waitForLoadState('networkidle');
  expect(scripts.some((u) => /three|observatory|Observatory/i.test(u))).toBe(false);
  expect(await page.locator('canvas').count()).toBe(0);
});

test('every sourced number opens its provenance sheet and Escape closes it', async ({ page }) => {
  await page.goto(PLANS_URL);
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
  await page.goto(PLANS_URL);
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

test('one year flows from the science page to the copilot', async ({ page }) => {
  await page.goto('/#/khoa-hoc?nam=2020');
  await expect(page.getByRole('heading', { level: 2, name: /Một năm, ba cách nhìn · 2020/ })).toBeVisible();
  await page.getByRole('link', { name: 'Hỏi trợ lý về năm 2020' }).click();
  await expect(page).toHaveURL(/tro-ly/);
  await expect(page.locator('ol[aria-live] > li').first()).toContainText('2020', { timeout: 30_000 });
});

test('the copilot answers from data and abstains otherwise', async ({ page }) => {
  await page.goto('/#/tro-ly');
  await page.getByRole('button', { name: 'Năm 2010 có hạn không?' }).click();
  await expect(page.locator('ol[aria-live] > li').first()).toContainText('Năm 2010', { timeout: 30_000 });
  await page.getByLabel('Câu hỏi của bạn').fill('công thức nấu phở');
  await page.getByRole('button', { name: 'Hỏi', exact: true }).click();
  await expect(page.locator('ol[aria-live] > li').last()).toContainText(/Chưa đủ dữ liệu|chưa có bằng chứng/, { timeout: 30_000 });
});

test('with the API running, the farmer question returns the six plans in study order and never a ranking', async ({ page }) => {
  test.skip(!(await apiUp(page)), 'the MIAUDOW API is not running');
  await page.goto('/#/tro-ly');
  await page.getByRole('button', { name: /cuối kênh/ }).first().click();
  const answer = page.locator('ol[aria-live] > li').first();
  await expect(answer).toContainText('không chọn cách trồng thay gia đình bạn', { timeout: 30_000 });
  await expect(answer.getByRole('link', { name: /Xem thẻ so sánh/ })).toHaveCount(6);
  await expect(answer).not.toContainText('tốt nhất');
});

for (const url of ['/#/', '/#/nong-dan/ruong', PLANS_URL, '/#/can-bo', '/#/khoa-hoc', '/#/bang-chung', '/#/tro-ly']) {
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
  for (const url of ['/#/', PLANS_URL, '/#/can-bo', '/#/khoa-hoc', '/#/bang-chung', '/#/tro-ly']) {
    await page.goto(url);
    await page.waitForTimeout(400);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, url).toBeLessThanOrEqual(0);
  }
});

test('no visible text is smaller than 17 px (H6)', async ({ page }) => {
  for (const url of ['/#/', PLANS_URL, '/#/can-bo', '/#/bang-chung', '/#/tro-ly']) {
    await page.goto(url);
    await page.reload();
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const small = await page.evaluate(() => {
      const out: string[] = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const el = n.parentElement;
        if (!el || !n.textContent?.trim()) continue;
        if (el.closest('.visually-hidden, [aria-hidden="true"], svg, title, script, style, option')) continue;
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') continue;
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        if (parseFloat(cs.fontSize) < 16.9) out.push(`${cs.fontSize} ${n.textContent.trim().slice(0, 30)}`);
      }
      return out.slice(0, 8);
    });
    expect(small, url).toEqual([]);
  }
});
