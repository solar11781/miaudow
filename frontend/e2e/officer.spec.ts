import { expect, test } from '@playwright/test';

// roleplay audit 2026-11-16 (extension officer, laptop): the desk's left column ended early and left about a screen
// of blank space beside the longer right column. The shorter column now stays in view to the end of the panel.
test('the desk never shows an empty column beside the other one on a laptop', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto('/#/can-bo');
  const panel = page.locator('#desk-panel');
  await expect(panel).toBeVisible();
  const columns = panel.locator(':scope > *');
  await expect(columns).toHaveCount(2);
  // scroll until the panel's last 200 px are at the bottom of the window: both columns must still reach there
  await panel.evaluate((el) => {
    const end = el.getBoundingClientRect().bottom + window.scrollY;
    window.scrollTo(0, end - window.innerHeight - 200);
  });
  const bottoms = await columns.evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().bottom)));
  for (const bottom of bottoms) expect(bottom).toBeGreaterThanOrEqual(768 - 48);
});
