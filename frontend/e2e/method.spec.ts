import { expect, test } from '@playwright/test';
import { en } from '../src/i18n/en';
import { vi } from '../src/i18n/vi';

// Visual audit of the method page: the result tables were wider than their frame, so the last columns were cut with
// nothing to say so. H6 (no text under 17 px) stays; H10 (no page scroll sideways at 360 px) stays.
const tables = 'main div[role="region"]:has([data-testid^="metric-row-"])';

for (const [lang, path, t] of [
  ['vi-VN', '/#/phuong-phap', vi],
  ['en-GB', '/#/method', en],
] as const) {
  test.describe(`method tables (${lang})`, () => {
    test.use({ locale: lang });

    test('T10 result-tables every column of every result table fits a 1440 px screen', async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(path);
      await expect(page.locator(tables).first()).toBeVisible({ timeout: 30_000 });
      await page.evaluate(() => document.querySelectorAll('details').forEach((d) => (d.open = true)));
      const cut = await page
        .locator(tables)
        .evaluateAll((els) => els.filter((e) => e.scrollWidth > e.clientWidth).map((e) => e.scrollWidth));
      expect(cut).toEqual([]);
      await expect(page.getByText(t.method.scrollHint).first()).toBeHidden();
    });

    test('T10 result-tables on a phone the table scrolls inside its frame and says so', async ({ page }) => {
      await page.setViewportSize({ width: 360, height: 740 });
      await page.goto(path);
      const first = page.locator(tables).first();
      await expect(first).toBeVisible({ timeout: 30_000 });
      await expect(page.getByText(t.method.scrollHint).first()).toBeVisible();
      // a keyboard reaches the scrolling frame (axe scrollable-region-focusable) and the last column scrolls into view
      await expect(first).toHaveAttribute('tabindex', '0');
      await expect(first).toHaveAttribute('aria-label', /.+/);
      await first.locator('thead th').last().scrollIntoViewIfNeeded();
      await expect(first.locator('thead th').last()).toBeInViewport();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
      const small = await page
        .locator(`${tables} :is(th, td)`)
        .evaluateAll((els) => els.map((e) => parseFloat(getComputedStyle(e).fontSize)).filter((px) => px < 17));
      expect(small).toEqual([]);
    });
  });
}
