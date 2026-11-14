import { test } from '@playwright/test';

// Viewport screenshots with motion on: the 3D grid, a dragged view, and the first screen of key pages.
test('science 3D grid, default and dragged', async ({ page }, info) => {
  // CI's Chromium has no GPU and draws the three.js scene in software: the 360 px run took 31 s of the 45 s limit and
  // the 1440 px run timed out. The scene works under the server CSP locally with and without WebGL (2026-11-14).
  test.slow();
  await page.goto('/#/khoa-hoc');
  const stage = page.getByRole('group', { name: /Lưới NASA POWER/ });
  await stage.scrollIntoViewIfNeeded();
  await page.waitForTimeout(900);
  await stage.screenshot({ path: `review-shots/${info.project.name}-grid3d.png` });
  const box = await stage.boundingBox();
  if (box) {
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2 + 160, box.y + box.height / 2 - 40, { steps: 8 });
    await page.mouse.up();
  }
  await page.getByRole('radio', { name: /Nắng nóng/ }).click();
  await page.waitForTimeout(900);
  await stage.screenshot({ path: `review-shots/${info.project.name}-grid3d-heat.png` });
});

for (const [name, url] of [
  ['home-top', '/#/'],
  ['plans-top', '/#/nong-dan/phuong-an?ruong=dry&nam=2010,2015,2020&uutien=water'],
  ['years-top', '/#/nong-dan/nam?ruong=dry&nam=2010,2015,2020'],
] as const) {
  test(`first screen ${name}`, async ({ page }, info) => {
    await page.goto(url);
    await page.waitForTimeout(1600);
    await page.screenshot({ path: `review-shots/${info.project.name}-${name}.png` });
  });
}
