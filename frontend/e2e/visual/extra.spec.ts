import { test } from '@playwright/test';

test('provenance sheet open', async ({ page }, info) => {
  await page.goto('/#/nong-dan/phuong-an?ruong=dry&nam=2010,2020&uutien=income');
  await page.locator('#the-cc1 [data-value]').first().click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `review-shots/${info.project.name}-sheet.png` });
});

test('dark theme home and assistant', async ({ page }, info) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/#/nong-dan/phuong-an?ruong=dry&nam=2010,2020&uutien=land');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `review-shots/${info.project.name}-dark-plans.png` });
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/#/hoi');
  await page.waitForTimeout(900);
  await page.screenshot({ path: `review-shots/${info.project.name}-assistant-top.png` });
});
