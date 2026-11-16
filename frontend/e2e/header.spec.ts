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

// at 360 px the wordmark hides and the logo link shrank to the 36 px mark; spec hard rule: targets at least 44 x 44
for (const route of ['/', '/#/nong-dan']) {
  test(`the logo link is at least 44 x 44 px on a 360 px phone (${route})`, async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto(route);
    const brand = page.locator('header a[class*="brand"]');
    await expect(brand).toBeVisible();
    const box = await brand.boundingBox();
    expect(box?.width).toBeGreaterThanOrEqual(44);
    expect(box?.height).toBeGreaterThanOrEqual(44);
  });
}

// T7, D-187: every header control, the open menu sheet included, keeps a 44 x 44 px target on a 360 px phone
for (const route of ['/', '/#/nong-dan/ruong']) {
  test(`T7 tap-targets every header control is at least 44 x 44 px at 360 px (${route})`, async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto(route);
    await expect(page.locator('header a[class*="brand"]')).toBeVisible();
    const menu = page.locator('header button[class*="menuBtn"]');
    if (await menu.isVisible()) await menu.click();
    const small = await page.getByRole('banner').evaluate((h) =>
      [...h.querySelectorAll('a, button')]
        .filter((e) => e.getClientRects().length > 0)
        .map((e) => ({ name: e.getAttribute('aria-label') ?? e.textContent?.trim(), box: e.getBoundingClientRect() }))
        .filter(({ box }) => box.width < 44 || box.height < 44)
        .map(({ name, box }) => `${name}: ${box.width} x ${box.height}`),
    );
    expect(small).toEqual([]);
  });
}

// audit F10, D-187: the switch only stops motion, and the theme button showed a bare icon
test('the farmer header names its motion switch and shows the theme it is on at 360 px', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto('/#/nong-dan/ruong');
  const header = page.getByRole('banner');
  await expect(header.getByRole('switch', { name: 'Giảm chuyển động' })).toBeVisible();
  await expect(header.getByRole('button', { name: 'Giao diện: Tự động' })).toHaveText('Tự động');
});

test.describe('on a phone in light mode', () => {
  test.use({ colorScheme: 'light' });
  // audit F10, D-187: the theme Auto stayed dark on a phone set to light mode
  test('the theme Auto shows the light page', async ({ page }) => {
    await page.goto('/#/nong-dan/ruong');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    const [r, g, b] = (bg.match(/\d+/g) ?? []).map(Number);
    expect(Math.min(r, g, b)).toBeGreaterThan(200);
  });
});

// member A, 2026-11-16: in Vietnamese the bar ran off a 1600 px screen. The bar's column stops growing at 1280 px, so
// every control must stay inside that column at every width, in both languages, on the site and the farmer header.
const WIDTHS = [
  360, 480, 600, 759, 760, 770, 800, 859, 860, 1024, 1259, 1260, 1270, 1280, 1319, 1320, 1366, 1440, 1536, 1600, 1680,
  1920, 2560,
];
for (const route of ['/#/', '/#/nong-dan/ruong', '/#/home', '/#/farmer/field']) {
  test(`the header's controls stay inside its column at every width (${route})`, async ({ page }, info) => {
    test.skip(info.project.name !== 'desktop-1440', 'the test sets every width itself');
    await page.goto(route);
    await expect(page.locator('header a[class*="brand"]')).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    const over: string[] = [];
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 800 });
      const past = await page.locator('header div[class*="bar"]').evaluate((bar) => {
        const right = bar.getBoundingClientRect().right - parseFloat(getComputedStyle(bar).paddingRight);
        const edges = [...bar.querySelectorAll('a, button')]
          .filter((e) => e.getClientRects().length > 0)
          .map((e) => e.getBoundingClientRect().right - right);
        return Math.max(0, ...edges);
      });
      if (past > 0.5) over.push(`${width} px: ${Math.round(past)} px past the column`);
    }
    expect(over).toEqual([]);
  });
}

// the language button showed a bare globe between 1260 and 1500 px
test('the language button shows the other language next to its icon on a laptop', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop-1440', 'a laptop width');
  await page.setViewportSize({ width: 1440, height: 800 });
  await page.goto('/#/');
  const text = page.getByRole('banner').getByRole('button', { name: 'EN · Switch to English' }).locator('span');
  await expect(text).toHaveText('EN');
  expect((await text.boundingBox())?.width).toBeGreaterThan(10);
});

test.describe('in light mode', () => {
  test.use({ colorScheme: 'light' });
  // the light theme darkened the ivory wordmark on every header, so on the dark headers it could not be seen
  test('the wordmark is darkened only on the light header bar', async ({ page }, info) => {
    test.skip(info.project.name !== 'desktop-1440', 'the phone bar hides the wordmark; its menu is checked below');
    // the old page's header stays up while the next page loads, so wait for the header this page gives
    const filter = async (route: string, light: boolean) => {
      await page.goto(route);
      await expect(page.locator('header[class*="paper"]')).toHaveCount(light ? 1 : 0);
      const mark = page.locator('header div[class*="bar"] img[alt="Miaudow"]');
      await expect(mark).toBeVisible();
      return mark.evaluate((img) => getComputedStyle(img).filter);
    };
    expect(await filter('/#/dai-quan-sat', true)).toContain('brightness'); // paper header
    expect(await filter('/#/khoa-hoc', false)).toBe('none'); // forest header
    expect(await filter('/#/', false)).toBe('none'); // over the photograph
  });

  test('the wordmark stays light in the dark menu sheet', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto('/#/dai-quan-sat');
    await page.locator('header button[class*="menuBtn"]').click();
    const mark = page.getByRole('dialog').locator('img[alt="Miaudow"]');
    await expect(mark).toBeVisible();
    expect(await mark.evaluate((img) => getComputedStyle(img).filter)).toBe('none');
  });
});
