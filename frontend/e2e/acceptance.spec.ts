import { expect, test, type Page } from '@playwright/test';

// The acceptance tests of UI-UX-SPEC section 14 that no other browser test covers. Expected texts are copied from
// src/i18n/vi.ts (key named next to each); expected data come from the API response the page loaded.
const PLANS_URL = '/#/nong-dan/phuong-an?ruong=canal_end&nam=2010,2020&uutien=income';
const YEARS_URL = '/#/nong-dan/nam?ruong=canal_end&nam=2010,2020';
const NOT_FORECAST = 'Năm đã qua, không phải dự báo'; // common.notForecast
const SUPPORT =
  'Ứng dụng giúp bạn xem và so sánh. Nó không thay thế kinh nghiệm của bạn và lời khuyên của cán bộ khuyến nông.'; // common.support
const COMPUTED_NOTE = 'Đây là phép tính của chúng tôi từ số liệu NASA, không phải số liệu chính thức.'; // common.computedNote
const RULE_TEXT = 'Lời văn của quy định'; // sheet.ruleText
const yearsCount = (n: number) => `${n} năm có số thật`; // farmer.rice.yearsCount

const SCENES = ['cosmos', 'earth', 'satellites', 'vietnam', 'nghe-an', 'do-luong', 'analysis', 'insight'];
const PAGES = [
  '/#/',
  '/#/nong-dan',
  '/#/nong-dan/ruong',
  YEARS_URL,
  '/#/nong-dan/uu-tien?ruong=canal_end&nam=2010,2020',
  PLANS_URL,
  '/#/can-bo',
  '/#/khoa-hoc',
  '/#/phuong-phap',
  ...SCENES.map((c) => `/#/dai-quan-sat?canh=${c}`),
  '/#/bang-chung',
  '/#/tro-ly',
  '/#/dang-nhap',
  '/#/da-luu',
];

type Text = { vi: string; en: string };
type Compare = {
  rules: { code: string; rule_text: Text; threshold_source_id: string; values_source_ids: string[] }[];
  plans: { id: string; stability: { years_count: number; scope: Text }[] | null }[];
  sources: Record<string, { citation: Text }>;
};

async function openPlans(page: Page): Promise<Compare> {
  const res = page.waitForResponse((r) => r.url().endsWith('/api/compare') && r.request().method() === 'POST');
  await page.goto(PLANS_URL);
  const body = (await (await res).json()) as Compare;
  await expect(page.locator('article[id^="the-"]')).toHaveCount(body.plans.length);
  return body;
}

// the per-year share tables fold (UI-UX-SPEC section 9); open them so their buttons count too
async function openFolds(page: Page) {
  const folded = page.locator('main button[aria-controls$="-years"][aria-expanded="false"]');
  await folded.evaluateAll((folds) => folds.forEach((b) => (b as HTMLButtonElement).click()));
  await expect(folded).toHaveCount(0);
}

test('T2 no slider on any page', async ({ page }) => {
  test.setTimeout(120_000);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const url of PAGES) {
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
    await expect(page.locator('input[type="range"], [role="slider"]'), url).toHaveCount(0);
  }
});

test('T13 the not-a-forecast label is visible on the past-years and plans pages', async ({ page }) => {
  await page.goto(YEARS_URL);
  await expect(page.getByRole('main').getByText(NOT_FORECAST).first()).toBeVisible();
  await openPlans(page);
  await expect(page.getByRole('main').getByText(NOT_FORECAST).first()).toBeVisible();
});

// H18 names the farmer start (`/`, here /nong-dan) and the plans page; the footer's copy on every page is not counted
test('T17 the support reminder is visible on the farmer start and plans pages', async ({ page }) => {
  await page.goto('/#/nong-dan');
  await expect(page.getByRole('main').getByText(SUPPORT).first()).toBeVisible();
  await openPlans(page);
  await expect(page.getByRole('main').getByText(SUPPORT).first()).toBeVisible();
});

// T18's `common.dataLine` part is left out: the spec row still names it, and decision D-188 drops the data line
test('T18 every condition share on the cards opens the rule text, both NASA sources and the computed note', async ({
  page,
}) => {
  test.setTimeout(180_000);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const res = await openPlans(page);
  await openFolds(page);
  const shares = page.locator('main td[data-rule] button[data-value]');
  const count = await shares.count();
  expect(count).toBeGreaterThan(0);
  const sheet = page.getByTestId('source-sheet');
  for (let i = 0; i < count; i++) {
    const button = shares.nth(i);
    const code = await button.evaluate((b) => b.closest('td')?.getAttribute('data-rule'));
    const rule = res.rules.find((r) => r.code === code);
    expect(rule, `rule ${code}`).toBeDefined();
    await button.click();
    await expect(sheet).toBeVisible();
    const text = (await sheet.textContent()) ?? '';
    for (const part of [
      RULE_TEXT,
      rule?.rule_text.vi,
      ...[rule?.threshold_source_id, ...(rule?.values_source_ids ?? [])].map(
        (id) => res.sources[id ?? '']?.citation.vi,
      ),
      COMPUTED_NOTE,
    ])
      expect(part && text.includes(part), `share ${i} (${code}): ${part}`).toBe(true);
    // H19: the threshold source is R-A01 and the value sources are R-N01 and R-N02
    expect([rule?.threshold_source_id, ...(rule?.values_source_ids ?? [])]).toEqual(['R-A01', 'R-N01', 'R-N02']);
    await page.keyboard.press('Escape');
    await expect(sheet).toBeHidden();
  }
});

// UI-UX-SPEC section 8 item 2 places a legend with one "?" button per rule (`legend-<rule code>`) on /nam
test.fixme('T18 every legend "?" button on the past-years page opens the rule sheet', async ({ page }) => {
  // fixme: /nam has no legend and no legend-<rule code> buttons, so this part of T18 cannot run as written
  await page.goto(YEARS_URL);
  const legend = page.locator('[data-testid^="legend-"]');
  await expect(legend).toHaveCount(5);
  for (const button of await legend.all()) {
    await button.click();
    const sheet = page.getByTestId('source-sheet');
    await expect(sheet).toContainText(RULE_TEXT);
    await expect(sheet).toContainText(COMPUTED_NOTE);
    await page.keyboard.press('Escape');
  }
});

test('T26 every stability block shows its years count and its scope', async ({ page }) => {
  const res = await openPlans(page);
  const blocks = res.plans.flatMap((p) => (p.stability ?? []).map((st) => ({ id: p.id, ...st })));
  expect(blocks.length).toBeGreaterThan(0);
  for (const { id, years_count, scope } of blocks) {
    const same = blocks.filter((b) => b.id === id && b.years_count === years_count && b.scope.vi === scope.vi);
    const lines = page
      .getByTestId(`card-${id}-row-weather`)
      .locator('p')
      .filter({ hasText: yearsCount(years_count) })
      .filter({ hasText: scope.vi });
    await expect(lines, `card ${id}`).toHaveCount(same.length);
    await expect(lines.first()).toBeVisible();
  }
});
