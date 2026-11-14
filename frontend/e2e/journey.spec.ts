import AxeBuilder from '@axe-core/playwright';
import { readFileSync } from 'node:fs';
import { expect, test, type Page } from '@playwright/test';

const PLANS_URL = '/#/nong-dan/phuong-an?ruong=canal_end&nam=2010,2020&uutien=income';

// member B's copilot backend; our backend has no copilot route (D-166), and then its health has no copilot entry
async function copilotUp(page: Page): Promise<boolean> {
  const res = await page.request.get('/api/health').catch(() => null);
  return !!res && res.ok() && 'copilot' in ((await res.json()) as Record<string, unknown>);
}

test('T4 T14 a farmer completes the four steps by tapping only, and nothing is stored in the browser', async ({
  page,
}) => {
  await page.goto('/#/nong-dan');
  await page.getByRole('link', { name: 'Bắt đầu', exact: false }).last().click();
  await expect(page.getByRole('heading', { level: 1, name: 'Ruộng nhà mình thế nào?' })).toBeVisible();
  await expect(page.getByRole('radio')).toHaveCount(5);
  await page.getByRole('radio', { name: /Ruộng ở cuối kênh/ }).click();
  await expect(page.getByRole('radio', { name: /Ruộng ở cuối kênh/ })).toHaveAttribute('aria-checked', 'true');
  await page.getByRole('link', { name: 'Tiếp tục' }).click();

  await expect(page.getByRole('heading', { level: 1, name: 'Những năm trước ra sao?' })).toBeVisible();
  await page.getByRole('button', { name: '2005', exact: true }).click();
  await expect(page.getByRole('heading', { level: 2, name: 'Năm 2005' })).toBeVisible();
  await page.getByRole('link', { name: 'Tiếp tục' }).click();

  await page.getByRole('radio', { name: /Tiết kiệm nước/ }).click();
  await page.getByRole('link', { name: 'Xem các cách trồng' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'So sánh 6 cách trồng' })).toBeVisible();
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await expect(page).toHaveURL(/ruong=canal_end/);
  await expect(page).toHaveURL(/uutien=water/);
  // the cards come from POST /api/compare; the chosen priority highlights one row per card
  await expect(page.locator('#the-cc1 [data-highlighted="true"]')).toHaveCount(1);

  // UI-UX-SPEC H14: no localStorage, sessionStorage or cookies
  const stored = await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie.length]);
  expect(stored).toEqual([0, 0, 0]);

  // answers survive a reload (URL state) and the back link keeps them
  await page.reload();
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole('link', { name: /Quay lại/ }).click();
  await expect(page.getByRole('radio', { name: /Tiết kiệm nước/ })).toHaveAttribute('aria-checked', 'true');
});

test('T31 links shared before the four water situations still open', async ({ page }) => {
  await page.goto('/#/nong-dan/phuong-an?ruong=dry&nam=2010&uutien=income');
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
});

test('T1 the farmer route loads no WebGL and no 3D code', async ({ page }) => {
  const scripts: string[] = [];
  page.on('request', (r) => {
    if (r.resourceType() === 'script') scripts.push(r.url());
  });
  await page.goto(PLANS_URL);
  await page.waitForLoadState('networkidle');
  expect(scripts.some((u) => /three|observatory|Observatory|cesium|globe|EarthPage/i.test(u))).toBe(false);
  expect(await page.locator('canvas').count()).toBe(0);
});

test('T5 every sourced number opens its provenance sheet and Escape closes it', async ({ page }) => {
  await page.goto(PLANS_URL);
  const firstValue = page.locator('#the-cc1 [data-value]').first();
  await firstValue.click();
  const sheet = page.getByRole('dialog');
  await expect(sheet).toBeVisible();
  // the source facts of the API response (UI-UX-SPEC section 10)
  await expect(sheet).toContainText('Nơi và năm');
  await page.keyboard.press('Escape');
  await expect(sheet).toBeHidden();
  await expect(firstValue).toBeFocused();
});

test('T31 share copies the link of that exact card', async ({ page, context, browserName }, info) => {
  test.skip(info.project.name !== 'desktop-1440' || browserName !== 'chromium', 'clipboard check on desktop only');
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto(PLANS_URL);
  await page.locator('#the-cc3').getByRole('button', { name: 'Gửi thẻ này' }).click();
  await expect(page.locator('#the-cc3')).toContainText('Đã chép liên kết của thẻ này');
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toContain('#/nong-dan/phuong-an?');
  expect(copied).toContain('the=cc3');
  await page.goto(copied);
  await expect(page.locator('#the-cc3')).toBeInViewport();
});

test('T33 language switch changes the whole interface', async ({ page }) => {
  await page.goto('/#/khoa-hoc');
  await expect(page.getByRole('heading', { level: 1, name: 'Nghệ An qua 30 mùa vụ' })).toBeVisible();
  const lang = page.getByRole('button', { name: 'Switch to English' });
  if (await lang.isVisible()) await lang.click();
  else {
    await page.getByRole('button', { name: 'Mở menu' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Switch to English' }).click();
  }
  await expect(page.getByRole('heading', { level: 1, name: 'Nghệ An across 30 seasons' })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('T31 one year flows from the science page to the copilot', async ({ page }) => {
  await page.goto('/#/khoa-hoc?nam=2020');
  await expect(page.getByRole('heading', { level: 2, name: /Một năm, ba cách nhìn · 2020/ })).toBeVisible();
  await page.getByRole('link', { name: 'Hỏi trợ lý về năm 2020' }).click();
  await expect(page).toHaveURL(/tro-ly/);
  await expect(page.locator('ol[aria-live] > li').first()).toContainText('2020', { timeout: 30_000 });
});

// Annual rain of one NASA POWER cell, read straight from the canonical file the app is built from.
function canonicalRain(cell: string, year: number): number {
  const climate = JSON.parse(readFileSync(new URL('../data/canonical/climate.json', import.meta.url), 'utf-8'));
  return climate.series.cells[cell][String(year)].annual_rain_mm;
}

test('T1 T31 the Earth observatory walks its eight scenes, keeps them in the link and shows the canonical numbers', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/#/dai-quan-sat');
  const rail = page.getByRole('navigation', { name: 'Các cảnh của chuyến đi' });
  await expect(rail.locator('ol button')).toHaveCount(8);
  await expect(rail.getByRole('button', { name: 'Tự chạy' })).toHaveCount(0);
  await rail.getByRole('button', { name: 'Cảnh sau' }).click();
  await expect(page).toHaveURL(/canh=earth/);
  await rail.getByRole('button', { name: /Vệ tinh/ }).click();
  await expect(page.getByRole('heading', { level: 3, name: 'Terra (MODIS)' })).toBeVisible();
  await expect(page.getByText('Chưa tải được').first()).toBeVisible();
  await rail.getByRole('button', { name: /Phân tích/ }).click();
  await expect(page).toHaveURL(/canh=analysis/);
  await page.getByRole('combobox', { name: 'Năm' }).selectOption('2010');
  const cellRadio = page.getByRole('radio', { name: '18.5°N 105.625°E' });
  await cellRadio.click();
  await expect(cellRadio).toBeChecked();
  const rain = Math.round(canonicalRain('18.5_105.625', 2010)).toLocaleString('vi-VN');
  await expect(page.getByRole('button', { name: `Mưa cả năm · 2010 · 18.5_105.625: ${rain} mm` })).toBeVisible();
  await expect(page).toHaveURL(/nam=2010/);
  await expect(page).toHaveURL(/o=18\.5_105\.625/);
  // with reduced motion the globe is off and the page says so
  expect(await page.locator('canvas').count()).toBe(0);
  await expect(page.getByText(/giảm chuyển động/)).toBeVisible();
});

test('T31 the observatory insight hands the year to the copilot', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/#/dai-quan-sat?canh=insight&nam=2020');
  await expect(page.getByText('Năm 2020, ô này', { exact: false })).toBeVisible();
  await page.getByRole('link', { name: 'Hỏi trợ lý về năm này' }).click();
  await expect(page).toHaveURL(/tro-ly/);
  await expect(page.locator('ol[aria-live] > li').first()).toContainText('2020', { timeout: 30_000 });
});

test('T14 NASA Eyes opens in a dialog and "back to Earth" lands on Nghệ An', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/#/dai-quan-sat?canh=cosmos');
  await page.getByRole('button', { name: 'Sao Hỏa' }).click();
  const dialog = page.getByRole('dialog', { name: 'Sao Hỏa' });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator('iframe')).toHaveAttribute('src', 'https://eyes.nasa.gov/apps/solar-system/#/mars');
  await expect(dialog.getByRole('link', { name: /Mở ở thẻ mới/ })).toHaveAttribute(
    'href',
    'https://eyes.nasa.gov/apps/solar-system/#/mars',
  );
  await dialog.getByRole('button', { name: 'Trở về Trái Đất — Khám phá đồng lúa Nghệ An' }).click();
  await expect(dialog).toBeHidden();
  await expect(page).toHaveURL(/canh=nghe-an/);
});

const canonical = (name: string) =>
  JSON.parse(readFileSync(new URL(`../data/canonical/${name}`, import.meta.url), 'utf-8'));

test('T5 the evidence page shows the data-quality report as written, warnings included', async ({ page }) => {
  const q = canonical('quality.json');
  await page.goto('/#/bang-chung');
  const section = page.locator('section[aria-labelledby="ev-quality"]');
  for (const st of ['pass', 'warn', 'fail'])
    await expect(section.locator(`p[data-status="${st}"] strong`)).toHaveText(String(q.counts[st]));
  await expect(section.locator('li[data-status="warn"]')).toHaveCount(q.counts.warn);
  await expect(section.locator('li[data-status="fail"]')).toHaveCount(q.counts.fail);
});

test('T5 the copilot answers from data and abstains otherwise', async ({ page }) => {
  await page.goto('/#/tro-ly');
  await page.getByRole('button', { name: 'Năm 2010 có hạn không?' }).click();
  await expect(page.locator('ol[aria-live] > li').first()).toContainText('Năm 2010', { timeout: 30_000 });
  await page.getByLabel('Câu hỏi của bạn').fill('công thức nấu phở');
  await page.getByRole('button', { name: 'Hỏi', exact: true }).click();
  await expect(page.locator('ol[aria-live] > li').last()).toContainText(/Chưa đủ dữ liệu|chưa có bằng chứng/, {
    timeout: 30_000,
  });
});

test('T3 with the API running, the farmer question returns the six plans in study order and never a ranking', async ({
  page,
}) => {
  test.skip(!(await copilotUp(page)), 'no copilot backend is running');
  await page.goto('/#/tro-ly');
  await page
    .getByRole('button', { name: /cuối kênh/ })
    .first()
    .click();
  const answer = page.locator('ol[aria-live] > li').first();
  await expect(answer).toContainText('không chọn cách trồng thay gia đình bạn', { timeout: 30_000 });
  await expect(answer.getByRole('link', { name: /Xem thẻ so sánh/ })).toHaveCount(6);
  await expect(answer).not.toContainText('tốt nhất');
});

for (const url of [
  '/#/',
  '/#/nong-dan/ruong',
  PLANS_URL,
  '/#/can-bo',
  '/#/khoa-hoc',
  '/#/dai-quan-sat?canh=insight',
  '/#/bang-chung',
  '/#/tro-ly',
  '/#/dang-nhap',
  '/#/da-luu',
]) {
  test(`T7 T8 no WCAG 2.2 AA violations on ${url}`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    const result = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze();
    const summary = result.violations.map(
      (v) =>
        `${v.id} (${v.impact}): ${v.nodes
          .slice(0, 3)
          .map((n) => n.target.join(' '))
          .join(' | ')}`,
    );
    expect(summary).toEqual([]);
  });
}

test('T10 the page never scrolls sideways', async ({ page }) => {
  for (const url of [
    '/#/',
    PLANS_URL,
    '/#/can-bo',
    '/#/khoa-hoc',
    '/#/dai-quan-sat?canh=satellites',
    '/#/bang-chung',
    '/#/tro-ly',
    '/#/dang-nhap',
    '/#/da-luu',
  ]) {
    await page.goto(url);
    await page.waitForTimeout(400);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, url).toBeLessThanOrEqual(0);
  }
});

test('T6 no visible text is smaller than 17 px (H6)', async ({ page }) => {
  for (const url of [
    '/#/',
    PLANS_URL,
    '/#/can-bo',
    '/#/dai-quan-sat?canh=analysis',
    '/#/bang-chung',
    '/#/tro-ly',
    '/#/dang-nhap',
    '/#/da-luu',
  ]) {
    await page.goto(url);
    await page.reload();
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const small = await page.evaluate(() => {
      // SVG text is drawn at its font size times the scale of its drawing (rendered width / viewBox width)
      const scaleOf = (el: Element) => {
        const svg = el.closest('svg');
        const box = svg?.viewBox.baseVal;
        return svg && box && box.width ? svg.getBoundingClientRect().width / box.width : 1;
      };
      const out: string[] = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const el = n.parentElement;
        if (!el || !n.textContent?.trim()) continue;
        if (el.closest('.visually-hidden, [aria-hidden="true"], title, script, style, option')) continue;
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') continue;
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        const px = parseFloat(cs.fontSize) * scaleOf(el);
        if (px < 16.995) out.push(`${px.toFixed(2)}px ${n.textContent.trim().slice(0, 30)}`);
      }
      return out.slice(0, 8);
    });
    expect(small, url).toEqual([]);
  }
});

// D-167: the farmer routes, the home page and the other pages make no third-party request; NASA GIBS tiles and the NASA
// Eyes frame on /dai-quan-sat are the one allowed exception, so that page is not in this list
test('T14 no page outside the observatory makes a third-party request', async ({ page, baseURL }) => {
  const own = new URL(baseURL ?? 'http://127.0.0.1:8000/').origin;
  const outside: string[] = [];
  // an antivirus on a team laptop injects its own script into every page; that request is not the app's
  const local = (u: URL) => u.hostname.endsWith('.kaspersky-labs.com');
  page.on('request', (r) => {
    const u = new URL(r.url());
    if (/^https?:$/.test(u.protocol) && u.origin !== own && !local(u)) outside.push(r.url());
  });
  for (const url of [
    '/#/',
    '/#/nong-dan',
    '/#/nong-dan/ruong',
    '/#/nong-dan/nam?ruong=canal_end&nam=2010',
    '/#/nong-dan/uu-tien?ruong=canal_end&nam=2010',
    PLANS_URL,
    '/#/phuong-phap',
    '/#/can-bo',
    '/#/khoa-hoc',
    '/#/bang-chung',
    '/#/tro-ly',
  ]) {
    await page.goto(url);
    await page.waitForLoadState('networkidle');
  }
  expect(outside).toEqual([]);
});

// walkthrough 2026-11-14: after a tap the picked year's detail is on screen, not under the sticky Next bar
test('T28 a picked year scrolls its detail into view above the sticky bar', async ({ page }) => {
  await page.goto('/#/nong-dan/nam?ruong=canal_end');
  await page.getByTestId('year-1998').click();
  const card = page.getByRole('heading', { level: 2, name: 'Năm 1998' }).locator('xpath=ancestor::article');
  await expect(card).toBeInViewport();
  // the scroll is smooth unless motion is reduced, so the place is checked once the scroll has settled; the Next bar
  // is sticky at the bottom at both widths
  const clear = async () => {
    const bar = await page.getByRole('link', { name: 'Tiếp tục' }).boundingBox();
    const top = await card.boundingBox();
    return !!top && !!bar && top.y >= 0 && top.y + 40 < bar.y;
  };
  await expect.poll(clear, { timeout: 5_000 }).toBe(true);
});

// walkthrough 2026-11-14: the note that three choices lead to the same plans is read before choosing
test('UI-UX-SPEC 7 field screen, no 14 test id: the same-plans note sits above the field choices', async ({ page }) => {
  await page.goto('/#/nong-dan/ruong');
  const note = await page.getByText('Ba ô đầu đều là ruộng thiếu nước', { exact: false }).boundingBox();
  const first = await page.getByRole('radio').first().boundingBox();
  expect(note && first && note.y < first.y).toBe(true);
});

// UI-UX-SPEC T35 print, D-170: the folded per-year tables print
test('T35 print: the folded per-year tables show in print', async ({ page }) => {
  await page.goto(PLANS_URL);
  const table = page.locator('#card-cc1-weather-years table');
  await expect(table).toBeHidden();
  await page.emulateMedia({ media: 'print' });
  await expect(table).toBeVisible();
  await expect(page.locator('#card-cc1-water-years table')).toBeVisible();
});
