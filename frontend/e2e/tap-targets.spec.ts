import { expect, test, type Locator } from '@playwright/test';

// T7 (UI-UX-SPEC H7): the small controls tonight's 360 px audit measured below 44 x 44 px
async function tooSmall(controls: Locator) {
  await expect(controls.first()).toBeVisible({ timeout: 30_000 });
  return controls.evaluateAll((els) =>
    els
      .filter((e) => e.getClientRects().length > 0)
      .map((e) => ({ name: (e.textContent ?? '').trim(), box: e.getBoundingClientRect() }))
      .filter(({ box }) => box.width < 44 || box.height < 44)
      .map(({ name, box }) => `${name.slice(0, 40)}: ${box.width} x ${box.height}`),
  );
}

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
});

test('T7 tap-targets the cost and price toggles on the officer page are at least 44 x 44 px', async ({ page }) => {
  await page.goto('/#/can-bo');
  // the evidence table sits in a fold; open it so its toggles show
  await page.locator('main details[class*="matrixDetails"] > summary').click();
  expect(await tooSmall(page.locator('main details[class*="costs"] > summary'))).toEqual([]);
});

test('T7 tap-targets the season tabs on the science page are at least 44 x 44 px', async ({ page }) => {
  await page.goto('/#/khoa-hoc');
  expect(await tooSmall(page.locator('main [role="radio"]'))).toEqual([]);
});

test('T7 tap-targets the photo credit and licence links on the evidence page are at least 44 x 44 px', async ({
  page,
}) => {
  await page.goto('/#/bang-chung');
  expect(await tooSmall(page.locator('section[aria-labelledby="ev-photos"] a'))).toEqual([]);
});

test('T7 tap-targets the globe data attribution link is at least 44 x 44 px', async ({ page }) => {
  await page.goto('/#/dai-quan-sat?canh=vietnam');
  expect(await tooSmall(page.locator('main a.cesium-credit-expand-link'))).toEqual([]);
});
