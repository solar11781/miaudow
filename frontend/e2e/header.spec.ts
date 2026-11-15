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
