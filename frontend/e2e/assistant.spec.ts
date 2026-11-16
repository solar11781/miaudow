import { expect, test } from '@playwright/test';

// member A, 2026-11-16: the question box was pinned to the bottom of the window, so while the page scrolled it floated
// over the example questions and the mode switch of its own panel
test('the question box sits at the end of its panel and never covers the example questions', async ({ page }) => {
  await page.goto('/#/tro-ly');
  const form = page.getByRole('main').locator('form');
  const examples = page.getByLabel('Câu hỏi mẫu');
  await expect(form).toBeVisible();
  await expect(examples).toBeVisible();
  for (const y of [0, 200, 400, 600]) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    const [f, e] = await Promise.all([form.boundingBox(), examples.boundingBox()]);
    expect(f && e && f.y >= e.y + e.height, `scrolled ${y} px`).toBe(true);
  }
});
