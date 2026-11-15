import { expect, test, type Page } from '@playwright/test';

// The acceptance tests of UI-UX-SPEC section 14 that no other browser test covers. Expected texts are copied from
// src/i18n/vi.ts (key named next to each); expected data come from the API response the page loaded.
const PLANS_URL = '/#/nong-dan/phuong-an?ruong=canal_end&nam=2010,2020&uutien=income';
const YEARS_URL = '/#/nong-dan/nam?ruong=canal_end&nam=2010,2020';
const NOT_FORECAST = 'Năm đã qua, không phải dự báo'; // common.notForecast
const SUPPORT =
  'Ứng dụng giúp bạn xem và so sánh. Nó không thay thế kinh nghiệm của bạn và lời khuyên của cán bộ khuyến nông.'; // common.support
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
