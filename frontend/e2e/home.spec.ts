import { expect, test } from '@playwright/test';

// D-187 (roleplay audit F6): a farmer opening a shared home link sees, without scrolling, what the app is and the way in
test('D-187 the first screen holds the start button and the "what this is" box', async ({ page }) => {
  await page.goto('/#/');
  const start = page.getByRole('main').getByRole('link', { name: 'Tìm hiểu ruộng nhà mình' }).first();
  const about = page.getByRole('region', { name: 'Ứng dụng này làm gì?' });
  await expect(start).toBeInViewport({ ratio: 1 });
  await expect(about).toBeInViewport({ ratio: 1 });
  await expect(about).toContainText('Không dự báo vụ tới');
  await expect(about).toContainText('Không chọn thay gia đình bạn');
});

// visual audit 2026-11-16: the satellite section's heading and paragraph ran past the page column to the window edge
test('the satellite section keeps its picture and its text inside the page column', async ({ page }) => {
  await page.goto('/#/');
  const section = page.locator('section', { has: page.locator('#obs-title') });
  await section.scrollIntoViewIfNeeded();
  // the page column: the box inside the padding of any .container (the footer has one on every page)
  const column = await page
    .locator('footer .container')
    .first()
    .evaluate((el) => {
      const box = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return { left: box.left + parseFloat(style.paddingLeft), right: box.right - parseFloat(style.paddingRight) };
    });
  for (const part of [section.locator('figure'), section.locator('h2'), section.locator('p.lead')]) {
    const box = await part.boundingBox();
    expect(box).not.toBeNull();
    if (!box) continue;
    expect(box.x).toBeGreaterThanOrEqual(column.left - 1);
    expect(box.x + box.width).toBeLessThanOrEqual(column.right + 1);
  }
});
