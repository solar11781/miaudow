import { expect, test } from '@playwright/test';

// step 2 put each hazard name in a 26 px icon column, so "Mưa lớn" wrapped one word per line (final audit, 2026-11-15)
test('each hazard name on a year card has room for its words on a 360 px phone', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto('/#/nong-dan/nam?ruong=water_short&nam=2010');
  const names = page.locator('#year-card-2010 li[data-rule] > span:first-child');
  await expect(names.first()).toBeVisible();
  for (const box of await names.evaluateAll((els) => els.map((e) => e.getBoundingClientRect().width))) {
    expect(box).toBeGreaterThanOrEqual(80);
  }
});
