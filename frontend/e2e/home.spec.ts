import { expect, test } from '@playwright/test';

// D-187 (roleplay audit F6): a farmer opening a shared home link sees, without scrolling, what the app is and the way in
test('D-187 the first screen holds the start button and the "what this is" box', async ({ page }) => {
  await page.goto('/#/');
  const start = page.getByRole('main').getByRole('link', { name: 'Tìm hiểu ruộng nhà mình' }).first();
  const about = page.getByRole('region', { name: 'Ứng dụng này làm gì?' });
  await expect(start).toBeInViewport({ ratio: 1 });
  await expect(about).toBeInViewport({ ratio: 1 });
  await expect(about).toContainText('Không dự báo mùa tới');
  await expect(about).toContainText('Không chọn thay gia đình bạn');
});
