import { expect, test } from '@playwright/test';

// the header squeezed the start button on wide screens until its arrow covered the word (member A, 2026-11-15)
test('the start button keeps its arrow clear of its words on a wide screen', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('/');
  const cta = page.locator('header a[class*="cta"]');
  await expect(cta).toBeVisible();
  const gap = await cta.evaluate((a) => {
    const text = [...a.querySelectorAll('*'), a]
      .flatMap((e) => [...e.childNodes])
      .find((n) => n.nodeType === 3 && n.textContent?.trim());
    const range = document.createRange();
    range.selectNodeContents(text as Node);
    const icon = a.querySelector('svg') as SVGElement;
    return icon.getBoundingClientRect().left - range.getBoundingClientRect().right;
  });
  expect(gap).toBeGreaterThanOrEqual(4);
});

// at 360 px the wordmark hides and the logo link shrank to the 36 px mark; spec hard rule: targets at least 44 x 44
for (const route of ['/', '/#/nong-dan']) {
  test(`the logo link is at least 44 x 44 px on a 360 px phone (${route})`, async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto(route);
    const brand = page.locator('header a[class*="brand"]');
    await expect(brand).toBeVisible();
    const box = await brand.boundingBox();
    expect(box?.width).toBeGreaterThanOrEqual(44);
    expect(box?.height).toBeGreaterThanOrEqual(44);
  });
}

test.describe('on a phone in light mode', () => {
  test.use({ colorScheme: 'light' });
  // audit F10, D-187: the theme Auto stayed dark on a phone set to light mode
  test('the theme Auto shows the light page', async ({ page }) => {
    await page.goto('/#/nong-dan/ruong');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    const [r, g, b] = (bg.match(/\d+/g) ?? []).map(Number);
    expect(Math.min(r, g, b)).toBeGreaterThan(200);
  });
});
