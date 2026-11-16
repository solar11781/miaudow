import { expect, test } from '@playwright/test';

// member A, 2026-11-15: the footer keeps the brand, the reminder, the privacy and code links and the team line;
// no copy of the menu, no citation, no build time, never Space Apps (UI-UX-SPEC 12b)
test('the footer holds the brand, the reminder, two links and the team line, nothing else', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto('/');
  const footer = page.locator('footer');
  const links = footer.getByRole('link');
  await expect(links).toHaveCount(2);
  await expect(footer.getByRole('link', { name: 'Quyền riêng tư', exact: true })).toBeVisible();
  await expect(footer.getByRole('link', { name: 'Mã nguồn trên GitHub', exact: true })).toBeVisible();
  const text = (await footer.textContent()) ?? '';
  expect(text).toMatch(/không thay thế/);
  expect(text).toMatch(/Nhóm Miau/);
  expect(text).not.toMatch(/Space Apps|Trịnh Đức Toàn|Dữ liệu tạo lúc|Ảnh và giấy phép/);
  for (const box of await links.evaluateAll((els) => els.map((e) => e.getBoundingClientRect())))
    expect(Math.min(box.width, box.height)).toBeGreaterThanOrEqual(44);
});

// roleplay audit 2026-11-16: the notice is one page, Vietnamese first; the English site opens it at its English part
test('the English footer opens the privacy notice at its English part', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto('/#/home');
  const link = page.locator('footer').getByRole('link', { name: 'Privacy', exact: true });
  await expect(link).toHaveAttribute('href', '/quyen-rieng-tu#en');
  await link.click();
  await expect(page.getByRole('heading', { level: 2 })).toBeInViewport();
  await page.goto('/#/');
  await expect(page.locator('footer').getByRole('link', { name: 'Quyền riêng tư', exact: true })).toHaveAttribute(
    'href',
    '/quyen-rieng-tu',
  );
});

// the CC BY and CC BY-SA licences ask for each photo's author and licence; they moved to the sources page
test('the evidence page lists every photograph with its licence', async ({ page }) => {
  await page.goto('/#/bang-chung');
  const credits = page.locator('section[aria-labelledby="ev-photos"]');
  await expect(credits.getByRole('heading', { name: 'Ảnh và giấy phép' })).toBeVisible();
  await expect(credits.getByRole('link', { name: /^Giấy phép: / }).first()).toBeVisible();
});

// visual audit 2026-11-16: on a short page the footer ended above the bottom of the window, a pale band under it
for (const path of ['/#/da-luu', '/#/dang-nhap'])
  test(`the footer of the short page ${path} reaches the bottom of the window`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const footer = await page.locator('footer').evaluate((el) => el.getBoundingClientRect().bottom + window.scrollY);
    const sizes = await page.evaluate(() => ({ window: window.innerHeight, height: document.body.scrollHeight }));
    expect(footer).toBeGreaterThanOrEqual(sizes.window - 1);
    // the footer is the end of the page: nothing under it
    expect(footer).toBeGreaterThanOrEqual(sizes.height - 1);
  });
