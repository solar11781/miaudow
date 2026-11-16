import { expect, test } from '@playwright/test';

// visual audit 2026-11-16: the source button under the grid table started left of the table's text
test('the source under the grid table starts where the table text starts', async ({ page }) => {
  await page.goto('/#/khoa-hoc');
  const wrap = page.locator('[class*="tableWrap"]');
  await expect(wrap.locator('tbody tr')).toHaveCount(5);
  const left = await wrap.evaluate((w) => {
    const textLeft = (el: Element | null) => {
      const range = document.createRange();
      range.selectNodeContents(el as Element);
      return range.getBoundingClientRect().left;
    };
    return {
      cell: textLeft(w.querySelector('tbody th')),
      source: textLeft(w.querySelector('button [class*="figure"]')),
    };
  });
  expect(Math.abs(left.source - left.cell)).toBeLessThanOrEqual(1);
});
