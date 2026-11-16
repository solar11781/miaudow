import { expect, test, type Page } from '@playwright/test';
import { vi } from '../src/i18n/vi';

// D-187 (roleplay audit 2026-11-15, F2): the source notes move from the cards into the source sheets; the card keeps
// its warnings (H17), the statistics office credit in the rice block (UI-UX-SPEC 12b) and the soil model label
const PLANS_URL = '/#/nong-dan/phuong-an?ruong=water_short&nam=2010&uutien=income';
const IDS = ['usual', 'usual_p03', 'cc1', 'cc2', 'cc3', 'cc4'];
// D-187 item 4 (F1): each row under the card head folds behind its heading button
const openRow = (page: Page, id: string, row: string) =>
  page.getByTestId(`card-${id}-row-${row}`).locator('h3 > button').click();

test('T16 card-warnings each card shows its warnings, and the rice and soil labels stay visible', async ({ page }) => {
  await page.goto(PLANS_URL);
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  for (const id of IDS) {
    const card = page.getByTestId(`card-${id}`);
    for (const line of [vi.farmer.trialNote, vi.farmer.priceYear('2020-21'), vi.common.notForecast, vi.common.support])
      await expect(card.getByText(line, { exact: true }), `${id}: ${line}`).toBeVisible();
    // the money row's heading: profit in the trial, not on the farmer's field (CLAUDE.md: revenue is not profit)
    const heading = page.getByTestId(`card-${id}-row-money`).locator('h3');
    await expect(heading, id).toBeVisible();
    await expect(heading, id).toContainText(vi.farmer.rows.money);
  }
  // the two rice cards: the credit sits inside the rice block of the weather row
  for (const id of ['usual', 'usual_p03']) {
    await openRow(page, id, 'weather');
    const rice = page.getByTestId(`card-${id}-row-weather`);
    await expect(rice.getByText(vi.farmer.rice.nsoCredit, { exact: true }), id).toBeVisible();
  }
  for (const id of ['usual', 'cc1', 'cc2', 'cc3', 'cc4']) {
    await openRow(page, id, 'water');
    const water = page.getByTestId(`card-${id}-row-water`);
    await expect(water.getByText(vi.farmer.rows.soilNote, { exact: true }), id).toBeVisible();
  }
});

test('D-187 a note that left the card opens in the source sheet of its number', async ({ page }) => {
  await page.goto(PLANS_URL);
  const money = page.getByTestId('card-cc1-row-money');
  await expect(money).not.toContainText('Bảng 13');
  await expect(money).not.toContainText('RVAC');
  await openRow(page, 'cc1', 'money');
  await money.locator('ul [data-value]').first().click();
  const sheet = page.getByTestId('source-sheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toContainText(vi.farmer.profitTable);
  await expect(sheet).toContainText('RVAC');
  await page.keyboard.press('Escape');
  await expect(sheet).toBeHidden();
});

// D-187 (F4): each risk quote is one plain line on the card; the full quote opens with the line's source button
test('D-187 a consideration is one plain line and its quote opens in the source sheet', async ({ page }) => {
  await page.goto(PLANS_URL);
  await openRow(page, 'cc1', 'checks');
  const checks = page.getByTestId('card-cc1-row-checks');
  const cost = checks.locator('li', { hasText: vi.farmer.considerations.cost.line });
  await expect(cost).toBeVisible();
  await expect(checks).not.toContainText('Thị trường tiêu thụ nhỏ hẹp');
  await cost.getByRole('button').click();
  const sheet = page.getByTestId('source-sheet');
  await expect(sheet).toContainText(vi.sheet.quote);
  await expect(sheet).toContainText(
    'Tổng chi phí trồng lạc và ớt chỉ thiên F1 thường cao gấp 2 - 3 lần so với trồng lúa.',
  );
});

// D-187 (F5): each card lists the officer page's questions for its plan; D-191: the trial-field question every plan
// shares is asked once, in the closing box
test('D-187 each card lists the questions for the officer of its plan', async ({ page }) => {
  await page.goto(PLANS_URL);
  for (const id of IDS) {
    await openRow(page, id, 'checks');
    const checks = page.getByTestId(`card-${id}-row-checks`);
    await expect(checks.getByText(vi.farmer.askOfficer, { exact: true }), id).toBeVisible();
    expect(await checks.locator('ol li').count(), id).toBeGreaterThan(0);
    await expect(checks, id).not.toContainText('ruộng thử ở Lưu Sơn');
  }
  await expect(page.getByTestId('card-cc4-row-checks')).toContainText('hợp đồng thu mua ngô sinh khối');
  await expect(page.locator('section[aria-labelledby="ask-officer"]')).toContainText(
    vi.farmer.officerQuestions[0] ?? '',
  );
});

// D-190 (roleplay audit 2026-11-15, F9): one name per plan with its crops under it, and money in million dong per ha;
// the source sheet keeps the paper's exact thousand value and unit (P-02 Table 13)
test('D-190 each plan has one name and its money is in million dong per hectare', async ({ page }) => {
  await page.goto(PLANS_URL);
  const jump = page.getByRole('navigation', { name: vi.farmer.jumpTo });
  await expect(jump).toContainText(vi.farmer.trialShort('1'));
  await expect(jump).not.toContainText(/\bCC\d\b/i);
  const head = page.getByTestId('card-cc1-row-header');
  await expect(head.locator('p').first()).toHaveText(vi.farmer.trialShort('1'));
  await expect(page.getByTestId('card-usual-row-header').locator('p').first()).toHaveText(vi.farmer.current);
  await openRow(page, 'cc1', 'money');
  const money = page.getByTestId('card-cc1-row-money');
  const button = money.locator('ul [data-value]').first();
  await expect(button).toContainText(vi.common.millionPerHa);
  const exact = await button.getAttribute('data-value');
  expect(exact).toMatch(/^[\d.]+ nghìn đồng\/ha$/);
  await button.click();
  await expect(page.getByTestId('source-sheet').locator('h2')).toHaveText(exact ?? '');
});

// D-187 item 4 (F1): the jump strip marks the card in view (on a wide screen, the row of two cards in view)
test('D-187 the jump strip marks the card in view', async ({ page }, info) => {
  await page.goto(PLANS_URL);
  const jump = page.getByRole('navigation', { name: vi.farmer.jumpTo });
  const current = jump.locator('a[aria-current="true"]');
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  for (const id of ['cc2', 'cc4']) {
    await page.getByTestId(`card-${id}`).evaluate((el) => el.scrollIntoView({ block: 'center' }));
    await expect(jump.locator(`a[href="#the-${id}"]`), id).toHaveAttribute('aria-current', 'true');
    if (info.project.name === 'phone-360') await expect(current, id).toHaveCount(1);
  }
});

// tonight's walkthrough of F1: a row or card brought into view lands below the sticky jump strip, not under it
test('D-187 the water shortcut and the jump strip land below the strip', async ({ page }) => {
  await page.goto(PLANS_URL);
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  const strip = page.getByRole('navigation', { name: vi.farmer.jumpTo });
  const below = async (target: ReturnType<Page['locator']>) => {
    const [s, t] = await Promise.all([strip.boundingBox(), target.boundingBox()]);
    return (t?.y ?? 0) - ((s?.y ?? 0) + (s?.height ?? 0));
  };
  await page
    .getByTestId('card-cc2')
    .getByRole('link', { name: vi.farmer.summaryWater(vi.farmer.rows.water) })
    .click();
  const heading = page.getByTestId('card-cc2-row-water').locator('h3');
  await expect(heading).toBeInViewport();
  expect(await below(heading)).toBeGreaterThanOrEqual(0);
  await strip.locator('a[href="#the-cc4"]').click();
  const card = page.getByTestId('card-cc4');
  // the strip scrolls smoothly: wait until the card stops moving
  let last = NaN;
  await expect
    .poll(async () => {
      const [was, now] = [last, (last = await below(card))];
      return now === was;
    })
    .toBe(true);
  expect(last).toBeGreaterThanOrEqual(0);
  await expect(card.locator('h2')).toBeInViewport();
});

// visual audit 2026-11-16: the stamp's word ran out of its box and touched the title
for (const [lang, path] of [
  ['vi', '/#/nong-dan/phuong-an'],
  ['en', '/#/farmer/plans'],
] as const)
  test(`the source sheet's stamp holds its word (${lang})`, async ({ page }) => {
    await page.goto(`${path}?ruong=water_short&nam=2010&uutien=income`);
    await openRow(page, 'cc1', 'money');
    await page.getByTestId('card-cc1-row-money').locator('ul [data-value]').first().click();
    const stamp = page.getByTestId('source-sheet').locator('header > span[aria-hidden="true"]');
    await expect(stamp).toBeVisible();
    const fits = await stamp.evaluate((el) => ({ word: el.scrollWidth, box: el.clientWidth }));
    expect(fits.word).toBeLessThanOrEqual(fits.box);
    expect(await stamp.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(17);
  });
