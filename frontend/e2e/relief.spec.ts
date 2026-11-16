import { expect, test, type Page } from '@playwright/test';

// D-138, UI-UX-SPEC section 12: the NASA SRTM relief picture is fetched only when its toggle is switched on.
const PLANS_URL = '/#/nong-dan/phuong-an?ruong=canal_end&nam=2010,2020&uutien=income';

function trackRelief(page: Page): string[] {
  const seen: string[] = [];
  page.on('request', (r) => {
    if (r.url().includes('/media/relief/')) seen.push(r.url());
  });
  return seen;
}

test('T15 relief-lazy the farmer plans page never requests the relief picture', async ({ page }) => {
  const seen = trackRelief(page);
  await page.goto(PLANS_URL);
  await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
  await page.waitForLoadState('networkidle');
  expect(seen).toEqual([]);
});

test('T15 relief-lazy the data room loads the relief picture only after the terrain toggle is switched on', async ({
  page,
}) => {
  const seen = trackRelief(page);
  await page.goto('/#/khoa-hoc');
  const flat = page.getByRole('button', { name: '2D', exact: true });
  const toggle = page.getByRole('button', { name: 'Địa hình (NASA SRTM)' });
  await flat.or(toggle).first().waitFor();
  // with WebGL the page opens in 3D; the layer belongs to the flat map
  if (await flat.isVisible()) await flat.click();
  await toggle.scrollIntoViewIfNeeded();
  await expect(toggle).toHaveAttribute('aria-pressed', 'false');
  expect((await toggle.boundingBox())?.height).toBeGreaterThanOrEqual(44);
  await page.waitForLoadState('networkidle');
  expect(seen).toEqual([]);
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('Chỉ là độ cao. Không cho biết nước tới được đâu.')).toBeVisible();
  await expect.poll(() => seen.length).toBeGreaterThan(0);
  const href = await page.locator('image[href*="nghe-an-relief"]').getAttribute('href');
  const res = await page.request.get(new URL(href ?? '', page.url()).href);
  expect(res.ok()).toBe(true);
  expect((await res.body()).length).toBeLessThan(200_000);
  const drawn = await page.locator('image[href*="nghe-an-relief"]').evaluate(async (el) => {
    const probe = new Image();
    probe.src = el.getAttribute('href') ?? '';
    await probe.decode();
    return probe.naturalWidth;
  });
  expect(drawn).toBe(900);
});

// the shared svg rule max-width: 100% shrank the map's drawing to the width of its frame, so the NASA cells and the
// boundary no longer lined up with the cell buttons laid over them
test('the flat map drawing is as wide as its frame, so cells line up with their buttons', async ({ page }) => {
  await page.goto('/#/khoa-hoc');
  const flat = page.getByRole('button', { name: '2D', exact: true });
  const toggle = page.getByRole('button', { name: 'Địa hình (NASA SRTM)' });
  await flat.or(toggle).first().waitFor();
  if (await flat.isVisible()) await flat.click();
  await toggle.waitFor();
  const box = await page.locator('svg[class*="plane"]').first().boundingBox();
  // viewBox is (W + 80) x (H + 80) = 476.4 x 416 for the 2.5 x 2 degree frame
  expect((box?.width ?? 0) / (box?.height ?? 1)).toBeCloseTo(476.4 / 416, 1);
});
