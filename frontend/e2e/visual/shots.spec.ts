import { test } from '@playwright/test';

// Full-page screenshots of every area, for visual review (written to test-results/shots).
// Reduced motion is emulated so scroll reveals and fades do not hide content in a single full-page capture.
const PAGES = [
  ['home', '/#/'],
  ['farmer-start', '/#/nong-dan'],
  ['farmer-land', '/#/nong-dan/ruong?ruong=dry&nam=2010,2015,2020'],
  ['farmer-years', '/#/nong-dan/nam?ruong=dry&nam=2010,2015,2020'],
  ['farmer-prio', '/#/nong-dan/uu-tien?ruong=dry&nam=2010,2015,2020&uutien=water'],
  ['farmer-plans', '/#/nong-dan/phuong-an?ruong=dry&nam=2010,2015,2020&uutien=water'],
  ['officer', '/#/can-bo'],
  ['science', '/#/khoa-hoc'],
  ['assistant', '/#/hoi'],
] as const;

for (const [name, url] of PAGES) {
  test(`screenshot ${name}`, async ({ page }, info) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(url);
    await page.evaluate(async () => {
      for (let y = 0; y < document.documentElement.scrollHeight; y += 500) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 50));
      }
      document.querySelectorAll('img[loading="lazy"]').forEach((img) => img.setAttribute('loading', 'eager'));
      window.scrollTo(0, 0);
    });
    await page
      .waitForFunction(() => [...document.images].every((i) => i.complete), undefined, { timeout: 30_000 })
      .catch(() => undefined);
    await page.waitForTimeout(500);
    await page.screenshot({ path: `review-shots/${info.project.name}-${name}.png`, fullPage: true });
  });
}
